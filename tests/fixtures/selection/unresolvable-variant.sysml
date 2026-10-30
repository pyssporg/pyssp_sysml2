package UnresolvableVariant {
  part def SspModel;
  part def Analysis;

  /* The variant names a type that is not declared. */
  variation part def SourceChoice {
    variant part step : MissingType;
  }

  part def System :> SspModel {
    part source : SourceChoice;
  }

  part def BadSystem :> System {
    part :>> source = SourceChoice::step;
  }

  part def bad :> Analysis {
    part sut : BadSystem;
  }
}
