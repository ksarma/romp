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
# not. Nothing checks the whole rule for every rostered leg, so the step can read green a rostered leg that breaks it.
# Examples, not the whole set: a rostered leg that launches its own browser and swallows a failed launch without skipping; a
# rostered module that launches nothing; a leg that drives a browser from a child process and tolerates the child's failure;
# a todo test that passes beside a real pass; a leg that catches inBrowser's rejection and passes (a try and catch around
# the awaited call, .catch(), .then's second argument or Promise's allSettled). A leg built to pass without a browser is
# outside what the step can detect. tools/ci-browser-legs.test.mjs runs a synthetic leg of each example and reads it green.
# Nothing checks that every browser leg in the tree is rostered, and main has no such check. inBrowser's read of the
# switch changes inBrowser's own skip alone, so a launch or a skip of the leg's own stands outside that read, and Chromium
# is the one engine the job installs. A leg with no line runs only under the Test step, before the job installs a browser.
# tools/ci-browser-legs.test.mjs (CI's vendored-tooling job, no node_modules) runs this script over synthetic trees,
# with a stub node on PATH that records each node --test call and writes the record a case hands it, and with the real
# node and the real reporter. `--check`, read as the first argument alone, runs the pre-run checks alone and starts no
# node --test (it does not check that the bundles are built, which the step's run does). The tree test's case "the
# script runs the rostered legs" runs --check as the first argument, and as the second, where it is not read.
# How the legs run. Each rostered leg runs as a node --test of its own over that one bundle, ROMP_BROWSER_LEGS_JOBS at a
# time (by default one less than the CPUs that nproc, or getconf, counts, and at least one, which is node's own
# --test-concurrency default where no cgroup CPU quota applies, as on CI's hosted runner: node counts the CPUs by
# os.availableParallelism(), which honours such a quota and nproc does not, so under one the script runs more legs at
# once than node would, and ROMP_BROWSER_LEGS_JOBS sets the count; nproc runs with OMP_NUM_THREADS and OMP_THREAD_LIMIT
# unset, since GNU nproc honours them and node's count does not), started in roster order, each start printed at once on
# a line naming the leg, so a log cut short (by the step's own timeout, say) still names the legs that were running;
# each run's spec output and stderr are held and printed in roster order, after a line naming the leg and its node
# --test's exit, so a leg's spec output appears when the leg and every leg before it in roster order have ended.
# The step's status is node's own: the first non-zero exit among those runs, in roster order, a run the grace's end
# killed aside. On an INT or a TERM the script ends each leg still running, as the grace's end below does, waits for
# that leg's subshell to write its node --test's exit, and then prints in roster order every leg's output it still
# holds, the ended legs' partial output among it, each after the line naming its exit; a further INT, TERM or HUP while
# it does so is ignored, so it cannot cut that short. A SIGKILL runs no trap: the output still held then is lost, the
# run's directory stays in TMPDIR, and the legs still running, the processes under them and their timers run on until
# they end (each posts to the event pipe through the descriptor it inherited and holds open itself, so none waits for a
# reader that is gone). The per-file bound: ROMP_BROWSER_LEGS_FILE_MS (default 240000) ms after a leg's node --test
# starts, the script stops and kills every process under that node --test, found by parent links over the whole process
# table (the file's own node process, and a browser Playwright launched, which runs in a session of its own and so
# outside the file's process group, among them), with the process group each of them leads, which reaches a process left
# in such a group after its parent exited, outside the parent links. Two kinds of process are reached by neither: a
# process double-forked out of the tree into a group whose leader has exited, as Chromium starts its crash handler (that
# handler ends when its browser does: recorded with Playwright's new-headless Chromium on a development box, not
# executed here), and a process left in the file's own process group, this script's, after its parent exited, since no
# kill signals that group (the file's process shares this script's own process group, which holds the script itself).
# The walk stops each process it finds and reads the table again until a read finds no new one, a guard against a
# process that forks during the walk, which no case executes. node --test then records the file as failed as a whole
# (its process ended on a signal), beside the results the file recorded before the kill, and the cut's red after the run
# names the leg and the bound. When the walk finds no live process under the leg's node --test (none, or only processes
# that had already ended, a zombie not yet reaped among them: its file's process had ended and node --test was ending),
# the leg is not cut. A node --test still running ROMP_BROWSER_LEGS_GRACE_MS (default 10000) ms after the bound is
# killed too, with what is under it, and named; one that has exited by then (gone, or a zombie its subshell has not yet
# reaped) with nothing alive under it is not named, and its exit is read as any other leg's. node's own --test-timeout
# is not passed: on node 22.23.2 its cancel at the bound reports the file and sends the file's process alone a SIGTERM,
# and node --test then waits for that process; the process of a leg that had launched a browser outlived the signal
# (Playwright handles SIGTERM itself; recorded on a development box through the step's own command, not executed here),
# and a file's process that does end on the signal leaves what is under it running, before any walk reads the tree. The
# knobs are whole numbers above 0 of at most 9 digits (digits alone, no leading zero), refused by name before any leg
# runs, and the step sets none of them. The tree test's case "the per-file bound ends a leg that outlives it" runs, with
# the real node and a short bound, a synthetic leg whose node process ignores SIGTERM and starts a process in a session
# of its own and one in the file's own process group, each with a child, and a process in a session of its own whose
# child exits at once and leaves a grandchild in its group, reparented out of the tree, and reads every one of those
# processes gone by the bound plus the grace; its case "a TERM to the script" reads each leg's start line printed while
# the legs run, then those processes, the hanging leg's node --test and the run's timers gone after a TERM, and the held
# output printed, the hanging leg's after a line naming its node --test's exit (137, the kill's); its case "a second
# TERM to the script" reads them and that node --test gone when a second TERM comes 100 ms after the first, that leg's
# output after the same line, and the run's TMPDIR empty; its case "a SIGKILL to the script" reads the leg's subshell
# and its timer gone once the leg and its bound have ended; its case "the per-file bound through the stub" runs the
# grace's end after a cut and with nothing cut, a node --test that has exited and is not yet reaped when the grace runs
# out, a node --test that outlives the bound with nothing under it or with only a zombie under it, the knobs' refusals,
# the status of legs that exit differently, and a roster longer than the legs run at once; its case "the per-file bound
# counts from each leg's own start" runs, with the real node, two legs one at a time, each shorter than the bound and
# the two together longer, and reads neither cut. The timers and the event pipe use what bash 3.2 has (no wait -n), as
# tests/shell-portability.bats holds for every shell script the repo ships. The legs' records are joined in roster order
# into the one record the pass below reads.
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
# ends on a signal, the bound's kill among them, outside any one test's result) is red naming the file and pointing at
# the spec output above for the cause; and a failed test whose message BEGINS with the phrase inBrowser fails with when
# it cannot launch (the switch's name; a message that merely quotes that phrase after other text, as a leg embedding a
# child run's output does, is an ordinary failure) is printed beside its leg with the remedy: the runner lost its
# browser, check the Chromium install step. The property and each of these reds read only the results the record
# attributes to a rostered bundle, so a test registered in any other file, such as one a leg loads at run time outside
# its bundle, is read through node's status alone: its skip, or its failure inside a todo, reads green beside a pass of
# the bundle's own that counts; its failure outside a todo, a lost browser's included, is red by node's status without
# the lost-browser remedy; and a leg whose bundle has neither a pass that counts nor a failure outside a todo is red as
# unrun, the red's tally counting none of that file's results. One pass over the record (awk), linear in its length,
# executed by the tree test's post-run and composition cases. From a checkout whose path holds a backslash, node refuses
# to load the reporter (ERR_INVALID_MODULE_SPECIFIER, the backslash percent-encoded in the reporter's module path) and
# each leg's node --test exits 7 before its leg runs, so every rostered leg is red as unrun with a zero tally and the
# step exits 7 (executed under node 22). An empty roster prints "no legs in the roster" and exits 0 without starting
# node --test: with no file arguments node --test runs its default glob, the whole suite again.
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
# malformed and dropped there, a red on one side. The tree test's case "the script refuses" runs the malformed rows (a
# source path and five whitespace shapes, each shown as bash's %q spells it, and three non-canonical spellings), and its
# case "the script runs the rostered legs" a bundle straight under out-tests/ and the empty roster's comment line and
# whitespace-only line, both skipped.
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

