# Case: `identity`

The fixture record for this directory. It says what the bytes cannot: why the
case exists, which oracle proves it, and how the output may be normalized.

- **Conversion:** `architecture.sysml` (SysML v2) → `SystemStructure.ssd`,
  `parameter_sets/*.ssv`, `*_*.ssm`, `<Component>/modelDescription.xml`
- **Requirement / fault:** a whole-object bind must reach the SSD as a
  `ParameterBinding` with its `prefix` and no per-member mapping, and a
  per-member bind must reach it as an explicit `MappingEntry`. Dropping either
  changes what an SSP tool binds at load time, without any document becoming
  invalid.
- **Level:** component
- **Input:** `architecture.sysml` — synthetic, authored for this case
  (package `IdentityGolden`, composition `IdentityComposition`); no external
  source, no licence obligation
- **Expected:** the committed artifacts listed under *Artifacts* below
- **Independent oracle:** `pyssp_standard` facade — `SSD`, `SSV`, `SSM`,
  `ModelDescription` re-parse each document and run `check_compliance()` (XSD
  plus semantic validators). The writer is this repository; the checker is not.
- **Comparison:** exact bytes against the committed file (unified diff on
  mismatch), plus parsed structure through the facade for both the generated and
  the committed copy
- **Normalization:** none; the writer is deterministic, and the only clock
  value, `generationDateAndTime`, is pinned to `GENERATION_TIME`
  (`2026-01-01T00:00:00Z`)
- **Volatile fields:** none. `guid` is `uuid5` of `pyssp_sysml2/<package>/<part>`,
  not random; `generationDateAndTime` is pinned by the test.
- **Update policy:** `UPDATE_GOLDENS=1`, read the diff, commit inputs and outputs
  together; refused when `CI` is set
- **Notes:** two components and two parameter sets, so one case exercises both
  binding forms side by side. It is the minimal fixture that distinguishes them.

## Artifacts

Generated from `architecture.sysml`; every path is relative to this directory.

| Path | Kind |
| --- | --- |
| `SystemStructure.ssd` | SSD system structure, both binding forms |
| `parameter_sets/GainSet.ssv` | SSV, bound whole-object with the gain prefix |
| `parameter_sets/ControllerSet.ssv` | SSV, bound member by member |
| `ControllerSet_controller.ssm` | SSM, explicit mapping for `controller` |
| `Gain/modelDescription.xml` | FMI 2.0 model description for `Gain` |
| `Controller/modelDescription.xml` | FMI 2.0 model description for `Controller` |

`architecture.sysml` and this file are inputs and provenance, not goldens.

## What this case proves

If the case is deleted, a regression that stops emitting the whole-object
`prefix` (or that expands it into per-member entries) escapes: the remaining
case only covers per-member binds, and every document would still validate.

## Update history

| Date | Change | Reason |
| --- | --- | --- |
| 2026-10-28 | Case record added | The goldens existed with no per-case provenance; bytes unchanged |
