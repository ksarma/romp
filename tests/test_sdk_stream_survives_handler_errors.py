#!/usr/bin/env python3
"""A handler failure on ONE streamed message must not end a session's CLI, and the live tail the two
threads share must be safe to sweep (2026-09-06).

What happened live: a session's receive loop died on `KeyError: '<message uuid>'` — the only line
the journal had — and the client teardown that followed closed its CLI mid-work (an in-flight turn,
a Workflow run with four subagents and a background agent), then the session came back as a crash
resume. The KeyError came from a live-tail sweep at the ResultMessage settle (retire_live_work)
racing the kernel thread's prune_live on the same unlocked dict: `for k in list(d.keys()): a = d[k]`
with the kernel thread deleting the just-landed reply between the snapshot and the read. The review
then found the same unlocked dict raising RuntimeError out of the pusher's build (_persist_echoes)
and out of the session thread at reconnect (_mark_dropped_echoes), and the two-step
`if not d: _live.pop(sid)` orphaning an atom stashed between the steps. Three fixes, all covered here:

  * the live tail has ONE lock (SdkBackend._live_lock): every stash, every pop, the sid-level pop and
    every iterating read take it; sweeps walk a snapshot taken under it; the emptiness check and the
    sid-level pop are one step; the lock is never held across I/O or a callback. Real-thread hammers
    below drive the shapes the reviewers' probes reproduced on the lock-free tail;
  * the sweeps still walk a snapshot and pop with a default (belt-and-braces), and prune_live /
    _evict_live_overflow report a key that vanishes anyway once per site per kernel life — under the
    lock that means a mutator bypassed it;
  * the receive loop (_drain) runs each message through _handle_stream_message, which keeps a
    handler's exception to that message — logged with its type, the message kind, a bounded frame
    chain and what that class of message losing its handling costs, deduped in the error-center ring
    — with the reporter itself guarded and the settle's turn-end plumbing in a finally; a fault of
    the stream itself still ends the loop as before.

Every id here is synthetic (the placeholder uuid family); no message content is real.
"""
import asyncio
import inspect
import os
import sys
import tempfile
import threading
import time
import traceback
import unittest
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()       # hermetic state BEFORE the load (import-time root)
os.environ.pop("ROMP_STATE_DIR", None)
sb = SourceFileLoader("romp_sdk_backend_streamsurvive",
                      os.path.join(BIN, "romp_sdk_backend.py")).load_module()

SID = "11111111-2222-3333-4444-aaaaaaaaaaa1"           # this module's own synthetic sid
UNKNOWN_SID = "11111111-2222-3333-4444-bbbbbbbbbbb2"   # a session id the kernel never registered
MSG_UUID = "11111111-2222-3333-4444-ccccccccccc3"      # a message uuid (the live tail's key kind)


# ---- message doubles: the SDK's shapes, by class name (msg_to_atom / _on_message key on them) ----
class _TextBlock:
    def __init__(self, text): self.text = text
class _ToolUseBlock:
    def __init__(self, id, name, inp): self.id, self.name, self.input = id, name, inp
class _AssistantMessage:
    def __init__(self, content, model="claude-x", uuid="a1", parent_tool_use_id=None):
        self.content, self.model, self.uuid = content, model, uuid
        self.parent_tool_use_id, self.stop_reason, self.error = parent_tool_use_id, "end_turn", None
class _UserMessage:
    def __init__(self, content, uuid="u1", parent_tool_use_id=None):
        self.content, self.uuid, self.parent_tool_use_id, self.tool_use_result = content, uuid, parent_tool_use_id, None
class _ResultMessage:
    uuid = "r1"
    num_turns = 1
class _SystemMessage:
    def __init__(self, subtype, data=None, uuid=None):
        self.subtype, self.data, self.uuid = subtype, (data or {}), uuid
class _HookEventMessage(_SystemMessage):
    """The SDK's HookEventMessage IS a SystemMessage subclass (types.py) — so hook_started /
    hook_response reach the SystemMessage catch-all exactly as the new subtypes did live."""
class _StreamEvent:
    uuid = "se1"
_TextBlock.__name__ = "TextBlock"; _ToolUseBlock.__name__ = "ToolUseBlock"
_AssistantMessage.__name__ = "AssistantMessage"; _UserMessage.__name__ = "UserMessage"
_ResultMessage.__name__ = "ResultMessage"; _SystemMessage.__name__ = "SystemMessage"
_HookEventMessage.__name__ = "HookEventMessage"; _StreamEvent.__name__ = "StreamEvent"


class _RacyTail(dict):
    """A live tail whose snapshot goes stale by one key: right after a sweep takes its keys()/items()
    snapshot, `victim` is removed — a mutator changing the dict without the lock, which is the shape
    that killed the session live. The old `a = d[k]` raises KeyError(victim) on it; a snapshot-and-pop
    sweep does not."""
    def __init__(self, *a, victim=None, **k):
        super().__init__(*a, **k)
        self.victim = victim
    def keys(self):
        ks = list(super().keys()); self._other_thread_prunes(); return ks
    def items(self):
        it = list(super().items()); self._other_thread_prunes(); return it
    def _other_thread_prunes(self):
        if self.victim in self:
            dict.__delitem__(self, self.victim)


def _backend(lines=None, **kw):
    d = tempfile.mkdtemp()
    log = (lambda m: lines.append(str(m))) if lines is not None else (lambda *a, **k: None)
    return sb.SdkBackend(d, "/bin/true", lambda *a, **k: None, log=log, **kw)


