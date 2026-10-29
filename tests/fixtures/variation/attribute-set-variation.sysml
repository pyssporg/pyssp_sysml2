package AttributeSetVariation {
  part def SspModel;
  part def Analysis;

  port def ParameterInterface;
  attribute def ParameterSet;

  port def StepParameters :> ParameterInterface {
    attribute height : Real;
    attribute offset : Real;
    attribute startTime : Real;
  }

  port def GainParameters :> ParameterInterface {
    attribute k : Real;
  }

  attribute def BaselineScenario :> ParameterSet {
    attribute height = 2.0;
    attribute offset = 1.0;
    attribute startTime = 0.25;
    attribute k = 3.0;
  }

  attribute def LateStepScenario :> ParameterSet {
    attribute height = 2.0;
    attribute offset = 1.0;
    attribute startTime = 0.75;
    attribute k = 3.0;
  }

  attribute def HighGainScenario :> ParameterSet {
    attribute height = 2.0;
    attribute offset = 1.0;
    attribute startTime = 0.25;
    attribute k = 9.0;
  }

  variation attribute def ScenarioChoice {
    variant attribute baseline : BaselineScenario;
    variant attribute lateStep : LateStepScenario;
    variant attribute highGain : HighGainScenario;
  }

  attribute def Experiment {
    attribute startTime : Real;
    attribute stopTime : Real;
    attribute stepSize : Real;
    attribute tolerance : Real;
  }

  attribute def BaselineExperiment :> Experiment {
    attribute startTime = 0.0;
    attribute stopTime = 1.0;
    attribute stepSize = 0.001;
    attribute tolerance = 0.0001;
  }

  part def Step {
    in port parameters : StepParameters;
  }

  part def Gain {
    in port parameters : GainParameters;
  }

  part def System :> SspModel {
    part step : Step;
    part gain : Gain;
  }

  part def test_selected_scenario :> Analysis {
    attribute experiment_baseline : BaselineExperiment;
    attribute scenario : ScenarioChoice;
    part sut : System;

    bind sut.step.parameters.height = scenario.height;
    bind sut.step.parameters.offset = scenario.offset;
    bind sut.step.parameters.startTime = scenario.startTime;
    bind sut.gain.parameters.k = scenario.k;
  }
}
