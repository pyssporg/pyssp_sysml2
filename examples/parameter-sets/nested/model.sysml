package NestedPathExample {
  doc /* A set applied to a component below a nested system usage. */

  port def ParameterInterface;
  attribute def ParameterSet;

  port def InnerParameters :> ParameterInterface {
    attribute k : Real;
  }

  attribute def NominalSet :> ParameterSet {
    attribute k = 3.0;
  }

  part def Inner {
    in port parameters : InnerParameters;
  }

  part def Outer {
    part inner : Inner;
  }

  part def NestedPathComposition {
    part outer : Outer;
    attribute nominal : NominalSet;

    bind outer.inner.parameters.k = nominal.k;
  }
}
