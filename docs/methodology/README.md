# SysML v2 Simulation Modeling Methodology

> Status: living document. The code and tests are the source of truth.
> If this page and the implementation disagree, the implementation wins and
> this page needs an update.

This knowledge base records **how this repository models simulation systems in
SysML v2** and how those models are transferred to SSP and FMI. Many of the
rules are implicit in the generator code and in the test suite; the goal here
is to make them explicit, reviewable, and teachable.

The first chapter is deliberately about **parameter sets**, because that is the
part of the dialect with the most implicit rules. Later chapters collect the
conventions that apply to the rest of the simulation model.

## Status labels

Every chapter or major section carries one of these labels:

| Label | Meaning |
| --- | --- |
| **Implemented** | Enforced by the current code and covered by tests. |
| **Convention** | A project convention encoded in the implementation, even if SysML v2 itself is more permissive. |
| **Proposed** | A design direction that is documented for review but **not implemented**. Do not use it in working models yet. |

## Chapters

| Chapter | Status | Covers |
| --- | --- | --- |
| [01 — Parameter sets](01-parameter-sets.md) | Implemented | Interfaces, sets, identity/explicit binds, multiple disjoint sets, nested part paths, lists, legacy parameters |
| [02 — Implicit modeling conventions](02-implicit-conventions.md) | Convention | Files/packages, parts vs systems vs FMUs, ports/connections, control attributes, naming |
| [03 — Generation and round-trip](03-generation-and-roundtrip.md) | Implemented | SSV/SSM/SSD/FMI generation, SSD→SysML synthesis, `sync ssd`, fidelity limits |
| [04 — Validation catalog](04-validation-catalog.md) | Implemented | Valid/invalid rules, diagnostics, fixes |
| [Proposal — Parameter-set reuse](proposals/parameter-set-reuse.md) | Proposed | Inheritance/union methodology for reusable sets; not implemented |
| [Runnable examples](examples/parameter-sets/README.md) | Implemented | Self-contained parameter-set models used by this handbook |

## How to use this handbook

- Start with [01 — Parameter sets](01-parameter-sets.md) when modeling a new
  parameterized component.
- Use [04 — Validation catalog](04-validation-catalog.md) when a generator
  rejects a model.
- Use [03 — Generation and round-trip](03-generation-and-roundtrip.md) when
  moving between SysML and SSP/FMI artifacts.
- Use the proposal page only for design discussions. It is not a description
  of current behavior.

Examples follow a simple convention:

- `Valid` examples are intended to load and generate.
- `Invalid` examples are intentionally rejected. The expected error is stated
  next to the example.
- `Proposed` examples are not accepted by the current tooling.
- Commands write into `build/` or `/tmp`; generated artifacts are not checked
  into the repository.

## Glossary

| Term | Meaning |
| --- | --- |
| **Parameter interface** | An `attribute def` marked `:> ParameterInterface`. It defines the component's parameter surface: names, types, multiplicities, optional defaults. |
| **Parameter set** | An `attribute def` marked `:> ParameterSet`. It holds named values that can be applied to a component. |
| **Set usage** | A composition attribute typed by a parameter set, e.g. `attribute nominal : NominalSet;`. |
| **Set member** | An attribute of a parameter set, e.g. `n_waypoints = 10`. The member name is the SSV parameter name. |
| **Interface member** | An attribute of a parameter interface, e.g. `waypointCount : Integer;`. |
| **Identity bind** | A whole-object bind: `bind nominal = autopilot.parameters;`. Names must match, and SSP uses a `ParameterBinding` prefix instead of an SSM. |
| **Explicit bind** | A per-member bind: `bind nominal.n_waypoints = autopilot.parameters.waypointCount;`. This produces an SSP mapping entry. |
| **Component path** | The dotted part-usage path from the composition root to a component or nested system, e.g. `outer.inner`. |
| **Control attribute** | A `pyssp_*` attribute used to carry metadata that has no first-class SysML v2 equivalent. Generators skip control attributes as model data. |
| **Leaf component** | A part definition with no subparts. It becomes an SSD `Component` and gets an FMI model description. |
| **Nested system** | A part definition with subparts. It becomes a nested SSD `System`. |

## Editorial rules

1. **Prefer executable examples.** If a rule can be shown with a small model,
   show the model. Runnable counterparts live under
   [`examples/parameter-sets`](examples/parameter-sets/README.md).
2. **Label status.** Do not present proposed behavior as implemented.
3. **State the SSP consequence.** A SysML rule is only useful here if the
   reader can see what it becomes in SSD/SSV/SSM/FMI.
4. **Keep one behavior per section.** Long mixed examples are harder to
   review than two short ones.
5. **Link to the source of truth.** When a rule is enforced by code or pinned
   by a test, reference the module or test next to it.
6. **Do not duplicate generated files.** Use `build/` or `/tmp` for output.
7. **Record intentional limitations.** A limitation is part of the
   methodology, not an omission.

## Source-of-truth map

| Topic | Code | Tests |
| --- | --- | --- |
| Parameter interfaces, sets, binds | `src/pyssp_sysml2/parameters.py` | `tests/test_parameter_sets.py` |
| SSD→SysML parameter synthesis | `src/pyssp_sysml2/parameter_synthesis.py` | `tests/test_generate_sysml.py`, `tests/test_roundtrip.py` |
| SSD generation | `src/pyssp_sysml2/ssd.py` | `tests/test_parameter_sets.py`, `tests/test_roundtrip.py` |
| SSV/SSM generation | `src/pyssp_sysml2/ssv.py`, `src/pyssp_sysml2/ssm.py` | `tests/test_parameter_sets.py` |
| FMI model descriptions | `src/pyssp_sysml2/fmi.py` | `tests/test_parameter_sets.py`, `tests/test_roundtrip.py` |
| SSD→SysML model synthesis | `src/pyssp_sysml2/sysml.py` | `tests/test_generate_sysml.py` |
| Sync | `src/pyssp_sysml2/sync.py` | `tests/test_sync.py` |
| Control attributes | `src/pyssp_sysml2/control.py` | — |
| SysML model adapter | `src/pyssp_sysml2/sysml_model/` | `tests/test_sysml_model.py` |

## Related documents

- [Repository README](../../README.md) — installation, CLI, artifact overview.
- [Development guide](../development.md) — maintainer architecture and test
  strategy.
- [SysML model adapter](../sysml_model_adapter.md) — parser boundary,
  sysmlpy internals, model dialect requirements.
- [Parameter sets example](../../examples/parameter_sets/README.md) — a
  runnable example that predates this handbook.
