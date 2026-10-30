package Rebinding {
  part def SspModel;
  part def Analysis;

  variation part def PathChoice {
    variant part directPath : DirectPath;
    variant part nestedPath : NestedPath;
  }

  part def DirectPath;

  variation part def StageChoice {
    variant part gainStage : Gain;
  }

  part def Gain;

  part def NestedPath {
    part inner : StageChoice;
  }

  part def Root :> SspModel {
    part path : PathChoice;
  }

  part def Nested :> Root {
    part :>> path = PathChoice::nestedPath {
      part :>> inner = StageChoice::gainStage;
    }
  }

  /* Rebinds the point an ancestor configuration already bound. */
  part def Direct :> Nested {
    part :>> path = PathChoice::directPath;
  }

  part def direct :> Analysis {
    part sut : Direct;
  }
}
