"""
Streamlit dashboard for exploring UFC fighter statistics.

Run with:
    streamlit run app/dashboard.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Allow ``streamlit run app/dashboard.py`` to import sibling packages.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import charts, derived  # noqa: E402
from scraper import scraper  # noqa: E402

st.set_page_config(
    page_title="UFC Fighter Dashboard",
    page_icon="🥊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Theming
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
<style>
:root {
    --ufc-red: #D20A0A;
    --ufc-black: #0D0D0D;
    --ufc-grey: #1A1A1A;
    --ufc-white: #F5F5F5;
}
.stApp { background-color: var(--ufc-black); color: var(--ufc-white); }
section[data-testid="stSidebar"] {
    background-color: var(--ufc-grey);
    border-right: 1px solid var(--ufc-red);
}
h1, h2, h3, h4 { color: var(--ufc-white) !important; }
.stButton > button {
    background-color: var(--ufc-red);
    color: var(--ufc-white);
    border: none;
    border-radius: 4px;
    font-weight: 600;
}
.stButton > button:hover { background-color: #b00808; color: white; }
div[data-testid="stMetric"] {
    background-color: var(--ufc-grey);
    padding: 12px;
    border-left: 4px solid var(--ufc-red);
    border-radius: 4px;
}
.fighter-card {
    background-color: var(--ufc-grey);
    border-left: 6px solid var(--ufc-red);
    padding: 18px 22px;
    border-radius: 6px;
    margin-bottom: 12px;
}
.fighter-card h2 { margin: 0 0 4px 0; }
.fighter-card .nickname { color: #BBB; font-style: italic; margin-bottom: 8px; }
.compare-row { display: flex; align-items: center; padding: 6px 10px; border-bottom: 1px solid #222; }
.compare-row .stat-name { flex: 1; color: var(--ufc-white); }
.compare-row .val { flex: 1; text-align: center; font-weight: 600; }
.win { color: #2ECC71; }
.lose { color: #E74C3C; }
.tie { color: #BBBBBB; }
.info-popover {
    background-color: var(--ufc-grey);
    border: 1px solid var(--ufc-red);
    border-radius: 6px;
    padding: 14px 18px;
}
</style>
"""


