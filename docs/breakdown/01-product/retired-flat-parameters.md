---
id: INFO-024
type: info
title: Retired flat-attribute parameters
summary: Direct parameter attributes on a part are rejected; parameters use an interface and a bound set.
date: 2026-10-22
status: current
---

# Retired flat-attribute parameters

The flat-attribute dialect is no longer supported. Parameters must be declared
through a parameter interface and applied through SysML-defined sets.

A component that still declares `attribute gain : Real;` directly fails with:

```text
Comp.gain is a flat parameter attribute, which is no longer supported.
Declare a parameter interface with 'in port parameters : <Interface>;' and
apply a ParameterSet with 'bind'.
```

The legacy `pyssp_parameter_set` composition attribute is retired for the same
reason.

`generate sysml` can still convert an SSD `ParameterBinding` into interfaces,
sets, and binds when bootstrapping from an existing SSP.

The replacement form:

```sysml
port def Params :> ParameterInterface {
  attribute gain : Real;
}

part def Comp {
  in port parameters : Params;
}

attribute def NominalSet :> ParameterSet {
  attribute gain = 2.0;
}

part def Composition {
  part comp : Comp;
  attribute nominal : NominalSet;
  bind comp.parameters.gain = nominal.gain;
}
```
