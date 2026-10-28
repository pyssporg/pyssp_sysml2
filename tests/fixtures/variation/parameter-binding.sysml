package ParameterBindingVariation {
  part def SspModel;
  part def Study;

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

  attribute def BaselineValues :> ParameterSet {
    attribute height = 2.0;
    attribute offset = 1.0;
    attribute startTime = 0.25;
    attribute k = 3.0;
  }

  attribute def LateStepValues :> ParameterSet {
    attribute height = 2.0;
    attribute offset = 1.0;
    attribute startTime = 0.75;
    attribute k = 3.0;
  }

  attribute def HighGainValues :> ParameterSet {
    attribute height = 2.0;
    attribute offset = 1.0;
    attribute startTime = 0.25;
    attribute k = 9.0;
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

  /* Fixed topology. No variation point appears anywhere inside it. */
  part def System :> SspModel {
    attribute pyssp_default_start_time : Real = 0.0;
    attribute pyssp_default_stop_time : Real = 1.0;
    part step : Step;
    part gain : Gain;
    connect step.y to gain.u;
  }

  /* Marker type for the binding point: the alternative adds no ports, only
   * values, so the variation usage has no interface of its own. */
  part def ParameterBinding;

  part def test_selected :> Study {
    doc /* One study per selection; the topology is the same composition. */
    attribute experiment_baseline : BaselineExperiment;
    part sut : System;

    variation part parameters : ParameterBinding {
      variant part baselineBinding {
        attribute values : BaselineValues;
        bind sut.step.parameters.height = values.height;
        bind sut.step.parameters.offset = values.offset;
        bind sut.step.parameters.startTime = values.startTime;
        bind sut.gain.parameters.k = values.k;
      }

      variant part lateStepBinding {
        attribute values : LateStepValues;
        bind sut.step.parameters.height = values.height;
        bind sut.step.parameters.offset = values.offset;
        bind sut.step.parameters.startTime = values.startTime;
        bind sut.gain.parameters.k = values.k;
      }

      variant part highGainBinding {
        attribute values : HighGainValues;
        bind sut.step.parameters.height = values.height;
        bind sut.step.parameters.offset = values.offset;
        bind sut.step.parameters.startTime = values.startTime;
        bind sut.gain.parameters.k = values.k;
      }
    }
  }
}
