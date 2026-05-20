from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

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


CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

:root {
    --bg-base: #0A0D14;
    --bg-surface: #131822;
    --bg-surface-2: #1B2230;
    --bg-elev: #232B3A;
    --border-subtle: rgba(255,255,255,0.06);
    --border-strong: rgba(255,255,255,0.12);
    --accent: #EF4444;
    --accent-deep: #DC2626;
    --accent-glow: rgba(239,68,68,0.18);
    --gold: #F59E0B;
    --emerald: #10B981;
    --rose: #F43F5E;
    --sky: #38BDF8;
    --text-primary: #F4F4F5;
    --text-secondary: #A1A1AA;
    --text-muted: #71717A;
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.4);
    --shadow-md: 0 4px 12px rgba(0,0,0,0.35);
    --shadow-glow: 0 0 24px rgba(239,68,68,0.12);
}

html, body, .stApp, [class*="st-"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    font-feature-settings: 'cv11', 'ss01', 'ss03';
    letter-spacing: -0.01em;
}

.stApp {
    background:
        radial-gradient(ellipse 80% 50% at 50% -20%, rgba(239,68,68,0.08), transparent 60%),
        radial-gradient(ellipse 60% 40% at 100% 100%, rgba(56,189,248,0.05), transparent 50%),
        var(--bg-base);
    color: var(--text-primary);
}

.block-container {
    padding-top: 2.5rem !important;
    padding-bottom: 4rem !important;
    max-width: 1400px;
}

h1, h2, h3, h4, h5, h6 {
    color: var(--text-primary) !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
}

h1 { font-size: 2.25rem !important; line-height: 1.15 !important; }
h2 { font-size: 1.5rem !important; }
h3 { font-size: 1.15rem !important; font-weight: 600 !important; }

p, label, .stCaption, [data-testid="stCaptionContainer"] {
    color: var(--text-secondary) !important;
    font-size: 0.92rem;
    line-height: 1.55;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(19,24,34,0.95) 0%, rgba(10,13,20,0.98) 100%);
    border-right: 1px solid var(--border-subtle);
    backdrop-filter: blur(20px);
}
section[data-testid="stSidebar"] > div { padding-top: 1.5rem; }
section[data-testid="stSidebar"] hr {
    border: none; border-top: 1px solid var(--border-subtle); margin: 1rem 0 !important;
}

.brand-mark {
    display: flex; align-items: center; gap: 10px;
    padding: 4px 8px 18px;
}
.brand-mark .logo {
    width: 38px; height: 38px;
    background: linear-gradient(135deg, var(--accent), var(--accent-deep));
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px;
    box-shadow: 0 4px 12px var(--accent-glow);
}
.brand-mark .label {
    display: flex; flex-direction: column; line-height: 1.1;
}
.brand-mark .label strong { color: var(--text-primary); font-weight: 700; font-size: 1.05rem; letter-spacing: -0.02em;}
.brand-mark .label span { color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em; }

div[data-testid="stRadio"] > div { gap: 4px; }
div[data-testid="stRadio"] label {
    background: transparent;
    border-radius: var(--radius-sm);
    padding: 8px 12px;
    transition: all 160ms ease;
    border: 1px solid transparent;
    cursor: pointer;
}
div[data-testid="stRadio"] label:hover {
    background: var(--bg-surface);
    border-color: var(--border-subtle);
}
div[data-testid="stRadio"] label[data-checked="true"] {
    background: linear-gradient(135deg, rgba(239,68,68,0.12), rgba(239,68,68,0.04));
    border-color: rgba(239,68,68,0.35);
    box-shadow: inset 2px 0 0 var(--accent);
}
div[data-testid="stRadio"] label p { color: var(--text-primary) !important; font-weight: 500; margin: 0 !important; }

.stButton > button {
    background: linear-gradient(135deg, var(--accent), var(--accent-deep));
    color: var(--text-primary);
    border: none;
    border-radius: var(--radius-sm);
    padding: 0.6rem 1rem;
    font-weight: 600;
    font-size: 0.9rem;
    letter-spacing: -0.005em;
    box-shadow: 0 1px 0 rgba(255,255,255,0.08) inset, 0 6px 16px rgba(239,68,68,0.25);
    transition: transform 120ms ease, box-shadow 200ms ease, filter 200ms ease;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 1px 0 rgba(255,255,255,0.12) inset, 0 10px 22px rgba(239,68,68,0.32);
    filter: brightness(1.05);
}
.stButton > button:active { transform: translateY(0); }

