"""Data update coordinator for the Checkiday National Day integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CheckidayApiClient, CheckidayApiError, CheckidayAuthError, CheckidayEventsResult
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Typed alias so platforms can annotate the entry and get a typed
# `entry.runtime_data` (the coordinator) for free.
type CheckidayConfigEntry = ConfigEntry[CheckidayUpdateCoordinator]


@dataclass
class CheckidayData:
    """The data fetched on each refresh cycle."""

    today: CheckidayEventsResult


class CheckidayUpdateCoordinator(DataUpdateCoordinator[CheckidayData]):
    """Coordinator that refreshes once per day at a configured local time.

    Home Assistant's usual fixed-interval polling doesn't fit this
    integration well: the Checkiday free tier only allows 100 requests per
    month, and the underlying data (which "National Day(s)" it is) only
    changes once per day. Refreshes are instead triggered externally by
    `async_track_time_change` (see `__init__.py`), so `update_interval` is
    intentionally left unset here.

    Only "today" is fetched: the Checkiday API's `date` parameter (needed
    for "tomorrow") requires a Pro or Enterprise APILayer plan, so it isn't
    usable on the Free plan this integration targets. See api.py's module
    docstring for details.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: CheckidayConfigEntry,
        client: CheckidayApiClient,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=None,
        )
        self.client = client

    async def _async_update_data(self) -> CheckidayData:
        """Fetch today's events."""
        try:
            today = await self.client.async_get_today()
        except CheckidayAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except CheckidayApiError as err:
            raise UpdateFailed(f"Error fetching today's Checkiday events: {err}") from err

        return CheckidayData(today=today)
