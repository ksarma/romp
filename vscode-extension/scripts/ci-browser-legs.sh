#!/usr/bin/env bash
# Runs the browser legs named in ci-browser-legs.txt under node --test. The step "Browser legs (node --test over
# ci-browser-legs.txt)" of .github/workflows/ci.yml calls this from vscode-extension/ after the job installs Chromium,
# with ROMP_BROWSER_LEGS_REQUIRE=1. The one shared launcher, inBrowser in ui/webview/real-viewer-leg.ts, reads the
# switch (any non-empty value arms it) and under it a leg that cannot launch fails naming the switch and the reason
# instead of skipping. Before node --test this script checks that the roster and the tree agree, and every red names
# the line and what to do:
#   - a roster or exclusions line whose source is not in the tree (the source moved or was deleted): fix the line;
#   - a browser leg in neither file: add it to the roster, or to ci-browser-legs-excluded.txt with a tab and a reason;
#   - a line in both files, a duplicate line, an exclusions line with no reason, a line naming no browser leg: fix it;
#   - a malformed line (trailing whitespace or a carriage return counts): printed with the whitespace visible, and the leg
#     it names is reported as named by that line, not as missing from both files;
#   - a roster line whose source does not launch through the one shared launcher: a rostered leg imports
#     ./real-viewer-leg and calls inBrowser( by that name, and holds no .launch( and no .skip( of its own on a code
#     line. Only inBrowser reads the switch, so a launch or a skip of the leg's own stands outside it: a private skip
#     stays a skip, and a private launch that fails is never the failure naming the switch, which the step's red relies
#     on. The check reads the text (a call under an import alias is not read as an inBrowser( call), so an aliased leg
#     is refused until it calls inBrowser( by that name;
#   - a roster line whose source names Firefox or WebKit outside a comment: the gating job installs Chromium only;
#   - a roster line whose bundle is not under out-tests/: the Test step's npm test builds it (node esbuild.js --tests).
# After node --test it reads the run's TAP record: a test skipped under the switch is red too, with the skipped tests
# named as node names them, the switch's state in the run and the rostered sources whose text holds each name (node's
# TAP escaping undone), since a skip here is coverage the step claims and does not have (with the switch unset, as a
# local run may have it, the remedy is to run with it set); a rostered leg that registered no test is red too (node's
# record reports such a file as one passing test named by the bundle's path as node received it, and the step would
# read green with the leg's coverage gone); and a failed test whose error names the switch (inBrowser could not launch)
# is printed
# beside its leg, read from the record's location line, with the remedy: the runner lost its browser, check the Chromium
# install step. The census rule is the one tools/ci-browser-legs.test.mjs states; that test runs `--list-legs` here and holds
# the two to the same set, and runs the checks above on synthetic trees. An empty roster prints "no legs in the roster"
# and exits 0 without starting node --test: with no file arguments node --test runs its default glob, the whole suite
# again.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
ROOT=$(cd .. && pwd)
ROSTER=ci-browser-legs.txt
EXCLUDED=ci-browser-legs-excluded.txt
SWITCH=ROMP_BROWSER_LEGS_REQUIRE
# The switch's state in this run, printed by the messages after node --test: the step sets it to 1; a local run may not,
# and a skip with it unset is inBrowser skipping as designed, so the remedy differs.
if [ -n "${!SWITCH:-}" ]; then switch_state="$SWITCH=${!SWITCH}"; else switch_state="$SWITCH unset"; fi

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
# The gap between the leg and the one shared launcher, printed; nothing when the leg launches through it. A rostered leg
# imports ./real-viewer-leg and calls inBrowser( by that name on a line that is not a // comment, and holds no .launch(
# and no .skip( of its own on such a line: inBrowser is the one launch that reads the switch, and a private launch or
# skip stands outside it. The check is textual: a call under an import alias (inBrowser as <alias>) is not read as an
# inBrowser( call. tools/ci-browser-legs.test.mjs's launchesShared states the same rule.
shared_launch_gap() {
  local code
  code=$(code_of "$1")
  if ! grep -q '"\./real-viewer-leg"' <<<"$code" || ! grep -q 'inBrowser(' <<<"$code"; then printf '%s' "no inBrowser( call beside an import of ./real-viewer-leg; a call under an import alias is not read as one"; return 0; fi
  if grep -q '\.launch(' <<<"$code"; then printf '%s' "holds a launch of its own (.launch( on a code line)"; return 0; fi
  if grep -q '\.skip(' <<<"$code"; then printf '%s' "holds a skip of its own (.skip( on a code line)"; return 0; fi
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
  gap=$(shared_launch_gap "$src")
  if [ -n "$gap" ]; then red "$ROSTER line $n: '$line' does not launch through the one shared launcher ($gap): only inBrowser reads $SWITCH, so a launch or a skip of the leg's own stands outside the switch (a private skip stays a skip; a private launch that fails is never the failure naming the switch): launch through inBrowser (ui/webview/real-viewer-leg.ts), with no launch or skip of the leg's own, before rostering it"; continue; fi
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
# every test at the top level), so each skipped name is looked up in the rostered sources' text with node's TAP escaping
# undone (the record doubles a backslash and writes # as \#; undone, a newline in the name reads \n, as a source spells
# it). A name built at run time, or spelled otherwise in its source, may match none, and the line says so.
skipped=$(grep -E '^[[:space:]]*(not )?ok [0-9]+ - .* # SKIP' "$tap" || [ $? -eq 1 ])
if [ -n "$skipped" ]; then
  while IFS= read -r s; do
    name=$(sed -E 's/^[[:space:]]*(not )?ok [0-9]+ - //; s/ # SKIP.*$//; s/\\#/#/g; s/\\\\/\\/g' <<<"$s")
    holders=""
    for leg in "${legs[@]}"; do
      if grep -qF -- "$name" "$(source_of "$leg")"; then holders="${holders:+$holders, }$leg"; fi
    done
    echo "ci-browser-legs: skipped with $switch_state: ${s#"${s%%[![:space:]]*}"} (rostered sources whose text holds that test name, node's TAP escaping undone: ${holders:-none})" >&2
  done <<<"$skipped"
  if [ -n "${!SWITCH:-}" ]; then
    echo "ci-browser-legs: a rostered leg skipped a test with $switch_state, so the step claims coverage it did not run: the test skips for a reason of its own (only inBrowser in ui/webview/real-viewer-leg.ts turns a launch it cannot make into a failure here); until every test of the leg runs here, move it to $EXCLUDED with that reason" >&2
  else
    echo "ci-browser-legs: a rostered leg skipped a test with $switch_state, so this run claims coverage it did not run: the step sets $SWITCH=1, under which inBrowser in ui/webview/real-viewer-leg.ts fails a launch it cannot make instead of skipping; run with it set, and a test that still skips there skips for a reason of its own" >&2
  fi
  [ "$status" -ne 0 ] || status=1
fi

# A rostered leg that registered no test: node's record reports such a file as one passing test named by the bundle's
# path as node received it, the roster line itself here (a file with tests reports its tests and no line for the file),
# so the step would read green with the leg's coverage gone.
results=$(grep -E '^[[:space:]]*(not )?ok [0-9]+ - ' "$tap" || [ $? -eq 1 ])
for leg in "${legs[@]}"; do
  while IFS= read -r s; do
    [ -n "$s" ] || continue
    name=$(sed -E 's/^[[:space:]]*(not )?ok [0-9]+ - //' <<<"$s")
    if [ "$name" = "$leg" ]; then
      echo "ci-browser-legs: $leg registered no test in this run (node's record reports the file as one passing test named by its path), so the step claims coverage it did not run: a rostered leg holds a test that runs here; a leg whose tests are all behind a condition runs none when it is unmet, so move it to $EXCLUDED with that reason until one runs" >&2
      [ "$status" -ne 0 ] || status=1
      break
    fi
  done <<<"$results"
done

# A failed test whose error names the switch: inBrowser could not launch under $SWITCH, and the step's Chromium install
# is what it launches, so the runner lost its browser. The record's failure block carries the test's location (the
# bundle's absolute path, as node resolves it from its physical working directory, with a line and column) and its
# error; each such failure is printed beside its leg with the remedy.
here=$(pwd -P)
lost=$(awk -v msg="$SWITCH is set and this leg cannot run" '
  /^[[:space:]]*not ok [0-9]+ - / { name=$0; sub(/^[[:space:]]*not ok [0-9]+ - /, "", name); loc=""; err=""; infail=1; next }
  infail && /^[[:space:]]*location: / { loc=$0; sub(/^[[:space:]]*location: /, "", loc) }
  infail && /^[[:space:]]*error: / { err=$0; sub(/^[[:space:]]*error: /, "", err) }
  infail && /^[[:space:]]*\.\.\.[[:space:]]*$/ { if (index(err, msg)) print loc "\t" name "\t" err; infail=0 }
' "$tap")
if [ -n "$lost" ]; then
  while IFS=$'\t' read -r loc name err; do
    # the location as node quotes it: '<absolute bundle path>:<line>:<column>'; the leg is that path relative to here
    file=${loc#\'}; file=${file%\'}; file=${file%:*}; file=${file%:*}
    leg=${file#"$here/"}
    echo "ci-browser-legs: $leg: '$name' failed under $switch_state because inBrowser could not launch ($err): the runner lost its browser: check the Chromium install step" >&2
  done <<<"$lost"
  [ "$status" -ne 0 ] || status=1
fi
exit "$status"
