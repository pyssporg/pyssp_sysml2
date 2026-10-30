package ConfigurationErrors {
  part def System;

  /* A port usage is not one of the members a configuration body carries. */
  part def Boundary :> System {
    part holder : System {
      port p : System;
    }
  }
}
