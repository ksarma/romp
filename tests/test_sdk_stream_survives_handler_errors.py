#!/usr/bin/env python3
"""A handler failure on ONE streamed message must not end a session's CLI (2026-09-06).

What happened live: a session's receive loop died on `KeyError: '<message uuid>'` — the only line
the journal had — and the client teardown that followed closed its CLI mid-work (an in-flight turn,
a Workflow run with four subagents and a background agent), then the session came back as a crash
resume. The KeyError came from a live-tail sweep at the ResultMessage settle (retire_live_work)
racing the kernel thread's prune_live on the same unlocked dict: `for k in list(d.keys()): a = d[k]`
with the kernel thread deleting the just-landed reply between the snapshot and the read. Two fixes,
both covered here:

  * the three live-tail sweeps (prune_live, retire_live_work, _evict_live_overflow) iterate an items
    SNAPSHOT and pop with a default, and report a vanished key once per site per kernel life;
  * the receive loop (_drain) runs each message through _handle_stream_message, which keeps a
    handler's exception to that message — logged with its type, the message kind and a frame chain —
    while a fault of the stream itself still ends the loop as before.

Every id here is synthetic (the placeholder uuid family); no message content is real.
"""
import asyncio
import inspect
import os
import tempfile
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
_TextBlock.__name__ = "TextBlock"; _ToolUseBlock.__name__ = "ToolUseBlock"
_AssistantMessage.__name__ = "AssistantMessage"; _UserMessage.__name__ = "UserMessage"
_ResultMessage.__name__ = "ResultMessage"; _SystemMessage.__name__ = "SystemMessage"
_HookEventMessage.__name__ = "HookEventMessage"


class _RacyTail(dict):
    """A live tail whose snapshot goes stale by one key: right after a sweep takes its keys()/items()
    snapshot, `victim` is removed — the kernel thread's prune_live landing between the session
    thread's snapshot and its read, which is the interleaving that killed the session live. The old
    `a = d[k]` raises KeyError(victim) on it; a snapshot-and-pop sweep does not."""
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


def _backend(lines=None):
    d = tempfile.mkdtemp()
    log = (lambda m: lines.append(str(m))) if lines is not None else (lambda *a, **k: None)
    return sb.SdkBackend(d, "/bin/true", lambda *a, **k: None, log=log)


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


class LiveTailSweepsSurviveAConcurrentPrune(unittest.TestCase):
    def setUp(self):
        sb.SdkBackend._live_tail_race_seen.clear()     # per-kernel-life set; a fresh life per test

    def _problems(self, be, site):
        return [t for t in _problems(be) if t.startswith("live tail (%s)" % site)]

    def test_retire_live_work_survives_the_settle_race_and_reports_once(self):
        """THE reported failure: the settle sweep held a snapshot of keys while the kernel thread pruned
        the just-landed reply — `a = d[k]` raised KeyError('<message uuid>') out of _on_message."""
        be = _backend()
        be._live[SID] = _RacyTail({MSG_UUID: _work(MSG_UUID, 5), "w2": _work("w2", 6)}, victim=MSG_UUID)
        be.retire_live_work(SID)                        # raised KeyError before the fix
        self.assertNotIn(SID, be._live, "every work atom retired, the vanished one included")
        self.assertEqual(len(self._problems(be, "retire_live_work")), 1, "the race is reported")
        be._live[SID] = _RacyTail({"w3": _work("w3", 7)}, victim="w3")
        be.retire_live_work(SID)
        self.assertEqual(len(self._problems(be, "retire_live_work")), 1, "…ONCE per site per kernel life")
        txt = self._problems(be, "retire_live_work")[0]
        self.assertIn("message-uuid key", txt, "the line names the key KIND")
        self.assertNotIn(MSG_UUID, txt, "…never the key's value")

    def test_prune_live_survives_a_retire_under_it(self):
        be = _backend()
        be._live[SID] = _RacyTail({MSG_UUID: _work(MSG_UUID, 5), "w2": _work("w2", 6)}, victim=MSG_UUID)
        be.prune_live(SID, {MSG_UUID, "w2"})            # both landed; the victim vanished mid-sweep
        self.assertNotIn(SID, be._live)
        self.assertEqual(len(self._problems(be, "prune_live")), 1)

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

    def test_repeats_of_one_signature_log_a_short_counted_line(self):
        be = _backend()
        s = _session(be)
        def boom(msg, *a):
            raise KeyError("k")
        s._on_message = boom
        for _ in range(3):
            s._handle_stream_message(_ResultMessage(), _AssistantMessage, _ResultMessage, _SystemMessage)
        probs = _problems(be)
        self.assertEqual(len(probs), 3, "every failure is a line — nothing silent")
        self.assertRegex(probs[0], r"at .*\.py:\d+", "the first carries the frame chain")
        self.assertIn("repeat 2", probs[1])
        self.assertIn("repeat 3", probs[2])
        self.assertNotRegex(probs[2], r"\.py:\d+", "repeats do not re-print the chain")
        # a DIFFERENT message kind is a new signature → the chain again
        s._handle_stream_message(_AssistantMessage([_TextBlock("x")]), _AssistantMessage, _ResultMessage, _SystemMessage)
        self.assertRegex(_problems(be)[-1], r"AssistantMessage.*at .*\.py:\d+")

    def test_a_clean_handler_reports_true_and_logs_nothing(self):
        be = _backend()
        s = _session(be)
        ok = s._handle_stream_message(_SystemMessage("task_notification", {"task_id": "gone1", "status": "completed"}),
                                      _AssistantMessage, _ResultMessage, _SystemMessage)
        self.assertTrue(ok)
        self.assertEqual(_problems(be), [])


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

    def test_describe_msg_names_type_and_subtype_only(self):
        self.assertEqual(sb._describe_msg(_SystemMessage("api_retry", {"error": "content"})), "SystemMessage/api_retry")
        self.assertEqual(sb._describe_msg(_AssistantMessage([_TextBlock("content")])), "AssistantMessage")
        self.assertEqual(sb._describe_msg(_HookEventMessage("hook_started")), "HookEventMessage/hook_started")


if __name__ == "__main__":
    unittest.main()
