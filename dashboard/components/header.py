"""
Top banner / mission-control header for the dashboard.
"""

from datetime import datetime
import streamlit as st

from dashboard.constants import AIRPORT_NAME, AIRPORT_CODE, ORG_NAME
from utils.config import config


def render_header():
    """Render the airport operations control-center header banner."""
    flights = st.session_state.get("flights", [])
    gates = st.session_state.get("gates", [])
    conflicts = st.session_state.get("conflicts", [])
    data_generated = st.session_state.get("data_generated", False)

    if data_generated:
        status_color = "#e53e3e" if conflicts else "#48bb78"
        status_text = f"{len(conflicts)} ACTIVE CONFLICTS" if conflicts else "ALL SYSTEMS NOMINAL"
    else:
        status_color = "#a0aec0"
        status_text = "AWAITING FLIGHT DATA"

    now = datetime.now().strftime("%A, %d %B %Y  •  %H:%M:%S")

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(120deg, #10192b 0%, #16233d 55%, #1a2c4d 100%);
            border: 1px solid #2d3748;
            border-radius: 14px;
            padding: 22px 28px;
            margin-bottom: 18px;
            box-shadow: 0 6px 24px rgba(0,0,0,0.35);
        ">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:14px;">
                <div>
                    <div style="display:flex; align-items:center; gap:12px;">
                        <span style="font-size:2rem;">🛫</span>
                        <div>
                            <div style="font-size:1.5rem; font-weight:800; color:#e2f2ff; letter-spacing:0.02em;">
                                GateOptimizer Sim
                            </div>
                            <div style="font-size:0.85rem; color:#8fa5c0;">
                                AI-Powered Gate Allocation Decision Support &nbsp;•&nbsp; {ORG_NAME}
                            </div>
                        </div>
                    </div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:0.95rem; color:#e2e8f0; font-weight:600;">
                        {AIRPORT_NAME} ({AIRPORT_CODE})
                    </div>
                    <div style="font-size:0.8rem; color:#8fa5c0;">{now}</div>
                </div>
            </div>
            <div style="display:flex; gap:24px; margin-top:16px; flex-wrap:wrap;">
                <div style="
                    background-color:{status_color}1a; border:1px solid {status_color};
                    color:{status_color}; padding:6px 14px; border-radius:999px;
                    font-size:0.8rem; font-weight:700; letter-spacing:0.04em;">
                    ● {status_text}
                </div>
                <div style="color:#a0aec0; font-size:0.85rem; padding-top:4px;">
                    Flights: <b style="color:#e2e8f0;">{len(flights)}</b>
                </div>
                <div style="color:#a0aec0; font-size:0.85rem; padding-top:4px;">
                    Gates: <b style="color:#e2e8f0;">{len(gates) or config.airport.total_gates}</b>
                </div>
                <div style="color:#a0aec0; font-size:0.85rem; padding-top:4px;">
                    Terminals: <b style="color:#e2e8f0;">{config.airport.terminals}</b>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