# The per-file bound, its grace and the number of legs run at once, the knobs the header's "How the legs run" states, each
# a whole number above 0 of at most 9 digits, refused by name before any leg runs. The bound's default sits above every
# timeout: value the tree test's bound pin reads in a rostered source, and the bound and the grace together sit under the
# step's own timeout-minutes (.github/workflows/ci.yml), so a hung leg fails by name inside the step instead of the job
# being cancelled nameless (for a leg that starts within the step's first timeout-minutes less the bound and the grace,
# 50 s at the defaults: the bound counts from each leg's own start, and a leg queued later than that can be cut by the
# step first); tools/ci-browser-legs.test.mjs holds those edges, and its bound pin states the spellings it reads. A leg
# whose timeout is spelled outside them and whose file outlasts the bound is cut here and named by the cut's red, not by
# its test.
BOUND_MS=${ROMP_BROWSER_LEGS_FILE_MS:-240000}
GRACE_MS=${ROMP_BROWSER_LEGS_GRACE_MS:-10000}
# GNU nproc honours OMP_NUM_THREADS and OMP_THREAD_LIMIT, which node's count of the CPUs does not, so nproc runs without
# them; node's count also honours a cgroup CPU quota, which nproc does not (the header's "How the legs run")
cpus=$(env -u OMP_NUM_THREADS -u OMP_THREAD_LIMIT nproc 2>/dev/null || getconf _NPROCESSORS_ONLN 2>/dev/null || echo 2)
JOBS=${ROMP_BROWSER_LEGS_JOBS:-$(( cpus > 1 ? cpus - 1 : 1 ))}
# At most 9 digits, a cap far inside bash's integer range: a value of 2^63 or more (19 digits and up) wraps in secs()
# below, and the timer's sleep then fails at once or sleeps for ages, so the bound would never fire, and nothing would say
# so.
whole() { case "$2" in ''|*[!0-9]*|0*|??????????*) echo "ci-browser-legs: $1='$2' is not a whole number above 0 of at most 9 digits (digits alone, no leading zero): fix it or unset it; no leg ran" >&2; exit 1;; esac; }
whole ROMP_BROWSER_LEGS_FILE_MS "$BOUND_MS"
whole ROMP_BROWSER_LEGS_GRACE_MS "$GRACE_MS"
whole ROMP_BROWSER_LEGS_JOBS "$JOBS"
secs() { printf '%d.%03d' $(( $1 / 1000 )) $(( $1 % 1000 )); }

