"""
Live Simulation tab: an animated, control-tower-style view of aircraft
moving onto, sitting at, and pushing back from their assigned gates over
the course of the simulated day.

Draws a proper airport backdrop (terminal bands, gate boxes, taxiway,
runway) with Plotly shapes/annotations, then layers a frame-based
animation of labeled flight markers on top (play/pause + scrub slider).
Gates with an active conflict flash red, and the flight currently
selected in the sidebar (for ML predictions) gets a glowing halo so it's
easy to track through the animation.
"""

from datetime import timedelta

import plotly.graph_objects as go
import streamlit as st

from simulation.airport_layout import AirportLayout
from dashboard.constants import SEVERITY_COLORS
from dashboard.utils import require_flights

APPROACH_MINUTES = 80   # how long a plane is shown "inbound" before arrival (split across 2 legs)
DEPARTURE_MINUTES = 80  # how long a plane is shown "departing" after pushback (split across 2 legs)

SIZE_COLOR = {"small": "#63b3ed", "medium": "#48bb78", "large": "#ed8936"}
STATUS_COLOR = {"Inbound": "#ecc94b", "At Gate": None, "Departing": "#e53e3e"}
SIZE_MARKER = {"small": 11, "medium": 14, "large": 18}
HIGHLIGHT_COLOR = "#f6e05e"

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


def _static_backdrop(positions, x_range, y_range):
    """Build the parts of the backdrop that never change: terminal bands, taxiway, runway."""
    shapes = []
    annotations = []

    terminals = sorted({t for (_, _, t, _) in positions.values()})
    x_min, x_max = x_range
    y_min, y_max = y_range
    band_left = x_min - TERMINAL_BAND_PAD - 60
    band_right = x_max + TERMINAL_BAND_PAD

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

    # Gate ID labels (static; only the gate box fill/border below changes per frame)
    for gid, (gx, gy, term, size) in positions.items():
        color = SIZE_COLOR.get(size, "#a0aec0")
        annotations.append(dict(
            x=gx, y=gy - GATE_BOX_H / 2 - 10, text=gid,
            showarrow=False, font=dict(size=9, color=color), xanchor="center",
        ))
        shapes.append(dict(
            type="line", x0=gx, x1=gx, y0=gy + GATE_BOX_H / 2, y1=gy + GATE_BOX_H / 2 + 14,
            line=dict(color="#22314a", width=1, dash="dot"),
        ))

    taxiway_y = y_min - TERMINAL_BAND_PAD - 30
    shapes.append(dict(
        type="line", x0=band_left, x1=band_right, y0=taxiway_y, y1=taxiway_y,
        line=dict(color="#4a5568", width=2, dash="dash"),
    ))
    annotations.append(dict(
        x=band_right - 10, y=taxiway_y + 10, text="TAXIWAY — planes drive here between gate and runway",
        showarrow=False, font=dict(size=9, color="#4a5568"), xanchor="right",
    ))

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
        x=band_right - 10, y=runway_y + 26, text="RUNWAY — planes take off and land here",
        showarrow=False, font=dict(size=9, color="#a0aec0"), xanchor="right",
    ))

    full_y_range = (runway_y - 40, y_max + TERMINAL_BAND_PAD + 30)
    full_x_range = (band_left - 40, band_right + 20)
    return shapes, annotations, full_x_range, full_y_range, taxiway_y, runway_y


def _gate_box_shapes(positions, conflicted_gates, flash_on):
    """
    Per-frame gate box shapes. Gates with an active conflict at this frame's
    time are drawn with a bright, thick border that alternates every other
    frame (flash_on) so the animation reads as a blinking alert; unaffected
    gates keep their normal size-colored outline.
    """
    shapes = []
    for gid, (gx, gy, term, size) in positions.items():
        base_color = SIZE_COLOR.get(size, "#a0aec0")
        severity = conflicted_gates.get(gid)

        if severity and flash_on:
            color = SEVERITY_COLORS.get(severity, "#e53e3e")
            width = 3.5
            fill = "rgba(229, 62, 62, 0.22)"
        elif severity:
            color = base_color
            width = 2
            fill = "rgba(15, 23, 42, 0.9)"
        else:
            color = base_color
            width = 2
            fill = "rgba(15, 23, 42, 0.9)"

        shapes.append(dict(
            type="rect",
            x0=gx - GATE_BOX_W / 2, x1=gx + GATE_BOX_W / 2,
            y0=gy - GATE_BOX_H / 2, y1=gy + GATE_BOX_H / 2,
            fillcolor=fill, line=dict(color=color, width=width),
            layer="below",
        ))
    return shapes


