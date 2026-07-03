"""Minimal async client for the Checkiday API (served via APILayer).

Reference: https://marketplace.apilayer.com/checkiday-api/tabs/api_docs

This client intentionally implements only the free-tier-safe shape of the
`events` endpoint:

    GET https://api.apilayer.com/checkiday/events?adult=false
    Header: apikey: <your key>

Per APILayer's own API reference, the `date` and `timezone` query parameters
on `/events` are gated behind Pro and Enterprise plans respectively (and the
`/event` and `/search` endpoints are Pro & Enterprise only in their
entirety). This integration is built around the Free plan, so it never
sends `date` or `timezone` - the API always resolves "today" using its own
fixed default timezone (America/Chicago; see const.API_TIMEZONE).

The API returns the caller's remaining monthly quota in the
`X-RateLimit-Remaining-Month` / `X-RateLimit-Limit-Month` response headers.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import json
import logging
from typing import Any

import aiohttp

from .const import API_BASE_URL, API_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class CheckidayApiError(Exception):
    """Base error for any problem talking to the Checkiday API."""


class CheckidayAuthError(CheckidayApiError):
    """The API key was rejected (invalid, revoked, or no active subscription)."""


class CheckidayRateLimitError(CheckidayApiError):
    """The request was refused due to a quota or rate limit."""


class CheckidayConnectionError(CheckidayApiError):
    """The API could not be reached at all (network/timeout)."""


@dataclass
class CheckidayEvent:
    """A single Checkiday event ("National Day")."""

    id: str
    name: str
    url: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CheckidayEvent:
        """Build a CheckidayEvent from the API's JSON representation."""
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            url=str(data.get("url", "")),
        )


@dataclass
class CheckidayEventsResult:
    """The result of a single `events` API call."""

    date: str
    timezone: str
    events: list[CheckidayEvent] = field(default_factory=list)
    multiday_starting: list[CheckidayEvent] = field(default_factory=list)
    multiday_ongoing: list[CheckidayEvent] = field(default_factory=list)
    rate_limit_remaining: int | None = None
    rate_limit_limit: int | None = None


class CheckidayApiClient:
    """Thin async wrapper around the Checkiday `events` endpoint."""

    def __init__(self, session: aiohttp.ClientSession, api_key: str) -> None:
        """Initialize the client with a shared aiohttp session and API key."""
        self._session = session
        self._api_key = api_key

    async def async_get_today(self, adult: bool = False) -> CheckidayEventsResult:
        """Fetch today's events, as resolved by the API's own default timezone.

        Deliberately takes no `date` or `timezone` arguments - both require a
        paid APILayer plan (see module docstring). This is the only request
        shape guaranteed to work on the Free plan.
        """
        params: dict[str, str] = {"adult": "true" if adult else "false"}
        return await self._async_request(params)

    async def _async_request(self, params: dict[str, str]) -> CheckidayEventsResult:
        url = f"{API_BASE_URL}events"
        headers = {"apikey": self._api_key}

        try:
            async with asyncio.timeout(API_TIMEOUT):
                response = await self._session.get(url, params=params, headers=headers)
                text = await response.text()
        except TimeoutError as err:
            raise CheckidayConnectionError("Timed out contacting the Checkiday API") from err
        except aiohttp.ClientError as err:
            raise CheckidayConnectionError(f"Error contacting the Checkiday API: {err}") from err

        try:
            payload: dict[str, Any] = json.loads(text) if text else {}
        except ValueError as err:
            raise CheckidayApiError(
                f"Received an unreadable response (HTTP {response.status}): {text[:500]}"
            ) from err

        if response.status in (401, 403):
            message = _extract_error_message(payload, text)
            raise CheckidayAuthError(f"HTTP {response.status}: {message}")
        if response.status == 429:
            message = _extract_error_message(payload, text)
            raise CheckidayRateLimitError(
                f"HTTP {response.status} (monthly quota likely exhausted): {message}"
            )
        if response.status >= 400:
            message = _extract_error_message(payload, text)
            raise CheckidayApiError(f"HTTP {response.status}: {message}")

        remaining = _parse_int(response.headers.get("X-RateLimit-Remaining-Month"))
        limit = _parse_int(response.headers.get("X-RateLimit-Limit-Month"))

        return CheckidayEventsResult(
            date=str(payload.get("date", "")),
            timezone=str(payload.get("timezone", "")),
            events=[CheckidayEvent.from_dict(e) for e in payload.get("events", [])],
            multiday_starting=[
                CheckidayEvent.from_dict(e) for e in payload.get("multiday_starting", [])
            ],
            multiday_ongoing=[
                CheckidayEvent.from_dict(e) for e in payload.get("multiday_ongoing", [])
            ],
            rate_limit_remaining=remaining,
            rate_limit_limit=limit,
        )


def _extract_error_message(payload: dict[str, Any], raw_text: str) -> str:
    """Pull the most useful human-readable error out of an API response."""
    for key in ("message", "error", "info"):
        value = payload.get(key)
        if value:
            return str(value)
    return raw_text[:500] if raw_text else "(empty response body)"


def _parse_int(value: str | None) -> int | None:
    """Best-effort int parsing that returns None instead of raising."""
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None
