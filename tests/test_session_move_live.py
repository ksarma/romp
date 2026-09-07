#!/usr/bin/env python3
"""LIVE integration test for the session move (the user 2026-09-01): the CLI's `set_cwd` control
request, driven through the real Claude Agent SDK against a real `claude`, in a HERMETIC config dir
(CLAUDE_CONFIG_DIR under a temp path — the recipe the 2026-09-02 investigation verified the response
shape with). It proves the facts SdkBackend.move is built on: the `ok {cwd, changed,
transcript_relocated}` arm, the messages that follow with no query sent (init with the new cwd, the
turn-less ResultMessage), `changed: false` on a same-dir request, `rejected not_found`, and that the
transcript ends up under the NEW project slug ONLY — never copied — while the conversation (a codeword
planted before the move) is still remembered after it.

OPT-IN, and skipped otherwise: it bills two short model turns and reaches a real CLI, which the test
suite's floors (conftest's ROMP_CLAUDE_BIN=/bin/false) exist to prevent by default. Runs only when
  * ROMP_MOVE_LIVE=1,
  * an interpreter with claude_agent_sdk is available — this one, $ROMP_SDK_PYTHON, or the kernel's own
    SDK venv (~/.local/state/romp/sdkvenv, what bin/romp-sdk-setup builds) — the child runs there, so the
    suite's interpreter needs no SDK,
  * a `claude` binary ($ROMP_MOVE_LIVE_CLAUDE, else PATH), and
  * Claude Code auth the hermetic config dir can use: ANTHROPIC_API_KEY in the environment; or
    $ROMP_MOVE_LIVE_API_KEY_HELPER — a shell command that prints a key, written into the hermetic
    settings as their apiKeyHelper; or, failing both, the `apiKeyHelper` from the user's OWN Claude
    Code settings ($CLAUDE_CONFIG_DIR/settings.json, default ~/.claude/settings.json), copied into
    the hermetic settings as-is (the hermetic dir sees none of the operator's own settings otherwise).
    Either way the helper COMMAND travels, never a key, and no key is ever written to a file (the
    2026-09-05 rule: keys live only in the vault and in process environment; the ~/.config key cache
    this test once read no longer exists).
CI has none of these and skips cleanly. Synthetic content throughout (an invented sid, an invented
codeword, temp folders)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from romp_load import load_source
from types import SimpleNamespace

SID = "aaaaaaaa-1111-4222-8333-444444444444"
CODEWORD = "PLUM-FORTY-TWO"

# Hermetic state BEFORE the load below: the state-isolation ratchet (tests/test_state_isolation_order.py)
# counts every in-process load as state-touching, and only pytest runs conftest's floor. The module
# loaded here reads no state; the two lines are the ratchet's price and change nothing for the child
# (its config dir is the hermetic CLAUDE_CONFIG_DIR, and the SDK venv is found under HOME).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor

# The child below runs the user's own apiKeyHelper and a real CLI, so its stdout and stderr can carry
# a credential (a helper that echoes, a CLI that prints its headers on a failure). What a failure
# renders of them is scrubbed with the suite's credential-shaped token list first (the same list
# tests/conftest.py's report hook applies, loaded by path so this file also works outside pytest),
# and capped: the last CHILD_OUTPUT_CAP characters of each stream.
_cp = load_source("romp_tests_credential_patterns_live", os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                                        "credential_patterns.py"))
CHILD_OUTPUT_CAP = 1500


def _child_output(r):
    """The text a failed run shows of the child's two streams: scrubbed, then the tail of each."""
    return "child failed:\n%s\n%s" % (_cp.scrub(r.stdout or "")[-CHILD_OUTPUT_CAP:],
                                        _cp.scrub(r.stderr or "")[-CHILD_OUTPUT_CAP:])

