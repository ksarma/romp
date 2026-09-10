#!/usr/bin/env python3
"""SdkBackend (bin/romp_sdk_backend.py) — the non-tmux session backend.

Two layers:
  * Pure translation logic (AskUserQuestion <-> the existing askLive picker shape,
    state/registry files) is tested WITHOUT the SDK, so it runs in CI.
  * The async runner + the can_use_tool round-trip is tested with a FAKE
    ClaudeSDKClient (monkeypatched in), skipped where claude_agent_sdk is absent.
    This exercises the headline path: a user turn -> the model calls
    AskUserQuestion -> it surfaces as an askLive picker -> the UI answers ->
    PermissionResultAllow(updated_input={questions, answers}) goes back.
"""
import asyncio
import inspect
import io
import os
import json
import shutil
import sys
import threading
import time
import tracemalloc
import tempfile
import types
import unittest
from contextlib import redirect_stderr
from importlib.machinery import ModuleSpec
from pathlib import Path
from unittest import mock
from romp_load import load_source
from unittest import mock

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
sb = load_source("romp_sdk_backend", os.path.join(BIN, "romp_sdk_backend.py"))


class PureTranslation(unittest.TestCase):
    def test_single_question_to_live(self):
        q = {"question": "Pick one", "header": "H", "multiSelect": False,
             "options": [{"label": "A", "description": "aa"}, {"label": "B", "description": "bb"}]}
        ask = sb.ask_question_to_live(q, 0, 1)
        self.assertEqual(ask["kind"], "single")
        self.assertEqual(ask["header"], "H")
        self.assertFalse(ask["multiSelect"])
        real = [o for o in ask["options"] if o["label"] != sb.TYPE_SOMETHING]
        self.assertEqual([o["n"] for o in real], [1, 2])
        self.assertEqual(ask["options"][0]["label"], "A")
        self.assertEqual(ask["options"][0]["desc"], "aa")
        self.assertFalse(ask["options"][0]["selected"])
        # the "add your own" affordance is ALWAYS offered, as a trailing meta option (the user 2026-06-27)
        self.assertEqual(ask["options"][-1]["label"], sb.TYPE_SOMETHING)
        self.assertEqual(ask["options"][-1]["n"], 3, "contiguous after the real options")
        self.assertNotIn("progress", ask)        # single question -> no "n of m"

    def test_add_your_own_offered_for_multi_and_shows_typed_customs(self):
        q = {"question": "Pick many", "header": "H", "multiSelect": True,
             "options": [{"label": "A"}, {"label": "B"}]}
        ask = sb.ask_question_to_live(q, 0, 1, selected={1}, customs=["my own thing"])
        labels = [o["label"] for o in ask["options"]]
        self.assertEqual(labels, ["A", "B", "my own thing", sb.TYPE_SOMETHING])
        self.assertTrue(ask["options"][2]["checked"], "a typed custom shows as a checked row")
        self.assertFalse(ask["options"][3]["checked"], "the meta add-your-own row is not checked")
        self.assertEqual([o["n"] for o in ask["options"]], [1, 2, 3, 4], "contiguous ordinals")

    def test_multi_question_marks_checked_and_progress(self):
        q = {"question": "Pick many", "header": "H", "multiSelect": True,
             "options": [{"label": "A"}, {"label": "B"}, {"label": "C"}]}
        ask = sb.ask_question_to_live(q, 1, 3, selected={2})
        self.assertEqual(ask["kind"], "multi")
        self.assertTrue(ask["options"][1]["checked"])      # option 2 toggled on
        self.assertFalse(ask["options"][0]["checked"])
        self.assertEqual(ask["progress"], {"i": 2, "n": 3})

    def test_preview_passthrough(self):
        q = {"question": "q", "header": "h", "multiSelect": False,
             "options": [{"label": "A", "preview": "<b>mock</b>"}]}
        ask = sb.ask_question_to_live(q, 0, 1)
        self.assertEqual(ask["options"][0]["preview"], "<b>mock</b>")

    def test_label_for_target(self):
        q = {"options": [{"label": "cats"}, {"label": "dogs"}]}
        self.assertEqual(sb.label_for_target(q, 1), "cats")
        self.assertEqual(sb.label_for_target(q, "2"), "dogs")
        self.assertEqual(sb.label_for_target(q, 9), "9")        # out of range -> verbatim
        self.assertEqual(sb.label_for_target(q, "custom text"), "custom text")

    def test_build_answers(self):
        qs = [{"question": "Q1"}, {"question": "Q2"}, {"question": "Q3"}]
        ans = sb.build_answers(qs, {0: "a", 2: ["x", "y"]})
        self.assertEqual(ans, {"Q1": "a", "Q3": ["x", "y"]})    # Q2 unanswered -> omitted

    def test_permission_to_live(self):
        ask = sb.permission_to_live("Bash", {"command": "rm -rf /tmp/x"})
        self.assertTrue(ask["permission"])
        self.assertEqual([o["label"] for o in ask["options"]], ["Allow", "Deny"])
        self.assertIn("rm -rf", ask["question"])
        self.assertNotIn("preview", ask, "a Bash command has no diff preview")

    def test_permission_uses_sdk_title_and_description(self):
        class Ctx:
            title = "Claude wants to read foo.txt"
            description = "Read a file in the project"
            suggestions = []
        ask = sb.permission_to_live("Read", {"file_path": "foo.txt"}, Ctx())
        self.assertEqual(ask["question"], "Claude wants to read foo.txt", "uses the SDK's own prompt sentence")
        self.assertEqual(ask["options"][0]["desc"], "Read a file in the project")

    def test_permission_adds_allow_and_remember_when_suggestions_present(self):
        class Ctx:
            title = None; description = None
            suggestions = ["<a PermissionUpdate>"]   # truthy → offer the remember option
        ask = sb.permission_to_live("Bash", {"command": "ls"}, Ctx())
        labels = [o["label"] for o in ask["options"]]
        self.assertEqual(labels, ["Allow", "Allow & don't ask again", "Deny"])
        self.assertEqual([o["n"] for o in ask["options"]], [1, 2, 3], "ordinals stay 1..N for arrow-nav")

    def test_edit_permission_carries_a_diff_preview(self):
        ask = sb.permission_to_live("Edit", {"file_path": "a.py", "old_string": "x = 1\ny = 2",
                                              "new_string": "x = 1\ny = 3"})
        self.assertEqual(ask["previewKind"], "diff")
        self.assertIn("a.py", ask["preview"])
        self.assertIn("-y = 2", ask["preview"])
        self.assertIn("+y = 3", ask["preview"])

    def test_tool_preview_write_plan_multiedit_and_none(self):
        # Write → all-additions diff
        kind, txt = sb.tool_preview("Write", {"file_path": "n.txt", "content": "hello\nworld"})
        self.assertEqual(kind, "diff")
        self.assertIn("+hello", txt); self.assertIn("+world", txt)
        # ExitPlanMode → the plan verbatim, kind "plan"
        kind, txt = sb.tool_preview("ExitPlanMode", {"plan": "1. do this\n2. then that"})
        self.assertEqual(kind, "plan"); self.assertIn("do this", txt)
        # MultiEdit → concatenated diffs
        kind, txt = sb.tool_preview("MultiEdit", {"file_path": "m.py",
            "edits": [{"old_string": "a", "new_string": "b"}, {"old_string": "c", "new_string": "d"}]})
        self.assertEqual(kind, "diff"); self.assertIn("-a", txt); self.assertIn("+d", txt)
        # a tool with nothing visual → None
        self.assertIsNone(sb.tool_preview("Bash", {"command": "ls"}))
        self.assertIsNone(sb.tool_preview("ExitPlanMode", {"plan": ""}))

    def test_tool_preview_clips_huge_diffs(self):
        big = "\n".join("line %d" % i for i in range(1000))
        _, txt = sb.tool_preview("Write", {"file_path": "big.txt", "content": big})
        self.assertIn("more lines)", txt, "an enormous preview is capped, not sent whole")
        self.assertLess(len(txt.splitlines()), 1000)

    def test_pretty_model(self):
        self.assertEqual(sb.pretty_model("claude-opus-4-8"), "Opus 4.8")
        self.assertEqual(sb.pretty_model("claude-sonnet-4-6"), "Sonnet 4.6")
        self.assertEqual(sb.pretty_model("claude-haiku-4-5-20251001"), "Haiku 4.5")  # trailing date dropped
        self.assertEqual(sb.pretty_model("claude-fable-5"), "Fable 5")               # no minor version
        self.assertEqual(sb.pretty_model(""), "")
        self.assertEqual(sb.pretty_model("some-custom-id"), "some-custom-id")        # unrecognised → verbatim

    def test_model_family(self):
        # the /api-health bucket family a rate limit is scoped to: re.search, not pretty_model's anchored
        # match, so a provider-prefixed Bedrock/Vertex id lands in its family; the badge form the session
        # displays is accepted for the retry-attribution fallback; generation-first ids name the family
        # after the generation and still file under it rather than pooling in `other`
        for raw, fam in [
            ("claude-fable-5-1", "fable"),
            ("claude-fable-5", "fable"),
            ("claude-haiku-4-5-20251001", "haiku"),
            ("claude-opus-4-8", "opus"),
            ("us.anthropic.claude-fable-5-20250101-v1:0", "fable"),   # provider-prefixed: not anchored
            ("Fable 5", "fable"),                                      # the badge form
            ("Opus 4.8", "opus"),
            ("", "unknown"),                                           # nothing learned yet
            (None, "unknown"),
            ("some-custom-id", "other"),                               # non-empty, matching nothing
            ("claude-3-5-sonnet-20241022", "sonnet"),                  # generation-first
            ("claude-3-opus-20240229", "opus"),
            ("anthropic.claude-3-haiku-20240307-v1:0", "haiku"),
        ]:
            self.assertEqual(sb.model_family(raw), fam, repr(raw))

    def test_model_label(self):
        # the live (init/assistant-echoed) name always wins once known
        self.assertEqual(sb.model_label("Opus 4.8", "opus"), "Opus 4.8")
        self.assertEqual(sb.model_label("Opus 4.8", ""), "Opus 4.8")
        # before the live name arrives, show a best-effort label from the CHOSEN model so the badge isn't
        # blank on a freshly-created SDK session (the user 2026-06-24)
        self.assertEqual(sb.model_label("", "opus"), "Opus")                 # CLI alias → capitalised
        self.assertEqual(sb.model_label("", "sonnet"), "Sonnet")
        self.assertEqual(sb.model_label("", "claude-opus-4-8"), "Opus 4.8")  # raw id → pretty_model
        # 'default'/unset → blank: the REAL default name fills in from the init message (eager-connect pokes it)
        self.assertEqual(sb.model_label("", "default"), "")
        self.assertEqual(sb.model_label("", ""), "")

    def test_identity_color_stable_and_in_palette(self):
        bg, fg = sb.pick_identity_color("11111111-2222-3333-4444-555555555555")
        self.assertIn(bg, sb._pal.PALETTES[sb._pal.DEFAULT]["bg"])   # no state_dir → the default set
        self.assertIn(fg, ("black", "white"))
        self.assertEqual(sb.pick_identity_color("11111111-2222-3333-4444-555555555555"), (bg, fg))  # stable per sid

    def test_identity_color_follows_the_active_palette(self):
        # the gear's Session-colors pick (STATE/palette) steers what NEW sessions are assigned
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "palette").write_text("phase")
            bg, fg = sb.pick_identity_color("11111111-2222-3333-4444-555555555555", td)
            p = sb._pal.PALETTES["phase"]
            self.assertIn(bg, p["bg"])
            self.assertEqual(fg, p["fg"][p["bg"].index(bg)])


# --- live tail (in-memory stream → atoms, ahead of disk). Pure: fakes match by type-name, no SDK. ---
class _TextBlock:
    def __init__(self, text): self.text = text
class _ToolUseBlock:
    def __init__(self, id, name, inp): self.id, self.name, self.input = id, name, inp
class _AssistantMessage:
    def __init__(self, content, model="claude-x", uuid="a1", stop_reason="end_turn"):
        self.content, self.model, self.uuid, self.stop_reason = content, model, uuid, stop_reason
class _ToolResultBlock:
    def __init__(self, tool_use_id, content="", is_error=False):
        self.tool_use_id, self.content, self.is_error = tool_use_id, content, is_error
class _UserMessage:
    def __init__(self, content, uuid="u1", tool_use_result=None):
        self.content, self.uuid, self.tool_use_result = content, uuid, tool_use_result
class _ResultMessage:
    uuid = "r1"
# rename so type(...).__name__ matches what msg_to_atom checks
_TextBlock.__name__ = "TextBlock"; _ToolUseBlock.__name__ = "ToolUseBlock"
_ToolResultBlock.__name__ = "ToolResultBlock"
_AssistantMessage.__name__ = "AssistantMessage"; _UserMessage.__name__ = "UserMessage"
_ResultMessage.__name__ = "ResultMessage"


class LiveTail(unittest.TestCase):
    def test_msg_to_atom_assistant(self):
        m = _AssistantMessage([_TextBlock("hi"), _ToolUseBlock("t1", "Bash", {"command": "ls"})])
        a = sb.msg_to_atom(m, "sid9", "fsidA", 100)
        self.assertEqual(a["type"], "assistant")
        self.assertEqual(a["uuid"], "a1")
        self.assertEqual(a["session_id"], "sid9")
        self.assertEqual(a["t"], 100)
        self.assertEqual(a["fsid"], "fsidA")
        self.assertEqual(a["message"]["content"],
                         [{"type": "text", "text": "hi"},
                          {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "ls"}}])

    def test_msg_to_atom_user_and_nonrenderable(self):
        a = sb.msg_to_atom(_UserMessage([_TextBlock("hello")]), "s", "f", 5)
        self.assertEqual(a["type"], "user")
        self.assertEqual(a["message"]["content"], [{"type": "text", "text": "hello"}])
        self.assertIsNone(sb.msg_to_atom(_ResultMessage(), "s", "f", 5))   # result has no renderable content
        self.assertIsNone(sb.msg_to_atom(_AssistantMessage([]), "s", "f", 5))  # empty content → None

    def test_tool_result_atom_carries_the_structured_tooluseresult(self):
        # The SDK's UserMessage exposes the record-level structured result (the CLI streams the
        # transcript record's toolUseResult on the wire as `tool_use_result`; the SDK parser maps it
        # onto UserMessage.tool_use_result — verified against claude-agent-sdk 0.2.132 / CLI 2.1.224).
        # The live atom must carry it exactly like the file adapter's atom does, or a JUST-answered
        # AskUserQuestion renders via the lossy regex scrape until the disk record is parsed, and
        # Edit's diffRows lag a parse behind the stream.
        tur = {"questions": ["Pick a color"], "answers": {"Pick a color": "Blue"}}
        m = _UserMessage([_ToolResultBlock("t1", "answered")], tool_use_result=tur)
        a = sb.msg_to_atom(m, "s", "f", 5)
        self.assertEqual(a["type"], "user")
        self.assertEqual(a["toolUseResult"], tur)
        self.assertEqual(a["message"]["content"][0]["type"], "tool_result")

    def test_string_tooluseresult_is_not_carried(self):
        # A dismissed picker records toolUseResult as a plain STRING — dict form only, the same gate
        # as the file adapter (no consumer reads the string form).
        m = _UserMessage([_ToolResultBlock("t1", "dismissed", is_error=True)],
                         tool_use_result="dismissed the questions")
        a = sb.msg_to_atom(m, "s", "f", 5)
        self.assertNotIn("toolUseResult", a)

    def test_tooluseresult_without_a_tool_result_block_is_not_carried(self):
        # The file adapter's other gate: only an atom that carries a tool_result block may carry the
        # record-level dict — a text-only message never does.
        m = _UserMessage([_TextBlock("hello")], tool_use_result={"x": 1})
        a = sb.msg_to_atom(m, "s", "f", 5)
        self.assertNotIn("toolUseResult", a)

    def test_an_unconsumed_shape_is_not_carried(self):
        # The consumed-keys gate: a Read result's dict embeds the WHOLE read file, and nothing
        # reads it off the atom — carrying every dict held ~a fifth of transcript bytes in the
        # parse cache by reference. Only the consumed shapes ride (answers, structuredPatch).
        m = _UserMessage([_ToolResultBlock("t9", "file contents…")],
                         tool_use_result={"type": "text", "file": {"content": "x" * 512}})
        a = sb.msg_to_atom(m, "s", "f", 5)
        self.assertNotIn("toolUseResult", a)

    def test_the_consumed_key_set_cannot_drift_from_the_file_adapter_s(self):
        # sdk_backend loads standalone (no event-model import), so the set is MIRRORED — this pin
        # is what keeps the two halves widening together.
        em2 = load_source("romp_event_model_drift", os.path.join(BIN, "romp-event-model"))
        self.assertEqual(sb.TUR_CONSUMED_KEYS, em2.TUR_CONSUMED_KEYS)

    def test_command_stdout_stream_becomes_a_turn_ENDING_assistant_atom(self):
        # the user 2026-07-02: client.set_model() makes the CLI stream its feedback as a UserMessage
        # wrapped in <local-command-stdout>. As a raw USER atom it opened a turn no reply would ever
        # close — the chat chip read "working" forever (fresh session + set model) while the timeline
        # (disk-only) showed nothing. The live atom must get the FILE adapter's classification: a
        # synthetic ASSISTANT command atom whose stop_reason end_turn CLOSES the turn.
        m = _UserMessage([_TextBlock("<local-command-stdout>Set model to sonnet (claude-sonnet-5)</local-command-stdout>")])
        a = sb.msg_to_atom(m, "s", "f", 5)
        self.assertEqual(a["type"], "assistant", "command OUTPUT is a synthetic assistant atom, like the file adapter")
        self.assertTrue(a["command"])
        self.assertEqual(a["message"]["stop_reason"], "end_turn", "the turn CLOSES — no phantom working chip")
        self.assertEqual(a["message"]["content"], [{"type": "text", "text": "Set model to sonnet (claude-sonnet-5)"}])

    def test_command_name_stream_becomes_the_command_chip_user_atom(self):
        m = _UserMessage([_TextBlock("<command-name>/model</command-name>\n"
                                     "<command-message>model</command-message>\n"
                                     "<command-args>sonnet</command-args>")])
        a = sb.msg_to_atom(m, "s", "f", 5)
        self.assertEqual(a["type"], "user")
        self.assertEqual(a["command"], "/model", "the invocation carries the command flag (the chat's chip)")
        self.assertEqual(a["message"]["content"], [{"type": "text", "text": "/model sonnet"}])

    def test_other_command_wrappers_are_noise(self):
        m = _UserMessage([_TextBlock("<local-command-caveat>whatever</local-command-caveat>")])
        self.assertIsNone(sb.msg_to_atom(m, "s", "f", 5), "non-invocation/output wrappers stay dropped, like the file adapter")

    def test_image_read_placeholder_is_dropped(self):
        # A Read of an image makes Claude Code stream a synthetic UserMessage carrying only this
        # placeholder alongside the image block. On disk it's isMeta (the file adapter skips it), but the
        # STREAM has no such flag, so as a raw user atom it rendered as a bare "you typed this" bubble
        # mid-conversation (the user 2026-07-23, who saw the box and asked what it was). The tool that fed
        # the image already shows in the rail, so the echo is dropped.
        m = _UserMessage([_TextBlock("[Image: original 2496x572, displayed at 2000x458. "
                                     "Multiply coordinates by 1.25 to map to original image.]")])
        self.assertIsNone(sb.msg_to_atom(m, "s", "f", 5), "the synthetic image-read echo is not a message")

    def test_image_paste_chip_is_not_dropped(self):
        # A composer paste chip is `[Image #N]` (no colon) and always rides WITH the human's typed text,
        # never alone — so it must NOT be swept up by the echo skip. A genuine human turn survives.
        m = _UserMessage([_TextBlock("look at [Image #1] and tell me what's wrong")])
        a = sb.msg_to_atom(m, "s", "f", 5)
        self.assertIsNotNone(a)
        self.assertEqual(a["type"], "user")

    def test_live_store_and_prune(self):
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)
        be._live["s"] = {"a1": {"uuid": "a1", "t": 2}, "echo:x": {"uuid": "echo:x", "t": 1, "_echo_text": "hi"}}
        self.assertEqual([a["uuid"] for a in be.live_atoms("s")], ["echo:x", "a1"])   # sorted by t
        be.prune_live("s", {"a1"}, {"hi"})     # a1 now on disk; echo text "hi" now on disk
        self.assertEqual(be.live_atoms("s"), [])

    def test_turn_settle_retires_unlanded_live_work_atoms(self):
        """A usage-limit retry storm streams work atoms whose attempt the API errors away — the CLI writes
        no transcript record for them, so the uuid-match prune can never retire them, and their live_work
        held the merged turn open FOREVER: the chat chip read WORKING with a 3h+ timer on a settled
        session (the user 2026-07-03). The turn's ResultMessage proves the stream is over — settle must
        drop unlanded WORK atoms, and ONLY them: an input echo keeps the dropped-send visibility, and a
        command atom has its own human-floor retirement."""
        import asyncio
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)
        s = sb.SdkSession(be, {"sid": "11111111-2222-3333-4444-555555555555", "name": "n", "cwd": "/tmp"})
        be._live[s.sid] = {"w1": {"uuid": "w1", "t": 5},
                           "echo:hi": {"uuid": "echo:hi", "t": 1, "_echo_text": "hi"},
                           "c1": {"uuid": "c1", "t": 3, "command": True}}
        s.inflight = 1

        async def run():
            s._on_message(_ResultMessage(), _AssistantMessage, _ResultMessage, type("S", (), {}))
            await asyncio.sleep(0)
        asyncio.run(run())
        self.assertEqual(set(be._live[s.sid]), {"echo:hi", "c1"},
                         "settle drops unlanded WORK atoms; echoes + command feedback survive")

    def test_session_gone_retires_unlanded_live_work_atoms(self):
        """The process dying mid-turn (laptop sleep, a killed CLI) is the other stream-over event: no
        ResultMessage is ever coming, so _on_session_gone must retire the work atoms — else the phantom
        WORKING chip outlives the process indefinitely."""
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)
        s = sb.SdkSession(be, {"sid": "11111111-2222-3333-4444-555555555555", "name": "n", "cwd": "/tmp"})
        be._live[s.sid] = {"w1": {"uuid": "w1", "t": 5}}
        be._on_session_gone(s)
        self.assertNotIn(s.sid, be._live, "no stream left → no work atom may hold the turn open")

    def test_forwards_sends_is_true_for_the_sdk(self):
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)
        self.assertTrue(be.forwards_sends(),
                        "the SDK forwards its own sends (mid-turn + one message each + interrupt-hold): the kernel hands "
                        "composer sends straight over instead of parking them (the user 2026-07-17)")

    def test_queued_turns_survive_an_interrupt_and_release_when_the_turn_settles(self):
        """The user 2026-07-17: messages queued while working, then interrupt → interrupt AND THEN send them
        all. An interrupted turn's ResultMessage still settles inflight to 0, and must leave the queued turns
        intact and WAKE the input generator so they feed (inputs() holds the queue while inflight>0 AND
        _interrupted, releasing at settle)."""
        import asyncio
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)
        s = sb.SdkSession(be, {"sid": "11111111-2222-3333-4444-555555555555", "name": "n", "cwd": "/tmp"})
        s.enqueue("first queued")
        s.enqueue("second queued")
        self.assertEqual(s.pending(), ["first queued", "second queued"], "held in _pending, not fed to the CLI yet")
        s.inflight = 1                                  # a turn is in flight...
        s._interrupted = True                          # ...and the user interrupted it
        s._input_wake = asyncio.Event()                # inputs() owns this; stub it here to observe the release

        async def run():
            s._on_message(_ResultMessage(), _AssistantMessage, _ResultMessage, type("S", (), {}))
            await asyncio.sleep(0)
        asyncio.run(run())
        self.assertEqual(s.pending(), ["first queued", "second queued"],
                         "the interrupt did NOT drop the queue — the messages are still there to send")
        self.assertEqual(s.inflight, 0, "the interrupted turn settled to idle")
        self.assertFalse(s._interrupted, "settle cleared the interrupt flag → inputs() stops blocking the queue")
        self.assertTrue(s._input_wake.is_set(),
                        "settle woke the input generator to feed the held turns as a fresh turn")

    def test_inputs_generator_holds_the_queue_while_interrupted(self):
        # The hold half of the guarantee above: the input generator must NOT feed the next turn into a CLI
        # whose current turn is interrupted/wedged (inflight>0 AND _interrupted); it releases only once the
        # ResultMessage settles inflight to 0. Source-pinned because inputs() is a nested closure.
        import inspect
        src = inspect.getsource(sb.SdkSession)
        self.assertIn("blocked = self.inflight > 0 and self._interrupted", src,
                      "inputs() holds queued turns while a turn is interrupted/wedged")

    def test_image_echo_is_never_floored_it_lands_by_text(self):
        # The screenshots-piling-up bug (the user 2026-06-25) was the TMUX composer's: its paste hook
        # rewrites a pasted image path to "[Image #N]", so the echoed path is never in tx_user_texts and a
        # FIFO floor had to retire the echo once a later genuine-human turn landed. The SDK route never
        # runs that hook — stream-json input lands the path as typed — so since 2026-09-06 no SDK echo is
        # floored: an image echo retires when its own text lands (or when the CLI dies holding it, the
        # dropped marking), exactly like a plain-text one. tests/test_sdk_echo_durability.py has the rest.
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)
        be._live["s"] = {"echo:img": {"uuid": "echo:img", "t": 100, "_echo_text": "/abs/shot.png"}}
        be.prune_live("s", set(), set())               # nothing landed → the echo is the send's only record
        self.assertEqual([a["uuid"] for a in be.live_atoms("s")], ["echo:img"])
        be.prune_live("s", set(), set(), human_floor=120)   # a later genuine-human turn: not a retire here
        self.assertEqual([a["uuid"] for a in be.live_atoms("s")], ["echo:img"],
                         "the message may still sit in the CLI's queue; its path will land as typed")
        be.prune_live("s", set(), {"/abs/shot.png": 130}, human_floor=130)   # its own record lands → retire
        self.assertEqual(be.live_atoms("s"), [])
        # the floor must NOT retire a real stream atom (no _echo_text) — those prune by uuid only
        be._live["s"] = {"a9": {"uuid": "a9", "t": 50}}
        be.prune_live("s", set(), set(), human_floor=300)
        self.assertEqual([a["uuid"] for a in be.live_atoms("s")], ["a9"])

    def test_stale_command_atom_pruned_by_human_floor(self):
        # a COMMAND atom (the CLI's streamed /model feedback) from a TURN-LESS control request may never
        # get a transcript record to land against (the user 2026-07-02) — the floor retires it once a
        # genuine human turn postdates it, so the stale confirmation never rides inside later turns.
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)
        cmd = {"uuid": "c1", "t": 100, "command": True, "type": "assistant"}
        be._live["s"] = {"c1": dict(cmd)}
        be.prune_live("s", set(), set())                    # no floor yet → the confirmation stays visible
        self.assertEqual([a["uuid"] for a in be.live_atoms("s")], ["c1"])
        be.prune_live("s", set(), set(), human_floor=150)   # a later genuine human turn → retire it
        self.assertEqual(be.live_atoms("s"), [])
        be._live["s"] = {"c2": {"uuid": "c2", "t": 200, "command": True, "type": "assistant"}}
        be.prune_live("s", set(), set(), human_floor=150)   # newer than the floor → survives
        self.assertEqual([a["uuid"] for a in be.live_atoms("s")], ["c2"])

    def test_send_adds_optimistic_echo(self):
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)
        be._ensure = lambda sid: type("S", (), {"enqueue": lambda self, t, todo="": None})()   # no real session thread
        self.assertTrue(be.send("s", "type this"))
        echoes = [a for a in be.live_atoms("s") if a.get("_echo_text") == "type this"]
        self.assertEqual(len(echoes), 1)
        self.assertEqual(echoes[0]["type"], "user")
        self.assertEqual(echoes[0]["author"], "human", "a typed message echoes as a human (blue) bubble")
        self.assertEqual(echoes[0]["message"]["content"], [{"type": "text", "text": "type this"}])

    def test_set_effort_synthesizes_the_command_atom(self):
        """The effort reconnect leaves NO transcript record — without a synthesized "/effort X" atom an
        idle-session effort change showed nothing in the chat while a busy (parked) one showed a queued
        chip: the same pick, acknowledged or not depending on timing (the user 2026-07-05). Mirrors the
        set_model synthesis exactly."""
        d = tempfile.mkdtemp()
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None)
        sid = "11111111-2222-3333-4444-555555555555"
        sb.write_reg(d, sid, {"sid": sid, "name": "n", "cwd": "/tmp", "alive": True})
        s = sb.SdkSession(be, {"sid": sid, "name": "n", "cwd": "/tmp"})
        be.sessions[sid] = s
        self.assertTrue(be.set_effort(sid, "high"))
        cmds = [a for a in be.live_atoms(sid) if a.get("command") == "/effort"]
        self.assertEqual(len(cmds), 1, "one live '/effort high' invocation atom, like set_model's '/model X'")
        self.assertEqual(cmds[0]["_echo_text"], "/effort high")
        self.assertEqual(cmds[0]["message"]["content"], [{"type": "text", "text": "/effort high"}])
        self.assertEqual(cmds[0]["author"], "human")

    def test_set_effort_on_a_dormant_session_still_leaves_the_acknowledging_chip(self):
        # no live thread → the value applies on the next connect — but the pick is still acknowledged
        # (reversing this test's earlier "stays quiet" pin): the chip is what the composer's optimistic
        # bubble retires against, and with nothing landing on a dormant session a typed "/effort low"
        # sat as an unconfirmed dashed bubble and then vanished without a trace
        d = tempfile.mkdtemp()
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None)
        sid = "11111111-2222-3333-4444-666666666666"
        sb.write_reg(d, sid, {"sid": sid, "name": "n", "cwd": "/tmp", "alive": True})
        self.assertTrue(be.set_effort(sid, "low"))
        cmds = [a for a in be.live_atoms(sid) if a.get("command") == "/effort"]
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0]["message"]["content"], [{"type": "text", "text": "/effort low"}])
        self.assertIsNone(cmds[0]["fsid"], "no live thread and no last resume target → none")
        self.assertEqual(sb.read_reg(d, sid)["effort"], "low", "and the value still applies at the next connect")

    def _live_fast_session(self, d, sid, unlocked=False):
        """A constructed SdkSession whose thread READS alive (set_fast's gate) without spawning a CLI.
        `unlocked` simulates a connection made WITH the fastMode flag (the _connect_once snapshot)."""
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None)
        sb.write_reg(d, sid, {"sid": sid, "name": "n", "cwd": "/tmp", "alive": True})
        s = sb.SdkSession(be, {"sid": sid, "name": "n", "cwd": "/tmp"})
        s.thread = type("T", (), {"is_alive": lambda self: True})()
        s._fast_unlocked = unlocked
        be.sessions[sid] = s
        return be, s

    def test_set_fast_on_an_unlocked_connection_delivers_the_slash_command(self):
        """A connection made WITH the fastMode flag-settings opt-in interprets the literal '/fast on|off'
        (the CLI's descriptor is marked supportsNonInteractive; without the flag it refuses the command
        outright — verified against claude 2.1.224). So an unlocked session takes the live send in BOTH
        directions, no reconnect: the echo is the chat's acknowledgement, the flip is optimistic, and
        fast_mode_state on the next init re-asserts the truth. The reg mirrors every toggle — the
        persisted ask that drives the next connect's flag, so a lingering opt-in is impossible."""
        d = tempfile.mkdtemp()
        sid = "11111111-2222-3333-4444-777777777777"
        be, s = self._live_fast_session(d, sid, unlocked=True)
        self.assertTrue(s._fast_unlocked, "precondition: THIS connection carries the opt-in flag")
        reconnects = []
        s.request_reconnect = lambda: reconnects.append(1)
        self.assertTrue(be.set_fast(sid, "on"))
        self.assertEqual(s.pending(), ["/fast on"], "the literal command is queued for the CLI to interpret")
        echoes = [a for a in be.live_atoms(sid) if a.get("_echo_text") == "/fast on"]
        self.assertEqual(len(echoes), 1, "the send path's echo IS the chat acknowledgement")
        self.assertEqual(s.fast, "on", "optimistic flip — init re-asserts")
        self.assertEqual(s.snapshot()["fast"], "on", "the badge reads it from the snapshot")
        self.assertTrue(sb.read_reg(d, sid)["fast"], "the reg mirrors the toggle")
        self.assertTrue(be.set_fast(sid, "off"), "…and OFF is a live send too, not a reconnect")
        self.assertEqual(s.pending(), ["/fast on", "/fast off"])
        self.assertFalse(sb.read_reg(d, sid)["fast"], "the reg mirrors the off as well")
        self.assertEqual(reconnects, [], "an unlocked connection never reconnects for a toggle")

    def test_a_live_toggle_arms_the_one_shot_expectation(self):
        # The toggle's own turn opens with an init reporting the state at turn START — one word stale.
        # set_fast arms _fast_expect so exactly that init yields (behavior in FastModeReportedState).
        d = tempfile.mkdtemp()
        sid = "11111111-2222-3333-4444-999999999999"
        be, s = self._live_fast_session(d, sid, unlocked=True)
        self.assertTrue(be.set_fast(sid, "on"))
        self.assertEqual(s._fast_expect, "on")
        self.assertTrue(be.set_fast(sid, "off"))
        self.assertEqual(s._fast_expect, "off")

    def test_set_fast_first_opt_in_reconnects_to_apply_the_flag(self):
        # The current connection was made WITHOUT the flag, so the CLI would refuse the literal send;
        # the opt-in applies at the (re)connect that carries it (request_reconnect, the /effort machinery:
        # at once when the session is quiet, else at the turn settle that finds it quiet).
        d = tempfile.mkdtemp()
        sid = "11111111-2222-3333-4444-888888888888"
        be, s = self._live_fast_session(d, sid, unlocked=False)
        reconnects = []
        s.request_reconnect = lambda: reconnects.append(1)
        self.assertTrue(be.set_fast(sid, "on"))
        self.assertEqual(len(reconnects), 1, "the flag is connect-time here → reconnect to apply")
        self.assertEqual(s.pending(), [], "no literal send — this connection would refuse it")
        self.assertTrue(s.fast_opt, "the next _options carries the flag")
        self.assertEqual(s.fast, "", "no flip at the pick: the ARM flips the badge when the flagged connect is due "
                         "(review round 3; SettingsPickWaitsForLiveWork.test_m drives it)")
        self.assertTrue(sb.read_reg(d, sid)["fast"])

    def test_set_fast_off_on_a_locked_connection_is_a_no_op_beyond_the_reg(self):
        # No flag at connect → fast mode is already off on this connection; there is nothing to send
        # and nothing to reconnect for. The reg still flips — it is the persisted ask.
        d = tempfile.mkdtemp()
        sid = "11111111-2222-3333-4444-999999999999"
        be, s = self._live_fast_session(d, sid, unlocked=False)
        sb.write_reg(d, sid, dict(sb.read_reg(d, sid), fast=True))   # a stale on-disk ask to clear
        reconnects = []
        s.request_reconnect = lambda: reconnects.append(1)
        self.assertTrue(be.set_fast(sid, "off"))
        self.assertEqual(s.pending(), [], "nothing to send — the connection never had fast mode")
        self.assertEqual(reconnects, [], "and nothing to reconnect for")
        self.assertFalse(sb.read_reg(d, sid)["fast"], "but the ask is cleared, so the next connect is plain")
        self.assertFalse(s.fast_opt)

    def test_set_fast_on_a_dormant_session_persists_and_applies_at_the_next_connect(self):
        # No live thread → nothing to send and nothing to reconnect; the reg carries the ask and the
        # NEXT connect applies it (fast_opt seeds from the reg, _options writes the flag file).
        d = tempfile.mkdtemp()
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None)
        sid = "11111111-2222-3333-4444-aaaaaaaaaaaa"
        sb.write_reg(d, sid, {"sid": sid, "name": "n", "cwd": "/tmp", "alive": True})
        self.assertTrue(be.set_fast(sid, "on"), "accepted: the pick applies at the next connect")
        self.assertTrue(sb.read_reg(d, sid)["fast"])
        self.assertEqual(be.live_atoms(sid), [], "nothing claimed in the chat — no live CLI took it")
        s = sb.SdkSession(be, {"sid": sid, "name": "n", "cwd": "/tmp", "fast": True})
        self.assertTrue(s.fast_opt, "a fresh construction picks the ask up from the reg")
        # the per-connection unlock is snapshotted from fast_opt exactly where _connect_once builds
        # the options that carry the flag, so the two can never disagree
        import inspect
        self.assertIn("self._fast_unlocked = self.fast_opt", inspect.getsource(sb.SdkSession._amain))

    def test_set_fast_refuses_bad_values_and_unknown_sids(self):
        d = tempfile.mkdtemp()
        sid = "11111111-2222-3333-4444-bbbbbbbbbbbb"
        be, s = self._live_fast_session(d, sid, unlocked=True)
        self.assertFalse(be.set_fast(sid, "maybe"))
        self.assertEqual(s.pending(), [], "a bad value never reaches the CLI")
        be2 = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)
        self.assertFalse(be2.set_fast("no-such-sid", "on"))

    def test_fast_mode_is_never_remembered_as_the_seed_for_new_sessions(self):
        # Fast mode draws credits at a higher rate and has its own rate limit, so it stays per-session —
        # the same call ultracode makes, and the reason romp never spreads it to every new session.
        d = tempfile.mkdtemp()
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None)
        sid = be.spawn("a", d)
        self.assertTrue(be.set_fast(sid, "on"))
        self.assertNotIn("fast", sb.read_sdk_defaults(d), "never becomes the default for the next session")
        self.assertFalse(sb.read_reg(d, be.spawn("b", d)).get("fast"), "a NEW session starts plain")
        self.assertTrue(sb.read_reg(d, sid)["fast"], "but THIS session keeps it")

    def test_init_reports_fast_mode_state_into_the_snapshot(self):
        """fast_mode_state rides the CLI's init message ("on"/"off"/"cooldown", plus a disabled_reason
        when the org/model can't use it) — the AUTHORITATIVE source behind the chat's fast badge. An
        init WITHOUT the field (older CLI) must leave the state unknown, never fabricate "off"."""
        import asyncio
        class _Sys:
            def __init__(self, data): self.subtype = "init"; self.data = data
        d = tempfile.mkdtemp()
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None)
        sid = "11111111-2222-3333-4444-aaaaaaaaaaaa"
        sb.write_reg(d, sid, {"sid": sid, "name": "n", "cwd": "/tmp", "alive": True})
        s = sb.SdkSession(be, {"sid": sid, "name": "n", "cwd": "/tmp"})
        async def _noop(): pass
        s._do_refresh_context = _noop
        self.assertEqual(s.snapshot()["fast"], "", "unknown until an init lands → no badge")

        async def run(data):
            s._on_message(_Sys(data), _AssistantMessage, _ResultMessage, _Sys)
            await asyncio.sleep(0)                       # let the ensure_future'd refresh run
        asyncio.run(run({"fast_mode_state": "on"}))
        self.assertEqual(s.fast, "on")
        self.assertEqual(s.snapshot()["fast"], "on")
        self.assertEqual(s.snapshot()["fastReason"], "")
        asyncio.run(run({"fast_mode_state": "off", "fast_mode_disabled_reason": "Fast mode is org-disabled"}))
        self.assertEqual(s.fast, "off")
        self.assertEqual(s.snapshot()["fastReason"], "Fast mode is org-disabled",
                         "a disabled_reason rides along so the kernel can hide the toggle")
        asyncio.run(run({}))                             # an init with no field → the last truth STANDS
        self.assertEqual(s.fast, "off", "absent field never overwrites the known state")

    def test_the_opt_in_required_reason_never_hides_the_toggle(self):
        """The CLI stamps 'sdk_opt_in_required' on EVERY connect made without the fastMode
        flag-settings opt-in (verified live 2026-08-10 on 2.1.226 — opus/fable/sonnet headless
        connects alike). Treating it like a real refusal hid the chat toggle on every SDK session:
        the control that GRANTS the opt-in was gated on already having it (the user 2026-08-10,
        who switched to Opus and found no toggle anywhere). It reads as 'available, currently off';
        every other reason still hides the dead control."""
        import asyncio
        class _Sys:
            def __init__(self, data): self.subtype = "init"; self.data = data
        d = tempfile.mkdtemp()
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None)
        sid = "11111111-2222-3333-4444-cccccccccccc"
        sb.write_reg(d, sid, {"sid": sid, "name": "n", "cwd": "/tmp", "alive": True})
        s = sb.SdkSession(be, {"sid": sid, "name": "n", "cwd": "/tmp"})
        async def _noop(): pass
        s._do_refresh_context = _noop

        async def run(data):
            s._on_message(_Sys(data), _AssistantMessage, _ResultMessage, _Sys)
            await asyncio.sleep(0)
        asyncio.run(run({"fast_mode_state": "off", "fast_mode_disabled_reason": "sdk_opt_in_required"}))
        self.assertEqual(s.fast, "off")
        self.assertEqual(s.snapshot()["fastReason"], "", "the curable opt-in reason shows the badge")
        asyncio.run(run({"fast_mode_state": "off", "fast_mode_disabled_reason": "Fast mode is org-disabled"}))
        self.assertEqual(s.snapshot()["fastReason"], "Fast mode is org-disabled",
                         "a real refusal still hides the toggle")

    def test_a_refusal_answering_the_users_ask_warns_clears_it_and_restores_the_badge(self):
        """A disabled_reason that lands while the user's ask is ARMED (fast_opt — they picked On) is
        the CLI ANSWERING that ask, not standing state to hide behind. Adopting it silently was the
        vanishing-button bug (the user 2026-08-11, whose tap on a phone-width statusline was refused
        with extra_usage_disabled): the reason hid the very toggle they had just clicked, no word
        why, and the reg's ask stayed armed forever. The refusal is LOUD now — one warn toast naming
        the humanized reason — the ask clears (fast_opt + reg, so the opt-in flag doesn't linger),
        and a flagless reconnect is requested: its connect-time re-probe reports the blanked
        sdk_opt_in_required, so the badge comes BACK instead of staying vanished."""
        import asyncio
        class _Sys:
            def __init__(self, data): self.subtype = "init"; self.data = data
        d = tempfile.mkdtemp()
        notes = []
        be = sb.SdkBackend(d, "/bin/true", lambda app, msg: notes.append((app, msg)))
        sid = "11111111-2222-3333-4444-eeeeeeeeeeee"
        sb.write_reg(d, sid, {"sid": sid, "name": "n", "cwd": "/tmp", "alive": True})
        s = sb.SdkSession(be, {"sid": sid, "name": "n", "cwd": "/tmp"})
        s.thread = type("T", (), {"is_alive": lambda self: True})()
        be.sessions[sid] = s
        async def _noop(): pass
        s._do_refresh_context = _noop
        reconnects = []
        s.request_reconnect = lambda: reconnects.append(1)
        async def run(data):
            s._on_message(_Sys(data), _AssistantMessage, _ResultMessage, _Sys)
            await asyncio.sleep(0)

        def warns():
            return [m for _, m in notes if isinstance(m, dict) and m.get("type") == "warn"]

        self.assertTrue(be.set_fast(sid, "on"))          # arms the ask (locked connection → reconnect)
        self.assertEqual(len(reconnects), 1)
        asyncio.run(run({"fast_mode_state": "off",
                         "fast_mode_disabled_reason": "extra_usage_disabled"}))
        self.assertEqual(len(warns()), 1, "ONE toast says why — a refusal is never a silent vanish")
        self.assertIn("extra usage", warns()[0]["text"], "the reason is humanized, not the raw token")
        self.assertFalse(s.fast_opt, "the ask is answered — cleared, not left armed forever")
        self.assertFalse(sb.read_reg(d, sid)["fast"], "…and cleared on disk, so the next connect is plain")
        self.assertEqual(len(reconnects), 2, "a flagless reconnect re-probes so the badge comes back")
        # the same refusal WITHOUT an armed ask stays the quiet dead-control hide it always was
        asyncio.run(run({"fast_mode_state": "off",
                         "fast_mode_disabled_reason": "extra_usage_disabled"}))
        self.assertEqual(len(warns()), 1, "no fresh ask → no re-warn")
        self.assertEqual(len(reconnects), 2, "…and no reconnect churn")
        self.assertEqual(s.snapshot()["fastReason"], "extra_usage_disabled",
                         "the reason still hides the dead control when nobody asked")

    def test_the_toggle_turns_own_init_yields_to_the_sent_word_once(self):
        """A literal '/fast on' send opens a turn whose init still reports the state at turn START —
        one word stale, since the toggle applies after it. Taking it verbatim stomps set_fast's
        optimistic flip until the NEXT turn's init, so the badge reads off for a whole turn right
        after the CLI acknowledged the toggle. That single stale, reason-less word yields to the
        send's one-shot expectation; the next init wins unconditionally, and a disabled_reason
        (real refusal evidence) always wins immediately."""
        import asyncio
        class _Sys:
            def __init__(self, data): self.subtype = "init"; self.data = data
        d = tempfile.mkdtemp()
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None)
        sid = "11111111-2222-3333-4444-bbbbbbbbbbbb"
        sb.write_reg(d, sid, {"sid": sid, "name": "n", "cwd": "/tmp", "alive": True})
        s = sb.SdkSession(be, {"sid": sid, "name": "n", "cwd": "/tmp"})
        s.thread = type("T", (), {"is_alive": lambda self: True})()
        s._fast_unlocked = True
        be.sessions[sid] = s
        async def _noop(): pass
        s._do_refresh_context = _noop
        async def run(data):
            s._on_message(_Sys(data), _AssistantMessage, _ResultMessage, _Sys)
            await asyncio.sleep(0)

        self.assertTrue(be.set_fast(sid, "on"))
        self.assertEqual(s.fast, "on", "optimistic flip on the live send")
        self.assertEqual(s._fast_expect, "on", "…armed for the send's own turn-init")
        asyncio.run(run({"fast_mode_state": "off"}))     # the toggle turn's init: one word stale
        self.assertEqual(s.fast, "on", "the same-turn stale word yields")
        asyncio.run(run({"fast_mode_state": "off"}))     # any LATER init is authoritative
        self.assertEqual(s.fast, "off", "one-shot — the next init wins")

        self.assertTrue(be.set_fast(sid, "on"))          # armed again…
        asyncio.run(run({"fast_mode_state": "off",
                         "fast_mode_disabled_reason": "Fast mode is org-disabled"}))
        self.assertEqual(s.fast, "off", "…but a disabled_reason beats the expectation immediately")
        self.assertEqual(s.snapshot()["fastReason"], "Fast mode is org-disabled")

    def test_fast_state_survives_a_kernel_restart_via_the_reg(self):
        """The init message only streams WITH a turn, so in-memory-only fast state meant every kernel
        restart blanked every session's badge until it next spoke (the user 2026-08-10, who found the
        toggle nowhere). The state persists to the reg on adoption (liveFast/liveFastReason, the
        liveModel pattern) and seeds the next construction — and a DORMANT session (no thread at all
        after a restart) reports it straight from the reg in live_sessions."""
        import asyncio
        class _Sys:
            def __init__(self, data): self.subtype = "init"; self.data = data
        d = tempfile.mkdtemp()
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None)
        sid = "11111111-2222-3333-4444-dddddddddddd"
        sb.write_reg(d, sid, {"sid": sid, "name": "n", "cwd": "/tmp", "alive": True})
        s = sb.SdkSession(be, {"sid": sid, "name": "n", "cwd": "/tmp"})
        async def _noop(): pass
        s._do_refresh_context = _noop
        async def run(data):
            s._on_message(_Sys(data), _AssistantMessage, _ResultMessage, _Sys)
            await asyncio.sleep(0)
        asyncio.run(run({"fast_mode_state": "off", "fast_mode_disabled_reason": "sdk_opt_in_required"}))
        reg = sb.read_reg(d, sid)
        self.assertEqual(reg["liveFast"], "off", "adoption persists the state")
        self.assertEqual(reg["liveFastReason"], "", "…with the curable reason already blanked")
        # "the kernel restarts": a fresh construction from the same reg — the badge is there pre-turn
        s2 = sb.SdkSession(be, sb.read_reg(d, sid))
        self.assertEqual(s2.fast, "off", "seeded from the reg, no init needed")
        self.assertEqual(s2.fast_reason, "")
        # …and a session with NO thread at all reports it straight from the reg
        live = be.live_sessions()
        self.assertEqual(live[sid]["fast"], "off", "a dormant session's badge survives the restart")
        self.assertEqual(live[sid]["fastReason"], "")

    def test_connect_adopts_fast_state_from_the_initialize_response(self):
        """A turn-less connect emits NO init message, so a session that merely reconnected (every
        session, after a kernel restart) knew nothing until it next spoke — and a /model switch never
        produced a badge at all. The initialize response the SDK stores at connect (get_server_info)
        carries the same fast_mode_state/fast_mode_disabled_reason fields (verified live 2026-08-10 on
        2.1.226), and _connect_once adopts it right beside the pre-turn context/model refresh."""
        import asyncio
        import inspect
        d = tempfile.mkdtemp()
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None)
        sid = "11111111-2222-3333-4444-eeeeeeeeeeee"
        sb.write_reg(d, sid, {"sid": sid, "name": "n", "cwd": "/tmp", "alive": True})
        s = sb.SdkSession(be, {"sid": sid, "name": "n", "cwd": "/tmp"})
        self.assertEqual(s.fast, "", "unknown before the connect")
        class _Client:
            async def get_server_info(self):
                return {"fast_mode_state": "off", "fast_mode_disabled_reason": "sdk_opt_in_required"}
        s.client = _Client()
        asyncio.run(s._do_adopt_server_info())
        self.assertEqual(s.fast, "off", "the badge exists pre-turn")
        self.assertEqual(s.fast_reason, "", "the curable opt-in reason never hides the toggle")
        self.assertEqual(sb.read_reg(d, sid)["liveFast"], "off", "…and it persisted")
        # the adoption is wired into the connect path, beside the pre-turn context refresh
        self.assertIn("_do_adopt_server_info", inspect.getsource(sb.SdkSession._amain))

    def test_send_echo_authors_a_romp_nudge_as_romp_not_human(self):
        # the bug (the user 2026-06-28): an auto-nudge sent through send() echoed as a BLUE HUMAN "Follow-up"
        # instead of the GRAY "from romp" auto-nudge it is, because the echo hardcoded author="human". The echo
        # must author from the same markers the event model uses on the real atom.
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)
        be._ensure = lambda sid: type("S", (), {"enqueue": lambda self, t, todo="": None})()
        body = "Status on the goal above?\n<!-- romp-injected --><!-- romp-auto --><!-- romp-goal-id: s:g1 -->"
        be.send("s", body)
        e = next(a for a in be.live_atoms("s") if a.get("_echo_text") == body)
        self.assertEqual(e["author"], "romp", "a romp-injected nudge echoes as romp, not human")
        self.assertTrue(e.get("rompAuto"), "the romp-auto marker → the romp-logo (auto-nudge) flag")
        # a NUDGE-BUTTON injection (romp-injected, NOT romp-auto) is romp but not auto
        be.send("s", "do X\n<!-- romp-injected --><!-- romp-goal-id: s:g1 -->")
        e2 = next(a for a in be.live_atoms("s") if a.get("_echo_text", "").startswith("do X"))
        self.assertEqual(e2["author"], "romp")
        self.assertFalse(e2.get("rompAuto"), "a Nudge-button injection is romp but not auto (no romp-logo)")

    def test_context_pct_from_sdk_get_context_usage(self):
        """The context bar reads the SDK's OWN number, not a window guess (the user 2026-06-24: SDK read 14%
        where tmux read 3% on a 1M-context model — a wrong-window inference). _do_refresh_context calls
        get_context_usage() — the control request behind the CLI's /context, which already divides by the real
        window and accounts for the autocompact buffer — and stores its `percentage` (rounded) + live `model`,
        persisting both so they survive idle/restart. None until the first refresh lands."""
        import asyncio
        d = tempfile.mkdtemp()
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None)
        sid = "11111111-2222-3333-4444-555555555555"
        s = sb.SdkSession(be, {"sid": sid, "name": "n", "cwd": "/tmp"})
        self.assertIsNone(s._ctx_pct(), "no refresh yet → no context bar")

        class _Client:
            def __init__(self, payload): self._p = payload
            async def get_context_usage(self): return self._p
        s.client = _Client({"percentage": 2.7, "model": "claude-opus-4-8"})
        asyncio.run(s._do_refresh_context())
        self.assertEqual(s._ctx_pct(), 3, "stores the SDK's rounded percentage — no window inference")
        self.assertEqual(s.model, "Opus 4.8", "adopts the SDK-reported model id")
        self.assertEqual(sb.read_reg(d, sid).get("liveCtx"), 3, "persists ctx so the bar survives idle/restart")
        self.assertEqual(sb.read_reg(d, sid).get("liveModel"), "Opus 4.8", "persists the live model too")

        s.client = _Client({"percentage": 88, "model": "claude-opus-4-8"})
        asyncio.run(s._do_refresh_context())
        self.assertEqual(s._ctx_pct(), 88, "tracks the live value across turns")
        self.assertFalse(s._ctx_over, "88% is inside the window — no overflow flag")

        # the CLI documents percentage as "0-100+": past 100 the tokens exceed the CURRENT model's
        # window (a 1M→200k model switch does this instantly). The battery stays clamped at 100,
        # but the overflow is surfaced (ctxOver) instead of clamped into a silent, wrong-looking
        # 100% (the user 2026-09-02, who switched models and read the full battery as a bug).
        s.client = _Client({"percentage": 147, "model": "claude-haiku-4-5"})
        asyncio.run(s._do_refresh_context())
        self.assertEqual(s._ctx_pct(), 100, "the gauge value itself stays clamped")
        self.assertTrue(s._ctx_over, "…but the overflow is news, not noise")
        self.assertTrue(s.snapshot()["ctxOver"], "the snapshot ships it to the statusline")
        self.assertTrue(sb.read_reg(d, sid).get("liveCtxOver"),
                        "persisted beside liveCtx so a dormant/restarted session keeps saying so")
        s.client = _Client({"percentage": 61, "model": "claude-haiku-4-5"})
        asyncio.run(s._do_refresh_context())
        self.assertFalse(s._ctx_over, "dropping back inside the window clears the flag")
        self.assertFalse(sb.read_reg(d, sid).get("liveCtxOver"))

    def test_context_refresh_queued_when_one_is_in_flight(self):
        """A model/effort switch can ask for a context refresh while the turn-end refresh is still in
        flight. The in-flight guard used to DROP that call silently, leaving the old model's percentage
        standing until the next turn (the user 2026-09-02) — now it queues exactly one rerun, so the
        number reflects the newest world."""
        import asyncio
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)
        s = sb.SdkSession(be, {"sid": "11111111-2222-3333-4444-555555555555", "name": "n", "cwd": "/tmp"})

        class _Counting:
            def __init__(self): self.calls = 0
            async def get_context_usage(self): self.calls += 1; return {"percentage": 40}
        s.client = _Counting()
        s._ctx_refreshing = True                       # a refresh is mid-flight
        asyncio.run(s._do_refresh_context())
        self.assertEqual(s.client.calls, 0, "the guarded call never races the in-flight one")
        self.assertTrue(s._ctx_refresh_again, "…but it is REMEMBERED, not dropped")
        s._ctx_refreshing = False
        asyncio.run(s._do_refresh_context())           # the in-flight one finishing runs the queued ask
        self.assertEqual(s.client.calls, 2, "the queued rerun fires after the live refresh lands")
        self.assertFalse(s._ctx_refresh_again, "the queue holds ONE rerun, not a storm")

    def test_queued_refresh_survives_a_failed_attempt(self):
        """PR #886 review: the early return on a failed/None payload sat BEFORE the rerun tail, so a
        switch-time ask queued behind a refresh that then errored was dropped on the floor — the old
        model's number stood until the next turn. The rerun fires however the attempt ended."""
        import asyncio
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)
        s = sb.SdkSession(be, {"sid": "11111111-2222-3333-4444-555555555555", "name": "n", "cwd": "/tmp"})

        class _FailThenWork:
            def __init__(self): self.calls = 0
            async def get_context_usage(self):
                self.calls += 1
                if self.calls == 1:
                    raise RuntimeError("control channel hiccup")
                return {"percentage": 40}
        s.client = _FailThenWork()
        s._ctx_refresh_again = True                    # an ask queued while the failing one was in flight
        asyncio.run(s._do_refresh_context())           # attempt 1 fails; the queued rerun must still run
        self.assertEqual(s.client.calls, 2, "the queued ask reruns even when the attempt it waited on failed")
        self.assertEqual(s._ctx_pct(), 40, "…and the rerun's answer lands")
        self.assertFalse(s._ctx_refresh_again)

    def test_assistant_model_sets_badge_but_synthetic_does_not_corrupt_it(self):
        """The model 'doesn't show' mid-conversation (the user 2026-06-24): injected/synthetic assistant turns
        carry model='<synthetic>', which an unguarded assign wrote straight onto the statusline + timeline
        badge (both read self.model via the snapshot). A real model id sets the badge; '<synthetic>' must be
        ignored so the last real model sticks."""
        class _Sys:                                              # a stand-in for SystemMessage (isinstance arg only)
            pass
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)
        s = sb.SdkSession(be, {"sid": "11111111-2222-3333-4444-555555555555", "name": "n", "cwd": "/tmp"})
        s._on_message(_AssistantMessage([_TextBlock("hi")], model="claude-opus-4-8"),
                      _AssistantMessage, _ResultMessage, _Sys)
        self.assertEqual(s.model, "Opus 4.8", "a real model id sets the badge")
        s._on_message(_AssistantMessage([_TextBlock("x")], model="<synthetic>"),
                      _AssistantMessage, _ResultMessage, _Sys)
        self.assertEqual(s.model, "Opus 4.8", "a synthetic turn must NOT overwrite the real model")

    def test_compact_boundary_refreshes_context_now(self):
        """After /compact the active context drops to the summary, but the % used to refresh only on the next
        turn's ResultMessage. The CLI auto-runs a continuation turn after /compact that can work for minutes,
        so until it settled the bar kept showing the STALE pre-compact % (the user 2026-06-30, who compacted
        but it still said 72%). A compact_boundary system message must re-pull the % on the boundary itself."""
        import asyncio
        class _Sys:                                              # stand-in for SystemMessage (isinstance + subtype)
            def __init__(self, subtype): self.subtype = subtype; self.data = {}
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)
        s = sb.SdkSession(be, {"sid": "11111111-2222-3333-4444-555555555555", "name": "n", "cwd": "/tmp"})
        calls = []
        async def _fake_refresh(): calls.append(True)
        s._do_refresh_context = _fake_refresh

        async def run():
            s._on_message(_Sys("compact_boundary"), _AssistantMessage, _ResultMessage, _Sys)
            await asyncio.sleep(0)                               # let the ensure_future'd refresh run
        asyncio.run(run())
        self.assertEqual(len(calls), 1, "compact_boundary re-pulls the context % immediately, not next turn")

    def test_interrupt_flips_to_waiting_before_the_blocking_control_request(self):
        """client.interrupt() BLOCKS until the CLI acknowledges the interrupt, which can take seconds mid-
        stream (the CLI won't ack until the model call hits a boundary). If _interrupted — the flag that makes
        the snapshot read 'waiting' — were set only AFTER that await, a stopped turn keeps reading 'working'
        the whole time (the user 2026-06-30, who interrupted but it said working for a while). The flag must
        flip up front, so the lane reflects the stop the instant the user hits it."""
        import asyncio
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)
        s = sb.SdkSession(be, {"sid": "11111111-2222-3333-4444-555555555555", "name": "n", "cwd": "/tmp"})
        s.inflight = 1
        seen = {}
        class _Client:
            async def interrupt(self):
                seen["interrupted_at_send"] = s._interrupted   # what the UI already reads when the request goes out
        s.client = _Client()
        asyncio.run(s._do_interrupt())
        self.assertTrue(seen.get("interrupted_at_send"),
                        "the snapshot already read 'waiting' BEFORE the blocking control request")
        self.assertEqual(s.snapshot()["state"], "waiting", "an interrupted in-flight turn reads 'waiting', not 'working'")

    def test_snapshot_exposes_the_in_flight_interrupt_flag(self):
        """The kernel's chip + feed 'interrupting' badge keys on this snapshot field (== _interrupted), NOT the
        transcript tail — the tail retires at the ResultMessage BEFORE the stop record lands, so keying on it
        flickered 'Interrupting…' → 'Working' (the user 2026-07-07). The flag spans the whole in-flight window:
        True from dispatch, False once the aborted turn's ResultMessage settles it."""
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)
        s = sb.SdkSession(be, {"sid": "11111111-2222-3333-4444-555555555555", "name": "n", "cwd": "/tmp"})
        self.assertFalse(s.snapshot()["interrupting"], "idle → not interrupting")
        s._interrupted = True
        self.assertTrue(s.snapshot()["interrupting"], "an in-flight interrupt surfaces on the snapshot")
        s._interrupted = False
        self.assertFalse(s.snapshot()["interrupting"], "cleared once the ResultMessage settles it")

    def test_interrupt_sets_the_flag_synchronously_at_dispatch(self):
        """interrupt() schedules the async _do_interrupt, but the kernel stamps _interrupt_clicked and pushes
        the instant it returns — so _interrupted must already be True SYNCHRONOUSLY, not one event-loop tick
        later (else the first snapshot after the click misses it and the badge flickers, the user 2026-07-07)."""
        import asyncio
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)
        s = sb.SdkSession(be, {"sid": "11111111-2222-3333-4444-555555555555", "name": "n", "cwd": "/tmp"})
        loop = asyncio.new_event_loop()
        try:
            s.loop = loop
            s.client = object()   # truthy — interrupt() only guards on `self.loop and self.client`
            self.assertFalse(s._interrupted)
            s.interrupt()         # loop never runs → the scheduled _do_interrupt does NOT execute
            self.assertTrue(s._interrupted, "the flag flips synchronously, before the scheduled _do_interrupt")
            self.assertTrue(s.snapshot()["interrupting"], "so the very next snapshot already reads 'interrupting'")
        finally:
            loop.close()


class LiveSubagents(unittest.TestCase):
    """SubagentStart/SubagentStop hooks track the Task subagents running RIGHT NOW — the transparency the tmux
    backend never had (the user 2026-06-30). The live set keeps the session 'working' while any run (covers a
    BACKGROUNDED subagent that outlives the main turn) and surfaces a count on the lane."""

    def _sess(self):
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)
        return sb.SdkSession(be, {"sid": "11111111-2222-3333-4444-555555555555", "name": "n", "cwd": "/tmp"})

    def test_start_and_stop_track_the_live_set(self):
        import asyncio
        s = self._sess()
        async def run():
            await s._subagent_start_hook({"agent_id": "a1", "agent_type": "code-reviewer"}, None, None)
            await s._subagent_start_hook({"agent_id": "a2", "agent_type": "general-purpose"}, None, None)
            self.assertEqual({d["type"] for d in s._live_subagents()}, {"code-reviewer", "general-purpose"})
            await s._subagent_stop_hook({"agent_id": "a1"}, None, None)
            self.assertEqual([d["type"] for d in s._live_subagents()], ["general-purpose"])
            await s._subagent_stop_hook({"agent_id": "a2"}, None, None)
            self.assertEqual(s._live_subagents(), [], "the set empties when the last subagent stops")
        asyncio.run(run())

    def test_snapshot_exposes_the_live_subagents(self):
        import asyncio
        s = self._sess()
        asyncio.run(s._subagent_start_hook({"agent_id": "a1", "agent_type": "code-reviewer"}, None, None))
        snap = s.snapshot()
        self.assertEqual([d["type"] for d in snap["subagents"]], ["code-reviewer"],
                         "the snapshot carries the live subagents for the lane")

    def test_backgrounded_subagent_keeps_the_session_working(self):
        """The main turn settled (inflight 0) but a backgrounded Task subagent is still running: the session is
        still working, not idle. Clears itself when the subagent stops."""
        import asyncio
        s = self._sess()
        s.inflight = 0                                          # main turn already ended
        self.assertEqual(s.snapshot()["state"], "waiting", "no subagents → idles to waiting")
        asyncio.run(s._subagent_start_hook({"agent_id": "a1", "agent_type": "explorer"}, None, None))
        self.assertEqual(s.snapshot()["state"], "working", "a live backgrounded subagent reads 'working'")
        asyncio.run(s._subagent_stop_hook({"agent_id": "a1"}, None, None))
        self.assertEqual(s.snapshot()["state"], "waiting", "back to idle once it stops")

    def test_a_parked_permission_still_wins_over_subagents(self):
        """A live subagent must NOT mask a permission/picker prompt that needs the user — parked wins."""
        import asyncio
        s = self._sess()
        s.inflight = 1
        s.backend._pending_ask[s.sid] = {"kind": "single"}     # parked on a prompt
        asyncio.run(s._subagent_start_hook({"agent_id": "a1", "agent_type": "x"}, None, None))
        sb.append_state(s.backend.state_dir, s.sid, "permission")
        self.assertEqual(s.snapshot()["state"], "permission", "needs-you still surfaces over a running subagent")


class SnapshotParkedOnAsk(unittest.TestCase):
    """A RUNNING SDK session parked in can_use_tool/_ask_user on a permission/picker prompt must snapshot
    as that needs-input state, NOT 'working'. The turn stays inflight through the wait, so the old snapshot
    reported 'working' and the kernel never floored the card to blocked (the user 2026-06-27: an SDK
    AskUserQuestion didn't register as blocked the way tmux's does)."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)
        self.sid = "11111111-2222-3333-4444-555555555555"
        self.s = sb.SdkSession(self.be, {"sid": self.sid, "name": "n", "cwd": "/tmp"})

    def test_inflight_and_not_parked_is_working(self):
        self.s.inflight = 1
        self.assertEqual(self.s.snapshot()["state"], "working", "actively producing → working")

    def test_parked_on_a_picker_reports_picker(self):
        self.s.inflight = 1                                    # turn still in flight (mid-tool)
        sb.append_state(self.d, self.sid, "picker")            # _ask_user logs it before raising the picker
        self.be._pending_ask[self.sid] = {"kind": "single"}   # the ask is up, awaiting the user
        self.assertEqual(self.s.snapshot()["state"], "picker",
                         "parked on an AskUserQuestion picker → needs-input, not working")

    def test_parked_on_a_permission_reports_permission(self):
        self.s.inflight = 1
        sb.append_state(self.d, self.sid, "permission")
        self.be._pending_ask[self.sid] = {"permission": True}
        self.assertEqual(self.s.snapshot()["state"], "permission",
                         "parked on a tool-permission Allow/Deny → needs-input")

    def test_back_to_working_after_the_ask_clears(self):
        self.s.inflight = 1
        sb.append_state(self.d, self.sid, "picker")
        self.be._pending_ask[self.sid] = {"kind": "single"}
        self.be._pending_ask.pop(self.sid, None)              # user answered → _clear_ask
        sb.append_state(self.d, self.sid, "working")          # _ask_user's finally re-logs working
        self.assertEqual(self.s.snapshot()["state"], "working",
                         "ask resolved, turn resumes → working again")


class StateAndRegistryFiles(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def test_state_log_roundtrip(self):
        sb.append_state(self.d, "sid1", "working", t=100)
        sb.append_state(self.d, "sid1", "waiting", t=200)
        self.assertEqual(sb.last_state(self.d, "sid1"), {"t": 200, "state": "waiting"})
        # matches the kernel's format: one JSON object per line
        p = os.path.join(self.d, "states", "sid1.jsonl")
        with open(p) as f:
            self.assertEqual(len(f.read().strip().splitlines()), 2)

    def test_names_file_format(self):
        sb.write_name(self.d, "sid2", "alpha", "/work/dir", "#fff", "black")
        with open(os.path.join(self.d, "names", "sid2")) as f:
            line = f.read().rstrip("\n")
        self.assertEqual(line.split("\t"), ["alpha", "/work/dir", "#fff", "black"])

    def test_registry_roundtrip(self):
        sb.write_reg(self.d, "sid3", {"sid": "sid3", "name": "n", "alive": True})
        self.assertEqual(sb.read_reg(self.d, "sid3")["name"], "n")
        sb.write_reg(self.d, "sid4", {"sid": "sid4", "alive": False})
        regs = {r["sid"]: r for r in sb.list_regs(self.d)}
        self.assertEqual(set(regs), {"sid3", "sid4"})
        self.assertTrue(regs["sid3"]["alive"])

    def test_spawn_assigns_identity_color(self):
        be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)
        sid = be.spawn("c", self.d)
        with open(os.path.join(self.d, "names", sid)) as f:
            parts = f.read().rstrip("\n").split("\t")
        self.assertTrue(parts[2].startswith("#"), "SDK session gets an identity colour like tmux ones")

    def test_dormant_session_reports_waiting_not_stale_inflight(self):
        """False blocked/approval state (the user 2026-06-24): after a kernel restart an alive SDK session's
        thread is gone, but its state log still reads its last in-flight state. A NOT-running session can't be
        mid-turn, so live_sessions must report 'waiting' — else the UI shows it blocked/needs-approval with no
        prompt to resolve (the prompt died with the thread). A running session is unaffected (snapshot path)."""
        be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)
        sid = be.spawn("reorder_like", self.d)            # reg(alive) + a 'waiting' state; NOT started (no thread)
        for stale in ("working", "permission", "picker", "compacting", "retrying"):
            sb.append_state(self.d, sid, stale)           # ...it went mid-turn, then the kernel restarted
            ls = be.live_sessions()                        # registry-only path (session not running here)
            self.assertEqual(ls[sid]["state"], "waiting",
                             "a dormant session must read 'waiting', not the stale '%s'" % stale)

    def test_dormant_session_shows_persisted_live_model(self):
        """A default-model SDK session has no chosen 'model' in its reg, so a dormant/post-restart read showed
        a BLANK model badge — and the timeline hides effort too when model is empty (the user 2026-06-24).
        _learn_model persists the observed model as reg['liveModel']; live_sessions' registry path uses it so
        the badge survives dormancy."""
        be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)
        sid = be.spawn("def_model", self.d)               # reg has effort/mode but NO chosen 'model'
        self.assertEqual(be.live_sessions()[sid]["model"], "", "no model known yet → blank")
        sb.write_reg(self.d, sid, {**sb.read_reg(self.d, sid), "liveModel": "Opus 4.8"})   # as _learn_model persists
        self.assertEqual(be.live_sessions()[sid]["model"], "Opus 4.8",
                         "a dormant session shows the persisted live model, not a blank badge")

    def test_dormant_session_shows_persisted_context(self):
        """Context fill must SURVIVE idle/restart, like the model (the user 2026-06-24: no context bar). The
        backend persists each turn's % as reg['liveCtx']; the registry path surfaces it so a dormant session
        still shows its last context, instead of a blank bar."""
        be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)
        sid = be.spawn("ctxsess", self.d)
        self.assertEqual(be.live_sessions()[sid]["ctx"], "", "no context fill yet → blank")
        sb.write_reg(self.d, sid, {**sb.read_reg(self.d, sid), "liveCtx": 42})   # as a turn persists
        self.assertEqual(be.live_sessions()[sid]["ctx"], 42, "dormant shows the persisted context fill")

    def test_kernel_restart_heals_stale_awaiting(self):
        """A background task's completion is lost on kernel restart: the awaiting:true overlay never gets its
        awaiting:false, because the Stop hook that writes it died with the thread — so the session reads
        working/awaiting forever and climbs a ghost work-timer (reorder_bug 2026-06-24, verified). On
        (re)construction the backend heals every alive, not-running session: a stale awaiting:true →
        awaiting:false. Idempotent — no write when already cleared/absent."""
        sb.write_reg(self.d, "sid_aw", {"sid": "sid_aw", "name": "n", "cwd": "/tmp", "alive": True})
        sb.append_awaiting(self.d, "sid_aw", True, "1 background task(s) running")
        self.assertIs(sb.last_awaiting(self.d, "sid_aw"), True)
        sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)        # kernel restart re-constructs the backend
        self.assertIs(sb.last_awaiting(self.d, "sid_aw"), False,
                      "a dormant session's stale awaiting is cleared on kernel start")
        path = os.path.join(self.d, "states", "sid_aw.jsonl")
        before = len(open(path).read().splitlines())
        sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)        # already false → no redundant write
        self.assertEqual(len(open(path).read().splitlines()), before, "idempotent: no spam when already cleared")

    def test_heal_does_not_touch_a_session_with_no_awaiting(self):
        """The heal writes nothing for a session that never set an awaiting overlay (last_awaiting → None)."""
        sb.write_reg(self.d, "sid_plain", {"sid": "sid_plain", "name": "n", "cwd": "/tmp", "alive": True})
        sb.append_state(self.d, "sid_plain", "waiting")
        before = len(open(os.path.join(self.d, "states", "sid_plain.jsonl")).read().splitlines())
        sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)
        after = len(open(os.path.join(self.d, "states", "sid_plain.jsonl")).read().splitlines())
        self.assertEqual(before, after, "no awaiting overlay → nothing to heal")
        self.assertIsNone(sb.last_awaiting(self.d, "sid_plain"))

    def test_restart_does_NOT_heal_a_stale_working_state(self):
        """A turn in flight when the kernel restarts is killed mid-stream (e.g. the user hit Refresh mid-turn),
        so no ResultMessage ever writes "waiting" — the state log is left at "working". The backend must LEAVE
        that "working" in place: the auto-nudge GENUINE-STOP gate (_last_state_value in _PROGRESSING_STATES)
        then correctly SKIPS the session — it was interrupted, not stopped, and must not be nudged (the user
        2026-06-29: Refresh was nudging in-progress sessions). We used to heal "working"→"waiting" here, which
        opened that gate and caused the spurious nudge; that heal is gone. The dormant in-flight→waiting heal
        is DISPLAY-only and lives in live_sessions, not in the state LOG."""
        sb.write_reg(self.d, "sid_w", {"sid": "sid_w", "name": "n", "cwd": "/tmp", "alive": True})
        sb.append_state(self.d, "sid_w", "working")                     # a turn that never got its ResultMessage
        sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)        # kernel restart re-constructs the backend
        self.assertEqual(sb.last_state(self.d, "sid_w").get("state"), "working",
                         "a refresh-interrupted session keeps 'working' so the auto-nudge stop-gate skips it")

    def test_restart_still_heals_a_stale_awaiting_overlay(self):
        """The awaiting OVERLAY heal stays (a dormant session can't have live background tasks), even though the
        state heal is gone — they're independent. The awaiting heal appends an awaiting-only record, so the
        latest STATE-bearing record (what the kernel's _last_state_value reads, ignoring overlays) must still
        be "working" — never rewritten to "waiting"."""
        import json as _j
        sb.write_reg(self.d, "sid_a", {"sid": "sid_a", "name": "n", "cwd": "/tmp", "alive": True})
        sb.append_state(self.d, "sid_a", "working")
        sb.append_awaiting(self.d, "sid_a", True, "1 background task(s) running")
        sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)
        self.assertEqual(sb.last_awaiting(self.d, "sid_a"), False, "stale awaiting:true is cleared on restart")
        states = []
        with open(os.path.join(self.d, "states", "sid_a.jsonl")) as f:
            for line in f:
                rec = _j.loads(line)
                if isinstance(rec.get("state"), str):
                    states.append(rec["state"])
        self.assertEqual(states[-1], "working", "the latest STATE record is untouched (no 'waiting' heal)")

    def test_new_session_does_not_guess_a_model(self):
        """A brand-new SDK session's model is UNKNOWN until it connects — we DON'T guess it from the fleet (the
        user 2026-06-24: implement the designed way, not heuristics). spawn writes no liveModel; the lane shows
        blank until eager-connect-on-open pulls the real model from get_context_usage()/the init message. A
        peer already knowing its own model must NOT bleed onto the new session's badge."""
        be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)
        s1 = be.spawn("first", self.d)
        sb.write_reg(self.d, s1, {**sb.read_reg(self.d, s1), "liveModel": "Opus 4.8"})   # s1 learned its own model
        s2 = be.spawn("second", self.d)
        self.assertIsNone(sb.read_reg(self.d, s2).get("liveModel"), "no fleet-wide model guess on spawn")
        self.assertEqual(be.live_sessions()[s2]["model"], "", "blank until it connects and reports its own")

    def _last_awaiting(self, sid):
        import json as _j
        rec = None
        with open(os.path.join(self.d, "states", sid + ".jsonl")) as f:
            for line in f:
                o = _j.loads(line)
                if "awaiting" in o:
                    rec = o
        return rec

    def test_awaiting_overlay_shape(self):
        # bugz's reader scans for the latest line with an "awaiting" key (interleaved with state records)
        sb.append_state(self.d, "a1", "working")
        sb.append_awaiting(self.d, "a1", True, "2 background task(s) running")
        rec = self._last_awaiting("a1")
        self.assertEqual(rec["awaiting"], True)
        self.assertEqual(rec["why"], "2 background task(s) running")
        sb.append_awaiting(self.d, "a1", False)
        rec = self._last_awaiting("a1")
        self.assertEqual(rec["awaiting"], False)
        self.assertNotIn("why", rec)               # false clears, no why

    def test_stop_hook_clears_awaiting_ignoring_bg_shell_tasks(self):
        # The Stop hook CLEARS awaiting (false), even with run_in_background SHELL tasks still outstanding
        # (the user 2026-07-07): a leftover backgrounded shell task must not pin an idle session to a
        # working flavor. Only real subagents (the live snapshot) leave a session awaiting, so the Stop
        # hook ignores inp['background_tasks'] and just clears any stale awaiting:true.
        import asyncio
        be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)
        sess = sb.SdkSession(be, {"sid": "h1", "name": "n", "cwd": self.d, "mode": "acceptEdits"})
        asyncio.run(sess._stop_hook({"background_tasks": [{"id": "t1"}, {"id": "t2"}]}, None, None))
        self.assertEqual(self._last_awaiting("h1")["awaiting"], False,
                         "leftover run_in_background shell tasks do NOT make the session awaiting")
        asyncio.run(sess._stop_hook({"background_tasks": []}, None, None))   # nothing outstanding → still cleared
        self.assertEqual(self._last_awaiting("h1")["awaiting"], False)


class SetModelModePure(unittest.TestCase):
    """set_model / set_mode persist to the registry even with no live session thread (CI-safe,
    no SDK). The live control-channel apply is covered by AskRoundTrip.test_set_model_and_mode_apply_live."""
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)

    def test_set_model_persists_to_registry(self):
        sid = self.be.spawn("m", self.d)                  # writes reg; no session thread until send()
        self.assertTrue(self.be.set_model(sid, "opus"))
        self.assertEqual(sb.read_reg(self.d, sid)["model"], "opus")
        self.assertFalse(self.be.set_model("no-such-sid", "opus"))

    def test_set_model_on_a_dormant_session_resolves_the_badge_not_stale(self):
        # the user 2026-07-03: set_model stamped the chosen alias but left reg.liveModel stale, and
        # model_label PREFERS liveModel → the badge kept the OLD name (track: chose fable, showed Opus 4.8).
        # A dormant session (no live thread, no turn coming) resolves to the chosen alias's label NOW —
        # never stale, never trapped on switching-dots.
        sid = self.be.spawn("m", self.d)
        sb.write_reg(self.d, sid, {**sb.read_reg(self.d, sid), "liveModel": "Opus 4.8"})   # a stale prior live name
        self.assertTrue(self.be.set_model(sid, "fable"))
        reg = sb.read_reg(self.d, sid)
        # a bare alias has no version until the real name lands, so the best-effort label is "Fable" — the
        # point is it reflects the PICK (not the stale "Opus 4.8"); the real "Fable 5" fills in on next connect.
        self.assertEqual(reg["liveModel"], "Fable", "the dormant badge reflects the pick, not the stale prior")
        self.assertFalse(reg.get("modelPending"), "nothing is coming to resolve dots → resolve immediately, no trap")
        self.assertEqual(sb.model_label(reg["liveModel"], reg["model"]), "Fable")

    def test_learn_model_persists_the_raw_id_beside_the_pretty_name(self):
        # the pickers' version lists are seeded from a table and COMPLETED from what the CLI actually
        # reports (the authoritative source for what it serves) — that needs the raw id, not just
        # the badge text, persisted where the kernel reads regs (liveModelId)
        sid = self.be.spawn("m", self.d)
        sess = sb.SdkSession(self.be, sb.read_reg(self.d, sid))
        sess._learn_model("Fable 5.1", raw="claude-fable-5-1")
        reg = sb.read_reg(self.d, sid)
        self.assertEqual((reg["liveModel"], reg["liveModelId"]), ("Fable 5.1", "claude-fable-5-1"))
        # a pre-fix reg knows the NAME but not the id: the first report of an unchanged name still
        # lands the id (otherwise a long-running session would never contribute its version)
        sid2 = self.be.spawn("n", self.d)
        sb.write_reg(self.d, sid2, {**sb.read_reg(self.d, sid2), "liveModel": "Fable 5"})
        sess2 = sb.SdkSession(self.be, sb.read_reg(self.d, sid2))
        self.assertEqual(sess2.model, "Fable 5")
        sess2._learn_model("Fable 5", raw="claude-fable-5")
        self.assertEqual(sb.read_reg(self.d, sid2)["liveModelId"], "claude-fable-5")
        # the seeded id survives construction, so an unchanged report writes nothing new
        sess3 = sb.SdkSession(self.be, sb.read_reg(self.d, sid2))
        self.assertEqual(sess3._model_id, "claude-fable-5")

    def test_refresh_context_persists_the_live_model_id(self):
        # _do_refresh_context is the pre-turn source (get_context_usage answers on connect, before any
        # init message), so an eager-connected session that never runs a turn still contributes its
        # version to the pickers
        sid = self.be.spawn("m", self.d)
        sess = sb.SdkSession(self.be, sb.read_reg(self.d, sid))

        class _Client:
            async def get_context_usage(self):
                return {"percentage": 41.6, "model": "claude-fable-5-1"}
        sess.client = _Client()
        asyncio.run(sess._do_refresh_context())
        reg = sb.read_reg(self.d, sid)
        self.assertEqual((reg["liveModelId"], reg["liveModel"], reg["liveCtx"]), ("claude-fable-5-1", "Fable 5.1", 42))
        self.assertEqual(sess._model_id, "claude-fable-5-1")

        # a [1m] variant is persisted as reported — the kernel's picker strips the tag on read
        class _Client1m:
            async def get_context_usage(self):
                return {"percentage": 41.6, "model": "claude-fable-5-1[1m]"}
        sess.client = _Client1m()
        asyncio.run(sess._do_refresh_context())
        self.assertEqual(sb.read_reg(self.d, sid)["liveModelId"], "claude-fable-5-1[1m]")

    def test_alias_label_and_model_reflects_alias(self):
        self.assertEqual(sb._alias_label("opus"), "Opus")
        self.assertEqual(sb._alias_label("claude-opus-4-8"), "Opus 4.8")
        self.assertEqual(sb._alias_label("default"), "")
        self.assertEqual(sb._alias_label(""), "")
        self.assertTrue(sb._model_reflects_alias("Opus 4.8", "opus"), "the bare alias is a substring of the pretty name")
        self.assertTrue(sb._model_reflects_alias("Fable 5", "fable"))
        self.assertTrue(sb._model_reflects_alias("Opus 4.8", "claude-opus-4-8"), "a full id alias matches on its family word")
        self.assertFalse(sb._model_reflects_alias("Fable 5", "opus"), "the OLD name does not reflect the new pick")
        self.assertTrue(sb._model_reflects_alias("anything", "default"), "default matches the resolved name")
        self.assertFalse(sb._model_reflects_alias("", "opus"), "no live name yet → not resolved")

    def test_a_context_tagged_pick_resolves_its_pending_switch(self):
        # "/model fable[1m]" — the CLI's 1M-context spelling — routes through the setter, but the literal
        # "fable[1m]" is never a substring of the pretty live name "Fable 5.1", so the switching-dots
        # stuck until the thread died. The check reads through the tag.
        self.assertTrue(sb._model_reflects_alias("Fable 5.1", "fable[1m]"))
        self.assertTrue(sb._model_reflects_alias("Opus 4.8", "claude-opus-4-8[1m]"))
        self.assertFalse(sb._model_reflects_alias("Fable 5.1", "opus[1m]"), "still the family that must match")
        sess = sb.SdkSession(self.be, {"sid": "q", "name": "n", "cwd": self.d, "model": "fable[1m]"})
        sess.model = "Opus 4.8"
        sess._model_pending = "fable[1m]"
        sess._learn_model("Fable 5.1", raw="claude-fable-5-1[1m]")
        self.assertEqual(sess._model_pending, "", "the new name clears the tagged switch — dots stop")

    def test_a_refused_set_model_reverts_every_layer_and_warns(self):
        # set_model PERSISTED before the CLI accepted — sdk-defaults.json (the seed for every future
        # session), the reg (the reconnect's --model) and chosen_model — and a refusal only LOGGED,
        # unlike _do_set_mode, which reverts every layer. A well-formed id the CLI's catalog rejects
        # poisoned all three. The refusal now restores what was there and rings the problems.
        sid = self.be.spawn("m", self.d)
        self.assertTrue(self.be.set_model(sid, "opus"))                      # the prior, accepted pick
        sess = sb.SdkSession(self.be, sb.read_reg(self.d, sid))
        sess.model = "Opus 4.8"
        self.be.sessions[sid] = sess

        class _RefusingClient:
            async def set_model(self, model=None):
                raise Exception("Unknown model: %s" % model)   # the SDK's shape for a CLI error response (_cli_refusal)

            async def get_context_usage(self):
                return {"percentage": 3, "model": "claude-opus-4-8"}       # the CLI stayed where it was
        sess.client = _RefusingClient()
        scheduled = []
        sess.set_model_live = lambda model, prev=None: scheduled.append((model, prev))   # the loop hop, stubbed
        # a well-formed id of a known family that the CLI's catalog rejects (another family than the
        # live one, so the switch is genuinely pending until the CLI answers)
        self.assertTrue(self.be.set_model(sid, "claude-fable-9-9"))
        self.assertEqual(sb.read_reg(self.d, sid)["model"], "claude-fable-9-9", "accepted optimistically, as before")
        self.assertEqual(sess._model_pending, "claude-fable-9-9")
        self.assertEqual(len(scheduled), 1)
        asyncio.run(sess._do_set_model(*scheduled[0]))
        reg = sb.read_reg(self.d, sid)
        self.assertEqual(reg["model"], "opus", "the reg — the reconnect's --model — is back to the accepted pick")
        self.assertEqual(sb.read_sdk_defaults(self.d).get("model"), "opus", "the seed for future sessions too")
        self.assertEqual(sess.chosen_model, "opus")
        self.assertEqual(sess._model_pending, "", "nothing is coming to resolve dots for a refused switch")
        self.assertFalse(reg.get("modelPending"))
        probs = [p["text"] for p in self.be.problems()]
        self.assertEqual(len(probs), 1, "loud: the refusal rings the problems, the mode path's idiom")
        self.assertIn("claude-fable-9-9", probs[0])
        self.assertIn("did NOT apply", probs[0])
        self.assertIn("opus", probs[0].rsplit("reverted", 1)[-1], "and names what it reverted to")

    def test_a_refused_set_model_with_no_prior_pick_leaves_no_residue(self):
        # the prior state may be ABSENT (a session on the account default, no remembered model):
        # the revert removes the keys it wrote rather than parking a null or the refused value
        sid = self.be.spawn("m", self.d)
        self.assertNotIn("model", sb.read_reg(self.d, sid))
        self.assertNotIn("model", sb.read_sdk_defaults(self.d))
        sess = sb.SdkSession(self.be, sb.read_reg(self.d, sid))
        self.be.sessions[sid] = sess

        class _RefusingClient:
            async def set_model(self, model=None):
                raise Exception("Unknown model: %s" % model)

            async def get_context_usage(self):
                return {"percentage": 3, "model": "claude-fable-5-1"}
        sess.client = _RefusingClient()
        scheduled = []
        sess.set_model_live = lambda model, prev=None: scheduled.append((model, prev))
        self.assertTrue(self.be.set_model(sid, "claude-fable-9-9"))
        asyncio.run(sess._do_set_model(*scheduled[0]))
        self.assertNotIn("model", sb.read_reg(self.d, sid), "no pick before → no pick after")
        self.assertNotIn("model", sb.read_sdk_defaults(self.d))
        self.assertEqual(sess.chosen_model, "")
        self.assertEqual(sb.read_reg(self.d, sid)["liveModel"], "Fable 5.1", "the badge shows what the CLI runs")

    # ── refusal vs no-answer ──────────────────────────────────────────────────────────────────────
    # The installed SDK (claude_agent_sdk 0.2.132, _internal/query.py) raises a BARE Exception for two
    # different worlds: the CLI ANSWERED a control request with an error (`Exception(response["error"])`,
    # built from the control_response frame — no cause), and the answer NEVER CAME (`Exception("Control
    # request timeout: set_model") from TimeoutError` after fail_after; Query.close() cancels the reader
    # without resolving pending requests, so a request stranded by a reconnect teardown ends the same
    # way). A reader that dies re-raises ITS OWN typed error into every pending request; a disconnected
    # client raises CLIConnectionError. Verified by probe against the installed package. The fakes below
    # reproduce those exact shapes.

    def _live(self, prior="opus", live="Opus 4.8"):
        sid = self.be.spawn("m", self.d)
        if prior:
            self.assertTrue(self.be.set_model(sid, prior))
        sess = sb.SdkSession(self.be, sb.read_reg(self.d, sid))
        sess.model = live
        self.be.sessions[sid] = sess
        scheduled = []
        sess.set_model_live = lambda model, prev=None: scheduled.append((model, prev))
        return sid, sess, scheduled

    def test_the_refusal_discriminator_matches_the_installed_sdks_shapes(self):
        refusal = Exception("Unknown model: claude-fable-9-9")                 # control_response subtype=error
        self.assertTrue(sb._cli_refusal(refusal))
        self.assertTrue(sb._cli_refusal(Exception("Unknown error")), "the SDK's default text when the CLI's error is empty")
        try:
            raise Exception("Control request timeout: set_model") from TimeoutError()   # fail_after expired / stranded
        except Exception as e:
            self.assertFalse(sb._cli_refusal(e), "a timeout is no answer")
        self.assertFalse(sb._cli_refusal(Exception("Control request timeout: set_model")),
                         "…even read without its cause: the prefix alone says no answer")

        class ProcessError(Exception):                                          # a typed SDK error the dying reader
            pass                                                                # fans out to pending requests
        self.assertFalse(sb._cli_refusal(ProcessError("exit 1")), "a reader death is no answer")
        self.assertFalse(sb._cli_refusal(RuntimeError("stream broke")))

    def test_a_lost_answer_is_not_a_refusal_the_pick_stands_and_nothing_rings(self):
        # the reproduced strand: a model AND an effort picked while the session worked, both parked,
        # replayed back-to-back at turn end — set_model's control request went to the OLD CLI and
        # set_effort's reconnect tore that client down with the answer unread. The NEW connection came
        # up with --model <new> (chosen_model rides _options) and ran it; 60s later the stranded request
        # timed out and a revert flipped chosen_model, the reg and sdk-defaults back to the PREVIOUS
        # model while the CLI ran the new one — the registry/argv divergence this change exists to
        # close, re-minted, plus a false "did NOT apply" problem and, for a cheaper prev, a false
        # model-fallback card at the next reconnect.
        sid, sess, scheduled = self._live()
        logs = []
        self.be._log_cb = logs.append

        class _NeverAnswers:
            async def set_model(self, model=None):
                raise Exception("Control request timeout: set_model") from TimeoutError()

            async def get_context_usage(self):
                return {"percentage": 3, "model": "claude-fable-5-1"}    # the reconnect runs the pick
        sess.client = _NeverAnswers()
        self.assertTrue(self.be.set_model(sid, "fable"))
        asyncio.run(sess._do_set_model(*scheduled[0]))
        self.assertEqual(sess.chosen_model, "fable", "the pick stands — the next connect's _options asserts it")
        self.assertEqual(sb.read_reg(self.d, sid)["model"], "fable", "the reg (the reconnect's --model) keeps the pick")
        self.assertEqual(sb.read_sdk_defaults(self.d).get("model"), "fable", "so does the seed for future sessions")
        self.assertEqual(self.be.problems(), [], "a lost answer is not a failed switch — nothing rings")
        lost = [m for m in logs if "set_model" in m and "fable" in m]
        self.assertEqual(len(lost), 1, "one line says the answer was lost")
        self.assertNotIn("refused", lost[0])
        self.assertNotIn("did NOT apply", lost[0])
        self.assertIn("lost", lost[0])
        # the same for a client that was already disconnected when the request was made (the SDK's
        # typed CLIConnectionError), and for a reader death fanned out to the pending request
        for exc in (type("CLIConnectionError", (Exception,), {})("Not connected. Call connect() first."),
                    type("ProcessError", (Exception,), {})("Command failed with exit code 1")):
            sid2, sess2, sched2 = self._live()

            class _Typed:
                async def set_model(self, model=None, _e=exc):
                    raise _e

                async def get_context_usage(self):
                    return {"percentage": 3, "model": "claude-sonnet-4-6"}
            sess2.client = _Typed()
            self.assertTrue(self.be.set_model(sid2, "sonnet"))
            asyncio.run(sess2._do_set_model(*sched2[0]))
            self.assertEqual(sess2.chosen_model, "sonnet", type(exc).__name__)
            self.assertEqual(sb.read_reg(self.d, sid2)["model"], "sonnet", type(exc).__name__)
        self.assertEqual(self.be.problems(), [])

    def test_a_refusal_landing_after_a_newer_pick_stands_down_entirely(self):
        # same session, A then B: A's control request answers late with the CLI's error AFTER B was
        # accepted. A revert that wrote A's captured snapshots back unconditionally rolled the ACCEPTED
        # pick B back to the pre-A model in every layer while the CLI ran B. A writer whose evidence
        # predates the diary stands down.
        sid, sess, scheduled = self._live()

        class _Client:
            def __init__(self):
                self.b_done = asyncio.Event()
                self.accepted = None

            async def set_model(self, model=None):
                if model == "claude-fable-9-9":          # pick A — the CLI answers with an error, late
                    await self.b_done.wait()
                    raise Exception("Unknown model: %s" % model)
                self.accepted = model                    # pick B — accepted at once
                self.b_done.set()

            async def get_context_usage(self):
                return {"percentage": 3, "model": "claude-sonnet-4-6"}
        self.assertTrue(self.be.set_model(sid, "claude-fable-9-9"))     # A: prev = opus
        self.assertTrue(self.be.set_model(sid, "sonnet"))               # B: prev = A
        self.assertEqual(sb.read_reg(self.d, sid)["model"], "sonnet")

        async def drive():
            cl = _Client()
            sess.client = cl
            ta = asyncio.ensure_future(sess._do_set_model(*scheduled[0]))   # one task per pick, as set_model_live does
            tb = asyncio.ensure_future(sess._do_set_model(*scheduled[1]))
            await asyncio.gather(ta, tb)
            return cl
        cl = asyncio.run(drive())
        self.assertEqual(cl.accepted, "sonnet")
        self.assertEqual(sess.chosen_model, "sonnet", "B stands: the late refusal of A owns nothing any more")
        self.assertEqual(sb.read_reg(self.d, sid)["model"], "sonnet")
        self.assertEqual(sb.read_sdk_defaults(self.d).get("model"), "sonnet")
        self.assertEqual(self.be.problems(), [], "a superseded refusal is not the user's problem — B applied")

    def test_a_revert_leaves_a_layer_a_newer_writer_holds(self):
        # the cross-session twin: sdk-defaults.json is SHARED. S1 picks X (later refused); S2 — dormant,
        # no CLI to refuse — picks Y, which lands in the defaults as every set_model does. X's refusal
        # must not restore S1's captured default over Y. Each layer reverts only while it still holds
        # the refused value (compare-and-swap).
        s1, sess1, sched1 = self._live()
        s2 = self.be.spawn("two", self.d)
        self.assertTrue(self.be.set_model(s1, "claude-fable-9-9"))     # X: captures default = opus
        self.assertTrue(self.be.set_model(s2, "haiku"))                # Y: defaults.model = haiku
        self.assertEqual(sb.read_sdk_defaults(self.d).get("model"), "haiku")

        class _Refusing:
            async def set_model(self, model=None):
                raise Exception("Unknown model: %s" % model)

            async def get_context_usage(self):
                return {"percentage": 3, "model": "claude-opus-4-8"}
        sess1.client = _Refusing()
        asyncio.run(sess1._do_set_model(*sched1[0]))
        self.assertEqual(sess1.chosen_model, "opus", "S1's own layers revert — they still held X")
        self.assertEqual(sb.read_reg(self.d, s1)["model"], "opus")
        self.assertEqual(sb.read_sdk_defaults(self.d).get("model"), "haiku", "S2's newer default survives")
        self.assertEqual(sb.read_reg(self.d, s2)["model"], "haiku")
        self.assertEqual(len(self.be.problems()), 1, "S1's refusal is still loud")

    def test_a_refusal_tells_the_kernel_to_forget_the_pick_superseded_or_not_a_lost_answer_does_not(self):
        """The kernel records a version as its family's pin BEFORE the CLI rules (_set_model_or_park →
        _note_model_pick), and the revert never reached that memory: after a refusal the family row kept
        sending the refused id, re-ringing the problem on every click. The backend tells the kernel through
        a class-level hook, the on_model_fallback idiom — on a VERDICT.

        A SUPERSEDED refusal forgets too: the newer pick owns chosen_model and the reg, but the pin the
        kernel recorded for the REFUSED id is its own — a pick in another family, or the same family's
        pin when the newer pick is an alias — and the CLI did rule on it. Left in place, a family click
        re-sent the refused id. Firing the hook is safe for the newer pick because the kernel's forget
        compares-and-swaps by value (_forget_model_pick(fam, only=id)): a newer pin for the same family
        is never this refusal's to drop (test_model_versions pins that side). A LOST answer forgets
        nothing — it says nothing about the id."""
        calls = []
        type(self.be).on_model_refused = staticmethod(lambda sid, value: calls.append((sid, value)))
        try:
            sid, sess, scheduled = self._live()

            class _Refusing:
                async def set_model(self, model=None):
                    raise Exception("Unknown model: %s" % model)

                async def get_context_usage(self):
                    return {"percentage": 3, "model": "claude-opus-4-8"}
            sess.client = _Refusing()
            self.assertTrue(self.be.set_model(sid, "claude-fable-9-9"))
            asyncio.run(sess._do_set_model(*scheduled[0]))
            self.assertEqual(calls, [(sid, "claude-fable-9-9")], "the refused id, as the kernel recorded it")
            # a lost answer: no call
            sid2, sess2, sched2 = self._live()

            class _Lost:
                async def set_model(self, model=None):
                    raise Exception("Control request timeout: set_model") from TimeoutError()

                async def get_context_usage(self):
                    return {"percentage": 3, "model": "claude-fable-5-1"}
            sess2.client = _Lost()
            self.assertTrue(self.be.set_model(sid2, "claude-fable-5-1"))
            asyncio.run(sess2._do_set_model(*sched2[0]))
            self.assertEqual(len(calls), 1, "a lost answer forgets nothing")
            # a superseded refusal: the CLI ruled on the id, so its pin goes too — the newer pick (another
            # family here) recorded its own pin, which this forget cannot reach (CAS by value, kernel side)
            sid3, sess3, sched3 = self._live()
            sess3.client = _Refusing()
            rang = len(self.be.problems())
            self.assertTrue(self.be.set_model(sid3, "claude-fable-9-9"))
            self.assertTrue(self.be.set_model(sid3, "claude-sonnet-4-6"))
            asyncio.run(sess3._do_set_model(*sched3[0]))
            self.assertEqual(calls[1:], [(sid3, "claude-fable-9-9")], "a superseded refusal forgets the refused id")
            self.assertEqual(sess3.chosen_model, "claude-sonnet-4-6", "…and touches nothing the newer pick owns")
            self.assertEqual(sb.read_reg(self.d, sid3)["model"], "claude-sonnet-4-6")
            self.assertEqual(len(self.be.problems()), rang, "and rings nothing — the user already picked again")
        finally:
            del type(self.be).on_model_refused

    def test_a_superseded_write_whose_answer_was_lost_forgets_nothing_and_drops_its_node(self):
        # superseded is computed from chosen_model alone — so a superseded write whose answer was LOST
        # (a timeout, a request stranded by a reconnect teardown) must not forget the user's pin for it:
        # a lost answer says nothing about the id. The hook fires on a refusal alone. The superseded lost
        # write's node goes the way a settled write's does (dropped ≡ settled, the dead-thread rule): the
        # store keeps the newer pick, and the newer pick's own unwind lands on this write — a lost pick
        # stands, it was never refused.
        calls = []
        type(self.be).on_model_refused = staticmethod(lambda sid, value: calls.append((sid, value)))
        try:
            sid, sess, sched = self._live()                                     # accepted: opus

            class _LostThenRefuses:
                async def set_model(self, model=None):
                    if model == "claude-fable-9-9":
                        raise Exception("Control request timeout: set_model") from TimeoutError()
                    raise Exception("Unknown model: %s" % model)

                async def get_context_usage(self):
                    return {"percentage": 3, "model": "claude-opus-4-8"}
            sess.client = _LostThenRefuses()
            self.assertTrue(self.be.set_model(sid, "claude-fable-9-9"))         # A: a version pin
            self.assertTrue(self.be.set_model(sid, "claude-sonnet-4-6"))        # B: the newer pick
            rang = len(self.be.problems())
            asyncio.run(sess._do_set_model(*sched[0]))                         # A's answer: lost, superseded by B
            self.assertEqual(calls, [], "a lost answer forgets nothing, superseded or not")
            self.assertEqual(sess.chosen_model, "claude-sonnet-4-6", "the newer pick owns the session's layers")
            self.assertEqual(sb.read_reg(self.d, sid)["model"], "claude-sonnet-4-6")
            self.assertEqual(sb.read_sdk_defaults(self.d).get("model"), "claude-sonnet-4-6", "the store keeps the newer write")
            self.assertEqual(len(self.be.problems()), rang, "and rings nothing — the user already picked again")
            nodes = {n["value"]: n for n in self.be._seed_writes.values()}
            self.assertEqual(set(nodes), {"claude-sonnet-4-6"}, "A's node is dropped; B's stays pending")
            self.assertEqual(nodes["claude-sonnet-4-6"]["prior"], "claude-fable-9-9",
                             "B still points at A's write — lost, not refused, so it is what B unwinds onto")
            asyncio.run(sess._do_set_model(*sched[1]))                         # B refused — the head
            self.assertEqual(calls, [(sid, "claude-sonnet-4-6")], "B's refusal is a verdict: it forgets B alone")
            self.assertEqual(sb.read_sdk_defaults(self.d).get("model"), "claude-fable-9-9")
            self.assertEqual(sess.chosen_model, "opus", "the session's own layers go back to the last ACCEPTED model")
            self.assertEqual(self.be._seed_writes, {})
        finally:
            del type(self.be).on_model_refused

    # ── the revert target is the last ACCEPTED state ──────────────────────────────────────────────
    class _RefusesAll:
        """A CLI that answers every set_model with an error and keeps running Opus 4.8."""
        async def set_model(self, model=None):
            raise Exception("Unknown model: %s" % model)

        async def get_context_usage(self):
            return {"percentage": 3, "model": "claude-opus-4-8"}

    def test_two_refusals_in_a_row_restore_the_accepted_model_never_the_first_refused_pick(self):
        # A then B, BOTH refused. A's answer lands after B's optimistic writes and stands down
        # (superseded) — right. But B's snapshot was captured AFTER A's writes, so it held A, and a
        # revert to "what the write replaced" would compare-and-swap A — a REFUSED id — back into
        # chosen_model, the reg and the shared defaults: the poison the revert exists to remove,
        # embedded by the revert. The revert restores the last state the CLI ACCEPTED (opus, before
        # either pick), never the last state WRITTEN. First with NO accepted pick anywhere (a fresh
        # store, a session on the account default): every layer returns to ABSENCE, never to A.
        sid0, sess0, sched0 = self._live(prior="")
        self.assertNotIn("model", sb.read_reg(self.d, sid0))
        sess0.client = self._RefusesAll()
        self.assertTrue(self.be.set_model(sid0, "claude-fable-9-9"))        # A
        self.assertTrue(self.be.set_model(sid0, "claude-sonnet-9-9"))       # B, written over A

        async def drive0():
            await asyncio.gather(sess0._do_set_model(*sched0[0]), sess0._do_set_model(*sched0[1]))
        asyncio.run(drive0())
        self.assertEqual(sess0.chosen_model, "")
        self.assertNotIn("model", sb.read_reg(self.d, sid0), "no accepted pick before → none after")
        self.assertNotIn("model", sb.read_sdk_defaults(self.d))
        self.assertEqual(len(self.be.problems()), 1, "B's refusal rings once; A's stood down")
        # then with an accepted pick before A (opus, set while the session was dormant — the connect asserts
        # it): every layer returns to opus
        sid, sess, scheduled = self._live()                                 # accepted: opus
        sess.client = self._RefusesAll()
        self.assertTrue(self.be.set_model(sid, "claude-fable-9-9"))         # A
        self.assertTrue(self.be.set_model(sid, "claude-sonnet-9-9"))        # B, written over A
        self.assertEqual(sb.read_reg(self.d, sid)["model"], "claude-sonnet-9-9")

        async def drive():
            await asyncio.gather(sess._do_set_model(*scheduled[0]), sess._do_set_model(*scheduled[1]))
        asyncio.run(drive())
        self.assertEqual(sess.chosen_model, "opus", "not A — a refused id is never a revert target")
        self.assertEqual(sb.read_reg(self.d, sid)["model"], "opus")
        self.assertEqual(sb.read_sdk_defaults(self.d).get("model"), "opus")
        self.assertFalse(sb.read_reg(self.d, sid).get("modelPending"))
        probs = [p["text"] for p in self.be.problems()]
        self.assertEqual(len(probs), 2, "one ring per session — B's refusal; A's stood down")
        self.assertIn("opus", probs[1].rsplit("reverted", 1)[-1], "and names the ACCEPTED model it went back to")

    def test_a_late_acceptance_becomes_the_revert_target_of_the_pick_after_it(self):
        # the accepted state moves on ACCEPTANCE, whenever it lands: A accepted after B was already
        # written, then B refused → B reverts to A (the CLI runs A), not to the pre-A model
        sid, sess, scheduled = self._live()                                 # accepted: opus

        class _Client:
            async def set_model(self, model=None):
                if model != "claude-fable-5-1":
                    raise Exception("Unknown model: %s" % model)         # B refused; A accepted

            async def get_context_usage(self):
                return {"percentage": 3, "model": "claude-fable-5-1"}
        sess.client = _Client()
        self.assertTrue(self.be.set_model(sid, "claude-fable-5-1"))         # A
        self.assertTrue(self.be.set_model(sid, "claude-sonnet-9-9"))        # B

        async def drive():
            await asyncio.gather(sess._do_set_model(*scheduled[0]), sess._do_set_model(*scheduled[1]))
        asyncio.run(drive())
        self.assertEqual(sess.chosen_model, "claude-fable-5-1")
        self.assertEqual(sb.read_reg(self.d, sid)["model"], "claude-fable-5-1")
        self.assertEqual(sb.read_sdk_defaults(self.d).get("model"), "claude-fable-5-1")

    def test_a_connect_asserts_the_pick_whose_answer_died_with_its_thread(self):
        # a pick written optimistically whose control request never resolved (the thread died) is what
        # the NEXT connect launches with (--model rides _options); the CLI's init reporting it is the
        # acceptance — so a later refused pick reverts to IT, not to the model accepted before it
        sid, sess, scheduled = self._live()                                 # accepted: opus
        self.assertTrue(self.be.set_model(sid, "claude-fable-5-1"))         # A — never driven: its task died

        class _Sys:
            def __init__(self, data): self.subtype = "init"; self.data = data

        async def _noop(): pass
        sess._do_refresh_context = _noop

        async def connect():
            sess._on_message(_Sys({"model": "claude-fable-5-1"}), _AssistantMessage, _ResultMessage, _Sys)
            await asyncio.sleep(0)
        asyncio.run(connect())
        sess.client = self._RefusesAll()
        self.assertTrue(self.be.set_model(sid, "claude-sonnet-9-9"))        # B, refused
        asyncio.run(sess._do_set_model(*scheduled[1]))
        self.assertEqual(sess.chosen_model, "claude-fable-5-1", "the connect made A the accepted model")
        self.assertEqual(sb.read_reg(self.d, sid)["model"], "claude-fable-5-1")
        self.assertEqual(sb.read_sdk_defaults(self.d).get("model"), "claude-fable-5-1")

    # ── the SHARED defaults are ruled per write, by token ─────────────────────────────────────────
    # sdk-defaults.json is one store for every session. Deciding "is the value in it still my write?" by
    # VALUE from a per-session picture of the layer is wrong three ways, each reproduced below; the store
    # carries the identity of the write that set it (`modelTok`), and a refusal unwinds exactly its own write.
    class _AcceptsAll:
        """A CLI that accepts every set_model and reports the picked model."""
        def __init__(self, live="claude-sonnet-5-2"):
            self.live = live

        async def set_model(self, model=None):
            return None

        async def get_context_usage(self):
            return {"percentage": 3, "model": self.live}

    def test_picking_the_value_the_shared_default_already_holds_then_being_refused_leaves_it_in_place(self):
        # The most common pick of all: the value another session's ACCEPTED pick left in the shared
        # defaults — a new session seeds from it, and picking it again is one click. A by-value scheme
        # cannot adopt it as the baseline (the value is in this session's own unaccepted set the moment
        # it is picked), so the refusal restores a STALE baseline over the other session's pick.
        sid, sess, sched = self._live()                                    # accepted opus; defaults = opus
        other = self.be.spawn("two", self.d)
        self.assertTrue(self.be.set_model(other, "claude-sonnet-5-2"))     # dormant: accepted where it stands
        self.assertEqual(sb.read_sdk_defaults(self.d)["model"], "claude-sonnet-5-2")
        sess.client = self._RefusesAll()
        self.assertTrue(self.be.set_model(sid, "claude-sonnet-5-2"))       # the SAME value; this CLI refuses it
        asyncio.run(sess._do_set_model(*sched[-1]))
        self.assertEqual(sb.read_sdk_defaults(self.d).get("model"), "claude-sonnet-5-2",
                         "the other session's accepted pick stays the seed")
        self.assertEqual(sb.read_reg(self.d, sid)["model"], "opus", "this session's own layers revert")
        self.assertEqual(sess.chosen_model, "opus")
        self.assertEqual(sb.read_reg(self.d, other)["model"], "claude-sonnet-5-2")
        # the same with the other session LIVE and its CLI accepting — its accepted pick, literally
        s3, sess3, sched3 = self._live()
        s4, sess4, sched4 = self._live()
        sess4.client = self._AcceptsAll()
        self.assertTrue(self.be.set_model(s4, "claude-sonnet-5-2"))
        asyncio.run(sess4._do_set_model(*sched4[-1]))                      # accepted
        sess3.client = self._RefusesAll()
        self.assertTrue(self.be.set_model(s3, "claude-sonnet-5-2"))
        asyncio.run(sess3._do_set_model(*sched3[-1]))                      # refused
        self.assertEqual(sb.read_sdk_defaults(self.d).get("model"), "claude-sonnet-5-2")
        self.assertEqual(sb.read_reg(self.d, s3)["model"], "opus")
        self.assertEqual(sb.read_reg(self.d, s4)["model"], "claude-sonnet-5-2")

    def test_an_id_this_session_once_refused_stays_when_another_session_has_since_accepted_it(self):
        # a by-value scheme keeps a refused id in the session's unaccepted set FOREVER, so the shared
        # default holding it — put there later by another session whose CLI accepted it (a newer CLI,
        # another account) — can never be adopted as a baseline, and this session's next refusal restores
        # its own stale baseline over that accepted pick
        sid, sess, sched = self._live()                                    # accepted opus
        sess.client = self._RefusesAll()
        self.assertTrue(self.be.set_model(sid, "claude-fable-9-9"))        # X, refused here
        asyncio.run(sess._do_set_model(*sched[-1]))
        self.assertEqual(sb.read_sdk_defaults(self.d).get("model"), "opus")
        other, sess2, sched2 = self._live()
        sess2.client = self._AcceptsAll("claude-fable-9-9")
        self.assertTrue(self.be.set_model(other, "claude-fable-9-9"))      # X again, on a CLI that takes it
        asyncio.run(sess2._do_set_model(*sched2[-1]))
        self.assertEqual(sb.read_sdk_defaults(self.d).get("model"), "claude-fable-9-9")
        self.assertTrue(self.be.set_model(sid, "claude-sonnet-9-9"))       # Y, refused
        asyncio.run(sess._do_set_model(*sched[-1]))
        self.assertEqual(sb.read_sdk_defaults(self.d).get("model"), "claude-fable-9-9",
                         "the other session's accepted X stands; this session's old refusal is not evidence")
        self.assertEqual(sb.read_reg(self.d, sid)["model"], "opus")

    def test_two_cross_session_refusals_never_seed_a_refused_id_in_either_order(self):
        # Two live sessions pick concurrently: b's write lands on a's PENDING one. A by-value scheme
        # adopts a's pending value as b's baseline (it is not in b's own unaccepted set), so when both
        # are refused — a first, whose compare-and-swap stands down because b holds the store — b's
        # revert restores a's REFUSED id as the seed every new session launches with.
        a, sa, qa = self._live()
        b, sb_, qb = self._live()
        sa.client = sb_.client = self._RefusesAll()
        self.assertTrue(self.be.set_model(a, "claude-fable-9-9"))          # Va, pending
        self.assertTrue(self.be.set_model(b, "claude-sonnet-9-9"))         # Vb on top of it
        asyncio.run(sa._do_set_model(*qa[-1]))                             # Va refused — not the head: spliced out
        self.assertEqual(sb.read_sdk_defaults(self.d).get("model"), "claude-sonnet-9-9", "b's write still pending")
        asyncio.run(sb_._do_set_model(*qb[-1]))                            # Vb refused — head: back past Va
        self.assertEqual(sb.read_sdk_defaults(self.d).get("model"), "opus", "neither refused id is the seed")
        self.assertEqual((sb.read_reg(self.d, a)["model"], sb.read_reg(self.d, b)["model"]), ("opus", "opus"))
        # the other order: b's refusal first unwinds onto a's pending Va (honest — a's verdict is still out),
        # then a's refusal takes it back to opus
        self.assertTrue(self.be.set_model(a, "claude-fable-9-9"))
        self.assertTrue(self.be.set_model(b, "claude-sonnet-9-9"))
        asyncio.run(sb_._do_set_model(*qb[-1]))
        self.assertEqual(sb.read_sdk_defaults(self.d).get("model"), "claude-fable-9-9", "a's write, still pending")
        asyncio.run(sa._do_set_model(*qa[-1]))
        self.assertEqual(sb.read_sdk_defaults(self.d).get("model"), "opus")
        self.assertEqual(len(self.be.problems()), 4, "every refusal rang once")
        # and an ACCEPTED write under a refused one is what the refusal unwinds onto
        sa.client = self._AcceptsAll("claude-fable-9-9")
        self.assertTrue(self.be.set_model(a, "claude-fable-9-9"))
        self.assertTrue(self.be.set_model(b, "claude-sonnet-9-9"))
        asyncio.run(sa._do_set_model(*qa[-1]))                             # Va accepted
        asyncio.run(sb_._do_set_model(*qb[-1]))                            # Vb refused
        self.assertEqual(sb.read_sdk_defaults(self.d).get("model"), "claude-fable-9-9")
        self.assertEqual(sb.read_reg(self.d, a)["model"], "claude-fable-9-9")
        self.assertEqual(sb.read_reg(self.d, b)["model"], "opus")

    def test_the_store_carries_the_writes_token_and_a_seed_never_does(self):
        # every writer of `model` stamps a fresh token; the spawn seed copies the model alone
        sid = self.be.spawn("m", self.d)
        self.assertTrue(self.be.set_model(sid, "opus"))                    # dormant path
        d = sb.read_sdk_defaults(self.d)
        self.assertEqual(d["model"], "opus")
        t0 = d.get("modelTok")
        self.assertTrue(t0 and isinstance(t0, str))
        s2 = self.be.spawn("n", self.d)
        self.assertEqual(sb.read_reg(self.d, s2)["model"], "opus")
        self.assertNotIn("modelTok", sb.read_reg(self.d, s2), "the token is the store's, not the session's")
        sess = sb.SdkSession(self.be, sb.read_reg(self.d, sid))
        self.be.sessions[sid] = sess
        sess.set_model_live = lambda model, prev=None: None
        self.assertTrue(self.be.set_model(sid, "claude-fable-9-9"))        # live path
        d = sb.read_sdk_defaults(self.d)
        self.assertTrue(d["modelTok"] and d["modelTok"] != t0, "a new write, a new token")
        self.be.set_effort(sid, "low")
        self.assertEqual(sb.read_sdk_defaults(self.d)["modelTok"], d["modelTok"], "an effort write leaves it alone")
        self.assertNotIn("effortTok", sb.read_sdk_defaults(self.d), "only the model carries one")

    def test_a_defaults_file_without_a_token_is_never_reverted(self):
        # compat, fail-safe: a file an older kernel or a hand edit wrote carries no `modelTok` — no
        # token, no match, and the revert leaves the store alone rather than guess
        sid, sess, sched = self._live()                                    # accepted opus
        sess.client = self._RefusesAll()
        self.assertTrue(self.be.set_model(sid, "claude-fable-9-9"))
        self.assertTrue(sb.read_sdk_defaults(self.d).get("modelTok"))
        sb._defaults_path(self.d).write_text(json.dumps({"model": "claude-fable-9-9", "effort": "low"}))
        asyncio.run(sess._do_set_model(*sched[-1]))                        # refused
        self.assertEqual(sb.read_sdk_defaults(self.d), {"model": "claude-fable-9-9", "effort": "low"},
                         "untokened: not this write's to move")
        self.assertEqual(sb.read_reg(self.d, sid)["model"], "opus", "the session's own layers still revert")
        self.assertEqual(sess.chosen_model, "opus")
        # and a write whose verdict never came (the thread died) leaves no node behind to unwind later
        sid2, sess2, sched2 = self._live()
        self.assertTrue(self.be.set_model(sid2, "claude-sonnet-9-9"))
        self.assertEqual(len(self.be._seed_writes), 1)
        self.be._on_session_gone(sess2)
        self.assertEqual(self.be._seed_writes, {}, "dropped with the thread; the store keeps the value")
        self.assertEqual(sb.read_sdk_defaults(self.d).get("model"), "claude-sonnet-9-9")

    def test_a_refusal_landing_between_the_shared_write_and_its_node_never_seeds_the_refused_id(self):
        # If _seed_write_pending wrote the store under the lock, RELEASED it, and took it again to insert
        # the node, a refusal for the write it replaced — on the SDK loop thread, through _revert_model —
        # could run in that gap: it would pop its own node and re-point only the nodes that EXISTED, so
        # the new node would be inserted afterwards still pointing at the refused (value, token); the
        # head check would stand down (the file's head is the new write). The new write's own refusal
        # would then restore the refused id under a token no node knew — unwindable by nothing, and the
        # seed of every new session. Deterministic stand-in for "the other thread takes the lock the
        # instant this one lets go": a lock whose RELEASE runs an armed action once — A's refusal — so it
        # lands wherever the first release inside set_model falls. The write and the insert are one hold.
        a, sa, qa = self._live()
        b, sb_, qb = self._live()
        sa.client = sb_.client = self._RefusesAll()
        self.assertTrue(self.be.set_model(a, "claude-fable-9-9"))          # Va pending, the head

        class _ReleaseRuns:
            """_defaults_lock stand-in: the first release after arming runs the armed action."""
            def __init__(self):
                self._l, self.armed = threading.Lock(), None

            def locked(self):
                return self._l.locked()

            def __enter__(self):
                self._l.acquire()
                return self

            def __exit__(self, *exc):
                self._l.release()
                fn, self.armed = self.armed, None
                if fn:
                    fn()
        lock = _ReleaseRuns()
        lock.armed = lambda: asyncio.run(sa._do_set_model(*qa[-1]))       # Va refused, at the first release
        with mock.patch.object(sb, "_defaults_lock", lock):
            self.assertTrue(self.be.set_model(b, "claude-sonnet-9-9"))     # Vb on top of Va
        self.assertIsNone(lock.armed, "the refusal ran inside b's set_model")
        self.assertEqual(sb.read_sdk_defaults(self.d).get("model"), "claude-sonnet-9-9", "b's write is the head")
        self.assertEqual(sb.read_reg(self.d, a)["model"], "opus", "a's own layers reverted")
        (nb,) = self.be._seed_writes.values()
        self.assertEqual((nb["value"], nb["prior"]), ("claude-sonnet-9-9", "opus"),
                         "b's node points PAST the refused write: the refusal saw it")
        asyncio.run(sb_._do_set_model(*qb[-1]))                            # Vb refused — the head: back to opus
        self.assertEqual(sb.read_sdk_defaults(self.d).get("model"), "opus", "neither refused id is the seed")
        self.assertEqual(self.be._seed_writes, {})
        self.assertEqual(len(self.be.problems()), 2, "every refusal rang once")

    # ── snapshot and write in ONE lock hold; chosen_model compare-and-assign under the session lock ──
    def test_a_defaults_or_reg_read_taken_outside_the_store_lock_never_feeds_the_revert(self):
        # A set_model that captured its snapshots (read_reg, read_sdk_defaults) OUTSIDE _reg_lock /
        # _defaults_lock and only then took the locks to write let a writer on the other thread (a
        # revert, another session's pick) land between the read and the write, so the snapshot described
        # a world the write never replaced. Deterministic stand-in for that interleave: a read made
        # WITHOUT the store lock held reports a phantom value. If any such read feeds the revert, the
        # phantom lands in the store; a read-modify-write under one hold never sees it.
        sid, sess, scheduled = self._live()                                 # accepted: opus
        sess.client = self._RefusesAll()
        real_defaults, real_reg = sb.read_sdk_defaults, sb.read_reg
        be = self.be

        def phantom_defaults(state_dir):
            d = real_defaults(state_dir)
            return d if sb._defaults_lock.locked() else {**d, "model": "phantom-unlocked-read"}

        def phantom_reg(state_dir, s):
            r = real_reg(state_dir, s)
            return r if (r is None or be._reg_lock.locked()) else {**r, "model": "phantom-unlocked-read"}
        with mock.patch.object(sb, "read_sdk_defaults", phantom_defaults), mock.patch.object(sb, "read_reg", phantom_reg):
            self.assertTrue(self.be.set_model(sid, "claude-fable-9-9"))
        self.assertEqual(sb.read_reg(self.d, sid)["model"], "claude-fable-9-9", "the optimistic write landed")
        asyncio.run(sess._do_set_model(*scheduled[0]))
        self.assertEqual(sb.read_sdk_defaults(self.d).get("model"), "opus", "the defaults snapshot was read under the lock")
        self.assertEqual(sb.read_reg(self.d, sid)["model"], "opus", "so was the reg snapshot")
        self.assertEqual(sess.chosen_model, "opus")

    def test_chosen_model_is_written_only_under_the_session_lock(self):
        # _revert_model compares and assigns sess.chosen_model while the kernel thread's set_model
        # assigns it — a torn compare-and-swap unless both writers hold the session's lock around the
        # compare-and-assign; a property stand-in records any write made without it.
        sid = self.be.spawn("m", self.d)
        self.assertTrue(self.be.set_model(sid, "opus"))
        unlocked = []

        class _Guarded(sb.SdkSession):
            @property
            def chosen_model(self):
                return self.__dict__.get("_chosen", "")

            @chosen_model.setter
            def chosen_model(self, v):
                lk = self.__dict__.get("_lock")           # absent during __init__'s own seed (before the lock exists)
                if lk is not None and not lk.locked():
                    unlocked.append(v)
                self.__dict__["_chosen"] = v
        sess = _Guarded(self.be, sb.read_reg(self.d, sid))
        sess.model = "Opus 4.8"
        self.be.sessions[sid] = sess
        scheduled = []
        sess.set_model_live = lambda model, prev=None: scheduled.append((model, prev))
        sess.client = self._RefusesAll()
        self.assertTrue(self.be.set_model(sid, "claude-fable-9-9"))
        self.assertEqual(sess.chosen_model, "claude-fable-9-9")
        asyncio.run(sess._do_set_model(*scheduled[0]))
        self.assertEqual(sess.chosen_model, "opus")
        self.assertEqual(unlocked, [], "every write — the optimistic one and the revert — held the lock")
        # the compare half of the revert's compare-and-swap sits in the SAME hold as its assign
        src = inspect.getsource(sb.SdkBackend._revert_model)
        hold = src.index("with sess._lock:")
        self.assertLess(hold, src.index("sess.chosen_model == picked"), "the compare is inside the hold")
        self.assertLess(src.index("sess.chosen_model == picked"), src.index("with self._reg_lock:"),
                        "…and the hold is released before the reg lock (no nesting)")

    def test_set_model_and_effort_on_a_dormant_session_leave_an_acknowledgment_chip(self):
        # a composer "/model X" on a LIVE session lands the synthesized command chip and the webview's
        # optimistic bubble retires against it; on a DORMANT session nothing landed, so the dashed
        # bubble sat as "unconfirmed" and vanished with no trace. The chip — and its durable gesture
        # twin — are the acknowledgment, whatever the session's liveness.
        sid = self.be.spawn("m", self.d)                  # a reg, no thread: dormant
        self.assertTrue(self.be.set_model(sid, "fable"))
        self.assertTrue(self.be.set_effort(sid, "high"))
        chips = {a["command"]: a for a in self.be.live_atoms(sid) if a.get("command")}
        self.assertEqual(set(chips), {"/model", "/effort"})
        for cmd, disp in (("/model", "/model fable"), ("/effort", "/effort high")):
            a = chips[cmd]
            self.assertTrue(a["uuid"].startswith("cmd:"), a["uuid"])
            self.assertEqual((a["type"], a["author"], a["_echo_text"]), ("user", "human", disp))
            self.assertEqual(a["message"]["content"][0]["text"], disp, "the text the optimistic bubble retires against")
            self.assertEqual(a["session_id"], sid)
        gestures = [json.loads(l).get("cmdGesture") for l in (Path(self.d) / "states" / (sid + ".jsonl")).read_text().splitlines()]
        self.assertEqual([g for g in gestures if g], ["/model fable", "/effort high"], "the durable twin, so the history keeps the gesture")
        # the dormant resolution is unchanged: the badge shows the pick now, no dots
        reg = sb.read_reg(self.d, sid)
        self.assertEqual((reg["model"], reg["liveModel"], reg.get("modelPending")), ("fable", "Fable", False))

    def test_learn_model_clears_pending_only_when_the_new_name_lands(self):
        sess = sb.SdkSession(self.be, {"sid": "p", "name": "n", "cwd": self.d, "model": "fable"})
        sess.model = "Fable 5"
        sess._model_pending = "opus"                       # a switch to opus is resolving
        sess._learn_model("Fable 5")                       # a still-in-flight fable turn reports the OLD name
        self.assertEqual(sess._model_pending, "opus", "the old name does not clear the switch — dots stay")
        sess._learn_model("Opus 4.8")                      # the new model finally streams
        self.assertEqual(sess._model_pending, "", "the matching name clears the switch — dots stop")
        self.assertEqual(sess.model, "Opus 4.8")
        self.assertFalse(sb.read_reg(self.d, "p").get("modelPending") or False)

    def test_session_gone_mid_switch_does_not_trap_the_dots(self):
        sess = sb.SdkSession(self.be, {"sid": "g", "name": "n", "cwd": self.d, "model": "opus"})
        sess._model_pending = "opus"
        self.be._on_session_gone(sess)
        self.assertEqual(sess._model_pending, "", "a thread that dies mid-switch resolves the pending marker")
        self.assertFalse(sb.read_reg(self.d, "g").get("modelPending") or False)
        self.assertEqual(sb.read_reg(self.d, "g").get("liveModel"), "Opus", "and lands a best-effort label, not blank")

    def test_set_mode_persists_to_registry(self):
        sid = self.be.spawn("m", self.d)
        self.assertTrue(self.be.set_mode(sid, "plan"))
        self.assertEqual(sb.read_reg(self.d, sid)["mode"], "plan")

    def test_bypass_applies_to_THIS_session_and_is_never_remembered(self):
        # The picker offers Bypass on SDK sessions (the user 2026-08-15). Every other mode is a
        # preference worth inheriting, so it seeds the next new session — but spawn() reads that seed
        # with nothing in the create UI showing it, so remembering BYPASS would hand every session you
        # started afterwards an unprompted agent, off one click on one tab. It stays where you set it.
        sid = self.be.spawn("m", self.d)
        self.assertTrue(self.be.set_mode(sid, "plan"))
        self.assertEqual(sb.read_sdk_defaults(self.d).get("mode"), "plan", "an ordinary mode is remembered")

        self.assertTrue(self.be.set_mode(sid, "bypassPermissions"))
        self.assertEqual(sb.read_reg(self.d, sid)["mode"], "bypassPermissions",
                         "it DOES apply to the session you set it on")
        self.assertEqual(sb.read_sdk_defaults(self.d).get("mode"), "plan",
                         "…and leaves the remembered default alone, rather than clobbering it")
        self.assertEqual(sb.read_reg(self.d, self.be.spawn("m2", self.d))["mode"], "plan",
                         "so the NEXT new session comes up prompting, not bypassing")

    def test_bypass_is_not_remembered_even_as_the_first_mode_ever_picked(self):
        # The guard cannot be "keep the previous default" alone: with no default written yet there is
        # nothing to keep, and spawn()'s own fallback has to be what a new session lands on.
        sid = self.be.spawn("m", self.d)
        self.assertTrue(self.be.set_mode(sid, "bypassPermissions"))
        self.assertNotEqual(sb.read_sdk_defaults(self.d).get("mode"), "bypassPermissions")
        self.assertNotEqual(sb.read_reg(self.d, self.be.spawn("m2", self.d))["mode"], "bypassPermissions")

    def test_chosen_model_read_from_reg_on_construct(self):
        sess = sb.SdkSession(self.be, {"sid": "x", "name": "n", "cwd": self.d, "model": "sonnet"})
        self.assertEqual(sess.chosen_model, "sonnet")
        plain = sb.SdkSession(self.be, {"sid": "y", "name": "n", "cwd": self.d})
        self.assertEqual(plain.chosen_model, "")          # default: no model flag → CLI default

    def test_spawn_sets_default_effort_and_set_effort_validates(self):
        sid = self.be.spawn("e", self.d)
        self.assertEqual(sb.read_reg(self.d, sid)["effort"], sb.DEFAULT_EFFORT)   # explicit default so the picker shows a true value
        self.assertTrue(self.be.set_effort(sid, "low"))
        self.assertEqual(sb.read_reg(self.d, sid)["effort"], "low")
        self.assertFalse(self.be.set_effort(sid, "ultra"))   # not a real level → rejected
        self.assertEqual(sb.read_reg(self.d, sid)["effort"], "low")   # reg unchanged after a bad value
        self.assertFalse(self.be.set_effort("no-such-sid", "low"))

    def test_effort_read_from_reg_on_construct(self):
        s1 = sb.SdkSession(self.be, {"sid": "a", "name": "n", "cwd": self.d, "effort": "max"})
        self.assertEqual(s1.effort, "max")
        s2 = sb.SdkSession(self.be, {"sid": "b", "name": "n", "cwd": self.d})
        self.assertEqual(s2.effort, sb.DEFAULT_EFFORT)   # no reg effort → default (so the picker is never empty)


class RememberedDefaults(unittest.TestCase):
    """A NEW SDK session seeds its model+effort from the user's LAST pick on any session (remembered
    globally in sdk-defaults.json), falling back to the hardcoded defaults — and the seed lands in the new
    session's OWN reg, so the badge can't desync from what _options launches with (the user 2026-06-27).
    CI-safe: spawn/set_model/set_effort all work with no live session thread."""
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)

    def test_fresh_install_uses_hardcoded_defaults(self):
        sid = self.be.spawn("a", self.d)
        reg = sb.read_reg(self.d, sid)
        self.assertEqual(reg["effort"], sb.DEFAULT_EFFORT)
        self.assertNotIn("model", reg)               # nothing remembered → account default (no model override)
        self.assertEqual(sb.read_sdk_defaults(self.d), {})

    def test_set_effort_is_remembered_and_seeds_the_next_session(self):
        s1 = self.be.spawn("a", self.d)
        self.assertTrue(self.be.set_effort(s1, "low"))
        self.assertEqual(sb.read_sdk_defaults(self.d).get("effort"), "low", "the pick is remembered globally")
        s2 = self.be.spawn("b", self.d)                                   # a NEW session, created AFTER the pick
        self.assertEqual(sb.read_reg(self.d, s2)["effort"], "low", "new session seeds the remembered effort")
        self.assertEqual(self.be.live_sessions()[s2]["effort"], "low", "and the badge shows exactly that")

    def test_set_model_is_remembered_and_seeds_the_next_session(self):
        s1 = self.be.spawn("a", self.d)
        self.assertTrue(self.be.set_model(s1, "sonnet"))
        self.assertEqual(sb.read_sdk_defaults(self.d).get("model"), "sonnet")
        s2 = self.be.spawn("b", self.d)
        self.assertEqual(sb.read_reg(self.d, s2)["model"], "sonnet", "new session seeds the remembered model")
        # no desync: what the dormant badge shows pre-connect == the alias it will actually launch with
        self.assertEqual(self.be.live_sessions()[s2]["model"], "Sonnet")
        self.assertEqual(sb.SdkSession(self.be, sb.read_reg(self.d, s2)).chosen_model, "sonnet")

    def test_remembering_model_does_not_clobber_remembered_effort(self):
        s1 = self.be.spawn("a", self.d)
        self.be.set_effort(s1, "max")
        self.be.set_model(s1, "opus")                                    # touches model only
        d = sb.read_sdk_defaults(self.d)
        self.assertEqual((d.get("model"), d.get("effort")), ("opus", "max"))

    def test_fresh_session_defaults_to_acceptEdits_mode(self):
        sid = self.be.spawn("a", self.d)
        self.assertEqual(sb.read_reg(self.d, sid)["mode"], "acceptEdits", "no remembered mode → acceptEdits")

    def test_set_mode_is_remembered_and_seeds_the_next_session(self):
        # the bug (the user 2026-06-27): mode wasn't remembered like model/effort, so every new SDK session
        # came up acceptEdits regardless of the user's preferred mode. (This used to demonstrate the point
        # with bypassPermissions, which is now the ONE mode deliberately left out of the memory — see
        # SetModelModePure.test_bypass_applies_to_THIS_session_and_is_never_remembered. Any other mode
        # still seeds, which is what this covers.)
        s1 = self.be.spawn("a", self.d)
        self.assertTrue(self.be.set_mode(s1, "auto"))
        self.assertEqual(sb.read_sdk_defaults(self.d).get("mode"), "auto", "remembered globally")
        s2 = self.be.spawn("b", self.d)                                  # a NEW session, created AFTER the pick
        self.assertEqual(sb.read_reg(self.d, s2)["mode"], "auto", "new session seeds the mode")
        self.assertEqual(self.be.live_sessions()[s2]["mode"], "auto", "and the badge shows it")

    def test_a_hand_written_bypass_default_is_still_honoured(self):
        # The carve-out lives in set_mode, NOT in spawn: romp declines to remember bypass off a click,
        # but it does not overrule someone who wrote the default themselves. The escape hatch stays open
        # for anyone who genuinely wants every new session unprompted.
        sb.write_sdk_default(self.d, mode="bypassPermissions")
        self.assertEqual(sb.read_reg(self.d, self.be.spawn("a", self.d))["mode"], "bypassPermissions")

    def test_remembering_mode_does_not_clobber_model_or_effort(self):
        s1 = self.be.spawn("a", self.d)
        self.be.set_effort(s1, "low"); self.be.set_model(s1, "opus"); self.be.set_mode(s1, "plan")
        d = sb.read_sdk_defaults(self.d)
        self.assertEqual((d.get("model"), d.get("effort"), d.get("mode")), ("opus", "low", "plan"))

    def test_resetting_model_to_default_clears_the_override_for_new_sessions(self):
        s1 = self.be.spawn("a", self.d)
        self.be.set_model(s1, "sonnet")
        self.be.set_model(s1, "default")                                 # user resets to the account default
        self.assertEqual(sb.read_sdk_defaults(self.d).get("model"), "default")
        s2 = self.be.spawn("b", self.d)
        self.assertNotIn("model", sb.read_reg(self.d, s2), "remembered 'default' → no model override (account default)")

    def test_bad_remembered_effort_falls_back_to_hardcoded(self):
        sb.write_sdk_default(self.d, effort="ultra")                     # a level that isn't valid (e.g. stale file)
        sid = self.be.spawn("a", self.d)
        self.assertEqual(sb.read_reg(self.d, sid)["effort"], sb.DEFAULT_EFFORT)


class LiveAskReplay(unittest.TestCase):
    """A blocked SDK session's prompt must REPLAY, not vanish (the user 2026-06-24: blocked-no-prompt). _emit_ask
    STORES the ask (not just a bool) so the kernel's _ask_poll can re-push it to any chat client that connects /
    refocuses / reloads after the ask was raised; _clear_ask removes it on answer/cancel. Before this, the ask
    was a one-shot push and _ask_poll pane-scraped the (pane-less) SDK session, found nothing, and cleared the
    prompt every 1.2s tick."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.backend = sb.SdkBackend(self.d, "/bin/true", lambda app, msg: None)

    def test_emit_stores_ask_for_replay_and_clear_removes(self):
        class _Sess:
            sid = "11111111-2222-3333-4444-555555555555"
        sess = _Sess()
        ask = {"kind": "single", "header": "Pet",
               "options": [{"n": 1, "label": "cats"}, {"n": 2, "label": "dogs"}]}
        self.assertIsNone(self.backend.current_ask(sess.sid))       # nothing pending yet
        self.backend._emit_ask(sess, ask)
        self.assertEqual(self.backend.current_ask(sess.sid), ask)   # stored verbatim → _ask_poll replays it
        self.backend._clear_ask(sess)
        self.assertIsNone(self.backend.current_ask(sess.sid))       # answered/cancelled → gone


class AskArmedBeforePresent(unittest.TestCase):
    """An ask is never PRESENTED before the future its answer lands on exists. resolve_ask reads
    _cur_ask_fut synchronously on the caller's thread and reports False when nothing is waiting (T214's
    truthful delivery outcome), so an answer that arrives between _emit_ask and the coroutine's first
    await must already find the future armed — or it is reported lost and the coroutine waits forever.
    Production dodges the gap by microseconds (only the kernel's click handlers answer, from another
    thread); an answer delivered synchronously INSIDE the presentation callback hits it every time. That
    is exactly how the SDK-gated round-trip classes below drive their asks, and CI does not install the
    SDK, so the hang was never seen there. Pinned WITHOUT the SDK: _ask_one needs none, so the standard
    runner and CI exercise the invariant. The answer rides on_ask -> resolve_ask, the kernel's own path."""

    SID = "11111111-2222-3333-4444-555555555555"

    def test_an_answer_delivered_inside_the_presentation_callback_is_not_lost(self):
        import asyncio
        outcomes = []

        def notify(app, msg):
            if msg.get("type") == "askLive":
                # same call stack as _emit_ask: the future must ALREADY exist here
                outcomes.append(self.backend.on_ask(msg["id"], "answer", 2))

        d = tempfile.mkdtemp()
        self.backend = sb.SdkBackend(d, "/bin/true", notify)
        sess = sb.SdkSession(self.backend, {"sid": self.SID, "name": "n", "cwd": d})
        self.backend.sessions[self.SID] = sess
        q = {"question": "Cats or dogs?", "header": "Pet", "multiSelect": False,
             "options": [{"label": "cats"}, {"label": "dogs"}]}

        async def go():
            sess.loop = asyncio.get_running_loop()
            return await asyncio.wait_for(sess._ask_one(q, 0, 1), timeout=5)

        try:
            res = asyncio.run(go())
        except asyncio.TimeoutError:
            self.fail("the answer was dropped: _ask_one presented its ask before arming the future, "
                      "so resolve_ask found nothing waiting and the coroutine never returned")
        self.assertEqual(res, "dogs")
        self.assertEqual(outcomes, [True], "resolve_ask must report the answer DELIVERED (T214), not lost")
        self.assertIsNone(sess._cur_ask_fut, "the armed future clears once the ask is answered")


class OverlappingAsksAnswerInTurn(unittest.TestCase):
    """Two asks presented concurrently on one session (the SDK dispatches every control request as its
    own detached task) must each get THEIR OWN answer. Before the per-session lock, arming at the sites
    let the second ask find the first's live future and share it — one click resolved both, so an Allow
    given to tool B was applied to tool A silently (PR #875 review). Now the second ask is not even
    PRESENTED until the first resolves, and the answers land on the asks they were given to."""

    SID = "11111111-2222-3333-4444-777777777777"

    def test_the_second_ask_waits_and_each_gets_its_own_answer(self):
        import asyncio
        presented = []                                    # askLive ids in presentation order

        def notify(app, msg):
            if msg.get("type") == "askLive":
                presented.append(msg["id"])

        d = tempfile.mkdtemp()
        backend = sb.SdkBackend(d, "/bin/true", notify)
        sess = sb.SdkSession(backend, {"sid": self.SID, "name": "n", "cwd": d})
        backend.sessions[self.SID] = sess
        qa = {"question": "First?", "header": "A", "multiSelect": False, "options": [{"label": "a1"}, {"label": "a2"}]}
        qb = {"question": "Second?", "header": "B", "multiSelect": False, "options": [{"label": "b1"}, {"label": "b2"}]}

        async def go():
            sess.loop = asyncio.get_running_loop()
            ta = asyncio.ensure_future(sess._ask_one(qa, 0, 1))
            tb = asyncio.ensure_future(sess._ask_one(qb, 0, 1))
            await asyncio.sleep(0)                        # both tasks start; only ONE may be presented
            self.assertEqual(len(presented), 1, "the second ask waits for the first — never two live at once")
            self.assertTrue(backend.on_ask(presented[0], "answer", 2), "answer the FIRST ask: option 2")
            await asyncio.wait_for(ta, timeout=5)        # the first ask resolves and releases the lock…
            for _ in range(10):                           # …and the second acquires it within a few loop hops
                if len(presented) == 2:
                    break
                await asyncio.sleep(0)
            self.assertEqual(len(presented), 2, "the second ask is presented only after the first resolved")
            self.assertTrue(backend.on_ask(presented[1], "answer", 1), "answer the SECOND ask: option 1")
            return await asyncio.wait_for(asyncio.gather(ta, tb), timeout=5)

        ra, rb = asyncio.run(go())
        self.assertEqual((ra, rb), ("a2", "b1"), "each ask got the answer given to IT — no shared future")
        self.assertIsNone(sess._cur_ask_fut)


class ThinkingKw(unittest.TestCase):
    """The thinking-summaries decision WITHOUT the SDK (2026-09-01, round 2): `thinking_kw` is what
    _options hands ClaudeAgentOptions as `thinking=`, and `thinking_override_note` the one log line owed
    when that flag will override a thinking cap. Both are pure, so the standard runner — which has no
    claude_agent_sdk and therefore SKIPS every OptionsAssembly pin — still exercises the rule.
    OptionsAssembly keeps the composition and the transport's `--thinking adaptive --thinking-display
    summarized` pin; run it with the SDK venv on PYTHONPATH (tests/README.md)."""

    def setUp(self):
        self.d = tempfile.mkdtemp()

    def _write(self, obj):
        with open(os.path.join(self.d, sb.THINKING_SUMMARIES_FILE), "w") as f:
            f.write(obj if isinstance(obj, str) else json.dumps(obj))

    def test_off_is_none_whether_absent_explicit_or_unreadable(self):
        self.assertIsNone(sb.thinking_kw(self.d), "absent file → pass nothing; the CLI's own default stands")
        self._write({"enabled": False, "gt": 2})
        self.assertIsNone(sb.thinking_kw(self.d), "an explicit off is the same as absent")
        self._write("not json")
        self.assertIsNone(sb.thinking_kw(self.d), "unreadable refuses — the opt-in must be provable")

    def test_on_is_the_typed_adaptive_summarized_field(self):
        self._write({"enabled": True, "gt": 1})
        self.assertEqual(sb.thinking_kw(self.d), {"type": "adaptive", "display": "summarized"},
                         "the SDK's ThinkingConfigAdaptive shape, display summarized")
        self.assertIsNot(sb.thinking_kw(self.d), sb.THINKING_SUMMARIES_KW, "a copy per call, never the shared literal")

    def test_the_override_note_fires_only_for_a_cap_in_the_cli_environment(self):
        # The CLI resolves --thinking adaptive ahead of MAX_THINKING_TOKENS (verified in the 2.1.257
        # binary, re-read at 2.1.258): with a cap in the environment the toggle turns thinking ON where
        # the cap had it off. Real, so never silent — but only when it is real.
        on = {"type": "adaptive", "display": "summarized"}
        self.assertEqual(sb.thinking_override_note(None, {"MAX_THINKING_TOKENS": "0"}), "",
                         "toggle off → the flag is not sent, so nothing is overridden")
        self.assertEqual(sb.thinking_override_note(on, {"PATH": "/bin"}), "",
                         "no cap in the environment → the flag changes only the display; nothing to say")
        note = sb.thinking_override_note(on, {"MAX_THINKING_TOKENS": "0", "PATH": "/bin"})
        self.assertIn("MAX_THINKING_TOKENS=0", note, "names the cap it overrides, with its value")
        self.assertIn("--thinking adaptive", note, "…and the flag that wins")
        self.assertIn("adaptive thinking", note, "…and what the sessions will actually run")


# --- Runner + can_use_tool bridge (needs the SDK message classes) ---
try:
    import claude_agent_sdk as _sdk
    _HAVE_SDK = True
except Exception:
    _HAVE_SDK = False


@unittest.skipUnless(_HAVE_SDK, "claude_agent_sdk not installed")
class AskRoundTrip(unittest.TestCase):
    """Drive a full turn through a fake client and assert the AskUserQuestion
    answer round-trips as PermissionResultAllow(updated_input)."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self._orig_client = _sdk.ClaudeSDKClient

        QUESTION = {"questions": [{
            "question": "Cats or dogs?", "header": "Pet", "multiSelect": False,
            "options": [{"label": "cats", "description": "c"}, {"label": "dogs", "description": "d"}],
        }]}

        class _Ctx:
            title = display_name = decision_reason = None

        import asyncio as _aio

        class FakeClient:
            """Models the real split: query(iterable) WRITES each turn (blocking until the
            iterable ends), receive_messages() yields outputs independently. So this only
            works if the backend runs feeder + receiver CONCURRENTLY — if it awaited query()
            first (the bug the live smoke caught), the never-ending input generator would
            starve the receive loop and this test would hang."""
            instances = []

            def __init__(self, options=None, transport=None):
                self.options = options
                self.captured = None
                self.interrupted = False
                self.model_calls = []        # records set_model() over the control channel
                self.mode_calls = []         # records set_permission_mode()
                self._turnq = _aio.Queue()
                FakeClient.instances.append(self)

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def query(self, prompt, session_id="default"):
                async for turn in prompt:                # writes each turn (blocks like the real one)
                    await self._turnq.put(turn)

            async def interrupt(self):
                self.interrupted = True

            async def set_model(self, model=None):
                self.model_calls.append(model)

            async def set_permission_mode(self, mode):
                self.mode_calls.append(mode)

            async def get_context_usage(self):
                # The DESIGNED control request behind the CLI's /context. Unlike the message stream, it
                # answers PRE-TURN — returning the live model id + % the instant the control channel is up.
                # This is the source the eager-connect publish relies on (verified against the real SDK).
                return {"percentage": 2, "model": "claude-x"}

            async def receive_messages(self):
                # FAITHFUL to the real CLI: a turn-less streaming connection emits NO message at all — the
                # `init` SystemMessage rides the FIRST turn's response, NOT connect. (The old fake yielded
                # init on connect, which let the broken pre-turn path pass CI while real sessions stayed
                # blank until message 1 — the user 2026-06-27.) So init is yielded only once a turn arrives.
                first = True
                while True:
                    await self._turnq.get()              # next enqueued user turn
                    if first:
                        first = False
                        yield _sdk.SystemMessage("init", {
                            "model": "claude-x", "permissionMode": "acceptEdits",
                            "session_id": (self.options.session_id or "fsid")})
                    allow = await self.options.can_use_tool("AskUserQuestion", QUESTION, _Ctx())
                    self.captured = allow
                    yield _sdk.AssistantMessage(content=[_sdk.TextBlock("ok")], model="claude-x")
                    yield _sdk.ResultMessage("success", 1, 1, False, 1, "fsid")

        _sdk.ClaudeSDKClient = FakeClient
        self.Fake = FakeClient
        FakeClient.instances = []

        self.notes = []

        def notify(app, msg):
            self.notes.append((app, msg))
            if msg.get("type") == "askLive":            # the UI auto-answers option 1 (cats)
                self.backend.on_ask(msg["id"], "answer", 1)

        self.backend = sb.SdkBackend(self.d, "/bin/true", notify)

    def tearDown(self):
        _sdk.ClaudeSDKClient = self._orig_client

    def _wait(self, pred, timeout=6.0):
        end = time.time() + timeout
        while time.time() < end:
            if pred():
                return True
            time.sleep(0.02)
        return False

    def test_spawn_then_ask_round_trip(self):
        sid = self.backend.spawn("alpha", self.d)
        # spawn registers identity + registry + initial state, all on disk
        self.assertTrue(sb.read_reg(self.d, sid)["alive"])
        self.assertTrue(os.path.exists(os.path.join(self.d, "names", sid)))
        self.assertIn(sid, self.backend.live_sessions())

        self.assertTrue(self.backend.send(sid, "hello"))
        self.assertTrue(self._wait(lambda: self.Fake.instances and self.Fake.instances[0].captured),
                        "can_use_tool never returned an answer")

        allow = self.Fake.instances[0].captured
        self.assertEqual(allow.behavior, "allow")
        self.assertEqual(allow.updated_input["answers"], {"Cats or dogs?": "cats"})
        self.assertEqual(allow.updated_input["questions"], [{
            "question": "Cats or dogs?", "header": "Pet", "multiSelect": False,
            "options": [{"label": "cats", "description": "c"}, {"label": "dogs", "description": "d"}]}])

        # an askLive went out and was later cleared
        kinds = [m.get("type") for _app, m in self.notes]
        self.assertIn("askLive", kinds)
        self.assertIn("askLiveClear", kinds)

        # state settled working -> waiting after the result
        self.assertTrue(self._wait(
            lambda: sb.last_state(self.d, sid).get("state") == "waiting"))

    def test_connect_publishes_model_and_ctx_without_a_turn(self):
        """Eager-connect (used at createSession + on chat open) brings up the session WITHOUT a user turn, and
        its model AND context % must publish on OPEN — like a tmux session shows them on launch (the user
        2026-06-27). The streaming `init` SystemMessage does NOT arrive until the first turn (the FakeClient
        now models this), so connect resolves both from get_context_usage() — the designed control request
        that answers pre-turn. REGRESSION: the old code keyed model/ctx resolution off that init message, so a
        freshly-created SDK session showed neither until the first message was sent."""
        sid = self.backend.spawn("eager", self.d)
        self.assertEqual(self.backend.live_sessions()[sid]["model"], "", "no model before connect")
        self.assertEqual(self.backend.live_sessions()[sid]["ctx"], "", "no context before connect")
        self.assertTrue(self.backend.connect(sid))
        self.assertTrue(self._wait(lambda: self.backend.live_sessions().get(sid, {}).get("model")),
                        "eager-connect must publish the model via get_context_usage — no init message, no turn")
        snap = self.backend.live_sessions()[sid]
        self.assertEqual(snap["model"], "claude-x", "model resolves from get_context_usage on connect")
        self.assertEqual(snap["ctx"], 2, "context % resolves from get_context_usage on connect")
        # prove no user turn was ever fed: the ask callback never fired
        self.assertTrue(self.Fake.instances, "a client was created on connect")
        self.assertIsNone(self.Fake.instances[0].captured, "no turn was sent — can_use_tool must not have run")
        self.assertFalse(self.backend.connect("no-such-sid"))

    def test_kill_marks_dead(self):
        sid = self.backend.spawn("beta", self.d)
        self.backend.send(sid, "hi")
        self._wait(lambda: self.Fake.instances and self.Fake.instances[0].captured)
        self.assertTrue(self.backend.kill(sid))
        self.assertFalse(sb.read_reg(self.d, sid)["alive"])
        self.assertNotIn(sid, self.backend.live_sessions())

    def test_set_model_and_mode_apply_live(self):
        """The model/mode pickers go over the SDK CONTROL channel (set_model / set_permission_mode),
        not a /model or /effort slash injection into the prompt stream (which the SDK ignores)."""
        sid = self.backend.spawn("ctrl", self.d)
        self.assertTrue(self.backend.send(sid, "hi"))
        self.assertTrue(self._wait(lambda: self.Fake.instances and self.Fake.instances[0].captured),
                        "session never connected")
        c = self.Fake.instances[0]
        self.backend.set_model(sid, "opus")
        self.assertTrue(self._wait(lambda: "opus" in c.model_calls),
                        "model alias not sent via set_model control request")
        self.backend.set_model(sid, "default")
        self.assertTrue(self._wait(lambda: None in c.model_calls),
                        "'default' must reset via set_model(None)")
        self.backend.set_mode(sid, "plan")
        self.assertTrue(self._wait(lambda: "plan" in c.mode_calls),
                        "mode not sent via set_permission_mode control request")
        # persisted so a reconnect keeps the choice; _options carries chosen_model
        self.assertEqual(sb.read_reg(self.d, sid)["model"], "default")
        self.assertEqual(sb.read_reg(self.d, sid)["mode"], "plan")
        sess = self.backend.sessions[sid]
        sess.chosen_model = "sonnet"
        opts = self.backend._options(sess, _sdk.ClaudeAgentOptions)
        self.assertEqual(opts.model, "sonnet")

    def test_effort_change_reconnects_with_new_flag(self):
        """effort is a connect-time CLI flag, so changing it RECONNECTS the client (a 2nd ClaudeSDKClient)
        with the new --effort, resuming the same conversation — not a /effort slash the SDK ignores."""
        sid = self.backend.spawn("eff", self.d)
        self.assertTrue(self.backend.send(sid, "hi"))
        self.assertTrue(self._wait(lambda: self.Fake.instances and self.Fake.instances[0].captured),
                        "first connection never completed a turn")
        self.assertEqual(self.Fake.instances[0].options.effort, sb.DEFAULT_EFFORT)   # spawned at the default
        self.assertTrue(self.backend.set_effort(sid, "low"))
        self.assertTrue(self._wait(lambda: len(self.Fake.instances) >= 2),
                        "effort change did not reconnect the client")
        c2 = self.Fake.instances[1]
        self.assertEqual(c2.options.effort, "low")          # reconnected with the new flag
        self.assertEqual(c2.options.resume, sid)             # resume continues the SAME conversation, not a fresh session
        self.assertEqual(sb.read_reg(self.d, sid)["effort"], "low")
        self.backend.kill(sid)


@unittest.skipUnless(_HAVE_SDK, "claude_agent_sdk not installed")
class CustomAnswerRoundTrip(unittest.TestCase):
    """The 'add your own' free-text affordance on AskUserQuestion (the user 2026-06-27). _ask_one is driven
    through a scripted sequence of actions: each emitted askLive triggers the next action via on_ask, exactly
    as the kernel routes a UI click. Single-select returns the typed text; multi accumulates customs and
    includes them on Submit; unchecking a typed custom removes it."""

    SID = "11111111-2222-3333-4444-555555555555"

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.actions = []
        def notify(app, msg):
            if msg.get("type") == "askLive" and self.actions:
                kind, payload = self.actions.pop(0)
                self.backend.on_ask(msg["id"], kind, payload)
        self.backend = sb.SdkBackend(self.d, "/bin/true", notify)
        self.sess = sb.SdkSession(self.backend, {"sid": self.SID, "name": "n", "cwd": self.d})
        self.backend.sessions[self.SID] = self.sess

    def _ask(self, question, actions):
        import asyncio
        self.actions = list(actions)
        async def go():
            self.sess.loop = asyncio.get_running_loop()
            return await self.sess._ask_one(question, 0, 1)
        return asyncio.run(go())

    def test_single_select_returns_typed_custom_answer(self):
        q = {"question": "Pick", "header": "H", "multiSelect": False,
             "options": [{"label": "A"}, {"label": "B"}]}
        res = self._ask(q, [("custom", "something else entirely")])
        self.assertEqual(res, "something else entirely")

    def test_multi_select_includes_custom_with_checked_options(self):
        q = {"question": "Pick many", "header": "H", "multiSelect": True,
             "options": [{"label": "A"}, {"label": "B"}]}
        res = self._ask(q, [("toggle", 1), ("custom", "extra"), ("submit", None)])
        self.assertEqual(res, ["A", "extra"])

    def test_multi_select_unchecking_a_custom_removes_it(self):
        q = {"question": "Pick many", "header": "H", "multiSelect": True,
             "options": [{"label": "A"}, {"label": "B"}]}
        # add a custom (becomes option n=3), then toggle n=3 off, then submit → nothing chosen
        res = self._ask(q, [("custom", "oops"), ("toggle", 3), ("submit", None)])
        self.assertEqual(res, [])


@unittest.skipUnless(_HAVE_SDK, "claude_agent_sdk not installed")
class PermissionAndPlanRoundTrip(unittest.TestCase):
    """Drive _can_use_tool / _approve_plan directly and assert the PermissionResult the SDK gets back.
    The picker answer is delivered via resolve_ask (call_soon_threadsafe), exactly as the kernel does
    on an inbound on_ask. (the user 2026-06-27: plan approval + diffs + allow-and-don't-ask-again.)"""

    SID = "11111111-2222-3333-4444-555555555555"

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.answer = "1"
        def notify(app, msg):
            if msg.get("type") == "askLive":
                self.last_ask = msg["ask"]
                self.backend.on_ask(msg["id"], "answer", self.answer)
        self.backend = sb.SdkBackend(self.d, "/bin/true", notify)
        self.sess = sb.SdkSession(self.backend, {"sid": self.SID, "name": "n", "cwd": self.d})
        self.backend.sessions[self.SID] = self.sess
        self.sess.inflight = 1                      # mid-turn (a permission interrupts a live turn)

    def _drive(self, coro_fn):
        import asyncio
        async def go():
            self.sess.loop = asyncio.get_running_loop()
            return await coro_fn()
        return asyncio.run(go())

    def test_allow_and_dont_ask_again_returns_updated_permissions(self):
        # the remember path just echoes the SDK's own suggestions back verbatim, so a sentinel suffices
        upd = _sdk.PermissionUpdate(type="setMode", mode="acceptEdits")
        class Ctx:
            title = None; description = None; suggestions = [upd]
        self.answer = "2"                            # "Allow & don't ask again"
        res = self._drive(lambda: self.sess._can_use_tool("Bash", {"command": "ls"}, Ctx()))
        self.assertEqual(res.behavior, "allow")
        self.assertEqual(res.updated_permissions, [upd], "the SDK's own suggestion is echoed back as the rule")

    def test_plain_allow_carries_no_rule(self):
        class Ctx:
            title = None; description = None; suggestions = []
        self.answer = "1"
        res = self._drive(lambda: self.sess._can_use_tool("Bash", {"command": "ls"}, Ctx()))
        self.assertEqual(res.behavior, "allow")
        self.assertIsNone(res.updated_permissions)

    def test_deny_is_deny(self):
        class Ctx:
            title = None; description = None; suggestions = []
        self.answer = "2"                            # with no suggestions, option 2 is Deny
        res = self._drive(lambda: self.sess._can_use_tool("Bash", {"command": "ls"}, Ctx()))
        self.assertEqual(res.behavior, "deny")

    def test_plan_proceed_allows(self):
        self.answer = "1"
        res = self._drive(lambda: self.sess._approve_plan({"plan": "do the thing"}))
        self.assertEqual(res.behavior, "allow")
        self.assertIsNone(res.updated_permissions)
        self.assertEqual(self.last_ask["previewKind"], "plan")
        self.assertIn("do the thing", self.last_ask["preview"])

    def test_plan_accept_edits_sets_mode(self):
        self.answer = "2"                            # "Yes, auto-accept edits"
        res = self._drive(lambda: self.sess._approve_plan({"plan": "go"}))
        self.assertEqual(res.behavior, "allow")
        self.assertEqual(res.updated_permissions[0].type, "setMode")
        self.assertEqual(res.updated_permissions[0].mode, "acceptEdits")

    def test_plan_keep_planning_denies(self):
        self.answer = "3"
        res = self._drive(lambda: self.sess._approve_plan({"plan": "go"}))
        self.assertEqual(res.behavior, "deny")


class StopTask(unittest.TestCase):
    """The bg-task box's Stop button rides the SDK's designed stop_task control request (the user
    2026-08-04). The box shows tasks by TOOL-USE id (the kernel's transcript scan); the control request
    takes the CLI's lifecycle task id (_bg_tasks' key) — request_stop_task resolves either form. A
    refusal returns False so the kernel can WARN, never a silent no-op; tmux inherits the ABC's False
    (its box never shows live tasks)."""

    def _sess(self):
        d = tempfile.mkdtemp()
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None)
        return sb.SdkSession(be, {"sid": "11111111-2222-3333-4444-555555555555", "name": "n", "cwd": d})

    def test_resolves_the_tool_use_id_to_the_lifecycle_task_id(self):
        sess = self._sess()
        sess._bg_tasks["task-1"] = {"desc": "sweep", "type": "bash", "since": 1, "toolUseId": "toolu_9", "lastTool": ""}
        dispatched = []
        sess.loop = type("L", (), {"call_soon_threadsafe": staticmethod(lambda cb: dispatched.append(cb))})()
        sess.client = object()
        self.assertTrue(sess.request_stop_task("toolu_9"), "the box's tool-use id resolves")
        self.assertTrue(sess.request_stop_task("task-1"), "the lifecycle id itself is accepted too")
        self.assertEqual(len(dispatched), 2, "the control request is scheduled on the loop thread")

    def test_unknown_task_or_dead_client_refuses(self):
        sess = self._sess()
        self.assertFalse(sess.request_stop_task("toolu_missing"), "unknown/terminal task → False → kernel warns")
        sess._bg_tasks["task-1"] = {"toolUseId": "toolu_9"}
        self.assertFalse(sess.request_stop_task("toolu_9"), "no connected client → False, never a crash")

    def test_backend_routes_by_sid_and_tmux_defaults_false(self):
        d = tempfile.mkdtemp()
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None)
        self.assertFalse(be.stop_task("no-such-sid", "toolu_9"))
        import importlib.util as _u
        spec_src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                                     "kernel", "session_backend.py")).read()
        self.assertIn("def stop_task(self, sid: str, task_id: str) -> bool:", spec_src)
        self.assertIn("return False", spec_src.split("def stop_task", 1)[1][:600],
                      "the ABC default is False — tmux has no such control")

    def test_kernel_op_warns_on_refusal(self):
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "bin", "romp-kernel")) as f:
            src = f.read()
        self.assertIn('"stopTask"', src[src.index("ID_OPS"):src.index("ID_OPS") + 700],
                      "stopTask routes by session id like every session op")
        self.assertIn('elif t == "stopTask" and msg.get("taskId"):', src)
        self.assertIn("Couldn't stop that background task", src, "a refusal warns the user — never a silent no-op")


class ApiKeyAuthUsage(unittest.TestCase):
    """API-key auth is a PER-SESSION fact (the user 2026-08-08): with a real key in the service env,
    only the sessions whose project approved it used it, while every other session rode the
    subscription login — yet the old backend-global flag let whichever init arrived LAST speak for all
    of them, wiping the login's windows and re-wiping on every keyed session's reconnect. The flag now
    lives on the session: it gates that session's own get_usage polls and its RateLimitEvent records,
    and NOTHING wipes usage.json — the login's lifecycle is tracked read-side (the acct stamp, plus
    kernel _usage()'s no-login spend arm)."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)
        self.p = Path(self.d) / "usage.json"
        self.p.write_text(json.dumps({"t": 1785898746,
                                      "five_hour": {"pct": 46, "resets_at": 1785907200},
                                      "seven_day": {"pct": 21, "resets_at": 1786388400}}))
        self.s = sb.SdkSession(self.be, {"sid": "11111111-2222-3333-4444-000000000001",
                                         "name": "n", "cwd": "/tmp"})

    def test_a_keyed_init_marks_only_its_own_session_and_never_wipes(self):
        before = self.p.read_text()
        self.be._note_auth_source(self.s, "ANTHROPIC_API_KEY")
        self.assertTrue(self.s.api_key_auth)
        self.assertEqual(self.p.read_text(), before,
                         "one keyed session never speaks for the login's windows — no wipe, ever")
        other = sb.SdkSession(self.be, {"sid": "11111111-2222-3333-4444-000000000002",
                                        "name": "m", "cwd": "/tmp"})
        self.assertFalse(other.api_key_auth, "the flag is the session's, not the backend's")

    def test_the_string_none_is_a_subscription_login_not_an_api_key(self):
        """The CLI has said "no API key" two ways: the field absent (verified 2026-08-04) and — since
        about CLI 2.1.222 — the literal string 'none' (both hosts' journals, 2026-08-08)."""
        self.be._note_auth_source(self.s, "none")
        self.assertFalse(self.s.api_key_auth, "'none' means NO api key — a subscription login")
        self.be._note_auth_source(self.s, "ANTHROPIC_API_KEY")
        self.assertTrue(self.s.api_key_auth)
        self.be._note_auth_source(self.s, "none")
        self.assertFalse(self.s.api_key_auth, "'none' flips a keyed session back, like the absent field")

    def test_a_keyed_sessions_rate_limit_events_never_reach_the_login_windows(self):
        # the key's limits are ANOTHER allowance — recording them contaminated the login's bars
        calls = []
        self.be._record_rate_limit = lambda info: calls.append(info)
        class _RL:
            rate_limit_info = {"kind": "five_hour"}
        self.be._forward = lambda sess, msg: None
        self.s.api_key_auth = True
        self.s._on_message(_RL(), _AssistantMessage, _ResultMessage, type("S", (), {}))
        self.assertEqual(calls, [], "a keyed session's events are ignored")
        self.s.api_key_auth = False
        self.s._on_message(_RL(), _AssistantMessage, _ResultMessage, type("S", (), {}))
        self.assertEqual(len(calls), 1, "a subscription session's events record as ever")

    def test_refresh_skips_keyed_sessions_and_polls_a_subscription_one(self):
        keyed = self.s
        keyed.api_key_auth = True
        keyed.client, keyed.loop, keyed.ended = object(), object(), False
        sub = sb.SdkSession(self.be, {"sid": "11111111-2222-3333-4444-000000000003",
                                      "name": "m", "cwd": "/tmp"})
        sub.client, sub.loop, sub.ended = object(), object(), False
        polled = []
        keyed.refresh_usage = lambda: polled.append("keyed") or True
        sub.refresh_usage = lambda: polled.append("sub") or True
        self.be.sessions = {keyed.sid: keyed, sub.sid: sub}
        self.be.refresh_usage()
        self.assertEqual(polled, ["sub"], "the click heals off the login's session, never the keyed one")

    def test_init_reads_the_field_and_the_poll_is_gated_per_session(self):
        src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                                "kernel", "sdk_backend.py")).read()
        self.assertIn('self.backend._note_auth_source(self, d.get("apiKeySource"))', src,
                      "the init message is the one in-band auth signal, handed the SESSION")
        self.assertIn("if self.api_key_auth:", src.split("async def _do_refresh_usage", 1)[1][:1600],
                      "get_usage is gated on the SESSION's own auth — it only times out on a keyed one")


class SpendRecord(unittest.TestCase):
    """Under API-key auth the rail shows SPEND where the subscription bars sat (the user 2026-08-04):
    each ResultMessage's total_cost_usd accumulates into spend.json by LOCAL date. Recorded on every
    result regardless of auth (display is gated, the record is not); pruned to 90 days."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)
        self.p = Path(self.d) / "spend.json"

    def _today(self):
        return time.strftime("%Y-%m-%d")

    def test_accumulates_cost_turns_and_tokens_by_day_and_hour(self):
        self.be._record_spend(0.02, {"input_tokens": 100, "output_tokens": 40,
                                     "cache_read_input_tokens": 1000, "cache_creation_input_tokens": 60})
        self.be._record_spend(0.03, {"input_tokens": 10, "output_tokens": 5})
        o = json.loads(self.p.read_text())
        d = o["days"][self._today()]
        self.assertAlmostEqual(d["usd"], 0.05)
        self.assertEqual(d["turns"], 2)
        self.assertEqual((d["tokIn"], d["tokOut"], d["tokCacheR"], d["tokCacheW"]), (110, 45, 1000, 60))
        h = o["hours"][time.strftime("%Y-%m-%dT%H")]   # the rolling 5h/7d windows read these buckets
        self.assertAlmostEqual(h["usd"], 0.05)
        self.assertEqual(h["turns"], 2)

    def test_a_result_without_usage_still_records_cost(self):
        self.be._record_spend(0.02)
        d = json.loads(self.p.read_text())["days"][self._today()]
        self.assertEqual((d["usd"], d["tokIn"], d["tokOut"]), (0.02, 0, 0))

    def test_ignores_missing_zero_and_junk_costs(self):
        for v in (None, 0, -1, "0.5"):
            self.be._record_spend(v)
        self.assertFalse(self.p.exists(), "no real cost → no file, never a confident zero")

    def test_prunes_to_ninety_days(self):
        days = {"2020-01-%02d" % (i + 1) for i in range(25)}
        self.p.write_text(json.dumps({"days": {k: {"usd": 1, "turns": 1} for k in days}}))
        self.be._record_spend(0.01)
        kept = json.loads(self.p.read_text())["days"]
        self.assertLessEqual(len(kept), 90)
        self.assertIn(self._today(), kept)

    def test_by_sid_attribution_with_keyed_split(self):
        # T100 (the nightly optimizer's accepted ask): key-billed cost PER SESSION. Two sids, one
        # keyed and one login — the bucket totals stay whole, and each sid carries its own keyed
        # dimension. Private synthetic sids (the goal-store fixture rule).
        self.be._record_spend(0.02, {"input_tokens": 100, "output_tokens": 40}, keyed=True,
                              sid="aaaa1111-spend-attr-1")
        self.be._record_spend(0.03, {"input_tokens": 10, "output_tokens": 5}, keyed=False,
                              sid="aaaa1111-spend-attr-2")
        self.be._record_spend(0.05, {"input_tokens": 1, "output_tokens": 1}, keyed=True,
                              sid="aaaa1111-spend-attr-1")
        d = json.loads(self.p.read_text())["days"][self._today()]
        self.assertAlmostEqual(d["usd"], 0.10)
        by = d["bySid"]
        s1, s2 = by["aaaa1111-spend-attr-1"], by["aaaa1111-spend-attr-2"]
        self.assertAlmostEqual(s1["usd"], 0.07)
        self.assertEqual((s1["turns"], s1["tok"]), (2, 142))
        self.assertAlmostEqual(s1["key"]["usd"], 0.07, msg="the keyed split rides the sid — the optimizer's dimension")
        self.assertEqual((s1["key"]["turns"], s1["key"]["tok"]), (2, 142))
        self.assertAlmostEqual(s2["usd"], 0.03)
        self.assertNotIn("key", s2, "a login-only sid carries no keyed split — its cost is dollars nobody is billed")
        h = json.loads(self.p.read_text())["hours"][time.strftime("%Y-%m-%dT%H")]
        self.assertAlmostEqual(h["bySid"]["aaaa1111-spend-attr-1"]["usd"], 0.07, msg="the hour buckets attribute too")

    def test_a_thread_turn_bills_the_owning_session(self):
        # T144: highlight-reply comment threads minted phantom cheap sessions in spend.json and
        # undercounted the owner (one session split $360.31 own + $3.11 + $5.36 fork sids). The
        # settle passes threadOf when present — assert at the recorder level with the owner's sid.
        OWNER = "aaaa1111-spend-own-1"
        self.be._record_spend(0.02, keyed=True, sid=OWNER)                  # the owner's own turn
        self.be._record_spend(0.03, keyed=True, sid=OWNER)                  # a thread turn, billed via threadOf
        d = json.loads(self.p.read_text())["days"][self._today()]
        self.assertAlmostEqual(d["bySid"][OWNER]["usd"], 0.05,
                               msg="whole-session truth: the thread's spend lands under the owner")
        self.assertEqual(len(d["bySid"]), 1, "no phantom fork sid appears")

    def test_the_settle_seam_prefers_thread_of(self):
        # the session-object seam, executed: thread_of set → the owner's sid reaches the recorder;
        # promotion clears it → the session bills itself from that moment
        sid = "aaaa1111-spend-own-2"
        own = "aaaa1111-spend-own-3"
        sb.write_reg(Path(self.d), sid, {"sid": sid, "name": "c1", "cwd": "/tmp", "threadOf": own})
        s = sb.SdkSession(self.be, sb.read_reg(Path(self.d), sid))
        self.assertEqual(s.thread_of, own, "the durable reg field seeds the object")
        self.assertEqual(s.thread_of or s.sid, own, "the settle's sid expression bills the owner")
        self.be.sessions[sid] = s
        sb.write_name(Path(self.d), sid, "promoted", "/tmp", "#123456", "white")  # promote needs no name write order here
        self.assertTrue(self.be.promote_thread(sid, "promoted"))
        self.assertEqual(s.thread_of, "", "a promoted session bills ITSELF from this moment")
        self.assertEqual(s.thread_of or s.sid, sid)

    def test_fork_spend_spanning_days_stays_under_the_owner(self):
        # the day-spanning fixture: a thread that worked before and after midnight accumulates
        # under the OWNER in each day's bucket independently (buckets key on local date at fold
        # time; the owner sid is constant, so both days read whole-session truth)
        OWNER = "aaaa1111-spend-own-4"
        yesterday = {"usd": 1.0, "turns": 2, "bySid": {OWNER: {"usd": 1.0, "turns": 2, "tok": 5}}}
        self.p.write_text(json.dumps({"days": {"2020-01-01": yesterday}}))
        self.be._record_spend(0.04, keyed=True, sid=OWNER)                  # after midnight, same owner
        days = json.loads(self.p.read_text())["days"]
        self.assertAlmostEqual(days["2020-01-01"]["bySid"][OWNER]["usd"], 1.0, msg="yesterday untouched")
        self.assertAlmostEqual(days[self._today()]["bySid"][OWNER]["usd"], 0.04,
                               msg="today's bucket bills the same owner — no phantom split at midnight")

    def test_legacy_rows_and_sidless_folds_stay_lossless(self):
        # a pre-T100 bucket (no bySid) folds cleanly, and a sid-less fold never drops attribution
        # already there (lossless legacy, the T18 discipline)
        self.p.write_text(json.dumps({"days": {self._today(): {"usd": 1.0, "turns": 3}}}))
        self.be._record_spend(0.02, keyed=True, sid="aaaa1111-spend-attr-3")
        d = json.loads(self.p.read_text())["days"][self._today()]
        self.assertAlmostEqual(d["usd"], 1.02)
        self.assertAlmostEqual(d["bySid"]["aaaa1111-spend-attr-3"]["usd"], 0.02,
                               msg="attribution begins mid-history without touching the legacy totals")
        self.be._record_spend(0.01)   # a sid-less caller
        d = json.loads(self.p.read_text())["days"][self._today()]
        self.assertAlmostEqual(d["usd"], 1.03)
        self.assertAlmostEqual(d["bySid"]["aaaa1111-spend-attr-3"]["usd"], 0.02,
                               msg="the sid-less fold carried the existing bySid forward")

    def test_by_sid_prunes_with_its_bucket(self):
        # the maps live INSIDE the buckets, so the 90d prune takes them with it — no second ledger
        # to sweep and no orphaned attribution
        days = {"2020-04-%02d" % (i % 30 + 1): {"usd": 1, "turns": 1,
                                                "bySid": {"aaaa1111-spend-attr-4": {"usd": 1, "turns": 1, "tok": 0}}}
                for i in range(30)}
        days.update({"2020-%02d-01" % (m + 1): {"usd": 1, "turns": 1} for m in range(12)})
        days.update({"2021-%02d-01" % (m + 1): {"usd": 1, "turns": 1} for m in range(12)})
        days.update({"2022-%02d-%02d" % (m + 1, d + 1): {"usd": 1, "turns": 1}
                     for m in range(12) for d in range(4)})
        self.assertGreater(len(days), 90, "the fixture really overflows the window")
        self.p.write_text(json.dumps({"days": days}))
        self.be._record_spend(0.01, sid="aaaa1111-spend-attr-5")
        kept = json.loads(self.p.read_text())["days"]
        self.assertLessEqual(len(kept), 90)
        self.assertIn(self._today(), kept)
        self.assertNotIn("2020-04-01", kept, "the oldest bucket left — and its bySid map with it, atomically")
        self.assertIn("bySid", kept[self._today()])

    def test_result_message_records_and_the_kernel_serves_it(self):
        src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                                "kernel", "sdk_backend.py")).read()
        self.assertIn("self.backend._record_spend(delta, turn_u, keyed=self.api_key_auth,", src,
                      "the settle folds THIS turn's cost DELTA and _turn_usage's token counts")
        self.assertIn("turn_u = self._turn_usage(msg)", src,
                      "tokens come from _turn_usage — the flat usage dict is per-turn and is never diffed")
        self.assertIn('mu = getattr(msg, "model_usage", None)', src,
                      "the cumulative modelUsage map is the counter the token watermarks diff")
        self.assertIn("sid=self.thread_of or self.sid)   # the rail's spend", src,
                      "a comment THREAD bills its OWNING session (T144); a plain session bills itself "
                      "(T100's per-session attribution, completed)")
        self.assertIn("self._seed_spend_watermarks()   # a fresh CLI process starts its cumulative counters at", src,
                      "each connect resets both watermarks with its new process, or seeds them from the resumed "
                      "transcript's cost-state record (the resume-guard tests below)")
        self.assertIn("self._last_cost_total = 0.0   # a fresh CLI process starts its cumulative cost at zero",
                      src, "the seed starts the cost watermark at zero")
        self.assertIn("self._last_usage_totals = {}  # and its cumulative token counters", src,
                      "and the token watermarks with it")
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "bin", "romp-kernel")) as f:
            ksrc = f.read()
        self.assertIn('if o.get("apiKey") or (not _claude_account() and (jd.STATE / "spend.json").exists()):',
                      ksrc, "_usage serves spend on the legacy marker OR a login-less machine with recorded spend")
        self.assertIn('"spend": _spend_windows(doc=doc)', ksrc)              # doc: the ledger parsed once per _usage() call (perf round 4 P18)
        self.assertIn("def _spend_windows(keyed_only=False, now=None, doc=None):", ksrc)   # keyed_only: the mixed-host API sum (test_session_auth)

    def _spend_session(self, sid="11111111-2222-3333-4444-bbbbbbbbbbbb", name="n", **reg):
        import asyncio
        s = sb.SdkSession(self.be, {"sid": sid, "name": name, "cwd": "/tmp", **reg})
        self.be._forward = lambda sess, msg: None
        self.be._turn_completed = lambda sid: None
        async def _noop(): pass
        s._do_refresh_context = _noop
        s._do_refresh_usage = _noop
        def run(r):
            async def go():
                s._on_message(r, _AssistantMessage, _ResultMessage, type("S", (), {}))
                await asyncio.sleep(0)
            asyncio.run(go())
        def day():
            return json.loads(self.p.read_text())["days"][self._today()]
        return s, run, day

    @staticmethod
    def _model_map(total_in, model="claude-x", out=0):
        return {model: {"inputTokens": total_in, "outputTokens": out, "cacheReadInputTokens": 0,
                        "cacheCreationInputTokens": 0, "webSearchRequests": 0, "costUSD": 0.0}}

    def test_cost_and_model_usage_are_running_totals_folded_as_deltas(self):
        """The CLI's total_cost_usd and its modelUsage map are CUMULATIVE per process — the CLI documents
        the map as cumulative like the cost: read the latest result, never sum results — so folding the
        raw values re-added the whole session-so-far on every turn (the dollars first: the user
        2026-08-08, who did not believe the bottom line; then the tokens). Fold deltas for both; reset
        the watermarks with each new CLI process; treat a shrunken counter as a reset we missed. The
        flat `usage` dict rides every result as the TURN's own total and, with the map present, is
        neither summed nor diffed — the map governs."""
        s, run, day = self._spend_session()
        def _result(total, map_in, turn_in):
            r = _ResultMessage()
            r.total_cost_usd = total
            r.model_usage = self._model_map(map_in)
            r.usage = {"input_tokens": 9999}         # deliberately NOT the map's delta: if the flat dict were read
            return r                                 # or summed, tokIn would show it (review fold on #956)
        run(_result(1.0, 100, 100))    # first turn of the process: delta = the whole counter
        run(_result(2.5, 140, 40))     # second turn: deltas = 1.5 / 40 tokens, NOT another 2.5 / 140
        d = day()
        self.assertAlmostEqual(d["usd"], 2.5, msg="two turns fold to the process total, never more")
        self.assertEqual(d["tokIn"], 140, "tokens fold as deltas of the modelUsage running total")
        self.assertEqual(d["turns"], 2)
        s._last_cost_total = 0.0       # the connect reset: a fresh CLI process starts at zero…
        s._last_usage_totals = {}      # …on both counters
        run(_result(0.8, 30, 30))
        self.assertAlmostEqual(day()["usd"], 3.3)
        self.assertEqual(day()["tokIn"], 170)
        run(_result(0.5, 20, 20))      # a counter BELOW the watermark = a reset we missed → fold it whole
        self.assertAlmostEqual(day()["usd"], 3.8)
        self.assertEqual(day()["tokIn"], 190)

    def test_a_clear_resets_the_watermarks_on_the_lastsid_flip_even_when_the_new_counter_is_higher(self):
        # the /clear reset used to be inferred only from a counter that fell BELOW the watermark; a first
        # post-clear turn larger than the whole pre-clear total was diffed against the old watermark and
        # under-counted. The lastSid flip with `clearing` set IS the reset event (review find on #956,
        # 2026-09-07): both watermarks go to zero there, so the next result folds whole.
        s, run, day = self._spend_session()
        def _result(total, map_in):
            r = _ResultMessage(); r.total_cost_usd = total; r.model_usage = self._model_map(map_in)
            r.usage = {"input_tokens": 9999}; return r
        run(_result(1.0, 100))
        self.assertEqual(day()["tokIn"], 100)
        s._clearing = True                                    # a /clear was delivered…
        class _Init:                                          # …and the CLI's init lands on a NEW fsid
            subtype = "init"
            data = {"session_id": "11111111-2222-3333-4444-cccccccccccc", "model": "claude-x"}
        import asyncio
        async def go():
            s._on_message(_Init(), _AssistantMessage, _ResultMessage, _Init)
            await asyncio.sleep(0)
        asyncio.run(go())
        self.assertEqual((s._last_cost_total, s._last_usage_totals), (0.0, {}), "reset on the event, not on a guess")
        run(_result(2.0, 150))                                # HIGHER than the old watermark: the guess would diff it
        self.assertEqual(day()["tokIn"], 250, "folded whole after the clear, not 150 - 100")
        self.assertAlmostEqual(day()["usd"], 3.0)

    def test_the_model_usage_map_sums_across_models_and_all_four_kinds(self):
        # a mid-process model switch keeps BOTH models' running totals in the map — the process total
        # is their sum, and every kind (in / out / cache read / cache write) folds
        s, run, day = self._spend_session()
        r = _ResultMessage(); r.total_cost_usd = 1.0
        r.model_usage = {"claude-a": {"inputTokens": 10, "outputTokens": 20, "cacheReadInputTokens": 1000, "cacheCreationInputTokens": 60}}
        run(r)
        r2 = _ResultMessage(); r2.total_cost_usd = 2.0
        r2.model_usage = {"claude-a": {"inputTokens": 10, "outputTokens": 20, "cacheReadInputTokens": 1000, "cacheCreationInputTokens": 60},
                          "claude-b": {"inputTokens": 5, "outputTokens": 7, "cacheReadInputTokens": 300, "cacheCreationInputTokens": 9}}
        run(r2)
        d = day()
        self.assertEqual((d["tokIn"], d["tokOut"], d["tokCacheR"], d["tokCacheW"]), (15, 27, 1300, 69))
        self.assertEqual(d["turns"], 2)

    def test_the_flat_usage_dict_is_the_turns_own_total_and_folds_whole(self):
        """REGRESSION (the user 2026-09-06, who read the day's token count, asked how it was possible,
        and was right in the other direction: the ledger held roughly HALF the true count). The flat
        `usage` on a result is the TURN's own total — measured on CLI 2.1.263 against the transcript:
        turn one's three API calls summed, turn two's single call alone — yet the settle diffed it
        against the previous turn's like a running total, so a 100-token turn followed by a 140-token
        turn recorded 140, not 240, and every turn but the first lost the previous turn's worth (a
        SMALLER turn folded whole, by the shrunken-counter rule, which is why the loss looked random).
        Without a modelUsage map (an older CLI) the flat dict folds WHOLE; it is never diffed."""
        s, run, day = self._spend_session()
        def _result(total, turn_in):
            r = _ResultMessage()
            r.total_cost_usd = total
            r.usage = {"input_tokens": turn_in}
            return r
        run(_result(1.0, 100))
        run(_result(2.5, 140))
        self.assertEqual(day()["tokIn"], 240, "two turns of 100 and 140 tokens are 240 tokens — the bug recorded 140")
        run(_result(3.0, 60))
        self.assertEqual(day()["tokIn"], 300, "a turn smaller than the last folds whole too — there is no watermark on a per-turn figure")
        self.assertAlmostEqual(day()["usd"], 3.0, msg="the dollars stay a delta of their running total")
        self.assertEqual(s._last_usage_totals, {}, "the per-turn dict leaves the modelUsage watermarks untouched")

    def test_a_paid_result_without_model_usage_says_so_once_per_session(self):
        """The fallback above was SILENT: a paid result with no modelUsage map recorded the flat dict and
        the day's token columns became main-loop-only figures with nothing in the error center saying
        so. The field is present here (None, then an empty map), so the SDK has it and the CLI sent
        nothing on this result: that is THIS session's CLI's doing, so the line names the session and
        is said once per session, not once per turn. The count itself is unchanged."""
        s, run, day = self._spend_session(name="web")
        def _result(total, turn_in, mu):
            r = _ResultMessage()
            r.total_cost_usd = total
            r.usage = {"input_tokens": turn_in, "output_tokens": 20}
            r.model_usage = mu                    # the attribute exists: a current SDK, a CLI that sent no map
            return r
        run(_result(1.0, 100, None))
        run(_result(2.0, 140, {}))
        self.assertEqual(day()["tokIn"], 240, "each per-turn figure still lands whole")
        self.assertAlmostEqual(day()["usd"], 2.0)
        probs = [p["text"] for p in self.be.problems()]
        self.assertEqual(len(probs), 1, "one line per session, not one per turn: %r" % probs)
        self.assertIn("no modelUsage", probs[0])
        self.assertIn("spend (web)", probs[0], "the CLI cause is this session's, so the line names it")
        self.assertNotIn("model_usage field", probs[0], "the SDK remedy is not given for a CLI omission")
        self.assertTrue(s._usage_fallback_noted)
        self.assertFalse(self.be._usage_fallback_sdk_noted, "the CLI cause never spends the SDK cause's flag")
        run(_result(3.0, 50, self._model_map(5000)))     # the map is back: the count diffs it, nothing new to say
        self.assertEqual(day()["tokIn"], 5240)
        self.assertEqual(len(self.be.problems()), 1)
        # the scope is the session, not the backend: another session's CLI omission is said for that session
        api, run_api, _ = self._spend_session("11111111-2222-3333-4444-aaaaaaaaaaaa", name="api")
        run_api(_result(1.0, 10, None))
        probs = [p["text"] for p in self.be.problems()]
        self.assertEqual(len(probs), 2, "a second session says it once for itself: %r" % probs)
        self.assertIn("spend (api)", probs[1])
        self.assertTrue(api._usage_fallback_noted)
        self.assertEqual(day()["tokIn"], 5250)

    def test_a_log_callback_that_raises_on_the_notice_never_costs_the_turn_its_count(self):
        """The notice is said from inside the token count, ahead of the spend write and after the cost
        watermark moved: a log callback that raised there would propagate out of _turn_usage and the
        turn's dollars and tokens would go unrecorded for the sake of a line. The line is not worth the
        count. The ring row has landed by the time the callback runs, so the raise is swallowed and the
        count proceeds; the settle's own containment never has to hear of it."""
        s, run, day = self._spend_session(name="web")
        def badlog(m):
            if "no modelUsage" in str(m):
                raise OSError(32, "Broken pipe")
        self.be._log_cb = badlog                  # armed after construction (construction logs too)
        r = _ResultMessage()
        r.total_cost_usd = 1.0
        r.usage = {"input_tokens": 100, "output_tokens": 20}
        r.model_usage = None
        run(r)
        self.assertEqual(day()["tokIn"], 100, "the count landed although the notice's callback raised")
        self.assertAlmostEqual(day()["usd"], 1.0)
        probs = [p["text"] for p in self.be.problems()]
        self.assertEqual(len(probs), 1, "the ring row landed before the callback raised: %r" % probs)
        self.assertIn("spend (web)", probs[0])
        self.assertTrue(s._usage_fallback_noted)

    def test_an_sdk_whose_result_message_lacks_the_field_is_said_once_per_kernel_life(self):
        """A ResultMessage with no model_usage ATTRIBUTE at all is the imported SDK's doing: the current
        claude-agent-sdk declares the field (None when the CLI sends nothing), so a result without it
        means the kernel imported an older copy found on sys.path ahead of the dedicated venv's. One
        fact for every session this kernel runs, so the line names no session, names the remedy, and is
        said once per backend: two sessions and three paid turns produce one line, and a fresh
        SdkSession for a sid already seen (a dormant revive) adds nothing. The line names the copy by
        path (the remedy is then a path, not a search), read off the imported module: a stand-in module
        supplies one here, since this test interpreter has no SDK of its own."""
        import sys
        import types
        fake = types.ModuleType("claude_agent_sdk")
        fake.__file__ = "/synthetic/site-packages/claude_agent_sdk/__init__.py"
        saved = sys.modules.get("claude_agent_sdk")
        sys.modules["claude_agent_sdk"] = fake
        def restore():
            if saved is None:
                sys.modules.pop("claude_agent_sdk", None)
            else:
                sys.modules["claude_agent_sdk"] = saved
        self.addCleanup(restore)
        web, run_web, day = self._spend_session("11111111-2222-3333-4444-aaaaaaaaaaaa", name="web")
        api, run_api, _ = self._spend_session("11111111-2222-3333-4444-bbbbbbbbbbbb", name="api")
        def _result(total):
            r = _ResultMessage()                  # no model_usage attribute at all
            r.total_cost_usd = total
            r.usage = {"input_tokens": 100, "output_tokens": 20}
            return r
        r0 = _result(0)                           # a zero-cost result never reaches the token count (total > 0)
        run_web(r0)
        self.assertEqual(self.be.problems(), [])
        run_web(_result(1.0))
        run_api(_result(1.0))
        run_web(_result(2.0))
        self.assertEqual(day()["tokIn"], 300, "every turn's tokens still land, counted whole")
        probs = [p["text"] for p in self.be.problems()]
        self.assertEqual(len(probs), 1, "one line for one host-level remedy: %r" % probs)
        self.assertIn("model_usage field", probs[0])
        self.assertIn("romp-sdk-setup", probs[0], "the remedy names the venv the kernel should be importing from")
        self.assertIn(fake.__file__, probs[0], "the line names the copy the kernel imported, by path")
        self.assertTrue(probs[0].startswith("spend: "), "a host-level line names no session: %r" % probs[0])
        self.assertNotIn("spend (web)", probs[0])
        self.assertNotIn("spend (api)", probs[0])
        self.assertTrue(self.be._usage_fallback_sdk_noted)
        self.assertFalse(web._usage_fallback_noted, "the per-session flag is the CLI cause's, untouched")
        self.assertFalse(api._usage_fallback_noted)
        again, run_again, _ = self._spend_session("11111111-2222-3333-4444-aaaaaaaaaaaa", name="web")
        run_again(_result(1.0))
        self.assertEqual(len(self.be.problems()), 1, "a revive of a seen sid adds nothing")
        self.assertEqual(day()["tokIn"], 400)
        sys.modules.pop("claude_agent_sdk")       # no SDK loaded at all: the line still reads, and says so
        self.assertIn("(an unknown path)", sb.usage_fallback_notice("web", _result(1.0)))

    def test_the_keyed_sub_count_carries_the_by_kind_split(self):
        # the hover splits each window's tokens by kind; a mixed host's API readout sums ONLY the keyed
        # sub-counts, so the split must ride them too (2026-09-06) — and a login turn carries it forward
        self.be._record_spend(0.02, {"input_tokens": 100, "output_tokens": 40,
                                     "cache_read_input_tokens": 1000, "cache_creation_input_tokens": 60}, keyed=True)
        self.be._record_spend(0.03, {"input_tokens": 10, "output_tokens": 5}, keyed=False)
        k = json.loads(self.p.read_text())["days"][self._today()]["key"]
        self.assertEqual((k["tok"], k["tokIn"], k["tokOut"], k["tokCacheR"], k["tokCacheW"]), (1200, 100, 40, 1000, 60))
        self.assertEqual(k["turns"], 1, "the login turn is carried forward, not counted")

    # ── the resume guard: a CLI that restores its cost counters on resume must not have the whole
    # ── session's history recorded as one turn's spend
    _FSID = "22222222-3333-4444-5555-dddddddddddd"

    @staticmethod
    def _cost_state(total, model_usage, fsid=_FSID):
        """The CLI's `cost-state` transcript record: totalCostUSD and modelUsage, the two counters the
        settle diffs, beside the duration fields the record also carries."""
        return json.dumps({"type": "cost-state", "sessionId": fsid, "totalCostUSD": total,
                           "totalAPIDuration": 1, "totalDuration": 2, "startTime": 3,
                           "modelUsage": model_usage})

    @staticmethod
    def _costed(total, model_usage):
        r = _ResultMessage()
        r.total_cost_usd = total
        r.model_usage = model_usage
        r.usage = {"input_tokens": 9999}     # never read while the map is present: the map governs
        return r

    @staticmethod
    def _init_of(s):
        """Deliver an init SystemMessage to `s` the way the stream does (the class passed as the
        SystemMessage type is the double's own, so isinstance holds)."""
        class _Sys:
            def __init__(self, data): self.subtype = "init"; self.data = data
        def init(data):
            async def go():
                s._on_message(_Sys(data), _AssistantMessage, _ResultMessage, _Sys)
                await asyncio.sleep(0)
            asyncio.run(go())
        return init

    def _private_dir(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        return td.name

    def _resumed_session(self, transcript_lines, sid="11111111-2222-3333-4444-eeeeeeeeeeee", name="n"):
        """A session whose reg resumes _FSID from self.d, with that transcript on disk under a private
        CLAUDE_CONFIG_DIR (transcript_path reads the env at call time)."""
        env = mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": self._private_dir()})
        env.start()
        self.addCleanup(env.stop)
        p = Path(sb.transcript_path(self.d, self._FSID))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(transcript_lines) + "\n")
        return self._spend_session(sid, name=name, cwd=self.d, lastSid=self._FSID)

    def test_connect_seeds_the_watermarks_from_the_transcripts_last_cost_state(self):
        """The CLI's transcript loader files `cost-state` as last-wins and its writer emits totalCostUSD
        + modelUsage, the two counters the settle diffs. A CLI that restores them on resume reports its
        first total_cost_usd as the WHOLE session's history plus this turn; watermarks at zero would
        record that history as one turn's spend. Seeding from the record the CLI restores keeps the
        first delta this turn's own."""
        mu_old = {"claude-x": {"inputTokens": 400, "outputTokens": 40,
                               "cacheReadInputTokens": 9000, "cacheCreationInputTokens": 100}}
        mu = {"claude-x": {"inputTokens": 1000, "outputTokens": 200,
                           "cacheReadInputTokens": 50000, "cacheCreationInputTokens": 3000}}
        s, run, day = self._resumed_session([
            json.dumps({"type": "user", "uuid": "u1", "message": {"role": "user", "content": "hello"}}),
            self._cost_state(4.0, mu_old),                     # an earlier snapshot, superseded (last-wins)
            json.dumps({"type": "assistant", "uuid": "a1", "message": {"role": "assistant", "content": []}}),
            self._cost_state(12.5, mu),
            json.dumps({"type": "last-prompt", "lastPrompt": "x"}),   # uuid-less trailers after it are fine
        ])
        lines = []
        self.be._log_cb = lines.append
        seeded = lambda: [l for l in lines if "watermarks seeded" in l]
        s._seed_spend_watermarks()                             # the connect-time step
        self.assertEqual(s._last_cost_total, 12.5, "the LAST record's total is the seed")
        self.assertEqual(s._last_usage_totals, {"input_tokens": 1000, "output_tokens": 200,
                                                "cache_read_input_tokens": 50000,
                                                "cache_creation_input_tokens": 3000})
        self.assertTrue(s._spend_first_result)
        self.assertEqual(len(seeded()), 1, "the seed is said once, in the kernel log")
        self.assertIn("12.50", seeded()[0])
        self.assertEqual(self.be.problems(), [], "an info line, not a problem: nothing for the user to act on")
        # the restoring CLI's first result: history + this turn. Only THIS turn lands.
        run(self._costed(13.0, {"claude-x": {"inputTokens": 1500, "outputTokens": 260,
                                             "cacheReadInputTokens": 50000, "cacheCreationInputTokens": 3000}}))
        d = day()
        self.assertAlmostEqual(d["usd"], 0.5)
        self.assertEqual((d["tokIn"], d["tokOut"], d["tokCacheR"]), (500, 60, 0))
        self.assertFalse(s._spend_first_result)
        self.assertEqual(len(seeded()), 1, "the settle says nothing about the seed")
        # a CLI that wrote the record but did NOT restore: its own first total sits below the seed, so the
        # shrunken-counter rule records it whole. The common case stays right without knowing which CLI it is.
        s._seed_spend_watermarks()
        self.assertEqual(len(seeded()), 2, "each connect that seeds says so")
        run(self._costed(0.7, {"claude-x": {"inputTokens": 300}}))
        self.assertAlmostEqual(day()["usd"], 1.2)
        self.assertEqual(day()["tokIn"], 800)
        self.assertEqual(self.be.problems(), [])

    def test_no_cost_state_record_and_no_resume_target_leave_the_watermarks_at_zero(self):
        s, run, day = self._resumed_session([
            json.dumps({"type": "user", "uuid": "u1", "message": {"role": "user", "content": "hello"}}),
            json.dumps({"type": "assistant", "uuid": "a1", "message": {"role": "assistant", "content": [],
                                                                        "usage": {"input_tokens": 5}}}),
        ])
        s._last_cost_total, s._last_usage_totals = 9.0, {"input_tokens": 9}   # stale from the old process
        s._seed_spend_watermarks()
        self.assertEqual((s._last_cost_total, s._last_usage_totals), (0.0, {}),
                         "no record: a fresh process starts at zero, as every resume does on the CLI as probed")
        run(self._costed(1.5, {"claude-x": {"inputTokens": 100}}))
        self.assertAlmostEqual(day()["usd"], 1.5, msg="the first result is recorded whole")
        self.assertEqual(day()["tokIn"], 100)
        s.resume_sid = None                                    # no resume target at all
        s._last_cost_total = 3.0
        s._seed_spend_watermarks()
        self.assertEqual((s._last_cost_total, s._last_usage_totals, s._spend_first_result), (0.0, {}, True))

    def test_last_cost_state_reads_backwards_across_chunk_edges_and_takes_the_last_valid_record(self):
        p = Path(self._private_dir()) / "t.jsonl"
        filler = json.dumps({"type": "user", "uuid": "u", "message": {"role": "user", "content": "x" * 900}})
        mu = {"m": {"inputTokens": 7, "outputTokens": 3}}
        # a valid record early in the file, then ~200 KB with no marker: the scan walks several 64 KB
        # chunks back to it. A later record with an unusable total is skipped, not taken as "none".
        lines = [filler, self._cost_state(2.25, mu)] + [filler] * 220
        lines.append(json.dumps({"type": "cost-state", "totalCostUSD": "not a number", "modelUsage": mu}))
        p.write_text("\n".join(lines) + "\n")
        self.assertEqual(sb.last_cost_state(str(p)), {"total": 2.25, "tokens": {
            "input_tokens": 7, "output_tokens": 3, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}})
        # a record STRADDLING a chunk edge: the tail after it is 21 bytes short of a chunk, so the edge of
        # the last chunk (read first) falls inside the record, whose two halves land in different chunks
        rec = self._cost_state(5.5, mu)
        head = "\n".join([filler] * 80) + "\n"
        tail = "x" * ((1 << 16) - 22) + "\n"
        p.write_text(head + rec + "\n" + tail)
        size = p.stat().st_size
        start = len(head.encode())
        edge = size - (1 << 16)
        self.assertTrue(start < edge < start + len(rec), "the premise: the chunk edge falls inside the record")
        self.assertEqual(sb.last_cost_state(str(p))["total"], 5.5, "a line split by the chunk edge is reassembled")
        # last-wins: two valid records take the later one; no trailing newline is fine
        p.write_text(self._cost_state(1.0, mu) + "\n" + self._cost_state(9.0, {}))
        self.assertEqual(sb.last_cost_state(str(p)), {"total": 9.0, "tokens": {}},
                         "an empty modelUsage seeds no token watermarks")
        # two models sum per field, the settle's own count of a result's map
        p.write_text(self._cost_state(3.0, {"a": {"inputTokens": 5, "cacheReadInputTokens": 10},
                                            "b": {"inputTokens": 6, "outputTokens": 1, "webSearchRequests": 4},
                                            "c": "not a map"}) + "\n")
        self.assertEqual(sb.last_cost_state(str(p))["tokens"], {
            "input_tokens": 11, "output_tokens": 1, "cache_read_input_tokens": 10, "cache_creation_input_tokens": 0})
        # a negative or non-finite total is unusable, like a non-number
        p.write_text(self._cost_state(-1.0, mu) + "\n")
        self.assertIsNone(sb.last_cost_state(str(p)))
        p.write_text('{"type": "cost-state", "totalCostUSD": NaN, "modelUsage": {}}\n')
        self.assertIsNone(sb.last_cost_state(str(p)))
        p.write_text('{"type": "cost-state", "totalCostUSD": Infinity, "modelUsage": {}}\n')
        self.assertIsNone(sb.last_cost_state(str(p)))
        self.assertIsNone(sb.last_cost_state(str(p.parent / "missing.jsonl")))
        p.write_text("")
        self.assertIsNone(sb.last_cost_state(str(p)))
        p.write_text(filler + "\n")
        self.assertIsNone(sb.last_cost_state(str(p)), "no record: None, never a zero seed")

    def _reads_through_a_stand_in(self, chunk_type=bytes):
        """Route the module's `open` through a stand-in file object for this test: it records the length
        of each read and hands the bytes back as `chunk_type`, so a test can see how the scan reads the
        file and, with a bytes subclass, what the scan does to what it read. Restored at tearDown."""
        reads, real_open = [], open

        class Reader:
            def __init__(self, f): self.f = f
            def __enter__(self): return self
            def __exit__(self, *exc): return self.f.__exit__(*exc)
            def seek(self, *a): return self.f.seek(*a)
            def tell(self): return self.f.tell()
            def read(self, n=-1):
                b = self.f.read(n)
                reads.append(len(b))
                return chunk_type(b)

        patch = mock.patch.object(sb, "open", lambda p, *a, **k: Reader(real_open(p, *a, **k)), create=True)
        patch.start()
        self.addCleanup(patch.stop)
        return reads

    @staticmethod
    def _line_of(length, **fields):
        """A JSON line of exactly `length` bytes: `fields`, then a `pad` of x's that makes up the length."""
        bare = json.dumps({**fields, "pad": ""})
        return json.dumps({**fields, "pad": "x" * (length - len(bare))})

    def _record_line(self, total, length, mu):
        """A record-shaped line of exactly `length` bytes: last_cost_state takes it when it is short enough."""
        return self._line_of(length, type="cost-state", sessionId=self._FSID, totalCostUSD=total, modelUsage=mu)

    def test_last_cost_state_reassembles_a_long_line_and_finds_the_record_before_it(self):
        """A transcript line is one JSON record, and a tool result can make one several MB long. The
        scan walks such a line back to its first byte in 64 KB reads, covering the bounded tail once
        and nothing more, reassembles it, and takes the record before it."""
        p = Path(self._private_dir()) / "t.jsonl"
        mu = {"m": {"inputTokens": 7, "outputTokens": 3}}
        long_line = json.dumps({"type": "user", "uuid": "u", "message": {"role": "user", "content": "x" * (3 << 20)}})
        after = json.dumps({"type": "last-prompt", "lastPrompt": "x"})
        p.write_text(self._cost_state(2.25, mu) + "\n" + long_line + "\n" + after + "\n")
        reads = self._reads_through_a_stand_in()
        self.assertEqual(sb.last_cost_state(str(p))["total"], 2.25)
        size = p.stat().st_size
        self.assertEqual(sum(reads), size, "the whole file, under the 8 MB bound, is read once")
        self.assertEqual(len(reads), -(-size // (1 << 16)), "in chunks of 64 KB, the head chunk shorter")
        self.assertLessEqual(max(reads), 1 << 16)

    def test_the_bound_reads_the_same_tail_and_drops_the_line_it_cuts_through(self):
        """The scan reads the last `scan_bytes` of the file and nothing before them: a record older than
        that is absent, and the line the bound cuts through is a fragment, never joined, so a record
        whose first byte the bound lands on is absent too, and found once the bound reaches the newline
        before it. This held before the pieces were collected in a list and holds after: a guard on the
        range read."""
        p = Path(self._private_dir()) / "t.jsonl"
        mu = {"m": {"inputTokens": 7, "outputTokens": 3}}
        filler = json.dumps({"type": "user", "uuid": "u", "message": {"role": "user", "content": "x" * 900}})
        bound = 3 << 16
        rec = self._cost_state(2.25, mu)
        p.write_text(rec + "\n" + (filler + "\n") * 300)          # about 290 KB after the record
        reads = self._reads_through_a_stand_in()
        self.assertIsNone(sb.last_cost_state(str(p), scan_bytes=bound), "older than the bound: absent")
        self.assertEqual(sum(reads), bound, "the last scan_bytes of the file, and no more")
        # the bound lands exactly on the record's first byte: the record is the cut line, a fragment; one
        # byte more reaches the newline before it, and the record is a whole line again
        tail = self._line_of(bound - len(rec) - 2, type="user", uuid="u", message={"role": "user"})
        p.write_text((filler + "\n") * 5 + rec + "\n" + tail + "\n")
        self.assertIsNone(sb.last_cost_state(str(p), scan_bytes=bound))
        self.assertEqual(sb.last_cost_state(str(p), scan_bytes=bound + 1)["total"], 2.25)

    def test_a_line_longer_than_the_cap_is_not_a_record_and_the_earlier_record_wins(self):
        """A cost-state record is under 1 KB. A line longer than last_cost_state's cap (4 MB) is skipped
        without being reassembled, even when its text would parse as a record: the record before it
        wins, and with none before it the answer is None, as for a file that has no record. The rule is
        exact on the length, and the same for a line the scan reassembles from the pieces of many chunks
        as for one whole inside a chunk: a line AT the cap is still a record, joined from its pieces in
        file order, and one byte longer is skipped."""
        p = Path(self._private_dir()) / "t.jsonl"
        mu = {"m": {"inputTokens": 7, "outputTokens": 3}}
        filler = json.dumps({"type": "user", "uuid": "u", "message": {"role": "user", "content": "x" * 900}})
        cap = 4 << 20
        huge = self._record_line(7.0, cap + (1 << 20), mu)        # record-shaped, well past the cap
        p.write_text(self._cost_state(1.0, mu) + "\n" + huge + "\n")
        self.assertEqual(sb.last_cost_state(str(p))["total"], 1.0, "the line past the cap is not a record")
        p.write_text(huge + "\n")
        self.assertIsNone(sb.last_cost_state(str(p)), "skipped without an exception; no record remains")
        p.write_text(huge)                                    # the too-long line is the file's head, unterminated
        self.assertIsNone(sb.last_cost_state(str(p)))
        p.write_text(huge + "\n" + self._cost_state(3.0, mu) + "\n")
        self.assertEqual(sb.last_cost_state(str(p))["total"], 3.0, "a record after it is taken as usual")
        # exactly the cap, spanning about 65 chunks between two other lines: a record, reassembled from its
        # pieces in file order (out of order it would not parse); one byte longer: skipped, and the record
        # before it wins
        for length, total in ((cap, 2.5), (cap + 1, 1.0)):
            p.write_text(self._cost_state(1.0, mu) + "\n" + self._record_line(2.5, length, mu) + "\n" + filler + "\n")
            self.assertEqual(sb.last_cost_state(str(p))["total"], total, f"a line of {length} bytes")
        # the cap is the parameter. A record-shaped line the scan carries in three pieces, one per chunk
        # (it begins on a chunk edge: the file's tail from its first byte is three chunks exactly), is a
        # record at a cap of its own length and skipped at one byte less, where the record before it wins
        three = self._record_line(6.0, 3 * (1 << 16) - 1, mu)
        p.write_text(self._cost_state(1.0, mu) + "\n" + three + "\n")
        self.assertEqual(sb.last_cost_state(str(p), max_line=len(three))["total"], 6.0)
        self.assertEqual(sb.last_cost_state(str(p), max_line=len(three) - 1)["total"], 1.0)
        # and for a line the scan never carries: the head piece alone in the file, and a line whole inside a
        # chunk between two others
        rec = self._cost_state(2.0, mu)
        for text in (rec + "\n", filler + "\n" + rec + "\n" + filler + "\n"):
            p.write_text(text)
            self.assertEqual(sb.last_cost_state(str(p), max_line=len(rec))["total"], 2.0)
            self.assertIsNone(sb.last_cost_state(str(p), max_line=len(rec) - 1))

    def test_the_scan_copies_a_line_once_and_holds_at_most_the_cap_however_long_the_line(self):
        """Linear by construction, pinned without a clock. The pieces of a line are collected as the
        chunks arrive and joined once at the newline that opens the line, so no chunk is ever
        concatenated onto the carried fragment (that copied the fragment again on every chunk, a cost
        quadratic in the line). A line past the cap is dropped as it arrives, so on such a line the scan
        holds at most the cap plus a few chunks at any moment; a reader that keeps the line, or re-copies
        it per chunk, peaks at one to three times the 7 MB line here. A line one byte past the cap is
        never joined either, though every piece of it was kept: joined, it would be held twice."""
        p = Path(self._private_dir()) / "t.jsonl"
        mu = {"m": {"inputTokens": 7, "outputTokens": 3}}
        filler = json.dumps({"type": "user", "uuid": "u", "message": {"role": "user", "content": "x" * 900}})
        adds = []

        class Chunk(bytes):
            """What the scan read, watching for a concatenation onto it."""
            def __add__(self, other): adds.append(len(self) + len(other)); return bytes(self) + other
            def __radd__(self, other): adds.append(len(self) + len(other)); return other + bytes(self)

        reads = self._reads_through_a_stand_in(Chunk)

        def scan():
            """The scan's answer and the process's growth in bytes over it, measured from what the process
            held as the scan began (a tracer already running, PYTHONTRACEMALLOC, then adds nothing)."""
            tracing = tracemalloc.is_tracing()
            if not tracing:
                tracemalloc.start()
            try:
                tracemalloc.reset_peak()
                held = tracemalloc.get_traced_memory()[0]
                rec = sb.last_cost_state(str(p))
                return rec, tracemalloc.get_traced_memory()[1] - held
            finally:
                if not tracing:
                    tracemalloc.stop()

        big = json.dumps({"type": "user", "uuid": "u", "message": {"role": "user", "content": "x" * (7 << 20)}})
        p.write_text(self._cost_state(2.25, mu) + "\n" + big + "\n" + filler + "\n")
        rec, peak = scan()
        self.assertEqual(rec["total"], 2.25, "the record before the 7 MB line is found")
        self.assertEqual(sum(reads), p.stat().st_size, "the range read is the same bounded tail")
        self.assertEqual(adds, [], "no chunk is concatenated onto: a line's pieces are joined once")
        self.assertLess(peak, (4 << 20) + (2 << 20), "held: the 4 MB cap plus chunks, never the 7 MB line")
        over = self._record_line(7.0, (4 << 20) + 1, mu)
        p.write_text(self._cost_state(2.25, mu) + "\n" + over + "\n" + filler + "\n")
        rec, peak = scan()
        self.assertEqual(rec["total"], 2.25, "one byte past the cap: not a record")
        self.assertEqual(adds, [])
        self.assertLess(peak, (4 << 20) + (2 << 20), "held: its pieces, and no joined line beside them")

    def test_a_first_result_after_connect_above_the_single_turn_mark_is_recorded_and_traced_as_info(self):
        """On the CLI as probed a resumed process starts its cost counters at zero, so a first delta above
        the mark is the turn's own cost: recorded as is and traced in the kernel log, NOT a problem (a
        problem row for a right figure sends the user to check a record that is correct)."""
        lines = []
        self.be._log_cb = lines.append
        traced = lambda: [l for l in lines if "first result after connect" in l]
        s, run, day = self._spend_session()
        s._seed_spend_watermarks()                             # no resume target: zero watermarks
        run(self._costed(5.0, {"m": {"inputTokens": 10}}))
        self.assertEqual(traced(), [], "an ordinary first turn says nothing")
        s._seed_spend_watermarks()                             # a reconnect
        run(self._costed(250.0, {"m": {"inputTokens": 20}}))
        self.assertEqual(len(traced()), 1)
        self.assertIn("250.00", traced()[0])
        self.assertIn("Recorded as is", traced()[0])
        self.assertEqual(self.be.problems(), [], "an info line: the figure is right, nothing to act on")
        self.assertAlmostEqual(day()["usd"], 255.0, msg="recorded anyway; the record drops nothing")
        run(self._costed(500.0, {"m": {"inputTokens": 30}}))   # a 250 USD delta on the NEXT result
        self.assertEqual(len(traced()), 1, "only the FIRST result after a connect is checked")
        self.assertAlmostEqual(day()["usd"], 505.0)

    def test_init_correcting_the_cwd_re_seeds_the_watermarks_before_the_first_result(self):
        """The connect-time seed reads the transcript under the REGISTRY's cwd; the CLI loads the one
        under ITS cwd, which init reports (the same keying: transcript_path realpaths the string, so a
        create-time variant such as a wrong case holds no transcript). Adopting the CLI's cwd re-seeds
        from the file the CLI opened while no result has settled, and never afterwards: resetting the
        watermarks mid-process would count the cumulative counters whole again."""
        mu = {"m": {"inputTokens": 1000, "outputTokens": 200}}
        s, run, day = self._resumed_session([self._cost_state(12.5, mu)])   # the record lives under self.d
        variant = self._private_dir()
        s.cwd = variant                                        # the registry's variant: no transcript there
        sb.write_reg(self.d, s.sid, {"sid": s.sid, "name": "n", "cwd": variant, "alive": True, "lastSid": self._FSID})
        s._seed_spend_watermarks()
        self.assertEqual((s._last_cost_total, s._last_usage_totals), (0.0, {}), "nothing under the variant")
        init = self._init_of(s)
        init({"cwd": self.d, "session_id": self._FSID, "model": "claude-x"})
        self.assertEqual(s.cwd, self.d)
        self.assertEqual(sb.read_reg(self.d, s.sid)["cwd"], self.d)
        self.assertEqual(s._last_cost_total, 12.5, "re-seeded from the file under the CLI's cwd")
        self.assertEqual(s._last_usage_totals["input_tokens"], 1000)
        self.assertTrue(s._spend_first_result)
        run(self._costed(13.0, {"m": {"inputTokens": 1500, "outputTokens": 260}}))
        self.assertAlmostEqual(day()["usd"], 0.5, msg="the first result records only this turn")
        self.assertEqual(day()["tokIn"], 500)
        # a cwd correction AFTER a settle (none is expected; the guard is the point) leaves them alone
        init({"cwd": self._private_dir(), "session_id": self._FSID, "model": "claude-x"})
        self.assertEqual(s._last_cost_total, 13.0, "no re-seed once a result has settled")
        run(self._costed(13.2, {"m": {"inputTokens": 1600, "outputTokens": 260}}))
        self.assertAlmostEqual(day()["usd"], 0.7)
        self.assertEqual(day()["tokIn"], 600)

    def test_an_init_that_lands_a_new_fsid_and_corrects_the_cwd_re_seeds_from_the_file_the_cli_loaded(self):
        """One init can both land a NEW fsid (a resume the CLI continues under a fresh file; a rewind via
        --resume-session-at is an in-place branch on the same fsid and never flips it) and correct the
        cwd. The flip moves resume_sid to the file the CLI will WRITE, which holds no record yet; a CLI
        that restores its counters took them from the file it LOADED, the old fsid's. The re-seed reads
        that one."""
        new_fsid = "33333333-4444-5555-6666-ffffffffffff"
        mu = {"m": {"inputTokens": 1000, "outputTokens": 200}}
        s, run, day = self._resumed_session([self._cost_state(12.5, mu)])   # the OLD fsid's record, under self.d
        variant = self._private_dir()
        s.cwd = variant                                        # the registry's variant: no transcript there
        sb.write_reg(self.d, s.sid, {"sid": s.sid, "name": "n", "cwd": variant, "alive": True, "lastSid": self._FSID})
        s._seed_spend_watermarks()
        self.assertEqual(s._last_cost_total, 0.0, "nothing under the variant")
        self._init_of(s)({"cwd": self.d, "session_id": new_fsid, "model": "claude-x"})
        self.assertEqual((s.cwd, s.resume_sid), (self.d, new_fsid), "cwd adopted, fsid flipped")
        self.assertEqual(sb.read_reg(self.d, s.sid)["lastSid"], new_fsid)
        self.assertEqual(s._last_cost_total, 12.5, "re-seeded from the OLD fsid's file under the CLI's cwd")
        self.assertEqual(s._last_usage_totals["input_tokens"], 1000)
        run(self._costed(13.0, {"m": {"inputTokens": 1500, "outputTokens": 260}}))
        self.assertAlmostEqual(day()["usd"], 0.5, msg="the restoring CLI's first result records only this turn")
        self.assertEqual(day()["tokIn"], 500)
        # a flip WITHOUT a cwd correction re-seeds nothing: the connect-time seed read the loaded file already
        s2, _, _ = self._spend_session("11111111-2222-3333-4444-abababababab", name="n2", cwd=self.d, lastSid=self._FSID)
        sb.write_reg(self.d, s2.sid, {"sid": s2.sid, "name": "n2", "cwd": self.d, "alive": True, "lastSid": self._FSID})
        s2._seed_spend_watermarks()
        self.assertEqual(s2._last_cost_total, 12.5)
        # the record changes under the seed: a re-seed here would read 99.0
        Path(sb.transcript_path(self.d, self._FSID)).write_text(self._cost_state(99.0, mu) + "\n")
        self._init_of(s2)({"cwd": self.d, "session_id": new_fsid, "model": "claude-x"})
        self.assertEqual((s2.resume_sid, s2._last_cost_total), (new_fsid, 12.5), "flipped, seed kept: not re-read")

    def test_an_init_that_ends_a_clear_and_corrects_the_cwd_keeps_the_watermarks_at_zero(self):
        """A /clear's init flip zeroes the watermarks on the event: the CLI zeroed its counters at that
        instant. When the same init also corrects the cwd, the re-seed stands down. The file the CLI
        loaded may carry a record (the CLI's writer appends one to the conversation a /clear abandons),
        and seeding from it would hold the watermarks above counters that are at zero."""
        mu = {"m": {"inputTokens": 1000, "outputTokens": 200}}
        s, run, day = self._resumed_session([self._cost_state(12.5, mu)])
        variant = self._private_dir()
        s.cwd = variant
        sb.write_reg(self.d, s.sid, {"sid": s.sid, "name": "n", "cwd": variant, "alive": True, "lastSid": self._FSID})
        s._seed_spend_watermarks()
        self.assertEqual(s._last_cost_total, 0.0)
        new_fsid = "33333333-4444-5555-6666-ffffffffffff"
        # planted so the stand-down is observable: a re-seed that fell back to the NEW fsid's file would read 7.0
        p = Path(sb.transcript_path(self.d, new_fsid))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self._cost_state(7.0, mu, fsid=new_fsid) + "\n")
        s._clearing = True                                     # a /clear was delivered on this connection...
        self._init_of(s)({"cwd": self.d, "session_id": new_fsid, "model": "claude-x"})
        self.assertEqual(s.cwd, self.d, "...and its init lands a new fsid under the CLI's cwd")
        self.assertEqual((s._last_cost_total, s._last_usage_totals), (0.0, {}),
                         "the clear's zero stands: neither the abandoned conversation's record nor the new file is read")
        run(self._costed(13.0, {"m": {"inputTokens": 1500}}))
        self.assertAlmostEqual(day()["usd"], 13.0, msg="the first post-clear turn is the whole counter")
        self.assertEqual(day()["tokIn"], 1500)


class RewindFiles(unittest.TestCase):
    """The bubble's restore-files affordance rides the SDK's designed rewind_files control request (the
    user 2026-08-04): the WORKSPACE goes back to its state before a user message; the conversation is
    untouched (edit/delete cover that). Checkpointing is enabled on every session so the checkpoints
    exist. A refusal returns False so the kernel warns — never a silent no-op; tmux inherits the ABC's
    False. No SDK import needed here (dispatch is deferred), so this runs in every venv."""

    def _sess(self):
        d = tempfile.mkdtemp()
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None)
        return be, sb.SdkSession(be, {"sid": "11111111-2222-3333-4444-555555555555", "name": "n", "cwd": d})

    def test_dispatches_on_the_loop_when_connected(self):
        _, sess = self._sess()
        dispatched = []
        sess.loop = type("L", (), {"call_soon_threadsafe": staticmethod(lambda cb: dispatched.append(cb))})()
        sess.client = object()
        self.assertTrue(sess.request_rewind_files("aaaa-uuid"))
        self.assertEqual(len(dispatched), 1, "the control request is scheduled on the loop thread")

    def test_refuses_without_a_client_or_uuid(self):
        _, sess = self._sess()
        self.assertFalse(sess.request_rewind_files("aaaa-uuid"), "no connected client → False → kernel warns")
        sess.loop = object(); sess.client = object()
        self.assertFalse(sess.request_rewind_files(""), "no uuid → refuse, never a blind restore")

    def test_backend_routes_by_sid_and_tmux_defaults_false(self):
        be, _ = self._sess()
        self.assertFalse(be.rewind_files("no-such-sid", "aaaa-uuid"))
        spec_src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                                     "kernel", "session_backend.py")).read()
        self.assertIn("def rewind_files(self, sid: str, uuid: str) -> bool:", spec_src)
        self.assertIn("return False", spec_src.split("def rewind_files", 1)[1][:600],
                      "the ABC default is False — tmux has no such control")

    def test_checkpointing_is_on_and_the_kernel_op_warns_on_refusal(self):
        base = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        sdk_src = open(os.path.join(base, "kernel", "sdk_backend.py")).read()
        self.assertIn("enable_file_checkpointing=True", sdk_src,
                      "every session checkpoints, so any user message is a restore point")
        with open(os.path.join(base, "bin", "romp-kernel")) as f:
            src = f.read()
        self.assertIn('"rewindFiles"', src[src.index("ID_OPS"):src.index("ID_OPS") + 700])
        self.assertIn('elif t == "rewindFiles" and msg.get("uuid"):', src)
        self.assertIn("Couldn't restore files", src, "a refusal warns the user — never a silent no-op")


@unittest.skipUnless(_HAVE_SDK, "claude_agent_sdk not installed")
class OptionsAssembly(unittest.TestCase):
    """_options must use the SDK's DESIGNED option fields, not the extra_args CLI-flag escape hatch (the user
    2026-06-24: implement things the way the SDK designed them). The romp harness prompt is appended via
    system_prompt={"type":"preset","preset":"claude_code","append":...} (types.py SystemPromptPreset) — the
    documented field — NOT extra_args={"append-system-prompt"}, the passthrough reserved for flags with no field."""

    def setUp(self):
        self.d = tempfile.mkdtemp()

    def _sess(self, be):
        return sb.SdkSession(be, {"sid": "11111111-2222-3333-4444-555555555555",
                                  "name": "n", "cwd": self.d, "mode": "acceptEdits"})

    def test_append_prompt_uses_designed_system_prompt_not_extra_args(self):
        p = os.path.join(self.d, "append.txt")
        with open(p, "w") as f:
            f.write("ROMP HARNESS PROMPT")
        be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None, append_prompt_path=p)
        opts = be._options(self._sess(be), _sdk.ClaudeAgentOptions)
        self.assertEqual(opts.system_prompt,
                         {"type": "preset", "preset": "claude_code", "append": "ROMP HARNESS PROMPT"},
                         "harness prompt appended via the designed system_prompt preset field")
        self.assertNotIn("append-system-prompt", opts.extra_args or {},
                         "must NOT route the append through the extra_args CLI-flag escape hatch")

    def test_no_append_prompt_leaves_the_default_system_prompt(self):
        be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)   # no append_prompt_path
        opts = be._options(self._sess(be), _sdk.ClaudeAgentOptions)
        self.assertIsNone(opts.system_prompt, "no harness prompt → leave the CLI's default system prompt")

    def test_ultracode_maps_to_xhigh_plus_the_settings_key(self):
        # "ultracode" (the user 2026-08-04) is not a typed EffortLevel: the CLI's documented per-session
        # hook is the `ultracode` settings key (--settings / flag-settings layer), and ultracode IS xhigh
        # plus standing workflow orchestration — so the typed field carries xhigh and the key rides a
        # settings file. Never through extra_args.
        be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)
        sess = self._sess(be)
        sess.effort = "ultracode"
        opts = be._options(sess, _sdk.ClaudeAgentOptions)
        self.assertEqual(opts.effort, "xhigh", "the typed field carries the effort half of ultracode")
        self.assertTrue(opts.settings and sb.FLAG_SETTINGS_DIR in opts.settings)
        with open(opts.settings) as f:
            self.assertEqual(json.load(f), {"ultracode": True})
        self.assertNotIn("effort", opts.extra_args or {})

    def test_plain_efforts_pass_through_with_no_settings_file(self):
        be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)
        sess = self._sess(be)
        sess.effort = "max"
        opts = be._options(sess, _sdk.ClaudeAgentOptions)
        self.assertEqual(opts.effort, "max")
        self.assertIsNone(opts.settings, "no ultracode and no fast mode → no flag-settings file")

    def test_fast_mode_rides_the_flag_settings_opt_in(self):
        # The CLI REFUSES fast mode to any non-interactive client ("Fast mode is not available in the
        # Agent SDK") unless `fastMode` is true in the flag-settings layer — options.settings is that
        # layer, and this key is the host's designed opt-in (verified against claude 2.1.224).
        be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)
        sess = self._sess(be)
        sess.fast_opt = True
        opts = be._options(sess, _sdk.ClaudeAgentOptions)
        self.assertTrue(opts.settings, "fast mode needs a flag-settings file to opt in through")
        with open(opts.settings) as f:
            self.assertEqual(json.load(f), {"fastMode": True})

    def test_ultracode_and_fast_mode_share_one_settings_file(self):
        # options.settings takes ONE path, so both keys must compose — an earlier shape wrote a fixed
        # single-key file and the second setting would have silently dropped the first.
        be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)
        sess = self._sess(be)
        sess.effort, sess.fast_opt = "ultracode", True
        opts = be._options(sess, _sdk.ClaudeAgentOptions)
        with open(opts.settings) as f:
            self.assertEqual(json.load(f), {"ultracode": True, "fastMode": True})

    def test_each_session_gets_its_own_flag_settings_file(self):
        # The file is per-sid, not one shared file: its content now VARIES by session, so a shared path
        # would hand one session's fast mode to every other session that reads it.
        be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)
        a, b = self._sess(be), self._sess(be)
        b.sid = "99999999-8888-7777-6666-555555555555"
        a.fast_opt, b.fast_opt = True, False
        b.effort = "ultracode"
        pa = be._options(a, _sdk.ClaudeAgentOptions).settings
        pb = be._options(b, _sdk.ClaudeAgentOptions).settings
        self.assertNotEqual(pa, pb, "two sessions, two settings files")
        with open(pa) as f:
            self.assertEqual(json.load(f), {"fastMode": True})
        with open(pb) as f:
            self.assertEqual(json.load(f), {"ultracode": True}, "b's file is untouched by a's fast mode")

    def test_ultracode_is_a_choice_everywhere_but_never_the_seeded_default(self):
        self.assertIn("ultracode", sb.EFFORT_LEVELS, "the SDK backend accepts the pick")
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "bin", "romp-kernel")) as f:
            self.assertIn('("low", "medium", "high", "xhigh", "max", "ultracode")', f.read(),
                          "the effort dropdown (kernel EFFORT_CHOICES) offers ultracode")
        # per-session by design (the CLI: "this session only") — picking it must not seed NEW sessions
        be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)
        sid = "11111111-2222-3333-4444-555555555555"
        sb.write_reg(self.d, sid, {"sid": sid, "name": "n", "cwd": self.d})
        self.assertTrue(be.set_effort(sid, "ultracode"))
        self.assertNotEqual(sb.read_sdk_defaults(self.d).get("effort"), "ultracode",
                            "ultracode never becomes the default for the next new session")
        self.assertEqual(sb.read_reg(self.d, sid)["effort"], "ultracode", "but THIS session keeps it")

    def test_raises_max_buffer_size_well_above_the_1mb_default(self):
        # A single >1MB stdout message (a big Read / grep result / echoed image) would otherwise crash the
        # receive loop → tear down the client → close stdin → the CLI rejects any PENDING picker with "Tool
        # permission stream closed before response received" (the user 2026-07-04, reproduced live).
        be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)
        opts = be._options(self._sess(be), _sdk.ClaudeAgentOptions)
        self.assertEqual(opts.max_buffer_size, sb.SDK_MAX_BUFFER, "romp sets the buffer cap explicitly")
        self.assertGreaterEqual(opts.max_buffer_size, 32 * 1024 * 1024,
                                "well past any realistic single message, so a picker never dies on overflow")

    # Thinking summaries (2026-09-01). On the SDK's stream-json path the CLI requests NO thinking display
    # (it uses an explicit --thinking-display when given, consults the showThinkingSummaries settings key
    # only when interactive, and forces "omitted" only for --print text/json output — verified in the
    # 2.1.257 binary, re-read at 2.1.258), so the API default applies and current models return
    # signature-only thinking blocks. The kernel's per-install gear toggle writes
    # STATE/thinking-summaries.json; _options reads it at every connect and, when on, passes the SDK's
    # TYPED ThinkingConfigAdaptive field (types.py: display "summarized" | "omitted") — never the
    # extra_args escape hatch, which this option has a field for.
    def test_thinking_summaries_off_by_default_requests_no_display(self):
        be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)
        self.assertFalse(sb.thinking_summaries_on(be.state_dir), "absent file reads OFF")
        opts = be._options(self._sess(be), _sdk.ClaudeAgentOptions)
        self.assertIsNone(opts.thinking, "off → no thinking option at all (the CLI's own default stands)")
        self.assertNotIn("thinking-display", opts.extra_args or {})

    def test_thinking_summaries_on_passes_the_typed_adaptive_summarized_field(self):
        with open(os.path.join(self.d, sb.THINKING_SUMMARIES_FILE), "w") as f:
            json.dump({"enabled": True, "gt": 1}, f)
        be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)
        self.assertTrue(sb.thinking_summaries_on(be.state_dir))
        opts = be._options(self._sess(be), _sdk.ClaudeAgentOptions)
        self.assertEqual(opts.thinking, {"type": "adaptive", "display": "summarized"},
                         "the designed field, in the shape the SDK types")
        self.assertNotIn("thinking-display", opts.extra_args or {},
                         "must NOT route the display through the extra_args CLI-flag escape hatch")
        # …and the installed SDK's transport turns that field into the CLI flags the binary honors
        # (--thinking adaptive --thinking-display summarized) — verified against the SDK romp runs, not
        # assumed from its docs.
        from claude_agent_sdk._internal.transport.subprocess_cli import SubprocessCLITransport
        cmd = SubprocessCLITransport("", opts)._build_command()
        self.assertIn("--thinking-display", cmd)
        self.assertEqual(cmd[cmd.index("--thinking-display") + 1], "summarized")
        self.assertEqual(cmd[cmd.index("--thinking") + 1], "adaptive")

    def test_thinking_summaries_explicit_off_requests_no_display(self):
        # OFF written as a value (the user turned it on, then off again) is the same as absent
        with open(os.path.join(self.d, sb.THINKING_SUMMARIES_FILE), "w") as f:
            json.dump({"enabled": False, "gt": 2}, f)
        be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)
        self.assertIsNone(be._options(self._sess(be), _sdk.ClaudeAgentOptions).thinking)
        with open(os.path.join(self.d, sb.THINKING_SUMMARIES_FILE), "w") as f:
            f.write("not json")
        self.assertFalse(sb.thinking_summaries_on(be.state_dir), "an unreadable file refuses — the opt-in must be provable")

    def test_thinking_summaries_on_over_a_thinking_cap_logs_the_override_once(self):
        # The CLI resolves --thinking adaptive ahead of MAX_THINKING_TOKENS (verified in the 2.1.257
        # binary), so with a cap in the manager's environment the toggle turns thinking ON where the cap
        # had it off — real, and never silent: one kernel-log line per backend (the environment is fixed
        # for the process's lifetime), not one per connect.
        with open(os.path.join(self.d, sb.THINKING_SUMMARIES_FILE), "w") as f:
            json.dump({"enabled": True, "gt": 1}, f)
        lines = []
        had = os.environ.get("MAX_THINKING_TOKENS")
        os.environ["MAX_THINKING_TOKENS"] = "0"
        try:
            be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None, log=lines.append)
            opts = be._options(self._sess(be), _sdk.ClaudeAgentOptions)
            self.assertEqual(opts.thinking, {"type": "adaptive", "display": "summarized"}, "the flag still goes")
            be._options(self._sess(be), _sdk.ClaudeAgentOptions)   # a second connect: no second line
        finally:
            if had is None:
                os.environ.pop("MAX_THINKING_TOKENS", None)
            else:
                os.environ["MAX_THINKING_TOKENS"] = had
        hits = [l for l in lines if "MAX_THINKING_TOKENS=0" in l]
        self.assertEqual(len(hits), 1, "one line though two sessions connected: %r" % lines)
        self.assertIn("--thinking adaptive", hits[0], "names the flag that wins")

    def test_thinking_summaries_on_without_a_cap_logs_nothing(self):
        with open(os.path.join(self.d, sb.THINKING_SUMMARIES_FILE), "w") as f:
            json.dump({"enabled": True, "gt": 1}, f)
        lines = []
        had = os.environ.pop("MAX_THINKING_TOKENS", None)
        try:
            be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None, log=lines.append)
            be._options(self._sess(be), _sdk.ClaudeAgentOptions)
        finally:
            if had is not None:
                os.environ["MAX_THINKING_TOKENS"] = had
        self.assertEqual([l for l in lines if "thinking" in l.lower()], [],
                         "no cap → the flag changes only the display; nothing to announce")


@unittest.skipUnless(_HAVE_SDK, "claude_agent_sdk not installed")
class FastModeReportedState(unittest.TestCase):
    """What fast mode is DOING comes from the CLI's init message, not from what romp asked for. The two
    genuinely differ — fast mode needs an Opus model and has its own rate limit — so an opted-in session
    can be running off or cooling down, and the badge has to say the true thing (the authoritative-source
    rule: read the real source, never a hopeful reconstruction of it)."""

    def setUp(self):
        import asyncio
        # the init branch schedules a context refresh on the session's loop; give it one to schedule onto
        # (never run — the coroutine is irrelevant here) so _on_message can be driven synchronously
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

    def tearDown(self):
        import asyncio
        asyncio.set_event_loop(None)
        self._loop.close()

    def _sess(self, **reg):
        d = tempfile.mkdtemp()
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None)
        s = sb.SdkSession(be, {"sid": "f1", "name": "n", "cwd": d, "mode": "acceptEdits", **reg})
        s.loop = self._loop
        return s

    def _init(self, sess, data):
        sess._on_message(_sdk.SystemMessage("init", data),
                         _sdk.AssistantMessage, _sdk.ResultMessage, _sdk.SystemMessage)

    def test_the_cli_report_lands_on_the_snapshot(self):
        sess = self._sess(fast=True)
        self.assertEqual(sess.snapshot()["fast"], "", "unknown until an init lands → no badge")
        self._init(sess, {"fast_mode_state": "on"})
        snap = sess.snapshot()
        self.assertEqual(snap["fast"], "on")
        self.assertTrue(sess.fast_opt, "and the persisted ask is untouched by the report")

    def test_an_opted_in_session_the_cli_refuses_reports_the_reason(self):
        # e.g. fast mode asked for on a session whose model isn't Opus: we say on, the CLI says off.
        sess = self._sess(fast=True)
        self._init(sess, {"fast_mode_state": "off", "fast_mode_disabled_reason": "model_not_allowed"})
        snap = sess.snapshot()
        self.assertTrue(sess.fast_opt, "romp's opt-in is unchanged — the user did ask for it")
        self.assertEqual(snap["fast"], "off", "but the CLI's verdict is what the badge shows")
        self.assertEqual(snap["fastReason"], "model_not_allowed")

    def test_cooldown_is_reported_verbatim(self):
        # fast mode has its own rate limit; a session that hit it runs normally until it resets, and the
        # only way anyone finds out is that the CLI says so.
        sess = self._sess(fast=True)
        self._init(sess, {"fast_mode_state": "cooldown"})
        self.assertEqual(sess.snapshot()["fast"], "cooldown")

    def test_an_init_without_the_field_never_overwrites_the_known_state(self):
        # an older CLI sends no fast_mode_state; the last truth STANDS, never fabricated to "off"
        sess = self._sess(fast=True)
        self._init(sess, {"fast_mode_state": "off", "fast_mode_disabled_reason": "model_not_allowed"})
        self._init(sess, {})
        self.assertEqual(sess.snapshot()["fast"], "off")
        self.assertEqual(sess.snapshot()["fastReason"], "model_not_allowed")

    def test_the_toggle_turns_own_init_yields_to_the_sent_word_once(self):
        # A literal '/fast on' send opens a turn whose init still reports "off" — the state at turn
        # START, before the toggle applied. Taking it verbatim stomped the optimistic flip for a whole
        # turn (the user 2026-08-09: the transcript acknowledged the toggle, the badge read off until
        # the next message). That single stale word yields; the NEXT init wins unconditionally.
        sess = self._sess(fast=True)
        sess.fast = "on"            # set_fast's optimistic flip…
        sess._fast_expect = "on"    # …and its one-shot expectation
        self._init(sess, {"fast_mode_state": "off"})
        self.assertEqual(sess.snapshot()["fast"], "on", "the same-turn stale word yields")
        self._init(sess, {"fast_mode_state": "off"})
        self.assertEqual(sess.snapshot()["fast"], "off", "one-shot: the next init is authoritative")

    def test_a_refusal_reason_always_beats_the_expectation(self):
        # A disabled_reason is real refusal evidence (org/model/cooldown gating), not a stale word —
        # the expectation never overrides it, so a refused toggle reads refused immediately.
        sess = self._sess(fast=True)
        sess.fast = "on"
        sess._fast_expect = "on"
        self._init(sess, {"fast_mode_state": "off", "fast_mode_disabled_reason": "org_disabled"})
        self.assertEqual(sess.snapshot()["fast"], "off")
        self.assertEqual(sess.snapshot()["fastReason"], "org_disabled")
        self.assertEqual(sess._fast_expect, "", "spent either way")

    def test_an_agreeing_init_spends_the_expectation(self):
        sess = self._sess(fast=True)
        sess.fast = "on"
        sess._fast_expect = "on"
        self._init(sess, {"fast_mode_state": "on"})
        self.assertEqual(sess.snapshot()["fast"], "on")
        self.assertEqual(sess._fast_expect, "")


@unittest.skipUnless(_HAVE_SDK, "claude_agent_sdk not installed")
class ApiRetryState(unittest.TestCase):
    """An api_retry storm (API rate-limit/overload) must surface as a distinct 'retrying' state, not a
    silent 'working', so a stall reads as an API issue (the user 2026-06-23). Cleared on real output."""

    def test_api_retry_shows_retrying_then_clears(self):
        d = tempfile.mkdtemp()
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None)
        sess = sb.SdkSession(be, {"sid": "r1", "name": "n", "cwd": d, "mode": "acceptEdits"})
        sess.inflight = 1                                        # a turn is in flight
        self.assertEqual(sess.snapshot()["state"], "working")
        sess._on_message(_sdk.SystemMessage("api_retry", {}), _sdk.AssistantMessage, _sdk.ResultMessage, _sdk.SystemMessage)
        self.assertTrue(sess.retrying)
        self.assertEqual(sess.snapshot()["state"], "retrying", "api_retry stall reads as 'retrying'")
        sess._on_message(_sdk.AssistantMessage(content=[_sdk.TextBlock("hi")], model="m"),
                         _sdk.AssistantMessage, _sdk.ResultMessage, _sdk.SystemMessage)
        self.assertFalse(sess.retrying)
        self.assertEqual(sess.snapshot()["state"], "working", "real output clears 'retrying'")

    def test_api_retry_detail_is_captured_and_cleared(self):
        # the payload's own numbers + the error behind the backoff ride snapshot["retryInfo"] so the
        # chat's retrying element can say WHAT is failing and when the next try fires (the user 2026-07-10)
        d = tempfile.mkdtemp()
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None)
        sess = sb.SdkSession(be, {"sid": "r2", "name": "n", "cwd": d, "mode": "acceptEdits"})
        sess.inflight = 1
        t0 = time.time()
        sess._on_message(_sdk.SystemMessage("api_retry", {"number": 3, "max_retries": 10,
                                                          "retry_delay_ms": 5000, "error_status": 529,
                                                          "error": "overloaded_error: overloaded"}),
                         _sdk.AssistantMessage, _sdk.ResultMessage, _sdk.SystemMessage)
        info = sess.snapshot()["retryInfo"]
        self.assertEqual(info["attempt"], 3)
        self.assertEqual(info["max"], 10)
        self.assertEqual(info["status"], 529)
        self.assertIn("overloaded", info["error"])
        self.assertAlmostEqual(info["retryAt"], t0 + 5, delta=2)
        sess._on_message(_sdk.AssistantMessage(content=[_sdk.TextBlock("hi")], model="m"),
                         _sdk.AssistantMessage, _sdk.ResultMessage, _sdk.SystemMessage)
        self.assertIsNone(sess.snapshot()["retryInfo"], "recovery clears the detail with the flag")

    def test_api_retry_with_a_bare_payload_still_counts(self):
        # only error_status has been SEEN on the wire — every other field must degrade to None / the
        # local attempt count, never crash or invent numbers
        d = tempfile.mkdtemp()
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None)
        sess = sb.SdkSession(be, {"sid": "r3", "name": "n", "cwd": d, "mode": "acceptEdits"})
        sess.inflight = 1
        for want in (1, 2):
            sess._on_message(_sdk.SystemMessage("api_retry", {}), _sdk.AssistantMessage,
                             _sdk.ResultMessage, _sdk.SystemMessage)
            info = sess.snapshot()["retryInfo"]
            self.assertEqual(info["attempt"], want, "falls back to the local storm count")
        self.assertIsNone(info["max"])
        self.assertIsNone(info["status"])
        self.assertIsNone(info["error"])
        self.assertIsNone(info["retryAt"])
        # a turn-end Result clears the detail too (an unrecovered storm leaves no stale info)
        sess._on_message(_sdk.ResultMessage("success", 1, 1, False, 1, "fsid"),
                         _sdk.AssistantMessage, _sdk.ResultMessage, _sdk.SystemMessage)
        self.assertIsNone(sess.snapshot()["retryInfo"])


@unittest.skipUnless(_HAVE_SDK, "claude_agent_sdk not installed")
class InterruptSettlesStall(unittest.TestCase):
    """Interrupt must drop a session out of 'working' even if the turn never produces a ResultMessage
    (e.g. it's stuck in an API-retry backoff) — the snapshot reads 'working' purely from inflight>0, so a
    user interrupt that the CLI is slow to honour would otherwise leave it 'working' forever."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self._orig = _sdk.ClaudeSDKClient
        import asyncio as _aio

        class StallClient:
            instances = []

            def __init__(self, options=None, transport=None):
                self.options = options
                self.interrupted = False
                self._turnq = _aio.Queue()
                StallClient.instances.append(self)

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def query(self, prompt, session_id="default"):
                async for turn in prompt:
                    await self._turnq.put(turn)

            async def interrupt(self):
                self.interrupted = True

            async def receive_messages(self):
                yield _sdk.SystemMessage("init", {"session_id": self.options.session_id or "fsid"})
                await self._turnq.get()              # consume the turn → inflight goes to 1...
                while True:
                    await _aio.sleep(3600)            # ...then STALL forever (never a ResultMessage)

        _sdk.ClaudeSDKClient = StallClient
        self.Fake = StallClient
        StallClient.instances = []
        self.backend = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)

    def tearDown(self):
        _sdk.ClaudeSDKClient = self._orig

    def _wait(self, pred, timeout=6.0):
        end = time.time() + timeout
        while time.time() < end:
            if pred():
                return True
            time.sleep(0.02)
        return False

    def test_interrupt_settles_a_stalled_turn(self):
        sid = self.backend.spawn("stall", self.d)
        self.backend.send(sid, "go")
        self.assertTrue(self._wait(lambda: self.backend.live_sessions().get(sid, {}).get("state") == "working"),
                        "a stalled in-flight turn reads as working")
        self.assertTrue(self.backend.interrupt(sid))
        self.assertTrue(self._wait(lambda: self.Fake.instances and self.Fake.instances[0].interrupted),
                        "client.interrupt() was sent")
        self.assertTrue(self._wait(lambda: self.backend.live_sessions().get(sid, {}).get("state") != "working"),
                        "after interrupt the session is no longer 'working' even with no ResultMessage")


class InterruptAckSettlesIdle(unittest.TestCase):
    """A stop that races the turn's own death must not strand the 'Interrupting…' flag (the user
    2026-07-20: stop pressed one second after the turn died of its API-retry storm — the ResultMessage
    had already settled inflight to 0 and cleared _interrupted; _do_interrupt then re-latched it against
    an idle CLI, and with no turn left there was no clearing event, so an idle session wore
    'Interrupting…' until the next fed turn / the kernel's 120s cap). The completed control round-trip
    is the settle when nothing is in flight; a live turn keeps the flag for its ResultMessage."""

    def _session(self):
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)
        return be, sb.SdkSession(be, {"sid": "11111111-2222-3333-4444-555555555555", "name": "n", "cwd": "/tmp"})

    def test_ack_with_nothing_in_flight_clears_the_flag(self):
        import asyncio
        be, s = self._session()
        class _Client:
            async def interrupt(self): pass
        s.client = _Client()
        asyncio.run(s._do_interrupt())          # inflight == 0 throughout: the turn is already over
        self.assertFalse(s._interrupted, "the ack settles the stop when there is no turn — no stranded flag")
        self.assertFalse(s.snapshot()["interrupting"], "an idle session never wears 'Interrupting…'")

    def test_failed_ack_with_nothing_in_flight_clears_too(self):
        import asyncio
        be, s = self._session()
        class _Client:
            async def interrupt(self): raise RuntimeError("no current client")
        s.client = _Client()
        asyncio.run(s._do_interrupt())          # idle-session refusal: logged, nothing to escalate...
        self.assertFalse(s._interrupted, "...and nothing left in flight → the flag settles down")

    def test_escalated_signal_on_an_idle_session_does_not_latch(self):
        import types
        be, s = self._session()
        be._session_cli_pid = lambda sess: 4242          # a CLI process exists...
        real_os = sb.os
        sb.os = types.SimpleNamespace(kill=lambda pid, sig: None)   # ...and the signal lands
        try:
            s._signal_cli(sb.signal.SIGINT, "sigint")
        finally:
            sb.os = real_os
        self.assertFalse(s._interrupted,
                         "no turn in flight → nothing this signal stops → no settle event exists to clear a latch")


class PendingQueue(unittest.TestCase):
    """The visible pending queue (no SDK / no loop needed) — enqueue holds turns in a list that
    pending_queued exposes, so the kernel can render the 'queued' indicator for SDK sessions."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)

    def _sess(self, sid="q1"):
        s = sb.SdkSession(self.be, {"sid": sid, "name": "n", "cwd": self.d, "mode": "acceptEdits"})
        self.be.sessions[sid] = s          # register WITHOUT starting the thread (no loop)
        return s

    def test_enqueue_holds_in_pending_oldest_first(self):
        s = self._sess()
        s.enqueue("first"); s.enqueue("second")
        self.assertEqual(s.pending(), ["first", "second"])              # both held, in order
        self.assertEqual(self.be.pending_queued("q1"), ["first", "second"])

    def test_pending_returns_a_copy(self):
        s = self._sess()
        s.enqueue("a")
        snap = s.pending(); snap.append("mutated")
        self.assertEqual(s.pending(), ["a"])                            # internal list untouched

    def test_unqueue_removes_by_index_and_returns_text(self):
        # the chat's cancel affordance: pull a still-queued message back out by its position (the user 2026-06-27)
        s = self._sess("q3")
        s.enqueue("alpha"); s.enqueue("beta"); s.enqueue("gamma")
        self.assertEqual(self.be.unqueue("q3", 1), "beta")              # cancel the middle one
        self.assertEqual(s.pending(), ["alpha", "gamma"])              # the rest keep order
        self.assertIsNone(self.be.unqueue("q3", 9), "out-of-range idx is a safe no-op")
        self.assertIsNone(self.be.unqueue("no-such-sid", 0), "unknown session → None")

    def test_unqueue_clears_the_optimistic_echo(self):
        # the bug (the user 2026-06-27): canceling a queued message popped its text back to the composer but
        # it kept rendering as a solid-blue SENT bubble, because send()'s optimistic echo — which normally
        # prunes when the real user atom lands in the transcript — was never cleared for a message that never
        # lands. unqueue must drop the echo too.
        sid = "qe1"
        s = self._sess(sid)
        s.enqueue("cancel me")
        self.be._live.setdefault(sid, {})["echo:x"] = {"type": "user", "_echo_text": "cancel me",
            "message": {"role": "user", "content": [{"type": "text", "text": "cancel me"}]}}
        self.assertEqual(self.be.unqueue(sid, 0), "cancel me")
        self.assertEqual(s.pending(), [])
        self.assertFalse(any(a.get("_echo_text") == "cancel me" for a in self.be._live.get(sid, {}).values()),
                         "the optimistic echo is gone → the canceled message no longer reads as sent")

    def test_pending_queued_empty_for_unknown_or_idle(self):
        self.assertEqual(self.be.pending_queued("no-such-sid"), [])     # not an SDK session
        self._sess("q2")
        self.assertEqual(self.be.pending_queued("q2"), [])             # session exists, nothing queued

    def test_unqueue_expect_relocates_under_the_lock(self):
        # the user 2026-07-20: the kernel's drift guard located the message in a SNAPSHOT, then popped
        # by raw index — the input generator consuming entries in between could cancel the WRONG
        # message. `expect` moves the verify inside the lock: a shifted index re-locates by exact text.
        s = self._sess("qx1")
        s.enqueue("alpha"); s.enqueue("beta")
        s.unqueue(0)                                     # the queue shifts after the caller's snapshot
        self.assertEqual(self.be.unqueue("qx1", 1, "beta"), "beta", "stale idx 1 re-locates to 'beta'")
        self.assertEqual(s.pending(), [])

    def test_unqueue_expect_missing_is_a_loud_miss_not_a_wrong_pop(self):
        # the already-forwarded case (no recall exists once the CLI has the message): the exact text is
        # gone from _pending → None, and the OTHER queued message is untouched — the caller turns the
        # None into the 'too late' toast instead of the old silent fake-delete.
        s = self._sess("qx2")
        s.enqueue("survivor")
        self.assertIsNone(self.be.unqueue("qx2", 0, "already forwarded"))
        self.assertEqual(s.pending(), ["survivor"], "a miss never pops a different message")

    def test_queue_recallable_only_while_a_recall_can_win(self):
        # the ✕ affordance gate (the user 2026-07-20): during a running UN-HELD turn the input
        # generator forwards a queued send into the CLI within milliseconds — a cancel there can only
        # lose, so the bubble must not offer one. The two romp-side HOLDS (interrupt, pending rewind)
        # and the idle/connecting states keep the queue genuinely recallable.
        s = self._sess("qr1")
        self.assertTrue(self.be.queue_recallable("qr1"), "idle → entries sit in _pending, recallable")
        s.inflight = 1
        self.assertFalse(self.be.queue_recallable("qr1"), "running un-held turn → forwards instantly")
        s._interrupted = True
        self.assertTrue(self.be.queue_recallable("qr1"), "interrupt hold → the queue is romp-held")
        s._interrupted = False
        s._rewind_to = "11111111-2222-3333-4444-555555555555"
        self.assertTrue(self.be.queue_recallable("qr1"), "pending rewind holds the queue too")
        s._rewind_armed = True
        self.assertFalse(self.be.queue_recallable("qr1"), "armed rewind releases the hold")
        self.assertTrue(self.be.queue_recallable("no-such-sid"), "unknown session fails toward the ✕")

    def test_queue_recallable_during_the_ping_feed_hold(self):
        # the rename ping's feed-hold (2026-08-25) is a romp-side hold exactly like the interrupt
        # and rewind ones: while the ping's turn is in flight the drain releases nothing, so a
        # recall can still win — withholding the ✕ there denies a cancel that would succeed
        # (found 2026-08-26).
        s = self._sess("qr2")
        s.inflight = 1
        s._ping_feeding = True
        self.assertTrue(self.be.queue_recallable("qr2"), "ping feed-hold → the queue is romp-held")
        s._ping_feeding = False
        self.assertFalse(self.be.queue_recallable("qr2"), "hold cleared → forwards instantly again")


@unittest.skipUnless(_HAVE_SDK, "claude_agent_sdk not installed")
class PendingQueueLoop(unittest.TestCase):
    """End-to-end: a turn enqueued while another is IN FLIGHT is FORWARDED to the SDK immediately
    (next-tool-boundary delivery), not held until the in-flight turn ends (the user 2026-06-27).
    It leaves romp's pending queue as soon as it's fed. (A wedged/interrupted turn still holds the
    queue — see InterruptWithQueue.)"""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self._orig_client = _sdk.ClaudeSDKClient
        import asyncio as _aio

        class GatedClient:
            instances = []
            received = []                  # turn texts actually fed to the SDK, in order
            release = threading.Event()    # test sets this to let the in-flight turn complete

            def __init__(self, options=None, transport=None):
                self.options = options
                self._turnq = _aio.Queue()
                GatedClient.instances.append(self)

            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False

            async def query(self, prompt, session_id="default"):
                async for turn in prompt:                 # the feeder writes each released turn here
                    await self._turnq.put(turn)

            async def interrupt(self): pass
            async def set_model(self, model=None): pass
            async def set_permission_mode(self, mode): pass

            async def receive_messages(self):
                yield _sdk.SystemMessage("init", {
                    "model": "claude-x", "permissionMode": "acceptEdits",
                    "session_id": (self.options.session_id or "fsid")})
                while True:
                    turn = await self._turnq.get()
                    GatedClient.received.append(turn["message"]["content"][0]["text"])
                    while not GatedClient.release.is_set():
                        await _aio.sleep(0.01)            # hold the turn 'in flight' until released
                    GatedClient.release.clear()
                    yield _sdk.ResultMessage("success", 1, 1, False, 1, "fsid")

        _sdk.ClaudeSDKClient = GatedClient
        self.Gated = GatedClient
        GatedClient.instances = []
        GatedClient.received = []
        GatedClient.release = threading.Event()
        self.backend = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)

    def tearDown(self):
        self.Gated.release.set()                          # unblock any in-flight turn so the thread can exit
        _sdk.ClaudeSDKClient = self._orig_client

    def _wait(self, pred, timeout=6.0):
        end = time.time() + timeout
        while time.time() < end:
            if pred():
                return True
            time.sleep(0.01)
        return False

    def test_second_turn_forwarded_immediately_mid_flight(self):
        sid = self.backend.spawn("q", self.d)
        self.assertTrue(self.backend.send(sid, "A"))
        self.assertTrue(self._wait(lambda: self.Gated.received == ["A"]), "A never reached the SDK")

        # B is enqueued while A is in flight: it is FORWARDED straight to the stream — it does NOT linger in
        # romp's queue waiting for A to finish (the user 2026-06-27). pending clears immediately.
        self.assertTrue(self.backend.send(sid, "B"))
        self.assertTrue(self._wait(lambda: self.backend.pending_queued(sid) == []),
                        "B should be forwarded to the SDK at once, not held in romp's queue")

        # The mock's receiver serializes (one turn at a time, like the CLI), so B SURFACES after A is released
        # — but it was already fed. Order is preserved.
        self.Gated.release.set()
        self.assertTrue(self._wait(lambda: self.Gated.received == ["A", "B"]),
                        "B is delivered after A, in order")


@unittest.skipUnless(_HAVE_SDK, "claude_agent_sdk not installed")
class InterruptWithQueue(unittest.TestCase):
    """Interrupt must NOT settle inflight or release the next queued turn itself — that's the
    double-count api caught (the forced interrupt-settle AND the aborted turn's ResultMessage both
    decrement, so the next turn is released early while the prior is still counted). Modeled
    deterministically with a STALLED interrupt (no ResultMessage, like InterruptSettlesStall) so
    there is no result-ordering race: the interrupted turn stays in flight, so its queued follower
    must WAIT (honest queue-pause; the CLI is stuck) rather than be force-fed into a wedged CLI.
      fix : B stays queued, session reads 'waiting' (inflight held, display only).
      bug : the forced settle frees inflight → B is popped + fed into the stuck CLI."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self._orig = _sdk.ClaudeSDKClient
        import asyncio as _aio

        class StallClient:
            instances = []
            received = []                  # turn texts actually fed to the SDK, in order

            def __init__(self, options=None, transport=None):
                self.options = options
                self.interrupted = False
                self._turnq = _aio.Queue()
                StallClient.instances.append(self)

            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False

            async def query(self, prompt, session_id="default"):
                async for turn in prompt:
                    await self._turnq.put(turn)

            async def interrupt(self):
                self.interrupted = True    # interrupt sent, but the wedged turn never produces a result

            async def receive_messages(self):
                yield _sdk.SystemMessage("init", {"session_id": self.options.session_id or "fsid"})
                while True:
                    turn = await self._turnq.get()
                    StallClient.received.append(turn["message"]["content"][0]["text"])
                    await _aio.sleep(3600)           # stall this turn forever (never a ResultMessage)

        _sdk.ClaudeSDKClient = StallClient
        self.Fake = StallClient
        StallClient.instances = []
        StallClient.received = []
        self.backend = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)

    def tearDown(self):
        _sdk.ClaudeSDKClient = self._orig

    def _wait(self, pred, timeout=6.0):
        end = time.time() + timeout
        while time.time() < end:
            if pred():
                return True
            time.sleep(0.01)
        return False

    def test_interrupt_holds_a_turn_queued_after_it(self):
        sid = self.backend.spawn("x", self.d)
        self.backend.send(sid, "A")
        self.assertTrue(self._wait(lambda: self.Fake.received == ["A"]), "A is in flight")

        # Interrupt the (wedged) A. Interrupt must only FLAG it — not drop inflight.
        self.assertTrue(self.backend.interrupt(sid))
        self.assertTrue(self._wait(lambda: self.backend.live_sessions().get(sid, {}).get("state") == "waiting"),
                        "interrupted turn reads 'waiting' (inflight held, _interrupted set)")

        # Mid-turn forwarding is SUSPENDED while interrupted: a turn queued AFTER the interrupt is HELD, not
        # force-fed into the stuck CLI (the double-count / wedge hazard). It releases once the wedged turn
        # settles inflight to 0 (the user 2026-06-27).
        self.backend.send(sid, "B")
        time.sleep(0.3)
        self.assertEqual(self.backend.pending_queued(sid), ["B"],
                         "B stays queued behind the interrupted turn — not fed into a stuck CLI")
        self.assertEqual(self.Fake.received, ["A"], "B was NOT fed to the SDK while interrupted")
        self.assertEqual(self.backend.live_sessions().get(sid, {}).get("state"), "waiting",
                         "still 'waiting' — inflight held, not double-counted")


@unittest.skipUnless(_HAVE_SDK, "claude_agent_sdk not installed")
class ReconnectReconcilesInflight(unittest.TestCase):
    """A reconnect abandons the previous client; a turn it left IN FLIGHT can never get its ResultMessage on
    the new connection (that client and its receive loop are gone), so inflight — and the 'working' signal it
    drives — would be stranded elevated FOREVER: the session reads 'working' indefinitely though it's idle
    (the user 2026-07-01, who started a new session and immediately switched the model, after which it
    said it was working indefinitely though it had just changed the model and was ready). request_reconnect defers
    while inflight>0, but a race (it fired at inflight==0, then the input generator started a turn before the
    teardown ran) still strands one. The reconnect must reconcile inflight to idle.
      fix : after the reconnect, inflight == 0 and the session reads 'waiting'.
      bug : inflight stays 1 across the reconnect → snapshot 'working' forever."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self._orig = _sdk.ClaudeSDKClient
        import asyncio as _aio

        class StallClient:
            instances = []
            received = []                  # turn texts actually fed to the SDK, in order

            def __init__(self, options=None, transport=None):
                self.options = options
                self._turnq = _aio.Queue()
                StallClient.instances.append(self)

            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False

            async def query(self, prompt, session_id="default"):
                async for turn in prompt:
                    await self._turnq.put(turn)

            async def interrupt(self): pass
            async def set_model(self, model=None): pass
            async def get_context_usage(self): return {"percentage": 2, "model": "claude-x"}

            async def receive_messages(self):
                yield _sdk.SystemMessage("init", {"session_id": self.options.session_id or "fsid"})
                while True:
                    turn = await self._turnq.get()
                    StallClient.received.append(turn["message"]["content"][0]["text"])
                    await _aio.sleep(3600)           # stall this turn forever (never a ResultMessage)

        _sdk.ClaudeSDKClient = StallClient
        self.Fake = StallClient
        StallClient.instances = []
        StallClient.received = []
        self.backend = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)

    def tearDown(self):
        _sdk.ClaudeSDKClient = self._orig

    def _wait(self, pred, timeout=6.0):
        end = time.time() + timeout
        while time.time() < end:
            if pred():
                return True
            time.sleep(0.01)
        return False

    def test_reconnect_settles_a_turn_stranded_by_the_teardown(self):
        sid = self.backend.spawn("recon", self.d)
        self.backend.send(sid, "A")                              # first turn → inflight 1, state 'working'
        self.assertTrue(self._wait(lambda: self.Fake.received == ["A"]), "A never reached the SDK (in flight)")
        s = self.backend.sessions[sid]
        self.assertEqual(s.inflight, 1)
        self.assertEqual(s.snapshot()["state"], "working", "the in-flight turn reads 'working'")
        # Force a reconnect WHILE the turn is in flight — models the race where request_reconnect fired at
        # inflight==0 but the input generator started a turn before _amain tore the client down.
        s.loop.call_soon_threadsafe(lambda: (setattr(s, "_reconnect", True), s._wake_set()))
        self.assertTrue(self._wait(lambda: len(self.Fake.instances) >= 2), "the reconnect did not rebuild the client")
        self.assertTrue(self._wait(lambda: s.inflight == 0),
                        "inflight must reconcile to 0 across the reconnect (else 'working' is stranded forever)")
        self.assertEqual(s.snapshot()["state"], "waiting",
                         "idle on the new connection reads 'waiting', not a stranded 'working'")
        self.assertEqual(sb.last_state(self.d, sid).get("state"), "waiting",
                         "the state log agrees — else snapshot's last_state branch re-reads the stale 'working'")
        self.backend.kill(sid)


class RateLimitUsageStaleness(unittest.TestCase):
    """usage.json (the /usage rail's 5h + weekly bars) is written by BOTH the tmux statusline — the CLI's
    CURRENT rate_limits handed to it every render, always fresh — and the SDK backend's _record_rate_limit,
    which is STATUS-AWARE (the user 2026-07-02): 19h of cadence instrumentation showed the CLI attaches
    `utilization` only in the allowed_warning band; `allowed` and `rejected` events carry None. The old
    util-only path dropped 97% of events — every REJECTED one included, so romp never showed the limit —
    and after an account switch nothing replaced the old account's reading. Now `status` + `resets_at`
    (always present) drive the merge: rejected=100, the event's resets_at names the LIVE window, and a
    same-window unknown utilization keeps the file's pct."""

    def _info(self, rlt, util, resets_at, status="allowed"):
        class _I:
            pass
        i = _I()
        i.rate_limit_type, i.utilization, i.resets_at, i.status = rlt, util, resets_at, status
        return i

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.logs = []
        self.be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None, log=self.logs.append)

    def _usage(self):
        return json.loads((Path(self.d) / "usage.json").read_text())

    def _write_usage(self, data):
        (Path(self.d) / "usage.json").write_text(json.dumps(data))

    def test_sdk_event_does_not_clobber_the_statuslines_fresh_five_hour(self):
        now = int(time.time())
        # the tmux statusline wrote a FRESH snapshot (current rate_limits every render): 5h=69%, wk=65%.
        self._write_usage({"t": now, "five_hour": {"pct": 69, "resets_at": now + 3600},
                                       "seven_day": {"pct": 65, "resets_at": now + 500000}})
        # a seven_day RateLimitEvent fires — it touches ONLY its own window, never the five_hour.
        self.be._record_rate_limit(self._info("seven_day", 0.65, now + 500000))
        out = self._usage()
        self.assertEqual(out["five_hour"]["pct"], 69,
                         "the statusline's fresh five_hour must survive an SDK seven_day write, not be clobbered")
        self.assertEqual(out["seven_day"]["pct"], 65)

    def test_higher_pct_wins_within_the_same_window(self):
        # Same window (same resets_at): usage only climbs within a window, so the higher pct is the newer read.
        now = int(time.time())
        self._write_usage({"t": now, "five_hour": {"pct": 69, "resets_at": now + 3600}, "seven_day": None})
        self.be._record_rate_limit(self._info("five_hour", 0.10, now + 3600))   # a stale low read, same window
        self.assertEqual(self._usage()["five_hour"]["pct"], 69, "a stale lower read must not lower the bar")

    def test_a_genuinely_newer_window_replaces_an_older_one(self):
        # A later resets_at IS a newer window (the old one reset): the fresh low read is correct, take it.
        now = int(time.time())
        self._write_usage({"t": now, "five_hour": {"pct": 90, "resets_at": now + 60}, "seven_day": None})
        self.be._record_rate_limit(self._info("five_hour", 0.05, now + 5 * 3600))   # window reset → new window
        self.assertEqual(self._usage()["five_hour"]["pct"], 5, "a genuinely newer window replaces the old one")

    def test_rejected_with_null_utilization_reads_100(self):
        # The CLI attaches NO utilization to a rejected event — but rejected IS the limit. Dropping it (the
        # old util-only gate) is how the user hit the session limit without romp ever showing it.
        now = int(time.time())
        self.be._record_rate_limit(self._info("five_hour", None, now + 3600, status="rejected"))
        seg = self._usage()["five_hour"]
        self.assertEqual(seg["pct"], 100, "rejected = the window is full, even with utilization=None")
        self.assertEqual(seg["resets_at"], now + 3600)

    def test_allowed_event_unsticks_a_dead_windows_reading(self):
        # ACCOUNT SWITCH (the user 2026-07-02): the file still holds the OLD account's near-limit reading;
        # the live CLI (new account) streams allowed events with utilization=None for a DIFFERENT window.
        # The event's resets_at names the LIVE window — the dead reading is replaced, not left to win.
        now = int(time.time())
        self._write_usage({"t": now, "five_hour": {"pct": 98, "resets_at": now + 4 * 3600}, "seven_day": None})
        self.be._record_rate_limit(self._info("five_hour", None, now + 3600, status="allowed"))
        seg = self._usage()["five_hour"]
        self.assertEqual(seg["resets_at"], now + 3600, "the live CLI's window replaces the dead one — even with an EARLIER reset")
        self.assertEqual(seg["pct"], 0, "unknown usage in a fresh window reads 0 (statusline/warning events refine it)")

    def test_allowed_event_with_null_utilization_keeps_the_same_windows_pct(self):
        # Same window, no utilization → the event adds nothing about the pct; keep the file's reading AND
        # don't rewrite the file (t = the last real reading, so the tooltip's "updated … ago" stays honest).
        now = int(time.time())
        self._write_usage({"t": now - 999, "five_hour": {"pct": 42, "resets_at": now + 3600}, "seven_day": None})
        self.be._record_rate_limit(self._info("five_hour", None, now + 3600, status="allowed"))
        out = self._usage()
        self.assertEqual(out["five_hour"]["pct"], 42)
        self.assertEqual(out["t"], now - 999, "a no-op event must not refresh t")

    def test_allowed_caps_a_stale_100_at_99(self):
        # An `allowed` event PROVES the account is not limited: a same-window pct claiming 100 (an earlier
        # rejected, or a stale statusline write) is capped to 99 so the limited banner can't outlive the CLI.
        now = int(time.time())
        self._write_usage({"t": now, "five_hour": {"pct": 100, "resets_at": now + 3600}, "seven_day": None})
        self.be._record_rate_limit(self._info("five_hour", None, now + 3600, status="allowed"))
        self.assertEqual(self._usage()["five_hour"]["pct"], 99)

    def test_write_failure_is_logged_not_swallowed(self):
        # the user 2026-07-02 (who suspected an error somewhere was being swallowed): a failed
        # usage.json write must land in the backend log, never a bare `except: pass`.
        now = int(time.time())
        self.be.state_dir = Path(self.d) / "gone" / "deeper"   # no parent → the tmp write raises
        self.be._record_rate_limit(self._info("five_hour", 0.5, now + 3600))
        self.assertTrue(any("usage.json write failed" in str(m) for m in self.logs),
                        "the write failure is logged")

    def test_fable_window_lands_in_its_own_key(self):
        # `seven_day_overage_included` = the included Fable 5 weekly allowance (Claude Code /usage labels it
        # "Fable 5 limit", the user 2026-07-02) -> usage.json `fable`, the rail's third bar. It must not
        # touch the 5h/weekly windows, and they must not clobber it.
        now = int(time.time())
        self._write_usage({"t": now, "five_hour": {"pct": 21, "resets_at": now + 3600}, "seven_day": None})
        self.be._record_rate_limit(self._info("seven_day_overage_included", 0.34, now + 500000))
        out = self._usage()
        self.assertEqual(out["fable"], {"pct": 34, "resets_at": now + 500000})
        self.assertEqual(out["five_hour"]["pct"], 21, "the 5h window is untouched")
        self.be._record_rate_limit(self._info("five_hour", 0.5, now + 3600))
        self.assertEqual(self._usage()["fable"]["pct"], 34, "a 5h event must not clobber the fable window")

    def test_rejected_fable_window_reads_100(self):
        now = int(time.time())
        self.be._record_rate_limit(self._info("seven_day_overage_included", None, now + 500000, status="rejected"))
        self.assertEqual(self._usage()["fable"]["pct"], 100, "hitting the Fable 5 limit shows, even util-less")

    def test_get_usage_snapshot_maps_all_three_windows_exactly(self):
        # get_usage (a CLI control request the SDK doesn't wrap; found 2026-07-02) returns the /usage
        # screen's own limits[] with an EXACT percent per window — the ONLY in-band source for the
        # Fable-scoped weekly, and exact numbers below the warning band for the others.
        snap = {"rate_limits": {"limits": [
            {"kind": "session", "percent": 54, "resets_at": "2026-07-03T00:59:59+00:00"},
            {"kind": "weekly_all", "percent": 39, "resets_at": "2026-07-06T18:59:59+00:00"},
            {"kind": "weekly_scoped", "percent": 45, "resets_at": "2026-07-06T18:59:59+00:00",
             "scope": {"model": {"id": None, "display_name": "Fable"}}},
        ]}}
        self.be._record_usage_snapshot(snap)
        out = self._usage()
        self.assertEqual(out["five_hour"]["pct"], 54)
        self.assertEqual(out["seven_day"]["pct"], 39)
        self.assertEqual(out["fable"]["pct"], 45, "the Fable-scoped weekly lands as the third bar")
        self.assertIsInstance(out["fable"]["resets_at"], int, "ISO resets_at is stored as an epoch")

    def test_get_usage_snapshot_is_authoritative_but_preserves_unmapped_windows(self):
        now = int(time.time())
        self._write_usage({"t": now - 500, "five_hour": {"pct": 98, "resets_at": now + 60},
                           "seven_day": None, "fable": {"pct": 7, "resets_at": now + 500000}})
        self.be._record_usage_snapshot({"rate_limits": {"limits": [
            {"kind": "session", "percent": 12, "resets_at": now + 3600}]}})
        out = self._usage()
        self.assertEqual(out["five_hour"], {"pct": 12, "resets_at": now + 3600},
                         "a full-snapshot window OVERWRITES — no max-merge games for the exact source")
        self.assertEqual(out["fable"]["pct"], 7, "a window the snapshot lacks keeps its file value")

    def test_get_usage_snapshot_no_change_no_rewrite(self):
        now = int(time.time())
        self._write_usage({"t": now - 999, "five_hour": {"pct": 12, "resets_at": now + 3600},
                           "seven_day": None, "fable": None})
        self.be._record_usage_snapshot({"rate_limits": {"limits": [
            {"kind": "session", "percent": 12, "resets_at": now + 3600}]}})
        self.assertEqual(self._usage()["t"], now - 999, "an identical snapshot must not refresh t")

    def test_turn_end_schedules_the_usage_refresh(self):
        import inspect
        src = inspect.getsource(sb.SdkSession._on_message)
        self.assertIn("asyncio.ensure_future(self._do_refresh_usage())", src,
                      "every turn end refreshes the exact /usage snapshot (event-based)")
        q = inspect.getsource(sb.SdkSession._do_refresh_usage)
        self.assertIn('_send_control_request({"subtype": "get_usage"})', q,
                      "the designed CLI control request, via the SDK transport")

    def test_on_message_routes_rate_limit_events_to_the_recorder(self):
        s = sb.SdkSession(self.be, {"sid": "11111111-2222-3333-4444-555555555555", "name": "n", "cwd": self.d})

        class _Msg:            # a duck-typed RateLimitEvent (the branch keys off `rate_limit_info`)
            pass
        m = _Msg()
        m.rate_limit_info = self._info("five_hour", 0.42, int(time.time()) + 3600)

        class _T:              # dummy type classes — the msg is none of Assistant/Result/System
            pass
        s._on_message(m, _T, _T, _T)
        self.assertEqual(self._usage()["five_hour"]["pct"], 42, "the event landed in usage.json")


class TurnStateIsEventNotCount(unittest.TestCase):
    """The working signal is an EVENT (the CLI's ResultMessage), never a feed-vs-result COUNT. A
    ResultMessage settles the session to idle in ONE step, no matter how many messages were forwarded
    into the turn — the phantom-working fix (the user 2026-07-09): a mid-turn forward did inflight += 1
    but the CLI emits ONE Result for the merged turn, so the old `inflight -= 1; if 0:` guard never ran
    the settle and the session read 'working' forever."""

    def _sess(self):
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)
        s = sb.SdkSession(be, {"sid": "11111111-2222-3333-4444-555555555555", "name": "n", "cwd": "/tmp"})
        return be, s

    def _tail(self, be, s):
        return sb.last_state_value(Path(be.state_dir), s.sid)

    def _result(self, s):
        import asyncio

        async def run():
            s._on_message(_ResultMessage(), _AssistantMessage, _ResultMessage, type("S", (), {}))
            await asyncio.sleep(0)
        asyncio.run(run())

    def test_a_single_result_settles_waiting_from_any_inflight(self):
        # inflight 2 = a message forwarded MID-TURN (each feed += 1); the CLI folds both into one turn and
        # emits ONE Result. The old guard left inflight at 1 → no 'waiting', phantom-working forever.
        for n in (1, 2, 3):
            be, s = self._sess()
            sb.append_state(Path(be.state_dir), s.sid, "working")
            s.inflight = n
            s._cli_working = True
            self._result(s)
            self.assertEqual(self._tail(be, s), "waiting",
                             f"one Result settles idle from inflight={n} — never gated on a count")
            self.assertEqual(s.inflight, 0, "a Result drains the CLI in one step, not a decrement")
            self.assertFalse(s._cli_working, "the settle clears the busy flag")

    def test_result_retires_unlanded_work_atoms_from_high_inflight(self):
        # the retire that the phantom-working session never got: a forwarded-then-merged turn (inflight 2)
        # whose stream atom never landed on disk must still drop at the Result.
        be, s = self._sess()
        be._live[s.sid] = {"w1": {"uuid": "w1", "t": 5},
                           "echo:hi": {"uuid": "echo:hi", "t": 1, "_echo_text": "hi"}}
        s.inflight = 2
        self._result(s)
        self.assertEqual(set(be._live.get(s.sid, {})), {"echo:hi"},
                         "unlanded WORK atom drops even from inflight>1; the echo survives")

    def test_stream_work_atom_reasserts_working_after_a_premature_settle(self):
        # If a state write ever settles ahead of real output (a separate turn queued in the CLI that
        # streams after the previous Result), the live stream is the truth: a genuine work atom re-stamps
        # 'working'. This is what makes the signal self-heal without a counter.
        be, s = self._sess()
        s._mark("waiting")
        self.assertFalse(s._cli_working)
        be._forward(s, _AssistantMessage([_TextBlock("more work")], uuid="w9"))
        self.assertEqual(self._tail(be, s), "working", "a streamed work atom re-asserts working")
        self.assertTrue(s._cli_working)

    def test_stream_reassert_is_transition_only_and_skips_echo_and_command(self):
        be, s = self._sess()
        statef = Path(be.state_dir) / "states" / (s.sid + ".jsonl")
        s._mark("working")                                   # already working
        before = statef.read_text().count("\n")
        be._forward(s, _AssistantMessage([_TextBlock("x")], uuid="w1"))   # already working → no new stamp
        after = statef.read_text().count("\n")
        self.assertEqual(before, after, "no redundant 'working' stamp while already working")
        # A command line (e.g. a streamed /model confirmation) is NOT active work → never re-asserts.
        s._mark("waiting")
        cmd = _UserMessage([_TextBlock("<command-name>/model</command-name>\n"
                                       "<command-message>model</command-message>\n"
                                       "<command-args>sonnet</command-args>")], uuid="c1")
        be._forward(s, cmd)
        self.assertEqual(self._tail(be, s), "waiting", "a command atom must not re-assert working")
        self.assertFalse(s._cli_working)

    def test_mark_tracks_the_busy_flag(self):
        be, s = self._sess()
        s._mark("working");    self.assertTrue(s._cli_working)
        s._mark("permission"); self.assertFalse(s._cli_working, "a non-working state clears the flag")
        s._mark("working");    self.assertTrue(s._cli_working)
        s._mark("waiting");    self.assertFalse(s._cli_working)


class BgTaskLifecycle(unittest.TestCase):
    """The CLI's DESIGNED background-task lifecycle stream (system/task_started → task_progress* →
    task_updated/task_notification) feeds SdkSession._bg_tasks — the live 'what's running in the
    background' set that lets an idle session waiting on a timer/watcher read AWAITING instead of plain
    idle (the user 2026-07-11: nimbus's 20-minute campaign timer). Terminal statuses clear from EITHER
    terminal message kind (a TaskStop can suppress the notification); a progress event self-heals an
    unknown id, so a backend that attached mid-task still converges."""

    class _Sys:                                   # stand-in for SystemMessage (isinstance + subtype + data)
        def __init__(self, subtype, data):
            self.subtype = subtype
            self.data = data

    def _sess(self):
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)
        return sb.SdkSession(be, {"sid": "11111111-2222-3333-4444-555555555555", "name": "n", "cwd": "/tmp"})

    def _feed(self, s, subtype, data):
        s._on_message(self._Sys(subtype, data), _AssistantMessage, _ResultMessage, self._Sys)

    def test_task_events_mirror_the_live_set_to_the_reg(self):
        # the in-memory set dies with the backend; the reg mirror is what lets the NEXT boot's
        # reconcile tell the session its tasks were killed (the user 2026-07-11). A normal task end
        # clears the mirror too, so it never false-alarms.
        s = self._sess()
        self._feed(s, "task_started", {"task_id": "b1", "description": "watcher"})
        reg = sb.read_reg(s.backend.state_dir, s.sid)
        self.assertEqual([t["desc"] for t in reg["bgTasks"]], ["watcher"])
        self._feed(s, "task_notification", {"task_id": "b1", "status": "completed",
                                            "output_file": "/tmp/x.output", "summary": "done"})
        self.assertEqual(sb.read_reg(s.backend.state_dir, s.sid)["bgTasks"], [])

    def test_session_gone_with_live_tasks_enqueues_the_death_notice_and_wakes(self):
        # the CLI died while the kernel lives: its bg tasks died with it — the session must HEAR that
        # (else it waits forever on a dead timer) and get woken to act on it. Our own drain (`ended`)
        # skips: the mirror survives for the next boot's reconcile instead.
        s = self._sess()
        be = s.backend
        self._feed(s, "task_started", {"task_id": "b1", "description": "power watcher"})
        be._ensured = []
        be._ensure = lambda sid, on_boot_settled=None: (be._ensured.append(sid), on_boot_settled and on_boot_settled())
        be._on_session_gone(s)
        reg = sb.read_reg(be.state_dir, s.sid)
        self.assertEqual(len(reg["queue"]), 1)
        self.assertIn("power watcher", reg["queue"][0])
        self.assertIn("romp-system", reg["queue"][0])
        self.assertEqual(reg["bgTasks"], [], "reported — never re-notify for the same deaths")
        self.assertEqual(be._ensured, [s.sid], "the session is woken to hear it")
        # drain/shutdown (`ended`): no notice now — the mirror stays for the next boot's reconcile
        s2 = self._sess()
        self._feed(s2, "task_started", {"task_id": "b2", "description": "timer"})
        s2.ended = True
        be2 = s2.backend
        be2._ensured = []
        be2._ensure = lambda sid, on_boot_settled=None: (be2._ensured.append(sid), on_boot_settled and on_boot_settled())
        be2._on_session_gone(s2)
        self.assertEqual(be2._ensured, [])
        self.assertEqual([t["desc"] for t in sb.read_reg(be2.state_dir, s2.sid)["bgTasks"]], ["timer"])

    def test_a_threads_crash_resume_hears_dead_tasks_once_after_the_nudge(self):
        # a comment thread's CLI dies mid-turn with the kernel alive: the crash resume spawns the
        # fresh session through _ensure, whose thread-wake report (the boot sweep never resumes a
        # thread, so a thread's dead life is reported at its wake) queues the task-death notice from
        # the reg mirror — and this method's own report from the in-memory set follows with the
        # identical text. The session hears it ONCE, after the continuation nudge: the order the
        # boot sweep gives a top-level session.
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)
        sid = "11111111-2222-3333-4444-00000000c0de"
        reg = {"sid": sid, "name": "n", "cwd": "/tmp", "alive": True,
               "threadOf": "11111111-2222-3333-4444-000000000000"}
        sb.write_reg(be.state_dir, sid, reg)
        s = sb.SdkSession(be, reg)
        self._feed(s, "task_started", {"task_id": "b1", "description": "release watcher"})
        note = sb.task_death_notice(s._live_bg_tasks())
        s.inflight = 1                                       # mid-turn: the crash-resume path
        made = []

        class _Rec:
            def __init__(self, backend, reg):
                made.append(dict(reg))
                self.thread = mock.Mock(is_alive=lambda: True)
                self.on_boot_settled = None

            def start(self):
                pass

        with mock.patch.object(sb, "SdkSession", _Rec):
            be._on_session_gone(s)
        self.assertEqual(made[0].get("queue"), [sb.CRASH_RESUME_NUDGE, note], "nudge first, the notice once")
        reg = sb.read_reg(be.state_dir, sid)
        self.assertEqual(reg["queue"], [sb.CRASH_RESUME_NUDGE, note], "the persisted queue agrees")
        self.assertEqual(reg["bgTasks"], [])

    def test_construction_heals_stranded_pending_switch_flags(self):
        # a pending /model / /effort switch that died with the previous process must not strand the
        # switching-dots (the user 2026-07-11): a fresh construction applies both at its next connect,
        # so pending is over — heal the reg at __init__.
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)
        sid = "11111111-2222-3333-4444-555555555555"
        sb.write_reg(be.state_dir, sid, {"sid": sid, "name": "n", "cwd": "/tmp", "alive": True,
                                         "effortPending": True, "modelPending": True})
        sb.SdkSession(be, sb.read_reg(be.state_dir, sid))
        reg = sb.read_reg(be.state_dir, sid)
        self.assertFalse(reg.get("effortPending"))
        self.assertFalse(reg.get("modelPending"))

    def test_started_tracks_the_task_and_the_snapshot_carries_it(self):
        s = self._sess()
        self._feed(s, "task_started", {"task_id": "b1", "description": "20-minute timer for campaign-start check",
                                       "task_type": "local_bash", "tool_use_id": "tu_1"})
        snap = s.snapshot()["bgTasks"]
        self.assertEqual(len(snap), 1)
        self.assertEqual(snap[0]["desc"], "20-minute timer for campaign-start check")
        self.assertEqual(snap[0]["toolUseId"], "tu_1", "carries the tool_use id — the join to the box's scan rows")

    def test_notification_always_ends_its_task(self):
        s = self._sess()
        self._feed(s, "task_started", {"task_id": "b1", "description": "watcher"})
        self._feed(s, "task_notification", {"task_id": "b1", "status": "completed",
                                            "output_file": "/tmp/x.output", "summary": "done"})
        self.assertEqual(s.snapshot()["bgTasks"], [])

    def test_updated_ends_only_on_a_terminal_patch_status(self):
        s = self._sess()
        self._feed(s, "task_started", {"task_id": "b1", "description": "watcher"})
        self._feed(s, "task_updated", {"task_id": "b1", "patch": {"end_time": 123}})   # no status → NOT terminal
        self.assertEqual(len(s.snapshot()["bgTasks"]), 1, "a status-less patch is not a terminal event")
        for status in ("killed", "failed", "stopped", "completed"):
            self._feed(s, "task_started", {"task_id": "t_" + status, "description": "x"})
            self._feed(s, "task_updated", {"task_id": "t_" + status, "patch": {"status": status}})
        self.assertEqual([t["desc"] for t in s.snapshot()["bgTasks"]], ["watcher"],
                         "every terminal status clears its task; the untouched one survives")

    def test_progress_self_heals_an_unknown_task_and_refreshes_fields(self):
        s = self._sess()
        self._feed(s, "task_progress", {"task_id": "b9", "description": "long build",
                                        "usage": {}, "last_tool_name": "Bash"})
        snap = s.snapshot()["bgTasks"]
        self.assertEqual((snap[0]["desc"], snap[0]["lastTool"]), ("long build", "Bash"),
                         "a progress event for an id we never saw ADDS it (mid-task attach converges)")

    def test_every_live_row_carries_its_lifecycle_task_id(self):
        # the CLI keys an Agent task's lifecycle by the AGENT ID (probe-verified on 2.1.257; _on_task_event
        # already retires the subagent by it). Shipping it on the row is what lets the kernel join the
        # stream's row to the SubagentStart hook's — without it the same agent listed twice in the
        # Awaiting box, once by type and once as "Running <description>" (2026-09-06).
        s = self._sess()
        self._feed(s, "task_started", {"task_id": "a1111111111111111", "description": "Running Map the parser",
                                       "task_type": "local_agent", "tool_use_id": "toolu_01"})
        self._feed(s, "task_started", {"task_id": "b2222", "description": "build the docs", "tool_use_id": "toolu_02"})
        rows = s.snapshot()["bgTasks"]
        self.assertEqual([(r["taskId"], r["toolUseId"]) for r in rows],
                         [("a1111111111111111", "toolu_01"), ("b2222", "toolu_02")])

    def test_a_task_id_less_event_is_ignored(self):
        s = self._sess()
        self._feed(s, "task_started", {"description": "no id"})
        self.assertEqual(s.snapshot()["bgTasks"], [])


class LiveAtomKinds(unittest.TestCase):
    """live_atom_kinds — the read-only DEBUG summary the kernel's chat-divergence tripwire logs (the
    2026-07-25 stale-"running" chat: the live atoms that held the turn open were cleared by a restart
    before anyone could read them; this accessor is how the tripwire captures them in time)."""

    def test_summarizes_live_atoms_without_mutating(self):
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)
        sid = "11111111-2222-3333-4444-555555555555"
        self.assertEqual(be.live_atom_kinds(sid), [], "no live tail → empty")
        be._live[sid] = {
            "k1": {"uuid": "u1", "type": "assistant", "t": 10,
                   "message": {"content": [{"type": "text", "text": "streamed reply"}]}},
            "k2": {"uuid": "u2", "type": "user", "t": 11, "_echo_text": "hi",
                   "message": {"content": "hi"}},
            "k3": "not-a-dict"}
        got = {a["uuid"]: a for a in be.live_atom_kinds(sid)}
        self.assertEqual(set(got), {"u1", "u2"}, "non-dict entries are skipped, atoms summarized")
        self.assertEqual((got["u1"]["type"], got["u1"]["hasText"], got["u1"]["echo"]),
                         ("assistant", True, False))
        self.assertTrue(got["u2"]["echo"])
        self.assertEqual(len(be._live[sid]), 3, "read-only: the live tail is untouched")


class RegListCache(unittest.TestCase):
    """list_regs' per-file parse cache (the 2026-08-10 CPU fix): the registry keeps a reg for every
    session EVER created, and list_regs sits on the liveness snapshot the kernel takes several times
    a second — re-parsing hundreds of unchanged files per sweep was a measured slice of the pusher's
    CPU burn. The cache keys on (mtime_ns, size, inode) — the file stays the truth — and hands out
    copies, so the _update_reg read-modify-write pattern can never corrupt it."""

    def setUp(self):
        self.sd = Path(tempfile.mkdtemp())
        (self.sd / "sdk").mkdir()
        sb.write_reg(self.sd, "aaaa", {"sid": "aaaa", "alive": True, "name": "web"})
        sb.write_reg(self.sd, "bbbb", {"sid": "bbbb", "alive": False, "name": "api"})

    def test_unchanged_files_serve_cached_parses_with_equal_content(self):
        first = sorted(sb.list_regs(self.sd), key=lambda r: r["sid"])
        second = sorted(sb.list_regs(self.sd), key=lambda r: r["sid"])
        self.assertEqual(first, second)
        self.assertEqual([r["sid"] for r in first], ["aaaa", "bbbb"])

    def test_a_mutated_result_never_leaks_into_the_cache(self):
        one = next(r for r in sb.list_regs(self.sd) if r["sid"] == "aaaa")
        one["name"] = "clobbered"          # the _update_reg pattern mutates its read
        again = next(r for r in sb.list_regs(self.sd) if r["sid"] == "aaaa")
        self.assertEqual(again["name"], "web", "the cache hands out copies, never its own dict")

    def test_a_rewrite_is_picked_up(self):
        # write_reg replaces the file (new inode), so even a same-instant rewrite misses the cache
        sb.list_regs(self.sd)              # warm
        sb.write_reg(self.sd, "aaaa", {"sid": "aaaa", "alive": True, "name": "renamed"})
        got = next(r for r in sb.list_regs(self.sd) if r["sid"] == "aaaa")
        self.assertEqual(got["name"], "renamed")

    def test_a_deleted_reg_drops_out(self):
        sb.list_regs(self.sd)              # warm
        (self.sd / "sdk" / "bbbb.json").unlink()
        self.assertEqual([r["sid"] for r in sb.list_regs(self.sd)], ["aaaa"])


class PushSessionCallback(unittest.TestCase):
    """_push_session — the connect handshake's targeted one-session push (2026-08-10). The handshake is
    the exact event the kernel's opening chip stands down on, and a plain pusher wake left that flip
    riding the next FULL push cycle (seconds on a busy fleet) — so the flip pushes its one session
    directly. Threaded, because the callback builds+serializes a payload and must never run on the
    session's asyncio loop thread."""

    SID = "11111111-2222-3333-4444-555555555555"

    def test_threaded_callback_receives_the_sid(self):
        got, done = [], threading.Event()
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None,
                           push_session=lambda sid: (got.append(sid), done.set()))
        be._push_session(self.SID)
        self.assertTrue(done.wait(5), "the callback fires, on its own thread")
        self.assertEqual(got, [self.SID])

    def test_without_the_callback_it_falls_back_to_the_pusher_wake(self):
        # an older kernel (or a test) that didn't wire push_session still gets the pre-existing
        # behavior: the periodic pusher wake, never a silent no-op
        woke = []
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None,
                           push=lambda: woke.append(True))
        be._push_session(self.SID)
        self.assertEqual(woke, [True])

    def test_a_failing_callback_is_contained_and_logged(self):
        logs = []   # the ctor may log too (a missing-SDK note) — poll for THIS failure's line

        def boom(sid):
            raise RuntimeError("nope")

        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None,
                           push_session=boom, log=logs.append)
        be._push_session(self.SID)   # must not raise into the caller (the connect path)
        deadline = time.time() + 5
        while time.time() < deadline and not any("session push" in str(m) for m in logs):
            time.sleep(0.01)
        self.assertTrue(any("session push" in str(m) for m in logs),
                        "the failure is reported, not swallowed: %r" % logs)


class LiveSubagentsRetire(unittest.TestCase):
    """The lane's live subagent count only ever GREW (the user 2026-09-02, whose session read Working with
    37 subagents for hours). The CLI fires SubagentStart for every workflow agent but not SubagentStop for
    every one of them (probe-verified on CLI 2.1.257: a run with one agent on a nonexistent model got one
    stop hook; the failed agent's slot in the run's `workflow_progress` list read state "error" and
    nothing else), so the set is retired on the events that DO arrive: a run's per-agent
    progress list (an end state, or a slot re-minted for a retry), the run's end, a Task agent's own
    task end (its task_id IS the agent id), and the client teardown. Every id and uuid here is synthetic."""

    SID = "11111111-2222-3333-4444-666666666666"

    def _sess(self):
        self.logs, self.pokes = [], []
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None, log=self.logs.append,
                           poke=lambda: self.pokes.append(1))
        s = sb.SdkSession(be, {"sid": self.SID, "name": "web", "cwd": "/tmp"})
        s.inflight = 0                                          # the main turn is idle throughout
        return s

    def _start(self, s, aid, kind="workflow-subagent"):
        import asyncio
        asyncio.run(s._subagent_start_hook({"agent_id": aid, "agent_type": kind}, None, None))

    @staticmethod
    def _wf(index, aid, state, label="reader"):
        e = {"type": "workflow_agent", "index": index, "label": label, "state": state, "queuedAt": 1}
        if aid:
            e["agentId"] = aid
            e["startedAt"] = 2
        return e

    def test_background_work_counts_as_busy_for_the_quiet_gate(self):
        # T240: busy_count counted only in-flight turns, so a quiet deploy applied INSTANTLY over a
        # session running a Workflow (no turn in flight between its own turns) and killed it — eight
        # review runs lost in one night. Background work makes the session busy; the breakdown is
        # separate so the manager can hold new turn starts only for turns that are actually in flight.
        s = self._sess()
        be = s.backend
        be.sessions[s.sid] = s
        self.assertEqual(be.busy_breakdown(), (0, 0))
        self.assertEqual(be.busy_count(), 0)
        s._on_task_event("task_started", {"task_id": "w1", "task_type": "local_workflow"})
        self.assertEqual(be.busy_breakdown(), (0, 1), "a live workflow with no turn in flight is background work")
        self.assertEqual(be.busy_count(), 1)
        s._on_task_event("task_notification", {"task_id": "w1", "status": "completed"})
        self.assertEqual(be.busy_breakdown(), (0, 0), "ended → not busy")
        self.assertEqual(be.busy_count(), 0)
        self._start(s, "a1")
        self.assertEqual(be.busy_breakdown(), (0, 1), "a live background agent counts the same way")
        s.inflight = 1
        self.assertEqual(be.busy_breakdown(), (1, 0), "a session is counted ONCE — in flight wins")
        self.assertEqual(be.busy_count(), 1)

    def test_a_failed_workflow_agent_retires_on_the_runs_progress_list(self):
        """The shape the probe recorded: the run's task_progress re-ships the whole per-agent list on every
        state change; the failed agent's slot flips to "error" with no SubagentStop ever following."""
        s = self._sess()
        s._on_task_event("task_started", {"task_id": "w1", "task_type": "local_workflow", "description": "review"})
        self._start(s, "a1"); self._start(s, "a2")
        s._on_task_event("task_progress", {"task_id": "w1", "workflow_progress": [
            self._wf(1, "a1", "start"), self._wf(2, "a2", "start"), self._wf(3, None, "start")]})   # 3rd still queued
        self.assertEqual(set(s._subagents), {"a1", "a2"}, "start states retire nothing")
        self.assertEqual(s.snapshot()["state"], "working", "live agents keep the session working")
        n0 = len(self.pokes)
        s._on_task_event("task_progress", {"task_id": "w1", "workflow_progress": [
            self._wf(1, "a1", "progress"), self._wf(2, "a2", "error"), self._wf(3, None, "start")]})
        self.assertEqual(set(s._subagents), {"a1"}, "the failed agent retires on its error state — no stop hook came")
        self.assertGreater(len(self.pokes), n0, "the retirement pushes a build now, not at the backstop")
        n1 = len(self.pokes)
        s._on_task_event("task_progress", {"task_id": "w1"})   # a throttled tick without the list changes nothing
        self.assertEqual(set(s._subagents), {"a1"})
        self.assertEqual(len(self.pokes), n1, "…and a tick that changed nothing pushes nothing")
        s._on_task_event("task_progress", {"task_id": "w1", "workflow_progress": [
            self._wf(1, "a1", "done"), self._wf(2, "a2", "error")]})
        self.assertEqual(s._subagents, {}, "a done state retires too (its stop hook would only be a no-op)")
        self.assertEqual(s.snapshot()["state"], "waiting", "and the session idles once the set empties")

    def test_b_the_runs_end_retires_every_agent_it_listed(self):
        """A run's end is the end of everything it ever listed, whatever state the slot last showed."""
        s = self._sess()
        s._on_task_event("task_started", {"task_id": "w1", "task_type": "local_workflow"})
        self._start(s, "a1"); self._start(s, "a2")
        s._on_task_event("task_progress", {"task_id": "w1", "workflow_progress": [
            self._wf(1, "a1", "start"), self._wf(2, "a2", "progress")]})
        s._on_task_event("task_notification", {"task_id": "w1", "status": "completed"})
        self.assertEqual(s._subagents, {}, "both listed agents retire at the run's end")
        self.assertNotIn("w1", s._wf_agents, "the run's roster is dropped with it")
        self.assertEqual(s.snapshot()["state"], "waiting")

    def test_c_an_agent_no_run_listed_is_never_inferred_dead(self):
        """Every retirement keys on an event about the agent. An agent no run has listed yet is NOT retired
        because some other run ended and "no run is live any more" — that is inference from absence, and an
        earlier draft that did it would have retired a live agent had the events ever landed in this order
        (review 2026-09-02). It stays until its own end arrives: here its run's list naming it done."""
        s = self._sess()
        s._on_task_event("task_started", {"task_id": "w1", "task_type": "local_workflow"})
        self._start(s, "b1")                                    # w2's first agent — its task_started still queued
        s._on_task_event("task_notification", {"task_id": "w1", "status": "completed"})
        self.assertEqual(set(s._subagents), {"b1"}, "w1's end says nothing about an agent w1 never listed")
        self.assertEqual(s.snapshot()["state"], "working", "the live agent still holds the session working")
        s._on_task_event("task_started", {"task_id": "w2", "task_type": "local_workflow"})
        s._on_task_event("task_progress", {"task_id": "w2", "workflow_progress": [self._wf(1, "b1", "done")]})
        self.assertEqual(s._subagents, {}, "its own run's list is what ends it")

    def test_c2_a_retried_slot_ends_the_attempt_it_displaced(self):
        """A retried workflow agent is re-minted with a NEW id in the SAME slot; the first attempt got a
        SubagentStart and nothing else, so the slot changing hands is its end."""
        s = self._sess()
        s._on_task_event("task_started", {"task_id": "w1", "task_type": "local_workflow"})
        self._start(s, "a1")
        s._on_task_event("task_progress", {"task_id": "w1", "workflow_progress": [self._wf(1, "a1", "start")]})
        self._start(s, "a1r")                                   # the retry, same slot
        s._on_task_event("task_progress", {"task_id": "w1", "workflow_progress": [self._wf(1, "a1r", "start")]})
        self.assertEqual(set(s._subagents), {"a1r"}, "the displaced attempt is over; the retry is live")
        s._on_task_event("task_progress", {"task_id": "w1", "workflow_progress": [self._wf(1, "a1r", "done")]})
        self.assertEqual(s._subagents, {})
        s._on_task_event("task_notification", {"task_id": "w1", "status": "completed"})
        self.assertNotIn("w1", s._wf_slots, "the run's slots are dropped with it")

    def test_d_a_task_agents_own_task_end_retires_it(self):
        """A Task/Agent subagent's lifecycle task carries the agent id as its task_id (probe-verified), so
        the task ending retires the agent — here as a failure. Whether a failed Task agent gets a
        SubagentStop is unverified (the probe saw a failed WORKFLOW agent get none); its task end retires
        it either way."""
        s = self._sess()
        self._start(s, "t1", "general-purpose")
        s._on_task_event("task_started", {"task_id": "t1", "task_type": "local_agent", "subagent_type": "general-purpose"})
        self.assertEqual(s.snapshot()["state"], "working")
        s._on_task_event("task_notification", {"task_id": "t1", "status": "failed"})
        self.assertEqual(s._subagents, {}, "the task's end is the agent's end")
        self.assertEqual(s._bg_tasks, {}, "the task itself cleared as before")
        self.assertEqual(s.snapshot()["state"], "waiting")

    def test_e_a_task_agents_progress_never_touches_the_workflow_path(self):
        """A local_agent task's progress is not a workflow list; nothing retires and nothing raises."""
        s = self._sess()
        self._start(s, "t1", "Explore")
        s._on_task_event("task_started", {"task_id": "t1", "task_type": "local_agent"})
        s._on_task_event("task_progress", {"task_id": "t1", "last_tool_name": "Read"})
        self.assertEqual(set(s._subagents), {"t1"})
        self.assertEqual(s._wf_agents, {}, "no roster is minted for a non-workflow task")

    def test_f_the_client_teardown_drops_the_abandoned_clients_agents_and_tasks(self):
        """A reconnect abandons the CLI process the agents and background tasks ran inside: they died with
        it and their hooks/notifications can never arrive, so the loop top forgets the agents, retires the
        tasks, queues the same death notice a CLI death does (once), clears the reg mirror, and logs."""
        s = self._sess()
        sb.write_reg(s.backend.state_dir, self.SID, {"sid": self.SID, "name": "web", "cwd": "/tmp", "alive": True})
        s._on_task_event("task_started", {"task_id": "w1", "task_type": "local_workflow", "description": "review sweep"})
        s._on_task_event("task_started", {"task_id": "b1", "task_type": "local_bash", "description": "watch the build"})
        self._start(s, "a1"); self._start(s, "a2")
        s._on_task_event("task_progress", {"task_id": "w1", "workflow_progress": [self._wf(1, "a1", "start")]})
        self.assertEqual(s.snapshot()["state"], "working")
        s._drop_live_work("reconnect")
        self.assertEqual(s._subagents, {})
        self.assertEqual(s._wf_agents, {})
        self.assertEqual(s._wf_slots, {})
        self.assertEqual(s._bg_tasks, {}, "the tasks died with the CLI too — their notifications can never arrive")
        self.assertEqual(s.snapshot()["state"], "waiting")
        self.assertEqual(s.snapshot()["bgTasks"], [])
        notes = [q for q in s.pending() if "background task" in q]
        self.assertEqual(len(notes), 1, "the session is told what it lost: %r" % s.pending())
        self.assertEqual(notes[0], sb.task_death_notice([{"desc": "review sweep"}, {"desc": "watch the build"}],
                                                        cause=sb.SdkSession._RECONNECT_CAUSE),
                         "the very copy the session reads, with the cause named truthfully")
        self.assertIn("(a deliberate restart)", notes[0], "the person's words: no romp operation name")
        self.assertNotIn("crash", notes[0], "a reconnect is neither a crash nor an unexplained restart")
        self.assertEqual(sb.read_reg(s.backend.state_dir, self.SID).get("bgTasks"), [], "mirror cleared: reported once")
        self.assertTrue(any("dropped 2 subagents and 2 background tasks on reconnect" in str(m) for m in self.logs), self.logs)
        self.logs.clear()
        s._drop_live_work("reconnect")
        self.assertFalse(self.logs, "an empty set drops silently — the first connect is not an event worth a line")
        self.assertEqual(len([q for q in s.pending() if "background task" in q]), 1, "no second notice for nothing")

    def test_f2_a_flapping_reconnect_does_not_stack_the_same_notice(self):
        s = self._sess()
        for _ in range(2):
            s._on_task_event("task_started", {"task_id": "b1", "task_type": "local_bash", "description": "watch"})
            s._drop_live_work("reconnect")
        self.assertEqual(len([q for q in s.pending() if "background task" in q]), 1, s.pending())

    def test_g_the_reconnect_loop_top_calls_the_drop_before_reconciling(self):
        """Pin the wiring: the drop runs at the loop top, before _reconcile_stranded, every iteration."""
        src = open(os.path.join(BIN, "romp_sdk_backend.py"), encoding="utf-8").read()
        i = src.index('self._drop_live_work("reconnect")')
        j = src.index("self._reconcile_stranded()")
        self.assertLess(i, j, "the drop precedes the stranded-turn reconcile at the loop top")
        k = src.rfind("while not self.ended:", 0, i)
        self.assertGreater(k, 0)
        self.assertNotIn("async with ClaudeSDKClient", src[k:i], "…inside the reconnect loop, before the connect")

    def test_i_a_run_seen_only_through_its_progress_list_still_retires(self):
        """A backend that attached mid-run never saw the run's task_started (the self-heal path); the
        per-agent list is shipped only by Workflow runs, so its presence types the entry and the run's
        error states and end retire its agents like any other."""
        s = self._sess()
        self._start(s, "a1"); self._start(s, "a2")
        s._on_task_event("task_progress", {"task_id": "w7", "workflow_progress": [
            self._wf(1, "a1", "error"), self._wf(2, "a2", "progress")]})
        self.assertEqual(s._bg_tasks["w7"]["type"], "local_workflow", "the entry learned what it is from the list")
        self.assertEqual(set(s._subagents), {"a2"}, "the failed agent retired on the first list seen")
        s._on_task_event("task_notification", {"task_id": "w7", "status": "completed"})
        self.assertEqual(s._subagents, {}, "the run's end retires the rest")

    def test_h_a_clean_stop_hook_still_retires_exactly_its_own_agent(self):
        """The designed path is untouched: a SubagentStop retires its agent and no other, and a later
        progress list naming it as done is a harmless no-op."""
        import asyncio
        s = self._sess()
        s._on_task_event("task_started", {"task_id": "w1", "task_type": "local_workflow"})
        self._start(s, "a1"); self._start(s, "a2")
        asyncio.run(s._subagent_stop_hook({"agent_id": "a1", "agent_type": "workflow-subagent"}, None, None))
        self.assertEqual(set(s._subagents), {"a2"})
        s._on_task_event("task_progress", {"task_id": "w1", "workflow_progress": [
            self._wf(1, "a1", "done"), self._wf(2, "a2", "progress")]})
        self.assertEqual(set(s._subagents), {"a2"})


class SettingsPickWaitsForLiveWork(unittest.TestCase):
    """A settings pick (effort, permission mode into bypass, fast mode's first opt-in, billing) applies by
    reconnecting the CLI, and the reconnect abandons every subagent, Workflow run and background task
    inside that process (_drop_live_work). Until 2026-09-09 the arm read only the open turn: a session
    idle between its own turns while a background agent ran read quiet, the teardown fired at once, and
    the work died (26 subagents and 10 background tasks across four sessions in one day, to picks that
    changed nothing). Now a settings-driven reconnect waits for the live sets to empty, and ONE event
    arms a held pick: a turn's ResultMessage settle that finds the sets empty (the settle-only rule,
    review round 2). No removal from the sets arms at its own frame: the CLI starts a turn of its own to
    deliver a background task's result whatever its type (probed on CLI 2.1.266: an agent's, a Workflow
    run's, a shell command's and a Monitor's end are each followed 30 to 90 ms later by system/init and
    a model reply), and an arm at the end frame cut that very turn; the removal sites log one line
    naming what ended and that the pick waits for the next settle. So a pick held after a shell task's
    end waits for the next turn to finish, the same as after an agent's. A pick equal to the launched
    value requests no reconnect at all; during a spawn the compare is against the shape being launched.
    A rewind keeps its old behaviour: it replaces the conversation from a point, and the work inside the
    old process is what it discards, and its arm over a hold has its own log line. Private synthetic sid
    (this class's own, never the shared placeholder: a journaled override against a shared sid replays
    into every test that minted the same node id); every id and name here is invented."""

    SID = "5e771e5d-9a1c-4b0f-8d2e-000000000437"   # private synthetic sid, never the shared placeholder

    class _Now:
        """A loop double: request_reconnect's call_soon_threadsafe runs the callback at once, here."""
        def call_soon_threadsafe(self, cb, *a):
            cb(*a)

    class _Queue:
        """A loop double that QUEUES: the callbacks run when the test flushes them, in order, as the loop
        thread would serve them after the kernel thread's picks."""
        def __init__(self):
            self.queued = []

        def call_soon_threadsafe(self, cb, *a):
            self.queued.append((cb, a))

        def flush(self):
            while self.queued:
                cb, a = self.queued.pop(0)
                cb(*a)

    class _Res:
        uuid = "r1"
        num_turns = 1

    class _ParkingSet(set):
        """The surface set with ONE read parked (the race tests, review round 5): the first call matching `where`
        ("any" for the first read of any kind, a method name, or ("__contains__", x) for the check of x) computes
        its value, signals `parked` and waits for `resume`, so the test can run the other thread between the parked
        thread's reads. The value is computed BEFORE the park, so what the parked thread has already read stands
        and what it reads next sees the other thread's write (or, under the lock, never sees it)."""
        def __init__(self, items, where, parked, resume):
            super().__init__(items)
            self._where, self._parked, self._resume, self._armed = where, parked, resume, True

        def _park(self, name, arg=None):
            if self._armed and self._where in ("any", name, (name, arg)):
                self._armed = False
                self._parked.set()
                self._resume.wait(5)

        def __len__(self):
            n = super().__len__()
            self._park("__len__")
            return n

        def __contains__(self, x):
            r = super().__contains__(x)
            self._park("__contains__", x)
            return r

    class _WatchedLock:
        """The session's hold lock, wrapped so the test knows when thread `watch` reaches it: with the lock in
        place the other thread's write blocks here while the parked read holds it; at a head without the lock
        (the one these tests are red at) the write lands between the reads instead."""
        def __init__(self, real, watch, reached):
            self._real, self._watch, self._reached = real, watch, reached

        def __enter__(self):
            if threading.current_thread().name == self._watch:
                self._reached.set()
            self._real.acquire()
            return self

        def __exit__(self, *a):
            self._real.release()

    def _race(self, s, where, loop_side, kernel_side):
        """Two threads sequenced through events (review round 5): L runs `loop_side` (a loop-thread routine) with
        one read of the surface set parked at `where`; K then runs `kernel_side` (a kernel-thread pick or revert);
        L resumes once K has FINISHED (no lock: K's write landed between L's reads) or is BLOCKED on the hold lock
        (the lock made L's read sequence atomic, and K's write waits for it). Both worlds run to completion; what
        differs is the state each leaves, which the caller asserts. Returns the exception L raised, or None."""
        parked, resume, k_at_lock, k_done = [threading.Event() for _ in range(4)]
        s._reconnect_surfaces = self._ParkingSet(s._reconnect_surfaces, where, parked, resume)
        if hasattr(s, "_hold_lock"):
            s._hold_lock = self._WatchedLock(s._hold_lock, "K", k_at_lock)
        err = []

        def run_l():
            try:
                loop_side()
            except Exception as e:
                err.append(e)

        def run_k():
            kernel_side()
            k_done.set()

        lt, kt = threading.Thread(target=run_l, name="L"), threading.Thread(target=run_k, name="K")
        lt.start()
        self.assertTrue(parked.wait(5), "the loop side never reached the parked read")
        kt.start()
        deadline = time.monotonic() + 5
        while not (k_done.is_set() or k_at_lock.is_set()):
            self.assertLess(time.monotonic(), deadline, "the kernel side neither finished nor reached the hold lock")
            time.sleep(0.001)
        resume.set()
        lt.join(5); kt.join(5)
        self.assertFalse(lt.is_alive() or kt.is_alive(), "a thread hung")
        return err[0] if err else None

    def setUp(self):
        self._dirs = []

    def tearDown(self):
        # the repo rule for goal-store fixtures: this sid's override journal never outlives the test (the
        # class mints no goals today; the cleanup keeps that true for whoever adds one). And the state
        # dirs go with the test: a leaked tempdir per _sess filled /tmp (2026-09-06)
        j = Path(os.environ["XDG_STATE_HOME"]) / "romp" / "overrides" / (self.SID + ".jsonl")
        if j.exists():
            j.unlink()
        for d in self._dirs:
            shutil.rmtree(d, ignore_errors=True)

    def _sess(self, **reg):
        self.logs, self.pokes = [], []
        self._dirs.append(tempfile.mkdtemp())
        be = sb.SdkBackend(self._dirs[-1], "/bin/true", lambda *a, **k: None, log=self.logs.append,
                           poke=lambda: self.pokes.append(1))
        sb.write_reg(be.state_dir, self.SID, {"sid": self.SID, "name": "web", "cwd": "/tmp", "alive": True, **reg})
        s = sb.SdkSession(be, sb.read_reg(be.state_dir, self.SID))
        s.inflight = 0                                          # idle between its own turns
        s.loop = self._Now()
        be.sessions[self.SID] = s
        return s

    @staticmethod
    def _start(s, aid, kind="general-purpose"):
        asyncio.run(s._subagent_start_hook({"agent_id": aid, "agent_type": kind}, None, None))

    @staticmethod
    def _stop(s, aid):
        return asyncio.run(s._subagent_stop_hook({"agent_id": aid, "agent_type": "general-purpose"}, None, None))

    def _settle(self, s):
        """One ResultMessage through the settle, the turn's end: for a background agent this is the end
        of the turn the CLI started to deliver the agent's result. Returns the arm state after it."""
        async def _noop(): pass
        s._do_refresh_usage = _noop
        s._do_refresh_context = _noop
        s.inflight = 1
        out = {}

        async def run():
            s.loop = asyncio.get_running_loop()
            s._input_wake = asyncio.Event()
            s._wake = asyncio.Event()
            out["ok"] = s._handle_stream_message(self._Res(), _AssistantMessage, self._Res, type("S", (), {}))
            await asyncio.sleep(0)
            out.update(reconnect=s._reconnect, deferred=s._reconnect_when_idle, wake=s._wake.is_set())
        asyncio.run(run())
        s.loop = self._Now()
        return out

    def _held(self):
        return [str(m) for m in self.logs if "held for" in str(m)]

    def _armed(self):
        return [str(m) for m in self.logs if "live work finished" in str(m)]

    def _ended(self):
        """The removal sites' lines: what ended, and that the pick waits for the next turn's settle."""
        return [str(m) for m in self.logs if "waits for the next turn's settle" in str(m)]

    def _seed(self, s):
        return sb.read_sdk_defaults(s.backend.state_dir)

    def test_a_an_effort_pick_over_a_live_subagent_holds_the_reconnect(self):
        s = self._sess()
        self._start(s, "a1")
        self.assertTrue(s.backend.set_effort(self.SID, "max"))
        self.assertFalse(s._reconnect, "the teardown must not arm while a subagent runs inside the CLI")
        self.assertTrue(s._reconnect_when_idle, "the pick waits for the live work to end")
        self.assertEqual(s._effort_pending, "max", "the badge shows the pick applying meanwhile")
        held = self._held()
        self.assertEqual(len(held), 1, self.logs)
        self.assertIn("effort (web): set to max; reconnect held for 1 subagent and 0 background tasks", held[0])

    def test_b_the_last_subagents_stop_leaves_the_arm_to_the_delivery_turns_settle(self):
        # the CLI starts a turn of its own to deliver a background agent's result, 27 to 92 ms after the
        # agent's end frames; an arm at the stop hook closed stdin under that turn and the teardown cut it
        # at the grace (the agent's reply to its own result was lost; the session stayed idle)
        s = self._sess()
        self._start(s, "a1"); self._start(s, "a2")
        s.backend.set_effort(self.SID, "max")
        self.assertFalse(s._reconnect)
        self._stop(s, "a1")
        self.assertFalse(s._reconnect, "one subagent still runs: not yet")
        self._stop(s, "a2")
        self.assertEqual(s._subagents, {}, "the set emptied")
        self.assertFalse(s._reconnect, "an agent's end is delivered by a turn: the stop must NOT arm")
        self.assertTrue(s._reconnect_when_idle, "the pick stays pending for that turn's settle")
        self.assertEqual(self._armed(), [])
        out = self._settle(s)
        self.assertTrue(out["ok"])
        self.assertTrue(out["reconnect"], "the delivery turn's settle is THE event that arms")
        self.assertFalse(out["deferred"])
        self.assertTrue(out["wake"])
        armed = self._armed()
        self.assertEqual(len(armed), 1, self.logs)
        self.assertIn("reconnect (web): live work finished; the held effort pick reconnects now", armed[0])

    def test_b2_a_shell_tasks_end_leaves_the_arm_to_the_settle_and_names_itself_in_the_log(self):
        # round 1 armed at a shell or monitor task's end on a 2026-08-18 queue census (enqueued, never
        # dequeued) that had counted a stuck regime; probed on 2.1.266 the CLI starts a delivery turn 30 to
        # 90 ms after a local_bash end too (a plain background Bash, a Monitor exiting or timing out), and
        # the immediate arm cut it (rc 143, no reply). The settle-only rule (review round 2): the end never
        # arms, one line says what ended and that the pick waits, and the next settle arms
        s = self._sess()
        s._on_task_event("task_started", {"task_id": "b1", "task_type": "local_bash", "description": "watch the build"})
        s.backend.set_effort(self.SID, "max")
        self.assertFalse(s._reconnect); self.assertTrue(s._reconnect_when_idle)
        self.assertIn("reconnect held for 0 subagents and 1 background task", self._held()[0])
        s._on_task_event("task_notification", {"task_id": "b1", "status": "completed"})
        self.assertFalse(s._reconnect, "a shell task's end is delivered by a turn like any other: no arm here")
        self.assertTrue(s._reconnect_when_idle)
        self.assertEqual(self._armed(), [])
        ended = self._ended()
        self.assertEqual(len(ended), 1, self.logs)
        self.assertIn("reconnect (web): a local_bash task ended; the live sets are empty; the pending effort pick "
                      "waits for the next turn's settle", ended[0])
        self.assertEqual(s.snapshot()["pickHeld"], {"surfaces": ["effort"], "subagents": 0, "tasks": 0, "inflight": False},
                         "held through the delivery turn: the one marker stands until the settle")
        out = self._settle(s)
        self.assertTrue(out["reconnect"] and not out["deferred"])
        self.assertIn("the held effort pick reconnects now", self._armed()[0])
        s = self._sess()
        s._on_task_event("task_started", {"task_id": "b2", "task_type": "local_bash"})
        s.backend.set_effort(self.SID, "max")
        s._on_task_event("task_updated", {"task_id": "b2", "patch": {"status": "killed"}})   # a terminal patch, too
        self.assertFalse(s._reconnect, "a terminal task_updated status is the same end: deferred")
        self.assertEqual(len(self._ended()), 1)
        self.assertTrue(self._settle(s)["reconnect"])
        # the MCP and websocket monitors, the same
        for kind in ("monitor_mcp", "monitor_ws"):
            s = self._sess()
            s._on_task_event("task_started", {"task_id": "m1", "task_type": kind})
            s.backend.set_effort(self.SID, "max")
            s._on_task_event("task_notification", {"task_id": "m1", "status": "completed"})
            self.assertFalse(s._reconnect, kind)
            self.assertIn("a %s task ended" % kind, self._ended()[0])
            self.assertTrue(self._settle(s)["reconnect"], kind)
        # under an open turn the same: that turn's settle arms
        s = self._sess()
        s._on_task_event("task_started", {"task_id": "b3", "task_type": "local_bash"})
        s.backend.set_effort(self.SID, "max")
        s.inflight = 1
        s._on_task_event("task_notification", {"task_id": "b3", "status": "completed"})
        self.assertFalse(s._reconnect, "a turn is open: its settle is the event")
        self.assertTrue(self._settle(s)["reconnect"])
        # and a task ending with no pick pending writes no line at all
        s = self._sess()
        s._on_task_event("task_started", {"task_id": "b4", "task_type": "local_bash"})
        s._on_task_event("task_notification", {"task_id": "b4", "status": "completed"})
        self.assertEqual(self._ended(), [])

    def test_b3_not_while_the_other_set_is_still_populated(self):
        s = self._sess()
        self._start(s, "a1")
        s._on_task_event("task_started", {"task_id": "b1", "task_type": "local_bash"})
        s.backend.set_effort(self.SID, "max")
        self.assertIn("1 subagent and 1 background task", self._held()[0])
        s._on_task_event("task_notification", {"task_id": "b1", "status": "completed"})
        self.assertFalse(s._reconnect, "the task ended; the subagent still runs")
        self.assertTrue(s._reconnect_when_idle)
        self._stop(s, "a1")
        self.assertFalse(s._reconnect, "the agent's end is delivered by a turn")
        self.assertTrue(self._settle(s)["reconnect"])
        # and the mirror image: the agent ends first, then the shell task; neither end arms, each is logged
        s = self._sess()
        self._start(s, "a1")
        s._on_task_event("task_started", {"task_id": "b1", "task_type": "local_bash"})
        s.backend.set_effort(self.SID, "max")
        self._stop(s, "a1")
        self.assertFalse(s._reconnect, "the subagent ended; the task still runs")
        self.assertIn("a subagent ended; 0 subagents and 1 background task still run", self._ended()[0])
        s._on_task_event("task_notification", {"task_id": "b1", "status": "completed"})
        self.assertFalse(s._reconnect, "the last end is not the arm either (review round 2)")
        self.assertIn("a local_bash task ended; the live sets are empty", self._ended()[1])
        self.assertTrue(self._settle(s)["reconnect"])

    def test_b4_a_workflow_runs_end_defers_to_the_settle_like_an_agents(self):
        s = self._sess()
        s._on_task_event("task_started", {"task_id": "w1", "task_type": "local_workflow"})
        self._start(s, "a1", "workflow-subagent")
        row = {"type": "workflow_agent", "index": 1, "label": "reader", "state": "start", "queuedAt": 1,
               "agentId": "a1", "startedAt": 2}
        s._on_task_event("task_progress", {"task_id": "w1", "workflow_progress": [row]})
        s.backend.set_effort(self.SID, "max")
        self.assertFalse(s._reconnect)
        s._on_task_event("task_progress", {"task_id": "w1", "workflow_progress": [dict(row, state="error")]})
        self.assertEqual(s._subagents, {}, "the failed agent retired on its error state")
        self.assertFalse(s._reconnect, "the run itself is still a live background task")
        s._on_task_event("task_notification", {"task_id": "w1", "status": "completed"})
        self.assertEqual(s._bg_tasks, {}); self.assertEqual(s._wf_agents, {})
        self.assertFalse(s._reconnect, "a run's end may be delivered by a turn: not at the notification")
        self.assertTrue(s._reconnect_when_idle)
        out = self._settle(s)
        self.assertTrue(out["reconnect"] and not out["deferred"])
        self.assertEqual(len(self._armed()), 1)
        # the terminal ordering the roster can take: the run ends with its agent still listed live
        s = self._sess()
        s._on_task_event("task_started", {"task_id": "w2", "task_type": "local_workflow"})
        self._start(s, "a2", "workflow-subagent")
        s._on_task_event("task_progress", {"task_id": "w2", "workflow_progress": [dict(row, agentId="a2")]})
        s.backend.set_effort(self.SID, "max")
        s._on_task_event("task_notification", {"task_id": "w2", "status": "completed"})
        self.assertEqual((s._subagents, s._bg_tasks), ({}, {}), "the run's end ends every agent it listed")
        self.assertFalse(s._reconnect)
        self.assertTrue(self._settle(s)["reconnect"])

    def test_b5_a_background_agents_own_task_counts_once_and_defers(self):
        # a Task/Agent subagent's lifecycle task carries the AGENT ID as its task_id, so the same id sits
        # in both live sets: the counts join it out (one agent, not "1 subagent and 1 background task")
        s = self._sess()
        self._start(s, "a1")
        s._on_task_event("task_started", {"task_id": "a1", "task_type": "local_agent", "description": "review the diff"})
        self.assertEqual(s._live_work_counts(), (1, 0))
        s.backend.set_effort(self.SID, "max")
        self.assertIn("reconnect held for 1 subagent and 0 background tasks", self._held()[0])
        self._stop(s, "a1")
        self.assertFalse(s._reconnect, "the stop hook alone leaves the agent's task live")
        self.assertEqual(s._live_work_counts(), (0, 1), "the task entry outlives the hook until its notification")
        s._on_task_event("task_notification", {"task_id": "a1", "status": "completed"})
        self.assertEqual(s._live_work_counts(), (0, 0))
        self.assertFalse(s._reconnect, "an agent's end: the delivery turn's settle arms, not the notification")
        self.assertTrue(s._reconnect_when_idle)
        self.assertTrue(self._settle(s)["reconnect"])
        # an agent plus a shell task still reads two, a run plus its agent two
        s = self._sess()
        self._start(s, "a1"); s._on_task_event("task_started", {"task_id": "b1", "task_type": "local_bash"})
        self.assertEqual(s._live_work_counts(), (1, 1))

    def test_b6_an_end_of_unknown_type_defers_to_the_settle_and_the_line_names_the_type(self):
        # a self-healed entry never saw its task_started, so its type is unknown; the CLI's other types
        # (mcp_task, remote_agent, in_process_teammate) defer like every end. The line names the type (or
        # says it was never learned), so an end the CLI never delivers as a turn can be placed in the log
        for kind in ("", "mcp_task", "remote_agent", "in_process_teammate", "some_new_type"):
            s = self._sess()
            s._on_task_event("task_started", {"task_id": "t1", **({"task_type": kind} if kind else {})})
            s.backend.set_effort(self.SID, "max")
            s._on_task_event("task_notification", {"task_id": "t1", "status": "completed"})
            self.assertFalse(s._reconnect, "type %r must defer" % kind)
            self.assertTrue(s._reconnect_when_idle)
            ended = self._ended()
            self.assertEqual(len(ended), 1, (kind, self.logs))
            self.assertIn("a %s task ended" % kind if kind else "a task of a type never learned ended", ended[0])
            self.assertNotIn("held for", ended[0]); self.assertNotIn("live work finished", ended[0])
            self.assertTrue(self._settle(s)["reconnect"], kind)

    def test_c_the_turn_end_settle_leaves_a_pick_held_while_work_runs(self):
        s = self._sess()
        self._start(s, "a1")
        s._reconnect_when_idle = True        # the pick landed mid-turn: deferred to the turn's end
        out = self._settle(s)
        self.assertTrue(out["ok"])
        self.assertEqual(s.inflight, 0, "the turn settled")
        self.assertFalse(out["reconnect"], "the turn ended, but the subagent still runs: no arm")
        self.assertTrue(out["deferred"], "the arm stays deferred until the work ends")
        self.assertFalse(out["wake"])
        held = self._held()
        self.assertEqual(len(held), 1, "the turn's end is where this pick became held for live work: one line")
        self.assertIn("reconnect (web): held for 1 subagent and 0 background tasks", held[0])
        self._stop(s, "a1")
        self.assertFalse(s._reconnect, "the stop is not the arm: the agent's delivery turn follows")
        out = self._settle(s)
        self.assertTrue(out["reconnect"] and not out["deferred"], "the delivery turn's settle arms it")
        self.assertEqual(len(self._held()), 1, "held once, said once")

    def test_c2_a_quiet_settle_still_arms_at_once(self):
        # the designed path is untouched: no live work, the deferred arm fires at the turn's end
        s = self._sess()
        s._reconnect_when_idle = True
        out = self._settle(s)
        self.assertTrue(out["reconnect"] and not out["deferred"] and out["wake"])
        self.assertEqual(self._held(), [])

    def test_d_a_billing_pick_over_live_work_holds_the_same_way(self):
        s = self._sess(auth="key")
        s._launched_auth = "key"
        self._start(s, "a1")
        self.assertTrue(s.backend.set_auth(self.SID, "login"))
        self.assertFalse(s._reconnect); self.assertTrue(s._reconnect_when_idle)
        self.assertEqual(s._auth_pending, "login")
        self.assertIn("auth (web): set to login; reconnect held for 1 subagent and 0 background tasks", self._held()[0])
        self._stop(s, "a1")
        self.assertFalse(s._reconnect)
        self.assertTrue(self._settle(s)["reconnect"])
        self.assertIn("the held auth pick reconnects now", self._armed()[0])

    def test_d2_two_held_picks_are_named_together_when_they_arm(self):
        s = self._sess(auth="key")
        s._launched_auth = "key"
        self._start(s, "a1")
        s.backend.set_effort(self.SID, "max")
        s.backend.set_auth(self.SID, "login")
        self.assertEqual(len(self._held()), 2, "each pick says it is held")
        self._stop(s, "a1")
        self._settle(s)
        self.assertIn("the held effort and auth picks reconnect now", self._armed()[0])

    def test_e_a_rewind_still_reconnects_over_live_work(self):
        # a rewind replaces the conversation from a point; the work inside the old process is what it
        # discards, and _RECONNECT_CAUSE still names it. Only the settings picks wait.
        s = self._sess()
        self._start(s, "a1")
        s._rewind_to = "22222222-3333-4444-5555-666666666666"
        s._rewind_armed = False
        s.request_reconnect()
        self.assertTrue(s._reconnect, "a rewind's queue cannot start until the reconnect arms it")
        self.assertFalse(s._reconnect_when_idle)
        self.assertEqual(self._held(), [])

    def test_e2_the_immediate_only_request_form_is_untouched(self):
        # request_reconnect(defer=False), the immediate-only form (its one production caller, the key cycle,
        # retired with romp's own key paths on 2026-09-09, so this is the form's pin). First the two cases
        # the pre-merge keyswap e2 pinned and main's key retire deleted (restored in review round 3): a
        # queued turn (_pending) on an otherwise quiet session drops the immediate form with its own line,
        # and the deferred form under the same queue defers
        s = self._sess()
        s._pending.append("a queued text")
        s._do_request_reconnect(defer=False)
        self.assertFalse(s._reconnect); self.assertFalse(s._reconnect_when_idle)
        self.assertTrue(any("became busy before the reconnect ran" in str(m) for m in self.logs), self.logs)
        s._do_request_reconnect(defer=True)
        self.assertTrue(s._reconnect_when_idle, "the deferred form waits for the queued turn's settle")
        self.assertFalse(s._reconnect)
        s._pending.clear(); s._reconnect_when_idle = False
        # over live work the immediate form drops the request with its own log line and arms nothing
        self._start(s, "a1")
        s._do_request_reconnect(defer=False)
        self.assertFalse(s._reconnect); self.assertFalse(s._reconnect_when_idle)
        self.assertTrue(any("live work registered before the reconnect ran" in str(m) for m in self.logs))
        self.assertEqual(self._held(), [])

    def test_e3_the_loop_top_clears_a_held_arm_the_rewind_took_over(self):
        # a rewind admitted during a hold reconnects over the live work; its connect reads the reg, so the
        # held pick rides it. The loop top used to clear only _reconnect: the deferred arm survived, and
        # the replacement turn's settle fired a second reconnect with a false "live work finished" line
        s = self._sess()
        self._start(s, "a1")
        s.backend.set_effort(self.SID, "max")
        self.assertTrue(s._reconnect_when_idle and s._reconnect_held_for_work)
        s._rewind_to = "22222222-3333-4444-5555-666666666666"
        s._rewind_armed = False
        s.request_reconnect()
        self.assertTrue(s._reconnect)
        s._reset_reconnect_state()             # what the loop top runs before it connects again
        s._drop_live_work("reconnect")         # and the teardown's retire of the old client's work
        self.assertFalse(s._reconnect); self.assertFalse(s._reconnect_when_idle)
        self.assertFalse(s._reconnect_held_for_work); self.assertEqual(s._reconnect_surfaces, set())
        self.assertIsNone(s.snapshot()["pickHeld"])
        rides = [str(m) for m in self.logs if "rides this reconnect" in str(m)]
        self.assertEqual(len(rides), 1, self.logs)
        self.assertIn("the pending effort pick rides this reconnect", rides[0])
        out = self._settle(s)
        self.assertFalse(out["reconnect"], "exactly one reconnect: the rewind's")
        self.assertFalse(out["deferred"])
        self.assertEqual(self._armed(), [], "no false 'live work finished' line")

    def test_e5_a_pick_riding_a_rewind_gets_the_arms_flips_at_the_rewinds_request(self):
        # a pending rewind's request set _reconnect itself, not through the arm, so a held auth or fast pick
        # riding it never got the arm's flips: after the landing the Billing row showed the contradiction
        # warning (the key picked, the login reported) until the new process's first init, which for a bare
        # rollback is the user's next message, and the fast badge stayed off under a flagged relaunch. One arm
        # routine now, whichever request arms (review round 4)
        s = self._sess(auth="login")
        s._launched_auth = "login"; s.auth_live = "login"
        s.thread = mock.Mock(is_alive=lambda: True)
        s.fast = "off"; s._fast_unlocked = False
        self._start(s, "a1")
        with mock.patch.object(sb.SdkBackend, "key_available", new_callable=mock.PropertyMock, return_value=True):
            self.assertTrue(s.backend.set_auth(self.SID, "key"))
            self.assertTrue(s.backend.set_fast(self.SID, "on"))
            self.assertTrue(s._reconnect_when_idle and s._reconnect_held_for_work)
            self.assertEqual((s.auth_live, s.fast), ("login", "off"), "held: nothing flips before the arm")
            s._rewind_to = "22222222-3333-4444-5555-666666666666"; s._rewind_armed = False
            s.request_reconnect()                                # the rewind's request arms at once, over the work
            self.assertTrue(s._reconnect)
            self.assertEqual(s.auth_live, "", "the arm clears the report: it described the process this reconnect replaces")
            self.assertEqual(s.fast, "on", "the arm's flip: the flag rides this connect")
            self.assertIsNotNone(s._launching, "the spawn window opens at this arm as at every other")
            self.assertEqual(s._launching["auth"], "key", "a keyed box: the helper bills the relaunch")
            s._reset_reconnect_state()                           # the loop top: the picks ride this reconnect
            rides = [str(m) for m in self.logs if " this reconnect" in str(m)]
            self.assertEqual(len(rides), 1, self.logs)
            self.assertIn("the pending fast and auth picks ride this reconnect", rides[0], "two picks: the plural verb")
            s._connect_landed()
        snap = s.snapshot()
        self.assertEqual((snap["auth"], snap["authLive"], snap["authPending"]), ("key", "", False), "no contradiction")
        self.assertEqual(snap["fast"], "on")
        self.assertIsNone(s._launching)

    def test_e6_the_loop_tops_ride_line_agrees_in_number(self):
        # the ride line was a fixed "rides this reconnect", so two picks read "the pending effort and auth picks
        # rides this reconnect" while the arm's sibling line already agreed in number (review round 4). One pick
        # rides; two ride; a lone restore rides; a pick and the restore ride; the no-names fallback rides
        def ride(s):
            s._rewind_to = "22222222-3333-4444-5555-666666666666"; s._rewind_armed = False
            s.request_reconnect()
            n0 = len(self.logs)
            s._reset_reconnect_state()
            lines = [str(m) for m in self.logs[n0:] if " this reconnect" in str(m)]
            self.assertEqual(len(lines), 1, self.logs[n0:])
            return lines[0]
        s = self._sess(effort="high", auth="login")
        s._launched_effort = sb.effort_launch_shape("high"); s._launched_auth = "login"
        self._start(s, "a1")
        s.backend.set_effort(self.SID, "max")
        with mock.patch.object(sb.SdkBackend, "key_available", new_callable=mock.PropertyMock, return_value=True):
            s.backend.set_auth(self.SID, "key")
        self.assertIn("reconnect (web): the pending effort and auth picks ride this reconnect", ride(s))
        s = self._sess(effort="high")
        s._launched_effort = sb.effort_launch_shape("high")
        self._start(s, "a1")
        s.backend.set_effort(self.SID, "max")
        self.assertIn("reconnect (web): the pending effort pick rides this reconnect", ride(s))
        s = self._sess()
        s.fast_opt = True
        self._start(s, "a1")
        s._adopt_fast_state({"fast_mode_state": "off", "fast_mode_disabled_reason": "extra_usage_disabled"})
        self.assertIn("reconnect (web): the pending fast mode restore rides this reconnect", ride(s))
        s = self._sess(effort="high")
        s._launched_effort = sb.effort_launch_shape("high"); s.fast_opt = True
        self._start(s, "a1")
        s._adopt_fast_state({"fast_mode_state": "off", "fast_mode_disabled_reason": "extra_usage_disabled"})
        s.backend.set_effort(self.SID, "max")
        self.assertIn("reconnect (web): the pending effort pick and fast mode restore ride this reconnect", ride(s))
        s = self._sess()
        self._start(s, "a1")
        s._reconnect_when_idle = True                                # a request that recorded no surface
        self.assertIn("reconnect (web): the pending reconnect rides this reconnect", ride(s))

    def test_e4_a_pick_the_session_cannot_reconnect_for_records_no_hold(self):
        # before the first connect (loop None) request_reconnect is a no-op and the reg carries the pick
        # to the connect; the setter's line says so, and neither the surface nor the hold is recorded
        # (a later held pick's arm line used to name this one too)
        s = self._sess()
        s.loop = None
        self.assertTrue(s.backend.set_effort(self.SID, "max"))
        self.assertTrue(any("effort (web): set to max; applies at the next connect" in str(m) for m in self.logs), self.logs)
        self.assertEqual(s._reconnect_surfaces, set()); self.assertFalse(s._reconnect_held_for_work)
        self.assertEqual(self._held(), [])
        s = self._sess()
        s.ended = True
        s.backend.set_effort(self.SID, "low")
        self.assertTrue(any("set to low; applies at the next connect" in str(m) for m in self.logs), self.logs)
        self.assertEqual(s._reconnect_surfaces, set())

    def test_f_the_launched_effort_picked_again_requests_no_reconnect(self):
        s = self._sess(effort="high")
        s._launched_effort = sb.effort_launch_shape("high")
        sb.write_sdk_default(s.backend.state_dir, effort="max")   # another session moved the seed since
        asked = []
        s.request_reconnect = lambda: asked.append(1)
        self.assertTrue(s.backend.set_effort(self.SID, "high"))
        self.assertEqual(asked, [], "the CLI already runs at this effort: nothing to apply")
        reg = sb.read_reg(s.backend.state_dir, self.SID)
        self.assertEqual(reg.get("effort"), "high")
        self.assertFalse(reg.get("effortPending"))
        self.assertEqual(s._effort_pending, "")
        self.assertEqual(self._seed(s).get("effort"), "high",
                         "the seed for NEW sessions follows every pick, the unchanged ones too, as it always did")
        chips = [a for a in s.backend._live.get(self.SID, {}).values() if a.get("command") == "/effort"]
        self.assertEqual(len(chips), 1, "the pick is still acknowledged in the chat")
        self.assertTrue(any("effort (web): set to high; unchanged, no reconnect" in str(m) for m in self.logs), self.logs)

    def test_f2_repicking_the_launched_effort_reverts_a_different_pending_pick(self):
        s = self._sess(effort="high")
        s._launched_effort = sb.effort_launch_shape("high")
        asked = []
        s.request_reconnect = lambda: asked.append(1)
        self.assertTrue(s.backend.set_effort(self.SID, "max"))
        self.assertEqual(asked, [1]); self.assertEqual(s._effort_pending, "max")
        self.assertEqual(self._seed(s).get("effort"), "max")
        self.assertTrue(s.backend.set_effort(self.SID, "high"))
        self.assertEqual(asked, [1], "no second request: the deferred arm, if it fires, relaunches the same shape")
        reg = sb.read_reg(s.backend.state_dir, self.SID)
        self.assertEqual(reg.get("effort"), "high"); self.assertFalse(reg.get("effortPending"))
        self.assertEqual(s._effort_pending, ""); self.assertEqual(s.effort, "high")
        self.assertEqual(self._seed(s).get("effort"), "high", "the latest pick is the seed")
        self.assertTrue(any("set to high; the pending max pick is withdrawn" in str(m) for m in self.logs), self.logs)

    def test_f3_ultracode_is_its_own_launch_shape_and_a_fresh_session_has_none(self):
        # xhigh and ultracode both hand the CLI --effort xhigh; ultracode adds the settings key, so a
        # pick of one over the other is a change. A session that has not connected has no launched
        # shape, so the guard never swallows the pick its first connect must read from the reg.
        self.assertNotEqual(sb.effort_launch_shape("xhigh"), sb.effort_launch_shape("ultracode"))
        self.assertEqual(sb.effort_launch_shape(""), sb.effort_launch_shape(sb.DEFAULT_EFFORT))
        s = self._sess(effort="high")
        self.assertIsNone(s._launched_effort); self.assertIsNone(s._launched_auth)
        asked = []
        s.request_reconnect = lambda: asked.append(1)
        s.backend.set_effort(self.SID, "high")
        self.assertEqual(asked, [1], "unlaunched: the pick persists and requests as before")

    def test_f4_the_launched_billing_picked_again_requests_no_reconnect(self):
        s = self._sess(auth="login")
        s._launched_auth = "login"
        sb.write_sdk_default(s.backend.state_dir, auth="key")
        asked = []
        s.request_reconnect = lambda: asked.append(1)
        self.assertTrue(s.backend.set_auth(self.SID, "login"))
        self.assertEqual(asked, [])
        reg = sb.read_reg(s.backend.state_dir, self.SID)
        self.assertEqual(reg.get("auth"), "login"); self.assertFalse(reg.get("authPending"))
        self.assertEqual(s._auth_pending, "")
        self.assertEqual(self._seed(s).get("auth"), "login", "the seed follows the unchanged pick too")
        chips = [a for a in s.backend._live.get(self.SID, {}).values() if a.get("command") == "/auth"]
        self.assertEqual(len(chips), 1)
        self.assertTrue(any("auth (web): set to login; unchanged, no reconnect" in str(m) for m in self.logs), self.logs)

    def test_f5_repicking_the_launched_billing_reverts_a_pending_switch(self):
        s = self._sess(auth="login")
        s._launched_auth = "login"
        asked = []
        s.request_reconnect = lambda: asked.append(1)
        with mock.patch.object(sb.SdkBackend, "key_available", new_callable=mock.PropertyMock, return_value=True):
            self.assertTrue(s.backend.set_auth(self.SID, "key"))
            self.assertEqual(asked, [1]); self.assertEqual(s._auth_pending, "key")
            self.assertTrue(s.backend.set_auth(self.SID, "login"))
        self.assertEqual(asked, [1], "no second request")
        reg = sb.read_reg(s.backend.state_dir, self.SID)
        self.assertEqual(reg.get("auth"), "login"); self.assertFalse(reg.get("authPending"))
        self.assertEqual(s._auth_pending, ""); self.assertEqual(s.auth, "login")

    def test_f6_the_unchanged_effort_branch_heals_a_drifted_reg_and_a_stale_pending(self):
        # the three states the branch heals, one per case; each was dead in the suite (review round 1)
        for case in ("reg flag only", "pending equal to the pick", "reg value drifted"):
            s = self._sess(effort="high")
            s._launched_effort = sb.effort_launch_shape("high")
            asked = []
            s.request_reconnect = lambda: asked.append(1)
            if case == "reg flag only":                 # the thread died with the flag set; the object is fresh
                s.backend._update_reg(self.SID, effortPending=True)
            elif case == "pending equal to the pick":
                s._effort_pending = "high"
                s.backend._update_reg(self.SID, effortPending=True)
            else:
                s.backend._update_reg(self.SID, effort="max")
                s.effort = "max"
            self.assertTrue(s.backend.set_effort(self.SID, "high"), case)
            reg = sb.read_reg(s.backend.state_dir, self.SID)
            self.assertEqual(reg.get("effort"), "high", case)
            self.assertFalse(reg.get("effortPending"), case)
            self.assertEqual(s._effort_pending, "", case); self.assertEqual(s.effort, "high", case)
            self.assertEqual(asked, [], case)
            self.assertTrue(any("effort (web): set to high; unchanged, no reconnect" in str(m) for m in self.logs), case)

    def test_f7_the_unchanged_billing_branch_heals_a_stale_pending_and_an_unpicked_reg(self):
        s = self._sess(auth="login")
        s._launched_auth = "login"
        s._auth_pending = "login"
        s.backend._update_reg(self.SID, authPending=True)   # after construction: __init__ clears the reg flag
        asked = []
        s.request_reconnect = lambda: asked.append(1)
        self.assertTrue(s.backend.set_auth(self.SID, "login"))
        reg = sb.read_reg(s.backend.state_dir, self.SID)
        self.assertFalse(reg.get("authPending")); self.assertEqual(s._auth_pending, "")
        self.assertEqual(asked, [])
        # an UNPICKED session whose launch landed on the login side takes the pick as its explicit intent
        s = self._sess()
        self.assertEqual(s.auth, "")
        s._launched_auth = "login"
        asked = []
        s.request_reconnect = lambda: asked.append(1)
        self.assertTrue(s.backend.set_auth(self.SID, "login"))
        self.assertEqual(s.auth, "login")
        self.assertEqual(sb.read_reg(s.backend.state_dir, self.SID).get("auth"), "login")
        self.assertEqual(asked, [], "the process already bills that side")

    def test_f8_a_repeat_pick_of_a_value_still_applying_waits_for_the_connect(self):
        # the launched shape is stamped when the connect LANDS, not when _options composes it: until then
        # the pending pick is applying, and picking it again adds nothing. A stamp at _options let a repeat
        # pick in the spawn window hit the unchanged guard and clear the flag, so the connect never wrote
        # the applied record (review round 1)
        s = self._sess(effort="high")
        s._launched_effort = sb.effort_launch_shape("high")
        asked = []
        s.request_reconnect = lambda: asked.append(1)
        self.assertTrue(s.backend.set_effort(self.SID, "max"))
        self.assertEqual(asked, [1])
        # the relaunch is composing: _options records what it hands the CLI; nothing is stamped yet
        s._launching = {"effort": sb.effort_launch_shape("max"), "mode": "default", "auth": "login"}
        self.assertEqual(s._launched_effort, sb.effort_launch_shape("high"), "the running process is still high")
        self.assertTrue(s.backend.set_effort(self.SID, "max"))
        self.assertEqual(asked, [1], "no second request")
        self.assertEqual(s._effort_pending, "max", "still applying")
        self.assertTrue(sb.read_reg(s.backend.state_dir, self.SID).get("effortPending"))
        self.assertTrue(any("effort (web): set to max; already applying, no new request" in str(m) for m in self.logs), self.logs)
        chips = [a for a in s.backend._live.get(self.SID, {}).values() if a.get("command") == "/effort"]
        self.assertGreaterEqual(len(chips), 1, "the pick is acknowledged (same-second picks share one chip uid)")
        s._connect_landed()                    # the connect lands: stamps, then the pending clear
        self.assertEqual(s._launched_effort, sb.effort_launch_shape("max"))
        self.assertEqual(s._launched_mode, "default"); self.assertEqual(s._launched_auth, "login")
        self.assertEqual(s._effort_pending, "")
        self.assertFalse(sb.read_reg(s.backend.state_dir, self.SID).get("effortPending"))
        recs = [json.loads(l) for l in (Path(s.backend.state_dir) / "states" / (self.SID + ".jsonl")).read_text().splitlines()]
        self.assertEqual([r["effortApplied"] for r in recs if "effortApplied" in r], ["max"], "written once, at the landing")
        self.assertTrue(s.backend.set_effort(self.SID, "max"))
        self.assertEqual(asked, [1])
        self.assertTrue(any("set to max; unchanged, no reconnect" in str(m) for m in self.logs))
        # billing, the same way
        s = self._sess(auth="login")
        s._launched_auth = "login"
        asked = []
        s.request_reconnect = lambda: asked.append(1)
        with mock.patch.object(sb.SdkBackend, "key_available", new_callable=mock.PropertyMock, return_value=True):
            self.assertTrue(s.backend.set_auth(self.SID, "key"))
            s._launching = {"effort": sb.effort_launch_shape("high"), "mode": "default", "auth": "key"}
            self.assertTrue(s.backend.set_auth(self.SID, "key"))
        self.assertEqual(asked, [1]); self.assertEqual(s._auth_pending, "key")
        self.assertTrue(sb.read_reg(s.backend.state_dir, self.SID).get("authPending"))
        self.assertTrue(any("auth (web): set to key; already applying, no new request" in str(m) for m in self.logs), self.logs)
        s._connect_landed()
        self.assertEqual(s._launched_auth, "key"); self.assertEqual(s._auth_pending, "")
        self.assertFalse(sb.read_reg(s.backend.state_dir, self.SID).get("authPending"))

    def test_f9_a_pick_made_during_the_spawn_survives_the_landing_of_the_other_shape(self):
        # the landing clears a pending effort only when it IS the shape that launched: a pick made
        # between _options and the connect stays pending for the reconnect its own request armed
        s = self._sess(effort="high")
        s._launched_effort = sb.effort_launch_shape("high")
        s.request_reconnect = lambda: None
        s.backend.set_effort(self.SID, "max")
        s._launching = {"effort": sb.effort_launch_shape("max"), "mode": "default", "auth": "login"}
        s.backend.set_effort(self.SID, "low")           # during the spawn of max
        self.assertEqual(s._effort_pending, "low")
        s._connect_landed()
        self.assertEqual(s._launched_effort, sb.effort_launch_shape("max"))
        self.assertEqual(s._effort_pending, "low", "max landed; low is still applying")
        self.assertTrue(sb.read_reg(s.backend.state_dir, self.SID).get("effortPending"))

    def test_g_every_setter_logs_the_pick_and_its_outcome(self):
        s = self._sess(effort="high", mode="default")
        s.perm_mode = "default"
        s.client = object()                                     # a live switch needs a client (review round 4)
        s.set_mode_live = lambda mode, prev="default": None
        s.backend.set_mode(self.SID, "plan")
        self.assertTrue(any("mode (web): set to plan; applied live" in str(m) for m in self.logs), self.logs)
        s.backend.set_mode(self.SID, "bypassPermissions")
        self.assertTrue(any("mode (web): set to bypassPermissions; reconnecting to apply" in str(m) for m in self.logs), self.logs)
        self.assertTrue(s._reconnect, "quiet and no live work: the bypass pick reconnects at once")
        s._reconnect = False; s._launching = None               # as the loop top and the landing leave them
        s.thread = mock.Mock(is_alive=lambda: True)
        s.backend.send = lambda sid, text, **kw: True
        s._fast_unlocked = True
        s.backend.set_fast(self.SID, "on")
        self.assertTrue(any("fast (web): set to on; applied live" in str(m) for m in self.logs), self.logs)
        s._fast_unlocked = False
        s.backend.set_fast(self.SID, "off")
        self.assertTrue(any("fast (web): set to off; unchanged, no reconnect" in str(m) for m in self.logs), self.logs)
        self._start(s, "a1")
        s.backend.set_fast(self.SID, "on")
        self.assertTrue(any("fast (web): set to on; reconnect held for 1 subagent and 0 background tasks" in str(m)
                            for m in self.logs), self.logs)
        self.assertFalse(s._reconnect); self.assertTrue(s._reconnect_when_idle)
        s.inflight = 1                                          # a turn opens: a pick now defers to its end
        s.backend.set_effort(self.SID, "max")
        self.assertTrue(any("effort (web): set to max; reconnect held for 1 subagent" in str(m) for m in self.logs),
                        "live work outranks the open turn in the outcome: the turn's end alone will not fire it")
        self._stop(s, "a1")
        s.backend.set_effort(self.SID, "low")
        self.assertTrue(any("effort (web): set to low; reconnect deferred to the end of the open turn" in str(m)
                            for m in self.logs), self.logs)

    def test_g2_mode_and_fast_no_op_shapes_request_no_reconnect(self):
        # set_mode and set_fast already skip the reconnect on their no-op shapes; pinned here so the
        # unchanged-value guards on effort and billing have their counterparts on record
        s = self._sess(mode="bypassPermissions")
        s.perm_mode = "bypassPermissions"
        asked = []
        s.request_reconnect = lambda: asked.append("reconnect")
        s.set_mode_live = lambda mode, prev="default": asked.append(("live", mode))
        self.assertTrue(s.backend.set_mode(self.SID, "bypassPermissions"))
        self.assertEqual(asked, [("live", "bypassPermissions")], "already in bypass: the live call, never a reconnect")
        asked.clear()
        s.thread = mock.Mock(is_alive=lambda: True)
        s.backend.send = lambda sid, text, **kw: True
        s._fast_unlocked = True
        self.assertTrue(s.backend.set_fast(self.SID, "on"))
        self.assertEqual(asked, [], "an unlocked connection takes the literal send")
        s._fast_unlocked = False
        self.assertTrue(s.backend.set_fast(self.SID, "off"))
        self.assertEqual(asked, [], "off on a flagless connection is already the state")

    def test_g3_set_env_logs_its_outcome_and_the_fast_refusal_records_its_surface(self):
        s = self._sess()
        self._start(s, "a1")
        self.assertTrue(s.backend.set_env(self.SID, {"X": "1"}))
        self.assertTrue(any("env (web): per-session env set (X); reconnect held for 1 subagent and 0 background tasks"
                            in str(m) for m in self.logs), self.logs)
        # the CLI refusing fast on a flagged connection relaunches flagless: that reconnect is a restore of the
        # fast mode control, not a fast pick (the toast has just said the pick is back off), so it records its
        # own surface, fast-reset, and the arm line names the restore. Recorded as "fast" until review round
        # 3b (2026-09-09), a held relaunch read as a waiting fast pick in the chat and in this line
        s = self._sess()
        s.fast_opt = True
        self._start(s, "a1")
        s._adopt_fast_state({"fast_mode_state": "off", "fast_mode_disabled_reason": "extra_usage_disabled"})
        self.assertFalse(s._reconnect); self.assertTrue(s._reconnect_when_idle)
        self.assertFalse(s.fast_opt, "the refusal clears the ask, so the arm's fast flip has nothing to key on")
        self.assertIn("fast-reset", s._reconnect_surfaces)
        self.assertNotIn("fast", s._reconnect_surfaces)
        self.assertEqual(s._pick_held()["surfaces"], ["fast-reset"])
        self._stop(s, "a1")
        self._settle(s)
        armed = self._armed()
        self.assertEqual(len(armed), 1, self.logs)
        self.assertIn("the held fast mode restore reconnects now", armed[0])
        self.assertNotIn("fast pick", armed[0])
        self.assertEqual(s.fast, "off", "no flip: the relaunch is flagless")
        # a pick held beside the relaunch: the line names the pick and the restore, in that order
        s = self._sess(effort="high")
        s.fast_opt = True
        self._start(s, "a1")
        s._adopt_fast_state({"fast_mode_state": "off", "fast_mode_disabled_reason": "extra_usage_disabled"})
        s.backend.set_effort(self.SID, "max")
        self.assertEqual(s._pick_held()["surfaces"], ["effort", "fast-reset"])
        self._stop(s, "a1")
        self._settle(s)
        self.assertIn("the held effort pick and fast mode restore reconnect now", self._armed()[0], self.logs)

    def test_g4_a_raising_log_callback_never_escapes_the_hook_or_the_settle(self):
        # the arm helper logs through the kernel's bare callback from a hook and from the settle's finally;
        # a callback that raises there used to escape the finally before the failed-step report and to make
        # the hook raise (the SDK turns that into an error control_response)
        def boom(m):
            raise RuntimeError("closed stderr")
        s = self._sess()
        self._start(s, "a1")
        s.backend.set_effort(self.SID, "max")
        s.backend._log_cb = boom
        self.assertEqual(self._stop(s, "a1"), {}, "the hook returns its empty result whatever the callback does")
        s._mark = lambda state: (_ for _ in ()).throw(RuntimeError("state dir gone"))
        out = self._settle(s)
        self.assertTrue(out["ok"], "the settle's finally completed")
        self.assertTrue(out["reconnect"], "and the arm still fired")
        self.assertEqual(s._reconnect_surfaces, set(), "the surfaces cleared before the log ran")
        self.assertTrue(any("'waiting' state write failed" in p["text"] for p in s.backend.problems()),
                        "the failed-step report still reached the ring")
        # the hold-announcing branch, the same way (the settle finds live work and says so)
        s = self._sess()
        self._start(s, "a1")
        s._reconnect_when_idle = True
        s.backend._log_cb = boom
        out = self._settle(s)
        self.assertTrue(out["ok"]); self.assertFalse(out["reconnect"]); self.assertTrue(out["deferred"])
        self.assertTrue(s._reconnect_held_for_work, "the hold was recorded even though the line could not be logged")
        # and a task end's line, from the message stream: the end frame completes and the pick still waits
        s = self._sess()
        s._on_task_event("task_started", {"task_id": "b1", "task_type": "local_bash"})
        s.backend.set_effort(self.SID, "max")
        s.backend._log_cb = boom
        s._on_task_event("task_notification", {"task_id": "b1", "status": "completed"})
        self.assertEqual(s._bg_tasks, {}, "the frame was processed")
        self.assertFalse(s._reconnect); self.assertTrue(s._reconnect_when_idle)
        self.assertTrue(self._settle(s)["reconnect"])

    def test_h_the_drop_notice_names_what_still_reconnects_over_live_work(self):
        # a settings switch no longer reaches _drop_live_work with work alive; the cause says the restart
        # was deliberate, in the person's words: no romp operation name ("key cycle" was romp's)
        self.assertNotIn("settings switch", sb.SdkSession._RECONNECT_CAUSE)
        self.assertNotIn("key cycle", sb.SdkSession._RECONNECT_CAUSE)
        self.assertEqual(sb.SdkSession._RECONNECT_CAUSE, "a deliberate restart")
        self.assertNotIn("crash", sb.SdkSession._RECONNECT_CAUSE, "LiveSubagentsRetire.test_f: a reconnect notice never says crash")

    def test_i_the_snapshot_reports_the_hold_and_the_launched_mode(self):
        # what the status readers see while a pick waits: which picks, on how much work; the chat renders
        # a waiting line off it instead of the "Reloading session" animation, which claimed a reload in
        # progress for the whole hold. A bypass pick held reports the mode the process still RUNS
        s = self._sess(mode="default")
        s.perm_mode = "default"
        s._launched_mode = "default"
        self.assertIsNone(s.snapshot()["pickHeld"])
        self._start(s, "a1")
        s.backend.set_effort(self.SID, "max")
        snap = s.snapshot()
        self.assertEqual(snap["pickHeld"], {"surfaces": ["effort"], "subagents": 1, "tasks": 0, "inflight": False})
        self.assertTrue(snap["effortPending"], "the badge dots stay: the pick IS pending")
        s.backend.set_mode(self.SID, "bypassPermissions")
        snap = s.snapshot()
        self.assertEqual(snap["pickHeld"]["surfaces"], ["effort", "mode"])
        self.assertEqual(snap["mode"], "default", "the process runs the launched mode until the held reconnect")
        self.assertEqual(s.perm_mode, "bypassPermissions", "the declared intent stands in memory (the consult guard reads it)")
        s._on_task_event("task_started", {"task_id": "b1", "task_type": "local_bash"})
        self.assertEqual(s.snapshot()["pickHeld"]["tasks"], 1, "counts are live")
        s._on_task_event("task_notification", {"task_id": "b1", "status": "completed"})
        self._stop(s, "a1")
        snap = s.snapshot()
        self.assertEqual(snap["pickHeld"], {"surfaces": ["effort", "mode"], "subagents": 0, "tasks": 0, "inflight": False},
                         "still held through the agent's delivery turn: no flap to 'reloading' before the settle")
        self.assertTrue(self._settle(s)["reconnect"])
        snap = s.snapshot()
        self.assertIsNone(snap["pickHeld"], "the arm clears it")
        self.assertTrue(snap["effortPending"], "now the reload is really in progress")
        self.assertEqual(snap["mode"], "bypassPermissions")

    def test_i2_a_consult_during_a_held_bypass_pick_allows_without_a_false_problem(self):
        # the process still runs the launched mode, so its permission consults are expected, not the
        # contract breach the T139 guard rings for a CONFIRMED bypass; romp still answers with the declared
        # intent (allow). The SDK's result classes are stubbed at call time, as tests/test_mode_truth.py does
        import sys as _sys, types as _types
        fake = _types.ModuleType("claude_agent_sdk")
        class _PRA:
            def __init__(self, behavior="allow", **kw): self.behavior = behavior
        class _PRD:
            def __init__(self, behavior="deny", **kw): self.behavior = behavior
        fake.PermissionResultAllow, fake.PermissionResultDeny = _PRA, _PRD
        before = _sys.modules.get("claude_agent_sdk")
        if before is None:
            _sys.modules["claude_agent_sdk"] = fake
        try:
            s = self._sess(mode="default")
            s.perm_mode = "default"
            s._launched_mode = "default"
            self._start(s, "a1")
            s.backend.set_mode(self.SID, "bypassPermissions")
            self.assertTrue(s._reconnect_when_idle and not s._reconnect)
            res = asyncio.run(s._can_use_tool("Bash", {"command": "ls"}, object()))
            self.assertEqual(res.behavior, "allow")
            self.assertEqual([p["text"] for p in s.backend.problems() if "contract" in p["text"]], [],
                             "an expected consult rings no problem")
            self.assertTrue(any("consult" in str(m) and "held" in str(m) for m in self.logs), self.logs)
            # a CONFIRMED bypass consult still rings (tests/test_mode_truth.py pins the guard; one line here)
            s2 = self._sess(mode="bypassPermissions")
            s2.perm_mode = "bypassPermissions"; s2._launched_mode = "bypassPermissions"
            asyncio.run(s2._can_use_tool("Bash", {"command": "ls"}, object()))
            self.assertTrue(any("contract" in p["text"] for p in s2.backend.problems()))
        finally:
            if before is None:
                _sys.modules.pop("claude_agent_sdk", None)

    def test_b7_a_rewind_at_the_settle_over_a_hold_has_its_own_line(self):
        # a pending rewind reaching the settle over a hold arms over the live work (the rewind's exemption,
        # request_reconnect), so "live work finished" would be false with the subagent still registered;
        # the line names the rewind and says the held pick rides it (review round 2)
        s = self._sess()
        self._start(s, "a1")
        s.backend.set_effort(self.SID, "max")
        self.assertTrue(s._reconnect_when_idle and s._reconnect_held_for_work)
        s._rewind_to = "22222222-3333-4444-5555-666666666666"
        s._rewind_armed = False
        out = self._settle(s)
        self.assertTrue(out["reconnect"], "the rewind's queue cannot wait: it arms over the work")
        self.assertFalse(out["deferred"])
        self.assertEqual(len(s._subagents), 1, "the subagent is still registered at the arm (the loop top drops it)")
        self.assertEqual(self._armed(), [], "no false 'live work finished' line")
        rew = [str(m) for m in self.logs if "the rewind reconnects over" in str(m)]
        self.assertEqual(len(rew), 1, self.logs)
        self.assertIn("reconnect (web): the rewind reconnects over 1 subagent and 0 background tasks; "
                      "the held effort pick rides it", rew[0])
        self.assertFalse(s._reconnect_held_for_work); self.assertIsNone(s.snapshot()["pickHeld"])
        # a rewind at a settle whose turn emptied the sets: the ordinary line, since it is true
        s = self._sess()
        self._start(s, "a1")
        s.backend.set_effort(self.SID, "max")
        self._stop(s, "a1")
        s._rewind_to = "22222222-3333-4444-5555-666666666666"; s._rewind_armed = False
        self.assertTrue(self._settle(s)["reconnect"])
        self.assertEqual(len(self._armed()), 1)
        self.assertEqual([m for m in self.logs if "the rewind reconnects over" in str(m)], [])

    def test_b8_the_hold_is_visible_before_the_loop_runs_the_request(self):
        # the setter marks the hold on the kernel thread; the loop thread sets _reconnect_when_idle only
        # when it runs the queued request. A snapshot between the two read pickHeld None with effortPending
        # True, and the chat drew the reloading animation for one push (review round 2)
        s = self._sess()
        queued = []
        s.loop = type("_Queue", (), {"call_soon_threadsafe": lambda self_, cb, *a: queued.append((cb, a))})()
        self._start(s, "a1")
        s.backend.set_effort(self.SID, "max")
        self.assertFalse(s._reconnect_when_idle, "the request is queued, not run")
        self.assertEqual(s.snapshot()["pickHeld"], {"surfaces": ["effort"], "subagents": 1, "tasks": 0, "inflight": False})
        for cb, a in queued:
            cb(*a)
        self.assertTrue(s._reconnect_when_idle)
        self.assertEqual(s.snapshot()["pickHeld"], {"surfaces": ["effort"], "subagents": 1, "tasks": 0, "inflight": False})
        self.assertEqual(len(self._held()), 1, "the loop's own held line is not repeated: the setter said it")
        s.ended = True
        self.assertIsNone(s.snapshot()["pickHeld"], "a session shutting down holds nothing")

    def test_f10_a_pick_in_the_spawn_window_compares_against_the_shape_being_launched(self):
        # the connect in progress runs the PENDING shape (_launching), not the stamp of the process it
        # replaces. A revert made in that window read as unchanged against the old stamp ("reverted the
        # pending max; no reconnect") while the new process came up on max: the CLI ran max, the reg and
        # the badge said high, nothing was pending (review round 2). Both orders, effort then billing.
        s = self._sess(effort="high")
        s._launched_effort = sb.effort_launch_shape("high")
        self.assertTrue(s.backend.set_effort(self.SID, "max"))
        self.assertTrue(s._reconnect, "quiet: reconnects at once")
        s._reset_reconnect_state()                                          # the loop top
        s._launching = {"effort": sb.effort_launch_shape("max"), "mode": "default", "auth": "login"}   # _options
        self.assertTrue(s.backend.set_effort(self.SID, "high"))             # the revert, during the spawn of max
        self.assertEqual(s._effort_pending, "high", "recorded as pending: the process coming up runs max")
        self.assertTrue(s._reconnect, "and a reconnect is requested for after the launch lands")
        self.assertTrue(sb.read_reg(s.backend.state_dir, self.SID).get("effortPending"))
        self.assertFalse(any("pick is withdrawn" in str(m) for m in self.logs), self.logs)
        self.assertTrue(any("effort (web): set to high; reconnecting to apply" in str(m) for m in self.logs), self.logs)
        s._connect_landed()                                                 # max lands
        self.assertEqual(s._launched_effort, sb.effort_launch_shape("max"))
        self.assertEqual(s._effort_pending, "high", "high survives the landing of max")

        def recs():
            p = Path(s.backend.state_dir) / "states" / (self.SID + ".jsonl")
            return [json.loads(l)["effortApplied"] for l in p.read_text().splitlines() if "effortApplied" in l] if p.exists() else []
        s._reset_reconnect_state()
        s._launching = {"effort": sb.effort_launch_shape("high"), "mode": "default", "auth": "login"}
        s._connect_landed()                                                 # high lands
        self.assertEqual(s._effort_pending, "")
        self.assertFalse(sb.read_reg(s.backend.state_dir, self.SID).get("effortPending"))
        self.assertEqual(recs(), ["high"], "the applied record: exactly one, for the pick that landed")
        self.assertEqual(s.effort, "high")
        # the other order: the value being launched, picked during its own spawn, is a no-op
        s = self._sess(effort="high")
        s._launched_effort = sb.effort_launch_shape("high")
        s.backend.set_effort(self.SID, "max")
        s._reset_reconnect_state()
        s._launching = {"effort": sb.effort_launch_shape("max"), "mode": "default", "auth": "login"}
        asked = []
        s.request_reconnect = lambda: asked.append(1)
        self.assertTrue(s.backend.set_effort(self.SID, "max"))
        self.assertEqual(asked, [], "already applying: no request")
        self.assertTrue(any("set to max; already applying, no new request" in str(m) for m in self.logs))
        # ...even when nothing was flagged pending (a connect launched from the reg): the flag is set so
        # the landing writes the applied record
        s._effort_pending = ""
        s.backend._update_reg(self.SID, effortPending=False)
        self.assertTrue(s.backend.set_effort(self.SID, "max"))
        self.assertEqual(asked, [])
        self.assertEqual(s._effort_pending, "max")
        self.assertTrue(sb.read_reg(s.backend.state_dir, self.SID).get("effortPending"))
        s._connect_landed()
        self.assertEqual(s._effort_pending, "")
        # billing, both orders
        s = self._sess(auth="key")
        s._launched_auth = "key"
        with mock.patch.object(sb.SdkBackend, "key_available", new_callable=mock.PropertyMock, return_value=True):
            self.assertTrue(s.backend.set_auth(self.SID, "login"))
            self.assertTrue(s._reconnect)
            s._reset_reconnect_state()
            s._launching = {"effort": sb.effort_launch_shape("high"), "mode": "default", "auth": "login"}
            self.assertTrue(s.backend.set_auth(self.SID, "key"))            # the revert, during the spawn of login
            self.assertEqual(s._auth_pending, "key"); self.assertTrue(s._reconnect)
            self.assertFalse(any("pick is withdrawn" in str(m) for m in self.logs), self.logs)
            s._connect_landed()
            self.assertEqual(s._launched_auth, "login")
            self.assertEqual(s._auth_pending, "key", "key survives the landing of login")
            s._reset_reconnect_state()
            s._launching = {"effort": sb.effort_launch_shape("high"), "mode": "default", "auth": "key"}
            s._connect_landed()
            self.assertEqual(s._auth_pending, ""); self.assertEqual(s._launched_auth, "key")
            s = self._sess(auth="key")
            s._launched_auth = "key"
            s.backend.set_auth(self.SID, "login")
            s._reset_reconnect_state()
            s._launching = {"effort": sb.effort_launch_shape("high"), "mode": "default", "auth": "login"}
            asked = []
            s.request_reconnect = lambda: asked.append(1)
            self.assertTrue(s.backend.set_auth(self.SID, "login"))
            self.assertEqual(asked, [])
            self.assertTrue(any("auth (web): set to login; already applying, no new request" in str(m) for m in self.logs), self.logs)

    def test_j_a_live_mode_switch_stamps_the_running_mode_and_a_held_bypass_reports_it(self):
        # _launched_mode followed only the connect; a live switch the CLI confirmed left it stale, so a
        # bypass pick held after a live plan pick reported the launch mode for the whole hold (review round 2)
        class _OK:
            async def set_permission_mode(self_, m): pass
        class _No:
            async def set_permission_mode(self_, m): raise RuntimeError("Cannot set permission mode")
        s = self._sess(mode="default")
        s.perm_mode = "default"; s._launched_mode = "default"
        s.client = _OK()
        asyncio.run(s._do_set_mode("plan", prev="default"))
        self.assertEqual(s._launched_mode, "plan", "the CLI confirmed it: the process runs plan")
        s.perm_mode = "plan"
        self._start(s, "a1")
        s.backend.set_mode(self.SID, "bypassPermissions")
        snap = s.snapshot()
        self.assertEqual(snap["pickHeld"]["surfaces"], ["mode"])
        self.assertEqual(snap["mode"], "plan", "the held bypass pick reports the mode the process runs")
        # a refused live switch leaves the stamp (and every layer) where it was
        s2 = self._sess(mode="default")
        s2.perm_mode = "default"; s2._launched_mode = "default"; s2.client = _No()
        asyncio.run(s2._do_set_mode("plan", prev="default"))
        self.assertEqual(s2._launched_mode, "default"); self.assertEqual(s2.perm_mode, "default")

    def test_j2_a_repeat_bypass_pick_during_the_hold_is_a_no_op_never_the_refused_live_call(self):
        # prev read the declared (unconfirmed) bypass, so the re-click went LIVE and the CLI refused it
        # with the red "did NOT apply" problem while the hold stood (review round 2)
        s = self._sess(mode="default")
        s.perm_mode = "default"; s._launched_mode = "default"
        live = []
        s.set_mode_live = lambda mode, prev="default": live.append((mode, prev))
        self._start(s, "a1")
        s.backend.set_mode(self.SID, "bypassPermissions")
        self.assertEqual(len(self._held()), 1)
        s.backend.set_mode(self.SID, "bypassPermissions")
        self.assertEqual(live, [], "no live call: the CLI refuses a live switch into bypass")
        self.assertEqual(len(self._held()), 1, "no second held line: nothing new was asked")
        self.assertTrue(any("mode (web): set to bypassPermissions; already applying, no new request" in str(m)
                            for m in self.logs), self.logs)
        self.assertEqual(s.snapshot()["pickHeld"]["surfaces"], ["mode"])
        # the spawn window too: the flags are reset, _launching carries the mode
        s._reset_reconnect_state()
        s._launching = {"effort": sb.effort_launch_shape("high"), "mode": "bypassPermissions", "auth": "login"}
        s.backend.set_mode(self.SID, "bypassPermissions")
        self.assertEqual(live, [])
        self.assertFalse(s._reconnect_when_idle, "no new request during the spawn either")
        # a FIRST bypass pick during an effort hold still asks (the guard keys on the mode surface, not the hold)
        s = self._sess(mode="default")
        s.perm_mode = "default"; s._launched_mode = "default"
        s.set_mode_live = lambda mode, prev="default": live.append((mode, prev))
        self._start(s, "a1")
        s.backend.set_effort(self.SID, "max")
        s.backend.set_mode(self.SID, "bypassPermissions")
        self.assertEqual(s.snapshot()["pickHeld"]["surfaces"], ["effort", "mode"])
        self.assertEqual(len(self._held()), 2)
        self.assertEqual(live, [])

    def test_j3_a_live_pick_during_a_held_bypass_withdraws_the_bypass_pick(self):
        # the newer intent wins: a live plan pick retires the held bypass pick, with prev = the mode the
        # process runs (never the unconfirmed bypass), and the reconnect the bypass asked for is cancelled
        # when nothing else asked, so the settle relaunches nothing (review round 2)
        s = self._sess(mode="default")
        s.perm_mode = "default"; s._launched_mode = "default"
        s.client = object()                                     # a live switch needs a client (review round 4)
        live = []
        s.set_mode_live = lambda mode, prev="default": live.append((mode, prev))
        self._start(s, "a1")
        s.backend.set_mode(self.SID, "bypassPermissions")
        self.assertTrue(s._reconnect_when_idle)
        s.backend.set_mode(self.SID, "plan")
        self.assertEqual(live, [("plan", "default")], "prev is the confirmed mode, never the pending bypass")
        self.assertTrue(any("mode (web): set to plan; applied live; the held bypass pick is withdrawn" in str(m)
                            for m in self.logs), self.logs)
        self.assertFalse(s._reconnect_when_idle, "the bypass pick was the only one pending: no reconnect")
        self.assertFalse(s._reconnect_held_for_work)
        self.assertIsNone(s.snapshot()["pickHeld"])
        self.assertEqual(s.snapshot()["mode"], "plan")
        self.assertTrue(any("the withdrawn mode pick was the only one pending; no reconnect" in str(m) for m in self.logs))
        self._stop(s, "a1")
        out = self._settle(s)
        self.assertFalse(out["reconnect"], "nothing relaunches a mode the process already runs")
        self.assertEqual(self._armed(), [])
        # with an effort pick also held, the hold stands for that pick alone
        s = self._sess(mode="default")
        s.perm_mode = "default"; s._launched_mode = "default"
        s.set_mode_live = lambda mode, prev="default": None
        self._start(s, "a1")
        s.backend.set_effort(self.SID, "max")
        s.backend.set_mode(self.SID, "bypassPermissions")
        s.backend.set_mode(self.SID, "acceptEdits")
        self.assertTrue(s._reconnect_when_idle)
        self.assertEqual(s.snapshot()["pickHeld"], {"surfaces": ["effort"], "subagents": 1, "tasks": 0, "inflight": False})
        self.assertEqual(s.snapshot()["mode"], "acceptEdits")
        # the deferred case (a turn open, no live work) withdraws the same way
        s = self._sess(mode="default")
        s.perm_mode = "default"; s._launched_mode = "default"
        s.set_mode_live = lambda mode, prev="default": None
        s.inflight = 1
        s.backend.set_mode(self.SID, "bypassPermissions")
        self.assertTrue(s._reconnect_when_idle)
        s.backend.set_mode(self.SID, "plan")
        self.assertFalse(s._reconnect_when_idle)
        # a pending rewind keeps its arm: the rewind's request records no surface
        s = self._sess(mode="default")
        s.perm_mode = "default"; s._launched_mode = "default"
        s.set_mode_live = lambda mode, prev="default": None
        self._start(s, "a1")
        s.backend.set_mode(self.SID, "bypassPermissions")
        s._rewind_to = "22222222-3333-4444-5555-666666666666"; s._rewind_armed = False
        s.backend.set_mode(self.SID, "plan")
        self.assertTrue(s._reconnect_when_idle, "the rewind depends on the deferred arm")
        # bypass, plan, bypass again: the second bypass pick asks anew and reports plan while held
        class _OK:
            async def set_permission_mode(self_, m): pass
        s = self._sess(mode="default")
        s.perm_mode = "default"; s._launched_mode = "default"; s.client = _OK()
        s.set_mode_live = lambda mode, prev="default": asyncio.run(s._do_set_mode(mode, prev))
        self._start(s, "a1")
        s.backend.set_mode(self.SID, "bypassPermissions")
        s.backend.set_mode(self.SID, "plan")
        self.assertEqual(s._launched_mode, "plan")
        s.backend.set_mode(self.SID, "bypassPermissions")
        self.assertTrue(s._reconnect_when_idle)
        self.assertEqual(s.snapshot()["mode"], "plan")
        self.assertEqual(s.snapshot()["pickHeld"]["surfaces"], ["mode"])

    def test_j4_a_bypass_re_pick_after_a_live_switch_out_of_bypass_reconnects(self):
        # _launching was set by _options and never cleared, so after the landing the already-applying guard
        # still read it as a connect in progress: a process launched in bypass, live-switched to default and
        # re-picked into bypass logged "already applying, no new request" and never reconnected, and with
        # both reconnect flags False every consult rang the red contract problem (review round 3). The spawn
        # window ends at _connect_landed, which clears _launching; the guard still refuses a repeat pick
        # DURING the spawn, before the landing
        class _OK:
            async def set_permission_mode(self_, m): pass
        s = self._sess(mode="bypassPermissions")
        s.perm_mode = "bypassPermissions"
        s.client = _OK()
        s.set_mode_live = lambda mode, prev="default": asyncio.run(s._do_set_mode(mode, prev))
        s._launching = {"effort": sb.effort_launch_shape("high"), "mode": "bypassPermissions", "auth": "login"}
        s._connect_landed()
        self.assertEqual(s._launched_mode, "bypassPermissions")
        self.assertIsNone(s._launching, "the landing ends the spawn window")
        asked = []
        s.request_reconnect = lambda: asked.append(1)
        self.assertTrue(s.backend.set_mode(self.SID, "default"))
        self.assertEqual(s._launched_mode, "default", "the CLI confirmed the live switch: the process runs default")
        self.assertEqual(asked, [], "a live switch out of bypass needs no reconnect")
        self.assertTrue(s.backend.set_mode(self.SID, "bypassPermissions"))
        self.assertEqual(asked, [1], "the re-pick into bypass reconnects: nothing is applying")
        self.assertTrue(any("mode (web): set to bypassPermissions; reconnecting to apply" in str(m) for m in self.logs), self.logs)
        self.assertFalse(any("already applying" in str(m) for m in self.logs), self.logs)
        # during the spawn (before the landing) the guard still refuses the repeat pick
        s = self._sess(mode="default")
        s.perm_mode = "default"; s._launched_mode = "default"
        live = []
        s.set_mode_live = lambda mode, prev="default": live.append((mode, prev))
        s._reset_reconnect_state()
        s._launching = {"effort": sb.effort_launch_shape("high"), "mode": "bypassPermissions", "auth": "login"}
        asked = []
        s.request_reconnect = lambda: asked.append(1)
        s.perm_mode = "bypassPermissions"; s.mode = "bypassPermissions"   # the declared pick, riding the connect
        self.assertTrue(s.backend.set_mode(self.SID, "bypassPermissions"))
        self.assertEqual(asked, [], "the connect in progress launches bypass: already applying")
        self.assertEqual(live, [])
        self.assertTrue(any("already applying, no new request" in str(m) for m in self.logs), self.logs)

    def _withdrawn(self):
        return [str(m) for m in self.logs if "the withdrawn" in str(m)]

    def test_l_reverting_a_held_effort_pick_withdraws_it_and_the_settle_reconnects_nothing(self):
        # the launched value picked again while a different pick is held cleared the pending flag and
        # logged "no reconnect", but left the surface in the pending set and the hold armed: pickHeld kept
        # naming the withdrawn pick and the settle that found no work relaunched the identical shape
        # ("live work finished; the held effort pick reconnects now"). One withdraw routine for every
        # surface now (review round 3); the request runs through the loop double, so the surfaces populate
        s = self._sess(effort="high")
        s._launched_effort = sb.effort_launch_shape("high")
        self._start(s, "a1")
        self.assertTrue(s.backend.set_effort(self.SID, "max"))
        self.assertTrue(s._reconnect_when_idle and s._reconnect_held_for_work)
        self.assertEqual(s.snapshot()["pickHeld"]["surfaces"], ["effort"])
        self.assertTrue(s.backend.set_effort(self.SID, "high"))
        self.assertIsNone(s._pick_held(), "the withdrawn pick is no longer held")
        self.assertIsNone(s.snapshot()["pickHeld"])
        self.assertFalse(s._reconnect_when_idle, "the only pending pick was withdrawn: no reconnect waits")
        self.assertFalse(s._reconnect); self.assertFalse(s._reconnect_held_for_work)
        self.assertEqual(s._reconnect_surfaces, set())
        self.assertEqual(s._effort_pending, ""); self.assertEqual(s.effort, "high")
        reg = sb.read_reg(s.backend.state_dir, self.SID)
        self.assertEqual(reg.get("effort"), "high"); self.assertFalse(reg.get("effortPending"))
        self.assertTrue(any("effort (web): set to high; the pending max pick is withdrawn" in str(m) for m in self.logs), self.logs)
        self.assertTrue(any("the withdrawn effort pick was the only one pending; no reconnect" in str(m) for m in self.logs), self.logs)
        self.assertFalse(any("unchanged, no reconnect" in str(m) for m in self.logs), "never 'unchanged' while a hold stood")
        self._stop(s, "a1")
        out = self._settle(s)
        self.assertFalse(out["reconnect"], "nothing relaunches the shape the process already runs")
        self.assertFalse(out["deferred"])
        self.assertEqual(self._armed(), [])

    def test_l2_reverting_a_held_billing_pick_withdraws_it_and_keeps_the_report(self):
        s = self._sess(auth="login")
        s._launched_auth = "login"
        s.auth_live = "login"
        self._start(s, "a1")
        with mock.patch.object(sb.SdkBackend, "key_available", new_callable=mock.PropertyMock, return_value=True):
            self.assertTrue(s.backend.set_auth(self.SID, "key"))
            self.assertTrue(s._reconnect_when_idle and s._reconnect_held_for_work)
            self.assertEqual(s.snapshot()["pickHeld"]["surfaces"], ["auth"])
            self.assertEqual(s.auth_live, "login", "held: the report still describes the running process")
            self.assertTrue(s.backend.set_auth(self.SID, "login"))
        self.assertIsNone(s._pick_held()); self.assertIsNone(s.snapshot()["pickHeld"])
        self.assertFalse(s._reconnect_when_idle); self.assertFalse(s._reconnect_held_for_work)
        self.assertEqual(s._auth_pending, ""); self.assertEqual(s.auth, "login")
        self.assertEqual(s.auth_live, "login", "the report is kept through the revert: the process bills the login")
        self.assertEqual(s.snapshot()["authLive"], "login"); self.assertFalse(s.snapshot()["authPending"])
        reg = sb.read_reg(s.backend.state_dir, self.SID)
        self.assertEqual(reg.get("auth"), "login"); self.assertFalse(reg.get("authPending"))
        self.assertTrue(any("auth (web): set to login; the pending key pick is withdrawn" in str(m) for m in self.logs), self.logs)
        self.assertTrue(any("the withdrawn auth pick was the only one pending; no reconnect" in str(m) for m in self.logs), self.logs)
        self._stop(s, "a1")
        out = self._settle(s)
        self.assertFalse(out["reconnect"]); self.assertEqual(self._armed(), [])

    def test_l3_fast_off_over_a_pending_on_pick_withdraws_it_held_and_deferred(self):
        # held for live work: the on pick waits, off returns to the state the process runs
        s = self._sess()
        s.thread = mock.Mock(is_alive=lambda: True)
        s.fast = "off"; s._fast_unlocked = False
        self._start(s, "a1")
        self.assertTrue(s.backend.set_fast(self.SID, "on"))
        self.assertTrue(s._reconnect_when_idle and s._reconnect_held_for_work)
        self.assertEqual(s.snapshot()["pickHeld"]["surfaces"], ["fast"])
        self.assertEqual(s.snapshot()["fast"], "off", "held: the badge shows the running state")
        self.assertTrue(s.backend.set_fast(self.SID, "off"))
        self.assertFalse(s.fast_opt, "the ask is off for the next connect")
        self.assertIsNone(s._pick_held()); self.assertIsNone(s.snapshot()["pickHeld"])
        self.assertFalse(s._reconnect_when_idle); self.assertFalse(s._reconnect_held_for_work)
        self.assertEqual(s.snapshot()["fast"], "off")
        self.assertFalse(sb.read_reg(s.backend.state_dir, self.SID).get("fast"))
        self.assertTrue(any("fast (web): set to off; the pending on pick is withdrawn" in str(m) for m in self.logs), self.logs)
        self.assertTrue(any("the withdrawn fast pick was the only one pending; no reconnect" in str(m) for m in self.logs), self.logs)
        self._stop(s, "a1")
        out = self._settle(s)
        self.assertFalse(out["reconnect"]); self.assertEqual(self._armed(), [])
        # deferred (a turn open, no live work): the same withdraw, and the badge reads off, never the
        # picked value (a deferred on pick used to flip the badge on at pick time and the cancelled
        # reconnect's init no longer reset it)
        s = self._sess()
        s.thread = mock.Mock(is_alive=lambda: True)
        s.fast = "off"; s._fast_unlocked = False
        s.inflight = 1
        self.assertTrue(s.backend.set_fast(self.SID, "on"))
        self.assertTrue(s._reconnect_when_idle and not s._reconnect)
        self.assertTrue(any("fast (web): set to on; reconnect deferred to the end of the open turn" in str(m) for m in self.logs), self.logs)
        self.assertTrue(s.backend.set_fast(self.SID, "off"))
        self.assertFalse(s._reconnect_when_idle)
        self.assertEqual(s.fast, "off"); self.assertEqual(s.snapshot()["fast"], "off")
        out = self._settle(s)
        self.assertFalse(out["reconnect"]); self.assertFalse(out["deferred"])
        # an UNLOCKED connection takes off as a live send and cancels nothing: the refusal relaunch pends
        # its own surface, fast-reset, on a flagged connection (review round 3b, 2026-09-09; "fast" before),
        # and a live off must leave that reconnect standing
        s = self._sess()
        s.thread = mock.Mock(is_alive=lambda: True)
        s.fast = "off"; s._fast_unlocked = True
        s.fast_opt = True
        self._start(s, "a1")
        s._adopt_fast_state({"fast_mode_state": "off", "fast_mode_disabled_reason": "extra_usage_disabled"})
        self.assertTrue(s._reconnect_when_idle); self.assertIn("fast-reset", s._reconnect_surfaces)
        self.assertTrue(s.backend.set_fast(self.SID, "off"))
        self.assertTrue(s._reconnect_when_idle, "the flagless relaunch still waits")
        self.assertIn("fast-reset", s._reconnect_surfaces)
        self.assertEqual(s.pending(), ["/fast off"], "the unlocked branch is untouched: a live send")

    def test_l4_a_withdrawn_pick_leaves_another_held_pick_and_its_reconnect_standing(self):
        s = self._sess(effort="high", auth="login")
        s._launched_effort = sb.effort_launch_shape("high"); s._launched_auth = "login"
        self._start(s, "a1")
        with mock.patch.object(sb.SdkBackend, "key_available", new_callable=mock.PropertyMock, return_value=True):
            self.assertTrue(s.backend.set_effort(self.SID, "max"))
            self.assertTrue(s.backend.set_auth(self.SID, "key"))
            self.assertEqual(s.snapshot()["pickHeld"]["surfaces"], ["effort", "auth"])
            self.assertTrue(s.backend.set_effort(self.SID, "high"))
        self.assertEqual(s.snapshot()["pickHeld"]["surfaces"], ["auth"], "the billing pick still waits")
        self.assertTrue(s._reconnect_when_idle and s._reconnect_held_for_work, "the hold stands for it")
        self.assertEqual(s._auth_pending, "key")
        self.assertTrue(any("the withdrawn effort pick leaves the pending auth pick pending; the reconnect stands"
                            in str(m) for m in self.logs), self.logs)
        self.assertEqual([m for m in self._withdrawn() if "only one pending" in m], [])
        self._stop(s, "a1")
        out = self._settle(s)
        self.assertTrue(out["reconnect"], "the settle still reconnects for the billing pick")
        armed = self._armed()
        self.assertEqual(len(armed), 1, self.logs)
        self.assertIn("the held auth pick reconnects now", armed[0])

    def test_l5_a_revert_during_a_pending_rewind_ends_the_hold_and_leaves_the_rewinds_arm(self):
        # the withdraw's early return on a pending unarmed rewind ran after the surface discard and before the
        # flag clears, so the hold flag stood with an empty surface set: the chat said the pending change was
        # waiting on 1 subagent for nothing, and the settle's arm said the held reconnect rode the rewind. The
        # hold ends whenever no surface remains, rewind or not; the rewind keeps its deferred arm (review round
        # 4). The reachable gesture is a message deleted on a busy session (_arm_rollback_busy: the rewind
        # pending and unarmed, a turn in flight); its wait flag is left off here, since with no transcript on
        # disk the settle's wait completion would restore the rewind before the arm it is about to test
        s = self._sess(effort="high")
        s._launched_effort = sb.effort_launch_shape("high")
        self._start(s, "a1")
        s.inflight = 1
        self.assertTrue(s.backend.set_effort(self.SID, "max"))
        self.assertTrue(s._reconnect_when_idle and s._reconnect_held_for_work)
        s._rewind_to = "22222222-3333-4444-5555-666666666666"; s._rewind_armed = False
        self.assertTrue(s.backend.set_effort(self.SID, "high"))          # the revert, during the pending rewind
        self.assertIsNone(s._pick_held()); self.assertFalse(s._reconnect_held_for_work)
        self.assertIsNone(s.snapshot()["pickHeld"], "no hold naming no pick")
        self.assertTrue(s._reconnect_when_idle, "the rewind's deferred arm stands"); self.assertFalse(s._reconnect)
        self.assertTrue(any("the withdrawn effort pick was the only one pending; the rewind's reconnect stands" in str(m)
                            for m in self.logs), self.logs)
        self.assertEqual([m for m in self._withdrawn() if "no reconnect" in m], [])
        out = self._settle(s)                                            # the turn ends: the rewind arms over the work
        self.assertTrue(out["reconnect"]); self.assertFalse(out["deferred"])
        self.assertEqual([m for m in self.logs if "rides it" in str(m)], [], "nothing is held, so nothing rides")
        self.assertEqual(self._armed(), [], "no false 'live work finished' line")
        rew = [str(m) for m in self.logs if "the rewind reconnects over" in str(m)]
        self.assertEqual(len(rew), 1, self.logs)
        self.assertTrue(rew[0].endswith("the rewind reconnects over 1 subagent and 0 background tasks"), rew)

    def test_m_a_pick_made_mid_turn_flips_nothing_until_the_arm(self):
        # a pick made during a turn with no live work flipped at pick time (fast to on, auth_live blanked);
        # when that turn spawned work and settled, the hold began with the flipped value in place: the fast
        # badge read on under the held mark and the delivery turn's init flipped it back with the mark
        # standing; the billing row lost the report. The flips are the ARM's now (review round 3): nothing
        # moves until the settle that finds no work arms the reconnect
        s = self._sess(auth="login")
        s._launched_auth = "login"; s.auth_live = "login"
        s.thread = mock.Mock(is_alive=lambda: True)
        s.fast = "off"; s._fast_unlocked = False
        s.inflight = 1                                   # a turn open, no live work
        with mock.patch.object(sb.SdkBackend, "key_available", new_callable=mock.PropertyMock, return_value=True):
            self.assertTrue(s.backend.set_auth(self.SID, "key"))
            self.assertTrue(s.backend.set_fast(self.SID, "on"))
        self.assertTrue(s._reconnect_when_idle and not s._reconnect and not s._reconnect_held_for_work)
        self.assertTrue(any("auth (web): set to key; reconnect deferred to the end of the open turn" in str(m) for m in self.logs), self.logs)
        self.assertEqual(s.fast, "off", "deferred: no flip at the pick"); self.assertTrue(s.fast_opt)
        self.assertEqual(s.auth_live, "login", "deferred: the report stands")
        self._start(s, "a1")                             # the turn spawns work
        out = self._settle(s)                            # its settle finds the work: the hold begins here
        self.assertFalse(out["reconnect"]); self.assertTrue(out["deferred"])
        self.assertTrue(s._reconnect_held_for_work)
        snap = s.snapshot()
        self.assertEqual(snap["pickHeld"]["surfaces"], ["fast", "auth"])
        self.assertEqual(snap["fast"], "off", "the badge shows what the session runs under the held mark")
        self.assertEqual(snap["authLive"], "login", "the billing row names the report as what bills until the work finishes")
        self.assertTrue(snap["authPending"]); self.assertEqual(snap["auth"], "key")
        # an init during the hold (the delivery turn's) changes nothing: the running state is what it says
        s._adopt_fast_state({"fast_mode_state": "off", "fast_mode_disabled_reason": "sdk_opt_in_required"})
        snap = s.snapshot()
        self.assertEqual(snap["fast"], "off"); self.assertTrue(s.fast_opt)
        self.assertEqual(snap["pickHeld"]["surfaces"], ["fast", "auth"])
        self._stop(s, "a1")
        out = self._settle(s)                            # the settle that finds none: the arm flips
        self.assertTrue(out["reconnect"])
        snap = s.snapshot()
        self.assertIsNone(snap["pickHeld"])
        self.assertEqual(snap["fast"], "on", "the arm's optimism: the flag rides this connect")
        self.assertEqual(snap["authLive"], "", "the arm clears the report: it described the process this reconnect replaces")
        # an idle pick flips at its immediate arm, as before
        s = self._sess(auth="login")
        s._launched_auth = "login"; s.auth_live = "login"
        with mock.patch.object(sb.SdkBackend, "key_available", new_callable=mock.PropertyMock, return_value=True):
            self.assertTrue(s.backend.set_auth(self.SID, "key"))
        self.assertTrue(s._reconnect); self.assertEqual(s.auth_live, "")

    def test_n_the_hold_reports_whether_a_turn_is_open(self):
        # at zero counts the copy said "applies when this turn finishes" whatever the session was doing; in the
        # stuck-queue regime (the CLI started no delivery turn) an idle session showed it while the kernel log
        # said the pick waits for the next turn's settle. The payload carries whether a turn is open, so the
        # words can say which turn (review round 3); event-based, no timer
        s = self._sess()
        s._on_task_event("task_started", {"task_id": "b1", "task_type": "local_bash"})
        s.backend.set_effort(self.SID, "max")
        self.assertFalse(s._pick_held()["inflight"], "idle between its own turns")
        s._on_task_event("task_notification", {"task_id": "b1", "status": "completed"})
        h = s._pick_held()
        self.assertEqual((h["subagents"], h["tasks"], h["inflight"]), (0, 0, False),
                         "the work is done and no turn is open: the pick waits for the session's next turn")
        self.assertEqual(s.snapshot()["pickHeld"], {"surfaces": ["effort"], "subagents": 0, "tasks": 0, "inflight": False})
        s.inflight = 1                                   # the delivery turn opened
        self.assertTrue(s._pick_held()["inflight"], "a turn is open: the pick waits for it to finish")
        self.assertTrue(s.snapshot()["pickHeld"]["inflight"])

    def test_o_a_revert_then_a_re_pick_before_the_loop_serves_the_withdraw_keeps_the_re_pick(self):
        # the setters added a surface on the kernel thread, but the revert only QUEUED the withdraw, which
        # discarded on the loop: a revert then a re-pick of the same surface before the loop served the
        # withdraw lost the re-pick (review round 4). Mode: set_mode's guard read the stale membership and
        # logged "already applying" while the withdraw then ended the hold, so the reg said bypass and the
        # process ran default for good, every consult ringing the contract problem; effort and fast: the hold
        # stood with no surface (no badge mark, a subject-less chat line, no fast flip at the arm). The
        # discard is the kernel thread's now, in the order the picks arrive, and the loop decides the hold's
        # fate from the set it finds. A queuing loop double, since the _Now double serves each call at once
        class _OK:
            async def set_permission_mode(self_, m): pass
        q = self._Queue()
        s = self._sess(mode="default")
        s.perm_mode = "default"; s._launched_mode = "default"; s.client = _OK()
        s.loop = q
        s.set_mode_live = lambda mode, prev="default": asyncio.run(s._do_set_mode(mode, prev))
        self._start(s, "a1")
        self.assertTrue(s.backend.set_mode(self.SID, "bypassPermissions"))
        self.assertTrue(s.backend.set_mode(self.SID, "plan"))                # the revert: forgotten now, settled later
        self.assertNotIn("mode", s._reconnect_surfaces, "the kernel thread forgets the surface at once")
        self.assertIsNone(s.snapshot()["pickHeld"], "and the readers see no hold before the loop has run")
        self.assertEqual(s._launched_mode, "plan")
        self.assertTrue(s.backend.set_mode(self.SID, "bypassPermissions"))   # the re-pick, before the loop serves the withdraw
        self.assertIn("mode", s._reconnect_surfaces)
        self.assertFalse(any("already applying" in str(m) for m in self.logs), self.logs)
        self.assertEqual(s.snapshot()["pickHeld"]["surfaces"], ["mode"])
        q.flush()                                                            # the loop serves: request, withdraw, request
        self.assertTrue(s._reconnect_when_idle and s._reconnect_held_for_work, "the re-pick's reconnect stands")
        self.assertIn("mode", s._reconnect_surfaces)
        self.assertEqual(s.snapshot()["pickHeld"]["surfaces"], ["mode"])
        self.assertEqual(s.snapshot()["mode"], "plan", "the running mode while the bypass pick is held")
        self.assertTrue(any("a newer mode pick asks again after the withdrawn one; the reconnect stands" in str(m)
                            for m in self.logs), self.logs)
        self.assertEqual([m for m in self._withdrawn() if "only one pending" in m], [])
        self.assertEqual([m for m in self.logs if "it arms at the settle that finds none" in str(m)], [],
                         "the loop's own held line is not repeated: the setters said it")
        self._stop(s, "a1")
        out = self._settle(s)
        self.assertTrue(out["reconnect"], "the settle reconnects for the re-picked bypass")
        self.assertIn("the held mode pick reconnects now", self._armed()[0], self.logs)
        self.assertEqual(s.perm_mode, "bypassPermissions")
        self.assertEqual(sb.read_reg(s.backend.state_dir, self.SID).get("mode"), "bypassPermissions")
        # effort: the surface stays and the hold stands for the re-pick
        q = self._Queue()
        s = self._sess(effort="high")
        s._launched_effort = sb.effort_launch_shape("high")
        s.loop = q
        self._start(s, "a1")
        self.assertTrue(s.backend.set_effort(self.SID, "max"))
        self.assertTrue(s.backend.set_effort(self.SID, "high"))
        self.assertNotIn("effort", s._reconnect_surfaces); self.assertIsNone(s.snapshot()["pickHeld"])
        self.assertTrue(s.backend.set_effort(self.SID, "max"))
        self.assertIn("effort", s._reconnect_surfaces); self.assertEqual(s._effort_pending, "max")
        q.flush()
        self.assertTrue(s._reconnect_when_idle and s._reconnect_held_for_work)
        self.assertEqual(s.snapshot()["pickHeld"]["surfaces"], ["effort"])
        self.assertTrue(sb.read_reg(s.backend.state_dir, self.SID).get("effortPending"))
        self.assertTrue(any("a newer effort pick asks again after the withdrawn one" in str(m) for m in self.logs), self.logs)
        self.assertEqual([m for m in self._withdrawn() if "only one pending" in m], [])
        self._stop(s, "a1")
        self.assertTrue(self._settle(s)["reconnect"])
        self.assertIn("the held effort pick reconnects now", self._armed()[0], self.logs)
        # fast: the surface stays, and the arm flips the badge for the re-picked opt-in
        q = self._Queue()
        s = self._sess()
        s.thread = mock.Mock(is_alive=lambda: True)
        s.fast = "off"; s._fast_unlocked = False
        s.loop = q
        self._start(s, "a1")
        self.assertTrue(s.backend.set_fast(self.SID, "on"))
        self.assertTrue(s.backend.set_fast(self.SID, "off"))
        self.assertNotIn("fast", s._reconnect_surfaces); self.assertIsNone(s.snapshot()["pickHeld"])
        self.assertTrue(s.backend.set_fast(self.SID, "on"))
        self.assertIn("fast", s._reconnect_surfaces); self.assertTrue(s.fast_opt)
        q.flush()
        self.assertEqual(s.snapshot()["pickHeld"]["surfaces"], ["fast"])
        self.assertEqual(s.snapshot()["fast"], "off", "held: the badge shows the running state")
        self.assertTrue(any("a newer fast pick asks again after the withdrawn one" in str(m) for m in self.logs), self.logs)
        self._stop(s, "a1")
        self.assertTrue(self._settle(s)["reconnect"])
        self.assertEqual(s.fast, "on", "the arm flips: the flag rides this connect")
        self.assertIn("the held fast pick reconnects now", self._armed()[0], self.logs)

    def test_p_a_pick_after_the_immediate_arm_reads_the_connect_in_flight(self):
        # an idle pick arms at once: the arm flipped s.fast to on, cleared the surfaces, and the relaunch was a
        # teardown and a spawn away. An off pick in that window found no fast surface and no _launching (the
        # stamp was _options', a teardown later), so it read the OLD connection, logged "unchanged, no
        # reconnect" and left s.fast and the badge on for 2 to 7 s while the relaunch ran flagless; an effort
        # revert there logged "the pending max pick is withdrawn" while the armed reconnect relaunched the
        # identical shape. The arm opens the spawn window now (_launching, review round 4), so a pick made
        # between the arm and the connect is a connect-time pick, treated by the spawn-window guards
        s = self._sess()
        s.thread = mock.Mock(is_alive=lambda: True)
        s.fast = "off"; s._fast_unlocked = False
        self.assertTrue(s.backend.set_fast(self.SID, "on"))
        self.assertTrue(s._reconnect, "idle: the arm is immediate"); self.assertEqual(s.fast, "on", "the arm's flip")
        self.assertIsNotNone(s._launching, "the spawn window opens at the arm")
        self.assertEqual(s._reconnect_surfaces, set())
        self.assertTrue(s.backend.set_fast(self.SID, "off"))
        self.assertEqual(s.fast, "off", "s.fast follows the ask"); self.assertEqual(s.snapshot()["fast"], "off")
        self.assertFalse(s.fast_opt, "what _options hands the flag-settings file: no flag")
        self.assertFalse(sb.read_reg(s.backend.state_dir, self.SID).get("fast"), "the reg agrees")
        self.assertTrue(s._reconnect, "the armed reconnect stands, and relaunches without the flag")
        self.assertTrue(any("fast (web): set to off; the reconnect in flight launches without the flag" in str(m)
                            for m in self.logs), self.logs)
        self.assertFalse(any("unchanged, no reconnect" in str(m) for m in self.logs), self.logs)
        self.assertFalse(any("pick is withdrawn" in str(m) for m in self.logs), "nothing was pending to withdraw")
        # the landing closes the window: off on the landed flagless connection is unchanged, and says so
        s._reset_reconnect_state(); s._connect_landed()
        self.assertIsNone(s._launching)
        self.assertTrue(s.backend.set_fast(self.SID, "off"))
        self.assertTrue(any("fast (web): set to off; unchanged, no reconnect" in str(m) for m in self.logs), self.logs)
        # effort: the revert after the immediate arm is recorded pending against the shape being launched, never
        # logged as a withdrawal (the reconnect in flight cannot be withdrawn), and the landing clears it
        s = self._sess(effort="high")
        s._launched_effort = sb.effort_launch_shape("high")
        self.assertTrue(s.backend.set_effort(self.SID, "max"))
        self.assertTrue(s._reconnect)
        self.assertEqual(s._launching["effort"], sb.effort_launch_shape("max"), "the arm stamped the shape the relaunch runs")
        self.assertTrue(s.backend.set_effort(self.SID, "high"))
        self.assertEqual(s._effort_pending, "high", "recorded pending for the landing")
        self.assertTrue(sb.read_reg(s.backend.state_dir, self.SID).get("effortPending"))
        self.assertFalse(any("pick is withdrawn" in str(m) for m in self.logs), self.logs)
        self.assertFalse(any("unchanged, no reconnect" in str(m) for m in self.logs), "never unchanged while the reg disagrees")
        self.assertTrue(any("effort (web): set to high; reconnecting to apply" in str(m) for m in self.logs), self.logs)
        s._reset_reconnect_state()
        s._launching = s.backend._launch_shape(s)               # _options composes from the session: it reads high
        self.assertEqual(s._launching["effort"], sb.effort_launch_shape("high"))
        s._connect_landed()
        self.assertEqual(s._effort_pending, ""); self.assertEqual(s._launched_effort, sb.effort_launch_shape("high"))
        # a stamp already standing is never overwritten by a second arm: the connect _options composed runs
        # that shape, and the landing must stamp it as launched
        s = self._sess(effort="high")
        s._launched_effort = sb.effort_launch_shape("high")
        s._launching = {"effort": sb.effort_launch_shape("max"), "mode": "default", "auth": "login"}
        self.assertTrue(s.backend.set_effort(self.SID, "low"))
        self.assertTrue(s._reconnect)
        self.assertEqual(s._launching["effort"], sb.effort_launch_shape("max"), "the composed shape stands")

    def test_q_a_fast_pick_during_the_refusals_restore_makes_the_pending_relaunch_a_fast_pick(self):
        # a fast on during a fast-reset hold took the unlocked live send, re-armed fast_opt and reg.fast, logged
        # "applied live" and touched no surface: pickHeld kept naming the restore, the arm's line said "fast mode
        # restore" and _options composed a flagged relaunch (review round 4). The pending relaunch's surface
        # follows the ask in both directions now: the pick replaces the restore surface, and a second refusal
        # (the fed turn's init re-reporting the reason, what the real CLI does) or an off puts it back, so the
        # chat line, the arm's line and the flip describe the relaunch that happens. The pick reaches set_fast
        # by the composer's /fast on, the setFast ws message or POST /send
        refusal = {"fast_mode_state": "off", "fast_mode_disabled_reason": "extra_usage_disabled"}
        refusals = lambda: [str(m) for m in self.logs if "refused the toggle" in str(m)]
        s = self._sess()
        s.thread = mock.Mock(is_alive=lambda: True)
        s.fast = "off"; s._fast_unlocked = True; s.fast_opt = True
        self._start(s, "a1")
        s._adopt_fast_state(refusal)
        self.assertEqual(s._pick_held()["surfaces"], ["fast-reset"]); self.assertFalse(s.fast_opt)
        self.assertTrue(s.backend.set_fast(self.SID, "on"))              # the pick, during the restore's hold
        self.assertTrue(s.fast_opt); self.assertEqual(s.pending(), ["/fast on"], "the flagged connection takes the send")
        self.assertEqual(s._pick_held()["surfaces"], ["fast"], "the pending relaunch is a fast pick")
        self.assertNotIn("fast-reset", s._reconnect_surfaces)
        self.assertTrue(any("fast (web): set to on; applied live; the pending relaunch carries the flag" in str(m)
                            for m in self.logs), self.logs)
        # no second refusal before the settle: the relaunch carries the flag, and the arm's line and flip say so
        self._stop(s, "a1")
        out = self._settle(s)
        self.assertTrue(out["reconnect"])
        self.assertIn("the held fast pick reconnects now", self._armed()[0], self.logs)
        self.assertEqual(s.fast, "on", "the arm's flip: the flag rides this connect"); self.assertTrue(s.fast_opt)
        self.assertEqual(len(refusals()), 1)
        # the real CLI re-reports the refusal at the fed turn's init: the second refusal makes it a restore again
        s = self._sess()
        s.thread = mock.Mock(is_alive=lambda: True)
        s.fast = "off"; s._fast_unlocked = True; s.fast_opt = True
        self._start(s, "a1")
        s._adopt_fast_state(refusal)
        self.assertTrue(s.backend.set_fast(self.SID, "on"))
        self.assertEqual(s._pick_held()["surfaces"], ["fast"])
        s._adopt_fast_state(refusal)                                       # the fed /fast on turn's init
        self.assertEqual(len(refusals()), 2); self.assertFalse(s.fast_opt)
        self.assertEqual(s._pick_held()["surfaces"], ["fast-reset"], "the relaunch is the restore again")
        self.assertNotIn("fast", s._reconnect_surfaces)
        self.assertFalse(sb.read_reg(s.backend.state_dir, self.SID).get("fast"))
        self._stop(s, "a1")
        out = self._settle(s)
        self.assertTrue(out["reconnect"])
        self.assertIn("the held fast mode restore reconnects now", self._armed()[0], self.logs)
        self.assertNotIn("fast pick", self._armed()[0])
        self.assertEqual(s.fast, "off", "flagless: no flip")
        # an off during the pick's pending relaunch makes it the restore again, and says so
        s = self._sess()
        s.thread = mock.Mock(is_alive=lambda: True)
        s.fast = "off"; s._fast_unlocked = True; s.fast_opt = True
        self._start(s, "a1")
        s._adopt_fast_state(refusal)
        self.assertTrue(s.backend.set_fast(self.SID, "on"))
        self.assertTrue(s.backend.set_fast(self.SID, "off"))
        self.assertEqual(s.pending(), ["/fast on", "/fast off"])
        self.assertEqual(s._pick_held()["surfaces"], ["fast-reset"]); self.assertFalse(s.fast_opt)
        self.assertTrue(any("fast (web): set to off; applied live; the pending relaunch drops the flag" in str(m)
                            for m in self.logs), self.logs)
        # a live toggle with no relaunch pending swaps nothing and says nothing more
        s = self._sess()
        s.thread = mock.Mock(is_alive=lambda: True)
        s.fast = "off"; s._fast_unlocked = True; s.fast_opt = True
        self.assertTrue(s.backend.set_fast(self.SID, "on"))
        self.assertEqual(s._reconnect_surfaces, set())
        self.assertTrue(any(str(m).endswith("fast (web): set to on; applied live") for m in self.logs), self.logs)

    def test_r_set_env_withdraws_a_pending_env_pick_reverted_to_the_running_env(self):
        # set_env compared only against the reg, stamped no launched env and never withdrew: a revert to the env
        # the process runs while a different env pick was held kept the hold, and the settle relaunched the
        # identical env; the deferred form relaunched too (review round 4; not a regression against the base,
        # whose set_env reconnected at once, but a breach of the one-withdraw-routine contract). It compares
        # against the launched and the launching env now, like set_effort, and withdraws through the one routine
        s = self._sess(env={"A": "1"})
        s._launched_env = {"A": "1"}
        self._start(s, "a1")
        self.assertTrue(s.backend.set_env(self.SID, {"A": "2"}))
        self.assertTrue(s._reconnect_when_idle and s._reconnect_held_for_work)
        self.assertEqual(s.snapshot()["pickHeld"]["surfaces"], ["env"])
        self.assertTrue(s.backend.set_env(self.SID, {"A": "1"}))              # the revert
        self.assertIsNone(s.snapshot()["pickHeld"]); self.assertFalse(s._reconnect_when_idle)
        self.assertEqual(s.env_vars, {"A": "1"}); self.assertEqual(sb.read_reg(s.backend.state_dir, self.SID).get("env"), {"A": "1"})
        self.assertTrue(any("env (web): per-session env set (A); the pending env pick is withdrawn" in str(m) for m in self.logs), self.logs)
        self.assertTrue(any("the withdrawn env pick was the only one pending; no reconnect" in str(m) for m in self.logs), self.logs)
        self._stop(s, "a1")
        out = self._settle(s)
        self.assertFalse(out["reconnect"], "nothing relaunches the env the process already runs")
        self.assertEqual(self._armed(), [])
        # the deferred form: a turn open, no live work
        s = self._sess(env={"A": "1"})
        s._launched_env = {"A": "1"}
        s.inflight = 1
        self.assertTrue(s.backend.set_env(self.SID, {"A": "2"}))
        self.assertTrue(s._reconnect_when_idle and not s._reconnect)
        self.assertTrue(any("env (web): per-session env set (A); reconnect deferred to the end of the open turn" in str(m) for m in self.logs), self.logs)
        self.assertTrue(s.backend.set_env(self.SID, {"A": "1"}))
        self.assertFalse(s._reconnect_when_idle)
        out = self._settle(s)
        self.assertFalse(out["reconnect"]); self.assertFalse(out["deferred"])
        # the spawn window: the running env picked during another env's spawn is recorded and reconnects after
        # the landing (never a withdrawal, never unchanged); the env being launched, picked again, is already
        # applying. The arm stamps the env the relaunch runs, minus nothing here (no reserved names)
        s = self._sess(env={"A": "1"})
        s._launched_env = {"A": "1"}
        self.assertTrue(s.backend.set_env(self.SID, {"A": "2"}))
        self.assertTrue(s._reconnect); self.assertEqual(s._launching["env"], {"A": "2"})
        asked = []
        s.request_reconnect = lambda: asked.append(1)
        self.assertTrue(s.backend.set_env(self.SID, {"A": "1"}))
        self.assertEqual(asked, [1], "a reconnect is requested for after the launch lands")
        self.assertEqual(s.env_vars, {"A": "1"})
        self.assertFalse(any("withdrawn" in str(m) or "unchanged" in str(m) for m in self.logs if "env (web)" in str(m)), self.logs)
        self.assertTrue(s.backend.set_env(self.SID, {"A": "2"}))
        self.assertEqual(asked, [1], "already applying: no new request")
        self.assertTrue(any("env (web): per-session env set (A); already applying, no new request" in str(m) for m in self.logs), self.logs)
        self.assertEqual(s.env_vars, {"A": "2"})
        s._reset_reconnect_state()
        s._launching = s.backend._launch_shape(s)                          # _options composes from the session
        s._connect_landed()
        self.assertEqual(s._launched_env, {"A": "2"}, "the landing stamps the launched env")
        self.assertIsNone(s._launching)
        # a launch with no env stamps {}, and a fresh session has no stamp at all
        s = self._sess()
        self.assertIsNone(s._launched_env)
        s._launching = s.backend._launch_shape(s)
        self.assertEqual(s._launching["env"], {})
        s._connect_landed()
        self.assertEqual(s._launched_env, {})
        # an unchanged re-assert of the reg's env is a no-op before any compare, as before
        asked = []
        s.request_reconnect = lambda: asked.append(1)
        self.assertTrue(s.backend.set_env(self.SID, {}))
        self.assertEqual(asked, [])

    def test_s_a_second_withdrawal_between_the_settles_reads_neither_raises_nor_skips_the_poke(self):
        # _settle_withdrawal read the set three times (its truthiness, `surface in`, _pick_names for the line)
        # while the kernel thread discards from it: two picks held and both reverted, with the second revert
        # landing between the first settle's reads, emptied the set under the decision, and the line phrased an
        # empty list (IndexError out of the loop callback, no poke, the hold standing). One snapshot under the
        # one hold lock now, and the discard waits for it (review round 5). Two threads sequenced through
        # events: L is the loop serving the first revert's settle, parked after its first read; K is the
        # kernel thread making the second revert meanwhile
        q = self._Queue()
        s = self._sess(effort="high", auth="login")
        s._launched_effort = sb.effort_launch_shape("high"); s._launched_auth = "login"
        s.auth_live = "login"
        s.loop = q
        self._start(s, "a1")
        with mock.patch.object(sb.SdkBackend, "key_available", new_callable=mock.PropertyMock, return_value=True):
            self.assertTrue(s.backend.set_effort(self.SID, "max"))
            self.assertTrue(s.backend.set_auth(self.SID, "key"))
            q.flush()                                                        # the loop serves both requests
            self.assertTrue(s._reconnect_when_idle and s._reconnect_held_for_work)
            self.assertEqual(s._pick_names(), ["effort", "auth"])
            self.assertTrue(s.backend.set_effort(self.SID, "high"))         # the first revert: discarded now, settled by L
            self.assertEqual(s._pick_names(), ["auth"])
            settle = [c for c in q.queued if c[0] == s._settle_withdrawal]
            self.assertEqual(len(settle), 1); q.queued.remove(settle[0])
            self.pokes.clear()
            err = self._race(s, "any", lambda: s._settle_withdrawal("effort"),
                             lambda: s.backend.set_auth(self.SID, "login"))   # the second revert, between L's reads
        self.assertIsNone(err, "the settle raised: %r" % (err,))
        self.assertTrue(any("the withdrawn effort pick leaves the pending auth pick pending; the reconnect stands" in str(m)
                            for m in self.logs), self.logs)
        self.assertGreaterEqual(len(self.pokes), 1, "the first settle poked")
        self.assertTrue(any("auth (web): set to login; the pending key pick is withdrawn" in str(m) for m in self.logs), self.logs)
        q.flush()                                                            # the second revert's settle
        self.assertTrue(any("the withdrawn auth pick was the only one pending; no reconnect" in str(m) for m in self.logs), self.logs)
        self.assertFalse(s._reconnect_when_idle); self.assertFalse(s._reconnect_held_for_work)
        self.assertEqual(set(s._reconnect_surfaces), set()); self.assertIsNone(s._pick_held())
        self.assertEqual(s.auth_live, "login", "the report is kept: the process bills the login")
        self._stop(s, "a1")
        self.assertFalse(self._settle(s)["reconnect"], "nothing relaunches the shape the process runs")
        # and the phrase itself never raises on an empty list (a log line must not take a settle down)
        self.assertEqual(sb.SdkSession._picks_phrase([], "pending", "pending"), "no pending pick")
        self.assertEqual(sb.SdkSession._picks_phrase([], "held", "held"), "no held pick")

    def test_s2_a_pick_landing_between_the_arms_read_and_its_clear_keeps_its_surface_and_its_flip(self):
        # the settle's arm read the names (_pick_names inside _arm_reconnect) and then cleared the WHOLE set: a
        # kernel-thread pick landing between the two was wiped, so its own queued request armed naming nothing
        # and never flipped the fast badge on or cleared the billing report (the pick still rode the connect;
        # the badge read off until the landing's re-assert, the Billing row contradicted itself until the first
        # init). The arm, its read and the discard of exactly the names it read run in one hold of the one lock
        # now (review round 5). L is the loop at the delivery turn's settle, parked after its read of the names;
        # K is the kernel thread picking fast on and the key meanwhile
        q = self._Queue()
        s = self._sess(effort="high", auth="login")
        s._launched_effort = sb.effort_launch_shape("high"); s._launched_auth = "login"
        s.auth_live = "login"
        s.thread = mock.Mock(is_alive=lambda: True)
        s.fast = "off"; s._fast_unlocked = False
        s.loop = q
        self._start(s, "a1")
        self.assertTrue(s.backend.set_effort(self.SID, "max"))
        q.flush()
        self.assertTrue(s._reconnect_when_idle and s._reconnect_held_for_work)
        self._stop(s, "a1")                                                  # the work ends; the settle arms
        with mock.patch.object(sb.SdkBackend, "key_available", new_callable=mock.PropertyMock, return_value=True):
            def picks():
                s.backend.set_fast(self.SID, "on")
                s.backend.set_auth(self.SID, "key")
            err = self._race(s, ("__contains__", "env"),                      # the last name _pick_names checks
                             lambda: s._arm_reconnect_if_quiet("turn end", queued_ok=True), picks)
        self.assertIsNone(err, "the arm raised: %r" % (err,))
        self.assertTrue(s._reconnect, "the settle armed for the effort pick")
        self.assertEqual(s._pick_names(), ["fast", "auth"], "the picks that landed during the arm keep their surfaces")
        self.assertTrue(s.fast_opt); self.assertEqual(s._auth_pending, "key")
        q.flush()                                                            # the two picks' own requests arm
        self.assertEqual(s.fast, "on", "the fast pick's own arm flips the badge: the flag rides the connect")
        self.assertEqual(s.snapshot()["fast"], "on")
        self.assertEqual(s.auth_live, "", "the billing pick's own arm clears the report of the process this replaces")
        self.assertEqual(set(s._reconnect_surfaces), set())
        self.assertFalse(s._reconnect_when_idle)
        # the arm's line names what it read, the effort pick alone: the two later picks were not riding it
        self.assertIn("reconnect (web): live work finished; the held effort pick reconnects now", self._armed()[0])

    def test_s3_the_fast_and_fast_reset_swap_from_both_threads_leaves_one_consistent_surface(self):
        # set_fast's live path set the ask (fast_opt), sent the literal toggle (I/O on the kernel thread) and
        # then swapped the pending relaunch's surface to "fast"; the refusal the loop adopts from a turn's init
        # meanwhile answered that very ask (fast_opt False) and swapped the surface back to the restore. The two
        # swaps on two threads left {"fast"} with the flag off: pickHeld named a fast pick, the arm's line said
        # "the held fast pick reconnects now" and the relaunch ran flagless. Both swaps run under the one hold
        # lock now, and set_fast re-reads the ask inside it: an ask the refusal answered flips nothing and says
        # so (review round 5). K is the kernel thread inside set_fast, parked in the send; the refusal lands
        # from this thread while it is parked
        refusal = {"fast_mode_state": "off", "fast_mode_disabled_reason": "extra_usage_disabled"}
        q = self._Queue()
        s = self._sess()
        s.thread = mock.Mock(is_alive=lambda: True)
        s.fast = "off"; s._fast_unlocked = True; s.fast_opt = False
        s.loop = q
        self._start(s, "a1")
        parked, resume, sent = threading.Event(), threading.Event(), []

        def send(sid, text, **kw):
            sent.append(text)
            parked.set()
            resume.wait(5)
            return True
        s.backend.send = send
        kt = threading.Thread(target=lambda: s.backend.set_fast(self.SID, "on"), name="K")
        kt.start()
        self.assertTrue(parked.wait(5), "set_fast never reached the send")
        self.assertTrue(s.fast_opt, "the ask is armed before the send")
        s._adopt_fast_state(refusal)                                        # the CLI answers the ask meanwhile
        self.assertFalse(s.fast_opt); self.assertEqual(s._pick_names(), ["fast-reset"])
        resume.set(); kt.join(5)
        self.assertFalse(kt.is_alive())
        self.assertEqual(sent, ["/fast on"])
        self.assertEqual(s._pick_names(), ["fast-reset"], "the answered ask never re-makes the restore a fast pick")
        self.assertFalse(s.fast_opt); self.assertFalse(sb.read_reg(s.backend.state_dir, self.SID).get("fast"))
        self.assertEqual(s.fast, "off", "no optimistic flip for an ask the refusal answered")
        self.assertEqual(s._fast_expect, "")
        self.assertTrue(any("fast (web): set to on; the CLI refused the toggle meanwhile; the pick is back off" in str(m)
                            for m in self.logs), self.logs)
        self.assertFalse(any("applied live" in str(m) for m in self.logs), self.logs)
        q.flush()                                                            # the refusal's request: held for the work
        self.assertTrue(s._reconnect_when_idle and s._reconnect_held_for_work)
        self.assertEqual(s._pick_held()["surfaces"], ["fast-reset"])
        self._stop(s, "a1")
        self.assertTrue(self._settle(s)["reconnect"])
        self.assertIn("the held fast mode restore reconnects now", self._armed()[0], self.logs)
        self.assertEqual(s.fast, "off", "flagless: no flip")
        # the other order, the refusal first and the pick after it, is the ordinary pick during the restore's
        # hold (test_q); with no refusal in between the swap is as before
        s = self._sess()
        s.thread = mock.Mock(is_alive=lambda: True)
        s.fast = "off"; s._fast_unlocked = True; s.fast_opt = True
        s.backend.send = lambda sid, text, **kw: True
        self._start(s, "a1")
        s._adopt_fast_state(refusal)
        self.assertTrue(s.backend.set_fast(self.SID, "on"))
        self.assertEqual(s._pick_names(), ["fast"]); self.assertTrue(s.fast_opt); self.assertEqual(s.fast, "on")

    def test_t_a_bypass_re_pick_over_a_pending_pick_out_of_bypass_in_the_spawn_window_withdraws_it(self):
        # set_mode's withdraw branch (a pick OUT of bypass pending on the reconnect after the bypass connect in
        # flight, then bypass again) was executed by no test (review round 5, tests-1). The re-pick makes the
        # out-pick moot: its surface goes, the hold and the deferred reconnect end, no live call is made, and
        # the landing stamps the launched bypass with nothing owed. The bypass connect is spawning: no client,
        # _launching carries bypass, and a turn is open so the out-pick defers rather than arming
        live = []
        s = self._sess(mode="bypassPermissions")
        s.perm_mode = "bypassPermissions"; s._launched_mode = "default"
        s._launching = {"effort": sb.effort_launch_shape("high"), "mode": "bypassPermissions", "auth": "login", "env": {}}
        s.client = None; s.inflight = 1
        s.set_mode_live = lambda mode, prev="default": live.append((mode, prev))
        self.assertTrue(s.backend.set_mode(self.SID, "default"))
        self.assertIn("mode", s._reconnect_surfaces); self.assertTrue(s._reconnect_when_idle)
        self.assertTrue(any("mode (web): set to default; reconnect deferred to the end of the open turn" in str(m) for m in self.logs), self.logs)
        self.assertTrue(s.backend.set_mode(self.SID, "bypassPermissions"))
        self.assertTrue(any("mode (web): set to bypassPermissions; the pending default pick is withdrawn" in str(m)
                            for m in self.logs), self.logs)
        self.assertFalse(any("already applying" in str(m) for m in self.logs), self.logs)
        self.assertNotIn("mode", s._reconnect_surfaces)
        self.assertFalse(s._reconnect_when_idle); self.assertFalse(s._reconnect_held_for_work); self.assertFalse(s._reconnect)
        self.assertEqual(s.perm_mode, "bypassPermissions"); self.assertEqual(s.mode, "bypassPermissions")
        self.assertEqual(live, [], "no live call: the connect in flight launches bypass")
        self.assertIsNone(s.snapshot()["pickHeld"])
        self.assertTrue(any("the withdrawn mode pick was the only one pending; no reconnect" in str(m) for m in self.logs), self.logs)
        asked = []
        s.request_reconnect = lambda: asked.append(1)
        s._reset_reconnect_state(); s._connect_landed()
        self.assertEqual(s._launched_mode, "bypassPermissions"); self.assertEqual(asked, [])
        self.assertIsNone(s._launching)

    def test_t2_a_live_pick_with_no_connected_client_says_so_and_never_claims_applied_live(self):
        # set_mode's live branch on a session between connects (no spawn in progress, no client): the pick is
        # recorded in the reg and the line says the next connect carries it; until round 4 it said "applied
        # live" with set_mode_live sending to nobody. Asserted by no test before (review round 5, tests-3)
        s = self._sess(effort="high", mode="default")
        s.perm_mode = "default"; s._launched_mode = "default"
        s.client = None; s._launching = None
        live = []
        s.set_mode_live = lambda mode, prev="default": live.append((mode, prev))
        self.assertTrue(s.backend.set_mode(self.SID, "plan"))
        self.assertTrue(any("mode (web): set to plan; no connected client for the live switch; the reg carries the pick "
                            "to the next connect" in str(m) for m in self.logs), self.logs)
        self.assertFalse(any("applied live" in str(m) for m in self.logs), self.logs)
        self.assertEqual(live, [("plan", "default")], "set_mode_live is still asked (a no-op with no client)")
        self.assertEqual(sb.read_reg(s.backend.state_dir, self.SID).get("mode"), "plan")
        self.assertEqual(s._reconnect_surfaces, set()); self.assertFalse(s._reconnect_when_idle)
        self.assertEqual(s.perm_mode, "plan")

    def test_t3_a_bypass_re_pick_on_a_process_already_in_bypass_withdraws_the_out_pick_without_a_live_call(self):
        # the state a refused landing switch leaves: the process runs bypass, a pick OUT of bypass is pending
        # on the reconnect (its surface recorded), and the user picks bypass again. The re-pick took the live
        # branch and sent set_permission_mode(bypass) into a process already in bypass (the CLI accepts it on
        # a bypass launch, so no red problem; one redundant control request and an "applied live" line for a
        # mode the process already runs). It only withdraws the out-pick now (review round 5, fresh-2)
        s = self._sess(mode="default")
        s.perm_mode = "default"; s._launched_mode = "bypassPermissions"
        s.client = object(); s._launching = None
        with s._hold_lock:
            s._reconnect_surfaces.add("mode")
        s._reconnect_when_idle = True
        live = []
        s.set_mode_live = lambda mode, prev="default": live.append((mode, prev))
        self.assertTrue(s.backend.set_mode(self.SID, "bypassPermissions"))
        self.assertEqual(live, [], "never set_permission_mode into a process already in bypass")
        self.assertTrue(any("mode (web): set to bypassPermissions; the pending default pick is withdrawn" in str(m)
                            for m in self.logs), self.logs)
        self.assertFalse(any("applied live" in str(m) or "already applying" in str(m) for m in self.logs), self.logs)
        self.assertNotIn("mode", s._reconnect_surfaces)
        self.assertFalse(s._reconnect_when_idle, "the out-pick was the only one pending: nothing reconnects")
        self.assertEqual((s.perm_mode, s._launched_mode), ("bypassPermissions", "bypassPermissions"))
        self.assertEqual(s.snapshot()["mode"], "bypassPermissions")
        # a bypass re-pick while a bypass pick is HELD is the already-applying no-op it always was (test_j2)
        s = self._sess(mode="default")
        s.perm_mode = "default"; s._launched_mode = "default"
        s.set_mode_live = lambda mode, prev="default": live.append((mode, prev))
        self._start(s, "a1")
        s.backend.set_mode(self.SID, "bypassPermissions")
        s.backend.set_mode(self.SID, "bypassPermissions")
        self.assertEqual(live, [])
        self.assertTrue(any("already applying, no new request" in str(m) for m in self.logs), self.logs)
        self.assertEqual(s.snapshot()["pickHeld"]["surfaces"], ["mode"])

    def test_t4_a_revert_in_the_spawn_window_disarms_a_reconnect_armed_for_it_alone_and_leaves_one_armed_for_more(self):
        # the loop's ordering where the out-pick's request has NOT yet run when the re-pick lands (the surface
        # still recorded, the withdraw branch): the request then arms a reconnect after the connect in progress
        # and the queued settle finds it standing for the withdrawn pick alone, with the connect launching what
        # the session asks for: disarmed (review round 5). The same settle leaves the arm standing when another
        # pick is pending, when a rewind is, or when the connect in progress runs a different shape; and never
        # disarms in the arm-to-teardown half of the window (the old client still up), where the loop top
        # composes the relaunch from the session anyway
        def spawning(**reg):
            q = self._Queue()
            s = self._sess(**reg)
            s.loop = q
            s.perm_mode = s.mode = "bypassPermissions"; s._launched_mode = "default"
            s._launched_effort = sb.effort_launch_shape("high")
            s._launching = s.backend._launch_shape(s)                   # _options composed: bypass
            s._connecting = True; s.client = None
            s._wake = asyncio.Event(); s._wake.set()
            s._input_wake = asyncio.Event()
            s.set_mode_live = lambda mode, prev="default": None
            return s, q
        s, q = spawning(mode="bypassPermissions", effort="high")
        self.assertTrue(s.backend.set_mode(self.SID, "default"))       # pending: differs from the launching mode
        self.assertIn("mode", s._reconnect_surfaces)
        self.assertTrue(s.backend.set_mode(self.SID, "bypassPermissions"))   # the revert, request not yet served
        self.assertNotIn("mode", s._reconnect_surfaces)
        q.flush()                                                        # the request arms; the settle disarms
        self.assertFalse(s._reconnect, "the arm stood for the withdrawn pick alone")
        self.assertFalse(s._wake.is_set(), "the waker is not left set for the landing")
        self.assertTrue(s._input_wake.is_set(), "the feeder is woken: it holds the queue while _reconnect is set")
        self.assertFalse(s._reconnect_when_idle); self.assertFalse(s._reconnect_held_for_work)
        self.assertTrue(any("the withdrawn mode pick leaves the connect in progress launching what this session asks "
                            "for; the reconnect armed after it is disarmed" in str(m) for m in self.logs), self.logs)
        self.assertEqual(s._launching["mode"], "bypassPermissions", "the connect in progress is untouched")
        self.assertEqual(len(self.pokes), 1)
        # another pick pending: the arm stands for it
        s, q = spawning(mode="bypassPermissions", effort="high")
        self.assertTrue(s.backend.set_mode(self.SID, "default"))
        self.assertTrue(s.backend.set_effort(self.SID, "max"))
        self.assertTrue(s.backend.set_mode(self.SID, "bypassPermissions"))
        q.flush()
        self.assertTrue(s._reconnect, "the effort pick still needs the relaunch")
        self.assertEqual(s._pick_names(), [], "the arm cleared the surfaces it read")
        self.assertFalse(any("is disarmed" in str(m) for m in self.logs), self.logs)
        # the connect in progress runs another shape than the session asks for (a pick rode the arm): stands
        s, q = spawning(mode="bypassPermissions", effort="high")
        self.assertTrue(s.backend.set_mode(self.SID, "default"))
        q.flush()                                                        # armed; the surface cleared by the arm
        self.assertTrue(s._reconnect)
        s.effort = "max"                                                 # the session asks for more than bypass
        self.assertTrue(s.backend.set_mode(self.SID, "bypassPermissions"))   # already applying: a "repeat"
        q.flush()
        self.assertTrue(s._reconnect, "the connect in progress launches high; the arm stands for max")
        # a pending rewind: its arm stands
        s, q = spawning(mode="bypassPermissions", effort="high")
        s._rewind_to = "22222222-3333-4444-5555-666666666666"; s._rewind_armed = False
        self.assertTrue(s.backend.set_mode(self.SID, "default"))
        self.assertTrue(s.backend.set_mode(self.SID, "bypassPermissions"))
        q.flush()
        self.assertTrue(s._reconnect)
        # the arm-to-teardown half of the window: the old client is up, the connect is not composed; never disarm
        s, q = spawning(mode="bypassPermissions", effort="high")
        s._connecting = False; s.client = object()
        self.assertTrue(s.backend.set_mode(self.SID, "default"))
        self.assertTrue(s.backend.set_mode(self.SID, "bypassPermissions"))
        q.flush()
        self.assertTrue(s._reconnect, "the loop top composes the relaunch from the session; nothing to disarm yet")
        self.assertTrue(s._wake.is_set())
        # a deferred (never armed) reconnect naming no pick during a connect that launches what the session asks
        # for ends on the re-pick too: the loop-top clear's known case, a window pick riding the connect
        s, q = spawning(mode="bypassPermissions", effort="high")
        s._reconnect_when_idle = True
        self.assertTrue(s.backend.set_mode(self.SID, "bypassPermissions"))
        q.flush()
        self.assertFalse(s._reconnect_when_idle)
        self.assertTrue(any("the re-picked mode was the only one pending; no reconnect" in str(m) for m in self.logs), self.logs)

    def test_k_every_held_kind_marks_the_snapshot_and_the_badges_read_the_running_value(self):
        # one marker (pickHeld) for effort, mode, fast and auth; the values beside it are what the process
        # RUNS: the effort it launched with, the mode it runs, the fast state the init reported, the CLI's
        # own billing report, so no badge shows a pick as if it applied (review round 2)
        s = self._sess(effort="high", mode="default", auth="key")
        s.perm_mode = "default"; s._launched_mode = "default"
        s._launched_effort = sb.effort_launch_shape("high"); s._launched_auth = "key"
        s.auth_live = "key"; s.fast = "off"
        s.thread = mock.Mock(is_alive=lambda: True)
        s.set_mode_live = lambda mode, prev="default": None
        self._start(s, "a1")
        self.assertTrue(s.backend.set_effort(self.SID, "max"))
        snap = s.snapshot()
        self.assertEqual(snap["pickHeld"], {"surfaces": ["effort"], "subagents": 1, "tasks": 0, "inflight": False})
        self.assertEqual(snap["effort"], "high", "the badge shows the running effort, not the pick")
        self.assertEqual(s.effort, "max", "the pick itself is what the reconnect will launch")
        self.assertTrue(snap["effortPending"])
        s.backend.set_mode(self.SID, "bypassPermissions")
        s.backend.set_fast(self.SID, "on")
        s.backend.set_auth(self.SID, "login")
        snap = s.snapshot()
        self.assertEqual(snap["pickHeld"]["surfaces"], ["effort", "mode", "fast", "auth"])
        self.assertEqual(snap["mode"], "default")
        self.assertEqual(snap["fast"], "off", "no optimistic flip while held: the running state stays")
        self.assertTrue(s.fast_opt, "the ask is armed for the connect")
        self.assertEqual(snap["auth"], "login", "the pick is the intent"); self.assertTrue(snap["authPending"])
        self.assertEqual(snap["authLive"], "key", "the CLI's report still describes the running process")
        # an init during the hold (the delivery turn's) re-asserts off; the marker stands and the ask stays
        s._adopt_fast_state({"fast_mode_state": "off", "fast_mode_disabled_reason": "sdk_opt_in_required"})
        snap = s.snapshot()
        self.assertEqual(snap["fast"], "off"); self.assertTrue(s.fast_opt)
        self.assertIn("fast", snap["pickHeld"]["surfaces"])
        self._stop(s, "a1")
        self.assertTrue(self._settle(s)["reconnect"])
        snap = s.snapshot()
        self.assertIsNone(snap["pickHeld"])
        self.assertEqual(snap["effort"], "max", "armed: the pick is what reloads")
        self.assertEqual(snap["fast"], "on", "the badge's optimism at the arm: the flag rides this connect")
        self.assertEqual(snap["authLive"], "", "the report described the process this reconnect replaces")
        self.assertEqual(snap["mode"], "bypassPermissions")
        # ultracode is reported as itself while held; an unlaunched session has no running value to show
        s = self._sess(effort="ultracode")
        s._launched_effort = sb.effort_launch_shape("ultracode")
        self._start(s, "a1")
        s.backend.set_effort(self.SID, "low")
        self.assertEqual(s.snapshot()["effort"], "ultracode")
        s = self._sess(effort="high")
        self._start(s, "a1")
        s.backend.set_effort(self.SID, "low")
        self.assertEqual(s.snapshot()["effort"], "low")
        # an idle fast pick keeps the optimistic flip the badge relied on (2026-08-11): its arm is immediate,
        # and the flip is the arm's (review round 3)
        s = self._sess()
        s.fast = "off"; s.thread = mock.Mock(is_alive=lambda: True)
        s.backend.set_fast(self.SID, "on")
        self.assertEqual(s.fast, "on"); self.assertTrue(s._reconnect)


class SettingsPickThroughTheLoop(unittest.TestCase):
    """The reconnect a settings pick asks for, driven through the REAL loop (_amain) against a stand-in SDK
    module, so the loop top's _reset_reconnect_state and the landing's _connect_landed run where they live:
    until review round 2 (2026-09-09) every test called both helpers by hand, and the loop top reverted to
    the round-0 line, or the landing call replaced with `pass`, left every module green. The client records
    the options it was built with; the test pushes the frames (init, assistant, result) the CLI would
    stream. Private synthetic sid and CLI session id; the name and every text are invented."""

    SID = "5e771e5d-9a1c-4b0f-8d2e-000000000438"    # private synthetic sid, never the shared placeholder
    FSID = "5e771e5d-9a1c-4b0f-8d2e-ffffffff0438"   # the CLI's own session id, announced by the init

    class _Client:
        instances = []
        spawn_gate = {}   # client index -> threading.Event: that client's __aenter__ waits for it, so a test can
        #   hold the spawn window open (the connect in progress, no client yet) and pick during it
        refuse_modes = False   # set_permission_mode raises, as the CLI does for a switch INTO bypass on a process
        #   not launched with the flag (T139); the landing's live switch takes its refusal path (review round 5)

        def __init__(self, options=None, transport=None):
            self.options = options
            type(self).instances.append(self)
            self.loop = asyncio.get_running_loop()
            self.frames = asyncio.Queue()
            self.writes = []
            self.modes = []   # the live switches this process took (set_permission_mode), in order
            self.torn_down = False

        async def set_permission_mode(self, mode):
            if type(self).refuse_modes:
                raise RuntimeError("Cannot set permission mode to %s" % mode)
            self.modes.append(mode)

        async def __aenter__(self):
            gate = type(self).spawn_gate.get(type(self).instances.index(self))
            if gate is not None:
                await self.loop.run_in_executor(None, gate.wait)
            return self

        async def __aexit__(self, *a):
            self.torn_down = True
            return False

        async def query(self, prompt, session_id="default"):
            async for turn in prompt:
                self.writes.append(turn["message"]["content"][0]["text"])

        async def interrupt(self):
            pass

        async def get_context_usage(self):
            return {"percentage": 2, "model": "claude-x"}

        async def get_server_info(self):
            return {}

        async def receive_messages(self):
            while True:
                yield await self.frames.get()

    class _Options:
        def __init__(self, **kw):
            self.session_id = self.resume = None
            for k, v in kw.items():
                setattr(self, k, v)

    class _Sys:
        def __init__(self, subtype, data, uuid):
            self.subtype, self.data, self.uuid = subtype, data, uuid

    class _Asst:
        def __init__(self, text, uuid):
            self.content, self.model, self.uuid = [_TextBlock(text)], "claude-x", uuid
            self.parent_tool_use_id, self.stop_reason, self.error = None, "end_turn", None

    _Sys.__name__ = "SystemMessage"; _Asst.__name__ = "AssistantMessage"

    def setUp(self):
        self._Client.instances = []
        self._Client.spawn_gate = {}
        self._Client.refuse_modes = False
        fake = types.ModuleType("claude_agent_sdk")
        fake.__spec__ = ModuleSpec("claude_agent_sdk", loader=None)
        fake.ClaudeSDKClient, fake.ClaudeAgentOptions, fake.HookMatcher = self._Client, self._Options, (lambda **kw: kw)
        fake.AssistantMessage, fake.ResultMessage, fake.SystemMessage = self._Asst, _ResultMessage, self._Sys
        fake.TextBlock = _TextBlock
        class _PRA:   # _can_use_tool imports the SDK's result classes at call time (test_i2's stubs)
            def __init__(self, behavior="allow", **kw): self.behavior = behavior
        class _PRD:
            def __init__(self, behavior="deny", **kw): self.behavior = behavior
        fake.PermissionResultAllow, fake.PermissionResultDeny = _PRA, _PRD
        self._saved_sdk = sys.modules.get("claude_agent_sdk")
        sys.modules["claude_agent_sdk"] = fake
        async def _noop_refresh(self_): pass
        self._saved_refresh = sb.SdkSession._do_refresh_usage
        sb.SdkSession._do_refresh_usage = _noop_refresh
        self.state = tempfile.mkdtemp()
        self.cwd = os.path.join(self.state, "proj")
        os.makedirs(self.cwd)
        self.lines = []
        self.be = sb.SdkBackend(self.state, "/bin/true", lambda *a, **k: None,
                                log=lambda m, **k: self.lines.append(str(m)))
        reg = {"sid": self.SID, "name": "web", "mode": "default", "effort": "high", "alive": True, "cwd": self.cwd}
        sb.write_reg(self.be.state_dir, self.SID, reg)
        self.s = sb.SdkSession(self.be, dict(reg))
        self.be.sessions[self.SID] = self.s
        self.n = 0

    def tearDown(self):
        if self.s.thread.is_alive():
            self.s.shutdown()
        if self.s.thread.ident is not None:
            self.s.thread.join(timeout=10)
        sb.SdkSession._do_refresh_usage = self._saved_refresh
        if self._saved_sdk is None:
            sys.modules.pop("claude_agent_sdk", None)
        else:
            sys.modules["claude_agent_sdk"] = self._saved_sdk
        j = Path(os.environ["XDG_STATE_HOME"]) / "romp" / "overrides" / (self.SID + ".jsonl")
        if j.exists():
            j.unlink()
        shutil.rmtree(self.state, ignore_errors=True)

    def _wait(self, pred, what, timeout=10.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if pred():
                return
            time.sleep(0.01)
        self.fail("timed out waiting for %s; clients %d; log tail %r"
                  % (what, len(self._Client.instances), self.lines[-8:]))

    def _uid(self):
        self.n += 1
        return "5e771e5d-9a1c-4b0f-8d2e-%012d" % self.n

    def _push(self, client, frame):
        client.loop.call_soon_threadsafe(client.frames.put_nowait, frame)

    def _turn(self, client, mode="default"):
        """One turn the CLI starts on its own (the delivery turn after a background task's end, or any turn
        romp did not feed): init, a reply, the result. Its settle is the arm's one event. `mode` is the
        permission mode the init reports, the one the process runs."""
        self._push(client, self._Sys("init", {"model": "claude-x", "permissionMode": mode,
                                              "session_id": self.FSID}, self._uid()))
        self._push(client, self._Asst("here is the result", self._uid()))
        self._push(client, type("ResultMessage", (_ResultMessage,), dict(
            uuid=self._uid(), subtype="success", is_error=False, num_turns=1, session_id=self.FSID,
            duration_ms=1, duration_api_ms=1, total_cost_usd=0.01, usage={"input_tokens": 1, "output_tokens": 1},
            result="ok", parent_tool_use_id=None))())

    def _connect(self):
        s = self.s
        s.start()
        self._wait(lambda: s.client is not None and s._launched_effort is not None, "the first connect landed")
        return self._Client.instances[0]

    def _applied(self):
        p = Path(self.be.state_dir) / "states" / (self.SID + ".jsonl")
        return [json.loads(l)["effortApplied"] for l in p.read_text().splitlines() if "effortApplied" in l] if p.exists() else []

    def test_an_idle_effort_pick_reconnects_through_the_loop_and_the_landing_stamps_the_new_shape(self):
        s, c1 = self.s, self._connect()
        self.assertEqual(s._launched_effort, ("high", False), "the first landing stamped the launch shape")
        self.assertEqual(c1.options.effort, "high")
        self.assertTrue(self.be.set_effort(self.SID, "low"))
        # the reg's effortPending is written one statement after the field this waits on (_connect_landed:
        # the field, then _update_reg's locked read, temp file and replace), and the assertion below reads
        # the reg: wait on the flag it asserts (review round 4; the test failed alone 2 of 20 runs)
        self._wait(lambda: len(self._Client.instances) == 2 and self._Client.instances[1] is s.client
                   and s._effort_pending == "" and not (sb.read_reg(self.be.state_dir, self.SID) or {}).get("effortPending"),
                   "the reconnect landed and cleared the pending pick")
        c2 = self._Client.instances[1]
        self.assertTrue(c1.torn_down, "the old client was abandoned")
        self.assertEqual(c2.options.effort, "low", "the new client launched the pick")
        self.assertEqual(s._launched_effort, ("low", False), "stamped where the connect lands")
        self.assertIsNone(s._launching, "the spawn window ended at the landing (review round 3)")
        self.assertFalse(sb.read_reg(self.be.state_dir, self.SID).get("effortPending"))
        self.assertEqual(self._applied(), ["low"], "the applied record, once, at the landing")
        self.assertFalse(s._reconnect); self.assertFalse(s._reconnect_when_idle)
        self.assertFalse(s._reconnect_held_for_work); self.assertEqual(s._reconnect_surfaces, set())
        self.assertIsNone(s.snapshot()["pickHeld"])
        self.assertTrue(self.be.set_effort(self.SID, "low"))
        time.sleep(0.2)
        self.assertEqual(len(self._Client.instances), 2, "the launched value picked again reconnects nothing")

    def test_a_held_pick_survives_a_settle_over_live_work_and_reconnects_at_the_settle_that_finds_none(self):
        s, c1 = self.s, self._connect()
        asyncio.run(s._subagent_start_hook({"agent_id": "a1", "agent_type": "general-purpose"}, None, None))
        self.assertTrue(self.be.set_effort(self.SID, "low"))
        self._wait(lambda: s._reconnect_when_idle, "the request ran on the loop")
        self.assertTrue(s._reconnect_held_for_work)
        self.assertEqual(s.snapshot()["pickHeld"], {"surfaces": ["effort"], "subagents": 1, "tasks": 0, "inflight": False})
        self.assertEqual(s.snapshot()["effort"], "high", "the running value while held")
        self._turn(c1)                                   # a turn ends while the subagent still runs
        self._wait(lambda: s.inflight == 0 and s._settled_msg is not None, "the turn settled")
        time.sleep(0.2)
        self.assertEqual(len(self._Client.instances), 1, "no reconnect: the settle found live work")
        self.assertTrue(s._reconnect_when_idle)
        asyncio.run(s._subagent_stop_hook({"agent_id": "a1", "agent_type": "general-purpose"}, None, None))
        time.sleep(0.2)
        self.assertEqual(len(self._Client.instances), 1, "the stop is not the arm")
        self.assertTrue(any("a subagent ended; the live sets are empty" in l for l in self.lines), self.lines)
        s._settled_msg = None
        self._turn(c1)                                   # the delivery turn: its settle finds the sets empty
        self._wait(lambda: len(self._Client.instances) == 2 and self._Client.instances[1] is s.client
                   and s._effort_pending == "", "the reconnect at the settle that found no live work")
        self.assertTrue(any("live work finished; the held effort pick reconnects now" in l for l in self.lines), self.lines)
        self.assertEqual([l for l in self.lines if " this reconnect" in l], [],
                         "the loop top found the arm it was woken for, nothing else pending (either verb)")
        self.assertEqual(s._launched_effort, ("low", False))
        self.assertEqual(self._Client.instances[1].options.effort, "low")
        self.assertEqual(self._applied(), ["low"])
        self.assertFalse(s._reconnect_held_for_work); self.assertIsNone(s.snapshot()["pickHeld"])
        self.assertEqual(s.snapshot()["effort"], "low")


    def test_a_held_bypass_pick_survives_a_cli_started_turns_init_and_the_landing_agrees(self):
        # the per-turn init reset perm_mode to the running mode at the first CLI-started turn of a hold, so
        # the held-consult auto-allow stopped applying and every later consult took the ask path against the
        # declared bypass (review round 3). perm_mode is the declared intent for the whole hold; the init's
        # report goes to the stamp (the mode the process runs), and after the arm and the landing the two agree
        s, c1 = self.s, self._connect()
        self.assertEqual(s._launched_mode, "default")
        asyncio.run(s._subagent_start_hook({"agent_id": "a1", "agent_type": "general-purpose"}, None, None))
        self.assertTrue(self.be.set_mode(self.SID, "bypassPermissions"))
        self._wait(lambda: s._reconnect_when_idle, "the request ran on the loop")
        self.assertTrue(s._reconnect_held_for_work)
        self.assertEqual(s.perm_mode, "bypassPermissions"); self.assertEqual(s.snapshot()["mode"], "default")
        self._turn(c1)                                   # a CLI-started turn during the hold: its init reports default
        self._wait(lambda: s.inflight == 0 and s._settled_msg is not None, "the turn settled")
        time.sleep(0.2)
        self.assertEqual(len(self._Client.instances), 1, "no reconnect: the settle found live work")
        self.assertEqual(s.perm_mode, "bypassPermissions", "the declared intent survives the init")
        self.assertEqual(s._launched_mode, "default", "the init's report is the running mode")
        self.assertEqual(s.snapshot()["mode"], "default")
        self.assertEqual(s.snapshot()["pickHeld"]["surfaces"], ["mode"])
        # the consult guard still auto-allows, with its line and no ask
        res = asyncio.run(s._can_use_tool("Bash", {"command": "ls"}, object()))
        self.assertEqual(res.behavior, "allow")
        self.assertIsNone(self.be._pending_ask.get(self.SID), "no ask reached the user")
        self.assertTrue(any("while the bypass pick is held" in l for l in self.lines), self.lines[-6:])
        self.assertEqual([l for l in self.lines if "contract says this cannot happen" in l], [])
        # the work ends; the delivery turn's settle arms; the new client launches bypass
        asyncio.run(s._subagent_stop_hook({"agent_id": "a1", "agent_type": "general-purpose"}, None, None))
        s._settled_msg = None
        self._turn(c1)
        # self.client is set 17 lines before _connect_landed stamps the launched mode asserted below: wait for
        # the landing itself, the end of the spawn window (review round 4)
        self._wait(lambda: len(self._Client.instances) == 2 and self._Client.instances[1] is s.client
                   and s._launching is None, "the reconnect at the settle that found no live work landed")
        c2 = self._Client.instances[1]
        self.assertEqual(c2.options.permission_mode, "bypassPermissions")
        self.assertEqual(s._launched_mode, "bypassPermissions", "the landing stamps the launched mode")
        self.assertEqual(s.perm_mode, "bypassPermissions")
        self.assertEqual(s.snapshot()["mode"], "bypassPermissions")
        self.assertIsNone(s.snapshot()["pickHeld"])
        s._settled_msg = None
        self._turn(c2, mode="bypassPermissions")         # the new process's first init confirms it
        self._wait(lambda: s.inflight == 0 and s._settled_msg is not None, "the first turn settled")
        self.assertEqual((s.perm_mode, s._launched_mode), ("bypassPermissions", "bypassPermissions"))
        # with no mode pick pending, today's behaviour: the init's report IS perm_mode
        s._settled_msg = None
        self._turn(c2, mode="acceptEdits")
        self._wait(lambda: s.inflight == 0 and s._settled_msg is not None, "the turn settled")
        self.assertEqual(s.perm_mode, "acceptEdits")

    def test_a_live_pick_out_of_bypass_in_the_spawn_window_is_pending_and_applies_live_at_the_landing(self):
        # a pick OUT of bypass made while the bypass connect was spawning (s.client None, _launching mode
        # bypass) took set_mode's live branch: set_mode_live had no client and dropped it silently while the
        # line said "applied live"; nothing armed, the landing stamped bypass, the first init wrote bypass to
        # perm_mode, and the reg said default against a process running bypass until some later reconnect
        # applied the pick by accident (review round 4). In the spawn window the pick is a connect-time pick:
        # recorded pending and said so. Round 4 applied it by a THIRD client after the landing; since review
        # round 5 the landing applies it LIVE over the control channel (a switch out of bypass is one the CLI
        # accepts on a bypass launch), before any queued turn could run, and the reconnect the pick's own
        # request armed during the spawn, standing for that pick alone, is disarmed by its settle: two
        # clients, the second switched. The second client's __aenter__ is held on an event so the window
        # stays open for the pick
        s, c1 = self.s, self._connect()
        gate = threading.Event()
        self.addCleanup(gate.set)                                    # a failed assertion must not leave the loop thread on the gate
        self._Client.spawn_gate[1] = gate
        self.assertTrue(self.be.set_mode(self.SID, "bypassPermissions"))
        self._wait(lambda: len(self._Client.instances) == 2 and s.client is None, "the bypass connect is spawning")
        self.assertEqual((s._launching or {}).get("mode"), "bypassPermissions")
        self.assertTrue(s._connecting, "the composed half of the spawn window")
        n0 = len(self.lines)
        self.assertTrue(self.be.set_mode(self.SID, "default"))      # a live pick OUT of bypass, during the spawn
        new = self.lines[n0:]
        self.assertTrue(any("mode (web): set to default; reconnecting to apply" in l for l in new), new)
        self.assertFalse(any("applied live" in l for l in new), new)
        self._wait(lambda: s._reconnect, "the pick's request armed a reconnect after the connect in progress")
        gate.set()                                                   # the bypass connect lands
        c2 = self._Client.instances[1]
        self._wait(lambda: c2 is s.client and s._launching is None and s._launched_mode == "default",
                   "the landing applied the pick live")
        self.assertEqual(c2.options.permission_mode, "bypassPermissions", "launched in bypass")
        self.assertEqual(c2.modes, ["default"], "and switched out of it at the landing, before the feeder")
        self.assertTrue(any("mode (web): the pending default pick applied live at the landing, before any queued turn; "
                            "the process launched bypassPermissions" in l for l in self.lines), self.lines)
        self._wait(lambda: not s._reconnect, "the redundant arm was disarmed by the applied pick's settle")
        self.assertTrue(any("the mode pick applied live at the landing leaves the connect in progress launching what "
                            "this session asks for; the reconnect armed after it is disarmed" in l for l in self.lines), self.lines)
        time.sleep(0.3)
        self.assertEqual(len(self._Client.instances), 2, "no third client: the live switch was the apply")
        self.assertFalse(c2.torn_down)
        self.assertEqual(s._launched_mode, "default"); self.assertEqual(s.perm_mode, "default")
        self.assertEqual(sb.read_reg(self.be.state_dir, self.SID).get("mode"), "default", "the reg agrees with the process")
        self.assertEqual(s.snapshot()["mode"], "default"); self.assertIsNone(s.snapshot()["pickHeld"])
        self.assertFalse(s._reconnect); self.assertFalse(s._reconnect_when_idle)
        self.assertEqual(s._reconnect_surfaces, set())
        self.assertEqual([l for l in self.lines if "contract says this cannot happen" in l], [])
        # the switched process takes a turn as any connected client does
        self.be.send(self.SID, "after the switch")
        self._wait(lambda: c2.writes == ["after the switch"], "the feeder runs on the switched client")
        self._turn(c2, mode="default")
        self._wait(lambda: s.inflight == 0 and s._settled_msg is not None, "that turn settled")
        self.assertEqual(s.perm_mode, "default")
        # a repeat of the mode being launched, during its own spawn, is already applying and reconnects nothing
        self._Client.spawn_gate[2] = gate2 = threading.Event()
        self.addCleanup(gate2.set)
        self.assertTrue(self.be.set_mode(self.SID, "bypassPermissions"))
        self._wait(lambda: len(self._Client.instances) == 3 and s.client is None, "the second bypass connect is spawning")
        n1 = len(self.lines)
        self.assertTrue(self.be.set_mode(self.SID, "bypassPermissions"))
        self.assertTrue(any("mode (web): set to bypassPermissions; already applying, no new request" in l for l in self.lines[n1:]), self.lines[n1:])
        gate2.set()
        self._wait(lambda: self._Client.instances[2] is s.client and s._launching is None, "the second bypass connect landed")
        time.sleep(0.2)
        self.assertEqual(len(self._Client.instances), 3, "the repeat pick reconnected nothing")
        self.assertEqual(s._launched_mode, "bypassPermissions")
        self.assertEqual(self._Client.instances[2].modes, [], "nothing owed at that landing: the declared mode launched")

    def test_a_queued_turn_never_runs_on_bypass_after_the_user_withdrew_it(self):
        # a pick OUT of bypass made in a bypass spawn with a text queued was a DEFERRED pick (the request saw
        # the queue and waited for a settle): the landing stamped bypass, the feeder released the queued turn
        # to the bypass process, and it ran with no consults while the reg, perm_mode and snapshot read
        # "default" with no held mark; the default relaunch came only at that turn's settle (review round 5,
        # kernel-1). The landing applies the pick live BEFORE the feeder exists, so the queued turn runs in
        # the picked mode, consults on; the deferred reconnect, which stood for that pick alone, ends
        s, c1 = self.s, self._connect()
        gate = threading.Event()
        self.addCleanup(gate.set)
        self._Client.spawn_gate[1] = gate
        self.assertTrue(self.be.set_mode(self.SID, "bypassPermissions"))
        self._wait(lambda: len(self._Client.instances) == 2 and s.client is None, "the bypass connect is spawning")
        self.assertTrue(self.be.send(self.SID, "run the deploy"))   # queued: no client to feed it to yet
        self.assertEqual(s.pending(), ["run the deploy"])
        n0 = len(self.lines)
        self.assertTrue(self.be.set_mode(self.SID, "default"))      # the user withdraws bypass before the turn runs
        self.assertTrue(any("mode (web): set to default; reconnect deferred to the end of the open turn" in l
                            for l in self.lines[n0:]), self.lines[n0:])
        self._wait(lambda: s._reconnect_when_idle, "the pick's request deferred behind the queued text")
        self.assertFalse(s._reconnect)
        gate.set()
        c2 = self._Client.instances[1]
        self._wait(lambda: c2.writes == ["run the deploy"], "the queued turn ran")
        self.assertEqual(c2.modes, ["default"], "switched out of bypass BEFORE the queued turn was fed")
        self.assertEqual(s._launched_mode, "default", "the process runs the picked mode")
        self.assertEqual(s.perm_mode, "default")
        self.assertEqual(sb.read_reg(self.be.state_dir, self.SID).get("mode"), "default")
        self.assertEqual(s.snapshot()["mode"], "default"); self.assertIsNone(s.snapshot()["pickHeld"])
        self.assertFalse(s._reconnect_when_idle, "the deferred reconnect stood for the applied pick alone")
        self.assertFalse(s._reconnect); self.assertEqual(s._reconnect_surfaces, set())
        self.assertTrue(any("the mode pick applied live at the landing was the only one pending; no reconnect" in l
                            for l in self.lines), self.lines)
        self._turn(c2, mode="default")
        self._wait(lambda: s.inflight == 0 and s._settled_msg is not None, "the turn settled")
        time.sleep(0.2)
        self.assertEqual(len(self._Client.instances), 2, "the settle relaunched nothing: the pick applied live")
        # the refusal path: a CLI that refuses the landing's switch keeps the queued turn HELD, and the reconnect
        # applies the pick; the queued text reaches the new client, never the process running the withdrawn mode
        self._Client.refuse_modes = True
        self._Client.spawn_gate[2] = gate2 = threading.Event()
        self.addCleanup(gate2.set)
        self.assertTrue(self.be.set_mode(self.SID, "bypassPermissions"))
        self._wait(lambda: len(self._Client.instances) == 3 and s.client is None, "the second bypass connect is spawning")
        self.assertTrue(self.be.send(self.SID, "and the tests"))
        self.assertTrue(self.be.set_mode(self.SID, "default"))
        self._wait(lambda: s._reconnect_when_idle, "deferred behind the queued text")
        gate2.set()
        self._wait(lambda: len(self._Client.instances) == 4 and self._Client.instances[3] is s.client
                   and s._launching is None, "the refused switch's reconnect landed the picked mode")
        c3, c4 = self._Client.instances[2], self._Client.instances[3]
        self.assertEqual(c3.writes, [], "the bypass process was fed nothing: the queue stayed held")
        self.assertTrue(c3.torn_down)
        self.assertEqual(c4.options.permission_mode, "default")
        self._wait(lambda: c4.writes == ["and the tests"], "the new client took the queued turn")
        self.assertTrue(any("refused the live switch to the pending default pick" in l and "the queued turns wait for the "
                            "new client" in l for l in self.lines), self.lines)
        self.assertEqual(s._launched_mode, "default"); self.assertEqual(s.perm_mode, "default")
        self.assertEqual(sb.read_reg(self.be.state_dir, self.SID).get("mode"), "default")
        self.assertEqual([l for l in self.lines if "contract says this cannot happen" in l], [])
        self._Client.refuse_modes = False

    def test_a_revert_in_the_spawn_window_disarms_the_reconnect_that_stood_for_it_alone(self):
        # bypass, then default, then bypass within one bypass spawn: the default pick's request armed a
        # reconnect after the connect in progress, and the bypass re-pick logged "already applying, no new
        # request" while that arm stood, so the loop relaunched the identical bypass shape after the landing
        # (three clients); effort high, max, high launched three the same way, the revert saying "the pending
        # max pick is withdrawn" with the arm standing (review round 5: correctness-2 and fresh-1, one root, an
        # armed reconnect had no un-arm). The settle of the withdrawal or re-pick disarms an arm that stands
        # for the withdrawn pick alone when the connect in progress launches what the session asks for
        s, c1 = self.s, self._connect()
        gate = threading.Event()
        self.addCleanup(gate.set)
        self._Client.spawn_gate[1] = gate
        self.assertTrue(self.be.set_mode(self.SID, "bypassPermissions"))
        self._wait(lambda: len(self._Client.instances) == 2 and s.client is None, "the bypass connect is spawning")
        self.assertTrue(self.be.set_mode(self.SID, "default"))
        self._wait(lambda: s._reconnect, "the default pick armed a reconnect after the connect in progress")
        n0 = len(self.lines)
        self.assertTrue(self.be.set_mode(self.SID, "bypassPermissions"))   # the revert, during the same spawn
        self.assertTrue(any("mode (web): set to bypassPermissions; already applying, no new request" in l for l in self.lines[n0:]),
                        self.lines[n0:])
        self._wait(lambda: not s._reconnect, "the redundant arm is disarmed")
        self.assertTrue(any("the re-picked mode leaves the connect in progress launching what this session asks for; "
                            "the reconnect armed after it is disarmed" in l for l in self.lines[n0:]), self.lines[n0:])
        gate.set()
        c2 = self._Client.instances[1]
        self._wait(lambda: c2 is s.client and s._launching is None, "the bypass connect landed")
        time.sleep(0.3)
        self.assertEqual(len(self._Client.instances), 2, "no relaunch of the identical shape")
        self.assertFalse(c2.torn_down); self.assertEqual(c2.modes, [], "nothing owed at the landing")
        self.assertEqual((s._launched_mode, s.perm_mode), ("bypassPermissions", "bypassPermissions"))
        self.assertEqual(sb.read_reg(self.be.state_dir, self.SID).get("mode"), "bypassPermissions")
        self.assertFalse(s._reconnect); self.assertFalse(s._reconnect_when_idle)
        self.be.send(self.SID, "still here")
        self._wait(lambda: c2.writes == ["still here"], "the feeder was woken by the disarm and serves the client")
        self._turn(c2, mode="bypassPermissions")
        self._wait(lambda: s.inflight == 0 and s._settled_msg is not None, "that turn settled")
        # effort: high, max, high during the max spawn (fresh-1's shape); the revert line stays, the arm goes
        self._Client.spawn_gate[2] = gate2 = threading.Event()
        self.addCleanup(gate2.set)
        self.assertTrue(self.be.set_effort(self.SID, "max"))
        self._wait(lambda: len(self._Client.instances) == 3 and s.client is None, "the max connect is spawning")
        self.assertTrue(self.be.set_effort(self.SID, "high"))            # differs from the launching shape: pending
        self._wait(lambda: s._reconnect, "armed after the connect in progress")
        n1 = len(self.lines)
        self.assertTrue(self.be.set_effort(self.SID, "max"))             # the revert to the launching value
        self.assertTrue(any("effort (web): set to max; already applying, no new request" in l for l in self.lines[n1:]), self.lines[n1:])
        self._wait(lambda: not s._reconnect, "disarmed")
        # the high pick's own arm had cleared its surface, so the re-pick withdrew nothing recorded: the settle
        # words it as the re-pick (test_t4 pins the "withdrawn" wording for a surface still recorded)
        self.assertTrue(any("the re-picked effort leaves the connect in progress launching what this session asks for; "
                            "the reconnect armed after it is disarmed" in l for l in self.lines[n1:]), self.lines[n1:])
        gate2.set()
        c3 = self._Client.instances[2]
        self._wait(lambda: c3 is s.client and s._launching is None and s._effort_pending == "", "the max connect landed")
        time.sleep(0.3)
        self.assertEqual(len(self._Client.instances), 3)
        self.assertEqual(s._launched_effort, sb.effort_launch_shape("max")); self.assertEqual(s.effort, "max")
        self.assertEqual(self._applied()[-1], "max")
        # env: {"A": "1"}, {}, {"A": "1"} during the {"A": "1"} spawn
        self._Client.spawn_gate[3] = gate3 = threading.Event()
        self.addCleanup(gate3.set)
        self.assertTrue(self.be.set_env(self.SID, {"A": "1"}))
        self._wait(lambda: len(self._Client.instances) == 4 and s.client is None, "the env connect is spawning")
        self.assertTrue(self.be.set_env(self.SID, {}))
        self._wait(lambda: s._reconnect, "armed after the connect in progress")
        n2 = len(self.lines)
        self.assertTrue(self.be.set_env(self.SID, {"A": "1"}))
        self.assertTrue(any("env (web): per-session env set (A); already applying, no new request" in l for l in self.lines[n2:]), self.lines[n2:])
        self._wait(lambda: not s._reconnect, "disarmed")
        gate3.set()
        c4 = self._Client.instances[3]
        self._wait(lambda: c4 is s.client and s._launching is None, "the env connect landed")
        time.sleep(0.3)
        self.assertEqual(len(self._Client.instances), 4)
        self.assertEqual(s._launched_env, {"A": "1"}); self.assertEqual(s.env_vars, {"A": "1"})


class WorkflowProgressShapeIsLoud(unittest.TestCase):
    """The retirement parser keys on the field names the probe recorded. If the CLI renames them, the
    ever-growing live count comes back — and would come back SILENTLY, so a list this build cannot read is
    reported once per process, naming what arrived (the api_retry shape warning's pattern)."""

    SID = "11111111-2222-3333-4444-888888888888"

    def setUp(self):
        sb.SdkSession._wf_shape_warned = False

    def tearDown(self):
        sb.SdkSession._wf_shape_warned = False

    def _sess(self):
        be = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None, log=lambda m, problem=None: None)
        s = sb.SdkSession(be, {"sid": self.SID, "name": "web", "cwd": "/tmp"})
        s.inflight = 0
        s._on_task_event("task_started", {"task_id": "w1", "task_type": "local_workflow"})
        return s

    def _feed(self, s, progress):
        buf = io.StringIO()
        with redirect_stderr(buf):
            s._on_task_event("task_progress", {"task_id": "w1", "workflow_progress": progress})
        return buf.getvalue()

    def test_a_renamed_list_says_so_once_and_names_what_arrived(self):
        s = self._sess()
        out = self._feed(s, [{"type": "wf_agent", "agent_ref": "a1", "phase": "done"}])
        self.assertIn("workflow_progress payload", out)
        self.assertIn("workflow_agent", out, "the diagnostic names the type it expected")
        self.assertIn("agent_ref", out, "…and the keys it actually got")
        self.assertIn("live subagent count", out, "…and what the user will see go wrong")
        self.assertIn("until the session reconnects", out, "…stated for the worst case: a type/agentId rename "
                                                          "leaves the roster empty, so a run's end retires nothing")
        self.assertEqual(self._feed(s, [{"type": "wf_agent", "agent_ref": "a2"}]), "", "once per process, not per event")

    def test_b_the_probe_recorded_shapes_are_silent(self):
        """Every shape CLI 2.1.257 was seen to ship on an ordinary run must stay silent, or the latch is spent
        on a false alarm and a real rename later in the process goes unreported (review 2026-09-03)."""
        s = self._sess()
        cases = {
            "phases only, before any agent is queued": [
                {"type": "workflow_phase", "index": 0, "title": "Review", "kind": "review"},
                {"type": "workflow_phase", "index": 1, "title": "Verify"}],
            "a log line beside the phases": [
                {"type": "workflow_log", "message": "scanning"}, {"type": "workflow_phase", "index": 0, "title": "Review"}],
            "a queued slot has no agentId yet": [
                {"type": "workflow_agent", "index": 1, "label": "a", "agentId": "a1", "state": "done", "queuedAt": 1, "startedAt": 2},
                {"type": "workflow_agent", "index": 2, "label": "b", "state": "start", "queuedAt": 1},
                {"type": "workflow_phase", "index": 0, "title": "Review"}],
            "a slot blocked before spawn: error, no agentId, no startedAt": [
                {"type": "workflow_agent", "index": 1, "label": "a", "state": "error", "blocked": True,
                 "error": "blocked", "queuedAt": 1, "lastProgressAt": 2}],
            "a slot whose spawn threw: error, no agentId, no startedAt": [
                {"type": "workflow_agent", "index": 1, "label": "a", "state": "error", "error": "spawn failed", "queuedAt": 1}],
        }
        for name, shape in cases.items():
            self.assertEqual(self._feed(s, shape), "", name)
        self.assertFalse(sb.SdkSession._wf_shape_warned)

    def test_c_a_missing_field_is_named(self):
        for entry, word in (({"type": "workflow_agent", "index": 1, "agentId": "a1", "startedAt": 2}, "'state'"),
                            ({"type": "workflow_agent", "agentId": "a1", "state": "done"}, "'index'"),
                            ({"type": "workflow_agent", "index": 1, "state": "done", "startedAt": 2}, "'agentId'"),
                            ({"type": "workflow_step", "index": 1, "agentId": "a1", "state": "done"}, "'workflow_agent'")):
            sb.SdkSession._wf_shape_warned = False
            out = self._feed(self._sess(), [entry])
            self.assertIn(word, out, "the diagnostic names the missing field: %r → %r" % (entry, out))

    def test_d_an_unknown_state_word_is_named(self):
        out = self._feed(self._sess(), [{"type": "workflow_agent", "index": 1, "agentId": "a1", "state": "failed", "startedAt": 2}])
        self.assertIn("failed", out)
        self.assertIn("unknown state word", out)

    def test_e_a_throttled_tick_without_the_list_is_not_a_shape(self):
        s = self._sess()
        buf = io.StringIO()
        with redirect_stderr(buf):
            s._on_task_event("task_progress", {"task_id": "w1"})
            s._on_task_event("task_progress", {"task_id": "w1", "workflow_progress": []})
        self.assertEqual(buf.getvalue(), "")


class SettleBeforePoke(unittest.TestCase):
    """The kernel's parked-op drain wakes on the backend's turn-end poke (2026-09-03) and reads busy() to
    decide whether the session is quiet — so the settle must CLOSE the turn (inflight 0, compaction over)
    before the poke fires, or the woken cycle reads the session as still working and delivery slips to
    the pusher's backstop with every test green. Codex got the same pin in tests/test_codex_backend.py."""

    def test_the_result_branch_settles_before_it_pokes(self):
        import inspect
        src = inspect.getsource(sb.SdkSession._on_message)
        i = src.index("elif isinstance(msg, ResultMessage):")
        zero, comp, poke = (src.index("self.inflight = 0", i), src.index("self._compacting = False", i),
                            src.index("self.backend._poke()", i))
        self.assertLess(zero, poke, "inflight is zeroed before the poke")
        self.assertLess(comp, poke, "…and the compaction cue is cleared before it")

    def test_the_fed_turn_counts_as_in_flight_under_the_pop_lock(self):
        # busy() is inflight>0 or _pending; the input generator pops _pending and must count the turn in
        # flight under the SAME lock, or a drain re-running right after a delivery reads the gap as idle
        src = open(os.path.join(BIN, "romp_sdk_backend.py"), encoding="utf-8").read()
        body = src[src.index("async def inputs():"):src.index("# Reconnect loop:")]   # the generator, up to the
        #   connect loop that follows it (the receive side is SdkSession._drain since 2026-09-06)
        self.assertLess(body.index("self.inflight += 1"), body.index("if item is None:"),
                        "the increment sits inside the lock block that popped the item")
        self.assertLess(body.index("self.inflight += 1"), body.index("self._persist_queue()"),
                        "…before the registry write that used to separate them")


if __name__ == "__main__":
    unittest.main()
