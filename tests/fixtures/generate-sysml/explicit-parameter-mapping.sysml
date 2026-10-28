package RecoveredFromSSD {
  port def CompParameters :> ParameterInterface {
    attribute count : Integer;
    attribute xs : Real[2];
  }

  port def ParameterInterface;

  attribute def Nom :> ParameterSet {
    attribute n : Integer = 5;
    attribute x : Real[2] = (1.0, 2.0);
  }

  attribute def ParameterSet;

  part def Comp {
    in port parameters : CompParameters;
  }

  part def ParamDemo {
    attribute Nom : Nom;
    part comp : Comp;
    bind comp.parameters.count = Nom.n;
    bind comp.parameters.xs = Nom.x;
  }
}
