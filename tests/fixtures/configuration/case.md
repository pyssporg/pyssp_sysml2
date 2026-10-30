# Case: `configuration`

Input document for model-level configuration capture (`IMP-106`).

## Artifacts

| Path | Kind |
| --- | --- |
| `configuration.sysml` | Input |

No expected artifact: the tests assert the captured model and the SysML text the
exporter emits for the same document.

## What this case proves

`configuration.sysml` declares three model-level configuration shapes:

- a simple 100% binding (`part :>> source = SourceChoice::step;`), where the
  redefinition target becomes the usage name and the feature value is kept;
- a nested configuration whose outer usage specializes a variant
  (`part nestedGainPath :> PathChoice::nestedPath { ... }`) and whose body
  redefines the inner variation usage;
- analysis-local scenario attributes, once bound by name and once by
  redefinition (`attribute :>> scenario = ...`).

The tests prove that the raw parse tree recovers what `sysmlpy` drops
(redefinition target, subsetting target, feature value, and usage body), that
the loader exposes it on `PartUsage` and `Attribute`, and that the exporter
re-emits `:>>`, `:>`, and the feature value so the document reloads with the
same bindings. The usage body is model structure only; the exporter keeps the
generated-SysML minimal convention and does not emit it.

- **Conversion:** SysML v2 text → `Architecture` through
  `pyssp_sysml2.model.load`, then back to text through
  `Architecture.export_declared` and `load` again.
- **Requirement / fault:** a configuration binding must be captured on the
  model, never silently dropped to an anonymous usage with no target or value.
- **Level:** unit.
- **Input:** `configuration.sysml`, authored here for these tests.
- **Expected:** none. Each test asserts the captured fields inline and checks
  the exported text for the emitted binding syntax.
- **Independent oracle:** the tests. Parsed-structure assertions are the only
  authority on what the document must produce.
- **Comparison:** exact tuples, strings, and captured substrings.
- **Normalization:** `write_model` strips the file and keeps one trailing
  newline; the round-trip test writes the exported text the same way.
- **Volatile fields:** none.
- **Update policy:** edit the document only together with
  `tests/test_configuration_capture.py`; the tests fail on any change that
  alters the captured bindings.
- **Notes:** the fixture deliberately includes non-configuration definitions
  (`System`, `Step`, `Gain`, the variation points) so the exported document is
  a complete, loadable package.

## Why a file

The configuration idiom is SysML syntax, not Python data; a reviewer must read
the redefinition, the subsetting, and the feature value as authored. Inlining it
in the test module would hide the exact shape the parser drops.

## Update history

| Date | Change | Reason |
| --- | --- | --- |
| 2026-10-30 | Created | Slice 1 of `IMP-106`: capture model-level configuration syntax. |
