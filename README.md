<p align="center">
  <img src="data_files/logo.png" alt="Turkey Süper Lig Predictions" width="200">
</p>

<h1 align="center">Turkey Süper Lig Predictions</h1>

<p align="center">
  AI-powered match predictions for Turkish football with bookmaker odds comparison
</p>

---

## Overview

This app predicts outcomes for Turkey's Süper Lig matches using machine learning models trained on historical data. It compares model probabilities against real-time bookmaker odds to identify potential value bets.

## Features

- **Match Predictions** — Win/Draw/Loss probabilities for upcoming fixtures
- **Bookmaker Comparison** — Real-time odds from Bet365, Unibet, and more
- **Value Detection** — Highlights bets where the model disagrees with the market
- **Team Analysis** — Deep dive into team performance and statistics
- **Live Standings** — Current league table and historical trends
- **Model Lab** — Explore model performance and feature importance

## League Info

- **League:** Süper Lig (Turkey)
- **Teams:** 19 clubs including Galatasaray, Fenerbahçe, Beşiktaş, and more
- **Data Sources:** football-data.org, ESPN, Odds-API.io
- **Season:** 2026-27

## Quick Start

1. Clone the repository
2. Copy `.env.example` to `.env` and add your API keys
3. Run the app:

```bash
pip install -r requirements.txt
streamlit run predictions.py
```

For detailed setup, configuration, and development workflows, see [TECHNICAL.md](TECHNICAL.md).

## How It Works

The app uses an ensemble of machine learning models (XGBoost, neural networks) trained on:
- Historical match results and statistics
- Team form and head-to-head records
- Stadium coordinates and weather data
- Bookmaker odds (for comparison, not prediction)

Predictions are generated before each matchday and cached for fast loading.

## API Keys

You'll need free API keys from:
- [football-data.org](https://www.football-data.org/) — Historical match data
- [Odds-API.io](https://the-odds-api.com/) — Live bookmaker odds

Add them to your `.env` file. See [TECHNICAL.md](TECHNICAL.md) for detailed setup, configuration, and development workflows.

## License

This project uses the Pitch Oracle core library. See `pitch-oracle-core` for licensing details.
