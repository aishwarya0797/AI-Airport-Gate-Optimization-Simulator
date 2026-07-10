"""
Live Simulation tab: an animated, control-tower-style view of aircraft
moving onto, sitting at, and pushing back from their assigned gates over
the course of the simulated day.

Draws a proper airport backdrop (terminal bands, gate boxes, taxiway,
runway) with Plotly shapes/annotations, then layers a frame-based
animation of labeled flight markers on top (play/pause + scrub slider).
"""

from datetime import timedelta

import plotly.graph_objects as go
import streamlit as st

from simulation.airport_layout import AirportLayout
from dashboard.utils import require_flights

APPROACH_MINUTES = 20   # how long a plane is shown "inbound" before arrival
DEPARTURE_MINUTES = 20  # how long a plane is shown "departing" after pushback

SIZE_COLOR = {"small": "#63b3ed", "medium": "#48bb78", "large": "#ed8936"}
STATUS_COLOR = {"Inbound": "#ecc94b", "At Gate": None, "Departing": "#e53e3e"}
SIZE_MARKER = {"small": 11, "medium": 14, "large": 18}

GATE_BOX_W, GATE_BOX_H = 46, 30
TERMINAL_BAND_PAD = 46


def _gate_positions(layout: AirportLayout):
    """Extract {gate_id: (x, y, terminal, size)} plus axis extents."""
    positions = {}
    for gid, g in layout.gates.items():
        positions[gid] = (g["x_coord"], g["y_coord"], g["terminal"], g["size"])
    xs = [p[0] for p in positions.values()]
    ys = [p[1] for p in positions.values()]
    return positions, (min(xs), max(xs)), (min(ys), max(ys))


def _airport_backdrop_shapes_and_annotations(layout: AirportLayout, positions, x_range, y_range):
    """Build the static airport backdrop: terminal bands, gate boxes/labels, taxiway, runway."""
    shapes = []
    annotations = []

    terminals = sorted({t for (_, _, t, _) in positions.values()})
    x_min, x_max = x_range
    y_min, y_max = y_range
    band_left = x_min - TERMINAL_BAND_PAD - 60
    band_right = x_max + TERMINAL_BAND_PAD

    # Terminal background bands
    for term in terminals:
        term_ys = [y for (_, y, t, _) in positions.values() if t == term]
        band_top = max(term_ys) + TERMINAL_BAND_PAD
        band_bottom = min(term_ys) - TERMINAL_BAND_PAD
        shapes.append(dict(
            type="rect", x0=band_left, x1=band_right, y0=band_bottom, y1=band_top,
            fillcolor="rgba(49, 130, 206, 0.06)", line=dict(color="#22314a", width=1),
            layer="below",
        ))
        annotations.append(dict(
            x=band_left + 8, y=band_top - 12, text=f"<b>TERMINAL {term}</b>",
            showarrow=False, font=dict(size=11, color="#63b3ed"), xanchor="left",
        ))

    # Gate boxes + labels
    for gid, (gx, gy, term, size) in positions.items():
        color = SIZE_COLOR.get(size, "#a0aec0")
        shapes.append(dict(
            type="rect",
            x0=gx - GATE_BOX_W / 2, x1=gx + GATE_BOX_W / 2,
            y0=gy - GATE_BOX_H / 2, y1=gy + GATE_BOX_H / 2,
            fillcolor="rgba(15, 23, 42, 0.9)", line=dict(color=color, width=2),
            layer="below",
        ))
        annotations.append(dict(
            x=gx, y=gy - GATE_BOX_H / 2 - 10, text=gid,
            showarrow=False, font=dict(size=9, color=color), xanchor="center",
        ))
        # Jet bridge stub connecting gate to the taxiway
        shapes.append(dict(
            type="line", x0=gx, x1=gx, y0=gy + GATE_BOX_H / 2, y1=gy + GATE_BOX_H / 2 + 14,
            line=dict(color="#22314a", width=1, dash="dot"),
        ))

    # Taxiway (horizontal line under the lowest terminal band)
    taxiway_y = y_min - TERMINAL_BAND_PAD - 30
    shapes.append(dict(
        type="line", x0=band_left, x1=band_right, y0=taxiway_y, y1=taxiway_y,
        line=dict(color="#4a5568", width=2, dash="dash"),
    ))
    annotations.append(dict(
        x=band_right - 10, y=taxiway_y + 10, text="TAXIWAY",
        showarrow=False, font=dict(size=9, color="#4a5568"), xanchor="right",
    ))

    # Runway (thick strip further out, with dashed centerline)
    runway_y = taxiway_y - 60
    shapes.append(dict(
        type="rect", x0=band_left, x1=band_right, y0=runway_y - 16, y1=runway_y + 16,
        fillcolor="rgba(74, 85, 104, 0.25)", line=dict(color="#4a5568", width=1),
        layer="below",
    ))
    shapes.append(dict(
        type="line", x0=band_left, x1=band_right, y0=runway_y, y1=runway_y,
        line=dict(color="#e2e8f0", width=1, dash="dash"),
    ))
    annotations.append(dict(
        x=band_right - 10, y=runway_y + 26, text="RUNWAY 10/28",
        showarrow=False, font=dict(size=9, color="#a0aec0"), xanchor="right",
    ))

    full_y_range = (runway_y - 40, y_max + TERMINAL_BAND_PAD + 30)
    full_x_range = (band_left - 40, band_right + 20)
    return shapes, annotations, full_x_range, full_y_range


