#!/usr/bin/env python3
"""client-diag.jsonl tells a declared redial from one the shim's dial term gated off (2026-09-10).

The landing shim declares a redial (`?reconnect=1` on the /ws URL) only when `everConnected && bundleReady &&
!readyQueued` all hold, and its one drop breadcrumb, the `wsclose` row, recorded `everConnected` alone, so the
kernel's log could not say which kind of redial followed a close: a declared one, a mid-load drop redialed as a
fresh page, or a `ready` that reached the shim while its socket was going down and rode the redial as the page's
own. Two fields fix that, each recorded where it is known:
- the kernel's clientDiag handler stamps EVERY row with `reconnect`, whether the socket that carried the row
  declared the redial. The shim queues the `wsclose` row while its socket is down and flushes it onto the redial
  ahead of the re-sent `ready`, whose strip consumes the flag, so the row is stamped while the flag still stands;
- the shim's `wsclose` row carries `bundleReady`, the shim's state at the close.
The pair: both true, a declared redial; both false, a drop before the bundle said ready; reconnect false with
bundleReady true, the ready queued during the close and the redial carried no term. `readyQueued` is not recorded:
it is false at every close the row is built at, and the pair above already separates the shapes.

Three legs: the handler alone (a client dict with and without the flag), the REAL shim core under node (the
row's field in each shape, and the row's place ahead of the queued ready), and the two joined (the real handshake
dialed with the URL the shim built, the shim's own row dispatched on that client, the pair read back from the
file). Synthetic only: placeholder UUIDs, TESTHOST. Never run raw: pytest's conftest poisons the live ports.
"""
import contextlib
import io
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest
import urllib.parse
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Hermetic state BEFORE the loads: they resolve their state root at import time, and only pytest runs
# conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
km = load_source("romp_kernel_cdiag_reconnect", os.path.join(BIN, "romp-kernel"))

WID = "11111111-2222-3333-4444-555555555556"
S1 = "11111111-2222-3333-4444-555555555551"   # the tab the page persisted as active

# The browser the shim thinks it runs in (tests/test_chat_skeleton_reconnect_gate.py's harness): `var` at module
# scope shadows node's own WebSocket / setTimeout / MessageChannel for the core that follows in the same file.
_SHIM_HARNESS = r"""
var NOW=1000000;Date.now=function(){return NOW;};
var timers=[];var setTimeout=function(fn,ms){timers.push({fn:fn,ms:ms,live:true});return timers.length;};
var clearTimeout=function(id){if(id&&timers[id-1])timers[id-1].live=false;};
var setInterval=function(fn,ms){return 1;};
var docL={};var document={visibilityState:"visible",wasDiscarded:false,
addEventListener:function(t,f){(docL[t]=docL[t]||[]).push(f);},getElementById:function(){return null;}};
var window={innerWidth:800,innerHeight:600,parent:{postMessage:function(m){}},
dispatchEvent:function(e){return true;},sessionStorage:{getItem:function(){return "";}},__rompFed:{inbound:function(h,m){}}};
var location={protocol:"http:",host:"TESTHOST",search:""};
var localStorage={getItem:function(){return JSON.stringify({activeId:"%s"});},setItem:function(){}};
var sockets=[];function WebSocket(url){this.url=url;this.readyState=0;this.sent=[];sockets.push(this);}
WebSocket.prototype.send=function(s){this.sent.push(s);};WebSocket.prototype.close=function(){this.readyState=3;};
function MessageChannel(){this.port1={onmessage:null};this.port2={postMessage:function(d){}};}
function sock(){return sockets[sockets.length-1];}
function open(){var s=sock();s.readyState=1;s.onopen();return s;}
function redial(){var live=timers.filter(function(t){return t.live&&t.fn.name==="connect";});live[live.length-1].fn();}
function drop(){sock().readyState=3;sock().onclose();redial();}
function ready(){window.__rompLocalSend({type:"ready"});}
""" % S1

# the three shapes, as the scenario that drives the first socket to its drop and leaves the redial dialed
DECLARED = "open();ready();drop();"                                   # the bundle said ready on the socket that died
GATED = "open();drop();"                                              # the socket died before the bundle said ready
CLOSING = "open();sock().readyState=2;ready();sock().readyState=3;sock().onclose();redial();"   # the ready landed while the socket was closing


