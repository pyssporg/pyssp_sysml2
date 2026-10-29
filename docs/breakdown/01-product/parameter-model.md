---
id: CP-001
type: capability
title: Parameter model
summary: Parameter interfaces, parameter sets, and set usages separate a component surface from reusable values.
date: 2026-10-22
status: current
---

# Parameter model

A simulation component has two parameter concerns:

- **Interface** describes what parameters exist: names, types, fixed lengths,
  optional defaults.
- **Values** describe which values a particular analysis uses: nominal mission,
  aggressive mission, trimmed configuration.

The dialect separates them so a component definition stays stable while
scenarios are added as new sets.

## The three objects

- **Parameter interface** is a `port def X :> ParameterInterface`. It becomes
  SSD parameter connectors and FMI parameter variables.
- **Parameter set** is an `attribute def Y :> ParameterSet`. It becomes one
  SSV file named after the set.
- **Set application** is `attribute s : Y;` plus `bind ...` in a composition.
  It becomes one SSD `ParameterBinding`, plus an SSM for explicit mappings.

A set is not a component. It is a value bundle applied to a component usage.

## Markers

`ParameterInterface` and `ParameterSet` are project markers, not standard SysML
v2 library types. They are empty defs whose meaning comes from this dialect:
a `port def` for the interface marker, an `attribute def` for the set marker.

SysML v2 has no built-in parameter-set construct. `bind` is used here as a
mapping declaration. In SysML itself, `bind` is an equality constraint, not an
assignment or override.

The implementation recognizes only direct marker specialization. It does not
flatten inherited set or interface members; reuse is proposed in `IMP-001`.

## Minimum complete model

```sysml
package ParameterDemo {
  port def ParameterInterface;
  attribute def ParameterSet;

  port def AutopilotParameters :> ParameterInterface {
    attribute waypointCount : Integer;
    attribute waypointX_km : Real[3];
  }

  attribute def NominalSet :> ParameterSet {
    attribute waypointCount = 10;
    attribute waypointX_km = (0.0, 10.0, 20.0);
  }

  part def AutopilotModule {
    in port parameters : AutopilotParameters;
  }

  part def AircraftComposition {
    part autopilot : AutopilotModule;
    attribute nominal : NominalSet;
    bind autopilot.parameters = nominal;
  }
}
```

What each piece means:

- `AutopilotParameters` is the interface of `AutopilotModule`; its members are
  the parameter names the component understands.
- `NominalSet` is a reusable set of values; its member names are SSV parameter
  names.
- `in port parameters : AutopilotParameters;` is the fixed port that connects a
  part definition to its parameter interface.
- `attribute nominal : NominalSet;` declares a set usage in the composition.
- `bind autopilot.parameters = nominal;` applies the set to the component.

Generated artifacts:

- `parameter_sets/NominalSet.ssv` with `waypointCount` and the three
  `waypointX_km[i]` values.
- `SystemStructure.ssd` with component `autopilot`, parameter connectors, and a
  `ParameterBinding` for `NominalSet.ssv` with prefix `autopilot.`.
- `model_descriptions/AutopilotModule/modelDescription.xml` with parameter
  variables.

The FMI model description contains the interface, not the applied set values.
The set is a runtime SSP mapping.
