# Local Felicity for Home Assistant

[![Open your Home Assistant instance and open this repository inside HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=murilobast&repository=ha_felicity_inverter&category=integration)

Local Home Assistant integration for Felicity Solar devices.

Each config entry represents one local device:

- one serial inverter over RS232
- or one WiFi battery over the built-in local TCP endpoint

Multiple config entries are supported, so you can add one entry per inverter or battery.

## Features

- Reads inverter status registers directly from the inverter
- Reads FLA battery telemetry over the built-in local WiFi TCP endpoint
- Exposes a preset mode selector:
  - `grid_charge`
  - `grid_only`
  - `battery`
- Exposes writable `Max Grid Charge Current`
- Config flow support: when adding the integration, available `/dev/ttyUSB*` devices are listed for selection

## Important Safety Warning

The Felicity RJ45 inverter port exposes an extra **12V line on pin 3**.

That 12V line is **not used** for RS232 communication. The serial link only needs:

- `pin 1`: TX
- `pin 2`: RX
- `pin 8`: GND

If you are using the included RJ45 cable with a USB-RS232 adapter, the **green/white wire on pin 3 must be cut/disconnected** before connecting it to your adapter. Leaving pin 3 connected can overheat and permanently damage the adapter.

## Supported Communication

- Interface: RS232 on the inverter RJ45 port
- Serial settings: `2400 baud`, `8N1`
- Modbus slave ID: `1`
- Protocol: raw Modbus RTU

## Supported Entities

Serial inverter entries expose sensors for known status and settings registers, including:

- Working mode
- Charge mode
- Battery voltage, current and power
- Output voltage
- Grid voltage
- Load watts and load percentage
- PV voltage and PV power
- WiFi battery entries expose:
  - Battery SOC
  - Battery voltage, current and computed power
  - Battery min/max temperature
  - Battery min/max cell voltage and cell delta
  - Battery warning/fault/state diagnostic codes
- Charge and voltage thresholds from the settings block
- Output source priority and charge source priority
- Max charge current and max AC/grid charge current

Serial inverter control entities:

- `select`: `Preset Mode`
- `number`: `Max Grid Charge Current`

## Known Model-Specific Warnings

This inverter family is not fully consistent across models.

- On at least one tested model, `output_priority = 2` behaved like `BYPASS` instead of the expected SBU behavior.
- `charge_priority = 3` (`Only solar`) can leave the inverter stuck until a physical power cycle if there is no solar input.

Because of that, the `battery` preset should be treated carefully on real hardware:

- `grid_charge` -> `output=0`, `charge=2`
- `grid_only` -> `output=0`, `charge=0`
- `battery` -> `output=2`, `charge=3`

The integration exposes the actual inverter `working_mode` separately so you can compare the selected preset with the behavior the hardware reports back.

## HACS Installation

### Option 1: Custom repository

1. Open HACS in Home Assistant.
2. Open the menu in the top-right corner.
3. Select `Custom repositories`.
4. Add this repository URL:

```text
https://github.com/murilobast/ha_felicity_inverter
```

5. Select category `Integration`.
6. Install `Local Felicity`.
7. Restart Home Assistant.

### Option 2: Manual install

Copy the `custom_components/felicity_inverter` directory into your Home Assistant `custom_components` directory and restart Home Assistant.

## Home Assistant Setup

After installation:

1. Go to `Settings` -> `Devices & Services`.
2. Click `Add Integration`.
3. Search for `Local Felicity`.
4. Choose either `Serial inverter` or `WiFi battery`.
5. For inverter entries, select the serial device presented in the setup form, such as `/dev/ttyUSB0`.
6. For battery entries, enter the local battery IP, for example `10.0.0.16`.
7. Set the polling interval.

If no serial devices are detected automatically, you can enter the device path manually.

Battery entries send the local TCP command `wifilocalMonitor:get dev real infor` to the configured host on port `53970` by default.

## Production vs Development

This integration is designed for **direct serial access in production**.

The repository also contains `bridge.py` and other development scripts used during reverse engineering and testing, but those are not required by Home Assistant and are not used by the integration itself.

## Requirements

Your Home Assistant environment must have access to the serial adapter device, for example:

- `/dev/ttyUSB0`
- `/dev/ttyUSB1`

If Home Assistant runs in Docker, the serial device must be passed through to the container.

## Limitations

- Battery percentage / state of charge is not exposed by the current inverter Modbus register map.
- Battery SOC and cell telemetry require a separate WiFi battery entry.
- The integration currently targets the known Felicity register blocks already mapped in this repository.
- Different inverter firmware or models may expose additional registers or behave differently for control values.

## Credits

This project was informed by public reverse-engineering work and protocol references, especially:

- dj-nitehawk/Felicity-Inverter-Monitor
- mxbode/Felicitysolar-FLA48300-WiFi-Readout
- community protocol notes for Felicity RS232 Modbus communication

## Support

- Documentation: https://github.com/murilobast/ha_felicity_inverter
- Issues: https://github.com/murilobast/ha_felicity_inverter/issues
