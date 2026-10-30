package AmbiguousNested {
  part def SspModel;
  part def Leaf;

  part def Inner {
    part x : Leaf;
  }

  part def Mid {
    part inner : Inner;
  }

  part def System :> SspModel {
    part a : Mid;
    part b : Mid;
  }
}