def _problems(be):
    """The backend's problem ring, minus the construction-time line this venv always adds (no SDK
    installed here → 'claude_agent_sdk is NOT importable'), which is not what these tests observe."""
    return [p["text"] for p in be.problems() if "claude_agent_sdk" not in p["text"]]


def _session(be):
    s = sb.SdkSession(be, {"sid": SID, "name": "web", "cwd": "/tmp"})
    async def _noop(): pass
    s._do_refresh_context = _noop
    s._do_refresh_usage = _noop
    return s


def _work(uuid, t):
    return {"type": "assistant", "uuid": uuid, "t": t,
            "message": {"role": "assistant", "content": [{"type": "tool_use", "id": "toolu_" + uuid, "name": "Bash", "input": {}}]}}


def _text_atom(uuid, t):
    return {"type": "assistant", "uuid": uuid, "t": t,
            "message": {"role": "assistant", "content": [{"type": "text", "text": "a reply the user watched"}]}}


def _echo(key, text, t, **flags):
    a = {"type": "user", "uuid": key, "session_id": SID, "t": t, "parentUuid": None, "author": "human",
         "_echo_text": text, "message": {"role": "user", "content": [{"type": "text", "text": text}]}}
    a.update(flags)
    return a


def _chain(e):
    return " > ".join("%s:%d %s" % (os.path.basename(f.filename), f.lineno, f.name)
                      for f in traceback.extract_tb(e.__traceback__))


class LiveTailSweepsSurviveAConcurrentPrune(unittest.TestCase):
    """The scripted race: a dict subclass drops a key between a sweep's snapshot and its pop. Under the
    lock this can only be a mutator bypassing it, and the sweeps still tolerate it."""
    def setUp(self):
        sb.SdkBackend._live_tail_race_seen.clear()     # per-kernel-life set; a fresh life per test

    def _problems(self, be, site):
        return [t for t in _problems(be) if t.startswith("live tail (%s)" % site)]

    def test_retire_live_work_survives_the_settle_race_and_does_not_report_it(self):
        """THE reported failure: the settle sweep held a snapshot of keys while the kernel thread pruned
        the just-landed reply — `a = d[k]` raised KeyError('<message uuid>') out of _on_message. The
        sweep tolerates the vanished key. It does NOT report it: retire_live_work releases the lock for
        the orphan salvage's transcript read, so a key gone at its pop is a landing prune_live filed in
        that window — legitimate, and a problem line for it would be a false alarm on every such settle."""
        be = _backend()
        be._live[SID] = _RacyTail({MSG_UUID: _work(MSG_UUID, 5), "w2": _work("w2", 6)}, victim=MSG_UUID)
        be.retire_live_work(SID)                        # raised KeyError before the fix
        self.assertNotIn(SID, be._live, "every work atom retired, the vanished one included")
        self.assertEqual(self._problems(be, "retire_live_work"), [], "not a fault at this site")
        self.assertEqual(_problems(be), [])

    def test_prune_live_survives_a_key_taken_from_under_it_and_reports_once(self):
        """prune_live runs wholly under the lock, so a key that vanishes anyway means a mutator bypassed
        it — reported once per site per kernel life, naming the key's KIND and never its value."""
        be = _backend()
        be._live[SID] = _RacyTail({MSG_UUID: _work(MSG_UUID, 5), "w2": _work("w2", 6)}, victim=MSG_UUID)
        be.prune_live(SID, {MSG_UUID, "w2"})            # both landed; the victim vanished mid-sweep
        self.assertNotIn(SID, be._live)
        self.assertEqual(len(self._problems(be, "prune_live")), 1, "the bypass is reported")
        be._live[SID] = _RacyTail({"w3": _work("w3", 7)}, victim="w3")
        be.prune_live(SID, {"w3"})
        self.assertEqual(len(self._problems(be, "prune_live")), 1, "…ONCE per site per kernel life")
        txt = self._problems(be, "prune_live")[0]
        self.assertIn("message-uuid key", txt, "the line names the key KIND")
        self.assertIn("_live_lock", txt, "…and what a vanished key means now: the lock was bypassed")
        self.assertNotIn(MSG_UUID, txt, "…never the key's value")

    def test_evict_live_overflow_survives_a_prune_under_it(self):
        d = _RacyTail({("w%03d" % i): _work("w%03d" % i, i) for i in range(sb.LIVE_TAIL_CAP + 5)}, victim="w000")
        vanished = sb._evict_live_overflow(d)          # raised KeyError('w000') before the fix
        self.assertLessEqual(len(d), sb.LIVE_TAIL_CAP, "still bounded")
        self.assertEqual(vanished, 1, "the sweep counts the key another thread took, for the caller to report")
        self.assertEqual(sb._evict_live_overflow(dict(d)), 0, "a quiet sweep reports nothing")

    def test_forward_reports_an_evict_race_once(self):
        be = _backend()
        s = _session(be)
        tail = _RacyTail({("w%03d" % i): _work("w%03d" % i, i) for i in range(sb.LIVE_TAIL_CAP + 2)}, victim="w000")
        be._live[SID] = tail
        be._forward(s, _AssistantMessage([_TextBlock("hi")], uuid="new1"))
        self.assertIn("new1", tail, "the new atom landed")
        self.assertLessEqual(len(tail), sb.LIVE_TAIL_CAP)
        self.assertEqual(len(self._problems(be, "_evict_live_overflow")), 1)

    def test_the_result_settle_survives_a_pruned_live_tail(self):
        """The reproduction through the real handler: a ResultMessage settles the turn → retire_live_work
        → the racy tail. Before the fix this raised out of _on_message; the receive loop ended on it."""
        be = _backend()
        s = _session(be)
        be._live[SID] = _RacyTail({MSG_UUID: _work(MSG_UUID, 5)}, victim=MSG_UUID)
        s.inflight = 1

        async def run():
            s._on_message(_ResultMessage(), _AssistantMessage, _ResultMessage, _SystemMessage)
            await asyncio.sleep(0)
        asyncio.run(run())                              # no KeyError
        self.assertEqual(s.inflight, 0, "the turn settled")
        self.assertNotIn(SID, be._live)


