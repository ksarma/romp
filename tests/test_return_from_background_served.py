#!/usr/bin/env python3
"""The phone-emulated background-and-return leg: what the dashboard's thirteen reconnect machines do when a suspended
page returns against a path that is down, measured against a hermetic lab kernel and recorded (2026-09-18).

The measured symptom (the phone's own client-diag rows, one 24-minute window): six returns from the background, six
pane documents plus the shell, seven WebSockets, one main thread; every socket dead on five of six returns; 24
`wsconnfail` rows with the first failed handshake about 30 s after each return; fresh content 5.6 s at best and about
35 s at the median; a connect / watchdog-close / reconnect loop on the federation relay (76 `watchdog-close` rows, 55 of
them `connecting`). The reconnect design's PR plan lands the fixes as PRs 2 to 5; this harness is PR 1: it records the
baseline the fixes are measured against and asserts SHAPES only (rows present, fields typed, counts recorded into a
JSON artifact), never counts ahead of the fix that earns them. The count assertions arrive with each fix (relay redials
that wait for the local socket: zero `watchdog-close connecting`; hidden panes that park their redial, LANDED as D2 on
2026-09-18 and pinned in `_parked` below: on the phone every loaded pane but two tells the shell `parked` at the return (four at
D2's landing, none since stage 0 made the other four lazy, except a pane a leg tapped; see below) and two dial, the visible chat and the feed, which is exempt from parking by the user's ruling of
2026-09-18 so the shell's bell keeps receiving card-trouble entries while the Feed tab is hidden, one extra redial per
return accepted; the witness is the shell's wsState words the driver records, because a parked pane's own `return` row
with `parked:true` waits in its queue for the tap, which no leg makes, so within a leg only the dialing panes' rows reach
the kernel; the shell leading the visible pane's redial: zero pane `wsconnfail` and one `return-probe`), so a count
pinned here ahead of its fix would pin today's storm. Since stage 0 (2026-09-18, `_lazy` below) the phone loads only the chat
and the feed at boot: the Outline, the Sessions band, the Waiting pane and the Files pane have no document until their first tap,
so the cold open's documents, sockets and connect pushes drop by four, the parked set at a return is empty (a pane a leg tapped
excepted), and the tab-tap leg exercises the parked contract on a pane that did not exist at boot.

The lab: one kernel from test_ship_reship_served.kernel_env (a private XDG root, `session-hosts` floored off,
ROMP_MANAGER_PORT=1, no catalog or update fetch, a hermetic postal bus), with ROMP_WS_KEEPALIVE=2 (WS_DEAD_S 6 s, a floor for a socket the
driver's close at the suspend misses; the records show none does, see the limits below); a private dist
(lab_dist.copy_dist); four synthetic sessions (`web`, `api`, `tests` of the notes-api demo with closed-turn transcripts,
and a transcript-less `docs`; placeholder uuids, host TESTHOST). The driver (tests/return_from_background_browser.mjs) opens the served shell, waits for every pane socket's
`wsState up` word, emulates the suspend (visibilityState hidden in every document, the held sockets closed with 1001),
holds the outage on new dials for the interval after the return, then reads the rows. Two shells (a phone: an iPhone
descriptor at 390 x 844, under _MOBILE_MQ, six pane iframes with one .m-on; a desktop window at 1600 x 760), two outage
regimes (REFUSED: every new dial is closed at once; HUNG: a new dial stays CONNECTING until the outage ends, the phone's
case), at 12 s and 30 s (the 30 s desktop legs are opt-in: RETURN_HARNESS_FULL=1; the repo marks no test slow, so the slow
legs carry `slow` in their names and the desktop's are behind the knob, which keeps the file under CI's budget).

What is recorded per leg, from `<lab xdg>/romp/client-diag.jsonl` (the shim's rows reach it on the reopened socket) and
the driver's own log, into `<lab>/return-harness-<shell>-<regime>-<s>s.json` and, at the end, one combined
`return-harness-measurements.json` (copied to $RETURN_HARNESS_OUT when set): per pane the `return` decision and
`hiddenMs`, `wsconnfail` attempts, `wsclose` count, `watchdog-close` by why, `return-fresh` ms / bytesSince / redialed,
the shell's `return-probe` rows (none today), federation `hostconn` rows by ev and why (none without an attached host),
the kernel's `wsopen` rows per app at boot and in the return window (the storm as the kernel saw it), the beacon's `perf`
rows with `vis`, `wsBytes`, `free`, `rafGap`, `marks` when present (perfShare is on in the lab's romp:settings), the
sockets dialed per return by verdict, and the order in which the eight documents' visibilitychange handlers ran (the shell, the settings frame at about:blank and the six panes).

Emulation limits, stated so the baseline is read right: scripts keep running while the documents read hidden (a
suspended phone's do not), so the hidden dwell is short and the closes land as the FIN a thawed tab receives; the
handler order is the dispatch order the driver chose (top document first, frames in tree order), recorded for the note
rather than discovered; no `pageshow` is dispatched (the design dispatches none); the REFUSED regime is a closed port,
not the phone's dead path, which the HUNG regime emulates. The override is installed per DOCUMENT, by an init script and
again at boot in any frame the init script missed: an iframe navigating from its initial about:blank to a same-origin
page keeps its Window (Firefox and WebKit every time, Chromium sometimes), and playwright's init script never reached the
eagerly created frames (chat and feed on the phone; every pane on the desktop) in Firefox, so without the late pass their shims read the browser's
real visibilityState and filed `keep` with `hiddenMs -1`; the artifact's `lateInstall` names the frames the pass caught.
The kernel's dead-socket drop plays no part here: the driver's close at the suspend reaches the kernel at once (the
kernel-side leg of every held socket closed 13 to 25 ms after the suspend, code 1006), so the kernel sees an immediate
drop where the phone's kernel keeps pushing into a dead socket until WS_DEAD_S; ROMP_WS_KEEPALIVE=2 stays only as the
floor for a socket the close misses. The refused-regime dial counts are point samples of a 250 ms cadence and vary by a
few percent between runs; the hung-regime counts are exact.
The measurements are the emulated baseline for this box, not the phone's.

TODO (federation half, not built here): two hermetic kernels, a hub plus a checked-in TESTHOST (the pattern of
tests/test_federated_dial_terms_served.py), the hub's /remote/<host>/ws relay dials routed by the same matcher and
refused or hung alongside /ws, asserting after PR 2 `dial-deferred` on the hub's panes and no relay dial before the local
`wsopen`. Left out of this PR for the runtime budget (two more kernel boots plus the check-in poll); the single-kernel
legs record the federation rows' shape (none) so the reader sees the slot.

Skips: LOUDLY without the extension deps or a Chromium (CI installs Chromium and runs the *_served.py files under
ROMP_SERVED_TESTS_REQUIRE=1); the Firefox and WebKit legs are `optional:` skips when that engine is absent or not
declared in ROMP_SERVED_TESTS_ENGINES. The lab kernel uses its own port; the driver asserts /healthz on that port before
any request. Synthetic sessions only; no real data.
"""
import json
import lab_dist
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
EXT = os.path.join(ROOT, "vscode-extension")
sys.path.insert(0, HERE)
import test_ship_reship_served as _lab                      # noqa: E402  (kernel_env: every lab kernel's environment)

# Hermetic state BEFORE anything: this module loads no romp code in-process (the kernel is a subprocess under
# kernel_env's roots), but the floor costs two lines and a later edit that adds a load must not write real state.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor

DRIVER = os.path.join(HERE, "return_from_background_browser.mjs")
APPS = ("chat", "timeline", "fleet", "feed", "waiting", "files")   # the six pane documents the shell serves iframes for; the shell itself dials app=shell
FRESH_APPS = tuple(a for a in APPS if a != "files")                # the Files pane gets no resync frame, so it files no return-fresh
# stage 0 (2026-09-18): on the phone these load on their FIRST TAP (no document, no shim, no socket at boot); the chat ships its src,
# the feed is exempt (the bell). The desktop loads all six at boot.
LAZY_PHONE = ("timeline", "fleet", "waiting", "files")


def km_pane_order():
    """kernel.py's _PANE_ORDER, read as text (this module loads no romp code in-process): the (key, label) pairs of the pane routes."""
    src = Path(os.path.join(ROOT, "kernel", "kernel.py")).read_text()
    m = re.search(r"^_PANE_ORDER = \((.*?)\)\n", src, re.S | re.M)
    assert m, "kernel.py defines _PANE_ORDER"
    pairs = re.findall(r'\("([a-z]+)", "([^"]+)"\)', m.group(1))
    assert len(pairs) >= 6, pairs
    return pairs


def _eager(shell, tap=None):
    """The panes whose documents the shell has loaded before the suspend: every pane on the desktop; on the phone the eager ones plus
    the pane a leg tapped (its document loaded on the tap)."""
    return tuple(a for a in APPS if shell != "phone" or a not in LAZY_PHONE or a == tap)
VISIBLE = "chat"                                                  # the phone's default tab and the desktop's first pane
HOST = "TESTHOST"
SESSIONS = (("11111111-2222-4333-8444-000000000101", "web", "w"),
            ("11111111-2222-4333-8444-000000000102", "api", "a"),
            ("11111111-2222-4333-8444-000000000103", "tests", "t"),
            ("11111111-2222-4333-8444-000000000104", "docs", ""))   # transcript-less (no .jsonl): never a skeleton, its full carries no events; the boot-on-Feed legs' active tab (extra9-1)
TRANSCRIPT_SESSIONS = tuple(s for s in SESSIONS if s[2])   # the three with a transcript: the skeletons the chain fetches, the feed's cards
DECISIONS = {"keep", "redial-closed", "redial-stale"}
FULL = os.environ.get("RETURN_HARNESS_FULL") == "1"
OUT_DIR = os.environ.get("RETURN_HARNESS_OUT", "")
# the reconnect cue (iOS item 4, 2026-10-02): the badge's no-flash hold, read off kernel.py as text (this module loads no romp code
# in-process), and the cue's Log lines as drafted, spelled here so a change to the product's copy shows up as a red, not a match
CUE_WAIT = "Waiting for the kernel to respond. The dashboard updates on its own when it does."
CUE_HUNG1 = "Trying again: the first try got no response."
CUE_CONNECT = "could not connect to the kernel."
BADGE_TEXT = "reconnecting…"   # the glance's whole text whenever it is painted (upstream's word, no count), read off the painted frames


def cue_hold_ms():
    src = Path(os.path.join(ROOT, "kernel", "kernel.py")).read_text()
    m = re.search(r"^_RECONN_BADGE_HOLD_MS = (\d+)$", src, re.M)
    assert m, "kernel.py defines _RECONN_BADGE_HOLD_MS"
    return int(m.group(1))


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def _transcript(sid, tag, cwd, pairs):
    """`pairs` CLOSED user/assistant turns for `sid` (an OPEN turn would invite the boot reconcile to resume it)."""
    out, parent = [], None
    filler = ["The search index rebuild now reads its weights from the notes-api config.",
              "Tokenizer edge cases (hyphens, quotes) are covered by the fixture set.",
              "The stemmer dominates the rebuild; caching its table halves the time."]
    for i in range(pairs):
        u, a = "%s-u%02d" % (tag, i), "%s-a%02d" % (tag, i)
        out.append({"type": "user", "uuid": u, "parentUuid": parent, "sessionId": sid, "cwd": cwd,
                    "timestamp": "2024-01-01T00:%02d:00Z" % (i % 60), "promptSource": "typed",
                    "message": {"role": "user", "content": "turn %d: what changed in the notes-api search?" % i}})
        out.append({"type": "assistant", "uuid": a, "parentUuid": u, "sessionId": sid, "cwd": cwd,
                    "timestamp": "2024-01-01T00:%02d:30Z" % (i % 60),
                    "message": {"role": "assistant", "model": "claude-opus-5", "stop_reason": "end_turn",
                                "content": [{"type": "text", "text": filler[i % len(filler)]}]}})
        parent = a
    return "".join(json.dumps(r) + "\n" for r in out)


# one synthetic subagent under the `tests` session (round 1 of the review, 2026-10-03): an Agent turn closing its transcript and the
# agent's own transcript and sidecar beside it, as the CLI writes them (plans/subagent-transcripts.md), so a leg can open the chat's
# subagent viewer, whose sticky header and pin sit inside the transcript's container. Placeholder ids; invented text.
SUB_SID, SUB_AGENT, SUB_TOOL = "11111111-2222-4333-8444-000000000103", "a0123456789abcdef", "toolu_11112222333344445555"


def _subagent(proj, cwd):
    sid, aid = SUB_SID, SUB_AGENT
    turn = [{"type": "user", "uuid": "t-u90", "parentUuid": "t-a05", "sessionId": sid, "cwd": cwd, "timestamp": "2024-01-01T00:20:00Z", "promptSource": "typed",
             "message": {"role": "user", "content": "turn 6: check the notes-api tokenizer fixtures"}},
            {"type": "assistant", "uuid": "t-a90", "parentUuid": "t-u90", "sessionId": sid, "cwd": cwd, "timestamp": "2024-01-01T00:20:10Z",
             "message": {"role": "assistant", "model": "claude-opus-5", "stop_reason": "tool_use",
                         "content": [{"type": "tool_use", "id": SUB_TOOL, "name": "Agent", "input": {"description": "Check fixtures", "prompt": "Read the tokenizer fixtures and list gaps.", "subagent_type": "general-purpose"}}]}},
            {"type": "user", "uuid": "t-u91", "parentUuid": "t-a90", "sessionId": sid, "cwd": cwd, "timestamp": "2024-01-01T00:21:00Z",
             "toolUseResult": {"agentId": aid, "content": [{"type": "text", "text": "The fixtures cover hyphens and quotes."}], "totalDurationMs": 50000},
             "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": SUB_TOOL, "content": [{"type": "text", "text": "The fixtures cover hyphens and quotes."}]}]}},
            {"type": "assistant", "uuid": "t-a91", "parentUuid": "t-u91", "sessionId": sid, "cwd": cwd, "timestamp": "2024-01-01T00:21:10Z",
             "message": {"role": "assistant", "model": "claude-opus-5", "stop_reason": "end_turn", "content": [{"type": "text", "text": "The fixture set already covers both edge cases."}]}}]
    with open(os.path.join(proj, sid + ".jsonl"), "a") as f:
        f.write("".join(json.dumps(r) + "\n" for r in turn))
    sub, parent = [], None
    for i in range(14):
        u, a = "s-u%02d" % i, "s-a%02d" % i
        for rec in ({"type": "user", "uuid": u, "parentUuid": parent, "message": {"role": "user", "content": "step %d: read the next tokenizer fixture" % i}},
                    {"type": "assistant", "uuid": a, "parentUuid": u, "message": {"role": "assistant", "model": "claude-opus-5", "stop_reason": "end_turn",
                                                                                   "content": [{"type": "text", "text": "Fixture %d covers hyphenated words in the notes-api search index." % i}]}}):
            rec.update(isSidechain=True, agentId=aid, sessionId=sid, cwd=cwd, timestamp="2024-01-01T00:20:%02dZ" % (11 + i))
            sub.append(rec)
        parent = a
    sd = os.path.join(proj, sid, "subagents")
    os.makedirs(sd, exist_ok=True)
    Path(sd, "agent-%s.jsonl" % aid).write_text("".join(json.dumps(r) + "\n" for r in sub))
    Path(sd, "agent-%s.meta.json" % aid).write_text(json.dumps({"agentType": "general-purpose", "description": "Check fixtures", "spawnDepth": 1, "toolUseId": SUB_TOOL}))


