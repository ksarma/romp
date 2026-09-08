#!/usr/bin/env python3
"""Anonymous mail is refused at the door, and legacy "unknown" mail never renders the mint.

A sender that failed to resolve its own identity used to mail anyway: the bus minted a message
literally "from unknown" (empty from_id), and the recipient's injected banner printed that word
raw — a canned-sounding body over a ghost sender, met by the user on their laptop 2026-08-18
("a greeting from an unknown thread"; the 2026-07-27 clear-fork minted the same ghost). Three
seams now hold, all pinned here:
  - the bus /send handler REFUSES a from_id-less send with an error naming the sender's own
    identity resolution as the breakage (fail loudly, 2026-07-03);
  - the MCP/CLI sender paths say the same thing BEFORE posting, with the actionable half;
  - the banner formatters never print the literal "unknown"/"?" for mail already on disk or
    arriving from an older peer bus — "an unidentified session" is what is true.
"""
import json
import os
import tempfile
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
ps = load_source("romp_postal_sender_identity",
                      os.path.join(BIN, "romp-postal-service"))


class FromDisplay(unittest.TestCase):
    def test_minted_ghosts_render_as_unidentified(self):
        for ghost in ("unknown", "Unknown", "?", "", None):
            self.assertEqual(ps._from_disp({"from": ghost}), "an unidentified session")

    def test_real_names_pass_through(self):
        self.assertEqual(ps._from_disp({"from": "web"}), "web")
        self.assertEqual(ps._from_disp({"from": "TESTHOST:api"}), "TESTHOST:api")

    def test_push_banner_uses_the_guard(self):
        out = ps.format_push([{"from": "unknown", "date": "", "body": "How's it going?",
                               "id": "m1", "kind": ""}])
        self.assertIn("from an unidentified session", out)
        self.assertNotIn("from unknown", out)

    def test_inbox_banner_uses_the_guard(self):
        out = ps.format_inbox([{"from": "?", "date": "", "body": "checking in",
                                "id": "m2", "kind": ""}], me_id="abc")
        self.assertIn("from an unidentified session", out)
        self.assertNotIn("from ?", out)


class SendRefusal(unittest.TestCase):
    def test_handler_source_refuses_fromless_sends(self):
        # the handler is route-bound (an HTTP class method); pin the guard at source the way
        # the UI pins render branches — the bats drive the live route
        src = open(os.path.join(BIN, "romp-postal-service")).read()
        self.assertIn('if not frm_id:', src)
        self.assertIn("sender identity required", src)

    def test_mcp_and_cli_guards_precede_the_post(self):
        src = open(os.path.join(BIN, "romp-postal-service")).read()
        self.assertIn("identity did not resolve", src, "the MCP surface guards (always in-session)")
        self.assertIn("pass --from <label>", src,
                      "the CLI surface guards AND names the non-session door (2026-08-19: the "
                      "refusal broke launchd scripts that had been mailing as 'unknown')")
        self.assertIn('mid = frm_label, "ext:" + frm_label', src,
                      "--from mails placeable under a stable synthetic id, never anonymously")


class McpSendWithoutIdentity(unittest.TestCase):
    """The MCP send tool, driven with NO session identity: CLAUDE_CODE_SESSION_ID is absent, so the
    real _self_identity resolves to (None, None), the way it does on a runner with no session around
    it (CI). Two answers are pinned, in this order. A malformed request is refused for its SHAPE, the
    field named, before the identity is consulted, and the bus is not dialed; with the identity check
    first (2026-09-08), a string `tracked` from an unresolved session was answered with the identity
    refusal, so what the caller heard depended on the environment rather than on the request. A
    well-formed request from an unresolved session still gets the identity refusal, unchanged, and the
    bus is not dialed either. Nothing here asserts on os.environ itself (tests/README.md: a failing
    assertion over the environment mapping would print it)."""

    def setUp(self):
        self._env = os.environ.pop("CLAUDE_CODE_SESSION_ID", None)
        self._saved = (ps._http, ps._heartbeat)
        self.dialed = []

        def http(*a, **k):
            self.dialed.append(a)
            raise ps.BusError("stubbed: the bus is not dialed here")
        ps._http, ps._heartbeat = http, (lambda mid, me: None)
        self.assertEqual(ps._self_identity(), (None, None), "the rig's premise: no identity resolves")

    def tearDown(self):
        ps._http, ps._heartbeat = self._saved
        if self._env is not None:
            os.environ["CLAUDE_CODE_SESSION_ID"] = self._env

    def _send(self, **extra):
        args = {"to": "api", "body": "hello", "kind": "delegate"}
        args.update(extra)
        return ps._mcp_call("send_message", args)

    def test_a_string_tracked_is_a_shape_refusal_even_with_no_identity(self):
        for bad in ("false", "true", 1, "yes"):
            text, is_err = self._send(tracked=bad)
            self.assertTrue(is_err, (bad, text))
            self.assertIn("'tracked' must be true or false, got %s" % json.dumps(bad), text)
            self.assertNotIn("identity did not resolve", text,
                             "the field's refusal, not the session's: the request is what is wrong")
        self.assertEqual(self.dialed, [], "the bus is never dialed with a malformed flag")

    def test_a_well_formed_send_with_no_identity_gets_the_identity_refusal(self):
        for extra in ({}, {"tracked": True}, {"tracked": False}, {"tracked": None}):
            text, is_err = self._send(**extra)
            self.assertTrue(is_err, (extra, text))
            self.assertIn("this session's own identity did not resolve (no session id)", text, extra)
            self.assertIn("worth surfacing to the user", text, "the actionable half is kept")
        self.assertEqual(self.dialed, [], "anonymous mail is refused before the post, not by the bus")

    def test_the_to_body_and_kind_checks_still_come_first(self):
        # the shape checks upstream's contract puts first stay ahead of both: a request missing its
        # parts is told so, not blamed on its sender
        text, is_err = ps._mcp_call("send_message", {"to": "api", "kind": "delegate", "tracked": "false"})
        self.assertEqual((text, is_err), ("Need both 'to' and 'body'.", True))
        text, is_err = ps._mcp_call("send_message", {"to": "api", "body": "hello", "kind": "fyi", "tracked": "false"})
        self.assertTrue(is_err)
        self.assertIn("Need 'kind'", text)
        self.assertEqual(self.dialed, [])


if __name__ == "__main__":
    unittest.main()