def _shim_close(scenario):
    """Run the REAL shim core under node through `scenario`, then open the redial socket (its onopen flushes the
    queue). Returns the redial's URL query minus the page identity, the frames the redial socket carried in order
    (each clientDiag row as its `what`, every other frame as its type), and the `wsclose` rows it carried."""
    node = shutil.which("node")
    if not node:
        raise unittest.SkipTest("node not installed")
    fx = tempfile.mkdtemp()
    path = os.path.join(fx, "run.js")
    with open(path, "w") as f:
        f.write(_SHIM_HARNESS + km._shim_core_js(app="chat", caps=km.READY_GATE_CAP) + "\n" + scenario
                + "\nvar url=sock().url;open();var fr=sock().sent.map(function(x){return JSON.parse(x);});"
                + "process.stdout.write(JSON.stringify({url:url,"
                + "kinds:fr.map(function(m){return m.type==='clientDiag'?m.what:m.type;}),"
                + "closes:fr.filter(function(m){return m.type==='clientDiag'&&m.what==='wsclose';})}));")
    r = subprocess.run([node, path], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError("node failed:\n" + r.stderr)
    out = json.loads(r.stdout)
    pairs = urllib.parse.parse_qsl(out["url"].split("?", 1)[1], keep_blank_values=True)
    query = "&".join("%s=%s" % (k, v) for k, v in pairs if k not in ("app", "delta", "iid"))
    return query, out["kinds"], out["closes"]


def _fake_self(path):
    """A connect handler with a peer that closes at once (the test_view_deltas.py HandlerWiring shape)."""
    class FakeSelf:
        headers = {"Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ=="}
        rfile = io.BytesIO(); wfile = io.BytesIO()
        connection = type("FakeSock", (), {"sendall": lambda self, b: None, "shutdown": lambda self, how: None})()
        close_connection = False
        def send_response(self, *a): pass
        def send_header(self, *a): pass
        def end_headers(self): pass
    FakeSelf.path = path
    return FakeSelf()


class _State(unittest.TestCase):
    """A private state root per test (km.jd.STATE is shared by every module that loads the judge)."""
    def setUp(self):
        self._saved_state = km.jd.STATE
        self._td = tempfile.TemporaryDirectory()
        km.jd._rebind_state(pathlib.Path(self._td.name))
        self.fp = km.jd.STATE / "client-diag.jsonl"

    def tearDown(self):
        km.jd._rebind_state(self._saved_state)
        self._td.cleanup()

    def rows(self):
        return [json.loads(line) for line in self.fp.read_text(encoding="utf-8").splitlines() if line.strip()]

    def post(self, client, what="wsclose", data=None):
        """One breadcrumb through the real dispatch, on `client`."""
        km.Handler._dispatch_ws(None, {"type": "clientDiag", "surface": "pane-shim", "what": what,
                                       "data": data if data is not None else {"app": "chat", "code": 1006}}, client)


class TheHandlerStampsTheCarryingSocket(_State):
    def test_a_row_on_a_declared_redial_is_stamped_true(self):
        self.post({"wid": WID, "reconnect": True, "redial": True})
        rows = self.rows()
        self.assertEqual(len(rows), 1)
        self.assertIs(rows[0]["reconnect"], True)
        self.assertEqual(sorted(rows[0]), ["data", "reconnect", "surface", "t", "what", "wid"])

    def test_a_row_on_a_fresh_socket_is_stamped_false(self):
        self.post({"wid": WID})                             # a first socket, or a redial that carried no term
        self.post({"wid": WID, "redial": True})             # a declared redial after its strip consumed the flag
        self.post({"wid": WID, "reconnect": False})
        self.assertEqual([r["reconnect"] for r in self.rows()], [False, False, False])

    def test_the_stamp_is_a_bool_whatever_the_flag_holds(self):
        self.post({"wid": WID, "reconnect": 1})
        self.post({"wid": WID, "reconnect": None})
        self.assertEqual([r["reconnect"] for r in self.rows()], [True, False])


class TheShimRowCarriesBundleReady(unittest.TestCase):
    def test_declared_the_bundle_had_said_ready(self):
        q, kinds, closes = _shim_close(DECLARED)
        self.assertTrue(q.endswith("&reconnect=1"), q)
        self.assertEqual(len(closes), 1)
        self.assertIs(closes[0]["data"]["bundleReady"], True)
        self.assertIs(closes[0]["data"]["everConnected"], True)
        self.assertEqual(kinds, ["wsclose", "ready"], "the queued row flushes ahead of the re-sent ready")

    def test_gated_off_the_bundle_had_not_said_ready(self):
        q, kinds, closes = _shim_close(GATED)
        self.assertNotIn("reconnect", q, q)
        self.assertEqual(len(closes), 1)
        self.assertIs(closes[0]["data"]["bundleReady"], False)
        self.assertIs(closes[0]["data"]["everConnected"], True, "everConnected alone could not tell this shape from the declared one")
        self.assertEqual(kinds, ["wsclose"], "no ready to re-send: the bundle has not sent its own")

    def test_a_ready_during_the_close_is_ready_true_with_no_term(self):
        q, kinds, closes = _shim_close(CLOSING)
        self.assertNotIn("reconnect", q, "the ready is still queued for this open, so the redial carries no term")
        self.assertEqual(len(closes), 1)
        self.assertIs(closes[0]["data"]["bundleReady"], True)
        self.assertEqual(kinds, ["ready", "wsclose"], "the bundle's own ready queued first (during the close), once, then the row")

    def test_the_row_is_built_from_the_shim_state_at_the_close(self):
        js = km._shim("chat", caps=km.READY_GATE_CAP)
        self.assertIn("everConnected:everConnected,bundleReady:bundleReady}", js)
        self.assertNotIn("readyQueued:readyQueued", js, "not recorded: false at every close the row is built at")


class ThePairInTheLog(_State):
    """The two halves joined: the real handshake dialed with the URL the shim built, the shim's own wsclose row
    dispatched on the client it registered, and the pair read back from client-diag.jsonl."""
    def setUp(self):
        super().setUp()
        self._clients = list(km._clients)
        del km._clients[:]

    def tearDown(self):
        del km._clients[:]
        km._clients.extend(self._clients)
        super().tearDown()

    def _dial(self, query):
        """The real handshake for one socket whose peer closes at once; returns the client dict it registered."""
        got = []
        real_reg, real_recv = km._register_ws_client, km._ws_recv
        km._register_ws_client = lambda c: (got.append(c), km._clients.append(c))
        km._ws_recv = lambda rfile: (0x8, b"", True)              # the peer closes at once
        km._pusher_wake.clear()
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                km.Handler._ws(_fake_self("/ws?app=chat&delta=1&iid=page-c&wid=%s&" % WID + query))
        finally:
            km._register_ws_client, km._ws_recv = real_reg, real_recv
            for c in got:
                if c in km._clients:
                    km._clients.remove(c)
        self.assertEqual(len(got), 1, query)
        return got[0]

    def _pair(self, scenario):
        q, kinds, closes = _shim_close(scenario)
        c = self._dial(q)
        self.assertIn("wsclose", kinds, "the row rides the redial")
        if c.get("reconnect"):
            self.assertEqual(kinds[0], "wsclose", "on a declared redial the row is flushed ahead of the re-sent ready whose strip consumes the flag")
        km.Handler._dispatch_ws(None, closes[0], c)
        rows = self.rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["what"], "wsclose")
        self.assertEqual(rows[0]["wid"], WID)
        return rows[0]["reconnect"], rows[0]["data"]["bundleReady"]

    def test_declared(self):
        self.assertEqual(self._pair(DECLARED), (True, True))

    def test_gated_off(self):
        self.assertEqual(self._pair(GATED), (False, False))

    def test_ready_during_the_close(self):
        self.assertEqual(self._pair(CLOSING), (False, True))

    def test_the_stamp_reads_the_flag_before_the_strip_consumes_it(self):
        # on a declared redial the flag stands until _resolve_reconnect runs for the strip the re-sent ready
        # triggers; the row is dispatched ahead of that ready (kinds above), so it is stamped True; a row that
        # lands after the strip reads False, and `redial` (never consumed) is not what the stamp reads
        q, kinds, closes = _shim_close(DECLARED)
        c = self._dial(q)
        self.assertIs(c.get("reconnect"), True)
        self.assertIs(c.get("redial"), True)
        km.Handler._dispatch_ws(None, closes[0], c)
        c.pop("reconnect")                                   # what the first strip's _resolve_reconnect does
        km.Handler._dispatch_ws(None, {"type": "clientDiag", "surface": "pane-shim", "what": "stale-raise",
                                       "data": {"app": "chat", "why": "reconnect"}}, c)
        self.assertEqual([(r["what"], r["reconnect"]) for r in self.rows()],
                         [("wsclose", True), ("stale-raise", False)])


if __name__ == "__main__":
    raise SystemExit("run under pytest: a raw run skips conftest and can reach the live kernel")
