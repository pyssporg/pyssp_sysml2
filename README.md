# pyssp_sysml2

Generate SSP and FMI artifacts from a SysML v2 architecture.

## 1) Install

```bash
pip install git+https://github.com/pyssporg/pyssp_sysml2
```

## 2) Generate Artifacts (CLI)

`pyssp` exposes two command families:

```bash
pyssp generate <ssd|ssv|fmi> [options]
pyssp sync ssd [options]
```

Common options:

- `--architecture`: folder containing `.sysml` files (or a file inside that folder)
- `--composition`: top-level part definition to generate from

### SSD

```bash
pyssp generate ssd \
  --architecture tests/fixtures/aircraft_subset \
  --composition AircraftComposition \
  --output build/generated/SystemStructure.ssd
```

### SSV

```bash
pyssp generate ssv \
  --architecture tests/fixtures/aircraft_subset \
  --composition AircraftComposition \
  --output build/generated/parameters.ssv
```

### FMI model descriptions

```bash
pyssp generate fmi \
  --architecture tests/fixtures/aircraft_subset \
  --composition AircraftComposition \
  --output-dir build/generated/model_descriptions
```

## 3) Sync Back from SSD to SysML

Apply edited SSD connection wiring back into SysML composition:

```bash
pyssp sync ssd \
  --architecture tests/fixtures/aircraft_subset \
  --composition AircraftComposition \
  --ssd build/generated/SystemStructure.ssd
```

Optional output directory (instead of overwriting source architecture files):

```bash
pyssp sync ssd \
  --architecture tests/fixtures/aircraft_subset \
  --composition AircraftComposition \
  --ssd build/generated/SystemStructure.ssd \
  --output-architecture-dir build/synced_sysml
```

## 4) Use as a Python Module

```python
from pathlib import Path

from pyssp_sysml2.ssd import generate_ssd
from pyssp_sysml2.ssv import generate_parameter_set
from pyssp_sysml2.fmi import generate_model_descriptions
from pyssp_sysml2.sync import sync_sysml_from_ssd

architecture = Path("tests/fixtures/aircraft_subset")
composition = "AircraftComposition"

generate_ssd(architecture, Path("build/generated/SystemStructure.ssd"), composition)
generate_parameter_set(architecture, Path("build/generated/parameters.ssv"), composition)
generate_model_descriptions(architecture, Path("build/generated/model_descriptions"), composition)
sync_sysml_from_ssd(
    architecture,
    Path("build/generated/SystemStructure.ssd"),
    composition,
    output_architecture_dir=Path("build/synced_sysml"),
)
```

## Runnable Examples

- CLI workflow: [`examples/cli_usage.sh`](/home/eriro/pwa/2_work/pyssp_sysml2/examples/cli_usage.sh)
- Python module workflow: [`examples/module_usage.py`](/home/eriro/pwa/2_work/pyssp_sysml2/examples/module_usage.py)

## Help / Discovery

```bash
pyssp --help
pyssp generate --help
pyssp generate ssd --help
pyssp generate ssv --help
pyssp generate fmi --help
pyssp sync --help
pyssp sync ssd --help
```

## Outputs

Typical generated structure:

- `build/generated/SystemStructure.ssd`
- `build/generated/parameters.ssv`
- `build/generated/model_descriptions/*/modelDescription.xml`

## Development Docs

Project internals, test/reference behavior, and maintainer workflow are in:

- [`docs/development.md`](/home/eriro/pwa/2_work/pyssp_sysml2/docs/development.md)
