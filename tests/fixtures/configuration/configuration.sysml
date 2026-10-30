package Configuration {
  part def System;

  part def Analysis;

  part def Step;

  part def Gain;

  variation part def SourceChoice {
    variant part step : Step;
  }

  variation part def StageChoice {
    variant part gainStage : Gain;
  }

  variation part def PathChoice {
    variant part nestedPath;
  }

  variation attribute def ScenarioChoice {
    variant attribute nominalK3;
  }

  /* Simple configuration: a 100% binding of the source variation usage. */
  part def StepSystem :> System {
    part :>> source = SourceChoice::step;
  }

  /* Nested configuration: the outer usage specializes the path variant and
     its body binds the inner variation usage. */
  part def NestedGainSystem :> System {
    part nestedGainPath :> PathChoice::nestedPath {
      part :>> inner_stage = StageChoice::gainStage;
      part gain : Gain {
        part sub : Step;
      }
      attribute :>> mode : Integer;
      connect inner_stage.y to gain.u;
    }
    part :>> path = nestedGainPath;
  }

  /* Analysis-local scenario binding, once by name and once by redefinition. */
  part def nominal :> Analysis {
    part sut : System;
    attribute scenario : ScenarioChoice = ScenarioChoice::nominalK3;
  }

  part def nominalRedefined :> nominal {
    attribute :>> scenario = ScenarioChoice::nominalK3;
  }
}
