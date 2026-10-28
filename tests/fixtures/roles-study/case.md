# Case: `roles-study`

The SysML inputs for study generation and role marking.

## Artifacts

| Path | Kind |
| --- | --- |
| `architecture.sysml` | Input |
| `experiment-only.sysml` | Input, `.replace()`d by two tests |
| `model-owned-scenario.sysml` | Input, `.replace()`d by one test |

No expected artifact: the tests inspect the study descriptor JSON, the emitted
SSV/SSM, the exported SysML text, or the raised error.

## What this case proves

`architecture.sysml` carries both roles (`:> SspModel`, `:> Study`), a scenario
set, and a study-owned parameter bind, so it proves role detection, SysML
export/round-trip of specializations, and that a study scenario reaches the SSM
as `leaf.k`, not `sut.leaf.k`. `experiment-only.sysml` has no scenario and
proves an experiment-only descriptor; one test rewrites it in memory to insert a
`doc` and prove the study body becomes the descriptor description.
`model-owned-scenario.sysml` proves a scenario owned by the model produces no
study SSV/SSM, and the `.replace()`d variant adds a study-owned scenario to
prove the conflict is rejected. The replace calls are the case: they are the
smallest edit that turns one document into the near-miss variant.

Origin: module-level literals in `tests/test_roles_study.py`; they were already
written verbatim, so the fixture bytes are the literal bytes.

## Update history

| Date | Change | Reason |
| --- | --- | --- |
| 2026-10-28 | Moved out of `tests/test_roles_study.py` | Documents belong in files; the derived variants stay `.replace()` edits |
