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
    variant part twoStages : Gain;
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

  /* Simple structural configuration; it inherits the family's assert. */
  part def StepSingleSystem :> System {
    part :>> source = SourceChoice::stepImplementation;
    part :>> gain = GainChoice::singleStage;
  }

  /* Conditional configuration: same inherited constraint, an illegal pair. */
  part def SineTwoSystem :> System {
    part :>> source = SourceChoice::sineImplementation;
    part :>> gain = GainChoice::twoStages;
  }

  part def step_single :> Analysis {
    attribute experiment : BaselineExperiment;
    part sut : StepSingleSystem;
  }

  part def sine_two :> Analysis {
    attribute experiment : BaselineExperiment;
    part sut : SineTwoSystem;
  }

  /* Composes the root composition: its points stay unbound. */
  part def broken :> Analysis {
    attribute experiment : BaselineExperiment;
    part sut : System;
  }

  variation part def PathChoice {
    variant part directPath : DirectPath;
    variant part nestedPath : NestedPath;
  }

  part def DirectPath;

  variation part def StageChoice {
    variant part gainStage : Gain;
    variant part unityStage : Gain;
  }

  /* The nested point exists only inside the selected variant's type. */
  part def NestedPath {
    part inner_stage : StageChoice;
  }

  part def PathSystem :> SspModel {
    part path : PathChoice;
  }

  part def NestedGainSystem :> PathSystem {
    part nestedGainPath :> PathChoice::nestedPath {
      part :>> inner_stage = StageChoice::gainStage;
    }
    part :>> path = nestedGainPath;
  }

  /* Selects the outer variant but leaves the inner point unbound. */
  part def NestedUnboundSystem :> PathSystem {
    part :>> path = PathChoice::nestedPath;
  }

  part def nested_gain :> Analysis {
    attribute experiment : BaselineExperiment;
    part sut : NestedGainSystem;
  }

  part def nested_unbound :> Analysis {
    attribute experiment : BaselineExperiment;
    part sut : NestedUnboundSystem;
  }

  attribute def ScenarioK3;
  attribute def ScenarioK5;

  variation attribute def ScenarioChoice {
    variant attribute nominalK3 : ScenarioK3;
    variant attribute nominalK5 : ScenarioK5;
  }

  part def PlainSystem :> SspModel {
    part leaf : Gain;
  }

  /* Analysis-local attribute point: the value binds it without a configuration. */
  part def nominal :> Analysis {
    attribute experiment : BaselineExperiment;
    attribute scenario : ScenarioChoice = ScenarioChoice::nominalK3;
    part sut : PlainSystem;
  }

  /* Composes the plain root: derives an empty selection. */
  part def plain :> Analysis {
    attribute experiment : BaselineExperiment;
    part sut : PlainSystem;
  }
}
