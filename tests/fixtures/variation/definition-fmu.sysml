package DefinitionVariationFmu {
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
    attribute source = "models/fmu/Step";
    attribute implementation = "CoSimulation";
  }

  attribute def SineFmu :> FmuMetadata {
    attribute source = "models/fmu/Sine";
    attribute implementation = "CoSimulation";
  }

  part def Step {
    attribute fmu_meta : StepFmu;
    out port y : RealSignal;
  }

  part def Sine {
    attribute fmu_meta : SineFmu;
    out port y : RealSignal;
  }

  part def Gain {
    in port u : RealSignal;
    out port y : RealSignal;
  }

  variation part def SourceChoice {
    variant part stepImplementation : Step;
    variant part sineImplementation : Sine;
  }

  part def System :> SspModel {
    part source : SourceChoice;
    part gain : Gain;
    connect source.y to gain.u;
  }
}
