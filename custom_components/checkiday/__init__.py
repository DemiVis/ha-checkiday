"""The Checkiday National Day integration.

Fetches today's (and optionally tomorrow's) "National Day(s)" from the
Checkiday API (https://apilayer.com/marketplace/checkiday-api) once per day,
at a user-configurable local time, and exposes them as sensors.

Unofficial, community integration — not affiliated with Checkiday, Westy92
LLC, or APILayer. See README.md for details.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change

from .api import CheckidayApiClient
from .const import (
    CONF_INCLUDE_TOMORROW,
    CONF_UPDATE_TIME,
    DATA_COORDINATOR,
    DATA_UNSUB_SCHEDULE,
    DEFAULT_INCLUDE_TOMORROW,
    DEFAULT_UPDATE_TIME,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import CheckidayUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Checkiday National Day from a config entry."""
    session = async_get_clientsession(hass)
    client = CheckidayApiClient(session, entry.data[CONF_API_KEY])

    include_tomorrow = entry.options.get(CONF_INCLUDE_TOMORROW, DEFAULT_INCLUDE_TOMORROW)

    coordinator = CheckidayUpdateCoordinator(
        hass=hass,
        config_entry=entry,
        client=client,
        include_tomorrow=include_tomorrow,
    )

    # Raises ConfigEntryNotReady / ConfigEntryAuthFailed as appropriate,
    # which Home Assistant handles for us (retry later, or start reauth).
    await coordinator.async_config_entry_first_refresh()

    update_time = entry.options.get(CONF_UPDATE_TIME, DEFAULT_UPDATE_TIME)
    hour, minute, second = _parse_time(update_time)

    async def _scheduled_refresh(_now) -> None:
        _LOGGER.debug("Running scheduled Checkiday refresh (%s local time)", update_time)
        await coordinator.async_request_refresh()

    unsub_schedule = async_track_time_change(
        hass, _scheduled_refresh, hour=hour, minute=minute, second=second
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
        DATA_UNSUB_SCHEDULE: unsub_schedule,
    }

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    entry.async_on_unload(unsub_schedule)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when its options change.

    This is the simplest correct way to pick up a new update_time (which
    needs the daily schedule re-registered) or include_tomorrow value.
    """
    await hass.config_entries.async_reload(entry.entry_id)


def _parse_time(value: str) -> tuple[int, int, int]:
    """Parse an "HH:MM[:SS]" string into (hour, minute, second)."""
    parts = [int(part) for part in value.split(":")]
    while len(parts) < 3:
        parts.append(0)
    return parts[0], parts[1], parts[2]
