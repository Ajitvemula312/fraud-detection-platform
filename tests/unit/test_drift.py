from __future__ import annotations

import unittest

from fraud_platform.drift.cusum import CUSUMDriftDetector


class DriftTests(unittest.TestCase):
    def test_cusum_emits_alert_after_sustained_shift(self) -> None:
        detector = CUSUMDriftDetector(
            reference_means={"Amount": 100.0},
            reference_stds={"Amount": 10.0},
            threshold_multiplier=3.0,
            slack_multiplier=0.2,
        )
        alert = None
        for value in [104.0, 108.0, 135.0, 140.0]:
            alert = detector.update("Amount", value) or alert
        self.assertIsNotNone(alert)
        assert alert is not None
        self.assertEqual(alert.feature_name, "Amount")


if __name__ == "__main__":
    unittest.main()

