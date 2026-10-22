package StudyDemo {
  attribute def NominalScenario :> ParameterSet {
    attribute inputScale = 1.0;
    attribute gain = 1.0;
    attribute timeConstant = 0.25;
  }

  attribute def AggressiveScenario :> ParameterSet {
    attribute inputScale = 2.0;
    attribute gain = 1.5;
    attribute timeConstant = 0.15;
  }

  attribute def BaselineExperiment :> Experiment {
    attribute startTime = 0.0;
    attribute stopTime = 10.0;
    attribute stepSize = 0.01;
    attribute tolerance = 0.000001;
  }

  attribute def FastExperiment :> Experiment {
    attribute startTime = 0.0;
    attribute stopTime = 2.0;
    attribute stepSize = 0.002;
    attribute tolerance = 0.0000001;
  }

  part def test_baseline :> Study {
    doc /* Nominal actuator over a long horizon. */
    attribute experiment_baseline : BaselineExperiment;
    attribute scenario : NominalScenario;
    part sut : PositionServo;

    bind sut.axis.plant.parameters.inputScale = scenario.inputScale;
    bind sut.axis.plant.parameters.gain = scenario.gain;
    bind sut.axis.plant.parameters.timeConstant = scenario.timeConstant;
  }

  part def test_aggressive :> Study {
    doc /* Higher input scale and gain over a short horizon. */
    attribute experiment_aggressive : FastExperiment;
    attribute scenario : AggressiveScenario;
    part sut : PositionServo;

    bind sut.axis.plant.parameters.inputScale = scenario.inputScale;
    bind sut.axis.plant.parameters.gain = scenario.gain;
    bind sut.axis.plant.parameters.timeConstant = scenario.timeConstant;
  }
}
