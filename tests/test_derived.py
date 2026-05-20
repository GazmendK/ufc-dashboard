
from __future__ import annotations

import pandas as pd
import pytest

from app.derived import (
    _attach_title_flags,
    _classify_ko_tko,
    _classify_method,
    _current_streak,
    _fight_time_seconds,
    _is_completed,
    _max_streak,
    enrich_with_fight_data,
    z_score_by_weight_class,
)


class TestClassifyMethod:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("KO/TKO", "KO"),
            ("KO", "KO"),
            ("TKO", "KO"),
            ("SUB", "SUB"),
            ("Submission", "SUB"),
            ("U-DEC", "DEC"),
            ("S-DEC", "DEC"),
            ("Decision", "DEC"),
            ("DQ", "OTHER"),
            ("Overturned", "OTHER"),
            ("", "OTHER"),
        ],
    )
    def test_buckets(self, raw, expected):
        assert _classify_method(raw) == expected

    def test_non_string_safe(self):
        assert _classify_method(None) == "OTHER"  # type: ignore[arg-type]


class TestCurrentStreak:
    def test_three_win_streak(self):
        # Most-recent-first ordering
        wins, losses = _current_streak(["win", "win", "win", "loss"])
        assert wins == 3
        assert losses == 0

    def test_two_loss_streak(self):
        wins, losses = _current_streak(["loss", "loss", "win"])
        assert wins == 0
        assert losses == 2

    def test_single_win(self):
        wins, losses = _current_streak(["win", "loss"])
        assert (wins, losses) == (1, 0)

    def test_empty(self):
        assert _current_streak([]) == (0, 0)

    def test_draw_at_top_yields_zeros(self):
        # A draw / NC at most recent fight resets both counters to 0.
        wins, losses = _current_streak(["draw", "win", "win"])
        assert (wins, losses) == (0, 0)

    def test_case_insensitive(self):
        wins, losses = _current_streak(["Win", "WIN", "loss"])
        assert wins == 2


# ---------------------------------------------------------------------------
# enrich_with_fight_data — the main integration point
# ---------------------------------------------------------------------------

def _fights_df():
    """Build a fights DataFrame with two fighters of varying outcomes."""
    rows = [
        # Fighter A: 3 wins (2 KO, 1 SUB), 1 loss — currently on a 3-win streak
        {"fighter_url": "url_A", "result": "win",  "method": "KO/TKO", "event_date": "Nov. 16, 2025"},
        {"fighter_url": "url_A", "result": "win",  "method": "SUB",    "event_date": "Mar. 04, 2025"},
        {"fighter_url": "url_A", "result": "win",  "method": "KO/TKO", "event_date": "Jul. 30, 2024"},
        {"fighter_url": "url_A", "result": "loss", "method": "DEC",    "event_date": "Feb. 11, 2023"},
        # Fighter B: 1 win 1 loss, last fight was a loss
        {"fighter_url": "url_B", "result": "loss", "method": "DEC",    "event_date": "Jan. 15, 2024"},
        {"fighter_url": "url_B", "result": "win",  "method": "DEC",    "event_date": "Jun. 02, 2023"},
    ]
    df = pd.DataFrame(rows)
    df["event_date_parsed"] = pd.to_datetime(df["event_date"], format="%b. %d, %Y")
    return df


def _fighters_df():
    return pd.DataFrame([
        {"name": "Alpha", "url": "url_A", "weight_class": "Lightweight"},
        {"name": "Bravo", "url": "url_B", "weight_class": "Lightweight"},
        {"name": "Jon Jones", "url": "url_C", "weight_class": "Heavyweight"},  # in champ list
    ])


