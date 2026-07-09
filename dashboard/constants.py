"""
Dashboard-wide constants.

Centralizes application metadata, UI labels, and scenario definitions so
every dashboard module references a single source of truth.
"""

APP_NAME = "GateOptimizer Sim | Airport Operations Control Center"
APP_ICON = "🛫"
ORG_NAME = "Airport Authority of India (AAI)"
AIRPORT_CODE = "DEL"
AIRPORT_NAME = "Indira Gandhi International Airport"

# Operational scenarios offered in the sidebar. These map to behaviors
# implemented in dashboard.handlers.actions.handle_generation.
SCENARIOS = [
    "Normal Operations",
    "Peak Hour Traffic",
    "Gate Closure",
    "Emergency Aircraft",
    "VIP Flight",
]

WEATHER_ICONS = {
    "Clear": "☀️",
    "Rain": "🌧️",
    "Fog": "🌫️",
    "Thunderstorm": "⛈️",
    "Snow": "❄️",
}

SEVERITY_ORDER = ["critical", "high", "medium", "low"]

SEVERITY_COLORS = {
    "critical": "#e53e3e",
    "high": "#ed8936",
    "medium": "#ecc94b",
    "low": "#48bb78",
}

STATUS_COLORS = {
    "scheduled": "#a0aec0",
    "arrived": "#63b3ed",
    "departed": "#718096",
    "priority": "#e53e3e",
    "vip": "#d69e2e",
    "unassigned": "#e53e3e",
}
