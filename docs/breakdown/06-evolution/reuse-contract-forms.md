---
id: IMP-005
type: imp
title: Reuse contract forms: base and additive
summary: A base set is a normal valued set, and a derived set adds members by specializing it.
date: 2026-11-05
status: proposed
---

# Reuse contract forms: base and additive

Status: proposed, not implemented.

## Base and additive sets

A base set is a normal parameter set with values.

```sysml
attribute def NominalSet :> ParameterSet {
  attribute n_waypoints = 10;
  attribute waypoints_x_km = (0.0, 10.0, 20.0);
}
```

Additive reuse specializes the base and adds members.

```sysml
attribute def AggressiveSet :> NominalSet {
  attribute max_speed = 15.0;
}
```

`AggressiveSet` effectively contains all `NominalSet` members plus
`max_speed`.

- Specialization is definition-time reuse; the effective set is computed, then
  flattened for SSP (`IMP-002`).
- Override, multiple inheritance, and conflict forms are `IMP-012`.
- A set inside a set stays rejected (`IMP-001`).
