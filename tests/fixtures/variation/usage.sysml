package UsageVariation {
  part def SspModel;

  part def SignalSource;
  part def Step :> SignalSource;
  part def Sine :> SignalSource;

  part def System :> SspModel {
    variation part source : SignalSource {
      variant part stepSource : Step;
      variant part sineSource : Sine;
    }
  }
}
