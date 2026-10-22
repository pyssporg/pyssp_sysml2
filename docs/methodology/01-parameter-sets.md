# 01 — Parameter Sets

> **Status: implemented.** This chapter describes the current dialect and the
> current generators. The proposed inheritance/union extension is documented
> separately in [Parameter-set reuse](proposals/parameter-set-reuse.md).

## 1. Why split interface from values?

A simulation component has two different parameter concerns:

1. **What parameters exist?** Names, types, fixed lengths, optional defaults.
2. **Which values should a particular study use?** A nominal mission, an
   aggressive mission, a trimmed configuration, and so on.

The dialect separates them:

- a **parameter interface** describes the component surface;
- a **parameter set** is one reusable bundle of values;
- a **bind** in a composition applies a set to a component usage.

This keeps the component definition stable while scenarios are added as new
sets.

## 2. The three objects

| Object | SysML form | SSP consequence |
| --- | --- | --- |
| Parameter interface | `port def X :> ParameterInterface` | SSD parameter connectors and FMI parameter variables |
| Parameter set | `attribute def Y :> ParameterSet` | one SSV file named after the set |
| Set application | `attribute s : Y;` plus `bind ...` in a composition | one SSD `ParameterBinding`, plus an SSM for explicit mappings |

A set is **not** a component. It is a value bundle that is applied to a
component usage.

> **Design note.** `ParameterInterface` and `ParameterSet` are project markers,
> not standard SysML v2 library types. They are ordinary empty defs — a `port
> def` for the interface marker, an `attribute def` for the set marker — whose
> meaning comes from this dialect. SysML v2 has no built-in parameter-set
> construct; `bind` is used here as a mapping declaration. In SysML itself,
> `bind` is an equality constraint, not an assignment or override.
>
> The current implementation recognizes only direct marker specialization. It
> does **not** flatten inherited set/interface members. Set inheritance and
> union are proposed in
> [Parameter-set reuse](proposals/parameter-set-reuse.md).

## 3. Minimum complete example

```sysml
package ParameterDemo {
  port def ParameterInterface;
  attribute def ParameterSet;

  port def AutopilotParameters :> ParameterInterface {
    attribute waypointCount : Integer;
    attribute waypointX_km : Real[3];
  }

  attribute def NominalSet :> ParameterSet {
    attribute waypointCount = 10;
    attribute waypointX_km = (0.0, 10.0, 20.0);
  }

  part def AutopilotModule {
    in port parameters : AutopilotParameters;
  }

  part def AircraftComposition {
    part autopilot : AutopilotModule;

    attribute nominal : NominalSet;

    bind autopilot.parameters = nominal;
  }
}
```

What each piece means:

- `port def ParameterInterface;` and `attribute def ParameterSet;` are
  **marker definitions**. They must exist in the package. They have no members.
- `AutopilotParameters` is the **interface** of `AutopilotModule`. Its members
  are the parameter names the component understands.
- `NominalSet` is a reusable **set** of values. Its member names are SSV
  parameter names.
- `in port parameters : AutopilotParameters;` is the **fixed port** that
  connects a part definition to its parameter interface.
- `attribute nominal : NominalSet;` declares a **set usage** in the
  composition.
- `bind autopilot.parameters = nominal;` applies the set to the component.

Generated artifacts for this model:

```text
parameter_sets/NominalSet.ssv
  waypointCount = 10
  waypointX_km[0] = 0.0
  waypointX_km[1] = 10.0
  waypointX_km[2] = 20.0

SystemStructure.ssd
  Component name="autopilot" source="resources/AutopilotModule.fmu"
  Parameter connectors: waypointCount, waypointX_km[0..2]
  ParameterBinding source="parameter_sets/NominalSet.ssv" prefix="autopilot."

model_descriptions/AutopilotModule/modelDescription.xml
  Parameters: waypointCount, waypointX_km[0..2]
```

