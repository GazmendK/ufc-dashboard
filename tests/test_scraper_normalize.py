
from __future__ import annotations

import pandas as pd

from scraper.scraper import _to_dataframe


def _raw_fighter(**overrides):
    base = {
        "first_name": "Test",
        "last_name": "Fighter",
        "nickname": "",
        "height": "6' 0\"",
        "weight": "170 lbs.",
        "reach": "72.0\"",
        "stance": "Orthodox",
        "wins": "10",
        "losses": "2",
        "draws": "0",
        "url": "http://example.com/fighter/test",
        # detail-page stats
        "slpm": "4.0",
        "str_acc": "55%",
        "sapm": "2.5",
        "str_def": "60%",
        "td_avg": "1.5",
        "td_acc": "40%",
        "td_def": "70%",
        "sub_avg": "0.5",
    }
    base.update(overrides)
    return base


class TestToDataFrame:
    def test_name_concatenation(self):
        df = _to_dataframe([_raw_fighter(first_name="Jon", last_name="Jones")])
        assert df.iloc[0]["name"] == "Jon Jones"

    def test_unit_conversion_columns_present(self):
        df = _to_dataframe([_raw_fighter()])
        row = df.iloc[0]
        assert row["height_in"] == 72  # 6' 0"
        assert row["weight_lbs"] == 170
        assert row["reach_in"] == 72.0
        assert row["weight_class"] == "Welterweight"

    def test_percentage_stripped(self):
        df = _to_dataframe([_raw_fighter(str_acc="57%", td_def="95%")])
        assert df.iloc[0]["str_acc"] == 57
        assert df.iloc[0]["td_def"] == 95

    def test_total_fights_computed(self):
        df = _to_dataframe([_raw_fighter(wins="20", losses="3", draws="1")])
        assert df.iloc[0]["total_fights"] == 24

    def test_zero_fights_nulls_rate_stats(self):
        """The fix for the 0/50/100% spike — fighters with no UFC bouts
        should not carry their fake 0% / 0.0 placeholder values."""
        df = _to_dataframe([_raw_fighter(wins="0", losses="0", draws="0")])
        row = df.iloc[0]
        assert row["total_fights"] == 0
        for col in ["str_acc", "str_def", "td_acc", "td_def",
                    "slpm", "sapm", "td_avg", "sub_avg"]:
            assert pd.isna(row[col]), f"{col} should be NaN for a 0-fight fighter"

    def test_fighter_with_fights_keeps_rate_stats(self):
        df = _to_dataframe([_raw_fighter(wins="5", losses="2", str_acc="55%")])
        assert df.iloc[0]["str_acc"] == 55
        assert df.iloc[0]["slpm"] == 4.0

    def test_empty_input_returns_empty_df(self):
        df = _to_dataframe([])
        assert df.empty
