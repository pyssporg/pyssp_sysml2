package Example {
          port def Signal {
            attribute x: Real;
            attribute y: Real;
          }

          part def Source {
            out port outSig : Signal;
          }

          part def Sink {
            in port inSig : Signal;
          }

          part def AltSink {
            in port inSig : Signal;
          }

          part def SystemComposition {
            part src : Source;
            part dst : Sink;
            connect src.outSig to dst.inSig;
          }
        }
