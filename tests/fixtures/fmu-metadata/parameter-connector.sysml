package Example {
          port def ParameterInterface;
          attribute def ParameterSet;

          attribute def FmuMetadata { attribute implementation : String; }

          attribute def CompFmu :> FmuMetadata {
            attribute implementation = "CoSimulation";
          }

          port def CompParameters :> ParameterInterface {
            attribute gain : Real;
          }

          part def Comp {
            attribute fmu_meta : CompFmu;
            in port parameters : CompParameters;
          }

          part def $COMPOSITION_NAME {
            part comp : Comp;
          }
        }
