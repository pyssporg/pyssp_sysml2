package Example {
  port def Signal {
    attribute x : Real;
    attribute y : Real;
  }

  part def AltSink {
    in port inSig : Signal;
  }

  part def Sink {
    in port inSig : Signal;
  }

  part def Source {
    out port outSig : Signal;
  }

  part def SystemComposition {
    part alt : AltSink;
    part dst : Sink;
    part src : Source;
    connect src.outSig to alt.inSig;
    connect src.outSig to dst.inSig;
  }
}
