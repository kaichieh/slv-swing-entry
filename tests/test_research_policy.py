import unittest

from research_policy import GateDecision, evaluate_policy


class ResearchPolicyTest(unittest.TestCase):
    def test_policy_marks_viability_warning_when_walkforward_is_weak(self):
        metrics = {
            "rows": 4600,
            "positive_rate": 0.39,
            "baseline_score": 0.55,
            "walkforward_median_bal_acc": 0.49,
            "recent_consistency": 0.58,
            "trade_count": 18,
            "max_drawdown_pct": 0.08,
        }

        decision = evaluate_policy("macro_default", metrics)

        self.assertIsInstance(decision, GateDecision)
        self.assertEqual(decision.viability, "viable_with_caution")
        self.assertEqual(decision.improvement, "research_only_improvement")
        self.assertEqual(decision.adoption, "keep_as_research_primary")

    def test_policy_rejects_degenerate_momentum_candidate(self):
        metrics = {
            "rows": 3000,
            "positive_rate": 0.98,
            "baseline_score": 0.57,
            "walkforward_median_bal_acc": 0.50,
            "recent_consistency": 0.62,
            "trade_count": 4,
            "max_drawdown_pct": 0.19,
        }

        decision = evaluate_policy("momentum_default", metrics)

        self.assertEqual(decision.viability, "not_viable")
        self.assertEqual(decision.adoption, "archive_reference_only")


if __name__ == "__main__":
    unittest.main()
