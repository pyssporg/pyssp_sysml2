package Aircraft {
  part def AircraftComposition {
    doc /* Top-level aircraft composition with functional subsystem instances. */
    
    part autopilot : AutopilotModule;
    part missionComputer : MissionComputer;
    part environment : Environment;

    connect autopilot.autopilotCmd to missionComputer.autopilotInput;
    connect missionComputer.direction_command to environment.direction_command;
    connect environment.orientation to autopilot.currentOrientation;
    connect environment.location to autopilot.currentLocation;
    connect environment.flight_status to autopilot.feedbackBus;
  }
}