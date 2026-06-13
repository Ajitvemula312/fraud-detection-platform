from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]


@dataclass(slots=True)
class AppConfig:
    project_root: Path = field(default_factory=_project_root)
    model_name: str = "fraud-xgboost-prod"
    raw_dataset_path: Path = field(init=False)
    processed_dataset_path: Path = field(init=False)
    sample_dataset_path: Path = field(init=False)
    models_dir: Path = field(init=False)
    mlruns_dir: Path = field(init=False)
    state_dir: Path = field(init=False)
    metrics_path: Path = field(init=False)
    alerts_path: Path = field(init=False)
    scored_events_path: Path = field(init=False)
    retraining_path: Path = field(init=False)
    registry_path: Path = field(init=False)
    dashboard_port: int = 8501
    api_port: int = 8000
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topics: dict[str, str] = field(
        default_factory=lambda: {
            "raw": "transactions.raw",
            "features": "transactions.features",
            "predictions": "predictions.scored",
            "alerts": "monitoring.alerts",
        }
    )

    def __post_init__(self) -> None:
        data_dir = self.project_root / "data"
        artifacts_dir = self.project_root / "artifacts"
        self.raw_dataset_path = data_dir / "raw" / "creditcard.csv"
        self.processed_dataset_path = data_dir / "processed" / "fraud_dataset_enriched.csv"
        self.sample_dataset_path = data_dir / "sample" / "smoke_transactions.csv"
        self.models_dir = artifacts_dir / "models"
        self.mlruns_dir = artifacts_dir / "mlruns"
        self.state_dir = artifacts_dir / "state"
        self.metrics_path = self.state_dir / "current_metrics.json"
        self.alerts_path = self.state_dir / "drift_alerts.jsonl"
        self.scored_events_path = self.state_dir / "scored_events.jsonl"
        self.retraining_path = self.state_dir / "retraining_events.jsonl"
        self.registry_path = self.models_dir / "registry.json"

    def ensure_dirs(self) -> None:
        for path in (
            self.raw_dataset_path.parent,
            self.processed_dataset_path.parent,
            self.sample_dataset_path.parent,
            self.models_dir,
            self.mlruns_dir,
            self.state_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

