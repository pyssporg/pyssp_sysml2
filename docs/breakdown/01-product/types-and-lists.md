---
id: CP-004
type: capability
title: Types and lists
summary: Supported primitive parameter types and fixed list multiplicity, with their expansion rules and errors.
date: 2026-11-05
status: current
---

# Types and lists

Supported primitive parameter types are `Real`, `Integer`, `Boolean`, and
`String`.

Parameter lists use declared multiplicity on the interface and a tuple value on
the set:

```sysml
port def AutopilotParameters :> ParameterInterface {
  attribute waypointX_km : Real[3];
}

attribute def NominalSet :> ParameterSet {
  attribute waypoints_x_km = (0.0, 10.0, 20.0);
}

bind autopilot.parameters.waypointX_km = nominal.waypoints_x_km;
```

Consequences:

- SSD and FMI names expand to `waypointX_km[0]`, `[1]`, `[2]`.
- The SSV writes `waypoints_x_km[0]`, `[1]`, `[2]`.
- The SSM and mapping expand both sides element-wise.
- Tuple length must match interface multiplicity.
- Only fixed lengths are supported. `Real[0..*]` fails with:
  `Parameter 'waypointX_km' has unbounded multiplicity '[0..*]'; SSP
  parameters need a fixed length`.
- A tuple of the wrong length fails with:
  `'waypoints_x_km' provides 2 values but 'waypointX_km' declares [3]`.

Lists of scalars are supported. Lists of sets or nested parameter groups are
not part of the dialect (`CP-015`).

Set member type and interface member type must be compatible. A mismatch fails
with `Parameter mapping 'n_waypoints' -> 'waypointCount' has incompatible
types: Real vs Integer`.

Explicit type annotations on set members are allowed. Without a declared type,
the type is inferred from the value. A member with neither value nor declared
type provides no value and is not written to the SSV; do not bind it
explicitly.
