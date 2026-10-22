# 04 — Validation Catalog

> **Status: implemented.** Use this page when a model loads but a generator
> rejects it. The loader itself is non-validating; these checks live in the
> parameter, SSD, synthesis, and sync layers.

## 1. When validation happens

The loader accepts a model even when references are unresolved. Validation
happens when a generator needs the model:

- `generate ssv` / `generate ssd` / `generate ssm` / `generate fmi` validate
  the parameter dialect and applied sets;
- `generate sysml` validates SSD parameter shapes, names, and mappings;
- `sync ssd` validates composition edits and, if the parameter dialect is
  present, reconciles it.

The first error usually tells you which layer rejected the model.

## 2. Markers and roles

| Rule | Diagnostic | Fix |
| --- | --- | --- |
| Marker definitions must exist in the package | `missing marker definition(s) ...` | Add `port def ParameterInterface;` and `attribute def ParameterSet;` |
| A parameter port must be typed by a marked interface | `... is not marked ':> ParameterInterface'` | Add `:> ParameterInterface` to the port's type |
| A set usage must be typed by a marked set | `... is not marked ':> ParameterSet'` | Add `:> ParameterSet` to the set definition |
| A set and an interface are different roles | `... is not marked ':> ...'` | Do not use an interface as a set or vice versa |

Valid:

```sysml
port def ParameterInterface;
attribute def ParameterSet;

port def P :> ParameterInterface { attribute x : Real; }
attribute def S :> ParameterSet { attribute x = 1.0; }
```

> Inheritance is not transitive yet. A set that only specializes another set
> is rejected unless it directly lists `:> ParameterSet`; even then, inherited
> members are not flattened. See
> [the reuse proposal](proposals/parameter-set-reuse.md).

Invalid:

```sysml
attribute def P { attribute x : Real; }
part def Comp { in port parameters : P; }
```

```text
Parameter port Comp.parameters is typed by 'P', which is not marked
':> ParameterInterface'
```

## 3. Parameter port and mixing

| Rule | Diagnostic | Fix |
| --- | --- | --- |
| At most one `parameters` port per part | Duplicate port / model error | Rename or remove the extra port |
| A part with a port may not also have flat parameter attributes | `mixes a 'parameters' port with flat parameter attributes: ...` | Move flat attributes into the interface |
| A composition may not mix parameter ports and legacy components | `Composition mixes parameter interfaces/sets (...) with flat parameter attributes (...)` | Use one dialect per composition |
| The composition root is not a parameter target | `Top-level composition parameter interfaces are not supported` | Attach the port to a component or nested-system usage |
| A synthesized parameter port cannot reuse a subpart name | `already has a subpart named 'parameters'` | Rename the subpart |

Valid leaf component:

```sysml
part def Comp {
  in port parameters : CompParameters;
}
```

Invalid mixed leaf:

```sysml
part def Comp {
  in port parameters : CompParameters;
  attribute gain : Real;
}
```

```text
Comp mixes a 'parameters' port with flat parameter attributes: gain
```

Invalid top-level port:

```sysml
part def Composition {
  in port parameters : CompositionParameters;
}
```

```text
Top-level composition parameter interfaces are not supported;
attach parameter interfaces to component usages
```

## 4. Set application and binds

| Rule | Diagnostic | Fix |
| --- | --- | --- |
| A bind must name a set usage in the composition | `... references 'x', which is not a composition attribute` | Declare `attribute x : SomeSet;` |
| A bind target component path must resolve | `Parameter bind target '...' does not resolve to a component usage` | Fix the component path or add the part usage |
| A bind target must put the parameter port on the left | `must be written with the parameter port on the left` | Swap the two sides |
| A bind target must use the `parameters` port | `Parameter bind targets must be '<component>.parameters' ...` | Add `.parameters` and optionally one member |
| A bind must pair whole set with whole port, or member with member | `Parameter binds must bind a whole set to ... or one set member to ...` | Match the shapes on both sides |
| A per-member bind must use `<set>.<member>` | `Parameter bind sources must be '<set>' or '<set>.<member>'` | Use exactly one set member |
| A set usage must not mix identity and per-member binds | `mixes whole-object and per-member parameter binds for set ...` | Choose one form |
| A bound component must have an interface | `... declares no parameter interface` | Add a port or remove the bind |
| Identity bind members must exist in the interface | `Whole-object bind ... cannot map set members ...` | Rename members or use explicit binds |
| A per-member bind must name a set member | `Parameter set 'S' has no member 'x'` | Fix the set member name |
| A per-member bind must name an interface member | `Parameter interface 'P' has no member 'x'` | Fix the port member name |
| Binds inside nested part definitions are rejected | `Parameter binds inside nested part definition 'X' are not supported` | Move the bind to the composition root |

