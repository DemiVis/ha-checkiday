"""Constants for the Checkiday National Day integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "checkiday"

PLATFORMS: list[Platform] = [Platform.SENSOR]

# -- Checkiday / APILayer API ------------------------------------------------

API_BASE_URL = "https://api.apilayer.com/checkiday/"
API_TIMEOUT = 10  # seconds

# Defensive cap on API response size. A normal day's payload is a few kB
# even on event-heavy dates, we have plenty of headroom; anything larger
# indicates a broken (or compromised) upstream and is rejected outright.
MAX_RESPONSE_BYTES = 48 * 1024

# If a scheduled daily refresh fails, retry this often, at most this many
# times, before giving up until the next scheduled refresh (and raising a
# Repairs warning). Worst case this costs 3 extra API requests on a bad day.
RETRY_DELAY = timedelta(minutes=30)
MAX_RETRIES = 3

# The Checkiday API always calculates "today" in this fixed timezone. Per
# APILayer's own API reference (marketplace.apilayer.com/checkiday-api),
# the `date` and `timezone` request parameters are gated behind Pro and
# Enterprise plans respectively, so the Free plan this integration is built
# around can only ever ask for the bare, param-less "today" - which the API
# resolves using this timezone, not the caller's.
API_TIMEZONE = "America/Chicago"

# The Checkiday free tier (via APILayer) allows this many requests/month.
# This integration makes 1 request/day, i.e. roughly 30 requests/month.
FREE_TIER_MONTHLY_LIMIT = 100

# -- Config entry data / options keys ----------------------------------------

CONF_UPDATE_TIME = "update_time"

# Static fallback only - used if a per-timezone default can't be computed
# (see config_flow.async_compute_default_update_time). Prefer that smart
# default wherever possible; this exists purely as a last resort.
DEFAULT_UPDATE_TIME = "00:00:00"

# -- Misc ---------------------------------------------------------------------

MANUFACTURER = "Checkiday (via APILayer) — unofficial integration"

ATTRIBUTION = (
    "Data provided by Checkiday (checkiday.com) via the APILayer Checkiday "
    "API. This is an independent, unofficial integration, used under "
    "Checkiday's free-tier API at their grace, for personal, non-commercial "
    "use. Not affiliated with, endorsed by, or sponsored by Checkiday, "
    "Westy92 LLC, or APILayer."
)
