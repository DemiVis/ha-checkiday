"""Config flow for the Checkiday National Day integration."""

from __future__ import annotations

from datetime import timedelta
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
import homeassistant.util.dt as dt_util
import voluptuous as vol

from .api import (
    CheckidayApiClient,
    CheckidayApiError,
    CheckidayAuthError,
    CheckidayRateLimitError,
)
from .const import API_TIMEZONE, CONF_UPDATE_TIME, DEFAULT_UPDATE_TIME, DOMAIN

_LOGGER = logging.getLogger(__name__)

_API_KEY_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
    }
)

# hassfest forbids literal URLs inside strings.json/translations values, so
# the link text lives here and is injected via description_placeholders at
# runtime instead (strings.json references it as `{pricing_link}`).
_PRICING_URL = "https://apilayer.com/marketplace/checkiday-api#pricing"
_PRICING_LINK_MARKDOWN = f"[apilayer.com/marketplace/checkiday-api#pricing]({_PRICING_URL})"


async def _async_test_api_key(hass: HomeAssistant, api_key: str) -> None:
    """Validate an API key with one real request. Raises on any failure."""
    session = async_get_clientsession(hass)
    client = CheckidayApiClient(session, api_key)
    await client.async_get_today()


def _key_unique_id(api_key: str) -> str:
    """Derive a stable, non-reversible unique id from the API key."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def _compute_default_update_time(hass: HomeAssistant) -> str:
    """Suggest an update time that runs after the API's day has rolled over.

    The Checkiday API always resolves "today" using its own fixed timezone
    (America/Chicago) - the Free plan can't override this per-request (see
    api.py's module docstring). To line up with the user's *local* calendar
    day as often as possible, default to fetching at the local clock time
    that corresponds to America/Chicago's midnight, rather than always
    defaulting to the user's own midnight.

    For most US timezones this is a 0-2 hour offset from local midnight
    (e.g. Pacific/Mountain: 00:00, Eastern: ~01:00). For timezones far from
    Central Time - especially outside the Americas - this can suggest a
    late-day update time, since there may be no local time at which both
    calendars agree on "today". See the README's timezone limitations
    section. Users can always override this in the integration's options.
    """
    hass_tz_name = hass.config.time_zone
    if not hass_tz_name:
        return DEFAULT_UPDATE_TIME

    local_tz = dt_util.get_time_zone(hass_tz_name)
    api_tz = dt_util.get_time_zone(API_TIMEZONE)
    if local_tz is None or api_tz is None:
        return DEFAULT_UPDATE_TIME

    now = dt_util.utcnow()
    local_offset = local_tz.utcoffset(now)
    api_offset = api_tz.utcoffset(now)
    if local_offset is None or api_offset is None:
        return DEFAULT_UPDATE_TIME

    delay = local_offset - api_offset
    if delay < timedelta(0):
        delay = timedelta(0)

    total_minutes = int(delay.total_seconds() // 60)
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02d}:{minutes:02d}:00"


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
                        CONF_UPDATE_TIME: _compute_default_update_time(self.hass),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_API_KEY_SCHEMA,
            errors=errors,
            description_placeholders={"pricing_link": _PRICING_LINK_MARKDOWN, **placeholders},
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
            description_placeholders={"pricing_link": _PRICING_LINK_MARKDOWN, **placeholders},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> CheckidayOptionsFlowHandler:
        """Create the options flow."""
        return CheckidayOptionsFlowHandler()


class CheckidayOptionsFlowHandler(OptionsFlow):
    """Handle Checkiday options: the daily update time."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options
        default_update_time = current.get(CONF_UPDATE_TIME) or _compute_default_update_time(
            self.hass
        )
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_UPDATE_TIME, default=default_update_time
                ): selector.TimeSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
