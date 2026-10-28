---
id: INFO-012
type: info
title: SSP packaging
summary: generate ssp packages the SSD, built FMUs, and applied SSVs into one deterministic archive.
date: 2026-10-23
status: current
---

# SSP packaging

```bash
pyssp generate ssp \
  --architecture examples/aircraft_subset \
  --composition AircraftComposition \
  --output build/generated/AircraftComposition.ssp \
  --fmu-root .
```

`generate ssp` builds the SSD from SysML, writes applied SSVs, and packages the
built FMUs into one archive. Sync externally edited SSDs back into SysML first.

Archive layout:

- `SystemStructure.ssd` at the root;
- `resources/<PartDefinition>.fmu` for each packaged FMU;
- `resources/parameter_sets/<SetName>.ssv` for applied sets;
- `extra/org.pyssp/selection.json` when the build selects variants.

Rules:

- A leaf without `fmu_meta.source` is a design placeholder: empty component
  `source`, no packaged resource, and a warning. No flag is required.
- A declared `source` must exist unless `--allow-missing-fmus` exports the
  design. The component then keeps `resources/<PartDefinition>.fmu` and nothing
  is packaged.
- `source` may be a `.fmu` file or an extracted FMU directory. Directories are
  packaged as `.fmu` entries on archive commit.
- The bundled resource is always `resources/<PartDefinition>.fmu`.
- The SSD `ParameterBinding` source and packaged SSV path share
  `--parameter-set-prefix`, default `resources/parameter_sets`.
- Explicit binds remain inline `ParameterMapping` entries in the SSD; separate
  `.ssm` files are not required.
- Relative `source` paths resolve against `--fmu-root`, default the current
  working directory.
- The FMU `modelDescription.xml` is checked against generated SSD connector
  names and `fmu_meta.implementation`. `--skip-fmu-validation` bypasses the
  check.
- Archive entries use fixed timestamps, so unchanged inputs produce
  byte-identical `.ssp` files.
- A non-empty selection mapping is recorded at
  `extra/org.pyssp/selection.json`: the composition name and the mapping sorted
  by key, with no time-dependent content.
- A package built without selections carries no `extra/` entry.

The variable-name check is intentionally strict: an SSD connector absent from
the FMU would make the packaged system fail to instantiate. This matters for
Modelica FMUs, whose record and array names can flatten differently from
structured SysML port names.

## Design-first export

A leaf with no `fmu_meta.source`, or no metadata at all, is exported without a
flag. Its SSD component and connectors are written, its `source` is empty, no
resource is packaged, and FMU validation skips it. A warning names each such
component.

A declared source that is not on disk is an error unless `--allow-missing-fmus`
is passed. In that case the component keeps `resources/<PartDefinition>.fmu` as
its source and no resource is packaged. Present FMUs are still packaged and
validated.

The result is a structurally complete design artifact, not a runnable SSP.
Populate it with built binaries:

```python
from pyssp_standard import SSP

with SSP("build/design.ssp", mode="a") as ssp:
    ssp.attach_fmu("source", "build/CsvSource.fmu")
    ssp.validate_fmu_interfaces()
```

`attach_fmu` copies the FMU into `resources/`, points the component's `source`
at it, and checks connector names, connector kinds, and implementation. A
populated archive is an ordinary SSP: it can be simulated, reopened, or
unpacked.
