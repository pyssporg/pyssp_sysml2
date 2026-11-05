---
id: INFO-019
type: info
title: Warnings
summary: Warnings do not stop generation; each names an expected design state or a forgotten step without rejecting the model.
date: 2026-11-05
status: current
---

# Warnings

Warnings do not stop generation.

- `Parameter set 'S' members x are not bound to comp; SSP will ignore them`
  means an explicit-mapping set has valued members outside this application.
  This is expected for partial applications.
- `...: FMU source is missing; ...` means a leaf has no `fmu_meta.source`, or
  its declared source is absent under `--allow-missing-fmus`. Add a source or
  populate the archive with `SSP.attach_fmu`.
- A set declared but never bound is reported with a `UserWarning` naming it.
- A leaf with no source is reported per component at packaging time.

Valid but suspicious, and intentional:

- a component interface with no applied set;
- a set applied explicitly to only a subset of its members;
- extra interface members that no set provides;
- multiple set usages of the same set definition on different components;
- a nested system with its own parameter interface;
- a leaf component with FMU metadata and no parameter interface;
- a nested SSD `System` with no parameter connectors.
