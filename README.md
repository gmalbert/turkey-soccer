# Pitch Oracle Süper Lig Consumer

This repository is a thin Süper Lig deployment backed by
`pitch-oracle-core`. League behavior lives in `config.py`; shared data preparation,
training, artifact contracts, and Streamlit pages come from the immutable core pin.

## First run

Use Python 3.12 or newer:

Copy `.env.example` to `.env` and set `FD_API_KEY` when using the
football-data.org integration. Set `ODDS_API_IO_KEY` to enrich upcoming
predictions with server-cached Odds-API.io 1X2 prices. The integration selects
bookmakers from `ODDS_API_IO_BOOKMAKERS` (comma-separated; defaults to Bet365
and Unibet), removes the bookmaker margin, and compares those market
probabilities with the independent model. Missing odds never stop prediction
generation; affected fixtures remain explicitly marked as having no bet.

Consumers created by `bootstrap_consumer.py`
automatically copy the core repository's local `.env` when it exists. The
populated file is Git-ignored and must never be committed.

Local verification:

```bash
python -m venv venv
venv\\Scripts\\python -m pip install -r requirements.txt
venv\\Scripts\\python -m compileall -q .
venv\\Scripts\\python -m pytest -q
venv\\Scripts\\python scripts/bootstrap_local.py
venv\\Scripts\\streamlit run predictions.py
```

On macOS or Linux, activate the virtual environment first and use its Python:

```bash
python -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python -m compileall -q .
python -m pytest -q
python scripts/bootstrap_local.py
streamlit run predictions.py
```

Generated `data_files/`, `models/`, and `precomputed/` artifacts are produced by
the **Süper Lig artifact pipeline** workflow. Run it manually after the initial
push. It must commit those directories together with a strict cache manifest.

Before that first build, artifact tests skip because no model cache exists. After
the workflow succeeds, run `python scripts/verify_consumer.py`; missing or
mismatched artifacts then fail hard.

The baseline intentionally uses football-data history and ESPN fixtures. Add
optional sources only after league-specific coverage and failure-mode tests exist.

For GitHub Actions, add the required keys from `.env.example` as repository or
organization secrets. The reusable artifact workflow receives them through `secrets: inherit`;
local `.env` files are deliberately unavailable to CI.

To refresh only the bookmaker cache and enriched predictions locally:

```bash
venv\\Scripts\\python scripts/fetch_live_odds.py
venv\\Scripts\\python scripts/precompute_predictions.py
venv\\Scripts\\python -m build_cache_manifest
```

The Predictions page also offers a "Fetch latest Odds-API.io prices" button
(under the Bookmaker market section) that refetches the odds cache and
regenerates enriched predictions without leaving the app.

For the full creation, GitHub configuration, validation, release, and core-upgrade
process, see `docs/new-consumer-repository.md` in `pitch-oracle-core`.