The FMI model description contains the interface, not the applied set values.
The set is a runtime SSP mapping.

## 4. The naming model

There are three names to keep apart:

```text
bind autopilot.parameters.waypointCount = nominal.n_waypoints
     ^^^^^^^^^ ^^^^^^^^^^ ^^^^^^^^^^^^^   ^^^^^^^ ^^^^^^^^^^^
     component port        interface      set      set member
     path                 member         usage
```

- The **set member name** becomes the SSV parameter name.
- The **interface member name** becomes the SSD parameter connector name and
  the FMI variable name.
- The **parameter port on the left** determines the SSP hierarchical target
  name, for example `autopilot.waypointCount`.

The bind is always written with the parameter port on the left. SSP stores the
mapping in the opposite order, so this is expected:

```text
SysML:  bind autopilot.parameters.waypointCount = nominal.n_waypoints;
SSP:    <ssm:MappingEntry source="n_waypoints" target="autopilot.waypointCount"/>
```

An explicit bind is therefore a rename:

```text
SSV:       n_waypoints
SSD/SSM:   n_waypoints -> autopilot.waypointCount
FMI name:  waypointCount
```

An identity bind requires the names to be the same.

## 5. Identity binding

An identity bind applies a whole set by matching member names:

```sysml
port def AutopilotParameters :> ParameterInterface {
  attribute waypointCount : Integer;
  attribute waypointX_km : Real[3];
}

attribute def NominalSet :> ParameterSet {
  attribute waypointCount = 10;
  attribute waypointX_km = (0.0, 10.0, 20.0);
}

part def AircraftComposition {
  part autopilot : AutopilotModule;
  attribute nominal : NominalSet;
  bind autopilot.parameters = nominal;
}
```

Rules:

- Every **valued** set member must exist in the interface with the same
  primitive type and the same multiplicity.
- Interface members that the set does not provide are ignored by this
  application. They may be set elsewhere or remain at their interface default.
- A valued set member that does not exist in the interface is an error; this
  is not a silent skip.
- Lists are expanded element-wise in the SSP mapping.
- SSP represents an identity bind as a `ParameterBinding` with a prefix and
  **no SSM**:

```xml
<!-- abridged -->
<ssd:ParameterBinding
    source="parameter_sets/NominalSet.ssv"
    prefix="autopilot." />
```

The prefix means “prepend `autopilot.` to every name in the SSV”. A source
parameter `waypointCount` therefore targets `autopilot.waypointCount`.

### Identity with a nested component path

Identity is not limited to top-level components:

```sysml
part def Outer {
  part inner : Inner;
}

part def SystemComposition {
  part outer : Outer;
  attribute nominal : NominalSet;
  bind outer.inner.parameters = nominal;
}
```

The generated prefix is `outer.inner.`, and the target namespace is the nested
component path.

### Identity is not a fallback for renamed members

This is **invalid**:

```sysml
attribute def NominalSet :> ParameterSet {
  attribute n_waypoints = 10;          // different name
}

part def AircraftComposition {
  part autopilot : AutopilotModule;
  attribute nominal : NominalSet;
  bind autopilot.parameters = nominal; // error: n_waypoints is not in the interface
}
```

Use an explicit bind for differently named parameters.

## 6. Explicit per-member binding

Explicit binds are one bind per set member:

```sysml
port def AutopilotParameters :> ParameterInterface {
  attribute waypointCount : Integer;
  attribute waypointX_km : Real[3];
}

attribute def NominalSet :> ParameterSet {
  attribute n_waypoints = 10;
  attribute waypoints_x_km = (0.0, 10.0, 20.0);
}

part def AircraftComposition {
  part autopilot : AutopilotModule;
  attribute nominal : NominalSet;

  bind autopilot.parameters.waypointCount = nominal.n_waypoints;
  bind autopilot.parameters.waypointX_km = nominal.waypoints_x_km;
}
```

SSP consequence:

