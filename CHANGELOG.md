# Changelog

All notable changes to this project are documented here. Release notes
are also published on the [GitHub Releases page](https://github.com/virtuallytd/ha-virtual-solar/releases).

## 0.4.2 (2026-06-15)

**Fixed**: `virtual_solar.get_dashboard` now produces YAML that the HA
Raw configuration editor accepts cleanly.

- Drops the top-level `title:` (storage-mode dashboards set their title
  via the UI, and the validator rejected the extra key as
  `views: undefined`).
- Drops `path:` on the view (storage mode auto-slugs).
- Drops the deprecated `refresh_interval:` from history-graph cards.
- Indents list items under their parent key so the output matches the
  format HA's editor expects.

## 0.4.1 (2026-06-15)

Docs-only release.

- Added [`LICENSE`](LICENSE) (MIT).
- Added [`CHANGELOG.md`](CHANGELOG.md) with notes back to 0.1.0.
- Added [`CONTRIBUTING.md`](CONTRIBUTING.md) covering profile contributions, local dev, and the release workflow.
- Added [`docs/profiles.md`](docs/profiles.md) with the profile schema reference.
- Linked the above from the README.

## 0.4.0 (2026-06-15)

**Profiles**

The setup wizard now starts with a profile picker. Profiles live in
[`custom_components/virtual_solar/profiles.yaml`](custom_components/virtual_solar/profiles.yaml).
Starter set:

- Custom (no preset)
- Anker SOLIX SOLARBANK 3 E2700 Pro
- EcoFlow DELTA 2
- Generic 800 W balcony solar (DE)
- Generic 5 kW residential rooftop

See [docs/profiles.md](docs/profiles.md) for the schema and how to
contribute a new one.

**New parameters**

- `system_efficiency` (%): single multiplier wrapping inverter, wiring,
  and thermal losses. Default 95.
- `max_charge_rate` / `max_discharge_rate` (W): split from a single
  combined value to support asymmetric kits like the EcoFlow DELTA 2.

**New live entities**

- `number.virtual_solar_battery_capacity` (kWh, 0.1 – 100). Resizing the
  capacity auto-resizes the battery level slider.
- `number.virtual_solar_system_efficiency` (50 – 100 %).

**Migration**: v2 entries auto-migrate to v3. `max_discharge_rate` is
seeded from the existing `max_charge_rate`; `system_efficiency` defaults
to 95.

## 0.3.0 (2026-06-15)

Three derived sensors added so the dashboard can render the blog-style
layout without user-built template sensors:

- `sensor.virtual_solar_battery_percentage` (`device_class: battery`,
  dynamic icon).
- `sensor.virtual_solar_battery_charge_rate` (`device_class: power`,
  arrow icon flips with direction).
- `sensor.virtual_solar_battery_time_to_full` (human-readable string
  `2h 15m` / `Full` / `No solar input`).

The `virtual_solar.get_dashboard` service now produces a richer YAML
layout including these new entities.

## 0.2.1 (2026-06-15)

**Fixed**: battery status now reports the *action* before the
*condition*. A 0 % battery actively being charged now shows `Charging`
instead of `Empty`. New rule order:

1. `solar > house` and pct ≥ 99 → `Full`
2. `solar > house` → `Charging`
3. `solar ≤ house` and pct < 5 → `Empty`
4. otherwise → `Discharging`

## 0.2.0 (2026-06-15)

The integration now owns the simulation end-to-end. No more
`input_number` helpers or automations required.

**New entities**

- `number.virtual_solar_battery_level`: the virtual battery. Ticks every
  60 s applying `(solar − house)` capped at the configured rate; clamps
  to `[0, capacity]`; survives restarts via `RestoreEntity`.
- `number.virtual_solar_panel_count` (1 – 20).
- `number.virtual_solar_panel_wattage` (100 – 800 W).

`sensor.virtual_solar_estimated_output` reads panel count and wattage
from the live entities, so dashboard sliders recompute output instantly.

**New service**

- `virtual_solar.get_dashboard`: returns a Lovelace YAML pre-populated
  with the entity IDs from the config entry.

**Config flow**

- Initial setup is 3 steps (sensors → panel → battery), where the
  battery step asks for max charge/discharge rate (W) instead of a
  battery level sensor.
- Options flow is 2 steps; panel values are slider-controlled after
  install.

**Breaking**: if you ran 0.1.0, delete any `input_number.virtual_battery_level`
helpers and the 5-minute charge/discharge automation. They are no longer
used.

## 0.1.0 (2026-06-15)

Initial release. Two sensors driven by a user-supplied lux sensor, a
whole-house power sensor, and a user-managed battery level helper.
