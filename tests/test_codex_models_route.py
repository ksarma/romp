#!/usr/bin/env python3
"""GET /models' Codex section says WHY it is empty. A Codex session's model picker opened on a blank menu
with no word of what was wrong: the route carried `codex: {models: []}` whenever the backend's
model_catalog() answered [] (the app-server client in its retry backoff, a model_list that raised, an
empty page) or raised (the handler swallowed the exception into the same empty list), and it carried the
same empty list on a dashboard where the Codex consult is gated off (no live Codex session, Codex neither
the default backend nor the judge engine) or where the backend module failed to load. The section now
carries `error`: null beside a non-empty list, else one sentence naming the reason, read from the
backend after an empty answer (model_catalog_error) or built from the raise (out of either call), and the
closed gate and an absent backend name themselves so an empty list is never read as the app-server's
answer. A raising catalog is logged once per distinct reason, and again when the same fault recurs after
the catalog answered: every picker open and every models frame re-reads the route.
The handler runs in-process on a loopback ThreadingHTTPServer (the test_kernel_cors idiom) over a FAKE
backend holding the slice the handler reads, and once over the REAL clientless backend so the sentence the
route serves is the backend's own. Synthetic fixtures only.
"""
import http.client
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest import mock
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
# Hermetic state BEFORE the loads: they resolve their state root at import time, and only pytest runs
# conftest's floor (a bare unittest or script run otherwise writes REAL state, and a kernel module that
# can reach a live manager port restarts the live kernel).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
os.environ["ROMP_MANAGER_PORT"] = "1"             # a dead port, never an inherited live one
os.environ["ROMP_MODEL_CATALOG"] = "off"          # never the Models API from a test
km = load_source("romp_kernel_codex_models", os.path.join(BIN, "romp-kernel"))
cb = load_source("romp_codex_backend_codex_models", os.path.join(ROOT, "kernel", "codex_backend.py"))

SID = "11111111-2222-4333-8444-555555555555"
MODELS = [{"value": "gpt-5-test", "label": "GPT-5 Test"}]


class FakeCodex:
    """The slice of CodexBackend the /models handler reads: the gate's row walk, the catalog, its reason."""

    def __init__(self, models=None, error=None, live=None, raise_catalog=None, raise_error=None):
        self.models, self.error, self.live = list(models or []), error, dict(live or {})
        self.raise_catalog, self.raise_error = raise_catalog, raise_error
        self.catalog_calls = 0

    def live_sessions(self):
        return self.live

    def model_catalog(self):
        self.catalog_calls += 1
        if self.raise_catalog:
            raise self.raise_catalog
        return list(self.models)

    def model_catalog_error(self):
        if self.raise_error:
            raise self.raise_error
        return self.error


