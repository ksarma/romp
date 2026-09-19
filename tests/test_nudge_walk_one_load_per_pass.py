#!/usr/bin/env python3
"""Fold ruling A condition 7 as the reviewer ruled it on 2026-09-19 after jobs stage 1 (fork PR 784), stated PER MECHANISM:
the condition bounds two loaders of a session's goal store on the walk's road, the look's decision read and the placement
gate's currency check, each on its own. The WALK takes at most one shared goal-store load per alive session per pass:
exactly one when its look reaches the store, zero when the look is skipped or ends at a state gate before the store read.
The PLACEMENT GATE's post-derivation currency check is a SEPARATE load, at most one per DERIVED session, counted apart. Two
bounds, each attributable to its caller. Other readers of the same store run on the same pass under their own rules and
outside both bounds: the dead-man's fresh re-read inside the look (`_wake_goal`, the writer's loader, under `goals.loads`)
and the wake sweep after the per-session loop (`_awaiting_wake_outcomes`, called outside the toggle guard, one shared load
per wake record it owns that `memos.nudgeWalk.loads` does not count), which runs after the walk in the same pass, not on
it. The rule was first written as one call count; a total is falsified by any new legitimate reader of the store, where a
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
pass-through call (the line read from the wrapper's source at setUp), so a load written inside a wrapper's own body is
named for the wrapper in the judge's file, and calls through to the real loader, so nothing about the shared cache is
stubbed. A call from the look's body or from its gate wrapper (`_nudge_look_gated`'s
inner function, the same mechanism) is the walk's, a call from `_nudge_placement_gate` is the gate's, a call from
`_awaiting_wake_outcomes` is the wake sweep's (the store's third reader on the pass, bounded below), and any other caller
during a pass fails the test, named by function, file and line. The writer door has its own assertion on every pass: the
writer recorder's list must be empty after the tick, each entry named by function, file and line, kept apart from the
shared door's assertion (one filter over both lists would accept a writer-door load whose caller is the walk); a call
through `load_goals_or_fault` is named for its kernel caller, never for the judge's `_or_fault`, and a load written inside
`_or_fault` or either outer wrapper is named for that wrapper. The claim has three limits. The door: a third loader that reaches the store through the judge's loaders during the pass is caught and named;
a reader below those loaders (the judge's own file reader and parser) is outside the recorders and outside the claim. The
road: the execution witness covers every caller the fixture actually executes; the helpers in REPLACED_KM and REPLACED_JD
and Sessions.backend_for run as stubs, so a loader inside their real bodies is outside the recorders and is caught by the
source census in TheCountersOneSite instead, one level deep (the helper's own source); setUp checks that it rebinds
exactly the listed names, so the census reads the fixture's list and not a hand-kept copy of it. The window: each pass, the
`_auto_nudge_tick` call (the records are cleared before it and read after it), so a load elsewhere in the process (a
builder, a handler, the perf snapshot the test reads after its last pass) is outside the window and is not this test's
claim. By the store's own counters, a witness keyed on the store rather than on a list of doors, one per door. The shared
door: every call that reaches the shared cache's branch and returns moves exactly one of hit, miss, compare_miss, absent
and fallback in `jd.shared_store_stats()` (a call whose open or read raises moves none, and reds as a recorded call that
took no read), so per pass the delta of those five must equal the walk's, the gate's and the sweep's recorded calls
together. The writer door: every `load_goals` call bumps `loads` in `jd.goal_io_stats()` at the loader's
first line, and the shared door hands a read to `load_goals` on exactly the absent, fallback, corrupt and
unreadable_journal counters (SHARED_HANDOFF_KEYS), so per pass the delta of `loads` must equal the recorded writer calls
plus those hand-offs (review round 2: until then the writer door was a recorder on one name, and a `load_goals` through a
reference bound before the recorder stood, or written inside the shared door's own body where the fallback skip takes it
for the hand-off, left every witness green). So a load through a door of this judge module onto its cache or its
counters that the recorders do not wrap, or through a reference to a real door taken before a recorder stood, is noticed
even though it cannot be named. Outside both witnesses: a reader that bypasses the kernel's judge module, the kernel
opening the store file itself or a second judge module loaded under another name with a cache and counters of its own
(review round 2 planted both; neither moved a witness). The two witnesses answer different questions: the recorders say
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
wake record, so the sweep reads nothing there, and TheSweepIsItsOwnBoundedReader seeds one record for an unwalked private
sid and shows one sweep load on each of two passes, once with a store whose nodes lack the goal and once with no store
file, where the shared door falls back into load_goals and that fallback is one logical read of the shared door's.

Red in both directions, each mutation landed on kernel/kernel.py and reverted: a load creeping into the skip path (a shared
read in the gated look before it consults the memo, or the skip's early return dropped) reds the skip pass on the walk's
bound; the load disappearing from the run path (the walk reusing a stale snapshot instead of reading) reds the run pass on
the walk's bound. The door plants, each through the bare `jd.load_goals_shared` spelling that a recorder on the outer door
alone missed: a load per session in the pass loop of `_auto_nudge_pass` reds every case on the unattributed caller, named
`_auto_nudge_pass` with the kernel's real file and the plant's line (4 failed, 3 passed); the same loop over the alive set
at the tick's setup, the same way (4 failed, 3 passed); a second read above the walk's own in `_auto_nudge_session` reds
the walk's bound (2 per session against 1), the census (2 sites against 1) and the store's counters (4 failed, 3 passed);
a load per walked sid at the top of `_awaiting_wake_outcomes` reds the sweep's bound in every case (1 against 0 owned
records) (4 failed, 3 passed); the sweep's read duplicated reds the sweep case on its bound (2 against 1) (2 failed, 5
passed); the sweep's read moved to the writer door reds the sweep case on the writer assertion, named
`_awaiting_wake_outcomes` with the kernel's real file and the read's line, and on its sweep count (no sweep load where 1
is asserted) (2 failed, 5 passed). The outer spelling at the pass-loop site names `_auto_nudge_pass`, never the judge's
`_or_fault`. The writer door: `jd.load_goals` per session in the pass loop reds every case on the writer assertion, named
`_auto_nudge_pass` (4 failed, 3 passed); `jd.load_goals_or_fault` at the same site is named for `_auto_nudge_pass` in the
kernel's file, not for `_or_fault` in the judge's (4 failed, 3 passed); `jd.load_goals(sid)` above the walk's own read is
named `_auto_nudge_session`, the case one filter over both doors would have taken for the walk's (3 failed, 4 passed);
`jd.load_goals_or_fault(key)` in `_put_walk_gate`'s write-on-change no-op branch, reached only on the state-gate case's
second and third passes, is named `_put_walk_gate` there (1 failed, 6 passed). The fallback edge: with the writer
recorder's code-identity skip removed, the sweep's no-store case reds on the writer assertion naming `load_goals_shared`
in the judge's file, the misattribution the skip prevents (1 failed, 6 passed). The road: `jd.load_goals_shared_or_fault` as the first statement
of the real `_session_awaiting` or the real `_closer_settled` leaves every execution case green (the stub runs) and reds
the source census naming the helper (1 failed, 6 passed each); the same plant in `_nudge_look_check`, which the fixture
does not replace, reds by execution naming `_nudge_look_check` (4 failed, 3 passed); with `_session_working` real, a
bare shared load at the top of its body reds by execution naming `_session_working`, where the stub hid it before (3
failed, 4 passed). The gate's bound: with the fixture's parse not recorded in jd._PARSE_CACHE, the first pass derives twice
and checks nothing (derived 2, gate 0), the bound holds and the qualified equality reds with its fixture message, at the
first pass's gate assertion (3 failed, 4 passed); the currency read duplicated in `_nudge_placement_gate` after the
derive count gives two checks per derive, and the bound, the per-sid ceiling and the first pass's gate assertion red (3
failed, 4 passed). The store's counters: a reference to the
real door bound at kernel import (`_REAL_LGS = jd.load_goals_shared`) and called per session in the pass loop is
invisible to the recorders and reds the reconciliation on every pass whose looks run, the counters two calls over the
recorded ones (4 failed, 3 passed); a phantom walk record appended by the recorder without a call through reds it the
other way, the recorded calls over the counters (3 failed, 4 passed). Every figure is from a run at the final head of the
second review round, over the module's seven cases; the assertion texts name the mechanism and are in the commit messages.

Drives the real pass (_auto_nudge_tick) over two alive sessions with real transcript files and real goal stores, on the
suite's fake clock (the pass takes `now`). SYNTHETIC fixtures only; a PRIVATE synthetic sid pair (the goal-store fixture
rule), their override journals cleaned in the teardown; the state root rebound through jd._rebind_state and `off` written
into its session-hosts."""
import ast
import inspect
import json
import os
import tempfile
import textwrap
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
KERNEL_FILE = os.path.basename(os.path.realpath(km.__file__))   # the kernel's real file: it is loaded from bin/romp-kernel, a symlink
# The callables the fixture replaces, other than the two recorded doors: the kernel names (the look's gates and the pass's
# helpers; _pending_ops and _PREV_ALIVE are data, not callables), the judge names, and Sessions.backend_for (replaced by
# setUp beside them). Their real bodies never run under the fixture, so the source census in TheCountersOneSite is the only
# witness for a loader inside them. _session_working is not in the list: its real body runs (the event model reads the
# fixture turns, both ended, as not working, the answer the stub gave), and the state-gate case replaces it for its own world.
REPLACED_KM = ("_alive_sessions", "_wait_for_graph", "_session_flag", "_compacting_now", "_api_error",
               "_interrupt_suppresses_nudge", "_backend_rewind_pending", "_last_state",
               "_session_awaiting", "_turn_romp_injected", "_closer_settled", "_revivers_pending",
               "_pending_ops", "_log_nudge_event", "_push_all", "_mark_views_dirty", "_path_of",
               "_debt_backstop_tick", "_PREV_ALIVE")
