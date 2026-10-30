package NonPoint {
  part def SspModel;
  part def Analysis;

  variation part def SourceChoice {
    variant part step : Step;
  }

  part def Step;
  part def Gain;

  part def System :> SspModel {
    part source : SourceChoice;
  }

  part def BadSystem :> System {
    part :>> gain = Gain;
  }

  part def bad :> Analysis {
    part sut : BadSystem;
  }
}
