---
id: CP-007
type: capability
title: Interface-only models
summary: A component can declare a parameter interface without applying a set; generators emit connectors and defaults only.
date: 2026-10-22
status: current
---

# Interface-only models

A component can declare an interface without applying a set:

```sysml
port def Params :> ParameterInterface {
  attribute count : Integer = 10;
}

part def Comp {
  in port parameters : Params;
}

part def Composition {
  part comp : Comp;
}
```

Consequences:

- `generate ssd` emits parameter connectors but no `ParameterBinding`.
- `generate fmi` emits parameter variables, using interface defaults as FMI
  `start` values where declared.
- `generate ssv` writes nothing because no set is applied.

This supports components parameterized externally or later in the workflow.
