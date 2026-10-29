# Analysis / SspModel Example

Demonstrates the `Analysis` and `SspModel` role markers:

- `PositionServo :> SspModel` is the exportable model.
- `test_baseline` and `test_aggressive` are `:> Analysis` definitions over the
  same model. Each composes it through `sut`, applies exactly one parameter
  set, and declares exactly one `Experiment`.

The model is a position servo with a `ServoAxis` system containing a `driver`
and a parameterized `plant`. Both analyses bind the applied scenario set to the
plant's parameter interface.

```text
examples/analysis/
├── part_definitions.sysml  roles, experiment, parameter interface, model
├── composition.sysml       scenario sets, experiments, analyses
└── README.md
```

## Generate analysis artifacts

```bash
pyssp generate analysis \
  --architecture examples/analysis \
  --composition test_baseline \
  --model position_servo \
  --output-dir build/generated/analyses/test_baseline

pyssp generate analysis \
  --architecture examples/analysis \
  --composition test_aggressive \
  --model position_servo \
  --output-dir build/generated/analyses/test_aggressive
```

Each run writes:

- `NominalScenario.ssv` (or `AggressiveScenario.ssv`): the applied scenario.
- `test_baseline.ssm` (or `test_aggressive.ssm`): mappings relative to the
  exported model root. The `sut.` prefix is stripped, so the targets are
  `axis.plant.inputScale`, `axis.plant.gain`, and
  `axis.plant.timeConstant`.
- `analysis.json`: the model name, composition, `sut` usage, target SSD,
  experiment window, and scenario paths.

For example, `test_baseline/analysis.json` contains:

```json
{
  "analysis": "test_baseline",
  "composition": "PositionServo",
  "experiment": {
    "name": "experiment_baseline",
    "start_time": 0.0,
    "step_size": 0.01,
    "stop_time": 10.0,
    "tolerance": 1e-06
  },
  "model": "position_servo",
  "scenario": {
    "set": "NominalScenario",
    "ssm": "test_baseline.ssm",
    "ssv": "NominalScenario.ssv"
  },
  "sut": "sut",
  "target_ssd": "SystemStructure.ssd"
}
```

`generate analysis` never writes an SSD or an SSP. Generate the model structure
separately when needed:

```bash
pyssp generate ssd \
  --architecture examples/analysis \
  --composition PositionServo \
  --output build/generated/PositionServo/SystemStructure.ssd
```

## Rules this example relies on

- The marker definitions `part def SspModel;` and `part def Analysis;` live in
  the same package.
- An analysis has exactly one `SspModel` part usage (`sut` here), one applied
  scenario set, and one attribute typed by an `Experiment`.
- `generate ssp` accepts `PositionServo` but rejects any `:> Analysis`
  composition. Packaging the model as an SSP additionally requires
  `fmu_meta.source` on each leaf component.
