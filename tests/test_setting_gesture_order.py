#!/usr/bin/env python3
"""A kernel setting applies in GESTURE order, not arrival order (2026-08-29).

Federation queues KERNEL_SETTING sends per host while a socket is down and flushes them on
reconnect (ui/webview/federation.ts sendRemote/flushPending) — latest per TYPE, but only per TAB.
A dashboard tab frozen for hours (a backgrounded phone, a throttled browser tab) can therefore
re-dial and deliver a pick the user superseded from another device long ago. The kernel used to
apply whatever arrived, and the judge tiers RE-PROPAGATE what they apply, so one stale flush
walked every linked kernel back to the hours-old pick — and with the mesh then AGREEING, the
gear's mixed-marks disagreement surface showed nothing. The standing rule (CLAUDE.md, cards):
a writer whose evidence predates newer filed state stands down at the write moment.

The mechanism under test (kernel/kernel.py), enforced at the authoritative store so every path
is covered at once — live sends, queue flushes, racing dashboards, propagation legs:
- dashboards stamp every setting gesture with `gt` (epoch ms captured at the click; a queued
  flush carries the ORIGINAL stamp — pinned in ui/webview/federation-send-queue.test.ts),
- each setting's store persists the last-APPLIED stamp beside the value (auto-nudge.json /
  file-editing.json gain a "gt" field; the bare judge-tier stores gain a `<name>.gt` sidecar;
  a store without the field reads as gt 0),
- an arriving stamp older-or-equal to the stored one STANDS DOWN: no apply, no propagation,
  one loud stderr line naming both stamps; a message with NO stamp (older dashboard, direct
  HTTP caller) applies as it always did and records its arrival time.

Synthetic everything: hermetic XDG state, placeholder hosts/tokens, stubbed transport. The WS
handlers fan propagation out on a daemon thread; these tests swap the kernel's `threading`
binding for a delegating namespace whose Thread runs inline, so every fan-out is observed
synchronously and nothing sleeps.
"""
import contextlib
import io
import json
import os
import shutil
import tempfile
import threading as _real_threading
import time
import types
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
km = SourceFileLoader("romp_kernel_gestureorder", os.path.join(BIN, "romp-kernel")).load_module()

T_OLD, T_NEW = 1_700_000_000_000, 1_700_000_360_000   # two gestures six minutes apart


class _InlineThread:
    """Thread stand-in for the WS handlers' propagation fan-out: start() runs the target
    synchronously, so a test sees every propagation call without waiting on a real thread."""

    def __init__(self, target=None, args=(), kwargs=None, daemon=None, name=None):
        self._target, self._args, self._kwargs = target, args, (kwargs or {})

    def start(self):
        if self._target:
            self._target(*self._args, **self._kwargs)


def _inline_threading():
    """A namespace that answers like the real threading module except Thread runs inline.
    Swapped onto km's MODULE GLOBAL only — the stdlib module itself is never touched, so
    nothing outside the kernel module can pick the fake up."""
    ns = types.SimpleNamespace(**{k: getattr(_real_threading, k)
                                  for k in dir(_real_threading) if not k.startswith("_")})
    ns.Thread = _InlineThread
    return ns


class _Base(unittest.TestCase):
    """Fresh STATE per test; the WS handlers' side effects stubbed (nudge tick, tmux, threads,
    the propagation fan-out recorded)."""

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self._saved_state = km.jd.STATE
        km.jd.STATE = Path(self._td)
        km.jd._state_cache.clear()
        km._autonudge_cache.clear()
        self._saved = {n: getattr(km, n) for n in
                       ("_propagate_judge_settings", "_auto_nudge_tick", "_tmux_sessions", "threading")}
        self.propagated = []
        km._propagate_judge_settings = self.propagated.append
        km._auto_nudge_tick = lambda *a, **k: None
        km._tmux_sessions = lambda: {}
        km.threading = _inline_threading()

    def tearDown(self):
        for n, v in self._saved.items():
            setattr(km, n, v)
        km.jd.STATE = self._saved_state
        km.jd._state_cache.clear()
        km._autonudge_cache.clear()
        shutil.rmtree(self._td, ignore_errors=True)

    def dispatch(self, msg):
        """Drive the real WS handler; returns what it wrote to stderr."""
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km.Handler._dispatch_ws(types.SimpleNamespace(), msg, {})
        return err.getvalue()


