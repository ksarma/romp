#!/usr/bin/env python3
"""Judge-tier settings follow to every linked kernel (the user 2026-08-12, who picked a new triage
model and wanted all machines on it — per-machine judge tiers are a surprise, not a feature).

Three pieces, each covered here:
- POST /judge-settings: the settable surface a peer kernel drives — applies any of the four fields
  through the EXISTING validated setters (_apply_judge_settings) and answers with the current
  values, so an ignored invalid value is visible in the ack.
- _propagate_judge_settings: the fan-out — one call per up linked kernel over its tunnel + its own
  serve token (mirror_trust's transport and trust boundary), loud on a miss, never blocking the
  pick (callers thread it).
- One hop, never a loop: the gear's WS ops and the route's explicit {"propagate": true} fan out;
  a FORWARDED body never carries the flag, so a receiving kernel applies and stops.

Synthetic hosts and tokens; hermetic state dir; the transport is stubbed — no sockets.
"""
import contextlib
import io
import os
import tempfile
import time
import unittest
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
km = SourceFileLoader("romp_kernel_judgesync", os.path.join(BIN, "romp-kernel")).load_module()


class ApplySettings(unittest.TestCase):
    def setUp(self):
        for f in ("judge-model", "index-model", "judge-effort", "index-effort",
                  "distill-model", "distill-effort",
                  "comment-model", "comment-effort", "comment-fast"):
            try:
                (km.jd.STATE / f).unlink()
            except OSError:
                pass

    def test_distill_pair_applies_pins_and_reports_raw(self):
        # the ack answers the RAW stored value ("triage" = following the triage pick), matching
        # /version, so the gear shows the user's CHOICE — never its resolution
        res = km._apply_judge_settings({})
        self.assertEqual((res["distillModel"], res["distillEffort"]), ("triage", "triage"))
        res = km._apply_judge_settings({"distillModel": "haiku", "distillEffort": "none"})
        self.assertEqual((km.jd.STATE / "distill-model").read_text(), "haiku")
        self.assertEqual((km.jd.STATE / "distill-effort").read_text(), "none",
                         '"none" PINS no-flag; "" is unstorable (folds into the follow default) and ignored')
        self.assertEqual((res["distillModel"], res["distillEffort"]), ("haiku", "none"))
        res = km._apply_judge_settings({"distillEffort": ""})
        self.assertEqual(res["distillEffort"], "none", "an empty distill effort is invalid, not a clear")

    def test_comment_defaults_apply_and_report_raw(self):
        # the default-comment trio (the user 2026-08-29) rides the same cross-kernel door as the
        # judge tiers: applied through the validated setters, answered RAW ("session" = same as
        # the session), garbage ignored and visible in the ack
        res = km._apply_judge_settings({})
        self.assertEqual((res["commentModel"], res["commentEffort"], res["commentFast"]),
                         ("session", "session", "session"))
        res = km._apply_judge_settings({"commentModel": "claude-opus-5", "commentEffort": "high",
                                        "commentFast": "on"})
        self.assertEqual((km.jd.STATE / "comment-model").read_text(), "claude-opus-5")
        self.assertEqual((km.jd.STATE / "comment-effort").read_text(), "high")
        self.assertEqual((km.jd.STATE / "comment-fast").read_text(), "on")
        self.assertEqual((res["commentModel"], res["commentEffort"], res["commentFast"]),
                         ("claude-opus-5", "high", "on"))
        res = km._apply_judge_settings({"commentModel": "gpt-99", "commentFast": "true"})
        self.assertEqual((res["commentModel"], res["commentFast"]), ("claude-opus-5", "on"),
                         "garbage never reaches the files or `claude --model`")

    def test_an_older_propagated_value_never_overwrites_a_newer_pick(self):
        # THE REPORTED STOMP (the user 2026-08-30): their Distilling pick kept resetting — any
        # later-arriving propagation replaced a fresher local pick wholesale, because the apply had
        # no notion of WHEN each value was picked. Now every propagated field carries its pick
        # stamp, and older-or-equal never lands.
        km._apply_judge_settings({"distillModel": "claude-opus-4-8"})   # the user's pick, mtime = now
        res = km._apply_judge_settings({"distillModel": "triage",
                                        "stamps": {"distillModel": time.time() - 3600}})
        self.assertEqual(res["distillModel"], "claude-opus-4-8",
                         "an hour-old peer value must not stomp the fresh pick")
        newer = time.time() + 60
        res = km._apply_judge_settings({"distillModel": "triage", "stamps": {"distillModel": newer}})
        self.assertEqual(res["distillModel"], "triage", "a genuinely newer pick still lands")
        self.assertAlmostEqual((km.jd.STATE / "distill-model").stat().st_mtime, newer, delta=1,
                               msg="the ORIGIN's pick time rides the file, so recency survives re-fans")

    def test_a_stampless_body_keeps_the_legacy_apply(self):
        # an older kernel (or a manual curl) sends no stamps — it applies unconditionally, exactly
        # as before; the stomp protection needs both ends on this code
        km._apply_judge_settings({"distillModel": "claude-opus-4-8"})
        res = km._apply_judge_settings({"distillModel": "haiku"})
        self.assertEqual(res["distillModel"], "haiku")

    def test_a_rejected_value_never_steals_the_stamp(self):
        # garbage with a newer stamp: the setter refuses it, and the utime must NOT re-stamp the
        # surviving old content with the new time (that would shadow-block the next honest pick)
        km._apply_judge_settings({"judgeModel": "fable"})
        t0 = (km.jd.STATE / "judge-model").stat().st_mtime
        km._apply_judge_settings({"judgeModel": "gpt-99", "stamps": {"judgeModel": time.time() + 999}})
        self.assertEqual((km.jd.STATE / "judge-model").read_text(), "fable")
        self.assertEqual((km.jd.STATE / "judge-model").stat().st_mtime, t0)

    def test_distill_sentinel_returns_the_pair_to_follow_mode(self):
        km._apply_judge_settings({"distillModel": "haiku", "distillEffort": "high"})
        res = km._apply_judge_settings({"distillModel": "triage", "distillEffort": "triage"})
        self.assertEqual((res["distillModel"], res["distillEffort"]), ("triage", "triage"))

    def test_distill_garbage_is_ignored_like_every_other_tier(self):
        km._apply_judge_settings({"distillModel": "haiku"})
        res = km._apply_judge_settings({"distillModel": "gpt-99"})
        self.assertEqual(res["distillModel"], "haiku", "garbage never reaches `claude --model`")

    def test_version_and_tunnels_carry_the_settings_dict(self):
        # source pins in the sync file's own style: /version publishes ONE settings dict a peer
        # kernel lifts onto its /tunnels row, and the row serializer forwards it (None = older kernel)
        import inspect
        src = inspect.getsource(km)
        self.assertIn('"settings": {"autoNudge": _auto_nudge_on(), "updateMode": _update_mode()', src)
        self.assertIn('"settings": r.get("settings") if isinstance(r.get("settings"), dict) else None', src)
        self.assertIn('r["settings"] = (rver or {}).get("settings")', src)

    def test_valid_fields_land_and_the_ack_reports_them(self):
        res = km._apply_judge_settings({"judgeModel": "fable", "indexEffort": "low"})
        self.assertEqual((km.jd.STATE / "judge-model").read_text(), "fable")
        self.assertEqual((km.jd.STATE / "index-effort").read_text(), "low")
        self.assertEqual((res["judgeModel"], res["indexEffort"]), ("fable", "low"))
        self.assertTrue(res["ok"])

    def test_an_invalid_value_is_ignored_and_the_ack_shows_what_actually_holds(self):
        km._apply_judge_settings({"judgeModel": "fable"})
        res = km._apply_judge_settings({"judgeModel": "gpt-99"})
        self.assertEqual((km.jd.STATE / "judge-model").read_text(), "fable",
                         "garbage never reaches `claude --model`")
        self.assertEqual(res["judgeModel"], "fable")

    def test_an_empty_effort_clears_back_to_default(self):
        km._apply_judge_settings({"judgeEffort": "high"})
        res = km._apply_judge_settings({"judgeEffort": ""})
        self.assertEqual((km.jd.STATE / "judge-effort").read_text(), "")
        self.assertEqual(res["judgeEffort"], "")

    def test_fields_not_in_the_body_are_untouched(self):
        km._apply_judge_settings({"judgeModel": "fable"})
        km._apply_judge_settings({"indexModel": "haiku"})
        self.assertEqual((km.jd.STATE / "judge-model").read_text(), "fable")


