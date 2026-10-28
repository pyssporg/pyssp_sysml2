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
- `generate ssd`, `generate ssp`, and `generate study` take `selections`, a
  mapping from a part- or attribute-usage path inside the composition to a
  variant name.
- The CLI passes repeatable `--select KEY=VARIANT` values as that mapping.
- Resolution runs on a deep copy of the architecture before generation.
- A variant with a type replaces the usage type; the usage name and the SSD
  element name stay unchanged.
- A variant with a body (`variant part directPath { part gain : Gain; connect u
  to gain.u; }`) is a selection step of its own: resolution synthesizes an
  anonymous `PartDefinition` from the body, carrying the variation point's
  ports, registers it under `<Point>__<variant>`, and retypes the usage to it.
  Generation then emits a subsystem for that usage, with the body's subparts
  and connections; because the definition has subparts, the usage is no longer
  a leaf.
- Body connections that touch a parameter-interface port are kept on the
  captured body but are not emitted as SSD connections; parameters are applied
  with binds and mappings, not with `connect`.
- For attribute variation, the selected type becomes the parameter set
  definition, so parameter binds and the emitted SSV use its values.
- Attribute usages on a study that composes the generated model are selectable
  from the model's selection.
- An unselected variation point fails generation.
- A body that declares bindings is rejected: binding statements inside variants
  are out of scope.

## Practical ordering

1. Generate SSV, SSD, and FMI from SysML.
2. Optionally generate standalone SSM files for inspection.
3. Package built FMUs, SSD, and applied sets as an SSP.
4. Edit the SSD externally, then `sync ssd` to bring structural changes back.
5. Or run `generate sysml` to synthesize a fresh SysML model from the SSD.

`generate sysml` and `sync ssd` need the SSV/SSM files referenced by the SSD.
Keep the parameter directory next to the SSD or preserve relative paths.
