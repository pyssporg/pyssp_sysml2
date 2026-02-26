#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash examples/cli_usage.sh [ARCH_DIR] [COMPOSITION] [OUT_DIR]
#
# Example:
#   bash examples/cli_usage.sh tests/fixtures/aircraft_subset AircraftComposition build/generated

ARCH="${1:-tests/fixtures/aircraft_subset}"
COMP="${2:-AircraftComposition}"
OUT_DIR="${3:-build/generated}"

printf "Architecture : %s\n" "$ARCH"
printf "Composition  : %s\n" "$COMP"
printf "Output dir   : %s\n" "$OUT_DIR"

pyssp generate ssd \
  --architecture "$ARCH" \
  --composition "$COMP" \
  --output "$OUT_DIR/SystemStructure.ssd"

pyssp generate ssv \
  --architecture "$ARCH" \
  --composition "$COMP" \
  --output "$OUT_DIR/parameters.ssv"

pyssp generate fmi \
  --architecture "$ARCH" \
  --composition "$COMP" \
  --output-dir "$OUT_DIR/model_descriptions"

printf "\nGenerated artifacts:\n"
printf "- %s\n" "$OUT_DIR/SystemStructure.ssd"
printf "- %s\n" "$OUT_DIR/parameters.ssv"
printf "- %s\n" "$OUT_DIR/model_descriptions"
