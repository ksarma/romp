#!/usr/bin/env python3
"""One flaky tmux read must not read as mass death for the CHAT TAB LIST (2026-08-18).

list_lines collapses any exec error/timeout to [] — deliberately (the primitive stays lossy; each
consumer applies its own doctrine, and other consumers have theirs). The death writers already
refuse to inherit that collapse: alive_sids returns None on a REAL probe failure and they stand
down. The tab list had no doctrine at all: one collapsed read flowed through the pusher's snapshot
into _chat_tab_sessions, the push omitted every tmux session, and the client — for which the
continuous tabOrder push is the authority on what exists — tore them all down. The next push
re-listed ids whose sessions the client no longer held: the permanent dead-swirl strip
(seen on a remote host's tabs, 2026-08-18).

_tab_list_tmux mirrors the death writers' refusal for the tab list only: an empty tmux half where
the previous push had sessions is corroborated with alive_sids — an authoritative zero (no server /
no romp sessions) is adopted, a real probe failure carries the PREVIOUS push's tmux entries, loudly
(one log per episode), until a read answers again.

SYNTHETIC fixtures only: placeholder UUIDs, invented names, hermetic temp STATE.
"""
import contextlib
import io
import json
import os
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
SourceFileLoader("romp_event_model", os.path.join(BIN, "romp-event-model")).load_module()
SourceFileLoader("romp_judge", os.path.join(BIN, "romp-judge")).load_module()
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
km = SourceFileLoader("romp_kernel_tabcarry", os.path.join(BIN, "romp-kernel")).load_module()
jd = km.jd

SID = "11111111-2222-3333-4444-555555555555"
ROW = {"state": "waiting", "since": 0, "model": "", "effort": "", "context": None,
       "compactPct": None, "color": None, "mode": "", "backend": "tmux"}
SDK_SID = "99999999-8888-7777-6666-555555555555"
SDK_ROW = {"state": "working", "backend": "sdk"}


def reset_carry():
    km._tab_tmux_carry["prev"] = {}
    km._tab_tmux_carry["collapsed"] = False


class CollapseCarryUnit(unittest.TestCase):
    """_tab_list_tmux in isolation: adopt / corroborate / carry / recover."""

    def setUp(self):
        reset_carry()
        self._alive = km._TMUX.alive_sids
        self.probes = []

    def tearDown(self):
        km._TMUX.alive_sids = self._alive
        reset_carry()

    def _probe(self, answer):
        def alive_sids(t=3):
            self.probes.append(1)
            return answer
        km._TMUX.alive_sids = alive_sids

    def _guard(self, tmux):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            out = km._tab_list_tmux(tmux)
        return out, err.getvalue()

    def test_a_healthy_read_passes_through_and_never_probes(self):
        self._probe(None)
        out, err = self._guard({SID: ROW})
        self.assertIn(SID, out)
        self.assertEqual(self.probes, [], "a non-empty read needs no corroboration")
        self.assertEqual(err, "")

    def test_a_collapsed_read_carries_the_previous_push_loudly_once(self):
        self._guard({SID: ROW})                       # the previous push's world
        self._probe(None)                             # a REAL probe failure — the ambiguous case
        out, err = self._guard({})
        self.assertIn(SID, out, "the collapse is carried — never an empty tab list from a failed read")
        self.assertIn("tab-list", err, "loud: the carry is logged")
        out2, err2 = self._guard({})                  # the episode continues…
        self.assertIn(SID, out2)
        self.assertEqual(err2, "", "…but logs once per episode, not once per cycle")

    def test_a_probe_that_sees_sessions_proves_the_collapse_and_carries(self):
        self._guard({SID: ROW})
        self._probe({SID})                            # list_lines collapsed, the corroboration answered
        out, _err = self._guard({})
        self.assertIn(SID, out, "an empty snapshot the probe contradicts is a collapse, not a death")

    def test_an_authoritative_zero_is_adopted_not_carried(self):
        self._guard({SID: ROW})
        self._probe(set())                            # no server / no romp sessions — the reboot shape
        out, err = self._guard({})
        self.assertNotIn(SID, out, "a genuine mass death must reach the client — carrying would keep dead tabs")
        n = len(self.probes)
        out2, _e = self._guard({})                    # the empty world persists…
        self.assertNotIn(SID, out2)
        self.assertEqual(len(self.probes), n, "…with nothing left to carry, no more corroboration probes")
        self.assertNotIn("carrying", err)

    def test_recovery_resumes_live_reads_and_says_so(self):
        self._guard({SID: ROW})
        self._probe(None)
        self._guard({})                               # the collapse episode starts
        out, err = self._guard({SID: ROW})            # a read answers again
        self.assertIn(SID, out)
        self.assertIn("recovered", err, "the episode's end is logged too")
        out2, err2 = self._guard({})
        # prev was refreshed by the healthy read, so a NEW collapse is a NEW episode with a new log
        self.assertIn(SID, out2)
        self.assertIn("tab-list", err2)

    def test_sdk_sessions_ride_through_a_carry_untouched(self):
        self._guard({SID: ROW})
        self._probe(None)
        out, _err = self._guard({SDK_SID: SDK_ROW})
        # the SDK half of the snapshot answered; only the tmux half collapsed — carry must MERGE,
        # never replace, or a tmux flake would tear down every SDK tab instead
        self.assertIn(SDK_SID, out)
        self.assertIn(SID, out)

    def test_first_boot_with_no_previous_world_trusts_the_empty_read(self):
        self._probe(None)
        out, err = self._guard({})
        self.assertEqual({k for k, v in out.items() if (v or {}).get("backend") == "tmux"}, set())
        self.assertEqual(self.probes, [], "nothing to carry → nothing to corroborate")
        self.assertEqual(err, "")


