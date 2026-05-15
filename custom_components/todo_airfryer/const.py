"""Constants for the Todo AirFryer integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "todo_airfryer"
MANUFACTURER = "Todo"
MODEL = "T-AF05W"

CONF_FRYER_IP = "fryer_ip"
CONF_PASSWORD = "password"

DEFAULT_PASSWORD = "fryme"

UPDATE_INTERVAL = timedelta(seconds=15)

PLATFORMS = ["sensor", "number", "select", "button"]
