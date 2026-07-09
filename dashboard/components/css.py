"""
Global stylesheet for the Airport Operations Control Center theme.
"""

import streamlit as st


def load_css():
    """Inject the dashboard's dark "ops control center" theme."""
    st.markdown(
        """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .main, .stApp {
        background: radial-gradient(circle at 20% 0%, #10192b 0%, #0a0f1c 55%, #070b13 100%);
    }

    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #101a2e 0%, #0d1421 100%);
        border-right: 1px solid #23324a;
    }
    div[data-testid="stSidebar"] .stMarkdown, div[data-testid="stSidebar"] label {
        color: #c3d3e8;
    }

    h1, h2, h3, h4, h5, h6 {
        color: #7db8f0 !important;
        font-weight: 800 !important;
        letter-spacing: -0.01em;
    }

    /* KPI metrics */
    div[data-testid="stMetric"] {
        background: linear-gradient(160deg, #131e33 0%, #0f1826 100%);
        border: 1px solid #22314a;
        border-radius: 12px;
        padding: 14px 16px 10px 16px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.25);
    }
    div[data-testid="stMetric"] label {
        color: #8fa5c0 !important;
        font-size: 0.78rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600 !important;
    }
    div[data-testid="stMetricValue"] {
        color: #eaf3ff !important;
        font-weight: 800 !important;
        font-family: 'JetBrains Mono', monospace;
    }

    div[data-testid="stDataFrame"] {
        background-color: #0f1826;
        border: 1px solid #22314a;
        border-radius: 10px;
    }

    div[data-testid="stMarkdownContainer"] p {
        color: #d5e1f0;
    }

    /* Buttons */
    .stButton button {
        background: linear-gradient(135deg, #2b6cb0 0%, #1e4e8c 100%);
        color: white;
        border: 1px solid #2f6db8;
        border-radius: 9px;
        padding: 10px 20px;
        font-weight: 600;
        letter-spacing: 0.01em;
        transition: all 0.2s ease-in-out;
    }
    .stButton button:hover {
        background: linear-gradient(135deg, #3182ce 0%, #235a9e 100%);
        border-color: #63b3ed;
        box-shadow: 0 4px 16px rgba(66, 153, 225, 0.35);
        transform: translateY(-1px);
    }
    .stButton button:active {
        transform: translateY(0);
    }
    .stButton button[kind="primary"] {
        background: linear-gradient(135deg, #38a169 0%, #276749 100%);
        border-color: #48bb78;
    }
    .stButton button[kind="primary"]:hover {
        background: linear-gradient(135deg, #48bb78 0%, #2f855a 100%);
        box-shadow: 0 4px 16px rgba(72, 187, 120, 0.35);
    }

    div[data-baseweb="select"] > div, div[data-baseweb="input"] {
        background-color: #16233d;
        border-color: #2d3f5c;
        border-radius: 8px;
    }

    .stAlert {
        border-radius: 10px;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #0f1826;
        border-radius: 10px 10px 0 0;
        padding: 4px;
        border: 1px solid #22314a;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        color: #8fa5c0;
        border-radius: 8px;
        font-weight: 600;
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #2b6cb0 0%, #1e4e8c 100%) !important;
        color: white !important;
    }

    /* Expanders */
    div[data-testid="stExpander"] {
        background-color: #0f1826;
        border: 1px solid #22314a;
        border-radius: 10px;
    }

    /* Progress bar */
    .stProgress > div > div {
        background-color: #1c2b45;
        border-radius: 999px;
    }
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #48bb78, #38a169);
        border-radius: 999px;
    }

    /* Scrollbars */
    ::-webkit-scrollbar { width: 10px; height: 10px; }
    ::-webkit-scrollbar-track { background: #0d1421; }
    ::-webkit-scrollbar-thumb { background: #2d3f5c; border-radius: 6px; }
    ::-webkit-scrollbar-thumb:hover { background: #3d5578; }

    footer, #MainMenu { visibility: hidden; }

    /* Overall page spacing */
    .block-container {
        padding-top: 1.6rem;
        padding-bottom: 3rem;
        max-width: 1400px;
    }

    /* Sidebar section headers */
    section[data-testid="stSidebar"] h4 {
        color: #63b3ed !important;
        font-size: 0.92rem !important;
        margin-top: 4px;
        margin-bottom: 6px;
    }
    section[data-testid="stSidebar"] hr {
        border-color: #22314a;
        margin: 10px 0;
    }

    /* Dividers */
    hr {
        border-color: #22314a;
    }

    /* Sliders */
    div[data-testid="stSliderTickBarMin"], div[data-testid="stSliderTickBarMax"] {
        color: #8fa5c0;
    }
    .stSlider [role="slider"] {
        background-color: #3182ce !important;
    }

    /* Select boxes text color */
    div[data-baseweb="select"] span {
        color: #eaf3ff;
    }

    /* Info / warning / success alert accents */
    div[data-testid="stAlert"] {
        border: 1px solid #22314a;
    }
</style>
""",
        unsafe_allow_html=True,
    )
