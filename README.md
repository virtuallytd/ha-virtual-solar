# Virtual Solar

A [Home Assistant](https://www.home-assistant.io/) custom integration that
simulates a solar panel + battery system from sensors you already own. Use it
to answer "would a balcony solar setup actually be worth it?" before spending
the money. Point it at an ambient light sensor and a whole-house power meter,
and it produces live solar output and battery status entities.

## What it does

- **Estimates solar panel output** from an ambient light (lux) reading using
  the well-known sunlight relationship `1 W/m² ≈ 120 lux`, scaled to the
  panel wattage and count you configure.
- **Reports virtual battery status** (Charging / Discharging / Full / Empty)
  based on the current solar estimate, your house consumption, and a battery
  level sensor of your choice (typically an `input_number` helper updated by
  an automation).

Both sensors update reactively. The moment the lux sensor or house
consumption changes, the entities recalculate. No polling.

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

All configuration is done through the UI. The setup wizard has three steps:

### Step 1: Sensors

| Field | What to pick |
|---|---|
| **Ambient light sensor** | A `sensor` entity with `device_class: illuminance`, reporting lux. Outdoor sensors give the best results. |
| **House consumption sensor** | A `sensor` entity with `device_class: power`, reporting your whole-house instantaneous draw in W. |

### Step 2: Solar panels

| Field | Range | Default |
|---|---|---|
| **Panel wattage (W)** | 100 – 800, step 10 | 500 |
| **Number of panels** | 1 – 4, step 1 | 1 |

### Step 3: Virtual battery

| Field | Range | Default |
|---|---|---|
| **Battery capacity (kWh)** | 0.1 – 30, step 0.01 | 2.68 |
| **Max charge/discharge rate (W)** | 100 – 10000, step 50 | 1200 (matches the Anker SOLIX inverter) |

All of these are editable post-install via the **Configure** button on the
integration card.

## Entities produced

| Entity ID | Unit | Notes |
|---|---|---|
| `sensor.virtual_solar_estimated_output` | W | `device_class: power`, `state_class: measurement`. Updates whenever the lux sensor, panel count, or panel wattage changes. |
| `number.virtual_solar_panel_count` | (none) | How many panels to simulate (1 – 4). Set from the wizard, live-editable via the dashboard slider. Drives `estimated_output`. |
| `number.virtual_solar_panel_wattage` | W | Rated wattage of a single panel (100 – 800). Set from the wizard, live-editable via the dashboard slider. Drives `estimated_output`. |
| `number.virtual_solar_battery_level` | kWh | The virtual battery's current stored energy. Self-updates every minute. User-editable, so you can manually reset it to 0 or full. Survives HA restarts. |
| `sensor.virtual_solar_battery_status` | n/a | Enum: `Charging`, `Discharging`, `Full`, `Empty`. Icon updates to match (`mdi:battery-charging`, `mdi:battery-minus`, `mdi:battery-check`, `mdi:battery-alert`). |

Battery status rules:

- `< 5%` of capacity → **Empty**
- `>= 99%` of capacity → **Full**
- `solar_output > house_consumption` → **Charging**
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
net_W      = solar_output − house_consumption
net_W      = clamp(net_W, −max_rate, +max_rate)
ΔkWh       = net_W × (60s / 3600s) / 1000
new_level  = clamp(current + ΔkWh, 0, capacity)
```

You don't need any helpers or automations. The number entity is
user-editable, so you can override the level from the UI at any time
(handy for resetting to 0 to simulate a depleted start, or to capacity
to test the "Full" state). Restarts persist the level via
`RestoreEntity`.

## Notes & caveats

- **Sensor placement matters more than anything else.** An indoor lux sensor
  will dramatically understate output; an outdoor unobstructed sensor at the
  panel's angle is ideal.
- The `1 W/m² ≈ 120 lux` constant is an approximation. Expect ±20% versus
  reality, more in winter and at low sun angles.
- Panel temperature derating, inverter losses, and panel degradation aren't
  modelled. This is a planning tool, not a yield estimator.

## License

MIT
