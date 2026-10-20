#!/bin/bash
# Rebuild the OpenFOAM part of the team deck: draw the figures for the deck, then build the pptx.
# usage: presentation/openfoam/deck/build.sh [INPUT.pptx] [OUTPUT.pptx] [ASSETDIR]
# ASSETDIR holds multiLevel-car-numa.png, copied from the Box folder presentation/openfoam/decomposition/panels/.
set -euo pipefail
deck="$(cd "$(dirname "$0")" && pwd)"
input="${1:-$HOME/apac26/Tokyo Rapids with RIKEN Presentation.pptx}"
output="${2:-$HOME/apac26/Tokyo Rapids with RIKEN Presentation (HPC revised).pptx}"
assets="${3:-$HOME/apac26/deck-assets}"
figures="$(mktemp -d)"
trap 'rm -rf "$figures"' EXIT
uv run "$deck/deck_figures.py" "$deck/../figures.py" "$figures"
uv run "$deck/build_deck.py" "$input" "$output" "$figures" "$assets"
