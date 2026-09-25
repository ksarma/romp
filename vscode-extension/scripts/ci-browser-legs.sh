#!/usr/bin/env bash
# Runs the browser legs named in ci-browser-legs.txt under node --test. The step "Browser legs (node --test over
# ci-browser-legs.txt)" of .github/workflows/ci.yml calls this from vscode-extension/ after the job installs Chromium,
# with ROMP_BROWSER_LEGS_REQUIRE=1. The one shared launcher, inBrowser in ui/webview/real-viewer-leg.ts, reads the
# switch (any non-empty value counts), and under the switch, inBrowser fails a launch it cannot make, naming the switch
# and the reason, instead of skipping. Before node --test this script checks the roster file alone, and every red names
# the line (or the file) and what to do:
#   - the roster file is not in vscode-extension/: restore it;
#   - a malformed line (the comment above well_formed states the shape): fix the line;
#   - a duplicate line: remove one;
#   - a line whose source (ui/webview/<name>.test.ts for out-tests/ui/webview/<name>.test.js) is not in the tree, because
#     the source moved or was deleted: fix the line;
#   - a line whose bundle is not under out-tests/ (the Test step's npm test builds it; locally, node esbuild.js --tests).
# The tree test's case "the script refuses" runs each of these reds.
# The roster rule: under the switch, a rostered leg passes only when inBrowser has launched Chromium, and the leg does
# nothing that lets it pass otherwise (for example: it launches no browser of its own; nothing catches or settles
# inBrowser's rejection, so the rejection fails its test; it does not change ROMP_BROWSER_LEGS_REQUIRE, and hands inBrowser
# no test context but the one node gave it; it does not end its own process, from a test, a hook or a timer; no condition
# the runner can leave unmet stands between a browser test and its inBrowser call; it skips and marks todo nothing). The
# reviewer of any PR that adds a roster line or changes a rostered leg's source or inBrowser checks the rule; the step does
# not. Nothing in the tree reads a leg's source for the rule, so the step can read green a rostered leg that breaks it.
# Examples, not the whole set: a rostered leg that launches its own browser and swallows a failed launch without skipping; a
# rostered module that launches nothing; a leg that drives a browser from a child process and tolerates the child's failure;
# a todo test that passes beside a real pass; a leg that catches inBrowser's rejection and passes (a try and catch around
# the awaited call, .catch(), .then's second argument or Promise's allSettled). A leg built to pass without a browser is
# outside what the step can detect. tools/ci-browser-legs.test.mjs runs a synthetic leg of each example and reads it green.
# Nothing checks that every browser leg in the tree is rostered, and main has no such check. inBrowser's read of the
# switch changes inBrowser's own skip alone, so a launch or a skip of the leg's own stands outside that read, and Chromium
# is the one engine the job installs. A leg with no line runs only under the Test step, before the job installs a browser.
# tools/ci-browser-legs.test.mjs (CI's Shell job, no node_modules) runs this script over synthetic trees, with a stub node
# on PATH that records the node --test call and writes the record a case hands it, and with the real node and the real
# reporter. `--check`, read as the first argument alone, runs the pre-run checks alone and starts no node --test (it does
# not check that the bundles are built, which the step's run does). The tree test's case "the script runs the rostered
# legs" runs --check as the first argument, and as the second, where it is not read.
# After node --test it reads the run's record from scripts/ci-browser-legs-reporter.mjs (the reporter's header states
# what each line records) and derives, per rostered leg, that A TEST OF ITS BUNDLE PASSED: at least one result
# attributed to it is a pass that carries no skip or todo, is a test and not a suite, and is not marked as node's
# file-level result (node reports a file that registered nothing, from itself or from a file it loads, as one pass named
# by its path; the reporter's header states what its mark reads). That is the whole of what the record can prove: node's
# events carry no launch, so a bundle that mixes source pins with its browser tests satisfies the property by a pin's
# pass alone, and a browser test behind an unmet condition, which registers nothing and emits no event, leaves no line
# to read; for a leg that follows the roster rule, the skip and lost-browser reads below see inBrowser's own skip and
# failure by name when the launch is reached from a test registered in the bundle, and nothing here proves it was
# reached. A leg with no such pass and no failure outside a todo is red naming the leg and what the record held instead
# (skips, todos, suites, the file-level result), since the step would otherwise claim coverage it did not run; a leg
# with a failure outside a todo and no such pass is node's red, passed through. Beside that property: a test skipped is
# red naming the test, its reason and the switch's state in the run (with the switch unset, as a local run may have it,
# the remedy is to run with it set); a failure inside a todo is red (node discards it: # fail 0, exit 0); a file that
# failed as a whole (node's file-level result failing: node fails a file as a whole when its process exits non-zero or
# is cut at the run's --test-timeout outside any one test's result) is red naming the file and pointing at the spec
# output above for the cause; and a failed test whose message BEGINS with the phrase inBrowser fails with when it cannot
# launch (the switch's name; a message that merely quotes that phrase after other text, as a leg embedding a child run's
# output does, is an ordinary failure) is printed beside its leg with the remedy: the runner lost its browser, check the
# Chromium install step. The property and each of these reds read only the results the record attributes to a rostered
# bundle, so a test registered in any other file, such as one a leg loads at run time outside its bundle, is read
# through node's status alone: its skip, or its failure inside a todo, reads green beside a pass of the bundle's own
# that counts; its failure outside a todo, a lost browser's included, is red by node's status without the lost-browser
# remedy; and a leg whose bundle has neither a pass that counts nor a failure outside a todo is red as unrun, the red's
# tally counting none of that file's results. One pass over the record (awk), linear in its length, executed by the tree
# test's post-run and composition cases. From a checkout whose path holds a backslash, node refuses to load the reporter
# (ERR_INVALID_MODULE_SPECIFIER, the backslash percent-encoded in the reporter's module path) and exits 7 before any leg
# runs, so every rostered leg is red as unrun with a zero tally and the step exits 7 (executed under node 22). An empty
# roster prints "no legs in the roster" and exits 0 without starting node --test: with no file arguments node --test runs
# its default glob, the whole suite again.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
ROOT=$(cd .. && pwd)
ROSTER=ci-browser-legs.txt
SWITCH=ROMP_BROWSER_LEGS_REQUIRE
REPORTER=./scripts/ci-browser-legs-reporter.mjs
# The switch's state in this run, printed by the messages after node --test: set when its value is not empty (any
# non-empty value counts, as in inBrowser's read), unset otherwise; the tree test's post-run case runs it set to 1, set to
# yes and unset. The step sets it to 1; a local run may not, and a skip with it unset is inBrowser skipping as designed, so
# the remedy differs.
if [ -n "${!SWITCH:-}" ]; then switch_state="$SWITCH=${!SWITCH}"; else switch_state="$SWITCH unset"; fi