# The run's files, in one directory under TMPDIR that the EXIT trap removes: per leg i (its place in the roster, from 0),
# its spec output (i.out), its node --test's stderr (i.err), its record (i.rec; the reporter's header states the eight
# fields of a line), its node --test's pid (i.pid) and exit (i.status), and a mark when the bound cut it (i.cut) or its node
# --test outlived the grace (i.held); the record the pass below reads, the legs' records in roster order; and the event
# pipe, on which each leg's subshell posts "done i" when its node --test exits and each timer posts "bound i" or "grace i"
# when it runs out. This shell opens the pipe for reading and writing on fd 3, and each leg's subshell and each timer
# inherits that descriptor and posts through it, holding the pipe open itself, so a post never waits for a reader, even
# after this shell is gone (a SIGKILL); node and the timer's sleep are handed no fd 3, so nothing the leg starts holds it.
job=(); tmr=(); fin=()
started=0
work=$(mktemp -d)
# On any exit: each leg still running is ended (its timer's group killed, its node --test and every process under it
# killed, as end_leg below does) and its subshell waited for, so the subshell has written its node --test's exit (137,
# the kill's) before the output is printed and writes nothing in the run's directory while it is removed (a write that
# landed during the removal failed it, and the script exited 1 instead of the signal's status, leaving the directory);
# then every started leg's output not yet printed is printed in roster order (on an INT or a TERM: the ended legs'
# partial output, and the whole output of legs that finished behind one still running), then the run's directory is
# removed. A further INT, TERM or HUP while it does so is ignored (its first line), so a second
# signal cannot end the shell between a stop and its kill, which would leave the rest of the legs running and the one being
# ended stopped for good. A leg counts as started before its launch begins, so a signal that lands during the launch ends
# what the launch had started by then; a signal in the gap between a background start and the next command, which keeps
# its pid (tmr[i] or job[i]), can leave that one process outside this reach.
cleanup() {
  trap '' INT TERM HUP
  local i=0
  while [ "$i" -lt "$started" ]; do
    if [ -z "${fin[$i]:-}" ]; then
      [ -z "${tmr[$i]:-}" ] || kill -TERM -- "-${tmr[$i]}" 2>/dev/null || true
      end_leg "$i" exit || true
      [ -z "${job[$i]:-}" ] || wait "${job[$i]}" 2>/dev/null || true
    fi
    i=$((i + 1))
  done
  while [ "${shown:-0}" -lt "$started" ]; do show "${shown:-0}"; shown=$(( ${shown:-0} + 1 )); done
  rm -rf "$work"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
rep="$work/record"
events="$work/events"
mkfifo "$events"
exec 3<>"$events"
# The pid kill_below starts from for leg $1: its node --test's, or, before that pid is written, the leg's subshell's, or
# none before the launch keeps that one (kill_below then starts nothing).
runner() { local p=""; [ ! -s "$work/$1.pid" ] || read -r p < "$work/$1.pid"; echo "${p:-${job[$1]:-}}"; }
# Every process under $1 (not $1 itself), found by parent links over the whole process table (ps -A): each one found is
# stopped at once (SIGSTOP, so it forks nothing more), the table is read again until a read finds no new one, and then each
# is killed (SIGKILL), the process group it leads first. A browser Playwright launched runs in a session of its own, outside
# the file's process group, so a kill of the file's group alone would miss it; the group it leads is its own, and the group
# kill also reaches a process left in that group after its parent exited, which the parent links no longer lead to. A pid
# that is not a number above 1 starts nothing. After the stops, each process found is read again: one that is gone, or is
# a zombie (it has ended and its parent has not reaped it), had ended on its own before its stop, and a stopped one cannot
# end on its own. Returns 1 when it found no live process (none at all, or only ones that had ended, such as a file's
# process that ended just before the walk and that node --test has not yet reaped), 0 when it killed one. Either way the
# kills go to every process found, and so to the group each leads.
kill_below() {
  local all=" " found p live=""
  case "$1" in ''|*[!0-9]*|0|1) return 1;; esac
  while :; do
    found=$(ps -A -o pid= -o ppid= | awk -v r="$1" -v seen="$all" '{ kids[$2] = kids[$2] " " $1 } END { q[1] = r; n = 1; for (i = 1; i <= n; i++) { m = split(kids[q[i]], c, " "); for (j = 1; j <= m; j++) { q[++n] = c[j]; if (index(seen, " " c[j] " ") == 0) printf "%s ", c[j] } } }')
    [ -n "$found" ] || break
    kill -STOP $found 2>/dev/null || true
    all="$all$found"
  done
  [ "$all" != " " ] || return 1
  for p in $all; do case "$(ps -o stat= -p "$p" 2>/dev/null)" in ''|*Z*) ;; *) live=1; break;; esac; done
  for p in $all; do kill -KILL -- "-$p" 2>/dev/null || true; done
  kill -KILL $all 2>/dev/null || true
  [ -n "$live" ]
}
# Ends leg $1's node --test with every process under it (at the grace's end, and on an exit before the legs ended): the
# node --test is stopped first, so it starts nothing between the walk and its own kill (a guard, like the walk's own
# stops, against a process that forks during the walk, which no case executes). The leg's subshell is left to post
# its "done" (when the node --test never started, kill_below took what was under the subshell instead). With a second
# argument (on an exit), a leg whose node --test has not written its pid yet (the exit came during its launch) is ended
# with its subshell, stopped first and killed last as a node --test is, so the exit's wait for that subshell cannot sit
# through a leg the subshell would start next (a guard no case executes: no case sends a signal during a launch).
# Returns 0 when it found a live process to kill (the node --test, read after its stop as kill_below reads a process,
# or one under it), 1 when it found none: a node --test that had exited (gone, or a zombie its subshell had not yet
# reaped, since that subshell posts "done" only after it reaps it) with nothing alive under it.
end_leg() {
  local p live=""; p=$(runner "$1")
  if [ "$p" != "${job[$1]:-}" ] || [ -n "${2:-}" ]; then
    kill -STOP "$p" 2>/dev/null || true
    case "$(ps -o stat= -p "$p" 2>/dev/null)" in ''|*Z*) ;; *) live=1;; esac
  fi
  kill_below "$p" && live=1
  if [ "$p" != "${job[$1]:-}" ] || [ -n "${2:-}" ]; then kill -KILL "$p" 2>/dev/null || true; fi
  [ -n "$live" ]
}
# A timer for leg $1: $3 ms after it starts it posts "$2 $1". Its sleep runs in a process group of its own (set -m), whose
# id is tmr[$1], so the leg's end kills the sleep with its group; it is started from a subshell that exits at once, so the
# process killed is never a job of this shell, and bash prints no job notice. It holds none of this script's output, so
# nothing reading the step's output waits on a timer; it posts through the event pipe's fd 3, which it inherits.
timer() {
  set -m
  ( ( sleep "$(secs "$3")" 3>&- && echo "$2 $1" >&3 ) & ) >/dev/null 2>&1 &
  set +m
  tmr[$1]=$!
}
# Leg $1: a line naming it, printed at once, then its bound's timer, then its node --test over that one bundle, in a
# subshell that writes the pid and the exit and posts "done $1" through the event pipe's fd 3, which it inherits. Node's
# stdin is /dev/null, as for any background job of a shell without job control.
launch() {
  local i=$1 d="$work/$1"
  echo "ci-browser-legs: started ${legs[$i]}"
  timer "$i" bound "$BOUND_MS"
  (
    set +e
    node --test --test-reporter=spec --test-reporter-destination=stdout --test-reporter="$REPORTER" --test-reporter-destination="$d.rec" "${legs[$i]}" >"$d.out" 3>&- &
    p=$!
    echo "$p" > "$d.pid"
    wait "$p"
    echo "$?" > "$d.status"
    echo "done $i" >&3
  ) 2>"$d.err" &
  job[$i]=$!
}
# Leg $1's spec output to stdout and its node --test's stderr to stderr, after a line naming the leg and its exit.
show() {
  local d="$work/$1" st=""
  [ ! -s "$d.status" ] || read -r st < "$d.status"
  echo "ci-browser-legs: ${legs[$1]} (node --test exited ${st:-with no status}):"
  [ ! -f "$d.out" ] || cat "$d.out"
  [ ! -f "$d.err" ] || cat "$d.err" >&2
}

