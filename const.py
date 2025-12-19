"""Constants for the Norman Blinds integration."""

from datetime import timedelta
import logging

from homeassistant.const import CONF_HOST, CONF_PASSWORD

DOMAIN = "norman_blinds"
LOGGER = logging.getLogger(__package__)

DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)

DEFAULT_APP_VERSION = "2.11.21"
DEFAULT_PASSWORD = "123456789"

LOGIN_ENDPOINT = "/cgi-bin/cgi/GatewayLogin"
ROOM_INFO_ENDPOINT = "/cgi-bin/cgi/getRoomInfo"
WINDOW_INFO_ENDPOINT = "/cgi-bin/cgi/getWindowInfo"