class PropagateFansOut(unittest.TestCase):
    def setUp(self):
        self._rkc = km._remote_kernel_call
        self._rem = dict(km._remotes)
        km._remotes.clear()
        km._remotes.update({
            "boxup":    {"host": "boxup", "status": "up", "local_port": 1, "token": "t1"},
            "boxdown":  {"host": "boxdown", "status": "down", "local_port": 2, "token": "t2"},
            "boxnotok": {"host": "boxnotok", "status": "up", "local_port": 3, "token": ""},
        })
        self.calls = []

    def tearDown(self):
        km._remote_kernel_call = self._rkc
        km._remotes.clear()
        km._remotes.update(self._rem)

    def test_every_up_kernel_with_an_admin_path_gets_the_pick(self):
        km._remote_kernel_call = lambda r, m, p, payload=None, timeout=8: (
            self.calls.append((r["host"], m, p, payload)) or (200, {"ok": True}, None))
        try:
            (km.jd.STATE / "judge-model").unlink()   # never picked here -> no stamp to carry
        except OSError:
            pass
        km._propagate_judge_settings({"judgeModel": "fable"})
        self.assertEqual(self.calls,
                         [("boxup", "POST", "/judge-settings", {"judgeModel": "fable", "stamps": {}})],
                         "up + token only; a down row or one with no token is not an admin path")

    def test_the_fanned_body_stamps_each_field_with_its_pick_time(self):
        # the user 2026-08-30 ("my Distilling pick continually gets reset"): authority is per field
        # and per PICK TIME — the stamp is the STATE file's own mtime, the pick event itself
        km._remote_kernel_call = lambda r, m, p, payload=None, timeout=8: (
            self.calls.append(payload) or (200, {"ok": True}, None))
        km._set_distill_model("claude-opus-4-8")
        want = (km.jd.STATE / "distill-model").stat().st_mtime
        km._propagate_judge_settings({"distillModel": "claude-opus-4-8"})
        self.assertEqual(self.calls[0]["stamps"], {"distillModel": want})

    def test_a_miss_is_loud_and_names_the_machine(self):
        km._remote_kernel_call = lambda *a, **k: (None, None, "could not reach boxup's kernel: boom")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._propagate_judge_settings({"judgeModel": "fable"})
        self.assertIn("boxup", err.getvalue())
        self.assertIn("did not take the pick", err.getvalue())


