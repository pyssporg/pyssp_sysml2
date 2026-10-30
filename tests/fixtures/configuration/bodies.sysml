package ConfigurationBodies {
  part def System;

  part def Gain;

  part def TwoLevels :> System {
    part :>> outer : System {
      part :>> middle : System {
        part :>> inner : System;
      }
    }
  }

  part def Renamed :> System {
    part holder : System {
      part :>> bound : System;
    }
  }

  part def Wired :> System {
    part src : System {
      part a : Gain;
      part b : Gain;
      connect a.y to b.u;
      bind a.x = b.y;
      attribute :>> mode : Integer;
      attribute extra : Integer;
    }
  }
}
