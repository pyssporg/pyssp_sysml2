    package Example {
      port def ParameterInterface;
      attribute def ParameterSet;
      port def Params :> ParameterInterface {
        attribute count : Integer;
        attribute gain : Real;
      }
      attribute def Counts :> ParameterSet { attribute n = 10; }
      attribute def Gains :> ParameterSet { attribute k = 2.5; }
      part def Comp { in port parameters : Params; }
      part def $COMPOSITION_NAME {
        part comp : Comp;
        attribute counts : Counts;
        attribute gains : Gains;
        bind comp.parameters.count = counts.n;
        bind comp.parameters.gain = gains.k;
      }
    }
