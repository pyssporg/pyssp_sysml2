---
id: INFO-012
type: info
title: SSP packaging
summary: generate ssp packages the SSD, built FMUs, and applied SSVs into one deterministic archive.
date: 2026-11-05
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

## Archive and rules

- `SystemStructure.ssd` at the root.
- `resources/<PartDefinition>.fmu` for each packaged FMU.
- `resources/parameter_sets/<SetName>.ssv` for applied sets.
- `extra/org.pyssp/selection.json` when the build selects variants; no
  selection means no `extra/` entry.
- A leaf without `fmu_meta.source` is a design placeholder (`INFO-048`).
- A declared `source` must exist unless `--allow-missing-fmus` exports the
  design.
- `source` may be a `.fmu` file or an extracted FMU directory; directories are
  packaged as `.fmu` entries on commit.
- The bundled resource is always `resources/<PartDefinition>.fmu`.
- The SSD `ParameterBinding` source and packaged SSV path share
  `--parameter-set-prefix`, default `resources/parameter_sets`.
- Explicit binds stay as inline `ParameterMapping` entries; separate `.ssm`
  files are not required.
- Relative `source` paths resolve against `--fmu-root`, default the current
  working directory.
- The FMU `modelDescription.xml` is checked against connector names and
  `fmu_meta.implementation`; `--skip-fmu-validation` bypasses the check.
- Archive entries use fixed timestamps, so unchanged inputs produce
  byte-identical `.ssp` files.
- `selection.json` records the composition, the optional configuration name,
  and the mapping sorted by key, with no time-dependent content.

The variable-name check is intentionally strict: an SSD connector absent from
the FMU would make the packaged system fail to instantiate. Modelica FMUs can
flatten record and array names differently from structured SysML port names.
