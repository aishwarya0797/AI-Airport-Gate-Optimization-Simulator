"""
Live Simulation tab: an animated, real-time-style view of aircraft moving
onto, sitting at, and pushing back from their assigned gates over the
course of the simulated day.

Built on top of the same gate coordinates used by
visualization.charts.AirportVisualizer, with a Plotly frame-based
animation (play/pause + scrub slider) layered on top.
"""

from datetime import timedelta

import plotly.graph_objects as go
import streamlit as st

from simulation.airport_layout import AirportLayout
from dashboard.utils import require_flights

APPROACH_MINUTES = 20   # how long a plane is shown "inbound" before arrival
DEPARTURE_MINUTES = 20  # how long a plane is shown "departing" after pushback

SIZE_COLOR = {"small": "#63b3ed", "medium": "#48bb78", "large": "#ed8936"}
SIZE_MARKER = {"small": 10, "medium": 14, "large": 18}


def _gate_positions(layout: AirportLayout):
    """Extract {gate_id: (x, y)} plus min/max extents from the layout."""
    positions = {gid: (g["x_coord"], g["y_coord"]) for gid, g in layout.gates.items()}
    xs = [p[0] for p in positions.values()]
    ys = [p[1] for p in positions.values()]
    return positions, (min(xs), max(xs)), (min(ys), max(ys))


def _base_gate_trace(layout: AirportLayout):
    """Static background trace: gate boxes + labels, drawn once per frame."""
    xs, ys, labels = [], [], []
    for gid, g in layout.gates.items():
        xs.append(g["x_coord"])
        ys.append(g["y_coord"])
        labels.append(gid)

    return go.Scatter(
        x=xs, y=ys,
        mode="markers+text",
        marker=dict(size=34, color="#1a2c4d", line=dict(color="#3182ce", width=2), symbol="square"),
        text=labels,
        textposition="middle center",
        textfont=dict(size=9, color="#8fa5c0"),
        hoverinfo="skip",
        showlegend=False,
        name="gates",
    )


def _flight_positions_at(flights, positions, x_range, t):
    """Compute marker x/y/color/size/hover for every visible flight at time t."""
    xs, ys, colors, sizes, hover, symbols = [], [], [], [], [], []
    sky_x = x_range[0] - 140

    for f in flights:
        if not f.assigned_gate or f.assigned_gate not in positions:
            continue
        gate_x, gate_y = positions[f.assigned_gate]
        departure_time = f.arrival_time + timedelta(minutes=f.turnaround_time + f.delay)
        approach_start = f.arrival_time - timedelta(minutes=APPROACH_MINUTES)
        departed_end = departure_time + timedelta(minutes=DEPARTURE_MINUTES)

        if approach_start <= t < f.arrival_time:
            # Inbound: interpolate from the "sky" holding point to the gate.
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

        xs.append(x)
        ys.append(y)
        colors.append(SIZE_COLOR.get(f.aircraft_size, "#a0aec0"))
        sizes.append(SIZE_MARKER.get(f.aircraft_size, 12))
        symbols.append("triangle-right" if status != "At Gate" else "circle")
        hover.append(
            f"{f.flight_number} ({f.airline})<br>Gate: {f.assigned_gate}<br>"
            f"Status: {status}<br>{f.aircraft_type}"
        )

    return xs, ys, colors, sizes, symbols, hover


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

    frames = []
    for t in times:
        xs, ys, colors, sizes, symbols, hover = _flight_positions_at(assigned_flights, positions, x_range, t)
        frames.append(
            go.Frame(
                data=[go.Scatter(
                    x=xs, y=ys, mode="markers",
                    marker=dict(size=sizes, color=colors, symbol=symbols,
                                line=dict(color="#0b1220", width=1)),
                    text=hover, hoverinfo="text",
                    showlegend=False, name="flights",
                )],
                name=t.strftime("%H:%M"),
            )
        )

    initial_xs, initial_ys, initial_colors, initial_sizes, initial_symbols, initial_hover = (
        _flight_positions_at(assigned_flights, positions, x_range, times[0])
    )

    fig = go.Figure(
        data=[
            _base_gate_trace(layout),
            go.Scatter(
                x=initial_xs, y=initial_ys, mode="markers",
                marker=dict(size=initial_sizes, color=initial_colors, symbol=initial_symbols,
                            line=dict(color="#0b1220", width=1)),
                text=initial_hover, hoverinfo="text", showlegend=False, name="flights",
            ),
        ],
        frames=frames,
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=520,
        margin=dict(l=20, r=20, t=30, b=10),
        xaxis=dict(range=[x_range[0] - 180, x_range[1] + 60], visible=False),
        yaxis=dict(range=[y_range[0] - 60, y_range[1] + 60], visible=False, scaleanchor="x"),
        updatemenus=[{
            "type": "buttons",
            "direction": "left",
            "x": 0.0, "y": -0.05, "xanchor": "left", "yanchor": "top",
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
            "x": 0.08, "y": -0.05, "len": 0.9,
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
    legend_cols = st.columns(4)
    legend_cols[0].markdown("🔵 **Small aircraft**")
    legend_cols[1].markdown("🟢 **Medium aircraft**")
    legend_cols[2].markdown("🟠 **Large aircraft**")
    legend_cols[3].markdown("▶ **Triangle = inbound / departing**")

    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
    st.caption(
        f"Simulated day: {day_start.strftime('%H:%M')} – {day_end.strftime('%H:%M')} • "
        f"{len(assigned_flights)} gated flights animated • click ▶ Play or drag the slider."
    )
