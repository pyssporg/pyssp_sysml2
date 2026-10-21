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

pyssp generate ssm \
  --architecture examples/parameter_sets \
  --composition AircraftComposition \
  --output-dir build/generated/parameter_mappings
```

`generate ssv --all-sets` also writes `AggressiveSet.ssv`.

`generate ssd` / `generate fmi` currently reject the parameter-set dialect;
they still support the legacy flat-attribute models such as
`examples/aircraft_subset`.
