#!/usr/bin/env bash
# Runs the browser legs named in ci-browser-legs.txt under node --test. The step "Browser legs (node --test over
# ci-browser-legs.txt)" of .github/workflows/ci.yml calls this from vscode-extension/ after the job installs Chromium,
# with ROMP_BROWSER_LEGS_REQUIRE=1 (ui/webview/browser-legs-require.ts) so a leg whose launch fails is red, not a skip.
# Before node --test it checks that the roster and the tree agree, and every red names the line and what to do:
#   - a roster or exclusions line whose source is not in the tree (the source moved or was deleted): fix the line;
#   - a browser leg in neither file: add it to the roster, or to ci-browser-legs-excluded.txt with a tab and a reason;
#   - a line in both files, a duplicate line, an exclusions line with no reason, a line naming no browser leg: fix it;
#   - a malformed line (trailing whitespace or a carriage return counts): printed with the whitespace visible, and the leg
#     it names is reported as named by that line, not as missing from both files;
#   - a roster line whose source never reads the switch: only a leg that launches through real-viewer-leg.ts's inBrowser
#     or browser-legs-require.ts's launchBrowser (or skipOrFail) turns its launch skip into a failure here; a leg with a
#     launch and a t.skip of its own skips under the switch as it does without it, so it cannot be rostered as it is;
#   - a roster line whose source names Firefox or WebKit outside a comment: the gating job installs Chromium only;
#   - a roster line whose bundle is not under out-tests/: the Test step's npm test builds it (node esbuild.js --tests).
# After node --test it reads the run's TAP record: a test skipped under the switch is red too, with the skipped tests
# named as node names them and the rostered sources that hold each name, since a skip here is coverage the step claims
# and does not have. The census rule is the one tools/ci-browser-legs.test.mjs states; that test runs `--list-legs`
# here and holds the two to the same set, and runs the checks above on synthetic trees. An empty roster prints "no legs
# in the roster" and exits 0 without starting node --test: with no file arguments node --test runs its default glob,
# the whole suite again.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
ROOT=$(cd .. && pwd)
ROSTER=ci-browser-legs.txt
EXCLUDED=ci-browser-legs-excluded.txt
SWITCH=ROMP_BROWSER_LEGS_REQUIRE

