---
id: CP-010
type: capability
title: Identity binding
summary: A whole-set bind matches member names and becomes an SSP ParameterBinding with a prefix and no SSM.
date: 2026-11-05
status: current
---

# Identity binding

An identity bind applies a whole set by matching member names:

```sysml
bind autopilot.parameters = nominal;
```

Rules:

- Every valued set member must exist in the interface with the same primitive
  type and multiplicity.
- Interface members the set does not provide are ignored by this application.
- A valued set member absent from the interface is an error, never a silent
  skip.
- Lists expand element-wise in the SSP mapping.
- SSP represents an identity bind as a `ParameterBinding` with a prefix and no
  SSM. The prefix means prepend `autopilot.` to every SSV name.

Identity also works with a nested component path: `bind outer.inner.parameters
= nominal;` produces prefix `outer.inner.` (`CP-013`).

Identity is not a fallback for renamed members. Use explicit binds instead
(`CP-011`).
