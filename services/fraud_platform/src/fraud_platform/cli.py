from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
import subprocess

import pandas as pd

from fraud_platform.config import AppConfig
from fraud_platform.data.public_dataset import prepare_training_dataset
from fraud_platform.data.sample_data import generate_smoke_test_dataset, write_smoke_test_dataset
from fraud_platform.ml.training import train_model_suite
from fraud_platform.schemas import CurrentMetrics
from fraud_platform.storage.event_store import JsonStateStore


def _load_training_dataframe(config: AppConfig, source: str) -> pd.DataFrame:
    if source == "sample":
        dataframe = generate_smoke_test_dataset()
        dataframe.to_csv(config.sample_dataset_path, index=False)
        return dataframe
    if source == "raw":
        dataframe = prepare_training_dataset(config.raw_dataset_path)
        dataframe.to_csv(config.processed_dataset_path, index=False)
        return dataframe
    if config.raw_dataset_path.exists():
        dataframe = prepare_training_dataset(config.raw_dataset_path)
        dataframe.to_csv(config.processed_dataset_path, index=False)
        return dataframe
    if config.processed_dataset_path.exists():
        return pd.read_csv(config.processed_dataset_path)
    dataframe = generate_smoke_test_dataset()
    dataframe.to_csv(config.sample_dataset_path, index=False)
    return dataframe


def _command_check(command: list[str]) -> dict[str, str | bool | None]:
    binary = shutil.which(command[0])
    if binary is None:
        return {"path": None, "available": False, "detail": "not installed"}
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False, timeout=5)
    except Exception as exc:
        return {"path": binary, "available": False, "detail": str(exc)}
    detail = (completed.stdout or completed.stderr).strip().splitlines()
    return {
        "path": binary,
        "available": completed.returncode == 0,
        "detail": detail[0] if detail else f"exit={completed.returncode}",
    }


def cmd_check_prereqs(_: argparse.Namespace) -> None:
    config = AppConfig()
    checks = {
        "python": _command_check(["python3", "--version"]),
        "docker": _command_check(["docker", "--version"]),
        "java": _command_check(["java", "-version"]),
        "node": _command_check(["node", "--version"]),
        "npm": _command_check(["npm", "--version"]),
    }
    print(json.dumps({"project_root": str(config.project_root), "checks": checks}, indent=2))


def cmd_make_sample_data(args: argparse.Namespace) -> None:
    config = AppConfig()
    config.ensure_dirs()
    path = write_smoke_test_dataset(config.sample_dataset_path, rows=args.rows, seed=args.seed)
    print(f"Wrote sample dataset to {path}")


def cmd_train(args: argparse.Namespace) -> None:
    config = AppConfig()
    dataframe = _load_training_dataframe(config, args.source)
    result = train_model_suite(dataframe, config)
    JsonStateStore(config.metrics_path).write(
        CurrentMetrics(
            processed_events=0,
            high_risk_events=0,
            drift_alerts=0,
            latest_model_version=result.model_version,
            precision=result.metrics.get("precision"),
            recall=result.metrics.get("recall"),
            f1=result.metrics.get("f1"),
            roc_auc=result.metrics.get("roc_auc"),
            pr_auc=result.metrics.get("pr_auc"),
        ).model_dump(mode="json")
    )
    print(
        json.dumps(
            {
                "model_name": result.model_name,
                "model_version": result.model_version,
                "selected_estimator": result.selected_estimator,
                "metrics": result.metrics,
                "model_path": str(result.model_path),
            },
            indent=2,
        )
    )


def cmd_reset_state(_: argparse.Namespace) -> None:
    config = AppConfig()
    config.ensure_dirs()
    for path in (
        config.metrics_path,
        config.alerts_path,
        config.scored_events_path,
        config.retraining_path,
    ):
        if path.exists():
            path.unlink()
    JsonStateStore(config.metrics_path).write(
        CurrentMetrics(
            processed_events=0,
            high_risk_events=0,
            drift_alerts=0,
            latest_model_version="untrained",
        ).model_dump(mode="json")
    )
    print("Reset local demo state.")


def cmd_stream_demo(args: argparse.Namespace) -> None:
    from fraud_platform.streaming.simulator import run_local_demo_stream

    config = AppConfig()
    if args.reset_state:
        cmd_reset_state(args)
    summary = run_local_demo_stream(
        config=config,
        max_events=args.events,
        sleep_seconds=args.sleep,
        inject_drift_after=args.inject_drift_after,
    )
    print(json.dumps(summary, indent=2))


def cmd_retrain(_: argparse.Namespace) -> None:
    from fraud_platform.api.service import FraudPlatformService

    service = FraudPlatformService(AppConfig())
    result = service.retrain()
    print(result.model_dump_json(indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fraud platform CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prereqs = subparsers.add_parser("check-prereqs")
    prereqs.set_defaults(func=cmd_check_prereqs)

    sample = subparsers.add_parser("make-sample-data")
    sample.add_argument("--rows", type=int, default=240)
    sample.add_argument("--seed", type=int, default=42)
    sample.set_defaults(func=cmd_make_sample_data)

    train = subparsers.add_parser("train")
    train.add_argument("--source", choices=["auto", "raw", "sample"], default="auto")
    train.set_defaults(func=cmd_train)

    reset_state = subparsers.add_parser("reset-state")
    reset_state.set_defaults(func=cmd_reset_state)

    stream = subparsers.add_parser("stream-demo")
    stream.add_argument("--events", type=int, default=120)
    stream.add_argument("--sleep", type=float, default=0.05)
    stream.add_argument("--inject-drift-after", type=int, default=70)
    stream.add_argument("--reset-state", action="store_true")
    stream.set_defaults(func=cmd_stream_demo)

    retrain = subparsers.add_parser("retrain")
    retrain.set_defaults(func=cmd_retrain)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
