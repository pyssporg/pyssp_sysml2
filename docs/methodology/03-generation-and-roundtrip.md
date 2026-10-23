# 03 — Generation and Round-trip

> **Status: implemented.** This chapter describes what the generators actually
> do. The SysML dialect rules themselves are in
> [01 — Parameter sets](01-parameter-sets.md) and
> [02 — Implicit conventions](02-implicit-conventions.md).

## 1. Pipeline overview

```text
                 +-------------------+
                 | SysML v2 model    |
                 +---------+---------+
                           |
        +------------------+------------------+
        |                  |                  |
        v                  v                  v
  parameter_sets/*.ssv  *.ssm            SystemStructure.ssd
        |                  |                  |
        +------------------+------------------+
                           |
                           v
                  modelDescriptions/*.xml

  SystemStructure.ssd + SSV/SSM files
                           |
                           v
                 generate sysml / sync ssd
                           |
                           v
                    SysML v2 model
```

The key point: **SSV/SSM/SSD/FMI are separate outputs**. `generate ssd` does
not embed parameter values; it references an SSV and optionally inlines a
mapping. `generate fmi` does not use applied set values; it uses the interface.

## 2. Artifact responsibilities

| Artifact | Source of truth | Contains |
| --- | --- | --- |
| SSV | parameter set definition | Parameter values, flat names, list indices |
| SSM | explicit binds | Source→target name mapping |
| SSD | composition + parts + interfaces + binds + FMU metadata | Structure, connectors, connections, `ParameterBinding`s, component source/implementation |
| FMI model description | leaf part definition + interface | Parameters, ports, types, defaults, model metadata |
| SSP archive | SSD + `fmu_meta.source` + applied sets | Packaged structure, FMUs, SSVs |
| SysML from SSD | SSD + referenced SSV/SSM | Synthesized model, sets, interfaces, binds |

## 3. SSV generation

Command:

```bash
pyssp generate ssv \
  --architecture examples/parameter_sets \
  --composition AircraftComposition \
  --output-dir build/generated/parameter_sets
```

Default behavior:

- one `.ssv` per **applied** parameter set;
- file name `<SetDefinitionName>.ssv`;
- only members with values are written;
- list members are expanded to `name[0]`, `name[1]`, ...
- interface defaults are **not** copied into the SSV.

Selection options:

```bash
# one named set (repeatable)
pyssp generate ssv ... --set NominalSet

# every set definition in the architecture, applied or not
pyssp generate ssv ... --all-sets

# exactly one set to one explicit file
pyssp generate ssv ... --set NominalSet --output build/nominal.ssv
```

`--output` rejects a selection that resolves to more than one set.

Example:

```sysml
attribute def NominalSet :> ParameterSet {
  attribute n_waypoints = 10;
  attribute waypoints_x_km = (0.0, 10.0, 20.0);
}
```

```xml
<!-- abridged -->
<ssv:ParameterSet version="1.0" name="NominalSet">
  <ssv:Parameters>
    <ssv:Parameter name="n_waypoints">
      <ssv:Integer value="10" />
    </ssv:Parameter>
    <ssv:Parameter name="waypoints_x_km[0]">
      <ssv:Real value="0.0" />
    </ssv:Parameter>
    <ssv:Parameter name="waypoints_x_km[1]">
      <ssv:Real value="10.0" />
    </ssv:Parameter>
    <ssv:Parameter name="waypoints_x_km[2]">
      <ssv:Real value="20.0" />
    </ssv:Parameter>
  </ssv:Parameters>
</ssv:ParameterSet>
```

If the applied set has no values, `write_parameter_set` raises instead of
writing an empty file. An interface-only model produces no SSV.

## 4. SSM generation

Command:

```bash
pyssp generate ssm \
  --architecture examples/parameter_sets \
  --composition AircraftComposition \
  --output-dir build/generated/parameter_mappings
```

Behavior:

- one `.ssm` per explicit `(set, component)` application;
- identity binds are skipped (they use an SSD prefix instead);
- file name `<SetName>_<ComponentName>.ssm`;
- nested component paths have dots replaced by underscores:
  `outer.inner` → `outer_inner.ssm`.

Example explicit bind:

```sysml
bind autopilot.parameters.waypointCount = nominal.n_waypoints;
bind autopilot.parameters.waypointX_km = nominal.waypoints_x_km;
```

