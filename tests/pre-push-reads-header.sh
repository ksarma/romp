#!/usr/bin/env bash
# fixer r8b-hook (A.8): emit the hook header's gate= and own= list block from tests/pre-push-reads.tsv, the one
# authority for it. tests/pre-push-hook.bats' table case asserts the hook's own block equals this output byte for
# byte, so a hand edit of either the header or the table's read column reds. One argument: the tsv path.
set -u
tsv="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/pre-push-reads.tsv}"
printf '# Reads gated by a sibling fact (gate=):\n'
awk -F'\t' '$1 == "gate" { print "#   " $2 }' "$tsv"
printf '# Reads whose empty answer is the object'"'"'s own (own=):\n'
awk -F'\t' '$1 == "own" { print "#   " $2 }' "$tsv"
