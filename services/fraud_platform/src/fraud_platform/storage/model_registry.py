from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib


def register_model(registry_path: Path, model_path: Path, metadata: dict[str, Any]) -> None:
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "active_model_path": str(model_path),
        "metadata": metadata,
    }
    registry_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_registry(registry_path: Path) -> dict[str, Any]:
    if not registry_path.exists():
        raise FileNotFoundError(
            f"No registry found at {registry_path}. Train a model first with `make train`."
        )
    return json.loads(registry_path.read_text(encoding="utf-8"))


def load_active_model_bundle(registry_path: Path) -> dict[str, Any]:
    registry = load_registry(registry_path)
    return joblib.load(registry["active_model_path"])

