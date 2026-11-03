package Quoted {
  port def Fluid {
    attribute 'X[1]' : Real;
    attribute 'part' : Real;
    attribute p : Real;
  }

  part def Consumer {
    out port feed : Fluid;
  }

  part def EcsHw {
    in port feed : Fluid;
  }

  part def 'System.Top' {
    part consumer : Consumer;
    part hw : EcsHw;
    connect consumer.feed to hw.feed;
  }
}
