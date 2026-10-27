---
id: IMP-002
type: imp
title: Effective set semantics and SSP transfer
summary: An effective member map collects inherited members; application and SSP flatten the result into one SSV.
date: 2026-10-22
status: current
---

# Effective set semantics and SSP transfer

Status: proposed, not implemented.

## Effective member map

For every set definition, compute an effective member map:

1. Recursively collect effective members from all supertypes.
2. Ignore the `ParameterSet` marker itself.
3. Merge members by name.
4. Apply direct attributes:
   - new name adds a member;
   - inherited name with `:>>` overrides;
   - inherited name without `:>>` is an error.
5. If distinct supertypes define the same member and there is no direct
   redefinition, error.
6. A member inherited through a diamond from the same origin counts once.
7. Detect cycles, unknown supertypes, and non-set supertypes.

Rules:

- Every supertype of a parameter set must be a parameter set or the
  `ParameterSet` marker.
- A direct redefinition must have a compatible primitive type and multiplicity.
- A redefinition without a value inherits the base value.
- A redefinition with a value overrides it.
- Values from base sets cannot be removed.
- Direct new members must not collide with inherited names.
- The declared `definition.attributes` remains the direct member set. The
  effective map is a computed view; inherited members are not flattened into the
  definition.

## Set application

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

## SSP transfer

The effective set flattens into one SSV:

```text
AggressiveSet.ssv
  n_waypoints = 20
  waypoints_x_km[0..2] = ...
  max_speed = 15
```

- One applied set definition produces one SSV.
- Member names stay flat.
- No dotted group names.
- No inheritance metadata in SSP.
- Base definitions are not emitted unless they are themselves applied.
- `generate ssd` writes one `ParameterBinding` for the applied set.
- `generate ssm` can map inherited members by their effective names.
- `generate fmi` uses effective interface members if interface inheritance is
  implemented; the applied set remains a runtime mapping.

This is the main advantage over containment: SSP stays deterministic and flat.
