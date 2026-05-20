from __future__ import annotations

import datetime as dt

import pandas as pd

KNOWN_CHAMPIONS: set[str] = {
    "Jon Jones", "Tom Aspinall", "Alex Pereira", "Magomed Ankalaev",
    "Dricus Du Plessis", "Khamzat Chimaev", "Belal Muhammad", "Jack Della Maddalena",
    "Islam Makhachev", "Ilia Topuria", "Merab Dvalishvili",
    "Alexandre Pantoja", "Valentina Shevchenko", "Zhang Weili",
    "Julianna Pena", "Raquel Pennington", "Kayla Harrison",
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
EXCLUDED_RESULTS = {"next", "", "scheduled", "upcoming"}


def _is_completed(result: str) -> bool:
    r = (result or "").strip().lower()
    return r in WIN_FLAGS | LOSS_FLAGS | DRAW_FLAGS | NC_FLAGS


def _classify_method(method: str) -> str:
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


_TKO_DETAIL_KEYWORDS = (
    "PUNCHES", "ELBOWS", "KICKS",
    "DOCTOR", "CORNER", "STOPPAGE", "RETIREMENT",
    "GROUND AND POUND", "GROUND & POUND",
    "STRIKES",
)


def _classify_ko_tko(method: str, detail: str) -> str:
    if _classify_method(method) != "KO":
        return ""
    d = (detail or "").upper()
    for kw in _TKO_DETAIL_KEYWORDS:
        if kw in d:
            return "TKO"
    return "KO"


def _current_streak(results: list[str]) -> tuple[int, int]:
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
    longest = current = 0
    for r in results:
        if r.lower() in target_flags:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _fight_time_seconds(time_str: str, round_num: str | int | None) -> int | None:
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
    group = group.copy()
    group["_completed"] = group["result"].apply(_is_completed)
    group = group[group["_completed"]].drop(columns=["_completed"])

    dedup_cols = [c for c in ("event", "opponent", "event_date") if c in group.columns]
    if dedup_cols:
        group = group.drop_duplicates(subset=dedup_cols, keep="first")

    ordered = group.sort_values(
        "event_date_parsed", ascending=False, na_position="last"
    )

    results = ordered["result"].fillna("").tolist()
    methods = ordered["method"].fillna("").tolist()
    details = ordered["method_detail"].fillna("").tolist() if "method_detail" in ordered.columns else [""] * len(results)
    rounds = ordered["round"].tolist() if "round" in ordered.columns else [None] * len(results)
    times = ordered["time"].tolist() if "time" in ordered.columns else [""] * len(results)

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

    win_streak, loss_streak = _current_streak(results)
    max_win_streak = _max_streak(results, WIN_FLAGS)
    max_loss_streak = _max_streak(results, LOSS_FLAGS)

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

    last_dt = ordered["event_date_parsed"].dropna().head(1)
    last_fight_date = last_dt.iloc[0] if not last_dt.empty else pd.NaT
    if pd.notna(last_fight_date):
        days_since = (pd.Timestamp(dt.date.today()) - last_fight_date).days
    else:
        days_since = None

    if "is_title_fight" in ordered.columns:
        title_mask = ordered["is_title_fight"].fillna(False).astype(bool)
        title_fights = int(title_mask.sum())
        chrono = ordered.sort_values("event_date_parsed", ascending=True, na_position="first")
        title_chrono = chrono[chrono["is_title_fight"].fillna(False).astype(bool)]
        title_results = [
            (r or "").lower() for r in title_chrono["result"].tolist()
        ]
        title_wins = sum(1 for r in title_results if r in WIN_FLAGS)
        title_losses = sum(1 for r in title_results if r in LOSS_FLAGS)
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
        "ko_wins": ko_wins,
        "tko_wins": tko_wins,
        "sub_wins": sub_wins,
        "dec_wins": dec_wins,
        "finish_wins": finish_wins,
        "ko_rate": _share(ko_wins + tko_wins, total_wins),
        "sub_rate": _share(sub_wins, total_wins),
        "dec_rate": _share(dec_wins, total_wins),
        "finish_rate": _share(finish_wins, total_wins),
        "ko_losses": ko_losses,
        "tko_losses": tko_losses,
        "sub_losses": sub_losses,
        "dec_losses": dec_losses,
        "finished_losses": finished_losses,
        "finished_loss_rate": _share(finished_losses, total_losses),
        "win_streak": win_streak,
        "loss_streak": loss_streak,
        "max_win_streak": max_win_streak,
        "max_loss_streak": max_loss_streak,
        "last_fight_date": last_fight_date,
        "days_since_last_fight": days_since,
        "ufc_fights_counted": len(group),
        "avg_fight_seconds": avg_fight_seconds,
        "avg_round_ended": avg_round,
        "title_fights": title_fights,
        "title_wins": title_wins,
        "title_losses": title_losses,
        "title_defenses": defenses,
    })


def z_score_by_weight_class(df: pd.DataFrame, stat: str) -> pd.Series:
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
    fights = fights.copy()
    if events is None or events.empty or "event_name" not in events.columns:
        fights["is_title_fight"] = False
        return fights

    flags: dict[tuple[str, str], bool] = {}
    for _, row in events.iterrows():
        ev = str(row.get("event_name", "")).strip()
        is_title = bool(row.get("is_title_fight", False))
        for fname_col in ("fighter_a", "fighter_b"):
            name = str(row.get(fname_col, "")).strip()
            if ev and name:
                key = (ev, name.lower())
                flags[key] = flags.get(key, False) or is_title

    def _lookup(ev_name: str, opponent: str) -> bool:
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
    out = fighters.copy()
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
