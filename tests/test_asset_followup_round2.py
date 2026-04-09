from __future__ import annotations

import unittest

import asset_followup as af
import asset_followup_round2 as afr2


class AssetFollowupRound2Tests(unittest.TestCase):
    def test_build_round2_specs_expands_candidate_features_without_duplicates(self) -> None:
        candidates = [
            af.FollowupCandidate(
                role="headline",
                model_name="ret_60_plus_sma_gap_60_plus_above_200dma_flag",
                feature_names=("ret_1", "ret_3", "ret_60", "sma_gap_60", "above_200dma_flag"),
                headline_score=0.62,
                validation_f1=0.64,
                validation_bal_acc=0.72,
                test_f1=0.54,
                test_bal_acc=0.67,
                test_positive_rate=0.52,
            ),
            af.FollowupCandidate(
                role="operator",
                model_name="sma_gap_60",
                feature_names=("ret_1", "ret_3", "sma_gap_60"),
                headline_score=0.50,
                validation_f1=0.59,
                validation_bal_acc=0.69,
                test_f1=0.39,
                test_bal_acc=0.54,
                test_positive_rate=0.41,
            ),
        ]

        specs = afr2.build_round2_specs(candidates)
        names = [spec.name for spec in specs]

        self.assertIn("ret_60_plus_sma_gap_60_plus_above_200dma_flag_plus_atr_pct_20_plus_neg_weight_1_15", names)
        self.assertIn("ret_60_plus_sma_gap_60_plus_above_200dma_flag_plus_distance_to_252_high_plus_neg_weight_1_15", names)
        self.assertIn("sma_gap_60_plus_above_200dma_flag", names)
        self.assertEqual(len(names), len(set(names)))

    def test_build_round2_specs_marks_neg_weight_for_combo_models(self) -> None:
        candidates = [
            af.FollowupCandidate(
                role="headline",
                model_name="ret_60_plus_sma_gap_60",
                feature_names=("ret_1", "ret_3", "ret_60", "sma_gap_60"),
                headline_score=0.60,
                validation_f1=0.60,
                validation_bal_acc=0.60,
                test_f1=0.60,
                test_bal_acc=0.60,
                test_positive_rate=0.60,
            )
        ]

        specs = afr2.build_round2_specs(candidates)
        combo_specs = [spec for spec in specs if spec.neg_weight is not None]

        self.assertTrue(combo_specs)
        self.assertTrue(any(spec.neg_weight == 1.15 for spec in combo_specs))

    def test_prioritize_round2_specs_keeps_base_and_limits_total(self) -> None:
        candidates = [
            af.FollowupCandidate(
                role="headline",
                model_name="ret_60_plus_sma_gap_60",
                feature_names=("ret_1", "ret_3", "ret_60", "sma_gap_60"),
                headline_score=0.60,
                validation_f1=0.60,
                validation_bal_acc=0.60,
                test_f1=0.60,
                test_bal_acc=0.60,
                test_positive_rate=0.60,
            )
        ]

        specs = afr2.build_round2_specs(candidates)
        chosen = afr2.prioritize_round2_specs(specs, limit=4)

        self.assertEqual(len(chosen), 4)
        self.assertEqual(chosen[0].extra_features, ("ret_60", "sma_gap_60"))
        self.assertTrue(any("atr_pct_20" in spec.extra_features for spec in chosen))

    def test_compute_round2_score_rewards_walkforward_and_operator_quality(self) -> None:
        score = afr2.compute_round2_score(
            headline_score=0.60,
            walkforward_avg_test_bal_acc=0.58,
            operator_avg_return=0.05,
            operator_trade_count=12,
        )

        self.assertGreater(score, 0.60)


if __name__ == "__main__":
    unittest.main()
