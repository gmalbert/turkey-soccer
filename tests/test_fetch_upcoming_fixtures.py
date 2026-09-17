from datetime import datetime, timezone
from pathlib import Path

import requests

import fetch_upcoming_fixtures as module


class _Response:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "events": [
                {
                    "date": "2026-09-20T16:00:00Z",
                    "status": {"type": {"name": "STATUS_SCHEDULED"}},
                    "competitions": [
                        {
                            "competitors": [
                                {
                                    "homeAway": "home",
                                    "team": {"displayName": "Galatasaray"},
                                },
                                {
                                    "homeAway": "away",
                                    "team": {"displayName": "Besiktas"},
                                },
                            ]
                        }
                    ],
                }
            ]
        }


def test_upcoming_fixtures_persist_exact_utc_kickoff(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(module.requests, "get", lambda *args, **kwargs: _Response())

    result = module.fetch_upcoming_fixtures(output_dir=tmp_path)

    assert result.loc[0, "kickoff_utc"] == "2026-09-20T16:00:00+00:00"
    assert result.loc[0, "Date"] == "2026-09-20"
    assert result.loc[0, "Time"] == "12:00"
    persisted = (tmp_path / "upcoming_fixtures.csv").read_text()
    assert "kickoff_utc" in persisted.splitlines()[0]


def test_scoreboard_falls_back_to_daily_requests_after_range_400(monkeypatch):
    calls = []

    class _RangeRejected:
        def raise_for_status(self):
            response = type("Response", (), {"status_code": 400})()
            raise requests.HTTPError("range rejected", response=response)

    class _EmptyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"events": []}

    def fake_get(url, **kwargs):
        calls.append(kwargs["params"]["dates"])
        if "-" in calls[-1]:
            return _RangeRejected()
        return _EmptyResponse()

    monkeypatch.setattr(module.requests, "get", fake_get)

    events = module._scoreboard_events(
        datetime(2026, 9, 17, tzinfo=timezone.utc), days_ahead=1
    )

    assert events == []
    assert calls == ["20260917-20260918", "20260917", "20260918"]
