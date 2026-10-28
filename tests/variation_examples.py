"""Verbatim model text of the variation-point examples used as fixtures.

The package bodies are copied from
``docs/breakdown/06-evolution/selected/examples/variation-points/``
in the product repository; the descriptive header comment is omitted.
"""

from __future__ import annotations

USAGE_LEVEL_VARIATION = """\
package UsageLevelVariation {
  part def SspModel;

  port def ParameterInterface;

  port def StepParameters :> ParameterInterface {
    attribute height : Real;
    attribute offset : Real;
    attribute startTime : Real;
  }

  port def SineParameters :> ParameterInterface {
    attribute amplitude : Real;
    attribute f : Real;
    attribute offset : Real;
    attribute phase : Real;
    attribute startTime : Real;
  }

  port def RealSignal {
    attribute pyssp_flat_connector : Boolean = true;
    attribute value : Real;
  }

  attribute def FmuMetadata {
    attribute source : String;
    attribute implementation : String;
  }

  attribute def StepFmu :> FmuMetadata {
    attribute source = "models/fmu/Modelica.Blocks.Sources.Step/fmu";
    attribute implementation = "CoSimulation";
  }

  attribute def SineFmu :> FmuMetadata {
    attribute source = "models/fmu/Modelica.Blocks.Sources.Sine/fmu";
    attribute implementation = "CoSimulation";
  }

  attribute def GainFmu :> FmuMetadata {
    attribute source = "models/fmu/Modelica.Blocks.Math.Gain/fmu";
    attribute implementation = "CoSimulation";
  }

  part def SignalSource {
    out port y : RealSignal;
  }

  part def Step :> SignalSource {
    attribute fmu_meta : StepFmu;
    in port parameters : StepParameters;
    out port :>> y : RealSignal;
  }

  part def Sine :> SignalSource {
    attribute fmu_meta : SineFmu;
    in port parameters : SineParameters;
    out port :>> y : RealSignal;
  }

  part def Gain {
    attribute fmu_meta : GainFmu;
    in port u : RealSignal;
    out port y : RealSignal;
  }

  part def System :> SspModel {
    attribute pyssp_default_start_time : Real = 0.0;
    attribute pyssp_default_stop_time : Real = 1.0;

    variation part source : SignalSource {
      variant part stepSource : Step;
      variant part sineSource : Sine;
    }

    part gain : Gain;
    connect source.y to gain.u;
  }
}
"""

CONNECTION_VARIATION = """\
package ConnectionVariation {
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

  part def test_selected :> Study {
    doc /* One study per selection; the selection itself is not recorded here. */
    attribute experiment_baseline : BaselineExperiment;
    attribute scenario : BaselineScenario;
    part sut : System;

    bind sut.source.parameters.height = scenario.height;
    bind sut.source.parameters.offset = scenario.offset;
    bind sut.source.parameters.startTime = scenario.startTime;
    bind sut.path.parameters.k = scenario.k;
  }
}
"""

PARAMETER_BINDING_VARIATION = """\
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
"""

NESTED_VARIATION = """\
package NestedVariation {
  part def SspModel;

  port def RealSignal {
    attribute pyssp_flat_connector : Boolean = true;
    attribute value : Real;
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

  attribute def AttenuateFmu :> FmuMetadata {
    attribute source = "models/fmu/Modelica.Blocks.Math.Gain/attenuate";
    attribute implementation = "CoSimulation";
  }

  part def Step {
    attribute fmu_meta : StepFmu;
    out port y : RealSignal;
  }

  part def Gain {
    attribute fmu_meta : GainFmu;
    in port u : RealSignal;
    out port y : RealSignal;
  }

  part def Attenuate {
    attribute fmu_meta : AttenuateFmu;
    in port u : RealSignal;
    out port y : RealSignal;
  }

  /* Inner point: the stage that feeds the gain in the nested path. */
  variation part def StageChoice {
    in port u : RealSignal;
    out port y : RealSignal;

    variant part gainStage : Gain;
    variant part attenuateStage : Attenuate;
  }

  /* Outer point. Its direct body holds no variation; its nested body does. */
  variation part def PathChoice {
    in port u : RealSignal;
    out port y : RealSignal;

    variant part directPath {
      part gain : Gain;
      connect u to gain.u;
      connect gain.y to y;
    }

    variant part nestedPath {
      /* The inner usage declares the same alternatives as its definition. */
      variation part stage : StageChoice {
        variant part gainStage : Gain;
        variant part attenuateStage : Attenuate;
      }

      part gain : Gain;
      connect u to stage.u;
      connect stage.y to gain.u;
      connect gain.y to y;
    }
  }

  part def System :> SspModel {
    out port y : RealSignal;
    attribute pyssp_default_start_time : Real = 0.0;
    attribute pyssp_default_stop_time : Real = 1.0;
    part source : Step;
    part path : PathChoice;

    /* Fixed in every selection: only the outer point's ports are named. */
    connect source.y to path.u;
    connect path.y to y;
  }
}
"""