class TheLiveTailLock(unittest.TestCase):
    """REAL threads on plain dicts, with the interpreter's switch interval lowered so the interleavings
    the GIL permits show up within a second: one thread plays the session's loop (stash work atoms,
    retire them at the settle, mark dropped echoes at a reconnect), the other plays the kernel (stash
    an echo at send, land it in prune_live, mirror it). On the lock-free tail the reviewers' probes
    raised RuntimeError out of prune_live on 1412 of 1500 calls, out of _mark_dropped_echoes on 8 of
    3000, and orphaned 343 of 60000 stashes in the sid-level pop's window; under the lock nothing
    raises and nothing is orphaned. Bounded by a call count on the kernel side and a wall-clock cap."""
    SEEDED = 60          # unlanded echoes sitting in the tail (the _persist_echoes walk's length)
    CAP_S = 6.0          # a hammer that runs longer than this stops and still asserts on what it saw

    def setUp(self):
        self._interval = sys.getswitchinterval()
        sys.setswitchinterval(1e-6)
        sb.SdkBackend._live_tail_race_seen.clear()

    def tearDown(self):
        sys.setswitchinterval(self._interval)          # process-global; the rest of the suite gets it back

    def _backend(self):
        be = _backend()
        be._update_reg = lambda sid, **f: None          # the reg write is file I/O outside the lock — not under test
        for i in range(self.SEEDED):
            be._stash_live(SID, "echo:seed%03d" % i, _echo("echo:seed%03d" % i, "seed %d" % i, 5))
        return be

    def _hammer(self, session_body, kernel_body, n_kernel):
        """kernel_body(i) runs n_kernel times on one thread while session_body(i) loops on another; both
        start on a barrier. Returns (errors, session_iterations, kernel_iterations)."""
        barrier = threading.Barrier(2)
        stop = threading.Event()
        errors, iters = [], [0, 0]
        deadline = time.monotonic() + self.CAP_S
        def session():
            barrier.wait()
            i = 0
            while not stop.is_set():
                try:
                    session_body(i)
                except Exception as e:
                    errors.append(("session", repr(e), _chain(e)))
                i += 1
                iters[0] = i
        def kernel():
            barrier.wait()
            for i in range(n_kernel):
                if time.monotonic() > deadline:
                    break
                try:
                    kernel_body(i)
                except Exception as e:
                    errors.append(("kernel", repr(e), _chain(e)))
                iters[1] = i + 1
            stop.set()
        ts = threading.Thread(target=session, name="session"), threading.Thread(target=kernel, name="kernel")
        for t in ts:
            t.start()
        for t in ts:
            t.join(self.CAP_S + 5)
        return errors, iters[0], iters[1]

    def test_prune_live_and_the_echo_mirror_survive_the_session_threads_stash_and_retire(self):
        """Refuter finding 1: prune_live (kernel thread) lands an echo → _persist_echoes walks the tail
        while the session thread's _forward stashes and retire_live_work pops — RuntimeError('dictionary
        changed size during iteration') escaped prune_live and aborted the pusher's whole build."""
        be = self._backend()
        s = _session(be)
        s._mark = lambda state: None                   # the state write is I/O the hammer does not need
        def session_body(i):
            for j in range(3):                         # _forward: one stash per streamed message
                be._forward(s, _AssistantMessage([_ToolUseBlock("toolu_%d_%d" % (i, j), "Bash", {})],
                                                 uuid="s%d-%d" % (i, j)))
            be.retire_live_work(SID)                   # the settle sweep, once per 'turn'
        def kernel_body(i):
            text = "probe send %d" % i
            be._stash_live(SID, "echo:k%d" % i, _echo("echo:k%d" % i, text, 5))   # send(): the echo
            be._persist_echoes(SID)                                                # …and its mirror
            be.prune_live(SID, set(), {text: 6.0}, 0)  # the echo lands by text → echo_removed → the mirror walk
        errors, si, ki = self._hammer(session_body, kernel_body, 1500)
        self.assertEqual(errors, [], "no exception on either thread: %r" % errors[:3])
        self.assertGreater(si, 2, "the session thread ran (%d turns against %d kernel calls)" % (si, ki))
        self.assertGreater(ki, 100, "the kernel thread ran")
        tail = be._live.get(SID) or {}
        self.assertTrue(all(("echo:seed%03d" % i) in tail for i in range(self.SEEDED)), "no seeded echo was lost")
        self.assertFalse([k for k in tail if k.startswith("echo:k")], "every landed echo was pruned")
        self.assertEqual([p for p in _problems(be) if p.startswith("live tail (")], [],
                         "under the lock no key vanishes mid-sweep, so no race line")

    def test_mark_dropped_echoes_survives_a_concurrent_send_stash(self):
        """Refuter finding 2: _mark_dropped_echoes runs on the SESSION thread at spawn and at every
        reconnect, outside the connect's try; its comprehension over the tail raised RuntimeError when
        the kernel thread's send() stashed an echo mid-walk, and the session thread died with no reconnect."""
        be = self._backend()
        def session_body(i):
            be._mark_dropped_echoes(SID, [], refeed=False)   # the resumable-reconnect arm (flag path only)
        def kernel_body(i):
            text = "probe send %d" % i
            be._stash_live(SID, "echo:k%d" % i, _echo("echo:k%d" % i, text, 5))
            be._persist_echoes(SID)
            be.prune_live(SID, set(), {text: 6.0}, 0)  # land it, so the tail stays bounded
        errors, si, ki = self._hammer(session_body, kernel_body, 3000)
        self.assertEqual(errors, [], "no exception on either thread: %r" % errors[:3])
        self.assertGreater(si, 2, "the session thread ran (%d passes against %d kernel calls)" % (si, ki))
        self.assertGreater(ki, 100)
        tail = be._live.get(SID) or {}
        self.assertTrue(all(tail["echo:seed%03d" % i].get("dropped") for i in range(self.SEEDED)),
                        "the seeded echoes were marked (the marking still does its job)")

    def test_no_stash_is_orphaned_by_the_sid_level_pop(self):
        """Refuter finding 3: `if not d: _live.pop(sid)` was two steps; a stash between them landed in a
        dict nothing could reach (an input echo gone from the chat and from reg['echoes']; a work atom
        the settle's salvage never sees). Under the lock the check and the pop are one step, so an atom
        just stashed is always reachable from _live — checked from OUTSIDE the lock after every stash,
        which is exactly the invariant: the sid's dict is never unreachable while non-empty."""
        for pair in ("retire_live_work vs an echo stash", "prune_live vs a work stash"):
            with self.subTest(pair=pair):
                be = _backend()
                be._update_reg = lambda sid, **f: None
                orphans = []
                if pair.startswith("retire"):
                    def session_body(i):
                        be._stash_live(SID, "w%d" % i, _work("w%d" % i, 1))
                        be.retire_live_work(SID)       # empties the tail → the sid-level pop
                    def kernel_body(i):
                        key = "echo:%08x" % i
                        be._stash_live(SID, key, _echo(key, "message %d" % i, 2))
                        if key not in (be._live.get(SID) or {}):
                            orphans.append(key)
                        with be._live_lock:
                            (be._live.get(SID) or {}).pop(key, None)
                else:
                    def session_body(i):
                        be.prune_live(SID, {"landed"}, (), 0)   # pops the landed atom → maybe the sid-level pop
                    def kernel_body(i):
                        be._stash_live(SID, "landed", _work("landed", 1))
                        key = "x%08x" % i
                        be._stash_live(SID, key, _work(key, 3))
                        if key not in (be._live.get(SID) or {}):
                            orphans.append(key)
                        with be._live_lock:
                            (be._live.get(SID) or {}).pop(key, None)
                errors, si, ki = self._hammer(session_body, kernel_body, 20000)
                self.assertEqual(errors, [], "no exception on either thread: %r" % errors[:3])
                self.assertGreater(si, 10, "the sweeper ran (%d sweeps against %d stashes)" % (si, ki))
                self.assertGreater(ki, 1000)
                self.assertEqual(orphans, [], "%d of %d stashes landed in an unreachable dict" % (len(orphans), ki))

    def test_the_lock_is_never_held_across_io_or_a_callback(self):
        """The rule's other half: copy under the lock, act outside. The reg write (the echo mirror), the
        transcript read and the marker append (the orphan salvage) and the pusher wake all observe the
        lock UNHELD — a lock held across a 4 MB tail read would stall the pusher's build on it."""
        be = _backend()
        seen = []
        note = lambda what: seen.append((what, be._live_lock._is_owned()))
        be._update_reg = lambda sid, **f: note("reg write")
        be._push_cb = lambda: note("pusher wake")
        be._reply_on_disk = lambda sid, u: (note("transcript read"), False)[1]
        orig = sb.append_orphan_reply
        sb.append_orphan_reply = lambda *a, **k: note("orphan append")
        try:
            be._stash_live(SID, "echo:a", _echo("echo:a", "hello", 5))
            be._persist_echoes(SID)                                     # send()'s mirror write
            be.prune_live(SID, set(), {"hello": 6.0}, 0)                # landing → the mirror write
            be._live[SID] = {MSG_UUID: _text_atom(MSG_UUID, 5)}
            be.retire_live_work(SID)                                    # the salvage's read + append
            be._live[SID] = {"echo:d": _echo("echo:d", "lost", 5, dropped=True)}
            self.assertEqual(be.dismiss_echo(SID, uuid="echo:d"), "lost")   # mirror write + wake
        finally:
            sb.append_orphan_reply = orig
        kinds = {w for w, _ in seen}
        self.assertEqual(kinds, {"reg write", "pusher wake", "transcript read", "orphan append"}, seen)
        self.assertFalse([w for w, held in seen if held], "the lock was held across: %r" % [w for w, h in seen if h])
        self.assertNotIn(SID, be._live, "the dismiss emptied the tail and popped the sid entry")

    def test_every_sweep_and_stash_is_locked_by_source(self):
        """A pin on the rule's coverage, so a new unlocked walk fails here before it fails live: every
        method that touches `_live` takes the lock (or goes through _stash_live, which does)."""
        for name in ("live_atoms", "prune_live", "retire_live_work", "live_atom_kinds", "_persist_echoes",
                     "_mark_dropped_echoes", "dismiss_echo", "unqueue", "_forward", "_stash_live"):
            src = inspect.getsource(getattr(sb.SdkBackend, name))
            self.assertIn("with self._live_lock", src, "%s does not take the live-tail lock" % name)
        for name in ("send", "_reseed_echoes"):
            src = inspect.getsource(getattr(sb.SdkBackend, name))
            self.assertIn("self._stash_live(", src, "%s stashes outside _stash_live" % name)
            self.assertNotIn("self._live.setdefault", src)
        whole = inspect.getsource(sb.SdkBackend)
        self.assertEqual(whole.count("self._live.setdefault("), 2, "_stash_live and _forward are the only stashes")


