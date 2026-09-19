#!/usr/bin/env python3
"""memos.feedComposition on GET /perf (2026-09-18): what the feed frame is made of, and what each pane would receive if
it were sent only the fields it reads.

One feed frame (about 8.8 MB on a busy board) goes whole to every client that rides the feed slot: the feed pane, the
Outline (app `fleet`) and the Waiting-on-you pane (app `waiting`). feed.ts reads no ledgers, waiting.ts reads three of
the frame's fields, fleet.ts the ledgers and a few fields of each card, and nothing said how the frame's bytes divided.
The kernel now accounts for the frame at the pusher's per-entry encode (_feed_parts): the cards' and ledgers' strings as
the size estimate already summed them, and the remainder encoded per field and joined into the one sort_keys string it
always was, byte for byte, so every field's bytes come from the frame's own encode, with no second encode and no
change to any frame. Per consuming app the block projects the bytes of the fields FEED_APP_FIELDS says it reads, a
checked-in table pinned here against the bundles' source both ways, beside the whole frame it receives today.

Pinned here: (a) on a served kernel the block is on GET /perf, its parts sum to its frame figure exactly and that
figure sits under the frame the client received by no more than the stated tolerance (the tints, key names and
separators the estimate does not count), `wire` is the exact body once a whole frame went, and every key is an
identifier over integer leaves; (b) the per-app table matches the readers' source both ways, for the frame's fields,
for the Outline's card fields and for the field federation.ts consumes on a pane's behalf (clearedForeign, read off the
local frame by mergeHostFeeds; applyViewerClears rewrites the merged cards and the ledgers from it, so the two panes
that read those carry it), and the frame-fields list matches a built frame, the off frame and the views fault marker;
(c) a synthetic build with a known ledger share projects the expected bytes per app, a ledgers refill re-sizes only the
ledgers, and the lifetime sums accumulate; (d) the remainder's per-field encode is byte for byte the
whole sort_keys encode, and a build encodes each card, ledger and remainder field once and a refill no card; (e) the
`phoneFace` projection row (FEED_PROJECTIONS) beside the readers' rows sizes a frame that does not exist yet, a phone
client's feed slot carrying a face per active card (the address, the title, the state and the age: fields feed.ts
reads off a card today) plus one summary row per session with a card: on the 60-card fixture it sits far below the feed
row, a fixture with every card active projects more than one with none, and the reader pin skips the row, with no bundle
to pin it against; (f) the populated block, from cards in every column and two ledgers, passes the export's paste-safe walk
(cli/perf_public.py, the check `romp perf export --public` runs over its output) and the fold keeps it whole; (g) the
tables are PUBLISHED folded (the review of 2026-09-18 and its third round, 2026-09-19): the sums `frame`, `cards` and
`rest` (the frame outside the cards), with the card and ledger counts withheld (a count beside a sum discloses the
single-object case) and the ledgers, whose count /perf publishes elsewhere as the chat tab count, folded into `rest`
and `other`; the `by` table as the flag and count rows (FEED_BY_ROWS), the off frame's empty federation lists and
`other`, the sum of the ledgers and every text-bearing field (FEED_BY_FOLDED, a pinned list classified by what a
field can carry, never a byte floor), folded at report time on the last and the lifetime tables alike, so no
published row is the length of one string, while frame equals cards plus rest and rest the sum of the published
table; the per-app projections read the stored tables but count the folded set as ONE atom (an app that reads any
folded field is credited with all of `other`, the ledgers included), so the invariant holds in the scoped form the
kernel's FEED_COMPOSITION_INVARIANT states (every published number but the Outline's row is a sum of published rows,
and no published number or difference says which folded field a byte belongs to): a one-character step in any
folded field, a ledger's text among them, moves the same leaves by the same amounts, and on a one-session board with
a ledger attached no published number or difference of two is that ledger row's length; a key outside the checked-in
names is counted under `other` at build time; the stored tables keep the counts and the ledgers apart; the reference
and the ledger state the same shape and repeat the kernel's residual sentences verbatim; (h) the card-field and projection estimates run inside their own guard: a raise is counted, said once,
memoized with the cards so a refill neither re-raises nor repeats it, and the frame goes out unchanged at every call
site; (i) the block's shape is pinned from the kernel's constants, the estimates run once per build and not on a
refill, and the remainder's fields go through one encoder per pass.

Synthetic only: the notes-api demo world, TESTHOST, placeholder ids."""
import base64
import copy
import io
import json
import os
import re
import socket
import struct
import tempfile
import threading
import time
import unittest
import urllib.request
from contextlib import redirect_stderr
from http.server import ThreadingHTTPServer
from unittest import mock
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
WEBVIEW = os.path.join(ROOT, "ui", "webview")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads: the modules resolve their state root at import, and a root minted here is outside
# conftest's belt, so session hosts are switched off in it too.
_ROOT = tempfile.mkdtemp()
os.environ["XDG_STATE_HOME"] = _ROOT
os.environ.pop("ROMP_STATE_DIR", None)
os.makedirs(os.path.join(_ROOT, "romp"), exist_ok=True)
with open(os.path.join(_ROOT, "romp", "session-hosts"), "w") as _fh:
    _fh.write("off")
km = load_source("romp_kernel_feedcomp", os.path.join(BIN, "romp-kernel"))
pp = load_source("romp_perf_public", os.path.join(ROOT, "cli", "perf_public.py"))   # the export's paste-safe walk

SID = "11111111-2222-3333-4444-555555555555"
SID_B = "11111111-2222-3333-4444-666666666666"
NOW = 1781100000
# The frame's size estimate counts the per-card strings minus their tints, the per-ledger strings and the remainder;
# the served body adds the frame's key names and separators and a tint per card and per tree node (about 20 bytes
# each). The fixture card below is about 2 KB with seven tints, so the estimate sits 7 to 9 percent under the body;
# the live board's cards are larger and the gap smaller. The tolerance is the stated bound on that gap.
FRAME_TOLERANCE = 0.15
VOLATILE = {"type", "now", "buildId"}
# The fixture's own strings, planted for the export's walk (cli/perf_public.py): a key or string value of the block that
# carries one is a leak. The block is counts and byte totals only, so none can reach it; the walk holds it to that.
PLANTED = (SID, SID_B, SID[:8], "TESTHOST", "example/notes-api", "notes-api", "Synthetic goal", "Decide the response shape",
           "pulled 3 commits", "tags unavailable")
# The export's identifier scan, with synthetic probes in place of the machine's own (tests/test_perf_export.py's shape).
SYNTHETIC_HOME = "/home/tester"                                       # a synthetic home; never this machine's
SYNTHETIC_PROBES = (("hostname", "testhost"), ("username", "tester"), ("home directory", SYNTHETIC_HOME),
                    ("session id", SID.lower()), ("session id", SID[:8].lower()),
                    ("session directory", SYNTHETIC_HOME + "/code/notes-api"))


def _doc_row(doc, name):
    """The _PerfStats docstring row whose entry line starts with `name`: from that line to the next line at or above its
    indentation that begins an entry (a non-space after the indentation), or the docstring's end. The locator is RELATIVE
    to the entry line's own indentation on purpose: Python 3.13 and later strip a docstring's common leading whitespace at
    compile time, so a pin that counts leading spaces (the source's six before a row's name) passes on a 3.12 venv and
    finds nothing on the 3.13 and 3.14t CI cells. Do not simplify it back to a space count."""
    m = re.search(r"^( *)%s\s" % re.escape(name), doc, re.M)
    if m is None:
        raise ValueError("no docstring row starts with %r" % name)
    nxt = re.compile(r"^ {0,%d}\S" % len(m.group(1)), re.M).search(doc, m.end())
    return doc[m.start():nxt.start() if nxt else len(doc)]


def _card(i, now=NOW, provisional=False, **over):
    t = now - i * 60
    c = {"itemId": "%s:g%d" % (SID, i), "sid": SID, "name": "web", "color": {"bg": "#123456", "fg": "#ffffff"},
         "text": "Synthetic goal %d on the notes-api board" % i, "t": t, "live": True,
         "trgb": list(km.cm.age_rgb(now - t)), "turnId": "%s:g%d" % (SID, i), "column": "working",
         "summary": None if provisional else "s" * 400, "blockSummary": None,
         "background": None if provisional else "b" * 300, "notify": True,
         "tree": [] if provisional else [{"id": "%s:g%d.%d" % (SID, i, j), "text": "step %d" % j, "status": "done",
                                          "t": t, "last": t, "trgb": list(km.cm.age_rgb(now - t)), "children": []}
                                         for j in range(6)]}
    if provisional:
        c["provisional"] = True
    c.update(over)
    return c


def _ledger(sid=SID, name="web", tops=3):
    return {"sid": sid, "name": name, "color": None, "status": {"state": "working"},
            "ledger": {"tops": ["t" * 2000] * tops}}


def _feed(n=40, now=NOW, build_id=1, asks=None, ledgers=None, **top):
    f = {"type": "feed", "now": now, "buildId": build_id,
         "asks": asks if asks is not None else [_card(i, now=now, provisional=(i % 10 == 9)) for i in range(n)],
         "order": [SID, SID_B], "working": ["web"], "awaiting": ["api"], "stateUnknown": [], "bgServices": {},
         "sessions": [{"sid": SID, "name": "web", "color": None, "githubRepo": None},
                      {"sid": SID_B, "name": "api", "color": None, "githubRepo": "example/notes-api"}],
         "userTodos": {SID: 1},
         "userTodoRows": [{"sid": SID, "name": "web", "color": None,
                           "todos": [{"id": "ut-1", "text": "Decide the response shape", "createdT": now - 100}]}],
         "userTodosOn": True, "judgeLimit": None,
         "views": {"seq": 3, "tags": {"backend": ["web", "api"], "alpha": {"z": 1, "a": 2}}},
         "dismissedCount": 2, "showDismissed": False, "clearedForeign": [], "canUndoClear": True,
         "clearNotices": [], "sdkNotices": [], "syncNotices": [{"sig": "s1", "text": "pulled 3 commits"}],
         "selfHost": "TESTHOST"}
    f["ledgers"] = [_ledger(), _ledger(SID_B, "api", tops=1)] if ledgers is None else ledgers
    f.update(top)
    return f


def _rest_of(feed):
    return {k: v for k, v in feed.items() if k not in ("type", "asks", "ledgers") and k not in km._DEDUP_VOLATILE}


def _expected(feed):
    """The parts' sizes computed here, apart from the kernel: the tint-stripped cards, the ledgers and the remainder per
    field (its quoted name, the separators, its sort_keys value)."""
    cards = sum(len(json.dumps(km._strip_trgb(a))) for a in feed["asks"])
    leds = sum(len(json.dumps(l)) for l in feed.get("ledgers") or [])
    by = {k: len(json.dumps(k)) + 4 + len(json.dumps(v, sort_keys=True)) for k, v in _rest_of(feed).items()}
    return cards, leds, by


# The `by` rows a published table can carry (the kernel's FEED_BY_ROWS comment): the flag and count fields, the off
# frame's four federation lists (outside FEED_FRAME_FIELDS, always empty here) and `other`, the sum of every text-bearing
# field (FEED_BY_FOLDED), folded at report time.
# (read with getattr so the module imports on a kernel without the lists and each test reds on its own: fails before)
OFF_LISTS = frozenset(km._FEED_FRAME_LISTS) - frozenset(km.FEED_FRAME_FIELDS)
PUBLIC_NAMES = frozenset(getattr(km, "FEED_BY_ROWS", ())) | OFF_LISTS | {"other"}


def _published(by, leds=0):
    """The test's own per-field table regrouped the way the block publishes it: every FEED_BY_FOLDED row summed into
    `other` with the ledgers' bytes (`leds`), the rest as they are, `other` present on any non-empty table. A
    projection pin's expected value is the test's own sum: the cards, the FEED_BY_ROWS rows the app reads from the
    unfolded `by`, and this table's `other` once for an app that reads any folded field (the ledgers are one)."""
    out = {k: v for k, v in by.items() if k not in km.FEED_BY_FOLDED}
    if by or leds:
        out["other"] = out.get("other", 0) + sum(v for k, v in by.items() if k in km.FEED_BY_FOLDED) + leds
    return out


def _has_str(v):
    """Whether a str sits anywhere in `v`: the value, a dict key, a list element, at any depth."""
    if isinstance(v, str):
        return True
    if isinstance(v, dict):
        return any(_has_str(k) or _has_str(x) for k, x in v.items())
    if isinstance(v, (list, tuple)):
        return any(_has_str(x) for x in v)
    return False


def _fresh_pass(frame, comp=None):
    """One _feed_parts pass over `frame` on `comp` (a fresh accumulator by default), the cards memo cleared first so the
    pass is a build; returns the accumulator."""
    comp = km._FeedComposition() if comp is None else comp
    with mock.patch.object(km, "_FEED_COMP", comp):
        km._feed_cards_memo = None
        km._feed_parts(frame)
    return comp


def _report(comp):
    """The accumulator's report with no wire held, as GET /perf would serve it."""
    with mock.patch.object(km, "_feed_wire", None):
        return comp.report()


def _assert_shape(tc, block, after_pass, wire_went):
    """The block's shape from the kernel's constants, never a hand-listed copy of the table's values: the five top-level
    keys; lifetime as the PUBLISHED sums (frame, cards, rest: the ledgers folded, the two counts withheld) plus by and
    apps; last the same plus ledgersAttached once a pass ran, else {}; wire as bytes and exact once a frame is held,
    else {}; apps one row per reader and per projection, each today and projected. After a pass no sub-block is empty
    and both tables hold only the published names."""
    sums = set(km._FeedComposition.PUBLISHED)
    apps = set(km.FEED_APP_FIELDS) | set(km.FEED_PROJECTIONS)
    tc.assertEqual(set(block), {"passes", "failed", "lifetime", "last", "wire"})
    tc.assertEqual(set(block["lifetime"]), sums | {"by", "apps"})
    for k in ("cardCount", "ledgerCount", "ledgers"):        # fails before: the counts and the ledgers were published
        tc.assertNotIn(k, block["lifetime"], k)
        tc.assertNotIn(k, block["last"], k)
    tc.assertEqual(set(block["lifetime"]["apps"]), apps)
    for app, row in block["lifetime"]["apps"].items():
        tc.assertEqual(set(row), {"today", "projected"}, app)
    if after_pass:
        tc.assertEqual(set(block["last"]), sums | {"ledgersAttached", "by", "apps"})
        tc.assertEqual(set(block["last"]["apps"]), apps)
        for app, row in block["last"]["apps"].items():
            tc.assertEqual(set(row), {"today", "projected"}, app)
        tc.assertIn("other", block["last"]["by"])
        tc.assertIn("other", block["lifetime"]["by"])
        tc.assertLessEqual(set(block["last"]["by"]), PUBLIC_NAMES)
        tc.assertLessEqual(set(block["lifetime"]["by"]), PUBLIC_NAMES)
    else:
        tc.assertEqual(block["last"], {})
        tc.assertEqual(block["lifetime"]["by"], {})
    tc.assertEqual(set(block["wire"]), {"bytes", "exact"} if wire_went else set())


