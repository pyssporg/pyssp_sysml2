package BindingErrors {
  part def SspModel;
  part def Analysis;

  variation part def SourceChoice {
    variant part step : Step;
    variant part sine : Sine;
  }

  variation part def OtherChoice {
    variant part thing : Thing;
  }

  part def Step;
  part def Sine;
  part def Thing;

  part def System :> SspModel {
    part source : SourceChoice;
  }

  /* Qualified value names another point's definition. */
  part def WrongTypeSystem :> System {
    part :>> source = OtherChoice::thing;
  }

  /* Unqualified value names no local usage. */
  part def NoLocalSystem :> System {
    part :>> source = missingUsage;
  }

  /* The local usage specialises no variant. */
  part def NoSubsetSystem :> System {
    part local;
    part :>> source = local;
  }

  /* The local usage specialises two variants. */
  part def TwoSubsetSystem :> System {
    part local :> SourceChoice::step, SourceChoice::sine;
    part :>> source = local;
  }

  /* The local usage specialises a member of a different point. */
  part def NotVariantSystem :> System {
    part local :> OtherChoice::thing;
    part :>> source = local;
  }

  part def wrong_type :> Analysis {
    part sut : WrongTypeSystem;
  }

  part def no_local :> Analysis {
    part sut : NoLocalSystem;
  }

  part def no_subset :> Analysis {
    part sut : NoSubsetSystem;
  }

  part def two_subsets :> Analysis {
    part sut : TwoSubsetSystem;
  }

  part def not_variant :> Analysis {
    part sut : NotVariantSystem;
  }
}