class CollapseCarryThroughPush(unittest.TestCase):
    """The seam end-to-end: a collapsed cycle's PUSH must still list the previous cycle's tmux
    sessions in tabOrder (the frame the client treats as authoritative for teardown)."""

    def setUp(self):
        reset_carry()
        self.td = tempfile.TemporaryDirectory()
        td = Path(self.td.name)
        self.saved = (jd.NAMES, jd.PROJECTS, jd.CAPDIR, jd.ARCHDIR, jd.GOALDIR, jd.STATE,
                      km.NAMES, km._sdk, km._cached_feed, km._fleet_view_sig)
        names = td / "names"; names.mkdir()
        proj = td / "projects"; proj.mkdir()
        jd.NAMES, jd.PROJECTS = names, proj
        jd.CAPDIR, jd.ARCHDIR, jd.GOALDIR = td / "captions", td / "archive", td / "goals"
        for d in (jd.CAPDIR, jd.ARCHDIR, jd.GOALDIR):
            d.mkdir()
        jd.STATE = td
        km.NAMES = names
        km._sdk = lambda: None
        km._cached_feed = lambda *a, **k: None      # the feed leg is not under test
        km._fleet_view_sig = lambda *a, **k: None
        cdir = td / "work"; cdir.mkdir()
        pdir = proj / jd.re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(str(cdir)))
        pdir.mkdir(parents=True)
        rec = {"type": "user", "timestamp": "2026-06-11T00:00:00.000Z", "uuid": "u1",
               "parentUuid": None, "promptSource": "typed",
               "message": {"role": "user", "content": "hello there"}}
        (pdir / (SID + ".jsonl")).write_text(json.dumps(rec) + "\n")
        (names / SID).write_text("web\t%s\t#abcdef\n" % str(cdir))
        self._alive = km._TMUX.alive_sids

    def tearDown(self):
        (jd.NAMES, jd.PROJECTS, jd.CAPDIR, jd.ARCHDIR, jd.GOALDIR, jd.STATE,
         km.NAMES, km._sdk, km._cached_feed, km._fleet_view_sig) = self.saved
        km._TMUX.alive_sids = self._alive
        reset_carry()
        self.td.cleanup()

    def _push_orders(self, tmux):
        frames = []
        client = {"app": "chat", "alive": True, "wid": "", "qbytes": 0,
                  "send": lambda s: frames.append(json.loads(s)), "sent": {}, "echat": {}}
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._push([client], tmux=tmux)
        return [f["order"] for f in frames if f.get("type") == "tabOrder"], err.getvalue()

    def test_one_collapsed_cycle_does_not_omit_the_board_and_recovery_resumes(self):
        orders, _e = self._push_orders({SID: ROW})              # a healthy cycle: the tab exists
        self.assertTrue(orders and SID in orders[-1], "healthy baseline lists the session")
        km._TMUX.alive_sids = lambda t=3: None                  # the next read collapses for real
        orders, err = self._push_orders({})
        self.assertTrue(orders and SID in orders[-1],
                        "the collapsed cycle's push carries the previous set — the client must never "
                        "see the one-push omission that tears every tab down")
        self.assertIn("tab-list", err, "and says so, once")
        km._TMUX.alive_sids = lambda t=3: set()                 # …later, an authoritative zero
        orders, _e = self._push_orders({})
        self.assertTrue(orders and SID not in orders[-1],
                        "a corroborated empty board flows through — dead sessions really do drop")


if __name__ == "__main__":
    unittest.main()
