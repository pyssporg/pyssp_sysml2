package RoleModel {
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
    attribute tolerance : Real;
  }

  attribute def BaselineExperiment :> Experiment {
    attribute startTime = 0.0;
    attribute stopTime = 1.0;
    attribute stepSize = 0.1;
    attribute tolerance = 0.0001;
  }

  part def Leaf {
    in port parameters : LeafParameters;
  }

  part def System :> SspModel {
    part leaf : Leaf;
  }

  part def test_baseline :> Study {
    attribute experiment_baseline : BaselineExperiment;
    attribute scenario : ScenarioSet;
    part sut : System;
    bind sut.leaf.parameters.k = scenario.k;
  }
}
