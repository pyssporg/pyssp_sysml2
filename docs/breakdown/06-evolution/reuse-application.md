---
id: IMP-007
type: imp
title: Effective sets in application and disjointness
summary: A set usage sees all effective members, and disjointness is checked on effective targets rather than direct attributes.
date: 2026-11-05
status: proposed
---

# Effective sets in application and disjointness

Status: proposed, not implemented.

```sysml
part def Composition {
  part autopilot : AutopilotModule;
  attribute aggressive : AggressiveSet;
  bind autopilot.parameters.waypointCount = aggressive.n_waypoints;
}
```

- A set usage sees all effective members.
- Identity binds match effective member names.
- Explicit binds can target inherited members.
- Multiple sets on one component are checked for disjointness using effective
  members.
- Applying both `NominalSet` and `AggressiveSet` to one component conflicts,
  because `AggressiveSet` inherits all `NominalSet` members.
- The direct-attribute map is `IMP-002`; the SSP result is `IMP-008`.
