package UndeclaredBodyPort {
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
    in port u : RealSignal;

    variant part directPath {
      part gain : Gain;
      connect u to gain.u;
      connect gain.y to missing;
    }
  }

  part def System :> SspModel {
    part path : PathChoice;
  }
}