.stDownloadButton > button {
    background: var(--bg-surface-2);
    color: var(--text-primary);
    border: 1px solid var(--border-strong);
    border-radius: var(--radius-sm);
    font-weight: 500;
}
.stDownloadButton > button:hover { background: var(--bg-elev); }

div[data-testid="stMetric"] {
    background: linear-gradient(180deg, var(--bg-surface), var(--bg-surface-2));
    padding: 16px 18px;
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-sm);
    transition: border-color 200ms ease, transform 200ms ease;
}
div[data-testid="stMetric"]:hover {
    border-color: rgba(239,68,68,0.35);
    transform: translateY(-1px);
}
div[data-testid="stMetric"] label {
    color: var(--text-muted) !important;
    font-size: 0.72rem !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 600 !important;
}
div[data-testid="stMetricValue"] {
    color: var(--text-primary) !important;
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em;
    margin-top: 6px;
}

div[data-testid="stSelectbox"] > div > div,
div[data-testid="stMultiSelect"] > div > div,
div[data-testid="stTextInput"] > div > div,
div[data-testid="stNumberInput"] > div > div {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-sm) !important;
    transition: border-color 160ms ease, box-shadow 160ms ease;
}
div[data-testid="stSelectbox"] > div > div:hover,
div[data-testid="stMultiSelect"] > div > div:hover,
div[data-testid="stTextInput"] > div > div:hover {
    border-color: var(--border-strong) !important;
}
div[data-testid="stSelectbox"] > div > div:focus-within,
div[data-testid="stMultiSelect"] > div > div:focus-within,
div[data-testid="stTextInput"] > div > div:focus-within {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--accent-glow) !important;
}

div[data-testid="stSlider"] > div > div > div > div {
    background: linear-gradient(90deg, var(--accent), var(--accent-deep)) !important;
}
div[data-testid="stSlider"] [role="slider"] {
    background: white !important;
    border: 3px solid var(--accent) !important;
    box-shadow: 0 0 0 4px rgba(239,68,68,0.18) !important;
}

div[data-testid="stCheckbox"] label {
    color: var(--text-primary) !important;
    font-weight: 500;
}

div[data-testid="stDataFrame"] {
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    overflow: hidden;
    background: var(--bg-surface);
}

.fighter-card {
    background: linear-gradient(135deg, var(--bg-surface) 0%, var(--bg-surface-2) 100%);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    padding: 24px 28px;
    margin-bottom: 8px;
    box-shadow: var(--shadow-md);
    position: relative;
    overflow: hidden;
}
.fighter-card::before {
    content: ""; position: absolute; top: 0; left: 0;
    width: 4px; height: 100%;
    background: linear-gradient(180deg, var(--accent), var(--accent-deep));
}
.fighter-card .name-row {
    display: flex; align-items: center; gap: 12px; margin-bottom: 6px;
}
.fighter-card h2 {
    margin: 0 !important;
    font-size: 1.65rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.025em !important;
}
.fighter-card .nickname {
    color: var(--text-muted); font-style: italic;
    font-size: 0.95rem; margin-bottom: 16px;
}
.fighter-card .meta { color: var(--text-secondary); font-size: 0.88rem; margin: 6px 0; }
.fighter-card .meta strong { color: var(--text-primary); font-weight: 600; }

