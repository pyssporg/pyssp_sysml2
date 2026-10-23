# pyssp_sysml2

Generate SSP, FMI, and SysML artifacts from a SysML v2 architecture or SSD.

**Library boundary:** the interchange is the SSP/FMI artifact (SSP, SSD, SSV,
SSM, FMI XML). The CLI is the public surface for other projects. When a Python
consumer needs this package, it uses documented public functions only; parser
internals and schema bindings do not cross.

## Who This Is For

- `README.md` (this file): package users who want to generate/sync artifacts.
- `docs/development.md`: contributors and maintainers.

## Workflow Overview

Typical workflow:

1. Start from a SysML architecture (`*.sysml`).
2. Generate SSD (`SystemStructure.ssd`) for system wiring.
3. Generate one SSV per parameter set (`pyssp generate ssv`); see “Parameter Sets” below.
4. Generate SSM mapping files for explicit `bind` mappings (`pyssp generate ssm`).
5. Generate FMI `modelDescription.xml` per component.
6. Package the built FMUs, SSD, and SSVs into an `.ssp` archive (`pyssp generate ssp`).
7. Generate a minimal SysML model from SSD when starting from an external SSP model (`pyssp generate sysml`).
8. Optionally edit SSD wiring in an external tool.
9. Sync SSD wiring changes back into an existing SysML composition (`pyssp sync ssd`).

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

This version targets the refactored `pyssp_standard` model API
(`SSD.xml`, `SSV.xml`, `Connector.type_name`). It does not use the older
`common_content_ssc` type objects. Install the refactored
`pyssp_standard` checkout before installing this package.

If you are working in the `ssp_references` workspace and want to use its vendored `pyssp_standard` checkout instead of a package index:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_local.txt
pip install -e .
```

## 2) Generate Artifacts (CLI)

`pyssp` exposes two command families:

```bash
pyssp generate <ssp|ssd|ssv|ssm|study|fmi|sysml> [options]
pyssp sync ssd [options]
```

Common options for architecture-based generators (`ssp`, `ssd`, `ssv`, `ssm`, `fmi`):

- `--architecture`: folder containing `.sysml` files (or a file inside that folder).
- `--composition`: top-level part definition to generate from

### SSD

```bash
pyssp generate ssd \
  --architecture examples/aircraft_subset \
  --composition AircraftComposition \
  --output build/generated/SystemStructure.ssd
```

For parameter-set models the SSD gets parameter connectors plus system-level
`ParameterBinding` entries. Nested SysML part usages become nested
`ssd:System` elements; leaf parts become `ssd:Component` elements. Use
`--parameter-set-prefix` to control the relative SSV path written into the
SSD (default `parameter_sets`):

```bash
pyssp generate ssd \
  --architecture examples/parameter_sets \
  --composition AircraftComposition \
  --output build/generated/SystemStructure.ssd \
  --parameter-set-prefix parameter_sets
```

### SSV

Parameters live in SysML `ParameterSet` definitions, so `generate ssv` writes one
file per set:

```bash
pyssp generate ssv \
  --architecture examples/aircraft_subset \
  --composition AircraftComposition \
  --output-dir build/generated/parameter_sets
```

Options:

- `--set NAME` (repeatable): emit only the named set(s).
- `--all-sets`: emit every set in the architecture, applied or not.
- `--output FILE`: write a single selected set to a specific file.

### SSM

Explicit `bind` mappings produce SSP parameter-mapping files:

```bash
pyssp generate ssm \
  --architecture examples/parameter_sets \
  --composition AircraftComposition \
  --output-dir build/generated/parameter_mappings
```

`generate ssd` inlines the mapping into the SSD `ParameterBinding`, so a
separate `.ssm` file is optional. `generate ssm` remains useful for external
SSM artifacts or inspection.

### Study

A `part def ... :> Study` composes one exportable `part def ... :> SspModel`
through a single part usage, conventionally named `sut`. The study applies zero
or one parameter set and declares one `Experiment` attribute:

```sysml
part def SspModel;
part def Study;

attribute def Experiment {
  attribute startTime : Real;
  attribute stopTime : Real;
  attribute stepSize : Real;
  attribute tolerance : Real;
}