class HandlerFailuresStayWithTheirMessage(unittest.TestCase):
    def setUp(self):
        sb.SdkSession._stream_fail_seen.clear()

    def test_a_raising_handler_is_logged_with_detail_and_does_not_propagate(self):
        lines = []
        be = _backend(lines)
        s = _session(be)
        def boom(msg, *a):
            raise KeyError(MSG_UUID)                    # the live failure's shape: the key IS a uuid
        s._on_message = boom
        msg = _SystemMessage("background_tasks_changed", {"session_id": UNKNOWN_SID})
        self.assertFalse(s._handle_stream_message(msg, _AssistantMessage, _ResultMessage, _SystemMessage))
        probs = _problems(be)
        self.assertEqual(len(probs), 1, "one problem line, in the error center's ring")
        txt = probs[0]
        self.assertIn("KeyError", txt, "the exception type")
        self.assertIn("SystemMessage/background_tasks_changed", txt, "the message type and subtype")
        self.assertRegex(txt, r"at .*\.py:\d+ \w+", "a file:line frame chain")
        self.assertIn(MSG_UUID[:8] + "…", txt, "the key's first 8 characters…")
        self.assertNotIn(MSG_UUID, txt, "…and not its full value")
        self.assertIn("stream continues", txt)
        self.assertIn(txt, lines, "the same line reached the kernel log")

    def test_the_line_says_what_that_message_class_lost(self):
        """'(the transcript keeps it)' was true for assistant/user records only; a SystemMessage frame or
        a ResultMessage exists on the stream alone, and the line has to say so for the message it is about."""
        lines = []
        be = _backend(lines)
        s = _session(be)
        def boom(msg, *a):
            raise ValueError("v")
        s._on_message = boom
        cases = ((_SystemMessage("task_notification", {"task_id": "t1"}), "stream-only frame"),
                 (_ResultMessage(), "the turn still closed"),
                 (_AssistantMessage([_TextBlock("x")]), "the transcript keeps the message"),
                 (_StreamEvent(), "partial-stream event"))
        for msg, phrase in cases:
            sb.SdkSession._stream_fail_seen.clear()        # each case is a first-of-signature line…
            s._handle_stream_message(msg, _AssistantMessage, _ResultMessage, _SystemMessage)
            self.assertIn(phrase, lines[-1], "%s: %s" % (type(msg).__name__, lines[-1]))
        # …in the kernel log; the ring folds them (same session, exception type and site), and its one
        # entry keeps the first line's phrase with the repeat count
        self.assertEqual(len(_problems(be)), 1)
        self.assertIn("stream-only frame", _problems(be)[0])
        self.assertIn("(3 repeats this kernel life", _problems(be)[0])
        self.assertEqual(sb._failure_consequence(_HookEventMessage("hook_started")),
                         sb._failure_consequence(_SystemMessage("status")), "every other frame: stream-only")

    def test_repeats_count_on_one_ring_entry_and_bust_the_feed_cache_once(self):
        """Every repeat is a kernel-log line; the error-center RING keeps one entry per (session,
        exception type, failing frame) and counts on it. Before: a handler failing on every streamed
        message put every repeat in the 100-entry ring (evicting every unrelated problem within a
        minute) and bumped problem_seq — the feed's cache key — per message."""
        lines = []
        be = _backend(lines)
        s = _session(be)
        def boom(msg, *a):
            raise KeyError("k")
        s._on_message = boom
        seq0 = be.problem_seq()
        for _ in range(5):
            s._handle_stream_message(_ResultMessage(), _AssistantMessage, _ResultMessage, _SystemMessage)
        probs = _problems(be)
        self.assertEqual(len(probs), 1, "ONE ring entry for the five failures: %r" % probs)
        self.assertRegex(probs[0], r"at .*\.py:\d+", "it carries the frame chain from the first")
        self.assertIn("(4 repeats this kernel life", probs[0], "…and the count of the repeats")
        self.assertEqual(be.problem_seq(), seq0 + 1, "one cache bust for the new problem, none per repeat")
        logged = [l for l in lines if "KeyError while handling" in l]
        self.assertEqual(len(logged), 5, "every failure is a kernel-log line — nothing silent")
        self.assertIn("repeat 5", logged[4])
        self.assertNotRegex(logged[4], r"\.py:\d+", "repeats do not re-print the chain")
        # a different exception TYPE at the same site is a new problem: a new entry, one more bust
        def boom2(msg, *a):
            raise ValueError("other")
        s._on_message = boom2
        s._handle_stream_message(_ResultMessage(), _AssistantMessage, _ResultMessage, _SystemMessage)
        self.assertEqual(len(_problems(be)), 2)
        self.assertEqual(be.problem_seq(), seq0 + 2)
        # …while the same failure on ANOTHER message kind folds into the first entry (same site, same type)
        s._on_message = boom
        s._handle_stream_message(_AssistantMessage([_TextBlock("x")]), _AssistantMessage, _ResultMessage, _SystemMessage)
        self.assertEqual(len(_problems(be)), 2)
        self.assertIn("(5 repeats this kernel life", _problems(be)[0])

    def test_a_ring_entry_evicted_meanwhile_enters_again_as_new(self):
        be = _backend()
        s = _session(be)
        def boom(msg, *a):
            raise KeyError("k")
        s._on_message = boom
        s._handle_stream_message(_ResultMessage(), _AssistantMessage, _ResultMessage, _SystemMessage)
        for i in range(be.PROBLEM_RING):
            be._log("unrelated problem %d" % i, problem=True)   # the ring turns over
        self.assertFalse([p for p in _problems(be) if "KeyError" in p], "the entry was evicted")
        seq = be.problem_seq()
        s._handle_stream_message(_ResultMessage(), _AssistantMessage, _ResultMessage, _SystemMessage)
        self.assertEqual(len([p for p in _problems(be) if "KeyError" in p]), 1, "back in the ring as a new entry")
        self.assertEqual(be.problem_seq(), seq + 1)

    def test_a_clean_handler_reports_true_and_logs_nothing(self):
        be = _backend()
        s = _session(be)
        ok = s._handle_stream_message(_SystemMessage("task_notification", {"task_id": "gone1", "status": "completed"}),
                                      _AssistantMessage, _ResultMessage, _SystemMessage)
        self.assertTrue(ok)
        self.assertEqual(_problems(be), [])

    def test_a_reporter_failure_is_one_plain_line_and_never_propagates(self):
        """An exception whose __str__ raises reached _mask_ids inside the except and ended the drain —
        the outcome the containment exists to prevent. The reporter is guarded: one plain line from
        names only, and the stream goes on."""
        class Unrenderable(Exception):
            def __str__(self):
                raise TypeError("unrenderable")
        be = _backend()
        s = _session(be)
        def boom(msg, *a):
            raise Unrenderable()
        s._on_message = boom
        self.assertFalse(s._handle_stream_message(_SystemMessage("hook_started"), _AssistantMessage, _ResultMessage, _SystemMessage))
        probs = _problems(be)
        self.assertEqual(len(probs), 1)
        self.assertIn("Unrenderable", probs[0])
        self.assertIn("reporting it failed too (TypeError)", probs[0])

    def test_a_raising_log_callback_does_not_end_the_stream(self):
        """The kernel's log callback writes stderr; closed under a service restart it raises OSError from
        inside the report. The ring still has the entry (recorded before the callback), and nothing propagates."""
        be = _backend()
        s = _session(be)
        def badlog(m):
            raise OSError(32, "Broken pipe")
        be._log_cb = badlog                            # armed AFTER construction (construction logs too)
        def boom(msg, *a):
            raise KeyError("k")
        s._on_message = boom
        for _ in range(4):
            self.assertFalse(s._handle_stream_message(_ResultMessage(), _AssistantMessage, _ResultMessage, _SystemMessage))
        probs = _problems(be)
        self.assertEqual(len(probs), 2, "the report landed before the callback raised, and the broken "
                                        "callback is its own entry — each deduped across the repeats: %r" % probs)
        self.assertIn("KeyError while handling a ResultMessage", probs[0])
        self.assertIn("(3 repeats this kernel life", probs[0])
        self.assertIn("reporting it failed too (BrokenPipeError)", probs[1])
        self.assertIn("(3 repeats this kernel life", probs[1])


