# Case: `selection`

Input document for authored variation selections and analysis plans.

## Artifacts

| Path | Kind |
| --- | --- |
| `selection.sysml` | Input |

No expected artifact: the tests assert the parsed selection maps, the plan
statuses, and the generated analysis descriptor.

## What this case proves

`selection.sysml` declares one selection per analysis with the
`pyssp_selection` control attribute. It proves that the attribute parses into
the same key language as `--select`, that a plan resolves the selection and
evaluates the constraint on the analysis scope, that an illegal combination is
`violated`, and that a malformed or missing selection is `invalid` rather than
silently unselected.

## Update history

| Date | Change | Reason |
| --- | --- | --- |
| 2026-10-30 | Created | Authored selection and analysis plans. |
