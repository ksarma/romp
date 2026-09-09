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
import contextlib
import io
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

    def test_the_end_route_and_the_ws_endSession_op_run_one_end_routine(self):
        # Two of the three kill doors that record a death, POST /end (`romp end <session>`) and the
        # dashboard's endSession op (the third is the end-on-idle sweep's arm, driven by the sweep tests
        # below; cancelCreate's _end_pending_sid stays outside the routine and records none), each call
        # _end_and_record once, with the sid and the backend that owns it, and neither kills on its own. The routine's epilogue (the death record, _comment_kill_all, the
        # closed frame) is exercised through the thread doors below; this test holds the doors to the one
        # routine, so a door that grows its own inline sweep, or skips the routine, fails here rather than
        # drifting (review round 4, 2026-09-09: the extension's source pin on the two inline sweeps went
        # stale when round 3 folded them into the routine; that pin now reads the same seam).
        fake = mock.Mock()
        calls = []

        def record(sid, be, now, via, fresh=False, why=None):
            calls.append((sid, be, via, fresh))
            return True
        with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
             mock.patch.object(km, "_end_and_record", record), \
             mock.patch.object(km, "_confirm_close_now", lambda sid: None), \
             mock.patch.object(km, "_push_soon", lambda *a, **k: None), \
             mock.patch.object(km, "_send_to_app", lambda app, m: None):
            code, resp = self._post("/end", {"id": "sid-x"})
            self.assertEqual((code, resp), (200, {"ok": True}))
            self.assertTrue(km._drive({"type": "endSession", "id": "sid-x"}, {"send": lambda s: None}))
        self.assertEqual([c[:2] for c in calls], [("sid-x", fake), ("sid-x", fake)],
                         "each door runs the routine once, with the sid and its owning backend")
        self.assertEqual([c[3] for c in calls], [False, False],
                         "an immediate door reads the owner's cycle snapshot; only the sweep asks fresh")
        self.assertEqual(len({c[2] for c in calls}), 2, "each door names itself in the kill attribution")
        fake.kill.assert_not_called()   # the routine owns the kill; no door kills beside it
        fake.interrupt.assert_not_called()

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
        # the arm reads the status beside the body (_remote_forward_answer), so that is the seam patched
        with mock.patch.object(km, "_host_for_sid", lambda sid: {"host": "TESTHOST"}), \
             mock.patch.object(km, "_remote_forward_answer", lambda r, path, body, method="POST": (200, {"ok": True, "queued": True}, "")):
            code, resp = self._post("/send", {"id": "sid-r", "text": "/frobnicate now"})
        self.assertEqual((code, resp), (200, {"ok": True, "queued": True}))
        with mock.patch.object(km, "_host_for_sid", lambda sid: {"host": "TESTHOST"}), \
             mock.patch.object(km, "_remote_forward_answer", lambda r, path, body, method="POST": (200, {"ok": True}, "")):
            code, resp = self._post("/send", {"id": "sid-r", "text": "hello"})
        self.assertEqual((code, resp), (200, {"ok": True, "queued": False}))
        # …and a far kernel's REFUSAL rides back as itself, never rewritten into an ok (review find, #904)
        refusal = {"ok": False, "error": "isolation: the target session's mailbox is OFF"}
        with mock.patch.object(km, "_host_for_sid", lambda sid: {"host": "TESTHOST"}), \
             mock.patch.object(km, "_remote_forward_answer", lambda r, path, body, method="POST": (200, dict(refusal), "")):
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
FAR_SID = "77777777-8888-9999-0000-111111111111"          # a session an attached host runs (its roster row)
FAR_SID_B = "88888888-9999-0000-1111-222222222222"


def _remote_row(srv, host="TESTHOST", sids=(), names=None):
    """A hub roster row for an attached host whose kernel is `srv` (a _far_kernel on loopback): the shape
    the supervisor's poll files (_remotes[host]), sids and the names that host lists for them."""
    return {"host": host, "local_port": srv.server_address[1], "token": "far-token",
            "sids": list(sids), "names": dict(names or {})}


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
    for f in (km.jd.STATE / "comments" / (parent + ".json"), km.jd.STATE / "sdk" / (tsid + ".json"),
              km.jd.STATE / "gone" / (tsid + ".json"), km.jd.STATE / "states" / (tsid + ".jsonl")):
        try:
            f.unlink()
        except OSError:
            pass


def _reg_flipping_kill(tsid):
    """A fake backend's kill with SdkBackend.kill's one durable effect: the reg's alive flag flips to False
    (the record _confirmed_ended reads for a thread) before the CLI is shut down."""
    reg_path = km.jd.STATE / "sdk" / (tsid + ".json")

    def kill(sid):
        if sid != tsid:
            return True
        reg = json.loads(reg_path.read_text())
        reg["alive"] = False
        tmp = reg_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(reg))
        os.replace(tmp, reg_path)
        return True
    return kill


def _thread_state(parent, tsid):
    """Every durable record an ended thread leaves, by relative path (None = absent): the reg, the death
    marker, the states rows and the parent's comment store."""
    out = {}
    for rel in ("sdk/%s.json" % tsid, "gone/%s.json" % tsid, "states/%s.jsonl" % tsid, "comments/%s.json" % parent):
        f = km.jd.STATE / rel
        out[rel] = f.read_bytes() if f.exists() else None
    return out


class _PinnedClock:
    """The kernel's `time` binding with time() pinned, everything else the real module: two kill doors
    stamping the same second leave byte-identical records."""

    def __init__(self, real, t):
        self._real, self._t = real, t

    def time(self):
        return self._t

    def __getattr__(self, name):
        return getattr(self._real, name)


