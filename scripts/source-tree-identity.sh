#!/usr/bin/env bash
set -euo pipefail

source_tree=$(realpath -- "${1:?source tree is required}")
test -d "${source_tree}"
(cd "${source_tree}" && find . -type f -print0 | LC_ALL=C sort -z | xargs -0 -r sha256sum --zero) | sha256sum | awk '{print $1}'
