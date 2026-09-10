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
Round 2 (2026-09-08) pinned three more:
  * an accepted live move's init (no query; the CLI answers a set_cwd with an init and a turn-less result)
    counts no CLI-owned turn, and the move's result zeroes a count that fired anyway: an idle session stays
    idle (busy() False, a reconnect fires at once);
  * busy() reads a live hold as in flight, as the reconnect gate does, so a drive op or a slash command
    pressed in the settled gap parks instead of landing in the drained turn as text;
  * the CLI's EXIT is the one event that loses its queue (the interrupt is not: verified on CLI 2.1.263,
    which drains a queued text into a new turn right after the interrupted result, while a SIGINT makes it
    exit without running the text): at the exit a held text that never landed goes back to the head of the
    queue for the next client; one the CLI took is left alone; an unreadable transcript flags, never re-feeds.
Round 3 (2026-09-08) pinned two more:
  * a stale move arm (the CLI accepted a set_cwd and never emitted the turn-less result) is dropped at a
    real turn's result and at the loop top, so it cannot switch the CLI-owned-turn count off for the
    session's life and re-open the fuse the count closes;
  * the exit release applies _reconcile_stranded's distinction: when no conversation ever materialised
    (no init streamed) a transcript the scan cannot read re-heads the text, since the next client starts
    fresh and a re-feed cannot duplicate; a resumable conversation keeps the flag path.
