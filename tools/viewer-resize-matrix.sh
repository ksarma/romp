#!/usr/bin/env bash
# Runs the viewer-resize bench matrix one run at a time under nice 19, resumably: each configuration writes a marker under
# <out>/matrix/<name>.done holding its run-JSON path, and a rerun skips configurations that already have one. The bench
# and its knobs are tools/viewer-resize-bench.mjs; tools/viewer-resize-summarize.mjs folds the runs into MEASURE.md.
# Usage: tools/viewer-resize-matrix.sh [phase...]   phases: head box1 escalate (default: head box1)
# The box1 phase needs the detached worktree at the incident commit (see the launcher's header) beside this checkout.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/.." && pwd)
OUT=${VRB_OUT:-$HOME/.local/state/romp-perf/viewer-resize}
BOX1=${VRB_BOX1:-$REPO/../romp-perf-viewer-resize-box1}
mkdir -p "$OUT/matrix"
PHASES=${*:-head box1}

run() { # run <name> <bench args...>
  local name=$1; shift
  local marker="$OUT/matrix/$name.done" log="$OUT/matrix/$name.log"
  if [ -f "$marker" ]; then echo "skip $name (done)"; return 0; fi
  echo "=== $name  $(date -u +%FT%TZ)  $*" | tee -a "$OUT/matrix/matrix.log"
  nice -n 19 node "$HERE/viewer-resize-bench.mjs" --label "$name" "$@" >"$log" 2>&1
  local rc=$?
  local json
  json=$(grep -o 'json=[^ ]*' "$log" | tail -1 | cut -d= -f2)
  echo "--- $name rc=$rc json=${json:-none} $(date -u +%FT%TZ)" | tee -a "$OUT/matrix/matrix.log"
  if [ -n "$json" ]; then echo "$json" >"$marker"; fi
  return 0
}

for phase in $PHASES; do
case $phase in
head)
  T=(--tree "$REPO")
  # document-size axis at the three review states of the incident file the user described (2026-09-09): no comments, the 32 left after the merge, the full review
  run m1-head-small-c0-h0      "${T[@]}" --size small  --comments 0   --hunks 0
  run m1-head-small-c32-h0     "${T[@]}" --size small  --comments 32  --hunks 0
  run m1-head-small-c200-h200  "${T[@]}" --size small  --comments 200 --hunks 200
  run m1-head-medium-c0-h0     "${T[@]}" --size medium --comments 0   --hunks 0
  run m1-head-medium-c32-h0    "${T[@]}" --size medium --comments 32  --hunks 0
  # comments axis and hunks axis at medium, independent of document size
  run m1-head-medium-c50-h0    "${T[@]}" --size medium --comments 50  --hunks 0
  run m1-head-medium-c200-h0   "${T[@]}" --size medium --comments 200 --hunks 0
  run m1-head-medium-c500-h0   "${T[@]}" --size medium --comments 500 --hunks 0   --timeout-s 900
  run m1-head-medium-c0-h50    "${T[@]}" --size medium --comments 0   --hunks 50
  run m1-head-medium-c0-h200   "${T[@]}" --size medium --comments 0   --hunks 200
  run m1-head-medium-c0-h500   "${T[@]}" --size medium --comments 0   --hunks 500  --timeout-s 900
  run m1-head-medium-c200-h200 "${T[@]}" --size medium --comments 200 --hunks 200  --cpu-profile
  run m1-head-medium-c500-h500 "${T[@]}" --size medium --comments 500 --hunks 500  --timeout-s 1500
  run m1-head-medium-c200-h200-closed "${T[@]}" --size medium --comments 200 --hunks 200 --panel closed --no-add
  # large: the mixed document and the three composition variants, with and without the 32 comments
  run m1-head-large-c0-h0      "${T[@]}" --size large --comments 0   --hunks 0   --cpu-profile --timeout-s 900
  run m1-head-large-c32-h0     "${T[@]}" --size large --comments 32  --hunks 0   --cpu-profile --timeout-s 900
  run m1-head-large-c32-h0-closed "${T[@]}" --size large --comments 32 --hunks 0 --panel closed --no-add --timeout-s 900
  run m1-head-large-prose-c0-h0  "${T[@]}" --size large --variant prose --comments 0  --hunks 0 --cpu-profile --timeout-s 900
  run m1-head-large-prose-c32-h0 "${T[@]}" --size large --variant prose --comments 32 --hunks 0 --cpu-profile --timeout-s 900
  run m1-head-large-fence-c0-h0  "${T[@]}" --size large --variant fence --comments 0  --hunks 0 --cpu-profile --timeout-s 900
  run m1-head-large-fence-c32-h0 "${T[@]}" --size large --variant fence --comments 32 --hunks 0 --cpu-profile --timeout-s 900
  run m1-head-large-table-c0-h0  "${T[@]}" --size large --variant table --comments 0  --hunks 0 --cpu-profile --timeout-s 900
  run m1-head-large-table-c32-h0 "${T[@]}" --size large --variant table --comments 32 --hunks 0 --cpu-profile --timeout-s 900
  run m1-head-large-c200-h200  "${T[@]}" --size large --comments 200 --hunks 200 --cpu-profile --timeout-s 2400
  ;;