class TestEnrichWithFightData:
    def test_finish_rates_for_fighter_a(self):
        out = enrich_with_fight_data(_fighters_df(), _fights_df())
        a = out[out["name"] == "Alpha"].iloc[0]
        # 3 wins: 2 KO + 1 SUB → 66.67% KO, 33.33% SUB, 0% DEC
        assert a["ko_rate"] == pytest.approx(66.6667, abs=0.01)
        assert a["sub_rate"] == pytest.approx(33.3333, abs=0.01)
        assert a["dec_rate"] == 0.0
        assert a["finish_rate"] == pytest.approx(100.0, abs=0.01)

    def test_win_streak(self):
        out = enrich_with_fight_data(_fighters_df(), _fights_df())
        a = out[out["name"] == "Alpha"].iloc[0]
        b = out[out["name"] == "Bravo"].iloc[0]
        assert a["win_streak"] == 3
        assert a["loss_streak"] == 0
        assert b["win_streak"] == 0
        assert b["loss_streak"] == 1

    def test_champion_flag(self):
        out = enrich_with_fight_data(_fighters_df(), _fights_df())
        assert bool(out[out["name"] == "Jon Jones"].iloc[0]["is_champion"]) is True
        assert bool(out[out["name"] == "Alpha"].iloc[0]["is_champion"]) is False

    def test_last_fight_date_is_most_recent(self):
        out = enrich_with_fight_data(_fighters_df(), _fights_df())
        a = out[out["name"] == "Alpha"].iloc[0]
        assert pd.to_datetime(a["last_fight_date"]).date().isoformat() == "2025-11-16"

    def test_fighter_with_no_history_has_null_streak(self):
        out = enrich_with_fight_data(_fighters_df(), _fights_df())
        # Jon Jones (url_C) has no rows in our fixture fights_df
        jj = out[out["name"] == "Jon Jones"].iloc[0]
        assert pd.isna(jj["win_streak"]) or jj["win_streak"] == 0 or jj["win_streak"] is None

    def test_empty_fights_keeps_derived_columns_null(self):
        out = enrich_with_fight_data(_fighters_df(), pd.DataFrame())
        for col in ["ko_rate", "sub_rate", "dec_rate", "win_streak"]:
            assert col in out.columns

    def test_none_fights_keeps_derived_columns_null(self):
        out = enrich_with_fight_data(_fighters_df(), None)
        assert "ko_rate" in out.columns
        assert out["ko_rate"].isna().all()


class TestMaxStreak:
    def test_peak_when_currently_losing(self):
        # Most-recent-first: lost last, won 10 before, lost before that.
        # The current win streak is 0, but the peak should be 10.
        results = ["loss"] + ["win"] * 10 + ["loss"] * 3 + ["win"] * 2
        assert _max_streak(results, {"win", "w"}) == 10

    def test_peak_loss_streak(self):
        results = ["win", "loss", "loss", "loss", "loss", "win", "loss", "loss"]
        assert _max_streak(results, {"loss", "l"}) == 4

    def test_empty(self):
        assert _max_streak([], {"win"}) == 0

    def test_case_insensitive(self):
        assert _max_streak(["WIN", "win", "loss"], {"win"}) == 2


class TestClassifyKoTko:
    @pytest.mark.parametrize(
        "method,detail,expected",
        [
            ("KO/TKO", "Punch", "KO"),
            ("KO/TKO", "Spinning Back Kick", "KO"),
            ("KO/TKO", "Head Kick", "KO"),
            ("KO/TKO", "Punches", "TKO"),
            ("KO/TKO", "Elbows", "TKO"),
            ("KO/TKO", "Ground and Pound", "TKO"),
            ("KO/TKO", "Doctor Stoppage", "TKO"),
            ("KO/TKO", "Corner Stoppage", "TKO"),
            ("KO/TKO", "Retirement", "TKO"),
            ("SUB", "Guillotine Choke", ""),  # not a KO/TKO at all
            ("DEC", "", ""),
        ],
    )
    def test_heuristic(self, method, detail, expected):
        assert _classify_ko_tko(method, detail) == expected


