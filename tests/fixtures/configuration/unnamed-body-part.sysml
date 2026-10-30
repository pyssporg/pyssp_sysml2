package ConfigurationErrors {
  part def System;

  /* An anonymous body part with no redefinition target has no name at all. */
  part def Anonymous :> System {
    part holder : System {
      part : System;
    }
  }
}
