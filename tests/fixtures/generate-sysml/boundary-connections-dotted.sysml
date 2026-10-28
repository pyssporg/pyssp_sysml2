package RecoveredFromSSD {
  port def Port_1 {
    attribute value : Real;
  }

  part def Boundary {
    out port y : Port_1;
    part inner : inner;
    connect inner.v to y;
  }

  part def Sink {
    out port sig : Port_1;
    in port sigIn : Port_1;
  }

  part def Source {
    out port sig : Port_1;
  }

  part def inner {
    in port u : Port_1;
    out port v : Port_1;
    part dst : Sink;
    part src : Source;
    connect u to src.sig;
    connect dst.sig to v;
    connect src.sig to dst.sigIn;
  }
}
