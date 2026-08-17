# Technical Setup & Development

This document contains detailed setup instructions, configuration, and development workflows for the Turkey Süper Lig prediction app.

## Prerequisites

- Python 3.12 or newer
- API keys (see [Configuration](#configuration))

## First Run

### Configuration

Copy `.env.example` to `.env` and configure the following:

| Variable | Description |
|----------|-------------|
| `FD_API_KEY` | football-data.org API key (for historical data) |
| `ODDS_API_IO_KEY` | Odds-API.io key (for bookmaker odds) |
| `ODDS_API_IO_BOOKMAKERS` | Comma-separated bookmaker names (default: Bet365, Unibet) |

The odds integration removes bookmaker margin and compares market probabilities with the model. Missing odds never stop prediction generation; affected fixtures are marked as having no bet.

Consumers created by `bootstrap_consumer.py` automatically copy the core repository's local `.env` when it exists. The populated file is Git-ignored and must never be committed.

### Windows Setup

```bash
python -m venv venv
venv\Scripts\python -m pip install -r requirements.txt
venv\Scripts\python -m compileall -q .
venv\Scripts\python -m pytest -q
venv\Scripts\python scripts/bootstrap_local.py
venv\Scripts\streamlit run predictions.py
```

### macOS/Linux Setup

```bash
python -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python -m compileall -q .
python -m pytest -q
python scripts/bootstrap_local.py
streamlit run predictions.py
```

## Artifacts

Generated `data_files/`, `models/`, and `precomputed/` artifacts are produced by the **Süper Lig artifact pipeline** workflow. Run it manually after the initial push. It must commit those directories together with a strict cache manifest.

Before that first build, artifact tests skip because no model cache exists. After the workflow succeeds, run `python scripts/verify_consumer.py`; missing or mismatched artifacts then fail hard.

The baseline intentionally uses football-data history and ESPN fixtures. Add optional sources only after league-specific coverage and failure-mode tests exist.

## GitHub Actions

For GitHub Actions, add the required keys from `.env.example` as repository or organization secrets. The reusable artifact workflow receives them through `secrets: inherit`; local `.env` files are deliberately unavailable to CI.

## Refreshing Odds & Predictions

To refresh only the bookmaker cache and enriched predictions locally:

```bash
venv\Scripts\python scripts/fetch_live_odds.py
venv\Scripts\python scripts/precompute_predictions.py
venv\Scripts\python -m build_cache_manifest
```

The Predictions page also offers a "Fetch latest Odds-API.io prices" button (under the Bookmaker market section) that refetches the odds cache and regenerates enriched predictions without leaving the app.

## Architecture

This repository is a thin Süper Lig deployment backed by `pitch-oracle-core`. League behavior lives in `config.py`; shared data preparation, training, artifact contracts, and Streamlit pages come from the immutable core pin.

For the full creation, GitHub configuration, validation, release, and core-upgrade process, see `docs/new-consumer-repository.md` in `pitch-oracle-core`.
