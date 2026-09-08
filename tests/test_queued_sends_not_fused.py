#!/usr/bin/env python3
"""Two texts queued during one open turn reach the agent as two messages, never one (2026-09-08).

What happened live: while a session's turn was open the person sent a composer message, then answered a
user todo through the Reply modal (a "Re: <todo> — <reply>" message). The kernel's input feeder forwards
every queued text into the CLI's stdin the moment it is queued, so both sat in the CLI's own queue when
the turn ended; the CLI drains every queued prompt it holds into ONE user message when it next reads that
queue, so the agent received one message wearing both texts, the chat showed one bubble wearing both,
and the client's "sending…" bubble for the first message — matched by exact text — never found its
landing and stayed up until a ✕. Two fixes, both covered here:
  * the feeder feeds ONE text and holds the rest until the CLI demonstrably TOOK it (SdkSession._untaken,
    cleared by _untaken_taken on an exact event: a turn frame after a feed from idle; a turn frame after
    the ResultMessage of the turn a mid-turn feed went into — the CLI's drain, and the next turn's first
    frame proves it; or the fed text's queued_command attachment landing in the transcript — a mid-turn
    splice, which lets the next text follow it into the same turn). Order is preserved and a todo answer
    keeps its shape and its id;
  * every send carries the CLIENT's id for it (send_id → _QueueText.send_id, the echo's _send_id, the
    landed record's stamped ids — kernel._note_send_landings), so the bubble is matched to its own copy
    by id and a ✕ removes exactly the entry it was pressed on (unqueue / _cancel_backend_queued by id).
The REAL _amain runs here (its inputs() closure) against a stand-in SDK module whose client records what
it was fed and in which phase of the scripted stream — installed in sys.modules for the test (the
backend imports the SDK lazily, at the top of _amain) and removed after. Every id is synthetic (the
placeholder uuid family), the hostname TESTHOST, every text invented.
"""
import asyncio
import json
import os
import shutil
import sys
import tempfile
import time
import types
import unittest
from datetime import datetime, timezone
from importlib.machinery import ModuleSpec
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()       # hermetic state BEFORE the load (import-time root)
os.environ["CLAUDE_CONFIG_DIR"] = tempfile.mkdtemp()    # the transcripts the take check scans live here, not ~/.claude
os.environ.pop("ROMP_STATE_DIR", None)
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
sb = load_source("romp_sdk_backend_queuejoin", os.path.join(BIN, "romp_sdk_backend.py"))
km = load_source("romp_kernel_queuejoin", os.path.join(BIN, "romp-kernel"))

SID = "11111111-2222-3333-4444-aaaaaaaaaa11"        # this module's own synthetic sid
FSID = "11111111-2222-3333-4444-ffffffffff11"       # the CLI's own session id, announced by the init


# ---- message doubles: the SDK's shapes, by class name (msg_to_atom / _on_message key on them) ----
class _TextBlock:
    def __init__(self, text): self.text = text
class _AssistantMessage:
    def __init__(self, content, model="claude-x", uuid="a1", parent_tool_use_id=None):
        self.content, self.model, self.uuid = content, model, uuid
        self.parent_tool_use_id, self.stop_reason, self.error = parent_tool_use_id, "end_turn", None
class _ResultMessage:
    pass
def _result(**fields):
    return type("ResultMessage", (_ResultMessage,), dict(fields))()
class _SystemMessage:
    def __init__(self, subtype, data=None, uuid=None):
        self.subtype, self.data, self.uuid = subtype, (data or {}), uuid
class _RateLimitEvent:
    """A frame that is NOT a turn frame (the SDK's RateLimitEvent): proves nothing about the CLI's queue."""
    def __init__(self, uuid="rl1"): self.uuid = uuid
_TextBlock.__name__ = "TextBlock"; _AssistantMessage.__name__ = "AssistantMessage"
_ResultMessage.__name__ = "ResultMessage"; _SystemMessage.__name__ = "SystemMessage"
_RateLimitEvent.__name__ = "RateLimitEvent"


def _iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