CHILD = r'''
import asyncio, glob, json, os, sys
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
CFG, A, B, CLI, SID, CODEWORD, SETTINGS = sys.argv[1:8]

def desc(m):
    t = type(m).__name__
    if t == "ResultMessage":
        return {"type": t, "num_turns": m.num_turns, "result": (m.result or "")[:400], "is_error": m.is_error}
    if t == "SystemMessage":
        return {"type": t, "subtype": m.subtype, "cwd": (m.data or {}).get("cwd")}
    if t == "AssistantMessage":
        return {"type": t, "text": " ".join(getattr(b, "text", "") for b in m.content)[:400]}
    return {"type": t}

async def drain(c, secs):
    out = []
    async def rd():
        async for m in c.receive_messages():
            out.append(desc(m))
    try:
        await asyncio.wait_for(rd(), timeout=secs)
    except asyncio.TimeoutError:
        pass
    return out

async def main():
    res = {}
    opts = ClaudeAgentOptions(cwd=A, cli_path=CLI, settings=SETTINGS, env={"CLAUDE_CONFIG_DIR": CFG},
                              setting_sources=["user", "project"],
                              system_prompt={"type": "preset", "preset": "claude_code"},
                              extra_args={"session-id": SID})
    async with ClaudeSDKClient(opts) as c:
        q = c._query
        res["has_sender"] = callable(getattr(q, "_send_control_request", None))
        await c.query("The codeword for this project is %s. Reply with just OK." % CODEWORD)
        async for m in c.receive_response():
            pass
        r = await q._send_control_request({"subtype": "set_cwd", "path": B})
        if r.get("status") == "needs_trust":
            res["needs_trust"] = r
            r = await q._send_control_request({"subtype": "set_cwd", "path": B, "trust_accepted": True,
                                               "trusted_directory": r.get("directory") or B})
        res["move"] = r
        res["after_move"] = await drain(c, 6)
        res["same_dir"] = await q._send_control_request({"subtype": "set_cwd", "path": B})
        res["missing"] = await q._send_control_request({"subtype": "set_cwd", "path": B + "/does-not-exist"})
        await c.query("Without running any tools, answer in one line: what is the codeword?")
        reply = ""
        async for m in c.receive_response():
            d = desc(m)
            if d["type"] == "ResultMessage":
                reply = d["result"]
        res["reply"] = reply
    res["files"] = sorted(os.path.relpath(p, os.path.join(CFG, "projects"))
                          for p in glob.glob(os.path.join(CFG, "projects", "*", "*.jsonl")))
    print(json.dumps(res))

asyncio.run(main())
'''


def _sdk_python():
    for cand in (sys.executable, os.environ.get("ROMP_SDK_PYTHON") or "",
                 os.path.expanduser("~/.local/state/romp/sdkvenv/bin/python")):
        if cand and os.path.exists(cand):
            r = subprocess.run([cand, "-c", "import claude_agent_sdk"], capture_output=True)
            if r.returncode == 0:
                return cand
    return ""


def _user_api_key_helper(config_dir=None):
    """The `apiKeyHelper` command from the user's own Claude Code settings ("" when there is none): the
    hermetic config dir borrows the COMMAND, so the child authenticates exactly the way the user's real
    sessions do. Never a key — keys live in the vault and in process environment only, and this test
    writes none to disk. `config_dir` defaults to the user's real config dir: under pytest the suite's
    conftest floors $CLAUDE_CONFIG_DIR to an empty dir and saves the real location in
    $ROMP_TESTS_REAL_CLAUDE_CONFIG_DIR, so that is read first; else $CLAUDE_CONFIG_DIR, else ~/.claude."""
    d = (config_dir or os.environ.get("ROMP_TESTS_REAL_CLAUDE_CONFIG_DIR") or os.environ.get("CLAUDE_CONFIG_DIR")
         or os.path.expanduser("~/.claude"))
    try:
        with open(os.path.join(d, "settings.json")) as f:
            v = json.load(f).get("apiKeyHelper")
    except (OSError, ValueError, AttributeError):
        return ""
    return v.strip() if isinstance(v, str) else ""