part def test_baseline :> Study {
  attribute experiment_baseline : BaselineExperiment;
  attribute scenario : ScenarioSet;
  part sut : System;
  bind sut.step.parameters.height = scenario.height;
}
```

Generate study artifacts:

```bash
pyssp generate study \
  --architecture examples/study \
  --composition test_baseline \
  --model position_servo \
  --output-dir build/generated/studies/test_baseline
```

The command writes the applied scenario SSV, one `<Study>.ssm` with targets
relative to the exported model root (the `sut.` prefix is stripped), and
`study.json` with the experiment window and scenario paths. With zero applied
sets it writes an experiment-only `study.json` (no SSV, no SSM), for a model
body that stays a checked-in SSP and only authors its experiment window in
SysML. It never writes an SSD or an SSP. `generate ssp` rejects a `:> Study`
composition.

A study over a checked-in SSP body selects that body through `SspMetadata`:

```sysml
attribute def SspMetadata {
  attribute source : String;
}

attribute def LegacySsp :> SspMetadata {
  attribute source = "models/ssp/example/ssp";
}

part def LegacyBody :> SspModel {
  attribute ssp_meta : LegacySsp;
}
```

`source` is a directory with `SystemStructure.ssd` and optional `resources/`,
resolved against the repository root. `study.json` records it as
`model_source`. Such a composition is a study-only boundary; `generate ssp`
and `generate ssd` reject it.

A complete two-study example over one `SspModel` is in
[`examples/study/`](examples/study/README.md).

### Parameter Sets

Parameters can be separated from the component definition into an interface
and reusable value sets. The full methodology, including multiple-set and
nested-path patterns, is in
[`docs/methodology/01-parameter-sets.md`](docs/methodology/01-parameter-sets.md).

```sysml
port def ParameterInterface;
attribute def ParameterSet;

port def AutopilotParameters :> ParameterInterface {
  attribute waypointCount : Integer;
  attribute waypointX_km : Real[3];
}

attribute def NominalSet :> ParameterSet {
  attribute n_waypoints = 10;
  attribute waypoints_x_km = (0.0, 10.0, 20.0);
}

part def AutopilotModule {
  in port parameters : AutopilotParameters;
}

part def AircraftComposition {
  part autopilot : AutopilotModule;

  attribute nominal : NominalSet;

  bind autopilot.parameters.waypointCount = nominal.n_waypoints;
  bind autopilot.parameters.waypointX_km = nominal.waypoints_x_km;
}
```

Mapping to SSP artifacts:

| SysML | SSP |
| --- | --- |
| `port def <X> :> ParameterInterface` | parameter connectors in SSD and parameter variables in `modelDescription.xml` |
| `attribute def <Set> :> ParameterSet` | one `<Set>.ssv` |
| `bind path.parameters.member = set.member` | inline `ssm:MappingEntry source="member" target="path.member"` |
| `bind path.parameters = set` | identity mapping → `ParameterBinding prefix="path."` |
| multiple sets on one component | allowed when target members are disjoint; overlapping targets are rejected |

Rules:

- Mark interfaces with `:> ParameterInterface` (a `port def` marker) and sets
  with `:> ParameterSet` (an `attribute def` marker). The marker definitions
  must exist in the same package.
- A component or nested system has at most one
  `in port parameters : <Interface>;` declaration.
- Write parameter binds with the parameter port on the left:
  `bind path.parameters.member = set.member;`. The reversed form is rejected
  with the rewritten bind in the error message.
- Sets are applied per component or nested-system usage with `bind`. An
  element may have several applied sets as long as no target parameter is
  bound more than once.
  SysML `bind` is an equality constraint, not an override, so overlapping
  targets are rejected instead of imposing an order.
- `path` may be a nested part path, for example
  `bind outer.inner.parameters.k = nominal.k`. Nested parts are emitted as
  nested `ssd:System` elements and use SSP hierarchical target names.
- Apply sets at the composition root. Bindings stored inside a nested part
  definition are rejected; target nested usages from the root instead.
- The composition itself is not a parameter target. Attach parameter
  interfaces to component or nested-system usages; top-level SSD system
  parameter connectors are rejected.
- Set member names are the SSV names; the parameter port on the left determines
  the SSP hierarchical target name.
- Fixed list lengths use declared multiplicity, e.g. `Real[3]`.
- `generate ssd` emits parameter connectors from the interface and inlines
  explicit mappings; `generate fmi` emits interface parameters using interface
  defaults, never applied-set values.
- `generate sysml` synthesizes interfaces, sets, ports, and binds from SSD
  parameter connectors and `ParameterBinding` entries; `sync ssd` reconciles
  them when the SysML model already uses the parameter dialect.
- SSM transformations and unit-conversion suppression are rejected: only
  identity mappings and plain source→target name mapping are supported.
- Parameter names become SysML feature names. Reserved SysML keywords (for
  example `part`, `port`, `attribute`, `typed`) are rejected with a clear
  error instead of producing a model that cannot be parsed.

### FMI model descriptions

```bash
pyssp generate fmi \
  --architecture examples/aircraft_subset \
  --composition AircraftComposition \
  --output-dir build/generated/model_descriptions
