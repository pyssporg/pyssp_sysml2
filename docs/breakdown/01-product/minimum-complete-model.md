---
id: CP-009
type: capability
title: Minimum complete model
summary: A complete interface, set, usage, and bind, with the artifacts it produces.
date: 2026-11-05
status: current
---

# Minimum complete model

A complete parameter model declares the two marker defs, an interface, a set, a
component that owns the interface, and a composition that applies the set:

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

Generated here: `parameter_sets/NominalSet.ssv` with `waypointCount` and the
three `waypointX_km[i]` values, and `SystemStructure.ssd` with component
`autopilot`, parameter connectors, and a `ParameterBinding` for
`NominalSet.ssv` with prefix `autopilot.`. The FMI model description is
`pyfmi_sysml2`'s; it carries the interface, never the applied set values, which
stay a runtime SSP mapping (`INFO-031`).
