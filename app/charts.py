"""
Plotly chart builders for the UFC dashboard.

All charts are themed with a UFC-style red/black/white palette and
return ``plotly.graph_objects.Figure`` instances for ``st.plotly_chart``.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

UFC_RED = "#D20A0A"
UFC_BLACK = "#0D0D0D"
UFC_WHITE = "#F5F5F5"
UFC_GREY = "#2A2A2A"
UFC_GOLD = "#FFB400"

PLOT_BG = "#111111"
PAPER_BG = "#0D0D0D"

RADAR_STATS = [
    ("slpm", "SLpM"),
    ("str_acc", "Str. Acc. %"),
    ("str_def", "Str. Def. %"),
    ("td_avg", "TD Avg."),
    ("td_acc", "TD Acc. %"),
    ("sub_avg", "Sub. Avg."),
]


def _base_layout(fig: go.Figure, title: str | None = None) -> go.Figure:
    """Apply the shared dark UFC layout to a figure."""
    fig.update_layout(
        title=title,
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(color=UFC_WHITE, family="Inter, sans-serif"),
        title_font=dict(color=UFC_WHITE, size=20),
        margin=dict(l=40, r=20, t=60, b=40),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=UFC_WHITE)),
    )
    fig.update_xaxes(gridcolor=UFC_GREY, zerolinecolor=UFC_GREY, color=UFC_WHITE)
    fig.update_yaxes(gridcolor=UFC_GREY, zerolinecolor=UFC_GREY, color=UFC_WHITE)
    return fig


def fighter_striking_bar(fighter: pd.Series) -> go.Figure:
    """Bar chart of a single fighter's striking metrics."""
    values = [
        fighter.get("slpm") or 0,
        fighter.get("sapm") or 0,
        fighter.get("str_acc") or 0,
        fighter.get("str_def") or 0,
    ]
    labels = ["SLpM", "SApM", "Str. Acc. %", "Str. Def. %"]
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker_color=[UFC_RED, UFC_GOLD, UFC_RED, UFC_RED],
            text=[f"{v:.2f}" if v else "—" for v in values],
            textposition="outside",
        )
    )
    return _base_layout(fig, "Striking")


def fighter_grappling_bar(fighter: pd.Series) -> go.Figure:
    """Bar chart of a single fighter's grappling metrics."""
    values = [
        fighter.get("td_avg") or 0,
        fighter.get("td_acc") or 0,
        fighter.get("td_def") or 0,
        fighter.get("sub_avg") or 0,
    ]
    labels = ["TD Avg.", "TD Acc. %", "TD Def. %", "Sub. Avg."]
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker_color=[UFC_RED, UFC_RED, UFC_RED, UFC_GOLD],
            text=[f"{v:.2f}" if v else "—" for v in values],
            textposition="outside",
        )
    )
    return _base_layout(fig, "Grappling")


def comparison_radar(fighter_a: pd.Series, fighter_b: pd.Series) -> go.Figure:
    """
    Radar chart comparing two fighters across the six core stats.

    Percentage stats are used as-is; SLpM and the count averages are
    scaled to a 0-100 range for a fair visual comparison.
    """
    def _scale(stat_key: str, value) -> float:
        if value is None or pd.isna(value):
            return 0.0
        if stat_key in {"str_acc", "str_def", "td_acc"}:
            return float(value)
        if stat_key == "slpm":
            return min(float(value) / 10 * 100, 100)
        if stat_key == "td_avg":
            return min(float(value) / 8 * 100, 100)
        if stat_key == "sub_avg":
            return min(float(value) / 4 * 100, 100)
        return float(value)

    labels = [label for _, label in RADAR_STATS]
    values_a = [_scale(k, fighter_a.get(k)) for k, _ in RADAR_STATS]
    values_b = [_scale(k, fighter_b.get(k)) for k, _ in RADAR_STATS]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=values_a + [values_a[0]],
            theta=labels + [labels[0]],
            fill="toself",
            name=fighter_a.get("name", "Fighter A"),
            line=dict(color=UFC_RED, width=2),
            fillcolor="rgba(210, 10, 10, 0.35)",
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=values_b + [values_b[0]],
            theta=labels + [labels[0]],
            fill="toself",
            name=fighter_b.get("name", "Fighter B"),
            line=dict(color=UFC_GOLD, width=2),
            fillcolor="rgba(255, 180, 0, 0.25)",
        )
    )

    fig.update_layout(
        polar=dict(
            bgcolor=PLOT_BG,
            radialaxis=dict(visible=True, range=[0, 100], color=UFC_WHITE, gridcolor=UFC_GREY),
            angularaxis=dict(color=UFC_WHITE, gridcolor=UFC_GREY),
        ),
    )
    return _base_layout(fig, "Head-to-Head Profile")