class TheSettleFinishesItsPlumbingWhenAStepRaises(unittest.TestCase):
    """With per-message containment, an exception in the ResultMessage settle no longer ends the
    stream — so the turn-end plumbing that used to follow the failing step in straight-line code (the
    queue wake, the poke, the rename ping, the deferred effort reconnect) must not be skipped by it, or
    a gate-held queue stays parked and a deferred reconnect never fires while the session reads 'waiting'."""
    def setUp(self):
        sb.SdkSession._stream_fail_seen.clear()

    def _settle(self, be, s, ok_expected):
        pokes = []
        be._poke_cb = lambda: pokes.append(1)
        out = {}
        async def run():
            s.loop = asyncio.get_running_loop()
            s._input_wake = asyncio.Event()
            s._wake = asyncio.Event()
            out["ok"] = s._handle_stream_message(_ResultMessage(), _AssistantMessage, _ResultMessage, _SystemMessage)
            await asyncio.sleep(0)
            out.update(wake=s._input_wake.is_set(), pokes=len(pokes), reconnect=s._reconnect,
                       still_deferred=s._reconnect_when_idle, wake_event=s._wake.is_set())
        asyncio.run(run())
        self.assertEqual(out["ok"], ok_expected)
        return out

    def test_a_raising_retire_still_wakes_the_queue_pokes_and_fires_the_deferred_reconnect(self):
        be = _backend()
        s = _session(be)
        s.inflight = 1
        s._interrupted = True                          # the queue is gate-held behind an interrupted turn
        s._pending = ["queued during the interrupted turn"]
        s._reconnect_when_idle = True                  # an /effort change waiting for this turn's end
        def boom(sid):
            raise OSError("the sweep's transcript read failed")
        be.retire_live_work = boom
        out = self._settle(be, s, ok_expected=False)
        self.assertEqual(s.inflight, 0, "the turn settled")
        self.assertTrue(out["wake"], "the input feeder was released")
        self.assertEqual(out["pokes"], 1, "the kernel was poked")
        self.assertTrue(out["reconnect"] and not out["still_deferred"], "the deferred reconnect fired")
        self.assertTrue(out["wake_event"], "…and the loop was woken for it")
        probs = _problems(be)
        self.assertEqual(len(probs), 1)
        self.assertIn("OSError while handling a ResultMessage", probs[0])
        self.assertIn("the turn still closed", probs[0])

    def test_a_clean_settle_runs_the_same_plumbing_once(self):
        be = _backend()
        s = _session(be)
        s.inflight = 1
        s._reconnect_when_idle = True
        out = self._settle(be, s, ok_expected=True)
        self.assertTrue(out["wake"])
        self.assertEqual(out["pokes"], 1)
        self.assertTrue(out["reconnect"] and not out["still_deferred"])
        self.assertEqual(_problems(be), [])

    def test_the_plumbing_sits_in_a_finally_by_source(self):
        src = inspect.getsource(sb.SdkSession._on_message)
        i_retire = src.index("self.backend.retire_live_work(self.sid)")
        i_finally = src.index("finally:", i_retire)
        i_wake = src.index("self._input_wake.set()", i_finally)
        self.assertLess(i_retire, i_finally, "the sweep is inside the try")
        self.assertLess(i_finally, i_wake, "the queue wake is in the finally")
        self.assertIn("self._reconnect_when_idle and not self.ended", src[i_finally:])


