from __future__ import annotations

import unittest

import numpy as np

import train


class ThresholdSelectionControlTests(unittest.TestCase):
    def test_select_threshold_from_grid_prefers_rate_cap_when_enabled(self) -> None:
        probabilities = np.array([0.95, 0.85, 0.75, 0.65, 0.55, 0.45], dtype=np.float64)
        labels = np.array([0, 0, 0, 0, 0, 1], dtype=np.float32)
        thresholds = np.array([0.40, 0.80], dtype=np.float64)

        unconstrained = train.select_threshold_from_grid(probabilities, labels, thresholds)
        constrained = train.select_threshold_from_grid(
            probabilities,
            labels,
            thresholds,
            max_positive_rate=0.5,
        )

        self.assertEqual(unconstrained, 0.4)
        self.assertEqual(constrained, 0.8)

    def test_select_threshold_from_grid_penalizes_distance_from_target_positive_rate(self) -> None:
        probabilities = np.array([0.95, 0.85, 0.75, 0.65, 0.55, 0.45], dtype=np.float64)
        labels = np.array([0, 0, 0, 0, 0, 1], dtype=np.float32)
        thresholds = np.array([0.40, 0.60], dtype=np.float64)

        unconstrained = train.select_threshold_from_grid(probabilities, labels, thresholds)
        penalized = train.select_threshold_from_grid(
            probabilities,
            labels,
            thresholds,
            target_positive_rate=0.35,
            positive_rate_penalty=1.5,
        )

        self.assertEqual(unconstrained, 0.4)
        self.assertEqual(penalized, 0.6)


if __name__ == "__main__":
    unittest.main()
