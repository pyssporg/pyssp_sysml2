package Boundary {
          part def Source {
            out port outSig : Signal;
          }

          part def Sink { in port inSig : Signal; }

          part def Inner {
            in port u : Signal;
            out port v : Signal;
            part src : Source;
            part dst : Sink;
            connect u to src.inSig;
            connect src.outSig to dst.inSig;
            connect dst.inSig to v;
          }
        }
