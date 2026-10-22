# Parameter Sets Example

Demonstrates the interface/set dialect:

- `AutopilotParameters` is the component parameter interface.
- `NominalSet` and `AggressiveSet` are reusable value sets with their own names.
- `AircraftComposition` applies `NominalSet` to the `autopilot` usage with
  per-member `bind` statements.

```bash
pyssp generate ssv \
  --architecture examples/parameter_sets \
  --composition AircraftComposition \
  --output-dir build/generated/parameter_sets

pyssp generate ssd \
  --architecture examples/parameter_sets \
  --composition AircraftComposition \
  --output build/generated/SystemStructure.ssd

pyssp generate fmi \
  --architecture examples/parameter_sets \
  --composition AircraftComposition \
  --output-dir build/generated/model_descriptions
```

`generate ssv --all-sets` also writes `AggressiveSet.ssv`.

The SSD gets parameter connectors from the interface and an inline
`ssd:ParameterMapping` for the explicit binds; its `ParameterBinding/@source`
points at `parameter_sets/NominalSet.ssv`. The FMI model description gets
parameter variables (with interface defaults when declared; the applied set
is a runtime mapping, not an FMI start value).

The same dialect supports multiple disjoint sets per component and nested part
paths such as `bind nominal.k = outer.inner.parameters.k`. For the full
methodology and more examples, see
[`docs/methodology/01-parameter-sets.md`](../../docs/methodology/01-parameter-sets.md).

Regenerate SysML from the SSD to see the synthesized dialect:

```bash
pyssp generate sysml \
  --ssd build/generated/SystemStructure.ssd \
  --output build/generated/parameter_sets_roundtrip.sysml
```
