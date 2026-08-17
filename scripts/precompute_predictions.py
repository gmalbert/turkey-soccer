"""Build the strict upcoming-prediction artifact from the shared feature contract."""

from pathlib import Path
import pickle
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pitch_oracle_core import (
    FeatureContract,
    add_weather_features,
    build_prediction_frame,
    build_upcoming_feature_matrix,
)
from config import (  # noqa: E402
    LEAGUE_CONFIG,
    ODDS_VALUE_MIN_EDGE,
    ODDS_VALUE_MIN_EXPECTED_RETURN,
)
from odds_api_io import attach_market_odds, empty_odds_frame  # noqa: E402


def generate() -> Path:
    historical = pd.read_csv(
        ROOT / "data_files" / "combined_historical_data_with_calculations_new.csv",
        sep="\t",
    )
    upcoming = pd.read_csv(ROOT / "data_files" / "upcoming_fixtures.csv")
    if LEAGUE_CONFIG.sources.weather and LEAGUE_CONFIG.stadium_coordinates:
        # Resolve raw fixture team names through the league aliases so names like
        # "Çorum FK" map to their stadium coordinate key ("Corum").
        stadium_map = dict(LEAGUE_CONFIG.team_aliases)
        for team in LEAGUE_CONFIG.stadium_coordinates:
            stadium_map.setdefault(team, team)
        upcoming = add_weather_features(
            upcoming,
            cache_file=f"weather_cache_{LEAGUE_CONFIG.key}.csv",
            stadium_map=stadium_map,
            stadium_coords={
                team: {"lat": coordinates[0], "lon": coordinates[1]}
                for team, coordinates in LEAGUE_CONFIG.stadium_coordinates.items()
            },
            data_dir=ROOT / "data_files",
            timezone=LEAGUE_CONFIG.sources.weather_timezone,
        )
    contract = FeatureContract.load(ROOT / "precomputed" / "preprocessed_data.pkl")
    with (ROOT / "models" / "ensemble_model.pkl").open("rb") as stream:
        model = pickle.load(stream)
    matrix = build_upcoming_feature_matrix(historical, upcoming, contract)
    # Preserve the expected-goal inputs needed by the shared goal-market UI.
    for feature in ("HomeGoalsAve", "AwayGoalsAve", "HomexG_Avg_L5", "AwayxG_Avg_L5"):
        if feature in contract.feature_names:
            upcoming[feature] = matrix[:, contract.feature_names.index(feature)]
    predictions = build_prediction_frame(upcoming, model.predict_proba(matrix))
    odds_path = ROOT / "data_files" / "odds.csv"
    odds = pd.read_csv(odds_path) if odds_path.is_file() else empty_odds_frame()
    predictions = attach_market_odds(
        predictions,
        odds,
        min_edge=ODDS_VALUE_MIN_EDGE,
        min_expected_return=ODDS_VALUE_MIN_EXPECTED_RETURN,
    )
    output = ROOT / "data_files" / "upcoming_predictions.csv"
    predictions.to_csv(output, index=False)
    return output


if __name__ == "__main__":
    print(f"Wrote {generate()}")
