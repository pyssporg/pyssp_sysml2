package RecoveredFromSSD {
  port def GainParameters :> ParameterInterface {
    attribute k : Real;
  }

  port def ParameterInterface;

  attribute def ParameterSet;

  part def Gain {
    in port parameters : GainParameters;
  }

  part def ParamDemo {
    part gain : Gain;
  }
}
