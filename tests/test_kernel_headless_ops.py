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
        # No tmux for the route tests: the routes' 404 path asks the tmux probe whether the live scan answered,
        # which on a box with tmux forks the real server and reads its session list. Patched per test, never
        # set in os.environ at import: an environment pin leaks into every module an xdist worker imports
        # after this one, and turned three tmux-behaviour tests in another module red in the same run. The
        # tests that need the probe patch _TMUX.available and _TMUX._run over this (review round 5, 2026-09-09).
        self._tmux_off = mock.patch.object(km._TMUX, "available", lambda: False)
        self._tmux_off.start()
        for sid, name in KNOWN_SIDS.items():
            _register(sid, name)

    def tearDown(self):
        for sid in KNOWN_SIDS:
            _unregister(sid)
        self._tmux_off.stop()

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


def _sdk_reporting(running):
    """The real SDK backend with running_sids() answering `running` (a list the test may mutate): the set
    _backend_reports_running reads, the one liveness that bears on a torn SDK reg (round 9). owns() and the
    rest stay the real backend's, so the registry doors behave as they would."""
    real = km._sdk()

    class _Be:
        def running_sids(self):
            return list(running)

        def __getattr__(self, name):
            return getattr(real, name)
    return _Be()


def _tmux_server(sids):
    """A stand-in for _TMUX._run: a tmux server whose panes carry `sids`. `list-sessions -F <fmt>` answers one
    line per sid in the caller's own format (LANE_FMT for live_sessions, the bare sid for alive_sids, NAME_FMT
    for _tmux_name_of), as panes carrying those sids would, so the REAL Sessions.live() scan reads these sids
    on the tmux backend with nothing patched above the fork; every other command exits 0 with nothing. The
    pane's name is minted from the sid."""
    import re
    import subprocess

    def run(args, t=3):
        args = list(args)
        out = ""
        if args[:1] == ["list-sessions"]:
            fmt = args[args.index("-F") + 1] if "-F" in args else "#{session_name}"
            for sid in sids:
                line = (fmt.replace("#{@romp}", "1").replace("#{@romp-session-id}", sid)
                        .replace("#{@claude-state}", "waiting").replace("#{session_name}", "pane-" + sid[:8]))
                out += re.sub(r"#\{[^}]*\}", "", line) + "\n"
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=out, stderr="")
    return run


def _scripted_run(answers, calls=None):
    """A stand-in for _TMUX._run that answers `list-sessions` from `answers` in order (None for a probe that
    failed, a CompletedProcess for one that answered) and records each such call in `calls`; a request that
    forks more often than the script allows raises rather than reading a stale answer. Every other command
    exits 0 with nothing."""
    import subprocess
    answers = list(answers)

    def run(args, t=3):
        args = list(args)
        if args[:1] == ["list-sessions"]:
            if calls is not None:
                calls.append(args)
            if not answers:
                raise AssertionError("tmux forked more often than the script allows: %r" % args)
            return answers.pop(0)
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
    return run


def _forget_regs(paths):
    """Forget a test's private SDK regs in the SDK backend module's reg cache and incident latch, the files
    untouched: the cold list_regs cache a kernel restart leaves, so a test can hold one file at a cold and a
    warm cache (the round-9 pair tests). The cache is module-global and prunes only past a 64-entry drift, so
    a row it cached for a path a later test reuses would be served for that test's file."""
    import sys
    sbm = sys.modules.get("romp_sdk_backend")
    if sbm is not None:
        for p in paths:
            sbm._REG_CACHE.pop(str(p), None)
            sbm._REG_SERVE_WARNED.discard(str(p))


def _drop_regs(paths):
    """Unlink a test's private SDK regs and forget them (_forget_regs)."""
    for p in paths:
        try:
            p.unlink()
        except OSError:
            pass
    _forget_regs(paths)


