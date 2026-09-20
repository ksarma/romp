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
one door both of the judge's boundary wrappers reach (`load_goals_shared_or_fault` resolves the name from the judge's globals at
each call and hands the object to `_or_fault`, which resolves no door name itself, so every spelling of the shared read
arrives at this door), and a
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
spells a door whole wherever it appears and whatever receives it (an ASCII bytes literal decoded, surrounding whitespace stripped and
str.lower applied read as the name: the three transforms _door_text undoes, one member of each family and not the family), and none
containing the name reaches a dynamic lookup, a dict read or a subscript key; a name completed at run time from constants that spell no
door whole and either carry the name in one piece to none of those receivers or reach one in a text those three transforms do not
restore (a bytes literal in another codec, a strip of other characters, another case fold) is outside every static pin here, a limit the
enumeration holds on its side; the consolidation pass, and the whole-spelling rule since the round-4 fixes), and the census's own forms,
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
took no read; held by execution since the round-5 fixes by the door witness's two raise-road drives, a symlink loop and a directory at
the store path, each propagating its OSError with no key moved; a call whose fill raises after its miss bump, a malformed journal row
raising out of the replay, moves that one call key and no second key, held by the witness's third raise-road drive since the round-5
consolidation), so per pass the delta of those five must equal the walk's, the gate's and the sweep's recorded calls
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
each per session in the pass loop, re-taken at this head (named by role in the round-7 paragraph below), over its 39 cases, one at a time with
the kernel, the judge and this module hashed before the plant, across the run and after the revert: the first two leave every case
green with no file changed across a run, so they stay outside every witness here; the third has been refused since the consolidation
pass by the kernel-wide birth pin, whose called population names `_PJ.load_goals_shared` as a fifth loader spelling, so a second judge
module is outside both execution witnesses and inside the static pin, which reds alone while every execution case stays green; and
the alias control beside them reds the shared reconciliation on each of the five harness cases that drive a pass, and the birth pin
(6 failed, 33 passed at this head; the door witness's fourteen cases run outside any pass, thirteen each driving
one call of the door under _drive (three of them, hit, compare_miss and dup, priming the cache with a call of their own before the
drive's window, and the refuse case calling again after it) and one reading the table, seventeen calls over the fourteen, counted by a
profile of the door's frames at this head, and stay green under the control, so it reds five of the nineteen
harness cases; review round 5, extra7-1: this sentence said every harness case, and one of the six at the head the round-5 ruling read
drove no pass; a verifier of the round-5 fixes: it then said the door witness's cases call the door, one of them reading the table;
review round 6, regression-2: it then said thirteen cases, twelve calling the door once, against sixteen calls the same profile
counted at the head of the round-6 fixes, the three primes and the refuse case's second call among them). Review round 3, correctness-2 and
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
twelve findings, round 2 fourteen, round 3 nine, round 4 seventeen, round 5 seventeen, round 6 thirteen (one refuted), and "the round-N fixes" are the changes that answer
round N's rulings. The
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
seventeen (the second-bump roster pin, the kernel-and-judge birth pin and the three enumeration cases are new). Three lenses
read the head, the reviewer ruled on what they found (the reviewer's rulings
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
here produces, reds the interpreter check alone, naming it (1 failed, 18 passed of 19); a fake node class planted into the ast
module at import reds the interpreter check naming Frobnicate (1 failed, 18 passed of 19); _walk passing an unknown node instead of
raising reds the refusal case, AssertionError not raised (1 failed, 18 passed of 19); a census walking a tree outside _walk reds the
refusal case's source pin, 2 spellings against 1 (1 failed, 18 passed of 19; that pin, a count of one spelling, is the structural
walker case's since the round-4 fixes); on 3.14t, TemplateStr and Interpolation removed red the interpreter check naming both and
the enumeration at F61, where _walk refuses the TemplateStr (2 failed, 17 passed of 19). The clean module with the table, at the
head of the round-3 fixes that added it, 19 cases: 19 passed single-process on 3.10, 3.11, 3.12, 3.13 and 3.14t, and with four
workers on 3.12 (review round 4, correctness-2 and regression-4: the figures of this paragraph read against 19 while its final
head had 20 cases and the clean line named no head, so each names its count now, the clean line its head by role, and the clean
module at the head of the round-4 fixes is pinned by the Docs case in the next paragraph). The bypass
plants (correctness-2, regression-2), re-taken at the head the round-4 ruling read, of 20 cases, each landed on the kernel alone, run single-process on
3.12 and reverted with the kernel, the judge and this module hashed before and after: the kernel opening and parsing the store
file itself, and the kernel calling jd._read_store_json, each per session in the pass loop, 20 passed each and no file changed
across a run; a second judge module loaded under another name, rebound to the state and its shared door called per session,
reds the kernel-wide birth pin alone, naming `_PJ.load_goals_shared` as a fifth loader spelling (1 failed, 19 passed; every case
green at both earlier heads, before the pin); the alias control, the shared door bound at kernel import
and called per session, 6 failed, 14 passed, the shared reconciliation on every harness case and the birth pin; and the count
pin: the sentence's count set to a stale figure reds the Docs case naming both figures (1 failed, 19 passed).

Review round 4 (2026-09-19; seventeen findings, none refuted, three mediums, and the reviewer's synthesis: three contracts stated
as lists, each falsified by the first construct nobody listed, fixed as one inversion keyed on the closed set rather than a longer
list). Two fixers landed the round's fixes, three verifiers read them and left nine findings, all low, and a consolidator closed the
nine; every state below was re-taken by the consolidator at the head of the round-4 fixes, over its 22 cases (the round's
fixes add two, the walker pin and the fill-road case), each landed on kernel/kernel.py, kernel/judge.py or this module and reverted
with the file checked clean, the module run single-process on 3.12 through the clean runner; a figure from an earlier head names
that head by role. The loader-naming string constant (correctness-1, tests-1,
extra6-1): the kernel-wide pin refuses a constant whose whole text is one of the four door spellings wherever it appears and whatever
receives it, and a constant that merely contains the name where it reaches a listed lookup, a dict read or a subscript key; by
whole-text equality the kernel and the judge carry zero such constants (the substring rule with docstrings excluded would cost the
judge three error strings and the kernel none), so the rule has no exception and needs no exemption row. Seven whole-spelling
constants at unlisted receivers as real loads in a replaced helper, handed to itemgetter, to getattr_static, to a partial of getattr,
to methodcaller and to an aliased getattr, as a match-mapping key and as a comparison operand in a generator over vars(jd), and three at
kernel module level, bound to a name, handed to a partial of getattr and as a dict key, each red the pin naming the constant, its
receiver and the def (1 failed, 21 passed each; the fixer's baseline at the head the round-4 ruling read, 20 passed of 20); the clean
kernel and judge stay green with the judge's three containing strings unreported. F07d moved from the assembled class to the string
class (the name bound to a variable is spelled whole in the constant the pin reads) and F45 from none to string (a dict key spelled
whole is refused wherever it appears); with the value clause disabled the enumeration reds at F07d, the first of the rows that clause
alone holds, F07d, F45 and F64 to F67 (1 failed, 21 passed; F07g stays a birth there, getattr being a listed lookup the consumer clause
walks into). Ten rows are new: the f-string, the conditional, the walrus and the needle-keeping concatenation as a subscript key
(extra6-2: the slice is walked as the Call clause walks its arguments; the three whole spellings as real loads in the replaced helper
each red the pin as a subscript key, 1 failed, 21 passed each, and with the clause reverted to a direct Constant the enumeration reds
at F30h alone, the other three staying caught by the value rule, 1 failed, 21 passed), methodcaller, itemgetter over vars(jd), a
partial of getattr and a match-mapping key (the doors the round found on no list), an f-string of the whole name handed to getattr
(one constant, refused) and an f-string assembling the name from pieces (assembled, outside, the JoinedStr limit the ruling names).
The walker contract (regression-3, extra7-1): the module's own AST is read for every reference to the four traversal names (the
standard walk, the child iterator and the two visitor classes), the names assembled at run time so the case's text holds none; every
reference sits inside _walk but for two exemptions named with their reasons, _loader_births' child listing for its parent map and the
refusal case's control comparison; a NodeVisitor subclass, a from-import of the walk under an alias, a module alias walking, a getattr
with the name in a string and a child-iterator recursion each planted at module level red the pin naming the line, the name, the form
and the enclosing def (1 failed, 21 passed each; the fixer's baseline at the head the round-4 ruling read, 20 passed of 20), the
_loader_births row removed reds it naming that real site (1 failed, 21 passed), and a bogus row reds it as an exemption with no
reference (1 failed, 21 passed). The bound's third clause (tests-2, regression-2, extra4-1): the roster pin reads, for every
second-key bump in the door's body, the innermost statement list holding it, asserts that list carries exactly one second-key bump
over the full subtrees of its statements and ends in a Return or a Raise, and derives the fill road's entry keys as the call keys
whose list falls through, asserting them equal to SHARED_FILL_KEYS, which _pass sums; a refuse bump beside the dup bump reds the
at-most-one clause, 2 against 1 (1 failed, 21 passed), the refuse block's return replaced by a pass reds the ends-in-Return clause
naming the Pass (1 failed, 21 passed), an absent bump below the miss bump reds the derived fill keys, absent among them, with the
shared reconciliation of the five cases that call the door (6 failed, 16 passed), a return added after the compare_miss bump reds the
derived keys the other way, miss alone (1 failed, 21 passed), and every handler body collected a second time reds the count of lists
against bumps, 7 against 5 (1 failed, 21 passed); the refuters' baseline for a second bump beside an existing one and for a new fill
key was 20 passed of 20 at the head the round-4 ruling read. By execution, a store whose bytes do not parse, read once through the
door for the never-walked sid, bumps miss once, corrupt once and hands off once (TheDoorBumpsAtMostOneSecondKeyPerCall), and a dup
bump spelled through __setitem__ beside the corrupt bump reds that case alone, the AST clause reading neither spelling (1 failed, 21
passed). The dup and refuse layer (extra5-1): a dup bump and a refuse bump planted after the walk's read and conditioned on its miss,
so each rides beside a genuine fill, each red _pass's zero line at the first pass of the three cases whose first pass fills, {'dup':
2} against {} with the bound green at two fills (3 failed, 19 passed each; every case green at the head the round-4 ruling read). The
identity lines (correctness-3): the gate decorator's wraps dropped reds the walk census's identity line naming the wrapper gated
(1 failed, 21 passed; the site count's 0 against 1 at the head the round-4 ruling read, a true red with a false cause), and a
decorator without wraps on the gate factory reds the gate scan's identity line naming its wrapper, alone with nothing planted
(1 failed, 21 passed) and beside the harness ceilings and the per-spelling dict with a shared load planted in the gate's body
(7 failed, 15 passed; the ceilings alone at the head the round-4 ruling read, the scan green reading the wrapper). The population
(tests-3): one writer-door call site re-doored to the shared door reds the per-spelling dict, 26 and 8 against 27 and 7 with the sum
unchanged at 58, and one removed reds it 26 against 27 (1 failed, 21 passed each; the set assertion green under both at the head the
round-4 ruling read). The messages (tests-4, regression-5, extra7-2): the pair beside a fill, a corrupt bump and a goal_io loads bump
after the walk's read, reds the first pass's writerLoads line 2 against 0 and the two unwalked-sid sweep cases' hand-off lines
2 against 0 and 3 against 1, each naming the pair and printing writerLoads, the call counters and the second bumps (3 failed, 19
passed; the same three lines at the head the round-4 ruling read, each naming another cause); a row's limit set outside _LIMITS reds
naming the classes by their count, five (1 failed, 21 passed); TypeIgnore deleted from the ast module at import reds the interpreter
check naming the removal as the third cause (1 failed, 21 passed). The staleness (correctness-2, regression-4): the round-3
paragraph's figures are labelled with the count they read against and its clean line with its head by role, and the clean module at
that head is pinned by the Docs case beside the bypass count, the line's figures summed against the loader's count; the clean figure
set one below reds the Docs case at the clean line, 21 against 22 (1 failed, 21 passed), the bypass count set one behind reds it at
the bypass line (1 failed, 21 passed), and the round-3 clean line set to 18 leaves the module green (22 passed), the historical lines
being labelled and not pinned, the ruling's alternative.

The verifiers of the round-4 fixes (nine findings, all low), each closed and re-taken at the head of the round-4 fixes, over its 22
cases; a state's earlier figure reads at the head the verifiers read, where the Docs count pin was red at every case
count, so "green" there means every case but that pin. The residue of the string pin (the inversion verifier's first): the prose
named the residue as a name assembled from pieces that split the needle while four working doors that split no needle escaped every
witness, a bytes literal decoded at getattr, an upper-cased constant lowered there, a padded constant stripped and bound first, and a
bytes literal decoded as a subscript key (each green at the head the verifiers read); both clauses of the pin read a constant's text
through _door_text now (an ASCII bytes literal decoded, surrounding whitespace stripped, str.lower), so each reds the pin naming the constant and its receiver (1 failed, 21
passed each), while a needle-keeping concatenation handed to a partial of getattr and a reversed literal at getattr stay green
(22 passed each), the assembled residue the limit sentences state by the pin's boundary; seven rows hold it, and with the bytes
decode, the strip and the lower disabled in turn the enumeration reds at F70, F69 and F68 (1 failed, 21 passed each), and with the
consumer clause's gate dropped it reds at F72 beside the birth pin on the judge's three containing strings (2 failed, 20 passed). The
walker finder's roads (the inversion verifier's second): the attribute and getattr forms were keyed on the names the ast module was
imported under, and a walk through importlib.import_module, __import__, sys.modules or a name rebound to the module passed the pin
(each green at the head the verifiers read); keyed on the four names alone, each road reds the pin naming its spelling, a getattr on
sys.modules["ast"] too (1 failed, 21 passed each), a walk read from vars(ast) by string stays green as the stated limit (22 passed),
the finder narrowed back to the bare module base reds the case's module-alias sample (1 failed, 21 passed), and a finder reading a
call's subscript key as a reference reds the case's limit sample (1 failed, 21 passed). The finally clause (the third-clause
verifier's): a second-key bump under a finally beside the corrupt handler left the AST clauses green with the execution case alone
red, and beside the unreadable_journal handler, a road no case drives, every case green (at the head the verifiers read); the pin
refuses a bump under any finalbody and a second-key list ending in a raise under a try statement, a sibling hole the consolidator
found, so the first reds the pin beside the execution case (2 failed, 20 passed), the second reds the pin alone (1 failed, 21
passed), and a corrupt list ending in a raise that an outer handler catches to bump dup reds the pin beside the execution case
(2 failed, 20 passed; the execution case alone at the head the verifiers read). The prose (the prose verifier's six): this paragraph
carried one fixer's states and no figure for the round's three mediums, the bypass sentence counted 20 cases against 22 with the
Docs count pin red at every head of the fixes, the breakdown message counted five doors on no list where four were, seven figures
carried no head label, the provenance paragraph stopped at round 3, and a clause of _loader_sites' docstring had no verb; each is
closed in the module, this paragraph re-taking every state at one head. The bypass plants and the alias control, re-taken at the head
of the round-4 fixes over its 22 cases (the bypass sentence in the first paragraph named the same head and count until the round-5
re-take), each landed on the kernel alone with the kernel, the judge and this module hashed before and after: the kernel opening and
parsing the store file itself, and the kernel calling jd._read_store_json, each per session in the pass loop, 22 passed each and no
file changed across a run; a second judge module loaded under another name reds the birth pin alone, naming `_PJ.load_goals_shared`
(1 failed, 21 passed); the alias control, the shared door bound at kernel import and called per session, reds the shared
reconciliation on each of the five harness cases that drive a pass, 2 against 0, 7 against 5 twice, 6 against 4 and 3 against 1, and
the birth pin (6 failed, 16 passed; review round 5, extra7-1: this sentence said every harness case while the sixth, the corrupt-road
case, called the door outside a pass and stayed green). The clean module at the head of the round-4 fixes: 22 passed single-process
on 3.10, 3.11, 3.12, 3.13 and 3.14t, and with two workers on 3.12.

Review round 5 (2026-09-20; seventeen findings, none refuted, one medium, sixteen lows, and the reviewer's ruling on approach: five
rounds each closed what was asked and the same class returned one construct over, because pinning a shape property by AST is a
list-of-syntax problem by construction, so each AST clause is kept as an early warning that refuses the forms it names and is silent
on the rest, and the two contracts, the walker's and the at-most-one, are carried by execution). The reviewer's correction: four
findings said the roster pin walks outside _walk at its iter_fields read; it does not (the traversal is _walk, and iter_fields lists
a walked node's fields), and no exemption row was added there. Three fixers landed the round's fixes in sequence, the two execution
witnesses, the finder and the Docs count pin, and the prose; three verifiers read them and left fifteen findings, one medium and
fourteen lows, and a consolidator closed the fifteen (the next paragraph). Every state below was re-taken by the consolidator at
the head of the round-5 fixes, over its 37 cases (the round adds fifteen: the walker witness's three, the door witness's
eleven beyond the corrupt case, and the consolidation's drive of the fill's own raise road), each landed on kernel/kernel.py,
kernel/judge.py or this module at the head of the round's last code change, one docstring-only commit before this one, which adds no
case, and reverted with the planted file and the kernel, judge and module triple hashed before the plant and after the revert and
found equal, the module run single-process on 3.12 through the clean runner. The walker contract by execution (correctness-2,
tests-1, extra5-2, regression-2): every census entry point of this module,
the roster of eight rows in _CENSUSES read against a derivation over its own AST (_census_floor), refuses a stranger statement
planted at each of three sites alone and at all together, naming its class, and unplanted returns; _loader_sites rewritten as an
ast.iter_fields recursion around _walk reds the witness naming it at the module site, the def site and the sites together (its tree,
one helper's source, offers no class body) while the finder case stays green (1 failed, 36 passed; the finder is silent on that
class by design, and its class docstring says so); a hand-rolled census handed a tree, added as a ninth row, reds the witness naming
it while the floor stays green, the stated boundary (1 failed, 36 passed); its roster row removed with the count set to seven reds
the floor naming the def and the no-class list (2 failed, 35 passed), and the count set one off reds the count line (1 failed, 36
passed); _walk's refusal disabled reds the witness with every row and site named as having passed the stranger over, the refusal
case and the witness's own control (3 failed, 34 passed); a NodeVisitor subclass at module level, the plant the finder is known to
catch, reds the finder case alone (1 failed, 36 passed). The at-most-one by execution (correctness-1, regression-1, extra6-1,
extra6-2): the door witness drives one road per key of both rosters and three raise roads on the real door and asserts the exact
keys per road and at most one second key per call; a helper defined inside the door bumping dup from the corrupt handler, a Return
whose expression raises into an outer handler that bumps dup, and a raising statement in the corrupt list under such a handler each
red the corrupt drive, two second keys against one, corrupt and dup, with the roster pin's AST clauses green (1 failed, 36 passed
each), as does the round-4 plant the clauses are known not to read, a dup bump through __setitem__ beside the corrupt bump (1
failed, 36 passed); a dup bump planted as the first statement of each callee derives the witness per callee the roster pin's
docstring states: in _shared_forget it reds the absent, unreadable_journal, corrupt, open_raises and read_raises drives and the
no-store sweep case (6 failed, 31 passed); in _guard_nodes and in _finish_load the miss, compare_miss, dup, refuse,
unreadable_journal and fill_raises drives and the four harness cases with fills, and not the corrupt drive (10 failed, 27 passed
each); in _freeze_store the miss, compare_miss, dup and refuse drives and the four fill cases (8 failed, 29 passed); in
_journal_read every fill-road drive, fill_raises among them, and the four fill cases (11 failed, 26 passed); in _disk_parse those
but unreadable_journal (10 failed, 27 passed); refuse dropped from SHARED_SECOND_KEYS reds the coverage case naming it, the roster
pin and the refuse drive (3 failed, 34 passed), a key added to that roster with no drive reds the coverage case naming it and the
roster pin (2 failed, 35 passed), and the dup drive's method renamed off the road rule reds _drive's name check in it and the
coverage case (2 failed, 35 passed). The finder (extra5-1, tests-4, extra5-3): a getattr with the walk in a no-placeholder f-string
and a from-import through a sys.modules alias, each planted at module level, red the finder case naming the line and the form (1
failed, 36 passed each; both left the module green at the head the round-5 ruling read), the getattr clause reverted to a direct
Constant reds the two f-string sample rows, the from-import branch narrowed back to the module road reds the alias row, a misspelled
traversal name reds the derivation check naming it, and the same misspelling with that check disabled reds the name's sample row (1
failed, 36 passed each), the samples spelled independently of the roster they test. The Docs count pin (tests-2): this paragraph's
count set one below and the first paragraph's count set one below each red it naming the figure and its fragment, a historical
fragment relabelled this head at its own count reds it the same way, a second current head left standing beside this one reds its
one-head line naming rounds 4 and 5, the clean line one below reds its sum, a second clean line reds its one-line count, a
historical label removed reds its unlabelled line, and two counts in one fragment red its one-count line (1 failed, 36 passed each);
the battery paragraph's count spelled as a word changed leaves the module green, the stated unread form (37 passed). The transform
limit (tests-3, regression-3, extra4-1), held on its side by three enumeration rows, F75 to F77, and by kernel plants as real loads
in the real _closer_settled, a replaced helper whose body never runs under the harness: the door's name as a utf-16 bytes literal
decoded at getattr, and a chars-strip of a padded name handed to a partial of getattr, each leave the module green (37 passed each,
the assembled class), while the same bytes literal in ASCII at getattr and the chars-strip handed to getattr itself, a listed
receiver, each red the birth pin naming the constant and its receiver (1 failed, 36 passed each, the string class); _door_text
widened to a utf-16 decode, to a strip of the padding characters and to casefold reds F75, F76 and F77 in turn (1 failed, 36 passed
each). The bypass plants and the alias control, re-taken at the head of the round-5 fixes, over its 37 cases, each landed
on the kernel alone with the kernel, the judge and this module hashed before the plant, across the run and after the revert: the
kernel opening and parsing the store file itself and the kernel calling jd._read_store_json, per session in the pass loop, 37 passed
each and no file changed across a run; a second judge module loaded under another name reds the birth pin alone, naming
`_PJ.load_goals_shared` (1 failed, 36 passed); the alias control, the shared door bound at kernel import and called per session,
reds the shared reconciliation on each of the five harness cases that drive a pass, 2 against 0, 7 against 5 twice, 6 against 4 and
3 against 1, and the birth pin (6 failed, 31 passed). The clean module at the head of the round-5 fixes: 37 passed
single-process on 3.10, 3.11, 3.12, 3.13 and 3.14t, and with two workers on 3.12.

The verifiers of the round-5 fixes (three lenses, fifteen findings, one medium and fourteen lows: the adversarial lens's five, the
fixtures lens's three, the prose lens's seven), each closed and re-taken at the head of the round-5 fixes, over its 37
cases; a state's earlier figure reads at the head the round-5 verifiers read, over its 36 cases, where the clean module read 36
passed on the five interpreters and with four workers on 3.12. The walker witness's plant sat at two sites with one refusal per
drive accepted (the adversarial lens's medium): _census_floor with its module level read by hand, and _traversal_references the
same, each left the module green at the head the verifiers read, the def plant refused and the module-level plant passed over; the
plant lands at three sites now, each driven alone and then together, so those two shapes red the witness naming the census and the
site, the module site and the class site for the first and the module site for the second (1 failed, 36 passed each), and the class
site disabled in the plant reds the landing check naming the rows whose tree holds a class (1 failed, 36 passed). The floor's
boundary (the adversarial lens's first low): an unregistered census parsing through compile with ast.PyCF_ONLY_AST, and one parsing
through the module under an alias, each walking by hand, leave the module green while the same def through ast.parse reds the floor
naming it (37 passed, 37 passed, and 1 failed, 36 passed; the same three states at the head the verifiers read), and _census_floor's
docstring, the roster's comment and the witness's docstring state the boundary as the code has it, the spelling of the reader. The
fill's own raise road (the adversarial lens's third low): a journal row whose instant is not a number raised out of _finish_load
after the miss bump with no second key, on a road no drive reached and the undriven list did not name, and a dup bump in a handler
around _finish_load left the module green at the head the verifiers read; the twelfth road drives it, that bump reds the drive at
its raise (1 failed, 36 passed), and the raise swallowed reds it the same way (1 failed, 36 passed). The arrangement's limit (the
fourth low): a dup bump conditioned on a two-node store after _finish_load leaves every drive green at both heads (36 passed there;
37 passed here), since no drive arranges a store of more than one node, every drive is on one sid and calls once, stated in the
witness's docstring and its message (the round-5 wording, every drive seeds one node, was false for the five drives that seed none;
the round-7 close weakened it). The
fifth refused form (the fifth low): a second-key bump that is not a statement of a list, an assignment's value, reds the roster
pin's count of lists against bumps and the miss, compare_miss, dup, refuse and fill_raises drives and the four fill cases (10
failed, 27 passed; 9 failed, 27 passed at the head the verifiers read), named in the early-warning sentences now. The Docs count pin
(the fixtures lens's first two lows): a stale count written before a fresh one in the same fragment left the module green at the
head the verifiers read and reds the one-count line now (1 failed, 36 passed), and the pin's docstring says what the sweep reads and
what it does not. The getattr under another name (the fixtures lens's third low): the rebound name as a real walk at module level
leaves the module green at both heads (36 passed; 37 passed), the stated silence, held by two limits rows, and the getattr form
widened to the rebound name reds the first of them (1 failed, 36 passed). The prose lens's seven: the at-most-one clause's message;
the enumeration docstring's claim that the limit texts cannot overstate (the assembled text rewritten to a false universal left the
module green at the head the verifiers read; the texts are messages no assertion reads, said so now); the derivation check's
self-contradicting comment (a misspelled name with the check off reds the sample row, 1 failed, 36 passed); 'every road of both
rosters' at four sites; 'every census' at two; the door witness's case count in the first paragraph; and the three assembled
enumeration rows tests-3's Fix line asked for, each landed.

Review round 6 (2026-09-20; the reviewer's five lenses on the round-5 instruments, each judged by whether it sees what the syntax
lists could not: the splice-site population, the roads' derivation, the silence sentences, the independent source, and the round-5
items spot-checked). Three fixes landed, each with its states, and every state below was taken at the head of the round-6
fixes, over its 38 cases (the round adds one, the walker witness's instrument case, in its first fix): the point-1 states on the tree of
the round's first fix, the point-2 states on the tree of its second, and the first paragraph's bypass plants and alias control on the
tree of its third, the round's last change but this paragraph, which adds no case; each landed on kernel/kernel.py, kernel/judge.py or
this module and reverted, the kernel, the judge and this module hashed before the plant and after the revert and found equal, the
module run single-process on 3.12 through the clean runner. Lens one, the splice-site population: the walker witness planted its
stranger at three hand sites, the module body's end, the first def's body and the first class's body, three of the 147 node positions an exec-mode Module offers on 3.12 and all of them statement lists, so a
hand-rolled walk substituted for _walk that read any other position class by hand (a decorator list, a call's arguments, a
comprehension's generators, an f-string's values, a match statement's cases, annotations and type parameters, the nested statement
lists, AsyncFunctionDef.body) kept the witness's three cases green, and one plant per position class was green under a walk reading
ClassDef.body alone, so the unit is the position; the positions are derived now (_grammar_positions, every field of every concrete
class the interpreter defines observed non-empty over a synthetic corpus or red naming the field) and planted each alone
(_plant_at), 147 positions and 1323 drives on 3.12, 153 and 1377 on 3.14, 136 and 1224 on 3.10, 140 and 1260 on 3.11, 150 and 1350
on 3.13, the roster holding nine rows with the derivation itself the ninth. The derived plant found the one position where the
refusal did not come first: the finder read every name's `.name` at the ImportFrom and raised AttributeError on a stranger among the
names before the walk reached it; it reads alias nodes alone now. The states: the alias read unguarded reds the plant case naming
_traversal_references at position ImportFrom.names as having raised AttributeError instead of the grammar refusal (1 failed, 37
passed); _census_floor reading class bodies by hand at the module level reds the plant case naming it as having passed the stranger
over at ClassDef.bases and five more class positions, and the roster case, whose read of the inline methods empties under that walk
(2 failed, 36 passed); _traversal_references reading the module level by hand reds the plant case (1 failed, 37 passed); the match
statement cut from the corpus reds the derivation naming the twenty match fields, in the plant case, the instrument case and the
negative control (3 failed, 35 passed); the keyword container row removed reds the plant case at keyword.value and the instrument
case, each naming the base (2 failed, 36 passed); the planter planting a statement at the module level whatever the position reds
the instrument case alone, the plant case staying green since every module-level plant is refused (1 failed, 37 passed); the roster
count set to eight reds the count line, and the derivation's row removed with the count at eight reds the floor naming
_grammar_positions (1 failed, 37 passed each); _walk's refusal disabled reds the plant case, the refusal case and the negative
control's control (3 failed, 35 passed), the run taking 271 seconds where the clean module takes 38, since every drive then walks
the whole kernel. Lens two, the roads' derivation: the coverage case derived the key set of ROADS against the rosters, so a new key
with no drive red it naming the key and the roster pin red a key the rosters did not hold, but the derivation was keyed on names and
a second site bumping an already driven key was on no driven road with the module green (the lens's plant, a second refuse branch on
state no drive arranges); the door's bump sites are read as (key, ordinal) now, each row of ROADS names the sites its call executes,
each drive holds that by a trace of the door's frame (_line_trace), and the coverage case derives that the door's sites are the
rows' sites plus UNDRIVEN_SITES, none in both. The states: the same second refuse branch reds the refuse drive by execution, its call
executing the second refuse site where the row names the first, and the coverage case naming the first site at its line as one no
drive executes and no statement names (2 failed, 36 passed); UNDRIVEN_SITES emptied reds the coverage case naming the _unread arm's
site (1 failed, 37 passed); the corrupt row's sites column naming the miss site alone reds the corrupt drive by execution and the
coverage case's row consistency, sites against deltas (2 failed, 36 passed); the corrupt site stated undriven reds the coverage case
as a site a drive executes (1 failed, 37 passed); the tracer recording nothing reds every drive whose road bumps, ten, and leaves the
two raise roads green, which execute no site (10 failed, 28 passed); the dup and refuse arms swapped in the door leave the module
green (38 passed), the stated control: a site is (key, ordinal), so a moved site is the same site. Lens three, the silence sentences:
the lens planted every form the roster pin's sentences claim silence on and each ran silent, and three boundary variants the
sentences do not claim silence on each red by the clause the module names; two sentences named a construct where a form was meant,
and say the form now (a second-key raise list under a contextlib.suppress with statement; a helper defined outside the second-key list
that calls it), prose only. Lens four, the independent source: the lens established that _TRAVERSAL's samples are literal rows that
read the constant nowhere, that the interpreter pins the spelling and the rows the membership, and that a derivation from vars(ast)
would spell the four names by hand in another form, so nothing changed. The bypass plants and the alias control, re-taken at the
head of the round-6 fixes over its 38 cases, each landed on the kernel alone with the kernel, the judge and this module hashed before the plant, across
the run and after the revert: the kernel opening and parsing the store file itself and the kernel calling jd._read_store_json, per
session in the pass loop, 38 passed each and no file changed across a run; a second judge module loaded under another name reds
the birth pin alone, naming `_PJ.load_goals_shared` (1 failed, 37 passed); the alias control, the shared door bound at kernel import
and called per session, reds the shared reconciliation on each of the five harness cases that drive a pass, 2 against 0, 7 against
5 twice, 6 against 4 and 3 against 1, and the birth pin (6 failed, 32 passed). The clean module at the head of the round-6 fixes: 38
passed single-process on 3.10, 3.11, 3.12, 3.13 and 3.14t. Re-taken at the head of the round-7 fixes, over its 39 cases, by the
round's records pass: every state above reads the same failed and passed figures there but for the case count, with three exceptions. UNDRIVEN_SITES
emptied cannot be landed at that head, the dict being empty since the unread road was driven (the round-7 paragraph's
row-and-method-removed state is its successor). The tracer recording nothing reds every drive whose road executes a site, eleven
with the unread drive, and the coverage case's control over the trace's nested code objects, and leaves the two raise roads that
execute no site green (12 failed, 27 passed). The first bypass plant, the kernel opening and parsing the store file itself, red the
five harness cases that drive a pass at their cleanup on the tree of the round's door-names fix, naming __warningregistry__ and no
stub (5 failed, 34 passed), its unclosed handle warned about by the collector from the kernel's frame; the round's warnings-registry
fix sets that name aside and the plant leaves every case green since (39 passed).

Review round 7 (2026-09-20; the reviewer's standard after round 6: no instrument in this module carries a hand-written population on
any axis where the module can compute one, and every instrument states which axes it derives and which it bounds). Ten fixes landed,
nine planned and one the records pass found, and every state below was taken at this head, the head of the round-7 fixes, over its
39 cases (the round adds one, the door witness's unread road), each landed on kernel/kernel.py, kernel/judge.py or this module and
reverted, the kernel, the judge and this module hashed before the plant and after the revert and found equal, the module run
single-process on 3.12 through the clean runner; where a plant left the module green on the tree before its fix the paragraph says
so in words, and every figure is this head's. The census floor (regression-1, extra4-2 and tests-3): _census_floor read two
container shapes, a module-level def and a direct method of a module-level class, so a reader in any other container was attributed
to nothing; it attributes every reader reference to its nearest def or class chain over the whole tree now, and the roster case pins
the class chains and the module statements with a reason each. The states, each green before the fix: a census written as a method
of the roster pin's class that spells ast.parse and inspect.getsource and walks node._fields by hand, a nested class's method
reading through _walk, a class-body statement calling _walk over ast.parse, a method handing _walk to map as a value, and a
module-level statement outside _CENSUSES reading through _walk each red the roster case naming the chain, or the statement's target
(1 failed, 38 passed each); the round-6 state, _census_floor reading class bodies by hand at the module level, reds the plant case
naming it as having passed the stranger over at ClassDef.bases, four more class positions and Module.type_ignores, and the roster
case, whose class rows empty under that walk (2 failed, 37 passed). The traversal roster (extra7-1): the finder's samples pinned the
roster one way, a sample naming a name outside it red and a roster name with no sample did not; the sets are held equal both ways
now, so a fifth name the module spells nowhere added to _TRAVERSAL and the NodeTransformer sample row removed, each green before,
each red the membership line naming the name (1 failed, 38 passed each). The unread road (extra5-1, extra6-2 and tests-5): the
door's `if store.get("_unread")` arm, the second unreadable_journal site, was the one row of UNDRIVEN_SITES on the ground of the
door's own comment, which calls the arm unreachable while the journal's rows arrive as lines; the comment is right about the
replay's mark, which a replay handed lines never sets, and the arm is reachable with no code change through the store file's own
content, a top-level _unread key the writer never serializes and a hand-written or foreign file can carry, since nothing between the
parse and the arm strips it. The witness drives it now, a thirteenth row of ROADS and a method that writes the key into the seeded
store file, UNDRIVEN_SITES is empty with its mechanism kept, and the coverage case's derivation is unchanged. The states: the row
and its method removed reds the coverage case naming the arm's site as one no drive executes and no statement names, and the Docs
count, 39 against the 38 cases left (2 failed, 36 passed); a helper defined inside the door on that arm bumping dup through an alias
of the counters, a form no clause of the roster pin reads and green before the road was driven, reds the unread drive at the line
where the sites the trace saw and the keys the counters moved must agree (1 failed, 38 passed); the same helper bumping through the
spelling the clauses read reds the dup drive's sites, the coverage case, the roster pin's deep count and the unread drive (4 failed,
35 passed). The two false sentences (regression-2; tests-2 with regression-3): the first paragraph's alias-control sentence said the
door witness's thirteen cases run outside any pass, twelve calling the door once, where a profile of the door's frames counts
seventeen calls over fourteen cases, thirteen under _drive and one each before the window in the three priming cases and after it in
the refuse case, the figures the sentence carries since (no assertion reads it; the profile at this head is the state); the case
count's 'reads against N' copies, one each in the paragraphs of the consolidation pass and rounds 4, 5 and 6, sat in fragments the
split at '3.12' left with no head label, so a stale copy was green wherever it stood; the copies are removed and the Docs case reads
this paragraph whole by a census of its figures, so a stale copy written into this paragraph reds it naming the clause (1 failed, 38
passed) while the same copy in a historical paragraph leaves the module green by design (39 passed). The axis statements, the
standard's second clause: every instrument's docstring carries a sentence naming what it derives and what it bounds, prose no
assertion reads (of this module's docstrings the Docs case reads the module's own alone), each checked against the code; a Bounds
sentence made false and a Derives clause negated each leave the module green (39 passed each), the stated bound. The hand-off keys
(the plan's hunt for a seventh hand-written axis, the class of extra7-1 and tests-2): SHARED_HANDOFF_KEYS was pinned by nothing
while its three siblings are pinned against the door's AST; the roster pin derives the keys from the door's statement lists, the
direct bump keys of every list whose last statement returns a call of load_goals, and holds them equal to the tuple both ways, and
the door witness's coverage case derives from the same lists each road's hand-off column and the no-hand-off sites of hand-off keys,
the _unread arm alone. The states: dup added to the tuple, which also narrowed _pass's dup and refuse zero line to refuse alone, and
corrupt removed from it, each green before, each red the roster pin naming the key (1 failed, 38 passed each); the corrupt handler's
hand-off rewritten through a temporary, `store = load_goals(fsid)` then `return store`, reds the roster pin naming corrupt and the
coverage case at the corrupt row's hand-off column, 1 against 0 (2 failed, 37 passed), and the coverage case alone with the tuple
edited to match (1 failed, 38 passed). The door trace (the hunt's second find): _line_trace read frames whose code was the door's
own code object, a singleton, while the door's nested code objects are computable; it reads the door's code object and every code
object reachable through co_consts now. The states: the corrupt bump moved into a helper defined inside the door's ValueError
handler, its body a bump and a return, red the corrupt drive's executed-sites line with a false cause before the fix, the site
having run in the helper's frame, and reds the two hand-off lines alone since, a true reading of the helper's list, which hands
nothing off (2 failed, 37 passed); the round-5 shape, a helper inside the door bumping dup from the corrupt handler, reds the
corrupt drive at its executed-sites line naming the dup site, the dup drive's sites, the coverage case and the roster pin (4 failed,
35 passed); the remaining bound, a dup bump first in _shared_forget, a callee defined outside the door, reds six drives at the
agreement line and the no-store sweep case (7 failed, 32 passed). The cleanup's restore (the hunt's third find): CASE_KM and CASE_JD
bounded what _restore put back while nothing checked that a case replaced only those; setUp keeps its first snapshots and _restore,
after the saved names go back and the root is rebound, checks every kernel and judge global against them by identity, the names the
restoring rebind moves subtracted, and puts a leaked name back. The states, each green before with the stub live for every later
test: the wedge-gate sweep case standing a new-identity pass-through on km._nudge_response_ready, a kernel name in neither list,
reds that case at its cleanup naming the kernel name, as do a pass-through on jd._journal_key and a kernel global the case adds and
never deletes (1 failed, 38 passed each). The door names' copies (the hunt's fourth find): the four door names were spelled by hand
three times, in _DOOR_SPELLINGS, in the birth pin's defs line and in the enumeration's stub judge, copies pinned to each other by
nothing; the defs line reads the constant, the stub judge is built from it, and the birth pin holds the constant against the
spellings the kernel calls and against the judge's defs both ways. The states: a fifth spelling added to the constant, green before,
reds the birth pin naming it as one the kernel never calls, and a spelling removed reds the same line naming it as called and not
spelled (1 failed, 38 passed each). The warnings registry (the records pass's find, re-taking the bypass plants): the restore's
check read every name of both modules' globals as a case's rebinding, and the interpreter writes one of its own,
__warningregistry__, which the warnings module creates in the globals of the module a warning is attributed to on the first warning
raised from its code, so the first bypass plant, whose unclosed handle the collector warned about from the kernel's frame, red the
five harness cases that drive a pass at their cleanup naming the registry and no stub, as did a warnings.warn call in the pass loop
(5 failed, 34 passed each, on the tree of the door-names fix); the name is set aside, stated as a bound with its reason beside the
tick allowance, and both plants leave the module green since (39 passed each) while the leak plants above red as before. The bypass
plants and the alias control, re-taken at this head: the kernel opening and parsing the store file itself and the kernel calling
jd._read_store_json, per session in the pass loop, leave every case green with no file changed across a run (39 passed each); a
second judge module loaded under another name reds the birth pin alone, naming `_PJ.load_goals_shared` (1 failed, 38 passed); the
alias control, the shared door bound at kernel import and called per session, reds the shared reconciliation on each of the five
harness cases that drive a pass, 2 against 0, 7 against 5 twice, 6 against 4 and 3 against 1, and the birth pin, the door witness's
fourteen cases green under it (6 failed, 33 passed). The round-6 paragraph's states were re-taken at this head as well, and that
paragraph's last sentences record the result. The clean module at this head, the head of the round-7 fixes: 39 passed single-process
on 3.10, 3.11, 3.12, 3.13 and 3.14t.

Drives the real pass (_auto_nudge_tick) over two alive sessions with real transcript files and real goal stores, on the
suite's fake clock (the pass takes `now`). SYNTHETIC fixtures only; a PRIVATE synthetic sid pair (the goal-store fixture
rule), their override journals cleaned in the teardown; the state root rebound through jd._rebind_state and `off` written
into its session-hosts."""
import ast
import contextlib
import errno
import functools
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
import unittest.mock
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
# in _pass reads; _pass's dup and refuse zero line reads the second keys outside this tuple. The roster pin in TheCountersOneSite
# derives the keys from the door's AST, the direct bump keys of every statement list whose last statement returns a call of
# load_goals (_door_hands_off), and asserts them equal to this tuple both ways, so a key that starts handing off, or one of these
# that stops, reds there (review round 7, the plan's hunt for a seventh hand-written axis: this tuple was pinned by nothing while
# its three siblings were pinned against the door's AST, and dup added to it, which also narrowed the zero line to refuse alone, or
# corrupt removed from it left the module green). The door's _unread arm bumps unreadable_journal with no hand-off. The door's own
# comment calls the arm unreachable while the journal's rows arrive as lines, which is true of the replay's mark alone: a store file
# carrying a top-level _unread key reaches it with no code change, since nothing between the parse and the arm strips the key, and
# the door witness drives it (the unread road, 0 hand-offs, outside any pass). The witness reads from the same lists, per bump site,
# whether its list hands off, ties each road's hand-off column to the count over its sites, and derives the no-hand-off sites of
# hand-off keys, that arm alone today, which no row of UNDRIVEN_SITES may hold: _pass's writer reconciliation counts every bump of a
# hand-off key as a load, so a pass that reached such a site reds there, loud, and its only witness is a drive that reads 0 hand-offs
# at it.
SHARED_HANDOFF_KEYS = ("absent", "fallback", "corrupt", "unreadable_journal")
# The door's second bumps, read from load_goals_shared's body (judge.py): below the call-key bumps the fill road, entered after the
# miss or compare_miss bump, bumps at most one of these and returns (by execution, TheDoorBumpsAtMostOneSecondKeyPerCall).
# unreadable_journal: _journal_read raised OSError (a hand-off to load_goals), or the store carries _unread after the replay (no
# hand-off; the door's comment calls that arm unreachable through the replay's mark, and a store file carrying the key reaches it: the
# witness's unread road). corrupt: _disk_parse raised ValueError (a hand-off). dup: a concurrent fill of
# the same version published first. refuse: the archive key moved under the replay. The fallback, absent and hit returns bump none
# of them, so per pass their sum never exceeds the fills, the call keys whose bump falls through into the fill road
# (SHARED_FILL_KEYS below, miss and compare_miss): _pass's second-bump bound (ruling 1 of the reviewer's rulings on the pre-emption).
# The bound rests on three premises about the body. Two are pinned against the door's own source by the roster pin in
# TheCountersOneSite: the keys the door bumps are the two rosters exactly, and every second-key bump sits below every call-key bump.
# The third, that a call bumps AT MOST ONE second key, is carried by execution: TheDoorBumpsAtMostOneSecondKeyPerCall drives one
# road per key of both rosters, nine, a second road for the unreadable_journal key's second site, and three raise roads on the real
# door and reads the counters per call, and ties each drive to the door's bump SITES by a trace of the door's frame, every site of
# the door driven by a row, or stated undriven with its reason, none today (review
# round 6, lens two: a second site under an already driven key was on no driven road with the module green). The roster pin's
# AST clauses are an early warning for that premise: they refuse the forms they name (a second-key bump that is not a statement of a
# list, an assignment's value, a with item or a lambda body, say; a second-key list holding two; a list not ending in a return or a
# raise; a bump under a finally clause; a second-key raise list under a try statement) and are silent on the rest (a helper defined
# inside the door, outside the second-key list that calls it, its body reading as a clean list of its own; a return whose expression
# raises into a bumping handler; an exception from a clean list's other statement caught by one; a second-key raise list under a
# contextlib.suppress with statement, which the raising clause, reading try statements alone, does not see; and any construct nobody
# listed), each of which the witness catches
# on the road it sits on when a drive reaches that road; no drive arranges a store of more than one node, every drive is on one sid
# and calls the door once, so a bump conditioned on state no drive arranges is on no driven road, stated in the witness's docstring (review round 4, tests-2,
# regression-2 and extra4-1: the pin read the first two premises and the third was
# held by reading the body; a verifier of the round-4 fixes: a bump in a finally clause left the list predicate green; review round
# 5, correctness-1, regression-1 and extra6-1: the first three constructs above, each planted on the corrupt road, bumped two second
# keys with every clause green, so the clauses stopped being the premise's pin). Two of the second keys,
# corrupt and unreadable_journal, are hand-off keys that are NOT call keys, so a bump of either beside a goal_io loads bump with no
# call through the door balanced the shared
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
# CASE_KM: names a CASE may replace after setUp for its own world, saved with the rest and restored by the cleanup, which then
# checks every other global of both modules against setUp's first snapshot (_restore); setUp leaves them real (the agreement
# check there). The two writers are the wedge-gate sweep case's: their real bodies load
# through the writer door at their write moments by design (the reference's jobs block names them among the store's other
# readers), so the census has nothing to say about them.
CASE_KM = ("_session_working", "_mark_nudge_failed", "_file_wake_answer")
# CASE_JD: the judge names a CASE may replace after setUp for its own world, saved with the rest and restored by the cleanup, as
# CASE_KM's are; setUp leaves them real, so its agreement check is unchanged. _freeze_store is the door witness's seam for the dup and
# refuse roads (TheDoorBumpsAtMostOneSecondKeyPerCall): a wrapper over the real function that calls through, so its real body runs on
# every fill and is covered by execution, not by the census.
CASE_JD = ("_freeze_store",)
# TICK_REBOUND_KM / TICK_REBOUND_JD: a kernel or judge global the tick itself rebinds (a `global` statement run by the pass), which
# _restore's check against setUp's first snapshot would name at every harness case's cleanup: name -> the reason the rebinding is
# the tick's and not a case's leak. Empty: over the whole module on 3.12 and 3.14t no harness case ends with a global of either
# module rebound outside the saved lists (the kernel's _PREV_ALIVE, which the tick rebinds, is in REPLACED_KM and goes back with
# them). A row here must name a global the snapshot holds (a row for a name that is gone reds as stale); whether the tick still
# rebinds it is not checked, so a row that outlives its rebinding is unseen here.
TICK_REBOUND_KM = {}
TICK_REBOUND_JD = {}
# _INTERPRETER_GLOBALS: the names the interpreter itself writes into a module's globals, which are no case's rebinding and which
# _restore's check sets aside. One today: `__warningregistry__`, which the warnings module creates in the globals of the frame a
# warning is attributed to the first time one is raised from that module's code (warnings.warn's globals.setdefault, before the
# filters decide what becomes of the warning; the C path does the same), so the first warning of a process raised from the kernel
# inside a harness case would otherwise be named a leak at that case's cleanup, deleted there, and named again at the next
# (review round 7, a records pass re-taking the first paragraph's bypass plants at the round's head: the plant that opens the store
# file in the kernel's pass loop left its handle to the collector, whose unclosed-file warning carries the kernel's frame, and five
# harness cases red at their cleanup naming this name and no stub). A bound, not a derivation: which names the interpreter writes
# is the interpreter's, stated here and set aside by name.
_INTERPRETER_GLOBALS = frozenset({"__warningregistry__"})
REPLACED_KM = ("_alive_sessions", "_wait_for_graph", "_session_flag", "_compacting_now", "_api_error",
               "_interrupt_suppresses_nudge", "_backend_rewind_pending", "_last_state",
               "_session_awaiting", "_turn_romp_injected", "_closer_settled", "_revivers_pending",
               "_pending_ops", "_log_nudge_event", "_push_all", "_mark_views_dirty", "_path_of",
               "_debt_backstop_tick", "_PREV_ALIVE")
# REPLACED_DATA: the names of REPLACED_KM whose object is data, not a callable, which the replaced-helpers census skips (a source census
# has nothing to read on a dict or a set). setUp derives the same tuple from the kernel objects it found and holds it equal to this
# one both ways, so a callable put here, or a data name left off, reds every harness case at setUp naming both tuples (review round 7,
# the seventh-axis verifier: the tuple was pinned by the census's count alone, and with the count edited a callable put here had its
# real body skipped unseen).
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
# none of them and is refused before any of them answers (held by execution over every census entry point of this module, the
# roster _CENSUSES, in TheWalkersRefuseAStrangerByExecution: a stranger planted in a real tree at every node position of the
# grammar the running interpreter defines, each alone, and each entry point refuses each naming it).
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
    it met. The class is matched by identity against the ast module's own, so a stranger of a known name is refused too. The
    refusal comes when the walk yields the node, so a census that reads a child off the parent the walk yielded, before the child's
    own turn, meets a stranger there unrefused and fails some other way (the finder's from-import branch read every name's `.name`
    at the ImportFrom and raised AttributeError on a stranger among the names until the round-6 fixes; it reads alias nodes alone
    now, and the witness files any such read as an exception that is not the refusal). Derives: nothing of its own; the class set it
    refuses against, _AST_KNOWN, is the table's classes by identity, and the interpreter check
    (TheGrammarIsTheOneTheWalkersClassify.test_the_interpreter_defines_no_node_class_outside_the_table) reads every node class of the
    running interpreter from vars(ast) and pins the three tables against it both ways: no class outside them, the concrete classes
    present exactly the table's at or below the version, _AST_KNOWN that set by identity, every concrete class a leaf but for the
    compatibility classes and derived from a sum type or from AST, every sum type at or below its version defined with subclasses
    and one above it absent. Bounds: the tables themselves, _AST_CONCRETE with its version gates, _AST_ABSTRACT and _AST_COMPAT, and
    the split between them, a policy the version demand asks for (a new class must red by name rather than be absorbed, so the table
    is kept by hand and pinned by execution on each interpreter, never computed from it); a compatibility name the interpreter lacks
    is no red, since that set shrinks by version."""
    for node in ast.walk(tree):
        if type(node) not in _AST_KNOWN:
            raise AssertionError("a node of class %s, which the census walkers of this module do not classify (not in _AST_CONCRETE, "
                                 "or not the ast module's own class of that name): a reader that cannot classify a node must fail "
                                 "naming it rather than scan less and report a site absent; list the class in _AST_CONCRETE with the "
                                 "version that adds it and say in the table's comment how each walker reads it" % type(node).__name__)
        yield node


# The ast module's four traversal names the early-warning finder (_traversal_references) keys on, spelled plainly and tied to the
# interpreter by the walker case's derivation check (every name is an attribute of the ast module). Until the round-5 fixes they were
# assembled from string halves so this module's text spelled none, and the case's samples were built from the same constants, so a
# misassembled name matched its own sample and the case stayed green (review round 5, extra5-3: a fixture sharing a source with the
# thing it tests is not a fixture). The finder reads a string constant only as getattr's second argument, so a plain spelling here
# or in a sample is no reference. Every reference to one of these names in the three forms the finder reads must sit inside _walk
# (TheGrammarIsTheOneTheWalkersClassify); the finder is silent on a walk under an unlisted name, and the walk contract itself is
# carried by execution (TheWalkersRefuseAStrangerByExecution).
_TRAVERSAL = ("walk", "iter_child_nodes", "NodeVisitor", "NodeTransformer")
# _FINDER_FORMS: the forms _traversal_references reads, a roster like _TRAVERSAL (which forms the finder reads is a policy, not a
# population the module can compute). The finder case derives the forms the finder reports from the finder's own source and the
# forms the samples cover from the rows, and holds each equal to this roster both ways (review round 7, the seventh-axis verifier: the
# forms were pinned one way, so the getattr rows removed left the finder's getattr branch pinned by nothing; the round's close: the
# source derivation held against the samples alone agreed with them when the branch and the rows were removed together, so this
# roster is the copy that names the loss). A form removed from the finder, the samples and this roster at once is unseen, as a name
# removed from _TRAVERSAL with its samples is.
_FINDER_FORMS = ("attribute", "from-import", "getattr")
# Every reference to a traversal name outside _walk, keyed (enclosing def, name) with the reason it walks nothing around _walk. The
# pin asserts each row is used (a stale row reds) and that nothing else refers to one; a new legitimate reference gets a row here.
_WALK_EXEMPT = {
    ("_loader_births", "iter_child_nodes"):
        "lists a node's direct children to build the parent map and traverses nothing: every child is yielded by _walk on the next "
        "level, where it is classified or refused",
    ("_census_floor", "iter_child_nodes"):
        "lists a node's direct children to build the parent map and traverses nothing: every child is yielded by _walk on the next "
        "level, where it is classified or refused",
    ("TheGrammarIsTheOneTheWalkersClassify.test_a_walker_refuses_a_node_it_does_not_classify_by_name", "walk"):
        "the control the refusal case compares _walk against, over a tree of grammar nodes only",
}


def _traversal_references(tree):
    """Every reference in `tree` to one of the ast module's traversal names (_TRAVERSAL), as sorted (line, name, form, spelling,
    owner) tuples, in three forms (_FINDER_FORMS) keyed on the NAME and never on the road to the module: `attribute`, an Attribute named like one on
    any base at all (`ast.walk`; `_a.walk` after `import ast as _a`; `importlib.import_module("ast").walk`, `__import__("ast").walk`,
    `sys.modules["ast"].walk`; `_m.walk` after `_m = ast`; a NodeVisitor or NodeTransformer base is spelled this way too), the base
    spelled by ast.unparse for the message; `from-import`, keyed on the imported name alone whatever module the road names (`from
    ast import walk`, with or without `as`; `from myast import walk` after `sys.modules["myast"] = ast`; `from pkg.ast import walk`;
    `from . import walk`), and a star import from any module, a reference to every name reported as `*`, the road spelled from the
    node's level and module for the message (review round 5, tests-4: the branch tested n.module == "ast" while this docstring said
    every form keys on the name and never on the road, and a from-import through a sys.modules alias of the module passed); the
    names are read off the ImportFrom when the walk yields it, so the read is kept to alias nodes and a stranger among the names is
    left to the walk, which refuses it at its own turn (review round 6, lens one: the position witness planted a stranger at
    ImportFrom.names and this read raised AttributeError on it before the refusal, the one position of the grammar where the
    refusal did not come first; the witness files such a raise as an exception that is not the refusal); the
    name-keying's false positive, the price of keying on the closed set, is that `from os import walk` and any star import are
    references too, bought off by a _WALK_EXEMPT row if this module ever needs one (clean today: the module from-imports load_source
    and Path only); and `getattr`, a getattr on any first argument whose second argument holds the name in
    a string constant anywhere under it, read through _walk over that argument the way the birth pin reads a constant, so a
    no-placeholder f-string (`getattr(ast, f"walk")`, a JoinedStr holding the Constant) is a reference beside the plain string
    (review round 5, extra5-1: the form tested the argument itself as a Constant, the sibling of the defect round 4 ruled on the
    birth pin one function away), the call spelled by ast.unparse for the message. The
    first cut keyed the attribute and getattr forms on the names the ast module was imported under, an open set of roads to the
    module, and a verifier of the round-4 fixes walked a tree through each of the four roads above with the pin green (the list
    shape the round's ruling names, one more time); the four names are the closed set, so the forms key on them alone, which is
    clean today: the module spells a traversal attribute at four sites, each inside _walk or exempt. `owner` is the enclosing
    top-level def, `Class.method` for a method, `Class` for a class body, `<module>` otherwise, found by walking each module-body
    def's subtree (through _walk, as every reader here walks). Keyed on four names, the finder is wrong in both directions: an
    innocent use of a listed name needs a _WALK_EXEMPT row (the parent maps in _loader_births and _census_floor list a walked node's
    children and traverse nothing), and a walk under an unlisted name is not seen. Outside these forms: a traversal name read from the module's
    namespace by string (`vars(ast)[...]`, `ast.__dict__[...]`, `operator.attrgetter(...)`) or assembled at run time, a getattr
    reached under another name (`_g = getattr` then `_g(ast, "walk")`, `builtins.getattr(ast, "walk")`: the form keys on the callee
    being the bare Name getattr, and a verifier of the round-5 fixes planted the rebound name as a real walk with the case green),
    the limits the walker case holds on their side with samples, and any traversal under an unlisted name, a recursion over ast.iter_fields,
    node._fields or ast.dump, a whole walk this finder never sees (review round 5, correctness-2, tests-1, extra5-2 and regression-2:
    the ruling stops the name list at four, so the finder refuses the forms it names and is silent on the rest, an early warning;
    the contract, a stranger node refused and never passed over, is carried by execution in TheWalkersRefuseAStrangerByExecution
    over every roster census entry point of this module). The interpreter check beside the walker case scans vars(ast) for every node
    class and reds by name on a new one with no walker involved, so the version demand does not rest on this finder. Derives: every
    reference to a name of _TRAVERSAL in the three forms over the tree handed, each with its line, form, spelling and owner. Bounds:
    the four names (the ruling's stop) and the three forms; and the owner label, which reads two container shapes, a module-body def
    and a class with its direct methods, and labels a deeper reference by the module-body def, the class or the direct method that
    holds it, a label for the message and the exemption key and not a population. The roster's membership and the exemption rows
    are pinned by the finder case, not here."""
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
        if isinstance(n, ast.Attribute) and n.attr in _TRAVERSAL:
            out.append((n.lineno, n.attr, "attribute", ast.unparse(n), owner))
        elif isinstance(n, ast.ImportFrom):
            road = "." * n.level + (n.module or "")      # the message's spelling only: the branch keys on the imported name
            for a in n.names:                             # read off the parent the walk yielded: a name that is not an alias node is
                if isinstance(a, ast.alias) and (a.name in _TRAVERSAL or a.name == "*"):   # left to the walk, which refuses it at its turn
                    out.append((n.lineno, a.name, "from-import", "from %s import %s%s" % (road, a.name, " as " + a.asname if a.asname else ""), owner))
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "getattr" and len(n.args) >= 2:
            hit = [sub.value for sub in _walk(n.args[1]) if isinstance(sub, ast.Constant) and sub.value in _TRAVERSAL]
            if hit:
                out.append((n.lineno, hit[0], "getattr", ast.unparse(n), owner))
    return sorted(out)


def _pass_through_lines(fn, callee):
    """(lines, calls): the line numbers, in `fn`'s file, of its calls to `callee`, and how many such calls there are. The calls
    are the boundary wrapper's hand-off of the read (`loader(fsid)` in _or_fault, `_or_fault(...)` in the two outer wrappers),
    read from the source by the AST so a docstring or a comment naming the callee is not one. The lines are absolute (inspect
    gives the source with its first line's number) and are what _caller steps over at; the count is the guard's (review round
    2, extra5-2: two hand-off calls written on one line are one line and were passed by a guard whose message said one call).
    Derives: the lines and the count from the AST of `fn`'s source. Bounds: the one form read, a Call whose callee is the bare Name
    `callee`; a hand-off spelled otherwise (through __call__, a partial, a local alias) is no call here and setUp's guard reds on it,
    each form held on its side by the hand-off enumeration (_HANDOFF_FORMS)."""
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
    of these lookups, a dict read (`.get`, `.pop`, `.setdefault`, `.__getitem__`) or a subscript key, both clauses reading a
    constant's text with an ASCII bytes literal decoded, surrounding whitespace stripped and str.lower applied (another codec, a strip
    of other characters and another case fold are not undone); a name completed at run time from constants that spell no door whole
    and either carry the name in one piece to none of those receivers (`"load_" + "goals_shared"`, `"load_%s_shared" % "goals"`, a
    needle-keeping concatenation handed to an unlisted callable, a reversed literal) or reach one in a text the three transforms do
    not restore (a utf-16 bytes literal at getattr) is spelled as a door in
    no constant it reads and is outside every static pin in this module (a verifier of the consolidation pass planted the two
    subscript forms and the dict read as a real load in a replaced helper and the module stayed green, the round-4 refuters planted
    six doors on no list the same way, and a verifier of the round-4 fixes a bytes literal decoded, a padded constant stripped and a
    cased one lowered; _LIMITS names the two classes, string and assembled, and the enumeration runs the pin over each form of both
    and expects a birth from the first class and none from the second). A name bound OUTSIDE obj's source is no site in
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
    the JoinedStr's FormattedValue and its Call on every interpreter, and reads the f-string's literal text on none. Derives: the
    sites from the AST of `obj`'s source as inspect gives it. Bounds: the three node kinds read, Name, Attribute and alias, and the
    substring rule over the needle, so a loader in any other node or in a string is no site, each form held on the side it falls by
    the loader enumeration (_LOADER_FORMS) and, for the string and assembled classes, by the kernel-wide pin's verdict over the form's
    file; and the object handed, the wrapper behind a decorator without functools.wraps, which the identity check of the
    replaced-helpers census and the walk census holds first."""
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
    enumerated in TheCensusOverEveryForm (the consolidation pass). Derives: the bump lines from the AST of `obj`'s source. Bounds:
    the one spelling read, an augmented Add on a constant "loads" subscript of the Name _NUDGE_WALK_STATS, so every other spelling
    is no bump and the walk census reds on it, conservatively, each form held on its side by the bump enumeration (_BUMP_FORMS)."""
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
# six on no list), never need listing; _DYNAMIC_LOOKUPS and _DICT_READS stay for the constant that merely CONTAINS the name. Both
# clauses read a constant's text through _door_text, which undoes three run-time transforms of a name and no others: an ASCII bytes
# literal decoded (bytes in another codec are not undone), surrounding whitespace stripped (a strip of other characters is not),
# str.lower (casefold or any other fold is not).
_DOOR_SPELLINGS = ("load_goals", "load_goals_or_fault", "load_goals_shared", "load_goals_shared_or_fault")


def _door_text(node):
    """The text of a str or bytes Constant as both clauses of _loader_births read it, None for any other node: an ASCII bytes
    literal decoded (a door's name is ASCII, so `b"load_goals_shared".decode()` restores it at run time; the read here decodes as
    ASCII with replacement, so a bytes literal in another codec, utf-16 say, reads as no door and is not undone), surrounding
    whitespace stripped (`.strip()` with no argument; a strip of other characters, `.strip("x")` around a padded name, is not undone)
    and str.lower (`.lower()`; casefold or any other case fold is not undone: a constant str.lower leaves as it is and casefold folds
    to the name, the long s say, reads as no door). These three are the transforms the pin undoes, one member of each family and not
    the family, each undone at run time by one method call on the constant itself; every other completion of a name at run time (a
    split across constants, a reversal, a needle-keeping concatenation at an unlisted receiver, a decode in another codec, a strip of
    other characters, another case fold) is the assembled class of _LIMITS, stated there by this boundary (a verifier of the round-4
    fixes planted the bytes, the padded and the cased forms as real loads and the module stayed green while its prose named the
    split alone as the residue; review round 5, tests-3, regression-3 and extra4-1: the recaps then named the families, a decode, a
    strip, a lower, where this function undoes one member of each, and a utf-16 bytes door at getattr and a chars-strip at a partial
    of getattr each reach a real load with the module green, the limit held on its side by three enumeration rows since the round-5
    consolidation, F75 to F77, and recorded in the round-5 paragraph)."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bytes):
            return node.value.decode("ascii", "replace").strip().lower()
        if isinstance(node.value, str):
            return node.value.strip().lower()
    return None


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
    loader-naming string CONSTANT, under two clauses, both reading a constant's text through _door_text (an ASCII bytes literal
    decoded, surrounding whitespace stripped, str.lower applied: the three transforms of a name the pin undoes, one member of each
    family and not the family). The value rule: a constant whose whole
    text so read is one of the four door spellings (_DOOR_SPELLINGS) is a birth wherever it appears and whatever receives it, the receiver named from the constant's
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
    the module green. The limit that remains is what the two clauses' boundary leaves out, stated by that boundary and not by a
    list of examples: a constant that spells no door whole after the three transforms _door_text undoes, and either carries the
    name in one piece to no listed lookup, dict read or subscript key, or reaches one in a text those three transforms do not
    restore, however the name is completed at run time. A concatenation, a format or an f-string that splits the needle (`"load_"
    + "goals_shared"`, `"load_%s_shared" % "goals"`, `f"load_{'goals'}_shared"`), a needle-keeping concatenation handed to an
    unlisted callable (`functools.partial(getattr, jd)("load_goals_" + "shared")`), a reversed literal, a bytes literal in a codec
    other than ASCII (the name encoded as utf-16 and decoded at getattr: it reaches the listed lookup, in bytes the ASCII read does
    not restore), a strip of characters other than whitespace (`"xxload_goals_sharedxx".strip("x")` at an unlisted receiver; at a
    listed one the constant contains the name and the consumer clause reads it), a case change other than str.lower (a constant
    str.lower leaves as it is and casefold folds to the name) and any transform other than the three _door_text undoes are of that
    class; each spells the door in no constant this pin reads as the door and is outside every static pin in this module (_LIMITS
    names the class `assembled`, and the enumeration holds each form of the string and assembled classes on the side it falls; a
    verifier of the round-4 fixes: the residue was stated here as the split alone while a bytes literal decoded, a padded constant
    stripped and a cased one lowered each reached a real load with the module green, so the pin undoes those three and the sentence
    names the boundary; review round 5, tests-3, regression-3 and extra4-1: the sentence then named the complement as any transform
    other than a decode, a strip or a lower, families where the pin undoes one member of each, and a utf-16 bytes door at getattr
    and a chars-strip at a partial of getattr each reached a real load with the module green). The name
    bound to a variable before the lookup (`n = "load_goals_shared"; getattr(jd, n)`)
    was that class's until the round-4 fixes and is the string class's now: the constant spells the door whole where it is bound,
    and the rule reads it there. `called` counts each spelling called and `defs` each def named like a loader, so a caller can
    check the population it read is the doors' and not empty. Derives: every birth, every called spelling, every loader def and
    every hand-off from the whole AST of the file at `path`, with one parent map over the walk. Bounds: _DOOR_SPELLINGS, the four
    doors' names, the closed set the value rule keys on, spelled by hand once (the birth pin holds that copy against the judge's defs
    and the kernel's called spellings both ways, so the set is a policy here and a derived check there); _DYNAMIC_LOOKUPS and _DICT_READS, the receivers the
    consumer clause reads, an open set kept only for a constant that merely contains the name (a whole spelling is refused whatever
    receives it); the three transforms _door_text undoes, a policy boundary, so the assembled class is outside by it; and the
    needle, "load_goals" by substring."""
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
        """Every str or bytes Constant under `node`, walked as _walk walks (so a constant inside an f-string, a conditional, a walrus
        or a concatenation is reached), whose text as _door_text reads it contains the needle: a birth described by `what`, each
        constant reported once."""
        for sub in _walk(node):
            text = _door_text(sub)
            if text is not None and "load_goals" in text and id(sub) not in reported:
                reported.add(id(sub))
                born.append((sub.lineno, "a loader-naming string %s in %s: %r" % (what, enclosing(sub), sub.value[:48])))

    def receiver(n, p):
        """What received a whole-spelling constant, for the message: handed to a call's callee when its parent is a Call it is an
        argument of (methodcaller, itemgetter, getattr_static or any dispatcher, named without being listed), through a keyword
        when its parent is one, the object of a method when its parent is an Attribute on it (`" load_goals_shared ".strip()`), else
        under the parent's class (Assign, Dict, MatchMapping, Compare, a docstring's Expr)."""
        if isinstance(p, ast.Call) and p.func is not n:
            return "handed to %s" % _callee_name(p.func)
        if isinstance(p, ast.Attribute) and p.value is n:
            return "as the object of .%s" % p.attr
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
        # the value rule: a constant spelling a door WHOLE, its text read through _door_text (an ASCII bytes literal decoded, surrounding
        # whitespace stripped, str.lower), is a birth wherever it appears and whatever receives it (the receiver is named from the
        # parent, never matched against a list); one the consumer clause reached first is not reported twice
        if _door_text(n) in _DOOR_SPELLINGS and id(n) not in reported:
            born.append((n.lineno, "a loader-naming string constant %r %s in %s" % (n.value, receiver(n, p), enclosing(n))))
    return sorted(born), called, defs, sorted(handoffs)


def _door_bump_key(n):
    """The key a bump node of the door moves, `_shared_bump("<key>")` or `_SHARED_STATS["<key>"] += ...`; None for any other
    node. The roster pin's reader (TheCountersOneSite), a module-level def since the round-5 fixes so that the pin's reading of
    the door's tree, _door_regions, is a census entry point the witness by execution can drive (TheWalkersRefuseAStrangerByExecution)."""
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "_shared_bump" and n.args and isinstance(n.args[0], ast.Constant):
        return n.args[0].value
    if (isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Subscript) and isinstance(n.target.value, ast.Name)
            and n.target.value.id == "_SHARED_STATS" and isinstance(n.target.slice, ast.Constant)):
        return n.target.slice.value
    return None


def _door_stmt_key(s):
    """The key a bump STATEMENT of the door moves: an Expr whose value is the _shared_bump call, or the AugAssign itself."""
    return _door_bump_key(s.value if isinstance(s, ast.Expr) else s)


def _door_hands_off(blk):
    """Whether a statement list of the door hands its read to load_goals: its last statement is a Return whose value is a Call of
    the Name load_goals. One predicate for two readers: the roster pin derives SHARED_HANDOFF_KEYS as the direct bump keys of the
    lists this answers True for, and the door witness's _sites reads it per bump site, so each road's hand-off column is tied to the
    lists holding its sites (review round 7: the tuple was the one roster pinned by nothing). Reads one form; a hand-off written
    through a temporary or an alias of the loader answers False here, and both readers red on it (the roster pin naming the key, the
    witness's hand-off column by the writer door's counter)."""
    last = blk[-1]
    return (isinstance(last, ast.Return) and isinstance(last.value, ast.Call) and isinstance(last.value.func, ast.Name)
            and last.value.func.id == "load_goals")


def _door_regions(tree):
    """The roster pin's three reads of the door's tree, (bumps, blocks, tries): every bump as (line, key); every statement list
    of the door, each list-valued field of a walked node whose members are all statements (a body, an orelse, a finalbody, a
    handler's body; Try.handlers holds ExceptHandler nodes, so no try region is collected twice; ast.iter_fields here lists the
    fields of a node _walk yielded and traverses nothing, the traversal is _walk); and every try statement, the one node class
    with a finalbody field. The first read walks the whole tree, so a node the grammar table does not classify anywhere in
    `tree` is refused here, before the pin's own reads over the subtrees these hold (the deep count per list, the bumps under
    each finalbody, the try subtrees) run."""
    bumps = [(n.lineno, _door_bump_key(n)) for n in _walk(tree) if _door_bump_key(n) is not None]
    blocks = [val for node in _walk(tree) for _field, val in ast.iter_fields(node)
              if isinstance(val, list) and val and all(isinstance(s, ast.stmt) for s in val)]
    tries = [node for node in _walk(tree) if hasattr(node, "finalbody")]
    return bumps, blocks, tries


_TREE_READERS = ("ast.parse", "inspect.getsource", "inspect.getsourcelines")   # the calls by attribute that make their container a reader of a tree it parses


def _census_floor(tree):
    """The mechanical floor under the roster of census entry points (_CENSUSES), read from this module's own AST: (defs, classes,
    module). Every reader reference in the tree, _walk by that Name or one of _TREE_READERS by attribute (ast.parse,
    inspect.getsource, inspect.getsourcelines: the calls that make their container a reader of a tree it parses), as a callee or
    as a value (a container that hands _walk or ast.parse to another callable, `map(_walk, trees)`, `real = ast.parse`, reads a
    tree as surely as one that calls it, and a predicate over calls alone attributed it to nothing), is attributed to its nearest
    enclosing def or class chain, whatever the container. `defs` maps a module-level def to the sorted spellings it
    references (its nested defs and lambdas fold into it), so every such def must be a row of the roster. `classes` maps a chain that
    starts at a class, the enclosing classes named from the top and the first def below them: a method ("C.m"), a nested class's
    method ("C.Inner.m"), a class-body statement ("C"), a method's inner defs folded into the method; these are the inline readers
    the roster case pins with the reason each is outside the roster. `module` maps a reader reference under no def and no class (a lambda
    or a comprehension in a module-body statement) to its spellings, keyed by the statement's assignment target, or "<Expr>" and the
    like for a statement that assigns nothing. Derives: the owner chain of every reader reference over the whole tree, from one parent
    map built as _loader_births builds its own (ast.iter_child_nodes lists a walked node's children and traverses nothing, the
    _WALK_EXEMPT row), so no container shape is outside the floor. Until the round-7 fixes the floor read two shapes, a module-level
    def and a direct method of a module-level class, and every other container was attributed to nothing: a method spelling ast.parse
    and inspect.getsource and walking node._fields by hand, a nested class's method and a class-body statement reading through
    _walk, and a module-level statement outside _CENSUSES reading through _walk each left the module green at the head the round-7
    plan read, and each reds the roster case naming its chain since. Bounds: the spelling of the reader alone. A reference is in the
    floor only when it names _walk or spells one of _TREE_READERS exactly, the base Name and the attribute (`ast.parse`, not `_a.parse`
    after `import ast as _a`, not `compile(source, ..., ast.PyCF_ONLY_AST)`, not an importlib road), so a census that parses under
    any other road, or is handed a pre-parsed tree under any parameter name, and walks by hand calls none of these and is outside
    this floor in every container (a verifier of the round-5 fixes planted the compile road and the alias road unregistered with the
    module green, and the same def through ast.parse red this floor naming it); it joins the roster by the rule in the roster's
    comment, and the roster's count pin is what notices the edit. Itself a census over a tree (a reader that passed over a node it
    does not classify would report a container absent), so it is a row of the roster and drives like the rest: the references are
    collected during the one walk and attributed after it, so every node of the tree has been yielded, and a stranger refused,
    before a statement's target is spelled for a key. _walk calls ast.walk and spells none of these, so it is in no map; were it
    ever to, the roster case would name it as a def outside the roster."""
    parents, found = {}, []
    for node in _walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
        if isinstance(node, ast.Name) and node.id == "_walk":
            found.append((node, "_walk"))
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id + "." + node.attr in _TREE_READERS:
            found.append((node, node.value.id + "." + node.attr))
    defs, classes, module = {}, {}, {}
    for ref, spelled in found:                        # after the walk: every node has been yielded and refused before a key is spelled
        chain, node, stmt = [], ref, ref
        while node is not None:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                chain.append(node)
            if parents.get(node) is tree:
                stmt = node                           # the module-body statement the reference sits in
            node = parents.get(node)
        chain.reverse()                               # from the top: the enclosing classes, then the first def below them
        names = []
        for owner in chain:
            names.append(owner.name)
            if isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef)):
                break
        if not names:
            targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target] if isinstance(stmt, (ast.AnnAssign, ast.AugAssign)) else []
            key = ", ".join(ast.unparse(t) for t in targets) or "<%s>" % type(stmt).__name__
            module.setdefault(key, set()).add(spelled)
        elif len(names) == 1 and isinstance(chain[0], (ast.FunctionDef, ast.AsyncFunctionDef)):
            defs.setdefault(names[0], set()).add(spelled)
        else:
            classes.setdefault(".".join(names), set()).add(spelled)
    return ({k: sorted(v) for k, v in defs.items()}, {k: sorted(v) for k, v in classes.items()}, {k: sorted(v) for k, v in module.items()})


# The node positions of the grammar, derived from the running interpreter by execution and never listed: the witness by execution
# (TheWalkersRefuseAStrangerByExecution) plants a stranger at every one of them, each alone, in place of three hand sites (review
# round 6, lens one: the module body's end, the first def's body and the first class's body were three of the 147 node positions an
# exec-mode Module offers on 3.12, all statement lists, so a census that read any other position by hand, a decorator list, a call's
# arguments, a comprehension's generators, an f-string's values, a match statement's cases, an annotation, a type-parameter list, was
# green under the witness; three sites are a list, and the ruling on approach is that lists do not converge). A position is a
# (class, field) pair, a concrete node class and a field of it that holds a node or a list of nodes. The population is read off the
# instances a synthetic corpus produces (_GRAMMAR_CORPUS, parsed in every mode), every field of every concrete class the interpreter
# defines observed non-empty at least once, so a field the corpus leaves unobserved reds naming it rather than going unplanted, and a
# class or field a new interpreter adds joins the population with no edit here once the corpus exercises it (the interpreter check
# beside the table reds first on a class the table does not list; the unobserved check reds on a field the corpus does not reach).
# The version-gated sources are strings, so a source in a syntax the interpreter lacks is never parsed there.
_GRAMMAR_CORPUS = [
    ("""
import a as b, c
from ..d import e as f, g
from h import *
@deco1
@deco2(1)
def fn(p1, /, p2: int = 1, *args: str, k: int = 2, **kw) -> int:
    global gx
    nonlocal nx
    return p1
@adeco
async def afn() -> int:
    await x
    async for i in y:
        pass
    else:
        pass
    async with a as b, c:
        pass
    [i async for i in y]
@deco
class K(Base, metaclass=M):
    x: int = 1
    y: int
del a, b
a = b = 1
a += 1
for i in it:
    pass
else:
    pass
while cond:
    break
else:
    continue
if t:
    pass
elif u:
    pass
else:
    pass
with a as b, c:
    pass
match subj:
    case 1 | 2:
        pass
    case [1, *rest]:
        pass
    case {"k": v, **others}:
        pass
    case Point(0, x=0, y=1) if guard:
        pass
    case True:
        pass
    case str() as s:
        pass
    case _:
        pass
raise E from cause
try:
    pass
except E as e:
    pass
except:
    pass
else:
    pass
finally:
    pass
assert t, "msg"
lambda q, /, r=1, *s, t=2, **u: q
(a and b) or c
(w := 1)
a + b
-a
not a
a if b else c
{1: 2, **d}
{1, 2}
[i for i in it if cond if cond2]
{i for i in it}
{i: j for i, j in it}
(i for i in it)
def g():
    yield
    yield 1
    yield from x
a < b <= c
f(a, *b, k=1, **kw)
f"{a!r:>{w}} text {b}"
u"kind"
a.b
a[1:2:3, 4]
[*a, b]
(a, b) = c
x[...]
""", "exec", False),
    # the type-comment fields and the type ignores are filled only under type_comments=True
    ("""
def tc(a,  # type: int
       b,  # type: str
       ):
    # type: (...) -> None
    pass
async def atc():
    # type: () -> None
    pass
x = 1  # type: int
for i in it:  # type: int
    pass
async def z():
    async for i in it:  # type: int
        pass
    async with a as b:  # type: int
        pass
with a as b:  # type: int
    pass
y = 2  # type: ignore
""", "exec", True),
    # the roots of the other parse modes
    ("x = 1\n", "single", False),
    ("a + 1", "eval", False),
    ("(int, str) -> bool", "func_type", False),
]
if sys.version_info >= (3, 11):
    _GRAMMAR_CORPUS.append(("try:\n    pass\nexcept* E:\n    pass\nelse:\n    pass\nfinally:\n    pass\n", "exec", False))
if sys.version_info >= (3, 12):
    _GRAMMAR_CORPUS.append(("def fn2[T: int, *Ts, **P](a):\n    pass\nasync def afn2[U](a):\n    pass\nclass K2[V]:\n    pass\n"
                            "type Alias[W] = list[W]\n", "exec", False))
if sys.version_info >= (3, 13):
    _GRAMMAR_CORPUS.append(("def fn3[T: int = int, *Ts = *tuple[int], **P = [int]](a):\n    pass\n", "exec", False))
if sys.version_info >= (3, 14):
    _GRAMMAR_CORPUS.append(("t'{a!r:>{w}} text {b}'\n", "exec", False))
_GRAMMAR_CORPUS = tuple(_GRAMMAR_CORPUS)


def _grammar_positions(corpus=_GRAMMAR_CORPUS):
    """Every field of every concrete node class the running interpreter defines (the classes of _AST_CONCRETE present at this
    version, by identity), as {(class, field): {kind, list, base, prims}}, derived by execution: `corpus` parsed in its modes, every
    node each parse produces read through _walk, and the fields of each yielded node listed with ast.iter_fields (a listing of that
    node's fields, traversing nothing). kind is "node" when a node, or a list holding one, was observed in the field and "prim" when
    only primitives were; list says a list was observed; base is, for a node field, the sum type every observed child derives from,
    or the child's own class when it is a product type (comprehension, arguments, arg, keyword, alias, withitem, match_case), so a
    stranger for the position can derive from it; prims lists the python types observed. Reds naming every field the corpus left
    unobserved (None or [] on every instance), so the population is complete for this interpreter by execution and a field a new
    interpreter adds is exercised by the corpus or named here, and reds on a field whose children derive from two sum types, which
    no grammar version has. A roster row (_CENSUSES): it parses by attribute and walks through _walk, so the witness drives it over
    its own corpus with a stranger planted, and _walk refuses the stranger before the derivation reads a field off it."""
    classes = {c.__name__: c for c in _AST_KNOWN}
    seen = {(name, field): {"nodes": set(), "prims": set(), "list": False} for name, c in classes.items() for field in c._fields}
    for source, mode, type_comments in corpus:
        for node in _walk(ast.parse(source, mode=mode, type_comments=type_comments)):
            for field, value in ast.iter_fields(node):
                rec = seen[(type(node).__name__, field)]
                if isinstance(value, list):
                    rec["list"] = True
                for item in (value if isinstance(value, list) else (value,)):
                    if isinstance(item, ast.AST):
                        rec["nodes"].add(type(item).__name__)
                    elif item is not None:
                        rec["prims"].add(type(item).__name__)
    positions, unobserved, mixed = {}, [], []
    for key, rec in sorted(seen.items()):
        bases = {classes[n].__bases__[0].__name__ if classes[n].__bases__[0].__name__ in _AST_ABSTRACT else n for n in rec["nodes"]}
        if len(bases) > 1:
            mixed.append((key, sorted(bases)))
        if not rec["nodes"] and not rec["prims"]:
            unobserved.append(key)
        positions[key] = {"kind": "node" if rec["nodes"] else "prim", "list": rec["list"],
                          "base": min(bases) if bases else None, "prims": sorted(rec["prims"])}
    if unobserved or mixed:
        raise AssertionError("the grammar corpus left these fields unobserved (None or [] on every instance the corpus produced), so "
                             "the position population is not complete for Python %s and the witness would plant nothing there: %r; "
                             "fields whose children derive from more than one sum type: %r. Add a source that fills each to "
                             "_GRAMMAR_CORPUS" % (sys.version.split()[0], unobserved, mixed))
    return positions


_STRANGERS = {}


def _stranger(base):
    """The class named Frobnicate for `base`, which the ast module does not define: it derives from the sum type of that name (stmt,
    expr, pattern, ...) or from AST itself when `base` is a product class (alias, keyword, ...), as the products do, so an instance
    sits in a position of that base as a new grammar form would; _walk refuses it by identity whatever it derives from."""
    if base not in _STRANGERS:
        _STRANGERS[base] = type("Frobnicate", (getattr(ast, base) if base in _AST_ABSTRACT else ast.AST,), {"_fields": ()})
    return _STRANGERS[base]


def _leaf(base, positions):
    """A minimal grammar node for a single field of type `base`: for a sum type, its concrete class with the fewest node fields
    (a Constant for an expr, a MatchSingleton for a pattern, an Add for an operator), built by _minimal; for a product class, that
    class itself."""
    if base in _AST_ABSTRACT:
        sum_type = getattr(ast, base)
        base = min((c.__name__ for c in _AST_KNOWN if c.__bases__[0] is sum_type),
                   key=lambda n: (sum(1 for (cn, _f), p in positions.items() if cn == n and p["kind"] == "node"), n))
    return _minimal(base, positions)


def _minimal(cls_name, positions):
    """A minimal instance of the concrete class `cls_name`, every field set from the derived positions: a leaf node for a single node
    field, [] for a list field, a primitive of an observed type for a primitive field (a str, an int, a bool, else None). Nothing
    here is compiled or unparsed, so the values need only be of the field's type."""
    kw = {}
    for field in getattr(ast, cls_name)._fields:
        p = positions[(cls_name, field)]
        if p["kind"] == "node":
            kw[field] = [] if p["list"] else _leaf(p["base"], positions)
        elif p["list"]:
            kw[field] = []
        elif "str" in p["prims"]:
            kw[field] = "_x"
        elif "int" in p["prims"]:
            kw[field] = 0
        elif "bool" in p["prims"]:
            kw[field] = False
        else:
            kw[field] = None
    return getattr(ast, cls_name)(**kw)


def _as_statement(node, positions):
    """A statement carrying `node` in its natural container, for appending to a module body, by the base of `node`'s class: a
    statement as itself; an expression under an Expr; a pattern under a match_case of a Match; an except handler under a Try; a type
    parameter on a FunctionDef; and each product type that holds a node under the one class that holds it (a comprehension under a
    ListComp, arguments and an arg on a FunctionDef, a keyword under a Call, a withitem under a With, a match_case under a Match; an
    alias and a TypeIgnore hold no node, so neither is ever a container here). Reds naming a base no row holds, so a sum type or
    product class a new interpreter adds is named here rather than left unplanted (the rows are scaffolding for the containers and
    pin nothing: which positions exist is derived, and a row a position needs and lacks reds the witness and the instrument case)."""
    cls_name = type(node).__name__
    sum_type = type(node).__bases__[0].__name__
    base = sum_type if sum_type in _AST_ABSTRACT else cls_name
    if base == "stmt":
        return node
    if base == "expr":
        return ast.Expr(value=node)
    if base in ("pattern", "match_case"):
        case = node if base == "match_case" else _minimal("match_case", positions)
        if base == "pattern":
            case.pattern = node
        match = _minimal("Match", positions)
        match.cases = [case]
        return match
    if base == "excepthandler":
        t = _minimal("Try", positions)
        t.handlers = [node]
        return t
    if base in ("type_param", "arguments", "arg"):
        fd = _minimal("FunctionDef", positions)
        if base == "type_param":
            fd.type_params = [node]
        elif base == "arguments":
            fd.args = node
        else:
            fd.args.args = [node]
        return fd
    if base == "comprehension":
        comp = _minimal("ListComp", positions)
        comp.generators = [node]
        return ast.Expr(value=comp)
    if base == "keyword":
        call = _minimal("Call", positions)
        call.keywords = [node]
        return ast.Expr(value=call)
    if base == "withitem":
        w = _minimal("With", positions)
        w.items = [node]
        return w
    raise AssertionError("no container row in _as_statement for a node of base %s (class %s): a sum type or product class the rows do "
                         "not hold; add its row so the witness can plant at its positions" % (base, cls_name))


def _plantable(positions):
    """The node positions a plant can reach in the tree every census parses, an exec-mode Module, sorted: every node position but
    those of the roots of the other parse modes (Interactive, Expression and FunctionType derive from mod as Module does and are roots
    only, so nothing inside a Module holds them), the residue the witness states."""
    return sorted(key for key, p in positions.items()
                  if p["kind"] == "node" and (key[0] == "Module" or getattr(ast, key[0]).__bases__[0] is not ast.mod))


def _plant_at(tree, key, positions):
    """Plant a stranger at position `key`, (class, field), in `tree`, a Module: for a Module position the tree is the container (a
    stranger statement appended to its body, a stranger type ignore to its type_ignores); for any other, a minimal instance of the
    class (_minimal) with the field holding the stranger ([stranger] for a list field), wrapped to a statement by its natural
    container (_as_statement) and appended to the module body, the stranger deriving from the field's base (_stranger). Answers
    (container, stranger, unplant), unplant removing the plant by identity so a parsed tree is reused across drives. Builds nodes and
    traverses nothing (ast.copy_location and ast.fix_missing_locations give the plant line numbers, as a parse would)."""
    cls_name, field = key
    stranger = _stranger(positions[key]["base"])()
    if cls_name == "Module":
        held = getattr(tree, field)
        held.append(stranger)

        def unplant():
            held[:] = [item for item in held if item is not stranger]
        return tree, stranger, unplant
    container = _minimal(cls_name, positions)
    setattr(container, field, [stranger] if positions[key]["list"] else stranger)
    stmt = _as_statement(container, positions)
    if tree.body:
        ast.copy_location(stmt, tree.body[-1])
    ast.fix_missing_locations(stmt)
    tree.body.append(stmt)

    def unplant():
        tree.body[:] = [item for item in tree.body if item is not stmt]
    return container, stranger, unplant


# The census entry points of this module: every reader that walks a tree and answers a census, as (name, shape, drive) rows, the
# roster TheWalkersRefuseAStrangerByExecution drives over a tree with a stranger planted at every node position of the grammar the
# running interpreter defines (_grammar_positions, derived by execution; _plant_at, each position alone) and asserts each refuses
# every plant by name (the grammar refusal in _walk), so a census that walked around _walk in any position would pass that plant over
# and red the witness naming it and the position; the residue is the node positions of the roots of the other parse modes, which
# nothing inside a Module holds and no census parses, and a census that reads a child off the parent the walk yielded, which reds as
# an exception that is not the refusal. `shape` says where the entry point gets its tree: "tree", it is handed one (the drive takes a
# parser and parses the source the entry point reads with it); "parses", it parses inside (inspect.getsource, then ast.parse by
# attribute, which the witness patches so the plant lands exactly where that entry point parses; a parse whose root is not a Module
# takes no plant). The rule: a new census joins this roster
# with its row. The witness pins the roster's count and its floor, _census_floor's derivation over this module's own AST: every
# reader reference (_walk by name, or ast.parse, inspect.getsource or inspect.getsourcelines by attribute, called or handed on as a
# value) attributed to its enclosing def or class chain, whatever the container. A module-level def in the floor must be a row
# here; every class chain in the floor (a method, a nested class's method, a class-body statement) and every module-level statement
# in the floor is pinned by the roster case with the reason it is outside the roster (the readers inside the test classes, each a
# helper of a case or a case reading the tree it hands to a row, and the _door_regions row's drive lambda below, which reads the
# door's source as the argument of the parse the witness hands it). The floor's boundary is the spelling of the reader alone: a
# reference is in it only when it names _walk or spells one of the three exactly, base name and attribute; a census that parses
# under any other road (compile with ast.PyCF_ONLY_AST, the module under an alias, importlib) or is handed a pre-parsed tree under
# any parameter name, and walks by hand, is outside the floor in any container and joins by this rule alone, the count pin
# noticing the edit.
_CENSUSES = (
    ("_traversal_references", "tree", lambda parse: _traversal_references(parse(Path(os.path.realpath(__file__)).read_text(encoding="utf-8")))),
    ("_pass_through_lines", "parses", lambda _parse: _pass_through_lines(jd._or_fault, "loader")),
    ("_loader_sites", "parses", lambda _parse: _loader_sites(km._auto_nudge_session, "load_goals")),
    ("_bump_sites", "parses", lambda _parse: _bump_sites(km._auto_nudge_session)),
    ("_loader_births", "parses", lambda _parse: _loader_births(Path(os.path.realpath(jd.__file__)), judge=True)),
    ("_loader_births", "parses", lambda _parse: _loader_births(Path(os.path.realpath(km.__file__)), judge=False)),
    ("_door_regions", "tree", lambda parse: _door_regions(parse(textwrap.dedent(inspect.getsource(jd.load_goals_shared))))),
    ("_census_floor", "tree", lambda parse: _census_floor(parse(Path(os.path.realpath(__file__)).read_text(encoding="utf-8")))),
    ("_grammar_positions", "parses", lambda _parse: _grammar_positions()),
)


def _nested_codes(code):
    """The code object `code` and every code object reachable from it through co_consts, recursively, each once by identity, `code`
    first: the frames a call of the function compiled to `code` can run inside the function's own source, the function itself, the
    defs and lambdas nested in it at any depth, and the comprehensions the interpreter compiles as functions (generator expressions on
    every interpreter this module runs on; list, set and dict comprehensions on 3.10 and 3.11, which 3.12 and later inline, so the
    set's size is the interpreter's and no count is pinned). The door witness traces the door through this set (review round 7, the
    seventh-axis hunt: the trace read the door's own code object alone, a hand-written singleton where the interpreter holds the
    population, so the corrupt bump moved into a helper defined inside the door's handler executed in a frame the trace did not read,
    and the corrupt drive red its executed-sites line with a false cause, the site named as not executed while the counters had seen
    it). Derives: the set from the interpreter's constants, every level down. Bounds: a function defined outside `code` and called from
    it, a callee, is among no constant of it and is not in the set; a bump in a callee is no site of the door's tree either
    (_door_regions reads the door's source), so the counters alone see it, the drive reds where the trace and the counters must agree,
    and which callee each drive reaches is the door witness's class docstring's derivation."""
    found, todo = {id(code): code}, [code]
    while todo:
        for const in todo.pop().co_consts:
            if isinstance(const, types.CodeType) and id(const) not in found:
                found[id(const)] = const
                todo.append(const)
    return tuple(found.values())


@contextlib.contextmanager
def _line_trace(codes, hit):
    """Record in `hit` the line number of every 'line' event in frames running any code object of `codes`, by identity, while the
    block runs: sys.settrace on this thread, a tracer that traces those frames alone (any other frame gets no local tracer) and is put
    back the way it was found. The door witness hands it the door's code object and every code object nested in it (_nested_codes),
    so a bump site of the door is tied to a drive by execution and not by the name of the key it bumps (review round 6, lens two),
    whether the site runs in the door's own frame or in the frame of a helper defined inside the door (review round 7, the
    seventh-axis hunt). Derives: nothing; it records the lines that run. Bounds: `codes`, the caller's set; this thread; and a tracer
    already installed on it, which is set aside for the block, receives no event for anything entered inside it (a frame of a code
    object in `codes` or not), and is put back after it, so a coverage tool or a debugger over this module records nothing the
    drives run (measured with an outer tracer over the door witness on every interpreter this module runs on: it saw none of the
    thirteen in-window door calls and every door call outside a window)."""
    ids = {id(c) for c in codes}

    def local(frame, event, _arg):
        if event == "line":
            hit.add(frame.f_lineno)
        return local

    def tracer(frame, event, _arg):
        return local if event == "call" and id(frame.f_code) in ids else None
    previous = sys.gettrace()
    sys.settrace(tracer)
    try:
        yield hit
    finally:
        sys.settrace(previous)


def _caller(frame, boundary):
    """(function, file, line) of the frame that asked for the store: `frame` is the recorder's own, its f_back the immediate
    caller, and the judge's boundary frames are stepped over by code identity, never by name, so a call through either
    boundary wrapper is named for the kernel function that made it. `boundary` pairs each wrapper's code object with the
    lines of its pass-through calls (_pass_through_lines, taken at setUp): a boundary frame is stepped over only while it
    sits at one of those lines, so a load written anywhere else in a wrapper's own body is named for the wrapper itself,
    in the judge's file (the build's verifier pass after the round-1 fixes: stepped over unconditionally, a load planted inside
    _or_fault was named for the wrapper's kernel caller, the misnaming that costs more than silence). The file is the basename of the frame's REAL
    path: the kernel is loaded from bin/romp-kernel, a symlink to kernel/kernel.py, so the bare basename would read
    romp-kernel. Derives: the asker from the frame chain, the boundary frames stepped over by code identity while at a hand-off
    line. Bounds: `boundary`, the wrappers and lines setUp derives from the judge's source, three wrappers hand-picked as the
    judge's boundary set (held against the judge's AST by the birth pin's hand-offs line), so a fourth wrapper is a caller named
    for itself."""
    f = frame.f_back
    while True:
        lines = next((ls for c, ls in boundary if f.f_code is c), None)
        if lines is None or f.f_lineno not in lines:
            break
        f = f.f_back
    return f.f_code.co_name, os.path.basename(os.path.realpath(f.f_code.co_filename)), f.f_lineno


def _class_attributes(mod):
    """Every attribute of every class `mod` defines, {(class name, attribute): object}, read from the classes' own dicts (vars(c), so
    a staticmethod is the descriptor object and not the function it wraps) for every type bound in the module's globals whose
    __module__ is the module's name. The cleanup's leak check (_restore) compares this against setUp's snapshot: one container below
    the module globals, the level the fixture's own seam sits at (Sessions.backend_for). Before it, a stub a case left on any other
    class attribute of either module lived for every later test with the cleanup naming nothing (review round 7, the seventh-axis
    verifier: a new-identity pass-through on km.Sessions.live and on jd._ParseStore.get in the wedge-gate sweep case was still live at
    the module's last case), and the one hand-picked restore was itself lossy, since setUp read backend_for through getattr, the plain
    function a staticmethod hands out, and the restore put that function into the class dict in place of the staticmethod object
    (inert by reading: the kernel calls backend_for on the class at every site and never instantiates Sessions). Derives: the classes
    from the module's globals and their attributes from the class dicts, so no class attribute of either module is outside the check.
    Bounds: the containers read, a module's globals and its classes' dicts; the contents of a module-level dict, list or set, an
    instance's attributes and an imported module's attributes are outside it; and the ownership test, __module__ equal to the
    module's name, so a class the module imports, or builds under another module's name, is not read."""
    return {(cn, an): v for cn, c in vars(mod).items() if isinstance(c, type) and c.__module__ == mod.__name__
            for an, v in vars(c).items()}


class _FakeBackend:
    def __init__(self):
        self.sent = []

    def send(self, sid, body):
        self.sent.append((sid, body))

    def pending_queued(self, sid):
        return []


class _WalkHarness(unittest.TestCase):
    """The real pass over two synthetic sessions, the toggle off, every seam it moves put back by a cleanup registered
    before the first rebind (unittest skips tearDown when setUp raises and runs the cleanups regardless). Derives: what setUp
    rebinds, against REPLACED_KM and REPLACED_JD both ways (set equality over the kernel's and the judge's globals by identity, the
    names jd._rebind_state moves subtracted) with Sessions.backend_for beside them; REPLACED_DATA, the data names the census skips,
    against the names of REPLACED_KM whose kernel object is not callable, both ways (until the round-7 close the tuple was read one
    way: a data name left off it errored in the census's identity check, a callable put on it moved the census's count and, with
    the count edited, was skipped unseen); the two doors' identity before the recorders
    stand; the wrappers' hand-off lines and call counts from their source (_pass_through_lines), one line and one call each; per
    pass, in _pass, every counter delta against the recorded calls; and in the cleanup, _restore, every kernel and judge global
    against setUp's first snapshot by identity once the saved names are back, the names the restoring rebind moves subtracted, so a
    name a case rebound outside every list is named at that case's cleanup and put back (until the round-7 fixes _restore put the
    saved names back and checked no other name, so a new-identity pass-through on such a kernel name left the module green and the
    stub live for every later test), and every attribute of every class either module defines against the same snapshot, read
    from the classes' own dicts (_class_attributes; the container Sessions.backend_for sits in, which the cleanup put back by hand
    while a stub on any other class attribute was named by nothing until the round-7 close). Bounds: REPLACED_KM, REPLACED_JD, CASE_KM and CASE_JD, what the fixture replaces and what a
    case may, a policy, the first two pinned by execution in setUp and the last two by the cleanup's check (a case may replace only
    names on the saved lists, since any other is named as leaked); the containers the cleanup's check reads, the globals and the class dicts of both
    modules (the contents of a module-level dict, list or set, an instance's attributes and an imported module's attributes are
    outside it); the window, one tick; the doors recorded, the judge's two; WALK, GATE and SWEEP,
    the callers the condition names; the boundary set, three wrappers hand-picked as the judge's, held against the judge's AST by
    the birth pin's hand-offs line; KEYS, the walk counters the cases pin exactly (a tuple derived from km._NUDGE_WALK_STATS would
    report more with nothing asserting it); and the fixture constants, SIDS, NOW and the seeded stores."""

    def setUp(self):
        before_km, before_jd = dict(vars(km)), dict(vars(jd))   # FIRST: the agreement check at the end of setUp compares against these,
        self.before_km, self.before_jd = before_km, before_jd   #   and _restore compares every global of both modules against them
        self.before_cls = {label: _class_attributes(mod) for label, mod in (("kernel", km), ("judge", jd))}   # and every class
        #                                                   attribute of both, the container the fixture's own seam sits in (_restore)
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)                  # cleanups run last in, first out: the seams go back, then the dir
        td = Path(self.td.name)
        self.saved = {k: getattr(km, k) for k in REPLACED_KM + CASE_KM}   # CASE_KM and CASE_JD saved too: a case replaces them after setUp
        self.saved_jd = {k: getattr(jd, k) for k in REPLACED_JD + CASE_JD + ("load_goals", "load_goals_shared")}
        self.saved_state = jd.STATE
        self.saved_backend = vars(km.Sessions)["backend_for"]   # the class-dict object, a staticmethod; through getattr it would be
        #                                                       the plain function, and the restore would bind that in its place
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
        # the INNER door, jd.load_goals_shared: load_goals_shared_or_fault resolves that name from the judge's globals at each
        # call and hands the object to _or_fault, so a call by either spelling arrives here (a recorder on the outer door alone
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
        data = tuple(k for k in REPLACED_KM if not callable(before_km[k]))   # the data names among them, from the objects setUp found
        self.assertEqual(data, REPLACED_DATA, "REPLACED_DATA is exactly the names of REPLACED_KM whose kernel object is not callable, in the "
                                              "list's order, derived from setUp's first snapshot (the replaced-helpers census skips these names; "
                                              "until the round-7 close the tuple was pinned by its count alone, so a callable put on it with the "
                                              "count edited to match left that helper's real body unscanned): derived %r, the tuple %r"
                                              % (data, REPLACED_DATA))
        rebound_jd = {k for k, v in vars(jd).items() if before_jd.get(k, _UNSET) is not v} - rebound_by_rebind
        self.assertEqual(rebound_jd, set(REPLACED_JD) | {"load_goals", "load_goals_shared"},
                         "and exactly the judge names REPLACED_JD lists plus the two recorded doors (the names jd._rebind_state moves "
                         "subtracted)")
        self.assertIsNot(vars(km.Sessions)["backend_for"], self.saved_backend, "and Sessions.backend_for, replaced beside them")

    def _before_rebind(self):
        """A no-op hook, called right before the judge snapshot the rebind's diff is read against: the region between setUp's first
        snapshot and the rebind, where a judge stub was filed as the rebind's and escaped until the build's verifier pass after the
        round-2 fixes. A pin overrides it
        to place a stub there and expects setUp to refuse it (TheAgreementCheckSpansSetUp)."""

    def _after_rebind(self):
        """A no-op hook, called right after jd._rebind_state: the region the agreement check's first snapshot missed (review round
        2). A pin overrides it to place a stub there and expects setUp to refuse it (TheAgreementCheckSpansSetUp)."""

    def _restore(self):
        """Every seam back the way setUp found it: the saved kernel and judge names, the backend, the caches, the counters, the
        journals, the state root; then the check the saved lists cannot make: every kernel and judge global is the object setUp's
        first snapshot held, by identity, over the union of the names then and now, the names jd._rebind_state moves subtracted (the
        diff across the restoring rebind, as setUp reads them across its own), and then the same check one container below, every
        attribute of every class either module defines against setUp's snapshot of the class dicts (_class_attributes), read after
        the globals are back so a rebound class name reaches the snapshot's class. A name a case rebound, added or deleted outside
        REPLACED_KM, CASE_KM, REPLACED_JD, CASE_JD, the two doors and Sessions.backend_for, at either level, is put back and this
        cleanup reds naming it (a class attribute as Class.attr under a kernel or judge class-attributes label), so the case that
        leaked it fails and the tests after it run over the modules setUp found (review round 7, the seventh-axis hunt: before this
        check a new-identity pass-through on km._nudge_response_ready, a kernel name in neither list, left the module green with the
        stub live for every later test; the round's seventh-axis verifier: the same pass-through on km.Sessions.live and on
        jd._ParseStore.get, class attributes, was live at the module's last case with the check over the globals green). Derives:
        the leaked names from both modules' globals and from their classes' dicts against the snapshots. Bounds: the containers
        read, the globals and the class dicts (a member of a module-level dict, list or set, an instance attribute or an imported
        module's attribute is outside it); the
        names the restoring rebind moves, subtracted, so a stub a case leaves on one of the judge's directory or path names is
        overwritten by the rebind and not named (setUp's check has the same edge); TICK_REBOUND_KM and TICK_REBOUND_JD, the
        allowance for a global the tick itself rebinds, empty today and checked only to name a live global; and _INTERPRETER_GLOBALS,
        the warnings registry the interpreter writes into a module's globals on the first warning raised from it, set aside by name
        (a kernel warning inside a harness case is no stub; before this, it red the case's cleanup naming the registry)."""
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
        pre_rebind = dict(vars(jd))                      # the judge's globals AT the restoring rebind, so the names it moves are the diff
        jd._rebind_state(self.saved_state)               # the root goes back the way it was found (the parse entries go with it)
        moved = {k for k, v in vars(jd).items() if pre_rebind.get(k, _UNSET) is not v}
        stale = ([k for k in TICK_REBOUND_KM if k not in self.before_km] + [k for k in TICK_REBOUND_JD if k not in self.before_jd])
        self.assertEqual(stale, [], "an allowance row names a global the snapshot holds; these name none: %r" % stale)
        leaked = {}
        for label, mod, before, allowed, subtract in (("kernel", km, self.before_km, TICK_REBOUND_KM, set()),
                                                      ("judge", jd, self.before_jd, TICK_REBOUND_JD, moved)):
            now = dict(vars(mod))
            names = sorted(k for k in (set(before) | set(now)) - subtract - set(allowed) - _INTERPRETER_GLOBALS
                           if now.get(k, _UNSET) is not before.get(k, _UNSET))
            for k in names:                              # back to the snapshot's object first, so the tests after this one are undisturbed
                if k in before:
                    setattr(mod, k, before[k])
                else:
                    delattr(mod, k)
            if names:
                leaked[label] = names
        for label, mod in (("kernel", km), ("judge", jd)):    # one container below: every class attribute of both modules, read after
            before, now = self.before_cls[label], _class_attributes(mod)   # the globals went back, so a rebound class name reaches
            names = sorted(k for k in set(before) | set(now) if now.get(k, _UNSET) is not before.get(k, _UNSET))   # the snapshot's class
            for cls_name, attr in names:
                if (cls_name, attr) in before:
                    setattr(getattr(mod, cls_name), attr, before[(cls_name, attr)])
                else:
                    delattr(getattr(mod, cls_name), attr)
            if names:
                leaked[label + " class attributes"] = ["%s.%s" % k for k in names]
        self.assertEqual(leaked, {}, "every kernel and judge global, and every attribute of every class either module defines, is the "
                                     "object setUp's first snapshot held once the saved names are back (the names the rebind moves "
                                     "subtracted); these were rebound, added or deleted by this case outside REPLACED_KM, CASE_KM, "
                                     "REPLACED_JD, CASE_JD, the two doors and Sessions.backend_for, and are put back here: %r"
                                     % leaked)

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
        only after its miss or compare_miss bump and bumps at most one, witnessed per road by execution in
        TheDoorBumpsAtMostOneSecondKeyPerCall, and per pass
        unreadable_journal + corrupt + dup + refuse <= miss + compare_miss. Of the three premises of that reading, the rosters and
        the order are pinned against the door's AST by the roster pin in TheCountersOneSite; the at-most-one is carried by that
        witness, which drives one road per key of both rosters, a second road for the unreadable_journal key's second site, and three
        raise roads on the real door and reads the counters per call, and the roster pin's AST clauses are its early warning, refusing the forms they name (a second-key bump that is not a
        statement of a list, a second-key list holding two, a list not ending in a return or a raise, a bump under a finally clause,
        a second-key raise list under a try statement) and silent on the rest;
        the fill keys the right-hand side sums are derived by the pin from the same AST and asserted equal to SHARED_FILL_KEYS,
        which this method sums (review round 4, tests-2, regression-2 and extra4-1: the two named by hand here, and the
        at-most-one held by nothing; review round 5, correctness-1, regression-1 and extra6-1: held by the clauses alone, and three
        constructs they pass bumped two). The bound is what refuses the forged pair: corrupt and
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
        and a spurious dup or refuse bump beside a genuine fill, up to the fill count, was witnessed by nothing; the door witness
        drives the dup and refuse roads on purpose, one call each outside any pass, so this line stands as written). `calls` carries the
        shared records (sid, function, file, line) for a case's own assertions, and `second` the second keys' delta, so the writerLoads
        lines that catch the pair beside a fill can print it (review round 4, tests-4). Derives: per pass, the recorded shared calls
        against WALK, GATE and SWEEP by the caller's function name, the caller named by code identity through the wrappers' hand-off
        lines (_pass_through_lines at setUp); the call keys' delta against the recorded calls; the second keys' sum against the fills
        over SHARED_FILL_KEYS, the keys the roster pin derives from the door's AST; the writer door's loads against the hand-offs over
        SHARED_HANDOFF_KEYS, the keys the same pin derives from the door's lists that end in a return of a load_goals call; the gate's
        checks against its derives. Bounds: WALK, GATE and SWEEP, the callers the condition names, hand
        lists; the ceilings (one per sid for the walk and the gate, the owned records for the sweep), the condition's own figures; the
        window, one _auto_nudge_tick call; and the doors recorded, the judge's two, with what setUp replaces pinned there against
        REPLACED_KM and REPLACED_JD both ways, and CASE_KM and CASE_JD, what a case replaces after setUp, pinned from the outside by
        the cleanup's check (_restore) over both modules' globals and their classes' attributes: a case may replace only names on the
        saved lists, since any other is named as leaked at its cleanup (until the round-7 fixes the two lists were pinned by nothing,
        and this sentence said so past that fix)."""
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
                         "shared door hands a read to load_goals on exactly the %s counters (SHARED_HANDOFF_KEYS, derived from the door's "
                         "AST by the roster pin); the recorded writer calls are zero here (the assertion above), so the delta must equal "
                         "those hand-offs alone; a difference is a writer-door load the recorder did not see, through a reference to the "
                         "real door taken before it stood or written inside the shared door's own body (the fallback skip takes it for the "
                         "hand-off): loads %d against hand-offs %d" % (", ".join(SHARED_HANDOFF_KEYS), g1 - g0, handoffs))
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
    """The at-most-one premise of the second-bump bound by execution, over one road per key of both rosters, nine, a second road for
    the unreadable_journal key's second site, the door's _unread arm, and three raise roads on neither (review round 4, tests-2,
    regression-2 and extra4-1 for the corrupt road; review round 5, correctness-1, regression-1, extra6-1 and extra6-2, and the
    reviewer's ruling on approach: the roster pin's three AST clauses in TheCountersOneSite are an early warning that refuses
    the forms they name and are silent on the rest, and this class carries the contract on something that enumerates no
    syntax). Each drive is one call of the real door, jd.load_goals_shared, on SID_C (never alive, so never walked; each method
    has a state root of its own from setUp), outside any pass (no tick runs, so _pass's dup and refuse zero line stands as
    written), under the harness's recorders (setUp stands them and checked the door's code identity; the recorder calls
    through, and the counters read are the real _SHARED_STATS through shared_store_stats, never a spy over the AST), the road
    arranged first and the counters read before and after the call. Every drive asserts the same lines through _drive: one
    recorded call, made by _drive in this file; the call keys' delta exactly the road's; AT MOST ONE second key bumped, the
    line every construct nobody listed reds (a helper defined inside the door and called from a second-key list, a Return whose
    expression raises into a handler that bumps, an exception from any other statement of a clean list caught by a bumping
    handler, contextlib.suppress: each is caught here on the road it sits on when a drive reaches that road; the first three, each
    planted on the corrupt road, bumped two with the AST clauses green, and the round-5 history paragraph records the figures); the
    second keys' delta exactly the road's, so a bump
    outside the fill road (in _shared_forget on the absent road, say) reds too; the hand-offs, goal_io loads, exactly the road's;
    and the writer recorder empty. ROADS is the table of expected deltas per road, one method per road named for it
    (`test_the_<road>_road...`; _drive checks the name), and the coverage case derives from the table that the drives cover
    every key of both rosters and from the method names that every row is driven, so a key added to a roster with no drive
    reds naming it, as does a row with no method.
    Driven: hit ({'hit': 1}, no second key, no hand-off, loads_shared moves); miss ({'miss': 1}, none, none); compare_miss
    (the store file rewritten in place at the same length with its mtime put back, so (ino, mtime_ns, size) stand and the
    bytes differ: {'compare_miss': 1}, none, none); absent (no store: {'absent': 1}, none, one hand-off); fallback (the cache
    off, no store: {'fallback': 1}, none, one hand-off, load_goals' fresh store); corrupt (bytes that do not parse: {'miss': 1},
    {'corrupt': 1}, one hand-off, the quarantine); unreadable_journal (a symlink loop at the journal's path: _journal_key
    answers a _StatFailed before the read and _journal_read's open raises ELOOP, an OSError that is not FileNotFoundError:
    {'miss': 1}, {'unreadable_journal': 1}, one hand-off; load_goals' own replay sees is_file() false on the loop and marks
    nothing, so no history-unreadable row is written, and the case says so); unread (the seeded store file rewritten with a top-level
    _unread key, which the writer never serializes and a hand-written or foreign file can carry: the parse answers the file's dict, the
    node guard and the replay leave the key, and the door's `if store.get("_unread")` arm takes it, the second unreadable_journal site:
    {'miss': 1}, {'unreadable_journal': 1}, no hand-off, the marked store answered and nothing published); dup (the published entry
    popped and republished
    from a seam on _freeze_store between the door's two archive-key reads, what a concurrent fill does at its publish:
    {'miss': 1}, {'dup': 1}, none, the published object answered); refuse (an archive file written from the same seam, so the
    archive key moved under the replay: {'miss': 1}, {'refuse': 1}, none, nothing published, and a following call is a miss
    that fills); and three raise roads on neither roster: a symlink loop at the store path (the open raises) and a directory
    there (the read raises), each moving no key and propagating the OSError, the module docstring's sentence that a call whose
    open or read raises moves none, held by execution; and a journal row whose instant is not a number (fill_raises: the replay's
    int() raises out of _finish_load after the miss bump and the loads_shared bump, {'miss': 1}, no second key, no hand-off, the
    ValueError propagated, nothing cached; a verifier of the round-5 fixes found this road neither driven nor named, and a
    second-key bump planted in a handler around _finish_load was witnessed by nothing). The seam on jd._freeze_store is a wrapper over the real function
    (functools.wraps, calling through), a name CASE_JD lists so the cleanup restores it; _archive_key stays real. The roads are
    tied to the door's bump SITES by execution and not by the keys' names (review round 6, lens two: the coverage case derived the
    key set of ROADS against the rosters, so a new key with no drive red it, but a second site bumping an already driven key, a
    second refuse branch conditioned on state no drive arranges, was on no driven road with the module green): the sites are read
    from the real door's source as (key, ordinal) pairs, the ordinal counting a key's sites in source order (_door_regions, the
    roster pin's read, mapped to the file's lines as _pass_through_lines maps a hand-off), each row of ROADS names the sites its
    call executes, each drive asserts by a trace of the door's frames, its own code object and every code object nested in it
    (_line_trace over _nested_codes), that exactly those sites ran, and the
    coverage case derives that every site of the door is named by a row or by UNDRIVEN_SITES, with none in both, so a new site
    reds naming its line until a drive or a statement names it. UNDRIVEN_SITES is empty: every bump site of the door is executed by
    a drive. The door's `if store.get("_unread")` arm, the second unreadable_journal site, was its one row until the round-7 fixes, on
    the ground of the door's own comment, which calls the arm unreachable while _journal_read hands the rows as lines; the comment is
    right about the replay's mark, which a replay handed lines never sets, and the arm is reachable through the store file's own
    content, so the unread road drives it, and a bump planted on the arm through an alias of the counters, a form no clause of the
    roster pin reads, left the module green on the tree of the round's second fix and reds the unread drive since (review round 6,
    extra5-1, extra6-2 and tests-5). Undriven and
    not a site: a compare_miss entering the dup or refuse arm (the drives enter both from a miss; past the fill's
    first statement the code is the same); and any second bump conditioned on the hand-off itself raising (load_goals raising
    on the corrupt road: the drive's load_goals quarantines and answers a fresh store, so a Return whose expression raises is
    exercised by another raise, not by a raising hand-off); and the arrangement itself: no drive arranges a store of more than one
    node (the drives that seed, seed one node under SID_C; the absent, fallback, corrupt, open_raises and read_raises drives seed
    none), every drive is on one sid and _drive calls the door once, so a second bump conditioned on state no drive arranges (a
    store of two or more nodes, another sid, a call count) is on no driven road, and the at-most-one line holds against whatever nobody listed ON A DRIVEN
    ROAD (a verifier of the round-5 fixes: a dup bump under a two-node condition after _finish_load left every drive green with
    the AST clauses green, and a two-node store moved it). Which callee each drive witnesses, as a dup bump planted in each and
    run derives it (re-derived over the drives on the tree of the round-7 unread-road fix): a bump in _shared_forget by the absent,
    unreadable_journal, corrupt and unread drives and the open_raises and
    read_raises drives (and by _pass's per-pass lines on the no-store sweep case; the fill's raise propagates before the door
    would call it); one in _guard_nodes or _finish_load by the miss, compare_miss, dup, refuse, unreadable_journal, unread and
    fill_raises drives (unreadable_journal through load_goals' own tail on the hand-off; fill_raises because the bump runs before
    the replay raises; the corrupt drive's load_goals answers a fresh store after the quarantine and runs neither) and by
    _pass's reconciliation on fill passes; one in _freeze_store by the miss, compare_miss, dup and refuse drives and by _pass on
    fill passes (the _unread arm returns before the freeze); one in _journal_read by every drive that enters the fill road (miss,
    compare_miss, corrupt, unreadable_journal, dup, refuse, fill_raises, unread) and one in _disk_parse by those but
    unreadable_journal, whose journal read raises before the parse; one on the door's _unread arm, between its bump and its return,
    by the unread drive alone and by no harness case's pass (the harness's stores carry no mark and their journals read).
    Derives: the door's bump sites as (key, ordinal) from the real door's source through _door_regions (_sites); the sites each call
    executed, by a trace of the door's code object and every code object nested in it, the set derived from co_consts (_line_trace
    over _nested_codes), the set checked by the coverage case against the defs nested in the door's statement lists both ways and, since
    the door holds no nested code object today, by execution over a stand-in with a def two levels down, a lambda and a generator
    expression, the old singleton as the control; the coverage, the door's sites against the rows' sites plus
    UNDRIVEN_SITES both ways and none in both; the keys ROADS expects against both rosters both ways; the rows against the class's
    method names both ways; per site, whether the statement list holding it hands the read to load_goals (_door_hands_off, the roster
    pin's predicate), each row's hand-off column against the count over its sites, and the no-hand-off sites of hand-off keys, the
    _unread arm alone today, each executed by a drive and in no row of UNDRIVEN_SITES; the counters per call from the real
    _SHARED_STATS and goal_io loads. Bounds: the expected call-key and second-key deltas per road and each road's arrangement,
    hand-written and held by execution; the arrangement's limit, at most one node in the store, one sid and one call per drive
    (until the round-7 close this sentence said every drive seeds a one-node store, false for the five drives that seed none), so
    a bump conditioned on state no drive arranges is on no driven road; the stand-in's shape, hand-written, a contract over
    the mechanism; and the trace's reach, the door's source: a bump in a function defined outside the door and called from it, a
    callee, is no site of the door's tree (_door_regions reads the door's source) and runs in no frame of the derived set, so the
    counters alone see it and the drive reds at the line where the trace's keys and the counters' must agree, naming the key, and
    which callee each drive witnesses is the derivation above."""

    # The roads and the deltas each drive asserts: road -> (call keys, second keys, goal_io loads hand-offs, the exception the call
    # propagates or None, the bump SITES the call executes as (key, ordinal) pairs, the ordinal counting that key's sites in the door's
    # source order from 0). The coverage case derives from this table that the call and second keys over every row are exactly both
    # rosters, that a row's sites name exactly the keys its deltas name, that the sites over every row plus UNDRIVEN_SITES are
    # exactly the door's own bump sites (_sites), that each row's hand-off column is the number of its sites whose statement list ends
    # in `return load_goals(...)` (_sites reads it from the door's lists through _door_hands_off, the roster pin's predicate), and from
    # the class's method names that every road here has a method named for it; each drive asserts by a trace of the door's frames (its
    # code object and every code object nested in it) that its call executed exactly its row's sites.
    ROADS = {
        "hit": ({"hit": 1}, {}, 0, None, (("hit", 0),)),
        "miss": ({"miss": 1}, {}, 0, None, (("miss", 0),)),
        "compare_miss": ({"compare_miss": 1}, {}, 0, None, (("compare_miss", 0),)),
        "absent": ({"absent": 1}, {}, 1, None, (("absent", 0),)),
        "fallback": ({"fallback": 1}, {}, 1, None, (("fallback", 0),)),
        "corrupt": ({"miss": 1}, {"corrupt": 1}, 1, None, (("miss", 0), ("corrupt", 0))),
        "unreadable_journal": ({"miss": 1}, {"unreadable_journal": 1}, 1, None, (("miss", 0), ("unreadable_journal", 0))),
        "dup": ({"miss": 1}, {"dup": 1}, 0, None, (("miss", 0), ("dup", 0))),
        "refuse": ({"miss": 1}, {"refuse": 1}, 0, None, (("miss", 0), ("refuse", 0))),
        "open_raises": ({}, {}, 0, OSError, ()),
        "read_raises": ({}, {}, 0, OSError, ()),
        "fill_raises": ({"miss": 1}, {}, 0, ValueError, (("miss", 0),)),
        "unread": ({"miss": 1}, {"unreadable_journal": 1}, 0, None, (("miss", 0), ("unreadable_journal", 1))),
    }
    # The door's bump sites no drive reaches, (key, ordinal) -> the reason, derived against the door's own sites by the coverage case
    # (every site is in a row of ROADS or here, none in both), so a site added to the door reds there naming its line until a drive
    # reaches it or a row here says why none does. Empty: every site of the door is driven today. The `if store.get("_unread")` arm,
    # the second unreadable_journal site, stood here until the round-7 fixes on the ground of the door's own comment, which calls the
    # arm unreachable while the journal's rows arrive as lines; that is true of the replay's mark and not of the arm, which a store
    # file carrying a top-level _unread key reaches (the unread road). A future site no drive can reach states its (key, ordinal) and
    # the reason here; the coverage case's derivation does not change.
    UNDRIVEN_SITES = {}

    def _sites(self):
        """The door's bump sites in execution's coordinates, two maps over the same (key, ordinal) pairs, the ordinal counting a key's
        sites in source order from 0: the absolute line of each, read from the real door's source through _door_regions (the roster
        pin's read of the door, a roster row) and mapped to the file's lines as _pass_through_lines maps a hand-off (inspect gives the
        source with its first line's number); and whether the statement list holding each as a direct statement hands the read to
        load_goals (_door_hands_off, the roster pin's predicate over the same lists). A bump that is a direct statement of no list (an
        assignment's value, say) hands nothing off here, and the row whose drive reads a load at it disagrees with the derivation. Third,
        the sorted names of the defs nested in the door, every FunctionDef or AsyncFunctionDef that is a statement of one of the same
        lists below the parsed source's own body (which holds the door's def), at any depth, the tree's side of the coverage case's
        check on the traced code objects (_nested_codes). The
        real door is the one setUp saved before it stood the recorder on the name."""
        door = self.saved_jd["load_goals_shared"]
        src, start = inspect.getsourcelines(door)
        tree = ast.parse(textwrap.dedent("".join(src)))
        bumps, blocks, _tries = _door_regions(tree)
        handing = {(s.lineno, _door_stmt_key(s)): _door_hands_off(blk) for blk in blocks for s in blk if _door_stmt_key(s) is not None}
        by_key = {}
        for rel, key in sorted(bumps):
            by_key.setdefault(key, []).append(rel)
        lines = {(key, i): start - 1 + rel for key, rels in by_key.items() for i, rel in enumerate(rels)}
        hands = {(key, i): handing.get((rel, key), False) for key, rels in by_key.items() for i, rel in enumerate(rels)}
        nested = sorted(s.name for blk in blocks if blk is not tree.body      # the parsed source's own body holds the door's def
                        for s in blk if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)))
        return lines, hands, nested

    def _store_path(self):
        return jd.GOALDIR / (SID_C + ".json")

    def _drive(self, road):
        """One call of the real door on SID_C for `road`, arranged by the caller, the counters read before and after: the lines
        every road asserts (the class docstring). Answers (store, the stderr text, the exception propagated) for the road's own
        assertions."""
        self.assertTrue(self._testMethodName.startswith("test_the_%s_road" % road),
                        "a drive sits in the method named for its road (test_the_<road>_road...), the rule the coverage case derives from: "
                        "%s drives %r" % (self._testMethodName, road))
        expect_calls, expect_second, expect_loads, raises, expect_sites = self.ROADS[road]
        here = os.path.basename(os.path.realpath(__file__))
        (sites, _hands, _nested), hit = self._sites(), set()
        door = self.saved_jd["load_goals_shared"]
        codes = _nested_codes(door.__code__)
        self.assertIs(codes[0], door.__code__, "the set the trace reads is derived from the real door's code object, which heads it: %r"
                                               % [c.co_name for c in codes])
        s0, g0 = jd.shared_store_stats(), jd.goal_io_stats()["loads"]
        self.calls.clear(); self.writer.clear()
        err, store, exc = io.StringIO(), None, None
        with contextlib.redirect_stderr(err), _line_trace(codes, hit):
            if raises is None:
                store = jd.load_goals_shared(SID_C)
            else:
                with self.assertRaises(raises) as cm:
                    jd.load_goals_shared(SID_C)
                exc = cm.exception
        s1, g1 = jd.shared_store_stats(), jd.goal_io_stats()["loads"]
        calls = {k: s1[k] - s0[k] for k in SHARED_CALL_KEYS if s1[k] != s0[k]}
        second = {k: s1[k] - s0[k] for k in SHARED_SECOND_KEYS if s1[k] != s0[k]}
        executed = sorted(site for site, line in sites.items() if line in hit)
        self.assertEqual(executed, sorted(expect_sites),
                         "%s road: the bump sites the call executed, read by a trace of the door's frames (its code object and every code "
                         "object nested in it, derived from co_consts) against the sites _door_regions "
                         "reads from its source ((key, ordinal), the ordinal counting that key's sites in source order), are exactly the "
                         "road's, %r, and were %r; so a site is tied to this drive by execution and not by its key's name, and a second site "
                         "bumping an already driven key is on no driven road until a row names it (review round 6, lens two); the sites by "
                         "line: %r" % (road, sorted(expect_sites), executed, sorted(sites.items())))
        self.assertEqual({k for k, _i in executed}, set(calls) | set(second),
                         "%s road: the keys of the sites the trace saw executed are the keys whose counters moved, so the trace and the "
                         "counters agree on this call: sites %r, counters %r" % (road, executed, sorted(set(calls) | set(second))))
        self.assertEqual([(c, f) for _s, c, f, _ln in self.calls], [("_drive", here)],
                         "%s road: one call through the door, made by _drive for %s, recorded by the shared recorder in this file: %r"
                         % (road, self._testMethodName, self.calls))
        self.assertLessEqual(sum(second.values()), 1,
                             "%s road: a call of the door bumps AT MOST ONE second key (unreadable_journal, corrupt, dup, refuse), the premise "
                             "the second-bump bound's derivation rests on, and this call bumped %d: %r. This line reads the real counters "
                             "after one call on the real door, so it holds against every construct the roster pin's AST clauses do not name "
                             "(a helper defined inside the door, a Return whose expression raises into a bumping handler, an exception from a "
                             "clean list's other statement caught by one, contextlib.suppress, and whatever nobody listed on a driven road: "
                             "no drive arranges a store of more than one node, every drive is on one sid and the drive calls the door once, "
                             "so a bump conditioned on state no drive arranges is on none); the call keys moved: %r" % (road, sum(second.values()), second, calls))
        self.assertEqual(calls, expect_calls, "%s road: the call keys' delta is exactly the road's, %r, and was %r (a call that reaches the "
                                              "cache's branch and returns moves exactly one; a call whose open or read raises moves none)"
                                              % (road, expect_calls, calls))
        self.assertEqual(second, expect_second, "%s road: the second keys' delta is exactly the road's, %r, and was %r (so a bump on a road "
                                                "that takes none, in a callee such as _shared_forget on the absent road, reds here)"
                                                % (road, expect_second, second))
        self.assertEqual(g1 - g0, expect_loads, "%s road: the hand-offs to load_goals, read from the writer door's own counter (goal_io loads), "
                                                "are exactly the road's, %d, and were %d" % (road, expect_loads, g1 - g0))
        self.assertEqual(self.writer, [], "%s road: a hand-off is the shared door's own read, skipped by code identity, so the writer recorder "
                                          "recorded nothing: %r" % (road, self.writer))
        return store, err.getvalue(), exc

    def test_the_table_covers_both_rosters_and_every_row_is_driven_by_a_method_named_for_it(self):
        keys = set()
        for road, (calls, second, _loads, _raises, _sites) in self.ROADS.items():
            keys |= set(calls) | set(second)
        rosters = set(SHARED_CALL_KEYS) | set(SHARED_SECOND_KEYS)
        self.assertEqual(keys, rosters, "the keys the drives expect over ROADS are exactly the call keys and the second keys: a key in a "
                                        "roster that no drive reaches, %r, is a road this class does not witness (add its drive); a key a "
                                        "drive expects that is in neither roster, %r, is a counter the reconciliations do not read"
                                        % (sorted(rosters - keys), sorted(keys - rosters)))
        declared = {m.group(1) for m in (re.match(r"test_the_(\w+?)_road", name) for name in dir(type(self))) if m}
        self.assertEqual(declared, set(self.ROADS), "every road of ROADS is driven by a method named test_the_<road>_road... and every such "
                                                    "method drives a road of the table (_drive checks the name it is called under): rows "
                                                    "with no method %r, methods with no row %r"
                                                    % (sorted(set(self.ROADS) - declared), sorted(declared - set(self.ROADS))))
        # the sites (review round 6, lens two): every bump site of the door, read from its source as (key, ordinal), is named by a row's
        # sites column, which its drive holds by a trace of the door's frame, or by UNDRIVEN_SITES with its reason, and by neither both,
        # so a second site under an already driven key reds here naming its line, where the key set above cannot see it
        for road, (calls, second, _loads, _raises, road_sites) in self.ROADS.items():
            self.assertEqual({k for k, _i in road_sites}, set(calls) | set(second),
                             "%s: the sites column names exactly the keys the row's deltas name (a site of a key whose counter the road "
                             "does not move, or a moved key with no site, is a row that disagrees with itself): sites %r, deltas %r"
                             % (road, road_sites, sorted(set(calls) | set(second))))
        sites, hands, nested = self._sites()
        driven = {site for _road, row in self.ROADS.items() for site in row[4]}
        stated = set(self.UNDRIVEN_SITES)
        self.assertEqual(sorted(driven & stated), [], "a site a drive executes is stated undriven: remove the statement: %r" % sorted(driven & stated))
        self.assertEqual(sorted((driven | stated) - set(sites)), [],
                         "a row or a statement names a bump site the door does not have (by (key, ordinal); the door's sites are %r): %r"
                         % (sorted(sites), sorted((driven | stated) - set(sites))))
        self.assertEqual(sorted(set(sites) - (driven | stated)), [],
                         "a bump site of the door that no drive executes and no statement names, by (key, ordinal) and line: %s. A second "
                         "site bumping an already driven key is on no driven road; add the drive that reaches it, or a row to "
                         "UNDRIVEN_SITES saying why none does"
                         % "; ".join("%r at line %d" % (site, sites[site]) for site in sorted(set(sites) - (driven | stated))))
        # the hand-off column (review round 7, the seventh-axis hunt): each row's hand-offs are the count of its sites whose statement
        # list hands the read to load_goals, read from the door's lists by _sites through the roster pin's predicate, so the column a
        # drive holds by the writer door's counter and the lists the roster pin derives SHARED_HANDOFF_KEYS from agree per road
        for road, (_calls, _second, loads, _raises, road_sites) in self.ROADS.items():
            self.assertEqual(loads, sum(1 for site in road_sites if hands[site]),
                             "%s: the row's hand-off column, %d, is the number of its sites whose statement list ends in `return load_goals(...)` "
                             "(_door_hands_off over the door's lists), %d: sites %r (the drive holds the column by goal_io loads, so a "
                             "disagreement is a hand-off the list does not show, through a temporary or an alias of the loader, or a list "
                             "that hands off on a road whose drive reads no load)"
                             % (road, loads, sum(1 for site in road_sites if hands[site]), sorted((site, hands[site]) for site in road_sites)))
        # a bump of a hand-off key whose list does not hand off (the door's _unread arm today): _pass's writer reconciliation counts
        # every bump of a hand-off key as a load, so a pass that reached it would red there, and its only witness is a drive that
        # reads 0 hand-offs at it; such a site is never left to a statement
        silent = sorted(site for site, off in hands.items() if site[0] in SHARED_HANDOFF_KEYS and not off)
        self.assertEqual(sorted(set(silent) - driven), [],
                         "a bump site of a hand-off key whose statement list does not hand the read to load_goals is executed by a drive, "
                         "which reads 0 hand-offs at it, and is in no row of UNDRIVEN_SITES: a pass that reached it would red _pass's writer "
                         "reconciliation (every bump of a hand-off key counted as a load), so a drive outside any pass is its one witness; "
                         "such sites %r, of which undriven %r" % (silent, sorted(set(silent) - driven)))
        # the trace's reach (review round 7, the seventh-axis hunt): the drives trace the door through _nested_codes, its code object and
        # every code object nested in it, derived from co_consts. The set against the door's tree: every def nested in the door's
        # statement lists (the third map of _sites, read from the lists _door_regions holds) is a code object of the set by name, and
        # every unbracketed name of the set below the door is such a def, both ways (the bracketed names, <lambda>, <genexpr> and the
        # comprehensions of 3.10 and 3.11, are no statement and are traced without a tree-side twin). The door holds no nested code
        # object today, so both sides are empty there and the check would pass with a derivation answering the door alone; the mechanism
        # is therefore held by execution over a stand-in, each of its code objects traced alone first
        door = self.saved_jd["load_goals_shared"]
        codes = _nested_codes(door.__code__)
        self.assertIs(codes[0], door.__code__, "the derived set is headed by the real door's code object: %r" % [c.co_name for c in codes])
        self.assertEqual(sorted(c.co_name for c in codes[1:] if not c.co_name.startswith("<")), nested,
                         "the defs nested in the door by the interpreter's constants (_nested_codes, the unbracketed names below the door) "
                         "are the defs nested in the door's statement lists by its tree (_sites), both ways: by the constants %r, by the tree "
                         "%r; a def the tree holds and the constants do not is a frame the trace would not read"
                         % (sorted(c.co_name for c in codes[1:] if not c.co_name.startswith("<")), nested))

        def stand_in(x):
            def helper(y):
                def deeper(z):
                    return z + 1
                return deeper(y) + 1
            twice = lambda v: (
                v * 2)
            return helper(x) + twice(x) + sum(w for w in (x,))

        derived = _nested_codes(stand_in.__code__)
        self.assertEqual(sorted(c.co_name for c in derived), ["<genexpr>", "<lambda>", "deeper", "helper", "stand_in"],
                         "the stand-in's code objects by the derivation: itself, a def, a def nested in that def, a lambda and a generator "
                         "expression (its shape, a contract), and were %r" % sorted(c.co_name for c in derived))
        own = {}
        for code in derived:
            with _line_trace((code,), set()) as lines:
                self.assertEqual(stand_in(1), 6, "the stand-in ran: helper(1) is 3, twice(1) is 2, the sum over (1,) is 1")
            own[code.co_name] = set(lines)
        self.assertEqual(sorted(name for name, lines in own.items() if not lines), [],
                         "every code object of the stand-in ran a line under a trace of it alone (a code object the trace never sees is a "
                         "frame a bump could hide in): none recorded for %r" % sorted(name for name, lines in own.items() if not lines))
        with _line_trace(derived, set()) as together:
            stand_in(1)
        self.assertEqual(together, set().union(*own.values()),
                         "a trace of the derived set records exactly the lines the traces of its members record one at a time (the set is "
                         "the composition of the singletons): together %r, one at a time %r" % (sorted(together), sorted(set().union(*own.values()))))
        outer = own["stand_in"]
        alone = {name: lines - outer for name, lines in own.items() if not name.startswith("<")}
        self.assertEqual(sorted(name for name, lines in alone.items() if name != "stand_in" and not lines), [],
                         "each def nested in the stand-in runs a line the stand-in's own frame never runs (the lines the singleton lost): "
                         "none for %r" % sorted(name for name, lines in alone.items() if name != "stand_in" and not lines))
        with _line_trace((stand_in.__code__,), set()) as control:
            stand_in(1)
        self.assertEqual(control, outer, "the control, the singleton the trace read until the round-7 fixes, records the stand-in's own "
                                         "lines alone: %r against %r" % (sorted(control), sorted(outer)))
        self.assertEqual(sorted(control & set().union(*(alone[n] for n in alone if n != "stand_in"))), [],
                         "and none of the lines the nested defs alone run, so a bump on such a line was invisible to it: %r"
                         % sorted(control & set().union(*(alone[n] for n in alone if n != "stand_in"))))

    def test_the_miss_road_a_seeded_store_read_once_fills_and_publishes(self):
        self._seed(SID_C, stamped=False)
        store, _err, _exc = self._drive("miss")
        path_s = str(self._store_path())
        self.assertIn(path_s, jd._SHARED, "the fill published an entry for the path")
        self.assertIs(jd._SHARED[path_s][2], store, "and the object answered is the published one")

    def test_the_hit_road_a_second_read_of_a_filled_store_moves_hit_alone(self):
        self._seed(SID_C, stamped=False)
        first = jd.load_goals_shared(SID_C)               # the prime: the fill, a miss, before the drive's window
        ls0 = jd.goal_io_stats()["loads_shared"]
        store, _err, _exc = self._drive("hit")
        self.assertIs(store, first, "the hit answers the published object, one object for every reader of it")
        self.assertEqual(jd.goal_io_stats()["loads_shared"] - ls0, 1, "and loads_shared moved once: a store read the cache answered")

    def test_the_compare_miss_road_the_same_identity_over_other_bytes(self):
        self._seed(SID_C, stamped=False)
        p = self._store_path()
        first = jd.load_goals_shared(SID_C)               # the prime fill
        st = os.stat(p)
        old = p.read_bytes()
        new = old.replace(b'"seq": 1', b'"seq": 2')
        self.assertEqual(len(new), len(old), "the rewrite keeps the length, so the size stands")
        self.assertNotEqual(new, old, "and changes the bytes")
        with open(p, "r+b") as fh:
            fh.write(new)
        os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))   # the mtime put back: the identity (ino, mtime_ns, size) stands
        st2 = os.stat(p)
        self.assertEqual((st2.st_ino, st2.st_mtime_ns, st2.st_size), (st.st_ino, st.st_mtime_ns, st.st_size), "the identity stands")
        self.assertEqual(p.read_bytes(), new, "over the new bytes")
        store, _err, _exc = self._drive("compare_miss")
        self.assertIsNot(store, first, "the compare miss refilled: a new object")
        self.assertEqual(store.get("seq"), 2, "parsed from the new bytes")

    def test_the_absent_road_no_store_file_hands_the_read_to_load_goals(self):
        self.assertFalse(self._store_path().exists(), "no store for SID_C: setUp seeds SID_A and SID_B alone")
        store, _err, _exc = self._drive("absent")
        self.assertEqual((store.get("rompUuid"), store.get("nodes")), (SID_C, {}), "load_goals' fresh store, private, nothing to share")
        self.assertNotIn(str(self._store_path()), jd._SHARED, "and nothing cached for the path")

    def test_the_fallback_road_the_cache_off_hands_the_read_to_load_goals(self):
        jd._SHARED_OFF[0] = True                          # setUp's cleanup lifts the switch (jd._shared_clear) and puts the saved value back
        store, _err, _exc = self._drive("fallback")
        self.assertEqual((store.get("rompUuid"), store.get("nodes")), (SID_C, {}), "load_goals' fresh store: no store file under SID_C")
        self.assertNotIn(str(self._store_path()), jd._SHARED, "and nothing cached")

    def test_the_corrupt_road_bytes_that_do_not_parse_bump_miss_once_corrupt_once_and_hand_off_once(self):
        path = self._store_path()
        path.write_text("{not json")
        store, err, _exc = self._drive("corrupt")
        self.assertEqual((store.get("rompUuid"), store.get("nodes")), (SID_C, {}),
                         "the fresh store came back: the bytes were moved aside and nothing was cached for the path")
        self.assertFalse(path.exists(), "the unparseable file was moved aside, so the path reads as absent now")
        aside = [p.name for p in jd.GOALDIR.iterdir() if p.name.startswith(SID_C + ".json.corrupt-")]
        self.assertEqual(len(aside), 1, "one sidecar holds the bytes: %r" % aside)
        self.assertIn("could not be parsed", err, "the quarantine's one stderr line, captured: %r" % err)
        rows = [json.loads(ln) for ln in jd.ERRORS.read_text().splitlines()]
        self.assertEqual([(r["err"], r["fsid"]) for r in rows], [("store-quarantined", SID_C)],
                         "and its one store-quarantined row under the rebound judge-errors file: %r" % rows)

    def test_the_unreadable_journal_road_a_symlink_loop_at_the_journal_path(self):
        self._seed(SID_C, stamped=False)
        jdir = jd._overrides_dir()
        jdir.mkdir(parents=True, exist_ok=True)
        jp = jdir / (SID_C + ".jsonl")
        os.symlink(str(jp), str(jp))                      # a journal that exists and cannot be read: every open of it raises ELOOP
        self.addCleanup(os.unlink, str(jp))
        self.assertIsInstance(jd._journal_key(SID_C), jd._StatFailed, "the journal key before the read is a _StatFailed: the stat fails on the loop")
        with self.assertRaises(OSError) as cm:
            jd._journal_read(SID_C)
        self.assertEqual((cm.exception.errno, isinstance(cm.exception, FileNotFoundError)), (errno.ELOOP, False),
                         "and _journal_read's open raises ELOOP, an OSError that is not FileNotFoundError, so the door's OSError arm takes it")
        store, _err, _exc = self._drive("unreadable_journal")
        self.assertIn(SID_C + ":g1", store.get("nodes", {}), "the seeded store came back through load_goals")
        self.assertNotIn(str(self._store_path()), jd._SHARED, "and nothing was cached: an unreadable journal is not memoized")
        self.assertFalse(store.get("_unread"), "load_goals' own replay saw is_file() false on the loop and marked nothing")
        rows = [json.loads(ln) for ln in jd.ERRORS.read_text().splitlines()] if jd.ERRORS.exists() else []
        self.assertEqual([r["err"] for r in rows], [], "so no history-unreadable row was written either (stated, not relied on): %r" % rows)

    def test_the_unread_road_a_store_file_carrying_the_unread_mark_bumps_the_second_site_with_no_hand_off(self):
        """The door's `if store.get("_unread")` arm, the second unreadable_journal site: the store FILE carries a top-level `_unread`
        key. The writer never serializes the key (save_goals pops it, the transient mark of a replay whose journal did not read), so
        the door's own comment calls the arm unreachable while the journal's rows arrive as lines; that is true of the replay's mark,
        and the arm is reachable with no code change through the file's own content, a hand-written or foreign file: _disk_parse
        answers the file's dict, _guard_nodes wraps its nodes and returns it, _finish_load replays the lines it was handed (a replay
        given lines never touches the key) and stamps _baseRev, and the arm takes the key. The road: {'miss': 1}, {'unreadable_journal':
        1}, no hand-off (the arm returns the store itself, not load_goals' answer), the marked store answered and nothing published,
        the invariant the arm is kept for. Until the round-7 fixes this site was the one row of UNDRIVEN_SITES, on the comment's
        ground, and a bump planted on the arm in a form the roster pin's clauses do not read (a helper defined inside the door, bumping
        through an alias of the counters) was witnessed by nothing."""
        self._seed(SID_C, stamped=False)
        p = self._store_path()
        data = json.loads(p.read_text())
        data["_unread"] = "journal"
        p.write_text(json.dumps(data))
        store, _err, _exc = self._drive("unread")
        self.assertIn(SID_C + ":g1", store.get("nodes", {}), "the seeded store came back through the door itself (no hand-off: _drive read 0)")
        self.assertEqual(store.get("_unread"), "journal", "carrying the file's mark: the parse, the node guard and the replay left it")
        self.assertNotIn(str(p), jd._SHARED, "and nothing was published: a marked store is never shared")
        rows = [json.loads(ln) for ln in jd.ERRORS.read_text().splitlines()] if jd.ERRORS.exists() else []
        self.assertEqual(rows, [], "and no judge-errors row was written: the mark came from the file, not from a journal that failed to "
                                   "read (stated, not relied on): %r" % rows)

    def test_the_dup_road_a_concurrent_fill_published_this_version_first(self):
        self._seed(SID_C, stamped=False)
        path_s = str(self._store_path())
        first = jd.load_goals_shared(SID_C)               # the prime fill
        with jd._SHARED_LOCK:
            ent = jd._SHARED.pop(path_s)
        self.assertIs(ent[2], first, "the prime published the object it answered")
        real = jd._freeze_store

        @functools.wraps(real)
        def republish(store, fsid=None):
            frozen = real(store, fsid)
            with jd._SHARED_LOCK:
                jd._SHARED[path_s] = ent                  # what a concurrent fill does at its publish, between the door's two archive-key reads
            return frozen
        jd._freeze_store = republish                      # CASE_JD: the cleanup restores the real one
        store, _err, _exc = self._drive("dup")
        self.assertIs(store, ent[2], "the dup answers the entry published first: one object for every reader of it")

    def test_the_refuse_road_the_archive_moved_under_the_replay(self):
        self._seed(SID_C, stamped=False)
        path_s = str(self._store_path())
        jd.GOALARCHDIR.mkdir(parents=True, exist_ok=True)
        arch = jd.GOALARCHDIR / (SID_C + ".json")
        self.assertIsNone(jd._archive_key(SID_C), "no archive before the call: the door's first archive-key read answers None")
        real = jd._freeze_store

        @functools.wraps(real)
        def archive_write(store, fsid=None):
            frozen = real(store, fsid)
            arch.write_text(json.dumps({"rompUuid": SID_C, "nodes": {}}))   # a real archive write between the door's two archive-key reads
            return frozen
        jd._freeze_store = archive_write                  # CASE_JD: the cleanup restores the real one
        store, _err, _exc = self._drive("refuse")
        self.assertEqual(store.get("rompUuid"), SID_C, "the caller gets its store")
        self.assertNotIn(path_s, jd._SHARED, "and nothing was published: right for this caller, unproven for the next")
        jd._freeze_store = real
        s0 = jd.shared_store_stats()
        again = jd.load_goals_shared(SID_C)
        s1 = jd.shared_store_stats()
        self.assertEqual({k: s1[k] - s0[k] for k in SHARED_CALL_KEYS + SHARED_SECOND_KEYS if s1[k] != s0[k]}, {"miss": 1},
                         "a following call is a miss that fills: the archive key now stands on both reads")
        self.assertIs(jd._SHARED.get(path_s, (None, None, None))[2], again, "and publishes")

    def test_the_open_raises_road_a_symlink_loop_at_the_store_path_moves_no_key(self):
        path = self._store_path()
        os.symlink(str(path), str(path))
        self.addCleanup(os.unlink, str(path))
        _store, _err, exc = self._drive("open_raises")
        self.assertEqual((exc.errno, isinstance(exc, FileNotFoundError)), (errno.ELOOP, False),
                         "the open raised ELOOP, an OSError that is not FileNotFoundError, and the door re-raised it: %r" % exc)
        self.assertNotIn(str(path), jd._SHARED, "nothing cached for the path")

    def test_the_read_raises_road_a_directory_at_the_store_path_moves_no_key(self):
        path = self._store_path()
        path.mkdir()                                      # the open succeeds on a directory and the read raises
        _store, _err, exc = self._drive("read_raises")
        self.assertIsInstance(exc, IsADirectoryError, "the read raised EISDIR and the door re-raised it: %r" % exc)
        self.assertNotIn(str(path), jd._SHARED, "nothing cached for the path")

    def test_the_fill_raises_road_a_malformed_journal_row_raises_out_of_the_replay_after_the_miss_bump(self):
        """The fill's own raise road (a verifier of the round-5 fixes found it neither driven nor named): a journal row whose instant
        is not a number raises out of _replay_overrides and _finish_load after the miss bump and the loads_shared bump, with no
        second key, no hand-off and nothing cached, the ValueError propagated as the door's comment on that line says (a malformed
        row raises, as in load_goals). A second-key bump planted in a handler around _finish_load was witnessed by nothing before
        this drive; it reds here at the second keys' line and at the raise, since the handler returns instead."""
        self._seed(SID_C, stamped=False)
        jdir = jd._overrides_dir()
        jdir.mkdir(parents=True, exist_ok=True)
        (jdir / (SID_C + ".jsonl")).write_text(json.dumps({"op": "block", "node": SID_C + ":g1", "t": "abc"}) + "\n")   # int("abc") raises in the replay
        ls0 = jd.goal_io_stats()["loads_shared"]
        _store, _err, exc = self._drive("fill_raises")
        self.assertIn("invalid literal for int()", str(exc), "the replay's int() of the row's instant raised, out of _finish_load and the door: %r" % exc)
        self.assertEqual(jd.goal_io_stats()["loads_shared"] - ls0, 1, "loads_shared moved once before the tail raised: the fill had passed the "
                                                                    "journal read, the parse and the guard, and the miss bump before them")
        self.assertNotIn(str(self._store_path()), jd._SHARED, "nothing cached for the path: the fill never reached its publish")
        with self.assertRaises(ValueError):               # the same row raises out of load_goals: the road is the loaders' shared tail's
            jd.load_goals(SID_C)