RADAR_COLORS = ["#D20A0A", "#FFB400", "#3498DB", "#2ECC71", "#9B59B6"]


def multi_radar(fighters: list[pd.Series]) -> go.Figure:
    """Radar chart overlaying up to 5 fighters on the six core stats."""
    def _scale(stat_key: str, value) -> float:
        if value is None or pd.isna(value):
            return 0.0
        if stat_key in {"str_acc", "str_def", "td_acc"}:
            return float(value)
        if stat_key == "slpm":
            return min(float(value) / 10 * 100, 100)
        if stat_key == "td_avg":
            return min(float(value) / 8 * 100, 100)
        if stat_key == "sub_avg":
            return min(float(value) / 4 * 100, 100)
        return float(value)

    labels = [label for _, label in RADAR_STATS]
    fig = go.Figure()
    for i, fighter in enumerate(fighters):
        values = [_scale(k, fighter.get(k)) for k, _ in RADAR_STATS]
        color = RADAR_COLORS[i % len(RADAR_COLORS)]
        fig.add_trace(
            go.Scatterpolar(
                r=values + [values[0]],
                theta=labels + [labels[0]],
                fill="toself",
                name=fighter.get("name", f"Fighter {i+1}"),
                line=dict(color=color, width=2),
                fillcolor=color.replace(")", ",0.25)").replace("#", "rgba(") if False else color,
                opacity=0.55,
            )
        )

    fig.update_layout(
        polar=dict(
            bgcolor=PLOT_BG,
            radialaxis=dict(visible=True, range=[0, 100], color=UFC_WHITE, gridcolor=UFC_GREY),
            angularaxis=dict(color=UFC_WHITE, gridcolor=UFC_GREY),
        ),
    )
    return _base_layout(fig, "Multi-Fighter Comparison")


def top_n_bar(df: pd.DataFrame, stat: str, label: str, n: int = 10) -> go.Figure:
    """Horizontal bar chart of the top N fighters for a given stat."""
    subset = (
        df.dropna(subset=[stat])
        .sort_values(stat, ascending=False)
        .head(n)
        .iloc[::-1]
    )
    fig = go.Figure(
        go.Bar(
            x=subset[stat],
            y=subset["name"],
            orientation="h",
            marker_color=UFC_RED,
            text=subset[stat].round(2),
            textposition="outside",
        )
    )
    fig.update_layout(height=420)
    return _base_layout(fig, f"Top {n} — {label}")


def all_fighters_scatter(
    df: pd.DataFrame,
    stat: str,
    label: str,
    color_by: str | None = "weight_class",
) -> go.Figure:
    """
    Scatter plot of every fighter against a chosen stat.

    The x-axis indexes fighters (sorted by stat) so the cloud reads
    left-to-right; the user clicks any point to inspect that fighter.
    Custom data carries enough fields for the on-click info panel.
    """
    subset = df.dropna(subset=[stat]).copy()
    subset = subset.sort_values(stat, ascending=False).reset_index(drop=True)
    subset["rank"] = subset.index + 1

    custom = subset[
        [
            "name",
            "wins",
            "losses",
            "draws",
            "weight_class",
            "stance",
            "height",
            "reach",
            stat,
        ]
    ].fillna("").values

    fig = px.scatter(
        subset,
        x="rank",
        y=stat,
        color=color_by if color_by in subset.columns else None,
        hover_name="name",
        custom_data=[
            "name",
            "wins",
            "losses",
            "draws",
            "weight_class",
            "stance",
            "height",
            "reach",
            stat,
        ],
        labels={"rank": "Rank (by stat)", stat: label},
    )
    fig.update_traces(marker=dict(size=9, line=dict(width=0.5, color=UFC_BLACK)))
    fig.update_layout(height=560, legend_title_text=color_by)
    return _base_layout(fig, f"All Fighters — {label}")