n=${#legs[@]}
echo "ci-browser-legs: $n rostered legs, $JOBS at a time, each its own node --test, cut with every process under it if still running $BOUND_MS ms after it starts"
finished=0
shown=0
while [ "$started" -lt "$n" ] && [ "$started" -lt "$JOBS" ]; do started=$((started + 1)); launch $((started - 1)); done
while [ "$finished" -lt "$n" ]; do
  read -r event i <&3
  [ -z "${fin[$i]:-}" ] || continue   # a timer that ran out as its leg ended
  case "$event" in
    bound)
      # a cut only when the walk found a live process to kill: a node --test whose file's process had already ended (gone,
      # or a zombie not yet reaped), ending itself as the bound came, is not cut, and its exit is read as any other leg's
      tmr[$i]=""
      if kill_below "$(runner "$i")"; then : > "$work/$i.cut"; fi
      timer "$i" grace "$GRACE_MS";;
    grace)
      # held only when end_leg found a live process to kill: a node --test that had exited as the grace ran out (gone, or a
      # zombie its subshell had not yet reaped), with nothing alive under it, is not held, and its exit is read as any
      # other leg's
      tmr[$i]=""
      if end_leg "$i"; then : > "$work/$i.held"; fi;;
    done)
      fin[$i]=1
      finished=$((finished + 1))
      [ -z "${tmr[$i]:-}" ] || kill -TERM -- "-${tmr[$i]}" 2>/dev/null || true
      tmr[$i]=""
      if [ "$started" -lt "$n" ]; then started=$((started + 1)); launch $((started - 1)); fi
      while [ "$shown" -lt "$n" ] && [ -n "${fin[$shown]:-}" ]; do show "$shown"; shown=$((shown + 1)); done;;
  esac
