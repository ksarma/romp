#!/usr/bin/env python3
"""The bus's live-push (auto-wake on deliver) goes through the kernel (POST /deliver), not a tmux pane-inject
(the user 2026-06-26): drain the maildir, hand the banner to the kernel, and put the mail BACK if the kernel
didn't inject — so the maildir-drain stays the backstop and the bus never shells tmux. Synthetic only.
"""
import os
import tempfile
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
pm = load_source("romp_postal_delivery", os.path.join(BIN, "romp-postal-service"))


class PushThroughKernel(unittest.TestCase):
    def setUp(self):
        self._seam = os.environ.pop("ROMP_SESSIONS_FILE", None)   # not a seam test: let _push actually run
        self.saved = (pm._drain, pm._kernel_post, pm.deliver, pm._push_disabled)
        self.posted, self.redelivered = [], []
        pm._push_disabled = lambda: False
        pm._drain = lambda sid: {"messages": [{"from": "alpha", "from_id": "uuid-a", "body": "hi"}]}
        pm.deliver = lambda sid, frm, frm_id, body, **k: self.redelivered.append((sid, body))

    def tearDown(self):
        if self._seam is not None:
            os.environ["ROMP_SESSIONS_FILE"] = self._seam
        pm._drain, pm._kernel_post, pm.deliver, pm._push_disabled = self.saved

    def test_injected_consumes_and_returns_true(self):
        pm._kernel_post = lambda path, body, timeout=2: (self.posted.append((path, body)),
                                                         {"ok": True, "injected": True})[1]
        self.assertTrue(pm._push("sid-b", {"id": "sid-b", "state": "idle"}))
        self.assertEqual(self.posted[0][0], "/deliver")
        self.assertEqual(self.posted[0][1]["id"], "sid-b")
        self.assertTrue(self.posted[0][1]["text"], "the banner text is handed to the kernel")
        self.assertEqual(self.redelivered, [], "injected → nothing put back")

    def test_not_injected_redelivers_for_the_drain(self):
        pm._kernel_post = lambda path, body, timeout=2: {"ok": True, "injected": False}
        self.assertFalse(pm._push("sid-b", {"id": "sid-b", "state": "idle"}))
        self.assertEqual(self.redelivered, [("sid-b", "hi")], "not injected → mail put back for the drain")

    def test_unreachable_kernel_redelivers(self):
        pm._kernel_post = lambda path, body, timeout=2: None
        self.assertFalse(pm._push("sid-b", {"id": "sid-b", "state": "idle"}))
        self.assertEqual(self.redelivered, [("sid-b", "hi")])

    def test_skips_not_ready_local_without_draining(self):
        pm._kernel_post = lambda *a, **k: self.fail("must not POST for a skipped session")
        pm._drain = lambda sid: self.fail("must not drain a skipped session")
        self.assertFalse(pm._push("sid-b", {"id": "sid-b", "state": "permission"}))
        self.assertEqual(self.redelivered, [])

    def test_remote_agent_is_woken_through_the_kernel(self):
        # A REMOTE (federated) peer has no local 'state' here; _push must still POST /deliver so the local
        # kernel's wake-router forwards it over the host's -L tunnel to the owning kernel. (Regression: the
        # bus used to SKIP remote agents, so an idle remote peer could never be woken cross-machine.)
        self.posted = []
        pm._kernel_post = lambda path, body, timeout=2: (self.posted.append((path, body)),
                                                         {"ok": True, "injected": True})[1]
        self.assertTrue(pm._push("sid-r", {"id": "sid-r", "remote": True}))
        self.assertEqual(self.posted[0][0], "/deliver")
        self.assertEqual(self.posted[0][1]["id"], "sid-r")

    # The bus's /heartbeat handler decides locality from ITS OWN listing (the kernel's GET /sessions,
    # thread rows included) and answers with the bit, so a local session's MCP can stop beating
    # (2026-09-06). The listing is stubbed at _kernel_sessions_checked, the seam every bus-side
    # fetch goes through, so the tests also count fetches.
    LOCAL, THREAD = "local-1", "22222222-3333-4444-5555-666666666666"
    REMOTE = "11111111-2222-3333-4444-555555555555"

    def _listing(self, rows, answered=True):
        self.fetches = []
        pm._kernel_sessions_checked = lambda threads=False: (self.fetches.append(threads), (rows, answered))[1]

    def _with_bus_listing(self, rows, answered=True):
        saved = pm._kernel_sessions_checked
        self._listing(rows, answered)
        pm.HEARTBEATS.clear()
        self.addCleanup(lambda: (setattr(pm, "_kernel_sessions_checked", saved), pm.HEARTBEATS.clear()))

    def test_heartbeat_records_remote_but_ignores_local(self):
        # Only sids the local kernel does NOT own get remote-presence; a local session is already visible via
        # /sessions and must not linger as a phantom [remote] after it dies.
        self._with_bus_listing([{"id": self.LOCAL, "name": "mysess"}])
        self.assertFalse(pm._record_heartbeat(self.REMOTE, "remotetest"), "not local → recorded, answer False")
        self.assertTrue(pm._record_heartbeat(self.LOCAL, "mysess"), "local → ignored, answer True")
        self.assertIn(self.REMOTE, pm.HEARTBEATS)
        self.assertNotIn(self.LOCAL, pm.HEARTBEATS)
        self.assertEqual(self.fetches, [True, True], "one listing fetch per beat, thread rows included")

    def test_heartbeat_unanswered_listing_is_not_local(self):
        # A kernel mid-restart leaves the listing UNANSWERED: the bus must not tell anyone it is local
        # (a remote session that heard that would stop beating for good), and it records the beat
        # exactly as before, so presence survives the restart the way it always did.
        # The rows are NON-empty and hold the sid on purpose: only the answered bit can make this
        # False, so dropping the `answered and` guard fails here (the seam never returns rows with
        # answered=False today; the guard is the docstring's promise, and this is its test).
        self._with_bus_listing([{"id": self.LOCAL, "name": "mysess"}], answered=False)
        self.assertFalse(pm._record_heartbeat(self.LOCAL, "mysess"),
                         "the sid is in the rows, but the rows did not ANSWER: never local")
        self.assertIn(self.LOCAL, pm.HEARTBEATS, "an unanswered listing records the beat, as before")

    def test_heartbeat_from_a_thread_row_is_local(self):
        # A comment thread heartbeats under its own row; the default listing hides thread rows, so the
        # handler asks for them or it would file every live thread as a phantom remote peer.
        self._with_bus_listing([{"id": self.LOCAL, "name": "mysess"},
                                {"id": self.THREAD, "name": "mysess-t1", "thread": True, "parent": self.LOCAL}])
        self.assertTrue(pm._record_heartbeat(self.THREAD, "mysess-t1"))
        self.assertNotIn(self.THREAD, pm.HEARTBEATS)
        self.assertEqual(self.fetches, [True], "the handler asks for thread rows")

    def test_heartbeat_route_answers_the_locality_bit(self):
        # The wire contract the MCP loop reads: {ok, local}. Pinned in source so an edit that drops
        # the bit fails here, not as a remote session that never stops beating.
        src = open(os.path.join(BIN, "romp-postal-service"), encoding="utf-8").read()
        self.assertIn('local = _record_heartbeat(data.get("id"), data.get("name", "?"))', src)
        self.assertIn('return self._send({"ok": True, "local": local})', src)

    def test_source_uses_the_kernel_deliver_not_a_tmux_inject(self):
        src = open(os.path.join(BIN, "romp-postal-service"), encoding="utf-8").read()
        self.assertIn('_kernel_post("/deliver"', src, "the live-push wakes via the kernel")
        self.assertNotIn("paste-buffer", src, "no tmux pane-inject remains in the bus")
        self.assertNotIn("capture-pane", src, "no tmux pane-capture remains in the bus")


if __name__ == "__main__":
    unittest.main()
