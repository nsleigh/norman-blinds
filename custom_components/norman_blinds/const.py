"""Constants for the Norman Blinds integration."""

from datetime import timedelta
import logging

from homeassistant.const import CONF_HOST, CONF_PASSWORD

DOMAIN = "norman_blinds"
LOGGER = logging.getLogger(__package__)

DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)
DEFAULT_REQUEST_TIMEOUT = 10
DEFAULT_REFRESH_DELAY = 5  # seconds delay before requesting refresh after a command
LOGIN_ATTEMPTS = 3  # total login attempts on 5xx/connection/timeout errors
LOGIN_RETRY_DELAY = 5  # seconds between login attempts
MAX_TOLERATED_UPDATE_FAILURES = 2  # consecutive failed polls served from cached data
# GatewayLogin errorCodes (with HTTP 200) that mean the credentials/session were
# rejected -- a genuine auth failure. Every other nonzero login errorCode is
# treated as the hub being transiently busy (e.g. a scheduled job) and is ridden
# out with cached data, rather than enumerating transient codes (-12, -15, ...)
# which the hub keeps inventing.
AUTH_LOGIN_ERROR_CODES: frozenset[int] = frozenset({-13})

DEFAULT_APP_VERSION = "2.11.21"
DEFAULT_PASSWORD = "123456789"

LOGIN_ENDPOINT = "/cgi-bin/cgi/GatewayLogin"
ROOM_INFO_ENDPOINT = "/cgi-bin/cgi/getRoomInfo"
WINDOW_INFO_ENDPOINT = "/cgi-bin/cgi/getWindowInfo"
REMOTE_CONTROL_ENDPOINT = "/cgi-bin/cgi/RemoteControl"

REMOTE_CONTROL_MODEL = 1
# "level" commands address one of the room's five groupname slots
# (0 Left, 1 Middle, 2 Right, 3 All, 4 spare). Slot 3 moves the whole room and
# updates the hub's stored positions. Lid 9 also moved the room but left the
# stored positions stale, so HA showed the wrong state.
ROOM_REMOTE_CONTROL_LID = 3
ALLOWED_POSITIONS: tuple[int, ...] = (100, 81, 65, 50, 37, 25, 12, 0)
SOLAR_NO_READING = 65535  # 0xFFFF: the blind reports no solar reading

# Room preset commands
ROOM_PRESETS = {
    "view": "fullopen",      # open
    "privacy": "fullclose",  # closed
    "favorite": "Favorite",  # custom favorite position
}