class TestFightTimeSeconds:
    def test_first_round_finish(self):
        # Round 1, 4:30 in → 4*60+30 = 270 seconds
        assert _fight_time_seconds("4:30", 1) == 270

    def test_third_round_finish(self):
        # 2 full rounds (600s) + 1:00 into round 3 = 660s
        assert _fight_time_seconds("1:00", 3) == 660

    def test_full_5_round_decision(self):
        # Round 5, 5:00 in → 4*300 + 5*60 = 1500s
        assert _fight_time_seconds("5:00", 5) == 1500

    def test_returns_none_when_garbage(self):
        assert _fight_time_seconds("", 1) is None
        assert _fight_time_seconds("4:30", None) is None
        assert _fight_time_seconds("not a time", 1) is None


class TestAttachTitleFlags:
    def test_marks_title_fight_when_event_matches(self):
        fights = pd.DataFrame([
            {"fighter_url": "url_A", "event": "UFC 309", "opponent": "Stipe Miocic"},
            {"fighter_url": "url_A", "event": "UFC 100", "opponent": "Frank Mir"},
        ])
        events = pd.DataFrame([
            {"event_name": "UFC 309", "fighter_a": "Jon Jones",
             "fighter_b": "Stipe Miocic", "is_title_fight": True},
            {"event_name": "UFC 100", "fighter_a": "Brock Lesnar",
             "fighter_b": "Frank Mir", "is_title_fight": False},
        ])
        merged = _attach_title_flags(fights, events)
        assert bool(merged.iloc[0]["is_title_fight"]) is True
        assert bool(merged.iloc[1]["is_title_fight"]) is False

    def test_no_events_leaves_all_false(self):
        fights = pd.DataFrame([
            {"fighter_url": "url_A", "event": "UFC 309", "opponent": "Stipe Miocic"},
        ])
        merged = _attach_title_flags(fights, None)
        assert bool(merged.iloc[0]["is_title_fight"]) is False


class TestDerivedWithTitleEvents:
    """End-to-end check that title aggregation lands in the merged df."""

    def test_title_wins_and_defenses(self):
        fights = pd.DataFrame([
            # Chronological (oldest first in this fixture, sorted inside derive)
            {"fighter_url": "url_A", "result": "win", "method": "KO/TKO",
             "method_detail": "Punch", "event": "UFC 100", "opponent": "Bob",
             "round": "2", "time": "1:30",
             "event_date": "Jan. 01, 2020"},
            {"fighter_url": "url_A", "result": "win", "method": "DEC",
             "method_detail": "Unanimous", "event": "UFC 101", "opponent": "Carl",
             "round": "5", "time": "5:00",
             "event_date": "Jun. 01, 2020"},
            {"fighter_url": "url_A", "result": "win", "method": "SUB",
             "method_detail": "Triangle", "event": "UFC 102", "opponent": "Dan",
             "round": "3", "time": "2:00",
             "event_date": "Jan. 01, 2021"},
        ])
        fights["event_date_parsed"] = pd.to_datetime(fights["event_date"], format="%b. %d, %Y")

        events = pd.DataFrame([
            {"event_name": "UFC 100", "fighter_a": "Alpha", "fighter_b": "Bob",
             "is_title_fight": True},
            {"event_name": "UFC 101", "fighter_a": "Alpha", "fighter_b": "Carl",
             "is_title_fight": True},
            {"event_name": "UFC 102", "fighter_a": "Alpha", "fighter_b": "Dan",
             "is_title_fight": True},
        ])

        fighters = pd.DataFrame([{
            "name": "Alpha", "url": "url_A", "weight_class": "Lightweight",
        }])

        out = enrich_with_fight_data(fighters, fights, events)
        row = out.iloc[0]
        # 3 title fights, 3 title wins, 2 defenses (wins after first title win)
        assert row["title_fights"] == 3
        assert row["title_wins"] == 3
        assert row["title_defenses"] == 2


class TestIsCompleted:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("win", True),
            ("WIN", True),
            ("loss", True),
            ("draw", True),
            ("nc", True),
            ("no contest", True),
            ("next", False),
            ("", False),
            ("scheduled", False),
            (None, False),
        ],
    )
    def test_completed_detection(self, raw, expected):
        assert _is_completed(raw) is expected


