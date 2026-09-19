#!/usr/bin/env python3
"""Fold ruling A condition 7 as the reviewer ruled it on 2026-09-19 after jobs stage 1 (fork PR 784), stated PER MECHANISM:
the condition bounds two loaders of a session's goal store on the walk's road, the look's decision read and the placement
gate's currency check, each on its own. The WALK takes at most one shared goal-store load per alive session per pass:
exactly one when its look reaches the store, zero when the look is skipped or ends at a state gate before the store read.
The PLACEMENT GATE's post-derivation currency check is a SEPARATE load, at most one per DERIVED session, counted apart. Two
bounds, each attributable to its caller. Other readers of the same store run on the same pass under their own rules and
outside both bounds; the reference's `jobs` block (docs/reference.md) names them with their bounds and their callers on the
toggle-off pass, and the Docs case pins that text and this pointer (one home for the clause: review round 2 found it in four
hand-kept copies, two of them pinned by nothing). The rule was first written as one call count;
a total is falsified by any new legitimate reader of the store, where a
named mechanism adds a clause, so the counts below never sum the two. Stage 1 made the wake-only look record a memo row and skip on the
ten-file key, and the first wording of its amendment kept the walk's ceiling (at most one) and dropped the floor; the ruling
restored the floor, so this pin holds both.

The walk's load is its one decision read, `jd.load_goals_shared_or_fault(sid)` in `_auto_nudge_session`, the read ruling
A counted (its wording: every alive session walked wake-only with exactly one load_goals_shared_or_fault and zero plain
load_goals in the decision path). Three witnesses count it. By execution: a recorder stands on `jd.load_goals_shared`, the
one door both of the judge's boundary wrappers reach (`load_goals_shared_or_fault` hands the name to `_or_fault`, which
resolves it from the judge's globals at call time, so every spelling of the shared read arrives at this door), and a
second recorder on `jd.load_goals`, the writer's door. Each records the call with its caller's function, file and line,
stepping over the judge's boundary frames by code identity (never by name) and only while a wrapper's frame sits at its
pass-through call (the line read from the wrapper's source at setUp), so a load written anywhere in a wrapper's body other
than its hand-off line is named for the wrapper in the judge's file, while one written on the hand-off line itself is
named for the kernel caller of that call and counted under that caller's mechanism, the walk's for the look's read and the
gate's for its currency check, or the writer list for a call through load_goals_or_fault (the step-over is line-granular:
review round 2, extra5-1; the walk's ceiling is the line that fires first, since the look's read precedes the gate's on a pass:
the build's verifier pass after the round-2 fixes), and calls through to the real loader, so nothing about the shared cache is stubbed. A call from the look's body or from its gate wrapper (`_nudge_look_gated`'s
inner function, the same mechanism) is the walk's, a call from `_nudge_placement_gate` is the gate's, a call from
`_awaiting_wake_outcomes` is the wake sweep's (the store's third reader on the pass, bounded below), and any other caller
during a pass fails the test, named by function, file and line. The writer door has its own assertion on every pass: the
writer recorder's list must be empty after the tick, each entry named by function, file and line, kept apart from the
shared door's assertion (one filter over both lists would accept a writer-door load whose caller is the walk); that
assertion is _pass's, so the list is empty on every return and the cases read the door's own counter instead, goal_io
loads as `writerLoads`, against the hand-offs each pass expects (review round 2: seven case-level reads of the list could
not fail); a call
through `load_goals_or_fault` is named for its kernel caller, never for the judge's `_or_fault`, and a load written inside
`_or_fault` or either outer wrapper, off its hand-off line, is named for that wrapper (on the hand-off line it is named
for the kernel caller of that call and counted under that caller's mechanism). The claim has three limits. The door: a third loader that reaches the store through the judge's loaders during the pass is caught and named;
a reader below those loaders (the judge's own file reader and parser) is outside the recorders and outside the claim. The
road: the execution witness covers every caller the fixture actually executes; the helpers in REPLACED_KM and REPLACED_JD
and Sessions.backend_for run as stubs, so a loader inside their real bodies is outside the recorders and is caught by the
source census in TheCountersOneSite instead, one level deep (the helper's own source, checked to be the named helper's: a
decorator without functools.wraps would hand the census its wrapper's source), while a loader that would reach a body under
another name, or through a string, is refused where that name is born, by a pin over the kernel's and the judge's whole
source (every loader by attribute the callee of a call; no alias, bare name, parameter or keyword spells one, no string constant
spells a door whole wherever it appears and whatever receives it, and none containing the name reaches a dynamic lookup, a dict read
or a subscript key; a name assembled at run time from pieces none of which spells a door whole is outside every static pin here, a
limit the enumeration holds on its side; the consolidation pass, and the whole-spelling rule since the round-4 fixes), and the census's own forms,
counted and missed, are enumerated in
TheCensusOverEveryForm; setUp checks that it rebinds
exactly the listed names, so the census reads the fixture's list and not a hand-kept copy of it, and the check spans the
whole setUp: its snapshots are setUp's first statements and its comparison the last, and the judge names the rebind moves are
the diff across the rebind call alone, read against a second judge snapshot taken at the rebind, so a stub placed before the
rebind is not filed as the rebind's (the build's verifier pass after the round-2 fixes: read against the first snapshot, a judge
stub between it and the rebind was subtracted and escaped); a stub installed before setUp, or on a judge directory or path name the rebind also moves, is
outside it. The window: each pass, the
`_auto_nudge_tick` call (the records are cleared before it and read after it), so a load elsewhere in the process (a
builder, a handler, the perf snapshot the test reads after its last pass) is outside the window and is not this test's
claim. By the store's own counters, a witness keyed on the store rather than on a list of doors, one per door. The shared
door: every call that reaches the shared cache's branch and returns moves exactly one of hit, miss, compare_miss, absent
and fallback in `jd.shared_store_stats()` (a call whose open or read raises moves none, and reds as a recorded call that
took no read), so per pass the delta of those five must equal the walk's, the gate's and the sweep's recorded calls
together; and the door's second bumps, unreadable_journal, corrupt, dup and refuse (SHARED_SECOND_KEYS), each sit on the fill
road below the miss or compare_miss bump and return, so per pass their sum never exceeds the fills, miss plus compare_miss
(the second-bump bound, ruling 1 of the reviewer's rulings on the pre-emption: corrupt and unreadable_journal are hand-off keys
that are not call keys, so a bump of
either beside a goal_io loads bump with no call through the door balanced the two reconciliations below and red nothing in
_pass). The writer door: every `load_goals` call bumps `loads` in `jd.goal_io_stats()` at the loader's
first line, and the shared door hands a read to `load_goals` on exactly the absent, fallback, corrupt and
unreadable_journal counters (SHARED_HANDOFF_KEYS), so per pass the delta of `loads` must equal the recorded writer calls
plus those hand-offs (the build's verifier pass after the round-1 fixes: until then the writer door was a recorder on one name,
and a `load_goals` through a
reference bound before the recorder stood, or written inside the shared door's own body where the fallback skip takes it
for the hand-off, left every witness green). So a load through a door of this judge module onto its cache or its
counters that the recorders do not wrap, or through a reference to a real door taken before a recorder stood, is noticed
even though it cannot be named. Outside both witnesses: a reader below the judge's loaders or beside its module, the
kernel opening and parsing the store file itself, the kernel calling the judge's own file reader (`jd._read_store_json`,
below the loaders) or a second judge module loaded under another name with a cache and counters of its own (three plants,
each per session in the pass loop, re-taken at this head, the head of the round-3 fixes, over its 20 cases, one at a time with
the kernel, the judge and this module hashed before and after each run: the first two leave every case green with no file changed
across a run, so they stay outside every witness here; the third has been refused since the consolidation pass by the kernel-wide
birth pin, whose called population names `_PJ.load_goals_shared` as a fifth loader spelling, so a second judge module is outside
both execution witnesses and inside the static pin, which reds alone while every execution case stays green; and the alias
control beside them reds the shared reconciliation on every harness case and the birth pin. Review round 3, correctness-2 and
regression-2: this sentence had been written at the head of the build's verifier pass after the round-2 fixes, over that
head's cases, said every case green of all three plants, and went stale as cases and the pin were added, so the count here is pinned by
a Docs case against the loader's count of this module's cases, and the plants are re-taken whenever it moves). The two
witnesses answer different questions: the recorders say
who loaded, the delta says that something did. By the served counter: `memos.nudgeWalk.loads`, bumped at the walk's one call site, must
move by the walk's count per pass. A skipped look repeats its verdict and writes nothing (the wake-only memo of PR 784),
so it needs no data: the recorder sees no call from either.

The gate's load is `_nudge_placement_gate`'s currency check after a derivation (upstream's since the 2026-09-09 fold; ruling
A listed it as open, to be offered upstream, never edited here): at most one call per DERIVED session, none when the gate
is served or the look skipped. A derive whose parse the cache does not hold checks nothing: `derived` is bumped on every
non-raising derivation and the currency read sits under `if parse_key is not None`, so the code's invariant is the bound,
and the equality the cases assert holds here because the harness's parsed_session records every parse in jd._PARSE_CACHE.
So the first pass and a moved-transcript pass derive and the gate loads once per derived session
beside the walk's one; a ledger-driven run pass (the ledger is the tenth keyed file) re-evaluates every look with the gate
served, so the walk loads once and the gate not at all. A look the state gates end before the store read (a working
session's, say) runs, records, and loads through neither.

The wake sweep, `_awaiting_wake_outcomes`, is the store's third reader on the pass. It runs after the per-session loop,
in the same pass and outside the toggle guard, and takes one shared load per wake record it owns: a record that is
wake-set, not failed, moot or answered, not muted, and whose sid the walk did not visit or visited under a wedge gate.
It keeps no memo, so it reads again every pass, and `memos.nudgeWalk.loads` does not count it. The harness holds it to
that bound per sid per pass (`owned_records`, the records the seeding helper gave it): the first cases' ledger holds no
wake record, so the sweep reads nothing there, and TheSweepIsItsOwnBoundedReader drives both of its constituencies: one
record for an unwalked private sid, with one sweep load on each of two passes, once with a store whose nodes lack the goal
and once with no store file, where the shared door falls back into load_goals and that fallback is one logical read of
the shared door's; and one live record for an alive sid whose look the walk leaves on a wedge gate (api-error), where the
walk and the gate load nothing, the sweep loads once per pass and reaches the failure stamp (replaced by a recorder there,
since its real body is a writer).

Two provenances are named in this module, never by one word. The reviewer's rounds carry a number: review round 1 ruled
twelve findings, round 2 fourteen, round 3 nine, and "the round-N fixes" are the changes that answer round N's rulings. The
build's own passes carry a role and never a number: the build's verifier pass after the round-1 fixes, the build's verifier
pass after the round-2 fixes, and the consolidation pass, the build's pass between the round-2 fixes and the reviewer's round
3, in which three lenses read the head, the reviewer ruled on what they found (the reviewer's rulings on the pre-emption,
three rulings, not a round), a fixer applied the rulings, three verifiers read the fixes and a consolidator closed what the
verifiers found.

Red in both directions. For every assertion this module makes, a battery at the head of the build's verifier pass after the
round-2 fixes constructs the state in which that line fails and records the first failing line: each state landed on kernel/kernel.py,
kernel/judge.py, cli/perf_public.py, docs/reference.md or this module and reverted, the module run over its twelve cases
on 3.12 with the caches cleared (three states on 3.11 as well); the figures below are counts from its log. A plant that
reds every harness case reads 5 failed, 7 passed; the two pin cases' probe setUps raise the first guard they meet, so a
setUp plant that changes which guard raises reads 7 failed, 5 passed. setUp: a stand-in left on a door by a peer module
reds the door check (7 failed, 5 passed); two hand-off calls on `_or_fault`'s one hand-off line red the call-count
guard, 2 against 1, where before the round-2 fixes (extra5-2) only the per-mechanism counts red, and the second call on its own
line,
or the `loader` parameter renamed so no call matches, reds the line guard (7 failed, 5 passed each); a kernel stub above
the old snapshot position and a kernel stub inside the seeding helper each red the agreement check naming the stub, and
the judge-stub pin beside the harness cases, whose probe meets that kernel guard before its own (6 failed, 6 passed
each); a judge stub without a list entry and a judge stub between the first snapshot and the rebind (the build's verifier
pass after the round-2 fixes: read against the first snapshot, the rebind's diff filed it as the rebind's and it escaped) each red the check naming
the stub (5 failed, 7 passed each); the backend replacement removed reds the backend assertion (5 failed, 7 passed); a
stub placed through the hook right after the rebind is refused by name, and with the kernel snapshot back at its old
position the hook's stub escapes and that pin case reds (1 failed, 11 passed); a stub placed through the hook before the
rebind is refused by name, and with the rebind's diff read against the first snapshot again it escapes and that pin case
reds (1 failed, 11 passed). _pass: `jd.load_goals_shared` per session in the pass loop reds the unattributed-caller
assertion naming `_auto_nudge_pass` with the kernel's real file and the plant's line (5 failed, 7 passed), the sweep's
read made through a lambda is named for the lambda there (3 failed, 9 passed), and with the boundary set emptied every
pass with a load is named `_or_fault` there (3 failed, 9 passed); a load per walked sid at the top of
`_awaiting_wake_outcomes` reds the sweep's bound, 1 against 0 owned records and 2 against 1 in the wedge case (5 failed,
7 passed), the sweep's read duplicated reds it at 2 against 1 in the three sweep cases, and a foreign-sid load from the
sweep reds it by sid, the message naming the sweep's records for that sid by function, file and line (3 failed, 9 passed
each); a foreign-sid load above the gate's currency read reds the foreign assertion naming `_nudge_placement_gate` (3
failed, 9 passed), and above the walk's read naming `_auto_nudge_session`, with the census (4 failed, 8 passed); a read
by the look of the OTHER pass session passes the foreign assertion and reds the walk's ceiling, which names the sid and
the mechanism, with the census (4 failed, 8 passed); a shared read in the gated look before it consults the memo reds
the walk's ceiling at the first pass, 2 against 1 per session, with the two cases that pin zeros and the gate wrapper's
census (6 failed, 6 passed); a second shared load written on `_or_fault`'s hand-off line, taken by the look's call and
the gate's, reds the walk's ceiling first (3 failed, 9 passed); the currency read duplicated after the derive count reds
the gate's ceiling, 2 against 1 (3 failed, 9 passed); a currency read on the served path reds the general bound alone, 2
checks against 0 derives (1 failed, 11 passed); a derive counted in the skip branch reds the equality at the first
skipping pass, 0 against 2 (4 failed, 8 passed), as do the currency read dropped and the fixture's parse left out of
jd._PARSE_CACHE (3 failed, 9 passed each; at the head before the ceilings moved, those two red the first pass's gate
assertion); a reference to the real shared door bound at kernel import and called per session in the pass loop reds the
shared reconciliation, the counters two over the recorded calls (5 failed, 7 passed; the consolidation pass: and the birth pin, 6
failed, 11 passed of 17, below), a shared counter moved with no
recorded call reds it on every pass, one over (5 failed, 7 passed), the door's hit bump dropped reds it the other way (4
failed, 8 passed), and a phantom record appended by the recorder reds the ceilings ahead of it (4 failed, 8 passed);
`jd.load_goals` per session in the pass loop reds the writer assertion naming `_auto_nudge_pass` (5 failed, 7 passed),
and with the writer recorder's code-identity skip removed the no-store sweep case reds there naming `load_goals_shared`
in the judge's file (1 failed, 11 passed); the same import-time alias to the writer door reds the writer reconciliation,
loads two over the hand-offs (5 failed, 7 passed), as does `load_goals(fsid)` at the top of the shared door's cache
branch (4 failed, 8 passed). The first case, one state per assertion: the looks bump removed (3 failed, 9 passed); every
look ending at the working gate, its test replaced by a constant true, the first pass's walk {0, 0} against {1, 1} (3
failed, 9 passed; the build's verifier pass after the round-2 fixes: the battery had folded this line into the walk ceiling's
state, whose plant reds the ceiling first); a duplicate bump statement, 4 against 2 on the counter and 2 against 1 in the census (3 failed, 9 passed
each); a served bump beside the derive, memo (2, 2) against (0, 2) (2 failed, 10 passed); the shared cache switched off
after setUp, writerLoads 4 against 0 (1 failed, 11 passed); SID_A's store read once before the first pass, the counters
{hit 3, miss 1} against {hit 2, miss 2} (1 failed, 11 passed); the memo row never recorded (4 failed, 8 passed); the
skip's early return dropped, the skip pass's walk at 1 per session (3 failed, 9 passed); the gate called from the skip
path on a copy of the memo's store, the skip pass's gate at 1 per session (a contrived plant; 3 failed, 9 passed); the
skippedParses bump removed (2 failed, 10 passed); a loads bump in the skip branch, 2 on the skip pass (3 failed, 9
passed); the ledger dropped from the ten keyed files, so its move re-evaluates nothing (2 failed, 10 passed); the walk
reusing a stale per-sid snapshot, the run pass's walk at 0 (2 failed, 10 passed, the census's adjacency the other); the
gate memo cleared before the run pass, so it derives (1 failed, 11 passed); a loads bump on the served path, 4 against 2
(1 failed, 11 passed); the cache switched off before the run pass, so the gate cannot be served and derives (1 failed,
11 passed); the ledger touched again before the second skip pass, so it runs (1 failed, 11 passed); a loads bump in the
skip branch conditioned on four parses, so the second skip pass alone (a contrived plant; 2 failed, 10 passed); the
transcript dropped from the ten keyed files, so the moved transcript skips (1 failed, 11 passed); the working gate
answering true before the moved-transcript pass, its walk at 0 (1 failed, 11 passed); the parse-key term dropped from
the gate memo's hit test, so it serves the moved parse (1 failed, 11 passed); SID_A's store re-seeded before that pass,
a miss in place of a hit, and the cache switched off before it, two fallbacks and two hand-offs (1 failed, 11 passed
each); a send in the look (3 failed, 9 passed); the served snapshot handing out zero loads, 0 against 5, the counter
preset to 100 after setUp, 105 against 5, the bump adding a float, and `loads` denied in the public fold (1 failed, 11
passed each). Four case-level tuples carried the writer door's counter and the store's call counters beside the walk's
counter, on the two skip passes, the run pass and the state-gate case's first pass; the build's verifier pass after the round-2
fixes reduced them to the walk's counter alone, reasoning that a counter moved with no recorded call reds _pass's reconciliation
first and that on the run pass a non-hit makes the gate derive and its line fire first. The gap that narrowing left on the run
pass is forged-only: a genuine writer-door load on that pass is named by _pass's writer assertion and a genuine shared load by
its recorders, so only a counter moved with no call through the door, the forged pair, could reach the case level. That was
established and not assumed: the run pass was found to be the single pass taking shared loads whose tuple carried no
writerLoads element (the first pass and the moved-transcript pass kept theirs), and the pair was then planted ahead of it, in
_closer_settled and after the walk's read on a served look, to test whether it reached that line, rather than reasoning from the
reconciliations that nothing could; it did, writerLoads 2 against 0 with the bound disabled (the states below). The
consolidation pass's tuple-elements lens found that reasoning true of the call keys only: a corrupt or unreadable_journal bump beside a goal_io loads bump with no
call through the door (a hand-off key that is not a call key) balanced both reconciliations, and at that head red nothing on
the pass it was planted, only the moved-transcript tuple two passes later or nothing at all. Ruling 1 of the reviewer's rulings
on the pre-emption restored the writer door's counter and the store's counters to the first skip pass, the run pass and the
state-gate case's first pass (the second skip pass's tuple stays on the walk's counter and its skipped count) and added the
second-bump bound to _pass, where the pair reds on its own pass; the consolidation then gave the state-gate case's third pass,
a skip pass, the same two elements, so every skip pass a pair can land on has both layers. The states re-run at the head of the
consolidation pass are recorded below. The state-gate case: the working gate moved below the store
read (1 failed, 11 passed); a served bump in the working branch (contrived; 1 failed, 11 passed); the loads bump moved
above the working gate (2 failed, 10 passed, the census the other); the verdict renamed (1 failed, 11 passed);
`_put_walk_gate` made a no-op, so the second pass skips (2 failed, 10 passed); a read conditioned on a memo row standing
(contrived; 3 failed, 9 passed; ruling 2 of the reviewer's rulings on the pre-emption dropped the second-pass tuple that was one
of the three, below); a read in the
skip branch (5 failed, 7 passed). The sweep cases: the sweep's ownership
inverted (3 failed, 9 passed); the recorder using the bare basename, the sweep's read filed under `romp-kernel` (3
failed, 9 passed); SID_C's store deleted in the store case and written in the no-store case, the hand-off count 1
against 0 and 0 against 1 (1 failed, 11 passed each); SID_C's store read before the first pass, and the cache cleared
between the passes (1 failed, 11 passed each); a send in the sweep (3 failed, 9 passed); SID_A's store read before the
no-store case's first pass, and the ledger touched between its passes (1 failed, 11 passed each); the api-error gate
moved below the parse, the wedge clause dropped, the cache switched off in the wedge case, the sweep's parse skipped,
SID_A's store read before its first pass, the cache cleared between its passes, the failure stamp skipped and SID_B's
walk gate popped (1 failed, 11 passed each), and a read in the api-error branch, with the census (2 failed, 10 passed).
The censuses: a second read above the walk's own, 2 sites against 1 with the walk's ceiling (4 failed, 8 passed); the
bump moved one line off the load (1 failed, 11 passed); a call in the gate wrapper (6 failed, 6 passed); `loads` popped
from the served block (1 failed, 11 passed); a name added to REPLACED_KM, 22 targets against 21 with setUp's check (7
failed, 5 passed); `jd.load_goals_shared_or_fault` as the first statement of the real `_closer_settled`, and the same
call inside an f-string on 3.11 (1 failed, 11 passed each; 8 passed on 3.11 at the head before the AST census); the
loader imported under an alias there, on 3.12 and on 3.11 (1 failed, 11 passed each; the build's verifier pass after the
round-2 fixes: 11 passed each before the census read ast.alias); the census reverted to raw lines, the prose sample counting sites (1 failed, 11
passed), attributes ignored, one call counting none (2 failed, 10 passed), and aliases ignored, the import sample
counting none (1 failed, 11 passed); the old tokenize census with the f-string sample on 3.11 (1 failed, 11 passed); a
comment quoting the bump, and a docstring mention in the gate wrapper, green (12 passed each). The recorder: the
step-over made unconditional, the in-body call named for the test method (1 failed, 11 passed); `_or_fault` rebound to a
functools.partial, setUp erroring with inspect's TypeError (7 failed, 5 passed; the loud failure, not an assertion). The
reference: the class word, a writer's name, the dead-man's bound, `_dead_wait_block`'s callers, the first-two needle and
the toggle needle dropped from the jobs block, each of the walk entry's four needles and its pointer dropped, this
module's pointer dropped, and the gloss phrase changed (1 failed, 11 passed each). The assertion texts name the
mechanism and are in the commit messages.

The consolidation pass (2026-09-19, between the round-2 fixes and the reviewer's round 3). The record above is the battery of
the build's verifier pass after the round-2 fixes, over the twelve cases of that head; the consolidation pass's head has
seventeen (the second-bump roster pin, the kernel-and-judge birth pin and the three enumeration cases are new), so a figure
in this paragraph reads against 17. Three lenses read the head, the reviewer ruled on what they found (the reviewer's rulings
on the pre-emption, three rulings, not a round), three verifiers read the rulings' fixes, and the consolidation closed what
the verifiers found (the state-gate case's third-pass tuple carries the writer door's
and the store's counters; the birth pin reads a subscript's slice and a dict read's arguments, with the string limit split into
what it refuses and what stays outside it; three texts). Every state below was re-run at the head of the consolidation pass,
the head of those closures, each
plant landed on kernel/kernel.py, kernel/judge.py or this module and reverted, the module run single-process on 3.12; the
figures are counts from those logs. The tuple-elements lens, the forged pair (a corrupt or unreadable_journal
bump beside a goal_io loads bump, no call through the door): in the kernel's skip branch it reds the second-bump bound in
_pass at the first skip pass of the first case, of the two unwalked-sid sweep cases and of the state-gate case, its third
(4 failed, 13 passed; at the head before the bound the moved-transcript tuple two passes later, 3 failed, 9 passed of 12);
in _wait_for_graph before the first skip pass, and in _closer_settled before the run pass, the bound at that pass (1 failed,
16 passed each; 12 passed before); in the kernel's working branch before the state-gate case's first pass, the bound at that
pass (1 failed, 16 passed; 12 passed before); after the walk's read on a look whose gate is served, the bound at the run pass
(1 failed, 16 passed; the moved-transcript tuple before); a dup or a refuse bump in place of the corrupt bump reds the bound
the same way (4 failed, 13 passed). The elements behind the bound, each shown with the bound disabled: the skip-branch pair reds
the restored first-skip-pass tuple and the state-gate case's third-pass tuple, writerLoads 2 against 0 each, with the two
unwalked-sid sweep cases' hand-off lines (4 failed, 13 passed; 3 failed, 14 passed before the third-pass tuple carried the
elements), and with those two elements dropped again that pass is green under the same pair (3 failed, 14 passed) while the
drop alone leaves the module green (17 passed); the pair in _closer_settled before the run pass, and the pair after the walk's
read on a served look, each red the restored run-pass tuple, writerLoads 2 against 0 (1 failed, 16 passed each); the pair in the
kernel's working branch reds the restored state-gate first-pass tuple, writerLoads 2 against 0 (1 failed, 16 passed); the pair
in _wait_for_graph reds the first-skip-pass tuple, writerLoads 1 against 0 (1 failed, 16 passed). The shared elements of those
tuples have no state of their own: a call key cannot move without a call, which the shared reconciliation reds first, and on
the run pass a non-hit derives the gate, whose line fires first. The pair beside a fill: one corrupt bump and one loads bump
after each miss the walk's read made leaves second equal to fills and passes the bound, and the first pass's writerLoads line
reds it, 2 against 0, with the two unwalked-sid sweep cases' hand-off lines (3 failed, 14 passed); two pairs per miss red the
bound, 4 against 2 (3 failed, 14 passed). The bound's own weakening: the comprehension with corrupt filtered out, and the
assertion disabled, each leave the clean module green (17 passed each), since an assertion's own weakening is shown by the
plants above and by nothing in the module; the roster pin reads the door's source and the constant, not the comprehension. The
roster pin: refuse dropped from SHARED_SECOND_KEYS, and a poisoned bump added to the door's fallback
branch, each red the roster (1 failed, 16 passed each); a refuse bump placed above every call-key bump reds the order (1
failed, 16 passed). The replay lens, the re-arming: a memo row recorded only when none stood, and one re-recorded under the
standing row's key, each red the first case's fourth pass (walk 1 against 0 per session) and the state-gate case's third
(skippedParses 0 against 2) with every pass before them green (2 failed, 15 passed each); the walk gate's write-on-change
dropped reds the state-gate case's third pass alone (1 failed, 16 passed); `_put_walk_gate` made a no-op reds its
second-pass re-evaluation line and the wedge sweep case (2 failed, 15 passed); the read conditioned on a memo row, whose one
red in the state-gate case was the dropped second-pass tuple, reds the first case's walk ceiling at the run pass and the walk
census (2 failed, 15 passed). Five earlier states of those roads red what they did: the skip's early return dropped and the
gate called from the skip path (3 failed, 14 passed each), the loads bump conditioned on four parses (2 failed, 15 passed),
the working gate moved below the read and the served bump in the working branch (1 failed, 16 passed each). The census lens,
the three limits: `_closer_settled` decorated without functools.wraps with a shared load in its real body reds the identity
check naming the wrapper (1 failed, 16 passed; 12 passed before the check, the census reading the wrapper's three lines);
the gate decorator's wraps dropped reds the walk census's site count, 0 against 1, a true red with a false cause (1 failed,
16 passed; that census carries no identity line). The birth pin: the shared door bound to a kernel module-level name at
import and never called, `getattr` with the door's name at kernel module level, and the door imported under an alias there
each red the pin naming the line and the form (1 failed, 16 passed each; the first was 12 passed before the pin); in the
judge, a module-level alias of the door below its definition, and the door passed to `map` rather than to `_or_fault`, each
red it as a bare name outside a call (1 failed, 16 passed each). The battery's two import-time aliases, each called per
session in the pass loop, red their reconciliation on every pass and the pin (6 failed, 11 passed each). The widened pin
(a consolidation-pass verifier's finding: the first cut read a dynamic lookup's arguments alone): `vars(jd)[...]`, `jd.__dict__[...]`
and `jd.__dict__.get(...)` spelled with the shared door, each at kernel module level and each as a real load inside
`_closer_settled`, red the pin naming the line and the form (1 failed, 16 passed each; 17 passed before the widening); the
name bound to a variable before the getattr, and a concatenation that splits the needle, leave the module green (17 passed
each), the assembled limit stated as such. The enumeration's births check: the subscript branch dropped reds it at F30, and
with the `vars(jd)[...]` plant landed beside that drop the pin stays green and the enumeration alone reds (1 failed, 16
passed each); the dict-read roster emptied, and the call test over the dynamic lookups alone, each red it at F30d (1 failed,
16 passed each); every loader-naming string constant read as a birth reds the kernel pin on its docstrings and the enumeration
at F07d, the name bound first (2 failed, 15 passed). The enumeration:
the census with its alias kind dropped reds the alias sample and the loader forms at F03, the from-import with as (2 failed,
15 passed); with its Attribute kind dropped, the walk census, the sample case, the bump forms at B01 and the loader forms at
F02 (4 failed, 13 passed); with its Name kind dropped, the loader forms at F01 (1 failed, 16 passed); reading string
constants as spellings, the prose sample and the loader forms at F07 (2 failed, 15 passed); reading getattr's string
argument as a spelling, the via_getattr sample and F07 (2 failed, 15 passed); the bump scan without its operator check, the
bump forms at B08, `-= -1` (1 failed, 16 passed); the hand-off count taken from the lines, the hand-off forms at P04, two
calls on one line (1 failed, 16 passed). The clean module: 17 passed single-process on 3.10, 3.11, 3.12, 3.13 and 3.14t.

Review round 3 (2026-09-19; nine findings, all low, and the reviewer's version demand restated for the AST readers). Each state
below was landed on kernel/kernel.py, kernel/judge.py or this module and reverted, the module run single-process on 3.12 through
the clean runner unless another interpreter is named; a figure names the case count it reads against, since the round's fixes
add cases. The bare-name sample (extra5-1): the census's Name branch dropped reds the sample case, naming the bare form, and the
enumeration at F01, the bare from-import's call (2 failed, 15 passed of 17); a bare-name shared load as the first statement of
the real jd._segs reds the replaced-helpers census naming jd._segs and the planted line (1 failed, 16 passed of 17); the same
plant with the Name branch dropped escapes that census and is caught by the sample case and the enumeration alone (2 failed, 15
passed of 17), the state that read 12 passed at the head of the build's verifier pass after the round-2 fixes. The grammar table
(the version demand): Call removed from _AST_CONCRETE reds the interpreter check naming Call and every census, the harness's
setUp among them, since _walk refuses the first Call it meets (18 failed, 1 passed of 19); TypeIgnore removed, a class no parse
here produces, reds the interpreter check alone, naming it (1 failed, 18 passed); a fake node class planted into the ast module
at import reds the interpreter check naming Frobnicate (1 failed, 18 passed); _walk passing an unknown node instead of raising
reds the refusal case, AssertionError not raised (1 failed, 18 passed); a census walking a tree outside _walk reds the refusal
case's source pin, 2 spellings against 1 (1 failed, 18 passed); on 3.14t, TemplateStr and Interpolation removed red the
interpreter check naming both and the enumeration at F61, where _walk refuses the TemplateStr (2 failed, 17 passed). The clean
module with the table: 19 passed single-process on 3.10, 3.11, 3.12, 3.13 and 3.14t, and with four workers on 3.12. The bypass
plants (correctness-2, regression-2), re-taken at this head of 20 cases, each landed on the kernel alone, run single-process on
3.12 and reverted with the kernel, the judge and this module hashed before and after: the kernel opening and parsing the store
file itself, and the kernel calling jd._read_store_json, each per session in the pass loop, 20 passed each and no file changed
across a run; a second judge module loaded under another name, rebound to the state and its shared door called per session,
reds the kernel-wide birth pin alone, naming `_PJ.load_goals_shared` as a fifth loader spelling (1 failed, 19 passed; every case
green at both earlier heads, before the pin); the alias control, the shared door bound at kernel import
and called per session, 6 failed, 14 passed, the shared reconciliation on every harness case and the birth pin; and the count
pin: the sentence's count set to a stale figure reds the Docs case naming both figures (1 failed, 19 passed).

Drives the real pass (_auto_nudge_tick) over two alive sessions with real transcript files and real goal stores, on the
suite's fake clock (the pass takes `now`). SYNTHETIC fixtures only; a PRIVATE synthetic sid pair (the goal-store fixture
rule), their override journals cleaned in the teardown; the state root rebound through jd._rebind_state and `off` written
into its session-hosts."""
import ast
import contextlib
import importlib.util
import inspect
import io
import json
import os
import re
import sys
import tempfile
import textwrap
import types
import unittest
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads: they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_c7pin", os.path.join(BIN, "romp-kernel"))
jd = km.jd                                        # the kernel's OWN judge instance: the recorder must land where the walk reads it
pp = load_source("romp_perf_public", os.path.join(os.path.dirname(HERE), "cli", "perf_public.py"))   # the export's public fold