def _drive_push(tc, apps, fixture):
    """The real _push driven per app id on a fresh client, with the build stage stubbed to a fixture frame (the harness
    of tests/test_observability_routes.py): {app: [the frame types the client received]}. The pusher's wire state is
    restored after."""
    stubs = ("_cached_feed", "_fleet_view_sig", "_chat_tab_sessions", "_retry_parked_creates", "build_timeline",
             "_cached_timeline")
    saved = {nm: getattr(km, nm) for nm in stubs}
    saved_state = (list(km._last_tab_order), km._feed_wire, km._bars_wire, list(km._built_feed))
    km._cached_feed = lambda now, live, sig, connect=False: dict(fixture, now=now)
    km._fleet_view_sig = lambda now, live: ("SIG",)
    km._chat_tab_sessions = lambda now, live: []
    km._retry_parked_creates = lambda: None
    timeline = lambda now, live, *a, **kw: {"lanes": [], "turns": {}, "judging": [], "messages": [], "now": now}
    km.build_timeline = timeline
    km._cached_timeline = timeline
    out = {}
    err = io.StringIO()
    try:
        with redirect_stderr(err):
            for app in apps:
                frames = []
                c = {"app": app, "alive": True, "sent": {}, "send": lambda s, frames=frames: frames.append(json.loads(s))}
                km._feed_wire = None
                km._push([c], connect=True)
                out[app] = [f.get("type") for f in frames]
    finally:
        for nm, v in saved.items():
            setattr(km, nm, v)
        km._last_tab_order[:], km._feed_wire, km._bars_wire = saved_state[:3]
        km._built_feed[:] = saved_state[3]
    tc.assertNotIn("Traceback", err.getvalue(), err.getvalue())
    return out


def _built_with_one_live_session(tc):
    """A real build_feed over ONE synthetic live session: the session's derivation (store reads on a real kernel) is
    stubbed to a fixed entry with one card, a working dot, a service chip and an open todo, and the per-session memo to
    a miss, so the frame's working, order, sessions, bgServices, userTodos and userTodoRows are populated. The reader
    pins over an empty board pass blind on those fields; this frame is where they are held to the list."""
    sess = {"sid": SID, "name": "web", "path": None}
    card = dict(_card(0), _ageT=NOW - 60)
    for r in card["tree"]:
        r["_ageT"] = NOW - 60
    entry = {"asks": [card], "working": "web", "awaiting": None, "bgServices": ["dev server on :3000"],
             "userTodos": {"sid": SID, "name": "web", "color": None,
                           "todos": [{"id": "ut-1", "text": "Decide the response shape", "createdT": NOW - 100}]}}
    err = io.StringIO()
    with redirect_stderr(err), mock.patch.multiple(
            km, _alive_sessions=lambda now, tm: [dict(sess)], _warm_fleet_bg=lambda now: None,
            _sessions=lambda now, window=None, forks=True: [dict(sess)], _sdk=lambda: None,
            _feed_memo_get=lambda sid: None, _feed_session_key=lambda s, tm, ctx, prev: ("synthetic",),
            _feed_key_with_deps=lambda key, ctx, entry: key, _feed_memo_put=lambda sid, key, js: None,
            _feed_session_entry=lambda s, ctx: copy.deepcopy(entry),
            _chat_tab_sessions=lambda now, live: [dict(sess)],
            _state_unknown_names=lambda alive, live, working, awaiting: [],
            _wait_for_graph=lambda now, sids: {}, _subagent_trees_forget=lambda alive: None):
        built = km.build_feed(NOW, {SID: {}})
    tc.assertNotIn("Traceback", err.getvalue(), err.getvalue())
    return built


def _leaves(v, path=""):
    if isinstance(v, dict):
        for k, x in v.items():
            yield from _leaves(x, path + "." + str(k))
    elif isinstance(v, (list, tuple)):
        for x in v:
            yield from _leaves(x, path + "[]")
    else:
        yield path, v


def _paste_safe(tc, block):
    """The block as `romp perf export --public` and the served-snapshot invariant test walk it (cli/perf_public.py), under
    memos/feedComposition: the walk (paste_problems) finds no problem under the served snapshot's key grammar (the
    kernel's _PERF_IDENT: no colon, 32 characters) with the fixture's strings planted, nor under the export's own; the
    fold keeps the block whole (no key on the denylist, none folded to `other`, no bound or uptime coarsened, so the
    export carries every number); the identifier scan finds no hit against synthetic probes; and every leaf is an int,
    a count or a byte total (never a bool, a float, a string or null)."""
    doc = {"memos": {"feedComposition": block}}
    problems = pp.paste_problems(doc, planted=PLANTED, ident=km._PERF_IDENT)
    tc.assertEqual(problems, [], "%d problem(s) in the block:\n  %s" % (len(problems), "\n  ".join(map(str, problems))))
    tc.assertEqual(pp.paste_problems(doc, planted=PLANTED), [], "and under the export's own grammar")
    tc.assertEqual(pp.fold(doc), doc, "the export keeps the block whole: no key denied, none folded, nothing coarsened")
    tc.assertEqual(pp.identifier_hits(doc, SYNTHETIC_PROBES), [])
    for path, leaf in _leaves(block):
        tc.assertIsInstance(leaf, int, "%s = %r" % (path, leaf))
        tc.assertNotIsInstance(leaf, bool, path)


def _connect(port, query):
    """A browser-style client socket to the kernel's /ws?`query`; returns (socket, leftover bytes)."""
    key = base64.b64encode(os.urandom(16)).decode()
    req = ("GET /ws?%s&token=%s HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nOrigin: http://127.0.0.1:%d\r\n"
           "Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: %s\r\n"
           "Sec-WebSocket-Version: 13\r\n\r\n") % (query, km.TOKEN, port, port, key)
    s = socket.create_connection(("127.0.0.1", port), timeout=10)
    s.sendall(req.encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = s.recv(65536)
        if not chunk:
            raise RuntimeError("closed during the handshake")
        buf += chunk
    head, buf = buf.split(b"\r\n\r\n", 1)
    if not head.startswith(b"HTTP/1.1 101"):
        raise RuntimeError(head[:80])
    return s, buf


def _read_frame(s, buf):
    """One server frame (unmasked) -> (opcode, payload, leftover)."""
    def need(n):
        nonlocal buf
        while len(buf) < n:
            chunk = s.recv(1 << 20)
            if not chunk:
                raise RuntimeError("socket closed")
            buf += chunk
    need(2)
    ln = buf[1] & 0x7F
    off = 2
    if ln == 126:
        need(4)
        ln = struct.unpack(">H", buf[2:4])[0]
        off = 4
    elif ln == 127:
        need(10)
        ln = struct.unpack(">Q", buf[2:10])[0]
        off = 10
    need(off + ln)
    return buf[0] & 0x0F, buf[off:off + ln], buf[off + ln:]


def _registered(wid, deadline_s=5):
    deadline = time.time() + deadline_s
    while time.time() < deadline:
        with km._clients_lock:
            client = next((c for c in km._clients if c.get("wid") == wid), None)
        if client is not None:
            return client
        time.sleep(0.005)
    raise AssertionError("the socket %s was not registered" % wid)


class ServedBlock(unittest.TestCase):
    """(a): a served kernel, a feed page on a real socket, a pusher cycle, GET /perf."""

    def _get(self, port, path):
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path),
                                     headers={"X-Romp-Token": os.environ["ROMP_SERVE_TOKEN"]})
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode())

    def test_the_block_is_served_and_its_parts_sum_to_the_frame_the_client_received(self):
        fixture = _feed(n=60)
        saved = (km.build_feed, km._feed_wire, list(km._built_feed))
        km.build_feed = lambda now, live: dict(fixture, now=now)
        km._feed_wire = None
        km._built_feed[:] = [None, None, 0.0, 0.0]
        srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        s = None
        # a fresh accumulator for this pass, so the block walked below holds this fixture alone (the module-global one
        # carries every other test's passes in this process, odd remainder keys among them); the served path is the
        # same: the memo reader and the pusher's pass read the module attribute at call time
        fresh = mock.patch.object(km, "_FEED_COMP", km._FeedComposition())
        fresh.start()
        self.addCleanup(fresh.stop)
        passes0 = km._FEED_COMP.report()["passes"]
        try:
            s, buf = _connect(port, "app=feed&wid=wfc1&caps=feedDelta")
            _registered("wfc1")
            err = io.StringIO()
            with redirect_stderr(err):
                km._push_all()                                   # the pusher's cycle: the build, the per-entry pass, the send
            received = None
            deadline = time.time() + 10
            while received is None and time.time() < deadline:   # the caps and tab-order frames come first
                op, payload, buf = _read_frame(s, buf)
                if op != 0x1:
                    continue
                if payload.startswith(b'{"now": ') and b'"type": "feed"' in payload:
                    received = payload
            self.assertIsNotNone(received, "the page received a whole feed frame")
            frame = json.loads(received)
            self.assertEqual(frame["type"], "feed")
            self.assertEqual(len(frame["asks"]), 60)
            self.assertEqual(len(frame["ledgers"]), 2)
            status, snap = self._get(port, "/perf")
            self.assertEqual(status, 200)
            block = snap["memos"]["feedComposition"]            # fails before: no such block
            self.assertEqual(block["passes"], passes0 + 1, "one per-entry pass for the one build")
            self.assertEqual(block["failed"], 0)
            last = block["last"]
            self.assertEqual(last["cards"] + last["rest"], last["frame"], "the two parts sum to the frame figure")
            self.assertEqual(sum(last["by"].values()), last["rest"], "the published rows sum to the published rest")
            self.assertEqual(sum(block["lifetime"]["by"].values()), block["lifetime"]["rest"],
                             "and so do the lifetime table's rows")
            # the counts and the ledgers are withheld from both published tables (fails before: cardCount 60,
            # ledgerCount 2 and the ledgers' bytes were published beside the sums); the stored pass keeps them apart
            stored = km._FEED_COMP.last
            for k in ("cardCount", "ledgerCount", "ledgers"):
                self.assertNotIn(k, last, k)
                self.assertNotIn(k, block["lifetime"], k)
            self.assertEqual((stored["cardCount"], stored["ledgerCount"], last["ledgersAttached"]), (60, 2, 1))
            self.assertEqual(stored["ledgers"], sum(len(json.dumps(l)) for l in fixture["ledgers"]))
            self.assertEqual(last["rest"], stored["rest"] + stored["ledgers"], "the published rest is the frame outside the cards")
            # the published table (fails before: a row per remainder field, selfHost among them): the flag and count
            # rows the frame carries plus `other`, the text-bearing fields' sum, and no folded name in either table
            self.assertEqual(set(last["by"]), {f for f in km.FEED_BY_ROWS if f in frame} | {"other"})
            self.assertFalse(set(last["by"]) & km.FEED_BY_FOLDED)
            self.assertFalse(set(block["lifetime"]["by"]) & km.FEED_BY_FOLDED)
            _assert_shape(self, block, True, True)
            n = len(received)
            self.assertLessEqual(last["frame"], n, "the estimate never exceeds the frame")
            gap = (n - last["frame"]) / n
            self.assertLessEqual(gap, FRAME_TOLERANCE,
                                 "the frame figure sits under the received frame (%d B) by %.1f%%: the tints, key names "
                                 "and separators it does not count, bounded by %.0f%%" % (n, 100 * gap, 100 * FRAME_TOLERANCE))
            # `wire` is the served body's exact length: the received frame is the body with the clock spliced in front
            self.assertEqual(block["wire"]["exact"], 1, "a whole frame went, so the body is materialized")
            self.assertEqual(block["wire"]["bytes"], n - 9 - len(json.dumps(frame["now"])))
            self.assertGreaterEqual(block["wire"]["bytes"], last["frame"])
            for app in ("feed", "fleet", "waiting", "phoneFace"):
                self.assertEqual(last["apps"][app]["today"], last["frame"], app)
                self.assertLess(last["apps"][app]["projected"], last["frame"], app)
            # the projection row rides `apps` beside the readers' rows (fails before: no such row); its `today` is the
            # whole frame, pinned by the loop above with every row's (a phone's Outline dials as fleet, its feed page as
            # feed, so the row reads as the saving), and its estimate sits below the Outline's card fields plus ledgers
            self.assertLess(last["apps"]["phoneFace"]["projected"], last["apps"]["fleet"]["projected"])
            self.assertLess(last["apps"]["waiting"]["projected"], last["rest"],
                            "the Waiting-on-you row is `other` plus the switch, under the remainder by the count and flag rows")
            # every projected figure but the Outline's is a sum of the published rows, and the Outline's is one plus its
            # card-field estimate (fails before: the feed row was the frame minus the
            # ledgers minus the two fields the pane never reads, one of them folded, so the difference published that
            # field's bytes; and, before the third round, the frame minus the ledgers minus the switch, so the
            # difference published the ledgers): the feed row is the cards, `other` and the flag rows the pane reads,
            # which is the frame minus the switch; the Waiting-on-you row is `other` and the switch; the Outline's is
            # its card-field estimate (over the cards the client received) and `other`, the ledgers inside it
            pub = last["by"]
            flags = sum(pub[f] for f in ("dismissedCount", "showDismissed", "canUndoClear", "off") if f in pub)
            self.assertEqual(last["apps"]["feed"]["projected"], last["cards"] + pub["other"] + flags)
            self.assertEqual(last["apps"]["feed"]["projected"], last["frame"] - pub["userTodosOn"])
            self.assertEqual(last["apps"]["waiting"]["projected"], pub["other"] + pub["userTodosOn"])
            est = km._ask_fields_est(frame["asks"], km._FEED_APP_ASK_FIELDS["fleet"])
            self.assertEqual(last["apps"]["fleet"]["projected"], est + pub["other"] + pub.get("off", 0))
            # no published number and no difference of two is the ledgers' bytes (fails before: last.ledgers was, and
            # frame - cards - rest, and frame - feed.projected - userTodosOn)
            ints = [(p, v) for p, v in _leaves({"last": last, "lifetime": block["lifetime"], "wire": block["wire"]})
                    if isinstance(v, int) and not isinstance(v, bool)]
            hits = [p for p, v in ints if v == stored["ledgers"]]
            hits += ["%s - %s" % (p, q) for p, v in ints for q, w in ints if p != q and v - w == stored["ledgers"]]
            self.assertEqual(hits, [])
            two = sum(len(json.dumps(k)) + 4 + len(json.dumps(frame[k], sort_keys=True))
                      for k in ("userTodoRows", "sessions"))
            self.assertNotEqual(last["apps"]["waiting"]["projected"] - pub["userTodosOn"], two,
                                "the Waiting-on-you row minus the switch is not the two folded fields the pane reads")
            # the fold is at report time: the accumulator's stored table has a row per remainder field of the frame the
            # client received, and the served table is that table folded with the stored ledgers
            self.assertEqual(set(stored["by"]), set(frame) - VOLATILE - {"asks", "ledgers"})
            self.assertEqual(km._FeedComposition.public_by(stored["by"], stored["ledgers"]), pub)
            for k in block["lifetime"]:
                if k not in ("by", "apps"):
                    self.assertGreaterEqual(block["lifetime"][k], last[k], k)
            # paste-safe: identifier keys, integer leaves, and the whole snapshot serializes
            for path, leaf in _leaves(block):
                self.assertIsInstance(leaf, int, "%s = %r" % (path, leaf))
                self.assertNotIsInstance(leaf, bool, path)
            keys = set()

            def walk(v):
                if isinstance(v, dict):
                    for k, x in v.items():
                        keys.add(k)
                        walk(x)
            walk(block)
            bad = sorted(k for k in keys if not km._PERF_IDENT.fullmatch(k))
            self.assertEqual(bad, [], "every key of the block is an identifier")
            json.dumps(snap)
            # the served block through the export's own walk (cli/perf_public.py), after a real pass with the cards and
            # the ledgers attached: the paste-safe contract GET /perf's public form is held to, on the populated block
            _paste_safe(self, block)
        finally:
            if s is not None:
                s.close()
            srv.shutdown()
            srv.server_close()
            km.build_feed, km._feed_wire = saved[0], saved[1]
            km._built_feed[:] = saved[2]
            with km._clients_lock:
                km._clients[:] = [c for c in km._clients if c.get("wid") != "wfc1"]


