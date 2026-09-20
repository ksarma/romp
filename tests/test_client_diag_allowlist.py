#!/usr/bin/env python3
"""The clientDiag handler admits each surface's known top-level data keys and bounds the row (2026-09-18, the beacon
extension). The file used to take whatever a page posted, of any shape and size. Now: a key outside the surface's
allowlist (CLIENT_DIAG_KEYS) is dropped and said once on stderr per surface and key; a data that is not an object is
stored as null; every string value is cut at CLIENT_DIAG_STR_MAX characters at any depth; a row whose JSON runs past
CLIENT_DIAG_ROW_MAX bytes keeps its surface, what and app and carries {"capped": true, "bytes": N, "app": ...} as its
data, except a perf minute row, which sheds CLIENT_DIAG_MINUTE_SHED's keys in order (the uncapped wsBytesByHost map first
and whole, then its per-minute figures) until it fits and names them under `capped`, so the once-per-page nav, res, marks
and env survive; the bound is derived from the collector's own caps, so the row it builds at every cap at once is stored
whole while its wsBytesByHost map is under the crossing the ladder test derives, and past it the map alone is shed; the
surface and what strings are cut too, once; the
stderr latch is bounded at CLIENT_DIAG_SAID_MAX pairs and one row can have at most CLIENT_DIAG_ROW_SAY_MAX of its keys
said; and a page's row under the kernel's own surface is refused. Today's rows (the collector's minute and slowframe,
the shim's return, close and stale rows) pass whole, so the desktop readers keep every key they depend on, and one
fixture row per call site of every bundle and shell poster ties the table to what the posters send.

Drives the REAL Handler's WS dispatch (_dispatch_ws with a clientDiag message, the way the pane shim delivers one)
against a hermetic state directory. Synthetic fixtures only: a placeholder dashboard id, invented numbers."""
import contextlib
import io
import json
import os
import pathlib
import re
import tempfile
import unittest
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
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
km = load_source("romp_kernel_cdiag_allow", os.path.join(BIN, "romp-kernel"))

WID = "11111111-2222-3333-4444-555555555555"
UI = os.path.join(os.path.dirname(HERE), "ui", "webview")

# a minute row as ui/webview/perf-telemetry.ts builds it today (perf-telemetry.test.ts pins the same keys)
MINUTE = {"app": "chat", "since": 1700000000000, "span_ms": 60000,
          "frames": {"session": {"n": 12, "ms_sum": 340.5, "ms_max": 88.1, "n16": 5, "n100": 0, "hist": [0] * 14}},
          "free": {"n": 3, "p50": 12.5, "p90": 40, "max": 41.2},
          "loaf": {"n": 1, "blocking_ms": 60, "worst_ms": 110, "top": [{"k": "render.js:paintAll@9000", "ms": 90, "n": 1, "inv": "WebSocket.onmessage"}], "src": "loaf"},
          "slow": {"sent": 1, "suppressed": 0, "suppressed_worst_ms": 0},
          "dom": 53306, "visible": True, "hidden_pane": False, "ua": "safari-ios", "heap_mb": 210.4}
# the shared fields the same row carries when the gear's share switch is on
SHARED = {"nav": {"type": "reload", "responseEnd": 210, "domContentLoaded": 656, "loadEventEnd": 0},
          "res": {"feed.js": {"transferSize": 120000, "encodedBodySize": 119700, "duration": 88}, "other": {"transferSize": 600, "encodedBodySize": 400, "duration": 45}},
          "marks": {"wsOpen": 121, "bundleReady": 300, "firstFrame": 455, "fp": 388, "fcp": 402},
          "env": {"standalone": True, "iosMajor": 17, "touch": True, "vw": 390, "vh": 664, "dpr": 3, "entryTypes": ["paint", "resource", "navigation"], "ric": False, "dv": 1757100000},
          "vis": {"hiddenN": 1, "visibleN": 1, "hiddenMs": 30000}, "wsBytes": 12345, "rafGap": {"n": 2, "worst": 120},
          # wsBytesByHost (2026-09-19, the user's approval: the bytes each attached host sent, one number per host, no content):
          # the same unit per REMOTE host by its position on the page, h1 the first remote host it attached; positions, never names
          "wsBytesByHost": {"h1": 40123, "h2": 991}}