box1)
  if [ ! -d "$BOX1/vscode-extension/node_modules/playwright" ]; then echo "box1 tree missing at $BOX1"; continue; fi
  T=(--tree "$BOX1")
  run m1-box1-small-c32-h0     "${T[@]}" --size small  --comments 32  --hunks 0
  run m1-box1-small-c200-h200  "${T[@]}" --size small  --comments 200 --hunks 200
  run m1-box1-medium-c0-h0     "${T[@]}" --size medium --comments 0   --hunks 0
  run m1-box1-medium-c32-h0    "${T[@]}" --size medium --comments 32  --hunks 0
  run m1-box1-medium-c200-h200 "${T[@]}" --size medium --comments 200 --hunks 200  --cpu-profile
  run m1-box1-large-c0-h0      "${T[@]}" --size large --comments 0   --hunks 0   --cpu-profile --timeout-s 900
  run m1-box1-large-c32-h0     "${T[@]}" --size large --comments 32  --hunks 0   --cpu-profile --timeout-s 900
  run m1-box1-large-prose-c32-h0 "${T[@]}" --size large --variant prose --comments 32 --hunks 0 --cpu-profile --timeout-s 900
  run m1-box1-large-fence-c32-h0 "${T[@]}" --size large --variant fence --comments 32 --hunks 0 --cpu-profile --timeout-s 900
  run m1-box1-large-table-c32-h0 "${T[@]}" --size large --variant table --comments 32 --hunks 0 --cpu-profile --timeout-s 900
  run m1-box1-large-c200-h200  "${T[@]}" --size large --comments 200 --hunks 200 --cpu-profile --timeout-s 2400
  ;;
escalate)
  T=(--tree "$REPO")
  run m1-head-40k-c0-h0        "${T[@]}" --lines 40000  --comments 0  --hunks 0  --cpu-profile --timeout-s 1500
  run m1-head-40k-c32-h0       "${T[@]}" --lines 40000  --comments 32 --hunks 0  --cpu-profile --timeout-s 1500
  run m1-head-100k-c0-h0       "${T[@]}" --lines 100000 --comments 0  --hunks 0  --cpu-profile --timeout-s 2400
  run m1-head-100k-c32-h0      "${T[@]}" --lines 100000 --comments 32 --hunks 0  --cpu-profile --timeout-s 2400
  run m1-head-40k-fence-c0-h0  "${T[@]}" --lines 40000 --variant fence --comments 0 --hunks 0 --cpu-profile --timeout-s 1500
  run m1-head-40k-table-c0-h0  "${T[@]}" --lines 40000 --variant table --comments 0 --hunks 0 --cpu-profile --timeout-s 1500
  ;;
*) echo "unknown phase $phase";;
esac
done
echo "matrix finished $(date -u +%FT%TZ)" | tee -a "$OUT/matrix/matrix.log"
