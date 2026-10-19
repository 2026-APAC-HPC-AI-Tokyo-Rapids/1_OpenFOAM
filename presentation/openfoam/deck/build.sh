#!/bin/bash
# Rebuild the OpenFOAM part of the team deck: draw the figures without their captions, then build the pptx.
# usage: presentation/openfoam/deck/build.sh [INPUT.pptx] [OUTPUT.pptx]
set -euo pipefail
deck="$(cd "$(dirname "$0")" && pwd)"
input="${1:-$HOME/apac26/Tokyo Rapids with RIKEN Presentation.pptx}"
output="${2:-$HOME/apac26/Tokyo Rapids with RIKEN Presentation (HPC revised).pptx}"
figures="$(mktemp -d)"
trap 'rm -rf "$figures"' EXIT
uv run "$deck/figures_nocaption.py" "$deck/../figures.py" "$figures"
uv run "$deck/build_deck.py" "$input" "$output" "$figures"
