package Example {
  part def SystemComposition {
    part dst : Sink;
    part src : Source;
  }
}

package Example {
  part def Sink {
    in port inSig : Signal;
  }

  part def Source {
    out port outSig : Signal;
  }

  part def Utility {
    out port debug : DebugSignal;
  }
}

package Example {
  port def DebugSignal {
    attribute level : Integer;
  }

  port def Signal {
    attribute x : Real;
    attribute y : Real;
  }
}
