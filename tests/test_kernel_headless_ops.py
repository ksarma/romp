#!/usr/bin/env python3
"""Kernel half of the SDK-lifecycle hardening (2026-07-05):

  * parked-ops persistence — _pending_ops mirrors to pending-ops.json on every mutation and is
    restored at boot, so a kernel restart can't silently drop messages the user queued against a
    busy session;
  * POST /interrupt + /end — the headless control routes mirroring the WS drive ops (before this a
    session could be FED without a browser but never STOPPED);
  * wiring pins — main() installs the SIGTERM drain handler and constructs the SDK backend eagerly
    with reconcile=True (source-pinned, same style as test_sdk_kernel's dispatch pins);
  * _sdk() single-flight — the eager boot thread races handler threads, and an unlocked
    check-then-act built 2-3 duplicate SdkBackends whose reconciles reaped each other's live CLIs
    (2026-07-06 kill storm: sessions dying with exit 143 mid-turn).

XDG_STATE_HOME is pointed at a temp dir BEFORE the kernel module loads, so jd.STATE — and with it
pending-ops.json and every state write — stays out of the live user state (see
[[distiller-giveup-rearm]]: leaking test state into ~/.local/state/romp corrupts live behavior).
"""
import json
import os
import tempfile
import unittest
from unittest import mock
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
_STATE_TMP = tempfile.mkdtemp()
os.environ["XDG_STATE_HOME"] = _STATE_TMP
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
km = load_source("romp_kernel_headless", os.path.join(BIN, "romp-kernel"))

# The ACCOUNT gate (_limit_hold: a usage limit / monthly spend cap parks every drive op, tested in
# tests/test_kernel_limit_queue.py) is a SEPARATE axis from the compaction/busy gates this module
# covers. Neutralize it here: left live, these tests would read the REAL machine's usage.json and
# start parking — correctly, but for a reason none of them is about — the moment that account hit a
# limit. Pinning it off keeps them hermetic.
km._limit_hold = lambda sid: None

# The tmux PROMPT HOLD (_hold_drain: a tmux-shaped delivery holds the sid for a moment, tested in
# tests/test_kernel_parked_ops_liveness.py) is a separate axis: off here, so back-to-back
# _apply_pending_ops calls stand for successive cycles.
km._TMUX_PROMPT_HOLD_S = 0.0


class PendingOpsPersistence(unittest.TestCase):
    def setUp(self):
        km._pending_ops.clear()
        try:
            os.unlink(km._PENDING_OPS_FILE)
        except OSError:
            pass

    def test_state_dir_is_isolated(self):
        self.assertTrue(str(km._PENDING_OPS_FILE).startswith(_STATE_TMP),
                        "the test must never write the live pending-ops.json")

    def test_park_mirrors_to_disk_and_reload_restores(self):
        km._park_op("sid-1", ("send", "queued while busy", "human"))
        km._park_op("sid-1", ("model", "opus"))
        km._park_op("sid-1", ("model", "sonnet"))     # replace-in-place also persists
        on_disk = json.loads(km._PENDING_OPS_FILE.read_text())
        self.assertEqual(on_disk, {"sid-1": [["send", "queued while busy", "human"],
                                             ["model", "sonnet"]]})
        # a fresh kernel's boot path restores the same queues, as tuples
        self.assertEqual(km._load_pending_ops(),
                         {"sid-1": [("send", "queued while busy", "human"), ("model", "sonnet")]})

    def test_delivery_shrinks_the_disk_mirror(self):
        km._park_op("sid-2", ("effort", "high"))
        fake = mock.Mock()
        with mock.patch.object(km, "_compacting_now", return_value=False), \
             mock.patch.object(km, "_working_now", return_value=False), \
             mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)):
            km._apply_pending_ops()
        fake.set_effort.assert_called_once_with("sid-2", "high")
        self.assertEqual(km._load_pending_ops(), {}, "a delivered op leaves the disk mirror")

    def test_missing_file_loads_empty(self):
        self.assertEqual(km._load_pending_ops(), {})


# The sids these route tests address. The routes refuse a target the kernel has never heard of
# (UnknownSessionRefused below), so each is registered in the hermetic names registry: known to the
# kernel, not live, exactly the shape of a session between turns or dormant.
KNOWN_SIDS = {"runaway": "runaway", "sid-x": "web", "sid-q": "web", "sid-m": "web", "sid-r": "web"}


