#!/usr/bin/env python3
"""Cancelling the "Opening…" cue (the ✕/Esc/backdrop → cancelCreate) tears down the pending session.

The user 2026-07-14: a new-session spawn sometimes fails and the modal hung on the 30s backstop, so the
cue got an abort. The webview knows only the session NAME, so the kernel resolves it to a live session and
ends it — a slow-but-successful open must not leave an orphan tab. If the session hasn't materialized yet,
the name is armed in _cancel_pending so the in-flight threaded tmux spawn is reaped the moment it lands.
A remote cue ("host:name") is dismissed client-side only; the local kernel reaps nothing.

HISTORY GUARD (the user 2026-07-16, the staged-demo teardowns): names are not identities — same-named
generations coexist, so the cancel's name lookup can resolve to an ESTABLISHED conversation instead of
the just-opened spawn, and the kill+hide erased staged work with no trace. A session whose transcript
holds a user record refuses the teardown loudly; only a never-prompted session is torn down.

Synthetic only: placeholder UUID, hostname TESTHOST, hermetic temp STATE.
"""
import os
import tempfile
import types
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_cancelcreate", os.path.join(BIN, "romp-kernel"))

SID = "11111111-2222-3333-4444-555555555555"
NAME = "TESTHOST-newsess"


class FakeBackend:
    """kill() lands for REAL: the sid leaves the test's live map, the way a real kill leaves the
    liveness owner's answer — which is the corroboration the closed broadcast now rides on
    (2026-08-18). The refusal tests below break kill deliberately."""

    def __init__(self, tc):
        self.tc = tc
        self.killed = []

    def kill(self, sid):
        self.killed.append(sid)
        self.tc._live.pop(sid, None)