class OneHopNeverALoop(unittest.TestCase):
    """The wiring is inline (WS handlers + the route) — pinned at the source; the behaviors the
    pins delegate to are tested above."""

    def setUp(self):
        with open(os.path.join(BIN, "romp-kernel")) as f:
            self.src = f.read()

    def test_the_route_exists_and_only_fans_out_on_the_explicit_flag(self):
        self.assertIn('if u.path == "/judge-settings":', self.src)
        self.assertIn('if isinstance(body, dict) and body.get("propagate"):', self.src)
        self.assertIn('fwd = {k: v for k, v in body.items() if k != "propagate"}', self.src,
                      "a forwarded body never carries the flag — one hop, never a mesh loop")

    def test_every_gear_op_propagates_its_own_field(self):
        for frag in ('args=({"judgeModel": str(msg["model"])},)',
                     'args=({"indexModel": str(msg["model"])},)',
                     'args=({"judgeEffort": str(msg.get("effort") or "")},)',
                     'args=({"indexEffort": str(msg.get("effort") or "")},)',
                     'args=({"commentModel": str(msg["model"])},)',
                     'args=({"commentEffort": str(msg["effort"])},)',
                     'args=({"commentFast": str(msg["fast"])},)'):
            self.assertIn(frag, self.src, frag)

    def test_the_gear_copy_says_the_pick_follows(self):
        with open(os.path.join(os.path.dirname(HERE), "ui", "webview", "gear.js")) as f:
            gear = f.read()
        self.assertGreaterEqual(gear.count("connected machine's kernel"), 4,
                                "all four judge rows say the pick follows to the other machines")


if __name__ == "__main__":
    unittest.main(verbosity=2)
