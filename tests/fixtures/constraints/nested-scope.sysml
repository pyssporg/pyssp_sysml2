package NestedScope {
  constraint def RequiresOn {
    in chosen : Boolean;
    chosen == ModeChoice::on
  }

  variation part def ModeChoice {
    variant part on;
    variant part off;
  }

  part def Leaf {
    part selected : ModeChoice;

    constraint innerAssertion : RequiresOn {
      in chosen = selected;
    }

    assert innerAssertion;
  }

  part def Mid {
    part inner : Leaf;
  }

  part def NestedComposition {
    part sut : Mid;
  }
}
