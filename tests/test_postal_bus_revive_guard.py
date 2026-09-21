#!/usr/bin/env python3
"""The kernel's bus revive guard and the ensure ROADS (the fold 3 review, 2026-09-21: regression-2, kernel-2, regression-3).

_revive_postal_bus reads the environment's client-only word as "this kernel must start no bus", a stricter gate than the
postal service's own mode on purpose: the suite's floor sets the word with peers ON, and a guard that mirrored
postal_service.is_client_only() (peers off AND the word or the marker) would let every in-process test kernel spawn a real
bus off a refused notify on a daemon thread, the 2026-09-18 leak. What the kernel knows of its own bus outranks the word:
a kernel that ensured a bus of its own (_BUS_ENSURED) revives it, word or no word. The flag is armed only on an ensure road
on which this machine owns a local bus (`spawned`, `up`), which postal_service.ensure_road reports and the `ensure` verb
prints on stdout, never on a client-only host's ping of its tunnel nor on a tunnel or another environment's bus answering
the port. Hermetic: a private state root with the hosts floor off, the ensure a stub or its ping stubbed, the spawn a
recorder; no bus is ever started."""
import contextlib
import inspect
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest

from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
_XDG = tempfile.mkdtemp()                      # a state root of this module's own: the record below is never the machine's
os.environ["XDG_STATE_HOME"] = _XDG
os.environ.pop("ROMP_STATE_DIR", None)
os.makedirs(os.path.join(_XDG, "romp"), exist_ok=True)
open(os.path.join(_XDG, "romp", "session-hosts"), "w").write("off\n")
km = load_source("romp_kernel_bus_revive_guard", os.path.join(BIN, "romp-kernel"))
pm = load_source("romp_postal_bus_revive_guard", os.path.join(BIN, "romp-postal-service"))

ROADS = ("spawned", "up", "answering", "client-only", "refused", "down")   # ensure_road's roads, as its docstring lists them


class ReviveGuard(unittest.TestCase):
    """_revive_postal_bus under the four worlds: the word with peers on (the suite's floor), the word with a bus of the
    kernel's own, a client-only host, and no word."""

    def setUp(self):
        self._env = {k: os.environ.get(k) for k in ("ROMP_POSTAL_CLIENT_ONLY", "ROMP_POSTAL_PEERS")}
        self._saved = (km._ensure_postal_bus, km._BUS_ENSURED[0], km._bus_reviving[0])
        self.kicked = threading.Event()
        km._ensure_postal_bus = self.kicked.set     # the ensure is a stub: no subprocess, no bus
        km._bus_reviving[0] = False
        km._BUS_ENSURED[0] = False

    def tearDown(self):
        for _ in range(200):                       # a revive thread finishes before the world goes back
            if not km._bus_reviving[0]:
                break
            time.sleep(0.01)
        km._ensure_postal_bus, km._BUS_ENSURED[0], km._bus_reviving[0] = self._saved
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _world(self, word, peers):
        for k, v in (("ROMP_POSTAL_CLIENT_ONLY", word), ("ROMP_POSTAL_PEERS", peers)):
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_the_word_with_no_bus_of_its_own_skips_the_revive_the_suites_floor(self):
        # the world the run's conftest floors: the word set, peers on. The service's mode says NOT client-only here, so a guard
        # that mirrored it would revive and spawn (the fix the refuters rejected); the kernel's reads the word as "start no bus"
        self._world("1", None)
        self.assertFalse(pm.is_client_only(), "the service's mode is inert to the word while peers are on")
        km._revive_postal_bus()
        self.assertFalse(self.kicked.wait(0.3), "no ensure: this kernel never ensured a bus of its own and the word says start none")
        for word in ("on", "true", "yes"):        # the word's spellings
            self._world(word, None)
            km._revive_postal_bus()
            self.assertFalse(self.kicked.wait(0.1), word)

    def test_a_kernel_that_ensured_a_bus_of_its_own_revives_it_word_or_no_word(self):
        # the fold 3 review's defect: a kernel that set the word with peers on owns a real bus (its ensure spawned one) and used
        # to refuse silently to re-ensure it when it died. What the kernel knows of its own bus outranks the word.
        self._world("1", None)
        km._BUS_ENSURED[0] = True
        km._revive_postal_bus()
        self.assertTrue(self.kicked.wait(5), "the kernel ensured a bus of its own: the refusal kicks the ensure, word or no word")

    def test_a_client_only_host_never_revives(self):
        # peers off and the word: the service's client-only mode, whose ensure only pings the tunnel and never arms the flag
        self._world("1", "0")
        self.assertTrue(pm.is_client_only())
        km._revive_postal_bus()
        self.assertFalse(self.kicked.wait(0.3), "a client-only host owns no bus to revive")

    def test_without_the_word_the_revive_runs(self):
        self._world(None, None)
        km._revive_postal_bus()
        self.assertTrue(self.kicked.wait(5), "no word, no flag needed: a kernel that owns its machine's bus re-ensures it")


