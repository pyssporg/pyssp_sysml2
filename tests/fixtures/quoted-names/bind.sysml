package QuotedEnds {
  port def Parameters {
    attribute 'pipeA.L' : Real;
  }

  part def Block {
    in port parameters : Parameters;
  }

  part def System {
    attribute nominal : Scenario;
    part block : Block;
    bind block.parameters.'pipeA.L' = nominal.'pipeA.L';
  }

  attribute def Scenario {
    attribute 'pipeA.L' : Real;
  }
}