REPLACED_DATA = ("_pending_ops", "_PREV_ALIVE")
REPLACED_JD = ("parsed_session", "_segs", "plan_units")
JUDGE_FILE = os.path.basename(os.path.realpath(jd.__file__))
_UNSET = object()


def _pass_through_lines(fn, callee):
    """The line numbers, in `fn`'s file, of its calls to `callee`: the boundary wrapper's hand-off of the read (`loader(fsid)`
    in _or_fault, `_or_fault(...)` in the two outer wrappers), read from the source by the AST so a docstring or a comment
    naming the callee is not one. Absolute: inspect gives the source with its first line's number."""
    src, start = inspect.getsourcelines(fn)
    tree = ast.parse(textwrap.dedent("".join(src)))
    return frozenset(start - 1 + node.lineno for node in ast.walk(tree)
                     if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == callee)


def _caller(frame, boundary):
    """(function, file, line) of the frame that asked for the store: `frame` is the recorder's own, its f_back the immediate
    caller, and the judge's boundary frames are stepped over by code identity, never by name, so a call through either
    boundary wrapper is named for the kernel function that made it. `boundary` pairs each wrapper's code object with the
    lines of its pass-through calls (_pass_through_lines, taken at setUp): a boundary frame is stepped over only while it
    sits at one of those lines, so a load written anywhere else in a wrapper's own body is named for the wrapper itself,
    in the judge's file (review round 2: stepped over unconditionally, a load planted inside _or_fault was named for the
    wrapper's kernel caller, the misnaming that costs more than silence). The file is the basename of the frame's REAL
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
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)                  # cleanups run last in, first out: the seams go back, then the dir
        td = Path(self.td.name)
        self.saved = {k: getattr(km, k) for k in REPLACED_KM + ("_session_working",)}   # saved too: the state-gate case stubs it
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
        jd._rebind_state(td)                              # STATE and every dir derived from it, never jd.STATE alone
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
        before_km, before_jd = dict(vars(km)), dict(vars(jd))   # for the agreement check below: what this setUp rebinds
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
        boundary = tuple((fn.__code__, _pass_through_lines(fn, callee)) for fn, callee in
                         ((jd._or_fault, "loader"), (jd.load_goals_shared_or_fault, "_or_fault"), (jd.load_goals_or_fault, "_or_fault")))
        for code, lines in boundary:
            self.assertEqual(len(lines), 1, "%s hands the read on at exactly one call; the recorder steps over the wrapper only "
                                            "while its frame sits at that line" % code.co_name)
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
        jd.load_goals_shared = _shared                                           #  recorder recorded its caller, so nothing is recorded here
        jd.load_goals = _load
        # The road limit's list is checked against the fixture, not kept by hand: this setUp rebinds exactly the names REPLACED_KM
        # and REPLACED_JD list plus the two recorded doors, and Sessions.backend_for beside them. A stub added here without a
        # list entry would hide a loader from the execution witness AND from the census that reads the list (review round 2,
        # shown by re-adding the _session_working stub with a shared load in its real body: 7 passed)
        rebound_km = {k for k, v in vars(km).items() if before_km.get(k, _UNSET) is not v}
        self.assertEqual(rebound_km, set(REPLACED_KM), "setUp replaces exactly the kernel names REPLACED_KM lists, the census's targets: a "
                                                        "stub without a list entry hides a loader from the execution witness and the census")
        rebound_jd = {k for k, v in vars(jd).items() if before_jd.get(k, _UNSET) is not v}
        self.assertEqual(rebound_jd, set(REPLACED_JD) | {"load_goals", "load_goals_shared"},
                         "and exactly the judge names REPLACED_JD lists plus the two recorded doors")
        self.assertIsNot(km.Sessions.backend_for, self.saved_backend, "and Sessions.backend_for, replaced beside them")
        self._toggle(False)
        self._seed(SID_A, stamped=False)
        self._seed(SID_B, stamped=True, age=5 * H)

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
        check; `sweep`: the wake sweep's read per owned record, over every sid seen; never a total), the writer loads, and
        the sids parsed. The recorders stand on the judge's two doors, `jd.load_goals_shared` and `jd.load_goals`, and
        attribute through its boundary frames by code identity, so a shared load from any other function the fixture
        executes during the pass fails here, named by function, file and line (the helpers the fixture replaces, REPLACED_KM,
        REPLACED_JD and Sessions.backend_for, are the source census's in TheCountersOneSite, not this witness's), and the
        sweep is held to its bound per sid; the writer door's list is asserted empty after every pass, separately, each
        entry named the same way; a reader below the doors is outside the claim. The store's counters are reconciled
        against the recorded calls per door (`shared`, the delta over SHARED_CALL_KEYS, against the walk's, the gate's and
        the sweep's; `writerLoads`, the delta of goal_io loads, against the writer records plus the shared door's hand-offs
        over SHARED_HANDOFF_KEYS), so a load through a door of the judge module the recorders do not wrap is noticed,
        unnamed; a reader that bypasses the module is outside both. `calls` carries the shared records (sid, function, file,
        line) for a case's own assertions."""
        before = {k: km._NUDGE_WALK_STATS[k] for k in self.KEYS}
        gate0 = dict(km._NUDGE_GATE_STATS)
        s0, g0 = jd.shared_store_stats(), jd.goal_io_stats()["loads"]
        self.calls.clear(); self.writer.clear(); self.parsed.clear()
        km._auto_nudge_tick(now, {sid: {"state": ""} for sid in SIDS})
        s1, g1 = jd.shared_store_stats(), jd.goal_io_stats()["loads"]
        d = {k: km._NUDGE_WALK_STATS[k] - before[k] for k in self.KEYS}
        d["memo"] = tuple(km._NUDGE_GATE_STATS[k] - gate0[k] for k in ("served", "derived"))
        d["walk"] = {sid: sum(1 for s, c, _f, _ln in self.calls if s == sid and c in WALK) for sid in SIDS}
        d["gate"] = {sid: sum(1 for s, c, _f, _ln in self.calls if s == sid and c in GATE) for sid in SIDS}
        d["sweep"] = {}                                   # over every sid seen: the sweep's constituency includes unwalked sids
        for s, c, _f, _ln in self.calls:
            if c in SWEEP:
                d["sweep"][s] = d["sweep"].get(s, 0) + 1
        others = ["%s (%s:%d, sid ..%s)" % (c, f, ln, s[-4:]) for s, c, f, ln in self.calls if c not in WALK + GATE + SWEEP]
        self.assertEqual(others, [], "a shared load from a caller that is neither the walk, the placement gate nor the wake sweep, "
                                     "by function, file and line: %s" % "; ".join(others))
        for sid, n in sorted(d["sweep"].items()):
            self.assertLessEqual(n, self.owned_records.get(sid, 0),
                                 "sid ..%s: the sweep takes at most one shared load per wake record it owns per pass (a record that is "
                                 "wake-set, not failed, moot or answered, not muted, and whose sid the walk did not visit or visited "
                                 "under a wedge gate), none for a sid with no owned record; it runs after the per-session loop in the "
                                 "same pass and memos.nudgeWalk.loads does not count it" % sid[-4:])
        d["shared"] = {k: s1[k] - s0[k] for k in SHARED_CALL_KEYS if s1[k] != s0[k]}
        self.assertEqual(sum(d["shared"].values()), sum(d["walk"].values()) + sum(d["gate"].values()) + sum(d["sweep"].values()),
                         "every shared-store call moves one of the five counters; a difference is a load through a door the recorder "
                         "does not wrap (unnamed by construction) or a recorded call that took no read: counters %r against walk %r, "
                         "gate %r, sweep %r" % ((d["shared"],) + tuple({k[-4:]: v for k, v in d[m].items()} for m in ("walk", "gate", "sweep"))))
        d["calls"] = list(self.calls)
        writer = ["%s (%s:%d, sid ..%s)" % (c, f, ln, s[-4:]) for s, c, f, ln in self.writer]
        self.assertEqual(writer, [], "zero plain load_goals from any caller during the pass, the whole tick (condition 7 in ruling A's "
                                     "wording says the decision path; this window is wider), by function, file and line: %s" % "; ".join(writer))
        handoffs = sum(s1[k] - s0[k] for k in SHARED_HANDOFF_KEYS)
        self.assertEqual(g1 - g0, len(self.writer) + handoffs,
                         "the writer door's own counter, goal_io loads, moves once per load_goals call (the loader's first line), and the "
                         "shared door hands a read to load_goals on exactly the absent, fallback, corrupt and unreadable_journal counters, "
                         "so the delta must equal the recorded writer calls plus those hand-offs; a difference is a writer-door load the "
                         "recorder did not see, through a reference to the real door taken before it stood or written inside the shared "
                         "door's own body (the fallback skip takes it for the hand-off): loads %d against writer %d + hand-offs %d"
                         % (g1 - g0, len(self.writer), handoffs))
        d["writer"] = len(self.writer)
        d["writerLoads"] = g1 - g0
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
        self.assertEqual(p1["writer"], 0, "zero plain load_goals in the decision path")
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
        self.assertEqual((p2["loads"], p2["writer"], p2["shared"]), (0, 0, {}), "and neither the counter nor the store's counters move")
        # (a) again with the gate SERVED: the ledger is the tenth keyed file, so its move re-evaluates every session once while
        # the parse and the store stand; the walk loads once per session and the gate not at all
        os.utime(jd.STATE / "auto-nudge.json", (NOW + 8, NOW + 8))
        p3 = self._pass(NOW + 10)
        self.assertEqual((p3["looks"], p3["parses"], p3["skippedParses"]), (2, 2, 0), p3)
        self.assertEqual(p3["walk"], {SID_A: 1, SID_B: 1},
                         "the walk takes exactly one shared load per alive session when its look reaches the store (condition 7, the walk's bound)")
        self.assertEqual((p3["gate"], p3["memo"]), ({SID_A: 0, SID_B: 0}, (2, 0)),
                         "the placement gate is served and makes no currency check (condition 7, the gate's bound)")
        self.assertEqual((p3["loads"], p3["writer"], p3["shared"]), (2, 0, {"hit": 2}), "the counter moves by the walk's two, no writer load, two hits")
        # (b) again
        p4 = self._pass(NOW + 15)
        self.assertEqual((p4["walk"], p4["gate"]), ({SID_A: 0, SID_B: 0}, {SID_A: 0, SID_B: 0}),
                         "the walk takes no shared load on a skipped look, and the placement gate is never reached (condition 7, both bounds)")
        self.assertEqual((p4["skippedParses"], p4["loads"], p4["shared"]), (2, 0, {}))
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
                         "the placement gate, per session: the moved parse derives once and checks once, the skipped session not at all (condition 7, the gate's bound)")
        self.assertEqual((p5["loads"], p5["writer"], p5["shared"]), (1, 0, {"hit": 2}), "the walk's one and the gate's one, both hits")
        for name, p in (("p1", p1), ("p2", p2), ("p3", p3), ("p4", p4), ("p5", p5)):
            for sid in SIDS:
                self.assertLessEqual(p["walk"][sid], 1, "%s %s: the walk takes at most one shared load per alive session per pass (condition 7, the walk's bound)" % (name, sid[-4:]))
                self.assertLessEqual(p["gate"][sid], 1, "%s %s: the placement gate checks at most once per derived session (condition 7, the gate's bound)" % (name, sid[-4:]))
            self.assertLessEqual(sum(p["gate"].values()), p["memo"][1],
                                 "%s: the gate's checks never exceed its derives (condition 7, the gate's bound; a derive without a cached parse "
                                 "checks nothing)" % name)
            self.assertEqual(sum(p["gate"].values()), p["memo"][1],
                             "%s: equal here because the harness's parsed_session records every parse in jd._PARSE_CACHE, so every derive "
                             "holds its parse and checks once; the gate's rule is the bound above" % name)
            self.assertEqual(p["sweep"], {}, "%s: the fixture ledger holds no wake record, so the wake sweep reads no store" % name)
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
        is journaled as a walk gate, a write into the ledger that moves every session's key once, so the skip comes on the
        third pass, with no load on the second either."""
        km._session_working = lambda turns: True
        p1 = self._pass(NOW)
        self.assertEqual((p1["looks"], p1["parses"], p1["skippedParses"]), (2, 2, 0), p1)
        self.assertEqual(p1["walk"], {SID_A: 0, SID_B: 0},
                         "the walk takes no load on a look a state gate ends before the store read (condition 7, the walk's bound)")
        self.assertEqual((p1["gate"], p1["memo"]), ({SID_A: 0, SID_B: 0}, (0, 0)),
                         "and the placement gate, never reached, checks nothing (condition 7, the gate's bound)")
        self.assertEqual((p1["loads"], p1["writer"], p1["shared"]), (0, 0, {}), "no counter and no store counter moves")
        for sid in SIDS:
            self.assertEqual(self._row(sid)[-1], "working", "the verdict recorded, file-keyed, for %s" % sid[-4:])
        p2 = self._pass(NOW + 5)
        self.assertEqual((p2["looks"], p2["parses"], p2["skippedParses"]), (2, 2, 0),
                         "the first pass journaled each verdict as a walk gate (_put_walk_gate, a write-on-change into the ledger, the "
                         "tenth keyed file), so the second pass re-evaluates every session once")
        self.assertEqual((p2["walk"], p2["gate"], p2["loads"]), ({SID_A: 0, SID_B: 0}, {SID_A: 0, SID_B: 0}, 0), "and loads through neither")
        p3 = self._pass(NOW + 10)
        self.assertEqual((p3["skippedParses"], p3["walk"], p3["gate"], p3["loads"]), (2, {SID_A: 0, SID_B: 0}, {SID_A: 0, SID_B: 0}, 0),
                         "the gate rows stand: skipped, and still no load through either")
        for name, p in (("p1", p1), ("p2", p2), ("p3", p3)):
            self.assertEqual(p["sweep"], {}, "%s: the fixture ledger holds no wake record, so the wake sweep reads no store" % name)


class TheSweepIsItsOwnBoundedReader(_WalkHarness):
    """The wake sweep reads the store once per wake record it owns per pass, keeps no memo, and is counted apart from the
    walk and the gate. One wake record for SID_C, a sid that is never alive (so never walked: the sweep's original
    constituency), goes into the ledger before the first pass; the two alive sessions run their first pass as in the first
    case, and the sweep takes exactly one shared load for SID_C on that pass and again on the skip pass. With a store whose
    nodes lack the goal, the read is followed by the inert-record continue (no parse, no writer load, nothing sent). With
    no store file, the shared door falls back into load_goals: one logical read, recorded once by the shared recorder as
    the sweep's and never as a writer call. Not the wedge-gate recipe (an api-error gate on an alive sid with a live
    record): past the read that sweep reaches _mark_nudge_failed, which loads through the writer door and stamps a failure."""

    def _seed_wake_record(self, store_file):
        """One owned wake record for SID_C in the ledger (the toggle stays off), and its store: with `store_file`, a store
        whose nodes lack the goal; without, no file at all."""
        (jd.STATE / "auto-nudge.json").write_text(json.dumps({"enabled": False, "nudged": {
            SID_C + ":g1": {"wake": True, "at": NOW - 2 * H, "count": 1, "lastTurnId": "t1"}}}))
        km._autonudge_cache.clear()
        self.owned_records = {SID_C: 1}
        if store_file:
            (jd.GOALDIR / (SID_C + ".json")).write_text(json.dumps(
                {"rompUuid": SID_C, "seq": 1, "placements": {}, "status": {}, "nodes": {}}))

    def _one_sweep_load(self, p, name):
        self.assertEqual(p["sweep"], {SID_C: 1},
                         "%s: the sweep takes exactly one shared load for the one record it owns, and none for the walk's sids" % name)
        self.assertEqual([(c, f) for _s, c, f, _ln in p["calls"] if c in SWEEP], [("_awaiting_wake_outcomes", KERNEL_FILE)],
                         "%s: the sweep's read is recorded as _awaiting_wake_outcomes's, in the kernel's real file" % name)
        self.assertEqual(p["writer"], 0, "%s: no writer load: the record is inert past the read, and the shared door's fallback into "
                                         "load_goals is the shared door's own read" % name)

    def test_a_store_whose_nodes_lack_the_goal(self):
        self._seed_wake_record(store_file=True)
        p1 = self._pass(NOW)
        self.assertEqual((p1["walk"], p1["gate"], p1["memo"], p1["loads"]), ({SID_A: 1, SID_B: 1}, {SID_A: 1, SID_B: 1}, (0, 2), 2),
                         "the walk and the gate as on any first pass: the record is SID_C's, a sid neither look is about, and the "
                         "counter counts the walk alone")
        self._one_sweep_load(p1, "p1")
        self.assertEqual(p1["shared"], {"hit": 2, "miss": 3}, "the walk's two fills and the sweep's one, the gate's two hits")
        p2 = self._pass(NOW + 5)
        self.assertEqual((p2["walk"], p2["gate"], p2["loads"]), ({SID_A: 0, SID_B: 0}, {SID_A: 0, SID_B: 0}, 0),
                         "the looks skip: nothing of theirs moved")
        self._one_sweep_load(p2, "p2")                    # the sweep keeps no memo: one read per owned record per pass
        self.assertEqual(p2["shared"], {"hit": 1}, "the sweep's read alone, a hit on the store it filled last pass")
        self.assertEqual(self.fb.sent, [], "nothing sent: the node is gone, so the record is inert and the sweep continues past it")

    def test_no_store_file(self):
        self._seed_wake_record(store_file=False)
        p1 = self._pass(NOW)
        self._one_sweep_load(p1, "p1")
        self.assertEqual(p1["shared"], {"hit": 2, "miss": 2, "absent": 1}, "the sweep's read is the absent case: one call, one counter")
        p2 = self._pass(NOW + 5)
        self._one_sweep_load(p2, "p2")
        self.assertEqual(p2["shared"], {"absent": 1})
        self.assertEqual(self.fb.sent, [], "nothing sent: the fresh store has no node for the record")


class TheCountersOneSite(unittest.TestCase):
    def test_the_walk_has_one_shared_load_site_and_the_counter_is_bumped_beside_it(self):
        """A census over the look's own source (the gate decorator unwraps): one shared load by either spelling of the shared
        door (`jd.load_goals_shared` is a prefix of both), counted over non-comment lines, the counter bumped on the line
        after it so the two cannot drift, and the gate around the look reads no store (a skipped look needs no data)."""
        lines = inspect.getsource(km._auto_nudge_session).splitlines()
        at = [i for i, ln in enumerate(lines) if "jd.load_goals_shared" in ln and not ln.strip().startswith("#")]
        self.assertEqual(len(at), 1, "one shared load in the walk's look, by either spelling of the shared door: a second call site is "
                                     "a second load per look (condition 7, the walk's bound)")
        bump = [i for i, ln in enumerate(lines) if '_NUDGE_WALK_STATS["loads"] += 1' in ln]
        self.assertEqual(len(bump), 1, "the counter is bumped once")
        self.assertEqual(bump[0], at[0] + 1, "on the line after the load")
        gated = inspect.getsource(km._nudge_look_gated)
        self.assertNotIn("load_goals", gated, "the gate around the look reads no store: a skipped look loads through neither mechanism")
        self.assertIn("loads", km._NUDGE_WALK_STATS, "the counter is a key of the served block")

    def test_the_replaced_helpers_sources_load_no_store(self):
        """The road limit as a check: the fixture replaces the callables in REPLACED_KM (less the two data names), REPLACED_JD
        and Sessions.backend_for, so a loader planted in any of their real bodies never runs under the harness and the
        execution witness cannot see it; this scan of each real source for either door's name (over non-comment lines) is the
        only witness for those bodies. One level deep, the helper's own source: _session_awaiting reaches two bare-door
        readers (_owned_yield_why and _session_stamp_read) only under stamp=True, which the walk's call does not pass, so
        the walk's road does not reach them; a helper the fixture does not replace is covered by execution instead."""
        targets = ([(k, getattr(km, k)) for k in REPLACED_KM if k not in REPLACED_DATA]
                   + [("jd." + k, getattr(jd, k)) for k in REPLACED_JD]
                   + [("Sessions.backend_for", km.Sessions.backend_for)])
        self.assertEqual(len(targets), 21, "the census covers every replaced callable")
        for label, obj in targets:
            hits = [ln.strip() for ln in inspect.getsource(obj).splitlines() if "load_goals" in ln and not ln.strip().startswith("#")]
            self.assertEqual(hits, [], "%s: a loader planted in a replaced helper never runs under the fixture, so this scan is the only "
                                       "witness for its body: %s" % (label, "; ".join(hits)))


