---
id: INFO-016
type: info
title: Validation of sets and disjointness
summary: No target parameter may be bound twice; multiple targets must be disjoint because SysML bind is equality, not override.
date: 2026-11-05
status: current
---

# Validation of sets and disjointness

- No target parameter may be bound twice. The diagnostic is
  `Multiple parameter sets bind 'comp.count': ...`.
- Make target members disjoint or use one set.
- List members are whole-feature targets, so two sets binding different indices
  of one list still overlap.
- Identity and explicit binds count by effective target member.

SysML `bind` is equality, not override. SSP defines precedence for multiple
`ParameterBinding`s, but the dialect deliberately does not invent declaration
order. Disjoint targets are the deterministic choice.
