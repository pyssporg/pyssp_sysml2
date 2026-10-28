package RoundTrip {
          port def ParameterInterface;
          attribute def ParameterSet;

          port def Measurements :> ParameterInterface {
            attribute temperature : Real[2];
          }

          attribute def NominalMeasurements :> ParameterSet {
            attribute temps = (1.0, 2.0);
          }

          port def Signal {
            doc /* A signal. */
            attribute level : Real;
            attribute count : Integer;
          }

          part def Source {
            doc /* Source doc. */
            attribute gain : Real = 2.0;
            attribute offset = -1.5;
            attribute label = "hi";
            attribute enabled = true;
            attribute taps = (1.0, 2.0);
            out port sig : Signal;
          }

          part def Sink {
            in port sigIn : Signal;
          }

          part def Measured {
            in port parameters : Measurements;
          }

          part def SystemComposition {
            out port outSig : Signal;
            part src : Source;
            part dst : Sink;
            part measured : Measured;
            attribute nominal : NominalMeasurements;

            connect src.sig to dst.sigIn;
            connect src.sig to outSig;
            bind measured.parameters.temperature = nominal.temps;
          }

          requirement def Connected {
            doc /* src must connect to dst */
          }
        }
