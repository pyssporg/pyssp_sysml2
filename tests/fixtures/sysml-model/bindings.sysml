package Bindings {
          attribute def Interface {
            attribute gain : Real;
          }

          attribute def Set {
            attribute gain_value = 2.0;
          }

          part def Component {
            in port parameters : Interface;
          }

          part def SystemComposition {
            part componentA : Component;
            part componentB : Component;
            attribute nominal : Set;

            bind componentA.parameters.gain = nominal.gain_value;
            bind componentB.parameters = nominal;
          }
        }
