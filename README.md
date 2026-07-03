# UFC Fighter Dashboard

An interactive Streamlit dashboard for exploring UFC fighter statistics scraped
from [ufcstats.com](http://ufcstats.com/statistics/fighters).

## Features

- **Fighter Explorer** — searchable profile, KO/SUB/DEC rates, current form, career-trajectory
  chart, win-method breakdown, last 5 fights.
- **Fighter Comparison** — 2 to 5 fighters overlaid on a radar, color-coded stat table,
  head-to-head bouts from fight history.
- **Rankings** — filterable, sortable leaderboard with finish-rate columns and CSV export.
- **Stat Universe** — every UFC fighter on one XY scatter for any two metrics; toggleable
  **z-score normalization within weight class** and **champion overlay**; click any point
  to inspect; multi-select search to highlight specific fighters with name labels.
- **Insights** — Pearson correlation heatmap across all stats; group-by-stance /
  weight-class means; "Champions vs the field" delta table.
- **ML Matchup** — logistic regression trained on fighter-vs-opponent stat differentials
  predicts win probability for any pairing, with held-out accuracy/AUC and feature importances.
- **Network** — interactive opponent graph across all fighters; node size by number of
  bouts, color by weight class.
- **Global filters** in sidebar — minimum UFC fights (cleans 0/50/100% small-sample
  spikes) and "active fighters only" (last fight ≤ 2 years).
- Dark UFC red/black/white theme, one-click refresh, cache-first loading.

## Project structure

```
ufc-dashboard/
├── scraper/
│   └── scraper.py         # ufcstats.com scraper (listing + detail + fight history)
├── data/
│   ├── fighters.csv       # generated cache (gitignored)
│   └── fights.csv         # per-bout fight history cache (gitignored)
├── app/
│   ├── dashboard.py       # Streamlit entry point (7 pages)
│   ├── charts.py          # Plotly chart builders + UFC theme
│   ├── derived.py         # finish rates / streaks / activity / champion enrichment
│   └── ml.py              # win-probability model (scikit-learn)
├── requirements.txt
├── .gitignore
└── README.md
```

## Setup

> Requires Python 3.10+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

On macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run locally

```bash
streamlit run app/dashboard.py
```

The first launch triggers a full scrape: ~4000 fighters across 26 alphabetical
pages, one detail page per fighter (career stats **+** full bout history).
This takes 5-10 minutes once. Results are cached at `data/fighters.csv` and
`data/fights.csv`; subsequent launches are instant. Use the **Refresh data**
button in the sidebar to re-scrape any time.

You can also run the scraper standalone:

```bash
python scraper/scraper.py
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

133 tests cover the HTML parsers (with fixture HTML), unit conversions, weight-class
bucketing, the 0-fight data-cleanup, finish-rate / streak derivation, z-score
normalisation, and the ML training pipeline. Runs in a few seconds.


## Tech

`requests` + `beautifulsoup4` for scraping · `pandas` for data shaping ·
`streamlit` for the UI · `plotly` for interactive charts · `scikit-learn` for the
matchup model · `networkx` for the fighter network graph.
