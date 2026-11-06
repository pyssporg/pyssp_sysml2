# Product Breakdown — pyssp_sysml2

Current-state systems-engineering record for `pyssp_sysml2`: why it exists, the
parameter dialect it promises, how generation is organized, what realizes it,
and how it is verified and run.

## The Seven Layers

- `00-intent/` — why the package exists, its scope, commitments, and roles.
- `01-product/` — the parameter-set dialect and its promises.
- `02-architecture/` — structure, ports, metadata, selection, pipeline, sync.
- `03-implementation/` — modules, artifact writers, and the pycps_sysml2
  dependency.
- `04-verification/` — test strategy, validation rules, and diagnostics.
- `05-operation/` — setup, CLI, examples, troubleshooting, authoring rules.
- `06-evolution/` — reuse proposal and dependency evaluation.
- the decision archive (`docs/archive/archive.zip`) — dated decision stream,
  history only, read via `pb archive`.

All seven layers are present.

## Boundary Rule

A document's home is the layer whose question it answers; information flows
downward only. Current state lives in layer leaves, history in the decision
archive, and tracking in the generated registers. This file indexes current
state only.

- Read top-down: intent, product, architecture, implementation, verification,
  operation.
- Cite other nodes by ID, never by path.
- Evolution holds candidates only; it never restates current state.

## Excludes

- Runnable parameter-set models: `examples/parameter-sets/`.
- Generated builds and artifacts: `build/` and `/tmp`.
- Sibling package checkouts: the flat ecosystem workspace (`../..` repos).
- Dated history: the decision archive, read via `pb archive`.
