package Overwrite {
          part def SystemComposition {
            part src : Source;
            part dst : Sink;
            connect src.outSig to dst.inSig;
            connect src.outSig to dst.inSig;
          }
        }
