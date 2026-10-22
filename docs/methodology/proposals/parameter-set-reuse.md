# Proposal — Parameter-set reuse by inheritance and union

> **Status: proposed — not implemented.**
>
> This page records the agreed design direction for reusing parameter sets in
> SysML v2. The current tooling does **not** accept inherited sets or `:>>`
> redefinitions. Do not use the examples below in working models until the
> implementation lands.

## 1. Problem

A study often needs several variants of the same parameters:

- a nominal set;
- an aggressive set that changes a few values;
- a sensor set that adds unrelated values;
- a combined set that reuses both.

The current dialect has two options:

1. duplicate values in each set;
2. apply multiple disjoint sets to one component.

Neither expresses “this set is the nominal set plus these changes” or “this
set is the union of these reusable sets.”

## 2. Why not a set inside a set

A parameter set inside a parameter set is containment. SSP does not have
contained parameter sets: an SSV is a flat list of uniquely named parameters.
Containment would force one of:

- dotted parameter names such as `gains.k`, which collide conceptually with
  SSP’s hierarchical component names;
- multiple SSVs and multiple `ParameterBinding`s behind one SysML bind.

Both add complexity and ambiguity that reuse does not require.

Inheritance is different: it is definition-time reuse. The effective set is
computed in SysML, then flattened into one SSP parameter set. SSP sees no
inheritance.

## 3. Proposed SysML v2 contract

### 3.1 Base set

```sysml
attribute def NominalSet :> ParameterSet {
  attribute n_waypoints = 10;
  attribute waypoints_x_km = (0.0, 10.0, 20.0);
}
```

A base set is a normal parameter set with values.

### 3.2 Additive reuse

```sysml
attribute def AggressiveSet :> NominalSet {
  attribute max_speed = 15.0;
}
```

`AggressiveSet` effectively contains all `NominalSet` members plus
`max_speed`.

### 3.3 Value override

Use standard SysML redefinition:

```sysml
attribute def AggressiveSet :> NominalSet {
  attribute n_waypoints : Integer :>> NominalSet::n_waypoints = 20;
  attribute max_speed = 15.0;
}
```

The short form is also valid:

```sysml
attribute n_waypoints :>> NominalSet::n_waypoints = 20;
```

Effective values:

```text
n_waypoints     = 20
waypoints_x_km  = inherited from NominalSet
max_speed       = 15
```

### 3.4 Multiple inheritance as union

```sysml
attribute def SensorSet :> ParameterSet {
  attribute range = 100.0;
}

attribute def CombinedSet :> AggressiveSet, SensorSet {
  attribute extra_margin = 2.0;
}
```

`CombinedSet` effectively contains:

```text
n_waypoints
waypoints_x_km
max_speed
range
extra_margin
```

`ParameterSet` need not be repeated on `CombinedSet`; it is a parameter set
transitively through both bases.

### 3.5 Conflict

```sysml
attribute def A :> ParameterSet { attribute gain = 1.0; }
attribute def B :> ParameterSet { attribute gain = 2.0; }

attribute def C :> A, B;  // invalid unless C redefines gain
```

`C` must explicitly resolve the conflict:

```sysml
attribute def C :> A, B {
  attribute gain : Real :>> A::gain, B::gain = 3.0;
}
```

There is no “first base wins” or “last base wins” rule. Explicit redefinition
is the only way to resolve an ambiguity.

## 4. Effective set semantics

For every set definition, compute an **effective member map**:

1. Recursively collect effective members from all supertypes.
2. Ignore the `ParameterSet` marker itself.
3. Merge members by name.
4. Apply direct attributes:
   - new name → add;
   - inherited name with `:>>` → override;
   - inherited name without `:>>` → error.
5. If distinct supertypes define the same member and there is no direct
   redefinition, error.
6. A member inherited through a diamond from the same origin counts once.
7. Detect cycles, unknown supertypes, and non-set supertypes.

Rules:

- Every supertype of a parameter set must itself be a parameter set, or the
  `ParameterSet` marker.
- A direct redefinition must have a compatible primitive type and
  multiplicity.
- A redefinition without a value inherits the base value.
- A redefinition with a value overrides it.
- Values from base sets cannot be removed. A derived set always inherits a
  base member's value unless it overrides it.
- Direct new members must not collide with inherited names.
- The declared `definition.attributes` remains the direct member set. The
  effective map is a computed view; do not flatten inherited members into the
  definition.

## 5. Set application

```sysml
part def Composition {
  part autopilot : AutopilotModule;
  attribute aggressive : AggressiveSet;
  bind autopilot.parameters.waypointCount = aggressive.n_waypoints;
}
```

- A set usage sees all effective members.
- Identity binds match effective member names.
- Explicit binds can target inherited members.
- Multiple sets applied to one component are checked for disjointness using
  effective members.
