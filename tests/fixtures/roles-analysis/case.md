# Case: `roles-analysis`

The SysML inputs for analysis generation and role marking.

## Artifacts

| Path | Kind |
| --- | --- |
| `architecture.sysml` | Input |
| `experiment-only.sysml` | Input, `.replace()`d by two tests |
| `model-owned-scenario.sysml` | Input, `.replace()`d by one test |

No expected artifact: the tests inspect the analysis descriptor JSON, the emitted
SSV/SSM, the exported SysML text, or the raised error.

## What this case proves

`architecture.sysml` carries both roles (`:> SspModel`, `:> Analysis`), a scenario
set, and an analysis-owned parameter bind, so it proves role detection, SysML
export/round-trip of specializations, and that an analysis scenario reaches the SSM
as `leaf.k`, not `sut.leaf.k`. `experiment-only.sysml` has no scenario and
proves an experiment-only descriptor; one test rewrites it in memory to insert a
`doc` and prove the analysis body becomes the descriptor description.
`model-owned-scenario.sysml` proves a scenario owned by the model produces no
analysis SSV/SSM, and the `.replace()`d variant adds an analysis-owned scenario to
prove the conflict is rejected. The replace calls are the case: they are the
smallest edit that turns one document into the near-miss variant.

Origin: module-level literals in `tests/test_roles_analysis.py`; they were already
written verbatim, so the fixture bytes are the literal bytes.

## Update history

| Date | Change | Reason |
| --- | --- | --- |
| 2026-10-28 | Moved out of `tests/test_roles_analysis.py` | Documents belong in files; the derived variants stay `.replace()` edits |
