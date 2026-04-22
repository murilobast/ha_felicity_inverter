# Felicity Inverter for Home Assistant

[![Open your Home Assistant instance and open this repository inside HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=murilobast&repository=ha_felicity_inverter&category=integration)

Local Home Assistant integration for Felicity Solar inverters that expose Modbus RTU over the RS232 RJ45 port.

This integration talks directly to the serial device available inside Home Assistant, typically `/dev/ttyUSB0`, and does not depend on the vendor cloud.

## Features

- Reads inverter status registers directly from the inverter
- Reads known writable settings for visibility in Home Assistant
- Exposes a preset mode selector:
  - `grid_charge`
  - `grid_only`
  - `battery`
- Exposes writable `Max Grid Charge Current`
- Config flow support: when adding the integration, available `/dev/ttyUSB*` devices are listed for selection

## Important Safety Warning

The Felicity RJ45 RS232 cable carries **12V on pin 3**.

If you are using the included RJ45 cable with a USB-RS232 adapter, the **green/white wire must be cut/disconnected** before connecting it to your adapter. Failing to do this can overheat and permanently damage the adapter.

Only TX, RX and GND are needed.

## Supported Communication

- Interface: RS232 on the inverter RJ45 port
- Serial settings: `2400 baud`, `8N1`
- Modbus slave ID: `1`
- Protocol: raw Modbus RTU

## Supported Entities

The integration currently exposes sensors for known status and settings registers, including:

- Working mode
- Charge mode
- Battery voltage, current and power
- Output voltage
- Grid voltage
- Load watts and load percentage
- PV voltage and PV power
- Charge and voltage thresholds from the settings block
- Output source priority and charge source priority
- Max charge current and max AC/grid charge current

Control entities:

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
6. Install `Felicity Inverter`.
7. Restart Home Assistant.

### Option 2: Manual install

Copy the `custom_components/felicity_inverter` directory into your Home Assistant `custom_components` directory and restart Home Assistant.

## Home Assistant Setup

After installation:

1. Go to `Settings` -> `Devices & Services`.
2. Click `Add Integration`.
3. Search for `Felicity Inverter`.
4. Choose the serial device presented in the setup form, such as `/dev/ttyUSB0`.
5. Set the polling interval.

If no serial devices are detected automatically, you can enter the device path manually.

## Production vs Development

This integration is designed for **direct serial access in production**.

The repository also contains `bridge.py` and other development scripts used during reverse engineering and testing, but those are not required by Home Assistant and are not used by the integration itself.

## Requirements

Your Home Assistant environment must have access to the serial adapter device, for example:

- `/dev/ttyUSB0`
- `/dev/ttyUSB1`

If Home Assistant runs in Docker, the serial device must be passed through to the container.

## Limitations

- Battery percentage / state of charge is not exposed directly by the currently known inverter register map.
- The integration currently targets the known Felicity register blocks already mapped in this repository.
- Different inverter firmware or models may expose additional registers or behave differently for control values.

## Credits

This project was informed by public reverse-engineering work and protocol references, especially:

- dj-nitehawk/Felicity-Inverter-Monitor
- community protocol notes for Felicity RS232 Modbus communication

## Support

- Documentation: https://github.com/murilobast/ha_felicity_inverter
- Issues: https://github.com/murilobast/ha_felicity_inverter/issues
