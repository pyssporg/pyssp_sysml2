---
id: INFO-056
type: info
title: Pre-flight checklist
summary: The checklist catches dialect and packaging mistakes before a generator runs.
date: 2026-11-05
status: current
---

# Pre-flight checklist

- Markers exist: `ParameterInterface`, `ParameterSet`, and `FmuMetadata` when
  used.
- Every port is typed by a marked interface.
- Every set usage is typed by a marked set.
- No part or composition declares flat parameter attributes.
- FMU metadata is only on leaf components and uses known members.
- Every leaf that must run has an existing `fmu_meta.source`; leaves without
  one export as empty-source design placeholders.
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