def _register(sid, name):
    km.NAMES.mkdir(parents=True, exist_ok=True)
    (km.NAMES / sid).write_text("%s\t\n" % name)


def _unregister(sid):
    try:
        (km.NAMES / sid).unlink()
    except OSError:
        pass


class _RouteServer(unittest.TestCase):
    """The REAL handler on loopback (the ServeSecurity pattern) with KNOWN_SIDS registered; no tests of its
    own, so a class that needs the server inherits the fixture and not the other class's tests."""

    @classmethod
    def setUpClass(cls):
        import threading
        from http.server import ThreadingHTTPServer
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        for sid, name in KNOWN_SIDS.items():
            _register(sid, name)

    def tearDown(self):
        for sid in KNOWN_SIDS:
            _unregister(sid)

    def _post(self, path, body):
        import urllib.request, urllib.error
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path),
                                     method="POST", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json",
                                              "X-Romp-Token": km.TOKEN})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode() or "{}")


class HeadlessRoutes(_RouteServer):
    """POST /interrupt and /end over the REAL handler on loopback (the ServeSecurity pattern)."""

    def test_interrupt_route_mirrors_the_ws_op(self):
        fake = mock.Mock()
        with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)):
            code, resp = self._post("/interrupt", {"name": "runaway"})
        self.assertEqual((code, resp), (200, {"ok": True}))
        fake.interrupt.assert_called_once()
        sid = fake.interrupt.call_args[0][0]
        self.assertIn(str(sid), km._interrupt_clicked,
                      "the chat chip flips to 'interrupting' exactly like the WS op")

    def test_end_route_kills_and_announces_close(self):
        fake = mock.Mock()
        sent = []
        with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
             mock.patch.object(km, "_send_to_app", side_effect=lambda app, m: sent.append((app, m))):
            code, resp = self._post("/end", {"id": "sid-x"})
        self.assertEqual((code, resp), (200, {"ok": True}))
        fake.kill.assert_called_once()
        self.assertIn(("chat", {"type": "closed", "id": fake.kill.call_args[0][0]}), sent)

    def test_send_route_reports_queued_vs_sent(self):
        # `queued` says which arm the send took (2026-09-03): an agent sending ITSELF a slash command from
        # inside its own turn read 'ok' and could not know the command was parked until that turn ended
        fake = mock.Mock()
        fake.busy.return_value = None
        km._pending_ops.clear()
        try:
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km, "_compacting_now", lambda sid, **k: False), \
                 mock.patch.object(km, "_working_now", lambda sid: True):
                code, resp = self._post("/send", {"id": "sid-q", "text": "/frobnicate now"})
            self.assertEqual((code, resp), (200, {"ok": True, "queued": True}))
            self.assertEqual(list(km._pending_ops.values()), [[("command", "/frobnicate now", None)]])
            fake.send.assert_not_called()
            km._pending_ops.clear()
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km, "_compacting_now", lambda sid, **k: False), \
                 mock.patch.object(km, "_working_now", lambda sid: False):
                code, resp = self._post("/send", {"id": "sid-q", "text": "/frobnicate now"})
            self.assertEqual((code, resp), (200, {"ok": True, "queued": False}))
            fake.send.assert_called_once()
            self.assertEqual(fake.send.call_args[0][1], "/frobnicate now")
        finally:
            km._pending_ops.clear()

    def test_send_route_reports_a_parked_meta_command_as_queued(self):
        # /model, /effort and /fast take the kernel's own setters (_route_meta_command), which park under
        # the same gate as a text send — the route must say `queued` for them too (review find, 2026-09-03)
        fake = mock.Mock()
        fake.busy.return_value = None
        km._pending_ops.clear()
        try:
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km, "_compacting_now", lambda sid, **k: False), \
                 mock.patch.object(km, "_working_now", lambda sid: True):
                code, resp = self._post("/send", {"id": "sid-m", "text": "/effort high"})
            self.assertEqual((code, resp), (200, {"ok": True, "queued": True}))
            self.assertEqual(list(km._pending_ops.values()), [[("effort", "high")]], "parked as the setter's op")
            fake.set_effort.assert_not_called()
            km._pending_ops.clear()
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km, "_compacting_now", lambda sid, **k: False), \
                 mock.patch.object(km, "_working_now", lambda sid: False):
                code, resp = self._post("/send", {"id": "sid-m", "text": "/effort high"})
            self.assertEqual((code, resp), (200, {"ok": True, "queued": False}))
            fake.set_effort.assert_called_once()
        finally:
            km._pending_ops.clear()

    def test_send_route_reads_the_setters_locked_verdict_not_a_second_gate(self):
        # #954 moved the deciding park under the queue lock (_gate_or_park); the route must report the
        # setter's OWN verdict, not a separate unlocked _ops_gate read that can disagree (review find on
        # #954, 2026-09-07: a parked /model answered queued:false). Force the two apart: _gate_or_park
        # parks (True) while _ops_gate reads False.
        fake = mock.Mock(); fake.busy.return_value = None
        km._pending_ops.clear()
        try:
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km, "_ops_gate", lambda sid: False), \
                 mock.patch.object(km, "_gate_or_park", lambda sid, op: (km._pending_ops.setdefault(str(sid), []).append(op) or True)):
                code, resp = self._post("/send", {"id": "sid-x", "text": "/model sonnet"})
            self.assertEqual((code, resp), (200, {"ok": True, "queued": True}),
                             "the route reports the setter's locked park, not the unlocked gate")
            fake.set_model.assert_not_called()
        finally:
            km._pending_ops.clear()

    def test_send_route_passes_a_remote_kernels_queued_through(self):
        # a session living on another kernel: its answer's `queued` rides back to the caller; an older
        # remote without the field reads as not queued (today's behaviour)
        # the arm reads the status beside the body (_remote_forward_status), so that is the seam patched
        with mock.patch.object(km, "_host_for_sid", lambda sid: {"host": "TESTHOST"}), \
             mock.patch.object(km, "_remote_forward_status", lambda r, path, body, method="POST": (200, {"ok": True, "queued": True})):
            code, resp = self._post("/send", {"id": "sid-r", "text": "/frobnicate now"})
        self.assertEqual((code, resp), (200, {"ok": True, "queued": True}))
        with mock.patch.object(km, "_host_for_sid", lambda sid: {"host": "TESTHOST"}), \
             mock.patch.object(km, "_remote_forward_status", lambda r, path, body, method="POST": (200, {"ok": True})):
            code, resp = self._post("/send", {"id": "sid-r", "text": "hello"})
        self.assertEqual((code, resp), (200, {"ok": True, "queued": False}))
        # …and a far kernel's REFUSAL rides back as itself, never rewritten into an ok (review find, #904)
        refusal = {"ok": False, "error": "isolation: the target session's mailbox is OFF"}
        with mock.patch.object(km, "_host_for_sid", lambda sid: {"host": "TESTHOST"}), \
             mock.patch.object(km, "_remote_forward_status", lambda r, path, body, method="POST": (200, dict(refusal))):
            code, resp = self._post("/send", {"id": "sid-r", "text": "hello"})
        self.assertEqual((code, resp), (200, refusal))

    def test_missing_who_is_a_400(self):
        code, resp = self._post("/interrupt", {})
        self.assertEqual(code, 400)
        self.assertFalse(resp.get("ok"))


