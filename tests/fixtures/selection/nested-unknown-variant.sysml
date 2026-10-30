package NestedUnknownVariant {
  part def SspModel;
  part def Analysis;

  variation part def AChoice {
    variant part a : A;
    variant part b : B;
  }

  part def A;

  variation part def BChoice {
    variant part b1 : B1;
  }

  part def B1;

  part def B {
    part inner : BChoice;
  }

  part def Root :> SspModel {
    part top : AChoice;
  }

  /* The unknown variant is bound inside the selected variant's body. */
  part def Config :> Root {
    part :>> top = AChoice::b {
      part :>> inner = BChoice::missing;
    }
  }

  part def conf :> Analysis {
    part sut : Config;
  }
}