def _flight_positions_at(flights, positions, x_range, t):
    """Compute marker x/y/color/size/label/hover for every visible flight at time t."""
    xs, ys, colors, sizes, labels, hover = [], [], [], [], [], []
    sky_x = x_range[0] + 30

    for f in flights:
        if not f.assigned_gate or f.assigned_gate not in positions:
            continue
        gate_x, gate_y, _, _ = positions[f.assigned_gate]
        departure_time = f.arrival_time + timedelta(minutes=f.turnaround_time + f.delay)
        approach_start = f.arrival_time - timedelta(minutes=APPROACH_MINUTES)
        departed_end = departure_time + timedelta(minutes=DEPARTURE_MINUTES)

        if approach_start <= t < f.arrival_time:
            progress = (t - approach_start).total_seconds() / (APPROACH_MINUTES * 60)
            x = sky_x + (gate_x - sky_x) * progress
            y = gate_y
            status = "Inbound"
        elif f.arrival_time <= t < departure_time:
            x, y = gate_x, gate_y
            status = "At Gate"
        elif departure_time <= t < departed_end:
            progress = (t - departure_time).total_seconds() / (DEPARTURE_MINUTES * 60)
            x = gate_x + (sky_x - gate_x) * progress
            y = gate_y
            status = "Departing"
        else:
            continue

        color = STATUS_COLOR.get(status) or SIZE_COLOR.get(f.aircraft_size, "#a0aec0")
        xs.append(x)
        ys.append(y)
        colors.append(color)
        sizes.append(SIZE_MARKER.get(f.aircraft_size, 12) + (4 if status != "At Gate" else 0))
        labels.append(f.flight_number)
        hover.append(
            f"{f.flight_number} ({f.airline})<br>Gate: {f.assigned_gate}<br>"
            f"Status: {status}<br>{f.aircraft_type} • {f.passenger_count} pax"
        )

    return xs, ys, colors, sizes, labels, hover, sum(1 for _ in xs)


