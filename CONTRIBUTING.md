# Contributing

Thanks for considering a contribution. The most welcome contribution is
adding a profile for a kit you actually own. That's a five-line YAML
change. Code contributions are also welcome.

## Adding a profile

Profiles let new users pick a preset and skip the "what numbers should I
use?" decision. To add one:

1. Open [`custom_components/virtual_solar/profiles.yaml`](custom_components/virtual_solar/profiles.yaml).
2. Append a block at the bottom following the schema (see
   [`docs/profiles.md`](docs/profiles.md) for the field reference).
3. Run `python3 -c "import yaml; yaml.safe_load(open('custom_components/virtual_solar/profiles.yaml'))"`
   to confirm valid YAML.
4. Open a PR.

Conventions:

- `id`: `lower_snake_case`, no spaces.
- `name`: human-readable, what shows in the dropdown. Use the
  manufacturer's exact product name.
- `description`: short, one line, optional.
- Numeric fields are in their respective real-world units (kWh, W, %)
  with no suffix in the field name except where noted (`_kwh`, `_w`,
  `_pct`).

We will not accept profiles for hypothetical or vapourware products. The
preset list should reflect what people can actually buy.

## Code contributions

### Local setup

```bash
git clone https://github.com/virtuallytd/ha-virtual-solar.git
cd ha-virtual-solar
```

Python tooling isn't strictly required since the integration is loaded
inside Home Assistant. For static checks before pushing:

```bash
# Validate JSON / YAML / Python syntax
python3 -c "
import ast, json
for p in [
    'custom_components/virtual_solar/__init__.py',
    'custom_components/virtual_solar/config_flow.py',
    'custom_components/virtual_solar/const.py',
    'custom_components/virtual_solar/dashboard.py',
    'custom_components/virtual_solar/number.py',
    'custom_components/virtual_solar/sensor.py',
    'custom_components/virtual_solar/util.py',
]:
    ast.parse(open(p).read())
for p in [
    'custom_components/virtual_solar/manifest.json',
    'custom_components/virtual_solar/strings.json',
    'custom_components/virtual_solar/translations/en.json',
    'hacs.json',
]:
    json.load(open(p))
print('OK')
"
```

### Testing in Home Assistant

The fastest loop is to symlink the integration into a running HA
instance's `custom_components` directory:

```bash
ln -s "$(pwd)/custom_components/virtual_solar" /path/to/ha/config/custom_components/virtual_solar
```

Then restart HA and watch `home-assistant.log` for errors. After code
changes, reload via Developer Tools → YAML → Restart, or use HACS to
reload the integration without a full restart.

### CI

Every push to `main` and every PR runs hassfest + HACS validation via
[`.github/workflows/validate.yml`](.github/workflows/validate.yml). PRs
that don't pass both will not be merged.

### Manifest changes

Hassfest enforces:

- Manifest keys sorted as `domain`, `name`, then alphabetical.
- No `homeassistant` field (that's a core-integration concept; for HACS
  the minimum HA version lives in `hacs.json`).

### Releasing

Maintainers only.

1. Bump `version` in `custom_components/virtual_solar/manifest.json`.
2. Update [`CHANGELOG.md`](CHANGELOG.md) with the new version block.
3. Commit, push.
4. Tag: `git tag -a vX.Y.Z -m "vX.Y.Z" && git push origin vX.Y.Z`
5. Publish a GitHub Release referencing the changelog block.

## Reporting issues

Use [GitHub Issues](https://github.com/virtuallytd/ha-virtual-solar/issues).
Include:

- HA version
- Integration version (visible on the integration card)
- Steps to reproduce
- Relevant log lines from Settings → System → Logs (filter on
  `virtual_solar`)