class AppTable(unittest.TestCase):
    """(b): the checked-in table against the bundles' source, both ways, and the frame-fields list against the frames."""

    READERS = {"feed": "feed.ts", "fleet": "fleet.ts", "waiting": "waiting.ts"}

    @staticmethod
    def _src(name):
        with open(os.path.join(WEBVIEW, name), encoding="utf-8") as fh:
            return fh.read()

    @staticmethod
    def _fn(src, head):
        """The text of the top-level function whose declaration starts with `head`, to its closing brace."""
        start = src.index(head)
        return src[start:src.index("\n}", start)]

    def test_the_table_names_every_frame_field_each_reader_reads_and_nothing_else(self):
        table = km.FEED_APP_FIELDS                               # fails before: no table
        self.assertEqual(set(table), set(self.READERS), "one row per app that rides the feed slot")
        # The projection rows are NOT in the readers' table, and the pin below skips them: a projection sizes a frame
        # no bundle reads yet (phoneFace, the phone's face frame, decided 2026-09-18 and not built), so there is no
        # reader source to pin it against; the day a bundle reads one, its row moves into the table and the pin reads
        # it there. What CAN be pinned is the face itself: its five fields are fields every card carries and feed.ts
        # reads off a card today (it.<field>), so the face is drawn from the frame as it is, not from a wished-for card.
        self.assertEqual(set(km.FEED_PROJECTIONS), {"phoneFace"}, "one projection row today")
        self.assertNotIn("phoneFace", table,
                         "phoneFace is a projection of a frame that does not exist yet: no reader, so no reader pin")
        self.assertFalse(set(km.FEED_PROJECTIONS) & set(table), "a projection is never also a reader row")
        for app in km.FEED_PROJECTIONS:
            self.assertNotIn(app, self.READERS, "%s has no bundle to read against; the reader pin skips it" % app)
        self.assertEqual(km.FEED_PHONE_FACE_FIELDS, ("itemId", "sid", "text", "column", "t"),
                         "the face: the address (itemId, sid), the title (text), the state (column) and the age (t)")
        feed_src = self._src("feed.ts")
        for f in km.FEED_PHONE_FACE_FIELDS:
            self.assertTrue(re.search(r"\bit\??\.%s\b" % re.escape(f), feed_src),
                            "%s: a card field feed.ts reads off a card today" % f)
        self.assertEqual(set(km.FEED_PHONE_FACE_ACTIVE), {"working", "needs_input"},
                         "active is the Working and Blocked columns; Completed is not")
        self.assertIn('column: "working" | "needs_input" | "completed"', feed_src, "the card's column values, as feed.ts types them")
        # federation.js loads on every feed-slot page ahead of the pane's bundle and hands it the merged frame. Most
        # fields it merges through, and the pane's own read counts them; the fields it CONSUMES on the pane's behalf
        # are the local frame's fields mergeHostFeeds reads by name (clearedForeign: applyViewerClears drops the remote
        # cards and strikes the remote ledger tops the local ledger cleared). A pane that reads a field the consumer
        # rewrites receives the consumed field's effect, so its row carries the field; a pane that reads none of the
        # rewritten fields does not (fails before: the feed and fleet rows lacked clearedForeign).
        fed = self._src("federation.ts")
        consumed = set(re.findall(r"\blocal\??\.(\w+)", self._fn(fed, "export function mergeHostFeeds("))) \
            & set(km.FEED_FRAME_FIELDS)
        clears = self._fn(fed, "export function applyViewerClears(")
        rewrites = set(re.findall(r"\bmerged\.(\w+) = ", clears)) & set(km.FEED_FRAME_FIELDS)
        if "ledgers[i] = " in clears:
            rewrites.add("ledgers")
        self.assertTrue(consumed, "mergeHostFeeds reads a frame field off the local frame by name")
        self.assertTrue(rewrites, "applyViewerClears rewrites a frame field of the merged frame")
        self.assertIn("clearedForeign", consumed)
        for app, fname in self.READERS.items():
            src = self._src(fname)
            reads = {f for f in km.FEED_FRAME_FIELDS if re.search(r"\bm\??\.%s\b" % re.escape(f), src)}
            via = consumed if reads & rewrites else set()
            top = {f.split(".", 1)[0] for f in table[app]}       # `asks.<field>` rows are a read of `asks`
            self.assertEqual(top, reads | via,
                             "%s: the table's top-level fields are exactly the frame fields %s reads off its frame "
                             "(m.<field>) plus the fields federation consumes for it (%s); table-only %s, "
                             "source-only %s"
                             % (app, fname, sorted(via), sorted(top - reads - via), sorted((reads | via) - top)))
            for f in top:
                self.assertIn(f, km.FEED_FRAME_FIELDS, "%s: %s names a frame field" % (app, f))
        # the Outline reads a few fields of each card (never the card): the provisional card's face in its frame handler
        # (a.<field>) and the goal card's distiller texts at the hover (ask.<field>, asksById)
        src = self._src("fleet.ts")
        start = src.index('if (m.type !== "feed") return;')
        handler = src[start:src.index("\n}));", start)]
        card_reads = set(re.findall(r"\ba\??\.(\w+)", handler)) | set(re.findall(r"\bask\??\.(\w+)", src))
        sub = {f[5:] for f in table["fleet"] if f.startswith("asks.")}
        self.assertEqual(sub, card_reads, "fleet: the table's card fields are the ones fleet.ts reads; table-only %s, "
                         "source-only %s" % (sorted(sub - card_reads), sorted(card_reads - sub)))
        self.assertNotIn("asks", table["fleet"], "the Outline never takes the cards whole")
        self.assertIn("asks", table["feed"], "the feed pane takes the cards whole")
        self.assertFalse(any(f.startswith("asks") for f in table["waiting"]), "waiting.ts reads no card")
        self.assertIsNone(re.search(r"\bm\??\.asks\b", self._src("waiting.ts")))

    def test_the_apps_are_the_send_stages_and_the_frame_fields_list_matches_the_frames(self):
        for app in km.FEED_APP_FIELDS:
            self.assertTrue(km._feed_audience([{"app": app}]), "%s rides the feed payload" % app)
        # the table's apps are the send stage's, by execution: the REAL _push is driven per app id with a fixture build
        # and the frame types each client receives are recorded (the harness of tests/test_observability_routes.py), in
        # place of a regex over the send stage's source, which held a copy of the tuple beside its comment and failed
        # on a rewrap of that comment
        received = _drive_push(self, ("feed", "fleet", "waiting", "chat", "timeline", "shell"), _feed(n=2))
        self.assertEqual({app for app, types in received.items() if "feed" in types}, set(km.FEED_APP_FIELDS),
                         "the apps handed a feed frame are the table's rows; received %s" % received)
        self.assertEqual(len(km.FEED_FRAME_FIELDS), len(set(km.FEED_FRAME_FIELDS)))
        err = io.StringIO()
        with redirect_stderr(err), mock.patch.object(km, "_alive_sessions", lambda now, tm: []), \
                mock.patch.object(km, "_warm_fleet_bg", lambda now: None), \
                mock.patch.object(km, "_sessions", lambda now, window=None, forks=True: []), \
                mock.patch.object(km, "_sdk", lambda: None):
            built = km.build_feed(NOW, {})
        self.assertEqual(sorted(set(built) - VOLATILE - set(km.FEED_FRAME_FIELDS)), [],
                         "every field of a built frame is in the list")
        off = km._feed_off_frame(NOW, {})
        self.assertIn("off", off)
        self.assertEqual(sorted(set(off) - VOLATILE - set(km._FEED_FRAME_LISTS) - set(km.FEED_FRAME_FIELDS)), [],
                         "every field of the off frame is in the list, its empty federation lists aside")
        with mock.patch.object(km, "_timeline_views_display", lambda: (None, RuntimeError("synthetic"))), \
                mock.patch.object(km, "_views_fault_text", lambda f: "tags unavailable: synthetic"):
            fault = km._views_payload()
        self.assertEqual(set(fault), {"viewsFault"})
        self.assertIn("viewsFault", km.FEED_FRAME_FIELDS)
        self.assertIn("ledgers", km.FEED_FRAME_FIELDS, "the pusher's attach")
        for f in km.FEED_FRAME_FIELDS:
            self.assertTrue(f in built or f in off or f == "viewsFault" or f == "ledgers", "%s is a frame field" % f)
        # the same pin over a frame with one live session: the empty board above leaves working, order, sessions,
        # bgServices, userTodos and userTodoRows empty, so a field a live session adds would pass it blind
        live = _built_with_one_live_session(self)
        self.assertEqual(live["working"], ["web"])
        self.assertEqual([s["sid"] for s in live["sessions"]], [SID])
        self.assertEqual((len(live["asks"]), live["userTodos"], len(live["userTodoRows"])), (1, {SID: 1}, 1))
        self.assertEqual(live["bgServices"], {"web": ["dev server on :3000"]})
        self.assertEqual(sorted(set(live) - VOLATILE - set(km.FEED_FRAME_FIELDS)), [],
                         "every field of a frame with a live session is in the list")

    def test_the_by_table_is_a_partition_of_the_frame_fields_into_flag_rows_and_a_folded_list(self):
        """The classification behind the published table (the review of 2026-09-18): FEED_BY_ROWS and FEED_BY_FOLDED
        are disjoint and together are every frame field outside the cards (the ledgers among the folded, since the
        third round), so a field added to the frame must be classified here or this fails; every FEED_BY_ROWS value
        on a built frame (an empty board and one live session), the off frame and every fixture is a bool, an int or
        None with no str anywhere, and the off frame's four lists outside FEED_FRAME_FIELDS are empty; and every
        FEED_BY_FOLDED field holds a str somewhere on the module's populated fixture, the witness that the list is
        about what a field can carry."""
        fields = set(km.FEED_FRAME_FIELDS) - {"asks"}
        self.assertEqual(km.FEED_BY_ROWS | km.FEED_BY_FOLDED, fields, "a partition of the frame fields outside the cards")
        self.assertIn("ledgers", km.FEED_BY_FOLDED, "the ledgers are folded (fails before)")
        self.assertFalse(km.FEED_BY_ROWS & km.FEED_BY_FOLDED, "disjoint")
        self.assertEqual(km.FEED_BY_ROWS, {"userTodosOn", "dismissedCount", "showDismissed", "canUndoClear", "off"},
                         "the published rows: a flag or a count each")
        self.assertEqual(OFF_LISTS, {"items", "hosts", "pendingHosts", "pendingDead"})
        self.assertEqual(PUBLIC_NAMES, km.FEED_BY_ROWS | OFF_LISTS | {"other"})
        err = io.StringIO()
        with redirect_stderr(err), mock.patch.object(km, "_alive_sessions", lambda now, tm: []), \
                mock.patch.object(km, "_warm_fleet_bg", lambda now: None), \
                mock.patch.object(km, "_sessions", lambda now, window=None, forks=True: []), \
                mock.patch.object(km, "_sdk", lambda: None):
            built = km.build_feed(NOW, {})
            off = km._feed_off_frame(NOW, {})
        live = _built_with_one_live_session(self)
        faulted = _feed(n=2, viewsFault="tags unavailable: synthetic", off=True)
        del faulted["views"]
        frames = {"built": built, "live": live, "off": off, "fixture": _feed(n=3), "faulted": faulted,
                  "populated": _populated()}
        for name, frame in frames.items():
            for f in km.FEED_BY_ROWS:
                if f in frame:
                    v = frame[f]
                    self.assertTrue(v is None or isinstance(v, (bool, int)), "%s.%s = %r" % (name, f, v))
                    self.assertFalse(_has_str(v), "%s.%s" % (name, f))
            for f in OFF_LISTS:
                if f in frame:
                    self.assertEqual(frame[f], [], "%s.%s: the off frame's federation lists are always empty" % (name, f))
        populated = frames["populated"]
        for f in km.FEED_BY_FOLDED:
            frame = faulted if f == "viewsFault" else populated    # the fault marker rides in place of the views blob
            self.assertTrue(f in frame, "%s: the populated fixture carries every folded field" % f)
            self.assertTrue(_has_str(frame[f]), "%s: a folded field is one that can carry text" % f)


def _populated():
    """A frame with a string in EVERY text-bearing field (FEED_BY_FOLDED), each of a known length: the perturbation and
    classification tests' base. Synthetic throughout."""
    return _feed(n=4, stateUnknown=["dev"],
                 judgeLimit={"loginSessions": [{"name": "web", "host": "TESTHOST", "sid": SID, "color": None}],
                             "billingUnknown": []},
                 bgServices={"web": ["dev server on :3000"]}, clearedForeign=[SID_B + ":g1"],
                 clearNotices=[{"sig": "c1", "text": "cleared the boundary"}],
                 sdkNotices=[{"sig": "k1", "text": "backend restarted"}],
                 userTodoRows=[{"sid": SID, "name": "web", "color": None,
                                "todos": [{"id": "ut-1", "text": "Decide the response shape", "createdT": NOW - 100,
                                           "file": SYNTHETIC_HOME + "/code/notes-api/README.md"}]}])


