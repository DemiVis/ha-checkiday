"""Sensor platform for the Checkiday National Day integration."""

from __future__ import annotations

from dataclasses import asdict
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, MANUFACTURER
from .coordinator import CheckidayConfigEntry, CheckidayData, CheckidayUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CheckidayConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Checkiday sensors from a config entry."""
    coordinator = entry.runtime_data

    async_add_entities(
        [
            CheckidayNationalDaySensor(coordinator, entry),
            CheckidayAllNamesSensor(coordinator, entry),
            CheckidayRateLimitSensor(coordinator, entry),
        ]
    )


def _device_info(entry: CheckidayConfigEntry) -> DeviceInfo:
    """Shared device info so all of this entry's entities group together."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Checkiday National Day",
        manufacturer=MANUFACTURER,
        model="Checkiday API (via APILayer)",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url="https://apilayer.com/marketplace/checkiday-api",
    )


class CheckidayNationalDaySensor(CoordinatorEntity[CheckidayUpdateCoordinator], SensorEntity):
    """Exposes today's National Day(s).

    The sensor's state is the name of the first/primary event for today.
    Because most dates have multiple observances, the full list is exposed
    via the `events` attribute (each with `id`, `name`, `url`) so dashboards,
    templates, or ESPHome can iterate through all of them.

    Only "today" is available - the Checkiday API's `date` parameter
    (needed for "tomorrow") requires a paid APILayer plan. See api.py.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "national_day"
    _attr_attribution = ATTRIBUTION

    def __init__(
        self, coordinator: CheckidayUpdateCoordinator, entry: CheckidayConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_national_day"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> str | None:
        """Return the first event's name as the primary state."""
        data: CheckidayData | None = self.coordinator.data
        if data is None or not data.today.events:
            return None
        return data.today.events[0].name

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the full list of events plus supporting metadata."""
        data: CheckidayData | None = self.coordinator.data
        if data is None:
            return {}
        result = data.today
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


class CheckidayAllNamesSensor(CoordinatorEntity[CheckidayUpdateCoordinator], SensorEntity):
    """Optional convenience sensor: all of today's event names in one string.

    Disabled by default. A long comma-joined string is a clunky sensor
    state, and the primary `national_day` sensor's `events`/`all_names`
    attributes already carry this data for templates and dashboards - this
    entity only exists for anyone who'd rather enable a ready-made entity
    than write a template sensor themselves. Not mentioned as a
    recommendation anywhere; it's just here if someone wants it.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "all_names"
    _attr_attribution = ATTRIBUTION
    _attr_entity_registry_enabled_default = False

    def __init__(
        self, coordinator: CheckidayUpdateCoordinator, entry: CheckidayConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_all_names"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> str | None:
        """Return today's event names joined into one string."""
        data: CheckidayData | None = self.coordinator.data
        if data is None or not data.today.events:
            return None
        joined = ", ".join(e.name for e in data.today.events)
        # Sensor states are capped at 255 chars; truncate defensively so a
        # heavy day doesn't get silently dropped/warned about by the
        # recorder.
        if len(joined) > 255:
            joined = joined[:252] + "..."
        return joined

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the event count, for context if the state got truncated."""
        data: CheckidayData | None = self.coordinator.data
        if data is None:
            return {}
        return {"event_count": len(data.today.events)}


class CheckidayRateLimitSensor(CoordinatorEntity[CheckidayUpdateCoordinator], SensorEntity):
    """Diagnostic sensor showing the remaining monthly API request quota."""

    _attr_has_entity_name = True
    _attr_translation_key = "api_requests_remaining"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = "requests"

    def __init__(
        self, coordinator: CheckidayUpdateCoordinator, entry: CheckidayConfigEntry
    ) -> None:
        """Initialize the diagnostic sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_api_requests_remaining"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> int | None:
        """Return the remaining monthly request count, if known."""
        data: CheckidayData | None = self.coordinator.data
        if data is None:
            return None
        return data.today.rate_limit_remaining

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the monthly limit and a usage note."""
        data: CheckidayData | None = self.coordinator.data
        if data is None:
            return {}
        return {
            "monthly_limit": data.today.rate_limit_limit,
            "note": (
                "This integration uses 1 request/day, roughly 30% of the "
                "free tier's 100/month allowance."
            ),
        }
