// Golden case: one whole-object (identity) bind plus one per-member mapping.
// Regenerate with UPDATE_GOLDENS=1; review every changed byte (see README.md).
package IdentityGolden {
  port def ParameterInterface;
  attribute def ParameterSet;

  port def Signal {
    attribute value : Real;
  }

  port def GainParameters :> ParameterInterface {
    attribute k : Real;
    attribute enabled : Boolean;
  }

  port def ControllerParameters :> ParameterInterface {
    attribute count : Integer;
  }

  attribute def GainSet :> ParameterSet {
    attribute k = 3.0;
    attribute enabled = true;
  }

  attribute def ControllerSet :> ParameterSet {
    attribute count = 5;
  }

  part def Gain {
    in port parameters : GainParameters;
    in port u : Signal;
    out port y : Signal;
  }

  part def Controller {
    in port parameters : ControllerParameters;
    in port u : Signal;
    out port y : Signal;
  }

  part def IdentityComposition {
    attribute gain_set : GainSet;
    attribute controller_set : ControllerSet;
    part gain : Gain;
    part controller : Controller;
    bind gain.parameters = gain_set;
    bind controller.parameters.count = controller_set.count;
  }
}