class EnsureRoads(unittest.TestCase):
    """postal_service.ensure_road, each road by execution over a stubbed ping and a recording spawn, the bus's record under
    this module's private root."""

    def setUp(self):
        self._saved = (pm.ping, pm.is_client_only, pm._fixed_port_refusal, pm._refuse_loudly, pm.subprocess, pm.time)
        pm.PORTFILE.parent.mkdir(parents=True, exist_ok=True)
        self._unlink()
        self.spawned, self.refused = [], []
        pm.subprocess = types.SimpleNamespace(Popen=lambda argv, **kw: self.spawned.append([str(a) for a in argv]),
                                              DEVNULL=subprocess.DEVNULL)
        pm.time = types.SimpleNamespace(sleep=lambda s: None, time=time.time)   # the spawn wait's ~4 s of sleeps, skipped
        pm._refuse_loudly = self.refused.append
        pm._fixed_port_refusal = lambda: None
        pm.is_client_only = lambda: False

    def tearDown(self):
        (pm.ping, pm.is_client_only, pm._fixed_port_refusal, pm._refuse_loudly, pm.subprocess, pm.time) = self._saved
        self._unlink()

    def _unlink(self):
        try:
            pm.PORTFILE.unlink()
        except FileNotFoundError:
            pass

    def _record(self, port=45678, pid=None, tok=None):
        pm.PORTFILE.write_text(json.dumps({"port": port, "pid": os.getpid() if pid is None else pid,
                                           "tok": pm._token_mark() if tok is None else tok}))

    def test_the_machines_own_bus_already_answering_is_up(self):
        pm.ping = lambda: True
        self._record()
        self.assertEqual(pm.ensure_road(), (True, "up"), "a live record under this token: the machine's own bus")
        self.assertEqual(self.spawned, [])
        self._record(port=45679)                   # the record's port need not be the port that answered: the bus is still ours
        self.assertEqual(pm.ensure_road(), (True, "up"))

    def test_a_bus_answering_without_a_live_record_of_this_token_is_answering_and_owned_by_nobody_here(self):
        pm.ping = lambda: True
        self.assertEqual(pm.ensure_road(), (True, "answering"), "no record: a tunnel, another environment's bus, a failed record write")
        self._record(pid=2 ** 22 + 12345)          # a pid that does not run: a stale record
        self.assertEqual(pm.ensure_road(), (True, "answering"))
        self._record(tok="0123456789abcdef")       # another token's mark: another world's bus
        self.assertEqual(pm.ensure_road(), (True, "answering"))
        pm.PORTFILE.write_text("torn")
        self.assertEqual(pm.ensure_road(), (True, "answering"), "a torn record: never a raise")
        self._record(port=0)
        self.assertEqual(pm.ensure_road(), (True, "answering"))
        self.assertEqual(self.spawned, [], "reachable is reachable: nothing is spawned over an answering bus")

    def test_a_client_only_host_only_pings(self):
        pm.is_client_only = lambda: True
        pm.ping = lambda: True
        self._record()                             # even a live local record does not make a client-only host's bus its own
        self.assertEqual(pm.ensure_road(), (True, "client-only"))
        pm.ping = lambda: False
        self.assertEqual(pm.ensure_road(), (False, "client-only"), "the tunnel is down: not ok, and still nothing started")
        self.assertEqual(self.spawned, [])

    def test_the_fixed_port_refusal_is_the_refused_road_said_before_any_spawn(self):
        pm.ping = lambda: False
        pm._fixed_port_refusal = lambda: "under a test: refusing the fixed port"
        self.assertEqual(pm.ensure_road(), (False, "refused"))
        self.assertEqual(self.refused, ["under a test: refusing the fixed port"])
        self.assertEqual(self.spawned, [])

    def test_a_spawn_that_answers_is_spawned(self):
        pm.ping = lambda: bool(self.spawned)       # nothing answers until the serve is started
        self.assertEqual(pm.ensure_road(), (True, "spawned"))
        self.assertEqual(len(self.spawned), 1)
        self.assertEqual(self.spawned[0][0], sys.executable)
        self.assertEqual(self.spawned[0][-1], "serve")

    def test_a_spawn_nothing_answers_is_down(self):
        pm.ping = lambda: False
        self.assertEqual(pm.ensure_road(), (False, "down"))
        self.assertEqual(len(self.spawned), 1)

    def test_ensure_is_the_roads_ok(self):
        pm.ping = lambda: True
        self.assertIs(pm.ensure(), True)
        pm.ping = lambda: False
        pm.is_client_only = lambda: True
        self.assertIs(pm.ensure(), False)

    def test_the_verb_prints_the_road_and_exits_on_the_ok(self):
        saved = pm.ensure_road
        try:
            for ok, road, code in ((True, "up", 0), (True, "spawned", 0), (False, "down", 1), (False, "client-only", 1)):
                pm.ensure_road = lambda ok=ok, road=road: (ok, road)
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    rc = pm.main(["ensure"])
                self.assertEqual((rc, out.getvalue()), (code, "ensure: road=%s\n" % road))
        finally:
            pm.ensure_road = saved

    def test_the_roads_are_the_documented_six_and_the_owned_two_are_the_same_on_both_sides(self):
        src = inspect.getsource(pm.ensure_road)
        for road in ROADS:
            self.assertIn('"%s"' % road, src, road)
        self.assertEqual(set(pm.ENSURE_OWNED), {"spawned", "up"})
        self.assertEqual(set(km._BUS_OWNED_ROADS), set(pm.ENSURE_OWNED), "the kernel arms on the roads the service calls owned")
        self.assertEqual(pm._token_mark(), km._bus_token_mark(), "one token, one mark: the record the service calls its own is the one the kernel trusts")


