from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


UFC_RED = "#EF4444"
UFC_RED_DEEP = "#DC2626"
UFC_BLACK = "#0A0D14"
UFC_WHITE = "#F4F4F5"
UFC_GREY = "#1B2230"
UFC_GOLD = "#F59E0B"
ACCENT_EMERALD = "#10B981"
ACCENT_SKY = "#38BDF8"
ACCENT_VIOLET = "#A78BFA"
ACCENT_PINK = "#F472B6"
TEXT_MUTED = "#A1A1AA"
GRID_LINE = "rgba(255,255,255,0.06)"
GRID_LINE_STRONG = "rgba(255,255,255,0.12)"

PLOT_BG = "#0F1420"
PAPER_BG = "#0A0D14"

FONT_FAMILY = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"

CATEGORICAL_PALETTE = [
    UFC_RED, ACCENT_SKY, UFC_GOLD, ACCENT_EMERALD, ACCENT_VIOLET, ACCENT_PINK,
    "#FB923C", "#22D3EE", "#E879F9", "#84CC16",
]

RADAR_STATS = [
    ("slpm", "SLpM"),
    ("str_acc", "Str. Acc. %"),
    ("str_def", "Str. Def. %"),
    ("td_avg", "TD Avg."),
    ("td_acc", "TD Acc. %"),
    ("sub_avg", "Sub. Avg."),
]

RADAR_COLORS = [UFC_RED, UFC_GOLD, ACCENT_SKY, ACCENT_EMERALD, ACCENT_VIOLET]


def _hover_label() -> dict:
    return dict(
        bgcolor="rgba(15,20,32,0.95)",
        bordercolor=GRID_LINE_STRONG,
        font=dict(color=UFC_WHITE, family=FONT_FAMILY, size=12),
    )


def _base_layout(fig: go.Figure, title: str | None = None) -> go.Figure:
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(color=UFC_WHITE, size=18, family=FONT_FAMILY, weight=600),
            x=0.0,
            xanchor="left",
            y=0.96,
            pad=dict(l=8, t=6),
        ) if title else None,
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(color=UFC_WHITE, family=FONT_FAMILY, size=12),
        margin=dict(l=50, r=24, t=70, b=50),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT_MUTED, family=FONT_FAMILY, size=11),
            borderwidth=0,
        ),
        hoverlabel=_hover_label(),
        hovermode="closest",
        transition=dict(duration=300, easing="cubic-in-out"),
    )
    fig.update_xaxes(
        gridcolor=GRID_LINE,
        zerolinecolor=GRID_LINE_STRONG,
        color=TEXT_MUTED,
        showline=False,
        ticks="outside",
        tickcolor=GRID_LINE,
        tickfont=dict(family=FONT_FAMILY, size=11),
    )
    fig.update_yaxes(
        gridcolor=GRID_LINE,
        zerolinecolor=GRID_LINE_STRONG,
        color=TEXT_MUTED,
        showline=False,
        ticks="outside",
        tickcolor=GRID_LINE,
        tickfont=dict(family=FONT_FAMILY, size=11),
    )
    return fig


def _gradient_bar(values: list[float], base_color: str = UFC_RED) -> list[str]:
    if not values:
        return []
    mx = max(values) or 1
    out = []
    for v in values:
        ratio = (v / mx) if v else 0.2
        alpha = 0.45 + 0.55 * ratio
        out.append(_rgba(base_color, alpha))
    return out


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha:.3f})"


def fighter_striking_bar(fighter: pd.Series) -> go.Figure:
    values = [
        fighter.get("slpm") or 0,
        fighter.get("sapm") or 0,
        fighter.get("str_acc") or 0,
        fighter.get("str_def") or 0,
    ]
    labels = ["SLpM", "SApM", "Str. Acc.", "Str. Def."]
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker=dict(
                color=_gradient_bar(values, UFC_RED),
                line=dict(width=0),
            ),
            text=[f"{v:.2f}" if v else "—" for v in values],
            textposition="outside",
            textfont=dict(color=UFC_WHITE, family=FONT_FAMILY, size=11),
            hovertemplate="<b>%{x}</b><br>%{y:.2f}<extra></extra>",
        )
    )
    fig.update_layout(bargap=0.45, height=320, showlegend=False)
    return _base_layout(fig, "Striking")


def fighter_grappling_bar(fighter: pd.Series) -> go.Figure:
    values = [
        fighter.get("td_avg") or 0,
        fighter.get("td_acc") or 0,
        fighter.get("td_def") or 0,
        fighter.get("sub_avg") or 0,
    ]
    labels = ["TD Avg.", "TD Acc.", "TD Def.", "Sub. Avg."]
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker=dict(
                color=_gradient_bar(values, ACCENT_SKY),
                line=dict(width=0),
            ),
            text=[f"{v:.2f}" if v else "—" for v in values],
            textposition="outside",
            textfont=dict(color=UFC_WHITE, family=FONT_FAMILY, size=11),
            hovertemplate="<b>%{x}</b><br>%{y:.2f}<extra></extra>",
        )
    )
    fig.update_layout(bargap=0.45, height=320, showlegend=False)
    return _base_layout(fig, "Grappling")