class SyntheticBuild(unittest.TestCase):
    """(c) and (d): a synthetic build through the pusher's per-entry pass, in process."""

    def setUp(self):
        km._feed_cards_memo = None                               # a fresh build's pass: no memo from another test

    def test_a_synthetic_build_projects_the_expected_bytes_per_app(self):
        feed = _feed(n=40)
        cards, leds, by = _expected(feed)
        rep0 = km._feed_composition_report()                    # fails before: no report
        life_s0 = dict(km._FEED_COMP.life)                      # the stored lifetime sums (the ledgers and the counts among them)
        parts = km._feed_parts(feed)
        rep = km._feed_composition_report()
        last = rep["last"]
        stored = km._FEED_COMP.last                             # the stored pass: the ledgers and the counts kept apart
        self.assertEqual(rep["passes"], rep0["passes"] + 1)
        self.assertEqual(last["cards"], cards, "the cards' bytes: the tint-stripped per-card strings")
        self.assertEqual(stored["ledgers"], leds, "the ledgers' bytes, stored: the per-ledger strings, the known share")
        self.assertEqual(last["by"], _published(by, leds), "the remainder per field (quoted name, separators, sort_keys "
                         "value), published folded: the flag and count rows and `other`, the ledgers and the "
                         "text-bearing fields' sum")
        self.assertEqual(sum(last["by"].values()), sum(by.values()) + leds, "the fold regroups bytes and drops none")
        self.assertEqual(set(last["by"]), {f for f in km.FEED_BY_ROWS if f in feed} | {"other"})
        self.assertEqual(stored["rest"], len(parts[3]), "the stored remainder is the remainder string's length")
        self.assertEqual(last["rest"], len(parts[3]) + leds, "the published rest is the frame outside the cards")
        self.assertEqual(last["frame"], km._feed_est(parts), "the frame figure is the size estimate the wire uses")
        self.assertEqual(last["frame"], cards + leds + sum(by.values()))
        self.assertEqual(last["frame"], last["cards"] + last["rest"])
        self.assertEqual((stored["cardCount"], stored["ledgerCount"], last["ledgersAttached"]), (40, 2, 1))
        self.assertFalse({"cardCount", "ledgerCount", "ledgers"} & set(last), "the counts and the ledgers are withheld")
        apps = last["apps"]
        self.assertEqual(set(apps), {"feed", "fleet", "waiting", "phoneFace"}, "the readers' rows and the projection row")
        self.assertEqual(apps["phoneFace"], {"today": last["frame"], "projected": km._phone_face_est(feed["asks"])},
                         "the phone face projection: the whole frame today beside the face estimate over the build's cards")
        other = _published(by, leds)["other"]                    # the folded fields' sum with the ledgers: the one row published
        flags = {f: by[f] for f in km.FEED_BY_ROWS if f in by}   # the flag and count rows the fixture carries
        self.assertEqual(set(flags), {"userTodosOn", "dismissedCount", "showDismissed", "canUndoClear"})
        self.assertEqual(apps["waiting"], {"today": last["frame"], "projected": other + flags["userTodosOn"]},
                         "the Waiting-on-you pane reads its rows, the switch and the session list: the two folded "
                         "fields count as the whole of `other`, the ledgers inside it, the switch by name")
        self.assertEqual(apps["feed"]["projected"],
                         cards + other + flags["dismissedCount"] + flags["showDismissed"] + flags["canUndoClear"],
                         "the feed pane reads the cards, every flag row but the switch and every folded field but "
                         "three, credited as the whole of `other`, the ledgers it does not read among them; "
                         "clearedForeign stays in, federation drops remote cards from it for the pane")
        self.assertEqual(apps["feed"]["projected"], last["frame"] - flags["userTodosOn"],
                         "which is the frame minus the switch: the difference is a flag row, never the ledgers (fails "
                         "before: the frame minus the ledgers minus the switch, so the difference was the ledgers)")
        fields = km._FEED_APP_ASK_FIELDS["fleet"]
        est = km._ask_fields_est(feed["asks"], fields)
        self.assertEqual(apps["fleet"]["projected"], other + est,
                         "the Outline reads the ledgers, a few fields of each card and three folded fields (the views, "
                         "the session list, the viewer's foreign clears), the ledgers and the three credited as the "
                         "whole of `other`; no `off` here")
        # every projected figure but the Outline's is a sum of published rows, and the Outline's is one plus its
        # card-field estimate (fails before: the projections were exact per-field sums
        # over the stored table, so frame - ledgers - feed.projected - userTodosOn was the userTodoRows row, and
        # waiting.projected minus that minus userTodosOn the sessions row, on every board)
        pub = last["by"]
        self.assertEqual(last["frame"] - apps["feed"]["projected"] - pub["userTodosOn"], 0)
        self.assertNotEqual(apps["waiting"]["projected"] - pub["userTodosOn"], by["sessions"] + by["userTodoRows"])
        self.assertEqual(apps["waiting"]["projected"] - pub["userTodosOn"], pub["other"])
        self.assertGreater(apps["waiting"]["projected"], by["userTodoRows"] + by["userTodosOn"] + by["sessions"],
                           "the row over-counts the pane's three fields by the rest of `other`, and says so")
        # the fold is at report time: the stored table is whole, a row per remainder field with the ledgers and the
        # counts apart, and only the report folds it (with the projections counting the folded set as one, a fold
        # moved before record() would publish the same numbers, so the stored table is pinned directly)
        self.assertEqual(km._FEED_COMP.last["by"], by, "the stored table: a row per remainder field")
        self.assertLessEqual(set(by) & km.FEED_BY_FOLDED, set(km._FEED_COMP.life["by"]), "and the lifetime table too")
        self.assertNotIn("ledgers", km._FEED_COMP.last["by"], "the ledgers are a stored sum, never a row of the table")
        _assert_shape(self, rep, True, km._feed_wire is not None)
        # the card-field estimate: the docstring's arithmetic, done again here over one goal card and one provisional
        # card, and bounded by the texts it counts and the cards it stands in for
        goal, prov = feed["asks"][0], feed["asks"][9]
        self.assertTrue(prov.get("provisional"))

        def one(card):
            n = 2
            for f in fields:
                if f not in card:
                    continue
                v = card[f]
                if isinstance(v, str):
                    n += len(f) + 8 + len(v)
                elif v is None:
                    n += len(f) + 6 + 4
                elif isinstance(v, bool):
                    n += len(f) + 6 + (4 if v else 5)
                else:
                    n += len(f) + 6 + len(repr(v))
            return n
        self.assertEqual(km._ask_fields_est([goal], fields), one(goal))
        self.assertEqual(km._ask_fields_est([prov], fields), one(prov))
        self.assertEqual(km._ask_fields_est([goal, prov, "not a card"], fields), one(goal) + one(prov))
        texts = sum(len(a[f]) for a in feed["asks"] for f in fields if isinstance(a.get(f), str))
        self.assertGreater(est, texts, "at least the texts it names")
        self.assertLess(est, cards, "and less than the cards whole")
        self.assertEqual(km._ask_fields_est([{"color": {"bg": "#123456", "fg": "#ffffff"}}], ("color",)),
                         2 + len("color") + 6 + len(json.dumps({"bg": "#123456", "fg": "#ffffff"})),
                         "a nested value at its repr's length, the JSON length for the frame's nested values")
        # a ledgers-only refill of the same build: the cards memo answers, the ledgers re-size, the projections move by
        # the ledgers alone, and the lifetime sums carry both passes
        refill = dict(feed)
        refill["ledgers"] = [_ledger(tops=5)]
        s0 = dict(km._wire_stats)
        km._feed_parts(refill)
        self.assertEqual(km._wire_stats["feed_cards_hit"], s0["feed_cards_hit"] + 1)
        rep2 = km._feed_composition_report()
        last2 = rep2["last"]
        stored2 = km._FEED_COMP.last
        leds2 = len(json.dumps(refill["ledgers"][0]))
        self.assertEqual((last2["cards"], last2["by"], stored2["cardCount"]), (cards, _published(by, leds2), 40))
        self.assertEqual((stored2["ledgers"], stored2["ledgerCount"]), (leds2, 1))
        self.assertEqual(last2["rest"] - last["rest"], leds2 - leds, "the published rest moves by the ledgers alone")
        self.assertEqual(last2["apps"]["fleet"]["projected"] - apps["fleet"]["projected"], leds2 - leds)
        self.assertEqual(last2["apps"]["waiting"]["projected"] - apps["waiting"]["projected"], leds2 - leds,
                         "credited with the atom, the ledgers inside it")
        self.assertEqual(last2["apps"]["feed"]["projected"] - apps["feed"]["projected"], leds2 - leds)
        self.assertEqual(last2["apps"]["phoneFace"]["projected"], apps["phoneFace"]["projected"],
                         "the face reads no ledger; its estimate is memoized with the cards, so a refill pays none of it")
        life, life0 = rep2["lifetime"], rep0["lifetime"]
        life_s = km._FEED_COMP.life
        self.assertEqual(life["cards"] - life0["cards"], 2 * cards)
        self.assertEqual(life_s["ledgers"] - life_s0["ledgers"], leds + leds2, "the stored lifetime ledgers")
        self.assertEqual(life["frame"] - life0["frame"], last["frame"] + last2["frame"])
        self.assertEqual(life["rest"] - life0["rest"], last["rest"] + last2["rest"])
        self.assertEqual((life_s["cardCount"] - life_s0["cardCount"], life_s["ledgerCount"] - life_s0["ledgerCount"]), (80, 3),
                         "the stored lifetime counts")
        self.assertFalse({"cardCount", "ledgerCount", "ledgers"} & set(life), "withheld from the lifetime table too")
        expect = {k: 2 * v for k, v in _published(by).items()}
        expect["other"] += leds + leds2
        for k, v in expect.items():
            self.assertEqual(life["by"][k] - life0["by"].get(k, 0), v, k)
        self.assertEqual(set(life["by"]), set(last2["by"]), "the lifetime table has the published key set")
        self.assertEqual(sum(life["by"].values()), life["rest"], "the lifetime rows sum to the lifetime rest")
        for app in apps:
            self.assertEqual(life["apps"][app]["today"] - life0["apps"][app]["today"], last["frame"] + last2["frame"], app)
            self.assertEqual(life["apps"][app]["projected"] - life0["apps"][app]["projected"],
                             apps[app]["projected"] + last2["apps"][app]["projected"], app)
        # a build with no ledgers attached (a feed-only push): zero, said so, and no ledger bytes in any projection
        bare = _feed(n=3, build_id=3)
        del bare["ledgers"]
        km._feed_parts(bare)
        last3 = km._feed_composition_report()["last"]
        stored3 = km._FEED_COMP.last
        self.assertEqual((stored3["ledgers"], stored3["ledgerCount"], last3["ledgersAttached"]), (0, 0, 0))
        self.assertEqual(last3["frame"], last3["cards"] + last3["rest"])
        self.assertEqual(last3["rest"], stored3["rest"], "no ledgers: the published rest is the remainder")
        self.assertEqual(rep2["failed"], 0)

    def test_a_fresh_accumulator_reads_as_empty_dicts_and_zeros(self):
        fresh = km._FeedComposition()
        with mock.patch.object(km, "_feed_wire", None):
            rep = fresh.report()
        self.assertEqual(rep["passes"], 0)
        self.assertEqual(rep["failed"], 0)
        self.assertEqual(rep["last"], {})
        self.assertEqual(rep["wire"], {})
        self.assertEqual(rep["lifetime"]["by"], {})
        self.assertEqual(rep["lifetime"]["apps"],
                         {a: {"today": 0, "projected": 0} for a in (*km.FEED_APP_FIELDS, *km.FEED_PROJECTIONS)})
        for path, leaf in _leaves(rep):
            self.assertIsInstance(leaf, int, path)
        json.dumps(rep)
        _assert_shape(self, rep, False, False)
        # `wire` before any whole frame went: the estimate, said inexact
        feed = _feed(n=2)
        parts = km._feed_parts(feed)
        lazy = km._LazyWire(lambda: km._feed_body(feed), km._feed_est(parts), "feed_body")
        with mock.patch.object(km, "_feed_wire", (feed, feed["ledgers"], feed, lazy, km._feed_sig(parts), parts)):
            self.assertEqual(fresh.report()["wire"], {"bytes": km._feed_est(parts), "exact": 0})
            lazy.text()
            self.assertEqual(fresh.report()["wire"], {"bytes": len(km._feed_body(feed)), "exact": 1})
            # after one pass every sub-block has its full shape and none is empty (the memo's sub-blocks never collapse)
            _fresh_pass(feed, fresh)
            _assert_shape(self, fresh.report(), True, True)

    def test_the_populated_block_passes_the_exports_paste_safe_walk_on_cards_in_every_column(self):
        """(f): the served /perf document is paste-safe by contract (cli/perf_public.py: identifier keys; no id, path, text
        or clock stamp; measurements stay), and the served walks (tests/test_perf_stats.py ServedSnapshotIsPasteSafe,
        tests/test_perf_export.py ServedKernel) read whatever the module-global accumulator holds when they run, which in
        a parallel run may be no pass at all (the lifetime rows zeroed, `last` empty). So the populated block is walked
        here: cards in every column (working, needs_input, completed; a provisional card among them; two sessions) and
        two ledgers through the pusher's per-entry pass, then a frame carrying the views fault marker and the off flag,
        then a REAL off frame (the production frame while task tracking is off), each report as GET /perf serves it.
        Beyond the fixture, every name the block can ever carry is held to the grammar and to the export's fold: its
        fixed names, every `by` row a published table can carry (FEED_BY_ROWS, the off frame's own lists and `other`),
        every frame field and frame list the stored table is keyed by (a wider set than the published one), the app
        names and the projection names."""
        fresh = mock.patch.object(km, "_FEED_COMP", km._FeedComposition())
        fresh.start()
        self.addCleanup(fresh.stop)
        asks = ([_card(i, column="working") for i in range(4)]
                + [_card(10 + i, column="needs_input", provisional=(i == 0)) for i in range(3)]
                + [_card(20 + i, column="completed") for i in range(3)]
                + [_card(40 + i, sid=SID_B, column=("working", "needs_input", "completed")[i]) for i in range(3)])
        self.assertEqual({a["column"] for a in asks}, set(km.FEED_PHONE_FACE_ACTIVE) | {"completed"}, "cards in every column")
        feed = _feed(asks=asks)
        self.assertEqual(len(feed["ledgers"]), 2)
        km._feed_parts(feed)
        block = km._feed_composition_report()
        last = block["last"]
        stored = km._FEED_COMP.last
        self.assertEqual((block["passes"], stored["cardCount"], stored["ledgerCount"], last["ledgersAttached"]), (1, 13, 2, 1))
        self.assertEqual(set(last["apps"]), {"feed", "fleet", "waiting", "phoneFace"}, "the app rows and the projection row")
        self.assertTrue(all(row["today"] > row["projected"] > 0 for row in last["apps"].values()), last["apps"])
        _, leds1, by1 = _expected(feed)
        self.assertEqual(set(last["by"]), {f for f in km.FEED_BY_ROWS if f in feed} | {"other"},
                         "the published table: the flag and count rows the frame carries, and `other`")
        self.assertLessEqual(set(last["by"]), PUBLIC_NAMES)
        self.assertEqual(last["by"], _published(by1, leds1))
        _paste_safe(self, block)
        # the two frame fields the fixture frame does not carry: the views fault marker (free text on the frame: romp's
        # wording plus the OS error text, which can name a path, so its bytes are in `other`) and the off frame's flag
        # (a fixed spelling: its own row)
        faulted = _feed(asks=asks, viewsFault="tags unavailable: synthetic", off=True)
        del faulted["views"]
        km._feed_parts(faulted)
        block2 = km._feed_composition_report()
        _, leds2, by2 = _expected(faulted)
        self.assertEqual(block2["passes"], 2)
        self.assertIn("off", block2["last"]["by"])
        self.assertNotIn("viewsFault", block2["last"]["by"])
        self.assertEqual(block2["last"]["by"]["other"], sum(v for k, v in by2.items() if k in km.FEED_BY_FOLDED) + leds2)
        self.assertIn("viewsFault", km.FEED_BY_FOLDED)
        life = block2["lifetime"]["by"]
        self.assertIn("off", life, "the lifetime table carries both passes")
        self.assertFalse({"viewsFault", "views"} & set(life), "and no folded name")
        self.assertEqual(life["other"], last["by"]["other"] + block2["last"]["by"]["other"],
                         "the lifetime `other` is the two passes' folded sums")
        self.assertEqual(set(life), set(last["by"]) | set(block2["last"]["by"]))
        self.assertEqual(sum(life.values()), block2["lifetime"]["rest"])
        _paste_safe(self, block2)
        # a REAL off frame (task tracking off: no build, every list the readers iterate, empty, the notice rings and the
        # bell's bits) through the same pass on a fresh accumulator: its four lists outside FEED_FRAME_FIELDS (items,
        # hosts, pendingHosts, pendingDead) stay their own rows, each the bytes of an empty list under its name, so the
        # key bucketing honours _FEED_FRAME_LISTS; `off` and the bell's bits are rows; the rings, the pips' lists and
        # the todo rows are in `other`; and the report passes the export's walk
        with mock.patch.object(km, "_FEED_COMP", km._FeedComposition()), \
                mock.patch.object(km, "_alive_sessions", lambda now, tm: []):
            km._feed_cards_memo = None
            off = km._feed_off_frame(NOW, {})
            km._feed_parts(off)
            block3 = km._feed_composition_report()
            stored3 = km._FEED_COMP.last
        _, _, by3 = _expected(off)
        last3 = block3["last"]
        self.assertEqual((block3["passes"], stored3["cardCount"], stored3["ledgerCount"], last3["ledgersAttached"]), (1, 0, 0, 1))
        self.assertEqual(off.get("ledgers"), [], "the off frame ships an empty attach")
        for name in OFF_LISTS:
            self.assertEqual(last3["by"][name], len(json.dumps(name)) + 4 + 2, "%s: an empty list under its name" % name)
        self.assertEqual(last3["by"]["off"], len('"off"') + 4 + len("true"))
        self.assertLessEqual({"dismissedCount", "showDismissed", "canUndoClear", "userTodosOn"}, set(last3["by"]))
        self.assertEqual(set(last3["by"]), {f for f in km.FEED_BY_ROWS if f in off} | OFF_LISTS | {"other"})
        self.assertEqual(last3["by"], _published(by3))
        self.assertEqual(sum(last3["by"].values()), last3["rest"])
        for f in ("working", "awaiting", "stateUnknown", "order", "sessions", "userTodoRows", "userTodos",
                  "clearNotices", "sdkNotices", "syncNotices"):
            self.assertIn(f, off)
            self.assertNotIn(f, last3["by"], "%s: folded" % f)
        _paste_safe(self, block3)
        # every name the block can carry, whatever the frame: an identifier the kernel's own grammar admits, and a key the
        # export neither drops (the denylist) nor coarsens (a bound, an uptime), so every published `by` row (the flag and
        # count rows, the off frame's own lists, `other`), every name the stored table is keyed by (the frame fields and
        # the frame lists: the wider set, in case a row is ever published) and every app or projection row survive the
        # export whole. A name added to _FEED_FRAME_LISTS that the export drops or coarsens fails here.
        names = (set(km._FeedComposition.SUMS) | set(km._FeedComposition.PUBLISHED)
                 | {"passes", "failed", "lifetime", "last", "wire", "bytes", "exact",
                                                   "ledgersAttached", "by", "apps", "today", "projected", "other"}
                 | set(km.FEED_FRAME_FIELDS) | set(km._FEED_FRAME_LISTS) | set(km.FEED_BY_ROWS) | PUBLIC_NAMES
                 | set(km.FEED_APP_FIELDS) | set(km.FEED_PROJECTIONS))
        for name in sorted(names):
            self.assertTrue(km._PERF_IDENT.fullmatch(name), name)
            self.assertFalse(pp.denied(name, 1), "%s: a key the export drops" % name)
            self.assertNotIn(name, pp.BOUND_KEYS | pp.UPTIME_KEYS, "%s: a key the export coarsens" % name)
        table = {"memos": {"feedComposition": {"last": {"by": {n: 1 for n in names}}}}}
        self.assertEqual(pp.fold(table), table)

    def test_the_phone_face_projection_sits_far_below_the_feed_row_and_counts_the_active_cards(self):
        """(e): the 60-card, 2-ledger fixture (every card in the Working column, so every card active) against the
        feed row; the arithmetic done again here; the active set and the group rows on fixtures that move the column."""
        fields = km.FEED_PHONE_FACE_FIELDS
        feed = _feed(n=60)
        self.assertTrue(all(f in a for a in feed["asks"] for f in fields), "every fixture card carries the five face fields")
        km._feed_parts(feed)
        last = km._feed_composition_report()["last"]
        self.assertEqual((km._FEED_COMP.last["cardCount"], km._FEED_COMP.last["ledgerCount"]), (60, 2))
        face, full = last["apps"]["phoneFace"]["projected"], last["apps"]["feed"]["projected"]
        ratio = full / face
        self.assertGreaterEqual(ratio, 8,
                                "the face frame sits far below the feed row: %d B against the feed row's %d B (the "
                                "frame's %d B), a ratio of %.1f; bounded at 8" % (face, full, last["frame"], ratio))
        self.assertLess(face, last["apps"]["fleet"]["projected"], "and below the Outline's card fields plus ledgers")

        def one(card, fs):
            n = 2
            for f in fs:
                if f not in card:
                    continue
                v = card[f]
                n += len(f) + (8 + len(v) if isinstance(v, str) else 6 + len(repr(v)))
            return n
        # the arithmetic, done again here: a face per active card (five fields at their lengths), one summary row per
        # session with a card (its sid and the count of the cards it holds); the fixture's cards share one sid
        self.assertEqual(face, sum(one(a, fields) for a in feed["asks"]) + one({"sid": SID, "count": 60}, ("sid", "count")))
        # a fixture where every card is active projects more than one where none is: the same cards, the column moved
        # to completed, leave only the one summary row
        none = [_card(i, column="completed", provisional=(i % 10 == 9)) for i in range(60)]
        est_none = km._phone_face_est(none)
        self.assertEqual(est_none, one({"sid": SID, "count": 60}, ("sid", "count")), "no active card: the group row alone")
        self.assertGreater(km._phone_face_est(feed["asks"]), est_none)
        self.assertGreater(face, 50 * est_none, "sixty faces against one group row")
        # active is the Working and Blocked columns, whatever the card's kind; the groups are the sessions with a card
        mixed = ([_card(i, column="working") for i in range(10)]
                 + [_card(10 + i, column="needs_input", provisional=True) for i in range(5)]
                 + [_card(20 + i, column="completed") for i in range(20)]
                 + [_card(40 + i, sid=SID_B, column="completed" if i % 2 else "working") for i in range(4)])
        active = [a for a in mixed if a["column"] in ("working", "needs_input")]
        self.assertEqual(len(active), 17)
        self.assertEqual(km._phone_face_est(mixed),
                         sum(one(a, fields) for a in active)
                         + one({"sid": SID, "count": 35}, ("sid", "count")) + one({"sid": SID_B, "count": 4}, ("sid", "count")),
                         "seventeen faces and two group rows, every card counted in its group")
        self.assertEqual(km._phone_face_est([]), 0)
        self.assertEqual(km._phone_face_est(["not a card", 3]), 0)
        # the frame's own pips are session names, not card groups: moving a name between them moves no byte of the face
        moved = dict(feed, working=[], awaiting=["web"], stateUnknown=["api"])
        km._feed_cards_memo = None
        km._feed_parts(moved)
        self.assertEqual(km._feed_composition_report()["last"]["apps"]["phoneFace"]["projected"], face)

    def test_an_accounting_fault_is_counted_and_said_once_and_the_frame_is_unaffected(self):
        """The RECORDING half of the guard: record() raising is counted, said once and never reaches the frame. This
        proves only that half; the estimates' half (a raise in _ask_fields_est or a projection estimator, which sat
        outside the try until the review of 2026-09-18) is AccountingGuard's, with a card whose sid cannot be hashed."""
        feed = _feed(n=2)
        err = io.StringIO()
        with mock.patch.object(km._FeedComposition, "record", side_effect=KeyError("synthetic")), redirect_stderr(err):
            parts = km._feed_parts(feed)
            failed = km._FEED_COMP.failed
            km._feed_parts(_feed(n=2, build_id=2))
        self.assertEqual(parts[3], json.dumps(_rest_of(feed), sort_keys=True), "the frame's remainder is the same bytes")
        self.assertEqual(km._FEED_COMP.failed - failed, 1)
        self.assertEqual(err.getvalue().count("feed composition: the accounting raised"), 1, "said once")

    def test_the_remainder_is_encoded_per_field_and_joined_byte_for_byte(self):
        odd = {"zeta": {"b": 1, "a": [3, 2, {"y": None, "x": True}]}, "alpha": "ünïcode ✓ \"quoted\" \\ back",
               "empty": {}, "none": None, "flt": 1.5, "neg": -7, "big": 10 ** 20, "lst": [], "t": True, "f": False,
               "nested": {"k2": {"z": 1, "a": 2}, "k1": ["a", {"b": 1}]}, "Upper": 1, "_under": 2, "a.dot": 3}
        for extra in (odd, {}, {"only": 1}):
            feed = _feed(n=2)
            for k in list(_rest_of(feed)):
                del feed[k]
            feed.update(extra)
            parts = km._feed_parts(feed)
            self.assertEqual(parts[3], json.dumps(extra, sort_keys=True), extra)
            self.assertEqual(parts[2], extra)
            last = km._feed_composition_report()["last"]
            leds = km._FEED_COMP.last["ledgers"]
            self.assertEqual(km._FEED_COMP.last["rest"], len(parts[3]))
            self.assertEqual(last["rest"], len(parts[3]) + leds, "the published rest carries the ledgers")
            # an empty remainder's two braces are not yet charged to a row (corrected in the arithmetic commit)
            self.assertEqual(sum(last["by"].values()), last["rest"] if extra else last["rest"] - 2)
            # none of these keys is a frame field: each is counted under `other` and never stands as a row (fails
            # before: the table's keys were the frame dict's keys at runtime, and this pin blessed them)
            self.assertEqual(last["by"], {"other": last["rest"]} if extra else {"other": leds}, extra)
        # a value json cannot encode meets the wire default once, as before, and its str() bytes are in the field's
        # row, which for a key outside the checked-in names is `other`, beside the folded fields' bytes
        base = _feed(n=2)
        _, _, by_base = _expected(base)
        feed = dict(base)
        feed["extra"] = {"x"}
        s0 = dict(km._wire_stats)
        err = io.StringIO()
        with redirect_stderr(err):
            parts = km._feed_parts(feed)
        self.assertEqual(km._wire_stats["default_str"] - s0["default_str"], 1)
        self.assertEqual(parts[3], json.dumps(_rest_of(feed), sort_keys=True, default=str))
        published = km._feed_composition_report()["last"]["by"]
        self.assertNotIn("extra", published)
        self.assertEqual(published["other"], sum(v for k, v in by_base.items() if k in km.FEED_BY_FOLDED)
                         + km._FEED_COMP.last["ledgers"] + len('"extra": ') + len(json.dumps(str({"x"}))) + 2)
        # a key that is not a str (never the frame's case) takes the whole encode under one name: the same bytes for
        # keys json coerces, and the same TypeError the whole sort_keys encode always raised on keys it cannot order
        feed = _feed(n=2)
        for k in list(_rest_of(feed)):
            del feed[k]
        feed[7] = "seven"
        parts = km._feed_parts(feed)
        self.assertEqual(parts[3], json.dumps({7: "seven"}, sort_keys=True))
        self.assertEqual(km._feed_composition_report()["last"]["by"], {"other": len(parts[3]) + km._FEED_COMP.last["ledgers"]})
        mixed = _feed(n=2)
        mixed[7] = "seven"
        with self.assertRaises(TypeError):
            json.dumps(_rest_of(mixed), sort_keys=True)
        with self.assertRaises(TypeError):
            km._feed_parts(mixed)

    def test_a_build_encodes_each_part_once_and_a_refill_encodes_no_card(self):
        """Every encode of a pass, counted at json.JSONEncoder.encode (json.dumps with any argument constructs an
        encoder and calls it; the remainder goes through ONE encoder per pass since the review of 2026-09-18, whose
        encode() is what json.dumps ran per field): one per card, per ledger, and per remainder field name and value on
        a build; the ledgers and the remainder, no card, on a refill; and one sort_keys encoder constructed per pass
        (fails before: one per remainder field, about forty percent of the per-field overhead)."""
        feed = _feed(n=12)
        rest = _rest_of(feed)
        real_dumps, Real = km.json.dumps, km.json.JSONEncoder
        dumps_calls, encodes, made = [], [], []

        class Counting(Real):
            def __init__(self, *a, **kw):
                made.append(kw)
                super().__init__(*a, **kw)

            def encode(self, o):
                encodes.append(o)
                return super().encode(o)

        def counting_dumps(obj, *a, **kw):
            dumps_calls.append(obj)
            return real_dumps(obj, *a, **kw)

        def cards_in(objs):
            return sum(1 for o in objs if isinstance(o, dict) and "itemId" in o)
        patches = (mock.patch.object(km.json, "JSONEncoder", Counting), mock.patch.object(km.json, "dumps", side_effect=counting_dumps))
        with patches[0], patches[1]:
            km._feed_parts(feed)
        self.assertEqual(len(encodes), 12 + len(feed["ledgers"]) + 2 * len(rest),
                         "one encode per card, per ledger, and per remainder field (its name and its value)")
        self.assertEqual(cards_in(encodes), 12)
        self.assertEqual(len(dumps_calls), 12 + len(feed["ledgers"]), "json.dumps runs per card and per ledger; the "
                         "remainder's fields go through the pass's one encoder")
        self.assertEqual(sum(1 for kw in made if kw.get("sort_keys")), 1, "one sort_keys encoder per pass")
        self.assertEqual(len(made), 12 + len(feed["ledgers"]) + 1)
        # the remainder's names and values are each encoded once, in sorted order, name then value
        tail = encodes[-2 * len(rest):]
        self.assertEqual(tail[0::2], sorted(rest))
        self.assertEqual(tail[1::2], [rest[k] for k in sorted(rest)])
        del encodes[:], dumps_calls[:], made[:]
        refill = dict(feed)
        refill["ledgers"] = [_ledger(tops=1)]
        with patches[0], patches[1]:
            km._feed_parts(refill)
        self.assertEqual(len(encodes), 1 + 2 * len(rest), "a refill encodes the ledgers and the remainder, no card")
        self.assertEqual(cards_in(encodes), 0)
        self.assertEqual(len(dumps_calls), 1)
        self.assertEqual(sum(1 for kw in made if kw.get("sort_keys")), 1)
        # the wire's signature and delta read the same strings as before
        self.assertEqual(km._feed_sig(km._feed_parts(feed))[0], json.dumps(rest, sort_keys=True))


