---
id: INFO-029
type: info
title: Commitments
summary: The invariants pyssp_sysml2 holds itself to at its borders and in the artifacts it emits.
date: 2026-11-05
status: current
---

# Commitments

- **The artifact is the library boundary.** Cross-project interchange is the
  SSP, SSD, SSV, or SSM artifact. A Python consumer uses only documented public
  functions; parser internals and schema bindings do not cross.
- **The parser is delegated.** This package consumes a loaded `Architecture`
  from `pycps_sysml2` and never imports `sysmlpy`; `sysmlpy` is not a direct
  dependency because `pycps-sysml2` pins `==0.96.4` (`INFO-031`).
- **Standard handling is delegated.** SSP XML objects come from
  `pyssp_standard`, at the SSP border only (`INFO-028`).
- **Generated SysML is deliberately minimal.** Only SSD information with a
  documented SysML representation is emitted. The rest is carried as typed FMU
  metadata or `pyssp_*` control attributes and preserved on regeneration.
- **Round-trip limits are explicit.** Fidelity limits are documented in
  `INFO-041`; they are not to be presented as full round-trip.
- **The code is the source of truth.** When the documented dialect and the
  implementation disagree, the implementation wins and the documentation is
  updated.
