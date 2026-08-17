"""Strict league-neutral artifact and chronological model-quality gate."""

from __future__ import annotations

import math
from pathlib import Path
import pickle
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import LEAGUE_CONFIG
from pitch_oracle_core import FeatureContract, __version__
from pitch_oracle_core.cache import validate_cache


def main() -> None:
    validate_cache(ROOT, expected_league=LEAGUE_CONFIG.key)
    contract = FeatureContract.load(ROOT / "precomputed" / "preprocessed_data.pkl")
    with (ROOT / "models" / "ensemble_model.pkl").open("rb") as stream:
        ensemble = pickle.load(stream)
    width = getattr(ensemble, "n_features_in_", None)
    if width is not None and width != len(contract.feature_names):
        raise SystemExit(
            f"Ensemble width {width} does not match contract width "
            f"{len(contract.feature_names)}"
        )

    with (ROOT / "models" / "model_performance.pkl").open("rb") as stream:
        performance = pickle.load(stream)
    required = {"class_prior_baseline", "xgb_baseline", "ensemble", "optimized_xgb", "poisson"}
    missing = required.difference(performance)
    if missing:
        raise SystemExit(f"Missing model metrics: {sorted(missing)}")
    for name in ("xgb_baseline", "ensemble", "optimized_xgb"):
        accuracy = float(performance[name]["accuracy"])
        log_loss = float(performance[name]["log_loss"])
        if not (0.0 <= accuracy <= 1.0 and math.isfinite(log_loss) and log_loss < 2.0):
            raise SystemExit(f"Implausible chronological metrics for {name}: {performance[name]}")
    production = performance["ensemble"]
    baseline = performance["class_prior_baseline"]
    if (
        float(production["log_loss"]) >= float(baseline["log_loss"])
        or float(production["brier_score"]) >= float(baseline["brier_score"])
    ):
        raise SystemExit(
            "Production no-odds model does not beat the class-prior baseline "
            "on log loss and Brier score"
        )
    poisson_accuracy = float(performance["poisson"]["outcome_acc"])
    if not 0.0 <= poisson_accuracy <= 1.0:
        raise SystemExit(f"Invalid Poisson outcome accuracy: {poisson_accuracy}")

    odds_path = ROOT / "data_files" / "odds.csv"
    if not odds_path.is_file():
        raise SystemExit("Missing server-side odds cache: data_files/odds.csv")
    odds = pd.read_csv(odds_path)
    required_odds_columns = {
        "Date", "Time", "HomeTeam", "AwayTeam", "Bookmaker",
        "OddsHome", "OddsDraw", "OddsAway", "MarketHomeProb",
        "MarketDrawProb", "MarketAwayProb", "MarketMargin", "OddsProvider",
    }
    missing_odds = required_odds_columns.difference(odds.columns)
    if missing_odds:
        raise SystemExit(f"Odds cache is missing columns: {sorted(missing_odds)}")
    if not odds.empty:
        prices = odds[["OddsHome", "OddsDraw", "OddsAway"]].apply(pd.to_numeric, errors="coerce")
        probabilities = odds[["MarketHomeProb", "MarketDrawProb", "MarketAwayProb"]].apply(
            pd.to_numeric,
            errors="coerce",
        )
        if prices.isna().any().any() or not (prices > 1.0).all().all():
            raise SystemExit("Odds cache contains incomplete or invalid decimal prices")
        if probabilities.isna().any().any() or not probabilities.sum(axis=1).between(0.999, 1.001).all():
            raise SystemExit("No-vig market probabilities do not sum to one")

    predictions = pd.read_csv(ROOT / "data_files" / "upcoming_predictions.csv")
    required_market_columns = {
        "OddsMatched", "BestValueOutcome", "BestValueEdge",
        "BestValueExpectedReturn", "BetRecommendation", "BetReason",
    }
    missing_market = required_market_columns.difference(predictions.columns)
    if missing_market:
        raise SystemExit(f"Prediction cache is missing market columns: {sorted(missing_market)}")

    print(f"{LEAGUE_CONFIG.display_name} artifacts verified with core {__version__}")
    print(f"Feature contract width: {len(contract.feature_names)}")
    print(f"Complete bookmaker lines: {len(odds)}")


if __name__ == "__main__":
    main()
