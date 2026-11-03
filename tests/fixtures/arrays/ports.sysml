package Arrays {
  port def RealSignal {
    attribute pyssp_flat_connector : Boolean = true;
    attribute value : Real;
  }

  part def Source {
    out port 'feed.X' : RealSignal[3];
  }

  part def Sink {
    in port 'feed.X' : RealSignal[3];
  }

  part def System {
    part source : Source;
    part sink : Sink;
    connect source.'feed.X' to sink.'feed.X';
  }
}
