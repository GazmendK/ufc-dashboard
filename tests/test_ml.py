from __future__ import annotations

import pandas as pd
import pytest

from app.ml import (
    FEATURE_COLS,
    build_training_data,
    feature_importances,
    head_to_head,
    predict_proba,
    train_model,
)


def _fighters(n: int = 10) -> pd.DataFrame:
    rows = []
    for i in range(n):
        rows.append({
            "name": f"Fighter {i}",
            "url": f"http://f/{i}",
            "slpm": 2.0 + i * 0.5,
            "str_acc": 40 + i * 2,
            "sapm": 4.0 - i * 0.2,
            "str_def": 45 + i * 2,
            "td_avg": 1.0 + i * 0.3,
            "td_acc": 30 + i * 3,
            "td_def": 50 + i * 3,
            "sub_avg": 0.2 + i * 0.1,
            "height_in": 68 + i * 0.5,
            "reach_in": 70 + i * 0.5,
        })
    return pd.DataFrame(rows)


def _fights(n_fighters: int = 10, rematches: int = 2) -> pd.DataFrame:
    rows = []
    toggle = True
    for k in range(rematches):
        for i in range(n_fighters):
            for j in range(i + 1, n_fighters):
                event = f"UFC TEST {i}-{j}-{k}"
                if toggle:
                    rows.append({
                        "fighter_url": f"http://f/{j}", "opponent": f"Fighter {i}",
                        "result": "win", "event": event,
                        "event_date": "Jan. 01, 2024", "method": "DEC",
                    })
                else:
                    rows.append({
                        "fighter_url": f"http://f/{i}", "opponent": f"Fighter {j}",
                        "result": "loss", "event": event,
                        "event_date": "Jan. 01, 2024", "method": "DEC",
                    })
                toggle = not toggle
    return pd.DataFrame(rows)


class TestBuildTrainingData:
    def test_shapes_match(self):
        fighters = _fighters()
        X, y = build_training_data(fighters, _fights())
        assert X.shape[0] == len(y)
        assert X.shape[1] == len(FEATURE_COLS)

    def test_labels_binary(self):
        X, y = build_training_data(_fighters(), _fights())
        assert set(y) == {0, 1}

    def test_same_bout_from_both_perspectives_counted_once(self):
        fighters = _fighters(2)
        fights = pd.DataFrame([
            {"fighter_url": "http://f/1", "opponent": "Fighter 0",
             "result": "win", "event": "UFC X", "event_date": "", "method": "DEC"},
            {"fighter_url": "http://f/0", "opponent": "Fighter 1",
             "result": "loss", "event": "UFC X", "event_date": "", "method": "DEC"},
        ])
        X, y = build_training_data(fighters, fights)
        assert len(X) == 1

    def test_rematch_on_other_event_counted_separately(self):
        fighters = _fighters(2)
        fights = pd.DataFrame([
            {"fighter_url": "http://f/1", "opponent": "Fighter 0",
             "result": "win", "event": "UFC X", "event_date": "", "method": "DEC"},
            {"fighter_url": "http://f/1", "opponent": "Fighter 0",
             "result": "win", "event": "UFC Y", "event_date": "", "method": "DEC"},
        ])
        X, y = build_training_data(fighters, fights)
        assert len(X) == 2

    def test_non_completed_results_excluded(self):
        fighters = _fighters(2)
        fights = pd.DataFrame([
            {"fighter_url": "http://f/1", "opponent": "Fighter 0",
             "result": "next", "event": "UFC X", "event_date": "", "method": ""},
            {"fighter_url": "http://f/1", "opponent": "Fighter 0",
             "result": "nc", "event": "UFC Y", "event_date": "", "method": ""},
        ])
        X, y = build_training_data(fighters, fights)
        assert len(X) == 0

    def test_unknown_opponent_excluded(self):
        fighters = _fighters(2)
        fights = pd.DataFrame([
            {"fighter_url": "http://f/1", "opponent": "Unknown Guy",
             "result": "win", "event": "UFC X", "event_date": "", "method": "DEC"},
        ])
        X, y = build_training_data(fighters, fights)
        assert len(X) == 0


class TestTrainModel:
    def test_returns_none_for_tiny_dataset(self):
        fighters = _fighters(3)
        fights = _fights(3, rematches=1)
        assert train_model(fighters, fights) is None

    def test_report_fields(self):
        report = train_model(_fighters(), _fights())
        assert report is not None
        assert 0.0 <= report.accuracy <= 1.0
        assert report.n_fights >= 50

    def test_separable_data_learns_well(self):
        report = train_model(_fighters(), _fights())
        assert report.accuracy > 0.8

    def test_stronger_fighter_favored(self):
        fighters = _fighters()
        report = train_model(fighters, _fights())
        prob = predict_proba(report.pipeline, fighters, "Fighter 9", "Fighter 0")
        assert prob is not None
        assert prob > 0.5

    def test_predict_range(self):
        fighters = _fighters()
        report = train_model(fighters, _fights())
        prob = predict_proba(report.pipeline, fighters, "Fighter 3", "Fighter 6")
        assert 0.0 <= prob <= 1.0

    def test_unknown_fighter_returns_none(self):
        fighters = _fighters()
        report = train_model(fighters, _fights())
        assert predict_proba(report.pipeline, fighters, "Nobody", "Fighter 0") is None

    def test_feature_importances_cover_all_features(self):
        fighters = _fighters()
        report = train_model(fighters, _fights())
        imp = feature_importances(report.pipeline, fighters)
        assert len(imp) == len(FEATURE_COLS)
        assert (imp.values >= 0).all()


class TestHeadToHead:
    def test_finds_meeting(self):
        fighters = _fighters(3)
        fights = pd.DataFrame([
            {"fighter_url": "http://f/1", "opponent": "Fighter 0",
             "result": "win", "event": "UFC X", "event_date": "Jan. 01, 2024",
             "method": "KO/TKO"},
        ])
        meetings = head_to_head(fights, fighters, "Fighter 1", "Fighter 0")
        assert len(meetings) == 1
        assert meetings[0]["winner"] == "Fighter 1"
        assert meetings[0]["method"] == "KO/TKO"

    def test_loss_flips_winner(self):
        fighters = _fighters(3)
        fights = pd.DataFrame([
            {"fighter_url": "http://f/1", "opponent": "Fighter 0",
             "result": "loss", "event": "UFC X", "event_date": "", "method": "SUB"},
        ])
        meetings = head_to_head(fights, fighters, "Fighter 1", "Fighter 0")
        assert meetings[0]["winner"] == "Fighter 0"

    def test_never_met_returns_empty(self):
        fighters = _fighters(3)
        fights = pd.DataFrame([
            {"fighter_url": "http://f/1", "opponent": "Fighter 0",
             "result": "win", "event": "UFC X", "event_date": "", "method": "DEC"},
        ])
        assert head_to_head(fights, fighters, "Fighter 1", "Fighter 2") == []

    def test_upcoming_bout_excluded(self):
        fighters = _fighters(3)
        fights = pd.DataFrame([
            {"fighter_url": "http://f/1", "opponent": "Fighter 0",
             "result": "next", "event": "UFC X", "event_date": "", "method": ""},
        ])
        assert head_to_head(fights, fighters, "Fighter 1", "Fighter 0") == []

    def test_empty_fights_returns_empty(self):
        assert head_to_head(pd.DataFrame(), _fighters(2), "Fighter 1", "Fighter 0") == []