def _active_conflicts_at(conflicts, t):
    """{gate_id: worst_severity} for conflicts whose time window covers t."""
    severity_rank = {"critical": 3, "high": 2, "medium": 1, "low": 0}
    active = {}
    for c in conflicts:
        if c.start_time <= t < c.end_time:
            current = active.get(c.gate_id)
            if current is None or severity_rank.get(c.severity, 0) > severity_rank.get(current, 0):
                active[c.gate_id] = c.severity
    return active


def _flight_positions_at(flights, positions, full_x_range, taxiway_y, runway_y, t, selected_flight_id):
    """Compute marker x/y/color/size/label/hover for every visible flight at time t,
    plus a separate halo entry if the selected flight is currently visible.

    Inbound/departing flights are routed through a two-segment path (holding
    point out past the runway -> taxiway under their gate -> the gate itself)
    instead of a single straight line, so the motion actually reads as
    "landing and taxiing in" rather than teleporting.
    """
    xs, ys, colors, sizes, labels, hover = [], [], [], [], [], []
    halo_x, halo_y = [], []
    holding_x = full_x_range[0] + 30

    for f in flights:
        if not f.assigned_gate or f.assigned_gate not in positions:
            continue
        gate_x, gate_y, _, _ = positions[f.assigned_gate]
        departure_time = f.arrival_time + timedelta(minutes=f.turnaround_time + f.delay)
        approach_start = f.arrival_time - timedelta(minutes=APPROACH_MINUTES)
        taxi_in_start = f.arrival_time - timedelta(minutes=APPROACH_MINUTES / 2)
        taxi_out_end = departure_time + timedelta(minutes=DEPARTURE_MINUTES / 2)
        departed_end = departure_time + timedelta(minutes=DEPARTURE_MINUTES)

        if approach_start <= t < taxi_in_start:
            # Leg 1: inbound from the holding point, along the runway line.
            progress = (t - approach_start).total_seconds() / ((APPROACH_MINUTES / 2) * 60)
            x = holding_x + (gate_x - holding_x) * progress
            y = runway_y
            status = "Inbound"
        elif taxi_in_start <= t < f.arrival_time:
            # Leg 2: taxi up from the runway, along the taxiway, into the gate.
            progress = (t - taxi_in_start).total_seconds() / ((APPROACH_MINUTES / 2) * 60)
            x = gate_x
            y = runway_y + (gate_y - runway_y) * progress
            status = "Inbound"
        elif f.arrival_time <= t < departure_time:
            x, y = gate_x, gate_y
            status = "At Gate"
        elif departure_time <= t < taxi_out_end:
            # Leg 1: push back from the gate down to the taxiway.
            progress = (t - departure_time).total_seconds() / ((DEPARTURE_MINUTES / 2) * 60)
            x = gate_x
            y = gate_y + (runway_y - gate_y) * progress
            status = "Departing"
        elif taxi_out_end <= t < departed_end:
            # Leg 2: taxi out along the runway and head off into the distance.
            progress = (t - taxi_out_end).total_seconds() / ((DEPARTURE_MINUTES / 2) * 60)
            x = gate_x + (holding_x - gate_x) * progress
            y = runway_y
            status = "Departing"
        else:
            continue

        status_label = {
            "Inbound": "Inbound (landing soon)",
            "At Gate": "Parked at gate",
            "Departing": "Departing (pushed back)",
        }[status]
        color = STATUS_COLOR.get(status) or SIZE_COLOR.get(f.aircraft_size, "#a0aec0")
        xs.append(x)
        ys.append(y)
        colors.append(color)
        sizes.append(SIZE_MARKER.get(f.aircraft_size, 12) + (4 if status != "At Gate" else 0))
        labels.append(f.flight_number)
        hover.append(
            f"✈️ {f.flight_number} — {f.airline}<br>"
            f"Gate: {f.assigned_gate}<br>"
            f"Status: {status_label}<br>"
            f"{f.aircraft_type} • {f.passenger_count} passengers"
        )

        if selected_flight_id and f.flight_id == selected_flight_id:
            halo_x.append(x)
            halo_y.append(y)

    return xs, ys, colors, sizes, labels, hover, halo_x, halo_y


def _halo_trace(halo_x, halo_y):
    return go.Scatter(
        x=halo_x, y=halo_y, mode="markers",
        marker=dict(size=32, color=HIGHLIGHT_COLOR, opacity=0.35,
                    line=dict(color=HIGHLIGHT_COLOR, width=2)),
        hoverinfo="skip", showlegend=False, name="highlight",
    )


