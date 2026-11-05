---
id: INFO-050
type: info
title: Validation of set application and binds
summary: A bind must pair whole set with whole port or one member with one member, and binds live only at the composition root.
date: 2026-11-05
status: current
---

# Validation of set application and binds

- A bind must name a set usage in the composition.
- A bind target component path must resolve to a component usage.
- The parameter port must be on the left; the rewrite is rejected.
- A bind target must use the `parameters` port.
- A bind must pair a whole set with a whole port, or one member with one
  member.
- A per-member bind source must be `<set>` or `<set>.<member>`.
- A set usage must not mix whole-object and per-member binds.
- A bound component must have an interface.
- Identity bind members must exist in the interface. Otherwise use explicit
  binds.
- A per-member bind must name an existing set member and interface member.
- Binds inside nested part definitions are rejected. Move the bind to the
  composition root.

Invalid identity with renamed members reports:

```text
Whole-object bind of 'nominal' to comp cannot map set members n;
use per-member binds for differently named parameters
```
