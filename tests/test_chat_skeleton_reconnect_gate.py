#!/usr/bin/env python3
"""Reconnect skeletons under the fork's READY_GATE_CAP hold: the differential the 2026-09-09 ruling asked for
(condition 1), run against the real handshake (Handler._ws), the real `ready` handler (Handler._dispatch_ws) and
the real push paths (_push, _push_session_now, _confirm_close_now).

Upstream's #1017 (tests/test_chat_skeleton_reconnect.py, beside this module) pops the skeleton state on `ready`
because there a `ready` comes only from a renderer that just evaluated; a redial socket never sends one. The fork
holds every client that announced READY_GATE_CAP until its bundle says `ready` (slice 1: nothing is pushed at
accept), and its shim re-sends `ready` on a redial once the bundle has sent its own, so on the fork a redial's
`ready` is NOT a fresh evaluation. The fork keeps upstream's behaviour on both paths with a second flag: `redial`,
set at accept beside `reconnect` and never consumed, and a reset that keeps a declared redial's skeleton state.
That flag made the shim's URL term load-bearing, so the shim declares the redial only once the page has held a
socket AND its bundle has said `ready` (`everConnected&&bundleReady`, 2026-09-10): a first socket that opened and
died before the bundle evaluated (the documented mid-load drop) held nothing for the page, and its redial dials as
a fresh page. Path by path, what this module pins:
- a redial socket (?caps=readyGate&reconnect=1) is sent NOTHING before its re-sent `ready`: not by the pusher, not by
  the off-cycle push, not by a close confirmation;
- its first strip after `ready` carries `skeleton`: the reset kept the flag, and the pusher's _resolve_reconnect
  resolves the set on the _push_one the handler runs;
- a later resolve (activeTab, needFull) fills the set, and the strip says so;
- a fresh page (no reconnect term) is held the same way, its `ready` pops the state, and its first strip is full
  with no `skeleton` key: every session whole, as before;
- neither path gets a tabOrder frame from the `ready` handler itself: the guarded push is the only source;
- the two halves joined, with the URL the REAL shim builds under node: a page whose first socket opened and died
  before its bundle's `ready` redials without the reconnect term and its bundle's own `ready` is served everything
  whole; only a page whose bundle had said `ready` before the drop declares the redial and is served skeletons.
Synthetic only: the notes-api demo world (web/api/tests/docs), placeholder UUIDs, TESTHOST. Never run raw: the
loads below set no ROMP_MANAGER_PORT; pytest's conftest poisons the live ports.
"""
import contextlib
import inspect
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
import urllib.parse
from romp_load import load_source
from pathlib import Path

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
km = load_source("romp_kernel_skeleton_gate", os.path.join(BIN, "romp-kernel"))   # a private copy: the globals below are swapped

S1 = "11111111-2222-3333-4444-555555555551"   # web: the tab the page is looking at (mid-size transcript)
S2 = "11111111-2222-3333-4444-555555555552"   # api: the BIGGEST transcript
S3 = "11111111-2222-3333-4444-555555555553"   # tests: the smallest transcript
S4 = "11111111-2222-3333-4444-555555555554"   # docs: just created, no transcript on disk yet
GONE = "11111111-2222-3333-4444-555555555559"  # an ended session, listed nowhere
NAMES = {S1: "web", S2: "api", S3: "tests", S4: "docs"}
TAB_ORDER = [S2, S1, S3, S4]
SIZES = {S2: 3000, S1: 2000, S3: 1000}        # transcript bytes; S4 has none
REDIAL = "active=%s&caps=readyGate&reconnect=1" % S1   # what the fork's shim dials after a drop (caps first, reconnect last)
FRESH = "active=%s&caps=readyGate" % S1               # a page's first socket: the gate announced, no reconnect term

