---
id: IMP-006
type: imp
title: SysML variation points to one SSP per selection
summary: Capture variation and variant members through the raw parse tree, fail loud today, and generate one SSP per explicit selection.
date: 2026-10-28
status: current
---

# SysML variation points to one SSP per selection

A variation point is a SysML 2.0 definition or usage marked `variation` whose alternatives are `variant` members.
The pinned parser discards every `variant` member and every usage-level `variation` flag.
A build therefore exports one model whatever variation the architecture declares.
Selection has no home in SysML, so it enters from outside and produces one artifact per selection.

## Evidence

- **Definition flag survives**: `Part.grammar.prefix.prefix.isVariation` is readable today, but no dataclass exposes it.
- **Usage flag lost**: the occurrence-usage prefix visitor never tests `VARIATION`, so usage-level points vanish.
- **Members lost**: the definition-body visitor has no `variantUsageElement` branch and returns `None`, filtered out later.
- **Loss point**: `antlr_visitor.py:10245-10265` builds nothing for a variant; `:9094-9097` drops the `None`.
- **Not fixable by upgrade**: the 0.97.1 wheel carries identical code at the same lines.
- **Raw tree retains all members**: `sysmlpy.antlr_parser.parse` keeps `VariantUsageElementContext` nodes with full text.
- **Probe**: five variant members recovered from one file — parts, a connect, a bind, and a usage-level part.
- **Five variants observed**: variation definition, variant parts, variant connect, variant bind, usage-level variant part.
- **Adapter is the single importer**: only the loader may read the parse tree; generators see dataclasses only.
- **Silent today**: generation of an architecture with variation succeeds and emits a variant-less SSD.
- **Worst case measured**: a path variation emitted one component with an empty source and no internal parts.
- **Constraint drop confirmed**: constraints parse and are then ignored; the adapter model has no constraint element.
- **Vocabulary**: ISO/IEC 26580 delegates selection to an external configurator; SysML has no binding time.

## Current Pain Or Risk

- A declared variation silently produces a different model than the author wrote.
- Nothing in the artifact records which alternative a build used.
- Part, connect, and bind variants are indistinguishable from absence.
- A selection record authored inside the architecture fails the flat-parameter check.
- Consumers cannot tell an authoring mistake from deliberate flattening.

## Decision

- Capture route: a raw-tree walk inside the loader.
- No fork of the parser and no vendored patch; the pin stays.
- Selection enters on the command line, not inside the architecture.
- Generation baseline: one SSP per selection.

## Implementation Phases

1. **Fail loud**: detect a reachable variation point and reject the build with an actionable message.
2. **Model**: add the variation flag and a variant-member list to the definition and usage dataclasses.
3. **Loader**: read the definition flag from the grammar object and members from the raw tree.
4. **Resolve**: substitute the selected alternative before generation; reject unknown, duplicate, and missing selections.
5. **Generate**: one package and one artifact directory per selection, named after the selection.
6. **Provenance**: record the selection outside the SSP. Home undecided.
7. **Export**: refuse SysML export for an architecture that carries variation.

## Expected Benefit

- A declared variation reaches the artifact or fails at build time.
- Selection identity joins build, artifact directory, and comparison case.
- Structural and parameter variants follow one route.
- The dialect boundary stays explicit: only what the adapter reads is supported.

## Risk And Blast Radius

- **Parser coupling**: the raw tree is an internal API; a pin change can break the walk without a version signal.
- **Double parse**: one extra parse pass per architecture; acceptable at fixture scale, not free.
- **Model surface**: a new field on a dataclass shared by every generator, exporter, and sync path.
- **Ambiguity**: a variant member shares a name with a plain part unless the field separates them.
- **Scope creep**: `variant connect` and `variant bind` invite a general variability engine; the intent forbids it.
- **Provenance**: SSP has no selection slot, so any home is a local convention.
- **Round-trip**: export cannot represent variation, so sync would erase points unless it refuses.

## Open Questions

- Does a selection name the variant, or the artifact case, or both?
- Where does provenance live: an `extra/` entry in the package, or a sidecar file?
- Is a missing selection an error, or does an explicit default variant apply?
- Are `variant connect` and `variant bind` supported or rejected with a message?
- Do nested variation points need a qualified selection key?
- Does the raw-tree walk stay in the loader, or move to a small parser-adjacent module?

## Owns

- The capture and selection strategy that turns one architecture into one SSP per selection.
- The dialect boundary for variation constructs.

## Excludes

- Selection policy inside SysML; the language has no binding time.
- General SysML v2 variability support; the intent forbids a general toolchain.
- Parameter-set reuse semantics; see `IMP-001` and `IMP-002`.
- Parser replacement and adapter scope; see `EVAL-001` and `EVAL-002`.
- SSP packaging of multiple SSDs; one package per selection is the baseline.