- Applying both `NominalSet` and `AggressiveSet` to the same component
  conflicts because `AggressiveSet` inherits all `NominalSet` members.

## 6. SSP transfer

The effective set is flattened into one SSV:

```text
AggressiveSet.ssv
  n_waypoints = 20
  waypoints_x_km[0..2] = ...
  max_speed = 15
```

- One applied set definition → one SSV.
- Member names stay flat.
- No dotted group names.
- No inheritance metadata in SSP.
- Base definitions are not emitted unless they are themselves applied.
- `generate ssd` writes one `ParameterBinding` for the applied set.
- `generate ssm` can map inherited members by their effective names.
- `generate fmi` uses effective interface members if interface inheritance is
  implemented; the applied set remains a runtime mapping.

This is the main advantage over containment: SSP stays deterministic and flat.

## 7. Round-trip and sync

### Generation

`generate sysml --ssd ...` has no inheritance metadata. It should synthesize a
**flat** set. Inheritance is an authoring-level reuse mechanism, not an SSP
artifact.

### Sync overlay

If `sync ssd` finds an existing set definition with the same name, it should
preserve inheritance:

- If the SSD value differs from an inherited value, add/update a `:>>`
  redefinition on the derived set.
- If the SSD value equals the inherited value, remove a redundant override and
  fall back to the base.
- If the member is new, add a direct attribute.
- If a direct new member is absent from the SSD, remove it.
- Inherited members absent from the SSD keep their base value.

This keeps derived sets small:

```sysml
attribute def AggressiveSet :> NominalSet {
  attribute n_waypoints : Integer :>> NominalSet::n_waypoints = 20;
}
```

instead of materializing every inherited value after the first sync.

Updating a base set affects every derived set that inherits it. That is the
expected consequence of reuse and should be documented in the model.

## 8. Current adapter gap

The current code cannot represent this proposal yet:

- `is_parameter_set()` and `is_parameter_interface()` only check direct
  `:> ParameterSet` / `:> ParameterInterface`; they are not transitive.
- `parameter_declarations()`, `mapping_entries()`, `write_parameter_set()`,
  `_signature()`, and `add_set()` use only direct `definition.attributes`.
- `parameter_synthesis` clears direct attributes during sync; it does not
  preserve inherited members.
- The repo `Attribute` model has no `redefines` field.
- The loader drops sysmlpy’s redefinition information.
- The exporter emits a same-named attribute without `:>>`, so an override
  would not round-trip as a standard SysML redefinition.

The parser already accepts the standard form:

```sysml
attribute y : Real :>> A::y = 2.0;
```

and records the target in the usage (sysmlpy's `_redefined_refs`; the public
`redefined_name` only covers the bare form). The adapter needs to preserve it.

## 9. Implementation phases

### Phase A — model support

- Add `Attribute.redefines: tuple[str, ...]`.
- Capture redefinition targets in the loader.
- Emit `:>> Qualified::member` in the exporter.
- Add load/export round-trip tests.
- Add transitive marker helpers.
- Add an effective-attribute resolver with cycle/conflict checks.

### Phase B — generation

- Use effective set members in SSV, SSD, SSM, and disjointness.
- Use effective interface members in FMI/SSD when interface inheritance is
  supported.
- Keep base definitions out of SSP unless applied.

### Phase C — sync

- Preserve existing inheritance by name.
- Apply the override-overlay policy.
- Keep synthesized flat sets flat.
- Document base-set update effects.

### Phase D — optional interface inheritance

- Use the same effective-attribute resolver for parameter interfaces.
- Flatten for FMI/SSD.
- Preserve inherited interface definitions during sync.
- Can be deferred if only set reuse is needed.

## 10. Out of scope

- Nested set containment.
- Dotted parameter group names.
- Reconstructing inheritance from SSV/SSD.
- Abstract set definitions (unless a concrete need appears).
- Namespacing within a set. Member names must be unique across the effective
  union.

## 11. Open decisions

1. Overrides: allow explicit `:>>` redefinitions, or additive-only
   inheritance? **Recommended: allow overrides.**
2. Multiple inheritance: allow union of multiple base sets with explicit
   conflict resolution? **Recommended: yes.**
3. Interface inheritance: sets only first, or implement interfaces too?
   **Recommended: sets first, interfaces as a follow-up.**
4. Sync policy: preserve inheritance with an override overlay, or flatten?
   **Recommended: overlay.**
5. `generate sysml` from SSD: acceptable to synthesize a flat set and lose the
   base/derived structure? **Recommended: yes.**
6. Conflicts: reject two bases defining the same member unless the derived set
   explicitly redefines it? **Recommended: yes.**
