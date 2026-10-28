package AmbiguousNames {
  part def SspModel;
  part def Leaf;

  part def Nested {
    part x : Leaf;
  }

  part def System :> SspModel {
    part x : Leaf;
    part inner : Nested;
  }
}
