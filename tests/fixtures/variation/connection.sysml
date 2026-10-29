package ConnectionVariation {
  part def SspModel;
  part def Analysis;

  port def ParameterInterface;

  port def StepParameters :> ParameterInterface {
    attribute height : Real;
    attribute offset : Real;
    attribute startTime : Real;
  }

  port def GainParameters :> ParameterInterface {
    attribute k : Real;
  }

  port def RealSignal {
    attribute pyssp_flat_connector : Boolean = true;
    attribute value : Real;
  }

  attribute def ParameterSet;

  attribute def BaselineScenario :> ParameterSet {
    attribute height = 2.0;
    attribute offset = 1.0;
    attribute startTime = 0.25;
    attribute k = 3.0;
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

  attribute def FmuMetadata {
    attribute source : String;
    attribute implementation : String;
  }

  attribute def StepFmu :> FmuMetadata {
    attribute source = "models/fmu/Modelica.Blocks.Sources.Step/fmu";
    attribute implementation = "CoSimulation";
  }

  attribute def GainFmu :> FmuMetadata {
    attribute source = "models/fmu/Modelica.Blocks.Math.Gain/fmu";
    attribute implementation = "CoSimulation";
  }

  part def Step {
    attribute fmu_meta : StepFmu;
    in port parameters : StepParameters;
    out port y : RealSignal;
  }

  part def Gain {
    attribute fmu_meta : GainFmu;
    in port u : RealSignal;
    out port y : RealSignal;
    in port parameters : GainParameters;
  }

  /* The variation point. Its ports are the contract every variant has to wire,
   * because the outer composition connects to these and to nothing else. */
  variation part def PathChoice {
    in port u : RealSignal;
    out port y : RealSignal;
    in port parameters : GainParameters;

    /* Direct path: one stage, so the outer source reaches the gain directly. */
    variant part directPath {
      part gain : Gain;
      connect u to gain.u;
      connect gain.y to y;
      connect parameters to gain.parameters;
    }

    /* Filtered path: the same endpoints, one more stage in between. */
    variant part filteredPath {
      part firstStage : Gain;
      part gain : Gain;
      connect u to firstStage.u;
      connect firstStage.y to gain.u;
      connect gain.y to y;
      connect parameters to firstStage.parameters;
      connect parameters to gain.parameters;
    }
  }

  part def System :> SspModel {
    out port y : RealSignal;
    attribute pyssp_default_start_time : Real = 0.0;
    attribute pyssp_default_stop_time : Real = 1.0;
    part source : Step;
    part path : PathChoice;

    /* Fixed in every selection: only the variation point's ports are named. */
    connect source.y to path.u;
    connect path.y to y;
  }

  part def test_selected :> Analysis {
    doc /* One analysis per selection; the selection itself is not recorded here. */
    attribute experiment_baseline : BaselineExperiment;
    attribute scenario : BaselineScenario;
    part sut : System;

    bind sut.source.parameters.height = scenario.height;
    bind sut.source.parameters.offset = scenario.offset;
    bind sut.source.parameters.startTime = scenario.startTime;
    bind sut.path.parameters.k = scenario.k;
  }
}
