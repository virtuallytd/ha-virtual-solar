# Virtual Solar

A [Home Assistant](https://www.home-assistant.io/) custom integration that
simulates a solar panel + battery system from sensors you already own. Use it
to answer "would a balcony solar setup actually be worth it?" before spending
the money. Point it at an ambient light sensor and a whole-house power meter,
and it produces live solar output and battery status entities.

## What it does

- **Estimates solar panel output** from an ambient light (lux) reading using
  the sunlight approximation `1 W/m² ≈ 120 lux`, scaled to panel wattage,
  count, and system efficiency.
- **Simulates a virtual battery** that charges and discharges over time based
  on solar input minus house consumption, capped at configurable charge and
  discharge rates.
- **Reports a friendly status** (Charging / Discharging / Full / Empty) and
  derived metrics (battery %, net flow, time-to-full).

Everything updates reactively. The battery ticks once a minute and survives
HA restarts.

## Profiles

The setup wizard's first step lets you pick from preset kits in
[`custom_components/virtual_solar/profiles.yaml`](custom_components/virtual_solar/profiles.yaml).
Today: Anker SOLIX SOLARBANK 3 E2700 Pro, EcoFlow DELTA 2, a generic 800 W
balcony kit, a generic 5 kW rooftop, and Custom. Each profile prefills the
panel and battery defaults; you can still override anything before
finishing setup, and you can adjust live values via the dashboard sliders
afterwards.

**Adding a profile** is a one-block YAML append in that file. See the
inline comments for the schema. PRs welcome.

## Installation

### HACS (recommended)

1. In HACS → **Integrations** → menu → **Custom repositories**.
2. Add `https://github.com/virtuallytd/ha-virtual-solar` with category
   **Integration**.
3. Find "Virtual Solar" in the HACS integration list and install it.
4. Restart Home Assistant.
5. **Settings → Devices & Services → Add Integration**, search for
   "Virtual Solar".

### Manual

1. Copy `custom_components/virtual_solar/` into your Home Assistant
   `config/custom_components/` directory.
2. Restart Home Assistant.
3. **Settings → Devices & Services → Add Integration**, search for
   "Virtual Solar".

## Configuration

All configuration is done through the UI. The setup wizard has four steps:

### Step 1: Profile

A dropdown of preset kits. Pick one to prefill the next steps, or "Custom"
to fill everything manually.

### Step 2: Sensors

| Field | What to pick |
|---|---|
| **Ambient light sensor** | A `sensor` entity with `device_class: illuminance`, reporting lux. Outdoor sensors give the best results. |
| **House consumption sensor** | A `sensor` entity with `device_class: power`, reporting your whole-house instantaneous draw in W. |

### Step 3: Solar panels

| Field | Range | Default |
|---|---|---|
| **Panel wattage (W)** | 100 – 800, step 10 | 500 |
| **Number of panels** | 1 – 20, step 1 | 1 |

### Step 4: Virtual battery

| Field | Range | Default |
|---|---|---|
| **Battery capacity (kWh)** | 0.1 – 100, step 0.01 | 2.68 |
| **Max charge rate (W)** | 100 – 15000, step 50 | 1200 |
| **Max discharge rate (W)** | 100 – 15000, step 50 | 1200 |
| **System efficiency (%)** | 50 – 100, step 1 | 95 |

After install, the **Configure** dialog only edits sensors and battery/inverter
specs (charge rate, discharge rate, efficiency, capacity). Panel count, panel
wattage, battery capacity, and system efficiency are also live-editable as
sliders on the dashboard, so you don't need to open Configure to tweak them.

## Entities produced

| Entity ID | Unit | Notes |
|---|---|---|
| `sensor.virtual_solar_estimated_output` | W | `device_class: power`, `state_class: measurement`. Updates whenever lux, panel count, panel wattage, or system efficiency changes. |
| `number.virtual_solar_panel_count` | (none) | How many panels to simulate (1 – 20). Live-editable via the dashboard slider. Drives `estimated_output`. |
| `number.virtual_solar_panel_wattage` | W | Rated wattage of a single panel (100 – 800). Live-editable. Drives `estimated_output`. |
| `number.virtual_solar_battery_capacity` | kWh | Total battery capacity (0.1 – 100). Live-editable. The battery level slider auto-resizes when you change it. |
| `number.virtual_solar_system_efficiency` | % | Combined inverter + wiring + thermal losses (50 – 100). Live-editable. Applied as a multiplier on solar output before any other calculation. |
| `number.virtual_solar_battery_level` | kWh | The virtual battery's current stored energy. Ticks every minute. User-editable for manual resets. Survives HA restarts. |
| `sensor.virtual_solar_battery_percentage` | % | `device_class: battery`. `(level / capacity) * 100` with a dynamic icon that tracks charge level. |
| `sensor.virtual_solar_battery_charge_rate` | W | `device_class: power`. Net flow into (positive) or out of (negative) the battery, clamped at the configured max rate. Icon flips between `mdi:battery-arrow-up` and `mdi:battery-arrow-down`. |
| `sensor.virtual_solar_battery_time_to_full` | n/a | Human-readable countdown like `2h 15m`, or `Full` / `No solar input` when those apply. |
| `sensor.virtual_solar_battery_status` | n/a | Enum: `Charging`, `Discharging`, `Full`, `Empty`. Action wins over condition (a 0% battery being charged shows `Charging`). Icon updates to match. |

Battery status rules (action takes precedence over condition):

- `solar > house` and capacity reached (`>= 99%`) → **Full**
- `solar > house` → **Charging**
- `solar <= house` and battery near empty (`< 5%`) → **Empty**
- Otherwise → **Discharging**

## Sample dashboard

There are two ways to get a Virtual Solar dashboard.

### Option A: auto-generated (recommended)

The integration registers a service that builds a dashboard YAML using the
entity IDs you picked in the config flow, so there's nothing to find-and-
replace.

1. **Developer Tools → Actions** (older HA: "Services").
2. Select **Virtual Solar: Get dashboard YAML**.
3. Click **Perform action**. The response panel shows a `yaml` field.
4. Copy that string.
5. **Settings → Dashboards → Add Dashboard → New dashboard from scratch**.
6. Open the new dashboard, **Edit dashboard** → 3-dot menu → **Raw
   configuration editor** and paste.

If you change anything in the integration's **Configure** dialog, re-run
the service to get a fresh YAML.

### Option B: static template

If you'd rather paste a fixed YAML and edit the entity IDs by hand, copy
the YAML below into a new dashboard's Raw configuration editor and
search for `REPLACE_LUX` and `REPLACE_HOUSE`, then swap each one for the
entity ID you picked during the integration config flow.

```yaml
title: Solar
views:
  - title: Solar
    path: solar
    icon: mdi:solar-panel
    cards:
      - type: gauge
        entity: sensor.virtual_solar_estimated_output
        name: Estimated Solar Output
        min: 0
        max: 2000 # raise to (panel_wattage * panel_count) for your setup
        needle: true
        severity:
          green: 500
          yellow: 150
          red: 0

      - type: gauge
        entity: number.virtual_solar_battery_level
        name: Battery Level
        min: 0
        max: 2.68 # raise to your configured capacity
        needle: true

      - type: entity
        entity: sensor.virtual_solar_battery_status
        name: Battery Status

      - type: entities
        title: Current Status
        entities:
          - entity: sensor.virtual_solar_estimated_output
            name: Solar Output
            icon: mdi:solar-panel
          - entity: REPLACE_HOUSE # your house consumption sensor
            name: House Consumption
            icon: mdi:home-lightning-bolt
          - entity: number.virtual_solar_battery_level
            name: Stored Energy
            icon: mdi:battery
          - entity: REPLACE_LUX # your lux sensor
            name: Light Level
            icon: mdi:brightness-5

      - type: entities
        title: Solar Panel Setup
        entities:
          - entity: number.virtual_solar_panel_wattage
            name: Panel wattage (W)
            icon: mdi:solar-panel
          - entity: number.virtual_solar_panel_count
            name: Number of panels
            icon: mdi:solar-panel-large

      - type: history-graph
        title: Solar Output (24h)
        hours_to_show: 24
        entities:
          - entity: sensor.virtual_solar_estimated_output
            name: Estimated Output (W)

      - type: history-graph
        title: Solar & Battery (7 days)
        hours_to_show: 168
        refresh_interval: 300
        entities:
          - entity: sensor.virtual_solar_estimated_output
            name: Solar Output (W)
          - entity: number.virtual_solar_battery_level
            name: Stored Energy (kWh)
```

## How the battery level moves

The integration owns `number.virtual_solar_battery_level` and ticks it
every minute:

```
raw_solar   = (lux / 120) × panel_wattage × panel_count / 1000
solar       = raw_solar × system_efficiency
net_W       = solar − house_consumption
net_W       = clamp(net_W, −max_discharge_rate, +max_charge_rate)
ΔkWh        = net_W × (60s / 3600s) / 1000
new_level   = clamp(current + ΔkWh, 0, capacity)
```

The slider is user-editable, so you can manually reset to 0 (depleted) or
capacity (full) any time. Restarts persist the level via `RestoreEntity`.

## Notes & caveats

- **Sensor placement matters more than anything else.** An indoor lux sensor
  will dramatically understate output; an outdoor unobstructed sensor at the
  panel's angle is ideal.
- The `1 W/m² ≈ 120 lux` constant is an approximation. Expect ±20% versus
  reality, more in winter and at low sun angles.
- System efficiency lumps inverter, wiring, and thermal losses into a single
  multiplier. Panel temperature derating and panel degradation aren't
  modelled separately. This is a planning tool, not a yield estimator.

## License

MIT
