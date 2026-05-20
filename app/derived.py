"""
Post-load enrichment of the fighters DataFrame.

Joins the per-fight history (``data/fights.csv``) onto the fighters table
to derive:

- ``ko_rate``, ``sub_rate``, ``dec_rate`` — share of *wins* by method.
- ``finish_rate`` — KO+SUB share of wins.
- ``win_streak``, ``loss_streak`` — current consecutive run.
- ``last_fight_date`` / ``days_since_last_fight`` / ``is_active``.
- ``is_champion`` — flagged from a curated list of known UFC champions.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd

# Curated set of known UFC champions (current + notable past holders).
# Tagged for the "Highlight champions" overlay on Stat Universe.
KNOWN_CHAMPIONS: set[str] = {
    # Current / recent champions (as of 2026)
    "Jon Jones", "Tom Aspinall", "Alex Pereira", "Magomed Ankalaev",
    "Dricus Du Plessis", "Khamzat Chimaev", "Belal Muhammad", "Jack Della Maddalena",
    "Islam Makhachev", "Ilia Topuria", "Merab Dvalishvili",
    "Alexandre Pantoja", "Valentina Shevchenko", "Zhang Weili",
    "Julianna Pena", "Raquel Pennington", "Kayla Harrison",
    # Notable past champions
    "Khabib Nurmagomedov", "Conor McGregor", "Anderson Silva", "Georges St-Pierre",
    "Daniel Cormier", "Stipe Miocic", "Francis Ngannou", "Israel Adesanya",
    "Kamaru Usman", "Leon Edwards", "Charles Oliveira", "Sean O'Malley",
    "Aljamain Sterling", "Henry Cejudo", "Demetrious Johnson", "TJ Dillashaw",
    "Max Holloway", "Jose Aldo", "Alexander Volkanovski", "Dustin Poirier",
    "Tyron Woodley", "Robert Whittaker", "Sean Strickland", "Glover Teixeira",
    "Jiri Prochazka", "Jan Blachowicz", "Cain Velasquez", "Junior Dos Santos",
    "Fabricio Werdum", "Andrei Arlovski", "Tim Sylvia", "Randy Couture",
    "Chuck Liddell", "Rich Franklin", "Matt Hughes", "BJ Penn",
    "Frankie Edgar", "Benson Henderson", "Anthony Pettis", "Rafael Dos Anjos",
    "Eddie Alvarez", "Tony Ferguson", "Tito Ortiz", "Lyoto Machida",
    "Vitor Belfort", "Mauricio Rua", "Rashad Evans", "Forrest Griffin",
    "Quinton Jackson", "Rampage Jackson", "Holly Holm", "Ronda Rousey",
    "Miesha Tate", "Amanda Nunes", "Carla Esparza", "Joanna Jedrzejczyk",
    "Rose Namajunas", "Jessica Andrade", "Cris Cyborg", "Germaine de Randamie",
    "Nicco Montano", "Brock Lesnar", "Shane Carwin",
}

WIN_FLAGS = {"win"}
LOSS_FLAGS = {"loss"}
DRAW_FLAGS = {"draw"}
NC_FLAGS = {"nc", "no contest"}
# Result strings that represent NON-completed bouts (upcoming, scheduled,
# or otherwise excluded from career stats). Anything in this set is
# filtered out of every aggregation including ufc_fights_counted.
EXCLUDED_RESULTS = {"next", "", "scheduled", "upcoming"}


def _is_completed(result: str) -> bool:
    """True if the result string represents a finished, ranked bout."""
    r = (result or "").strip().lower()
    return r in WIN_FLAGS | LOSS_FLAGS | DRAW_FLAGS | NC_FLAGS


def _classify_method(method: str) -> str:
    """Bucket a raw method string into KO/SUB/DEC/OTHER."""
    if not isinstance(method, str):
        return "OTHER"
    m = method.upper()
    if "KO" in m or "TKO" in m:
        return "KO"
    if "SUB" in m:
        return "SUB"
    if "DEC" in m:
        return "DEC"
    return "OTHER"


# Heuristic split between KO (single decisive blow) and TKO (stoppage /
# accumulation). ufcstats.com lumps them as "KO/TKO" in the method column;
# the detail row hints at which it was. Not 100% accurate — knockouts via
# "Punches" (plural) can technically be either — but matches the common
# usage on highlight reels and rankings sites.
_TKO_DETAIL_KEYWORDS = (
    "PUNCHES", "ELBOWS", "KICKS",
    "DOCTOR", "CORNER", "STOPPAGE", "RETIREMENT",
    "GROUND AND POUND", "GROUND & POUND",
    "STRIKES",
)


def _classify_ko_tko(method: str, detail: str) -> str:
    """Return ``"KO"`` or ``"TKO"`` for a KO/TKO finish, else ``""``."""
    if _classify_method(method) != "KO":
        return ""
    d = (detail or "").upper()
    for kw in _TKO_DETAIL_KEYWORDS:
        if kw in d:
            return "TKO"
    return "KO"


def _current_streak(results: list[str]) -> tuple[int, int]:
    """
    Compute ``(win_streak, loss_streak)`` from a chronologically-ordered
    result list (most recent first). Exactly one of the two will be > 0
    when the latest fight was W or L; both are 0 for draws/NC.
    """
    if not results:
        return 0, 0
    latest = results[0].lower()
    if latest in WIN_FLAGS:
        streak = 0
        for r in results:
            if r.lower() in WIN_FLAGS:
                streak += 1
            else:
                break
        return streak, 0
    if latest in LOSS_FLAGS:
        streak = 0
        for r in results:
            if r.lower() in LOSS_FLAGS:
                streak += 1
            else:
                break
        return 0, streak
    return 0, 0


def _max_streak(results: list[str], target_flags: set[str]) -> int:
    """
    Longest consecutive run of results matching ``target_flags`` anywhere
    in the fighter's history. Order-independent; works on chronological
    or reverse-chronological input.
    """
    longest = current = 0
    for r in results:
        if r.lower() in target_flags:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _fight_time_seconds(time_str: str, round_num: str | int | None) -> int | None:
    """
    Convert a fight ending at round ``round_num`` with ``time_str`` (m:ss
    within that round) into total elapsed seconds, assuming 5-minute rounds.
    Returns None if either field can't be parsed.
    """
    if not isinstance(time_str, str) or ":" not in time_str:
        return None
    try:
        rd = int(round_num) if round_num not in (None, "", "NA") else None
        if rd is None:
            return None
        m_str, s_str = time_str.split(":", 1)
        return (rd - 1) * 300 + int(m_str) * 60 + int(s_str)
    except (ValueError, TypeError):
        return None


def _derive_per_fighter(group: pd.DataFrame) -> pd.Series:
    """Compute one row of derived stats for a single fighter's UFC fights."""
    # Drop any non-completed bouts (upcoming "next" rows, blank result
    # rows from malformed scrape) BEFORE any aggregation. This is the
    # root fix for Anderson Silva-style streak overcounts where a
    # scheduled fight row inflated ufc_fights_counted by 1.
    group = group.copy()
    group["_completed"] = group["result"].apply(_is_completed)
    group = group[group["_completed"]].drop(columns=["_completed"])

    # Defensive de-dup on the per-fighter axis: same fighter, same event,
    # same opponent, same date appearing twice = scrape artefact.
    dedup_cols = [c for c in ("event", "opponent", "event_date") if c in group.columns]
    if dedup_cols:
        group = group.drop_duplicates(subset=dedup_cols, keep="first")

    # Most-recent-first ordering for streak + last-fight calcs.
    ordered = group.sort_values(
        "event_date_parsed", ascending=False, na_position="last"
    )

    results = ordered["result"].fillna("").tolist()
    methods = ordered["method"].fillna("").tolist()
    details = ordered["method_detail"].fillna("").tolist() if "method_detail" in ordered.columns else [""] * len(results)
    rounds = ordered["round"].tolist() if "round" in ordered.columns else [None] * len(results)
    times = ordered["time"].tolist() if "time" in ordered.columns else [""] * len(results)

    # ---- Wins / losses splits by method ----------------------------------
    win_methods = [
        (_classify_method(m), _classify_ko_tko(m, d))
        for r, m, d in zip(results, methods, details) if r.lower() in WIN_FLAGS
    ]
    loss_methods = [
        (_classify_method(m), _classify_ko_tko(m, d))
        for r, m, d in zip(results, methods, details) if r.lower() in LOSS_FLAGS
    ]
    total_wins = len(win_methods)
    total_losses = len(loss_methods)

    def _share(count: int, total: int) -> float | None:
        return (count / total * 100) if total else None

    ko_wins = sum(1 for _, kt in win_methods if kt == "KO")
    tko_wins = sum(1 for _, kt in win_methods if kt == "TKO")
    sub_wins = sum(1 for mm, _ in win_methods if mm == "SUB")
    dec_wins = sum(1 for mm, _ in win_methods if mm == "DEC")
    finish_wins = ko_wins + tko_wins + sub_wins

    ko_losses = sum(1 for _, kt in loss_methods if kt == "KO")
    tko_losses = sum(1 for _, kt in loss_methods if kt == "TKO")
    sub_losses = sum(1 for mm, _ in loss_methods if mm == "SUB")
    dec_losses = sum(1 for mm, _ in loss_methods if mm == "DEC")
    finished_losses = ko_losses + tko_losses + sub_losses

    # ---- Streaks ---------------------------------------------------------
    win_streak, loss_streak = _current_streak(results)
    max_win_streak = _max_streak(results, WIN_FLAGS)
    max_loss_streak = _max_streak(results, LOSS_FLAGS)

    # ---- Time / round averages -------------------------------------------
    fight_durations = [
        _fight_time_seconds(t, r)
        for t, r in zip(times, rounds)
    ]
    fight_durations = [s for s in fight_durations if s is not None]
    avg_fight_seconds = (
        sum(fight_durations) / len(fight_durations) if fight_durations else None
    )

    round_ints: list[int] = []
    for r in rounds:
        try:
            round_ints.append(int(r))
        except (TypeError, ValueError):
            continue
    avg_round = sum(round_ints) / len(round_ints) if round_ints else None

    # ---- Activity --------------------------------------------------------
    last_dt = ordered["event_date_parsed"].dropna().head(1)
    last_fight_date = last_dt.iloc[0] if not last_dt.empty else pd.NaT
    if pd.notna(last_fight_date):
        days_since = (pd.Timestamp(dt.date.today()) - last_fight_date).days
    else:
        days_since = None

    # ---- Title fights ----------------------------------------------------
    if "is_title_fight" in ordered.columns:
        title_mask = ordered["is_title_fight"].fillna(False).astype(bool)
        title_fights = int(title_mask.sum())
        # Title wins / defenses: walk chronologically (oldest → newest) and
        # count title wins. Defenses = title wins after the first.
        chrono = ordered.sort_values("event_date_parsed", ascending=True, na_position="first")
        title_chrono = chrono[chrono["is_title_fight"].fillna(False).astype(bool)]
        title_results = [
            (r or "").lower() for r in title_chrono["result"].tolist()
        ]
        title_wins = sum(1 for r in title_results if r in WIN_FLAGS)
        title_losses = sum(1 for r in title_results if r in LOSS_FLAGS)
        # First title win is "title-winning"; subsequent wins are defenses
        # *until* a loss resets that. Simplified: count consecutive wins
        # after the first win, resetting on a loss.
        defenses = 0
        held = False
        for r in title_results:
            if r in WIN_FLAGS:
                if held:
                    defenses += 1
                held = True
            elif r in LOSS_FLAGS:
                held = False
    else:
        title_fights = None
        title_wins = None
        title_losses = None
        defenses = None

    return pd.Series({
        # Win-method counts + rates
        "ko_wins": ko_wins,
        "tko_wins": tko_wins,
        "sub_wins": sub_wins,
        "dec_wins": dec_wins,
        "finish_wins": finish_wins,
        "ko_rate": _share(ko_wins + tko_wins, total_wins),
        "sub_rate": _share(sub_wins, total_wins),
        "dec_rate": _share(dec_wins, total_wins),
        "finish_rate": _share(finish_wins, total_wins),
        # Loss-method counts + rates
        "ko_losses": ko_losses,
        "tko_losses": tko_losses,
        "sub_losses": sub_losses,
        "dec_losses": dec_losses,
        "finished_losses": finished_losses,
        "finished_loss_rate": _share(finished_losses, total_losses),
        # Streaks
        "win_streak": win_streak,            # current
        "loss_streak": loss_streak,          # current
        "max_win_streak": max_win_streak,    # peak historical
        "max_loss_streak": max_loss_streak,  # peak historical
        # Activity
        "last_fight_date": last_fight_date,
        "days_since_last_fight": days_since,
        "ufc_fights_counted": len(group),
        # Fight pace
        "avg_fight_seconds": avg_fight_seconds,
        "avg_round_ended": avg_round,
        # Title
        "title_fights": title_fights,
        "title_wins": title_wins,
        "title_losses": title_losses,
        "title_defenses": defenses,
    })


