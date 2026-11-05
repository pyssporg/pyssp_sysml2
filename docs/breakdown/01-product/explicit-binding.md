---
id: CP-011
type: capability
title: Explicit binding
summary: Per-member binds rename each member and become an inline SSD mapping or a standalone SSM.
date: 2026-11-05
status: current
---

# Explicit binding

Explicit binds are one bind per set member:

```sysml
bind autopilot.parameters.waypointCount = nominal.n_waypoints;
bind autopilot.parameters.waypointX_km = nominal.waypoints_x_km;
```

This produces an SSV with the set names, an SSD `ParameterMapping` with the
renames, and optionally a standalone SSM. The standalone file is named
`<SetName>_<ComponentName>.ssm`; the inline SSD mapping is the default.

An explicit bind may cover a subset of the set. Unapplied valued members produce
a warning: `Parameter set 'NominalSet' members reserve_km are not bound to
autopilot; SSP will ignore them`. This is a warning, not an error.

An explicit bind is a rename, not a fallback for an identity bind (`CP-010`);
the mapping direction is `CP-002`.
