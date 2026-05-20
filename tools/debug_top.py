
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import derived  # noqa: E402
from scraper import scraper  # noqa: E402

LEADERBOARDS = [
    ("ufc_fights_counted", "Most UFC bouts (completed)"),
    ("wins", "Most career MMA wins (listing-page total)"),
    ("max_win_streak", "Highest UFC win streak"),
    ("max_loss_streak", "Highest UFC loss streak"),
    ("finish_wins", "Most finishes (KO + TKO + SUB)"),
    ("ko_wins", "Most KO wins"),
    ("tko_wins", "Most TKO wins"),
    ("sub_wins", "Most submission wins"),
    ("dec_wins", "Most decision wins"),
    ("finished_losses", "Most times finished"),
    ("title_wins", "Most title wins"),
    ("title_defenses", "Most title defenses"),
]


def _load() -> pd.DataFrame:
    fighters = scraper.load_cached()
    if fighters is None or fighters.empty:
        sys.exit("No cached fighters.csv found — run a scrape first.")
    fights = scraper.load_cached_fights()
    events = scraper.load_cached_events()
    return derived.enrich_with_fight_data(fighters, fights, events)


def _print_top(df: pd.DataFrame, stat: str, label: str, n: int = 15) -> None:
    if stat not in df.columns:
        print(f"\n[{label}] -- column '{stat}' missing")
        return
    sub = df.dropna(subset=[stat]).copy()
    sub = sub[pd.to_numeric(sub[stat], errors="coerce").notna()]
    sub[stat] = pd.to_numeric(sub[stat], errors="coerce")
    top = sub.sort_values(stat, ascending=False).head(n)
    print(f"\n== {label} ({stat}) ==")
    for i, (_, row) in enumerate(top.iterrows(), start=1):
        name = row.get("name", "?")
        val = row[stat]
        ufc_n = int(row.get("ufc_fights_counted") or 0)
        print(f"  {i:>2}. {name:<30} {val:>8.1f}   (UFC bouts: {ufc_n})")


def _dump_fighter(df: pd.DataFrame, fighter_name: str) -> None:
    fighters = df[df["name"].str.lower() == fighter_name.lower()]
    if fighters.empty:
        print(f"No fighter found matching '{fighter_name}'.")
        return
    fighter = fighters.iloc[0]
    print(f"\n== {fighter['name']} ==")
    print(f"  URL                    : {fighter.get('url')}")
    print(f"  Career W-L-D (listing) : {int(fighter.get('wins', 0))}-"
          f"{int(fighter.get('losses', 0))}-{int(fighter.get('draws', 0))}")
    print(f"  UFC bouts counted      : {fighter.get('ufc_fights_counted')}")
    print(f"  Max win streak         : {fighter.get('max_win_streak')}")
    print(f"  Current form           : W{int(fighter.get('win_streak') or 0)} / "
          f"L{int(fighter.get('loss_streak') or 0)}")
    print(f"  Finish wins            : {fighter.get('finish_wins')}  "
          f"(KO {fighter.get('ko_wins')}, TKO {fighter.get('tko_wins')}, "
          f"SUB {fighter.get('sub_wins')}, DEC {fighter.get('dec_wins')})")
    print(f"  Title fights / wins    : {fighter.get('title_fights')} / "
          f"{fighter.get('title_wins')}")
    print(f"  Title defenses (est.)  : {fighter.get('title_defenses')}")

    fights = scraper.load_cached_fights()
    if fights is None:
        print("  (no fights.csv — cannot dump bout list)")
        return
    own = fights[fights["fighter_url"] == fighter["url"]].copy()
    if "event_date_parsed" in own.columns:
        own = own.sort_values("event_date_parsed", ascending=False, na_position="last")
    print(f"\n  Fight history ({len(own)} rows):")
    for _, f in own.iterrows():
        print(f"    [{f.get('result','?'):>4}] {f.get('event_date',''):>14}  "
              f"{f.get('method','?'):<10} {f.get('method_detail',''):<25}  "
              f"vs {f.get('opponent','?')}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fighter", help="Dump full fight history for one fighter")
    parser.add_argument("--top", type=int, default=15, help="How many rows per leaderboard")
    args = parser.parse_args()

    df = _load()
    print(f"Loaded {len(df)} fighters from cache.")

    if args.fighter:
        _dump_fighter(df, args.fighter)
        return

    for stat, label in LEADERBOARDS:
        _print_top(df, stat, label, n=args.top)


if __name__ == "__main__":
    main()
