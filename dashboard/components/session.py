"""
Session state initialization.

Streamlit re-runs the whole script on every interaction, so any state
that must survive across a rerun (generated flights, allocation results,
trained ML models, etc.) is stashed in ``st.session_state``. This module
defines the single canonical set of keys used throughout the dashboard so
no other module needs to guess whether a key already exists.
"""

import streamlit as st


def init_session_state():
    """Initialize all session state keys used across the dashboard, once."""
    defaults = {
        # --- Core generated data -------------------------------------------------
        "flights": [],
        "gates": [],
        "layout": None,
        "generator": None,
        "weather_info": {},
        "scenario": "Normal Operations",
        "data_generated": False,
        "num_flights_last": 100,
        "num_gates_last": 12,

        # --- Rule-based allocation ------------------------------------------------
        "allocated": False,
        "rule_based_assignments": {},
        "rule_based_results": [],
        "rule_based_summary": {},

        # --- Naive allocation (comparison baseline) --------------------------------
        "naive_assignments": {},
        "naive_results": [],
        "naive_summary": {},

        # --- Conflict detection -----------------------------------------------------
        "conflicts_detected": False,
        "conflicts": [],
        "conflict_summary": {},

        # --- Simulation ---------------------------------------------------------------
        "simulation_results": {},

        # --- Optimization ---------------------------------------------------------------
        "optimized": False,
        "optimized_assignments": {},
        "optimization_stats": {},
        "optimization_metrics": {},
        "naive_metrics": {},
        "rule_based_metrics": {},
        "comparison": {},

        # --- Machine learning -----------------------------------------------------------
        "ml_trained": False,
        "ml_pipeline": None,
        "ml_results": {},
        "explainer": None,
        "explainer_ready": False,

        # --- Predictions / explanations for a selected flight ----------------------------
        "predictions": {},
        "selected_flight_id": None,

        # --- Reports / export ------------------------------------------------------------
        "export_data": {},
        "last_report": None,

        # --- Misc UI state ----------------------------------------------------------------
        "last_action_message": None,
        "last_action_status": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
