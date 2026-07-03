from __future__ import annotations

from typing import NamedTuple

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURE_COLS = [
    "slpm", "str_acc", "sapm", "str_def",
    "td_avg", "td_acc", "td_def", "sub_avg",
    "height_in", "reach_in",
]

FEATURE_LABELS = {
    "slpm": "Str. Landed/min",
    "str_acc": "Str. Accuracy %",
    "sapm": "Str. Absorbed/min",
    "str_def": "Str. Defense %",
    "td_avg": "TD Avg/15min",
    "td_acc": "TD Accuracy %",
    "td_def": "TD Defense %",
    "sub_avg": "Sub Avg/15min",
    "height_in": "Height (in)",
    "reach_in": "Reach (in)",
}

MIN_TRAINING_SAMPLES = 50


class ModelReport(NamedTuple):
    pipeline: Pipeline
    accuracy: float
    auc: float
    n_fights: int


def _fighter_lookup(fighters: pd.DataFrame) -> pd.DataFrame:
    available = [c for c in FEATURE_COLS if c in fighters.columns]
    num = fighters[["name"] + available].copy()
    for c in available:
        num[c] = pd.to_numeric(num[c], errors="coerce")
    return num.drop_duplicates(subset=["name"]).set_index("name")


def _available_cols(fighters: pd.DataFrame) -> list[str]:
    return [c for c in FEATURE_COLS if c in fighters.columns]


def build_training_data(
    fighters: pd.DataFrame,
    fights: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray]:
    lookup = _fighter_lookup(fighters)
    available = _available_cols(fighters)
    url_to_name = fighters.set_index("url")["name"].to_dict()

    X_rows: list[np.ndarray] = []
    y_rows: list[int] = []
    seen_bouts: set[tuple] = set()

    for _, row in fights.iterrows():
        result = (row.get("result") or "").strip().lower()
        if result not in {"win", "loss"}:
            continue
        fname = url_to_name.get(row.get("fighter_url", ""), "")
        oname = (row.get("opponent") or "").strip()
        if not fname or not oname:
            continue
        if fname not in lookup.index or oname not in lookup.index:
            continue

        bout_key = (
            tuple(sorted((fname.lower(), oname.lower()))),
            str(row.get("event", "")).strip().lower(),
        )
        if bout_key in seen_bouts:
            continue
        seen_bouts.add(bout_key)

        f_entry = lookup.loc[fname]
        o_entry = lookup.loc[oname]
        if isinstance(f_entry, pd.DataFrame):
            f_entry = f_entry.iloc[0]
        if isinstance(o_entry, pd.DataFrame):
            o_entry = o_entry.iloc[0]
        f_stats = f_entry[available].values.astype(float)
        o_stats = o_entry[available].values.astype(float)
        diff = f_stats - o_stats
        if diff.ndim != 1 or len(diff) != len(available):
            continue
        X_rows.append(diff)
        y_rows.append(1 if result == "win" else 0)

    if not X_rows:
        return np.empty((0, len(available))), np.empty(0, dtype=int)

    X = np.array(X_rows, dtype=float)
    y = np.array(y_rows, dtype=int)
    col_means = np.nan_to_num(np.nanmean(X, axis=0))
    for i in range(X.shape[1]):
        mask = np.isnan(X[:, i])
        X[mask, i] = col_means[i]
    return X, y


def _make_pipeline() -> Pipeline:
    return Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=1000, C=1.0, random_state=42)),
    ])


def train_model(fighters: pd.DataFrame, fights: pd.DataFrame) -> ModelReport | None:
    X, y = build_training_data(fighters, fights)
    if len(X) < MIN_TRAINING_SAMPLES or len(np.unique(y)) < 2:
        return None

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    eval_pipe = _make_pipeline()
    eval_pipe.fit(X_train, y_train)
    accuracy = float(eval_pipe.score(X_test, y_test))
    try:
        auc = float(roc_auc_score(y_test, eval_pipe.predict_proba(X_test)[:, 1]))
    except ValueError:
        auc = float("nan")

    final_pipe = _make_pipeline()
    final_pipe.fit(X, y)
    return ModelReport(
        pipeline=final_pipe,
        accuracy=accuracy,
        auc=auc,
        n_fights=len(X),
    )


def predict_proba(
    pipe: Pipeline,
    fighters: pd.DataFrame,
    name1: str,
    name2: str,
) -> float | None:
    lookup = _fighter_lookup(fighters)
    available = _available_cols(fighters)
    if name1 not in lookup.index or name2 not in lookup.index:
        return None
    f1 = lookup.loc[name1][available].values.astype(float)
    f2 = lookup.loc[name2][available].values.astype(float)
    diff = np.where(np.isnan(f1 - f2), 0.0, f1 - f2).reshape(1, -1)
    return float(pipe.predict_proba(diff)[0][1])


def feature_importances(pipe: Pipeline, fighters: pd.DataFrame) -> pd.Series:
    available = _available_cols(fighters)
    coefs = pipe.named_steps["clf"].coef_[0]
    n = min(len(coefs), len(available))
    return pd.Series(
        np.abs(coefs[:n]),
        index=[FEATURE_LABELS.get(c, c) for c in available[:n]],
    ).sort_values(ascending=True)


def head_to_head(
    fights: pd.DataFrame,
    fighters: pd.DataFrame,
    name1: str,
    name2: str,
) -> list[dict]:
    if fights is None or fights.empty:
        return []
    name_to_url = fighters.drop_duplicates(subset=["name"]).set_index("name")["url"].to_dict()
    url1 = name_to_url.get(name1)
    if not url1:
        return []
    own = fights[fights["fighter_url"] == url1]
    meetings = []
    for _, row in own.iterrows():
        if (row.get("opponent") or "").strip().lower() != name2.strip().lower():
            continue
        result = (row.get("result") or "").strip().lower()
        if result not in {"win", "loss", "draw", "nc", "no contest"}:
            continue
        if result == "win":
            winner = name1
        elif result == "loss":
            winner = name2
        else:
            winner = None
        meetings.append({
            "winner": winner,
            "method": row.get("method", ""),
            "event": row.get("event", ""),
            "date": row.get("event_date", ""),
        })
    return meetings