def _far_kernel(status, body, ctype="application/json"):
    """A far kernel on loopback answering every POST with one status and body, for the relay tests: the
    real _remote_forward_answer connects to it, so what the tests stub is the tunnel row, not the helper."""
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer
    data = body.encode()
    received = []          # (path, parsed body) per POST, so a test can pin what the hub forwarded

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            try:
                received.append((self.path.split("?")[0], json.loads(raw or b"{}")))
            except ValueError:
                received.append((self.path.split("?")[0], raw))
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass
    srv = HTTPServer(("127.0.0.1", 0), H)
    srv.received = received
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


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
        deaths, sent, comment_kills = [], [], []
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
                # the pusher's sweep serves that wish at the thread's settle: the sibling test below
                code, resp = self._post("/end", {"name": THREAD_NAME, "when": "idle"})
                self.assertEqual((code, resp), (200, {"ok": True, "deferred": True}))
                # an immediate /end (`romp end self --now`) reaches the backend's kill on the tsid, the real
                # gate reads the flipped reg, and the thread leaves the state every ended session leaves
                # (_end_and_record): the death record, _comment_kill_all and the closed frame
                fake.kill.side_effect = _reg_flipping_kill(THREAD_TSID)
                with mock.patch.object(km, "_record_death", side_effect=lambda sid, t, kind: deaths.append(sid)), \
                     mock.patch.object(km, "_comment_kill_all", lambda sid, be: comment_kills.append(sid)), \
                     mock.patch.object(km, "_send_to_app", side_effect=lambda app, m: sent.append((app, m))):
                    code, resp = self._post("/end", {"id": THREAD_TSID})
                self.assertEqual((code, resp), (200, {"ok": True}))
                fake.kill.assert_called_once_with(THREAD_TSID)
                self.assertEqual(deaths, [THREAD_TSID])
                self.assertEqual(comment_kills, [THREAD_TSID])
                self.assertEqual(sent, [("chat", {"type": "closed", "id": THREAD_TSID})])
                # a name that is NOT a thread still falls through to the 404
                code, resp = self._post("/interrupt", {"name": self.GHOST})
                self._assert_404(code, resp)
        finally:
            km._pending_ops.clear()
            km._end_on_idle_save(km._end_on_idle_load() - {THREAD_TSID})
            _rm_thread(THREAD_PARENT, THREAD_TSID)
            _unregister(THREAD_PARENT)

    def test_a_threads_deferred_end_is_served_by_the_sweep_at_its_settle(self):
        # the deferred arm's other half: `romp end self` from a thread records the wish, and the pusher's
        # sweep must serve it. A thread is in no liveness snapshot (live_sessions hides threadOf regs by
        # design), so the sweep took its absent branch, where _confirmed_ended certified the thread dead
        # by the bare existence of its reg, and the wish was spent with no kill: the caller was told the
        # thread was closing while it kept running (review round 2, 2026-09-09). The sweep now reads the
        # reg's alive+threadOf as the owner's answer, waits on the thread's own transcript through its
        # reg (discovery lists no threads, so _path_of is None for one), and at the settle runs the one
        # end routine the immediate arm runs (_end_and_record): the kill, the death record,
        # _comment_kill_all and the closed frame, so the deferred and the immediate `romp end self` leave
        # one state (review round 3: the sweep killed and wrote nothing else, and its comment promised a
        # revive no code performed; the sibling test below diffs the two doors' state).
        fake = mock.Mock()
        fake.busy.return_value = None
        reg_path = km.jd.STATE / "sdk" / (THREAD_TSID + ".json")
        fake.kill.side_effect = _reg_flipping_kill(THREAD_TSID)
        working, parsed, deaths, sent, comment_kills = [True], [], [], [], []
        _register(THREAD_PARENT, "web-parent")
        _mk_thread(THREAD_PARENT, THREAD_TSID, THREAD_NAME)
        try:
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km.Sessions, "live", staticmethod(lambda: {})), \
                 mock.patch.object(km, "_parse", lambda path, sid, now: parsed.append(path) or {"turns": []}), \
                 mock.patch.object(km, "_session_working", lambda turns: working[0]), \
                 mock.patch.object(km, "_record_death", side_effect=lambda sid, t, kind: deaths.append(sid)), \
                 mock.patch.object(km, "_comment_kill_all", lambda sid, be: comment_kills.append(sid)), \
                 mock.patch.object(km, "_send_to_app", side_effect=lambda app, m: sent.append((app, m))), \
                 mock.patch.object(km, "_push_soon", lambda *a, **k: None):
                code, resp = self._post("/end", {"id": THREAD_TSID, "when": "idle"})
                self.assertEqual((code, resp), (200, {"ok": True, "deferred": True}))
                self.assertIn(THREAD_TSID, km._end_on_idle_load())
                self.assertIs(km._confirmed_ended(THREAD_TSID), False,
                              "an alive thread is not certified dead by the existence of its reg")
                # its turn is open: the sweep waits, reading the thread's own transcript
                km._end_on_idle_sweep(1000, {})
                fake.kill.assert_not_called()
                self.assertIn(THREAD_TSID, km._end_on_idle_load(), "the wish stays armed while the turn is open")
                self.assertEqual(parsed, [km._thread_transcript_path(km._thread_reg(THREAD_TSID), THREAD_TSID)])
                # the turn settles: the sweep kills the tsid and spends the wish on that kill
                working[0] = False
                km._end_on_idle_sweep(1001, {})
                fake.kill.assert_called_once_with(THREAD_TSID)
                self.assertNotIn(THREAD_TSID, km._end_on_idle_load(), "spent by the kill, not by inference")
                self.assertFalse(json.loads(reg_path.read_text()).get("alive"))
                self.assertIs(km._confirmed_ended(THREAD_TSID), True, "the flipped reg is the owner's answer")
                self.assertEqual(deaths, [THREAD_TSID], "the death record the immediate arm writes")
                self.assertEqual(comment_kills, [THREAD_TSID], "its own threads' teardown, as the immediate arm")
                self.assertEqual(sent, [("chat", {"type": "closed", "id": THREAD_TSID})], "the closed frame too")
        finally:
            km._end_on_idle_save(km._end_on_idle_load() - {THREAD_TSID})
            _rm_thread(THREAD_PARENT, THREAD_TSID)
            _unregister(THREAD_PARENT)

    def test_both_end_doors_leave_a_thread_in_byte_identical_state(self):
        # `romp end self` (deferred: the wish, served by the sweep at the settle) and `romp end self --now`
        # (the immediate /end) from inside a comment thread run ONE routine, _end_and_record, so the
        # durable state they leave is the same to the byte: the reg, the death marker, the states row,
        # the comment row and the frames sent. Before round 3 the sweep's arm killed a thread and wrote
        # none of the three records the immediate arm wrote, and a comment promised a dormant thread a
        # reply would revive, which no code performed (review round 3, 2026-09-09). The real
        # _record_death, _comment_kill_all and _confirmed_ended run; only the clock is pinned, so both
        # doors stamp the same second.
        fake = mock.Mock()
        fake.busy.return_value = None
        fake.kill.side_effect = _reg_flipping_kill(THREAD_TSID)
        frames = []

        def reset():
            _rm_thread(THREAD_PARENT, THREAD_TSID)
            _mk_thread(THREAD_PARENT, THREAD_TSID, THREAD_NAME)
            fake.kill.reset_mock()
            del frames[:]
        _register(THREAD_PARENT, "web-parent")
        try:
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km.Sessions, "live", staticmethod(lambda: {})), \
                 mock.patch.object(km, "_parse", lambda path, sid, now: {"turns": []}), \
                 mock.patch.object(km, "_session_working", lambda turns: False), \
                 mock.patch.object(km, "_send_to_app", side_effect=lambda app, m: frames.append((app, m))), \
                 mock.patch.object(km, "_push_soon", lambda *a, **k: None), \
                 mock.patch.object(km, "time", _PinnedClock(km.time, 1000.0)):
                # door one: the immediate arm
                reset()
                code, resp = self._post("/end", {"id": THREAD_TSID})
                self.assertEqual((code, resp), (200, {"ok": True}))
                fake.kill.assert_called_once_with(THREAD_TSID)
                now_state, now_frames = _thread_state(THREAD_PARENT, THREAD_TSID), list(frames)
                # door two: the deferred arm, served by the sweep at the settle
                reset()
                code, resp = self._post("/end", {"id": THREAD_TSID, "when": "idle"})
                self.assertEqual((code, resp), (200, {"ok": True, "deferred": True}))
                km._end_on_idle_sweep(1000, {})
                fake.kill.assert_called_once_with(THREAD_TSID)
                self.assertNotIn(THREAD_TSID, km._end_on_idle_load(), "the wish is spent by the kill")
                idle_state, idle_frames = _thread_state(THREAD_PARENT, THREAD_TSID), list(frames)
            self.assertEqual(now_state, idle_state, "the two doors leave different durable state")
            self.assertEqual(now_frames, idle_frames, "the two doors send different frames")
            # and that shared state is the whole epilogue, not a shared nothing
            self.assertEqual(json.loads(now_state["gone/%s.json" % THREAD_TSID]), {"t": 999, "by": "kill"})
            self.assertEqual([json.loads(ln) for ln in now_state["states/%s.jsonl" % THREAD_TSID].splitlines()],
                             [{"t": 999, "state": "idle"}])
            self.assertIs(json.loads(now_state["sdk/%s.json" % THREAD_TSID])["alive"], False)
            self.assertEqual(now_frames, [("chat", {"type": "closed", "id": THREAD_TSID})])
            self.assertEqual(json.loads(now_state["comments/%s.json" % THREAD_PARENT])["threads"][0]["status"], "open",
                             "neither door touches the comment row")
        finally:
            km._end_on_idle_save(km._end_on_idle_load() - {THREAD_TSID})
            _rm_thread(THREAD_PARENT, THREAD_TSID)
            _unregister(THREAD_PARENT)

    def test_an_unreadable_reg_cannot_confirm_an_end_and_the_wish_stays_armed(self):
        # _confirmed_ended's SDK partition read {} for a reg that exists but would not read (_thread_reg
        # answers {} for a file that fails to parse and for a non-object body) and certified the thread
        # dead: the sweep took its absent branch and spent the wish with no kill while the reg on disk
        # still meant alive. An unreadable reg is no answer: None, the writer stands down, the wish stays
        # armed, and it is served once the reg reads again (review round 3, 2026-09-09). A plain SDK
        # session's unreadable reg answers None on the same path, where it used to answer True.
        fake = mock.Mock()
        fake.busy.return_value = None
        fake.kill.side_effect = _reg_flipping_kill(THREAD_TSID)
        reg_path = km.jd.STATE / "sdk" / (THREAD_TSID + ".json")
        plain_reg = km.jd.STATE / "sdk" / "sid-q.json"
        _register(THREAD_PARENT, "web-parent")
        _mk_thread(THREAD_PARENT, THREAD_TSID, THREAD_NAME)
        good = reg_path.read_text()
        km._thread_reg_memo.clear()
        km._thread_reg_failed.clear()
        deaths = []
        try:
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km.Sessions, "live", staticmethod(lambda: {})), \
                 mock.patch.object(km, "_parse", lambda path, sid, now: {"turns": []}), \
                 mock.patch.object(km, "_session_working", lambda turns: False), \
                 mock.patch.object(km, "_record_death", side_effect=lambda sid, t, kind: deaths.append(sid)), \
                 mock.patch.object(km, "_comment_kill_all", lambda sid, be: None), \
                 mock.patch.object(km, "_send_to_app", lambda app, m: None), \
                 mock.patch.object(km, "_push_soon", lambda *a, **k: None):
                code, resp = self._post("/end", {"id": THREAD_TSID, "when": "idle"})
                self.assertEqual((code, resp), (200, {"ok": True, "deferred": True}))
                for bad in (b"{not json", json.dumps([1, 2]).encode()):
                    reg_path.write_bytes(bad)
                    self.assertIsNone(km._confirmed_ended(THREAD_TSID), bad)
                    km._end_on_idle_sweep(1000, {})
                    fake.kill.assert_not_called()
                    self.assertIn(THREAD_TSID, km._end_on_idle_load(), "the wish stays armed: %r" % bad)
                    self.assertEqual(deaths, [])
                # the reg reads again: the wish is served as before
                reg_path.write_text(good)
                km._end_on_idle_sweep(1001, {})
                fake.kill.assert_called_once_with(THREAD_TSID)
                self.assertNotIn(THREAD_TSID, km._end_on_idle_load())
                self.assertEqual(deaths, [THREAD_TSID])
                # a plain SDK session on the same partition: unreadable is None, readable is the owner's answer
                plain_reg.write_bytes(b"{not json")
                self.assertIsNone(km._confirmed_ended("sid-q"))
                plain_reg.write_text(json.dumps({"sid": "sid-q", "alive": False}))
                self.assertIs(km._confirmed_ended("sid-q"), True)
        finally:
            km._end_on_idle_save(km._end_on_idle_load() - {THREAD_TSID})
            _rm_thread(THREAD_PARENT, THREAD_TSID)
            _unregister(THREAD_PARENT)
            try:
                plain_reg.unlink()
            except OSError:
                pass
            km._thread_reg_memo.clear()
            km._thread_reg_failed.clear()

    def test_the_sweep_waits_for_a_threads_fork_to_land(self):
        # while the reg carries forkOf, lastSid is the PARENT's transcript (sdk_backend.fork mints it so,
        # and the CLI init that pins the thread's own fsid spends it), so the sweep parsed the parent's
        # file and gated the thread's kill on the parent's turn: a settled parent killed the thread at
        # once, a mid-turn parent held it. Reachable from outside (`romp end --when-idle <thread>` in that
        # window). The sweep stands down on forkOf as _thread_messages does; the wish stays armed until
        # the flip, the exact event, and then the settle-then-kill sequence runs (review round 3).
        fake = mock.Mock()
        fake.busy.return_value = None
        fake.kill.side_effect = _reg_flipping_kill(THREAD_TSID)
        reg_path = km.jd.STATE / "sdk" / (THREAD_TSID + ".json")
        _register(THREAD_PARENT, "web-parent")
        _mk_thread(THREAD_PARENT, THREAD_TSID, THREAD_NAME)
        reg = json.loads(reg_path.read_text())
        reg["forkOf"], reg["lastSid"] = THREAD_PARENT, THREAD_PARENT
        reg_path.write_text(json.dumps(reg))
        parsed = []
        try:
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km.Sessions, "live", staticmethod(lambda: {})), \
                 mock.patch.object(km, "_parse", lambda path, sid, now: parsed.append(path) or {"turns": []}), \
                 mock.patch.object(km, "_session_working", lambda turns: False), \
                 mock.patch.object(km, "_record_death", lambda sid, t, kind: None), \
                 mock.patch.object(km, "_comment_kill_all", lambda sid, be: None), \
                 mock.patch.object(km, "_send_to_app", lambda app, m: None), \
                 mock.patch.object(km, "_push_soon", lambda *a, **k: None):
                code, resp = self._post("/end", {"id": THREAD_TSID, "when": "idle"})
                self.assertEqual((code, resp), (200, {"ok": True, "deferred": True}))
                km._end_on_idle_sweep(1000, {})
                km._end_on_idle_sweep(1001, {})
                fake.kill.assert_not_called()
                self.assertIn(THREAD_TSID, km._end_on_idle_load(), "the wish stays armed until the fork lands")
                self.assertEqual(parsed, [], "the parent's transcript is never read for the thread")
                # the init lands: forkOf is spent and lastSid is the thread's own fsid
                reg.pop("forkOf")
                reg["lastSid"] = THREAD_TSID
                reg_path.write_text(json.dumps(reg))
                km._end_on_idle_sweep(1002, {})
                self.assertEqual(parsed, [km._thread_transcript_path(reg, THREAD_TSID)])
                fake.kill.assert_called_once_with(THREAD_TSID)
                self.assertNotIn(THREAD_TSID, km._end_on_idle_load())
        finally:
            km._end_on_idle_save(km._end_on_idle_load() - {THREAD_TSID})
            _rm_thread(THREAD_PARENT, THREAD_TSID)
            _unregister(THREAD_PARENT)

    def test_a_thread_whose_fork_never_launched_takes_its_deferred_end(self):
        # a thread whose fork failed to launch keeps forkOf (spent only by a CLI init that never came) and
        # carries launchError (_record_launch_error writes it; only a connect proof clears it), with alive
        # still True. Its deferred end was accepted (200 deferred) and the sweep's forkOf arm then stood down
        # silently on every tick, forever short of a relaunch, while the immediate door on the same reg
        # killed and recorded. Nothing is launching it, so no turn can be open: the sweep takes the kill
        # path through the one routine (the death record, the closed frame, the spent wish), reading no
        # transcript. While the backend lists the sid as running (a reply relaunching the CLI leaves both
        # flags set for the whole launch) it stands down and says so each tick, as the sibling branches do
        # (review round 4, 2026-09-09).
        fake = mock.Mock()
        fake.busy.return_value = None
        fake.kill.side_effect = _reg_flipping_kill(THREAD_TSID)
        fake.running_sids.return_value = [THREAD_TSID]
        reg_path = km.jd.STATE / "sdk" / (THREAD_TSID + ".json")
        _register(THREAD_PARENT, "web-parent")
        _mk_thread(THREAD_PARENT, THREAD_TSID, THREAD_NAME)
        reg = json.loads(reg_path.read_text())
        reg["forkOf"], reg["lastSid"] = THREAD_PARENT, THREAD_PARENT
        reg["launchError"] = {"kind": "spawn", "text": "the CLI exited before it connected", "t": 1}
        reg_path.write_text(json.dumps(reg))
        deaths, sent, parsed = [], [], []
        try:
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km.Sessions, "live", staticmethod(lambda: {})), \
                 mock.patch.object(km, "_parse", lambda path, sid, now: parsed.append(path) or {"turns": []}), \
                 mock.patch.object(km, "_session_working", lambda turns: False), \
                 mock.patch.object(km, "_record_death", side_effect=lambda sid, t, kind: deaths.append(sid)), \
                 mock.patch.object(km, "_comment_kill_all", lambda sid, be: None), \
                 mock.patch.object(km, "_send_to_app", side_effect=lambda app, m: sent.append(m)), \
                 mock.patch.object(km, "_push_soon", lambda *a, **k: None):
                code, resp = self._post("/end", {"id": THREAD_TSID, "when": "idle"})
                self.assertEqual((code, resp), (200, {"ok": True, "deferred": True}))
                # a launch in flight: the backend lists the sid; stand down, and say so
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    km._end_on_idle_sweep(1000, {})
                fake.kill.assert_not_called()
                self.assertIn(THREAD_TSID, km._end_on_idle_load(), "the wish stays armed while a launch is in flight")
                self.assertIn("fork has not landed", err.getvalue(), "the stand-down is said, not silent")
                self.assertEqual(parsed, [], "the parent's transcript is never read for the thread")
                # nothing launching it: the fork will never land, and the wish is served now
                fake.running_sids.return_value = []
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    km._end_on_idle_sweep(1001, {})
                fake.kill.assert_called_once_with(THREAD_TSID)
                self.assertEqual(deaths, [THREAD_TSID], "the death is recorded")
                self.assertIn({"type": "closed", "id": THREAD_TSID}, sent, "the closed frame is sent")
                self.assertNotIn(THREAD_TSID, km._end_on_idle_load(), "the wish is spent")
                self.assertEqual(parsed, [], "no transcript is parsed: no CLI is up, so no turn can be open")
                self.assertIn("kill: %s via end-on-idle" % THREAD_TSID, err.getvalue())
        finally:
            km._end_on_idle_save(km._end_on_idle_load() - {THREAD_TSID})
            _rm_thread(THREAD_PARENT, THREAD_TSID)
            _unregister(THREAD_PARENT)

    def test_a_send_the_backend_refuses_is_a_409_not_an_ok(self):
        # a KNOWN sid the backend no longer holds (SdkBackend.send answers False when its reg is missing or
        # reads alive=False: a dead SDK session by id, an ended comment thread by name or by id): the route
        # folded that False into 200 ok:true queued:false, and `romp send` printed ok for a message nothing
        # received (review round 3, 2026-09-09). The refusal is a 409 in the unknown-session refusal's
        # shape, naming the caller's spelling; nothing is parked. The gate still admits the sid: it is
        # known, it is just not running.
        fake = mock.Mock()
        fake.busy.return_value = None
        fake.send.return_value = False
        _register(THREAD_PARENT, "web-parent")
        _mk_thread(THREAD_PARENT, THREAD_TSID, THREAD_NAME)
        reg_path = km.jd.STATE / "sdk" / (THREAD_TSID + ".json")
        reg = json.loads(reg_path.read_text())
        reg["alive"] = False
        reg_path.write_text(json.dumps(reg))
        km._pending_ops.clear()
        try:
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km.Sessions, "live", staticmethod(lambda: {})), \
                 mock.patch.object(km, "_compacting_now", lambda sid, **k: False), \
                 mock.patch.object(km, "_working_now", lambda sid: False):
                for who in ("sid-q", THREAD_NAME, THREAD_TSID):
                    key = "name" if who == THREAD_NAME else "id"
                    code, resp = self._post("/send", {key: who, "text": "hello"})
                    self.assertEqual(code, 409, who)
                    self.assertIs(resp.get("ok"), False, who)
                    self.assertIn(who, resp.get("error", ""), "the reason names the caller's spelling")
                    self.assertIn("not delivered", resp.get("error", ""), who)
                self.assertEqual(fake.send.call_count, 3, "the backend was asked each time; it refused")
                self.assertEqual(km._pending_ops, {}, "a refused send parks nothing")
        finally:
            km._pending_ops.clear()
            _rm_thread(THREAD_PARENT, THREAD_TSID)
            _unregister(THREAD_PARENT)

    def test_a_remote_deferred_end_forwards_the_deferral(self):
        # the remote arm forwarded {id} alone, so `romp end <far-sid> --when-idle` took the far kernel's
        # immediate arm and killed at once while the rows promised a settle (review round 3, 2026-09-09).
        # The validated field rides along, and only it: the caller's `name` key stays here, an immediate
        # end forwards {id} as before, and /interrupt never carries it. Against a REAL far kernel on
        # loopback, which records what it was sent; its deferred answer is relayed as is.
        # The roster is seeded, not _host_for_sid patched, so the request routes as a real hub's would
        # (review round 4: the earlier version pinned a NAME forwarded as an id, a shape routing never makes)
        srv = _far_kernel(200, json.dumps({"ok": True, "deferred": True}))
        try:
            with mock.patch.dict(km._remotes, {"TESTHOST": _remote_row(srv, sids=[FAR_SID])}, clear=True):
                code, resp = self._post("/end", {"id": FAR_SID, "when": "idle"})
                self.assertEqual((code, resp), (200, {"ok": True, "deferred": True}))
                self._post("/end", {"id": FAR_SID})
                self._post("/end", {"id": FAR_SID, "when": "now"})
                self._post("/interrupt", {"id": FAR_SID, "when": "idle"})
        finally:
            srv.shutdown()
        self.assertEqual(srv.received, [("/end", {"id": FAR_SID, "when": "idle"}),
                                        ("/end", {"id": FAR_SID}),
                                        ("/end", {"id": FAR_SID}),
                                        ("/interrupt", {"id": FAR_SID})])

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
        with mock.patch.dict(km._remotes, {"TESTHOST": {"host": "TESTHOST", "sids": [FAR_SID]}}, clear=True), \
             mock.patch.object(km, "_remote_forward_answer", lambda r, path, body, method="POST": (200, {"ok": True}, "")):
            code, resp = self._post("/end", {"id": FAR_SID})
        self.assertEqual((code, resp), (200, {"ok": True}))

    def test_a_far_session_is_reached_by_the_name_the_hubs_roster_lists(self):
        # _resolve_sid reads the local names registry, the local live map and the thread names, and
        # _host_for_sid matches sids only, so `romp end far-web` from the hub answered 404 "no live session
        # named 'far-web'" with nothing forwarded while the roster (_remotes[host]["names"], the copy
        # _remote_name_of reads) listed that very name and the far session ran on; by id the request
        # forwarded. The roster is consulted by name after every local door missed, and a match takes the
        # remote arm with the far sid exactly as the sid path does, the deferral included (review round 4,
        # 2026-09-09). A live local session of the same name wins; a name two hosts list is refused naming
        # both as host:name, and that spelling picks one. Against a real far kernel on loopback.
        srv = _far_kernel(200, json.dumps({"ok": True, "deferred": True}))
        row = _remote_row(srv, sids=[FAR_SID], names={FAR_SID: "far-web"})
        row_b = _remote_row(srv, host="TESTHOST-B", sids=[FAR_SID_B], names={FAR_SID_B: "far-web"})
        fake = mock.Mock()
        try:
            with mock.patch.dict(km._remotes, {"TESTHOST": row}, clear=True), \
                 mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km.Sessions, "live", staticmethod(lambda: {})):
                self.assertEqual(km._remote_name_of("TESTHOST", FAR_SID), "far-web")
                for body in ({"name": "far-web", "when": "idle"}, {"id": FAR_SID, "when": "idle"},
                             {"name": "TESTHOST:far-web", "when": "idle"}):
                    code, resp = self._post("/end", body)
                    self.assertEqual((code, resp), (200, {"ok": True, "deferred": True}), body)
                self._post("/end", {"name": "far-web"})
                self._post("/interrupt", {"name": "far-web"})
                self._post("/send", {"name": "far-web", "text": "hello"})
                code, resp = self._post("/end", {"name": "far-api"})      # a name no roster lists stays a 404
                self.assertEqual(code, 404)
                self.assertIn("far-api", resp.get("error", ""))
                with mock.patch.dict(km._remotes, {"TESTHOST-B": row_b}):
                    code, resp = self._post("/interrupt", {"name": "far-web"})
                    self.assertEqual(code, 409, resp)
                    self.assertIn("TESTHOST:far-web", resp.get("error", ""))
                    self.assertIn("TESTHOST-B:far-web", resp.get("error", ""))
                    code, resp = self._post("/interrupt", {"name": "TESTHOST-B:far-web"})
                    self.assertEqual((code, resp), (200, {"ok": True, "deferred": True}))
            # a LIVE local session named far-web outranks the roster: the local doors are asked first
            _register("sid-x", "far-web")
            with mock.patch.dict(km._remotes, {"TESTHOST": row}, clear=True), \
                 mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km.Sessions, "live", staticmethod(lambda: {"sid-x": {}})):
                code, resp = self._post("/interrupt", {"name": "far-web"})
                self.assertEqual((code, resp), (200, {"ok": True}))
                fake.interrupt.assert_called_once_with("sid-x")
        finally:
            _register("sid-x", "web")
            srv.shutdown()
        self.assertEqual(srv.received, [("/end", {"id": FAR_SID, "when": "idle"})] * 3
                         + [("/end", {"id": FAR_SID}), ("/interrupt", {"id": FAR_SID}),
                            ("/send", {"id": FAR_SID, "text": "hello"}), ("/interrupt", {"id": FAR_SID_B})],
                         "every by-name request forwards the FAR sid, never the name")

    def test_a_far_kernels_answer_is_relayed_in_its_own_words(self):
        # against a REAL far kernel on loopback, so the helper's body read is under test, not a stub of
        # it. The far gate's JSON 404 carries the reason: relayed with the far host named and the same
        # status. A text/plain 404 is the far do_POST's answer for a route that kernel predates (the other
        # remote arms read that status as version skew): relayed as the status and the body's first line,
        # never dressed as an unknown session; any other non-200 the same way. Before round 2 every far
        # 404 was composed locally as the unknown-name text (review round 2, 2026-09-09).
        gate = json.dumps({"ok": False, "error": "no live session named '%s'" % self.GHOST})
        # a far kernel running this change answers /send's backend refusal with a 409 that already ends
        # in "the message was not delivered"; the arm's own coda doubled it in the relayed body (review
        # round 4, 2026-09-09). The far words come through verbatim, the sentence once
        refused = json.dumps({"ok": False, "error": "the session '%s' is not running; the message was not "
                                                   "delivered" % self.GHOST})
        cases = ((404, gate, "application/json",
                  ("no live session named '%s'" % self.GHOST, "TESTHOST"), ("HTTP 404",)),
                 (409, refused, "application/json",
                  ("is not running", "the message was not delivered", "TESTHOST"), ("HTTP 409",)),
                 (404, "not found", "text/plain",
                  ("HTTP 404", "not found", "TESTHOST"), (self.GHOST,)),
                 (503, "gateway down\nsecond line", "text/plain",
                  ("HTTP 503", "gateway down", "TESTHOST"), ("second line", self.GHOST)))
        for path, body in (("/end", {"id": self.GHOST}), ("/interrupt", {"id": self.GHOST}),
                           ("/send", {"id": self.GHOST, "text": "hello"})):
            for status, far_body, ctype, expect, absent in cases:
                srv = _far_kernel(status, far_body, ctype)
                remote = {"host": "TESTHOST", "local_port": srv.server_address[1], "token": "far-token"}
                try:
                    with mock.patch.object(km, "_host_for_sid", lambda sid: remote):
                        code, resp = self._post(path, body)
                finally:
                    srv.shutdown()
                self.assertEqual(code, status, (path, far_body))
                self.assertFalse(resp.get("ok"))
                for s in expect:
                    self.assertIn(s, resp.get("error", ""), (path, far_body))
                for s in absent:
                    self.assertNotIn(s, resp.get("error", ""), (path, far_body))
                self.assertLessEqual(resp.get("error", "").count("the message was not delivered"), 1,
                                     "the coda is the far kernel's sentence or the local refusal's, never both")
            # a dead tunnel: nothing listens on the port, so the call never lands (status 0)
            import socket
            s = socket.socket()
            s.bind(("127.0.0.1", 0))
            dead_port = s.getsockname()[1]
            s.close()
            remote = {"host": "TESTHOST", "local_port": dead_port, "token": ""}
            with mock.patch.object(km, "_host_for_sid", lambda sid: remote), \
                 mock.patch.object(km, "_demand_redial", lambda host, kind: None):
                code, resp = self._post(path, body)
            self.assertEqual(code, 200, path)
            self.assertIn("isn't answering", resp.get("error", ""), path)
            self.assertIn("TESTHOST", resp.get("error", ""), path)

    def test_the_relay_arms_read_the_far_answer_seam(self):
        # the three arms read _remote_forward_answer (status, parsed JSON, body text), never the
        # 200-only _remote_forward_status the other remote arms keep: a far gate's 404 relays its JSON
        # error, a text 503 relays the status and line, and status 0 stays the tunnel text
        remote = {"host": "TESTHOST"}
        gate = {"ok": False, "error": "no live session named '%s'" % self.GHOST}
        for path, body in (("/end", {"id": self.GHOST}), ("/interrupt", {"id": self.GHOST}),
                           ("/send", {"id": self.GHOST, "text": "hello"})):
            with mock.patch.object(km, "_host_for_sid", lambda sid: remote), \
                 mock.patch.object(km, "_remote_forward_answer",
                                   lambda r, p, b, method="POST": (404, dict(gate), json.dumps(gate))):
                code, resp = self._post(path, body)
            self.assertEqual(code, 404, path)
            self.assertFalse(resp.get("ok"))
            self.assertIn(self.GHOST, resp.get("error", ""), path)
            self.assertIn("TESTHOST", resp.get("error", ""), path)
            self.assertNotIn("isn't answering", resp.get("error", ""), path)
            with mock.patch.object(km, "_host_for_sid", lambda sid: remote), \
                 mock.patch.object(km, "_remote_forward_answer", lambda r, p, b, method="POST": (0, None, "")):
                code, resp = self._post(path, body)
            self.assertEqual(code, 200, path)
            self.assertIn("isn't answering", resp.get("error", ""), path)
            with mock.patch.object(km, "_host_for_sid", lambda sid: remote), \
                 mock.patch.object(km, "_remote_forward_answer",
                                   lambda r, p, b, method="POST": (503, None, "gateway down")):
                code, resp = self._post(path, body)
            self.assertEqual(code, 503, path)
            self.assertFalse(resp.get("ok"))
            self.assertIn("HTTP 503", resp.get("error", ""), path)
            self.assertIn("gateway down", resp.get("error", ""), path)
            self.assertIn("TESTHOST", resp.get("error", ""), path)

    def test_an_unconfirmed_end_names_its_cause_at_both_doors(self):
        # _confirmed_ended answers None for two causes, an SDK reg that exists but would not read (round 3)
        # and a failed owner scan, and both immediate doors phrased every None as "tmux isn't answering",
        # including on a headless box with no tmux at all. The cause rides beside the verdict (`why`) and one
        # routine, _unconfirmed_end_text, phrases both doors from it (review round 4, 2026-09-09). The reg
        # case: a reg valid at the gate that the kill leaves unreadable (a record broken between the gate
        # and the corroboration), so the door itself reaches the corroboration. Nothing durable is written
        # for either cause: no death record, no closed frame.
        reg_path = km.jd.STATE / "sdk" / "sid-q.json"
        reg_path.parent.mkdir(parents=True, exist_ok=True)
        deaths, sent, faileds = [], [], []
        client = {"send": lambda s: faileds.append(json.loads(s))}
        fake = mock.Mock()
        fake.kill.side_effect = lambda sid: reg_path.write_bytes(b"{not json") or True
        km._thread_reg_memo.clear()
        km._thread_reg_failed.clear()
        try:
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km.Sessions, "live", staticmethod(lambda: {})), \
                 mock.patch.object(km, "_record_death", side_effect=lambda sid, t, kind: deaths.append(sid)), \
                 mock.patch.object(km, "_comment_kill_all", lambda sid, be: None), \
                 mock.patch.object(km, "_send_to_app", side_effect=lambda app, m: sent.append(m)), \
                 mock.patch.object(km, "_confirm_close_now", lambda sid: None), \
                 mock.patch.object(km, "_push_soon", lambda *a, **k: None):
                reg_path.write_text(json.dumps({"sid": "sid-q", "alive": True}))
                code, resp = self._post("/end", {"id": "sid-q"})
                self.assertEqual(code, 200)
                self.assertIs(resp.get("ok"), False)
                self.assertIn("the session's record could not be read", resp.get("error", ""))
                self.assertNotIn("tmux", resp.get("error", ""))
                reg_path.write_text(json.dumps({"sid": "sid-q", "alive": True}))
                self.assertTrue(km._drive({"type": "endSession", "id": "sid-q"}, client))
                self.assertEqual([f["type"] for f in faileds], ["endFailed"])
                self.assertIn("the session's record could not be read", faileds[0]["text"])
                self.assertIn("Couldn't confirm", faileds[0]["text"])
                self.assertIn("web", faileds[0]["text"], "the toast names the session")
                self.assertNotIn("tmux", faileds[0]["text"])
                # the probe cause: no reg, a tmux server up, the owner scan fails
                reg_path.unlink()
                fake.kill.side_effect = None
                del faileds[:]
                with mock.patch.object(km._TMUX, "available", lambda: True), \
                     mock.patch.object(km._TMUX, "alive_sids", lambda *a, **k: None):
                    code, resp = self._post("/end", {"id": "sid-q"})
                    self.assertEqual(code, 200)
                    self.assertIn("tmux isn't answering", resp.get("error", ""))
                    self.assertNotIn("record", resp.get("error", ""))
                    self.assertTrue(km._drive({"type": "endSession", "id": "sid-q"}, client))
                    self.assertIn("tmux isn't answering", faileds[0]["text"])
                    self.assertNotIn("record", faileds[0]["text"])
                self.assertEqual(deaths, [], "an unconfirmed end records no death")
                self.assertEqual([m for m in sent if m.get("type") == "closed"], [], "and broadcasts no closed frame")
        finally:
            try:
                reg_path.unlink()
            except OSError:
                pass
            km._thread_reg_memo.clear()
            km._thread_reg_failed.clear()

    def test_the_ws_drive_gate_and_the_http_gate_give_one_verdict_per_state(self):
        # the WS _drive gate (_kernel_knows: names, the SDK registry, the live map) and the HTTP gate
        # (_unknown_session_refusal: names, the live map, then a threadOf reg only) were two predicates
        # with a different third door: a dead non-thread SDK reg with no names/ entry was ended by the
        # dashboard's endSession op and refused 404 by /end, /interrupt and /send. One predicate now, and
        # this table holds the two doors to one verdict per state (review round 4, 2026-09-09). The map
        # _resolve_sid read is what the routes hand the predicate, so the refusal path still scans once.
        dead, named, live = ("aaaa1111-2222-3333-4444-555555555555", "bbbb1111-2222-3333-4444-555555555555",
                             "cccc1111-2222-3333-4444-555555555555")
        sdir = km.jd.STATE / "sdk"
        sdir.mkdir(parents=True, exist_ok=True)
        (sdir / (dead + ".json")).write_text(json.dumps({"sid": dead, "alive": False, "cwd": "/tmp"}))
        _register(THREAD_PARENT, "web-parent")
        _mk_thread(THREAD_PARENT, THREAD_TSID, THREAD_NAME)
        _register(named, "named-only")
        states = (("no record", self.GHOST, False), ("dead SDK reg, no names entry", dead, True),
                  ("comment thread", THREAD_TSID, True), ("names entry only", named, True),
                  ("live, unregistered", live, True))
        refused = []
        fake = mock.Mock()
        try:
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km.Sessions, "live", staticmethod(lambda: {live: {}})), \
                 mock.patch.object(km, "_refuse_drive", side_effect=lambda c, op, sid, msg: refused.append(sid)), \
                 mock.patch.object(km, "_end_and_record", lambda sid, be, now, via, fresh=False, why=None: True), \
                 mock.patch.object(km, "_send_or_park", lambda be, sid, text: True), \
                 mock.patch.object(km, "_route_meta_command", lambda be, sid, text, state=None: False), \
                 mock.patch.object(km, "_confirm_close_now", lambda sid: None), \
                 mock.patch.object(km, "_send_to_app", lambda app, m: None), \
                 mock.patch.object(km, "_push_soon", lambda *a, **k: None):
                for label, sid, admitted in states:
                    del refused[:]
                    self.assertTrue(km._drive({"type": "interrupt", "id": sid}, {"send": lambda s: None}))
                    self.assertEqual(not refused, admitted, "the WS drive gate on %s" % label)
                    for path, body in (("/end", {"id": sid}), ("/interrupt", {"id": sid}),
                                       ("/send", {"id": sid, "text": "hello"})):
                        code, resp = self._post(path, body)
                        self.assertEqual(code != 404, admitted, "%s on %s answered %s" % (path, label, code))
        finally:
            for f in (sdir / (dead + ".json"),):
                try:
                    f.unlink()
                except OSError:
                    pass
            _rm_thread(THREAD_PARENT, THREAD_TSID)
            _unregister(THREAD_PARENT)
            _unregister(named)
            km._thread_reg_memo.clear()

    def test_a_record_that_will_not_read_is_a_503_naming_the_read_not_a_404(self):
        # a thread whose reg exists but does not parse was answered 404 "no live session named '<tsid>'"
        # on /end when:idle, /send and /interrupt: the gate's third door read _thread_reg, whose {} meant
        # absent OR unreadable, while _confirmed_ended on the same reg answered None, "exists but would not
        # read". A failed read is never reported as a session that does not exist (the fail-loudly rule):
        # the gate answers 503 naming the read and does nothing, by id and by name. The comment threads'
        # store: _thread_names answers None by its contract when the stores cannot be read, and the
        # resolution says so instead of falling through to the 404 (review round 4, 2026-09-09).
        _register(THREAD_PARENT, "web-parent")
        _mk_thread(THREAD_PARENT, THREAD_TSID, THREAD_NAME)
        reg_path = km.jd.STATE / "sdk" / (THREAD_TSID + ".json")
        fake = mock.Mock()
        km._thread_reg_memo.clear()
        km._thread_reg_failed.clear()
        try:
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km.Sessions, "live", staticmethod(lambda: {})), \
                 mock.patch.object(km, "_push_soon", lambda *a, **k: None):
                for bad in (b"{not json", json.dumps([1, 2]).encode()):
                    reg_path.write_bytes(bad)
                    self.assertTrue(km._reg_unreadable(THREAD_TSID), bad)
                    for path, body in (("/end", {"id": THREAD_TSID, "when": "idle"}), ("/end", {"name": THREAD_NAME}),
                                       ("/send", {"id": THREAD_TSID, "text": "hello"}),
                                       ("/send", {"name": THREAD_NAME, "text": "hello"}),
                                       ("/interrupt", {"id": THREAD_TSID})):
                        code, resp = self._post(path, body)
                        self.assertEqual(code, 503, (bad, path, body, resp))
                        self.assertIs(resp.get("ok"), False)
                        self.assertIn("could not read the record", resp.get("error", ""), (bad, path))
                        self.assertNotIn("no live session", resp.get("error", ""), (bad, path))
                    self.assertNotIn(THREAD_TSID, km._end_on_idle_load(), "a refused deferred end records no wish")
                fake.kill.assert_not_called()
                fake.send.assert_not_called()
                fake.interrupt.assert_not_called()
                self.assertFalse(km._reg_unreadable(self.GHOST), "no record at all is not a failed read")
                # the store: no reg to admit the sid, the name resolves through the store, and it will not read
                reg_path.unlink()
                km._thread_reg_memo.clear()
                with mock.patch.object(km, "_thread_names", lambda: None):
                    for path, body in (("/end", {"name": THREAD_NAME, "when": "idle"}),
                                       ("/send", {"name": THREAD_NAME, "text": "hello"}),
                                       ("/interrupt", {"name": THREAD_NAME})):
                        code, resp = self._post(path, body)
                        self.assertEqual(code, 503, (path, resp))
                        self.assertIn("comment threads' store", resp.get("error", ""), path)
                        self.assertNotIn("no live session", resp.get("error", ""), path)
                    # a sid the registry holds never reaches the store: a local session wins
                    code, resp = self._post("/interrupt", {"id": "sid-x"})
                    self.assertEqual((code, resp), (200, {"ok": True}))
                self.assertNotIn(THREAD_TSID, km._end_on_idle_load())
                fake.kill.assert_not_called()
                fake.send.assert_not_called()
        finally:
            km._end_on_idle_save(km._end_on_idle_load() - {THREAD_TSID})
            _rm_thread(THREAD_PARENT, THREAD_TSID)
            _unregister(THREAD_PARENT)
            km._thread_reg_memo.clear()
            km._thread_reg_failed.clear()


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