class OneFedTextAtATime(unittest.TestCase):
    """The feed hold, end to end through the real inputs() closure and _on_message."""

    class _Client:
        instances = []

        def __init__(self, options=None, transport=None):
            self.options = options
            self.no = len(type(self).instances) + 1
            type(self).instances.append(self)
            self.writes = []                # (text, phase) — the test's own phase label at the write
            self.phase = "before-turn-1"
            self.frames = asyncio.Queue()   # the scripted stream: the test pushes frames
            self.torn_down = False

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            self.torn_down = True
            return False

        async def query(self, prompt, session_id="default"):
            async for turn in prompt:
                self.writes.append((turn["message"]["content"][0]["text"], self.phase))

        async def interrupt(self):
            pass

        async def get_context_usage(self):
            return {"percentage": 2, "model": "claude-x"}

        async def get_server_info(self):
            return {}

        async def receive_messages(self):
            while True:
                f = await self.frames.get()
                yield f

    class _Options:
        def __init__(self, **kw):
            self.session_id = self.resume = None
            for k, v in kw.items():
                setattr(self, k, v)

    def setUp(self):
        sb.SdkSession._stream_fail_seen.clear()
        self._Client.instances = []
        fake = types.ModuleType("claude_agent_sdk")
        fake.__spec__ = ModuleSpec("claude_agent_sdk", loader=None)
        fake.ClaudeSDKClient, fake.ClaudeAgentOptions, fake.HookMatcher = self._Client, self._Options, (lambda **kw: kw)
        fake.AssistantMessage, fake.ResultMessage = _AssistantMessage, _ResultMessage
        fake.SystemMessage, fake.TextBlock = _SystemMessage, _TextBlock
        self._saved_sdk = sys.modules.get("claude_agent_sdk")
        sys.modules["claude_agent_sdk"] = fake
        self.state = tempfile.mkdtemp()
        self.cwd = os.path.join(self.state, "proj")
        os.makedirs(self.cwd)
        self.lines = []
        self.be = sb.SdkBackend(self.state, "/bin/true", lambda *a, **k: None,
                                log=lambda m, **k: self.lines.append(str(m)))
        reg = {"sid": SID, "name": "web", "mode": "acceptEdits", "alive": True, "cwd": self.cwd}
        sb.write_reg(self.be.state_dir, SID, reg)
        self.s = sb.SdkSession(self.be, dict(reg))
        async def _noop(): pass
        self.s._do_refresh_usage = _noop
        self.be.sessions[SID] = self.s
        self.n = 0

    def tearDown(self):
        self.s.shutdown()
        if self.s.thread.ident is not None:
            self.s.thread.join(timeout=10)
        if self._saved_sdk is None:
            sys.modules.pop("claude_agent_sdk", None)
        else:
            sys.modules["claude_agent_sdk"] = self._saved_sdk
        shutil.rmtree(self.state, ignore_errors=True)

    # -- the scripted stream --
    def _wait(self, pred, what, timeout=10.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if pred():
                return
            time.sleep(0.01)
        self.fail("timed out waiting for %s; client fed %r; pending %r; hold %r; log tail %r"
                  % (what, [c.writes for c in self._Client.instances], self.s.pending(),
                     self.s._untaken, self.lines[-6:]))

    def _settle(self, dt=0.15):
        """Every chance for a (wrong) feed to happen: the loop runs its wakeups within this."""
        time.sleep(dt)

    def _push(self, client, frame):
        self.s.loop.call_soon_threadsafe(client.frames.put_nowait, frame)

    def _uid(self):
        self.n += 1
        return "11111111-2222-3333-4444-%012d" % self.n

    def _init(self, client):
        self._push(client, _SystemMessage("init", {"model": "claude-x", "permissionMode": "acceptEdits",
                                                    "session_id": FSID}, uuid=self._uid()))

    def _assistant(self, client, text="working on it"):
        self._push(client, _AssistantMessage([_TextBlock(text)], uuid=self._uid()))

    def _result_frame(self, client):
        self._push(client, _result(uuid=self._uid(), subtype="success", is_error=False, num_turns=1,
                                   session_id=FSID, duration_ms=1, duration_api_ms=1, total_cost_usd=0.01,
                                   usage={"input_tokens": 1, "output_tokens": 1}, result="ok",
                                   parent_tool_use_id=None))

    def _first_turn(self):
        """Connect, feed a first turn from idle, and let its init + first reply stream: the CLI has
        demonstrably started it, so the hold on THAT text is released and the turn is open."""
        s = self.s
        s.start()
        self._wait(lambda: s.client is not None, "the first connect")
        c = self._Client.instances[0]
        c.phase = "turn-1"
        s.enqueue("first turn")
        self._wait(lambda: c.writes == [("first turn", "turn-1")], "the first turn fed")
        self.assertIsNotNone(s._untaken, "fed from idle: held until the CLI shows the turn started")
        self._init(c)
        self._assistant(c)
        self._wait(lambda: s._untaken is None and s.resume_sid == FSID, "the first turn's start releases its hold")
        self.assertEqual(s.inflight, 1)
        return c

    def _transcript(self):
        reg = sb.read_reg(self.state, SID) or {}
        return sb.transcript_path(self.cwd, str(reg.get("lastSid") or SID))

    def _append(self, rec):
        p = self._transcript()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a") as f:
            f.write(json.dumps(rec) + "\n")

    # -- the tests --
    def test_two_texts_sent_mid_turn_reach_the_client_one_at_a_time_and_in_order(self):
        """The incident's shape: two texts queued while a turn is open. The first forwards at once (the
        designed mid-turn forward); the second is HELD — through the rest of the turn and through its
        ResultMessage — until the next turn's first frame shows the CLI drained its queue with the first
        text in it. Only then is the second fed: it can no longer share a drain with the first."""
        s, c = self.s, self._first_turn()
        s.enqueue("please also update the changelog")
        self._wait(lambda: len(c.writes) == 2, "the first mid-turn send forwarded")
        self.assertEqual(c.writes[1], ("please also update the changelog", "turn-1"))
        s.enqueue("and bump the version")
        self._settle()
        self.assertEqual(len(c.writes), 2, "the second text is NOT fed while the first is untaken")
        self.assertEqual(s.pending(), ["and bump the version"], "…it waits, visibly, in the queue")
        self.assertTrue(self.be.queue_recallable(SID), "…and is still recallable there (the ✕ can win)")
        self._assistant(c, "still working")            # more of the same turn: nothing proves a take
        self._push(c, _RateLimitEvent())                # a non-turn frame proves nothing either
        self._settle()
        self.assertEqual(len(c.writes), 2, "a frame of the running turn does not release the hold")
        c.phase = "after-result-1"
        self._result_frame(c)
        self._wait(lambda: s.inflight == 0, "the turn's result settles it")
        self._settle()
        self.assertEqual(len(c.writes), 2, "the result alone does not release it: the CLI drains AFTER it")
        self.assertTrue(s._untaken and s._untaken.get("settled"), "the hold now waits for the next turn's frame")
        c.phase = "turn-2"
        self._init(c)                                   # the next turn's first frame: the drain happened
        self._wait(lambda: len(c.writes) == 3, "the second text fed once the first was taken")
        self.assertEqual([w[0] for w in c.writes],
                         ["first turn", "please also update the changelog", "and bump the version"],
                         "queue order, one message each")
        self.assertEqual(c.writes[2][1], "turn-2", "fed into the turn that took the first, never its drain")
        self.assertEqual(s.pending(), [])

    def test_a_todo_answer_after_a_composer_message_keeps_its_shape_and_its_id(self):
        """The incident's second text was a user-todo answer: it is fed byte for byte as its own
        message — never appended to the composer text — and the fed entry still carries the id of the
        ask it answers (the recall/loss machinery reads it off the entry)."""
        s, c = self.s, self._first_turn()
        s.enqueue("can you also check the tests")
        self._wait(lambda: len(c.writes) == 2, "the composer message forwarded")
        answer = "Re: Which branch should I target? — main, please"
        s.enqueue(answer, todo="ut-11111111")
        self._settle()
        self.assertEqual(len(c.writes), 2, "the answer waits behind the untaken composer message")
        self.assertEqual(getattr(s.pending()[0], "todo", ""), "ut-11111111", "the queued answer keeps its ask")
        self._result_frame(c)
        self._wait(lambda: s.inflight == 0, "the turn settles")
        c.phase = "turn-2"
        self._init(c)
        self._wait(lambda: len(c.writes) == 3, "the answer fed once the composer message was taken")
        self.assertEqual(c.writes[2][0], answer, "the answer's text, unchanged, as its own message")
        self.assertEqual([getattr(t, "todo", "") for t in s.fed_texts()], ["ut-11111111"],
                         "the fed entry still carries the ask's id")

    def test_a_mid_turn_splice_releases_the_next_text_into_the_same_turn(self):
        """The accelerator: when the CLI takes the fed text at a tool boundary (the queued_command
        attachment lands in the transcript), the next text may follow it into the same turn — the
        take check reads the record from the feed-time mark, on the next turn frame."""
        s, c = self.s, self._first_turn()
        s.enqueue("first note")
        self._wait(lambda: len(c.writes) == 2, "the first note forwarded")
        s.enqueue("second note")
        self._settle()
        self.assertEqual(len(c.writes), 2, "the second note waits")
        # a record of another text: not the take
        self._append({"type": "attachment", "uuid": self._uid(), "timestamp": _iso(time.time()),
                      "attachment": {"type": "queued_command", "prompt": "some other text"}})
        self._assistant(c)
        self._settle()
        self.assertEqual(len(c.writes), 2, "another text's record releases nothing")
        # the fed text's own splice record
        self._append({"type": "attachment", "uuid": self._uid(), "timestamp": _iso(time.time()),
                      "attachment": {"type": "queued_command", "prompt": "first note"}})
        self._assistant(c)
        self._wait(lambda: len(c.writes) == 3, "the second note fed on the frame after the splice landed")
        self.assertEqual(c.writes[2], ("second note", "turn-1"), "into the SAME turn — the turn never ended")
        self.assertEqual(s.inflight, 3, "three feeds into one turn, settled by its one result")

    def test_the_scan_resumes_where_it_stopped(self):
        """_text_landed with a cursor: a miss records the offset after the last complete line and the next
        call starts there; a partial trailing line is re-read whole; an unchanged file is not reopened."""
        p = sb.transcript_path(self.cwd, FSID)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        sb.write_reg(self.state, SID, {**sb.read_reg(self.state, SID), "lastSid": FSID})
        junk = json.dumps({"type": "assistant", "uuid": self._uid(), "message": {"content": []}}) + "\n"
        with open(p, "w") as f:
            f.write(junk * 3)
        cur = {}
        self.assertIs(self.be._text_landed(SID, "the fed text", 0, 0, FSID, cursor=cur), False)
        self.assertEqual(cur["scan_off"], len(junk) * 3, "the cursor sits after the last complete line")
        self.assertEqual(cur["scan_fsid"], FSID)
        rec = json.dumps({"type": "user", "uuid": self._uid(), "timestamp": _iso(time.time()),
                          "message": {"role": "user", "content": "the fed text"}}) + "\n"
        with open(p, "a") as f:
            f.write(rec[:-12])                       # the CLI mid-write: no newline yet
        self.assertIs(self.be._text_landed(SID, "the fed text", 0, 0, FSID, cursor=cur), False)
        self.assertEqual(cur["scan_off"], len(junk) * 3, "a partial line is not skipped past")
        with open(p, "a") as f:
            f.write(rec[-12:])
        self.assertIs(self.be._text_landed(SID, "the fed text", 0, 0, FSID, cursor=cur), True)
        # without a cursor, the mark rule is unchanged: a scan from the file's end finds nothing
        self.assertIs(self.be._text_landed(SID, "the fed text", 0, os.path.getsize(p), FSID), False)
        self.assertIs(self.be._text_landed(SID, "the fed text", 0, 0, FSID), True)

    def test_a_reconnect_clears_the_hold_so_the_new_client_is_fed(self):
        """A hold never outlives its client: the reconnect's loop top clears it (the fed text is the
        stranded reconcile's business), so a text held behind it reaches the NEW client."""
        s, c1 = self.s, self._first_turn()
        s.enqueue("mid-turn note")
        self._wait(lambda: len(c1.writes) == 2, "the note forwarded")
        s.enqueue("held behind it")
        self._settle()
        self.assertEqual(s.pending(), ["held behind it"])
        s.request_reconnect()                          # an /effort change while busy: deferred to the turn's end
        self._wait(lambda: s._reconnect_when_idle, "the deferred reconnect armed")
        self._result_frame(c1)
        self._wait(lambda: len(self._Client.instances) == 2 and self._Client.instances[1].writes,
                   "the reconnected client to be fed")
        c2 = self._Client.instances[1]
        self.assertEqual([w[0] for w in c2.writes], ["held behind it"], "the held text went to the new client")
        self.assertEqual(c1.writes[-1][0], "mid-turn note", "nothing more was fed to the torn-down client")

    def test_a_cancel_removes_exactly_its_own_entry_of_two_wearing_the_same_words(self):
        """Two queued entries with identical text and different send ids: the ✕ pressed on the second
        removes the second (unqueue by send_id), whatever index or text the click carried."""
        s, c = self.s, self._first_turn()
        s.enqueue("go ahead")                          # fed at once, untaken: the two below are held
        self._wait(lambda: len(c.writes) == 2, "the first forwarded")
        s.enqueue("go ahead", send_id="s-aaa")
        s.enqueue("go ahead", send_id="s-bbb")
        self._settle()
        self.assertEqual([getattr(t, "send_id", "") for t in s.pending()], ["s-aaa", "s-bbb"])
        got = s.unqueue(0, "go ahead", send_id="s-bbb")   # a stale index and the shared text: the id wins
        self.assertEqual(getattr(got, "send_id", ""), "s-bbb")
        self.assertEqual([getattr(t, "send_id", "") for t in s.pending()], ["s-aaa"], "the other entry stays")
        # the kernel's cancel path resolves the same way, through the backend's pending list
        self.assertIsNone(km._cancel_backend_queued(self.be, SID, 0, "go ahead", send_id="s-aaa"))
        self.assertEqual(s.pending(), [], "…and removed exactly that entry")
        # an id the queue does not hold falls back to the body, and misses loudly when nothing matches
        self.assertTrue(km._cancel_backend_queued(self.be, SID, 0, "go ahead", send_id="s-zzz"))
        # through send(): the backend-level unqueue drops the canceled entry's OWN echo, not the first
        # echo wearing the words
        self.assertTrue(self.be.send(SID, "go ahead", send_id="s-ccc"))
        self.assertTrue(self.be.send(SID, "go ahead", send_id="s-ddd"))
        self._settle()
        self.assertEqual([getattr(q, "send_id", "") for q in s.pending()], ["s-ccc", "s-ddd"])
        got = self.be.unqueue(SID, 0, "go ahead", send_id="s-ddd")
        self.assertEqual(getattr(got, "send_id", ""), "s-ddd")
        left = [a.get("_send_id") for a in self.be.live_atoms(SID) if a.get("_echo_text") == "go ahead"]
        self.assertEqual(left, ["s-ccc"], "the other send's echo stays; the canceled one's is gone")
        self.assertEqual([getattr(q, "send_id", "") for q in s.pending()], ["s-ccc"])

    def test_the_send_id_rides_the_queue_entry_its_mirror_and_the_echo(self):
        """send(sid, text, send_id=…) → the entry carries it, the reg mirror serializes it, the
        echo carries it (for the chat's copy and the restart mirror), and a bare send stays bare."""
        s, c = self.s, self._first_turn()
        self.assertTrue(self.be.send(SID, "carry me", send_id="s-123"))
        self.assertTrue(self.be.send(SID, "plain"))
        self._wait(lambda: len(c.writes) == 2, "the first forwarded")
        self._settle()
        self.assertEqual(s.pending(), ["plain"])
        q = (sb.read_reg(self.state, SID) or {}).get("queue")
        self.assertEqual(q, ["plain"], "a bare send's mirror entry is the bare string")
        self.assertEqual(getattr(s.fed_texts()[-1], "send_id", ""), "s-123", "the fed entry carries the id")
        echoes = {a["_echo_text"]: a for a in self.be.live_atoms(SID) if a.get("_echo_text")}
        self.assertEqual(echoes["carry me"].get("_send_id"), "s-123")
        self.assertNotIn("_send_id", echoes["plain"])
        mirror = {e["text"]: e for e in (sb.read_reg(self.state, SID) or {}).get("echoes", [])}
        self.assertEqual(mirror["carry me"].get("sendId"), "s-123", "the restart mirror keeps it")
        self.assertNotIn("sendId", mirror["plain"])


class QueueEntryWire(unittest.TestCase):
    def test_round_trip_keeps_both_ids_and_the_bare_shapes(self):
        self.assertEqual(sb._queue_wire("plain"), "plain")
        self.assertEqual(sb._queue_wire(sb._QueueText("ans", "ut-1")), {"text": "ans", "todo": "ut-1"},
                         "an answer alone keeps the 2026-08-22 shape")
        self.assertEqual(sb._queue_wire(sb._QueueText("msg", "", "s-1")), {"text": "msg", "sendId": "s-1"})
        self.assertEqual(sb._queue_wire(sb._QueueText("both", "ut-2", "s-2")),
                         {"text": "both", "todo": "ut-2", "sendId": "s-2"})
        back = sb._queue_texts(["plain", {"text": "ans", "todo": "ut-1"}, {"text": "msg", "sendId": "s-1"},
                                {"text": "both", "todo": "ut-2", "sendId": "s-2"}, {"text": ""}, 7])
        self.assertEqual([str(t) for t in back], ["plain", "ans", "msg", "both"])
        self.assertEqual([getattr(t, "todo", "") for t in back], ["", "ut-1", "", "ut-2"])
        self.assertEqual([getattr(t, "send_id", "") for t in back], ["", "", "s-1", "s-2"])
        self.assertIs(type(back[0]), str, "a bare entry stays a plain str")
        self.assertIs(sb._TodoText, sb._QueueText, "the answer-only name still resolves")
        self.assertEqual(sb._TodoText("t", "ut-3").todo, "ut-3")


class TheKernelCarriesTheId(unittest.TestCase):
    def test_backend_send_passes_the_id_only_to_a_backend_that_keeps_it(self):
        calls = []
        class _Keeps:
            queue_carries_todos = True
            queue_carries_send_ids = True
            def send(self, sid, text, **kw):
                calls.append(("keeps", text, kw)); return True
        class _Plain:
            def send(self, sid, text):
                calls.append(("plain", text)); return True
        km._backend_send(_Keeps(), SID, "hi", None, "s-1")
        km._backend_send(_Keeps(), SID, "ans", "ut-1", "s-2")
        km._backend_send(_Plain(), SID, "hi", None, "s-3")
        self.assertEqual(calls, [("keeps", "hi", {"send_id": "s-1"}),
                                 ("keeps", "ans", {"user_todo": "ut-1", "send_id": "s-2"}),
                                 ("plain", "hi")])

    def test_a_landed_record_is_stamped_with_the_ids_of_every_send_it_landed(self):
        """_note_send_landings: two sends in order wearing the same words map to their two records in
        order; a record that wears two sends' words (the CLI's fold) carries both ids; a send whose text
        has not landed maps nothing."""
        t0 = 1_700_000_000
        live = [{"_echo_text": "ship it", "_send_id": "s-1", "t": t0 + 1, "uuid": "echo:1"},
                {"_echo_text": "ship it", "_send_id": "s-2", "t": t0 + 2, "uuid": "echo:2"},
                {"_echo_text": "first words", "_send_id": "s-3", "t": t0 + 3, "uuid": "echo:3"},
                {"_echo_text": "Re: the ask — the reply", "_send_id": "s-4", "t": t0 + 3, "uuid": "echo:4"},
                {"_echo_text": "still in the queue", "_send_id": "s-5", "t": t0 + 4, "uuid": "echo:5"}]
        def user(uuid, t, content):
            return {"type": "user", "uuid": uuid, "t": t, "message": {"role": "user", "content": content}}
        turns = [{"atoms": [user("old", t0 - 50, "ship it")]},                       # before every send
                 {"atoms": [user("r1", t0 + 5, "ship it"), user("r2", t0 + 6, "ship it"),
                            user("r3", t0 + 7, [{"type": "text", "text": "first words"},
                                                {"type": "text", "text": "Re: the ask — the reply"}])]}]
        tx_text_t = {}
        for turn in turns:
            for a in turn["atoms"]:
                for k in km._atom_user_texts(a):
                    tx_text_t[k] = max(tx_text_t.get(k, 0), a["t"])
        km._landed_send_ids.pop(SID, None)
        km._note_send_landings(SID, live, turns, tx_text_t)
        ids = {u: v["ids"] for u, v in km._landed_send_ids[SID].items()}
        self.assertEqual(ids, {"r1": ["s-1"], "r2": ["s-2"], "r3": ["s-3", "s-4"]})
        self.assertNotIn("old", ids, "a record before the send is never this send's")
        # idempotent across builds: the same echoes map to the same records, nothing doubles
        km._note_send_landings(SID, live, turns, tx_text_t)
        self.assertEqual({u: v["ids"] for u, v in km._landed_send_ids[SID].items()}, ids)
        km._landed_send_ids.pop(SID, None)


if __name__ == "__main__":
    unittest.main()
