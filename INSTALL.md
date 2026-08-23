# GANN-ASTRO v3.8 — Installation Guide

## Folder Structure
```
GANN-ASTRO-v3.8/
├── START.bat               ← Double-click to run
├── app.py                  ← Main server
├── requirements.txt        ← All Python dependencies
├── market_data.db          ← YOUR DATABASE (copy from old install, or fresh)
├── gann_settings.json      ← Notification config (email / WhatsApp)
├── download_history.py     ← Run once to fetch full price history
├── bulk_news_fetch.py      ← Daily news fetcher
├── core/                   ← Analysis engines
│   ├── scheduler.py
│   ├── signal_engine.py
│   ├── quant_engine.py
│   ├── wyckoff_engine.py
│   ├── fundamental_engine.py
│   ├── sentiment_db.py
│   ├── notifier.py
│   └── ...
├── pages/                  ← UI page modules
│   ├── page_dashboard.py
│   ├── page_advisor.py
│   └── ...
└── data/
    └── instruments.py      ← 40 NSE/BSE/MCX instruments
```

## Fresh Install (no existing data)

1. Extract the zip anywhere, e.g. C:\GANN-ASTRO\
2. Double-click START.bat
   - Installs all dependencies automatically
   - Creates a fresh market_data.db
   - Opens browser at http://localhost:8080
3. After the app loads, run price history download:
   python download_history.py
   This takes 10-15 min and downloads full OHLCV history for all 40 symbols.

## Upgrading from v3.7 (existing install)

1. Extract this zip to a NEW folder, e.g. C:\GANN-ASTRO-v3.8\
2. Copy your database from the old folder:
   C:\GANN-ASTRO-v3.7\market_data.db  ->  C:\GANN-ASTRO-v3.8\market_data.db
3. Double-click START.bat — done.

Your historical prices, pivot levels, news sentiment, and labels are all in the DB
and will be loaded automatically. No data is lost.

## Requirements

- Python 3.10+ — download from https://python.org
  - Tick "Add Python to PATH" during install
- Windows 10/11 (START.bat is Windows only)
- Linux/Mac: run  pip install -r requirements.txt  then  python app.py

## Troubleshooting

Problem                   | Fix
--------------------------|----------------------------------------------
Python not found          | Install Python 3.10+ and tick "Add to PATH"
Browser does not open     | Go to http://localhost:8080 manually
Port 8080 in use          | Set env var GANN_PORT=8081 before running
ModuleNotFoundError       | Run: pip install -r requirements.txt
Blank page on first load  | Wait 10s and refresh — first boot takes longer