class PublishedTable(unittest.TestCase):
    """(g): the `by` table as the block publishes it. Each text-bearing field's bytes were a row of their own, and on a
    small board a row was the length of ONE string (selfHost: 16 plus the machine's name; working: 17 plus one session's
    name; userTodoRows: a todo's text, which can name a path), a number the export's identifier scan cannot see. The
    remainder equals the sum of the table exactly, so dropping or coarsening one row alone re-derives it; the fix folds
    a PINNED list of fields (FEED_BY_FOLDED, classified by what a field can carry) into one row, `other`, at report
    time, on the last and the lifetime tables alike, so the published table's shape is the same whatever the board.
    The projections read the stored table and count the folded set as ONE atom (an app that reads any folded field is
    credited with all of `other`): with per-field partial sums published beside the frame, the ledgers and the flag
    rows, the userTodoRows and sessions rows were re-derivable by subtraction on every board. So every published
    number but the Outline's row is a sum of published rows, and a one-character step in any folded field moves the
    same published leaves by the same amounts, whichever field took it: the perturbation below checks every integer
    leaf of the report, and the invariant's wording is pinned in its scoped form (FEED_COMPOSITION_INVARIANT).
    The third round (2026-09-19) put the ledgers in the fold and withheld the two counts: `ledgers` beside
    `ledgerCount` was one session's whole ledger row on a one-session board, and the ledger count is the chat tab
    count, which /perf publishes elsewhere, so the sum was never an aggregate from the reader's side; a ledger's text
    is a step below like any folded field's, and the one-session board is held to no published number or difference
    of two being the ledger row's length."""

    def setUp(self):
        km._feed_cards_memo = None

    @staticmethod
    def _tables(frame):
        rep = _report(_fresh_pass(frame))
        return rep["last"], rep["lifetime"]

    @staticmethod
    def _signature(rep_a, rep_b):
        """Every integer leaf of the published block that moved between two reports, with its delta: what a reader of
        the block sees of a step. Both reports have the same leaves."""
        fa = {p: v for p, v in _leaves({"last": rep_a["last"], "lifetime": rep_a["lifetime"]}) if isinstance(v, int)}
        fb = {p: v for p, v in _leaves({"last": rep_b["last"], "lifetime": rep_b["lifetime"]}) if isinstance(v, int)}
        assert set(fa) == set(fb), sorted(set(fa) ^ set(fb))
        return {p: fb[p] - fa[p] for p in fa if fb[p] != fa[p]}

    # the leaves a one-byte step in any folded field moves, each by one: the whole-frame figures, `other`, every app's
    # `today`, and the `projected` of every app that reads a folded field (the phoneFace row reads only cards)
    STEP_LEAVES = frozenset(".%s.%s" % (t, leaf) for t in ("last", "lifetime")
                            for leaf in ("frame", "rest", "by.other", "apps.feed.today", "apps.fleet.today",
                                         "apps.waiting.today", "apps.phoneFace.today", "apps.feed.projected",
                                         "apps.fleet.projected", "apps.waiting.projected"))

    def _one_char_step(self, field, base, variant, what):
        """`variant` is `base` with one string of `field` one character longer: the field's own bytes move by one and
        no other field's; the published tables (last and lifetime) name no such field, have the same key set, agree on
        every row but `other`, and `other` moves by exactly one; both remainders equal their table's sum; after both
        passes on ONE accumulator the lifetime `other` is the two passes' folded sums; and over EVERY integer leaf of
        the block the step moves exactly STEP_LEAVES, each by one, so no leaf and no difference of leaves says which
        field took the step (fails before: the step moved apps.waiting.projected for a todo's text or a session's
        name and not for the hostname, and apps.feed.projected for the hostname and not for a todo's text). Returns
        the signature, for the caller to hold equal across fields."""
        _, leds_a, by_a = _expected(base)
        _, leds_b, by_b = _expected(variant)
        self.assertIn(field, km.FEED_BY_FOLDED, what)
        if field == "ledgers":                                   # the ledgers: a stored sum, folded at report time
            self.assertEqual(leds_b - leds_a, 1, "%s: the step is one byte of the ledgers" % what)
            self.assertEqual(by_a, by_b, "%s: no remainder field moved" % what)
        else:
            self.assertEqual(by_b[field] - by_a[field], 1, "%s: the step is one byte of %s" % (what, field))
            self.assertEqual(leds_a, leds_b, "%s: the ledgers are unchanged" % what)
        for k in set(by_a) | set(by_b):
            if k != field:
                self.assertEqual(by_a.get(k), by_b.get(k), "%s: %s is unchanged" % (what, k))
        ra, rb = _report(_fresh_pass(base)), _report(_fresh_pass(variant))
        la, lla, lb, llb = ra["last"], ra["lifetime"], rb["last"], rb["lifetime"]
        sig = self._signature(ra, rb)
        self.assertEqual(set(sig), self.STEP_LEAVES, "%s: the leaves the step moves" % what)
        self.assertEqual(set(sig.values()), {1}, "%s: each by the one byte" % what)
        for name, ta, tb in (("last", la["by"], lb["by"]), ("lifetime", lla["by"], llb["by"])):
            self.assertNotIn(field, ta, "%s: %s is not a published row (%s)" % (what, field, name))
            self.assertNotIn(field, tb, "%s: %s is not a published row (%s)" % (what, field, name))
            self.assertEqual(set(ta), set(tb), "%s: the same rows whatever the string's length (%s)" % (what, name))
            self.assertLessEqual(set(ta), PUBLIC_NAMES, what)
            self.assertEqual({k: v for k, v in ta.items() if k != "other"}, {k: v for k, v in tb.items() if k != "other"},
                             "%s: every published row but `other` is unchanged (%s)" % (what, name))
            self.assertEqual(tb["other"] - ta["other"], 1, "%s: `other` moves by the one byte (%s)" % (what, name))
        for last, life in ((la, lla), (lb, llb)):
            self.assertEqual(sum(last["by"].values()), last["rest"], what)
            self.assertEqual(sum(life["by"].values()), life["rest"], what)
        comp = _fresh_pass(base)
        _fresh_pass(variant, comp)
        rep = _report(comp)
        self.assertEqual(set(rep["lifetime"]["by"]), set(rep["last"]["by"]), what)
        self.assertEqual(rep["lifetime"]["by"]["other"], la["by"]["other"] + lb["by"]["other"], what)
        self.assertEqual(sum(rep["lifetime"]["by"].values()), rep["lifetime"]["rest"], what)
        self.assertEqual(rep["lifetime"]["rest"], la["rest"] + lb["rest"], what)
        return sig

    def test_a_one_character_step_in_any_text_bearing_field_moves_only_the_other_row(self):
        """One step per folded field (fails before: HEAD published each as its own row, which moved with the string):
        the hostname, each pips list's one name, a session id in the order, a session's name and its repository string,
        a todo's text, its path and its row's name, the todo map's key, a tag name, the latch's login row (a name and a
        host), a service chip's session name and its description, a foreign clear's id, one notice in each ring, the
        views fault text on the faulted frame, and (the third round) a ledger's top title and a ledger's session name
        (fails before: `ledgers` was its own published row, so those two steps moved it and the folded steps did not).
        Every step has the same signature over every integer leaf of the block, so a reader cannot tell a hostname
        step from a todo-text step, a session-name step or a ledger-text step."""
        base = _populated()
        steps, sigs = [], []

        def step(field, what, mutate):
            variant = copy.deepcopy(base)
            mutate(variant)
            steps.append(field)
            sigs.append(self._one_char_step(field, base, variant, what))
        step("ledgers", "a ledger's top title", lambda f: f["ledgers"][0]["ledger"]["tops"].__setitem__(0, "t" * 2001))
        step("ledgers", "a ledger's session name", lambda f: f["ledgers"][1].update(name="apix"))
        step("selfHost", "the machine's hostname", lambda f: f.update(selfHost="TESTHOSTX"))
        step("working", "a working session's name", lambda f: f.update(working=["webx"]))
        step("awaiting", "an awaiting session's name", lambda f: f.update(awaiting=["apix"]))
        step("stateUnknown", "an unreadable session's name", lambda f: f.update(stateUnknown=["devx"]))
        step("order", "a session id in the order", lambda f: f.update(order=[SID, SID_B + "0"]))
        step("sessions", "a session's name", lambda f: f["sessions"][0].update(name="webx"))
        step("sessions", "a session's repository string", lambda f: f["sessions"][1].update(githubRepo="example/notes-apix"))
        step("userTodoRows", "a todo's text", lambda f: f["userTodoRows"][0]["todos"][0].update(text="Decide the response shapex"))
        step("userTodoRows", "a todo's path", lambda f: f["userTodoRows"][0]["todos"][0].update(file=SYNTHETIC_HOME + "/code/notes-api/README.mdx"))
        step("userTodoRows", "a todo row's session name", lambda f: f["userTodoRows"][0].update(name="webx"))
        step("userTodos", "the todo map's key", lambda f: f.update(userTodos={SID + "0": 1}))
        step("views", "a tag name", lambda f: f["views"]["tags"].update({"backendx": f["views"]["tags"].pop("backend")}))
        step("judgeLimit", "a login row's session name", lambda f: f["judgeLimit"]["loginSessions"][0].update(name="webx"))
        step("judgeLimit", "a login row's host name", lambda f: f["judgeLimit"]["loginSessions"][0].update(host="TESTHOSTX"))
        step("bgServices", "a service chip's session name", lambda f: f.update(bgServices={"webx": f["bgServices"]["web"]}))
        step("bgServices", "a service description", lambda f: f.update(bgServices={"web": ["dev server on :3000x"]}))
        step("clearedForeign", "a foreign clear's id", lambda f: f.update(clearedForeign=[SID_B + ":g10"]))
        step("clearNotices", "a clear notice's text", lambda f: f["clearNotices"][0].update(text="cleared the boundaryx"))
        step("sdkNotices", "an SDK notice's text", lambda f: f["sdkNotices"][0].update(text="backend restartedx"))
        step("syncNotices", "a sync notice's text", lambda f: f["syncNotices"][0].update(text="pulled 3 commitsx"))
        faulted = copy.deepcopy(base)
        del faulted["views"]
        faulted["viewsFault"] = "tags unavailable: synthetic"
        longer = copy.deepcopy(faulted)
        longer["viewsFault"] += "x"
        steps.append("viewsFault")
        sigs.append(self._one_char_step("viewsFault", faulted, longer, "the views fault text"))
        self.assertEqual(set(steps), set(km.FEED_BY_FOLDED), "one step at least per folded field")
        self.assertEqual(len({json.dumps(s, sort_keys=True) for s in sigs}), 1,
                         "every folded-field step moves the same leaves by the same amounts: indistinguishable")

    def test_no_published_number_or_difference_isolates_a_folded_field_on_a_one_session_board(self):
        """The board where a single leaf isolated one string (the review's re-derivation): one working session with no
        repository string, no card, no open todo, no tag, no notice and no service chip, its ledger row attached. Then
        the sessions field is a constant plus the session name's length, and a Waiting-on-you row that summed its
        three fields by name (userTodoRows, the switch, sessions) published that length: waiting.projected minus the
        switch minus (frame - ledgers - feed.projected - the switch) was the sessions row exactly, and the sessions
        row moved for the session's name and for nothing else (fails before). And `ledgers` was that one ledger row's
        length outright, beside a ledgerCount of 1, and frame - cards - rest and frame - feed.projected - userTodosOn
        were it again (fails before, the third round): now no published integer leaf and no difference of two is the
        row's length. Six one-character steps (the hostname, the session's name in the session list, its name in the
        working pips, a session id in the order, the ledger's working note, the ledger's session name) have one
        signature over every integer leaf; each projected row but the Outline's is a sum of published rows, and the
        Outline's is `other` alone here (no card, so its estimate is zero); and the candidate the
        re-derivation used for the hostname row (the feed row's remainder share minus twice the sessions estimate,
        plus a constant read from the source) moves the wrong way under a hostname step, so no constant makes it the
        hostname row for two hostnames of different length."""
        def board(host="TESTHOST", name="web", pip="web", order=(SID,), note="", led_name="web"):
            ledger = {"sid": SID, "name": led_name, "color": None, "status": {"state": "working"},
                      "ledger": {"tops": ["Synthetic goal 1"], "workingNote": note}}
            return _feed(n=0, asks=[], ledgers=[ledger], order=list(order), working=[pip], awaiting=[], bgServices={},
                         sessions=[{"sid": SID, "name": name, "color": None, "githubRepo": None}], userTodos={},
                         userTodoRows=[], views={"seq": 3, "tags": {}}, dismissedCount=0, canUndoClear=False,
                         syncNotices=[], selfHost=host)
        base = board()
        _, leds, by = _expected(base)
        self.assertEqual(by["sessions"] - len("web"), len(json.dumps("sessions")) + 4 + len(json.dumps(
            [{"sid": SID, "name": "", "color": None, "githubRepo": None}], sort_keys=True)),
            "on this board the sessions field is a constant plus the session name's length")
        row_len = len(json.dumps(base["ledgers"][0]))
        self.assertEqual(leds, row_len, "and the ledgers' bytes are that one row's length")
        comp = _fresh_pass(base)
        rep = _report(comp)
        last = rep["last"]
        pub = last["by"]
        self.assertEqual((last["cards"], comp.last["ledgers"], comp.last["ledgerCount"]), (0, row_len, 1))
        self.assertNotIn("ledgers", last)
        self.assertEqual(set(pub), {"userTodosOn", "dismissedCount", "showDismissed", "canUndoClear", "other"})
        flags = pub["dismissedCount"] + pub["showDismissed"] + pub["canUndoClear"]
        self.assertEqual(last["apps"]["waiting"]["projected"], pub["other"] + pub["userTodosOn"])
        self.assertEqual(last["apps"]["feed"]["projected"], pub["other"] + flags)
        self.assertEqual(last["apps"]["fleet"]["projected"], pub["other"], "no card, no `off`: `other` alone, the ledger in it")
        self.assertEqual(last["apps"]["phoneFace"]["projected"], 0)
        # the re-derivation's two steps, on the published numbers: neither is a folded row any more
        d1 = last["frame"] - last["apps"]["feed"]["projected"] - pub["userTodosOn"]
        self.assertEqual(d1, 0, "not the userTodoRows row (%d), and not the ledgers (%d)" % (by["userTodoRows"], row_len))
        self.assertNotEqual(last["apps"]["waiting"]["projected"] - pub["userTodosOn"] - d1, by["sessions"],
                            "not the sessions row")
        # the ledger row's length is no published integer leaf, no difference of two and no sum of two (fails before:
        # last.ledgers, frame - cards - rest, frame - feed.projected - userTodosOn, and the lifetime twins)
        ints = [(p, v) for p, v in _leaves({"last": last, "lifetime": rep["lifetime"]}) if isinstance(v, int)]
        hits = [p for p, v in ints if v == row_len]
        hits += ["%s - %s" % (p, q) for p, v in ints for q, w in ints if p != q and v - w == row_len]
        hits += ["%s + %s" % (p, q) for p, v in ints for q, w in ints if p < q and v + w == row_len]
        self.assertEqual(hits, [], "the ledger row's length (%d) is recoverable" % row_len)
        steps = {"the hostname": board(host="TESTHOSTX"), "the session's name": board(name="webx"),
                 "the working pip": board(pip="webx"), "a session id in the order": board(order=(SID + "0",)),
                 "the ledger's working note": board(note="n"), "the ledger's session name": board(led_name="webx")}
        sigs = {}
        for what, variant in steps.items():
            _, leds_v, by_v = _expected(variant)
            self.assertEqual(sum(by_v.values()) + leds_v - sum(by.values()) - leds, 1, what)
            sigs[what] = self._signature(rep, _report(_fresh_pass(variant)))
            self.assertEqual(set(sigs[what]), self.STEP_LEAVES, what)
            self.assertEqual(set(sigs[what].values()), {1}, what)
        self.assertEqual(len({json.dumps(s, sort_keys=True) for s in sigs.values()}), 1, sigs)
        # the hostname candidate: F = the feed row minus the cards and the flag rows (the pane's remainder share), S =
        # the sessions estimate above; F - 2S + K for a constant K. Under a one-character hostname step F and S each
        # move by one, so the candidate moves by minus one while the hostname row moves by plus one
        def candidate(r):
            l = r["last"]
            f = l["apps"]["feed"]["projected"] - l["cards"] - sum(l["by"][k] for k in l["by"] if k not in ("other", "userTodosOn"))
            s = l["apps"]["waiting"]["projected"] - l["by"]["userTodosOn"] - (l["frame"] - l["apps"]["feed"]["projected"] - l["by"]["userTodosOn"])
            return f - 2 * s
        longer = _report(_fresh_pass(steps["the hostname"]))
        _, _, by_l = _expected(steps["the hostname"])
        self.assertEqual(by_l["selfHost"] - by["selfHost"], 1)
        self.assertEqual(candidate(longer) - candidate(rep), -1, "the candidate moves against the hostname row")

    def test_the_exported_table_carries_the_published_rows_and_no_row_recovers_the_hostname(self):
        """The export path (cli/perf_public.py fold, the form `romp perf export --public` writes): two boards identical
        but for the hostname's length export the same rows with the same values, `other` apart, so no exported row
        minus a constant is the hostname's length; the row set is the published set, and the fold keeps it whole."""
        short, long = _populated(), _populated()
        long["selfHost"] = "TESTHOST-LONGER-NAME"
        docs = []
        for frame in (short, long):
            rep = _report(_fresh_pass(frame))
            doc = {"memos": {"feedComposition": rep}}
            self.assertEqual(pp.fold(doc), doc, "the export keeps the block whole")
            docs.append(pp.fold(doc)["memos"]["feedComposition"])
        a, b = docs
        for table in ("last", "lifetime"):
            ta, tb = a[table]["by"], b[table]["by"]
            self.assertEqual(set(ta), set(tb))
            self.assertEqual(set(ta), {f for f in km.FEED_BY_ROWS if f in short} | {"other"})
            self.assertNotIn("selfHost", ta)
            self.assertEqual({k: v for k, v in ta.items() if k != "other"}, {k: v for k, v in tb.items() if k != "other"})
            self.assertEqual(tb["other"] - ta["other"], len(long["selfHost"]) - len(short["selfHost"]))
        # the whole-frame figures move with the hostname, as the base's push.send bytes and the served body's own
        # length always did: the fold restores the base's exposure and does not remove the frame's total
        self.assertEqual(b["last"]["frame"] - a["last"]["frame"], len(long["selfHost"]) - len(short["selfHost"]))

    def test_every_published_table_holds_only_the_allowlisted_rows(self):
        """The allowlist, over every fixture the module builds: the flag and count rows (FEED_BY_ROWS), the off frame's
        own lists and `other`, in the last and the lifetime tables alike (fails before: selfHost, sessions, views and
        the rest were rows)."""
        every = ([_card(i, column="working") for i in range(4)]
                 + [_card(10 + i, column="needs_input", provisional=(i == 0)) for i in range(3)]
                 + [_card(20 + i, column="completed") for i in range(3)]
                 + [_card(40 + i, sid=SID_B, column=("working", "needs_input", "completed")[i]) for i in range(3)])
        faulted = _feed(asks=every, viewsFault="tags unavailable: synthetic", off=True)
        del faulted["views"]
        odd = {"zeta": {"b": 1}, "alpha": "text", "Upper": 1, "_under": 2, "a.dot": 3}
        rogue = _feed(n=2)
        rogue.update(odd)
        bare = _feed(n=2)
        for k in list(_rest_of(bare)):
            del bare[k]
        bare.update(odd)
        with mock.patch.object(km, "_alive_sessions", lambda now, tm: []):
            off = km._feed_off_frame(NOW, {})
        frames = {"forty": _feed(n=40), "every column": _feed(asks=every), "faulted and off": faulted, "off frame": off,
                  "rogue keys": rogue, "rogue keys alone": bare, "populated": _populated(),
                  "live session": _built_with_one_live_session(self)}
        comp = km._FeedComposition()
        for name, frame in frames.items():
            last, life = self._tables(frame)
            self.assertLessEqual(set(last["by"]), PUBLIC_NAMES, "%s: last" % name)
            self.assertLessEqual(set(life["by"]), PUBLIC_NAMES, "%s: lifetime" % name)
            self.assertFalse(set(last["by"]) & km.FEED_BY_FOLDED, name)
            self.assertEqual(sum(last["by"].values()), last["rest"], name)
            _fresh_pass(frame, comp)
        life = _report(comp)["lifetime"]
        self.assertLessEqual(set(life["by"]), PUBLIC_NAMES, "every fixture on one accumulator")
        self.assertEqual(sum(life["by"].values()), life["rest"])

    def test_a_key_outside_the_checked_in_names_is_counted_under_other_and_never_stands_as_a_row(self):
        """A frame with top-level keys outside FEED_FRAME_FIELDS and _FEED_FRAME_LISTS (a session-name-shaped key, a
        forty-character identifier, keys the export's denylist drops, the odd-key set the encode identity test uses):
        none is a row of either table, their bytes are in `other`, the table sums to the remainder, the four parts are
        the same bytes as ever, and the export's fold keeps the block whole (fails before: every key rode into the table
        verbatim, and a denylisted name would have been dropped by the export, breaking the block's wholeness)."""
        odd = {"zeta": {"b": 1, "a": [3, 2, {"y": None, "x": True}]}, "alpha": "ünïcode ✓ \"quoted\" \\ back",
               "empty": {}, "none": None, "flt": 1.5, "neg": -7, "big": 10 ** 20, "lst": [], "t": True, "f": False,
               "nested": {"k2": {"z": 1, "a": 2}, "k1": ["a", {"b": 1}]}, "Upper": 1, "_under": 2, "a.dot": 3}
        rogue = dict(odd, web=["web"], since=1781100000, sid=SID)
        rogue["a" * 40] = {"n": 2}
        self.assertTrue({"t", "since", "sid"} <= pp.DENY_KEYS, "three of the keys collide with the export's denylist")
        self.assertFalse(set(rogue) & set(km._FEED_BY_NAMES), "none of the keys is a checked-in name")
        feed = _feed(n=3)
        feed.update(rogue)
        _, leds, by = _expected(feed)
        comp = km._FeedComposition()
        with mock.patch.object(km, "_FEED_COMP", comp):
            parts = km._feed_parts(feed)
        rest = _rest_of(feed)
        self.assertEqual(parts[0], {a["itemId"]: json.dumps(km._strip_trgb(a)) for a in feed["asks"]})
        self.assertEqual(parts[1], {l["sid"]: json.dumps(l) for l in feed["ledgers"]})
        self.assertEqual(parts[2], rest)
        self.assertEqual(parts[3], json.dumps(rest, sort_keys=True), "the remainder is the same bytes")
        rep = _report(comp)
        last, life = rep["last"], rep["lifetime"]
        for table in (last["by"], life["by"]):
            self.assertFalse(set(table) & set(rogue), "no rogue key is a row: %s" % sorted(set(table) & set(rogue)))
            self.assertLessEqual(set(table), PUBLIC_NAMES)
            self.assertEqual(table["other"], sum(v for k, v in by.items() if k in rogue or k in km.FEED_BY_FOLDED) + leds,
                             "the rogue keys' bytes are in `other`, beside the folded fields' and the ledgers'")
            bucketed = {}
            for k, v in by.items():
                name = k if k in km._FEED_BY_NAMES else "other"
                bucketed[name] = bucketed.get(name, 0) + v
            self.assertEqual(table, _published(bucketed, leds), "the table is the per-field sums bucketed, then folded")
        self.assertEqual(sum(last["by"].values()), last["rest"])
        self.assertEqual(last["rest"], len(parts[3]) + leds)
        self.assertEqual(comp.last["rest"], len(parts[3]))
        self.assertEqual(sum(life["by"].values()), life["rest"])
        # the projections credit an app that reads a folded field with the PUBLISHED `other`, the rogue keys' bytes
        # included (fails before: the folded fields alone, so feed.projected minus the cards and the flag rows was
        # `other` minus the rogue bytes, and the difference published them)
        flags = sum(v for k, v in last["by"].items() if k in km.FEED_BY_ROWS and k != "userTodosOn")
        self.assertEqual(last["apps"]["feed"]["projected"], last["cards"] + last["by"]["other"] + flags)
        self.assertEqual(last["apps"]["waiting"]["projected"], last["by"]["other"] + last["by"]["userTodosOn"])
        doc = {"memos": {"feedComposition": rep}}
        self.assertEqual(pp.fold(doc), doc, "the export keeps the block whole: no denied key stood as a row")
        _paste_safe(self, rep)
        # two rogue keys sum into the one row: the same frame with one of them removed loses exactly that key's bytes
        fewer = dict(feed)
        del fewer["web"]
        km._feed_cards_memo = None
        rep2 = _report(_fresh_pass(fewer))
        self.assertEqual(last["by"]["other"] - rep2["last"]["by"]["other"], by["web"])
        self.assertEqual(set(rep2["last"]["by"]), set(last["by"]))

    def test_the_fold_is_at_report_time_and_the_stored_tables_keep_a_row_per_field(self):
        """The ruling's second point, pinned directly: the accumulator's last and lifetime tables hold a row per remainder
        field (selfHost, sessions and the rest among them) after a pass, with the ledgers and the two counts stored
        apart as sums, and report() publishes each table folded by public_table (the ledgers into `rest` and `other`,
        the counts withheld); folded_sum over the stored table with the stored ledgers is the published `other`, and
        a fold moved before record() (the stored table already folded) fails here whatever it publishes."""
        frame = _populated()
        _, leds, by = _expected(frame)
        comp = _fresh_pass(frame)
        _fresh_pass(frame, comp)
        self.assertEqual(comp.last["by"], by, "the stored last table is the per-field table")
        self.assertEqual(comp.life["by"], {k: 2 * v for k, v in by.items()}, "and so is the lifetime table, summed")
        self.assertEqual(set(comp.last["by"]) & km.FEED_BY_FOLDED, km.FEED_BY_FOLDED - {"viewsFault", "ledgers"},
                         "every folded field the fixture carries has its row in the store (the fault marker rides in "
                         "place of the views blob, so a frame carries one of the two; the ledgers are a stored sum)")
        self.assertEqual((comp.last["ledgers"], comp.life["ledgers"]), (leds, 2 * leds), "the stored ledgers, apart")
        self.assertEqual((comp.last["cardCount"], comp.last["ledgerCount"]), (4, 2), "the stored counts")
        self.assertEqual((comp.life["cardCount"], comp.life["ledgerCount"]), (8, 4))
        rep = _report(comp)
        self.assertEqual(rep["last"]["by"], _published(by, leds))
        self.assertEqual(rep["lifetime"]["by"], _published({k: 2 * v for k, v in by.items()}, 2 * leds))
        self.assertEqual(rep["last"]["rest"], comp.last["rest"] + leds)
        self.assertEqual(rep["lifetime"]["rest"], comp.life["rest"] + 2 * leds)
        for table in (rep["last"], rep["lifetime"]):
            self.assertFalse({"cardCount", "ledgerCount", "ledgers"} & set(table), "withheld (fails before)")
        self.assertEqual(km._FeedComposition.folded_sum(by), _published(by)["other"])
        self.assertEqual(km._FeedComposition.folded_sum(by, leds), _published(by, leds)["other"])
        self.assertEqual(km._FeedComposition.folded_sum({}), 0)
        self.assertEqual(km._FeedComposition.folded_sum({"off": 3, "selfHost": 9, "other": 2}), 11)
        self.assertEqual(km._FeedComposition.folded_sum({"off": 3, "selfHost": 9, "other": 2}, 5), 16)
        self.assertEqual(km._FeedComposition.public_by({"off": 3, "selfHost": 9, "other": 2}), {"off": 3, "other": 11})
        self.assertEqual(km._FeedComposition.public_by({"off": 3, "selfHost": 9, "other": 2}, 5), {"off": 3, "other": 16})
        self.assertEqual(km._FeedComposition.public_by({}, 5), {"other": 5}, "ledgers on an empty table: `other` alone")
        self.assertEqual(km._FeedComposition.public_by({}), {})

    def test_the_counts_are_withheld_and_the_ledgers_folded_and_the_projections_credit_them(self):
        """Ruling (b) of the third round, on a fixture with cards in every column and two ledgers, and on the same
        fixture with the ledgers detached: the published last and lifetime tables carry frame, cards and rest and
        neither count nor a ledgers row (fails before: all three were published); the stored tables carry them; the
        published rest is the stored remainder plus the stored ledgers and `other` the folded fields plus the ledgers;
        frame == cards + rest and rest == sum(by) in both tables; every app that reads a folded field is credited with
        the ledgers (the feed row is the frame minus the switch, the Waiting-on-you row `other` plus the switch, the
        Outline's row its estimate plus `other`), and the projection row is not; and with no ledgers attached the
        published rest is the remainder alone."""
        asks = ([_card(i, column="working") for i in range(3)] + [_card(10, column="needs_input", provisional=True)]
                + [_card(20, column="completed"), _card(41, sid=SID_B, column="working")])
        feed = _feed(asks=asks)
        cards, leds, by = _expected(feed)
        comp = _fresh_pass(feed)
        rep = _report(comp)
        for name, t in (("last", rep["last"]), ("lifetime", rep["lifetime"])):
            self.assertEqual(set(t) & {"frame", "cards", "rest", "ledgers", "cardCount", "ledgerCount"},
                             set(km._FeedComposition.PUBLISHED), name)
            self.assertEqual(t["frame"], t["cards"] + t["rest"], name)
            self.assertEqual(sum(t["by"].values()), t["rest"], name)
            self.assertEqual(t["by"]["other"], sum(v for k, v in by.items() if k in km.FEED_BY_FOLDED) + leds, name)
            self.assertEqual(t["apps"]["feed"]["projected"], t["frame"] - t["by"]["userTodosOn"], name)
            self.assertEqual(t["apps"]["waiting"]["projected"], t["by"]["other"] + t["by"]["userTodosOn"], name)
            self.assertEqual(t["apps"]["fleet"]["projected"],
                             km._ask_fields_est(asks, km._FEED_APP_ASK_FIELDS["fleet"]) + t["by"]["other"], name)
            self.assertEqual(t["apps"]["phoneFace"]["projected"], km._phone_face_est(asks), name)
        self.assertEqual((comp.last["cardCount"], comp.last["ledgerCount"], comp.last["ledgers"], comp.last["rest"]),
                         (6, 2, leds, sum(by.values())), "the stored pass")
        self.assertEqual((comp.life["cardCount"], comp.life["ledgerCount"], comp.life["ledgers"]), (6, 2, leds))
        self.assertEqual(rep["last"]["rest"], comp.last["rest"] + leds)
        self.assertEqual(rep["last"]["cards"], cards)
        _paste_safe(self, rep)
        bare = dict(feed)
        del bare["ledgers"]
        comp2 = _fresh_pass(bare)
        rep2 = _report(comp2)
        self.assertEqual((comp2.last["ledgers"], comp2.last["ledgerCount"], rep2["last"]["ledgersAttached"]), (0, 0, 0))
        self.assertEqual(rep2["last"]["rest"], comp2.last["rest"], "no ledgers attached: the published rest is the remainder")
        self.assertEqual(rep2["last"]["by"]["other"], sum(v for k, v in by.items() if k in km.FEED_BY_FOLDED))
        self.assertEqual(rep["last"]["rest"] - rep2["last"]["rest"], leds)
        self.assertEqual(rep["last"]["apps"]["feed"]["projected"] - rep2["last"]["apps"]["feed"]["projected"], leds)
        self.assertEqual(rep["last"]["apps"]["phoneFace"]["projected"], rep2["last"]["apps"]["phoneFace"]["projected"])

    def test_the_invariant_is_stated_in_its_scoped_form_everywhere_and_holds_by_execution(self):
        """The invariant the block's safety is read from (fresh-1 of the second round): the universal claim, every
        published number is a sum of published rows, is false for the Outline's row, which adds its card-field
        estimate, a figure published nowhere else and not publishable as a row (on a one-card board it is that card's
        field lengths). So the claim is stated in its scoped form, FEED_COMPOSITION_INVARIANT, verbatim in the
        reference and the ledger entry, and no document, the kernel's source included, states the universal form
        without the exception (fails before: all three did). By execution, on the populated fixture and on the
        one-card board: frame, rest, every `today`, the feed row and the Waiting-on-you row are each a sum of other
        published integer leaves, and the Outline's row minus `other` and `off` is the card-field estimate and no
        published leaf."""
        inv = km.FEED_COMPOSITION_INVARIANT
        self.assertTrue(inv.startswith("Every published number is a sum of published rows, except the Outline's row"))
        ref = open(os.path.join(ROOT, "docs", "reference.md"), encoding="utf-8").read()
        para = ref[ref.index("  `feedComposition` says what the feed frame is made of"):]
        para = para[:para.index("\n- `judge`:")]
        ledger = open(os.path.join(ROOT, "upstream", "2026-09-18-feed-composition-perf.md"), encoding="utf-8").read()
        kernel = open(os.path.join(ROOT, "kernel", "kernel.py"), encoding="utf-8").read()
        k0, k1 = kernel.index("# What the block PUBLISHES of the `by` table"), kernel.index("def _feed_sig(parts):")
        for name, text in (("the reference", para), ("the ledger", ledger), ("the kernel", kernel[k0:k1])):
            flat = " ".join(text.split())
            if name != "the kernel":
                self.assertEqual(flat.count(inv), 1, "%s states the invariant in the kernel's words, once" % name)
            loose = [m.start() for m in re.finditer(r"sum of published rows(?!, except the Outline's row)", flat)]
            loose = [i for i in loose if not re.search(r"(but the Outline's row|plus, for the Outline|the Outline's plus its card-field estimate)",
                                                        flat[max(0, i - 80):i + 130])]
            self.assertEqual(loose, [], "%s: the universal claim without its exception at %r"
                             % (name, [flat[max(0, i - 60):i + 60] for i in loose]))
        for frame in (_populated(), _feed(n=1, asks=[_card(0)], ledgers=[_ledger(tops=1)])):
            rep = _report(_fresh_pass(frame))
            for t in (rep["last"], rep["lifetime"]):
                pub, apps = t["by"], t["apps"]
                flags = sum(pub[f] for f in ("dismissedCount", "showDismissed", "canUndoClear", "off") if f in pub)
                self.assertEqual(t["frame"], t["cards"] + t["rest"])
                self.assertEqual(t["rest"], sum(pub.values()))
                self.assertEqual(apps["feed"]["projected"], t["cards"] + pub["other"] + flags)
                self.assertEqual(apps["waiting"]["projected"], pub["other"] + pub["userTodosOn"])
                self.assertTrue(all(row["today"] == t["frame"] for row in apps.values()))
                est = apps["fleet"]["projected"] - pub["other"] - pub.get("off", 0)
                self.assertEqual(est, km._ask_fields_est(frame["asks"], km._FEED_APP_ASK_FIELDS["fleet"]))
                leaves = {v for p, v in _leaves(t) if isinstance(v, int) and not p.endswith("apps.fleet.projected")}
                self.assertNotIn(est, leaves, "the Outline's estimate is no published leaf: the one exception")
                self.assertNotIn(est, {a - b for a in leaves for b in leaves}, "nor a difference of two")

    def test_the_reference_and_the_ledger_state_the_published_shape_and_the_residuals(self):
        """docs/reference.md's memos.feedComposition entry and the ledger entry describe the block the kernel publishes:
        the published rows and the folded list by name (each set equal to the kernel's constant, so a reclassified
        field changes both or fails here; `ledgers` is in the folded list since the third round), the off frame's four
        lists, the report-time fold, the remainder invariant (frame == cards + rest; rest the sum of the published
        rows), the projections' one-atom rule, the withheld counts and the reason (a count beside a sum discloses the
        single-object case; the ledger count is the chat tab count, published elsewhere), and the residuals: each
        sentence of the kernel's FEED_COMPOSITION_RESIDUALS verbatim in both documents, whitespace apart, and no
        other residual count claimed. The PR body is outside the repository, so it is not read here."""
        ref = open(os.path.join(ROOT, "docs", "reference.md"), encoding="utf-8").read()
        para = ref[ref.index("  `feedComposition` says what the feed frame is made of"):]
        para = para[:para.index("\n- `judge`:")]
        ledger = open(os.path.join(ROOT, "upstream", "2026-09-18-feed-composition-perf.md"), encoding="utf-8").read()
        names = set(re.findall(r"`([A-Za-z]+)`", para))
        self.assertLessEqual(km.FEED_BY_ROWS | km.FEED_BY_FOLDED | OFF_LISTS | {"other"}, names)
        rows = re.search(r"count fields\s+\((.*?):\s+the checked-in list `FEED_BY_ROWS`", para, re.S).group(1)
        self.assertEqual(set(re.findall(r"`(\w+)`", rows)), km.FEED_BY_ROWS, "the reference's FEED_BY_ROWS list")
        folded = re.search(r"can carry a string\s+\((.*?): the checked-in list\s+`FEED_BY_FOLDED`", para, re.S).group(1)
        self.assertEqual(set(re.findall(r"`(\w+)`", folded)), km.FEED_BY_FOLDED, "the reference's FEED_BY_FOLDED list")
        self.assertIn("ledgers", km.FEED_BY_FOLDED, "the ledgers are in the fold (fails before)")
        flats = {}
        for text, phrase in (("the reference", para), ("the ledger", ledger)):
            flat = flats[text] = " ".join(phrase.split())
            for needle in ("the folded fields as one", "credited with all of `other`", "report",
                           "difference of published numbers", "hostname", "`phoneFace`", "title",
                           "withheld", "single-object case", "chat tab count", "builtChat.tabs", "Two residuals remain"):
                self.assertIn(needle, flat, "%s: %r" % (text, needle))
            for stale in ("tells the reader nothing", "forty percent under", "`cardCount`", "`ledgerCount`",
                          "three parts", "Two residuals.", "Three residuals", "minus `ledgers`"):
                self.assertNotIn(stale, flat, "%s: %r" % (text, stale))
            self.assertNotIn("\u2014", phrase, text)
            self.assertNotIn("\u2013", phrase, text)
            # the residuals, verbatim: the kernel's tuple is the arbiter, and a residual added, dropped or reworded in
            # one place fails here until the three agree
            self.assertEqual(len(km.FEED_COMPOSITION_RESIDUALS), 2, "two residuals")
            for i, sentence in enumerate(km.FEED_COMPOSITION_RESIDUALS):
                self.assertIn(sentence, flat, "%s: residual %d is not stated in the kernel's words" % (text, i + 1))
                self.assertEqual(flat.count(sentence), 1, "%s: residual %d once" % (text, i + 1))
        for sentence in km.FEED_COMPOSITION_RESIDUALS:
            self.assertNotIn("\u2014", sentence)
            self.assertNotIn("\u2013", sentence)
            self.assertTrue(sentence.endswith("."), sentence[-40:])
        for name in sorted(km.FEED_BY_ROWS | km.FEED_BY_FOLDED):
            self.assertIn(name, ledger, "the ledger names %s" % name)
        self.assertIn("`rest` is the exact sum of the published rows", flats["the reference"])
        self.assertIn("`frame` is `cards` plus `rest`", flats["the reference"])
        self.assertIn("rows drawn from a fixed list", flats["the reference"])
        self.assertIn("`other` is present on every non-empty published table", flats["the reference"])

    def test_the_perf_stats_docstring_row_names_every_key_of_the_last_pass(self):
        """The _PerfStats docstring's feedComposition row (the served snapshot's own reference) names every key of `last`
        (fails before on one word: ledgersAttached) and the published shape of `by`."""
        doc = km._PerfStats.__doc__
        # the feedComposition entry is the tail of the memos row, from its opening parenthesis to the row's end. The row is
        # cut by _doc_row, relative to its own indentation: Python 3.13 and later strip a docstring's common leading
        # whitespace at compile time, so the old lookahead on six spaces before the next row's name matched nothing on the
        # 3.13 and 3.14t CI cells
        memos = _doc_row(doc, "memos")
        i = memos.find("feedComposition (")
        self.assertNotEqual(i, -1, "the docstring has a feedComposition row")
        row = memos[i:]
        rep = _report(_fresh_pass(_feed(n=2)))
        for key in rep["last"]:
            self.assertIn(key, row, "%s: a key of `last` the row does not name" % key)
        for key in ("passes", "failed", "lifetime", "last", "wire", "bytes", "exact", "today", "projected"):
            self.assertIn(key, row, key)
        self.assertIn("FEED_BY_ROWS", row, "the row names the published rows' list")
        self.assertIn("other", row)


