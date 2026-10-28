package RecoveredFromSSD {
  port def GainParameters :> ParameterInterface {
    attribute k : Real;
  }

  port def ParameterInterface;

  attribute def ParameterSet;

  attribute def parameters :> ParameterSet {
    attribute k : Real = 4.0;
  }

  part def Gain {
    in port parameters : GainParameters;
  }

  part def ParamDemo {
    attribute parameters_set : parameters;
    part gain : Gain;
    bind gain.parameters = parameters_set;
  }
}
