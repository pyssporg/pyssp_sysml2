# AGENTS

## Vision first (required)

Before you read code, edit files, or plan a change, read the project vision:

**`docs/breakdown/00-intent/intent.md`**

It states why this repository exists, what it commits to, and what it refuses to
become. It is the first document to read, not a reference of last resort.

- Read it in full before making any change to code, tests, docs, or artifacts.
- Judge every proposed change against it. If a change conflicts with the vision,
  its commitments, goals, or non-goals, stop and surface the conflict; do not
  implement it silently.
- If the work shows the long-term direction is wrong, change the vision
  deliberately first, then the code. Never let the repository drift away from
  its stated intent.

## Rules

1. **Don't assume. Surface tradeoffs.** If a contract is ambiguous, stop and say
   so rather than picking a behaviour silently.
2. **Minimum code that solves the problem.** Nothing speculative.
3. **Touch only what you must.** Clean up only your own mess.
4. **Define success criteria and verify.**

## Repository Focus

`pyssp_sysml2` generates SSP, FMI, and SysML artifacts from a SysML v2
architecture or an SSD, and syncs SSD wiring edits back into SysML. The
interchange artifact (SSD/SSV/SSM/SSP/FMI XML) is the library boundary; the CLI
is the public surface for other projects.

- SysML parsing sits behind the adapter in `src/pyssp_sysml2/sysml_model/`.
- Modeling conventions live in `docs/methodology/`; the code is the source of
  truth when the two disagree.
- This is also a test and experiment repo: keep it easy to extend.

## Hard constraints

- **The artifact is the library boundary.** Cross-project interchange is the
  SSD, SSV, SSM, SSP, or FMI XML artifact. A Python consumer uses only
  documented public functions; parser internals and schema bindings do not
  cross.
- **SysML parsing stays in the adapter.** Only
  `src/pyssp_sysml2/sysml_model/loader.py` imports `sysmlpy`; generators use the
  repo-owned dataclasses in `src/pyssp_sysml2/sysml_model/model.py`, and
  `src/pyssp_sysml2/sysml_model/exporter.py` emits the SysML text contract.
- **SSP/FMI XML object handling belongs to `pyssp_standard`.** Do not duplicate
  it.
- **Generated SysML is deliberately minimal.** Only SSD information with a
  documented SysML representation is emitted; the rest is carried as typed FMU
  metadata or `pyssp_*` control attributes and preserved on regeneration.
- **Round-trip limits are explicit.** The documented fidelity limits are not to
  be presented as full round-trip.

## Code guidelines

- Prefer readability, agility, and clear behavior over minimal diffs.
- Keep changes focused, but do not avoid a small refactor that makes the code
  easier to understand or test.
- Prefer small modules with clear responsibilities; factor reusable behavior
  into focused helpers instead of letting one file accumulate unrelated
  concerns.
- Avoid abstraction for its own sake, but bias toward a code disposition that
  keeps future experiments easy to extend.
- Avoid thin shims or wrappers when adopting legacy code if inlining is
  reasonable.
- Preserve user changes in a dirty worktree; never revert unrelated edits.

## Conventions

- Current state and intent live in `docs/breakdown/`; modeling conventions live
  in `docs/methodology/`. When code and docs disagree, the code wins and the
  documentation is updated.
- When behavior changes, update or add tests close to the affected code.
- Prefer test-local model setup over large shared fixtures unless the fixture is
  the contract under test; favor small, explicit tests that isolate one behavior
  at a time.
- When asserting generated artifacts, use concise summaries or normalized text
  so failures stay readable.
- Keep docs aligned with the actual CLI, file layout, and dependency setup.

## Environment

- Python >= 3.10.
- Development: `python3 -m venv venv`, then `pip install -r requirements.txt`
  and `pip install -e .`; use `requirements_local.txt` when working against the
  bundled `pyssp_standard` checkout.
- Tests: `./venv/bin/python -m pytest -q`; inspect the implementation first and
  prefer `rg` for search.
