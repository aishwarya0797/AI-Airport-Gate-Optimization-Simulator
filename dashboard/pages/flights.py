"""
Flight Schedule tab: searchable/filterable flight table.
"""

import streamlit as st

from dashboard.utils import require_flights, flights_to_display_dataframe


def render_flight_table():
    """Render the full flight schedule with filtering controls."""
    if not require_flights("Generate a flight schedule to see the flight list."):
        return

    flights = st.session_state.get("flights", [])
    df = flights_to_display_dataframe(flights)

    st.markdown("##### ✈️ Flight Schedule")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        airlines = ["All"] + sorted(df["Airline"].unique().tolist())
        airline_filter = st.selectbox("Airline", airlines)
    with col2:
        sizes = ["All"] + sorted(df["Size"].unique().tolist())
        size_filter = st.selectbox("Aircraft Size", sizes)
    with col3:
        statuses = ["All"] + sorted(df["Status"].unique().tolist())
        status_filter = st.selectbox("Status", statuses)
    with col4:
        search = st.text_input("Search flight #", placeholder="e.g. AI4521")

    filtered = df.copy()
    if airline_filter != "All":
        filtered = filtered[filtered["Airline"] == airline_filter]
    if size_filter != "All":
        filtered = filtered[filtered["Size"] == size_filter]
    if status_filter != "All":
        filtered = filtered[filtered["Status"] == status_filter]
    if search:
        filtered = filtered[filtered["Flight"].str.contains(search, case=False, na=False)]

    st.caption(f"Showing {len(filtered)} of {len(df)} flights")
    st.dataframe(
        filtered,
        width='stretch',
        height=460,
        hide_index=True,
        column_config={
            "Delay (min)": st.column_config.NumberColumn(format="%d min"),
            "Passengers": st.column_config.NumberColumn(format="%d"),
        },
    )

    csv_bytes = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download filtered schedule (CSV)",
        data=csv_bytes,
        file_name="flight_schedule.csv",
        mime="text/csv",
    )
