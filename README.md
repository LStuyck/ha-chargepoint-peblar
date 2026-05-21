# ChargePoint (Peblar) Local API for Home Assistant

[![Release](https://img.shields.io/github/v/release/LStuyck/ha-chargepoint-peblar?style=flat-square&color=blue)](https://github.com/LStuyck/ha-chargepoint-peblar/releases)
[![License](https://img.shields.io/github/license/LStuyck/ha-chargepoint-peblar?style=flat-square)](LICENSE)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat-square)](https://hacs.xyz)
[![hassfest](https://github.com/LStuyck/ha-chargepoint-peblar/actions/workflows/hassfest.yml/badge.svg)](https://github.com/LStuyck/ha-chargepoint-peblar/actions/workflows/hassfest.yml)
[![HACS](https://github.com/LStuyck/ha-chargepoint-peblar/actions/workflows/hacs.yml/badge.svg)](https://github.com/LStuyck/ha-chargepoint-peblar/actions/workflows/hacs.yml)
[![Lint](https://github.com/LStuyck/ha-chargepoint-peblar/actions/workflows/lint.yml/badge.svg)](https://github.com/LStuyck/ha-chargepoint-peblar/actions/workflows/lint.yml)

A Home Assistant custom integration for ChargePoint EV chargers that run **Peblar** firmware (Prodrive Technologies) and expose the WLAC v1 **local REST API** on the LAN.

The integration talks directly to the charger over HTTP — **no cloud, no account required**.

> **Note**: This integration is community-maintained and not affiliated with ChargePoint, Inc. or Prodrive Technologies / Peblar. It targets chargers that run Peblar firmware version 1.6 or later with the local REST API enabled.

---

## Highlights

- 🔌 100% local — no cloud round-trips, no third-party account
- ⚡ Live power, current, voltage per phase + session/lifetime energy
- 🎛️ Charge current limit and 1-phase / 3-phase toggle (when supported)
- 🔧 UI configuration flow — no YAML
- 🔁 10-second polling, well under the charger's 5 req/s rate limit
- 🛠️ Diagnostic sensors for signal strength, uptime, firmware, active errors/warnings
- 🌍 Localised strings (extendable via translations folder)

## Exposed entities

### Sensors
- **Status** — readable string (No vehicle / Vehicle connected / Charging / Charging (ventilation) / Error / Fault) with the raw IEC 61851 control-pilot state as an attribute
- **Charge current limit**, **Charge current limit (actual)** (A) and **Charge current limit source** (e.g. "Dynamic load balancing", "User", etc.)
- **Current L1 / L2 / L3** (A) — three-phase aware
- **Voltage L1 / L2 / L3** (V)
- **Power L1 / L2 / L3** (W) and **Power total** (W)
- **Energy total** (kWh, `total_increasing`) — lifetime cumulative
- **Energy session** (kWh, `total_increasing`) — resets per session
- **Firmware version**, **WLAN signal strength**, **Cellular signal strength** (dBm)
- **Uptime** (seconds)
- **Active error codes**, **Active warning codes** — counts as state, raw integer codes in attributes

### Binary sensors
- **Charging** — true while a vehicle is drawing current
- **Vehicle connected** — true whenever a vehicle is plugged in
- **Cable locked**
- **Force 1-phase**
- **Has errors**, **Has warnings**

### Controls *(only when the charger's local API is in ReadWrite mode)*
- **Charge current limit (set)** — Number entity for setting the maximum current in A
- **Force 1-phase** — Switch (only created when the charger reports `Force1PhaseAllowed: true`)

### Services
- **`chargepoint_peblar.authorize_charge_session`** — (de)authorize a charge session using a token from the charger's local list
  - Fields: `device_id`, `method` (e.g. `Rfid`), `token`
  - Requires ReadWrite access mode

## Requirements

- **Home Assistant 2026.1.0** or newer
- A Peblar / ChargePoint charger on **firmware 1.6 or newer**
- The local REST API **enabled** in the charger's advanced settings page
- The 64-character API token (also in the charger's advanced settings)
- The charger set to **ReadWrite** access mode if you want the number, switch, and authorize service to load — sensors and binary sensors work in ReadOnly mode too

## Install via HACS (recommended)

1. In Home Assistant: **HACS** → ⋮ → **Custom repositories**.
2. Add `https://github.com/LStuyck/ha-chargepoint-peblar` with category **Integration**.
3. Find **ChargePoint (Peblar) Local API** in HACS and click **Download**.
4. Restart Home Assistant.
5. **Settings → Devices & Services → Add Integration** → search **ChargePoint (Peblar)**.
6. Enter the charger's IP and 64-character API token.

## Manual install

1. Copy the `custom_components/chargepoint_peblar/` folder into your HA config's `custom_components/` directory.
2. Restart Home Assistant.
3. Add the integration via **Settings → Devices & Services**.

## Configuration

All configuration is done through the UI — no YAML required. After install, the integration will ask for:

| Field | Example | Notes |
|---|---|---|
| Host or IP | `192.168.2.173` | LAN-reachable IP or hostname of the charger |
| API token | `64-character string` | From the charger's advanced settings page |

If the token is rejected, the form returns a clear error and you can try again. The charger's serial number is used as the integration's unique ID, so adding a second instance for the same charger is automatically blocked.

## How the integration polls the charger

Every 10 seconds the coordinator issues four parallel GETs (`/health`, `/system`, `/evinterface`, `/meter`) — about 0.4 req/s average. The charger's documented rate limit is 5 req/s shared with a burst of 10, so this leaves plenty of headroom if you have other clients hitting the same charger.

## Notes on units

- **Currents** are reported in mA by the API and converted to A.
- **Voltages** are reported and shown in V.
- **Powers** are reported and shown in W.
- **Energy** is reported in mWh and converted to kWh. If your charger reports energy in a different unit, the conversion lives in `custom_components/chargepoint_peblar/sensor.py` (the `_mwh_to_kwh` helper) — adjust the divisor and please open an issue with what you saw so this can auto-detect later.

## Troubleshooting

<details>
<summary><strong>Write entities (number, switch, service) don't appear</strong></summary>

The local API must be in **ReadWrite** mode. Open the charger's web UI → advanced settings → switch from ReadOnly to ReadWrite, then reload the integration in HA. The integration logs a warning on setup when this is the case.
</details>

<details>
<summary><strong>"Authentication failed" when adding the integration</strong></summary>

Re-copy the 64-character token from the charger's advanced settings page — make sure there's no trailing newline or surrounding whitespace. The API uses the raw token in the `Authorization` header (no `Bearer` prefix).
</details>

<details>
<summary><strong>Number entity caps at a current lower than my hardware supports</strong></summary>

The maximum value of the Number entity is snapshotted at first setup from whatever the charger reported as `ChargeCurrentLimit` at that moment. If a dynamic load balancer was active when you added the integration, the cap is the load-balanced value, not the hardware maximum. To raise it: change the limit in the charger's web UI to your desired ceiling, then reload the integration in HA → the new cap is picked up on the next setup.
</details>

<details>
<summary><strong>Energy values look 1000× too high or too low</strong></summary>

The OpenAPI spec doesn't document the unit explicitly; this integration treats `EnergyTotal` and `EnergySession` as mWh based on sample responses (a ~2.67 GWh-equivalent raw value implies mWh). If your charger differs, edit the `_mwh_to_kwh` divisor in `sensor.py` and please open an issue so the conversion can be made smarter for everyone.
</details>

<details>
<summary><strong>Charger is unreachable / connection refused</strong></summary>

Confirm that:
1. The charger is on the same LAN as your HA instance.
2. The local REST API is enabled (not just configured) — there's a separate toggle in the advanced settings page.
3. Nothing else is hitting the charger's API at >5 req/s (the rate limit is shared across all clients).
</details>

## Contributing

Issues and pull requests are welcome. Please:

- Open an issue first for any non-trivial change.
- Run `ruff check . --fix && ruff format .` before committing — the **Lint** workflow blocks PRs that fail.
- Avoid bumping the manifest `version` in a PR — that's done at release time.

## Acknowledgements

- [Peblar / Prodrive Technologies](https://peblar.com) for documenting the local REST API ([OpenAPI spec](https://peblar.com)).
- [HACS](https://hacs.xyz) for the custom-integration distribution channel.
- [ludeeus/integration_blueprint](https://github.com/ludeeus/integration_blueprint) for the CI workflow patterns this repo borrows from.

## License

MIT — see [LICENSE](LICENSE).
