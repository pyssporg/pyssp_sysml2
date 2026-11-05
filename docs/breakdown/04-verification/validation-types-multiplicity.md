---
id: INFO-051
type: info
title: Validation of types and multiplicity
summary: Set and interface types must match, lists must have a fixed length, and indexed mappings must agree on both sides.
date: 2026-11-05
status: current
---

# Validation of types and multiplicity

- Set and interface types must match. A mismatch reports
  `has incompatible types: ... vs ...`.
- Lists must have a fixed length. `[0..*]` reports
  `has unbounded multiplicity '[0..*]'`.
- Set tuple length must match interface multiplicity. A mismatch reports
  `provides N values but ... declares [M]`.
- A list-valued set member needs a list target.
- A scalar set member cannot target a list.
- Indexed mappings must match on both sides, or use indices on neither side.
