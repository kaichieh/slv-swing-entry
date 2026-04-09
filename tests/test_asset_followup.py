from __future__ import annotations

import unittest

import asset_followup as af


class AssetFollowupTests(unittest.TestCase):
    def test_candidate_selection_prefers_viable_non_degenerate_models(self) -> None:
        models = {
            "all_positive": {
                "name": "all_positive",
                "feature_names": ["ret_1", "ret_3", "ret_60"],
                "validation_f1": 0.70,
                "validation_bal_acc": 0.50,
                "test_f1": 0.75,
                "test_bal_acc": 0.50,
                "test_positive_rate": 0.999,
            },
            "balanced_leader": {
                "name": "balanced_leader",
                "feature_names": ["ret_1", "ret_3", "ret_60", "above_200dma_flag"],
                "validation_f1": 0.58,
                "validation_bal_acc": 0.62,
                "test_f1": 0.56,
                "test_bal_acc": 0.64,
                "test_positive_rate": 0.44,
            },
            "headline_leader": {
                "name": "headline_leader",
                "feature_names": ["ret_1", "ret_3", "ret_60", "sma_gap_60"],
                "validation_f1": 0.62,
                "validation_bal_acc": 0.59,
                "test_f1": 0.60,
                "test_bal_acc": 0.61,
                "test_positive_rate": 0.58,
            },
        }
        backtests = [
            {
                "model_name": "headline_leader",
                "rule_name": "top_15pct",
                "selected_count": 8,
                "hit_rate": 0.75,
                "avg_return": 0.04,
            },
            {
                "model_name": "balanced_leader",
                "rule_name": "top_12_5pct",
                "selected_count": 11,
                "hit_rate": 0.82,
                "avg_return": 0.06,
            },
        ]

        chosen = af.select_followup_candidates(models, backtests, top_n=3)

        self.assertEqual([row.role for row in chosen], ["headline", "balance", "operator"])
        self.assertEqual(chosen[0].model_name, "headline_leader")
        self.assertEqual(chosen[1].model_name, "balanced_leader")
        self.assertEqual(chosen[2].model_name, "balanced_leader")
        self.assertNotIn("all_positive", [row.model_name for row in chosen])

    def test_candidate_selection_falls_back_when_only_degenerate_models_exist(self) -> None:
        models = {
            "degenerate": {
                "name": "degenerate",
                "feature_names": ["ret_1", "ret_3", "ret_60"],
                "validation_f1": 0.55,
                "validation_bal_acc": 0.50,
                "test_f1": 0.60,
                "test_bal_acc": 0.50,
                "test_positive_rate": 0.999,
            }
        }

        chosen = af.select_followup_candidates(models, backtests=[], top_n=3)

        self.assertEqual(len(chosen), 1)
        self.assertEqual(chosen[0].model_name, "degenerate")
        self.assertEqual(chosen[0].role, "headline")


if __name__ == "__main__":
    unittest.main()
