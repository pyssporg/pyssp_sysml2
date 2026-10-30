package Negated {
  constraint def RequiresOn {
    chosen == ModeChoice::on
  }

  variation part def ModeChoice {
    variant part on;
    variant part off;
  }

  part def NegatedComposition {
    part selected : ModeChoice;

    constraint mustBeOff : RequiresOn {
      in chosen = selected;
    }

    assert not mustBeOff;
  }
}