class KernelReadsTheRoad(unittest.TestCase):
    """The kernel's side: the road line parsed off the ensure's stdout, and _BUS_ENSURED armed on the owned roads alone."""

    def test_the_road_line_is_read_and_a_missing_one_is_empty(self):
        self.assertEqual(km._ensure_road("ensure: road=up\n"), "up")
        self.assertEqual(km._ensure_road("some other line\nensure: road=spawned\n"), "spawned")
        self.assertEqual(km._ensure_road(""), "")
        self.assertEqual(km._ensure_road(None), "")
        self.assertEqual(km._ensure_road("road=up\n"), "", "a line that is not the verb's is no road")

    def test_the_record_trust_is_armed_on_the_owned_roads_alone(self):
        saved_run, saved_flag, saved_err = km.subprocess.run, km._BUS_ENSURED[0], sys.stderr
        class R:
            def __init__(self, code, out): self.returncode, self.stdout, self.stderr = code, out, ""
        try:
            for road in ROADS:
                km._BUS_ENSURED[0] = False
                km.subprocess.run = lambda *a, road=road, **kw: R(0, "ensure: road=%s\n" % road)
                sys.stderr = err = io.StringIO()
                km._ensure_postal_bus()
                self.assertEqual(km._BUS_ENSURED[0], road in pm.ENSURE_OWNED, road)
                if road not in pm.ENSURE_OWNED:
                    self.assertIn("postal bus ensure took the %s road" % road, err.getvalue(), "an unowned road is said once in the kernel's log")
                else:
                    self.assertEqual(err.getvalue(), "")
        finally:
            km.subprocess.run, km._BUS_ENSURED[0], sys.stderr = saved_run, saved_flag, saved_err

    def test_the_words_the_verb_prints_are_the_words_the_kernel_arms_on_end_to_end(self):
        saved = pm.ensure_road
        try:
            for road in ROADS:
                pm.ensure_road = lambda road=road: (True, road)
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    pm.main(["ensure"])
                self.assertEqual(km._ensure_road(out.getvalue()) in km._BUS_OWNED_ROADS, road in pm.ENSURE_OWNED, road)
        finally:
            pm.ensure_road = saved


if __name__ == "__main__":
    unittest.main()
