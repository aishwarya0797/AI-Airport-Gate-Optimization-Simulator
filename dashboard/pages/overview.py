"""
Airport Overview tab: live weather, gate layout map, and flight timeline.
"""

import streamlit as st

from simulation.airport_layout import AirportLayout
from visualization.charts import AirportVisualizer, FlightVisualizer
from dashboard.constants import WEATHER_ICONS
from dashboard.utils import require_flights, gate_status_map


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
