---
id: INFO-017
type: info
title: Validation of FMU metadata and composition
summary: Metadata must be typed, unique, leaf-only, and use known string members; part hierarchies must resolve and stay acyclic.
date: 2026-10-23
status: current
---

# Validation of FMU metadata and composition

## FMU metadata

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

## Composition and nesting

- Part references must resolve. Otherwise the diagnostic reports an unresolved
  part definition.
- Recursive part hierarchies are rejected, for example `Recursive part
  hierarchy at 'a.b' (A)`.
- A system cannot also be an FMU.
- Nested SSD systems are supported recursively.
- Bind targets may use nested part paths.
- A nested system may own an interface.
- Top-level SSD system parameter connectors are rejected.

Invalid recursive parts:

```sysml
part def A { part b : B; }
part def B { part a : A; }
```
