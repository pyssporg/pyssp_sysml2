---
id: IMP-002
type: imp
title: Effective set member map
summary: An effective member map collects inherited members by name, applies overrides, and rejects unresolved conflicts.
date: 2026-11-05
status: proposed
---

# Effective set member map

Status: proposed, not implemented.

## The map

For every set definition, compute an effective member map:

1. Recursively collect effective members from all supertypes.
2. Ignore the `ParameterSet` marker itself.
3. Merge members by name.
4. Apply direct attributes: a new name adds a member; an inherited name with
   `:>>` overrides; an inherited name without `:>>` is an error.
5. If distinct supertypes define the same member and there is no direct
   redefinition, error.
6. A member inherited through a diamond from the same origin counts once.
7. Detect cycles, unknown supertypes, and non-set supertypes.

Rules:

- Every supertype of a parameter set must be a parameter set or the
  `ParameterSet` marker.
- A direct redefinition must have a compatible primitive type and multiplicity.
- A redefinition without a value inherits the base value; a redefinition with a
  value overrides it.
- Values from base sets cannot be removed.
- Direct new members must not collide with inherited names.
- `definition.attributes` remains the direct member set. The effective map is a
  computed view; inherited members are not flattened into the definition.

Application is `IMP-007`; SSP transfer is `IMP-008`.
