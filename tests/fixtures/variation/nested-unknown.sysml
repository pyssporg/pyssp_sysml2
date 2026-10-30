package NestedUnknown {
  part def SspModel;
  part def A;
  part def B;

  variation part def InnerChoice {
    variant part a : A;
    variant part b : B;
  }

  variation part def OuterChoice {
    variant part chosen {
      variation part inner : InnerChoice {
        variant part a : A;
        variant part b : B;
      }
    }
  }

  part def System :> SspModel {
    part outer : OuterChoice;
  }
}
