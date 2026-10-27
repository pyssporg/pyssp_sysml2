---
id: INFO-004
type: info
title: Control attributes and FMU metadata
summary: pyssp_ attributes carry SSP metadata; typed FmuMetadata definitions carry source and implementation on leaf parts.
date: 2026-10-23
status: current
---

# Control attributes and FMU metadata

Several SSP concepts have no first-class SysML v2 equivalent. Simple metadata is
carried as ordinary `pyssp_*` attributes:

- `pyssp_default_start_time` on the composition maps to SSD
  `DefaultExperiment/@startTime`.
- `pyssp_default_stop_time` on the composition maps to SSD
  `DefaultExperiment/@stopTime`.
- `pyssp_flat_connector` on a port definition emits a scalar connector instead
  of `port.attribute`.

All attributes whose name starts with `pyssp_` are skipped as model data by
parameter, port, and FMI generation. The prefix is reserved.

## Typed FMU metadata

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
component definitions.

- `source` is the build artifact path. It is not written to the SSD;
  `generate ssp` reads it to add the FMU to the archive.
- When a source is declared, `generate ssd` writes
  `Component/@source="resources/<PartDefinition>.fmu"`.
- `implementation` maps to `Component/@implementation`.
- Without a source, the component is exported with an empty `source`.

The retired `pyssp_implementation` and `pyssp_parameter_set` attributes are
rejected with a migration message.

## Default experiment

```sysml
part def Composition {
  attribute pyssp_default_start_time : Real = 0.0;
  attribute pyssp_default_stop_time : Real = 3600.0;
  part comp : Comp;
}
```

This produces `<ssd:DefaultExperiment startTime="0" stopTime="3600" />`.