```xml
<!-- abridged -->
<ssm:ParameterMapping version="1.0">
  <ssm:MappingEntry source="n_waypoints" target="autopilot.waypointCount" />
  <ssm:MappingEntry source="waypoints_x_km[0]" target="autopilot.waypointX_km[0]" />
  <ssm:MappingEntry source="waypoints_x_km[1]" target="autopilot.waypointX_km[1]" />
  <ssm:MappingEntry source="waypoints_x_km[2]" target="autopilot.waypointX_km[2]" />
</ssm:ParameterMapping>
```

`generate ssd` writes the same mapping inline by default, so a standalone SSM
is optional. Use `generate ssm` for external consumers or inspection.

## 5. SSD generation

Command:

```bash
pyssp generate ssd \
  --architecture examples/parameter_sets \
  --composition AircraftComposition \
  --output build/generated/SystemStructure.ssd
```

### Structure

- A leaf part definition becomes an `ssd:Component`.
- A part definition with subparts becomes a nested `ssd:System`.
- The part **usage name** becomes the SSD element name.
- The part **definition name** determines the default `resources/<Definition>.fmu`
  for a leaf component.
- `fmu_meta.resource_name` overrides the FMU resource name.
- `fmu_meta.implementation` sets `Component/@implementation`.
- Connections are written per system level.

### FMU metadata

```sysml
attribute def FmuMetadata {
  attribute source : String;
  attribute resource_name : String;
  attribute implementation : String;
}

attribute def AutopilotFmu :> FmuMetadata {
  attribute source = "build/fmus/AutopilotModule.fmu";
  attribute resource_name = "AutopilotModule.fmu";
  attribute implementation = "CoSimulation";
}

part def AutopilotModule {
  attribute fmu_meta : AutopilotFmu;
}
```

`generate ssd` writes `source="resources/<resource_name>"` and
`implementation="<implementation>"`. `source` is authoring/build metadata and
is not written to the SSD. Metadata on a nested system is rejected.

### Parameter connectors

Parameter connectors come from the interface:

```sysml
port def AutopilotParameters :> ParameterInterface {
  attribute waypointCount : Integer;
  attribute waypointX_km : Real[3];
}
```

```xml
<!-- abridged -->
<ssd:Connector name="waypointCount" kind="parameter">
  <ssc:Integer />
</ssd:Connector>
<ssd:Connector name="waypointX_km[0]" kind="parameter">
  <ssc:Real />
</ssd:Connector>
...
```

### Parameter bindings

Identity bind:

```sysml
bind autopilot.parameters = nominal;
```

```xml
<ssd:ParameterBinding
    source="parameter_sets/NominalSet.ssv"
    prefix="autopilot." />
```

Explicit bind:

```xml
<ssd:ParameterBinding source="parameter_sets/NominalSet.ssv">
  <ssd:ParameterMapping>
    <ssm:ParameterMapping version="1.0">
      <ssm:MappingEntry source="n_waypoints" target="autopilot.waypointCount" />
    </ssm:ParameterMapping>
  </ssd:ParameterMapping>
</ssd:ParameterBinding>
```

The source path prefix is controlled by `--parameter-set-prefix`
(default `parameter_sets`).

### Multiple sets and nested paths

Multiple disjoint sets produce multiple `ParameterBinding` entries at the top
system level:

```xml
<ssd:ParameterBinding source="parameter_sets/Counts.ssv">...</ssd:ParameterBinding>
<ssd:ParameterBinding source="parameter_sets/Gains.ssv">...</ssd:ParameterBinding>
```

Nested targets use hierarchical names:

```xml
<ssm:MappingEntry source="k" target="outer.inner.k" />
```

The binding is still written at the top system level, not inside `outer`.

### Default experiment

```sysml
part def Composition {
  attribute pyssp_default_start_time : Real = 0.0;
  attribute pyssp_default_stop_time : Real = 3600.0;
}
```

```xml
<ssd:DefaultExperiment startTime="0" stopTime="3600" />
```

### Top-level restrictions

`generate ssd` rejects a parameter interface on the top composition:

```text
Top-level composition parameter interfaces are not supported;
attach parameter interfaces to component usages
```

## 6. FMI model descriptions

Command:

```bash
pyssp generate fmi \
  --architecture examples/parameter_sets \
  --composition AircraftComposition \
  --output-dir build/generated/model_descriptions
```

