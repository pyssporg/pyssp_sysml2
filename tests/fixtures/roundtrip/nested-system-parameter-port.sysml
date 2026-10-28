package Example {
          port def ParameterInterface;
          attribute def ParameterSet;

          port def InnerParams :> ParameterInterface {
            attribute k : Real;
          }

          port def OuterParams :> ParameterInterface {
            attribute gain : Real = 2.0;
          }

          attribute def InnerSet :> ParameterSet {
            attribute k = 3.0;
          }

          attribute def OuterSet :> ParameterSet {
            attribute g = 4.0;
          }

          part def Inner {
            in port parameters : InnerParams;
          }

          part def Outer {
            in port parameters : OuterParams;
            part inner : Inner;
          }

          part def SystemComposition {
            part outer : Outer;
            attribute inner_set : InnerSet;
            attribute outer_set : OuterSet;
            bind outer.inner.parameters.k = inner_set.k;
            bind outer.parameters.gain = outer_set.g;
          }
        }