class UnknownSessionRefused(_RouteServer):
    """A name (or id) that resolves to no session is a 404 naming it, on /end, /interrupt and /send
    alike. _sid_of falls back to its input unchanged, so a typo used to mint a phantom sid: /end
    "killed" it, _confirmed_ended found nothing listed and certified the death, and `romp end <typo>`
    printed a bare ok while the real session kept running; /send handed the phantom to the tmux
    backend, whose refusal the route folded into ok:true. A caller that trusted those oks had to
    re-check the roster to learn nothing had happened. The verdict is _session_gate's, one gate for the WS
    drive door and these routes: a session a backend reports running is admitted whatever its record reads;
    else _kernel_knows (the names registry; the SDK registry, any reg the SDK backend wrote, a comment
    thread's included since a thread has no names/ entry and live_sessions hides it; the live map), so a
    registered-but-idle sid and a dead non-thread SDK reg both pass and a dead session addressed by id keeps
    its idempotent end; a registry entry that exists but will not read is a 503 naming the read, not a 404,
    and so are a comment threads' store and a live session list that will not read. The gate is asked with
    the live map _resolve_sid already read, so the refusal path scans once."""

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

    def test_a_threads_turn_cut_by_a_restart_with_nothing_to_resume_it_is_ended_now(self):
        # a comment thread's deferred end whose turn a kernel restart cut was held forever and silently: threads
        # are not resumed at boot (_boot_reconcile skips a threadOf reg without a persisted queue), drain leaves
        # the trailing working row, and the sweep's open-turn branch waited for a settle only the next human
        # reply would produce, so the wish killed the thread at that reply, weeks later. With nothing running
        # the sid (running_sids) and no persisted queue (pending_queued reads the reg mirror for a session not
        # running) no settle is coming: the sweep ends it now through the one end routine, saying why (review
        # round 5, 2026-09-09).
        fake = mock.Mock()
        fake.busy.return_value = None
        fake.kill.side_effect = _reg_flipping_kill(THREAD_TSID)
        fake.running_sids.return_value = []
        fake.pending_queued.return_value = []
        _register(THREAD_PARENT, "web-parent")
        _mk_thread(THREAD_PARENT, THREAD_TSID, THREAD_NAME)
        deaths, sent, parsed = [], [], []
        try:
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km.Sessions, "live", staticmethod(lambda: {})), \
                 mock.patch.object(km, "_parse", lambda path, sid, now: parsed.append(path) or {"turns": []}), \
                 mock.patch.object(km, "_session_working", lambda turns: True), \
                 mock.patch.object(km, "_record_death", side_effect=lambda sid, t, kind: deaths.append(sid)), \
                 mock.patch.object(km, "_comment_kill_all", lambda sid, be: None), \
                 mock.patch.object(km, "_send_to_app", side_effect=lambda app, m: sent.append(m)), \
                 mock.patch.object(km, "_push_soon", lambda *a, **k: None):
                code, resp = self._post("/end", {"id": THREAD_TSID, "when": "idle"})
                self.assertEqual((code, resp), (200, {"ok": True, "deferred": True}))
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    km._end_on_idle_sweep(1000, {})
                fake.kill.assert_called_once_with(THREAD_TSID)
                self.assertEqual(deaths, [THREAD_TSID], "the death is recorded")
                self.assertIn({"type": "closed", "id": THREAD_TSID}, sent, "the closed frame is sent")
                self.assertNotIn(THREAD_TSID, km._end_on_idle_load(), "the wish is spent by the kill")
                self.assertEqual(parsed, [km._thread_transcript_path(km._thread_reg(THREAD_TSID), THREAD_TSID)],
                                 "the thread's own transcript was read: the turn IS open, nothing will settle it")
                self.assertIn("turn was cut and nothing resumes it", err.getvalue())
                self.assertIn("kill: %s via end-on-idle (self-close, a comment thread)" % THREAD_TSID, err.getvalue())
                # a second tick finds nothing armed
                fake.kill.reset_mock()
                km._end_on_idle_sweep(1001, {})
                fake.kill.assert_not_called()
        finally:
            km._end_on_idle_save(km._end_on_idle_load() - {THREAD_TSID})
            _rm_thread(THREAD_PARENT, THREAD_TSID)
            _unregister(THREAD_PARENT)

    def test_a_cut_thread_turn_waits_on_a_running_cli_or_a_queued_reply(self):
        # the cut-turn arm's guards: a CLI running the turn is the ordinary open turn, waited on in silence like
        # any session's; a persisted queue with nothing running is the exact event that a boot resume is coming
        # (the staggered to_start loop feeds it, and running_sids lists the sid only once its _ensure runs), so
        # the arm stands down aloud and the queued reply is not dropped; once the resume runs the turn and it
        # settles, the ordinary settle path kills (review round 5, 2026-09-09).
        fake = mock.Mock()
        fake.busy.return_value = None
        fake.kill.side_effect = _reg_flipping_kill(THREAD_TSID)
        fake.running_sids.return_value = [THREAD_TSID]
        fake.pending_queued.return_value = []
        _register(THREAD_PARENT, "web-parent")
        _mk_thread(THREAD_PARENT, THREAD_TSID, THREAD_NAME)
        working, deaths, sent = [True], [], []
        try:
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km.Sessions, "live", staticmethod(lambda: {})), \
                 mock.patch.object(km, "_parse", lambda path, sid, now: {"turns": []}), \
                 mock.patch.object(km, "_session_working", lambda turns: working[0]), \
                 mock.patch.object(km, "_record_death", side_effect=lambda sid, t, kind: deaths.append(sid)), \
                 mock.patch.object(km, "_comment_kill_all", lambda sid, be: None), \
                 mock.patch.object(km, "_send_to_app", side_effect=lambda app, m: sent.append(m)), \
                 mock.patch.object(km, "_push_soon", lambda *a, **k: None):
                code, resp = self._post("/end", {"id": THREAD_TSID, "when": "idle"})
                self.assertEqual((code, resp), (200, {"ok": True, "deferred": True}))
                # a CLI runs the open turn: wait, silently, as for any session
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    km._end_on_idle_sweep(1000, {})
                fake.kill.assert_not_called()
                self.assertIn(THREAD_TSID, km._end_on_idle_load())
                self.assertEqual(err.getvalue(), "", "an ordinary open turn is waited on in silence")
                # nothing runs it, but a reply is queued: the resume is coming; stand down and say so
                fake.running_sids.return_value = []
                fake.pending_queued.return_value = ["the reply the CLI never started"]
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    km._end_on_idle_sweep(1001, {})
                fake.kill.assert_not_called()
                self.assertIn(THREAD_TSID, km._end_on_idle_load(), "the wish stays armed for the resume")
                self.assertIn("turn was cut with a reply queued", err.getvalue())
                fake.pending_queued.assert_called_with(THREAD_TSID)
                # the resume lands: the CLI runs the turn and the queue is fed; the turn is open, so wait
                fake.running_sids.return_value = [THREAD_TSID]
                fake.pending_queued.return_value = []
                km._end_on_idle_sweep(1002, {})
                fake.kill.assert_not_called()
                # its settle: the ordinary path
                working[0] = False
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    km._end_on_idle_sweep(1003, {})
                fake.kill.assert_called_once_with(THREAD_TSID)
                self.assertEqual(deaths, [THREAD_TSID])
                self.assertIn({"type": "closed", "id": THREAD_TSID}, sent)
                self.assertNotIn(THREAD_TSID, km._end_on_idle_load())
                self.assertNotIn("turn was cut", err.getvalue(), "a settled turn takes the settle path, not the cut arm")
        finally:
            km._end_on_idle_save(km._end_on_idle_load() - {THREAD_TSID})
            _rm_thread(THREAD_PARENT, THREAD_TSID)
            _unregister(THREAD_PARENT)

    def test_a_cut_thread_turn_reads_as_open_from_its_real_transcript_and_is_ended(self):
        # the shape a restart leaves on disk, parsed for real: a user prompt answered by an assistant tool_use
        # with no stop record (live resumes carry none), and no idle row. The real parse reads an open turn
        # that nothing will settle, and the cut-turn arm ends the thread once nothing runs it (review round 5,
        # 2026-09-09). The transcript lives under the test run's projects root, never the real one.
        import time as _time
        from datetime import datetime, timezone
        from pathlib import Path
        self.assertNotEqual(os.path.realpath(str(km.jd.PROJECTS)),
                            os.path.realpath(os.path.expanduser("~/.claude/projects")),
                            "the projects root must be the test run's, never the real one")

        def iso(t):
            return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        now = int(_time.time())
        fake = mock.Mock()
        fake.busy.return_value = None
        fake.kill.side_effect = _reg_flipping_kill(THREAD_TSID)
        fake.running_sids.return_value = [THREAD_TSID]
        fake.pending_queued.return_value = []
        _register(THREAD_PARENT, "web-parent")
        _mk_thread(THREAD_PARENT, THREAD_TSID, THREAD_NAME)
        reg_path = km.jd.STATE / "sdk" / (THREAD_TSID + ".json")
        tpath = Path(km._thread_transcript_path(json.loads(reg_path.read_text()), THREAD_TSID))
        tpath.parent.mkdir(parents=True, exist_ok=True)
        recs = [{"type": "user", "timestamp": iso(now - 90), "uuid": "u1", "parentUuid": None, "promptSource": "typed",
                 "message": {"role": "user", "content": "please look into the flaky test"}},
                {"type": "assistant", "timestamp": iso(now - 80), "uuid": "a1", "parentUuid": "u1",
                 "message": {"role": "assistant", "stop_reason": "tool_use",
                             "content": [{"type": "text", "text": "Looking."},
                                         {"type": "tool_use", "id": "tu_1", "name": "Bash",
                                          "input": {"command": "pytest -q"}}]}}]
        tpath.write_text("\n".join(json.dumps(r) for r in recs) + "\n")
        deaths, sent = [], []
        try:
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km.Sessions, "live", staticmethod(lambda: {})), \
                 mock.patch.object(km, "_record_death", side_effect=lambda sid, t, kind: deaths.append(sid)), \
                 mock.patch.object(km, "_comment_kill_all", lambda sid, be: None), \
                 mock.patch.object(km, "_send_to_app", side_effect=lambda app, m: sent.append(m)), \
                 mock.patch.object(km, "_push_soon", lambda *a, **k: None):
                ps = km._parse(str(tpath), THREAD_TSID, now)
                self.assertTrue(km._session_working(ps.get("turns") or []), "the fixture reads as an open turn")
                code, resp = self._post("/end", {"id": THREAD_TSID, "when": "idle"})
                self.assertEqual((code, resp), (200, {"ok": True, "deferred": True}))
                km._end_on_idle_sweep(now, {})
                fake.kill.assert_not_called()
                self.assertIn(THREAD_TSID, km._end_on_idle_load(), "a CLI runs the turn: the wish waits")
                fake.running_sids.return_value = []
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    km._end_on_idle_sweep(now + 1, {})
                fake.kill.assert_called_once_with(THREAD_TSID)
                self.assertEqual(deaths, [THREAD_TSID])
                self.assertIn({"type": "closed", "id": THREAD_TSID}, sent)
                self.assertNotIn(THREAD_TSID, km._end_on_idle_load())
                self.assertIn("turn was cut and nothing resumes it", err.getvalue())
        finally:
            km._end_on_idle_save(km._end_on_idle_load() - {THREAD_TSID})
            _rm_thread(THREAD_PARENT, THREAD_TSID)
            _unregister(THREAD_PARENT)
            try:
                tpath.unlink()
            except OSError:
                pass

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

    def test_a_send_to_a_tmux_session_no_pane_runs_is_refused_before_the_paste(self):
        # a KNOWN tmux-backed sid that no longer runs (a names/ entry, no pane, no SDK reg; a dead Codex
        # session by id takes the same path): TmuxBackend.send answers truthy and hands the paste to
        # _tmux_send's daemon thread, which failed after the route had answered 200 ok:true queued:false, so
        # `romp send` printed ok for a message nothing received, where the CLI's help and the reference promise
        # a 409 for a known session that is not running. The /send local arm asks the tmux server first,
        # through the failure-aware primitive, before the setters and _send_or_park (a dead sid mid-turn would
        # otherwise park and answer queued:true): a set without the sid is the 409 the SDK refusal answers,
        # None is a 503 with nothing done, a tmux-less box the 409; a pane carrying the sid proceeds as before
        # (review round 5, 2026-09-09). sid-x is registered with no SDK reg, so the REAL backend_for falls to
        # the tmux backend.
        parked, routed = [], []
        refusal = {"ok": False, "error": "the session 'sid-x' is not running; the message was not delivered"}
        km._pending_ops.clear()
        try:
            with mock.patch.object(km, "_send_or_park", lambda be, sid, text: parked.append((sid, text)) or True), \
                 mock.patch.object(km, "_route_meta_command",
                                   lambda be, sid, text, state=None: (routed.append(text), False)[1]), \
                 mock.patch.object(km, "_push_soon", lambda *a, **k: None):
                self.assertIs(km.Sessions.backend_for("sid-x"), km._TMUX)
                with mock.patch.object(km._TMUX, "available", lambda: True), \
                     mock.patch.object(km._TMUX, "alive_sids", lambda *a, **k: {"sid-q"}):
                    for text in ("hello", "/model opus"):
                        code, resp = self._post("/send", {"id": "sid-x", "text": text})
                        self.assertEqual((code, resp), (409, refusal), text)
                with mock.patch.object(km._TMUX, "available", lambda: True), \
                     mock.patch.object(km._TMUX, "alive_sids", lambda *a, **k: None):
                    err = io.StringIO()
                    with contextlib.redirect_stderr(err):
                        code, resp = self._post("/send", {"id": "sid-x", "text": "hello"})
                    self.assertEqual(code, 503, resp)
                    self.assertIn("tmux isn't answering", resp.get("error", ""))
                    # and the kernel log says so, as every sibling stand-down on a failed probe does (round 6)
                    self.assertIn("send sid-x: tmux probe failed; answered 503, nothing delivered", err.getvalue())
                    self.assertIn("'sid-x'", resp.get("error", ""))
                    self.assertIn("not delivered", resp.get("error", ""))
                with mock.patch.object(km._TMUX, "available", lambda: False):
                    code, resp = self._post("/send", {"id": "sid-x", "text": "hello"})
                    self.assertEqual((code, resp), (409, refusal), "a tmux-less box runs no tmux session")
                self.assertEqual((parked, routed), ([], []), "nothing reached the setters or the paste")
                self.assertEqual(km._pending_ops, {}, "nothing parked")
                with mock.patch.object(km._TMUX, "available", lambda: True), \
                     mock.patch.object(km._TMUX, "alive_sids", lambda *a, **k: {"sid-x", "sid-q"}):
                    code, resp = self._post("/send", {"id": "sid-x", "text": "hello"})
                    self.assertEqual((code, resp), (200, {"ok": True, "queued": False}))
                self.assertEqual(parked, [("sid-x", "hello")], "a pane carrying the sid takes the send as before")
        finally:
            km._pending_ops.clear()

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

    def test_a_far_host_whose_key_carries_a_colon_is_picked_by_the_409s_own_spelling(self):
        # _remote_session_named split `who` at its FIRST colon, so a session on a host whose roster key
        # carries one (an IPv6 literal such as fd00::1, which _safe_ssh_host admits) could never be picked by
        # the host:name spelling the 409 itself printed: `fd00::1:far-web` answered 404. The match is composed
        # per roster host instead (nm == who, or who == host + ":" + nm), so hosts may carry colons while
        # names may not; a user@host key, colon-free, round-trips as before (review round 5, 2026-09-09).
        srv = _far_kernel(200, json.dumps({"ok": True, "deferred": True}))
        rows = {"fd00::1": _remote_row(srv, host="fd00::1", sids=[FAR_SID], names={FAR_SID: "far-web"}),
                "me@TESTHOST-B": _remote_row(srv, host="me@TESTHOST-B", sids=[FAR_SID_B],
                                             names={FAR_SID_B: "far-web"})}
        try:
            with mock.patch.dict(km._remotes, rows, clear=True), \
                 mock.patch.object(km.Sessions, "live", staticmethod(lambda: {})):
                code, resp = self._post("/end", {"name": "far-web", "when": "idle"})
                self.assertEqual(code, 409, resp)
                self.assertIn("fd00::1:far-web", resp.get("error", ""))
                self.assertIn("me@TESTHOST-B:far-web", resp.get("error", ""))
                for spelling in ("fd00::1:far-web", "me@TESTHOST-B:far-web"):
                    code, resp = self._post("/end", {"name": spelling, "when": "idle"})
                    self.assertEqual((code, resp), (200, {"ok": True, "deferred": True}), spelling)
        finally:
            srv.shutdown()
        self.assertEqual(srv.received, [("/end", {"id": FAR_SID, "when": "idle"}),
                                        ("/end", {"id": FAR_SID_B, "when": "idle"})],
                         "each spelling forwards its own host's far sid")

    def test_an_away_hosts_stale_names_route_nowhere(self):
        # the supervisor clears a row's `sids` when the ssh probe declares the host away and never clears its
        # `names`, so a far session's stale name routed a by-name request into the dead tunnel (200 "isn't
        # answering", a redial demanded per request) while the same request by id answered 404, and the stale
        # name made a false 409 against a live host's same-named session. Only a far sid the row's sids list
        # carries counts now, the liveness the by-id route reads, so both doors answer alike (review round 5,
        # 2026-09-09). A plain tunnel death without ssh corroboration keeps both lists, so both doors still
        # forward and demand the redial: the pre-existing consistent behaviour, not exercised here.
        import socket
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        dead_port = s.getsockname()[1]
        s.close()
        away = {"host": "TESTHOST", "local_port": dead_port, "token": "", "sids": [], "names": {FAR_SID: "far-web"}}
        redials = []
        srv = _far_kernel(200, json.dumps({"ok": True}))
        live_b = _remote_row(srv, host="TESTHOST-B", sids=[FAR_SID_B], names={FAR_SID_B: "far-web"})
        fake = mock.Mock()
        try:
            with mock.patch.dict(km._remotes, {"TESTHOST": away}, clear=True), \
                 mock.patch.object(km, "_demand_redial", lambda host, kind: redials.append((host, kind))), \
                 mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km.Sessions, "live", staticmethod(lambda: {})):
                for path, body in (("/end", {"name": "far-web"}), ("/end", {"name": "far-web", "when": "idle"}),
                                   ("/send", {"name": "far-web", "text": "hello"}),
                                   ("/interrupt", {"name": "far-web"}), ("/end", {"id": FAR_SID})):
                    code, resp = self._post(path, body)
                    self.assertEqual(code, 404, (path, body, resp))
                    self.assertIn("no live session named", resp.get("error", ""), (path, body))
                self.assertEqual(redials, [], "nothing dials a host the probe declared away")
                fake.kill.assert_not_called()
                fake.send.assert_not_called()
                fake.interrupt.assert_not_called()
                # beside a live host's same-named session the stale name is no candidate: no 409, and the
                # request forwards to the live host
                with mock.patch.dict(km._remotes, {"TESTHOST-B": live_b}):
                    code, resp = self._post("/interrupt", {"name": "far-web"})
                    self.assertEqual((code, resp), (200, {"ok": True}))
                self.assertEqual(redials, [])
        finally:
            srv.shutdown()
        self.assertEqual(srv.received, [("/interrupt", {"id": FAR_SID_B})])

    def test_two_same_named_sessions_on_one_host_are_refused_by_id(self):
        # two live same-named sessions on ONE attached host: the refusal said "more than one attached
        # machine; say which: h:web, h:web" (one machine, one spelling twice), and `h:web` then picked
        # whichever far sid the roster iterated first. The refusal names each as host:name [sid8] and says
        # the bare full far sid routes by id (_host_for_sid), the one spelling that tells them apart, and
        # host:name with more than one hit refuses the same way. Mixed (host A twice, host B once): A's
        # ids and B:web; B:web picks, A:web refuses with the ids (review round 5, 2026-09-09).
        a, b = "aaaa7777-8888-9999-0000-111111111111", "bbbb7777-8888-9999-0000-111111111111"
        srv = _far_kernel(200, json.dumps({"ok": True}))
        row = _remote_row(srv, sids=[a, b], names={a: "web", b: "web"})
        row_b = _remote_row(srv, host="TESTHOST-B", sids=[FAR_SID_B], names={FAR_SID_B: "web"})
        try:
            with mock.patch.dict(km._remotes, {"TESTHOST": row}, clear=True), \
                 mock.patch.object(km.Sessions, "live", staticmethod(lambda: {})):
                for who in ("web", "TESTHOST:web"):
                    code, resp = self._post("/interrupt", {"name": who})
                    self.assertEqual(code, 409, (who, resp))
                    err = resp.get("error", "")
                    self.assertIn("more than one session on TESTHOST answers to 'web'", err, who)
                    self.assertNotIn("attached machine", err, who)
                    self.assertEqual(err.count("TESTHOST:web [%s]" % a[:8]), 1, err)
                    self.assertEqual(err.count("TESTHOST:web [%s]" % b[:8]), 1, err)
                    self.assertIn("routes by id", err, who)
                for body in ({"id": b}, {"name": b}):
                    code, resp = self._post("/interrupt", body)
                    self.assertEqual((code, resp), (200, {"ok": True}), body)
                with mock.patch.dict(km._remotes, {"TESTHOST-B": row_b}):
                    code, resp = self._post("/interrupt", {"name": "web"})
                    self.assertEqual(code, 409, resp)
                    err = resp.get("error", "")
                    self.assertIn("more than one attached machine", err)
                    for cand in ("TESTHOST:web [%s]" % a[:8], "TESTHOST:web [%s]" % b[:8], "TESTHOST-B:web"):
                        self.assertEqual(err.count(cand), 1, (cand, err))
                    self.assertNotIn("TESTHOST-B:web [", err, "a host with one session of the name needs no id")
                    code, resp = self._post("/interrupt", {"name": "TESTHOST-B:web"})
                    self.assertEqual((code, resp), (200, {"ok": True}))
                    code, resp = self._post("/interrupt", {"name": "TESTHOST:web"})
                    self.assertEqual(code, 409, resp)
                    self.assertIn("TESTHOST:web [%s]" % a[:8], resp.get("error", ""))
        finally:
            srv.shutdown()
        self.assertEqual(srv.received, [("/interrupt", {"id": b}), ("/interrupt", {"id": b}),
                                        ("/interrupt", {"id": FAR_SID_B})],
                         "only an unambiguous target forwards, and by its own far sid")

    def test_a_failed_live_scan_is_a_503_not_a_session_that_does_not_exist(self):
        # when the tmux probe fails (an exec error, a timeout, an unrecognised nonzero exit) Sessions.live()
        # inherits list_lines' error->[] collapse, _resolve_sid cannot map a name to its sid, and the routes
        # answered 404 "no live session named" for a session the kernel knows while the same request by id
        # said tmux isn't answering: a failed read reported as a session that does not exist, against
        # _control_target's own rule. On the 404 path, when the live scan the resolution read failed (the
        # map's own tmux_failed, the failure alive_sids reads as None), the routes answer 503 naming the list;
        # the no-server exit (the authoritative zero) and a tmux-less box keep the 404 (review rounds 5 and 6,
        # 2026-09-09).
        import subprocess
        fake = mock.Mock()
        with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
             mock.patch.object(km, "_push_soon", lambda *a, **k: None), \
             mock.patch.object(km._TMUX, "available", lambda: True), \
             mock.patch.object(km._TMUX, "_run", lambda *a, **k: None):
            self.assertIsNone(km._TMUX.alive_sids())
            for path, body in (("/end", {"name": "web"}), ("/end", {"name": "web", "when": "idle"}),
                               ("/interrupt", {"name": "web"}), ("/send", {"name": "web", "text": "hello"})):
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    code, resp = self._post(path, body)
                self.assertEqual(code, 503, (path, body, resp))
                # the refusal is in the kernel log too, as every sibling stand-down on a failed probe is; a
                # substring, since the first request in a process also captures the SDK backend's boot lines
                # (review round 6, 2026-09-09)
                self.assertIn("control %s: tmux probe failed while resolving 'web'; answered 503, nothing done" % path,
                              err.getvalue(), path)
                self.assertIn("could not read the live session list", resp.get("error", ""), path)
                self.assertIn("'web'", resp.get("error", ""), path)
                self.assertIn("try again", resp.get("error", ""), "tmux answers again: this retry has a writer")
                self.assertNotIn("no live session", resp.get("error", ""), path)
            self.assertNotIn("sid-x", km._end_on_idle_load(), "a refused deferred end records no wish")
            fake.kill.assert_not_called()
            fake.send.assert_not_called()
            fake.interrupt.assert_not_called()
            # the same request by id reaches the end routine, whose corroboration says the same thing
            code, resp = self._post("/end", {"id": "sid-x"})
            self.assertEqual(code, 200)
            self.assertIn("tmux isn't answering", resp.get("error", ""))
            # a nonzero exit naming a missing server is the authoritative zero: an unregistered name, and a
            # registered name no session runs, stay 404 (a dormant session is addressed by id)
            gone = subprocess.CompletedProcess(args=[], returncode=1, stdout="",
                                               stderr="no server running on /tmp/tmux-1000/default")
            with mock.patch.object(km._TMUX, "_run", lambda *a, **k: gone):
                self.assertEqual(km._TMUX.alive_sids(), set())
                for who in (self.GHOST, "web"):
                    code, resp = self._post("/interrupt", {"name": who})
                    self.assertEqual(code, 404, (who, resp))
                    self.assertIn("no live session named '%s'" % who, resp.get("error", ""))
        # a tmux-less box never asks the probe: the 404 stands
        with mock.patch.object(km._TMUX, "available", lambda: False), \
             mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)):
            code, resp = self._post("/interrupt", {"name": self.GHOST})
            self._assert_404(code, resp)

    def test_a_failed_live_scan_stands_ahead_of_the_roster_by_name(self):
        # with the local scan failed, "a local session wins" cannot be evaluated (a local session of the name
        # may be running unseen), so a name the roster lists is not forwarded: the 503 comes first and
        # nothing is done, where a forward could have acted on the wrong session. With the scan answering (a
        # set; the no-server exit included) the same name forwards as before (review round 5, 2026-09-09).
        import subprocess
        srv = _far_kernel(200, json.dumps({"ok": True}))
        row = _remote_row(srv, sids=[FAR_SID], names={FAR_SID: "far-web"})
        gone = subprocess.CompletedProcess(args=[], returncode=1, stdout="",
                                           stderr="error connecting to /tmp/tmux-1000/default (No such file or directory)")
        try:
            with mock.patch.dict(km._remotes, {"TESTHOST": row}, clear=True), \
                 mock.patch.object(km._TMUX, "available", lambda: True):
                with mock.patch.object(km._TMUX, "_run", lambda *a, **k: None):
                    code, resp = self._post("/interrupt", {"name": "far-web"})
                    self.assertEqual(code, 503, resp)
                    self.assertIn("could not read the live session list", resp.get("error", ""))
                    self.assertEqual(srv.received, [], "nothing is forwarded while the local scan is unread")
                    # the host:name spelling (the one the 409 tells the caller to type) names no local session:
                    # NAME_RE forbids the colon at every name door, so the failed LOCAL scan is not what fails
                    # it, and it forwards while the bare name is held (review round 6, 2026-09-09: it was
                    # refused 503 by a scan that could never have matched it, while the far sid forwarded)
                    code, resp = self._post("/interrupt", {"name": "TESTHOST:far-web"})
                    self.assertEqual((code, resp), (200, {"ok": True}), "the 409's own spelling routes while the local probe is down")
                    self.assertEqual(srv.received, [("/interrupt", {"id": FAR_SID})])
                    code, resp = self._post("/interrupt", {"name": "far-web"})
                    self.assertEqual(code, 503, "the bare name stays held: a local session of the name may run unseen")
                with mock.patch.object(km._TMUX, "_run", lambda *a, **k: gone):
                    code, resp = self._post("/interrupt", {"name": "far-web"})
                    self.assertEqual((code, resp), (200, {"ok": True}))
        finally:
            srv.shutdown()
        self.assertEqual(srv.received, [("/interrupt", {"id": FAR_SID})] * 2)

    def test_the_failed_scan_verdict_is_the_scans_own_not_a_second_probes(self):
        # the failed-scan 503 keyed on a SECOND tmux probe (_TMUX.alive_sids()) taken after the gate, not on
        # the failure of the scan _resolve_sid read (Sessions.live() -> TmuxBackend.live_sessions(), which
        # collapsed a failed _run to []). First probe fails, second answers: `romp end web` said 404 "no live
        # session named 'web'" for a live session the second probe itself listed, while by id it was admitted.
        # The mirror, the scan answers and the re-probe fails, gave an unknown name a spurious 503. live_sessions
        # now classifies its own _run result as alive_sids does and the verdict rides the map (tmux_failed), so
        # the 503 is decided by the one scan the request made and each by-name request forks tmux once
        # (review round 6, 2026-09-09). The script answers one fork per request; a second fork would drain it.
        import subprocess
        fake = mock.Mock()
        ok_sid_x = _tmux_server(["sid-x"])(["list-sessions", "-F", km.TmuxBackend.LANE_FMT])
        empty = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
             mock.patch.object(km, "_push_soon", lambda *a, **k: None), \
             mock.patch.object(km._TMUX, "available", lambda: True):
            for path, body in (("/end", {"name": "web"}), ("/interrupt", {"name": "web"}),
                               ("/send", {"name": "web", "text": "hello"})):
                calls = []
                with mock.patch.object(km._TMUX, "_run", _scripted_run([None, ok_sid_x], calls)):
                    code, resp = self._post(path, body)
                self.assertEqual(code, 503, (path, resp))
                self.assertIn("could not read the live session list", resp.get("error", ""), path)
                self.assertNotIn("no live session", resp.get("error", ""), path)
                self.assertEqual(len(calls), 1, "%s forked tmux %d times: %r" % (path, len(calls), calls))
            fake.kill.assert_not_called()
            fake.interrupt.assert_not_called()
            fake.send.assert_not_called()
            # the mirror: the scan answered an empty board, so an unknown name is the accurate 404 whatever a
            # later probe would have said
            for path, body in (("/end", {"name": self.GHOST}), ("/interrupt", {"name": self.GHOST}),
                               ("/send", {"name": self.GHOST, "text": "hello"})):
                calls = []
                with mock.patch.object(km._TMUX, "_run", _scripted_run([empty, None], calls)):
                    code, resp = self._post(path, body)
                self._assert_404(code, resp)
                self.assertIn("no live session named '%s'" % self.GHOST, resp.get("error", ""), path)
                self.assertEqual(len(calls), 1, "%s forked tmux %d times: %r" % (path, len(calls), calls))
            # the scan that lists the session admits it by name, from that one fork
            calls = []
            with mock.patch.object(km._TMUX, "_run", _scripted_run([ok_sid_x], calls)):
                code, resp = self._post("/interrupt", {"name": "web"})
            self.assertEqual((code, resp), (200, {"ok": True}))
            fake.interrupt.assert_called_once_with("sid-x")
            self.assertEqual(len(calls), 1, calls)

    def test_the_refusal_path_forks_tmux_once_on_a_tmux_box(self):
        # the scans-once pin above counts Sessions.live calls under the fixture's tmux-off patch, so it could
        # not see the second fork: on a tmux box every by-name 404 and every far-name forward forked tmux
        # twice, the resolution's list-sessions plus the round-5 alive_sids probe, where the docstrings promised
        # one scan. Counted at the fork: one list-sessions per refused request on all three routes and one on
        # the far-name forward; by id the names registry answers and nothing forks (review round 6, 2026-09-09).
        import subprocess
        empty = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        calls = []
        fake = mock.Mock()
        srv = _far_kernel(200, json.dumps({"ok": True}))
        row = _remote_row(srv, sids=[FAR_SID], names={FAR_SID: "far-web"})
        try:
            with mock.patch.object(km._TMUX, "available", lambda: True), \
                 mock.patch.object(km._TMUX, "_run", lambda args, t=3: calls.append(list(args)) or empty), \
                 mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km, "_push_soon", lambda *a, **k: None), \
                 mock.patch.dict(km._remotes, {"TESTHOST": row}, clear=True):
                for path, body in (("/end", {"name": self.GHOST}), ("/interrupt", {"name": self.GHOST}),
                                   ("/send", {"name": self.GHOST, "text": "hello"})):
                    del calls[:]
                    code, resp = self._post(path, body)
                    self._assert_404(code, resp)
                    forks = [c for c in calls if c[:1] == ["list-sessions"]]
                    self.assertEqual(len(forks), 1, "%s forked tmux %d times: %r" % (path, len(forks), calls))
                del calls[:]
                code, resp = self._post("/interrupt", {"name": "far-web"})
                self.assertEqual((code, resp), (200, {"ok": True}))
                forks = [c for c in calls if c[:1] == ["list-sessions"]]
                self.assertEqual(len(forks), 1, "the far-name forward forked tmux %d times: %r" % (len(forks), calls))
                del calls[:]
                code, resp = self._post("/interrupt", {"id": "sid-x"})
                self.assertEqual((code, resp), (200, {"ok": True}))
                self.assertEqual(calls, [], "by id the names registry answers and nothing forks")
            # an ADMITTED /send by name through the real backend_for: the arm reads the resolution's scan for
            # the dead-pane verdict instead of forking alive_sids (review round 7, 2026-09-09: two forks)
            server = _tmux_server(["sid-x"])
            del calls[:]
            with mock.patch.object(km._TMUX, "available", lambda: True), \
                 mock.patch.object(km._TMUX, "_run", lambda args, t=3: calls.append(list(args)) or server(args, t)), \
                 mock.patch.object(km, "_send_or_park", lambda be, sid, text: True), \
                 mock.patch.object(km, "_route_meta_command", lambda be, sid, text, state=None: False), \
                 mock.patch.object(km, "_push_soon", lambda *a, **k: None):
                code, resp = self._post("/send", {"name": "web", "text": "hello"})
                self.assertEqual((code, resp), (200, {"ok": True, "queued": False}))
                forks = [c for c in calls if c[:1] == ["list-sessions"]]
                self.assertEqual(len(forks), 1, "the admitted by-name send forked tmux %d times: %r" % (len(forks), calls))
        finally:
            srv.shutdown()
        self.assertEqual(srv.received, [("/interrupt", {"id": FAR_SID})])

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
                # the reg cause promises a retry only while a backend reports the session running (its next
                # flip rewrites the row); nothing runs sid-q here, so both doors name the record and the way
                # out instead of "Try again" (review round 5, 2026-09-09)
                self.assertNotIn("try again", resp.get("error", "").lower())
                self.assertIn(km._tilde(str(reg_path)), resp.get("error", ""))
                self.assertIn("needs repair or removal", resp.get("error", ""))
                self.assertNotIn("try again", faileds[0]["text"].lower())
                self.assertIn("needs repair or removal", faileds[0]["text"])
                with mock.patch.object(km, "_sdk", lambda be=_sdk_reporting(["sid-q"]): be):
                    reg_path.write_text(json.dumps({"sid": "sid-q", "alive": True}))
                    code, resp = self._post("/end", {"id": "sid-q"})
                    self.assertIn("the session's record could not be read; try again", resp.get("error", ""))
                    self.assertNotIn("repair", resp.get("error", ""))
                    del faileds[:]
                    reg_path.write_text(json.dumps({"sid": "sid-q", "alive": True}))
                    self.assertTrue(km._drive({"type": "endSession", "id": "sid-q"}, client))
                    self.assertIn("could not be read. Try again.", faileds[0]["text"])
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
        # dashboard's endSession op and refused 404 by /end, /interrupt and /send (review round 4,
        # 2026-09-09). Round 5 found the doors apart again on a record that will not read: the dashboard
        # called it a session this kernel does not have (the modal for a foreign sid) where `romp end` said
        # 503; a names-registered session on such a row passed the WS gate into the tmux fallthrough while
        # HTTP refused it; a LIVE session on such a row was refused by HTTP and served by WS. One gate now,
        # _session_gate, and this table holds both doors to a three-way verdict per state: admitted (the op
        # reaches the backend at both doors), unknown (the WS err frame for a session the kernel has no
        # record of; HTTP 404) or unreadable (the WS err frame naming the record; HTTP 503; "try again" at
        # neither, since no writer serves it). A running session is admitted whatever its record reads. The
        # map _resolve_sid read is what the routes hand the gate, so the refusal path still scans once.
        # Round 6: the table is driven through the REAL Sessions.live() scan (real reg files under the test's
        # state dir, a stubbed tmux server), never a hand-built map. A hand-built row stood for "running",
        # while the SDK half of the real map lists every alive=True reg, dormant included, and serves a
        # corrupt reg's last good cached row (the pusher keeps the cache warm while the kernel runs), so a
        # dormant session whose record broke after the scan had cached it was admitted at both doors and fell
        # through to tmux. Running, for a torn record, means the SDK backend runs the session now (running_sids):
        # an SDK row in the map is a reg that says alive, never liveness, and a tmux pane carrying the sid is no
        # writer for the reg, so it is the record's verdict too (round 9; rounds 6 to 8 admitted it, an answer that
        # depended on the list_regs cache, since a warm cache serves the torn reg's last good row as an SDK row
        # that overwrites the pane's in the merge). A reg that is a JSON list is on disk before the SDK backend is
        # first built, so the build reads it.
        dead, named, live = ("aaaa1111-2222-3333-4444-555555555555", "bbbb1111-2222-3333-4444-555555555555",
                             "cccc1111-2222-3333-4444-555555555555")
        bad_thread, bad_named, bad_list = ("dddd1111-2222-3333-4444-555555555555",
                                           "eeee1111-2222-3333-4444-555555555555",
                                           "ffff1111-2222-3333-4444-555555555555")
        bad_live_tmux, bad_live_sdk, bad_running = ("abab1111-2222-3333-4444-555555555555",
                                                    "baba1111-2222-3333-4444-555555555555",
                                                    "cdcd1111-2222-3333-4444-555555555555")
        sdir = km.jd.STATE / "sdk"
        sdir.mkdir(parents=True, exist_ok=True)
        regs = [sdir / (s + ".json") for s in (dead, bad_thread, bad_named, bad_list, bad_live_tmux, bad_live_sdk,
                                                bad_running)]
        (sdir / (dead + ".json")).write_text(json.dumps({"sid": dead, "alive": False, "cwd": "/tmp"}))
        for sid in (bad_thread, bad_named, bad_live_tmux, bad_running):
            (sdir / (sid + ".json")).write_bytes(b"{not json")
        (sdir / (bad_list + ".json")).write_bytes(json.dumps([1, 2]).encode())
        _register(THREAD_PARENT, "web-parent")
        _mk_thread(THREAD_PARENT, THREAD_TSID, THREAD_NAME)
        _register(named, "named-only")
        _register(bad_named, "named-bad")
        _register(bad_live_tmux, "live-bad-tmux")
        _register(bad_live_sdk, "live-bad-sdk")
        states = (("no record", self.GHOST, "unknown"),
                  ("dead SDK reg, no names entry", dead, "admitted"),
                  ("comment thread", THREAD_TSID, "admitted"),
                  ("names entry only", named, "admitted"),
                  ("a tmux pane carries the sid, unregistered", live, "admitted"),
                  ("a reg that will not read, no names entry (a thread's)", bad_thread, "unreadable"),
                  ("names-registered, dormant, a reg that will not read", bad_named, "unreadable"),
                  ("a reg that is a JSON list, no names entry", bad_list, "unreadable"),
                  ("names-registered, a reg that will not read, a tmux pane carries the sid", bad_live_tmux,
                   "unreadable"),
                  ("names-registered, a reg that broke after the scan cached it: in the live map on the SDK "
                   "backend, no thread runs it", bad_live_sdk, "unreadable"),
                  ("a reg that will not read, the SDK backend runs it", bad_running, "admitted"))
        status = {"admitted": 200, "unknown": 404, "unreadable": 503}
        frames = []
        client = {"send": lambda s: frames.append(json.loads(s))}
        fake = mock.Mock()
        km._thread_reg_memo.clear()
        km._thread_reg_failed.clear()
        try:
            with mock.patch.object(km._TMUX, "available", lambda: True), \
                 mock.patch.object(km._TMUX, "_run", _tmux_server([live, bad_live_tmux])), \
                 mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km, "_sdk", lambda be=_sdk_reporting([bad_running]): be), \
                 mock.patch.object(km, "_end_and_record", lambda sid, be, now, via, fresh=False, why=None: True), \
                 mock.patch.object(km, "_send_or_park", lambda be, sid, text: True), \
                 mock.patch.object(km, "_route_meta_command", lambda be, sid, text, state=None: False), \
                 mock.patch.object(km, "_confirm_close_now", lambda sid: None), \
                 mock.patch.object(km, "_send_to_app", lambda app, m: None), \
                 mock.patch.object(km, "_push_soon", lambda *a, **k: None):
                # the warm-cache row: readable when the scan cached it, broken after
                (sdir / (bad_live_sdk + ".json")).write_text(json.dumps({"sid": bad_live_sdk, "alive": True}))
                scan = km.Sessions.live()
                self.assertEqual(scan.get(bad_live_sdk, {}).get("backend"), "sdk", "the scan cached the readable row")
                (sdir / (bad_live_sdk + ".json")).write_bytes(b"{not json")
                km._thread_reg_memo.clear()
                km._thread_reg_failed.clear()
                scan = km.Sessions.live()
                self.assertEqual({s: r.get("backend") for s, r in scan.items() if s in (live, bad_live_tmux, bad_live_sdk)},
                                 {live: "tmux", bad_live_tmux: "tmux", bad_live_sdk: "sdk"},
                                 "the real scan: the stubbed panes on tmux, the cached last good row on sdk")
                self.assertNotIn(bad_list, scan, "an uncached body that is not an object is skipped, hiding no other row")
                for label, sid, expect in states:
                    del frames[:]
                    fake.interrupt.reset_mock()
                    self.assertTrue(km._drive({"type": "interrupt", "id": sid}, client))
                    errs = [f for f in frames if f.get("type") == "err"]
                    if expect == "admitted":
                        self.assertEqual(errs, [], "the WS drive gate on %s" % label)
                        fake.interrupt.assert_called_once_with(sid)
                    else:
                        self.assertEqual(len(errs), 1, "the WS drive gate on %s: %r" % (label, frames))
                        fake.interrupt.assert_not_called()
                        text = errs[0]["text"]
                        if expect == "unknown":
                            self.assertIn("has no session with id", text, label)
                        else:
                            self.assertIn("could not read the record", text.lower(), label)
                            self.assertIn(km._tilde(str(sdir / (sid + ".json"))), text, label)
                            self.assertNotIn("no session with id", text, label)
                            self.assertNotIn("try again", text.lower(), label)
                    for path, body in (("/end", {"id": sid}), ("/interrupt", {"id": sid}),
                                       ("/send", {"id": sid, "text": "hello"})):
                        code, resp = self._post(path, body)
                        self.assertEqual(code, status[expect], "%s on %s answered %s %r" % (path, label, code, resp))
                        if expect == "unknown":
                            self.assertIn("no live session named", resp.get("error", ""), (path, label))
                        elif expect == "unreadable":
                            self.assertIn("could not read the record", resp.get("error", ""), (path, label))
                            self.assertNotIn("try again", resp.get("error", "").lower(), (path, label))
        finally:
            _drop_regs(regs)
            _rm_thread(THREAD_PARENT, THREAD_TSID)
            for sid in (THREAD_PARENT, named, bad_named, bad_live_tmux, bad_live_sdk):
                _unregister(sid)
            km._thread_reg_memo.clear()
            km._thread_reg_failed.clear()

    def test_a_dormant_sessions_record_that_breaks_while_the_kernel_runs_is_unreadable_at_both_doors(self):
        # _backend_reports_running read membership in Sessions.live() as "a backend runs the sid", but the SDK
        # half of that map lists every alive=True reg, dormant included, and list_regs serves a corrupt reg's
        # last good cached row once it has read it (the pusher scans every tick, so the cache is always warm
        # while the kernel runs). So a dormant names-registered SDK session whose record broke after the scan
        # had cached it was ADMITTED at both doors: owns() answered False for the unreadable reg, backend_for
        # fell to tmux, the dashboard's message went to TmuxBackend.send for a pane that did not exist with no
        # modal, no undelivered.jsonl row and no log line, `romp interrupt <name>` sent Esc to a tmux target
        # named after the session, `romp end <sid>` killed a same-named tmux session and said the kill did not
        # take, and _unconfirmed_end_text promised "try again". The 503 the tests modelled appeared only with a
        # cold cache (after a kernel restart). Running means the backend runs the session now: the tmux pane
        # set or running_sids, never an SDK row in the map (review round 6, 2026-09-09). Through the REAL
        # Sessions.live() (tmux off: the map is the SDK half only), by id and by name, at both doors.
        sid, name = "abab2222-3333-4444-5555-666666666666", "warm-web"
        reg_path = km.jd.STATE / "sdk" / (sid + ".json")
        reg_path.parent.mkdir(parents=True, exist_ok=True)
        undelivered = km.jd.STATE / "undelivered.jsonl"
        _register(sid, name)
        frames = []
        client = {"send": lambda s: frames.append(json.loads(s))}
        fake = mock.Mock()
        km._thread_reg_memo.clear()
        km._thread_reg_failed.clear()
        try:
            reg_path.write_text(json.dumps({"sid": sid, "alive": True, "name": name}))
            self.assertEqual(km.Sessions.live().get(sid, {}).get("backend"), "sdk", "the scan cached the readable row")
            reg_path.write_bytes(b"{not json")
            km._thread_reg_memo.clear()
            km._thread_reg_failed.clear()
            self.assertTrue(km._reg_unreadable(sid))
            self.assertIn(sid, km.Sessions.live(), "the premise: the cached last good row is served while the kernel runs")
            before = len(undelivered.read_text().splitlines()) if undelivered.exists() else 0
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda s: fake)), \
                 mock.patch.object(km, "_push_soon", lambda *a, **k: None):
                for path, body in (("/end", {"id": sid}), ("/end", {"name": name}), ("/end", {"name": name, "when": "idle"}),
                                   ("/send", {"id": sid, "text": "hello"}), ("/send", {"name": name, "text": "hello"}),
                                   ("/interrupt", {"id": sid}), ("/interrupt", {"name": name})):
                    code, resp = self._post(path, body)
                    self.assertEqual(code, 503, (path, body, resp))
                    self.assertIn("could not read the record for '%s'" % (body.get("id") or body.get("name")),
                                  resp.get("error", ""), (path, body))
                    self.assertIn(km._tilde(str(reg_path)), resp.get("error", ""), path)
                    self.assertNotIn("try again", resp.get("error", "").lower(), path)
                    self.assertNotIn("no live session", resp.get("error", ""), path)
                self.assertNotIn(sid, km._end_on_idle_load(), "a refused deferred end records no wish")
                self.assertTrue(km._drive({"type": "sendMessage", "id": sid, "text": "keep this text"}, client))
                errs = [f for f in frames if f.get("type") == "err"]
                self.assertEqual(len(errs), 1, frames)
                self.assertIn("could not read the record", errs[0]["text"].lower())
                self.assertIn(km._tilde(str(reg_path)), errs[0]["text"])
                self.assertNotIn("no session with id", errs[0]["text"])
                self.assertNotIn("try again", errs[0]["text"].lower())
                self.assertEqual(errs[0]["copy"], "keep this text")
                rows = [json.loads(x) for x in undelivered.read_text().splitlines()][before:]
                self.assertEqual([(r["op"], r["sid"], r["what"], r["text"]) for r in rows],
                                 [("sendMessage", sid, "message", "keep this text")], "the typed text is kept verbatim")
                self.assertEqual(fake.method_calls, [], "nothing reached a backend at either door")
                # the corroboration's phrasing for the same record: no writer serves a retry
                self.assertNotIn("try again", km._unconfirmed_end_text({"cause": "reg"}, sid=sid).lower())
                self.assertIn(km._tilde(str(reg_path)), km._unconfirmed_end_text({"cause": "reg"}, sid=sid))
                self.assertNotIn("Try again", km._unconfirmed_end_text({"cause": "reg"}, name=name, sid=sid))
        finally:
            km._end_on_idle_save(km._end_on_idle_load() - {sid})
            _unregister(sid)
            _drop_regs([reg_path])
            km._thread_reg_memo.clear()
            km._thread_reg_failed.clear()

    def test_a_reg_that_is_a_json_list_hides_no_other_sdk_session(self):
        # list_regs ran setdefault on whatever json.loads returned, so a reg whose body is valid JSON but not
        # an object raised out of the scan; Sessions.live() caught that around the WHOLE SDK half and dropped
        # every SDK row, so by-name resolution of every OTHER SDK session answered 404 "no live session named"
        # while the corrupt sid itself was gated unreadable, and a first SdkBackend build with such a file on
        # disk failed, leaving the kernel with no SDK backend for its lifetime (review round 6, 2026-09-09).
        # Through the REAL Sessions.live(): the good session resolves by name beside the broken file, which is
        # skipped with one log line.
        good, bad, name = "a1a12222-3333-4444-5555-666666666666", "b2b22222-3333-4444-5555-666666666666", "good-web"
        sdir = km.jd.STATE / "sdk"
        sdir.mkdir(parents=True, exist_ok=True)
        good_path, bad_path = sdir / (good + ".json"), sdir / (bad + ".json")
        _register(good, name)
        good_path.write_text(json.dumps({"sid": good, "alive": True, "name": name}))
        bad_path.write_bytes(json.dumps([1, 2]).encode())
        fake = mock.Mock()
        km._thread_reg_memo.clear()
        km._thread_reg_failed.clear()
        try:
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                scan = km.Sessions.live()
            self.assertEqual(scan.get(good, {}).get("backend"), "sdk", scan)
            self.assertNotIn(bad, scan)
            self.assertIn("list_regs: read failed for %s.json (ValueError)" % bad, err.getvalue())
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda s: fake)), \
                 mock.patch.object(km, "_send_or_park", lambda be, sid, text: True), \
                 mock.patch.object(km, "_route_meta_command", lambda be, sid, text, state=None: False), \
                 mock.patch.object(km, "_push_soon", lambda *a, **k: None):
                code, resp = self._post("/send", {"name": name, "text": "hello"})
                self.assertEqual((code, resp), (200, {"ok": True, "queued": False}))
                code, resp = self._post("/interrupt", {"name": name})
                self.assertEqual((code, resp), (200, {"ok": True}))
                fake.interrupt.assert_called_once_with(good)
                code, resp = self._post("/interrupt", {"id": bad})
                self.assertEqual(code, 503, resp)
                self.assertIn("could not read the record", resp.get("error", ""))
        finally:
            _unregister(good)
            _drop_regs([good_path, bad_path])
            km._thread_reg_memo.clear()
            km._thread_reg_failed.clear()

    def test_sid_of_keeps_its_fallback_for_a_torn_dormant_name_and_the_pr_watch_contact_reads_the_alive_generation(self):
        # _resolve_sid's round-5 miss path returned _unreadable_dormant_named(who) or who, and _sid_of is its
        # first field, so every _sid_of caller took a dormant torn-reg generation of a name the live map does
        # not list while _sid_of's docstring still promised the input unchanged (tests/test_thread_rows.py pins
        # that for a name nobody holds). _pr_watch_contact_sid takes a changed answer as resolved and never asks
        # SdkBackend.sid_for_name, so a PR-watch escalation to a name landed on the older same-named generation
        # with the torn reg and was classified "wait: its record could not be read" every tick with no bound;
        # add_pr_watch and add_watch store the same answer. The lookup is _control_target's own now (the routes'
        # 503 by name stands) and _sid_of hands the name back unchanged, so the contact resolves through the
        # durable record to the alive generation (review round 6, 2026-09-09). Two generations of one name,
        # both registered: A dormant with its reg torn, B alive by its reg; the live map lists neither.
        a, b, name = "a0a03333-4444-5555-6666-777777777777", "b0b03333-4444-5555-6666-777777777777", "torn-web"
        sdir = km.jd.STATE / "sdk"
        sdir.mkdir(parents=True, exist_ok=True)
        a_path, b_path = sdir / (a + ".json"), sdir / (b + ".json")
        _register(a, name)
        _register(b, name)
        a_path.write_bytes(b"{not json")
        b_path.write_text(json.dumps({"sid": b, "alive": True, "name": name}))
        fake = mock.Mock()
        km._thread_reg_memo.clear()
        km._thread_reg_failed.clear()
        try:
            with mock.patch.object(km.Sessions, "live", staticmethod(lambda: {})), \
                 mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km, "_push_soon", lambda *a, **k: None):
                self.assertEqual(km._sid_of(name), name, "the documented fallback: the input unchanged")
                self.assertEqual(km._pr_watch_contact_sid(name), b,
                                 "the escalation contact is the alive generation, through the durable record")
                # the routes keep the by-name 503 for the torn record: the lookup is their own
                code, resp = self._post("/interrupt", {"name": name})
                self.assertEqual(code, 503, resp)
                self.assertIn("could not read the record for '%s'" % name, resp.get("error", ""))
                self.assertIn(km._tilde(str(a_path)), resp.get("error", ""))
                fake.interrupt.assert_not_called()
        finally:
            _unregister(a)
            _unregister(b)
            _drop_regs([a_path, b_path])
            km._thread_reg_memo.clear()
            km._thread_reg_failed.clear()

    def test_a_dormant_sessions_record_that_will_not_read_is_a_503_by_name_too(self):
        # the failed-read-as-404 class was closed for threads and by id in round 4 and stayed open by name:
        # a dormant names-registered session's name resolves only through the live map, and list_regs lists
        # a corrupt reg only when it has cached a good row for it (an uncached one is omitted), so `romp end
        # <name>` answered 404 "no live session named" on every attempt for a session whose record `romp end
        # <sid>` said it could not read. The routes' resolution hands back the registered sid for exactly
        # this record (_unreadable_dormant_named), and the gate answers its 503 (review round 5, 2026-09-09).
        # A dormant session with a READABLE record keeps the by-name contract: a dormant session is addressed
        # by id, 404 by name and admitted by id.
        dormant, name = "dddd2222-3333-4444-5555-666666666666", "dormant-web"
        reg_path = km.jd.STATE / "sdk" / (dormant + ".json")
        reg_path.parent.mkdir(parents=True, exist_ok=True)
        _register(dormant, name)
        reg_path.write_bytes(b"{not json")
        fake = mock.Mock()
        km._thread_reg_memo.clear()
        km._thread_reg_failed.clear()
        try:
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km.Sessions, "live", staticmethod(lambda: {})), \
                 mock.patch.object(km, "_push_soon", lambda *a, **k: None):
                for path, body in (("/end", {"name": name}), ("/end", {"name": name, "when": "idle"}),
                                   ("/send", {"name": name, "text": "hello"}), ("/interrupt", {"name": name})):
                    code, resp = self._post(path, body)
                    self.assertEqual(code, 503, (path, body, resp))
                    self.assertIn("could not read the record for '%s'" % name, resp.get("error", ""), path)
                    self.assertIn(km._tilde(str(reg_path)), resp.get("error", ""), path)
                    self.assertNotIn("no live session", resp.get("error", ""), path)
                self.assertNotIn(dormant, km._end_on_idle_load(), "a refused deferred end records no wish")
                fake.kill.assert_not_called()
                fake.send.assert_not_called()
                fake.interrupt.assert_not_called()
                # the record reads again: by name it is the dormant session it always was, by id admitted
                reg_path.write_text(json.dumps({"sid": dormant, "alive": False}))
                km._thread_reg_memo.clear()
                code, resp = self._post("/interrupt", {"name": name})
                self.assertEqual(code, 404, resp)
                self.assertIn("no live session named '%s'" % name, resp.get("error", ""))
                code, resp = self._post("/interrupt", {"id": dormant})
                self.assertEqual((code, resp), (200, {"ok": True}))
                fake.interrupt.assert_called_once_with(dormant)
        finally:
            km._end_on_idle_save(km._end_on_idle_load() - {dormant})
            _unregister(dormant)
            try:
                reg_path.unlink()
            except OSError:
                pass
            km._thread_reg_memo.clear()
            km._thread_reg_failed.clear()

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
                        # no writer serves a retry for a record no backend holds live: the text names the
                        # file and the way out instead (review round 5, 2026-09-09)
                        self.assertNotIn("try again", resp.get("error", "").lower(), (bad, path))
                        self.assertIn(km._tilde(str(reg_path)), resp.get("error", ""), (bad, path))
                        self.assertIn("drops the session from the board", resp.get("error", ""), (bad, path))
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
                        self.assertNotIn("try again", resp.get("error", "").lower(), path)
                        self.assertIn(km._tilde(str(km.jd.STATE / "comments")), resp.get("error", ""), path)
                    # a sid the registry holds never reaches the store: a local session wins
                    code, resp = self._post("/interrupt", {"id": "sid-x"})
                    self.assertEqual((code, resp), (200, {"ok": True}))
                    # the store's 503 holds a BARE name only: the roster's host:name spelling is no thread's, so
                    # the unreadable store is not what fails it and it forwards (review round 7, 2026-09-09: the
                    # guard was unpinned)
                    srv = _far_kernel(200, json.dumps({"ok": True}))
                    try:
                        with mock.patch.dict(km._remotes, {"TESTHOST": _remote_row(srv, sids=[FAR_SID],
                                                                                   names={FAR_SID: "far-web"})}, clear=True):
                            code, resp = self._post("/interrupt", {"name": "TESTHOST:far-web"})
                            self.assertEqual((code, resp), (200, {"ok": True}))
                            self.assertEqual(srv.received, [("/interrupt", {"id": FAR_SID})])
                            code, resp = self._post("/interrupt", {"name": "far-web"})
                            self.assertEqual(code, 503, resp)
                            self.assertIn("comment threads' store", resp.get("error", ""))
                            self.assertEqual(srv.received, [("/interrupt", {"id": FAR_SID})], "the bare name is held")
                    finally:
                        srv.shutdown()
                self.assertNotIn(THREAD_TSID, km._end_on_idle_load())
                fake.kill.assert_not_called()
                fake.send.assert_not_called()
        finally:
            km._end_on_idle_save(km._end_on_idle_load() - {THREAD_TSID})
            _rm_thread(THREAD_PARENT, THREAD_TSID)
            _unregister(THREAD_PARENT)
            km._thread_reg_memo.clear()
            km._thread_reg_failed.clear()


    def test_a_torn_record_of_the_name_is_the_records_verdict_before_the_scan_is_read(self):
        # round 7 answered a failed scan before a torn dormant generation of the name (try again, the log line,
        # no file named) and reached a pane's generation of the name once the scan answered, so the by-name
        # verdict for a torn record rode the probe and, at a warm list_regs cache, the cache. The doors'
        # resolution reads the on-disk names registry first now: a name registered to a torn record is the
        # record's verdict with the probe down (no scan is made, so no probe-failed log line), with a pane's
        # generation of the name listed (the pane is not reached; the text says a live session of the name is
        # reachable by it again once the file is repaired or removed) and on the no-server exit, and the request
        # forks tmux zero times; with the file removed the same name reaches the pane's generation from the
        # resolution's one fork (review round 10, 2026-09-09).
        import subprocess
        torn_path = km.jd.STATE / "sdk" / ("sid-q" + ".json")
        torn_path.parent.mkdir(parents=True, exist_ok=True)
        torn_path.write_bytes(b"{not json")
        _forget_regs([torn_path])
        km._thread_reg_memo.clear()
        km._thread_reg_failed.clear()
        fake = mock.Mock()
        gone = subprocess.CompletedProcess(args=[], returncode=1, stdout="",
                                           stderr="no server running on /tmp/tmux-1000/default")
        ok_sid_x = _tmux_server(["sid-x"])(["list-sessions", "-F", km.TmuxBackend.LANE_FMT])
        again = "A live session named 'web' is reachable by that name again once the file is repaired or removed."
        try:
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km, "_push_soon", lambda *a, **k: None), \
                 mock.patch.object(km._TMUX, "available", lambda: True):
                for label, run in (("the probe down", lambda *a, **k: None),
                                   ("a pane's generation of the name listed", _tmux_server(["sid-x"])),
                                   ("the no-server exit", lambda *a, **k: gone)):
                    with mock.patch.object(km._TMUX, "_run", run):
                        for path, body in (("/end", {"name": "web"}), ("/interrupt", {"name": "web"}),
                                           ("/send", {"name": "web", "text": "hello"})):
                            err = io.StringIO()
                            with contextlib.redirect_stderr(err):
                                code, resp = self._post(path, body)
                            self.assertEqual(code, 503, (label, path, resp))
                            self.assertIn("could not read the record for 'web'", resp.get("error", ""), (label, path))
                            self.assertIn(km._tilde(str(torn_path)), resp.get("error", ""), (label, path))
                            self.assertIn(again, resp.get("error", ""), (label, path))
                            self.assertNotIn("try again", resp.get("error", "").lower(), (label, path))
                            self.assertNotIn("could not read the live session list", resp.get("error", ""), (label, path))
                            self.assertNotIn("tmux probe failed", err.getvalue(), (label, path, "no scan is made for a torn name"))
                    fake.interrupt.assert_not_called()
                    fake.kill.assert_not_called()
                    fake.send.assert_not_called()
                # zero forks: the script refuses any
                calls = []
                with mock.patch.object(km._TMUX, "_run", _scripted_run([], calls)):
                    code, resp = self._post("/interrupt", {"name": "web"})
                    self.assertEqual(code, 503, resp)
                    self.assertEqual(calls, [], "a torn record of the name forks tmux zero times")
                # the file removed: the pane's generation is the name's again, from the resolution's one fork
                _drop_regs([torn_path])
                km._thread_reg_memo.clear()
                km._thread_reg_failed.clear()
                calls = []
                with mock.patch.object(km._TMUX, "_run", _scripted_run([ok_sid_x], calls)):
                    code, resp = self._post("/interrupt", {"name": "web"})
                self.assertEqual((code, resp), (200, {"ok": True}), "the file removed: the pane's generation is the name's")
                fake.interrupt.assert_called_once_with("sid-x")
                self.assertEqual(len(calls), 1, calls)
        finally:
            _drop_regs([torn_path])
            km._thread_reg_memo.clear()
            km._thread_reg_failed.clear()

    def test_the_ws_by_name_door_reads_a_torn_dormant_record_and_a_failed_scan_as_the_routes_do(self):
        # the WS compact and sendCommand door resolved its NAME through _sid_of, which drops the scan's failure
        # and never consults the torn dormant record, so it said "no session with id web" where the HTTP routes
        # said 503 "could not read" for the same name at both states: a torn dormant names-registered reg the
        # live map does not list (cold list_regs cache; round 6 regressed the door, 478ccdc0 agreed with HTTP),
        # and a tmux probe that did not answer (pre-existing at the base). One miss path now (_named_miss), so
        # the door refuses naming the read, with the typed spelling in the modal, the undelivered.jsonl row and
        # the stderr cause; the no-server exit and a name nobody holds stay the unknown refusal
        # (review round 7, 2026-09-09).
        import subprocess
        torn_path = km.jd.STATE / "sdk" / ("sid-q" + ".json")
        torn_path.parent.mkdir(parents=True, exist_ok=True)
        undelivered = km.jd.STATE / "undelivered.jsonl"
        frames = []
        client = {"send": lambda s: frames.append(json.loads(s))}
        fake = mock.Mock()
        gone = subprocess.CompletedProcess(args=[], returncode=1, stdout="",
                                           stderr="no server running on /tmp/tmux-1000/default")

        def rows_since(n):
            return [json.loads(x) for x in undelivered.read_text().splitlines()][n:] if undelivered.exists() else []

        def drive(op, name, **extra):
            del frames[:]
            before = len(undelivered.read_text().splitlines()) if undelivered.exists() else 0
            err = io.StringIO()
            msg = dict({"type": op, "name": name}, **extra)
            with contextlib.redirect_stderr(err):
                self.assertTrue(km._drive(msg, client))
            errs = [f for f in frames if f.get("type") == "err"]
            return errs, rows_since(before), err.getvalue()
        try:
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km, "_compact_or_park", lambda be, sid: fake.compact(sid)), \
                 mock.patch.object(km, "_send_or_park", lambda be, sid, text: fake.send(sid, text)), \
                 mock.patch.object(km, "_route_meta_command", lambda *a, **k: False), \
                 mock.patch.object(km, "_push_soon", lambda *a, **k: None):
                # the torn dormant record, at a cold cache (the scan lists nothing for sid-q), then warm (round 6's
                # state, built the real way: a good reg the scan cached, then torn; the map serves the cached last
                # good row and _live_names resolves web to sid-q). Since round 10 the doors' resolution reads the torn
                # generation from the names registry FIRST at both warmths, so neither state reads the map for it;
                # the premises stay asserted to show what the map holds in each. Round 7's warm iteration was the
                # cold one repeated: the file was torn before any scan, so nothing was cached and both took the
                # round-7 miss path (review round 8, 2026-09-09)
                for label in ("cold", "warm"):
                    if label == "cold":
                        torn_path.write_bytes(b"{not json")
                        km._thread_reg_memo.clear()
                        km._thread_reg_failed.clear()
                        self.assertNotIn("sid-q", km.Sessions.live(), "cold: the scan lists nothing for the torn sid")
                    else:
                        _drop_regs([torn_path])
                        torn_path.write_text(json.dumps({"sid": "sid-q", "alive": True, "name": "web"}))
                        km._thread_reg_memo.clear()
                        km._thread_reg_failed.clear()
                        self.assertEqual(km.Sessions.live().get("sid-q", {}).get("backend"), "sdk", "the scan cached the readable row")
                        torn_path.write_bytes(b"{not json")
                        km._thread_reg_memo.clear()
                        km._thread_reg_failed.clear()
                        warm = km.Sessions.live()
                        self.assertIn("sid-q", warm, "warm: the map serves the cached last good row")
                        self.assertEqual(km._live_names(warm).get("web"), "sid-q", "the name resolves to the cached row")
                        self.assertTrue(km._reg_unreadable("sid-q"))
                    for op, extra in (("compact", {}), ("sendCommand", {"cmd": "/model opus"})):
                        errs, rows, log = drive(op, "web", **extra)
                        self.assertEqual(len(errs), 1, (label, op, frames))
                        self.assertIn("could not read the record for 'web'", errs[0]["text"].lower(), (label, op))
                        self.assertIn(km._tilde(str(torn_path)), errs[0]["text"], (label, op))
                        self.assertNotIn("no session with id", errs[0]["text"], (label, op))
                        self.assertEqual(errs[0]["sid"], "sid-q", "the modal carries the torn generation's sid")
                        self.assertEqual([(r["op"], r["sid"]) for r in rows], [(op, "sid-q")], (label, op))
                        self.assertIn("undeliverable %s: the record for session sid-q will not read" % op, log, (label, op))
                        self.assertNotIn("no session", log, (label, op))
                        # the name is the session addressed, kept as the row's target and never as the text: a
                        # compact carries no text, a sendCommand's is its cmd (review round 8, 2026-09-09)
                        self.assertEqual(errs[0]["copy"], extra.get("cmd", ""), (label, op))
                        self.assertEqual(errs[0]["title"], "That %s was not delivered" % km._FOREIGN_OP_VERB[op], (label, op))
                        self.assertEqual([(r["what"], r["text"], r["target"]) for r in rows],
                                         [(km._FOREIGN_OP_VERB[op], extra.get("cmd", ""), "web")], (label, op))
                        if op == "compact":
                            self.assertIn("The refusal is recorded in undelivered.jsonl", errs[0]["text"], label)
                            self.assertNotIn("Your text is saved verbatim", errs[0]["text"], label)
                        else:
                            self.assertIn("Your text is saved verbatim", errs[0]["text"], label)
                self.assertEqual(fake.method_calls, [], "nothing reached a backend")
                # a name nobody holds stays the unknown refusal
                errs, rows, log = drive("compact", self.GHOST)
                self.assertEqual(len(errs), 1, frames)
                self.assertIn("has no session with id %s" % self.GHOST, errs[0]["text"])
                # the failed scan: the list could not be read, never a session that does not exist
                _drop_regs([torn_path])
                km._thread_reg_memo.clear()
                km._thread_reg_failed.clear()
                with mock.patch.object(km._TMUX, "available", lambda: True), \
                     mock.patch.object(km._TMUX, "_run", lambda *a, **k: None):
                    for op, extra in (("compact", {}), ("sendCommand", {"cmd": "/model opus"})):
                        errs, rows, log = drive(op, "web", **extra)
                        self.assertEqual(len(errs), 1, (op, frames))
                        self.assertIn("could not read the live session list", errs[0]["text"].lower(), op)
                        self.assertIn("tmux did not answer", errs[0]["text"], op)
                        self.assertIn("try again", errs[0]["text"], op)
                        self.assertNotIn("no session with id", errs[0]["text"], op)
                        self.assertEqual([(r["op"], r["sid"]) for r in rows], [(op, "web")], op)
                        self.assertIn("undeliverable %s: tmux probe failed while resolving 'web'" % op, log, op)
                        self.assertNotIn("no session", log, op)
                        self.assertEqual(errs[0]["copy"], extra.get("cmd", ""), "the name is the target, never the text")
                        self.assertEqual(errs[0]["title"], "That %s was not delivered" % km._FOREIGN_OP_VERB[op], op)
                        self.assertEqual([(r["what"], r["text"], r["target"]) for r in rows],
                                         [(km._FOREIGN_OP_VERB[op], extra.get("cmd", ""), "web")], op)
                        if op == "compact":
                            self.assertIn("The refusal is recorded in undelivered.jsonl", errs[0]["text"])
                            self.assertNotIn("Your text is saved verbatim", errs[0]["text"])
                        else:
                            # the whole modal text, as sentences: the gate's text ended without a period and the
                            # writer joined it to the next sentence (review round 8, 2026-09-09)
                            self.assertEqual(errs[0]["text"],
                                             "Nothing was sent. Could not read the live session list while resolving 'web' "
                                             "(tmux did not answer); nothing was done, try again. Your text is saved verbatim "
                                             "in undelivered.jsonl under romp's state directory.")
                    self.assertEqual(fake.method_calls, [], "nothing reached a backend")
                # the comment threads' store will not read: the miss path's third arm, refused naming the store with
                # the typed spelling and the same three records (round 7 built the arm and tested it at the HTTP door
                # only); the roster's host:name spelling is no thread's, so the store is not what fails it and it
                # stays the unknown refusal (review round 8, 2026-09-09)
                with mock.patch.object(km, "_thread_names", lambda: None):
                    for op, extra in (("compact", {}), ("sendCommand", {"cmd": "/model opus"})):
                        errs, rows, log = drive(op, "web", **extra)
                        self.assertEqual(len(errs), 1, (op, frames))
                        self.assertIn("comment threads' store", errs[0]["text"], op)
                        self.assertIn("'web'", errs[0]["text"], op)
                        self.assertIn(km._tilde(str(km.jd.STATE / "comments")), errs[0]["text"], op)
                        self.assertNotIn("no session with id", errs[0]["text"], op)
                        self.assertNotIn("try again", errs[0]["text"].lower(), op)
                        self.assertEqual(errs[0]["sid"], "web", op)
                        self.assertEqual([(r["op"], r["sid"], r["target"]) for r in rows], [(op, "web", "web")], op)
                        self.assertIn("undeliverable %s: %s" % (op, km._refusal_cause(km._GATE_STORE_UNREADABLE, "web")), log, op)
                        self.assertNotIn("no session", log, op)
                        if op == "sendCommand":
                            self.assertEqual(errs[0]["text"],
                                             "Nothing was sent. Could not read the comment threads' store (%s) while resolving "
                                             "'web'; nothing was done. Your text is saved verbatim in undelivered.jsonl under "
                                             "romp's state directory." % km._tilde(str(km.jd.STATE / "comments")))
                    self.assertEqual(fake.method_calls, [], "nothing reached a backend")
                    errs, rows, log = drive("compact", "TESTHOST:web")
                    self.assertEqual(len(errs), 1, frames)
                    self.assertIn("has no session with id TESTHOST:web", errs[0]["text"])
                    self.assertEqual([(r["op"], r["sid"]) for r in rows], [("compact", "TESTHOST:web")])
                    self.assertEqual(fake.method_calls, [], "nothing reached a backend")
                # the scan answers with the pane: the op reaches the backend for the pane's sid
                with mock.patch.object(km._TMUX, "available", lambda: True), \
                     mock.patch.object(km._TMUX, "_run", _tmux_server(["sid-x"])):
                    errs, rows, log = drive("compact", "web")
                    self.assertEqual(errs, [], frames)
                    fake.compact.assert_called_once_with("sid-x")
                # the no-server exit is the authoritative empty board: a registered name no session runs is unknown
                with mock.patch.object(km._TMUX, "available", lambda: True), \
                     mock.patch.object(km._TMUX, "_run", lambda *a, **k: gone):
                    errs, rows, log = drive("compact", "web")
                    self.assertEqual(len(errs), 1, frames)
                    self.assertIn("has no session with id web", errs[0]["text"])
        finally:
            _drop_regs([torn_path])
            km._thread_reg_memo.clear()
            km._thread_reg_failed.clear()

    def test_a_store_resolved_name_with_no_record_takes_the_miss_path_at_both_doors(self):
        # a comment thread's name the store resolves to its sid, whose SDK reg is absent: the gate reads that
        # sid as unknown, and under a failed tmux probe the routes answered the scan's 503 (try again, the log
        # line) while the WS compact and sendCommand door, which took the miss path for a name handed back
        # unchanged only, refused it as a session that does not exist, by the thread's sid. The live map is
        # incomplete when the scan failed, so a live namesake could have won the resolution had tmux answered,
        # and a 404 there reports a transient failure as a permanent absence. Both doors take the miss path on
        # every unknown verdict for a typed name now: the scan's verdict with the typed spelling, and on the
        # no-server exit the unknown refusal at both (the routes' 404 by the typed name, the WS door's by the
        # resolved sid). The corollary: a torn names-registered generation of the same name answers its
        # record's 503 at the WS door as the routes do (review round 8, 2026-09-09).
        import subprocess
        _register(THREAD_PARENT, "web-parent")
        _mk_thread(THREAD_PARENT, THREAD_TSID, THREAD_NAME)
        _drop_regs([km.jd.STATE / "sdk" / (THREAD_TSID + ".json")])   # the store's row stands; the record is absent
        torn = "e0e07777-8888-9999-0000-111111111111"
        torn_path = km.jd.STATE / "sdk" / (torn + ".json")
        km._thread_reg_memo.clear()
        km._thread_reg_failed.clear()
        undelivered = km.jd.STATE / "undelivered.jsonl"
        frames = []
        client = {"send": lambda s: frames.append(json.loads(s))}
        fake = mock.Mock()
        gone = subprocess.CompletedProcess(args=[], returncode=1, stdout="",
                                           stderr="no server running on /tmp/tmux-1000/default")

        def drive(op, **extra):
            del frames[:]
            before = len(undelivered.read_text().splitlines()) if undelivered.exists() else 0
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertTrue(km._drive(dict({"type": op, "name": THREAD_NAME}, **extra), client))
            errs = [f for f in frames if f.get("type") == "err"]
            rows = [json.loads(x) for x in undelivered.read_text().splitlines()][before:] if undelivered.exists() else []
            return errs, rows, err.getvalue()
        try:
            self.assertEqual((km._thread_names() or {}).get(THREAD_NAME, (None,))[0], THREAD_TSID, "the store resolves the name")
            self.assertFalse(km._reg_unreadable(THREAD_TSID), "no record: absent, not torn")
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda sid: fake)), \
                 mock.patch.object(km, "_compact_or_park", lambda be, sid: fake.compact(sid)), \
                 mock.patch.object(km, "_send_or_park", lambda be, sid, text: fake.send(sid, text)), \
                 mock.patch.object(km, "_route_meta_command", lambda *a, **k: False), \
                 mock.patch.object(km, "_push_soon", lambda *a, **k: None), \
                 mock.patch.object(km._TMUX, "available", lambda: True):
                with mock.patch.object(km._TMUX, "_run", lambda *a, **k: None):
                    self.assertEqual(km._resolve_sid(THREAD_NAME)[0], THREAD_TSID, "the resolution answers the thread's sid")
                    for path, body in (("/end", {"name": THREAD_NAME}), ("/interrupt", {"name": THREAD_NAME}),
                                       ("/send", {"name": THREAD_NAME, "text": "hello"})):
                        err = io.StringIO()
                        with contextlib.redirect_stderr(err):
                            code, resp = self._post(path, body)
                        self.assertEqual(code, 503, (path, resp))
                        self.assertIn("could not read the live session list while resolving '%s'" % THREAD_NAME,
                                      resp.get("error", ""), path)
                        self.assertIn("try again", resp.get("error", ""), path)
                        self.assertNotIn(THREAD_TSID, resp.get("error", ""), "the typed spelling, not the resolved sid")
                        self.assertIn("control %s: tmux probe failed while resolving %r; answered 503, nothing done"
                                      % (path, THREAD_NAME), err.getvalue(), path)
                    for op, extra in (("compact", {}), ("sendCommand", {"cmd": "/model opus"})):
                        errs, rows, log = drive(op, **extra)
                        self.assertEqual(len(errs), 1, (op, frames))
                        self.assertIn("could not read the live session list while resolving '%s'" % THREAD_NAME,
                                      errs[0]["text"].lower(), op)
                        self.assertIn("try again", errs[0]["text"], op)
                        self.assertNotIn("no session with id", errs[0]["text"], op)
                        self.assertNotIn(THREAD_TSID, errs[0]["text"], op)
                        self.assertEqual(errs[0]["sid"], THREAD_NAME, "the modal carries the typed name")
                        self.assertEqual([(r["op"], r["sid"]) for r in rows], [(op, THREAD_NAME)], op)
                        self.assertIn("undeliverable %s: tmux probe failed while resolving %r" % (op, THREAD_NAME), log, op)
                        self.assertNotIn("no session", log, op)
                    self.assertEqual(fake.method_calls, [], "nothing reached a backend at either door")
                # the no-server exit is the authoritative empty board: the unknown refusal at both doors
                with mock.patch.object(km._TMUX, "_run", lambda *a, **k: gone):
                    code, resp = self._post("/interrupt", {"name": THREAD_NAME})
                    self.assertEqual(code, 404, resp)
                    self.assertIn("no live session named '%s'" % THREAD_NAME, resp.get("error", ""))
                    errs, rows, log = drive("compact")
                    self.assertEqual(len(errs), 1, frames)
                    self.assertIn("has no session with id %s" % THREAD_TSID, errs[0]["text"])
                    self.assertEqual([(r["op"], r["sid"]) for r in rows], [("compact", THREAD_TSID)])
                    # the corollary: a torn names-registered generation of the name is its record's 503 at both doors
                    _register(torn, THREAD_NAME)
                    torn_path.write_bytes(b"{not json")
                    km._thread_reg_memo.clear()
                    km._thread_reg_failed.clear()
                    self.assertEqual(km._resolve_sid(THREAD_NAME)[0], THREAD_TSID, "the store still answers first")
                    code, resp = self._post("/interrupt", {"name": THREAD_NAME})
                    self.assertEqual(code, 503, resp)
                    self.assertIn("could not read the record for '%s'" % THREAD_NAME, resp.get("error", ""))
                    self.assertIn(km._tilde(str(torn_path)), resp.get("error", ""))
                    for op, extra in (("compact", {}), ("sendCommand", {"cmd": "/model opus"})):
                        errs, rows, log = drive(op, **extra)
                        self.assertEqual(len(errs), 1, (op, frames))
                        self.assertIn("could not read the record for '%s'" % THREAD_NAME, errs[0]["text"].lower(), op)
                        self.assertIn(km._tilde(str(torn_path)), errs[0]["text"], op)
                        self.assertNotIn("no session with id", errs[0]["text"], op)
                        self.assertEqual(errs[0]["sid"], torn, "the modal carries the torn generation's sid")
                        self.assertEqual([(r["op"], r["sid"]) for r in rows], [(op, torn)], op)
                        self.assertIn("undeliverable %s: the record for session %s will not read" % (op, torn), log, op)
                self.assertEqual(fake.method_calls, [], "nothing reached a backend at either door")
                self.assertNotIn(THREAD_TSID, km._end_on_idle_load(), "a refused deferred end records no wish")
        finally:
            km._end_on_idle_save(km._end_on_idle_load() - {THREAD_TSID})
            _rm_thread(THREAD_PARENT, THREAD_TSID)
            _unregister(THREAD_PARENT)
            _unregister(torn)
            _drop_regs([torn_path])
            km._thread_reg_memo.clear()
            km._thread_reg_failed.clear()

    def test_a_torn_record_under_a_failed_probe_is_the_records_verdict_by_id_and_by_name(self):
        # for a names-registered sid whose SDK reg is torn, at a cold list_regs cache (the map lists no row for
        # the sid), _session_gate answered the record's 503 while the probe was down (round 5); rounds 7 and 8
        # then made it the scan's verdict there (try again) and admitted the sid the moment a pane carried it.
        # Both read the live map, whose answer for a torn reg depends on the cache, so the verdict flipped with
        # the warmth of the cache and not with the world. The gate reads no map for a torn record now: by id the
        # record's verdict in every tmux state (the probe down, the no-server exit, a pane carrying the sid), the
        # file named, no "try again", no probe made and so no probe-failed log line, at every door (round 9). By
        # NAME the same since round 10: the doors' resolution reads the torn record from the names registry
        # ahead of any scan, so with the probe down the verdict is the record's, not the scan's (round 9 left it
        # the scan's there: the name resolved to nothing at a cold cache), and the text says a live session of the
        # name is reachable by it again once the file is repaired or removed (review rounds 9 and 10, 2026-09-09;
        # rounds 7 and 8 pinned the flips this test denies).
        import subprocess
        sid, name = "abab7777-8888-9999-0000-111111111111", "torn-pane-web"
        reg_path = km.jd.STATE / "sdk" / (sid + ".json")
        reg_path.parent.mkdir(parents=True, exist_ok=True)
        _register(sid, name)
        reg_path.write_bytes(b"{not json")
        _forget_regs([reg_path])
        km._thread_reg_memo.clear()
        km._thread_reg_failed.clear()
        frames = []
        client = {"send": lambda s: frames.append(json.loads(s))}
        fake = mock.Mock()
        gone = subprocess.CompletedProcess(args=[], returncode=1, stdout="",
                                           stderr="no server running on /tmp/tmux-1000/default")
        record = "could not read the record for '%s'"
        try:
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda s: fake)), \
                 mock.patch.object(km, "_push_soon", lambda *a, **k: None), \
                 mock.patch.object(km._TMUX, "available", lambda: True):
                with mock.patch.object(km._TMUX, "_run", lambda *a, **k: None):
                    self.assertNotIn(sid, km.Sessions.live(), "the premise: a cold cache, the map lists no row for the sid")
                    self.assertFalse(km._backend_reports_running(sid))
                    verdict, text = km._session_gate(sid)
                    self.assertEqual(verdict, km._GATE_UNREADABLE, text)
                    self.assertIn("Repair or remove", text)
                    self.assertIn(km._tilde(str(reg_path)), text, "the record is named: its verdict does not ride the scan")
                    self.assertNotIn("try again", text.lower())
                    for path, body in (("/end", {"id": sid}), ("/interrupt", {"id": sid}),
                                       ("/send", {"id": sid, "text": "hello"})):
                        err = io.StringIO()
                        with contextlib.redirect_stderr(err):
                            code, resp = self._post(path, body)
                        self.assertEqual(code, 503, (path, body, resp))
                        self.assertIn(record % sid, resp.get("error", ""), (path, body))
                        self.assertIn(km._tilde(str(reg_path)), resp.get("error", ""), (path, body))
                        self.assertNotIn("try again", resp.get("error", "").lower(), (path, body))
                        self.assertNotIn("tmux probe failed", err.getvalue(), "by id no probe is made, so none fails")
                    for path, body in (("/end", {"name": name}), ("/interrupt", {"name": name}),
                                       ("/send", {"name": name, "text": "hello"})):
                        err = io.StringIO()
                        with contextlib.redirect_stderr(err):
                            code, resp = self._post(path, body)
                        self.assertEqual(code, 503, (path, body, resp))
                        self.assertIn(record % name, resp.get("error", ""), (path, body))
                        self.assertIn(km._tilde(str(reg_path)), resp.get("error", ""), (path, body))
                        self.assertIn("Repair or remove", resp.get("error", ""), (path, body))
                        self.assertIn("A live session named '%s' is reachable by that name again once the file is "
                                      "repaired or removed." % name, resp.get("error", ""), (path, body))
                        self.assertNotIn("try again", resp.get("error", "").lower(), (path, body))
                        self.assertNotIn("could not read the live session list", resp.get("error", ""), (path, body))
                        self.assertNotIn("tmux probe failed", err.getvalue(), "by name no scan is made for a torn record either")
                    self.assertNotIn(sid, km._end_on_idle_load(), "a refused deferred end records no wish")
                    del frames[:]
                    err = io.StringIO()
                    with contextlib.redirect_stderr(err):
                        self.assertTrue(km._drive({"type": "sendMessage", "id": sid, "text": "keep this"}, client))
                    errs = [f for f in frames if f.get("type") == "err"]
                    self.assertEqual(len(errs), 1, frames)
                    self.assertEqual(errs[0]["copy"], "keep this")
                    self.assertEqual(errs[0]["text"],
                                     "Nothing was sent. Could not read the record for '%s': its registry entry %s exists but "
                                     "will not read; nothing was done. Repair or remove that file (removing it drops the "
                                     "session from the board). Your text is saved verbatim in undelivered.jsonl under romp's "
                                     "state directory." % (sid, km._tilde(str(reg_path))),
                                     "the whole modal text, as sentences (review round 8, 2026-09-09)")
                    self.assertIn("undeliverable sendMessage: the record for session %s will not read; 'keep this'" % sid,
                                  err.getvalue())
                    self.assertNotIn("tmux probe failed", err.getvalue())
                    del frames[:]
                    err = io.StringIO()
                    with contextlib.redirect_stderr(err):
                        self.assertTrue(km._drive({"type": "compact", "name": name}, client))
                    errs = [f for f in frames if f.get("type") == "err"]
                    self.assertEqual(len(errs), 1, frames)
                    self.assertIn("could not read the record for '%s'" % name, errs[0]["text"].lower())
                    self.assertIn(km._tilde(str(reg_path)), errs[0]["text"])
                    self.assertIn("reachable by that name again once the file is repaired or removed", errs[0]["text"])
                    self.assertNotIn("try again", errs[0]["text"].lower())
                    self.assertEqual(errs[0]["sid"], sid, "the modal carries the torn record's sid")
                    self.assertIn("undeliverable compact: the record for session %s will not read" % sid, err.getvalue())
                    self.assertNotIn("tmux probe failed", err.getvalue())
                    self.assertEqual(fake.method_calls, [], "nothing reached a backend at either door")
                with mock.patch.object(km._TMUX, "_run", lambda *a, **k: gone):
                    self.assertEqual(km._session_gate(sid)[0], km._GATE_UNREADABLE, "the no-server exit: the record's verdict")
                    code, resp = self._post("/interrupt", {"id": sid})
                    self.assertEqual(code, 503, resp)
                    self.assertIn(record % sid, resp.get("error", ""))
                    self.assertIn(km._tilde(str(reg_path)), resp.get("error", ""))
                    self.assertNotIn("try again", resp.get("error", "").lower())
                with mock.patch.object(km._TMUX, "_run", _tmux_server([sid])):
                    self.assertEqual(km.Sessions.live().get(sid, {}).get("backend"), "tmux",
                                     "the premise: cold, the pane's row stands in the map")
                    self.assertEqual(km._session_gate(sid)[0], km._GATE_UNREADABLE,
                                     "a pane carries the sid: the record's verdict all the same")
                    for body in ({"id": sid}, {"name": name}):
                        code, resp = self._post("/interrupt", body)
                        self.assertEqual(code, 503, (body, resp))
                        self.assertIn(record % (body.get("id") or body.get("name")), resp.get("error", ""), body)
                        self.assertIn(km._tilde(str(reg_path)), resp.get("error", ""), body)
                        self.assertNotIn("try again", resp.get("error", "").lower(), body)
                    fake.interrupt.assert_not_called()
        finally:
            km._end_on_idle_save(km._end_on_idle_load() - {sid})
            _unregister(sid)
            _drop_regs([reg_path])
            km._thread_reg_memo.clear()
            km._thread_reg_failed.clear()

    def test_a_torn_record_the_map_lists_is_the_records_verdict_whatever_tmux_answers(self):
        # the gate's scan-failed arm answered "try again" for a torn names-registered sid the live map lists as
        # an SDK row (a warm list_regs cache: the reg read once, then broken, the map serving its cached last
        # good row), but no tmux answer can change that verdict: the SDK row wins the merge in Sessions.live()
        # and _backend_reports_running read an SDK row as not running, so the moment the probe answered the
        # verdict flipped to the record's 503 with the real remedy (review round 8, 2026-09-09). Round 9 took the
        # map out of the gate's reading altogether: a torn record is the record's verdict in every tmux state,
        # the probe down, the no-server exit, and a pane carrying the sid, at a warm cache (this test) as at a
        # cold one (the pair tests below). The warm state is built the real way: a good reg, one Sessions.live()
        # read, the file torn, the thread-reg memos cleared; _drop_regs evicts the cached row at the end.
        import subprocess
        sid, name = "dcdc7777-8888-9999-0000-111111111111", "warm-torn-web"
        reg_path = km.jd.STATE / "sdk" / (sid + ".json")
        reg_path.parent.mkdir(parents=True, exist_ok=True)
        _register(sid, name)
        reg_path.write_text(json.dumps({"sid": sid, "alive": True, "name": name}))
        km._thread_reg_memo.clear()
        km._thread_reg_failed.clear()
        frames = []
        client = {"send": lambda s: frames.append(json.loads(s))}
        fake = mock.Mock()
        gone = subprocess.CompletedProcess(args=[], returncode=1, stdout="",
                                           stderr="no server running on /tmp/tmux-1000/default")
        try:
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda s: fake)), \
                 mock.patch.object(km, "_push_soon", lambda *a, **k: None), \
                 mock.patch.object(km._TMUX, "available", lambda: True):
                with mock.patch.object(km._TMUX, "_run", lambda *a, **k: None):
                    scan = km.Sessions.live()
                    self.assertEqual(scan.get(sid, {}).get("backend"), "sdk", "the scan cached the readable row")
                    reg_path.write_bytes(b"{not json")
                    km._thread_reg_memo.clear()
                    km._thread_reg_failed.clear()
                    warm = km.Sessions.live()
                    self.assertTrue(warm.tmux_failed, "the probe is down")
                    self.assertEqual(warm.get(sid, {}).get("backend"), "sdk", "the premise: the map serves the cached row")
                    self.assertTrue(km._reg_unreadable(sid))
                    self.assertFalse(km._backend_reports_running(sid), "an SDK row is not liveness")
                    verdict, text = km._session_gate(sid)
                    self.assertEqual(verdict, km._GATE_UNREADABLE, text)
                    self.assertIn("Repair or remove", text)
                    self.assertNotIn("try again", text.lower())
                    for path, body in (("/end", {"id": sid}), ("/end", {"name": name}), ("/interrupt", {"id": sid}),
                                       ("/interrupt", {"name": name}), ("/send", {"id": sid, "text": "hello"}),
                                       ("/send", {"name": name, "text": "hello"})):
                        who = body.get("id") or body.get("name")
                        err = io.StringIO()
                        with contextlib.redirect_stderr(err):
                            code, resp = self._post(path, body)
                        self.assertEqual(code, 503, (path, body, resp))
                        self.assertIn("could not read the record for '%s'" % who, resp.get("error", ""), (path, body))
                        self.assertIn(km._tilde(str(reg_path)), resp.get("error", ""), (path, body))
                        self.assertIn("Repair or remove", resp.get("error", ""), (path, body))
                        self.assertNotIn("try again", resp.get("error", "").lower(), (path, body))
                        self.assertNotIn("tmux probe failed", err.getvalue(), (path, body))
                    self.assertNotIn(sid, km._end_on_idle_load(), "a refused deferred end records no wish")
                    for msg, who in (({"type": "sendMessage", "id": sid, "text": "keep this"}, sid),
                                     ({"type": "compact", "name": name}, name)):
                        del frames[:]
                        err = io.StringIO()
                        with contextlib.redirect_stderr(err):
                            self.assertTrue(km._drive(msg, client))
                        errs = [f for f in frames if f.get("type") == "err"]
                        self.assertEqual(len(errs), 1, (msg, frames))
                        self.assertIn("could not read the record for '%s'" % who, errs[0]["text"].lower(), msg)
                        self.assertIn("Repair or remove", errs[0]["text"], msg)
                        self.assertNotIn("try again", errs[0]["text"].lower(), msg)
                        self.assertEqual(errs[0]["sid"], sid, msg)
                        self.assertIn("undeliverable %s: the record for session %s will not read" % (msg["type"], sid),
                                      err.getvalue(), msg)
                    self.assertEqual(fake.method_calls, [], "nothing reached a backend at either door")
                # the no-server exit: the same verdict, no flip
                with mock.patch.object(km._TMUX, "_run", lambda *a, **k: gone):
                    self.assertEqual(km._session_gate(sid)[0], km._GATE_UNREADABLE, "tmux answered: the record's verdict")
                    code, resp = self._post("/interrupt", {"name": name})
                    self.assertEqual(code, 503, resp)
                    self.assertIn("could not read the record for '%s'" % name, resp.get("error", ""))
                    self.assertNotIn("try again", resp.get("error", "").lower())
                # a pane carries the sid: the SDK row overwrites the pane's row in the merge, and the record's
                # verdict stands (as it does at a cold cache, where the pane's row stands: the pair tests below)
                with mock.patch.object(km._TMUX, "_run", _tmux_server([sid])):
                    scan = km.Sessions.live()
                    self.assertEqual(scan.get(sid, {}).get("backend"), "sdk", "the SDK row wins the merge")
                    self.assertEqual(km._session_gate(sid)[0], km._GATE_UNREADABLE, "warm: the record's verdict")
                    code, resp = self._post("/interrupt", {"id": sid})
                    self.assertEqual(code, 503, resp)
                    self.assertIn("could not read the record for '%s'" % sid, resp.get("error", ""))
                fake.interrupt.assert_not_called()
        finally:
            km._end_on_idle_save(km._end_on_idle_load() - {sid})
            _unregister(sid)
            _drop_regs([reg_path])
            km._thread_reg_memo.clear()
            km._thread_reg_failed.clear()

    def test_an_admitted_send_by_name_reads_the_resolutions_scan_and_forks_tmux_once(self):
        # an admitted /send to a tmux session addressed by name forked tmux twice: the resolution's
        # list-sessions, then the arm's alive_sids, so the "no pane runs" verdict was a second probe's and a
        # second probe that failed after the first listed the pane answered 503 for a session the request's
        # own scan saw running. The arm reads the map the resolution scanned (through the REAL backend_for:
        # the fork-count test fakes it, which is why it missed this) and falls to alive_sids only when nothing
        # was scanned (by id). The script answers one fork; a second would raise (review round 7, 2026-09-09).
        import subprocess
        ok_sid_x = _tmux_server(["sid-x"])(["list-sessions", "-F", km.TmuxBackend.LANE_FMT])
        sent = []
        with mock.patch.object(km, "_send_or_park", lambda be, sid, text: sent.append((sid, text)) or True), \
             mock.patch.object(km, "_route_meta_command", lambda be, sid, text, state=None: False), \
             mock.patch.object(km, "_push_soon", lambda *a, **k: None), \
             mock.patch.object(km._TMUX, "available", lambda: True):
            calls = []
            with mock.patch.object(km._TMUX, "_run", _scripted_run([ok_sid_x], calls)):
                code, resp = self._post("/send", {"name": "web", "text": "hello"})
            self.assertEqual((code, resp), (200, {"ok": True, "queued": False}))
            self.assertEqual(sent, [("sid-x", "hello")])
            self.assertEqual(len(calls), 1, "the by-name send forked tmux %d times: %r" % (len(calls), calls))
            # by id nothing was scanned: the arm's own probe is the request's one fork, and its failure the 503
            calls = []
            with mock.patch.object(km._TMUX, "_run", _scripted_run([None], calls)):
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    code, resp = self._post("/send", {"id": "sid-x", "text": "hello"})
            self.assertEqual(code, 503, resp)
            self.assertIn("tmux isn't answering", resp.get("error", ""))
            self.assertIn("send sid-x: tmux probe failed; answered 503, nothing delivered", err.getvalue())
            self.assertEqual(len(calls), 1, calls)
            # by id, a pane the arm's own probe does not list is the 409, from that one fork
            calls = []
            empty = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
            with mock.patch.object(km._TMUX, "_run", _scripted_run([empty], calls)):
                code, resp = self._post("/send", {"id": "sid-x", "text": "hello"})
            self.assertEqual(code, 409, resp)
            self.assertEqual(sent, [("sid-x", "hello")], "nothing else was delivered")

    def test_a_send_by_id_to_a_torn_record_a_pane_runs_is_refused_at_the_gate_with_no_fork(self):
        # by id to a names-registered tmux session whose SDK reg is torn, round 7 forked tmux twice (the gate's
        # unreadable arm scanned to ask whether a pane runs the sid, then the /send arm asked alive_sids again)
        # and round 8 once, in _control_target, ahead of the gate, admitting the send when the pane was listed:
        # an answer that depended on the list_regs cache (warm, the cached SDK row overwrote the pane's and the
        # same request was refused). The gate reads no map for a torn record, so the request is the record's
        # 503 with no fork at all when the names registry answers the resolution, and with the resolution's one
        # fork when it does not; the /send arm is never reached (review round 9, 2026-09-09). The script answers
        # a first fork with the pane and fails a second, so a stale answer can never stand in for a fork.
        reg_path = km.jd.STATE / "sdk" / ("sid-x" + ".json")
        reg_path.parent.mkdir(parents=True, exist_ok=True)
        reg_path.write_bytes(b"{not json")
        _forget_regs([reg_path])
        km._thread_reg_memo.clear()
        km._thread_reg_failed.clear()
        ok_sid_x = _tmux_server(["sid-x"])(["list-sessions", "-F", km.TmuxBackend.LANE_FMT])
        sent = []
        try:
            self.assertTrue(km._reg_unreadable("sid-x"))
            with mock.patch.object(km, "_send_or_park", lambda be, sid, text: sent.append((sid, text)) or True), \
                 mock.patch.object(km, "_route_meta_command", lambda be, sid, text, state=None: False), \
                 mock.patch.object(km, "_push_soon", lambda *a, **k: None), \
                 mock.patch.object(km._TMUX, "available", lambda: True):
                for registered, forks in ((True, 0), (False, 1)):
                    if registered:
                        _register("sid-x", "web")           # KNOWN_SIDS registers it; said here for the row below
                    else:
                        _unregister("sid-x")
                    calls = []
                    with mock.patch.object(km._TMUX, "_run", _scripted_run([ok_sid_x, None], calls)):
                        err = io.StringIO()
                        with contextlib.redirect_stderr(err):
                            code, resp = self._post("/send", {"id": "sid-x", "text": "hello"})
                    self.assertEqual(code, 503, (registered, resp))
                    self.assertIn("could not read the record for 'sid-x'", resp.get("error", ""), registered)
                    self.assertIn(km._tilde(str(reg_path)), resp.get("error", ""), registered)
                    self.assertNotIn("try again", resp.get("error", "").lower(), registered)
                    self.assertEqual(len(calls), forks, "registered=%s: the by-id send to a torn record forked tmux %d "
                                     "times: %r" % (registered, len(calls), calls))
                    self.assertNotIn("tmux probe failed", err.getvalue(), registered)
                self.assertEqual(sent, [], "nothing was pasted in either state")
        finally:
            _register("sid-x", KNOWN_SIDS["sid-x"])
            _drop_regs([reg_path])
            km._thread_reg_memo.clear()
            km._thread_reg_failed.clear()

    def _torn_reg_at(self, reg_path, sid, name, cold):
        """The same reg bytes on disk at a cold or a warm list_regs cache: cold forgets any cached row (the
        state a kernel restart leaves); warm writes a good reg, reads it once through the real scan (the map
        lists it on the SDK backend), then tears it, so the scan serves the cached last good row. The
        thread-reg memos are cleared either way (round 9)."""
        if not cold:
            reg_path.write_text(json.dumps({"sid": sid, "alive": True, "name": name}))
            km._thread_reg_memo.clear()
            km._thread_reg_failed.clear()
            self.assertEqual(km.Sessions.live().get(sid, {}).get("backend"), "sdk", "the scan cached the readable row")
        reg_path.write_bytes(b"{not json")
        if cold:
            _forget_regs([reg_path])
        km._thread_reg_memo.clear()
        km._thread_reg_failed.clear()
        self.assertTrue(km._reg_unreadable(sid))

    def test_a_torn_record_a_pane_carries_is_one_verdict_at_a_cold_and_a_warm_cache_at_the_routes(self):
        # one reg, torn, and one pane carrying its sid gave two verdicts by the warmth of the list_regs cache:
        # cold (after a kernel restart, the reg never read while readable) the map listed the pane's row and the
        # gate admitted the sid, so `romp interrupt <sid>` reached the pane; warm (the reg read once, then torn)
        # the cached last good row, an SDK row, overwrote the pane's row in Sessions.live()'s merge and the same
        # request was the record's 503. With the probe down the same flip gave the scan's verdict cold and the
        # record's warm. A verdict must not depend on a cache: a torn reg is the record's verdict at both
        # warmths, pane or no pane, at every route by id and by name, with the probe up and with it down (round
        # 9 by id, and by name with the probe up; round 10 by name with the probe down, the doors' resolution
        # reading the names registry ahead of the map). The same with a live NAMESAKE, a pane carrying another
        # sid registered under the name (round 10: cold the namesake was reached, 200 with the interrupt
        # delivered to it; warm the record's 503), and with a second SDK generation of the name that the SDK
        # backend runs (the same flip, scandir order deciding); the namesake itself stays reachable by id. The
        # text by name says a live session of the name is reachable by it again once the file is repaired or
        # removed. Fails before on the cold side (review rounds 9 and 10, 2026-09-09).
        sid, name = "cdcd7777-8888-9999-0000-111111111111", "pair-web"
        mate = "cdcd7777-8888-9999-0000-222222222222"
        reg_path = km.jd.STATE / "sdk" / (sid + ".json")
        mate_path = km.jd.STATE / "sdk" / (mate + ".json")
        reg_path.parent.mkdir(parents=True, exist_ok=True)
        _register(sid, name)
        fake = mock.Mock()
        requests = (("/interrupt", {"id": sid}), ("/interrupt", {"name": name}), ("/end", {"id": sid}),
                    ("/end", {"name": name}), ("/send", {"id": sid, "text": "hello"}),
                    ("/send", {"name": name, "text": "hello"}))
        again = "A live session named '%s' is reachable by that name again once the file is repaired or removed." % name

        def verdicts(label, reqs):
            out = []
            for path, body in reqs:
                who = body.get("id") or body.get("name")
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    code, resp = self._post(path, body)
                self.assertEqual(code, 503, (label, path, body, resp))
                self.assertIn("could not read the record for '%s'" % who, resp.get("error", ""), (label, path, body))
                self.assertIn(km._tilde(str(reg_path)), resp.get("error", ""), (label, path, body))
                self.assertNotIn("try again", resp.get("error", "").lower(), (label, path, body))
                self.assertNotIn("tmux probe failed", err.getvalue(), (label, path, body))
                if "name" in body:
                    self.assertIn(again, resp.get("error", ""), (label, path, body))
                else:
                    self.assertNotIn("reachable by that name", resp.get("error", ""), (label, path, body))
                out.append((path, who, code, resp.get("error")))
            return out

        def pair(label, panes, cold_backend):
            # the same reg bytes at a cold and a warm cache, the probe up (with `panes` listed) and down
            with mock.patch.object(km._TMUX, "_run", _tmux_server(panes)):
                self._torn_reg_at(reg_path, sid, name, cold=True)
                self.assertEqual(km.Sessions.live().get(sid, {}).get("backend"), cold_backend, ("the premise, cold", label))
                self.assertEqual(km._session_gate(sid)[0], km._GATE_UNREADABLE, ("cold", label))
                cold = verdicts("cold, " + label, requests)
                self._torn_reg_at(reg_path, sid, name, cold=False)
                self.assertEqual(km.Sessions.live().get(sid, {}).get("backend"), "sdk",
                                 ("the premise, warm: the cached row stands in the map", label))
                self.assertEqual(km._session_gate(sid)[0], km._GATE_UNREADABLE, ("warm", label))
                warm = verdicts("warm, " + label, requests)
                self.assertEqual(cold, warm, "one verdict for one world, whatever the cache holds: " + label)
                self.assertNotIn(sid, km._end_on_idle_load(), "a refused deferred end records no wish")
            with mock.patch.object(km._TMUX, "_run", lambda *a, **k: None):
                down = {}
                for warmth, cold_cache in (("warm", False), ("cold", True)):
                    self._torn_reg_at(reg_path, sid, name, cold=cold_cache)
                    if cold_cache:
                        self.assertNotIn(sid, km.Sessions.live(), "cold: the map lists no row for the sid")
                    else:
                        self.assertEqual(km.Sessions.live().get(sid, {}).get("backend"), "sdk", "warm: the cached row")
                    down[warmth] = (km._session_gate(sid), verdicts("%s, probe down, %s" % (warmth, label), requests))
                self.assertEqual(down["cold"], down["warm"],
                                 "the probe down: one verdict by id and by name at both warmths: " + label)
                self.assertEqual(down["cold"][0][0], km._GATE_UNREADABLE)

        try:
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda s: fake)), \
                 mock.patch.object(km, "_push_soon", lambda *a, **k: None), \
                 mock.patch.object(km._TMUX, "available", lambda: True):
                # a live namesake: a pane carrying another sid registered under the same name
                _register(mate, name)
                pair("a live namesake pane bears the name", [mate], None)
                with mock.patch.object(km._TMUX, "_run", _tmux_server([mate])):
                    self.assertEqual(km._live_names(km.Sessions.live()).get(name), mate,
                                     "the premise: the live map resolves the name to the namesake, which the doors no longer read for it")
                    code, resp = self._post("/interrupt", {"id": mate})
                    self.assertEqual((code, resp), (200, {"ok": True}), "the namesake stays reachable by id")
                    fake.interrupt.assert_called_once_with(mate)
                    fake.reset_mock()
                # no namesake: the pane carries the torn sid itself
                _unregister(mate)
                pair("the pane carries the torn sid", [sid], "tmux")
                self.assertEqual(fake.method_calls, [], "nothing reached a backend in any state")
                # a second SDK generation of the name that the SDK backend runs: the same one verdict by name
                _register(mate, name)
                mate_path.write_text(json.dumps({"sid": mate, "alive": True, "name": name}))
                km._thread_reg_memo.clear()
                with mock.patch.object(km, "_sdk", lambda be=_sdk_reporting([mate]): be):
                    pair("a running SDK generation bears the name", [], None)
                    self.assertEqual(km.Sessions.live().get(mate, {}).get("backend"), "sdk", "the premise: the running generation is in the map")
                    self.assertTrue(km._backend_reports_running(mate))
                    code, resp = self._post("/interrupt", {"id": mate})
                    self.assertEqual((code, resp), (200, {"ok": True}), "the running generation by id")
                    fake.interrupt.assert_called_once_with(mate)
                    fake.reset_mock()
                self.assertEqual(fake.method_calls, [], "nothing but the namesake by id reached a backend")
        finally:
            km._end_on_idle_save(km._end_on_idle_load() - {sid})
            _unregister(sid)
            _unregister(mate)
            _drop_regs([reg_path, mate_path])
            km._thread_reg_memo.clear()
            km._thread_reg_failed.clear()

    def test_a_torn_record_a_pane_carries_is_one_verdict_at_a_cold_and_a_warm_cache_at_the_ws_door(self):
        # the WS door's half of the pair above: interrupt and sendMessage by id and compact and sendCommand by
        # name through _drive, the err frame naming the record at both warmths with the pane listed and with the
        # probe down, without and with a live namesake pane bearing the name; the frames' text, sid and copy
        # agree across the cache states, the modal carries the torn record's sid by name too, and the by-name
        # text says a live session of the name is reachable by it again once the file is repaired or removed.
        # Fails before on the cold side (no err frame, fake.interrupt called; with the namesake, the compact
        # reached the namesake) (review rounds 9 and 10, 2026-09-09).
        sid, name = "cdcd8888-9999-0000-1111-222222222222", "pair-ws-web"
        mate = "cdcd8888-9999-0000-1111-333333333333"
        reg_path = km.jd.STATE / "sdk" / (sid + ".json")
        reg_path.parent.mkdir(parents=True, exist_ok=True)
        _register(sid, name)
        frames = []
        client = {"send": lambda s: frames.append(json.loads(s))}
        fake = mock.Mock()
        msgs = ({"type": "interrupt", "id": sid}, {"type": "sendMessage", "id": sid, "text": "keep this"},
                {"type": "compact", "name": name}, {"type": "sendCommand", "name": name, "cmd": "/model opus"})
        again = "A live session named '%s' is reachable by that name again once the file is repaired or removed." % name

        def verdicts(label, ms):
            out = []
            for msg in ms:
                who = msg.get("id") or msg.get("name")
                del frames[:]
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    self.assertTrue(km._drive(msg, client), (label, msg))
                errs = [f for f in frames if f.get("type") == "err"]
                self.assertEqual(len(errs), 1, (label, msg, frames))
                self.assertIn("could not read the record for '%s'" % who, errs[0]["text"].lower(), (label, msg))
                self.assertIn(km._tilde(str(reg_path)), errs[0]["text"], (label, msg))
                self.assertNotIn("try again", errs[0]["text"].lower(), (label, msg))
                self.assertEqual(errs[0]["sid"], sid, (label, msg))
                self.assertIn("undeliverable %s: the record for session %s will not read" % (msg["type"], sid),
                              err.getvalue(), (label, msg))
                self.assertNotIn("tmux probe failed", err.getvalue(), (label, msg))
                if "name" in msg:
                    self.assertIn(again, errs[0]["text"], (label, msg))
                else:
                    self.assertNotIn("reachable by that name", errs[0]["text"], (label, msg))
                out.append((msg["type"], errs[0]["text"], errs[0]["sid"], errs[0].get("copy")))
            return out

        def pair(label, panes, cold_backend):
            with mock.patch.object(km._TMUX, "_run", _tmux_server(panes)):
                self._torn_reg_at(reg_path, sid, name, cold=True)
                self.assertEqual(km.Sessions.live().get(sid, {}).get("backend"), cold_backend, ("the premise, cold", label))
                cold = verdicts("cold, " + label, msgs)
                self._torn_reg_at(reg_path, sid, name, cold=False)
                self.assertEqual(km.Sessions.live().get(sid, {}).get("backend"), "sdk",
                                 ("the premise, warm: the cached row stands in the map", label))
                warm = verdicts("warm, " + label, msgs)
                self.assertEqual(cold, warm, "one verdict for one world, whatever the cache holds: " + label)
                self.assertEqual([c[3] for c in cold], ["", "keep this", "", "/model opus"], "the typed text is offered back")
            with mock.patch.object(km._TMUX, "_run", lambda *a, **k: None):
                down = {}
                for warmth, cold_cache in (("warm", False), ("cold", True)):
                    self._torn_reg_at(reg_path, sid, name, cold=cold_cache)
                    down[warmth] = verdicts("%s, probe down, %s" % (warmth, label), msgs)
                self.assertEqual(down["cold"], down["warm"],
                                 "the probe down: one verdict by id and by name at both warmths: " + label)

        try:
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda s: fake)), \
                 mock.patch.object(km, "_compact_or_park", lambda be, s: fake.compact(s)), \
                 mock.patch.object(km, "_push_soon", lambda *a, **k: None), \
                 mock.patch.object(km._TMUX, "available", lambda: True):
                _register(mate, name)
                pair("a live namesake pane bears the name", [mate], None)
                with mock.patch.object(km._TMUX, "_run", _tmux_server([mate])):
                    self.assertEqual(km._live_names(km.Sessions.live()).get(name), mate,
                                     "the premise: the live map resolves the name to the namesake, which the door no longer reads for it")
                    del frames[:]
                    self.assertTrue(km._drive({"type": "compactSession", "id": mate}, client))
                    self.assertEqual([f for f in frames if f.get("type") == "err"], [], "the namesake stays reachable by id")
                    fake.compact.assert_called_once_with(mate)
                    fake.reset_mock()
                _unregister(mate)
                pair("the pane carries the torn sid", [sid], "tmux")
                self.assertEqual(fake.method_calls, [], "nothing reached a backend in any state")
        finally:
            _unregister(sid)
            _unregister(mate)
            _drop_regs([reg_path])
            km._thread_reg_memo.clear()
            km._thread_reg_failed.clear()

    def test_a_spelling_outside_the_name_alphabet_is_the_unknown_refusal_before_any_file_is_read(self):
        # the gate asked _reg_unreadable for any spelling the resolution handed back unchanged, a path segment
        # included, so `romp end ../<file>` built STATE/sdk/../<file>.json, read a file of the kernel's own under
        # STATE (end-on-idle.json, a JSON list) as a torn registry entry and answered 503 telling the caller to
        # repair or remove it, with a thread-reg log line per request; the names door read `../<file>.json` and
        # `../palette` through NAMES / who as a registry entry and ADMITTED them (the /end route ran the end
        # routine on the spelling); an absolute path replaced the base the same way. Every sid romp mints and
        # every name its doors admit is NAME_RE's, so a spelling outside that alphabet can name nothing local: the
        # unknown refusal at both doors, decided before any path is built from it. The fake open raises a
        # BaseException on every read-mode open while the requests run (no read-swallowing `except Exception` can
        # hide it); the WS door's append to undelivered.jsonl is a write and passes. The probe file is this
        # test's own, so no live state file is written (review round 10, 2026-09-09).
        import builtins
        import io as iolib

        class _Opened(BaseException):
            pass
        real_open = builtins.open
        opened = []

        def guard(file, mode="r", *a, **k):
            if not any(c in str(mode) for c in "wax+"):
                opened.append(str(file))
                raise _Opened("a read-mode open of %s" % (file,))
            return real_open(file, mode, *a, **k)

        def rows_now():
            # the test's own read of the records, through the real open: the fake watches the kernel, not this
            if not undelivered.exists():
                return []
            with real_open(undelivered) as fh:
                return [json.loads(x) for x in fh.read().splitlines()]
        state = km.jd.STATE
        km.NAMES.mkdir(parents=True, exist_ok=True)
        (state / "sdk").mkdir(parents=True, exist_ok=True)      # the directory the record door traverses out of
        probe = state / "r10-probe.json"
        probe.write_text(json.dumps(["11111111-2222-3333-4444-555555555555"]))
        spellings = ("../r10-probe", "../r10-probe.json", str(probe), "web/2", "web 2")
        frames = []
        client = {"send": lambda s: frames.append(json.loads(s))}
        fake = mock.Mock()
        ended = []
        undelivered = state / "undelivered.jsonl"
        km._thread_reg_memo.clear()
        km._thread_reg_failed.clear()

        def refused(who, label):
            for path, body in (("/end", {"id": who}), ("/end", {"name": who}), ("/end", {"name": who, "when": "idle"}),
                                       ("/interrupt", {"id": who}), ("/interrupt", {"name": who}),
                                       ("/send", {"id": who, "text": "hello"}), ("/send", {"name": who, "text": "hello"})):
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    code, resp = self._post(path, body)
                self.assertEqual(code, 404, (label, who, path, body, resp))
                self.assertIn("no live session named '%s'" % who, resp.get("error", ""), (label, who, path, body))
                self.assertNotIn("could not read", resp.get("error", ""), (label, who, path, body))
                self.assertNotIn("thread-reg:", err.getvalue(), (label, who, path, body))
                self.assertNotIn("owns(", err.getvalue(), (label, who, path, body))
            before = len(rows_now())
            for msg in ({"type": "interrupt", "id": who}, {"type": "sendMessage", "id": who, "text": "keep this"},
                        {"type": "endSession", "id": who}, {"type": "compact", "name": who},
                        {"type": "sendCommand", "name": who, "cmd": "/model opus"}):
                del frames[:]
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    self.assertTrue(km._drive(msg, client), (label, who, msg))
                errs = [f for f in frames if f.get("type") == "err"]
                self.assertEqual(len(errs), 1, (label, who, msg, frames))
                self.assertIn("has no session with id %s" % who, errs[0]["text"], (label, who, msg))
                self.assertNotIn("could not read", errs[0]["text"].lower(), (label, who, msg))
                self.assertEqual(errs[0]["sid"], who, (label, who, msg))
                self.assertIn("undeliverable %s: this kernel has no session %s" % (msg["type"], who), err.getvalue(), (label, who, msg))
                self.assertNotIn("thread-reg:", err.getvalue(), (label, who, msg))
            rows = rows_now()[before:]
            self.assertEqual([(r["op"], r["sid"], r["text"], r["target"]) for r in rows],
                             [("interrupt", who, "", ""), ("sendMessage", who, "keep this", ""), ("endSession", who, "", ""),
                              ("compact", who, "", who), ("sendCommand", who, "/model opus", who)],
                             (label, "the refusal is recorded, the typed text kept, the addressed spelling under target"))
        try:
            with mock.patch.object(km.Sessions, "backend_for", staticmethod(lambda s: fake)), \
                 mock.patch.object(km, "_end_and_record", lambda sid, be, now, via, fresh=False, why=None: ended.append(sid) or True), \
                 mock.patch.object(km, "_push_soon", lambda *a, **k: None):
                # first with the real open, so the answer is asserted as the caller sees it (the archive's 503
                # names the probe file here); then with the fake, so the answer is shown to cost no read
                for who in spellings:
                    refused(who, "plain")
                with mock.patch("builtins.open", guard), mock.patch.object(iolib, "open", guard):
                    for who in spellings:
                        refused(who, "guarded")
                    self.assertEqual(opened, [], "no file was opened for reading while the spellings were refused")
                    # the fake bites: a spelling inside the alphabet reads the names registry at once
                    with self.assertRaises(_Opened):
                        km._resolve_sid(self.GHOST, door=True)
            self.assertEqual(ended, [], "the end routine never ran on a spelling")
            self.assertEqual(fake.method_calls, [], "nothing reached a backend at either door")
            for who in spellings:
                self.assertNotIn(who, km._end_on_idle_load(), "a refused deferred end records no wish")
                self.assertFalse(km._local_spelling(who), who)
            self.assertTrue(km._local_spelling(self.GHOST))
            self.assertTrue(km._local_spelling("abab7777-8888-9999-0000-111111111111"))
            self.assertTrue(probe.exists(), "the probe file is untouched")
        finally:
            try:
                probe.unlink()
            except OSError:
                pass
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
