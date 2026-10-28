# Test fixtures — pyssp_sysml2

SysML inputs and expected artifacts live here. The test modules keep only the
setup that makes each case different.

## Layout

```
fixtures/<subject>/
├── case.md            # provenance, oracle, comparison, update policy
├── <name>.sysml       # one native document per case
└── template.sysml     # only when a test fills slots
```

`<subject>` names the behaviour the set exercises (`sysml-model`, `variation`,
`generate-sysml`, `sync`, …), not the test file. A document set can share one
`case.md`; the record must name every file it owns.

## Loading

```python
from tests.fixture_files import assert_matches_fixture, fixture_text, render_fixture

write_model(tmp_path / "model.sysml", fixture_text("sysml-model/values.sysml"))
write_model(tmp_path / "model.sysml", render_fixture("parameter-sets/template.sysml", sets=...))
assert_matches_fixture(generated_text, "sync/expected.sysml")
```

- `fixture_text` returns the file as it should be written: UTF-8, one trailing
  newline.
- `render_fixture` fills `$slot` / `${slot}` with `string.Template`, so SysML
  braces are literal and need no escaping.
- `assert_matches_fixture` shows a unified diff between the expected artifact
  and the generated text.

## Rules

- A document of 15 or more lines lives here, not in a test module; the policy
  test enforces it.
- A file the code under test generates is an `expected` artifact, committed and
  compared, never regenerated during a normal run.
- Add a case by adding a file and naming it in `case.md`. No test code changes
  unless the test needs a new behaviour.
- `case.md` records what the bytes cannot: where the document came from, which
  defect it pins, and whether byte or semantic comparison applies.
- The session guard hashes this tree; a test that writes here fails the run.
