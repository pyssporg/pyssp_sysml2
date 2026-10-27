---
id: INFO-008
type: info
title: Module map
summary: Core modules, dependencies, and the adapter boundary between generators and the parser.
date: 2026-10-22
status: current
---

# Module map

Core modules under `src/pyssp_sysml2/`:

- `sysml_model/`: SysML v2 model adapter. Loader over `sysmlpy`, repo-owned
  dataclasses, and a conformant text exporter.
- `ssd.py`: generates `SystemStructure.ssd`.
- `ssv.py`: generates one SSV file per parameter set.
- `ssm.py`: generates SSP parameter-mapping `.ssm` files.
- `parameters.py`: resolves parameter interfaces, sets, applied-set bindings,
  and mapping entries.
- `parameter_synthesis.py`: synthesizes interfaces, sets, and binds from SSD
  parameter connectors and bindings, including nested systems and multiple
  disjoint sets per element.
- `control.py`: shared `pyssp_*` control-attribute names.
- `fmu_metadata.py`: resolves typed `FmuMetadata` definitions and maps them to
  SSD component source and implementation.
- `fmi.py`: generates `modelDescription.xml` files.
- `ssp.py`: packages the SSD, built FMUs, and applied SSVs into an `.ssp`
  archive.
- `sysml.py`: generates a minimal SysML model from an SSD.
- `sync.py`: syncs SSD composition edits back into SysML.
- `cli.py`: CLI entrypoint (`pyssp`).
- `paths.py`: default paths and composition constants.

## Dependencies

- `sysmlpy`, pinned to an exact version, for SysML v2 parsing. It is wrapped by
  the `pyssp_sysml2.sysml_model` adapter; see `INFO-013` and `INFO-014`.
- `pyssp_standard` for SSP and FMI XML object handling. Consumed only through
  its top-level surface (`from pyssp_standard import ...`) and its facade
  methods; `tests/test_layering.py` rejects submodule imports.

## Adapter boundary

The `sysml_model` package is the anti-corruption layer between generators and
the parser. Only `sysml_model/loader.py` imports `sysmlpy`. Generators work
against the dataclasses in `sysml_model/model.py`, and
`sysml_model/exporter.py` emits the SysML v2 text contract independently of the
parser's serializer.

## Topic to code and tests

- Parameter interfaces, sets, and binds: `parameters.py`;
  `tests/test_parameter_sets.py`.
- SSD-to-SysML parameter synthesis: `parameter_synthesis.py`;
  `tests/test_generate_sysml.py`, `tests/test_roundtrip.py`.
- SSD generation: `ssd.py`; `tests/test_parameter_sets.py`,
  `tests/test_roundtrip.py`.
- SSV and SSM generation: `ssv.py`, `ssm.py`;
  `tests/test_parameter_sets.py`.
- FMI model descriptions: `fmi.py`; `tests/test_parameter_sets.py`,
  `tests/test_roundtrip.py`.
- FMU metadata: `fmu_metadata.py`; `tests/test_fmu_metadata.py`.
- SSP packaging: `ssp.py`; `tests/test_generate_ssp.py`.
- SSD-to-SysML model synthesis: `sysml.py`; `tests/test_generate_sysml.py`.
- Sync: `sync.py`; `tests/test_sync.py`.
- Control attributes: `control.py`.
- SysML model adapter: `sysml_model/`; `tests/test_sysml_model.py`.
