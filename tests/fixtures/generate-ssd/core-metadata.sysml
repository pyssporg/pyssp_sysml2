package Example {
          port def Signal {
            attribute x: Real;
          }

          part def Source {
            out port outSig : Signal;
          }

          part def $COMPOSITION_NAME {
            part src : Source;
          }
        }
