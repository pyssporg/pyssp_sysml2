# Conversion goldens

Each directory is one case: a small SysML v2 architecture plus the SSP/FMI
artifacts generated from it. They are the regression gate for the generator
output itself, in two independent ways:

1. **Independent validator.** Every produced document is re-read through the
   `pyssp_standard` facade (`SSD`, `SSV`, `SSM`, `ModelDescription`) and
   validated with `check_compliance()`, which runs the registered XSD and
   semantic validators. The writer is this repository; the checker is not.
2. **Exact bytes.** Each produced file must equal its committed golden
   byte-for-byte. A changed attribute, a reordered element, or an extra
   document fails the test with a unified diff.

## Cases

| Case       | Composition           | Covers                                                        |
| ---------- | --------------------- | ------------------------------------------------------------- |
| `identity` | `IdentityComposition` | whole-object bind (SSD `ParameterBinding` prefix), per-member SSM for a second component, two components |
| `mapping`  | `MappingComposition`  | per-member binds, fixed-length list expansion into `[0]`/`[1]` entries |

Both cases produce all four artifact kinds: `SystemStructure.ssd`, one `.ssv`
per parameter set, one `.ssm` per explicit set/component mapping, and one
`<Component>/modelDescription.xml` per leaf component.

Layout inside a case directory mirrors a built SSP runtime, so an SSD
`source="parameter_sets/<Set>.ssv"` resolves inside the case:

```
<case>/
  architecture.sysml            input, not a golden
  SystemStructure.ssd           SSD artifact
  parameter_sets/<Set>.ssv      one per applied parameter set
  <Set>_<component>.ssm         one per explicit mapping
  <Component>/modelDescription.xml
```

`modelDescription.xml` carries `generationDateAndTime`, so the golden test
passes a frozen `GENERATION_TIME` (2026-01-01T00:00:00Z). Keep that constant and
the goldens in sync when regenerating.

## Regenerating

```bash
UPDATE_GOLDENS=1 python -m pytest tests/test_golden_artifacts.py
```

Then **review the diff**, and commit the inputs with the outputs:

- read every changed line: a golden change is a contract change, not a test fix;
- confirm the change is intended (dialect, mapping rules, version, ordering);
- never regenerate to silence a failure you have not explained.

Regeneration is a developer action only. It must never run in CI: CI runs the
test without `UPDATE_GOLDENS` set, so a mismatch fails the build.

Adding a case: create `<case>/architecture.sysml`, add the directory to `CASES`
in `tests/test_golden_artifacts.py` with its composition name, then regenerate
and review.
