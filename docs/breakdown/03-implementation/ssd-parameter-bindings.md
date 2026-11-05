---
id: INFO-046
type: info
title: SSD parameter bindings
summary: Identity binds become prefixed ParameterBindings, explicit binds inline an SSM mapping, all at the top system level.
date: 2026-11-05
status: current
---

# SSD parameter bindings

- An identity bind `bind autopilot.parameters = nominal;` becomes a
  `ParameterBinding` with `source="parameter_sets/NominalSet.ssv"` and
  `prefix="autopilot."`.
- An explicit bind becomes a `ParameterBinding` with an inline
  `ssm:ParameterMapping` and `MappingEntry` rows.
- `--parameter-set-prefix` controls the source path prefix; the default is
  `parameter_sets`.
- Multiple disjoint sets produce multiple `ParameterBinding` entries at the top
  system level.
- Nested targets use hierarchical names such as `target="outer.inner.k"`. The
  binding still sits at the top system level, not inside `outer`.
- Identity and explicit binds count by effective target member, so overlapping
  targets are rejected (`INFO-016`).
