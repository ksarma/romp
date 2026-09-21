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
#   - a malformed line (trailing whitespace or a carriage return counts) or an exclusions line with no reason: printed with
#     the whitespace visible (as bash's %q spells it), and the leg it names (the line's first word after its leading
#     whitespace) is reported as named by that refused line, not as missing from both files;
#   - a roster line whose source does not pass the roster gate, with the gap the census read: it never imports the shared
#     launcher, or imports it and never calls inBrowser through that import, or loads playwright itself, or holds a launch
#     of its own, or drives playwright from a child process, or holds a skip or todo of its own. Only inBrowser reads the
#     switch, so a launch or a skip of the leg's own stands outside it: a private skip stays a skip, and a private launch
#     that fails is never the failure naming the switch, which the step's red relies on. A shared call inside a try with
#     a catch clause is admitted (the census reports it; the census test prints the count);
#   - a roster line whose source reaches Firefox or WebKit: the gating job installs Chromium only;
#   - a roster line whose bundle is not under out-tests/: the Test step's npm test builds it (node esbuild.js --tests);
#   - an exclusions reason "pending #<PR>: <why>" names a leg an open PR brings: allowed while the leg's source is absent
#     from the tree (the line is then in neither the roster nor the census, and the census pass below is over the roster
#     plus the exclusions lines whose source is present); once the source is present the line is red with the promotion
#     remedy the census derives from the source (a roster line, a reason of its own, or no line), and the leg is not also
#     called missing from both files; a pending reason that names no PR is red.
# THE CENSUS is scripts/browser-legs-census.mjs, run once here (--tsv) for the population and every per-line verdict: it
# reads each test module's tree with the TypeScript compiler (a leg calls the shared launcher through its import under
# any binding, or names a playwright package by any specifier, or holds a driver string that does; engines and launches
# from playwright-derived expressions; skips and todos from the tree, so a comment holds none) and REFUSES, with file and
# line, a form it cannot classify, on which this script exits 1 having judged nothing. The compiler lives under
# vscode-extension/node_modules, present in the vscode-extension job after its npm ci; without it the census exits 1
# naming CI's Shell job and this script stops the same way. ui/webview/ci-browser-legs-census.test.ts (the job's test
# leg) holds the roster plus the exclusions to the census and runs the planted forms; tools/ci-browser-legs.test.mjs
# (the Shell job, no node_modules) holds the parse-free checks and runs this script over synthetic trees with a stub
# node that answers the census call from a table, so what it executes is this script's reading of the census, not the
# census. `--list-legs` prints the census's legs; `--check` runs the pre-run checks alone and starts no node --test
# (it does not check that the bundles are built, which the step's run does).
# After node --test it reads the run's record from scripts/ci-browser-legs-reporter.mjs (one line per result, attributed to
# its bundle by node's own record of the file; node's TAP record names no file for a pass, so it cannot say which leg a pass
# belongs to) and derives, per rostered leg, DID THIS LEG RUN: at least one result attributed to it is a pass that carries no
# skip or todo, is a test and not a suite, and is not node's file-level result (node reports a file that registered nothing as
# one pass named by its path). A leg with none is red naming the leg and what the record held instead (skips, todos, suites,
# the file-level result), since the step would otherwise claim coverage it did not run; a leg whose results all fail is
# node's red, passed through. Beside that property: a test skipped is red naming the test, its reason and the switch's state
# in the run (with the switch unset, as a local run may have it, the remedy is to run with it set); a failure inside a todo is
# red (node discards it: # fail 0, exit 0); a file that failed as a whole (node's file-level result failing: a timeout under
# the run's --test-timeout, or a throw at load) is red naming the file; and a failed test whose message names the switch (inBrowser could not launch) is printed beside its
# leg with the remedy: the runner lost its browser, check the Chromium install step. One pass over the record (awk),
# linear in its length. An empty roster prints "no legs in the roster" and exits 0 without starting node --test: with no
# file arguments node --test runs its default glob, the whole suite again.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
ROOT=$(cd .. && pwd)
ROSTER=ci-browser-legs.txt
EXCLUDED=ci-browser-legs-excluded.txt
SWITCH=ROMP_BROWSER_LEGS_REQUIRE
CENSUS=scripts/browser-legs-census.mjs
REPORTER=./scripts/ci-browser-legs-reporter.mjs
# The switch's state in this run, printed by the messages after node --test: the step sets it to 1; a local run may not,
# and a skip with it unset is inBrowser skipping as designed, so the remedy differs.
if [ -n "${!SWITCH:-}" ]; then switch_state="$SWITCH=${!SWITCH}"; else switch_state="$SWITCH unset"; fi

