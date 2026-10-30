package ConfigurationValues {
  part def System;

  variation part def SourceChoice {
    variant part step : System;
  }

  variation part def PathChoice {
    variant part nestedPath;
  }

  part def ValueForms :> System {
    part :>> qualified = SourceChoice::step;
    part :>> local = qualified;
    part choice :> PathChoice::nestedPath;
    part :>> combined :> PathChoice::nestedPath = SourceChoice::step;
  }

  /* Two targets name nothing: the walker skips the extras instead of guessing. */
  part def Ambiguous :> System {
    part :>> alpha, beta : System = SourceChoice::step;
  }
}
