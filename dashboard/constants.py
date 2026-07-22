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

# Major Indian airports selectable from the sidebar. Selecting one updates
# the header's airport name/code (see dashboard.components.sidebar and
# dashboard.components.header).
INDIAN_AIRPORTS = [
    {"city": "Delhi", "code": "DEL", "name": "Indira Gandhi International Airport"},
    {"city": "Mumbai", "code": "BOM", "name": "Chhatrapati Shivaji Maharaj International Airport"},
    {"city": "Bengaluru", "code": "BLR", "name": "Kempegowda International Airport"},
    {"city": "Chennai", "code": "MAA", "name": "Chennai International Airport"},
    {"city": "Kolkata", "code": "CCU", "name": "Netaji Subhas Chandra Bose International Airport"},
    {"city": "Hyderabad", "code": "HYD", "name": "Rajiv Gandhi International Airport"},
    {"city": "Ahmedabad", "code": "AMD", "name": "Sardar Vallabhbhai Patel International Airport"},
    {"city": "Kochi", "code": "COK", "name": "Cochin International Airport"},
    {"city": "Goa", "code": "GOI", "name": "Goa International Airport (Dabolim)"},
    {"city": "Pune", "code": "PNQ", "name": "Pune Airport"},
    {"city": "Jaipur", "code": "JAI", "name": "Jaipur International Airport"},
    {"city": "Lucknow", "code": "LKO", "name": "Chaudhary Charan Singh International Airport"},
    {"city": "Guwahati", "code": "GAU", "name": "Lokpriya Gopinath Bordoloi International Airport"},
    {"city": "Thiruvananthapuram", "code": "TRV", "name": "Trivandrum International Airport"},
    {"city": "Nagpur", "code": "NAG", "name": "Dr. Babasaheb Ambedkar International Airport"},
    {"city": "Chandigarh", "code": "IXC", "name": "Chandigarh Airport"},
    {"city": "Bhubaneswar", "code": "BBI", "name": "Biju Patnaik International Airport"},
    {"city": "Indore", "code": "IDR", "name": "Devi Ahilya Bai Holkar Airport"},
    {"city": "Amritsar", "code": "ATQ", "name": "Sri Guru Ram Dass Jee International Airport"},
    {"city": "Varanasi", "code": "VNS", "name": "Lal Bahadur Shastri International Airport"},
]

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
