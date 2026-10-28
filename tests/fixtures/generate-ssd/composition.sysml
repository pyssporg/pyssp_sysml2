package Example {
          part def $COMPOSITION_NAME {
            part src : Source;
            part dst : Sink;

            connect src.sig to dst.sigIn;
          }
        }
