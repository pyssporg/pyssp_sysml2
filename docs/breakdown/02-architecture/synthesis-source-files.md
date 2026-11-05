---
id: INFO-038
type: info
title: Synthesis source files
summary: Generated and synced definitions are written to fixed files, and each fact is either stored in SysML or derived.
date: 2026-11-05
status: current
---

# Synthesis source files

## Files and derived facts

Generated and synced definitions are written to fixed files:

- `generate sysml --ssd ...` writes `architecture.sysml`.
- `sync ssd` writes new components and ports to
  `inferred_external_parts.sysml`.
- `sync ssd` writes new parameter interfaces and sets to
  `parameter_sets.sysml`.
- Existing definitions stay in their original `source_file`.

The exporter (`pycps_sysml2`) groups by `source_file`, so sync preserves an
existing multi-file layout instead of collapsing everything into one file.

What lives in SysML and what is derived:

- **Parameter names and types**: stored in the interface; derived by
  `generate ssd`; FMI variables read them in `pyfmi_sysml2`.
- **Parameter values**: stored in the set; derived by `generate ssv`.
- **SSV file path prefix**: not stored; CLI `--parameter-set-prefix`.
- **Inline versus standalone SSM**: not stored; `generate ssd` inlines explicit
  mappings, `generate ssm` writes a file.
- **FMU resource path**: presence via `fmu_meta.source`, name from part
  definition; derived by `generate ssd` (`INFO-037`).
- **Implementation string**: `fmu_meta.implementation`; derived by
  `generate ssd`.
- **Built FMU location**: `fmu_meta.source`; read by `generate ssp`.
- **Default experiment**: control attributes; derived by `generate ssd`
  (`INFO-004`).
- **FMU model name and GUID**: derived by `pyfmi_sysml2` (`INFO-031`).

Synthesizing the parameter dialect for generated SysML is the one job of
`parameters/synthesis/`, the only `pyssp_standard`-touching dialect helper left
in this package (`INFO-005`).