def _api_key_helper():
    """The apiKeyHelper command the hermetic settings get when ANTHROPIC_API_KEY is unset: the explicit
    $ROMP_MOVE_LIVE_API_KEY_HELPER first, else the command borrowed from the user's own settings."""
    return os.environ.get("ROMP_MOVE_LIVE_API_KEY_HELPER") or _user_api_key_helper()


def _skip_reason():
    if os.environ.get("ROMP_MOVE_LIVE") != "1":
        return "live move test is opt-in (ROMP_MOVE_LIVE=1): it bills two model turns against a real CLI"
    if not _sdk_python():
        return "no interpreter with claude_agent_sdk (this one, $ROMP_SDK_PYTHON, or ~/.local/state/romp/sdkvenv)"
    if not (os.environ.get("ROMP_MOVE_LIVE_CLAUDE") or shutil.which("claude")):
        return "no `claude` binary ($ROMP_MOVE_LIVE_CLAUDE or PATH)"
    if not (os.environ.get("ANTHROPIC_API_KEY") or _api_key_helper()):
        return ("no Claude Code auth for a hermetic config dir (ANTHROPIC_API_KEY in the environment, "
                "ROMP_MOVE_LIVE_API_KEY_HELPER, or an apiKeyHelper in your Claude Code settings)")
    return ""


class UserApiKeyHelper(unittest.TestCase):
    """The lookup the live test's hermetic settings borrow their apiKeyHelper from: the command string
    when the user's settings name one; "" for a missing dir, unreadable JSON, or settings without the
    key — never a default that reads a key file (the 2026-09-05 rule: no key on disk anywhere)."""

    def test_returns_the_configured_command(self):
        td = tempfile.mkdtemp(prefix="romp-move-live-cfg-")
        try:
            with open(os.path.join(td, "settings.json"), "w") as f:
                json.dump({"apiKeyHelper": " /opt/example/helper --print "}, f)
            self.assertEqual(_user_api_key_helper(td), "/opt/example/helper --print")
        finally:
            shutil.rmtree(td, ignore_errors=True)

    def test_empty_without_a_helper(self):
        td = tempfile.mkdtemp(prefix="romp-move-live-cfg-")
        try:
            self.assertEqual(_user_api_key_helper(os.path.join(td, "absent")), "")
            with open(os.path.join(td, "settings.json"), "w") as f:
                f.write("{not json")
            self.assertEqual(_user_api_key_helper(td), "")
            with open(os.path.join(td, "settings.json"), "w") as f:
                json.dump({"permissions": {"defaultMode": "default"}, "apiKeyHelper": 7}, f)
            self.assertEqual(_user_api_key_helper(td), "")
            with open(os.path.join(td, "settings.json"), "w") as f:
                json.dump(["not", "an", "object"], f)
            self.assertEqual(_user_api_key_helper(td), "")
        finally:
            shutil.rmtree(td, ignore_errors=True)