Behavior:

- only **leaf** part definitions get a model description;
- nested leaf components are discovered recursively;
- definitions are deduplicated by part definition name;
- output is `<PartDefinitionName>/modelDescription.xml`;
- `modelName` is `<CompositionName>.<PartDefinitionName>`;
- `CoSimulation/@modelIdentifier` is the part definition name;
- parameters are emitted before port variables;
- parameter `start` values come from the **interface**, not from an applied
  set;
- `variableNamingConvention` is `structured`;
- GUIDs are deterministic for a given composition/part name;
- a generation timestamp is included, so byte-for-byte comparisons need to
  ignore it.

Example:

```sysml
port def AutopilotParameters :> ParameterInterface {
  attribute waypointCount : Integer = 10;
  attribute waypointX_km : Real[3];
}
```

```xml
<!-- abridged -->
<ScalarVariable name="waypointCount" causality="parameter"
                variability="fixed" valueReference="0">
  <Integer start="10" />
</ScalarVariable>
<ScalarVariable name="waypointX_km[0]" causality="parameter"
                variability="fixed" valueReference="1">
  <Real />
</ScalarVariable>
```

A set value such as `n_waypoints = 25` does **not** become an FMI start value.
It is applied later through the SSD/SSV binding.

If a system part definition also has an interface, it does not get an FMI
model description because it has subparts and is not a leaf FMU. Its interface
can still become SSD system connectors and be a parameter target.

## 6.5 SSP packaging

Command:

```bash
pyssp generate ssp \
  --architecture examples/aircraft_subset \
  --composition AircraftComposition \
  --output build/generated/AircraftComposition.ssp \
  --fmu-root .
```

`generate ssp` builds the SSD from SysML, writes applied SSVs, and packages the
built FMUs into one archive. Sync externally edited SSDs back into SysML first.

```text
AircraftComposition.ssp
├── SystemStructure.ssd
└── resources/
    ├── AutopilotModule.fmu
    ├── Environment.fmu
    ├── MissionComputer.fmu
    └── parameter_sets/
        └── NominalSet.ssv
```

Rules:

- Every leaf component must have `fmu_meta.source`, unless
  `--allow-missing-fmus` exports a design whose FMUs are not built yet.
- `source` may be a `.fmu` file or an extracted FMU directory. Directories are
  packaged as `.fmu` entries on archive commit.
- `resource_name` determines the bundled `resources/<name>`; the default is
  `<PartDefinition>.fmu`.
- The SSD `ParameterBinding` source and packaged SSV path share
  `--parameter-set-prefix` (default `resources/parameter_sets`).
- Explicit binds remain inline `ParameterMapping` entries in the SSD; separate
  `.ssm` files are not required.
- Relative `source` paths resolve against `--fmu-root` (default: current
  working directory).
- The FMU `modelDescription.xml` is checked against the generated SSD
  connector names and `fmu_meta.implementation`. `--skip-fmu-validation`
  bypasses the check.
- Archive entries use fixed timestamps, so unchanged inputs produce
  byte-identical `.ssp` files.

The variable-name check is intentionally strict: an SSD connector that does
not exist in the FMU would make the packaged system fail to instantiate. This
is especially relevant for Modelica FMUs, whose record/array names can be
flattened differently from the structured SysML port names.

### Design-first export

A design often exists before the FMUs do. `--allow-missing-fmus` exports that
design as an SSP:

```bash
pyssp generate ssp \
  --architecture architecture \
  --composition System \
  --output build/design.ssp \
  --allow-missing-fmus
```

A leaf whose `fmu_meta` is missing, has no `source`, or points at a path that
does not exist is *pending*: its SSD component and connectors are written, its
`source` is `resources/<resource_name>` (default `<PartDefinition>.fmu`), no
resource is packaged, and FMU validation skips it. Present FMUs are still
packaged and validated, and a warning names each pending component.

The result is a structurally complete design artifact, not a runnable SSP.
Populate it with the built binaries and check the result:

```python
from pyssp_standard import SSP

with SSP("build/design.ssp", mode="a") as ssp:
    ssp.attach_fmu("source", "build/CsvSource.fmu")
    ssp.validate_fmu_interfaces()
```

