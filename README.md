# 🥊 UFC Fighter Dashboard

An interactive Streamlit dashboard for exploring UFC fighter statistics scraped
from [ufcstats.com](http://ufcstats.com/statistics/fighters).

## Features

- **Fighter Explorer** — searchable profile, KO/SUB/DEC rates, current form, last 5 fights.
- **Fighter Comparison** — 2 to 5 fighters overlaid on a radar, color-coded stat table,
  head-to-head bouts from fight history.
- **Rankings** — filterable, sortable leaderboard with finish-rate columns and CSV export.
- **Stat Universe** — every UFC fighter on one XY scatter for any two metrics; toggleable
  **z-score normalization within weight class** and **champion overlay**; click any point
  to inspect; multi-select search to highlight specific fighters with name labels.
- **Insights** — Pearson correlation heatmap across all stats; group-by-stance /
  weight-class means; "Champions vs the field" delta table.
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
│   ├── dashboard.py       # Streamlit entry point (5 pages)
│   ├── charts.py          # Plotly chart builders + UFC theme
│   └── derived.py         # finish rates / streaks / activity / champion enrichment
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
`data/fights.csv`; subsequent launches are instant. Use the **🔄 Refresh data**
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

76 tests cover the HTML parsers (with fixture HTML), unit conversions, weight-class
bucketing, the 0-fight data-cleanup, finish-rate / streak derivation, and z-score
normalisation. Runs in ~2 seconds.

## Screenshots

> _Screenshots go here once you've run the dashboard locally._

- ![Fighter Explorer](docs/screenshot-explorer.png)
- ![Comparison Radar](docs/screenshot-comparison.png)
- ![Stat Universe](docs/screenshot-universe.png)

## Notes

- Career-average stats (SLpM, Str. Acc., Str. Def., SApM, TD Avg., TD Acc.,
  TD Def., Sub. Avg.) come from each fighter's individual detail page.
- Weight class is derived from listed weight (lbs).
- Per-fight history ("Last 5 fights" and head-to-head) is not yet wired up —
  ufcstats.com publishes it on the same detail pages and can be added by
  extending `scraper/scraper.py`.

## Tech

`requests` + `beautifulsoup4` for scraping · `pandas` for data shaping ·
`streamlit` for the UI · `plotly` for interactive charts.
