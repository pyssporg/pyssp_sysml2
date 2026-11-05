---
id: IMP-008
type: imp
title: Effective sets flattened into SSP
summary: One applied effective set produces one flat SSV, one SSD ParameterBinding, and no inheritance metadata in SSP.
date: 2026-11-05
status: proposed
---

# Effective sets flattened into SSP

Status: proposed, not implemented.

The effective set flattens into one SSV:

```text
AggressiveSet.ssv
  n_waypoints = 20
  waypoints_x_km[0..2] = ...
  max_speed = 15
```

- One applied set definition produces one SSV.
- Member names stay flat; no dotted group names.
- No inheritance metadata in SSP.
- Base definitions are not emitted unless they are themselves applied.
- `generate ssd` writes one `ParameterBinding` for the applied set.
- `generate ssm` maps inherited members by their effective names.
- SSP stays deterministic and flat, which is the main advantage over
  containment (`IMP-001`).
