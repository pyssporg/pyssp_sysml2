# pyssp_sysml2

Generate SSP, FMI, and SysML artifacts from a SysML v2 architecture or SSD.

## Who This Is For

- `README.md` (this file): package users who want to generate/sync artifacts.
- `docs/development.md`: contributors and maintainers.

## Workflow Overview

Typical workflow:

1. Start from a SysML architecture (`*.sysml`).
2. Generate SSD (`SystemStructure.ssd`) for system wiring.
3. Generate SSV (`parameters.ssv`) for default parameter values.
4. Generate FMI `modelDescription.xml` per component.
5. Generate a minimal SysML model from SSD when starting from an external SSP model (`pyssp generate sysml`).
6. Optionally edit SSD wiring in an external tool.
7. Sync SSD wiring changes back into an existing SysML composition (`pyssp sync ssd`).

If no SysML files are available yet, `pyssp generate sysml` can bootstrap a minimal SysML architecture from an SSD.

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

If you are working from this repository and want to use the bundled third-party checkouts instead of resolving dependencies from package indexes:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_local.txt
pip install -e .
```

## 2) Generate Artifacts (CLI)

`pyssp` exposes two command families:

```bash
pyssp generate <ssd|ssv|fmi|sysml> [options]
pyssp sync ssd [options]
```

Common options for architecture-based generators (`ssd`, `ssv`, `fmi`):

- `--architecture`: folder containing `.sysml` files (or a file inside that folder).
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

### SysML from SSD

Generate a minimal SysML model directly from an SSD:

```bash
pyssp generate sysml \
  --ssd build/generated/SystemStructure.ssd \
  --composition AircraftComposition \
  --output build/generated/architecture.sysml
```

If `--composition` is omitted, the SSD system name is used.

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

### Sync Capabilities and Limits

`pyssp sync ssd` currently syncs **composition parts and connection wiring** from SSD back to SysML.

Supported:

- Adding/removing component instances through SSD component edits when the component `source` resolves to a known SysML part definition.
- Adding/removing/changing port-to-port composition connections through SSD connection edits.
- Writing updates in-place or to a separate output architecture directory.

Not supported (command will fail with a validation error):

- Partial attribute mapping for a port connection (for example only `x` but not `y`).
- Attribute remapping between different names (`port.a -> port.b`).
- Connectors that are not expressed in `port.attribute` form.
- Connections between incompatible port definitions.
- Unknown components/ports that do not exist in the SysML composition.
- Nested SSD systems (only flat SSD systems with components are supported).

Notes for `generate sysml`:

- Generated SysML is intentionally minimal and exported to `architecture.sysml`.
- Part names are derived from SSD component `source` (FMU stem) when available, otherwise from component names.
- Port definitions are inferred from SSD connector attribute signatures.

## 4) Use as a Python Module

```python
from pathlib import Path

from pyssp_sysml2.ssd import generate_ssd
from pyssp_sysml2.ssv import generate_parameter_set
from pyssp_sysml2.fmi import generate_model_descriptions
from pyssp_sysml2.sysml import generate_sysml_from_ssd
from pyssp_sysml2.sync import sync_sysml_from_ssd

architecture = Path("examples/aircraft_subset")
composition = "AircraftComposition"

generate_ssd(architecture, Path("build/generated/SystemStructure.ssd"), composition)
generate_parameter_set(architecture, Path("build/generated/parameters.ssv"), composition)
generate_model_descriptions(architecture, Path("build/generated/model_descriptions"), composition)
generate_sysml_from_ssd(
    Path("build/generated/SystemStructure.ssd"),
    Path("build/generated/architecture.sysml"),
    composition,
)
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
pyssp generate sysml --help
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
- `build/generated/architecture.sysml` (when running `pyssp generate sysml`)
- `build/synced_sysml/*.sysml` (when running `pyssp sync ssd --output-architecture-dir ...`)

Artifact purpose:

- `SystemStructure.ssd`: component/connectors/connections structure for SSP workflows.
- `parameters.ssv`: default parameter values for component attributes.
- `modelDescription.xml`: FMI variable/interface declaration per component.
- `architecture.sysml`: minimal SysML architecture generated from an SSD.
- `synced_sysml/*.sysml`: SysML files exported after applying SSD wiring updates.

## Common Errors

| Symptom | Likely cause | Fix |
|---|---|---|
| `No module named pycps_sysmlv2` / `No module named pyssp_standard` | Dependencies not installed in current environment | Create/activate venv and run `pip install -r requirements.txt && pip install -e .`, or use `pip install -r requirements_local.txt && pip install -e .` when working with the bundled third-party checkouts |
| `[error] 'Part not found: ...'` | `--composition` does not match a part definition name | Use the correct top-level composition name |
| `[error] No .sysml files found under ...` | Running an architecture-based generator without SysML files in `--architecture` | Provide SysML inputs first, or use `pyssp generate sysml --ssd ...` to bootstrap from SSD |
| `[error] ... partial/invalid attribute mapping ...` during `sync ssd` | SSD connection edits do not include full port attribute mapping | Ensure all attributes of connected ports are mapped consistently |
| `[error] Connector '...' is not in 'port.attribute' form` | SSD contains connectors that do not map to a SysML port attribute endpoint | Normalize SSD connectors so sync sees `port.attribute` endpoints |
| `[error] ... incompatible ports ...` during `sync ssd` | SSD connects ports of different definitions | Connect only compatible source/destination ports |
| `[error] Nested SSD systems are not supported for SysML sync` | SSD contains subsystems instead of only component elements at sync level | Flatten/adjust SSD structure to component-level elements |
| `pyssp: command not found` | Console script not installed on PATH | Use `PYTHONPATH=src python3 -m pyssp_sysml2.cli ...` or `pip install -e .` |

## Development Docs

Project internals, test/reference behavior, and maintainer workflow are in:

- [`docs/development.md`](/home/eriro/pwa/2_work/pyssp_sysml2/docs/development.md)
