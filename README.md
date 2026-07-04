# Checkiday National Day for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Home Assistant custom integration that surfaces today's
["National Day"](https://checkiday.com) — e.g. *National Pizza Day*,
*International Cat Day* — as a sensor, using the
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

- Fetches **today's** National Day(s) from Checkiday.
- Most calendar dates have *multiple* observances — every event is exposed
  in a structured attribute list so a dashboard, template, or ESPHome display
  can iterate through all of them, not just the first one.
- Runs on your own schedule: fetches once per day at a **local time you
  choose**, instead of constant polling. The default time is chosen
  automatically to work around a Free-plan limitation — see
  [Timezone limitations](#timezone-limitations) below.
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
3. After setup, click **Configure** on the integration to adjust the
   **daily update time** — the local time each day the integration fetches
   new data. See [Timezone limitations](#timezone-limitations) for why the
   default isn't always `00:00:00`.

If your API key later stops working (revoked, quota exhausted long-term,
etc.), Home Assistant will prompt you to re-authenticate with a new key
without losing your other settings.

## Entities

| Entity | Description |
| --- | --- |
| `sensor.checkiday_national_day_today` | State = the first National Day for today. Attributes include the full `events` list (`id`, `name`, `url` for every event today), `event_count`, `all_names`, and any multi-day events starting/ongoing. |
| `sensor.checkiday_national_day_api_requests_remaining` | Diagnostic sensor showing your remaining monthly API requests (from the API's rate-limit headers). |

There's also an `all_names` sensor (all of today's event names joined into
one string) that's disabled by default — it's there under **Settings →
Devices & Services → Entities** if you'd rather enable a ready-made entity
than build the template below yourself, but the dashboard card is the
better way to see everything at a glance.

### Seeing all of today's events without digging through attributes

The entity's "details" popup only shows one value at a time, so to see the
full list at a glance, add a **Markdown card** to your dashboard:

```yaml
type: markdown
content: |
  {% for event in state_attr('sensor.checkiday_national_day_today', 'events') %}
  - [{{ event.name }}]({{ event.url }})
  {% endfor %}
title: Today's National Days
```

For a rotating/cycling dashboard card or an ESPHome display, consider a
`template` sensor or an automation that steps through
`state_attr('sensor.checkiday_national_day_today', 'events')` on a timer and publishes
the current index's name to a helper `input_text`, which is easy for
ESPHome's `homeassistant.text_sensor` to consume (ESPHome can read entity
*state*, but not arbitrary attributes, directly).

## Timezone limitations

The Checkiday API's Free plan is more restrictive than the client library
examples suggest. Per
[APILayer's own API reference](https://marketplace.apilayer.com/checkiday-api/tabs/api_docs),
the `events` endpoint's `date` parameter requires a **Pro or Enterprise**
plan, and its `timezone` parameter requires **Enterprise**. On the Free
plan, the only request this integration can make is the bare endpoint with
no date or timezone — which means:

- **There's no lookup.** Asking for a specific date requires a
  paid plan, so this integration only ever fetches today.
- **"Today" is always calculated in the API's own timezone (America/Chicago,
  Central Time)** — not whatever timezone your Home Assistant instance is
  set to, since overriding that also requires Enterprise.

To make the second point as painless as possible, the integration doesn't
just default to your local midnight. Instead, it computes the local clock
time that corresponds to Central Time's midnight, and uses that as the
default daily update time — so that by the time it fetches, the API's
calendar day has already rolled over to match yours. Concretely, for US
timezones:

| Your timezone | Default update time |
| --- | --- |
| Pacific / Mountain | `00:00:00` (Central has already rolled over) |
| Central | `00:00:00` |
| Eastern | `01:00:00` (waits 1 hour for Central to catch up) |

For timezones far from Central Time — especially outside the Americas —
this can produce a much later default update time, or in extreme cases
there may be no local time at which both calendars agree on "today" for a
full 24 hours. If you're outside the US, check the computed default under
**Configure** after setup, and adjust it if needed. Regardless of the
update time chosen, there will always be a window around your local
midnight where the "Today" sensor is technically still showing the
*previous* Central-Time day.

## API usage

Checkiday's free APILayer plan allows **100 requests/month**. This
integration makes **1 request/day** ≈ **30 requests/month**, about 30% of
the free allowance — leaving headroom for the occasional Home Assistant
restart or manual reload. If you need more than the free tier offers,
APILayer sells paid plans with a higher monthly quota — see the
[pricing page](https://apilayer.com/marketplace/checkiday-api#pricing).

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
- This code was written in tandem both manually and with the help of Claude Code. 
  The author is a software engineer and attempts to use LLMs to assist in coding
  as responsibly as possible, and performs manual review of all edited lines. But 
  some people don't want to use any code known to be made with AI so this notice
  serves as a transparent notice to those folks. 

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE) © DemiVis
