package Expressions {
  constraint def ImpliesAssociates { false implies true implies false }
  constraint def ImpliesVacuous { false implies false }
  constraint def Parentheses { (false implies false) implies false }
  constraint def EscapedString { "a\"b" == "a\"b" }
  constraint def TypeMember { Choice::on == "on" }
  constraint def TrueLiteral { true }
  constraint def FalseLiteral { false }
  constraint def NonBooleanOperand { "x" and true }
  constraint def NonBooleanValue { Choice::on }
  constraint def NotBindsTighterThanEquality { not "a" == "b" }
  constraint def AndOverOr { false and true or true }
  constraint def OrOverXor { true xor false or true }
  constraint def XorOverAnd { true xor false and false }
  constraint def NonBooleanRightOr { true or "x" }
  constraint def NonBooleanRightAnd { false and "x" }
  constraint def NonBooleanRightXor { true xor "x" }
  constraint def NonBooleanRightImplies { false implies "x" }

  part def Marker;

  part def ExpressionsComposition {
    part selected : Marker;

    constraint impliesAssociates : ImpliesAssociates { }
    constraint impliesVacuous : ImpliesVacuous { }
    constraint parentheses : Parentheses { }
    constraint escapedString : EscapedString { }
    constraint typeMember : TypeMember {
      in Choice = selected;
    }
    constraint trueLiteral : TrueLiteral { }
    constraint falseLiteral : FalseLiteral { }
    constraint nonBooleanOperand : NonBooleanOperand { }
    constraint nonBooleanValue : NonBooleanValue { }
    constraint notBindsTighterThanEquality : NotBindsTighterThanEquality { }
    constraint andOverOr : AndOverOr { }
    constraint orOverXor : OrOverXor { }
    constraint xorOverAnd : XorOverAnd { }
    constraint nonBooleanRightOr : NonBooleanRightOr { }
    constraint nonBooleanRightAnd : NonBooleanRightAnd { }
    constraint nonBooleanRightXor : NonBooleanRightXor { }
    constraint nonBooleanRightImplies : NonBooleanRightImplies { }

    assert impliesAssociates;
    assert impliesVacuous;
    assert parentheses;
    assert escapedString;
    assert typeMember;
    assert trueLiteral;
    assert falseLiteral;
    assert nonBooleanOperand;
    assert nonBooleanValue;
    assert notBindsTighterThanEquality;
    assert andOverOr;
    assert orOverXor;
    assert xorOverAnd;
    assert nonBooleanRightOr;
    assert nonBooleanRightAnd;
    assert nonBooleanRightXor;
    assert nonBooleanRightImplies;
  }
}
