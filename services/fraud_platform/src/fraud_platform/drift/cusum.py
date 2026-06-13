from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC

from fraud_platform.schemas import DriftAlert


@dataclass(slots=True)
class CUSUMState:
    positive: float = 0.0
    negative: float = 0.0


@dataclass(slots=True)
class CUSUMDriftDetector:
    reference_means: dict[str, float]
    reference_stds: dict[str, float]
    threshold_multiplier: float = 5.0
    slack_multiplier: float = 0.5
    states: dict[str, CUSUMState] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for feature_name in self.reference_means:
            self.states.setdefault(feature_name, CUSUMState())

    def update(self, feature_name: str, observed_value: float) -> DriftAlert | None:
        if feature_name not in self.reference_means:
            return None
        mean = self.reference_means[feature_name]
        std = max(self.reference_stds.get(feature_name, 1.0), 1e-6)
        slack = self.slack_multiplier * std
        threshold = self.threshold_multiplier * std
        delta = observed_value - mean

        state = self.states[feature_name]
        state.positive = max(0.0, state.positive + delta - slack)
        state.negative = min(0.0, state.negative + delta + slack)

        if state.positive > threshold:
            state.positive = 0.0
            return self._build_alert(feature_name, observed_value, state_score=state.positive + delta, threshold=threshold, direction="positive")
        if abs(state.negative) > threshold:
            state.negative = 0.0
            return self._build_alert(feature_name, observed_value, state_score=abs(state.negative) + abs(delta), threshold=threshold, direction="negative")
        return None

    def update_many(self, observation: dict[str, float]) -> list[DriftAlert]:
        alerts: list[DriftAlert] = []
        for feature_name, value in observation.items():
            alert = self.update(feature_name, float(value))
            if alert is not None:
                alerts.append(alert)
        return alerts

    def _build_alert(
        self,
        feature_name: str,
        observed_value: float,
        state_score: float,
        threshold: float,
        direction: str,
    ) -> DriftAlert:
        return DriftAlert(
            feature_name=feature_name,
            drift_score=round(abs(state_score), 4),
            threshold=round(threshold, 4),
            direction=direction,
            observed_value=round(observed_value, 4),
            timestamp=datetime.now(UTC),
            message=f"CUSUM drift detected for {feature_name} with {direction} movement.",
        )

