---
id: INFO-015
type: info
title: Validation of markers, ports, and binds
summary: The loader accepts unresolved models; generators validate markers, the parameters port, flat attributes, and bind shapes.
date: 2026-10-23
status: current
---

# Validation of markers, ports, and binds

The loader accepts a model even when references are unresolved. Validation
happens when a generator needs the model:

- `generate ssv`, `ssd`, `ssm`, and `fmi` validate the parameter dialect and
  applied sets;
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
  flattened; see `IMP-001`.

Valid:

```sysml
port def ParameterInterface;
attribute def ParameterSet;

port def P :> ParameterInterface { attribute x : Real; }
attribute def S :> ParameterSet { attribute x = 1.0; }
```

## Parameter port and mixing

- At most one `parameters` port per part. A duplicate is a model error; rename
  or remove the extra port.
- A part may not declare flat parameter attributes. The diagnostic says
  `... is a flat parameter attribute, which is no longer supported`.
- A composition may not declare flat parameter attributes.
- The composition root is not a parameter target. The diagnostic says
  `Top-level composition parameter interfaces are not supported`.
- A synthesized parameter port cannot reuse a subpart name. The diagnostic says
  `already has a subpart named 'parameters'`.

## Set application and binds

- A bind must name a set usage in the composition.
- A bind target component path must resolve to a component usage.
- The parameter port must be on the left; the rewrite is rejected.
- A bind target must use the `parameters` port.
- A bind must pair a whole set with a whole port, or one member with one
  member.
- A per-member bind source must be `<set>` or `<set>.<member>`.
- A set usage must not mix whole-object and per-member binds.
- A bound component must have an interface.
- Identity bind members must exist in the interface. Otherwise use explicit
  binds.
- A per-member bind must name an existing set member and interface member.
- Binds inside nested part definitions are rejected. Move the bind to the
  composition root.

Invalid identity with renamed members reports:

```text
Whole-object bind of 'nominal' to comp cannot map set members n;
use per-member binds for differently named parameters
```
