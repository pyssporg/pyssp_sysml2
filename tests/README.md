# Tests

Two rules decide where a test belongs and what its green means.

- **Path = case.** A test file is named for the thing it is evidence about, and
  the fixture it needs lives beside it or under `tests/golden/<case>/`.
- **Marker = level.** The level says what a passing run proves, not how long the
  test takes. The level is declared once per file in `FILE_LEVELS`
  (`tests/conftest.py`) and applied at collection, so a new test file cannot
  arrive without one: `test_layering.py` fails until the file is listed.

## Levels

| Marker | A green run proves | Command |
| --- | --- | --- |
| `static` | source or files were inspected; the package was not executed | `python -m pytest -m static` |
| `unit` | one object behaves; no generated artifact involved | `python -m pytest -m unit` |
| `component` | a generated artifact (SSD, SSV, SSM, SSP, FMI, SysML) is the unit under test | `python -m pytest -m component` |
| `contract` | two directions agree (round-trip, SSD↔SysML sync) | `python -m pytest -m contract` |
| `system` | the installed CLI was driven end to end | `python -m pytest -m system` |
| `slow` | excluded from the default CI subset, run on purpose | `python -m pytest -m slow` |

`python -m pytest` runs everything; CI runs `python -m pytest -m "not slow"`.
A file whose tests span two levels is listed with both markers and must appear
in `MIXED_FILES`; no other combination is accepted.

## Where the evidence lives

- `tests/fixtures/<subject>/` — SysML documents and expected artifacts used as
  test data: one native file per case, plus a `case.md` naming every file. Load
  with `tests/fixture_files.py` (`fixture_text`, `render_fixture`,
  `assert_matches_fixture`). See `tests/fixtures/README.md`.
- `tests/golden/<case>/` — one conversion case: the SysML input plus the
  committed SSP/FMI artifacts generated from it.
- `tests/golden/<case>/case.md` — the provenance record for that case: what it
  converts, which oracle proves it, how it may be normalized, and the list of
  every artifact in the directory.
- `tests/golden/README.md` — how the goldens are checked and regenerated.
- `tests/resources/` — externally authored fixtures that are read, never
  written.
- `tests/test_golden_artifacts.py` — generates each case, compares bytes with
  the committed golden, and validates both the generated and the committed copy
  through the `pyssp_standard` facade.
- `tests/test_fixture_policy.py` — static policy over both trees: every
  directory has a `case.md`, every fixture file is named in its record, every
  golden case is named in the converter test's `CASES` map, no test module
  embeds a document of 15+ lines, and no fixture is read through the cwd.

## Adding a golden case

The conversion itself is a data change; only one line of code is involved
because the composition name is a fact about the SysML model, not about the
directory.

1. Create `tests/golden/<case>/` and add `architecture.sysml`.
2. Add `tests/golden/<case>/case.md` from
   `project-test-suites/templates/conversion-case.md`, adapted as the existing
   records are: `Conversion` names `.sysml` → `.ssd`/`.ssv`/`.ssm`/
   `modelDescription.xml`, `Input` states provenance, `Independent oracle` is
   `pyssp_standard` `check_compliance()`, `Comparison` is exact bytes plus parsed
   structure, `Update policy` is `UPDATE_GOLDENS=1` with a reviewed diff,
   refused in CI, and the pinned `GENERATION_TIME` is named. List every
   non-SysML artifact by relative path under `## Artifacts`.
3. Add one entry `<case>: "<CompositionName>"` to `CASES` in
   `tests/test_golden_artifacts.py`. This is a data row, not test logic; a case
   directory that is missing from it fails
   `test_every_golden_case_is_exercised_by_the_golden_test`.
4. Regenerate and review (below).
5. `python -m pytest -m static` proves the record is complete before the
   artifacts exist.

## Regenerating goldens

```bash
UPDATE_GOLDENS=1 python -m pytest tests/test_golden_artifacts.py
```

Then read the diff before committing. A golden change is a contract change, not
a test fix: confirm it is intended (dialect, mapping rules, version, ordering),
and never regenerate to silence a failure you have not explained. Commit the
inputs and the outputs together.

- `modelDescription.xml` carries `generationDateAndTime`; the test pins it to
  `GENERATION_TIME` (`2026-01-01T00:00:00Z`). Do not make it clock-dependent.
- Regeneration is a developer action. The test refuses to write when
  `UPDATE_GOLDENS=1` and `CI` is set (`refusing to update goldens in CI`), and
  CI itself never sets `UPDATE_GOLDENS`.
- `UPDATE_REF=1` is the same idea for an external reference tree, where one
  exists.

## The fixture-write guard

`tests/fixture_guard.py` hashes every file under `tests/fixtures`,
`tests/golden`, and `tests/resources` at session start and re-hashes them at session finish
(`pytest_sessionstart` / `pytest_sessionfinish` in `conftest.py`). A test that
adds, removes, or rewrites a committed fixture fails the session and the changed
paths are printed, even when every assertion passed. Bytecode caches
(`__pycache__`, `*.pyc`) are ignored.

Runs that legitimately write fixtures (`UPDATE_GOLDENS`, `UPDATE_REF`) skip the
guard. If you find yourself wanting to disable it for anything else, the test is
probably asserting on evidence it just created; give it `tmp_path` instead.