def _flights_trace(xs, ys, colors, sizes, labels, hover):
    return go.Scatter(
        x=xs, y=ys, mode="markers+text",
        marker=dict(size=sizes, color=colors, symbol="circle",
                    line=dict(color="#0b1220", width=1.5)),
        text=labels, textposition="top center",
        textfont=dict(size=9, color="#e2e8f0"),
        hovertext=hover, hoverinfo="text",
        showlegend=False, name="flights",
    )


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
    static_shapes, static_annotations, full_x_range, full_y_range, taxiway_y, runway_y = _static_backdrop(
        positions, x_range, y_range
    )

    conflicts = st.session_state.get("conflicts", [])
    selected_flight_id = st.session_state.get("selected_flight_id")

    col1, col2 = st.columns([1, 1])
    with col1:
        step_minutes = st.select_slider(
            "Time step per frame", options=[10, 15, 20, 30, 60], value=10,
            help="Smaller steps = smoother, more visible motion but more frames to render.",
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

    def build_frame(t, frame_idx):
        xs, ys, colors, sizes, labels, hover, halo_x, halo_y = _flight_positions_at(
            assigned_flights, positions, full_x_range, taxiway_y, runway_y, t, selected_flight_id
        )
        conflicted_gates = _active_conflicts_at(conflicts, t)
        flash_on = (frame_idx % 2 == 0)
        gate_shapes = _gate_box_shapes(positions, conflicted_gates, flash_on)

        return go.Frame(
            data=[_halo_trace(halo_x, halo_y), _flights_trace(xs, ys, colors, sizes, labels, hover)],
            name=t.strftime("%H:%M"),
            layout=go.Layout(
                annotations=static_annotations + [clock_annotation(t, len(xs))],
                shapes=static_shapes + gate_shapes,
            ),
        )

    frames = [build_frame(t, i) for i, t in enumerate(times)]

    init_xs, init_ys, init_colors, init_sizes, init_labels, init_hover, init_halo_x, init_halo_y = (
        _flight_positions_at(assigned_flights, positions, full_x_range, taxiway_y, runway_y, times[0], selected_flight_id)
    )
    init_gate_shapes = _gate_box_shapes(positions, _active_conflicts_at(conflicts, times[0]), True)

    fig = go.Figure(
        data=[
            _halo_trace(init_halo_x, init_halo_y),
            _flights_trace(init_xs, init_ys, init_colors, init_sizes, init_labels, init_hover),
        ],
        frames=frames,
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(6, 12, 24, 0.6)",
        height=560,
        margin=dict(l=10, r=10, t=10, b=10),
        shapes=static_shapes + init_gate_shapes,
        annotations=static_annotations + [clock_annotation(times[0], len(init_xs))],
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
    st.caption(
        "👋 Watch flights move through the airport across a full day — landing, "
        "parking at their gate, and taking off again — just like a real airport display board."
    )

    with st.expander("❓ How to read this map (click to expand)", expanded=False):
        st.markdown(
            """
- **The three shaded rows** are the airport's terminals — each holds a row of numbered gates (G1, G2, ...).
- **A colored dot with a flight number** is a plane. Where it sits tells you what it's doing:
    - 🟡 **Yellow** = about to land, on its way in
    - 🔵🟢🟠 **Blue / Green / Orange** = parked at its gate (color just shows the plane's size — small / medium / large)
    - 🔴 **Red** = has left the gate and is heading out
- **A gate box that flashes bright red** means that gate is double-booked at that moment — two flights need it at once.
- **A gold glowing circle** around a plane means it's the flight you picked in the sidebar to get an AI prediction for.
- **Hover over any plane** to see its flight number, airline, gate, and passenger count.
- Press **▶ Play** to watch the whole day unfold automatically, or drag the **slider** at the bottom to jump to any time yourself.
            """
        )

    st.markdown(
        "🔵 Small &nbsp;•&nbsp; 🟢 Medium &nbsp;•&nbsp; 🟠 Large &nbsp;plane parked &nbsp;&nbsp;|&nbsp;&nbsp; "
        "🟡 Landing &nbsp;&nbsp;|&nbsp;&nbsp; 🔴 Taking off &nbsp;&nbsp;|&nbsp;&nbsp; "
        "🚨 Flashing box = gate conflict"
    )

    if selected_flight_id:
        selected = next((f for f in assigned_flights if f.flight_id == selected_flight_id), None)
        if selected:
            st.caption(f"✨ Highlighting **{selected.flight_number}** (selected in sidebar) with a gold halo when it's on screen.")

    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
    st.caption(
        f"Simulated day: {day_start.strftime('%H:%M')} – {day_end.strftime('%H:%M')} • "
        f"{len(assigned_flights)} gated flights animated • click ▶ Play or drag the slider."
    )
