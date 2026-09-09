#!/usr/bin/env python3
"""GET /models' Codex section says WHY it is empty, and the Codex gate's flip tells every picker (2026-09-09).
The owner's Codex picker opened on a blank menu while the session's default badge showed: /models carried
`codex: {models: []}` with no reason -- the backend's model_catalog() had answered [] (client not up, a failed
model_list, an empty page) or the handler's gate (a live Codex session, the Codex default backend, or the
Codex judge engine) was closed when the dashboard loaded, and nothing re-sent the models frame when the first
Codex session opened it. Now the section carries `error` in every empty state (the closed gate and an absent
backend name themselves, so the menu never reads an empty list as the app-server's answer), and the first
live Codex session fires the models frame the pick memory and the catalog fetch already send, through
EITHER door that opens the gate: the spawn (_create_codex_session_inner) and the revive of a dead session
(_revive_session_inner's Codex arm; the first cut covered the spawn alone, the round-1 verification). The
frame is keyed on the door's OWN before-snapshot of the gate (_codex_gate_closed), not on the live count read
after the row landed: two first creates or two first revives can interleave (a thread per POST /new, one per WS
client), and the post-count test saw 2 in both and fired for neither (the round-2 verification, executed with a
barrier); the snapshot fires both, once each when sequential. The backend is a FAKE here (no app-server, no
network); the handler runs in-process on a loopback ThreadingHTTPServer, the test_kernel_cors idiom. Synthetic
fixtures only.
"""
import http.client
import json
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest import mock
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
# Hermetic state BEFORE the loads -- they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
os.environ["ROMP_MODEL_CATALOG"] = "off"          # never the Models API from a test
km = load_source("romp_kernel_codex_models", os.path.join(BIN, "romp-kernel"))

SID = "11111111-2222-4333-8444-555555555555"
SID2 = "22222222-3333-4444-8555-666666666666"


class FakeCodex:
    """The slice of CodexBackend the /models handler, the spawn door and the revive door read. `dead`:
    sids the registry knows (a _session row) that are not live, the shape a revive starts from. `sids`:
    what successive spawns mint (the last one repeats). `barrier`: a threading.Barrier that spawn and
    resume wait on AFTER landing their row, so two doors driven from two threads both hold a live row
    before either reaches the gate check, the interleaving the real backend's tail (registry save,
    transcript touch, names write) leaves open."""

    def __init__(self, models=None, error=None, live=None, raise_catalog=None, dead=(), sids=(SID,), barrier=None):
        self.models, self.error, self.live = list(models or []), error, dict(live or {})
        self.raise_catalog = raise_catalog
        self.catalog_calls = 0
        self.dead = set(dead)
        self.sids, self.spawns = list(sids), 0
        self.barrier = barrier
        self._lock = threading.Lock()

    def live_sessions(self):
        return self.live

    def _session(self, sid):
        return object() if sid in self.live or sid in self.dead else None

    def _landed(self):
        if self.barrier is not None:
            self.barrier.wait()   # the other door's row is live too before this one checks the gate

    def resume(self, name, sid, cwd=None):
        with self._lock:
            if sid not in self.dead:
                return False
            self.dead.discard(sid)
            self.live[sid] = {"state": "waiting", "model": "gpt-5-test", "backend": "codex", "name": name}
        self._landed()
        return True

    def model_catalog(self):
        self.catalog_calls += 1
        if self.raise_catalog:
            raise self.raise_catalog
        return list(self.models)

    def model_catalog_error(self):
        return self.error

    def spawn(self, nm, cwd, bg, fg):
        with self._lock:
            sid = self.sids[min(self.spawns, len(self.sids) - 1)]
            self.spawns += 1
            self.live[sid] = {"state": "ready", "model": "gpt-5-test", "backend": "codex", "name": nm}
        self._landed()
        return sid


