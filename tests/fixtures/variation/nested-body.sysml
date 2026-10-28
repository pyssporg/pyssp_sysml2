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
