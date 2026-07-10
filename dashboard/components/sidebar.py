"""
Sidebar control panel.

Renders every operator control (data generation parameters, scenario
selector, and the action buttons that drive the allocation / optimization
/ ML / export pipeline) and returns the current values to ``app.py`` so it
can dispatch to the handlers in ``dashboard.handlers.actions``.
"""

from typing import Tuple
import streamlit as st

from utils.config import config
from dashboard.constants import SCENARIOS


def render_sidebar() -> Tuple:
    """Render sidebar controls and return the operator's selections/actions."""
    with st.sidebar:
        st.markdown(
            """
            <div style="padding:6px 0 14px 0;">
                <div style="font-size:1.1rem; font-weight:800; color:#63b3ed;">
                    ⚙️ Operations Control Panel
                </div>
                <div style="font-size:0.78rem; color:#8fa5c0;">
                    Configure and drive the simulation
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("#### 1️⃣ Flight Schedule")
        num_flights = st.select_slider(
            "Number of Flights",
            options=config.simulation.num_flights_options,
            value=st.session_state.get("num_flights_last", config.simulation.default_num_flights),
            help="Number of synthetic flights to generate for this simulation run.",
        )
        num_gates = st.select_slider(
            "Number of Gates",
            options=config.airport.gate_options,
            value=st.session_state.get("num_gates_last", config.airport.default_total_gates),
            help="Total gates across 3 terminals (small/medium/large mix scales automatically).",
        )
        weather = st.selectbox(
            "Weather Condition",
            options=config.weather.conditions,
            index=config.weather.conditions.index(config.weather.default_condition),
            help="Weather scenario used to bias generated conditions/delays.",
        )
        scenario = st.selectbox(
            "Operational Scenario",
            options=SCENARIOS,
            help="Special operating conditions to inject into the generated schedule.",
        )
        generate_btn = st.button("🚀 Generate Flight Schedule", width='stretch', type="primary")

        st.markdown("---")
        st.markdown("#### 2️⃣ Gate Allocation")
        col_a, col_b = st.columns(2)
        with col_a:
            allocate_btn = st.button("🗺️ Allocate", width='stretch',
                                      help="Run the rule-based allocator and detect conflicts.")
        with col_b:
            optimize_btn = st.button("⚡ Optimize", width='stretch',
                                      help="Run the OR-Tools optimization engine.")

        st.markdown("---")
        st.markdown("#### 3️⃣ AI / Machine Learning")
        train_ml_btn = st.button("🧠 Train ML Models", width='stretch')

        flights = st.session_state.get("flights", [])
        if flights:
            flight_labels = {
                f"{f.flight_number} ({f.arrival_time.strftime('%H:%M')}, {f.aircraft_size})": f.flight_id
                for f in flights
            }
            selected_label = st.selectbox(
                "Flight to Predict / Explain",
                options=list(flight_labels.keys()),
                key="selected_flight_label",
            )
            st.session_state["selected_flight_id"] = flight_labels.get(selected_label)
        else:
            st.caption("Generate flights to enable predictions.")

        predict_btn = st.button("🔮 Predict & Explain", width='stretch')

        st.markdown("---")
        st.markdown("#### 4️⃣ Reports")
        export_btn = st.button("📤 Generate Export Bundle", width='stretch')

        st.markdown("---")
        _render_quick_stats()

    return (
        num_flights, num_gates, weather, scenario,
        generate_btn, allocate_btn, optimize_btn,
        train_ml_btn, predict_btn, export_btn,
    )


def _render_quick_stats():
    """Render a compact snapshot of current simulation state in the sidebar."""
    st.markdown("#### 📊 Session Snapshot")
    flights = st.session_state.get("flights", [])
    gates = st.session_state.get("gates", [])
    conflicts = st.session_state.get("conflicts", [])

    c1, c2 = st.columns(2)
    c1.metric("Flights", len(flights))
    c2.metric("Gates", len(gates))

    c3, c4 = st.columns(2)
    c3.metric("Conflicts", len(conflicts))
    c4.metric(
        "ML Ready",
        "Yes" if st.session_state.get("ml_trained") else "No",
    )