`attach_fmu` copies the FMU into `resources/`, points the component's
`source` at it, and checks connector names, connector kinds, and the
implementation by default. Once populated, the archive is an ordinary SSP: it
can be simulated, reopened, or unpacked to use the FMUs individually.

## 7. SysML from SSD

Command:

```bash
pyssp generate sysml \
  --ssd build/generated/SystemStructure.ssd \
  --output build/generated/architecture.sysml
```

### Inputs

`generate sysml` reads the SSD and resolves referenced parameter sources
relative to the SSD:

- `ParameterBinding/@source` → SSV;
- inline `ParameterMapping` or `ParameterMapping/@source` → inline or external
  SSM.

If a referenced SSV/SSM is missing, generation fails with an error such as:

```text
Parameter set source not found: parameter_sets/NominalSet.ssv
```

### Output

The generated model:

- uses package `RecoveredFromSSD`;
- uses the SSD system name as the composition name unless `--composition`
  overrides it;
- synthesizes marker definitions if they are missing;
- synthesizes parameter interfaces from `kind="parameter"` connectors;
- synthesizes parameter sets from SSV names and values;
- synthesizes `parameters` ports and `bind` statements;
- recursively synthesizes nested systems, parts, ports, and connections;
- emits `fmu_meta` for non-default source/implementation values, but cannot
  recover the original `source` path;
- writes everything to `architecture.sysml` by default.

Add `fmu_meta.source` to each leaf before running `generate ssp` on a
bootstrapped model.

Example identity synthesis:

```sysml
port def GainParameters :> ParameterInterface {
  attribute k : Real;
}

attribute def parameters :> ParameterSet {
  attribute k : Real = 3.0;
}

part def Gain {
  in port parameters : GainParameters;
}

part def ParamDemo {
  attribute parameters_set : parameters;
  part gain : Gain;
  bind gain.parameters = parameters_set;
}
```

Set name `parameters` is special: the set usage becomes `parameters_set` to
avoid the reserved port name.

Explicit mapping synthesis:

```sysml
bind comp.parameters.count = Nom.n;
bind comp.parameters.xs = Nom.x;
```

List entries `x[0]`, `x[1]` in an SSV/SSM are grouped back into a list member
with multiplicity, and the bind addresses the whole list feature.

### Nested systems

An SSD `System` becomes a nested part definition and usage:

```sysml
part def outer {
  part inner : Inner;
}
```

The target of a nested binding is expressed as:

```sysml
bind outer.inner.parameters.k = Nom.k;
```

### Component-level and system-level bindings

The synthesis accepts bindings at the top system and inside nested systems.
Nested owner paths are made absolute before matching components. A
component-level binding is treated as relative to that component.

### Rejections during synthesis

- Top-level SSD system parameter connectors are rejected.
- Reserved SysML keywords in parameter names are rejected.
- Parameter connectors that cannot be represented as flat SysML feature names
  (for example, dotted names) are rejected.
- A parameter interface/port is not created for the top composition.
- Flat parameter attributes are rejected; parameters must use an interface.

## 8. Sync

Command:

```bash
pyssp sync ssd \
  --architecture build/generated \
  --ssd build/generated/SystemStructure.ssd \
  --composition AircraftComposition \
  --output build/synced
```

Sync applies SSD composition edits back to SysML.

### If the architecture exists

- The existing model is loaded.
- If it already uses the parameter dialect, the dialect is reconciled.
- Parts and connections are recursively reconciled at every nested system
  level.
- Components can be added, removed, or retyped from their `source`.
- New component definitions and port definitions are synthesized into
  `inferred_external_parts.sysml`.
- New parameter interfaces/sets are synthesized into `parameter_sets.sysml`.
- Existing definitions stay in their original `source_file`, so multi-file
  layouts are preserved.
- Unrelated definitions are preserved.

### If the architecture is missing

Sync bootstraps a model from the SSD using the same logic as
`generate sysml`. It writes `architecture.sysml`.

### Parameter reconciliation

If the existing model uses interfaces/sets, sync:

- removes old top-level set usages and parameter binds;
- rebuilds them from SSD/SSV/SSM;
- reuses an existing set definition by name during sync;
- reuses/merges synthesized set definitions by signature when building a fresh
  model;
- updates set values;
- preserves interface defaults and docs when the signature is unchanged;
- removes a port when the SSD no longer has parameter connectors.

Flat-attribute architectures are rejected: components must declare parameters
through a parameter interface and SysML-defined sets.

