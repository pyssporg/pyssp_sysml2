package Example {
          port def ParameterInterface;
          attribute def ParameterSet;

          port def Parameters :> ParameterInterface {
            attribute gain : Real;
          }

          attribute def NominalSet :> ParameterSet {
            attribute gain_value = 2.0;
          }

          part def Source {
            in port parameters : Parameters;
            out port outSig : Signal;
          }

          port def Signal {
            attribute x : Real;
          }

          part def $COMPOSITION_NAME {
            part src : Source;
            attribute nominal : NominalSet;
            bind src.parameters.gain = nominal.gain_value;
          }
        }
