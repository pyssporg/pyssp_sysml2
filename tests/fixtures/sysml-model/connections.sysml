package Connections {
          part def Source {
            out port outSig : Signal;
            out port aux : Signal;
          }

          part def Sink { in port inSig : Signal; }

          part def SystemComposition {
            part src : Source;
            part dst : Sink;
            connect src.outSig to dst.inSig;
            connection explicit : Link connect src.aux to dst.inSig;
          }
        }
