---
id: CP-014
type: capability
title: Naming rules
summary: Which declared, port, and synthesized names the dialect accepts.
date: 2026-11-05
status: current
---

# Naming rules

- A declared name is either a simple SysML identifier or a single-quoted name.
  A quoted name may contain dots, brackets, spaces, and leading digits. The
  model stores the name without its quotes; generators write it verbatim into
  SSD and SSV artifacts, `pyfmi_sysml2` writes it into FMI artifacts, and the
  SysML exporter re-quotes it (`INFO-005`).
- An SSD connector name is `port.attribute` for a grouped port and the port name
  alone for a flat port. A flat port named `'consumerFeed.X[1]'` produces the
  connector `consumerFeed.X[1]`, so an FMU variable that is not a SysML
  identifier can be one flat port.
- A fixed port multiplicity expands to indexed connectors and connections:
  `port 'feed.X' : RealSignal[3]` produces `feed.X[1]`, `feed.X[2]`, and
  `feed.X[3]`. Signal indices are 1-based to match FMI array variable names;
  parameter list indices stay 0-based (`CP-004`).
- A quoted parameter name maps to the same name in the SSV and to
  `<Component>.<name>` as its SSP target. For example,
  `bind sut.ECS_HW.parameters.'pipeA.L' = scenario.'pipeA.L';` maps `pipeA.L`
  to `ECS_HW.pipeA.L`.
- The parameter port is named `parameters`. Only this name is recognized. A
  part definition may have at most one such port.
- A `parameters` port on the composition root is rejected. Attach interfaces to
  component or nested-system usages (`INFO-002`).
- `pyssp_` names are control attributes. Generators skip them as parameter
  data. Do not use the prefix for parameters (`INFO-004`).
- SysML keywords are rejected as parameter names: `part`, `port`, `attribute`,
  `bind`, `typed`, `comment`. They would produce a file that cannot be parsed
  back.
- A set usage name is local to the composition and need not match the set
  definition name. It is the left side of the bind.
- Synthesized set usage names derive from the SSV or set name. A collision
  appends a numeric suffix. A set named `parameters` becomes `parameters_set`
  (`INFO-005`).
