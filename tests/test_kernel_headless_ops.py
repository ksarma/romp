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
        srv = _far_kernel(200, json.dumps({"ok": True, "deferred": True}))
        remote = {"host": "TESTHOST", "local_port": srv.server_address[1], "token": "far-token"}
        try:
            with mock.patch.object(km, "_host_for_sid", lambda sid: remote):
                code, resp = self._post("/end", {"name": self.GHOST, "when": "idle"})
                self.assertEqual((code, resp), (200, {"ok": True, "deferred": True}))
                self._post("/end", {"id": self.GHOST})
                self._post("/end", {"id": self.GHOST, "when": "now"})
                self._post("/interrupt", {"id": self.GHOST, "when": "idle"})
        finally:
            srv.shutdown()
        self.assertEqual(srv.received, [("/end", {"id": self.GHOST, "when": "idle"}),
                                        ("/end", {"id": self.GHOST}),
                                        ("/end", {"id": self.GHOST}),
                                        ("/interrupt", {"id": self.GHOST})])

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
             mock.patch.object(km, "_remote_forward_answer", lambda r, path, body, method="POST": (200, {"ok": True}, "")):
            code, resp = self._post("/end", {"id": self.GHOST})
        self.assertEqual((code, resp), (200, {"ok": True}))

    def test_a_far_kernels_answer_is_relayed_in_its_own_words(self):
        # against a REAL far kernel on loopback, so the helper's body read is under test, not a stub of
        # it. The far gate's JSON 404 carries the reason: relayed with the far host named and the same
        # status. A text/plain 404 is the far do_POST's answer for a route that kernel predates (the other
        # remote arms read that status as version skew): relayed as the status and the body's first line,
        # never dressed as an unknown session; any other non-200 the same way. Before round 2 every far
        # 404 was composed locally as the unknown-name text (review round 2, 2026-09-09).
        gate = json.dumps({"ok": False, "error": "no live session named '%s'" % self.GHOST})
        cases = ((404, gate, "application/json",
                  ("no live session named '%s'" % self.GHOST, "TESTHOST"), ("HTTP 404",)),
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
