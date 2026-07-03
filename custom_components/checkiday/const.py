"""Constants for the Checkiday National Day integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "checkiday"

PLATFORMS: list[Platform] = [Platform.SENSOR]

# -- Checkiday / APILayer API ------------------------------------------------

API_BASE_URL = "https://api.apilayer.com/checkiday/"
API_TIMEOUT = 10  # seconds

# The Checkiday free tier (via APILayer) allows this many requests/month.
# This integration makes at most 2 requests/day (today + tomorrow), i.e.
# roughly 60 requests/month if "include tomorrow" is enabled, or roughly 30
# requests/month if it's disabled.
FREE_TIER_MONTHLY_LIMIT = 100

# -- Config entry data / options keys ----------------------------------------

CONF_UPDATE_TIME = "update_time"
CONF_INCLUDE_TOMORROW = "include_tomorrow"

DEFAULT_UPDATE_TIME = "00:00:00"
DEFAULT_INCLUDE_TOMORROW = True

# -- hass.data storage keys --------------------------------------------------

DATA_COORDINATOR = "coordinator"
DATA_UNSUB_SCHEDULE = "unsub_schedule"

# -- Misc ---------------------------------------------------------------------

MANUFACTURER = "Checkiday (via APILayer) — unofficial integration"

ATTRIBUTION = (
    "Data provided by Checkiday (checkiday.com) via the APILayer Checkiday "
    "API. This is an independent, unofficial integration, used under "
    "Checkiday's free-tier API at their grace, for personal, non-commercial "
    "use. Not affiliated with, endorsed by, or sponsored by Checkiday, "
    "Westy92 LLC, or APILayer."
)
