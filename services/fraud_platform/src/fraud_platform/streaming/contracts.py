from __future__ import annotations

from datetime import datetime, UTC
from typing import Any

from fraud_platform.schemas import ScoredEvent
from fraud_platform.utils.risk import to_risk_level


def build_scored_event(
    transaction: dict[str, Any],
    fraud_probability: float,
    model_name: str,
    model_version: str,
    latency_ms: float,
    actual_label: int | None = None,
) -> ScoredEvent:
    return ScoredEvent(
        transaction_id=str(transaction["transaction_id"]),
        event_timestamp=datetime.now(UTC),
        model_name=model_name,
        model_version=model_version,
        fraud_probability=round(fraud_probability, 4),
        risk_level=to_risk_level(fraud_probability),
        latency_ms=round(latency_ms, 3),
        features={key: value for key, value in transaction.items() if key not in {"is_fraud"}},
        raw_transaction=transaction,
        actual_label=actual_label,
    )