def xy_fighters_scatter(
    df: pd.DataFrame,
    x_stat: str,
    y_stat: str,
    x_label: str,
    y_label: str,
    color_by: str | None = "weight_class",
    size_by: str | None = None,
    highlight_names: list[str] | None = None,
    show_trendline: bool = False,
) -> go.Figure:
    """
    True XY scatter — every fighter as a point on a user-chosen
    (x_stat, y_stat) plane.

    If ``highlight_names`` is given those fighters are drawn on top as
    larger gold-ringed markers with name labels. Custom data carries the
    fields the dashboard needs for the on-click info panel.
    """
    subset = df.dropna(subset=[x_stat, y_stat]).copy()

    size_arg = None
    if size_by and size_by in subset.columns:
        size_series = pd.to_numeric(subset[size_by], errors="coerce")
        subset["_size"] = size_series.fillna(size_series.median() or 1).clip(lower=1)
        size_arg = "_size"

    fade_unselected = bool(highlight_names)
    fig = px.scatter(
        subset,
        x=x_stat,
        y=y_stat,
        color=color_by if color_by and color_by in subset.columns else None,
        size=size_arg,
        size_max=22,
        hover_name="name",
        custom_data=[
            "name",
            "wins",
            "losses",
            "draws",
            "weight_class",
            "stance",
            "height",
            "reach",
            x_stat,
            y_stat,
        ],
        labels={x_stat: x_label, y_stat: y_label},
    )
    base_opacity = 0.25 if fade_unselected else 0.85
    fig.update_traces(
        marker=dict(line=dict(width=0.5, color=UFC_BLACK), opacity=base_opacity)
    )

    if highlight_names:
        picks = subset[subset["name"].isin(highlight_names)]
        if not picks.empty:
            fig.add_trace(
                go.Scatter(
                    x=picks[x_stat],
                    y=picks[y_stat],
                    mode="markers+text",
                    text=picks["name"],
                    textposition="top center",
                    textfont=dict(color=UFC_WHITE, size=12),
                    name="Search match",
                    marker=dict(
                        size=18,
                        color=UFC_GOLD,
                        line=dict(width=2, color=UFC_RED),
                        symbol="star",
                    ),
                    customdata=picks[
                        [
                            "name", "wins", "losses", "draws",
                            "weight_class", "stance", "height", "reach",
                            x_stat, y_stat,
                        ]
                    ].values,
                    hovertemplate="<b>%{customdata[0]}</b><br>"
                                  f"{x_label}: %{{x}}<br>{y_label}: %{{y}}<extra></extra>",
                )
            )

    if show_trendline:
        _add_ols_trendline(fig, subset[x_stat], subset[y_stat])

    fig.update_layout(height=620, legend_title_text=color_by)
    return _base_layout(fig, f"{y_label} vs. {x_label}")