.champion-badge {
    display: inline-flex; align-items: center; gap: 5px;
    background: linear-gradient(135deg, var(--gold), #D97706);
    color: #1A1A1A;
    padding: 3px 9px;
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    box-shadow: 0 2px 8px rgba(245,158,11,0.35);
}

.record-chip { display: inline-flex; align-items: center; gap: 4px; padding: 4px 10px; border-radius: 999px; font-size: 0.85rem; font-weight: 600; }
.record-w { background: rgba(16,185,129,0.12); color: var(--emerald); border: 1px solid rgba(16,185,129,0.25); }
.record-l { background: rgba(244,63,94,0.12); color: var(--rose); border: 1px solid rgba(244,63,94,0.25); }
.record-d { background: rgba(161,161,170,0.12); color: var(--text-secondary); border: 1px solid rgba(161,161,170,0.25); }

.val { text-align: center; font-weight: 600; font-size: 0.95rem; padding: 6px 10px; border-radius: var(--radius-sm); }
.stat-name { color: var(--text-secondary); text-align: center; font-size: 0.88rem; padding: 6px 10px; }
.win  { color: var(--emerald); background: rgba(16,185,129,0.08); }
.lose { color: var(--rose); background: rgba(244,63,94,0.08); }
.tie  { color: var(--text-muted); }

.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid var(--border-subtle); }
.stTabs [data-baseweb="tab"] {
    background: transparent;
    color: var(--text-muted);
    border-radius: 0;
    padding: 10px 16px;
    font-weight: 500;
}
.stTabs [aria-selected="true"] {
    color: var(--text-primary) !important;
    border-bottom: 2px solid var(--accent) !important;
}

.stAlert {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-secondary) !important;
}

.stProgress > div > div > div { background: linear-gradient(90deg, var(--accent), var(--gold)) !important; }