# a comment thread as the kernel keeps it (the tests/test_thread_rows.py shape): a row in the parent's
# comments store and an SDK reg carrying threadOf, no names/ entry of its own. Synthetic uuids only.
THREAD_PARENT = "11111111-2222-3333-4444-555555555555"
THREAD_TSID = "66666666-7777-8888-9999-000000000000"
THREAD_NAME = "web-comment-1"


def _mk_thread(parent, tsid, name):
    cdir = km.jd.STATE / "comments"
    cdir.mkdir(parents=True, exist_ok=True)
    row = {"tid": tsid, "sid": tsid, "name": name, "status": "open", "createdT": 1, "lastSeenT": 1}
    (cdir / (parent + ".json")).write_text(json.dumps({"threads": [row]}))
    sdir = km.jd.STATE / "sdk"
    sdir.mkdir(parents=True, exist_ok=True)
    reg = {"sid": tsid, "cwd": "/tmp", "alive": True, "threadOf": parent, "lastSid": tsid, "name": name}
    (sdir / (tsid + ".json")).write_text(json.dumps(reg))


def _rm_thread(parent, tsid):
    for f in (km.jd.STATE / "comments" / (parent + ".json"), km.jd.STATE / "sdk" / (tsid + ".json")):
        try:
            f.unlink()
        except OSError:
            pass


