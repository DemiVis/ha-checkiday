"""Diagnostics support for the Checkiday National Day integration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DATA_COORDINATOR, DOMAIN

# Never include the API key in diagnostics exports.
TO_REDACT = {"api_key"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    data = coordinator.data

    return {
        "entry_data": async_redact_data(dict(entry.data), TO_REDACT),
        "entry_options": dict(entry.options),
        "coordinator_data": (
            {
                "today": asdict(data.today) if data.today else None,
                "tomorrow": asdict(data.tomorrow) if data.tomorrow else None,
            }
            if data
            else None
        ),
    }
