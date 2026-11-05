---
id: INFO-034
type: info
title: Constraints
summary: Constraint definitions and usages are captured and evaluated by pycps_sysml2 during selection.
date: 2026-11-05
status: current
---

# Constraints

## Capture and evaluation

Constraint capture and evaluation are `pycps_sysml2`'s (`INFO-031`); this package
calls them with `SSP_POLICY` and consumes the verdict (`INFO-043`).

- A package-level `constraint def` becomes a `ConstraintDefinition` with typed
  parameters and one source-scanned expression.
- A `constraint name : Type { in p = ref; }` becomes a `ConstraintUsage` on its
  owning part def, with bindings in source order.
- `assert [not] name;` sets `asserted` and `negated`; an unknown name is
  rejected.
- Each binding resolves to `owner path + "." + reference` in the variant
  selection (`INFO-044`).
- Evaluation walks reachable part usages and runs asserted usages after
  resolution, over `==`, `!=`, `implies`, `and`, `or`, `xor`, `not`,
  parentheses, and references (`Type::member` becomes `member`).
- An asserted failure or an invalid evaluation raises before an SSD, SSP, or
  analysis write; non-asserted usages report `unasserted`; with no selection the
  step is a no-op.
- Constraints come from the effective members of a part definition, so a
  configuration is judged by the asserted usages it inherits, evaluated at the
  composed usage's path.