class UnknownSessionRefused(_RouteServer):
    """A name (or id) that resolves to no session is a 404 naming it, on /end, /interrupt and /send
    alike. _sid_of falls back to its input unchanged, so a typo used to mint a phantom sid: /end
    "killed" it, _confirmed_ended found nothing listed and certified the death, and `romp end <typo>`
    printed a bare ok while the real session kept running; /send handed the phantom to the tmux
    backend, whose refusal the route folded into ok:true. A caller that trusted those oks had to
    re-check the roster to learn nothing had happened. Three doors admit a sid: the names registry, the
    live map, and the SDK registry's threadOf (a comment thread has neither of the first two). A
    registered-but-idle sid still passes, so a dead session addressed by id keeps its idempotent end.
    The gate is asked with the live map _resolve_sid already read, so the refusal path scans once."""

    GHOST = "no-such-session"

    def _assert_404(self, code, resp):
        self.assertEqual(code, 404, "an unknown session is a 404, not an ok")
        self.assertFalse(resp.get("ok"))
        self.assertIn(self.GHOST, resp.get("error", ""), "the reason names the unknown name")

    def test_end_of_an_unknown_name_is_a_404_and_kills_nothing(self):
        fake = mock.Mock()
        sent, deaths = [], []
        with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
             mock.patch.object(km, "_send_to_app", side_effect=lambda app, m: sent.append((app, m))), \
             mock.patch.object(km, "_record_death", side_effect=lambda sid, t, kind: deaths.append(sid)):
            code, resp = self._post("/end", {"name": self.GHOST})
        self._assert_404(code, resp)
        fake.kill.assert_not_called()
        self.assertEqual(deaths, [], "no death record for a session that never existed")
        self.assertEqual(sent, [], "no closed broadcast either")

    def test_end_when_idle_of_an_unknown_name_records_no_wish(self):
        code, resp = self._post("/end", {"name": self.GHOST, "when": "idle"})
        self._assert_404(code, resp)
        self.assertNotIn(self.GHOST, km._end_on_idle_load(), "nothing to defer for a phantom")

    def test_interrupt_of_an_unknown_name_is_a_404_and_touches_nothing(self):
        fake = mock.Mock()
        with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)):
            code, resp = self._post("/interrupt", {"name": self.GHOST})
        self._assert_404(code, resp)
        fake.interrupt.assert_not_called()
        self.assertNotIn(self.GHOST, km._interrupt_clicked, "no chip flip for a phantom")

    def test_send_to_an_unknown_name_is_a_404_and_delivers_nothing(self):
        fake = mock.Mock()
        fake.busy.return_value = None
        km._pending_ops.clear()
        try:
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km, "_compacting_now", lambda sid, **k: False), \
                 mock.patch.object(km, "_working_now", lambda sid: False):
                code, resp = self._post("/send", {"name": self.GHOST, "text": "hello"})
            self._assert_404(code, resp)
            fake.send.assert_not_called()
            self.assertEqual(km._pending_ops, {}, "nothing parked for a phantom")
        finally:
            km._pending_ops.clear()

    def test_an_unknown_id_is_refused_the_same_way(self):
        fake = mock.Mock()
        with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)):
            code, resp = self._post("/end", {"id": self.GHOST})
        self._assert_404(code, resp)
        fake.kill.assert_not_called()

    def test_a_live_unregistered_sid_still_resolves_by_id(self):
        # the gate must not refuse a session that is live but not yet in the registry snapshot: the
        # existing tests cover registered-not-live; this covers live-not-registered, which is reachable
        # only by id (no registry entry, so no name)
        fake = mock.Mock()
        _unregister("sid-x")
        with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
             mock.patch.object(km.Sessions, "live", staticmethod(lambda: {"sid-x": {}})):
            code, resp = self._post("/interrupt", {"id": "sid-x"})
        self.assertEqual((code, resp), (200, {"ok": True}))
        fake.interrupt.assert_called_once()

    def test_a_live_name_is_gated_on_the_sid_it_resolves_to(self):
        # `romp end web`: the name resolves through _live_names to a differently spelled sid, and the gate
        # must read THAT sid, not the caller's spelling. setUp registers sid-x as "web"; "web" itself has
        # no registry entry and is in no live map, so a gate on `who` refuses it while a gate on `sid`
        # admits it (review find, 2026-09-09: no test posted by a name that resolved to another spelling)
        fake = mock.Mock()
        with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
             mock.patch.object(km.Sessions, "live", staticmethod(lambda: {"sid-x": {}})):
            code, resp = self._post("/interrupt", {"name": "web"})
        self.assertEqual((code, resp), (200, {"ok": True}))
        fake.interrupt.assert_called_once_with("sid-x")

    def test_a_comment_thread_passes_the_gate_by_name_and_by_id(self):
        # a comment thread has no names/ entry (sdk_backend.fork withholds it) and live_sessions skips
        # threadOf regs, while _sid_of resolves its name to its tsid on purpose (T223). A gate of names +
        # live alone answered 404 to every thread, by name and by id, so /send, /interrupt and /end never
        # reached the backend, and `romp end self` from inside a thread (ROMP_SID = the tsid) was refused
        # (review find, 2026-09-09). The third door reads the SDK reg's threadOf.
        fake = mock.Mock()
        fake.busy.return_value = None
        _register(THREAD_PARENT, "web-parent")
        _mk_thread(THREAD_PARENT, THREAD_TSID, THREAD_NAME)
        km._pending_ops.clear()
        deaths, sent = [], []
        try:
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km.Sessions, "live", staticmethod(lambda: {})), \
                 mock.patch.object(km, "_compacting_now", lambda sid, **k: False), \
                 mock.patch.object(km, "_working_now", lambda sid: False):
                code, resp = self._post("/send", {"name": THREAD_NAME, "text": "hello"})
                self.assertEqual((code, resp), (200, {"ok": True, "queued": False}), "by name")
                self.assertEqual(fake.send.call_args[0][:2], (THREAD_TSID, "hello"))
                code, resp = self._post("/send", {"id": THREAD_TSID, "text": "again"})
                self.assertEqual((code, resp), (200, {"ok": True, "queued": False}), "by id")
                self.assertEqual(fake.send.call_count, 2)
                code, resp = self._post("/interrupt", {"id": THREAD_TSID})
                self.assertEqual((code, resp), (200, {"ok": True}))
                fake.interrupt.assert_called_once_with(THREAD_TSID)
                # `romp end self` from inside the thread: /end {id: tsid, when: idle}, and the same by name
                code, resp = self._post("/end", {"id": THREAD_TSID, "when": "idle"})
                self.assertEqual((code, resp), (200, {"ok": True, "deferred": True}))
                self.assertIn(THREAD_TSID, km._end_on_idle_load(), "the wish is recorded for the tsid")
                code, resp = self._post("/end", {"name": THREAD_NAME, "when": "idle"})
                self.assertEqual((code, resp), (200, {"ok": True, "deferred": True}))
                # an immediate /end reaches the backend's kill on the tsid
                with mock.patch.object(km, "_confirmed_ended", lambda sid: True), \
                     mock.patch.object(km, "_record_death", side_effect=lambda sid, t, kind: deaths.append(sid)), \
                     mock.patch.object(km, "_comment_kill_all", lambda sid, be: None), \
                     mock.patch.object(km, "_send_to_app", side_effect=lambda app, m: sent.append((app, m))):
                    code, resp = self._post("/end", {"id": THREAD_TSID})
                self.assertEqual((code, resp), (200, {"ok": True}))
                fake.kill.assert_called_once_with(THREAD_TSID)
                self.assertEqual(deaths, [THREAD_TSID])
                # a name that is NOT a thread still falls through to the 404
                code, resp = self._post("/interrupt", {"name": self.GHOST})
                self._assert_404(code, resp)
        finally:
            km._pending_ops.clear()
            km._end_on_idle_save(km._end_on_idle_load() - {THREAD_TSID})
            _rm_thread(THREAD_PARENT, THREAD_TSID)
            _unregister(THREAD_PARENT)

    def test_the_refusal_path_scans_the_live_map_once(self):
        # _sid_of scans Sessions.live() once the names registry misses; a gate that scanned again forked
        # tmux and walked the SDK regs twice per refused request. The routes hand the gate the map the
        # resolution read (review find, 2026-09-09)
        scans = []
        with mock.patch.object(km.Sessions, "live", staticmethod(lambda: scans.append(1) or {})), \
             mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: mock.Mock())):
            for path, body in (("/end", {"name": self.GHOST}), ("/interrupt", {"name": self.GHOST}),
                               ("/send", {"name": self.GHOST, "text": "hello"})):
                del scans[:]
                code, resp = self._post(path, body)
                self._assert_404(code, resp)
                self.assertEqual(len(scans), 1, "%s scanned the live map %d times" % (path, len(scans)))

    def test_a_remote_session_forwards_before_the_gate(self):
        # a session living on another kernel is in neither the local registry nor the local live map;
        # the remote map owns it and the request must forward, never 404 here
        with mock.patch.object(km, "_host_for_sid", lambda sid: {"host": "TESTHOST"}), \
             mock.patch.object(km, "_remote_forward_status", lambda r, path, body, method="POST": (200, {"ok": True})):
            code, resp = self._post("/end", {"id": self.GHOST})
        self.assertEqual((code, resp), (200, {"ok": True}))

    def test_a_remote_kernels_404_is_relayed_as_a_404_with_its_reason(self):
        # the far kernel's own gate answers 404; _remote_forward_status keeps a 200's body only, so the
        # arms used to read (404, None) as None and say "isn't answering" (the tunnel fault). The 404 is
        # relayed as a 404 naming the session and the host; a dead tunnel (status 0) keeps the tunnel
        # text; any other answered non-200 names the host and the status (review find, 2026-09-09)
        remote = {"host": "TESTHOST"}
        for path, body in (("/end", {"id": self.GHOST}), ("/interrupt", {"id": self.GHOST}),
                           ("/send", {"id": self.GHOST, "text": "hello"})):
            with mock.patch.object(km, "_host_for_sid", lambda sid: remote), \
                 mock.patch.object(km, "_remote_forward_status", lambda r, p, b, method="POST": (404, None)):
                code, resp = self._post(path, body)
            self.assertEqual(code, 404, path)
            self.assertFalse(resp.get("ok"))
            self.assertIn(self.GHOST, resp.get("error", ""), path)
            self.assertIn("TESTHOST", resp.get("error", ""), path)
            self.assertNotIn("isn't answering", resp.get("error", ""), path)
            with mock.patch.object(km, "_host_for_sid", lambda sid: remote), \
                 mock.patch.object(km, "_remote_forward_status", lambda r, p, b, method="POST": (0, None)):
                code, resp = self._post(path, body)
            self.assertEqual(code, 200, path)
            self.assertIn("isn't answering", resp.get("error", ""), path)
            with mock.patch.object(km, "_host_for_sid", lambda sid: remote), \
                 mock.patch.object(km, "_remote_forward_status", lambda r, p, b, method="POST": (503, None)):
                code, resp = self._post(path, body)
            self.assertEqual(code, 200, path)
            self.assertFalse(resp.get("ok"))
            self.assertIn("HTTP 503", resp.get("error", ""), path)
            self.assertIn("TESTHOST", resp.get("error", ""), path)


