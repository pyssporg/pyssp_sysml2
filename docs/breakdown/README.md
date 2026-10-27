# Product Breakdown — pyssp_sysml2

Current-state systems-engineering record for `pyssp_sysml2`: why it exists, the
parameter dialect it promises, how generation is organized, what realizes it,
and how it is verified and run.

## The Seven Layers

- `00-intent/` — why the project exists and who it serves.
- `01-product/` — the parameter-set dialect and its promises.
- `02-architecture/` — model structure, ports, pipeline, and round-trip design.
- `03-implementation/` — modules, artifact writers, adapter, and parser pin.
- `04-verification/` — test strategy, validation rules, and diagnostics.
- `05-operation/` — setup, CLI, examples, troubleshooting, authoring rules.
- `06-evolution/` — reuse proposal and parser evaluation.
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
- Vendored dependencies and capability checkouts: `3rd_party/`.
- Dated history: the decision archive, read via `pb archive`.
