"""Plotly zodiac wheel and matplotlib word-cloud rendering.

The wheel is composed of four concentric guide circles with:

* segment ring (outermost): one colored wedge per zodiac sign
* planet ring: planet symbols and their degree labels
* axis/cusp lines: Asc/Desc/MC/IC and house-cusp lines
* aspect lines: chords connecting bodies with angular relationships
"""
from __future__ import annotations

import io
from pathlib import Path

import matplotlib

# Use non-interactive backend for server environments (must be set before pyplot import)
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
from wordcloud import WordCloud  # noqa: E402

from app.config import settings  # noqa: E402
from app.core.constants import ZODIAC_INFO  # noqa: E402


# Geometry derived from settings
CIRCLE_1 = settings.CIRCLE_1
CIRCLE_SPACING = settings.CIRCLE_SPACING
CIRCLE_2 = CIRCLE_1 + CIRCLE_SPACING
CIRCLE_3 = CIRCLE_2 + (4 * CIRCLE_SPACING)
CIRCLE_4 = CIRCLE_3 + CIRCLE_SPACING


# ---------------------------------------------------------------------------
# Zodiac wheel
# ---------------------------------------------------------------------------
def generate_zodiac_chart(
    bodies: pd.DataFrame,
    aspects_df: pd.DataFrame,
) -> go.Figure:
    """Render the full zodiac wheel for the given chart data.

    Parameters
    ----------
    bodies
        DataFrame from :class:`app.core.chart.Chart.bodies` with
        pre-computed ``Rotated_Pos``, ``rad_rot_x``, ``rad_rot_y``.
    aspects_df
        DataFrame from :class:`app.core.chart.Chart.aspects`.
    """
    fig = go.Figure()
    _setup_layout(fig)
    _draw_base_circles(fig)

    rotation_deg = _infer_rotation(bodies)
    zodiac = ZODIAC_INFO.copy()
    zodiac["Rotated_Pos"] = zodiac["Start Angle (°)"] - rotation_deg

    _draw_axes_and_cusps(fig, bodies)
    _draw_zodiac_segments(fig, zodiac)
    _draw_planets(fig, bodies)
    _draw_aspect_lines(fig, bodies, aspects_df)

    return fig


def _setup_layout(fig: go.Figure) -> None:
    limit = CIRCLE_4 + CIRCLE_SPACING
    fig.update_xaxes(range=[-limit, limit], showticklabels=False,
                     showgrid=False, zeroline=False)
    fig.update_yaxes(range=[-limit, limit], showticklabels=False,
                     showgrid=False, zeroline=False)
    fig.update_layout(
        showlegend=False,
        width=800,
        height=800,
        plot_bgcolor="white",
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(showgrid=False, zeroline=False),
    )


def _draw_base_circles(fig: go.Figure) -> None:
    for r, line in [
        (CIRCLE_4, dict(color="white")),
        (CIRCLE_3, dict(color="white")),
        (CIRCLE_2, dict(color="grey", width=0.5)),
        (CIRCLE_1, dict(color="grey", width=0.5)),
    ]:
        fig.add_shape(
            type="circle", xref="x", yref="y",
            x0=-r, y0=-r, x1=r, y1=r,
            line=line,
        )


def _infer_rotation(bodies: pd.DataFrame) -> float:
    """Pull the rotation (Descendant longitude) back out of pre-rotated data."""
    desc = bodies.loc[bodies["Body"] == "Desc"]
    if desc.empty:
        return 0.0
    return float(desc.iloc[0]["Longitude (°)"])


