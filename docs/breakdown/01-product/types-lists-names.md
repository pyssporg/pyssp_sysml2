---
id: CP-004
type: capability
title: Types, lists, and names
summary: Supported primitive types, fixed list multiplicity, the reserved parameters port, and naming limits.
date: 2026-10-22
status: current
---

# Types, lists, and names

## Lists and fixed multiplicity

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
not part of the dialect.

## Types and compatibility

Supported primitive parameter types are `Real`, `Integer`, `Boolean`, and
`String`.

Set member type and interface member type must be compatible. A mismatch fails
with `Parameter mapping 'n_waypoints' -> 'waypointCount' has incompatible
types: Real vs Integer`.

Explicit type annotations on set members are allowed. Without a declared type,
the type is inferred from the value. A member with neither value nor declared
type provides no value and is not written to the SSV; do not bind it
explicitly.

## Naming rules

- The parameter port is named `parameters`. Only this name is recognized. A
  part definition may have at most one such port.
- A `parameters` port on the composition root is rejected. Attach interfaces to
  component or nested-system usages.
- `pyssp_` names are control attributes. Generators skip them as parameter
  data. Do not use the prefix for parameters.
- SysML keywords are rejected as parameter names: `part`, `port`, `attribute`,
  `bind`, `typed`, `comment`. They would produce a file that cannot be parsed
  back.
- A set usage name is local to the composition and need not match the set
  definition name. It is the left side of the bind.
- Synthesized set usage names derive from the SSV or set name. A collision
  appends a numeric suffix. A set named `parameters` becomes `parameters_set`.

## Not supported

- A parameter set inside a parameter set: SSP has a flat parameter list.
- Set inheritance or union: proposed only in `IMP-001`.
- Parameter groups inside an interface: interface members are flat.
- A top-level composition parameter interface: the composition is not a
  parameter target.
- Top-level SSD system parameter connectors: not represented by the dialect.
- Bindings inside a nested part definition: apply sets at the composition root.
- Unbounded multiplicity: SSP parameters need a fixed length.
- SSM transformations or unit conversion: only identity and plain
  source-to-target mapping are generated.
- Multiple `parameters` ports: the port name is fixed and unique per part.
- Dotted parameter names: not representable as SysML feature names.