```

Parameter-set interfaces produce FMI parameter variables (including fixed
list expansion). `start` values come from the interface declarations only; an
applied SSV/SSM supplies runtime values. Nested leaf components are discovered
recursively and get their own model description.

### FMU metadata

Leaf component definitions can carry typed metadata for the built FMU. The
schema is a normal `attribute def` hierarchy:

```sysml
attribute def FmuMetadata {
  attribute source : String;         // built .fmu file or extracted FMU dir
  attribute implementation : String;
}

attribute def AutopilotFmu :> FmuMetadata {
  attribute source = "build/fmus/AutopilotModule.fmu";
  attribute implementation = "CoSimulation";
}

part def AutopilotModule {
  attribute fmu_meta : AutopilotFmu;
}
```

When the metadata declares `source`, `generate ssd` writes
`Component/@source="resources/<PartDef>.fmu"`; `implementation` becomes
`Component/@implementation`. `source` is authoring/build metadata, is not
written to the SSD, and is consumed by `generate ssp`. A leaf without
`fmu_meta.source` (or without metadata at all) is a design placeholder: its
component is exported with an empty `source`. A declared `implementation` is
still written.

Metadata is only valid on leaf part definitions. Nested systems and the
composition cannot declare it.

### SSP archive

Package the SSD, applied parameter sets, and built FMUs into an SSP archive:

```bash
pyssp generate ssp \
  --architecture examples/aircraft_subset \
  --composition AircraftComposition \
  --output build/generated/AircraftComposition.ssp \
  --fmu-root .
```

`generate ssp` always builds the SSD from SysML. If you edited an SSD in an
external tool, run `sync ssd` first so the architecture reflects those edits.

Each `fmu_meta.source` may be a `.fmu` file or an extracted FMU directory. A
leaf without `fmu_meta.source` needs no flag: it is exported with an empty
`Component/@source`, no resource is packaged, and a warning names it. The
archive is then a design artifact that must be populated (`SSP.attach_fmu`)
before it can run. A *declared* source that does not exist on disk is an error
unless `--allow-missing-fmus` is passed; that path keeps
`resources/<PartDef>.fmu` as the component source without packaging it. The
archive contains:

- `SystemStructure.ssd`
- `resources/<PartDef>.fmu` for each packaged FMU
- `<parameter-set-prefix>/<Set>.ssv` for each applied set
  (default prefix `resources/parameter_sets`)

Explicit parameter mappings are inlined in the SSD, so the archive does not
need separate `.ssm` files. By default the FMU `modelDescription.xml` is
checked against the generated SSD connector names and
`fmu_meta.implementation`. Use `--skip-fmu-validation` if the model
deliberately uses different variable names. Relative `source` paths resolve
against `--fmu-root` (default: current working directory).

### SysML from SSD

Generate a minimal SysML model directly from an SSD:

```bash
pyssp generate sysml \
  --ssd build/generated/SystemStructure.ssd \
  --composition AircraftComposition \
  --output build/generated/architecture.sysml
