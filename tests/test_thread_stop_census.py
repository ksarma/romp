#!/usr/bin/env python3
"""The census of every thread a test starts and HOW its stop is reached, derived by AST over tests/*.py (T282, the stop
shape, 2026-09-21). A thread a test starts must be ended by a construct that runs on EVERY exit path of the test, so a
failed assertion in the body cannot leave it running. This module reads each start, decides what the thread would do
if nobody stopped it (its KIND), reads how the test stops it (its SHAPE), and holds that no thread that would run on
or wait on the test has its stop only on the body's tail.

WHY (the mechanism found on 2026-09-21, romp-manager's verification). tests/test_kernel_parked_ops_liveness.py starts
a REAL kernel judge loop (km._producer) and stopped it on its body's last lines: km._LOOPS_STOP.set(), gate.set(),
km._producer_wake.set(), producer.join(5). Its assertion at the head of the body ("a judge pass is in flight") began
failing when kernel commit 3421c94d0 (2026-09-11) put an 8 s boot hold (BOOT_JUDGE_HOLD_S, _wait_boot_attached) in
front of the producer's first pass, against a test written 2026-09-03 that polled 5 s for the pass. The defect is a
CONDITION, not a frequency: _BOOT_ATTACHED (kernel/kernel.py:30789, set at :30860) is a one-way, process-wide latch,
never cleared, and the test patches km._sdk to lambda: None, so it can never latch it itself; the test passes if and
only if something earlier in the same interpreter already latched it, and fails otherwise after the 8 s hold against its
5 s deadline. Alone serially: always red. The module serially: green (its alphabetically first test's km._pusher_cycle()
reaches _sdk() through _turn_notify_tick and _alive_sessions and builds a real SdkBackend whose boot reconcile latches
it as a side effect). The module under -n 9: red. A full -n 10 sweep: a prior latcher in the target's worker is likely
but not guaranteed: five full sweeps checked on 2026-09-21 did not fire it (those for 853, 862 twice and 887, and 781's
at c7e51ae47), one did (box 2's control at 65f1895f6). An isolated-level certainty and a sweep-level flake at the same
time, decided by which tests ran before it in that worker's process; never in CI (serial). The failed assertion skipped the stop on
the tail, the tearDown only CLEARED the stop flag when the producer was already dead and never SET it, so a live,
fully UNPATCHED judge loop (the with-block's eleven patches were undone on the way out while the producer was still in
its hold) ran for the rest of the worker's life. The T282 census in tearDown named the leftover thread (the "1 error"
beside the "1 failed") but could not stop it.

THE BLAST RADIUS, proven by romp-manager's probe, has TWO FIGURES with different meanings. REACH: the leaked loop runs
_compact_goal_stores() on its 3 s backstop (_producer_wake.wait(3)), globbing jd.GOALDIR and rewriting any store whose
mtime moved; km.jd is the ONE process-wide judge module (kernel/kernel.py:52, jd = load_source("romp_judge", ...): one
object per interpreter; tests/conftest.py's shared-judge note), and the probe counted 141 callers of jd._rebind_state()
among the test modules, so the leaked loop follows jd.GOALDIR to wherever the LATEST rebind put it: any of those 141
scheduled after the failure in the same worker (a store saved under a private sid with a cleared root was archived 7.5 s later by the leaked thread).
VISIBLE SET: 13 modules save stores with cleared roots and 18 assert on the archive; that is where a wrong result would
surface, a SPURIOUS PASS as well as a spurious failure in a module that did nothing wrong, and the spurious pass is the
dangerous direction. 13 is not the exposure; 141 is the reach. NOT DETERMINED, carried and not dropped: whether the
leaked loop produced flakes in earlier sweeps. The contamination disclosure is CONDITIONAL: a sweep carried the leaked
loop only if the target's failure line is in that sweep's pytest log. The SdkBackend
side-effect build is benign on its own (its orphan reap is gated on its own empty registry; sweep_dead_test_roots
removes only romp-tests-* roots whose marker names a dead pid).

THE START SITES. A `.start()` call whose receiver the walk resolves to a Thread or Timer construction: by name, through
an alias (`from threading import Thread as Th`; a module-level or local `Real = threading.Thread`), or of a Thread
SUBCLASS defined in the module or in the function (its run() is what the thread does); chained (`Thread(...).start()`),
through a name bound in the same function (an assignment, a for-target or a comprehension target over a list of such, a
list appended to, an element of a dict or a list assigned by subscript, a conditional expression, a tuple unpacked from
a helper's return), through an attribute bound on self or cls anywhere in the class or a base in the same file, through
a module name, or through a HELPER whose return is such a construction (a module function, a method of the class, a
function of the body, a lambda, a function of a HELPER MODULE under tests/ reached through the imported module
(`git_fixture.spawn()`), the imported name (`spawn()`) or the dotted spelling of a package import (`import
tests.git_fixture` then `tests.git_fixture.spawn()`), or a function of ANOTHER TEST MODULE reached through its import
(`import test_asm_checkpoint as TA`, `TA.kernel_module()`): the target is read where the construction sits). The binding
in force at a start is the last one at or before it (`[... for t in range(8)]` and then `for t in threads: t.start()`
reads the for's), in the start's own scope: a def in the body binds its own names, a use reads its scope and then the
enclosing ones (a closure), and a name a nested def declares nonlocal binds in the NEAREST enclosing function that binds
it (Python's rule: `def outer(): def inner(): nonlocal t; t = Thread(...)` binds the body's t when outer binds no t of
its own), the body's when none does. A receiver
bound to a known non-thread (a mock patcher, a regex match, tracemalloc, an object of a product or library module such
as sb.SdkSession(...), whose start() is its own) is not a thread start; a receiver the walk cannot resolve (a parameter,
a call it cannot classify, a method the class does not define, a product Thread subclass) is UNREADABLE and LISTED,
never passed in silence. A bound `.start` HANDED ON AS A VALUE rather than called (a keyword or positional argument:
tests/test_postal_token.py's `self._load_watched(before=writer.start, ...)`; the value of an assignment or a return; an
element of a list, tuple, set, dict or comprehension; a conditional or boolean expression, a default argument, a yield, an
await or a starred value in such a position) is a start the callee makes on the test's behalf: it is a row like
a call's, classed at the HANDING statement (its kind from the target as usual; its shape from the walk forward from that
statement, whose own text is read first: the `after=lambda: writer.join(timeout=5)` beside it is the join), and one
whose receiver the walk cannot resolve is listed unreadable like a call's. A `.start` in an operand position
(`self.start <= m.start()`, `r.start + 0`: a slice's, a range's or a match's) is a value of some other object and not a
start handed on.

THE KIND of a thread, read from its target: what it does if the test never stops it. THE RULE: EVERY CASE THE WALK
CANNOT READ FALLS TO THE RESTRICTED SIDE, NEVER TO EXCUSED. `bounded` comes ONLY from a body the walk READ and found free
of loops, of untimed waits and of calls of a parameter it has not in hand (the third arm, below), or from a method of the
stdlib the STDLIB_RETURNS table says returns WHATEVER ITS ARGUMENTS
AND ON ANY STDLIB RECEIVER (EMPTY since the ninth pass, 2026-09-22: release, its last entry, moved to the conditioned
names when the refuter showed its reason claimed a receiver read as threading's, multiprocessing's or asyncio's
construction while _library_ctor answers True for a constructor of ANY stdlib module, so a release on a mmap or a sqlite3
connection would have read bounded by name; an entry, should one return, must say so in those words, UNCONDITIONAL_WORDS,
state which receiver classes carry the name and what its arguments do, and a table-shaped test holds every entry to the
words; a name that cannot say it is CONDITIONED instead, STDLIB_CONDITIONED,
checked at the call: time.sleep is bounded only when args= carries a literal number at or under BOUND_S, 5 s;
server_close only when the receiver was constructed as a TCPServer, UDPServer, HTTPServer or ThreadingHTTPServer, a
server with no handler threads to join, since socketserver.ThreadingMixIn.server_close joins live handlers under its
defaults and a ThreadingTCPServer with a handler parked in recv did not return in the runtime probe of 2026-09-22; an
Event's set, clear and is_set only on a threading or asyncio Event() (multiprocessing.Event.set runs
Condition.notify_all's per-sleeper handshake, the argument that dropped notify and notify_all in pass 5 and, re-run over
every entry, moved these three: the `set` entry had said "no stdlib set() blocks"); a queue's put_nowait and get_nowait
only on a queue or asyncio queue, put_nowait also on a multiprocessing.Queue() (a JoinableQueue's put takes a
multiprocessing Condition; a multiprocessing get reads the pipe untimed); the receiver's module read through the
imports (mp.Event(), a bare Event() from either module); a cancel only on a threading.Timer() (it sets the Timer's
finished Event), on an asyncio future, task or handle (cancel schedules the done callbacks through loop.call_soon) or on
a concurrent.futures.Future() the unit registers no add_done_callback on, because concurrent.futures.Future.cancel runs
the done callbacks SYNCHRONOUSLY and a blocking one blocks it (the refuter's probe on round 2 of PR 891, 2026-09-22,
which moved cancel out of STDLIB_RETURNS); a release only on a receiver constructed as a lock, semaphore or condition of
threading or _thread, of multiprocessing's own constructors or of asyncio (RELEASE_RECEIVERS, _release_rule: re-examined
on round 2 the same way as cancel, no release among them runs a caller's callback, and a probe had a Semaphore's and an
asyncio Lock's release with a parked waiter return at once), UNREADABLE on any other stdlib object (a mmap.mmap(), a
sqlite3.connect(): the objects the table's entry excused by name until the ninth pass, since _library_ctor answers True
for a constructor of ANY stdlib module) and on a multiprocessing.managers PROXY, Manager().Lock() / .RLock() /
.Semaphore() / .BoundedSemaphore() / .Condition(), an AcquirerProxy, whose release is a synchronous round trip to the
manager process, blocked while that process is stopped or busy, the probe of 2026-09-22 on round 2 of PR 891's review,
alive after 1 s with the manager SIGSTOPped and a BrokenPipeError after shutdown; the walk reads such a proxy as an
object it does not read and never through the tables, because its construction is a method's result and not a stdlib
constructor (_library_ctor, _library_made), and a plant holds a proxy Lock's and Semaphore's release, a proxy Event's
set, clear and is_set and a proxy Queue's put_nowait and get_nowait each unreadable and LISTED, through the module, an
import alias, a bare Manager, a manager bound to a name, a with-as manager, a chained call and a SyncManager, whose own
start() the walk lists as an unreadable receiver too, and a mmap's and a sqlite3 connection's release unreadable and
listed; and a Timer is bounded only for a literal interval at or under
the same bound, whatever its function does; each otherwise UNREADABLE); the name rules (serve_forever, an untimed wait, a read) classify the other way, to loop or
waits; a target the walk cannot read is UNREADABLE, never bounded, and its tail-only stop is listed with the unreadable
receivers (the pin asserts that bucket empty; ALLOW may excuse one by name with its reason). A structural test hands
_kind a table of unknown targets, and of bodies whose work is a call of a parameter, and asserts none reads bounded;
another asserts every bounded row of the tree carries a read-body reason. The bodies the walk reads: a function of the test module (a def of the body, a module function, a
lambda, a name bound to one, a for-target over a tuple of them: each read, joined on the restricted side); a METHOD of
a class of the test module, reached through an instance (`f.run`, `self.fake.run`, `_Fake().run`, an element of a list
of fakes: `for f in fakes`, `fakes[0].run`, `self.fakes[0].run`; the `as` name of a `with` over one whose __enter__
returns self), through the class (`_Child._pump`, its instance the first of args= when that is a name; a @staticmethod
has no instance; a @classmethod's cls is the class), or through a lambda that calls one (`lambda: f.run()`): read by the
method's body, found in the class or a base in the module, whatever the method is called, in the CLASS'S OWN unit, so
its `self.x()` is the class's x and not the test's (a `run` that delegates to `self._pump()` reads _pump's loop); a
fake's `self.go` (a classmethod's `cls.go`) is the test's `f.go` / `self.fake.go` / `_Cls.go` for the release and stop
rules below, and nothing when the fake is constructed inline; a method handed an instance the walk cannot write as a
name (`args=(*kids,)`, a literal, a lambda) is UNREADABLE, and the name it would have synthesised is never parsed (the
parse of one that is a name chain is guarded, so no synthesised text can raise out of the census); a Thread subclass's
run() (the construction's target when it has none); the def or lambda a helper of the test returns (`wrap(i, fn)`); a
PRODUCT function (kernel/, postal/, cli/, the bin scripts: _Product), reached through a product module (km, sb, jd, pm,
em, cb: a module-level name bound to load_source(...), to a call returning one (TA.kernel_module()), to an attribute of
one (jd = km.jd) or imported from another test module; a local so bound; an import from those directories) as
`km._push_all`, or as a method of a product object (`be._boot_reconcile`, be bound to sb.SdkBackend(...), to a helper
returning one, or unpacked from one's tuple): the module-level functions of that name, or the method of that class in
its file, else every product function of that name, each read in its own module's unit and joined on the restricted
side (any loop is a loop, else any waits, else bounded: read). A body read is read for its own whiles, iter(f, sentinel)
loops, untimed waits, reads and serve_forever calls and, one level down, for the bodies of the fakes' methods, the
class's own methods, the module's and the body's functions and the product functions it calls; a call it does not
resolve (a library's) is not followed. A parameter target of a helper (`_build_on(self, runner)`) is
read at each CALLER from the argument handed in, in the caller's unit (a lambda's body, a def), and is unreadable in
the helper's own row. THE THIRD ARM (romp-manager's ruling, 2026-09-22: the rule named unknown TARGETS; the property is
an unknown DECIDER, wherever it sits): a body the walk read whose WORK is a call of a parameter, of a callable attribute
of one or through a parameter's method (`fn()`, `fn(*a)`, `obj.frob()`, `obj.a.b()`: _opaque_calls, the parameters of the
def or lambda read, of the defs nested in it and of the helper it closes over; self and cls are not parameters here) is
UNREADABLE in that row, never bounded, and READ where the argument is in hand (`given`, a HAND: the argument, the unit it
is written in and where it was handed): at the caller of the helper (`_run(fn)` starting `go`, whose `fn(*a)` is the
caller's `km._retry_parked_creates`, a product function read in its module; `park(self, fn)`; `_race(self, loop_side,
kernel_side)`), at the construction (`Thread(target=run, args=(km._dismiss_lane, SID4))` for a `run(fn, arg)` that calls
fn; a method's self and an unbound method's instance are not parameters' values), or at the call of a function whose body
the walk reads (a def of the body, a module function, a fake's method, a product function: `jd._run_tier(build, ...)`
calls its fn), through a chain of such hands (`_build_on`'s caller lambda `lambda build: jd._run_tier(build, ...)`
receives the construction's `lambda: la[0]` as build, which _run_tier calls as fn: read to its end). The argument in hand
is read as a target is (a lambda's or a def's body, an attribute as a fake's method, a product function or a stdlib
method: _attribute_kind); a constant (`before=None`, a default) is no callable to run, the call, if it happens, raises
at once and the thread ends; the row's reason carries each hand after ` | ` (`fn of _run is `_once` handed in by the
caller`). A METHOD called on a parameter (`s._connect_landed()`, `e.stat()`, `p.read_text()`) is read on the hand, the
attribute over the argument as written: a fake's method by its body, a product object's method in its module, a stdlib
object's by the tables, and UNREADABLE for an object the walk does not read (a dict, a path, a scandir entry: `e.stat`
is a method of a scandir() the walk has no rule for). The scan reads what RUNS when the body runs: a def or a lambda the
body only defines is read where it is called (a def or a name-bound lambda the body itself calls, with that call's
hands; a returned one where its caller runs it: a decorator factory's wrapper, _stage_marked's `marked`, calls its fn
when the decorated function is called; a helper's returned `go` runs on the thread its caller starts), and one handed to
a library call (`sorted(rows, key=lambda r: r.get("t"))`) is inside a call the walk does not follow, a stated limit. A
helper whose caller is itself a helper (`_hammer(fn)` calling `_run(lambda: [fn() ...])`), when the row at that
caller is tail-only and of a pinned or unreadable kind, is classed at the caller's own callers with both levels' hands
(two levels, no further). Among the verdicts of one body a loop or a waits outranks an unreadable (both restricted: the more specific
one names the row). What no hand supplies (a parameter of the caller itself beyond those two levels, an argument behind
a *, a nested def's parameter the body itself calls) stays UNREADABLE and is listed when its stop is tail-only. A hand
supplied at the caller is read in the caller's row only: the helper's own row keeps the unreadable kind.
  loop:    it runs until told: serve_forever / run_forever by name; a body with a `while` (a `while` bounded by a clock
           reading, in its test or by an `if <clock>: break` in its body, is not one; a `while True` that searches local
           data IS one to the walk, which cannot tell it from a spin on a flag: tests/test_view_deltas.py's _py_maps
           positional-key search was one until 2026-09-22, when it became `for n in range(n, n + len(items) + 1)` with
           the same break, bounded, equivalent to the while on 20000 random payloads, and the ALLOW entry that had
           excused it was deleted), or that iterates
           `iter(f, sentinel)`, or that calls a function with one. A loop found in a PRODUCT function a callee reached
           (run -> em.hydrate; km._git_branch -> _tree_of -> _dotgit_on_chain; be.send -> _registry_queue_entries) is
           INDIRECT evidence the walk cannot weigh (the product loop may well return: a walk over data, a retry with a
           bound), so for the timed-join rule below such a thread is read as bounded, while its tail-only stop is still
           pinned; a product function whose OWN body has a `while` (km._producer, _pusher, _heartbeat, _jobs_loop,
           _ws_sender, _apply_pending_ops, pm._heartbeat_loop) is a loop outright, by name (product_loops) or by its body.
  waits:   it blocks until the test releases it: the target is an untimed Event.wait / Lock.acquire / Queue.get / join /
           Future.result or a read (recv, accept, readline, read), by name or in a body the walk reads with no timeout
           (km._login_reader -> _login_reader_loop reads a pty: waits; a test's `self.post()` helper reading its HTTP
           response: waits; a body waiting on `ex.submit(...).result()` for a pool it started: waits, round 2 of PR 891's
           review, 2026-09-22).
           UNTIMED is no arguments or only the spellings Python reads as untimed (_untimed_call): q.get(True),
           q.get(block=True), ev.wait(None), ev.wait(timeout=None), lk.acquire(blocking=True), t.join(None), fut.result(None), in the body
           or through the construction's args= / kwargs=, and the spellings Python reads the same way (a nonzero number
           as the block flag: q.get(1), lk.acquire(1); an acquire's timeout=-1; arguments the walk cannot read, *a /
           **kw); a name or a number as the TIMEOUT is a timeout to the walk (ev.wait(deadline) reads timed).
  bounded: a body the walk read with no loop, only timed waits and no call of a parameter the walk has not in hand (a
           hand read bounded is one), a stdlib call the table says returns, a Thread with
           no target (the default run() does nothing). Such a thread ends on its own whatever the test does, within its
           own bound, so its join is a convenience of the body and not the stop; the shape rule BOUNDED excuses it, with
           this as the reason. What the read does not see: a body that blocks in a lock (`with lock:`), in a call the
           walk does not follow (a parameter's, a library's, a product callee two levels down), or in a product function
           the test REBOUND (tests/test_post_push_coalescing.py's `km._push_all = slow_build` is read as the product's);
           the runtime oracle, tests/conftest.py's thread_census and wait_for_census in a module's own teardown, catches
           those only in the modules that call it: 5 test modules at this head (of the modules the census reads, a count
           the table prints; 2026-09-22: test_codex_backend, test_heartbeat_thread, test_kernel_parked_ops_liveness,
           test_kernel_remote_ws_proxy, test_model_live_midturn; this module's only mention is this sentence), a figure the
           census derives from the imports and calls (census's extras["oracle"]), the table prints and a tree test holds
           this sentence to.
  unreadable: a target the walk cannot read: a parameter in the helper's own row, a body whose work is a call of a
           parameter no hand supplies (the third arm), a function of a module it does not
           read (a third-party import), a stdlib function or method with no STDLIB_RETURNS entry (a shutdown blocks until
           the serve loop ends; a put can block on a full queue) or whose CONDITIONED check fails at the call
           (time.sleep(3600), server_close of a ThreadingTCPServer, set of a multiprocessing.Event(), release of a
           mmap.mmap() or a sqlite3.connect(), cancel of a concurrent.futures.Future() with an add_done_callback on it or
           of a pool future, a Timer(3600, ...)), a
           method of an object the walk does not read (release, set or put_nowait of a Manager proxy: the tables are
           never consulted for it), a
           method run on an instance it
           cannot name, a product
           attribute no product function defines, a callable built by a call it does not read (functools.partial(f),
           factory()), a target hidden in * / ** arguments, any other expression (an element of a list, a conditional).
           Read as a loop for the timed-join rule; a tail-only stop of one is listed in the unreadable bucket.

THE SHAPE of the stop, read in this order; the first match names it. The walk forward from a start reads the
statements that follow it (climbing out of the for, the comprehension or the with that did the starting) up to the
FIRST ASSERTION (self.assert*, self.fail, a bare assert, a raise): a statement that is not an assertion is taken not to
fail, and the shape this census forbids is a stop that stands BEHIND an assertion, the shape that leaked.
  finally: the start is inside a try body that has a finally, or the walk forward meets such a try before any assertion
    (start, then `try: ... finally: stop`, the contextmanager idiom).
  cleanup-before-start: a cleanup (addCleanup, addClassCleanup, addfinalizer, addModuleCleanup, or a registrar handed in
    as a parameter whose name says cleanup) that names a stop OF THIS THREAD: its text, or the body of the local
    function, the lambda or the method of the class it names, has a stop (an attribute or call of join / set / shutdown /
    stop / close / cancel / terminate / kill, the loops' seam _LOOPS_STOP, a name one of whose WORDS, split on `_` and
    on case, is stop / end / close / shutdown / cancel / join / release: `stop_all`, `endWorker`; not `pending`, `send`,
    `append`, `render`, `calendar`, which only hold one as a substring) AND
    mentions the thread: its receiver (and the attribute or holder behind `self.x` or `h[k]`), the list a for-target
    iterates, what its target waits on or polls, its target and the object the target runs on (srv for
    srv.serve_forever), the names handed to it through args= / kwargs= (an Event a product loop is given), the loops'
    seam for a loop outside the module, or the attribute on self that holds it. A cleanup that stops another thread
    excuses nothing about this one: setUp's addCleanup(self.srv.shutdown) covers the server's serve_forever thread and no
    other start in the class. Registered at or before the start in the same function or in the class's setUp. unittest
    runs cleanups after tearDown, LIFO, on every exit path. THE HELPER ROAD (round 2 of PR 891's review, 2026-09-22): a
    cleanup that runs a function of a HELPER MODULE under tests/ (`self.addCleanup(join_started, release, ts, 5)`; a
    lambda, a local function or a method that calls one; the imported name, the imported module or the dotted package
    spelling) is read by that function's BODY through the import, with its parameters standing for the arguments the
    call handed (_helper_bodies, _bound_body: positional, keyword or default; a parameter handed the constant None
    applies no verb, so `release.set()` for release=None is no release), one level down: tests/thread_ends.py's
    join_started sets the release and joins each started thread of the list it is handed, so a cleanup that hands it
    the list is a stop that names the list (its body's for-join) and, when the release is an Event, a release of it;
    a helper whose body joins a list the cleanup did not hand it, or only timed-joins an outright loop, is no stop.
    The name rule (a bare name that says stop) stands only for a callable whose body the walk has not: with a helper's
    body in hand the body decides. THE TIMED-JOIN DECISION for cleanups (round 2 of PR 891's
    review, 2026-09-22; a rule each way, stated here): for a LOOP the walk read OUTRIGHT (kind loop, not a loop found
    only in a product callee) a cleanup whose only stop is a TIMED JOIN (`self.addCleanup(t.join, 10)`, `lambda: [t.join(2)
    for t in ts]`) is NOT the stop, the body rule below applied to cleanups: the join runs on every exit path but the loop
    outlives its bound and runs on, so the cleanup must also set, release, shut down, cancel or close something the thread
    watches, put the sentinel into the queue it reads, set the loops' seam, or join untimed (the strict probe found three
    such sites, all in tests/test_ws_send_bounded.py: a sender cleanup that already put the sentinel, and two socket
    drains, whose cleanups now shut the socket down first). For a thread of UNREADABLE kind the cleanup's timed join IS
    accepted as its stop, THE DOCUMENTED ACCEPTANCE: the walk cannot show the thread loops (its work is a call it cannot
    read, most often a handed-in function bounded by construction, so there is no loop to release), the cleanup runs on
    every exit path, including one where a statement the body walk takes not to fail raises, and bounds the test's wait;
    whether the thread ended within the bound is the runtime oracle's to say. The body rule stays strict for both kinds
    because a body statement's guarantee rests on the walk's assumption that nothing before it fails and a cleanup's on
    unittest: the two rules differ by the strength of the guarantee, not by the thread. For a bounded thread the join is
    a convenience either way (the bounded rule).
  cleanup-before-first-assertion: such a cleanup registered by a statement the walk forward meets before any assertion
    (`Thread(target=srv.serve_forever).start()` then `self.addCleanup(srv.shutdown)`).
  stop-before-first-assertion: the walk meets the stop itself before any assertion, in the start's own statement first
    (`t.start(), t.join()` in one) and then forward: a join of the same receiver or the same list (`for t in ts:
    t.start()` then `for t in ts: t.join()`), a shutdown / stop / cancel of it or of the object the target runs on
    (srv.shutdown() for srv.serve_forever; loop.stop handed to call_soon_threadsafe), a set or release of what the thread
    waits on or polls (`go.set()`), a shutdown of the socket it reads (`peer.shutdown(socket.SHUT_RDWR)` for a drain parked
    in peer.recv()), a sentinel put into the queue it reads or was handed (`q.put_nowait(None)` for km._ws_sender), or the
    loops' seam set for a loop outside the module (km._LOOPS_STOP.set() for
    km._producer). A TIMED join of a loop thread (or of one of unreadable kind) is a wait the loop may outlive, not its
    stop: alone it is passed over,
    and the walk goes on to a release, a shutdown or the seam; an untimed join counts (a loop that did not end would
    hang the test, loudly).
  class-hook: the thread, the object its target runs on (target=self.srv.serve_forever), a local receiver the body
    stores on self (self.loops.append(loop)), or the attribute a helper's result is assigned to (self.bus = _serve(...))
    is on self or cls, and a hook of the class or a base in the same file (tearDown, tearDownClass, a cleanup registered
    in setUp or setUpClass, tearDownModule) applies a stop verb to it, as a call or as a callback handed over
    (loop.call_soon_threadsafe(loop.stop)), or sets _LOOPS_STOP.
  object-owned: the start is in a method of a fake (a class that is not a TestCase), and the class has an end method
    (close, stop, shutdown, __exit__, end, drain, terminate, kill) that applies a stop verb: the fake owns its thread and
    ends it when the test ends the fake. The second hop, that every test ends the fake on every path, is not read here.
  allowlisted: an entry in ALLOW, one site each, with its reason; an entry that matches no tail-only site is STALE and
    fails the census, so the list cannot outlive the sites it excuses. ALLOW is EMPTY BY CONSTRUCTION today (2026-09-22):
    the one entry it carried, tests/test_view_deltas.py:1033's encoder search read as a loop, went with the rewrite of
    _py_maps above. A future entry owes two things, both stated in the entry: a NAMED REASON the walk misreads the site,
    and a FAILURE MODE NO CLEANUP COULD END; the removed entry's reason overstated the second (it called a same-thread
    re-acquire of a plain Lock a deadlock no cleanup could end, but a plain Lock can be released by any thread, so a
    cleanup could have unwedged it). A plant exercises the mechanism on a planted module.
  tail-only: none of the above: the stop, if the body has one, stands behind an assertion. For a loop, a waits or an
    unreadable thread this set is asserted EMPTY (an unreadable one is listed with the unreadable receivers).
A helper that starts a thread and is not itself a test (a `_start`, a `_pass`, a `_wire`) is classed in its own body
first; when its own body has no guarantee, each caller in the same class is classed at its call (a cleanup registered
before the call, the walk forward from the call, the attribute the call's result is stored on against the caller's
hooks), and the site is named at the caller.

WHAT THIS CENSUS DOES NOT SEE. The shape rules read constructs and not their meaning: a cleanup that names the
thread and a stop verb whose stop does not reach it (a set of an event the loop stopped reading), a finally that does
not join, a tearDown or tearDownClass whose only stop of a loop thread is a timed join (the thread is waited for on every
exit path; whether the loop ended within the bound is the oracle's to say: the timed-join rule reads the body's forward
walk and the cleanups, not the class hooks, a stated asymmetry left for a later pass: a probe over the tree on 2026-09-22,
when the cleanup rule went strict for outright loops, found no such hook row; its one candidate, a server thread parked in
accept() whose tearDownClass shuts the listening socket down before its join, is credited once a read's receiver counts as
what the thread waits on), an end method no test calls, are all classed as guaranteed here and caught only by
the runtime oracle. A thread started by code outside tests/*.py is the product's to end, and the census COUNTS the ones it can see
rather than passing them in silence: INFORMATIONAL rows (kind `product-start`, printed by the table with the site and
what starts, their counts asserted by a tree test, NEVER PINNED: no stop judgment is made) for a product object's own
start() (sb.SdkSession(...).start(): the session's thread), for a test's call of a product SPAWN-HELPER (a product
function whose own body constructs and starts a Thread or Timer, derived from the product index, _Product.spawners:
run_pass, helper_key, _handshake, _boot_warm, _push_notify, ...; one whose start sits under `if <parameter>:` is counted
when the argument handed, or the default, is a true literal, and counted as MAY START when it is not a literal:
km._new_ws_client(...) with start_sender defaulting True, sb.SdkBackend(..., reconcile=True)), for
loop.run_in_executor(None, gate.wait) (a worker of the loop's default executor on an untimed wait) and for a
ThreadPoolExecutor (its workers; every one in the tree is under a `with`, which shuts the pool down and joins them on
exit). OUT OF SCOPE, not rows: the two Python heredocs inside tests/romp.bats (a Timer(7.5, os._exit) at :1553 and a
server shutdown thread at :2595, threads of the fake processes the bats tests run) and tests/fixtures/fake_claude.py:192
(a thread inside the fake claude subprocess). A call through an imported name is that module's
object and not a thread of ours (known_non_thread), with the exceptions the walk parses: the HELPER MODULES under tests/
(tests/*.py and tests/fixtures/*.py that are not test modules: helper_modules) and the other TEST MODULES a test imports,
whose functions are read for a returned Thread as a module function's are, so a factory there is a start the census
sees and not a call passed in silence. No helper module returns a Thread at this head (helper_thread_factories() is
empty, pinned by a test; grep finds one Thread construction outside the test modules, tests/fixtures/fake_claude.py:192,
a chained start inside the fake claude the tests run as a subprocess, not a factory). One helper module ENDS threads:
tests/thread_ends.py's join_started(release, threads, timeout), the guarded list join written once (set the release, join
only the threads whose ident is not None: a cleanup registered before a start loop runs on the exit path where the body
failed between two starts, and Thread.join raises on a thread never started), read as a stop through the import (the
helper road above) and run by a nested case in tests/test_codex_backend.py whose planted failure between two starts reds
when the guard is stripped. EVERY cleanup REGISTRATION in the test modules that joins a LIST of threads goes through it, a
property held BY CENSUS and not by grep (round 2 of PR 891's review): list_join_cleanups derives, over every cleanup
registration of every unit (addCleanup, addClassCleanup, addfinalizer, addModuleCleanup, a registrar parameter whose name
says cleanup), the joins whose receiver is an element of what a for or a comprehension iterates, the target itself, an
element of a tuple target or a subscript of the iterated name by the target (`[t.join(5) for t in ts]`, `for t in (a, b):
t.join(5)`, `for i, t in enumerate(ts): t.join(5)`, `ts[i].join()`, guarded or not: the ninth pass widened the shape from a
Name target), in the registration's own arguments or in the body of the lambda, local function, module function or method
it names, and a tree test pins that list EMPTY (before the pin the tree carried ten such joins in five modules, derived by
this function over the tree as it stood: six in tests/test_codex_backend.py, three of them the nested proofs' own, and one
each in tests/test_file_read_memos.py, tests/test_post_push_coalescing.py, tests/test_free_threaded_caches.py and
tests/test_sdk_backend.py, every one now a call of join_started but the second nested case's unguarded contrast, which
joins each of its three callers by index, written out, no loop); a plant reds it on an inline comprehension, a for in a
local def, a for over a tuple, a tuple target over enumerate, a join by index, a method and a module function, and passes
the helper through the registration and through a lambda. The pin covers cleanup REGISTRATIONS, the constructs unittest
runs on every exit path; a tearDown or tearDownClass that joins a list of threads inline is outside it and named here
rather than read: tests/test_heartbeat_thread.py's tearDown (:70) and tests/test_ws_liveness.py's tearDown (:116) join
self.threads inline (the class-hook shape reads those joins for the threads stored on self, not the list-join pin). The
helper module is not in the population, so its own for-join is the one place the shape lives. The fakes' roads have edges the
walk states rather than reads: `self.fake` bound to two classes across the class reads the first (class_bindings); a
class of the module shadows a local of the same name (class_named); a fake's release and receiver names (`self.go`,
`self._srv`) are read from the target method's own body, not from the methods it delegates to (its KIND follows the
delegation, its names do not); a product function defined in several files is read in all of them and joined; a product
method not on the object's class in its file is read by name across the product; a product attribute the test REBINDS
(`km._push_all = slow_build`, mock.patch.object) is read as the product's. THE TEXT of a target the table shows, an
ALLOW entry is keyed on and a plant compares is the SOURCE SEGMENT of the expression as the author wrote it, whitespace
collapsed (_text), never ast.unparse, a renderer whose spelling differs between interpreters (Python 3.10 writes
`lambda : f()`, 3.12 `lambda: f()`); ast.unparse is used only where two texts it rendered under ONE interpreter are
matched against each other (UNPARSE_ROADS names every such function with its reason, and a test parses this module to
assert there is no other). THE POPULATION is the non-recursive listing of tests/test_*.py (module_paths), a count with ONE
HOME, the table the census prints: NO LITERAL MODULE COUNT stands in this docstring, in the oracle bullet's denominator
above, in tests/test_kernel_parked_ops_liveness.py's docstring or in the ledger entry, and a tree test pins the absence over
those THREE HOMES, the prose that carried the figure (romp-manager's ruling on the ninth pass, 2026-09-22: CI tests a pull
request's MERGE with main, so a docstring pinned to the count read went red the day main gained a test module, and would
every time; the oracle's own figure beside it stays pinned to the derivation; the ninth pass's pin read this docstring
alone, the tenth's reads the three, the reviewer's ruling of 2026-09-22); tests/conftest.py,
tests/__init__.py, the helper modules under tests/ and tests/fixtures/ are read only for a returned Thread
(helper_modules). The listing is
what pytest collects under tests/ only while two things hold, both PINNED by a tree test
(test_the_population_is_what_pytest_collects_under_tests, romp-manager's ruling of 2026-09-22): this repository has no
pytest configuration (no pytest.ini, setup.cfg, tox.ini or pyproject.toml at the root or under tests/, where pytest's
inifile search for `pytest tests/` starts; tests/conftest.py names no python_files), so
pytest's defaults apply, `test_*.py` AND `*_test.py`, recursively; and no `*_test.py` exists anywhere under tests/ and
no `test_*.py` below its top level, so those defaults collect exactly this listing. The day one appears the pin says
so, instead of the census omitting it in silence. Run the module
directly for the table (`--table`; `--tail` prints only the tail-only and unreadable rows).

HOW THE TREE IS READ ONCE (the ninth pass, 2026-09-22: CI's 3.10 and 3.11 cells had been cancelled at their 25-minute cap
with this module's serial cost in them). Every file the census reads, a test module, a helper module, a product file, goes
through tests/parse_cache.py, ONE PARSE PER FILE PER PROCESS (keyed on the file's realpath and its size, mtime_ns, inode and
ctime_ns, under the helper's one lock; one module
object every census in the process shares, imported as `from . import parse_cache` under pytest, where tests/ is a package,
and as `import parse_cache` when this module runs as a script), and the whole derivation over the tree, the product loops
and thread classes, the helper modules, the product index, every module's units, the rows, the informational rows, the
oracle modules and the inline list joins in the cleanups, is ONE value built once per process (_Tree, behind
parse_cache.derived's TREE_KEY: tree_census), which setUpClass, the --table road and the list-join pin read. A tree test
pins the MECHANISM through the helper's counters, not the seconds: the entry point run again builds nothing, every module
of the population and every product file was parsed once, the parse count over the population is the module count, and a
second derivation reds (a planted key beside the census's shows it). The cache is per PROCESS: under pytest-xdist the
censuses that land on different workers parse and derive on their own, and no saving is claimed there; the saving is the
serial cell and this module's own tests. A second census in the same process that reads kernel/kernel.py or another
product file through the helper gets this census's parse (a tree test holds that from this side).

"""
import ast
import builtins
import collections
import copy
import os
import re
import shutil
import sys
import tempfile
import threading
import time
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
if __package__:                                   # under pytest tests/ is a package: THE SAME parse_cache module object every
    from . import parse_cache as PC               # census in the process shares (one parse per file, one derivation per key)
    from .thread_ends import join_started         # the one cleanup shape for the threads ParseCacheKeyAndLock starts
else:                                             # `python3 tests/test_thread_stop_census.py --table`: a script, the module by name
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import parse_cache as PC
    from thread_ends import join_started

THREAD_CTORS = ("Thread", "Timer")
STOP_VERBS = ("join", "set", "shutdown", "stop", "close", "cancel", "terminate", "kill", "server_close", "release")
STOP_SEAM = "_LOOPS_STOP"
STOP_WORDS = ("stop", "end", "close", "shutdown", "cancel", "join", "release")
CLEANUP_NAMES = ("addCleanup", "addClassCleanup", "addfinalizer", "addModuleCleanup")
HOOK_NAMES = ("setUp", "tearDown", "setUpClass", "tearDownClass", "setUpModule", "tearDownModule")
OWNER_ENDS = ("close", "stop", "shutdown", "__exit__", "end", "drain", "terminate", "kill")
BLOCKING = ("wait", "acquire", "join", "get", "result")  # untimed with no arguments or the untimed spellings (_untimed_call)
UNTIMED_KEYWORDS = {"block": True, "blocking": True, "timeout": None}   # the keyword spellings that mean untimed
BOUND_S = 5.0                    # the stated bound: a literal time.sleep argument or Timer interval at or under it is bounded
PRODUCT_START = "product-start"  # the kind of an INFORMATIONAL row: a thread the product starts on a test's call, never pinned
POOL_CTORS = ("ThreadPoolExecutor", "_TimedPool")                        # judge.py binds ThreadPoolExecutor to its _TimedPool
ORACLE_NAMES = ("thread_census", "wait_for_census")                      # tests/conftest.py's runtime oracle
BUILTIN_METHODS = ("append", "extend", "add", "update", "get", "put", "pop", "setdefault", "insert", "remove", "discard",
                   "clear", "copy", "keys", "items", "values", "sort", "reverse", "index", "count", "join", "split", "strip",
                   "format", "encode", "decode", "write", "read", "flush", "set", "wait", "acquire", "release", "is_set", "start")
ASSERTS = ("fail", "failIf", "failUnless", "skipTest")
READS = ("recv", "recv_into", "recvfrom", "accept", "readline", "read")
FOREVER = ("serve_forever", "run_forever")
CLOCK = re.compile(r"\btime\.|monotonic|perf_counter|deadline|thread_time")
PRODUCT_DIRS = ("kernel", "postal", "cli")
KINDS_PINNED = ("loop", "waits")
KIND_UNREAD = "unreadable"       # the kind of a target the walk cannot read: never excused, listed unless its stop is guaranteed
# Methods of a stdlib object (a Timer, a Lock, a Future built through a stdlib module) that return on their own WHATEVER
# THEIR ARGUMENTS AND ON ANY STDLIB RECEIVER, by name, each with a reason that says so in those words (UNCONDITIONAL_WORDS;
# stdlib_table_problems holds every entry to them, asserted by a test) and states its RE-EXAMINATION of 2026-09-22
# (romp-manager's ruling on round 1 of PR 891: which receiver classes carry the name, and what its arguments do). A name
# that cannot say that is CONDITIONED instead (STDLIB_CONDITIONED, below its checkers, each reading the receiver's
# construction or the call: time.sleep on a literal argument at or under BOUND_S; server_close on a server with no handler
# threads to join; an Event's set, clear and is_set and a queue's put_nowait and get_nowait on the receiver's module; a
# cancel on the receiver's construction and, for a concurrent.futures.Future, on the unit's add_done_callback calls; a
# release on the receiver's construction, a lock, semaphore or condition of threading, multiprocessing or asyncio) or
# dropped. Any other method of a stdlib object used as a target is UNREADABLE (a shutdown blocks until the serve loop
# ends; a put can block on a full queue; a wait with a timeout is a wait the walk has no rule for).
# EMPTY since the ninth pass (2026-09-22): release, its last entry, moved to the conditioned names when the refuter showed
# that the entry's reason ("on any stdlib receiver the walk reads as a stdlib construction, threading's, multiprocessing's
# or asyncio's own constructor") claimed more than the walk checked: _library_ctor answers True for a constructor of ANY
# stdlib module, so a release on a mmap.mmap() or a sqlite3.connect() would have read bounded by name. The table stays, with
# its words and its test, for an entry that can say them; none does today.
UNCONDITIONAL_WORDS = ("whatever its arguments", "on any stdlib receiver")
STDLIB_RETURNS = {}
# CONDITIONED on 2026-09-22 (round 2 of PR 891's review, the refuter's probe): cancel, because concurrent.futures.Future.cancel
# runs the done callbacks SYNCHRONOUSLY (_invoke_callbacks) and a blocking add_done_callback blocks it (`fut.add_done_callback(
# lambda f: gate.wait())` then `Thread(target=fut.cancel)`: the thread stays alive; re-run here, alive after 0.5 s), so the
# entry could not say "on any stdlib receiver"; bounded on a threading.Timer(), on an asyncio future, task or handle, and on a
# concurrent.futures.Future() with no add_done_callback on it in the unit (_cancel_rule), UNREADABLE elsewhere (a pool
# future, a sched.scheduler, a receiver the walk cannot name). No tree row used it.
# Dropped on 2026-09-22 (the adversarial review of pass 5): notify / notify_all, because multiprocessing.Condition.notify does an
# untimed _woken_count.acquire() per woken sleeper, so the entry could not say "on any stdlib receiver"; no tree row used them.
# CONDITIONED on 2026-09-22 (round 1 of PR 891's review: the same argument re-run over every entry): set, because
# multiprocessing.Event.set runs that notify_all; clear and is_set, because multiprocessing.Event's take the Condition's lock a
# set() stuck in that handshake holds; put_nowait, because multiprocessing.JoinableQueue.put takes its multiprocessing
# Condition, which task_done's notify_all holds through the same handshake; get_nowait, because multiprocessing.Queue.get(False)
# reads the pipe untimed after its poll. Each is bounded on the receivers its checker names (_event_method_rule,
# _queue_method_rule) and UNREADABLE elsewhere; one tree row uses them, km._LOOPS_STOP.set on the kernel's threading.Event().
_BUILTIN_NAMES = frozenset(dir(builtins))     # range(...), slice(...), object(): a builtin constructs no thread of ours
# Servers whose server_close has no handler threads to join: a plain socketserver / HTTPServer handles in the accept
# thread; ThreadingHTTPServer's handlers are daemon threads, which ThreadingMixIn.server_close does not join. A
# ThreadingTCPServer / ThreadingUDPServer under its defaults (block_on_close=True, daemon_threads=False) joins every live
# handler: a runtime probe on 2026-09-22 had one not return within 2 s with a handler parked in recv.
DAEMON_HANDLER_SERVERS = ("TCPServer", "UDPServer", "HTTPServer", "ThreadingHTTPServer")
# Receivers whose start() is known not to be a thread of ours: a mock patcher (mock.patch, patch.object, patch.dict), a
# regex match (re.finditer / match / search), the tracemalloc module. Any other call the walk cannot read is UNREADABLE.
NON_THREAD_HEADS = ("re", "regex", "tracemalloc")
NON_THREAD_PARTS = ("patch",)
NON_THREAD_ATTRS = ("finditer", "match", "search", "fullmatch", "compile")

# Shapes that are not leaks, excused one site at a time. Key: (file, unit the shape was read in, the target's text);
# value: the reason. Every entry must match a site the walk classes tail-only at this head, or the entry is stale and
# the census is red. EMPTY BY CONSTRUCTION today (2026-09-22): the one entry it carried (tests/test_view_deltas.py:1033,
# an encoder search read as a loop) went when the search became a bounded for. A future entry owes two things, both
# stated in the entry: a NAMED REASON the walk misreads the site, and a FAILURE MODE NO CLEANUP COULD END. The removed
# entry's reason overstated the second: it called a same-thread re-acquire of a plain Lock a deadlock no cleanup could
# end, but a plain Lock can be released by any thread, so a cleanup could have unwedged it.
ALLOW = {}


def _text(node, module):
    """The text of an expression AS THE AUTHOR WROTE IT: its source segment in `module`, whitespace collapsed to single
    spaces (a target spanning lines reads as one line). Every target text the census DISPLAYS, keys an ALLOW entry on or
    compares in a plant comes from here and never from ast.unparse, a renderer whose spelling differs between
    interpreters (Python 3.10 writes `lambda : f()`, 3.12 `lambda: f()`): with the source segment the difference is
    impossible by construction. A node the walk SYNTHESISED over a hand (`s._do_set_mode`, the method a body calls on a
    parameter, written over the argument as the caller wrote it: _given_kind) carries its text as `_shown`, the hand's
    segment and the chain. A node with no segment (none should reach here) reads as its type and position. The segment is
    sliced from the module's lines split ONCE (_segment, _source_lines), the same slicing ast.get_source_segment does over a
    split it repeats per call (on Python 3.10 a per-character loop over the whole file, 5 MB for kernel/kernel.py, for every
    product target or callee the census names: this module's 3.10 cost before the ninth pass, 2026-09-22)."""
    shown = getattr(node, "_shown", None)
    if shown is not None:
        return shown
    seg = _segment(module, node) if module is not None and getattr(module, "src", None) else None
    if seg is None:
        return "<%s at %s:%s>" % (type(node).__name__, getattr(node, "lineno", "?"), getattr(node, "col_offset", "?"))
    return " ".join(seg.split())


_LINE = re.compile(r"[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+\Z")   # a line with its ending, as the parser splits them (a form feed breaks none)


def _source_lines(module):
    """`module.src` split into lines as the parser splits it (on \\n, \\r\\n and \\r, each line keeping its ending), computed once
    per module and kept on it."""
    lines = getattr(module, "_lines", None)
    if lines is None:
        lines = _LINE.findall(module.src)
        try:
            module._lines = lines
        except AttributeError:
            pass
    return lines


def _segment(module, node):
    """What ast.get_source_segment(module.src, node) answers, from the cached lines: the same slicing (a node's column
    offsets are UTF-8 byte offsets into its line), None for a node without positions."""
    try:
        if node.end_lineno is None or node.end_col_offset is None:
            return None
        lineno, end_lineno, col, end_col = node.lineno - 1, node.end_lineno - 1, node.col_offset, node.end_col_offset
    except AttributeError:
        return None
    lines = _source_lines(module)
    if end_lineno == lineno:
        return lines[lineno].encode()[col:end_col].decode()
    first = lines[lineno].encode()[col:].decode()
    last = lines[end_lineno].encode()[:end_col].decode()
    return "".join([first] + lines[lineno + 1:end_lineno] + [last])


# The functions that still call ast.unparse, each with the reason: every one renders a text only to MATCH it against
# another text rendered by the same interpreter (a binding key, a receiver name, a cleanup's words), never to display it,
# key an ALLOW entry on it or compare it in a plant (that is _text's road). A test parses this module and asserts the set
# of functions calling ast.unparse is exactly this one, so a new use must be registered here with its reason.
UNPARSE_ROADS = {
    "_Module.derives_thread": "a base's last dotted part, matched against the module's class names",
    "_Module.bases_of": "a base's last dotted part, matched against the module's class names",
    "_Module.is_testcase": "a base's last dotted part, matched against TestCase",
    "_Unit._bind": "the holder text of an append / += target: the key of appends",
    "_Unit._bind_target": "the text of an attribute or subscript target: the key of a binding",
    "_Unit.known_non_thread": "the dotted parts of a callee, matched against import names",
    "_Unit.method_of": "a base's last dotted part, matched against class names",
    "_Unit.resolve": "the text of a name chain: the key its binding is looked up under",
    "_Unit.thread_of": "the text of a name chain: the key its binding is looked up under",
    "_Start.__init__": "recv_text, the receiver as a NAME matched against join / shutdown receivers (recv_shown is displayed)",
    "_applies_stop": "the receiver a hook applies a stop verb to, matched against the stored attribute names",
    "_body_kind": "a while's test, searched for a clock reading",
    "_body_waits_on": "a wait's receiver, rewritten by _own and matched against a set / release call's receiver",
    "_class_of": "a bound attribute's text: the key of its binding",
    "_cleanup_ends": "a sentinel put's receiver, matched against the names handed to the thread and what it reads",
    "_cleanup_stops": "a cleanup's nodes, searched for the thread's words",
    "_clock_break": "an if's test, searched for a clock reading",
    "_forever_receivers": "a serve_forever's receiver, rewritten by _own and matched against a shutdown's receiver",
    "_handed_names": "the names in args= / kwargs=, matched against a cleanup's text",
    "_hook_stops": "a setUp cleanup's text, searched for the stored attribute names",
    "_method_call": "the owner a fake's self is rewritten to (f, self.fake, child), matched against release texts",
    "_object_of": "a bound attribute's text: the key of its binding",
    "_registers_callback": "a future's receiver, matched against an add_done_callback's receiver",
    "_release_names": "a wait's receiver, matched against a set / release call's receiver",
    "_start_names": "the iterated list's text, matched against a join's receiver",
    "_stop_in": "a call's receiver, matched against the start's names and release names",
    "_stored_attrs": "a holder's text, matched against the attributes on self",
    "_target_receivers": "the target's receiver, matched against a shutdown's receiver",
    "_thread_words": "the words a stop of the thread would mention, matched against a cleanup's text",
    "classify": "the names a caller binds a helper's result to, matched against a cleanup's text",
}


def _callee_name(call):
    f = call.func
    if isinstance(f, ast.Attribute):
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return None


def _names_thread_ctor(node):
    """The expression is threading.Thread / Timer by name: `threading.Thread`, `Thread`, `_real_threading.Timer`."""
    if isinstance(node, ast.Attribute):
        return node.attr in THREAD_CTORS
    if isinstance(node, ast.Name):
        return node.id in THREAD_CTORS
    return False


def _is_thread_ctor(node):
    """A Thread or Timer construction by NAME only (no aliases, no subclasses): the unit-aware check is _Unit.is_thread_ctor."""
    return isinstance(node, ast.Call) and _callee_name(node) in THREAD_CTORS


def _names_timer(node):
    """The expression names threading.Timer by its own name (threading.Timer, Timer)."""
    return (isinstance(node, ast.Attribute) and node.attr == "Timer") or (isinstance(node, ast.Name) and node.id == "Timer")


def _is_timer(call, unit=None):
    """The construction is a Timer: by name, or (with `unit` to read the bindings) through an alias or a Timer subclass
    (_Unit.is_timer_ctor)."""
    return unit.is_timer_ctor(call) if unit is not None else _names_timer(call.func)


def _target_expr(call, unit=None):
    """The callable a Thread or Timer runs: `target=` (or the first positional) for Thread, `function=` (or the second
    positional) for Timer, a Timer being read by name or, with `unit`, through an alias or a subclass (Tm =
    threading.Timer; class T2(threading.Timer))."""
    if _is_timer(call, unit):
        for kw in call.keywords:
            if kw.arg == "function":
                return kw.value
        return call.args[1] if len(call.args) > 1 else None
    for kw in call.keywords:
        if kw.arg == "target":
            return kw.value
    return call.args[0] if call.args else None


def _handed_args(call, unit=None):
    """(the positional argument nodes, the (name, node) keyword pairs) a construction hands its target through args= /
    kwargs= (a tuple or list; a dict with string keys); None when the walk cannot read them (a name, a starred value, a
    ** argument, a positional past the target: a Timer's are interval and function, only a third is the target's; the
    Timer read by name or, with `unit`, through an alias or a subclass)."""
    args, kws = [], []
    for kw in call.keywords:
        if kw.arg == "args":
            if not isinstance(kw.value, (ast.Tuple, ast.List)) or any(isinstance(e, ast.Starred) for e in kw.value.elts):
                return None
            args += kw.value.elts
        elif kw.arg == "kwargs":
            if not isinstance(kw.value, ast.Dict) or not all(isinstance(k, ast.Constant) and isinstance(k.value, str) for k in kw.value.keys):
                return None
            kws += [(k.value, v) for k, v in zip(kw.value.keys, kw.value.values)]
        elif kw.arg is None:
            return None
    n = 2 if _is_timer(call, unit) else 1
    if len(call.args) > n or any(isinstance(a, ast.Starred) for a in call.args):
        return None
    return args, kws


def _untimed_call(name, args, keywords):
    """A blocking call is UNTIMED with no arguments or with only the spellings Python reads as untimed (romp-manager's
    ruling, 2026-09-22): q.get(True), q.get(block=True), lk.acquire(blocking=True) (a true block flag and no timeout or
    timeout=None), ev.wait(None), ev.wait(timeout=None), t.join(None), fut.result(None) (no timeout or timeout=None: a
    Future's result() waits untimed for the pool, round 2 of PR 891's review); and the spellings
    Python reads the same way (the adversarial review of pass 5): a nonzero number as the block flag (q.get(1),
    lk.acquire(1)), an acquire's timeout=-1 (the Lock's own forever), and arguments the walk cannot read (*a, **kw:
    the restricted side). A name or a number as the TIMEOUT is a timeout to the walk: ev.wait(deadline) reads timed, the
    body's excused side, a stated edge. `keywords` are (name, node) pairs; a ** argument has the name None."""
    if any(isinstance(a, ast.Starred) for a in args) or any(k is None for k, _v in keywords):
        return True
    kw = dict(keywords)

    def is_none(node):
        return isinstance(node, ast.Constant) and node.value is None

    def is_on(node):
        return isinstance(node, ast.Constant) and (node.value is True or (isinstance(node.value, (int, float))
                                                                          and not isinstance(node.value, bool) and node.value != 0))

    if name in ("get", "acquire"):
        flag = "block" if name == "get" else "blocking"
        block = args[0] if args else kw.get(flag)
        timeout = args[1] if len(args) > 1 else kw.get("timeout")
        extra = args[2:] or [k for k in kw if k not in (flag, "timeout")]
        forever = timeout is None or is_none(timeout) or (name == "acquire" and _number_literal(timeout) == -1)
        return not extra and (block is None or is_on(block)) and forever
    if name in ("wait", "join", "result"):
        timeout = args[0] if args else kw.get("timeout")
        extra = args[1:] or [k for k in kw if k != "timeout"]
        return not extra and (timeout is None or is_none(timeout))
    return not args and not keywords


def _handed_untimed(ctor, name, unit=None):
    """The target `name` (a BLOCKING method) runs untimed with what the construction hands it through args= / kwargs=:
    nothing, or only the untimed spellings; arguments the walk cannot read are not untimed here (the target then falls
    to the stdlib table or to unreadable, the restricted side)."""
    handed = _handed_args(ctor, unit)
    return handed is not None and _untimed_call(name, handed[0], handed[1])


def _args_text(call, module):
    """The arguments of a call as written: `True`, `block=True`, `**kw`."""
    return ", ".join([_text(a, module) for a in call.args]
                     + [("**%s" % _text(k.value, module)) if k.arg is None else "%s=%s" % (k.arg, _text(k.value, module)) for k in call.keywords])


def _number_literal(node):
    """The number a literal spells (3, 0.5, -1 as a UnaryOp over one); None for anything else (a bool is not one)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        v = _number_literal(node.operand)
        return -v if v is not None else None
    return None


_TOKEN = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+")


def _tokens(name):
    """The words of an identifier, split on `_` and on case boundaries, lower-cased: `endProducer` -> end, producer;
    `_LOOPS_STOP` -> loops, stop; `pending` -> pending."""
    return [t.lower() for t in _TOKEN.findall(name)]


def _says_stop(name):
    """A bare name says stop when one of its WORDS is a stop word (`stop_all`, `end`, `_close_srv`, `endProducer`), not
    when a stop word is merely a substring of one (`pending`, `render`, `send`, `append`, `calendar` say nothing)."""
    return name == STOP_SEAM or any(t in STOP_WORDS for t in _tokens(name))


def _stop_shaped(node):
    """The node (a cleanup's argument, a local function, a lambda) names a stop: an attribute or call of a stop verb, the
    loops' stop seam, or a bare name one of whose words says stop."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Attribute) and sub.attr in STOP_VERBS:
            return True
        if isinstance(sub, ast.Name) and _says_stop(sub.id):
            return True
    return False


def _run_nodes(stmt):
    """The nodes of a statement that run when it does: not the bodies of the functions, lambdas and classes it defines."""
    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return                                          # a definition: nothing of its body runs here
    stack = [stmt]
    while stack:
        n = stack.pop()
        yield n
        for c in ast.iter_child_nodes(n):
            if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                continue
            stack.append(c)


def _returns(fn):
    """The value of every `return` of the function's OWN body (not of the functions it defines)."""
    for s in fn.body:
        for n in _run_nodes(s):
            if isinstance(n, ast.Return) and n.value is not None:
                yield n.value


def _join_kinds(kinds):
    """One answer for a set of element answers: a thread among them makes the whole a thread; an unread element makes it
    unread; all read and none a thread is other; no elements is empty."""
    if "thread" in kinds:
        return "thread"
    if None in kinds:
        return None
    return "other" if kinds else "empty"


def _word_in(word, text):
    """`word` appears in `text` as a whole name (`producer` in `self.producer.join(10)`; not in `_producer_wake`)."""
    return re.search(r"(?<!\w)%s(?!\w)" % re.escape(word), text) is not None


def product_loops(root=ROOT):
    """The name of every function in the product sources whose body has a `while`: kernel/, postal/, cli/ and the bin
    scripts that are files of their own (the rest of bin/ are links into those directories)."""
    names = set()
    for tree in _product_trees(root):
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(isinstance(s, ast.While) for s in ast.walk(n)):
                names.add(n.name)
    return names


def product_thread_classes(root=ROOT):
    """The name of every class in the product sources whose bases name threading.Thread: a construction of one by a test
    (km.Worker(...).start()) is a thread the walk does not read the target of, so it is listed unreadable."""
    names = set()
    for tree in _product_trees(root):
        for n in ast.walk(tree):
            if isinstance(n, ast.ClassDef) and any(_names_thread_ctor(b) for b in n.bases):
                names.add(n.name)
    return names


def _product_trees(root):
    """The tree of every product file (_product_files), each parsed once per process (parse_cache)."""
    for p in _product_files(root):
        try:
            yield PC.source_and_tree(p)[1]
        except (SyntaxError, UnicodeDecodeError):
            continue


def helper_modules(root=ROOT):
    """The modules under tests/ that are not test modules (tests/*.py, tests/fixtures/*.py and deeper; not test_*.py, not
    __init__.py), by the dotted name a test would import them under with the leading `tests.` removed: fs_clock,
    git_fixture, lab_dist, fixtures.fake_claude. A function of one that returns a Thread is read as a module function's
    return is (callee_of), so a factory in a helper module is a start the census reads, not a call passed in silence."""
    out = {}
    tests = os.path.join(root, "tests")
    for dp, dns, fns in os.walk(tests):
        dns[:] = sorted(d for d in dns if d != "__pycache__")
        for f in sorted(fns):
            if f.endswith(".py") and not f.startswith("test_") and f != "__init__.py":
                p = os.path.join(dp, f)
                out[_helper_key(os.path.relpath(p, root)[:-3].replace(os.sep, "."))] = p
    return out


def _helper_key(dotted):
    """`tests.fixtures.fake_claude` and `fixtures.fake_claude` are one module: the key drops the leading `tests.`."""
    return dotted[6:] if dotted.startswith("tests.") else dotted


def helper_thread_factories(root=ROOT, helpers=None):
    """(helper key, function name) for every function of a helper module under tests/ one of whose returns is a Thread /
    Timer construction: the factories a test could start a thread through. None today (2026-09-22)."""
    helpers = helper_modules(root) if helpers is None else helpers
    loops, cache, out = set(), {}, []
    for key, p in sorted(helpers.items()):
        try:
            m = _Module(p, loops, helpers=helpers, helper_cache=cache)
        except (SyntaxError, UnicodeDecodeError):
            continue
        for name, fn in m.functions.items():
            u = m.unit_for(fn)
            if any(u.resolve(v, v.lineno) == "thread" for v in _returns(fn)):
                out.append((key, name))
    return out


class _Product:
    """The product sources (kernel/, postal/, cli/, the bin scripts that are files of their own) indexed for the kind
    reading: every function by name, every class by name, and the _Module of each file built on first use, so a
    target that is a product function (km._push_all, be._boot_reconcile through sb.SdkBackend(...)) is READ in its own
    module's unit and not classed by its name alone. A name defined in several product files is read in all of them and
    the answers joined on the restricted side (any loop is a loop, else any waits is waits, else bounded: read)."""
    def __init__(self, root=ROOT, files=None):
        self.root = root
        self.files = list(_product_files(root)) if files is None else list(files)
        self.functions = {}              # name -> [(path, ClassDef or None, FunctionDef)]
        self.classes = {}                # name -> [(path, ClassDef)]
        self.trees = {}
        for p in self.files:
            try:
                tree = PC.source_and_tree(p)[1]
            except (SyntaxError, UnicodeDecodeError, OSError):
                continue
            self.trees[p] = tree
            holder = {}
            for n in ast.walk(tree):
                if isinstance(n, ast.ClassDef):
                    self.classes.setdefault(n.name, []).append((p, n))
                    for f in n.body:
                        if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            holder[id(f)] = n
            for n in ast.walk(tree):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self.functions.setdefault(n.name, []).append((p, holder.get(id(n)), n))
        self.modules = {}
        self._spawners = None
        self._globals = None

    def spawners(self):
        """{name: [(path, class name or None, FunctionDef, guards)]} for every product function whose OWN body (not the
        functions it defines) constructs a Thread or Timer AND calls a .start(): the SPAWN-HELPERS a test's call runs
        (run_pass, helper_key, _handshake, _boot_warm, _push_notify, _new_ws_client, SdkBackend.__init__). `guards` are
        the (parameter, wanted) pairs of a start under `if <parameter>:` / `if not <parameter>:` (_start_guards)."""
        if self._spawners is None:
            out = {}
            for name, defs in self.functions.items():
                for p, c, fn in defs:
                    nodes = [n for s in fn.body for n in _run_nodes(s)]
                    starts = [n for n in nodes if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "start"]
                    if starts and any(isinstance(n, ast.Call) and _names_thread_ctor(n.func) for n in nodes):
                        out.setdefault(name, []).append((p, c.name if c is not None else None, fn, _start_guards(fn, starts)))
            self._spawners = out
        return self._spawners

    def module(self, path, like):
        """The _Module of one product file (built once), sharing `like`'s loops, thread classes, helpers and product."""
        m = self.modules.get(path)
        if m is None:
            m = self.modules[path] = _Module(path, like.loops, thread_classes=like.product_thread_classes,
                                             helpers=like.helpers, helper_cache=like.helper_cache, product=self)
        return m

    def methods(self, class_name, method, like):
        """[(path, the class that defines it, FunctionDef)] for `method` of the product class `class_name`, in the class
        or a base of it in the same file (nearest first, per definition of the class); [] when none defines it."""
        out = []
        for p, cls in self.classes.get(class_name, []):
            m = self.module(p, like)
            for c in m.bases_of(cls):
                for f in c.body:
                    if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and f.name == method:
                        out.append((p, c, f))
                if out:
                    break
        return out

    def file_named(self, strings):
        """The product file a load_source(...) call names by its string arguments: the one whose basename is among them
        (kernel.py, judge.py, sdk_backend.py), else the real file behind a script named there (bin/romp-judge ->
        kernel/judge.py); False when the strings name an existing file under the root that is NOT a product file
        (tools/loadsource-sweep.py, scripts/restart_metrics_report.py: a load_source the tests make of a tool, whose
        functions are not the product's); None when the walk cannot tell."""
        names = {s for s in strings if s}
        for p in self.files:
            if os.path.basename(p) in names:
                return p
        real = {os.path.realpath(p): p for p in self.files}
        outside = False
        for s in names:
            for d in ("bin", "tools", "scripts", "."):
                cand = os.path.join(self.root, d, s)
                if os.path.isfile(cand):
                    if os.path.realpath(cand) in real:
                        return real[os.path.realpath(cand)]
                    outside = True
            if s.endswith(".py"):
                outside = True
        return False if outside else None

    def file_dotted(self, dotted):
        """The product file an import's dotted name is in: kernel.credentials.helper_key -> kernel/credentials.py."""
        parts = dotted.split(".")
        real = {os.path.realpath(p): p for p in self.files}
        for n in range(len(parts), 0, -1):
            cand = os.path.realpath(os.path.join(self.root, *parts[:n]) + ".py")
            if cand in real:
                return real[cand]
        return None

    def global_value(self, name):
        """The value a product file binds the module-level `name` to (km._LOOPS_STOP is threading.Event()), else None: the
        first construction bound to the name across the product files in order, else the first value (indexed once)."""
        if self._globals is None:
            calls, firsts = {}, {}
            for tree in self.trees.values():
                for n in tree.body:
                    if isinstance(n, ast.Assign):
                        for t in n.targets:
                            if isinstance(t, ast.Name):
                                firsts.setdefault(t.id, n.value)
                                if isinstance(n.value, ast.Call):
                                    calls.setdefault(t.id, n.value)
            self._globals = (calls, firsts)
        calls, firsts = self._globals
        return calls.get(name, firsts.get(name))


def _product_files(root):
    files = []
    for d in PRODUCT_DIRS:
        p = os.path.join(root, d)
        if os.path.isdir(p):
            files += [os.path.join(p, f) for f in sorted(os.listdir(p)) if f.endswith(".py")]
    b = os.path.join(root, "bin")
    if os.path.isdir(b):
        for f in sorted(os.listdir(b)):
            p = os.path.join(b, f)
            if os.path.isfile(p) and not os.path.islink(p):
                with open(p, "rb") as fh:
                    head = fh.readline()
                if head.startswith(b"#!") and b"python" in head:
                    files.append(p)
    return files


class _Module:
    def __init__(self, path, loops, src=None, thread_classes=None, helpers=None, helper_cache=None, product=None):
        self.path = path
        self.loops = loops
        self.product_thread_classes = set() if thread_classes is None else thread_classes
        self.helpers = {} if helpers is None else helpers            # helper key -> path (helper_modules)
        self.helper_cache = {} if helper_cache is None else helper_cache   # path -> _Module, shared across the census
        self.product = product                                        # _Product, shared across the census (None: no product read)
        if src is None:                                               # a file: parsed once per process (parse_cache)
            self.src, self.tree = PC.source_and_tree(path)
        else:                                                         # a planted text: its own parse, never cached
            self.src, self.tree = src, ast.parse(src, path)
        self.classes = {n.name: n for n in self.tree.body if isinstance(n, ast.ClassDef)}
        self.functions = {n.name: n for n in self.tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.globals, self.imports = {}, set()
        self.import_names = {}               # local name -> the dotted name it imports (lab_dist; tests.fs_clock.move_ctime)
        self.thread_aliases = set()          # names bound at module level to threading.Thread / Timer
        self.timer_aliases = set()           # of those, the ones bound to threading.Timer (its callable is function=)
        self.calls_oracle = False            # the module imports or calls the runtime oracle (ORACLE_NAMES), read in this one walk
        self._appends_index = None           # name -> the values .append()ed to it anywhere in the module (appended)
        self._class_attrs = {}               # id(class) -> {attribute: the values bound to <x>.<attribute> in it} (class_attr_bindings)
        self._bases = {}                     # id(class) -> bases_of's answer
        for n in ast.walk(self.tree):
            if not self.calls_oracle and ((isinstance(n, ast.alias) and n.name in ORACLE_NAMES) or (isinstance(n, ast.Name) and n.id in ORACLE_NAMES)
                                          or (isinstance(n, ast.Attribute) and n.attr in ORACLE_NAMES)):
                self.calls_oracle = True
            if isinstance(n, ast.Import):
                self.imports.update((a.asname or a.name).split(".")[0] for a in n.names)
                for a in n.names:            # import a.b as c -> c: a.b; import a.b -> a: a
                    self.import_names[a.asname or a.name.split(".")[0]] = a.name if a.asname else a.name.split(".")[0]
            elif isinstance(n, ast.ImportFrom):
                self.imports.update(a.asname or a.name for a in n.names)
                if n.module and n.level == 0:
                    for a in n.names:        # from tests.fs_clock import move_ctime as mc -> mc: tests.fs_clock.move_ctime
                        self.import_names[a.asname or a.name] = "%s.%s" % (n.module, a.name)
                if n.module == "threading":                          # from threading import Thread as Th
                    self.thread_aliases.update(a.asname or a.name for a in n.names if a.name in THREAD_CTORS)
                    self.timer_aliases.update(a.asname or a.name for a in n.names if a.name == "Timer")
        for n in self.tree.body:
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        self.globals[t.id] = n.value
        su = self.functions.get("setUpModule")
        if su is not None:                                   # setUpModule's `global x; x = ...` binds module names too
            declared = {nm for s in ast.walk(su) if isinstance(s, ast.Global) for nm in s.names}
            for s in ast.walk(su):
                if isinstance(s, ast.Assign):
                    for t in s.targets:
                        if isinstance(t, ast.Name) and t.id in declared:
                            self.globals[t.id] = s.value
        for name, value in self.globals.items():                     # Th = threading.Thread
            if _names_thread_ctor(value):
                self.thread_aliases.add(name)
            if _names_timer(value):                                  # Tm = threading.Timer
                self.timer_aliases.add(name)
        self.thread_classes = {}             # module classes whose bases (here, transitively) name Thread or an alias of it
        for name, c in self.classes.items():
            if self.derives_thread(c):
                self.thread_classes[name] = c
        self._units = None
        self._unit_of = {}

    def base_names_thread(self, base, local_aliases=()):
        """The base expression names Thread / Timer, an alias of it (module-level or handed in), or a module class that
        derives from it."""
        if _names_thread_ctor(base):
            return True
        return isinstance(base, ast.Name) and (base.id in self.thread_aliases or base.id in local_aliases
                                               or base.id in self.thread_classes)

    def derives_thread(self, cls, local_aliases=(), local_classes=None):
        """The class or a base of it in this file (or a local class handed in) has a base that names Thread / Timer or an
        alias of it."""
        seen, q = set(), [cls]
        while q:
            c = q.pop(0)
            if c.name in seen:
                continue
            seen.add(c.name)
            for b in c.bases:
                if self.base_names_thread(b, local_aliases):
                    return True
                nm = ast.unparse(b).split(".")[-1]
                nxt = (local_classes or {}).get(nm) or self.classes.get(nm)
                if nxt is not None:
                    q.append(nxt)
        return False

    def derives_timer(self, cls, local_aliases=(), local_classes=None):
        """The class or a base of it in this file (or a local class handed in) has a base that names threading.Timer or
        an alias of it: its construction's callable is function= (or the second positional), its interval the first."""
        seen, q = set(), [cls]
        while q:
            c = q.pop(0)
            if c.name in seen:
                continue
            seen.add(c.name)
            for b in c.bases:
                if _names_timer(b) or (isinstance(b, ast.Name) and (b.id in self.timer_aliases or b.id in local_aliases)):
                    return True
                nm = _text(b, self).split(".")[-1]
                nxt = (local_classes or {}).get(nm) or self.classes.get(nm)
                if nxt is not None:
                    q.append(nxt)
        return False

    def bases_of(self, cls):
        """The class and its bases in this file, nearest first (answered once per class; the callers read the list)."""
        out = self._bases.get(id(cls))
        if out is not None:
            return out
        out, q, seen = [], [cls], set()
        while q:
            c = q.pop(0)
            if c.name in seen:
                continue
            seen.add(c.name)
            out.append(c)
            for b in c.bases:
                nm = ast.unparse(b).split(".")[-1]
                if nm in self.classes:
                    q.append(self.classes[nm])
        self._bases[id(cls)] = out
        return out

    def is_testcase(self, cls):
        return any(ast.unparse(b).split(".")[-1] == "TestCase" for c in self.bases_of(cls) for b in c.bases)

    def methods_of(self, cls, name):
        return [f for c in self.bases_of(cls) for f in c.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and f.name == name]

    def class_attr_bindings(self, cls):
        """{attribute: [values]} for every `<x>.<attribute>` bound anywhere in `cls` by an assignment, an element assigned by
        subscript or a += of a list, plus every `.append(v)` / `.add(v)` into one, in the class's walk order: what
        _Unit.class_bindings reads per attribute, the class walked once."""
        idx = self._class_attrs.get(id(cls))
        if idx is None:
            idx = self._class_attrs[id(cls)] = {}
            for sub in ast.walk(cls):
                if isinstance(sub, ast.Assign):
                    for t in sub.targets:
                        if isinstance(t, ast.Attribute):
                            idx.setdefault(t.attr, []).append(sub.value)
                        elif isinstance(t, ast.Subscript) and isinstance(t.value, ast.Attribute):
                            idx.setdefault(t.value.attr, []).append(sub.value)
                elif isinstance(sub, ast.AugAssign) and isinstance(sub.target, ast.Attribute):
                    idx.setdefault(sub.target.attr, []).extend(sub.value.elts if isinstance(sub.value, (ast.List, ast.Tuple)) else [sub.value])
                elif isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr in ("append", "add") \
                        and isinstance(sub.func.value, ast.Attribute) and sub.args:
                    idx.setdefault(sub.func.value.attr, []).append(sub.args[0])
        return idx

    def units(self):
        """Every function the walk classes on its own: module-level functions and every method of every class, a class
        nested in a class included (SettingsPickThroughTheLoop._Client in tests/test_sdk_backend.py: 68 such classes in
        the tree on 2026-09-22, none starting a thread, two of them calling run_in_executor at three sites)."""
        if self._units is None:
            out = []
            for f in self.tree.body:
                if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out.append(_Unit(self, None, f))
            for c in self.tree.body:
                if isinstance(c, ast.ClassDef):
                    queue = [c]
                    while queue:
                        k = queue.pop(0)
                        for f in k.body:
                            if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                out.append(_Unit(self, k, f))
                            elif isinstance(f, ast.ClassDef):
                                queue.append(f)
            self._units = out
            for u in out:
                self._unit_of.setdefault(id(u.fn), u)
        return self._units

    def unit_for(self, fn, cls=None, parent=None):
        """The unit that reads `fn`, built once per function: with `cls` for a method (its self.x() is the class's x), with
        `parent` for a function defined inside another (its free names resolve through the parent). Lazy: a product
        module's one function is read without building a unit for every function of the file."""
        u = self._unit_of.get(id(fn))
        if u is None:
            u = _Unit(self, cls, fn, parent=parent)
            self._unit_of[id(fn)] = u
        return u

    def is_stdlib_alias(self, name):
        """The local name imports a module of the standard library (`import time`; `from unittest import mock`)."""
        dotted = self.import_names.get(name)
        return bool(dotted) and dotted.split(".")[0] in getattr(sys, "stdlib_module_names", ())

    def is_product_alias(self, name, depth=0):
        """The module-level name is a product module (km, sb, jd, pm, em, cb): an import from kernel/, postal/ or cli/,
        a name imported from another test module that is one there (`from tests.test_x import km`), or a global whose
        value is a product module (product_module_value)."""
        if depth > 6:
            return False
        dotted = self.import_names.get(name)
        if dotted:
            if dotted.split(".")[0] in PRODUCT_DIRS:
                return True
            if "." in dotted:
                mod, last = dotted.rsplit(".", 1)
                m = self.tests_module(mod)
                if m is not None:
                    return m.is_product_alias(last, depth + 1)
            return False
        g = self.globals.get(name)
        return g is not None and self.product_module_value(g, depth + 1)

    def product_module_value(self, node, depth=0):
        """The module-level value is a product module: load_source(...); a call of a function of this module or of an
        imported test module whose return is one (km = TA.kernel_module()); an attribute of a product module that its
        file binds to one (jd = km.jd: the kernel's jd = load_source(...)); an attribute of an imported test module
        that is one there (em = TA.em); a name that is one."""
        if depth > 6 or node is None:
            return False
        if isinstance(node, ast.Call):
            if _callee_name(node) == "load_source":
                return True
            f = node.func
            if isinstance(f, ast.Name) and f.id in self.functions:
                return any(self.product_module_value(v, depth + 1) for v in _returns(self.functions[f.id]))
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
                m = self.tests_module_for(f.value.id)
                if m is not None and f.attr in m.functions:
                    return any(m.product_module_value(v, depth + 1) for v in _returns(m.functions[f.attr]))
            return False
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if self.is_product_alias(node.value.id, depth + 1):
                g = self.product.global_value(node.attr) if self.product is not None else None
                return g is not None and self.product_module_value(g, depth + 1)
            m = self.tests_module_for(node.value.id)
            if m is not None:
                g = m.globals.get(node.attr)
                return g is not None and m.product_module_value(g, depth + 1)
            return False
        if isinstance(node, ast.Subscript):                                     # return _KM[0]
            return self.product_module_value(node.value, depth + 1)
        if isinstance(node, ast.Name):
            if self.is_product_alias(node.id, depth + 1):
                return True
            return any(self.product_module_value(v, depth + 1) for v in self.appended(node.id))   # a global list filled once
        return False

    def product_file(self, name, depth=0):
        """The product FILE a module-level alias binds (the roads of is_product_alias, answered with the file instead of
        yes): an import from a product directory (file_dotted), a name imported from another test module that is one
        there, a global whose value names one (product_file_of); None when the walk cannot tell."""
        if depth > 6 or self.product is None:
            return None
        dotted = self.import_names.get(name)
        if dotted:
            if dotted.split(".")[0] in PRODUCT_DIRS:
                return self.product.file_dotted(dotted)
            if "." in dotted:
                mod, last = dotted.rsplit(".", 1)
                m = self.tests_module(mod)
                if m is not None:
                    return m.product_file(last, depth + 1)
            return None
        g = self.globals.get(name)
        r = self.product_file_of(g, depth + 1) if g is not None else None
        if r is None:
            for v in self.appended(name):
                r = self.product_file_of(v, depth + 1)
                if r is not None:
                    break
        return r

    def product_file_of(self, node, depth=0):
        """The product file a value names (the roads of product_module_value): load_source(...)'s string arguments
        (file_named), a function of this or an imported test module whose return names one, an attribute of a product
        module its file binds to one (jd = km.jd: the kernel's jd = load_source(..., 'judge.py')), an attribute of an
        imported test module, a subscript, a name; None when the walk cannot tell."""
        if depth > 6 or node is None or self.product is None:
            return None
        if isinstance(node, ast.Call):
            if _callee_name(node) == "load_source":
                nodes = [node] + [self.globals[n.id] for n in ast.walk(node) if isinstance(n, ast.Name) and n.id in self.globals]
                return self.product.file_named([c.value for n in nodes for c in ast.walk(n) if isinstance(c, ast.Constant) and isinstance(c.value, str)])
            f = node.func
            if isinstance(f, ast.Name) and f.id in self.functions:
                for v in _returns(self.functions[f.id]):
                    r = self.product_file_of(v, depth + 1)
                    if r is not None:
                        return r
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
                m = self.tests_module_for(f.value.id)
                if m is not None and f.attr in m.functions:
                    for v in _returns(m.functions[f.attr]):
                        r = m.product_file_of(v, depth + 1)
                        if r is not None:
                            return r
            return None
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if self.is_product_alias(node.value.id):
                g = self.product.global_value(node.attr)
                return self.product_file_of(g, depth + 1) if g is not None else None
            m = self.tests_module_for(node.value.id)
            if m is not None:
                return m.product_file_of(m.globals.get(node.attr), depth + 1)
            return None
        if isinstance(node, ast.Subscript):
            return self.product_file_of(node.value, depth + 1)
        if isinstance(node, ast.Name):
            return self.product_file(node.id, depth + 1)
        return None

    def appended(self, name):
        """The values `.append`ed to the module-level name anywhere in the module (`_KM.append(load_source(...))` inside
        the function that fills the cache), for a global bound to an empty container; the module walked once for every
        name asked."""
        if name not in self.globals:
            return []
        if self._appends_index is None:
            self._appends_index = {}
            for n in ast.walk(self.tree):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "append" and n.args \
                        and isinstance(n.func.value, ast.Name):
                    self._appends_index.setdefault(n.func.value.id, []).append(n.args[0])
        return list(self._appends_index.get(name, []))

    def tests_module(self, dotted):
        """The _Module of another module under tests/ named by its import spelling (`tests.test_x`, `test_x`,
        `tests.fixtures.y`), built once per census; None when there is no such file or it is this module."""
        rel = dotted[6:] if dotted.startswith("tests.") else dotted
        p = os.path.join(ROOT, "tests", rel.replace(".", os.sep) + ".py")
        if not os.path.isfile(p) or os.path.realpath(p) == os.path.realpath(self.path):
            return None
        m = self.helper_cache.get(p)
        if m is None:
            try:
                m = self.helper_cache[p] = _Module(p, self.loops, thread_classes=self.product_thread_classes,
                                                   helpers=self.helpers, helper_cache=self.helper_cache, product=self.product)
            except (SyntaxError, UnicodeDecodeError):
                return None
        return m

    def tests_module_for(self, local):
        """The module under tests/ a local name imports (`import test_asm_checkpoint as TA`; `from tests import
        test_kernel_file_comments_save as tks`), else None."""
        dotted = self.import_names.get(local)
        return self.tests_module(dotted) if dotted else None

    def tests_function(self, local):
        """(_Module, FunctionDef) when a local name imports a function of another module under tests/ (`from
        test_asm_checkpoint import kernel_module`), else None: its returns are read there (a product module it builds)."""
        dotted = self.import_names.get(local)
        if not dotted or "." not in dotted:
            return None
        mod, name = dotted.rsplit(".", 1)
        m = self.tests_module(mod)
        if m is not None and name in m.functions:
            return m, m.functions[name]
        return None

    def _helper(self, dotted):
        """The _Module of the helper module under tests/ that `dotted` names (built once per census), else None."""
        p = self.helpers.get(_helper_key(dotted))
        if p is None or os.path.realpath(p) == os.path.realpath(self.path):
            return None
        m = self.helper_cache.get(p)
        if m is None:
            m = self.helper_cache[p] = _Module(p, self.loops, thread_classes=self.product_thread_classes,
                                               helpers=self.helpers, helper_cache=self.helper_cache)
        return m

    def helper_module(self, local):
        """The helper module a local name imports (`import lab_dist`; `from tests import fs_clock`), else None."""
        dotted = self.import_names.get(local)
        return self._helper(dotted) if dotted else None

    def helper_module_dotted(self, node):
        """The helper module a dotted expression names through an import of its package (`import tests.fs_clock` and then
        `tests.fs_clock.move_ctime(...)`; `import tests.fixtures.fake_claude`), else None."""
        parts = []
        while isinstance(node, ast.Attribute):
            parts.insert(0, node.attr)
            node = node.value
        if not isinstance(node, ast.Name) or not parts:
            return None
        base = self.import_names.get(node.id)
        return self._helper(".".join([base] + parts)) if base else None

    def helper_function(self, local):
        """(helper _Module, FunctionDef) when a local name imports a function of a helper module (`from git_fixture import
        git`), else None."""
        dotted = self.import_names.get(local)
        if not dotted or "." not in dotted:
            return None
        mod, name = dotted.rsplit(".", 1)
        m = self._helper(mod)
        if m is not None and name in m.functions:
            return m, m.functions[name]
        return None


def _declares(fn, name):
    """'nonlocal' / 'global' when the function's own body (not a nested def's) declares `name` so, else None."""
    for s in fn.body:
        for n in _run_nodes(s):
            if isinstance(n, ast.Nonlocal) and name in n.names:
                return "nonlocal"
            if isinstance(n, ast.Global) and name in n.names:
                return "global"
    return None


def _binds_name(fn, name):
    """The function binds `name` in its own scope: a parameter, an assignment or a for / with / walrus / except target of
    its own body (not of a nested def's, not a comprehension's), or a def or class of that name in its body."""
    a = fn.args
    if any(x.arg == name for x in a.args + a.kwonlyargs + a.posonlyargs) or (a.vararg and a.vararg.arg == name) \
            or (a.kwarg and a.kwarg.arg == name):
        return True
    for s in fn.body:
        for n in _run_nodes(s):
            if isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, ast.Store):
                return True
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == name:
                return True
            if isinstance(n, ast.ExceptHandler) and n.name == name:
                return True
            if isinstance(n, (ast.Import, ast.ImportFrom)) and any((al.asname or al.name.split(".")[0]) == name for al in n.names):
                return True
        for n in ast.walk(s):                                   # a def nested anywhere in the statement binds its name here
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == name:
                return True
    return False


def _stmts(body, stack, out):
    """Every statement in `body`, recursively, with the block holding it, its index there and the compound statements
    enclosing it, outermost first."""
    for i, s in enumerate(body):
        out.append((s, body, i, tuple(stack)))
        for field in ("body", "orelse", "finalbody"):
            sub = getattr(s, field, None)
            if isinstance(sub, list) and sub and isinstance(sub[0], ast.stmt):
                _stmts(sub, stack + [(s, field)], out)
        for h in getattr(s, "handlers", []) or []:
            _stmts(h.body, stack + [(s, "handler")], out)
        for c in getattr(s, "cases", []) or []:
            _stmts(c.body, stack + [(s, "case")], out)


class _Unit:
    def __init__(self, module, cls, fn, parent=None):
        self.module, self.cls, self.fn, self.parent = module, cls, fn, parent
        self.qualname = ("%s.%s" % (cls.name, fn.name)) if cls is not None else fn.name
        self.params = {a.arg for a in fn.args.args + fn.args.kwonlyargs + fn.args.posonlyargs}
        self.rows = []
        _stmts(fn.body, [], self.rows)
        self.row_of = {id(s): (s, block, i, stack) for s, block, i, stack in self.rows}
        self.parent_node = {}           # id(expression node) -> the node, or the statement, that holds it
        self.exprs = {}                 # id(statement) -> its expression nodes (not those of the statements it holds), in
        for s, _b, _i, _st in self.rows:                                    # ast.walk's order: walked ONCE here and read by _bind,
            nodes, todo = [], collections.deque()                           # starts, product_starts, callers and the cleanup
            for child in ast.iter_child_nodes(s):                           # readers instead of a walk per reader
                if isinstance(child, ast.stmt):
                    continue
                self.parent_node.setdefault(id(child), s)
                todo.append(child)
                while todo:                                                 # ast.walk's own order: breadth first, per child
                    node = todo.popleft()
                    nodes.append(node)
                    for sub in ast.iter_child_nodes(node):
                        self.parent_node.setdefault(id(sub), node)
                        todo.append(sub)
            self.exprs[id(s)] = nodes
        # Bindings are kept PER SCOPE: a function defined in the body binds its own names (a nested `t = Thread(target=_once)`
        # rebinds nothing of the enclosing body's `t`), and a use reads its own scope first, then the enclosing ones out to
        # the unit's body (a closure), then the parent unit's. A name declared nonlocal or global in a nested def binds in
        # the scope out from it. Appends (`ts.append(...)`) are unit-wide: a nested def appends into the list it closes over.
        self.scopes = {id(fn): {}}      # id(scope function) -> {name or attribute text -> [(line, value)], in source order}
        self.scope_fn = {id(fn): fn}
        self.enclosing = {}             # id(nested def) -> the function whose body defines it
        self.nested = []                # every def in the body, at any depth
        self.appends = {}
        for s, _b, _i, st in self.rows:
            if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.scopes[id(s)], self.scope_fn[id(s)] = {}, s
                self.enclosing[id(s)] = self._scope_of(st)
                self.nested.append(s)
        for s, _b, _i, st in self.rows:
            self._bind(s, self._scope_of(st))
        self.bindings = self.scopes[id(fn)]   # the unit's own body's bindings (the ones a use in the body reads first)
        self.local_defs = {}
        self.local_classes = {}
        for s, _b, _i, _st in self.rows:
            if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.local_defs.setdefault(s.name, s)
            elif isinstance(s, ast.ClassDef):
                self.local_classes.setdefault(s.name, s)
        self.thread_aliases = {nm for table in self.scopes.values() for nm, vals in table.items()   # Real = threading.Thread
                               if any(not isinstance(v, tuple) and _names_thread_ctor(v) for _l, v in vals)}
        self.timer_aliases = {nm for table in self.scopes.values() for nm, vals in table.items()    # Tm = threading.Timer
                              if any(not isinstance(v, tuple) and _names_timer(v) for _l, v in vals)}
        self.thread_classes = {nm: c for nm, c in self.local_classes.items()     # class W(threading.Thread), in the body
                               if module.derives_thread(c, self.thread_aliases | module.thread_aliases, self.local_classes)}

    # ── bindings ──

    def _scope_of(self, stack):
        """The function whose body holds a statement with the enclosing compound statements `stack`: the innermost def
        among them, else the unit's own function."""
        for s, _field in reversed(stack):
            if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return s
        return self.fn

    def scope_at(self, line):
        """The innermost def in the body whose lines hold `line`, else the unit's own function: the scope a use at that
        line reads first."""
        best = self.fn
        for nested in self.nested:
            end = nested.end_lineno or nested.lineno
            if nested.lineno <= line <= end and (best is self.fn or end - nested.lineno < (best.end_lineno or best.lineno) - best.lineno):
                best = nested
        return best

    def scope_chain(self, scope):
        """`scope`, then the functions enclosing it, out to the unit's own."""
        out = [scope]
        while id(scope) in self.enclosing and scope is not self.fn:
            scope = self.enclosing[id(scope)]
            out.append(scope)
        if out[-1] is not self.fn:
            out.append(self.fn)
        return out

    def _binding_scope(self, name, scope):
        """The scope a Name assigned in `scope` binds in: `scope` itself; the unit's own when the def declares the name
        global; when it declares it nonlocal, the NEAREST enclosing function that binds the name itself (Python's rule:
        `def outer(): def inner(): nonlocal t; t = ...` binds the t of the function enclosing outer when outer binds no t
        of its own), the unit's own body when none does."""
        fn = self.scope_fn.get(id(scope), self.fn)
        if fn is self.fn:
            return scope
        decl = _declares(fn, name)
        if decl == "global":
            return self.fn
        if decl == "nonlocal":
            outer = self.enclosing.get(id(fn), self.fn)
            while outer is not self.fn:
                d = _declares(outer, name)
                if d == "global":
                    return self.fn
                if d != "nonlocal" and _binds_name(outer, name):
                    return outer
                outer = self.enclosing.get(id(outer), self.fn)
            return self.fn
        return scope

    def _bind(self, s, scope):
        if isinstance(s, ast.Assign):
            for t in s.targets:
                self._bind_target(t, s.value, s.lineno, scope)
        elif isinstance(s, ast.AnnAssign) and s.value is not None:
            self._bind_target(s.target, s.value, s.lineno, scope)
        elif isinstance(s, ast.AugAssign) and isinstance(s.op, ast.Add):          # self.threads += [peer, handler]
            holder = ast.unparse(s.target)
            for v in (s.value.elts if isinstance(s.value, (ast.List, ast.Tuple)) else [s.value]):
                self.appends.setdefault(holder, []).append(v)
        elif isinstance(s, (ast.For, ast.AsyncFor)):
            self._bind_target(s.target, ("for", s.iter), s.lineno, scope)
        elif isinstance(s, (ast.With, ast.AsyncWith)):
            for it in s.items:
                if it.optional_vars is not None:
                    self._bind_target(it.optional_vars, ("with", it.context_expr), s.lineno, scope)
        for sub in self.exprs[id(s)]:
            if isinstance(sub, ast.NamedExpr):
                self._bind_target(sub.target, sub.value, s.lineno, scope)
            elif isinstance(sub, ast.comprehension):
                self._bind_target(sub.target, ("for", sub.iter), s.lineno, scope)
            elif isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr in ("append", "add") and sub.args:
                self.appends.setdefault(ast.unparse(sub.func.value), []).append(sub.args[0])

    def _bind_target(self, t, value, line, scope):
        if isinstance(t, ast.Name):
            table = self.scopes.setdefault(id(self._binding_scope(t.id, scope)), {})
            table.setdefault(t.id, []).append((line, value))
        elif isinstance(t, ast.Attribute):
            self.scopes.setdefault(id(scope), {}).setdefault(ast.unparse(t), []).append((line, value))
        elif isinstance(t, ast.Subscript):                                          # holder["a"] = Thread(...): the element
            self.scopes.setdefault(id(scope), {}).setdefault(ast.unparse(t), []).append((line, value))   # by its text, and
            self.appends.setdefault(ast.unparse(t.value), []).append(value)                              # as one of the holder's
        elif isinstance(t, (ast.Tuple, ast.List)):
            if isinstance(value, (ast.Tuple, ast.List)) and len(value.elts) == len(t.elts):
                for e, v in zip(t.elts, value.elts):
                    self._bind_target(e, v, line, scope)
            else:
                for i, e in enumerate(t.elts):
                    self._bind_target(e, ("unpack", value, i), line, scope)

    def binding_at(self, text, line):
        """(line, value) of the binding of `text` in force at `line`: in the scope of the use first (the innermost def whose
        lines hold it, else the unit's body), then the scopes enclosing it; within a scope the last binding at or before the
        line, else the first one after it (a use inside a loop body ahead of the rebinding); else the parent unit's; else
        None."""
        for scope in self.scope_chain(self.scope_at(line)):
            vals = self.scopes.get(id(scope), {}).get(text)
            if vals:
                before = [lv for lv in vals if lv[0] <= line]
                return before[-1] if before else vals[0]
        if self.parent is not None:
            return self.parent.binding_at(text, line)
        return None

    def class_bindings(self, attr):
        """Every value bound to `self.<attr>` / `cls.<attr>` by any spelling across the class and its bases (an assignment,
        an element assigned by subscript, a += of a list), plus every `.append(v)` into it."""
        if self.cls is None:
            return []
        out = []
        for c in self.module.bases_of(self.cls):                     # each class walked once (class_attr_bindings)
            out += self.module.class_attr_bindings(c).get(attr, [])
        return out

    # ── what a call constructs ──

    def is_thread_ctor(self, node, line=None):
        """A Thread / Timer construction: by name, through an alias (`from threading import Thread as Th`, a module-level or
        local `Real = threading.Thread`), or of a Thread subclass defined in this module or in this function."""
        if not isinstance(node, ast.Call):
            return False
        f = node.func
        if _names_thread_ctor(f):
            return True
        if isinstance(f, ast.Name):
            if f.id in self.module.thread_aliases or f.id in self.thread_aliases:
                return True
            if f.id in self.thread_classes or f.id in self.module.thread_classes:
                return True
            if self.parent is not None and (f.id in self.parent.thread_aliases or f.id in self.parent.thread_classes):
                return True
        return False

    def thread_class_of(self, call):
        """The ClassDef when the construction is of a Thread subclass defined in this module or this function."""
        f = call.func
        if isinstance(f, ast.Name):
            for scope in (self, self.parent):
                if scope is not None and f.id in scope.thread_classes:
                    return scope.thread_classes[f.id]
            return self.module.thread_classes.get(f.id)
        return None

    def is_timer_ctor(self, call):
        """The construction is a Timer: by name (threading.Timer, Timer), through an alias (module-level or local, `Tm =
        threading.Timer`, `from threading import Timer as Tm`) or of a Timer subclass defined in this module or this
        function: its callable is function= (or the second positional) and its interval the first (_timer_rule)."""
        f = call.func
        if _names_timer(f):
            return True
        if not isinstance(f, ast.Name):
            return False
        aliases = self.timer_aliases | self.module.timer_aliases | (self.parent.timer_aliases if self.parent is not None else set())
        if f.id in aliases:
            return True
        cls = self.thread_class_of(call)
        if cls is None:
            return False
        local = dict(self.parent.local_classes) if self.parent is not None else {}
        local.update(self.local_classes)
        return self.module.derives_timer(cls, aliases, local)

    def class_named(self, name):
        """The ClassDef a bare name denotes here: a class defined in this function, in the enclosing one, or in the module."""
        for scope in (self, self.parent):
            if scope is not None and name in scope.local_classes:
                return scope.local_classes[name]
        return self.module.classes.get(name)

    def method_of(self, cls, name):
        """The method `name` of a class defined in this module or this function, in the class or a base of it here (nearest
        first); None when none defines it."""
        seen, q = set(), [cls]
        while q:
            c = q.pop(0)
            if c.name in seen:
                continue
            seen.add(c.name)
            for f in c.body:
                if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and f.name == name:
                    return f
            for b in c.bases:
                nxt = self.class_named(ast.unparse(b).split(".")[-1])
                if nxt is not None:
                    q.append(nxt)
        return None

    def run_method_of(self, cls):
        """The `run` method of a Thread subclass, in the class or a base of it defined in this module or this function."""
        return self.method_of(cls, "run")

    def callee_of(self, call, line):
        """(function or lambda, the unit that reads it) for a call of a function defined in this function, a module
        function, a method of the class (self.x() / cls.x()), a name bound to a lambda, or a function of a helper module
        under tests/ (`git_fixture.spawn()` through the imported module, `spawn()` through the imported name: read in that
        module's own unit); None for anything else."""
        f = call.func
        if isinstance(f, ast.Name):
            for scope in (self, self.parent):
                if scope is not None and f.id in scope.local_defs:
                    fn = scope.local_defs[f.id]
                    return fn, self.module.unit_for(fn, scope.cls, parent=scope)
            if f.id in self.module.functions:
                fn = self.module.functions[f.id]
                return fn, self.module.unit_for(fn)
            b = self.binding_at(f.id, line)
            if b is not None and isinstance(b[1], ast.Lambda):
                return b[1], self
            g = self.module.globals.get(f.id)
            if isinstance(g, ast.Lambda):
                return g, self
            hf = self.module.helper_function(f.id) or self.module.tests_function(f.id)
            if hf is not None:
                return hf[1], hf[0].unit_for(hf[1])
            return None
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
            if f.value.id in ("self", "cls") and self.cls is not None:
                ms = self.module.methods_of(self.cls, f.attr)
                if ms:
                    return ms[0], self.module.unit_for(ms[0], self.cls)
            hm = self.module.helper_module(f.value.id) or self.module.tests_module_for(f.value.id)
            if hm is not None and f.attr in hm.functions:
                return hm.functions[f.attr], hm.unit_for(hm.functions[f.attr])
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Attribute):     # tests.helper_mod.spawn(): the dotted road
            hm = self.module.helper_module_dotted(f.value)
            if hm is not None and f.attr in hm.functions:
                return hm.functions[f.attr], hm.unit_for(hm.functions[f.attr])
        return None

    def known_non_thread(self, call):
        """The call constructs something whose start() is not a thread of ours: a mock patcher, a regex match, the
        tracemalloc module, or an object of a product or library module (sb.SdkSession(...), socket.socket()): a product
        Thread subclass is the exception, listed unreadable so the walk is extended rather than silent."""
        parts = ast.unparse(call.func).split(".")
        if parts[0] in NON_THREAD_HEADS or any(p in NON_THREAD_PARTS for p in parts) or parts[-1] in NON_THREAD_ATTRS:
            return True
        if isinstance(call.func, ast.Name) and call.func.id in _BUILTIN_NAMES and call.func.id not in self.module.classes \
                and call.func.id not in self.module.functions and call.func.id not in self.thread_classes \
                and call.func.id not in self.module.thread_classes and call.func.id not in self.local_defs:
            return True                 # range(3), slice(1, 2), object(): a builtin constructs no thread of ours
        if len(parts) >= 2 and isinstance(call.func, ast.Attribute):
            head = parts[0]
            g = self.module.globals.get(head)
            if head in self.module.imports or isinstance(g, (ast.Call, ast.Attribute)):
                return parts[-1] not in self.module.product_thread_classes
        return False

    # ── what a receiver is ──

    def resolve(self, node, line, depth=0):
        """'thread' when the expression is (or is bound to) a Thread/Timer construction, 'other' when it is bound to
        something else the walk can read, 'empty' for an empty container, None when it cannot read it."""
        if depth > 8 or node is None:
            return None
        if isinstance(node, tuple):
            kind, inner = node[0], node[1]
            if kind == "for":
                return self.resolve(inner, line, depth + 1)
            if kind == "with":
                return "other"
            if kind == "unpack":                                    # t, ev = helper(): the helper's returned tuple, by position
                callee = self.callee_of(inner, line) if isinstance(inner, ast.Call) else None
                if callee is None:
                    return None
                fn, u = callee
                kinds = set()
                for v in (_returns(fn) if not isinstance(fn, ast.Lambda) else [fn.body]):
                    if isinstance(v, (ast.Tuple, ast.List)) and len(v.elts) > node[2]:
                        kinds.add(u.resolve(v.elts[node[2]], v.lineno, depth + 1))
                    else:
                        kinds.add(None)
                return _join_kinds(kinds) if kinds else None
            return None
        if isinstance(node, ast.Call):
            if self.is_thread_ctor(node, line):
                return "thread"
            callee = self.callee_of(node, line)
            if callee is not None:                                  # a helper: what its returns resolve to, in its own unit
                fn, u = callee
                if isinstance(fn, ast.Lambda):
                    return u.resolve(fn.body, fn.lineno, depth + 1)
                vals = list(_returns(fn))
                if not vals:
                    return "other"                                  # returns None: nothing to start
                return _join_kinds({u.resolve(v, v.lineno, depth + 1) for v in vals})
            return "other" if self.known_non_thread(node) else None
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            return _join_kinds({self.resolve(e, line, depth + 1) for e in node.elts})
        if isinstance(node, ast.Dict):
            return _join_kinds({self.resolve(v, line, depth + 1) for v in node.values if v is not None})
        if isinstance(node, ast.BoolOp):
            return _join_kinds({self.resolve(e, line, depth + 1) for e in node.values})
        if isinstance(node, ast.IfExp):
            return _join_kinds({self.resolve(node.body, line, depth + 1), self.resolve(node.orelse, line, depth + 1)})
        if isinstance(node, (ast.ListComp, ast.GeneratorExp, ast.SetComp)):
            return self.resolve(node.elt, line, depth + 1)
        if isinstance(node, (ast.Name, ast.Attribute, ast.Subscript)):
            text = node.id if isinstance(node, ast.Name) else ast.unparse(node)
            b = self.binding_at(text, line)
            if b is not None:
                r = self.resolve(b[1], b[0], depth + 1)
                if r == "empty" or (r is None and text in self.appends):
                    return self._appended(text, depth)
                return r
            if text in self.appends:
                return self._appended(text, depth)
            if isinstance(node, ast.Name):
                if node.id in self.module.globals:
                    g = self.module.globals[node.id]
                    r = self.resolve(g, g.lineno, depth + 1)
                    return self._appended(text, depth) if r == "empty" else r
                if node.id in self.module.imports or node.id in self.module.functions or node.id in self.module.classes:
                    return "other"                                  # a module, a function, a class: no thread of ours
                return None
            if isinstance(node, ast.Attribute):
                vals = self.class_bindings(node.attr)
                if vals:
                    r = _join_kinds({self.resolve(v, v.lineno, depth + 1) for v in vals})
                    return "other" if r == "empty" else r
                if isinstance(node.value, ast.Name) and (node.value.id in self.module.globals or node.value.id in self.module.imports):
                    return "other"      # a module object's attribute (mock.patch, tracemalloc.start): never a thread of ours
                return None
            r = self.resolve(node.value, line, depth + 1)           # a subscript of a container the walk read
            if r in ("empty", None) and ast.unparse(node.value) in self.appends:
                return self._appended(ast.unparse(node.value), depth)
            return r if r in ("thread", "other") else None
        if isinstance(node, (ast.Constant, ast.JoinedStr, ast.BinOp, ast.Compare, ast.Lambda, ast.UnaryOp)):
            return "other"
        return None

    def _appended(self, holder, depth):
        kinds = {self.resolve(v, v.lineno, depth + 1) for v in self.appends.get(holder, [])}
        return _join_kinds(kinds) if kinds else None

    def thread_of(self, node, line, depth=0):
        """(the construction, the unit it is read in) behind a start receiver, following the same roads as resolve."""
        if depth > 8 or node is None:
            return None
        if isinstance(node, tuple):
            if node[0] == "for":
                return self.thread_of(node[1], line, depth + 1)
            if node[0] == "unpack" and isinstance(node[1], ast.Call):
                callee = self.callee_of(node[1], line)
                if callee is not None:
                    fn, u = callee
                    for v in (_returns(fn) if not isinstance(fn, ast.Lambda) else [fn.body]):
                        if isinstance(v, (ast.Tuple, ast.List)) and len(v.elts) > node[2]:
                            r = u.thread_of(v.elts[node[2]], v.lineno, depth + 1)
                            if r:
                                return r
            return None
        if isinstance(node, ast.Call):
            if self.is_thread_ctor(node, line):
                return node, self
            callee = self.callee_of(node, line)
            if callee is not None:
                fn, u = callee
                for v in (_returns(fn) if not isinstance(fn, ast.Lambda) else [fn.body]):
                    r = u.thread_of(v, v.lineno, depth + 1)
                    if r:
                        return r
            return None
        elts = None
        if isinstance(node, (ast.List, ast.Tuple, ast.Set, ast.BoolOp)):
            elts = node.elts if not isinstance(node, ast.BoolOp) else node.values
        elif isinstance(node, ast.Dict):
            elts = [v for v in node.values if v is not None]
        elif isinstance(node, ast.IfExp):
            elts = [node.body, node.orelse]
        elif isinstance(node, (ast.ListComp, ast.GeneratorExp, ast.SetComp)):
            elts = [node.elt]
        if elts is not None:
            for e in elts:
                r = self.thread_of(e, line, depth + 1)
                if r:
                    return r
            return None
        if isinstance(node, (ast.Name, ast.Attribute, ast.Subscript)):
            text = node.id if isinstance(node, ast.Name) else ast.unparse(node)
            b = self.binding_at(text, line)
            if b is not None:
                r = self.thread_of(b[1], b[0], depth + 1)
                if r:
                    return r
            for v in self.appends.get(text, []):
                r = self.thread_of(v, v.lineno, depth + 1)
                if r:
                    return r
            if isinstance(node, ast.Name) and node.id in self.module.globals:
                g = self.module.globals[node.id]
                return self.thread_of(g, g.lineno, depth + 1)
            if isinstance(node, ast.Attribute):
                for v in self.class_bindings(node.attr):
                    r = self.thread_of(v, v.lineno, depth + 1)
                    if r:
                        return r
            if isinstance(node, ast.Subscript):
                r = self.thread_of(node.value, line, depth + 1)
                if r:
                    return r
                for v in self.appends.get(ast.unparse(node.value), []):
                    r = self.thread_of(v, v.lineno, depth + 1)
                    if r:
                        return r
        return None

    # ── the starts ──

    def starts(self):
        """Every `.start()` in the unit whose receiver resolves to a thread, or to nothing the walk can read; and every
        bound `.start` HANDED ON as a value (a keyword or positional argument, an assigned or returned value, a container
        element: `self._load_watched(before=writer.start)`), a start the callee makes, classed at the handing statement."""
        out = []
        for s, block, i, stack in self.rows:
            for sub in self.exprs[id(s)]:
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == "start" \
                        and not sub.args and not sub.keywords:
                    if self._value_used(sub):
                        continue        # `m.start() - width`, `heads[-1].start()` in a subscript: a regex match, not a thread
                    recv, handed = sub.func.value, False
                elif isinstance(sub, ast.Attribute) and sub.attr == "start" and isinstance(sub.ctx, ast.Load) and self._handed_on(sub):
                    recv, handed = sub.value, True
                else:
                    continue
                kind = self.resolve(recv, sub.lineno)
                if kind in ("other", "empty"):
                    continue
                found = self.thread_of(recv, sub.lineno) if kind == "thread" else None
                ctor, ctor_unit = found if found else (None, self)
                out.append(_Start(self, sub, recv, ctor, ctor_unit, s, block, i, stack, kind == "thread" and ctor is not None, handed=handed))
        return out

    def _handed_on(self, attr):
        """The bound `.start` is a VALUE handed on: a keyword or positional argument of a call (not its callee), the value
        of an assignment or a return, an element of a list, tuple, set, dict or comprehension, a conditional or boolean
        expression, a default argument, a yield, an await or a starred value in such a position. Not one in an operand
        position (`self.start <= m.start()`, `r.start + 0`: a slice's, a range's or a match's start, a value of some
        other object); a builtin's construction (range(3), slice(1, 2)) resolves to no thread (known_non_thread)."""
        p = self.parent_node.get(id(attr))
        if isinstance(p, ast.keyword):
            return True
        if isinstance(p, ast.Call):
            return any(a is attr for a in p.args)
        if isinstance(p, (ast.Assign, ast.AnnAssign, ast.NamedExpr, ast.Return)):
            return p.value is attr
        if isinstance(p, (ast.List, ast.Tuple, ast.Set)):
            return any(e is attr for e in p.elts)
        if isinstance(p, ast.Dict):
            return any(v is attr for v in p.values)
        if isinstance(p, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            return p.elt is attr
        if isinstance(p, ast.DictComp):
            return p.key is attr or p.value is attr
        if isinstance(p, ast.IfExp):                                # before=t.start if fast else None
            return p.body is attr or p.orelse is attr
        if isinstance(p, ast.BoolOp):                               # before=hook or t.start
            return any(v is attr for v in p.values)
        if isinstance(p, (ast.Yield, ast.YieldFrom, ast.Await, ast.Starred)):
            return p.value is attr
        if isinstance(p, ast.arguments):                            # def go(cb=t.start); lambda cb=t.start: cb()
            return any(d is attr for d in p.defaults + [d for d in p.kw_defaults if d is not None])
        return False

    def product_starts(self):
        """The INFORMATIONAL rows of this unit (_ProductStart, kind product-start, never pinned): the calls on which the
        PRODUCT starts a thread. A product object's own start() (sess.start() with sess = sb.SdkSession(...)); a call of a
        product SPAWN-HELPER (_Product.spawners: km._push_notify(...), jd.run_pass(...), be.drive_idle_queue(...),
        sb.SdkBackend(..., reconcile=True), km._new_ws_client(...) with start_sender defaulting True: a guard that is a
        false literal at the call is no start); loop.run_in_executor(None, f) (a worker of the loop's default executor);
        a ThreadPoolExecutor construction (its workers; whether it is under a `with` is said)."""
        prod = self.module.product
        names = prod.spawners() if prod is not None else {}
        out = []
        for s, _b, _i, _st in self.rows:
            for sub in self.exprs[id(s)]:
                if not isinstance(sub, ast.Call):
                    continue
                f, nm = sub.func, _callee_name(sub)
                if nm == "run_in_executor" and len(sub.args) >= 2:
                    ran = sub.args[1]
                    untimed = isinstance(ran, ast.Attribute) and ran.attr in BLOCKING and len(sub.args) == 2
                    ex = sub.args[0]
                    where = "the loop's default executor" if isinstance(ex, ast.Constant) and ex.value is None else "the executor `%s`" % _text(ex, self.module)
                    out.append(_ProductStart(self, sub, "run_in_executor", "a worker of %s runs %s%s"
                                             % (where, _text(ran, self.module), ", an untimed wait" if untimed else "")))
                elif nm in POOL_CTORS:
                    under = isinstance(self.parent_node.get(id(sub)), ast.withitem)
                    out.append(_ProductStart(self, sub, "pool", "the pool's worker threads, %s"
                                             % ("under a with that shuts the pool down and joins them on exit" if under else "NOT under a with")))
                elif prod is None or nm is None:
                    continue
                elif isinstance(f, ast.Attribute) and f.attr == "start" and not sub.args and not sub.keywords:
                    obj = _product_object(self, f.value, sub.lineno)
                    if obj is not None and obj != "module":
                        out.append(_ProductStart(self, sub, "object-start", "%s's own start(): the object's thread"
                                                 % (obj if isinstance(obj, str) else "a product object")))
                elif nm in names or (nm in prod.classes and "__init__" in names):
                    for _head, what in _spawner_calls(self, sub, nm):
                        out.append(_ProductStart(self, sub, "spawn-helper", what))
        return out

    def _value_used(self, call):
        """The call's value is consumed (an operand, a subscript, an argument, an assigned value): Thread.start() returns
        None, so this is some other object's start()."""
        p = self.parent_node.get(id(call))
        while p is not None and isinstance(p, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.Tuple, ast.List, ast.Lambda, ast.IfExp, ast.BoolOp)):
            if isinstance(p, ast.Lambda):
                return False
            p = self.parent_node.get(id(p))
        return not (p is None or isinstance(p, ast.Expr))

    def forward(self, stmt):
        """The statements that run after `stmt`, in order: the rest of its block, then, when the block is the body of a
        for, a with, an if or a try without a finally, the rest of the block holding that, climbing."""
        s = stmt
        while True:
            row = self.row_of.get(id(s))
            if row is None:
                return
            _s, block, i, stack = row
            yield from block[i + 1:]
            if not stack:
                return
            parent, field = stack[-1]
            if isinstance(parent, (ast.For, ast.AsyncFor, ast.With, ast.AsyncWith, ast.If)) and field in ("body", "orelse"):
                s = parent
                continue
            if isinstance(parent, ast.Try) and field == "body" and not parent.finalbody:
                s = parent
                continue
            return

    def assigned_attrs(self, stmt):
        """The self/cls attributes an assignment statement stores its value in (self.bus, self.ver = _serve(), _serve())."""
        out = []
        if isinstance(stmt, ast.Assign):
            for t in stmt.targets:
                for node in ast.walk(t):
                    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in ("self", "cls"):
                        out.append(node.attr)
        return out

    def hooks(self):
        """(name, FunctionDef) for every hook of the class and its bases, plus the module's tearDownModule."""
        out = []
        if self.cls is not None:
            for c in self.module.bases_of(self.cls):
                for f in c.body:
                    if isinstance(f, ast.FunctionDef) and f.name in HOOK_NAMES:
                        out.append((f.name, f))
        for nm in ("tearDownModule", "setUpModule"):
            if nm in self.module.functions:
                out.append((nm, self.module.functions[nm]))
        return out

    def callers(self):
        """(unit, call, statement, block, index, stack) for every call of this unit by name from the same class, a
        subclass in this file, or the module."""
        out = []
        for u in self.module.units():
            if u.fn is self.fn:
                continue
            if self.cls is not None and (u.cls is None or self.cls not in self.module.bases_of(u.cls)):
                continue
            for s, block, i, stack in u.rows:
                for sub in u.exprs[id(s)]:
                    if isinstance(sub, ast.Call) and _callee_name(sub) == self.fn.name:
                        out.append((u, sub, s, block, i, stack))
        return out


class _Start:
    def __init__(self, unit, call, recv, ctor, ctor_unit, stmt, block, index, stack, is_thread, handed=False):
        self.unit, self.call, self.recv, self.ctor, self.ctor_unit = unit, call, recv, ctor, ctor_unit
        self.stmt, self.block, self.index, self.stack = stmt, block, index, stack
        self.is_thread = is_thread
        self.handed = handed            # a bound `.start` handed on as a value (`call` is then the Attribute), not called here
        self.recv_text = ast.unparse(recv)                          # the receiver as a NAME: matched, never displayed
        self.recv_shown = _text(recv, unit.module)                  # the receiver as written: displayed and compared
        self.subclass = ctor_unit.thread_class_of(ctor) if ctor is not None else None
        if self.subclass is not None:                 # a Thread subclass: its run() is what the thread does
            run = ctor_unit.run_method_of(self.subclass)
            if run is not None:
                self.target_expr = run
                self.target = "%s.run" % self.subclass.name
            else:                                     # no run() of its own: Thread.run calls the construction's target
                self.target_expr = _target_expr(ctor, ctor_unit)
                self.target = _text(self.target_expr, ctor_unit.module) if self.target_expr is not None else "%s (no run)" % self.subclass.name
        else:
            self.target_expr = _target_expr(ctor, ctor_unit) if ctor is not None else None
            self.target = _text(self.target_expr, ctor_unit.module) if self.target_expr is not None else "?"
        self.line = call.lineno
        self._words = {}
        self.given = {}                 # the HANDS a caller supplies for the helper's parameters (at_caller): none in the start's own row
        self.kind, self.why = ("?", "") if ctor is None else _kind(self)
        self.indirect = _indirect(self.kind, self.why)

    def at_caller(self, unit, call, outer=None):
        """This start as read at a caller of its helper, with the arguments the caller hands the helper's parameters in
        hand (the HANDS, `given`; `outer` the caller's own hands when the caller is itself a helper classed at ITS callers).
        Two roads: the target itself is a PARAMETER of the helper (`self._build_on(lambda build: ...)`: the lambda's body,
        read in the caller's unit, with the construction's args= as its own arguments), or the start's own kind is
        UNREADABLE and the hands may decide it (a body whose work is a call of a parameter: the third arm, re-read by _kind
        with the hands in place). A copy: the start's own row keeps its own kind. The same start when the caller hands
        nothing the walk can place (a * argument) or the kind does not turn on the arguments."""
        helper = self.unit.fn
        given = _given_from(helper, call, unit, self.unit, outer, "handed in by the caller")
        expr = self.target_expr
        if isinstance(expr, ast.Name) and (expr.id, id(helper)) in given:      # the target IS the parameter
            arg, u, _outer, where, label = given[(expr.id, id(helper))]
            view = copy.copy(self)
            view._words, view.given = {}, given
            k, why = _expr_kind(u, arg, call.lineno, 0, self.ctor, self.ctor_unit, given)
            view.kind, view.why = k, "%s | %s of %s is `%s` %s" % (why, expr.id, label, _text(arg, u.module), where)
        elif self.kind == KIND_UNREAD and given:
            view = copy.copy(self)
            view._words, view.given = {}, given
            view.kind, view.why = _kind(view)
        else:
            return self
        view.indirect = _indirect(view.kind, view.why)
        return view

    def words(self, extra=()):
        """_thread_words, memoised per caller binding (`extra`)."""
        key = tuple(extra)
        if key not in self._words:
            self._words[key] = _thread_words(self, extra)
        return self._words[key]

    def file(self):
        return os.path.relpath(self.unit.module.path, ROOT)

    def describe(self):
        via = "%s.start handed on" % self.recv_shown if self.handed else "%s.start()" % self.recv_shown
        if self.ctor is None:
            return "%s:%d %s %s" % (self.file(), self.line, self.unit.qualname, ("hands %s.start on" % self.recv_shown) if self.handed else "calls %s" % via)
        return "%s:%d %s starts Thread(target=%s) via %s" % (self.file(), self.line, self.unit.qualname, self.target, via)


def _indirect(kind, why):
    """A loop the walk found in a PRODUCT function a callee reached (run -> em.hydrate; km._git_branch -> _tree_of ->
    _dotgit_on_chain) is evidence it cannot weigh: the product loop may well return (a walk over data, a retry with a
    bound), so for the timed-join rule such a thread is read as bounded; a loop in the target's own body, or in a
    function of the test module, is not."""
    return kind == "loop" and "calls " in why and "product function" in why


def _argument_for(fn, param, call):
    """The expression a call hands to the function's parameter `param`: by keyword, else by position (the first
    parameter of a method being self or cls), else the parameter's default; None when the walk cannot tell (a * or **
    argument before it)."""
    for kw in call.keywords:
        if kw.arg == param:
            return kw.value
    if any(kw.arg is None for kw in call.keywords):
        return None
    kwonly = [a.arg for a in fn.args.kwonlyargs]
    if param in kwonly:
        return fn.args.kw_defaults[kwonly.index(param)]      # None for a required keyword-only parameter not handed
    names = [a.arg for a in fn.args.posonlyargs + fn.args.args]
    if names and names[0] in ("self", "cls"):
        names = names[1:]
    if param not in names:
        return None
    pos = names.index(param)
    if any(isinstance(a, ast.Starred) for a in call.args[:pos + 1]):
        return None
    if pos < len(call.args):
        return call.args[pos]
    defaults = fn.args.defaults
    off = len(names) - len(defaults)
    return defaults[pos - off] if pos >= off and pos - off < len(defaults) else None


class _ProductStart:
    """An INFORMATIONAL row: a thread the PRODUCT starts on a test's call. Counted and printed with its site and what
    starts; never pinned (no stop judgment: the product's to end). `shape` is the category: object-start, spawn-helper,
    run_in_executor, pool."""
    kind, is_thread, indirect, handed = PRODUCT_START, False, False, False

    def __init__(self, unit, node, category, what):
        self.unit, self.node, self.shape, self.why = unit, node, category, what
        self.target = _text(node, unit.module)
        self.line = node.lineno

    def file(self):
        return os.path.relpath(self.unit.module.path, ROOT)

    def describe(self):
        return "%s:%d %s calls %s" % (self.file(), self.line, self.unit.qualname, self.target)


def _param_guards(test, params, wanted):
    """(parameter, wanted) for an if's test that is a bare parameter (`if reconcile:`), its negation (`if not _async:`),
    or an `and` of such (the start needs each); nothing for any other test (the start is then counted as it may happen)."""
    if isinstance(test, ast.Name) and test.id in params:
        return [(test.id, wanted)]
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        return _param_guards(test.operand, params, not wanted)
    if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And) and wanted:
        return [g for v in test.values for g in _param_guards(v, params, True)]
    return []


def _start_guards(fn, starts):
    """The (parameter, wanted) guards over a spawner's .start() calls: an `if` of the function whose body (wanted True) or
    orelse (wanted False) holds a start and whose test names a parameter (_param_guards)."""
    ids = {id(s) for s in starts}
    params = {a.arg for a in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs}
    guards = []
    for node in ast.walk(fn):
        if isinstance(node, ast.If):
            for field, wanted in (("body", True), ("orelse", False)):
                if any(id(n) in ids for s in getattr(node, field) for n in ast.walk(s)):
                    for g in _param_guards(node.test, params, wanted):
                        if g not in guards:
                            guards.append(g)
    return guards


def _guard_note(fn, guards, call, module, product_module):
    """How each `if <parameter>:` guard of a spawner stands at this call: '' with no guard; a clause naming the argument
    handed (or the default) when it is a literal that is on, or saying the start MAY happen when it is not a literal;
    None when a guard is a literal that is off (no thread starts on this call)."""
    if not guards:
        return ""
    parts = []
    for param, wanted in guards:
        arg = _argument_for(fn, param, call)
        default = any(d is arg for d in fn.args.defaults + [d for d in fn.args.kw_defaults if d is not None])
        if isinstance(arg, ast.Constant):
            if bool(arg.value) != wanted:
                return None
            parts.append("%s %s %s" % (param, _text(arg, product_module if default else module), "by default" if default else "handed in"))
        elif arg is None:
            parts.append("%s not read here (a * or ** argument): it may start" % param)
        else:
            parts.append("%s = %s, not a literal: it may start" % (param, _text(arg, product_module if default else module)))
    return " when %s (%s)" % (" and ".join("%s is %s" % (p, "true" if w else "false") for p, w in guards), "; ".join(parts))


def _spawner_calls(unit, call, name):
    """[(head, what starts)] for a test's call of a product SPAWN-HELPER: km.x(...) or a bare product import (the
    module-level functions of that name), a product class construction whose __init__ spawns (sb.SdkBackend(...)), or a
    method of a product object (be.drive_idle_queue(...): the method of be's class, else by name for a product object of
    a class the walk cannot name). A head whose guard is a literal that is off at this call (reconcile left False) is no
    start; one whose guard is not a literal may start and is counted, saying so."""
    prod, f = unit.module.product, call.func
    table = prod.spawners()
    heads, by_name = [], ""
    if _product_call(unit, call):
        if name in prod.classes:
            heads = [h for h in table.get("__init__", []) if h[1] == name]
        else:
            heads = [h for h in table.get(name, []) if h[1] is None]
        file = _alias_file(unit, f, call.lineno)
        if file is False:                      # a load_source of a file outside the product (a tool, a script): not a product function
            heads = []
        elif file is not None:                 # the alias's own file: ru.main is the update CLI's main, not the kernel's
            heads = [h for h in heads if h[0] == file]
        elif heads:
            by_name = " [matched by name: the alias's file is not read]"
    elif isinstance(f, ast.Attribute):
        obj = _product_object(unit, f.value, call.lineno)
        if isinstance(obj, str) and obj != "module":
            defs = prod.methods(obj, name, unit.module)
            heads = [h for h in table.get(name, []) if any(h[2] is fn for _p, _c, fn in defs)]
        elif obj is True:                      # a product object whose class the walk cannot name: every class's method of that name
            heads = [h for h in table.get(name, []) if h[1] is not None]
            if heads:
                by_name = " [matched by name: the object's class is not read]"
    out = []
    for p, cname, fn, guards in heads:
        m = prod.module(p, unit.module)
        note = _guard_note(fn, guards, call, unit.module, m)
        if note is None:
            continue
        ctor = next((n for s in fn.body for n in _run_nodes(s) if isinstance(n, ast.Call) and _names_thread_ctor(n.func)), None)
        target = _target_expr(ctor) if ctor is not None else None
        kind = _callee_name(ctor) if ctor is not None else "Thread"
        what = "%s starts %s(%s)%s%s" % ("%s.%s" % (cname, fn.name) if cname else fn.name, kind,
                                          ("%s=%s" % ("function" if kind == "Timer" else "target", _text(target, m))) if target is not None else "", note, by_name)
        out.append(((p, cname, fn), what))
    return out


def _alias_file(unit, func, line):
    """The product file the callee's module alias binds (km -> kernel/kernel.py; jd or km.jd -> kernel/judge.py; a bare
    import's module; a local alias bound to a load_source(...) the walk follows), so a spawn-helper is matched in that
    file and not by name across the product; False for a load_source of a file outside the product; None when the walk
    cannot tell."""
    m = unit.module
    if isinstance(func, ast.Name):
        return m.product_file(func.id)
    if isinstance(func, ast.Attribute):
        if isinstance(func.value, ast.Name):
            r = m.product_file(func.value.id)
            if r is not None:
                return r
        call = _object_of(unit, func.value, line)
        return m.product_file_of(call) if call is not None else None
    return None


# ── the kind of a thread ────────────────────────────────────────────────────────────────────────────────

def _body_kind(unit, fn_body_nodes, loops, depth, given=None):
    """The kind a function body gives its thread: loop, waits, bounded or UNREADABLE, with the reason. The body is READ: its
    own whiles (not those a clock bounds), iter(f, sentinel) loops, untimed waits, reads and serve_forever calls, and, one
    level down, the bodies of the fakes' methods it calls, of the class's own methods (self.x() in a method read in its
    class's unit), of the module's functions (each in its own unit: its parameters and bindings are its own) and the
    body's, and of the product functions it calls (read in the product sources). A call of a PARAMETER, or through one (`fn()`, `fn(*a)`, `obj.frob()`: _opaque_calls), is work the
    walk cannot see: the body is UNREADABLE (the third arm, romp-manager's ruling of 2026-09-22) unless the argument is in
    hand (`given`: (parameter, its function) -> (the argument, the unit it is written in, that unit's own hands, where it
    was handed, whose parameter), filled at the caller of a helper, at the construction from args= / kwargs=, or at the call
    of a function whose body is read), when the argument is read as a target is and decides the kind; the reason carries
    each hand after ` | `. A library call the walk does not resolve is not followed: bounded then says the body itself,
    and what the walk followed, has no loop and no untimed wait."""
    for sub in fn_body_nodes:
        if isinstance(sub, ast.While):
            if CLOCK.search(ast.unparse(sub.test)) or _clock_break(sub):
                continue
            return "loop", "a while loop"
        if isinstance(sub, (ast.For, ast.AsyncFor)) and isinstance(sub.iter, ast.Call) and _callee_name(sub.iter) == "iter" and len(sub.iter.args) == 2:
            return "loop", "iterates iter(f, sentinel)"
    for sub in fn_body_nodes:
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
            if sub.func.attr in BLOCKING and _untimed_call(sub.func.attr, sub.args, [(k.arg, k.value) for k in sub.keywords]):
                return "waits", "an untimed .%s(%s)" % (sub.func.attr, _args_text(sub, unit.module))
            if sub.func.attr in READS:
                return "waits", "a read of .%s()" % sub.func.attr
            if sub.func.attr in FOREVER:
                return "loop", sub.func.attr
    hands, unread = [], None          # a loop or a waits found anywhere is the verdict; else the first unreadable callee or hand; else bounded
    if depth < 2:
        for sub in fn_body_nodes:
            if isinstance(sub, ast.Call):
                nm = _callee_name(sub)
                methods = _method_calls_in(unit, [sub], sub.lineno)              # f.run(), where f is a fake of the module
                if methods:
                    for m, _owner in methods:
                        r = _reader(unit, m)
                        k, why = _body_kind(r, list(ast.walk(m)), loops, depth + 1,
                                            {**_instance_given(unit, sub.func.value, given),
                                             **_call_given(m, sub, unit, r, given, unbound=_through_class(unit, sub.func, m))})
                        if k in ("loop", "waits"):
                            return k, "calls %s, %s" % (_text(sub.func, unit.module), why)
                        if k == KIND_UNREAD:
                            unread = unread or (k, "calls %s, %s" % (_text(sub.func, unit.module), why))
                        else:
                            hands += why.split(" | ")[1:]
                    continue
                own = _own_method(unit, sub)                                     # self._serve(), in a method read in its class
                if own is not None:
                    r = _reader(unit, own)
                    k, why = _body_kind(r, list(ast.walk(own)), loops, depth + 1, _call_given(own, sub, unit, r, given))
                    if k in ("loop", "waits"):
                        return k, "calls %s, %s" % (_text(sub.func, unit.module), why)
                    if k == KIND_UNREAD:
                        unread = unread or (k, "calls %s, %s" % (_text(sub.func, unit.module), why))
                    else:
                        hands += why.split(" | ")[1:]
                    continue
                fn = unit.local_defs.get(nm) or (unit.parent.local_defs.get(nm) if unit.parent is not None else None)
                bound = unit.binding_at(nm, sub.lineno) if nm is not None and fn is None else None
                r = None
                if fn is not None:                                               # a def of the body: a closure over the same hands
                    r = _body_kind(unit, list(ast.walk(fn)), loops, depth + 1, {**(given or {}), **_call_given(fn, sub, unit, unit, given)})
                elif isinstance(sub.func, ast.Lambda) or (bound is not None and isinstance(bound[1], ast.Lambda)):
                    lam = sub.func if isinstance(sub.func, ast.Lambda) else bound[1]     # (lambda: fn())(); worker = lambda: fn(); worker()
                    r = _body_kind(unit, list(ast.walk(lam)), loops, depth + 1, {**(given or {}), **_call_given(lam, sub, unit, unit, given)})
                    nm = nm or "a lambda"
                elif nm in unit.module.functions:                                # a module function: read in its own unit
                    fn = unit.module.functions[nm]
                    fu = unit.module.unit_for(fn)
                    r = _body_kind(fu, list(ast.walk(fn)), loops, depth + 1, _call_given(fn, sub, unit, fu, given))
                elif nm in loops and nm not in BUILTIN_METHODS and _module_call(unit, sub):
                    return "loop", "calls %s, a product function with a while loop" % nm
                elif nm not in BUILTIN_METHODS and _product_call(unit, sub):    # km.x(): the product function, read
                    r = _product_kind(unit, sub.func, sub.lineno, depth + 1, call=sub, given=given)
                    if r is not None and r[0] == KIND_UNREAD and OPAQUE_MARK not in r[1]:
                        r = None            # a product callee unreadable for another reason is not followed, as before; one whose
                if r is None:               # work is a parameter no hand supplies is opaque work, carried up
                    continue
                k, why = r
                if k in ("loop", "waits"):
                    return k, "calls %s, %s" % (nm, why)
                if k == KIND_UNREAD:
                    unread = unread or (k, "calls %s, %s" % (nm, why))
                else:
                    hands += why.split(" | ")[1:]
    for name, owner, road, call, others, shown, through in _opaque_calls(unit, fn_body_nodes):
        alt = [_road_kind(unit, o, suffix, given, call, depth + 1, _fn_label(owner)) for o, suffix in others]
        pinned = next((a for a in alt if a[0] in ("loop", "waits")), None)      # `(fn or _loop)()`: the other operand may run
        if pinned is not None:
            return pinned[0], "calls %s, %s" % (shown, pinned[1])
        r = _given_kind(given, name, depth, owner, road, call)
        if r is None and "bound in " in through and _is_product_unit(unit) and road and isinstance(road[-1], str):
            by_name = _by_name_kind(unit, road[-1], depth)                    # self.backend._update_reg(): a product object's
            if by_name is not None:                                            # collaborator the product's own spawn handed in
                k, why = by_name
                why = "calls %s, %s%s %s no hand supplies: %s" % (shown, through, OPAQUE_MARK, _fn_label(owner), why)
                if k in ("loop", "waits"):
                    return k, why
                if k == KIND_UNREAD:
                    unread = unread or (k, why)
                continue
        if r is None:
            unread = unread or (KIND_UNREAD, "calls %s, %s%s %s: what the caller hands in is not read here"
                                % (shown, through, OPAQUE_MARK, _fn_label(owner)))
            continue
        k, why, hand = r
        if k in ("loop", "waits"):
            return k, "%s | %s" % (why, hand)
        if k == KIND_UNREAD:
            unread = unread or (k, "%s | %s" % (why, hand))
            continue
        other = next((a for a in alt if a[0] == KIND_UNREAD), None)
        if other is not None:
            unread = unread or (KIND_UNREAD, "calls %s, %s" % (shown, other[1]))
            continue
        hands += [hand] + why.split(" | ")[1:]
    if unread is not None:
        return unread
    return "bounded", " | ".join(["no loop, no untimed wait"] + hands)


OPAQUE_MARK = "a parameter of"      # the words of the third arm's reason: a product callee's such verdict is carried up


def _fn_label(fn):
    """A function's name for a reason: a def's own, `a lambda` for a lambda."""
    return "a lambda" if isinstance(fn, ast.Lambda) else fn.name


def _own_params(fn):
    """The parameter names of a def or a lambda (positional, keyword-only), self and cls excluded: the instance is the
    class's, read by its methods, not a value a hand supplies."""
    a = fn.args
    return [x.arg for x in a.posonlyargs + a.args + a.kwonlyargs if x.arg not in ("self", "cls")]


def _star_params(fn):
    """The *args and **kwargs names of a def or a lambda: parameters too (an element of `*fns`, a value of `**kw`, is what
    the caller handed, behind a * the hands never place)."""
    a = fn.args
    return [x.arg for x in (a.vararg, a.kwarg) if x is not None]


def _own_stmts(fn):
    """The statements of a def's OWN body at any depth (inside its ifs, fors, withs, tries), not those of the defs and
    classes it defines; nothing for a lambda."""
    if isinstance(fn, ast.Lambda):
        return
    stack = list(reversed(fn.body))
    while stack:
        s = stack.pop()
        yield s
        if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        blocks = [getattr(s, f, None) for f in ("body", "orelse", "finalbody")]
        blocks += [h.body for h in getattr(s, "handlers", []) or []] + [c.body for c in getattr(s, "cases", []) or []]
        for b in reversed(blocks):
            if isinstance(b, list):
                stack.extend(reversed([x for x in b if isinstance(x, ast.stmt)]))


def _shadows(fn, name):
    """The function's OWN body (not a nested def's) SHADOWS `name` with a def, a class, an import or an except target: a
    call of the name is that object's, not the parameter's. An assignment, a for, a with, a comprehension or a walrus
    target is a BINDING the walk follows instead (_root_param: `fn = fn or _once` binds fn to an expression rooted at the
    parameter, `g = fn` to an alias of it)."""
    if isinstance(fn, ast.Lambda):
        return False
    for s in _own_stmts(fn):
        if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and s.name == name:
            return True
        if isinstance(s, (ast.Import, ast.ImportFrom)) and any((al.asname or al.name.split(".")[0]) == name for al in s.names):
            return True
        if any(h.name == name for h in getattr(s, "handlers", []) or []):
            return True
    return False


def _binding_skipping(unit, name, line, skip, owner=None):
    """_Unit.binding_at, but never the binding `skip` (the assignment whose value is being resolved: `fn = fn or _once`
    reads its right side's fn as the binding BEFORE it, the parameter when there is none), and, for a PARAMETER (`owner`
    its def or lambda), only a binding at or before the use and only in the scopes out to the owner's own: a parameter is
    a local of its function, so an enclosing scope's same-named binding is invisible to it (`wrap(i, fn)`'s fn is wrap's,
    not the comprehension target of the function around it), and a rebinding after the use does not reach a call before
    it."""
    for scope in unit.scope_chain(unit.scope_at(line)):
        vals = [lv for lv in unit.scopes.get(id(scope), {}).get(name, []) if lv is not skip]
        if vals:
            before = [lv for lv in vals if lv[0] <= line]
            if before:
                return before[-1]
            if owner is None:
                return vals[0]
        if owner is not None and scope is owner:
            return None
    if unit.parent is not None and (owner is None or scope is not owner):
        return _binding_skipping(unit.parent, name, line, skip, owner)
    return None


ITEM, RESULT, UNNAMED = ("item",), ("result",), ("unnamed",)      # the ROAD steps that are not an attribute's name
KEY_METHODS = ("get", "pop", "setdefault")                      # a container's element by key: `d.get("k")`, an ITEM step by key
CONTAINER_METHODS = ("items", "keys", "values", "get", "pop", "popitem", "setdefault", "update", "copy", "clear", "append",
                     "extend", "insert", "remove", "index", "count", "sort", "reverse", "discard", "add")


def _road_text(road):
    """A road rendered after a name or a hand: `.frob` for an attribute, `[]` for an element (by index, by key, or any),
    `()` for a call's result, `.<name>` for an attribute the walk cannot name."""
    return "".join(("." + s) if isinstance(s, str) else "[]" if s[0] in ("item", "key") else {RESULT: "()", UNNAMED: ".<name>"}[s] for s in road)


def _step(r, step):
    """The root `r` one step further along: the step appended to its road and to the suffix of every OTHER expression
    (the operands beside the parameter in an `or`, the elements beside a *spread), which the same steps apply to."""
    if r is None:
        return None
    name, owner, road, others, via = r
    return name, owner, road + (step,), [(o, suffix + (step,)) for o, suffix in others], via


def _root_param(unit, node, line, params, depth=0, skip=None):
    """(the parameter's name, its def or lambda, the ROAD from the parameter to `node`, the OTHER expressions that may run
    in its place, each with the road suffix that applies to it, the indirection's text for the reason) when `node`, an
    expression written in `unit` at `line`, is ROOTED at a parameter in `params` (name -> its def or lambda): the
    parameter itself (`fn`); an attribute of it (a step per attribute: `obj.a.b`); an element of it (`fns[0]`, `kw["fn"]`,
    `d.get("k")`, `d.pop("k")`, `d.setdefault("k", v)`: an ITEM step, by the constant index or key when there is one); a
    name bound over it (a local alias `g = fn`, a for or comprehension target `for f in fns`, an unpacked element `a, b =
    pair`: the binding in force, followed, never the assignment being resolved, so `fn = fn or _once` reads its fn as the
    parameter, and never a binding beyond the parameter's own function); an operand of a BoolOp or an IfExp (`fn or _once`,
    `fn if flag else _once`: the other operands are what may run instead, and the steps after the operator apply to them
    too: `(d.get("nodes") or {}).get(k)` reads `{}`.get as well); a *spread of it into a container the body then iterates
    or indexes (`(*fns, _once)`: the other elements likewise); functools.partial over it (the callable is partial's first
    argument); getattr(it, "name") (an attribute step by a literal name, else an UNNAMED step); any other call on it whose
    RESULT is then used (`fn()()`, `obj.make()()`: a RESULT step). None when nothing on the road is a parameter."""
    if depth > 8 or node is None:
        return None
    if isinstance(node, ast.Name):
        if node.id in ("self", "cls"):
            return None
        owner = params.get(node.id)
        b = _binding_skipping(unit, node.id, line, skip, owner)
        if b is None:
            return (node.id, owner, (), [], "") if owner is not None else None
        r = _root_param(unit, b[1], b[0], params, depth + 1, skip=b)
        if r is None or isinstance(b[1], tuple):        # a for / unpack target: the tuple case below says "an element of"
            return r
        name, owner, road, others, via = r
        return name, owner, road, others, "bound to `%s`, %s" % (_text(b[1], unit.module), via)
    if isinstance(node, tuple):
        if node[0] in ("for", "unpack"):
            r = _step(_root_param(unit, node[1], line, params, depth + 1, skip), ITEM)
            if r is None:
                return None
            name, owner, road, others, via = r
            return name, owner, road, others, "an element of `%s`, %s" % (_text(node[1], unit.module), via)
        return None
    if isinstance(node, ast.Attribute):
        return _step(_root_param(unit, node.value, line, params, depth + 1, skip), node.attr)
    if isinstance(node, ast.Subscript):
        key = node.slice.value if isinstance(node.slice, ast.Constant) else None
        return _step(_root_param(unit, node.value, line, params, depth + 1, skip), ("key", key) if key is not None else ITEM)
    if isinstance(node, ast.Starred):
        return _root_param(unit, node.value, line, params, depth + 1, skip)
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        for e in node.elts:
            if isinstance(e, ast.Starred):
                r = _root_param(unit, e.value, line, params, depth + 1, skip)
                if r is not None:
                    name, owner, road, others, via = r
                    return name, owner, road, others + [(x, ()) for x in node.elts if x is not e], "spread from %s, %s" % (_text(e.value, unit.module), via)
        return None
    if isinstance(node, (ast.BoolOp, ast.IfExp)):
        operands = node.values if isinstance(node, ast.BoolOp) else [node.body, node.orelse]
        for op in operands:
            r = _root_param(unit, op, line, params, depth + 1, skip)
            if r is not None:
                name, owner, road, others, via = r
                return name, owner, road, others + [(x, ()) for x in operands if x is not op], "one of which is %s, %s" % (_text(op, unit.module), via)
        return None
    if isinstance(node, ast.Call):
        f, nm = node.func, _callee_name(node)
        if nm == "partial" and node.args:                                       # functools.partial(fn, 1): fn is what runs
            r = _root_param(unit, node.args[0], line, params, depth + 1, skip)
            return None if r is None else (r[0], r[1], r[2], r[3], "over %s, %s" % (_text(node.args[0], unit.module), r[4]))
        if isinstance(f, ast.Name) and f.id == "getattr" and len(node.args) >= 2:
            r = _root_param(unit, node.args[0], line, params, depth + 1, skip)
            if r is None:
                return None
            attr = node.args[1]
            step = attr.value if isinstance(attr, ast.Constant) and isinstance(attr.value, str) else UNNAMED
            return _step((r[0], r[1], r[2], r[3], "an attribute of %s, %s" % (_text(node.args[0], unit.module), r[4])), step)
        if isinstance(f, ast.Attribute) and nm in KEY_METHODS and node.args:    # d.get("k"): the element under the key
            key = node.args[0].value if isinstance(node.args[0], ast.Constant) else None
            r = _root_param(unit, f.value, line, params, depth + 1, skip)
            return None if r is None else _step((r[0], r[1], r[2], r[3], "an element of %s, %s" % (_text(f.value, unit.module), r[4])),
                                                ("key", key) if key is not None else ITEM)
        r = _root_param(unit, f, line, params, depth + 1, skip)
        return None if r is None else _step((r[0], r[1], r[2], r[3], "the result of a call on %s, %s" % (_text(f, unit.module), r[4])), RESULT)
    return None


def _self_bound_params(unit):
    """{attribute: (the parameter's name, its method, the road, the other expressions, the indirection's text, the value's
    text)} for every `self.<attr> = <expression rooted at a parameter of the method>` in the unit's class or a base in
    the module (`__init__(self, fn): self.fn = fn`; a setUp's or a configure's alike; `self.fn = fn or _once` with _once
    as the other): a call of self.<attr> in a method read in the class's unit runs what that method was handed
    (_opaque_calls), and its hand is the construction's argument (_instance_given). The first binding of an attribute in
    source order names it. Memoised per unit."""
    cached = getattr(unit, "_self_bound", None)
    if cached is not None:
        return cached
    out = {}
    if unit.cls is not None:
        for c in unit.module.bases_of(unit.cls):
            for m in c.body:
                if not isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                own = {p_: m for p_ in _own_params(m) + _star_params(m) if not _shadows(m, p_)}
                if not own:
                    continue
                mu = _reader(unit, m)
                for s in sorted(_own_stmts(m), key=lambda s: s.lineno):
                    if isinstance(s, ast.Assign):
                        for t in s.targets:
                            if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id in ("self", "cls") and t.attr not in out:
                                r = _root_param(mu, s.value, s.lineno, own)
                                if r is not None:
                                    out[t.attr] = r + (_text(s.value, mu.module),)
    unit._self_bound = out
    return out


def _is_product_unit(unit):
    """The unit reads a function of the product sources (kernel/, postal/, cli/, bin/), not of a test module."""
    rel = os.path.relpath(unit.module.path, ROOT).split(os.sep)
    return rel[0] in PRODUCT_DIRS + ("bin",)


def _by_name_kind(unit, method, depth):
    """(kind, reason) for a method called on a PRODUCT object's constructor collaborator no hand supplies (`self.backend
    ._update_reg()` in SdkSession, `backend` a parameter of its __init__ handed by the product's own spawn, not by the test):
    the method read BY NAME across the product, every product function of that name in its own module's unit, joined on the
    restricted side (the docstring's rule for a product method not on the object's class in its file); None when no product
    function of that name exists."""
    prod = unit.module.product
    heads = prod.functions.get(method, []) if prod is not None else []
    if not heads or depth > 6:
        return None
    answers = []
    for p, c, f in heads:
        pu = prod.module(p, unit.module).unit_for(f, c)
        answers.append(_body_kind(pu, list(ast.walk(f)), unit.module.loops, depth + 1))
    k, why = _join_kind_answers(answers)
    return k, "%s read by name across the product, %d definition%s: %s" % (method, len(answers), "" if len(answers) == 1 else "s", why)


def _opaque_calls(unit, nodes):
    """The calls that RUN when a read body runs whose callee is a PARAMETER or is reached through one: [(the parameter's
    name, the def or lambda whose parameter it is, the ROAD from the parameter to the callable, the call, the OTHER
    expressions that may run in its place, the callee's text, the indirection's words for the reason)], each (name,
    owner, road) once, in source order. The callee is rooted at a parameter (_root_param) when it is the parameter (`fn()`,
    `fn(*a)`), an attribute of one (`obj.frob()`, `obj.a.b()`), an element of one (`fns[0]()`, `kw["fn"]()`), a name bound
    over one (a local alias `g = fn; g()`, a for or comprehension target `for f in fns: f()`, `[f() for f in fns]`), an
    operand beside one (`(fn or _once)()`, `(fn if flag else _once)()`), an element of a *spread of one (`for f in (*fns,
    _once)`), functools.partial over one (`partial(fn, 1)()`), getattr over one (`getattr(obj, "run")()`, `getattr(obj,
    name)()`), or the result of a call on one (`fn()()`); and when it is `self.<attr>` in a method read in its class's
    unit whose <attr> a method of the class binds from its own parameter (`self.fn = fn` in __init__, then `self.fn()`:
    _self_bound_params; not when <attr> is a method of the class, the method road's). `nodes` is ast.walk of the body's
    def or lambda; the parameters in scope are its own (positional, keyword-only, *args, **kwargs: a method of the *args
    tuple or the **kwargs dict ITSELF, `kw.items()`, `args.count(x)`, is a builtin container's and not opaque; an element
    of one, `args[0]()`, `kw["fn"]()`, `for f in kw.values(): f()`, is) and those of the unit's
    function and its parent's (a def of a helper's body calls the helper's parameter through its closure); a name the body
    SHADOWS with a def, a class, an import or an except target is not the parameter (_shadows), a name it rebinds by
    assignment is followed to what it was bound to; self and cls are not parameters here. The defs and lambdas the body
    only DEFINES are not entered (the census's rule for what runs, _run_nodes): a def or a name-bound lambda the body calls
    is read at that call with the call's hands (_body_kind's callee loop), a returned one where its caller runs it
    (_call_target), one handed to a library call (`sorted(rows, key=lambda r: r.get("t"))`) is inside a call the walk does
    not follow, and a thread target inside a product spawn-helper is that thread's, counted as a product-start row."""
    root = nodes[0] if nodes else None
    params, stars = {}, set()
    fns = [s.fn for s in (unit.parent, unit) if s is not None]          # outermost first: an inner def's parameter shadows
    if isinstance(root, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) and not any(root is f for f in fns):
        fns.append(root)
    for fn in fns:
        params = {p_: o for p_, o in params.items() if not _shadows(fn, p_)}
        for p_ in _own_params(fn):
            if not _shadows(fn, p_):
                params[p_] = fn
                stars.discard((p_, id(fn)))
        for p_ in _star_params(fn):
            if not _shadows(fn, p_):
                params[p_] = fn
                stars.add((p_, id(fn)))
    bound = _self_bound_params(unit)
    out, seen = [], set()
    stack = [root] if root is not None else []
    while stack:
        n = stack.pop()
        if isinstance(n, ast.Call):
            head, chain = n.func, []
            while isinstance(head, ast.Attribute):
                chain.append(head.attr)
                head = head.value
            chain.reverse()
            if isinstance(head, ast.Name) and head.id in ("self", "cls") and chain and chain[0] in bound \
                    and unit.cls is not None and unit.method_of(unit.cls, chain[0]) is None:
                name, method, road, others, via, value = bound[chain[0]]
                r = (name, method, road, others, "bound in %s to `%s`, %s" % (method.name, value, via))
                for a in chain[1:]:
                    r = _step(r, a)
            else:
                r = _root_param(unit, n.func, getattr(n, "lineno", 0), params)
            if r is not None:
                name, owner, road, others, via = r
                key = (name, id(owner), road)
                if (name, id(owner)) in stars and len(road) == 1 and road[0] in CONTAINER_METHODS:
                    continue                        # kw.items(), args.count(x): a method of the *args tuple or **kwargs dict itself
                if key not in seen:
                    seen.add(key)
                    through = via if via else ((name + " ") if road else "")
                    out.append((name, owner, road, n, others, _text(n.func, unit.module), through))
        for c in ast.iter_child_nodes(n):
            if c is not root and isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                continue                            # defined here, run elsewhere (or at a call of it, read there)
            stack.append(c)
    out.sort(key=lambda r: (getattr(r[3], "lineno", 0), getattr(r[3], "col_offset", 0)))
    return out


def _instance_given(unit, recv, given=None):
    """The hands a FAKE'S CONSTRUCTION supplies for its __init__'s parameters, for a method of the fake read through the
    instance `recv` (f.run, self.fake.run, _F(_loop).run, with f bound to `_F(_loop)` and `class _F: def __init__(self, fn):
    self.fn = fn`): the construction the instance is bound to (_object_of), its arguments written in `unit` under its hands
    `given`, keyed on __init__ as `handed in at the construction`, so a `self.fn()` in the method (_self_bound_params) is
    read from `_loop`; likewise for a PRODUCT class the test constructs itself (`s = sb.SdkSession(be, ...)`: its __init__
    in the product, one definition), so `self.backend._update_reg()` in a method of s is read from `be`. Nothing when the
    instance is the unit's own self, is not bound to a construction of a class the walk can name, or the class has no
    __init__ of its own (a product object the product's own spawn built has no hand: _by_name_kind reads its
    collaborators' methods by name)."""
    if recv is None or (isinstance(recv, ast.Name) and recv.id in ("self", "cls")):
        return {}
    line = getattr(recv, "lineno", 0)
    call = _object_of(unit, recv, line)
    if not isinstance(call, ast.Call):
        return {}
    cls = _class_of(unit, recv, line)
    if cls is not None:                                   # a class of the test module
        init = unit.method_of(cls, "__init__")
        if init is None or _class_of(unit, call, line) is not cls:
            return {}
        return _given_from(init, call, unit, _reader(unit, init), given, "handed in at the construction")
    obj = _product_object(unit, recv, line)               # a product class built by the test: sb.SdkSession(be, ...)
    if isinstance(obj, str) and unit.module.product is not None and _callee_name(call) == obj:
        heads = unit.module.product.methods(obj, "__init__", unit.module)
        if len(heads) == 1:
            p, c, f = heads[0]
            return _given_from(f, call, unit, unit.module.product.module(p, unit.module).unit_for(f, c), given, "handed in at the construction")
    return {}


def _given_from(fn, call, unit, callee_unit, given, where):
    """{(parameter, id(fn)): (the argument, the unit it is written in, that unit's own hands, `where`, fn's label)} for the
    parameters of `fn` a call hands values to (_argument_for: by keyword, by position with a method's self excluded,
    else the parameter's default, read in the callee's own unit as `its default`); nothing for a parameter the walk cannot
    place (behind a * or ** argument, or a required one not handed)."""
    out, label = {}, _fn_label(fn)
    defaults = fn.args.defaults + [d for d in fn.args.kw_defaults if d is not None]
    for p_ in _own_params(fn):
        arg = _argument_for(fn, p_, call)
        if arg is None:
            continue
        if any(d is arg for d in defaults):
            out[(p_, id(fn))] = (arg, callee_unit, None, "its default", label)
        else:
            out[(p_, id(fn))] = (arg, unit, given, where, label)
    return out


def _call_given(fn, call, unit, callee_unit, given=None, unbound=False):
    """The hands a CALL in a body the walk reads supplies for the callee's parameters (`_until(lambda: ...)`, `f.run(x)`,
    `jd._run_tier(build, ...)`): the arguments are written in `unit` under its hands `given`; `unbound` drops the instance
    handed first to a method reached through its class (`_Child._pump(child)`)."""
    if unbound:
        call = ast.Call(func=call.func, args=list(call.args[1:]), keywords=list(call.keywords))
    return _given_from(fn, call, unit, callee_unit, given, "handed in at the call")


def _ctor_given(fn, ctor, ctor_unit, given=None, unbound=False):
    """The hands a CONSTRUCTION supplies through args= / kwargs= for the parameters of the def or lambda it runs
    (`Thread(target=run, args=(km._dismiss_lane, SID4))`), written in the construction's unit under its hands `given`;
    nothing when the walk cannot read them (_handed_args None); `unbound` drops the instance handed first to a method
    reached through its class."""
    handed = _handed_args(ctor, ctor_unit) if ctor is not None and fn is not None else None
    if handed is None:
        return {}
    pos, kws = handed
    call = ast.Call(func=ast.Name(id="_", ctx=ast.Load()), args=list(pos[1:] if unbound else pos),
                    keywords=[ast.keyword(arg=k, value=v) for k, v in kws])
    return _given_from(fn, call, ctor_unit, ctor_unit, given, "handed in at the construction")


def _through_class(unit, func, fn):
    """The call `func(...)` reaches the method `fn` through its CLASS by name (`_Child._pump(child)`), so the first argument
    is the instance: not for a staticmethod or a classmethod."""
    return isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and unit.class_named(func.value.id) is not None \
        and not _decorated(fn, "staticmethod") and not _decorated(fn, "classmethod")


_LITERALS = (ast.Dict, ast.List, ast.Set, ast.Tuple, ast.Constant, ast.JoinedStr, ast.ListComp, ast.SetComp, ast.DictComp)


def _data_of(unit, node, line, depth=0):
    """The LITERAL an expression is, or is bound to: a dict, list, set, tuple, constant, f-string or comprehension written
    in the source, through a name's binding, a module global (a product module's `_cache = {}` in its own unit), an
    attribute on self bound across the class, or a subscript's holder; None for anything else (a call, a parameter, a
    for-target)."""
    if depth > 8 or node is None:
        return None
    if isinstance(node, _LITERALS):
        return node
    if isinstance(node, ast.Subscript):
        return _data_of(unit, node.value, line, depth + 1)
    if isinstance(node, ast.Name):
        b = unit.binding_at(node.id, line)
        if b is not None:
            return None if isinstance(b[1], tuple) else _data_of(unit, b[1], b[0], depth + 1)
        g = unit.module.globals.get(node.id)
        return _data_of(unit, g, g.lineno, depth + 1) if g is not None else None
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in ("self", "cls"):
        for v in unit.class_bindings(node.attr):
            r = _data_of(unit, v, v.lineno, depth + 1)
            if r is not None:
                return r
    if isinstance(node, ast.Call):                        # jd._pass_acc(), _make_store(): the ONE literal every return returns
        return _returned_literal(unit, node, line, depth + 1)
    return None


def _returned_literal(unit, call, line, depth):
    """The literal a call returns, when the walk reads its callee (a def of the body, a module function, a lambda, a helper
    module's function: callee_of; a product module's function through its alias, one definition) and EVERY return of it
    is a literal of one type: `def _pass_acc(): return {"cpuS": 0.0, "failures": [], ...}` is a dict whose "failures" is a
    list. None otherwise (a function with a non-literal return, several definitions, a method, a library call)."""
    if depth > 8:
        return None
    heads = []
    callee = unit.callee_of(call, line)
    if callee is not None:
        heads = [callee]
    elif unit.module.product is not None and _callee_name(call) not in BUILTIN_METHODS and _product_call(unit, call):
        prod = unit.module.product
        found = [(p, c, f) for p, c, f in prod.functions.get(_callee_name(call), []) if c is None]
        if len(found) == 1:
            p, c, f = found[0]
            heads = [(f, prod.module(p, unit.module).unit_for(f, c))]
    if len(heads) != 1:
        return None
    fn, u = heads[0]
    rets = [fn.body] if isinstance(fn, ast.Lambda) else list(_returns(fn))
    lits = [_data_of(u, v, getattr(v, "lineno", line), depth + 1) for v in rets]
    if not lits or any(l is None for l in lits) or any(type(l) is not type(lits[0]) for l in lits):
        return None
    if not hasattr(lits[0], "_unit"):
        lits[0]._unit = u                                 # written in the callee's module: its elements are read there (_road_kind)
    return lits[0]


def _given_kind(given, name, depth, owner=None, road=(), call=None):
    """(kind, reason, the hand as text) for the argument a parameter was given (`given`, keyed (name, id(owner)); by name
    alone when `owner` is None: a Name in a body read under those hands); None when no hand supplies it. A constant is no
    callable to run (a call of it raises at once, and the thread ends): bounded. The parameter CALLED (`fn()`, road ())
    is read as a target is, in the unit it is written in and under that unit's own hands (_expr_kind); a road from it
    (`s.frob()`: ("frob",); `fns[0]()`: (ITEM,); `getattr(obj, name)()`: (UNNAMED,); `fn()()`: (RESULT,); `call` the
    call) is followed over the hand (_road_kind): a hand that is itself a parameter of the unit it is written in follows
    that unit's own hands first (`_land(s)` handed the test's s); a LITERAL hand (a dict, a list, a string, a constant:
    _data_of) is data, whose methods return at once (a dict's get is not a Queue's) and whose elements are each read; any
    other is the attribute over the argument as written (_attribute_kind: a fake's method by its body, a product object's
    method in its module, a stdlib object's by the tables, the call's own arguments deciding an untimed wait; UNREADABLE
    for an object the walk does not read: a scandir entry, a client dict a product function built)."""
    if not given:
        return None
    if owner is not None:
        g = given.get((name, id(owner)))
    else:
        g = next((v for (n, _o), v in given.items() if n == name), None)
    if g is None:
        return None
    node, u, outer, where, label = g
    dotted = _road_text(road)
    hand = "%s%s of %s is `%s`%s %s" % (name, dotted, label, _text(node, u.module), dotted, where)
    if isinstance(node, ast.Constant) and not road:
        return "bounded", "a constant `%s`, not a callable: a call of it raises at once and the thread ends" % _text(node, u.module), hand
    if road:
        if isinstance(node, ast.Name) and (node.id in u.params or (u.parent is not None and node.id in u.parent.params)):
            inner = _given_kind(outer, node.id, depth + 1, None, road, call)     # the hand is a parameter: its own hand
            if inner is not None:
                return inner[0], "%s | %s" % (inner[1], inner[2]), hand
        k, why = _road_kind(u, node, road, outer, call, depth, label)
        return k, why, hand
    k, why = _expr_kind(u, node, getattr(node, "lineno", 0), depth + 1, None, None, outer)
    return k, why, hand


def _road_kind(u, node, road, given, call, depth, label="the body"):
    """(kind, reason) for what a ROAD leads to from a hand `node`, written in `u` under its hands `given` (`label` the
    parameter's function, for the reason): no step left, the hand read as a target is (_expr_kind); attribute steps, the
    attribute over the hand as written (_attribute_kind: a fake's method by its body, a product object's method in its
    module, a stdlib object's by the tables, `call` the call's own arguments; a LITERAL hand's method returns at once); an
    ITEM step, each element of a literal container in hand (a list, tuple or set's elements, a dict's values, a
    comprehension's element: _data_of, which follows a helper's or a product function's returned literal), or the one
    element under a constant index or key (`fns[0]`, `d.get("nodes")`: every element when the key is not in the literal),
    read on with the rest of the road and joined on the restricted side (an EMPTY literal is bounded: nothing runs from
    it, a subscript or a later call raises and the thread ends; so is an element of a string or number constant: a
    character, or an error), UNREADABLE for a hand that is not a literal container
    (or one with a *spread); an UNNAMED step (getattr by a name the walk
    cannot read) or a RESULT step (a call on the hand, then a use of what it returned) is UNREADABLE. Each unreadable
    reason carries OPAQUE_MARK: it is opaque work through a parameter, carried up from a product callee."""
    line, shown = getattr(node, "lineno", 0), _text(node, u.module)
    if not road:
        return _expr_kind(u, node, line, depth + 1, None, None, given)
    if depth > 8:
        return KIND_UNREAD, "a road too deep to follow (%s %s)" % (OPAQUE_MARK, label)
    step = road[0]
    if step == ITEM or step[0] == "key":
        lit = _data_of(u, node, line)
        lu = getattr(lit, "_unit", u)                     # a literal a helper or a product function returned: read where it is written
        elts = None
        if isinstance(lit, ast.Dict):
            elts = lit.values
            if step != ITEM:
                hit = [v for k, v in zip(lit.keys, lit.values) if isinstance(k, ast.Constant) and k.value == step[1]]
                elts = hit or elts
        elif isinstance(lit, (ast.List, ast.Tuple, ast.Set)):
            elts = lit.elts
            if step != ITEM and isinstance(step[1], int) and not isinstance(step[1], bool) and -len(elts) <= step[1] < len(elts):
                elts = [elts[step[1]]]
        elif isinstance(lit, (ast.ListComp, ast.SetComp)):
            elts = [lit.elt]
        elif isinstance(lit, (ast.Constant, ast.JoinedStr)):   # `msg["type"][0]` on a string: a character or an error, nothing to run
            return "bounded", "an element of the constant `%s`: a character, or an error that ends the thread; nothing to run" % shown
        if elts is None:
            return KIND_UNREAD, "an element of `%s`, which the walk does not read as a container of callables (%s %s)" % (shown, OPAQUE_MARK, label)
        if any(isinstance(e, ast.Starred) for e in elts):
            return KIND_UNREAD, "an element of `%s`, a container with a *spread the walk does not read (%s %s)" % (shown, OPAQUE_MARK, label)
        if not elts:                                      # `{}`.get(k) is None, `[]` iterates nothing: whatever follows raises or skips
            return "bounded", "an element of `%s`, an empty literal: nothing to run" % shown
        return _join_kind_answers([_road_kind(lu, e, road[1:], given if lu is u else None, call, depth + 1, label) for e in elts])
    if step == UNNAMED:
        return KIND_UNREAD, "an attribute of `%s` named by a value the walk does not read (%s %s)" % (shown, OPAQUE_MARK, label)
    if step == RESULT:
        return KIND_UNREAD, "the result of a call on `%s`, which the walk does not read (%s %s)" % (shown, OPAQUE_MARK, label)
    attrs = []
    while road and isinstance(road[0], str):
        attrs.append(road[0])
        road = road[1:]
    if not road:
        lit = _data_of(u, node, line)
        if lit is not None:
            return "bounded", "a literal %s handed in: its .%s returns at once (a dict's get is not a Queue's; an attribute it lacks raises)" % (type(lit).__name__.lower(), ".".join(attrs))
    expr = node
    for attr in attrs:
        expr = ast.copy_location(ast.Attribute(value=expr, attr=attr, ctx=ast.Load()), node)
        shown = "%s.%s" % (shown, attr)
        expr._shown = shown
    if road:
        return _road_kind(u, expr, road, given, call, depth + 1, label)
    return _attribute_kind(u, expr, line, None, None, given, call)


def _unbound_target(start, fn):
    """The start's target reaches the method `fn` through its class by name (`_Child._pump` with the instance first in
    args=): not for a staticmethod or a classmethod."""
    expr = start.target_expr
    return isinstance(expr, ast.Attribute) and isinstance(expr.value, ast.Name) and start.ctor_unit.class_named(expr.value.id) is not None \
        and not _decorated(fn, "staticmethod") and not _decorated(fn, "classmethod")


def _attribute_kind(unit, node, line, ctor=None, ctor_unit=None, given=None, call=None):
    """(kind, reason) for an attribute in hand as a callable (an argument at a caller, at a construction or at a call:
    km._push_all, self.be.move, f.run, self.dispatch, ev.set, srv.serve_forever), read as a target is (_target_kind's
    roads; the construction's args= apply when `ctor` is the construction that runs it): a method of a class of the
    module (or of the unit's own class) by its body, then the name rules (serve_forever; an untimed wait, read from the
    call's own arguments when `call` is the call of the method on the hand, from args= when a construction runs it, and
    untimed to the walk with neither; a read), a product function in its module, a stdlib method by the tables;
    UNREADABLE otherwise (a method of a parameter no hand supplies)."""
    loops = unit.module.loops
    fn, _owner = _method_call(unit, node, [], line)
    if fn is None and isinstance(node.value, ast.Name) and node.value.id in ("self", "cls") and unit.cls is not None:
        ms = unit.module.methods_of(unit.cls, node.attr)
        fn = ms[0] if ms else None
    body = None
    if fn is not None:
        unbound = isinstance(node.value, ast.Name) and unit.class_named(node.value.id) is not None \
            and not _decorated(fn, "staticmethod") and not _decorated(fn, "classmethod")
        body = _body_kind(_reader(unit, fn), list(ast.walk(fn)), loops, 0,
                          {**_instance_given(unit, node.value, given), **_ctor_given(fn, ctor, ctor_unit or unit, given, unbound=unbound)})
        if body[0] != "bounded":
            return body
    if node.attr in FOREVER:
        return "loop", node.attr
    if node.attr in BLOCKING:
        if call is not None:
            untimed = _untimed_call(node.attr, list(call.args), [(k.arg, k.value) for k in call.keywords])
        else:
            untimed = ctor is None or _handed_untimed(ctor, node.attr, ctor_unit or unit)
        if untimed:
            return "waits", "the target is an untimed .%s" % node.attr
    if node.attr in READS:
        return "waits", "the target is a read"
    if body is not None:
        return body
    if node.attr in loops and node.attr not in BUILTIN_METHODS:
        return "loop", "a product function with a while loop"
    prod = _product_kind(unit, node, line, 0, ctor=ctor, ctor_unit=ctor_unit, given=given)
    if prod is not None:
        return prod
    lib = _library_kind(unit, node, line, ctor)
    if lib is not None:
        return lib
    return KIND_UNREAD, _unread_reason(unit, node, line)


def _own_method(unit, call):
    """The method `self.x()` / `cls.x()` names in a unit that reads a method of a class: the class's own x (or a base's
    in this module); None for a call that is not such, or in a unit without a class."""
    f = call.func
    if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id in ("self", "cls") and unit.cls is not None:
        return unit.method_of(unit.cls, f.attr)
    return None


def _clock_break(loop):
    """The while's body leaves it on a clock reading (`if time.monotonic() > deadline: break`): bounded, as a while whose
    test reads the clock is."""
    for sub in ast.walk(loop):
        if isinstance(sub, ast.If) and CLOCK.search(ast.unparse(sub.test)) \
                and any(isinstance(n, (ast.Break, ast.Return)) for b in sub.body for n in ast.walk(b)):
            return True
    return False


def _is_module_alias(unit, node):
    """The name is a module object: an import, or a module-level name bound to a call or an attribute (km = load_source(...))."""
    if not isinstance(node, ast.Name):
        return False
    g = unit.module.globals.get(node.id)
    return node.id in unit.module.imports or isinstance(g, (ast.Call, ast.Attribute))


def _module_call(unit, call):
    """The call reaches a function outside the test module: a bare name the module imported (not one it defines), or an
    attribute of a module alias (a name imported or bound at module level to a call or an attribute). The road of the
    by-name loops rule: a name in product_loops reached this way is a loop (restricted, whatever the alias is)."""
    f = call.func
    if isinstance(f, ast.Name):
        return f.id not in unit.local_defs and f.id not in unit.module.functions and f.id in unit.module.imports
    if isinstance(f, ast.Attribute):
        return _is_module_alias(unit, f.value)
    return False


def _product_call(unit, call):
    """The call reaches a PRODUCT function the walk can read: a bare name imported from kernel/, postal/ or cli/ (not one
    the module defines), or an attribute of a product module (km = load_source(...), sb, jd, pm, a local km =
    kernel_module(); not time, not a third-party module)."""
    f = call.func
    if isinstance(f, ast.Name):
        return f.id not in unit.local_defs and f.id not in unit.module.functions and f.id in unit.module.imports \
            and unit.module.is_product_alias(f.id)
    if isinstance(f, ast.Attribute):
        return _product_module(unit, f.value, call.lineno)
    return False


def _class_of(unit, node, line, depth=0):
    """The ClassDef of the test module (or of the function) that `node` is an instance of, or is: the class itself by name
    (`_Child._pump`: a method reached through the class), a construction of it (`_Fake().run`), a name or an attribute
    bound to such a construction (`f = _Fake()`; `self.fake = _Fake()` anywhere in the class or a base), or the `as`
    name of a `with` over one whose __enter__ returns self. None for anything else (a product object, a parameter)."""
    if depth > 8 or node is None:
        return None
    if isinstance(node, tuple):
        if node[0] == "with":                                   # with _Fake() as f: f is the fake when __enter__ returns self
            c = _class_of(unit, node[1], line, depth + 1)
            enter = unit.method_of(c, "__enter__") if c is not None else None
            if enter is not None and any(isinstance(v, ast.Name) and v.id == "self" for v in _returns(enter)):
                return c
        if node[0] == "for":                                    # for f in fakes: f is an element of what fakes holds
            return _class_of(unit, node[1], line, depth + 1)
        return None
    if isinstance(node, ast.Call):
        return unit.class_named(node.func.id) if isinstance(node.func, ast.Name) else None
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):        # [_Fake(), _Fake()]: the first element the walk reads
        for e in node.elts:
            c = _class_of(unit, e, line, depth + 1)
            if c is not None:
                return c
        return None
    if isinstance(node, (ast.ListComp, ast.GeneratorExp, ast.SetComp)):
        return _class_of(unit, node.elt, line, depth + 1)
    if isinstance(node, ast.Subscript):                         # fakes[0].run, self.fakes[0].run: an element of the holder
        return _class_of(unit, node.value, line, depth + 1)
    if isinstance(node, ast.Name):
        c = unit.class_named(node.id)
        if c is not None:
            return c
        b = unit.binding_at(node.id, line)
        if b is not None:
            return _class_of(unit, b[1], b[0], depth + 1)
        g = unit.module.globals.get(node.id)
        return _class_of(unit, g, g.lineno, depth + 1) if g is not None else None
    if isinstance(node, ast.Attribute):
        b = unit.binding_at(ast.unparse(node), line)
        if b is not None:
            return _class_of(unit, b[1], b[0], depth + 1)
        if isinstance(node.value, ast.Name) and node.value.id in ("self", "cls"):
            for v in unit.class_bindings(node.attr):
                c = _class_of(unit, v, v.lineno, depth + 1)
                if c is not None:
                    return c
    return None


def _method_call(unit, func, args, line):
    """(the method's FunctionDef, the text that stands for `self` in its body) for an attribute `func` that is a method of
    a class of the test module reached through an instance (`f.run`: self is f; `self.fake.run`: self is self.fake) or
    through the class (`_Child._pump` with `child` handed as the first argument: self is child); (None, None) otherwise,
    and for the unit's own class's `self.x` (that is _target_fn's road, and `self` there is the test's)."""
    recv = func.value
    if isinstance(recv, ast.Name) and recv.id in ("self", "cls"):
        return None, None
    cls = _class_of(unit, recv, line)
    if cls is None:
        return None, None
    fn = unit.method_of(cls, func.attr)
    if fn is None:
        return None, None
    if _decorated(fn, "staticmethod"):                                             # no instance at all
        return fn, None
    if isinstance(recv, ast.Name) and unit.class_named(recv.id) is cls:          # the class itself
        if _decorated(fn, "classmethod"):                                          # cls is the class: cls.go is _Cls.go
            return fn, recv.id
        inst = args[0] if args else None                                           # an unbound method: its instance is the
        return fn, (ast.unparse(inst) if inst is not None and _is_chain(inst) else None)   # first of args=, when a name
    if isinstance(recv, ast.Call):                                                 # _Fake().run: nothing in the test names it
        return fn, None
    return fn, ast.unparse(recv)


def _decorated(fn, name):
    return any(isinstance(d, ast.Name) and d.id == name for d in fn.decorator_list)


def _is_chain(node):
    """A Name, or an Attribute / Subscript chain down to one (`f`, `self.fake`, `fakes[0]`, `h[k].x`): a name the walk
    can write another name against."""
    while isinstance(node, (ast.Attribute, ast.Subscript)):
        node = node.value
    return isinstance(node, ast.Name)


def _parse_chain(text):
    """The expression `text` parses to, when it is a name chain (_is_chain); None for anything else and for text no
    parser accepts (`*kids.go`, `0.go`), so a name the walk synthesises can never raise out of the census."""
    if not text:
        return None
    try:
        node = ast.parse(text, mode="eval").body
    except (SyntaxError, ValueError):
        return None
    return node if _is_chain(node) else None


def _handed(start):
    """The elements of the construction's args= tuple or list, in order; [] when none or not a literal."""
    if start.ctor is None:
        return []
    for kw in start.ctor.keywords:
        if kw.arg == "args" and isinstance(kw.value, (ast.Tuple, ast.List)):
            return list(kw.value.elts)
    return []


def _unwritable_instance(start):
    """The first of args= when the target is a method reached through the class (not a staticmethod or a classmethod) and
    that first argument is not a name chain nor a construction: `*kids`, `0`, a lambda. The thread runs the method on
    something the walk cannot name, so it cannot read what the thread waits on: the row is UNREADABLE. None otherwise."""
    expr = start.target_expr
    if not isinstance(expr, ast.Attribute) or start.ctor is None or not isinstance(expr.value, ast.Name):
        return None
    unit = start.ctor_unit
    cls = unit.class_named(expr.value.id)
    if cls is None:
        return None
    fn = unit.method_of(cls, expr.attr)
    if fn is None or _decorated(fn, "staticmethod") or _decorated(fn, "classmethod"):
        return None
    handed = _handed(start)
    if not handed:
        return None
    inst = handed[0]
    return None if _is_chain(inst) or isinstance(inst, ast.Call) else inst


def _target_method(start):
    """_method_call for the start's target: (method, owner text) when the target is a method of a class of the test module
    reached through an instance or the class, the instance for an unbound method being the first of args=."""
    expr = start.target_expr
    if not isinstance(expr, ast.Attribute) or start.ctor is None:
        return None, None
    return _method_call(start.ctor_unit, expr, _handed(start), start.ctor.lineno)


def _method_calls_in(unit, nodes, line):
    """(method, owner text) for every call among `nodes` of a method of a class of the test module on an instance or the
    class (`f.run()`, `self.fake.step()`, `_Fake().run()`, `_Child._pump(child)`): what a lambda target reaches."""
    out = []
    for sub in nodes:
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
            fn, owner = _method_call(unit, sub.func, sub.args, getattr(sub, "lineno", line))
            if fn is not None:
                out.append((fn, owner))
    return out


def _own(text, owner):
    """A name read in a fake's method body as the test would write it: `self.go` in _Fake.run is `f.go` when the thread
    runs on f, `self.fake.go` when it runs on self.fake, `cls.go` in a classmethod is `_Cls.go`; None when nothing in the
    test names the fake (`_Fake().run`) or the owner is not a name chain the walk can write (`*kids`). A name that is
    not the fake's `self` or `cls` is returned as it is."""
    head, _sep, rest = text.partition(".")
    if head in ("self", "cls"):
        if owner is None or _parse_chain(owner) is None:
            return None
        return owner + ("." + rest if rest else "")
    return text


def _target_fn(start):
    """The function body behind the target, when it is in the test module: a local def, a module function, a lambda, a
    method of the class the construction sits in, a method of a class of the module reached through an instance or the
    class (`f.run`, `self.fake.run`, `_Fake().run`, `_Child._pump`), or a Thread subclass's run()."""
    unit, expr = start.ctor_unit, start.target_expr
    if isinstance(expr, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return expr
    if isinstance(expr, ast.Lambda):
        return expr
    if isinstance(expr, ast.Name):
        fn = unit.local_defs.get(expr.id) or (unit.parent.local_defs.get(expr.id) if unit.parent is not None else None) \
            or unit.module.functions.get(expr.id)
        if fn is not None:
            return fn
        b = unit.binding_at(expr.id, start.ctor.lineno)
        if b is not None and isinstance(b[1], ast.Lambda):
            return b[1]
    if isinstance(expr, ast.Attribute):
        fn, _owner = _target_method(start)
        if fn is not None:
            return fn
        if isinstance(expr.value, ast.Name) and expr.value.id in ("self", "cls") and unit.cls is not None:
            ms = unit.module.methods_of(unit.cls, expr.attr)
            if ms:
                return ms[0]
    if isinstance(expr, ast.Call):                      # wrap(i, fn): a helper of the test returning a def or a lambda
        built = _call_target(unit, expr, start.ctor.lineno)
        if built is not None:
            return built[0]
    return None


def _call_target(unit, call, line):
    """(the def or lambda, the unit that reads it) that a helper call builds as a target (`wrap(i, fn)` returning its
    nested `go`; a helper returning a lambda): the helper's returns, read in the helper's own unit; None otherwise."""
    callee = unit.callee_of(call, line)
    if callee is None:
        return None
    fn, u = callee
    for v in (_returns(fn) if not isinstance(fn, ast.Lambda) else [fn.body]):
        if isinstance(v, ast.Lambda):
            return v, u
        if isinstance(v, ast.Name):
            inner = u.local_defs.get(v.id) or (u.parent.local_defs.get(v.id) if u.parent is not None else None) \
                or u.module.functions.get(v.id)
            if inner is not None:
                return inner, u
    return None


def _reader(unit, fn):
    """The unit that reads a function's body: for a method, its class's own unit (so `self.x()` in it is the class's x and
    not the test's; a class defined in the body reads through the body's unit as its parent); `unit` itself otherwise."""
    if fn is None:
        return unit
    for scope in (unit, unit.parent):
        if scope is not None:
            for c in scope.local_classes.values():
                if any(f is fn for f in c.body):
                    return unit.module.unit_for(fn, c, parent=scope)
    for c in unit.module.classes.values():
        if any(f is fn for f in c.body):
            return unit.module.unit_for(fn, c)
    return unit


def _body_waits_on(unit, body, owner, lambda_depth=True):
    """The receivers of the untimed waits, the reads (recv, accept, readline, read: the socket or file the thread is
    parked on) and the is_set polls in a function body (`go` for go.wait(); `f.go` for a fake's self.go.wait() when the
    thread runs on f; `peer` for peer.recv()), and, for a lambda or a body that calls a fake's method, those of the
    methods it calls, one level down."""
    out = set()
    for sub in ast.walk(body):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr in BLOCKING + READS + ("is_set",):
            nm = _own(ast.unparse(sub.func.value), owner)      # a read's receiver too: a drain parked in peer.recv() is woken
            if nm:                                               # by peer.shutdown(), what it waits on (round 2, 2026-09-22)
                out.add(nm)
    if lambda_depth:
        for fn, o in _method_calls_in(unit, list(ast.walk(body)), body.lineno):
            out |= _body_waits_on(unit, fn, o, lambda_depth=False)
    return out


def _kind(start):
    """(kind, reason) for the thread: _target_kind's reading of the target, then the Timer rule (_timer_rule): a Timer
    sleeps its interval before its function runs, so a bounded function makes a bounded thread only for a literal
    interval at or under BOUND_S."""
    kind, why = _target_kind(start)
    return _timer_rule(start, kind, why)


def _timer_rule(start, kind, why):
    """A Timer(interval, function) holds its thread for `interval` before the function runs (or until cancelled): bounded
    ONLY when the interval is a literal at or under BOUND_S (romp-manager's ruling, 2026-09-22: a Timer(3600, ev.set) sits
    for an hour whatever ev.set does); a loop or a wait in the function stays what it is; otherwise UNREADABLE (a cancel
    or an untimed join before the first assertion is still its stop)."""
    ctor = start.ctor
    if ctor is None or kind != "bounded" or not start.ctor_unit.is_timer_ctor(ctor):
        return kind, why
    interval = next((kw.value for kw in ctor.keywords if kw.arg == "interval"), ctor.args[0] if ctor.args else None)
    n = _number_literal(interval)
    if n is not None and n <= BOUND_S:
        return kind, why
    shown = _text(interval, start.ctor_unit.module) if interval is not None else "?"
    return KIND_UNREAD, "a Timer whose interval `%s` is not a literal at or under %g s: it holds its thread until it fires, whatever its function does" % (shown, BOUND_S)


def _target_kind(start):
    """(kind, reason) for the thread: loop, waits, bounded or UNREADABLE. THE RULE: every case the walk cannot read falls
    to the restricted side. `bounded` comes ONLY from a body the walk read (_body_kind: a function of the test module, a
    fake's method, a helper's returned def, a Thread subclass's run(), a product function found in the product sources
    and read in its own module) and found free of loops, untimed waits and calls of a parameter no hand supplies, or from
    a stdlib call STDLIB_RETURNS says returns whatever its arguments (or whose STDLIB_CONDITIONED check passes at the
    call), each with its reason; the name rules (FOREVER, BLOCKING, READS) classify the other way, to loop or waits,
    and apply when the body the walk read says bounded (a body it cannot see through: asyncio.run(self._main()),
    self.fut.result()); a target it cannot resolve (a parameter, a function of a module it does not read, a stdlib
    method with no rule, a method run on an instance it cannot name, a call or an expression it does not read) is
    UNREADABLE, never bounded. The HANDS in force: the caller's (start.given, when read at a caller) for a body that
    closes over the helper's parameters (a lambda, a def of the body), and the construction's args= / kwargs= for the
    parameters of the def, lambda or method it runs (_ctor_given)."""
    unit, expr, ctor = start.ctor_unit, start.target_expr, start.ctor
    loops, given = unit.module.loops, start.given
    if expr is None:
        if any(kw.arg is None for kw in ctor.keywords) or any(isinstance(a, ast.Starred) for a in ctor.args):
            return KIND_UNREAD, "the target is hidden in a * or ** argument of the construction"
        return "bounded", "no target: the default run() does nothing"
    if isinstance(expr, (ast.FunctionDef, ast.AsyncFunctionDef)):          # a Thread subclass: what its run() does
        return _body_kind(_reader(unit, expr), list(ast.walk(expr)), loops, 0)
    if isinstance(expr, ast.Lambda):
        return _body_kind(unit, list(ast.walk(expr)), loops, 0, {**given, **_ctor_given(expr, ctor, unit, given)})
    if isinstance(expr, ast.Attribute):
        bad = _unwritable_instance(start)
        if bad is not None:
            return KIND_UNREAD, "a method reached through the class on `%s`, an instance the walk cannot name" % _text(bad, unit.module)
        fn = _target_fn(start)                     # a method of a class of the module (f.run, self.fake.run, _Fake().run,
        body = None                                # _Child._pump, self.x): its body is what the thread does, whatever the method is called
        if fn is not None:
            body = _body_kind(_reader(unit, fn), list(ast.walk(fn)), loops, 0,
                              {**_instance_given(unit, expr.value, given), **_ctor_given(fn, ctor, unit, given, unbound=_unbound_target(start, fn))})
            if body[0] != "bounded":
                return body
        if expr.attr in FOREVER:
            return "loop", expr.attr
        if expr.attr in BLOCKING and _handed_untimed(ctor, expr.attr, unit):
            return "waits", "the target is an untimed .%s" % expr.attr
        if expr.attr in READS:
            return "waits", "the target is a read"
        if body is not None:
            return body
        if expr.attr in loops and expr.attr not in BUILTIN_METHODS:
            return "loop", "a product function with a while loop"
        prod = _product_kind(unit, expr, ctor.lineno, 0, ctor=ctor, ctor_unit=unit, given=given)
        if prod is not None:
            return prod
        lib = _library_kind(unit, expr, ctor.lineno, ctor)
        if lib is not None:
            return lib
        return KIND_UNREAD, _unread_reason(unit, expr, ctor.lineno)
    if isinstance(expr, ast.Name):
        return _name_kind(start, expr, ctor.lineno, 0)
    if isinstance(expr, ast.Call):
        built = _call_target(unit, expr, ctor.lineno)
        if built is not None:                       # wrap(i, fn): the def or lambda the helper returns, under the call's hands
            fn, u = built
            callee = unit.callee_of(expr, ctor.lineno)
            g = _call_given(callee[0], expr, unit, u, given) if callee is not None else {}
            return _body_kind(u, list(ast.walk(fn)), loops, 0, {**g, **_ctor_given(fn, ctor, unit, given)})
        return KIND_UNREAD, "a callable built by %s(), a call the walk does not read" % _text(expr.func, unit.module)
    return KIND_UNREAD, "a target expression the walk does not read (%s)" % _text(expr, unit.module)


def _name_kind(start, node, line, depth):
    return _expr_kind(start.ctor_unit, node, line, depth, start.ctor, start.ctor_unit, start.given)


def _expr_kind(unit, node, line, depth, ctor=None, ctor_unit=None, given=None):
    """The kind of a Name target, of an argument a caller hands a helper's parameter, or of a hand a body's parameter was
    given: a function of the body or the module or a lambda bound to the name is read (with the construction's args= /
    kwargs= as its own arguments when `ctor`, in `ctor_unit`, is the construction that runs it, and under the hands
    `given` of the scope it closes over); a for-target over a tuple of such (`for target in (a, b, c)`) is each of them,
    joined on the restricted side; an attribute is read as a target is (_attribute_kind); a product function imported by
    name is read in the product sources; a stdlib function is looked up in STDLIB_RETURNS; a parameter a hand supplies is
    that hand's argument; a parameter otherwise, a function of a module the walk does not read, or anything else is
    UNREADABLE."""
    loops = unit.module.loops
    if depth > 8:
        return KIND_UNREAD, "a name bound too deep to follow"
    if isinstance(node, ast.Lambda):
        return _body_kind(unit, list(ast.walk(node)), loops, 0, {**(given or {}), **_ctor_given(node, ctor, ctor_unit or unit, given)})
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return _join_kind_answers([_expr_kind(unit, e, line, depth + 1, ctor, ctor_unit, given) for e in node.elts])
    if isinstance(node, ast.Attribute):
        return _attribute_kind(unit, node, line, ctor, ctor_unit, given)
    if not isinstance(node, ast.Name):
        return KIND_UNREAD, "a target the walk does not read as a callable (%s)" % _text(node, unit.module)
    fn = unit.local_defs.get(node.id) or (unit.parent.local_defs.get(node.id) if unit.parent is not None else None)
    if fn is not None:                                  # a def of the body: a closure over the same hands
        return _body_kind(unit, list(ast.walk(fn)), loops, 0, {**(given or {}), **_ctor_given(fn, ctor, ctor_unit or unit, given)})
    fn = unit.module.functions.get(node.id)
    if fn is not None:                                  # a module function: read in its own unit
        return _body_kind(unit.module.unit_for(fn), list(ast.walk(fn)), loops, 0, _ctor_given(fn, ctor, ctor_unit or unit, given))
    b = unit.binding_at(node.id, line)
    if b is not None:
        v = b[1]
        if isinstance(v, tuple):
            if v[0] == "for":
                return _expr_kind(unit, v[1], b[0], depth + 1, ctor, ctor_unit, given)
            return KIND_UNREAD, "a name bound by a %s the walk does not read as a callable" % v[0]
        if isinstance(v, (ast.Lambda, ast.Name, ast.Tuple, ast.List, ast.Set)):
            return _expr_kind(unit, v, b[0], depth + 1, ctor, ctor_unit, given)
        return KIND_UNREAD, "a name bound to `%s`, which the walk does not read as a callable" % _text(v, unit.module)
    r = _given_kind(given, node.id, depth)
    if r is not None:                                   # a parameter a hand supplies: the hand's argument, read where it is written
        k, why, hand = r
        return k, "%s | %s" % (why, hand)
    if node.id in loops:
        return "loop", "a product function with a while loop"
    if node.id in unit.params or (unit.parent is not None and node.id in unit.parent.params):
        return KIND_UNREAD, "a parameter (%s): what the caller hands in is not read here" % node.id
    if node.id in unit.module.imports:
        if unit.module.is_product_alias(node.id):
            prod = _product_kind(unit, node, line, 0, ctor=ctor, ctor_unit=ctor_unit, given=given)
            if prod is not None:
                return prod
        if unit.module.is_stdlib_alias(node.id):
            return _stdlib_rule(unit, node.id, node.id, ctor, None)
        return KIND_UNREAD, "%s: imported from %s, a module the walk does not read" % (node.id, unit.module.import_names.get(node.id, "?"))
    return KIND_UNREAD, "%s: a name the walk cannot resolve" % node.id


def _join_kind_answers(answers):
    """One answer for several read bodies, on the restricted side: any loop is a loop, else any waits, else any
    unreadable, else bounded (every one read)."""
    for k in ("loop", "waits", KIND_UNREAD):
        for a in answers:
            if a[0] == k:
                return a
    if not answers:
        return KIND_UNREAD, "nothing to read"
    return "bounded", answers[0][1] if len(answers) == 1 else "each of %d read: no loop, no untimed wait" % len(answers)


def _product_kind(unit, expr, line, depth, ctor=None, ctor_unit=None, call=None, given=None):
    """(kind, reason) for a target or a callee that is a PRODUCT function, read in the product sources (_Product): an
    attribute of a product module alias (km._push_all: the module-level functions of that name), or a method of a
    product object (be._boot_reconcile, be built by sb.SdkBackend(...) or by a helper returning one: the method of that
    class in its file, else every product function of that name), each read in its own module's unit and joined on the
    restricted side. None when the receiver is not a product module or object; UNREADABLE when it is one but no product
    function of that name exists (an attribute that is not a function). `ctor` (in `ctor_unit`) is the construction that
    runs the function, `call` the call of it in a body the walk reads: either hands the function's parameters their
    arguments (_ctor_given, _call_given), read when the body calls one (the third arm)."""
    prod = unit.module.product
    if prod is None:
        return None
    if isinstance(expr, ast.Name):                                   # from kernel.x import f; Thread(target=f)
        heads = [(p, c, f) for p, c, f in prod.functions.get(expr.id, []) if c is None] or prod.functions.get(expr.id, [])
        what = expr.id
    else:
        recv, what = expr.value, _text(expr, unit.module)
        obj = "module" if isinstance(recv, ast.Name) and unit.module.is_product_alias(recv.id) else _product_object(unit, recv, line)
        if obj is None:
            return None
        if obj == "module":                                                  # km.x: the module-level functions of that name
            heads = [(p, c, f) for p, c, f in prod.functions.get(expr.attr, []) if c is None]
        else:                                                                # be.x: the method of be's class, else by name
            heads = prod.methods(obj, expr.attr, unit.module) if isinstance(obj, str) else []
            heads = heads or prod.functions.get(expr.attr, [])
    if not heads:
        return KIND_UNREAD, "%s: a product attribute no product function defines" % what
    answers = []
    for p, c, f in heads:
        m = prod.module(p, unit.module)
        pu = m.unit_for(f, c)
        g = {}
        if ctor is not None:
            g.update(_ctor_given(f, ctor, ctor_unit or unit, given))
        if call is not None:
            g.update(_call_given(f, call, unit, pu, given))
        answers.append(_body_kind(pu, list(ast.walk(f)), unit.module.loops, depth, g))
    k, why = _join_kind_answers(answers)
    if k == "loop":
        return k, "a product function with a while loop" if why == "a while loop" else "a product function: %s" % why
    if k == "bounded":
        if len(answers) == 1:
            return k, "a product function read in 1 definition: %s" % why
        return k, "a product function read in %d definitions: no loop, no untimed wait" % len(answers)
    return k, "a product function: %s" % why


def _object_of(unit, node, line, depth=0):
    """The construction (a Call the walk does not resolve further) behind an expression, following the roads resolve
    does: a name's binding, a for or with target, a container's first element, a subscript's holder, self.x across the
    class, a module global, a helper's return, a product module's global (km._LOOPS_STOP). None when there is none."""
    if depth > 8 or node is None:
        return None
    if isinstance(node, tuple):
        if node[0] in ("for", "with"):
            return _object_of(unit, node[1], line, depth + 1)
        if node[0] == "unpack" and isinstance(node[1], ast.Call):          # be, fake, _ = build(): the tuple's element
            callee = unit.callee_of(node[1], line)
            if callee is not None:
                fn, u = callee
                for v in (_returns(fn) if not isinstance(fn, ast.Lambda) else [fn.body]):
                    if isinstance(v, (ast.Tuple, ast.List)) and len(v.elts) > node[2]:
                        r = _object_of(u, v.elts[node[2]], v.lineno, depth + 1)
                        if r is not None:
                            return r
        return None
    if isinstance(node, ast.Call):
        callee = unit.callee_of(node, line)
        if callee is None:
            return node
        fn, u = callee
        for v in (_returns(fn) if not isinstance(fn, ast.Lambda) else [fn.body]):
            r = _object_of(u, v, v.lineno, depth + 1)
            if r is not None:
                return r
        return None
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        for e in node.elts:
            r = _object_of(unit, e, line, depth + 1)
            if r is not None:
                return r
        return None
    if isinstance(node, (ast.ListComp, ast.GeneratorExp, ast.SetComp)):
        return _object_of(unit, node.elt, line, depth + 1)
    if isinstance(node, ast.Subscript):
        return _object_of(unit, node.value, line, depth + 1)
    if isinstance(node, ast.Name):
        b = unit.binding_at(node.id, line)
        if b is not None:
            r = _object_of(unit, b[1], b[0], depth + 1)
            if r is not None:
                return r
        g = unit.module.globals.get(node.id)
        if g is not None:
            r = _object_of(unit, g, g.lineno, depth + 1)
            if r is not None:
                return r
        for v in unit.appends.get(node.id, []) + unit.module.appended(node.id):   # _KM = []; _KM.append(load_source(...))
            r = _object_of(unit, v, v.lineno, depth + 1)
            if r is not None:
                return r
        return None
    if isinstance(node, ast.Attribute):
        b = unit.binding_at(ast.unparse(node), line)
        if b is not None:
            r = _object_of(unit, b[1], b[0], depth + 1)
            if r is not None:
                return r
        if isinstance(node.value, ast.Name) and node.value.id in ("self", "cls"):
            for v in unit.class_bindings(node.attr):
                r = _object_of(unit, v, v.lineno, depth + 1)
                if r is not None:
                    return r
            return None
        if unit.module.product is not None and _product_module(unit, node.value, line, depth + 1):
            g = unit.module.product.global_value(node.attr)              # km._LOOPS_STOP: the kernel's threading.Event()
            return g if isinstance(g, ast.Call) else None
        return None
    return None


def _product_module(unit, node, line, depth=0):
    """The expression is a product module: a module-level product alias (km), or a name whose value resolves to
    load_source(...) (a local `km = kernel_module()`; `self.km` so bound in the class)."""
    if isinstance(node, ast.Name) and unit.module.is_product_alias(node.id):
        return True
    call = _object_of(unit, node, line, depth)
    return call is not None and _callee_name(call) == "load_source"


def _product_object(unit, node, line):
    """The product class an expression is an instance of, by name (`be` bound to sb.SdkBackend(...), to a helper
    returning one, or to self.be so bound in the class); "module" when the expression is itself a product module
    (a local km = kernel_module() whose return is load_source(...)); True for an object built through a product module
    whose class the sources do not name (km.make_thing()); None when it is not a product object the walk can see."""
    call = _object_of(unit, node, line)
    if call is None or unit.module.product is None:
        return None
    if _callee_name(call) == "load_source":
        return "module"
    f = call.func
    if isinstance(f, ast.Attribute) and _product_module(unit, f.value, line):
        return f.attr if f.attr in unit.module.product.classes else True
    if isinstance(f, ast.Name):
        dotted = unit.module.import_names.get(f.id, "")
        if dotted.split(".")[0] in PRODUCT_DIRS and f.id in unit.module.product.classes:
            return f.id
    return None


_STDLIB_CTORS = ("Event", "Queue", "LifoQueue", "PriorityQueue", "SimpleQueue", "Lock", "RLock", "Condition", "Semaphore",
                 "BoundedSemaphore", "Barrier", "Timer")


def _library_ctor(call, unit=None):
    """The construction is of a stdlib object: through a stdlib module (threading.Event(), queue.Queue(), socket.socket(),
    socketserver.TCPServer()), or a bare class name imported from one (Event(); `from http.server import HTTPServer`
    when `unit` is given to read the import)."""
    f = call.func
    head = f
    while isinstance(head, ast.Attribute):
        head = head.value
    if isinstance(f, ast.Attribute) and isinstance(head, ast.Name):
        return head.id in getattr(sys, "stdlib_module_names", ()) or (unit is not None and unit.module.is_stdlib_alias(head.id))
    if isinstance(f, ast.Name):
        return f.id in _STDLIB_CTORS or (unit is not None and unit.module.is_stdlib_alias(f.id))
    return False


def _library_kind(unit, expr, line, ctor=None):
    """(kind, reason) for a target that is a function of a stdlib module (time.sleep) or a method of a stdlib object
    (km._LOOPS_STOP.set, gate.clear, srv.server_close): bounded when STDLIB_RETURNS says the call returns whatever its
    arguments and on any receiver, or when a STDLIB_CONDITIONED check passes at the call (`ctor` is the construction
    whose args= a time.sleep is read from); UNREADABLE for any other; None when the receiver is neither."""
    recv = expr.value
    if isinstance(recv, ast.Name) and unit.module.is_stdlib_alias(recv.id):
        return _stdlib_rule(unit, expr.attr, _text(expr, unit.module), ctor, None)
    call = _object_of(unit, recv, line)
    if call is not None and (_library_ctor(call, unit) or _library_made(unit, call) is not None):
        return _stdlib_rule(unit, expr.attr, _text(expr, unit.module), ctor, call, recv)
    return None


ASYNCIO_MAKERS = ("call_soon", "call_later", "call_at", "call_soon_threadsafe", "create_task", "create_future", "ensure_future")


def _library_made(unit, call):
    """The stdlib module whose object's METHOD built the receiver, for the makers the walk reads as stdlib constructions:
    an asyncio loop's handle, task or future (loop.call_later(...), loop.create_task(...): ASYNCIO_MAKERS on a loop built
    by asyncio) and a pool's future (ex.submit(...) on a concurrent.futures executor); None for any other method's result
    (a Manager's proxy, say: an object the walk does not read, the restricted side)."""
    f = call.func
    if not isinstance(f, ast.Attribute) or f.attr not in ASYNCIO_MAKERS + ("submit",):
        return None
    obj = _object_of(unit, f.value, getattr(call, "lineno", 0))
    if obj is None or not _library_ctor(obj, unit):
        return None
    mod = _ctor_module(unit, obj)
    return mod if mod in ("asyncio", "concurrent") else None


def _stdlib_rule(unit, name, shown, ctor, call, recv=None):
    """The verdict for a stdlib function or method used as a target: STDLIB_RETURNS by name (bounded whatever the
    arguments, on any receiver), else STDLIB_CONDITIONED's check at the call (`ctor` the construction, `call` the
    receiver's construction or None for a module function, `recv` the receiver as written, for a checker that reads what
    the unit did to it), else UNREADABLE."""
    r = STDLIB_RETURNS.get(name)
    if r:
        return "bounded", r
    cond = STDLIB_CONDITIONED.get(name)
    if cond is not None:
        return cond(unit, ctor, call, recv)
    if call is not None:
        return KIND_UNREAD, "%s: a method of a %s() the walk has no rule for" % (shown, _callee_name(call))
    return KIND_UNREAD, "%s: a stdlib function the walk has no rule for" % shown


def _sleep_rule(unit, ctor, call, recv=None):
    """time.sleep as a target is bounded ONLY when args= carries a literal number at or under BOUND_S, read at the call
    (romp-manager's ruling, 2026-09-22): a sleep of 3600 s, or of a name, outlives the test; UNREADABLE otherwise."""
    handed = _handed_args(ctor, unit) if ctor is not None else None
    secs = handed[0][0] if handed and handed[0] else None
    n = _number_literal(secs)
    if n is not None and n <= BOUND_S:
        shown = _text(secs, unit.module)
        return "bounded", "time.sleep(%s) returns after %s s, a literal at or under the %g s bound read at the call" % (shown, shown, BOUND_S)
    shown = "`%s` in args=" % _text(secs, unit.module) if secs is not None else ("no args=" if handed is not None else "arguments the walk cannot read")
    return KIND_UNREAD, "time.sleep with %s: not a literal at or under %g s (a thread asleep that long outlives the test)" % (shown, BOUND_S)


def _server_close_rule(unit, ctor, call, recv=None):
    """server_close as a target is bounded ONLY on a server with no handler threads to join (DAEMON_HANDLER_SERVERS, read
    from the receiver's construction): socketserver.ThreadingMixIn.server_close joins live handlers under its defaults."""
    name = _callee_name(call) if call is not None else None
    if name in DAEMON_HANDLER_SERVERS:
        return "bounded", ("server_close of a %s() returns: no handler threads to join (a plain socketserver handles in the accept thread; "
                           "ThreadingHTTPServer's handlers are daemon threads, which ThreadingMixIn.server_close does not join), so it "
                           "closes the listening socket and returns" % name)
    return KIND_UNREAD, ("server_close of a %s(): socketserver.ThreadingMixIn.server_close joins every live handler under its defaults "
                         "(block_on_close=True, daemon_threads=False), unbounded while a handler is parked in a read (the runtime probe "
                         "of 2026-09-22)" % (name or "server the walk cannot name"))


def _ctor_module(unit, call):
    """The stdlib module a receiver's construction names, resolved through the unit's imports: `threading` for
    threading.Event(), `multiprocessing` for mp.Event() under `import multiprocessing as mp` and for a bare Event() from
    `from multiprocessing import Event`, `queue` for queue.Queue(); None when the head is not a name (a call's result:
    multiprocessing.get_context().Event())."""
    head = call.func
    while isinstance(head, ast.Attribute):
        head = head.value
    if not isinstance(head, ast.Name):
        return None
    return unit.module.import_names.get(head.id, head.id).split(".")[0]


def _ctor_class(unit, call):
    """The class a receiver's construction names, through the unit's imports for a bare name (`Q()` under `from queue import
    Queue as Q` is a Queue; `MpEvent()` under `from multiprocessing import Event as MpEvent` an Event): the attribute of a
    dotted construction (threading.Event()), else the imported name's last part, else the name as written."""
    f = call.func
    if isinstance(f, ast.Attribute):
        return f.attr
    if isinstance(f, ast.Name):
        return unit.module.import_names.get(f.id, f.id).split(".")[-1]
    return None


def _event_method_rule(name):
    """The checker for an Event's set / clear / is_set: bounded on a threading.Event() (the flag under a lock its own methods
    hold briefly; wait releases it while waiting; set's notify_all is a threading Condition's, no handshake) and on an
    asyncio.Event() (the flag and the waiters' futures, no lock); UNREADABLE on a multiprocessing.Event() (set runs
    Condition.notify_all's per-sleeper _woken_count.acquire() handshake, the argument that dropped notify; clear and is_set
    take the Condition's lock a set() stuck in that handshake holds) and on a receiver whose construction the walk cannot
    name."""
    def rule(unit, ctor, call, recv=None):
        mod = _ctor_module(unit, call) if call is not None else None
        ctor_name = _ctor_class(unit, call) if call is not None else None
        if ctor_name == "Event" and mod == "threading":
            return "bounded", ("%s of a threading.Event() returns: the flag under a lock its own methods hold briefly (wait releases it while "
                               "waiting), set's notify_all a threading Condition's with no handshake" % name)
        if ctor_name == "Event" and mod == "asyncio":
            return "bounded", "%s of an asyncio.Event() returns: the flag and the waiters' futures, no lock" % name
        if mod == "multiprocessing":
            return KIND_UNREAD, ("%s of a multiprocessing.%s(): set runs Condition.notify_all's per-sleeper _woken_count.acquire() handshake (the "
                                 "argument that dropped notify), and clear and is_set take the Condition's lock a set() stuck in it holds"
                                 % (name, ctor_name or "Event"))
        return KIND_UNREAD, "%s of a %s the walk has no rule for: an Event's %s is bounded only on a threading or asyncio Event()" % (
            name, ("%s.%s()" % (mod, ctor_name)) if mod and ctor_name else "receiver whose construction the walk cannot name", name)
    return rule


def _queue_method_rule(name):
    """The checker for a queue's put_nowait / get_nowait: bounded on queue's Queue, LifoQueue, PriorityQueue and SimpleQueue
    (a mutex every method holds briefly, a blocking put or get waiting on a Condition with it released; Full or Empty
    raised at once) and on asyncio's (no lock); on a multiprocessing.Queue() put_nowait is bounded (a non-blocking
    semaphore acquire, then the feeder thread's threading.Condition) and get_nowait UNREADABLE (get(False) reads the pipe
    untimed after its poll); on a multiprocessing.JoinableQueue() both are UNREADABLE (put takes its multiprocessing
    Condition, which task_done's notify_all holds through its per-sleeper handshake); UNREADABLE on a receiver whose
    construction the walk cannot name."""
    def rule(unit, ctor, call, recv=None):
        mod = _ctor_module(unit, call) if call is not None else None
        ctor_name = _ctor_class(unit, call) if call is not None else None
        if mod == "queue" and ctor_name in ("Queue", "LifoQueue", "PriorityQueue", "SimpleQueue"):
            return "bounded", ("%s of a queue.%s() returns: Full or Empty raised at once, else the item, under a mutex every method holds "
                               "briefly (a blocking put or get waits on a Condition with it released)" % (name, ctor_name))
        if mod == "asyncio" and ctor_name in ("Queue", "LifoQueue", "PriorityQueue"):
            return "bounded", "%s of an asyncio.%s() returns: QueueFull or QueueEmpty raised at once, else the item, no lock" % (name, ctor_name)
        if mod == "multiprocessing" and ctor_name == "Queue" and name == "put_nowait":
            return "bounded", ("put_nowait of a multiprocessing.Queue() returns: a non-blocking acquire of its semaphore (Full), then the feeder "
                               "thread's threading.Condition, held briefly")
        if mod == "multiprocessing":
            return KIND_UNREAD, ("%s of a multiprocessing.%s(): get(False) reads the pipe untimed after its poll; a JoinableQueue's put takes its "
                                 "multiprocessing Condition, which task_done's notify_all holds through its per-sleeper handshake"
                                 % (name, ctor_name or "Queue"))
        return KIND_UNREAD, "%s of a %s the walk has no rule for: bounded only on a queue or asyncio queue, and put_nowait on a multiprocessing.Queue()" % (
            name, ("%s.%s()" % (mod, ctor_name)) if mod and ctor_name else "receiver whose construction the walk cannot name")
    return rule


def _registers_callback(unit, recv):
    """The unit registers an add_done_callback on the receiver `recv`: in its function, in the function enclosing it or,
    for a self attribute, anywhere in the class or a base in the module. A callback registered elsewhere (in a helper
    that built the future, in another test) is not seen: the stated limit of _cancel_rule's bounded verdict."""
    key = ast.unparse(recv)
    scopes = [unit.fn] + ([unit.parent.fn] if unit.parent is not None else [])
    if isinstance(recv, ast.Attribute) and isinstance(recv.value, ast.Name) and recv.value.id in ("self", "cls") and unit.cls is not None:
        scopes += unit.module.bases_of(unit.cls)
    for scope in scopes:
        for sub in ast.walk(scope):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == "add_done_callback" \
                    and ast.unparse(sub.func.value) == key:
                return True
    return False


def _cancel_rule(unit, ctor, call, recv=None):
    """cancel as a target (round 2 of PR 891's review, 2026-09-22): bounded on a threading.Timer() (cancel sets the Timer's
    finished Event, whatever its function does; by name, through an alias or a subclass: is_timer_ctor), on asyncio's
    Future, Task, Handle and TimerHandle (asyncio.Future(), loop.create_future(), asyncio.ensure_future(...),
    loop.create_task(...), loop.call_soon / call_later / call_at / call_soon_threadsafe(...) on a loop built by asyncio:
    cancel schedules the done callbacks through loop.call_soon and returns, and a Handle marks itself cancelled; the
    runtime probe of 2026-09-22 had an asyncio Future's cancel with a blocking done-callback return at once), and on a
    concurrent.futures.Future() ONLY when the unit registers no add_done_callback on the receiver (_registers_callback),
    because concurrent.futures.Future.cancel runs the done callbacks SYNCHRONOUSLY (_invoke_callbacks) and a blocking one
    blocks cancel (the refuter's probe: `fut.add_done_callback(lambda f: gate.wait())` then `Thread(target=fut.cancel)`
    stays alive; re-run: alive after 0.5 s). UNREADABLE for such a Future with a callback registered, for a pool future
    (ex.submit(...): the pool and its other callers may register callbacks the walk does not see), for a sched.scheduler
    (its cancel takes the scheduler's lock, which a run() holds while an action runs) and for any receiver the walk cannot
    name."""
    if call is None:
        return KIND_UNREAD, ("cancel of a receiver whose construction the walk cannot name: bounded only on a threading.Timer(), an asyncio "
                             "future, task or handle, or a concurrent.futures.Future() with no add_done_callback on it in the unit")
    if unit.is_timer_ctor(call):
        return "bounded", "cancel of a threading.Timer() returns: it sets the Timer's finished Event, whatever the Timer's function does"
    mod, ctor_name, made = _ctor_module(unit, call), _ctor_class(unit, call), _library_made(unit, call)
    if (mod == "asyncio" and ctor_name in ("Future", "Task", "ensure_future", "create_task")) or made == "asyncio":
        return "bounded", ("cancel of an asyncio %s() returns: it schedules the done callbacks through loop.call_soon and returns (a Handle or "
                           "TimerHandle marks itself cancelled)" % (("%s.%s" % (mod, ctor_name)) if mod == "asyncio" else "loop.%s" % _callee_name(call)))
    if mod == "concurrent" and ctor_name == "Future":
        if recv is not None and _registers_callback(unit, recv):
            return KIND_UNREAD, ("cancel of a concurrent.futures.Future() with an add_done_callback registered on `%s`: Future.cancel runs the done "
                                 "callbacks synchronously, so a blocking callback blocks cancel (the probe of 2026-09-22)" % _text(recv, unit.module))
        return "bounded", ("cancel of a concurrent.futures.Future() with no add_done_callback on it in the unit returns: it takes the future's "
                           "Condition, held briefly by every method, notifies it, and has no done callbacks to run")
    if made == "concurrent":
        return KIND_UNREAD, "cancel of a pool future (%s()): the pool and its other callers may register done callbacks the walk does not see" % _callee_name(call)
    return KIND_UNREAD, "cancel of a %s the walk has no rule for: bounded only on a threading.Timer(), an asyncio future, task or handle, or a concurrent.futures.Future() with no add_done_callback on it in the unit" % (
        ("%s.%s()" % (mod, ctor_name)) if mod and ctor_name else "receiver whose construction the walk cannot name")


# The receivers whose release returns on its own, by the module their construction names and the class: threading's and
# _thread's locks, semaphores and conditions, multiprocessing's own (multiprocessing.synchronize's classes, reached as
# multiprocessing.Lock() and the like), asyncio's.
RELEASE_RECEIVERS = {"threading": ("Lock", "RLock", "Condition", "Semaphore", "BoundedSemaphore"),
                     "_thread": ("allocate_lock", "allocate", "LockType", "RLock"),
                     "multiprocessing": ("Lock", "RLock", "Condition", "Semaphore", "BoundedSemaphore"),
                     "asyncio": ("Lock", "Condition", "Semaphore", "BoundedSemaphore")}


def _release_rule(unit, ctor, call, recv=None):
    """release as a target (the refuter's finding on the ninth pass, 2026-09-22): bounded ONLY on a receiver whose construction
    the walk reads as a lock, semaphore or condition of threading or _thread (release frees the lock, raising when not held;
    a Semaphore takes its Condition briefly and notifies it, release(n) n times), of multiprocessing's own constructors
    (post the semaphore, no handshake) or of asyncio (wake a waiter's future, whose callbacks loop.call_soon schedules):
    RELEASE_RECEIVERS, the receiver's module read through the imports (_ctor_module) and its class (_ctor_class). The
    re-examinations of 2026-09-22 (round 1 of PR 891's review: which receiver classes carry the name and what the arguments
    do; round 2: a caller's callback run synchronously) stand for those receivers: no stdlib release among them runs a
    caller's callback synchronously (the way concurrent.futures.Future.cancel runs its done callbacks, the reason cancel left
    the table), and a runtime probe had threading.Semaphore.release and asyncio.Lock.release with a parked waiter return at
    once. UNREADABLE
    for any other stdlib object's release (a mmap.mmap(), whose release is the buffer's; a sqlite3.connect(), whatever it
    may do: the objects the table's entry would have excused by name, since _library_ctor answers True for a constructor
    of ANY stdlib module) and for a receiver whose construction the walk cannot name. A multiprocessing.managers proxy
    (Manager().Lock(), .RLock(), .Semaphore(), .BoundedSemaphore(), .Condition(): an AcquirerProxy) never reaches this
    checker: its construction is a method's result and not a stdlib constructor (_library_ctor, _library_made), so the walk
    reads it as an object it does not read, and rightly, since its release is a synchronous round trip to the manager
    process, blocked while that process is stopped or busy (the probe of 2026-09-22: a Manager().Lock() proxy's release on a
    thread was alive after 1 s with the manager process SIGSTOPped and returned after SIGCONT; after the manager's shutdown
    it raised BrokenPipeError); a plant holds it listed."""
    if call is None:
        return KIND_UNREAD, "release of a receiver whose construction the walk cannot name: bounded only on a lock, semaphore or condition of threading, multiprocessing or asyncio"
    mod, ctor_name = _ctor_module(unit, call), _ctor_class(unit, call)
    if mod in RELEASE_RECEIVERS and ctor_name in RELEASE_RECEIVERS[mod]:
        what = {"threading": "frees the lock (raising when not held), a Semaphore's takes its Condition briefly and notifies it",
                "_thread": "frees the lock, raising when not held",
                "multiprocessing": "posts the semaphore, no handshake",
                "asyncio": "wakes a waiter's future, whose callbacks loop.call_soon schedules"}[mod]
        return "bounded", "release of a %s.%s() returns: it %s" % (mod, ctor_name, what)
    return KIND_UNREAD, "release of a %s the walk has no rule for: bounded only on a lock, semaphore or condition of threading, multiprocessing or asyncio" % (
        ("%s.%s()" % (mod, ctor_name)) if mod and ctor_name else "receiver whose construction the walk cannot name")


# The stdlib names whose boundedness is CONDITIONED on the call: each checker reads the construction (`ctor`), the
# receiver's construction (`call`) or the receiver as written (`recv`) and answers bounded with its reason or unreadable.
# A name here is never in STDLIB_RETURNS (stdlib_table_problems holds the two apart).
STDLIB_CONDITIONED = {"sleep": _sleep_rule, "server_close": _server_close_rule, "cancel": _cancel_rule, "release": _release_rule,
                      "set": _event_method_rule("set"), "clear": _event_method_rule("clear"), "is_set": _event_method_rule("is_set"),
                      "put_nowait": _queue_method_rule("put_nowait"), "get_nowait": _queue_method_rule("get_nowait")}
CONDITIONED_HEADS = ("time.sleep(",) + tuple("%s of a" % n for n in STDLIB_CONDITIONED if n != "sleep")   # the bounded reasons' heads


def _unread_reason(unit, expr, line):
    recv = expr.value
    if isinstance(recv, ast.Name):
        if recv.id in unit.params or (unit.parent is not None and recv.id in unit.parent.params):
            return "a method of the parameter %s: what the caller hands in is not read here" % recv.id
        if recv.id in unit.module.imports:
            return "a function of %s, a module the walk does not read" % unit.module.import_names.get(recv.id, recv.id)
        if unit.binding_at(recv.id, line) is None and recv.id not in unit.module.globals:
            return "a method of %s, a name the walk cannot resolve" % recv.id
    return "a method of `%s`, an object the walk does not read" % _text(recv, unit.module)


def _release_names(start):
    """The names a waiting or polling thread would be released by: the receivers of the untimed waits and the is_set
    polls in its target, or the target's own receiver when the target is an Event.wait. A Thread subclass's run() waits
    on the fake's own attributes, which are not the test's: none."""
    expr = start.target_expr
    out = set()
    if expr is None or isinstance(expr, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return out
    method, owner = _target_method(start)
    if method is not None:                              # a fake's method: its self.go is the test's f.go (or nothing, inline)
        out = _body_waits_on(start.ctor_unit, method, owner, lambda_depth=False)
        if isinstance(expr, ast.Attribute) and ((not out and expr.attr in BLOCKING)   # w.wait whose body the walk sees no wait
                                                or (out and owner and all(n == owner or n.startswith(owner + ".") for n in out))):
            out.add(ast.unparse(expr.value))            # in, or whose waits are all the fake's own (self.fut.result()): the fake's
        return out                                      # own set / release method on w is what ends them
    if isinstance(expr, ast.Attribute) and expr.attr in BLOCKING:
        out.add(ast.unparse(expr.value))
        return out
    body = _target_fn(start)
    if body is not None:                                # the test's own function: its self IS the test's; a lambda's calls
        out |= _body_waits_on(start.ctor_unit, body, "self")   # of a fake's method are read one level down
    elif _outside_target(start):
        out |= _handed_names(start)                     # an Event handed to a product loop is what releases it
    return out


def _target_receivers(start):
    """The object the target runs on, whose shutdown / stop / cancel ends the thread: `srv` for srv.serve_forever, `loop` for
    a run_forever the target's body calls; never a module alias (km._producer runs on the module)."""
    out = set()
    expr = start.target_expr
    if isinstance(expr, ast.Attribute) and not _is_module_alias(start.ctor_unit, expr.value):
        out.add(ast.unparse(expr.value))
    body = _target_fn(start)
    if body is not None and not isinstance(expr, (ast.FunctionDef, ast.AsyncFunctionDef)):   # not a subclass's run(): its
        method, owner = _target_method(start)                                                 # self.* are the fake's own
        out |= _forever_receivers(start.ctor_unit, body, owner if method is not None else "self", method is None)
    return out


def _forever_receivers(unit, body, owner, lambda_depth):
    """The receivers of the serve_forever / run_forever calls in a body (`self._srv` in a fake's method is `f._srv` when
    the thread runs on f), and, one level down, those in the fakes' methods a lambda calls."""
    out = set()
    for sub in ast.walk(body):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr in FOREVER:
            nm = _own(ast.unparse(sub.func.value), owner)
            if nm:
                out.add(nm)
    if lambda_depth:
        for fn, o in _method_calls_in(unit, list(ast.walk(body)), body.lineno):
            out |= _forever_receivers(unit, fn, o, False)
    return out


def _outside_target(start):
    """The target is a function outside the test module (km._producer, self.km._producer, pm._heartbeat_loop, an imported
    name): the kernel loops' seam (_LOOPS_STOP) is what such a loop watches, and the walk cannot read its body."""
    expr = start.target_expr
    if isinstance(expr, ast.Attribute):
        return expr.attr not in FOREVER + BLOCKING + READS and _target_fn(start) is None
    if isinstance(expr, ast.Name):
        return _target_fn(start) is None
    return False


def _handed_names(start):
    """The names handed to the target through the construction's args= / kwargs= (`kwargs={"stop": stop}`): what the
    thread holds, so a cleanup that sets or releases one is about this thread."""
    out = set()
    if start.ctor is None:
        return out
    for kw in start.ctor.keywords:
        if kw.arg in ("args", "kwargs"):
            for sub in ast.walk(kw.value):
                if isinstance(sub, (ast.Name, ast.Attribute)) and not (isinstance(sub, ast.Name) and sub.id in ("self", "cls")):
                    out.add(ast.unparse(sub))
    return out


# ── the shape of the stop ───────────────────────────────────────────────────────────────────────────────

def _is_cleanup_call(unit, call):
    nm = _callee_name(call)
    if nm in CLEANUP_NAMES:
        return True
    return isinstance(call.func, ast.Name) and call.func.id in unit.params and "cleanup" in call.func.id.lower()


def _thread_words(start, extra=()):
    """The names a stop of this thread would mention: its receiver (and the attribute and holder behind `self.x`, `h[k]`),
    the list a for-target iterates, its release names, its target and the object the target runs on (a server, a loop;
    a module alias is not one, the loops' seam stands for a product loop), the attributes on self that hold it, and the
    names a caller binds a helper's result to."""
    words = set(extra)
    words.add(start.recv_text)
    node = start.recv
    while isinstance(node, ast.Subscript):
        node = node.value
        words.add(ast.unparse(node))
    if isinstance(node, ast.Attribute):
        words.add(node.attr)
    if isinstance(start.recv, ast.Name):
        b = start.unit.binding_at(start.recv.id, start.line)
        if b is not None and isinstance(b[1], tuple) and b[1][0] == "for":
            words.add(ast.unparse(b[1][1]))
            if isinstance(b[1][1], ast.Attribute):
                words.add(b[1][1].attr)
    owners = _owners(start)
    for nm in _release_names(start):
        words.add(nm)
        if _bare_word(start, nm, owners):                # a fake's f.go is f's alone: `go` names every fake's, so a
            words.add(nm.rsplit(".", 1)[1])              # release of g.go says nothing of f; a test's self.stop is `stop`
    expr = start.target_expr
    if isinstance(expr, (ast.Name, ast.Attribute)):
        words.add(ast.unparse(expr))
        if isinstance(expr, ast.Attribute):
            words.add(expr.attr)
    for r in _target_receivers(start) | _handed_names(start):
        words.add(r)
        if _bare_word(start, r, owners):                 # f._srv is f's alone: g._srv.shutdown says nothing of f
            words.add(r.rsplit(".", 1)[1])
    if start.kind == "loop" and _outside_target(start):
        words.add(STOP_SEAM)
    words.update(_stored_attrs(start))
    return {w for w in words if w and w not in ("self", "cls")}


def _owners(start):
    """The texts that stand for a fake's `self` in what the target reaches: the target method's owner (`f` for f.run,
    `self.fake` for self.fake.run, `_Cls` for a classmethod through the class) and the owners of the fakes' methods a
    lambda or a function of the test calls (`f` for lambda: f.wait())."""
    method, owner = _target_method(start)
    out = {owner} if owner else set()
    if method is None:
        body = _target_fn(start)
        if body is not None:
            out |= {o for _fn, o in _method_calls_in(start.ctor_unit, list(ast.walk(body)), body.lineno) if o}
    return out


def _bare_word(start, name, owners):
    """The last attribute of a dotted `name` may stand alone as a word of the thread (`stop` for self.stop, `_LOOPS_STOP`
    for km._LOOPS_STOP): not when a proper prefix of it is a fake's name (an owner, or a name bound to a class of the
    module), whose attributes are that fake's alone."""
    if "." not in name:
        return False
    parts = name.split(".")
    for i in range(1, len(parts)):
        prefix = ".".join(parts[:i])
        if prefix in owners:
            return False
        node = _parse_chain(prefix)
        if node is not None and not (isinstance(node, ast.Name) and node.id in ("self", "cls")) \
                and _class_of(start.ctor_unit, node, start.line) is not None:
            return False
    return True


def _imported_function(unit, func):
    """(FunctionDef, its _Module) for a callee that is a function of a HELPER MODULE under tests/ or of another test module,
    reached through the imports: the imported name (`join_started(...)` under `from tests.thread_ends import
    join_started`), the imported module (`thread_ends.join_started(...)`) or the dotted package spelling
    (`tests.thread_ends.join_started(...)`); None for any other callee (a local def, a module function, a lambda, a
    method: each read where it is defined)."""
    m = unit.module
    if isinstance(func, ast.Name):
        hf = m.helper_function(func.id) or m.tests_function(func.id)
        return (hf[1], hf[0]) if hf is not None else None
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        hm = m.helper_module(func.value.id) or m.tests_module_for(func.value.id)
        if hm is not None and func.attr in hm.functions:
            return hm.functions[func.attr], hm
        return None
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Attribute):
        hm = m.helper_module_dotted(func.value)
        if hm is not None and func.attr in hm.functions:
            return hm.functions[func.attr], hm
    return None


class _Bound(ast.NodeTransformer):
    """A helper's body with its parameters standing for the arguments a call handed it: a Name that is a parameter becomes a
    copy of the argument; an attribute over a parameter handed the constant None (`release.set()` for release=None)
    becomes None itself, so no verb is read as applied to it; a name the body binds itself (its for-target `t`) is
    renamed `_<helper>__<name>`, so the helper's own words are never taken for the test's (a test's thread `t` is not
    mentioned by the helper's `t.join`)."""
    def __init__(self, given, renamed):
        self.given, self.renamed = given, renamed

    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name) and node.value.id in self.given:
            arg = self.given[node.value.id]
            if isinstance(arg, ast.Constant) and arg.value is None:
                return ast.copy_location(ast.Constant(value=None), node)
        return self.generic_visit(node)

    def visit_Name(self, node):
        if node.id in self.renamed:
            return ast.copy_location(ast.Name(id=self.renamed[node.id], ctx=node.ctx), node)
        if isinstance(node.ctx, ast.Load) and node.id in self.given:
            return copy.deepcopy(self.given[node.id])
        return node


def _bound_body(fn, args, keywords):
    """An ast.Module holding a copy of `fn`'s body with each parameter replaced by the argument the call handed it: by
    position (up to a starred argument), by keyword, else by the parameter's default; a parameter no argument reaches, or
    one the body rebinds, keeps its name; the body's own bindings are renamed (_Bound)."""
    params = [a.arg for a in fn.args.posonlyargs + fn.args.args]
    given = {}
    for name, arg in zip(params, args):
        if isinstance(arg, ast.Starred):
            break
        given[name] = arg
    for kw in keywords:
        if kw.arg is not None:
            given[kw.arg] = kw.value
    defaults = fn.args.defaults
    for name, d in zip(params[len(params) - len(defaults):], defaults):
        given.setdefault(name, d)
    for a, d in zip(fn.args.kwonlyargs, fn.args.kw_defaults):
        if d is not None:
            given.setdefault(a.arg, d)
    body = ast.Module(body=copy.deepcopy(fn.body), type_ignores=[])
    stored = {n.id for n in ast.walk(body) if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del))}
    for name in stored:
        given.pop(name, None)
    renamed = {name: "_%s__%s" % (fn.name, name) for name in stored}
    return ast.fix_missing_locations(_Bound(given, renamed).visit(body))


def _helper_bodies(unit, call, nodes):
    """The bodies of the helper-module (or other-test-module) functions a cleanup runs, each bound to the arguments handed
    (THE HELPER ROAD): a registration whose callable is such a function runs it with the registration's remaining
    arguments (`self.addCleanup(join_started, release, ts, 5)`); a lambda, local function or method the cleanup names
    runs it where it calls it. One level down: the helper's own calls are not followed."""
    out = []
    if call.args:
        found = _imported_function(unit, call.args[0])
        if found is not None:
            out.append(_bound_body(found[0], list(call.args[1:]), call.keywords))
    for n in nodes:
        for sub in ast.walk(n):
            if isinstance(sub, ast.Call):
                found = _imported_function(unit, sub.func)
                if found is not None:
                    out.append(_bound_body(found[0], list(sub.args), sub.keywords))
    return out


def _cleanup_nodes(unit, call, helpers=True):
    """The nodes a cleanup registration runs, read for its stop: its arguments; the local function (of the unit or its
    parent), the module function or the lambda a name among them is bound to; the methods of the class a `self.x` /
    `cls.x` among them names; and, one level down (`helpers`), the bodies of the helper-module functions any of those
    run, bound to the arguments handed (_helper_bodies)."""
    nodes = []
    for a in list(call.args) + [k.value for k in call.keywords]:
        nodes.append(a)
        if isinstance(a, ast.Name):
            fn = unit.local_defs.get(a.id) or (unit.parent.local_defs.get(a.id) if unit.parent is not None else None) \
                or unit.module.functions.get(a.id)
            if fn is not None:
                nodes.append(fn)
            b = unit.binding_at(a.id, call.lineno)
            if b is not None and isinstance(b[1], ast.Lambda):
                nodes.append(b[1])
        if isinstance(a, ast.Attribute) and isinstance(a.value, ast.Name) and a.value.id in ("self", "cls") and unit.cls is not None:
            nodes += unit.module.methods_of(unit.cls, a.attr)
    return nodes + (_helper_bodies(unit, call, nodes) if helpers else [])


def _cleanup_stops(unit, call, start, extra=()):
    """The cleanup names a stop (an attribute or call of a stop verb, the loops' seam, or a name that says stop, in its own
    arguments, in the body of the local function, lambda or method of the class it names, or in the body of the
    helper-module function it runs, bound to the arguments handed: _cleanup_nodes) AND that text mentions the started
    thread (_thread_words): a cleanup that stops another thread excuses nothing about this one. With no start the stop
    shape alone is read."""
    nodes = _cleanup_nodes(unit, call)
    if not any(_stop_shaped(n) for n in nodes):
        return False
    if start is None:
        return True
    if _cleanup_needs_release(start) and not _cleanup_ends(call, nodes, start):
        return False
    text = "\n".join(ast.unparse(n) for n in nodes)
    return any(_word_in(w, text) for w in start.words(extra))


def _target_names(t):
    """The names a for or comprehension target binds: the Name itself, the elements of a tuple or list target (`for i, t in
    enumerate(ts)`), a starred element's name."""
    if isinstance(t, ast.Name):
        return {t.id}
    if isinstance(t, ast.Starred):
        return _target_names(t.value)
    if isinstance(t, (ast.Tuple, ast.List)):
        return {n for e in t.elts for n in _target_names(e)}
    return set()


def _list_joins(node):
    """The join calls in `node` whose receiver is an element of the collection the for or the comprehension enclosing them
    iterates: the target itself (`[t.join(5) for t in ts]`, `for t in (a, b): t.join(5)`, `list(t.join(1) for t in ts)`), an
    element of a tuple target (`for i, t in enumerate(ts): t.join(5)`), or a subscript, by a target, of a name the iterable
    is built over (`for i in range(len(ts)): ts[i].join(5)`, `for i, _t in enumerate(ts): ts[i].join()`): a join of every
    element of a collection, THE LIST-JOIN SHAPE, guarded on ident or not (a Name target alone until the ninth pass,
    2026-09-22, the refuter's nit). Subscript joins written out one by one (`callers[0].join(2), callers[1].join(2), ...`)
    are no loop and not this shape."""
    out = []
    for sub in ast.walk(node):
        if isinstance(sub, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            gens, scope = [(g.target, g.iter) for g in sub.generators], [sub.elt]
        elif isinstance(sub, ast.For):
            gens, scope = [(sub.target, sub.iter)], sub.body
        else:
            continue
        targets, iterated = set(), set()
        for t, it in gens:
            targets |= _target_names(t)
            iterated |= {n.id for n in ast.walk(it) if isinstance(n, ast.Name)}
        for s in scope:
            for c in ast.walk(s):
                if not (isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == "join"):
                    continue
                r = c.func.value
                if isinstance(r, ast.Name) and r.id in targets:
                    out.append(c)
                elif isinstance(r, ast.Subscript) and isinstance(r.value, ast.Name) and r.value.id in iterated \
                        and any(isinstance(n, ast.Name) and n.id in targets for n in ast.walk(r.slice)):
                    out.append(c)
    return out


def list_join_cleanups(paths, helpers=None, modules=None):
    """Every cleanup registration in the modules under `paths` that joins a LIST of threads inline (_list_joins over the
    registration's own arguments and the bodies of the lambda, local function, module function or method it names, the
    helper-module bodies excluded): [(file, line, unit qualname, the join's text)]. THE PROPERTY THE TREE HOLDS (round 2
    of PR 891's review, 2026-09-22): this is EMPTY, because every such cleanup goes through tests/thread_ends.py's
    join_started, the guard on a thread never started written once (a cleanup registered before a start loop runs on
    the exit path where the body failed between two starts, and Thread.join raises on one never started). A helper module
    is not in `paths` (module_paths lists tests/test_*.py), so the helper's own for-join is not a finding. REGISTRATIONS
    only (CLEANUP_NAMES and a registrar parameter whose name says cleanup): a tearDown or tearDownClass that joins a list
    inline is not read here, and two on the tree do, tests/test_heartbeat_thread.py's and tests/test_ws_liveness.py's
    tearDown, named in the module docstring as outside the pin. `modules` maps a
    path to its _Module already built (the tree derivation hands census's own, so the tree's units are built once per
    process); a path not in it is built here. The finding does not depend on the loops or the product a module was built
    with: a cleanup's nodes are read from the module alone."""
    helpers = helper_modules() if helpers is None else helpers
    out, cache, seen = [], {}, set()
    for p in paths:
        m = (modules or {}).get(p)
        if m is None:
            m = _Module(p, set(), helpers=helpers, helper_cache=cache)
        for u in m.units():
            for s, _b, _i, _st in u.rows:
                for sub in u.exprs[id(s)]:
                    if isinstance(sub, ast.Call) and _is_cleanup_call(u, sub):
                        for n in _cleanup_nodes(u, sub, helpers=False):
                            for j in _list_joins(n):
                                key = (p, j.lineno, j.col_offset)
                                if key not in seen:
                                    seen.add(key)
                                    out.append((os.path.relpath(p, ROOT), j.lineno, u.qualname, _text(j, m)))
    return out


def _loop_kind(start):
    """The start's thread runs on unless told, for the BODY's timed-join rule (_stop_in): a loop the walk read outright
    (not a loop found only in a product callee, _indirect, which the rule reads as bounded) or a thread of unreadable
    kind. A TIMED join in the body alone is a wait such a thread may outlive, not its stop."""
    return (start.kind == "loop" and not start.indirect) or start.kind == KIND_UNREAD


def _cleanup_needs_release(start):
    """The start's thread is a LOOP THE WALK READ OUTRIGHT (kind loop, not indirect): a cleanup must release it, a timed
    join alone is not its stop (_cleanup_ends). Not a thread of UNREADABLE kind: THE DOCUMENTED ACCEPTANCE (round 2 of PR
    891's review, 2026-09-22): the walk cannot show such a thread loops (its work is a call it cannot read, most often a
    handed-in function bounded by construction), there is no loop to release, and a cleanup's timed join runs on EVERY
    exit path, including one where a statement the body walk takes not to fail raises, and bounds the test's wait; whether
    the thread ended within the bound is the runtime oracle's to say. The body rule (_stop_in) stays strict for both: a
    body statement is guaranteed only by the walk's assumption that the statements before it do not fail, a cleanup by
    unittest, so the two rules differ by the strength of the guarantee, not by the thread."""
    return start.kind == "loop" and not start.indirect


def _cleanup_ends(call, nodes, start):
    """The cleanup's stop is more than a TIMED JOIN ALONE (round 2 of PR 891's review, 2026-09-22: the body rule applied to
    cleanups for a loop read outright): a stop verb other than join (set, shutdown, stop, cancel, close, terminate, kill,
    server_close, release) or the loops' seam as an attribute or a call, in its arguments or in the body of the function,
    lambda or method it names; a SENTINEL PUT (`put` / `put_nowait`) into a queue handed to the thread or one it reads
    (`q.put_nowait(None)` for km._ws_sender: the handler's own teardown sentinel); an UNTIMED join (`self.addCleanup(t.join)`
    with nothing after it; `t.join()` in the body); or a bare name that says stop whose body the walk does not have (a
    parameter, a returned callable: the name is the evidence, as before; not for a helper-module function, whose BOUND
    BODY is among the nodes and decides: join_started handed an Event releases, handed None it only joins). A timed join
    alone (`self.addCleanup(t.join, 10)`, `lambda: t.join(5)`, `lambda: [t.join(2) for t in ts]`) waits for the thread on
    every exit path and lets a loop run on when the bound passes: not the stop. The strict probe of 2026-09-22 found three
    such sites on the tree, all in tests/test_ws_send_bounded.py: the sender helper's cleanup, which already put the
    sentinel the walk had no verb for, and two socket drains, whose cleanups now shut the socket down before the join."""
    fed = _handed_names(start) | _release_names(start)
    for n in nodes:
        for sub in ast.walk(n):
            if isinstance(sub, ast.Attribute) and sub.attr in STOP_VERBS and sub.attr != "join":
                return True
            if isinstance(sub, ast.Name) and sub.id == STOP_SEAM:
                return True
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == "join" and not sub.args and not sub.keywords:
                return True
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr in ("put", "put_nowait") \
                    and ast.unparse(sub.func.value) in fed:
                return True
    if call.args and isinstance(call.args[0], ast.Attribute) and call.args[0].attr == "join" and len(call.args) == 1 and not call.keywords:
        return True                                     # self.addCleanup(t.join): the join itself, untimed
    named = [n for n in nodes if isinstance(n, ast.Name) and _says_stop(n.id)]
    bodies = [n for n in nodes if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.Module))]
    return bool(named) and not bodies


def _is_assertion(stmt):
    """The statement is a designed failure point: an assert* or fail call, a bare assert, a raise. A raise or an assertion
    inside a function the statement defines is that function's, not the statement's."""
    for sub in _run_nodes(stmt):
        if isinstance(sub, (ast.Assert, ast.Raise)):
            return True
        if isinstance(sub, ast.Call):
            nm = _callee_name(sub)
            if nm is not None and (nm.startswith("assert") or nm in ASSERTS):
                return True
    return False


def _cleanup_before(unit, line, start, extra=()):
    """A cleanup that names a stop of THIS thread, registered at or before `line` in the unit, or in the class's setUp /
    setUpClass (which run before every test body)."""
    for s, _b, _i, _st in unit.rows:
        for sub in unit.exprs[id(s)]:
            if isinstance(sub, ast.Call) and _is_cleanup_call(unit, sub) and sub.lineno <= line and _cleanup_stops(unit, sub, start, extra):
                return True
    if unit.cls is not None and unit.fn.name not in ("setUp", "setUpClass"):
        for name, fn in unit.hooks():
            if name in ("setUp", "setUpClass"):
                hook_unit = unit.module.unit_for(fn, unit.cls)
                for sub in ast.walk(fn):
                    if isinstance(sub, ast.Call) and _is_cleanup_call(hook_unit, sub) and _cleanup_stops(hook_unit, sub, start, extra):
                        return True
    return False


def _in_try_finally(stack):
    return any(isinstance(s, ast.Try) and s.finalbody and field == "body" for s, field in stack)


def _stop_in(unit, stmt, names, releases, start, extra=()):
    """The stop one statement holds for the thread: a cleanup naming its stop ('cleanup-before-first-assertion'); a join
    of the same receiver or list, a shutdown / stop / cancel of it or of the object its target runs on (called, or handed
    over as loop.call_soon_threadsafe(loop.stop)), a set / release of what it waits on, a shutdown of the socket it reads,
    a sentinel put into the queue it reads or was handed, or the loops' seam set for a product loop
    ('stop-before-first-assertion'). A TIMED join of a loop thread is a wait, not its stop: when it returns
    the loop runs on unless something else ended it, so it counts only beside a release, a shutdown or the seam."""
    loop_vars = {}
    for loop in ast.walk(stmt):
        if isinstance(loop, (ast.For, ast.comprehension)) and isinstance(loop.target, ast.Name):
            loop_vars[loop.target.id] = ast.unparse(loop.iter)
    target_recvs = _target_receivers(start) if start is not None else set()
    seam_ok = start is not None and start.kind == "loop" and _outside_target(start)
    loop_kind = start is not None and _loop_kind(start)
    timed_join, ended = False, False
    for sub in ast.walk(stmt):
        if isinstance(sub, ast.Call):
            if _is_cleanup_call(unit, sub) and _cleanup_stops(unit, sub, start, extra):
                return "cleanup-before-first-assertion"
            if not isinstance(sub.func, ast.Attribute):
                continue
            f = sub.func
            r = ast.unparse(f.value)
            same = r in names or (r in loop_vars and loop_vars[r] in names)
            if f.attr == "join" and same:
                if loop_kind and (sub.args or sub.keywords):
                    timed_join = True
                    continue
                return "stop-before-first-assertion"
            if f.attr in ("shutdown", "stop", "cancel", "close", "server_close") and (same or r in target_recvs):
                ended = True
            if f.attr in ("set", "release") and (r in releases or (seam_ok and STOP_SEAM in r)):
                ended = True
            if f.attr == "shutdown" and r in releases:      # peer.shutdown(SHUT_RDWR) wakes the recv a drain thread is parked in
                ended = True
            if f.attr in ("put", "put_nowait") and r in releases:   # q.put_nowait(None): the sentinel a queue-fed loop reads
                ended = True
        elif isinstance(sub, ast.Attribute) and sub.attr in ("stop", "shutdown", "cancel", "close") and ast.unparse(sub.value) in target_recvs:
            ended = True                                    # handed over: loop.call_soon_threadsafe(loop.stop)
    if ended:
        return "stop-before-first-assertion"
    return "timed-join" if timed_join else None


def _guard_ahead(unit, stmt, names, releases, start, extra=()):
    """The shape the walk forward from `stmt` meets before the first assertion: 'finally', 'cleanup-before-first-assertion',
    'stop-before-first-assertion', or None. The start's own statement is read first (`t.start(), t.join()` in one), then
    the statements after it. A timed join of a loop thread is passed over: the walk goes on to a release, a shutdown or
    the seam, and finds none before the assertion, the stop is behind it."""
    for nxt in [stmt] + list(unit.forward(stmt)):
        if nxt is not stmt:
            if isinstance(nxt, ast.Try) and nxt.finalbody:
                return "finally"
            if _is_assertion(nxt):
                return None
        r = _stop_in(unit, nxt, names, releases, start, extra)
        if r and r != "timed-join":
            return r
    return None


def _self_attrs_holding(unit, name):
    """The attributes on self/cls the unit stores the local name `name` in (assigned, appended or += into)."""
    out = []
    for s, _b, _i, _st in unit.rows:
        if isinstance(s, ast.Assign) and isinstance(s.value, ast.Name) and s.value.id == name:
            out += [t.attr for t in s.targets if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id in ("self", "cls")]
    for holder, values in unit.appends.items():
        if holder.startswith(("self.", "cls.")) and any(isinstance(v, ast.Name) and v.id == name for v in values):
            out.append(holder.split(".", 1)[1].split("[", 1)[0])
    return out


def _stored_attrs(start):
    """The attribute names on self/cls that hold the thread, the object its target runs on, or the event it waits on."""
    u, recv, names = start.unit, start.recv, []
    node = recv
    while isinstance(node, ast.Subscript):                    # self.threads["a"].start(): the holder
        node = node.value
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in ("self", "cls"):
        names.append(node.attr)
    if isinstance(recv, ast.Name):
        names += _self_attrs_holding(u, recv.id)
        for s, _b, _i, _st in u.rows:               # producer = self.producer = Thread(...)
            if isinstance(s, ast.Assign) and u.is_thread_ctor(s.value) and any(isinstance(t, ast.Name) and t.id == recv.id for t in s.targets):
                names += [t.attr for t in s.targets if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id in ("self", "cls")]
    expr = start.target_expr
    holders = []
    if isinstance(expr, ast.Attribute):
        holders.append(expr.value)
    for nm in _release_names(start):
        holders.append(_parse_chain(nm))
    body = _target_fn(start)
    if body is not None and not isinstance(expr, (ast.FunctionDef, ast.AsyncFunctionDef)):   # not a subclass's run()
        method, owner = _target_method(start)                   # a fake's self.go is the test's f.go, or nothing (inline)
        for sub in ast.walk(body):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr in FOREVER + BLOCKING + ("is_set",):
                nm = _own(ast.unparse(sub.func.value), owner if method is not None else "self")
                holders.append(_parse_chain(nm))
    for h in holders:
        if h is None:
            continue
        if isinstance(h, ast.Attribute) and isinstance(h.value, ast.Name) and h.value.id in ("self", "cls"):
            names.append(h.attr)
        elif isinstance(h, ast.Name):
            names += _self_attrs_holding(start.ctor_unit, h.id)
            if start.ctor_unit is not u:
                names += _self_attrs_holding(u, h.id)
    return sorted(set(names))


def _applies_stop(fn, attrs, loops_seam=True):
    """The function applies a stop verb to one of `attrs` (as a call or as a callback handed over), to a loop variable
    over one of them, or sets the loops' seam."""
    text = ast.unparse(fn)
    if not any(_word_in(a, text) for a in attrs):
        return False
    loop_vars = {}
    for loop in ast.walk(fn):
        if isinstance(loop, (ast.For, ast.comprehension)) and isinstance(loop.target, ast.Name):
            loop_vars[loop.target.id] = ast.unparse(loop.iter)
    for sub in ast.walk(fn):
        if isinstance(sub, ast.Attribute) and sub.attr in STOP_VERBS:
            recv = ast.unparse(sub.value)
            if any(_word_in(a, recv) for a in attrs):
                return True
            if recv in loop_vars and any(_word_in(a, loop_vars[recv]) for a in attrs):
                return True
            if loops_seam and sub.attr == "set" and STOP_SEAM in recv:
                return True
    return False


def _hook_stops(unit, attrs, start):
    for name, fn in unit.hooks():
        if _applies_stop(fn, attrs):
            return name
        if name in ("setUp", "setUpClass", "setUpModule"):
            hook_unit = unit.module.unit_for(fn, unit.cls)
            for sub in ast.walk(fn):
                if isinstance(sub, ast.Call) and _is_cleanup_call(hook_unit, sub) and _cleanup_stops(hook_unit, sub, start) \
                        and any(_word_in(a, ast.unparse(sub)) for a in attrs):
                    return name
    return None


def _object_owned(unit):
    if unit.cls is None or unit.module.is_testcase(unit.cls):
        return None
    for c in unit.module.bases_of(unit.cls):
        for f in c.body:
            if isinstance(f, ast.FunctionDef) and f.name in OWNER_ENDS:
                if any(isinstance(sub, ast.Attribute) and sub.attr in STOP_VERBS for sub in ast.walk(f)):
                    return f.name
    return None


def _start_names(start):
    names = {start.recv_text}
    if isinstance(start.recv, ast.Name):
        b = start.unit.binding_at(start.recv.id, start.line)
        if b is not None and isinstance(b[1], tuple) and b[1][0] == "for":
            names.add(ast.unparse(b[1][1]))
    return names


def classify(start, at=None):
    """The stop shape of one start, read in its own function or, for a helper's start, at a caller's call site `at`
    (unit, statement, stack, line)."""
    if at is None:
        unit, stmt, stack, line, extra = start.unit, start.stmt, start.stack, start.line, ()
    else:
        unit, stmt, stack, line = at
        extra = tuple(ast.unparse(t) for t in getattr(stmt, "targets", [])) + tuple(unit.assigned_attrs(stmt))
    if _in_try_finally(stack):
        return "finally"
    if _cleanup_before(unit, line, start, extra):
        return "cleanup-before-start"
    names, releases = _start_names(start) | set(extra), _release_names(start)
    ahead = _guard_ahead(unit, stmt, names, releases, start, extra)
    if ahead:
        return ahead
    attrs = _stored_attrs(start) if at is None else sorted(set(_stored_attrs(start)) | set(unit.assigned_attrs(stmt)))
    if attrs:
        hook = _hook_stops(unit, attrs, start)
        if hook:
            return "class-hook:" + hook
    if at is None:
        owner = _object_owned(unit)
        if owner:
            return "object-owned:" + owner
    return "tail-only"


def census(paths, loops=None, thread_classes=None, helpers=None, product=None, extras=None, modules=None):
    """Every thread start under `paths`: rows (start, shape, where) with `where` the unit the shape was read in (the
    start's own, or a caller's); a receiver the walk cannot read is a row with shape 'unreadable'. `helpers` maps the
    helper modules under tests/ a test may import (helper_modules) so a thread one of their functions returns is read;
    `product` is the _Product index of the product sources a product target is read in (built here when None). A dict
    handed as `extras` is filled in the same pass: "modules" (the count of modules read), "product_starts" (the
    INFORMATIONAL _ProductStart rows: threads the product starts on a test's call) and "oracle" (the modules that
    import or call tests/conftest.py's thread_census / wait_for_census). A dict handed as `modules` receives each path's
    _Module, so a second reading of the same modules (list_join_cleanups in the tree derivation, _Tree) reuses their
    units instead of building them again."""
    loops = product_loops() if loops is None else loops
    thread_classes = product_thread_classes() if thread_classes is None else thread_classes
    helpers = helper_modules() if helpers is None else helpers
    product = _Product() if product is None else product
    out, cache = [], {}
    if extras is not None:
        extras["modules"], extras["product_starts"], extras["oracle"] = 0, [], []
    for p in paths:
        m = _Module(p, loops, thread_classes=thread_classes, helpers=helpers, helper_cache=cache, product=product)
        if modules is not None:
            modules[p] = m
        if extras is not None:
            extras["modules"] += 1
            if m.calls_oracle:
                extras["oracle"].append(os.path.relpath(p, ROOT))
        for u in m.units():
            if extras is not None:
                extras["product_starts"].extend(u.product_starts())
            for st in u.starts():
                if not st.is_thread:
                    out.append((st, "unreadable", u.qualname))
                    continue
                shape = classify(st)
                if shape != "tail-only" or u.fn.name.startswith("test_") or u.fn.name in HOOK_NAMES:
                    out.append((st, shape, u.qualname))
                    continue
                callers = u.callers()
                if not callers:
                    out.append((st, shape, u.qualname))
                    continue
                for (cu, call, s, block, i, stack) in callers:
                    view = st.at_caller(cu, call)                # the caller's hands: a parameter target, a parameter called
                    shape = classify(view, at=(cu, s, stack, call.lineno))
                    if shape == "tail-only" and view.kind in KINDS_PINNED + (KIND_UNREAD,) and not (cu.fn.name.startswith("test_") or cu.fn.name in HOOK_NAMES):
                        callers2 = cu.callers()                  # a helper's helper (`_hammer(fn)` calling `_run(lambda: fn())`):
                        if callers2:                             # classed at ITS callers, with both levels' hands
                            for (cu2, call2, s2, _b2, _i2, stack2) in callers2:
                                outer = _given_from(cu.fn, call2, cu2, cu, None, "handed in by the caller")
                                view2 = st.at_caller(cu, call, outer=outer)
                                out.append((view2, classify(view2, at=(cu2, s2, stack2, call2.lineno)), cu2.qualname))
                            continue
                    out.append((view, shape, cu.qualname))
    return out


_HAND = re.compile(r"^\S+ of .+? is `.*`(?:\.[\w.<>]+|\[\]|\(\))* (handed in by the caller|handed in at the construction|handed in at the call|its default)$")


def bounded_reason_is_read(why):
    """The reason of a bounded row says a body was READ (or a stdlib call is in the table): its HEAD is _body_kind's own
    verdict, a tuple's elements each read, a product function read, a Thread with no target, a constant in hand for a
    callable, a STDLIB_RETURNS entry or a conditioned rule's verdict, and every further segment (after ` | `) is a HAND:
    the argument a parameter was given and where (`fn of _run is `_once` handed in by the caller`), whose own verdict
    was read in turn (a hand read loop or waits makes the row that, never bounded)."""
    head, *hands = why.split(" | ")
    ok = head in ("no loop, no untimed wait", "no target: the default run() does nothing") \
        or head.startswith(("each of ", "a product function read in ", "a constant `", "a literal ") + CONDITIONED_HEADS) \
        or head in STDLIB_RETURNS.values()
    return ok and all(_HAND.match(h) for h in hands)


def stdlib_table_problems(table):
    """The entries of a STDLIB_RETURNS-shaped table whose reason does not say, in UNCONDITIONAL_WORDS, that the call
    returns whatever its arguments and on any stdlib receiver (the property that lets a name alone excuse a thread), and
    the entries that are CONDITIONED names (their check runs at the call): [(name, the problem)]."""
    out = []
    for name, reason in sorted(table.items()):
        missing = [w for w in UNCONDITIONAL_WORDS if w not in reason]
        if missing:
            out.append((name, "the reason does not say %s" % " and ".join("'%s'" % w for w in missing)))
        if name in STDLIB_CONDITIONED:
            out.append((name, "a conditioned name: its check runs at the call, it cannot be excused by name"))
    return out


def tail_only(rows, allow=None):
    """(loop/waits sites whose stop is tail-only and not excused, the UNREADABLE sites (a receiver the walk cannot read,
    or a thread of unreadable KIND whose stop is tail-only and not excused), stale allow entries, the bounded tail-only
    sites the BOUNDED rule excuses). Only a bounded kind is ever excused by the shape alone."""
    allow = ALLOW if allow is None else allow
    tails, unread, bounded, seen = [], [], [], set()
    for st, shape, where in rows:
        if shape == "unreadable":
            unread.append((st, where))
        elif shape == "tail-only":
            key = (st.file(), where, st.target)
            seen.add(key)
            if st.kind == KIND_UNREAD:
                if key not in allow:
                    unread.append((st, where))
            elif st.kind not in KINDS_PINNED:
                bounded.append((st, where))
            elif key not in allow:
                tails.append((st, where))
    stale = [k for k in allow if k not in seen]
    return tails, unread, stale, bounded


def module_paths(root=HERE):
    return sorted(os.path.join(root, f) for f in os.listdir(root) if f.startswith("test_") and f.endswith(".py"))


_MODULE_COUNT = re.compile(r"\b\d{3,}\s+(?:test\s+)?modules\b|\bof\s+(?:the\s+)?\d{3,}(?=\s*[,;.)]|\s+(?:test\s+)?modules\b|\s*$)|\bmodules\s*\(\d{3,}\b")


def _literal_module_counts(text):
    """The literal module counts in a prose text, the shapes the population figure has taken: a number of three or more
    digits before `modules` or `test modules`, after `of` or `of the` when a comma, a semicolon, a period, a parenthesis, the
    word modules or the end follows (not a date, a time, a decimal or a quantity with a unit: `a sleep of 3600 s`), or in a
    parenthesis after `modules`. The population has one home, the table; a tree test pins this empty over the prose's three
    homes: this module's docstring, the liveness module's docstring and the ledger entry."""
    return [m.group(0) for m in _MODULE_COUNT.finditer(text)]


def _report(rows, only_tail=False):
    lines = []
    for st, shape, where in sorted(rows, key=lambda r: (r[0].file(), r[0].line)):
        if only_tail and (shape not in ("tail-only", "unreadable") or (shape == "tail-only" and st.kind not in KINDS_PINNED + (KIND_UNREAD,))):
            continue
        lines.append("%-8s %-24s %s  [at %s]  (%s)" % (st.kind, shape, st.describe(), where, st.why))
    return "\n".join(lines)


def _report_info(info):
    """The INFORMATIONAL rows, one line each: kind, category, site, what starts."""
    return "\n".join("%-13s %-16s %s  (%s)" % (r.kind, r.shape, r.describe(), r.why) for r in sorted(info, key=lambda r: (r.file(), r.line)))


TREE_KEY = ("tests/test_thread_stop_census.py", "the tree")   # parse_cache.derived's key for _Tree, with the root appended


class _Tree:
    """THE ONE DERIVATION over the tree, built once per process (tree_census, behind parse_cache.derived under TREE_KEY): the
    population (`paths`), the product loops and thread classes, the helper modules, the product index, the rows, the
    informational rows and the oracle modules (`extras`) and the inline list joins in the cleanups (`list_joins`,
    list_join_cleanups over the same modules census built). ThreadStopCensus.setUpClass, the --table road and the
    list-join pin all read it, so the tree is parsed once per module and derived once per process, whichever runs first;
    a tree test pins that through the helper's counters."""
    def __init__(self, root):
        self.root = root
        self.paths = module_paths(os.path.join(root, "tests"))
        self.loops = product_loops(root)
        self.thread_classes = product_thread_classes(root)
        self.helpers = helper_modules(root)
        self.product = _Product(root)
        self.extras, modules = {}, {}
        self.rows = census(self.paths, self.loops, self.thread_classes, self.helpers, self.product, self.extras, modules=modules)
        self.list_joins = list_join_cleanups(self.paths, self.helpers, modules=modules)


def tree_census(root=ROOT):
    """The tree's derivation (_Tree): built on the first call in the process, the same object after (parse_cache.derived).
    The one entry point for the tests and the --table road."""
    return PC.derived(TREE_KEY + (root,), lambda: _Tree(root))


class ThreadStopCensus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = tree_census()
        cls.loops, cls.thread_classes = cls.tree.loops, cls.tree.thread_classes
        cls.extras, cls.rows = cls.tree.extras, cls.tree.rows

    def test_every_loop_or_waiting_thread_a_test_starts_is_stopped_on_every_exit_path(self):
        tails, unread, stale, _bounded = tail_only(self.rows)
        problems = []
        for st, where in tails:
            problems.append("TAIL-ONLY stop of a %s thread (%s): %s (classed at %s). Register the stop as a cleanup BEFORE the "
                            "start (self.addCleanup(end), where end sets the stop, releases the gate and joins), or store the "
                            "thread on self and stop it in tearDown, or start it inside a try whose finally stops it."
                            % (st.kind, st.why, st.describe(), where))
        for st, where in unread:
            if st.is_thread:
                problems.append("UNREADABLE target: %s (classed at %s): %s. The walk could not read what the thread does, so "
                                "its tail-only stop is not excused as bounded. Make the target a function of the test module or "
                                "a product function the walk can find, stop it on every exit path (a cleanup registered before "
                                "the start, tearDown, a finally), or excuse it by name in ALLOW with the reason."
                                % (st.describe(), where, st.why))
                continue
            problems.append("UNREADABLE receiver: %s: the walk could not resolve what .start() is called on; bind the receiver "
                            "in the same function (t = threading.Thread(...)) or on self, or return the construction from the "
                            "helper that builds it." % st.describe())
        for k in stale:
            problems.append("STALE allow entry %r: it matches no tail-only site at this head; remove it." % (k,))
        self.assertEqual(problems, [], "\n%d modules read (tests/test_*.py, non-recursive), %d start rows, %d allow entries\n%s"
                         % (self.extras["modules"], len(self.rows), len(ALLOW), "\n".join(problems)))

    def test_the_product_loops_the_walk_reads_include_the_kernels_three_long_lived_loops(self):
        for name in ("_producer", "_pusher", "_heartbeat", "_jobs_loop", "_ws_sender"):
            self.assertIn(name, self.loops, name)

    def test_the_census_reads_the_shapes_the_tree_has(self):
        """The heartbeat module's loops through its _start helper (stored on self, joined in tearDown); the parked-ops
        module's producer (a cleanup registered before the start); the judges' process module's producer through its
        _pass helper (the stop seam set and the join done before any assertion); a fake server owned by its close();
        a peer server whose shutdown is the cleanup registered right after the start; the ws liveness module's Thread
        SUBCLASSES (_Peer, _Handler: their run() loops, appended to self.threads by +=, joined in tearDown); the update
        module's local alias (Real = threading.Thread) serving a fake manager inside a try whose finally shuts it down;
        the served checkpoint module's sampler bound by a conditional expression; and the atomic-write hammers, whose
        for-target name a comprehension had bound earlier (the binding in force at the start is the later one)."""
        by_file = {}
        for st, shape, where in self.rows:
            by_file.setdefault(st.file(), []).append((st.target, st.kind, shape, where))
        hb = by_file.get("tests/test_heartbeat_thread.py", [])
        self.assertTrue(any(t == "target" and s.startswith("class-hook:tearDown") for t, k, s, w in hb), hb)
        po = by_file.get("tests/test_kernel_parked_ops_liveness.py", [])
        self.assertTrue(po, "the parked-ops module starts a producer")
        self.assertTrue(all(k == "loop" and s == "cleanup-before-start" for t, k, s, w in po), po)
        sd = by_file.get("tests/test_spend_detail.py", [])
        self.assertTrue(any(t == "srv.serve_forever" and s == "cleanup-before-first-assertion" for t, k, s, w in sd), sd)
        bs = by_file.get("tests/test_bus_seed_token.py", [])
        self.assertTrue(bs and all(s.startswith("class-hook:tearDown") for t, k, s, w in bs), bs)
        jp = by_file.get("tests/test_judges_process.py", [])
        self.assertTrue(any(t == "km._producer" and k == "loop" and s == "stop-before-first-assertion" for t, k, s, w in jp), jp)
        fb = by_file.get("tests/test_kernel_bus_restore.py", [])
        self.assertTrue(any(t == "self.srv.serve_forever" and s == "object-owned:close" for t, k, s, w in fb), fb)
        wl = {(t, k, s) for t, k, s, w in by_file.get("tests/test_ws_liveness.py", [])}
        self.assertTrue({("_Handler.run", "loop", "class-hook:tearDown"), ("_Peer.run", "loop", "class-hook:tearDown")} <= wl, wl)
        ku = {(t, k, s, w) for t, k, s, w in by_file.get("tests/test_kernel_update.py", [])}
        for where in ("Routes.test_a_converge_thread_that_fails_to_start_gives_the_flag_back_and_the_next_click_converges",
                      "Routes._drift_click_whose_thread_fails_to_start"):                  # Real(target=mgr.serve_forever)
            self.assertIn(("mgr.serve_forever", "loop", "finally", where), ku)
        cs = by_file.get("tests/test_asm_checkpoint_served.py", [])
        self.assertIn(("sample", "finally"), [(t, s) for t, k, s, w in cs], cs)
        aw = by_file.get("tests/test_atomic_write.py", [])
        self.assertIn(("hammer", "bounded", "stop-before-first-assertion"), [(t, k, s) for t, k, s, w in aw], aw)
        # the product road (pass 4): km._login_reader's body is read (its _login_reader_loop reads a pty: waits, no longer
        # 'bounded, no while'); jd.serve iterates iter(f, sentinel); be.set_model reaches a while through the class's own
        # methods, and the cleanup registered before the start is its stop; a parameter target is read at each caller
        lf = by_file.get("tests/test_login_flow.py", [])
        self.assertIn(("km._login_reader", "waits", "stop-before-first-assertion"), [(t, k, s) for t, k, s, w in lf], lf)
        js = by_file.get("tests/test_judge_serve.py", [])
        self.assertIn(("jd.serve", "loop", "cleanup-before-start"), [(t, k, s) for t, k, s, w in js], js)
        cbk = by_file.get("tests/test_codex_backend.py", [])
        self.assertIn(("be.set_model", "loop", "cleanup-before-start"), [(t, k, s) for t, k, s, w in cbk], cbk)
        sm = by_file.get("tests/test_stage_marks.py", [])
        self.assertIn(("runner", "bounded", "tail-only", "BuildsCountUnderTheThreadsStage.test_a_pool_workers_build_lands_under_the_tier_that_submitted_it"), sm, sm)
        ps = by_file.get("tests/test_perf_stats.py", [])
        self.assertIn(("target", "bounded", "stop-before-first-assertion"), [(t, k, s) for t, k, s, w in ps], ps)
        fc = by_file.get("tests/test_first_cycle_stage_split.py", [])     # km = kernel_module() through another test module's
        self.assertIn(("km._LOOPS_STOP.set", "bounded", "finally"), [(t, k, s) for t, k, s, w in fc], fc)   # function; Event.set
        # pass 5: a bound .start handed on as a keyword argument (tests/test_postal_token.py:436, before=writer.start): the tree's
        # one such row, classed at the handing statement, whose own `after=lambda: writer.join(timeout=5)` is the join
        pt = by_file.get("tests/test_postal_token.py", [])
        self.assertIn(("lambda: os.replace(str(tmp), str(live))", "bounded", "stop-before-first-assertion"), [(t, k, s) for t, k, s, w in pt], pt)
        self.assertEqual([(st.file(), st.target) for st, _s, _w in self.rows if st.handed],
                         [("tests/test_postal_token.py", "lambda: os.replace(str(tmp), str(live))")])

    def test_the_threads_the_product_starts_on_a_tests_call_are_counted(self):
        """INFORMATIONAL rows over the tree (romp-manager's ruling, 2026-09-22): the threads the PRODUCT starts on a test's
        call are counted rather than invisible. Every row is kind product-start and none is a start row; the counts held
        here are the ruling's figures as floors (the table prints the exact ones): SdkSession.start() in 5 modules,
        km._new_ws_client(...) with start_sender defaulting True at 3 sites, sb.SdkBackend(..., reconcile=True) handed at
        2 sites (the ruling's 6 counted four mentions in docstrings, a comment and an assertIn string) and never a
        construction that leaves reconcile False, loop.run_in_executor at 5 sites (four on an untimed Event.wait), every
        ThreadPoolExecutor under a with, and the spawn-helpers the ruling named among the heads."""
        info = self.extras["product_starts"]
        by = {}
        for r in info:
            by.setdefault(r.shape, []).append(r)
        self.assertEqual({r.kind for r in info}, {PRODUCT_START})
        self.assertFalse({id(r) for r in info} & {id(st) for st, _s, _w in self.rows})
        sess = {r.file() for r in by.get("object-start", []) if r.why.startswith("SdkSession's own start()")}
        self.assertGreaterEqual(len(sess), 5, sorted(sess))
        ws = [r for r in by.get("spawn-helper", []) if r.why.startswith("_new_ws_client starts")]
        self.assertGreaterEqual(len(ws), 3, [r.describe() for r in ws])
        self.assertTrue(all("start_sender True by default" in r.why for r in ws), [r.why for r in ws])
        rec = [r for r in by.get("spawn-helper", []) if r.why.startswith("SdkBackend.__init__ starts")]
        self.assertGreaterEqual(len([r for r in rec if "reconcile True handed in" in r.why]), 2, [r.describe() for r in rec])
        self.assertTrue(all("when reconcile is true" in r.why for r in rec), [r.why for r in rec])
        ex = by.get("run_in_executor", [])
        self.assertGreaterEqual(len(ex), 5, [r.describe() for r in ex])
        self.assertGreaterEqual(len([r for r in ex if r.why.endswith("an untimed wait")]), 4, [r.why for r in ex])
        pools = by.get("pool", [])
        self.assertTrue(pools and all("under a with" in r.why for r in pools), [r.describe() for r in pools])
        heads = {r.why.split(" starts ")[0] for r in by.get("spawn-helper", [])}
        for name in ("run_pass", "helper_key", "CodexBackend._handshake", "_boot_warm", "_push_notify"):
            self.assertIn(name, heads, sorted(heads))
        self.assertFalse([r.describe() for r in info if "matched by name" in r.why],
                         "a spawn-helper matched by name across the product: resolve the alias's file")

    def test_the_runtime_oracle_is_called_by_the_modules_the_docstring_counts(self):
        """The docstring's claim about the runtime oracle carries its figure (romp-manager's ruling, 2026-09-22): the modules
        that import or call thread_census / wait_for_census, derived by the census in the same pass, printed by the table,
        held here against the sentence."""
        m = re.search(r"only in the modules that call it: (\d+) test modules", __doc__)
        self.assertIsNotNone(m, "the docstring's bounded bullet states the oracle's figure")
        oracle = self.extras["oracle"]
        self.assertEqual(int(m.group(1)), len(oracle), "%d of %d modules import or call the oracle: %s; restate the docstring's figure"
                         % (len(oracle), self.extras["modules"], oracle))
        for name in ("tests/test_kernel_parked_ops_liveness.py", "tests/test_heartbeat_thread.py", "tests/test_codex_backend.py"):
            self.assertIn(name, oracle)
        self.assertNotIn("tests/test_thread_stop_census.py", oracle, "this module names the oracle in its docstring only")

    def test_no_literal_module_count_stands_in_any_of_the_three_homes(self):
        """romp-manager's ruling on the ninth pass (2026-09-22): the population count has ONE home, the table the census
        prints, and no literal module count stands in prose. The pin this replaces held the docstring's figure to the count
        read; CI tests a pull request's MERGE with main, so it went red the day main gained a test module
        (tests/test_docs_stylesheet.py), and would every time. This pins the ABSENCE: no number of three or more digits
        stands beside the word modules, in the shapes the population figure took (`NNN modules`, `NNN test modules`,
        `(of NNN,`, `of the NNN`, `modules (NNN`), in ANY of the prose's THREE HOMES (the reviewer's ruling on the tenth
        pass, 2026-09-22; the ninth's pin read this docstring alone): this module's docstring, the liveness module's
        docstring (tests/test_kernel_parked_ops_liveness.py, whose reach sentence carried the figure) and the ledger entry
        (upstream/2026-09-21-parked-ops-liveness-boot-hold.md, which carried ten); the failure message names the three.
        The liveness module's docstring is read from its PARSED FILE (parse_cache.source_and_tree, the parse the tree
        derivation already holds, so this test parses nothing, held on the counter; ast.get_docstring of the module,
        uncleaned, which is the module's __doc__ verbatim: asserted on this module, where both roads are in hand) and NOT
        by importing it: its import sets XDG_STATE_HOME to a fresh directory for the whole process and loads bin/romp-kernel
        under a module name of its own, side effects a census that reads the tree by parse must not take in the middle of
        a run (this module alone under pytest, or as a script, has not imported it, and every test after it in the process
        would read the liveness module's state root). The ledger entry is read by path, as text. The oracle bullet's `5
        test modules` is the oracle's own figure, derived and held by the test above, and the reach figure of the
        2026-09-21 probe is phrased as callers in both docstrings. THE RED, planted in each home: the sentences the
        docstring carried, with the count the census read written into their shapes (so this test carries no literal
        either), appended to the home's text one at a time, and the regex names exactly the plant and nothing of the home;
        and a date, a commit, a quantity with a unit or a two-digit figure is not a count."""
        own = PC.source_and_tree(__file__)[1]
        self.assertEqual(ast.get_docstring(own, clean=False), __doc__,
                         "the parse road reads this module's docstring as its __doc__: the liveness module's is read the same way")
        parses = PC.stats()["parses"]
        liveness = os.path.join(HERE, "test_kernel_parked_ops_liveness.py")
        ledger = os.path.join(ROOT, "upstream", "2026-09-21-parked-ops-liveness-boot-hold.md")
        with open(ledger, encoding="utf-8") as f:
            ledger_text = f.read()
        homes = (("tests/test_thread_stop_census.py (its docstring)", __doc__),
                 ("tests/test_kernel_parked_ops_liveness.py (its docstring)",
                  ast.get_docstring(PC.source_and_tree(liveness)[1], clean=False)),
                 ("upstream/2026-09-21-parked-ops-liveness-boot-hold.md", ledger_text))
        self.assertEqual(PC.stats()["parses"], parses, "the liveness module's docstring came from the parse the tree holds")
        names = ", ".join(name for name, _text in homes)
        for name, text in homes:
            self.assertTrue(text and "modules" in text, "%s: the text read carries the word the regex looks beside" % name)
            self.assertEqual(_literal_module_counts(text), [], "a literal module count in %s: the table is its one home; the "
                             "three prose homes this pin reads are %s" % (name, names))
        n = self.extras["modules"]
        for planted in ("the listing of tests/test_*.py (module_paths; %d modules at this head, a figure the table prints" % n,
                        "call it: 5 test modules at this head (of %d, 2026-09-22: test_codex_backend" % n,
                        "the runtime oracle called by 5 of the %d" % n, "the runtime oracle called by 5 of the %d; the liveness module" % n,
                        "a population of %d test modules" % (n + 63), "the modules (%d at this head)" % n):
            named = _literal_module_counts(planted)
            self.assertTrue(named, planted)
            for name, text in homes:                              # the red in each home: the plant, and only the plant, is named
                self.assertEqual(_literal_module_counts(text + "\n" + planted), named, "%s with the plant %r" % (name, planted))
        for fine in ("5 test modules at this head (of the modules the census reads, a count the table prints; 2026-09-22:",
                     "the probe of 2026-09-22", "kernel commit 3421c94d0", "13 modules save stores", "141 callers of jd._rebind_state()",
                     "on 20000 random payloads", "round 2 of PR 891's review", "a sleep of 3600 s, or of a name", "a bound of 107 bytes"):
            self.assertEqual(_literal_module_counts(fine), [], fine)

    def test_every_bounded_kind_comes_from_a_read_body_or_the_stdlib_table(self):
        """THE RULE over the tree: no bounded row carries a reason other than a body the walk read (its own, each of a
        tuple's, a product function's), the default run() of a Thread with no target, or a STDLIB_RETURNS entry; and
        every unreadable-kind row is either guaranteed by its shape or listed."""
        bad = [(st.describe(), st.why) for st, _s, _w in self.rows if st.kind == "bounded" and not bounded_reason_is_read(st.why)]
        self.assertEqual(bad, [])
        for st, shape, where in self.rows:
            if st.kind == KIND_UNREAD and shape == "tail-only":
                self.assertIn((st.file(), where, st.target), ALLOW, st.describe())

    def test_the_bounded_rule_excuses_at_least_one_site_or_it_is_stale(self):
        _tails, _unread, _stale, bounded = tail_only(self.rows)
        self.assertTrue(bounded, "no bounded thread has a tail-only join anymore: retire the BOUNDED shape rule")

    def test_the_population_is_what_pytest_collects_under_tests(self):
        """The census reads the non-recursive listing of tests/test_*.py (module_paths). pytest, with no configuration file in
        this repository, collects by its defaults: python_files `test_*.py` AND `*_test.py`, recursively under tests/. The two
        agree only while no configuration appears (a pytest.ini, setup.cfg, tox.ini or pyproject.toml at the repository root
        OR under tests/: pytest's inifile search starts at the arguments' common ancestor and walks up, so a file under tests/
        governs `pytest tests/`, round 2 of PR 891's review; a python_files line in
        tests/conftest.py), no `*_test.py` exists anywhere under tests/ and no `test_*.py` sits below the top level: this pins
        that emptiness, so the day one appears the census says so instead of silently omitting it (romp-manager's ruling,
        2026-09-22); and the listing's length is the count the census read."""
        for root in (ROOT, HERE):                # the inifile search starts at the arguments' common ancestor: `pytest tests/`
            for name in ("pytest.ini", "setup.cfg", "tox.ini", "pyproject.toml"):   # would be governed by a file under tests/
                self.assertFalse(os.path.exists(os.path.join(root, name)),
                                 "%s exists: pytest's collection may no longer be its defaults; re-derive the population"
                                 % os.path.relpath(os.path.join(root, name), ROOT))
        with open(os.path.join(HERE, "conftest.py"), encoding="utf-8") as f:
            self.assertNotIn("python_files", f.read(), "tests/conftest.py names python_files: the collection pattern moved; re-derive the population")
        strays = []
        for dirpath, _dirs, files in os.walk(HERE):
            for name in files:
                if name.endswith("_test.py") or (name.startswith("test_") and name.endswith(".py") and dirpath != HERE):
                    strays.append(os.path.relpath(os.path.join(dirpath, name), ROOT))
        self.assertEqual(sorted(strays), [], "pytest collects these by its defaults and the census does not read them: widen module_paths or move them")
        self.assertEqual(len(module_paths()), self.extras["modules"])

    def test_the_helper_modules_under_tests_are_parsed_for_thread_factories(self):
        """The road a test takes to a thread through a helper module is walked over the tree: the helper modules the
        tests import are found by their import names, and each of their functions is read for a returned Thread. None
        returns one at this head; the docstring's does-not-see paragraph says so and dates it."""
        hm = helper_modules()
        for key in ("conftest", "fs_clock", "git_fixture", "lab_dist", "romp_load", "fixtures.fake_claude", "thread_ends", "parse_cache"):
            self.assertIn(key, hm)
        self.assertEqual(helper_thread_factories(helpers=hm), [],
                         "a helper module returns a Thread now: the census reads it; update the does-not-see paragraph")

    def test_every_cleanup_that_joins_a_list_of_threads_goes_through_the_helper(self):
        """Round 2 of PR 891's review (2026-09-22): every cleanup REGISTRATION in the test modules that joins a list of threads
        goes through tests/thread_ends.py's join_started, whose join is guarded on the thread having started; held by census,
        not by grep: list_join_cleanups derives the inline list joins over every cleanup registration of the tree and this
        pins the list empty (the plant reds it on an inline comprehension). Registrations only: the two tearDowns that join a
        list inline (tests/test_heartbeat_thread.py's, tests/test_ws_liveness.py's) are outside the pin, named in the module
        docstring. The helper itself is in the tree (helper_modules) and is the guarded shape."""
        self.assertIn("thread_ends", helper_modules())
        _src, helper = PC.source_and_tree(os.path.join(HERE, "thread_ends.py"))
        fn = next(n for n in helper.body if isinstance(n, ast.FunctionDef) and n.name == "join_started")
        joins = _list_joins(fn)
        self.assertEqual(len(joins), 1, "the helper joins the list once")
        self.assertTrue(any(isinstance(n, ast.If) and "ident" in ast.dump(n.test) for n in ast.walk(fn)), "the helper's join is guarded on ident")
        found = self.tree.list_joins                    # list_join_cleanups over the tree, in the one derivation (_Tree)
        self.assertEqual(found, [], "a cleanup joins a list of threads inline; route it through tests/thread_ends.py's join_started "
                                    "(the guard on a thread never started, written once):\n%s"
                                    % "\n".join("%s:%d %s: %s" % f for f in found))

    def test_the_tree_is_parsed_once_per_module_and_derived_once_per_process(self):
        """THE MECHANISM, not the seconds (romp-manager's ruling on the ninth pass, 2026-09-22: CI's 3.10 and 3.11 cells had
        been cancelled at their 25-minute cap with this module's serial cost in them, and a pin on seconds would read a slow
        runner as a defect). Every file the census reads goes through tests/parse_cache.py, one parse per file per process,
        and the whole tree derivation (_Tree: the product index, every module's units, the rows, the list joins) sits behind
        one derived() key, so setUpClass, the --table road and every test of this class read ONE derivation. Held through
        the helper's counters: the entry point run twice more answers the object setUpClass holds and builds nothing (the
        key's build count stays 1, the process's derivation count does not move, the hit count moves by two); no file is
        parsed by those calls; every module of the population and every product file the index holds was parsed exactly
        once; and the parse count over the population equals the module count (the helper's one lock keeps that so under
        threads, and its four-field key under a rewrite, each planted in ParseCacheKeyAndLock; the key's stated blind
        spot, a same-size in-place rewrite within the timestamp granularity, is named in the message). THE RED, planted
        on a key of this test's own
        beside the census's (clearing the census's own cache here would only make the next test derive again): a copy of the
        entry point that forgets its key between two calls builds twice, and the counters show it, because clear() leaves
        them alone; the same counters would show a second parse or derivation of the tree."""
        before = PC.stats()
        again, third = tree_census(), tree_census()
        self.assertIs(again, self.tree, "the entry point answers the derivation setUpClass holds")
        self.assertIs(third, self.tree)
        after = PC.stats()
        self.assertEqual(PC.builds_of(TREE_KEY + (ROOT,)), 1, "the tree was derived more than once in this process")
        self.assertEqual(after["derivations"], before["derivations"], "the two calls built nothing")
        self.assertEqual(after["derived_hits"], before["derived_hits"] + 2, "the two calls were answered from the cache")
        self.assertEqual(after["parses"], before["parses"], "the two calls parsed nothing")
        files = list(self.tree.paths) + sorted(self.tree.product.trees)
        self.assertEqual([os.path.relpath(p, ROOT) for p in files if PC.parses_of(p) != 1], [],
                         "a module of the population or a product file was parsed other than once in this process (the key is the "
                         "file's size, mtime_ns, inode and ctime_ns: a rewrite that keeps all four, a same-size in-place write within "
                         "the timestamp granularity, is the stated blind spot, served the old tree and never a second parse here)")
        self.assertEqual(sum(PC.parses_of(p) for p in self.tree.paths), self.extras["modules"],
                         "one parse per module: the parse count over the population is the module count")
        key = ("tests/test_thread_stop_census.py", "a planted key: the red of this pin")
        built = []

        def entry_point(forget):                                  # a copy of tree_census over the planted key
            if forget:
                PC.clear(key)
            return PC.derived(key, lambda: built.append(1) or object())
        a, b = entry_point(False), entry_point(False)
        self.assertIs(a, b)
        self.assertEqual((len(built), PC.builds_of(key)), (1, 1), "two calls, one build")
        c = entry_point(True)
        self.assertIsNot(c, a)
        self.assertEqual((len(built), PC.builds_of(key)), (2, 2), "the red: the copy that forgets its key builds again, and the counter says so")
        PC.clear(key)

    def test_the_product_files_parse_is_shared_with_any_other_census_in_the_process(self):
        """The cross-module property (the cross-PR ruling of 2026-09-22: one shared parse cache per process, in a tests-local
        helper both censuses import). A second census in the same process that reads kernel/kernel.py or another product
        file through tests/parse_cache.py gets THIS census's parse: stated from this side, after the derivation
        source_and_tree over every product file the index holds answers the very tree object the index holds, counts a hit
        and no parse, and kernel/kernel.py was parsed once in the process. The state-root censuses adopt the helper in their
        own pull request; their derivation then reads these entries. The key holds the file's size, mtime_ns, inode and
        ctime_ns, so a file REWRITTEN between two calls is parsed again (shown on a planted file: two texts of different
        sizes, two parses; a restored mtime and a rename-over are ParseCacheKeyAndLock's plants) and an unchanged one is not
        (a third call, one more hit and no parse)."""
        before = PC.stats()
        for p, tree in sorted(self.tree.product.trees.items()):
            _text_, again = PC.source_and_tree(p)
            self.assertIs(again, tree, "%s: another census's read is this census's parse" % os.path.relpath(p, ROOT))
        after = PC.stats()
        self.assertEqual(after["parses"], before["parses"], "no product file was parsed again")
        self.assertEqual(after["parse_hits"], before["parse_hits"] + len(self.tree.product.trees))
        self.assertEqual(PC.parses_of(os.path.join(ROOT, "kernel", "kernel.py")), 1, "kernel/kernel.py: one parse in the process")
        d = tempfile.mkdtemp(prefix="romp-tests-census-")
        self.addCleanup(shutil.rmtree, d, True)
        p = os.path.join(d, "rewritten.py")
        with open(p, "w", encoding="utf-8") as f:
            f.write("x = 1\n")
        first = PC.source_and_tree(p)[1]
        with open(p, "w", encoding="utf-8") as f:
            f.write("x = 1\ny = 2\n")
        second = PC.source_and_tree(p)[1]
        third = PC.source_and_tree(p)[1]
        self.assertIsNot(first, second, "a rewritten file is parsed again")
        self.assertIs(second, third, "an unchanged file is not")
        self.assertEqual(PC.parses_of(p), 2)
        PC.clear(p)


class ParseCacheKeyAndLock(unittest.TestCase):
    """tests/parse_cache.py's key and lock, each property planted on a file or a key of this class's own, never on a
    population module or a product file (the counter pin holds those to one parse in the process), so these run in any
    worker and need no tree. The tenth pass's probe of the helper (2026-09-22) verified each by execution on a copy; the two
    it found wanting were the lock, which the helper lacked, and the key, which could not see a rewrite that kept size and
    mtime_ns. Every thread a case starts ends on every exit path in the T282 shape: join_started registered as a cleanup
    before the start loop, a bounded join in the body, and no thread alive after it; the bodies are bounded (a timed
    barrier, one read or one build)."""
    KEY = ("tests/test_thread_stop_census.py", "a planted key of ParseCacheKeyAndLock")

    def _planted_dir(self):
        d = tempfile.mkdtemp(prefix="romp-tests-census-")
        self.addCleanup(shutil.rmtree, d, True)
        return d

    @staticmethod
    def _write(path, text):
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def test_a_symlink_and_its_target_are_one_cache_entry_with_one_parse(self):
        """The key's first element is the realpath: a symlinked copy of a module (a copy of tests/thread_ends.py, a link
        beside it, and the copy reached through a symlinked directory) is one entry, parsed once, the same tree object on
        every spelling, and the counters say one parse and two hits; clear(link) drops the target's entry (one realpath),
        the next read parses again and the counter, left alone by clear, counts it."""
        d = self._planted_dir()
        target = os.path.join(d, "copy.py")
        shutil.copyfile(os.path.join(HERE, "thread_ends.py"), target)
        link = os.path.join(d, "link.py")
        os.symlink(target, link)
        os.symlink(d, os.path.join(d, "dir"))
        through_dir = os.path.join(d, "dir", "copy.py")
        before = PC.stats()
        by_link = PC.source_and_tree(link)[1]
        by_target = PC.source_and_tree(target)[1]
        by_dir = PC.source_and_tree(through_dir)[1]
        self.assertIs(by_target, by_link, "the symlink and its target are one entry")
        self.assertIs(by_dir, by_link, "the copy through a symlinked directory is the same entry")
        self.assertEqual((PC.parses_of(link), PC.parses_of(target), PC.parses_of(through_dir)), (1, 1, 1))
        after = PC.stats()
        self.assertEqual((after["parses"] - before["parses"], after["parse_hits"] - before["parse_hits"]), (1, 2))
        PC.clear(link)
        self.assertIsNot(PC.source_and_tree(target)[1], by_target, "clear(link) dropped the one entry, by realpath")
        self.assertEqual(PC.parses_of(target), 2, "the counter is left as it was and counts the second parse")
        PC.clear(target)

    def test_a_build_that_raises_is_not_memoised_is_counted_and_releases_the_lock(self):
        """derived() counts a build before it runs, so a build that raises is counted and memoised as nothing: the next
        call builds again, lands its value, and the call after hits. The raise leaves the lock released: a second thread's
        derivation of another key completes after it, joined with a bound, so a lock still held would be a failure here
        and not a hang."""
        key = self.KEY + ("a build that raises",)
        calls = []

        def build():
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("the first build fails")
            return object()
        with self.assertRaises(RuntimeError):
            PC.derived(key, build)
        self.assertEqual((len(calls), PC.builds_of(key)), (1, 1), "the raise was a build attempt, counted")
        other = self.KEY + ("another key, asked from a second thread after the raise",)
        got = []

        def derive_other():
            got.append(PC.derived(other, object))
        t = threading.Thread(target=derive_other, name="census-derive-after-raise")
        self.addCleanup(join_started, None, [t], 5)
        t.start()
        t.join(5)
        self.assertFalse(t.is_alive(), "the second thread's derivation waited on a lock the raise should have released")
        self.assertEqual(len(got), 1)
        before = PC.stats()
        a = PC.derived(key, build)
        b = PC.derived(key, build)
        self.assertIs(a, b, "the second build's value is the memo")
        self.assertEqual((len(calls), PC.builds_of(key)), (2, 2), "the raise memoised nothing: the next call built")
        self.assertEqual(PC.stats()["derived_hits"] - before["derived_hits"], 1)
        PC.clear(key, other)

    def test_two_threads_on_one_path_parse_once_and_on_one_key_build_once(self):
        """THE LOCK (the gap the tenth pass's probe found: without it two threads reading kernel/kernel.py both missed and
        both parsed, five trials of five under 3.12 and 3.10, two tree objects and the parse counter moving by two, and two
        threads on derived() built twice; a threaded reader of a product file would then have shown the counter pin a
        second parse that was no defect of the census). Two threads released together by a barrier read one path, a copy
        of kernel/kernel.py of this test's own (its parse takes seconds, so the second thread arrives while the first is
        parsing): one parse, the same tree object to both. Two threads on derived() with one key, the build sleeping
        inside the lock: one build, the same object to both. A build that reads files and derives through the cache
        re-enters the lock from its own thread (the shape of the census's own tree derivation, which ThreadStopCensus's
        setUpClass runs under the lock): shown on a planted key."""
        d = self._planted_dir()
        p = os.path.join(d, "kernel_copy.py")
        shutil.copyfile(os.path.join(ROOT, "kernel", "kernel.py"), p)
        gate = threading.Barrier(2)
        got = {}

        def read(name):
            gate.wait(5)
            got[name] = PC.source_and_tree(p)[1]
        readers = [threading.Thread(target=read, args=(n,), name="census-reader-%s" % n) for n in ("a", "b")]
        self.addCleanup(join_started, None, readers, 5)
        before = PC.stats()
        for t in readers:
            t.start()
        for t in readers:
            t.join(60)
        self.assertEqual([t.name for t in readers if t.is_alive()], [], "a reader did not finish")
        self.assertIs(got["a"], got["b"], "two threads on one path: one tree object")
        self.assertEqual(PC.parses_of(p), 1, "two threads on one path: one parse")
        self.assertEqual(PC.stats()["parses"] - before["parses"], 1)
        key = self.KEY + ("two threads",)
        built = []
        gate2 = threading.Barrier(2)

        def build():
            built.append(object())
            time.sleep(0.05)                                     # inside the lock: the second asker waits on it, builds nothing
            return built[-1]

        def ask(name):
            gate2.wait(5)
            got[name] = PC.derived(key, build)
        askers = [threading.Thread(target=ask, args=(n,), name="census-asker-%s" % n) for n in ("c", "d")]
        self.addCleanup(join_started, None, askers, 5)
        for t in askers:
            t.start()
        for t in askers:
            t.join(10)
        self.assertEqual([t.name for t in askers if t.is_alive()], [], "an asker did not finish")
        self.assertIs(got["c"], got["d"], "two threads on one key: one object")
        self.assertEqual((len(built), PC.builds_of(key)), (1, 1), "two threads on one key: one build")
        nested = self.KEY + ("a re-entrant build",)
        inner = self.KEY + ("a re-entrant build: the inner key",)
        value = PC.derived(nested, lambda: (PC.source_and_tree(p)[1], PC.derived(inner, object)))
        self.assertIs(value[0], got["a"], "the build read the cache from inside the lock: the same tree")
        self.assertEqual((PC.builds_of(nested), PC.builds_of(inner)), (1, 1))
        PC.clear(p, key, nested, inner)

    def test_the_key_sees_a_restored_mtime_and_a_rename_over_and_names_its_blind_spot(self):
        """THE KEY (size, mtime_ns, inode, ctime_ns; the ninth pass's held size and mtime_ns alone, and its docstring said
        a rewrite re-parses, which the tenth pass's probe showed false twice). A same-size rewrite whose mtime is put back
        with os.utime keeps the two old fields and moves ctime: re-parsed, the new text served. A rename-over of a file
        carrying a copied mtime keeps them too and moves the inode: re-parsed. Unchanged after both: a hit. THE BLIND
        SPOT, stated in the helper's docstring and in the counter pin's message: a rewrite that keeps the inode and the
        size within the timestamp granularity is served the old tree. On a kernel with coarse timestamps the restored
        write below can land in the tick of the file's creation, which is that blind spot exactly, so the plant repeats
        the write until ctime has moved (bounded) and asserts the fields it relies on before each read."""
        d = self._planted_dir()
        p = os.path.join(d, "planted.py")
        self._write(p, "x = 1\n")
        st0 = os.stat(p)
        first_text, first = PC.source_and_tree(p)
        self.assertEqual(first_text, "x = 1\n")
        for _attempt in range(200):                              # a coarse clock: wait out the tick the file was created in
            self._write(p, "x = 2\n")
            os.utime(p, ns=(st0.st_atime_ns, st0.st_mtime_ns))
            st1 = os.stat(p)
            if st1.st_ctime_ns != st0.st_ctime_ns:
                break
            time.sleep(0.005)
        self.assertEqual((st1.st_size, st1.st_mtime_ns, st1.st_ino), (st0.st_size, st0.st_mtime_ns, st0.st_ino),
                         "the restored rewrite kept the size, the mtime and the inode")
        self.assertNotEqual(st1.st_ctime_ns, st0.st_ctime_ns, "ctime moved: the clock ticked")
        second_text, second = PC.source_and_tree(p)
        self.assertIsNot(second, first, "a restored mtime hides nothing: ctime moved, re-parsed")
        self.assertEqual(second_text, "x = 2\n")
        side = os.path.join(d, "planted.py.new")
        self._write(side, "x = 3\n")
        os.utime(side, ns=(st1.st_atime_ns, st1.st_mtime_ns))
        os.replace(side, p)
        st2 = os.stat(p)
        self.assertEqual((st2.st_size, st2.st_mtime_ns), (st1.st_size, st1.st_mtime_ns), "the rename-over carried the copied mtime")
        self.assertNotEqual(st2.st_ino, st1.st_ino, "the rename-over moved the inode")
        third_text, third = PC.source_and_tree(p)
        self.assertIsNot(third, second, "a rename-over with a copied mtime: the inode moved, re-parsed")
        self.assertEqual(third_text, "x = 3\n")
        self.assertIs(PC.source_and_tree(p)[1], third, "unchanged after both: a hit")
        self.assertEqual(PC.parses_of(p), 3)
        PC.clear(p)


class PlantedShapes(unittest.TestCase):
    """The rules read on synthetic modules: each shape planted alone, the walk's answer for it."""
    HEAD = ("import threading\nimport time\nimport unittest\nfrom unittest import mock\n"
            "def _loop():\n    while True:\n        time.sleep(0.01)\n"
            "def _once():\n    return 1\n\nclass T(unittest.TestCase):\n")
    HEAD_KM = HEAD.replace("class T(", "km = __import__('types').ModuleType('km')   # a module alias, as km = load_source(...)\nclass T(")

    def _census(self, body, allow=None, head=None, helpers=None, product=None, extras=None):
        """The census of one planted module; `helpers` maps helper module names to sources planted beside it, `product`
        maps product file names to sources planted beside it (the defaults are none, so neither the tree's helper
        modules nor its product sources are consulted for a plant); `extras` is census's dict of informational results."""
        d = tempfile.mkdtemp(prefix="romp-tests-census-")
        self.addCleanup(shutil.rmtree, d, True)
        p = os.path.join(d, "test_planted.py")
        with open(p, "w", encoding="utf-8") as f:
            f.write((self.HEAD if head is None else head) + body)
        paths = {}
        for name, src in (helpers or {}).items():
            hp = os.path.join(d, name + ".py")
            with open(hp, "w", encoding="utf-8") as f:
                f.write(src)
            paths[name] = hp
        prod_files = []
        for name, src in (product or {}).items():
            pp = os.path.join(d, name + ".py")
            with open(pp, "w", encoding="utf-8") as f:
                f.write(src)
            prod_files.append(pp)
        rows = census([p], loops={"_producer"}, thread_classes={"KernelWorker"}, helpers=paths, product=_Product(files=prod_files), extras=extras)
        return rows, tail_only(rows, allow={} if allow is None else allow), os.path.relpath(p, ROOT)

    def _tails(self, tails):
        return sorted((s.target, w) for s, w in tails)

    def test_a_loops_stop_on_the_bodys_tail_after_an_assertion_is_named(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_x(self):\n"
            "        t = threading.Thread(target=_loop, daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "        t.join(5)\n")
        self.assertEqual(self._tails(tails), [("_loop", "T.test_x")])
        self.assertEqual((unread, bounded), ([], []))

    def test_a_loop_never_stopped_is_named_and_a_product_loop_is_read_by_name(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_x(self):\n"
            "        threading.Thread(target=_loop, daemon=True).start()\n"
            "        self.assertTrue(True)\n"
            "    def test_y(self):\n"
            "        threading.Thread(target=km._producer, daemon=True).start()\n"
            "        self.assertTrue(True)\n")
        self.assertEqual(self._tails(tails), [("_loop", "T.test_x"), ("km._producer", "T.test_y")])

    def test_a_bounded_worker_joined_on_the_tail_is_excused_by_the_bounded_rule(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_x(self):\n"
            "        out = []\n"
            "        def run():\n"
            "            out.append(_once())\n"
            "        ts = [threading.Thread(target=run) for _ in range(3)]\n"
            "        for t in ts:\n"
            "            t.start()\n"
            "        self.assertTrue(False)\n"
            "        for t in ts:\n"
            "            t.join(5)\n")
        self.assertEqual(tails, [])
        self.assertEqual([(s.target, s.kind) for s, w in bounded], [("run", "bounded")])

    def test_a_waiting_worker_is_pinned_and_its_release_as_the_next_statement_counts(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_x(self):\n"
            "        go = threading.Event()\n"
            "        def run():\n"
            "            go.wait()\n"
            "        t = threading.Thread(target=run)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "        go.set(); t.join(5)\n"
            "    def test_y(self):\n"
            "        go = threading.Event()\n"
            "        def run():\n"
            "            go.wait()\n"
            "        ts = [threading.Thread(target=run) for _ in range(2)]\n"
            "        for t in ts:\n"
            "            t.start()\n"
            "        go.set()\n"
            "        self.assertTrue(False)\n"
            "    def test_z(self):\n"
            "        gate = threading.Event()\n"
            "        t = threading.Thread(target=gate.wait, daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "        gate.set()\n")
        self.assertEqual(self._tails(tails), [("gate.wait", "T.test_z"), ("run", "T.test_x")])
        self.assertIn(("run", "waits", "stop-before-first-assertion", "T.test_y"), [(s.target, s.kind, sh, w) for s, sh, w in rows])

    def test_a_cleanup_registered_before_the_start_or_right_after_it_is_not_named(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_x(self):\n"
            "        t = threading.Thread(target=_loop, daemon=True)\n"
            "        stop = threading.Event()\n"
            "        def end():\n"
            "            stop.set()\n"
            "            t.join(5)\n"
            "        self.addCleanup(end)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_y(self):\n"
            "        srv = object()\n"
            "        threading.Thread(target=srv.serve_forever, daemon=True).start()\n"
            "        self.addCleanup(srv.shutdown)\n"
            "        self.assertTrue(False)\n"
            "    def test_z(self):\n"
            "        stop = self._go()\n"
            "        self.addCleanup(stop)\n"
            "        self.assertTrue(False)\n"
            "    def _go(self):\n"
            "        threading.Thread(target=_loop, daemon=True).start()\n"
            "        return lambda: None\n")
        self.assertEqual(tails, [])
        self.assertEqual(sorted(s for _s, s, _w in rows), ["cleanup-before-first-assertion"] * 2 + ["cleanup-before-start"])

    def test_a_cleanup_registered_after_an_assertion_or_naming_no_stop_does_not_count(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_x(self):\n"
            "        t = threading.Thread(target=_loop, daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "        self.addCleanup(t.join)\n"
            "    def test_y(self):\n"
            "        self.addCleanup(print, 'bye')\n"
            "        t = threading.Thread(target=_loop, daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "        t.join(5)\n")
        self.assertEqual(self._tails(tails), [("_loop", "T.test_x"), ("_loop", "T.test_y")])

    def test_a_cleanup_that_stops_another_thread_excuses_nothing_about_this_one(self):
        """A stop-shaped cleanup counts only for the thread it names: setUp's addCleanup(self.srv.shutdown) covers the
        server's serve_forever thread and no other start in the class; a cleanup for loop thread a says nothing about
        loop thread b, whose only stop stands behind the assertion."""
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def setUp(self):\n"
            "        self.srv = object()\n"
            "        self.addCleanup(self.srv.shutdown)\n"
            "    def test_x(self):\n"
            "        threading.Thread(target=self.srv.serve_forever, daemon=True).start()\n"
            "        self.assertTrue(False)\n"
            "    def test_y(self):\n"
            "        b = threading.Thread(target=_loop, daemon=True)\n"
            "        b.start()\n"
            "        self.assertTrue(False)\n"
            "        b.join()\n"
            "    def test_z(self):\n"
            "        a = threading.Thread(target=_loop, daemon=True)\n"
            "        b = threading.Thread(target=_loop, daemon=True)\n"
            "        self.addCleanup(a.join)\n"
            "        a.start(); b.start()\n"
            "        self.assertTrue(False)\n"
            "        b.join()\n"
            "    def test_w(self):\n"
            "        b = threading.Thread(target=_loop, daemon=True)\n"
            "        def end():\n"
            "            b.join()\n"
            "        self.addCleanup(end)\n"
            "        b.start()\n"
            "        self.assertTrue(False)\n")
        self.assertEqual(self._tails(tails), [("_loop", "T.test_y"), ("_loop", "T.test_z")])
        self.assertEqual(sorted((s.recv_shown, sh, w) for s, sh, w in rows if sh == "cleanup-before-start"),
                         [("a", "cleanup-before-start", "T.test_z"), ("b", "cleanup-before-start", "T.test_w"),
                          ("threading.Thread(target=self.srv.serve_forever, daemon=True)", "cleanup-before-start", "T.test_x")])

    def test_a_start_inside_a_try_with_a_finally_or_right_before_one_is_not_named(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_x(self):\n"
            "        t = threading.Thread(target=_loop, daemon=True)\n"
            "        try:\n"
            "            t.start()\n"
            "            self.assertTrue(False)\n"
            "        finally:\n"
            "            t.join(5)\n"
            "    def test_y(self):\n"
            "        gate = threading.Event()\n"
            "        ts = [threading.Thread(target=gate.wait) for _ in range(2)]\n"
            "        for t in ts:\n"
            "            t.start()\n"
            "        try:\n"
            "            self.assertTrue(False)\n"
            "        finally:\n"
            "            gate.set()\n")
        self.assertEqual(tails, [])
        self.assertEqual([s for _s, s, _w in rows], ["finally", "finally"])

    def test_a_thread_on_self_stopped_in_tear_down_is_not_named_and_one_only_read_there_is(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def tearDown(self):\n"
            "        t = getattr(self, 't', None)\n"
            "        if t is not None:\n"
            "            self.stop.set(); self.t.join(5)\n"
            "        for loop in self.loops:\n"
            "            loop.call_soon_threadsafe(loop.stop)\n"
            "    def test_x(self):\n"
            "        self.stop = threading.Event()\n"
            "        self.t = threading.Thread(target=_loop, daemon=True)\n"
            "        self.t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_y(self):\n"
            "        loop = object()\n"
            "        threading.Thread(target=loop.run_forever, daemon=True).start()\n"
            "        self.loops.append(loop)\n"
            "        self.assertTrue(False)\n")
        self.assertEqual(tails, [])
        self.assertEqual([s for _s, s, _w in rows], ["class-hook:tearDown", "class-hook:tearDown"])
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def tearDown(self):\n"
            "        p = getattr(self, 'producer', None)\n"
            "        if p is None or not p.is_alive():\n"
            "            self.flag.clear()\n"
            "    def test_x(self):\n"
            "        self.flag = threading.Event()\n"
            "        producer = self.producer = threading.Thread(target=_loop, daemon=True)\n"
            "        producer.start()\n"
            "        self.assertTrue(False)\n"
            "        self.flag.set(); producer.join(5)\n")
        self.assertEqual(self._tails(tails), [("_loop", "T.test_x")], "a tearDown that reads the thread but stops nothing is not a stop")

    def test_a_fakes_thread_is_owned_by_its_end_method_and_a_fake_without_one_is_named(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    pass\n\n"
            "class _Fake:\n"
            "    def __init__(self):\n"
            "        self.stop = threading.Event()\n"
            "        threading.Thread(target=self.stop.wait, daemon=True).start()\n"
            "    def close(self):\n"
            "        self.stop.set()\n\n"
            "class _Bare:\n"
            "    def __init__(self):\n"
            "        threading.Thread(target=_loop, daemon=True).start()\n")
        self.assertEqual(self._tails(tails), [("_loop", "_Bare.__init__")])
        self.assertIn("object-owned:close", [s for _s, s, _w in rows])

    def test_a_helper_start_is_classed_at_its_callers(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def _go(self):\n"
            "        t = threading.Thread(target=_loop, daemon=True)\n"
            "        t.start()\n"
            "        return t\n"
            "    def test_guarded(self):\n"
            "        self.addCleanup(self.stop.set)\n"
            "        self._go()\n"
            "        self.assertTrue(False)\n"
            "    def test_bare(self):\n"
            "        t = self._go()\n"
            "        self.assertTrue(False)\n"
            "        t.join()\n"
            "    def test_named(self):\n"
            "        t = self._go()\n"
            "        self.addCleanup(t.join)\n"
            "        self.assertTrue(False)\n")
        self.assertEqual(self._tails(tails), [("_loop", "T.test_bare"), ("_loop", "T.test_guarded")],
                         "a cleanup that names no thread of the helper's excuses nothing (self.stop is not what _loop waits on)")
        self.assertIn(("_loop", "cleanup-before-first-assertion", "T.test_named"), [(s.target, sh, w) for s, sh, w in rows])

    def test_a_stop_before_the_first_assertion_is_not_named_even_for_a_loop(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_x(self):\n"
            "        t = threading.Thread(target=_loop)\n"
            "        t.start()\n"
            "        t.join()\n"
            "        self.assertTrue(False)\n"
            "    def test_many(self):\n"
            "        ts = [threading.Thread(target=_loop) for _ in range(3)]\n"
            "        for t in ts:\n"
            "            t.start()\n"
            "        for t in ts:\n"
            "            t.join()\n"
            "        self.assertTrue(False)\n"
            "    def test_comp(self):\n"
            "        ts = [threading.Thread(target=_loop) for _ in range(3)]\n"
            "        [t.start() for t in ts]\n"
            "        [t.join() for t in ts]\n"
            "        self.assertTrue(False)\n"
            "    def test_between(self):\n"
            "        srv = object()\n"
            "        for s in (srv,):\n"
            "            threading.Thread(target=srv.serve_forever, daemon=True).start()\n"
            "        port = 1\n"
            "        saved = dict(a=1)\n"
            "        def helper():\n"
            "            return port\n"
            "        try:\n"
            "            self.assertTrue(False)\n"
            "        finally:\n"
            "            srv.shutdown()\n")
        self.assertEqual(tails, [])
        self.assertEqual(sorted(s for _s, s, _w in rows), ["finally"] + ["stop-before-first-assertion"] * 3)

    def test_a_join_in_the_starts_own_statement_counts_and_a_timed_join_alone_does_not_stop_a_loop(self):
        """The start statement's remaining nodes are read first (`t.start(), t.join()` in one statement is a stop, not
        tail-only); a TIMED join of a loop thread is a wait the loop outlives, so alone it is not the stop (test_y is
        named), while the loops' seam set beside it (a product loop), a shutdown of the object the target runs on, or a
        release of what the thread waits on is."""
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_x(self):\n"
            "        t = threading.Thread(target=_loop)\n"
            "        t.start(), t.join()\n"
            "        self.assertTrue(False)\n"
            "    def test_y(self):\n"
            "        t = threading.Thread(target=_loop)\n"
            "        t.start()\n"
            "        t.join(5)\n"
            "        self.assertTrue(False)\n"
            "    def test_z(self):\n"
            "        t = threading.Thread(target=km._producer, daemon=True)\n"
            "        t.start()\n"
            "        km._LOOPS_STOP.set(); km._producer_wake.set()\n"
            "        t.join(10)\n"
            "        self.assertTrue(False)\n"
            "    def test_w(self):\n"
            "        srv = object()\n"
            "        t = threading.Thread(target=srv.serve_forever)\n"
            "        t.start()\n"
            "        srv.shutdown(); t.join(5)\n"
            "        self.assertTrue(False)\n"
            "    def test_v(self):\n"
            "        go = threading.Event()\n"
            "        def run():\n"
            "            while not go.is_set():\n"
            "                time.sleep(0.01)\n"
            "        t = threading.Thread(target=run)\n"
            "        t.start()\n"
            "        go.set(); t.join(5)\n"
            "        self.assertTrue(False)\n", head=self.HEAD_KM)
        self.assertEqual(self._tails(tails), [("_loop", "T.test_y")])
        self.assertEqual(sorted((w, s) for _s, s, w in rows if w != "T.test_y"),
                         [(w, "stop-before-first-assertion") for w in ("T.test_v", "T.test_w", "T.test_x", "T.test_z")])

    def test_a_cleanup_registered_in_set_up_and_a_helpers_result_stored_on_self_count_for_the_class(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def setUp(self):\n"
            "        self.addCleanup(self._sweep)\n"
            "    def _sweep(self):\n"
            "        self.loop.call_soon_threadsafe(self.loop.stop)\n"
            "    def test_x(self):\n"
            "        self.loop = object()\n"
            "        def run_loop():\n"
            "            self.loop.run_forever()\n"
            "        threading.Thread(target=run_loop, daemon=True).start()\n"
            "        self.assertTrue(False)\n\n"
            "class U(unittest.TestCase):\n"
            "    def setUp(self):\n"
            "        self.bus, self.ver = _serve(), _serve()\n"
            "    def tearDown(self):\n"
            "        for srv in (self.bus, self.ver):\n"
            "            srv.shutdown()\n"
            "    def test_y(self):\n"
            "        self.assertTrue(False)\n\n"
            "def _serve():\n"
            "    srv = object()\n"
            "    threading.Thread(target=srv.serve_forever, daemon=True).start()\n"
            "    return srv\n")
        self.assertEqual(tails, [])
        self.assertEqual(sorted(s for _s, s, _w in rows), ["class-hook:tearDown", "class-hook:tearDown", "cleanup-before-start"])

    def test_a_raise_inside_a_function_the_body_defines_is_not_the_bodys_assertion(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_x(self):\n"
            "        mgr = object()\n"
            "        threading.Thread(target=mgr.serve_forever, daemon=True).start()\n"
            "        port = 1\n"
            "        def build():\n"
            "            raise RuntimeError('esbuild vanished')\n"
            "        def check():\n"
            "            self.assertEqual(1, 1)\n"
            "        try:\n"
            "            self.assertTrue(False)\n"
            "        finally:\n"
            "            mgr.shutdown()\n")
        self.assertEqual(tails, [])
        self.assertEqual([s for _s, s, _w in rows], ["finally"])

    def test_a_patcher_a_match_and_a_module_are_not_threads_and_an_unbound_receiver_is_listed(self):
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def setUp(self):\n"
            "        self._patches = [mock.patch.object(threading, 'x', 1)]\n"
            "        for p in self._patches:\n"
            "            p.start()\n"
            "    def test_x(self):\n"
            "        import re, tracemalloc\n"
            "        mock.patch.object(threading, 'y', 1).start()\n"
            "        tracemalloc.start()\n"
            "        heads = [m.start() for m in re.finditer('a', 'aa')]\n"
            "        self.assertTrue(heads[-1].start() or True)\n"
            "        ths = []\n"
            "        for _ in range(2):\n"
            "            ths.append(threading.Thread(target=_once))\n"
            "        for t in ths:\n"
            "            t.start()\n"
            "        for t in ths:\n"
            "            t.join()\n"
            "    def test_y(self, worker=None):\n"
            "        worker.start()\n"
            "    def _context(self, text, m, width=40):\n"
            "        return text[max(0, m.start() - width):m.end() + width]\n")
        self.assertEqual(tails, [])
        self.assertEqual([(s.recv_shown, w) for s, w in unread], [("worker", "T.test_y")])
        self.assertEqual([(s.target, sh) for s, sh, w in rows if sh != "unreadable"], [("_once", "stop-before-first-assertion")])

    def test_a_helper_built_thread_a_subclass_an_alias_and_a_container_element_are_read_as_threads(self):
        """Four starts the walk used to pass in silence, each named now: a thread a helper returns (a module function, a
        method of the class, a function of the body, a tuple the caller unpacks), a Thread SUBCLASS defined in the module
        or in the body (its run() gives the kind), an import alias or a local alias of threading.Thread, and a thread
        stored in a dict or list element and started from it. Also a name a comprehension bound earlier and a for
        rebinds (the binding in force at the start is the for's), and a thread bound by a conditional expression."""
        head = ("import threading\nimport time\nimport unittest\nfrom threading import Thread as Th\n"
                "def _loop():\n    while True:\n        time.sleep(0.01)\n"
                "def _once():\n    return 1\n"
                "def _make():\n    t = threading.Thread(target=_loop, daemon=True)\n    return t\n"
                "def _pair():\n    return threading.Thread(target=_loop, daemon=True), threading.Event()\n"
                "class W(threading.Thread):\n    def run(self):\n        while True:\n            time.sleep(0.01)\n"
                "class W2(W):\n    pass\n"
                "class Once(threading.Thread):\n    def run(self):\n        return _once()\n"
                "class T(unittest.TestCase):\n")
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def _mk(self):\n"
            "        return threading.Thread(target=_loop, daemon=True)\n"
            "    def test_helper(self):\n"
            "        t = _make()\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_method(self):\n"
            "        t = self._mk()\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_local(self):\n"
            "        def build():\n"
            "            return threading.Thread(target=_loop, daemon=True)\n"
            "        build().start()\n"
            "        self.assertTrue(False)\n"
            "    def test_unpack(self):\n"
            "        t, ev = _pair()\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_subclass(self):\n"
            "        w = W2(daemon=True)\n"
            "        w.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_subclass_bounded(self):\n"
            "        Once().start()\n"
            "        self.assertTrue(False)\n"
            "    def test_local_subclass(self):\n"
            "        Real = threading.Thread\n"
            "        class L(Real):\n"
            "            def run(self):\n"
            "                while True:\n"
            "                    time.sleep(0.01)\n"
            "        L().start()\n"
            "        Real(target=_loop).start()\n"
            "        self.assertTrue(False)\n"
            "    def test_alias(self):\n"
            "        Th(target=_loop, daemon=True).start()\n"
            "        self.assertTrue(False)\n"
            "    def test_dict(self):\n"
            "        self.threads = {}\n"
            "        self.threads['a'] = threading.Thread(target=_loop, daemon=True)\n"
            "        self.threads['a'].start()\n"
            "        self.assertTrue(False)\n"
            "    def test_list(self):\n"
            "        ts = []\n"
            "        ts.append(threading.Thread(target=_loop, daemon=True))\n"
            "        ts[0].start()\n"
            "        self.assertTrue(False)\n"
            "    def test_rebound(self):\n"
            "        ts = [threading.Thread(target=_loop, args=(t,)) for t in range(3)]\n"
            "        for t in ts:\n"
            "            t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_ifexp(self):\n"
            "        th = threading.Thread(target=_loop) if _once() else None\n"
            "        if th is not None:\n"
            "            th.start()\n"
            "        self.assertTrue(False)\n", head=head)
        self.assertEqual(unread, [], [(s.recv_shown, w) for s, w in unread])
        self.assertEqual(self._tails(tails), sorted([
            ("_loop", "T.test_helper"), ("_loop", "T.test_method"), ("_loop", "T.test_local"), ("_loop", "T.test_unpack"),
            ("W2.run", "T.test_subclass"), ("L.run", "T.test_local_subclass"), ("_loop", "T.test_local_subclass"),
            ("_loop", "T.test_alias"), ("_loop", "T.test_dict"), ("_loop", "T.test_list"), ("_loop", "T.test_rebound"),
            ("_loop", "T.test_ifexp")]))
        self.assertEqual([(s.target, s.kind) for s, w in bounded], [("Once.run", "bounded")])

    def test_a_call_the_walk_cannot_read_is_listed_and_a_known_non_thread_is_not(self):
        """A receiver built by a call the walk cannot classify (a parameter's, a method the class does not define, a
        product Thread subclass) is UNREADABLE and listed; a mock patcher, a regex match, tracemalloc and an object of a
        product or library module (its start() is its own) are not thread starts of the test."""
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_x(self, factory=None):\n"
            "        factory().start()\n"
            "        self.other().start()\n"
            "        km.KernelWorker().start()\n"
            "        mock.patch.object(threading, 'y', 1).start()\n"
            "        from unittest.mock import patch\n"
            "        patch.dict({}, {}).start()\n"
            "        km.SdkSession(1).start()\n"
            "        self.assertTrue(False)\n"
            "    def test_none(self):\n"
            "        def nothing():\n"
            "            return None\n"
            "        self.addCleanup(nothing)\n", head=self.HEAD_KM)
        self.assertEqual(sorted((s.recv_shown, w) for s, w in unread),
                         [("factory()", "T.test_x"), ("km.KernelWorker()", "T.test_x"), ("self.other()", "T.test_x")])
        self.assertEqual([sh for _s, sh, _w in rows if sh != "unreadable"], [])

    def test_an_allow_entry_excuses_one_site_and_a_stale_one_is_named(self):
        body = ("    def test_x(self):\n"
                "        t = threading.Thread(target=_loop, daemon=True)\n"
                "        t.start()\n"
                "        self.assertTrue(False)\n"
                "        t.join(5)\n")
        rows, (tails, unread, stale, bounded), rel = self._census(body, allow={(None, "T.test_x", "_loop"): "x"})
        self.assertEqual(self._tails(tails), [("_loop", "T.test_x")])
        tails, unread, stale, bounded = tail_only(rows, allow={(rel, "T.test_x", "_loop"): "the fake's loop ends with the process"})
        self.assertEqual((tails, stale), ([], []))
        tails, unread, stale, bounded = tail_only(rows, allow={(rel, "T.test_gone", "_loop"): "an entry for a site that is gone"})
        self.assertEqual(self._tails(tails), [("_loop", "T.test_x")])
        self.assertEqual(stale, [(rel, "T.test_gone", "_loop")])

    HEAD_FAKES = ("import threading\nimport time\nimport unittest\n"
                  "def _loop():\n    while True:\n        time.sleep(0.01)\n"
                  "def _once():\n    return 1\n"
                  "class _Srv:\n    def serve_forever(self):\n        while True:\n            time.sleep(0.01)\n"
                  "    def shutdown(self):\n        pass\n"
                  "class _Base:\n    def run(self):\n        while True:\n            time.sleep(0.01)\n"
                  "class _Fake(_Base):\n"
                  "    def __init__(self):\n        self.go = threading.Event()\n        self._srv = _Srv()\n"
                  "    def block(self):\n        self.go.wait()\n"
                  "    def step(self):\n        return _once()\n"
                  "    def serve(self):\n        self._srv.serve_forever()\n"
                  "    def relay(self):\n        self._pump()\n"
                  "    def _pump(self):\n        while True:\n            time.sleep(0.01)\n"
                  "    def __enter__(self):\n        return self\n"
                  "    def __exit__(self, *a):\n        self.go.set()\n"
                  "class _Child:\n"
                  "    def _pump(self):\n        while True:\n            time.sleep(0.01)\n"
                  "    def _drain(self):\n        self.go.wait()\n"
                  "class _Cls:\n    go = threading.Event()\n"
                  "    @classmethod\n    def block(cls):\n        cls.go.wait()\n"
                  "    @staticmethod\n    def pump(sink):\n        while True:\n            time.sleep(0.01)\n"
                  "class T(unittest.TestCase):\n"
                  "    def setUp(self):\n        self.fake = _Fake()\n")

    def test_a_method_of_a_class_of_the_module_is_read_by_its_body_however_the_thread_reaches_it(self):
        """The target is a method of a fake defined in the module, reached through an instance (`f.run`), through the
        test's own attribute (`self.fake.run`), through an inline construction (`_Fake().run`), through the class with the
        instance handed as the first of args= (`_Child._pump`), through a lambda that calls one (`lambda: f.run()`), or
        through an element of a list of fakes (`for f in fakes`, `fakes[0].run`, `self.fakes[0].run`), and the method's
        body is what the thread does: a while (in the class or a base, or in the method it delegates to through
        `self._pump()`) is a loop, an untimed wait is waits, and a tail-only stop of either is NAMED. The methods are
        called run, block, _pump, _drain, relay: no name rule reaches them (a method called `wait` was waits before by the
        BLOCKING name rule, which is why the fake's is not), so before this each was classed bounded as 'a function
        outside the test module' and the tail-only stop was excused. A method with no loop and no wait is bounded, as
        before."""
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_inst_loop(self):\n"
            "        f = _Fake()\n"
            "        t = threading.Thread(target=f.run, daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "        t.join(5)\n"
            "    def test_inst_waits(self):\n"
            "        f = _Fake()\n"
            "        t = threading.Thread(target=f.block, daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "        f.go.set(); t.join(5)\n"
            "    def test_class_loop(self):\n"
            "        child = _Child()\n"
            "        t = threading.Thread(target=_Child._pump, args=(child,), daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_class_waits(self):\n"
            "        child = _Child()\n"
            "        t = threading.Thread(target=_Child._drain, args=(child,), daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_inline_loop(self):\n"
            "        threading.Thread(target=_Fake().run, daemon=True).start()\n"
            "        self.assertTrue(False)\n"
            "    def test_inline_waits(self):\n"
            "        threading.Thread(target=_Fake().block, daemon=True).start()\n"
            "        self.assertTrue(False)\n"
            "    def test_self_loop(self):\n"
            "        t = threading.Thread(target=self.fake.run, daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_self_waits(self):\n"
            "        t = threading.Thread(target=self.fake.block, daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_lambda_loop(self):\n"
            "        f = _Fake()\n"
            "        t = threading.Thread(target=lambda: f.run(), daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_lambda_waits(self):\n"
            "        f = _Fake()\n"
            "        t = threading.Thread(target=lambda: f.block(), daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_for_fakes(self):\n"
            "        fakes = [_Fake(), _Fake()]\n"
            "        for f in fakes:\n"
            "            threading.Thread(target=f.run, daemon=True).start()\n"
            "        self.assertTrue(False)\n"
            "    def test_indexed(self):\n"
            "        fakes = [_Fake()]\n"
            "        t = threading.Thread(target=fakes[0].run, daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_self_indexed(self):\n"
            "        self.fakes = [_Fake()]\n"
            "        t = threading.Thread(target=self.fakes[0].run, daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_relay(self):\n"
            "        f = _Fake()\n"
            "        t = threading.Thread(target=f.relay, daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_with_loop(self):\n"
            "        with _Fake() as f:\n"
            "            t = threading.Thread(target=f.run, daemon=True)\n"
            "            t.start()\n"
            "            self.assertTrue(False)\n"
            "    def test_bounded(self):\n"
            "        f = _Fake()\n"
            "        t = threading.Thread(target=f.step, daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "        t.join()\n", head=self.HEAD_FAKES)
        self.assertEqual(unread, [], [(s.recv_shown, w) for s, w in unread])
        self.assertEqual(sorted((s.target, s.kind, w) for s, w in tails), sorted([
            ("f.run", "loop", "T.test_inst_loop"), ("f.block", "waits", "T.test_inst_waits"),
            ("_Child._pump", "loop", "T.test_class_loop"), ("_Child._drain", "waits", "T.test_class_waits"),
            ("_Fake().run", "loop", "T.test_inline_loop"), ("_Fake().block", "waits", "T.test_inline_waits"),
            ("self.fake.run", "loop", "T.test_self_loop"), ("self.fake.block", "waits", "T.test_self_waits"),
            ("lambda: f.run()", "loop", "T.test_lambda_loop"), ("lambda: f.block()", "waits", "T.test_lambda_waits"),
            ("f.run", "loop", "T.test_for_fakes"), ("fakes[0].run", "loop", "T.test_indexed"),
            ("self.fakes[0].run", "loop", "T.test_self_indexed"), ("f.relay", "loop", "T.test_relay"),
            ("f.run", "loop", "T.test_with_loop")]))
        self.assertEqual([(s.target, s.kind) for s, w in bounded], [("f.step", "bounded")])
        self.assertEqual({s.why for s, w in tails if s.target == "f.relay"}, {"calls self._pump, a while loop"},
                         "the delegation is read in the fake's own unit: self._pump is _Fake._pump, not the test's")

    def test_a_fakes_stop_is_read_as_the_test_writes_it(self):
        """The fake's `self.go` in its method is the test's `f.go` (or `self.fake.go`): a release of it before the first
        assertion, a cleanup naming it or the fake, a tearDown that sets it, or an end method of the fake called before
        the assertion, is this thread's stop; a lambda's call of the method is read one level down for the same names.
        A fake's attributes are that fake's alone: a cleanup that releases ANOTHER fake's `g.go`, or shuts down another
        fake's `g._srv`, excuses nothing about f's thread, whether the target is `f.block`, `lambda: f.block()` (the
        owner is read through the lambda) or `f.serve` (whose `self._srv.serve_forever()` runs on f._srv); a cleanup
        naming f's own `_srv` is its stop."""
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def tearDown(self):\n"
            "        self.fake.go.set()\n"
            "    def test_release(self):\n"
            "        f = _Fake()\n"
            "        t = threading.Thread(target=f.block, daemon=True)\n"
            "        t.start()\n"
            "        f.go.set()\n"
            "        self.assertTrue(False)\n"
            "    def test_lambda_release(self):\n"
            "        f = _Fake()\n"
            "        t = threading.Thread(target=lambda: f.block(), daemon=True)\n"
            "        t.start()\n"
            "        f.go.set()\n"
            "        self.assertTrue(False)\n"
            "    def test_cleanup(self):\n"
            "        f = _Fake()\n"
            "        self.addCleanup(f.go.set)\n"
            "        t = threading.Thread(target=f.block, daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_hook(self):\n"
            "        t = threading.Thread(target=self.fake.block, daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_other_fake(self):\n"
            "        f, g = _Fake(), _Fake()\n"
            "        self.addCleanup(g.go.set)\n"
            "        t = threading.Thread(target=f.block, daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_other_fake_lambda(self):\n"
            "        f, g = _Fake(), _Fake()\n"
            "        self.addCleanup(g.go.set)\n"
            "        t = threading.Thread(target=lambda: f.block(), daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_other_fakes_server(self):\n"
            "        f, g = _Fake(), _Fake()\n"
            "        self.addCleanup(g._srv.shutdown)\n"
            "        t = threading.Thread(target=f.serve, daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_own_server(self):\n"
            "        f = _Fake()\n"
            "        self.addCleanup(f._srv.shutdown)\n"
            "        t = threading.Thread(target=f.serve, daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n", head=self.HEAD_FAKES)
        named = ("T.test_other_fake", "T.test_other_fake_lambda", "T.test_other_fakes_server")
        self.assertEqual(self._tails(tails), [("f.block", "T.test_other_fake"), ("f.serve", "T.test_other_fakes_server"),
                                              ("lambda: f.block()", "T.test_other_fake_lambda")],
                         "a cleanup that releases or shuts down another fake excuses nothing")
        self.assertEqual(sorted((w, s) for _s, s, w in rows if w not in named),
                         [("T.test_cleanup", "cleanup-before-start"), ("T.test_hook", "class-hook:tearDown"),
                          ("T.test_lambda_release", "stop-before-first-assertion"), ("T.test_own_server", "cleanup-before-start"),
                          ("T.test_release", "stop-before-first-assertion")])

    def test_a_classmethod_or_a_staticmethod_of_a_fake_is_read_through_the_class_or_an_attribute(self):
        """A @classmethod reached through the class (`_Cls.block`) has the class for its `cls`: its `cls.go` is `_Cls.go`,
        so a set of that before the first assertion is the stop and a tail-only one is NAMED (waits); reached through an
        attribute the class is stored on (`self.clsfake.block`, `cls.clsfake = _Cls` in setUpClass), `cls.go` is
        `self.clsfake.go`, and a tearDownClass that sets it is the class hook. A @staticmethod reached through the class
        has no instance: the first of args= is not one, and its body's while is a loop, NAMED when tail-only."""
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    @classmethod\n"
            "    def setUpClass(cls):\n"
            "        cls.clsfake = _Cls\n"
            "    @classmethod\n"
            "    def tearDownClass(cls):\n"
            "        cls.clsfake.go.set()\n"
            "    def test_cls_hook(self):\n"
            "        t = threading.Thread(target=self.clsfake.block, daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_cls_release(self):\n"
            "        t = threading.Thread(target=_Cls.block, daemon=True)\n"
            "        t.start()\n"
            "        _Cls.go.set()\n"
            "        self.assertTrue(False)\n"
            "    def test_cls_named(self):\n"
            "        t = threading.Thread(target=_Cls.block, daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_static(self):\n"
            "        sink = []\n"
            "        t = threading.Thread(target=_Cls.pump, args=(sink,), daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n", head=self.HEAD_FAKES)
        self.assertEqual(unread, [], [(s.recv_shown, w) for s, w in unread])
        self.assertEqual(sorted((s.target, s.kind, w) for s, w in tails),
                         [("_Cls.block", "waits", "T.test_cls_named"), ("_Cls.pump", "loop", "T.test_static")])
        self.assertEqual(sorted((w, sh) for _s, sh, w in rows if w in ("T.test_cls_hook", "T.test_cls_release")),
                         [("T.test_cls_hook", "class-hook:tearDownClass"), ("T.test_cls_release", "stop-before-first-assertion")])

    def test_a_method_whose_body_the_walk_sees_no_loop_or_wait_in_keeps_its_name_rule(self):
        """A class of the module whose serve_forever runs an asyncio loop (asyncio.run(self._main())) or whose get blocks
        on a queue with a timeout (self.q.get(True, 30); block=True alone is an untimed spelling since romp-manager's
        ruling of 2026-09-22 and the body road reads it): the body reads bounded, so the NAME rules apply as they did
        before the body road existed: serve_forever is a loop, get is a wait, and a tail-only stop is NAMED; a shutdown
        of the server before the first assertion is the stop. A wait that blocks on a future (self.fut.result()) is read
        by the BODY road since round 2 of PR 891's review (result joined BLOCKING, 2026-09-22): the untimed .result() is
        the wait, and because every wait of the body is on the fake's own attributes, the receiver `w` is still what a
        set or release must name (w.release() sets the future). The body road takes precedence only when it finds a loop
        or an untimed wait."""
        head = self.HEAD.replace("import unittest\n", "import unittest\nimport asyncio\nimport queue\nimport concurrent.futures\n") \
            .replace("class T(", "class _Srv2:\n    def serve_forever(self):\n        asyncio.run(self._main())\n"
                                 "    async def _main(self):\n        return 1\n    def shutdown(self):\n        pass\n"
                                 "class _W:\n    def __init__(self):\n        self.fut = concurrent.futures.Future(); self.q = queue.Queue()\n"
                                 "    def wait(self):\n        return self.fut.result()\n"
                                 "    def get(self):\n        return self.q.get(True, 30)\n"
                                 "    def release(self):\n        self.fut.set_result(1)\n"
                                 "class T(")
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_serve_named(self):\n"
            "        s = _Srv2()\n"
            "        t = threading.Thread(target=s.serve_forever, daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "        s.shutdown()\n"
            "    def test_wait_named(self):\n"
            "        w = _W()\n"
            "        t = threading.Thread(target=w.wait, daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_get_named(self):\n"
            "        w = _W()\n"
            "        t = threading.Thread(target=w.get, daemon=True)\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_lambda_serve_named(self):\n"
            "        s = _Srv2()\n"
            "        threading.Thread(target=lambda: s.serve_forever(), daemon=True).start()\n"
            "        self.assertTrue(False)\n"
            "    def test_shutdown_before(self):\n"
            "        s = _Srv2()\n"
            "        t = threading.Thread(target=s.serve_forever, daemon=True)\n"
            "        t.start()\n"
            "        s.shutdown()\n"
            "        self.assertTrue(False)\n"
            "    def test_wait_released(self):\n"
            "        w = _W()\n"
            "        t = threading.Thread(target=w.wait, daemon=True)\n"
            "        t.start()\n"
            "        w.release()\n"
            "        self.assertTrue(False)\n", head=head)
        self.assertEqual(unread, [], [(s.recv_shown, w) for s, w in unread])
        self.assertEqual(sorted((s.target, s.kind, s.why, w) for s, w in tails), sorted([
            ("s.serve_forever", "loop", "serve_forever", "T.test_serve_named"),
            ("w.wait", "waits", "an untimed .result()", "T.test_wait_named"),
            ("w.get", "waits", "the target is an untimed .get", "T.test_get_named"),
            ("lambda: s.serve_forever()", "loop", "serve_forever", "T.test_lambda_serve_named")]))
        self.assertEqual(bounded, [])
        self.assertEqual(sorted((w, sh) for _s, sh, w in rows if w in ("T.test_shutdown_before", "T.test_wait_released")),
                         [("T.test_shutdown_before", "stop-before-first-assertion"), ("T.test_wait_released", "stop-before-first-assertion")])

    def test_a_stop_word_matches_a_word_of_the_name_and_not_a_substring(self):
        """`pending`, `render`, `send`, `append`, `calendar` say nothing about stopping (they held `end` as a substring):
        a cleanup of such a name before a loop start is not its stop, and the tail-only stop is NAMED. `endWorker` and
        `stop_all` say stop by a word of theirs, and count."""
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_pending(self):\n"
            "        worker = threading.Thread(target=_loop, daemon=True)\n"
            "        self.addCleanup(pending, worker)\n"
            "        worker.start()\n"
            "        self.assertTrue(False)\n"
            "        worker.join(5)\n"
            "    def test_words(self):\n"
            "        worker = threading.Thread(target=_loop, daemon=True)\n"
            "        self.addCleanup(render, worker)\n"
            "        self.addCleanup(send, worker)\n"
            "        self.addCleanup(calendar, worker)\n"
            "        worker.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_end_worker(self):\n"
            "        worker = threading.Thread(target=_loop, daemon=True)\n"
            "        self.addCleanup(endWorker, worker)\n"
            "        worker.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_stop_all(self):\n"
            "        worker = threading.Thread(target=_loop, daemon=True)\n"
            "        self.addCleanup(stop_all, worker)\n"
            "        worker.start()\n"
            "        self.assertTrue(False)\n",
            head=self.HEAD.replace("def _once", "def pending(w):\n    return w.is_alive()\ndef _once"))
        self.assertEqual(self._tails(tails), [("_loop", "T.test_pending"), ("_loop", "T.test_words")])
        self.assertEqual(sorted((w, s) for _s, s, w in rows if s != "tail-only"),
                         [("T.test_end_worker", "cleanup-before-start"), ("T.test_stop_all", "cleanup-before-start")])
        self.assertEqual([_says_stop(n) for n in ("pending", "render", "send", "append", "calendar", "closer", "joined")], [False] * 7)
        self.assertEqual([_says_stop(n) for n in ("endWorker", "stop_all", "_close_srv", "end", "_LOOPS_STOP", "shutdownAll")], [True] * 6)

    def test_a_def_in_the_body_binds_its_own_names_and_a_nonlocal_binds_the_bodys(self):
        """A nested def's `t = Thread(target=_once)` is its own `t`: the body's later `t.start()` reads the body's
        `t = Thread(target=_loop)`, a loop, and its tail-only stop is NAMED (the nested binding used to rebind the body's).
        The nested start reads its own binding (bounded, joined at once). A nested def that declares `nonlocal t` binds
        the NEAREST enclosing function's `t` that exists: the body's when the def between binds no t of its own (test_w:
        two defs deep, the start used to resolve to `t = None` and produce NO row), the middle def's when it does
        (test_v: the body's t stays the bounded one)."""
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_x(self):\n"
            "        t = threading.Thread(target=_loop, daemon=True)\n"
            "        def helper():\n"
            "            t = threading.Thread(target=_once)\n"
            "            t.start()\n"
            "            t.join()\n"
            "        helper()\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "        t.join(5)\n"
            "    def test_y(self):\n"
            "        t = None\n"
            "        def make():\n"
            "            nonlocal t\n"
            "            t = threading.Thread(target=_loop, daemon=True)\n"
            "        make()\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_z(self):\n"
            "        t = threading.Thread(target=_once)\n"
            "        def helper():\n"
            "            t.start()\n"
            "            t.join()\n"
            "        helper()\n"
            "        self.assertTrue(False)\n"
            "    def test_w(self):\n"
            "        t = None\n"
            "        def outer():\n"
            "            def inner():\n"
            "                nonlocal t\n"
            "                t = threading.Thread(target=_loop, daemon=True)\n"
            "            inner()\n"
            "        outer()\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_v(self):\n"
            "        t = threading.Thread(target=_once)\n"
            "        def outer():\n"
            "            t = None\n"
            "            def inner():\n"
            "                nonlocal t\n"
            "                t = threading.Thread(target=_loop, daemon=True)\n"
            "            inner()\n"
            "            return t\n"
            "        outer()\n"
            "        t.start(); t.join()\n"
            "        self.assertTrue(False)\n")
        self.assertEqual(self._tails(tails), [("_loop", "T.test_w"), ("_loop", "T.test_x"), ("_loop", "T.test_y")])
        self.assertEqual(sorted((s.target, s.kind, sh, w) for s, sh, w in rows),
                         sorted([("_loop", "loop", "tail-only", "T.test_x"), ("_once", "bounded", "stop-before-first-assertion", "T.test_x"),
                                 ("_loop", "loop", "tail-only", "T.test_y"), ("_once", "bounded", "stop-before-first-assertion", "T.test_z"),
                                 ("_loop", "loop", "tail-only", "T.test_w"), ("_once", "bounded", "stop-before-first-assertion", "T.test_v")]),
                         "the nested start reads its own binding; a closure over the body's binding reads the body's")

    def test_a_thread_a_helper_module_under_tests_returns_is_read_on_both_import_roads(self):
        """A function of a helper module under tests/ that returns a Thread is read as a module function's return is,
        through the imported module (`helper_mod.spawn()`), through the imported name (`spawn()`) and through the dotted
        spelling of a package import (`import tests.helper_mod`; `tests.helper_mod.spawn()`): the target's kind is read
        in the helper's own module, and a tail-only stop is NAMED. A helper function that returns no thread is no start.
        Before this a call through an imported module name was every module's object and passed in silence (the dotted
        spelling still was, after the first two roads were read)."""
        helper = ("import threading\nimport time\n"
                  "def _loop():\n    while True:\n        time.sleep(0.01)\n"
                  "def spawn():\n    return threading.Thread(target=_loop, daemon=True)\n"
                  "def nothing():\n    return 1\n")
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_module_road(self):\n"
            "        helper_mod.spawn().start()\n"
            "        self.assertTrue(False)\n"
            "    def test_name_road(self):\n"
            "        t = spawn()\n"
            "        t.start()\n"
            "        self.assertTrue(False)\n"
            "    def test_no_thread(self):\n"
            "        helper_mod.nothing().start()\n"
            "        nothing().start()\n"
            "        self.assertTrue(False)\n"
            "    def test_dotted_road(self):\n"
            "        tests.helper_mod.spawn().start()\n"
            "        self.assertTrue(False)\n",
            head=self.HEAD.replace("import unittest\n", "import unittest\nimport helper_mod\nimport tests.helper_mod\nfrom helper_mod import spawn, nothing\n"),
            helpers={"helper_mod": helper})
        self.assertEqual(unread, [], [(s.recv_shown, w) for s, w in unread])
        self.assertEqual(sorted((s.target, s.kind, w) for s, w in tails),
                         [("_loop", "loop", "T.test_dotted_road"), ("_loop", "loop", "T.test_module_road"), ("_loop", "loop", "T.test_name_road")])
        self.assertEqual(len(rows), 3, [(s.recv_shown, sh, w) for s, sh, w in rows])
        d = os.path.dirname(_p)
        self.assertEqual(helper_thread_factories(helpers={"helper_mod": os.path.join(ROOT, d, "helper_mod.py")}), [("helper_mod", "spawn")])

    def test_a_while_true_search_over_data_reached_through_a_fakes_method_is_a_loop_the_allow_list_excuses(self):
        """The walk cannot tell a search over local data (`while True: kk = pre + '#%d' % n; if kk not in items: break;
        n += 1`, tests/test_view_deltas.py's _py_maps, reached through _Stream.push and a lambda) from a spin on a flag the
        test flips (`while True: if flag[0] and n > 0: break`; `d2 = d; if d2['go']: break`): every such while is a loop,
        a timed join alone is not its stop, and the site is NAMED unless an ALLOW entry excuses it by name with its
        reason (the tree carried one for that _py_maps site until the search became a bounded for on 2026-09-22; ALLOW is
        empty by construction now and the mechanism is exercised here, on this plant). A rule that read the search as
        bounded by its shape (no call in the body, the break guarded by a name the body rebinds) excused the two spins
        too, and was dropped."""
        head = self.HEAD.replace("class T(", "def _maps(msg):\n    items, order = {}, []\n"
                                 "    def put(kk, val, pre=''):\n        if kk is None or kk in items:\n            n = len(order)\n"
                                 "            while True:\n                kk = pre + '#%d' % n\n                if kk not in items:\n"
                                 "                    break\n                n += 1\n        items[kk] = val; order.append(kk)\n"
                                 "    put(None, msg)\n    return items\n"
                                 "class _Stream:\n    def push(self, payload):\n        return _maps(payload)\n"
                                 "class T(")
        body = ("    def test_via_method(self):\n"
                "        st = _Stream()\n"
                "        done = []\n"
                "        t = threading.Thread(target=lambda: (st.push(1), done.append(st.push(2))), daemon=True); t.start(); t.join(5)\n"
                "        self.assertFalse(t.is_alive())\n"
                "    def test_flag_and_counter(self):\n"
                "        flag = [False]\n"
                "        def spin():\n"
                "            n = 0\n"
                "            while True:\n"
                "                n += 1\n"
                "                if flag[0] and n > 0:\n"
                "                    break\n"
                "        t = threading.Thread(target=spin)\n"
                "        t.start()\n"
                "        self.assertTrue(False)\n"
                "    def test_dict_alias(self):\n"
                "        d = {'go': False}\n"
                "        def spin():\n"
                "            while True:\n"
                "                d2 = d\n"
                "                if d2['go']:\n"
                "                    break\n"
                "        t = threading.Thread(target=spin)\n"
                "        t.start()\n"
                "        self.assertTrue(False)\n")
        rows, (tails, unread, stale, bounded), rel = self._census(body, head=head)
        lam = "lambda: (st.push(1), done.append(st.push(2)))"
        self.assertEqual(sorted((s.target, s.kind, w) for s, w in tails),
                         [(lam, "loop", "T.test_via_method"), ("spin", "loop", "T.test_dict_alias"), ("spin", "loop", "T.test_flag_and_counter")])
        self.assertEqual(bounded, [])
        tails, unread, stale, bounded = tail_only(rows, allow={(rel, "T.test_via_method", lam): "a search over local data"})
        self.assertEqual((sorted((s.target, w) for s, w in tails), stale),
                         ([("spin", "T.test_dict_alias"), ("spin", "T.test_flag_and_counter")], []))

    def test_a_bound_start_handed_on_as_a_value_is_a_start_classed_at_the_handing_statement(self):
        """tests/test_postal_token.py:435-436's shape (romp-manager's ruling, 2026-09-22): a Thread whose bound `.start` is
        HANDED to a helper that calls it, as a keyword (`before=t.start`), as a positional, in a list, as an assigned value.
        Each is a start row classed at the handing statement: kind from the target as usual, shape from the walk forward
        from that statement, whose own text is read first (the `after=lambda: t.join(timeout=5)` beside a bounded worker's
        start is its join). A receiver the walk cannot resolve (a parameter's `.start`) is listed unreadable, as a call's
        would be; a `.start` in an operand position (a range's) is not a start."""
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def _run(self, *steps, before=None, after=None):\n"
            "        pass\n"
            "    def test_kw(self):\n"
            "        t = threading.Thread(target=_loop)\n"
            "        self._run(before=t.start)\n"
            "        self.assertTrue(False)\n"
            "        t.join()\n"
            "    def test_kw_join_beside(self):\n"
            "        t = threading.Thread(target=_once)\n"
            "        self._run(before=t.start, after=lambda: t.join(timeout=5))\n"
            "        self.assertTrue(False)\n"
            "    def test_pos(self):\n"
            "        t = threading.Thread(target=_loop)\n"
            "        self._run(t.start)\n"
            "        self.assertTrue(False)\n"
            "    def test_list(self):\n"
            "        t = threading.Thread(target=_loop)\n"
            "        steps = [t.start, t.join]\n"
            "        self.assertTrue(False)\n"
            "    def test_assigned(self):\n"
            "        t = threading.Thread(target=_loop)\n"
            "        go = t.start\n"
            "        go()\n"
            "        t.join()\n"
            "        self.assertTrue(False)\n"
            "    def test_param(self, worker=None):\n"
            "        self._run(before=worker.start)\n"
            "        self.assertTrue(False)\n"
            "    def test_operand(self):\n"
            "        r = range(3)\n"
            "        self.assertEqual(r.start + 0, 0)\n"
            "        self.assertEqual(max(r.start, 0), 0)\n"
            "    def test_ifexp(self, fast=True):\n"
            "        t = threading.Thread(target=_loop)\n"
            "        self._run(before=t.start if fast else None)\n"
            "        self.assertTrue(False)\n"
            "    def test_boolop(self, hook=None):\n"
            "        t = threading.Thread(target=_loop)\n"
            "        self._run(before=hook or t.start)\n"
            "        self.assertTrue(False)\n"
            "    def test_default(self):\n"
            "        t = threading.Thread(target=_loop)\n"
            "        def go(cb=t.start):\n"
            "            cb()\n"
            "        go()\n"
            "        self.assertTrue(False)\n"
            "    def test_starred(self):\n"
            "        t = threading.Thread(target=_loop)\n"
            "        self._run(*[t.start])\n"
            "        self.assertTrue(False)\n")
        by = {w: (s.target, s.kind, sh, s.handed) for s, sh, w in rows}
        for name in ("test_ifexp", "test_boolop", "test_default", "test_starred"):
            self.assertEqual(by["T." + name], ("_loop", "loop", "tail-only", True), name)
        self.assertEqual(by["T.test_kw"], ("_loop", "loop", "tail-only", True))
        self.assertEqual(by["T.test_kw_join_beside"], ("_once", "bounded", "stop-before-first-assertion", True))
        self.assertEqual(by["T.test_pos"], ("_loop", "loop", "tail-only", True))
        self.assertEqual(by["T.test_list"], ("_loop", "loop", "tail-only", True))
        self.assertEqual(by["T.test_assigned"], ("_loop", "loop", "stop-before-first-assertion", True))
        self.assertNotIn("T.test_operand", by)
        self.assertEqual(self._tails(tails), [("_loop", "T.test_boolop"), ("_loop", "T.test_default"), ("_loop", "T.test_ifexp"),
                                              ("_loop", "T.test_kw"), ("_loop", "T.test_list"), ("_loop", "T.test_pos"), ("_loop", "T.test_starred")])
        self.assertEqual([(s.recv_shown, w, s.handed) for s, w in unread], [("worker", "T.test_param", True)], "a range's start as an argument is no start")
        self.assertTrue(unread[0][0].describe().endswith("T.test_param hands worker.start on"), unread[0][0].describe())
        self.assertTrue(any(s.describe().endswith("via t.start handed on") for s, _sh, _w in rows if s.is_thread))

    def test_the_untimed_spellings_of_a_blocking_call_are_read_as_untimed(self):
        """romp-manager's ruling (2026-09-22): a blocking call whose only arguments are the spellings Python reads as
        untimed is UNTIMED wherever a BLOCKING call is judged: q.get(True), q.get(block=True), ev.wait(None),
        ev.wait(timeout=None), lk.acquire(blocking=True), t.join(None) in a body (each waits, pinned), and the same through
        the construction's args= / kwargs= for a target that is the method itself. A timeout in the body is bounded (the
        excused side: the same tail-only join is excused by the bounded rule); a timeout handed to a method target falls to
        the stdlib table, which has no rule for a timed wait (unreadable)."""
        head = self.HEAD.replace("import unittest\n", "import unittest\nimport queue\n")
        untimed = {"get_true": "q.get(True)", "get_block": "q.get(block=True)", "wait_none": "ev.wait(None)",
                   "wait_kw": "ev.wait(timeout=None)", "acq_blocking": "lk.acquire(blocking=True)", "join_none": "t0.join(None)",
                   "get_one": "q.get(1)", "get_block_one": "q.get(block=1)", "acq_one": "lk.acquire(1)",
                   "acq_forever": "lk.acquire(timeout=-1)", "acq_both": "lk.acquire(True, -1)", "wait_unread": "ev.wait(**kw)", "get_star": "q.get(*a)"}
        timed = {"get_timed": "q.get(True, 1)", "wait_timed": "ev.wait(1)", "acq_timed": "lk.acquire(True, 2)", "join_timed": "t0.join(timeout=1)",
                 "get_zero": "q.get(0)", "wait_name": "ev.wait(deadline)"}
        body = "".join("    def test_%s(self):\n        q, ev, lk = queue.Queue(), threading.Event(), threading.Lock()\n"
                       "        t0 = threading.Thread(target=_once); kw = {}; a = (); deadline = 1\n"
                       "        def run():\n            %s\n"
                       "        t = threading.Thread(target=run)\n        t.start()\n        self.assertTrue(False)\n        t.join(5)\n"
                       % (name, call) for name, call in list(untimed.items()) + list(timed.items()))
        body += ("    def test_ctor_args_none(self):\n        ev = threading.Event()\n"
                 "        t = threading.Thread(target=ev.wait, args=(None,))\n        t.start()\n        self.assertTrue(False)\n"
                 "    def test_ctor_kwargs_block(self):\n        q = queue.Queue()\n"
                 "        t = threading.Thread(target=q.get, kwargs={'block': True})\n        t.start()\n        self.assertTrue(False)\n"
                 "    def test_ctor_args_timed(self):\n        ev = threading.Event()\n"
                 "        t = threading.Thread(target=ev.wait, args=(1,))\n        t.start()\n        self.assertTrue(False)\n")
        rows, (tails, unread, stale, bounded), _p = self._census(body, head=head)
        by = {w.split(".")[1]: (s.kind, s.why, sh) for s, sh, w in rows}
        for name, call in untimed.items():
            self.assertEqual(by["test_" + name], ("waits", "an untimed .%s" % call.split(".", 1)[1], "tail-only"), name)
        for name in timed:
            self.assertEqual(by["test_" + name], ("bounded", "no loop, no untimed wait", "tail-only"), name)
        self.assertEqual(sorted(w.split(".")[1] for s, w in bounded), sorted("test_" + n for n in timed))
        self.assertEqual(by["test_ctor_args_none"][:2], ("waits", "the target is an untimed .wait"))
        self.assertEqual(by["test_ctor_kwargs_block"][:2], ("waits", "the target is an untimed .get"))
        self.assertEqual(by["test_ctor_args_timed"][0], KIND_UNREAD)
        self.assertIn("Event", by["test_ctor_args_timed"][1])
        self.assertEqual(sorted(w.split(".")[1] for s, w in tails), sorted(["test_" + n for n in untimed] + ["test_ctor_args_none", "test_ctor_kwargs_block"]))
        self.assertEqual([w.split(".")[1] for s, w in unread], ["test_ctor_args_timed"])

    def test_a_sleep_a_server_close_and_a_timer_are_bounded_only_under_their_conditions_read_at_the_call(self):
        """STDLIB_CONDITIONED (romp-manager's ruling, 2026-09-22). time.sleep as a target: bounded for a literal at or under
        BOUND_S in args= (through the module alias and the bare import), unreadable for 3600, for a name, for no args=.
        server_close: bounded on a socketserver.TCPServer, an http.server.ThreadingHTTPServer and a bare-imported HTTPServer
        (no handler threads to join); unreadable on a ThreadingTCPServer (ThreadingMixIn.server_close joins live handlers).
        Timer: bounded for a literal interval at or under the bound (positional or interval=), unreadable for 3600 or a
        name whatever its function; its cancel before the first assertion is still its stop; a Timer whose function loops
        is a loop still. Every bounded reason passes bounded_reason_is_read."""
        head = self.HEAD.replace("import unittest\n", "import unittest\nimport socketserver\nimport http.server\nfrom http.server import HTTPServer\nfrom time import sleep\n")
        body = ("    def test_sleep_ok(self):\n        t = threading.Thread(target=time.sleep, args=(3,)); t.start()\n        self.assertTrue(False)\n"
                "    def test_sleep_bare(self):\n        t = threading.Thread(target=sleep, args=(0.5,)); t.start()\n        self.assertTrue(False)\n"
                "    def test_sleep_long(self):\n        t = threading.Thread(target=time.sleep, args=(3600,)); t.start()\n        self.assertTrue(False)\n"
                "    def test_sleep_name(self):\n        s = 1\n        t = threading.Thread(target=time.sleep, args=(s,)); t.start()\n        self.assertTrue(False)\n"
                "    def test_sleep_noargs(self):\n        t = threading.Thread(target=time.sleep); t.start()\n        self.assertTrue(False)\n"
                "    def test_close_tcp(self):\n        srv = socketserver.TCPServer(('127.0.0.1', 0), None)\n        t = threading.Thread(target=srv.server_close); t.start()\n        self.assertTrue(False)\n"
                "    def test_close_http(self):\n        srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), None)\n        t = threading.Thread(target=srv.server_close); t.start()\n        self.assertTrue(False)\n"
                "    def test_close_bare(self):\n        srv = HTTPServer(('127.0.0.1', 0), None)\n        t = threading.Thread(target=srv.server_close); t.start()\n        self.assertTrue(False)\n"
                "    def test_close_threading(self):\n        srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), None)\n        t = threading.Thread(target=srv.server_close); t.start()\n        self.assertTrue(False)\n"
                "    def test_timer_ok(self):\n        ev = threading.Event()\n        t = threading.Timer(1, ev.set); t.start()\n        self.assertTrue(False)\n"
                "    def test_timer_kw(self):\n        ev = threading.Event()\n        t = threading.Timer(interval=0.5, function=ev.set); t.start()\n        self.assertTrue(False)\n"
                "    def test_timer_long(self):\n        ev = threading.Event()\n        t = threading.Timer(3600, ev.set); t.start()\n        self.assertTrue(False)\n"
                "    def test_timer_name(self):\n        ev = threading.Event(); n = 1\n        t = threading.Timer(n, ev.set); t.start()\n        self.assertTrue(False)\n"
                "    def test_timer_cancelled(self):\n        ev = threading.Event()\n        t = threading.Timer(3600, ev.set); t.start(); t.cancel()\n        self.assertTrue(False)\n"
                "    def test_timer_loop(self):\n        t = threading.Timer(0.1, _loop); t.start()\n        self.assertTrue(False)\n"
                "    def test_timer_local_alias_long(self):\n        ev = threading.Event(); Tm = threading.Timer\n        t = Tm(interval=3600, function=ev.set); t.start()\n        self.assertTrue(False)\n"
                "    def test_timer_local_alias_ok(self):\n        ev = threading.Event(); Tm = threading.Timer\n        t = Tm(1, ev.set); t.start()\n        self.assertTrue(False)\n"
                "    def test_timer_import_alias_long(self):\n        ev = threading.Event()\n        t = Tim(3600, ev.set); t.start()\n        self.assertTrue(False)\n"
                "    def test_timer_subclass_long(self):\n        ev = threading.Event()\n        class T2(threading.Timer):\n            pass\n"
                "        t = T2(3600, ev.set); t.start()\n        self.assertTrue(False)\n"
                "    def test_timer_global_alias_long(self):\n        ev = threading.Event()\n        t = TimerG(3600, ev.set); t.start()\n        self.assertTrue(False)\n")
        head = head.replace("from time import sleep\n", "from time import sleep\nfrom threading import Timer as Tim\nTimerG = threading.Timer\n")
        rows, (tails, unread, stale, bounded), _p = self._census(body, head=head)
        by = {w.split(".")[1]: (s.kind, s.why, sh) for s, sh, w in rows}
        self.assertEqual(by["test_sleep_ok"], ("bounded", "time.sleep(3) returns after 3 s, a literal at or under the 5 s bound read at the call", "tail-only"))
        self.assertEqual(by["test_sleep_bare"][0], "bounded")
        for name in ("sleep_long", "sleep_name", "sleep_noargs"):
            self.assertEqual(by["test_" + name][0], KIND_UNREAD, (name, by["test_" + name]))
            self.assertTrue(by["test_" + name][1].startswith("time.sleep with "), by["test_" + name][1])
        for name in ("close_tcp", "close_http", "close_bare"):
            self.assertEqual(by["test_" + name][0], "bounded", (name, by["test_" + name]))
            self.assertTrue(by["test_" + name][1].startswith("server_close of a "), by["test_" + name][1])
        self.assertEqual(by["test_close_threading"][0], KIND_UNREAD)
        self.assertIn("ThreadingTCPServer", by["test_close_threading"][1])
        self.assertEqual((by["test_timer_ok"][0], by["test_timer_ok"][2]), ("bounded", "tail-only"))
        self.assertTrue(by["test_timer_ok"][1].startswith("set of a threading.Event() returns"), by["test_timer_ok"][1])
        self.assertEqual(by["test_timer_kw"][0], "bounded")
        for name in ("timer_long", "timer_name"):
            self.assertEqual(by["test_" + name][0], KIND_UNREAD, (name, by["test_" + name]))
            self.assertTrue(by["test_" + name][1].startswith("a Timer whose interval "), by["test_" + name][1])
        self.assertEqual((by["test_timer_cancelled"][0], by["test_timer_cancelled"][2]), (KIND_UNREAD, "stop-before-first-assertion"))
        self.assertEqual(by["test_timer_loop"][0], "loop")
        self.assertEqual((by["test_timer_local_alias_ok"][0], by["test_timer_local_alias_ok"][2]), ("bounded", "tail-only"), "an alias reads as a Timer: function= is the callable")
        for name in ("timer_local_alias_long", "timer_import_alias_long", "timer_subclass_long", "timer_global_alias_long"):
            self.assertEqual(by["test_" + name][0], KIND_UNREAD, (name, by["test_" + name]))
            self.assertTrue(by["test_" + name][1].startswith("a Timer whose interval `3600`"), (name, by["test_" + name][1]))
        self.assertTrue(all(bounded_reason_is_read(s.why) for s, _sh, _w in rows if s.kind == "bounded"), [s.why for s, _sh, _w in rows if s.kind == "bounded"])
        self.assertEqual(sorted(w.split(".")[1] for s, w in unread),
                         sorted(["test_sleep_long", "test_sleep_name", "test_sleep_noargs", "test_close_threading", "test_timer_long", "test_timer_name",
                                 "test_timer_local_alias_long", "test_timer_import_alias_long", "test_timer_subclass_long", "test_timer_global_alias_long"]))
        self.assertEqual(self._tails(tails), [("_loop", "T.test_timer_loop")], "the looping Timer is pinned like any loop")

    def test_an_events_set_and_a_queues_nowait_are_bounded_only_on_a_receiver_whose_construction_the_walk_reads(self):
        """STDLIB_CONDITIONED's Event and queue names (romp-manager's ruling on round 1 of PR 891, 2026-09-22). set, clear and
        is_set: bounded on a threading.Event() (through the module, and a bare Event() imported from threading), on an
        asyncio.Event(), and on the kernel-style Timer(0.5, ev.set); UNREADABLE on a multiprocessing.Event() through the
        module, through an import alias (mp.Event()), as a bare name imported from multiprocessing, and on a construction
        the walk cannot name (multiprocessing.get_context().Event()). put_nowait and get_nowait: bounded on queue.Queue()
        and a bare Queue imported from queue, on asyncio.Queue(), and put_nowait on a multiprocessing.Queue(); UNREADABLE for
        get_nowait on a multiprocessing.Queue() and for put_nowait on a multiprocessing.JoinableQueue(). Every bounded reason
        passes bounded_reason_is_read; every unreadable one is listed."""
        head = self.HEAD.replace("import unittest\n", "import unittest\nimport asyncio\nimport queue\nimport multiprocessing\nimport multiprocessing as mp\n"
                                                    "from threading import Event\nfrom multiprocessing import Event as MpEvent\nfrom queue import Queue as Q\n")
        body = ("    def test_thr_set(self):\n        ev = threading.Event()\n        t = threading.Thread(target=ev.set); t.start()\n        self.assertTrue(False)\n"
                "    def test_thr_clear(self):\n        ev = threading.Event()\n        t = threading.Thread(target=ev.clear); t.start()\n        self.assertTrue(False)\n"
                "    def test_thr_is_set(self):\n        ev = threading.Event()\n        t = threading.Thread(target=ev.is_set); t.start()\n        self.assertTrue(False)\n"
                "    def test_bare_set(self):\n        ev = Event()\n        t = threading.Thread(target=ev.set); t.start()\n        self.assertTrue(False)\n"
                "    def test_aio_set(self):\n        ev = asyncio.Event()\n        t = threading.Thread(target=ev.set); t.start()\n        self.assertTrue(False)\n"
                "    def test_timer_set(self):\n        ev = threading.Event()\n        t = threading.Timer(0.5, ev.set); t.start()\n        self.assertTrue(False)\n"
                "    def test_mp_set(self):\n        ev = multiprocessing.Event()\n        t = threading.Thread(target=ev.set); t.start()\n        self.assertTrue(False)\n"
                "    def test_mp_alias_set(self):\n        ev = mp.Event()\n        t = threading.Thread(target=ev.set); t.start()\n        self.assertTrue(False)\n"
                "    def test_mp_bare_clear(self):\n        ev = MpEvent()\n        t = threading.Thread(target=ev.clear); t.start()\n        self.assertTrue(False)\n"
                "    def test_ctx_set(self):\n        ev = multiprocessing.get_context().Event()\n        t = threading.Thread(target=ev.set); t.start()\n        self.assertTrue(False)\n"
                "    def test_q_put(self):\n        q = queue.Queue()\n        t = threading.Thread(target=q.put_nowait, args=(1,)); t.start()\n        self.assertTrue(False)\n"
                "    def test_q_bare_get(self):\n        q = Q()\n        t = threading.Thread(target=q.get_nowait); t.start()\n        self.assertTrue(False)\n"
                "    def test_aio_get(self):\n        q = asyncio.Queue()\n        t = threading.Thread(target=q.get_nowait); t.start()\n        self.assertTrue(False)\n"
                "    def test_mp_put(self):\n        q = multiprocessing.Queue()\n        t = threading.Thread(target=q.put_nowait, args=(1,)); t.start()\n        self.assertTrue(False)\n"
                "    def test_mp_get(self):\n        q = multiprocessing.Queue()\n        t = threading.Thread(target=q.get_nowait); t.start()\n        self.assertTrue(False)\n"
                "    def test_jq_put(self):\n        q = multiprocessing.JoinableQueue()\n        t = threading.Thread(target=q.put_nowait, args=(1,)); t.start()\n        self.assertTrue(False)\n")
        rows, (tails, unread, stale, bounded), _p = self._census(body, head=head)
        by = {w.split(".")[1]: (s.kind, s.why, sh) for s, sh, w in rows}
        for name, start in (("thr_set", "set of a threading.Event() returns"), ("thr_clear", "clear of a threading.Event() returns"),
                            ("thr_is_set", "is_set of a threading.Event() returns"), ("bare_set", "set of a threading.Event() returns"),
                            ("aio_set", "set of an asyncio.Event() returns"), ("timer_set", "set of a threading.Event() returns"),
                            ("q_put", "put_nowait of a queue.Queue() returns"), ("q_bare_get", "get_nowait of a queue.Queue() returns"),
                            ("aio_get", "get_nowait of an asyncio.Queue() returns"), ("mp_put", "put_nowait of a multiprocessing.Queue() returns")):
            self.assertEqual(by["test_" + name][0], "bounded", (name, by["test_" + name]))
            self.assertTrue(by["test_" + name][1].startswith(start), (name, by["test_" + name][1]))
            self.assertTrue(bounded_reason_is_read(by["test_" + name][1]), (name, by["test_" + name][1]))
        for name, words in (("mp_set", "set of a multiprocessing.Event()"), ("mp_alias_set", "set of a multiprocessing.Event()"),
                            ("mp_bare_clear", "clear of a multiprocessing.Event()"), ("ctx_set", "an object the walk does not read"),
                            ("mp_get", "get_nowait of a multiprocessing.Queue()"), ("jq_put", "put_nowait of a multiprocessing.JoinableQueue()")):
            self.assertEqual(by["test_" + name][0], KIND_UNREAD, (name, by["test_" + name]))
            self.assertIn(words, by["test_" + name][1], (name, by["test_" + name][1]))
        self.assertEqual(sorted(w.split(".")[1] for s, w in unread),
                         sorted(["test_mp_set", "test_mp_alias_set", "test_mp_bare_clear", "test_ctx_set", "test_mp_get", "test_jq_put"]))
        self.assertEqual((tails, stale), ([], []))

    def test_a_release_or_a_conditioned_name_on_a_manager_proxy_is_unreadable_and_listed(self):
        """all-4 of round 2 of PR 891's review (2026-09-22): STDLIB_RETURNS' `release` says "on any stdlib receiver", false
        for a multiprocessing.managers proxy (AcquirerProxy.release is a synchronous round trip to the manager process,
        blocked while it is stopped or busy: the probe had a Manager().Lock() proxy's release alive after 1 s with the
        manager SIGSTOPped). The reason now states the exclusion, and this holds the exclusion BY CENSUS: a proxy receiver
        is read as UNREADABLE and LISTED, never through the table, for release (a proxy Lock, Semaphore, RLock: through the
        module, an alias, a bare Manager, a manager bound to a name, a with-as manager, a chained call, a SyncManager) and
        for the conditioned names (a proxy Event's set, clear and is_set; a proxy Queue's put_nowait and get_nowait), while
        the same names on multiprocessing's and threading's own constructors read bounded through the checkers. On the ninth
        pass (2026-09-22) release itself became a conditioned name (_release_rule): the refuter showed the table entry's
        reason claimed a receiver read as threading's, multiprocessing's or asyncio's construction while _library_ctor
        answers True for a constructor of ANY stdlib module, so here a release on a mmap.mmap() and on a sqlite3.connect()
        reads UNREADABLE and listed (the entry would have excused both by name), an asyncio.Lock()'s and a bare-imported
        RLock()'s read bounded through the checker, and the proxies read as they did."""
        head = self.HEAD.replace("import unittest\n", "import unittest\nimport multiprocessing\nimport multiprocessing as mp\n"
                                                    "from multiprocessing import Manager\nfrom multiprocessing.managers import SyncManager\n"
                                                    "import asyncio\nimport mmap\nimport sqlite3\nfrom threading import RLock\n")
        one = "        t = threading.Thread(target=%s); t.start()\n        self.assertTrue(False)\n"
        body = ("    def test_mp_lock(self):\n        lk = multiprocessing.Lock()\n" + one % "lk.release" +
                "    def test_thr_sem(self):\n        s = threading.Semaphore()\n" + one % "s.release" +
                "    def test_aio_lock(self):\n        lk = asyncio.Lock()\n" + one % "lk.release" +
                "    def test_bare_rlock(self):\n        lk = RLock()\n" + one % "lk.release" +
                "    def test_mmap(self):\n        m = mmap.mmap(-1, 16)\n" + one % "m.release" +
                "    def test_sqlite(self):\n        c = sqlite3.connect(':memory:')\n" + one % "c.release" +
                "    def test_mp_event_set(self):\n        ev = multiprocessing.Event()\n" + one % "ev.set" +
                "    def test_proxy_lock(self):\n        lk = multiprocessing.Manager().Lock()\n" + one % "lk.release" +
                "    def test_proxy_alias_sem(self):\n        s = mp.Manager().Semaphore()\n" + one % "s.release" +
                "    def test_proxy_bare_rlock(self):\n        lk = Manager().RLock()\n" + one % "lk.release" +
                "    def test_proxy_bound(self):\n        m = multiprocessing.Manager()\n        lk = m.Lock()\n" + one % "lk.release" +
                "    def test_proxy_with(self):\n        with multiprocessing.Manager() as m:\n            lk = m.Lock()\n"
                "            t = threading.Thread(target=lk.release); t.start()\n            self.assertTrue(False)\n" +
                "    def test_proxy_chained(self):\n" + one % "multiprocessing.Manager().Lock().release" +
                "    def test_sync_manager(self):\n        m = SyncManager()\n        m.start()\n        lk = m.Lock()\n" + one % "lk.release" +
                "    def test_proxy_event_set(self):\n        ev = multiprocessing.Manager().Event()\n" + one % "ev.set" +
                "    def test_proxy_event_clear(self):\n        ev = mp.Manager().Event()\n" + one % "ev.clear" +
                "    def test_proxy_event_is_set(self):\n        m = Manager()\n        ev = m.Event()\n" + one % "ev.is_set" +
                "    def test_proxy_queue_put(self):\n        q = multiprocessing.Manager().Queue()\n"
                "        t = threading.Thread(target=q.put_nowait, args=(1,)); t.start()\n        self.assertTrue(False)\n" +
                "    def test_proxy_queue_get(self):\n        q = Manager().Queue()\n" + one % "q.get_nowait")
        rows, (tails, unread, stale, bounded), _p = self._census(body, head=head)
        by = {}
        for s, sh, w in rows:
            by.setdefault(w.split(".")[1], []).append((s.kind, s.why, sh, s.recv_shown))
        for name, start in (("mp_lock", "release of a multiprocessing.Lock() returns"), ("thr_sem", "release of a threading.Semaphore() returns"),
                            ("aio_lock", "release of a asyncio.Lock() returns"), ("bare_rlock", "release of a threading.RLock() returns")):
            (kind, why, sh, _r), = by["test_" + name]
            self.assertEqual((kind, sh), ("bounded", "tail-only"), (name, by["test_" + name]))
            self.assertTrue(why.startswith(start), (name, why))
            self.assertTrue(bounded_reason_is_read(why), (name, why))
        for name, words in (("mmap", "release of a mmap.mmap() the walk has no rule for"), ("sqlite", "release of a sqlite3.connect() the walk has no rule for")):
            (kind, why, sh, _r), = by["test_" + name]
            self.assertEqual((kind, sh), (KIND_UNREAD, "tail-only"), (name, by["test_" + name]))
            self.assertIn(words, why, (name, why))
        (kind, why, sh, _r), = by["test_mp_event_set"]
        self.assertEqual((kind, sh), (KIND_UNREAD, "tail-only"))
        self.assertIn("set of a multiprocessing.Event()", why, "the conditioned checker, on the module's own constructor")
        proxies = ("proxy_lock", "proxy_alias_sem", "proxy_bare_rlock", "proxy_bound", "proxy_with", "proxy_chained",
                   "proxy_event_set", "proxy_event_clear", "proxy_event_is_set", "proxy_queue_put", "proxy_queue_get")
        for name in proxies:
            (kind, why, sh, _r), = by["test_" + name]
            self.assertEqual((kind, sh), (KIND_UNREAD, "tail-only"), (name, by["test_" + name]))
            self.assertIn("an object the walk does not read", why, (name, why))
            self.assertNotIn(why, STDLIB_RETURNS.values(), (name, "a proxy read through the table"))
            self.assertFalse(why.startswith(CONDITIONED_HEADS) or " returns" in why, (name, why))
        sm = sorted(by["test_sync_manager"], key=lambda r: r[3])
        self.assertEqual([(k, sh, r) for k, _w, sh, r in sm], [("?", "unreadable", "m"), (KIND_UNREAD, "tail-only", "t")],
                         "a SyncManager's start() is an unreadable receiver, listed; the thread on its proxy's release unreadable, listed: %r" % (sm,))
        self.assertIn("a method of `lk`, an object the walk does not read", sm[1][1])
        self.assertEqual(sorted(w.split(".")[1] for s, w in unread),
                         sorted(["test_" + n for n in proxies] + ["test_mp_event_set", "test_sync_manager", "test_sync_manager", "test_mmap", "test_sqlite"]))
        self.assertEqual(sorted(w.split(".")[1] for s, w in bounded), ["test_aio_lock", "test_bare_rlock", "test_mp_lock", "test_thr_sem"])
        self.assertEqual((tails, stale), ([], []))
        for words in ("multiprocessing.managers proxy", "AcquirerProxy", "synchronous round trip", "SIGSTOPped", "BrokenPipeError", "_library_ctor",
                      "mmap.mmap()", "sqlite3.connect()"):
            self.assertIn(words, _release_rule.__doc__, "the checker states the exclusions and their evidence")
        self.assertNotIn("release", STDLIB_RETURNS)

    def test_every_stdlib_returns_entry_says_it_returns_whatever_its_arguments_on_any_receiver(self):
        """Table-shaped (romp-manager's ruling, 2026-09-22): every STDLIB_RETURNS entry's reason states, in UNCONDITIONAL_WORDS,
        the property that lets a name alone excuse a thread: the call returns whatever its arguments and on any stdlib
        receiver. A planted conditional entry without the words reds (the sleep entry the tree carried until this ruling),
        and a conditioned name planted in the table reds even with the words. sleep, server_close, cancel, an Event's set,
        clear and is_set and a queue's put_nowait and get_nowait are the conditioned names, in STDLIB_CONDITIONED and not
        in STDLIB_RETURNS; the `set` entry the table carried until 2026-09-22 reds as a conditioned name now, and so does the
        `cancel` entry it carried until round 2 of PR 891's review (the same day), and the `release` entry it carried until
        the ninth pass (the same day again), which leaves the table EMPTY: the words and this test stand for an entry that
        can say them."""
        self.assertEqual(stdlib_table_problems(STDLIB_RETURNS), [])
        self.assertEqual(sorted(STDLIB_CONDITIONED), ["cancel", "clear", "get_nowait", "is_set", "put_nowait", "release", "server_close", "set", "sleep"])
        self.assertEqual(STDLIB_RETURNS, {}, "the table is empty by construction since the ninth pass")
        self.assertIn("round 2", _release_rule.__doc__, "release states its re-examination for a synchronous callback")
        planted = dict(STDLIB_RETURNS, release="Lock.release returns at once whatever its arguments and on any stdlib receiver the walk reads as a stdlib construction")
        self.assertEqual(stdlib_table_problems(planted), [("release", "a conditioned name: its check runs at the call, it cannot be excused by name")])
        planted = dict(STDLIB_RETURNS, cancel="Timer.cancel returns at once whatever its arguments and on any stdlib receiver")
        self.assertEqual(stdlib_table_problems(planted), [("cancel", "a conditioned name: its check runs at the call, it cannot be excused by name")])
        self.assertFalse(set(STDLIB_CONDITIONED) & set(STDLIB_RETURNS))
        planted = dict(STDLIB_RETURNS, set="Event.set raises the flag and returns whatever its arguments (it takes none) and on any stdlib receiver (no stdlib set() blocks)")
        self.assertEqual(stdlib_table_problems(planted), [("set", "a conditioned name: its check runs at the call, it cannot be excused by name")])
        planted = dict(STDLIB_RETURNS, wait="Event.wait returns when the flag is raised")
        self.assertEqual(stdlib_table_problems(planted), [("wait", "the reason does not say 'whatever its arguments' and 'on any stdlib receiver'")])
        planted = dict(STDLIB_RETURNS, sleep="time.sleep returns when its argument elapses")
        self.assertEqual([n for n, _w in stdlib_table_problems(planted)], ["sleep", "sleep"])
        planted = dict(STDLIB_RETURNS, sleep="time.sleep returns whatever its arguments and on any stdlib receiver")
        self.assertEqual(stdlib_table_problems(planted), [("sleep", "a conditioned name: its check runs at the call, it cannot be excused by name")])

    def test_the_threads_the_product_starts_on_a_tests_call_are_informational_rows(self):
        """INFORMATIONAL rows (romp-manager's ruling, 2026-09-22) on a planted product file: a spawn-helper called through the
        alias (a row saying what starts); one whose start sits under `if <parameter>:` is a row when the argument or the
        default is a true literal (start_sender defaulting True; reconcile=True handed in), no row when it is a false
        literal (reconcile left at its default False; start_sender=False handed), a MAY-START row when it is not a literal;
        a product helper that constructs a Thread without starting it is no row; a product object's method that starts a
        Timer; a product object's own start() (bound and chained); loop.run_in_executor(None, gate.wait) (an untimed wait);
        a ThreadPoolExecutor under a with and one not. None is a start row, none is in tail_only's buckets."""
        product = ("import threading\n"
                   "def _ws_sender(q):\n    while True:\n        q.get()\n"
                   "def _new_ws_client(app, start_sender=True):\n    q = []\n    if start_sender:\n"
                   "        threading.Thread(target=_ws_sender, args=(q,), daemon=True).start()\n    return q\n"
                   "def _push_notify(title):\n    threading.Thread(target=print, args=(title,)).start()\n"
                   "def _quiet(title):\n    t = threading.Thread(target=print)\n    return t\n"
                   "class SdkBackend:\n    def __init__(self, d, reconcile=False):\n        if reconcile:\n"
                   "            threading.Thread(target=self._boot_reconcile).start()\n    def _boot_reconcile(self):\n        pass\n"
                   "    def quiesce(self):\n        threading.Timer(0.1, self._boot_reconcile).start()\n"
                   "class SdkSession:\n    def __init__(self, be):\n        self.thread = threading.Thread(target=print)\n"
                   "    def start(self):\n        self.thread.start()\n")
        head = self.HEAD.replace("import unittest\n", "import unittest\nimport asyncio\nfrom concurrent.futures import ThreadPoolExecutor\n") \
            .replace("class T(", "km = load_source('fake_kernel', 'fake_kernel.py')\nclass T(")
        extras = {}
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_x(self, flag=None):\n"
            "        gate = threading.Event()\n"
            "        km._new_ws_client('chat')\n"
            "        km._new_ws_client('chat', start_sender=False)\n"
            "        km._new_ws_client('chat', start_sender=flag)\n"
            "        km._push_notify('t')\n"
            "        km._quiet('t')\n"
            "        be = km.SdkBackend('d')\n"
            "        be2 = km.SdkBackend('d', reconcile=True)\n"
            "        be2.quiesce()\n"
            "        s = km.SdkSession(be)\n"
            "        s.start()\n"
            "        km.SdkSession(be).start()\n"
            "        asyncio.get_event_loop().run_in_executor(None, gate.wait)\n"
            "        with ThreadPoolExecutor(max_workers=1) as ex:\n"
            "            ex.submit(print)\n"
            "        pool = ThreadPoolExecutor(max_workers=1)\n"
            "        self.assertTrue(False)\n", head=head, product={"fake_kernel": product}, extras=extras)
        self.assertEqual(rows, [], "no start row: every thread here is the product's")
        info = extras["product_starts"]
        got = sorted((r.shape, r.target, r.why) for r in info)
        self.assertEqual(got, sorted([
            ("spawn-helper", "km._new_ws_client('chat')", "_new_ws_client starts Thread(target=_ws_sender) when start_sender is true (start_sender True by default)"),
            ("spawn-helper", "km._new_ws_client('chat', start_sender=flag)", "_new_ws_client starts Thread(target=_ws_sender) when start_sender is true (start_sender = flag, not a literal: it may start)"),
            ("spawn-helper", "km._push_notify('t')", "_push_notify starts Thread(target=print)"),
            ("spawn-helper", "km.SdkBackend('d', reconcile=True)", "SdkBackend.__init__ starts Thread(target=self._boot_reconcile) when reconcile is true (reconcile True handed in)"),
            ("spawn-helper", "be2.quiesce()", "SdkBackend.quiesce starts Timer(function=self._boot_reconcile)"),
            ("object-start", "s.start()", "SdkSession's own start(): the object's thread"),
            ("object-start", "km.SdkSession(be).start()", "SdkSession's own start(): the object's thread"),
            ("run_in_executor", "asyncio.get_event_loop().run_in_executor(None, gate.wait)", "a worker of the loop's default executor runs gate.wait, an untimed wait"),
            ("pool", "ThreadPoolExecutor(max_workers=1)", "the pool's worker threads, under a with that shuts the pool down and joins them on exit"),
            ("pool", "ThreadPoolExecutor(max_workers=1)", "the pool's worker threads, NOT under a with"),
        ]))
        self.assertEqual({r.kind for r in info}, {PRODUCT_START})
        self.assertTrue(all(r.describe().startswith("%s:" % _p) for r in info), [r.describe() for r in info])
        self.assertEqual((tails, unread, stale, bounded), ([], [], [], []))
        self.assertEqual((extras["modules"], extras["oracle"]), (1, []))

    def test_every_unknown_target_falls_to_unreadable_never_bounded(self):
        """THE RULE, asserted structurally over a table of targets the walk cannot read rather than one plant each: a
        parameter and a method of one, a function of a module the walk does not read, a stdlib function with no
        STDLIB_RETURNS entry, a method reached through the class on an instance it cannot name (`*kids`, a literal, a
        lambda: the syntheses that used to raise SyntaxError out of the census), a callable built by a call it does not
        read (a parameter's, functools.partial), an element of a list, a stdlib method with no rule, a shape nobody
        anticipated (a conditional expression, getattr(...)), and the THIRD ARM (romp-manager's ruling, 2026-09-22): a body
        the walk read whose work is a call of a parameter (`lambda: param()`, a def calling one), of a callable attribute
        of one (`obj.frob()`), through a parameter's attribute (`obj.a.b(1)`), or of the def's own parameter no hand
        supplies (`own(cb)` started with no args=). Every row is kind UNREADABLE, none bounded, none crashes the census,
        and with a tail-only stop each is listed in the unreadable bucket."""
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_x(self, param=None, obj=None, factory=None):\n"
            "        kids = [_Child(), _Child()]\n"
            "        fns = [_once, _loop]\n"
            "        ev = threading.Event()\n"
            "        threading.Thread(target=param).start()\n"
            "        threading.Thread(target=obj.frob).start()\n"
            "        threading.Thread(target=somelib.run).start()\n"
            "        threading.Thread(target=os.getcwd).start()\n"
            "        threading.Thread(target=_Child._drain, args=(*kids,)).start()\n"
            "        threading.Thread(target=_Child._drain, args=(0,)).start()\n"
            "        threading.Thread(target=_Child._drain, args=(lambda: 1,)).start()\n"
            "        threading.Thread(target=factory()).start()\n"
            "        threading.Thread(target=functools.partial(_once)).start()\n"
            "        threading.Thread(target=fns[1]).start()\n"
            "        threading.Thread(target=ev.wait, args=(1,)).start()\n"
            "        threading.Thread(target=(param or _once)).start()\n"
            "        threading.Thread(target=getattr(km, 'x')).start()\n"
            "        threading.Thread(target=lambda: param()).start()\n"
            "        threading.Thread(target=lambda: obj.frob()).start()\n"
            "        threading.Thread(target=lambda: obj.a.b(1)).start()\n"
            "        def via_def():\n            return param(1)\n"
            "        threading.Thread(target=via_def).start()\n"
            "        def own(cb):\n            cb()\n"
            "        threading.Thread(target=own).start()\n"
            "        self.assertTrue(False)\n",
            head=self.HEAD_FAKES.replace("import unittest\n", "import unittest\nimport os\nimport functools\nimport somelib\n"
                                         "km = __import__('types').ModuleType('km')\n"))
        self.assertEqual(len(rows), 18, [(s.target, s.kind, sh) for s, sh, w in rows])
        self.assertEqual({s.kind for s, _sh, _w in rows}, {KIND_UNREAD}, [(s.target, s.kind, s.why) for s, _sh, _w in rows])
        self.assertEqual({sh for _s, sh, _w in rows}, {"tail-only"})
        self.assertEqual((tails, bounded, stale), ([], [], []))
        self.assertEqual(sorted(s.target for s, w in unread), sorted(s.target for s, _sh, _w in rows), "every one is listed")
        reasons = {}
        for s, _sh, _w in rows:
            reasons.setdefault(s.target, []).append(s.why)
        self.assertIn("parameter", reasons["param"][0])
        self.assertIn("parameter", reasons["obj.frob"][0])
        self.assertIn("somelib", reasons["somelib.run"][0])
        self.assertIn("stdlib", reasons["os.getcwd"][0])
        self.assertEqual(sorted(reasons["_Child._drain"]),
                         sorted("a method reached through the class on `%s`, an instance the walk cannot name" % h for h in ("*kids", "0", "lambda: 1")))
        self.assertIn("factory", reasons["factory()"][0])
        self.assertIn("Event", reasons["ev.wait"][0])
        # the third arm: a body the walk read whose work is a call of a parameter, or through one, no hand supplies
        self.assertEqual(reasons["lambda: param()"], ["calls param, a parameter of test_x: what the caller hands in is not read here"])
        self.assertEqual(reasons["lambda: obj.frob()"], ["calls obj.frob, obj a parameter of test_x: what the caller hands in is not read here"])
        self.assertEqual(reasons["lambda: obj.a.b(1)"], ["calls obj.a.b, obj a parameter of test_x: what the caller hands in is not read here"])
        self.assertEqual(reasons["via_def"], ["calls param, a parameter of test_x: what the caller hands in is not read here"])
        self.assertEqual(reasons["own"], ["calls cb, a parameter of own: what the caller hands in is not read here"])

    def test_a_body_whose_work_is_a_call_of_a_parameter_is_read_where_the_argument_is_in_hand(self):
        """The third arm's other side (romp-manager's ruling, 2026-09-22): a body whose work is a call of a parameter is
        UNREADABLE in the helper's own row and READ where the argument is in hand. At the CALLER of a helper (`_run(fn, *a)`
        starting `go`, whose `fn(*a)` is the caller's argument): a module function (bounded, excused on the tail), a
        looping one (pinned), a lambda calling a product loop (a loop by indirect evidence, pinned), a product function
        (bounded), a fake's method with an untimed wait (waits, pinned), a parameter of the caller itself (unreadable,
        listed), a loop joined untimed before the assertion (its stop). At the CONSTRUCTION (`Thread(target=run,
        args=(_loop,))` for a `run(fn)` that calls fn): the args= element, a kwargs= entry, none (unreadable). At the CALL
        (`_until(lambda: ...)`, a module function called in the body with a lambda): the lambda read to its end. Each row's
        reason names the hand."""
        product = "import threading\ndef spin():\n    while True:\n        pass\ndef once():\n    return 1\n"
        head = self.HEAD_FAKES.replace("class T(", "km = load_source('fake_kernel', 'fake_kernel.py')\n"
                                                  "def _until(fn):\n    if fn():\n        return 1\n"
                                                  "def _run(fn, *a):\n    def go():\n        fn(*a)\n"
                                                  "    t = threading.Thread(target=go)\n    t.start()\n    return t\n"
                                                  "class T(")
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_once(self):\n        t = _run(_once)\n        self.assertTrue(False)\n        t.join()\n"
            "    def test_loop(self):\n        t = _run(_loop)\n        self.assertTrue(False)\n        t.join()\n"
            "    def test_lambda(self):\n        t = _run(lambda: km.spin())\n        self.assertTrue(False)\n"
            "    def test_product(self):\n        t = _run(km.once, 1)\n        self.assertTrue(False)\n"
            "    def test_fake(self):\n        t = _run(self.fake.block)\n        self.assertTrue(False)\n"
            "    def test_param(self, cb=None):\n        t = _run(cb)\n        self.assertTrue(False)\n"
            "    def test_joined(self):\n        t = _run(_loop)\n        t.join()\n        self.assertTrue(False)\n"
            "    def test_ctor(self):\n"
            "        def run(fn):\n            fn()\n"
            "        threading.Thread(target=run, args=(_loop,)).start()\n"
            "        threading.Thread(target=run, args=(_once,)).start()\n"
            "        threading.Thread(target=run, kwargs={'fn': self.fake.block}).start()\n"
            "        threading.Thread(target=run).start()\n"
            "        self.assertTrue(False)\n"
            "    def test_call(self):\n"
            "        threading.Thread(target=lambda: _until(lambda: _loop())).start()\n"
            "        threading.Thread(target=lambda: _until(_once)).start()\n"
            "        self.assertTrue(False)\n"
            "    def test_method(self):\n"
            "        q = queue.Queue()\n"
            "        d = {'k': 1}\n"
            "        be = km.Be()\n"
            "        threading.Thread(target=lambda: _poke(q)).start()\n"
            "        threading.Thread(target=lambda: _poke(d)).start()\n"
            "        threading.Thread(target=lambda: _poke(self.fake)).start()\n"
            "        threading.Thread(target=lambda: _poke(be)).start()\n"
            "        threading.Thread(target=lambda: _pop(q)).start()\n"
            "        threading.Thread(target=lambda: _hand(self.fake)).start()\n"
            "        threading.Thread(target=lambda: _sorted(d)).start()\n"
            "        threading.Thread(target=lambda: _bound(_loop)).start()\n"
            "        self.assertTrue(False)\n",
            head=head.replace("import unittest\n", "import unittest\nimport queue\n")
                     .replace("class T(", "def _poke(x):\n    return x.get('k')\n"
                                          "def _pop(x):\n    return x.get()\n"
                                          "def _hand(f):\n    return _poke(f)\n"
                                          "def _sorted(rows):\n    return sorted(rows, key=lambda r: r.get('t'))\n"
                                          "def _bound(fn):\n    worker = lambda: fn()\n    return worker()\n"
                                          "class T("),
            product={"fake_kernel": product + "class Be:\n    def get(self, k):\n        while True:\n            pass\n"})
        by = {}
        for st, sh, w in rows:
            by.setdefault(w, []).append((st.target, st.kind, st.why, sh))
        self.assertNotIn("_run", by, "the helper's own row is tail-only and unreadable: classed at its callers")
        self.assertEqual(by["T.test_once"], [("go", "bounded", "no loop, no untimed wait | fn of _run is `_once` handed in by the caller", "tail-only")])
        self.assertEqual(by["T.test_loop"], [("go", "loop", "a while loop | fn of _run is `_loop` handed in by the caller", "tail-only")])
        self.assertEqual(by["T.test_lambda"], [("go", "loop", "calls spin, a product function with a while loop | fn of _run is `lambda: km.spin()` handed in by the caller", "tail-only")])
        self.assertEqual(by["T.test_product"], [("go", "bounded", "no loop, no untimed wait | fn of _run is `km.once` handed in by the caller", "tail-only")])
        self.assertEqual(by["T.test_fake"], [("go", "waits", "an untimed .wait() | fn of _run is `self.fake.block` handed in by the caller", "tail-only")])
        self.assertEqual(by["T.test_param"], [("go", KIND_UNREAD, "a parameter (cb): what the caller hands in is not read here | fn of _run is `cb` handed in by the caller", "tail-only")])
        self.assertEqual(by["T.test_joined"], [("go", "loop", "a while loop | fn of _run is `_loop` handed in by the caller", "stop-before-first-assertion")])
        self.assertEqual([r[1:] for r in by["T.test_ctor"]], [
            ("loop", "a while loop | fn of run is `_loop` handed in at the construction", "tail-only"),
            ("bounded", "no loop, no untimed wait | fn of run is `_once` handed in at the construction", "tail-only"),
            ("waits", "an untimed .wait() | fn of run is `self.fake.block` handed in at the construction", "tail-only"),
            (KIND_UNREAD, "calls fn, a parameter of run: what the caller hands in is not read here", "tail-only")])
        self.assertEqual([r[1:] for r in by["T.test_call"]], [
            ("loop", "calls _until, calls _loop, a while loop | fn of _until is `lambda: _loop()` handed in at the call", "tail-only"),
            ("bounded", "no loop, no untimed wait | fn of _until is `_once` handed in at the call", "tail-only")])
        # a METHOD called on the parameter is read on the hand, with the call's own arguments: x.get('k') on a Queue is a
        # method the table has no rule for (unreadable), on a dict literal a literal's (bounded), on a fake the walk does not
        # read (unreadable), on a product object its method in its module (a while: loop); x.get() with no arguments is the
        # body's own untimed wait, whatever x is (the name rule, first); a hand that is a parameter follows its own hand
        # (_hand(f) -> _poke(x): the fake, the innermost hand first); a lambda handed to sorted() is inside a call the walk does not follow (bounded,
        # the stated limit); a name-bound lambda the body calls is read with the call's hands (a loop)
        self.assertEqual([r[1:] for r in by["T.test_method"]], [
            (KIND_UNREAD, "calls _poke, q.get: a method of a Queue() the walk has no rule for | x.get of _poke is `q`.get handed in at the call", "tail-only"),
            ("bounded", "no loop, no untimed wait | x.get of _poke is `d`.get handed in at the call", "tail-only"),
            (KIND_UNREAD, "calls _poke, a method of `self.fake`, an object the walk does not read | x.get of _poke is `self.fake`.get handed in at the call", "tail-only"),
            ("loop", "calls _poke, a product function with a while loop | x.get of _poke is `be`.get handed in at the call", "tail-only"),
            ("waits", "calls _pop, an untimed .get()", "tail-only"),
            (KIND_UNREAD, "calls _hand, calls _poke, a method of `self.fake`, an object the walk does not read | f.get of _hand is `self.fake`.get handed in at the call | x.get of _poke is `f`.get handed in at the call", "tail-only"),
            ("bounded", "no loop, no untimed wait", "tail-only"),
            ("loop", "calls _bound, calls worker, a while loop | fn of _bound is `_loop` handed in at the call", "tail-only")])
        self.assertEqual(self._tails(tails), sorted([("go", "T.test_loop"), ("go", "T.test_lambda"), ("go", "T.test_fake"),
                                                     ("run", "T.test_ctor"), ("run", "T.test_ctor"), ("lambda: _until(lambda: _loop())", "T.test_call"),
                                                     ("lambda: _pop(q)", "T.test_method"), ("lambda: _poke(be)", "T.test_method"),
                                                     ("lambda: _bound(_loop)", "T.test_method")]))
        self.assertEqual(sorted((s_.target, w) for s_, w in unread), [("go", "T.test_param"), ("lambda: _hand(self.fake)", "T.test_method"),
                                                                       ("lambda: _poke(q)", "T.test_method"), ("lambda: _poke(self.fake)", "T.test_method"),
                                                                       ("run", "T.test_ctor")])
        self.assertEqual(sorted((s_.target, w) for s_, w in bounded), sorted([("go", "T.test_once"), ("go", "T.test_product"), ("run", "T.test_ctor"),
                                                                              ("lambda: _until(_once)", "T.test_call"),
                                                                              ("lambda: _poke(d)", "T.test_method"), ("lambda: _sorted(d)", "T.test_method")]))
        self.assertTrue(all(bounded_reason_is_read(s_.why) for s_, w in bounded), [s_.why for s_, w in bounded])
        self.assertFalse(bounded_reason_is_read("no loop, no untimed wait | fn is `x`"), "a segment that is not a hand is not read")

    def test_a_product_function_is_read_in_its_own_module_and_an_attribute_no_function_defines_is_unreadable(self):
        """The product road: a product module alias (km = load_source(...)), a local bound to one through a helper
        (k = _kernel()), a product object built through the alias (km.Be()) or unpacked from a helper's tuple. A product
        function is READ: a body with no loop and no wait is bounded (the excused kind, with the read-body reason), a
        while is a loop, an untimed get is waits, a delegation to a looping product function is a loop by indirect
        evidence (`calls`, so the timed-join rule reads it as bounded), a method of a product class follows its own
        `self._loop()`. A stdlib object the product module holds (km._LOOPS_STOP, a threading.Event) has its methods read
        from STDLIB_RETURNS (set: bounded) or the name rules (wait: waits). An attribute of the alias that no product
        function defines is UNREADABLE."""
        product = ("import threading\nimport queue\n_LOOPS_STOP = threading.Event()\nq = queue.Queue()\n"
                   "def once():\n    return 1\n"
                   "def spin():\n    while True:\n        pass\n"
                   "def block():\n    q.get()\n"
                   "def relay():\n    return spin()\n"
                   "class Be:\n    def send(self):\n        return self._save()\n    def _save(self):\n        return 1\n"
                   "    def pump(self):\n        self._loop()\n    def _loop(self):\n        while True:\n            pass\n")
        head = self.HEAD.replace("class T(", "km = load_source('fake_kernel', 'fake_kernel.py')\n"
                                             "def _kernel():\n    return km\n"
                                             "def _backend():\n    return km.Be(), 1\n"
                                             "class T(")
        rows, (tails, unread, stale, bounded), _p = self._census(
            "    def test_once(self):\n        threading.Thread(target=km.once).start()\n        self.assertTrue(False)\n"
            "    def test_spin(self):\n        threading.Thread(target=km.spin).start()\n        self.assertTrue(False)\n"
            "    def test_block(self):\n        threading.Thread(target=km.block).start()\n        self.assertTrue(False)\n"
            "    def test_relay(self):\n        threading.Thread(target=km.relay).start()\n        self.assertTrue(False)\n"
            "    def test_be_send(self):\n        be, _ = _backend()\n        threading.Thread(target=be.send).start()\n        self.assertTrue(False)\n"
            "    def test_be_pump(self):\n        be = km.Be()\n        threading.Thread(target=be.pump).start()\n        self.assertTrue(False)\n"
            "    def test_local_alias(self):\n        k = _kernel()\n        threading.Thread(target=k.once).start()\n        self.assertTrue(False)\n"
            "    def test_missing(self):\n        threading.Thread(target=km.nothing_here).start()\n        self.assertTrue(False)\n"
            "    def test_event_set(self):\n        threading.Timer(0.1, km._LOOPS_STOP.set).start()\n        self.assertTrue(False)\n"
            "    def test_event_wait(self):\n        threading.Timer(0.1, km._LOOPS_STOP.wait).start()\n        self.assertTrue(False)\n"
            "    def test_lambda_spin(self):\n        threading.Thread(target=lambda: km.spin()).start()\n        self.assertTrue(False)\n"
            "    def test_relay_joined(self):\n        t = threading.Thread(target=km.relay)\n        t.start(); t.join(5)\n        self.assertTrue(False)\n",
            head=head, product={"fake_kernel": product})
        by = {w: (s.kind, s.why, sh) for s, sh, w in rows}
        self.assertEqual(by["T.test_once"], ("bounded", "a product function read in 1 definition: no loop, no untimed wait", "tail-only"))
        self.assertEqual(by["T.test_spin"], ("loop", "a product function with a while loop", "tail-only"))
        self.assertEqual(by["T.test_block"], ("waits", "a product function: an untimed .get()", "tail-only"))
        self.assertEqual(by["T.test_relay"], ("loop", "a product function: calls spin, a while loop", "tail-only"))
        self.assertEqual(by["T.test_be_send"], ("bounded", "a product function read in 1 definition: no loop, no untimed wait", "tail-only"))
        self.assertEqual(by["T.test_be_pump"], ("loop", "a product function: calls self._loop, a while loop", "tail-only"))
        self.assertEqual(by["T.test_local_alias"][0], "bounded")
        self.assertEqual(by["T.test_missing"], (KIND_UNREAD, "km.nothing_here: a product attribute no product function defines", "tail-only"))
        self.assertEqual((by["T.test_event_set"][0], by["T.test_event_set"][2]), ("bounded", "tail-only"))
        self.assertTrue(by["T.test_event_set"][1].startswith("set of a threading.Event() returns"), by["T.test_event_set"][1])
        self.assertEqual(by["T.test_event_wait"], ("waits", "the target is an untimed .wait", "tail-only"))
        self.assertEqual(by["T.test_lambda_spin"], ("loop", "calls spin, a product function with a while loop", "tail-only"))
        self.assertEqual(by["T.test_relay_joined"][2], "stop-before-first-assertion", "an indirect loop: the timed join is its stop")
        self.assertEqual(sorted(w for s, w in unread), ["T.test_missing"])
        self.assertEqual(sorted(w for s, w in bounded), ["T.test_be_send", "T.test_event_set", "T.test_local_alias", "T.test_once"])
        self.assertTrue(all(bounded_reason_is_read(s.why) for s, w in bounded), [s.why for s, w in bounded])

    def test_a_cancel_is_bounded_only_on_a_timer_an_asyncio_handle_or_a_future_with_no_done_callback(self):
        """STDLIB_CONDITIONED's cancel (round 2 of PR 891's review, 2026-09-22). concurrent.futures.Future.cancel runs the done
        callbacks synchronously, so a Future with an add_done_callback in the unit (through the module, a bare import, or a
        self attribute whose callback setUp registered) is UNREADABLE and listed, one with none bounded; a threading.Timer's
        cancel (by name or alias) and an asyncio Future's or a loop handle's are bounded; a pool future's (ex.submit) and a
        sched.scheduler's are unreadable. release stays in STDLIB_RETURNS with its re-examination. Every bounded reason
        passes bounded_reason_is_read."""
        head = self.HEAD.replace("import unittest\n", "import unittest\nimport asyncio\nimport concurrent.futures\nimport sched\n"
                                                    "from concurrent.futures import Future\nfrom threading import Timer as Tm\n")
        body = ("    def setUp(self):\n        self.fut = concurrent.futures.Future()\n        self.fut.add_done_callback(print)\n"
                "    def test_fut_cb(self):\n        gate = threading.Event()\n        fut = concurrent.futures.Future()\n"
                "        fut.add_done_callback(lambda f: gate.wait())\n        t = threading.Thread(target=fut.cancel); t.start()\n        self.assertTrue(False)\n"
                "    def test_fut_no_cb(self):\n        fut = concurrent.futures.Future()\n        t = threading.Thread(target=fut.cancel); t.start()\n        self.assertTrue(False)\n"
                "    def test_fut_bare_cb(self):\n        fut = Future()\n        fut.add_done_callback(print)\n        t = threading.Thread(target=fut.cancel); t.start()\n        self.assertTrue(False)\n"
                "    def test_self_fut_cb(self):\n        t = threading.Thread(target=self.fut.cancel); t.start()\n        self.assertTrue(False)\n"
                "    def test_timer(self):\n        tm = threading.Timer(3600, print)\n        t = threading.Thread(target=tm.cancel); t.start()\n        self.assertTrue(False)\n"
                "    def test_timer_alias(self):\n        tm = Tm(3600, print)\n        t = threading.Thread(target=tm.cancel); t.start()\n        self.assertTrue(False)\n"
                "    def test_aio_future(self):\n        fut = asyncio.Future()\n        t = threading.Thread(target=fut.cancel); t.start()\n        self.assertTrue(False)\n"
                "    def test_aio_handle(self):\n        loop = asyncio.new_event_loop()\n        h = loop.call_later(1, print)\n"
                "        t = threading.Thread(target=h.cancel); t.start()\n        self.assertTrue(False)\n"
                "    def test_sched(self):\n        s = sched.scheduler(time.time, time.sleep)\n        t = threading.Thread(target=s.cancel, args=(None,)); t.start()\n        self.assertTrue(False)\n"
                "    def test_pool(self):\n        ex = concurrent.futures.ThreadPoolExecutor(1)\n        fut = ex.submit(print)\n"
                "        t = threading.Thread(target=fut.cancel); t.start()\n        self.assertTrue(False)\n"
                "    def test_release(self):\n        lk = threading.Lock(); lk.acquire()\n        t = threading.Thread(target=lk.release); t.start()\n        self.assertTrue(False)\n")
        rows, (tails, unread, stale, bounded), _p = self._census(body, head=head)
        by = {w.split(".")[1]: (s.kind, s.why, sh) for s, sh, w in rows}
        for name, start in (("fut_cb", "cancel of a concurrent.futures.Future() with an add_done_callback registered on `fut`"),
                            ("fut_bare_cb", "cancel of a concurrent.futures.Future() with an add_done_callback registered on `fut`"),
                            ("self_fut_cb", "cancel of a concurrent.futures.Future() with an add_done_callback registered on `self.fut`"),
                            ("sched", "cancel of a sched.scheduler() the walk has no rule for"),
                            ("pool", "cancel of a pool future (submit())")):
            self.assertEqual(by["test_" + name][0], KIND_UNREAD, (name, by["test_" + name]))
            self.assertTrue(by["test_" + name][1].startswith(start), (name, by["test_" + name][1]))
        for name, start in (("fut_no_cb", "cancel of a concurrent.futures.Future() with no add_done_callback on it in the unit returns"),
                            ("timer", "cancel of a threading.Timer() returns"), ("timer_alias", "cancel of a threading.Timer() returns"),
                            ("aio_future", "cancel of an asyncio asyncio.Future() returns"), ("aio_handle", "cancel of an asyncio loop.call_later() returns"),
                            ("release", "release of a threading.Lock() returns")):      # the conditioned checker since the ninth pass
            self.assertEqual(by["test_" + name][0], "bounded", (name, by["test_" + name]))
            self.assertTrue(by["test_" + name][1].startswith(start), (name, by["test_" + name][1]))
            self.assertTrue(bounded_reason_is_read(by["test_" + name][1]), (name, by["test_" + name][1]))
        self.assertEqual(sorted(w.split(".")[1] for s, w in unread), sorted(["test_fut_cb", "test_fut_bare_cb", "test_self_fut_cb", "test_sched", "test_pool"]))
        self.assertEqual((tails, stale), ([], []))

    def test_a_futures_untimed_result_is_a_wait_in_a_body_and_as_a_target(self):
        """result joined BLOCKING (round 2 of PR 891's review, 2026-09-22): a body waiting on `ex.submit(...).result()` or
        `.result(timeout=None)` is a waits thread (pinned when its stop is tail-only), `.result(5)` bounded; a `fut.result`
        target with no args= is an untimed wait, one with a timeout falls to the stdlib table, which has no rule for a timed
        wait (unreadable, listed)."""
        head = self.HEAD.replace("import unittest\n", "import unittest\nimport concurrent.futures\n")
        body = ("    def test_untimed(self):\n        ex = concurrent.futures.ThreadPoolExecutor(1)\n        def body():\n            ex.submit(print).result()\n"
                "        t = threading.Thread(target=body); t.start()\n        self.assertTrue(False)\n"
                "    def test_kw_none(self):\n        ex = concurrent.futures.ThreadPoolExecutor(1)\n        def body():\n            ex.submit(print).result(timeout=None)\n"
                "        t = threading.Thread(target=body); t.start()\n        self.assertTrue(False)\n"
                "    def test_timed(self):\n        ex = concurrent.futures.ThreadPoolExecutor(1)\n        def body():\n            ex.submit(print).result(5)\n"
                "        t = threading.Thread(target=body); t.start()\n        self.assertTrue(False)\n"
                "    def test_target(self):\n        fut = concurrent.futures.Future()\n        t = threading.Thread(target=fut.result); t.start()\n        self.assertTrue(False)\n"
                "    def test_target_timed(self):\n        fut = concurrent.futures.Future()\n        t = threading.Thread(target=fut.result, args=(1,)); t.start()\n        self.assertTrue(False)\n")
        rows, (tails, unread, stale, bounded), _p = self._census(body, head=head)
        by = {w.split(".")[1]: (s.kind, s.why, sh) for s, sh, w in rows}
        self.assertEqual(by["test_untimed"], ("waits", "an untimed .result()", "tail-only"))
        self.assertEqual(by["test_kw_none"], ("waits", "an untimed .result(timeout=None)", "tail-only"))
        self.assertEqual(by["test_timed"], ("bounded", "no loop, no untimed wait", "tail-only"))
        self.assertEqual(by["test_target"], ("waits", "the target is an untimed .result", "tail-only"))
        self.assertEqual(by["test_target_timed"][0], KIND_UNREAD)
        self.assertIn("Future", by["test_target_timed"][1])
        self.assertEqual(self._tails(tails), [("body", "T.test_kw_none"), ("body", "T.test_untimed"), ("fut.result", "T.test_target")])
        self.assertEqual([w.split(".")[1] for s, w in unread], ["test_target_timed"])
        self.assertEqual([w.split(".")[1] for s, w in bounded], ["test_timed"])

    def test_a_call_through_an_indirection_of_a_parameter_is_opaque_and_read_through_the_hand(self):
        """The third arm's INDIRECTIONS (round 2 of PR 891's review, 2026-09-22; each read BOUNDED before it): a local alias
        (`g = fn; g()`), a subscript (`fns[0]()`, `kw["fn"]()`), a for or comprehension target over the parameter, a BoolOp
        or an IfExp with the parameter as an operand, a *spread into the iterated tuple, a keyword-only parameter,
        functools.partial over the parameter (dotted and bare), getattr over it (a literal name reads the attribute; a
        name is unnameable, unreadable), a *args element (no hand can place it: unreadable), a **kwargs element (likewise)
        beside a **kwargs dict's own method (a builtin container's, not opaque), a self attribute __init__ bound from a
        parameter (`self.fn = fn; self.fn()`: read from the fake's construction, unreadable when the construction hands a
        parameter of the caller), and the same alias and subscript at the construction's args=. Every helper row is
        unreadable in its own body and classed at its callers, where the hand decides: a loop pinned, a bounded call
        excused, a road with no hand listed. The reason names the road (`fns[]`) and each hand. Data access on a handed-in
        literal is read as data: `(store.get("nodes") or {}).get("x")` on a dict literal, `acc["failures"].append(1)` on a
        helper's returned literal, both bounded."""
        helpers = ("import functools\nfrom functools import partial\n"
                   "def _alias(fn):\n    def go():\n        g = fn\n        g()\n    t = threading.Thread(target=go); t.start(); return t\n"
                   "def _sub(fns):\n    def go():\n        fns[0]()\n    t = threading.Thread(target=go); t.start(); return t\n"
                   "def _key(kw):\n    def go():\n        kw['fn']()\n    t = threading.Thread(target=go); t.start(); return t\n"
                   "def _each(fns):\n    def go():\n        for f in fns:\n            f()\n    t = threading.Thread(target=go); t.start(); return t\n"
                   "def _comp(fns):\n    def go():\n        [f() for f in fns]\n    t = threading.Thread(target=go); t.start(); return t\n"
                   "def _or(fn):\n    def go():\n        (fn or _once)()\n    t = threading.Thread(target=go); t.start(); return t\n"
                   "def _ifexp(fn, flag):\n    def go():\n        (fn if flag else _once)()\n    t = threading.Thread(target=go); t.start(); return t\n"
                   "def _star(fns):\n    def go():\n        for f in (*fns, _once):\n            f()\n    t = threading.Thread(target=go); t.start(); return t\n"
                   "def _kwonly(*, fn):\n    def go():\n        fn()\n    t = threading.Thread(target=go); t.start(); return t\n"
                   "def _partial(fn):\n    def go():\n        functools.partial(fn, 1)()\n    t = threading.Thread(target=go); t.start(); return t\n"
                   "def _partial_bare(fn):\n    def go():\n        partial(fn)()\n    t = threading.Thread(target=go); t.start(); return t\n"
                   "def _getattr(obj, name):\n    def go():\n        getattr(obj, name)()\n    t = threading.Thread(target=go); t.start(); return t\n"
                   "def _getattr_lit(obj):\n    def go():\n        getattr(obj, 'run')()\n    t = threading.Thread(target=go); t.start(); return t\n"
                   "def _varargs(*fns):\n    def go():\n        fns[0]()\n    t = threading.Thread(target=go); t.start(); return t\n"
                   "def _kwstar(**kw):\n    def go():\n        kw['fn']()\n    t = threading.Thread(target=go); t.start(); return t\n"
                   "def _kwitems(**kw):\n    def go():\n        return list(kw.items())\n    t = threading.Thread(target=go); t.start(); return t\n"
                   "def _nodes(store):\n    def go():\n        (store.get('nodes') or {}).get('x')\n    t = threading.Thread(target=go); t.start(); return t\n"
                   "def _acc():\n    return {'failures': [], 'n': 0}\n"
                   "def _rec(acc):\n    def go():\n        acc['failures'].append(1)\n    t = threading.Thread(target=go); t.start(); return t\n"
                   "class _F:\n    def __init__(self, fn):\n        self.fn = fn\n    def run(self):\n        self.fn()\n")
        body = ("    def test_alias(self):\n        t = _alias(_loop)\n        self.assertTrue(False)\n"
                "    def test_alias_once(self):\n        t = _alias(_once)\n        self.assertTrue(False)\n"
                "    def test_alias_param(self, cb=None):\n        t = _alias(cb)\n        self.assertTrue(False)\n"
                "    def test_sub(self):\n        t = _sub([_loop])\n        self.assertTrue(False)\n"
                "    def test_sub_once(self):\n        t = _sub([_once, _once])\n        self.assertTrue(False)\n"
                "    def test_key(self):\n        t = _key({'fn': _loop})\n        self.assertTrue(False)\n"
                "    def test_each(self):\n        t = _each([_loop, _once])\n        self.assertTrue(False)\n"
                "    def test_comp(self):\n        t = _comp((_once, _loop))\n        self.assertTrue(False)\n"
                "    def test_or(self):\n        t = _or(_loop)\n        self.assertTrue(False)\n"
                "    def test_or_once(self):\n        t = _or(_once)\n        self.assertTrue(False)\n"
                "    def test_ifexp(self):\n        t = _ifexp(_loop, True)\n        self.assertTrue(False)\n"
                "    def test_star(self):\n        t = _star([_loop])\n        self.assertTrue(False)\n"
                "    def test_kwonly(self):\n        t = _kwonly(fn=_loop)\n        self.assertTrue(False)\n"
                "    def test_partial(self):\n        t = _partial(_loop)\n        self.assertTrue(False)\n"
                "    def test_partial_bare(self):\n        t = _partial_bare(_loop)\n        self.assertTrue(False)\n"
                "    def test_getattr(self):\n        t = _getattr(_F(_loop), 'run')\n        self.assertTrue(False)\n"
                "    def test_getattr_lit(self):\n        t = _getattr_lit(_F(_loop))\n        self.assertTrue(False)\n"
                "    def test_varargs(self):\n        t = _varargs(_loop)\n        self.assertTrue(False)\n"
                "    def test_kwstar(self):\n        t = _kwstar(fn=_loop)\n        self.assertTrue(False)\n"
                "    def test_kwitems(self):\n        t = _kwitems(fn=_loop)\n        self.assertTrue(False)\n"
                "    def test_nodes(self):\n        t = _nodes({'rev': 1, 'nodes': {}})\n        self.assertTrue(False)\n"
                "    def test_rec(self):\n        t = _rec(_acc())\n        self.assertTrue(False)\n"
                "    def test_self_attr(self):\n        f = _F(_loop)\n        t = threading.Thread(target=f.run); t.start()\n        self.assertTrue(False)\n"
                "    def test_self_attr_param(self, cb=None):\n        f = _F(cb)\n        t = threading.Thread(target=f.run); t.start()\n        self.assertTrue(False)\n"
                "    def test_ctor_sub(self):\n        def run(fns):\n            fns[0]()\n        threading.Thread(target=run, args=([_loop],)).start()\n        self.assertTrue(False)\n"
                "    def test_ctor_alias(self):\n        def run(fn):\n            g = fn\n            g()\n        threading.Thread(target=run, args=(_loop,)).start()\n        self.assertTrue(False)\n")
        rows, (tails, unread, stale, bounded), _p = self._census(body, head=self.HEAD.replace("class T(", helpers + "class T("))
        by = {}
        for st, sh, w in rows:
            by.setdefault(w.split(".")[1] if "." in w else w, []).append((st.target, st.kind, st.why, sh))
        for helper in ("_alias", "_sub", "_key", "_each", "_comp", "_or", "_ifexp", "_star", "_kwonly", "_partial", "_partial_bare", "_getattr",
                       "_getattr_lit", "_varargs", "_kwstar", "_nodes", "_rec"):
            self.assertNotIn(helper, by, "%s's own row is unreadable and tail-only: classed at its callers" % helper)
        loop = "a while loop | %s"
        expect = {
            "alias": ("go", "loop", loop % "fn of _alias is `_loop` handed in by the caller", "tail-only"),
            "alias_once": ("go", "bounded", "no loop, no untimed wait | fn of _alias is `_once` handed in by the caller", "tail-only"),
            "alias_param": ("go", KIND_UNREAD, "a parameter (cb): what the caller hands in is not read here | fn of _alias is `cb` handed in by the caller", "tail-only"),
            "sub": ("go", "loop", loop % "fns[] of _sub is `[_loop]`[] handed in by the caller", "tail-only"),
            "sub_once": ("go", "bounded", "no loop, no untimed wait | fns[] of _sub is `[_once, _once]`[] handed in by the caller", "tail-only"),
            "key": ("go", "loop", loop % "kw[] of _key is `{'fn': _loop}`[] handed in by the caller", "tail-only"),
            "each": ("go", "loop", loop % "fns[] of _each is `[_loop, _once]`[] handed in by the caller", "tail-only"),
            "comp": ("go", "loop", loop % "fns[] of _comp is `(_once, _loop)`[] handed in by the caller", "tail-only"),
            "or": ("go", "loop", loop % "fn of _or is `_loop` handed in by the caller", "tail-only"),
            "or_once": ("go", "bounded", "no loop, no untimed wait | fn of _or is `_once` handed in by the caller", "tail-only"),
            "ifexp": ("go", "loop", loop % "fn of _ifexp is `_loop` handed in by the caller", "tail-only"),
            "star": ("go", "loop", loop % "fns[] of _star is `[_loop]`[] handed in by the caller", "tail-only"),
            "kwonly": ("go", "loop", loop % "fn of _kwonly is `_loop` handed in by the caller", "tail-only"),
            "partial": ("go", "loop", loop % "fn of _partial is `_loop` handed in by the caller", "tail-only"),
            "partial_bare": ("go", "loop", loop % "fn of _partial_bare is `_loop` handed in by the caller", "tail-only"),
            "getattr": ("go", KIND_UNREAD, "an attribute of `_F(_loop)` named by a value the walk does not read (a parameter of _getattr) | "
                                           "obj.<name> of _getattr is `_F(_loop)`.<name> handed in by the caller", "tail-only"),
            "getattr_lit": ("go", "loop", loop % "fn of __init__ is `_loop` handed in at the construction | obj.run of _getattr_lit is `_F(_loop)`.run handed in by the caller", "tail-only"),
            "varargs": ("go", KIND_UNREAD, "calls fns[0], fns a parameter of _varargs: what the caller hands in is not read here", "tail-only"),
            "kwstar": ("go", KIND_UNREAD, "calls kw['fn'], kw a parameter of _kwstar: what the caller hands in is not read here", "tail-only"),
            "kwitems": ("go", "bounded", "no loop, no untimed wait", "tail-only"),
            "self_attr": ("f.run", "loop", loop % "fn of __init__ is `_loop` handed in at the construction", "tail-only"),
            "self_attr_param": ("f.run", KIND_UNREAD, "a parameter (cb): what the caller hands in is not read here | fn of __init__ is `cb` handed in at the construction", "tail-only"),
            "ctor_sub": ("run", "loop", loop % "fns[] of run is `[_loop]`[] handed in at the construction", "tail-only"),
            "ctor_alias": ("run", "loop", loop % "fn of run is `_loop` handed in at the construction", "tail-only"),
        }
        for name, row in expect.items():
            self.assertEqual(by["test_" + name], [row], name)
        for name in ("nodes", "rec"):
            self.assertEqual([r[1:2] + r[3:] for r in by["test_" + name]], [("bounded", "tail-only")], (name, by["test_" + name]))
            self.assertIn("handed in by the caller", by["test_" + name][0][2], name)
            self.assertTrue(bounded_reason_is_read(by["test_" + name][0][2]), by["test_" + name][0][2])
        self.assertEqual(sorted(w.split(".")[1] for s, w in unread), sorted(["test_alias_param", "test_getattr", "test_varargs", "test_kwstar", "test_self_attr_param"]))
        self.assertEqual(sorted(w.split(".")[1] for s, w in bounded), sorted(["test_alias_once", "test_sub_once", "test_or_once", "test_kwitems", "test_nodes", "test_rec"]))
        self.assertEqual(sorted(w.split(".")[1] for s, w in tails),
                         sorted("test_" + n for n, r in expect.items() if r[1] == "loop"))
        self.assertTrue(all(bounded_reason_is_read(s.why) for s, w in bounded), [s.why for s, w in bounded])

    def test_a_cleanups_timed_join_alone_is_not_an_outright_loops_stop(self):
        """Round 2 of PR 891's review (2026-09-22), the timed-join decision for cleanups. For a LOOP the walk read outright, a
        cleanup whose only stop is a TIMED join (`self.addCleanup(t.join, 5)`, a lambda joining a list with a timeout, a
        local def whose body is a timed join, registered before or right after the start) is not the stop: the row is
        tail-only (named). An untimed join (`self.addCleanup(t.join)`), a release beside the join (`def end(): stop.set();
        t.join(5)`), the loops' seam set beside it (a product loop), a sentinel put into the queue the loop reads
        (`q.put_nowait(None)`) or a shutdown of the socket a drain reads (`peer.shutdown(...)`) is. A bounded thread's
        timed-join cleanup counts as before (its join is a convenience either way); a loop found only in a product callee
        (indirect) is read as bounded for this rule, as in the body; and for a thread of UNREADABLE kind the timed join is
        ACCEPTED (the documented acceptance: no loop to release, a bounded wait on every exit path)."""
        product = "def spin():\n    while True:\n        pass\ndef _producer():\n    while True:\n        pass\n"
        head = self.HEAD.replace("class T(", "km = load_source('fake_kernel', 'fake_kernel.py')\nclass T(")
        body = ("    def test_timed(self):\n        t = threading.Thread(target=_loop)\n        self.addCleanup(t.join, 5)\n        t.start()\n        self.assertTrue(False)\n"
                "    def test_untimed(self):\n        t = threading.Thread(target=_loop)\n        self.addCleanup(t.join)\n        t.start()\n        self.assertTrue(False)\n"
                "    def test_with_release(self):\n        stop = threading.Event()\n        def run():\n            while not stop.is_set():\n                time.sleep(0.01)\n"
                "        t = threading.Thread(target=run)\n        def end():\n            stop.set()\n            t.join(5)\n        self.addCleanup(end)\n        t.start()\n        self.assertTrue(False)\n"
                "    def test_lambda_timed(self):\n        ts = [threading.Thread(target=_loop) for _ in range(2)]\n        self.addCleanup(lambda: [t.join(2) for t in ts])\n"
                "        for t in ts:\n            t.start()\n        self.assertTrue(False)\n"
                "    def test_end_def_timed(self):\n        t = threading.Thread(target=_loop)\n        def end():\n            t.join(5)\n        self.addCleanup(end)\n        t.start()\n        self.assertTrue(False)\n"
                "    def test_after_start_timed(self):\n        t = threading.Thread(target=_loop)\n        t.start()\n        self.addCleanup(t.join, 5)\n        self.assertTrue(False)\n"
                "    def test_bounded_timed(self):\n        t = threading.Thread(target=_once)\n        self.addCleanup(t.join, 5)\n        t.start()\n        self.assertTrue(False)\n"
                "    def test_unreadable_timed(self, cb=None):\n        t = threading.Thread(target=cb)\n        self.addCleanup(t.join, 5)\n        t.start()\n        self.assertTrue(False)\n"
                "    def test_indirect_timed(self):\n        t = threading.Thread(target=lambda: km.spin())\n        self.addCleanup(t.join, 5)\n        t.start()\n        self.assertTrue(False)\n"
                "    def test_seam(self):\n        t = threading.Thread(target=km._producer)\n        self.addCleanup(lambda: (km._LOOPS_STOP.set(), t.join(5)))\n        t.start()\n        self.assertTrue(False)\n"
                "    def test_sentinel(self):\n        q = queue.Queue()\n        def run():\n            while True:\n                if q.get() is None:\n                    return\n"
                "        t = threading.Thread(target=run)\n        self.addCleanup(lambda: (q.put_nowait(None), t.join(5)))\n        t.start()\n        self.assertTrue(False)\n"
                "    def test_sentinel_body(self):\n        q = queue.Queue()\n        def run():\n            while True:\n                if q.get() is None:\n                    return\n"
                "        t = threading.Thread(target=run)\n        t.start()\n        q.put_nowait(None); t.join(5)\n        self.assertTrue(False)\n"
                "    def test_drain_shutdown(self):\n        peer = socket.socket()\n        got = bytearray()\n        def drain():\n            while len(got) < 10:\n"
                "                b = peer.recv(100)\n                if not b:\n                    return\n                got.extend(b)\n"
                "        t = threading.Thread(target=drain)\n        def end():\n            try:\n                peer.shutdown(socket.SHUT_RDWR)\n"
                "            except OSError:\n                pass\n            t.join(10)\n        self.addCleanup(end)\n        t.start()\n        self.assertTrue(False)\n"
                "    def test_drain_timed(self):\n        peer = socket.socket()\n        got = bytearray()\n        def drain():\n            while len(got) < 10:\n"
                "                b = peer.recv(100)\n                if not b:\n                    return\n                got.extend(b)\n"
                "        t = threading.Thread(target=drain)\n        self.addCleanup(t.join, 10)\n        t.start()\n        self.assertTrue(False)\n")
        head = head.replace("import unittest\n", "import unittest\nimport queue\nimport socket\n")
        rows, (tails, unread, stale, bounded), _p = self._census(body, head=head, product={"fake_kernel": product})
        by = {w.split(".")[1]: (s.kind, sh) for s, sh, w in rows}
        self.assertEqual(by["test_timed"], ("loop", "tail-only"))
        self.assertEqual(by["test_untimed"], ("loop", "cleanup-before-start"))
        self.assertEqual(by["test_with_release"], ("loop", "cleanup-before-start"))
        self.assertEqual(by["test_lambda_timed"], ("loop", "tail-only"))
        self.assertEqual(by["test_end_def_timed"], ("loop", "tail-only"))
        self.assertEqual(by["test_after_start_timed"], ("loop", "tail-only"))
        self.assertEqual(by["test_bounded_timed"], ("bounded", "cleanup-before-start"))
        self.assertEqual(by["test_unreadable_timed"], (KIND_UNREAD, "cleanup-before-start"), "the documented acceptance for the unreadable kind")
        self.assertEqual(by["test_indirect_timed"], ("loop", "cleanup-before-start"))
        self.assertEqual(by["test_seam"], ("loop", "cleanup-before-start"))
        self.assertEqual(by["test_sentinel"], ("loop", "cleanup-before-start"))
        self.assertEqual(by["test_sentinel_body"], ("loop", "stop-before-first-assertion"))
        self.assertEqual(by["test_drain_shutdown"], ("loop", "cleanup-before-start"))
        self.assertEqual(by["test_drain_timed"], ("loop", "tail-only"))
        self.assertEqual(sorted(w.split(".")[1] for s, w in tails), ["test_after_start_timed", "test_drain_timed", "test_end_def_timed", "test_lambda_timed", "test_timed"])
        self.assertEqual((unread, bounded, stale), ([], [], []))

    def test_a_cleanup_that_runs_a_helper_modules_function_is_read_by_the_helpers_body_bound_to_the_arguments(self):
        """THE HELPER ROAD (round 2 of PR 891's review, 2026-09-22). A cleanup that runs a function of a helper module under
        tests/ is read by that function's body with the parameters standing for the arguments handed. Proven on a helper
        named `settle`, a name that says no stop word, so the name rule cannot pass it: through the registration
        (`self.addCleanup(settle, go, ts, 5)`), a lambda, a local def, the imported module and the dotted package spelling,
        each a cleanup-before-start of the list it is handed; handed None for the release and an outright loop, the body is
        a timed join alone and the row is tail-only (named); handed a list the test did not start, the body mentions no
        thread of this start and the row is tail-only; for an unreadable kind the timed join through the helper is the
        documented acceptance. The tree's own helper, tests/thread_ends.py's join_started, read from its source, gives the
        same verdicts with a name that also says join."""
        helper = ("def settle(release, threads, timeout):\n    if release is not None:\n        release.set()\n"
                  "    for t in threads:\n        if t.ident is not None:\n            t.join(timeout)\n")
        with open(os.path.join(HERE, "thread_ends.py"), encoding="utf-8") as f:
            real = f.read()
        head = self.HEAD.replace("import unittest\n", "import unittest\nimport helper_mod\nimport tests.helper_mod\nfrom helper_mod import settle\n"
                                                    "from tests.thread_ends import join_started\n")
        loop = "        go = threading.Event()\n        ts = [threading.Thread(target=_loop) for _ in range(2)]\n"
        starts = "        for t in ts:\n            t.start()\n        self.assertTrue(False)\n"
        body = ("    def test_registration(self):\n" + loop + "        self.addCleanup(settle, go, ts, 5)\n" + starts +
                "    def test_lambda(self):\n" + loop + "        self.addCleanup(lambda: settle(go, ts, 5))\n" + starts +
                "    def test_local_def(self):\n" + loop + "        def after():\n            settle(go, ts, timeout=5)\n        self.addCleanup(after)\n" + starts +
                "    def test_module_road(self):\n" + loop + "        self.addCleanup(helper_mod.settle, go, ts, 5)\n" + starts +
                "    def test_dotted_road(self):\n" + loop + "        self.addCleanup(lambda: tests.helper_mod.settle(go, ts, 5))\n" + starts +
                "    def test_none_release(self):\n" + loop + "        self.addCleanup(settle, None, ts, 5)\n" + starts +
                "    def test_other_list(self):\n" + loop + "        others = [threading.Thread(target=_once)]\n        self.addCleanup(settle, go, others, 5)\n" + starts +
                "    def test_unreadable_none_release(self, cb=None):\n        ts = [threading.Thread(target=cb) for _ in range(2)]\n"
                "        self.addCleanup(settle, None, ts, 5)\n" + starts +
                "    def test_real_helper(self):\n" + loop + "        self.addCleanup(join_started, go, ts, 5)\n" + starts +
                "    def test_real_helper_none(self):\n" + loop + "        self.addCleanup(join_started, None, ts, 5)\n" + starts)
        rows, (tails, unread, stale, bounded), _p = self._census(body, head=head, helpers={"helper_mod": helper, "thread_ends": real})
        by = {}
        for s, sh, w in rows:
            by.setdefault(w.split(".")[1], set()).add((s.kind, sh))
        for name in ("registration", "lambda", "local_def", "module_road", "dotted_road", "real_helper"):
            self.assertEqual(by["test_" + name], {("loop", "cleanup-before-start")}, (name, by["test_" + name]))
        for name in ("none_release", "other_list", "real_helper_none"):
            self.assertEqual(by["test_" + name], {("loop", "tail-only")}, (name, by["test_" + name]))
        self.assertEqual(by["test_unreadable_none_release"], {(KIND_UNREAD, "cleanup-before-start")}, "the documented acceptance")
        self.assertEqual(sorted({w.split(".")[1] for s, w in tails}), ["test_none_release", "test_other_list", "test_real_helper_none"])
        self.assertEqual((unread, bounded, stale), ([], [], []))
        self.assertEqual(len(rows), 10, [(s.recv_shown, sh, w) for s, sh, w in rows])   # one start statement per test

    def test_a_cleanup_that_joins_a_list_of_threads_inline_is_named_by_the_list_join_pin(self):
        """The list-join pin (round 2 of PR 891's review, 2026-09-22) on a planted module: an inline comprehension join in the
        registration (`self.addCleanup(lambda: [t.join(5) for t in ts])`), a generator expression, a for in a local def, a
        for over a tuple with the ident guard written inline, a method of the class and a module function are each named
        with their unit and text, and so are (the ninth pass, the refuter's nit) a for with a tuple target over enumerate
        (`for i, t in enumerate(ts): t.join(5)`), a comprehension that joins the list by index (`ts[i].join(3) for i in
        range(len(ts))`) and a for that joins `ts[i]` by the enumerate index; a cleanup through tests/thread_ends.py's
        join_started, by the registration or by a lambda, a cleanup joining single threads and subscript joins written out
        one by one (`(ts[0].join(2), ts[1].join(2))`, the shape of the unguarded contrast in tests/test_codex_backend.py) are
        not."""
        with open(os.path.join(HERE, "thread_ends.py"), encoding="utf-8") as f:
            real = f.read()
        head = self.HEAD.replace("import unittest\n", "import unittest\nfrom tests.thread_ends import join_started\n")
        head = head.replace("class T(", "def _stop_all(ts):\n    [t.join(1) for t in ts]\n\nclass T(")
        pair = "        ts = [threading.Thread(target=_once) for _ in range(2)]\n"
        starts = "        for t in ts:\n            t.start()\n        self.assertTrue(False)\n"
        body = ("    def _end(self):\n        for t in self.ts:\n            t.join()\n"
                "    def test_comprehension(self):\n" + pair + "        self.addCleanup(lambda: [t.join(5) for t in ts])\n" + starts +
                "    def test_genexp(self):\n" + pair + "        self.addCleanup(lambda: list(t.join(1) for t in ts))\n" + starts +
                "    def test_for_def(self):\n" + pair + "        def end():\n            for t in ts:\n                t.join(2)\n        self.addCleanup(end)\n" + starts +
                "    def test_tuple_for(self):\n        a, b = threading.Thread(target=_once), threading.Thread(target=_once)\n"
                "        def end():\n            for t in (a, b):\n                if t.ident is not None:\n                    t.join(5)\n        self.addCleanup(end)\n"
                "        a.start(); b.start()\n        self.assertTrue(False)\n"
                "    def test_method(self):\n        self.ts = [threading.Thread(target=_once) for _ in range(2)]\n        self.addCleanup(self._end)\n"
                "        for t in self.ts:\n            t.start()\n        self.assertTrue(False)\n"
                "    def test_module_fn(self):\n" + pair + "        self.addCleanup(_stop_all, ts)\n" + starts +
                "    def test_enumerate(self):\n" + pair + "        def end():\n            for i, t in enumerate(ts):\n                t.join(5)\n        self.addCleanup(end)\n" + starts +
                "    def test_index(self):\n" + pair + "        self.addCleanup(lambda: [ts[i].join(3) for i in range(len(ts))])\n" + starts +
                "    def test_enumerate_index(self):\n" + pair + "        def end():\n            for i, _t in enumerate(ts):\n                ts[i].join()\n        self.addCleanup(end)\n" + starts +
                "    def test_indexed_out(self):\n" + pair + "        self.addCleanup(lambda: (ts[0].join(2), ts[1].join(2)))\n" + starts +
                "    def test_helper(self):\n" + pair + "        self.addCleanup(join_started, None, ts, 5)\n" + starts +
                "    def test_helper_lambda(self):\n" + pair + "        go = threading.Event()\n        self.addCleanup(lambda: join_started(go, ts, 5))\n" + starts +
                "    def test_single(self):\n        a, b = threading.Thread(target=_once), threading.Thread(target=_once)\n"
                "        self.addCleanup(a.join, 5)\n        self.addCleanup(lambda: (a.join(2), b.join(2)))\n        a.start(); b.start()\n        self.assertTrue(False)\n")
        rows, (tails, unread, stale, bounded), _p = self._census(body, head=head, helpers={"thread_ends": real})
        d = os.path.join(ROOT, os.path.dirname(_p))
        found = list_join_cleanups([os.path.join(ROOT, _p)], helpers={"thread_ends": os.path.join(d, "thread_ends.py")})
        self.assertEqual(sorted((u, t) for _f, _l, u, t in found),
                         sorted([("T.test_comprehension", "t.join(5)"), ("T.test_genexp", "t.join(1)"), ("T.test_for_def", "t.join(2)"),
                                 ("T.test_tuple_for", "t.join(5)"), ("T.test_method", "t.join()"), ("T.test_module_fn", "t.join(1)"),
                                 ("T.test_enumerate", "t.join(5)"), ("T.test_index", "ts[i].join(3)"), ("T.test_enumerate_index", "ts[i].join()")]), found)
        self.assertTrue(all(f == _p for f, _l, _u, _t in found), found)
        self.assertEqual(sorted(w.split(".")[1] for s, sh, w in rows if sh == "cleanup-before-start"),
                         sorted(["test_comprehension", "test_genexp", "test_for_def", "test_tuple_for", "test_tuple_for", "test_method",
                                 "test_module_fn", "test_enumerate", "test_index", "test_enumerate_index", "test_indexed_out",
                                 "test_helper", "test_helper_lambda", "test_single", "test_single"]),   # a.start(); b.start(): two rows
                         [(w, sh) for s, sh, w in rows])
        self.assertEqual((tails, unread, stale), ([], [], []))

    def test_no_displayed_or_compared_target_text_is_rendered_by_ast_unparse(self):
        """The text a row displays, an ALLOW entry is keyed on or a plant compares is the source segment (_text), never
        ast.unparse's rendering, which differs between interpreters (3.10: `lambda : f()`). This parses the census itself
        and asserts the functions calling ast.unparse are exactly UNPARSE_ROADS, each a name match between two texts
        rendered under one interpreter, with its reason; a new use must be registered there."""
        _src, tree = PC.source_and_tree(__file__)
        found = {}

        def visit(node, qual):
            for child in ast.iter_child_nodes(node):
                q = qual
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    q = (qual + "." if qual else "") + child.name
                elif isinstance(child, ast.ClassDef):
                    q = child.name
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute) and child.func.attr == "unparse" \
                        and isinstance(child.func.value, ast.Name) and child.func.value.id == "ast":
                    found.setdefault(qual, []).append(child.lineno)
                visit(child, q)
        visit(tree, "")
        self.assertEqual(sorted(found), sorted(UNPARSE_ROADS), "an ast.unparse call outside the registered roads: %r" % found)
        for road in ("_text", "_Start.describe", "_kind", "_expr_kind", "_product_kind", "_library_kind", "_unread_reason", "_report"):
            self.assertNotIn(road, found)
        self.assertEqual(_text(ast.parse("x = (lambda:\n    f.run())").body[0].value, type("M", (), {"src": "x = (lambda:\n    f.run())"})()),
                         "lambda: f.run()", "the author's text, whitespace collapsed")


if __name__ == "__main__":
    if "--table" in sys.argv or "--tail" in sys.argv:
        tree = tree_census()
        rows, extras = tree.rows, tree.extras
        print(_report(rows, only_tail="--tail" in sys.argv))
        tails, unread, stale, bounded = tail_only(rows)
        from collections import Counter
        info = extras["product_starts"]
        if "--tail" not in sys.argv:
            print("\n%s rows (informational: threads the PRODUCT starts on a test's call; the product's to end, never pinned):" % PRODUCT_START)
            print(_report_info(info))
        print("\nmodules read: %d (the non-recursive listing of tests/test_*.py)" % extras["modules"])
        print("start rows: %d" % len(rows))
        print("shapes:", dict(Counter(s for _st, s, _w in rows)))
        print("kinds:", dict(Counter(st.kind for st, _s, _w in rows)))
        print("%s rows: %d %s" % (PRODUCT_START, len(info), dict(Counter(r.shape for r in info))))
        print("runtime oracle (thread_census / wait_for_census) imported or called by %d of %d modules: %s"
              % (len(extras["oracle"]), extras["modules"], ", ".join(extras["oracle"])))
        print("pinned tail-only (not excused): %d, unreadable: %d, stale allow: %d, bounded tail-only (excused): %d, allow entries: %d"
              % (len(tails), len(unread), len(stale), len(bounded), len(ALLOW)))
        sys.exit(0)
    unittest.main()
