#!/usr/bin/env bash
# Runs the browser legs named in ci-browser-legs.txt under node --test. The step "Browser legs (node --test over
# ci-browser-legs.txt)" of .github/workflows/ci.yml calls this from vscode-extension/ after the job installs Chromium,
# with ROMP_BROWSER_LEGS_REQUIRE=1 (ui/webview/browser-legs-require.ts) so a leg whose launch fails is red, not a skip.
# Before node --test it checks that the roster and the tree agree, and every red names the line and what to do:
#   - a roster or exclusions line whose source is not in the tree (the source moved or was deleted): fix the line;
#   - a browser leg in neither file: add it to the roster, or to ci-browser-legs-excluded.txt with a tab and a reason;
#   - a line in both files, a duplicate line, an exclusions line with no reason, a line naming no browser leg: fix it;
#   - a roster line whose bundle is not under out-tests/: the Test step's npm test builds it (node esbuild.js --tests).
# The census rule is the one tools/ci-browser-legs.test.mjs states; that test runs `--list-legs` here and holds the two
# to the same set, and runs the checks above on synthetic trees. An empty roster prints "no legs in the roster" and exits
# 0 without starting node --test: with no file arguments node --test runs its default glob, the whole suite again.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
ROOT=$(cd .. && pwd)
ROSTER=ci-browser-legs.txt
EXCLUDED=ci-browser-legs-excluded.txt

# A browser leg: a test module esbuild's test build bundles (a .test.ts directly in vscode-extension/src, ui or ui/webview)
# that, on a line that is not a // comment, requires or imports the "playwright" package, or imports ./real-viewer-leg and
# calls its inBrowser(. Named by the bundle path the roster uses: out-tests/<dir>/<name>.test.js.
is_leg() {
  local code
  code=$(grep -v '^[[:space:]]*//' "$1" || [ $? -eq 1 ])
  # here-strings, not pipes: under pipefail a printf whose reader (grep -q) stops at the first match fails the pipeline
  if grep -qE '\([[:space:]]*"playwright"[[:space:]]*\)|from[[:space:]]+"playwright"' <<<"$code"; then return 0; fi
  grep -q '"\./real-viewer-leg"' <<<"$code" && grep -q 'inBrowser(' <<<"$code"
}
census() {
  local dir f rel
  for dir in vscode-extension/src ui ui/webview; do
    for f in "$ROOT/$dir"/*.test.ts; do
      [ -e "$f" ] || continue
      if is_leg "$f"; then rel=${f#"$ROOT/"}; printf 'out-tests/%s.test.js\n' "${rel%.test.ts}"; fi
    done
  done | sort
}
if [ "${1:-}" = "--list-legs" ]; then census; exit 0; fi

for f in "$ROSTER" "$EXCLUDED"; do
  if [ ! -f "$f" ]; then echo "ci-browser-legs: $f is not in vscode-extension/, where the roster and the exclusions are read from: restore it" >&2; exit 1; fi
done

fail=0
red() { echo "ci-browser-legs: $*" >&2; fail=1; }
source_of() { local rel=${1#out-tests/}; printf '%s/%s.test.ts' "$ROOT" "${rel%.test.js}"; }
well_formed() { [[ "$1" =~ ^out-tests/[^[:space:]]+\.test\.js$ ]]; }
# the lines seen so far in each file, one "bundle<TAB>line number" per line, for the duplicate and both-files checks
roster_seen=""
excluded_seen=""
seen_at() { awk -v k="$1" -F '\t' '$1 == k { print $2; exit }' <<<"$2"; }

legs=()
n=0
while IFS= read -r line || [ -n "$line" ]; do
  n=$((n + 1))
  [[ "$line" =~ ^[[:space:]]*(#|$) ]] && continue
  if ! well_formed "$line"; then red "$ROSTER line $n: '$line' is not a bundle path (out-tests/<dir>/<name>.test.js): fix the roster line"; continue; fi
  at=$(seen_at "$line" "$roster_seen")
  if [ -n "$at" ]; then red "$ROSTER line $n: '$line' duplicates line $at: remove one"; continue; fi
  roster_seen="$roster_seen$line	$n"$'\n'
  src=$(source_of "$line")
  if [ ! -f "$src" ]; then red "$ROSTER line $n: '$line' names ${src#"$ROOT/"}, which is not in the tree (the source moved or was deleted): fix the roster line"; continue; fi
  if ! is_leg "$src"; then red "$ROSTER line $n: '$line' names no browser leg (${src#"$ROOT/"} reaches no browser): remove the line"; continue; fi
  if [ ! -f "$line" ]; then red "$ROSTER line $n: '$line' is not under out-tests/ (the Test step's npm test builds it; locally, node esbuild.js --tests): build the bundles before this step"; continue; fi
  legs+=("$line")
done < "$ROSTER"

n=0
while IFS= read -r line || [ -n "$line" ]; do
  n=$((n + 1))
  [[ "$line" =~ ^[[:space:]]*(#|$) ]] && continue
  bundle=${line%%$'\t'*}
  reason=${line#*$'\t'}
  if [ "$bundle" = "$line" ] || [ -z "${reason//[[:space:]]/}" ]; then red "$EXCLUDED line $n: '$line' has no reason: write the bundle path, a tab, and why the gating job does not run it"; continue; fi
  if ! well_formed "$bundle"; then red "$EXCLUDED line $n: '$bundle' is not a bundle path (out-tests/<dir>/<name>.test.js): fix the line"; continue; fi
  at=$(seen_at "$bundle" "$excluded_seen")
  if [ -n "$at" ]; then red "$EXCLUDED line $n: '$bundle' duplicates line $at: remove one"; continue; fi
  excluded_seen="$excluded_seen$bundle	$n"$'\n'
  at=$(seen_at "$bundle" "$roster_seen")
  if [ -n "$at" ]; then red "$EXCLUDED line $n: '$bundle' is also $ROSTER line $at: a leg is in one file or the other, keep one"; continue; fi
  src=$(source_of "$bundle")
  if [ ! -f "$src" ]; then red "$EXCLUDED line $n: '$bundle' names ${src#"$ROOT/"}, which is not in the tree (the source moved or was deleted): fix the line"; continue; fi
  if ! is_leg "$src"; then red "$EXCLUDED line $n: '$bundle' names no browser leg (${src#"$ROOT/"} reaches no browser): remove the line"; fi
done < "$EXCLUDED"

while IFS= read -r leg; do
  [ -n "$leg" ] || continue
  if [ -z "$(seen_at "$leg" "$roster_seen")" ] && [ -z "$(seen_at "$leg" "$excluded_seen")" ]; then
    red "browser leg '$leg' is in neither $ROSTER nor $EXCLUDED: add it to the roster (the gating job runs it with a browser), or to the exclusions with a tab and a reason"
  fi
done < <(census)

if [ "$fail" -ne 0 ]; then echo "ci-browser-legs: the roster and the tree disagree (above); no leg ran" >&2; exit 1; fi

if [ "${#legs[@]}" -eq 0 ]; then echo "no legs in the roster"; exit 0; fi
printf '%s\n' "${legs[@]}" | xargs -r node --test