done

# The step's status is node's own: the first non-zero exit among the legs' node --test runs, in roster order, a run the
# script killed at the grace's end aside (its exit is the kill's, and its red below sets the status). Node's exit reaches
# it directly, with no xargs to map it (123 on GNU, 1 on BSD and macOS), so the status is node's own everywhere.
status=0
: > "$rep"
i=0
while [ "$i" -lt "$n" ]; do
  [ ! -f "$work/$i.rec" ] || cat "$work/$i.rec" >> "$rep"
  if [ "$status" -eq 0 ] && [ ! -e "$work/$i.held" ] && [ -s "$work/$i.status" ]; then read -r st < "$work/$i.status"; [ "$st" -eq 0 ] || status=$st; fi
  i=$((i + 1))
done

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
      echo "ci-browser-legs: $leg failed as a whole ($a: $b): node fails a file as a whole when its process exits non-zero, or ends on a signal such as the per-file bound's kill, outside any one test's result: read the spec output above for the cause" >&2
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
# The bound's reds, in roster order: a leg the bound cut, and a leg whose node --test the grace's end killed too.
i=0
while [ "$i" -lt "$n" ]; do
  if [ -e "$work/$i.cut" ]; then
    echo "ci-browser-legs: ${legs[$i]} ran past the per-file bound ($BOUND_MS ms), so the script killed its file's node process and every process under it, any browser it launched among them: the results it recorded before the kill are read here, and its spec output above shows where it stood; a leg that needs longer is split, or the bound (the default of ROMP_BROWSER_LEGS_FILE_MS in this script) is raised, under the step's timeout-minutes" >&2
    [ "$status" -ne 0 ] || status=1
  fi
  if [ -e "$work/$i.held" ]; then
    echo "ci-browser-legs: ${legs[$i]}: its node --test had not ended $GRACE_MS ms after the per-file bound, so the script killed it too, with every process under it: its record may be cut short, so read its spec output above" >&2
    [ "$status" -ne 0 ] || status=1
  fi
  i=$((i + 1))
done
exit "$status"