class CodexRuntimeSelection(unittest.TestCase):
    # The kernel loads codex_backend.py through load_source (kernel/loadsource.py), the fork's loader kept
    # over upstream's SourceFileLoader.load_module() in the 2026-09-07 fold (a standing fork ruling): patch that.
    def test_path_codex_does_not_override_managed_runtime(self):
        fake_mod = mock.Mock()
        with mock.patch.object(km, "_codex_backend", None), \
             mock.patch.object(km, "load_source", return_value=fake_mod), \
             mock.patch.object(km.shutil, "which", return_value="/TESTBIN/codex"):
            backend = km._codex()
            self.assertIs(backend, fake_mod.CodexBackend.return_value)
            self.assertIs(km._codex(), backend)
        fake_mod.CodexBackend.assert_called_once()
        self.assertIsNone(fake_mod.CodexBackend.call_args.kwargs.get("codex_bin"),
                          "the backend must resolve its managed runtime even when codex is on PATH")

    def test_romp_codex_bin_overrides_the_session_runtime(self):
        # PATH is ignored, but the one explicit knob the judges already read (ROMP_CODEX_BIN) governs
        # sessions too — an opt-in, not the ambient PATH accident #929 closed (review fold, 2026-09-07)
        fake_mod = mock.Mock()
        with mock.patch.object(km, "_codex_backend", None), \
             mock.patch.object(km, "load_source", return_value=fake_mod), \
             mock.patch.dict(km.os.environ, {"ROMP_CODEX_BIN": "/opt/codex/bin/codex"}), \
             mock.patch.object(km.shutil, "which", return_value="/TESTBIN/codex"):
            km._codex()
        self.assertEqual(fake_mod.CodexBackend.call_args.kwargs.get("codex_bin"), "/opt/codex/bin/codex",
                         "the explicit knob is forwarded; PATH is still not")


