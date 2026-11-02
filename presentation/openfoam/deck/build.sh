#!/bin/bash
# Rebuild the OpenFOAM part of the team deck: draw the figures and the per-job plots for the deck, then build the pptx.
# usage: presentation/openfoam/deck/build.sh [INPUT.pptx] [OUTPUT.pptx] [PICTURES]
# PICTURES is a copy of Box's presentation/openfoam/decomposition/ (WSL cannot read Box), for decomposition-numa.png and
# decomposition-numa-scotch-domains-vs-multilevel.png.
set -euo pipefail
deck="$(cd "$(dirname "$0")" && pwd)"
input="${1:-$HOME/apac26/Tokyo Rapids with RIKEN Presentation.pptx}"
output="${2:-$HOME/apac26/Tokyo Rapids with RIKEN Presentation HPC (8th edition).pptx}"
pictures="${3:-$HOME/apac26/decomposition}"
figures="$(mktemp -d)"
trap 'rm -rf "$figures"' EXIT
cp "$pictures/decomposition-numa.png" "$pictures/decomposition-numa-scotch-domains-vs-multilevel.png" "$figures/"
uv run "$deck/deck_figures.py" "$deck/../figures.py" "$figures"
uv run "$deck/deck_plots.py" "$deck/../figures.py" "$figures"
uv run "$deck/build_deck.py" "$input" "$output" "$figures"
