package NestedPathExample {
  doc /* A set applied to a component below a nested system usage. */

  attribute def ParameterInterface;
  attribute def ParameterSet;

  attribute def InnerParameters :> ParameterInterface {
    attribute k : Real;
  }

  attribute def NominalSet :> ParameterSet {
    attribute k = 3.0;
  }

  part def Inner {
    attribute parameters : InnerParameters;
  }

  part def Outer {
    part inner : Inner;
  }

  part def NestedPathComposition {
    part outer : Outer;
    attribute nominal : NominalSet;

    bind nominal.k = outer.inner.parameters.k;
  }
}
