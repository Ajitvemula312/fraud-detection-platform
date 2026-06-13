from __future__ import annotations

import json
import time
from datetime import datetime, UTC
from typing import Any

import pandas as pd

from fraud_platform.api.service import FraudPlatformService
from fraud_platform.config import AppConfig
from fraud_platform.data.public_dataset import enrich_creditcard_dataset
from fraud_platform.drift.cusum import CUSUMDriftDetector
from fraud_platform.ml.training import score_dataframe, train_model_suite
from fraud_platform.storage.event_store import JsonLineStore, JsonStateStore
from fraud_platform.storage.model_registry import load_active_model_bundle, load_registry
from fraud_platform.streaming.contracts import build_scored_event


def _load_stream_frame(config: AppConfig, max_events: int) -> pd.DataFrame:
    if config.processed_dataset_path.exists():
        df = pd.read_csv(config.processed_dataset_path)
    elif config.sample_dataset_path.exists():
        df = pd.read_csv(config.sample_dataset_path)
    else:
        df = pd.read_csv(config.sample_dataset_path) if config.sample_dataset_path.exists() else None
        if df is None:
            from fraud_platform.data.sample_data import generate_smoke_test_dataset

            df = generate_smoke_test_dataset(rows=max_events * 2)
    if "amount_to_avg_ratio" not in df.columns:
        df = enrich_creditcard_dataset(df)
    return df.head(max_events).copy()


def _ensure_model(config: AppConfig) -> dict[str, Any]:
    try:
        return load_active_model_bundle(config.registry_path)
    except FileNotFoundError:
        from fraud_platform.data.sample_data import generate_smoke_test_dataset

        train_model_suite(generate_smoke_test_dataset(rows=360), config)
        return load_active_model_bundle(config.registry_path)


def run_local_demo_stream(
    config: AppConfig,
    max_events: int = 120,
    sleep_seconds: float = 0.05,
    inject_drift_after: int = 70,
) -> dict[str, Any]:
    config.ensure_dirs()
    bundle = _ensure_model(config)
    registry = load_registry(config.registry_path)
    stream_df = _load_stream_frame(config, max_events)
    scored_store = JsonLineStore(config.scored_events_path)
    alert_store = JsonLineStore(config.alerts_path)
    metrics_store = JsonStateStore(config.metrics_path)
    service = FraudPlatformService(config)

    baseline_means = bundle["baseline_stats"]["means"]
    baseline_stds = bundle["baseline_stats"]["stds"]
    detector = CUSUMDriftDetector(reference_means=baseline_means, reference_stds=baseline_stds)

    metrics = service.current_metrics().model_dump(mode="json")
    metrics["latest_model_version"] = registry["metadata"]["model_version"]
    start = time.perf_counter()

    for event_index, (_, row) in enumerate(stream_df.iterrows(), start=1):
        transaction = row.to_dict()
        if inject_drift_after and event_index >= inject_drift_after:
            transaction["Amount"] = float(transaction["Amount"]) * 3.5
            transaction["amount_to_avg_ratio"] = float(transaction["amount_to_avg_ratio"]) * 2.0
            transaction["txn_velocity_score"] = float(transaction["txn_velocity_score"]) * 1.75
            transaction["risk_aggregation_score"] = float(transaction["risk_aggregation_score"]) * 2.4

        frame = pd.DataFrame([transaction])
        event_start = time.perf_counter()
        fraud_probability = float(score_dataframe(bundle, frame)[0])
        latency_ms = (time.perf_counter() - event_start) * 1000
        scored_event = build_scored_event(
            transaction=transaction,
            fraud_probability=fraud_probability,
            model_name=bundle["model_name"],
            model_version=bundle["model_version"],
            latency_ms=latency_ms,
            actual_label=int(transaction.get("is_fraud", 0)),
        )
        scored_store.append(scored_event.model_dump(mode="json"))
        metrics["processed_events"] = int(metrics.get("processed_events", 0)) + 1
        if scored_event.risk_level == "HIGH":
            metrics["high_risk_events"] = int(metrics.get("high_risk_events", 0)) + 1

        alerts = detector.update_many(
            {
                "Amount": float(transaction["Amount"]),
                "amount_to_avg_ratio": float(transaction["amount_to_avg_ratio"]),
                "txn_velocity_score": float(transaction["txn_velocity_score"]),
                "risk_aggregation_score": float(transaction["risk_aggregation_score"]),
            }
        )
        for alert in alerts:
            metrics["drift_alerts"] = int(metrics.get("drift_alerts", 0)) + 1
            alert_store.append(alert.model_dump(mode="json"))
            if metrics["drift_alerts"] % 3 == 0:
                retrain_result = service.retrain()
                metrics["last_retrained_at"] = datetime.now(UTC).isoformat()
                if retrain_result.accepted:
                    metrics["latest_model_version"] = retrain_result.model_version

        metrics_store.write(metrics)
        if sleep_seconds:
            time.sleep(sleep_seconds)

    duration_seconds = time.perf_counter() - start
    return {
        "processed_events": metrics["processed_events"],
        "high_risk_events": metrics["high_risk_events"],
        "drift_alerts": metrics["drift_alerts"],
        "latest_model_version": metrics["latest_model_version"],
        "duration_seconds": round(duration_seconds, 3),
    }


def export_recent_stream_state(config: AppConfig) -> str:
    payload = {
        "events": JsonLineStore(config.scored_events_path).read_recent(limit=20),
        "alerts": JsonLineStore(config.alerts_path).read_recent(limit=20),
        "metrics": JsonStateStore(config.metrics_path).read(),
    }
    return json.dumps(payload, default=str)
