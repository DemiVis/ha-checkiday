"""Config flow for the Checkiday National Day integration."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from .api import (
    CheckidayApiClient,
    CheckidayApiError,
    CheckidayAuthError,
    CheckidayRateLimitError,
)
from .const import (
    CONF_INCLUDE_TOMORROW,
    CONF_UPDATE_TIME,
    DEFAULT_INCLUDE_TOMORROW,
    DEFAULT_UPDATE_TIME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

_API_KEY_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
    }
)


async def _async_test_api_key(hass: HomeAssistant, api_key: str) -> None:
    """Validate an API key with one real request. Raises on any failure."""
    session = async_get_clientsession(hass)
    client = CheckidayApiClient(session, api_key)
    # No `date` -> the API defaults to "today" for us; we just need to know
    # the key works, we don't need the actual data here.
    await client.async_get_events(timezone=hass.config.time_zone)


def _key_unique_id(api_key: str) -> str:
    """Derive a stable, non-reversible unique id from the API key."""
    return hashlib.sha256(api_key.encode()).hexdigest()


async def _async_validate_and_build_errors(
    hass: HomeAssistant, api_key: str
) -> tuple[dict[str, str], dict[str, str]]:
    """Run the live API key test and translate exceptions into flow errors.

    Returns (errors, description_placeholders). `errors` is empty on success.
    """
    errors: dict[str, str] = {}
    placeholders: dict[str, str] = {}

    try:
        await _async_test_api_key(hass, api_key)
    except CheckidayAuthError as err:
        errors["base"] = "invalid_auth"
        placeholders["error_detail"] = str(err)
    except CheckidayRateLimitError as err:
        errors["base"] = "rate_limited"
        placeholders["error_detail"] = str(err)
    except CheckidayApiError as err:
        errors["base"] = "cannot_connect"
        placeholders["error_detail"] = str(err)
    except Exception:  # noqa: BLE001 - guard the flow against any surprise
        _LOGGER.exception("Unexpected error validating Checkiday API key")
        errors["base"] = "unknown"

    return errors, placeholders


class CheckidayConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Checkiday National Day."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._reauth_entry: ConfigEntry | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial setup step: collect and test an API key."""
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            errors, placeholders = await _async_validate_and_build_errors(self.hass, api_key)

            if not errors:
                await self.async_set_unique_id(_key_unique_id(api_key))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Checkiday National Day",
                    data={CONF_API_KEY: api_key},
                    options={
                        CONF_UPDATE_TIME: DEFAULT_UPDATE_TIME,
                        CONF_INCLUDE_TOMORROW: DEFAULT_INCLUDE_TOMORROW,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_API_KEY_SCHEMA,
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle a reauth flow, triggered when the stored API key fails."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a new API key and test it before saving."""
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            errors, placeholders = await _async_validate_and_build_errors(self.hass, api_key)

            if not errors:
                assert self._reauth_entry is not None
                return self.async_update_reload_and_abort(
                    self._reauth_entry,
                    data={**self._reauth_entry.data, CONF_API_KEY: api_key},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_API_KEY_SCHEMA,
            errors=errors,
            description_placeholders=placeholders,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> CheckidayOptionsFlowHandler:
        """Create the options flow."""
        return CheckidayOptionsFlowHandler()


class CheckidayOptionsFlowHandler(OptionsFlow):
    """Handle Checkiday options: daily update time and tomorrow toggle."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_UPDATE_TIME,
                    default=current.get(CONF_UPDATE_TIME, DEFAULT_UPDATE_TIME),
                ): selector.TimeSelector(),
                vol.Required(
                    CONF_INCLUDE_TOMORROW,
                    default=current.get(CONF_INCLUDE_TOMORROW, DEFAULT_INCLUDE_TOMORROW),
                ): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
