---
id: INFO-016
type: info
title: Validation of sets, types, and names
summary: Overlapping targets are rejected; types and multiplicities must match; reserved names and dotted names are rejected.
date: 2026-10-23
status: current
---

# Validation of sets, types, and names

## Multiple sets and disjointness

- No target parameter may be bound twice. The diagnostic is
  `Multiple parameter sets bind 'comp.count': ...`.
- Make target members disjoint or use one set.
- List members are whole-feature targets, so two sets binding different indices
  of one list still overlap.
- Identity and explicit binds count by effective target member.

SysML `bind` is equality, not override. SSP defines precedence for multiple
`ParameterBinding`s, but the dialect deliberately does not invent declaration
order. Disjoint targets are the deterministic choice.

## Types and multiplicity

- Set and interface types must match. A mismatch reports
  `has incompatible types: ... vs ...`.
- Lists must have a fixed length. `[0..*]` reports
  `has unbounded multiplicity '[0..*]'`.
- Set tuple length must match interface multiplicity. A mismatch reports
  `provides N values but ... declares [M]`.
- A list-valued set member needs a list target.
- A scalar set member cannot target a list.
- Indexed mappings must match on both sides, or use indices on neither side.

## Names

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
