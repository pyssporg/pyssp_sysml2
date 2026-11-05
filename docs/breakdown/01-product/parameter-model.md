---
id: CP-001
type: capability
title: Parameter model
summary: Parameter interfaces, parameter sets, and set usages separate a component surface from reusable values.
date: 2026-11-05
status: current
---

# Parameter model

A simulation component has two parameter concerns:

- **Interface** describes what parameters exist: names, types, fixed lengths,
  optional defaults.
- **Values** describe which values a particular analysis uses: nominal mission,
  aggressive mission, trimmed configuration.

The dialect separates them so a component definition stays stable while
scenarios are added as new sets.

## The three objects

- **Parameter interface** is a `port def X :> ParameterInterface`. It becomes
  SSD parameter connectors; FMI parameter variables read the same interface in
  `pyfmi_sysml2`.
- **Parameter set** is an `attribute def Y :> ParameterSet`. It becomes one
  SSV file named after the set.
- **Set application** is `attribute s : Y;` plus `bind ...` in a composition.
  It becomes one SSD `ParameterBinding`, plus an SSM for explicit mappings.

A set is not a component. It is a value bundle applied to a component usage.

Markers, a complete example, identity and explicit binds, and the accepted
shapes are `CP-008`, `CP-009`, `CP-010`, `CP-011`, and `CP-012`.
