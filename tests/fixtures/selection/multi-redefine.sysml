package MultiRedefine {
  part def SspModel;
  part def Analysis;

  variation part def SourceChoice {
    variant part step : Step;
  }

  part def Step;

  part def System :> SspModel {
    part source : SourceChoice;
    part gain : SourceChoice;
  }

  /* One usage redefines two features: no single point is bound. */
  part def BadSystem :> System {
    part both :>> source :>> gain = SourceChoice::step;
  }

  part def bad :> Analysis {
    part sut : BadSystem;
  }
}