class TheDrainLoopOutlivesAHandlerFailure(unittest.TestCase):
    def setUp(self):
        sb.SdkSession._stream_fail_seen.clear()

    class _Client:
        def __init__(self, msgs, then=None):
            self.msgs, self.then = msgs, then
        async def receive_messages(self):
            for m in self.msgs:
                yield m
            if self.then is not None:
                raise self.then

    def test_the_stream_continues_past_the_message_that_failed(self):
        be = _backend()
        s = _session(be)
        seen = []
        bad = _SystemMessage("vcs_state_changed", {"session_id": UNKNOWN_SID})
        def handler(msg, *a):
            if msg is bad:
                raise KeyError(UNKNOWN_SID)
            seen.append(msg)
        s._on_message = handler
        good1, good2 = _SystemMessage("thinking_tokens"), _ResultMessage()
        asyncio.run(s._drain(self._Client([good1, bad, good2]), _AssistantMessage, _ResultMessage, _SystemMessage))
        self.assertEqual(seen, [good1, good2], "the messages after the failure were still handled")
        self.assertEqual(len(_problems(be)), 1)

    def test_the_stream_continues_past_a_failure_whose_report_fails(self):
        class Unrenderable(Exception):
            def __str__(self):
                raise TypeError("unrenderable")
        be = _backend()
        s = _session(be)
        seen = []
        bad = _SystemMessage("hook_response")
        def handler(msg, *a):
            if msg is bad:
                raise Unrenderable()
            seen.append(msg)
        s._on_message = handler
        good = _ResultMessage()
        asyncio.run(s._drain(self._Client([bad, good]), _AssistantMessage, _ResultMessage, _SystemMessage))
        self.assertEqual(seen, [good])

    def test_a_stream_fault_still_ends_the_loop(self):
        """The transport closing (the SDK re-raises it out of receive_messages) is the stream ending:
        the loop propagates it as before, so the client teardown and the crash heal still run."""
        be = _backend()
        s = _session(be)
        s._on_message = lambda *a: None
        with self.assertRaises(RuntimeError):
            asyncio.run(s._drain(self._Client([_ResultMessage()], then=RuntimeError("transport closed")),
                                 _AssistantMessage, _ResultMessage, _SystemMessage))

    def test_ended_stops_the_loop(self):
        be = _backend()
        s = _session(be)
        seen = []
        s._on_message = lambda msg, *a: seen.append(msg)
        s.ended = True
        asyncio.run(s._drain(self._Client([_ResultMessage(), _ResultMessage()]), _AssistantMessage, _ResultMessage, _SystemMessage))
        self.assertEqual(seen, [])

    def test_amain_routes_the_receive_loop_through_drain(self):
        src = inspect.getsource(sb.SdkSession._amain)
        self.assertIn("self._drain(client, AssistantMessage, ResultMessage, SystemMessage)", src)
        self.assertNotIn("self._on_message(msg", src, "no bare dispatch is left in the loop")
        self.assertIn("_compact_tb(e)", src, "the transport catch names the frame chain")
        self.assertIn("_mask_ids(e)", src, "…and masks ids in the exception text")


