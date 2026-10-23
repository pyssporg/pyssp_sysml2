# 02 — Implicit Modeling Conventions

> **Status: convention.** These rules are encoded in the implementation even
> where SysML v2 itself is more permissive. They exist so that SysML can be
> mapped to SSP/FMI deterministically.

This chapter collects the conventions that are easy to miss when reading the
generators for the first time. Parameter-set rules are in
[01 — Parameter sets](01-parameter-sets.md); this chapter covers the rest of
the simulation model.

## 1. Files, packages, and model merging

The loader accepts either one `.sysml` file or a directory. Directory loading
is:

- non-recursive;
- only `*.sysml` files are read;
- sorted by file name;
- merged into one architecture;
- expected to use the **same package name** in every file.

```text
architecture/
  composition.sysml
  part_definitions.sysml
  parameter_sets.sysml
```

```sysml
// composition.sysml
package Demo {
  part def Composition {
    part autopilot : AutopilotModule;
  }
}
```

```sysml
// part_definitions.sysml
package Demo {
  part def AutopilotModule {
    in port parameters : AutopilotParameters;
  }
}
```

All three files become one `Demo` model. Definitions keep their
`source_file`, which matters for export and `sync`.

The loader is deliberately **non-validating**:

- unresolved references return `None` from `resolve_part` / `resolve_port`;
- generators raise the context-specific error;
- a model can therefore be loaded even if a generator would reject it later.

## 2. Standard SysML v2 syntax constraints

The adapter delegates parsing to `sysmlpy`, but the repo dialect adds a few
constraints that matter in practice.

### Lists use tuples, not brackets

```sysml
attribute waypointX_km = (0.0, 10.0, 20.0);  // valid
```

```sysml
attribute waypointX_km = [0.0, 10.0, 20.0];  // not SysML v2 syntax
```

### `comment` is a reserved keyword

Do not use `comment` as an attribute name:

```sysml
attribute comment = "nominal";  // invalid
attribute note = "nominal";     // valid
```

### Bind and connect endpoints are feature chains

```sysml
bind autopilot.parameters.waypointCount = nominal.n_waypoints;
connect src.outSig to dst.inSig;
```

The loader preserves the full feature chain for binds. A parameter bind always
puts the parameter port on the left and the set usage on the right
(`bind comp.parameters.k = nominal.k;`); the reversed form is rejected. The
parameter tooling then interprets the chain as described in
[01 — Parameter sets](01-parameter-sets.md).

### One package per architecture

The model adapter currently resolves names inside one package. Imports across
packages are not part of the repository workflow. Put the marker definitions,
interfaces, sets, and parts in the same package.

## 3. Part definitions: FMU components vs nested systems

The SSD distinction is structural:

| SysML shape | SSD shape |
| --- | --- |
| `part def` with **no subparts** | `ssd:Component` with an FMU source |
| `part def` with **subparts** | `ssd:System` |
| part usage name | SSD element name |
| part definition name | FMU source stem for a leaf component |

Example — a leaf component:

```sysml
part def AutopilotModule {
  in port parameters : AutopilotParameters;
}
```

becomes:

```xml
<ssd:Component
    name="autopilot"
    source="resources/AutopilotModule.fmu"
    type="application/x-fmu-sharedlibrary">
  ...
</ssd:Component>
```

Example — a nested system:

```sysml
part def Controller {
  part src : Source;
  part dst : Sink;
}
```

becomes:

```xml
<ssd:System name="controller">
  <ssd:Elements>
    <ssd:Component name="src" ... />
    <ssd:Component name="dst" ... />
  </ssd:Elements>
  ...
</ssd:System>
```

The **usage name** is the SSD element name (`controller`, `src`, `dst`). The
**definition name** determines the default FMU resource stem (`Source.fmu`,
`Sink.fmu`); `fmu_meta.resource_name` can override it. Dots in a definition
name become underscores in the default FMU filename.

### A nested system cannot also be an FMU

This is rejected:

```sysml
part def Controller {
  attribute fmu_meta : ControllerFmu;
  part src : Source;
}
```

A part definition with subparts is a system; a leaf part definition is an FMU.
FMU metadata is only meaningful on a leaf.

### Childless systems

A `part def` with no subparts is a leaf component, even if the SSD originally
had a `System` element with no children. There is no structural marker that
distinguishes an empty system from an FMU leaf in the current dialect. This is
a documented round-trip limitation.

## 4. Ports and connections

### Port definitions

A port is an `attribute def`-like record of variables:

```sysml
port def Signal {
  attribute x : Real;
  attribute y : Real;
}

part def Source {
  out port outSig : Signal;
}

part def Sink {
  in port inSig : Signal;
}
```

SSD connectors use `port.attribute` names:

```text
Source.outSig.x, Source.outSig.y
Sink.inSig.x,   Sink.inSig.y
```

### Scalar connectors

A connector without a dot is a scalar connector:

