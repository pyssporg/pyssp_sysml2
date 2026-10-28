    package Ports {
      port def ParameterInterface;
      attribute def ParameterSet;

      port def Params :> ParameterInterface {
        attribute gain : Real;
      }

      part def Comp {
        in port parameters : Params;
      }

      part def $COMPOSITION_NAME {
        part left : Comp;
        part right : Comp;
        connect left.parameters to right.parameters;
      }
    }
