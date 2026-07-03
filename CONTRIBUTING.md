# Contributing

Thanks for considering a contribution to Checkiday National Day for Home Assistant.

## Ground rules

- This is an unofficial, community integration. It is not affiliated with Checkiday, Westy92 LLC, or APILayer — please keep contributions consistent with that (no impersonation, no claiming official support).
- Be mindful of the Checkiday free tier's 100 requests/month limit. Any change that increases API call frequency needs a clear justification and should stay opt-in.
- Never commit real API keys, tokens, or personal Home Assistant configuration.

## Local development

1. Clone this repo into a Home Assistant dev environment (or symlink `custom_components/checkiday` into an existing HA config's `custom_components/` folder).
2. Restart Home Assistant and add the integration via **Settings → Devices & Services → Add Integration → Checkiday National Day**.
3. Enable debug logging while testing:

   ```yaml
   logger:
     default: info
     logs:
       custom_components.checkiday: debug
   ```

## Before opening a PR

- `ruff check custom_components/checkiday`
- `ruff format custom_components/checkiday`
- `python -m py_compile` over all changed files
- Update `strings.json` **and** `translations/en.json` together — they must stay in sync
- Bump `version` in `manifest.json` for release-worthy changes

## Reporting bugs / requesting features

Please use the issue templates. Redact your API key from any logs before posting.