SID_A = "c7c0a001-5e55-4a11-8b22-000000000001"   # private to this module (the goal-store fixture rule): a plain working top
SID_B = "c7c0a001-5e55-4a11-8b22-000000000002"   # a stamped top whose dead-man is an hour away (the wake-only branch's other road)
SID_C = "c7c0a001-5e55-4a11-8b22-000000000003"   # never alive, so never walked: the sid of the wake record the sweep owns
SIDS = (SID_A, SID_B)
NOW = 1_787_900_000
H = 3600
WALK = ("_auto_nudge_session", "gated")   # the walk's look: its body and its gate wrapper (_nudge_look_gated's inner function)
GATE = ("_nudge_placement_gate",)         # the placement gate's post-derivation currency check: a second loader, counted apart
SWEEP = ("_awaiting_wake_outcomes",)      # the wake sweep after the per-session loop: a third reader, one shared load per wake record it owns
# The shared cache's per-call counters: load_goals_shared bumps exactly one of these per call that reaches the cache's branch
# (judge.py, the door's body). Not summed: unreadable_journal, corrupt, dup and refuse are second bumps on a fill; evict and
# poisoned are not calls; entries, bytes and off are gauges.
SHARED_CALL_KEYS = ("hit", "miss", "compare_miss", "absent", "fallback")
# The shared door's hand-offs into load_goals: the four counters load_goals_shared bumps right before it returns load_goals(fsid)
# (judge.py, the door's body: the cache off, no store file, an unreadable journal, bytes that did not parse). Each hand-off is one
# load_goals call and so one bump of `loads` in jd.goal_io_stats(), the writer door's own counter, which the writer reconciliation
# in _pass reads. The door's _unread branch bumps unreadable_journal with no hand-off; the door's own comment calls it unreachable
# while the journal's rows arrive as lines, and reached it would red that reconciliation as a hand-off over the loads.
SHARED_HANDOFF_KEYS = ("absent", "fallback", "corrupt", "unreadable_journal")
# The door's second bumps, read from load_goals_shared's body (judge.py): below the call-key bumps the fill road, entered after the
# miss or compare_miss bump, bumps at most one of these and returns. unreadable_journal: _journal_read raised OSError (a hand-off to
# load_goals), or the replayed store carries _unread (no hand-off; the door's comment calls that branch unreachable). corrupt:
# _disk_parse raised ValueError (a hand-off). dup: a concurrent fill of the same version published first. refuse: the archive key
# moved under the replay. The fallback, absent and hit returns bump none of them, so per pass their sum never exceeds the fills,
# the call keys whose bump falls through into the fill road (SHARED_FILL_KEYS below, miss and compare_miss): _pass's second-bump
# bound (ruling 1 of the reviewer's rulings on the pre-emption). The bound rests on three premises about the body, each pinned
# against the door's own source by the roster pin in TheCountersOneSite and by nothing here: the keys the door bumps are the two
# rosters exactly; every second-key bump sits below every call-key bump; and a call bumps AT MOST ONE second key, since the
# innermost statement list holding each second-key bump holds no other and ends in a return or a raise (review round 4, tests-2,
# regression-2 and extra4-1: the pin read the first two, and the third was held by reading the body). The third is pinned by
# execution as well: a store whose bytes do not parse, read once through the door, bumps miss once, corrupt once and hands off
# once (TheDoorBumpsAtMostOneSecondKeyPerCall). Two of them, corrupt
# and unreadable_journal, are hand-off
# keys that are NOT call keys, so a bump of either beside a goal_io loads bump with no call through the door balanced the shared
# reconciliation (no call key moved) and the writer one (one hand-off per loads) and red nothing in _pass; the bound is where it
# reds on a pass with no fill, and the cases' writerLoads elements where one such pair rides beside each fill (the bound admits
# second == fills). The other two, dup and refuse, are neither call keys nor hand-off keys, so a bump of either moves no
# reconciliation and the bound admits it up to the fills; _pass holds them to zero on every pass, with the reason zero holds in this
# harness (review round 4, extra5-1: a spurious bump of either beside a genuine fill was witnessed by nothing).
SHARED_SECOND_KEYS = ("unreadable_journal", "corrupt", "dup", "refuse")
# The fill road's entry keys: the call keys whose bump falls through into the fill (the statement list holding it does not end in
# a return or a raise), so the fills a pass made are their sum, the bound's right-hand side in _pass. The roster pin derives them
# from the door's AST and asserts them equal to this tuple, so a call key that starts falling through, or one of these that stops,
# reds there (review round 4, tests-2: _pass named the two by hand, and a new fill key left the module green with the bound summing
# the wrong keys).
SHARED_FILL_KEYS = ("miss", "compare_miss")
KERNEL_FILE = os.path.basename(os.path.realpath(km.__file__))   # the kernel's real file: it is loaded from bin/romp-kernel, a symlink
# The callables the fixture replaces, other than the two recorded doors: the kernel names (the look's gates and the pass's
# helpers; _pending_ops and _PREV_ALIVE are data, not callables), the judge names, and Sessions.backend_for (replaced by
# setUp beside them). Their real bodies never run under the fixture, so the source census in TheCountersOneSite is the only
# witness for a loader inside them. _session_working is not in the list: its real body runs (the event model reads the
# fixture turns, both ended, as not working, the answer the stub gave), and the state-gate case replaces it for its own world.
# CASE_KM: names a CASE may replace after setUp for its own world, saved with the rest and restored by the cleanup; setUp
# leaves them real (the agreement check there). The two writers are the wedge-gate sweep case's: their real bodies load
# through the writer door at their write moments by design (the reference's jobs block names them among the store's other
# readers), so the census has nothing to say about them.
CASE_KM = ("_session_working", "_mark_nudge_failed", "_file_wake_answer")
REPLACED_KM = ("_alive_sessions", "_wait_for_graph", "_session_flag", "_compacting_now", "_api_error",
               "_interrupt_suppresses_nudge", "_backend_rewind_pending", "_last_state",
               "_session_awaiting", "_turn_romp_injected", "_closer_settled", "_revivers_pending",
               "_pending_ops", "_log_nudge_event", "_push_all", "_mark_views_dirty", "_path_of",
               "_debt_backstop_tick", "_PREV_ALIVE")
REPLACED_DATA = ("_pending_ops", "_PREV_ALIVE")
REPLACED_JD = ("parsed_session", "_segs", "plan_units")
JUDGE_FILE = os.path.basename(os.path.realpath(jd.__file__))
_UNSET = object()

# The grammar the census walkers read. The reviewer's version demand (review round 2, correctness-1: a census that cannot scan an
# interpreter must fail loudly there, never scan less and pass), restated after round 3 for the AST readers: a walker that meets a
# node it does not classify must fail naming the class, since a reader that cannot parse must not report absent. So every concrete
# node class of Python's ast grammar on 3.10 through 3.14 is listed here by name with the version that adds it (None: all five),
# _walk refuses a node of any other class, and TheGrammarIsTheOneTheWalkersClassify checks at test time that the running
# interpreter defines no node class outside the three rosters, so a grammar that gains a node form reds naming the new class
# instead of scanning less. The classification itself is the walkers': _loader_sites reads Name, Attribute and alias as sites and
# every other class here as no site; _bump_sites reads AugAssign and its target; _pass_through_lines reads Call; _loader_births
# reads Attribute, Name, alias, arg, keyword, the two def classes, Subscript, Call and Constant; a class outside this table is classified by
# none of them and is refused before any of them answers.
_AST_CONCRETE = {
    # mod
    "Module": None, "Interactive": None, "Expression": None, "FunctionType": None,
    # stmt
    "FunctionDef": None, "AsyncFunctionDef": None, "ClassDef": None, "Return": None, "Delete": None, "Assign": None,
    "TypeAlias": (3, 12), "AugAssign": None, "AnnAssign": None, "For": None, "AsyncFor": None, "While": None, "If": None,
    "With": None, "AsyncWith": None, "Match": None, "Raise": None, "Try": None, "TryStar": (3, 11), "Assert": None,
    "Import": None, "ImportFrom": None, "Global": None, "Nonlocal": None, "Expr": None, "Pass": None, "Break": None,
    "Continue": None,
    # expr
    "BoolOp": None, "NamedExpr": None, "BinOp": None, "UnaryOp": None, "Lambda": None, "IfExp": None, "Dict": None, "Set": None,
    "ListComp": None, "SetComp": None, "DictComp": None, "GeneratorExp": None, "Await": None, "Yield": None, "YieldFrom": None,
    "Compare": None, "Call": None, "FormattedValue": None, "Interpolation": (3, 14), "JoinedStr": None, "TemplateStr": (3, 14),
    "Constant": None, "Attribute": None, "Subscript": None, "Starred": None, "Name": None, "List": None, "Tuple": None,
    "Slice": None,
    # expr_context, boolop, operator, unaryop, cmpop
    "Load": None, "Store": None, "Del": None,
    "And": None, "Or": None,
    "Add": None, "Sub": None, "Mult": None, "MatMult": None, "Div": None, "Mod": None, "Pow": None, "LShift": None,
    "RShift": None, "BitOr": None, "BitXor": None, "BitAnd": None, "FloorDiv": None,
    "Invert": None, "Not": None, "UAdd": None, "USub": None,
    "Eq": None, "NotEq": None, "Lt": None, "LtE": None, "Gt": None, "GtE": None, "Is": None, "IsNot": None, "In": None,
    "NotIn": None,
    # the product types
    "comprehension": None, "ExceptHandler": None, "arguments": None, "arg": None, "keyword": None, "alias": None,
    "withitem": None, "match_case": None,
    # pattern
    "MatchValue": None, "MatchSingleton": None, "MatchSequence": None, "MatchMapping": None, "MatchClass": None,
    "MatchStar": None, "MatchAs": None, "MatchOr": None,
    # type_ignore, type_param
    "TypeIgnore": None, "TypeVar": (3, 12), "ParamSpec": (3, 12), "TypeVarTuple": (3, 12),
}
# The grammar's sum types, which the parser never instantiates: every node is an instance of a concrete subclass of one of these
# or derives from AST itself (the product types); the version that adds one, as above.
_AST_ABSTRACT = {"mod": None, "stmt": None, "expr": None, "expr_context": None, "boolop": None, "operator": None, "unaryop": None,
                 "cmpop": None, "excepthandler": None, "type_ignore": None, "pattern": None, "type_param": (3, 12), "slice": None}
# Classes the ast module keeps for compatibility that no parse produces: the constant classes of the grammar before 3.8 (module
# attributes on 3.10 and 3.11, a private stand-in for Ellipsis on 3.12 and 3.13, gone on 3.14), the slice classes of the grammar
# before 3.9 under their sum type, the two unused contexts, Param and Suite.
_AST_COMPAT = frozenset(("Num", "Str", "Bytes", "NameConstant", "Ellipsis", "_ast_Ellipsis", "Index", "ExtSlice",
                         "AugLoad", "AugStore", "Param", "Suite"))
_AST_KNOWN = frozenset(getattr(ast, n) for n in _AST_CONCRETE if isinstance(getattr(ast, n, None), type))   # the classes, by identity


def _walk(tree):
    """ast.walk over `tree`, refusing a node whose class is not one of the grammar classes in _AST_CONCRETE, by name: the
    reviewer's version demand for the AST readers. A census that passed over such a node would scan less and report a shorter
    list, a site absent where it could not read; this raises instead, before any census answers, and the failure names the class
    it met. The class is matched by identity against the ast module's own, so a stranger of a known name is refused too."""
    for node in ast.walk(tree):
        if type(node) not in _AST_KNOWN:
            raise AssertionError("a node of class %s, which the census walkers of this module do not classify (not in _AST_CONCRETE, "
                                 "or not the ast module's own class of that name): a reader that cannot classify a node must fail "
                                 "naming it rather than scan less and report a site absent; list the class in _AST_CONCRETE with the "
                                 "version that adds it and say in the table's comment how each walker reads it" % type(node).__name__)
        yield node


# The ast module's four traversal names, assembled at run time so this module's text spells none of them where the walker pin
# reads it (the pin is structural and a literal here would be no reference, but the names are kept out of the text all the same):
# every reference to one of them, in any form, must sit inside _walk (TheGrammarIsTheOneTheWalkersClassify).
_TRAVERSAL = tuple("".join(p) for p in (("wal", "k"), ("iter_child", "_nodes"), ("Node", "Visitor"), ("Node", "Transformer")))
_WALK, _ITER_CHILD_NODES, _NODE_VISITOR, _NODE_TRANSFORMER = _TRAVERSAL
# Every reference to a traversal name outside _walk, keyed (enclosing def, name) with the reason it walks nothing around _walk. The
# pin asserts each row is used (a stale row reds) and that nothing else refers to one; a new legitimate reference gets a row here.
_WALK_EXEMPT = {
    ("_loader_births", _ITER_CHILD_NODES):
        "lists a node's direct children to build the parent map and traverses nothing: every child is yielded by _walk on the next "
        "level, where it is classified or refused",
    ("TheGrammarIsTheOneTheWalkersClassify.test_a_walker_refuses_a_node_it_does_not_classify_by_name", _WALK):
        "the control the refusal case compares _walk against, over a tree of grammar nodes only",
}


def _traversal_references(tree):
    """Every reference in `tree` to one of the ast module's traversal names (_TRAVERSAL), as sorted (line, name, form, spelling,
    owner) tuples, in four forms: `attribute`, an Attribute of the ast module or of any name it is imported under (`ast.walk`,
    `_a.walk` after `import ast as _a`; a NodeVisitor or NodeTransformer base is spelled this way too); `from-import`, `from ast
    import walk`, with or without `as`, and `from ast import *`, a reference to every name, reported as `*`; and `getattr`, a
    getattr on the module with a string constant. `owner` is the enclosing top-level def, `Class.method` for a method, `Class`
    for a class body, `<module>` otherwise, found by walking each module-body def's subtree (through _walk, as every reader here
    walks). Outside these forms: a name assembled at run time or read from vars(ast) or ast.__dict__."""
    aliases = {a.asname or a.name for n in _walk(tree) if isinstance(n, ast.Import) for a in n.names if a.name == "ast"}
    owners = {}
    for stmt in tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for n in _walk(stmt):
                owners[id(n)] = stmt.name
        elif isinstance(stmt, ast.ClassDef):
            for n in _walk(stmt):
                owners[id(n)] = stmt.name
            for item in stmt.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for n in _walk(item):
                        owners[id(n)] = stmt.name + "." + item.name
    out = []
    for n in _walk(tree):
        owner = owners.get(id(n), "<module>")
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id in aliases and n.attr in _TRAVERSAL:
            out.append((n.lineno, n.attr, "attribute", "%s.%s" % (n.value.id, n.attr), owner))
        elif isinstance(n, ast.ImportFrom) and n.module == "ast":
            for a in n.names:
                if a.name in _TRAVERSAL or a.name == "*":
                    out.append((n.lineno, a.name, "from-import", "from ast import %s%s" % (a.name, " as " + a.asname if a.asname else ""), owner))
        elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "getattr" and len(n.args) >= 2
              and isinstance(n.args[0], ast.Name) and n.args[0].id in aliases and isinstance(n.args[1], ast.Constant)
              and n.args[1].value in _TRAVERSAL):
            out.append((n.lineno, n.args[1].value, "getattr", "getattr(%s, %r)" % (n.args[0].id, n.args[1].value), owner))
    return sorted(out)


def _pass_through_lines(fn, callee):
    """(lines, calls): the line numbers, in `fn`'s file, of its calls to `callee`, and how many such calls there are. The calls
    are the boundary wrapper's hand-off of the read (`loader(fsid)` in _or_fault, `_or_fault(...)` in the two outer wrappers),
    read from the source by the AST so a docstring or a comment naming the callee is not one. The lines are absolute (inspect
    gives the source with its first line's number) and are what _caller steps over at; the count is the guard's (review round
    2, extra5-2: two hand-off calls written on one line are one line and were passed by a guard whose message said one call)."""
    src, start = inspect.getsourcelines(fn)
    tree = ast.parse(textwrap.dedent("".join(src)))
    calls = [node for node in _walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == callee]
    return frozenset(start - 1 + node.lineno for node in calls), len(calls)


def _spelled(node):
    """The dotted spelling of an Attribute chain (`jd.load_goals_shared_or_fault`; a base that is not a Name is spelled `...`)
    or a Name's id: the text _loader_sites and _loader_births match a needle against."""
    if isinstance(node, ast.Name):
        return node.id
    parts, v = [node.attr], node.value
    while isinstance(v, ast.Attribute):
        parts.append(v.attr)
        v = v.value
    parts.append(v.id if isinstance(v, ast.Name) else "...")
    return ".".join(reversed(parts))


