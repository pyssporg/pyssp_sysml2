package ParameterDemo {
  port def ParameterInterface;
  attribute def ParameterSet;

  port def AutopilotParameters :> ParameterInterface {
    doc /* Parameters exposed by the autopilot FMU. */
    attribute waypointCount : Integer;
    attribute waypointX_km : Real[3];
  }

  attribute def NominalSet :> ParameterSet {
    doc /* Nominal mission-planning parameter set, in study-side names. */
    attribute n_waypoints = 10;
    attribute waypoints_x_km = (0.0, 10.0, 20.0);
  }

  attribute def AggressiveSet :> ParameterSet {
    doc /* Aggressive waypoint spacing for a different mission profile. */
    attribute n_waypoints = 25;
    attribute waypoints_x_km = (0.0, 20.0, 40.0);
  }
}
