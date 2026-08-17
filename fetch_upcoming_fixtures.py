"""Fetch Süper Lig fixtures using the consumer-owned league configuration."""

from __future__ import annotations

from datetime import datetime, timedelta
import os
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from config import LEAGUE_CONFIG
from team_name_mapping import normalize_team_name


def fetch_upcoming_fixtures(
    days_ahead: int = 60,
    output_dir: str | Path | None = None,
) -> pd.DataFrame:
    """Fetch upcoming league fixtures from ESPN and persist the standard CSV."""
    now = datetime.now().astimezone()
    date_range = f"{now:%Y%m%d}-{(now + timedelta(days=days_ahead)):%Y%m%d}"
    url = (
        "https://site.api.espn.com/apis/site/v2/sports/soccer/"
        f"{LEAGUE_CONFIG.espn_slug}/scoreboard?dates={date_range}"
    )
    response = requests.get(url, timeout=15)
    response.raise_for_status()

    rows: list[dict[str, str]] = []
    for event in response.json().get("events", []):
        competition = (event.get("competitions") or [{}])[0]
        teams = {
            competitor.get("homeAway"): competitor.get("team", {}).get(
                "displayName", ""
            )
            for competitor in competition.get("competitors", [])
        }
        status = event.get("status", {}).get("type", {}).get("name", "")
        if (
            status in {"STATUS_FINAL", "STATUS_FULL_TIME"}
            or not teams.get("home")
            or not teams.get("away")
        ):
            continue
        kickoff = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
        kickoff = kickoff.astimezone(ZoneInfo("US/Eastern"))
        rows.append(
            {
                "Date": kickoff.strftime("%Y-%m-%d"),
                "Time": kickoff.strftime("%H:%M"),
                "HomeTeam": normalize_team_name(
                    teams["home"], LEAGUE_CONFIG.team_aliases
                ),
                "AwayTeam": normalize_team_name(
                    teams["away"], LEAGUE_CONFIG.team_aliases
                ),
                "Status": status,
            }
        )

    result = pd.DataFrame(
        rows,
        columns=["Date", "Time", "HomeTeam", "AwayTeam", "Status"],
    )
    active_output = output_dir or os.getenv(
        "PITCH_ORACLE_DATA_DIR", LEAGUE_CONFIG.data_dir_name
    )
    destination = Path(active_output)
    destination.mkdir(parents=True, exist_ok=True)
    result.to_csv(destination / "upcoming_fixtures.csv", index=False)
    return result


if __name__ == "__main__":
    fetch_upcoming_fixtures()
