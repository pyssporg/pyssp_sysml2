package AttributeBinding {
  part def SspModel;
  part def Analysis;

  attribute def ParameterSet;

  attribute def ScenarioK3 :> ParameterSet;

  attribute def ScenarioK5 :> ParameterSet;

  attribute def Experiment {
    attribute startTime : Real;
    attribute stopTime : Real;
    attribute stepSize : Real;
  }

  attribute def BaselineExperiment :> Experiment {
    attribute startTime = 0.0;
    attribute stopTime = 1.0;
    attribute stepSize = 0.001;
  }

  variation attribute def ScenarioChoice {
    variant attribute nominalK3 : ScenarioK3;
    variant attribute nominalK5 : ScenarioK5;
  }

  part def Root :> SspModel {
    attribute scenario : ScenarioChoice;
  }

  /* A configuration binds the model's attribute point structurally. */
  part def Configured :> Root {
    attribute :>> scenario = ScenarioChoice::nominalK3;
  }

  part def configured :> Analysis {
    attribute experiment : BaselineExperiment;
    part sut : Configured;
  }

  /* A variant the point does not declare stays an error. */
  part def BadConfigured :> Root {
    attribute :>> scenario = ScenarioChoice::missing;
  }

  part def bad :> Analysis {
    part sut : BadConfigured;
  }
}
