# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0]

### Added
- Reauth flow: when the API token starts being rejected (HTTP 401), HA now prompts for a new token via Settings → Devices & Services instead of requiring the integration to be deleted and re-added. The new token is validated against the same charger's serial number to prevent silently re-pointing the entry at a different device.
- Repair issue (Settings → Repair) when the charger's local API is in ReadOnly mode. Replaces the previously log-only warning with an actionable card pointing to the README's troubleshooting section.
- GitHub issue templates (bug report, feature request) prompting for the integration version, HA version, firmware version, and diagnostics file.
- Pull request template with a checklist for ruff, CHANGELOG, README updates.
- `CONTRIBUTING.md` covering issue filing, PR workflow, local development setup, and the release process.
- `SECURITY.md` with a private-disclosure vulnerability reporting policy.
- This `CHANGELOG.md`.

## [1.0.3]

### Fixed
- Energy values were 1000× too small. The integration assumed milliwatt-hours but real firmware reports watt-hours; the conversion divisor is now correct. After upgrading, `Energy total` and `Energy session` will jump 1000× — this is the first correct reading, not new energy. HA's Energy dashboard may interpret the jump as delivered energy; if needed, reset statistics for the affected entities via Developer Tools → Statistics.
- WLAN signal strength was always Unknown because of a field-name mismatch (`WLANSignalStrength` in the OpenAPI spec vs `WlanSignalStrength` in actual firmware responses). Both spellings are now accepted.
- `Cable locked` binary sensor stuck on Unknown for firmware variants (notably ChargePoint-branded Peblar) that don't expose `LockState`. The entity is now skipped at setup on those firmwares.

## [1.0.2]

### Added
- Diagnostics handler. Settings → Devices & Services → ChargePoint card → ⋮ → **Download diagnostics** now exposes the latest `/health`, `/system`, `/evinterface` and `/meter` payloads plus runtime state. The API token is redacted.

### Fixed
- All six binary sensors (Charging, Vehicle connected, Cable locked, Force 1-phase, Has errors, Has warnings) were stuck on Unknown in v1.0.0 because the `is_on` property had been truncated to an empty docstring during file-writes. Property restored.

## [1.0.0]

First stable release. Read-only sensors, binary sensors, optional number/switch (in ReadWrite mode), authorize service, UI config flow, HACS-installable with local brand assets.

## [0.2.x]

Domain renamed from `chargepoint` to `chargepoint_peblar` to avoid collision with the Home Assistant core ChargePoint integration. Added Hassfest + HACS + Lint CI workflows and Dependabot.

## [0.1.x]

Initial preview releases.

[Unreleased]: https://github.com/LStuyck/ha-chargepoint-peblar/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/LStuyck/ha-chargepoint-peblar/compare/v1.0.3...v1.1.0
[1.0.3]: https://github.com/LStuyck/ha-chargepoint-peblar/compare/v1.0.2...v1.0.3
[1.0.2]: https://github.com/LStuyck/ha-chargepoint-peblar/compare/v1.0.0...v1.0.2
[1.0.0]: https://github.com/LStuyck/ha-chargepoint-peblar/releases/tag/v1.0.0
