# Vprofitables: Institutional Quant & AI Engine

![Vprofitables](https://img.shields.io/badge/Status-Active-brightgreen.svg)
![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-blue.svg)

Vprofitables is an institutional-grade, fully automated quantitative trading engine and backtester. Originally starting as a retail script, it has been massively upgraded into a proprietary trading platform utilizing Machine Learning, Wavelet Transforms, and Statistical Arbitrage.

## 🚀 Features

*   **Continual Learning ML Engine:** Uses SGDClassifier to dynamically adapt trade scoring weights day-by-day, completely eliminating concept drift.
*   **Time-Frequency Analysis (CWT):** Extracts hidden dominant market cycles using Continuous Wavelet Transforms (Morlet) instead of rigid Fourier equations.
*   **Market-Neutral Statistical Arbitrage:** Finds highly cointegrated equity pairs and generates mean-reversion signals via Z-Score deviations.
*   **Order Flow Microstructure:** Calculates Cumulative Volume Delta (CVD) proxies from 1-minute DuckDB tick data to detect institutional spoofing.
*   **Institutional Backtesting:** Includes **Monte Carlo Permutation** for True Maximum Drawdowns (95% CI) and **Deflated Sharpe Ratio** to prevent multiple-testing bias (p-hacking).
*   **Progressive Web App (PWA):** Beautifully crafted UI/UX with "Traffic Light" confidence scoring, responsive mobile drawers, and single-page routing for millisecond latency.

## 🛠️ Quickstart (One-Click Deploy)

Run Vprofitables on any machine (Windows, Mac, Linux) seamlessly using Docker.

### Prerequisites
*   Docker & Docker Compose installed.

### Run via Docker
`ash
git clone https://github.com/chirag-kaura/vprofitables.git
cd vprofitables
docker-compose up --build -d
`
Navigate to [http://localhost:8080](http://localhost:8080) to access the Terminal.

### Run via Python (Locally)
`ash
pip install -r requirements.txt
python app.py
`

## 🧠 Architecture
- **Backend:** Python, DuckDB, Scikit-Learn, SciPy
- **Frontend:** Vanilla JS Single Page Application (SPA), PWA ready.
- **Data:** yfinance 1-minute polling combined with robust local SQLite/DuckDB caching.

## 📝 License
MIT License. Open-sourced for the quantitative finance community.
