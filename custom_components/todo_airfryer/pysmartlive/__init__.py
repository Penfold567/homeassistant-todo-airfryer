"""SmartLive LAN client library for TODO/T-AF05W air fryer."""
from .client import AirFryerClient, AirFryerStatus
from .protocol import AES_KEY_DEFAULT, encode_frame, parse_frame

__all__ = [
    "AirFryerClient",
    "AirFryerStatus",
    "AES_KEY_DEFAULT",
    "encode_frame",
    "parse_frame",
]
