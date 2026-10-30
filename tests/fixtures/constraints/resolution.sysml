package Resolution {
  constraint def NeedsTwo {
    in alpha : Boolean;
    in beta : Boolean;
    alpha == beta
  }

  part def Marker;

  part def ResolutionComposition {
    part selected : Marker;

    constraint ghost : MissingConstraint { }
    constraint bare;
    constraint missingBinding : NeedsTwo {
      in alpha = selected;
    }

    assert ghost;
    assert bare;
    assert missingBinding;
  }
}
