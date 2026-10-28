package RecoveredFromSSD {
  port def Port_1 {
    attribute Aircraft_State : Integer;
    attribute TLiquid : Real;
  }

  part def EnumMix {
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
