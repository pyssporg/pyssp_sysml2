package Example {
          part def Comp {
            attribute gain : Real = 1.0;
          }

          part def $COMPOSITION_NAME {
            part c : Comp;
          }
        }