# The browser the shim thinks it runs in, for the tests that dial the kernel with the URL the REAL shim builds
# (tests/test_pane_shim_return.py runs the same core against the same fakes, in more detail: this is its harness
# without the record-keeping). `var` at module scope shadows node's own WebSocket / setTimeout / MessageChannel for
# the core that follows in the same file; the page persisted S1 as its active tab, as the redial reads it.
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
function drop(){sock().readyState=3;sock().onclose();var live=timers.filter(function(t){return t.live&&t.fn.name==="connect";});live[live.length-1].fn();}
""" % S1


def _shim_redial_query(scenario):
    """Run the REAL shim core under node (km._shim_core_js with READY_GATE_CAP announced, as every pane's page
    announces it) through `scenario`, which drives the first socket to its drop and the redial, and return the
    query the redial was dialed with minus the page identity (app, delta, iid): the terms the kernel's accept
    reads (active, caps, reconnect), in the shim's order, ready for _dial."""
    node = shutil.which("node")
    if not node:
        raise unittest.SkipTest("node not installed")
    fx = tempfile.mkdtemp()
    path = os.path.join(fx, "run.js")
    with open(path, "w") as f:
        f.write(_SHIM_HARNESS + km._shim_core_js(app="chat", caps=km.READY_GATE_CAP) + "\n" + scenario
                + "\nprocess.stdout.write(sock().url);")
    r = subprocess.run([node, path], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError("node failed:\n" + r.stderr)
    pairs = urllib.parse.parse_qsl(r.stdout.split("?", 1)[1], keep_blank_values=True)
    return "&".join("%s=%s" % (k, v) for k, v in pairs if k not in ("app", "delta", "iid"))


def _sess(sid, n, state):
    """A synthetic build_session payload: n events (well under WIRE_TAIL, so a full send is the whole thing)."""
    return {"type": "session", "id": sid, "name": NAMES[sid],
            "events": [{"kind": "assistant", "uuid": "u%d" % i, "md": "m%d" % i} for i in range(n)],
            "status": {"state": state, "sinceEpoch": None}, "ledger": None}


class _Self:
    """The handler's `self` for _dispatch_ws: only _push_one is reached by the frames driven here. Records the
    call; runs `push_one` when given one (the real body is _push([client], connect=True))."""
    def __init__(self, push_one=None):
        self.calls = []
        self._po = push_one

    def _push_one(self, client):
        self.calls.append(client)
        if self._po:
            self._po(client)


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


class GateDifferential(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.paths = {}
        for sid, n in SIZES.items():          # real files: os.path.getsize is the kernel's ranking, so it must stat
            p = os.path.join(self.tmp, sid + ".jsonl")
            with open(p, "w") as f:
                f.write("x" * n)
            self.paths[sid] = p
        self.paths[S4] = os.path.join(self.tmp, S4 + ".jsonl")   # never written: the transcript-less session
        self.SESS = {S1: _sess(S1, 5, "working"), S2: _sess(S2, 7, "working"),
                     S3: _sess(S3, 3, "waiting"), S4: _sess(S4, 0, "waiting")}
        self._saved = (km._chat_tab_sessions, km._tmux_sessions, km._cached_feed, km.build_session,
                       km._comments_frame, km._push_subagents, km.NAMES, km.jd.STATE, list(km._clients))
        km._chat_tab_sessions = lambda now, tmux: [
            {"sid": sid, "name": NAMES[sid], "path": self.paths[sid], "anchor": sid} for sid in TAB_ORDER]
        km._tmux_sessions = lambda: {}
        km._cached_feed = lambda *a, **k: None          # no feed build: the chat frames are what is pinned

        def build(sid, now, tmux=None, **kw):
            return json.loads(json.dumps(self.SESS[sid]))   # a fresh copy per build, as the real builder returns
        km.build_session = build
        km._comments_frame = lambda sid, tmux: None
        km._push_subagents = lambda clients, now, tmux: None
        km.NAMES = Path(self.tmp) / "names"
        km.NAMES.mkdir()
        km.jd.STATE = Path(self.tmp) / "state"
        km.jd.STATE.mkdir(parents=True, exist_ok=True)
        km._built_chat.clear()
        km._prev_chat_events.clear()
        km._prev_chat_ledger.clear()
        del km._clients[:]
        km._pusher_wake.clear()

    def tearDown(self):
        (km._chat_tab_sessions, km._tmux_sessions, km._cached_feed, km.build_session,
         km._comments_frame, km._push_subagents, km.NAMES, km.jd.STATE, clients) = self._saved
        del km._clients[:]
        km._clients.extend(clients)
        km._built_chat.clear()
        km._prev_chat_events.clear()
        km._prev_chat_ledger.clear()

    # ── helpers ──
    def _dial(self, query):
        """Run the real handshake for one socket whose peer closes at once and return the client dict it
        registered, re-armed as a recording client: the handler's teardown marked it dead and ended its sender
        thread with the closed peer, so `send` records the frames the push paths enqueue instead."""
        got = []
        real_reg, real_recv = km._register_ws_client, km._ws_recv
        km._register_ws_client = lambda c: (got.append(c), km._clients.append(c))
        km._ws_recv = lambda rfile: (0x8, b"", True)              # the peer closes at once
        km._pusher_wake.clear()
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                km.Handler._ws(_fake_self("/ws?app=chat&delta=1&iid=page-g&" + query))
        finally:
            km._register_ws_client, km._ws_recv = real_reg, real_recv
            for c in got:
                if c in km._clients:
                    km._clients.remove(c)
        self.assertEqual(len(got), 1, query)
        c = got[0]
        frames = []
        c["send"] = lambda s: frames.append(json.loads(s))
        c["_frames"] = frames
        c["alive"] = True
        c.setdefault("sent", {})
        return c

    @staticmethod
    def _frames(c, typ=None):
        return [f for f in c["_frames"] if typ is None or f["type"] == typ]

    def _sessions(self, c):
        return [f["id"] for f in self._frames(c, "session")]

    def _statuses(self, c):
        return [(f["id"], f["status"]) for f in self._frames(c, "status")]

    def _tab_orders(self, c):
        return self._frames(c, "tabOrder")

    def _every_sender(self, c):
        """Every push path a chat client can be reached by, run once: the pusher (its periodic and connect forms),
        the off-cycle session push and the close confirmation."""
        km._push([c])
        km._push([c], connect=True)
        km._push_session_now(S3)
        self.assertTrue(km._confirm_close_now(GONE))

    # ── the redial path ──
    def test_01_a_redial_is_held_until_its_re_sent_ready_and_its_first_strip_after_it_is_skeleton_marked(self):
        c = self._dial(REDIAL)
        self.assertIs(c.get("reconnect"), True, "the shim's statement, recorded at accept")
        self.assertIs(c.get("redial"), True, "the ruling's flag, set at accept beside it")
        self.assertFalse(c["ready"], "a page that announced the gate is held")
        self.assertFalse(km._client_ready(c))
        # nothing before ready: every sender filters on the hold, and none saw the flag
        km._clients.append(c)
        self._every_sender(c)
        self.assertEqual(c["_frames"], [], "a held redial is sent nothing")
        self.assertIs(c.get("reconnect"), True, "the flag is untouched: no sender saw it")
        self.assertNotIn("skeleton", c)
        # the shim's re-sent ready: the handler re-bases the tails and KEEPS the declared redial's state
        h = _Self()                                   # records the _push_one call without running it
        km.Handler._dispatch_ws(h, {"type": "ready"}, c)
        self.assertTrue(c["ready"], "the hold lifts")
        self.assertEqual(h.calls, [c], "the guarded push is asked for")
        self.assertIs(c.get("reconnect"), True, "the reset keeps a declared redial's flag (upstream's pop is for a fresh evaluation)")
        self.assertIs(c.get("redial"), True, "never consumed")
        self.assertEqual(self._tab_orders(c), [], "the ready handler sends no strip of its own")
        self.assertEqual(self._sessions(c), [])
        self.assertEqual(self._statuses(c), [])
        # the push the handler asked for: the FIRST strip resolves the set and carries it
        km._push([c], connect=True)
        to = self._tab_orders(c)
        self.assertEqual(len(to), 1)
        self.assertEqual(to[0]["order"], TAB_ORDER)
        self.assertEqual(to[0]["skeleton"], [S3, S2], "every tab but the active one, cheapest transcript first")
        self.assertEqual(self._sessions(c), [S1, S4], "the active tab's full, plus the transcript-less one")
        self.assertEqual(sorted(self._statuses(c)),
                         sorted([(S2, self.SESS[S2]["status"]), (S3, self.SESS[S3]["status"])]),
                         "one status frame per skeleton sid")
        self.assertEqual(c["skeleton"], {S2, S3})
        self.assertEqual(c["skeletonOrder"], [S3, S2])
        self.assertIsNone(c.get("reconnect"), "consumed by the first strip sender: the pusher")
        self.assertIs(c.get("redial"), True, "the flag outlives the resolve")
        types = [f["type"] for f in c["_frames"]]
        self.assertLess(types.index("tabOrder"), types.index("session"), "strip first")

    def test_02_a_later_resolve_fills_a_redials_set_and_the_strip_says_so(self):
        c = self._dial(REDIAL)
        km.Handler._dispatch_ws(_Self(lambda cl: km._push([cl], connect=True)), {"type": "ready"}, c)   # the real _push_one body
        self.assertEqual(self._tab_orders(c)[0]["skeleton"], [S3, S2])
        c["_frames"].clear()
        km.Handler._dispatch_ws(_Self(), {"type": "activeTab", "id": S2}, c)   # a click on a skeleton tab
        self.assertEqual(c["skeleton"], {S3}, "the clicked tab left the set")
        km._push([c])
        self.assertEqual(self._sessions(c), [S2], "the clicked tab's full, and no other")
        self.assertEqual(self._tab_orders(c)[0]["skeleton"], [S3], "the strip says what is left")
        c["_frames"].clear()
        h = _Self()
        km.Handler._dispatch_ws(h, {"type": "needFull", "id": S3, "why": "prefetch"}, c)   # the idle prefetch
        self.assertEqual(c["skeleton"], set(), "the set emptied")
        self.assertEqual(h.calls, [c], "the repair push ran on the handler thread")
        km._push([c], connect=True)
        self.assertEqual(self._sessions(c), [S3])
        self.assertEqual(self._tab_orders(c)[0].get("skeleton"), [], "an emptied set is SAID as []")
        self.assertIs(c.get("redial"), True, "the flag is never consumed, whatever the set does")

    def test_03_a_second_ready_on_a_redial_socket_keeps_its_set_and_re_bases_its_tails(self):
        # the shim re-sends `ready` exactly once per redial in normal operation; if a second one arrives on the same
        # socket the reset still keeps the set (the flag is never consumed) while the tails re-base as slice 1 designed
        c = self._dial(REDIAL)
        km.Handler._dispatch_ws(_Self(lambda cl: km._push([cl], connect=True)), {"type": "ready"}, c)
        self.assertEqual(c["skeleton"], {S2, S3})
        self.assertEqual(set(c["echat"]), {S1, S4})
        c["_frames"].clear()
        km.Handler._dispatch_ws(_Self(), {"type": "ready"}, c)
        self.assertEqual(c["skeleton"], {S2, S3}, "kept")
        self.assertEqual(c["skeletonOrder"], [S3, S2])
        self.assertEqual(c["echat"], {}, "the tails re-base")
        self.assertFalse([k for k in c["sent"] if k[0] in ("chat", "status")], "the chat and status slots clear")
        self.assertEqual(self._tab_orders(c), [], "still no strip from the handler")
        km._push([c], connect=True)
        self.assertEqual(self._sessions(c), [S1, S4], "the held tabs re-sent whole, the skeleton ones not")
        self.assertEqual(self._tab_orders(c), [], "the strip is unchanged, so its slot dedups it (the reset keeps that slot)")
        self.assertEqual(c["skeleton"], {S2, S3}, "and the set stands")

    # ── the fresh-page path ──
    def test_04_a_fresh_page_is_held_the_same_way_and_its_ready_pops_the_state_for_a_full_strip(self):
        c = self._dial(FRESH)
        self.assertIsNone(c.get("reconnect"))
        self.assertIsNone(c.get("redial"), "a fresh page declares no redial (its shim dials with everConnected false, "
                          "or before its bundle has said ready: test_08)")
        self.assertFalse(c["ready"], "held all the same")
        km._clients.append(c)
        self._every_sender(c)
        self.assertEqual(c["_frames"], [], "nothing before ready on this path either")
        h = _Self()
        km.Handler._dispatch_ws(h, {"type": "ready"}, c)
        self.assertTrue(c["ready"])
        self.assertEqual(h.calls, [c])
        self.assertEqual(self._tab_orders(c), [], "no strip from the handler")
        for k in ("skeleton", "skeletonOrder", "reconnect", "redial"):
            self.assertNotIn(k, c, k)
        km._push([c], connect=True)
        to = self._tab_orders(c)
        self.assertEqual(len(to), 1)
        self.assertNotIn("skeleton", to[0], "a fresh page's strip has no key")
        self.assertEqual(set(to[0]), {"type", "order", "tabs", "views", "live", "selfHost"}, "today's frame, key for key")
        self.assertEqual(sorted(self._sessions(c)), sorted(TAB_ORDER), "every full")
        self.assertEqual(self._statuses(c), [], "no status frames: nothing is a skeleton")
        self.assertNotIn("skeleton", c)

    def test_05_a_redial_with_no_active_hint_is_held_and_then_gets_everything(self):
        # the kernel cannot know what the page shows: no set, a full push (fail safe), exactly as upstream's item 7,
        # now behind the hold
        c = self._dial("caps=readyGate&reconnect=1")
        self.assertIs(c.get("redial"), True)
        km._push([c])
        self.assertEqual(c["_frames"], [])
        km.Handler._dispatch_ws(_Self(lambda cl: km._push([cl], connect=True)), {"type": "ready"}, c)
        self.assertEqual(sorted(self._sessions(c)), sorted(TAB_ORDER))
        self.assertNotIn("skeleton", self._tab_orders(c)[0])
        self.assertNotIn("skeleton", c)
        self.assertIsNone(c.get("reconnect"), "consumed all the same")

    # ── the two halves joined: the URL the REAL shim dials, served by the real handshake (2026-09-10) ──
    def test_08_a_first_socket_that_died_before_the_bundles_ready_redials_as_a_fresh_page_and_gets_everything(self):
        # The documented mid-load drop (the shim's onopen comment: 3/3 headless loads with the first socket dropped
        # mid-load). The shim's everConnected is true from the first onopen, before the bundle has evaluated; keyed on
        # it alone the redial would declare itself, the bundle's OWN ready would land on a socket flagged `redial`,
        # the reset would keep `reconnect`, and _push_one would skeleton every tab for a page that holds nothing
        # (upstream and the fork before the fold sent everything whole). The term gates on bundleReady too, so this
        # redial dials as a fresh page and its ready pops the state.
        q = _shim_redial_query("open();drop();")            # opened, died, redialed: no bundle yet
        self.assertEqual(q, FRESH, "no reconnect term: the page has held no session")
        c = self._dial(q)
        self.assertIsNone(c.get("reconnect"))
        self.assertIsNone(c.get("redial"))
        self.assertFalse(c["ready"], "held all the same")
        km.Handler._dispatch_ws(_Self(lambda cl: km._push([cl], connect=True)), {"type": "ready"}, c)   # the bundle's own
        to = self._tab_orders(c)
        self.assertEqual(len(to), 1)
        self.assertNotIn("skeleton", to[0], "the full strip")
        self.assertEqual(sorted(self._sessions(c)), sorted(TAB_ORDER), "every session whole")
        self.assertEqual(self._statuses(c), [], "no status stand-ins")
        self.assertNotIn("skeleton", c)

    def test_09_only_a_page_whose_bundle_had_said_ready_before_the_drop_is_served_skeletons(self):
        # the designed redial, from the same shim: the bundle said ready on the first socket (the page held sessions),
        # the socket died, the redial declares itself, and the shim's re-sent ready gets the skeleton strip
        q = _shim_redial_query('open();window.__rompLocalSend({type:"ready"});drop();')
        self.assertEqual(q, REDIAL, "the reconnect term, after the active hint and the caps")
        c = self._dial(q)
        self.assertIs(c.get("redial"), True)
        km.Handler._dispatch_ws(_Self(lambda cl: km._push([cl], connect=True)), {"type": "ready"}, c)   # the shim's re-send
        to = self._tab_orders(c)
        self.assertEqual(len(to), 1)
        self.assertEqual(to[0]["skeleton"], [S3, S2])
        self.assertEqual(self._sessions(c), [S1, S4])
        self.assertEqual(c["skeleton"], {S2, S3})

    # ── the reset, in isolation ──
    def test_06_the_reset_pops_the_state_for_a_fresh_evaluation_and_keeps_it_for_a_declared_redial(self):
        fresh = {"reconnect": True, "skeleton": {S2}, "skeletonOrder": [S2], "echat": {S1: ("u0", 0)},
                 "sent": {("chat", S1): 1, ("status", S2): 1, ("taborder",): 1}}
        km._client_reset_chat_base(fresh)
        for k in ("skeleton", "skeletonOrder", "reconnect"):
            self.assertNotIn(k, fresh, k)
        self.assertEqual(fresh["echat"], {})
        self.assertEqual(fresh["sent"], {("taborder",): 1}, "the chat and status slots go; the strip's slot stays")
        redial = {"reconnect": True, "redial": True, "skeleton": {S2}, "skeletonOrder": [S2], "echat": {S1: ("u0", 0)},
                  "sent": {("chat", S1): 1, ("status", S2): 1, ("taborder",): 1}}
        km._client_reset_chat_base(redial)
        self.assertEqual((redial["skeleton"], redial["skeletonOrder"], redial["reconnect"]), ({S2}, [S2], True),
                         "a declared redial keeps its state for _resolve_reconnect to consume")
        self.assertIs(redial["redial"], True)
        self.assertEqual(redial["echat"], {}, "while the tails re-base, as slice 1 designed")
        self.assertEqual(redial["sent"], {("taborder",): 1})

    # ── the source, so a later fold keeps the flag (condition 3) ──
    def test_07_source_pins_the_flag_its_rationale_and_the_strip_less_ready_handler(self):
        src = inspect.getsource(km)
        s = inspect.getsource(km.Handler._ws)
        i = s.index("if reconnect:")
        arm = s[i:s.index("_register_ws_client(client)", i)]
        self.assertIn('client["reconnect"] = True', arm)
        self.assertIn('client["redial"] = True', arm, "set at accept, inside the reconnect arm, before registration")
        for needle in ("NEVER consumed", "fresh evaluation", "re-sends `ready`", "everConnected", "2026-09-09 ruling"):
            self.assertIn(needle, arm, "the rationale the ruling asked for, stated where the flag is set")
        self.assertEqual(src.count('client["redial"] = True'), 1, "the one write")
        self.assertEqual(src.count('pop("redial"'), 0, "never consumed")
        r = inspect.getsource(km._client_reset_chat_base)
        self.assertIn('if not client.get("redial"):', r)
        self.assertLess(r.index("with _client_lock(client):"), r.index('if not client.get("redial"):'), "under the slot lock")
        self.assertLess(r.index('if not client.get("redial"):'), r.index('client.pop("skeleton", None)'), "the pops sit under the guard")
        self.assertLess(r.index('client.pop("reconnect", None)'), r.index('k[0] in ("chat", "status")'),
                        "the slot clear follows, outside the guard: it runs for a redial too")
        i = src.index('if msg and msg.get("type") == "ready":')
        handler = src[i:src.index("_consume_pending_reveal(client)", i)]
        self.assertIn("_client_reset_chat_base(client)", handler)
        self.assertIn("self._push_one(client)", handler, "the guarded push is the one tabOrder source")
        self.assertLess(handler.index("_client_reset_chat_base(client)"), handler.index("self._push_one(client)"),
                        "reset, then push: a fresh page's pop precedes the strip that must carry no key")
        self.assertNotIn("_send_tab_order(", handler, "no strip of the handler's own")
        self.assertNotIn("_resolve_reconnect(", handler, "no resolve of the handler's own: the pusher's strip resolves")


if __name__ == "__main__":
    unittest.main()