```text
SSV: NominalSet.ssv
  n_waypoints = 10
  waypoints_x_km[0..2] = ...

SSD ParameterBinding:
  source="parameter_sets/NominalSet.ssv"
  ParameterMapping:
    n_waypoints       -> autopilot.waypointCount
    waypoints_x_km[0] -> autopilot.waypointX_km[0]
    waypoints_x_km[1] -> autopilot.waypointX_km[1]
    waypoints_x_km[2] -> autopilot.waypointX_km[2]
```

`generate ssm` can also write the mapping as a standalone file:

```text
NominalSet_autopilot.ssm
```

The inline SSD mapping is the default. The standalone SSM is optional.

### Explicit binds may cover a subset

A set can apply only some of its members:

```sysml
attribute def NominalSet :> ParameterSet {
  attribute n_waypoints = 10;
  attribute reserve_km = 5.0;
}

bind autopilot.parameters.waypointCount = nominal.n_waypoints;
```

`reserve_km` is not applied. The generator emits a warning:

```text
Parameter set 'NominalSet' members reserve_km are not bound to autopilot;
SSP will ignore them
```

This is useful for large reusable data sets where a given component consumes
only a subset. It is a warning, not an error, for explicit binds.

### Mixing identity and explicit forms for one set usage is invalid

A single set usage must use one form:

```sysml
attribute nominal : NominalSet;

bind autopilot.parameters = nominal;                    // identity
bind autopilot.parameters.count = nominal.n_waypoints;  // invalid mix
```

Use either a whole-object bind or per-member binds for that usage.

### Invalid bind shapes

These are rejected:

```sysml
bind autopilot.parameters.count = nominal;        // whole set into one member
bind autopilot.parameters = nominal.n_waypoints;  // whole port from one member
bind autopilot.parameters.count = nominal.a.b;    // set path deeper than one
bind autopilot.parameters.a.b = nominal.n_waypoints; // parameter path deeper than one
```

The current grammar for a parameter bind is:

```text
bind <component-path>.parameters[.<interface-member>] = <set-usage>[.<set-member>]
```

where `<component-path>` may itself contain dots for nested parts. A bind that
puts the set usage on the left is rejected with the rewritten form.

## 7. Multiple sets on one component

A component may have several applied sets, provided their target members are
**disjoint**.

```sysml
port def Params :> ParameterInterface {
  attribute count : Integer;
  attribute gain : Real;
}

attribute def Counts :> ParameterSet {
  attribute n = 10;
}

attribute def Gains :> ParameterSet {
  attribute k = 2.5;
}

part def Comp {
  in port parameters : Params;
}

part def Composition {
  part comp : Comp;
  attribute counts : Counts;
  attribute gains : Gains;

  bind comp.parameters.count = counts.n;
  bind comp.parameters.gain = gains.k;
}
```

This is valid. It produces:

- two SSVs: `Counts.ssv`, `Gains.ssv`;
- two SSD `ParameterBinding`s;
- two SSMs if explicit mappings are exported separately.

### Overlapping targets are rejected

```sysml
attribute def CountsA :> ParameterSet { attribute n = 10; }
attribute def CountsB :> ParameterSet { attribute m = 20; }

part def Composition {
  part comp : Comp;
  attribute counts_a : CountsA;
  attribute counts_b : CountsB;

  bind comp.parameters.count = counts_a.n;
  bind comp.parameters.count = counts_b.m;  // same target
}
```

Error:

```text
Multiple parameter sets bind 'comp.count': counts_a, counts_b.
Use disjoint target members.
```

Why reject instead of “last one wins”? SysML `bind` is an equality
constraint, not an assignment or an override. SSP does define precedence for
multiple `ParameterBinding`s, but the SysML dialect does not invent an order.
Disjoint targets keep the mapping deterministic.

### List members are whole-feature targets

You cannot bind a single list index:

```sysml
bind comp.parameters.xs[0] = counts.n;  // not a supported bind shape
```

