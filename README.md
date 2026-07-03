# Checkiday National Day for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Home Assistant custom integration that surfaces today's (and, optionally,
tomorrow's) ["National Day(s)"](https://checkiday.com) — e.g. *National Pizza
Day*, *International Cat Day* — as sensors, using the
[Checkiday API](https://apilayer.com/marketplace/checkiday-api), available via
APILayer.

> **⚠️ Unofficial project.** This integration is **not affiliated with,
> endorsed by, or sponsored by Checkiday, Westy92 LLC, or APILayer.** It is an
> independent, community-built client for their public API. It is intended
> for **personal, non-commercial, daily use only**, and relies entirely on
> the free tier of their API, made available at their discretion. Please
> respect their [terms of service](https://apilayer.com/marketplace/checkiday-api)
> and don't abuse the API.

## Features

- Fetches **today's** National Day(s) from Checkiday, plus **tomorrow's** if
  you want to preview them (e.g. for a display refreshed at night).
- Most calendar dates have *multiple* observances — every event is exposed
  in a structured attribute list so a dashboard, template, or ESPHome display
  can iterate through all of them, not just the first one.
- Runs on your own schedule: fetches once per day at a **local time you
  choose** (default: midnight), instead of constant polling.
- A built-in "API requests remaining" sensor so you can keep an eye on your
  monthly quota.
- Guided setup: paste your API key and the integration tests it immediately.
  If it doesn't work, you'll see exactly why (the raw API response) instead
  of a vague error.

## Installation

### Via HACS (recommended)

1. In Home Assistant, go to **HACS → Integrations → ⋮ → Custom repositories**.
2. Add this repository's URL, category **Integration**.
   (Once accepted into the default HACS store, this step won't be necessary.)
3. Find **Checkiday National Day** in HACS and install it.
4. Restart Home Assistant.

### Manual install

1. Copy `custom_components/checkiday` from this repo into your Home
   Assistant `config/custom_components/` directory.
2. Restart Home Assistant.

## Getting a free Checkiday API key

1. Go to the [Checkiday API on APILayer](https://apilayer.com/marketplace/checkiday-api#pricing)
   and create a free APILayer account (no credit card required).
2. Subscribe to the **Free Plan** (100 requests/month, free for life).
3. Copy the API key shown in your APILayer dashboard.

## Configuration

1. In Home Assistant, go to **Settings → Devices & Services → Add
   Integration**, and search for **Checkiday National Day**.
2. Paste your API key. It's tested with one real request before the
   integration is set up — if it fails, you'll see the API's actual error
   response so you can tell what went wrong (bad key, no active
   subscription, quota exhausted, etc.).
3. After setup, click **Configure** on the integration to adjust:
   - **Daily update time** — the local time each day the integration fetches
     new data (default `00:00:00`).
   - **Also fetch tomorrow's National Day(s)** — on by default; turn this off
     to roughly halve your monthly API usage.

If your API key later stops working (revoked, quota exhausted long-term,
etc.), Home Assistant will prompt you to re-authenticate with a new key
without losing your other settings.

## Entities

| Entity | Description |
| --- | --- |
| `sensor.checkiday_today` | State = the first National Day for today. Attributes include the full `events` list (`id`, `name`, `url` for every event today), `event_count`, `all_names`, and any multi-day events starting/ongoing. |
| `sensor.checkiday_tomorrow` | Same as above, for tomorrow. Only populated if "Also fetch tomorrow's National Day(s)" is enabled. |
| `sensor.checkiday_api_requests_remaining` | Diagnostic sensor showing your remaining monthly API requests (from the API's rate-limit headers). |

### Iterating through multiple events

Most dates have several observances. Use the `events` attribute (a list of
`{id, name, url}`) in a template to iterate:

```yaml
{% for event in state_attr('sensor.checkiday_today', 'events') %}
- {{ event.name }}
{% endfor %}
```

For a rotating/cycling dashboard card or an ESPHome display, consider a
`template` sensor or an automation that steps through
`state_attr('sensor.checkiday_today', 'events')` on a timer and publishes
the current index's name to a helper `input_text`, which is easy for
ESPHome's `homeassistant.text_sensor` to consume (ESPHome can read entity
*state*, but not arbitrary attributes, directly).

## API usage

Checkiday's free APILayer plan allows **100 requests/month**. This
integration is designed around that constraint:

- **2 requests/day** (today + tomorrow) ≈ **60 requests/month**, about 60% of
  the free allowance.
- **1 request/day** (today only — disable "tomorrow" in options) ≈ **30
  requests/month**, about 30% of the free allowance.

That leaves headroom for the occasional Home Assistant restart or manual
refresh. If you need more than the free tier offers, APILayer sells paid
plans with a higher monthly quota — see the [pricing
page](https://apilayer.com/marketplace/checkiday-api#pricing).

## Disclaimer & fair use

- This integration is provided **as-is**, under the MIT License (see
  [LICENSE](LICENSE)).
- All National Day data, names, and descriptions are the property of
  Checkiday / Westy92 LLC, served via the APILayer marketplace. This project
  merely calls their public API on your behalf, using **your own** API key.
- Use of the Checkiday API is subject to [their terms](https://apilayer.com/marketplace/checkiday-api)
  — this integration is meant for personal, non-commercial, daily
  home-automation use, in line with the free tier it's built around.
- The icon at `custom_components/checkiday/brand/` is an original, generic
  calendar/star mark created for this project — it is **not** Checkiday's
  logo or brand imagery, specifically to avoid implying this is an official
  or endorsed integration.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE) © DemiVis
