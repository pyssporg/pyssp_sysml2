---
id: INFO-054
type: info
title: Validation of sync diagnostics
summary: Sync requires port.attribute connectors, correct boundary directions, complete mappings, and resolvable composition parts.
date: 2026-11-05
status: current
---

# Validation of sync diagnostics

- Sync connections must use `port.attribute` form.
- Boundary ports must point the right way: `in` at the start, `out` at the
  end.
- Boundary connections must cross a subpart; boundary-to-boundary connections
  are rejected.
- Boundary ports must be declared on the enclosing system.
- Sync requires complete attribute mappings; partial mappings are rejected.
- Sync requires compatible ports.
- Unknown sources can be rejected with `references unknown part source '...'`.
  `sync ssd --no-synthesize` fails instead of creating a part definition.
- An empty component source must match an existing part.
- Unknown ports can be rejected.
- The composition must exist; otherwise `Part not found: ...`.