A bind addresses the whole `xs` list feature. Therefore two sets that both
bind `xs` overlap even if their SSVs happen to mention different indices.

### Same set definition, different components

One set definition can be applied to several component usages:

```sysml
attribute def Composition {
  part left : Comp;
  part right : Comp;
  attribute nominal : NominalSet;

  bind left.parameters = nominal;
  bind right.parameters = nominal;
}
```

The generator writes one `NominalSet.ssv` and two `ParameterBinding`s. The
disjointness rule is evaluated per component, so this is valid.

## 8. Nested part paths

Set targets use the component hierarchy, not a separate parameter namespace:

```sysml
package NestedDemo {
  port def ParameterInterface;
  attribute def ParameterSet;

  port def InnerParameters :> ParameterInterface {
    attribute k : Real;
  }

  attribute def NominalSet :> ParameterSet {
    attribute k = 3.0;
  }

  part def Inner {
    in port parameters : InnerParameters;
  }

  part def Outer {
    part inner : Inner;
  }

  part def SystemComposition {
    part outer : Outer;
    attribute nominal : NominalSet;
    bind outer.inner.parameters.k = nominal.k;
  }
}
```

Generated SSD shape:

```xml
<!-- abridged -->
<ssd:System name="SystemComposition">
  <ssd:ParameterBindings>
    <ssd:ParameterBinding source="parameter_sets/NominalSet.ssv">
      <ssd:ParameterMapping>
        <ssm:ParameterMapping version="1.0">
          <ssm:MappingEntry source="k" target="outer.inner.k" />
        </ssm:ParameterMapping>
      </ssd:ParameterMapping>
    </ssd:ParameterBinding>
  </ssd:ParameterBindings>
  <ssd:Elements>
    <ssd:System name="outer">
      <ssd:Elements>
        <ssd:Component name="inner" source="resources/Inner.fmu">
          <ssd:Connectors>
            <ssd:Connector name="k" kind="parameter">
              <ssc:Real />
            </ssd:Connector>
          </ssd:Connectors>
        </ssd:Component>
      </ssd:Elements>
    </ssd:System>
  </ssd:Elements>
</ssd:System>
```

Important distinctions:

- `outer.inner` is a **component path**.
- `k` is the **interface member**.
- There is no “set group path” in the current dialect.
  `bind outer.inner.parameters.k = nominal.gains.k` is not supported because
  sets cannot contain sets.

### Multiple disjoint sets at a nested path

The same rules apply inside a nested system:

```sysml
part def Outer {
  part inner : Inner;
}

part def SystemComposition {
  part outer : Outer;
  attribute counts : Counts;
  attribute gains : Gains;

  bind outer.inner.parameters.count = counts.n;
  bind outer.inner.parameters.gain = gains.k;
}
```

This produces two bindings with targets `outer.inner.count` and
`outer.inner.gain`.

### Nested systems can own a parameter interface

A nested system is also a parameterable element:

```sysml
port def OuterParameters :> ParameterInterface {
  attribute gain : Real = 2.0;
}

attribute def OuterSet :> ParameterSet {
  attribute g = 4.0;
}

part def Outer {
  in port parameters : OuterParameters;
  part inner : Inner;
}

part def SystemComposition {
  part outer : Outer;
  attribute outer_set : OuterSet;
  bind outer.parameters.gain = outer_set.g;
}
```

The generated SSD has a nested `System name="outer"` with a parameter
connector `gain`, and the binding target is `outer.gain`.

## 9. Lists and fixed multiplicity

Parameter lists use declared multiplicity on the interface and a tuple value
on the set:

```sysml
port def AutopilotParameters :> ParameterInterface {
  attribute waypointX_km : Real[3];
}

attribute def NominalSet :> ParameterSet {
  attribute waypoints_x_km = (0.0, 10.0, 20.0);
}

bind autopilot.parameters.waypointX_km = nominal.waypoints_x_km;
```

