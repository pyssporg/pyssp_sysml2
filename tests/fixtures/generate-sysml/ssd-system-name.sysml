package RecoveredFromSSD {
  port def Port_1 {
    attribute x : Real;
    attribute y : Real;
  }

  part def Sink {
    in port inSig : Port_1;
  }

  part def Source {
    out port outSig : Port_1;
  }

  part def SystemComposition {
    part dst : Sink;
    part src : Source;
    connect src.outSig to dst.inSig;
  }
}
