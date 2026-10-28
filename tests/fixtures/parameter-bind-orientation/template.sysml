    package Orientation {
      port def ParameterInterface;
      attribute def ParameterSet;

      port def Params :> ParameterInterface {
        attribute count : Integer;
      }

      attribute def Set1 :> ParameterSet {
        attribute n = 1;
      }

      part def Comp {
        in port parameters : Params;
      }

      part def $COMPOSITION_NAME {
        $parts
        attribute nominal : Set1;
        $bind_line
      }
    }