class GestureOrderAtTheStore(_Base):
    """The setters themselves enforce the ordering, so every caller is covered."""

    def test_a_stale_judge_pick_stands_down_loudly(self):
        self.assertEqual(km._set_judge_model("opus", gt=T_NEW), T_NEW)
        self.assertEqual((km.jd.STATE / "judge-model").read_text(), "opus")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertIsNone(km._set_judge_model("fable", gt=T_OLD), "older stamp must not apply")
        self.assertEqual((km.jd.STATE / "judge-model").read_text(), "opus", "the newer pick stands")
        for needle in ("judge-model", str(T_OLD), str(T_NEW), "stood down"):
            self.assertIn(needle, err.getvalue(), "the stand-down names the setting and both stamps")

    def test_equal_stamps_keep_the_stored_value(self):
        # determinism under identical clocks: equal gt → stand down, never a coin flip
        km._set_judge_model("opus", gt=T_NEW)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertIsNone(km._set_judge_model("fable", gt=T_NEW))
        self.assertEqual((km.jd.STATE / "judge-model").read_text(), "opus")
        self.assertEqual(km._set_judge_model("fable", gt=T_NEW + 1), T_NEW + 1, "any newer stamp applies")
        self.assertEqual((km.jd.STATE / "judge-model").read_text(), "fable")

    def test_auto_nudge_and_file_editing_order_the_same_way(self):
        self.assertEqual(km._set_auto_nudge(False, gt=T_NEW), T_NEW)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertIsNone(km._set_auto_nudge(True, gt=T_OLD))
        km._autonudge_cache.clear()
        self.assertFalse(km._auto_nudge_on(), "the newer OFF survives the stale ON")
        self.assertEqual(km._set_file_editing(True, gt=T_NEW), T_NEW)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertIsNone(km._set_file_editing(False, gt=T_OLD))
        self.assertTrue(km._file_editing_on(), "the newer consent survives the stale revoke")

    def test_an_unstamped_apply_still_arms_the_store_against_stale_flushes(self):
        # compat is one-way on purpose: no gt applies as today (arrival-stamped), and that arrival
        # stamp then outranks any hours-old stamped flush that shows up later
        before = int(time.time() * 1000)
        applied = km._set_judge_model("haiku")
        self.assertIsInstance(applied, int)
        self.assertGreaterEqual(applied, before, "an unstamped apply records its arrival time")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertIsNone(km._set_judge_model("fable", gt=T_OLD))
        self.assertEqual((km.jd.STATE / "judge-model").read_text(), "haiku")

    def test_an_invalid_value_never_writes_a_stamp(self):
        self.assertIsNone(km._set_judge_model("gpt-99", gt=T_NEW), "garbage is refused, stamped or not")
        self.assertFalse((km.jd.STATE / "judge-model").exists())
        self.assertFalse((km.jd.STATE / "judge-model.gt").exists(),
                         "a refused value must not burn its stamp — the store never heard it")


class PreexistingStoresReadAsZero(_Base):
    """File-format compat: every store written before this mechanism has no stamp, and must
    read as gt 0 so the FIRST stamped gesture wins over it."""

    def test_auto_nudge_json_without_the_field(self):
        (km.jd.STATE / "auto-nudge.json").write_text(json.dumps(
            {"enabled": True, "nudged": {"g1": {"count": 1}}}))
        km._autonudge_cache.clear()
        self.assertEqual(km._set_auto_nudge(False, gt=1), 1, "gt 1 beats the absent field's 0")
        d = json.loads((km.jd.STATE / "auto-nudge.json").read_text())
        self.assertFalse(d["enabled"])
        self.assertEqual(d["gt"], 1)
        self.assertEqual(d["nudged"], {"g1": {"count": 1}}, "the ledger the file also carries survives")

    def test_file_editing_json_without_the_field(self):
        (km.jd.STATE / "file-editing.json").write_text(json.dumps({"enabled": True}))
        self.assertEqual(km._set_file_editing(False, gt=1), 1)
        d = json.loads((km.jd.STATE / "file-editing.json").read_text())
        self.assertEqual((d["enabled"], d["gt"]), (False, 1))

    def test_judge_store_without_a_sidecar(self):
        (km.jd.STATE / "judge-model").write_text("opus")
        self.assertEqual(km._judge_state_gt("judge-model"), 0, "no sidecar reads as 0")
        self.assertEqual(km._set_judge_model("fable", gt=1), 1)
        self.assertEqual((km.jd.STATE / "judge-model").read_text(), "fable")


