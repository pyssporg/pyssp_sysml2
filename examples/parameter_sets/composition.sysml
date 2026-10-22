package ParameterDemo {
  part def AircraftComposition {
    doc /* Applies the nominal set to the autopilot component. */
    part autopilot : AutopilotModule;

    attribute nominal : NominalSet;

    bind autopilot.parameters.waypointCount = nominal.n_waypoints;
    bind autopilot.parameters.waypointX_km = nominal.waypoints_x_km;
  }
}
