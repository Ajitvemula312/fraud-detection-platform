from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class TransactionRecord(BaseModel):
    transaction_id: str
    timestamp: datetime
    amount: float = Field(ge=0)
    account_id: str
    merchant_category: str
    transaction_type: str
    region: str
    account_age_days: int = Field(ge=0)
    hour_of_day: int = Field(ge=0, le=23)
    previous_txn_count: int = Field(ge=0)
    avg_spend_rolling: float = Field(ge=0)
    amount_to_avg_ratio: float = Field(ge=0)
    merchant_txn_count: int = Field(ge=0)
    txn_velocity_score: float
    region_risk_score: float
    amount_zscore: float
    time_delta_seconds: float = Field(ge=0)
    weekend_flag: bool


class PredictionRequest(BaseModel):
    transaction: dict[str, Any]


class PredictionResponse(BaseModel):
    transaction_id: str
    fraud_probability: float = Field(ge=0, le=1)
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    model_name: str
    model_version: str


class BatchPredictionRequest(BaseModel):
    transactions: list[dict[str, Any]]


class BatchPredictionResponse(BaseModel):
    predictions: list[PredictionResponse]


class DriftAlert(BaseModel):
    feature_name: str
    drift_score: float
    threshold: float
    direction: Literal["positive", "negative"]
    observed_value: float
    timestamp: datetime
    message: str


class CurrentMetrics(BaseModel):
    processed_events: int
    high_risk_events: int
    drift_alerts: int
    latest_model_version: str
    precision: float | None = None
    recall: float | None = None
    f1: float | None = None
    roc_auc: float | None = None
    pr_auc: float | None = None
    last_retrained_at: datetime | None = None


class RetrainResult(BaseModel):
    accepted: bool
    model_name: str
    model_version: str
    challenger_metric: float
    incumbent_metric: float
    reason: str


class ScoredEvent(BaseModel):
    schema_version: str = "1.0"
    transaction_id: str
    event_timestamp: datetime
    model_name: str
    model_version: str
    fraud_probability: float = Field(ge=0, le=1)
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    latency_ms: float = Field(ge=0)
    features: dict[str, Any]
    raw_transaction: dict[str, Any]
    actual_label: int | None = None

