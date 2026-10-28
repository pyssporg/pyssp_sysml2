package NestedVariation {
  part def SspModel;
  part def A;
  part def B;

  variation part def Choice {
    variant part a : A;
    variant part b : B;
  }

  part def Inner {
    part source : Choice;
  }

  part def System :> SspModel {
    part inner : Inner;
  }
}
