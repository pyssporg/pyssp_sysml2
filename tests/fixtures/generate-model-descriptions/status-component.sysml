package Example {
          port def Status {
            attribute ok: Boolean;
          }

          part def Comp {
            out port status : Status;
          }

          part def $COMPOSITION_NAME {
            part c : Comp;
          }
        }
