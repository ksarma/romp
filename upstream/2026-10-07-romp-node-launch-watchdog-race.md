---
title: The node probe's watchdog ends its sleep wherever its stand-down lands, in the launcher and in the install
status: candidate
where: bin/romp-node-launch (_probe_node: the watchdog subshell and the comment above it; the comment above _end_sleep); bin/romp-service (_node_runs: the watchdog subshell and the comment above it); tests/romp-node-launch.bats (teardown; _stand_down_at, _stand_down_asserts and three stand-down cases); tests/romp-service.bats (teardown; _install_stand_down_at, _install_stand_down_asserts and three stand-down cases); upstream/2026-10-07-romp-node-launch-watchdog-race.md (this entry)
added: 2026-10-07
pr:
tier: fix
offered:
closed:
---
On the watchdog path of the node probe (no coreutils `timeout` on PATH, the normal case on a stock mac), a stand-down TERM that the shell handled after the watchdog forked its sleep but before `_s=$!` recorded the pid ran the trap with no pid, so the trap ended nothing and the sleep ran on to its bound (ten seconds by default) after the launcher had exec'd the manager. bin/romp-service's install probe has the same watchdog and the same race. In both, the trap now records the stand-down in a flag when it has no pid, and a check right after the assignment ends the sleep.

On the fork's CI the race failed the launcher's session check twice in 964 completed runs of the Shell (bats, ubuntu-latest) job that carried the check, in the 30 days to 2026-09-30. A local loop over the launcher's own functions left a sleep, each time after a trap with no pid, in 10 of 1,500 iterations under CPU contention and in 18 of 20 with strace delaying every fork's return; on a quiet machine it left none in 3,000.

The fix covers every point where the TERM can land. Before the trap is set, TERM's default action ends the subshell before it forks anything. Between the trap and the fork, or between the fork and the assignment, the trap sets the flag and returns, and the check after the assignment ends the sleep. After the assignment, the wait included, the trap finds the pid, ends the sleep and exits. The trap never falls back to `$!`: before the fork, `$!` in the subshell is the probe wrapper's pid, inherited from the launcher, and ending the wrapper's tree would fail a good copy.

The new tests are deterministic. Under bash with `set -T`, a DEBUG trap read through BASH_ENV sends the watchdog its TERM just before a named command of its own, so the pending TERM trap runs at that point. Each file gets three cases: before the fork, between the fork and the assignment, and after the assignment. Each case checks that the watchdog exited on that one TERM, that the probe's wrapper and the copy under it got no signal, that the sleep is gone and that nothing is left in the session. On the fork's main the case between the fork and the assignment failed 10 of 10 runs in each file, with the watchdog's sleep still running; the other two cases passed. With the fix, all six cases passed 10 of 10 runs. Three broken versions of the fix each fail at least one case: a trap that falls back to `$!` kills the probe's wrapper, so the launcher runs the manager on the system node and the install removes a good copy; the fix without the check after the assignment leaves the watchdog waiting out its bound, which holds the launch for that long; a trap that exits even when it has no pid leaves the sleep, as on main.

The local loop, re-run under the same contention (the loop and four busy loops pinned to the same two CPUs, with dash as /bin/sh), 1,500 iterations each: main's functions left a sleep in 4 iterations, each one after a trap with no pid; the fixed functions left none, and their trap ran with no pid in 7 of those iterations.

tests/romp-node-launch.bats passes 27 of 27 with the fix and 24 of 24 on main; tests/romp-service.bats passes 59 of 59 and 56 of 56; tests/shell-portability.bats passes 13 of 13 on both.

upstream/main has the same code: its bin/romp-node-launch is identical to the fork's, and its bin/romp-service carries the same watchdog line in `_node_runs`. The diff applies to upstream's copies of the four changed code and test files in a patch dry run; it has not been run against that tree.
