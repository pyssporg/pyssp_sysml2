# Case: `variation`

Input documents for `tests/test_variation.py`. Every file is a complete SysML v2
package that a test writes with `write_model` and loads; nothing is generated
from them, so the tree holds inputs only.

- **Conversion:** SysML v2 text → `Architecture` through
  `pyssp_sysml2.model.load`, then variation resolution
  (`pyssp_sysml2.parameters.variation.resolve`) and SSD, SSP, or analysis generation for the
  selected composition.
- **Requirement / fault:** a variation point must be captured, resolved by its
  usage path, or refused by name — never flattened silently. The set pins
  definition-level, usage-level, body-level, nested, and attribute variation,
  plus the errors for an unselected point, an unknown variant, an ambiguous
  bare key, a body port the point does not declare, three levels of nesting,
  and a body attribute carrying a value it cannot keep.
- **Level:** unit and component. Most tests read the resolved model; the
  example cases generate an SSD, an SSP, or an analysis.
- **Input:** the files listed below. `definition.sysml`,
  `definition-fmu.sysml`, `usage.sysml`, `body.sysml`, `nested.sysml`,
  `ambiguous-names.sysml`, `no-variation.sysml`,
  `undeclared-body-port.sysml`, `three-levels.sysml`,
  `valued-body-attribute.sysml`, `attribute-variation.sysml`,
  `attribute-set-variation.sysml`, and `untyped-attribute-variant.sysml` were
  authored here for these tests. `usage-level.sysml`, `connection.sysml`,
  `parameter-binding.sysml`, and `nested-body.sysml` are the variation-point
  examples from the product repository
  (`docs/breakdown/06-evolution/selected/examples/variation-points/`), moved
  verbatim with their descriptive header comment omitted.
- **Expected:** none. There is no expected artifact for these inputs; each test
  is its own oracle and asserts parsed structure or generated artifact content
  inline.
- **Independent oracle:** the tests. Parsed-structure assertions and the SSD,
  SSV, and SSM content checks in `tests/test_variation.py` are the only
  authority on what each document must produce.
- **Comparison:** exact values in test assertions, exact bytes where a test
  compares generated documents, and `pytest.raises` message matches for the
  refusal cases.
- **Normalization:** none. Each file is stored exactly as `write_model` writes
  it: stripped, with one trailing newline.
- **Volatile fields:** none.
- **Update policy:** edit a document only together with the test that reads it;
  the tests fail on any byte change that alters the parsed model or the
  generated artifacts.
- **Notes:** two different documents are both named "nested variation" in the
  test module: `nested.sysml` is the local dotted-key case and
  `nested-body.sysml` is the two-level body example. They are separate files on
  purpose.

## Artifacts

Inputs, relative to this directory. None is generated.

| Path | Behaviour |
| --- | --- |
| `definition.sysml` | variation part def with two variants; unselected point refuses generation |
| `definition-fmu.sysml` | the same shape with FMU metadata, so a selection changes the component source |
| `usage.sysml` | `variation part` usage with its own variants |
| `body.sysml` | variant with a statement body: nested parts and boundary connections |
| `nested.sysml` | variation point reached by a dotted usage path |
| `ambiguous-names.sysml` | bare selection key that matches two usages |
| `no-variation.sysml` | architecture without any variation construct |
| `undeclared-body-port.sysml` | body connects to a port the point does not declare |
| `three-levels.sysml` | variation nested three levels deep, refused |
| `valued-body-attribute.sysml` | variant body attribute with a value, refused |
| `attribute-variation.sysml` | `variation attribute def` marker |
| `attribute-set-variation.sysml` | attribute variation over parameter sets, resolved through an analysis |
| `untyped-attribute-variant.sysml` | attribute variant without a resolvable type |
| `usage-level.sysml` | example 03: usage-level point, SSD name stays `source` |
| `connection.sysml` | example 08: two path variants with different decompositions |
| `parameter-binding.sysml` | example 09: variation over parameter bindings inside an analysis |
| `nested-body.sysml` | example 10: variation point nested in a variant body |

## What this case proves

If these documents were dropped, the loader and resolver tests would have to
inline SysML again, and a reviewer could not read the input as SysML. Keeping
one file per behaviour also keeps the refusal cases distinguishable: the same
bytes cannot serve both the accepted and the rejected shape.

## Update history

| Date | Change | Reason |
| --- | --- | --- |
| 2026-10-28 | Case record added; documents moved out of the test modules | Test inputs were Python string literals, not reviewable SysML files |