class TheRecorderNamesTheAsker(unittest.TestCase):
    """_caller's rule over a stand-in. Derives: nothing. Bounds: a contract case over one stand-in wrapper with two body lines and a
    boundary of its own, so it holds the rule, a boundary frame stepped over only at its hand-off line, and not the composition of
    the real boundary set, which setUp's guard holds."""

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
    """setUp's agreement check over throwaway harness subclasses. Derives: nothing. Bounds: contract cases, each placing one stub
    through a hook on a named seam (a CASE_KM name right after the rebind; a judge name outside every list between the first
    snapshot and the rebind) and expecting setUp's refusal by name; the regions probed are the two the check once missed, not every
    point of setUp."""

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
        statements (a bump nested under an If in a later statement counts) and ends in a Return or a Raise; the clean door has a
        cleanup call between a bump and its return, so the predicate is the list's last statement and not the bump's next. Two
        constructs let a path leave such a list and bump again with every list reading clean, and each is refused by name: no bump
        of either roster sits anywhere under a finally clause, since a finalbody runs after its try's body or a handler returned (a
        verifier of the round-4 fixes planted a second-key bump in a finally beside the corrupt handler, which the execution case
        alone caught, and beside the unreadable_journal handler, a road no case drives, which nothing caught); and a second-key
        list that ends in a Raise sits under no try statement of the door, since a handler above could catch the raise and go on
        to bump (the clean door's second-key lists all end in a Return, and its one finally closes a descriptor). Before either,
        every second-key bump is a statement of some list, an Expr of the call or the AugAssign itself, so a bump written as an
        assignment's value, a with item or a lambda body reds the count of lists against bumps (a verifier of the round-5 fixes: the
        early-warning sentences named four refused forms while this clause refuses a fifth). The clauses
        refuse the forms they name and are silent on the rest: a helper defined inside the door, outside the second-key list that
        calls it (its body reads as a clean list of its own; one defined inside that list is refused by the deep count), a second-key
        list ending in a Return whose expression raises into a handler that bumps, an exception from any other statement of a clean
        list caught by a bumping handler, a second-key raise list under a contextlib.suppress with statement (the raising clause reads
        try statements alone, so it does not see one; a suppress around a second bump inside a second-key list is refused by the deep
        count), and any
        construct nobody listed (review round 5, correctness-1, regression-1 and extra6-1, after this docstring said that with the
        two constructs above refused no path the door's own body shows bumps two second keys: the first three, each planted on the
        corrupt road, bumped two with every clause green). So the clauses are an early warning, and the contract, at most one second
        key per call, is carried by execution in TheDoorBumpsAtMostOneSecondKeyPerCall over one road per key of both rosters, a
        second road for the unreadable_journal key's second site, and three raise roads on the real door, where each of those
        constructs is caught on the road it sits on when a drive reaches that road (every bump site of the door is on a driven road
        since the round-7 fixes; the witness's docstring names the arrangement's limit). What the clauses do not read: a callee's body; which
        drive witnesses a bump there is derived by planting one in each callee (review round 5, extra6-2: this sentence named the
        corrupt road alone, on which two of the three callees it listed never run). A bump in _shared_forget is witnessed by the
        absent, unreadable_journal and corrupt drives, by the open_raises and read_raises drives, and by _pass's per-pass lines on the
        no-store sweep case; one in _guard_nodes or _finish_load by the miss, compare_miss, dup and refuse drives, by the
        unreadable_journal drive (load_goals runs the same tail on that hand-off), by the fill_raises drive (the bump runs before the
        replay raises; the corrupt drive's load_goals answers a fresh store after the quarantine and runs neither), and by _pass's
        reconciliation on fill passes; one in _freeze_store by the miss, compare_miss, dup and refuse drives and by _pass on fill
        passes; one in _journal_read by every drive that enters the fill road, fill_raises among them, and one in _disk_parse by
        those but unreadable_journal, whose journal read raises before the parse (the unread drive enters the fill road and runs every
        callee but _freeze_store, before which its arm returns, so it witnesses a bump in each of the five others); one on the door's
        own _unread arm by the unread drive alone, and not by _pass. From the same lists the fill road's entry keys are derived: the call keys whose list does
        not end in a Return or a Raise fall through into the fill, and they must be SHARED_FILL_KEYS, which _pass sums as the bound's
        right-hand side, so a call key that starts falling through, or one of these that stops, reds here rather than leaving _pass
        summing the wrong keys. From the same lists the hand-off keys are derived: the direct bump keys of every list whose last
        statement returns a call of load_goals (_door_hands_off) must be SHARED_HANDOFF_KEYS, which _pass counts as loads in the writer
        reconciliation and leaves out of its dup and refuse zero line (review round 7, the plan's hunt for a seventh hand-written axis:
        the tuple was pinned by nothing while its three siblings were pinned here, and dup added to it or corrupt removed from it left the
        module green). Review round 4, tests-2, regression-2 and extra4-1: the pin read the rosters and the order, the
        at-most-one was held by reading the body, and a second second-key bump on one road or a new fill key left the module green
        with the bound no longer following from the body. Added in the consolidation pass beside ruling 1's bound, the fixer's addition
        beyond the ruling's letter. Derives: the door's bumps as (line, key), its statement lists and its try regions from the door's
        AST (_door_regions); the bump keys against both rosters both ways; the order, every second-key bump below every call-key bump;
        per statement list holding a second-key bump, one such bump over its subtrees and a Return or a Raise last; the count of such
        lists against the second-key bumps; the fill road's entry keys against SHARED_FILL_KEYS both ways; the hand-off keys, the direct
        bump keys of every list whose last statement returns a call of load_goals, against SHARED_HANDOFF_KEYS both ways; the bumps
        under a finalbody and the second-key raise lists under a try, none of either. Bounds: the forms these clauses refuse are the
        ones named here and no others, silent on the rest (the early warning); a callee's body, outside the door's AST; and the
        hand-off predicate's one form, a Return of a Call of the Name load_goals last in the list, so a hand-off written through a
        temporary or an alias of the loader reads here as none and reds the equality naming its key, and with the tuple edited to match
        it reds the door witness's hand-off column for that road, read from the writer door's counter by execution against the same
        lists (both by execution on the tree of the round-7 hand-off fix)."""
        door = jd.load_goals_shared
        self.assertEqual((door.__code__.co_name, os.path.basename(os.path.realpath(door.__code__.co_filename))), ("load_goals_shared", JUDGE_FILE),
                         "the door read here is the judge's own (a harness case's recorder is gone by its cleanup)")
        tree = ast.parse(textwrap.dedent(inspect.getsource(door)))
        # the three reads of the tree are module-level defs since the round-5 fixes (_door_bump_key, _door_stmt_key, _door_regions), so
        # the witness by execution drives this pin's reading of the door over a planted stranger too (TheWalkersRefuseAStrangerByExecution);
        # the reads below over the subtrees they hold stay inline, behind the whole-tree walk _door_regions makes first
        bumps, blocks, tries = _door_regions(tree)
        self.assertEqual({k for _ln, k in bumps}, set(SHARED_CALL_KEYS) | set(SHARED_SECOND_KEYS),
                         "the keys load_goals_shared bumps are exactly the call keys the shared reconciliation sums and the second keys the "
                         "second-bump bound sums (a key here and in neither roster is a bump no reconciliation reads; a key in a roster and "
                         "not here is a bound over a counter the door no longer moves): %r" % sorted(bumps))
        self.assertLess(max(ln for ln, k in bumps if k in SHARED_CALL_KEYS), min(ln for ln, k in bumps if k in SHARED_SECOND_KEYS),
                        "every second-key bump sits below every call-key bump in the door's body (the fill road follows the miss or "
                        "compare_miss bump), the structure the bound in _pass rests on; the bumps by line: %r" % sorted(bumps))
        # the at-most-one, over every statement list of the door (`blocks`: each list-valued field whose members are all statements, a
        # body, an orelse, a finalbody, a handler's body; Try.handlers holds ExceptHandler nodes, so no try region is collected twice)
        holding, fill_entries, handoff_keys = 0, set(), set()
        for blk in blocks:
            direct = [k for k in (_door_stmt_key(s) for s in blk) if k is not None]
            if _door_hands_off(blk):
                handoff_keys.update(direct)
            if any(k in SHARED_SECOND_KEYS for k in direct):
                holding += 1
                deep = [(x.lineno, _door_bump_key(x)) for s in blk for x in _walk(s) if _door_bump_key(x) is not None]
                second = [(ln, k) for ln, k in deep if k in SHARED_SECOND_KEYS]
                self.assertEqual(len(second), 1,
                                 "the statement list holding the second-key bump at line %d holds exactly one second-key bump over the full "
                                 "subtrees of its statements, the form this clause refuses (a helper defined inside the door, a return whose "
                                 "expression raises into a bumping handler, or an exception from another statement caught by one can still bump "
                                 "twice on a path through it; the door witness holds the at-most-one by execution): %r"
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
        self.assertEqual(handoff_keys, set(SHARED_HANDOFF_KEYS),
                         "the hand-off keys, the direct bump keys of every statement list of the door whose last statement returns a call of "
                         "load_goals, are SHARED_HANDOFF_KEYS, the keys _pass counts as loads in the writer reconciliation and leaves out of "
                         "its dup and refuse zero line: hands off with no place in the tuple %r (a load the reconciliation would not expect); "
                         "in the tuple with no list handing off %r (a bump counted as a load that never comes, and a second key the zero line "
                         "stops reading); derived %r against %r (a hand-off written through a temporary or an alias of the loader reads here "
                         "as none: write it as `return load_goals(fsid)`, or widen _door_hands_off with its reason)"
                         % (sorted(handoff_keys - set(SHARED_HANDOFF_KEYS)), sorted(set(SHARED_HANDOFF_KEYS) - handoff_keys),
                            sorted(handoff_keys), sorted(SHARED_HANDOFF_KEYS)))
        # the two constructs that leave a clean list and bump again (a verifier of the round-4 fixes): a finalbody runs after its try's
        # body or a handler returned, so a bump under one adds to theirs on the same path; a Raise ending a second-key list can be
        # caught by a handler above, which goes on. A try statement is the one node class with a finalbody field, so the try regions
        # are the subtrees of those nodes (`tries`)
        in_finally = sorted((x.lineno, _door_bump_key(x)) for node in tries for st in node.finalbody for x in _walk(st) if _door_bump_key(x) is not None)
        self.assertEqual(in_finally, [], "no bump of a call key or a second key sits under a finally clause of the door: a finalbody runs after its "
                                         "try's body or a handler returned, so a bump there adds to the one the returning list made on the same "
                                         "path with every statement list reading clean on its own (two second keys on one call, or a second call "
                                         "key, with the at-most-one clause green); the clean door's one finally closes a descriptor and bumps "
                                         "nothing; bumps under a finalbody by line: %r" % in_finally)
        under_try = {id(x) for node in tries for x in _walk(node)}
        raising = sorted((blk[-1].lineno, [k for k in (_door_stmt_key(st) for st in blk) if k in SHARED_SECOND_KEYS]) for blk in blocks
                         if isinstance(blk[-1], ast.Raise) and any(_door_stmt_key(st) in SHARED_SECOND_KEYS for st in blk) and id(blk[-1]) in under_try)
        self.assertEqual(raising, [], "a statement list holding a second-key bump and ending in a Raise sits under no try statement of the door: a "
                                      "handler above could catch the raise and go on to bump again on the same path, with every list reading "
                                      "clean on its own; the clean door's second-key lists all end in a Return; such lists by the raise's line "
                                      "and their keys: %r" % raising)

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
        would read the wrapper's source and answer no site for a body it never read. Derives: its targets from the lists setUp pins by
        execution, REPLACED_KM less REPLACED_DATA, REPLACED_JD and Sessions.backend_for, and each object's identity before its source
        is read. Bounds: one level deep, the helper's own source; the count, 21, a tripwire; and the needle, both doors by substring.
        REPLACED_DATA is no bound of this census since the round-7 close: setUp holds it against the non-callable names of
        REPLACED_KM both ways, so a callable put on it reds there by name (before that pin it moved this count alone, and with the
        count edited its real body went unscanned) and a data name left off it errors in the identity check here."""
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
        outer wrappers'. The limit that stays: a name completed at run time from constants that spell no door whole (with an ASCII
        bytes literal decoded, surrounding whitespace stripped and str.lower applied; another codec, a strip of other characters and
        another case fold are not undone) and either carry the name in one piece to no listed lookup, dict read or subscript key or
        reach one in a text those three transforms do not restore is spelled as a door in no constant the pin reads (the `assembled`
        class of _LIMITS, which the enumeration holds on that side). Review round 4,
        correctness-1, tests-1 and extra6-1: the string class was stated closed by a list of receivers, nine lookups, four dict
        reads and a subscript slice, and six working doors on no list passed the pin with a real load in a replaced helper's body;
        the pin keys on the door's spelling now, the closed set, and the receivers need no listing. Derives: the births, the called
        spellings, the defs and the hand-offs over the kernel's and the judge's whole files (_loader_births), and the door names' one
        copy, _DOOR_SPELLINGS, held both ways against the judge's defs and against the spellings the kernel calls (until the round-7
        fixes the four names were spelled by hand three times, in the constant, in this case's defs line and in the enumeration's stub
        judge, copies pinned to each other by nothing, so a fifth spelling added to the constant left the module green; the defs line
        reads the constant and the stub judge is built from it since). Bounds: the kernel's call sites per spelling, 27, 9, 7 and 15,
        a tripwire on the population read whose keys spell the doors with the kernel's base and whose key set the kernel-side line
        holds against the constant, so an upstream fold that moves one reds here by design; and the two hand-offs, the judge's two
        outer wrappers, a pinned pair that also holds the recorder's hand-picked boundary set against the judge's AST."""
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
        kernel_doors = {k[len("jd."):] for k in called}
        self.assertEqual(kernel_doors, set(_DOOR_SPELLINGS),
                         "%s: the doors the kernel calls are the names of _DOOR_SPELLINGS, the one copy of the four spellings (the defs line "
                         "below holds the same constant against the judge's defs, so the constant, the kernel's calls and the judge's defs "
                         "agree or one of the two lines reds). Spelled in the constant and never called %r; called and not spelled %r"
                         % (KERNEL_FILE, sorted(set(_DOOR_SPELLINGS) - kernel_doors), sorted(kernel_doors - set(_DOOR_SPELLINGS))))
        self.assertEqual((defs, handoffs), ({}, []), "%s: the kernel defines no loader and hands none to _or_fault" % KERNEL_FILE)
        born, called, defs, handoffs = _loader_births(Path(os.path.realpath(jd.__file__)), judge=True)
        self.assertEqual(born, [], "%s: the judge reaches its own doors by bare name as the callee of a call, or hands one to _or_fault from a "
                                   "boundary wrapper, and gives them no other name (no alias, parameter, keyword, attribute or decorator; no string "
                                   "constant spells one whole, wherever it appears and whatever receives it, and none containing the name reaches "
                                   "a dynamic lookup, a dict read or a subscript key): %s"
                                   % (JUDGE_FILE, "; ".join("line %d, %s" % b for b in born)))
        self.assertEqual(defs, dict.fromkeys(_DOOR_SPELLINGS, 1),
                         "%s: every door of _DOOR_SPELLINGS is defined once and no other def is named like a loader (a fifth def is a new "
                         "door, which needs a recorder or a bound and its spelling in the constant; a spelling in the constant with no def is "
                         "a name the value rule refuses for no door). Defined %r; spelled in the constant and not defined %r; defined and not "
                         "spelled %r" % (JUDGE_FILE, defs, sorted(set(_DOOR_SPELLINGS) - set(defs)), sorted(set(defs) - set(_DOOR_SPELLINGS))))
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
                         "a subscript key, each read with an ASCII bytes literal decoded, surrounding whitespace stripped and str.lower applied; a "
                         "name completed at run time from constants that spell no door whole and either carry it in one piece to none of those "
                         "receivers or reach one in a text those three transforms do not restore is outside "
                         "that pin as well (the consolidation pass and the round-4 fixes; the enumeration holds both classes on their sides): %r"
                         % _loader_sites(via_getattr, "load_goals"))


# The census's form enumeration (the consolidation pass). One sample module per form, written to a file and imported so inspect can read
# it, with a stub judge standing in for the real one (one def per name of _DOOR_SPELLINGS, each taking any argument and returning
# it, so a decorator form's def-time call is harmless and no store is touched; the samples are otherwise never called). Each row of _LOADER_FORMS: the
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
# concatenation that keeps the needle in one piece); a verifier of the round-4 fixes added seven (F68 to F71, on the string side: a
# cased, a padded and a bytes constant the pin's three normalisations read as the name, at a listed lookup, bound first or as a
# subscript key; F72 to F74, on the assembled side: a needle-keeping concatenation handed to two unlisted callables and a reversed
# literal, transforms the pin does not undo). The bodies' `romp_judge` is the stub's name when loaded. For a form of the string or
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
              "f-string of the whole name, an ASCII bytes literal decoded, a whitespace-padded constant stripped, an upper-cased one "
              "lowered, or any receiver "
              "nobody listed): the limit _loader_sites states, refused by the kernel-wide pin, _loader_births: a constant spelling a door "
              "whole wherever it appears and whatever receives it, and a constant containing the name where it reaches a listed lookup, a "
              "dict read or a subscript key, each read through _door_text (an ASCII bytes literal decoded, surrounding whitespace stripped, "
              "str.lower); the enumeration runs that "
              "pin over each form of this class and expects a birth",
    "assembled": "a loader reached through a name completed at run time from constants that spell no door whole, after the three "
                 "transforms the pin undoes (an ASCII bytes decode, a whitespace strip, str.lower; a decode in another codec, a chars-strip "
                 "and any other case fold are not undone and are of this class), and either carry the name in one piece to no listed "
                 "lookup, dict read or subscript key or reach one in a text the three transforms do not restore (a concatenation or a "
                 "format that splits the needle, an f-string interpolating a piece, a needle-keeping concatenation handed to an unlisted "
                 "callable, a reversed literal, a bytes literal in another codec at getattr, a chars-strip at an unlisted receiver, any "
                 "other transform undone at run time): spelled as a door in no node and in no constant either census reads, so outside "
                 "every static pin in this module, the kernel-wide pin included; the enumeration runs that pin over each form of this "
                 "class and expects no birth, so the class is held on the side it falls, and the class is stated by the pin's boundary "
                 "rather than by its examples (the rows hold the split, the interpolation, the unlisted receiver, the reversal, the "
                 "codec, the chars-strip at an unlisted receiver and the fold; the last three reached real loads in kernel plants too, "
                 "which the round-5 paragraph records)",
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
    # The three transforms the pin undoes, an ASCII bytes decode, a whitespace strip and str.lower (a verifier of the round-4 fixes: each
    # reached a real load with the module green while the prose named the split alone as the residue), on the string side, and six
    # completions it does not undo, on the assembled side (F72 to F74 by that verifier; F75 to F77, the codec, the chars-strip at an
    # unlisted receiver and the fold, by the round-5 consolidation after tests-3, regression-3 and extra4-1).
    ('F68', 'getattr with an upper-cased constant lowered at run time (the pin applies str.lower to the text it reads)',
     "def f(sid):\n    return getattr(jd, 'LOAD_GOALS_SHARED'.lower())(sid)\n", 'f', None, [], 0, 'string'),
    ('F69', 'getattr with a padded constant stripped at run time and bound to a variable first (the pin strips surrounding whitespace from the text it reads)',
     "def f(sid):\n    n = ' load_goals_shared '.strip()\n    return getattr(jd, n)(sid)\n", 'f', None, [], 0, 'string'),
    ('F70', 'getattr with an ASCII bytes literal decoded at run time (the pin reads a bytes constant decoded as ASCII)',
     "def f(sid):\n    return getattr(jd, b'load_goals_shared'.decode())(sid)\n", 'f', None, [], 0, 'string'),
    ('F71', 'an ASCII bytes literal decoded as a subscript key',
     "def f(sid):\n    return vars(jd)[b'load_goals_shared'.decode()](sid)\n", 'f', None, [], 0, 'string'),
    ('F72', 'functools.partial(getattr, jd) handed a concatenation that keeps the needle in one piece (an unlisted receiver: neither clause reaches it)',
     "def f(sid):\n    return functools.partial(getattr, jd)('load_goals_' + 'shared')(sid)\n", 'f', None, [], 0, 'assembled'),
    ('F73', 'operator.methodcaller handed a concatenation that keeps the needle in one piece',
     "def f(sid):\n    return operator.methodcaller('load_goals_' + 'shared', sid)(jd)\n", 'f', None, [], 0, 'assembled'),
    ('F74', 'getattr with a reversed literal (a transform the pin does not undo)',
     "def f(sid):\n    return getattr(jd, 'derahs_slaog_daol'[::-1])(sid)\n", 'f', None, [], 0, 'assembled'),
    # The three completions the round-5 recaps name as not undone (review round 5, tests-3, regression-3 and extra4-1: the recaps had
    # named the families, a decode, a strip, a lower, where _door_text undoes one member of each), each held on the assembled side: the
    # pin reads the constant and lets it pass and the enumeration expects no birth, so a widening of _door_text to any of the three
    # reds its row here (the codec form's bytes are the name encoded as utf-16, spelled as escapes so this module's text stays ASCII).
    ('F75', 'getattr with a bytes literal in a codec other than ASCII decoded at run time (utf-16: the pin reads bytes as ASCII, so the constant reads as no door and reaches the listed lookup undecoded)',
     "def f(sid):\n    return getattr(jd, b'\\xff\\xfel\\x00o\\x00a\\x00d\\x00_\\x00g\\x00o\\x00a\\x00l\\x00s\\x00_\\x00s\\x00h\\x00a\\x00r\\x00e\\x00d\\x00'.decode('utf-16'))(sid)\n",
     'f', None, [], 0, 'assembled'),
    ('F76', 'functools.partial(getattr, jd) handed a padded constant with its padding characters stripped at run time (a chars-strip, not undone, at an unlisted receiver; at getattr itself the constant contains the name and the consumer clause reads it)',
     "def f(sid):\n    return functools.partial(getattr, jd)('xxload_goals_sharedxx'.strip('x'))(sid)\n", 'f', None, [], 0, 'assembled'),
    ('F77', 'getattr with a constant casefold folds to the name and str.lower leaves as it is (a long s for each s, so the text str.lower leaves contains no door spelling either; a case fold the pin does not undo)',
     "def f(sid):\n    return getattr(jd, 'load_goal\\u017f_\\u017fhared'.casefold())(sid)\n", 'f', None, [], 0, 'assembled'),
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
    the input it lets pass over the forms the rows list; the two limit texts are messages no assertion reads, so an overstatement in
    them beyond the listed forms is not caught here (a verifier of the consolidation pass found the module's text saying the pin
    closed the string limit while vars(jd)[...] and jd.__dict__[...] passed it; review round 5 found the recaps naming families where
    _door_text undoes one member; a verifier of the round-5 fixes rewrote the assembled limit text to a false universal with every
    case green, which is why this sentence no longer says the texts cannot overstate). Derives: each row's answer by execution of
    the census on the running interpreter, the gated rows' SyntaxError below their version, and the kernel-wide pin's verdict over
    every string and assembled row's file. Bounds: the rows of _LOADER_FORMS, _BUMP_FORMS and _HANDOFF_FORMS, the lens's
    enumeration, a sample of Python's forms and not a population (no module can enumerate the language's forms, so a form nobody
    listed is held by nothing here); the five classes of _LIMITS and each row's class, a classification by hand; and the counts
    pinned, 122, 20 and 7 rows and the missed forms by class, tripwires that make an edit to a table carry a reason."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        stub = self._module(_STUB_JUDGE, "".join("def %s(fsid=None, *a, **k):\n    return fsid\n\n\n" % n for n in _DOOR_SPELLINGS))
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
        self.assertEqual(len(_LOADER_FORMS), 122, "the table carries the lens's 95 loader forms, a consolidation-pass verifier's four, the "
                                                  "round-3 fixes' three (a t-string interpolation, a type-parameter bound and a type-parameter "
                                                  "default), the round-4 fixes' ten (methodcaller, itemgetter over vars(jd), a partial of "
                                                  "getattr, a match-mapping key, an f-string handed to getattr with and without a piece "
                                                  "interpolated, and four subscript keys: an f-string, a conditional, a walrus and a "
                                                  "concatenation that keeps the needle in one piece) and a round-4 verifier's seven (a cased, a "
                                                  "padded and a bytes constant at a listed lookup or bound first, a bytes subscript key, and three "
                                                  "completions of the name the pin does not undo), and the round-5 consolidation's three (a bytes "
                                                  "literal in another codec at getattr, a chars-strip at an unlisted receiver and a casefold at "
                                                  "getattr, the three completions the round-5 recaps name as not undone)")
        self.assertEqual(len({row[0] for row in _LOADER_FORMS}), 122, "with distinct ids")
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
                                 "listed lookup, a dict read or a subscript key, the text read with an ASCII bytes literal decoded, surrounding whitespace "
                                 "stripped and str.lower applied, and the pin refuses it (a birth); a form of the assembled class spells the name whole in no "
                                 "constant so read and carries none containing it to such a receiver, and the pin lets it pass, the limit stated as "
                                 "%r; births: %s"
                                 % (fid, form, "reports a birth" if born else "reports none", limit,
                                    "; ".join("line %d, %s" % b for b in born) or "none"))
            if limit is None:
                counted += 1
            else:
                limits[limit] = limits.get(limit, 0) + 1
        self.assertEqual(counted + sum(limits.values()) + len(gated), 122, "every row was counted, a limit, or gated: %d, %r, %r" % (counted, limits, gated))
        self.assertEqual(limits, {"string": 26, "assembled": 9, "outside": 9, "wrapper": 2, "none": 5},
                         "the missed forms by limit: the lens's classification with its string class split by what the kernel-wide pin refuses "
                         "(the round-4 fixes moved F07d and F45 into the string class, a constant spelling a door whole being refused wherever "
                         "it appears, and added nine string rows, four for the doors the round found on no list, one for the f-string of the "
                         "whole name handed to getattr and four for the subscript keys the slice walk reaches, and one assembled row for the "
                         "f-string that splits the needle; a verifier of the round-4 fixes added four string rows, the cased, the padded and the "
                         "bytes constants the pin's three normalisations read as the name, and three assembled rows, a needle-keeping "
                         "concatenation at two unlisted receivers and a reversed literal; the round-5 consolidation added three assembled "
                         "rows, a bytes literal in another codec at getattr, a chars-strip at an unlisted receiver and a casefold at getattr)")

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
    compatibility that no parse produces), so a grammar that gains a node form reds here naming the new class; and _walk, the walk
    every census in this module is meant to read through, refuses a node of a class outside _AST_CONCRETE by name. A third case is
    the early warning over this module's own AST: no reference to one of four traversal names sits outside _walk in the three forms
    the finder reads (review round 4, regression-3 and extra7-1: a count of one spelling held it before). It is keyed on names and
    so wrong in both directions, an innocent use of a listed name costing an exemption row and a whole walk under an unlisted name
    (a recursion over ast.iter_fields, node._fields or ast.dump) invisible to it, so it refuses the forms it names and is silent on
    the rest; the contract itself, a stranger node refused by every roster census and never passed over, is carried by execution in
    TheWalkersRefuseAStrangerByExecution over the roster _CENSUSES (review round 5, correctness-2, tests-1, extra5-2 and regression-2)."""

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
        # the next case is the early warning over this module's AST (references to four traversal names outside _walk; a count of one
        # spelling before round 4); that every roster census reads through _walk is held by execution in TheWalkersRefuseAStrangerByExecution

    def test_no_reference_to_a_traversal_name_sits_outside_walk(self):
        """The early warning: no reference to one of four traversal names sits outside _walk in the three forms the finder reads,
        asserted over this module's own AST and not by counting one spelling (review round 4, regression-3 and extra7-1: the
        round-3 guard counted the text of one call spelling once, so a census written as a NodeVisitor subclass, an
        iter_child_nodes recursion, a from-import of the walk, a module alias walking or a getattr with the name in a string walked
        a tree without _walk, met a node the table does not classify, reported no site and left the guard green; a one-spelling
        contract is a list of length one). This case was named for the contract, no tree walk except through _walk, until the
        round-5 fixes; it holds less than that (review round 5, correctness-2, tests-1, extra5-2 and regression-2): the finder pins
        references to four names in three forms and is wrong in both directions, a row bought for the innocent parent-map listing
        in _loader_births and nothing to say about a recursion over ast.iter_fields, node._fields or ast.dump, a whole walk under
        no listed name. It refuses the forms it names and is silent on the rest; the walk contract, a stranger node refused by
        every roster census and never passed over, is carried by execution in TheWalkersRefuseAStrangerByExecution, and a fifth name is
        deliberately not added here (the ruling on approach: a list of syntax does not converge). _traversal_references reads every reference to the four
        traversal names in three forms keyed on the name and not on the road to the module: an attribute named like one on any base
        (the ast module, a name it is imported under or rebound to, importlib.import_module("ast"), __import__("ast"),
        sys.modules["ast"]; a NodeVisitor base is spelled this way too), a from-import of the name from any module at all, with or
        without `as` (a star import from any module counts as every name; review round 5, tests-4: the branch was keyed on the
        module road, `from ast`, so a from-import through a sys.modules alias of the module passed), and getattr on any first
        argument with the name in a string constant anywhere under its second
        argument, a plain string or a no-placeholder f-string (review round 5, extra5-1) (a verifier of the round-4
        fixes: keyed on the names the module was imported under, the attribute and getattr forms let a walk through importlib,
        __import__, sys.modules or a rebound module name pass, the list shape once more). Every reference sits inside _walk but for
        the rows of _WALK_EXEMPT, each with its reason, and every row is used, so a stale exemption reds too; _walk itself holds
        exactly one, the standard walk by attribute. _TRAVERSAL is pinned in both directions: the interpreter pins the spelling, every
        name it holds an attribute of the ast module (review round 5, extra5-3: the names were assembled from halves and the samples
        below were built from the same constants, so a misassembled name matched its own sample and the case stayed green with that
        form guarded by nothing), and the samples pin the membership both ways, the set of names the samples spell, less the star
        row, equal to the roster (review round 6, extra7-1: the samples loop reads each row's expected name off the row, so a sample
        naming a name outside the roster red as no reference while a roster name with no sample was read by nothing, and a fifth
        name this module spells nowhere, added to _TRAVERSAL, left the module green). The three forms are then run over synthetic
        sources spelled literally, with a source of their own and no reference to _TRAVERSAL, one per form and per road to the
        module, the forms covered held equal to the finder's own both ways, so the refused inputs are pinned here and not only by the plants the history paragraphs record, and the stated limit
        is run the same way and answers no reference, so it is held on its side (the finder reads a string constant only as
        getattr's second argument, so a sample spelling a name is no reference of this module's). Outside these forms: a traversal name read
        from the module's namespace by string (vars(ast), ast.__dict__, operator.attrgetter) or assembled at run time, a getattr
        reached under another name (a rebinding, builtins.getattr: the form keys on the bare Name getattr as the callee), and any
        traversal under an unlisted name, a recursion over ast.iter_fields, node._fields or ast.dump, a whole walk this finder never
        sees (the witness's negative control runs two such recursions over a planted tree and asserts this finder answers no
        reference over either); the interpreter check beside this case scans vars(ast) for every node class and reds by name on a
        new one with no walker involved, so the version demand does not rest on this pin alone. Derives: every reference in this
        module's AST in the three forms, from the module's own text; the _WALK_EXEMPT rows both ways (every row used, nothing
        outside them); the roster's names against the interpreter (each an attribute of ast) and against the samples both ways; and
        the finder's forms from its own source, the third element of every tuple it appends to out, and the forms the samples cover,
        each against _FINDER_FORMS both ways (until the round-7 close the samples pinned the roster by name both ways and by form one
        way, so a form whose rows were all removed left its branch of the finder pinned by nothing; the close's first pin held the
        source derivation against the samples alone, and the branch deleted with its rows removed left them agreeing, so the roster
        is the copy that names the loss). Bounds: the four names and the three forms (the ruling's stop and the finder's policy, two
        rosters: a list of syntax does not converge, and a form removed from the finder, the samples and the roster at once is unseen,
        as a name removed from _TRAVERSAL with its samples is); the samples and the limits as the independent source, literal rows the
        module cannot compute without spelling the names they test; and the roads per form, which no derivation counts (a road with
        no sample row is pinned by the plants the history paragraphs record alone)."""
        refs = _traversal_references(ast.parse(Path(os.path.realpath(__file__)).read_text(encoding="utf-8")))
        outside = [r for r in refs if r[4] != "_walk"]
        stray = [r for r in outside if (r[4], r[1]) not in _WALK_EXEMPT]
        self.assertEqual(stray, [], "a reference to an ast traversal name outside _walk and outside _WALK_EXEMPT, by line, name, form, spelling "
                                    "and enclosing def: %s. A census that walks a tree by itself passes a node the table does not classify as no "
                                    "site; read through _walk, or add an exemption row with the reason the reference traverses nothing"
                                    % "; ".join("line %d, %s, the %s form (%s) in %s" % r for r in stray))
        stale = sorted(k for k in _WALK_EXEMPT if not any((r[4], r[1]) == k for r in outside))
        self.assertEqual(stale, [], "an exemption with no reference: %r (the row outlived the code it excused; remove it)" % stale)
        self.assertEqual([(r[1], r[2]) for r in refs if r[4] == "_walk"], [("walk", "attribute")],
                         "_walk holds exactly one traversal reference, the standard walk by attribute: %r" % [r for r in refs if r[4] == "_walk"])
        # the roster is derived against the interpreter, not asserted: a misspelled or renamed name also reds the membership line below
        # the samples (the samples spell the names independently since the round-5 fixes, so it has no row), and this line names the
        # misspelling directly instead of leaving that line to say it (a verifier of the round-5 fixes: this comment said the samples
        # could not catch it)
        self.assertEqual([n for n in _TRAVERSAL if not hasattr(ast, n)], [],
                         "every name in _TRAVERSAL is an attribute of the ast module; these are not: %r (a misspelled or renamed traversal "
                         "name is guarded by nothing, since no source can spell it)" % [n for n in _TRAVERSAL if not hasattr(ast, n)])
        # the refused inputs, one synthetic source per form, per road to the module, and per name for the two the module never
        # spells in code; each row spells its source and its expected tuple as literal text, with no reference to _TRAVERSAL
        samples = (
            ("import ast\nclass _V(ast.NodeVisitor):\n    pass\n", (2, "NodeVisitor", "attribute", "ast.NodeVisitor", "_V")),
            ("import ast\nclass _T(ast.NodeTransformer):\n    def visit(self, n):\n        return n\n",
             (2, "NodeTransformer", "attribute", "ast.NodeTransformer", "_T")),
            ("import ast\ndef kids(n):\n    return list(ast.iter_child_nodes(n))\n", (3, "iter_child_nodes", "attribute", "ast.iter_child_nodes", "kids")),
            ("from ast import walk as _w\ndef census(t):\n    return list(_w(t))\n", (1, "walk", "from-import", "from ast import walk as _w", "<module>")),
            ("from ast import *\n", (1, "*", "from-import", "from ast import *", "<module>")),
            # the from-import keyed on the imported name whatever the road (review round 5, tests-4): an alias of the module in
            # sys.modules, a dotted road, a relative one; ast.unparse and the derived spelling agree on 3.10 through 3.14t
            ("import ast, sys\nsys.modules['myast'] = ast\nfrom myast import walk\n", (3, "walk", "from-import", "from myast import walk", "<module>")),
            ("from pkg.ast import walk\n", (1, "walk", "from-import", "from pkg.ast import walk", "<module>")),
            ("from . import walk\n", (1, "walk", "from-import", "from . import walk", "<module>")),
            # the name-keying's false positive, held as such: a walk that is not the ast module's is a reference too (a row buys it off)
            ("from os import walk\n", (1, "walk", "from-import", "from os import walk", "<module>")),
            ("import ast as _a\ndef census(t):\n    return list(_a.walk(t))\n", (3, "walk", "attribute", "_a.walk", "census")),
            ("import ast\ndef census(t):\n    return list(getattr(ast, 'walk')(t))\n", (3, "walk", "getattr", "getattr(ast, 'walk')", "census")),
            # the getattr key as a no-placeholder f-string, a JoinedStr holding the Constant (review round 5, extra5-1), as a call and
            # as a class base; ast.unparse spells the constant-only f-string f'walk' on 3.10 through 3.14t
            ("import ast\ndef census(t):\n    return list(getattr(ast, f'walk')(t))\n", (3, "walk", "getattr", "getattr(ast, f'walk')", "census")),
            ("import ast\nclass V(getattr(ast, f'NodeVisitor')):\n    pass\n", (2, "NodeVisitor", "getattr", "getattr(ast, f'NodeVisitor')", "V")),
            ("import ast\nclass C:\n    def m(self, t):\n        return list(ast.walk(t))\n", (4, "walk", "attribute", "ast.walk", "C.m")),
            # the four roads to the module a verifier of the round-4 fixes walked with the pin green: each ends in the name
            ("import importlib\ndef census(t):\n    return list(importlib.import_module('ast').walk(t))\n",
             (3, "walk", "attribute", "importlib.import_module('ast').walk", "census")),
            ("def census(t):\n    return list(__import__('ast').walk(t))\n", (2, "walk", "attribute", "__import__('ast').walk", "census")),
            ("import sys\ndef census(t):\n    return list(sys.modules['ast'].walk(t))\n",
             (3, "walk", "attribute", "sys.modules['ast'].walk", "census")),
            ("import ast\n_m = ast\ndef census(t):\n    return list(_m.walk(t))\n", (4, "walk", "attribute", "_m.walk", "census")),
            ("import sys\ndef census(t):\n    return list(getattr(sys.modules['ast'], 'walk')(t))\n",
             (3, "walk", "getattr", "getattr(sys.modules['ast'], 'walk')", "census")),
        )
        # the roster and the samples pin each other both ways (review round 6, extra7-1): the loop below reads each row's expected name
        # off the row, so a sample naming a name outside the roster reds there as no reference, but a roster name no sample spells was
        # read by nothing, and a fifth name this module spells nowhere added to _TRAVERSAL left the module green; the star row is the
        # from-import form's every-name report, not a roster name, so it is set aside (the shape of the door witness's keys == rosters)
        spelled = {expected[1] for _source, expected in samples}
        self.assertEqual(set(_TRAVERSAL), spelled - {"*"},
                         "the names the samples spell are exactly the roster's: a roster name with no sample, %r, is a name this case pins "
                         "by nothing (add its row per form); a sample naming a name outside the roster, %r, is a row the finder cannot "
                         "read as a reference (the loop below reds it)" % (sorted(set(_TRAVERSAL) - spelled), sorted(spelled - {"*"} - set(_TRAVERSAL))))
        # and the samples cover every form the finder reports, both ways (review round 7, the seventh-axis verifier: the names were
        # pinned both ways and the forms one way, so the four getattr rows removed with the finder's getattr branch deleted left the
        # module green). The finder's forms are derived from its own source: the string constant in the third position of every tuple
        # it appends to `out`, read through _walk over its parsed def, so a form added to the finder with no sample row reds here, as
        # does a sample naming a form the finder does not report
        finder = ast.parse(textwrap.dedent(inspect.getsource(_traversal_references)))
        forms = {c.args[0].elts[2].value for c in _walk(finder)
                 if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == "append"
                 and isinstance(c.func.value, ast.Name) and c.func.value.id == "out" and c.args and isinstance(c.args[0], ast.Tuple)
                 and len(c.args[0].elts) > 2 and isinstance(c.args[0].elts[2], ast.Constant)}
        self.assertTrue(forms, "the finder's forms are derived from its source, the third element of every tuple it appends to out, and "
                               "the derivation answered none: the finder's shape changed, so read it again here")
        self.assertEqual(forms, set(_FINDER_FORMS),
                         "the forms the finder reports, derived from its source, are exactly _FINDER_FORMS: a form the roster names and the "
                         "finder does not report, %r, lost its branch (the round-7 close: with the derivation held against the samples "
                         "alone, the getattr branch deleted with its rows removed left the two agreeing on two forms); a form the finder "
                         "reports and the roster does not name, %r, needs its roster entry and its sample rows"
                         % (sorted(set(_FINDER_FORMS) - forms), sorted(forms - set(_FINDER_FORMS))))
        covered = {expected[2] for _source, expected in samples}
        self.assertEqual(covered, set(_FINDER_FORMS),
                         "the forms the samples cover are exactly _FINDER_FORMS: a form with no sample, %r, has its branch of the finder "
                         "pinned by nothing (add a row per road); a sample naming a form outside the roster, %r, is a row the loop below "
                         "reds" % (sorted(set(_FINDER_FORMS) - covered), sorted(covered - set(_FINDER_FORMS))))
        for source, expected in samples:
            got = _traversal_references(ast.parse(source))
            self.assertEqual(got, [expected], "the finder reads %r as one reference, %r, and answers %r" % (source, expected, got))
        # the stated limits, held on their side: a traversal name read from the module's namespace by string, and a getattr reached
        # under another name (a rebinding, builtins.getattr), are no reference here (a verifier of the round-5 fixes planted the rebound
        # name as a real walk at module level with the case green)
        limits = ("import ast\ndef census(t):\n    return list(vars(ast)['walk'](t))\n",
                  "import ast\ndef census(t):\n    return list(ast.__dict__['walk'](t))\n",
                  "import ast, operator\ndef census(t):\n    return list(operator.attrgetter('walk')(ast)(t))\n",
                  "import ast\n_g = getattr\ndef census(t):\n    return list(_g(ast, 'walk')(t))\n",
                  "import ast, builtins\ndef census(t):\n    return list(builtins.getattr(ast, 'walk')(t))\n")
        for source in limits:
            got = _traversal_references(ast.parse(source))
            self.assertEqual(got, [], "the finder reads %r as no reference: a traversal name read from the module's namespace by string, or a "
                                      "getattr reached under another name, is the limit the docstring states, and a change here is a widening "
                                      "the docstring must follow: %r" % (source, got))