def _draw_axes_and_cusps(fig: go.Figure, bodies: pd.DataFrame) -> None:
    """Draw Asc/Desc/MC/IC lines and numbered house cusps."""
    for _, row in bodies.iterrows():
        is_axis = row["Body"] in {"Asc", "Desc", "MC", "IC"}
        is_cusp = "House Cusp" in row["Body"]
        if not (is_axis or is_cusp):
            continue

        fig.add_shape(
            type="line",
            x0=CIRCLE_1 * row["rad_rot_x"], y0=CIRCLE_1 * row["rad_rot_y"],
            x1=CIRCLE_3 * row["rad_rot_x"], y1=CIRCLE_3 * row["rad_rot_y"],
            layer="below",
            line=dict(
                color="blue" if is_axis else "grey",
                width=1.25 if is_axis else 0.5,
            ),
        )

        if is_axis:
            label_x = (CIRCLE_3 - CIRCLE_SPACING) * row["rad_rot_x"]
            label_y = (CIRCLE_3 - CIRCLE_SPACING) * row["rad_rot_y"]
            text_angle = 0 if row["Body"] in {"Asc", "Desc"} else 270
            fig.add_annotation(
                x=label_x, y=label_y,
                text=f"{row['Longitude (°)'] % 30:.2f}°",
                showarrow=False,
                font=dict(size=12, color="black"),
                xanchor="center", yanchor="middle",
                textangle=text_angle,
                bgcolor="white",
            )

    # House number annotations at cusp midpoints
    cusps = (
        bodies[bodies["Body"].str.contains("House Cusp")]
        .sort_values("Rotated_Pos")
        .reset_index(drop=True)
    )
    if cusps.empty:
        return

    mid_radius = (CIRCLE_1 + CIRCLE_2) / 2
    for i in range(len(cusps)):
        cur = np.deg2rad(cusps.iloc[i]["Rotated_Pos"])
        nxt = np.deg2rad(cusps.iloc[(i + 1) % len(cusps)]["Rotated_Pos"])
        if nxt < cur:
            nxt += 2 * np.pi
        mid = (cur + nxt) / 2
        fig.add_annotation(
            x=mid_radius * np.cos(mid),
            y=mid_radius * np.sin(mid),
            text=str(cusps.iloc[i]["House"]),
            showarrow=False,
            font=dict(size=10, color="grey"),
            xanchor="center", yanchor="middle",
        )


def _draw_zodiac_segments(fig: go.Figure, zodiac: pd.DataFrame) -> None:
    mid_r = (CIRCLE_4 + CIRCLE_3) / 2
    for _, row in zodiac.iterrows():
        start = np.deg2rad(row["Rotated_Pos"])
        end = np.deg2rad(row["Rotated_Pos"] + 30)
        theta = np.linspace(start, end, 100)

        x = np.concatenate([CIRCLE_4 * np.cos(theta), CIRCLE_3 * np.cos(theta[::-1])])
        y = np.concatenate([CIRCLE_4 * np.sin(theta), CIRCLE_3 * np.sin(theta[::-1])])

        fig.add_trace(go.Scatter(
            x=x, y=y,
            fill="toself", fillcolor="#D3D3D3",
            line=dict(width=5, color="white"),
            mode="lines", showlegend=False, hoverinfo="skip",
        ))

        # Symbol at segment midpoint
        mid_angle = np.deg2rad(row["Rotated_Pos"] + 15)
        fig.add_annotation(
            x=mid_r * np.cos(mid_angle),
            y=mid_r * np.sin(mid_angle),
            text=row["Zodiac Name"],
            showarrow=False,
            font=dict(size=CIRCLE_SPACING * 20),
        )


def _draw_planets(fig: go.Figure, bodies: pd.DataFrame) -> None:
    """Draw planet glyphs with simple stacking for tightly-conjunct planets."""
    planet_radius = CIRCLE_2 + 0.2
    text_radius = ((CIRCLE_2 + CIRCLE_3) / 2) - 0.2

    planets_only = bodies.dropna(subset=["Symbol"]).sort_values("Rotated_Pos")
    last_angle: float | None = None
    stack_offset = 0.02 * planet_radius

    for idx, (_, row) in enumerate(planets_only.iterrows()):
        angle_rad = np.deg2rad(row["Rotated_Pos"])

        # Stagger vertically when two planets are within 5°
        if last_angle is not None and abs(angle_rad - last_angle) < np.deg2rad(5):
            direction = 1 if idx % 2 == 0 else -1
            y_offset = direction * stack_offset * (idx % 3 + 1)
        else:
            y_offset = 0
        last_angle = angle_rad

        px = planet_radius * row["rad_rot_x"]
        py = planet_radius * row["rad_rot_y"] + y_offset

        fig.add_trace(go.Scatter(
            x=[px], y=[py],
            mode="text",
            text=row["Symbol"],
            textposition="middle center",
            textfont=dict(size=20, color="black"),
            hoverinfo="text",
            hovertext=row["Body"],
            showlegend=False,
        ))

        # Degree label
        tx = text_radius * row["rad_rot_x"]
        ty = text_radius * row["rad_rot_y"] + y_offset
        lon = row["Longitude (°)"]
        align = "right" if 90 < lon <= 270 else "left"
        text_angle = (
            -np.degrees(angle_rad) if 90 < lon <= 270
            else 180 - np.degrees(angle_rad)
        )
        fig.add_annotation(
            x=tx, y=ty,
            text=f"{lon % 30:.2f}°",
            showarrow=False,
            font=dict(size=10, color="black"),
            align=align,
            textangle=text_angle,
        )


