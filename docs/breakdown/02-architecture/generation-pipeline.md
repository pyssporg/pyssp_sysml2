---
id: INFO-006
type: info
title: Generation pipeline
summary: SSV, SSM, SSD, FMI, and SSP are separate outputs with distinct sources of truth.
date: 2026-10-23
status: current
---

# Generation pipeline

The pipeline has two directions:

- A SysML model produces `parameter_sets/*.ssv`, `*.ssm`,
  `SystemStructure.ssd`, and `modelDescription.xml` files.
- An SSD plus its referenced SSV/SSM files produce a SysML model through
  `generate sysml` or `sync ssd`.

SSV, SSM, SSD, and FMI are separate outputs. `generate ssd` does not embed
parameter values; it references an SSV and optionally inlines a mapping.
`generate fmi` does not use applied set values; it uses the interface.

## Artifact responsibilities

- **SSV**: source is the parameter set definition. Contains parameter values,
  flat names, and list indices.
- **SSM**: source is explicit binds. Contains source-to-target name mappings.
- **SSD**: source is composition, parts, interfaces, binds, and FMU metadata.
  Contains structure, connectors, connections, `ParameterBinding`s, and
  component source/implementation.
- **FMI model description**: source is a leaf part definition plus its
  interface. Contains parameters, ports, types, defaults, and model metadata.
- **SSP archive**: source is SSD plus `fmu_meta.source` plus applied sets.
  Contains packaged structure, FMUs, and SSVs.
- **SysML from SSD**: source is SSD plus referenced SSV/SSM. Contains a
  synthesized model, sets, interfaces, and binds.

## Variation selection

- A variation point is unresolved until a caller supplies a selection.
- `generate ssd` and `generate ssp` take `selections`, a mapping from a
  part-usage path inside the composition to a variant name.
- The CLI passes repeatable `--select KEY=VARIANT` values as that mapping.
- Resolution runs on a deep copy of the architecture before generation.
- The selected variant's type replaces the usage type; the usage name and the
  SSD element name stay unchanged.
- An unselected variation point fails generation.

## Practical ordering

1. Generate SSV, SSD, and FMI from SysML.
2. Optionally generate standalone SSM files for inspection.
3. Package built FMUs, SSD, and applied sets as an SSP.
4. Edit the SSD externally, then `sync ssd` to bring structural changes back.
5. Or run `generate sysml` to synthesize a fresh SysML model from the SSD.

`generate sysml` and `sync ssd` need the SSV/SSM files referenced by the SSD.
Keep the parameter directory next to the SSD or preserve relative paths.
