package ParameterDemo {
  part def AircraftComposition {
    doc /* Applies the nominal set to the autopilot component. */
    part autopilot : AutopilotModule;

    attribute nominal : NominalSet;

    bind nominal.n_waypoints = autopilot.parameters.waypointCount;
    bind nominal.waypoints_x_km = autopilot.parameters.waypointX_km;
  }
}
