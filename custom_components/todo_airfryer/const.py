"""Constants for the Todo AirFryer integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "todo_airfryer"
MANUFACTURER = "Todo"
MODEL = "T-AF05W"

CONF_FRYER_IP = "fryer_ip"
CONF_CLIENT_IP = "client_ip"
CONF_CLIENT_PORT = "client_port"
CONF_PASSWORD = "password"
CONF_ALLOW_START = "allow_unattended_start"

DEFAULT_CLIENT_PORT = 20631
DEFAULT_PASSWORD = "fryme"

UPDATE_INTERVAL = timedelta(seconds=15)

PLATFORMS = ["sensor", "number", "select", "button"]
