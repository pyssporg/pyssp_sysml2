package Quoted {
  port def Fluid {
    attribute p : Real;
    attribute 'X[1]' : Real;
    attribute 'X[2]' : Real;
  }

  part def Source {
    out port feed : Fluid;
  }

  part def Sink {
    in port feed : Fluid;
  }

  part def System {
    part source : Source;
    part sink : Sink;
    connect source.feed to sink.feed;
  }
}
