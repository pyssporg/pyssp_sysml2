package AttributeVariation {
  part def SspModel;
  variation attribute def Scale;

  part def System :> SspModel {
    attribute gain : Scale;
  }
}
