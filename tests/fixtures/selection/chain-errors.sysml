package ChainErrors {
  part def SspModel;
  part def Analysis;

  variation part def SourceChoice {
    variant part step : Step;
  }

  part def Step;

  part def FirstRoot :> SspModel {
    part source : SourceChoice;
  }

  part def SecondRoot :> SspModel;

  /* Specialises two SspModel definitions: the chain is not linear. */
  part def Linear :> FirstRoot, SecondRoot {
    part :>> source = SourceChoice::step;
  }

  part def linear :> Analysis {
    part sut : Linear;
  }

  part def Helper;

  /* Its only supertype is not marked SspModel. */
  part def Orphan :> Helper;
}