### Limits

- SSD connection endpoints must be in `port.attribute` form.
- Partial attribute mappings on a connection are rejected.
- Incompatible connected ports are rejected.
- Unknown component sources are synthesized by default; use
  `--no-synthesize` to fail instead.
- A childless SSD `System` can regenerate as a leaf component.
- Set inheritance/union is not implemented.
- Flat parameter attributes are retired.
- `pyssp_implementation` and `pyssp_parameter_set` are retired.

## 9. Round-trip fidelity

### Preserved or semantically preserved

| Item | Notes |
| --- | --- |
| Parameter member names | Except reserved/invalid names, which are rejected |
| Parameter values | SSV is the source of truth for set values |
| Parameter types | Primitive types and fixed multiplicities |
| Interface defaults | Preserved when sync reconciles an unchanged signature |
| Identity/explicit binding intent | Identity → prefix; explicit → mapping |
| Nested system structure | Nested SSD `System` ↔ nested part definition/usage |
| Connections | Per system level, including connections to the enclosing system's ports (bare-name ends) |
| FMU metadata | `fmu_meta` resource name and implementation |
| Control metadata | Default experiment |
| Unrelated definitions and file layout | `sync` preserves them; `generate sysml` starts fresh |

### Renamed or normalized

| Item | Normalization |
| --- | --- |
| Port definition names | Synthesized as `Port_N` |
| Single-attribute port attribute | Canonicalized to `value` |
| Scalar connector name | `signal` ↔ `signal.value` representation |
| Parameter interface name | `<PartDefinition>Parameters` on synthesis |
| Set usage name | Derived from set name; `parameters` → `parameters_set`; collision suffix |
| Composition name | SSD system name, unless `--composition` overrides |
| Package name | `RecoveredFromSSD` for `generate sysml` |
| SSM file name | `<Set>_<Component>.ssm`, dots → underscores |

### Lost or not reconstructible

| Item | Why |
| --- | --- |
| Original port definition names | SSD only stores connector names |
| Set inheritance/union | Not implemented; see proposal |
| Original multi-file layout in `generate sysml` | It writes one synthesized file |
| Distinction between an empty SSD `System` and a leaf component | No structural marker |
| Built FMU path (`fmu_meta.source`) | SSD only stores the packaged resource name |
| Exact source formatting/docs | Synthesis produces a repo-owned model |

## 10. Practical ordering

A typical workflow:

```bash
# 1. Generate values and structure from SysML
pyssp generate ssv --architecture arch --composition Composition \
  --output-dir build/parameter_sets
pyssp generate ssd --architecture arch --composition Composition \
  --output build/SystemStructure.ssd
pyssp generate fmi --architecture arch --composition Composition \
  --output-dir build/model_descriptions

# 2. Optional: inspect standalone mappings
pyssp generate ssm --architecture arch --composition Composition \
  --output-dir build/parameter_mappings

# 3. Package the built FMUs, SSD, and applied sets as an SSP
pyssp generate ssp --architecture arch --composition Composition \
  --output build/Composition.ssp --fmu-root .

# 4. Edit the SSD externally, then bring structural changes back
pyssp sync ssd --architecture arch --ssd build/SystemStructure.ssd \
  --composition Composition --output build/synced

# 5. Or synthesize a fresh SysML model from the SSD
pyssp generate sysml --ssd build/SystemStructure.ssd \
  --output build/recovered.sysml
```

`generate sysml` and `sync ssd` need the SSV/SSM files referenced by the SSD.
Keep the parameter directory next to the SSD or preserve the relative paths.

## 11. Source of truth

- `src/pyssp_sysml2/ssv.py`
- `src/pyssp_sysml2/ssm.py`
- `src/pyssp_sysml2/ssd.py`
- `src/pyssp_sysml2/fmi.py`
- `src/pyssp_sysml2/ssp.py`
- `src/pyssp_sysml2/fmu_metadata.py`
- `src/pyssp_sysml2/sysml.py`
- `src/pyssp_sysml2/parameter_synthesis.py`
- `src/pyssp_sysml2/sync.py`
- `tests/test_parameter_sets.py`
- `tests/test_fmu_metadata.py`
- `tests/test_generate_ssp.py`
- `tests/test_generate_sysml.py`
- `tests/test_roundtrip.py`
- `tests/test_sync.py`