::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: var(--bg-base); }
::-webkit-scrollbar-thumb { background: var(--bg-elev); border-radius: 6px; }
::-webkit-scrollbar-thumb:hover { background: #2D3748; }

.modern-section-title {
    display: flex; align-items: center; gap: 10px;
    margin: 28px 0 14px;
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.015em;
}
.modern-section-title::after {
    content: ""; flex: 1; height: 1px;
    background: linear-gradient(90deg, var(--border-strong), transparent);
}
</style>
"""


def inject_theme() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def _section_title(text: str) -> None:
    st.markdown(f"<div class='modern-section-title'>{text}</div>", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def _load_cached_df() -> pd.DataFrame | None:
    df = scraper.load_cached()
    if df is None or df.empty:
        return df
    df = _clean_dataframe(df)
    fights = scraper.load_cached_fights()
    events = scraper.load_cached_events()
    return derived.enrich_with_fight_data(df, fights, events)


@st.cache_data(show_spinner=False)
def _load_cached_fights() -> pd.DataFrame | None:
    return scraper.load_cached_fights()


@st.cache_data(show_spinner=False)
def _load_cached_events() -> pd.DataFrame | None:
    return scraper.load_cached_events()


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
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
    df = _load_cached_df()
    if df is None or df.empty:
        st.warning("No cached data found — running first-time scrape. This may take a few minutes.")
        df = run_scrape()
    return df


def run_scrape() -> pd.DataFrame:
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
    except Exception as exc:
        progress_bar.empty()
        st.error(f"Scrape failed: {exc}. Falling back to cached data if available.")
        cached = scraper.load_cached()
        if cached is None:
            st.stop()
        return cached


def render_sidebar(df: pd.DataFrame) -> tuple[str, int, bool]:
    st.sidebar.markdown(
        """
        <div class="brand-mark">
            <div class="logo">🥊</div>
            <div class="label">
                <strong>UFC Dashboard</strong>
                <span>Fighter Analytics</span>
            </div>
        </div>
        """,
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
    st.sidebar.markdown(
        "<div style='color:var(--text-muted);font-size:0.72rem;"
        "text-transform:uppercase;letter-spacing:0.08em;font-weight:600;"
        "margin-bottom:8px;'>Data filter</div>",
        unsafe_allow_html=True,
    )

    has_ufc_count = (
        "ufc_fights_counted" in df.columns
        and df["ufc_fights_counted"].notna().any()
    )
    filter_col = "ufc_fights_counted" if has_ufc_count else "total_fights"
    filter_label = "Min. UFC fights" if has_ufc_count else "Min. fights (total MMA)"
    max_fights = int(pd.to_numeric(df[filter_col], errors="coerce").max() or 30) if filter_col in df.columns else 30
    min_ufc_fights = st.sidebar.slider(
        filter_label,
        min_value=0,
        max_value=max(max_fights, 1),
        value=5,
        help=(
            "Filters by UFC-only completed fights." if has_ufc_count
            else "Fight history not loaded yet — click Refresh data."
        ),
    )

    active_available = "is_active" in df.columns and df["is_active"].notna().any()
    active_only = st.sidebar.checkbox(
        "Active fighters only (≤ 2y)",
        value=False,
        disabled=not active_available,
        help=(
            "Requires fight history." if not active_available
            else "Filters out fighters inactive for over 2 years."
        ),
    )

    mask = pd.Series(True, index=df.index)
    if filter_col in df.columns:
        col_numeric = pd.to_numeric(df[filter_col], errors="coerce").fillna(0)
        mask &= col_numeric >= min_ufc_fights
    if active_only and active_available:
        mask &= df["is_active"].fillna(False).astype(bool)
    filtered_count = int(mask.sum())
    st.sidebar.markdown(
        f"<div style='color:var(--text-muted);font-size:0.78rem;margin-top:4px;'>"
        f"<strong style='color:var(--text-primary);'>{filtered_count}</strong> of "
        f"{len(df)} fighters match</div>",
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Refresh data", use_container_width=True):
        run_scrape()
        st.rerun()

    fights_loaded = scraper.FIGHTS_CSV_PATH.exists()
    if not fights_loaded:
        st.sidebar.info("Fight history not cached. Click Refresh data to scrape (~3-5 min).")

    st.sidebar.markdown(
        "<div style='color:var(--text-muted);font-size:0.7rem;text-align:center;"
        "margin-top:1rem;'>Source: ufcstats.com</div>",
        unsafe_allow_html=True,
    )
    return page, min_ufc_fights, active_only


def apply_global_filter(
    df: pd.DataFrame,
    min_ufc_fights: int,
    active_only: bool = False,
) -> pd.DataFrame:
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


def _fmt(value, suffix: str = "") -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)) or value == "":
        return "—"
    if isinstance(value, float):
        return f"{value:.2f}{suffix}"
    return f"{value}{suffix}"


def render_fighter_card(fighter: pd.Series) -> None:
    nickname = fighter.get("nickname") or ""
    nickname_html = f'<div class="nickname">"{nickname}"</div>' if nickname else ""
    champ_badge = (
        '<span class="champion-badge">🏆 Champion</span>'
        if bool(fighter.get("is_champion", False)) else ""
    )
    wins = int(fighter.get("wins", 0))
    losses = int(fighter.get("losses", 0))
    draws = int(fighter.get("draws", 0))
    st.markdown(
        f"""
        <div class="fighter-card">
            <div class="name-row">
                <h2>{fighter.get('name', 'Unknown')}</h2>
                {champ_badge}
            </div>
            {nickname_html}
            <div style="margin: 12px 0;">
                <span class="record-chip record-w">{wins}W</span>
                <span class="record-chip record-l">{losses}L</span>
                <span class="record-chip record-d">{draws}D</span>
            </div>
            <p class="meta"><strong>Style:</strong> {_fmt(fighter.get('stance'))}
               &nbsp;·&nbsp; <strong>Division:</strong> {_fmt(fighter.get('weight_class'))}</p>
            <p class="meta"><strong>Height:</strong> {_fmt(fighter.get('height'))}
               &nbsp;·&nbsp; <strong>Weight:</strong> {_fmt(fighter.get('weight'))}
               &nbsp;·&nbsp; <strong>Reach:</strong> {_fmt(fighter.get('reach'))}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_fighter_explorer(df: pd.DataFrame) -> None:
    st.title("Fighter Explorer")
    st.caption("Pick any fighter to inspect their profile, career averages, and recent bouts.")

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
        st.metric("KO/TKO win %", _fmt(fighter.get("ko_rate"), "%"))
    with col3:
        st.metric("TD Avg.", _fmt(fighter.get("td_avg")))
        st.metric("TD Def.", _fmt(fighter.get("td_def"), "%"))
        st.metric("SUB win %", _fmt(fighter.get("sub_rate"), "%"))

    streak_col, last_col, peak_col = st.columns(3)
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
            except Exception:
                last_str = str(last_dt)
        st.metric("Last fight", last_str)
    with peak_col:
        peak = fighter.get("max_win_streak")
        st.metric("Peak win streak", _fmt(peak) if peak else "—")

    _section_title("Career stats")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(charts.fighter_striking_bar(fighter), use_container_width=True)
    with c2:
        st.plotly_chart(charts.fighter_grappling_bar(fighter), use_container_width=True)

    _section_title("Recent fights")
    fights = _load_cached_fights()
    if fights is None or fights.empty:
        st.info("Fight history not loaded. Click 🔄 Refresh data in the sidebar.")
    else:
        own = fights[fights["fighter_url"] == fighter.get("url")].copy()
        if own.empty:
            st.info("No fight history found for this fighter.")
        else:
            own = own.sort_values("event_date_parsed", ascending=False, na_position="last")
            recent = own.head(5)[
                ["result", "opponent", "method", "method_detail", "round", "time", "event", "event_date"]
            ].rename(columns={
                "result": "Result", "opponent": "Opponent", "method": "Method",
                "method_detail": "Detail", "round": "Rd", "time": "Time",
                "event": "Event", "event_date": "Date",
            })
            st.dataframe(recent.reset_index(drop=True), use_container_width=True, hide_index=True)


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


def page_fighter_comparison(df: pd.DataFrame) -> None:
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

    _section_title("Stat-by-stat")
    cols = st.columns([2] + [2] * len(fighters))
    cols[0].markdown("<div class='stat-name'><strong>Stat</strong></div>", unsafe_allow_html=True)
    for i, f in enumerate(fighters):
        cols[i + 1].markdown(
            f"<div class='val' style='color:var(--text-primary);'>"
            f"<strong>{f['name']}</strong></div>",
            unsafe_allow_html=True,
        )

    for col, label, higher_better in COMPARE_STATS:
        values: list[float | None] = []
        for f in fighters:
            v = f.get(col)
            try:
                values.append(float(v) if v is not None and not pd.isna(v) else None)
            except (TypeError, ValueError):
                values.append(None)

        present = [v for v in values if v is not None]
        best = (max(present) if higher_better else min(present)) if present else None

        cols = st.columns([2] + [2] * len(fighters))
        cols[0].markdown(f"<div class='stat-name'>{label}</div>", unsafe_allow_html=True)
        for i, v in enumerate(values):
            if v is None:
                text, cls = "—", "tie"
            else:
                text = f"{v:.2f}"
                cls = "win" if best is not None and v == best else "lose"
                if best is not None and values.count(best) > 1:
                    cls = "tie"
            cols[i + 1].markdown(
                f"<div class='val {cls}'>{text}</div>", unsafe_allow_html=True
            )

    _section_title("Head-to-Head")
    fights = _load_cached_fights()
    if fights is None or fights.empty:
        st.info("Fight history not loaded — click 🔄 Refresh data in the sidebar.")
        return

    h2h_rows = []
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
        h2h_df = pd.DataFrame(h2h_rows).drop_duplicates(subset=["Event", "Date"])
        st.dataframe(h2h_df.reset_index(drop=True), use_container_width=True, hide_index=True)
    else:
        st.info("No previous meetings between these fighters on record.")


NUMERIC_STAT_LABELS = {
    "wins": "Wins",
    "losses": "Losses",
    "ufc_fights_counted": "UFC fights",
    "slpm": "SLpM",
    "str_acc": "Str. Acc. %",
    "sapm": "SApM",
    "str_def": "Str. Def. %",
    "td_avg": "TD Avg.",
    "td_acc": "TD Acc. %",
    "td_def": "TD Def. %",
    "sub_avg": "Sub. Avg.",
    "ko_wins": "KO wins",
    "tko_wins": "TKO wins",
    "sub_wins": "SUB wins",
    "dec_wins": "DEC wins",
    "finish_wins": "Finish wins (KO+TKO+SUB)",
    "ko_rate": "KO/TKO win %",
    "sub_rate": "SUB win %",
    "dec_rate": "DEC win %",
    "finish_rate": "Finish win %",
    "ko_losses": "KO losses",
    "tko_losses": "TKO losses",
    "sub_losses": "SUB losses",
    "dec_losses": "DEC losses",
    "finished_losses": "Times finished",
    "finished_loss_rate": "Finished loss %",
    "win_streak": "Current win streak",
    "loss_streak": "Current loss streak",
    "max_win_streak": "Highest win streak (UFC)",
    "max_loss_streak": "Highest loss streak (UFC)",
    "title_fights": "Title fights",
    "title_wins": "Title wins",
    "title_losses": "Title losses",
    "title_defenses": "Title defenses",
    "avg_fight_seconds": "Avg. fight time (sec)",
    "avg_round_ended": "Avg. round ended",
}


def page_rankings(df: pd.DataFrame) -> None:
    st.title("Rankings & Leaderboards")
    st.caption("Filterable, sortable, exportable. Use the sidebar filters for noise reduction.")

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

    st.dataframe(display.reset_index(drop=True), use_container_width=True, height=480)
    st.download_button(
        "⬇  Download filtered CSV",
        data=display.to_csv(index=False).encode("utf-8"),
        file_name=f"ufc_rankings_{wc.replace(' ', '_').lower()}_{sort_by}.csv",
        mime="text/csv",
    )

    _section_title("Top 10 leaderboards")
    cat = st.selectbox(
        "Category",
        ["str_def", "td_def", "td_acc", "slpm", "sub_avg", "td_avg", "str_acc",
         "finish_wins", "ko_wins", "sub_wins", "max_win_streak", "title_defenses"],
        format_func=lambda k: NUMERIC_STAT_LABELS.get(k, k),
    )
    st.plotly_chart(
        charts.top_n_bar(subset, cat, NUMERIC_STAT_LABELS[cat]),
        use_container_width=True,
    )


def page_stat_universe(df: pd.DataFrame) -> None:
    st.title("Stat Universe")
    st.caption("Plot every fighter on an XY chart. Pick any metrics — click any point to inspect.")

    stat_keys = list(NUMERIC_STAT_LABELS.keys())

    col_x, col_y, col_color = st.columns(3)
    with col_x:
        x_stat = st.selectbox(
            "X axis", stat_keys,
            index=stat_keys.index("slpm"),
            format_func=lambda k: NUMERIC_STAT_LABELS[k],
            key="universe_x",
        )
    with col_y:
        y_stat = st.selectbox(
            "Y axis", stat_keys,
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
        z_score = st.checkbox("Normalize within weight class (z-score)", value=False)
    with col_champs:
        highlight_champs = st.checkbox(
            "Highlight champions 🏆", value=False,
            disabled="is_champion" not in df.columns,
        )
    with col_trend:
        show_trendline = st.checkbox("Show trendline", value=False)

    subset = df.copy()
    if wc != "All":
        subset = subset[subset["weight_class"] == wc]

    if subset.dropna(subset=[x_stat, y_stat]).empty:
        st.warning("No fighters match this filter with values for both selected stats.")
        return

    all_names = sorted(df["name"].dropna().unique().tolist())
    highlight_names = st.multiselect(
        "🔍 Search fighter(s) to highlight",
        options=all_names,
        default=[],
        placeholder="Type a name…",
        key="universe_search",
    )

    if highlight_names:
        missing = set(highlight_names) - set(subset["name"])
        if missing:
            extras = df[df["name"].isin(missing)]
            subset = pd.concat([subset, extras], ignore_index=True)
            st.caption(
                f"Showing {len(missing)} searched fighter(s) below the Min. UFC fights cutoff."
            )

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
        points = event["selection"]["points"]
        if points:
            selected_name = points[0]["customdata"][0]
    except (KeyError, TypeError, IndexError):
        selected_name = None

    _section_title("Fighter detail")
    if selected_name is None:
        st.info("Click any point on the scatter to see fighter details.")
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

    _section_title("Distributions")
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


def page_insights(df: pd.DataFrame) -> None:
    st.title("Insights")
    st.caption("Cross-stat correlations and categorical breakdowns.")

    _section_title("Stat correlations")
    st.caption(
        "Red = positive correlation, blue = negative. Spot style trade-offs at a glance."
    )
    st.plotly_chart(
        charts.correlation_heatmap(df, NUMERIC_STAT_LABELS),
        use_container_width=True,
    )

    _section_title("Group breakdowns")
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
        _section_title("Champions vs the field")
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


def main() -> None:
    inject_theme()
    df = get_dataframe()
    page, min_ufc_fights, active_only = render_sidebar(df)
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
