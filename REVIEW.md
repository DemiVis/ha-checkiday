# Code Review — 2026-07-03 (COMPLETE)

Full review in priority order: security, docs/UX, HA best practices, code
quality, HACS default readiness. All clear-cut fixes were applied; discussion
items and repo-side checklist are at the bottom.

## 1. Security — PASS

No vulnerabilities found. Specifically verified: HTTPS-only to a fixed host
(`api.apilayer.com`), API key sent only as a request header and never logged
or echoed into entity state; diagnostics export redacts `api_key`; the config
entry unique_id is a SHA-256 of the key (non-reversible); no dynamic code
execution, no file writes, no shell, no YAML parsing of untrusted input; all
API JSON is defensively parsed with `.get()` + explicit `str()`/`int()`
coercion so a malformed or hostile response can't inject unexpected types
into HA state. Timeouts wrap every request; all aiohttp errors are caught and
converted to typed exceptions. The one hardening gap fixed this session:
`_parse_time` could crash entry setup on a malformed stored option — it now
falls back to midnight with a warning instead.

Low-risk items noted, no action taken (see Discussion): unbounded response
body read; API-supplied `error_detail` text (capped at 500 chars) shown in
the config-flow UI; API-supplied event URLs rendered as links by the README's
markdown card. All require APILayer itself to be compromised, and the HA
frontend sanitizes markdown, so these are acceptable as-is.

## 2. Documentation & UX — GOOD (two fixes applied)

Install/API-key/config docs are clear and HACS-standard. Config flow tests
the key live, surfaces the API's real error text, supports reauth, and the
options flow uses a proper TimeSelector. Error strings are specific and
placeholdered. Fixes applied: README entity table used entity_ids that don't
match what HA actually generates (`sensor.checkiday_today` →
`sensor.checkiday_national_day_today`, same for the diagnostic sensor, and
one `state_attr()` example); typo "tandum" → "tandem".

## 3. HA best practices — modernized this session

Applied (all compatible with the declared minimum HA 2024.12):

- **`entry.runtime_data`** replaces `hass.data[DOMAIN][entry_id]` storage,
  with a typed `CheckidayConfigEntry` alias in coordinator.py. This is the
  current quality-scale rule; `__init__.py`, `sensor.py`, and
  `diagnostics.py` updated; `DATA_COORDINATOR`/`DATA_UNSUB_SCHEDULE` consts
  removed.
- **Import locations**: `DeviceInfo` now from
  `homeassistant.helpers.device_registry`, `EntityCategory` from
  `homeassistant.const` (the `helpers.entity` re-exports are deprecated).
- **`icons.json`** added; the three `_attr_icon` attributes removed in favor
  of icon translations keyed by `translation_key`.
- **Reauth flow** now uses the `self._get_reauth_entry()` helper and
  `async_update_reload_and_abort(..., data_updates=...)` instead of manually
  stashing the entry from `self.context`; `entry_data` typed as `Mapping`.
- **`_parse_time` hardening** (also listed under security).

Already matching best practice (no change needed): config entry-only setup
(no YAML), `DataUpdateCoordinator` with `config_entry=` passed,
`has_entity_name` + translation keys, `strings.json`/`translations/en.json`
in sync, `_attr_attribution`, DeviceEntryType.SERVICE device grouping,
`entity_registry_enabled_default=False` for the convenience sensor,
diagnostics platform, `async_on_unload` cleanup, deliberate
`update_interval=None` with time-based triggering (right call for a
100-req/month API).

Known deviations that need a minimum-HA bump (left alone deliberately):

- `OptionsFlowWithReload` (HA ≥2025.7) would delete the manual
  update-listener + reload boilerplate.
- `AddConfigEntryEntitiesCallback` (HA ≥2025.1) is the newer type for the
  sensor platform's `async_add_entities` parameter.

If you're happy requiring HA ≥2025.7 in hacs.json, both are small follow-ups.

## 4. Code quality — HIGH

Clean separation (api client / coordinator / platforms / flow), thorough
docstrings that explain *why* (especially the free-tier constraints), typed
throughout, custom exception hierarchy, no dead code found. Minor nit not
fixed: pyproject.toml `version = "0.1.0"` doesn't match manifest 0.3.0 —
harmless since the package isn't built, but you may want to set it to
something like `"0.0.0"` with a comment, or keep it synced.