class UnknownIdsInTheNewSdkShapesDoNotRaise(unittest.TestCase):
    """The shapes the newer CLI emits, each carrying an id the kernel has no record for, through the
    REAL handler: nothing raises, the live tail stays clean, and the unhandled subtypes log once."""
    def setUp(self):
        sb.SdkSession._sys_subtypes_seen.clear()

    def _run(self, s, msg):
        return s._handle_stream_message(msg, _AssistantMessage, _ResultMessage, _SystemMessage)

    def test_sidechain_messages_of_an_unregistered_subagent(self):
        be = _backend()
        s = _session(be)
        self.assertTrue(self._run(s, _UserMessage([_TextBlock("kickoff")], uuid="u9", parent_tool_use_id="toolu_unreg")))
        self.assertTrue(self._run(s, _AssistantMessage([_TextBlock("reply")], model="claude-tiny", uuid="a9",
                                                       parent_tool_use_id="toolu_unreg")))
        self.assertEqual(be.live_atoms(SID), [], "sidechain traffic never enters the parent's tail")
        self.assertNotEqual(s.model, "claude-tiny", "a subagent's model is never learned")
        self.assertEqual(_problems(be), [])

    def test_new_system_subtypes_with_an_unknown_session_id_log_once_each(self):
        lines = []
        be = _backend(lines)
        s = _session(be)
        for st in ("background_tasks_changed", "thinking_tokens", "vcs_state_changed"):
            for _ in range(2):
                self.assertTrue(self._run(s, _SystemMessage(st, {"session_id": UNKNOWN_SID, "tasks": []})))
        for st in ("hook_started", "hook_response"):
            for _ in range(2):
                self.assertTrue(self._run(s, _HookEventMessage(st, {"session_id": UNKNOWN_SID, "hook_id": MSG_UUID})))
        unhandled = [l for l in lines if "unhandled SystemMessage subtype" in l]
        self.assertEqual(len(unhandled), 5, "one line per subtype per kernel life: %r" % unhandled)
        for l in unhandled:
            self.assertNotIn(UNKNOWN_SID, l, "keys only — never the payload's values")
        self.assertEqual(_problems(be), [], "an unhandled subtype is a note, not a failure")

    def test_task_events_for_a_task_the_kernel_never_recorded(self):
        be = _backend()
        s = _session(be)
        for st, data in (("task_notification", {"task_id": "b_gone", "status": "completed"}),
                         ("task_updated", {"task_id": "b_gone", "patch": {"status": "killed"}}),
                         ("task_progress", {"task_id": "b_new", "description": "d"})):
            self.assertTrue(self._run(s, _SystemMessage(st, data)))
        self.assertEqual([t["desc"] for t in s._live_bg_tasks()], ["d"],
                         "an unknown id ENDING is a no-op; progress on an unknown id self-heals an entry")
        self.assertEqual(_problems(be), [])


