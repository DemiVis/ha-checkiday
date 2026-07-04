"""Diagnostics support for the Checkiday National Day integration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .coordinator import CheckidayConfigEntry

# Never include the API key in diagnostics exports.
TO_REDACT = {"api_key"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: CheckidayConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    data = coordinator.data

    return {
        "entry_data": async_redact_data(dict(entry.data), TO_REDACT),
        "entry_options": dict(entry.options),
        "coordinator_data": ({"today": asdict(data.today)} if data else None),
    }
