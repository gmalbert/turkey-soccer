# Handoff: odds + stadium weather integration

State at handoff: exploration complete, **no code changes made yet**. A permission
prompt for a network call was denied so you can reload with adjusted permissions.

## Task

1. Integrate Odds-API.io odds pulling into the app and the model (`ODDS_API_IO_KEY`
   is now populated in `.env`).
2. Add GPS coordinates for each stadium and pull weather for fixtures.

## Repo facts

- Thin consumer of immutable `pitch-oracle-core` pinned at **v1.3.26** (requirements.txt,
  requirements-ci.txt, artifact-pipeline.yml, `test_consumer_contract.py`).
- Consumer-owned files: `config.py`, `odds_api_io.py`, `market_ui.py`,
  `fetch_upcoming_fixtures.py`, `predictions.py`, `scripts/{fetch_live_odds,precompute_predictions,bootstrap_local,verify_consumer}.py`,
  `tests/`.
- Training pipeline modules live in the **venv site-packages**, not this repo:
  `venv/Lib/site-packages/{combine_raw_data,prepare_model_data,train_models,precompute_database,build_cache_manifest,fetch_weather_data}.py`.
- Windows: use `venv\Scripts\python -X utf8` for any command touching Turkish text
  (default cp1252 console crashes on `\u26bd` / `ç` etc.).
- Current tests: `venv\Scripts\python -m pytest -q` → 6 passed.

## Finding 1 — odds never cached because the league slug is wrong

- `config.py`: `ODDS_API_IO_LEAGUE_SLUG = "turkey-super-lig"` **→ 404**.
- Provider's real slug (queried `/v3/leagues?sport=football`, 795 leagues):
  **`turkiye-super-lig`** ("Turkiye - Super Lig"). Sport slug is `football` (lowercase;
  uppercase `Football` → 400 "Invalid sport slug").
- `data_files/odds.csv` exists but is **empty (0 rows)** → all `OddsMatched=False` in
  `upcoming_predictions.csv` → UI "Bookmaker market" section always empty.
- `.env` now has:
  - `ODDS_API_IO_KEY=61c77d3da19faa6523c52ccf080cf62571e672d5aff8dd70f4c24a7e66175cbd`
  - `ODDS_API_IO_BOOKMAKERS=DraftKings,Bet365` (config.py hardcodes `("Bet365", "Unibet")` and nothing reads the env var).
- `.env.example` has `ODDS_API_IO_KEY=` but no `ODDS_API_IO_BOOKMAKERS=` line.

### Verify (once network permission granted)

```bash
venv\Scripts\python -X utf8 -c "from dotenv import load_dotenv; import os, requests; load_dotenv('.env'); k=os.getenv('ODDS_API_IO_KEY'); r=requests.get('https://api.odds-api.io/v3/events', params={'sport':'football','league':'turkiye-super-lig','status':'pending','apiKey':k}, timeout=20); print(r.status_code); print(r.text[:1500])"
```

This exact call is what was denied. Expect 200 + a JSON event list.

## Finding 2 — weather never fetched because stadium_coordinates is empty

- `LEAGUE_CONFIG.stadium_coordinates` = `{}` (core `leagues.py` turkey entry has none).
- Core `prepare_model_data.py` (line ~460) calls `add_weather_features(...)` for the
  **historical** backfill, and `scripts/precompute_predictions.py` (line 34) for
  **upcoming** fixtures — both build stadium maps from `LEAGUE_CONFIG.stadium_coordinates`,
  so with `{}` nothing is ever fetched and columns get safe defaults.
- Confirmed: `combined_historical_data_with_calculations_new.csv` (1370 rows) has
  **all-NaN Temperature/Humidity/WindSpeed, Precipitation=0**.
- The model contract **already includes weather**: FeatureContract width 45 with
  `['Temperature', 'Humidity', 'WindSpeed', 'Precipitation']` (imputation 0.0), so
  real weather will flow straight into `build_upcoming_feature_matrix` → model inference.
