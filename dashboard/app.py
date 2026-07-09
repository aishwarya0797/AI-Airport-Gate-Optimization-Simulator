"""
GateOptimizer Sim - Main Dashboard Application

AI-Powered Airport Gate Allocation Decision Support System
For Airport Authority of India (AAI)

Author: GateOptimizer Team
"""

import streamlit as st
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.components.css import load_css
from dashboard.components.session import init_session_state
from dashboard.components.header import render_header
from dashboard.components.sidebar import render_sidebar
from dashboard.handlers.actions import (
    handle_generation,
    handle_allocation,
    handle_optimization,
    handle_ml_training,
    handle_prediction,
    handle_export,
)
from dashboard.pages.overview import (
    render_weather_panel,
    render_airport_overview,
    render_flight_timeline
)
from dashboard.pages.flights import render_flight_table

from dashboard.pages.utilization import (
    render_metrics_row,
    render_utilization_charts
)
from dashboard.pages.conflicts import render_conflict_analysis
from dashboard.pages.optimization import render_optimization_comparison
from dashboard.pages.predictions import (
    render_ml_predictions,
    render_explainable_ai
)
from dashboard.pages.reports import render_reports
from dashboard.constants import APP_NAME, APP_ICON

# Page configuration
st.set_page_config(
    page_title=APP_NAME,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

load_css()
init_session_state()


def main():
    """Main application entry point."""
    render_header()

    # Render sidebar and get controls
    num_flights, weather, scenario, generate_btn, allocate_btn, optimize_btn, train_ml_btn, predict_btn, export_btn = render_sidebar()

    # Handle button actions
    if generate_btn:
        handle_generation(num_flights, weather, scenario)

    if allocate_btn:
        handle_allocation()

    if optimize_btn:
        handle_optimization()

    if train_ml_btn:
        handle_ml_training()

    if predict_btn:
        handle_prediction()

    if export_btn:
        handle_export()

    # Main content area
    st.markdown("---")

    # Metrics row
    render_metrics_row()

    st.markdown("---")

    # Main tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "Airport Overview",
        "Flight Schedule",
        "Gate Utilization",
        "Conflicts",
        "Optimization",
        "AI Predictions",
        "Reports"
    ])

    with tab1:
        render_weather_panel()
        st.markdown("---")
        render_airport_overview()
        st.markdown("---")
        render_flight_timeline()

    with tab2:
        render_flight_table()

    with tab3:
        render_utilization_charts()

    with tab4:
        render_conflict_analysis()

    with tab5:
        render_optimization_comparison()

    with tab6:
        col1, col2 = st.columns(2)
        with col1:
            render_ml_predictions()
        with col2:
            render_explainable_ai()

    with tab7:
        render_reports()
        
if __name__ == "__main__":
    main()
