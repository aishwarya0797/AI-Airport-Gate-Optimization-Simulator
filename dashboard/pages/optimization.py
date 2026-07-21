"""
Optimization tab: naive vs rule-based vs OR-Tools comparison.
"""

import streamlit as st
import pandas as pd

from visualization.charts import MetricsVisualizer
from dashboard.utils import require_flights, chart_guide


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
            "See the **waitlist** below for exactly which gate each one should hold for and how long, "
            "or generate fewer flights / add more gates to avoid this entirely."
        )
    elif status == "feasible":
        st.info("ℹ️ Optimizer found a feasible (near-optimal) solution within its time budget.")
    else:
        st.warning(
            "⚠️ The solver itself failed to run and the engine fell back to a greedy assignment."
        )

    chart_guide(
        "**\"Naive\"** = the simplest possible approach: just give each flight the first free, "
        "size-compatible gate it finds, in arrival order. No real thinking involved.\n\n"
        "**\"Optimized\"** = the actual OR-Tools solver, which considers every flight and every "
        "gate together and tries to minimize total passenger walking distance while seating as "
        "many flights as possible without double-booking any gate.\n\n"
        "Comparing the two shows you exactly how much smarter the optimizer's plan is than just "
        "guessing.",
        label="❓ What's the difference between Naive and Optimized?",
    )

    st.markdown("##### ⚡ Optimization Statistics")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Solve Time", f"{stats.get('solve_time_ms', 0):.0f} ms")
    c2.metric("Flights Seated", f"{stats.get('num_seated', 0)}/{stats.get('num_flights', 0)}")
    c3.metric("Unassigned", f"{num_unassigned}")
    c4.metric("Total Walking Distance", f"{stats.get('total_walking_distance', 0):,.0f}")

    chart_guide(
        "- **Solve Time**: how long the optimizer took to compute this plan\n"
        "- **Flights Seated**: how many flights actually got a gate\n"
        "- **Unassigned**: flights that couldn't be seated anywhere — genuinely too many flights "
        "for available gates at that moment, not an error\n"
        "- **Total Walking Distance**: a rough proxy for total passenger walking across all seated "
        "flights (lower is better)"
    )

    waitlist = st.session_state.get("waitlist", {})
    if num_unassigned > 0 and waitlist:
        st.markdown("##### ⏳ Waitlist — Next Available Gate")

        flights_by_id = {f.flight_id: f for f in st.session_state.get("flights", [])}
        rows = []
        for flight_id, info in waitlist.items():
            flight = flights_by_id.get(flight_id)
            if not flight:
                continue
            rows.append({
                "Flight": flight.flight_number,
                "Airline": flight.airline,
                "Size": flight.aircraft_size.title(),
                "Original Arrival": flight.arrival_time.strftime("%H:%M"),
                "Recommended Gate": info["recommended_gate"],
                "Available From": info["available_from"].strftime("%H:%M (%d %b)"),
                "Est. Wait": f"{info['wait_minutes']:.0f} min",
                "_wait_sort": info["wait_minutes"],
            })

        if rows:
            waitlist_df = pd.DataFrame(rows).sort_values("_wait_sort").drop(columns="_wait_sort")
            st.dataframe(waitlist_df, width='stretch', hide_index=True)

        chart_guide(
            "Every flight that couldn't be seated gets a real, calculated answer here — not just "
            "\"no gate available.\" For each one, this looks at every size-compatible gate's actual "
            "schedule (from the flights that *did* get seated) and finds the earliest moment that "
            "gate genuinely frees up.\n\n"
            "- **Recommended Gate**: the specific gate to hold this flight for\n"
            "- **Available From**: the real time that gate becomes free\n"
            "- **Est. Wait**: how much longer past its original arrival time this flight would need "
            "to hold (e.g. in a remote bay, or circling) before it can dock\n\n"
            "This is sorted by shortest wait first, so the easiest wins are at the top."
        )

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

    chart_guide(
        "These three numbers summarize the optimizer's final plan on its own (not compared to "
        "naive): how far passengers walk on average, how efficiently gates are being used across "
        "the day, and how many conflicts remain in this plan (ideally zero)."
    )
