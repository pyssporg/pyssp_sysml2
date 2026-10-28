---
id: INFO-014
type: info
title: sysmlpy pin internals and dialect
summary: Internal sysmlpy structures the loader depends on, and the standard SysML v2 dialect the adapter accepts.
date: 2026-10-23
status: current
---

# sysmlpy pin internals and dialect

These sysmlpy 0.96.4 internals are not part of sysmlpy's public API. They are
the first things to check when upgrading the pin. All are isolated at the
bottom of `model/loader.py` in the grammar-layer walks section.

- **Port direction** lives at
  `port.grammar.prefix.prefix.prefix.direction` with
  `FeatureDirection.isIn/isOut/isInOut`; the public `Port` has no direction.
- **Connection and binding endpoints** live in
  `ConnectionUsage.part.part.children[].children[].children[]` and
  `BindingConnector.children[].children[].children[]`, using
  `OwnedReferenceSubsetting` and `OwnedFeatureChaining`. For a dotted end like
  `src.sig`, both names come from the feature-chaining list. A bare end such as
  `connect gain.y to y;` yields a single name, which the loader keeps as a
  boundary port with part `None`.
- **Attribute multiplicity** lives in
  `FeatureSpecializationPart.multiplicity`, from `MultiplicityPart` through
  `OwnedMultiplicity` to `MultiplicityRange` and `LiteralInteger` or
  `LiteralInfinity`. `Real[3]` reads as `"3"` and `[0..*]` as `"0..*"`.
- **Definition supertypes** live in
  `DefinitionDeclaration.subclassificationpart`, from `OwnedSubclassification`
  to `QualifiedName.names`. This recognizes `attribute def X :> ParameterSet`.
- **Negative literals**: `get_value()` drops a leading unary minus. The sign is
  re-attached from the grammar's `UnaryExpression.operator`.
- `get_value()` raises `AttributeError` for value-less attributes, returns
  `'true'`, `'false'`, and `'(1.0,2.0)'` as raw strings for bool and tuple
  literals, and returns a pint `Quantity` for unit literals. `model/loader.py`
  normalizes all of these.
- Loading emits a benign one-time `UserWarning` about a failed DFA cache save;
  it is suppressed at `model/loader.py` import time.

## Model dialect requirements

`.sysml` input must be standard-conformant SysML v2. Two legacy constructs were
removed from repository models during the migration:

- list-valued attributes use tuples, `attribute xs = (1.0, 2.0);`; bracket
  lists are a syntax error;
- `comment` is a reserved keyword, so attributes may not be named `comment`.

The adapter also loads the parameter-set dialect:

- `port def` and `attribute def` definitions, with member type, value, doc, and
  multiplicity;
- specialization with `:>`, used for the `ParameterInterface` and
  `ParameterSet` markers;
- `bind` statements with full feature chains, for example
  `bind component.parameters.member = set.member;`.

A `port def` is an interface and an `attribute def` is a set only when it
specializes the matching marker definition. The marker definitions must exist in
the package; the loader does not resolve imports across packages.

A component or nested system exposes its interface through the fixed port
`in port parameters : <Interface>;`. Only one such port per part is supported.
Flat parameter attributes are retired and rejected.

`generate ssd` consumes this dialect. `generate sysml` and `sync ssd`
synthesize or reconcile it from SSD parameter connectors and
`ParameterBinding` entries. Bind targets may use nested part paths, and several
sets may apply to one component when their target members are disjoint.