class TheWalkersRefuseAStrangerByExecution(unittest.TestCase):
    """The walker contract by execution (review round 5, correctness-2, tests-1, extra5-2 and regression-2, and the reviewer's
    ruling on approach; review round 6, lens one, for the positions). The contract: a node class the grammar table does not
    classify is REFUSED by every roster census of this module, never passed over as no site ("every" bounded by the roster
    _CENSUSES, its floor and the floor's stated boundary, below). The finder beside this class (_traversal_references, the case in
    TheGrammarIsTheOneTheWalkersClassify) keys on four traversal NAMES and so is wrong in both directions: an innocent use of a
    listed name costs a _WALK_EXEMPT row (the parent maps in _loader_births and _census_floor), and a real walk under an unlisted name, a
    recursion over ast.iter_fields, node._fields or ast.dump, is invisible to it with no row at all; the ruling stops the list
    widening, keeps the finder as an early warning that refuses the forms it names and is silent on the rest, and carries the
    contract here, on something that enumerates no syntax. Every census entry point in _CENSUSES is driven over the real tree it
    reads with a stranger planted at every node position of the grammar an exec-mode Module offers on the running interpreter
    (_grammar_positions: the positions derived by execution from a synthetic corpus and complete for the interpreter or red naming
    the field they are not; _plant_at: a class the ast module does not define, deriving from the position's base, in a minimal
    container appended to the module body), each position alone, and each drive must raise _walk's refusal naming the class;
    unplanted, each returns. An entry point that takes a tree is handed the planting parse; one that parses inside runs under a
    patch of ast.parse that plants what the real parse returns, so the plant lands exactly where that entry point parses (the module
    reads ast.parse by attribute at call time; _walk calls ast.walk, which the patch does not touch; the patch is lifted on exit,
    and no thread parses during the case), the parse cached per source and the plant removed after each drive. A census that walks
    around _walk in the position a plant sits in passes that plant over, answers a census and reds the first case naming it and the
    position, whatever name it walks under. The unit is the position and not a class of positions, and not a site (review round 6,
    lens one: the witness planted at three sites, the module body's end, the first def's body and the first class's body, three of
    the 147 node positions an exec-mode Module offers on 3.12, all statement lists, so a hand-rolled walk substituted for _walk that
    read any other position class by hand, a decorator list, a call's arguments, a comprehension's generators, an f-string's values,
    a match statement's cases, annotations and type parameters, kept every case green, as did one reading the nested statement
    lists or AsyncFunctionDef.body alone; and one plant per position class was not enough either, green under a walk hand-reading
    ClassDef.body alone). The residue, stated: the node positions of the roots of the other parse modes (Interactive.body,
    Expression.body, FunctionType.argtypes and FunctionType.returns), which nothing inside a Module holds and no census parses; and
    a census that reads a child off the parent the walk yielded, before the child's own turn, meets the stranger unrefused there
    and reds here as an exception that is not the refusal (the finder's from-import branch did, at ImportFrom.names, an
    AttributeError on the stranger's name, the one position where the refusal did not come first; it reads alias nodes alone since
    the round-6 fixes, so every position refuses). The second case holds the roster: its count, its floor by derivation
    (_census_floor over this module's own AST: every reader reference, _walk by name or ast.parse, inspect.getsource or
    inspect.getsourcelines by attribute, called or handed on as a value, attributed to its enclosing def or class chain over the
    whole tree; every module-level def in the floor is a row, and the floor is alive, since every row that parses inside is in it),
    that every row names a module-level def, and that the class chains and the module-level statements in the floor are exactly the
    pinned ones, each with its reason (the readers inside the test classes, the roster pin's inline _walk over subtrees _door_regions,
    a row, holds after a whole-tree walk that refuses first, and the refusal case's control over a synthetic grammar tree, the
    _WALK_EXEMPT row, among them; at module level the _door_regions row's drive lambda alone). The floor's boundary is the spelling
    of the reader alone, in any container: a reference is in it only when it names _walk or spells one of the three exactly, so a
    census that parses under another road (compile with ast.PyCF_ONLY_AST, an alias of the module, importlib) or is handed a
    pre-parsed tree under any parameter name and walks by hand calls none of those and joins the roster by the rule in its comment
    alone, the count pin noticing the edit; a reader in a nested class's method, a class-body statement or a module-level statement,
    or one handing _walk on as a value, is in the floor since the round-7 fixes and pinned by the second case (each was attributed
    to nothing, and green, before them). The third case holds
    the instrument: the derivation is complete or red naming the field (the corpus without its type-comment source reds naming the
    type-comment fields and the type ignores), the planter lands exactly one stranger at exactly the named position, deriving from
    the position's base, and removes it, and a hand-rolled walk substituted for _walk that reads one position by hand passes the
    plant at that position over while the plant at another is refused, the per-position sensitivity the first case rests on. The
    fourth case is the negative control and the reason the contract rides on execution: two hand-rolled recursions, one over
    ast.iter_fields and one over node._fields, walk the same planted tree, return a census listing the stranger twice with no
    refusal, and the finder answers no reference over either; ast.iter_fields is deliberately NOT added to _TRAVERSAL. Derives: the
    node positions from the running interpreter over the corpus (_grammar_positions, every field of every concrete class observed
    or red naming the field), the plantable residue as the positions of the mod roots other than Module (_plantable, re-derived by
    the instrument case), one drive per plantable position per roster row (the count asserted), and each stranger's base from the
    children the corpus showed at its position. Bounds: the roster's drive column, hand-written drives each executed unplanted and
    planted; _GRAMMAR_CORPUS, _as_statement's container rows and _minimal's defaults, scaffolding whose completeness the derivation
    reds on (an unobserved field, a base no row holds); the refusal's text matched, the stranger's name and the table's phrase; and
    the instrument case's samples, four field names the reduced corpus must name and one hand-read position, ClassDef.body, against
    one walked, FunctionDef.body."""

    def test_every_census_entry_point_refuses_a_planted_stranger_and_returns_unplanted(self):
        door = jd.load_goals_shared
        self.assertEqual((door.__code__.co_name, os.path.basename(os.path.realpath(door.__code__.co_filename))), ("load_goals_shared", JUDGE_FILE),
                         "the door the _door_regions row reads is the judge's own (a harness case's recorder is gone by its cleanup)")
        positions = _grammar_positions()
        plantable = _plantable(positions)
        self.assertTrue(plantable, "the derived population offers node positions to plant (a derived expectation fails on empty)")
        real = ast.parse
        accept = []
        for i, (name, shape, drive) in enumerate(_CENSUSES):
            label = "%s (row %d, shape %s)" % (name, i, shape)
            try:
                got = drive(real)
            except Exception as e:                      # noqa: BLE001  the accept side collects whatever an entry point raised
                accept.append("%s raised %s: %s" % (label, type(e).__name__, str(e)[:160]))
                continue
            if got is None:
                accept.append("%s answered None" % label)
        self.assertEqual(accept, [], "the accept side: every census entry point, driven unplanted over the tree it really reads, returns an "
                                     "answer: %s" % "; ".join(accept))
        # the refuse side, per position ALONE: a census that walks one position through _walk and reads another by hand refuses the
        # plant _walk meets and passes over the one in the hand-read position, so one refusal over a plant at several positions is not
        # the contract (a verifier of the round-5 fixes, for sites; review round 6, lens one, for positions). The parse is cached per
        # source and the plant removed after each drive, so a row over the kernel costs a walk and not a parse per position
        cache, refuse, drives = {}, [], 0

        def planting(key, planted):
            def planting_parse(source, *a, **k):
                ck = (source, a, tuple(sorted(k.items())))
                tree = cache.get(ck)
                if tree is None:
                    tree = cache[ck] = real(source, *a, **k)
                if isinstance(tree, ast.Module):      # the roots of the other parse modes take no plant (the stated residue)
                    planted.append(_plant_at(tree, key, positions))
                return tree
            return planting_parse
        for key in plantable:
            where = "position %s.%s" % key
            for i, (name, shape, drive) in enumerate(_CENSUSES):
                label = "%s (row %d, shape %s)" % (name, i, shape)
                planted = []
                planting_parse = planting(key, planted)
                drives += 1
                try:
                    if shape == "parses":
                        with unittest.mock.patch.object(ast, "parse", planting_parse):
                            drive(planting_parse)
                    else:
                        drive(planting_parse)
                except AssertionError as e:
                    if "Frobnicate" not in str(e) or "do not classify" not in str(e):
                        refuse.append("%s at %s raised an AssertionError that is not the grammar refusal: %s" % (label, where, str(e)[:200]))
                    elif not planted:
                        refuse.append("%s at %s refused, but nothing was planted through the planting parse, so the refusal is not the plant's"
                                      % (label, where))
                except Exception as e:                  # noqa: BLE001  any other raise is not the refusal either
                    refuse.append("%s at %s raised %s instead of the grammar refusal: %s" % (label, where, type(e).__name__, str(e)[:160]))
                else:
                    if not planted:
                        refuse.append("%s at %s parsed no Module through the planting parse and returned" % (label, where))
                    else:
                        refuse.append("%s PASSED THE STRANGER OVER at %s and answered a census (%d tree(s) planted)" % (label, where, len(planted)))
                finally:
                    for _container, _stranger, unplant in reversed(planted):
                        unplant()
        self.assertEqual(drives, len(plantable) * len(_CENSUSES), "one drive per position per roster row")
        self.assertEqual(refuse, [], "the refuse side: every census entry point, driven over the same tree with a stranger planted at each of the "
                                     "%d node positions of the grammar an exec-mode Module offers on Python %s, each alone, raises _walk's grammar "
                                     "refusal naming Frobnicate on each drive. One that did not walks around _walk in the position the plant sits "
                                     "in (a hand-rolled recursion over ast.iter_fields, node._fields, ast.dump or any other name, or a hand read "
                                     "of one position beside a _walk over the others) and would report a site absent where it could not read; "
                                     "route it through _walk. One that raised something else read a child off the parent the walk yielded, "
                                     "before the walk reached the child; read the child where the walk yields it: %s"
                                     % (len(plantable), sys.version.split()[0], "; ".join(refuse)))

    def test_the_roster_holds_its_count_and_its_floor(self):
        """The roster's count and its floor. Derives: the floor over this module's own AST (_census_floor: every reader reference
        attributed to its def or class chain, whatever the container) and, against it, every module-level def in the floor a roster
        row; every row that parses inside found by the floor (alive, so a derivation answering less reds); every row naming a
        module-level def of this module; the class chains equal to the pinned dict both ways; and the module-level statements equal
        to the one lambda. Bounds: the count, nine, a tripwire that makes a row added or removed carry a reason; the reason beside
        each pinned chain and the module statement, a judgment (each is outside the roster because it hands its parse to a row, reads
        a subtree a row holds, keeps a parse as a value, reads a line number or a def's first statement and walks nothing, or reads
        a synthetic grammar tree); and the floor's own boundary, the spelling of the reader (_TREE_READERS and _walk by Name), so a
        census parsing under another road or handed a pre-parsed tree joins the roster by the comment's rule alone."""
        tree = ast.parse(Path(os.path.realpath(__file__)).read_text(encoding="utf-8"))
        defs, classes, module = _census_floor(tree)
        names = {name for name, _shape, _drive in _CENSUSES}
        self.assertEqual(len(_CENSUSES), 9, "the roster holds nine rows: the finder over this module's text, the hand-off line reader, the site "
                                            "census, the bump census, the birth pin over the judge and over the kernel, the roster pin's reading "
                                            "of the door, the floor itself and the position derivation over its corpus (a census added or removed "
                                            "changes this count with its reason): %r" % [(name, shape) for name, shape, _drive in _CENSUSES])
        self.assertEqual(sorted(set(defs) - names), [],
                         "a module-level def that calls _walk by name or parses a source by attribute (ast.parse, inspect.getsource, "
                         "inspect.getsourcelines) and is not a row of _CENSUSES: %r. It reads a tree and answers a census, so the witness must "
                         "drive it over a planted stranger; add its row. The floor by def: %r" % (sorted(set(defs) - names), defs))
        parses = {name for name, shape, _drive in _CENSUSES if shape == "parses"}
        self.assertEqual(sorted(parses - set(defs)), [],
                         "the floor is alive: every row that parses inside calls ast.parse or an inspect source reader by attribute, so the "
                         "derivation must find it, and a derivation answering less (an empty floor would pass the line above) reds here: %r "
                         "missing from %r" % (sorted(parses - set(defs)), sorted(defs)))
        top = {s.name for s in tree.body if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertEqual(sorted(names - top), [], "every roster row names a module-level def of this module (a misspelled or moved row would "
                                                   "drive nothing under that name): %r" % sorted(names - top))
        # every class chain in the floor (a method, a nested class's method or a class-body statement referencing _walk by name or one
        # of _TREE_READERS by attribute, as a callee or a value), with the reason each is outside the roster; the floor derives the set,
        # this pins it both ways
        pinned = {
            "TheCensusOverEveryForm.test_every_hand_off_form_reads_as_the_table_says":
                ["inspect.getsourcelines"],                  # a line number for the table's rows; walks nothing
            "TheCountersOneSite._the_named_def":
                ["ast.parse", "inspect.getsource"],          # parses a helper and reads .body[0]; walks nothing
            "TheCountersOneSite.test_the_shared_doors_bump_roster_is_the_reconciliations_and_its_second_bumps_sit_below_the_fills":
                ["_walk", "ast.parse", "inspect.getsource"], # the roster pin's inline reads (the deep count per list, the bumps under each
                                                             # finalbody, the try subtrees) are over subtrees _door_regions, a row, holds
                                                             # after a whole-tree walk that refuses a stranger first
            "TheDoorBumpsAtMostOneSecondKeyPerCall._sites":
                ["ast.parse", "inspect.getsourcelines"],     # the door's bump sites through _door_regions, a row, mapped to lines for the trace
            "TheGrammarIsTheOneTheWalkersClassify.test_a_walker_refuses_a_node_it_does_not_classify_by_name":
                ["_walk", "ast.parse"],                      # the refusal case's control over a synthetic grammar tree (the _WALK_EXEMPT row)
            "TheGrammarIsTheOneTheWalkersClassify.test_no_reference_to_a_traversal_name_sits_outside_walk":
                ["_walk", "ast.parse", "inspect.getsource"], # parses this module's text and the samples for _traversal_references, a row
                                                             # (the parse is the row's argument), and reads the finder's own def through
                                                             # _walk for the forms it reports, a subtree of that def and no census
            "TheWalkersRefuseAStrangerByExecution.test_every_census_entry_point_refuses_a_planted_stranger_and_returns_unplanted":
                ["ast.parse"],                               # keeps the real parse as a value: the accept side hands it to every drive and
                                                             # the planting parse wraps it; the case parses nothing itself
            "TheWalkersRefuseAStrangerByExecution.test_a_hand_rolled_recursion_passes_the_stranger_over_and_the_finder_does_not_see_it":
                ["ast.parse", "inspect.getsource"],          # parses a census's source for the finder, a row, and the planted tree for the
                                                             # negative control; its nested recursion folds into the case
            "TheWalkersRefuseAStrangerByExecution.test_the_positions_are_derived_complete_the_planter_lands_where_it_says_and_a_hand_read_position_passes_its_plant_over":
                ["ast.parse"],                               # parses the trees the planter plants into and the hand-reading control reads
                                                             # (the control stands in for _walk under a patch)
            "TheWalkersRefuseAStrangerByExecution.test_the_roster_holds_its_count_and_its_floor":
                ["ast.parse"],                               # this case: parses this module's text for _census_floor, a row
        }
        self.assertEqual(classes, pinned,
                         "the class chains reading a tree inline are exactly the pinned ones, each outside the roster for the reason beside "
                         "its row. A chain in the floor and not pinned reads a tree and answers a census: route it through a module-level def "
                         "with its roster row, or pin it here with its reason; a pinned chain not in the floor is a stale row. Not pinned: %r; "
                         "not in the floor: %r; pinned with other spellings: %r"
                         % (sorted(set(classes) - set(pinned)), sorted(set(pinned) - set(classes)),
                            sorted(k for k in set(classes) & set(pinned) if classes[k] != pinned[k])))
        self.assertEqual(module, {"_CENSUSES": ["inspect.getsource"]},
                         "the module-level statements reading a tree under no def and no class are exactly one: the _door_regions row's drive "
                         "lambda in _CENSUSES reads the door's source as the argument of the parse the witness hands it, a reader and not a "
                         "census. Another module-level reader (a lambda or a comprehension at import time calling _walk or one of "
                         "_TREE_READERS) is a census under no name the roster can drive: route it through a module-level def with its row, or "
                         "pin it here with its reason: %r" % module)

    def test_the_positions_are_derived_complete_the_planter_lands_where_it_says_and_a_hand_read_position_passes_its_plant_over(self):
        positions = _grammar_positions()
        classes = {c.__name__: c for c in _AST_KNOWN}
        self.assertEqual(set(positions), {(name, field) for name, c in classes.items() for field in c._fields},
                         "one record per field of every concrete class the interpreter defines, the population the plants are drawn from")
        node = sorted(key for key, p in positions.items() if p["kind"] == "node")
        self.assertTrue(node, "the population holds node positions (a derived expectation fails on empty)")
        for key in node:
            self.assertIsNotNone(positions[key]["base"], "a node position has the base its children derive from: %r" % (key,))
        # complete or red naming the field: the corpus without its one type-comment source leaves the type-comment fields, the type
        # ignores and Module.type_ignores unobserved, and the derivation names them instead of answering a population short of them
        reduced = [row for row in _GRAMMAR_CORPUS if not row[2]]
        self.assertEqual(len(reduced), len(_GRAMMAR_CORPUS) - 1, "the corpus holds exactly one source parsed with type comments")
        with self.assertRaises(AssertionError) as cm:
            _grammar_positions(reduced)
        for name in ("('Module', 'type_ignores')", "('TypeIgnore', 'tag')", "('Assign', 'type_comment')", "('arg', 'type_comment')"):
            self.assertIn(name, str(cm.exception), "the reduced corpus's unobserved fields are named: %s" % cm.exception)
        self.assertNotIn("('Module', 'body')", str(cm.exception), "and a field the reduced corpus still fills is not")
        # the residue is derived: the node positions not plantable are exactly those of the mod classes other than Module
        plantable = _plantable(positions)
        self.assertEqual(sorted(set(node) - set(plantable)),
                         sorted(key for key in node if classes[key[0]].__bases__[0] is ast.mod and key[0] != "Module"),
                         "the residue is the node positions of the roots of the other parse modes, which nothing inside a Module holds")
        self.assertTrue(all(classes[key[0]].__bases__[0] is ast.mod for key in set(node) - set(plantable)))
        # the planter: at every plantable position exactly one stranger lands, in the named field of an instance of the named class,
        # deriving from the field's base and refused by _walk's identity test, and unplant restores the tree (ast.dump reads every field
        # of every node, so the count over its text is the count over the whole tree)
        for key in plantable:
            tree = ast.parse("x = 1\n")
            before = ast.dump(tree)
            container, stranger, unplant = _plant_at(tree, key, positions)
            self.assertEqual(type(container).__name__, key[0], "the container is an instance of the position's class at %s.%s" % key)
            held = getattr(container, key[1])
            self.assertEqual([item for item in (held if isinstance(held, list) else [held]) if item is stranger], [stranger],
                             "the stranger sits in the named field at %s.%s: %r" % (key + (held,)))
            base = positions[key]["base"]
            self.assertIsInstance(stranger, getattr(ast, base) if base in _AST_ABSTRACT else ast.AST,
                                  "the stranger derives from the position's base, %s, at %s.%s" % ((base,) + key))
            self.assertNotIn(type(stranger), _AST_KNOWN, "and is no class of the table, so _walk refuses it by identity")
            self.assertEqual(ast.dump(tree).count("Frobnicate()"), 1, "exactly one stranger in the whole tree at %s.%s: %s" % (key + (ast.dump(tree),)))
            unplant()
            self.assertEqual(ast.dump(tree), before, "unplant restores the tree at %s.%s" % key)
        # the per-position sensitivity the first case rests on: a hand-rolled walk substituted for _walk that reads ClassDef.body by
        # hand (yields what it finds there and refuses nowhere below it) passes the plant at ClassDef.body over, so the finder answers a
        # census over the planted tree, and is refused at FunctionDef.body, a position it walks; the first case would red the first and
        # not the second, which is why one plant per position, each alone, is the unit

        def hand_reading(hand):
            def reader(tree):
                todo = [(tree, True)]
                while todo:
                    current, refusing = todo.pop(0)
                    if refusing and type(current) not in _AST_KNOWN:
                        raise AssertionError("a node of class %s, which the census walkers of this module do not classify (a hand-rolled walk "
                                             "standing in for _walk)" % type(current).__name__)
                    for field, value in ast.iter_fields(current):
                        below = refusing and (type(current).__name__, field) not in hand
                        for child in (value if isinstance(value, list) else [value]):
                            if isinstance(child, ast.AST):
                                todo.append((child, below))
                    yield current
            return reader
        source = "def f(sid):\n    return jd.load_goals_shared(sid)\n"
        with unittest.mock.patch.object(sys.modules[__name__], "_walk", hand_reading({("ClassDef", "body")})):
            tree = ast.parse(source)
            _plant_at(tree, ("ClassDef", "body"), positions)
            self.assertEqual(_traversal_references(tree), [], "a walk that reads class bodies by hand passes the stranger in one over, and the "
                                                             "finder answers a census over the planted tree (the state the first case reds)")
            tree = ast.parse(source)
            _plant_at(tree, ("FunctionDef", "body"), positions)
            with self.assertRaises(AssertionError) as cm:
                _traversal_references(tree)
            self.assertIn("Frobnicate", str(cm.exception), "and refuses the stranger at a position it walks: %s" % cm.exception)

    def test_a_hand_rolled_recursion_passes_the_stranger_over_and_the_finder_does_not_see_it(self):
        def over_iter_fields(tree):
            """A whole walk written over ast.iter_fields, with no _walk: the class the name-keyed finder cannot see."""
            seen = []

            def rec(node):
                seen.append(type(node).__name__)
                for _field, value in ast.iter_fields(node):
                    for child in (value if isinstance(value, list) else [value]):
                        if isinstance(child, ast.AST):
                            rec(child)
            rec(tree)
            return seen

        def over_node_fields(tree):
            """The same walk over node._fields and getattr: no name of the ast module at all."""
            seen = []

            def rec(node):
                seen.append(type(node).__name__)
                for field in node._fields:
                    value = getattr(node, field, None)
                    for child in (value if isinstance(value, list) else [value]):
                        if isinstance(child, ast.AST):
                            rec(child)
            rec(tree)
            return seen

        positions = _grammar_positions()

        def planted():
            """A small tree with a stranger statement at the module level and one in a def's body (two plants, each alone a position)."""
            tree = ast.parse("def f(sid):\n    return jd.load_goals_shared(sid)\n")
            _plant_at(tree, ("Module", "body"), positions)
            _plant_at(tree, ("FunctionDef", "body"), positions)
            return tree
        with self.assertRaises(AssertionError) as cm:      # the control: a roster census refuses the same planted tree
            _traversal_references(planted())
        self.assertIn("Frobnicate", str(cm.exception), "a census that reads through _walk refuses the planted tree naming the class: %s" % cm.exception)
        for census in (over_iter_fields, over_node_fields):
            seen = census(planted())
            self.assertEqual(seen.count("Frobnicate"), 2,
                             "%s walks the whole planted tree, meets the stranger at module level and inside the def, and passes both over with "
                             "no refusal, answering a census of %d nodes: %r. This is the class the walker contract must be held against by "
                             "execution, since the finder below does not see it" % (census.__name__, len(seen), seen))
            refs = _traversal_references(ast.parse(textwrap.dedent(inspect.getsource(census))))
            self.assertEqual(refs, [], "the finder answers no reference over %s: it keys on four traversal names, and a recursion over "
                                       "ast.iter_fields or node._fields spells none, so it is silent on this whole class (the early warning's "
                                       "stated limit; the contract rides on the execution case above, and iter_fields is deliberately not "
                                       "added to _TRAVERSAL): %r" % (census.__name__, refs))


class Docs(unittest.TestCase):
    def test_the_reference_states_condition_7_in_the_jobs_paragraph_and_names_the_counter(self):
        """The reference's `jobs` block is the one home of the other-readers clause (review round 2, regression-2 and fresh-4:
        the clause stood in four hand-kept copies, two of them pinned by nothing, and said the three writers are reached from
        the look's wake legs and from the sweep, which is false of _dead_wait_block on the toggle-off pass). This case pins the
        home's wording, with each writer's callers, and the two pointers a test can read: the memos.nudgeWalk entry's and this
        module's own docstring's. The ledger entry (upstream/) carries the same pointer by hand and is not read here: the
        directory is fork-only infrastructure and this module is part of the offer the entry records, so a read of it would red
        upstream or need a skip, and a skipping pin pins nothing. Derives: nothing; the paragraphs are found by their anchors and the
        phrases asserted present. Bounds: the phrases pinned, the clause's wording as the reviewer ruled it, and the anchors that
        slice the reference and the field gloss, a policy; a rewording reds here and is answered by re-reading the ruling, not by
        widening the list."""
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
        """Every fragment of the module docstring that states a count of this module's cases in the form 'over its N cases', N in
        digits, is read here, the current head's against the loader's count and a historical one for its head label, and the current
        head's clean line against the same count, so a case added without a re-take reds this case naming each stale figure and its
        fragment, instead of leaving a count that reads true and is not (review round 3, correctness-2 and regression-2: the bypass sentence went stale nine
        commits and one case later; review round 4, correctness-2 and regression-4: the round-3 paragraph's clean line read 19
        passed at a head of 20 cases; review round 5, tests-2: the round-4 fix read one sentence through re.search while the same
        commit added three more case-count sentences it could not read, so the staleness class survived one sentence away, in prose
        the fix itself wrote). The sweep: every fragment of the docstring holding 'over its N cases' (a fragment runs between two
        full stops or semicolons, and holds one count, so each count sits with its own head label) is either the current head's,
        naming 'this head', whose N must equal the loader's count, or a historical one, which must name its head by role (the head of
        the round-N fixes, the head the round-N ruling read, the head the round-N verifiers read, of that head) and is not pinned; at
        least one current-head fragment must exist (a derived expectation fails on empty); the phrase
        'this head, the head of the round-N fixes' must name exactly one round across the docstring (two is a paragraph nobody
        relabelled when the next round's landed); and the clean line, 'The clean module at this head, the head of the round-N
        fixes: P passed[, F failed (...)] single-process on 3.10, 3.11, 3.12, 3.13 and 3.14t', must occur exactly once, name that
        same round, and carry figures that sum to the count (a failed figure records a head at which another count was one re-take
        behind). A paragraph that goes historical is relabelled 'at the head of the round-N fixes', which matches none of the
        current-head reads; the template a history paragraph writes its current-head sentences in is therefore exact: 'at this
        head, the head of the round-N fixes, over its N cases'. What the sweep does not read by value, stated and re-derived at the
        head of the round-7 fixes by a scan of every fragment of the docstring that names 'this head' (a verifier of the round-5
        fixes: the first sentence here said every sentence stating a figure): a count spelled as a word (the battery paragraph's
        'twelve cases', whose head is the build's verifier pass after the round-2 fixes, a role the label regex does not know); the
        historical clean lines (labelled by role, not summed); a paragraph's per-state figures, 'F failed, P passed', which ride on
        the paragraph's framing count and are re-taken with it (the current head's paragraph's are read for their form alone by the
        census below, and the first paragraph's alias-control figure, in a fragment naming this head outside that paragraph, by
        neither); and a historical paragraph's description of a mutation that spells 'this head' as the mutation's words, the
        round-5 paragraph's, whose figures are that head's. The current head's paragraph is then read whole by a census (review
        round 6, tests-2 and regression-3: the round-5 paragraph restated the head's count in a second form, 'so a figure here reads
        against 37', which the sweep does not read and which sat, as every per-state figure does, in a fragment the split at '3.12'
        leaves with no head label, so the copy set one below left the module green; the four copies, one each in the paragraphs of
        the consolidation pass and rounds 4, 5 and 6, are removed rather than read, and this census reds the next): the paragraph
        naming 'this head, the head of the round-N fixes' is found (exactly one, or red), and every digit run in it must sit inside
        one of the figure forms the census names: the swept count, 'P passed', 'F failed', a comparison 'N against N' or 'N against
        the N cases left', a round ('round N', 'rounds N, N and N'), a finding label ('tests-2'), a date, and an interpreter version; a
        digit run in no form, a 'reads against N' copy among them, reds naming its clause, and a form that matches nothing in the
        paragraph reds as a stale row. Derives: the framing counts and their head labels from every 'over its N cases' fragment, the
        one-head rule and the clean line's sum from the docstring's text, and every figure of the current head's paragraph, each
        checked against the forms. Bounds: the template forms read (the framing sentence, the head labels, the clean line) are the
        docstring's conventions, a policy; the figure forms are an enumeration of the prose's shapes and not a population, each row a
        tripwire that makes a new shape carry a reason; a per-state figure's value rides on its re-take (a state that removes a case
        sums below the count, so no sum pins it); and a historical paragraph's figures are unpinned by design, read for the head
        label alone."""
        doc = " ".join(sys.modules[__name__].__doc__.split())
        n = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]).countTestCases()
        # every count per fragment, a fragment running between two full stops or semicolons (a verifier of the round-5 fixes: a greedy
        # prefix before 'over its' read the last count of a fragment alone, so a stale count written before a fresh one in the same
        # sentence was invisible), and one count per fragment, so each count sits with its own head label
        counted = [(p.strip(), [int(c) for c in re.findall(r"over its (\d+) cases", p)]) for p in re.split(r"[.;]", doc)
                   if re.search(r"over its \d+ cases", p)]
        fragments = [(f, c) for f, cs in counted for c in cs]
        self.assertTrue(fragments, "the docstring states at least one figure over this module's cases in the form 'over its N cases'")
        self.assertEqual(len(counted), len(fragments), "one count per fragment, so every count sits in a fragment with its own head label: "
                                                        "%d fragment(s) hold %d count(s); the fragments holding more than one: %r"
                                                        % (len(counted), len(fragments), [f for f, cs in counted if len(cs) > 1]))
        current = [(f, c) for f, c in fragments if "this head" in f]
        historical = [(f, c) for f, c in fragments if "this head" not in f]
        self.assertTrue(current, "at least one 'over its N cases' fragment is the current head's, naming 'this head' (every one here is "
                                 "historical, so the current head's states have no count pinned): %r" % [f for f, _c in historical])
        stale = [(c, f) for f, c in current if c != n]
        self.assertEqual(stale, [], "a current-head figure over this module's cases that is not the loader's count, %d: %s. A case was added "
                                    "since the states were taken, so re-take them at this head (the bypass plants and the alias control, each "
                                    "landed on the kernel, run and reverted with the three files hashed) and write the new count, or relabel "
                                    "the paragraph by its head's role if it has gone historical"
                                    % (n, "; ".join("%d in '%s'" % (c, f) for c, f in stale)))
        unlabelled = [f for f, _c in historical
                      if not re.search(r"head of the round-\d+ fixes|head the round-\d+ (?:ruling|verifiers) read|of that head", f)]
        self.assertEqual(unlabelled, [], "a historical figure over this module's cases names its head by role (the head of the round-N fixes, "
                                         "the head the round-N ruling read, the head the round-N verifiers read, of that head), so a reader "
                                         "knows which count it reads against: %r" % unlabelled)
        heads = set(re.findall(r"this head, the head of the round-(\d+) fixes", doc))
        self.assertEqual(len(heads), 1, "exactly one round's head is 'this head' across the docstring: rounds %r (a paragraph that has gone "
                                        "historical is relabelled 'at the head of the round-N fixes')" % sorted(heads))
        clean = re.findall(r"The clean module at this head, the head of the round-(\d+) fixes: (\d+) passed(?:, (\d+) failed \([^)]*\))? "
                           r"single-process on 3\.10, 3\.11, 3\.12, 3\.13 and 3\.14t", doc)
        self.assertEqual(len(clean), 1, "the current head's paragraph carries exactly one clean line naming this head by role and its figures on "
                                        "the five interpreters: %r" % clean)
        rnd, passed, failed = clean[0][0], int(clean[0][1]), int(clean[0][2] or 0)
        self.assertEqual({rnd}, heads, "the clean line's round, %s, is the one round whose head is 'this head', %r" % (rnd, sorted(heads)))
        self.assertEqual(passed + failed, n, "the clean line's figures, %d passed and %d failed, sum to %d and this module has %d cases: the "
                                             "line was written at another head; re-take the five-interpreter run at this head and write its "
                                             "figures" % (passed, failed, passed + failed, n))
        # the current head's paragraph whole, every figure in it in a named form (review round 6, tests-2 and regression-3: the
        # 'reads against 37' copy sat in a fragment the split at '3.12' left unlabelled, as every per-state figure does, so a
        # fragment-keyed read cannot see the form; the paragraph, blank line to blank line, is the unit that carries the label)
        paragraphs = [" ".join(p.split()) for p in re.split(r"\n[ \t]*\n", sys.modules[__name__].__doc__) if p.strip()]
        head_paragraphs = [p for p in paragraphs if re.search(r"this head, the head of the round-\d+ fixes", p)]
        self.assertEqual(len(head_paragraphs), 1, "exactly one paragraph of the docstring names the current head by role, 'this head, the "
                                                  "head of the round-N fixes': %d do" % len(head_paragraphs))
        paragraph = head_paragraphs[0]
        forms = (r"over its \d+ cases", r"\d+ passed", r"\d+ failed", r"\d+ against (?:the )?\d+(?: cases left)?",
                 r"rounds? \d+(?:, \d+)*(?: and \d+)?", r"[a-z]+\d*-\d+", r"\d{4}-\d{2}-\d{2}", r"3\.1\d+t?")
        covered, unmatched = set(), []
        for form in forms:
            hits = list(re.finditer(form, paragraph))
            if not hits:
                unmatched.append(form)
            for h in hits:
                covered.update(range(h.start(), h.end()))
        self.assertEqual(unmatched, [], "every figure form the census names matches at least once in the current head's paragraph; a row "
                                        "nothing matches is stale, so drop it: %r" % unmatched)
        figures = list(re.finditer(r"\d+", paragraph))
        self.assertTrue(figures, "the current head's paragraph carries at least one figure, its framing count")
        stray = [paragraph[max(0, m.start() - 40):m.end() + 40] for m in figures if m.start() not in covered]
        self.assertEqual(stray, [], "a figure in the current head's paragraph in a form the census does not name, so nothing reads it and "
                                    "it can go stale unseen (a 'reads against N' copy of the framing count is the form review round 6 "
                                    "found): write it in a named form, or add the form here with its reason: %r" % stray)


if __name__ == "__main__":
    unittest.main()
