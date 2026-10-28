package Example {
          part def Source {
            out port outSig : Signal;
          }

          part def Sink {
            in port inSig : Signal;
          }

          part def Utility {
            out port debug : DebugSignal;
          }
        }
