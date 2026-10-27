package MultipleSetExample {
  doc /* Two disjoint sets applied to one component. */

  port def ParameterInterface;
  attribute def ParameterSet;

  port def ControllerParameters :> ParameterInterface {
    attribute count : Integer;
    attribute gain : Real;
  }

  attribute def Counts :> ParameterSet {
    attribute n = 10;
  }

  attribute def Gains :> ParameterSet {
    attribute k = 2.5;
  }

  part def Controller {
    in port parameters : ControllerParameters;
  }

  part def MultipleSetComposition {
    part controller : Controller;

    attribute counts : Counts;
    attribute gains : Gains;

    bind controller.parameters.count = counts.n;
    bind controller.parameters.gain = gains.k;
  }
}
