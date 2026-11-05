---
id: TEST-001
type: test
title: Test strategy
summary: Behavior-focused tests whose SysML documents are committed files and whose per-test case stays test-local; this repo owns artifact and round-trip evidence.
date: 2026-11-05
status: current
---

# Test strategy

Run:

```bash
./venv/bin/python -m pytest -q
```

## Ownership and fixtures

- Parser, model, variation, and selection behaviour is verified in
  `pycps_sysml2`; this repository verifies its artifact writers and the
  SSD-to-SysML round trip.
- `test_parameter_sets.py` covers SSV and SSM output, SSD parameter output,
  identity bindings, multiple disjoint sets, and dialect validation.
- `test_generate_sysml.py`, `test_generate_ssp.py`, `test_sync.py`, and
  `test_roundtrip.py` cover synthesis, packaging, nested part paths, nested SSD
  systems, and round-trips.
- A SysML document of 15 or more lines lives in `tests/fixtures/<subject>/`
  and is loaded with `tests.fixture_files.fixture_text`; the per-test case
  (slot values, fragments, `.replace()` mutations) stays in the test and is
  written under `tmp_path`. `test_fixture_policy.py` enforces both.
- Every fixture directory carries a `case.md` naming the files it owns.
- Generated artifacts stay inside pytest temporary directories.

Strategy:

- Optimize for clear, editable tests over maximal reuse.
- A document is data, so it is a file. A case is behavior, so it is in the
  test. Reuse a document when two tests exercise the same architecture; do not
  build a fixture factory to avoid two short fragments.
- Make each test behavior-focused: one small architecture, one behavior.
- Prefer concise text summaries over structural XML traversal when checking
  generated artifacts.
- Convert both formats to small text views before comparing, so assertions read
  as format-agnostic behavior checks.
- Keep assertions close to the behavior. An expected artifact is a committed
  file only when the full generated text is the contract; compare it with
  `assert_matches_fixture`, which reports a unified diff.
- Duplicating a small amount of setup is acceptable when it keeps a test easy
  to read and modify.
