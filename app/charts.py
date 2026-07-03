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
    ("td_def", "TD Def. %"),
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
    if stat_key in {"str_acc", "str_def", "td_acc", "td_def"}:
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


def fight_timeline(own_fights: pd.DataFrame, fighter_name: str) -> go.Figure:
    df = own_fights.copy()
    if "event_date_parsed" in df.columns and df["event_date_parsed"].notna().any():
        df = df.sort_values("event_date_parsed", ascending=True, na_position="first")
    else:
        df = df.iloc[::-1]

    net = 0
    nets: list[int] = []
    colors: list[str] = []
    hovers: list[str] = []
    for _, row in df.iterrows():
        result = str(row.get("result", "")).strip().lower()
        if result == "win":
            net += 1
            colors.append(ACCENT_EMERALD)
        elif result == "loss":
            net -= 1
            colors.append("#F43F5E")
        else:
            colors.append(TEXT_MUTED)
        nets.append(net)
        hovers.append(
            f"<b>{result.upper() or '?'}</b> vs {row.get('opponent', '?')}<br>"
            f"{row.get('method', '')} · {row.get('event', '')}<br>"
            f"{row.get('event_date', '')}"
        )

    x = list(range(1, len(nets) + 1))
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=nets,
        mode="lines",
        line=dict(color=_rgba(ACCENT_SKY, 0.5), width=2, shape="spline", smoothing=0.6),
        hoverinfo="skip",
        showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=x, y=nets,
        mode="markers",
        marker=dict(size=9, color=colors, line=dict(width=1, color=PAPER_BG)),
        hovertext=hovers,
        hovertemplate="%{hovertext}<extra></extra>",
        showlegend=False,
    ))
    fig.add_hline(y=0, line=dict(color=GRID_LINE_STRONG, width=1, dash="dot"))
    fig.update_layout(height=320)
    fig.update_xaxes(title="UFC fight #", dtick=max(1, len(x) // 12))
    fig.update_yaxes(title="Net record (W − L)")
    return _base_layout(fig, f"Career trajectory — {fighter_name}")


def win_method_donut(fighter: pd.Series) -> go.Figure:
    parts = [
        ("KO", fighter.get("ko_wins"), UFC_RED),
        ("TKO", fighter.get("tko_wins"), "#FB923C"),
        ("SUB", fighter.get("sub_wins"), ACCENT_SKY),
        ("DEC", fighter.get("dec_wins"), ACCENT_VIOLET),
    ]
    labels, values, colors = [], [], []
    for label, val, color in parts:
        v = pd.to_numeric(val, errors="coerce")
        if pd.notna(v) and v > 0:
            labels.append(label)
            values.append(int(v))
            colors.append(color)

    fig = go.Figure()
    if values:
        fig.add_trace(go.Pie(
            labels=labels,
            values=values,
            hole=0.62,
            marker=dict(colors=colors, line=dict(width=2, color=PAPER_BG)),
            textinfo="label+value",
            textfont=dict(color=UFC_WHITE, family=FONT_FAMILY, size=12),
            hovertemplate="<b>%{label}</b><br>%{value} wins (%{percent})<extra></extra>",
            sort=False,
        ))
        fig.add_annotation(
            text=f"<b>{sum(values)}</b><br><span style='font-size:11px;color:{TEXT_MUTED}'>UFC wins</span>",
            showarrow=False,
            font=dict(color=UFC_WHITE, size=22, family=FONT_FAMILY),
        )
    else:
        fig.add_annotation(
            text="No UFC wins on record",
            showarrow=False,
            font=dict(color=TEXT_MUTED, size=13, family=FONT_FAMILY),
        )
    fig.update_layout(height=320, showlegend=False)
    return _base_layout(fig, "Win methods")


def win_prob_gauge(name1: str, name2: str, prob1: float) -> go.Figure:
    prob2 = 1.0 - prob1
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[prob1], y=[""],
        orientation="h",
        name=name1,
        marker_color=UFC_RED,
        text=f"{prob1 * 100:.1f}%",
        textposition="inside",
        insidetextanchor="start",
        textfont=dict(color=UFC_WHITE, family=FONT_FAMILY, size=15, weight=700),
        hovertemplate=f"<b>{name1}</b><br>{prob1 * 100:.1f}%<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=[prob2], y=[""],
        orientation="h",
        name=name2,
        marker_color=ACCENT_SKY,
        text=f"{prob2 * 100:.1f}%",
        textposition="inside",
        insidetextanchor="end",
        textfont=dict(color=UFC_WHITE, family=FONT_FAMILY, size=15, weight=700),
        hovertemplate=f"<b>{name2}</b><br>{prob2 * 100:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        barmode="stack",
        height=110,
        margin=dict(l=0, r=0, t=50, b=10),
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        showlegend=True,
        legend=dict(
            orientation="h",
            y=-1.1,
            x=0.5,
            xanchor="center",
            font=dict(color=UFC_WHITE, family=FONT_FAMILY, size=12),
        ),
        xaxis=dict(range=[0, 1], showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        title=dict(
            text="Win Probability",
            font=dict(color=UFC_WHITE, size=15, family=FONT_FAMILY, weight=600),
            x=0.0,
        ),
    )
    return fig


def feature_importance_bar(importances: pd.Series) -> go.Figure:
    values = list(importances.values)
    fig = go.Figure(go.Bar(
        x=values,
        y=list(importances.index),
        orientation="h",
        marker=dict(
            color=_gradient_bar(values, UFC_RED),
            line=dict(width=0),
        ),
        text=[f"{v:.3f}" for v in values],
        textposition="outside",
        textfont=dict(color=UFC_WHITE, family=FONT_FAMILY, size=11),
        hovertemplate="<b>%{y}</b><br>|coef| = %{x:.3f}<extra></extra>",
    ))
    fig.update_layout(height=380, bargap=0.25, showlegend=False)
    fig.update_xaxes(title="Coefficient magnitude")
    return _base_layout(fig, "Feature Importance")


def network_graph_figure(
    fighters: pd.DataFrame,
    fights: pd.DataFrame,
    weight_class: str | None = None,
    top_n: int = 60,
) -> go.Figure:
    import networkx as nx

    url_to_name = fighters.set_index("url")["name"].to_dict()
    url_to_wc = (
        fighters.set_index("url")["weight_class"].to_dict()
        if "weight_class" in fighters.columns else {}
    )

    if weight_class and weight_class != "All":
        eligible = set(fighters[fighters["weight_class"] == weight_class]["url"])
    else:
        eligible = set(fighters["url"])

    col = "ufc_fights_counted" if "ufc_fights_counted" in fighters.columns else "total_fights"
    eligible_df = fighters[fighters["url"].isin(eligible)].copy()
    eligible_df["_sort"] = pd.to_numeric(eligible_df[col], errors="coerce").fillna(0)
    top_urls = set(eligible_df.nlargest(top_n, "_sort")["url"])

    completed = fights[
        fights["result"].str.lower().isin({"win", "loss"}) &
        fights["fighter_url"].isin(top_urls)
    ].copy()

    G = nx.Graph()
    for _, row in completed.iterrows():
        fname = url_to_name.get(row.get("fighter_url", ""), "")
        oname = (row.get("opponent") or "").strip()
        if not fname or not oname:
            continue
        result = (row.get("result") or "").lower()
        G.add_node(fname)
        G.add_node(oname)
        if G.has_edge(fname, oname):
            G[fname][oname]["weight"] += 1
        else:
            G.add_edge(fname, oname, weight=1,
                       winner=fname if result == "win" else oname)

    if not G.nodes:
        fig = go.Figure()
        return _base_layout(fig, "Fighter Network — no data")

    pos = nx.spring_layout(G, seed=42, k=1.5 / max(1, len(G.nodes) ** 0.5))
    degrees = dict(G.degree())
    max_deg = max(degrees.values()) if degrees else 1

    edge_x: list[float | None] = []
    edge_y: list[float | None] = []
    for u, v in G.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        mode="lines",
        line=dict(width=0.5, color="rgba(255,255,255,0.07)"),
        hoverinfo="none",
        showlegend=False,
    )

    _WC_COLORS: dict[str, str] = {
        "Heavyweight": "#EF4444",
        "Light Heavyweight": "#F97316",
        "Middleweight": "#EAB308",
        "Welterweight": "#22C55E",
        "Lightweight": "#06B6D4",
        "Featherweight": "#3B82F6",
        "Bantamweight": "#8B5CF6",
        "Flyweight": "#EC4899",
        "Women's Strawweight": "#F43F5E",
        "Women's Flyweight": "#D946EF",
        "Women's Bantamweight": "#A855F7",
        "Women's Featherweight": "#6366F1",
    }
    name_to_url = fighters.set_index("name")["url"].to_dict() if "name" in fighters.columns else {}

    nodes = list(G.nodes())
    node_x = [pos[n][0] for n in nodes]
    node_y = [pos[n][1] for n in nodes]
    node_sizes = [8 + 20 * (degrees[n] / max_deg) for n in nodes]

    label_cutoff = sorted(degrees.values(), reverse=True)[
        min(14, len(degrees) - 1)
    ] if degrees else 0
    node_labels = [n if degrees[n] >= max(label_cutoff, 2) else "" for n in nodes]

    def _node_color(name: str) -> str:
        url = name_to_url.get(name, "")
        wc = url_to_wc.get(url, "")
        return _WC_COLORS.get(wc, ACCENT_SKY)

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        hoverinfo="text",
        hovertext=[f"<b>{n}</b><br>{degrees[n]} connections" for n in nodes],
        text=node_labels,
        textposition="top center",
        textfont=dict(size=9, color="rgba(255,255,255,0.75)", family=FONT_FAMILY),
        showlegend=False,
        marker=dict(
            size=node_sizes,
            color=[_node_color(n) for n in nodes],
            line=dict(width=0.5, color="rgba(255,255,255,0.2)"),
        ),
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    _base_layout(fig, f"Fighter Network — top {top_n} by UFC bouts")
    fig.update_layout(
        height=720,
        margin=dict(l=0, r=0, t=60, b=0),
        showlegend=False,
        hovermode="closest",
    )
    fig.update_xaxes(showgrid=False, zeroline=False, showticklabels=False)
    fig.update_yaxes(showgrid=False, zeroline=False, showticklabels=False)
    return fig


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
