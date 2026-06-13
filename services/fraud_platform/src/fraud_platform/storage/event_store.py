from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Any


class JsonLineStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, payload: dict[str, Any]) -> None:
        enriched = dict(payload)
        enriched.setdefault("stored_at", datetime.now(UTC).isoformat())
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(enriched, default=str) + "\n")

    def read_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines[-limit:]]


class JsonStateStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, payload: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

