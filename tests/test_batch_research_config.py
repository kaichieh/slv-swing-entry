from __future__ import annotations

import unittest

import asset_config as ac
import batch_research_config as brc


class BatchResearchConfigTests(unittest.TestCase):
    def test_load_default_universe_config_reads_100_candidates(self) -> None:
        config = brc.load_batch_research_config()

        self.assertEqual(config.name, "cross_asset_100")
        self.assertEqual(config.template_asset_key, "tsla")
        self.assertEqual(len(config.candidates), 100)
        self.assertEqual(config.candidates[0].symbol, "SPY")
        self.assertEqual(config.candidates[-1].symbol, "BITB")

    def test_render_task_markdown_includes_template_and_first_round_targets(self) -> None:
        config = brc.load_batch_research_config()

        text = brc.render_task_markdown(config, round_size=12)

        self.assertIn("# Cross-Asset Batch Research", text)
        self.assertIn("Template asset folder: `assets/tsla`", text)
        self.assertIn("First round target count: `12`", text)
        self.assertIn("- [ ] `SPY`", text)
        self.assertIn("- [ ] `TSLA`", text)
        self.assertIn("- [ ] `BITB`", text)

    def test_first_round_assets_are_supported_by_asset_config(self) -> None:
        config = brc.load_batch_research_config()
        first_round = brc.get_round_candidates(config)

        self.assertEqual(len(first_round), 20)
        self.assertIn("dia", ac.ASSET_DEFAULTS)
        self.assertIn("xlre", ac.ASSET_DEFAULTS)
        self.assertEqual(first_round[0].asset_key, "spy")
        self.assertEqual(first_round[-1].asset_key, "xlre")

    def test_second_round_assets_are_supported_by_asset_config(self) -> None:
        config = brc.load_batch_research_config()
        second_round = config.candidates[20:40]

        self.assertEqual(len(second_round), 20)
        self.assertIn("smh", ac.ASSET_DEFAULTS)
        self.assertIn("fxb", ac.ASSET_DEFAULTS)
        self.assertEqual(second_round[0].asset_key, "smh")
        self.assertEqual(second_round[-1].asset_key, "fxb")


if __name__ == "__main__":
    unittest.main()
