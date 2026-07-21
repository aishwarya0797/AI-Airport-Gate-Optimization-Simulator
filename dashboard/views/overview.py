"""
Airport Overview tab: live weather, gate layout map, and flight timeline.
"""

import streamlit as st

from simulation.airport_layout import AirportLayout
from visualization.charts import AirportVisualizer, FlightVisualizer
from dashboard.constants import WEATHER_ICONS
from dashboard.utils import require_flights, gate_status_map, chart_guide


def render_weather_panel():
    """Render current weather conditions as a metric strip."""
    weather = st.session_state.get("weather_info") or {}
    if not weather:
        st.info("☀️ Generate a flight schedule to load current weather conditions.")
        return

    condition = weather.get("condition", "Clear")
    icon = WEATHER_ICONS.get(condition, "🌡️")

    st.markdown("##### 🌦️ Current Weather Conditions")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Condition", f"{icon} {condition}")
    c2.metric("Visibility", f"{weather.get('visibility', 0):,} m")
    c3.metric("Wind Speed", f"{weather.get('wind_speed', 0)} km/h")
    c4.metric("Temperature", f"{weather.get('temperature', 0)} °C")

    if condition in ("Rain", "Fog", "Thunderstorm", "Snow"):
        st.warning(
            f"⚠️ {condition} conditions may increase turnaround times and delay probability. "
            "Consider reviewing the AI Predictions tab for at-risk flights."
        )

    chart_guide(
        "This is today's simulated weather at the airport. It's not just for show — worse "
        "weather (rain, fog, storms, snow) means planes take longer to turn around and are "
        "more likely to run late, which feeds directly into the delay predictions on the "
        "**AI Predictions** tab. ☀️ Clear skies are the best-case scenario for on-time gate turnaround."
    )


def render_airport_overview():
    """Render the interactive gate layout / status map."""
    if not require_flights("Generate a flight schedule to view the live airport gate map."):
        return

    flights = st.session_state.get("flights", [])
    gates = st.session_state.get("gates", [])
    layout = st.session_state.get("layout") or AirportLayout()

    statuses = gate_status_map(gates, flights)

    st.markdown("##### 🗺️ Live Gate Map")
    visualizer = AirportVisualizer(layout)
    fig = visualizer.create_airport_layout_plot(gate_statuses=statuses)
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})

    legend_cols = st.columns(3)
    legend_cols[0].markdown("🟢 **Available**")
    legend_cols[1].markdown("🔴 **Occupied**")
    legend_cols[2].markdown("🟠 **Reserved / Closed**")

    chart_guide(
        "This is a snapshot of every gate right now, based on whichever plan you last ran "
        "(**Allocate** or **Optimize**) — not animated over time like the Live Simulation tab. "
        "- 🟢 **Green** = the gate is free\n"
        "- 🔴 **Red** = a flight currently has this gate assigned to it\n"
        "- 🟠 **Orange** = the gate is closed or reserved (for example, during a Gate Closure scenario)\n\n"
        "Hover over any gate to see which flight is there, if any. If you want to *watch* planes "
        "move between gates over the course of the day instead of a single snapshot, check the "
        "**Live Simulation** tab."
    )


def render_flight_timeline():
    """Render the Gantt-style flight timeline grouped by gate."""
    if not require_flights("Generate a flight schedule to view the flight timeline."):
        return

    flights = st.session_state.get("flights", [])
    assigned = [f for f in flights if f.assigned_gate]

    st.markdown("##### 🕒 Flight Timeline by Gate")
    if not assigned:
        st.info("No flights are assigned to gates yet — run allocation or optimization first.")
        return

    fig = FlightVisualizer.create_flight_timeline(flights)
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})

    chart_guide(
        "Think of this like a train schedule board, but for gates. Each horizontal bar is one "
        "flight sitting at its gate — the left edge is when it arrives, the right edge is when "
        "it leaves. Read the chart left-to-right as the clock moving through the day.\n\n"
        "If you see **two bars overlapping on the same gate row** at the same point in time, "
        "that's a conflict — two flights need the same gate at once. Check the **Conflicts** tab "
        "for the full breakdown of exactly which ones and why."
    )
