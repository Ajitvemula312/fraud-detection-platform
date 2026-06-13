from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class LocalRunTracker:
    output_path: Path

    def log_run(self, run_name: str, params: dict[str, Any], metrics: dict[str, float], artifacts: dict[str, Any]) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "run_name": run_name,
            "timestamp": datetime.now(UTC).isoformat(),
            "params": params,
            "metrics": metrics,
            "artifacts": artifacts,
        }
        with self.output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")


class MLflowCompatibleTracker:
    def __init__(self, tracking_dir: Path):
        self.tracking_dir = tracking_dir
        self.local_tracker = LocalRunTracker(tracking_dir / "local_runs.jsonl")
        try:
            import mlflow  # type: ignore
        except ImportError:
            self.mlflow = None
        else:
            self.mlflow = mlflow

    def log_run(self, run_name: str, params: dict[str, Any], metrics: dict[str, float], artifacts: dict[str, Any]) -> None:
        self.local_tracker.log_run(run_name, params, metrics, artifacts)
        if self.mlflow is None:
            return
        tracking_uri = self.tracking_dir.resolve().as_uri()
        self.mlflow.set_tracking_uri(tracking_uri)
        self.mlflow.set_experiment("fraud_detection")
        with self.mlflow.start_run(run_name=run_name):
            self.mlflow.log_params(params)
            self.mlflow.log_metrics(metrics)
            for artifact_name, artifact_value in artifacts.items():
                self.mlflow.log_text(str(artifact_value), f"{artifact_name}.txt")

