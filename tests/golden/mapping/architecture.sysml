// Golden case: per-member binds with fixed-length list expansion.
// Regenerate with UPDATE_GOLDENS=1; review every changed byte (see README.md).
package MappingGolden {
  port def ParameterInterface;
  attribute def ParameterSet;

  port def AutopilotParameters :> ParameterInterface {
    attribute waypointCount : Integer;
    attribute waypointX_km : Real[2];
  }

  port def Signal {
    attribute value : Real;
  }

  attribute def NominalSet :> ParameterSet {
    attribute n_waypoints = 10;
    attribute waypoints_x_km = (0.0, 10.0);
  }

  part def AutopilotModule {
    in port parameters : AutopilotParameters;
    in port u : Signal;
    out port y : Signal;
  }

  part def MappingComposition {
    attribute nominal : NominalSet;
    part autopilot : AutopilotModule;
    bind autopilot.parameters.waypointCount = nominal.n_waypoints;
    bind autopilot.parameters.waypointX_km = nominal.waypoints_x_km;
  }
}
