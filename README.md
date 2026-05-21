# ChargePoint (Peblar) Local API for Home Assistant

A Home Assistant custom integration for ChargePoint EV chargers that run
Peblar firmware (Prodrive Technologies) and expose the WLAC v1 local REST
API on the LAN.

The integration talks directly to the charger over HTTP — no cloud, no
account required.

## Features

**Sensors**

- Status (No vehicle / Vehicle connected / Charging / Charging (ventilation) / Error / Fault)
- Charge current limit, charge current limit (actual), and limit source
- Current L1 / L2 / L3 (A)
- Voltage L1 / L2 / L3 (V)
- Power L1 / L2 / L3 (W) and Power total (W)
- Energy total (kWh) — lifetime, `total_increasing`
- Energy session (kWh) — current session, `total_increasing`
- Firmware version, WLAN / cellular signal strength, uptime
- Active error / warning code counts (raw codes in entity attributes)

**Binary sensors**

- Charging, Vehicle connected, Cable locked, Force 1-phase, Has errors, Has warnings

**Controls** (only when the local API is in ReadWrite mode)

- `number.charge_current_limit_set` — set the maximum charging current (A)
- `switch.force_1_phase` — toggle 1-phase / 3-phase charging
  (only created when the charger reports `Force1PhaseAllowed: true`)

**Services**

- `chargepoint_peblar.authorize_charge_session` — (de)authorize a charge session
  using a token from the charger's local list. Fields: `device_id`,
  `method` (e.g. `Rfid`), `token`.

## Requirements

- Home Assistant 2026.4.4 or newer
- A Peblar / ChargePoint charger on firmware 1.6 or newer
- The local REST API **enabled** in the charger's advanced settings page
- The 64-character API token (also in the charger's advanced settings)
- The charger must be set to **ReadWrite** access mode if you want the
  number, switch, and authorize service to load

## Install via HACS

1. In HACS → Integrations → ⋮ → **Custom repositories**, add this repo's URL
   as type **Integration**.
2. Find **ChargePoint (Peblar) Local API** and click Install.
3. Restart Home Assistant.
4. **Settings → Devices & Services → Add Integration** → search for
   *ChargePoint*.
5. Enter the charger's IP and API token.

## Manual install

1. Copy the `custom_components/chargepoint_peblar/` folder into your HA config's
   `custom_components/` directory.
2. Restart Home Assistant.
3. Add the integration via **Settings → Devices & Services**.

## API rate limits

The charger imposes a shared rate limit of 5 requests/second with a burst
of 10. This integration polls 4 endpoints every 10 seconds (0.4 req/s
average), well below the limit, but be aware if you have multiple clients
hitting the same charger.

## Notes on units

- Currents are reported in mA by the API and converted to A by the
  integration.
- Energy is reported in mWh by the API and converted to kWh. If your
  charger reports energy in a different unit, the conversion is in
  `custom_components/chargepoint_peblar/sensor.py` (the `_mwh_to_kwh` helper) —
  adjust the divisor as needed.

## Troubleshooting

- **Write entities don't appear** — check that the API is in **ReadWrite**
  mode (charger web UI → advanced settings). The integration warns about
  this in the HA log on setup.
- **Authentication failed** — re-copy the 64-character token from the
  charger's advanced settings page. It uses the raw token in the
  `Authorization` header (no `Bearer` prefix).
- **Number entity caps at a current lower than your hardware supports** —
  the cap is snapshotted at first setup from whatever `ChargeCurrentLimit`
  was at that moment. Raise the limit in the charger's web UI, then
  reload the integration in HA to pick up the new cap.

## License

MIT — see [LICENSE](LICENSE).
