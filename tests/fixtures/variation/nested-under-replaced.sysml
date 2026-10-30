package NestedUnderReplaced {
  part def SspModel;
  part def A;
  part def B;
  part def Gain;

  variation part def StageChoice {
    variant part a : A;
    variant part b : B;
  }

  variation part def OuterChoice {
    variation part astage : StageChoice {
      variant part a : A;
      variant part b : B;
    }

    variant part plain {
      part gain : Gain;
    }
  }

  part def System :> SspModel {
    part zpath : OuterChoice;
  }
}
