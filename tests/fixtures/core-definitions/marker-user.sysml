package MarkerUser {
  part def MarkerSystem :> SspModel {
    part src : Source;
    part dst : Sink;
    connect src.outSig to dst.inSig;
  }

  port def Signal {
    attribute x: Real;
  }

  part def Source {
    out port outSig : Signal;
  }

  part def Sink {
    in port inSig : Signal;
  }
}
