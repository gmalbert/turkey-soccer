from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import pytest
import requests

from odds_api_io import OddsApiIoClient, attach_market_odds


class FakeResponse:
    def __init__(self, payload, *, error: Exception | None = None):
        self.payload = payload
        self.error = error

    def raise_for_status(self):
        if self.error is not None:
            raise self.error

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, *, params, timeout):
        self.calls.append((url, params, timeout))
        return self.responses.pop(0)


def test_fetch_batches_events_and_prefers_complete_bet365_moneyline():
    events = [
        {"id": number}
        for number in range(1, 12)
    ]
    first_odds = [
        {
            "id": 1,
            "home": "Fenerbahce",
            "away": "Galatasaray",
            "date": "2026-08-20T18:00:00Z",
            "bookmakers": {
                "Bet365": [{"name": "ML", "updatedAt": "2026-08-20T10:00:00Z", "odds": [
                    {"home": "2.10", "draw": "3.40", "away": "3.20"}
                ]}],
                "Unibet": [{"name": "ML", "odds": [{"home": "2.20", "draw": "3.30", "away": "3.10"}]}],
            },
        },
        {
            "id": 2,
            "home": "Istanbul Basaksehir FK",
            "away": "Caykur Rizespor",
            "date": "2026-08-21T17:00:00Z",
            "bookmakers": {
                "Bet365": [{"name": "ML", "odds": [{"home": "1.90", "away": "4.20"}]}],
                "Unibet": [{"name": "ML", "odds": [{"home": "1.95", "draw": "3.50", "away": "4.10"}]}],
            },
        },
    ]
    session = FakeSession([FakeResponse(events), FakeResponse(first_odds), FakeResponse([])])
    client = OddsApiIoClient(
        api_key="secret",
        league_slug="turkey-super-lig",
        bookmakers=("Bet365", "Unibet"),
        team_aliases={
            "Istanbul Basaksehir FK": "Buyuksehyr",
            "Caykur Rizespor": "Rizespor",
        },
        session=session,
    )

    result = client.fetch(
        start=datetime(2026, 8, 10, tzinfo=timezone.utc),
        end=datetime(2026, 9, 10, tzinfo=timezone.utc),
    )

    assert len(session.calls) == 3
    assert session.calls[1][1]["eventIds"] == ",".join(str(number) for number in range(1, 11))
    assert session.calls[2][1]["eventIds"] == "11"
    assert session.calls[1][1]["bookmakers"] == "Bet365,Unibet"
    assert session.calls[0][1]["apiKey"] == "secret"
    assert result["Bookmaker"].tolist() == ["Bet365", "Unibet"]
    assert result.loc[1, "HomeTeam"] == "Buyuksehyr"
    assert result.loc[1, "AwayTeam"] == "Rizespor"
    assert result.loc[0, ["MarketHomeProb", "MarketDrawProb", "MarketAwayProb"]].sum() == pytest.approx(1.0)
    assert result.loc[0, "MarketMargin"] > 0


def test_fetch_without_key_or_on_http_error_is_a_safe_empty_cache():
    session = FakeSession([])
    no_key = OddsApiIoClient(
        api_key=None,
        league_slug="turkey-super-lig",
        bookmakers=("Bet365",),
        session=session,
    )
    assert no_key.fetch().empty
    assert not session.calls
    assert "not configured" in no_key.last_error

    failing_session = FakeSession([FakeResponse({}, error=requests.HTTPError("429"))])
    failing = OddsApiIoClient(
        api_key="secret",
        league_slug="turkey-super-lig",
        bookmakers=("Bet365",),
        session=failing_session,
    )
    assert failing.fetch().empty
    assert "429" in failing.last_error


def test_attach_market_odds_matches_names_and_applies_value_and_risk_gates():
    predictions = pd.DataFrame(
        [
            {
                "Date": "2026-08-20", "Time": "14:00", "HomeTeam": "Fenerbahce",
                "AwayTeam": "Galatasaray", "HomeWin_Prob": 0.60, "Draw_Prob": 0.22,
                "AwayWin_Prob": 0.18, "Risk_Category": "Low Risk",
                "BetRecommendation": "No bet", "BetReason": "Market unavailable",
            },
            {
                "Date": "2026-08-21", "Time": "13:00", "HomeTeam": "Buyuksehyr",
                "AwayTeam": "Rizespor", "HomeWin_Prob": 0.60, "Draw_Prob": 0.22,
                "AwayWin_Prob": 0.18, "Risk_Category": "Critical Risk",
                "BetRecommendation": "No bet", "BetReason": "Market unavailable",
            },
        ]
    )
    odds = pd.DataFrame(
        [
            {
                "Date": "2026-08-20", "Time": "14:00", "HomeTeam": "Fenerbahçe SK",
                "AwayTeam": "Galatasaray SK", "OddsEventId": "1", "Bookmaker": "Bet365",
                "OddsHome": 2.10, "OddsDraw": 3.40, "OddsAway": 3.20,
                "MarketHomeProb": 0.44, "MarketDrawProb": 0.28, "MarketAwayProb": 0.28,
                "MarketMargin": 0.08, "OddsUpdatedAt": "2026-08-20T10:00:00Z",
                "OddsProvider": "Odds-API.io",
            },
            {
                "Date": "2026-08-21", "Time": "13:00", "HomeTeam": "Buyuksehyr",
                "AwayTeam": "Rizespor", "OddsEventId": "2", "Bookmaker": "Unibet",
                "OddsHome": 2.10, "OddsDraw": 3.40, "OddsAway": 3.20,
                "MarketHomeProb": 0.44, "MarketDrawProb": 0.28, "MarketAwayProb": 0.28,
                "MarketMargin": 0.08, "OddsUpdatedAt": "2026-08-20T10:00:00Z",
                "OddsProvider": "Odds-API.io",
            },
        ]
    )

    result = attach_market_odds(predictions, odds)

    assert result["OddsMatched"].tolist() == [True, True]
    assert result.loc[0, "BestValueOutcome"] == "Home Win"
    assert result.loc[0, "BestValueEdge"] == pytest.approx(0.16)
    assert result.loc[0, "BestValueExpectedReturn"] == pytest.approx(0.26)
    assert result.loc[0, "BetRecommendation"].startswith("Consider Fenerbahce @ 2.10")
    assert result.loc[1, "BetRecommendation"] == "No bet"
    assert "critical" in result.loc[1, "BetReason"].lower()