check_only=0
if [ "${1:-}" = "--check" ]; then check_only=1; fi

if [ ! -f "$ROSTER" ]; then echo "ci-browser-legs: $ROSTER is not in vscode-extension/, where the roster is read from: restore it" >&2; exit 1; fi

fail=0
red() { echo "ci-browser-legs: $*" >&2; fail=1; }
source_of() { local rel=${1#out-tests/}; printf '%s/%s.test.ts' "$ROOT" "${rel%.test.js}"; }
# a bundle path: out-tests/<dir>/<name>.test.js with no whitespace, and canonical, every segment after out-tests/
# non-empty and neither . nor .., the spelling normalizing leaves unchanged (the pattern reads out-tests/, a run with no
# whitespace and .test.js, so a bundle straight under out-tests/ passes too). The roster loop skips, before this check,
# a line of whitespace alone (an empty one among them) and one whose first non-blank character is #. Node resolves a
# bundle to that spelling and the post-run read keys a line by it; the duplicate check below reads only the lines that
# pass here, so it compares canonical paths. Whitespace here, and in the loop's test for a blank or # line, is bash's
# [[:space:]] in the runner's locale, not the tree test's \s: a no-break space inside a line passes here under C.UTF-8
# and is refused there, and a line holding a byte-order mark or a no-break space before its # is refused here as
# malformed and dropped there, a red on one side. The tree test's case "the script refuses" runs the malformed rows (six
# whitespace shapes and three non-canonical spellings), and its case "the script runs the rostered legs" a bundle
# straight under out-tests/ and the empty roster's comment line and whitespace-only line, both skipped.
well_formed() {
  [[ "$1" =~ ^out-tests/[^[:space:]]+\.test\.js$ ]] || return 1
  local seg rest="${1#out-tests/}/"
  while [ -n "$rest" ]; do
    seg=${rest%%/*}; rest=${rest#*/}
    case "$seg" in ''|.|..) return 1;; esac
  done
}
# the lines seen so far, one "bundle<TAB>line number" per line, for the duplicate check. seen_at hands awk the line in its
# environment (ENVIRON), so the line is compared as written: a value given with awk's -v has its backslash escapes
# processed, which would pass a line holding a\b rostered twice and refuse a line holding a\\b beside it as a duplicate.
# The tree test's case "the script refuses" runs both, in the step's run and under --check.
roster_seen=""
seen_at() { k="$1" awk -F '\t' '$1 == ENVIRON["k"] { print $2; exit }' <<<"$2"; }
malformed() {   # $1 the file, $2 the line number, $3 the LINE: red with the whitespace visible
  local shown; shown=$(printf '%q' "$3")
  red "$1 line $2: $shown is not a bundle path (out-tests/<dir>/<name>.test.js in its canonical spelling, no empty, . or .. segment; a trailing space, tab or carriage return counts and is shown here as bash's %q spells it): fix the line"
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
  if [ "$check_only" -eq 0 ] && [ ! -f "$line" ]; then red "$ROSTER line $n: '$line' is not under out-tests/ (the Test step's npm test builds it; locally, node esbuild.js --tests): build the bundles before this step"; continue; fi
  legs+=("$line")
done < "$ROSTER"

if [ "$fail" -ne 0 ]; then echo "ci-browser-legs: the roster is malformed or stale, or a rostered bundle is not built (above); no leg ran" >&2; exit 1; fi
if [ "$check_only" -eq 1 ]; then echo "ci-browser-legs: the roster is well formed and every line names a source in the tree: ${#legs[@]} rostered (--check reads the roster alone and starts no node --test; the step's run also checks that each rostered bundle is built under out-tests/)"; exit 0; fi

if [ "${#legs[@]}" -eq 0 ]; then echo "no legs in the roster"; exit 0; fi
# The run's record goes to a file beside the spec output on stdout, one line per result (the reporter's header states the
# eight fields); the pass below reads it once.
rep=$(mktemp)
trap 'rm -f "$rep"' EXIT
status=0
# --test-timeout bounds each FILE's whole run (node cancels that file and ends its process at the bound, naming it, and runs
# the other files on; a leg's own { timeout } names its test and leaves the process alive on a live browser handle), so a
# hung leg fails by name inside the step's own timeout-minutes (.github/workflows/ci.yml) instead of the job being cancelled
# nameless. The value sits above every timeout: value the tree test's bound pin reads in a rostered source and under the
# step's bound, and tools/ci-browser-legs.test.mjs holds both edges; its bound pin states the spellings it reads, and a leg
# whose timeout is spelled outside them and whose file outlasts this bound is cut here and named as a file that failed as a
# whole, testTimeoutFailure, not by its test. The roster array is node's argument list directly (no xargs, whose
# mapping of a failed command's status differs by platform: 123 on GNU, 1 on BSD and macOS), so the status below is node's
# own everywhere.
node --test --test-timeout=240000 --test-reporter=spec --test-reporter-destination=stdout --test-reporter="$REPORTER" --test-reporter-destination="$rep" "${legs[@]}" || status=$?

# One pass over the record with the roster on stdin: per rostered leg a TALLY line (passes that count, fails that count,
# skips, todos, todo failures, suites, file-level results); and one line per result the step reads a red from: SKIP, TODOFAIL,
# FILEFAIL (the file failed as a whole), LOST (the lost-browser read the header states). Node resolves a bundle from its
# physical working directory, so the roster's lines are keyed by that path, handed to awk in its environment (ENVIRON) and
# read as written: awk's -v would process its backslash escapes (a\t in a directory's name read as a tab), and every leg
# would be red as unrun. The tree test's case "the script runs the rostered legs" runs a tree under a directory whose name
# holds a backslash.
here=$(pwd -P)
report=$(printf '%s\n' "${legs[@]}" | here="$here" awk -v msg="$SWITCH is set and this leg cannot run" -F '\t' '
  NR == FNR { if ($0 != "") { a = ENVIRON["here"] "/" $0; leg[a] = $0; order[++n] = a; p[a] = 0; f[a] = 0; sk[a] = 0; td[a] = 0; tf[a] = 0; su[a] = 0; fl[a] = 0 }; next }
  !($1 in leg) { next }
  {
    if ($2 == "pass" && $3 == "test" && $4 == "-" && $5 == "test") p[$1]++
    if ($2 == "fail" && $4 != "todo") f[$1]++
    if ($4 == "skip") { sk[$1]++; print "SKIP\t" leg[$1] "\t" $6 "\t" $7 }
    if ($4 == "todo") { td[$1]++; if ($2 == "fail") { tf[$1]++; print "TODOFAIL\t" leg[$1] "\t" $6 "\t" $7 } }
    if ($3 == "suite") su[$1]++
    if ($5 == "file-level") { fl[$1]++; if ($2 == "fail") print "FILEFAIL\t" leg[$1] "\t" $8 "\t" $7 }
    # LOST: the lost-browser read the header states. It reads the start of the message because the assertion messages of
    # the rostered switch test embed the stdout of a child run, which carries the phrase after other text (the tree test
    # pins the literal in ui/webview/real-viewer-leg.ts). No apostrophe here: this awk program is a single-quoted bash
    # string.
    if ($2 == "fail" && index($7, msg) == 1) print "LOST\t" leg[$1] "\t" $6 "\t" $7
  }
  END { for (i = 1; i <= n; i++) { a = order[i]; print "TALLY\t" leg[a] "\t" p[a] "\t" f[a] "\t" sk[a] "\t" td[a] "\t" tf[a] "\t" su[a] "\t" fl[a] } }
' - "$rep")
skipped=0
while IFS=$'\t' read -r kind leg a b c d e f g; do
  case "$kind" in
    TALLY)   # $a passes that count, $b fails that count, $c skips, $d todos, $e todo failures, $f suites, $g file-level results
      if [ "$a" -eq 0 ] && [ "$b" -eq 0 ]; then
        echo "ci-browser-legs: $leg: no test of this leg passed in this run (the record holds $c skipped, $d todo, $f suite and $g file-level results for it), so the step claims coverage it did not run: a rostered leg holds a test that runs and passes here (a pass is the most the record proves: a pass from a test needing no browser satisfies this check, and, for a leg that follows the roster rule, the browser part's own run is read only by the skip and lost-browser lines when its launch is reached); a leg whose tests skip, are todo, or sit behind an unmet condition runs none when it is unmet, so take its line out of $ROSTER until one runs" >&2
        [ "$status" -ne 0 ] || status=1
      fi;;
    SKIP)
      skipped=1
      echo "ci-browser-legs: skipped with $switch_state: '$a' # SKIP $b ($leg)" >&2;;
    TODOFAIL)
      echo "ci-browser-legs: $leg: '$a' failed inside a todo ($b): node discards the failure (# fail 0, exit 0), so the step would read green over a broken test: remove the todo, or fix the test and remove it" >&2
      [ "$status" -ne 0 ] || status=1;;
    FILEFAIL)
      echo "ci-browser-legs: $leg failed as a whole ($a: $b): node fails a file as a whole when its process exits non-zero or is cut at the run's --test-timeout outside any one test's result: read the spec output above for the cause" >&2
      [ "$status" -ne 0 ] || status=1;;
    LOST)
      echo "ci-browser-legs: $leg: '$a' failed under $switch_state because inBrowser could not launch ($b): the runner lost its browser: check the Chromium install step" >&2
      [ "$status" -ne 0 ] || status=1;;
  esac
done <<<"$report"
if [ "$skipped" -ne 0 ]; then
  if [ -n "${!SWITCH:-}" ]; then
    echo "ci-browser-legs: a rostered leg skipped a test with $switch_state, so the step claims coverage it did not run: the test skips for a reason of its own (under the switch, inBrowser in ui/webview/real-viewer-leg.ts fails a launch it cannot make instead of skipping); until every test of the leg runs here, take its line out of $ROSTER" >&2
  else
    echo "ci-browser-legs: a rostered leg skipped a test with $switch_state, so this run claims coverage it did not run: the step sets $SWITCH=1, under which inBrowser in ui/webview/real-viewer-leg.ts fails a launch it cannot make instead of skipping; run with it set, and a test that still skips there skips for a reason of its own" >&2
  fi
  [ "$status" -ne 0 ] || status=1
fi
exit "$status"