def _scale_radar(stat_key: str, value) -> float:
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


def _radar_polar_layout() -> dict:
    return dict(
        bgcolor=PLOT_BG,
        radialaxis=dict(
            visible=True,
            range=[0, 100],
            color=TEXT_MUTED,
            gridcolor=GRID_LINE,
            tickfont=dict(family=FONT_FAMILY, size=10),
            angle=90,
            tickangle=90,
        ),
        angularaxis=dict(
            color=UFC_WHITE,
            gridcolor=GRID_LINE_STRONG,
            tickfont=dict(family=FONT_FAMILY, size=12, color=UFC_WHITE),
        ),
    )


def comparison_radar(fighter_a: pd.Series, fighter_b: pd.Series) -> go.Figure:
    labels = [label for _, label in RADAR_STATS]
    values_a = [_scale_radar(k, fighter_a.get(k)) for k, _ in RADAR_STATS]
    values_b = [_scale_radar(k, fighter_b.get(k)) for k, _ in RADAR_STATS]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=values_a + [values_a[0]],
            theta=labels + [labels[0]],
            fill="toself",
            name=fighter_a.get("name", "Fighter A"),
            line=dict(color=UFC_RED, width=2.5),
            fillcolor=_rgba(UFC_RED, 0.22),
            marker=dict(size=6, color=UFC_RED),
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=values_b + [values_b[0]],
            theta=labels + [labels[0]],
            fill="toself",
            name=fighter_b.get("name", "Fighter B"),
            line=dict(color=ACCENT_SKY, width=2.5),
            fillcolor=_rgba(ACCENT_SKY, 0.22),
            marker=dict(size=6, color=ACCENT_SKY),
        )
    )
    fig.update_layout(polar=_radar_polar_layout(), height=480)
    return _base_layout(fig, "Head-to-Head Profile")


def multi_radar(fighters: list[pd.Series]) -> go.Figure:
    labels = [label for _, label in RADAR_STATS]
    fig = go.Figure()
    for i, fighter in enumerate(fighters):
        values = [_scale_radar(k, fighter.get(k)) for k, _ in RADAR_STATS]
        color = RADAR_COLORS[i % len(RADAR_COLORS)]
        fig.add_trace(
            go.Scatterpolar(
                r=values + [values[0]],
                theta=labels + [labels[0]],
                fill="toself",
                name=fighter.get("name", f"Fighter {i+1}"),
                line=dict(color=color, width=2.5),
                fillcolor=_rgba(color, 0.18),
                marker=dict(size=6, color=color),
            )
        )
    fig.update_layout(polar=_radar_polar_layout(), height=520)
    return _base_layout(fig, "Multi-Fighter Comparison")


def top_n_bar(df: pd.DataFrame, stat: str, label: str, n: int = 10) -> go.Figure:
    subset = (
        df.dropna(subset=[stat])
        .sort_values(stat, ascending=False)
        .head(n)
        .iloc[::-1]
    )
    values = subset[stat].tolist()
    fig = go.Figure(
        go.Bar(
            x=values,
            y=subset["name"],
            orientation="h",
            marker=dict(
                color=_gradient_bar(values, UFC_RED),
                line=dict(width=0),
            ),
            text=[f"{v:.2f}" for v in values],
            textposition="outside",
            textfont=dict(color=UFC_WHITE, family=FONT_FAMILY, size=11),
            hovertemplate="<b>%{y}</b><br>%{x:.2f}<extra></extra>",
        )
    )
    fig.update_layout(height=440, bargap=0.3, showlegend=False)
    return _base_layout(fig, f"Top {n} — {label}")


