# Case: `mapping`

The fixture record for this directory. It says what the bytes cannot: why the
case exists, which oracle proves it, and how the output may be normalized.

- **Conversion:** `architecture.sysml` (SysML v2) → `SystemStructure.ssd`,
  `parameter_sets/*.ssv`, `*_*.ssm`, `<Component>/modelDescription.xml`
- **Requirement / fault:** a per-member bind on a fixed-length list must expand
  into one `MappingEntry` and one SSD connector per index (`waypoints_x_km[0]`,
  `waypoints_x_km[1]`). Collapsing the list to a single entry, or losing the
  index suffix, changes the target an SSP tool binds while every document still
  validates.
- **Level:** component
- **Input:** `architecture.sysml` — synthetic, authored for this case
  (package `MappingGolden`, composition `MappingComposition`); no external
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
- **Notes:** one component, one parameter set, one list of length two — the
  smallest fixture that shows list expansion and index preservation.

## Artifacts

Generated from `architecture.sysml`; every path is relative to this directory.

| Path | Kind |
| --- | --- |
| `SystemStructure.ssd` | SSD system structure, indexed mapping entries |
| `parameter_sets/NominalSet.ssv` | SSV, the mapped source values |
| `NominalSet_autopilot.ssm` | SSM, explicit mapping for `autopilot` |
| `AutopilotModule/modelDescription.xml` | FMI 2.0 model description for `AutopilotModule` |

`architecture.sysml` and this file are inputs and provenance, not goldens.

## What this case proves

If the case is deleted, a regression in fixed-length list expansion — the
`[0]`/`[1]` suffix on connectors, mapping entries, and parameter values — has no
remaining coverage: the other case only binds scalars, and the collapsed output
would still pass the facade validator.

## Update history

| Date | Change | Reason |
| --- | --- | --- |
| 2026-10-28 | Case record added | The goldens existed with no per-case provenance; bytes unchanged |