def z_score_by_weight_class(df: pd.DataFrame, stat: str) -> pd.Series:
    """
    Return ``stat`` z-scored within each weight class.

    A flyweight's 4 SLpM is not the same as a heavyweight's 4 SLpM —
    normalising against same-division peers makes the Stat Universe
    scatter directly comparable across divisions.
    """
    grouped = df.groupby("weight_class")[stat]
    return (df[stat] - grouped.transform("mean")) / grouped.transform("std")


DERIVED_COLUMNS = [
    "ko_wins", "tko_wins", "sub_wins", "dec_wins", "finish_wins",
    "ko_rate", "sub_rate", "dec_rate", "finish_rate",
    "ko_losses", "tko_losses", "sub_losses", "dec_losses",
    "finished_losses", "finished_loss_rate",
    "win_streak", "loss_streak", "max_win_streak", "max_loss_streak",
    "last_fight_date", "days_since_last_fight", "ufc_fights_counted",
    "avg_fight_seconds", "avg_round_ended",
    "title_fights", "title_wins", "title_losses", "title_defenses",
]


def _attach_title_flags(
    fights: pd.DataFrame,
    events: pd.DataFrame | None,
) -> pd.DataFrame:
    """
    Join an ``is_title_fight`` boolean onto each fight row by matching
    on (event_name, opponent). Events is the per-fight DataFrame produced
    by ``scrape_events``.
    """
    fights = fights.copy()
    if events is None or events.empty or "event_name" not in events.columns:
        fights["is_title_fight"] = False
        return fights

    # Build a lookup keyed by (event_name, fighter_name) → is_title.
    flags: dict[tuple[str, str], bool] = {}
    for _, row in events.iterrows():
        ev = str(row.get("event_name", "")).strip()
        is_title = bool(row.get("is_title_fight", False))
        for fname_col in ("fighter_a", "fighter_b"):
            name = str(row.get(fname_col, "")).strip()
            if ev and name:
                key = (ev, name.lower())
                # Keep True if any duplicate row says True.
                flags[key] = flags.get(key, False) or is_title

    def _lookup(ev_name: str, opponent: str) -> bool:
        # The "opponent" field on a fight row from a fighter's profile is
        # the OTHER fighter. The event row stores both. We can match by
        # either fighter_a or fighter_b, since the event row is shared.
        ev = (ev_name or "").strip()
        return flags.get((ev, (opponent or "").strip().lower()), False)

    fights["is_title_fight"] = [
        _lookup(ev, opp)
        for ev, opp in zip(fights.get("event", ""), fights.get("opponent", ""))
    ]
    return fights


