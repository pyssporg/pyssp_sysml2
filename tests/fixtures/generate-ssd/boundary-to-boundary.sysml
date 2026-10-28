package Example {
          port def Signal {
            attribute x : Real;
          }

          part def $COMPOSITION_NAME {
            in port u : Signal;
            out port v : Signal;
            connect u to v;
          }
        }
