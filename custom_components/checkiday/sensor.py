"""Sensor platform for the Checkiday National Day integration."""

from __future__ import annotations

from dataclasses import asdict
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import CheckidayEventsResult
from .const import ATTRIBUTION, DATA_COORDINATOR, DOMAIN, MANUFACTURER
from .coordinator import CheckidayData, CheckidayUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Checkiday sensors from a config entry."""
    coordinator: CheckidayUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]

    async_add_entities(
        [
            CheckidayDaySensor(coordinator, entry, day="today"),
            CheckidayDaySensor(coordinator, entry, day="tomorrow"),
            CheckidayRateLimitSensor(coordinator, entry),
        ]
    )


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    """Shared device info so all of this entry's entities group together."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Checkiday National Day",
        manufacturer=MANUFACTURER,
        model="Checkiday API (via APILayer)",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url="https://apilayer.com/marketplace/checkiday-api",
    )


class CheckidayDaySensor(CoordinatorEntity[CheckidayUpdateCoordinator], SensorEntity):
    """Exposes the National Day(s) for either 'today' or 'tomorrow'.

    The sensor's state is the name of the first/primary event for that day.
    Because most dates have multiple observances, the full list is exposed
    via the `events` attribute (each with `id`, `name`, `url`) so dashboards,
    templates, or ESPHome can iterate through all of them.
    """

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    _attr_icon = "mdi:calendar-star"

    def __init__(
        self, coordinator: CheckidayUpdateCoordinator, entry: ConfigEntry, day: str
    ) -> None:
        """Initialize the sensor for the given day ("today" or "tomorrow")."""
        super().__init__(coordinator)
        self._day = day
        self._attr_unique_id = f"{entry.entry_id}_{day}"
        self._attr_translation_key = f"{day}_national_day"
        self._attr_device_info = _device_info(entry)

    @property
    def _result(self) -> CheckidayEventsResult | None:
        data: CheckidayData | None = self.coordinator.data
        if data is None:
            return None
        return data.today if self._day == "today" else data.tomorrow

    @property
    def available(self) -> bool:
        """Unavailable if we have no data yet, or "tomorrow" is disabled."""
        return super().available and self._result is not None

    @property
    def native_value(self) -> str | None:
        """Return the first event's name as the primary state."""
        result = self._result
        if not result or not result.events:
            return None
        return result.events[0].name

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the full list of events plus supporting metadata."""
        result = self._result
        if not result:
            return {}
        events = [asdict(e) for e in result.events]
        return {
            "date": result.date,
            "timezone": result.timezone,
            "event_count": len(events),
            "events": events,
            "all_names": ", ".join(e["name"] for e in events),
            "multiday_starting": [asdict(e) for e in result.multiday_starting],
            "multiday_ongoing": [asdict(e) for e in result.multiday_ongoing],
        }


class CheckidayRateLimitSensor(CoordinatorEntity[CheckidayUpdateCoordinator], SensorEntity):
    """Diagnostic sensor showing the remaining monthly API request quota."""

    _attr_has_entity_name = True
    _attr_translation_key = "api_requests_remaining"
    _attr_icon = "mdi:api"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = "requests"

    def __init__(self, coordinator: CheckidayUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the diagnostic sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_api_requests_remaining"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> int | None:
        """Return the remaining monthly request count, if known."""
        data: CheckidayData | None = self.coordinator.data
        if data is None or data.today is None:
            return None
        return data.today.rate_limit_remaining

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the monthly limit and a usage note."""
        data: CheckidayData | None = self.coordinator.data
        if data is None or data.today is None:
            return {}
        return {
            "monthly_limit": data.today.rate_limit_limit,
            "note": (
                "This integration uses up to 2 requests/day (today + "
                "tomorrow), roughly 60% of the free tier's 100/month "
                "allowance. Disable 'Also fetch tomorrow's National Day(s)' "
                "in the integration's options to roughly halve usage."
            ),
        }
