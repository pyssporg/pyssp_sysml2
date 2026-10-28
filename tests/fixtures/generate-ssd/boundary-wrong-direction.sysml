package Example {
          port def Signal {
            attribute x : Real;
          }

          part def Source {
            out port sig : Signal;
          }

          part def $COMPOSITION_NAME {
            in port y : Signal;
            part src : Source;
            connect src.sig to y;
          }
        }
