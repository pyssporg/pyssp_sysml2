---
id: INFO-001
type: info
title: Intent
summary: Why pyssp_sysml2 exists, what it commits to, and what it refuses to become.
date: 2026-10-23
status: current
---

# Intent

## Purpose

`pyssp_sysml2` turns a SysML v2 architecture model into the standard artifacts a
simulation workflow consumes, and turns those artifacts back into SysML. It owns
SysML-to-SSP/FMI generation and the SSD-to-SysML sync; it does not run or judge
simulations.

It covers two directions:

- SysML architecture or SSD to SSD, one SSV per parameter set, SSM parameter
  mappings, FMI model descriptions, and a packaged SSP.
- SSD wiring edits to a sync back into an existing SysML composition, or a
  minimal SysML architecture bootstrapped from an SSD.

## Scope

Belongs here:

- SysML v2 model adapter and generators.
- SSD, SSV, SSM, FMI XML, and SSP generation.
- SSD to SysML synthesis and `sync ssd`.
- the `pyssp` CLI as the public surface.

Belongs elsewhere:

- SSP/FMI XML object model: `pyssp_standard`.
- engine execution and result normalisation: `pyssp_simulate`.
- measurement and judgment: `pyssp_vv`.
- workflow composition and scheduling: `pyssp_workflow`.

## Commitments

- **The artifact is the library boundary.** Cross-project interchange is the
  SSP, SSD, SSV, SSM, or FMI XML artifact. A Python consumer uses only
  documented public functions; parser internals and schema bindings do not
  cross.
- **The parser sits behind an adapter.** Only `model/parser.py` imports
  `sysmlpy`, and only `model/variation.py` walks the raw parse tree it returns.
  Generators work against the repo-owned dataclasses in `model/model.py`, and
  `model/exporter.py` emits the SysML text contract independently of the
  parser's serializer.
- **Standard handling is delegated.** SSP/FMI XML objects come from
  `pyssp_standard`; this package does not reimplement them.
- **Generated SysML is deliberately minimal.** Only SSD information with a
  documented SysML representation is emitted. The rest is carried as typed FMU
  metadata or `pyssp_*` control attributes and preserved on regeneration.
- **Round-trip limits are explicit.** Fidelity limits are documented in
  `INFO-007`; they are not to be presented as full round-trip.
- **The code is the source of truth for the methodology.** When the documented
  dialect and the implementation disagree, the implementation wins and the
  documentation is updated.

## Non-goals

- Simulation runtime and engine adapters.
- Measurement, acceptance criteria, or verdicts.
- A general SysML v2 toolchain: the generators cover the documented
  simulation-modeling dialect, not all of SysML v2.
- A full SSP authoring environment; SSP editing belongs to `pyssp_standard`.

## Roles of the ecosystem

- **`pyssp_sysml2`** generates SysML to SSP/FMI artifacts and syncs SSD to
  SysML.
- **`pyssp_standard`** handles SSP/FMI XML objects; consumed by this package.
- **`pyssp_simulate`** runs engines and normalises results; consumes the
  generated SSP.
- **`pyssp_vv`** measures, judges, and records evidence; judges the simulated
  result.
- **`pyssp_workflow`** builds, runs, compares, and verifies; composes the
  steps.