```

If `--composition` is omitted, the SSD system name is used. When the SSD
contains parameter connectors or `ParameterBinding` entries, the generated
model also gets parameter interfaces, sets, `parameters` ports, and `bind`
statements.

`Component/@implementation` becomes `fmu_meta` metadata when it is set. The
original build path cannot be recovered from an SSD, so the recovered model has
no `source`; add `source` to each leaf's `FmuMetadata` before running
`generate ssp`.

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

`pyssp sync ssd` syncs **composition parts, connection wiring, and the parameter dialect** from SSD back to SysML.

Supported:

- Adding/removing component or nested-system instances through SSD element edits when the source (for components) resolves to a known SysML part definition.
- Adding/removing/changing port-to-port composition connections through SSD connection edits.
- Writing updates in-place or to a separate output architecture directory.
- Reconciling the parameter dialect (interfaces, set values, set usages, and binds) when the SysML architecture already uses interfaces/sets or was bootstrapped from the SSD.
- Recursing through nested SSD systems and nested SysML part usages, including adding/removing nested components and reconciling nested connection wiring.
- Synthesizing part definitions for new SSD components or nested systems that have no matching SysML definition. Component definitions are derived from the FMU source stem; system definitions get ports from their SSD connectors and are populated recursively. Port definitions are reused by signature when possible, and new definitions are written to `inferred_external_parts.sysml`. Pass `--no-synthesize` to disable this and fail on unknown sources instead.

Not supported (command will fail with a validation error):

- Partial attribute mapping for a port connection (for example only `x` but not `y`).
- Attribute remapping between different names (`port.a -> port.b`).
- Connectors that are not expressed in `port.attribute` form.
- Connections between incompatible port definitions.
- Unknown components/ports that do not exist in the SysML composition when `--no-synthesize` is used.
- Flat parameter attributes. The legacy flat-attribute dialect was retired;
  parameters must be declared through a parameter interface and applied with
  SysML-defined sets.
- The retired `pyssp_implementation` and `pyssp_parameter_set` control
  attributes.

Notes for `generate sysml`:

- Generated SysML is intentionally minimal and exported to `architecture.sysml`.
- Part names are derived from SSD component `source` (FMU stem) when available, otherwise from component names.
- Port definitions are inferred from SSD connector attribute signatures.
- Nested `ssd:System` elements become nested part definitions and part usages.
- Parameter connectors become interface members; `ParameterBinding` entries become set definitions, composition set usages, and `bind` statements. Nested systems use hierarchical targets such as `outer.inner.k`.

## 3.5) Round-trip fidelity

`pyssp generate sysml` records SSD metadata that has no first-class SysML
equivalent as typed FMU metadata or `pyssp_*` control attributes. They are
preserved by `pyssp generate ssd` and skipped by the SSV/FMI generators:

| SSD metadata | SysML representation |
| --- | --- |
| `Component/@implementation` | `attribute fmu_meta : <Part>FmuMetadata` with `implementation` |
| Parameter connectors / bindings | `port def` interfaces, sets, `parameters` ports, and `bind` |
| `DefaultExperiment` | `attribute pyssp_default_start_time` / `pyssp_default_stop_time` |
| Flat connector name | `attribute pyssp_flat_connector : Boolean` on the port def |

`Component/@source` is derived from the part definition name
(`resources/<PartDef>.fmu`) when the leaf declares `fmu_meta.source`; with no
source it is exported empty. `generate sysml` and `sync` cannot recover the
build path, so add `fmu_meta.source` before regenerating an SSP from a
recovered model.

Parameter values are read from the bound SSV and written into synthesized set
definitions. A generated architecture therefore shows the effective values
and a regenerated SSD keeps the same interface, set names, and mappings.
SSD parameter connectors carry names and types only; interface *defaults* are
not part of SSD, so a generated interface starts without defaults. Applied
SSV values stay set values and are not promoted to interface defaults.

## 4) Use as a Python Module

```python
from pathlib import Path

from pyssp_sysml2.ssd import generate_ssd
from pyssp_sysml2.ssv import generate_parameter_sets
from pyssp_sysml2.fmi import generate_model_descriptions
from pyssp_sysml2.ssp import generate_ssp
from pyssp_sysml2.sysml import generate_sysml_from_ssd
from pyssp_sysml2.sync import sync_sysml_from_ssd

architecture = Path("examples/aircraft_subset")
composition = "AircraftComposition"