- Core weather API: `pitch_oracle_core.add_weather_features(df, *, cache_file, stadium_map,
  stadium_coords, data_dir, timezone, fetcher=None)`; `fetch_match_weather(stadium_location,
  match_date, *, stadium_coords, raise_on_error, timezone, client)`. Open-Meteo forecast
  for future dates, archive API for past. `Stadium = (name, latitude, longitude)`; config
  value is `dict[team -> tuple[lat, lon]]` (see EPL: `"Man United": (53.4631, -2.2913)`).
- `sources.weather=True`, `weather_timezone='Europe/London'`.

### Coordinates needed

For the 18 teams in `data_files/upcoming_fixtures.csv` (home-venue lookup):

`Alanyaspor, Amed SFK, Besiktas, Buyuksehyr, Erzurum BB, Eyupspor, Fenerbahce,
Galatasaray, Gaziantep, Genclerbirligi, Goztep, Kasimpasa, Kocaelispor, Konyaspor,
Rizespor, Samsunspor, Trabzonspor, Corum FK (shown as mojibake "�orum FK")`

Plus all historical teams so the backfill covers training data:

`Ad. Demirspor, Ankaragucu, Antalyaspor, Bodrumspor, Giresunspor, Hatayspor,
Istanbulspor, Karagumruk, Kayserispor, Pendikspor, Sivasspor, Umraniyespor`

### Team-name mismatch to handle

- New 2026-27 teams **Amed SFK, Erzurum BB, Corum FK** have no history → model imputes
  their team features; that's fine, but they still need stadium coords for weather.
- `upcoming_fixtures.csv` contains `�orum FK` (mojibake). `normalize_team_name` in
  `team_name_mapping` (core) needs an alias handling the replacement char / Turkish
  spelling, e.g. `"Çorum FK" -> "Corum"`, `"�orum FK" -> "Corum"`.

## Plan (agreed direction)

1. `config.py`:
   - `ODDS_API_IO_LEAGUE_SLUG = "turkiye-super-lig"`.
   - `ODDS_API_IO_BOOKMAKERS` read from env `ODDS_API_IO_BOOKMAKERS` (comma-split),
     fallback to `("Bet365", "Unibet")`.
   - Add `STADIUM_COORDINATES` dict (team → `(lat, lon)`) for upcoming + historical teams.
   - `LEAGUE_CONFIG = replace(get_league_config("turkey"), espn_slug="tur.1",
     team_aliases={...existing + Corum aliases...}, stadium_coordinates=STADIUM_COORDINATES)`.
2. `.env.example`: add `ODDS_API_IO_BOOKMAKERS=`.
3. Run `venv\Scripts\python scripts/fetch_live_odds.py` → verify `odds.csv` populates.
4. Run `venv\Scripts\python scripts/precompute_predictions.py` → verify weather columns
   (Temperature/Humidity/WindSpeed/Precipitation + WeatherImpact) appear on
   `upcoming_predictions.csv` and `OddsMatched` flips True where lines exist.
5. Optionally surface weather in `market_ui.py` / predictions table (add columns to
   `_format_market_table`).
6. App-side odds pulling: user asked to "integrate the odds pulling into the app" —
   decision point. Options: (a) sidebar refresh button in `market_ui.py` that calls
   `scripts.fetch_live_odds.fetch()` + regenerates predictions, or (b) keep server-cache
   model and only fix the pipeline. The current design is server-cached (README), so
   confirm with user before adding runtime network calls in Streamlit.
7. Update `tests/test_consumer_contract.py` if bookmaker defaults change (it asserts
   `ODDS_API_IO_BOOKMAKERS == ("Bet365", "Unibet")`).
8. Re-run pytest; update README only if behavior/commands change.

## Watch-outs

- `verify_consumer.py` validates `odds.csv` columns and no-vig probability sums — keep schema.
- `add_weather_features` refreshes future-date rows every build; keep
  `cache_file=f"weather_cache_{LEAGUE_CONFIG.key}.csv"` naming so historical backfill and
  upcoming enrichment share one cache.
- `bootstrap_local.py` runs the whole pipeline including network-dependent steps.
- `.github/workflows/artifact-pipeline.yml` uses `secrets: inherit`; ensure
  `ODDS_API_IO_KEY` exists as a GitHub secret (and any new env var used by CI).
- Do not commit `.env`. `.gitignore` already covers it.
