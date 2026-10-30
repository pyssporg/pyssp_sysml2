package Selection {
  part def SspModel;
  part def Analysis;

  attribute def Experiment {
    attribute startTime : Real;
    attribute stopTime : Real;
    attribute stepSize : Real;
  }

  attribute def BaselineExperiment :> Experiment {
    attribute startTime = 0.0;
    attribute stopTime = 1.0;
    attribute stepSize = 0.001;
  }

  variation part def SourceChoice {
    variant part stepImplementation : Step;
    variant part sineImplementation : Sine;
  }

  variation part def GainChoice {
    variant part singleStage : Gain;
    variant part twoStage : Gain;
  }

  part def Step;
  part def Sine;
  part def Gain;

  constraint def SineRequiresSingleStage {
    in chosenSource : SourceChoice;
    in chosenGain : GainChoice;
    chosenSource == SourceChoice::sineImplementation implies
      chosenGain == GainChoice::singleStage
  }

  part def System :> SspModel {
    part source : SourceChoice;
    part gain : GainChoice;

    constraint requiresSingleStage : SineRequiresSingleStage {
      in chosenSource = source;
      in chosenGain = gain;
    }
    assert requiresSingleStage;
  }

  part def step_single :> Analysis {
    attribute pyssp_selection = "source=stepImplementation;gain=singleStage";
    attribute experiment : BaselineExperiment;
    part sut : System;
  }

  part def sine_two :> Analysis {
    attribute pyssp_selection = "source=sineImplementation;gain=twoStage";
    attribute experiment : BaselineExperiment;
    part sut : System;
  }

  part def broken :> Analysis {
    attribute pyssp_selection = "source";
    attribute experiment : BaselineExperiment;
    part sut : System;
  }

  part def missing :> Analysis {
    attribute experiment : BaselineExperiment;
    part sut : System;
  }
}