# The census, once: one line per test module read, bundle TAB 1|0 (a browser leg or not) TAB the roster gap (- when the
# leg passes the gate; for a module that is not a leg, the launcher import it never calls, or -) TAB the engines other
# than Chromium it reaches (- when none) TAB its class. Exit 2 is a refusal (the lines above it name file and line);
# any other non-zero exit is the census not running (the compiler absent); either way nothing is judged.
census_err=$(mktemp)
census_rc=0
census_tsv=$(node "$CENSUS" --tsv 2>"$census_err") || census_rc=$?
if [ "$census_rc" -ne 0 ]; then
  cat "$census_err" >&2; rm -f "$census_err"
  if [ "$census_rc" -eq 2 ]; then
    echo "ci-browser-legs: the census refused a form it cannot classify (above, with file and line): rewrite that form, or teach $CENSUS to read it; nothing else was judged and no leg ran" >&2
  else
    echo "ci-browser-legs: the census did not run (exit $census_rc, above), so nothing was judged and no leg ran" >&2
  fi
  exit 1
fi
rm -f "$census_err"
census_field() { awk -v k="$1" -v f="$2" -F '\t' '$1 == k { print $f; exit }' <<<"$census_tsv"; }
is_leg() { [ "$(census_field "$1" 2)" = "1" ]; }
gap_of() { local g; g=$(census_field "$1" 3); if [ "$g" != "-" ]; then printf '%s' "$g"; fi; return 0; }
engines_of() { local e; e=$(census_field "$1" 4); if [ "$e" != "-" ]; then printf '%s' "$e"; fi; return 0; }
census() { awk -F '\t' '$2 == "1" { print $1 }' <<<"$census_tsv"; }
promotion_of() {   # $1 the bundle of a pending line whose source is present: the remedy the census derives from that source
  local gap engines cls why=""
  gap=$(gap_of "$1"); engines=$(engines_of "$1"); cls=$(census_field "$1" 5)
  if ! is_leg "$1"; then printf '%s' "remove the line (the source reaches no browser by the census rule${gap:+; $gap})"; return 0; fi
  if [ "$cls" = "embedded" ]; then printf '%s' "keep the line and replace the reason with the embedded-driver sentence the header of $EXCLUDED states (the leg's only playwright is in a driver string it runs as a child process, which the switch never reaches)"; return 0; fi
  if [ -z "$gap" ] && [ -z "$engines" ]; then printf '%s' "delete this line and add '$1' to $ROSTER (the source launches through inBrowser alone and reaches no engine but Chromium), with the step's measured seconds in the PR body"; return 0; fi
  if [ -n "$engines" ]; then why="launches $engines; the gating job installs Chromium only"; fi
  if [ -n "$gap" ]; then why="${why:+$why; }$gap"; fi
  printf '%s' "keep the line and replace the reason with why the gating job does not run it ($why)"
}
pending_re='^[[:space:]]*pending #([0-9]+): [^[:space:]]'
if [ "${1:-}" = "--list-legs" ]; then census; exit 0; fi
check_only=0
if [ "${1:-}" = "--check" ]; then check_only=1; fi

for f in "$ROSTER" "$EXCLUDED"; do
  if [ ! -f "$f" ]; then echo "ci-browser-legs: $f is not in vscode-extension/, where the roster and the exclusions are read from: restore it" >&2; exit 1; fi
done

