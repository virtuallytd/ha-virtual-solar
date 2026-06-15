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
| **Battery level sensor** | Any `sensor` (or `input_number`) reporting current stored energy in kWh | (none) |

All of these are editable post-install via the **Configure** button on the
integration card.

## Sensors produced

| Entity ID | Unit | Notes |
|---|---|---|
| `sensor.virtual_solar_estimated_output` | W | `device_class: power`, `state_class: measurement`. Updates whenever the lux sensor changes. |
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

If you'd rather paste a fixed YAML and edit the entity IDs by hand, use
[`dashboards/solar.yaml`](dashboards/solar.yaml). Search for `REPLACE_LUX`,
`REPLACE_HOUSE`, `REPLACE_LEVEL` and swap in your entity IDs.

The static template also ships with a few optional cards commented out
that depend on extra `input_number` helpers and template sensors (battery
percentage, charge rate, time-to-full) which aren't part of this
integration. Uncomment them once you've set those up.

## How the battery level moves

This integration does **not** modify the battery level sensor itself. It
only reads it. To drive it, create an `input_number` helper and an
automation that updates it every few minutes from the difference between
solar output and house consumption. A full worked example is on the blog
post that goes with this integration.

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
