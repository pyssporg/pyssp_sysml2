package Example {
          port def ParameterInterface;
          attribute def ParameterSet;

          port def CompParameters :> ParameterInterface {
            attribute int_list : Integer[2] = (1, 2);
            attribute bool_list : Boolean[2] = (true, false);
          }

          part def Comp {
            in port parameters : CompParameters;
            out port status : Status;
          }

          part def $COMPOSITION_NAME {
            part c : Comp;
          }
        }