class ChildOutputScrub(unittest.TestCase):
    """What a failed live run renders of the child's output: credential-shaped tokens scrubbed (the
    child ran the user's real apiKeyHelper), each stream capped. Not opt-in: this runs everywhere."""

    def test_a_fabricated_token_is_scrubbed_and_each_stream_is_capped(self):
        tok = "sk-" + "ant-" + "api03-" + uuid.uuid4().hex + uuid.uuid4().hex        # assembled, never a literal
        out = "starting\n" + "x" * 3000 + "\nkey=" + tok + "\n"
        err = "y" * 2000 + "\nAuthorization: Bearer " + tok
        text = _child_output(SimpleNamespace(stdout=out, stderr=err))
        self.assertFalse(tok in text, "the token is gone from both streams")
        self.assertEqual(text.count(_cp.REDACTED), 2)
        self.assertTrue(text.startswith("child failed:\n"))
        self.assertLessEqual(len(text), len("child failed:\n\n") + 2 * CHILD_OUTPUT_CAP)
        self.assertEqual(CHILD_OUTPUT_CAP, 1500)
        self.assertFalse("starting" in text, "the head of a long stream is what the cap drops")
        self.assertTrue(text.endswith("Bearer " + _cp.REDACTED), "the tail of stderr is what is kept")
        # scrubbed BEFORE the cut: a token straddling the cut can leave no half of itself behind
        text = _child_output(SimpleNamespace(stdout="z" * (CHILD_OUTPUT_CAP - 10) + "key=" + tok, stderr=""))
        self.assertFalse(tok[-20:] in text)
        self.assertTrue(_cp.REDACTED in text)
        # ordinary text stays: the codeword, a path, a fingerprint, an empty stream
        plain = _child_output(SimpleNamespace(stdout="the codeword is %s at /tmp/romp-move-live-x/a\nsha256:1a2b3c1a2b3c" % CODEWORD,
                                              stderr=None))
        self.assertEqual(plain, "child failed:\nthe codeword is %s at /tmp/romp-move-live-x/a\nsha256:1a2b3c1a2b3c\n" % CODEWORD)


@unittest.skipIf(_skip_reason(), _skip_reason())
class LiveSetCwd(unittest.TestCase):
    def test_set_cwd_relocates_and_the_conversation_survives(self):
        td = tempfile.mkdtemp(prefix="romp-move-live-")
        try:
            cfg, a, b = (os.path.join(td, d) for d in ("cfg", "a", "b"))
            for d in (cfg, a, b):
                os.makedirs(d)
            settings = {"permissions": {"defaultMode": "default"}}
            env = dict(os.environ)
            env.pop("ROMP_CLAUDE_BIN", None)
            if not env.get("ANTHROPIC_API_KEY"):
                settings["apiKeyHelper"] = _api_key_helper()
            spath = os.path.join(cfg, "settings.json")
            with open(spath, "w") as f:
                json.dump(settings, f)
            cli = os.environ.get("ROMP_MOVE_LIVE_CLAUDE") or shutil.which("claude")
            child = os.path.join(td, "child.py")
            with open(child, "w") as f:
                f.write(CHILD)
            r = subprocess.run([_sdk_python(), child, cfg, a, b, cli, SID, CODEWORD, spath],
                               capture_output=True, text=True, timeout=300, env=env, cwd=td)
            self.assertEqual(r.returncode, 0, _child_output(r))
            res = json.loads(r.stdout.strip().splitlines()[-1])
            self.assertTrue(res["has_sender"], "the SDK still exposes _send_control_request")
            mv = res["move"]
            self.assertEqual(mv.get("status"), "ok", mv)
            self.assertEqual(mv.get("cwd"), os.path.realpath(b))
            self.assertIs(mv.get("changed"), True)
            self.assertIs(mv.get("transcript_relocated"), True)
            kinds = [(m["type"], m.get("subtype"), m.get("cwd"), m.get("num_turns")) for m in res["after_move"]]
            self.assertIn(("SystemMessage", "init", os.path.realpath(b), None), kinds,
                          "the CLI announces the new cwd with no query sent")
            self.assertIn(("ResultMessage", None, None, 0), kinds, "…followed by the turn-less result")
            self.assertEqual(res["same_dir"].get("status"), "ok")
            self.assertIs(res["same_dir"].get("changed"), False)
            self.assertEqual((res["missing"].get("status"), res["missing"].get("reason")), ("rejected", "not_found"))
            self.assertIn(CODEWORD, res["reply"], "the conversation is remembered after the move")
            slug_b = "-".join(part for part in os.path.realpath(b).split("/") if part)
            self.assertEqual(res["files"], [os.path.join("-" + slug_b, SID + ".jsonl")],
                             "the transcript lives under the NEW slug only — moved, never copied")
        finally:
            shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