generate_ssd(architecture, Path("build/generated/SystemStructure.ssd"), composition)
generate_parameter_sets(
    architecture, Path("build/generated/parameter_sets"), composition
)
generate_model_descriptions(architecture, Path("build/generated/model_descriptions"), composition)
# Leaves without a built source are exported as design placeholders.
generate_ssp(
    architecture,
    Path("build/generated/AircraftComposition.ssp"),
    composition,
    fmu_root=Path("."),
)
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
    synthesize_external_parts=True,
)
```

## Runnable Examples

From repo root:

```bash
# Ensure dependencies are installed first (see Local development above).
bash examples/cli_usage.sh
PYTHONPATH=src python3 examples/module_usage.py
```

- CLI workflow: [`examples/cli_usage.sh`](examples/cli_usage.sh)
- Python module workflow: [`examples/module_usage.py`](examples/module_usage.py)
- Study / `SspModel` workflow: [`examples/study/README.md`](examples/study/README.md)

## Help / Discovery

```bash
pyssp --help
pyssp generate --help
pyssp generate ssd --help
pyssp generate ssv --help
pyssp generate ssm --help
pyssp generate fmi --help
pyssp generate ssp --help
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
- `build/generated/parameter_sets/*.ssv`
- `build/generated/parameter_mappings/*.ssm` (models with explicit binds)
- `build/generated/model_descriptions/*/modelDescription.xml`
- `build/generated/<Composition>.ssp` (when running `pyssp generate ssp`)
- `build/generated/architecture.sysml` (when running `pyssp generate sysml`)
- `build/synced_sysml/*.sysml` (when running `pyssp sync ssd --output-architecture-dir ...`)

Artifact purpose:

- `SystemStructure.ssd`: component/connectors/connections structure plus parameter bindings for SSP workflows.
- `parameter_sets/*.ssv`: one parameter set, referenced by SSD parameter bindings.
- `parameter_mappings/*.ssm`: optional standalone source→target mapping for explicit binds.
- `modelDescription.xml`: FMI variable/interface declaration per component.
- `<Composition>.ssp`: packaged SSD, FMUs, and applied parameter sets.
- `architecture.sysml`: minimal SysML architecture generated from an SSD.
- `synced_sysml/*.sysml`: SysML files exported after applying SSD wiring updates.

## Common Errors

| Symptom | Likely cause | Fix |
|---|---|---|
| `No module named sysmlpy` / `No module named pyssp_standard` | Dependencies not installed in current environment | Create/activate venv and run `pip install -r requirements.txt && pip install -e .`, or use `pip install -r requirements_local.txt && pip install -e .` when working with the bundled third-party checkouts |
| `[error] 'Part not found: ...'` | `--composition` does not match a part definition name | Use the correct top-level composition name |
| `[error] No .sysml files found under ...` | Running an architecture-based generator without SysML files in `--architecture` | Provide SysML inputs first, or use `pyssp generate sysml --ssd ...` to bootstrap from SSD |
| `[error] ... partial/invalid attribute mapping ...` during `sync ssd` | SSD connection edits do not include full port attribute mapping | Ensure all attributes of connected ports are mapped consistently |
| `[error] Connector '...' is not in 'port.attribute' form` | SSD contains connectors that do not map to a SysML port attribute endpoint | Normalize SSD connectors so sync sees `port.attribute` endpoints |
| `[error] ... incompatible ports ...` during `sync ssd` | SSD connects ports of different definitions | Connect only compatible source/destination ports |
| `[error] Multiple parameter sets bind '...'` | Two sets target the same component parameter | Make the target members disjoint, or use one set |
| `[error] ... is a flat parameter attribute` | A component declares parameters directly | Move the members into a `port def :> ParameterInterface` and apply a `ParameterSet` with `bind` |
| `[error] FMU source for ... does not exist` | Declared `fmu_meta.source` points to a missing file/directory, or `--fmu-root` is wrong | Build the FMU first, fix the path/root, or use `--allow-missing-fmus` |
| `[error] ... is missing variable(s) used by the SSD` | SSD connector names do not match the FMU model description | Rename the SysML ports/parameters or FMU variables, or use `--skip-fmu-validation` |
| `[error] ... exposes '...'` | `fmu_meta.implementation` disagrees with the FMU interface type | Set it to `CoSimulation` or `ModelExchange` to match the FMU |
| `[error] ... pyssp_implementation is no longer supported` | Legacy FMU implementation control attribute | Move `implementation` into `attribute fmu_meta : <Part>FmuMetadata` |
| `[error] ... pyssp_parameter_set is no longer supported` | Legacy external SSV pointer | Define sets in SysML and bind them to component usages |
| `pyssp: command not found` | Console script not installed on PATH | Use `PYTHONPATH=src python3 -m pyssp_sysml2.cli ...` or `pip install -e .` |

## Development Docs

Project internals, test/reference behavior, and maintainer workflow are in:

- [`docs/methodology/README.md`](docs/methodology/README.md) — SysML v2
  simulation-modeling methodology knowledge base, starting with parameter sets
- [`docs/development.md`](docs/development.md)
