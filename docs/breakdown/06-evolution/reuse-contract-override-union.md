---
id: IMP-012
type: imp
title: Reuse contract forms: override, union, and conflict
summary: Value override uses standard redefinition, multiple inheritance is a union, and a same-member conflict needs explicit redefinition.
date: 2026-11-05
status: proposed
---

# Reuse contract forms: override, union, and conflict

Status: proposed, not implemented.

**Override.** Use standard SysML redefinition:

```sysml
attribute def AggressiveSet :> NominalSet {
  attribute n_waypoints : Integer :>> NominalSet::n_waypoints = 20;
  attribute max_speed = 15.0;
}
```

The short form is also valid:
`attribute n_waypoints :>> NominalSet::n_waypoints = 20;`.

**Union.**

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

**Conflict.**

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

There is no first-base-wins or last-base-wins rule. Explicit redefinition is the
only resolution. Base and additive forms are `IMP-005`.