def render_live_simulation():
    """Render the animated real-time gate/flight simulation."""
    if not require_flights("Generate a flight schedule to view the live simulation."):
        return

    flights = st.session_state.get("flights", [])
    assigned_flights = [f for f in flights if f.assigned_gate]

    if not assigned_flights:
        st.info("Run **Allocate** or **Optimize** from the sidebar so flights have gates to animate.")
        return

    layout = st.session_state.get("layout") or AirportLayout()
    positions, x_range, y_range = _gate_positions(layout)
    shapes, backdrop_annotations, full_x_range, full_y_range = _airport_backdrop_shapes_and_annotations(
        layout, positions, x_range, y_range
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        step_minutes = st.select_slider(
            "Time step per frame", options=[10, 15, 20, 30, 60], value=20,
            help="Smaller steps = smoother motion but more frames to render.",
        )
    with col2:
        frame_speed = st.select_slider(
            "Playback speed", options=["Slow", "Normal", "Fast"], value="Normal",
        )
    speed_ms = {"Slow": 700, "Normal": 350, "Fast": 120}[frame_speed]

    day_start = min(f.arrival_time for f in assigned_flights).replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(hours=24)

    times = []
    t = day_start
    while t <= day_end:
        times.append(t)
        t += timedelta(minutes=step_minutes)

    def clock_annotation(t, active_count):
        return dict(
            x=full_x_range[0] + 10, y=full_y_range[1] - 10,
            text=f"<b>🕐 {t.strftime('%H:%M')}</b>  •  ✈ {active_count} active",
            showarrow=False, font=dict(size=14, color="#e2e8f0"), xanchor="left", yanchor="top",
        )

    frames = []
    for t in times:
        xs, ys, colors, sizes, labels, hover, count = _flight_positions_at(assigned_flights, positions, x_range, t)
        frames.append(
            go.Frame(
                data=[go.Scatter(
                    x=xs, y=ys, mode="markers+text",
                    marker=dict(size=sizes, color=colors, symbol="circle",
                                line=dict(color="#0b1220", width=1.5)),
                    text=labels, textposition="top center",
                    textfont=dict(size=9, color="#e2e8f0"),
                    hovertext=hover, hoverinfo="text",
                    showlegend=False, name="flights",
                )],
                name=t.strftime("%H:%M"),
                layout=go.Layout(annotations=backdrop_annotations + [clock_annotation(t, count)]),
            )
        )

    init_xs, init_ys, init_colors, init_sizes, init_labels, init_hover, init_count = (
        _flight_positions_at(assigned_flights, positions, x_range, times[0])
    )

    fig = go.Figure(
        data=[go.Scatter(
            x=init_xs, y=init_ys, mode="markers+text",
            marker=dict(size=init_sizes, color=init_colors, symbol="circle",
                        line=dict(color="#0b1220", width=1.5)),
            text=init_labels, textposition="top center",
            textfont=dict(size=9, color="#e2e8f0"),
            hovertext=init_hover, hoverinfo="text", showlegend=False, name="flights",
        )],
        frames=frames,
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(6, 12, 24, 0.6)",
        height=560,
        margin=dict(l=10, r=10, t=10, b=10),
        shapes=shapes,
        annotations=backdrop_annotations + [clock_annotation(times[0], init_count)],
        xaxis=dict(range=[full_x_range[0], full_x_range[1]], visible=False, fixedrange=True),
        yaxis=dict(range=[full_y_range[0], full_y_range[1]], visible=False, fixedrange=True, scaleanchor="x"),
        updatemenus=[{
            "type": "buttons",
            "direction": "left",
            "x": 0.0, "y": -0.06, "xanchor": "left", "yanchor": "top",
            "showactive": False,
            "buttons": [
                {
                    "label": "▶ Play",
                    "method": "animate",
                    "args": [None, {"frame": {"duration": speed_ms, "redraw": True},
                                     "fromcurrent": True, "transition": {"duration": 0}}],
                },
                {
                    "label": "⏸ Pause",
                    "method": "animate",
                    "args": [[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate"}],
                },
            ],
        }],
        sliders=[{
            "active": 0,
            "x": 0.1, "y": -0.06, "len": 0.88,
            "currentvalue": {"prefix": "Time: ", "font": {"color": "#e2e8f0"}},
            "steps": [
                {
                    "label": fr.name,
                    "method": "animate",
                    "args": [[fr.name], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
                }
                for fr in frames
            ],
        }],
    )

    st.markdown("##### 🛬 Live Airport Simulation")
    legend_cols = st.columns(5)
    legend_cols[0].markdown("🔵 **Small**")
    legend_cols[1].markdown("🟢 **Medium**")
    legend_cols[2].markdown("🟠 **Large**")
    legend_cols[3].markdown("🟡 **Inbound**")
    legend_cols[4].markdown("🔴 **Departing**")

    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
    st.caption(
        f"Simulated day: {day_start.strftime('%H:%M')} – {day_end.strftime('%H:%M')} • "
        f"{len(assigned_flights)} gated flights animated • click ▶ Play or drag the slider."
    )