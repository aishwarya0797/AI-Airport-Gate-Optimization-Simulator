"""
Top-level KPI strip and Gate Utilization tab.
"""

import numpy as np
import streamlit as st

from simulation.airport_layout import AirportLayout
from visualization.charts import AirportVisualizer, MetricsVisualizer
from dashboard.utils import require_flights, safe_mean


def render_metrics_row():
    """Render the always-visible KPI strip shown above the tabs."""
    flights = st.session_state.get("flights", [])
    gates = st.session_state.get("gates", [])
    conflicts = st.session_state.get("conflicts", [])
    optimization_metrics = st.session_state.get("optimization_metrics", {})
    rule_based_summary = st.session_state.get("rule_based_summary", {})

    total_flights = len(flights)
    assigned_flights = sum(1 for f in flights if f.assigned_gate)
    avg_delay = safe_mean([f.delay for f in flights]) if flights else 0.0

    if optimization_metrics:
        avg_utilization = optimization_metrics.get("average_gate_utilization", 0.0)
    else:
        avg_utilization = 0.0

    critical_conflicts = sum(1 for c in conflicts if getattr(c, "severity", "") == "critical")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Flights", f"{total_flights}")
    c2.metric(
        "Gates Assigned",
        f"{assigned_flights}/{total_flights}" if total_flights else "0/0",
        delta=f"{rule_based_summary.get('success_rate', 0):.0f}% success" if rule_based_summary else None,
    )
    c3.metric("Avg Gate Utilization", f"{avg_utilization:.1f}%")
    c4.metric(
        "Active Conflicts",
        f"{len(conflicts)}",
        delta=f"{critical_conflicts} critical" if critical_conflicts else "none critical",
        delta_color="inverse" if critical_conflicts else "normal",
    )
    c5.metric("Avg Delay", f"{avg_delay:.1f} min")


def render_utilization_charts():
    """Render the gate utilization bar chart and heatmap."""
    if not require_flights("Generate a flight schedule to see gate utilization."):
        return

    optimization_metrics = st.session_state.get("optimization_metrics", {})
    simulation_results = st.session_state.get("simulation_results", {})

    gate_utilization = optimization_metrics.get("gate_utilization") or simulation_results.get("stats", {}).get(
        "gate_utilization"
    )

    if not gate_utilization:
        st.info(
            "Run **Allocate** and/or **Optimize** from the sidebar to compute gate utilization."
        )
        return

    layout = st.session_state.get("layout") or AirportLayout()

    col1, col2 = st.columns([3, 2])
    with col1:
        fig_bar = MetricsVisualizer.create_utilization_bar_chart(gate_utilization)
        st.plotly_chart(fig_bar, width='stretch', config={"displayModeBar": False})
    with col2:
        visualizer = AirportVisualizer(layout)
        fig_heat = visualizer.create_utilization_heatmap(gate_utilization)
        st.plotly_chart(fig_heat, width='stretch', config={"displayModeBar": False})

    values = list(gate_utilization.values())
    st.caption(
        f"Average: {np.mean(values):.1f}% • Peak: {max(values):.1f}% • "
        f"Lowest: {min(values):.1f}% across {len(values)} gates"
    )