def all_fighters_scatter(
    df: pd.DataFrame,
    stat: str,
    label: str,
    color_by: str | None = "weight_class",
) -> go.Figure:
    subset = df.dropna(subset=[stat]).copy()
    subset = subset.sort_values(stat, ascending=False).reset_index(drop=True)
    subset["rank"] = subset.index + 1

    fig = px.scatter(
        subset,
        x="rank",
        y=stat,
        color=color_by if color_by in subset.columns else None,
        hover_name="name",
        color_discrete_sequence=CATEGORICAL_PALETTE,
        custom_data=[
            "name", "wins", "losses", "draws",
            "weight_class", "stance", "height", "reach", stat,
        ],
        labels={"rank": "Rank (by stat)", stat: label},
    )
    fig.update_traces(
        marker=dict(size=8, line=dict(width=0)),
        opacity=0.85,
    )
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
        size_max=24,
        hover_name="name",
        color_discrete_sequence=CATEGORICAL_PALETTE,
        custom_data=[
            "name", "wins", "losses", "draws",
            "weight_class", "stance", "height", "reach", x_stat, y_stat,
        ],
        labels={x_stat: x_label, y_stat: y_label},
    )
    base_opacity = 0.22 if fade_unselected else 0.75
    fig.update_traces(
        marker=dict(
            line=dict(width=0),
            opacity=base_opacity,
        ),
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
                    textfont=dict(color=UFC_WHITE, size=12, family=FONT_FAMILY),
                    name="Selected",
                    marker=dict(
                        size=16,
                        color=UFC_GOLD,
                        line=dict(width=2, color=UFC_WHITE),
                        symbol="diamond",
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
    xv = pd.to_numeric(x, errors="coerce")
    yv = pd.to_numeric(y, errors="coerce")
    mask = xv.notna() & yv.notna()
    xv, yv = xv[mask].to_numpy(), yv[mask].to_numpy()
    if len(xv) < 2 or np.ptp(xv) == 0:
        return

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
            name=f"Trend (R² = {r2:.2f}, slope = {slope:.3f})",
            line=dict(color=UFC_WHITE, width=2, dash="dot"),
            hovertemplate=(
                f"y = {slope:.3f}·x + {intercept:.3f}<br>"
                f"R² = {r2:.3f}<extra></extra>"
            ),
        )
    )


def correlation_heatmap(df: pd.DataFrame, stat_labels: dict[str, str]) -> go.Figure:
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
                [0.0, ACCENT_SKY],
                [0.5, PLOT_BG],
                [1.0, UFC_RED],
            ],
            colorbar=dict(
                title=dict(text="r", font=dict(color=TEXT_MUTED)),
                tickfont=dict(color=TEXT_MUTED, family=FONT_FAMILY, size=10),
                thickness=12,
                outlinewidth=0,
            ),
            text=corr.round(2).values,
            texttemplate="%{text}",
            textfont=dict(color=UFC_WHITE, size=10, family=FONT_FAMILY),
            hovertemplate="<b>%{y}</b> × <b>%{x}</b><br>r = %{z:.2f}<extra></extra>",
            xgap=2,
            ygap=2,
        )
    )
    fig.update_layout(height=640)
    return _base_layout(fig, "Stat correlations (Pearson)")


def group_mean_bar(
    df: pd.DataFrame,
    group_col: str,
    stat: str,
    stat_label: str,
    group_label: str,
) -> go.Figure:
    sub = df.dropna(subset=[stat, group_col]).copy()
    sub[stat] = pd.to_numeric(sub[stat], errors="coerce")
    agg = (
        sub.groupby(group_col)[stat]
        .agg(["mean", "count"])
        .reset_index()
        .sort_values("mean", ascending=False)
    )
    values = agg["mean"].tolist()
    fig = go.Figure(
        go.Bar(
            x=agg[group_col],
            y=values,
            marker=dict(color=_gradient_bar(values, UFC_RED), line=dict(width=0)),
            text=[f"{v:.2f}<br><span style='color:{TEXT_MUTED}'>n={n}</span>"
                  for v, n in zip(values, agg["count"])],
            textposition="outside",
            textfont=dict(color=UFC_WHITE, family=FONT_FAMILY, size=11),
            hovertemplate=f"<b>%{{x}}</b><br>{stat_label}: %{{y:.2f}}<extra></extra>",
        )
    )
    fig.update_layout(height=380, bargap=0.4, showlegend=False)
    fig.update_yaxes(title=stat_label)
    fig.update_xaxes(title=group_label)
    return _base_layout(fig, f"Mean {stat_label} by {group_label}")


def stat_distribution(df: pd.DataFrame, stat: str, label: str) -> go.Figure:
    series = df[stat].dropna()
    fig = go.Figure(
        go.Histogram(
            x=series,
            marker=dict(
                color=_rgba(UFC_RED, 0.75),
                line=dict(width=1, color=PAPER_BG),
            ),
            nbinsx=40,
            hovertemplate=f"{label}: %{{x}}<br>Count: %{{y}}<extra></extra>",
        )
    )
    fig.update_layout(bargap=0.04, height=320, showlegend=False)
    return _base_layout(fig, f"Distribution — {label}")


def compare_table_rows(
    fighter_a: pd.Series,
    fighter_b: pd.Series,
    stats: Iterable[tuple[str, str, bool]],
) -> list[dict]:
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
            {"label": label, "a": a_num, "b": b_num, "winner": winner}
        )
    return rows