Round 4 (2026-09-08) pinned one more:
  * the feeder holds the head while a move's settle is expected (move() armed _move_settle_expected and the
    CLI is relocating for its set_cwd): a text fed into that window could run a whole turn before the move's
    turn-less result, whose late arrival the settle would then take for a turn end. The hold lifts on the
    exact events that lower the arm (the move's result consumed; move() refused), never on a timer, and the
    move's own request rides the control channel, so the hold never delays it.
Round 5 (2026-09-08) pinned two more:
  * move()'s exits drop the claim (cwdPending) whatever the disarm does, and the disarm tolerates the closed
    loop of a session whose CLI exited after the claim: move() returns the SDK's named error, not a raise, and
    a later move is not refused as already pending;
  * a lost reply after the CLI relocated keeps the arm, and the hold it leaves on the queue is announced on the
    problem ring (the session named, queued sends wait for the move's result); the chip shows the text queued,
    busy() reads it, and the hold ends on the exact event that lowers the arm, never on a timer.
Round 6 (2026-09-08) pinned one more:
  * move()'s standing-down exits (rejected, nothing changed, no control sender, and the uncertain outcome whose
    heal finds the move never happened) lower the arm and THEN drop the claim: the claim keeps a second move()
    of the sid out, and a second mover claims and arms the moment it is released, so round 5's drop-first order
    lowered the second move's arm and left its relocation with the queue unheld. The drop still happens
    whatever the disarm does, and the uncertain exit names its answer from the heal's own outcome, not from a
    re-read of a reg the released claim no longer guards.
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
_EOF = object()   # pushed as a frame: the CLI process exited, its stream ends (receive_messages returns)


class _ControlChannel:
    """The SDK client's private control-request sender, scripted and GATED: the request is recorded the
    moment it is sent (it rides the control channel, not the feeder), and the CLI's answer waits for the
    test's gate, which stands in for the relocation the CLI performs BEFORE it replies to a set_cwd."""
    instances = []                       # every channel a test made, for tearDown's gate sweep: the client's
    #                                      _query is only the LAST one, and a channel a later _start_move (or a
    #                                      subTest that failed before its gate.set) replaced stays shut otherwise

    def __init__(self, answer, on_request=None):
        self.answer, self.requests, self.gate = answer, [], threading.Event()
        self.on_request = on_request     # what the CLI does on receipt, before any answer (a relocation)
        self.worker = None               # the loop's executor thread, once it is parked in gate.wait
        type(self).instances.append(self)

    def _park(self):
        self.worker = threading.current_thread()
        self.gate.wait()

    async def _send_control_request(self, req):
        if self.on_request is not None:
            self.on_request(dict(req))
        self.requests.append(dict(req))
        await asyncio.get_running_loop().run_in_executor(None, self._park)
        return self.answer
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
            self.loop = asyncio.get_running_loop()   # the session loop this client serves (a respawn has its own)
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
                if f is _EOF:
                    return          # the CLI process exited: the stream ends, and its queue died with it
                yield f

    class _Options:
        def __init__(self, **kw):
            self.session_id = self.resume = None
            for k, v in kw.items():
                setattr(self, k, v)

    def setUp(self):
        sb.SdkSession._stream_fail_seen.clear()
        self._Client.instances = []
        _ControlChannel.instances = []
        fake = types.ModuleType("claude_agent_sdk")
        fake.__spec__ = ModuleSpec("claude_agent_sdk", loader=None)
        fake.ClaudeSDKClient, fake.ClaudeAgentOptions, fake.HookMatcher = self._Client, self._Options, (lambda **kw: kw)
        fake.AssistantMessage, fake.ResultMessage = _AssistantMessage, _ResultMessage
        fake.SystemMessage, fake.TextBlock = _SystemMessage, _TextBlock
        self._saved_sdk = sys.modules.get("claude_agent_sdk")
        sys.modules["claude_agent_sdk"] = fake
        # a session the backend respawns itself (the exit tests) has no per-instance stub: quiet the class
        async def _noop_refresh(self): pass
        self._saved_refresh = sb.SdkSession._do_refresh_usage
        sb.SdkSession._do_refresh_usage = _noop_refresh
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
        for q in _ControlChannel.instances:
            q.gate.set()     # a gate still shut (a move whose CLI never answered; a subTest that failed between a
            #                  _start_move and its gate.set) parks the loop's executor thread in gate.wait: the join
            #                  below sat out its whole 10 s on it, and a worker still parked at interpreter exit
            #                  hangs the pytest process for good (concurrent.futures joins it without a timeout).
            #                  Open every gate first, here rather than in a cleanup, which unittest runs AFTER
            #                  tearDown, and from the fake's registry rather than the client's _query, which names
            #                  only the LAST channel: the one a later _start_move replaced would stay shut
        sessions = {id(x): x for x in [self.s] + list(self.be.sessions.values())}.values()   # respawns too
        for x in sessions:
            if x.thread.is_alive():          # a session whose CLI exited already closed its loop
                x.shutdown()
        for x in sessions:
            if x.thread.ident is not None:
                x.thread.join(timeout=10)
        sb.SdkSession._do_refresh_usage = self._saved_refresh
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
        client.loop.call_soon_threadsafe(client.frames.put_nowait, frame)

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

    def _move_result(self, client):
        """The turn-less result an accepted set_cwd emits after its init (verified 2026-09-02): num_turns 0."""
        self._push(client, _result(uuid=self._uid(), subtype="success", is_error=False, num_turns=0,
                                   session_id=FSID, duration_ms=0, duration_api_ms=0, total_cost_usd=0.0,
                                   usage={}, result="", parent_tool_use_id=None))

    def _interrupted_result(self, client):
        """The result of an interrupted turn, as CLI 2.1.263 emits it: error_during_execution, is_error."""
        self._push(client, _result(uuid=self._uid(), subtype="error_during_execution", is_error=True,
                                   num_turns=2, session_id=FSID, duration_ms=1, duration_api_ms=1,
                                   total_cost_usd=0.01, usage={"input_tokens": 1, "output_tokens": 1},
                                   result=None, parent_tool_use_id=None))

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
        # The init handler flips resume_sid in memory and persists it as the reg's lastSid one statement
        # later, on the loop thread. _transcript() keys the path on the REG, so wait for the write, not the
        # flip: a poll that landed between the two filed the record below under the module's own sid, and
        # every later reader of the CLI's transcript (the take check's scan, a move's heal, the fault
        # helper's os.remove) missed it (a CI flake, 2026-09-10; reproduced by delaying the reg write 10 ms).
        self._wait(lambda: s._untaken is None and s.resume_sid == FSID
                   and (sb.read_reg(self.state, SID) or {}).get("lastSid") == FSID,
                   "the first turn's start releases its hold and the init's lastSid is in the reg")
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
    def test_the_first_turns_record_lands_under_the_clis_sid_however_late_the_reg_write(self):
        """The helper's own race, pinned (2026-09-10): the init handler flips resume_sid in memory and
        persists it as the reg's lastSid one statement later, and _first_turn once returned on the flip,
        so a poll in that gap filed the record under the module's own sid, where the take check's scan,
        the fault helper and the move test's relocation never found it. A reg write that lands 50 ms
        late (five poll periods: a descheduled loop thread on a loaded runner) stands in for the gap."""
        from unittest import mock
        orig = sb.SdkBackend._update_reg
        def late(be, sid, **fields):
            if "lastSid" in fields:
                time.sleep(0.05)
            return orig(be, sid, **fields)
        with mock.patch.object(sb.SdkBackend, "_update_reg", late):
            self._first_turn()
        self.assertTrue(os.path.exists(sb.transcript_path(self.cwd, FSID)), "the record is under the CLI's sid")
        self.assertFalse(os.path.exists(sb.transcript_path(self.cwd, SID)), "…and not under the module's")

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
        immediate-only form (defer=False) is refused with its log line, as when a turn is running. The
        line reads 'not reconnected' since the 2026-09-09 fold: upstream #1128 retired the key cycle
        that was this form's caller and renamed the line; the refusal itself is unchanged."""
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
        self._wait(lambda: any("not reconnected" in l for l in self.lines), "the no-defer form refused, loudly")
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
        # the CLI-started turn's 0->1 raise in _on_message re-baselines the scope's OOM counter, like a fed turn's
        # raise in the feeder (the scope PR's round 3, 2026-09-10): count the snapshots through the instance
        snaps = []
        orig_snapshot = s._snapshot_oom_baseline
        s._snapshot_oom_baseline = lambda: (orig_snapshot(), snaps.append(1))
        c.phase = "auto-turn"
        self._init(c)                                   # the CLI starts a turn on its own
        self._wait(lambda: s.inflight == 1, "the CLI's own turn counted")
        self.assertEqual(len(snaps), 1, "the CLI-started turn re-baselined the OOM counter at its raise")
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

    # -- round 2 (2026-09-08) --
    def test_an_accepted_live_move_leaves_an_idle_session_idle(self):
        """An accepted set_cwd makes the CLI emit an init and a turn-less result (num_turns 0) with no query,
        then commands_changed frames. The init is a turn frame at inflight 0, so the CLI-owned-turn count
        read it as a turn the settle never zeroed (_consume_move_settle skips the settle on purpose): the
        idle session stayed busy until its next real turn, a reconnect asked for in between deferred, a
        drive op parked. The count skips the init while the move's settle is expected; the session stays
        idle and a reconnect fires at once."""
        s, c = self.s, self._first_turn()
        c.phase = "after-result-1"
        self._result_frame(c)
        self._wait(lambda: s.inflight == 0, "idle")
        s.loop.call_soon_threadsafe(setattr, s, "_move_settle_expected", True)   # move() arms BEFORE its request
        c.phase = "move"
        self._init(c)                                    # the CLI relocated: its init, no query behind it
        self._move_result(c)
        self._sys(c, "commands_changed")
        self._sys(c, "commands_changed")
        self._wait(lambda: not s._move_settle_expected, "the move's turn-less result consumed")
        self._settle()
        self.assertEqual(s.inflight, 0, "the move's init is no turn of the CLI's")
        self.assertEqual(s.fed_texts(), [])
        self.assertFalse(self.be.busy(SID), "an idle session stays idle after an accepted move")
        s.request_reconnect()                            # an /effort change right after the move
        self._wait(lambda: len(self._Client.instances) == 2 and self._Client.instances[1] is s.client,
                   "the reconnect fired at once, not deferred to a turn end that never comes")
        self.assertFalse(s._reconnect_when_idle)
        self.assertEqual(c.writes, [("first turn", "turn-1")], "nothing fed by the move")

    def test_the_moves_turn_less_result_zeroes_a_count_that_fired_anyway(self):
        """The backstop: should the count have read the move's init as a turn (nothing fed, an empty fed-turn
        twin), the turn-less result is the last frame the move emits, so it zeroes the count rather than
        leaving the session busy until some later real turn."""
        s, c = self.s, self._first_turn()
        c.phase = "after-result-1"
        self._result_frame(c)
        self._wait(lambda: s.inflight == 0, "idle")
        self._init(c)                                    # counted: the arm was not up yet
        self._wait(lambda: s.inflight == 1, "a CLI-owned turn counted")
        self.assertTrue(self.be.busy(SID))
        s.loop.call_soon_threadsafe(setattr, s, "_move_settle_expected", True)
        self._move_result(c)
        self._wait(lambda: s.inflight == 0, "the move's turn-less result zeroed the stray count")
        self.assertFalse(self.be.busy(SID))
        self.assertFalse(s._move_settle_expected, "the arm is spent")

    def test_busy_reads_a_settled_hold_as_in_flight_like_the_reconnect_gate(self):
        """After a mid-turn feed's result the counters read idle while the CLI still holds the text and is
        about to drain it into a turn. The reconnect gate reads that hold as in flight (round 1); busy()
        did not, so the kernel's _working_now let a parked /compact drain and a typed slash command bypass
        the park in that gap, and the feeder then fed them into the drained turn mid-turn, as text. busy()
        reads the hold now: True in the gap, True through the drained turn, False at its result."""
        s, c = self.s, self._first_turn()
        s.enqueue("mid-turn note")
        self._wait(lambda: len(c.writes) == 2, "the note forwarded")
        c.phase = "after-result-1"
        self._result_frame(c)
        self._wait(lambda: s.inflight == 0 and s._untaken and s._untaken.get("settled"), "settled, untaken")
        self.assertEqual(s.pending(), [])
        self.assertTrue(self.be.busy(SID), "the CLI still holds a text it drains into a turn next: a drive op parks")
        c.phase = "turn-2"
        self._init(c)
        self._wait(lambda: s._untaken is None and s.inflight == 1, "the drain counted")
        self.assertTrue(self.be.busy(SID), "…and the drained turn is a turn")
        self._result_frame(c)
        self._wait(lambda: s.inflight == 0, "its result")
        self.assertFalse(self.be.busy(SID), "idle for real now")

    def test_an_interrupt_keeps_the_held_text_in_the_clis_queue_and_its_drain_releases_the_hold(self):
        """The kernel's interrupt is NOT a loss event. Real CLI 2.1.263 over stream-json (2026-09-08): a text
        queued mid-turn survived the interrupt control request; the interrupted turn's result
        (error_during_execution) was followed 6 ms later by a new init and the queued text's own turn, and
        the CLI's schema says queued commands survive an interrupt without cancel_queued, which the SDK's
        interrupt() never sends. So the hold settles at the interrupted result like any other, the drain's
        init releases it, and nothing is re-fed: the text reaches the agent once."""
        s, c = self.s, self._first_turn()
        s.enqueue("B mid-turn")
        self._wait(lambda: len(c.writes) == 2, "B forwarded")
        s.enqueue("C behind B")
        self._settle()
        self.assertEqual(len(c.writes), 2, "C waits behind B's hold")
        s.interrupt()                                    # the stop button: the control request rung
        self._wait(lambda: s._interrupted, "interrupting")
        c.phase = "after-interrupt"
        self._interrupted_result(c)
        self._wait(lambda: s.inflight == 0 and s._untaken and s._untaken.get("settled"),
                   "the interrupted turn settled with B still in the CLI's queue")
        self._settle()
        self.assertFalse(s._interrupted, "the result settled the interrupt")
        self.assertEqual(len(c.writes), 2, "nothing re-fed at the interrupt: the CLI keeps B")
        self.assertEqual(s.pending(), ["C behind B"], "C still waits for B's take")
        c.phase = "turn-2"
        self._init(c)                                    # B's own turn, as the real CLI opens it
        self._wait(lambda: len(c.writes) == 3, "C fed once B's drain showed")
        self.assertEqual([w[0] for w in c.writes], ["first turn", "B mid-turn", "C behind B"], "B once, never twice")
        self.assertEqual(c.writes[2][1], "turn-2")

    def test_the_clis_exit_puts_a_held_text_back_at_the_head_of_the_queue_for_the_next_client(self):
        """The one loss event: the CLI's process exits (a crash, a kill, the stop ladder's SIGINT rung, which
        on CLI 2.1.263 emits the interrupted result and exits 30 ms later WITHOUT running the queued text).
        Its queue dies with it, so a settled hold's text is nowhere: not in a counter, not in the queue,
        no frame ever comes to release the hold. At the exit the hold is released and the text, whose
        record the final transcript does not hold, goes back to the HEAD of the queue with its id, ahead
        of what queued behind it, persisted for the next client; the chat shows it queued meanwhile; an
        idle death still settles 'waiting' (no crash heal: the CLI was between turns)."""
        s, c = self.s, self._first_turn()
        self.assertTrue(self.be.send(SID, "mid-turn note", send_id="s-note"))
        self._wait(lambda: len(c.writes) == 2, "the note forwarded")
        s.enqueue("behind the note")
        c.phase = "after-result-1"
        self._result_frame(c)
        self._wait(lambda: s.inflight == 0 and s._untaken and s._untaken.get("settled"), "settled, untaken")
        self.assertEqual(s.pending(), ["behind the note"])
        self._push(c, _EOF)                              # the CLI exits: its stream ends, its queue with it
        self._wait(lambda: not s.thread.is_alive(), "the session thread ended with the stream")
        self.assertIsNone(s._untaken, "the hold is released at the exit")
        self.assertEqual([(str(t), getattr(t, "send_id", "")) for t in s.pending()],
                         [("mid-turn note", "s-note"), ("behind the note", "")],
                         "the note is back at the head, with its id, ahead of what waited behind it")
        mirror = sb._queue_texts((sb.read_reg(self.state, SID) or {}).get("queue"))
        self.assertEqual([(str(t), getattr(t, "send_id", "")) for t in mirror],
                         [("mid-turn note", "s-note"), ("behind the note", "")], "…and persisted for the next client")
        self.assertEqual(self.be.pending_queued(SID), ["mid-turn note", "behind the note"],
                         "the chat shows both queued while no CLI runs")
        echo = next(a for a in self.be.live_atoms(SID) if a.get("_echo_text") == "mid-turn note")
        self.assertFalse(echo.get("dropped"), "not a loss: it is queued again")
        self.assertTrue(any("exited while it still held a fed text" in l for l in self.lines), self.lines[-5:])
        self.assertFalse(any("died mid-turn" in l for l in self.lines), "an idle death: no crash heal")
        self.assertNotIn(SID, self.be.sessions, "the dead session is gone; the next send spawns")
        # the next client (the next send, the boot reconcile) feeds the note FIRST, held until its turn shows
        s2 = self.be._ensure(SID)
        self.assertIsNotNone(s2)
        self._wait(lambda: len(self._Client.instances) == 2 and len(self._Client.instances[1].writes) == 1,
                   "the new client fed the note")
        c2 = self._Client.instances[1]
        self.assertEqual(c2.writes[0][0], "mid-turn note")
        self.assertEqual(getattr(s2.fed_texts()[0], "send_id", ""), "s-note", "the id rode along")
        self._settle()
        self.assertEqual(len(c2.writes), 1, "what queued behind it still waits for its take")
        c2.phase = "resumed"
        self._init(c2)
        self._wait(lambda: len(c2.writes) == 2, "…and follows once the note's turn showed")
        self.assertEqual(c2.writes[1][0], "behind the note")
        self.assertFalse(any("re-delivering a typed send" in l for l in self.lines),
                         "the spawn's echo scan had nothing to add: the queue already held it")

    def test_the_clis_exit_leaves_alone_a_held_text_the_cli_did_take(self):
        """The record landed (the CLI spliced or drained the text and wrote its record) but no frame reached
        the kernel before the exit: the hold is still live, and re-feeding would land the text twice. The
        final transcript decides: found means taken, nothing goes back to the queue."""
        s, c = self.s, self._first_turn()
        self.assertTrue(self.be.send(SID, "mid-turn note", send_id="s-note"))
        self._wait(lambda: len(c.writes) == 2, "the note forwarded")
        c.phase = "after-result-1"
        self._result_frame(c)
        self._wait(lambda: s.inflight == 0 and s._untaken and s._untaken.get("settled"), "settled, untaken")
        self._append(self._user_record("mid-turn note"))  # the drain wrote the record, then the CLI died
        self._push(c, _EOF)
        self._wait(lambda: not s.thread.is_alive(), "the thread ended")
        self.assertIsNone(s._untaken)
        self.assertEqual(s.pending(), [], "taken: never re-fed")
        self.assertEqual((sb.read_reg(self.state, SID) or {}).get("queue"), [])
        self.assertTrue(any("after taking the last fed text" in l for l in self.lines), self.lines[-5:])

    def test_the_clis_exit_flags_a_held_text_it_cannot_check_rather_than_re_feed_on_doubt(self):
        """The transcript unreadable at the exit: neither a proof of loss nor of a take. The echo takes the
        flag path ('never delivered', with restore), the queue gets nothing, and the log says why."""
        s, c = self.s, self._first_turn()
        self.assertTrue(self.be.send(SID, "mid-turn note", send_id="s-note"))
        self._wait(lambda: len(c.writes) == 2, "the note forwarded")
        c.phase = "after-result-1"
        self._result_frame(c)
        self._wait(lambda: s.inflight == 0 and s._untaken and s._untaken.get("settled"), "settled, untaken")
        self._fault_the_transcript()
        self._push(c, _EOF)
        self._wait(lambda: not s.thread.is_alive(), "the thread ended")
        self.assertEqual(s.pending(), [], "nothing re-fed on doubt")
        echo = next(a for a in self.be.live_atoms(SID) if a.get("_echo_text") == "mid-turn note")
        self.assertTrue(echo.get("dropped"), "the possible loss is visible")
        self.assertTrue(any("could not be read" in l for l in self.lines), self.lines[-5:])

    def test_a_stale_move_arm_is_dropped_at_a_real_turns_result_so_the_drain_still_counts(self):
        """Round 3: the round-2 skip made the CLI-owned-turn count depend on the move arm, and only the
        move's turn-less result spent it. A stale arm (the CLI accepted a set_cwd and never emitted that
        result, or move() kept the arm across a lost reply) then switched the count off for the session's
        life: the drain's init went uncounted, the next text was fed 'fresh', its hold cleared on the
        running turn's next frame with the text still in the CLI's queue, and the text behind it fused
        with it. A real turn's result (num_turns != 0) while the arm stands proves it stale (the move's
        result would have preceded it) and drops it, so the drain counts as before and the text fed into
        it waits for its own take. Round 4 holds the queue while the arm stands, so the real turn that
        drops a stale arm is one the CLI opened on its own (a notification woke it); the held text goes
        in at the drop, and every drain after it counts."""
        s, c = self.s, self._first_turn()
        c.phase = "after-result-1"
        self._result_frame(c)
        self._wait(lambda: s.inflight == 0, "idle")
        s.loop.call_soon_threadsafe(setattr, s, "_move_settle_expected", True)   # armed; no turn-less result comes
        self._settle()
        c.phase = "held-behind-the-arm"
        s.enqueue("A from idle")
        self._settle()
        self.assertEqual(len(c.writes), 1, "held: a move's settle is expected (round 4)")
        c.phase = "cli-owned-turn"
        self._init(c)                                    # the CLI opened a turn on its own (a notification)
        self._assistant(c, "the CLI's own turn")
        self._settle()
        self.assertEqual(s.inflight, 0, "not counted while the arm stands (round 2)")
        self.assertEqual(len(c.writes), 1, "still held: the running turn's frames are not the event")
        c.phase = "after-the-drop"
        self._result_frame(c)                            # num_turns 1: a real turn's result
        self._wait(lambda: len(c.writes) == 2, "the drop released the held text")
        self.assertFalse(s._move_settle_expected, "a real turn's result drops the stale arm")
        self.assertTrue(any("stale arm is dropped" in l for l in self.lines), self.lines[-5:])
        self.assertEqual(c.writes[1], ("A from idle", "after-the-drop"))
        self.assertIs(s._untaken["fresh"], True, "fed from idle")
        c.phase = "turn-A"
        self._init(c)
        self._assistant(c)
        self._wait(lambda: s._untaken is None, "A's turn started: its hold released")
        s.enqueue("B mid-turn")
        self._wait(lambda: len(c.writes) == 3, "B forwarded")
        c.phase = "after-result-A"
        self._result_frame(c)
        self._wait(lambda: s.inflight == 0 and s._untaken and s._untaken.get("settled"), "A settled, B held")
        c.phase = "turn-B"
        self._init(c)                                    # the drain: B's own turn
        self._wait(lambda: s._untaken is None and s.inflight == 1, "the drain released B's hold AND counted its turn")
        s.enqueue("C into B's turn")
        self._wait(lambda: len(c.writes) == 4, "C fed into B's turn")
        self.assertIs(s._untaken["fresh"], False, "C went into a running turn, not from idle")
        s.enqueue("D behind C")
        self._assistant(c, "turn B keeps going")        # a frame of the running turn: not C's take
        self._settle()
        self.assertEqual(len(c.writes), 4, "D waits: C is untaken and the running turn's frame proves nothing")
        c.phase = "after-result-B"
        self._result_frame(c)
        self._wait(lambda: s.inflight == 0, "B's turn settled")
        c.phase = "turn-C"
        self._init(c)
        self._wait(lambda: len(c.writes) == 5, "D fed once C's drain showed")
        self.assertEqual([w[0] for w in c.writes],
                         ["first turn", "A from idle", "B mid-turn", "C into B's turn", "D behind C"])
        self.assertEqual(c.writes[4][1], "turn-C")

    def test_a_reconnect_drops_a_stale_move_arm_so_the_new_clients_turns_count(self):
        """The loop top's backstop: the client that owed the move's turn-less result is torn down (a
        reconnect), and the new one will never emit it. The arm is dropped there, so a turn the new CLI
        starts on its own is counted like any CLI-owned turn."""
        s, c = self.s, self._first_turn()
        c.phase = "after-result-1"
        self._result_frame(c)
        self._wait(lambda: s.inflight == 0, "idle")
        s.loop.call_soon_threadsafe(setattr, s, "_move_settle_expected", True)
        self._settle()
        self.assertTrue(s._move_settle_expected)
        s.request_reconnect()                            # idle: fires at once
        self._wait(lambda: len(self._Client.instances) == 2 and self._Client.instances[1] is s.client,
                   "the reconnect")
        self.assertFalse(s._move_settle_expected, "the new client owes no turn-less result: the arm is dropped")
        c2 = self._Client.instances[1]
        c2.phase = "auto-turn"
        self._init(c2)                                   # the new CLI starts a turn on its own
        self._wait(lambda: s.inflight == 1, "the CLI-owned turn counted")
        self.assertTrue(self.be.busy(SID))

    def test_the_clis_exit_before_any_conversation_re_heads_the_first_text_rather_than_flag_it(self):
        """Round 3: a new session's first send is fed from idle (a fresh hold, inflight 1) and the CLI dies
        before it writes its first record (no init streamed: resume_sid None, no transcript file). The scan
        answers None (the file does not exist), and the release flagged the echo 'never delivered' and
        left the queue alone, so the crash heal respawned with the nudge only and the agent was told to
        pick the work back up in an empty conversation. _reconcile_stranded's distinction applies: no
        conversation materialised, so the next client starts fresh and a re-feed cannot duplicate. The
        text goes back to the head with its id, the heal's nudge ahead of it, and the new client is fed
        the nudge, then the text once the nudge's turn showed."""
        s = self.s
        s.start()
        self._wait(lambda: s.client is not None, "the first connect")
        c = self._Client.instances[0]
        c.phase = "turn-1"
        self.assertTrue(self.be.send(SID, "first composer send", send_id="s-first"))
        self._wait(lambda: c.writes == [("first composer send", "turn-1")], "fed from idle")
        self.assertIsNotNone(s._untaken)
        self.assertIsNone(s.resume_sid, "no init streamed: no conversation")
        self.assertFalse(os.path.exists(self._transcript()), "the CLI wrote nothing before it died")
        self._push(c, _EOF)                              # the crash, before the CLI's first write
        self._wait(lambda: not s.thread.is_alive(), "the thread ended")
        self.assertIsNone(s._untaken, "the hold is released at the exit")
        self.assertEqual([(str(t), getattr(t, "send_id", "")) for t in s.pending()],
                         [("first composer send", "s-first")], "re-headed with its id, not flagged")
        echo = next(a for a in self.be.live_atoms(SID) if a.get("_echo_text") == "first composer send")
        self.assertFalse(echo.get("dropped"), "not a loss: it is queued again")
        self.assertTrue(any("before any conversation materialised" in l for l in self.lines), self.lines[-6:])
        # a death mid-turn (inflight 1, no result): the crash heal respawns with its nudge AHEAD of the
        # kept queue, so the new client hears the nudge, then the user's message
        self._wait(lambda: len(self._Client.instances) == 2 and len(self._Client.instances[1].writes) == 1,
                   "the heal respawned and fed the nudge")
        self.assertTrue(any("died mid-turn" in l for l in self.lines), "the crash heal ran")
        c2 = self._Client.instances[1]
        self.assertEqual(c2.writes[0][0], sb.CRASH_RESUME_NUDGE)
        self._settle()
        self.assertEqual(len(c2.writes), 1, "the text waits for the nudge's take")
        c2.phase = "resumed"
        self._init(c2)
        self._wait(lambda: len(c2.writes) == 2, "the text fed once the nudge's turn showed")
        self.assertEqual(c2.writes[1][0], "first composer send")
        s2 = self.be.sessions[SID]
        self.assertEqual(getattr(s2.fed_texts()[1], "send_id", ""), "s-first", "the id rode along")
        self.assertFalse(any("re-delivering a typed send" in l for l in self.lines),
                         "the spawn's echo scan had nothing to add: the queue already held it")

    def test_the_clis_exit_still_flags_when_a_resumable_conversations_transcript_is_missing(self):
        """The other side of the distinction: a conversation that did materialise (an init streamed, the
        CLI wrote records) whose transcript file is gone at the exit. The scan answers None, and a
        resumable conversation keeps the flag path: the record may have landed in a file the next client
        resumes, so a re-feed could duplicate. Flagged, not re-fed (passes before round 3 too: it guards
        the re-head from reaching a resumable conversation)."""
        s, c = self.s, self._first_turn()
        self.assertTrue(self.be.send(SID, "mid-turn note", send_id="s-note"))
        self._wait(lambda: len(c.writes) == 2, "the note forwarded")
        c.phase = "after-result-1"
        self._result_frame(c)
        self._wait(lambda: s.inflight == 0 and s._untaken and s._untaken.get("settled"), "settled, untaken")
        self.assertEqual(s.resume_sid, FSID, "resumable")
        os.remove(self._transcript())                    # the file is gone, not merely unreadable
        self._push(c, _EOF)
        self._wait(lambda: not s.thread.is_alive(), "the thread ended")
        self.assertEqual(s.pending(), [], "resumable: nothing re-fed on doubt")
        self.assertEqual((sb.read_reg(self.state, SID) or {}).get("queue"), [])
        echo = next(a for a in self.be.live_atoms(SID) if a.get("_echo_text") == "mid-turn note")
        self.assertTrue(echo.get("dropped"), "the possible loss is visible")
        self.assertTrue(any("could not be read" in l for l in self.lines), self.lines[-5:])

    # -- round 4: the feeder holds while a move is in flight --
    def _idle_after_the_first_turn(self):
        s, c = self.s, self._first_turn()
        c.phase = "after-result-1"
        self._result_frame(c)
        self._wait(lambda: s.inflight == 0, "idle")
        return c

    def _start_move(self, c, answer, on_request=None):
        """Drive the REAL move() on a kernel-side thread against the running session. Its control channel
        is the gated fake on the client: the set_cwd request goes out at once and the CLI's answer waits
        for the gate. Returns the target folder, the thread and the dict move()'s answer lands in."""
        new = os.path.join(self.state, "moved")
        os.makedirs(new, exist_ok=True)
        c._query = _ControlChannel(answer(new) if callable(answer) else answer, on_request=on_request)
        out = {}                              # a gate a failed assertion leaves shut is opened by tearDown (every
        self.addCleanup(c._query.gate.set)    # registered gate), and by this backstop after it: a no-op then
        t = threading.Thread(target=lambda: out.__setitem__("r", self.be.move(SID, new)), daemon=True)
        t.start()
        self._wait(lambda: c._query.requests, "the set_cwd request went out")
        return new, t, out

    def test_a_text_sent_while_the_cli_relocates_waits_for_the_moves_turn_less_result(self):
        """Round 4: move() arms and sends set_cwd; the CLI relocates FIRST and replies after, then emits an
        init and a turn-less result. A text fed into that window could run a whole turn before the move's
        result arrived: that turn's result would read the arm as stale and drop it (round 3), and the late
        turn-less result would settle as a turn end (a turn_seq bump, a 'waiting' write, the rename ping or
        a deferred reconnect fired early). The feeder holds the head while the arm stands and feeds on the
        exact event that lowers it: the move's turn-less result, consumed. The move's own request is not
        held: it rides the control channel."""
        s, c = self.s, self._idle_after_the_first_turn()
        new, t, out = self._start_move(c, lambda path: {"status": "ok", "cwd": path, "changed": True,
                                                         "transcript_relocated": True})
        self.assertTrue(s._move_settle_expected, "armed before the request")
        self.assertEqual(c._query.requests, [{"subtype": "set_cwd", "path": new}],
                         "the request went out through the control channel while the arm stood")
        c.phase = "relocating"
        s.enqueue("sent during the move")
        self._settle()
        self.assertEqual(c.writes, [("first turn", "turn-1")], "held: the CLI is relocating for the move")
        self.assertEqual(s.pending(), ["sent during the move"], "queued, visible, cancellable")
        self.assertTrue(self.be.busy(SID), "a queued text: a drive op pressed now parks")
        c.phase = "after-ok"
        c._query.gate.set()                              # the CLI relocated and replies ok
        t.join(10)
        self.assertEqual(out.get("r"), "")
        self.assertEqual(s.cwd, new, "romp's half of the move followed the ok")
        self._settle()
        self.assertEqual(len(c.writes), 1, "the ok is not the event: the CLI still owes its turn-less result")
        c.phase = "after-move-init"
        self._init(c)                                    # the CLI's init, no query behind it
        self._settle()
        self.assertEqual(len(c.writes), 1, "the move's init is not the event either")
        self.assertEqual(s.inflight, 0, "the init counted no turn: the arm stands")
        c.phase = "after-move-result"
        self._move_result(c)
        self._wait(lambda: len(c.writes) == 2, "fed once the move's turn-less result was consumed")
        self.assertEqual(c.writes[1], ("sent during the move", "after-move-result"))
        self.assertFalse(s._move_settle_expected, "spent")
        self.assertEqual(s.inflight, 1)
        self.assertIs(s._untaken["fresh"], True, "fed from idle, after the move")
        self.assertEqual(s.pending(), [])
        self._sys(c, "commands_changed")                 # the move's tail frames prove nothing about the queue
        self._settle()
        self.assertIsNotNone(s._untaken, "still held until the turn shows")

    def test_a_refused_move_lowers_the_arm_and_the_held_text_is_fed_then(self):
        """Round 4, the other exit: the CLI refuses the set_cwd. move() lowers the arm at the refusal and
        wakes the feeder, so the text held through the request is fed then, with no move result to wait
        for; the session stays where it was."""
        s, c = self.s, self._idle_after_the_first_turn()
        words = "Couldn't find a directory at /srv/notes-api/moved."
        new, t, out = self._start_move(c, {"status": "rejected", "reason": "not_found", "message": words})
        self.assertTrue(s._move_settle_expected, "armed before the request")
        c.phase = "relocating"
        s.enqueue("sent during the move")
        self._settle()
        self.assertEqual(c.writes, [("first turn", "turn-1")], "held while the move is in flight")
        c.phase = "after-refusal"
        c._query.gate.set()                              # the CLI answers: rejected
        t.join(10)
        self.assertEqual(out.get("r"), words)
        self._wait(lambda: len(c.writes) == 2, "fed once the refusal lowered the arm")
        self.assertEqual(c.writes[1], ("sent during the move", "after-refusal"))
        self.assertFalse(s._move_settle_expected)
        self.assertEqual(s.cwd, self.cwd, "the session stays where it was")
        self.assertNotIn("cwdPending", sb.read_reg(self.state, SID) or {})
        self.assertEqual(s.inflight, 1)
        self.assertIs(s._untaken["fresh"], True)
        c.phase = "turn-2"
        self._init(c)
        self._wait(lambda: s._untaken is None, "the text's own turn started: its hold released")

    def test_a_move_whose_cli_exited_after_the_claim_names_the_error_and_drops_the_claim(self):
        """Round 5: the CLI exits between move()'s claim and its request (an idle death: the stream ends,
        the session's thread ends with it, asyncio.run closes its loop, and self.loop is never nulled). The
        request finds no client and move() takes the _NO_CONTROL_SENDER exit, which lowers the arm through
        _disarm_move_settle. At round 4 that raised RuntimeError on the closed loop before the claim was
        dropped: the kernel reported the raise in place of the SDK's named error, and every later move of
        the session was refused as already pending until a kernel boot healed it. The disarm tolerates a
        closed loop, and the exit drops the claim whatever the disarm does (round 6 put the disarm back in
        front of the drop: _stand_down_move)."""
        s, c = self.s, self._idle_after_the_first_turn()
        new = os.path.join(self.state, "moved")
        os.makedirs(new, exist_ok=True)
        real = self.be._claim_cwd_pending

        def claim_then_the_cli_exits(*a):
            out = real(*a)
            self._push(c, _EOF)
            self._wait(lambda: not s.thread.is_alive(), "the session thread ended after the claim")
            return out
        self.be._claim_cwd_pending = claim_then_the_cli_exits
        self.assertEqual(self.be.move(SID, new), sb._NO_CONTROL_SENDER, "the SDK's named error, not a raise")
        self.assertTrue(s.loop.is_closed(), "the loop the disarm would have woken is closed")
        self.assertFalse(s._move_settle_expected, "the arm is down")
        self.assertNotIn("cwdPending", sb.read_reg(self.state, SID) or {}, "the claim is dropped")
        self.assertEqual(real(SID, new), "", "a later move's claim is accepted")
        self.be._update_reg_dropping(SID, ("cwdPending",))

    def test_a_standing_down_exit_releases_the_claim_after_the_arm_so_a_second_movers_arm_survives(self):
        """Round 6: move()'s standing-down exits (the CLI rejected the set_cwd, or answered that nothing
        changed, or the SDK had no control sender) lower the arm and drop the claim. Round 5 put the drop
        first, which opened a window: the claim is what keeps a second move() of this sid out, so a second
        mover claims the instant the flag is gone and arms for its own request, and the first move's disarm
        then lowers THAT arm, leaving the second move's relocation with the queue unheld (round 4's hazard
        again). The arm is settled before the claim that guards it is released, and the drop still happens
        whatever the disarm does. The uncertain-outcome exit's "never happened" branch had the same window
        through a second door (the heal dropped the claim itself, ahead of move()'s disarm) and takes the same
        shape through the heal's release hook. The second mover's claim-and-arm is simulated inside the drop,
        the instant the flag is gone, so the probe is exact and not a timing."""
        s, c = self.s, self._idle_after_the_first_turn()
        second = os.path.join(self.state, "moved-again")
        real_drop, real_claim = self.be._update_reg_dropping, self.be._claim_cwd_pending
        fired = []

        def drop_then_a_second_mover_claims_and_arms(sid, drop=(), **fields):
            real_drop(sid, drop, **fields)
            if sid == SID and "cwdPending" in drop and not fired:
                fired.append(real_claim(SID, second))      # "": the flag is gone, so the claim is accepted
                with s._lock:
                    s._move_settle_expected = True         # the second move arms for its own request
        self.be._update_reg_dropping = drop_then_a_second_mover_claims_and_arms

        def after_the_first_moves_exit(label, answer):
            arm, claim = s._move_settle_expected, (sb.read_reg(self.state, SID) or {}).get("cwdPending")
            s._disarm_move_settle()                        # the second move's own exit, so the next case
            real_drop(SID, ("cwdPending",))                # starts clean whichever way this one went
            self.assertEqual(fired, [""], "%s: the second mover claimed the instant the flag was gone" % label)
            self.assertTrue(arm, "%s: the second move's arm survives the first move's exit" % label)
            self.assertEqual(claim, second, "%s: the second move's claim stands" % label)
            self.assertEqual(s.cwd, self.cwd, "%s: the session stays where it was" % label)
            del fired[:]
        words = "Couldn't find a directory at /srv/notes-api/moved."
        for label, answer, expect in (
                ("rejected", {"status": "rejected", "reason": "not_found", "message": words}, words),
                ("changed: false", lambda path: {"status": "ok", "cwd": path, "changed": False}, "")):
            with self.subTest(exit=label):
                new, t, out = self._start_move(c, answer)
                self.assertTrue(s._move_settle_expected, "the first move armed before its request")
                c._query.gate.set()                        # the CLI answers
                t.join(10)
                self.assertEqual(out.get("r"), expect)
                after_the_first_moves_exit(label, answer)
        with self.subTest(exit="no control sender"):
            c._query = object()                            # an SDK client without the private sender
            self.assertEqual(self.be.move(SID, os.path.join(self.state, "moved")), sb._NO_CONTROL_SENDER)
            after_the_first_moves_exit("no control sender", None)
        with self.subTest(exit="uncertain outcome, the move never happened"):
            # the CLI never answers and did not relocate: the request's own timeout returns move() to the
            # heal, which finds the transcript still under the old folder and releases the claim
            from unittest import mock
            with mock.patch.object(sb, "MOVE_CONTROL_TIMEOUT", 0.7):   # the pre-existing round-trip bound, shortened
                new, t, out = self._start_move(c, None)
                self.assertTrue(s._move_settle_expected, "the first move armed before its request")
                t.join(10)
            c._query.gate.set()                            # the late answer lands on a future move() stopped waiting on
            self.assertFalse(t.is_alive(), "move() returned on the control request's timeout")
            after_the_first_moves_exit("uncertain outcome", None)
            self.assertTrue(str(out.get("r", "")).startswith("the move failed: "),
                            "the answer comes from the heal's own outcome, not a re-read of a reg the released "
                            "claim no longer guards: %r" % (out.get("r"),))

    def test_a_lost_reply_after_the_cli_relocated_announces_the_hold_it_leaves(self):
        """Round 5: the CLI relocated the transcript for the set_cwd and never answered (a hang after the
        rename). The control request's own timeout returns move() to the heal, which finds the transcript
        under the target and finishes romp's half; the arm stands, since the CLI's turn-less result is
        still owed, and with it the round-4 hold on the queue. That hold outlives move()'s return, so it is
        announced: a problem-ring line naming the session and that queued sends wait for the move's
        result. The chip shows the text queued meanwhile, busy() reads it, and the hold ends on the exact
        event that lowers the arm (here a real turn's result, the stale-arm drop); no timer."""
        from unittest import mock
        s, c = self.s, self._idle_after_the_first_turn()
        fsid = str((sb.read_reg(self.state, SID) or {}).get("lastSid") or SID)

        def relocate(req):
            dst = sb.transcript_path(req["path"], fsid)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            os.rename(self._transcript(), dst)
        with mock.patch.object(sb, "MOVE_CONTROL_TIMEOUT", 0.7):   # the pre-existing round-trip bound, shortened
            new, t, out = self._start_move(c, None, on_request=relocate)
            c.phase = "hung-move"
            s.enqueue("sent during a hung move")
            t.join(10)
        self.assertFalse(t.is_alive(), "move() returned on the control request's timeout")
        self.assertEqual(out.get("r"), "", "the move stands: the transcript is under the target")
        self.assertEqual(s.cwd, new)
        self.assertTrue(s._move_settle_expected, "the CLI's result is still owed: the arm stands")
        self.assertEqual(c.writes, [("first turn", "turn-1")], "the text is held")
        self.assertEqual(self.be.pending_queued(SID), ["sent during a hung move"], "the chip shows it queued")
        self.assertTrue(self.be.busy(SID))
        rows = [r for r in self.be.problems() if "queued sends wait for the CLI's result" in r["text"]]
        self.assertEqual(len(rows), 1, self.be.problems())
        self.assertIn("(web)", rows[0]["text"], "names the session")
        # the hold ends on the exact event: a real turn's result drops the stale arm and the text is fed
        c.phase = "cli-owned-turn"
        self._init(c)
        self._assistant(c)
        self._result_frame(c)
        self._wait(lambda: len(c.writes) == 2, "fed at the stale arm's drop")
        self.assertEqual(c.writes[1], ("sent during a hung move", "cli-owned-turn"))
        self.assertFalse(s._move_settle_expected)

    def test_teardown_opens_a_replaced_control_channels_gate_so_its_worker_does_not_outlive_the_test(self):
        """The fixture's own hazard, pinned (2026-09-10): a scripted channel whose gate stays shut parks the
        loop's executor thread in gate.wait, and a subTest that fails between a _start_move and its gate.set
        leaves exactly that, with the next _start_move replacing the client's _query. tearDown once opened
        only the client's current channel, so the replaced one's worker was still parked at interpreter
        exit, which concurrent.futures joins without a timeout: the pytest process never exited (a
        single-process run, as CI's). tearDown opens every gate in the fake's registry instead. The check
        runs from a cleanup because unittest runs cleanups AFTER tearDown: it sees what tearDown left."""
        from unittest import mock
        c = self._idle_after_the_first_turn()
        with mock.patch.object(sb, "MOVE_CONTROL_TIMEOUT", 0.7):   # the pre-existing round-trip bound, shortened
            new, t, out = self._start_move(c, None)                # the CLI never answers: the gate stays shut
            t.join(10)
        self.assertFalse(t.is_alive(), "move() returned on the control request's timeout")
        parked = c._query
        self._wait(lambda: parked.worker is not None, "the loop's executor thread is parked in the shut gate")
        self.assertTrue(parked.worker.is_alive())
        c._query = _ControlChannel(None)                           # the replacement: the client names only this one
        self.assertEqual(_ControlChannel.instances, [parked, c._query], "both channels are registered")

        def no_worker_outlives_the_test():
            workers = [q.worker for q in _ControlChannel.instances if q.worker is not None]
            alive = [th.name for th in threading.enumerate() if th in workers]
            self.assertEqual(alive, [], "a control channel's worker is still parked after tearDown")
        self.addCleanup(no_worker_outlives_the_test)


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
