#!/usr/bin/env python3
"""Kernel-owned GENERIC watches (T121 part 2, 2026-08-27): sessions kept arming in-process
background watchers for every non-PR wait, and kernel restarts killed them mid-wait. A generic
watch is a PREDICATE COMMAND the kernel runs on a cadence — exit 0 = the condition holds → ONE
[romp] mail (with the check's output tail) and the watch retires; the TIMEOUT mails the giving-up
notice (the standing watcher rule's other end); a first-run exec failure (127/126) retires loudly
at once. Persisted (watches.json), boot re-armed, the pr-watch pump's discipline end to end.
Synthetic only; hermetic state; predicates are stubbed at _watch_run."""
import json
import os
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
SourceFileLoader("romp_event_model", os.path.join(BIN, "romp-event-model")).load_module()
SourceFileLoader("romp_judge", os.path.join(BIN, "romp-judge")).load_module()
km = SourceFileLoader("romp_kernel_gw", os.path.join(BIN, "romp-kernel")).load_module()
jd = km.jd

SID = "11111111-2222-3333-4444-6666666666aa"


class _Watches(unittest.TestCase):
    def setUp(self):
        with km._watch_lock:
            km._watches[:] = []
        try:
            km.WATCH_FILE.unlink()
        except OSError:
            pass
        self.mails = []
        self._saved_deliver = km._pr_watch_deliver
        self._saved_run = km._watch_run
        km._pr_watch_deliver = lambda sid, text: self.mails.append((sid, text)) or True

    def tearDown(self):
        km._pr_watch_deliver = self._saved_deliver
        km._watch_run = self._saved_run
        with km._watch_lock:
            km._watches[:] = []
        try:
            km.WATCH_FILE.unlink()
        except OSError:
            pass


class Register(_Watches):
    def test_add_persists_and_boot_rearms(self):
        row, err = km.add_watch("test -f /tmp/x", SID, every=30, timeout_s=600, note="the file", now=100)
        self.assertIsNone(err)
        self.assertEqual((row["every"], row["timeoutS"], row["note"]), (30, 600, "the file"))
        # the store survives a "restart": clear runtime, reload from disk
        with km._watch_lock:
            km._watches[:] = []
        km._watches_load()
        rows = km.list_watches()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], row["id"], "the watch re-arms on boot — a restart moves it, never kills it")

    def test_refusals_are_loud_and_floors_hold(self):
        row, err = km.add_watch("", SID)
        self.assertIsNotNone(err)
        row, err = km.add_watch("true", SID, every=1)
        self.assertEqual(row["every"], km.WATCH_MIN_EVERY, "the cadence floor — a watch never hammers")
        row, err = km.add_watch("true", SID)
        self.assertEqual(row["timeoutS"], km.WATCH_DEFAULT_TIMEOUT, "an unbounded watch is a leak — 24h default")

    def test_cancel_retires_early(self):
        row, _ = km.add_watch("true", SID)
        self.assertTrue(km.cancel_watch(row["id"]))
        self.assertFalse(km.cancel_watch(row["id"]))
        self.assertEqual(km.list_watches(), [])


class Tick(_Watches):
    def test_met_mails_once_with_the_output_tail_and_retires(self):
        km.add_watch("check thing", SID, note="the deploy finished", now=0)
        km._watch_run = lambda cmd: (1, "not yet")
        km._watch_tick(10.0)
        self.assertEqual(self.mails, [], "not-yet keeps waiting quietly")
        km._watch_run = lambda cmd: (0, "deployed v2 OK")
        km._watch_tick(100.0)
        self.assertEqual(len(self.mails), 1)
        sid, text = self.mails[0]
        self.assertEqual(sid, SID)
        self.assertIn("now HOLDS: the deploy finished", text, "the user's note leads — their words for the wait")
        self.assertIn("deployed v2 OK", text, "the check's output rides along")
        self.assertIn("<!-- romp-tag: watch -->", text)
        self.assertEqual(km.list_watches(), [], "one mail, then the watch retires")

    def test_timeout_mails_the_giving_up_notice(self):
        km.add_watch("never", SID, every=15, timeout_s=60, now=0)
        km._watch_run = lambda cmd: (1, "")
        km._watch_tick(30.0)
        self.assertEqual(self.mails, [])
        km._watch_tick(61.0)
        self.assertEqual(len(self.mails), 1)
        self.assertIn("gave up watching", self.mails[0][1])
        self.assertIn("never held", self.mails[0][1])
        self.assertEqual(km.list_watches(), [], "the standing watcher rule: never a silent dead loop")

    def test_first_run_exec_failure_retires_loudly_at_once(self):
        km.add_watch("nosuchbinary --flag", SID, now=0)
        km._watch_run = lambda cmd: (127, "sh: nosuchbinary: not found")
        km._watch_tick(1.0)
        self.assertEqual(len(self.mails), 1)
        self.assertIn("could not run at all", self.mails[0][1])
        self.assertEqual(km.list_watches(), [], "a typo'd command must not wait silently for its timeout")

    def test_a_rearmed_watch_never_takes_the_first_run_retire(self):
        km.add_watch("flaky", SID, now=0)
        with km._watch_lock:
            km._watches[:] = []
        km._watches_load()   # the boot path marks rows as already-run
        km._watch_run = lambda cmd: (127, "transient PATH blip on boot")
        km._watch_tick(1.0)
        self.assertEqual(self.mails, [], "a boot blip is not a typo — the re-armed watch keeps waiting")
        self.assertEqual(len(km.list_watches()), 1)

    def test_rate_gate_and_cadence(self):
        km.add_watch("slow", SID, every=60, now=0)
        runs = []
        km._watch_run = lambda cmd: runs.append(1) or (1, "")
        km._watch_tick(1.0)
        km._watch_tick(2.0)
        self.assertEqual(len(runs), 1, "the per-row gate holds between polls")
        km._watch_tick(62.0)
        self.assertEqual(len(runs), 2)


class Wiring(_Watches):
    def test_pump_and_boot_are_wired_beside_the_pr_watch(self):
        src = open(os.path.join(os.path.dirname(HERE), "kernel", "kernel.py")).read()
        self.assertIn("_watch_tick(now)             # generic predicate watches (T121 part 2)", src,
                      "the generic tick rides the same supervisor pass as the pr-watch pump")
        self.assertIn("_watches_load()                                            # …and the generic watches", src,
                      "…and the same boot re-arm")

    def test_the_real_watch_run_contract(self):
        code, out = km._watch_run("exit 3")
        self.assertEqual(code, 3)
        code, out = km._watch_run("echo held; exit 0")
        self.assertEqual((code, out), (0, "held"))


if __name__ == "__main__":
    unittest.main()
