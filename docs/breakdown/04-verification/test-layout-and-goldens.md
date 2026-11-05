---
id: TEST-002
type: test
title: Layout and golden gates
summary: A static layout test guards the shim boundary, and committed conversion goldens are checked byte for byte; FMI goldens are gone.
date: 2026-11-05
status: current
---

# Layout and golden gates

- `tests/test_module_layout.py` is a static test. It pins the package root,
  declared subpackages, shims that only re-export, no direct `sysmlpy` import,
  and real code only in `core/paths.py` and `parameters/synthesis/`
  (`INFO-008`, `AD-004`).
- `tests/test_layering.py` enforces the `pyssp_standard` public surface.
- `tests/test_golden_artifacts.py` runs each conversion case into `tmp_path`,
  compares every byte with the committed golden, and re-validates both copies
  through `pyssp_standard`.
- Goldens cover SSD, SSV, and SSM conversion. The FMI goldens were removed with
  FMI generation, which moved to `pyfmi_sysml2` (`INFO-058`).
- `UPDATE_GOLDENS=1` regenerates a golden; CI refuses to write, and a golden
  change is reviewed as a contract change.
- `tests/fixture_guard.py` fails a session that rewrites a committed fixture.
- `python -m pytest -m static` proves the fixture records and the layout gate
  before any artifact exists.
