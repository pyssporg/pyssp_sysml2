package Example {
          port def ParameterInterface;
          attribute def ParameterSet;

          port def InnerParams :> ParameterInterface {
            attribute count : Integer;
            attribute gain : Real;
          }

          attribute def Counts :> ParameterSet {
            attribute n = 10;
          }

          attribute def Gains :> ParameterSet {
            attribute k = 2.5;
          }

          part def Inner {
            in port parameters : InnerParams;
          }

          part def Outer {
            part inner : Inner;
          }

          part def SystemComposition {
            part outer : Outer;
            attribute counts : Counts;
            attribute gains : Gains;
            bind outer.inner.parameters.count = counts.n;
            bind outer.inner.parameters.gain = gains.k;
          }
        }