## 5. HACS default inclusion — code side READY; repo-side checklist for you

Per hacs.xyz/docs/publish/include (checked today), code requirements are met:
hacs.json has `name`; manifest has domain, docs, issue_tracker, codeowners,
version; a local `brand/` dir with `icon.png` satisfies the brands check (a
home-assistant/brands submission is only the fallback — you do NOT strictly
need it, though submitting there anyway gets you a UI icon in HA itself);
hacs/action + hassfest workflows are in place.

Repo-side items I can't verify from here — confirm on GitHub before
submitting:

- [ ] Repo has a **description**
- [ ] Repo has **topics** set
- [ ] **Issues enabled**
- [ ] At least one full GitHub **release** (not just a tag) created after
      both actions pass **with no errors or ignores**
- [ ] Then PR to `hacs/default`, adding the repo to the `integration` file
      **alphabetically**, from a branch (not master) on your personal fork,
      with the PR template filled out completely
- Note: review backlog is long (months); PR must stay editable (no org
  account).

## Discussion items (your call — happy to implement any)

1. **Min HA version bump** to 2025.7+ → enables `OptionsFlowWithReload` and
   `AddConfigEntryEntitiesCallback` cleanups above. HACS users on older HA
   would stop getting updates.
2. **Failed-fetch retry**: if the single daily fetch fails (API blip), the
   sensor stays stale ~24h. Options: schedule a bounded retry (e.g. hourly,
   max 3) after an UpdateFailed, at the cost of a few quota requests; or
   leave as-is (coordinator already retries at next setup/reload).
3. **Response-size cap** in api.py (e.g. reject bodies >1 MB) as
   defense-in-depth against a compromised upstream. Small change, mostly
   theoretical benefit.
4. **DST nuance**: the computed default update time is fixed at setup using
   the current UTC offsets; when DST shifts, the offset math can be off by an
   hour until the user reconfigures. Could recompute the schedule daily
   instead of storing a static time — more code for a small edge.

## Follow-up session (same day) — discussion items implemented

Per Demi's decisions, all four discussion items were resolved:

1. **Min HA bumped to 2025.7.0** (hacs.json). Options flow now extends
   `OptionsFlowWithReload` (manual update listener deleted from
   `__init__.py`); sensor platform uses `AddConfigEntryEntitiesCallback`.
2. **Bounded retry**: a failed scheduled refresh now retries every 30
   minutes, max 3 times (`RETRY_DELAY`/`MAX_RETRIES` in const.py, logic in
   `__init__.py`). After the final failure a **Repairs warning**
   (`stale_data`, translated in strings.json/en.json) tells the user the
   sensors stay unavailable until the next successful refresh; it's deleted
   automatically on any later success and on successful setup. Pending
   retries are cancelled on unload. Worst case: 3 extra API requests/day.
3. **Response-size cap: 256 kB** (`MAX_RESPONSE_BYTES`), enforced in api.py
   by reading at most cap+1 bytes (never buffering an oversized body) and
   raising `CheckidayApiError` on overflow. 256 kB ≈ 25x a heavy day's
   payload — plenty.
4. **DST note added to README** (Timezone limitations section) + a
   retry-behavior paragraph (API usage section).

Also: manifest version bumped 0.3.0 → 0.4.0 (release-worthy behavior
changes). pyproject.toml version left alone (dev-tooling only).

## Verification needed (hand-off)

Sandbox couldn't run ruff (stale mount + blocked installs). Please run:

    uv run ruff check custom_components/checkiday
    uv run ruff format custom_components/checkiday

and let CI (hassfest + HACS action) confirm on the PR. Files changed across
both sessions: `__init__.py`, `api.py`, `sensor.py`, `diagnostics.py`,
`config_flow.py`, `coordinator.py`, `const.py`, `icons.json` (new),
`strings.json`, `translations/en.json`, `manifest.json`, `hacs.json`,
`README.md`.

Worth a manual test of the new failure path: temporarily break the API key
(or block api.apilayer.com), trigger a refresh, and confirm the retry log
lines appear and the Repairs warning shows up / clears on recovery.
