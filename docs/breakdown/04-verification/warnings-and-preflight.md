---
id: INFO-019
type: info
title: Warnings and pre-flight checklist
summary: Warnings do not stop generation; the checklist catches dialect mistakes before a generator runs.
date: 2026-10-23
status: current
---

# Warnings and pre-flight checklist

Warnings do not stop generation.

- `Parameter set 'S' members x are not bound to comp; SSP will ignore them`
  means an explicit-mapping set has valued members outside this application.
  This is expected for partial applications.
- `...: FMU source is missing; ...` means a leaf has no `fmu_meta.source`, or
  its declared source is absent under `--allow-missing-fmus`. Add a source or
  populate the archive with `SSP.attach_fmu`.
- The sysmlpy DFA cache warning is harmless and suppressed by the adapter at
  import.

## Valid but suspicious

These are intentional:

- a component interface with no applied set;
- a set applied explicitly to only a subset of its members;
- extra interface members that no set provides;
- multiple set usages of the same set definition on different components;
- a nested system with its own parameter interface;
- a leaf component with FMU metadata and no parameter interface;
- a nested SSD `System` with no parameter connectors.

## Pre-flight checklist

- Markers exist: `ParameterInterface`, `ParameterSet`, and `FmuMetadata` when
  used.
- Every port is typed by a marked interface.
- Every set usage is typed by a marked set.
- No part or composition declares flat parameter attributes.
- FMU metadata is only on leaf components and uses known members.
- Every leaf that must run has an existing `fmu_meta.source`; leaves without one
  export as empty-source design placeholders.
- SSD connector names exist in each FMU's `modelDescription.xml`.
- Retired `pyssp_implementation` and `pyssp_parameter_set` attributes are
  absent.
- The composition has no `parameters` port.
- All binds are at the composition root.
- Every bind target is a declared set usage or member.
- Every bind source names a component parameter port.
- Multiple sets have disjoint effective targets.
- List multiplicities are fixed and lengths match.
- Parameter names avoid `pyssp_` and SysML keywords.
- Nested SSD parameter connectors are flat names.
- Referenced SSV and SSM files sit next to the SSD.
- Sync SSD connectors use `port.attribute` form.
- All files use the same package name and tuple list values.
- Each parameterized part has at most one `parameters` port.
- A part with subparts is intended as a system, not an FMU.
- Connected ports use compatible port definitions.
- If round-tripping, the expected synthesized name changes are known.
