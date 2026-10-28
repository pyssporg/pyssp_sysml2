package DefinitionVariation {
  part def SspModel;
  port def RealSignal {
    attribute pyssp_flat_connector : Boolean = true;
    attribute value : Real;
  }

  part def Step {
    out port y : RealSignal;
  }

  part def Sine {
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