def _draw_aspect_lines(
    fig: go.Figure,
    bodies: pd.DataFrame,
    aspects_df: pd.DataFrame,
) -> None:
    if aspects_df.empty:
        return

    positions = dict(zip(
        bodies["Body"],
        zip(bodies["rad_rot_x"], bodies["rad_rot_y"]),
    ))

    for _, row in aspects_df.iterrows():
        b1, b2 = row["Body1"], row["Body2"]
        if b1 not in positions or b2 not in positions:
            continue

        x0, y0 = positions[b1]
        x1, y1 = positions[b2]
        closeness = row["Closeness"]

        fig.add_shape(
            type="line",
            x0=CIRCLE_1 * x0, y0=CIRCLE_1 * y0,
            x1=CIRCLE_1 * x1, y1=CIRCLE_1 * y1,
            opacity=closeness,
            line=dict(color=row["Color"], width=2 * closeness),
        )

        fig.add_annotation(
            x=(CIRCLE_1 * x0 + CIRCLE_2 * x1) / 2,
            y=(CIRCLE_1 * y0 + CIRCLE_2 * y1) / 2,
            text=row["aspect_symbol"],
            showarrow=False,
            font=dict(size=10, color=row["Color"]),
            xanchor="center", yanchor="middle",
        )


# ---------------------------------------------------------------------------
# Word clouds
# ---------------------------------------------------------------------------
def generate_wordclouds(
    bodies: pd.DataFrame,
    personalities_csv_path: str | Path | None = None,
) -> bytes:
    """Render the strengths/stress word-cloud image as PNG bytes.

    Joins the chart against a trait-mapping CSV (planet × sign or house →
    positive/negative traits) and produces two word clouds side by side.
    """
    if personalities_csv_path is None:
        personalities_csv_path = settings.PERSONALITIES_CSV

    df_csv = pd.read_csv(personalities_csv_path, dtype=str)
    df_csv = df_csv.map(
        lambda x: x.replace(" ", "") if isinstance(x, str) else x
    )

    melted = pd.melt(
        bodies[~bodies["Body"].str.contains("Cusp")],
        id_vars=["Body", "Sys"],
        value_vars=["Sign", "House"],
        var_name="Attribute",
        value_name="Value",
    )
    merged = pd.merge(
        melted, df_csv,
        left_on=["Body", "Value"],
        right_on=["Planet", "SignsAndHouses"],
        how="left",
    )

    positives = ",".join(merged["Positives"].dropna().str.lower())
    negatives = ",".join(merged["Negatives"].dropna().str.lower())

    # WordCloud raises on empty input; fall back to a placeholder
    positives = positives or "none"
    negatives = negatives or "none"

    pos_wc = WordCloud(width=800, height=400,
                       background_color="white").generate(positives)
    neg_wc = WordCloud(width=800, height=400,
                       background_color="white").generate(negatives)

    fig = plt.figure(figsize=(15, 10))
    plt.subplot(1, 2, 1)
    plt.imshow(pos_wc, interpolation="bilinear")
    plt.axis("off")
    plt.title("Strengths")
    plt.subplot(1, 2, 2)
    plt.imshow(neg_wc, interpolation="bilinear")
    plt.axis("off")
    plt.title("Stress Causing Emotions")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()
