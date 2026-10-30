package Overridden {
  constraint def Always {
    true
  }

  constraint def Never {
    false
  }

  part def BaseRules {
    constraint inheritedRule : Always { }
    constraint { true }

    assert inheritedRule;
  }

  part def DerivedRules :> BaseRules {
    constraint inheritedRule : Never { }
    constraint ownRule : Always { }

    assert inheritedRule;
    assert ownRule;
  }

  part def OverriddenComposition {
    part rules : DerivedRules;
  }
}