class ModelsRoute(unittest.TestCase):
    def setUp(self):
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self._saved = km._codex_backend
        km._codex_backend = False        # every test picks its backend; none builds the real one by accident
        self._saved_fault = km._codex_catalog_fault[0]
        km._codex_catalog_fault[0] = None   # the once-per-reason latch starts clear whatever ran before

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        km._codex_backend = self._saved
        km._codex_catalog_fault[0] = self._saved_fault
        try:
            os.unlink(km.jd.STATE / "default-backend")
        except OSError:
            pass

    def _models(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request("GET", "/models", headers={"X-Romp-Token": km.TOKEN})
            r = conn.getresponse()
            self.assertEqual(r.status, 200)
            return json.loads(r.read())
        finally:
            conn.close()

    def _codex(self):
        d = self._models()
        self.assertIn("error", d["codex"], "the section always carries the field; null when the list is served")
        return d["codex"]

    def test_a_live_codex_session_gets_the_backends_list_and_no_error(self):
        km._codex_backend = FakeCodex(models=MODELS, live={SID: {"backend": "codex"}})
        cx = self._codex()
        self.assertEqual((cx["models"], cx["error"]), (MODELS, None))
        self.assertEqual([e["value"] for e in cx["efforts"]], ["low", "medium", "high", "xhigh"])

    def test_an_empty_list_carries_the_backends_reason(self):
        km._codex_backend = FakeCodex(models=[], error="model_list failed: app-server not ready",
                                      live={SID: {"backend": "codex"}})
        cx = self._codex()
        self.assertEqual((cx["models"], cx["error"]), ([], "model_list failed: app-server not ready"))

    def test_an_empty_list_with_no_recorded_reason_still_says_so(self):
        km._codex_backend = FakeCodex(models=[], error=None, live={SID: {"backend": "codex"}})
        cx = self._codex()
        self.assertEqual((cx["models"], cx["error"]), ([], "the Codex app-server sent no model list"))

    def test_a_raising_catalog_is_reported_not_swallowed(self):
        km._codex_backend = FakeCodex(raise_catalog=RuntimeError("pump died"), live={SID: {"backend": "codex"}})
        cx = self._codex()
        self.assertEqual((cx["models"], cx["error"]), ([], "model catalog: pump died"))

    def test_a_raise_out_of_the_reason_read_is_reported_too(self):
        # An empty list sends the handler to model_catalog_error(); a raise there is the same kind of
        # fault as a raise out of model_catalog() and takes the same sentence, never a swallowed None.
        km._codex_backend = FakeCodex(models=[], raise_error=RuntimeError("reason lost"),
                                      live={SID: {"backend": "codex"}})
        cx = self._codex()
        self.assertEqual((cx["models"], cx["error"]), ([], "model catalog: reason lost"))

    def test_a_raising_catalog_is_logged_once_per_distinct_reason(self):
        # The route is re-read on every picker open and every models frame, so a line per read repeats for
        # as long as the fault lasts: one line per distinct reason, and the SAME fault recurring after the
        # catalog answered in between is a new line (the answer clears the latch). A raise out of the
        # reason read is logged the same way.
        fake = FakeCodex(raise_catalog=RuntimeError("pump died"), live={SID: {"backend": "codex"}})
        km._codex_backend = fake
        err = io.StringIO()
        with mock.patch.object(sys, "stderr", err):
            self._codex()
            self._codex()
            fake.raise_catalog = RuntimeError("app-server not ready")
            self._codex()
            self._codex()
            fake.raise_catalog = None
            fake.models = list(MODELS)
            self.assertEqual(self._codex()["error"], None)
            fake.raise_catalog = RuntimeError("app-server not ready")
            self._codex()
            fake.raise_catalog, fake.models = None, []
            fake.raise_error = RuntimeError("reason lost")
            self._codex()
            self._codex()
        lines = [l for l in err.getvalue().splitlines() if "model catalog" in l]
        self.assertEqual(lines, ["codex-backend: model catalog: pump died",
                                 "codex-backend: model catalog: app-server not ready",
                                 "codex-backend: model catalog: app-server not ready",
                                 "codex-backend: model catalog: reason lost"])

    def test_the_closed_gate_consults_nothing_and_names_itself(self):
        # No live Codex session, Codex neither the default backend nor the judge engine: the backend is not
        # asked (asking would spawn the app-server on every dashboard load), and the reason says so rather
        # than leaving an empty list that reads as the app-server's answer.
        fake = FakeCodex(models=MODELS)
        km._codex_backend = fake
        cx = self._codex()
        self.assertEqual((cx["models"], cx["error"], fake.catalog_calls),
                         ([], "no live Codex session; the list is read once one runs", 0))

    def test_the_codex_default_backend_opens_the_gate_without_a_live_session(self):
        fake = FakeCodex(models=MODELS)
        km._codex_backend = fake
        km.jd.STATE.mkdir(parents=True, exist_ok=True)
        (km.jd.STATE / "default-backend").write_text("codex\n")
        cx = self._codex()
        self.assertEqual((cx["models"], cx["error"], fake.catalog_calls), (MODELS, None, 1))

    def test_an_unavailable_backend_names_itself(self):
        km._codex_backend = False        # _codex(): the module failed to load, so every caller gets None
        cx = self._codex()
        self.assertEqual((cx["models"], cx["error"]), ([], "the Codex backend is unavailable (see the kernel log)"))

    def test_the_real_backends_reason_rides_the_route(self):
        # The real backend, clientless: the client factory fails as a missing `codex login` does, so
        # model_catalog() answers [] with the client's failure as the reason, and the route serves that
        # sentence, not the fallback. The gate is opened by the machine default rather than a live row.
        be = cb.CodexBackend(tempfile.mkdtemp(), log=lambda m: None,
                             client_factory=lambda: (_ for _ in ()).throw(RuntimeError("codex login missing")))
        km._codex_backend = be
        km.jd.STATE.mkdir(parents=True, exist_ok=True)
        (km.jd.STATE / "default-backend").write_text("codex\n")
        cx = self._codex()
        self.assertEqual((cx["models"], cx["error"]),
                         ([], "the Codex app-server client is unavailable: codex login missing"))


class _ReviveFake(FakeCodex):
    """FakeCodex plus what the revive door reads: the registry lookup (_session) and resume. `dead` holds the
    sids the registry knows that are not live; like the real backend's, resume answers True for any known
    sid, landing a dead one and leaving a live one as it is."""

    def __init__(self, dead=(), **kw):
        super().__init__(**kw)
        self.dead = set(dead)

    def _session(self, sid):
        return object() if (sid in self.live or sid in self.dead) else None

    def resume(self, name, sid, cwd=None):
        if sid in self.dead:
            self.dead.discard(sid)
            self.live[sid] = {"backend": "codex", "state": "waiting", "name": name}
            return True
        return sid in self.live


def _revive_patched(focused, failed):
    """_revive_session_inner's neighbours, stubbed: no SDK backend, a ready Codex client, a known name and
    cwd, no command pre-warm, no pusher; the asker's focus lands in `focused`, and every view send in
    `failed` as (app, wid, message). A failed revive sends one reviveFailed to the asking dashboard's chat
    AND feed (the feed's parked card latched Revive on the click and re-arms on the reply for its own sid),
    so the app is part of what a test pins."""
    return mock.patch.multiple(km, _sdk=lambda: None, _codex_ready=lambda: True, _name_of=lambda sid: "web",
                               _cwd_of=lambda sid: "/TESTDIR", _commands_for_cwd=lambda cwd: None,
                               _push_soon=lambda: None,
                               _reveal_chat_for=lambda client, msg: focused.append(msg),
                               _send_to_view=lambda app, msg, wid: failed.append((app, wid, msg)))


class OneFrameOnRevive(unittest.TestCase):
    """The revive door sends exactly ONE models frame per picker app when a Codex row lands. The door calls
    _models_changed() once per landing (every landing, not only the closed-to-open flip: a door cannot see the
    flip by itself, and a repeated frame costs one GET /models per open picker, reconciled by the payload's
    rev). That design superseded an earlier gate-flip helper the same door ran from a finally beside the
    resume, and a merge that carried both left the revive door with two senders side by side: two frames per
    app per revive. tests/test_codex_models_frame.py pins the SET of apps reached through a sorted-list
    equality; this class pins the COUNT by name, over a fake and over the REAL clientless backend, and the
    rev counter's single step, so a second sender at the door fails a test that says so. One fake WS client
    per app that hosts a picker sits in the kernel's client list; a send records (app, frame)."""

    APPS = ("chat", "timeline", "feed")

    def setUp(self):
        self._saved = km._codex_backend
        self.got = []
        self._fakes = [{"app": app, "wid": "w-" + app, "alive": True,
                        "send": (lambda s, a=app: self.got.append((a, json.loads(s))))} for app in self.APPS]
        with km._clients_lock:
            km._clients.extend(self._fakes)

    def tearDown(self):
        km._codex_backend = self._saved
        with km._clients_lock:
            km._clients[:] = [c for c in km._clients if not any(c is f for f in self._fakes)]

    def _frame_counts(self):
        counts = {app: 0 for app in self.APPS}
        for app, f in self.got:
            if f.get("type") == "models":
                counts[app] += 1
        return counts

    def _revive(self, sid):
        focused, failed = [], []
        with _revive_patched(focused, failed), \
             mock.patch.object(km, "_push_session_now"), mock.patch.object(km, "_mark_views_dirty"):
            km._revive_session_inner(sid, {"wid": "w-chat"})
        return focused, failed

    def test_reviving_a_dead_codex_session_sends_exactly_one_frame_per_picker_app(self):
        fake = _ReviveFake(dead=(SID,), models=MODELS)
        km._codex_backend = fake
        rev0 = km._models_rev[0]
        focused, failed = self._revive(SID)
        self.assertEqual((failed, [m["type"] for m in focused], sorted(fake.live), fake.dead),
                         ([], ["focus"], [SID], set()), "the revive landed the row and focused the asker")
        self.assertEqual(self._frame_counts(), {"chat": 1, "timeline": 1, "feed": 1},
                         "one models frame per picker app, never two: %r" % (self.got,))
        self.assertTrue(all(f["rev"] > rev0 for _, f in self.got), "every frame carries the moved rev")
        self.assertEqual(km._models_rev[0], rev0 + 1, "the rev stepped once: one _models_changed() per landing")

    def test_the_real_backends_revive_sends_exactly_one_frame_per_picker_app(self):
        # The REAL CodexBackend, clientless (client_factory answers None: no app-server, no network) on a
        # private state dir: a spawn lands a live launch-error row as it does in the kernel, kill retires it,
        # and the door's resume flips it live again through the backend's own registry.
        td = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, td, True)
        be = cb.CodexBackend(td, client_factory=lambda: None, log=lambda m: None)
        km._codex_backend = be
        g = be.spawn("web", "/TESTDIR")
        self.assertTrue(be.kill(g))
        self.assertEqual(be.live_sessions(), {}, "the only row died")
        rev0 = km._models_rev[0]
        focused, failed = self._revive(g)
        self.assertEqual((failed, [m["type"] for m in focused], list(be.live_sessions())), ([], ["focus"], [g]),
                         "the real door over the real backend: the row is live again and the asker is focused")
        self.assertEqual(self._frame_counts(), {"chat": 1, "timeline": 1, "feed": 1},
                         "one frame per picker app from the real door: %r" % (self.got,))
        self.assertEqual(km._models_rev[0], rev0 + 1, "the rev stepped once")


if __name__ == "__main__":
    unittest.main()
