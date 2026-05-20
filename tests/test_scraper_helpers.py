
from __future__ import annotations

import pytest

from scraper.scraper import (
    _classify_weight,
    _clean,
    _height_to_inches,
    _reach_to_inches,
    _weight_to_lbs,
)


class TestHeightToInches:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("5' 11\"", 71),
            ("6' 0\"", 72),
            ("5' 6\"", 66),
            ("7' 1\"", 85),
        ],
    )
    def test_parses_feet_inches(self, raw, expected):
        assert _height_to_inches(raw) == expected

    @pytest.mark.parametrize("raw", ["", "--", "unknown", "5ft"])
    def test_returns_none_for_invalid(self, raw):
        assert _height_to_inches(raw) is None


class TestWeightToLbs:
    def test_strips_lbs_suffix(self):
        assert _weight_to_lbs("155 lbs.") == 155

    def test_handles_no_suffix(self):
        assert _weight_to_lbs("170") == 170

    def test_returns_none_when_empty(self):
        assert _weight_to_lbs("") is None


class TestReachToInches:
    def test_parses_inches(self):
        assert _reach_to_inches('72.0"') == 72.0

    def test_parses_integer(self):
        assert _reach_to_inches('76"') == 76.0

    def test_returns_none_for_empty(self):
        assert _reach_to_inches("") is None

    def test_returns_none_for_garbage(self):
        assert _reach_to_inches("abc") is None


class TestClassifyWeight:
    @pytest.mark.parametrize(
        "weight,expected",
        [
            (115, "Strawweight"),
            (125, "Flyweight"),
            (135, "Bantamweight"),
            (145, "Featherweight"),
            (155, "Lightweight"),
            (170, "Welterweight"),
            (185, "Middleweight"),
            (205, "Light Heavyweight"),
            (265, "Heavyweight"),
            (300, "Super Heavyweight"),
        ],
    )
    def test_buckets_correctly(self, weight, expected):
        assert _classify_weight(weight) == expected

    def test_below_strawweight_still_strawweight(self):
        # 100 lbs has no division, gets bucketed up to Strawweight (≤115).
        assert _classify_weight(100) == "Strawweight"

    def test_none_is_unknown(self):
        assert _classify_weight(None) == "Unknown"


class TestClean:
    def test_strips_whitespace(self):
        assert _clean("  hello  ") == "hello"

    def test_replaces_double_dash(self):
        assert _clean("--") == ""

    def test_replaces_triple_dash(self):
        assert _clean("---") == ""

    def test_passes_real_values_through(self):
        assert _clean("Orthodox") == "Orthodox"

    def test_handles_empty(self):
        assert _clean("") == ""
