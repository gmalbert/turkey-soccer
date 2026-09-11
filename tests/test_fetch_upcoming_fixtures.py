from pathlib import Path

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
