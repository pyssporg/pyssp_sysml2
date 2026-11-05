---
id: INFO-037
type: info
title: FMU metadata
summary: Typed FmuMetadata definitions name the built FMU; pyssp_sysml2 passes source and implementation through without interpreting FMI.
date: 2026-11-05
status: current
---

# FMU metadata

## Typed metadata

Structured FMU metadata uses a typed value definition:

```sysml
attribute def FmuMetadata {
  attribute source : String;
  attribute implementation : String;
}

attribute def AutopilotFmu :> FmuMetadata {
  attribute source = "build/fmus/AutopilotModule.fmu";
  attribute implementation = "CoSimulation";
}

part def AutopilotModule {
  attribute fmu_meta : AutopilotFmu;
}
```

Metadata is recognized by type, not by usage name, and is allowed only on leaf
component definitions (`INFO-002`). `pycps_sysml2` supplies `FmuMetadata` and
its accessors; this package never interprets FMI semantics — it passes both
fields through to the SSD and the archive.

- `source` is the build artifact path. It is not written to the SSD;
  `generate ssp` reads it to add the FMU to the archive.
- When a source is declared, `generate ssd` writes
  `Component/@source="resources/<PartDefinition>.fmu"`.
- `implementation` maps to `Component/@implementation`.
- Without a source, the component is exported with an empty `source`.

FMI generation itself is `pyfmi_sysml2`'s (`INFO-031`).
