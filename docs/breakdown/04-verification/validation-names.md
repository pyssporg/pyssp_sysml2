---
id: INFO-052
type: info
title: Validation of names
summary: pyssp_ and SysML keywords are rejected, parameter names must be flat, and generated set names must stay unique.
date: 2026-11-05
status: current
---

# Validation of names

- `pyssp_` is reserved. The diagnostic says `uses the reserved 'pyssp_'
  prefix`.
- SysML keywords are rejected. The diagnostic says `uses reserved SysML keyword
  'part'`.
- SSD parameter names must be flat. A dotted name reports `Parameter connector
  '...' cannot be represented as a SysML attribute name`.
- Generated set names must not collide; synthesis appends `_2`.
- `parameters` is reserved for the port. A set usage may be renamed to
  `parameters_set`.
- Nested component paths are allowed in targets, for example
  `outer.inner.parameters.k`.
- Dotted parameter names are not allowed.