def _add_ols_trendline(fig: go.Figure, x: pd.Series, y: pd.Series) -> None:
    """
    Fit an OLS line through the (x, y) cloud and append it as a trace.

    Uses ``numpy.polyfit`` directly to avoid pulling in ``statsmodels``
    just for this. R² is included in the legend label so the user can
    judge fit quality at a glance.
    """
    xv = pd.to_numeric(x, errors="coerce")
    yv = pd.to_numeric(y, errors="coerce")
    mask = xv.notna() & yv.notna()
    xv, yv = xv[mask].to_numpy(), yv[mask].to_numpy()
    if len(xv) < 2 or np.ptp(xv) == 0:
        return  # nothing meaningful to fit

    slope, intercept = np.polyfit(xv, yv, 1)
    y_pred = slope * xv + intercept
    ss_res = float(((yv - y_pred) ** 2).sum())
    ss_tot = float(((yv - yv.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    x_line = np.array([xv.min(), xv.max()])
    y_line = slope * x_line + intercept
    fig.add_trace(
        go.Scatter(
            x=x_line,
            y=y_line,
            mode="lines",
            name=f"Trend  (R² = {r2:.2f},  slope = {slope:.3f})",
            line=dict(color=UFC_WHITE, width=2.5, dash="dash"),
            hovertemplate=(
                f"y = {slope:.3f}·x + {intercept:.3f}<br>"
                f"R² = {r2:.3f}<extra></extra>"
            ),
        )
    )


def correlation_heatmap(df: pd.DataFrame, stat_labels: dict[str, str]) -> go.Figure:
    """Pearson correlation heatmap across the chosen numeric stats."""
    cols = [c for c in stat_labels.keys() if c in df.columns]
    sub = df[cols].apply(pd.to_numeric, errors="coerce").dropna(how="all")
    corr = sub.corr(method="pearson")

    labels = [stat_labels[c] for c in cols]
    fig = go.Figure(
        go.Heatmap(
            z=corr.values,
            x=labels,
            y=labels,
            zmin=-1,
            zmax=1,
            colorscale=[
                [0.0, "#3498DB"],
                [0.5, UFC_BLACK],
                [1.0, UFC_RED],
            ],
            colorbar=dict(title="r", tickfont=dict(color=UFC_WHITE)),
            text=corr.round(2).values,
            texttemplate="%{text}",
            textfont=dict(color=UFC_WHITE, size=11),
        )
    )
    fig.update_layout(height=620)
    return _base_layout(fig, "Stat correlations (Pearson)")


def group_mean_bar(
    df: pd.DataFrame,
    group_col: str,
    stat: str,
    stat_label: str,
    group_label: str,
) -> go.Figure:
    """Mean of a stat broken down by a categorical column (stance, weight class)."""
    sub = df.dropna(subset=[stat, group_col]).copy()
    sub[stat] = pd.to_numeric(sub[stat], errors="coerce")
    agg = (
        sub.groupby(group_col)[stat]
        .agg(["mean", "count"])
        .reset_index()
        .sort_values("mean", ascending=False)
    )
    fig = go.Figure(
        go.Bar(
            x=agg[group_col],
            y=agg["mean"],
            marker_color=UFC_RED,
            text=[f"{v:.2f}<br>n={n}" for v, n in zip(agg["mean"], agg["count"])],
            textposition="outside",
        )
    )
    fig.update_layout(height=360)
    fig.update_yaxes(title=stat_label)
    fig.update_xaxes(title=group_label)
    return _base_layout(fig, f"Mean {stat_label} by {group_label}")


def stat_distribution(df: pd.DataFrame, stat: str, label: str) -> go.Figure:
    """Histogram showing the distribution of a stat across all fighters."""
    series = df[stat].dropna()
    fig = go.Figure(
        go.Histogram(
            x=series,
            marker_color=UFC_RED,
            nbinsx=40,
            opacity=0.85,
        )
    )
    fig.update_layout(bargap=0.05, height=320)
    return _base_layout(fig, f"Distribution — {label}")


def compare_table_rows(
    fighter_a: pd.Series,
    fighter_b: pd.Series,
    stats: Iterable[tuple[str, str, bool]],
) -> list[dict]:
    """
    Build rows for the color-coded comparison table.

    Each entry in ``stats`` is ``(column, label, higher_is_better)``.
    Returns dicts with the stat label, both values, and a winner key.
    """
    rows: list[dict] = []
    for col, label, higher_better in stats:
        a_val = fighter_a.get(col)
        b_val = fighter_b.get(col)

        def _num(v):
            try:
                return float(v) if v is not None and not pd.isna(v) else None
            except (TypeError, ValueError):
                return None

        a_num, b_num = _num(a_val), _num(b_val)
        winner = "tie"
        if a_num is not None and b_num is not None and a_num != b_num:
            a_better = a_num > b_num if higher_better else a_num < b_num
            winner = "a" if a_better else "b"
        rows.append(
            {
                "label": label,
                "a": a_num,
                "b": b_num,
                "winner": winner,
            }
        )
    return rows
