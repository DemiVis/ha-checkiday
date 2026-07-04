"""The Checkiday National Day integration.

Fetches today's "National Day(s)" from the Checkiday API
(https://apilayer.com/marketplace/checkiday-api) once per day, at a
user-configurable local time, and exposes them as sensors. The Free API
plan only supports fetching "today" (see api.py's module docstring).

If the daily fetch fails, it is retried every RETRY_DELAY up to MAX_RETRIES
times; if all retries fail, a Repairs warning is raised so the user knows
the sensors will stay unavailable until the next successful refresh.

Unofficial, community integration — not affiliated with Checkiday, Westy92
LLC, or APILayer. See README.md for details.
"""

from __future__ import annotations

import logging

from homeassistant.const import CONF_API_KEY
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_call_later, async_track_time_change

from .api import CheckidayApiClient
from .const import (
    CONF_UPDATE_TIME,
    DEFAULT_UPDATE_TIME,
    DOMAIN,
    MAX_RETRIES,
    PLATFORMS,
    RETRY_DELAY,
)
from .coordinator import CheckidayConfigEntry, CheckidayUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: CheckidayConfigEntry) -> bool:
    """Set up Checkiday National Day from a config entry."""
    session = async_get_clientsession(hass)
    client = CheckidayApiClient(session, entry.data[CONF_API_KEY])

    coordinator = CheckidayUpdateCoordinator(
        hass=hass,
        config_entry=entry,
        client=client,
    )

    # Raises ConfigEntryNotReady / ConfigEntryAuthFailed as appropriate,
    # which Home Assistant handles for us (retry later, or start reauth).
    await coordinator.async_config_entry_first_refresh()

    # Setup just fetched successfully, so clear any stale-data warning left
    # over from before a reload/restart.
    issue_id = f"stale_data_{entry.entry_id}"
    ir.async_delete_issue(hass, DOMAIN, issue_id)

    update_time = entry.options.get(CONF_UPDATE_TIME, DEFAULT_UPDATE_TIME)
    hour, minute, second = _parse_time(update_time)

    # Retry state, shared by the closures below. Kept per-entry (closure
    # scope) rather than on the coordinator, since it belongs to the
    # scheduling layer, not the data-fetching layer.
    retry_count = 0
    retry_unsub: CALLBACK_TYPE | None = None

    async def _async_attempt_refresh() -> None:
        """Refresh now; on failure, retry every RETRY_DELAY up to MAX_RETRIES.

        After the final failed retry, raise a Repairs warning telling the
        user the sensors will stay unavailable until the next successful
        refresh. The warning is removed on the next success.
        """
        nonlocal retry_count, retry_unsub
        retry_unsub = None

        # async_refresh (not async_request_refresh): we need the result
        # immediately to decide whether to schedule a retry.
        await coordinator.async_refresh()

        if coordinator.last_update_success:
            retry_count = 0
            ir.async_delete_issue(hass, DOMAIN, issue_id)
            return

        if retry_count < MAX_RETRIES:
            retry_count += 1
            _LOGGER.warning(
                "Checkiday refresh failed; retrying in %s (attempt %d of %d)",
                RETRY_DELAY,
                retry_count,
                MAX_RETRIES,
            )
            retry_unsub = async_call_later(hass, RETRY_DELAY, _async_retry)
            return

        retry_count = 0
        _LOGGER.error(
            "Checkiday refresh failed after %d retries; giving up until the "
            "next scheduled update at %s",
            MAX_RETRIES,
            update_time,
        )
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="stale_data",
            translation_placeholders={
                "retries": str(MAX_RETRIES),
                "update_time": update_time,
            },
        )

    async def _async_retry(_now) -> None:
        """async_call_later callback: run one retry attempt."""
        await _async_attempt_refresh()

    async def _scheduled_refresh(_now) -> None:
        """Daily refresh at the configured local time."""
        nonlocal retry_count
        _LOGGER.debug("Running scheduled Checkiday refresh (%s local time)", update_time)
        retry_count = 0
        await _async_attempt_refresh()

    unsub_schedule = async_track_time_change(
        hass, _scheduled_refresh, hour=hour, minute=minute, second=second
    )

    @callback
    def _cancel_pending_retry() -> None:
        if retry_unsub is not None:
            retry_unsub()

    entry.runtime_data = coordinator

    entry.async_on_unload(unsub_schedule)
    entry.async_on_unload(_cancel_pending_retry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CheckidayConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def _parse_time(value: str) -> tuple[int, int, int]:
    """Parse an "HH:MM[:SS]" string into (hour, minute, second).

    Falls back to midnight if the stored option is malformed or out of
    range, rather than failing the whole entry setup.
    """
    try:
        parts = [int(part) for part in value.split(":")]
        while len(parts) < 3:
            parts.append(0)
        hour, minute, second = parts[0], parts[1], parts[2]
        if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
            raise ValueError(f"time out of range: {value!r}")
    except (ValueError, IndexError, AttributeError):
        _LOGGER.warning(
            "Invalid update_time option %r; falling back to %s", value, DEFAULT_UPDATE_TIME
        )
        return (0, 0, 0)
    return hour, minute, second
