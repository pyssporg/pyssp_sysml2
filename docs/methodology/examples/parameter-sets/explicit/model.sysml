package ExplicitExample {
  doc /* Explicit binds rename study-side set members to interface members. */

  attribute def ParameterInterface;
  attribute def ParameterSet;

  attribute def AutopilotParameters :> ParameterInterface {
    attribute waypointCount : Integer;
    attribute waypointX_km : Real[3];
  }

  attribute def NominalSet :> ParameterSet {
    attribute n_waypoints = 10;
    attribute waypoints_x_km = (0.0, 10.0, 20.0);
  }

  part def AutopilotModule {
    attribute parameters : AutopilotParameters;
  }

  part def ExplicitComposition {
    part autopilot : AutopilotModule;
    attribute nominal : NominalSet;

    bind autopilot.parameters.waypointCount = nominal.n_waypoints;
    bind autopilot.parameters.waypointX_km = nominal.waypoints_x_km;
  }
}
