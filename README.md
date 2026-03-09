# pyssp_sysml2

Generate SSP and FMI artifacts from a SysML v2 architecture.

## Who This Is For

- `README.md` (this file): package users who want to generate/sync artifacts.
- `docs/development.md`: contributors and maintainers.

## Workflow Overview

Typical workflow:

1. Start from a SysML architecture (`*.sysml`).
2. Generate SSD (`SystemStructure.ssd`) for system wiring.
3. Generate SSV (`parameters.ssv`) for default parameter values.
4. Generate FMI `modelDescription.xml` per component.
5. Optionally edit SSD wiring in an external tool.
6. Sync SSD wiring changes back into SysML composition (`pyssp sync ssd`).

If no SysML files are available yet, `pyssp sync ssd` can also bootstrap a minimal SysML architecture from an SSD.

## 1) Install

```bash
pip install git+https://github.com/pyssporg/pyssp_sysml2
```

For local development:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## 2) Generate Artifacts (CLI)

`pyssp` exposes two command families:

```bash
pyssp generate <ssd|ssv|fmi> [options]
pyssp sync ssd [options]
```

Common options:

- `--architecture`: folder containing `.sysml` files (or a file inside that folder). For `sync ssd`, this can also be an empty directory to bootstrap SysML from SSD.
- `--composition`: top-level part definition to generate from

### SSD

```bash
pyssp generate ssd \
  --architecture examples/aircraft_subset \
  --composition AircraftComposition \
  --output build/generated/SystemStructure.ssd
```

### SSV

```bash
pyssp generate ssv \
  --architecture examples/aircraft_subset \
  --composition AircraftComposition \
  --output build/generated/parameters.ssv
```

### FMI model descriptions

```bash
pyssp generate fmi \
  --architecture examples/aircraft_subset \
  --composition AircraftComposition \
  --output-dir build/generated/model_descriptions
```

## 3) Sync Back from SSD to SysML

Apply edited SSD connection wiring back into SysML composition:

```bash
pyssp sync ssd \
  --architecture examples/aircraft_subset \
  --composition AircraftComposition \
  --ssd build/generated/SystemStructure.ssd
```

Optional output directory (instead of overwriting source architecture files):

```bash
pyssp sync ssd \
  --architecture examples/aircraft_subset \
  --composition AircraftComposition \
  --ssd build/generated/SystemStructure.ssd \
  --output-architecture-dir build/synced_sysml
```

Bootstrap SysML from SSD when no `.sysml` files exist yet:

```bash
mkdir -p build/new_architecture
pyssp sync ssd \
  --architecture build/new_architecture \
  --composition AircraftComposition \
  --ssd build/generated/SystemStructure.ssd
```

### Sync Capabilities and Limits

`pyssp sync ssd` currently syncs **composition parts and connection wiring** from SSD back to SysML.

Supported:

- Adding/removing component instances through SSD component edits when the component `source` resolves to a known SysML part definition.
- Adding/removing/changing port-to-port composition connections through SSD connection edits.
- Writing updates in-place or to a separate output architecture directory.
- Bootstrapping a minimal SysML architecture from SSD when the architecture directory has no `.sysml` files.

Not supported (command will fail with a validation error):

- Partial attribute mapping for a port connection (for example only `x` but not `y`).
- Attribute remapping between different names (`port.a -> port.b`).
- Connections between incompatible port definitions.
- Unknown components/ports that do not exist in the SysML composition.
- Nested SSD systems (only flat SSD systems with components are supported).

Notes for SSD-only bootstrap:

- Generated SysML is intentionally minimal and exported to `architecture.sysml`.
- Part names are derived from SSD component `source` (FMU stem) when available, otherwise from component names.
- Port definitions are inferred from SSD connector attribute signatures.

## 4) Use as a Python Module

```python
from pathlib import Path

from pyssp_sysml2.ssd import generate_ssd
from pyssp_sysml2.ssv import generate_parameter_set
from pyssp_sysml2.fmi import generate_model_descriptions
from pyssp_sysml2.sync import sync_sysml_from_ssd

architecture = Path("examples/aircraft_subset")
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

From repo root:

```bash
# Ensure dependencies are installed first (see Local development above).
bash examples/cli_usage.sh
PYTHONPATH=src python3 examples/module_usage.py
```

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

If `pyssp` is not available on your shell path:

```bash
PYTHONPATH=src python3 -m pyssp_sysml2.cli --help
```

## Outputs

Typical generated structure:

- `build/generated/SystemStructure.ssd`
- `build/generated/parameters.ssv`
- `build/generated/model_descriptions/*/modelDescription.xml`
- `build/synced_sysml/*.sysml` (when running `pyssp sync ssd --output-architecture-dir ...`)
- `build/new_architecture/architecture.sysml` (when bootstrapping from SSD into an empty architecture directory)

Artifact purpose:

- `SystemStructure.ssd`: component/connectors/connections structure for SSP workflows.
- `parameters.ssv`: default parameter values for component attributes.
- `modelDescription.xml`: FMI variable/interface declaration per component.
- `synced_sysml/*.sysml`: SysML files exported after applying SSD wiring updates.

## Common Errors

| Symptom | Likely cause | Fix |
|---|---|---|
| `No module named pycps_sysmlv2` / `No module named pyssp_standard` | Dependencies not installed in current environment | Create/activate venv and run `pip install -r requirements.txt && pip install -e .` |
| `[error] 'Part not found: ...'` | `--composition` does not match a part definition name | Use the correct top-level composition name |
| `[error] No .sysml files found under ...` | Running `generate ...` without SysML files in `--architecture` | Provide SysML inputs first; only `sync ssd` can bootstrap from SSD |
| `[error] ... partial/invalid attribute mapping ...` during `sync ssd` | SSD connection edits do not include full port attribute mapping | Ensure all attributes of connected ports are mapped consistently |
| `[error] ... incompatible ports ...` during `sync ssd` | SSD connects ports of different definitions | Connect only compatible source/destination ports |
| `[error] Nested SSD systems are not supported for SysML sync` | SSD contains subsystems instead of only component elements at sync level | Flatten/adjust SSD structure to component-level elements |
| `pyssp: command not found` | Console script not installed on PATH | Use `PYTHONPATH=src python3 -m pyssp_sysml2.cli ...` or `pip install -e .` |

## Development Docs

Project internals, test/reference behavior, and maintainer workflow are in:

- [`docs/development.md`](/home/eriro/pwa/2_work/pyssp_sysml2/docs/development.md)
