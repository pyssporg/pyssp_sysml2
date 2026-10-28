package RecoveredFromSSD {
  port def Port_1 {
    attribute value : Real;
  }

  part def ScalarGroup {
    part dst : Sink;
    part src : Source;
    connect src.signal to dst.signal;
  }

  part def Sink {
    in port signal : Port_1;
  }

  part def Source {
    out port signal : Port_1;
  }
}
