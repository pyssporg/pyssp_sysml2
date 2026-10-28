package Example {
          port def ParameterInterface;
          attribute def ParameterSet;

          port def Params :> ParameterInterface {
            attribute count : Integer;
            attribute xs : Real[2];
          }

          attribute def Nom :> ParameterSet {
            attribute n = 5;
            attribute x = (1.0, 2.0);
          }

          part def Comp {
            in port parameters : Params;
          }

          part def SystemComposition {
            part c : Comp;
            attribute nominal : Nom;
            bind c.parameters.count = nominal.n;
            bind c.parameters.xs = nominal.x;
          }
        }