def inject_theme() -> None:
    """Inject custom CSS for the dark UFC theme."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def _load_cached_df() -> pd.DataFrame | None:
    """Memoized read of the CSV cache, with post-load cleanup + enrichment."""
    df = scraper.load_cached()
    if df is None or df.empty:
        return df
    df = _clean_dataframe(df)
    fights = scraper.load_cached_fights()
    events = scraper.load_cached_events()
    return derived.enrich_with_fight_data(df, fights, events)


@st.cache_data(show_spinner=False)
def _load_cached_fights() -> pd.DataFrame | None:
    """Memoized read of the fights CSV cache."""
    return scraper.load_cached_fights()


@st.cache_data(show_spinner=False)
def _load_cached_events() -> pd.DataFrame | None:
    """Memoized read of the events CSV cache."""
    return scraper.load_cached_events()


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Post-load sanity pass.

    Older cached CSVs may carry the ``0.00`` / ``0%`` placeholders that
    ufcstats.com serves for fighters with no UFC bouts on record. Null
    those rows out so they don't pollute distributions.
    """
    df = df.copy()
    for col in ["wins", "losses", "draws"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    if "total_fights" not in df.columns:
        df["total_fights"] = df.get("wins", 0) + df.get("losses", 0) + df.get("draws", 0)

    rate_cols = [c for c in
                 ["str_acc", "str_def", "td_acc", "td_def", "slpm", "sapm", "td_avg", "sub_avg"]
                 if c in df.columns]
    no_fights = df["total_fights"] == 0
    df.loc[no_fights, rate_cols] = pd.NA
    return df


def get_dataframe() -> pd.DataFrame:
    """Load fighters from cache, or fall back to a fresh scrape if missing."""
    df = _load_cached_df()
    if df is None or df.empty:
        st.warning("No cached data found — running first-time scrape. This may take a few minutes.")
        df = run_scrape()
    return df


def run_scrape() -> pd.DataFrame:
    """Run the scraper with a Streamlit progress bar, handling errors."""
    progress_bar = st.progress(0, text="Scraping ufcstats.com…")

    def _update(done: int, total: int) -> None:
        if total <= 0:
            return
        pct = min(done / total, 1.0)
        progress_bar.progress(pct, text=f"Scraping fighters + fight history… {done}/{total}")

    try:
        with st.spinner("Fetching fighters from ufcstats.com…"):
            df, fights = scraper.scrape_fighters(progress=_update)
        progress_bar.empty()
        _load_cached_df.clear()
        _load_cached_fights.clear()
        _load_cached_events.clear()
        st.success(f"Loaded {len(df)} fighters and {len(fights)} fight rows.")
        return df
    except Exception as exc:  # noqa: BLE001
        progress_bar.empty()
        st.error(f"Scrape failed: {exc}. Falling back to cached data if available.")
        cached = scraper.load_cached()
        if cached is None:
            st.stop()
        return cached


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_sidebar(df: pd.DataFrame) -> tuple[str, int, bool]:
    """Render the sidebar and return (page, min_ufc_fights, active_only)."""
    st.sidebar.markdown(
        "<h1 style='color:#D20A0A;margin-bottom:0;'>🥊 UFC</h1>"
        "<p style='color:#BBB;margin-top:0;'>Fighter Dashboard</p>",
        unsafe_allow_html=True,
    )

    page = st.sidebar.radio(
        "Navigation",
        [
            "Fighter Explorer",
            "Fighter Comparison",
            "Rankings",
            "Stat Universe",
            "Insights",
        ],
        label_visibility="collapsed",
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Data filter**")

    # Prefer UFC-only fight count (from fight history) over total MMA career
    # (from the listing page). Fall back to total_fights only if fight
    # history isn't cached yet.
    has_ufc_count = (
        "ufc_fights_counted" in df.columns
        and df["ufc_fights_counted"].notna().any()
    )
    filter_col = "ufc_fights_counted" if has_ufc_count else "total_fights"
    filter_label = "Min. UFC fights" if has_ufc_count else "Min. fights (total MMA — refresh for UFC-only)"
    max_fights = int(pd.to_numeric(df[filter_col], errors="coerce").max() or 30) if filter_col in df.columns else 30
    min_ufc_fights = st.sidebar.slider(
        filter_label,
        min_value=0,
        max_value=max(max_fights, 1),
        value=5,
        help=(
            "Filters by actual UFC-only fight count (length of the fight-history "
            "rows). Raise this to remove the 0/50/100% small-sample noise from "
            "stats like TD defense %." if has_ufc_count
            else "Fight history not loaded — slider currently uses total MMA career. "
                 "Click **Refresh data** to enable UFC-only filtering."
        ),
    )

    active_available = "is_active" in df.columns and df["is_active"].notna().any()
    active_only = st.sidebar.checkbox(
        "Active fighters only (last fight ≤ 2y)",
        value=False,
        disabled=not active_available,
        help=(
            "Requires fight history. Run a refresh once to populate it." if not active_available
            else "Filters out fighters who haven't competed in the last two years."
        ),
    )

    mask = pd.Series(True, index=df.index)
    if filter_col in df.columns:
        col_numeric = pd.to_numeric(df[filter_col], errors="coerce").fillna(0)
        mask &= col_numeric >= min_ufc_fights
    if active_only and active_available:
        mask &= df["is_active"].fillna(False).astype(bool)
    filtered_count = int(mask.sum())
    st.sidebar.caption(f"{filtered_count} of {len(df)} fighters match")

    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Refresh data (re-scrape)"):
        run_scrape()
        st.rerun()

    fights_loaded = scraper.FIGHTS_CSV_PATH.exists()
    if not fights_loaded:
        st.sidebar.warning(
            "Fight history not cached — some features are limited. "
            "Click **Refresh data** to scrape it (adds ~3-5 min)."
        )

    st.sidebar.caption("Source: ufcstats.com")
    return page, min_ufc_fights, active_only


def apply_global_filter(
    df: pd.DataFrame,
    min_ufc_fights: int,
    active_only: bool = False,
) -> pd.DataFrame:
    """Apply the sidebar UFC-fights + activity filters to ``df``."""
    if df is None or df.empty:
        return df
    has_ufc_count = (
        "ufc_fights_counted" in df.columns
        and df["ufc_fights_counted"].notna().any()
    )
    filter_col = "ufc_fights_counted" if has_ufc_count else "total_fights"
    mask = pd.Series(True, index=df.index)
    if filter_col in df.columns:
        col_numeric = pd.to_numeric(df[filter_col], errors="coerce").fillna(0)
        mask &= col_numeric >= min_ufc_fights
    if active_only and "is_active" in df.columns:
        mask &= df["is_active"].fillna(False).astype(bool)
    return df[mask].copy()


# ---------------------------------------------------------------------------
# Page 1 — Fighter Explorer
# ---------------------------------------------------------------------------

def _fmt(value, suffix: str = "") -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)) or value == "":
        return "—"
    if isinstance(value, float):
        return f"{value:.2f}{suffix}"
    return f"{value}{suffix}"


