---
id: INFO-005
type: info
title: Naming and synthesized definitions
summary: Artifact names and synthesized definition names form part of the round-trip contract.
date: 2026-10-23
status: current
---

# Naming and synthesized definitions

These names are synthesized by the tooling and are part of the round-trip
contract.

## Artifact names

- **SSV**: `<SetDefinitionName>.ssv`.
- **SSM**: `<SetDefinitionName>_<ComponentName>.ssm`.
- **Nested SSM component**: dots become underscores, `outer.inner` to
  `outer_inner`.
- **SSD**: whatever path the user passes, conventionally
  `SystemStructure.ssd`.
- **FMI**: `<PartDefinitionName>/modelDescription.xml`.

## Synthesized SysML definitions

- **Parameter interface**: `<PartDefinitionName>Parameters`, sanitized, with
  `_2` suffix on collision.
- **Parameter set**: SSV `name`, sanitized; fallback based on component or set.
- **Set usage**: set definition name; `parameters_set` if the name is
  `parameters`; numeric suffix on collision.
- **Inferred component or system definitions**: FMU source stem or SSD element
  name, with `_2` suffix on collision.
- **Inferred port definitions**: `Port_1`, `Port_2`, and so on.

Collision behavior lives in `parameters/synthesis.py` (`_unique_name`,
`_interface_name`) and `sysml/generate.py` (`_unique_part_def_name`).

## Source files for synthesized definitions

- `generate sysml --ssd ...` writes `architecture.sysml`.
- `sync ssd` writes new components and ports to
  `inferred_external_parts.sysml`.
- `sync ssd` writes new parameter interfaces and sets to
  `parameter_sets.sysml`.
- Existing definitions stay in their original `source_file`.

`export_declared()` groups by `source_file`, so sync preserves an existing
multi-file layout instead of collapsing everything into one file.

## Package name

`generate sysml` synthesizes the package name `RecoveredFromSSD`. Use
`--composition` to choose the top-level part definition name. The package name
is not configurable.

## What lives in SysML and what is derived

- **Parameter names and types**: stored in the interface; derived by
  `generate ssd` and `generate fmi`.
- **Parameter values**: stored in the set; derived by `generate ssv`.
- **SSV file path prefix**: not stored; CLI `--parameter-set-prefix`.
- **Inline versus standalone SSM**: not stored; `generate ssd` inlines explicit
  mappings, `generate ssm` writes a file.
- **FMU resource path**: presence via `fmu_meta.source`, name from part
  definition; derived by `generate ssd`.
- **Implementation string**: `fmu_meta.implementation`; derived by
  `generate ssd`.
- **Built FMU location**: `fmu_meta.source`; read by `generate ssp`.
- **Default experiment**: control attributes; derived by `generate ssd`.
- **FMU model name**: composition plus part definition; derived by
  `generate fmi`.
- **FMU GUID**: deterministic UUID; derived by `generate fmi`.