Consequences:

- SSD/FMI parameter names expand to `waypointX_km[0]`, `[1]`, `[2]`.
- The SSV writes `waypoints_x_km[0]`, `[1]`, `[2]`.
- The SSM/mapping expands both sides element-wise.
- The set tuple length must match the interface multiplicity.
- Only fixed lengths are supported.

Invalid:

```sysml
attribute waypointX_km : Real[0..*];  // unbounded
```

Error:

```text
Parameter 'waypointX_km' has unbounded multiplicity '[0..*]';
SSP parameters need a fixed length
```

Invalid length:

```sysml
attribute def NominalSet :> ParameterSet {
  attribute waypoints_x_km = (0.0, 10.0);  // 2 values for Real[3]
}
```

Error:

```text
'waypoints_x_km' provides 2 values but 'waypointX_km' declares [3]
```

Lists of scalars are supported. Lists of sets or nested parameter groups are
not part of the current dialect.

## 10. Types and compatibility

Supported primitive parameter types are:

```text
Real
Integer
Boolean
String
```

The set member type and the interface member type must be compatible. The
generator reports an error such as:

```text
Parameter mapping 'n_waypoints' -> 'waypointCount' has incompatible types:
Real vs Integer
```

Use an interface type that matches the value type:

```sysml
attribute waypointCount : Integer;   // interface
attribute n_waypoints = 10;          // Integer value
```

Explicit type annotations on set members are allowed:

```sysml
attribute n_waypoints : Integer = 10;
```

If a set member has no declared type, its type is inferred from the value.
If it has neither a value nor a declared type, it does not provide a value and
is not written to the SSV. Do not bind a value-less member explicitly; the
SSV would not contain the source parameter.

## 11. Naming rules and reserved names

### The parameter port is named `parameters`

```sysml
in port parameters : AutopilotParameters;
```

Only this fixed name is recognized. A part definition may have at most one
`parameters` port. A `parameters` port on the composition root is rejected;
attach interfaces to component or nested-system usages instead.

### `pyssp_` is reserved for control metadata

Names beginning with `pyssp_` are control attributes. They are skipped by
parameter generation. Do not use them as parameter names:

```sysml
attribute pyssp_gain = 1.0;  // treated as metadata, not a parameter
```

### SysML keywords are rejected as parameter names

Member names become SysML features when generating a model from an SSD. Names
such as `part`, `port`, `attribute`, `bind`, `typed`, and `comment` are
rejected instead of producing a file that cannot be parsed back.

```sysml
attribute def BadSet :> ParameterSet {
  attribute part = 1.0;  // invalid in the parameter dialect
}
```

### Set usage names

The set usage name is local to the composition:

```sysml
attribute nominal : NominalSet;
```

It does not have to match the set definition name. The usage name is the left
side of the bind.

When `generate sysml` synthesizes a model from an SSD, it derives a usage name
from the SSV/set name. If that name collides with an existing attribute or
part in the composition, it appends a numeric suffix. If the set name is
`parameters`, it uses `parameters_set` to avoid the reserved port name.

## 12. Interface-only models

A component can declare an interface without applying a set:

```sysml
port def Params :> ParameterInterface {
  attribute count : Integer = 10;
}

part def Comp {
  in port parameters : Params;
}

part def Composition {
  part comp : Comp;
}
```

Consequences:

- `generate ssd` emits the parameter connectors but no `ParameterBinding`.
- `generate fmi` emits parameter variables, using interface defaults as FMI
  `start` values where declared.
- `generate ssv` writes nothing because no set is applied.

This is useful when the component is parameterized externally or later in the
workflow.

## 13. Legacy flat-attribute parameters

Before interfaces/sets, a leaf component could declare its parameters directly:

```sysml
part def Comp {
  attribute gain : Real = 2.0;
  attribute count : Integer = 10;
}
```