```text
signal
```

The loader normalizes it to a port with one attribute named `value`:

```sysml
port def Port_1 {
  attribute value : Real;
}
```

The reverse direction uses the presence of the `pyssp_flat_connector`
control attribute:

```sysml
port def ScalarSignal {
  attribute pyssp_flat_connector = true;
  attribute value : Real;
}

part def Source {
  out port signal : ScalarSignal;
}
```

`generate ssd` then emits the connector name `signal` instead of
`signal.value`.

`sync ssd` still requires the SSD connection endpoints to be in
`port.attribute` form. Scalar SSD connections are not syncable.

### Port type compatibility

`generate ssd` and `generate sysml` compare port definitions by identity or
signature. A connection between incompatible port shapes is rejected.

```sysml
part def Composition {
  part src : Source;
  part dst : Sink;
  connect src.outSig to dst.inSig;
}
```

Both endpoints must resolve to the same effective port signature. Inferred
port definitions are shared by signature, so two different port names can use
the same inferred `Port_N` definition.

### Inferred port names are not preserved

`generate sysml` synthesizes port definitions named `Port_1`, `Port_2`, and so
on. The original SysML port names are not recoverable from an SSD. This is a
naming loss, not a semantic loss.

### Scalar single-attribute ports are canonicalized

A port with one attribute is canonicalized to an attribute named `value`.
A source connector `outSig.x` and a destination connector `inSig.y` can
therefore become the same one-attribute port type and round-trip as
`outSig.value` / `inSig.value`.

This is intentional: SSP only gives the attribute names, not the original
SysML port definition names.

### Boundary connections

A connection end without a part names a port of the enclosing part def, i.e.
the system boundary:

```sysml
part def Inner {
  in port u : Signal;
  out port v : Signal;
  part gain : Gain;
  connect u to gain.u;
  connect gain.y to v;
}
```

The SSD omits `startElement`/`endElement` for that end, which is how SSP
means "a connector of the enclosing system":

```xml
<ssd:Connection startConnector="u.x" endElement="gain" endConnector="u.x" />
<ssd:Connection startElement="gain" startConnector="y.x" endConnector="v.x" />
```

Rules:

- a boundary port used at the start of a connection must be declared `in`;
- a boundary port used at the end must be declared `out`;
- a connection between two boundary ports is rejected (it would not cross a
  subpart);
- `generate sysml` and `sync ssd` write the same bare-name form back.


## 5. Control attributes and FMU metadata

Several SSP concepts have no first-class SysML v2 equivalent. Simple metadata
is carried as ordinary `pyssp_*` attributes:

| Control attribute | Where | Meaning |
| --- | --- | --- |
| `pyssp_default_start_time` | composition | SSD `DefaultExperiment/@startTime` |
| `pyssp_default_stop_time` | composition | SSD `DefaultExperiment/@stopTime` |
| `pyssp_flat_connector` | port definition | Emit a scalar connector instead of `port.attribute` |

All attributes whose name starts with `pyssp_` are skipped as model data by
parameter, port, and FMI generation. The prefix is reserved.

Structured FMU metadata uses a typed value definition instead:

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

Metadata is recognized by type, not by the usage name, and is allowed only on
leaf component definitions. `source` is the build artifact path and is not
written to the SSD; `generate ssp` reads it to add the FMU to the archive.
`resource_name` and `implementation` map to `Component/@source` and
`Component/@implementation`.

The retired `pyssp_implementation` and `pyssp_parameter_set` attributes are
rejected with a migration message.

Example:

```sysml
part def Composition {
  attribute pyssp_default_start_time : Real = 0.0;
  attribute pyssp_default_stop_time : Real = 3600.0;
  part comp : Comp;
}
```

```xml
<ssd:DefaultExperiment startTime="0" stopTime="3600" />
```

## 6. Naming conventions

These names are synthesized by the tooling and are part of the round-trip
contract.

### SSP files

| Artifact | Name |
| --- | --- |
| SSV | `<SetDefinitionName>.ssv` |
| SSM | `<SetDefinitionName>_<ComponentName>.ssm` |
| Nested SSM component | dots become underscores: `outer.inner` → `outer_inner` |
| SSD | whatever path the user passes, conventionally `SystemStructure.ssd` |
| FMI | `<PartDefinitionName>/modelDescription.xml` |

### Synthesized SysML definitions

| Definition | Naming rule |
| --- | --- |
| Parameter interface | `<PartDefinitionName>Parameters`, sanitized, with `_2` suffix on collision |
| Parameter set | SSV `name`, sanitized; fallback based on component/set |
| Set usage | Set definition name; `parameters_set` if the name is `parameters`; numeric suffix on collision |
| Inferred component/system definitions | FMU source stem or SSD element name, with `_2` suffix on collision |
| Inferred port definitions | `Port_1`, `Port_2`, ... |

