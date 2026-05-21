# Contributing

Issues and pull requests are welcome.

## Filing an issue

- **Bug**: use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.yml). Include the diagnostics download — the **API token is redacted automatically**, so the file is safe to attach. Without diagnostics, most bug reports are guesswork.
- **Feature**: use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.yml). If the feature needs data from the charger that the integration doesn't already expose, link to the relevant Peblar OpenAPI endpoint.
- **Question or general discussion**: open a [Discussion](https://github.com/LStuyck/ha-chargepoint-peblar/discussions) instead of an issue.

## Submitting a pull request

1. Open an issue first for any non-trivial change — saves wasted work if the change isn't a fit.
2. Fork, branch from `main`, commit, push, open a PR against `main`.
3. CI must be green before review:
   - **Hassfest** — validates `manifest.json`
   - **HACS Validation** — validates HACS-required files
   - **Lint** — runs `ruff check` and `ruff format --check`

   To run the same checks locally:

   ```bash
   python -m pip install -r requirements.txt
   python -m ruff check .
   python -m ruff format .
   ```

4. **Do not bump `manifest.json` `version`** in your PR. The version is bumped by the maintainer at release time.
5. If the change is user-visible, add an entry under `## [Unreleased]` in [`CHANGELOG.md`](CHANGELOG.md).
6. If the change adds an entity, sensor, or service, update the feature list in `README.md`.

## Local development

Clone, then drop the `custom_components/chargepoint_peblar/` folder into your HA config's `custom_components/` directory (a symlink works well during development):

```bash
ln -s "$(pwd)/custom_components/chargepoint_peblar" /path/to/ha/config/custom_components/chargepoint_peblar
```

Restart HA. Iterate on the code, restart HA to pick up changes. Use **Settings → System → Logs** filtered on `chargepoint_peblar` to see what your changes are doing.

For changes to the `_async_update_data` coordinator method or anything that talks to the charger, the **Diagnostics download** is your best feedback loop: it dumps the raw `/system`, `/evinterface`, `/meter`, `/health` responses as the integration sees them.

## API reference

The charger's local REST API is documented by Peblar (Prodrive Technologies). The OpenAPI spec is the source of truth for field names — but be aware that **firmware variants disagree on some field names and may omit some fields entirely**. When in doubt, trust the diagnostics output over the spec.

## Code style

- Python 3.13 target (matches the lint workflow)
- 88-character line limit (ruff default)
- Double quotes for strings
- Type hints on public functions and class methods
- Docstrings on classes and public functions
- Imports sorted (handled automatically by `ruff check`)

## Release process (maintainer only)

1. Update `CHANGELOG.md`: move `## [Unreleased]` entries under a new dated heading.
2. Bump `custom_components/chargepoint_peblar/manifest.json` `version`.
3. Commit with message `vX.Y.Z: <summary>`.
4. Tag: `git tag -a vX.Y.Z -m "vX.Y.Z — <summary>"`.
5. Push branch and tag: `git push origin main && git push origin vX.Y.Z`.
6. On GitHub: Releases → Draft new release → choose tag → paste release notes (derived from CHANGELOG) → Publish.
7. HACS picks the new version up within ~1 hour; users see the update offer in their HACS dashboard.
