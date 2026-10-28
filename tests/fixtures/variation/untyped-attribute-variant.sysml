package UntypedAttributeVariant {
  part def SspModel;

  variation attribute def Choice {
    variant attribute empty;
  }

  part def System :> SspModel {
    attribute value : Choice;
  }
}
