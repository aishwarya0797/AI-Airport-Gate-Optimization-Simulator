"""
Shared dashboard helper utilities.

Small, dependency-light helpers used across multiple page/component
modules: dataframe builders, badge/HTML snippets, and safe-guards so
pages degrade gracefully before data has been generated.
"""

from typing import Dict, List, Optional
import pandas as pd
import streamlit as st

from dashboard.constants import SEVERITY_COLORS, STATUS_COLORS


def has_flights() -> bool:
    """Whether flights have been generated in this session."""
    return bool(st.session_state.get("flights"))


def has_allocation() -> bool:
    """Whether a rule-based allocation has been run."""
    return bool(st.session_state.get("allocated"))


def has_optimization() -> bool:
    """Whether the optimizer has produced assignments."""
    return bool(st.session_state.get("optimized"))


def has_ml() -> bool:
    """Whether ML models have been trained."""
    return bool(st.session_state.get("ml_trained"))


def require_flights(message: str = "Generate a flight schedule from the sidebar to get started.") -> bool:
    """Render an info notice and return False if no flights exist yet."""
    if not has_flights():
        st.info(f"✈️ {message}")
        return False
    return True


def severity_badge(severity: str) -> str:
    """Return an HTML pill badge for a conflict severity level."""
    color = SEVERITY_COLORS.get(severity, "#a0aec0")
    return (
        f'<span style="background-color:{color}22;color:{color};'
        f'border:1px solid {color};padding:2px 10px;border-radius:999px;'
        f'font-size:0.75rem;font-weight:600;letter-spacing:0.03em;">'
        f'{severity.upper()}</span>'
    )


def status_badge(status: str) -> str:
    """Return an HTML pill badge for a flight status."""
    color = STATUS_COLORS.get(status, "#a0aec0")
    label = status.replace("_", " ").upper()
    return (
        f'<span style="background-color:{color}22;color:{color};'
        f'border:1px solid {color};padding:2px 10px;border-radius:999px;'
        f'font-size:0.75rem;font-weight:600;">{label}</span>'
    )


def flights_to_display_dataframe(flights: List) -> pd.DataFrame:
    """Build a friendly, display-ready DataFrame from Flight objects."""
    rows = []
    for f in flights:
        rows.append({
            "Flight": f.flight_number,
            "Airline": f.airline,
            "Aircraft": f.aircraft_type,
            "Size": f.aircraft_size.title(),
            "Origin": f.origin,
            "Destination": f.destination,
            "Arrival": f.arrival_time.strftime("%H:%M"),
            "Departure": (f.arrival_time + pd.Timedelta(minutes=f.turnaround_time + f.delay)).strftime("%H:%M"),
            "Passengers": f.passenger_count,
            "Turnaround (min)": f.turnaround_time,
            "Delay (min)": f.delay,
            "Gate": f.assigned_gate or "—",
            "Status": f.status,
        })
    return pd.DataFrame(rows)


def gate_status_map(gates: List, flights: List) -> Dict[str, str]:
    """Compute a simple available/occupied status per gate for the current schedule."""
    occupied_gates = {f.assigned_gate for f in flights if getattr(f, "assigned_gate", "")}
    statuses = {}
    for g in gates:
        if not getattr(g, "is_available", True):
            statuses[g.gate_id] = "reserved"
        elif g.gate_id in occupied_gates:
            statuses[g.gate_id] = "occupied"
        else:
            statuses[g.gate_id] = "available"
    return statuses


def metric_card(label: str, value: str, delta: Optional[str] = None, help_text: Optional[str] = None):
    """Thin wrapper around st.metric kept for consistent call sites."""
    st.metric(label, value, delta=delta, help=help_text)


def safe_mean(values: List[float]) -> float:
    """Mean of a list, defensively returning 0 for empty input."""
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def chart_guide(text: str, label: str = "❓ What am I looking at?"):
    """
    Render a small collapsible, plain-language explanation directly under a
    chart or visual. Used everywhere in the app so a first-time visitor can
    always find out what a given chart/table/map means without needing
    someone else to explain it, while staying out of the way (collapsed by
    default) for returning users who already know the app.
    """
    with st.expander(label, expanded=False):
        st.markdown(text)


def render_html(html: str):
    """
    Render a multi-line HTML string via st.markdown, safely.

    Streamlit's markdown renderer follows standard Markdown rules: any line
    indented 4+ spaces is treated as a preformatted code block, not parsed
    as HTML. Writing HTML with normal Python indentation (which is exactly
    what every custom-styled component in this app naturally does) silently
    breaks it -- it renders as literal visible text instead of styled
    markup, even with unsafe_allow_html=True. This strips leading
    whitespace from every line first, so indentation in the *source code*
    never affects what actually renders in the browser.
    """
    dedented = "\n".join(line.strip() for line in html.strip("\n").splitlines())
    st.markdown(dedented, unsafe_allow_html=True)
