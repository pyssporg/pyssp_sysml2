---
id: IMP-005
type: imp
title: Reuse contract forms
summary: Base sets, additive reuse, value override by redefinition, multiple inheritance as union, and explicit conflict resolution.
date: 2026-10-22
status: current
---

# Reuse contract forms

Status: proposed, not implemented.
## Proposed contract

### Base set

A base set is a normal parameter set with values.

```sysml
attribute def NominalSet :> ParameterSet {
  attribute n_waypoints = 10;
  attribute waypoints_x_km = (0.0, 10.0, 20.0);
}
```

### Additive reuse

```sysml
attribute def AggressiveSet :> NominalSet {
  attribute max_speed = 15.0;
}
```

`AggressiveSet` effectively contains all `NominalSet` members plus
`max_speed`.

### Value override

Use standard SysML redefinition:

```sysml
attribute def AggressiveSet :> NominalSet {
  attribute n_waypoints : Integer :>> NominalSet::n_waypoints = 20;
  attribute max_speed = 15.0;
}
```

The short form is also valid:

```sysml
attribute n_waypoints :>> NominalSet::n_waypoints = 20;
```

### Multiple inheritance as union

```sysml
attribute def SensorSet :> ParameterSet {
  attribute range = 100.0;
}

attribute def CombinedSet :> AggressiveSet, SensorSet {
  attribute extra_margin = 2.0;
}
```

`ParameterSet` need not be repeated; the derived set is a parameter set
transitively through both bases.

### Conflict

```sysml
attribute def A :> ParameterSet { attribute gain = 1.0; }
attribute def B :> ParameterSet { attribute gain = 2.0; }

attribute def C :> A, B;  // invalid unless C redefines gain
```

`C` must resolve the conflict explicitly:

```sysml
attribute def C :> A, B {
  attribute gain : Real :>> A::gain, B::gain = 3.0;
}
```

There is no first-base-wins or last-base-wins rule. Explicit redefinition is
the only resolution.
