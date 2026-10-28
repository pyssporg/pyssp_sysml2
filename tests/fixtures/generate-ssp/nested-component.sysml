package Example {
          attribute def FmuMetadata {
            attribute source : String;
            attribute implementation : String;
          }

          attribute def LeafFmu :> FmuMetadata {
            attribute source = "$leaf_fmu";
            attribute implementation = "CoSimulation";
          }

          port def Signal {
            attribute y : Real;
          }

          part def Leaf {
            attribute fmu_meta : LeafFmu;
            out port output : Signal;
          }

          part def Sub {
            part leaf : Leaf;
          }

          part def $COMPOSITION_NAME {
            part sub : Sub;
          }
        }
