# Profiles

A profile is a named bundle of defaults for a real-world solar + battery
kit. When users install Virtual Solar, the first step of the setup
wizard is a dropdown of profiles. Picking one prefills the panel and
battery steps; users can still override any value before finishing
setup and tweak live entities from the dashboard afterwards.

Profiles live in
[`custom_components/virtual_solar/profiles.yaml`](../custom_components/virtual_solar/profiles.yaml).
The file is shipped as part of the integration, so adding a profile
requires a new release to surface in HACS.

## Schema

Each profile is a YAML block in the top-level list.

```yaml
- id: my_profile_id
  name: "My Profile Display Name"
  description: "Optional one-line description."
  battery_capacity_kwh: 2.68
  max_charge_rate_w: 1200
  max_discharge_rate_w: 1200
  panel_wattage: 500
  panel_count: 1
  system_efficiency_pct: 95
```

### Required

| Field | Type | Notes |
|---|---|---|
| `id` | string | `lower_snake_case`, unique across the file. Used internally and stored in the config entry. |
| `name` | string | Shown in the dropdown. Use the manufacturer's exact product name where applicable. |

### Optional

All field values are used to prefill the wizard. Missing fields fall
back to the integration's built-in defaults (500 W panel, 1 panel,
2.68 kWh capacity, 1200 W charge/discharge, 95 % efficiency).

| Field | Unit | Range | What it sets |
|---|---|---|---|
| `description` | string | n/a | Short blurb shown under the name. |
| `battery_capacity_kwh` | kWh | 0.1 – 100 | Total storage capacity. |
| `max_charge_rate_w` | W | 100 – 15000 | Max watts the battery can absorb. |
| `max_discharge_rate_w` | W | 100 – 15000 | Max watts the battery/inverter can supply. Often equal to charge rate; sometimes higher (e.g. EcoFlow DELTA 2: 500/1800). |
| `panel_wattage` | W | 100 – 800 | Rated wattage of a single panel. |
| `panel_count` | integer | 1 – 20 | Default number of panels in the array. |
| `system_efficiency_pct` | % | 50 – 100 | Combined inverter + wiring + thermal losses. ~95 % is a reasonable default for most kits. |

## Worked example: EcoFlow DELTA 2

A portable power station with notably asymmetric charge/discharge rates.

```yaml
- id: ecoflow_delta_2
  name: "EcoFlow DELTA 2"
  description: "Portable 1 kWh power station with solar input."
  battery_capacity_kwh: 1.024
  max_charge_rate_w: 500
  max_discharge_rate_w: 1800
  panel_wattage: 400
  panel_count: 1
  system_efficiency_pct: 92
```

Three things this models that a symmetric profile wouldn't:

1. The 500 W solar input limit shapes how fast the battery fills.
2. The 1800 W output limit means it can run high-draw appliances briefly.
3. The slightly lower efficiency (92 %) reflects the portable form
   factor's smaller inverter.

## Where the values come from

For each piece of kit, the spec sheet usually lists:

- Battery capacity: stated directly, e.g. "2.68 kWh".
- Max charge rate: look for "solar input max" or "AC input max".
- Max discharge rate: look for "AC output max" or "continuous output".
- System efficiency: rarely stated. Use ~95 % for fixed home systems
  and ~90 – 93 % for portable kits.

For panel wattage and count, pick what a buyer would realistically pair
with the battery. The user can change these via slider after install.

## Contributing a profile

See [`CONTRIBUTING.md`](../CONTRIBUTING.md). The process is one YAML
append + a PR. We won't accept profiles for vapourware or
manufacturer-only samples; the list should reflect what's actually
buyable.