def _seed(lab):
    """The lab's state root and Claude config dir, with the three synthetic sessions of the notes-api demo (the `tests` session
    with one synthetic subagent, _subagent)."""
    state = os.path.join(lab, "xdg", "romp")
    claude = os.path.join(lab, "claude")
    cwd = os.path.join(lab, "proj")
    for d in ("names", "sdk", "states"):
        os.makedirs(os.path.join(state, d), exist_ok=True)
    os.makedirs(cwd, exist_ok=True)
    Path(state, "session-hosts").write_text("off\n")   # a lab root writes its own hosts off (the conftest rule)
    Path(state, "usage.json").write_text(json.dumps({"five_hour": {"pct": 100}, "seven_day": {"pct": 10}}))   # park sends: no CLI spawns
    proj = os.path.join(claude, "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(cwd)))
    os.makedirs(proj, exist_ok=True)
    for sid, sname, tag in SESSIONS:
        Path(state, "names", sid).write_text("%s\t%s\t\t\n" % (sname, cwd))
        Path(state, "sdk", sid + ".json").write_text(json.dumps(
            {"sid": sid, "name": sname, "cwd": cwd, "mode": "auto", "effort": "high", "lastSid": sid, "alive": True}))
        if tag:   # the transcript-less `docs` session has a name and a live registration and no .jsonl (a session created and not yet spoken to)
            Path(proj, sid + ".jsonl").write_text(_transcript(sid, tag, cwd, 6))
    assert SESSIONS[2][0] == SUB_SID and SESSIONS[2][2] == "t", "the subagent's parent is the `tests` session"
    _subagent(proj, cwd)
    return state, claude


_DROPPED_SHELL_ROWS = ("pane-load-failed", "pane-load-unmarked")   # the lazy panes' two shell rows, dropped with their keys in the reviewer's round 7 (regression-1)


def _shell_rows(rows, wid):
    """This page's pane-load-failed and pane-load-unmarked rows, which a leg asserts absent. The shell's other rows are main's (its boot
    rows, deeplink and tap-pending; its return-probe, which measure() reads) and stay out of the read; a row re-added under another what
    or surface is the fake-DOM harness's to catch (tests/test_pane_state_broadcast.py LazyPanes reads every clientDiag message)."""
    return [x for x in rows if x.get("wid") == wid and x.get("surface") == "shell" and x.get("what") in _DROPPED_SHELL_ROWS]


def _rows(path):
    out = []
    try:
        txt = Path(path).read_text(encoding="utf-8")
    except OSError:
        return out
    for ln in txt.splitlines():
        try:
            out.append(json.loads(ln))
        except ValueError:
            pass   # a partial last line
    return out


def measure(rows, r):
    """The leg's measurements: `rows` the lab's client-diag rows, `r` the driver's RESULT. Rows are the run's own by wid
    (every pane document and the kernel's wsopen rows carry the dashboard's id); windows are the driver's wall clock
    against the rows' `t` (whole seconds), one second of slack each side."""
    wid = r.get("wid") or ""
    t = r.get("t") or {}
    s_suspend = int(t.get("suspend", 0) // 1000)
    s_return = int(t.get("return", 0) // 1000) - 1
    mine = [x for x in rows if x.get("wid") == wid]
    pane = [x for x in mine if x.get("surface") == "pane-shim"]

    def by_app(what, fields):
        out = {}
        for x in pane:
            if x.get("what") != what or x.get("t", 0) < s_return:
                continue
            d = x.get("data") or {}
            out.setdefault(d.get("app") or "?", []).append({k: d.get(k) for k in fields if k in d})
        return out

    ret = by_app("return", ("decision", "hiddenMs", "resumed", "resent", "quietMs", "ready", "parked", "awaitLink"))
    fresh = by_app("return-fresh", ("ms", "bytesSince", "redialed", "linkUpMs", "parked"))
    connfail = by_app("wsconnfail", ("attempts", "firstFailMs"))
    wsclose = {a: len(v) for a, v in by_app("wsclose", ("code", "quietMs", "sinceOpenMs")).items()}
    wd = {}
    for x in pane:
        if x.get("what") == "watchdog-close" and x.get("t", 0) >= s_return:
            d = x.get("data") or {}
            key = "%s/%s" % (d.get("app"), d.get("why"))
            wd[key] = wd.get(key, 0) + 1
    hostconn, deferred = {}, 0
    for x in mine:
        if x.get("surface") != "federation" or x.get("t", 0) < s_suspend:
            continue
        d = x.get("data") or {}
        if x.get("what") == "hostconn":
            key = "%s/%s/%s" % (d.get("ev"), d.get("why", "-"), "fg" if d.get("foreground") else "bg")
            hostconn[key] = hostconn.get(key, 0) + 1
        elif x.get("what") == "dial-deferred":
            deferred += 1
    page_load = {}
    for x in pane:
        if x.get("what") == "page-load" and x.get("t", 0) >= s_suspend - 5:
            d = x.get("data") or {}
            key = "%s/%s" % (d.get("app"), d.get("nav"))
            page_load[key] = page_load.get(key, 0) + 1
    shell = [{"what": x.get("what"), **{k: (x.get("data") or {}).get(k) for k in ("attempts", "firstFailMs", "ms")}}
             for x in mine if x.get("surface") == "shell" and x.get("what") == "return-probe" and x.get("t", 0) >= s_return]
    wsopen = [x for x in mine if x.get("surface") == "kernel" and x.get("what") == "wsopen"]
    boot_open, return_open = {}, {}
    for x in wsopen:
        d = x.get("data") or {}
        app = d.get("app") or "?"
        if x.get("t", 0) < s_suspend:
            boot_open[app] = boot_open.get(app, 0) + 1
        elif x.get("t", 0) >= s_return:
            return_open.setdefault(app, []).append({"kind": d.get("kind"), "reconnect": d.get("reconnect"), "t": x.get("t")})
    perf = {}
    for x in mine:
        if x.get("surface") != "perf" or x.get("t", 0) < s_suspend:
            continue
        d = x.get("data") or {}
        key = "%s/%s" % (x.get("what"), d.get("app"))
        ent = perf.setdefault(key, {"n": 0, "fields": []})
        ent["n"] += 1
        for k in ("vis", "wsBytes", "free", "rafGap", "marks", "slow", "capped"):
            if k in d and k not in ent["fields"]:
                ent["fields"].append(k)
        if "vis" in d and "vis" not in ent:
            ent["vis"] = d["vis"]
    dials = [d for d in (r.get("dials") or []) if d.get("t", 0) >= t.get("return", 0)]
    by_verdict, per_app, timeline = {}, {}, {}
    for d in dials:
        by_verdict[d.get("verdict") or "?"] = by_verdict.get(d.get("verdict") or "?", 0) + 1
        per_app[d.get("app") or "?"] = per_app.get(d.get("app") or "?", 0) + 1
        tl = timeline.setdefault(d.get("app") or "?", [])
        if len(tl) < 12:   # the first dials per app, as [ms after the return, verdict, reconnect term]: enough to read the cadence
            tl.append([int(d.get("t", 0) - t.get("return", 0)), d.get("verdict"), bool(d.get("reconnect"))])
    vis = r.get("vis") or []
    order = {}
    for v in vis:
        if v.get("t", 0) < t.get("suspend", 0) - 50:
            continue   # the engines fire a real visibilitychange in a frame's initial about:blank document at boot; kept in visRecords, not the order
        order.setdefault(v.get("state"), []).append(v.get("id") or v.get("doc"))
    return {
        "leg": {"engine": r.get("engine"), "shell": r.get("shell"), "regime": r.get("regime"), "outageMs": r.get("outageMs"),
                "hiddenDwellMs": r.get("hiddenDwellMs"), "mobileShell": r.get("mobileShell"), "bodyClass": r.get("bodyClass")},
        "wid": wid, "bootUpApps": r.get("bootUpApps"), "bootMs": r.get("bootMs"), "closedAtSuspend": r.get("closedAtSuspend"),
        "t": t, "pageErrors": len(r.get("errors") or []), "overrideErrors": r.get("overrideErrors") or [],
        "return": ret, "returnFresh": fresh, "wsconnfail": connfail, "wsclose": wsclose, "watchdogClose": wd,
        "hostconn": hostconn, "dialDeferred": deferred, "shellReturnProbe": shell,
        "wsopenBoot": boot_open, "wsopenReturn": {a: len(v) for a, v in return_open.items()}, "wsopenReturnRows": return_open,
        "dialsAfterReturn": {"total": len(dials), "byVerdict": by_verdict, "perApp": per_app,
                             "cutByPage": sum(1 for d in dials if d.get("cutByPage")), "firstPerApp": timeline},
        "freshSeenMsAfterOutage": r.get("freshSeenMsAfterOutage"),
        "visibilitychangeOrder": order, "visRecords": vis, "hiddenDispatch": r.get("hiddenDispatch"), "visibleDispatch": r.get("visibleDispatch"),
        "frames": r.get("frames"), "pageLoad": page_load, "wsWords": len(r.get("wsWords") or []),
        "lateInstall": r.get("lateInstall"), "installed": r.get("installed"),
        "perf": perf, "liveAtEnd": r.get("liveAtEnd"),
    }


class ReturnFromBackground(unittest.TestCase):
    """One lab kernel for every leg (setUpClass); each leg is one driver run, one measurement, one artifact."""
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.kernel, cls.lab, cls.measurements = None, None, {}
        try:
            cls._boot()
        except BaseException:
            cls.tearDownClass()
            raise

    @classmethod
    def _boot(cls):
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            raise unittest.SkipTest("extension deps absent (npm ci not run here): the served leg needs them")
        cls.lab = tempfile.mkdtemp(prefix="return-harness-")
        dist = os.path.join(cls.lab, "dist")
        lab_dist.copy_dist(dist)   # the checkout's ONE build of the bundles, copied under its lock (tests/lab_dist.py)
        cls.state, claude = _seed(cls.lab)
        cls.diag = os.path.join(cls.state, "client-diag.jsonl")
        cls.port, cls.token = _free_port(), "testtok-return"
        # ROMP_WS_KEEPALIVE=2: WS_DEAD_S 6 s, a floor for a socket the driver's close at the suspend misses. The records show
        # none does (every kernel-side leg closed 13 to 25 ms after the suspend, code 1006), so the kernel sees an immediate
        # drop here where the phone's kernel keeps pushing into a dead socket until WS_DEAD_S (review round 1).
        seams = {"ROMP_WS_KEEPALIVE": "2", "ROMP_HOST_NAME": HOST}   # a dict, not keyword arguments after the serve secret's positional slot: the secret scanner reads the first seam's name as a key assignment there
        cls.env = _lab.kernel_env(cls.lab, claude, dist, cls.port, cls.token, **seams)
        cls.klog = os.path.join(cls.lab, "kernel.log")
        cls.kernel = subprocess.Popen([os.path.join(BIN, "romp-kernel")], stdout=open(cls.klog, "w"),
                                      stderr=subprocess.STDOUT, env=cls.env)
        for _ in range(120):
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/healthz" % cls.port, timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise unittest.SkipTest("hermetic kernel never served /healthz here")

    @classmethod
    def tearDownClass(cls):
        if cls.lab and cls.measurements:
            combined = os.path.join(cls.lab, "return-harness-measurements.json")
            Path(combined).write_text(json.dumps(cls.measurements, indent=1, sort_keys=True))
            if OUT_DIR:
                os.makedirs(OUT_DIR, exist_ok=True)
                shutil.copy(combined, os.path.join(OUT_DIR, "return-harness-measurements.json"))
                for name in os.listdir(cls.lab):
                    if (name.startswith("return-harness-") or name.startswith("result-")) and (name.endswith(".json") or name.endswith(".png")) and name != "return-harness-measurements.json":
                        shutil.copy(os.path.join(cls.lab, name), os.path.join(OUT_DIR, name))
        if cls.kernel:
            try:
                os.kill(cls.kernel.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            cls.kernel.wait()
        if cls.lab:
            shutil.rmtree(cls.lab, ignore_errors=True)

    # ---- the driver ----
    def _drive(self, shell, regime, outage_s, engine="chromium", tap=None, boot_tab=None, abort=False, denied=False, hold_active_full_ms=0, active_sid=None, retry_enter=False, unmarked=False, post_tap=None,
               cue_app=None, sub_view=False, notice_after_paint=False):
        declared = os.environ.get("ROMP_SERVED_TESTS_ENGINES", "")
        if engine != "chromium" and declared and engine not in [e.strip() for e in declared.split(",")]:
            self.skipTest("optional: this runner declares no %s (ROMP_SERVED_TESTS_ENGINES=%s)" % (engine, declared))
        name = "%s-%s-%s-%ds%s%s%s%s%s%s%s%s%s%s" % (engine, shell, regime, outage_s, "-tap-" + tap if tap else "", "-abort" if abort else "", "-denied" if denied else "", "-unmarked" if unmarked else "", "-boot-" + boot_tab if boot_tab else "", "-heldfull" if hold_active_full_ms else "", "-posttap-" + post_tap if post_tap else "",
                                                     "-cue-" + cue_app if cue_app else "", "-subview" if sub_view else "", "-notice" if notice_after_paint else "")
        eager = _eager(shell, None if unmarked else tap)   # a tapped pane's document is loaded before the suspend (on the re-tap, under abort or denied); an unmarked document runs no shim, so the tapped pane never joins the eager set (pass 5, the author's label, taking the reviewer's round-4 finding tests-1)
        # a derived set that came out empty would hand the driver a boot wait and a fresh wait that end at once with nothing witnessed
        # (review round 2, 2026-09-19: every derived expectation must fail when the derivation yields nothing)
        self.assertTrue(_eager(shell), "the eager set for the %s shell is not empty" % shell)
        self.assertTrue([a for a in eager if a in FRESH_APPS], "the fresh set is not empty: %r" % (eager,))
        # a pane tapped after the return (post_tap, iOS item 4) is parked until that tap, so the return's fresh wait leaves it out (it
        # files its return-fresh only after the tap); the tap's own wait is the driver's
        fresh_apps = [a for a in eager if a in FRESH_APPS and a != post_tap]
        cfg = {"engine": engine, "shell": shell, "regime": regime, "outageMs": outage_s * 1000, "hiddenDwellMs": 400,
               "url": "http://127.0.0.1:%d/?token=%s" % (self.port, self.token),
               "healthz": "http://127.0.0.1:%d/healthz" % self.port, "diag": self.diag, "apps": list(APPS),
               "eagerApps": list(_eager(shell)), "freshApps": fresh_apps, "tapPane": tap,   # the boot wait is the eager panes' (a lazy pane has no shim to say up); the fresh wait includes a tapped pane
               "abortPane": tap if (abort or denied) else "",   # HIGH 2 (review round 1): the tapped pane's first document fetch fails; the shell must say so and the re-tap must load it
               "retryEnter": bool(retry_enter),   # ui-1 (review round 4): after the failed state, Enter on the focused Try again button; the route still fails the fetch, and the driver reads the active element at the re-failure
               "abortMode": "unmarked" if unmarked else ("denied" if denied else "abort"),   # unmarked (pass 5, the reviewer's round-4 tests-1): the route hands the frame the kernel's real 200 with the shim's marker statement stripped, a stamped document with no shim: shown as served, never a failure. Else the failure's input: abort (the route aborts the navigation) or denied (review round 4, kernel-1 and tests-1: the route re-issues the pane's one request credential-less and hands the frame the REAL kernel's 403; not shown as served, the retry road stands)
               "perfShare": True, "bootTimeoutMs": 30000, "freshTimeoutMs": 25000, "settleMs": 1500,
               "bootTab": boot_tab or "", "expectPrefetchAfterChatTap": bool(boot_tab and tap == "chat"),   # stage 0, review round 1: a phone left on another tab, then the Chat tab shown, arms the idle chain
               # the chat blob's active tab (the dial's hint): with none the kernel serves the whole board and there is no skeleton set to prefetch.
               # A leg names its own (active_sid); the boot-tab legs default to web, the held-full leg to web too (the kernel's one full is what is held)
               "activeSid": active_sid if active_sid is not None else (SESSIONS[0][0] if (boot_tab or hold_active_full_ms) else ""),
               "holdActiveFullMs": hold_active_full_ms,   # fresh-2 (review round 3): the driver's proxy holds the boot chat dial's frames naming the active tab for this long
               "postTap": post_tap or "", "postTapMs": 2000, "cueHoldMs": cue_hold_ms() if post_tap else 0,
               "cueApp": cue_app or "chat", "subView": bool(sub_view), "noticeAfterPaint": bool(notice_after_paint),   # round 1 of the review (2026-10-03): the pane whose badge is read, the subagent viewer opened before the suspend, the landing notice shown over the painted badge   # iOS item 4: the tap after the return, 2 s on (inside the badge's 30 s failsafe, where the off-screen paint showed)
               "showFilesControl": tap == "files",   # extra9-2 (review round 3): the Files tab exists only with the gear's Files control on (romp:settings.showFilesControl, the literal true); the install seeds it before the shell parses
               "shots": os.path.join(self.lab, "return-harness-" + name) if os.environ.get("RETURN_HARNESS_SHOTS") else ""}
        cfg["resultPath"] = os.path.join(self.lab, "result-%s.json" % name)   # the full result; the RESULT: line is a compact copy
        cfg_path = os.path.join(self.lab, "cfg-%s.json" % name)
        Path(cfg_path).write_text(json.dumps(cfg))
        try:
            p = subprocess.run(["node", DRIVER], capture_output=True, text=True, timeout=240,   # an abort leg on WebKit waits out the shell's 30 s backstop
                               env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg_path))
        except subprocess.TimeoutExpired as e:
            so = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode()
            self.fail("driver timed out; partial output:\n%s" % so[-3000:])
        if p.returncode == 3:
            if engine == "chromium":
                self.skipTest("no playwright chromium on this box: the served leg needs one (CI installs it)")
            self.skipTest("optional: no playwright %s on this machine: %s" % (engine, p.stderr.strip()[-300:]))
        self.assertEqual(p.returncode, 0, "driver failed:\n" + p.stdout[-3000:] + p.stderr[-3000:])
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
        self.assertIsNotNone(line, "driver printed no result:\n" + p.stdout[-3000:] + p.stderr[-3000:])
        r = json.loads(line[len("RESULT:"):])
        self.assertNotIn("died", r, "driver aborted early: %r (kernel log tail: %s)" % (r.get("died"), Path(self.klog).read_text()[-800:]))
        self.assertTrue(os.path.exists(cfg["resultPath"]), "the driver wrote its full result: %r" % r.get("resultWriteError"))
        full = json.loads(Path(cfg["resultPath"]).read_text(encoding="utf-8"))
        self.assertEqual(len(full.get("dials") or []), r.get("dialsN"), "the full result carries every dial the compact line counted")
        return name, full

    def _leg(self, shell, regime, outage_s, engine="chromium", tap=None, boot_tab=None, abort=False, denied=False, hold_active_full_ms=0, active_sid=None, retry_enter=False, unmarked=False):
        name, r = self._drive(shell, regime, outage_s, engine, tap, boot_tab, abort, denied, hold_active_full_ms, active_sid, retry_enter, unmarked)
        rows = _rows(self.diag)
        m = measure(rows, r)
        art = os.path.join(self.lab, "return-harness-%s.json" % name)
        Path(art).write_text(json.dumps(m, indent=1, sort_keys=True))
        type(self).measurements[name] = m
        if abort or denied:
            self._abort(name, r, rows, tap, engine, "denied" if denied else "abort", retry_enter)   # first on a failure leg: a detector that takes the failed fetch for a load leaves no shim to park or dial, so every later check fails after it, and the red should name the refused input (review round 2 closeout)
        if denied:
            self._denied(name, r, rows, tap)   # the denied leg's own checks: the real 403's status, and the page's state over the document it must not show
        if unmarked:
            self._unmarked(name, r, rows, tap)   # first on the unmarked leg: a detector that calls the served document a failure re-parks it, and every later read is of a re-parked pane
        self._shapes(name, r, m, regime)
        self._parked(name, r, m)
        self._lazy(name, r, m, None if unmarked else tap)   # the unmarked document has no shim: the lazy counts are a no-tap boot's
        self._dial(name, r, boot_tab, tap)
        if hold_active_full_ms:
            self._gate(name, r)
        self._feed_paint(name, r, boot_tab)
        self._return_chain(name, r, rows)
        self._cue(name, r, regime, outage_s)
        return m

    # ---- the reconnect cue (iOS item 4, 2026-10-02): the glance and its detail in a real engine ----
    def _cue(self, name, r, regime, outage_s, require_no_paint=False):
        """The visible chat's corner badge, read once per frame (the driver's requestAnimationFrame loop), and the shell's Log line,
        read at each of its mutations. The badge: nothing painted between the suspend and the return (the drop while hidden is held);
        after the return it paints ONCE, no sooner than the hold after the return, and clears ONCE, at or after the chat's first
        fresh frame (the clearing event); with an outage that is during the outage and after its end (the link up). With no outage
        (the healthy leg) the outcome is keyed on the hold's own events, never on elapsed time (_hold_outcome): one paint when the
        hold's timer fired before the chat's first fresh frame, none when that frame came first; a leg whose name claims no paint
        passes require_no_paint, and a run whose return was slow enough to paint fails, named (_hold_outcome).
        The Log line: shown with the wait line when the page returns, never hidden while the outage holds, hidden at the end, at or
        after the outage's end; in a hung outage past the connect cut it shows the cut's line; in a refused one the connect line."""
        where = name + ": "
        hold = cue_hold_ms()
        self.assertEqual(r.get("cueArm"), {"pane": "armed", "shell": "armed"}, where + "both cue recorders armed: %r" % (r.get("cueArm"),))
        cue = r.get("cue") or {}
        t = r["t"]
        ret, end, sus = t["return"], t["outageEnd"], t["suspend"]
        self.assertGreater(cue.get("frames", 0), 0, where + "the chat's frame loop ran: %r" % ({k: cue.get(k) for k in ("frames", "lastT", "err")},))
        self.assertGreaterEqual(cue.get("lastT", 0), t["fresh"], where + "...through the fresh frame, so 'never painted' was read, not assumed")
        badge = cue.get("badge") or []
        self._badge_text(where, badge)
        self._badge_clear_of_chrome(where, badge, moves=cue.get("moves"))
        self.assertEqual([b for b in badge if b["on"] and sus <= b["t"] < ret], [], where + "nothing painted while the page read hidden: %r" % (badge,))
        self.assertFalse([b for b in badge if b["t"] < ret] and [b for b in badge if b["t"] < ret][-1]["on"], where + "the badge was off entering the return: %r" % (badge,))
        fresh = [x for x in (cue.get("fresh") or []) if x >= ret]
        self.assertTrue(fresh, where + "the chat stamped a fresh frame after the return: %r" % (cue.get("fresh"),))
        ons = [b["t"] - ret for b in badge if b["on"] and b["t"] >= ret]
        offs = [b["t"] - ret for b in badge if not b["on"] and b["t"] >= ret]
        rel_fresh, rel_end = fresh[0] - ret, end - ret
        type(self).measurements.setdefault(name, {})["cue"] = {"holdMs": hold, "paintMs": ons, "clearMs": offs, "freshMs": rel_fresh, "outageEndMs": rel_end,
                                                               "holdEvents": [{"k": e.get("k"), "ms": e["t"] - ret, "f": e.get("f")} for e in (cue.get("hold") or []) if e.get("t", 0) >= ret],
                                                               "log": [{"ms": e["t"] - ret, "shown": e.get("shown"), "text": e.get("text")} for e in (cue.get("log") or []) if e["t"] >= sus]}
        if outage_s:
            self.assertEqual(len(ons), 1, where + "painted once after the return, no flap: on %r off %r" % (ons, offs))
            self.assertEqual(len(offs), 1, where + "cleared once: on %r off %r" % (ons, offs))
            self.assertGreaterEqual(ons[0], hold - 20, where + "not painted before the hold (%d ms): %r" % (hold, ons))
            self.assertLess(ons[0], rel_end, where + "painted during the outage (ends at %d ms): %r" % (rel_end, ons))
            self.assertGreaterEqual(offs[0], rel_end, where + "cleared only after the outage ended: %r (end %d ms)" % (offs, rel_end))
            self.assertGreaterEqual(offs[0], rel_fresh, where + "cleared at the chat's first fresh frame after the link came up, not before: %r (fresh %d ms)" % (offs, rel_fresh))
        else:
            self._hold_outcome(where + "a healthy return: ", badge, cue.get("hold"), ret, "the return", hold, require_no_paint)
        log = [e for e in (cue.get("log") or []) if e["t"] >= sus]
        self.assertTrue(log, where + "the Log line was recorded from the suspend on: %r" % (cue.get("log"),))
        entering = [e for e in log if e["t"] <= ret]
        state = entering[-1] if entering else log[0]
        self.assertEqual((state.get("shown"), state.get("text")), (True, CUE_WAIT), where + "the wait line when the page returns: %r" % (log,))
        during = [e for e in log if ret <= e["t"] < end]
        self.assertTrue(all(e.get("shown") for e in during), where + "never hidden while the outage holds: %r" % (log,))
        self.assertEqual((log[-1].get("shown"), log[-1].get("text")), (False, ""), where + "hidden at the end: %r" % (log,))
        self.assertGreaterEqual(log[-1]["t"], end, where + "...at or after the outage's end (the link up): %r" % (log,))
        texts = [e.get("text") for e in during]
        if regime == "hung" and outage_s >= 20:
            self.assertIn(CUE_HUNG1, texts, where + "the connect cut's line after the hung first try was cut: %r" % (log,))
            cut = next(e["t"] - ret for e in during if e.get("text") == CUE_HUNG1)
            self.assertGreaterEqual(cut, 15000 - 100, where + "...no sooner than the connect cut (15 s): %d" % cut)
        elif regime == "hung":
            self.assertEqual(set(texts) - {CUE_WAIT}, set(), where + "a hung outage shorter than the cut keeps the wait line: %r" % (log,))
        else:
            self.assertTrue([x for x in texts if x and x.endswith(CUE_CONNECT)], where + "a refused try's connect line: %r" % (log,))

    def _badge_text(self, where, badge):
        """The glance carries no count (romp-manager's rule of 2026-09-18): every frame that painted the badge read exactly BADGE_TEXT
        (the recorder reads textContent, so a count written through innerHTML or a child text node shows here)."""
        self.assertTrue(badge and all("text" in b for b in badge), where + "the recorder read the badge's text with each change: %r" % (badge,))
        self.assertEqual([b for b in badge if b["on"] and b["text"] != BADGE_TEXT], [], where + "the painted badge reads %r and nothing else: %r" % (BADGE_TEXT, badge))

    def _badge_clear_of_chrome(self, where, badge, need_controls=True, moves=None):
        """A painted badge covers none of the controls in the pane's chrome, the document outside its content container (finding of
        2026-10-02): at upstream's top:8px the chat's covered 78 percent of the phone header's tag filter and of its + button and the
        desktop strip's tag filter and gear, and the phone Outline's covered its tag filter and search, for the whole wait. Each
        painted record carries the badge's box and every visible chrome control's box (the recorder's chrome()); the overlap must be
        zero for each. need_controls: the pane's chrome holds controls (the chat's and the Outline's do), so a list read as empty
        fails instead of passing by default. The chrome counts what stays put when the content scrolls: the document outside the
        content container, and the sticky or fixed elements inside it with what they hold (round 1 of the review, 2026-10-03: the
        subagent viewer's header and pin, the Feed's column heads and drag chips); `moves` are the records a change to the page or
        to the badge's box added while it was painted (the recorder's), each checked the same way, so a control that appears under
        a painted badge is measured too."""
        painted = [b for b in badge if b["on"]] + list(moves or [])
        for b in painted:
            self.assertIn("box", b, where + "the painted badge's box was read: %r" % (b,))
            self.assertTrue(b.get("content"), where + "the recorder found the pane's content container: %r" % (b,))
            if need_controls:
                self.assertTrue(b.get("chrome"), where + "the pane's chrome holds controls, read: %r" % (b,))
            bx, by, bw, bh = b["box"]
            hits = []
            for c in b["chrome"]:
                x, y, w, h = c["box"]
                ix, iy = min(bx + bw, x + w) - max(bx, x), min(by + bh, y + h) - max(by, y)
                if ix > 0 and iy > 0:
                    hits.append((c["el"], c["label"], round(ix * iy / float(w * h), 2)))
            self.assertEqual(hits, [], where + "the painted badge at %r covers none of the header's controls: %r" % (b["box"], hits))

    def _tapcue(self, name, r, need_controls=False, require_no_paint=False):
        """The pane the return parked, tapped after the return (iOS item 4, finding of 2026-10-02): its corner badge read once per frame
        from the tap through its first fresh frame and a hold past it. The tap is that pane's return for the badge: no frame paints it
        sooner than the hold after the tap, and whether one paints it at all is keyed on the hold's own events (_hold_outcome): once
        when the hold's timer fired before the pane's first fresh frame, never when that frame came first. Before the fix the
        hold ran off screen, where a parked pane gets no frame, so the badge was painted there at one second and the tap showed it from
        the first frame until the pane's fresh frame, on a healthy link."""
        where = name + ": "
        hold = cue_hold_ms()
        pt = r.get("postTap") or {}
        self.assertEqual(pt.get("arm"), "armed", where + "the tapped pane's recorder armed: %r" % (pt.get("arm"),))
        rec = pt.get("rec") or {}
        tap = r["t"]["postTap"]
        fresh = [x for x in (rec.get("fresh") or []) if x >= tap]
        self.assertTrue(fresh, where + "the tapped pane stamped a fresh frame after the tap: %r" % ({k: rec.get(k) for k in ("fresh", "frames", "err")},))
        self.assertGreater(rec.get("frames", 0), 0, where + "the tapped pane's frame loop ran")
        self.assertGreaterEqual(rec.get("lastT", 0), fresh[0], where + "...through its fresh frame, so 'never painted' was read, not assumed")
        self.assertNotIn("postTapError", r, where + "the tap after the return ran: %r" % (r.get("postTapError"),))
        badge = rec.get("badge") or []
        self._badge_text(where, badge)
        self._badge_clear_of_chrome(where, badge, need_controls, moves=rec.get("moves"))
        ons = [b["t"] - tap for b in badge if b["on"] and b["t"] >= tap]
        rel_fresh = fresh[0] - tap
        type(self).measurements.setdefault(name, {})["postTapCue"] = {"pane": pt.get("pane"), "holdMs": hold, "armedOn": (rec.get("armed") or {}).get("on"),
                                                                     "paintMs": ons, "clearMs": [b["t"] - tap for b in badge if not b["on"] and b["t"] >= tap], "freshMs": rel_fresh,
                                                                     "holdEvents": [{"k": e.get("k"), "ms": e["t"] - tap, "f": e.get("f")} for e in (rec.get("hold") or []) if e.get("t", 0) >= tap]}
        self._hold_outcome(where + "a tap into a pane the return parked: ", badge, rec.get("hold"), tap, "the tap", hold, require_no_paint)

    def _hold_outcome(self, where, badge, events, t0, label, hold, require_no_paint=False):
        """Whether the badge painted after `t0` (the return, or the tap into a parked pane), keyed on the page's own events and never
        on elapsed time. `events` is the recorder's `hold` log (return_from_background_browser.mjs, cueRec): each arm and each run of
        the hold's timer (setTimeout(rpaint, RHOLD) in _pane_spin) and each romp:wsfresh, in the order they ran, each with the frame
        count at that moment. The expected outcome: the hold's timer fired before the first fresh frame after `t0`, and the page drew
        a frame between the two (the frame count moved), so the badge was up in that frame: exactly one paint, at or after that timer
        ran, cleared at or after the fresh frame. Otherwise none: the fresh frame came first and cleared the hold (a fresh frame never
        paints the badge), or the timer ran and the fresh frame came before the next frame, so the badge was set and cleared between
        two frames and was never on screen; then the timer's run must still have turned it on (the paint road ran). The time from
        `t0` to the fresh frame against the nominal hold is not the key: a timer delayed under load fires after a fresh frame that came
        past the nominal second (the full sweep of 2026-10-02: 1015 ms after the tap, no paint, correctly, and the old comparison
        expected one). Whatever the branch: no paint sooner than the hold after `t0` (the defect of 2026-10-02: a hold run off screen
        painted before the tap), and the badge is off at the end of the record (it never stays up after the fresh frame).
        require_no_paint (tests-3 of round 1): the healthy legs, whose names say no badge paints, accept only the no-paint branch. A run
        whose hold's timer ran before the fresh frame with a frame drawn between FAILS, naming the slow lab return (the fresh frame's
        time and the timer's), instead of passing on the paint branch: the leg measured no healthy return on that run, whether a
        loaded box or a regression made the return slow. It is a failure, not a skip, so CI's served job cannot turn a slower return
        into a quiet skip."""
        ons = [b["t"] - t0 for b in badge if b["on"] and b["t"] >= t0]
        self.assertEqual([x for x in ons if x < hold - 20], [], where + "no paint sooner than the %d ms hold after %s: on %r: %r" % (hold, label, ons, badge))
        events = events or []
        i_fresh = next((i for i, e in enumerate(events) if e.get("k") == "fresh" and e.get("t", 0) >= t0), None)
        self.assertIsNotNone(i_fresh, where + "the recorder heard the first fresh frame after %s: %r" % (label, events))
        fresh = events[i_fresh]
        rel_fresh = fresh["t"] - t0
        before = events[:i_fresh]
        # the precondition: the hold ran after t0 (a drop over content holds the badge; the return or the tap starts the timer).
        # Without an arm, "no paint" would witness nothing, and a renamed timer callback would silently read as a fresh frame first
        arms = [e for e in before if e.get("k") == "arm" and e.get("t", 0) >= t0]
        self.assertTrue(arms, where + "the hold's timer was armed after %s and before the fresh frame (a setTimeout of a callback named rpaint, the recorder's key): %r" % (label, events))
        fires = [e for e in before if e.get("k") == "fire" and e.get("t", 0) >= t0]
        shown = [e for e in fires if fresh.get("f", 0) > e.get("f", 0)]
        rel = lambda es: [e["t"] - t0 for e in es]
        if shown and require_no_paint:
            self.fail(where + "the return was too slow for this leg: the hold's timer ran at %r ms after %s and the first fresh frame came at %d ms, "
                      "with a frame drawn between, so the badge painted (on %r ms); this leg measures a healthy return, which needs the fresh frame first, "
                      "and this run measured none" % (rel(shown), label, rel_fresh, ons))
        if shown:
            self.assertEqual(len(ons), 1, where + "the hold's timer fired at %r ms after %s, before the fresh frame at %d ms, with a frame drawn between: one paint: %r" % (rel(shown), label, rel_fresh, badge))
            self.assertGreaterEqual(ons[0] + t0, shown[0]["t"], where + "...painted at or after the hold's timer ran (%d ms), not on another road: on %r" % (shown[0]["t"] - t0, ons))
            offs = [b["t"] - t0 for b in badge if not b["on"] and b["t"] - t0 > ons[0]]
            self.assertTrue(offs and offs[0] >= rel_fresh, where + "...cleared once, at or after the fresh frame (%d ms): %r" % (rel_fresh, badge))
        else:
            self.assertEqual(ons, [], where + "the fresh frame at %d ms after %s came before the hold's timer painted a frame (timer runs before it: %r ms; arms: %r ms): no paint: %r" % (rel_fresh, label, rel(fires), rel(arms), badge))
            self.assertEqual([e for e in fires if not e.get("on")], [], where + "...and a timer that ran before the fresh frame, with no frame drawn before the fresh frame cleared it, still turned the badge on: %r" % (events,))
        self.assertFalse(badge[-1]["on"], where + "the badge is off at the end of the record: it never stays up after the fresh frame: %r" % (badge,))

    # ---- the return's chain (the owner's decision, 2026-09-19): on the phone the redial reloads the visible tab alone ----
    def _return_chain(self, name, r, rows):
        """After the return the chat redials with reconnect=1 and the kernel re-skeletons every other tab on the new socket (the chat's
        own `skeleton` client-diag row, filed once per socket that produced a set, is the witness that there WAS something to fetch).
        On the phone the chain asks for none of them (needFull why=prefetch: zero from the return on); the other tabs load when
        tapped. On the desktop the chain runs as before and re-downloads them (at least one prefetch ask after the return)."""
        where = name + ": "
        wid = r.get("wid") or ""
        t_return_s = int((r.get("t") or {}).get("return", 0) // 1000) - 1
        skel = [x for x in rows if x.get("wid") == wid and x.get("surface") == "chat" and x.get("what") == "skeleton" and x.get("t", 0) >= t_return_s]
        self.assertTrue(skel, where + "the redial produced a skeleton set (the chat's skeleton row after the return): without one a zero prefetch count would witness nothing")
        self.assertGreater(max((x.get("data") or {}).get("n", 0) for x in skel), 0, where + "…with at least one tab withheld: %r" % ([x.get("data") for x in skel],))
        n = r.get("prefetchAfterReturn")
        self.assertIsInstance(n, int, where + "the driver counted the chain's asks after the return: %r" % (n,))
        if r.get("shell") == "phone":
            self.assertEqual(n, 0, where + "on the phone the redial reloads the visible tab alone: no background full was asked for after the return (the other tabs load when tapped)")
        else:
            self.assertGreater(n, 0, where + "on the desktop the chain re-downloads the other tabs after the return, as before")

    # ---- the feed's first paint (review round 1, regression-3; 2026-09-19): the change's central paint decision, in a real engine ----
    def _feed_paint(self, name, r, boot_tab):
        """On the phone behind another tab the feed's first frame is DELIVERED and applied (the shim's firstFrame mark is stamped) but the
        board is not painted. The hold's witness is the pane loader's own measure: `#feed-list` with no child (a paint appends `#feed-cols`,
        or `.feed-empty` over an empty model, and the loader retires on the first child), read while the model holds cards, so the loader
        stands over a HELD board and not over an empty frame; the Feed tab's first show paints it (children and cards > 0, the loader
        retired). The card count is a shape check beside it, not the witness: it read 0 under a disabled hold too (the boot's empty-board
        paint has no cards), review round 2 closeout, D6. On the desktop, and on a phone opened on the Feed tab, the first frame paints on
        its own."""
        where = name + ": "
        b = r.get("feedBeforeShow") or {}
        self.assertIsNotNone(b.get("firstFrame"), where + "the feed's first frame was delivered before the read (a read before it would say 0 for nothing): %r" % (b,))
        self.assertGreater(b.get("modelCards", -1), 0, where + "the feed's model holds cards before the read (the lab's three sessions), so an unpainted board is the hold's doing, not an empty frame's: %r" % (b,))
        if r.get("shell") == "phone" and boot_tab != "feed":
            self.assertEqual(b.get("listChildren"), 0, where + "the hold's witness: #feed-list has no child while the first paint is owed (the loader's measure; a disabled hold paints #feed-cols into the hidden pane) with %d cards in the model, behind the %s tab: %r" % (b.get("modelCards", -1), boot_tab or "chat", b))
            self.assertEqual(b.get("cards"), 0, where + "…and no card (the shape check beside the witness): %r" % (b,))
            self.assertFalse(b.get("spinGone"), where + "…so its own loader is still up (D3: it stands with no timer while the first paint is owed): %r" % (b,))
            a = r.get("feedAfterShow") or {}
            self.assertGreater(a.get("listChildren", 0), 0, where + "the Feed tab's first show painted the board into #feed-list: %r" % (a,))
            self.assertGreater(a.get("cards", 0), 0, where + "…with cards (the lab's three sessions have them): %r" % (a,))
            self.assertTrue(a.get("spinGone"), where + "…and the pane's loader retired on the paint: %r" % (a,))
            self.assertGreaterEqual(a.get("ms", -1), 0, where + "within the wait: %r" % (a,))
        else:
            self.assertGreater(b.get("cards", 0), 0, where + "the feed painted its first frame on its own (the desktop grid, or the phone's shown Feed tab): %r" % (b,))

    # ---- pass 5, the author's label (2026-09-20, taking the reviewer's round-4 finding tests-1): docState's `doc` answer witnessed in a real engine: the kernel's own stamped 200 with no shim, shown as served ----
    def _unmarked(self, name, r, rows, tap):
        """The tapped pane's document request was re-issued to the lab kernel by the driver's route and the frame fulfilled with the kernel's
        own 200, status and headers, its body with the inline shim's WHOLE <script> element removed (the one holding the marker statement
        `window.__rompApp=APP;`): a document the kernel stamped (data-romp-served=200 on its <html> tag, Handler._send's rule over every
        text/html 200 with a root tag) with no pane shim in its window, the shape of the kernel's "needs the ui/ modules" fallback page,
        through Chromium's own HTML parser. Pass 3's leg for this road was deleted with pass 4's narrowing, which left the `doc` answer
        with a hand-built stand-in as its only driver; pass 5's first cut removed the one statement, and the shim ran on to its connect()
        and redialed the kernel every ~250 ms, refused each time (the author's pass-5 verify): the document the prose called shim-less was not.
        Asserted: the route removed exactly one script element holding exactly one marker statement and a stamped root tag survived (counts,
        never the text); the premise the prose states, pinned: after the tap the pane's app dials no socket and posts no wsState word; in
        the engine the frame's document is at the pane's url, its documentElement carries data-romp-served=200 and its window has no
        __rompApp; the loader retired on the document's load (not the 30 s backstop), the src stands, no failed or loading state on the body
        or the pane div, and no pane-load-unmarked or pane-load-failed row (the reviewer's round 7, regression-1, dropped both rows with
        their keys: the loader's retirement on the load is what says the document was taken as served). The document runs no shim, so the leg's parked and
        lazy checks read a no-tap boot (out.tapped null)."""
        where = name + ": "
        u = r.get("unmarked") or {}
        self.assertEqual((u.get("stamp"), u.get("shim")), ("200", "undefined"), where + "read in the engine: the frame's root tag carries the kernel's stamp and its window has no pane shim (docState's `doc`; a re-parked pane reads no stamp, its frame back at about:blank): %r" % (u,))
        self.assertTrue(str(u.get("url") or "").endswith("/" + tap), where + "the frame's document is at the pane's url: %r" % (u,))
        wid = r.get("wid") or ""
        shell = _shell_rows(rows, wid)
        self.assertEqual(shell, [], where + "no pane-load-unmarked or pane-load-failed row: the document is shown as served and filed nowhere: %r" % (shell,))
        self.assertEqual((u.get("src"), u.get("lazy")), ("/" + tap, None), where + "the src stands, nothing re-parked: %r" % (u,))
        self.assertEqual((u.get("bodyFailed"), u.get("divFailed"), u.get("bodyLoading"), u.get("divLoading"), u.get("msg")), (False, False, False, False, ""), where + "no failed state, no loading state, no message: the document shows as served: %r" % (u,))
        self.assertGreaterEqual(r.get("loadingClearedMs", -1), 0, where + "the loading state retired within the wait: %r" % (r.get("loadingClearedMs"),))
        self.assertLess(r.get("loadingClearedMs"), 20000, where + "…on the document's load, not the 30 s backstop: %r ms" % (r.get("loadingClearedMs"),))
        ls = r.get("loaderSeen") or {}
        self.assertEqual(ls.get("display"), "flex", where + "the loader painted at the tap, before the document answered: %r" % (ls,))
        self.assertIn("/" + tap, r.get("frames") or [], where + "the frame is at the pane's url at the suspend: %r" % (r.get("frames"),))
        # the input's derivation, read off the route (counts of what it handed over, never the text): the kernel's 200, one marker statement
        # removed (zero would have handed over the pane's own document, `app`), the stamp on the root tag intact
        rt = r.get("unmarkedRoute") or {}
        self.assertEqual(rt.get("status"), 200, where + "the kernel answered the pane's request 200 (the stored cookie rode as ever): %r" % (rt,))
        self.assertTrue(str(rt.get("contentType") or "").startswith("text/html"), where + "…text/html: %r" % (rt,))
        self.assertEqual(rt.get("scriptsStripped"), 1, where + "the route removed exactly one script element, the inline shim's: %r" % (rt,))
        self.assertEqual(rt.get("stripped"), 1, where + "…which held exactly one marker statement (zero would mean the pane's own document, `app`): %r" % (rt,))
        # the script elements, all of them and the bundles' src ones, counted before and after the strip: the page carries inline script
        # elements besides the shim's (its loader's, and since main's fork PR #919 the page-key script), so a count of every script element
        # above one did not show a bundle, and the shim-pattern count above does not show that nothing else went with the shim's element
        self.assertGreater(rt.get("srcScripts") or 0, 0, where + "the page carried the bundles' src script elements: %r" % (rt,))
        self.assertEqual(rt.get("srcKept"), rt.get("srcScripts"), where + "...and every one stayed through the strip: %r" % (rt,))
        self.assertEqual(rt.get("scriptsKept"), (rt.get("scripts") or 0) - 1, where + "...and so did every other script element, the inline ones (the page-key script, the loader's) among them: the strip removed one element in all, the shim's: %r" % (rt,))
        self.assertEqual(rt.get("stampedTags"), 1, where + "…and the kernel's stamp on the <html> tag survived the strip, once: %r" % (rt,))
        # the premise, pinned (the author's pass-5 verify): no shim ran in the document, so the pane's app dialed no socket and posted no wsState word
        # after the tap. With the marker alone removed the shim connected and redialed every ~250 ms, refused each time: a perturbation the
        # prose denied, and one the leg's kernel-ledger reads could not see (the kernel accepted none of those sockets)
        t_tap = (r.get("t") or {}).get("tap") or 0
        self.assertGreater(t_tap, 0, where + "the tap is stamped: %r" % (r.get("t"),))
        late_dials = [d for d in (r.get("dials") or []) if d.get("app") == tap and d.get("t", 0) >= t_tap]
        self.assertEqual(late_dials, [], where + "no socket dial for the tapped pane's app after the tap (the shim, had it run, dials at parse and redials when refused): %r" % (late_dials,))
        late_words = [w for w in (r.get("wsWords") or []) if w.get("app") == tap and w.get("t", 0) >= t_tap]
        self.assertEqual(late_words, [], where + "no wsState word from the tapped pane after the tap (the shim posts one on every open and close): %r" % (late_words,))

    # ---- review round 4 (2026-09-19, kernel-1 and tests-1): the kernel's OWN denial at a pane url is a failure with the retry road, never shown as served ----
    def _denied(self, name, r, rows, tap):
        """The tapped pane's one document request was re-issued to the lab kernel with an explicit empty Cookie header (the driver's route, through
        route.fetch: the one form every engine lets keep the stored cookie off the wire) and the frame fulfilled with the kernel's own answer, so
        the REAL kernel answered as it does for a token-gated route with no credential: 403, text/plain, a body that names the serve-token
        file's path, and that is what the frame received, status, headers and bytes. Pass 3
        showed any same-origin document as served, which painted that body as the pane with no retry road for the page's life, and its leg
        fulfilled a hand-written stand-in, so no test met the real one. The pass-2 rule is scoped to a 200 the kernel served; the kernel
        now stamps every text/html 200 whose body has an <html> tag (data-romp-served=200 on that tag) and the shell's docState shows as served only a document
        carrying it. Asserted, on top of _abort's failed-state and re-tap checks: the status the kernel answered was 403 (read off the
        response event; the body is never read, printed or kept, by the driver or here), the failed overlay is painted opaque and fixed over
        the pane's whole box (the document under it is not on show), and the detector was the load
        listener (the 403 commits a document and fires load in every engine)."""
        where = name + ": "
        a = r.get("abort") or {}
        d = a.get("denied") or {}
        self.assertGreaterEqual(d.get("responses", 0), 1, where + "the pane's document request reached the kernel and was answered (the route re-issued it credential-less and handed the answer to the frame): %r" % (d,))
        self.assertEqual(d.get("status"), 403, where + "the kernel's own answer to the credential-less request at the pane's url: 403 (a 200 here means the stored cookie reached the wire, and the leg met no denial): %r" % (d,))
        ov = a.get("overlay") or {}
        fr = a.get("frame") or {}
        self.assertTrue(ov, where + "the overlay's box was read in the failed state: %r" % (a,))
        self.assertEqual((ov.get("position"), ov.get("zIndex")), ("fixed", "15"), where + "the overlay is the fixed, stacked element of the phone layout's failed state: %r" % (ov,))
        self.assertTrue(str(ov.get("bg", "")).startswith("rgb(") or str(ov.get("bg", "")).endswith(", 1)"), where + "…painted opaque (no alpha under 1): %r" % (ov,))
        self.assertEqual(fr.get("display"), "block", where + "the pane's frame is the shown tab's (display block on the phone), so covering it is the claim that matters: %r" % (fr,))
        self.assertGreater(fr.get("bottom", 0), fr.get("top", 0), where + "the frame has a box to cover: %r" % (fr,))
        self.assertTrue(ov.get("top", 1e9) <= fr.get("top", 0) + 1 and ov.get("bottom", -1e9) >= fr.get("bottom", 1e9) - 1 and ov.get("left", 1e9) <= fr.get("left", 0) + 1 and ov.get("right", -1e9) >= fr.get("right", 1e9) - 1,
                        where + "the overlay covers the frame's whole box (to the pixel): the denial's document is not on show: overlay %r, frame %r" % (ov, fr))
        self.assertLess(a.get("ms", -1), 20000, where + "the load listener judged the denial: the failed state painted within 20 s of the tap, never at the 30 s backstop: %r" % (a,))

    # ---- HIGH 2 (review round 1, 2026-09-19): a lazy pane whose first document fetch fails is re-parked, says so, and loads on the re-tap ----
    def _abort(self, name, r, rows, tap, engine, mode="abort", retry_enter=False):
        """The tapped pane's document fetch failed at the first tap: aborted by the route (mode abort), or answered by the real kernel's
        403 to a request stripped of its cookie (mode denied, review round 4; _denied below adds its own checks). The shell must paint the failed state where the user looks
        (body.pane-failed keeps #pane-load up at display:flex with the message and the loader down), re-park the pane (no src, the
        url back under data-lazy-src) and file no row (the reviewer's round 7, regression-1, dropped pane-load-failed with its keys); the
        re-tap then loads it (the frame at the pane's url, its shim up, the failed state gone). Chromium detects the failure on the error
        page's load event, so the failed state paints within 20 s of the tap; Firefox and WebKit fire no load event the shell can act on
        for the aborted navigation (the frame keeps about:blank), so the 30 s backstop detects it and the failed state paints 30 s after
        the tap, which is what the WebKit leg's wait is for (the rows' `via` said which detector ran; the page's own clock says it now).
        (Pass 3 showed any same-origin document at the url as served; pass 4 narrowed that to a 200 the kernel stamped, so the
        kernel's own 403 is a failure again, driven for real in the denied mode.)"""
        where = name + ": "
        a = r.get("abort") or {}
        self.assertEqual(a.get("mode"), mode, where + "the driver ran the leg's failure mode: %r" % (a,))
        self.assertGreaterEqual(a.get("ms", -1), 0, where + "the shell said the pane failed (body.pane-failed) within the wait: %r" % (a,))
        self.assertEqual(a.get("display"), "flex", where + "#pane-load is painted in the failed state: %r" % (a,))
        self.assertEqual(a.get("loaderDisplay"), "none", where + "…with the loader itself down: %r" % (a,))
        self.assertEqual(a.get("msg"), "Couldn't load this pane.", where + "the first failure's copy (the affordance is the button's text, review round 3): %r" % (a,))
        # ui-1 (review round 3): the retry is a real, keyboard-reachable button, painted in the failed state and hidden again once the re-tap loads
        rb = a.get("retry") or {}
        self.assertEqual((rb.get("text"), rb.get("hidden"), rb.get("role")), ("Try again", False, "alert"), where + "the button is shown with its name, and the message is announced: %r" % (rb,))
        self.assertNotEqual(rb.get("display"), "none", where + "…painted: %r" % (rb,))
        self.assertGreaterEqual(rb.get("tabIndex", -1), 0, where + "…in the tab order: %r" % (rb,))
        self.assertIs(rb.get("focusable"), True, where + "…and takes keyboard focus (focus() lands on it) in every engine: %r" % (rb,))
        if engine != "firefox":   # playwright's Firefox hands Tab to the browser chrome at the document's last focusable element and never wraps back in (the driver's comment records the probe), so the walk is a witness on Chromium and WebKit; the trail is recorded on every engine
            self.assertGreaterEqual(a.get("tabsToReach", -1), 1, where + "…and reached from the body by the keyboard (Tab presses until document.activeElement is the button): %r, the trail %r" % (a.get("tabsToReach"), a.get("tabTrail")))
        else:
            self.assertIsInstance(a.get("tabTrail"), list, where + "the Firefox walk is recorded (its Tab leaves the document): %r" % (a.get("tabTrail"),))
        self.assertEqual((a.get("src"), a.get("lazy")), (None, "/" + tap), where + "the pane is re-parked (no src, the url back under data-lazy-src): %r" % (a,))
        self.assertFalse(a.get("loading"), where + "the loading state is over: %r" % (a,))
        if retry_enter:
            # ui-1 (review round 4, 2026-09-19): the keyboard's retry keeps its focus. The driver focused the button and pressed Enter (its click:
            # the retry); paintLoading hid the button while the retry loaded, which drops focus to the body in every engine; the route failed the
            # fetch again and the failed paint that shows the button again must have put focus back on it (before: BODY, and no way back to the
            # button but the Tab walk). The re-failure is the episode's second, so its copy is the second.
            re_ = a.get("retryEnter") or {}
            self.assertGreaterEqual(re_.get("ms", -1), 0, where + "Enter on the focused Try again button retried, and the pane failed again within the wait (the second copy painted): %r" % (re_,))
            self.assertEqual(re_.get("msg"), "Still not loading. Try again, or reload the page.", where + "the episode's second failure's copy: %r" % (re_,))
            self.assertIs(re_.get("hidden"), False, where + "the button is shown again in the failed state: %r" % (re_,))
            self.assertEqual(re_.get("active"), "BUTTON#pane-load-retry", where + "…and holds the keyboard focus after the re-failure (the failed paint that shows it again puts focus back on the control that retried): %r" % (re_,))
        wid = r.get("wid") or ""
        shell = _shell_rows(rows, wid)
        self.assertEqual(shell, [], where + "no pane-load-failed or pane-load-unmarked row: the failure is shown where the user looks and filed nowhere: %r" % (shell,))
        if mode == "denied" or engine == "chromium":
            self.assertLess(a.get("ms", -1), 20000, where + "the load listener is the detector (Chromium commits an error page for the abort and fires load; the kernel's 403 commits a document in every engine): the failed state painted within 20 s of the tap, not at the 30 s backstop: %r" % (a,))
        else:
            self.assertGreaterEqual(a.get("ms", -1), 29000, where + "Firefox and WebKit fire no load event the shell can act on for the aborted navigation (the frame keeps about:blank), so the 30 s backstop is the detector: the failed state painted 30 s after the tap: %r" % (a,))
        if retry_enter:
            self.assertLess((a.get("retryEnter") or {}).get("ms", -1), 20000, where + "the re-failure, judged by the load listener too: its copy painted within 20 s of the Enter: %r" % (a.get("retryEnter"),))
        la = r.get("loadingAfterTap") or {}
        self.assertFalse(la.get("failed"), where + "the re-tap cleared the failed state: %r" % (la,))
        self.assertIs(la.get("retryHidden"), True, where + "…and the retry button is hidden again after the re-tap's load: %r" % (la,))
        self.assertEqual(la.get("failedPanes"), [], where + "no .pane carries `failed` after the re-tap: %r" % (la,))
        self.assertIn("/" + tap, r.get("frames") or [], where + "the re-tap loaded the pane's document (the frame at its url): %r" % (r.get("frames"),))

    # ---- the start gate's witness (review round 3, 2026-09-19, fresh-2): the chain waits for the active tab's full, with the chat ON SCREEN ----
    def _gate(self, name, r):
        """The gate's central claim, above the pure function: no background ask leaves before the visible tab's full has applied. The one
        served assertion that named it (prefetchBeforeTap, the boot-on-Feed legs) is carried by paneHidden() alone (the chat display:none),
        so this leg boots ON the chat tab (paneHidden() false) with an active tab stored (a skeleton set to prefetch), and the driver's
        proxy HOLDS the boot chat dial's frames naming that tab for cfg.holdActiveFullMs while the strip and the statuses pass: the strip's
        first paint arms the chain, the chat is visible, and the gate is the only thing that can hold the first prefetch. Asserted: the
        hold happened (the precondition, guarded: a derived expectation over nothing is no witness), no prefetch left before the release
        (a wire-time stamp on the proxy, so a prefetch inside the hold is unambiguous), and one left after it within the driver's wait
        (the gate opened on the full: the frame half). The mutation of record: nextPrefetch without its gate term asks inside the hold."""
        where = name + ": "
        boot_chat = [d for d in (r.get("dials") or []) if d.get("app") == "chat" and d.get("phase") == "boot"]
        self.assertTrue(boot_chat, where + "the chat pane dialed at boot")
        d = boot_chat[0]
        self.assertTrue(d.get("skeleton"), where + "the boot dial carries skeleton=1 (a set to prefetch exists): %r" % (d,))
        held, rel = d.get("held") or {}, d.get("heldRelease") or {}
        self.assertEqual(held.get("id"), SESSIONS[0][0], where + "the proxy held a frame naming the active tab (the precondition): %r" % (held,))
        self.assertGreater(rel.get("n", 0), 0, where + "…and released at least one held frame after the hold: %r" % (rel,))
        self.assertGreaterEqual(rel.get("t", 0) - held.get("t", 0), 1000, where + "the hold stood for about the configured time: held %r released %r" % (held, rel))
        asks = d.get("needFullT") or []
        early = [x for x in asks if x.get("why") == "prefetch" and x.get("t", 0) < rel["t"]]
        self.assertEqual(early, [], where + "no background full was asked for before the active tab's full was even on the wire, with the chat on screen: the gate alone held it (asks: %r)" % (asks,))
        g = r.get("gate") or {}
        self.assertGreaterEqual(g.get("prefetchAfterReleaseMs", -1), 0, where + "the chain asked for a background full once the active tab's full applied (the gate opened on the frame): %r; asks %r" % (g, asks))

    # ---- stage 0's dial pins (review round 1, 2026-09-19): the phone's first chat dial takes the diet; the chain waits for the chat pane's show ----
    def _dial(self, name, r, boot_tab, tap):
        """The phone's first chat dial carries skeleton=1 (the kernel serves one full plus statuses), the desktop's does not (F5's rule end to
        end); and on a phone opened on another tab the chat pane's idle prefetch asks for nothing while the chat is display:none and asks
        for its first background full once the Chat tab is shown (F1's outcome). The re-arm roads are render.ts's, the visibility
        publisher's show hook and the panes word's belt; what each engine's leg pins is what its single-road runs showed, never the two
        roads credited to a leg as a pair: the Chromium leg and the WebKit leg each red only with both roads removed and neither
        witnesses a road alone, the Firefox leg pins the outcome alone, and each road's executed witness is another test (the pointers
        are in the comment above test_phone_opened_on_the_feed_tab_arms_the_chain_when_chat_is_shown)."""
        where = name + ": "
        boot_chat = [d for d in (r.get("dials") or []) if d.get("app") == "chat" and d.get("phase") == "boot"]
        self.assertTrue(boot_chat, where + "the chat pane dialed at boot")
        if r.get("shell") == "phone":
            self.assertTrue(boot_chat[0].get("skeleton"), where + "the phone's first chat dial carries skeleton=1: %r" % (boot_chat[0],))
        else:
            self.assertFalse(any(d.get("skeleton") for d in boot_chat), where + "the desktop's chat dials whole, as before: %r" % (boot_chat,))
        if r.get("activeSid"):
            # the stored tab after the boot (review round 3, extra9-1): active and whole (the diet's one full; a transcript-less tab is never a
            # skeleton), the four lab sessions on the strip; behind another tab the chain has not run, so the skeletons at the settle are
            # exactly the other transcript-bearing tabs (the strip read is the witness that the `docs` full arrived and was applied)
            strip = r.get("chatStrip") or []
            self.assertTrue(strip, where + "the chat strip was read after the settle")
            self.assertEqual(sorted(t["id"] for t in strip), sorted(x[0] for x in SESSIONS), where + "the lab's sessions are on the strip: %r" % (strip,))
            act = [t for t in strip if t.get("active")]
            self.assertEqual([t["id"] for t in act], [r["activeSid"]], where + "the stored tab is the active one: %r" % (strip,))
            self.assertFalse(act[0].get("skeleton"), where + "…and whole, not a skeleton: %r" % (act,))
            n = (r.get("chatSessions") or {}).get(r["activeSid"])
            self.assertIsInstance(n, int, where + "the stored tab's full was delivered to the chat pane (its event count recorded): %r" % (r.get("chatSessions"),))
            self.assertGreaterEqual(n, 0, where + "%r" % (r.get("chatSessions"),))
            if boot_tab:
                want = sorted(x[0] for x in TRANSCRIPT_SESSIONS if x[0] != r["activeSid"])
                self.assertTrue(want, where + "the transcript-bearing others are not an empty set")
                self.assertEqual(sorted(t["id"] for t in strip if t.get("skeleton")), want, where + "behind the %s tab the chain has not run: every other transcript-bearing tab is still a skeleton at the settle: %r" % (boot_tab, strip))
        if boot_tab and tap == "chat":
            cv = r.get("chatVisibility") or {}
            self.assertEqual(cv.get("observer"), "function", where + "the chat document has its IntersectionObserver (the hook's road exists): %r" % (cv,))
            # carried by paneHidden() (nextPrefetch's `hidden` term), not by the start gate: the chat is display:none here, so this reads 0 with
            # the gate term removed too (the refuters' converse mutation, review round 1); the gate's own witness is _gate, the held-full leg
            self.assertEqual(r.get("prefetchBeforeTap"), 0, where + "no background full left while the chat pane was display:none behind the %s tab" % boot_tab)
            self.assertGreaterEqual(r.get("prefetchAfterChatTapMs", -1), 0, where + "the Chat tab's show re-armed the idle chain: a prefetch ask left the chat socket (ms after the tap: %r)" % r.get("prefetchAfterChatTapMs"))

    # ---- stage 0's count pin (2026-09-18): the lazy panes' cold-open counts, and the tab-tap leg ----
    def _lazy(self, name, r, m, tap):
        """T1 and T6, end to end (stage 0, 2026-09-18). On the phone the Outline, the Sessions band, the Waiting pane and the Files pane have
        no src, no document and no socket at boot: the kernel's wsopen rows before the suspend name the eager panes alone, no lazy pane's shim says
        a word, and the iframes read no src. The cold open's counts (documents, sockets, dials) drop by the four lazy panes; the
        desktop's do not. The tab-tap leg taps one lazy pane: its document loads on the tap (its src set, the shell's loader up while
        it loads), its shim says up, and at the return, off screen behind the chat, it parks like any pane (D2)."""
        where = name + ": "
        shell = r.get("shell")
        src = r.get("srcAtBoot") or {}
        self.assertEqual(sorted(src), sorted(APPS + ("settings",)), where + "every pane iframe is in the served page, lazy or not: %r" % (src,))
        if shell == "phone":
            for app in LAZY_PHONE:
                self.assertIsNone(src.get(app), where + "a lazy pane has no src at boot on the phone: %r" % (src,))
                self.assertNotIn(app, r.get("wsWordsAtBoot") or [], where + "…and its shim said nothing before the tap (no document): %r" % (r.get("wsWordsAtBoot"),))
                if app != tap:   # the tapped pane's one socket, after its tap, is counted below
                    self.assertNotIn(app, m["wsopenBoot"], where + "…so the kernel accepted no socket from it before the suspend (wsopen by app: %r)" % (m["wsopenBoot"],))
            self.assertEqual(sorted(_eager("phone")), ["chat", "feed"], where + "the phone's eager set is the chat and the feed (a literal, so the loops below cannot run over nothing)")
            for app in _eager("phone"):
                self.assertEqual(src.get(app), "/" + app, where + "an eager pane has its page at boot: %r" % (src,))
            self.assertEqual(sorted(k for k in m["wsopenBoot"] if k != "shell"), sorted(_eager("phone", tap)), where + "the kernel's boot pane sockets are the eager panes' (plus a tapped one's; the shell dials its own): %r" % (m["wsopenBoot"],))
        else:
            for app in APPS:
                self.assertEqual(src.get(app), "/" + app, where + "the desktop loads every pane at boot, as before: %r" % (src,))
            self.assertEqual(sorted(k for k in m["wsopenBoot"] if k != "shell"), sorted(APPS), where + "…one boot pane socket each (the shell dials its own): %r" % (m["wsopenBoot"],))
        if tap:
            self.assertGreaterEqual(r.get("tapUpMs", -1), 0, where + "the tapped pane's shim said up after the tap (its document loaded on it): %r" % r.get("tapUpMs"))
            self.assertEqual((r.get("srcAfterTap") or {}).get(tap), "/" + tap, where + "the tap set its src: %r" % (r.get("srcAfterTap"),))
            self.assertEqual(m["wsopenBoot"].get(tap), 1, where + "one socket from it, after the tap: %r" % (m["wsopenBoot"],))
            # the loading state retires on the iframe's load event; the driver waits for the retirement after the socket is up (a pane
            # with a large bundle, the Waiting and Files panes, loads after its shim dialed) and stamps it: the load event, never the 30 s
            # backstop, which clears the loader for a slow document too (review round 3, extra9-2)
            self.assertGreaterEqual(r.get("loadingClearedMs", -1), 0, where + "the tapped pane's loading state retired within the wait: %r" % (r.get("loadingClearedMs"),))
            self.assertLess(r.get("loadingClearedMs"), 20000, where + "…on the document's load event, not the 30 s backstop: %r ms" % (r.get("loadingClearedMs"),))
            la = r.get("loadingAfterTap") or {}
            self.assertIn("panes", la, where + "the loading state was read after the tap: %r" % (la,))
            self.assertNotIn(tap + "-pane", la.get("panes") or [], where + "its document loaded, so its .pane no longer carries the loading class: %r" % (la,))
            self.assertFalse(la.get("body"), where + "…and the shell's loader is down: %r" % (la,))
            # THE FIRST TAP'S WITNESS (review round 3, tests-1): the headline road in a real engine. Before this every browser leg that tapped a
            # lazy pane aborted its first fetch, so a lazy pane was witnessed only as a second promotion after a failure. Now every leg that taps
            # a pane with NO document at boot (a lazy pane) reads the pane DOCUMENT's own load event (a listener armed before the tap that
            # loaded it), the loading state's retirement AT that load (the page's own stamp, never the 30 s backstop), and the pane PAINTED (its
            # own loader retired, its app element with children); the no-abort legs (Waiting and Files in Chromium, the Outline in WebKit)
            # witness the FIRST tap with no route in the way, the abort legs the re-tap's load. An eager pane's tap is a SHOW, not a load (the
            # boot-on-Feed legs tap the chat, whose document loaded at boot): no load event follows it and there is nothing to stamp, so the
            # block is gated on the tapped pane's boot state (the touched-tests verifier's finding, review round 3: ungated, it red the three
            # boot-on-Feed legs on every engine)
            if tap not in _eager(shell):
                self.assertGreaterEqual(r.get("docLoadMs", -1), 0, where + "the pane's document fired its own load event after the tap that loaded it: %r" % (r.get("docLoadMs"),))
                self.assertTrue(str(r.get("docLoadUrl") or "").endswith("/" + tap), where + "…for the pane's page: %r" % (r.get("docLoadUrl"),))
                # the retirement is the PAGE's stamp: a MutationObserver over the body's and the pane div's class lists, armed with the load
                # listener before the tap, stamps the first moment the loading state it saw painted is gone. Both stamps are the page's, taken
                # in the load event's own dispatch (the driver's listener, then the shell's, then the observer's microtask), so the gap between
                # them is that dispatch and not the driver's poll cadence, which set the old bound's slack (a poll that starts after the
                # socket-up poll can lag a fast load by more than a read on a loaded box)
                lr, dl = r.get("loadingRetiredMs", -1), r.get("docLoadMs")
                self.assertGreaterEqual(lr, 0, where + "the page's observer saw the loading state painted at the tap and then retired: %r" % (lr,))
                self.assertGreaterEqual(lr, dl, where + "the loading state retired at the document's load, not before it: retired %r ms, load %r ms" % (lr, dl))
                self.assertLessEqual(lr - dl, 250, where + "…in the load event's own dispatch, not on a later timer or event: retired %r ms, load %r ms" % (lr, dl))
                pt = r.get("painted") or {}
                self.assertGreaterEqual(pt.get("ms", -1), 0, where + "the pane painted within the wait: %r" % (pt,))
                self.assertGreater(pt.get("count", -1), 0, where + "…its app element (%s) has children: %r" % (pt.get("el"), pt))
                self.assertNotEqual(pt.get("spinGone"), False, where + "…and its own loader retired (or the page carries none, the Files pane): %r" % (pt,))
            if shell == "phone" and tap in LAZY_PHONE:
                # ui-2 (review round 1): the shell's loader PAINTS, read by an observer armed before the tap the moment body.pane-loading
                # was added: display flex, a box of some height, above the tab bar, with the romp loader inside it
                ls = r.get("loaderSeen") or {}
                self.assertEqual(ls.get("display"), "flex", where + "the shell's loader painted when the pane started loading: %r" % (ls,))
                self.assertEqual(ls.get("loaderDisplay"), "flex", where + "…with the romp loader inside it: %r" % (ls,))
                self.assertGreater(ls.get("height", 0), 0, where + "…with a box: %r" % (ls,))
                self.assertLessEqual(ls.get("bottom", 1e9), ls.get("barTop", 0) + 1, where + "…that stops at the tab bar (the bar stays tappable): %r" % (ls,))

    # ---- D2's count pin (2026-09-18): which panes parked, through the wsState words the driver recorded ----
    def _parked(self, name, r, m):
        """Hidden panes park their return redial on the phone (D2, 2026-09-18). Pinned through the shell's wsState words the
        driver recorded, not the panes' `return` rows: a parked pane's row is queued on its down socket and reaches the kernel
        only at a tap, which these legs never make. On the phone every pane but two says `parked` exactly once after the return
        and the kernel accepts no socket from it; the visible chat dials as before, and so does the FEED, exempt from parking by
        the user's ruling of 2026-09-18 (its socket carries the card-trouble entries the shell's bell mirrors, and the bell
        surfaces trouble the user was not looking at; one extra redial per return is the accepted cost), keyed on the app alone.
        Both dialing panes file `return` rows saying parked:false. On the desktop nothing parks: no pane says `parked`, every
        pane's return row says parked:false, and every pane files one (the desktop leg's 7 dials, the shell's and six panes')."""
        where = name + ": "
        t_return = (r.get("t") or {}).get("return", 0)
        words = [w for w in (r.get("wsWords") or []) if w.get("t", 0) >= t_return]
        parked_apps = sorted({w.get("app") for w in words if w.get("state") == "parked"})
        if r.get("shell") == "phone":
            dialing = {VISIBLE, "feed"}
            if r.get("tapped") in LAZY_PHONE:
                expected = sorted(set(_eager("phone", r.get("tapped"))) - dialing)
                self.assertTrue(expected, where + "a leg that tapped a lazy pane expects it parked (the derivation yielded nothing: tapped %r)" % (r.get("tapped"),))   # review round 1 (tests-1): a derived-empty expectation is not a witness
                self.assertEqual(parked_apps, expected, where + "the tapped pane, loaded before the suspend and off screen at the return, parks; the visible chat and the exempt feed dial (parked words: %r)" % (parked_apps,))
            else:
                self.assertEqual(parked_apps, [], where + "no lazy pane loaded (a tap on the chat is a tap on an eager pane): nothing parks, a lazy pane has no shim to park (parked words: %r)" % (parked_apps,))
            for app in parked_apps:
                self.assertEqual([w.get("state") for w in words if w.get("app") == app].count("parked"), 1, where + "%s says parked once: %r" % (app, words))
                self.assertNotIn(app, m["wsopenReturn"], where + "a parked pane dials nothing at the return (kernel wsopen by app: %r)" % (m["wsopenReturn"],))
            for app in sorted(dialing):
                self.assertIn(app, m["wsopenReturn"], where + "%s dials at the return (kernel wsopen by app: %r)" % (app, m["wsopenReturn"]))
                rows = m["return"].get(app) or []
                self.assertTrue(rows, where + "%s filed a return row: %r" % (app, m["return"]))
                self.assertEqual([row.get("parked") for row in rows], [False] * len(rows), where + "%s return rows say parked:false: %r" % (app, rows))
        else:
            self.assertEqual(parked_apps, [], where + "nothing parks on the desktop (parked words: %r)" % (parked_apps,))
            self.assertEqual(sorted(m["return"]), sorted(APPS), where + "every pane filed a return row: %r" % (sorted(m["return"]),))
            for app, rows in m["return"].items():
                self.assertEqual([row.get("parked") for row in rows], [False] * len(rows), where + "%s return rows say parked:false: %r" % (app, rows))

    # ---- shapes only: rows present, fields typed, counts recorded; never a count pinned (the PR plan tightens them) ----
    def _shapes(self, name, r, m, regime):
        where = name + ": "
        self.assertTrue(r.get("wid"), where + "the dashboard minted its id (sessionStorage romp:wid): %r" % r.get("wid"))
        self.assertEqual(m["overrideErrors"], [], where + "the visibility override installed in every document")
        self.assertFalse([d for d in (m["installed"] or []) if d.endswith(":MISSING")], where + "every document carries the override before the suspend: %r" % (m["installed"],))
        for app, rows in m["return"].items():
            for row in rows:
                self.assertGreaterEqual(row.get("hiddenMs", -1), 0, where + "%s saw the emulated hide (hiddenMs stamped): %r" % (app, row))
        # the precondition of the measurement: every pane socket was up before the suspend (a pane that never connected
        # would file no return row and the storm would be undercounted)
        eager = _eager(r.get("shell"), r.get("tapped"))   # the panes with a document at the suspend: the boot's, plus one a leg tapped
        self.assertGreaterEqual(len(eager), 2, where + "the eager set holds at least the chat and the feed: %r" % (eager,))   # a derivation that yields nothing must not pass the comparisons below
        self.assertEqual(sorted(r.get("bootUpApps") or []), sorted(_eager(r.get("shell"))),
                         where + "every eager pane's shim said wsState up at boot, and no lazy pane said anything (the boot wait ends before any tap): %r (frames %r)" % (r.get("bootUpApps"), r.get("frames")))
        self.assertGreaterEqual(r.get("closedAtSuspend", 0), len(eager),
                                where + "the driver held one passed-through socket per pane to close at the suspend: %r" % r.get("closedAtSuspend"))
        self.assertEqual(r.get("mobileShell"), r.get("shell") == "phone", where + "the shell the viewport selects: %r" % r.get("bodyClass"))
        # the return rows: one decision per pane document that had connected, typed
        self.assertIn(VISIBLE, m["return"], where + "the visible pane filed a return row: %r" % (m["return"],))
        for app, rows in m["return"].items():
            for row in rows:
                self.assertIn(row.get("decision"), DECISIONS, where + "%s return.decision: %r" % (app, row))
                self.assertIsInstance(row.get("hiddenMs"), int, where + "%s return.hiddenMs is an int: %r" % (app, row))
                self.assertIsInstance(row.get("resumed"), bool, where + "%s return.resumed is a bool: %r" % (app, row))
        # the wait for current content: the visible pane's first fresh frame after the return, typed
        self.assertIn(VISIBLE, m["returnFresh"], where + "the visible pane filed return-fresh (fresh seen: %r; return rows %r; kernel log tail: %s)"
                      % (r.get("freshSeenMsAfterOutage"), m["return"], Path(self.klog).read_text()[-600:]))
        for app, rows in m["returnFresh"].items():
            for row in rows:
                self.assertIsInstance(row.get("ms"), int, where + "%s return-fresh.ms is an int: %r" % (app, row))
                self.assertGreaterEqual(row["ms"], 0, where + "%s return-fresh.ms is non-negative: %r" % (app, row))
                self.assertIsInstance(row.get("bytesSince"), int, where + "%s return-fresh.bytesSince is an int: %r" % (app, row))
                self.assertIsInstance(row.get("redialed"), bool, where + "%s return-fresh.redialed is a bool: %r" % (app, row))
        # the handshakes that never opened, one row per pane per open, typed (their count is the baseline, not a pin)
        for app, rows in m["wsconnfail"].items():
            for row in rows:
                self.assertIsInstance(row.get("attempts"), int, where + "%s wsconnfail.attempts is an int: %r" % (app, row))
                self.assertGreaterEqual(row["attempts"], 1, where + "%s wsconnfail.attempts counts at least one: %r" % (app, row))
                self.assertIsInstance(row.get("firstFailMs"), int, where + "%s wsconnfail.firstFailMs is an int: %r" % (app, row))
        # the storm as the kernel saw it: wsopen rows per app, at boot and in the return window, typed
        self.assertIn(VISIBLE, m["wsopenBoot"], where + "the kernel filed a wsopen row for the visible pane's first socket: %r" % (m["wsopenBoot"],))
        self.assertIn(VISIBLE, m["wsopenReturn"], where + "the kernel accepted the visible pane's redial after the return: %r" % (m["wsopenReturn"],))
        for app, rows in m["wsopenReturnRows"].items():
            for row in rows:
                self.assertIsInstance(row.get("kind"), str, where + "%s wsopen.kind is a string: %r" % (app, row))
                self.assertIsInstance(row.get("reconnect"), bool, where + "%s wsopen.reconnect is a bool: %r" % (app, row))
        # the outage regime held: the dials the page made after the return met the regime's verdict, and the passed ones came after it
        verdicts = m["dialsAfterReturn"]["byVerdict"]
        self.assertGreaterEqual(m["dialsAfterReturn"]["total"], 1, where + "the return dialed: %r" % (m["dialsAfterReturn"],))
        if regime == "refused":
            self.assertIn("refused", verdicts, where + "the refused regime refused a dial: %r" % (verdicts,))
            self.assertNotIn("hung", verdicts, where + "no dial hangs in the refused regime: %r" % (verdicts,))
        else:
            self.assertTrue(set(verdicts) & {"hung-released", "hung-cut"}, where + "the hung regime held a dial: %r" % (verdicts,))
            self.assertNotIn("refused", verdicts, where + "no dial is refused in the hung regime: %r" % (verdicts,))
            self.assertNotIn("hung", verdicts, where + "every hung dial was released or cut by the outage's end: %r" % (verdicts,))
        # the order the documents' handlers ran, recorded for the note. Asserted: both transitions were dispatched and reached the
        # shell document and the visible pane's frame, and the hidden dispatch reached every frame the page held. The order
        # itself is the driver's (top first, frames in tree order), so it is recorded, not pinned. (The engines also fire a real
        # visibilitychange in a frame's initial about:blank document at boot; those records predate the suspend and stay in
        # visRecords, outside the order.)
        order = m["visibilitychangeOrder"]
        self.assertEqual(sorted(order), ["hidden", "visible"], where + "both transitions dispatched: %r" % (order,))
        for state, docs in order.items():
            self.assertIn("top", docs, where + "%s reached the shell document: %r" % (state, docs))
            self.assertIn("f-" + VISIBLE, docs, where + "%s reached the visible pane's frame: %r" % (state, docs))
        self.assertEqual(m["hiddenDispatch"], m["frames"], where + "the hidden dispatch reached every frame the page held: %r vs %r" % (m["hiddenDispatch"], m["frames"]))
        # the artifact: written under the lab, JSON, with the measurement's keys
        art = json.loads(Path(os.path.join(self.lab, "return-harness-%s.json" % name)).read_text())
        for key in ("return", "returnFresh", "wsconnfail", "watchdogClose", "hostconn", "shellReturnProbe", "wsopenBoot",
                    "wsopenReturn", "dialsAfterReturn", "visibilitychangeOrder", "perf"):
            self.assertIn(key, art, where + "the artifact carries %s" % key)

    # ---- the legs: the phone (the measured device) in both regimes at both intervals; the desktop at 12 s, its 30 s legs opt-in ----
    def test_phone_refused_12s(self):
        self._leg("phone", "refused", 12)
    # iOS item 4 (2026-10-02): the healthy return. The hung regime with no outage: the dials the suspend left pending and the
    # return's own are released at the return, so the page links at once; the cue's glance must not flash. Only the cue is read
    # here (the shape checks of _leg assume an outage that held a dial).
    def _healthy(self, engine):
        name, r = self._drive("phone", "hung", 0, engine)
        self._cue(name, r, "hung", 0, require_no_paint=True)
        Path(os.path.join(self.lab, "return-harness-%s.json" % name)).write_text(json.dumps(type(self).measurements.get(name, {}), indent=1, sort_keys=True))

    def test_phone_healthy_return_paints_no_badge(self):
        self._healthy("chromium")

    # iOS item 4 (finding of 2026-10-02): the Waiting pane, loaded before the suspend and off screen at the return (parked), tapped 2 s
    # after a healthy return (the finding's lab case was the Outline, which parks the same way). The tap is the pane's return: its
    # badge must not show when its content lands inside the hold.
    def _healthy_post_tap(self, engine):
        name, r = self._drive("phone", "hung", 0, engine, tap="waiting", post_tap="waiting")
        self._cue(name, r, "hung", 0, require_no_paint=True)
        self._tapcue(name, r, require_no_paint=True)
        Path(os.path.join(self.lab, "return-harness-%s.json" % name)).write_text(json.dumps(type(self).measurements.get(name, {}), indent=1, sort_keys=True))

    def test_phone_healthy_return_then_a_parked_tab_tapped_paints_no_badge(self):
        self._healthy_post_tap("chromium")

    # iOS item 4 (findings of 2026-10-02): the Outline, loaded before the suspend and parked at the return, tapped 2 s into a hung
    # 12 s outage. Its badge paints a hold after the tap (not at the tap, not while parked), clear of the Outline's search and tag
    # filter, and clears at its first frame after the outage. The pane's key is read from the kernel's pane order by its label.
    def test_phone_hung_12s_a_parked_tab_tapped_during_the_outage_paints_a_hold_after_the_tap(self):
        outline = next(k for k, label in km_pane_order() if label == "Outline")
        name, r = self._drive("phone", "hung", 12, "chromium", tap=outline, post_tap=outline)
        self._cue(name, r, "hung", 12)
        self._tapcue(name, r, need_controls=True)
        Path(os.path.join(self.lab, "return-harness-%s.json" % name)).write_text(json.dumps(type(self).measurements.get(name, {}), indent=1, sort_keys=True))

    def test_webkit_phone_healthy_return_then_a_parked_tab_tapped_paints_no_badge(self):
        self._healthy_post_tap("webkit")

    def test_webkit_phone_healthy_return_paints_no_badge(self):
        self._healthy("webkit")

    # Round 1 of the review (2026-10-03: regression-1, extra5-1, correctness-1, correctness-2): three surfaces of controls that do not
    # scroll with the content, where the badge's first place (8 px below the content container's top) painted over a control. Each
    # leg is a short hung outage (the badge paints at the hold and clears at the pane's first fresh frame after it), read by the
    # pane's frame recorder, whose chrome counts sticky and fixed elements inside the container and what they hold
    # (_badge_clear_of_chrome), with a witness that the surface's control was in the chrome read beside the painted badge.
    def _chrome_witness(self, where, r, pred, what):
        cue = r.get("cue") or {}
        recs = [b for b in (cue.get("badge") or []) if b["on"]] + list(cue.get("moves") or [])
        self.assertTrue(any(pred(c) for b in recs for c in (b.get("chrome") or [])), where + "the recorder read %s as chrome beside the painted badge: %r" % (what, recs[:2]))
        return recs

    def _surface(self, name, r):
        Path(os.path.join(self.lab, "return-harness-%s.json" % name)).write_text(json.dumps(type(self).measurements.get(name, {}), indent=1, sort_keys=True))

    # the subagent viewer's sticky header (#sub-head) inside the transcript's container, its pin (role=button) at the right end:
    # opened before the suspend from the Agent head of the `tests` session (_subagent)
    def test_phone_hung_4s_the_subagent_viewers_header_and_its_pin_stay_clear_of_the_badge(self):
        name, r = self._drive("phone", "hung", 4, "chromium", active_sid=SUB_SID, sub_view=True)
        where = name + ": "
        self.assertEqual(r.get("subView"), {"opened": True, "pin": True}, where + "the viewer opened and its header holds the pin: %r" % (r.get("subView"),))
        self._cue(name, r, "hung", 4)
        self._chrome_witness(where, r, lambda c: c.get("inContent") and c["el"].startswith("span.sub-head-pin"), "the viewer's pin, inside the container")
        self._surface(name, r)

    # the chat's landing notice ("Going to the message from ..., click to stay here", the only cancel for a jump), drawn over the
    # transcript's top from outside its container, shown after the badge has painted (its on-demand hook): the badge must move off it
    def test_phone_hung_4s_a_landing_notice_shown_under_the_painted_badge_moves_it_clear(self):
        name, r = self._drive("phone", "hung", 4, "chromium", notice_after_paint=True)
        where = name + ": "
        self.assertNotIn("noticeError", r, where + "the notice step ran: %r" % (r.get("noticeError"),))
        self.assertEqual(r.get("notice"), {"hook": True, "shown": True}, where + "the notice was shown during the wait: %r" % (r.get("notice"),))
        self._cue(name, r, "hung", 4)
        recs = self._chrome_witness(where, r, lambda c: ".tx-landing-notice" in c["el"], "the landing notice")
        self.assertTrue([b for b in recs if b["t"] >= r["t"]["notice"]], where + "a record of the painted badge after the notice showed: %r" % (recs,))
        self._surface(name, r)

    # the desktop Feed: no header above its list, three column heads sticky at the list's top, each with its drag chip (a grab cursor
    # and nothing else); the badge's first place, 8 px down at the right, was on the third head's chip at this width (the Feed pane at
    # 636 px in the 1600 px window, three columns)
    def test_desktop_hung_4s_the_feeds_column_heads_and_drag_chips_stay_clear_of_the_badge(self):
        name, r = self._drive("desktop", "hung", 4, "chromium", cue_app="feed")
        where = name + ": "
        self._cue(name, r, "hung", 4)
        self._chrome_witness(where, r, lambda c: c.get("inContent") and c["el"].startswith("span.feed-col-name"), "a column head's drag chip, inside the list")
        self._surface(name, r)

    def test_phone_hung_12s(self):
        self._leg("phone", "hung", 12)

    def test_phone_hung_12s_tab_tap(self):
        self._leg("phone", "hung", 12, tap="fleet", abort=True, retry_enter=True)   # stage 0: a lazy pane tapped before the suspend loads on the tap and parks at the return; its FIRST fetch is aborted (HIGH 2, review round 1): the shell says so and the re-tap loads it; Enter on the focused Try again button keeps its focus across the re-failure (ui-1, review round 4; Chromium's detector is the load listener, so the re-failure is quick)

    # extra9-2 (review round 3, 2026-09-19): the two panes whose served markup this change takes lazy (src to data-src) tapped in a real
    # engine, so the first-tap road is witnessed on them and not on the Outline alone (which carried data-src before): the document loads
    # once on the tap (srcAfterTap, one wsopen row), the shell's loader paints and retires, the socket comes up, and the pane parks at the
    # return. The Files leg seeds the gear's Files control on, or the tab is hidden and show('files') falls to the chat.
    def test_phone_hung_12s_tab_tap_waiting(self):
        self._leg("phone", "hung", 12, tap="waiting")

    def test_phone_hung_12s_tab_tap_files(self):
        self._leg("phone", "hung", 12, tap="files")

    # review round 4 (2026-09-19, kernel-1 and tests-1): the tapped pane's one request loses its cookie on the wire, so the REAL kernel answers its 403
    # (text/plain, the body naming the serve-token file's path); the shell must not show it as served: the failed state, the retry road, no
    # pane-load row, and the re-tap (the cookie flowing again) loads the pane. Pass 3's leg fulfilled
    # a stand-in body here. The load listener is the detector in every engine (a 403 commits a document), so the twins pin the same detector
    def test_phone_hung_12s_tab_tap_denied_document(self):
        self._leg("phone", "hung", 12, tap="fleet", denied=True, retry_enter=True)   # + ui-1 (review round 4): the keyboard's retry keeps its focus across the re-failure, on every engine (the 403 fires load everywhere)

    def test_phone_hung_12s_tab_tap_unmarked_document(self):
        # pass 5, the author's label (2026-09-20, taking the reviewer's round-4 finding tests-1): docState's `doc` answer in a real engine. The tapped pane's fetch is answered by the REAL kernel's 200
        # with the shim's marker statement stripped by the route (a stamped document with no shim, the fallback page's shape): shown as served
        # (the loader retired on its load, the src kept, no failed state), the stamp read off documentElement in the engine, and no pane-load row.
        # Chromium alone: the composition proved engine-invariant in the reviewer's round-4 refuters' probes
        self._leg("phone", "hung", 12, tap="fleet", unmarked=True)

    def test_the_kernel_stamps_every_200_html_document_at_a_pane_url_and_its_denial_carries_no_stamp(self):
        # review round 4 (kernel-1): the writer's rule, read off the real kernel: every text/html 200 at a pane url (the seven pane routes and the
        # gear's) carries data-romp-served=200 on its <html> tag, once; the same routes with no credential answer 403 and a body with no <html>
        # tag of the kernel's at all (text/plain), so no stamp. The bodies are counted, never printed (the 403's names the serve-token file's path).
        routes = ["/" + k for k, _ in km_pane_order()] + ["/settings"]
        self.assertGreaterEqual(len(routes), 7, "the census has the pane routes: %r" % (routes,))
        for p in routes:
            with urllib.request.urlopen("http://127.0.0.1:%d%s?token=%s" % (self.port, p, self.token), timeout=10) as resp:
                body = resp.read()
                self.assertEqual(resp.status, 200, p + ": served with the token")
                self.assertTrue(resp.headers.get("Content-Type", "").startswith("text/html"), p + ": text/html: %r" % (resp.headers.get("Content-Type"),))
            self.assertEqual(body.count(b"<html data-romp-served=200"), 1, p + ": one stamp on the <html> tag (count %d, %d bytes)" % (body.count(b"data-romp-served"), len(body)))
            self.assertTrue(re.match(rb"\s*<!DOCTYPE html>\s*<html data-romp-served=200[\s>]", body, re.I), p + ": the stamped tag is the document's root, the one documentElement carries (the author's pass-5 verify: a count of one cannot tell a stamped root from a stamped <html in a leading comment; %d bytes)" % (len(body),))
            try:
                urllib.request.urlopen("http://127.0.0.1:%d%s" % (self.port, p), timeout=10)
                self.fail(p + ": a credential-less request was served (no denial to test)")
            except urllib.error.HTTPError as e:
                denial = e.read()
                self.assertEqual(e.code, 403, p + ": the kernel's denial")
                self.assertTrue(e.headers.get("Content-Type", "").startswith("text/plain"), p + ": text/plain: %r" % (e.headers.get("Content-Type"),))
                # asserted as derived booleans (the author's pass-4 verify): assertNotIn's red appends the container, the body that names the
                # serve-token file's path, to the failure text; a red here says the count and the size and prints no byte of it
                self.assertFalse(b"<html" in denial.lower(), p + ": the denial writes no <html> tag (%d bytes)" % (len(denial),))
                self.assertFalse(b"data-romp-served" in denial, p + ": ...and carries no stamp (%d bytes)" % (len(denial),))
        # pass 5, the author's label, taking the reviewer's round-4 finding tests-4: the shell page every client loads, `/` with the token (Handler._send's _landing() writer), is stamped once
        # although its body carries more than one <html match (its own script's), the first-tag rule; and the credential-less `/` is the
        # paste-the-token page, a text/html 200 with NO <html> tag and no stamp, the one such body the kernel writes (served at / to a request
        # with no credential and at /login, the sign-in page since main's fork PR #919, the same bytes; never at a pane url: unstamped, it
        # would read as a failure there). Counted, never printed.
        with urllib.request.urlopen("http://127.0.0.1:%d/?token=%s" % (self.port, self.token), timeout=10) as resp:
            landing = resp.read()
            self.assertEqual(resp.status, 200, "/: the landing, served with the token")
            self.assertTrue(resp.headers.get("Content-Type", "").startswith("text/html"), "/: text/html: %r" % (resp.headers.get("Content-Type"),))
        self.assertEqual(landing.count(b"<html data-romp-served=200"), 1, "/: one stamp on the landing's <html> tag (count %d, %d bytes)" % (landing.count(b"data-romp-served"), len(landing)))
        self.assertTrue(re.match(rb"\s*<!DOCTYPE html>\s*<html data-romp-served=200[\s>]", landing, re.I), "/: the stamped tag is the landing's root (%d bytes)" % (len(landing),))
        self.assertGreaterEqual(len(re.findall(rb"<html(?=[\s>])", landing, re.I)), 2, "/: the landing's body carries more than one <html match (its shell script's), so the count above pins the first-tag rule (%d matches)" % (len(re.findall(rb"<html(?=[\s>])", landing, re.I)),))
        with urllib.request.urlopen("http://127.0.0.1:%d/" % self.port, timeout=10) as resp:
            token_page = resp.read()
            self.assertEqual(resp.status, 200, "/ without a credential: the paste-the-token page, a 200")
            self.assertTrue(resp.headers.get("Content-Type", "").startswith("text/html"), "/ without a credential: text/html: %r" % (resp.headers.get("Content-Type"),))
        self.assertGreater(len(token_page), 0, "the token page has a body")
        self.assertEqual((len(re.findall(rb"<html(?=[\s>])", token_page, re.I)), token_page.count(b"data-romp-served")), (0, 0), "the paste-the-token page: no <html> tag, so unstamped, the disclosed exception, read off the real kernel (%d bytes)" % (len(token_page),))
        with urllib.request.urlopen("http://127.0.0.1:%d/login" % self.port, timeout=10) as resp:
            login_page = resp.read()
            self.assertEqual(resp.status, 200, "/login: the sign-in page, a 200")
            self.assertTrue(resp.headers.get("Content-Type", "").startswith("text/html"), "/login: text/html: %r" % (resp.headers.get("Content-Type"),))
        self.assertTrue(login_page == token_page, "/login serves the same paste-the-token page, so the exception has two routes and neither is a pane url (%d and %d bytes)" % (len(login_page), len(token_page)))

    def test_firefox_phone_hung_12s_tab_tap_denied_document(self):
        self._leg("phone", "hung", 12, engine="firefox", tap="fleet", denied=True, retry_enter=True)

    def test_webkit_phone_hung_12s_tab_tap_denied_document(self):
        self._leg("phone", "hung", 12, engine="webkit", tap="fleet", denied=True, retry_enter=True)

    def test_phone_hung_12s_the_start_gate_holds_the_chain_behind_the_active_tabs_full(self):
        self._leg("phone", "hung", 12, hold_active_full_ms=1500)   # fresh-2 (review round 3): the chat on screen, the active tab's full held 1.5 s on the wire: no prefetch inside the hold, one after it

    # The F1 legs (stage 0, review round 1): a phone opened on the Feed tab holds the chat's idle chain while the chat is display:none
    # (paneHidden) and the Chat tab's show re-arms it, by one of two roads in render.ts: the chat-visibility hook (onShown, the published
    # word's flip from hidden to shown) and the panes-word belt (the shell's word saying the chat is on). What each leg pins is what the
    # single-road runs showed (each road removed alone, then both: pass 3's record, and pass 8's runs at this head, the hook-alone
    # run repeated): the Chromium leg and the WebKit leg each red only with BOTH roads removed and stay green with either alone
    # removed, so each pins that one of the two re-arms the chain on its engine and neither witnesses the hook or the belt by itself
    # (one of the reviewer's round-2 refuters saw the WebKit leg red with the hook alone removed at an earlier head, before `docs`
    # became the active tab; the other saw it green there, and at this head it is green in every run). The roads' executed witnesses
    # are other tests: the hook's are tests/test_pane_hidden_word_browser.py (PaneHiddenWordInBrowsers.test_chromium and
    # test_webkit: the onShown counter runs once at the re-show, red at 0 != 1 with the onShown call removed) and the onShown case in
    # ui/webview/chat-visibility.test.ts; the belt's is the executed panes-word BELT case in ui/webview/skeleton-tabs-wiring.test.ts
    # (the chat's panes handler lifted and run, red with the belt line removed); render.ts's wiring of both, the third argument and
    # the wasChatOff line, is regex-pinned in those two node files, a text pin beside the executed ones. The ACTIVE tab is the
    # transcript-less `docs` (review round 3, extra9-1), chosen to leave
    # no build rAF pending while hidden; measured, its full still carries two events (the kernel's head events for a session with no
    # transcript), so render.ts still defers its build, and the tab stays for the strip pin in _dial (docs whole and active while the
    # three transcript-bearing tabs are still skeletons behind the Feed tab: the diet's shape, read off the DOM).
    def test_phone_opened_on_the_feed_tab_arms_the_chain_when_chat_is_shown(self):
        self._leg("phone", "hung", 12, tap="chat", boot_tab="feed", active_sid=SESSIONS[3][0])   # Chromium: the observer speaks for the hidden-since-load frame, so the hook runs at the show and the belt runs too; the leg reds only with both roads removed (the single-road runs, the comment above), so it pins the pair and neither road alone

    def test_firefox_phone_opened_on_the_feed_tab_arms_the_chain_when_chat_is_shown(self):
        # THE OUTCOME ON FIREFOX, NOT A ROAD (review round 3, extra9-1, traced): Firefox runs no rAF in a display:none iframe (idle
        # callbacks and timers it does run; probed on all three engines), so the active tab's deferred build stays pending for as long as
        # the chat is hidden and the idle pass's mid-build yield re-arms itself every pass (98 self re-arms at a 16 ms cadence before the
        # tap in the traced run) until the show, when the rAF runs and the next pass issues the prefetch on its own. With BOTH roads
        # removed this leg stays green (the record), so it witnesses neither; it pins that a Firefox phone opened on another tab asks
        # nothing while the chat is hidden and loads its other tabs after the Chat tab's show, whichever mechanism carries it. Firefox's
        # observer does not speak for a frame hidden since load (its first word is the shown one), so the hook is inert here and the
        # belt, when the yield is not spinning, is the re-arm; the belt's executed witness is in ui/webview/skeleton-tabs-wiring.test.ts.
        self._leg("phone", "hung", 12, engine="firefox", tap="chat", boot_tab="feed", active_sid=SESSIONS[3][0])

    def test_webkit_phone_opened_on_the_feed_tab_arms_the_chain_when_chat_is_shown(self):
        self._leg("phone", "hung", 12, engine="webkit", tap="chat", boot_tab="feed", active_sid=SESSIONS[3][0])   # Safari's engine: requestIdleCallback is absent and the chain runs on the 16 ms fallback; its observer speaks while hidden, so the hook runs at the show and the belt runs too; like the Chromium leg it reds only with both roads removed and stays green with either alone removed (the single-road runs, the comment above), so it pins the pair and neither road alone

    def test_phone_refused_30s_slow(self):
        self._leg("phone", "refused", 30)

    def test_phone_hung_30s_slow(self):
        self._leg("phone", "hung", 30)

    def test_desktop_refused_12s(self):
        self._leg("desktop", "refused", 12)

    def test_desktop_hung_12s(self):
        self._leg("desktop", "hung", 12)

    @unittest.skipUnless(FULL, "optional: the desktop 30 s legs run with RETURN_HARNESS_FULL=1 (the runtime budget)")
    def test_desktop_refused_30s_slow(self):
        self._leg("desktop", "refused", 30)

    @unittest.skipUnless(FULL, "optional: the desktop 30 s legs run with RETURN_HARNESS_FULL=1 (the runtime budget)")
    def test_desktop_hung_30s_slow(self):
        self._leg("desktop", "hung", 30)

    # the optional engines, one leg each: Firefox has no Page Lifecycle `resume`, the closest desktop stand-in for Safari's
    # return; WebKit is Safari's engine. Both skip `optional:` where the browser is absent (CI installs Chromium alone).
    # tests-1 (review round 1, 2026-09-19): both engine legs tap a lazy pane, so the parked-pane contract (D2) and the failed-load road
    # (HIGH 2) each have a witness in every engine, not Chromium alone (~90 s per leg; WebKit's abort waits out the 30 s backstop)
    def test_firefox_phone_hung_12s(self):
        self._leg("phone", "hung", 12, engine="firefox", tap="fleet", abort=True)

    def test_webkit_phone_hung_12s(self):
        self._leg("phone", "hung", 12, engine="webkit", tap="fleet", abort=True)

    # tests-1 (review round 3, 2026-09-19): the headline road on Safari's engine with NO abort: the Outline (the smallest bundle, and the one
    # pane every other tap leg aborted at its first fetch) loads on its FIRST tap: the document's load, the loader's retirement at it, the socket
    # up, the pane painted, then the park at the return (D2) on the same pane
    def test_webkit_phone_hung_12s_tab_tap_fleet_first_tap(self):
        self._leg("phone", "hung", 12, engine="webkit", tap="fleet")


if __name__ == "__main__":
    unittest.main()
