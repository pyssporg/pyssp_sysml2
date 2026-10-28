package ModelOwnedStudy {
  part def SspModel;
  part def Study;

  port def ParameterInterface;
  attribute def ParameterSet;

  port def LeafParameters :> ParameterInterface {
    attribute k : Real;
  }

  attribute def ScenarioSet :> ParameterSet {
    attribute k = 2.0;
  }

  attribute def Experiment {
    attribute startTime : Real;
    attribute stopTime : Real;
    attribute stepSize : Real;
  }

  attribute def BaselineExperiment :> Experiment {
    attribute startTime = 0.0;
    attribute stopTime = 1.0;
    attribute stepSize = 0.1;
  }

  part def Leaf {
    in port parameters : LeafParameters;
  }

  part def System :> SspModel {
    attribute scenario : ScenarioSet;
    part leaf : Leaf;
    bind leaf.parameters.k = scenario.k;
  }

  part def baseline :> Study {
    attribute experiment_baseline : BaselineExperiment;
    part sut : System;
  }
}