class TestSilvaStyleStreakRegression:
    """
    Models the Anderson Silva bug: a fighter with a 16-win streak followed
    by a loss should report max_win_streak == 16, not 17. Adds a "next"
    upcoming-fight row, an "nc" (overturned) row, and a duplicate scrape
    artefact — none of which should inflate the streak or fight count.
    """

    @staticmethod
    def _build_silva_like():
        rows = []
        # 16 chronological wins (oldest → newest by date)
        for i in range(16):
            year = 2006 + (i // 3)
            month = ((i * 4) % 12) + 1
            rows.append({
                "fighter_url": "url_AS",
                "result": "win",
                "method": "KO/TKO" if i % 2 == 0 else "DEC",
                "method_detail": "Punch" if i % 2 == 0 else "Unanimous",
                "round": "1" if i % 2 == 0 else "5",
                "time": "2:00" if i % 2 == 0 else "5:00",
                "event": f"UFC fight {i+1}",
                "opponent": f"Opponent {i+1}",
                "event_date": f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][month-1]}. 01, {year}",
            })
        # Loss to Weidman (ends the streak)
        rows.append({
            "fighter_url": "url_AS",
            "result": "loss", "method": "KO/TKO", "method_detail": "Punch",
            "round": "2", "time": "1:18",
            "event": "UFC 162", "opponent": "Chris Weidman",
            "event_date": "Jul. 06, 2013",
        })
        # "next" placeholder row from ufcstats.com (upcoming exhibition).
        # Pre-fix this would have been counted in ufc_fights_counted.
        rows.append({
            "fighter_url": "url_AS",
            "result": "next", "method": "", "method_detail": "",
            "round": "", "time": "",
            "event": "Future Fight", "opponent": "TBA",
            "event_date": "",
        })
        # An overturned-to-NC bout that should not count as a win.
        rows.append({
            "fighter_url": "url_AS",
            "result": "nc", "method": "Overturned", "method_detail": "",
            "round": "5", "time": "5:00",
            "event": "UFC 183", "opponent": "Nick Diaz",
            "event_date": "Jan. 31, 2015",
        })
        # Duplicate scrape artefact of the last win — must be deduped.
        rows.append(rows[15].copy())

        df = pd.DataFrame(rows)
        df["event_date_parsed"] = pd.to_datetime(
            df["event_date"], errors="coerce", format="%b. %d, %Y"
        )
        return df

    def test_max_win_streak_is_16(self):
        fights = self._build_silva_like()
        fighters = pd.DataFrame([{
            "name": "Anderson Silva", "url": "url_AS", "weight_class": "Middleweight",
        }])
        out = enrich_with_fight_data(fighters, fights)
        row = out.iloc[0]
        assert row["max_win_streak"] == 16, (
            f"expected 16 wins, got {row['max_win_streak']} — likely the 'next' "
            f"row, NC, or duplicate is being counted as a win"
        )

    def test_ufc_fights_counted_excludes_next_row(self):
        fights = self._build_silva_like()
        fighters = pd.DataFrame([{
            "name": "Anderson Silva", "url": "url_AS", "weight_class": "Middleweight",
        }])
        out = enrich_with_fight_data(fighters, fights)
        # 16 wins + 1 loss + 1 NC = 18 completed bouts.
        # The "next" row and the duplicate must NOT inflate the count.
        assert out.iloc[0]["ufc_fights_counted"] == 18

    def test_total_wins_excludes_nc_and_next(self):
        fights = self._build_silva_like()
        fighters = pd.DataFrame([{
            "name": "Anderson Silva", "url": "url_AS", "weight_class": "Middleweight",
        }])
        out = enrich_with_fight_data(fighters, fights)
        row = out.iloc[0]
        finish_wins = row["finish_wins"]
        dec_wins = row["dec_wins"]
        # 16 wins total: 8 KO/TKO (even-indexed) + 8 DEC (odd-indexed).
        # NC must not bump the finish count.
        assert finish_wins + dec_wins == 16