def render_fighter_card(fighter: pd.Series) -> None:
    """Render the styled profile card for a single fighter."""
    nickname = fighter.get("nickname") or ""
    nickname_html = (
        f'<div class="nickname">"{nickname}"</div>' if nickname else ""
    )
    st.markdown(
        f"""
        <div class="fighter-card">
            <h2>{fighter.get('name', 'Unknown')}</h2>
            {nickname_html}
            <p><strong>Record:</strong>
               <span class="win">{int(fighter.get('wins', 0))}W</span> -
               <span class="lose">{int(fighter.get('losses', 0))}L</span> -
               <span class="tie">{int(fighter.get('draws', 0))}D</span>
            </p>
            <p><strong>Style:</strong> {_fmt(fighter.get('stance'))} &nbsp;|&nbsp;
               <strong>Weight class:</strong> {_fmt(fighter.get('weight_class'))}</p>
            <p><strong>Height:</strong> {_fmt(fighter.get('height'))} &nbsp;|&nbsp;
               <strong>Weight:</strong> {_fmt(fighter.get('weight'))} &nbsp;|&nbsp;
               <strong>Reach:</strong> {_fmt(fighter.get('reach'))}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_fighter_explorer(df: pd.DataFrame) -> None:
    """Page 1 — single-fighter profile + stat charts + recent fights."""
    st.title("Fighter Explorer")
    st.caption("Pick any fighter to see their profile, career averages, and recent fight history.")

    names = df["name"].dropna().sort_values().unique().tolist()
    default_idx = names.index("Jon Jones") if "Jon Jones" in names else 0
    selected = st.selectbox("Search fighter", names, index=default_idx)

    fighter = df[df["name"] == selected].iloc[0]

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        render_fighter_card(fighter)
    with col2:
        st.metric("SLpM", _fmt(fighter.get("slpm")))
        st.metric("Str. Acc.", _fmt(fighter.get("str_acc"), "%"))
        st.metric("KO win %", _fmt(fighter.get("ko_rate"), "%"))
    with col3:
        st.metric("TD Avg.", _fmt(fighter.get("td_avg")))
        st.metric("TD Def.", _fmt(fighter.get("td_def"), "%"))
        st.metric("SUB win %", _fmt(fighter.get("sub_rate"), "%"))

    streak_col, last_col, active_col = st.columns(3)
    with streak_col:
        ws = fighter.get("win_streak") or 0
        ls = fighter.get("loss_streak") or 0
        if ws:
            st.metric("Current form", f"W{int(ws)}")
        elif ls:
            st.metric("Current form", f"L{int(ls)}")
        else:
            st.metric("Current form", "—")
    with last_col:
        last_dt = fighter.get("last_fight_date")
        last_str = "—"
        if last_dt and not (isinstance(last_dt, float) and pd.isna(last_dt)):
            try:
                last_str = pd.to_datetime(last_dt).date().isoformat()
            except Exception:  # noqa: BLE001
                last_str = str(last_dt)
        st.metric("Last fight", last_str)
    with active_col:
        is_champ = bool(fighter.get("is_champion", False))
        st.metric("Champion", "🏆 Yes" if is_champ else "—")

    st.markdown("### Career stats")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(charts.fighter_striking_bar(fighter), use_container_width=True)
    with c2:
        st.plotly_chart(charts.fighter_grappling_bar(fighter), use_container_width=True)

    st.markdown("### Recent fights")
    fights = _load_cached_fights()
    if fights is None or fights.empty:
        st.info(
            "Fight history not loaded — click **🔄 Refresh data** in the sidebar "
            "to scrape per-fight rows (one-time cost, ~3-5 minutes)."
        )
    else:
        own = fights[fights["fighter_url"] == fighter.get("url")].copy()
        if own.empty:
            st.info("No fight history found for this fighter.")
        else:
            own = own.sort_values("event_date_parsed", ascending=False, na_position="last")
            recent = own.head(5)[
                ["result", "opponent", "method", "method_detail", "round", "time", "event", "event_date"]
            ].rename(columns={
                "result": "Result",
                "opponent": "Opponent",
                "method": "Method",
                "method_detail": "Detail",
                "round": "Rd",
                "time": "Time",
                "event": "Event",
                "event_date": "Date",
            })
            st.dataframe(recent.reset_index(drop=True), use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Page 2 — Fighter Comparison
# ---------------------------------------------------------------------------

COMPARE_STATS: list[tuple[str, str, bool]] = [
    ("slpm", "SLpM", True),
    ("str_acc", "Str. Acc. %", True),
    ("sapm", "SApM (strikes absorbed)", False),
    ("str_def", "Str. Def. %", True),
    ("td_avg", "TD Avg.", True),
    ("td_acc", "TD Acc. %", True),
    ("td_def", "TD Def. %", True),
    ("sub_avg", "Sub. Avg.", True),
    ("wins", "Wins", True),
    ("losses", "Losses", False),
]


def _winner_class(winner: str, side: str) -> str:
    if winner == "tie":
        return "tie"
    if winner == side:
        return "win"
    return "lose"


def page_fighter_comparison(df: pd.DataFrame) -> None:
    """Page 2 — multi-fighter comparison (2 to 5) with H2H lookup."""
    st.title("Fighter Comparison")
    st.caption("Pick 2 to 5 fighters to overlay their stat profiles.")

    names = df["name"].dropna().sort_values().unique().tolist()
    if len(names) < 2:
        st.warning("Need at least two fighters in the dataset.")
        return

    default_picks = [n for n in ("Jon Jones", "Stipe Miocic") if n in names]
    if len(default_picks) < 2 and len(names) >= 2:
        default_picks = names[:2]

    picks = st.multiselect(
        "Fighters",
        options=names,
        default=default_picks,
        max_selections=5,
        key="cmp_picks",
    )
    if len(picks) < 2:
        st.warning("Pick at least two fighters.")
        return

    fighters = [df[df["name"] == n].iloc[0] for n in picks]

    st.plotly_chart(charts.multi_radar(fighters), use_container_width=True)

    st.markdown("### Stat-by-stat")
    # Header row: stat name + one column per fighter
    cols = st.columns([2] + [2] * len(fighters))
    cols[0].markdown("**Stat**")
    for i, f in enumerate(fighters):
        cols[i + 1].markdown(f"**{f['name']}**")

    for col, label, higher_better in COMPARE_STATS:
        values: list[float | None] = []
        for f in fighters:
            v = f.get(col)
            try:
                values.append(float(v) if v is not None and not pd.isna(v) else None)
            except (TypeError, ValueError):
                values.append(None)

        present = [v for v in values if v is not None]
        if not present:
            best = None
        else:
            best = max(present) if higher_better else min(present)

        cols = st.columns([2] + [2] * len(fighters))
        cols[0].markdown(
            f"<div class='stat-name'>{label}</div>", unsafe_allow_html=True
        )
        for i, v in enumerate(values):
            if v is None:
                text, cls = "—", "tie"
            else:
                text = f"{v:.2f}"
                cls = "win" if best is not None and v == best else "lose"
                # ties shouldn't all be marked win — if best appears more than once
                if best is not None and values.count(best) > 1:
                    cls = "tie"
            cols[i + 1].markdown(
                f"<div class='val {cls}'>{text}</div>", unsafe_allow_html=True
            )

    st.markdown("### Head-to-Head")
    fights = _load_cached_fights()
    if fights is None or fights.empty:
        st.info("Fight history not loaded — click **🔄 Refresh data** in the sidebar.")
        return

    h2h_rows = []
    picked_urls = {f.get("url") for f in fighters}
    for a in fighters:
        own_fights = fights[fights["fighter_url"] == a.get("url")]
        for _, fight in own_fights.iterrows():
            for b in fighters:
                if b.get("name") == a.get("name"):
                    continue
                if fight.get("opponent", "").strip().lower() == b.get("name", "").strip().lower():
                    h2h_rows.append({
                        "Winner side": a["name"] if str(fight.get("result")).lower() in {"win", "w"} else b["name"],
                        "Opponent side": b["name"] if str(fight.get("result")).lower() in {"win", "w"} else a["name"],
                        "Method": fight.get("method"),
                        "Round": fight.get("round"),
                        "Time": fight.get("time"),
                        "Event": fight.get("event"),
                        "Date": fight.get("event_date"),
                    })

    if h2h_rows:
        # Dedupe (each fight appears from both fighters' perspectives)
        h2h_df = pd.DataFrame(h2h_rows).drop_duplicates(subset=["Event", "Date"])
        st.dataframe(h2h_df.reset_index(drop=True), use_container_width=True, hide_index=True)
    else:
        st.info("No previous meetings between these fighters on record.")


# ---------------------------------------------------------------------------
# Page 3 — Rankings / Leaderboard
# ---------------------------------------------------------------------------

NUMERIC_STAT_LABELS = {
    # Record
    "wins": "Wins",
    "losses": "Losses",
    "ufc_fights_counted": "UFC fights",
    # Career averages
    "slpm": "SLpM",
    "str_acc": "Str. Acc. %",
    "sapm": "SApM",
    "str_def": "Str. Def. %",
    "td_avg": "TD Avg.",
    "td_acc": "TD Acc. %",
    "td_def": "TD Def. %",
    "sub_avg": "Sub. Avg.",
    # Win-method counts
    "ko_wins": "KO wins",
    "tko_wins": "TKO wins",
    "sub_wins": "SUB wins",
    "dec_wins": "DEC wins",
    "finish_wins": "Finish wins (KO+TKO+SUB)",
    # Win-method rates
    "ko_rate": "KO/TKO win %",
    "sub_rate": "SUB win %",
    "dec_rate": "DEC win %",
    "finish_rate": "Finish win %",
    # Loss-method counts + rate
    "ko_losses": "KO losses",
    "tko_losses": "TKO losses",
    "sub_losses": "SUB losses",
    "dec_losses": "DEC losses",
    "finished_losses": "Times finished",
    "finished_loss_rate": "Finished loss %",
    # Streaks
    "win_streak": "Current win streak",
    "loss_streak": "Current loss streak",
    "max_win_streak": "Highest win streak (UFC)",
    "max_loss_streak": "Highest loss streak (UFC)",
    # Title
    "title_fights": "Title fights",
    "title_wins": "Title wins",
    "title_losses": "Title losses",
    "title_defenses": "Title defenses",
    # Pace
    "avg_fight_seconds": "Avg. fight time (sec)",
    "avg_round_ended": "Avg. round ended",
}


def page_rankings(df: pd.DataFrame) -> None:
    """Page 3 — filterable, sortable leaderboard with top-10 charts."""
    st.title("Rankings & Leaderboards")
    st.caption("Use the **Min. UFC fights** slider in the sidebar to filter out small-sample noise.")

    weight_classes = ["All"] + sorted(
        c for c in df["weight_class"].dropna().unique().tolist() if c != "Unknown"
    )
    col_wc, col_search = st.columns([1, 2])
    with col_wc:
        wc = st.selectbox("Weight class", weight_classes)
    with col_search:
        name_query = st.text_input(
            "🔍 Search fighter",
            value="",
            placeholder="Type part of a name…",
            key="rankings_search",
        )

    subset = df.copy()
    if wc != "All":
        subset = subset[subset["weight_class"] == wc]
    if name_query.strip():
        subset = subset[subset["name"].str.contains(name_query.strip(), case=False, na=False)]

    sortable = [k for k in NUMERIC_STAT_LABELS.keys() if k in subset.columns]
    sort_by = st.selectbox(
        "Sort by", sortable,
        format_func=lambda k: NUMERIC_STAT_LABELS[k],
    )
    ascending = st.checkbox("Ascending", value=False)

    base_cols = ["name", "weight_class", "stance"]
    available = [c for c in NUMERIC_STAT_LABELS.keys() if c in subset.columns]
    cols = [c for c in base_cols if c in subset.columns] + [
        c for c in available if c not in base_cols
    ]
    display = subset[cols].sort_values(
        sort_by, ascending=ascending, na_position="last"
    )

    st.dataframe(display.reset_index(drop=True), use_container_width=True, height=460)
    st.download_button(
        "⬇ Download filtered CSV",
        data=display.to_csv(index=False).encode("utf-8"),
        file_name=f"ufc_rankings_{wc.replace(' ', '_').lower()}_{sort_by}.csv",
        mime="text/csv",
    )

    st.markdown("### Top 10 leaderboards")
    cat = st.selectbox(
        "Category",
        ["str_def", "td_def", "td_acc", "slpm", "sub_avg", "td_avg", "str_acc"],
        format_func=lambda k: NUMERIC_STAT_LABELS[k],
    )
    st.plotly_chart(
        charts.top_n_bar(subset, cat, NUMERIC_STAT_LABELS[cat]),
        use_container_width=True,
    )


# ---------------------------------------------------------------------------
# Page 4 — Stat Universe (clickable scatter of all fighters)
# ---------------------------------------------------------------------------

def page_stat_universe(df: pd.DataFrame) -> None:
    """
    Page 4 — the "all fighters in one graph" view.

    Pick any X stat and any Y stat — every fighter appears as a point
    on that XY plane. Click any point to open an inline info panel.
    """
    st.title("Stat Universe")
    st.caption(
        "Plot every UFC fighter on an XY chart. Pick any metric for each axis, "
        "then click a point to inspect that fighter."
    )

    stat_keys = list(NUMERIC_STAT_LABELS.keys())

    col_x, col_y, col_color = st.columns(3)
    with col_x:
        x_stat = st.selectbox(
            "X axis",
            stat_keys,
            index=stat_keys.index("slpm"),
            format_func=lambda k: NUMERIC_STAT_LABELS[k],
            key="universe_x",
        )
    with col_y:
        y_stat = st.selectbox(
            "Y axis",
            stat_keys,
            index=stat_keys.index("td_def"),
            format_func=lambda k: NUMERIC_STAT_LABELS[k],
            key="universe_y",
        )
    with col_color:
        color_opts = {
            "weight_class": "Weight class",
            "stance": "Stance",
            "(none)": "None",
        }
        color_by = st.selectbox(
            "Color by",
            list(color_opts.keys()),
            format_func=lambda k: color_opts[k],
            key="universe_color",
        )

    col_wc, col_size = st.columns(2)
    with col_wc:
        weight_classes = ["All"] + sorted(
            c for c in df["weight_class"].dropna().unique().tolist() if c != "Unknown"
        )
        wc = st.selectbox("Weight class filter", weight_classes, key="universe_wc")
    with col_size:
        size_opts = {"(uniform)": "Uniform size", **NUMERIC_STAT_LABELS}
        size_by = st.selectbox(
            "Bubble size by",
            list(size_opts.keys()),
            format_func=lambda k: size_opts[k],
            key="universe_size",
        )

    col_zscore, col_champs, col_trend = st.columns(3)
    with col_zscore:
        z_score = st.checkbox(
            "Normalize within weight class (z-score)",
            value=False,
            help=(
                "A flyweight's 4 SLpM ≠ a heavyweight's 4 SLpM. Toggling this "
                "z-scores each axis against same-division peers so divisions "
                "are comparable."
            ),
        )
    with col_champs:
        highlight_champs = st.checkbox(
            "Highlight champions 🏆",
            value=False,
            disabled="is_champion" not in df.columns,
        )
    with col_trend:
        show_trendline = st.checkbox(
            "Show OLS trendline",
            value=False,
            help=(
                "Fits a least-squares line through every visible point and "
                "shows the equation + R² in the legend. Useful for spotting "
                "stat correlations at a glance (e.g. does TD Avg predict SLpM?)."
            ),
        )

    st.caption("Use the **Min. UFC fights** slider in the sidebar to filter out small-sample outliers (the 0% / 50% / 100% spikes).")

    subset = df.copy()
    if wc != "All":
        subset = subset[subset["weight_class"] == wc]

    if subset.dropna(subset=[x_stat, y_stat]).empty:
        st.warning("No fighters match this filter with values for both selected stats.")
        return

    # Searchable highlight — picks come from the full df, not the filtered
    # subset, so a search can surface a fighter even if the sidebar filter
    # would otherwise hide them.
    all_names = sorted(df["name"].dropna().unique().tolist())
    highlight_names = st.multiselect(
        "🔍 Search fighter(s) to highlight on the chart",
        options=all_names,
        default=[],
        placeholder="Type a name… e.g. Jon Jones, Khabib Nurmagomedov",
        key="universe_search",
    )

    if highlight_names:
        missing = set(highlight_names) - set(subset["name"])
        if missing:
            extras = df[df["name"].isin(missing)]
            subset = pd.concat([subset, extras], ignore_index=True)
            st.caption(
                f"Showing {len(missing)} searched fighter(s) below the **Min. UFC fights** cutoff."
            )

    # Champion overlay → append champion names to highlight set
    if highlight_champs and "is_champion" in subset.columns:
        champ_names = subset[subset["is_champion"].fillna(False)]["name"].dropna().tolist()
        highlight_names = list(dict.fromkeys(highlight_names + champ_names))

    plot_df = subset.copy()
    x_label = NUMERIC_STAT_LABELS[x_stat]
    y_label = NUMERIC_STAT_LABELS[y_stat]
    x_col, y_col = x_stat, y_stat

    if z_score and "weight_class" in plot_df.columns:
        plot_df["_zx"] = derived.z_score_by_weight_class(plot_df, x_stat)
        plot_df["_zy"] = derived.z_score_by_weight_class(plot_df, y_stat)
        x_col, y_col = "_zx", "_zy"
        x_label = f"{NUMERIC_STAT_LABELS[x_stat]} (z within class)"
        y_label = f"{NUMERIC_STAT_LABELS[y_stat]} (z within class)"

    fig = charts.xy_fighters_scatter(
        plot_df,
        x_stat=x_col,
        y_stat=y_col,
        x_label=x_label,
        y_label=y_label,
        color_by=None if color_by == "(none)" else color_by,
        size_by=None if size_by == "(uniform)" else size_by,
        highlight_names=highlight_names,
        show_trendline=show_trendline,
    )

    event = st.plotly_chart(
        fig,
        use_container_width=True,
        key=f"universe_xy_{x_stat}_{y_stat}_{wc}_{color_by}_{size_by}_{len(highlight_names)}_{z_score}_{highlight_champs}_{show_trendline}",
        on_select="rerun",
        selection_mode=("points",),
    )

    selected_name: str | None = None
    try:
        points = event["selection"]["points"]  # type: ignore[index]
        if points:
            selected_name = points[0]["customdata"][0]
    except (KeyError, TypeError, IndexError):
        selected_name = None

    st.markdown("### Fighter detail")
    if selected_name is None:
        st.info("Click any point on the scatter above to see fighter details here.")
    else:
        match = subset[subset["name"] == selected_name]
        if match.empty:
            st.warning("Selected fighter not found in current filter.")
        else:
            fighter = match.iloc[0]
            info_col, stat_col = st.columns([2, 1])
            with info_col:
                render_fighter_card(fighter)
            with stat_col:
                st.metric(NUMERIC_STAT_LABELS[x_stat], _fmt(fighter.get(x_stat)))
                st.metric(NUMERIC_STAT_LABELS[y_stat], _fmt(fighter.get(y_stat)))
                st.metric(
                    "Record",
                    f"{int(fighter.get('wins', 0))}-{int(fighter.get('losses', 0))}-{int(fighter.get('draws', 0))}",
                )

    st.markdown("### Distributions")
    d1, d2 = st.columns(2)
    with d1:
        st.plotly_chart(
            charts.stat_distribution(subset, x_stat, NUMERIC_STAT_LABELS[x_stat]),
            use_container_width=True,
        )
    with d2:
        st.plotly_chart(
            charts.stat_distribution(subset, y_stat, NUMERIC_STAT_LABELS[y_stat]),
            use_container_width=True,
        )


# ---------------------------------------------------------------------------
# Page 5 — Insights
# ---------------------------------------------------------------------------

def page_insights(df: pd.DataFrame) -> None:
    """Page 5 — correlation heatmap + categorical breakdowns."""
    st.title("Insights")
    st.caption(
        "Cross-stat correlations and categorical breakdowns. Sidebar filters "
        "(min-fights, active-only) apply."
    )

    st.markdown("### Stat correlations")
    st.caption(
        "Red cells = positive correlation, blue = negative. "
        "Useful for spotting style trade-offs (e.g. high TD Avg vs SLpM)."
    )
    st.plotly_chart(
        charts.correlation_heatmap(df, NUMERIC_STAT_LABELS),
        use_container_width=True,
    )

    st.markdown("### Group breakdowns")
    col_group, col_stat = st.columns(2)
    with col_group:
        group_opts = {"stance": "Stance", "weight_class": "Weight class"}
        group_col = st.selectbox(
            "Group by",
            list(group_opts.keys()),
            format_func=lambda k: group_opts[k],
        )
    with col_stat:
        available = [k for k in NUMERIC_STAT_LABELS.keys() if k in df.columns]
        stat = st.selectbox(
            "Stat",
            available,
            index=available.index("slpm") if "slpm" in available else 0,
            format_func=lambda k: NUMERIC_STAT_LABELS[k],
            key="insights_stat",
        )

    st.plotly_chart(
        charts.group_mean_bar(
            df, group_col, stat,
            NUMERIC_STAT_LABELS[stat], group_opts[group_col],
        ),
        use_container_width=True,
    )

    if "is_champion" in df.columns:
        st.markdown("### Champions vs the field")
        champs = df[df["is_champion"].fillna(False)]
        rest = df[~df["is_champion"].fillna(False)]
        rows = []
        for col, label in NUMERIC_STAT_LABELS.items():
            if col not in df.columns:
                continue
            c_mean = pd.to_numeric(champs[col], errors="coerce").mean()
            r_mean = pd.to_numeric(rest[col], errors="coerce").mean()
            if pd.notna(c_mean) and pd.notna(r_mean):
                rows.append({
                    "Stat": label,
                    "Champions avg": round(c_mean, 2),
                    "Rest avg": round(r_mean, 2),
                    "Δ": round(c_mean - r_mean, 2),
                })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Streamlit entry point."""
    inject_theme()

    df = get_dataframe()
    page, min_ufc_fights, active_only = render_sidebar(df)

    # Explorer / Comparison let you pick *any* fighter by name regardless of
    # career length — the sample-size filter only matters for distributions
    # and leaderboards, so those two pages keep the unfiltered df.
    chart_df = apply_global_filter(df, min_ufc_fights, active_only)

    if page == "Fighter Explorer":
        page_fighter_explorer(df)
    elif page == "Fighter Comparison":
        page_fighter_comparison(df)
    elif page == "Rankings":
        page_rankings(chart_df)
    elif page == "Stat Universe":
        page_stat_universe(chart_df)
    elif page == "Insights":
        page_insights(chart_df)


if __name__ == "__main__":
    main()
