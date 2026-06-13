from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fraud_platform.config import AppConfig
from fraud_platform.storage.event_store import JsonLineStore, JsonStateStore
from fraud_platform.streaming.simulator import run_local_demo_stream


class DemoFlowIntegrationTests(unittest.TestCase):
    def test_local_stream_demo_writes_predictions_and_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = AppConfig(project_root=Path(tmpdir))
            summary = run_local_demo_stream(
                config=config,
                max_events=24,
                sleep_seconds=0.0,
                inject_drift_after=6,
            )
            metrics = JsonStateStore(config.metrics_path).read()
            events = JsonLineStore(config.scored_events_path).read_recent(limit=50)

            self.assertEqual(summary["processed_events"], 24)
            self.assertEqual(metrics["processed_events"], 24)
            self.assertEqual(len(events), 24)
            self.assertGreaterEqual(metrics["drift_alerts"], 1)


if __name__ == "__main__":
    unittest.main()
