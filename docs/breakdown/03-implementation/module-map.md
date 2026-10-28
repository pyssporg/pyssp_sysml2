---
id: INFO-008
type: info
title: Module map
summary: Domain packages, dependencies, and the adapter boundary between generators and the parser.
date: 2026-10-28
status: current
---

# Module map

`src/pyssp_sysml2/` is split by concern; the package facade re-exports the
public generator functions.

```
src/pyssp_sysml2/
├── __init__.py          # canonical public surface: 9 generator functions
├── cli.py               # `pyssp` entrypoint
├── core/                # control.py, paths.py, fmi_helpers.py
├── model/               # model.py, loader.py, exporter.py
├── parameters/          # dialect.py, synthesis.py, variation.py
├── metadata/            # fmu_metadata.py, ssp_metadata.py, roles.py
├── artifacts/           # ssd.py, ssv.py, ssm.py, ssp.py, fmi.py, study.py
└── sysml/               # generate.py, sync.py
```

Every directory carries an `__init__.py`.

## Public surface

`__init__.py` is canonical. `__all__` names exactly `build_ssd`, `generate_ssd`,
`generate_ssp`, `generate_parameter_sets`, `generate_parameter_mappings`,
`generate_study`, `generate_model_descriptions`, `generate_sysml_from_ssd`,
and `sync_sysml_from_ssd`. `cli.py` stays at the root because `pyproject.toml`
maps `pyssp_sysml2.cli:main`.

## Concerns

- `core/`: constants and path/format helpers.
- `model/`: the SysML v2 language adapter. `loader.py` is the only module that
  imports `sysmlpy`; `model.py` holds the dataclasses; `exporter.py` emits the
  text contract. `model/__init__.py` re-exports the dataclasses and
  `endpoint_text`, and defers `load` so the package import stays parser-free.
- `parameters/`: the parameter dialect and variation resolution. `dialect.py`
  resolves interfaces, sets, binds, and mappings; `synthesis.py` builds them
  from SSD connectors; `variation.py` selects one concrete architecture.
- `metadata/`: typed FMU/SSP metadata and role markers.
- `artifacts/`: SSP/FMI artifact generation, one module per artifact: SSD, SSV,
  SSM, SSP, FMI model descriptions, and the study descriptor.
- `sysml/`: SysML generation and sync. It uses `model/` and `artifacts/`;
  `generate.py` emits a minimal model from an SSD and `sync.py` applies SSD
  wiring edits. `sysml/__init__.py` re-exports both functions.

## Dependencies

- `sysmlpy`, pinned exactly, for SysML v2 parsing. Wrapped by the
  `pyssp_sysml2.model` adapter; see `INFO-013` and `INFO-014`.
- `pyssp_standard` for SSP and FMI XML objects, imported only through its
  top-level surface; `tests/test_layering.py` rejects submodule imports.

## Adapter boundary

`model/` is the anti-corruption layer. Only `model/loader.py` imports
`sysmlpy`; `tests/test_module_layout.py` enforces that by scanning source text.
Generators use the dataclasses in `model/model.py`, and `model/exporter.py`
emits the SysML v2 text contract independently of the parser's serializer.

## Topic to code and tests

- Parameter interfaces, sets, and binds: `parameters/dialect.py`;
  `tests/test_parameter_sets.py`.
- Parameter synthesis: `parameters/synthesis.py`; `tests/test_generate_sysml.py`,
  `tests/test_roundtrip.py`.
- Variation selection: `parameters/variation.py`; `tests/test_variation.py`.
- SSD, SSV, and SSM generation: `artifacts/ssd.py`, `artifacts/ssv.py`,
  `artifacts/ssm.py`; `tests/test_parameter_sets.py`.
- FMI model descriptions: `artifacts/fmi.py`; `tests/test_parameter_sets.py`,
  `tests/test_roundtrip.py`.
- FMU metadata: `metadata/fmu_metadata.py`; `tests/test_fmu_metadata.py`.
- SSP packaging: `artifacts/ssp.py`; `tests/test_generate_ssp.py`.
- Study descriptors: `artifacts/study.py`; `tests/test_roles_study.py`,
  `tests/test_variation.py`.
- SSD-to-SysML synthesis: `sysml/generate.py`; `tests/test_generate_sysml.py`.
- Sync: `sysml/sync.py`; `tests/test_sync.py`.
- SysML model adapter: `model/`; `tests/test_sysml_model.py`.
