package ResolutionOrder {
  part def SspModel;
  part def A;
  part def B;

  part def Inner {
    variation part y : A {
      variant part a : A;
      variant part b : B;
    }
  }

  part def System :> SspModel {
    variation part x : A {
      variant part a : A;
      variant part b : B;
    }
    part inner : Inner;
  }
}
