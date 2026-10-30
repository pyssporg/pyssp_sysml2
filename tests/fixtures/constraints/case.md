# Case: `constraints`

Input documents for constraint capture, evaluation, and export round trip.

## Artifacts

| Path | Kind |
| --- | --- |
| `constraints.sysml` | Input |
| `negated.sysml` | Input |
| `nested-scope.sysml` | Input |
| `overridden.sysml` | Input |
| `expressions.sysml` | Input |
| `resolution.sysml` | Input |

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

`negated.sysml` asserts a usage with `assert not`, proving the negation flag is
captured, flips the evaluated result, and survives export and reload.

`nested-scope.sysml` places the asserted usage in a leaf definition reached
through two part usages, proving that evaluation composes the owner path
(`sut.inner`) and resolves bindings against it.

`overridden.sysml` derives a rules definition from a base one and redeclares an
inherited constraint by name, proving the derived usage replaces the inherited
one while an unnamed inherited constraint is never overridden.

`expressions.sysml` carries one constraint per evaluator rule: implies
associativity and vacuous truth, parentheses, string escapes, `Type::member`
resolution, boolean literals, non-boolean operands and values, the full
precedence chain (`and` over `or`, `or` over `xor`, `xor` over `and`, `not`
over equality), and non-boolean right operands that must still be checked when
the left operand decides the result.

`resolution.sysml` carries the resolution failures: an unknown constraint
definition, a usage with no expression, and a usage that leaves a definition
parameter unbound.

## Update history

| Date | Change | Reason |
| --- | --- | --- |
| 2026-10-30 | Created | IMP-104: capture and evaluate constraints. |
| 2026-10-30 | Added negation, nested scope, override, expression, and resolution inputs | Close evaluator test gaps. |
