package Example {
          part def Comp {
            attribute pyssp_implementation = "CoSimulation";
          }

          part def $COMPOSITION_NAME {
            part comp : Comp;
          }
        }
