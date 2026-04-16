from __future__ import annotations

import unittest
from unittest import mock

import numpy as np
import pandas as pd

import research_gld_topbottom10_hard_gate_two_expert_mixed_vix_term_overlay as term_overlay


class GldVixTermOverlayResearchTests(unittest.TestCase):
    def test_build_term_overlay_mask_blocks_recent_extreme_term_panic(self) -> None:
        frame = pd.DataFrame({"vix_vxv_ratio_pct_63": [0.20, 0.96, 0.94, 0.60]})
        base_selected = np.array([True, True, True, True])

        selected = term_overlay.build_term_overlay_mask(frame, base_selected)

        np.testing.assert_array_equal(selected, np.array([True, True, False, False]))

    def test_build_research_frame_adds_vix_and_vix3m_features(self) -> None:
        raw = pd.DataFrame(
            {
                "date": pd.date_range("2020-01-01", periods=4, freq="D"),
                term_overlay.pr.TARGET_COLUMN: [0.0, 1.0, 0.0, 1.0],
                term_overlay.rb.FUTURE_RETURN_COLUMN: [0.01, 0.02, -0.01, 0.03],
            }
        )
        with_vix = raw.assign(vix_close_lag1=[20.0, 21.0, 22.0, 23.0])
        with_term = with_vix.assign(vix_vxv_ratio_pct_63=[0.3, 0.4, 0.5, 0.6])

        with mock.patch.object(term_overlay.pr, "download_symbol_prices", return_value=raw):
            with mock.patch.object(term_overlay.rb, "build_labeled_frame", return_value=raw):
                with mock.patch.object(term_overlay.pr, "download_vix_prices", return_value=pd.DataFrame({"date": [], "close": []})) as download_vix_prices:
                    with mock.patch.object(term_overlay.pr, "add_vix_features", return_value=with_vix) as add_vix_features:
                        with mock.patch.object(term_overlay.pr, "download_vix3m_prices", return_value=pd.DataFrame({"date": [], "close": []})) as download_vix3m_prices:
                            with mock.patch.object(term_overlay.pr, "add_vix_term_structure_features", return_value=with_term) as add_vix_term_structure_features:
                                enriched = term_overlay.build_research_frame()

        download_vix_prices.assert_called_once_with()
        add_vix_features.assert_called_once_with(raw, download_vix_prices.return_value)
        download_vix3m_prices.assert_called_once_with()
        add_vix_term_structure_features.assert_called_once_with(with_vix, download_vix3m_prices.return_value)
        pd.testing.assert_frame_equal(enriched, with_term)


if __name__ == "__main__":
    unittest.main()