class ModelsRoute(unittest.TestCase):
    def setUp(self):
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self._saved = km._codex_backend

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        km._codex_backend = self._saved

    def _models(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request("GET", "/models", headers={"X-Romp-Token": km.TOKEN})
            r = conn.getresponse()
            self.assertEqual(r.status, 200)
            return json.loads(r.read())
        finally:
            conn.close()

    def test_a_live_codex_session_gets_the_backends_list_and_no_error(self):
        km._codex_backend = FakeCodex(models=[{"value": "gpt-5-test", "label": "GPT-5 Test"}],
                                      live={SID: {"backend": "codex"}})
        cx = self._models()["codex"]
        self.assertEqual(cx["models"], [{"value": "gpt-5-test", "label": "GPT-5 Test"}])
        self.assertIsNone(cx["error"])
        self.assertEqual([e["value"] for e in cx["efforts"]], ["low", "medium", "high", "xhigh"])

    def test_an_empty_list_carries_the_backends_reason(self):
        km._codex_backend = FakeCodex(models=[], error="model_list failed: app-server not ready",
                                      live={SID: {"backend": "codex"}})
        cx = self._models()["codex"]
        self.assertEqual(cx["models"], [])
        self.assertEqual(cx["error"], "model_list failed: app-server not ready")

    def test_a_raising_catalog_is_reported_not_swallowed(self):
        km._codex_backend = FakeCodex(raise_catalog=RuntimeError("pump died"), live={SID: {"backend": "codex"}})
        cx = self._models()["codex"]
        self.assertEqual(cx["models"], [])
        self.assertIn("pump died", cx["error"])

    def test_an_empty_list_with_no_recorded_reason_still_says_so(self):
        km._codex_backend = FakeCodex(models=[], error=None, live={SID: {"backend": "codex"}})
        self.assertEqual(self._models()["codex"]["error"], "the Codex app-server sent no model list")

    def test_the_closed_gate_consults_nothing_and_names_itself(self):
        # no live Codex session, Codex neither the default backend nor the judge engine: the backend is
        # not asked (asking would spawn the app-server on every dashboard load), and the reason says so.
        # The first cut sent no reason here, and the menu's fallback text then blamed the app-server for
        # a list it was never asked for (the round-1 verification).
        fake = FakeCodex(models=[{"value": "gpt-5-test", "label": "GPT-5 Test"}])
        km._codex_backend = fake
        cx = self._models()["codex"]
        self.assertEqual((cx["models"], cx["error"], fake.catalog_calls),
                         ([], "no live Codex session; the list is read once one runs", 0))

    def test_an_unavailable_backend_names_itself(self):
        km._codex_backend = False        # _codex(): the module failed to load, so every caller gets None
        cx = self._models()["codex"]
        self.assertEqual((cx["models"], cx["error"]),
                         ([], "the Codex backend is unavailable (see the kernel log)"))


class GateFlipFrame(unittest.TestCase):
    def setUp(self):
        self._saved = km._codex_backend
        self.got = []
        fakes = [{"app": app, "wid": "w-" + app, "alive": True,
                  "send": (lambda s, a=app: self.got.append((a, json.loads(s))))} for app in ("chat", "timeline", "feed")]
        with km._clients_lock:
            km._clients.extend(fakes)
        self._fakes = fakes

    def tearDown(self):
        km._codex_backend = self._saved
        with km._clients_lock:
            km._clients[:] = [c for c in km._clients if c not in self._fakes]

    def _frames(self):
        return [(a, f) for a, f in self.got if f.get("type") == "models"]

    def test_the_first_codex_session_sends_a_models_frame_and_the_second_does_not(self):
        fake = FakeCodex(models=[{"value": "gpt-5-test", "label": "GPT-5 Test"}])
        km._codex_backend = fake
        rev0 = km._models_rev[0]
        with mock.patch.object(km, "_push_session_now"), mock.patch.object(km, "_mark_views_dirty"):
            sid, extra = km._create_codex_session_inner("web", "/TESTDIR")
            self.assertEqual(sid, SID)
            frames = self._frames()
            self.assertEqual(sorted(a for a, _ in frames), ["chat", "feed", "timeline"],
                             "the gate flipped: one models frame to every app that hosts a picker")
            self.assertTrue(all(f["rev"] > rev0 for _, f in frames))
            self.got.clear()
            fake.spawn = lambda nm, cwd, bg, fg: "22222222-3333-4444-8555-666666666666"
            fake.live["22222222-3333-4444-8555-666666666666"] = {"backend": "codex"}
            km._create_codex_session_inner("api", "/TESTDIR")
            self.assertEqual(self._frames(), [], "a second session changes nothing the payload carries")

    def test_reviving_the_only_codex_session_sends_the_frame_and_a_second_revive_does_not(self):
        # The second door to a first live Codex session: a dead row made live again through cx.resume
        # (_revive_session_inner's Codex arm). A kernel restart that found every Codex session dead,
        # then a revive, flipped the gate with no frame from the first cut: every tab loaded in the
        # zero-live window kept an empty Codex list (the round-1 verification).
        fake = FakeCodex(models=[{"value": "gpt-5-test", "label": "GPT-5 Test"}], dead=[SID, SID2])
        km._codex_backend = fake
        rev0 = km._models_rev[0]
        focused, failed = [], []
        with mock.patch.object(km, "_sdk", lambda: None), \
             mock.patch.object(km, "_codex_ready", lambda: True), \
             mock.patch.object(km, "_name_of", lambda sid: "web"), \
             mock.patch.object(km, "_cwd_of", lambda sid: "/TESTDIR"), \
             mock.patch.object(km, "_commands_for_cwd", lambda cwd: None), \
             mock.patch.object(km, "_push_soon", lambda: None), \
             mock.patch.object(km, "_reveal_chat_for", lambda client, msg: focused.append(msg)), \
             mock.patch.object(km, "_send_to_view", lambda app, msg, wid: failed.append(msg)):
            km._revive_session_inner(SID, {"wid": "w-chat"})
            self.assertEqual(failed, [], "the revive succeeded")
            self.assertEqual(list(fake.live), [SID])
            frames = self._frames()
            self.assertEqual(sorted(a for a, _ in frames), ["chat", "feed", "timeline"],
                             "the gate flipped on the revive: one models frame to every app that hosts a picker")
            self.assertTrue(all(f["rev"] > rev0 for _, f in frames))
            self.assertEqual([m["type"] for m in focused], ["focus"], "and the asker's chat is focused as before")
            self.got.clear()
            km._revive_session_inner(SID2, {"wid": "w-chat"})
            self.assertEqual((failed, sorted(fake.live)), ([], sorted([SID, SID2])))
            self.assertEqual(self._frames(), [], "a second live session changes nothing the payload carries")

    # Two doors at once. POST /new runs on a thread per request and the WS create op per client, so two
    # first creates (a script's two `romp new` Codex sessions) can both land their rows before either
    # reaches the gate check; the same for two revives after a kernel restart that found every Codex
    # session dead. The frame used to key on `len(live_sessions()) == 1` read AFTER the row landed, so
    # both threads saw 2 and neither sent one: every open dashboard's Codex list stayed empty until the
    # chat's own open-time re-read, and the timeline lane never re-reads (the round-2 verification,
    # executed with this barrier). Keyed on each door's own before-snapshot, both fire. The assertion is
    # the SET of apps reached, not a frame count: two frames per app is the designed outcome here (each
    # a cheap re-read; the rev increments and the picker drops the lower), one is fine, zero is the bug.
    def _race(self, run, names):
        errs = []
        def go(n):
            try:
                run(n)
            except Exception as e:   # a thread's raise must fail the test, not vanish
                errs.append(e)
        ts = [threading.Thread(target=go, args=(n,)) for n in names]
        for t in ts:
            t.start()
        for t in ts:
            t.join(15)
        self.assertEqual(errs, [])
        self.assertFalse(any(t.is_alive() for t in ts), "a door never came back")

    def test_two_first_creates_that_race_both_send_the_frame(self):
        fake = FakeCodex(models=[{"value": "gpt-5-test", "label": "GPT-5 Test"}], sids=(SID, SID2),
                         barrier=threading.Barrier(2, timeout=10))
        km._codex_backend = fake
        rev0 = km._models_rev[0]
        with mock.patch.object(km, "_push_session_now"), mock.patch.object(km, "_mark_views_dirty"):
            self._race(lambda nm: km._create_codex_session_inner(nm, "/TESTDIR"), ("web", "api"))
        self.assertEqual(sorted(fake.live), sorted([SID, SID2]), "both creates landed")
        frames = self._frames()
        self.assertEqual(set(a for a, _ in frames), {"chat", "feed", "timeline"},
                         "two first creates raced: every app that hosts a picker still hears the gate open")
        self.assertTrue(all(f["rev"] > rev0 for _, f in frames))

    def test_two_first_revives_that_race_both_send_the_frame(self):
        fake = FakeCodex(models=[{"value": "gpt-5-test", "label": "GPT-5 Test"}], dead=[SID, SID2],
                         barrier=threading.Barrier(2, timeout=10))
        km._codex_backend = fake
        rev0 = km._models_rev[0]
        focused, failed = [], []
        with mock.patch.object(km, "_sdk", lambda: None), \
             mock.patch.object(km, "_codex_ready", lambda: True), \
             mock.patch.object(km, "_name_of", lambda sid: "web"), \
             mock.patch.object(km, "_cwd_of", lambda sid: "/TESTDIR"), \
             mock.patch.object(km, "_commands_for_cwd", lambda cwd: None), \
             mock.patch.object(km, "_push_soon", lambda: None), \
             mock.patch.object(km, "_reveal_chat_for", lambda client, msg: focused.append(msg)), \
             mock.patch.object(km, "_send_to_view", lambda app, msg, wid: failed.append(msg)):
            self._race(lambda sid: km._revive_session_inner(sid, {"wid": "w-chat"}), (SID, SID2))
        self.assertEqual((failed, sorted(fake.live)), ([], sorted([SID, SID2])), "both revives succeeded")
        self.assertEqual([m["type"] for m in focused], ["focus", "focus"])
        frames = self._frames()
        self.assertEqual(set(a for a, _ in frames), {"chat", "feed", "timeline"},
                         "two first revives raced: every app that hosts a picker still hears the gate open")
        self.assertTrue(all(f["rev"] > rev0 for _, f in frames))


if __name__ == "__main__":
    unittest.main()