# A browser leg: a test module esbuild's test build bundles (a .test.ts directly in vscode-extension/src, ui or ui/webview)
# that, on a line that is not a // comment, requires or imports the "playwright" package, or imports ./real-viewer-leg and
# calls its inBrowser(. Named by the bundle path the roster uses: out-tests/<dir>/<name>.test.js.
code_of() { grep -v '^[[:space:]]*//' "$1" || [ $? -eq 1 ]; }
is_leg() {
  local code
  code=$(code_of "$1")
  # here-strings, not pipes: under pipefail a printf whose reader (grep -q) stops at the first match fails the pipeline
  if grep -qE '\([[:space:]]*"playwright"[[:space:]]*\)|from[[:space:]]+"playwright"' <<<"$code"; then return 0; fi
  grep -q '"\./real-viewer-leg"' <<<"$code" && grep -q 'inBrowser(' <<<"$code"
}
# The leg reads the switch: it launches through real-viewer-leg.ts's inBrowser, or through browser-legs-require.ts's
# launchBrowser or skipOrFail, on a line that is not a // comment.
reaches_switch() {
  local code
  code=$(code_of "$1")
  if grep -q '"\./real-viewer-leg"' <<<"$code" && grep -q 'inBrowser(' <<<"$code"; then return 0; fi
  grep -q '"\./browser-legs-require"' <<<"$code" && grep -qE 'launchBrowser\(|skipOrFail\(' <<<"$code"
}
# The engines other than Chromium the leg names outside comments ("firefox"/"webkit", pw.firefox/pw.webkit), joined by " and ".
other_engines() {
  local code n=""
  code=$(code_of "$1")
  if grep -qE '"firefox"|\.firefox\.' <<<"$code"; then n="Firefox"; fi
  if grep -qE '"webkit"|\.webkit\.' <<<"$code"; then n="${n:+$n and }WebKit"; fi
  printf '%s' "$n"
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
# the lines seen so far in each file, one "bundle<TAB>line number" per line, for the duplicate and both-files checks; and
# the bundle a malformed line names once its whitespace is stripped, "bundle<TAB><file> line <n>", so the census pass can
# point at that line instead of calling the leg missing
roster_seen=""
excluded_seen=""
malformed_seen=""
seen_at() { awk -v k="$1" -F '\t' '$1 == k { print $2; exit }' <<<"$2"; }
malformed() {   # $1 the file, $2 the line number, $3 the line: red with the whitespace visible, and remember the bundle it names
  local shown stripped
  shown=$(printf '%q' "$3")
  red "$1 line $2: $shown is not a bundle path (out-tests/<dir>/<name>.test.js; a trailing space, tab or carriage return counts and is shown here as bash's %q spells it): fix the line"
  stripped=${3//[[:space:]]/}
  if well_formed "$stripped"; then malformed_seen="$malformed_seen$stripped	$1 line $2"$'\n'; fi
}

legs=()
n=0
while IFS= read -r line || [ -n "$line" ]; do
  n=$((n + 1))
  [[ "$line" =~ ^[[:space:]]*(#|$) ]] && continue
  if ! well_formed "$line"; then malformed "$ROSTER" "$n" "$line"; continue; fi
  at=$(seen_at "$line" "$roster_seen")
  if [ -n "$at" ]; then red "$ROSTER line $n: '$line' duplicates line $at: remove one"; continue; fi
  roster_seen="$roster_seen$line	$n"$'\n'
  src=$(source_of "$line")
  if [ ! -f "$src" ]; then red "$ROSTER line $n: '$line' names ${src#"$ROOT/"}, which is not in the tree (the source moved or was deleted): fix the roster line"; continue; fi
  if ! is_leg "$src"; then red "$ROSTER line $n: '$line' names no browser leg (${src#"$ROOT/"} reaches no browser): remove the line"; continue; fi
  if ! reaches_switch "$src"; then red "$ROSTER line $n: '$line' launches on its own and never reads $SWITCH, so under the step its launch skip stays a skip: launch through inBrowser (ui/webview/real-viewer-leg.ts) or launchBrowser (ui/webview/browser-legs-require.ts) before rostering it"; continue; fi
  engines=$(other_engines "$src")
  if [ -n "$engines" ]; then red "$ROSTER line $n: '$line' names $engines outside a comment; the gating job installs Chromium only, so under the switch that launch is red: keep the leg in $EXCLUDED with that reason"; continue; fi
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
  if ! well_formed "$bundle"; then malformed "$EXCLUDED" "$n" "$bundle"; continue; fi
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
    at=$(seen_at "$leg" "$malformed_seen")
    if [ -n "$at" ]; then
      red "browser leg '$leg' is named by a malformed line ($at, above): fix that line"
    else
      red "browser leg '$leg' is in neither $ROSTER nor $EXCLUDED: add it to the roster (the gating job runs it with a browser), or to the exclusions with a tab and a reason"
    fi
  fi
done < <(census)

if [ "$fail" -ne 0 ]; then echo "ci-browser-legs: the roster and the tree disagree (above); no leg ran" >&2; exit 1; fi

if [ "${#legs[@]}" -eq 0 ]; then echo "no legs in the roster"; exit 0; fi
# The run's TAP record goes to a file beside the spec output on stdout, for the skip check below.
tap=$(mktemp)
trap 'rm -f "$tap"' EXIT
status=0
printf '%s\n' "${legs[@]}" | xargs -r node --test --test-reporter=spec --test-reporter-destination=stdout --test-reporter=tap --test-reporter-destination="$tap" || status=$?

# A skipped test under the switch: node's record names the test and its reason, not the file (a multi-file run reports
# every test at the top level), so each skipped name is looked up verbatim in the rostered sources.
skipped=$(grep -E '^[[:space:]]*(not )?ok [0-9]+ - .* # SKIP' "$tap" || [ $? -eq 1 ])
if [ -n "$skipped" ]; then
  while IFS= read -r s; do
    name=$(sed -E 's/^[[:space:]]*(not )?ok [0-9]+ - //; s/ # SKIP.*$//' <<<"$s")
    holders=""
    for leg in "${legs[@]}"; do
      if grep -qF -- "$name" "$(source_of "$leg")"; then holders="${holders:+$holders, }$leg"; fi
    done
    echo "ci-browser-legs: skipped under $SWITCH=1: ${s#"${s%%[![:space:]]*}"} (rostered sources holding that test name verbatim: ${holders:-none})" >&2
  done <<<"$skipped"
  echo "ci-browser-legs: a rostered leg skipped a test under $SWITCH=1, so the step claims coverage it did not run: the leg's launch or skip never reads the switch (launch through inBrowser in ui/webview/real-viewer-leg.ts or launchBrowser in ui/webview/browser-legs-require.ts), or the test skips for another reason; until every test of the leg runs here, move it to $EXCLUDED with that reason" >&2
  [ "$status" -ne 0 ] || status=1
fi
exit "$status"
