    package Ports {
      $markers

      $interface_decl {
        $interface_members
      }

      attribute def Nom :> ParameterSet {
        attribute gain_value = 3.0;
        attribute n = 7;
        attribute xs_value = (1.0, 2.0);
      }

      part def Comp {
        $port
      }

      part def $COMPOSITION_NAME {
        part comp : Comp;
        attribute nominal : Nom;
        bind comp.parameters.gain = nominal.gain_value;
        bind comp.parameters.count = nominal.n;
        bind comp.parameters.xs = nominal.xs_value;
      }
    }
