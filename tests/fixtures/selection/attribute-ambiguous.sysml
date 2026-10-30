package AttributeAmbiguous {
  part def SspModel;

  part def Leaf {
    attribute mode : Real;
  }

  part def Nested {
    part x : Leaf;
  }

  part def System :> SspModel {
    attribute mode : Real;
    part inner : Nested;
  }
}