class TestOliveiraStyleFinishesRegression:
    """
    Models a fighter with a huge finish count whose number must come out
    intact: 12 SUB wins + 8 KO wins, mixed with decisions and losses.
    Validates that finish_wins = ko_wins + tko_wins + sub_wins and that
    decisions don't accidentally fall into the finish bucket.
    """

    def test_finish_count_is_sum_of_methods(self):
        rows = []
        # 8 KO wins
        for i in range(8):
            rows.append({
                "fighter_url": "url_CO", "result": "win",
                "method": "KO/TKO", "method_detail": "Punch",
                "round": "1", "time": "2:00",
                "event": f"KO event {i}", "opponent": f"KO Opp {i}",
                "event_date": f"Jan. 0{(i % 9) + 1}, 2018",
            })
        # 12 SUB wins
        for i in range(12):
            rows.append({
                "fighter_url": "url_CO", "result": "win",
                "method": "SUB", "method_detail": "Guillotine Choke",
                "round": "1", "time": "1:30",
                "event": f"SUB event {i}", "opponent": f"SUB Opp {i}",
                "event_date": f"Feb. 0{(i % 9) + 1}, 2019",
            })
        # 4 decision wins (not finishes)
        for i in range(4):
            rows.append({
                "fighter_url": "url_CO", "result": "win",
                "method": "U-DEC", "method_detail": "Unanimous",
                "round": "3", "time": "5:00",
                "event": f"DEC event {i}", "opponent": f"DEC Opp {i}",
                "event_date": f"Mar. 0{i+1}, 2020",
            })
        # 9 losses (mix)
        for i in range(9):
            rows.append({
                "fighter_url": "url_CO", "result": "loss",
                "method": "KO/TKO" if i % 2 == 0 else "DEC",
                "method_detail": "Punches" if i % 2 == 0 else "Unanimous",
                "round": "2", "time": "3:00",
                "event": f"Loss event {i}", "opponent": f"Loss Opp {i}",
                "event_date": f"Apr. 0{i+1}, 2017",
            })

        fights = pd.DataFrame(rows)
        fights["event_date_parsed"] = pd.to_datetime(
            fights["event_date"], errors="coerce", format="%b. %d, %Y"
        )
        fighters = pd.DataFrame([{
            "name": "Charles Oliveira", "url": "url_CO", "weight_class": "Lightweight",
        }])

        out = enrich_with_fight_data(fighters, fights)
        row = out.iloc[0]

        # 8 KO + 12 SUB = 20 finishes (TKO heuristic may shift KO ↔ TKO
        # but the sum must remain stable).
        assert row["ko_wins"] + row["tko_wins"] == 8
        assert row["sub_wins"] == 12
        assert row["finish_wins"] == 20
        assert row["dec_wins"] == 4
        # Decision losses (the odd-indexed losses) shouldn't be counted as finished.
        assert row["finished_losses"] == 5  # 5 even-indexed KO/TKO losses (i=0,2,4,6,8)


class TestZScoreByWeightClass:
    def test_z_centered_around_zero(self):
        df = pd.DataFrame({
            "weight_class": ["Lightweight"] * 4 + ["Heavyweight"] * 4,
            "slpm": [3.0, 4.0, 5.0, 6.0, 1.0, 2.0, 3.0, 4.0],
        })
        z = z_score_by_weight_class(df, "slpm")
        # Within each weight class, the mean of the z-scores must be ~0.
        df["_z"] = z
        for _, group in df.groupby("weight_class"):
            assert group["_z"].mean() == pytest.approx(0.0, abs=1e-9)

    def test_relative_ranking_preserved(self):
        df = pd.DataFrame({
            "weight_class": ["Lightweight"] * 3,
            "slpm": [2.0, 4.0, 6.0],
        })
        z = z_score_by_weight_class(df, "slpm").tolist()
        assert z[0] < z[1] < z[2]