# The content census (review round 1 of the wsBytesByHost change, 2026-09-20). Every admitted key of every surface, classified by
# what its VALUE can carry as the first-party posters and the kernel's own writers build it: BARE (a host name as the value),
# PREFIXED (a session id with its host in front, <host>:<uuid>, when the row concerns a remote session), KEYED (a map whose keys
# are host names), NONE (why it cannot carry one, and where a shape holds it, who holds it: the collector, the poster or the
# kernel). A census keyed on the NAME `host` had missed the chat surface, whose sid, id, ids and active are the tab ids the page
# holds, which federation.ts prefixes for every remote session (prefixInbound on SCALAR_ID and ARRAY_ID, the tab records through
# OBJ_ID); the cut at CLIENT_DIAG_STR_MAX keeps the head of a string, prefix included. The kernel admits a surface's top-level
# keys and cuts nested string values; it inspects no nested key and no value's form, so every class here names the writer that
# holds the shape. test_every_admitted_key_is_classified_by_the_content_its_value_can_carry ties this table to CLIENT_DIAG_KEYS
# both ways, so a key added to the table without a row here fails, and the disclosure copies are read back against the
# host-carrying surfaces this table derives (test_the_disclosure_copies_state_the_content_rule_and_name_every_host_carrying_surface).
BARE, PREFIXED, KEYED, NONE = "bare", "prefixed", "keyed", "none"
_ENUM, _INT, _BOOL = "a fixed word", "a number", "a boolean"
CENSUS = {
    "perf": {   # perf-telemetry.ts: the minute and slowframe rows; every key's shape is the collector's
        "app": (NONE, "the pane word the collector is created with"), "since": (NONE, _INT), "span_ms": (NONE, _INT),
        "frames": (NONE, "keys: classifyFrame's type, an identifier of at most 32 characters or the fold word; values: counts"),
        "free": (NONE, "percentiles"), "loaf": (NONE, "top[].k is scriptKey's basename form, top[].inv is sanitizeInvoker's, which strips an element id and reduces a URL to its basename; src a fixed word"),
        "slow": (NONE, "counts"), "dom": (NONE, _INT), "visible": (NONE, _BOOL), "hidden_pane": (NONE, _BOOL),
        "ua": (NONE, "uaClass's fixed word"), "heap_mb": (NONE, _INT), "type": (NONE, "the slow frame's classified type"), "ms": (NONE, _INT),
        "nav": (NONE, "fixed keys, type from NAV_TYPES or other, whole ms"),
        "res": (NONE, "keys: resourceKey's same-origin /dist/ or /media/ basename, a root file name or other, so a cross-origin URL folds"),
        "marks": (NONE, "fixed keys, whole ms"), "env": (NONE, "fixed keys; entryTypes from a fixed list; dv a number"),
        "vis": (NONE, "counts"), "wsBytes": (NONE, _INT), "rafGap": (NONE, "counts"),
        "wsBytesByHost": (NONE, "keys h<ordinal>: the collector's bytesByHost keeps a key only on ^h[1-9][0-9]*$ and federation.ts mints them as 'h' plus the attach ordinal; values: characters; the kernel admits the key and does not inspect the map's keys"),
    },
    "pane-shim": {   # kernel.py's pane shim: staleDiag, returnDiag, the wsclose, wsconnfail and page-load rows
        "app": (NONE, "the pane word"), "why": (NONE, "a stale cause word"), "ready": (NONE, _INT), "quietMs": (NONE, _INT), "hidden": (NONE, _BOOL),
        "decision": (NONE, _ENUM), "resumed": (NONE, _BOOL), "hiddenMs": (NONE, _INT), "frozenMs": (NONE, _INT), "quietAtResumeMs": (NONE, _INT),
        "resent": (NONE, _BOOL), "ms": (NONE, _INT), "bytesSince": (NONE, _INT), "redialed": (NONE, _BOOL), "code": (NONE, "the close code"),
        "reason": (NONE, "the close frame's reason text: this kernel sends no close frame (a drop reads 1006), so empty, or an intermediary's text, cut"),
        "wasClean": (NONE, _BOOL), "sinceOpenMs": (NONE, _INT), "everConnected": (NONE, _BOOL), "bundleReady": (NONE, _BOOL),
        "attempts": (NONE, _INT), "firstFailMs": (NONE, _INT), "wasDiscarded": (NONE, _BOOL), "nav": (NONE, "the navigation type word"),
        "awaitLink": (NONE, _BOOL), "linkUpMs": (NONE, _INT), "parked": (NONE, _BOOL),
    },
    "reload-core": {"reason": (NONE, "build or fresh"), "detail": (NONE, "the offered dist token or code, a number's text"), "hold": (NONE, "the hold word"), "ageMs": (NONE, _INT)},
    "shell": {   # kernel.py's shell scripts: the push panel's rows, the tap ledger rows, the return probe
        "sidAttached": (NONE, _BOOL),
        "host": (BARE, "push-test: the active tab's host, read off the tab id's prefix (activeSession), empty for a local session"),
        "why": (NONE, "activeSession's cause word"), "tabs": (NONE, _INT), "status": (NONE, "an HTTP status or ok"), "via": (NONE, _ENUM), "boot": (NONE, _BOOL),
        "hasSid": (NONE, _BOOL), "hasCard": (NONE, _BOOL), "hasPid": (NONE, _BOOL), "controlled": (NONE, _BOOL), "dup": (NONE, _BOOL), "sub": (NONE, _BOOL),
        "rows": (NONE, _INT), "err": (NONE, "true when GET /push/pending failed; the row carries no text"), "getNotifications": (NONE, _BOOL),
        "displayed": (NONE, _INT), "vanished": (NONE, _INT), "superseded": (NONE, _INT),
        "sid8": (NONE, "the first 8 characters of a push ledger row's sid, a bare uuid: _push_pending carries the host in its own field, which the row does not copy"),
        "ageS": (NONE, _INT), "shape": (NONE, _ENUM), "kind": (NONE, "the worker message's kind word"), "sw": (NONE, _BOOL), "decision": (NONE, _ENUM),
        "hiddenMs": (NONE, _INT), "quietMs": (NONE, _INT), "attempts": (NONE, _INT), "firstFailMs": (NONE, _INT), "ms": (NONE, _INT),
    },
    "federation": {   # federation.ts diag(): hostconn, feedDelta-nobase, feedDelta-stale, feedmerge, sendqueue, senddrop
        "host": (BARE, "the conn's host on every hostconn, feedDelta-nobase, feedDelta-stale, sendqueue and senddrop row (federation_host_row_kinds, "
                       "derived from federation.ts); empty on the poll rows, local on the local nobase row"),
        "ev": (NONE, "the hostconn event word"),
        "why": (NONE, "a cause word, a slot name, the remote's build id, or the page's own /tunnels fetch failure text cut at 200"),
        "quietMs": (NONE, _INT), "foreground": (NONE, _BOOL), "msgType": (NONE, "a message type word"), "rs": (NONE, "a readyState"),
        "flushed": (NONE, "message type words"), "held": (NONE, "message type words"), "unread": (NONE, _BOOL), "endedUnread": (NONE, _BOOL),
        "code": (NONE, "the close code"), "clean": (NONE, _BOOL), "detached": (NONE, _BOOL), "pendingDropped": (NONE, "message type words or a count"),
        "buildId": (NONE, "the remote kernel's build id"),
        "counts": (KEYED, "feedmerge: the merged feed's ask count per host, keyed by the host name (local for the local kernel)"),
        "gt": (NONE, _INT), "superseded": (NONE, _BOOL),
    },
    "chat": {   # render.ts's direct posts and scroll-write.ts's rows through scrollDiagRow
        "sid": (PREFIXED, "the active tab's id or the session's id: <host>:<uuid> for a remote session (send, cancel-miss, reconcile-optimistic-failed, every scroll row)"),
        "error": (NONE, "a caught exception's message, cut at 200 by the poster and 64 here"), "held": (NONE, _INT), "got": (NONE, _INT), "distVer": (NONE, _INT),
        "path": (NONE, "location.pathname, the page's own route"), "mdLen": (NONE, _INT), "queuedLeft": (NONE, _INT),
        "ids": (PREFIXED, "live-omitted-kept: tab ids the kernel still affirms live, prefixed for remote sessions"),
        "n": (NONE, _INT),
        "active": (PREFIXED, "skeleton: the active tab's id, prefixed for a remote session"),
        "ts": (NONE, _INT), "len": (NONE, _INT), "route": (NONE, "plain, quote or followup"),
        "id": (PREFIXED, "empty-session-frame: the frame's session id, prefixed by prefixInbound for a remote session"),
        "load": (NONE, "the federation.js resource entry's figures"), "first": (NONE, "the earlier pass's load figures or a boolean"),
        "recovered": (NONE, _BOOL), "hadRestore": (NONE, _BOOL), "perMinute": (NONE, _INT), "writer": (NONE, "the writing function's name"),
        "before": (NONE, _INT), "after": (NONE, _INT), "delta": (NONE, _INT), "stick": (NONE, _BOOL), "gesture": (NONE, _BOOL), "sh": (NONE, _INT), "ch": (NONE, _INT),
        "anchor": (NONE, "the last 12 characters of an atom uuid"), "proto": (NONE, _INT), "events": (NONE, _INT), "regions": (NONE, _BOOL),
        "headKnown": (NONE, _BOOL), "headFrom": (NONE, _ENUM), "older": (NONE, _BOOL), "noframe": (NONE, _BOOL), "trail": (NONE, _INT),
        "dh": (NONE, _INT), "last": (NONE, "the tail element's class list or live-ask"), "cls": (NONE, "an element's class name"), "fromTail": (NONE, _INT),
        "atBottom": (NONE, _BOOL), "where": (NONE, "view or live-ask"), "removed": (NONE, "element class names"), "added": (NONE, "element class names"),
        "reAdded": (NONE, _BOOL), "shBefore": (NONE, _INT), "shAfter": (NONE, _INT), "st": (NONE, _INT), "top": (NONE, _INT), "bot": (NONE, _INT),
        "dTop": (NONE, _INT), "dBot": (NONE, _INT), "lo": (NONE, _INT), "hi": (NONE, _INT), "edge": (NONE, "top or bottom"), "why": (NONE, "scroll or land"),
        "notice": (NONE, _BOOL), "nav": (NONE, "the navigation type word"), "kind": (NONE, "the region kind word"), "keep": (NONE, _INT), "reland": (NONE, _BOOL),
    },
    "strip": {   # strip.ts: the host popover's fetch and toggle rows
        "ok": (NONE, _BOOL), "tunnels": (NONE, _INT), "err": (NONE, "the page's own /tunnels fetch failure as String(err), cut"), "open": (NONE, _BOOL),
        "base": (NONE, "empty on a kernel page; in the VS Code webview the extension's kernel URL, http://127.0.0.1:<port> (extension.ts HOST is the loopback literal), a URL with no host name"),
    },
    "feed": {   # feed.ts: colflip, itemset, feedDelta-unapplied
        "id": (NONE, "an item id, <bare sid>:g<n>: prefixInbound prefixes a row's sid and not its item ids"), "from": (NONE, "a column word"), "to": (NONE, "a column word"),
        "ev": (NONE, "the input change word"), "buildId": (NONE, _INT), "predicted": (NONE, _BOOL),
        "appeared": (NONE, "item ids, the bare-sid form"), "gone": (NONE, "item ids, the bare-sid form"), "total": (NONE, _INT),
    },
    "outline": {"buildId": (NONE, _INT), "slot": (NONE, "a slot word"), "rev": (NONE, _INT)},
    "waiting": {"buildId": (NONE, _INT)},
    "kernel": {   # the kernel's four direct writers: _note_ws_open, _note_history_reply, _note_chat_withheld_at_close, _implicit_handshake
        "app": (NONE, "the dial's app word"), "kind": (NONE, "page, relay or hub"), "reconnect": (NONE, _BOOL), "iid": (NONE, "a boolean: whether the dial stated one"),
        "cid": (NONE, "a minted hex id"),
        "host": (BARE, "wsopen, kind hub: the host a spliced /remote/<host>/ws upgrade was relayed to (_note_ws_open, from the hub's splice)"),
        "sid": (NONE, "the session id a history ask named: a page asks for its local sessions bare, and the relay strips a remote id's host before forwarding (federation.ts stripHost)"),
        "type": (NONE, "the ask's type word"), "span": (NONE, "turn numbers"), "events": (NONE, _INT), "bytes": (NONE, _INT), "head": (NONE, _BOOL),
        "missing": (NONE, _BOOL), "refused": (NONE, _BOOL),
        "reason": (NONE, "the fault text the kernel minted for a refused history reply (no build to answer from, or an exception's class and text)"),
        "sent": (NONE, _BOOL), "frames": (NONE, _INT), "ageS": (NONE, _INT), "frame": (NONE, "a WS_OPS word or other"), "withheld": (NONE, _INT), "proto": (NONE, _INT),
    },
}


def host_carrying_keys():
    """The census's host-carrying keys by surface, {surface: {key: class}}, derived from the rows whose class is not NONE."""
    out = {}
    for surface, table in CENSUS.items():
        keys = {k: c for k, (c, _why) in table.items() if c != NONE}
        if keys:
            out[surface] = keys
    return out


def federation_host_row_kinds():
    """The federation row kinds that carry the conn's host, derived from federation.ts: every `this.diag("<what>", ...)` call
    whose data literal names `host` on the call's line (the literal's first key at every site today). The disclosure copies
    name each kind (round 1, 2026-09-20: the copies said "hostconn rows" where the census reason said every hostconn,
    feedDelta and send row); a new host-carrying row kind fails the pin until the copies name it."""
    src = open(os.path.join(os.path.dirname(HERE), "ui", "webview", "federation.ts"), encoding="utf-8").read()
    return set(re.findall(r'this\.diag\("([\w-]+)",[^\n{]*\{[^\n}]*\bhost\b', src))


def disclosure_copies():
    """The three disclosure copies in the tree, each as its text or None when the anchors are gone: the wsBytesByHost entry's
    comment in kernel.py (from the entry to the next surface), the minute-row entry's wsBytesByHost passage in docs/reference.md
    (from the field's sentence to rafGap's) and the ledger entry's body (after its front matter)."""
    root = os.path.dirname(HERE)
    ksrc = open(os.path.join(root, "kernel", "kernel.py"), encoding="utf-8").read()
    k = re.search(r'"wsBytesByHost"\)\),(.*?)"pane-shim": frozenset\(', ksrc, re.S)
    dsrc = open(os.path.join(root, "docs", "reference.md"), encoding="utf-8").read()
    d = re.search(r"`wsBytesByHost` is the same\n(.*?)`rafGap` is\n", dsrc, re.S)
    lsrc = open(os.path.join(root, "upstream", "2026-09-19-relay-dial-page-caps-ws-bytes-by-host.md"), encoding="utf-8").read()
    l = re.search(r"^---\n.*?\n---\n(.*)", lsrc, re.S)
    def flat(m):
        # one line per copy: the comment markers and the doc's wrapping are not part of the claim
        return re.sub(r"\s+", " ", re.sub(r"\n\s*#", " ", m.group(1))).strip() if m else None
    return {"kernel": flat(k), "docs": flat(d), "ledger": flat(l)}


