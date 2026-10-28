package Example {
          part def Gain {
            attribute k : Real = 3.0;
          }

          part def $COMPOSITION_NAME {
            part gain : Gain;
            attribute pyssp_parameter_set : String = "parameters.ssv";
          }
        }
