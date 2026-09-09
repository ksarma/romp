"""Effort-switch UX (the user 2026-07-06): /effort has no SDK runtime control, so romp applies it by
RECONNECTING the session (resume) — which otherwise leaves nothing in the chat. Now the effort badge shows
switching-dots and the chat shows a transient "Reloading session…" element while the reconnect is pending,
both driven by an `effortPending` flag that mirrors `modelPending` end-to-end and clears when the new client
connects. Source pins on build_session + the SDK backend."""
import inspect
import os
import unittest
from romp_load import load_source
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_efr", os.path.join(BIN, "romp-kernel"))
BACKEND_SRC = open(os.path.join(BIN, "romp_sdk_backend.py")).read()


class EffortReconnect(unittest.TestCase):
    def test_build_session_emits_a_reconnecting_event_while_effort_pending(self):
        src = inspect.getsource(km.build_session)
        # ...and while ANY pick is held for the session's live work (review round 2, 2026-09-09): the
        # event is the chat's only carrier of the hold, and a held mode, fast or billing pick had none
        self.assertIn('if (tm0 or {}).get("effortPending") or (tm0 or {}).get("pickHeld"):', src)
        self.assertIn('events.append(_reconnecting_event(tm0))', src)

    def test_the_reconnecting_event_covers_every_held_kind_and_names_the_effort_only_when_it_is_the_pick(self):
        # behaviour, not a pin: the composed event for the rows the chat can be in
        ev = km._reconnecting_event({"effortPending": True, "effort": "max", "pickHeld": None})
        self.assertEqual(ev, {"kind": "reconnecting", "effort": "max", "held": None}, "the armed effort reload")
        held = {"surfaces": ["mode"], "subagents": 1, "tasks": 0}
        ev = km._reconnecting_event({"effortPending": False, "effort": "high", "pickHeld": held})
        self.assertEqual(ev["held"], held, "a held mode pick reaches the chat")
        self.assertEqual(ev["effort"], "", "the row's effort is what the session runs, not a pick: not sent as one")
        for kind in ("fast", "auth", "effort"):
            ev = km._reconnecting_event({"effortPending": kind == "effort", "effort": "high",
                                         "pickHeld": {"surfaces": [kind], "subagents": 0, "tasks": 2}})
            self.assertEqual(ev["held"]["surfaces"], [kind], kind)
            self.assertEqual(ev["effort"], "", "held: the waiting line is keyed on the surfaces (%s)" % kind)
        self.assertEqual(km._reconnecting_event({"effortPending": False, "effort": "high", "pickHeld": None})["held"], None)
        self.assertEqual(km._reconnecting_event(None), {"kind": "reconnecting", "effort": "", "held": None})

    def test_the_loop_top_resets_every_arm_field_before_the_drop_and_the_landing_stamps_after_the_handshake(self):
        # the reconnect loop's top: _reset_reconnect_state is the FIRST statement after the wake clear
        # (adjacent, not merely somewhere above), and it precedes the teardown's _drop_live_work; the
        # round-0 line (`self._reconnect = False`) left the deferred arm and its hold standing, and every
        # test stayed green with it (review round 2, 2026-09-09: the helper was only ever called by hand)
        loop = BACKEND_SRC[BACKEND_SRC.index("        while not self.ended:\n            self._wake.clear()"):]
        lines = [l.strip() for l in loop.splitlines()[:3]]
        self.assertEqual(lines[:3], ["while not self.ended:", "self._wake.clear()",
                                     "self._reset_reconnect_state()   # every request is served by this connect (a held pick rides it)"])
        self.assertLess(loop.index("self._reset_reconnect_state()"), loop.index('self._drop_live_work("reconnect")'))
        self.assertNotIn("self._reconnect = False   #", loop[:loop.index("self._reset_reconnect_state()")])
        # and the stamps land with the connect: _connect_landed follows the launch-error clear, inside the loop
        i = loop.index("self.backend._clear_launch_error(self.sid)")
        tail = [l.strip() for l in loop[i:].splitlines() if l.strip() and not l.strip().startswith("#")]
        self.assertEqual(tail[1], "self._connect_landed()", tail[:3])

    def test_the_held_pick_reaches_the_status_readers(self):
        # the backend snapshot's pickHeld ({surfaces, subagents, tasks} or None) passes through the live
        # map and the status dict, beside effortPending, so the UI can tell a hold from a reload
        self.assertIn('"pickHeld": st.get("pickHeld") or None,', inspect.getsource(km.Sessions.live))
        self.assertIn('"pickHeld": tm.get("pickHeld") or None,', inspect.getsource(km.build_session))
        self.assertIn('"pickHeld": held,', BACKEND_SRC)

    def test_the_reconnecting_notice_precedes_the_queued_bubble(self):
        # like the compacting element, it must sit ABOVE any queued/provisional message
        src = inspect.getsource(km.build_session)
        i_recon = src.index('events.append(_reconnecting_event(tm0))')
        i_queued = src.index('events.append({"kind": "queued"')
        self.assertGreater(i_recon, 0)
        self.assertGreater(i_queued, i_recon)

    def test_status_dict_carries_effortPending_for_the_badge_dots(self):
        src = inspect.getsource(km.build_session)
        self.assertIn('"effortPending": bool(tm.get("effortPending")),', src)

    def test_sessions_live_passes_effortPending_through_from_the_sdk_backend(self):
        src = inspect.getsource(km.Sessions.live)
        self.assertIn('"effortPending": bool(st.get("effortPending")),', src)

    def test_backend_set_effort_arms_the_pending_flag_and_reconnects(self):
        self.assertIn('s._effort_pending = value', BACKEND_SRC)
        self.assertIn('self._update_reg(sid, effort=value, effortPending=True)', BACKEND_SRC)
        self.assertIn('s.request_reconnect()', BACKEND_SRC)

    def test_every_effort_pick_is_remembered_ultracode_included(self):
        # the user 2026-08-14: they pick ultracode and expect NEW sessions to follow. The old guard
        # (`if value != "ultracode"`) deliberately never remembered it, so the seed sat on their one
        # historical max pick and every new session opened at max — reading as a downgrade. spawn
        # still hands each new session its own per-session launch shape (--effort xhigh + the
        # ultracode settings key), so the CLI's session-scoping is preserved.
        self.assertNotIn('if value != "ultracode"', BACKEND_SRC)
        self.assertIn("write_sdk_default(self.state_dir, effort=value)", BACKEND_SRC)
        # …and the seed round-trips through the defaults store (behavioral, hermetic state dir)
        import tempfile as _tf
        sb = load_source("romp_sdk_backend_efr", os.path.join(BIN, "romp_sdk_backend.py"))
        td = _tf.mkdtemp()
        sb.write_sdk_default(td, effort="ultracode")
        d = sb.read_sdk_defaults(td)
        self.assertEqual(d.get("effort"), "ultracode")
        self.assertIn("ultracode", sb.EFFORT_LEVELS,
                      "spawn's seed filter (in EFFORT_LEVELS) must accept the remembered ultracode")

    def test_setters_write_the_reg_through_the_locked_rmw(self):
        # the bare read→mutate→write raced the loop threads' own locked RMWs (queue/echo mirrors,
        # liveCtx) and could silently drop the just-picked field: the label looked right, then the
        # value reverted at the next respawn when __init__ re-read the reg (the user 2026-08-14,
        # whose ultracode sessions seemed to downgrade at random). The whole setter family goes
        # through _update_reg now.
        for pin in ('self._update_reg(sid, effort=value, effortPending=True)',
                    'self._update_reg(sid, auth=value, authPending=True, apiKeyAuth=None)',
                    'self._update_reg(sid, mode=mode)',
                    'self._update_reg(sid, fast=(value == "on"), liveFast=value)',
                    'self._update_reg(sid, name=new_name,',   # + the rename ping rides the same locked RMW when owed (2026-08-24/25)
                    'self._update_reg(sid, model=value, modelPending=pending)',   # the live model write
                    'self._update_reg(sid, model=value, liveModel=_alias_label(value), modelPending=False)'):
            self.assertIn(pin, BACKEND_SRC)

    def test_backend_clears_the_pending_flag_when_the_reconnect_lands(self):
        # cleared the instant the new client connects (reconnect loop) — event-based, mirrors _model_pending
        self.assertIn('if self._effort_pending:', BACKEND_SRC)
        self.assertIn('self.backend._update_reg(self.sid, effortPending=False)', BACKEND_SRC)
        # exposed on both the live snapshot and the reg-backed live_sessions (for dormant/all sessions)
        self.assertIn('"effortPending": bool(self._effort_pending),', BACKEND_SRC)
        self.assertIn('"effortPending": bool(reg.get("effortPending")),', BACKEND_SRC)

    def test_backend_clears_pending_on_thread_death_so_the_dots_never_trap(self):
        self.assertIn('if sess._effort_pending:', BACKEND_SRC)


if __name__ == "__main__":
    unittest.main()
