package MemberRules {
  part def SspModel;
  part def Gain;
  attribute def Weight;
  part def Marker;

  variation part def BothChoice {
    variant part both : Gain {
      part g : Gain;
    }
  }

  part def BothSystem :> SspModel {
    part point : BothChoice;
  }

  variation part def EmptyChoice {
    variant part empty;
  }

  part def EmptySystem :> SspModel {
    part point : EmptyChoice;
  }

  variation part def WrongTypeChoice {
    variant part wrong : Weight;
  }

  part def WrongTypeSystem :> SspModel {
    part point : WrongTypeChoice;
  }

  part def NoVariantsSystem :> SspModel {
    variation part point : Marker;
  }

  variation attribute def EmptyScale;

  part def AttributeSystem :> SspModel {
    attribute gain : EmptyScale;
  }
}
