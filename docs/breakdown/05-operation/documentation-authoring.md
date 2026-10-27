---
id: INFO-023
type: info
title: Documentation authoring rules
summary: Documented rules need a runnable example, an explicit status, the SSP consequence, and a source-of-truth pointer.
date: 2026-10-22
status: current
---

# Documentation authoring rules

Current state lives in this breakdown. Runnable parameter-set examples live in
`examples/parameter-sets/`. Generated artifacts go to `build/` or `/tmp` and
are not checked in.

## How to use the tree

- Start with `CP-001` when modeling a new parameterized component.
- Use `INFO-015` to `INFO-019` when a generator rejects a model.
- Use `INFO-006` when moving between SysML and SSP/FMI artifacts.
- Use `IMP-001` only for design discussions; it is not current behavior.

Examples follow a simple convention:

- **Valid** examples are intended to load and generate.
- **Invalid** examples are intentionally rejected; the expected error is stated
  next to the example.
- **Proposed** examples are not accepted by the current tooling.
- Commands write into `build/` or `/tmp`; generated artifacts are not checked
  in.

## Rule checklist

When writing or updating a rule:

1. **Prefer executable examples.** If a small model can show the rule, show the
   model. Runnable counterparts live under `examples/parameter-sets/`.
2. **Label status.** Do not present proposed behavior as implemented. The
   status labels are in `INFO-025`.
3. **State the SSP consequence.** A SysML rule is useful only when the reader
   sees what it becomes in SSD, SSV, SSM, or FMI.
4. **Keep one behavior per section.** Two short sections are easier to review
   than one long mixed example.
5. **Link to the source of truth.** When code or a test enforces a rule,
   reference the module or test next to it.
6. **Do not duplicate generated files.** Use `build/` or `/tmp` for output.
7. **Record intentional limitations.** A limitation is part of the methodology,
   not an omission.

When code and docs disagree, the code wins and the documentation is updated.