Valid identity:

```sysml
attribute nominal : NominalSet;
bind comp.parameters = nominal;
```

Valid explicit:

```sysml
attribute nominal : NominalSet;
bind comp.parameters.count = nominal.n;
```

Invalid identity with renamed members:

```sysml
attribute nominal : NominalSet;   // member n
bind comp.parameters = nominal;    // interface member count
```

```text
Whole-object bind of 'nominal' to comp cannot map set members n;
use per-member binds for differently named parameters
```

Invalid bind inside a nested part definition:

```sysml
part def Outer {
  part inner : Inner;
  attribute nominal : NominalSet;
  bind inner.parameters.k = nominal.k;  // rejected
}
```

Move the set usage and bind to the composition that owns `outer`.

## 5. Multiple sets and disjointness

| Rule | Diagnostic | Fix |
| --- | --- | --- |
| No target parameter may be bound twice | `Multiple parameter sets bind 'comp.count': ...` | Make target members disjoint or use one set |
| List members are whole-feature targets | Same overlap diagnostic | Do not apply two sets to different indices of the same list |
| Identity and explicit binds count by target member | Same overlap diagnostic | Inspect the effective mapping entries |

Valid:

```sysml
bind comp.parameters.count = counts.n;
bind comp.parameters.gain = gains.k;
```

Invalid:

```sysml
bind comp.parameters.count = counts_a.n;
bind comp.parameters.count = counts_b.m;
```

```text
Multiple parameter sets bind 'comp.count': counts_a, counts_b.
Use disjoint target members.
```

### Why this is an error

SysML `bind` is equality, not override. SSP does define precedence for
multiple `ParameterBinding`s, but the SysML dialect deliberately does not
invent a declaration order. Disjoint targets are the deterministic choice.

## 6. Types and multiplicity

| Rule | Diagnostic | Fix |
| --- | --- | --- |
| Set and interface types must match | `has incompatible types: ... vs ...` | Change the interface or the set value type |
| Lists must have a fixed length | `has unbounded multiplicity '[0..*]'` | Use `[N]` |
| Set tuple length must match interface multiplicity | `provides N values but ... declares [M]` | Fix the tuple or the multiplicity |
| A list-valued set member needs a list target | `is list-valued but target ... does not declare a multiplicity` | Add `[N]` to the interface |
| A scalar set member cannot target a list | `must provide N values ... got a scalar` | Make the set member a tuple |
| Indexed mappings must match on both sides | `must map matching indices` / `must use indices on both sides or on neither side` | Map `x[i]` to `y[i]` |

Valid:

```sysml
port def P :> ParameterInterface {
  attribute xs : Real[3];
}
attribute def S :> ParameterSet {
  attribute xs = (1.0, 2.0, 3.0);
}
bind comp.parameters.xs = s.xs;
```

Invalid unbounded:

```sysml
attribute xs : Real[0..*];
```

```text
Parameter 'xs' has unbounded multiplicity '[0..*]';
SSP parameters need a fixed length
```

Invalid length:

```sysml
attribute def S :> ParameterSet {
  attribute xs = (1.0, 2.0);  // interface is Real[3]
}
```

```text
'xs' provides 2 values but 'xs' declares [3]
```

## 7. Names

| Rule | Diagnostic | Fix |
| --- | --- | --- |
| `pyssp_` is reserved | `uses the reserved 'pyssp_' prefix` | Rename the parameter |
| SysML keywords are rejected | `uses reserved SysML keyword 'part'` | Rename the parameter |
| SSD parameter names must be flat | `Parameter connector '...' cannot be represented as a SysML attribute name` | Use a flat name; nested parameter groups are unsupported |
| Generated set names must not collide | Synthesized `_2` suffix | Rename the set for a stable model |
| `parameters` is reserved for the port | Set usage may be renamed to `parameters_set` | Avoid naming a set `parameters` if stable names matter |
| Nested component paths are allowed in targets | — | Use `outer.inner.parameters.k` |
| Dotted parameter names are not allowed | `cannot be represented` / bind shape error | Keep parameter names flat |

Invalid:

```sysml
attribute def BadSet :> ParameterSet {
  attribute part = 1.0;
}
```

```text
Parameter 'part' uses reserved SysML keyword 'part'
```

Invalid SSD connector:

```xml
<ssd:Connector name="gains.k" kind="parameter">...</ssd:Connector>
```

```text
Parameter connector 'gains.k' cannot be represented as a SysML
attribute name
```

## 8. Composition and nesting

