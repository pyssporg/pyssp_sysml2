---
id: CP-015
type: capability
title: Unsupported parameter shapes
summary: Parameter forms the dialect rejects or does not implement.
date: 2026-11-05
status: current
---

# Unsupported parameter shapes

- A parameter set inside a parameter set: SSP has a flat parameter list.
- Set inheritance or union: proposed only in `IMP-001`.
- Parameter groups inside an interface: interface members are flat.
- A top-level composition parameter interface: the composition is not a
  parameter target.
- Top-level SSD system parameter connectors: not represented by the dialect.
- Bindings inside a nested part definition: apply sets at the composition root.
- Unbounded multiplicity: SSP parameters need a fixed length (`CP-004`).
- SSM transformations or unit conversion: only identity and plain
  source-to-target mapping are generated.
- Multiple `parameters` ports: the port name is fixed and unique per part.
- Reserved SysML keywords as synthesized parameter names: a name recovered from
  an SSV is rejected when it is a keyword (`CP-014`).
- Flat parameter attributes: retired in favour of an interface and a bound set
  (`INFO-024`).
