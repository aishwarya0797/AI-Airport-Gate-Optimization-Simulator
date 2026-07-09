"""
Conflict Detection & Resolution tab.
"""

import streamlit as st

from visualization.charts import ConflictVisualizer
from dashboard.constants import SEVERITY_ORDER
from dashboard.utils import require_flights, severity_badge


def render_conflict_analysis():
    """Render conflict summary charts and a detailed, filterable conflict table."""
    if not require_flights("Generate a flight schedule to run conflict detection."):
        return

    if not st.session_state.get("conflicts_detected"):
        st.info("Run **Allocate** or **Optimize** from the sidebar to detect conflicts.")
        return

    conflicts = st.session_state.get("conflicts", [])
    conflict_summary = st.session_state.get("conflict_summary", {})

    if not conflicts:
        st.success("✅ No conflicts detected in the current gate assignment plan.")
        return

    st.markdown("##### 🚨 Conflict Summary")
    cols = st.columns(4)
    for col, severity in zip(cols, SEVERITY_ORDER):
        count = conflict_summary.get(f"{severity}_count", 0)
        col.metric(severity.capitalize(), count)

    fig = ConflictVisualizer.create_conflict_summary_chart(conflict_summary)
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})

    st.markdown("##### 📋 Detailed Conflict Log")

    severity_filter = st.multiselect(
        "Filter by severity", options=SEVERITY_ORDER, default=SEVERITY_ORDER
    )

    filtered = [c for c in conflicts if c.severity in severity_filter]
    st.caption(f"Showing {len(filtered)} of {len(conflicts)} conflicts")

    for conflict in sorted(filtered, key=lambda c: SEVERITY_ORDER.index(c.severity)):
        with st.container():
            st.markdown(
                f"""
                <div style="
                    background-color:#151f33; border:1px solid #2d3748;
                    border-left:4px solid {"#e53e3e" if conflict.severity=="critical" else "#ed8936" if conflict.severity=="high" else "#ecc94b" if conflict.severity=="medium" else "#48bb78"};
                    border-radius:8px; padding:12px 16px; margin-bottom:10px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <b style="color:#e2e8f0;">{conflict.conflict_id} — {conflict.conflict_type.replace('_',' ').title()}</b>
                        {severity_badge(conflict.severity)}
                    </div>
                    <div style="color:#a0aec0; font-size:0.85rem; margin-top:6px;">
                        Gate: <b>{conflict.gate_id}</b> &nbsp;•&nbsp; Flights: {', '.join(conflict.flight_ids)}
                    </div>
                    <div style="color:#cbd5e0; font-size:0.85rem; margin-top:6px;">
                        {conflict.description}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if conflict.resolution_suggestions:
                with st.expander("💡 Suggested resolutions"):
                    for suggestion in conflict.resolution_suggestions:
                        st.markdown(f"- {suggestion}")
