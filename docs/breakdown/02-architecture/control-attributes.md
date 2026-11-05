---
id: INFO-004
type: info
title: Control attributes
summary: pyssp_ attributes carry SSP metadata and are read through pycps_sysml2's ControlAttributes object.
date: 2026-11-05
status: current
---

# Control attributes

Several SSP concepts have no first-class SysML v2 equivalent. Simple metadata is
carried as ordinary `pyssp_*` attributes, read through `pycps_sysml2`'s
prefix-configurable `ControlAttributes` object (`INFO-031`):

- `pyssp_default_start_time` on the composition maps to SSD
  `DefaultExperiment/@startTime`.
- `pyssp_default_stop_time` on the composition maps to SSD
  `DefaultExperiment/@stopTime`.
- `pyssp_flat_connector` on a port definition emits a scalar connector instead
  of `port.attribute`; the value `false` means not flattened.

All attributes whose name starts with `pyssp_` are skipped as model data by
parameter, port, and FMI generation. The prefix is reserved.

```sysml
part def Composition {
  attribute pyssp_default_start_time : Real = 0.0;
  attribute pyssp_default_stop_time : Real = 3600.0;
  part comp : Comp;
}
```

This produces `<ssd:DefaultExperiment startTime="0" stopTime="3600" />`.

The retired `pyssp_implementation` and `pyssp_parameter_set` attributes are
rejected with a migration message (`INFO-024`). Typed FMU metadata is
`INFO-037`.