class TheIncidentReplay(_Base):
    """The failure that motivated this, driven through the real WS handler: host X was down when
    the pick queued; the tab froze; a newer pick from another device ran the mesh; hours later the
    old tab re-dialed and flushed the original pick."""

    def test_a_stale_flush_cannot_walk_the_pick_back(self):
        # the newer gesture (from the phone) landed first…
        self.dispatch({"type": "setJudgeModel", "model": "fable", "gt": T_NEW})
        self.assertEqual((km.jd.STATE / "judge-model").read_text(), "fable")
        self.assertEqual(self.propagated, [{"judgeModel": "fable", "gt": T_NEW}],
                         "an applied pick fans out carrying its own gesture stamp")
        # …then the frozen tab woke and flushed the superseded one
        err = self.dispatch({"type": "setJudgeModel", "model": "opus", "gt": T_OLD})
        self.assertEqual((km.jd.STATE / "judge-model").read_text(), "fable", "the store keeps the newer pick")
        self.assertEqual(len(self.propagated), 1,
                         "the stale flush propagates NOTHING — re-propagation is how one flush reverted a mesh")
        for needle in ("judge-model", str(T_OLD), str(T_NEW), "stood down"):
            self.assertIn(needle, err, "the stand-down is loud and names the stale and stored stamps")

    def test_reverse_arrival_order_newest_gesture_wins(self):
        # the race variant: same setting changed from two dashboards during one outage — both
        # flush on recovery and SOCKET order used to decide; gesture order must decide instead
        self.dispatch({"type": "setAutoNudge", "enabled": False, "gt": T_NEW})
        self.dispatch({"type": "setAutoNudge", "enabled": True, "gt": T_OLD})
        km._autonudge_cache.clear()
        self.assertFalse(km._auto_nudge_on(), "the newest gesture wins regardless of arrival order")
        self.dispatch({"type": "setFileEditing", "enabled": True, "gt": T_NEW})
        self.dispatch({"type": "setFileEditing", "enabled": False, "gt": T_OLD})
        self.assertTrue(km._file_editing_on())

    def test_an_unstamped_message_applies_exactly_as_before(self):
        # full compat: an older dashboard, an upstream peer, a direct HTTP caller
        before = int(time.time() * 1000)
        self.dispatch({"type": "setDistillModel", "model": "haiku"})
        self.assertEqual((km.jd.STATE / "distill-model").read_text(), "haiku")
        self.assertEqual(len(self.propagated), 1)
        self.assertEqual(self.propagated[0]["distillModel"], "haiku")
        self.assertGreaterEqual(self.propagated[0]["gt"], before,
                                "the fan-out carries the arrival stamp so receivers stay ordered too")
        # …and an unstamped message even beats a newer STORED stamp: old senders keep working
        self.dispatch({"type": "setDistillModel", "model": "triage"})
        self.assertEqual((km.jd.STATE / "distill-model").read_text(), "triage")


class PropagationCarriesTheStamp(_Base):
    """End to end: the origin's gt rides the /judge-settings leg, so a stale value can never win
    at any receiver by arriving via a second hop."""

    def setUp(self):
        super().setUp()
        km._propagate_judge_settings = self._saved["_propagate_judge_settings"]   # the real fan-out
        self._saved_rkc, self._saved_rem = km._remote_kernel_call, dict(km._remotes)
        km._remotes.clear()
        km._remotes.update({"boxup": {"host": "boxup", "status": "up", "local_port": 1, "token": "t1"}})
        self.calls = []
        km._remote_kernel_call = lambda r, m, p, payload=None, timeout=8: (
            self.calls.append((r["host"], m, p, payload)) or (200, {"ok": True}, None))

    def tearDown(self):
        km._remote_kernel_call = self._saved_rkc
        km._remotes.clear()
        km._remotes.update(self._saved_rem)
        super().tearDown()

    def test_the_forwarded_payload_carries_the_origin_gesture(self):
        self.dispatch({"type": "setJudgeModel", "model": "fable", "gt": T_NEW})
        self.assertEqual(self.calls, [("boxup", "POST", "/judge-settings",
                                       {"judgeModel": "fable", "gt": T_NEW})])

    def test_the_receiving_route_orders_by_the_forwarded_stamp(self):
        # play the RECEIVER: /judge-settings applies through _apply_judge_settings, which must
        # gate each field on the body-level gt — and never re-propagate (the one-hop contract,
        # pinned in test_judge_settings_sync.py)
        res = km._apply_judge_settings({"judgeModel": "fable", "gt": T_NEW})
        self.assertEqual(res["judgeModel"], "fable")
        with contextlib.redirect_stderr(io.StringIO()):
            res = km._apply_judge_settings({"judgeModel": "opus", "gt": T_OLD})
        self.assertEqual(res["judgeModel"], "fable", "the ack shows the newer pick still standing")
        self.assertEqual((km.jd.STATE / "judge-model").read_text(), "fable")
        self.assertEqual(self.calls, [], "a receiver applies without re-propagating")


class WiringPins(unittest.TestCase):
    """Source pins on the two non-judge WS branches (the judge branches' propagation args are
    pinned in test_judge_settings_sync.py): each must hand the message's stamp to its setter —
    a branch that drops it reopens the unconditional-apply hole for that setting."""

    def setUp(self):
        import inspect
        self.src = inspect.getsource(km.Handler._dispatch_ws)

    def test_auto_nudge_branch_gates_on_the_stamp_and_skips_the_tick_on_stand_down(self):
        self.assertIn('_set_auto_nudge(bool(msg["enabled"]), gt=_gesture_ms(msg)) is not None', self.src,
                      "a stood-down toggle must not fire the nudge tick either — no new information")

    def test_file_editing_branch_passes_the_stamp(self):
        self.assertIn('_set_file_editing(bool(msg["enabled"]), gt=_gesture_ms(msg))', self.src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
