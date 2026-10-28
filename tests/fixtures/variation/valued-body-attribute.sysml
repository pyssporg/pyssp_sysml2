package ValuedBodyAttribute {
  part def SspModel;
  attribute def Values {
    attribute x = 1.0;
  }
  part def Marker;

  part def System :> SspModel {
    variation part parameters : Marker {
      variant part chosen {
        attribute values : Real = 1.0;
      }
    }
  }
}
