"""Data update coordinator for the Checkiday National Day integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_type, timedelta
import logging

import homeassistant.util.dt as dt_util
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    CheckidayApiClient,
    CheckidayApiError,
    CheckidayAuthError,
    CheckidayEventsResult,
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class CheckidayData:
    """The data fetched on each refresh cycle."""

    today: CheckidayEventsResult
    tomorrow: CheckidayEventsResult | None


def _format_date(value: date_type) -> str:
    """Format a date the way the Checkiday API expects it (M/D/YYYY)."""
    return f"{value.month}/{value.day}/{value.year}"


class CheckidayUpdateCoordinator(DataUpdateCoordinator[CheckidayData]):
    """Coordinator that refreshes once per day at a configured local time.

    Home Assistant's usual fixed-interval polling doesn't fit this
    integration well: the Checkiday free tier only allows 100 requests per
    month, and the underlying data (which "National Day(s)" it is) only
    changes once per day, at local midnight. Refreshes are instead
    triggered externally by `async_track_time_change` (see `__init__.py`),
    so `update_interval` is intentionally left unset here.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: CheckidayApiClient,
        include_tomorrow: bool,
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
        self.include_tomorrow = include_tomorrow

    async def _async_update_data(self) -> CheckidayData:
        """Fetch today's (and optionally tomorrow's) events."""
        tz_name = self.hass.config.time_zone
        tz = dt_util.get_time_zone(tz_name) if tz_name else None
        now_local = dt_util.now(tz) if tz else dt_util.now()
        today_date = now_local.date()
        tomorrow_date = today_date + timedelta(days=1)

        try:
            today = await self.client.async_get_events(
                date=_format_date(today_date), timezone=tz_name
            )
        except CheckidayAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except CheckidayApiError as err:
            raise UpdateFailed(f"Error fetching today's Checkiday events: {err}") from err

        tomorrow: CheckidayEventsResult | None = None
        if self.include_tomorrow:
            try:
                tomorrow = await self.client.async_get_events(
                    date=_format_date(tomorrow_date), timezone=tz_name
                )
            except CheckidayAuthError as err:
                # The key stopped working between the two calls; treat this
                # the same as the "today" auth failure.
                raise ConfigEntryAuthFailed(str(err)) from err
            except CheckidayApiError as err:
                # Don't fail the whole update if only the "tomorrow" call
                # fails (e.g. the monthly quota was just exhausted) — keep
                # today's data usable.
                _LOGGER.warning("Could not fetch tomorrow's Checkiday events: %s", err)

        return CheckidayData(today=today, tomorrow=tomorrow)
