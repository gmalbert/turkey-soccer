"""Turkey-owned bookmaker extension for the shared Predictions page."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from pitch_oracle_core.ui_pages import render_predictions as render_core_predictions


ROOT = Path(__file__).resolve().parent


def _format_market_table(predictions: pd.DataFrame) -> pd.DataFrame:
    columns = (
        "Date",
        "Time",
        "HomeTeam",
        "AwayTeam",
        "Bookmaker",
        "OddsHome",
        "OddsDraw",
        "OddsAway",
        "MarketHomeProb",
        "MarketDrawProb",
        "MarketAwayProb",
        "BestValueEdge",
        "BestValueExpectedReturn",
        "BetRecommendation",
    )
    display = predictions.loc[predictions["OddsMatched"].fillna(False), list(columns)].copy()
    display = display.rename(
        columns={
            "HomeTeam": "Home",
            "AwayTeam": "Away",
            "OddsHome": "Home odds",
            "OddsDraw": "Draw odds",
            "OddsAway": "Away odds",
            "MarketHomeProb": "Market home",
            "MarketDrawProb": "Market draw",
            "MarketAwayProb": "Market away",
            "BestValueEdge": "Best model edge",
            "BestValueExpectedReturn": "Expected return",
            "BetRecommendation": "Value assessment",
        }
    )
    for column in ("Home odds", "Draw odds", "Away odds"):
        display[column] = pd.to_numeric(display[column], errors="coerce").map(
            lambda value: f"{value:.2f}" if pd.notna(value) else "—"
        )
    for column in ("Market home", "Market draw", "Market away", "Best model edge", "Expected return"):
        display[column] = pd.to_numeric(display[column], errors="coerce").map(
            lambda value: f"{value:.1%}" if pd.notna(value) else "—"
        )
    return display


def _refresh_caches() -> tuple[str, int]:
    """Refetch server-side odds and regenerate the prediction cache."""
    from scripts.fetch_live_odds import fetch as fetch_odds
    from scripts.precompute_predictions import generate as generate_predictions

    odds_path = fetch_odds()
    predictions_path = generate_predictions()
    predictions = pd.read_csv(predictions_path)
    matched = int(predictions["OddsMatched"].fillna(False).sum())
    return str(odds_path), matched


def render_predictions_with_market(config) -> None:
    """Render the shared page, then its cached model-versus-market section."""
    render_core_predictions(config)
    st.subheader("Bookmaker market")
    st.caption(
        "Server-cached Odds-API.io 1X2 prices. Market probabilities remove the selected "
        "bookmaker's margin; the prediction model itself does not use bookmaker odds."
    )
    with st.expander("Refresh odds and predictions", expanded=False):
        if st.button("Fetch latest Odds-API.io prices", type="secondary"):
            with st.spinner("Fetching live odds and rebuilding predictions…"):
                try:
                    odds_path, matched = _refresh_caches()
                except Exception as exc:  # network or provider failure must not crash the page
                    st.error(f"Odds refresh failed: {exc}")
                else:
                    st.success(
                        f"Fetched {odds_path.name}; {matched} fixture(s) now have a matched line."
                    )
                    st.rerun()
    cache_path = ROOT / "data_files" / "upcoming_predictions.csv"
    if not cache_path.is_file():
        st.info("Bookmaker comparisons will appear after the prediction cache is built.")
        return
    predictions = pd.read_csv(cache_path)
    if "OddsMatched" not in predictions.columns:
        st.info("Bookmaker comparisons will appear after the odds-enabled pipeline runs.")
        return
    display = _format_market_table(predictions)
    if display.empty:
        st.info(
            "No current Bet365 or Unibet 1X2 line matched these fixtures. "
            "Configure ODDS_API_IO_KEY and rerun the artifact pipeline."
        )
        return
    st.dataframe(display, hide_index=True, width="stretch")
    st.caption(
        "A value assessment appears only when both the model edge and expected-return gates clear. "
        "Odds can move; confirm the current line before acting."
    )
