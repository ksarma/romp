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
The review round (2026-09-08) tightened four edges, each pinned below:
  * a turn romp did not feed is COUNTED: a turn frame at inflight 0 raises inflight (the CLI's drain of a
    mid-turn text, or a turn a notification started), so a text fed into that turn is mid-turn, not
    "fresh", and its hold waits for its own take instead of clearing on the running turn's next frame;
  * only the init, assistant, user and result frames witness a take; task, hook, status and progress
    frames stream independently of the queue and release nothing;
  * a landing scan that raises is a logged fault the hold escapes from at the next turn frame (at once
    when that frame is the result), never a silent per-frame miss that parks the queue for good;
  * a reconnect defers while a hold is live (the CLI still owes the drain), and a hold that reaches the
    loop top anyway hands its text to the stranded reconcile (re-head or a flagged echo, never a drop).
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
import threading
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

    def _sys(self, client, subtype):
        """A system frame that is NOT the init: the CLI's background-task, hook and status machinery
        streams these on its own clock, turn or no turn, and none says anything about its prompt queue."""
        self._push(client, _SystemMessage(subtype, {"task_id": "t-1", "status": "running"}, uuid=self._uid()))

    def _user_record(self, text):
        """The CLI's own transcript record of a user turn."""
        return {"type": "user", "uuid": self._uid(), "timestamp": _iso(time.time()),
                "message": {"role": "user", "content": text}}

    def _fault_the_transcript(self):
        """Make the landing scan RAISE: a directory where the transcript file was (open() fails on it).
        The scan reports the fault to its caller as None."""
        p = self._transcript()
        os.remove(p)
        os.makedirs(p)

    def _fault_lines(self):
        return [l for l in self.lines if l.startswith("feed hold (")]

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
        # the CLI writes the turn's user record as it starts the turn, so by the time anything can be fed
        # mid-turn the transcript exists: the landing scans below read a real file (a file the scan
        # cannot read is a FAULT it reports, pinned separately)
        self._append(self._user_record("first turn"))
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
        self.assertEqual([(str(t), getattr(t, "todo", "")) for t in s.fed_texts()],
                         [("can you also check the tests", ""), (answer, "ut-11111111")],
                         "the drained message rejoined the fed-turn twin (its turn is running) and the fed "
                         "answer behind it still carries the ask's id")

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

    def test_a_deferred_reconnect_waits_until_the_cli_has_taken_the_text_it_still_holds(self):
        """An /effort change while busy defers to the turn's end. When a text was fed mid-turn, that
        turn's result is NOT the moment: the CLI still holds the text and drains it into a turn right
        after, and a teardown at the result killed the CLI with the message in its queue (nothing
        re-fed it, nothing flagged it; 2026-09-08 review). The arm stays set; the drained turn's first
        frame counts that turn and its result fires the reconnect, on the frame that proves the text
        left the queue. Nothing is re-fed and nothing is flagged: the message was delivered."""
        s, c1 = self.s, self._first_turn()
        self.assertTrue(self.be.send(SID, "mid-turn note", send_id="s-note"))
        self._wait(lambda: len(c1.writes) == 2, "the note forwarded")
        s.request_reconnect()                          # an /effort change while busy: deferred to the turn's end
        self._wait(lambda: s._reconnect_when_idle, "the deferred reconnect armed")
        c1.phase = "after-result-1"
        self._result_frame(c1)
        self._wait(lambda: s.inflight == 0 and s._untaken and s._untaken.get("settled"),
                   "the turn settled with the note still in the CLI's queue")
        self._settle()
        self.assertEqual(len(self._Client.instances), 1, "no teardown at this result: the CLI still holds the note")
        self.assertFalse(c1.torn_down)
        self.assertTrue(s._reconnect_when_idle, "the arm waits for the take")
        c1.phase = "turn-2"
        self._init(c1)                                 # the drained turn: the note left the CLI's queue
        self._wait(lambda: s._untaken is None and s.inflight == 1, "the drain counted as a turn")
        self.assertEqual(s.fed_texts(), ["mid-turn note"], "the drained text rides the fed-turn twin")
        self._settle()
        self.assertEqual(len(self._Client.instances), 1, "the drained turn runs to its end first")
        self._result_frame(c1)
        self._wait(lambda: len(self._Client.instances) == 2 and self._Client.instances[1] is s.client,
                   "the reconnect at the drained turn's result")
        c2 = self._Client.instances[1]
        self.assertTrue(c1.torn_down)
        self.assertEqual([w[0] for w in c1.writes], ["first turn", "mid-turn note"])
        self.assertEqual(c2.writes, [], "nothing re-fed: the note was delivered")
        echo = next(a for a in self.be.live_atoms(SID) if a.get("_echo_text") == "mid-turn note")
        self.assertFalse(echo.get("dropped"), "…and nothing flagged")
        self.assertEqual(s.inflight, 0)
        s.enqueue("after the reconnect")
        self._wait(lambda: c2.writes, "the new client fed")
        self.assertEqual([w[0] for w in c2.writes], ["after the reconnect"])

    def test_a_reconnect_asked_for_while_the_cli_still_holds_a_text_is_deferred_not_immediate(self):
        """The immediate arm: after a mid-turn feed's result the counters read idle (inflight 0, queue
        empty) while the text sits in the CLI's queue. A reconnect asked for in that gap defers; the
        key cycle's no-defer form is refused with its log line, as when a turn is running."""
        s, c1 = self.s, self._first_turn()
        s.enqueue("mid-turn note")
        self._wait(lambda: len(c1.writes) == 2, "the note forwarded")
        self._result_frame(c1)
        self._wait(lambda: s.inflight == 0 and s._untaken and s._untaken.get("settled"), "settled, untaken")
        self.assertEqual(s.pending(), [])
        s.request_reconnect()
        self._wait(lambda: s._reconnect_when_idle, "deferred, not fired")
        self._settle()
        self.assertEqual(len(self._Client.instances), 1, "the CLI keeps running: it still holds the note")
        s.request_reconnect(defer=False)
        self._wait(lambda: any("not cycled" in l for l in self.lines), "the no-defer form refused, loudly")
        self.assertEqual(len(self._Client.instances), 1)
        c1.phase = "turn-2"
        self._init(c1)
        self._wait(lambda: s.inflight == 1 and s._untaken is None, "the drain counted")
        self._result_frame(c1)
        self._wait(lambda: len(self._Client.instances) == 2, "the deferred reconnect fired at the drained turn's result")
        self.assertEqual([w[0] for w in c1.writes], ["first turn", "mid-turn note"])

    def test_a_teardown_that_finds_a_settled_hold_hands_its_text_to_the_stranded_reconcile(self):
        """The backstop: a teardown that armed some other way while a hold is settled (the reconnect
        arms defer, so nothing in the kernel does this today). The hold's text is in neither counter at
        that point; the loop top puts it back into the fed-turn twin so the reconcile treats it as the
        stranded turn it is: on a resumable conversation its echo is flagged 'never delivered' (the
        same flag-only branch every stranded turn takes there), never re-fed, never silently gone."""
        s, c1 = self.s, self._first_turn()
        self.assertTrue(self.be.send(SID, "mid-turn note", send_id="s-note"))
        self._wait(lambda: len(c1.writes) == 2, "the note forwarded")
        self._result_frame(c1)
        self._wait(lambda: s.inflight == 0 and s._untaken and s._untaken.get("settled"), "settled, untaken")
        s.loop.call_soon_threadsafe(lambda: (setattr(s, "_reconnect", True), s._wake_set()))
        self._wait(lambda: len(self._Client.instances) == 2 and s.client is self._Client.instances[1],
                   "the forced reconnect")
        self._settle()
        self.assertIsNone(s._untaken)
        self.assertEqual(s.inflight, 0, "the reconcile settled the counter it was handed")
        self.assertEqual(s.fed_texts(), [])
        self.assertEqual(s.pending(), [], "resumable: never re-fed (the record may have landed)")
        self.assertEqual(self._Client.instances[1].writes, [])
        echo = next(a for a in self.be.live_atoms(SID) if a.get("_echo_text") == "mid-turn note")
        self.assertTrue(echo.get("dropped"), "the loss is visible in the chat")
        self.assertTrue(any("never reached its CLI" in l for l in self.lines), "…and in the log")

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
        # an id the queue does not hold misses: nothing is removed and no body fallback runs (the rule is
        # pinned in tests/test_queued_sends_kernel.py, CancelBackendQueuedById and CancelParkedById)
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


    def test_a_text_fed_into_the_drained_turn_is_mid_turn_and_waits_for_its_own_take(self):
        """The review's high finding: after the drained turn's first frame released the settled hold,
        inflight read 0 (the settle zeroed it and nothing counted the drain), so a text fed into the
        running drained turn was 'fresh' and its hold cleared on that turn's very next frame with the
        text still in the CLI's queue; the text behind it was fed to fuse with it. Now the drain's
        first frame COUNTS the turn: the text fed into it is mid-turn, the running turn's frames prove
        nothing, and the text behind it waits for the drained turn's result plus the next turn's frame."""
        s, c = self.s, self._first_turn()
        s.enqueue("B mid-turn")
        self._wait(lambda: len(c.writes) == 2, "B forwarded")
        c.phase = "after-result-1"
        self._result_frame(c)
        self._wait(lambda: s.inflight == 0 and s._untaken and s._untaken.get("settled"), "B's turn settled")
        self.assertEqual(s.fed_texts(), [], "the settle cleared the twin")
        c.phase = "turn-2"
        self._init(c)                                   # the drain: B's own turn begins
        self._wait(lambda: s._untaken is None and s.inflight == 1, "the drain released B's hold AND counted its turn")
        self.assertEqual(s.fed_texts(), ["B mid-turn"], "the drained text is back in the fed-turn twin")
        self.assertTrue(self.be.busy(SID), "busy() reads the CLI's turn")
        s.enqueue("C into the drained turn")
        self._wait(lambda: len(c.writes) == 3, "C forwarded into B's turn")
        self.assertEqual(c.writes[2], ("C into the drained turn", "turn-2"))
        self.assertIs(s._untaken["fresh"], False, "C went into a running turn, not from idle")
        self.assertEqual(s.inflight, 2)
        s.enqueue("D behind C")
        self._settle()
        self.assertEqual(len(c.writes), 3, "D waits: C is untaken")
        self._assistant(c, "turn 2 keeps going")       # a frame of the running turn: not C's take
        self._settle()
        self.assertEqual(len(c.writes), 3, "the drained turn's next frame does NOT release C's hold")
        self.assertEqual(s.pending(), ["D behind C"])
        c.phase = "after-result-2"
        self._result_frame(c)
        self._wait(lambda: s.inflight == 0, "turn 2 settled")
        self._settle()
        self.assertEqual(len(c.writes), 3, "the result alone is not the take either")
        c.phase = "turn-3"
        self._init(c)
        self._wait(lambda: len(c.writes) == 4, "D fed once C's drain showed")
        self.assertEqual(c.writes[3], ("D behind C", "turn-3"))
        self.assertEqual([w[0] for w in c.writes], ["first turn", "B mid-turn", "C into the drained turn", "D behind C"])

    def test_a_turn_the_cli_started_itself_is_counted_and_a_send_into_it_waits_for_its_take(self):
        """The finding's other variant: a subagent's or task's notification wakes an idle CLI and it
        runs a turn romp never fed. Its turn frames count the turn (busy reads it); a send during it is
        mid-turn and its hold does not clear on the turn's next frame; the send behind it waits for the
        result plus the next turn's frame. Frames that are not turn frames count nothing at idle."""
        s, c = self.s, self._first_turn()
        c.phase = "after-result-1"
        self._result_frame(c)
        self._wait(lambda: s.inflight == 0, "idle")
        self.assertFalse(self.be.busy(SID))
        self._sys(c, "task_notification")               # a background task finished: not a turn
        self._sys(c, "hook_started")
        self._push(c, _RateLimitEvent())
        self._settle()
        self.assertEqual(s.inflight, 0, "no turn frame, no turn")
        c.phase = "auto-turn"
        self._init(c)                                   # the CLI starts a turn on its own
        self._wait(lambda: s.inflight == 1, "the CLI's own turn counted")
        self.assertEqual(s.fed_texts(), [], "…with no fed text of romp's in it")
        self.assertTrue(self.be.busy(SID))
        self._assistant(c)
        s.enqueue("first composer send")
        self._wait(lambda: len(c.writes) == 2, "the send forwarded into the running turn")
        self.assertEqual(c.writes[1], ("first composer send", "auto-turn"))
        self.assertIs(s._untaken["fresh"], False)
        self.assertEqual(s.inflight, 2)
        s.enqueue("second composer send")
        self._assistant(c, "the auto turn continues")
        self._settle()
        self.assertEqual(len(c.writes), 2, "the second send waits: the first is untaken and the turn's frames prove nothing")
        c.phase = "after-auto"
        self._result_frame(c)
        self._wait(lambda: s.inflight == 0, "the auto turn settled")
        self._settle()
        self.assertEqual(len(c.writes), 2, "not at the result either")
        c.phase = "turn-3"
        self._assistant(c, "the drained turn's first frame")   # an assistant frame at inflight 0 counts too
        self._wait(lambda: len(c.writes) == 3, "the second send fed once the first was drained")
        self.assertEqual(c.writes[2], ("second composer send", "turn-3"))
        self.assertEqual(s.inflight, 2, "the drained turn counted, plus the feed into it")

    def test_only_turn_frames_witness_a_take_never_a_task_hook_or_progress_frame(self):
        """The CLI streams system frames from its background-task and hook machinery regardless of its
        prompt queue (task_started/progress/notification, background_tasks_changed, hook_started,
        status), and the SDK types each as a SystemMessage. None is a take: one arriving between a feed
        from idle and the turn's init, or between a result and the drain, must not release the hold:
        the next text would go into exactly the window the hold protects. Only the init, an assistant
        message, the CLI's own user record and the result count."""
        S = sb.SdkSession._turn_frame
        class _UserMessage:                              # the SDK's shape, by name (duck-typed in the kernel)
            pass
        _UserMessage.__name__ = "UserMessage"
        for st in ("task_started", "task_progress", "task_updated", "task_notification",
                   "background_tasks_changed", "hook_started", "hook_response", "status", "compact_boundary"):
            self.assertFalse(S(_SystemMessage(st), _AssistantMessage, _ResultMessage, _SystemMessage), st)
        self.assertFalse(S(_RateLimitEvent(), _AssistantMessage, _ResultMessage, _SystemMessage))
        self.assertTrue(S(_SystemMessage("init"), _AssistantMessage, _ResultMessage, _SystemMessage))
        self.assertTrue(S(_AssistantMessage([]), _AssistantMessage, _ResultMessage, _SystemMessage))
        self.assertTrue(S(_result(), _AssistantMessage, _ResultMessage, _SystemMessage))
        self.assertTrue(S(_UserMessage(), _AssistantMessage, _ResultMessage, _SystemMessage))
        # through the stream: the fresh gap
        s, c = self.s, self._first_turn()
        c.phase = "after-result-1"
        self._result_frame(c)
        self._wait(lambda: s.inflight == 0, "idle")
        c.phase = "pre-turn-2"
        s.enqueue("A from idle")
        self._wait(lambda: len(c.writes) == 2, "A fed")
        self.assertTrue(s._untaken["fresh"])
        s.enqueue("B behind it")
        for st in ("task_started", "task_progress", "task_notification", "background_tasks_changed",
                   "hook_started", "status", "compact_boundary"):
            self._sys(c, st)
        self._push(c, _RateLimitEvent())
        self._settle()
        self.assertEqual(len(c.writes), 2, "no system subtype but the init releases a fresh hold")
        self.assertEqual(s.inflight, 1, "…and none counts a turn")
        c.phase = "turn-2"
        self._init(c)
        self._wait(lambda: len(c.writes) == 3, "the init is the take")
        self.assertEqual(c.writes[2], ("B behind it", "turn-2"))
        # the settled gap: B is untaken in turn 2, C waits
        s.enqueue("C held")
        c.phase = "after-result-2"
        self._result_frame(c)
        self._wait(lambda: s.inflight == 0 and s._untaken and s._untaken.get("settled"), "settled")
        self._sys(c, "task_progress")
        self._sys(c, "task_notification")
        self._settle()
        self.assertEqual(len(c.writes), 3, "a task frame in the drain gap is not the drain")
        self.assertEqual(s.inflight, 0)
        c.phase = "turn-3"
        self._init(c)
        self._wait(lambda: len(c.writes) == 4, "the drain's init is")
        self.assertEqual(c.writes[3], ("C held", "turn-3"))

    def test_a_take_scan_that_raises_is_logged_once_and_the_hold_escapes_on_the_next_turn_frame(self):
        """The landing scan answers None when it cannot read the transcript. Read as a miss, that held
        the queue for good once the fed text had been consumed mid-turn (no frame ever comes to release
        a settled hold whose text is not in the CLI's queue), silently, per frame. It is a fault: one
        problem line per hold, and the hold escapes on the next turn frame."""
        s, c = self.s, self._first_turn()
        s.enqueue("first note")
        self._wait(lambda: len(c.writes) == 2, "the first note forwarded")
        s.enqueue("second note")
        self._settle()
        self.assertEqual(len(c.writes), 2)
        self._fault_the_transcript()
        self._assistant(c)                              # the scan raises here
        self._settle()
        self.assertEqual(len(c.writes), 2, "the frame that met the fault is not yet the escape")
        self.assertTrue(s._untaken and s._untaken.get("fault"), "the hold knows")
        self.assertEqual(len(self._fault_lines()), 1, "one problem line")
        self.assertIn("IsADirectoryError", self._fault_lines()[0], "…naming the fault")
        self._assistant(c)                              # the next turn frame
        self._wait(lambda: len(c.writes) == 3, "the second note fed: the hold escaped")
        self.assertEqual(c.writes[2], ("second note", "turn-1"))
        self._assistant(c)
        self._settle()
        self.assertEqual(len(self._fault_lines()), 1, "one line for that hold, however many frames followed")

    def test_a_faulted_hold_escapes_at_the_result_when_nothing_later_streams(self):
        """The never-arrives path: the fault is met at the result itself. After a result nothing later is
        guaranteed to stream (a text consumed mid-turn leaves the CLI's queue empty), so a faulted hold
        escapes AT the result rather than waiting for a frame that may never come."""
        s, c = self.s, self._first_turn()
        s.enqueue("first note")
        self._wait(lambda: len(c.writes) == 2, "the first note forwarded")
        s.enqueue("second note")
        self._settle()
        self._fault_the_transcript()
        c.phase = "after-result-1"
        self._result_frame(c)
        self._wait(lambda: len(c.writes) == 3, "the second note fed at the result")
        self.assertEqual(c.writes[2], ("second note", "after-result-1"))
        self.assertEqual(len(self._fault_lines()), 1)
        self.assertTrue(s._untaken["fresh"], "fed from idle: the next turn's frame releases it as ever")

    def test_a_redelivered_send_keeps_its_id_on_the_live_arm_as_on_the_reg_arm(self):
        """A fresh CLI spawn re-delivers the typed sends the dead one held (_mark_dropped_echoes). The
        live-session arm enqueued the text without its send id while the reg arm kept it: the re-queued
        chip had no id, and its ✕ fell back to index and text. Both arms carry it now."""
        be, s = self.be, self.s                         # registered in setUp, never started: the live arm
        p = sb.transcript_path(self.cwd, SID)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "a").close()                            # readable and empty: the scan answers False (nothing landed)
        now = int(time.time())
        be._stash_live(SID, "echo:1", {"type": "user", "uuid": "echo:1", "session_id": SID, "t": now,
                                       "author": "human", "_echo_text": "carry me", "_send_id": "s-77"})
        be._mark_dropped_echoes(SID, s.pending())
        self.assertEqual([(str(t), getattr(t, "send_id", "")) for t in s.pending()], [("carry me", "s-77")],
                         "the live arm's entry carries the id")
        self.assertEqual((sb.read_reg(self.state, SID) or {}).get("queue"), [{"text": "carry me", "sendId": "s-77"}],
                         "…and its mirror")
        be.sessions.pop(SID)                            # no session object: the boot reseed's reg arm
        be._stash_live(SID, "echo:2", {"type": "user", "uuid": "echo:2", "session_id": SID, "t": now + 1,
                                       "author": "human", "_echo_text": "carry me too", "_send_id": "s-78"})
        be._mark_dropped_echoes(SID, ["carry me"])
        self.assertEqual((sb.read_reg(self.state, SID) or {}).get("queue"),
                         [{"text": "carry me", "sendId": "s-77"}, {"text": "carry me too", "sendId": "s-78"}])

    def test_the_queue_mirror_never_loses_an_entry_to_an_interleaved_persist(self):
        """_persist_queue snapshots under one lock and writes under another, from two threads: the
        feeder's post-pop persist (empty snapshot) racing an enqueue's persist (the new entry) could
        write in the order snapshot-A, snapshot-B, write-B, write-A and leave the mirror without the
        entry _pending held (a load-dependent failure of the mirror test below). One persist at a time."""
        s, be = self.s, self.be
        real = be._update_reg
        entered, go = threading.Event(), threading.Event()

        def slow_update(sid, **fields):
            if fields.get("queue") == [] and not entered.is_set():   # the post-pop persist, delayed inside its write
                entered.set()
                go.wait(5)
            return real(sid, **fields)
        be._update_reg = slow_update
        try:
            a = threading.Thread(target=s._persist_queue)       # _pending is empty: the snapshot after a pop
            a.start()
            self.assertTrue(entered.wait(5))
            b = threading.Thread(target=lambda: s.enqueue("plain"))
            b.start()
            b.join(1.0)                                         # unserialized, b's write lands here, ahead of a's
            go.set()
            a.join(5)
            b.join(5)
        finally:
            be._update_reg = real
        self.assertEqual((sb.read_reg(self.state, SID) or {}).get("queue"), ["plain"],
                         "the mirror ends as the latest snapshot, never the stale empty one")


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
