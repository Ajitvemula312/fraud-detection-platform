from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fraud_platform.config import AppConfig
from fraud_platform.data.sample_data import generate_smoke_test_dataset
from fraud_platform.ml.training import score_dataframe, train_model_suite
from fraud_platform.storage.model_registry import load_active_model_bundle, load_registry


class TrainingTests(unittest.TestCase):
    def test_training_creates_registry_and_model_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = AppConfig(project_root=Path(tmpdir))
            dataframe = generate_smoke_test_dataset(rows=180, seed=13)
            result = train_model_suite(dataframe, config)

            self.assertTrue(result.model_path.exists())
            registry = load_registry(config.registry_path)
            bundle = load_active_model_bundle(config.registry_path)
            probabilities = score_dataframe(bundle, dataframe.head(5))

            self.assertEqual(registry["metadata"]["model_version"], result.model_version)
            self.assertEqual(len(probabilities), 5)


if __name__ == "__main__":
    unittest.main()

