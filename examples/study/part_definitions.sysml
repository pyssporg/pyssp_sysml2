package StudyDemo {
  part def SspModel;
  part def Study;

  port def ParameterInterface;
  attribute def ParameterSet;

  attribute def Experiment {
    attribute startTime : Real;
    attribute stopTime : Real;
    attribute stepSize : Real;
    attribute tolerance : Real;
  }

  port def ServoCommand {
    attribute position_m : Real;
  }

  port def ServoFeedback {
    attribute position_m : Real;
  }

  port def ServoDemand {
    attribute voltage_v : Real;
  }

  port def ActuatorParameters :> ParameterInterface {
    attribute inputScale : Real;
    attribute gain : Real;
    attribute timeConstant : Real;
  }

  part def Driver {
    in port command : ServoCommand;
    out port demand : ServoDemand;
  }

  part def Actuator {
    in port demand : ServoDemand;
    in port parameters : ActuatorParameters;
    out port position : ServoFeedback;
  }

  part def ServoAxis {
    part driver : Driver;
    part plant : Actuator;

    connect driver.demand to plant.demand;
  }

  part def PositionServo :> SspModel {
    doc /* Commanded position servo exported as one SSP model. */
    part axis : ServoAxis;
  }
}