fail=0
red() { echo "ci-browser-legs: $*" >&2; fail=1; }
source_of() { local rel=${1#out-tests/}; printf '%s/%s.test.ts' "$ROOT" "${rel%.test.js}"; }
well_formed() { [[ "$1" =~ ^out-tests/[^[:space:]]+\.test\.js$ ]]; }
# the lines seen so far in each file, one "bundle<TAB>line number" per line, for the duplicate and both-files checks; and
# the bundle a refused line names, "bundle<TAB><file> line <n>", recorded BEFORE the refusal so the census pass can point
# at that line instead of calling the leg missing from both files
roster_seen=""
excluded_seen=""
refused_seen=""
pending_seen=""   # "bundle<TAB>line number" for each pending line whose source is present: red in the loop, not "in neither" too
pending_n=0
seen_at() { awk -v k="$1" -F '\t' '$1 == k { print $2; exit }' <<<"$2"; }
# The bundle a refused line names: the line's leading whitespace trimmed, then cut at the first whitespace, so a tab before a
# pasted reason, a trailing space, a carriage return, a leading tab and spaces before a tab all resolve to the path. The cut is
# at the first WHITESPACE, not the first tab: a tab cut leaves "<path> " and "<path>\r" unattributed (executed in the tree
# test). The condition that makes the cut safe: a bundle path cannot contain whitespace (well_formed requires
# [^[:space:]]+), so the first word is the path or nothing well formed; if a path ever can, this cut breaks and moves with it.
names_of() { local w=${1#"${1%%[![:space:]]*}"}; printf '%s' "${w%%[[:space:]]*}"; }
remember() {   # $1 the file, $2 the line number, $3 the LINE: record the bundle it names, so the census pass points at this line
  local named; named=$(names_of "$3")
  if well_formed "$named"; then refused_seen="$refused_seen$named	$1 line $2"$'\n'; fi
}
malformed() {   # $1 the file, $2 the line number, $3 the LINE: red with the whitespace visible, and remember the bundle it names
  local shown; shown=$(printf '%q' "$3")
  red "$1 line $2: $shown is not a bundle path (out-tests/<dir>/<name>.test.js; a trailing space, tab or carriage return counts and is shown here as bash's %q spells it): fix the line"
  remember "$1" "$2" "$3"
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
  gap=$(gap_of "$line")
  if ! is_leg "$line"; then red "$ROSTER line $n: '$line' names no browser leg: ${src#"$ROOT/"} ${gap:-reaches no browser (the census rule in $CENSUS): remove the line}"; continue; fi
  if [ -n "$gap" ]; then red "$ROSTER line $n: '$line' does not launch through the one shared launcher ($gap): only inBrowser reads $SWITCH, so a launch or a skip of the leg's own stands outside the switch (a private skip stays a skip; a private launch that fails is never the failure naming the switch): launch through inBrowser (ui/webview/real-viewer-leg.ts), with no launch or skip of the leg's own, before rostering it"; continue; fi
  engines=$(engines_of "$line")
  if [ -n "$engines" ]; then red "$ROSTER line $n: '$line' reaches $engines; the gating job installs Chromium only, so under the switch that launch is red: keep the leg in $EXCLUDED with that reason"; continue; fi
  if [ "$check_only" -eq 0 ] && [ ! -f "$line" ]; then red "$ROSTER line $n: '$line' is not under out-tests/ (the Test step's npm test builds it; locally, node esbuild.js --tests): build the bundles before this step"; continue; fi
  legs+=("$line")
done < "$ROSTER"

n=0
while IFS= read -r line || [ -n "$line" ]; do
  n=$((n + 1))
  [[ "$line" =~ ^[[:space:]]*(#|$) ]] && continue
  bundle=${line%%$'\t'*}
  reason=${line#*$'\t'}
  if [ "$bundle" = "$line" ] || [ -z "${reason//[[:space:]]/}" ]; then red "$EXCLUDED line $n: $(printf '%q' "$line") has no reason (the line as bash's %q spells it): write the bundle path, a tab, and why the gating job does not run it"; remember "$EXCLUDED" "$n" "$line"; continue; fi
  if ! well_formed "$bundle"; then malformed "$EXCLUDED" "$n" "$line"; continue; fi
  at=$(seen_at "$bundle" "$excluded_seen")
  if [ -n "$at" ]; then red "$EXCLUDED line $n: '$bundle' duplicates line $at: remove one"; continue; fi
  excluded_seen="$excluded_seen$bundle	$n"$'\n'
  at=$(seen_at "$bundle" "$roster_seen")
  if [ -n "$at" ]; then red "$EXCLUDED line $n: '$bundle' is also $ROSTER line $at: a leg is in one file or the other, keep one"; continue; fi
  src=$(source_of "$bundle")
  if [[ "$reason" =~ ^[[:space:]]*pending ]]; then
    if [[ ! "$reason" =~ $pending_re ]]; then red "$EXCLUDED line $n: '$bundle' has a pending reason that names no PR ('$reason'): a pending line reads 'pending #<PR>: <why>', the PR whose merge of main brings the leg and promotes the line"; continue; fi
    pr=${BASH_REMATCH[1]}
    if [ -f "$src" ]; then
      pending_seen="$pending_seen$bundle	$n"$'\n'
      red "$EXCLUDED line $n: '$bundle' is pending #$pr and its source ${src#"$ROOT/"} is in the tree, so the leg has arrived (#$pr merged main, or this is #$pr's branch) and the line's condition has passed: promote it: $(promotion_of "$bundle")"
    else
      pending_n=$((pending_n + 1))
    fi
    continue
  fi
  if [ ! -f "$src" ]; then red "$EXCLUDED line $n: '$bundle' names ${src#"$ROOT/"}, which is not in the tree (the source moved or was deleted): fix the line"; continue; fi
  if ! is_leg "$bundle"; then gap=$(gap_of "$bundle"); red "$EXCLUDED line $n: '$bundle' names no browser leg: ${src#"$ROOT/"} ${gap:-reaches no browser (the census rule in $CENSUS): remove the line}"; fi
done < "$EXCLUDED"

while IFS= read -r leg; do
  [ -n "$leg" ] || continue
  if [ -z "$(seen_at "$leg" "$roster_seen")" ] && [ -z "$(seen_at "$leg" "$excluded_seen")" ]; then
    if [ -n "$(seen_at "$leg" "$pending_seen")" ]; then continue; fi   # red above with the promotion remedy
    at=$(seen_at "$leg" "$refused_seen")
    if [ -n "$at" ]; then
      red "browser leg '$leg' is named by a line refused above ($at): fix that line"
    else
      red "browser leg '$leg' is in neither $ROSTER nor $EXCLUDED: add it to the roster (the gating job runs it with a browser), or to the exclusions with a tab and a reason"
    fi
  fi
done < <(census)

if [ "$fail" -ne 0 ]; then echo "ci-browser-legs: the roster and the tree disagree (above); no leg ran" >&2; exit 1; fi
if [ "$check_only" -eq 1 ]; then echo "ci-browser-legs: the roster and the tree agree: ${#legs[@]} rostered, $(census | awk 'END { print NR }') browser legs in the census, $pending_n pending lines naming absent sources (--check judges the two files against the tree and starts no node --test; the step's run also checks that each rostered bundle is built under out-tests/)"; exit 0; fi

if [ "${#legs[@]}" -eq 0 ]; then echo "no legs in the roster"; exit 0; fi
# The run's record goes to a file beside the spec output on stdout, one line per result (the reporter's header states the
# eight fields); the pass below reads it once.
rep=$(mktemp)
trap 'rm -f "$rep"' EXIT
status=0
# --test-timeout bounds each FILE's whole run (node cancels the file and ends the run, naming it; a leg's own { timeout } names
# its test and leaves the process alive on a live browser handle), so a hung leg fails by name inside the step's own
# timeout-minutes (.github/workflows/ci.yml) instead of the job being cancelled nameless. The value sits above the largest
# { timeout } a rostered leg passes and under the step's bound; tools/ci-browser-legs.test.mjs holds both edges. The roster
# array is node's argument list directly (no xargs, whose mapping of a failed command's status differs by platform: 123 on
# GNU, 1 on BSD and macOS), so the status below is node's own everywhere.
node --test --test-timeout=300000 --test-reporter=spec --test-reporter-destination=stdout --test-reporter="$REPORTER" --test-reporter-destination="$rep" "${legs[@]}" || status=$?

# One pass over the record with the roster on stdin: per rostered leg a TALLY line (passes that count, fails that count,
# skips, todos, todo failures, suites, file-level results); and one line per result the step reads a red from: SKIP, TODOFAIL,
# FILEFAIL (the file failed as a whole), LOST (a failure whose message names the switch). Node resolves a bundle from its
# physical working directory, so the roster's lines are keyed by that path.
here=$(pwd -P)
report=$(printf '%s\n' "${legs[@]}" | awk -v msg="$SWITCH is set and this leg cannot run" -F '\t' -v here="$here" '
  NR == FNR { if ($0 != "") { a = here "/" $0; leg[a] = $0; order[++n] = a; p[a] = 0; f[a] = 0; sk[a] = 0; td[a] = 0; tf[a] = 0; su[a] = 0; fl[a] = 0 }; next }
  !($1 in leg) { next }
  {
    if ($2 == "pass" && $3 == "test" && $4 == "-" && $5 == "test") p[$1]++
    if ($2 == "fail" && $4 != "todo") f[$1]++
    if ($4 == "skip") { sk[$1]++; print "SKIP\t" leg[$1] "\t" $6 "\t" $7 }
    if ($4 == "todo") { td[$1]++; if ($2 == "fail") { tf[$1]++; print "TODOFAIL\t" leg[$1] "\t" $6 "\t" $7 } }
    if ($3 == "suite") su[$1]++
    if ($5 == "file-level") { fl[$1]++; if ($2 == "fail") print "FILEFAIL\t" leg[$1] "\t" $8 "\t" $7 }
    if ($2 == "fail" && index($7, msg)) print "LOST\t" leg[$1] "\t" $6 "\t" $7
  }
  END { for (i = 1; i <= n; i++) { a = order[i]; print "TALLY\t" leg[a] "\t" p[a] "\t" f[a] "\t" sk[a] "\t" td[a] "\t" tf[a] "\t" su[a] "\t" fl[a] } }
' - "$rep")
skipped=0
while IFS=$'\t' read -r kind leg a b c d e f g; do
  case "$kind" in
    TALLY)   # $a passes that count, $b fails that count, $c skips, $d todos, $e todo failures, $f suites, $g file-level results
      if [ "$a" -eq 0 ] && [ "$b" -eq 0 ]; then
        echo "ci-browser-legs: $leg: no test of this leg passed in this run (the record holds $c skipped, $d todo, $f suite and $g file-level results for it), so the step claims coverage it did not run: a rostered leg holds a test that runs and passes here; a leg whose tests skip, are todo, or sit behind an unmet condition runs none when it is unmet, so move it to $EXCLUDED with that reason until one runs" >&2
        [ "$status" -ne 0 ] || status=1
      fi;;
    SKIP)
      skipped=1
      echo "ci-browser-legs: skipped with $switch_state: '$a' # SKIP $b ($leg)" >&2;;
    TODOFAIL)
      echo "ci-browser-legs: $leg: '$a' failed inside a todo ($b): node discards the failure (# fail 0, exit 0), so the step would read green over a broken test: remove the todo, or fix the test and remove it" >&2
      [ "$status" -ne 0 ] || status=1;;
    FILEFAIL)
      echo "ci-browser-legs: $leg failed as a whole ($a: $b): a file that timed out under node's --test-timeout, or threw at load, ran no test that counts" >&2
      [ "$status" -ne 0 ] || status=1;;
    LOST)
      echo "ci-browser-legs: $leg: '$a' failed under $switch_state because inBrowser could not launch ($b): the runner lost its browser: check the Chromium install step" >&2
      [ "$status" -ne 0 ] || status=1;;
  esac
done <<<"$report"
if [ "$skipped" -ne 0 ]; then
  if [ -n "${!SWITCH:-}" ]; then
    echo "ci-browser-legs: a rostered leg skipped a test with $switch_state, so the step claims coverage it did not run: the test skips for a reason of its own (only inBrowser in ui/webview/real-viewer-leg.ts turns a launch it cannot make into a failure here); until every test of the leg runs here, move it to $EXCLUDED with that reason" >&2
  else
    echo "ci-browser-legs: a rostered leg skipped a test with $switch_state, so this run claims coverage it did not run: the step sets $SWITCH=1, under which inBrowser in ui/webview/real-viewer-leg.ts fails a launch it cannot make instead of skipping; run with it set, and a test that still skips there skips for a reason of its own" >&2
  fi
  [ "$status" -ne 0 ] || status=1
fi
exit "$status"