class SdkSingleFlight(unittest.TestCase):
    """Concurrent _sdk() calls must construct exactly ONE backend. The 2026-07-06 storm: the eager
    boot thread + handler threads each passed the unlocked `if _sdk_backend is None` check and built
    their own SdkBackend; every duplicate ran its own boot reconcile, and each reconcile reaped the
    others' freshly-resumed LIVE CLIs (no ppid filter then), killing sessions mid-turn."""

    def test_concurrent_calls_build_one_backend(self):
        import threading
        built = []
        gate = threading.Event()

        class FakeBackend:
            def __init__(self):
                gate.wait(2)                       # hold construction open so every racer arrives
                built.append(self)

        fake_mod = mock.Mock()
        fake_mod.SdkBackend = lambda *a, **k: FakeBackend()
        prev = km._sdk_backend
        # _sdk_locked wires the loaded module's readers into the SHARED romp_judge module (jd._LOGIN_AUTH_ENV_FN
        # and its siblings, jd._UNPICKED_AUTH_FN and jd._USAGE_REFRESH_FN included; the key wires went with
        # romp's own key sources, 2026-09-08); with the module a Mock those wires would outlive this test and
        # hand a later module in the same process (test_judge's JudgeEnv) a Mock where it expects an
        # environment. Saved here, restored below, and checked afterwards so a new wire added to _sdk_locked
        # without a `_FN` name still shows up here.
        wires = {n: getattr(km.jd, n) for n in dir(km.jd) if n.endswith("_FN")}
        try:
            km._sdk_backend = None
            results = [None] * 6
            with mock.patch.object(km, "load_source", return_value=fake_mod), \
                 mock.patch.object(km, "_ensure_sdk_on_path", return_value=True):
                ts = [threading.Thread(target=lambda i=i: results.__setitem__(i, km._sdk()))
                      for i in range(6)]
                for t in ts:
                    t.start()
                gate.set()
                for t in ts:
                    t.join(5)
            self.assertEqual(len(built), 1, "one construction, however many racers")
            self.assertTrue(all(r is built[0] for r in results),
                            "every caller gets the same singleton")
        finally:
            km._sdk_backend = prev
            for n, fn in wires.items():
                setattr(km.jd, n, fn)
        for n in dir(km.jd):
            self.assertNotIsInstance(getattr(km.jd, n), mock.Mock, "%s still wired to the Mock module" % n)


