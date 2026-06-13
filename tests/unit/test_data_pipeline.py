from __future__ import annotations

import unittest

from fraud_platform.data.sample_data import generate_smoke_test_dataset


class DataPipelineTests(unittest.TestCase):
    def test_generate_smoke_dataset_contains_engineered_columns(self) -> None:
        dataframe = generate_smoke_test_dataset(rows=64, seed=7)
        required_columns = {
            "merchant_category",
            "transaction_type",
            "region",
            "previous_txn_count",
            "avg_spend_rolling",
            "amount_to_avg_ratio",
            "txn_velocity_score",
            "risk_aggregation_score",
            "is_fraud",
        }
        self.assertTrue(required_columns.issubset(set(dataframe.columns)))
        self.assertEqual(len(dataframe), 64)


if __name__ == "__main__":
    unittest.main()

