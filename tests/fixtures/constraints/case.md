# Case: `constraints`

Input document for constraint capture, evaluation, and export round trip.

## Artifacts

| Path | Kind |
| --- | --- |
| `constraints.sysml` | Input |

No expected artifact: the tests assert the loaded dataclasses and the exported
text directly.

## What this case proves

`constraints.sysml` holds one package-level `constraint def`, two variation
part definitions with two variants each, and a composition that binds the
constraint parameters to its part usages and asserts the usage. It proves that
the adapter captures the constraint body from source (because sysmlpy garbles a
definition's grammar dump), that export preserves the definition and usages,
and that evaluation rejects an illegal variant selection before generation.
A second, unasserted usage proves that only asserted usages can fail.

## Update history

| Date | Change | Reason |
| --- | --- | --- |
| 2026-10-30 | Created | IMP-104: capture and evaluate constraints. |
