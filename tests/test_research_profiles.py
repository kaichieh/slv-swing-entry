from pathlib import Path
import unittest

from research_profiles import ResearchProfile, load_all_research_profiles, load_research_profile


class ResearchProfilesTest(unittest.TestCase):
    def test_load_research_profile_reads_lane_and_thresholds(self):
        profile = load_research_profile("slv")

        self.assertIsInstance(profile, ResearchProfile)
        self.assertEqual(profile.asset_key, "slv")
        self.assertEqual(profile.asset_lane, "macro_defensive_commodity")
        self.assertEqual(profile.validation_policy, "macro_default")
        self.assertEqual(profile.adoption_thresholds["min_trade_count"], 12)

    def test_load_all_research_profiles_covers_every_asset(self):
        profiles = load_all_research_profiles()

        self.assertTrue({"gld", "slv", "qqq", "nvda", "tsla", "spy", "iwm", "tlt", "xle"} <= set(profiles))

    def test_asset_config_exposes_profile_path(self):
        import asset_config as ac

        path = ac.get_research_profile_path("nvda")
        self.assertEqual(path, Path(ac.get_asset_dir("nvda")) / "research_profile.json")


if __name__ == "__main__":
    unittest.main()
