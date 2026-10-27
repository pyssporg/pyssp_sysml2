---
id: TEST-001
type: test
title: Test strategy
summary: Small behavior-focused tests with test-local SysML snippets and no shared fixtures by default.
date: 2026-10-22
status: current
---

# Test strategy

Run:

```bash
./venv/bin/python -m pytest -q
```

Behavior:

- Tests use small explicit SysML snippets written per test under `tmp_path`.
- `test_parameter_sets.py` covers SSV and SSM output, SSD and FMI parameter
  output, identity bindings, multiple disjoint sets, and dialect validation.
- `test_generate_sysml.py`, `test_generate_ssp.py`, `test_sync.py`, and
  `test_roundtrip.py` cover SSD-to-SysML synthesis, SSP packaging, nested part
  paths, nested SSD systems, and round-trips.
- Tests follow a one-model-per-behavior style where practical, keeping intent
  explicit.
- Generated artifacts stay inside pytest temporary directories.
- Test readability is a primary concern because the repository is used for
  experimentation as well as regression coverage.

Strategy:

- Optimize for clear, editable tests over maximal reuse.
- Prefer standalone test-local model setup over shared external fixtures.
- Make each test behavior-focused: one small architecture, one behavior.
- Prefer concise text summaries over structural XML traversal when checking
  generated artifacts.
- Convert both formats to small text views before comparing, so assertions read
  as format-agnostic behavior checks.
- Keep assertions close to the behavior. Avoid large golden files unless the
  full artifact text is the contract.
- Duplicating a small amount of setup is acceptable when it keeps a test easy to
  read and modify.
