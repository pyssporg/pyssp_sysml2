package IdentityExample {
  doc /* Identity bind: set member names match interface member names. */

  port def ParameterInterface;
  attribute def ParameterSet;

  port def AutopilotParameters :> ParameterInterface {
    doc /* Parameter surface of the autopilot FMU. */
    attribute waypointCount : Integer;
    attribute waypointX_km : Real[3];
  }

  attribute def NominalSet :> ParameterSet {
    doc /* Values use the same names as the interface. */
    attribute waypointCount = 10;
    attribute waypointX_km = (0.0, 10.0, 20.0);
  }

  part def AutopilotModule {
    in port parameters : AutopilotParameters;
  }

  part def IdentityComposition {
    part autopilot : AutopilotModule;
    attribute nominal : NominalSet;

    bind autopilot.parameters = nominal;
  }
}