The exact collision behavior is in
`src/pyssp_sysml2/parameter_synthesis.py` (`_unique_name`, `_interface_name`)
and `src/pyssp_sysml2/sysml.py` (`_unique_part_def_name`).

### Source files for synthesized definitions

| Operation | New definitions written to |
| --- | --- |
| `generate sysml --ssd ...` | `architecture.sysml` |
| `sync ssd` — new components/ports | `inferred_external_parts.sysml` |
| `sync ssd` — new parameter interfaces/sets | `parameter_sets.sysml` |
| Existing definitions | Their original `source_file` |

`export_declared()` groups by `source_file`, so `sync` preserves an existing
multi-file layout instead of collapsing everything into one file.

### Package name

`generate sysml` synthesizes the package name `RecoveredFromSSD`. Use
`--composition` to choose the top-level part definition name; the package name
is not currently configurable.

## 7. Top-level composition constraints

The top composition is a structural container, not a parameter target.

Rejected:

```sysml
part def Composition {
  in port parameters : SomeInterface;  // top-level parameter port
  part comp : Comp;
}
```

Rejected when generating SysML:

```xml
<ssd:System name="Composition">
  <ssd:Connectors>
    <ssd:Connector name="gain" kind="parameter">...</ssd:Connector>
  </ssd:Connectors>
</ssd:System>
```

Attach parameter interfaces to component or nested-system usages instead. The
composition may still carry default-experiment control attributes and may have
ports for structural wiring.

## 8. Legacy flat-attribute dialect (retired)

The flat-attribute dialect is retired. A leaf component cannot declare
parameters directly:

```sysml
part def Comp {
  attribute gain : Real = 2.0;  // error
}
```

Use a parameter interface and a set instead:

```sysml
port def Params :> ParameterInterface {
  attribute gain : Real;
}

part def Comp {
  in port parameters : Params;
}
```

`generate ssd`, `generate ssv`, `generate fmi`, and `sync ssd` reject flat
parameter attributes with a migration message. `generate sysml` still converts
an existing SSD `ParameterBinding` into interfaces, sets, and binds.

## 9. What lives in SysML vs what is derived

Many artifacts are derived rather than stored. This is useful when reviewing
a model:

| Information | Stored in SysML? | Derived by |
| --- | --- | --- |
| Parameter names/types | interface | `generate ssd`, `generate fmi` |
| Parameter values | set | `generate ssv` |
| SSV file path prefix | no | CLI `--parameter-set-prefix` |
| Inline vs standalone SSM | no | `generate ssd` inlines explicit mappings; `generate ssm` writes a file |
| FMU resource path | `fmu_meta.resource_name`, else part definition name | `generate ssd` |
| Implementation string | `fmu_meta.implementation` | `generate ssd` |
| Built FMU location | `fmu_meta.source` | `generate ssp` |
| Default experiment | control attributes | `generate ssd` |
| FMU model name | composition + part definition | `generate fmi` |
| FMU GUID | deterministic UUID | `generate fmi` |

## 10. Implicit-knowledge checklist

Use this when adding a new model pattern:

- [ ] Are all files in the same package?
- [ ] Are list values written as tuples?
- [ ] Are marker definitions present (`ParameterInterface`, `ParameterSet`)?
- [ ] Does each parameterized part have at most one `parameters` port?
- [ ] Are all component parameters declared in a parameter interface?
- [ ] Is FMU metadata (`fmu_meta`) only on leaf component definitions?
- [ ] Does every leaf have `fmu_meta.source`, or is the model exported with
      `--allow-missing-fmus` and populated later?
- [ ] Is a part with subparts intended as a system, not an FMU?
- [ ] Does a connection use compatible port definitions?
- [ ] Are parameter binds at the composition root, not inside nested part
      definitions?
- [ ] Is the top composition free of a parameter port?
- [ ] Are names free of `pyssp_` and SysML keywords when they become features?
- [ ] Are all list multiplicities fixed?
- [ ] Are parameter targets disjoint when several sets apply to one component?
- [ ] If round-tripping, which synthesized names are expected to change?

## 11. Source of truth

- `src/pyssp_sysml2/sysml_model/loader.py` — package merge, multiplicity,
  directions, connections, binds;
- `src/pyssp_sysml2/sysml_model/exporter.py` — source-file grouping and text
  layout;
- `src/pyssp_sysml2/sysml.py` — leaf/system split, port inference, nested
  systems;
- `src/pyssp_sysml2/ssd.py` — port/parameter connectors and connections;
- `src/pyssp_sysml2/fmu_metadata.py` — typed FMU metadata resolution;
- `src/pyssp_sysml2/ssp.py` — SSP archive packaging;
- `src/pyssp_sysml2/control.py` — control-attribute names;
- `tests/test_sysml_model.py`, `tests/test_generate_sysml.py`,
  `tests/test_fmu_metadata.py`, `tests/test_generate_ssp.py`,
  `tests/test_roundtrip.py`.
