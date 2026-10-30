package AnalysisOrder {
  part def SspModel;
  part def Analysis;

  variation part def SourceChoice {
    variant part step : Step;
    variant part sine : Sine;
  }

  part def Step;
  part def Sine;

  part def System :> SspModel {
    part source : SourceChoice;
  }

  part def StepSystem :> System {
    part :>> source = SourceChoice::step;
  }

  part def SineSystem :> System {
    part :>> source = SourceChoice::sine;
  }

  part def Plain :> SspModel {
    part leaf : Step;
  }

  /* Declaration order fixes the order of the per-analysis maps. */
  part def one :> Analysis {
    part sut : StepSystem;
  }

  part def second :> Analysis {
    part sut : SineSystem;
  }

  part def plain :> Analysis {
    part sut : Plain;
  }
}