For a leaf component, non-control attributes are treated as parameters. This
still works for `generate ssd` and `generate fmi`.

Limits:

- A part definition cannot mix a `parameters` port with flat parameter
  attributes.
- Flat attributes on the **top composition** are not parameters; only leaf
  component definitions are parameterized.
- `sync ssd` does not migrate a legacy flat-attribute architecture to
  interfaces/sets. It preserves the legacy model.
- The legacy `pyssp_parameter_set` attribute on the composition can still
  point at an SSV.

Invalid mixing:

```sysml
part def Comp {
  in port parameters : Params;
  attribute gain : Real;  // error: mixed dialects
}
```

## 14. What is not supported

These are intentional current limits, not parser accidents:

| Not supported | Why / consequence |
| --- | --- |
| A parameter set inside a parameter set | SSP has a flat parameter list. A nested set would require dotted names or multiple sets; see the proposal page. |
| Set inheritance/union | Proposed only; see [Parameter-set reuse](proposals/parameter-set-reuse.md). |
| Parameter groups inside an interface | Interface members are flat. `parameters.gains.k` is not a valid bind target. |
| Top-level composition parameter interface | The composition is not a parameter target; attach interfaces to component/nested-system usages. |
| Top-level SSD system parameter connectors | Rejected when generating SysML; SSP system-level parameters are not represented by the dialect. |
| Bindings inside a nested part definition | Apply sets at the composition root and target nested usages from there. |
| Unbounded multiplicity | SSP parameters need a fixed length. |
| SSM transformations or unit conversion | Only identity and plain source→target mapping are generated. |
| Multiple `parameters` ports | The port name is fixed and unique per part definition. |
| Dotted parameter names | Not representable as SysML feature names in the current dialect. |

## 15. Bind-shape cheat sheet

| Intent | Valid syntax | Generated form |
| --- | --- | --- |
| Apply a set by matching names | `bind autopilot.parameters = nominal;` | `ParameterBinding` + prefix |
| Apply one member with a rename | `bind autopilot.parameters.count = nominal.n;` | inline mapping / SSM |
| Apply to a nested component | `bind outer.inner.parameters.k = nominal.k;` | target `outer.inner.k` |
| Apply to a nested system port | `bind outer.parameters.gain = nominal.g;` | target `outer.gain` |
| Apply two disjoint sets | `bind comp.parameters.count = counts.n;` plus `bind comp.parameters.gain = gains.k;` | two SSVs and two bindings |
| Apply a list | `bind comp.parameters.xs = nominal.xs;` | element-wise `xs[i]` mappings |
| Declare only an interface | no bind | connectors and FMI defaults only |

## 16. Related runnable examples

The handbook examples are self-contained and use the same package structure as
normal models:

- [Identity](examples/parameter-sets/identity/model.sysml)
- [Explicit rename](examples/parameter-sets/explicit/model.sysml)
- [Multiple disjoint sets](examples/parameter-sets/multiple/model.sysml)
- [Nested component path](examples/parameter-sets/nested/model.sysml)

See the [examples README](examples/parameter-sets/README.md) for generation
commands and expected artifacts.

## 17. Source of truth

The behavior in this chapter is enforced by:

- `src/pyssp_sysml2/parameters.py` — interface/set resolution, bind parsing,
  multiple-set disjointness, mapping entries;
- `src/pyssp_sysml2/ssv.py` — SSV writing;
- `src/pyssp_sysml2/ssd.py` — parameter connectors and `ParameterBinding`;
- `src/pyssp_sysml2/fmi.py` — FMI parameter variables;
- `src/pyssp_sysml2/parameter_synthesis.py` — SSD→SysML synthesis;
- `tests/test_parameter_sets.py`, `tests/test_generate_sysml.py`,
  `tests/test_roundtrip.py`, and `tests/test_sync.py`.

If a rule here is incomplete, add the missing rule to the code and tests first,
then update this chapter.
