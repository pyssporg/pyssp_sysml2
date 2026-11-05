---
id: CP-008
type: capability
title: Parameter dialect markers
summary: ParameterInterface and ParameterSet are project markers, not SysML v2 library types, and bind is a mapping declaration.
date: 2026-11-05
status: current
---

# Parameter dialect markers

`ParameterInterface` and `ParameterSet` are project markers, not standard SysML
v2 library types. They are empty defs whose meaning comes from this dialect:
a `port def` for the interface marker, an `attribute def` for the set marker.

SysML v2 has no built-in parameter-set construct. `bind` is used here as a
mapping declaration. In SysML itself, `bind` is an equality constraint, not an
assignment or override.

The implementation recognizes only direct marker specialization. It does not
flatten inherited set or interface members; reuse is proposed in `IMP-001`.

The markers are `pycps_sysml2`'s; this package consumes them (`INFO-031`) and
emits the artifacts (`CP-001`).
