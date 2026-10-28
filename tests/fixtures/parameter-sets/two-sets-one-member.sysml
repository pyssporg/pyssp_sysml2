    package Example {
      port def ParameterInterface;
      attribute def ParameterSet;
      port def Params :> ParameterInterface {
        attribute count : Integer;
      }
      attribute def CountsA :> ParameterSet { attribute n = 10; }
      attribute def CountsB :> ParameterSet { attribute m = 20; }
      part def Comp { in port parameters : Params; }
      part def $COMPOSITION_NAME {
        part comp : Comp;
        attribute counts_a : CountsA;
        attribute counts_b : CountsB;
        bind comp.parameters.count = counts_a.n;
        bind comp.parameters.count = counts_b.m;
      }
    }
