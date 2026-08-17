"""Fetch the server-side Odds-API.io cache used by predictions and best bets."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import sys

import pandas as pd
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import (  # noqa: E402
    LEAGUE_CONFIG,
    ODDS_API_IO_BOOKMAKERS,
    ODDS_API_IO_LEAGUE_SLUG,
)
from odds_api_io import OddsApiIoClient  # noqa: E402


def fetch(output: str | Path | None = None) -> Path:
    load_dotenv(ROOT / ".env", override=False)
    output_path = Path(output) if output is not None else ROOT / "data_files" / "odds.csv"
    fixtures_path = ROOT / "data_files" / "upcoming_fixtures.csv"
    start = datetime.now(timezone.utc)
    end = start + timedelta(days=60)
    if fixtures_path.is_file():
        fixtures = pd.read_csv(fixtures_path)
        dates = pd.to_datetime(fixtures.get("Date"), errors="coerce", utc=True).dropna()
        if not dates.empty:
            end = max(end, dates.max().to_pydatetime() + timedelta(days=1))
    client = OddsApiIoClient(
        api_key=os.getenv("ODDS_API_IO_KEY") or os.getenv("ODDS_API_KEY"),
        league_slug=ODDS_API_IO_LEAGUE_SLUG,
        bookmakers=ODDS_API_IO_BOOKMAKERS,
        team_aliases=LEAGUE_CONFIG.team_aliases,
    )
    odds = client.fetch(start=start, end=end)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    odds.to_csv(output_path, index=False)
    if client.last_error:
        print(f"Live odds unavailable: {client.last_error}")
    else:
        print(f"Fetched {len(odds)} complete 1X2 lines from Odds-API.io")
    return output_path


if __name__ == "__main__":
    print(f"Wrote {fetch()}")
