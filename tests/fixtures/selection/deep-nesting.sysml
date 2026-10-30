package DeepNesting {
  part def SspModel;
  part def Analysis;

  variation part def AChoice {
    variant part a : A;
    variant part b : B;
  }

  part def A;

  variation part def BChoice {
    variant part b1 : B1;
    variant part b2 : B2;
  }

  part def B {
    part inner : BChoice;
  }

  part def B1 {
    part deeper : CChoice;
  }

  part def B2;

  variation part def CChoice {
    variant part c1 : C1;
    variant part c2 : C2;
  }

  part def C1;
  part def C2;

  part def Root :> SspModel {
    part top : AChoice;
  }

  part def Config :> Root {
    part localB :> AChoice::b {
      part :>> inner = BChoice::b1 {
        part :>> deeper = CChoice::c1;
      }
    }
    part :>> top = localB;
  }

  part def deep :> Analysis {
    part sut : Config;
  }
}