| Rule | Diagnostic | Fix |
| --- | --- | --- |
| Part references must resolve | `Unresolved part definition for ...` | Add the part definition |
| Recursive part hierarchies are rejected | `Recursive part hierarchy at '...' (...)` | Break the part-definition cycle |
| A system cannot also be an FMU | `has both subparts and 'pyssp_implementation'` | Remove the implementation or the subparts |
| Nested SSD systems are supported recursively | — | Use nested part definitions/usages |
| Bind targets may use nested part paths | — | `outer.inner.parameters.k` |
| A nested system may own an interface | — | Put a port on the nested system part definition |
| Top-level SSD system parameter connectors are rejected | `Top-level SSD system parameter connectors are not supported` | Attach connectors to a component/nested-system element |

Invalid recursive parts:

```sysml
part def A { part b : B; }
part def B { part a : A; }
```

```text
Recursive part hierarchy at 'a.b' (A)
```

## 9. Generation selection and SSD/sync diagnostics

| Rule | Diagnostic | Fix |
| --- | --- | --- |
| `--output` requires exactly one set | `A single --output file requires exactly one parameter set; selected N` | Select one `--set`, or write to an output directory |
| `--set` must name a known set | `Unknown parameter set 'X'` | Fix the set definition name |
| A set must have values to produce an SSV | `Parameter set 'X' has no values` | Add values or do not select it |
| Referenced SSV must exist | `Parameter set source not found: ...` | Generate/copy the SSV next to the SSD |
| Referenced SSM must exist | source resolution error | Generate/copy the SSM |
| Mapping sources must exist in the SSV | `Parameter mapping source '...' is not present in the parameter set` | Fix the SSM or the SSV |
| Bound component must have parameter connectors | `... but that component has no parameter connectors` | Add connectors or remove the binding |
| Set members must exist on the component | `Parameter set members ... do not exist on component ...` | Fix the set/mapping or the connectors |
| Sync connections must use `port.attribute` | `Connector '...' is not in 'port.attribute' form` | Normalize the SSD connector |
| Sync requires complete port mappings | `partial/invalid attribute mapping ... missing=..., extra=...` | Map all attributes consistently |
| Sync requires compatible ports | `SSD connects incompatible ports ...` | Connect compatible port definitions |
| Unknown sources can be rejected | `references unknown part source '...'` | Add the part definition or allow synthesis |
| Unknown ports can be rejected | `Unknown source port ...` / `Unknown destination ...` | Fix the SSD or the model |
| The composition must exist | `Part not found: ...` | Fix `--composition` |

`sync` with `--no-synthesize` fails on an unknown FMU source instead of
creating a part definition:

```bash
pyssp sync ssd ... --no-synthesize
```

```text
references unknown part source 'resources/ExternalSink.fmu'
```

## 10. Warnings

Warnings do not stop generation.

| Warning | Meaning | Action |
| --- | --- | --- |
| `Parameter set 'S' members x are not bound to comp; SSP will ignore them` | An explicit-mapping set has valued members that are not part of this application | Expected for partial applications; bind them or ignore |
| DFA cache warning from sysmlpy | Parser cache save failed | Harmless; suppressed by the adapter at import |

## 11. Things that are valid but look suspicious

These are intentional:

- A component interface with no applied set.
- A set applied explicitly to only a subset of its members.
- Extra interface members that no set provides.
- Multiple set usages of the same set definition on different components.
- A nested system with its own parameter interface.
- A leaf component with a flat legacy parameter dialect.
- A nested SSD `System` with no parameter connectors.

## 12. Pre-flight checklist

Before running a generator:

- [ ] Markers exist.
- [ ] Every port is typed by a marked interface.
- [ ] Every set usage is typed by a marked set.
- [ ] No part mixes a port with flat attributes.
- [ ] No composition mixes parameter ports and legacy components.
- [ ] The composition has no `parameters` port.
- [ ] All binds are at the composition root.
- [ ] Every bind target is a declared set usage/member.
- [ ] Every bind source names a component parameter port.
- [ ] Multiple sets have disjoint effective targets.
- [ ] List multiplicities are fixed and lengths match.
- [ ] Parameter names avoid `pyssp_` and SysML keywords.
- [ ] Nested SSD parameter connectors are flat names.
- [ ] Referenced SSV/SSM files are next to the SSD.
- [ ] Sync SSD connectors use `port.attribute` form.

## 13. Source of truth

- `src/pyssp_sysml2/parameters.py`
- `src/pyssp_sysml2/parameter_synthesis.py`
- `src/pyssp_sysml2/ssd.py`
- `src/pyssp_sysml2/sysml.py`
- `src/pyssp_sysml2/sync.py`
- `tests/test_parameter_sets.py`
- `tests/test_generate_sysml.py`
- `tests/test_sync.py`
