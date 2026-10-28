package Example {
          port def Signal {
            attribute x : Real;
          }

          part def Source {
            out port outSig : Signal;
          }

          part def Sink {
            in port inSig : Signal;
          }

          part def Controller {
            part src : Source;
            part dst : Sink;
            connect src.outSig to dst.inSig;
          }

          part def SystemComposition {
            part controller : Controller;
          }
        }