class Docs(unittest.TestCase):
    def test_the_reference_states_condition_7_in_the_jobs_paragraph_and_names_the_counter(self):
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
                      "readers of the same store run on the same pass under their own rules and outside both bounds",
                      "`_wake_goal`", "`_awaiting_wake_outcomes`", "runs after the walk in the same pass, not on it"):
            self.assertIn(words, jobs, "the jobs paragraph states condition 7 per mechanism, scoped to the two loaders it bounds, names "
                                       "the store's other readers on the pass, the counter and this test: %r" % words)
        walk = " ".join(doc[doc.index("`nudgeWalk` is the auto-nudge walk's"):].split())   # wrapped: normalise before slicing
        walk = walk[:walk.index("a memo row is the ten files' stat")]
        self.assertIn("`loads`", walk, "memos.nudgeWalk.loads is named in the walk's entry")
        self.assertIn("bounds two loaders", walk, "and the entry scopes the condition to the two loaders it bounds")
        self.assertIn("a second loader with a bound of its own", walk, "and the entry names the gate's check as the second loader")
        self.assertIn("counted by the test and by no served counter", walk, "and says what counts it")
        for words in ("readers of the same store run on the same pass under their own rules and outside both bounds",
                      "`_wake_goal`", "`_awaiting_wake_outcomes`", "runs after the walk in the same pass, not on it"):
            self.assertIn(words, walk, "and the entry names the store's other readers on the pass, the sweep after the walk: %r" % words)
        gloss = km._PerfStats.__doc__
        field = gloss[gloss.index("nudgeWalk (the auto-nudge walk's"):]
        field = " ".join(field[:field.index("nudgeGate")].split())   # wrapped too
        self.assertIn("loads (the walk's shared goal-store reads", field, "the _PerfStats field docstring names the counter")


if __name__ == "__main__":
    unittest.main()
