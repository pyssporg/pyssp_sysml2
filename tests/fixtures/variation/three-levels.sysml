package ThreeLevels {
  part def SspModel;

  part def Step;
  part def Gain;

  variation part def DeepChoice {
    variant part leafGain : Gain;
  }

  variation part def StageChoice {
    variant part stepStage : Step;
    variant part deepStage {
      variation part deep : DeepChoice;
    }
  }

  variation part def PathChoice {
    variant part nestedPath {
      variation part stage : StageChoice {
        variant part stepStage : Step;
        variant part deepStage {
          variation part deep : DeepChoice;
        }
      }
    }
  }

  part def System :> SspModel {
    part path : PathChoice;
  }
}
