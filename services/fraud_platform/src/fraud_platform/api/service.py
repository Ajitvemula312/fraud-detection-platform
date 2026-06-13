from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

import pandas as pd

from fraud_platform.config import AppConfig
from fraud_platform.data.public_dataset import prepare_training_dataset
from fraud_platform.data.sample_data import generate_smoke_test_dataset
from fraud_platform.ml.training import score_dataframe, train_challenger_model
from fraud_platform.schemas import (
    BatchPredictionResponse,
    CurrentMetrics,
    PredictionResponse,
    RetrainResult,
)
from fraud_platform.storage.event_store import JsonLineStore, JsonStateStore
from fraud_platform.storage.model_registry import load_active_model_bundle, load_registry, register_model
from fraud_platform.streaming.contracts import build_scored_event
from fraud_platform.utils.risk import to_risk_level


class FraudPlatformService:
    def __init__(self, config: AppConfig):
        self.config = config
        self.config.ensure_dirs()
        self.metrics_store = JsonStateStore(config.metrics_path)
        self.alert_store = JsonLineStore(config.alerts_path)
        self.scored_store = JsonLineStore(config.scored_events_path)
        self.retraining_store = JsonLineStore(config.retraining_path)
        self._ensure_metrics_file()

    def health(self) -> dict[str, Any]:
        registry = self._safe_registry()
        return {
            "status": "ok",
            "model_loaded": registry is not None,
            "model_version": registry["metadata"]["model_version"] if registry else None,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def predict(self, transaction: dict[str, Any]) -> PredictionResponse:
        bundle = load_active_model_bundle(self.config.registry_path)
        frame = pd.DataFrame([transaction])
        probability = float(score_dataframe(bundle, frame)[0])
        response = PredictionResponse(
            transaction_id=str(transaction["transaction_id"]),
            fraud_probability=round(probability, 4),
            risk_level=to_risk_level(probability),
            model_name=bundle["model_name"],
            model_version=bundle["model_version"],
        )
        scored_event = build_scored_event(
            transaction=transaction,
            fraud_probability=probability,
            model_name=bundle["model_name"],
            model_version=bundle["model_version"],
            latency_ms=0.0,
            actual_label=transaction.get("is_fraud"),
        )
        self.scored_store.append(scored_event.model_dump(mode="json"))
        self._increment_metrics(probability)
        return response

    def batch_predict(self, transactions: list[dict[str, Any]]) -> BatchPredictionResponse:
        predictions = [self.predict(transaction) for transaction in transactions]
        return BatchPredictionResponse(predictions=predictions)

    def current_metrics(self) -> CurrentMetrics:
        payload = self.metrics_store.read()
        return CurrentMetrics.model_validate(payload)

    def drift_events(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.alert_store.read_recent(limit=limit)

    def stream_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.scored_store.read_recent(limit=limit)

    def retrain(self) -> RetrainResult:
        incumbent = self._safe_registry()
        incumbent_metric = (
            float(incumbent["metadata"]["metrics"].get("pr_auc", 0.0))
            if incumbent is not None
            else 0.0
        )

        dataframe = self._retraining_dataframe()
        result = train_challenger_model(dataframe, self.config)
        challenger_metric = float(result.metrics["pr_auc"])
        accepted = challenger_metric >= incumbent_metric
        reason = (
            "Challenger accepted because PR-AUC matched or exceeded incumbent."
            if accepted
            else "Challenger retained for analysis but incumbent still stronger."
        )
        active_model_version = incumbent["metadata"]["model_version"] if incumbent else result.model_version
        if accepted:
            register_model(
                self.config.registry_path,
                result.model_path,
                {
                    "model_name": result.model_name,
                    "model_version": result.model_version,
                    "selected_estimator": result.selected_estimator,
                    "metrics": result.metrics,
                },
            )
            active_model_version = result.model_version
        retrain_result = RetrainResult(
            accepted=accepted,
            model_name=result.model_name,
            model_version=result.model_version,
            challenger_metric=round(challenger_metric, 4),
            incumbent_metric=round(incumbent_metric, 4),
            reason=reason,
        )
        self.retraining_store.append(retrain_result.model_dump(mode="json"))
        payload = self.metrics_store.read()
        payload["latest_model_version"] = active_model_version
        payload["last_retrained_at"] = datetime.now(UTC).isoformat()
        payload["precision"] = result.metrics.get("precision")
        payload["recall"] = result.metrics.get("recall")
        payload["f1"] = result.metrics.get("f1")
        payload["roc_auc"] = result.metrics.get("roc_auc")
        payload["pr_auc"] = result.metrics.get("pr_auc")
        self.metrics_store.write(payload)
        return retrain_result

    def live_stream_snapshot(self) -> str:
        payload = {
            "metrics": self.metrics_store.read(),
            "alerts": self.alert_store.read_recent(limit=20),
            "events": self.scored_store.read_recent(limit=20),
        }
        return f"data: {json.dumps(payload, default=str)}\n\n"

    def _ensure_metrics_file(self) -> None:
        existing = self.metrics_store.read()
        if existing:
            return
        self.metrics_store.write(
            CurrentMetrics(
                processed_events=0,
                high_risk_events=0,
                drift_alerts=0,
                latest_model_version="untrained",
            ).model_dump(mode="json")
        )

    def _increment_metrics(self, probability: float) -> None:
        payload = self.metrics_store.read()
        payload["processed_events"] = int(payload.get("processed_events", 0)) + 1
        if to_risk_level(probability) == "HIGH":
            payload["high_risk_events"] = int(payload.get("high_risk_events", 0)) + 1
        self.metrics_store.write(payload)

    def _retraining_dataframe(self) -> pd.DataFrame:
        if self.config.processed_dataset_path.exists():
            return pd.read_csv(self.config.processed_dataset_path)
        if self.config.raw_dataset_path.exists():
            return prepare_training_dataset(self.config.raw_dataset_path)
        return generate_smoke_test_dataset(rows=360, fraud_ratio=0.18, seed=99)

    def _safe_registry(self) -> dict[str, Any] | None:
        try:
            return load_registry(self.config.registry_path)
        except FileNotFoundError:
            return None
