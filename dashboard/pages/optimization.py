"""
Optimization tab: naive vs rule-based vs OR-Tools comparison.
"""

import streamlit as st

from visualization.charts import MetricsVisualizer
from dashboard.utils import require_flights


def render_optimization_comparison():
    """Render optimizer status plus naive-vs-optimized comparison charts."""
    if not require_flights("Generate a flight schedule to run optimization."):
        return

    if not st.session_state.get("optimized"):
        st.info("Click **Optimize** in the sidebar to run the OR-Tools optimization engine.")
        return

    stats = st.session_state.get("optimization_stats", {})
    metrics = st.session_state.get("optimization_metrics", {})
    naive_metrics = st.session_state.get("naive_metrics", {})
    comparison = st.session_state.get("comparison", {})

    status = stats.get("status", "unknown")
    num_unassigned = stats.get("num_unassigned", 0)

    if status == "optimal" and num_unassigned == 0:
        st.success("✅ Optimizer converged to a mathematically optimal solution — every flight is gated.")
    elif status in ("optimal", "feasible") and num_unassigned > 0:
        st.warning(
            f"⚠️ Optimizer found its best possible plan, but {num_unassigned} of "
            f"{stats.get('num_flights', num_unassigned)} flights could not be seated at any gate — "
            "there are more overlapping, size-compatible flights than gates at some point in the day. "
            "Generate fewer flights, add more gates, or treat these as remote-stand flights."
        )
    elif status == "feasible":
        st.info("ℹ️ Optimizer found a feasible (near-optimal) solution within its time budget.")
    else:
        st.warning(
            "⚠️ The solver itself failed to run and the engine fell back to a greedy assignment."
        )

    st.markdown("##### ⚡ Optimization Statistics")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Solve Time", f"{stats.get('solve_time_ms', 0):.0f} ms")
    c2.metric("Flights Seated", f"{stats.get('num_seated', 0)}/{stats.get('num_flights', 0)}")
    c3.metric("Unassigned", f"{num_unassigned}")
    c4.metric("Total Walking Distance", f"{stats.get('total_walking_distance', 0):,.0f}")

    st.markdown("##### 📊 Naive vs Optimized")
    fig = MetricsVisualizer.create_optimization_comparison(naive_metrics, metrics)
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})

    if comparison:
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "Walking Distance Improvement",
                f"{comparison.get('distance_improvement_percent', 0):.1f}%",
            )
            st.metric("Naive Total Distance", f"{comparison.get('naive_total_distance', 0):,.0f}")
        with col2:
            st.metric("Optimized Total Distance", f"{comparison.get('optimized_total_distance', 0):,.0f}")
            st.metric(
                "Unique Gates Used",
                f"{comparison.get('optimized_unique_gates', 0)} (naive: {comparison.get('naive_unique_gates', 0)})",
            )

    st.markdown("##### 🧮 Optimized Metrics")
    m1, m2, m3 = st.columns(3)
    m1.metric("Avg Walking Distance", f"{metrics.get('average_walking_distance', 0):,.1f}")
    m2.metric("Avg Gate Utilization", f"{metrics.get('average_gate_utilization', 0):.1f}%")
    m3.metric("Total Conflicts", f"{metrics.get('total_conflicts', 0)}")
