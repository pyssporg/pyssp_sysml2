package Aircraft {
  port def ParameterInterface;
  attribute def ParameterSet;

  attribute def FmuMetadata {
    attribute source : String;
    attribute implementation : String;
  }

  port def AutopilotParameters :> ParameterInterface {
    attribute note : String;
    attribute waypointCount : Integer;
    attribute waypointX_km : Real[3];
  }

  attribute def NominalSet :> ParameterSet {
    attribute note = "uses waypoint tracking";
    attribute n_waypoints = 10;
    attribute waypoints_x_km = (0.0, 10.0, 20.0);
  }

  attribute def AutopilotFmu :> FmuMetadata {
    attribute source = "build/fmus/AutopilotModule.fmu";
    attribute implementation = "CoSimulation";
  }

  part def AutopilotModule {
    doc /* F-16 autopilot, takes in sensor data and translates it into a equivalent hotas command. */
    attribute fmu_meta : AutopilotFmu;

    doc /* Autopilot tuning and waypoint parameters. */
    in port parameters : AutopilotParameters;

    doc /* Mission-computer flight status back into autopilot. */
    in port feedbackBus : FlightStatusPacket;

    doc /* Current local position from sensors */
    in port currentLocation : PositionXYZ;

    doc /* Current attitude from sensors. */
    in port currentOrientation : OrientationEuler;

    doc /* HOTAS-equivalent command stream for mission computer blending. */
    out port autopilotCmd : PilotCommand;

    doc /* Waypoint progression for logging and verification. */
    out port missionStatus : MissionStatus;
  }

  part def MissionComputer {
    doc /* F-16C/D mission computer blending pilot HOTAS inputs with fly-by-wire control laws and stores management. */

    doc /* Autopilot command bundle using same HOTAS signal structure. */
    in port autopilotInput : PilotCommand;

    doc /* Command how to alter the current velocity vector, pith, yaw, roll */
    out port direction_command : OrientationEuler;
  }

  part def Environment {
    doc /* Tracking position and velocities of the aircraft and feeds the sensors */
    in port direction_command : OrientationEuler;

    doc /* Feedback for simulated sensors */
    out port orientation : OrientationEuler;
    out port location : PositionXYZ;
    out port flight_status : FlightStatusPacket;
  }

}