def _loader_sites(obj, needle):
    """Every place `obj`'s source names a loader whose spelling contains `needle`, read from the AST: (index, line) pairs, one
    per node, indexed as inspect.getsource(obj).splitlines() is, so a census can check adjacency against a line index. A site
    is an ast.Name whose id contains the needle, an ast.Attribute whose dotted spelling (the value chain and the attribute,
    `jd.load_goals_shared_or_fault`) contains it, or an ast.alias whose imported name contains it (`from romp_judge import
    load_goals_shared as _lgs`: the import line is the site, and the alias's later uses, Names of another spelling, are not;
    the build's verifier pass after the round-2 fixes: over Name and Attribute alone, a loader imported under an alias inside a
    replaced helper's body was no site), so `jd.load_goals_shared` counts both spellings of the shared door and nothing else, and a mention in a comment, a
    docstring or any string literal is no node of these kinds and no site: the one rule the source censuses share. By the same
    rule a loader reached through a string names it in no node of these kinds and is outside the census: `getattr(jd,
    "load_goals_shared")` (the string built by concatenation too), `exec` or `eval` of a string, `compile` of one,
    `operator.attrgetter("load_goals_shared")`, `vars(jd)["load_goals_shared"]` or `jd.__dict__[...]`,
    `jd.__getattribute__("load_goals_shared")`, and `getattr` on an `importlib.import_module` result (the consolidation pass: the
    limit named in full; the sample case holds the getattr form at no site). The kernel-wide pin, _loader_births, refuses, in the
    kernel and the judge, a string CONSTANT whose whole text is a door's name wherever it appears and whatever receives it (the
    value rule of the round-4 fixes: methodcaller, itemgetter, getattr_static, a partial of getattr, a match-mapping key and any
    dispatcher nobody listed receive the same refused constant), and a constant that merely CONTAINS the name where it reaches one
    of these lookups, a dict read (`.get`, `.pop`, `.setdefault`, `.__getitem__`) or a subscript key; a name assembled at run time
    from pieces none of which spells a door whole (`"load_" + "goals_shared"`, `"load_%s_shared" % "goals"`) is spelled in no
    constant it reads and is outside every static pin in this module (a verifier of the consolidation pass planted the two
    subscript forms and the dict read as a real load in a replaced helper and the module stayed green, and the round-4 refuters
    six doors on no list; _LIMITS names the two classes, string and assembled, and the enumeration runs the pin over each form of
    both and expects a birth from the first class and none from the second). A name bound OUTSIDE obj's source is no site in
    obj either (a module-level alias of a door, an import alias at module level, a module-level dict or partial, a closure
    variable, a parameter, a class or instance attribute when only the method is scanned): the same pin refuses every such birth
    in the kernel and the judge, where the alias is spelled. And the census reads the object it is handed: behind a decorator
    without functools.wraps that is the wrapper, so the replaced-helpers census checks each object is the named helper first.
    Every form, counted and missed, is enumerated in TheCensusOverEveryForm. Two calls on one line are two sites. A node of a class
    outside _AST_CONCRETE is refused by name before the census answers (_walk, the reviewer's version demand), never passed over as
    no site. Read from the tree and not from tokenised text
    (review round 2, correctness-1): the first cut blanked comments and strings token by token, and on 3.10 and 3.11 the
    tokenizer gives a whole f-string as one STRING token (3.12 and later split it into FSTRING_* parts), so a loader CALL
    written inside an f-string was blanked with the literal and invisible on two of the five CI interpreters; ast.walk reaches
    the JoinedStr's FormattedValue and its Call on every interpreter, and reads the f-string's literal text on none."""
    src = textwrap.dedent(inspect.getsource(obj))
    lines = src.splitlines()
    out = []
    for node in _walk(ast.parse(src)):
        if isinstance(node, ast.Name):
            spelled = node.id
        elif isinstance(node, ast.Attribute):
            spelled = _spelled(node)
        elif isinstance(node, ast.alias):
            spelled = node.name                       # the imported name; the alias itself (`as _lgs`) is a spelling of the census's own
        else:
            continue
        if needle in spelled:
            out.append((node.lineno - 1, lines[node.lineno - 1]))
    return sorted(out)


def _bump_sites(obj):
    """The line indices (as _loader_sites indexes) of every `_NUDGE_WALK_STATS["loads"] += 1` in `obj`'s source, read as a
    statement from the AST: an augmented add on a constant "loads" subscript of the Name _NUDGE_WALK_STATS, never a line of
    text (review round 2: a comment quoting the statement counted as a bump). Any other spelling (a plain assignment, the key in
    a variable, the dict under a local alias or qualified by its module, `-= -1`, `__setitem__`, `update`) is no bump here, so
    the walk census reds on it, conservatively; the increment's value is not read (the served counter's delta holds it), and a
    bump under a one-line `if` or `for` on the line after the load counts with its adjacency intact. The bump forms are
    enumerated in TheCensusOverEveryForm (the consolidation pass)."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(obj)))
    return [n.lineno - 1 for n in _walk(tree)
            if isinstance(n, ast.AugAssign) and isinstance(n.op, ast.Add) and isinstance(n.target, ast.Subscript)
            and isinstance(n.target.value, ast.Name) and n.target.value.id == "_NUDGE_WALK_STATS"
            and isinstance(n.target.slice, ast.Constant) and n.target.slice.value == "loads"]


_DYNAMIC_LOOKUPS = ("getattr", "exec", "eval", "compile", "__import__", "import_module", "attrgetter", "vars", "__getattribute__")
_DICT_READS = ("get", "pop", "setdefault", "__getitem__")   # a namespace dict read by key: jd.__dict__.get("load_goals_shared") and its kin
# The four doors' spellings: the CLOSED set the value rule in _loader_births keys on (the kernel spells them jd.<door>, the judge
# bare; _PJ.load_goals_shared, a second judge module's spelling, is an Attribute and not a string). A string constant whose whole
# text is one of these is refused wherever it appears and whatever receives it, so the receivers, an open set (review round 4 found
# six on no list), never need listing; _DYNAMIC_LOOKUPS and _DICT_READS stay for the constant that merely CONTAINS the name.
_DOOR_SPELLINGS = ("load_goals", "load_goals_or_fault", "load_goals_shared", "load_goals_shared_or_fault")


def _callee_name(func):
    """The name a Call's callee is spelled by, for a message: a Name's id, an Attribute's last part, and for a callee that is
    itself a call (`functools.partial(getattr, jd)("load_goals_shared")`) that call's callee with `(...)`."""
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Call):
        return _callee_name(func.func) + "(...)"
    return type(func).__name__


