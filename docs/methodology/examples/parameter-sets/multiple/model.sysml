package MultipleSetExample {
  doc /* Two disjoint sets applied to one component. */

  attribute def ParameterInterface;
  attribute def ParameterSet;

  attribute def ControllerParameters :> ParameterInterface {
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
    attribute parameters : ControllerParameters;
  }

  part def MultipleSetComposition {
    part controller : Controller;

    attribute counts : Counts;
    attribute gains : Gains;

    bind counts.n = controller.parameters.count;
    bind gains.k = controller.parameters.gain;
  }
}
