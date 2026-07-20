"""
Top banner / mission-control header for the dashboard.
"""

from datetime import datetime
import streamlit as st

from dashboard.constants import AIRPORT_NAME, AIRPORT_CODE, ORG_NAME
from dashboard.utils import render_html
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

    render_html(
        f"""
        <style>
        @keyframes radar-spin {{
            from {{ transform: translate(-50%, -50%) rotate(0deg); }}
            to   {{ transform: translate(-50%, -50%) rotate(360deg); }}
        }}
        @keyframes radar-pulse {{
            0%   {{ opacity: 0.55; }}
            50%  {{ opacity: 0.15; }}
            100% {{ opacity: 0.55; }}
        }}
        .gos-header {{
            position: relative;
            overflow: hidden;
            background: linear-gradient(120deg, #0a1120 0%, #10192b 45%, #16233d 100%);
            border: 1px solid #2d3748;
            border-radius: 14px;
            padding: 22px 28px;
            margin-bottom: 18px;
            box-shadow: 0 6px 24px rgba(0,0,0,0.35);
        }}
        .gos-radar-decor {{
            position: absolute;
            top: -70px;
            right: -70px;
            width: 260px;
            height: 260px;
            pointer-events: none;
            z-index: 0;
        }}
        .gos-radar-ring {{
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            border: 1px solid rgba(99, 179, 237, 0.18);
            border-radius: 50%;
            animation: radar-pulse 3.2s ease-in-out infinite;
        }}
        .gos-radar-ring.r1 {{ width: 90px;  height: 90px;  animation-delay: 0s; }}
        .gos-radar-ring.r2 {{ width: 165px; height: 165px; animation-delay: 0.4s; }}
        .gos-radar-ring.r3 {{ width: 240px; height: 240px; animation-delay: 0.8s; }}
        .gos-radar-sweep {{
            position: absolute;
            top: 50%; left: 50%;
            width: 240px; height: 240px;
            transform: translate(-50%, -50%);
            border-radius: 50%;
            background: conic-gradient(from 0deg, rgba(99, 179, 237, 0.45), rgba(99, 179, 237, 0) 30%);
            -webkit-mask-image: radial-gradient(circle, black 60%, transparent 100%);
            mask-image: radial-gradient(circle, black 60%, transparent 100%);
            animation: radar-spin 4.5s linear infinite;
        }}
        .gos-header-content {{
            position: relative;
            z-index: 1;
        }}
        .gos-title {{
            font-size: 1.15rem;
            font-weight: 800;
            letter-spacing: 0.04em;
            color: #f0f6ff;
            font-family: 'Courier New', ui-monospace, monospace;
        }}
        .gos-subtitle {{
            font-size: 0.8rem;
            letter-spacing: 0.06em;
            color: #63b3ed;
            font-family: 'Courier New', ui-monospace, monospace;
            text-transform: uppercase;
            margin-top: 2px;
        }}
        </style>

        <div class="gos-header">
            <div class="gos-radar-decor">
                <div class="gos-radar-ring r1"></div>
                <div class="gos-radar-ring r2"></div>
                <div class="gos-radar-ring r3"></div>
                <div class="gos-radar-sweep"></div>
            </div>

            <div class="gos-header-content">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:14px;">
                    <div>
                        <div style="display:flex; align-items:center; gap:12px;">
                            <span style="font-size:2rem;">🛫</span>
                            <div>
                                <div class="gos-title">GATEOPTIMIZER SIM</div>
                                <div class="gos-subtitle">AI-Powered Gate Allocation &amp; Airport Operations Digital Twin</div>
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
                    <div style="color:#a0aec0; font-size:0.85rem; padding-top:4px;">
                        {ORG_NAME}
                    </div>
                </div>
            </div>
        </div>
        """
    )
