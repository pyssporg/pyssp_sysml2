package VariantBodyUnsupportedMember {
  part def SspModel;
  port def RealSignal {
    attribute pyssp_flat_connector : Boolean = true;
    attribute value : Real;
  }
  part def Gain {
    in port u : RealSignal;
    out port y : RealSignal;
  }

  variation part def PathChoice {
    variant part directPath {
      port p : RealSignal;
    }
  }

  part def System :> SspModel {
    part path : PathChoice;
  }
}
