---
id: INFO-015
type: info
title: Validation of markers and roles
summary: The loader accepts unresolved models; generators validate markers, roles, and the parameters port before writing an artifact.
date: 2026-11-05
status: current
---

# Validation of markers and roles

The loader accepts a model even when references are unresolved. Validation
happens when a generator needs the model:

- `generate ssv`, `ssd`, and `ssm` validate the parameter dialect and applied
  sets;
- `generate sysml` validates SSD parameter shapes, names, and mappings;
- `sync ssd` validates composition edits and reconciles the parameter dialect
  when present.

The first error usually identifies the rejecting layer.

## Markers and roles

- Marker definitions must exist in the package; otherwise the generator reports
  missing marker definitions. Fix: add `port def ParameterInterface;` and
  `attribute def ParameterSet;`.
- A parameter port must be typed by a marked interface; otherwise the port type
  is not marked `:> ParameterInterface`.
- A set usage must be typed by a marked set; otherwise the type is not marked
  `:> ParameterSet`.
- A set and an interface are different roles. Do not use one as the other.
- Inheritance is not transitive. A set that only specializes another set is
  rejected unless it directly lists `:> ParameterSet`. Inherited members are not
  flattened; reuse is proposed in `IMP-001`.

Valid:

```sysml
port def ParameterInterface;
attribute def ParameterSet;

port def P :> ParameterInterface { attribute x : Real; }
attribute def S :> ParameterSet { attribute x = 1.0; }
```
