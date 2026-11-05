---
id: CP-012
type: capability
title: Bind shapes
summary: The accepted bind forms, from identity through nested targets and lists.
date: 2026-11-05
status: current
---

# Bind shapes

- Apply a set by matching names: `bind autopilot.parameters = nominal;` gives a
  `ParameterBinding` plus prefix (`CP-010`).
- Apply one member with a rename:
  `bind autopilot.parameters.count = nominal.n;` gives an inline mapping or
  SSM (`CP-011`).
- Apply to a nested component:
  `bind outer.inner.parameters.k = nominal.k;` targets `outer.inner.k`.
- Apply to a nested system port:
  `bind outer.parameters.gain = nominal.g;` targets `outer.gain` (`CP-013`).
- Apply two disjoint sets: two binds give two SSVs and two bindings
  (`CP-003`).
- Apply a list: `bind comp.parameters.xs = nominal.xs;` gives element-wise
  `xs[i]` mappings (`CP-004`).
- Declare only an interface with no bind: connectors and FMI defaults only
  (`CP-007`).

The grammar is `bind <component-path>.parameters[.<interface-member>] = <set-usage>[.<set-member>]`;
the rejected shapes are `INFO-026`.
