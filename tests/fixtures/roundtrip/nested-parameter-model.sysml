package Example {
          port def ParameterInterface;
          attribute def ParameterSet;

          port def InnerParams :> ParameterInterface {
            attribute k : Real = 1.0;
          }

          attribute def Nom :> ParameterSet {
            attribute k = 3.0;
          }

          part def Inner {
            in port parameters : InnerParams;
          }

          part def Outer {
            part inner : Inner;
          }

          part def SystemComposition {
            part outer : Outer;
            attribute nominal : Nom;
            bind outer.inner.parameters.k = nominal.k;
          }
        }
