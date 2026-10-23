# Intent

## Purpose

`pyssp_sysml2` turns a SysML v2 architecture model into the standard artifacts a
simulation workflow consumes, and turns those artifacts back into SysML. It owns
SysML-to-SSP/FMI generation and the SSD-to-SysML sync; it does not run or judge
simulations.

It covers two directions:

- SysML architecture or SSD → SSD, one SSV per parameter set, SSM parameter
  mappings, FMI model descriptions, and a packaged SSP.
- SSD wiring edits → a sync back into an existing SysML composition, or a
  minimal SysML architecture bootstrapped from an SSD.

## Scope

| Belongs here | Belongs elsewhere |
| --- | --- |
| SysML v2 model adapter and generators | SSP/FMI XML object model (`pyssp_standard`) |
| SSD/SSV/SSM/FMI XML/SSP generation | engine execution and result normalisation (`pyssp_simulate`) |
| SSD→SysML synthesis and `sync ssd` | measurement and judgment (`pyssp_vv`) |
| the `pyssp` CLI as the public surface | workflow composition and scheduling (`pyssp_workflow`) |

## Commitments

- **The artifact is the library boundary.** Cross-project interchange is the
  SSP, SSD, SSV, SSM, or FMI XML artifact. A Python consumer uses only
  documented public functions; parser internals and schema bindings do not
  cross.
- **The parser sits behind an adapter.** Only `sysml_model/loader.py` imports
  `sysmlpy`. Generators work against the repo-owned dataclasses in
  `sysml_model/model.py`, and `sysml_model/exporter.py` emits the SysML text
  contract independently of the parser's serializer.
- **Standard handling is delegated.** SSP/FMI XML objects come from
  `pyssp_standard`; this package does not reimplement them.
- **Generated SysML is deliberately minimal.** Only SSD information with a
  documented SysML representation is emitted. The rest is carried as typed FMU
  metadata or `pyssp_*` control attributes and preserved on regeneration.
- **Round-trip limits are explicit.** The fidelity limits are documented in
  `docs/methodology/03-generation-and-roundtrip.md`; they are not to be
  presented as full round-trip.
- **The code is the source of truth for the methodology.** When
  `docs/methodology/` and the implementation disagree, the implementation wins
  and the documentation is updated.

## Non-goals

- Simulation runtime and engine adapters.
- Measurement, acceptance criteria, or verdicts.
- A general SysML v2 toolchain: the generators cover the documented
  simulation-modeling dialect, not all of SysML v2.
- A full SSP authoring environment; SSP editing belongs to `pyssp_standard`.

## Roles of the ecosystem

| Package | Responsibility | Relation to `pyssp_sysml2` |
| --- | --- | --- |
| `pyssp_sysml2` | SysML → SSP/FMI generation, SSD → SysML sync | — |
| `pyssp_standard` | SSP/FMI XML object handling | consumed |
| `pyssp_simulate` | run engines, normalise results | consumes the generated SSP |
| `pyssp_vv` | measurement, judgment, evidence | judges the simulated result |
| `pyssp_workflow` | build/run/compare/verify flows | composes the steps |
