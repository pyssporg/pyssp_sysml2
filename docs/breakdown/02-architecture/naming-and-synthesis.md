---
id: INFO-005
type: info
title: Naming and synthesis
summary: Artifact names and synthesized definition names form part of the round-trip contract.
date: 2026-11-05
status: current
---

# Naming and synthesis

## Artifact names and synthesized definitions

These names are synthesized by the tooling and are part of the round-trip
contract.

Artifact file names:

- **SSV**: `<SetDefinitionName>.ssv`.
- **SSM**: `<SetDefinitionName>_<ComponentName>.ssm`.
- **Nested SSM component**: dots become underscores, `outer.inner` to
  `outer_inner`.
- **SSD**: whatever path the user passes, conventionally
  `SystemStructure.ssd`.
- **FMI**: `<PartDefinitionName>/modelDescription.xml`, emitted by
  `pyfmi_sysml2` (`INFO-031`).

Synthesized SysML definitions:

- **Parameter interface**: `<PartDefinitionName>Parameters`, sanitized, with
  `_2` suffix on collision.
- **Parameter set**: SSV `name`, sanitized; fallback based on component or set.
- **Set usage**: set definition name; `parameters_set` if the name is
  `parameters`; numeric suffix on collision.
- **Inferred component or system definitions**: FMU source stem or SSD element
  name, with `_2` suffix on collision.
- **Inferred port definitions**: `Port_1`, `Port_2`, and so on (`INFO-036`).

Collision behavior lives in `parameters/synthesis/` (`_unique_name` in
`generation.py`, `_interface_name` in `interfaces.py`) and `sysml/generate.py`
(`_unique_part_def_name`).

`generate sysml` synthesizes the package name `RecoveredFromSSD`. Use
`--composition` to choose the top-level part definition name. The package name
is not configurable.
