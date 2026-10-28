package Example {
          port def Signal {
            attribute x : Real;
            attribute y : Real;
          }

          part def Source {
            out port sig : Signal;
          }

          part def Sink {
            in port sigIn : Signal;
            out port sig : Signal;
          }

          part def Inner {
            in port u : Signal;
            out port v : Signal;
            part src : Source;
            part dst : Sink;
            connect u to src.sig;
            connect src.sig to dst.sigIn;
            connect dst.sig to v;
          }

          part def SystemComposition {
            out port y : Signal;
            part inner : Inner;
            connect inner.v to y;
          }
        }