class AccountingGuard(unittest.TestCase):
    """(h): the card-field and projection estimates run inside their own guard. Until the review of 2026-09-18 they sat
    OUTSIDE the try that keeps an accounting fault off the frame, so a raise in an estimator propagated out of
    _feed_parts and dropped the feed send for every feed-slot client that cycle, uncounted and unsaid. Now a raise is
    counted under `failed`, said once, and memoized with the cards in the estimates' slot, so a refill of the same build
    neither re-raises nor repeats the estimates and no pass records under-counted rows; the frame goes out unchanged at
    every call site. The record-side test in SyntheticBuild proves only the recording half."""

    def setUp(self):
        km._feed_cards_memo = None

    @staticmethod
    def _raiser(asks):
        raise RuntimeError("synthetic estimator fault")

    def test_a_card_whose_sid_cannot_be_hashed_is_grouped_by_its_spelling_and_nothing_raises(self):
        """No mock: a two-card frame whose sids are a list and a dict through _feed_parts (fails before: TypeError,
        unhashable type, out of _phone_face_est's group map, propagating out of the pusher's pass). The group rows
        are keyed by str(sid), so the face estimate counts one group row per spelling; the four parts are the test's
        own encodes; nothing is counted as failed."""
        feed = _feed(n=2)
        feed["asks"][0]["sid"] = [1, 2]
        feed["asks"][1]["sid"] = {"k": "v"}
        comp = km._FeedComposition()
        with mock.patch.object(km, "_FEED_COMP", comp):
            parts = km._feed_parts(feed)
        self.assertEqual((comp.failed, comp.passes), (0, 1))
        self.assertEqual(parts[0], {a["itemId"]: json.dumps(km._strip_trgb(a)) for a in feed["asks"]})
        self.assertEqual(parts[1], {l["sid"]: json.dumps(l) for l in feed["ledgers"]})
        self.assertEqual(parts[3], json.dumps(_rest_of(feed), sort_keys=True))

        def one(card, fs):
            n = 2
            for f in fs:
                if f not in card:
                    continue
                v = card[f]
                n += len(f) + (8 + len(v) if isinstance(v, str) else 6 + len(repr(v)))
            return n
        faces = sum(one(a, km.FEED_PHONE_FACE_FIELDS) for a in feed["asks"])
        groups = one({"sid": "[1, 2]", "count": 1}, ("sid", "count")) + one({"sid": "{'k': 'v'}", "count": 1}, ("sid", "count"))
        self.assertEqual(_report(comp)["last"]["apps"]["phoneFace"]["projected"], faces + groups,
                         "a group row per spelling of the sid")
        self.assertEqual(km._phone_face_est(feed["asks"]), faces + groups)

    def _guarded(self, feed, patch):
        """A build under `patch` (an estimator that raises), then a ledgers refill of the SAME build (a memo hit), then
        a fresh build with the patch lifted; the assertions of the guard's contract at each step."""
        clean = km._feed_parts(copy.deepcopy(feed))         # the unpatched pass over a copy: the bytes to match
        km._feed_cards_memo = None
        comp = km._FeedComposition()
        err = io.StringIO()
        s0 = dict(km._wire_stats)
        with mock.patch.object(km, "_FEED_COMP", comp), patch, redirect_stderr(err):
            parts = km._feed_parts(feed)                    # fails before: the raise propagates out of _feed_parts
            self.assertEqual(parts, clean, "the four parts are byte-identical to the unpatched pass")
            self.assertEqual((comp.failed, comp.passes), (1, 0), "counted as failed, not recorded")
            self.assertEqual(err.getvalue().count("feed composition: the accounting raised"), 1, err.getvalue())
            self.assertIn("RuntimeError: synthetic estimator fault", err.getvalue())
            self.assertEqual(km._wire_stats["feed_cards_miss"] - s0["feed_cards_miss"], 1)
            self.assertIsInstance(km._feed_cards_memo[2], Exception, "the fault is memoized in the estimates' slot")
            refill = dict(feed)
            refill["ledgers"] = [_ledger(tops=1)]
            parts2 = km._feed_parts(refill)                 # the same asks list: a memo hit
            self.assertEqual(km._wire_stats["feed_cards_hit"] - s0["feed_cards_hit"], 1)
            self.assertEqual(parts2[0], clean[0])
            self.assertEqual(parts2[1], {l["sid"]: json.dumps(l) for l in refill["ledgers"]})
            self.assertEqual((comp.failed, comp.passes), (2, 0), "counted again from the memo, still not recorded")
            self.assertEqual(err.getvalue().count("feed composition"), 1, "said once")
            self.assertEqual(_report(comp)["last"], {}, "no pass was recorded")
        with mock.patch.object(km, "_FEED_COMP", comp), redirect_stderr(err):
            km._feed_cards_memo = None
            km._feed_parts(_feed(n=3, build_id=2))        # the patch lifted: a fresh build records normally
        self.assertEqual((comp.failed, comp.passes), (2, 1))
        self.assertEqual(err.getvalue().count("feed composition"), 1)
        self.assertEqual(comp.last["cardCount"], 3, "the stored pass counts the cards")
        self.assertNotIn("cardCount", _report(comp)["last"], "and the published one withholds the count")

    def test_a_raising_projection_estimator_is_counted_said_once_memoized_and_keeps_the_frame(self):
        self._guarded(_feed(n=3), mock.patch.dict(km.FEED_PROJECTIONS, {"phoneFace": self._raiser}))

    def test_a_raising_card_field_estimate_is_counted_said_once_memoized_and_keeps_the_frame(self):
        self._guarded(_feed(n=3), mock.patch.object(km, "_ask_fields_est", side_effect=RuntimeError("synthetic estimator fault")))

    def test_the_guard_covers_every_call_site_the_wire_serve_and_the_push_included(self):
        """_feed_wire_now (a `ready` or a re-base on a client-less kernel) over a cached build whose estimator raises
        returns the wire tuple (fails before: the raise propagated out of it), and the real _push hands a feed-slot
        client the frame while the fault is counted."""
        feed = _feed(n=2)
        comp = km._FeedComposition()
        err = io.StringIO()
        saved = list(km._built_feed)
        with mock.patch.object(km, "_FEED_COMP", comp), mock.patch.dict(km.FEED_PROJECTIONS, {"phoneFace": self._raiser}), \
                mock.patch.object(km, "_feed_wire", None), redirect_stderr(err):
            km._built_feed[:] = [None, feed, 0.0, 0.0]
            try:
                w = km._feed_wire_now()
            finally:
                km._built_feed[:] = saved
            self.assertIsNotNone(w)
            self.assertIs(w[0], feed)
            self.assertEqual(w[5][3], json.dumps(_rest_of(feed), sort_keys=True))
            self.assertEqual((comp.failed, comp.passes), (1, 0))
            km._feed_cards_memo = None
            received = _drive_push(self, ("feed", "waiting"), feed)
        self.assertEqual({app for app, types in received.items() if "feed" in types}, {"feed", "waiting"},
                         "the feed-slot clients receive the frame while the estimates fault")
        self.assertGreaterEqual(comp.failed, 2)
        self.assertEqual(comp.passes, 0)
        self.assertEqual(err.getvalue().count("feed composition: the accounting raised"), 1)

    def test_the_estimates_run_once_per_build_and_not_on_a_refill(self):
        """The memoization claim, by counting (tests-2): the card-field estimate and the projection estimator are
        wrapped, a build runs each at least once (bounded loosely: the face estimate calls the card-field estimate
        twice itself), and a ledgers refill of the same build runs neither; a refill after a FAULTED build runs neither
        either, the fault being memoized too. Fails under the mutation that drops the estimates from the memo."""
        feed = _feed(n=6)
        real_est, real_face = km._ask_fields_est, km.FEED_PROJECTIONS["phoneFace"]
        est_calls, face_calls = [], []

        def est(asks, fields):
            est_calls.append(fields)
            return real_est(asks, fields)

        def face(asks):
            face_calls.append(1)
            return real_face(asks)
        apps_with_fields = len(km._FEED_APP_ASK_FIELDS)
        with mock.patch.object(km, "_ask_fields_est", est), mock.patch.dict(km.FEED_PROJECTIONS, {"phoneFace": face}):
            km._feed_cards_memo = None
            s0 = dict(km._wire_stats)
            km._feed_parts(feed)
            n_est, n_face = len(est_calls), len(face_calls)
            self.assertGreaterEqual(n_est, apps_with_fields, "at least one card-field pass per app that reads card fields")
            self.assertLessEqual(n_est, 4 * apps_with_fields + 4)
            self.assertGreaterEqual(n_face, 1)
            self.assertLessEqual(n_face, 4)
            for tops in (1, 5):
                km._feed_parts(dict(feed, ledgers=[_ledger(tops=tops)]))
            self.assertEqual(km._wire_stats["feed_cards_hit"] - s0["feed_cards_hit"], 2)
            self.assertEqual((len(est_calls), len(face_calls)), (n_est, n_face), "a refill runs no estimate")
        # a faulted build: the estimates ran (and raised); the refill runs none of them again
        del est_calls[:], face_calls[:]
        comp = km._FeedComposition()
        err = io.StringIO()
        with mock.patch.object(km, "_FEED_COMP", comp), mock.patch.object(km, "_ask_fields_est", est), \
                mock.patch.dict(km.FEED_PROJECTIONS, {"phoneFace": self._raiser}), redirect_stderr(err):
            km._feed_cards_memo = None
            km._feed_parts(feed)
            n_est = len(est_calls)
            self.assertGreaterEqual(n_est, 1)
            km._feed_parts(dict(feed, ledgers=[_ledger(tops=2)]))
            self.assertEqual(len(est_calls), n_est, "a refill after a faulted build repeats no estimate")
        self.assertEqual((comp.failed, comp.passes), (2, 0))


if __name__ == "__main__":
    unittest.main()