class CancelCreateTest(unittest.TestCase):
    def setUp(self):
        self._live = {}       # sid -> meta; drives the monkeypatched name lookup + liveness reads
        self.be = FakeBackend(self)
        self.sent = []        # (app, msg) handed to the chat view
        self._saved = {}

        def patch(nm, fn):
            self._saved[nm] = getattr(km, nm)
            setattr(km, nm, fn)

        patch("_send_to_app", lambda app, m: self.sent.append((app, m)))
        patch("_push_soon", lambda: None)
        patch("_push_all", lambda: None)
        patch("_tmux_sessions", lambda: self._live)
        patch("_live_names", lambda tmux: {NAME: SID} if SID in (tmux or {}) else {})
        self._saved_bf = km.Sessions.backend_for
        km.Sessions.backend_for = staticmethod(lambda sid: self.be)
        km._cancel_pending.clear()
        # _confirmed_ended's second leg: the probe mirrors the live map by default (a landed kill
        # reads as the authoritative zero; a survivor stays listed). The stall tests override it.
        km._TMUX.available = lambda: True
        km._TMUX.alive_sids = lambda t=3: set(self._live)

    def tearDown(self):
        for nm, v in self._saved.items():
            setattr(km, nm, v)
        km.Sessions.backend_for = self._saved_bf
        km._cancel_pending.clear()
        for nm in ("available", "alive_sids"):
            km._TMUX.__dict__.pop(nm, None)

    def _cancel(self, name):
        # Drive the real WS handler: _dispatch_ws starts with `if _drive(...)` which returns False for
        # cancelCreate before touching a backend, so a dummy self / empty client is safe.
        km.Handler._dispatch_ws(types.SimpleNamespace(), {"type": "cancelCreate", "name": name}, {})

    def test_live_session_is_ended(self):
        self._live = {SID: {}}                                 # the session already materialized
        self._cancel(NAME)
        self.assertEqual(self.be.killed, [SID], "the live pending session is killed on its backend")
        self.assertTrue(any(m.get("type") == "closed" and m.get("id") == SID for _a, m in self.sent),
                        "the live view is told to prune it (no tab-hide state anymore — the kill is the event)")
        self.assertNotIn(NAME, km._cancel_pending, "a resolved cancel never arms the pending set")

    def test_not_yet_live_arms_then_reaped_on_arrival(self):
        self._live = {}                                        # spawn still in flight — no session yet
        self._cancel(NAME)
        self.assertEqual(self.be.killed, [], "nothing to kill yet")
        self.assertIn(NAME, km._cancel_pending, "armed so the arriving spawn is reaped")
        self._live = {SID: {}}                                 # ...the spawn lands
        km._reap_if_cancelled(NAME)
        self.assertEqual(self.be.killed, [SID], "reaped on arrival")
        self.assertNotIn(NAME, km._cancel_pending, "and cleared from the pending set")

    def test_reap_is_a_noop_for_an_uncancelled_name(self):
        self._live = {SID: {}}
        km._reap_if_cancelled(NAME)                            # a normal (uncancelled) spawn lands
        self.assertEqual(self.be.killed, [], "an uncancelled arrival is left alone")

    def test_remote_cue_is_not_reaped_locally(self):
        self._live = {SID: {}}
        self._cancel("TESTHOST:" + NAME)                          # host-prefixed cue
        self.assertEqual(self.be.killed, [], "a remote spawn is not torn down by the local kernel")
        self.assertNotIn(NAME, km._cancel_pending)
        self.assertNotIn("TESTHOST:" + NAME, km._cancel_pending)

    # ── the closed broadcast is corroborated (2026-08-18) ──

    def test_a_kill_that_throws_does_not_broadcast_closed(self):
        # The throw was already caught and logged — and then `closed` went out anyway, dismissing a
        # session the kernel KEEPS LISTING on every chat client: the next push re-listed it with no
        # session behind it — the permanent dead-swirl seam. A failed kill's honest signal is a warn.
        self._live = {SID: {}}

        def boom(sid):
            self.be.killed.append(sid)
            raise RuntimeError("backend refused the kill")

        self.be.kill = boom
        self._cancel(NAME)
        self.assertFalse(any(m.get("type") == "closed" for _a, m in self.sent),
                         "nothing closed → no closed broadcast")
        self.assertTrue(any(m.get("type") == "warn" for _a, m in self.sent),
                        "…a warn instead, so the cancel's failure is loud, not a silent lie")

    def test_a_kill_that_silently_fails_warns_instead_of_dismissing(self):
        # tmux's kill primitive is fire-and-forget: a timeout is swallowed and kill() returns as if
        # it worked. Corroborate with the liveness owner instead of trusting the call.
        self._live = {SID: {}}
        self.be.kill = lambda sid: self.be.killed.append(sid)   # runs, but the session survives
        self._cancel(NAME)
        self.assertFalse(any(m.get("type") == "closed" for _a, m in self.sent))
        self.assertTrue(any(m.get("type") == "warn" for _a, m in self.sent))

    def test_a_collapsed_read_with_a_failed_probe_stands_down(self):
        # The corroboration must not inherit list_lines' error→[] collapse (2026-08-18): a wedged
        # tmux server swallows the kill AND empties the merged read in one gesture, so the old
        # membership gate read the survivor as dead-confirmed and broadcast the closed lie anyway.
        # A failed probe is not a death: warn, no closed. (Red before _confirmed_ended, green after.)
        import contextlib
        import io
        self._live = {}                                          # the merged read COLLAPSED to empty
        km._TMUX.alive_sids = lambda t=3: None                   # …and the probe failed with it
        self.be.kill = lambda sid: self.be.killed.append(sid)    # fires, never lands
        with contextlib.redirect_stderr(io.StringIO()):
            km._end_pending_sid(SID)
        self.assertFalse(any(m.get("type") == "closed" for _a, m in self.sent),
                         "silence is not a death — no dismissal on every client from a stalled read")
        self.assertTrue(any(m.get("type") == "warn" for _a, m in self.sent))

    def test_a_collapsed_read_with_an_authoritative_zero_still_prunes(self):
        # the probe ANSWERING zero is a real death even while the richer list read is collapsed —
        # the prune must not stall behind the stand-down rule
        import contextlib
        import io
        self._live = {}
        km._TMUX.alive_sids = lambda t=3: set()
        with contextlib.redirect_stderr(io.StringIO()):
            km._end_pending_sid(SID)
        self.assertTrue(any(m.get("type") == "closed" and m.get("id") == SID for _a, m in self.sent))
        self.assertFalse(any(m.get("type") == "warn" for _a, m in self.sent))

    # ── the history guard (the user 2026-07-16) ──

    def _transcript(self, records):
        import json
        p = os.path.join(tempfile.mkdtemp(), SID + ".jsonl")
        with open(p, "w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
        return p

    def test_an_established_conversation_refuses_the_teardown(self):
        # the demo shape: a staged session wearing a REUSED name; the cancelled cue's lookup lands on it
        path = self._transcript([
            {"type": "system", "subtype": "init"},
            {"type": "user", "uuid": "u1", "message": {"role": "user", "content": "stage the demo board"}},
            {"type": "assistant", "uuid": "a1"}])
        self._saved["_path_of"] = km._path_of
        km._path_of = lambda sid: path
        self._live = {SID: {}}
        self._cancel(NAME)
        self.assertEqual(self.be.killed, [], "a session with a human turn is work, never a pending spawn")
        self.assertEqual(self.sent, [], "and the live view is not told to prune it")

    def test_a_fresh_spawn_with_only_init_lines_is_still_torn_down(self):
        path = self._transcript([{"type": "system", "subtype": "init"}])
        self._saved["_path_of"] = km._path_of
        km._path_of = lambda sid: path
        self._live = {SID: {}}
        self._cancel(NAME)
        self.assertEqual(self.be.killed, [SID], "only system/init lines → a genuine pending spawn")

    def test_an_unreadable_transcript_fails_toward_refusing(self):
        self._saved["_path_of"] = km._path_of
        km._path_of = lambda sid: (_ for _ in ()).throw(OSError("boom"))
        self._live = {SID: {}}
        self._cancel(NAME)
        self.assertEqual(self.be.killed, [], "can't prove it's fresh → don't kill it")


if __name__ == "__main__":
    unittest.main()
