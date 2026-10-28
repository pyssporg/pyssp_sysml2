package Example {
          port def ParameterInterface;
          attribute def ParameterSet;

          port def SourceParameters :> ParameterInterface {
            attribute gains : Real[2];
          }

          part def Source {
            in port parameters : SourceParameters;
            out port sig : Signal;
          }

          part def Sink {
            in port sigIn : Signal;
          }
        }
