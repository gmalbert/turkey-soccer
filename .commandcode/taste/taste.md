# Taste

- Keeps API keys and provider configuration (e.g., odds API key, bookmaker lists) in `.env` and expects the app/model code to read them from there rather than hardcoding them in source. Confidence: 0.8
- Wants external data sources (odds, weather) wired end-to-end into the app UI and the model pipeline — a fetch script or cached file alone is not "integrated" until the app and model actually consume the data. Confidence: 0.7
- Repeatedly requires stadium GPS coordinates and weather data to be pulled and fed into predictions as model features — treats this as a required, recurring part of the pipeline, not an optional extra. Confidence: 0.6
- Wants a handoff markdown file (e.g., HANDOFF.md in the repo root) written when a session must be interrupted — capturing findings, exact commands, and next steps so a fresh session can resume cleanly after reload/permission changes. Confidence: 0.8
