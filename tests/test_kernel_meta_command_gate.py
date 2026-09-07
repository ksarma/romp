#!/usr/bin/env python3
"""_route_meta_command evaluates the drive-op gate (_ops_gate) exactly as often as the setter it calls
does, and never on its own account: /effort and /fast take _gate_or_park (ONE evaluation, outside the
queue lock, then the locked queue-presence check); /model takes _set_model_or_park's own rule (no
_ops_gate at all). Upstream's #923 line re-read _ops_gate AFTER the setter to answer POST /send's
`queued`: a tmux fork, a discover sweep and a usage read for a value each setter already returns. The
2026-09-07 upstream fold dropped that read and takes the setter's own verdict (tests/test_model_live_midturn
pins the value; this pins the cost). The gate is patched to a counter, so the counts are the gate's own
evaluations and nothing underneath it runs. Synthetic only."""
import os
import tempfile
import unittest
from romp_load import load_source

os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()   # isolate: importing the kernel must not touch live state
os.environ.pop("ROMP_STATE_DIR", None)
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
km = load_source("romp_kernel_meta_gate", os.path.join(BIN, "romp-kernel"))

SID = "11111111-2222-3333-4444-555555555555"


class _Backend:
    """A backend that takes every setter; records what fired."""
    def __init__(self): self.calls = []
    def owns(self, sid): return True
    def forwards_sends(self): return True
    def set_model(self, sid, v): self.calls.append(("model", v))
    def set_effort(self, sid, v): self.calls.append(("effort", v))
    def set_fast(self, sid, v): self.calls.append(("fast", v)); return True


class MetaCommandGateCost(unittest.TestCase):
    def setUp(self):
        self.be = _Backend()
        self.gate_calls = []
        km._pending_ops.pop(SID, None)
        km._moving.discard(SID)
        self._saved = (km._ops_gate, km._compacting_now, km._working_now, km._limit_hold,
                       km._mark_model_pending, km._note_model_pick)
        km._ops_gate = lambda sid: (self.gate_calls.append(str(sid)), self.verdict)[1]
        km._compacting_now = lambda sid, **k: False     # the model setter's own gates, cheap here
        km._working_now = lambda sid: False
        km._limit_hold = lambda sid: None
        km._mark_model_pending = lambda *a, **k: None
        km._note_model_pick = lambda *a, **k: None
        self.verdict = False

    def tearDown(self):
        (km._ops_gate, km._compacting_now, km._working_now, km._limit_hold,
         km._mark_model_pending, km._note_model_pick) = self._saved
        km._pending_ops.pop(SID, None)

    def _route(self, text):
        self.gate_calls.clear()
        state = {}
        self.assertTrue(km._route_meta_command(self.be, SID, text, state=state), text)
        return len(self.gate_calls), state.get("queued")

    def test_effort_and_fast_evaluate_the_gate_once_and_model_never_when_they_fire(self):
        self.assertEqual(self._route("/effort high"), (1, False))
        self.assertEqual(self._route("/fast on"), (1, False))
        self.assertEqual(self._route("/model opus"), (0, False), "the model setter has its own rule; no _ops_gate")
        self.assertEqual(self.be.calls, [("effort", "high"), ("fast", "on"), ("model", "opus")], "each fired once")
        self.assertNotIn(SID, km._pending_ops)

    def test_the_counts_are_the_same_when_the_gate_parks(self):
        # the verdict comes from the setter's own return, so a park costs the same single read: before the
        # fold a parked /effort read the gate twice (the setter's, then the route's re-read for `queued`)
        self.verdict = True
        self.assertEqual(self._route("/effort high"), (1, True))
        self.assertEqual(self._route("/fast on"), (1, True))
        km._compacting_now = lambda sid, **k: True       # the model setter parks on its own gates
        self.assertEqual(self._route("/model opus"), (0, True))
        self.assertEqual(self.be.calls, [], "nothing fired: every op parked")
        self.assertEqual([op[0] for op in km._pending_ops[SID]], ["effort", "fast", "model"], "parked in press order")

    def test_the_route_itself_never_names_the_gate(self):
        # the source pin behind the counts: the route's body reads no _ops_gate (the setters do)
        import inspect
        src = inspect.getsource(km._route_meta_command)
        body = src.split('"""', 2)[2]                    # past the docstring, which discusses the gate
        self.assertNotIn("_ops_gate(", body)


if __name__ == "__main__":
    unittest.main()