class LogHelpers(unittest.TestCase):
    def test_mask_ids_keeps_eight_characters_of_a_uuid_and_clips(self):
        self.assertEqual(sb._mask_ids(KeyError(MSG_UUID)), "'%s…'" % MSG_UUID[:8])
        self.assertEqual(sb._mask_ids("x" * 200, cap=10), "x" * 10 + "…")
        self.assertEqual(sb._mask_ids("plain"), "plain")

    def test_compact_tb_is_a_file_line_chain_without_locals(self):
        secret = "the message content"      # noqa: F841 — a local that must NOT appear
        def inner():
            raise ValueError("v")
        try:
            inner()
        except ValueError as e:
            chain = sb._compact_tb(e)
        self.assertRegex(chain, r"^test_sdk_stream_survives_handler_errors\.py:\d+ test_compact_tb_is_a_file_line_chain_without_locals"
                                r" > test_sdk_stream_survives_handler_errors\.py:\d+ inner$")
        self.assertNotIn("secret", chain)
        self.assertNotIn(secret, chain)
        self.assertEqual(sb._compact_tb(ValueError("no traceback")), "?")

    def test_compact_tb_is_bounded_to_the_innermost_frames_and_a_length_cap(self):
        """A RecursionError's chain ran to 18 KB — into the error-center ring and every feed payload that
        carries it. The chain keeps the innermost COMPACT_TB_FRAMES frames (the failing site is at that
        end), says how many outer ones it dropped, and is clipped to COMPACT_TB_CHARS."""
        def rec(n):
            return rec(n + 1)
        try:
            rec(0)
        except RecursionError as exc:
            e = exc                                    # the except clause unbinds its own name on exit
            chain = sb._compact_tb(e)
            depth = len(traceback.extract_tb(e.__traceback__))
        self.assertGreater(depth, 100)
        self.assertLessEqual(len(chain), sb.COMPACT_TB_CHARS)
        self.assertRegex(chain, r"^…%d outer frames dropped… > " % (depth - sb.COMPACT_TB_FRAMES))
        self.assertEqual(chain.count(" > "), sb.COMPACT_TB_FRAMES, "the prefix plus the kept frames")
        self.assertTrue(chain.endswith(" rec"), "the innermost frame is kept: %r" % chain[-40:])
        # the cap applies even when the frames are few but their names are long
        long = sb._compact_tb(e, max_frames=depth, cap=100)
        self.assertEqual(len(long), 100)
        self.assertTrue(long.endswith("…"))
        # one dropped frame reads as one
        self.assertRegex(sb._compact_tb(e, max_frames=depth - 1), r"^…1 outer frame dropped… > ")

    def test_a_recursing_handler_yields_one_bounded_problem_line(self):
        be = _backend()
        s = _session(be)
        def rec(msg, *a):
            return rec(msg, *a)
        s._on_message = rec
        self.assertFalse(s._handle_stream_message(_ResultMessage(), _AssistantMessage, _ResultMessage, _SystemMessage))
        probs = _problems(be)
        self.assertEqual(len(probs), 1)
        self.assertIn("RecursionError", probs[0])
        self.assertLess(len(probs[0]), 1000, "was 18 KB before the bound")

    def test_describe_msg_names_type_and_subtype_only(self):
        self.assertEqual(sb._describe_msg(_SystemMessage("api_retry", {"error": "content"})), "SystemMessage/api_retry")
        self.assertEqual(sb._describe_msg(_AssistantMessage([_TextBlock("content")])), "AssistantMessage")
        self.assertEqual(sb._describe_msg(_HookEventMessage("hook_started")), "HookEventMessage/hook_started")


if __name__ == "__main__":
    unittest.main()
