---
id: INFO-017
type: info
title: Validation of FMU metadata
summary: FMU metadata must be typed, unique, leaf-only, and use only the known source and implementation string members.
date: 2026-11-05
status: current
---

# Validation of FMU metadata

- A metadata usage must be typed by a def marked `:> FmuMetadata`.
- The marker definition `FmuMetadata` must exist.
- At most one metadata attribute per part.
- Metadata is allowed only on leaf parts. A part with subparts and `fmu_meta`
  reports `has both subparts and 'fmu_meta' metadata`.
- Only known members are allowed: `source` and `implementation`.
- Member values must be strings.
- `pyssp_implementation` is retired; move it into `fmu_meta`.
- `pyssp_parameter_set` is retired; define a set in SysML and bind it.

Invalid metadata on a nested system:

```text
Controller.fmu_meta is FMU metadata, but the part has subparts;
a nested system cannot also be an FMU component
```
