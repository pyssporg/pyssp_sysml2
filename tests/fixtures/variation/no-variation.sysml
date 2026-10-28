package NoVariation {
  part def SspModel;
  port def RealSignal {
    attribute pyssp_flat_connector : Boolean = true;
    attribute value : Real;
  }

  part def Step {
    out port y : RealSignal;
  }

  part def Gain {
    in port u : RealSignal;
    out port y : RealSignal;
  }

  part def System :> SspModel {
    part step : Step;
    part gain : Gain;
    connect step.y to gain.u;
  }
}
