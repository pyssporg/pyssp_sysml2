package Values {
          port def ParameterInterface;
          attribute def ParameterSet;

          port def Interface :> ParameterInterface {
            attribute gain : Real;
            attribute count : Integer;
          }

          attribute def NominalSet :> ParameterSet {
            attribute gain_value = 2.0;
          }
        }
