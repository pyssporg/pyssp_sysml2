---
id: INFO-039
type: info
title: Artifact responsibilities
summary: Each emitted artifact names its source of truth and what it contains.
date: 2026-11-05
status: current
---

# Artifact responsibilities

## Sources and contents

- **SSV**: source is the parameter set definition. Contains parameter values,
  flat names, and list indices. A `Real` value is written with the shortest
  representation that round-trips to the authored float, so a full-precision
  value is not rounded.
- **SSM**: source is explicit binds. Contains source-to-target name mappings.
- **SSD**: source is composition, parts, interfaces, binds, and FMU metadata.
  Contains structure, connectors, connections, `ParameterBinding`s, and
  component source/implementation.
- **Analysis descriptor**: source is an `Analysis` composition. Writes
  `analysis.json` and, when a scenario set is applied, an SSV plus one SSM; it
  never writes an SSD or an SSP. A model build records the configuration name in
  the SSP's `extra/org.pyssp/selection.json` (`INFO-043`).
- **SSP archive**: source is SSD plus `fmu_meta.source` plus applied sets.
  Contains packaged structure, FMUs, and SSVs.
- **SysML from SSD**: source is SSD plus referenced SSV/SSM. Contains a
  synthesized model, sets, interfaces, and binds (`INFO-038`).

The FMI model description is `pyfmi_sysml2`'s; it reads the same interface and
never the applied set values (`INFO-031`).