def enrich_with_fight_data(
    fighters: pd.DataFrame,
    fights: pd.DataFrame | None,
    events: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Merge per-fight derived stats + champion flag onto the fighters table.

    When ``fights`` is ``None`` or empty, returns ``fighters`` with the
    new columns present but null — the UI degrades gracefully ("re-scrape
    to load fight history"). ``events`` is optional; without it, title
    fight stats stay null.
    """
    out = fighters.copy()

    # Champion tag — string match against name.
    out["is_champion"] = out["name"].isin(KNOWN_CHAMPIONS)

    if fights is None or fights.empty or "fighter_url" not in fights.columns:
        for col in DERIVED_COLUMNS:
            out[col] = pd.NA
        out["is_active"] = pd.NA
        return out

    if "event_date_parsed" not in fights.columns and "event_date" in fights.columns:
        fights = fights.copy()
        fights["event_date_parsed"] = pd.to_datetime(
            fights["event_date"], errors="coerce", format="%b. %d, %Y"
        )

    fights = _attach_title_flags(fights, events)

    derived = fights.groupby("fighter_url", sort=False).apply(
        _derive_per_fighter, include_groups=False
    )
    derived = derived.reset_index()

    out = out.merge(derived, how="left", left_on="url", right_on="fighter_url")
    out.drop(columns=["fighter_url"], inplace=True, errors="ignore")

    out["is_active"] = out["days_since_last_fight"].apply(
        lambda d: bool(d is not None and not pd.isna(d) and d <= 730)
    )
    return out