class ClientDiagAllowlistTest(unittest.TestCase):
    def setUp(self):
        # A private state root (T282): km.jd is the judge module every test module shares, and its STATE is whatever
        # the last module left. A minted state root pins per-session hosts off (the repo rule of 2026-09-11).
        self._saved_state = km.jd.STATE
        self._td = tempfile.TemporaryDirectory()
        root = pathlib.Path(self._td.name)
        (root / "session-hosts").write_text("off\n", encoding="utf-8")
        km.jd._rebind_state(root)
        self.fp = km.jd.STATE / "client-diag.jsonl"
        km._client_diag_said.clear()    # the once-per-kernel stderr latch: each test is its own kernel

    def tearDown(self):
        km._client_diag_said.clear()
        km.jd._rebind_state(self._saved_state)
        self._td.cleanup()

    def post(self, surface, what, data):
        """One row through the real dispatch, the way a pane's shim delivers it; returns what the kernel said on stderr."""
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km.Handler._dispatch_ws(None, {"type": "clientDiag", "surface": surface, "what": what, "data": data}, {"wid": WID})
        return err.getvalue()

    def rows(self):
        return [json.loads(line) for line in self.fp.read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_the_constants_and_the_table(self):
        self.assertEqual(km.CLIENT_DIAG_STR_MAX, 64)
        self.assertEqual(km.CLIENT_DIAG_ROW_MAX, 24 * 1024, "above the collector's worst case (test_the_collectors_worst_case_minute_row_is_stored_whole)")
        self.assertEqual(sorted(km.CLIENT_DIAG_KEYS), ["chat", "federation", "feed", "kernel", "outline", "pane-shim", "perf", "reload-core", "shell", "strip", "waiting"])
        for surface, keys in km.CLIENT_DIAG_KEYS.items():
            self.assertIsInstance(keys, frozenset, surface)
            self.assertTrue(all(isinstance(k, str) and k for k in keys), surface)
        self.assertTrue(set(MINUTE) <= km.CLIENT_DIAG_KEYS["perf"], "every key of today's minute row is admitted")
        self.assertTrue(set(SHARED) <= km.CLIENT_DIAG_KEYS["perf"], "and every shared field")
        self.assertTrue({"app", "type", "ms", "dom", "loaf"} <= km.CLIENT_DIAG_KEYS["perf"], "the slowframe row's keys")
        self.assertEqual(km.CLIENT_DIAG_MINUTE_SHED, ("wsBytesByHost", "frames", "loaf", "free", "slow"),
                         "the uncapped map first and whole, then the per-minute figures largest first (the ladder test)")
        self.assertTrue(set(km.CLIENT_DIAG_MINUTE_SHED) <= km.CLIENT_DIAG_KEYS["perf"])
        self.assertEqual(km.CLIENT_DIAG_SAID_MAX, 512)
        self.assertEqual(km.CLIENT_DIAG_ROW_SAY_MAX, 8, "the foreign keys of one row said by name; the rest are counted in one line")

    def test_todays_rows_pass_whole_and_quietly(self):
        err = self.post("perf", "minute", MINUTE)
        err += self.post("perf", "slowframe", {"app": "chat", "type": "session", "ms": 150.2, "dom": 53306, "loaf": {"ms": 160, "blocking_ms": 110, "top": []}})
        err += self.post("pane-shim", "wsclose", {"app": "feed", "code": 1006, "reason": "", "wasClean": False, "sinceOpenMs": 5000, "quietMs": 31000, "everConnected": True, "bundleReady": True})
        err += self.post("pane-shim", "return", {"decision": "redial-closed", "resumed": False, "hiddenMs": 29000, "frozenMs": 0, "quietMs": 29500, "quietAtResumeMs": -1, "ready": 3, "app": "chat", "resent": True})
        err += self.post("pane-shim", "return-fresh", {"ms": 5600, "bytesSince": 40000, "redialed": True, "app": "chat"})
        err += self.post("pane-shim", "wsconnfail", {"app": "chat", "attempts": 3, "firstFailMs": 30000})
        err += self.post("pane-shim", "page-load", {"wasDiscarded": True, "nav": "reload", "app": "feed"})
        err += self.post("pane-shim", "watchdog-close", {"app": "feed", "why": "quiet", "ready": 1, "quietMs": 31000, "hidden": False})
        err += self.post("reload-core", "held", {"reason": "fresh", "detail": "", "hold": "fresh", "ageMs": 61000})
        self.assertEqual(err, "", "nothing dropped, nothing said")
        rows = self.rows()
        self.assertEqual(len(rows), 9)
        self.assertEqual(sorted(rows[0]), ["data", "reconnect", "surface", "t", "what", "wid"], "the row's own shape is unchanged")
        self.assertEqual(rows[0]["data"], MINUTE)
        self.assertEqual(rows[2]["data"]["reason"], "")
        self.assertEqual(rows[3]["data"]["resent"], True)

    def test_the_shell_led_return_keys_pass_whole(self):
        # D3 (2026-09-18): the pane's return awaits the shell's link (return.awaitLink) and its return-fresh carries
        # the path's own recovery (return-fresh.linkUpMs); the shell socket's return-probe is a fixed-shape row.
        err = self.post("pane-shim", "return", {"decision": "redial-closed", "resumed": False, "hiddenMs": 195000,
                                                 "frozenMs": 0, "quietMs": 195500, "quietAtResumeMs": -1, "ready": 3,
                                                 "app": "chat", "awaitLink": True})
        err += self.post("pane-shim", "return-fresh", {"ms": 1200, "bytesSince": 40000, "redialed": True,
                                                       "linkUpMs": 900, "app": "chat"})
        err += self.post("shell", "return-probe", {"decision": "redial-closed", "hiddenMs": 195000, "quietMs": 195500,
                                                   "attempts": 2, "firstFailMs": 12500, "ms": 33000})
        self.assertEqual(err, "", "the D3 keys are admitted whole (awaitLink, linkUpMs, and the shell return-probe)")
        rows = self.rows()
        self.assertIs(rows[-3]["data"]["awaitLink"], True)
        self.assertEqual(rows[-2]["data"]["linkUpMs"], 900)
        self.assertEqual(rows[-1]["data"]["decision"], "redial-closed")

    def test_the_parked_return_keys_pass_whole(self):
        # D2 (2026-09-18): a pane off screen on the phone parks its return redial (return.parked, true; false on a return
        # that did not park in a shell that told a word) and the return-fresh that answers its tap says so too
        # (return-fresh.parked, beside D3's linkUpMs). A bool, approved field by field; the one key this change adds.
        err = self.post("pane-shim", "return", {"decision": "redial-closed", "resumed": False, "hiddenMs": 181000,
                                                 "frozenMs": 0, "quietMs": 181500, "quietAtResumeMs": -1, "ready": 3,
                                                 "app": "files", "parked": True})
        err += self.post("pane-shim", "return-fresh", {"ms": 800, "bytesSince": 240000, "redialed": True,
                                                       "linkUpMs": 0, "parked": True, "app": "files"})
        err += self.post("pane-shim", "return", {"decision": "redial-closed", "resumed": False, "hiddenMs": 181000,
                                                 "frozenMs": 0, "quietMs": 181500, "quietAtResumeMs": -1, "ready": 3,
                                                 "app": "chat", "awaitLink": True, "parked": False})
        self.assertEqual(err, "", "the parked key is admitted whole on the return and return-fresh rows")
        rows = self.rows()
        self.assertIs(rows[-3]["data"]["parked"], True)
        self.assertIs(rows[-2]["data"]["parked"], True)
        self.assertEqual(rows[-2]["data"]["linkUpMs"], 0)
        self.assertIs(rows[-1]["data"]["parked"], False)
        self.assertIn("parked", km.CLIENT_DIAG_KEYS["pane-shim"])
        for surface in ("shell", "federation", "chat", "perf", "reload-core"):
            self.assertNotIn("parked", km.CLIENT_DIAG_KEYS[surface], "the key is the pane-shim surface's alone")

    def test_every_surface_in_the_table_admits_every_key_it_names(self):
        for surface, keys in sorted(km.CLIENT_DIAG_KEYS.items()):
            data = {k: i for i, k in enumerate(sorted(keys))}
            if surface == "kernel":
                # the kernel's own surface: the handler refuses a page's row under it (the test below), so the entry is
                # checked at the admit step alone; it names the keys the kernel's own writers use
                self.assertEqual(km._client_diag_admit(surface, data), data)
                continue
            err = self.post(surface, "probe", data)
            self.assertEqual(err, "", surface)
            self.assertEqual(self.rows()[-1]["data"], data, surface)

    def test_the_shared_fields_pass_and_an_unknown_key_is_dropped_and_said_once(self):
        data = dict(MINUTE, **SHARED)
        data["typed"] = "what the user wrote"
        data["sid"] = "11111111-2222-3333-4444-555555555555"
        err = self.post("perf", "minute", data)
        row = self.rows()[0]["data"]
        self.assertEqual(row, dict(MINUTE, **SHARED), "the admitted keys, the shared fields among them; the two foreign keys gone")
        lines = [l for l in err.splitlines() if l]
        self.assertEqual(len(lines), 2, err)
        self.assertTrue(any("'typed'" in l and "'perf'" in l for l in lines), err)
        self.assertTrue(any("'sid'" in l for l in lines), err)
        self.assertTrue(all(l.startswith("[client-diag] dropping a key the surface's allowlist does not admit") for l in lines), err)
        # the same keys again, from another minute: said already
        self.assertEqual(self.post("perf", "minute", data), "")
        # a different foreign key: its own line, once
        self.assertEqual(len(self.post("perf", "minute", dict(MINUTE, other_thing=1)).splitlines()), 1)
        self.assertEqual(self.post("perf", "minute", dict(MINUTE, other_thing=2)), "")
        self.assertEqual(len(self.rows()), 4)

    def test_strings_are_cut_at_the_cap_at_any_depth(self):
        long = "x" * 200
        self.post("pane-shim", "wsclose", {"app": "feed", "code": 1006, "reason": long, "wasClean": False, "sinceOpenMs": 1, "quietMs": 1, "everConnected": True, "bundleReady": True})
        row = self.rows()[-1]["data"]
        self.assertEqual(row["reason"], "x" * 64)
        self.assertEqual(row["code"], 1006)
        self.assertIs(row["wasClean"], False)
        nested = dict(MINUTE, loaf={"n": 1, "blocking_ms": 1, "worst_ms": 1, "src": "loaf",
                                    "top": [{"k": "a" * 100, "ms": 1, "n": 1, "inv": "b" * 70}]})
        self.post("perf", "minute", nested)
        top = self.rows()[-1]["data"]["loaf"]["top"][0]
        self.assertEqual(top["k"], "a" * 64)
        self.assertEqual(top["inv"], "b" * 64)
        self.assertEqual(top["ms"], 1)
        # the dict's own keys are not values and stay whole (the row cap bounds them); null stays null
        self.post("perf", "minute", dict(MINUTE, frames={"k" * 70: {"n": 1}}, free=None))
        d = self.rows()[-1]["data"]
        self.assertEqual(list(d["frames"]), ["k" * 70])
        self.assertIsNone(d["free"])

    def test_nesting_past_the_depth_cap_reads_null(self):
        deep = 1
        for _ in range(20):
            deep = [deep]
        self.post("perf", "minute", dict(MINUTE, frames=deep))
        v = self.rows()[-1]["data"]["frames"]
        depth = 0
        while isinstance(v, list):
            v = v[0]
            depth += 1
        self.assertIsNone(v)
        self.assertEqual(depth, km.CLIENT_DIAG_DEPTH_MAX, "lists at depths 0 to the cap less one, then null")

    def test_a_row_over_the_cap_is_stored_capped_with_its_surface_and_what_and_said_once(self):
        # a slowframe row whose long-frame report grew past the cap, a shape the collector never builds (its top is five
        # entries): the marker is the backstop for a row no first-party poster sends (the minute row has its own rule, below)
        big = {"app": "chat", "type": "session", "ms": 150.2, "dom": 53306,
               "loaf": {"ms": 160, "blocking_ms": 110, "top": [{"k": "render.js:paint%03d@9000" % i, "ms": 1, "n": 1, "inv": "WebSocket.onmessage"} for i in range(400)]}}
        self.assertGreater(len(json.dumps(big)), km.CLIENT_DIAG_ROW_MAX)
        err = self.post("perf", "slowframe", big)
        self.assertEqual(len(err.splitlines()), 1, err)
        self.assertIn("is stored capped", err)
        row = self.rows()[-1]
        self.assertEqual(row["surface"], "perf")
        self.assertEqual(row["what"], "slowframe")
        self.assertEqual(row["wid"], WID)
        self.assertIn("reconnect", row)
        self.assertEqual(sorted(row["data"]), ["app", "bytes", "capped"], "the marker keeps the pane, so the row still groups under it (review find, 2026-09-18)")
        self.assertEqual(row["data"]["app"], "chat")
        self.assertIs(row["data"]["capped"], True)
        self.assertGreater(row["data"]["bytes"], km.CLIENT_DIAG_ROW_MAX)
        self.assertLess(len(json.dumps(row)), 400, "the stored row is small")
        self.assertEqual(self.post("perf", "slowframe", big), "", "said once per surface and what")
        self.assertEqual(len(self.post("perf", "probe", big).splitlines()), 1, "another what: its own line")
        # a row with no string app takes the bare marker
        self.post("pane-shim", "probe", {"code": [1] * 20000, "app": 7})
        self.assertEqual(sorted(self.rows()[-1]["data"]), ["bytes", "capped"], "app is kept only where the poster sent a string")
        # a row just under the cap passes whole: frame types added until one more would not fit
        env = {"t": 1700000000, "wid": WID, "surface": "perf", "what": "minute", "reconnect": False}
        frames = {}
        while True:
            more = dict(frames, **{"type%03d" % len(frames): {"n": len(frames), "hist": [0] * 14}})
            if len(json.dumps(dict(env, data=dict(MINUTE, frames=more)))) > km.CLIENT_DIAG_ROW_MAX:
                break
            frames = more
        near = dict(MINUTE, frames=frames)
        line = json.dumps(dict(env, data=near))
        self.assertLess(len(line), km.CLIENT_DIAG_ROW_MAX)
        self.assertGreater(len(line), km.CLIENT_DIAG_ROW_MAX - 100, "within one frame entry of the bound")
        self.assertEqual(self.post("perf", "minute", near), "")
        self.assertEqual(self.rows()[-1]["data"], near)

    def test_a_minute_row_over_the_cap_sheds_its_frames_and_keeps_the_once_per_page_fields(self):
        # a first shared minute over the bound: the row the whole-row marker used to swallow, and with it nav, res, marks
        # and env for the page's life, since the collector sends them once (review find, 2026-09-18). The bound now sits
        # above the collector's own worst case (the test below), so this shape (260 frame types) is one no collector
        # builds; the shed is the backstop. Under pressure the ladder sheds the uncapped map first whatever the cause (the
        # ladder test), so this row's two-position map goes before its frames
        frames = {("fed:" if i % 2 else "") + "type%03d" % i: {"n": 12 + i, "ms_sum": 340.5 + i, "ms_max": 88.1, "n16": 5, "n100": 1, "hist": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]} for i in range(260)}
        res = {"bundle%02d.js" % i: {"transferSize": 120000 + i, "encodedBodySize": 119700 + i, "duration": 88 + i} for i in range(24)}
        res["other"] = {"transferSize": 600, "encodedBodySize": 400, "duration": 45}   # MAX_RES named entries and the fold, as the collector builds it
        shared = dict(SHARED, res=res)
        data = dict(MINUTE, frames=frames, **shared)
        line = json.dumps({"t": 1700000000, "wid": WID, "surface": "perf", "what": "minute", "reconnect": False, "data": data})
        self.assertGreater(len(line), km.CLIENT_DIAG_ROW_MAX, "the fixture is over the cap as posted")
        err = self.post("perf", "minute", data)
        row = self.rows()[-1]
        d = row["data"]
        self.assertNotIn("frames", d, "the largest per-minute figure is shed")
        self.assertNotIn("wsBytesByHost", d, "the uncapped map is shed first, whatever took the row over")
        self.assertEqual(d["capped"], {"bytes": len(line), "dropped": ["wsBytesByHost", "frames"]}, "the marker names what was shed, in ladder order, and the line's bytes before")
        for k in ("nav", "res", "marks", "env"):
            self.assertEqual(d[k], shared[k], k)
        for k in ("app", "since", "span_ms", "dom", "visible", "hidden_pane", "ua", "heap_mb", "vis", "wsBytes", "rafGap", "loaf", "free", "slow"):
            self.assertEqual(d[k], data[k], "%s stays: the shed stops once the line fits" % k)
        self.assertLessEqual(len(json.dumps(row)), km.CLIENT_DIAG_ROW_MAX)
        self.assertEqual(len(err.splitlines()), 1, err)
        self.assertIn("stored without some of its per-minute figures", err)
        self.assertEqual(self.post("perf", "minute", data), "", "said once per surface and what")
        # a minute whose long-frame report is big too: frames goes first, then loaf; free, slow and the shared fields stay
        loaf = {"n": 320, "blocking_ms": 900, "worst_ms": 200, "src": "loaf",
                "top": [{"k": "render.js:paint%03d@9000" % i, "ms": 90, "n": 1, "inv": "WebSocket.onmessage"} for i in range(320)]}
        self.post("perf", "minute", dict(MINUTE, frames=frames, loaf=loaf, **shared))
        d = self.rows()[-1]["data"]
        self.assertEqual(d["capped"]["dropped"], ["wsBytesByHost", "frames", "loaf"])
        self.assertNotIn("loaf", d)
        self.assertEqual(d["free"], MINUTE["free"])
        self.assertEqual(d["slow"], MINUTE["slow"])
        self.assertEqual(d["res"], res)
        self.assertLessEqual(len(json.dumps(self.rows()[-1])), km.CLIENT_DIAG_ROW_MAX)
        # a minute row that does not fit even without all four (a resource fold no collector builds) takes the whole-row marker
        wide = {"asset%03d.js" % i: {"transferSize": 100000 + i, "encodedBodySize": 99000 + i, "duration": 88} for i in range(400)}
        err = self.post("perf", "minute", dict(MINUTE, **dict(SHARED, res=wide)))
        d = self.rows()[-1]["data"]
        self.assertEqual(sorted(d), ["app", "bytes", "capped"])
        self.assertEqual(d["app"], "chat")
        self.assertIs(d["capped"], True)
        self.assertIn("is stored capped", err)
        # the shed is the minute row's alone: a slowframe row over the cap takes the marker whole (the test above)

    def test_a_long_surface_is_cut_once_for_the_row_the_lookup_and_the_stderr_line(self):
        # before the fix the allowlist lookup and the latch read the uncut string: a 200-character surface was printed whole
        # via %r, and every distinct spelling grew the latch (review find, 2026-09-18)
        err = self.post("s" * 200, "probe", {"a": 1})
        row = self.rows()[-1]
        self.assertEqual(row["surface"], "s" * 64)
        self.assertEqual(row["data"], {})
        lines = err.splitlines()
        self.assertEqual(len(lines), 1, err)
        self.assertIn("'%s'" % ("s" * 64), lines[0])
        self.assertNotIn("s" * 65, lines[0], "the stderr line carries the cut surface, never the 200 characters")
        self.assertIn(("s" * 64, "key 'a'"), km._client_diag_said, "the latch holds the cut surface")
        self.assertEqual(self.post("s" * 300, "probe", {"a": 2}), "", "another long spelling of the same 64 characters is the same latch entry")
        self.assertEqual(len(km._client_diag_said), 1)
        # a surface that is not a string reads as its str(), cut the same way
        err = self.post({"k": "v" * 200}, "probe", {"a": 1})
        self.assertEqual(self.rows()[-1]["surface"], str({"k": "v" * 200})[:64])
        self.assertLess(max(len(l) for l in err.splitlines()), 200)

    def test_one_row_with_many_foreign_keys_has_a_handful_said_and_the_rest_counted(self):
        # one row with 600 foreign keys used to print 513 lines and spend the whole latch, so every other surface was
        # silent for the kernel's life (review find, 2026-09-18); now a row has at most CLIENT_DIAG_ROW_SAY_MAX of its keys
        # said by name and one line counting the rest, every key still dropped
        n = km.CLIENT_DIAG_ROW_SAY_MAX
        foreign = {"zz%03d" % i: i for i in range(600)}
        err = self.post("perf", "minute", dict(MINUTE, **foreign))
        lines = err.splitlines()
        self.assertEqual(len(lines), n + 1, err)
        for i in range(n):
            self.assertIn("key 'zz%03d'" % i, lines[i], "the row's first keys, in its order")
            self.assertIn("dropping a key the surface's allowlist does not admit", lines[i])
        self.assertIn("and %d more keys dropped from one row, unnamed" % (600 - n), lines[-1])
        self.assertEqual(len(km._client_diag_said), n + 1, "the named keys and the counting line: a handful of the latch, not all of it")
        self.assertEqual(self.rows()[-1]["data"], MINUTE, "every foreign key is dropped regardless")
        # a second surface still says (the line the old pin held silent)
        self.assertEqual(len(self.post("mystery", "probe", {"q": 1}).splitlines()), 1, "one wide row did not spend the latch")
        # another wide row on the same surface: its first keys are new and are named; the counting line is said once per surface
        more = {"yy%03d" % i: i for i in range(100)}
        lines = self.post("perf", "minute", dict(MINUTE, **more)).splitlines()
        self.assertEqual(len(lines), n, lines)
        self.assertTrue(all("key 'yy" in l for l in lines), lines)
        # the same wide row again: every named key is latched, the counting line too
        self.assertEqual(self.post("perf", "minute", dict(MINUTE, **more)), "")
        # the same bound on a surface no allowlist names
        lines = self.post("nowhere", "probe", {"k%03d" % i: i for i in range(50)}).splitlines()
        self.assertEqual(len(lines), n + 1, lines)
        self.assertTrue(all("a surface no allowlist names" in l for l in lines[:-1]), lines)
        self.assertIn("and %d more keys" % (50 - n), lines[-1])

    def test_the_stderr_latch_is_bounded_and_says_so_once(self):
        # a flood of distinct pairs across rows: the latch holds CLIENT_DIAG_SAID_MAX, one closing line, then silence
        for i in range(600):
            err = self.post("perf", "minute", dict(MINUTE, **{"zz%03d" % i: i}))
            if i < km.CLIENT_DIAG_SAID_MAX:
                self.assertEqual(len(err.splitlines()), 1, (i, err))
                self.assertIn("dropping a key", err)
            elif i == km.CLIENT_DIAG_SAID_MAX:
                self.assertEqual(len(err.splitlines()), 1, (i, err))
                self.assertIn("nothing more is said", err)
            else:
                self.assertEqual(err, "", (i, err))
        self.assertEqual(len(km._client_diag_said), km.CLIENT_DIAG_SAID_MAX + 1, "the pairs and the latch's own entry")
        self.assertEqual(len(self.rows()), 600, "every row lands regardless")
        self.assertEqual(self.rows()[-1]["data"], MINUTE)
        # more foreign keys, another surface, a capped row: nothing more is said and the latch does not grow
        self.assertEqual(self.post("perf", "minute", dict(MINUTE, another=1)), "")
        self.assertEqual(self.post("mystery", "probe", {"q": 1}), "")
        big = {"app": "chat", "type": "x", "ms": 1, "loaf": {"top": [{"k": "render.js:paint%03d@9000" % i, "ms": 1, "n": 1, "inv": "WebSocket.onmessage"} for i in range(400)]}}
        self.assertGreater(len(json.dumps(big)), km.CLIENT_DIAG_ROW_MAX)
        self.assertEqual(self.post("perf", "slowframe", big), "")
        self.assertEqual(sorted(self.rows()[-1]["data"]), ["app", "bytes", "capped"], "the cap still applies, unsaid")
        self.assertEqual(len(km._client_diag_said), km.CLIENT_DIAG_SAID_MAX + 1)

    def test_a_page_row_under_the_kernels_surface_is_refused_and_said_once(self):
        # the table admitted surface kernel from a page, so a forged wsopen landed indistinguishable from the kernel's own
        # rows (_note_ws_open and its siblings write those directly, never through the handler); the handler now refuses
        # it, said once per what (review find, 2026-09-18). The table keeps the entry: it names the kernel's own keys.
        forged = {"app": "chat", "kind": "page", "iid": "forged", "reconnect": False}
        err = self.post("kernel", "wsopen", forged)
        self.assertFalse(self.fp.exists(), "no row: the file is not even created")
        lines = err.splitlines()
        self.assertEqual(len(lines), 1, err)
        self.assertIn("refusing a page's row under the kernel's own surface", lines[0])
        self.assertIn("surface 'kernel', what 'wsopen'", lines[0])
        self.assertEqual(self.post("kernel", "wsopen", forged), "", "said once per what")
        self.assertEqual(len(self.post("kernel", "historyReply", {"sid": "11111111-2222-3333-4444-555555555555"}).splitlines()), 1, "another what: its own line")
        self.assertFalse(self.fp.exists())
        self.assertIn("kernel", km.CLIENT_DIAG_KEYS, "the entry stays for the kernel's own rows")
        # a surface that merely begins with the word is another surface: unknown, so it keeps no key and lands
        self.post("kernel-ish", "wsopen", forged)
        self.assertEqual((self.rows()[-1]["surface"], self.rows()[-1]["data"]), ("kernel-ish", {}))

    def test_the_collectors_key_lists_are_admitted_by_the_perf_entry(self):
        # the collector's executed row is pinned against TODAY_KEYS and SHARED_KEYS in ui/webview/perf-telemetry.test.ts,
        # and the table here against hand-written fixtures; nothing tied the two, so a key the collector grows or renames
        # kept both suites green while the kernel dropped it from the file (review find, 2026-09-18). Parsed by regex, the way
        # tests/test_perf_stats.py reads perf-telemetry.ts; a subset, not equality: the perf entry is a union that also
        # carries the slowframe row's type and ms.
        ts = open(os.path.join(UI, "perf-telemetry.test.ts"), encoding="utf-8").read()
        lists = {}
        for name in ("TODAY_KEYS", "SHARED_KEYS"):
            m = re.search(r'^const %s = (\[[^\]]*\]);$' % name, ts, re.M)
            self.assertIsNotNone(m, "perf-telemetry.test.ts no longer declares %s on one line: re-aim this parse" % name)
            lists[name] = json.loads(m.group(1))
            self.assertTrue(lists[name] and all(isinstance(k, str) for k in lists[name]), name)
        table = km.CLIENT_DIAG_KEYS["perf"]
        for name, keys in lists.items():
            missing = sorted(set(keys) - table)
            self.assertEqual(missing, [], "%s in perf-telemetry.test.ts names %s, which CLIENT_DIAG_KEYS['perf'] does not admit: "
                                          "add the key to the table, or take it out of the collector and its list" % (name, missing))
        self.assertEqual(sorted(lists["TODAY_KEYS"]), sorted(MINUTE), "this module's MINUTE fixture is the same list")
        self.assertEqual(sorted(lists["SHARED_KEYS"]), sorted(SHARED), "and SHARED the same")

    def _worst_case_row(self):
        """The minute row the collector would send with every cap reached at once and eight attached hosts, built from the
        constants as perf-telemetry.ts declares them: (minute, shared, env, consts), `minute` the share-off row, `shared` the
        fields the share switch adds (wsBytesByHost among them at HOSTS positions of nine-digit counts), `env` the kernel's
        envelope and `consts` the collector's constants read. Shared by the worst-case row test and the ladder test."""
        src = open(os.path.join(UI, "perf-telemetry.ts"), encoding="utf-8").read()
        def const(name):
            m = re.search(r"^export const %s(?:: [^=]+)? = ([^;]+);" % name, src, re.M)
            self.assertIsNotNone(m, name)
            return m.group(1)
        max_types = int(const("MAX_FRAME_TYPES")); max_top = int(const("MAX_TOP")); free_ring = int(const("FREE_RING"))
        slow_rows = int(const("SLOW_ROWS_PER_MINUTE")); max_res = int(const("MAX_RES"))
        buckets = len(json.loads(const("HIST_EDGES"))) + 1
        ident_cap = int(re.search(r"\^\[A-Za-z0-9_\.:-\]\{1,(\d+)\}\$", src).group(1))    # ident(): a frame type at most this long
        self.assertEqual((max_types, max_top, free_ring, slow_rows, max_res, buckets, ident_cap), (32, 5, 64, 5, 24, 14, 32), "the constants this derivation was made with")
        entry_types = json.loads(re.search(r"^export const ENV_ENTRY_TYPES: readonly string\[\] = (\[[^\]]*\]);", src, re.M).group(1))
        big = 999999                                         # six-digit counts: more than a minute of frames at 60 Hz can hold
        ms = 60000.0                                         # one-decimal ms, a whole minute
        st = {"n": big, "ms_sum": ms, "ms_max": ms, "n16": big, "n100": big, "hist": [big] * buckets}
        frames = {}
        for i in range(max_types + 1):                       # the named types and the fold ("other" / "fed:other") are max_types + 1 keys each
            frames["delta:" + "w" * (ident_cap - 6) + "%06d" % i] = dict(st)      # the longest prefix (a raw delta by slot) and an identifier at the cap
            frames["fed:delta:" + "f" * (ident_cap - 6) + "%06d" % i] = dict(st)   # the federation layer's key for the same frame: fed: plus the classified type
        self.assertEqual(len(frames), 2 * (max_types + 1))
        self.assertEqual(max(len(k) for k in frames if not k.startswith("fed:")), 38, "a wire key is at most delta: plus the identifier cap")
        self.assertEqual(max(len(k) for k in frames), 42, "the longest key the collector emits is fed:delta: plus the identifier cap")
        top = [{"k": "k" * km.CLIENT_DIAG_STR_MAX, "ms": ms, "n": big, "inv": "i" * km.CLIENT_DIAG_STR_MAX} for _ in range(max_top)]
        minute = {"app": "timeline", "since": 1700000000000, "span_ms": 600000, "frames": frames,
                  "free": {"n": free_ring, "p50": ms, "p90": ms, "max": ms},
                  "loaf": {"n": big, "blocking_ms": 600000.0, "worst_ms": ms, "top": top, "src": "longtask"},
                  "slow": {"sent": slow_rows, "suppressed": big, "suppressed_worst_ms": ms},
                  "dom": 9999999, "visible": False, "hidden_pane": False, "ua": "chrome-desktop", "heap_mb": 99999.9}
        res = {"r" * 20 + "%03d.woff2" % i: {"transferSize": 99999999, "encodedBodySize": 99999999, "duration": ms} for i in range(max_res)}
        res["other"] = {"transferSize": 99999999, "encodedBodySize": 99999999, "duration": ms}
        # wsBytesByHost at its widest (2026-09-19): the field has no cap (one key per attached host, the owner's decision), so the
        # row states a count rather than reading one. Eight is twice the four an earlier cut capped at and more than any lab or
        # deployment attaches to one page (the labs' widest is two); each further host adds about 17 bytes to the row; a row
        # budget, if one is ever needed, is the owner's question through the design.
        HOSTS = 8
        by_host = {"h%d" % i: 999999999 for i in range(1, HOSTS + 1)}
        self.assertEqual(len(by_host), HOSTS, "one key per stated host, no fold key")
        shared = {"nav": {"type": "back_forward", "responseEnd": big, "domContentLoaded": big, "loadEventEnd": big}, "res": res,
                  "marks": {"wsOpen": big, "bundleReady": big, "firstFrame": big, "fp": big, "fcp": big},
                  "env": {"standalone": True, "iosMajor": 17, "touch": True, "vw": 99999, "vh": 99999, "dpr": 3.5, "entryTypes": entry_types, "ric": True, "dv": 1757100000000},
                  "vis": {"hiddenN": big, "visibleN": big, "hiddenMs": 99999999}, "wsBytes": 999999999, "rafGap": {"n": big, "worst": big},
                  "wsBytesByHost": by_host}
        env = {"t": 1700000000, "wid": WID, "surface": "perf", "what": "minute", "reconnect": False}
        return minute, shared, env, {"max_types": max_types, "hosts": HOSTS}

    def test_the_collectors_worst_case_minute_row_is_stored_whole(self):
        # CLIENT_DIAG_ROW_MAX sat at 8 KiB, below the collector's own worst case, so a share-off minute with 28 or more frame
        # types lost its frames where main stored it whole, and the shared row lost more (review find, 2026-09-18: 16481 B
        # share off, 19110 B share on, measured). The bound is now derived from the collector's caps; this builds the row
        # the collector would send with every cap reached at once, from the constants as perf-telemetry.ts declares them,
        # and asserts it lands whole, no shed, no marker, nothing said. A 16 KiB bound would still have shed it. The fed:
        # keys are spelled in their longest form, fed:delta: plus the 32-character identifier, 42 characters: federation.ts
        # times a frame as fed: plus classifyFrame(msg), which reads delta: plus the identifier for a delta frame. This test
        # first spelled them fed: plus the identifier, 36 characters, and the row it proved whole was 198 B under the row
        # the collector can build (review find, round 2, 2026-09-18). The one key with no cap, wsBytesByHost, is built at
        # the eight positions the derivation states; the ladder test below takes it past the bound.
        minute, shared, env, c = self._worst_case_row()
        max_types, HOSTS, by_host = c["max_types"], c["hosts"], shared["wsBytesByHost"]
        off, on = len(json.dumps(dict(env, data=minute))), len(json.dumps(dict(env, data=dict(minute, **shared))))
        self.assertGreater(off, 16 * 1024, "the share-off worst case is over 16 KiB, so the old 8 KiB bound shed its frames")
        self.assertLess(on, km.CLIENT_DIAG_ROW_MAX, "the share-on worst case fits under the bound (%d of %d bytes)" % (on, km.CLIENT_DIAG_ROW_MAX))
        # The row bound's derivation comment in kernel.py states this map's count, the bytes it adds to the row and the share-on
        # figure. Until the peer read of 2026-09-19 those were hand-kept copies of HOSTS with nothing tying them to the row built
        # here: a raised HOSTS left the comment claiming a margin this test no longer measured, and nothing went red. Read back
        # from the comment and compared to the row, so a change to HOSTS, or to any figure the row is made of, re-derives the
        # comment too. Derived reads: a comment the pattern no longer finds fails here rather than passing on nothing.
        ksrc = open(os.path.join(os.path.dirname(HERE), "kernel", "kernel.py"), encoding="utf-8").read()
        stated = re.search(r"the worst-case row test states (\w+) at nine digits each, (\d+) bytes", ksrc)
        self.assertIsNotNone(stated, "kernel.py's CLIENT_DIAG_ROW_MAX derivation no longer states the widest wsBytesByHost map: re-aim this read")
        words = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve")
        self.assertLess(HOSTS, len(words), "state HOSTS as a count word this read knows, or extend the tuple")
        self.assertEqual(stated.group(1), words[HOSTS], "the derivation's count word is the HOSTS this test states")
        without = len(json.dumps(dict(env, data=dict(minute, **{k: v for k, v in shared.items() if k != "wsBytesByHost"}))))
        self.assertEqual(int(stated.group(2)), on - without, "the derivation's byte figure is what the map adds to the row, its key and separator included")
        share_on = re.findall(r"\((\d+\.\d) KB(?: share on\)|; the derivation above\))", ksrc)
        self.assertEqual(len(share_on), 2, "the derivation and CLIENT_DIAG_ROW_MAX's own comment each state the share-on figure once")
        self.assertEqual(set(share_on), {"%.1f" % (on / 1000)}, "both share-on figures are this row's size in KB (%d bytes)" % on)
        # docs/reference.md states the same two figures for the same derivation, in its own phrasing: a third copy, which this
        # change moved in kernel.py and the body and left at the old figure in the docs (review round 1, 2026-09-20). Its own
        # pattern, whitespace-flattened (the doc wraps), and a not-None guard before the comparison, so a rephrased doc fails
        # here rather than passing on nothing; the assumed host count is read back too, since "every cap reached at once" is
        # not a bound on the one key that has no cap
        dsrc = re.sub(r"\s+", " ", open(os.path.join(os.path.dirname(HERE), "docs", "reference.md"), encoding="utf-8").read())
        doc = re.search(r"is about (\d+\.\d) KB with share off and (\d+\.\d) KB with share on\)", dsrc)
        self.assertIsNotNone(doc, "docs/reference.md no longer states the two worst-case figures: re-aim this read")
        self.assertEqual(doc.groups(), ("%.1f" % (off / 1000), "%.1f" % (on / 1000)), "the docs' figures are this row's (%d and %d bytes)" % (off, on))
        count = re.search(r"every cap reached at once and (\w+) attached hosts", dsrc)
        self.assertIsNotNone(count, "docs/reference.md no longer states the assumed host count beside the figures: re-aim this read")
        self.assertEqual(count.group(1), words[HOSTS], "the docs' host count word is the HOSTS this test states")
        for data in (minute, dict(minute, **shared)):
            self.assertEqual(self.post("perf", "minute", data), "", "nothing shed, nothing said")
            row = self.rows()[-1]
            self.assertEqual(row["data"], data, "stored whole")
            self.assertNotIn("capped", row["data"])
            self.assertEqual(len(row["data"]["frames"]), 2 * (max_types + 1), "every frame type intact")
        self.assertEqual(self.rows()[-1]["data"]["wsBytesByHost"], by_host, "the per-host map lands whole: the admit filters top-level keys only, the scrub walks it")

    def test_a_wide_wsBytesByHost_map_is_shed_whole_as_the_ladders_first_step_and_the_rest_of_the_row_is_stored_as_posted(self):
        # wsBytesByHost is the one key of the minute row the collector does not cap (one position per attached host, the owner's
        # decision), so it is the one key that can take a row the collector builds past CLIENT_DIAG_ROW_MAX. Before round 1 of
        # its review (2026-09-20) the ladder shed the frame histograms first and kept the map that caused the overflow, and past
        # a second crossing the whole row: a wide map lost exactly what the shed protects. Now the map is the ladder's first
        # step, shed WHOLE and named under capped (never truncated to the positions that fit, so a stored map is never read as a
        # host count), and shedding it returns the row to the derived worst case, which fits: the frames and the once-per-page
        # fields stay, however wide the map. The crossing and the per-position cost are DERIVED here from the row this test
        # builds and read back against the kernel's comment, so a moved figure or a reshaped row goes red rather than leaving
        # the comment claiming a crossing the row no longer has.
        minute, shared, env, c = self._worst_case_row()
        def with_hosts(n):
            return dict(minute, **dict(shared, wsBytesByHost={"h%d" % i: 999999999 for i in range(1, n + 1)}))
        def size(n):
            return len(json.dumps(dict(env, data=with_hosts(n))))
        n = c["hosts"]
        self.assertLessEqual(size(n), km.CLIENT_DIAG_ROW_MAX, "the stated worst case fits (the test above)")
        while size(n) <= km.CLIENT_DIAG_ROW_MAX:
            n += 1
            self.assertLess(n, 100000, "no crossing found: the map never takes the row over the bound?")
        crossing = n
        self.assertGreater(crossing, c["hosts"], "derived: the first position count whose row is over the bound")
        for count in (crossing, crossing + 1, 2000):
            data = with_hosts(count)
            line = json.dumps(dict(env, data=data))
            self.assertGreater(len(line), km.CLIENT_DIAG_ROW_MAX, count)
            km._client_diag_said.clear()
            err = self.post("perf", "minute", data)
            row = self.rows()[-1]
            d = row["data"]
            self.assertNotIn("wsBytesByHost", d, "%d positions: the map is shed whole, never stored truncated" % count)
            self.assertEqual(d["capped"], {"bytes": len(line), "dropped": ["wsBytesByHost"]}, "%d positions: the one step, recorded" % count)
            self.assertEqual(len(d["frames"]), 2 * (c["max_types"] + 1), "%d positions: every frame type intact" % count)
            for k, v in data.items():
                if k != "wsBytesByHost":
                    self.assertEqual(d[k], v, "%d positions: %s stored as posted" % (count, k))
            self.assertLessEqual(len(json.dumps(row)), km.CLIENT_DIAG_ROW_MAX)
            self.assertEqual(len(err.splitlines()), 1, err)
            self.assertIn("stored without some of its per-minute figures", err, "the shed's existing stderr line fires, once")
        data = with_hosts(crossing - 1)
        self.assertEqual(self.post("perf", "minute", data), "", "one position under the crossing: nothing shed, nothing said")
        self.assertEqual(self.rows()[-1]["data"], data, "stored whole, the map at %d positions included" % (crossing - 1))
        # the per-position cost by the ordinal's digit width (the separator, the quoted key and a nine-digit count), derived
        per = (size(9) - size(8), size(10) - size(9), size(100) - size(99))
        self.assertTrue(all(b > 0 for b in per), per)
        ksrc = open(os.path.join(os.path.dirname(HERE), "kernel", "kernel.py"), encoding="utf-8").read()
        ksrc = re.sub(r"\s+", " ", re.sub(r"\n\s*#", " ", ksrc))   # the comment's wrapping is not part of the claim
        rule = re.search(r"each further position adds (\d+) bytes at a one-digit ordinal, (\d+) at two and (\d+) at three", ksrc, re.I)
        self.assertIsNotNone(rule, "kernel.py's derivation no longer states the per-position rule: re-aim this read")
        self.assertEqual(tuple(int(x) for x in rule.groups()), per, "the derivation's per-position figures are this row's")
        cross = re.search(r"the map crosses the bound at (\d+) positions", ksrc)
        self.assertIsNotNone(cross, "kernel.py's derivation no longer states the crossing: re-aim this read")
        self.assertEqual(int(cross.group(1)), crossing, "the derivation's crossing is the one this row derives")
        margin = re.search(r"leaves (\d+) bytes under the bound", ksrc)
        self.assertIsNotNone(margin, "kernel.py's derivation no longer states the margin: re-aim this read")
        self.assertEqual(int(margin.group(1)), km.CLIENT_DIAG_ROW_MAX - size(c["hosts"]), "the stated margin is the bound less the stated worst case")

    def test_every_admitted_key_is_classified_by_the_content_its_value_can_carry(self):
        # The census (CENSUS, above) against the table, both ways per surface: a key the table admits with no row here fails, as
        # does a row here for a key the table no longer admits, so a surface cannot grow a key without a reader deciding what its
        # value can carry. The host-carrying surfaces are DERIVED from the rows' classes, never listed by hand, and the derivation
        # must not come out empty: the file carries host names today (the shell's and federation's `host`, the kernel's wsopen row,
        # federation's counts, the chat surface's prefixed session ids), and a census that found none would be reading nothing.
        self.assertEqual(sorted(CENSUS), sorted(km.CLIENT_DIAG_KEYS), "every surface of the table is classified and no other")
        for surface, table in sorted(CENSUS.items()):
            self.assertEqual(sorted(table), sorted(km.CLIENT_DIAG_KEYS[surface]),
                             "%s: every admitted key has a classification and every classified key is admitted" % surface)
            for key, (cls, why) in sorted(table.items()):
                self.assertIn(cls, (BARE, PREFIXED, KEYED, NONE), (surface, key))
                self.assertTrue(isinstance(why, str) and why, "%s.%s: a class names its reason" % (surface, key))
        carrying = host_carrying_keys()
        self.assertTrue(carrying, "the derivation found no host-carrying key: the census is reading nothing")
        self.assertEqual(carrying, {"chat": {"active": PREFIXED, "id": PREFIXED, "ids": PREFIXED, "sid": PREFIXED},
                                    "federation": {"counts": KEYED, "host": BARE}, "kernel": {"host": BARE}, "shell": {"host": BARE}},
                         "the host-carrying keys and their forms, as derived; a change here is a change to the disclosure copies")
        # the prefixed form lands as posted: the head of a string survives the cut, host and all (a 64-character cut of
        # <host>:<uuid> keeps the whole id for a host name of up to 27 characters and the host for any longer one)
        sid = "TESTHOST:11111111-2222-3333-4444-555555555555"
        self.assertEqual(self.post("chat", "send", {"sid": sid, "ts": 1700000000000, "len": 3, "route": "plain"}), "")
        self.assertEqual(self.rows()[-1]["data"]["sid"], sid)
        long_host = "h" * 80
        self.post("chat", "skeleton", {"n": 1, "active": long_host + ":" + sid.split(":")[1]})
        self.assertEqual(self.rows()[-1]["data"]["active"], long_host[:km.CLIENT_DIAG_STR_MAX])

    def test_the_disclosure_copies_state_the_content_rule_and_name_every_host_carrying_surface(self):
        # The disclosure is stated three times in the tree (the wsBytesByHost entry's comment in kernel.py, the minute-row entry
        # in docs/reference.md, the ledger entry) and once in the PR body outside it. Its first version enumerated the surfaces
        # that name a `host` KEY and missed the chat surface, whose values carry a host inside a session id (round 1, 2026-09-20).
        # Each copy must now state the rule (a value can carry a host name bare under a host key, as a host-prefixed session id
        # when the row concerns a remote session, or as a host-keyed map), name the chat road's condition and its independence
        # from the share switch, and name every host-carrying surface the census derives; a copy that drops a clause fails here.
        # The tokens are the rule's terms and the clauses the round asked for (the chat road's age, its frequency and its use, the
        # map clause, the registries' stamp); a copy's other sentences are not read here.
        copies = disclosure_copies()
        self.assertEqual(sorted(copies), ["docs", "kernel", "ledger"])
        for name, text in sorted(copies.items()):
            self.assertIsNotNone(text, "%s: the disclosure copy was not found: re-aim disclosure_copies()" % name)
            self.assertGreater(len(text), 200, name)
            for token in (r"host-prefixed session id", r"host-keyed map", r"remote session", r"share switch", r"`?host`? key", r"positions and no host name",
                          r"several positions for one machine",   # the per-document grain's consequence (round 3, fresh-2)
                          r"GET /tunnels", r"in (its|their) own right",
                          r"remotes\.json", r"remotes-known\.json", r"lastAttachedAt", r"exact for", r"order inference",
                          r"no page-life correlation", r"attached-host order",   # the fourth road's whole statement (round 3, extra8-1)
                          r"older than", r"most frequent", r"routine use", r"not from chat rows alone",
                          r"\bmints\b", r"does not inspect the map's keys", r"nested key"):
                self.assertIsNotNone(re.search(token, text, re.I), "%s: the disclosure no longer states %r" % (name, token))
        # the bare-name example is derived, not hand-kept: every federation row kind that carries the conn's host, read from
        # federation.ts's diag call sites, is named by every copy (round 1, 2026-09-20: the copies named hostconn alone)
        kinds = federation_host_row_kinds()
        self.assertEqual(kinds, {"hostconn", "feedDelta-nobase", "feedDelta-stale", "sendqueue", "senddrop"},
                         "the federation row kinds carrying a host, as derived; a change here is a change to the disclosure copies")
        for name, text in sorted(copies.items()):
            for kind in sorted(kinds):
                self.assertIsNotNone(re.search(r"\b%s\b" % re.escape(kind), text), "%s: the disclosure does not name federation's %s rows" % (name, kind))
        # the stability caveat lives where the position rule is stated for readers, the docs and the ledger (and the PR body outside
        # the tree): a reload re-derives the assignment from the same /tunnels order, so the caveat must carry its condition, never
        # read as a de-linking property (round 1, correctness-2; the ledger's copy since the round's own read)
        for name in ("docs", "ledger"):
            for token in (r"names the same one again", r"dialable rows", r"first poll", r"attach and detach history", r"rotation"):
                self.assertIsNotNone(re.search(token, copies[name], re.I), "%s: the reload sentence no longer states %r" % (name, token))
        named = {"chat": r"\bchat\b", "federation": r"\bfederation\b", "shell": r"\bshell\b", "kernel": r"\bwsopen\b"}
        carrying = host_carrying_keys()
        self.assertTrue(carrying)
        for surface in sorted(carrying):
            self.assertIn(surface, named, "a new host-carrying surface: say how each disclosure copy names it")
            for name, text in sorted(copies.items()):
                self.assertIsNotNone(re.search(named[surface], text), "%s: the disclosure does not name the %s surface" % (name, surface))

    def test_one_fixture_row_per_poster_call_site_passes_whole_and_the_table_names_nothing_else(self):
        """The table against the posters: one synthetic row per clientDiag call site in the bundles (render.ts and
        scroll-write.ts, federation.ts, feed.ts, fleet.ts, waiting.ts, strip.ts) and the shell scripts in kernel.py, with the
        keys each posts. Every row passes whole with no stderr line, and per surface the fixtures' keys are exactly the
        table's, so a poster that grows a key without the table, or a table key no poster sends, fails here. The perf,
        pane-shim and reload-core rows are test_todays_rows_pass_whole_and_quietly's."""
        sid = "TESTHOST:11111111-2222-3333-4444-555555555555"   # a REMOTE session's tab id as the page holds it, host-prefixed (the census, CENSUS)
        host = "TESTHOST"
        posters = {
            "chat": [   # render.ts's direct posts, then scrollDiagRow's kinds (scroll-write.ts builds the rows)
                ("reconcile-optimistic-failed", {"sid": sid, "error": "gone"}),
                ("views-stale-blob", {"held": 3, "got": 1}),
                ("pageload", {"distVer": 1757100000, "path": "/chat"}),
                ("cancel-provisional", {"mdLen": 12, "queuedLeft": 0}),
                ("live-omitted-kept", {"ids": [sid, "TESTHOST:11111111-2222-3333-4444-666666666666"]}),
                ("skeleton", {"n": 4, "active": sid}),
                ("send", {"sid": sid, "ts": 1700000000000, "len": 42, "route": "local"}),
                ("empty-session-frame", {"id": sid, "held": True}),
                ("federation-missing", {"load": 1, "first": True}),
                ("federation-missing", {"recovered": True, "first": False}),
                ("cancel-miss", {"sid": sid, "mdLen": 12, "hadRestore": False}),
                ("scrollwrite", {"sid": sid, "writer": "paintAll", "before": 100, "after": 120, "delta": 20, "stick": True, "gesture": False, "sh": 5000, "ch": 800}),
                ("landmiss", {"sid": sid, "anchor": "u1", "proto": 2, "events": 3, "regions": 1, "headKnown": True, "headFrom": "frame", "older": 0, "noframe": False, "trail": 2}),
                ("tailchange", {"sid": sid, "dh": 12, "last": "u9", "stick": True, "sh": 5000, "ch": 800}),
                ("unitchange", {"sid": sid, "dh": 4, "cls": "turn", "fromTail": True, "stick": False, "atBottom": True, "sh": 5000, "ch": 800}),
                ("tailmut", {"sid": sid, "where": "tail", "removed": 1, "added": 2, "reAdded": 0, "shBefore": 5000, "shAfter": 5010, "st": 4200, "ch": 800}),
                ("spacer", {"sid": sid, "top": 40, "bot": 0, "dTop": 8, "dBot": 0, "sh": 5000, "ch": 800}),
                ("scrollgesture", {"sid": sid, "top": 4100, "gesture": True, "sh": 5000, "ch": 800}),
                ("regionask", {"sid": sid, "lo": 10, "hi": 20, "edge": "top", "why": "scroll", "notice": False}),
                ("regionask", {"sid": sid, "why": "land", "nav": "reload", "kind": "older", "keep": 2, "reland": False, "trail": 1, "notice": True, "atBottom": False}),
                ("scrollwrite-capped", {"sid": sid, "perMinute": 200}),
            ],
            "federation": [   # federation.ts diag(): hostconn's events, then the others
                ("hostconn", {"host": host, "ev": "watchdog-close", "why": "quiet", "quietMs": 31000, "foreground": True}),
                ("hostconn", {"host": host, "ev": "dial-deferred", "why": "local-down"}),   # a relay dial put off while the pane's local socket is down (2026-09-18)
                ("hostconn", {"host": host, "ev": "hold", "msgType": "prompt", "rs": 0}),
                ("hostconn", {"host": host, "ev": "flush-halt", "flushed": 2, "held": 1}),
                ("hostconn", {"host": host, "ev": "tunnels-poll-failing", "why": "http", "unread": 3}),
                ("hostconn", {"host": host, "ev": "tunnels-poll-recovered", "unread": 3, "endedUnread": 1}),
                ("hostconn", {"host": host, "ev": "open", "flushed": 1}),
                ("hostconn", {"host": host, "ev": "close", "code": 1006, "clean": False, "detached": False}),
                ("hostconn", {"host": host, "ev": "detach", "pendingDropped": 2}),
                ("hostconn", {"host": host, "ev": "moot", "pendingDropped": ["needFull", "needFull"]}),   # the held asks the ready's connect push answers, dropped before the flush, by type (2026-09-18)
                ("hostconn", {"host": host, "ev": "delta-unknown-slot", "why": "lanes"}),   # a remote patch for a slot the conn's receiver has no table for (2026-09-19)
                ("hostconn", {"host": host, "ev": "delta-unkeyed-base", "why": "bars judging dictlist:k is a list @a1b2c3d4e"}),   # a remote's patch that found no base because its whole frame was refused as one (a collection the receiver's table cannot key): the slot, the collection and shape, and the remote's build when the /tunnels row names one; once per distinct row (2026-09-19)
                ("feedDelta-nobase", {"host": host, "buildId": "b1"}),
                ("feedDelta-stale", {"host": host, "buildId": "b1", "why": "gen"}),   # a stamped remote feedDelta refused by the gen gate (its gen not the held pair's, its base above the held rev, its through below it, or no rev): the ask carries the held pair (2026-09-19)
                ("feedmerge", {"counts": {host: 4}}),
                ("sendqueue", {"host": host, "msgType": "prompt", "gt": 2, "rs": 0, "superseded": True}),
                ("senddrop", {"host": host, "msgType": "prompt", "why": "closed"}),
            ],
            "feed": [
                ("colflip", {"id": "g1", "from": "working", "to": "blocked", "ev": "feedDelta", "buildId": "b1", "predicted": True}),
                ("itemset", {"appeared": 1, "gone": 0, "total": 12, "ev": "feed", "buildId": "b1"}),
                ("feedDelta-unapplied", {"buildId": "b1"}),
            ],
            "outline": [("feedDelta-unapplied", {"buildId": "b1"}), ("delta-unapplied", {"slot": "bars", "rev": 7})],
            "waiting": [("feedDelta-unapplied", {"buildId": "b1"})],
            "strip": [("netFetch", {"ok": True, "tunnels": 2}), ("netFetch", {"ok": False, "err": "TypeError"}), ("netToggle", {"open": True, "base": "/"})],
            "shell": [   # the shell scripts' shellDiag rows (kernel.py)
                ("push-test", {"sidAttached": True, "host": host, "why": "click", "tabs": 2}),
                ("reveal-post", {"status": "ok", "via": "tap", "boot": False}),
                ("deeplink", {"via": "url", "hasSid": True, "hasCard": False, "hasPid": False, "dup": False, "controlled": True}),
                ("tap-pending", {"via": "sw", "sub": True, "rows": 1, "err": "", "getNotifications": 1, "displayed": 1, "vanished": 0, "superseded": 0}),
                ("tap-pending-land", {"sid8": sid.split(":")[1][:8], "ageS": 4, "dup": False}),   # the push ledger's sid is bare; its host rides a field the row does not copy
                ("tap-vanish-land", {"sid8": sid.split(":")[1][:8], "ageS": 4}),
                ("sw-message", {"shape": "object", "hasSid": True, "kind": "tap", "dup": False, "sw": True}),
                ("return-probe", {"decision": "redial-closed", "hiddenMs": 30000, "quietMs": 31000, "attempts": 3, "firstFailMs": 12500, "ms": 30500}),   # D3 (2026-09-18): the shell socket's return probe, one row per return; decision is an enum, the rest ints
            ],
        }
        for surface, rows in posters.items():
            sent = set()
            for what, data in rows:
                err = self.post(surface, what, data)
                self.assertEqual(err, "", "%s %s: %s" % (surface, what, err))
                row = self.rows()[-1]
                self.assertEqual((row["surface"], row["what"], row["data"]), (surface, what, data), "%s %s passes whole" % (surface, what))
                sent |= set(data)
            self.assertEqual(sent, set(km.CLIENT_DIAG_KEYS[surface]), "%s: the fixtures' keys are the table's, both ways" % surface)

    def test_data_that_is_not_an_object_reads_null_and_an_unknown_surface_keeps_no_key(self):
        err = self.post("perf", "minute", "a string where an object goes")
        self.assertIsNone(self.rows()[-1]["data"])
        self.assertEqual(len(err.splitlines()), 1, err)
        self.assertIn("not an object", err)
        self.assertEqual(self.post("perf", "minute", ["a", "list"]), "", "said once per surface")
        self.assertIsNone(self.rows()[-1]["data"])
        self.assertEqual(self.post("perf", "minute", None), "", "a missing data is stored as null and is nothing to say")
        self.assertIsNone(self.rows()[-1]["data"])
        err = self.post("mystery", "probe", {"a": 1, "b": "two"})
        self.assertEqual(self.rows()[-1]["data"], {})
        lines = err.splitlines()
        self.assertEqual(len(lines), 2, err)
        self.assertTrue(all("a surface no allowlist names" in l and "'mystery'" in l for l in lines), err)
        self.assertEqual(self.post("mystery", "probe", {"a": 3}), "", "said once per surface and key")

    def test_the_surface_and_what_strings_are_cut_too(self):
        self.post("s" * 100, "w" * 100, {"a": 1})
        row = self.rows()[-1]
        self.assertEqual(row["surface"], "s" * 64)
        self.assertEqual(row["what"], "w" * 64)
        self.assertEqual(row["data"], {})


if __name__ == "__main__":
    unittest.main()