def _loader_births(path, judge):
    """Every place a file's source could give a loader another name, or reach one through a string, over its whole AST (the
    consolidation pass, and the value rule since the round-4 fixes): (born, called, defs, handoffs). `born` lists (line, what) for
    every reference to a loader the census could not follow into a body: an Attribute spelled with a loader that is not the callee
    of a call (bound to a name, passed, stored in a dict or list, a default, an assignment target); a bare Name spelled with a
    loader (in the kernel, any: the kernel reaches the judge's doors as `jd.<door>(...)`; in the judge, `judge`, one that is
    neither the callee of a call nor the loader a boundary wrapper hands to _or_fault, which is what `handoffs` lists as (wrapper,
    loader)); an import alias; a parameter or a keyword named like a loader; a loader defined behind a decorator; and a
    loader-naming string CONSTANT, under two clauses. The value rule: a constant whose whole text is one of the four door
    spellings (_DOOR_SPELLINGS) is a birth wherever it appears and whatever receives it, the receiver named from the constant's
    parent for the message (handed to a call's callee, which is how methodcaller, itemgetter, getattr_static, a partial of getattr
    and any dispatcher nobody listed are named without being listed; under an Assign, a Dict, a MatchMapping, a Compare, a
    docstring's Expr). The rule keys on the closed set, the doors' names, and not on the open one, the callables that could
    receive them (review round 4, correctness-1, tests-1 and extra6-1: the pin refused the constant at nine lookups, four dict
    reads and a subscript slice, and the round found six working doors on no list). It reads every constant, docstrings included,
    and needs no exemption at this head: by whole-text equality the kernel and the judge carry zero such constants (the judge's
    three error strings that mention a door contain its name and spell none whole), so the known call sites it would except are
    the empty set; a future legitimate whole-spelling constant needs an exemption row here with its reason, the shape the walker
    pin's table takes. The consumer clause, kept: a constant that merely CONTAINS the needle is a birth where it reaches one of
    _DYNAMIC_LOOKUPS (getattr, exec, eval, compile, __import__, import_module, attrgetter, vars, __getattribute__) or a dict read
    named in _DICT_READS (get, pop, setdefault, __getitem__), the callee matched by its last name and its arguments and keyword
    values walked, or a Subscript's slice (`vars(jd)["load_goals_shared"]`, `jd.__dict__["load_goals_shared"]`), walked as the
    arguments are, so a key written as an f-string, a conditional, a walrus or a concatenation reaches its constant (review round
    4, extra6-2: the Call clause walked into its arguments while the slice was tested as a direct Constant, and a real load through
    `vars(jd)[f"load_goals_shared"]` in a replaced helper passed every witness); it holds the dotted strings handed to exec, eval
    and compile (`"jd.load_goals_shared"`) and the concatenations that keep the needle in one piece (`"load_goals_" + "shared"`,
    `vars(jd)["load_goals_" + "shared"]`), which spell no door whole, and it names in the message the door a constant went
    through. Each constant is reported once, by the clause that reaches it first (the walk is breadth-first, so a Call or a
    Subscript is visited before its constant). The first cut read a dynamic lookup's arguments alone, and a verifier of the
    consolidation pass planted both subscript forms and `jd.__dict__.get(...)` as a real load inside a replaced helper's body with
    the module green. The limit that remains is the assembled class alone: a concatenation, a format or an f-string that splits the
    needle (`"load_" + "goals_shared"`, `"load_%s_shared" % "goals"`, `f"load_{'goals'}_shared"`) spells it in no constant this pin
    reads and is outside every static
    pin in this module (_LIMITS names the class `assembled`, and the enumeration holds each form of the string and assembled
    classes on the side it falls). The name bound to a variable before the lookup (`n = "load_goals_shared"; getattr(jd, n)`)
    was that class's until the round-4 fixes and is the string class's now: the constant spells the door whole where it is bound,
    and the rule reads it there. `called` counts each spelling called and `defs` each def named like a loader, so a caller can
    check the population it read is the doors' and not empty."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    parents = {}
    for node in _walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node

    def enclosing(node):
        while node is not None and not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            node = parents.get(node)
        return node.name if node is not None else "<module>"
    born, called, defs, handoffs = [], {}, {}, []
    reported = set()                                  # ids of the string constants the consumer clause has reported

    def string_births(node, what):
        """Every str Constant under `node`, walked as _walk walks (so a constant inside an f-string, a conditional, a walrus or a
        concatenation is reached), whose text contains the needle: a birth described by `what`, each constant reported once."""
        for sub in _walk(node):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str) and "load_goals" in sub.value and id(sub) not in reported:
                reported.add(id(sub))
                born.append((sub.lineno, "a loader-naming string %s in %s: %r" % (what, enclosing(sub), sub.value[:48])))

    def receiver(n, p):
        """What received a whole-spelling constant, for the message: handed to a call's callee when its parent is a Call it is an
        argument of (methodcaller, itemgetter, getattr_static or any dispatcher, named without being listed), through a keyword
        when its parent is one, else under the parent's class (Assign, Dict, MatchMapping, Compare, a docstring's Expr)."""
        if isinstance(p, ast.Call) and p.func is not n:
            return "handed to %s" % _callee_name(p.func)
        if isinstance(p, ast.keyword):
            call = parents.get(p)
            return "handed to %s as keyword %s" % (_callee_name(call.func) if isinstance(call, ast.Call) else type(call).__name__,
                                                    p.arg or "**")
        return "under %s" % type(p).__name__
    for n in _walk(tree):
        p = parents.get(n)
        as_callee = isinstance(p, ast.Call) and p.func is n
        if isinstance(n, ast.Attribute):
            spelled = _spelled(n)
            if "load_goals" in spelled:
                if as_callee:
                    called[spelled] = called.get(spelled, 0) + 1
                else:
                    born.append((n.lineno, "a loader by attribute that is not the callee of a call: %s, under %s in %s"
                                 % (spelled, type(p).__name__, enclosing(n))))
        elif isinstance(n, ast.Name) and "load_goals" in n.id:
            if judge and as_callee:
                called[n.id] = called.get(n.id, 0) + 1
            elif judge and isinstance(p, ast.Call) and isinstance(p.func, ast.Name) and p.func.id == "_or_fault" and n in p.args:
                handoffs.append((enclosing(n), n.id))
            else:
                born.append((n.lineno, "a loader as a bare name: %s, %s context under %s in %s"
                             % (n.id, type(n.ctx).__name__, type(p).__name__, enclosing(n))))
        elif isinstance(n, ast.alias) and "load_goals" in n.name + (n.asname or ""):
            born.append((n.lineno, "a loader imported: %s%s" % (n.name, " as " + n.asname if n.asname else "")))
        elif isinstance(n, ast.arg) and "load_goals" in n.arg:
            born.append((n.lineno, "a parameter named like a loader: %s in %s" % (n.arg, enclosing(n))))
        elif isinstance(n, ast.keyword) and n.arg and "load_goals" in n.arg:
            born.append((n.lineno, "a keyword named like a loader: %s in %s" % (n.arg, enclosing(n))))
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and "load_goals" in n.name:
            defs[n.name] = defs.get(n.name, 0) + 1
            if n.decorator_list:
                born.append((n.lineno, "a loader defined behind a decorator: %s" % n.name))
        # the consumer clause: a constant that merely CONTAINS the name, where it reaches a subscript key, a listed lookup or a dict read;
        # the slice is walked as the arguments are (review round 4, extra6-2: tested as a direct Constant, an f-string key passed)
        if isinstance(n, ast.Subscript):
            string_births(n.slice, "as a subscript key")
        if isinstance(n, ast.Call):
            last = n.func.id if isinstance(n.func, ast.Name) else n.func.attr if isinstance(n.func, ast.Attribute) else ""
            if last in _DYNAMIC_LOOKUPS or last in _DICT_READS:
                for a in list(n.args) + [k.value for k in n.keywords]:
                    string_births(a, "handed to %s" % last)
        # the value rule: a constant spelling a door WHOLE is a birth wherever it appears and whatever receives it (the receiver is
        # named from the parent, never matched against a list); one the consumer clause reached first is not reported twice
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in _DOOR_SPELLINGS and id(n) not in reported:
            born.append((n.lineno, "a loader-naming string constant %r %s in %s" % (n.value, receiver(n, p), enclosing(n))))
    return sorted(born), called, defs, sorted(handoffs)


def _caller(frame, boundary):
    """(function, file, line) of the frame that asked for the store: `frame` is the recorder's own, its f_back the immediate
    caller, and the judge's boundary frames are stepped over by code identity, never by name, so a call through either
    boundary wrapper is named for the kernel function that made it. `boundary` pairs each wrapper's code object with the
    lines of its pass-through calls (_pass_through_lines, taken at setUp): a boundary frame is stepped over only while it
    sits at one of those lines, so a load written anywhere else in a wrapper's own body is named for the wrapper itself,
    in the judge's file (the build's verifier pass after the round-1 fixes: stepped over unconditionally, a load planted inside
    _or_fault was named for the wrapper's kernel caller, the misnaming that costs more than silence). The file is the basename of the frame's REAL
    path: the kernel is loaded from bin/romp-kernel, a symlink to kernel/kernel.py, so the bare basename would read
    romp-kernel."""
    f = frame.f_back
    while True:
        lines = next((ls for c, ls in boundary if f.f_code is c), None)
        if lines is None or f.f_lineno not in lines:
            break
        f = f.f_back
    return f.f_code.co_name, os.path.basename(os.path.realpath(f.f_code.co_filename)), f.f_lineno


class _FakeBackend:
    def __init__(self):
        self.sent = []

    def send(self, sid, body):
        self.sent.append((sid, body))

    def pending_queued(self, sid):
        return []


class _WalkHarness(unittest.TestCase):
    """The real pass over two synthetic sessions, the toggle off, every seam it moves put back by a cleanup registered
    before the first rebind (unittest skips tearDown when setUp raises and runs the cleanups regardless)."""

    def setUp(self):
        before_km, before_jd = dict(vars(km)), dict(vars(jd))   # FIRST: the agreement check at the end of setUp compares against these
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)                  # cleanups run last in, first out: the seams go back, then the dir
        td = Path(self.td.name)
        self.saved = {k: getattr(km, k) for k in REPLACED_KM + CASE_KM}   # CASE_KM saved too: a case replaces them after setUp
        self.saved_jd = {k: getattr(jd, k) for k in REPLACED_JD + ("load_goals", "load_goals_shared")}
        self.saved_state = jd.STATE
        self.saved_backend = km.Sessions.backend_for
        self.shared_off_before = jd._SHARED_OFF[0]
        self.walk_stats = {k: (dict(v) if isinstance(v, dict) else v) for k, v in km._NUDGE_WALK_STATS.items()}
        self.gate_stats = dict(km._NUDGE_GATE_STATS)
        self.seen = dict(km._TICK_SEEN)
        self.first = ({k: (list(v) if isinstance(v, list) else v) for k, v in km._NUDGE_WALK_FIRST.items()},
                      km._NUDGE_WALK_FIRST_OPEN[0])
        self.addCleanup(self._restore)
        self._before_rebind()                             # a hook: a pin overrides it to place a stub between the first snapshot and the rebind
        pre_rebind = dict(vars(jd))                       # the judge's globals AT the rebind, so the names it moves are the diff across that
        jd._rebind_state(td)                              #   one call (STATE and every dir derived from it, never jd.STATE alone) and nothing
        rebound_by_rebind = {k for k, v in vars(jd).items() if pre_rebind.get(k, _UNSET) is not v}   # rebound before it is filed as the
        #                                                   rebind's (the build's verifier pass after the round-2 fixes: read against the FIRST
        #                                                   snapshot, a judge stub placed between it and the rebind was subtracted below and
        #                                                   escaped). The set is the judge's directory
        #                                                   and path globals (kernel/judge.py, _rebind_state's global list), subtracted at the
        #                                                   comparison below, so no hand-kept copy of that list exists
        self._after_rebind()                              # a hook: a pin overrides it to place a stub right after the rebind
        jd.GOALDIR.mkdir(parents=True)
        jd.EPIDIR.mkdir(parents=True)
        (td / "session-hosts").write_text("off")          # a root this test minted: no session host may start under it
        km._SESSION_STAMP_CACHE.clear(); km._autonudge_cache.clear()
        jd._shared_clear(); jd._SHARED_OFF[0] = False      # the shared cache is on for the test and restored after it
        km._nudge_gate_memo.clear(); km._nudge_deleg_memo.clear()
        km._TICK_SEEN.clear()
        for k, v in list(km._NUDGE_WALK_STATS.items()):
            km._NUDGE_WALK_STATS[k] = {} if isinstance(v, dict) else 0
        km._NUDGE_WALK_FIRST_OPEN[0] = False
        self.fb = _FakeBackend()
        km.Sessions.backend_for = lambda sid: self.fb
        km._wait_for_graph = lambda now, sids: {}
        km._session_flag = lambda sid, flag: False
        km._compacting_now = lambda sid: False
        km._api_error = lambda path: None
        # _session_working runs REAL: over the fixture turns (both ended, the last with no idle tail) the event model answers not
        # working, as the stub did, so the gate costs the fixture nothing and a loader planted in its body is caught by execution
        km._interrupt_suppresses_nudge = lambda turns, sid="", **k: False
        km._backend_rewind_pending = lambda sid: False
        km._last_state = lambda sid: ("", 0)
        km._session_awaiting = lambda *a, **k: None
        km._turn_romp_injected = lambda tn: False
        km._closer_settled = lambda *a: True              # kept stubbed: the fixture store carries no closedTurns, so the real gate ends
        #                                                   both looks at closer-unsettled before the placement gate (walk 1 and 1, gate 0
        #                                                   and 0, memo (0, 0)); seeding closer state is a larger fixture change than the
        #                                                   disclosure, and the source census below scans the real body instead
        km._revivers_pending = lambda *a, **k: ""
        km._pending_ops = {}
        km._log_nudge_event = lambda *a, **k: None
        km._push_all = lambda *a, **k: None
        km._mark_views_dirty = lambda *a, **k: None
        km._debt_backstop_tick = lambda now: None
        km._PREV_ALIVE = set(SIDS)                        # no death transition pending
        # the sessions: real transcript files under the state root (the memo's first keyed file; a missing one never skips)
        self.rows = {}
        for i, sid in enumerate(SIDS):
            p = td / (sid + ".jsonl")
            p.write_text(json.dumps({"type": "user", "uuid": sid[:8], "timestamp": "2026-09-10T00:00:00Z",
                                     "message": {"role": "user", "content": "x"}}) + "\n")
            os.utime(p, (NOW - H, NOW - H))
            self.rows[sid] = {"sid": sid, "path": str(p), "name": ("web", "api")[i], "mtime": NOW - H - 100 * i}
        km._alive_sessions = lambda now, live: [self.rows[s] for s in SIDS]
        km._path_of = lambda sid, now=None: self.rows[sid]["path"] if sid in self.rows else ""
        # the parse: fixture turns recorded in the parse cache under a per-sid generation key, as parsed_session records a
        # parse (the gate keys its memo on that key while the cached turns object is the one the walk holds; a re-parse
        # moves the key, so the gate derives again and pays its currency re-read)
        self.turns = {sid: [{"id": "t1", "ended": True, "end": NOW - 8 * H, "t": NOW - 8 * H - 10, "atoms": []},
                            {"id": "t2", "ended": True, "end": NOW - 7 * H - 100, "t": NOW - 7 * H - 200, "atoms": []}]
                      for sid in SIDS}
        self.parse_gen = dict.fromkeys(SIDS, 0)
        self.parsed = []

        def _parsed(sid, paths, now):
            self.parsed.append(sid)
            sess = {"turns": self.turns[sid]}
            jd._PARSE_CACHE[sid] = (("fixture", self.parse_gen[sid]), sess)
            return sess
        jd.parsed_session = _parsed
        jd._segs = lambda tn, store: []
        jd.plan_units = lambda session, store, lazy_text=None: []
        # the witnesses by execution: recorders on the judge's two doors, each calling through. The shared recorder stands on
        # the INNER door, jd.load_goals_shared: load_goals_shared_or_fault hands that name to _or_fault, which resolves it from
        # the judge's globals at call time, so a call by either spelling arrives here (a recorder on the outer door alone
        # missed the bare spelling, the one _awaiting_wake_outcomes uses: review round 1)
        real_shared, real_writer = self.saved_jd["load_goals_shared"], self.saved_jd["load_goals"]
        for fn, name in ((real_shared, "load_goals_shared"), (real_writer, "load_goals")):
            self.assertEqual((fn.__code__.co_name, os.path.basename(os.path.realpath(fn.__code__.co_filename))), (name, JUDGE_FILE),
                             "jd.%s is the judge's own door (no stand-in left by a peer module)" % name)
        # The boundary frames and the shared door's body, by CODE identity, taken from the real functions NOW, before this setUp
        # replaces a door. Not at import: the judge module is shared by every kernel a worker loads and re-executed into the same
        # module object by each load (romp_load), so a code object captured when this module was imported is a previous
        # execution's once a sibling module imports its kernel (the first run beside six siblings failed on exactly that).
        boundary = []
        for fn, callee in ((jd._or_fault, "loader"), (jd.load_goals_shared_or_fault, "_or_fault"), (jd.load_goals_or_fault, "_or_fault")):
            lines, calls = _pass_through_lines(fn, callee)
            self.assertEqual(len(lines), 1, "%s's hand-off calls sit on one line, the granularity the recorder steps over at: the "
                                            "wrapper's frame is stepped over only while it sits at that line" % fn.__name__)
            self.assertEqual(calls, 1, "%s hands the read on at exactly one call: a second call on the same line would be stepped "
                                       "over too and named for the wrapper's kernel caller" % fn.__name__)
            boundary.append((fn.__code__, lines))
        boundary = tuple(boundary)
        shared_body = real_shared.__code__
        self.calls, self.writer = [], []
        self.owned_records = {}                           # sid -> the wake records the sweep owns this test (the seeding helper sets it)

        def _shared(sid):
            self.calls.append((sid,) + _caller(inspect.currentframe(), boundary))
            return real_shared(sid)

        def _load(sid):
            if inspect.currentframe().f_back.f_code is not shared_body:          # the shared door's own fallback into load_goals (the
                self.writer.append((sid,) + _caller(inspect.currentframe(), boundary))   # cache off, no store file, an unreadable
            return real_writer(sid)                                              #  journal, corrupt bytes) is one logical read: the shared
        jd.load_goals_shared = _shared                                           #  recorder recorded its caller, so nothing is recorded here;
        jd.load_goals = _load                                                    #  the door's own counter counts it as a hand-off (writerLoads)
        self._toggle(False)
        self._seed(SID_A, stamped=False)
        self._seed(SID_B, stamped=True, age=5 * H)
        # The road limit's list is checked against the fixture, not kept by hand, over the WHOLE setUp: the snapshots are its first
        # statements and this comparison its last, so this setUp rebinds exactly the names REPLACED_KM and REPLACED_JD list plus the
        # two recorded doors, with Sessions.backend_for beside them, and a stub placed anywhere in between without a list entry
        # reds here (a stub without a list entry hides a loader from the execution witness AND from the census that reads the
        # list). Review round 2, correctness-2 and tests-1: the snapshot sat in the middle of setUp, after the cache clears, and
        # a stub above it escaped the check, the census and the execution witness (8 passed with a shared load in the stubbed
        # helper's real body). The build's verifier pass after the round-2 fixes: the judge names the rebind moves were read against
        # the first snapshot, so a judge stub between that snapshot and the rebind was filed as the rebind's and subtracted; they are read against a snapshot
        # taken at the rebind itself now (pre_rebind), so a stub anywhere before or after it stays in this comparison. Outside the
        # window: a stub installed before setUp, and a jd directory or path name the rebind also moves (subtracted below, so a
        # later stub on one of those names is not seen either).
        rebound_km = {k for k, v in vars(km).items() if before_km.get(k, _UNSET) is not v}
        self.assertEqual(rebound_km, set(REPLACED_KM), "setUp replaces exactly the kernel names REPLACED_KM lists, the census's targets: a "
                                                        "stub without a list entry hides a loader from the execution witness and the census")
        rebound_jd = {k for k, v in vars(jd).items() if before_jd.get(k, _UNSET) is not v} - rebound_by_rebind
        self.assertEqual(rebound_jd, set(REPLACED_JD) | {"load_goals", "load_goals_shared"},
                         "and exactly the judge names REPLACED_JD lists plus the two recorded doors (the names jd._rebind_state moves "
                         "subtracted)")
        self.assertIsNot(km.Sessions.backend_for, self.saved_backend, "and Sessions.backend_for, replaced beside them")

    def _before_rebind(self):
        """A no-op hook, called right before the judge snapshot the rebind's diff is read against: the region between setUp's first
        snapshot and the rebind, where a judge stub was filed as the rebind's and escaped until the build's verifier pass after the
        round-2 fixes. A pin overrides it
        to place a stub there and expects setUp to refuse it (TheAgreementCheckSpansSetUp)."""

    def _after_rebind(self):
        """A no-op hook, called right after jd._rebind_state: the region the agreement check's first snapshot missed (review round
        2). A pin overrides it to place a stub there and expects setUp to refuse it (TheAgreementCheckSpansSetUp)."""

    def _restore(self):
        journals = [jd._overrides_dir() / (sid + ".jsonl") for sid in SIDS + (SID_C,)]   # under this test's root, resolved before the rebind back
        for k, v in self.saved.items():
            setattr(km, k, v)
        for k, v in self.saved_jd.items():
            setattr(jd, k, v)
        km.Sessions.backend_for = self.saved_backend
        km._SESSION_STAMP_CACHE.clear(); km._autonudge_cache.clear()
        jd._shared_clear(); jd._SHARED_OFF[0] = self.shared_off_before
        km._nudge_gate_memo.clear(); km._nudge_deleg_memo.clear()
        km._NUDGE_WALK_STATS.clear(); km._NUDGE_WALK_STATS.update(self.walk_stats)
        km._NUDGE_GATE_STATS.clear(); km._NUDGE_GATE_STATS.update(self.gate_stats)
        km._TICK_SEEN.clear(); km._TICK_SEEN.update(self.seen)
        first, open_ = self.first
        for k, v in first.items():
            if isinstance(v, list):
                km._NUDGE_WALK_FIRST[k][:] = v
            else:
                km._NUDGE_WALK_FIRST[k] = v
        km._NUDGE_WALK_FIRST_OPEN[0] = open_
        for j in journals:
            try:
                j.unlink()
            except OSError:
                pass
        jd._rebind_state(self.saved_state)               # the root goes back the way it was found (the parse entries go with it)

    def _toggle(self, enabled):
        (jd.STATE / "auto-nudge.json").write_text(json.dumps({"enabled": enabled, "nudged": {}}))
        km._autonudge_cache.clear()

    def _seed(self, sid, stamped, age=5 * H):
        """A working top under `sid`; with `stamped`, carrying a kind=job awaiting stamp `age` old."""
        gid = sid + ":g1"
        at = NOW - age
        why = "the index rebuild is still running; picking the result up when it lands"
        top = {"id": gid, "text": "rebuild the notes-api index", "parentId": None,
               "nodeComplete": False, "blocked": False, "cleared": False, "trail": [], "t": 100, "mt": 100, "log": []}
        if stamped:
            top.update({"awaitingWhy": why, "awaitingAt": at, "awaitingKind": "job"})
            top["log"].append({"ev_t": at, "src": "closer", "kind": "awaiting", "why": why, "awaitKind": "job", "at": at})
        (jd.GOALDIR / (sid + ".json")).write_text(json.dumps({
            "rompUuid": sid, "seq": 1, "placements": {}, "status": {gid: "working"}, "nodes": {gid: top}}))
        km._SESSION_STAMP_CACHE.clear()

    KEYS = ("looks", "parses", "skippedParses", "wakeOnly", "loads")

    def _pass(self, now):
        """One pass over the two sessions: the walk's counter deltas, the placement gate's (served, derived) deltas, and the
        shared-loader calls per mechanism and sid (`walk`: the look's decision read; `gate`: the placement gate's currency
        check; `sweep`: the wake sweep's read per owned record; never a total), the writer loads, and the sids parsed. `walk`
        and `gate` are keyed on SIDS as the floor, so the cases' zero-assertions keep their keys, plus any other sid a
        recorded call of theirs names; `sweep` is keyed on every sid seen, since its constituency includes unwalked sids. So
        every recorded call sits inside one bound, and a shared load by the look or by the gate for a session that is not one
        of the pass's two is named by function, file, line and sid by its own assertion; a read by either of the OTHER pass
        session lands in that session's count and is held by the ceilings, which name the sid and the mechanism (the build's
        verifier pass after the round-2 fixes: this prose said the two read only the session they look at, which no assertion
        checks); the sweep's read of an
        unwalked sid is legitimate and is held to its bound per sid instead. With no owned record (`owned_records` empty, as in the first
        class) that bound holds the sweep to zero on every pass, which is why those cases assert nothing about it. The
        walk's per-sid ceiling, the gate's per-sid ceiling, the gate's general bound (checks never exceed derives) and its
        fixture equality (checks equal derives, because the harness's parsed_session records every parse) are asserted
        here too, on every pass, ahead of the cases' exact counts: a case pins each pass's dicts exactly, so a ceiling
        placed after those pins could never be the line that fails. The equality's failure message stays as it is (the
        reviewer's word after round 3): it names the fixture invariant that makes checks equal derives, the harness's
        parsed_session recording every parse in jd._PARSE_CACHE, and not condition 7's gate, whose rule is the bound beside it;
        widened to speak for the gate it would claim what the bound's own message already claims. The recorders stand on the judge's two doors,
        `jd.load_goals_shared` and `jd.load_goals`, and attribute through its boundary frames by code identity, so a shared
        load from any other function the fixture executes during the pass fails here, named by function, file and line (the
        helpers the fixture replaces, REPLACED_KM, REPLACED_JD and Sessions.backend_for, are the source census's in
        TheCountersOneSite, not this witness's), and the sweep is held to its bound per sid; the writer door's list is
        asserted empty after every pass, separately, each entry named the same way; a reader below the doors is outside the
        claim. The store's counters are reconciled against the recorded calls per door (`shared`, the delta over
        SHARED_CALL_KEYS, against every recorded shared call, listed in the message; `writerLoads`, the delta of goal_io
        loads, against the writer records plus the shared door's hand-offs over SHARED_HANDOFF_KEYS), so a load through a
        door of the judge module the recorders do not wrap is noticed, unnamed; a reader that bypasses the module is outside
        both. Between the two sits the second-bump bound (ruling 1 of the reviewer's rulings on the pre-emption), derived from
        load_goals_shared's body in judge.py,
        read top to bottom: `_shared_bump("fallback")` then `return load_goals(fsid)` under `if _SHARED_OFF[0]`;
        `_shared_bump("absent")` then the same return under `except FileNotFoundError` around the store's open;
        `_shared_bump("hit")` then `return ent[2]` when the cached entry's keys and bytes both match; `_shared_bump("compare_miss")`
        when the keys match and the bytes do not, else `_shared_bump("miss")`; and from there the fill road, on which at most one
        more key is bumped, each followed by its return: `_shared_bump("unreadable_journal")` under `except OSError` around
        `_journal_read` (then `return load_goals(fsid)`), `_shared_bump("corrupt")` under `except ValueError` around `_disk_parse`
        (then `return load_goals(fsid)`), `_shared_bump("unreadable_journal")` again under `if store.get("_unread")` (then
        `return store`), `_SHARED_STATS["dup"] += 1` when a concurrent fill published the same version first (then `return
        cur[2]`), and `_SHARED_STATS["refuse"] += 1` when `akey1 != akey0` (then `return frozen`). So a call bumps a second key
        only after its miss or compare_miss bump and bumps at most one, and per pass
        unreadable_journal + corrupt + dup + refuse <= miss + compare_miss. The three premises of that reading, the rosters, the
        order and the at-most-one, are pinned against the door's AST by the roster pin in TheCountersOneSite (the third as the
        innermost statement list holding each second-key bump holding exactly one and ending in a return or a raise), the at-most-one
        by execution as well in TheDoorBumpsAtMostOneSecondKeyPerCall, and the fill keys the right-hand side sums are derived there
        from the same AST and asserted equal to SHARED_FILL_KEYS, which this method sums (review round 4, tests-2, regression-2 and
        extra4-1: the two named by hand here, and the at-most-one held by nothing). The bound is what refuses the forged pair: corrupt and
        unreadable_journal are hand-off keys and not call keys, so a bump of either beside a goal_io loads bump with no call
        through the door moved no call key (the shared reconciliation balanced) and matched its loads bump with a hand-off (the
        writer reconciliation balanced), and before the bound red nothing here. The bound refuses the pair on a pass with no fill,
        and on a pass with fills refuses only what exceeds them: a pair that rides beside each genuine fill (one corrupt bump and one
        loads bump per miss the walk's read made) leaves second equal to fills, balances the writer reconciliation with its hand-off,
        and passes the bound; the cases' writerLoads elements are what red it there, 2 against 0 on the first pass (a
        consolidation-pass verifier's state), and two pairs per fill red the bound again, 4 against 2. So for the hand-off second keys,
        corrupt and unreadable_journal, the two layers cover different passes: the bound holds the passes with no fill on its own, and
        the tuples' writerLoads elements the passes with fills. For dup and refuse, neither call keys nor hand-off keys, the
        writerLoads elements see nothing, so the second layer is the zero line beside the bound: this harness is single-threaded (no
        concurrent fill, so no dup) and writes no goals-archive during a pass (so no refuse), and a bump of either on any pass is a
        counter moved with no road that moves it (review round 4, extra5-1: the sentence here said the two layers cover every pass,
        and a spurious dup or refuse bump beside a genuine fill, up to the fill count, was witnessed by nothing). `calls` carries the
        shared records (sid, function, file, line) for a case's own assertions, and `second` the second keys' delta, so the writerLoads
        lines that catch the pair beside a fill can print it (review round 4, tests-4)."""
        before = {k: km._NUDGE_WALK_STATS[k] for k in self.KEYS}
        gate0 = dict(km._NUDGE_GATE_STATS)
        s0, g0 = jd.shared_store_stats(), jd.goal_io_stats()["loads"]
        self.calls.clear(); self.writer.clear(); self.parsed.clear()
        km._auto_nudge_tick(now, {sid: {"state": ""} for sid in SIDS})
        s1, g1 = jd.shared_store_stats(), jd.goal_io_stats()["loads"]
        d = {k: km._NUDGE_WALK_STATS[k] - before[k] for k in self.KEYS}
        d["memo"] = tuple(km._NUDGE_GATE_STATS[k] - gate0[k] for k in ("served", "derived"))
        # the walk's and the gate's counts: keyed on SIDS as the floor (the cases' zero-assertions keep their keys) plus any other
        # sid a recorded call of theirs names, so every record of theirs sits inside a bound and the reconciliation below balances;
        # a record for a sid outside SIDS is then named by the assertion after the sweep's bound (review round 2, fresh-1: keyed on
        # SIDS alone, a foreign-sid read by the gate landed in no bound and red only the reconciliation, with a false cause)
        d["walk"] = {sid: sum(1 for s, c, _f, _ln in self.calls if s == sid and c in WALK)
                     for sid in set(SIDS) | {s for s, c, _f, _ln in self.calls if c in WALK}}
        d["gate"] = {sid: sum(1 for s, c, _f, _ln in self.calls if s == sid and c in GATE)
                     for sid in set(SIDS) | {s for s, c, _f, _ln in self.calls if c in GATE}}
        d["sweep"] = {}                                   # over every sid seen: the sweep's constituency includes unwalked sids
        for s, c, _f, _ln in self.calls:
            if c in SWEEP:
                d["sweep"][s] = d["sweep"].get(s, 0) + 1
        others = ["%s (%s:%d, sid ..%s)" % (c, f, ln, s[-4:]) for s, c, f, ln in self.calls if c not in WALK + GATE + SWEEP]
        self.assertEqual(others, [], "a shared load from a caller that is neither the walk, the placement gate nor the wake sweep, "
                                     "by function, file and line: %s" % "; ".join(others))
        for sid, n in sorted(d["sweep"].items()):
            recs = "; ".join("%s (%s:%d)" % (c, f, ln) for s, c, f, ln in self.calls if s == sid and c in SWEEP)
            self.assertLessEqual(n, self.owned_records.get(sid, 0),
                                 "sid ..%s: the sweep takes at most one shared load per wake record it owns per pass (a record that is "
                                 "wake-set, not failed, moot or answered, not muted, and whose sid the walk did not visit or visited "
                                 "under a wedge gate), none for a sid with no owned record; it runs after the per-session loop in the "
                                 "same pass and memos.nudgeWalk.loads does not count it; its records for this sid: %s" % (sid[-4:], recs))
        foreign = ["%s (%s:%d, sid ..%s)" % (c, f, ln, s[-4:]) for s, c, f, ln in self.calls if c in WALK + GATE and s not in SIDS]
        self.assertEqual(foreign, [], "a shared load by the look or the placement gate for a session that is not one of this pass's two, by "
                                      "function, file, line and sid (a read of the other pass session lands in its count and is the ceilings' "
                                      "below): %s" % "; ".join(foreign))
        # the ceilings and the gate's equality, here ahead of the cases' exact per-pass counts: a case pins each pass's dicts and
        # memo exactly, so a ceiling placed after those pins could never be the line that fails (review round 2, regression-1: the
        # three ceilings sat after the first case's five passes and no state reached them red), and the equality placed there
        # could fail only through a plant conditioned on the pass history; here each fires on the first pass that violates it
        for sid, n in sorted(d["walk"].items()):
            self.assertLessEqual(n, 1, "pass at %d, sid ..%s: the walk takes at most one shared load per alive session per pass "
                                       "(condition 7, the walk's bound)" % (now, sid[-4:]))
        for sid, n in sorted(d["gate"].items()):
            self.assertLessEqual(n, 1, "pass at %d, sid ..%s: the placement gate checks at most once per derived session (condition 7, "
                                       "the gate's bound)" % (now, sid[-4:]))
        self.assertLessEqual(sum(d["gate"].values()), d["memo"][1],
                             "pass at %d: the gate's checks never exceed its derives (condition 7, the gate's bound; a derive without a "
                             "cached parse checks nothing)" % now)
        self.assertEqual(sum(d["gate"].values()), d["memo"][1],
                         "pass at %d: equal here because the harness's parsed_session records every parse in jd._PARSE_CACHE, so every "
                         "derive holds its parse and checks once; the gate's rule is the bound above" % now)
        d["shared"] = {k: s1[k] - s0[k] for k in SHARED_CALL_KEYS if s1[k] != s0[k]}
        records = ["%s (%s:%d, sid ..%s)" % (c, f, ln, s[-4:]) for s, c, f, ln in self.calls]
        self.assertEqual(sum(d["shared"].values()), sum(d["walk"].values()) + sum(d["gate"].values()) + sum(d["sweep"].values()),
                         "the shared cache's five call counters (hit, miss, compare_miss, absent, fallback) moved %d times this pass and the "
                         "recorder on jd.load_goals_shared saw %d calls; the two must agree, since every call that reaches the cache's "
                         "branch and returns moves exactly one of them. This line knows the two figures and not the cause: counters %r; "
                         "recorded calls: %s. Among the possibilities: a load through a door of the judge module the recorders do not "
                         "wrap, a load through a reference to the real door taken before a recorder stood, a recorded call whose open or "
                         "read raised, a record appended without a call through"
                         % (sum(d["shared"].values()), len(self.calls), d["shared"], "; ".join(records) or "none"))
        # the second-bump bound (ruling 1 of the reviewer's rulings on the pre-emption): the derivation from the door's body is in
        # the docstring above
        second = {k: s1[k] - s0[k] for k in SHARED_SECOND_KEYS if s1[k] != s0[k]}
        fills = sum(d["shared"].get(k, 0) for k in SHARED_FILL_KEYS)   # the fill road's entry keys, derived from the door's AST by the roster pin
        self.assertLessEqual(sum(second.values()), fills,
                             "pass at %d: the shared door's second bumps, unreadable_journal + corrupt + dup + refuse, never exceed its fills, "
                             "miss + compare_miss: in load_goals_shared's body each sits on the fill road below the miss or compare_miss bump "
                             "and returns, so a call bumps at most one of them and none without a fill. This pass: second bumps %r, %d in all, "
                             "against %d fill(s) (%s); recorded shared calls: %s. A second bump past the fills is a "
                             "counter moved with no call through the door; corrupt and unreadable_journal are hand-off keys and not call keys, "
                             "so such a move beside a goal_io loads bump balances the shared and the writer reconciliations and is caught here "
                             "alone on a pass with no fill (on a pass with fills, one such pair per fill passes this bound and the case's "
                             "writerLoads element catches it)" % (now, second, sum(second.values()), fills,
                                        ", ".join("%s %d" % (k, d["shared"].get(k, 0)) for k in SHARED_FILL_KEYS), "; ".join(records) or "none"))
        # the second keys that are neither call keys nor hand-off keys, dup and refuse: no reconciliation reads them and the bound
        # above admits them up to the fills, so they are held to zero here, with the reason zero holds (review round 4, extra5-1)
        spurious = {k: v for k, v in second.items() if k not in SHARED_HANDOFF_KEYS}
        self.assertEqual(spurious, {},
                         "pass at %d: no dup and no refuse bump, the second keys that are neither call keys nor hand-off keys, so no "
                         "reconciliation reads them and the bound above admits them up to the fills (the cases' writerLoads elements read "
                         "the hand-off keys alone). Zero holds in this harness for a reason and not by luck: it is single-threaded, so no "
                         "concurrent fill publishes the same version first (dup), and nothing writes the goals-archive during a pass, so "
                         "_archive_key cannot move under a replay (refuse); a bump of either here is a counter moved with no road that moves "
                         "it. A future harness that drives those roads on purpose changes this line with its reason. This pass: second bumps "
                         "%r against %d fill(s); recorded shared calls: %s" % (now, second, fills, "; ".join(records) or "none"))
        d["second"] = second                              # the second keys' delta, for the writerLoads lines that catch the pair beside a fill
        d["calls"] = list(self.calls)
        writer = ["%s (%s:%d, sid ..%s)" % (c, f, ln, s[-4:]) for s, c, f, ln in self.writer]
        self.assertEqual(writer, [], "zero plain load_goals from any caller during the pass, the whole tick (condition 7 in ruling A's "
                                     "wording says the decision path; this window is wider), by function, file and line; the shared door's "
                                     "own fallback into load_goals is the shared door's read, skipped by code identity and counted under "
                                     "goal_io loads as a hand-off, never here: %s" % "; ".join(writer))
        handoffs = sum(s1[k] - s0[k] for k in SHARED_HANDOFF_KEYS)
        self.assertEqual(g1 - g0, handoffs,
                         "the writer door's own counter, goal_io loads, moves once per load_goals call (the loader's first line), and the "
                         "shared door hands a read to load_goals on exactly the absent, fallback, corrupt and unreadable_journal counters; "
                         "the recorded writer calls are zero here (the assertion above), so the delta must equal those hand-offs alone; a "
                         "difference is a writer-door load the recorder did not see, through a reference to the real door taken before it "
                         "stood or written inside the shared door's own body (the fallback skip takes it for the hand-off): loads %d against "
                         "hand-offs %d" % (g1 - g0, handoffs))
        d["writerLoads"] = g1 - g0                        # the writer door's own counter; the recorder's list is asserted empty above, so
        #                                                   it is not returned (a case-level read of it could never fail: review round 2)
        d["parsedSids"] = sorted(self.parsed)
        return d

    def _row(self, sid):
        return km._TICK_SEEN.get(("auto-nudge", sid))


class OneSharedLoadPerAliveSessionPerPass(_WalkHarness):
    def test_exactly_one_on_a_run_and_zero_on_a_skip_by_execution_and_by_the_served_counter(self):
        # (a) the first pass: no memo on record, so every look runs, and every placement gate derives
        p1 = self._pass(NOW)
        self.assertEqual((p1["looks"], p1["parses"], p1["skippedParses"], p1["wakeOnly"]), (2, 2, 0, 2), p1)
        self.assertEqual(p1["walk"], {SID_A: 1, SID_B: 1},
                         "the walk takes exactly one shared load per alive session when its look reaches the store (condition 7, the walk's bound)")
        self.assertEqual(p1["loads"], 2, "memos.nudgeWalk.loads moves by the walk's count: one per look that reached the store")
        self.assertEqual((p1["gate"], p1["memo"]), ({SID_A: 1, SID_B: 1}, (0, 2)),
                         "the placement gate's currency check loads at most once per derived session; here every gate derived with its parse "
                         "cached, so each checked once (condition 7, the gate's bound)")
        self.assertEqual(p1["writerLoads"], 0, "no hand-off: every read of this pass hits or fills, so the shared door hands nothing to "
                                               "load_goals and the writer door's own counter, goal_io loads, stays (the writer list itself is "
                                               "_pass's assertion, empty on every return). This line is also the layer behind _pass's "
                                               "second-bump bound on a pass with fills: a forged pair, a corrupt or unreadable_journal bump "
                                               "beside a goal_io loads bump with no call through the door, riding beside each genuine fill "
                                               "leaves second equal to fills and balances both reconciliations, and reds here as loads with "
                                               "no hand-off the door made. writerLoads %d; the store's call counters %r, its second bumps %r"
                                               % (p1["writerLoads"], p1["shared"], p1["second"]))
        self.assertEqual(p1["shared"], {"hit": 2, "miss": 2}, "the store's counters: each walk read fills (a miss), each gate check hits")
        for sid in SIDS:
            self.assertIsNotNone(self._row(sid), "a wake-mode memo row stands for %s" % sid[-4:])
        # (b) nothing changed: every look skips, and a skipped look repeats its verdict and needs no data
        p2 = self._pass(NOW + 5)
        self.assertEqual(p2["walk"], {SID_A: 0, SID_B: 0},
                         "the walk takes no shared load on a skipped look: zero per alive session (condition 7, the walk's bound)")
        self.assertEqual(p2["gate"], {SID_A: 0, SID_B: 0},
                         "the placement gate makes no currency check on a skipped look: it is never reached (condition 7, the gate's bound)")
        self.assertEqual((p2["looks"], p2["skippedParses"], p2["parses"]), (2, 2, 0), p2)
        self.assertEqual((p2["loads"], p2["writerLoads"], p2["shared"]), (0, 0, {}),
                         "and neither the counter, the writer door's counter nor the store's call counters move: no read, so no hand-off and no "
                         "call key (the two elements restored by ruling 1 of the reviewer's rulings on the pre-emption; _pass's two "
                         "reconciliations and its second-bump bound fire "
                         "first on a counter moved with no call, and this line stands behind them)")
        # (a) again with the gate SERVED: the ledger is the tenth keyed file, so its move re-evaluates every session once while
        # the parse and the store stand; the walk loads once per session and the gate not at all
        os.utime(jd.STATE / "auto-nudge.json", (NOW + 8, NOW + 8))
        p3 = self._pass(NOW + 10)
        self.assertEqual((p3["looks"], p3["parses"], p3["skippedParses"]), (2, 2, 0), p3)
        self.assertEqual(p3["walk"], {SID_A: 1, SID_B: 1},
                         "the walk takes exactly one shared load per alive session when its look reaches the store (condition 7, the walk's bound)")
        self.assertEqual((p3["gate"], p3["memo"]), ({SID_A: 0, SID_B: 0}, (2, 0)),
                         "the placement gate is served and makes no currency check (condition 7, the gate's bound)")
        self.assertEqual((p3["loads"], p3["writerLoads"], p3["shared"]), (2, 0, {"hit": 2}),
                         "the counter moves by the walk's two, no hand-off, two hits (that both reads hit is the gate's line above as well: a "
                         "non-hit gives the walk a new view object, so the gate derives; the two elements restored by ruling 1 of the "
                         "reviewer's rulings on the pre-emption, behind "
                         "_pass's reconciliations and its second-bump bound)")
        # (b) again, by the re-arming: p3's run recorded a fresh memo row for each session under the ledger's moved key (the gate
        # wrapper records after every look that parsed and did not fire, a standing row or not; nothing fires here, the toggle is
        # off) and journaled nothing (these looks end with no state-gate verdict, so the pass pops no walk gate and writes nothing
        # into the ledger), so every keyed file stands and
        # this pass skips. A look that recorded only when no row stood, or re-recorded under the standing row's key, would run
        # here with the three passes above green: this pass's two lines are what pin the re-record (the consolidation pass's replay
        # lens).
        p4 = self._pass(NOW + 15)
        self.assertEqual((p4["walk"], p4["gate"]), ({SID_A: 0, SID_B: 0}, {SID_A: 0, SID_B: 0}),
                         "the walk takes no shared load on a skipped look, and the placement gate is never reached (condition 7, both bounds)")
        self.assertEqual((p4["skippedParses"], p4["loads"]), (2, 0), "skipped again, and the counter stays")
        # one session's transcript moves: its look runs and derives (the parse key moved), the other's skips; per session
        pa = Path(self.rows[SID_A]["path"])
        pa.write_text(pa.read_text() + json.dumps({"type": "user", "uuid": "aaaaaaaa", "timestamp": "2026-09-10T00:01:00Z",
                                                   "message": {"role": "user", "content": "y"}}) + "\n")
        os.utime(pa, (NOW + 18, NOW + 18))
        self.parse_gen[SID_A] += 1
        p5 = self._pass(NOW + 20)
        self.assertEqual((p5["parsedSids"], p5["parses"], p5["skippedParses"]), ([SID_A], 1, 1), p5)
        self.assertEqual(p5["walk"], {SID_A: 1, SID_B: 0},
                         "the walk, per session: one load for the look that reached the store, none for the one that skipped (condition 7, the walk's bound)")
        self.assertEqual((p5["gate"], p5["memo"]), ({SID_A: 1, SID_B: 0}, (0, 1)),
                         "the placement gate, per session: the moved parse derives once and checks once, the skipped session not at all "
                         "(condition 7, the gate's bound: at most one check per derive; equal here because the harness caches every parse)")
        self.assertEqual((p5["loads"], p5["writerLoads"], p5["shared"]), (1, 0, {"hit": 2}), "the walk's one and the gate's one, both hits, no hand-off")
        # the walk's and the gate's ceilings, the gate's general bound and its equality are _pass's, on every pass (see there); with
        # no owned record the sweep's bound in _pass holds the sweep to zero on every pass, so this case asserts nothing about it
        self.assertEqual(self.fb.sent, [], "nudges off: nothing injected")
        served = km._PERF_STATS.snapshot()["memos"]["nudgeWalk"]
        self.assertEqual(served["loads"], km._NUDGE_WALK_STATS["loads"], "served under memos.nudgeWalk.loads")
        self.assertEqual(served["loads"], 5, "the five loads the five passes made, cumulative")
        self.assertIs(type(served["loads"]), int, "the served key carries nothing but an integer count")
        block = {"memos": {"nudgeWalk": {"loads": served["loads"]}}}
        self.assertEqual(pp.fold(block), block, "and the export's public fold keeps it as it is: neither denied, coarsened nor folded to other")

    def test_a_look_the_state_gates_end_before_its_store_read_takes_no_load(self):
        """The walk's exactly-one is for a look that reaches the store. A look a state gate ends earlier (here `working`: the
        session is still working by the event model) runs, parses, records a file-keyed row and loads through neither
        mechanism: the walk never reaches its read and the placement gate is never called; the counter stays. Its verdict
        is journaled as a walk gate, a write into the ledger that moves every session's key once, so the second pass
        re-evaluates every look (its line pins that re-arming) and the skip comes on the third pass, which rests on two things
        the second pass did: its look re-recorded its row under the moved key, and its verdict, unchanged, wrote nothing into
        the ledger (_put_walk_gate is write-on-change), so the key stands; the third pass's line names both."""
        km._session_working = lambda turns: True
        p1 = self._pass(NOW)
        self.assertEqual((p1["looks"], p1["parses"], p1["skippedParses"]), (2, 2, 0), p1)
        self.assertEqual(p1["walk"], {SID_A: 0, SID_B: 0},
                         "the walk takes no load on a look a state gate ends before the store read (condition 7, the walk's bound)")
        self.assertEqual((p1["gate"], p1["memo"]), ({SID_A: 0, SID_B: 0}, (0, 0)),
                         "and the placement gate, never reached, checks nothing (condition 7, the gate's bound)")
        self.assertEqual((p1["loads"], p1["writerLoads"], p1["shared"]), (0, 0, {}),
                         "no counter, no writer-door counter and no store counter moves: every look ends before any read (the two elements "
                         "restored by ruling 1 of the reviewer's rulings on the pre-emption, behind _pass's reconciliations and its "
                         "second-bump bound)")
        for sid in SIDS:
            self.assertEqual(self._row(sid)[-1], "working", "the verdict recorded, file-keyed, for %s" % sid[-4:])
        p2 = self._pass(NOW + 5)
        self.assertEqual((p2["looks"], p2["parses"], p2["skippedParses"]), (2, 2, 0),
                         "the first pass journaled each verdict as a walk gate (_put_walk_gate, a write-on-change into the ledger, the "
                         "tenth keyed file), so the second pass re-evaluates every session once")
        p3 = self._pass(NOW + 10)
        self.assertEqual((p3["skippedParses"], p3["walk"], p3["gate"], p3["loads"], p3["writerLoads"], p3["shared"]),
                         (2, {SID_A: 0, SID_B: 0}, {SID_A: 0, SID_B: 0}, 0, 0, {}),
                         "skipped, and still no load through either: the second pass's look ran over the standing row and re-recorded its row "
                         "under the ledger's moved key, and its verdict, unchanged, wrote nothing into the ledger (_put_walk_gate is "
                         "write-on-change), so every key stands and this pass skips; a re-record dropped over a standing row, or made under "
                         "the standing row's key, or an unchanged gate re-written, runs the looks here. Neither the writer door's counter nor "
                         "the store's call counters move either: the two elements were added by the consolidation pass so this skip pass has "
                         "the two "
                         "layers the first case's skip pass has, _pass's second-bump bound first and this line behind it (a forged pair in the "
                         "kernel's skip branch reds the bound here, and with the bound gone this line)")
        # no owned record, so the sweep's bound in _pass holds the sweep to zero on every pass: nothing to assert about it here


class TheSweepIsItsOwnBoundedReader(_WalkHarness):
    """The wake sweep reads the store once per wake record it owns per pass, keeps no memo, and is counted apart from the
    walk and the gate. Its records come from two constituencies, and a case drives each. The first two cases drive the
    UNWALKED one: one wake record for SID_C, a sid that is never alive (so never walked: the sweep's original constituency),
    goes into the ledger before the first pass; the two alive sessions run their first pass as in the first case, and the
    sweep takes exactly one shared load for SID_C on that pass and again on the skip pass. With a store whose nodes lack
    the goal, the read is followed by the inert-record continue (no parse, no writer load, nothing sent). With no store
    file, the shared door falls back into load_goals: one logical read, recorded once by the shared recorder as the
    sweep's and never as a writer call. The third case drives the WEDGE-GATED one: a live record for SID_A, an alive sid
    whose look the walk visits and leaves on a wedge gate (api-error), the reviewer's round-1 refuters probed; past its read
    that sweep reaches the failure stamp, whose real body loads through the writer door, so the case replaces the two
    writers it can reach with recorders and asserts the stamp was reached (see the case)."""

    def _seed_wake_record(self, sid=SID_C, store_file=True):
        """One owned wake record for `sid` in the ledger (the toggle stays off). For SID_C, never alive, its store too:
        with `store_file`, a store whose nodes lack the goal; without, no file at all. An alive sid keeps the store
        setUp seeded (a working top g1, the record's goal)."""
        (jd.STATE / "auto-nudge.json").write_text(json.dumps({"enabled": False, "nudged": {
            sid + ":g1": {"wake": True, "at": NOW - 2 * H, "count": 1, "lastTurnId": "t1"}}}))
        km._autonudge_cache.clear()
        self.owned_records = {sid: 1}
        if sid == SID_C and store_file:
            (jd.GOALDIR / (SID_C + ".json")).write_text(json.dumps(
                {"rompUuid": SID_C, "seq": 1, "placements": {}, "status": {}, "nodes": {}}))

    def _one_sweep_load(self, p, name, handoffs):
        """`handoffs`: the load_goals calls the shared door hands off this pass, read from the door's own counter (goal_io loads,
        `writerLoads`): 1 with no store file (the absent hand-off), 0 with a store whose nodes lack the goal (the read fills or
        hits). The writer recorder's list is _pass's assertion and is empty on every return, so the count is the case-level
        witness that the fallback went through load_goals exactly as the door's own hand-off and the record was inert past it."""
        self.assertEqual(p["sweep"], {SID_C: 1},
                         "%s: the sweep takes exactly one shared load for the one record it owns, and none for the walk's sids" % name)
        self.assertEqual([f for _s, c, f, _ln in p["calls"] if c in SWEEP], [KERNEL_FILE],
                         "%s: the sweep's read is recorded in the kernel's real file (the function is the filter's own, held by _pass's caller "
                         "assertion, and the count by the line above, so the file is the one element that can fail here)" % name)
        self.assertEqual(p["writerLoads"], handoffs,
                         "%s: the shared door's fallback into load_goals is the shared door's own read, counted once under goal_io loads as a "
                         "hand-off and never as a writer call; %d hand-off(s) expected this pass, and the record is inert past the read. This "
                         "line is also the layer behind _pass's second-bump bound on a pass with fills: a forged pair, a corrupt or "
                         "unreadable_journal bump beside a goal_io loads bump with no call through the door, riding beside each genuine fill "
                         "leaves second equal to fills and balances both reconciliations, and reds here as loads over the hand-offs the door "
                         "made. writerLoads %d; the store's call counters %r, its second bumps %r"
                         % (name, handoffs, p["writerLoads"], p["shared"], p["second"]))

    def test_a_store_whose_nodes_lack_the_goal(self):
        self._seed_wake_record(store_file=True)
        p1 = self._pass(NOW)
        self.assertEqual((p1["walk"], p1["gate"], p1["memo"], p1["loads"]), ({SID_A: 1, SID_B: 1}, {SID_A: 1, SID_B: 1}, (0, 2), 2),
                         "the walk and the gate as on any first pass: the record is SID_C's, a sid neither look is about, and the "
                         "counter counts the walk alone (the gate's rule is at most one check per derive; equal here because the harness "
                         "caches every parse)")
        self._one_sweep_load(p1, "p1", handoffs=0)        # the read fills: nothing handed to load_goals
        self.assertEqual(p1["shared"], {"hit": 2, "miss": 3}, "the walk's two fills and the sweep's one, the gate's two hits")
        p2 = self._pass(NOW + 5)
        self.assertEqual((p2["walk"], p2["gate"], p2["loads"]), ({SID_A: 0, SID_B: 0}, {SID_A: 0, SID_B: 0}, 0),
                         "the looks skip: nothing of theirs moved")
        self._one_sweep_load(p2, "p2", handoffs=0)        # the sweep keeps no memo: one read per owned record per pass
        self.assertEqual(p2["shared"], {"hit": 1}, "the sweep's read alone, a hit on the store it filled last pass")
        self.assertEqual(self.fb.sent, [], "nothing sent: the node is gone, so the record is inert and the sweep continues past it")

    def test_no_store_file(self):
        self._seed_wake_record(store_file=False)
        p1 = self._pass(NOW)
        self._one_sweep_load(p1, "p1", handoffs=1)        # no store file: the door hands the read to load_goals, once
        self.assertEqual(p1["shared"], {"hit": 2, "miss": 2, "absent": 1}, "the sweep's read is the absent case: one call, one counter")
        p2 = self._pass(NOW + 5)
        self._one_sweep_load(p2, "p2", handoffs=1)
        self.assertEqual(p2["shared"], {"absent": 1})
        self.assertEqual(self.fb.sent, [], "nothing sent: the fresh store has no node for the record")

    def test_a_wedge_gated_alive_sid_the_walk_visited(self):
        """The sweep's other constituency: a live wake record for SID_A, an alive sid the walk visits and leaves on a WEDGE
        gate. _api_error answers with text, so every look ends at "api-error" before its parse and its store read, and the
        walk journals that gate (a wedge gate has no session-produced ending event while a wake is dead, so the sweep acts
        on the record now rather than leaving it with the walk). The walk and the gate load nothing on either pass, and the
        sweep takes exactly one shared load for SID_A per pass, recorded as _awaiting_wake_outcomes's in the kernel's file.
        Past the read this sweep reaches the failure stamp (_nudge_response_ready over the fixture turns: no response
        segment and a record without armAtoms, so resp is None). _mark_nudge_failed's real body loads through the writer
        door twice at its write moment and stamps the record failed, which the sweep then no longer owns; so this case
        replaces it, and _file_wake_answer (the answered leg's writer), with recorders (CASE_KM, restored by the cleanup),
        asserts the stamp was reached for the record with wake=True on each pass, and the record stays live so the sweep
        reads it again on the second pass. The two writers are among the store's other readers the reference's jobs block
        names, loading by design at their write moments; the census is about helpers that should read nothing."""
        km._api_error = lambda path: "API Error: 529 overloaded"
        reached = []
        km._mark_nudge_failed = lambda gid, ev_t=None, wake=False: reached.append(("failed", gid, wake)) or None
        km._file_wake_answer = lambda sid, gid, now: reached.append(("answered", gid)) or False
        self._seed_wake_record(sid=SID_A)
        gid = SID_A + ":g1"
        p1 = self._pass(NOW)
        p2 = self._pass(NOW + 5)
        for name, p in (("p1", p1), ("p2", p2)):
            self.assertEqual((p["looks"], p["parses"], p["skippedParses"], p["wakeOnly"]), (2, 0, 0, 2),
                             "%s: every look runs and ends at the wedge gate before its parse, so nothing is recorded to skip" % name)
            self.assertEqual((p["walk"], p["gate"], p["memo"], p["loads"]), ({SID_A: 0, SID_B: 0}, {SID_A: 0, SID_B: 0}, (0, 0), 0),
                             "%s: a look the wedge gate ends before its store read loads through neither mechanism, and the counter "
                             "stays (condition 7, both bounds)" % name)
            self.assertEqual(p["sweep"], {SID_A: 1}, "%s: the sweep takes exactly one shared load for the wedge-held record of an alive sid "
                                                       "the walk visited, and none for SID_B, which owns no record" % name)
            self.assertEqual([f for _s, c, f, _ln in p["calls"] if c in SWEEP], [KERNEL_FILE],
                             "%s: the sweep's read is recorded in the kernel's real file (the function is the filter's own, held by _pass's caller "
                             "assertion, and the count by the line above, so the file is the one element that can fail here)" % name)
            self.assertEqual(p["writerLoads"], 0, "%s: the stamp is a recorder here and the sweep's read fills or hits, so the writer door's "
                                                  "counter stays: no writer load, no hand-off" % name)
            self.assertEqual(p["parsedSids"], [SID_A], "%s: the sweep parses the record's session once past its read" % name)
        self.assertEqual(p1["shared"], {"miss": 1}, "p1: the sweep's read fills SID_A's store, which no look read")
        self.assertEqual(p2["shared"], {"hit": 1}, "p2: the sweep keeps no memo, so it reads again: a hit on its own fill")
        self.assertEqual(reached, [("failed", gid, True)] * 2,
                         "the sweep reached the failure stamp for the record, wake=True, once per pass, and the answered leg's writer never")
        gates = km._auto_nudge_data().get("walkGates", {})
        self.assertEqual({s[-4:]: g.get("gate") for s, g in gates.items()}, {"0001": "api-error", "0002": "api-error"},
                         "the walk journaled the wedge gate for both sids: the class of gate whose records the sweep owns")
        self.assertEqual(self.fb.sent, [], "nothing sent")


class TheDoorBumpsAtMostOneSecondKeyPerCall(_WalkHarness):
    """The at-most-one premise of the second-bump bound by execution (review round 4, tests-2, regression-2 and extra4-1; the
    roster pin in TheCountersOneSite holds it by AST): one call of the door on a fill road that takes a second bump, and the
    second bump it takes is exactly one. The road is the corrupt one: a store whose bytes do not parse, written for SID_C (never
    alive, so never walked, and no store of its own but the one a case writes), read once through jd.load_goals_shared directly,
    under the harness's recorders (setUp stands them) and outside any pass (no tick runs, so the read is this method's and the
    recorder names it so). The door bumps miss (no entry stood), then corrupt (_disk_parse raised) and hands the read to
    load_goals, which quarantines the bytes (one stderr line, captured here, and one store-quarantined row under the rebound
    judge-errors file) and answers the fresh store; one goal_io loads bump is the hand-off, and the writer recorder records
    nothing (the hand-off is skipped by code identity). The roads not driven: unreadable_journal needs an OSError out of the
    journal's open (a directory at the path reads as no journal, and a mode change is unreliable under root); dup and refuse need
    a concurrent fill, or an archive write between the door's two archive-key reads, hooks on judge names this harness does not
    own. A second second bump on the corrupt road spelled outside the two spellings the roster pin reads
    (`_SHARED_STATS.__setitem__`, say) reds this case's second-key line and not the pin."""

    def test_a_corrupt_store_read_once_through_the_door_bumps_miss_once_corrupt_once_and_hands_off_once(self):
        path = jd.GOALDIR / (SID_C + ".json")
        path.write_text("{not json")
        s0, g0 = jd.shared_store_stats(), jd.goal_io_stats()["loads"]
        self.calls.clear(); self.writer.clear()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            store = jd.load_goals_shared(SID_C)
        s1, g1 = jd.shared_store_stats(), jd.goal_io_stats()["loads"]
        calls = {k: s1[k] - s0[k] for k in SHARED_CALL_KEYS if s1[k] != s0[k]}
        second = {k: s1[k] - s0[k] for k in SHARED_SECOND_KEYS if s1[k] != s0[k]}
        self.assertEqual([(c, f) for _s, c, f, _ln in self.calls], [(self._testMethodName, os.path.basename(os.path.realpath(__file__)))],
                         "one call through the door, this method's, recorded by the shared recorder in this file: %r" % self.calls)
        self.assertEqual(calls, {"miss": 1}, "the one call moved one call key, miss: no entry stood for the path, so the read entered the fill "
                                             "road; the call counters' delta: %r" % calls)
        self.assertEqual(second, {"corrupt": 1},
                         "and exactly one second key, corrupt, once: the bytes did not parse, and the door left the fill road right after that "
                         "bump (the at-most-one premise of the bound's derivation, witnessed per call; the roster pin's AST clause reads two "
                         "bump spellings, and this line reads the counters, so a second bump spelled another way reds here); the second keys' "
                         "delta: %r" % second)
        self.assertEqual(g1 - g0, 1, "the corrupt bump is a hand-off: one load_goals call, one goal_io loads bump, the quarantine and the fresh "
                                     "store answered by it; loads delta %d" % (g1 - g0))
        self.assertEqual(self.writer, [], "the hand-off is the shared door's own read, skipped by code identity, so the writer recorder recorded "
                                          "nothing: %r" % self.writer)
        self.assertEqual((store.get("rompUuid"), store.get("nodes")), (SID_C, {}),
                         "the fresh store came back: the bytes were moved aside and nothing was cached for the path")
        self.assertFalse(path.exists(), "the unparseable file was moved aside, so the path reads as absent now")
        aside = [p.name for p in jd.GOALDIR.iterdir() if p.name.startswith(SID_C + ".json.corrupt-")]
        self.assertEqual(len(aside), 1, "one sidecar holds the bytes: %r" % aside)
        self.assertIn("could not be parsed", err.getvalue(), "the quarantine's one stderr line, captured: %r" % err.getvalue())
        rows = [json.loads(ln) for ln in jd.ERRORS.read_text().splitlines()]
        self.assertEqual([(r["err"], r["fsid"]) for r in rows], [("store-quarantined", SID_C)],
                         "and its one store-quarantined row under the rebound judge-errors file: %r" % rows)


class TheRecorderNamesTheAsker(unittest.TestCase):
    def test_a_load_inside_a_stand_in_wrapper_is_named_for_the_wrapper_and_its_hand_off_for_the_caller(self):
        """_caller's contract over a stand-in, not the composition of the real boundary set (setUp's guard over the judge's three
        wrappers holds that): a boundary frame is stepped over only while it sits at its pass-through call. `wrapper` is the
        stand-in, two body lines: a call to `other`, off the hand-off line, and the hand-off `return loader()`; both callees
        record their asker through _caller with `wrapper` as the one boundary. The load written in the wrapper's own body is
        named for the wrapper, in this file; the hand-off is named for this method, the wrapper's caller. The (function, file)
        pairs are asserted and not the lines, so a reformatting of this body changes nothing (review round 2, tests-2: the
        conditional step-over landed with no case that failed without it; stepped over unconditionally, the in-body call is
        named for this method as well, which is the red this case gives)."""
        seen = []

        def wrapper(loader):
            other()                                       # a load written in the wrapper's own body, off the hand-off line
            return loader()                               # the hand-off: the one line the recorder steps over

        boundary = ((wrapper.__code__, _pass_through_lines(wrapper, "loader")[0]),)

        def other():
            seen.append(("in the body",) + _caller(inspect.currentframe(), boundary))

        def loader():
            seen.append(("the hand-off",) + _caller(inspect.currentframe(), boundary))

        wrapper(loader)
        here = os.path.basename(os.path.realpath(__file__))
        self.assertEqual([(what, fn, f) for what, fn, f, _ln in seen],
                         [("in the body", "wrapper", here), ("the hand-off", self._testMethodName, here)],
                         "a load inside a stand-in wrapper's body is named for the wrapper, its hand-off for the wrapper's caller: %r" % seen)


class TheAgreementCheckSpansSetUp(unittest.TestCase):
    def test_a_stub_placed_right_after_the_rebind_is_refused(self):
        """The agreement check covers the whole setUp (review round 2, correctness-2 and tests-1: with the snapshot taken after the
        cache clears, a stub above it for a name outside both lists escaped the check, the census and the execution witness). A
        throwaway harness subclass places a stub in the region the old snapshot missed, right after the rebind, through the
        _after_rebind hook, on a CASE_KM name so the cleanup puts the real one back; its setUp must raise the agreement check's
        AssertionError naming the stub. The cleanups run whether or not it raised, as unittest's would."""
        class _Probe(_WalkHarness):
            def _after_rebind(self):
                km._session_working = lambda turns: False

        probe = _Probe(methodName="setUp")
        try:
            with self.assertRaises(AssertionError) as cm:
                probe.setUp()
        finally:
            probe.doCleanups()
        self.assertIn("_session_working", str(cm.exception), "the check names the stub placed right after the rebind")

    def test_a_stub_placed_between_the_first_snapshot_and_the_rebind_is_refused(self):
        """The judge half of the check reads the names jd._rebind_state moves as the diff across that call alone, against a snapshot
        taken at the rebind (the build's verifier pass after the round-2 fixes: read against setUp's first snapshot, a judge stub
        placed between that snapshot and the
        rebind was filed as the rebind's, subtracted, and escaped the check with the module green). A throwaway harness subclass
        places a new-identity pass-through on a judge name outside both lists there, through the _before_rebind hook, restoring the
        real one by its own cleanup; setUp must raise the agreement check's AssertionError naming it."""
        class _Probe(_WalkHarness):
            def _before_rebind(self):
                real = jd._journal_key
                self.addCleanup(setattr, jd, "_journal_key", real)
                jd._journal_key = lambda fsid: real(fsid)

        probe = _Probe(methodName="setUp")
        try:
            with self.assertRaises(AssertionError) as cm:
                probe.setUp()
        finally:
            probe.doCleanups()
        self.assertIn("_journal_key", str(cm.exception), "the check names the stub placed between the first snapshot and the rebind")


class TheCountersOneSite(unittest.TestCase):
    def _the_named_def(self, label, obj, name):
        """The object a census is about to scan is the def named `name`, by the name inspect.unwrap reaches and by the def its
        source parses to (ruling 3 of the reviewer's rulings on the pre-emption, for the replaced-helpers census; review round 4,
        correctness-3, for the walk census and the gate scan, which read km._auto_nudge_session and km._nudge_look_gated with no
        identity line: the gate decorator's wraps dropped red the walk census's site count 0 against 1, a true red with a false cause,
        and a decorator without wraps on the factory with a load in the gate's body left the gate scan green, reading the wrapper).
        inspect follows __wrapped__ only through functools.wraps, so behind a decorator without it a census reads the wrapper's source
        and answers no site for a body it never read."""
        first = ast.parse(textwrap.dedent(inspect.getsource(obj))).body[0]
        self.assertEqual((inspect.unwrap(obj).__name__, type(first).__name__, getattr(first, "name", None)), (name, "FunctionDef", name),
                         "%s: the object the census scans is the named helper itself, by the name inspect.unwrap reaches and by the def "
                         "its source parses to; inspect follows __wrapped__ only through functools.wraps, so behind a decorator without it "
                         "the census would read the wrapper's source and answer no site for a body it never read: unwrap reaches %r and "
                         "the source's first statement is a %s named %r"
                         % (label, inspect.unwrap(obj).__name__, type(first).__name__, getattr(first, "name", None)))

    def test_the_walk_has_one_shared_load_site_and_the_counter_is_bumped_beside_it(self):
        """A census over the look's own source (the gate decorator unwraps): one shared load by either spelling of the shared
        door (`jd.load_goals_shared` is a prefix of both), read from the AST (_loader_sites: a name in code is a site, a
        mention in a comment, a docstring or a string is not), the counter bumped on the line after it so the two cannot
        drift, and the gate around the look reads no store (a skipped look needs no data), scanned by the same rule. The bump
        is read as a statement too, an augmented `+= 1` on `_NUDGE_WALK_STATS["loads"]`, never as a line of text (review round
        2, correctness-3: a comment quoting the statement counted as a second bump). Each object is first checked to be the
        named def (_the_named_def; review round 4, correctness-3): the look behind its gate decorator, whose wraps dropped red the
        site count with the opposite cause, and the gate factory, whose scan read a decorator's wrapper and answered no site."""
        self._the_named_def("_auto_nudge_session", km._auto_nudge_session, "_auto_nudge_session")
        at = [i for i, _ln in _loader_sites(km._auto_nudge_session, "jd.load_goals_shared")]
        self.assertEqual(len(at), 1, "one shared load in the walk's look, by either spelling of the shared door: a second call site is "
                                     "a second load per look (condition 7, the walk's bound)")
        bump = _bump_sites(km._auto_nudge_session)
        self.assertEqual(len(bump), 1, "the counter is bumped once, by one `_NUDGE_WALK_STATS[\"loads\"] += 1` statement")
        self.assertEqual(bump[0], at[0] + 1, "on the line after the load")
        self._the_named_def("_nudge_look_gated", km._nudge_look_gated, "_nudge_look_gated")
        gated = [ln.strip() for _i, ln in _loader_sites(km._nudge_look_gated, "load_goals")]
        self.assertEqual(gated, [], "the gate around the look reads no store: a skipped look loads through neither mechanism: %s" % "; ".join(gated))
        self.assertIn("loads", km._NUDGE_WALK_STATS, "the counter is a key of the served block")

    def test_the_shared_doors_bump_roster_is_the_reconciliations_and_its_second_bumps_sit_below_the_fills(self):
        """The second-bump bound in _pass is derived from load_goals_shared's body; this pin reads that body (the AST of the
        judge's own door, its identity checked as setUp checks it) so the derivation cannot go stale unnoticed, in three clauses,
        one per premise the bound rests on. The rosters: every counter the door bumps, by `_shared_bump("<key>")` or
        `_SHARED_STATS["<key>"] += 1`, is a call key or a second key and every key of both rosters is bumped there, so a new key
        in the door reds here before it slips past the reconciliations. The order: every second-key bump sits below every call-key
        bump in the body (the fill road follows the miss or compare_miss bump). The at-most-one: for every second-key bump, the
        innermost statement list holding it (a body, an orelse, a finalbody or a handler's body; a Try's handlers are ExceptHandler
        nodes and not statements, so no region is read twice) holds exactly one second-key bump over the full subtrees of its
        statements (a bump nested under an If in a later statement counts) and ends in a Return or a Raise, so no path through the
        door bumps two; the clean door has a cleanup call between a bump and its return, so the predicate is the list's last
        statement and not the bump's next. From the same lists the fill road's entry keys are derived: the call keys whose list does
        not end in a Return or a Raise fall through into the fill, and they must be SHARED_FILL_KEYS, which _pass sums as the bound's
        right-hand side, so a call key that starts falling through, or one of these that stops, reds here rather than leaving _pass
        summing the wrong keys. Review round 4, tests-2, regression-2 and extra4-1: the pin read the rosters and the order, the
        at-most-one was held by reading the body, and a second second-key bump on one road or a new fill key left the module green
        with the bound no longer following from the body. The at-most-one is pinned by execution as well, one call on the corrupt
        road, in TheDoorBumpsAtMostOneSecondKeyPerCall. Added in the consolidation pass beside ruling 1's bound, the fixer's addition
        beyond the ruling's letter."""
        door = jd.load_goals_shared
        self.assertEqual((door.__code__.co_name, os.path.basename(os.path.realpath(door.__code__.co_filename))), ("load_goals_shared", JUDGE_FILE),
                         "the door read here is the judge's own (a harness case's recorder is gone by its cleanup)")
        tree = ast.parse(textwrap.dedent(inspect.getsource(door)))

        def bump_key(n):
            """The key a bump node moves, `_shared_bump("<key>")` or `_SHARED_STATS["<key>"] += ...`; None for any other node."""
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "_shared_bump" and n.args and isinstance(n.args[0], ast.Constant):
                return n.args[0].value
            if (isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Subscript) and isinstance(n.target.value, ast.Name)
                    and n.target.value.id == "_SHARED_STATS" and isinstance(n.target.slice, ast.Constant)):
                return n.target.slice.value
            return None

        def stmt_key(s):
            """The key a bump STATEMENT moves: an Expr whose value is the _shared_bump call, or the AugAssign itself."""
            return bump_key(s.value if isinstance(s, ast.Expr) else s)

        bumps = [(n.lineno, bump_key(n)) for n in _walk(tree) if bump_key(n) is not None]
        self.assertEqual({k for _ln, k in bumps}, set(SHARED_CALL_KEYS) | set(SHARED_SECOND_KEYS),
                         "the keys load_goals_shared bumps are exactly the call keys the shared reconciliation sums and the second keys the "
                         "second-bump bound sums (a key here and in neither roster is a bump no reconciliation reads; a key in a roster and "
                         "not here is a bound over a counter the door no longer moves): %r" % sorted(bumps))
        self.assertLess(max(ln for ln, k in bumps if k in SHARED_CALL_KEYS), min(ln for ln, k in bumps if k in SHARED_SECOND_KEYS),
                        "every second-key bump sits below every call-key bump in the door's body (the fill road follows the miss or "
                        "compare_miss bump), the structure the bound in _pass rests on; the bumps by line: %r" % sorted(bumps))
        # the at-most-one, over every statement list of the door: each list-valued field whose members are all statements (a body, an
        # orelse, a finalbody, a handler's body; Try.handlers holds ExceptHandler nodes, so no try region is collected twice)
        blocks = [val for node in _walk(tree) for _field, val in ast.iter_fields(node)
                  if isinstance(val, list) and val and all(isinstance(s, ast.stmt) for s in val)]
        holding, fill_entries = 0, set()
        for blk in blocks:
            direct = [k for k in (stmt_key(s) for s in blk) if k is not None]
            if any(k in SHARED_SECOND_KEYS for k in direct):
                holding += 1
                deep = [(x.lineno, bump_key(x)) for s in blk for x in _walk(s) if bump_key(x) is not None]
                second = [(ln, k) for ln, k in deep if k in SHARED_SECOND_KEYS]
                self.assertEqual(len(second), 1,
                                 "the statement list holding the second-key bump at line %d holds exactly one second-key bump over the full "
                                 "subtrees of its statements, so no path through it bumps two (a call bumps at most one second key, the premise "
                                 "the bound's derivation rests on; two here and the bound no longer follows from the body): %r"
                                 % (second[0][0], second))
                self.assertIsInstance(blk[-1], (ast.Return, ast.Raise),
                                      "and ends in a Return or a Raise, so the path leaves the door after its one second bump (the clean door "
                                      "has a cleanup call between the bump and its return, which is why the predicate is the list's last "
                                      "statement and not the bump's next); the list holding the bump at line %d ends in a %s"
                                      % (second[0][0], type(blk[-1]).__name__))
            if any(k in SHARED_CALL_KEYS for k in direct) and not isinstance(blk[-1], (ast.Return, ast.Raise)):
                fill_entries.update(k for k in direct if k in SHARED_CALL_KEYS)
        self.assertEqual(holding, sum(1 for _ln, k in bumps if k in SHARED_SECOND_KEYS),
                         "every second-key bump is a statement of some list (an Expr of the call, or the AugAssign) and each list read above "
                         "held one, so the clause read every bump: %d list(s) against %d bump(s), by line %r"
                         % (holding, sum(1 for _ln, k in bumps if k in SHARED_SECOND_KEYS), sorted(bumps)))
        self.assertEqual(fill_entries, set(SHARED_FILL_KEYS),
                         "the fill road's entry keys, the call keys whose bump falls through into the fill (the statement list holding it does "
                         "not end in a Return or a Raise), are SHARED_FILL_KEYS, the keys _pass sums as the bound's right-hand side: derived "
                         "%r against %r (a call key that starts falling through, or one of these that stops, changes the bound's derivation "
                         "and the tuple with it)" % (sorted(fill_entries), sorted(SHARED_FILL_KEYS)))

    def test_the_replaced_helpers_sources_load_no_store(self):
        """The road limit as a check: the fixture replaces the callables in REPLACED_KM (less the two data names), REPLACED_JD
        and Sessions.backend_for, so a loader planted in any of their real bodies never runs under the harness and the
        execution witness cannot see it; this scan of each real source for either door's name (by the AST, _loader_sites, on
        every interpreter) is the only witness for those bodies. One level deep, the helper's own source: _session_awaiting reaches two bare-door
        readers (_owned_yield_why and _session_stamp_read) only under stamp=True, which the walk's call does not pass, so
        the walk's road does not reach them; a helper the fixture does not replace is covered by execution instead. Each
        object is first checked to be the named helper, by the name inspect.unwrap reaches and by the def its source parses to
        (ruling 3 of the reviewer's rulings on the pre-emption): inspect follows __wrapped__ only through functools.wraps, so behind
        a decorator without it the census
        would read the wrapper's source and answer no site for a body it never read."""
        targets = ([(k, getattr(km, k)) for k in REPLACED_KM if k not in REPLACED_DATA]
                   + [("jd." + k, getattr(jd, k)) for k in REPLACED_JD]
                   + [("Sessions.backend_for", km.Sessions.backend_for)])
        self.assertEqual(len(targets), 21, "the census covers every replaced callable")
        for label, obj in targets:
            self._the_named_def(label, obj, label.split(".")[-1])
            hits = [ln.strip() for _i, ln in _loader_sites(obj, "load_goals")]
            self.assertEqual(hits, [], "%s: a loader planted in a replaced helper never runs under the fixture, so this scan is the only "
                                       "witness for its body: %s" % (label, "; ".join(hits)))

    def test_no_other_name_for_a_loader_is_born_in_the_kernel_or_the_judge(self):
        """The census reads a body. A loader that reaches a body under another name (a module-level `_lgs = jd.load_goals_shared`,
        a `from romp_judge import load_goals_shared as _lgs` at module level, a dict of callables, a functools.partial, a closure
        variable, a parameter) or through a string constant (getattr, exec, eval, compile, operator.attrgetter, __getattribute__,
        importlib, `vars(jd)[...]`, `jd.__dict__[...]`, `jd.__dict__.get(...)`) is no site in that body, and inside a replaced
        helper nothing else sees it (the consolidation pass: every such form scanned as no site on 3.10 through 3.13 while a recorder
        saw the real load; a verifier of that pass then planted the two subscript forms and the dict read as a real load in
        _closer_settled, and the first cut of this pin, which read a dynamic lookup's arguments alone, let all three pass). So the
        kernel and the judge are each read once, whole, where any such name would be born, by _loader_births: in the kernel every
        reference to a loader by attribute is the callee of a call, no alias, bare name, parameter or keyword spells one, no string
        constant spells a door whole wherever it appears and whatever receives it, and none containing the name reaches a dynamic
        lookup, a dict read or a subscript key; in the judge every bare loader name is the callee of a call or the loader a
        boundary wrapper hands to _or_fault, the four doors are defined once each and undecorated, and the same list of births is
        empty (its three error strings that mention a door contain the name and spell none whole, so the value rule reports them
        not). The population read is asserted too, so an empty file or a moved door cannot pass as clean: the kernel calls the
        judge's four doors by `jd.<door>` and no other spelling, at exactly the call sites per spelling the pin asserts (58 at the
        head of the round-4 fixes, 27 through load_goals, 9 through load_goals_or_fault, 7 through load_goals_shared and 15 through
        load_goals_shared_or_fault; review round 4, tests-3: the figure was prose and the case asserted the set of spellings, which a
        kernel that kept one call site per spelling passed; the dict is pinned rather than the sum, since a swap between doors moves
        two counts and the sum not at all, so an upstream fold that adds, removes or re-doors a kernel call site reds here by design
        and the number moves with a re-read of the reference's other-readers clause or of a bound), and the two hand-offs are the two
        outer wrappers'. The limit that stays: a name assembled at run time from pieces none of which spells a door whole is spelled
        in no constant the pin reads (the `assembled` class of _LIMITS, which the enumeration holds on that side). Review round 4,
        correctness-1, tests-1 and extra6-1: the string class was stated closed by a list of receivers, nine lookups, four dict
        reads and a subscript slice, and six working doors on no list passed the pin with a real load in a replaced helper's body;
        the pin keys on the door's spelling now, the closed set, and the receivers need no listing."""
        born, called, defs, handoffs = _loader_births(Path(os.path.realpath(km.__file__)), judge=False)
        self.assertEqual(born, [], "%s: a loader bound to another name, or reached through a string, is a body the census cannot read; every "
                                   "reference to a loader in the kernel is the callee of a call spelled jd.<door>(...), so no other name is born, "
                                   "no string constant spells one whole, wherever it appears and whatever receives it, and none containing the "
                                   "name reaches a dynamic lookup, a dict read or a subscript key: %s"
                                   % (KERNEL_FILE, "; ".join("line %d, %s" % b for b in born)))
        self.assertEqual(called, {"jd.load_goals": 27, "jd.load_goals_or_fault": 9, "jd.load_goals_shared": 7, "jd.load_goals_shared_or_fault": 15},
                         "%s: the kernel calls the judge's four doors by attribute and no other loader spelling, at exactly these call sites per "
                         "spelling, 58 in all: the population the pin above read, so an empty file, a file that is not the kernel's or a kernel "
                         "that kept one call site per spelling and lost the rest cannot pass as clean. A change here is a new, a removed or a "
                         "re-doored call site (a swap between doors moves two counts and the sum not at all, which is why the dict is pinned and "
                         "not the sum), which needs the reference's other-readers clause or a bound re-read before the number moves; a fifth "
                         "spelling is a new door or a new base, which needs a recorder or a bound before this dict grows: %r"
                         % (KERNEL_FILE, {k: v for k, v in sorted(called.items())}))
        self.assertEqual((defs, handoffs), ({}, []), "%s: the kernel defines no loader and hands none to _or_fault" % KERNEL_FILE)
        born, called, defs, handoffs = _loader_births(Path(os.path.realpath(jd.__file__)), judge=True)
        self.assertEqual(born, [], "%s: the judge reaches its own doors by bare name as the callee of a call, or hands one to _or_fault from a "
                                   "boundary wrapper, and gives them no other name (no alias, parameter, keyword, attribute or decorator; no string "
                                   "constant spells one whole, wherever it appears and whatever receives it, and none containing the name reaches "
                                   "a dynamic lookup, a dict read or a subscript key): %s"
                                   % (JUDGE_FILE, "; ".join("line %d, %s" % b for b in born)))
        self.assertEqual(defs, dict.fromkeys(("load_goals", "load_goals_or_fault", "load_goals_shared", "load_goals_shared_or_fault"), 1),
                         "%s: the four doors are defined once each (a fifth def named like a loader is a new door, which needs a recorder or a "
                         "bound): %r" % (JUDGE_FILE, defs))
        self.assertEqual(set(called), set(defs), "%s: the judge calls its four doors and no other loader spelling: %r" % (JUDGE_FILE, sorted(called)))
        self.assertEqual(handoffs, [("load_goals_or_fault", "load_goals"), ("load_goals_shared_or_fault", "load_goals_shared")],
                         "%s: the two outer boundary wrappers hand their loader to _or_fault and no other function does (the recorder steps over "
                         "exactly those frames at their hand-off lines; a third wrapper would be a caller the recorder names for itself): %r"
                         % (JUDGE_FILE, handoffs))

    def test_the_census_reads_code_not_prose_and_sees_a_call_inside_an_f_string_on_every_interpreter(self):
        """The rule the censuses share, exercised (review round 2, tests-3: no scanned source carried a mention of a loader, so
        the rule was held by no assertion), over six local samples that are never called (inspect reads them; no store is
        touched, no recorder window entered and the import never runs): the loader named in a docstring, a string literal and a
        comment and nowhere in code is no site; one call is one site; one call inside an f-string is one site on every
        interpreter (correctness-1: the tokenizer gives 3.10 and 3.11 one STRING token for a whole f-string and 3.12 and later
        its FSTRING_* parts, and a census over blanked tokens read the call on the later ones only; the AST census does not
        consult the tokenizer); a loader imported under an alias is one site, the import line, and the alias's call is not
        (the build's verifier pass after the round-2 fixes: over Name and Attribute alone, an import alias inside a replaced helper's
        real body was no site and the module stayed green); a loader called by bare name is one site, its call line (review round 3,
        extra5-1: the census claims three node kinds, Name, Attribute and alias, and the samples held Attribute and alias, so the Name
        branch was held here by nothing; with it dropped, a bare-name loader planted in a replaced judge helper escaped the census,
        and at the head of the build's verifier pass after the round-2 fixes the module stayed green; the enumeration's F01 has held
        the branch since the consolidation pass, and this sample holds it in the case that states the rule)."""
        def mentions_only(sid):
            """The look's read is jd.load_goals_shared_or_fault(sid), named here and in no code line of this body."""
            note = "jd.load_goals_shared_or_fault(sid) in a string literal"   # jd.load_goals_shared_or_fault(sid) in a comment
            return note

        def one_call(sid):
            store, fault = jd.load_goals_shared_or_fault(sid)
            return store, fault

        def in_fstring(sid):
            return f"{jd.load_goals_shared_or_fault(sid)}"

        def under_an_alias(sid):
            from romp_judge import load_goals_shared as _lgs      # the import is the site; the call below is a Name of another spelling
            return _lgs(sid)

        def via_getattr(sid):
            return getattr(jd, "load_goals_shared")(sid)         # the loader reached through a string: spelled in no Name, Attribute or alias

        def bare_name(sid):
            return load_goals_shared(sid)                        # a bare Name, the judge's own spelling of its door: bound nowhere in this
            #                                                      module and never called, so the name never resolves; the census reads source

        self.assertEqual(_loader_sites(mentions_only, "load_goals"), [],
                         "a loader named in a docstring, a string literal or a comment is not a site")
        self.assertEqual(len(_loader_sites(one_call, "load_goals")), 1, "one call is one site: %r" % _loader_sites(one_call, "load_goals"))
        self.assertEqual(len(_loader_sites(in_fstring, "load_goals")), 1,
                         "a call inside an f-string is one site on every interpreter, this one %s: %r"
                         % (sys.version.split()[0], _loader_sites(in_fstring, "load_goals")))
        alias_sites = _loader_sites(under_an_alias, "load_goals")
        self.assertEqual([ln.split()[0] for _i, ln in alias_sites], ["from"],
                         "a loader imported under an alias is one site, the import line, and the alias's call is not: %r" % alias_sites)
        bare_sites = _loader_sites(bare_name, "load_goals")
        self.assertEqual([ln.split()[0] for _i, ln in bare_sites], ["return"],
                         "a loader called by bare name is one site, its call line, through the census's ast.Name branch (review round 3, "
                         "extra5-1: the samples held the Attribute and alias branches and this branch was held here by nothing): %r" % bare_sites)
        self.assertEqual(_loader_sites(via_getattr, "load_goals"), [],
                         "a loader reached through a string, getattr here (exec, eval, compile, operator.attrgetter, vars(), __dict__ and "
                         "__getattribute__ the same, and getattr on an importlib.import_module result), is spelled in no Name, Attribute or "
                         "alias node and is outside the census: the limit _loader_sites's docstring states, held by the census reading code and "
                         "not strings. The kernel-wide pin refuses the constant in the kernel and the judge: one spelling a door whole wherever "
                         "it appears and whatever receives it, and one containing the name where it reaches those callables, a dict read or "
                         "a subscript key; a name assembled at run time from pieces none of which spells a door whole is outside that pin as "
                         "well (the consolidation pass and the round-4 fixes; the enumeration holds both classes on their sides): %r"
                         % _loader_sites(via_getattr, "load_goals"))


# The census's form enumeration (the consolidation pass). One sample module per form, written to a file and imported so inspect can read
# it, with a stub judge standing in for the real one (its four loaders take any argument and return it, so a decorator form's
# def-time call is harmless and no store is touched; the samples are otherwise never called). Each row of _LOADER_FORMS: the
# form's id and description, the module body, the target's dotted name, the interpreter it needs (None: every one; a gated form
# fails to compile below it, which the test checks), the sites _loader_sites answers for the needle "load_goals" as line indices
# into the target's source, the site count for the needle "jd.load_goals_shared", and, for a form the census answers no site
# for, the stated limit it falls under (_LIMITS). The expectations are the lens's, read on 3.10 through 3.13 and identical there
# but for the three gated forms, plus four rows a consolidation-pass verifier's forms added (F07c, F07d, F07e, F30d: the string
# class split by what the kernel-wide pin refuses) and three rows the round-3 fixes added (F61, F62, F63: the t-string and the
# type-parameter nodes that 3.14 and 3.12 add, so the grammar table's newest classes are read by the census and not only listed);
# the round-4 fixes moved F07d from the assembled class to the string class and F45 from none to string (the pin refuses a constant
# spelling a door whole wherever it appears, so the name bound to a variable is read where it is bound and a dict key spelled whole
# is read under its Dict) and added ten rows (F07f, F07g, F64 to F67: the f-string handed to getattr with and without a piece
# interpolated, and the four doors the round found on no list, methodcaller, itemgetter over vars(jd), a partial of getattr and a
# match-mapping key; F30e to F30h: the subscript keys the slice walk reaches, an f-string, a conditional, a walrus and a
# concatenation that keeps the needle in one piece). The bodies' `romp_judge` is the stub's name when loaded. For a form of the string or
# the assembled class the enumeration also runs the kernel-wide pin, _loader_births, over the form's file and expects a birth from
# the first and none from the second, so each class is held on the side it falls.
_STUB_JUDGE, _STUB_KERNEL = "romp_judge_c7pin_stub", "romp_kernel_c7pin_stub"
_FORM_PRE = ("import functools, importlib, operator, sys\n"
             "import %s as jd\n"
             "import %s as km\n"
             "from typing import Callable\n"
             "_NUDGE_WALK_STATS = {'loads': 0}\n"
             "X = 3\n" % (_STUB_JUDGE, _STUB_KERNEL))
_LIMITS = {
    "string": "a loader reached through a string CONSTANT (getattr, exec, eval, compile, operator.attrgetter, __getattribute__, getattr on "
              "an importlib.import_module result, vars(jd)[...], jd.__dict__[...], jd.__dict__.get(...), the name bound to a variable "
              "first, a dict key spelled whole, methodcaller, itemgetter over vars(jd), a partial of getattr, a match-mapping key, an "
              "f-string of the whole name, or any receiver nobody listed): the limit _loader_sites states, refused by the kernel-wide "
              "pin, _loader_births: a constant spelling a door whole wherever it appears and whatever receives it, and a constant "
              "containing the name where it reaches a listed lookup, a dict read or a subscript key; the enumeration runs that pin over "
              "each form of this class and expects a birth",
    "assembled": "a loader reached through a name assembled at run time from pieces none of which spells a door whole (a concatenation "
                 "or a format that splits the needle, an f-string interpolating a piece): spelled in no node and in no constant either "
                 "census reads, so outside every static "
                 "pin in this module, the kernel-wide pin included; the enumeration runs that pin over each form of this class and expects "
                 "no birth, so the class is held on the side it falls",
    "outside": "a loader that reaches the scanned body under a name bound outside it (a module-level alias, an import alias at module "
               "level, a module-level dict or partial, a closure variable, a parameter, a class or instance attribute when only the "
               "method is scanned): the birth the kernel-wide pin refuses in the kernel and the judge",
    "wrapper": "the object handed to the census is not the body (a decorator without functools.wraps hands it the wrapper; "
               "functools.wraps around another function points inspect at that function): the limit the replaced-helpers census's "
               "identity check holds for the fixture's helpers",
    "none": "no loader is named in code at all (prose, a string annotation, a keyword spelled like one): the census's own rule",
}
_LOADER_FORMS = [
    ('F01', 'ast.Name call, bound by a MODULE-LEVEL bare from-import',
     'from romp_judge import load_goals_shared\ndef f(sid):\n    return load_goals_shared(sid)\n', 'f', None, [1], 0, None),
    ('F02', 'ast.Attribute call jd.<loader>',
     'def f(sid):\n    store, fault = jd.load_goals_shared_or_fault(sid)\n    return store\n', 'f', None, [1], 1, None),
    ('F03', 'from-import WITH as, inside the body, alias called',
     'def f(sid):\n    from romp_judge import load_goals_shared as _lgs\n    return _lgs(sid)\n', 'f', None, [1], 0, None),
    ('F04', 'bare from-import inside the body, then the Name call',
     'def f(sid):\n    from romp_judge import load_goals_shared\n    return load_goals_shared(sid)\n', 'f', None, [1, 2], 0, None),
    ('F05', 'import <module> as j inside the body; j.<loader>',
     'def f(sid):\n    import romp_judge as j\n    return j.load_goals_shared(sid)\n', 'f', None, [2], 0, None),
    ('F05b', 'import romp_judge (no alias) inside the body; romp_judge.<loader>',
     'def f(sid):\n    import romp_judge\n    return romp_judge.load_goals_shared(sid)\n', 'f', None, [2], 0, None),
    ('F06', 'star import at MODULE level, Name call in the body',
     'from romp_judge import *\ndef f(sid):\n    return load_goals_shared(sid)\n', 'f', None, [1], 0, None),
    ('F07', 'getattr with a string',
     "def f(sid):\n    return getattr(jd, 'load_goals_shared')(sid)\n", 'f', None, [], 0, 'string'),
    ('F07b', 'getattr with a string built by concatenation (the needle survives in one constant)',
     "def f(sid):\n    return getattr(jd, 'load_goals_' + 'shared')(sid)\n", 'f', None, [], 0, 'string'),
    ('F07c', 'getattr with a string built by a concatenation that SPLITS the needle',
     "def f(sid):\n    return getattr(jd, 'load_' + 'goals_shared')(sid)\n", 'f', None, [], 0, 'assembled'),
    ('F07d', 'getattr with the name bound to a variable first (the constant spells the door whole where it is bound: the value rule)',
     "def f(sid):\n    n = 'load_goals_shared'\n    return getattr(jd, n)(sid)\n", 'f', None, [], 0, 'string'),
    ('F07e', 'getattr with a %-format that splits the needle',
     "def f(sid):\n    return getattr(jd, 'load_%s_shared' % 'goals')(sid)\n", 'f', None, [], 0, 'assembled'),
    ('F07f', 'getattr with an f-string assembling the name from pieces (the JoinedStr limit the round-4 ruling names)',
     "def f(sid):\n    return getattr(jd, f\"load_{'goals'}_shared\")(sid)\n", 'f', None, [], 0, 'assembled'),
    ('F07g', 'getattr with an f-string carrying no interpolation (one Constant, the whole name, reached by the consumer clause through getattr and by the value rule)',
     "def f(sid):\n    return getattr(jd, f'load_goals_shared')(sid)\n", 'f', None, [], 0, 'string'),
    ('F08', 'importlib.import_module(...).<loader>',
     "def f(sid):\n    return importlib.import_module('romp_judge').load_goals_shared(sid)\n", 'f', None, [1], 0, None),
    ('F08b', "getattr(importlib.import_module(...), '<loader>')",
     "def f(sid):\n    return getattr(importlib.import_module('romp_judge'), 'load_goals_shared')(sid)\n", 'f', None, [], 0, 'string'),
    ('F09', "__import__('romp_judge').<loader>",
     "def f(sid):\n    return __import__('romp_judge').load_goals_shared(sid)\n", 'f', None, [1], 0, None),
    ('F10', "sys.modules['romp_judge'].<loader>",
     "def f(sid):\n    return sys.modules['romp_judge'].load_goals_shared(sid)\n", 'f', None, [1], 0, None),
    ('F11', 'decorator @jd.<loader> on the scanned function',
     '@jd.load_goals_shared\ndef f(sid):\n    return sid\n', 'f', None, [0], 1, None),
    ('F11b', 'decorator with a call, @functools.wraps(jd.<loader>)',
     '@functools.wraps(jd.load_goals_shared)\ndef f(sid):\n    return sid\n', 'f', None, [], 0, 'wrapper'),
    ('F12', 'default argument value loader=jd.<loader>, called via the parameter',
     'def f(sid, loader=jd.load_goals_shared):\n    return loader(sid)\n', 'f', None, [0], 1, None),
    ('F13', 'lambda body',
     'def f(sid):\n    g = lambda s: jd.load_goals_shared(s)\n    return g(sid)\n', 'f', None, [1], 1, None),
    ('F14', 'list comprehension',
     'def f(sid):\n    return [jd.load_goals_shared(s) for s in (sid,)]\n', 'f', None, [1], 1, None),
    ('F15', 'f-string expression',
     "def f(sid):\n    return f'{jd.load_goals_shared(sid)}'\n", 'f', None, [1], 1, None),
    ('F15b', 'f-string with conversion and nested format spec',
     "def f(sid):\n    w = 4\n    return f'{jd.load_goals_shared(sid)!r:>{w}}'\n", 'f', None, [2], 1, None),
    ('F15c', 'f-string debug specifier =',
     "def f(sid):\n    return f'{jd.load_goals_shared(sid)=}'\n", 'f', None, [1], 1, None),
    ('F15d', 'f-string nested in an f-string (different quotes)',
     'def f(sid):\n    return f"{f\'{jd.load_goals_shared(sid)}\'}"\n', 'f', None, [1], 1, None),
    ('F15e', 'f-string nested in an f-string, SAME quotes (PEP 701, 3.12+ only)',
     'def f(sid):\n    return f"{f"{jd.load_goals_shared(sid)}"}"\n', 'f', (3, 12), [1], 1, None),
    ('F16', 'walrus',
     'def f(sid):\n    if (store := jd.load_goals_shared(sid)):\n        return store\n', 'f', None, [1], 1, None),
    ('F16b', 'walrus inside a comprehension condition',
     'def f(sid):\n    return [y for s in (sid,) if (y := jd.load_goals_shared(s))]\n', 'f', None, [1], 1, None),
    ('F17', 'match value pattern case jd.<loader> (a reference, not a call)',
     'def f(sid):\n    match sid:\n        case jd.load_goals_shared:\n            return 1\n        case _:\n            return 0\n', 'f', None, [2], 1, None),
    ('F17b', 'match mapping pattern with the loader as a value',
     "def f(sid):\n    match sid:\n        case {'k': jd.load_goals_shared}:\n            return 1\n        case _:\n            return 0\n", 'f', None, [2], 1, None),
    ('F17c', 'match guard calling the loader',
     'def f(sid):\n    match sid:\n        case str() if jd.load_goals_shared(sid):\n            return 1\n        case _:\n            return 0\n', 'f', None, [2], 1, None),
    ('F18', 'global declaration then the Name call (binding at module level)',
     'from romp_judge import load_goals_shared\ndef f(sid):\n    global load_goals_shared\n    return load_goals_shared(sid)\n', 'f', None, [2], 0, None),
    ('F18b', 'nonlocal declaration; the loader bound in an inner function',
     'def f(sid):\n    L = None\n    def g():\n        nonlocal L\n        L = jd.load_goals_shared\n    g()\n    return L(sid)\n', 'f', None, [4], 1, None),
    ('F19', 'class attribute loader = jd.<loader>; the CLASS is scanned',
     'class C:\n    loader = jd.load_goals_shared\n    def f(self, sid):\n        return self.loader(sid)\n', 'C', None, [1], 1, None),
    ('F19b', 'class attribute bound in the class body; only the METHOD is scanned',
     'class C:\n    loader = jd.load_goals_shared\n    def f(self, sid):\n        return self.loader(sid)\n', 'C.f', None, [], 0, 'outside'),
    ('F19c', 'instance attribute bound in __init__; only the METHOD is scanned',
     'class C:\n    def __init__(self):\n        self.loader = jd.load_goals_shared\n    def f(self, sid):\n        return self.loader(sid)\n', 'C.f', None, [], 0, 'outside'),
    ('F19d', 'property returning the loader; only the METHOD is scanned',
     'class C:\n    @property\n    def loader(self):\n        return jd.load_goals_shared\n    def f(self, sid):\n        return self.loader(sid)\n', 'C.f', None, [], 0, 'outside'),
    ('F20', 'annotated assignment of the loader to a local',
     'def f(sid):\n    loader: Callable = jd.load_goals_shared\n    return loader(sid)\n', 'f', None, [1], 1, None),
    ('F20b', 'STRING annotation naming the loader (no call)',
     "def f(sid):\n    x: 'jd.load_goals_shared' = None\n    return x\n", 'f', None, [], 0, 'none'),
    ('F21', 'nested function defined and called inside the body',
     'def f(sid):\n    def inner():\n        return jd.load_goals_shared(sid)\n    return inner()\n', 'f', None, [2], 1, None),
    ('F21b', 'nested function defined and NEVER called (a reference that never loads)',
     'def f(sid):\n    def inner():\n        return jd.load_goals_shared(sid)\n    return sid\n', 'f', None, [2], 1, None),
    ('F22', 'local variable bound to the loader inside the body, then called',
     'def f(sid):\n    L = jd.load_goals_shared\n    return L(sid)\n', 'f', None, [1], 1, None),
    ('F22b', 'MODULE-LEVEL name bound to the loader (L = jd.<loader>), called in the body',
     'L = jd.load_goals_shared\ndef f(sid):\n    return L(sid)\n', 'f', None, [], 0, 'outside'),
    ('F22c', 'MODULE-LEVEL from-import with as, alias called in the body',
     'from romp_judge import load_goals_shared as _lgs\ndef f(sid):\n    return _lgs(sid)\n', 'f', None, [], 0, 'outside'),
    ('F22d', 'closure: loader bound in the ENCLOSING function; only the inner function is scanned',
     'def outer():\n    L = jd.load_goals_shared\n    def f(sid):\n        return L(sid)\n    return f\nf = outer()\n', 'f', None, [], 0, 'outside'),
    ('F22e', "loader handed in as a PARAMETER (the judge's _or_fault shape), body scanned",
     'def f(sid, loader):\n    return loader(sid)\n', 'f', None, [], 0, 'outside'),
    ('F23', 'dict of callables, indexed and called',
     "def f(sid):\n    return {'a': jd.load_goals_shared}['a'](sid)\n", 'f', None, [1], 1, None),
    ('F23b', 'list of callables',
     'def f(sid):\n    return [jd.load_goals_shared][0](sid)\n', 'f', None, [1], 1, None),
    ('F23c', 'loop over a tuple of callables',
     'def f(sid):\n    out = None\n    for L in (jd.load_goals_shared,):\n        out = L(sid)\n    return out\n', 'f', None, [2], 1, None),
    ('F24', 'functools.partial',
     'def f(sid):\n    return functools.partial(jd.load_goals_shared, sid)()\n', 'f', None, [1], 1, None),
    ('F25', 'method on a module alias chain km.jd.<loader>',
     'def f(sid):\n    return km.jd.load_goals_shared(sid)\n', 'f', None, [1], 1, None),
    ('F25b', 'attribute chain through self: self._jd.<loader>',
     'class C:\n    _jd = jd\n    def f(self, sid):\n        return self._jd.load_goals_shared(sid)\n', 'C.f', None, [1], 1, None),
    ('F25c', 'chain through a call: _judge().<loader>',
     'def _judge():\n    return jd\ndef f(sid):\n    return _judge().load_goals_shared(sid)\n', 'f', None, [1], 0, None),
    ('F25d', "chain through a subscript: globals()['jd'].<loader>",
     "def f(sid):\n    return globals()['jd'].load_goals_shared(sid)\n", 'f', None, [1], 0, None),
    ('F25e', "chain through a dict literal: {'jd': jd}['jd'].<loader>",
     "def f(sid):\n    return {'jd': jd}['jd'].load_goals_shared(sid)\n", 'f', None, [1], 0, None),
    ('F25f', "the loader's own attribute: jd.<loader>.__call__(sid)",
     'def f(sid):\n    return jd.load_goals_shared.__call__(sid)\n', 'f', None, [1, 1], 2, None),
    ('F25g', 'a forwarding object: _J().<loader> via __getattr__',
     'class _J:\n    def __getattr__(self, n):\n        return getattr(jd, n)\ndef f(sid):\n    return _J().load_goals_shared(sid)\n', 'f', None, [1], 0, None),
    ('F26', 'conditional import inside try/except, alias called',
     'def f(sid):\n    try:\n        from romp_judge import load_goals_shared as L\n    except ImportError:\n        L = None\n    return L(sid)\n', 'f', None, [2], 0, None),
    ('F27', 'exec of a string',
     "def f(sid):\n    exec('jd.load_goals_shared(sid)')\n", 'f', None, [], 0, 'string'),
    ('F28', 'eval of a string, result called',
     "def f(sid):\n    return eval('jd.load_goals_shared')(sid)\n", 'f', None, [], 0, 'string'),
    ('F29', 'operator.attrgetter with a string',
     "def f(sid):\n    return operator.attrgetter('load_goals_shared')(jd)(sid)\n", 'f', None, [], 0, 'string'),
    ('F30', "vars(jd)['<loader>']",
     "def f(sid):\n    return vars(jd)['load_goals_shared'](sid)\n", 'f', None, [], 0, 'string'),
    ('F30b', "jd.__dict__['<loader>']",
     "def f(sid):\n    return jd.__dict__['load_goals_shared'](sid)\n", 'f', None, [], 0, 'string'),
    ('F30c', "jd.__getattribute__('<loader>')",
     "def f(sid):\n    return jd.__getattribute__('load_goals_shared')(sid)\n", 'f', None, [], 0, 'string'),
    ('F30d', "jd.__dict__.get('<loader>')",
     "def f(sid):\n    return jd.__dict__.get('load_goals_shared')(sid)\n", 'f', None, [], 0, 'string'),
    # Subscript keys the slice walk reaches (review round 4, extra6-2: the slice was tested as a direct Constant). The first three are
    # whole spellings the value rule reaches as well; the fourth keeps the needle in one piece and spells no door whole, so the slice
    # walk alone holds it.
    ('F30e', 'f-string as a subscript key (one Constant, the whole name)',
     "def f(sid):\n    return vars(jd)[f'load_goals_shared'](sid)\n", 'f', None, [], 0, 'string'),
    ('F30f', 'conditional expression as a subscript key',
     "def f(sid):\n    return vars(jd)['load_goals_shared' if X else 'load_goals'](sid)\n", 'f', None, [], 0, 'string'),
    ('F30g', 'walrus as a subscript key',
     "def f(sid):\n    return vars(jd)[(k := 'load_goals_shared')](sid)\n", 'f', None, [], 0, 'string'),
    ('F30h', 'concatenation as a subscript key that keeps the needle in one piece (the slice walk alone catches it)',
     "def f(sid):\n    return vars(jd)['load_goals_' + 'shared'](sid)\n", 'f', None, [], 0, 'string'),
    ('F31', 'keyword argument NAMED like the loader (no loader referenced)',
     'def g(**k):\n    return k\ndef f(sid):\n    return g(load_goals_shared=sid)\n', 'f', None, [], 0, 'none'),
    ('F32', 'a PARAMETER named like the loader, called (not the loader)',
     'def f(load_goals_shared, sid):\n    return load_goals_shared(sid)\n', 'f', None, [1], 0, None),
    ('F33', 'call spanning lines: the site index vs the closing line',
     "def f(sid):\n    store, fault = jd.load_goals_shared_or_fault(\n        sid,\n    )\n    _NUDGE_WALK_STATS['loads'] += 1\n    return store\n", 'f', None, [1], 1, None),
    ('F33b', 'backslash continuation between jd. and the loader name',
     'def f(sid):\n    store = jd.\\\n        load_goals_shared(sid)\n    return store\n', 'f', None, [1], 1, None),
    ('F34', 'two calls on one line',
     'def f(sid):\n    a = jd.load_goals_shared(sid); b = jd.load_goals_shared(sid)\n    return a, b\n', 'f', None, [1, 1], 2, None),
    ('F35', 'conditional expression picking a loader',
     'def f(sid):\n    return (jd.load_goals_shared if X else jd.load_goals)(sid)\n', 'f', None, [1, 1], 1, None),
    ('F36', 'await (async def)',
     'async def f(sid):\n    return await jd.load_goals_shared(sid)\n', 'f', None, [1], 1, None),
    ('F37', 'with statement',
     'def f(sid):\n    with jd.load_goals_shared(sid) as s:\n        return s\n', 'f', None, [1], 1, None),
    ('F38', 'yield',
     'def f(sid):\n    yield jd.load_goals_shared(sid)\n', 'f', None, [1], 1, None),
    ('F39', 'class decorator',
     '@jd.load_goals_shared\nclass C:\n    pass\n', 'C', None, [0], 1, None),
    ('F40', 'assignment TARGET jd.<loader> = x (a monkeypatch, no call)',
     'def f(sid):\n    jd.load_goals_shared = jd.load_goals\n    return sid\n', 'f', None, [1, 1], 1, None),
    ('F41', 'passed as a callback: map(jd.<loader>, ...)',
     'def f(sid):\n    return list(map(jd.load_goals_shared, (sid,)))\n', 'f', None, [1], 1, None),
    ('F42', 'star-args call jd.<loader>(*a, **k)',
     'def f(sid):\n    a, k = (sid,), {}\n    return jd.load_goals_shared(*a, **k)\n', 'f', None, [2], 1, None),
    ('F43', "docstring, string literal and comment only (the module's sample)",
     "def f(sid):\n    '''jd.load_goals_shared_or_fault(sid) here'''\n    note = 'jd.load_goals_shared_or_fault(sid) in a string'   # jd.load_goals_shared_or_fault(sid)\n    return note\n", 'f', None, [], 0, 'none'),
    ('F43b', 'type comment naming the loader',
     'def f(sid):\n    x = None  # type: jd.load_goals_shared\n    return x\n', 'f', None, [], 0, 'none'),
    ('F44', 'compile() of a string then exec of the code object',
     "def f(sid):\n    exec(compile('jd.load_goals_shared(sid)', '<s>', 'exec'))\n", 'f', None, [], 0, 'string'),
    ('F45', 'the loader name as a dict KEY string (no call; the pin refuses the whole-text constant whatever receives it)',
     "def f(sid):\n    return {'load_goals_shared': sid}\n", 'f', None, [], 0, 'string'),
    ('F46', 'semicolon: load and the bump on ONE line',
     "def f(sid):\n    store = jd.load_goals_shared_or_fault(sid); _NUDGE_WALK_STATS['loads'] += 1\n    return store\n", 'f', None, [1], 1, None),
    ('F47', 'one-line if guarding the bump on the line after the load',
     "def f(sid):\n    store = jd.load_goals_shared_or_fault(sid)\n    if X: _NUDGE_WALK_STATS['loads'] += 1\n    return store\n", 'f', None, [1], 1, None),
    ('F48', 'inner CLASS method calling the loader inside the body',
     'def f(sid):\n    class K:\n        def m(self):\n            return jd.load_goals_shared(sid)\n    return K().m()\n', 'f', None, [3], 1, None),
    ('F49', 'except* clause body (3.11+)',
     "def f(sid):\n    out = None\n    try:\n        raise ExceptionGroup('x', [ValueError()])\n    except* ValueError:\n        out = jd.load_goals_shared(sid)\n    return out\n", 'f', (3, 11), [5], 1, None),
    ('F50', 'type alias statement referencing the loader in a subscript (3.12+)',
     'def f(sid):\n    type T = list[jd.load_goals_shared]\n    return sid\n', 'f', (3, 12), [1], 1, None),
    ('F51', 'shadowed local jd = km.jd; jd.<loader>',
     'def f(sid):\n    jd = km.jd\n    return jd.load_goals_shared(sid)\n', 'f', None, [2], 1, None),
    ('F52', 'Name in STORE context: load_goals_shared = None (no call)',
     'def f(sid):\n    load_goals_shared = None\n    return load_goals_shared\n', 'f', None, [1, 2], 0, None),
    ('F53', 'lambda default binding L=jd.<loader>',
     'def f(sid):\n    return (lambda s, L=jd.load_goals_shared: L(s))(sid)\n', 'f', None, [1], 1, None),
    ('F55', 'MODULE-LEVEL dict of callables, indexed in the body',
     "LOADERS = {'s': jd.load_goals_shared}\ndef f(sid):\n    return LOADERS['s'](sid)\n", 'f', None, [], 0, 'outside'),
    ('F56', 'MODULE-LEVEL functools.partial of the loader, called in the body',
     'P = functools.partial(jd.load_goals_shared)\ndef f(sid):\n    return P(sid)\n', 'f', None, [], 0, 'outside'),
    ('F57', 'generator expression',
     'def f(sid):\n    return next(jd.load_goals_shared(s) for s in (sid,))\n', 'f', None, [1], 1, None),
    ('F58', 'decorated WITHOUT functools.wraps: the scanned object is the wrapper',
     'def deco(fn):\n    def w(*a, **k):\n        return fn(*a, **k)\n    return w\n@deco\ndef f(sid):\n    return jd.load_goals_shared(sid)\n', 'f', None, [], 0, 'wrapper'),
    ('F58b', "decorated WITH functools.wraps (the kernel's gate shape)",
     'def deco(fn):\n    @functools.wraps(fn)\n    def w(*a, **k):\n        return fn(*a, **k)\n    return w\n@deco\ndef f(sid):\n    return jd.load_goals_shared(sid)\n', 'f', None, [2], 1, None),
    ('F58c', 'functools.lru_cache decorated',
     '@functools.lru_cache(maxsize=None)\ndef f(sid):\n    return jd.load_goals_shared(sid)\n', 'f', None, [2], 1, None),
    ('F58d', 'decorated WITHOUT wraps, and the WRAPPER also loads (what the census reads)',
     'def deco(fn):\n    def w(*a, **k):\n        return fn(*a, **k)\n    return w\n@deco\ndef f(sid):\n    return jd.load_goals_shared(sid)\n', 'deco', None, [], 0, 'none'),
    ('F59', 'staticmethod on a class, the METHOD scanned via the class attribute',
     'class C:\n    @staticmethod\n    def f(sid):\n        return jd.load_goals_shared(sid)\n', 'C.f', None, [2], 1, None),
    ('F60', 'loader referenced only via keyword default in a nested def, never called',
     'def f(sid):\n    def g(L=jd.load_goals_shared):\n        return L\n    return sid\n', 'f', None, [1], 1, None),
    ('F61', "t-string interpolation t'{...}' (PEP 750, 3.14+: the TemplateStr and Interpolation nodes)",
     "def f(sid):\n    return t'{jd.load_goals_shared(sid)}'\n", 'f', (3, 14), [1], 1, None),
    ('F62', 'type parameter bound naming the loader, def f[T: jd.<loader>] (3.12+: the TypeVar node; a reference, not a call)',
     'def f[T: jd.load_goals_shared](sid):\n    return sid\n', 'f', (3, 12), [0], 1, None),
    ('F63', 'type parameter default naming the loader, def f[T = jd.<loader>] (3.13+)',
     'def f[T = jd.load_goals_shared](sid):\n    return sid\n', 'f', (3, 13), [0], 1, None),
    # The doors review round 4 found on no list (correctness-1, tests-1, extra6-1): each spells the name whole in a constant that no
    # listed lookup receives, and the value rule refuses the constant whatever receives it.
    ('F64', 'operator.methodcaller with a string',
     "def f(sid):\n    return operator.methodcaller('load_goals_shared', sid)(jd)\n", 'f', None, [], 0, 'string'),
    ('F65', 'operator.itemgetter over vars(jd)',
     "def f(sid):\n    return operator.itemgetter('load_goals_shared')(vars(jd))(sid)\n", 'f', None, [], 0, 'string'),
    ('F66', 'functools.partial(getattr, jd) handed the name',
     "def f(sid):\n    return functools.partial(getattr, jd)('load_goals_shared')(sid)\n", 'f', None, [], 0, 'string'),
    ('F67', 'match mapping pattern with the loader name as the KEY',
     "def f(sid):\n    match vars(jd):\n        case {'load_goals_shared': L}:\n            return L(sid)\n        case _:\n            return None\n",
     'f', None, [], 0, 'string'),
]
# The bump forms: the statement placed on the line after the load in `def f(sid)`, the bump indices _bump_sites answers, and
# whether the walk census's adjacency (one bump, one load, the bump on the line after) holds.
_BUMP_FORMS = [
    ('B01', "_NUDGE_WALK_STATS['loads'] += 1 (the kernel's statement)", "    _NUDGE_WALK_STATS['loads'] += 1\n", [2], True),
    ('B02', 'plain assignment x = x + 1', "    _NUDGE_WALK_STATS['loads'] = _NUDGE_WALK_STATS['loads'] + 1\n", [], False),
    ('B03', '+= 2 (the value is not checked by the scan)', "    _NUDGE_WALK_STATS['loads'] += 2\n", [2], True),
    ('B04', '+= 1.0 (a float)', "    _NUDGE_WALK_STATS['loads'] += 1.0\n", [2], True),
    ('B05', 'key in a variable', "    key = 'loads'\n    _NUDGE_WALK_STATS[key] += 1\n", [], False),
    ('B06', 'the dict in a local alias', "    _S = _NUDGE_WALK_STATS\n    _S['loads'] += 1\n", [], False),
    ('B07', 'attribute-qualified dict km._NUDGE_WALK_STATS', "    km._NUDGE_WALK_STATS['loads'] += 1\n", [], False),
    ('B08', '-= -1', "    _NUDGE_WALK_STATS['loads'] -= -1\n", [], False),
    ('B09', '__setitem__', "    _NUDGE_WALK_STATS.__setitem__('loads', _NUDGE_WALK_STATS['loads'] + 1)\n", [], False),
    ('B10', "implicit string concatenation 'lo' 'ads'", "    _NUDGE_WALK_STATS['lo' 'ads'] += 1\n", [2], True),
    ('B11', 'parenthesised key', "    _NUDGE_WALK_STATS[('loads')] += 1\n", [2], True),
    ('B12', '+= +1', "    _NUDGE_WALK_STATS['loads'] += +1\n", [2], True),
    ('B13', 'dict.update', "    _NUDGE_WALK_STATS.update(loads=_NUDGE_WALK_STATS['loads'] + 1)\n", [], False),
    ('B14', 'the statement quoted in a comment and a string (no bump)', '    note = "_NUDGE_WALK_STATS[\'loads\'] += 1"   # _NUDGE_WALK_STATS[\'loads\'] += 1\n', [], False),
    ('B15', 'two bumps on one line', "    _NUDGE_WALK_STATS['loads'] += 1; _NUDGE_WALK_STATS['loads'] += 1\n", [2, 2], False),
    ('B16', 'bump under a one-line if', "    if X: _NUDGE_WALK_STATS['loads'] += 1\n", [2], True),
    ('B17', 'bump in a one-line for', "    for _ in range(1): _NUDGE_WALK_STATS['loads'] += 1\n", [2], True),
    ('B18', "bump on a bytes key b'loads'", "    _NUDGE_WALK_STATS[b'loads'] += 1\n", [], False),
    ('B19', "bump of a NESTED key _NUDGE_WALK_STATS['x']['loads']", "    _NUDGE_WALK_STATS['x']['loads'] += 1\n", [], False),
    ('B20', 'bump through operator.iadd', "    _NUDGE_WALK_STATS['loads'] = operator.iadd(_NUDGE_WALK_STATS['loads'], 1)\n", [], False),
]
# The hand-off forms: a stand-in wrapper `w(fsid, loader)`, the lines _pass_through_lines answers as offsets from the def's line,
# and its call count (setUp's guard reads both).
_HANDOFF_FORMS = [
    ('P01', "loader(fsid) (the judge's statement)", 'def w(fsid, loader):\n    store = loader(fsid)\n    return store\n', [1], 1),
    ('P02', '(loader)(fsid) parenthesised', 'def w(fsid, loader):\n    store = (loader)(fsid)\n    return store\n', [1], 1),
    ('P03', 'loader.__call__(fsid)', 'def w(fsid, loader):\n    store = loader.__call__(fsid)\n    return store\n', [], 0),
    ('P04', 'two calls on one line', 'def w(fsid, loader):\n    store = loader(fsid) if X else loader(fsid)\n    return store\n', [1], 2),
    ('P05', 'functools.partial(loader)(fsid)', 'def w(fsid, loader):\n    store = functools.partial(loader)(fsid)\n    return store\n', [], 0),
    ('P06', 'call inside an f-string', "def w(fsid, loader):\n    return f'{loader(fsid)}'\n", [1], 1),
    ('P07', 'alias then call: L = loader; L(fsid)', 'def w(fsid, loader):\n    L = loader\n    return L(fsid)\n', [], 0),
]


class TheCensusOverEveryForm(unittest.TestCase):
    """The census functions run over the enumeration above on the interpreter at hand: per loader form _loader_sites answers the
    sites the table expects for both needles (a form the census counts keeps counting, at the lines it counts it at; a form it
    misses stays a stated limit, named), per bump form _bump_sites answers the bumps and the adjacency the walk census reads,
    and per hand-off form _pass_through_lines answers the lines and the call count setUp's guard reads. The consolidation pass: a
    lens enumerated the forms on 3.10 through 3.13 and found the tables identical but for the gated forms; this is that
    enumeration as the module's own check, so a census that visits one node kind less reds here naming the form (the alias
    finding of the build's verifier pass after the round-2 fixes: over Name and Attribute alone, an import alias inside a
    helper's body was no site, and no sample said so). The loader
    forms of the string and the assembled classes are also run through the kernel-wide pin, _loader_births, over the form's own
    file: a birth from every string form and none from any assembled form, so the pin is held against the input it refuses and
    the input it lets pass, and the two limit texts cannot overstate it (a verifier of the consolidation pass found the module's
    text saying the pin closed the string limit while vars(jd)[...] and jd.__dict__[...] passed it)."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        stub = self._module(_STUB_JUDGE, "".join("def %s(fsid=None, *a, **k):\n    return fsid\n\n\n" % n for n in
                                                 ("load_goals", "load_goals_shared", "load_goals_or_fault", "load_goals_shared_or_fault")))
        kstub = types.ModuleType(_STUB_KERNEL)
        kstub.jd = stub
        sys.modules[_STUB_KERNEL] = kstub
        self.addCleanup(sys.modules.pop, _STUB_KERNEL, None)

    def _module(self, name, source):
        path = Path(self.td.name) / (name + ".py")
        path.write_text(source)
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod                           # inspect finds a class's source through sys.modules[cls.__module__]
        self.addCleanup(sys.modules.pop, name, None)
        spec.loader.exec_module(mod)
        return mod

    def _path(self, fid):
        return Path(self.td.name) / ("c7pin_form_%s.py" % fid)

    def _target(self, fid, body, dotted):
        obj = self._module("c7pin_form_" + fid, _FORM_PRE + body.replace("romp_judge", _STUB_JUDGE))
        for part in dotted.split("."):
            obj = getattr(obj, part)
        return obj

    def test_every_loader_form_is_a_site_where_the_table_says_or_a_stated_limit(self):
        here = sys.version.split()[0]
        self.assertEqual(len(_LOADER_FORMS), 112, "the table carries the lens's 95 loader forms, a consolidation-pass verifier's four, the "
                                                  "round-3 fixes' three (a t-string interpolation, a type-parameter bound and a type-parameter "
                                                  "default) and the round-4 fixes' ten (methodcaller, itemgetter over vars(jd), a partial of "
                                                  "getattr, a match-mapping key, an f-string handed to getattr with and without a piece "
                                                  "interpolated, and four subscript keys: an f-string, a conditional, a walrus and a "
                                                  "concatenation that keeps the needle in one piece)")
        self.assertEqual(len({row[0] for row in _LOADER_FORMS}), 112, "with distinct ids")
        counted, limits, gated = 0, {}, []
        for fid, form, body, dotted, needs, sites, jds, limit in _LOADER_FORMS:
            self.assertEqual(limit is None, bool(sites), "%s (%s): a form the census counts names no limit and a form it misses names one" % (fid, form))
            self.assertIn(limit, (None,) + tuple(_LIMITS), "%s (%s): the limit is one of the stated %d classes of _LIMITS" % (fid, form, len(_LIMITS)))
            if needs and sys.version_info[:2] < needs:
                with self.assertRaises(SyntaxError, msg="%s (%s): gated to %d.%d and later, so its syntax must not compile on %s (the gate is "
                                                        "checked on the side it refuses)" % (fid, form, needs[0], needs[1], here)):
                    compile(_FORM_PRE + body, fid, "exec")
                gated.append(fid)
                continue
            obj = self._target(fid, body, dotted)
            got = _loader_sites(obj, "load_goals")
            self.assertEqual([i for i, _ln in got], sites,
                             "%s (%s): on %s the census over the needle 'load_goals' answers %r and the table expects sites at line indices %r%s"
                             % (fid, form, here, got, sites,
                                "" if limit is None else "; the form is the stated limit %r: %s" % (limit, _LIMITS[limit])))
            self.assertEqual(len(_loader_sites(obj, "jd.load_goals_shared")), jds,
                             "%s (%s): on %s the walk census's needle 'jd.load_goals_shared' counts %d and the table expects %d"
                             % (fid, form, here, len(_loader_sites(obj, "jd.load_goals_shared")), jds))
            if limit in ("string", "assembled"):
                born = _loader_births(self._path(fid), judge=False)[0]
                self.assertEqual(bool(born), limit == "string",
                                 "%s (%s): the kernel-wide pin, _loader_births, over this form's file %s; a form of the string class spells a door "
                                 "whole in a constant, wherever it appears and whatever receives it, or hands a constant containing the name to a "
                                 "listed lookup, a dict read or a subscript key, and the pin refuses it (a birth); a form of the assembled class "
                                 "spells the name whole in no constant and carries none containing it to such a receiver, and the pin lets it "
                                 "pass, the limit stated as %r; births: %s"
                                 % (fid, form, "reports a birth" if born else "reports none", limit,
                                    "; ".join("line %d, %s" % b for b in born) or "none"))
            if limit is None:
                counted += 1
            else:
                limits[limit] = limits.get(limit, 0) + 1
        self.assertEqual(counted + sum(limits.values()) + len(gated), 112, "every row was counted, a limit, or gated: %d, %r, %r" % (counted, limits, gated))
        self.assertEqual(limits, {"string": 22, "assembled": 3, "outside": 9, "wrapper": 2, "none": 5},
                         "the missed forms by limit: the lens's classification with its string class split by what the kernel-wide pin refuses "
                         "(the round-4 fixes moved F07d and F45 into the string class, a constant spelling a door whole being refused wherever "
                         "it appears, and added nine string rows, five for the doors the round found on no list and four for the subscript "
                         "keys the slice walk reaches, and one assembled row for the f-string that splits the needle)")

    def test_every_bump_form_reads_as_the_table_says(self):
        self.assertEqual(len(_BUMP_FORMS), 20, "the table carries the lens's 20 bump forms")
        for bid, form, stmt, bumps, adjacent in _BUMP_FORMS:
            f = self._target(bid, "def f(sid):\n    store = jd.load_goals_shared_or_fault(sid)\n" + stmt + "    return store\n", "f")
            at = [i for i, _ln in _loader_sites(f, "jd.load_goals_shared")]
            self.assertEqual(at, [1], "%s (%s): the load sits at index 1 in every bump form" % (bid, form))
            got = _bump_sites(f)
            self.assertEqual(got, bumps, "%s (%s): _bump_sites answers %r and the table expects %r (a spelling other than the kernel's "
                                         "`_NUDGE_WALK_STATS[\"loads\"] += 1` is no bump, and the walk census reds on it, conservatively)"
                                         % (bid, form, got, bumps))
            self.assertEqual(len(got) == 1 and got[0] == at[0] + 1, adjacent,
                             "%s (%s): the walk census's adjacency, one bump on the line after the one load, %s here" % (bid, form, "holds" if adjacent else "fails"))

    def test_every_hand_off_form_reads_as_the_table_says(self):
        self.assertEqual(len(_HANDOFF_FORMS), 7, "the table carries the lens's 7 hand-off forms")
        for pid, form, body, offsets, count in _HANDOFF_FORMS:
            w = self._target(pid, body, "w")
            start = inspect.getsourcelines(w)[1]
            lines, n = _pass_through_lines(w, "loader")
            self.assertEqual((sorted(lines), n), (sorted(start + o for o in offsets), count),
                             "%s (%s): _pass_through_lines answers lines %r and %d call(s); the table expects the def's line %d plus %r and %d (a "
                             "hand-off spelled other than `loader(fsid)`, through __call__, a partial or a local alias, is no call here and "
                             "setUp's guard reds on it, conservatively; two on one line are two calls on one line)"
                             % (pid, form, sorted(lines), n, start, offsets, count))


class TheGrammarIsTheOneTheWalkersClassify(unittest.TestCase):
    """The reviewer's version demand (review round 2, correctness-1: a census that cannot scan an interpreter must fail loudly
    there, never scan less and pass), restated after round 3 for the AST readers: a walker that meets a node it does not
    classify must fail naming the class, since a reader that cannot parse must not report absent. Two halves. At test time the
    running interpreter's ast module is read whole and every node class it defines must be in _AST_CONCRETE (the grammar the
    walkers classify), _AST_ABSTRACT (the sum types the parser never instantiates) or _AST_COMPAT (the classes kept for
    compatibility that no parse produces), so a grammar that gains a node form reds here naming the new class; and _walk, the one
    walk every census in this module reads through, refuses a node of a class outside _AST_CONCRETE by name. A third case holds the
    "one walk" itself: no reference to an ast traversal name sits outside _walk, read from this module's own AST in every form
    (review round 4, regression-3 and extra7-1: a count of one spelling held it before)."""

    def test_the_interpreter_defines_no_node_class_outside_the_table(self):
        here, version = sys.version_info[:2], sys.version.split()[0]
        classes = {n: c for n, c in vars(ast).items() if inspect.isclass(c) and issubclass(c, ast.AST) and c is not ast.AST}
        outside = sorted(n for n in classes if n not in _AST_CONCRETE and n not in _AST_ABSTRACT and n not in _AST_COMPAT)
        self.assertEqual(outside, [], "Python %s defines ast node classes this module's census walkers do not classify: %s. A census that "
                                      "meets a node of one of them would scan less and report a site absent; list each in _AST_CONCRETE "
                                      "with the version that adds it (or in _AST_ABSTRACT or _AST_COMPAT, with the reason) and say in the "
                                      "table's comment how each walker reads it" % (version, ", ".join(outside)))
        expected = {n for n, since in _AST_CONCRETE.items() if since is None or here >= since}
        present = {n for n in _AST_CONCRETE if n in classes}
        self.assertEqual(present, expected,
                         "Python %s defines exactly the table's concrete classes at or below its version: missing %r (a name the table lists "
                         "for this version that the interpreter lacks: a misspelling, a gate set too low, or a class the interpreter removed, "
                         "for which no since-gate edit is correct: give the table a removal gate for the entry before listing the class as "
                         "absent; the version column is a lower bound alone today, since no released or beta interpreter has removed a "
                         "listed class), early %r (a class the interpreter "
                         "defines before the version the table says adds it)" % (version, sorted(expected - present), sorted(present - expected)))
        self.assertEqual(_AST_KNOWN, frozenset(classes[n] for n in present), "the class set _walk refuses against is the same table, by identity")
        for n in sorted(present):
            subs = sorted(m for m, c in classes.items() if issubclass(c, classes[n]) and c is not classes[n])
            self.assertLessEqual(set(subs), _AST_COMPAT, "%s is a leaf of the grammar but for the compatibility classes: %r" % (n, subs))
            base = classes[n].__bases__[0].__name__
            self.assertIn(base, set(_AST_ABSTRACT) | {"AST"}, "%s derives from a sum type or from AST itself, not from another concrete class: %s" % (n, base))
        for n, since in sorted(_AST_ABSTRACT.items()):
            if since is not None and here < since:
                self.assertTrue(n not in classes, "the sum type %s is listed from %d.%d and Python %s defines it already" % (n, since[0], since[1], version))
                continue
            self.assertTrue(n in classes, "the sum type %s is defined on Python %s" % (n, version))
            self.assertTrue(any(issubclass(c, classes[n]) and c is not classes[n] for c in classes.values()),
                            "the sum type %s has subclasses on Python %s; one with none is a name that no longer means what the table says" % (n, version))

    def test_a_walker_refuses_a_node_it_does_not_classify_by_name(self):
        tree = ast.parse("def f(sid):\n    return jd.load_goals_shared(sid)\n")
        self.assertEqual([type(n).__name__ for n in _walk(tree)], [type(n).__name__ for n in ast.walk(tree)],   # the control: a
                         "over grammar nodes _walk is the standard walk, whole and in order")                   # _WALK_EXEMPT row
        stranger = type("Frobnicate", (ast.expr_context,), {"_fields": ()})       # a class no grammar version defines
        tree.body[0].body[0].value.func.value.ctx = stranger()
        with self.assertRaises(AssertionError) as cm:
            list(_walk(tree))
        self.assertIn("Frobnicate", str(cm.exception), "the refusal names the class it met: %s" % cm.exception)
        namesake = type("Store", (ast.expr_context,), {"_fields": ()})           # a grammar name on a class that is not the ast module's
        tree = ast.parse("x = 1")
        tree.body[0].targets[0].ctx = namesake()
        with self.assertRaises(AssertionError) as cm:
            list(_walk(tree))
        self.assertIn("Store", str(cm.exception), "a stranger of a known name is refused as well, by identity: %s" % cm.exception)
        # that every walker reads through _walk is the next case's, over this module's AST (a count of one spelling before round 4)

    def test_no_tree_walk_happens_except_through_walk(self):
        """Every walker reads through _walk, asserted over this module's own AST and not by counting one spelling (review round 4,
        regression-3 and extra7-1: the round-3 guard counted the text of one call spelling once, so a census written as a
        NodeVisitor subclass, an iter_child_nodes recursion, a from-import of the walk, a module alias walking or a getattr with
        the name in a string walked a tree without _walk, met a node the table does not classify, reported no site and left the
        guard green; a one-spelling contract is a list of length one). _traversal_references reads every reference to the four
        traversal names in four forms: an attribute of the ast module or of any name it is imported under (which is how a
        NodeVisitor base is spelled too), a from-import with or without `as` (a star import from ast counts as every name), and
        getattr on the module with a string constant; the names are assembled at run time (_TRAVERSAL), so this case's text holds
        none. Every reference sits inside _walk but for the rows of _WALK_EXEMPT, each with its reason, and every row is used, so a
        stale exemption reds too; _walk itself holds exactly one, the standard walk by attribute. The four forms are also run over
        synthetic sources built from the assembled names, so the refused inputs are pinned here and not only by the plants the
        history paragraphs record. Outside these forms: a traversal name assembled at run time or read from vars(ast) or
        ast.__dict__; the interpreter check beside this case scans vars(ast) for every node class and reds by name on a new one
        with no walker involved, so the version demand does not rest on this pin alone."""
        refs = _traversal_references(ast.parse(Path(os.path.realpath(__file__)).read_text(encoding="utf-8")))
        outside = [r for r in refs if r[4] != "_walk"]
        stray = [r for r in outside if (r[4], r[1]) not in _WALK_EXEMPT]
        self.assertEqual(stray, [], "a reference to an ast traversal name outside _walk and outside _WALK_EXEMPT, by line, name, form, spelling "
                                    "and enclosing def: %s. A census that walks a tree by itself passes a node the table does not classify as no "
                                    "site; read through _walk, or add an exemption row with the reason the reference traverses nothing"
                                    % "; ".join("line %d, %s, the %s form (%s) in %s" % r for r in stray))
        stale = sorted(k for k in _WALK_EXEMPT if not any((r[4], r[1]) == k for r in outside))
        self.assertEqual(stale, [], "an exemption with no reference: %r (the row outlived the code it excused; remove it)" % stale)
        self.assertEqual([(r[1], r[2]) for r in refs if r[4] == "_walk"], [(_WALK, "attribute")],
                         "_walk holds exactly one traversal reference, the standard walk by attribute: %r" % [r for r in refs if r[4] == "_walk"])
        # the refused inputs, one synthetic source per form (and per name for the two the module never spells in code)
        samples = (
            ("import ast\nclass _V(ast.%s):\n    pass\n" % _NODE_VISITOR, (2, _NODE_VISITOR, "attribute", "ast." + _NODE_VISITOR, "_V")),
            ("import ast\nclass _T(ast.%s):\n    def visit(self, n):\n        return n\n" % _NODE_TRANSFORMER,
             (2, _NODE_TRANSFORMER, "attribute", "ast." + _NODE_TRANSFORMER, "_T")),
            ("import ast\ndef kids(n):\n    return list(ast.%s(n))\n" % _ITER_CHILD_NODES, (3, _ITER_CHILD_NODES, "attribute", "ast." + _ITER_CHILD_NODES, "kids")),
            ("from ast import %s as _w\ndef census(t):\n    return list(_w(t))\n" % _WALK, (1, _WALK, "from-import", "from ast import %s as _w" % _WALK, "<module>")),
            ("from ast import *\n", (1, "*", "from-import", "from ast import *", "<module>")),
            ("import ast as _a\ndef census(t):\n    return list(_a.%s(t))\n" % _WALK, (3, _WALK, "attribute", "_a." + _WALK, "census")),
            ("import ast\ndef census(t):\n    return list(getattr(ast, %r)(t))\n" % _WALK, (3, _WALK, "getattr", "getattr(ast, %r)" % _WALK, "census")),
            ("import ast\nclass C:\n    def m(self, t):\n        return list(ast.%s(t))\n" % _WALK, (4, _WALK, "attribute", "ast." + _WALK, "C.m")),
        )
        for source, expected in samples:
            got = _traversal_references(ast.parse(source))
            self.assertEqual(got, [expected], "the finder reads %r as one reference, %r, and answers %r" % (source, expected, got))


class Docs(unittest.TestCase):
    def test_the_reference_states_condition_7_in_the_jobs_paragraph_and_names_the_counter(self):
        """The reference's `jobs` block is the one home of the other-readers clause (review round 2, regression-2 and fresh-4:
        the clause stood in four hand-kept copies, two of them pinned by nothing, and said the three writers are reached from
        the look's wake legs and from the sweep, which is false of _dead_wait_block on the toggle-off pass). This case pins the
        home's wording, with each writer's callers, and the two pointers a test can read: the memos.nudgeWalk entry's and this
        module's own docstring's. The ledger entry (upstream/) carries the same pointer by hand and is not read here: the
        directory is fork-only infrastructure and this module is part of the offer the entry records, so a read of it would red
        upstream or need a skip, and a skipping pin pins nothing."""
        doc = Path(HERE).parent.joinpath("docs", "reference.md").read_text()
        jobs = doc[doc.index("- `jobs`: the jobs thread"):]
        jobs = " ".join(jobs[:jobs.index("\n- `caches`:")].split())   # the paragraph is wrapped: one space between words
        for words in ("bounds two loaders", "the look's decision read and the placement gate's currency check",
                      "the walk takes at most one shared goal-store load per alive session per pass",
                      "exactly one when its look reaches the store",
                      "zero when the look is skipped or ends at a state gate before the store read",
                      "the placement gate's post-derivation currency check is a second load", "not an exception to the walk's bound",
                      "at most one per derived session, counted apart by the test rather than by a served counter",
                      "`memos.nudgeWalk.loads`", "tests/test_nudge_walk_one_load_per_pass.py",
                      "readers of the same store run on the same pass under their own rules and outside both bounds, among them",
                      "`_wake_goal`", "at most one per stamped top whose dead-man is due, per look",
                      "the writers' own loads at their write moments", "`_mark_nudge_failed`", "`_file_wake_answer`", "`_dead_wait_block`",
                      "the first two reached from the look's wake legs and from the wake sweep", "from the look's dormant-owner branch",
                      "only with the toggle on",
                      "`_awaiting_wake_outcomes`", "runs after the walk in the same pass, not on it"):
            self.assertIn(words, jobs, "the jobs paragraph states condition 7 per mechanism, scoped to the two loaders it bounds, names "
                                       "the store's other readers on the pass as a class with its members, their bounds and each writer's "
                                       "callers on the toggle-off pass, the counter and this test: %r" % words)
        walk = " ".join(doc[doc.index("`nudgeWalk` is the auto-nudge walk's"):].split())   # wrapped: normalise before slicing
        walk = walk[:walk.index("a memo row is the ten files' stat")]
        self.assertIn("`loads`", walk, "memos.nudgeWalk.loads is named in the walk's entry")
        self.assertIn("bounds two loaders", walk, "and the entry scopes the condition to the two loaders it bounds")
        self.assertIn("a second loader with a bound of its own", walk, "and the entry names the gate's check as the second loader")
        self.assertIn("counted by the test and by no served counter", walk, "and says what counts it")
        self.assertIn("the store's other readers on the pass are named with their bounds in the `jobs` block above", walk,
                      "and the entry points at the jobs block for the store's other readers instead of carrying a copy of the clause")
        mine = " ".join(sys.modules[__name__].__doc__.split())
        self.assertIn("the reference's `jobs` block (docs/reference.md) names them with their bounds and their callers on the toggle-off pass",
                      mine, "this module's own docstring points at the jobs block for the store's other readers instead of carrying a copy")
        gloss = km._PerfStats.__doc__
        field = gloss[gloss.index("nudgeWalk (the auto-nudge walk's"):]
        field = " ".join(field[:field.index("nudgeGate")].split())   # wrapped too
        self.assertIn("loads (the walk's shared goal-store reads", field, "the _PerfStats field docstring names the counter")

    def test_the_bypass_retake_sentence_counts_this_heads_cases(self):
        """The module docstring says the three bypass plants were re-taken at this head over its N cases (review round 3,
        correctness-2 and regression-2: the sentence was true when written and went stale nine commits and one case later, its count
        one case behind the module's). N is read here against the loader's count of this module's cases, so a case
        added without a re-take reds this line and names the two figures, instead of leaving a count that reads true and is not."""
        doc = " ".join(sys.modules[__name__].__doc__.split())
        m = re.search(r"re-taken at this head, the head of the round-3 fixes, over its (\d+) cases", doc)
        self.assertIsNotNone(m, "the docstring's bypass sentence names the head by role and the count of cases it was re-taken over")
        n = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]).countTestCases()
        self.assertEqual(int(m.group(1)), n, "the sentence's count of cases, %s, is this module's, %d: a case was added since the plants "
                                             "were re-taken, so re-take them (the three bypass plants and the alias control, each landed "
                                             "on the kernel, run and reverted with the three files hashed) and write the new count"
                                             % (m.group(1), n))


if __name__ == "__main__":
    unittest.main()
