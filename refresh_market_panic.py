from __future__ import annotations

import json

import pandas as pd

import asset_config as ac
from prepare import download_symbol_prices, download_vix3m_prices, download_vix_prices


def load_market_prices(symbol: str, cache_name: str) -> pd.DataFrame:
    cache_path = ac.REPO_DIR / ".cache" / cache_name
    frame = download_symbol_prices(symbol, ac.stooq_url(symbol), str(cache_path))
    return frame.sort_values("date").reset_index(drop=True)


def rolling_percentile(series: pd.Series, window: int = 252) -> pd.Series:
    return series.rolling(window).rank(pct=True)


def zscore(series: pd.Series, window: int = 20) -> pd.Series:
    return (series - series.rolling(window).mean()) / (series.rolling(window).std(ddof=0) + 1e-10)


def latest_non_na(series: pd.Series) -> float:
    cleaned = series.dropna()
    if cleaned.empty:
        return float("nan")
    return float(cleaned.iloc[-1])


def classify_vix_state(vix_level: float, vix_percentile_252: float) -> str:
    if vix_level >= 35.0 or vix_percentile_252 >= 0.95:
        return "panic"
    if vix_level >= 25.0 or vix_percentile_252 >= 0.80:
        return "elevated"
    if vix_level <= 18.0 and vix_percentile_252 <= 0.35:
        return "calm"
    return "normal"


def classify_term_state(vix_vix3m_ratio: float) -> str:
    if vix_vix3m_ratio >= 1.05:
        return "backwardation"
    if vix_vix3m_ratio >= 1.00:
        return "flattening"
    if vix_vix3m_ratio <= 0.90:
        return "calm_contango"
    return "normal_contango"


def classify_credit_state(credit_ratio_z20: float, credit_ratio_ret_5: float) -> str:
    if credit_ratio_z20 <= -1.0 or credit_ratio_ret_5 <= -0.02:
        return "risk_off"
    if credit_ratio_z20 <= -0.5 or credit_ratio_ret_5 <= -0.01:
        return "cautious"
    if credit_ratio_z20 >= 0.5 and credit_ratio_ret_5 >= 0.0:
        return "supportive"
    return "neutral"


def panic_component_score(vix_state: str, term_state: str, credit_state: str) -> int:
    score = 0
    score += {"calm": 0, "normal": 0, "elevated": 1, "panic": 2}.get(vix_state, 0)
    score += {"calm_contango": 0, "normal_contango": 0, "flattening": 1, "backwardation": 2}.get(term_state, 0)
    score += {"supportive": 0, "neutral": 0, "cautious": 1, "risk_off": 2}.get(credit_state, 0)
    return min(score, 3)


def classify_panic_regime(score: int) -> str:
    if score >= 3:
        return "panic"
    if score == 2:
        return "stressed"
    if score == 1:
        return "guarded"
    return "calm"


def panic_summary_zh(vix_state: str, term_state: str, credit_state: str) -> str:
    parts: list[str] = []
    if vix_state == "panic":
        parts.append("VIX 偏高")
    elif vix_state == "elevated":
        parts.append("VIX 升溫")
    elif vix_state == "calm":
        parts.append("VIX 平靜")

    if term_state == "backwardation":
        parts.append("短端倒掛")
    elif term_state == "flattening":
        parts.append("期限結構轉平")
    elif term_state == "calm_contango":
        parts.append("期限結構平穩")

    if credit_state == "risk_off":
        parts.append("信用偏避險")
    elif credit_state == "cautious":
        parts.append("信用轉弱")
    elif credit_state == "supportive":
        parts.append("信用偏撐盤")

    return "／".join(parts) if parts else "風險訊號中性"


def build_market_panic() -> dict[str, object]:
    vix = download_vix_prices().rename(columns={"close": "vix_close"})
    vix3m = download_vix3m_prices().rename(columns={"close": "vix3m_close"})
    hyg = load_market_prices("HYG", "market_panic_hyg.csv")[["date", "close"]].rename(columns={"close": "hyg_close"})
    ief = load_market_prices("IEF", "market_panic_ief.csv")[["date", "close"]].rename(columns={"close": "ief_close"})

    merged = pd.merge_asof(vix.sort_values("date"), vix3m.sort_values("date"), on="date", direction="backward")
    merged = pd.merge_asof(merged, hyg.sort_values("date"), on="date", direction="backward")
    merged = pd.merge_asof(merged, ief.sort_values("date"), on="date", direction="backward")
    merged = merged.dropna(subset=["vix_close", "vix3m_close", "hyg_close", "ief_close"]).reset_index(drop=True)
    if merged.empty:
        raise RuntimeError("Unable to build market panic overlay because proxy series are empty.")

    merged["vix_percentile_252"] = rolling_percentile(merged["vix_close"], 252)
    merged["vix_vix3m_ratio"] = merged["vix_close"] / (merged["vix3m_close"] + 1e-10)
    merged["credit_ratio"] = merged["hyg_close"] / (merged["ief_close"] + 1e-10)
    merged["credit_ratio_z20"] = zscore(merged["credit_ratio"], 20)
    merged["credit_ratio_ret_5"] = merged["credit_ratio"].pct_change(5)

    latest = merged.iloc[-1]
    vix_level = float(latest["vix_close"])
    vix3m_level = float(latest["vix3m_close"])
    vix_percentile_252 = latest_non_na(merged["vix_percentile_252"])
    term_ratio = float(latest["vix_vix3m_ratio"])
    credit_ratio = float(latest["credit_ratio"])
    credit_ratio_z20 = latest_non_na(merged["credit_ratio_z20"])
    credit_ratio_ret_5 = latest_non_na(merged["credit_ratio_ret_5"])

    vix_state = classify_vix_state(vix_level, vix_percentile_252)
    term_state = classify_term_state(term_ratio)
    credit_state = classify_credit_state(credit_ratio_z20, credit_ratio_ret_5)
    panic_score = panic_component_score(vix_state, term_state, credit_state)
    regime = classify_panic_regime(panic_score)

    return {
        "date": str(pd.Timestamp(latest["date"]).date()),
        "panic_score": panic_score,
        "panic_regime": regime,
        "panic_summary_zh": panic_summary_zh(vix_state, term_state, credit_state),
        "vix_state": vix_state,
        "term_state": term_state,
        "credit_state": credit_state,
        "metrics": {
            "vix_close": round(vix_level, 2),
            "vix3m_close": round(vix3m_level, 2),
            "vix_percentile_252": round(vix_percentile_252, 4),
            "vix_vix3m_ratio": round(term_ratio, 4),
            "credit_ratio": round(credit_ratio, 4),
            "credit_ratio_z20": round(credit_ratio_z20, 4),
            "credit_ratio_ret_5": round(credit_ratio_ret_5, 4),
        },
    }


def main() -> None:
    payload = build_market_panic()
    output_path = ac.get_market_panic_path()
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"output_path": str(output_path), **payload}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
