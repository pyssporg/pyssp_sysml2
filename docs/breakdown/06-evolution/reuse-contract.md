---
id: IMP-001
type: imp
title: Parameter-set reuse contract
summary: Reuse by inheritance and union; a set inside a set is rejected because SSP parameters are flat.
date: 2026-10-22
status: current
---

# Parameter-set reuse contract

Status: proposed, not implemented. Current tooling rejects inherited sets and
`:>>` redefinitions.

## Problem

An analysis often needs several variants of the same parameters:

- a nominal set;
- an aggressive set that changes a few values;
- a sensor set that adds unrelated values;
- a combined set that reuses both.

The current dialect has two options:

1. duplicate values in each set;
2. apply multiple disjoint sets to one component.

Neither expresses "this set is the nominal set plus these changes" or "this set
is the union of these reusable sets."

## Why not a set inside a set

A parameter set inside a parameter set is containment. SSP has no contained
parameter sets: an SSV is a flat list of uniquely named parameters. Containment
would force one of:

- dotted parameter names such as `gains.k`, which collide conceptually with
  SSP's hierarchical component names;
- multiple SSVs and multiple `ParameterBinding`s behind one SysML bind.

Both add complexity and ambiguity that reuse does not require.

Inheritance is different: it is definition-time reuse. The effective set is
computed in SysML, then flattened into one SSP parameter set. SSP sees no
inheritance.

