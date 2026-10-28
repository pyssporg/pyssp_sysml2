# Case: `generate-sysml`

Committed inputs and expected artifacts for `tests/test_generate_sysml.py`.
Every SysML architecture is generated from an SSD, so the expected documents are
what the exporter produced and a reviewer accepted, not prose written by hand.

- **Conversion:** an SSD system structure (plus SSV/SSM parameter artifacts) →
  a SysML v2 architecture
- **Requirement / fault:** `generate_sysml_from_ssd` must recover every SSD fact
  with a documented SysML representation — system and composition names, ports,
  connectors, boundary connections, nested systems, and the parameter dialect
  (interface, set, bind) — without inventing detail the SSD does not carry.
- **Level:** component
- **Input:** the `*.ssv` files in this directory. The SSDs are not committed;
  each test builds its own through the `pyssp_standard` facade because the SSD
  setup is what makes the cases differ.
- **Expected:** the committed `*.sysml` files listed under *Artifacts*; each is
  compared as a whole document.
- **Independent oracle:** the `pyssp_standard` facade re-parses the SSV inputs
  the test feeds in, and `pyssp_sysml2.model.load` re-parses each generated
  architecture; the exporter's documented text contract
  (`src/pyssp_sysml2/model/exporter.py`) defines the expected shape. The
  writer is this repository, so the committed file records an accepted output
  rather than an independently produced one.
- **Comparison:** exact bytes against the committed file, via
  `assert_matches_fixture`, which prints a unified diff on mismatch.
- **Normalization:** none. Additional documents are concatenated in sorted file
  name order by `_architecture_text`; the expected files store that result.
- **Volatile fields:** none; the exporter is deterministic and the documents
  carry no timestamps or generated ids.
- **Update policy:** an expected file changes only with a reviewed implementation
  change. Edit the implementation, run the test, read the unified diff, and
  commit the new expected file with the change that caused it.
- **Notes:** `ssd-system-name.sysml` is the bootstrap architecture and is also
  referenced by `tests/fixtures/sync/case.md`;
  `explicit-parameter-mapping.sysml` is shared by two tests; `identity-binding.ssv`
  is shared with the sync case. The file lives here because this package
  generates it.

## Artifacts

Paths are relative to this directory.

| Path | Kind |
| --- | --- |
| `ssd-system-name.sysml` | expected, default composition name from SSD |
| `composition-override.sysml` | expected, composition name overridden |
| `scalar-connectors.sysml` | expected, scalar connector names |
| `enum-integer-mix.sysml` | expected, connected port type reuse across Integer/Enumeration |
| `scalar-group-names.sysml` | expected, scalar group attribute normalization |
| `identity-binding.sysml` | expected, prefixed parameter binding |
| `identity-binding.ssv` | input SSV, prefixed identity binding (shared with sync) |
| `explicit-parameter-mapping.sysml` | expected, inline SSM list expansion; shared by two tests |
| `external-mapping.ssv` | input SSV, external `ParameterMapping/@source` |
| `component-inline-parameter-set.sysml` | expected, component-level inline set |
| `interface-without-binding.sysml` | expected, parameter interface without a set |
| `nested-system-binding.sysml` | expected, binding inside a nested system |
| `nested-system-binding.ssv` | input SSV, nested binding |
| `boundary-connections.sysml` | expected, boundary connections with flat connectors |
| `boundary-connections-dotted.sysml` | expected, dotted boundary connectors |

## What this case proves

If this directory is deleted, the exporter's whole-document contract is no
longer pinned: a change that reorders definitions, drops a boundary connect, or
alters the parameter dialect would still pass every structural assertion in the
test but never reach a reviewer as a diff.

## Update history

| Date | Change | Reason |
| --- | --- | --- |
| 2026-10-28 | Case record and expected files added | Expected documents moved out of `test_generate_sysml.py`; bytes unchanged |
