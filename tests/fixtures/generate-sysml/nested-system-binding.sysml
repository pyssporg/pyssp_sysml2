package RecoveredFromSSD {
  port def InnerParameters :> ParameterInterface {
    attribute k : Real;
  }

  port def ParameterInterface;

  attribute def Nom :> ParameterSet {
    attribute k : Real = 3.0;
  }

  attribute def ParameterSet;

  part def Demo {
    attribute Nom : Nom;
    part outer : outer;
    bind outer.inner.parameters = Nom;
  }

  part def Inner {
    in port parameters : InnerParameters;
  }

  part def outer {
    part inner : Inner;
  }
}
