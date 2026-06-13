from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from fraud_platform.config import AppConfig
from fraud_platform.ml.preprocessing import FeatureSpec, build_preprocessor, infer_feature_spec
from fraud_platform.ml.tracker import MLflowCompatibleTracker
from fraud_platform.storage.model_registry import register_model


def _resolve_xgboost_classifier():
    try:
        from xgboost import XGBClassifier  # type: ignore
    except ImportError:
        return None
    return XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        eval_metric="logloss",
        random_state=42,
        scale_pos_weight=8,
    )


def _candidate_estimators() -> list[tuple[str, Any]]:
    estimators: list[tuple[str, Any]] = [
        (
            "logistic_regression",
            LogisticRegression(
                max_iter=1000,
                class_weight="balanced",
                solver="liblinear",
                random_state=42,
            ),
        ),
        (
            "random_forest",
            RandomForestClassifier(
                n_estimators=250,
                max_depth=14,
                min_samples_leaf=2,
                class_weight="balanced_subsample",
                random_state=42,
                n_jobs=-1,
            ),
        ),
    ]
    xgb = _resolve_xgboost_classifier()
    if xgb is not None:
        estimators.append(("xgboost", xgb))
    return estimators


@dataclass(slots=True)
class TrainingResult:
    model_path: Path
    model_name: str
    model_version: str
    selected_estimator: str
    metrics: dict[str, float]
    feature_spec: FeatureSpec


def _compute_metrics(y_true: pd.Series, probabilities: np.ndarray) -> dict[str, float]:
    predictions = (probabilities >= 0.5).astype(int)
    return {
        "precision": round(float(precision_score(y_true, predictions, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, predictions, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, predictions, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, probabilities)), 4),
        "pr_auc": round(float(average_precision_score(y_true, probabilities)), 4),
    }


def _select_score(metrics: dict[str, float]) -> float:
    return 0.5 * metrics["pr_auc"] + 0.3 * metrics["f1"] + 0.2 * metrics["recall"]


def _baseline_stats(dataframe: pd.DataFrame) -> dict[str, dict[str, float]]:
    tracked = ["Amount", "amount_to_avg_ratio", "txn_velocity_score", "risk_aggregation_score"]
    return {
        "means": {name: round(float(dataframe[name].mean()), 6) for name in tracked},
        "stds": {name: round(float(max(dataframe[name].std(ddof=0), 1e-6)), 6) for name in tracked},
    }


def train_model_suite(dataframe: pd.DataFrame, config: AppConfig) -> TrainingResult:
    return _train_model_suite(dataframe, config, register=True)


def _train_model_suite(dataframe: pd.DataFrame, config: AppConfig, register: bool) -> TrainingResult:
    config.ensure_dirs()
    tracker = MLflowCompatibleTracker(config.mlruns_dir)
    feature_spec = infer_feature_spec(dataframe)
    X = dataframe[feature_spec.numeric_features + feature_spec.categorical_features].copy()
    y = dataframe[feature_spec.target_column].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        stratify=y,
        random_state=42,
    )
    preprocessor = build_preprocessor(feature_spec)

    best: dict[str, Any] | None = None
    for estimator_name, estimator in _candidate_estimators():
        pipeline = Pipeline(
            [
                ("preprocessor", preprocessor),
                ("classifier", estimator),
            ]
        )
        pipeline.fit(X_train, y_train)
        probabilities = pipeline.predict_proba(X_test)[:, 1]
        metrics = _compute_metrics(y_test, probabilities)
        tracker.log_run(
            run_name=estimator_name,
            params={"estimator": estimator_name, "rows": len(dataframe)},
            metrics=metrics,
            artifacts={"feature_spec": feature_spec.to_dict()},
        )
        score = _select_score(metrics)
        if best is None or score > best["score"]:
            best = {
                "name": estimator_name,
                "pipeline": pipeline,
                "metrics": metrics,
                "score": score,
            }

    assert best is not None
    model_version = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    model_filename = f"{config.model_name}-{model_version}.joblib"
    model_path = config.models_dir / model_filename
    bundle = {
        "pipeline": best["pipeline"],
        "model_name": config.model_name,
        "model_version": model_version,
        "selected_estimator": best["name"],
        "metrics": best["metrics"],
        "feature_spec": feature_spec.to_dict(),
        "baseline_stats": _baseline_stats(dataframe),
    }
    joblib.dump(bundle, model_path)
    if register:
        register_model(
            config.registry_path,
            model_path,
            {
                "model_name": config.model_name,
                "model_version": model_version,
                "selected_estimator": best["name"],
                "metrics": best["metrics"],
            },
        )
    return TrainingResult(
        model_path=model_path,
        model_name=config.model_name,
        model_version=model_version,
        selected_estimator=best["name"],
        metrics=best["metrics"],
        feature_spec=feature_spec,
    )


def train_challenger_model(dataframe: pd.DataFrame, config: AppConfig) -> TrainingResult:
    return _train_model_suite(dataframe, config, register=False)


def score_dataframe(bundle: dict[str, Any], dataframe: pd.DataFrame) -> np.ndarray:
    feature_spec = bundle["feature_spec"]
    ordered_columns = feature_spec["numeric_features"] + feature_spec["categorical_features"]
    return bundle["pipeline"].predict_proba(dataframe[ordered_columns])[:, 1]
