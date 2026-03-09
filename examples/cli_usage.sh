#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash examples/cli_usage.sh [ARCH_DIR] [COMPOSITION] [OUT_DIR]
#
# Example:
#   bash examples/cli_usage.sh examples/aircraft_subset AircraftComposition build/generated

ARCH="${1:-examples/aircraft_subset}"
COMP="${2:-AircraftComposition}"
OUT_DIR="${3:-build/generated}"
BOOTSTRAP_DIR="$OUT_DIR/new_architecture"

if command -v pyssp >/dev/null 2>&1; then
  RUNNER=(pyssp)
else
  RUNNER=(python3 -m pyssp_sysml2.cli)
  export PYTHONPATH="${PYTHONPATH:-src}"
  if ! python3 -c "import pycps_sysmlv2, pyssp_standard" >/dev/null 2>&1; then
    echo "Missing runtime dependencies. Install first:"
    echo "  python3 -m venv venv && source venv/bin/activate"
    echo "  pip install -r requirements.txt && pip install -e ."
    exit 1
  fi
fi

printf "Architecture : %s\n" "$ARCH"
printf "Composition  : %s\n" "$COMP"
printf "Output dir   : %s\n" "$OUT_DIR"
printf "Command      : %s\n" "${RUNNER[*]}"

"${RUNNER[@]}" generate ssd \
  --architecture "$ARCH" \
  --composition "$COMP" \
  --output "$OUT_DIR/SystemStructure.ssd"

"${RUNNER[@]}" generate ssv \
  --architecture "$ARCH" \
  --composition "$COMP" \
  --output "$OUT_DIR/parameters.ssv"

"${RUNNER[@]}" generate fmi \
  --architecture "$ARCH" \
  --composition "$COMP" \
  --output-dir "$OUT_DIR/model_descriptions"

"${RUNNER[@]}" sync ssd \
  --architecture "$ARCH" \
  --composition "$COMP" \
  --ssd "$OUT_DIR/SystemStructure.ssd" \
  --output-architecture-dir "$OUT_DIR/synced_sysml"

mkdir -p "$BOOTSTRAP_DIR"
"${RUNNER[@]}" sync ssd \
  --architecture "$BOOTSTRAP_DIR" \
  --composition "$COMP" \
  --ssd "$OUT_DIR/SystemStructure.ssd"

printf "\nGenerated artifacts:\n"
printf "- %s\n" "$OUT_DIR/SystemStructure.ssd"
printf "- %s\n" "$OUT_DIR/parameters.ssv"
printf "- %s\n" "$OUT_DIR/model_descriptions"
printf "- %s\n" "$OUT_DIR/synced_sysml"
printf "- %s\n" "$BOOTSTRAP_DIR/architecture.sysml"
