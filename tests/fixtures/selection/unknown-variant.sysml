package UnknownVariant {
  part def SspModel;
  part def Analysis;

  variation part def SourceChoice {
    variant part step : Step;
  }

  part def Step;

  part def System :> SspModel {
    part source : SourceChoice;
  }

  part def BadSystem :> System {
    part :>> source = SourceChoice::missing;
  }

  part def bad :> Analysis {
    part sut : BadSystem;
  }
}
