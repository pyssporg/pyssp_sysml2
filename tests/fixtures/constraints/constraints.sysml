package Constraints {
  constraint def SineRequiresSingleStage {
    chosenSource == SourceChoice::sineImplementation implies chosenGain == GainChoice::singleStage
  }

  variation part def SourceChoice {
    variant part sineImplementation : SineSource;
    variant part stepImplementation : StepSource;
  }

  variation part def GainChoice {
    variant part singleStage : SingleStageGain;
    variant part twoStage : TwoStageGain;
  }

  part def SineSource;
  part def StepSource;
  part def SingleStageGain;
  part def TwoStageGain;

  part def ConstrainedComposition {
    part source : SourceChoice;
    part gain : GainChoice;

    constraint requiresSingleStage : SineRequiresSingleStage {
      in chosenSource = source;
      in chosenGain = gain;
    }

    constraint advisorySingleStage : SineRequiresSingleStage {
      in chosenSource = source;
      in chosenGain = gain;
    }

    assert requiresSingleStage;
  }
}
