"""
Reports tab: report summaries plus CSV / PDF export.
"""

import streamlit as st

from dashboard.utils import require_flights, chart_guide


def render_reports():
    """Render report summaries and download buttons for the prepared export bundle."""
    if not require_flights("Generate a flight schedule to build reports."):
        return

    st.markdown("##### 📤 Report Export Center")
    st.caption(
        "Click **Generate Export Bundle** in the sidebar to (re)build every report below "
        "from the current simulation state."
    )

    export_data = st.session_state.get("export_data", {})

    if not export_data:
        st.info("No reports generated yet for this session.")
        return

    chart_guide(
        "Each card below is a separate report built from whatever you've run so far — the more "
        "pipeline stages you complete (Allocate, Optimize, Train ML), the more reports appear "
        "here. Every report comes in two formats:\n"
        "- **CSV** — raw data, best for opening in Excel/Sheets or feeding into another tool\n"
        "- **PDF** — a formatted, readable document, best for sharing or printing\n\n"
        "The short text under each report's title is a plain-language summary of what's inside "
        "before you even download it."
    )

    for name, payload in export_data.items():
        report = payload["report"]
        with st.container():
            st.markdown(f"#### {name}")
            st.text(report.summary.strip())

            col1, col2 = st.columns(2)
            file_stub = name.lower().replace(" ", "_")
            with col1:
                st.download_button(
                    f"⬇️ Download CSV",
                    data=payload["csv"],
                    file_name=f"{file_stub}.csv",
                    mime="text/csv",
                    key=f"csv_{file_stub}",
                    use_container_width=True,
                )
            with col2:
                st.download_button(
                    f"⬇️ Download PDF",
                    data=payload["pdf"],
                    file_name=f"{file_stub}.pdf",
                    mime="application/pdf",
                    key=f"pdf_{file_stub}",
                    use_container_width=True,
                )
            st.markdown("---")
