"""Odds-API.io adapter and model-versus-market comparison helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
import math
import re
from typing import Any, Mapping
import unicodedata

import pandas as pd
import requests

from team_name_mapping import normalize_team_name


BASE_URL = "https://api.odds-api.io/v3"
ODDS_COLUMNS = (
    "Date",
    "Time",
    "HomeTeam",
    "AwayTeam",
    "OddsEventId",
    "Bookmaker",
    "OddsHome",
    "OddsDraw",
    "OddsAway",
    "MarketHomeProb",
    "MarketDrawProb",
    "MarketAwayProb",
    "MarketMargin",
    "OddsUpdatedAt",
    "OddsProvider",
)
MARKET_RESULT_COLUMNS = (
    "HomeValueEdge",
    "DrawValueEdge",
    "AwayValueEdge",
    "BestValueOutcome",
    "BestValueEdge",
    "BestValueExpectedReturn",
    "OddsMatched",
)
_STRING_ODDS_COLUMNS = {
    "Date",
    "Time",
    "HomeTeam",
    "AwayTeam",
    "OddsEventId",
    "Bookmaker",
    "OddsUpdatedAt",
    "OddsProvider",
    "BestValueOutcome",
}


def empty_odds_frame() -> pd.DataFrame:
    """Return an empty frame with a stable artifact schema."""
    return pd.DataFrame(columns=ODDS_COLUMNS)


def _decimal(value: object) -> float | None:
    try:
        decimal = float(value)
    except (TypeError, ValueError):
        return None
    return decimal if math.isfinite(decimal) and decimal > 1.0 else None


def _rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _event_local_datetime(value: object) -> pd.Timestamp | None:
    timestamp = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(timestamp):
        return None
    return timestamp.tz_convert("US/Eastern")


def _select_moneyline(
    payload: Mapping[str, Any],
    bookmakers: tuple[str, ...],
) -> tuple[str, Mapping[str, Any], str | None] | None:
    available = payload.get("bookmakers")
    if not isinstance(available, Mapping):
        return None
    names = {str(name).casefold(): str(name) for name in available}
    for requested in bookmakers:
        actual = names.get(requested.casefold())
        markets = available.get(actual) if actual is not None else None
        if not isinstance(markets, list):
            continue
        for market in markets:
            if not isinstance(market, Mapping) or str(market.get("name", "")).casefold() != "ml":
                continue
            prices = market.get("odds")
            if not isinstance(prices, list):
                continue
            for price in prices:
                if not isinstance(price, Mapping):
                    continue
                if all(_decimal(price.get(outcome)) is not None for outcome in ("home", "draw", "away")):
                    return actual, price, market.get("updatedAt")
    return None


class OddsApiIoClient:
    """Fetch pending football events and complete 1X2 lines from Odds-API.io."""

    def __init__(
        self,
        *,
        api_key: str | None,
        league_slug: str,
        bookmakers: tuple[str, ...],
        team_aliases: Mapping[str, str] | None = None,
        session: Any = requests,
        timeout: float = 20.0,
        base_url: str = BASE_URL,
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.league_slug = league_slug
        self.bookmakers = bookmakers
        self.team_aliases = team_aliases or {}
        self.session = session
        self.timeout = timeout
        self.base_url = base_url.rstrip("/")
        self.last_error: str | None = None

    def _get(self, endpoint: str, params: Mapping[str, object]) -> Any:
        response = self.session.get(
            f"{self.base_url}{endpoint}",
            params={**params, "apiKey": self.api_key},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, Mapping) and payload.get("error"):
            raise ValueError(str(payload["error"]))
        return payload

    def fetch(
        self,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> pd.DataFrame:
        """Return selected bookmaker 1X2 prices, or an empty frame on failure."""
        if not self.api_key:
            self.last_error = "ODDS_API_IO_KEY is not configured"
            return empty_odds_frame()
        start = start or datetime.now(timezone.utc)
        end = end or start + timedelta(days=60)
        try:
            events = self._get(
                "/events",
                {
                    "sport": "football",
                    "league": self.league_slug,
                    "status": "pending",
                    "from": _rfc3339(start),
                    "to": _rfc3339(end),
                    "limit": 500,
                },
            )
            if not isinstance(events, list):
                raise ValueError("Odds-API.io events response is not a list")
            event_ids = [str(event["id"]) for event in events if isinstance(event, Mapping) and event.get("id") is not None]
            odds_payloads: list[Mapping[str, Any]] = []
            for offset in range(0, len(event_ids), 10):
                batch = self._get(
                    "/odds/multi",
                    {
                        "eventIds": ",".join(event_ids[offset : offset + 10]),
                        "bookmakers": ",".join(self.bookmakers),
                    },
                )
                if isinstance(batch, Mapping):
                    batch = [batch]
                if not isinstance(batch, list):
                    raise ValueError("Odds-API.io multi-odds response is not a list")
                odds_payloads.extend(item for item in batch if isinstance(item, Mapping))
        except (requests.RequestException, KeyError, TypeError, ValueError) as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            return empty_odds_frame()

        rows: list[dict[str, object]] = []
        for payload in odds_payloads:
            selected = _select_moneyline(payload, self.bookmakers)
            kickoff = _event_local_datetime(payload.get("date"))
            if selected is None or kickoff is None:
                continue
            bookmaker, prices, updated_at = selected
            decimals = tuple(_decimal(prices.get(name)) for name in ("home", "draw", "away"))
            if any(value is None for value in decimals):
                continue
            home_odds, draw_odds, away_odds = (float(value) for value in decimals)
            implied = [1.0 / home_odds, 1.0 / draw_odds, 1.0 / away_odds]
            overround = sum(implied)
            rows.append(
                {
                    "Date": kickoff.strftime("%Y-%m-%d"),
                    "Time": kickoff.strftime("%H:%M"),
                    "HomeTeam": normalize_team_name(str(payload.get("home", "")), self.team_aliases),
                    "AwayTeam": normalize_team_name(str(payload.get("away", "")), self.team_aliases),
                    "OddsEventId": str(payload.get("id", "")),
                    "Bookmaker": bookmaker,
                    "OddsHome": home_odds,
                    "OddsDraw": draw_odds,
                    "OddsAway": away_odds,
                    "MarketHomeProb": implied[0] / overround,
                    "MarketDrawProb": implied[1] / overround,
                    "MarketAwayProb": implied[2] / overround,
                    "MarketMargin": overround - 1.0,
                    "OddsUpdatedAt": updated_at or payload.get("date"),
                    "OddsProvider": "Odds-API.io",
                }
            )
        if not rows:
            return empty_odds_frame()
        return (
            pd.DataFrame(rows, columns=ODDS_COLUMNS)
            .drop_duplicates(["Date", "HomeTeam", "AwayTeam"], keep="first")
            .sort_values(["Date", "Time", "HomeTeam"], kind="stable")
            .reset_index(drop=True)
        )


def _team_key(value: object) -> str:
    text = str(value).casefold().translate(str.maketrans("ıİşŞğĞçÇöÖüÜ", "iissggccoouu"))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    tokens = re.findall(r"[a-z0-9]+", text)
    ignored = {"fc", "fk", "sk", "sfk", "as", "club", "kulubu", "bb"}
    normalized = []
    for token in tokens:
        if token in ignored:
            continue
        normalized.append(token[:-4] if token.endswith("spor") and len(token) > 5 else token)
    return "".join(normalized)


def _team_similarity(left: object, right: object) -> float:
    left_key, right_key = _team_key(left), _team_key(right)
    if not left_key or not right_key:
        return 0.0
    return 1.0 if left_key == right_key else SequenceMatcher(None, left_key, right_key).ratio()


def _match_odds_row(fixture: pd.Series, odds: pd.DataFrame) -> pd.Series | None:
    fixture_date = pd.to_datetime(fixture.get("Date"), errors="coerce")
    if pd.isna(fixture_date):
        return None
    odds_dates = pd.to_datetime(odds.get("Date"), errors="coerce")
    candidates = odds.loc[(odds_dates - fixture_date).abs() <= pd.Timedelta(days=1)]
    best: tuple[float, pd.Series] | None = None
    for _, candidate in candidates.iterrows():
        home_score = _team_similarity(fixture.get("HomeTeam"), candidate.get("HomeTeam"))
        away_score = _team_similarity(fixture.get("AwayTeam"), candidate.get("AwayTeam"))
        if home_score < 0.72 or away_score < 0.72:
            continue
        score = (home_score + away_score) / 2
        if best is None or score > best[0]:
            best = score, candidate
    return None if best is None else best[1]


def attach_market_odds(
    predictions: pd.DataFrame,
    odds: pd.DataFrame,
    *,
    min_edge: float = 0.05,
    min_expected_return: float = 0.03,
) -> pd.DataFrame:
    """Attach cached prices and cautious value guidance to model predictions."""
    result = predictions.copy()
    for column in ODDS_COLUMNS:
        if column in {"Date", "Time", "HomeTeam", "AwayTeam"}:
            continue
        result[column] = pd.NA if column in _STRING_ODDS_COLUMNS else float("nan")
    for column in MARKET_RESULT_COLUMNS:
        if column == "OddsMatched":
            result[column] = False
        elif column == "BestValueOutcome":
            result[column] = pd.NA
        else:
            result[column] = float("nan")
    if odds.empty:
        return result

    copy_columns = [column for column in ODDS_COLUMNS if column not in {"Date", "Time", "HomeTeam", "AwayTeam"}]
    model_columns = ("HomeWin_Prob", "Draw_Prob", "AwayWin_Prob")
    market_columns = ("MarketHomeProb", "MarketDrawProb", "MarketAwayProb")
    odds_columns = ("OddsHome", "OddsDraw", "OddsAway")
    edge_columns = ("HomeValueEdge", "DrawValueEdge", "AwayValueEdge")
    outcome_names = ("Home Win", "Draw", "Away Win")
    for index, fixture in result.iterrows():
        market = _match_odds_row(fixture, odds)
        if market is None:
            continue
        for column in copy_columns:
            result.at[index, column] = market.get(column)
        model_probabilities = [float(fixture[column]) for column in model_columns]
        market_probabilities = [float(market[column]) for column in market_columns]
        decimal_odds = [float(market[column]) for column in odds_columns]
        edges = [model - fair for model, fair in zip(model_probabilities, market_probabilities)]
        expected_returns = [model * price - 1.0 for model, price in zip(model_probabilities, decimal_odds)]
        for column, edge in zip(edge_columns, edges):
            result.at[index, column] = edge
        best_index = max(range(3), key=lambda position: edges[position])
        result.at[index, "BestValueOutcome"] = outcome_names[best_index]
        result.at[index, "BestValueEdge"] = edges[best_index]
        result.at[index, "BestValueExpectedReturn"] = expected_returns[best_index]
        result.at[index, "OddsMatched"] = True

        display_outcome = (
            str(fixture.get("HomeTeam"))
            if best_index == 0
            else "Draw"
            if best_index == 1
            else str(fixture.get("AwayTeam"))
        )
        bookmaker = str(market.get("Bookmaker"))
        if str(fixture.get("Risk_Category")) == "Critical Risk":
            result.at[index, "BetRecommendation"] = "No bet"
            result.at[index, "BetReason"] = "Market price is available, but model uncertainty is critical."
        elif edges[best_index] >= min_edge and expected_returns[best_index] >= min_expected_return:
            result.at[index, "BetRecommendation"] = (
                f"Consider {display_outcome} @ {decimal_odds[best_index]:.2f} ({bookmaker})"
            )
            result.at[index, "BetReason"] = (
                f"Model edge {edges[best_index]:.1%}; expected return {expected_returns[best_index]:.1%}."
            )
        else:
            result.at[index, "BetRecommendation"] = "No bet"
            result.at[index, "BetReason"] = (
                f"Best market edge {edges[best_index]:.1%} and expected return "
                f"{expected_returns[best_index]:.1%} do not clear the value gate."
            )
    return result
