---
id: INFO-053
type: info
title: Validation of composition and nesting
summary: Part references must resolve, recursive hierarchies are rejected, and a nested system may own an interface but not FMU metadata.
date: 2026-11-05
status: current
---

# Validation of composition and nesting

- Part references must resolve. Otherwise the diagnostic reports an unresolved
  part definition.
- Recursive part hierarchies are rejected, for example `Recursive part
  hierarchy at 'a.b' (A)`.
- A system cannot also be an FMU.
- Nested SSD systems are supported recursively.
- Bind targets may use nested part paths.
- A nested system may own an interface.
- Top-level SSD system parameter connectors are rejected.

Invalid recursive parts:

```sysml
part def A { part b : B; }
part def B { part a : A; }
```