class WiringPins(unittest.TestCase):
    """Source pins (the test_sdk_kernel style) for boot/shutdown wiring that can't run in-process:
    delivering a real SIGTERM would os._exit the test runner."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(BIN, "romp-kernel")) as f:
            cls.src = f.read()

    def test_sigterm_handler_installed_in_main(self):
        self.assertIn("signal.signal(signal.SIGTERM, _graceful_term)", self.src)
        self.assertIn("be.drain(", self.src, "the handler drains the SDK backend")
        self.assertIn("os._exit(0)", self.src, "and always exits — a hung drain can't wedge the restart")

    def test_backend_constructed_eagerly_with_reconcile(self):
        self.assertIn("reconcile=True", self.src,
                      "the kernel opts into the boot reconcile (tests construct without it)")
        self.assertIn("threading.Thread(target=_sdk, daemon=True).start()", self.src,
                      "main() constructs the backend at boot so the reconcile isn't lazy")

    def test_graceful_term_never_constructs_the_backend(self):
        body = self.src.split("def _graceful_term", 1)[1].split("\ndef ", 1)[0]
        self.assertNotIn("_sdk()", body,
                         "shutdown must use the existing singleton only — constructing the backend "
                         "while dying makes no sense and can hang the drain")


if __name__ == "__main__":
    unittest.main()
