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
(lab_dist.copy_dist); three synthetic sessions (`web`, `api`, `tests` of the notes-api demo, placeholder uuids, host
TESTHOST). The driver (tests/return_from_background_browser.mjs) opens the served shell, waits for every pane socket's
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


def _eager(shell, tap=None):
    """The panes whose documents the shell has loaded before the suspend: every pane on the desktop; on the phone the eager ones plus
    the pane a leg tapped (its document loaded on the tap)."""
    return tuple(a for a in APPS if shell != "phone" or a not in LAZY_PHONE or a == tap)
VISIBLE = "chat"                                                  # the phone's default tab and the desktop's first pane
HOST = "TESTHOST"
SESSIONS = (("11111111-2222-4333-8444-000000000101", "web", "w"),
            ("11111111-2222-4333-8444-000000000102", "api", "a"),
            ("11111111-2222-4333-8444-000000000103", "tests", "t"))
DECISIONS = {"keep", "redial-closed", "redial-stale"}
FULL = os.environ.get("RETURN_HARNESS_FULL") == "1"
OUT_DIR = os.environ.get("RETURN_HARNESS_OUT", "")


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


def _seed(lab):
    """The lab's state root and Claude config dir, with the three synthetic sessions of the notes-api demo."""
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
        Path(proj, sid + ".jsonl").write_text(_transcript(sid, tag, cwd, 6))
    return state, claude


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
    def _drive(self, shell, regime, outage_s, engine="chromium", tap=None, boot_tab=None, abort=False, error_body=False):
        declared = os.environ.get("ROMP_SERVED_TESTS_ENGINES", "")
        if engine != "chromium" and declared and engine not in [e.strip() for e in declared.split(",")]:
            self.skipTest("optional: this runner declares no %s (ROMP_SERVED_TESTS_ENGINES=%s)" % (engine, declared))
        name = "%s-%s-%s-%ds%s%s%s" % (engine, shell, regime, outage_s, "-tap-" + tap if tap else "", ("-errbody" if error_body else "-abort") if abort else "", "-boot-" + boot_tab if boot_tab else "")
        eager = _eager(shell, tap)
        # a derived set that came out empty would hand the driver a boot wait and a fresh wait that end at once with nothing witnessed
        # (review round 2, 2026-09-19: every derived expectation must fail when the derivation yields nothing)
        self.assertTrue(_eager(shell), "the eager set for the %s shell is not empty" % shell)
        self.assertTrue([a for a in eager if a in FRESH_APPS], "the fresh set is not empty: %r" % (eager,))
        cfg = {"engine": engine, "shell": shell, "regime": regime, "outageMs": outage_s * 1000, "hiddenDwellMs": 400,
               "url": "http://127.0.0.1:%d/?token=%s" % (self.port, self.token),
               "healthz": "http://127.0.0.1:%d/healthz" % self.port, "diag": self.diag, "apps": list(APPS),
               "eagerApps": list(_eager(shell)), "freshApps": [a for a in eager if a in FRESH_APPS], "tapPane": tap,   # the boot wait is the eager panes' (a lazy pane has no shim to say up); the fresh wait includes a tapped pane
               "abortPane": tap if abort else "",   # HIGH 2 (review round 1): the tapped pane's first document fetch is aborted; the shell must say so and the re-tap must load it
               "abortMode": "error-body" if error_body else "abort",   # HIGH 2, review round 2 closeout: error-body answers the fetch with a 502 page (same-origin at the pane's url, load fires) instead of aborting it
               "perfShare": True, "bootTimeoutMs": 30000, "freshTimeoutMs": 25000, "settleMs": 1500,
               "bootTab": boot_tab or "", "expectPrefetchAfterChatTap": bool(boot_tab and tap == "chat"),   # stage 0, review round 1: a phone left on another tab, then the Chat tab shown, arms the idle chain
               "activeSid": SESSIONS[0][0] if boot_tab else "",   # the chat blob's active tab (the dial's hint): with none the kernel serves the whole board and there is no skeleton set to prefetch
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

    def _leg(self, shell, regime, outage_s, engine="chromium", tap=None, boot_tab=None, abort=False, error_body=False):
        name, r = self._drive(shell, regime, outage_s, engine, tap, boot_tab, abort, error_body)
        rows = _rows(self.diag)
        m = measure(rows, r)
        art = os.path.join(self.lab, "return-harness-%s.json" % name)
        Path(art).write_text(json.dumps(m, indent=1, sort_keys=True))
        type(self).measurements[name] = m
        if abort:
            self._abort(name, r, rows, tap, engine, error_body)   # first on an abort leg: a detector that takes the failed fetch for a load leaves no shim to park or dial, so every later check fails after it, and the red should name the refused input (review round 2 closeout)
        self._shapes(name, r, m, regime)
        self._parked(name, r, m)
        self._lazy(name, r, m, tap)
        self._dial(name, r, boot_tab, tap)
        self._feed_paint(name, r, boot_tab)
        self._return_chain(name, r, rows)
        return m

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

    # ---- HIGH 2 (review round 1, 2026-09-19): a lazy pane whose first document fetch fails is re-parked, says so, and loads on the re-tap ----
    def _abort(self, name, r, rows, tap, engine, error_body=False):
        """The tapped pane's document was aborted at the first tap. The shell must paint the failed state where the user looks
        (body.pane-failed keeps #pane-load up at display:flex with the message and the loader down), re-park the pane (no src, the
        url back under data-lazy-src) and file one `pane-load-failed` row whose keys survive CLIENT_DIAG_KEYS' allowlist; the re-tap
        then loads it (the frame at the pane's url, its shim up, the failed state gone). Chromium detects the failure on the error
        page's load event (`via` load); Firefox and WebKit fire no load event the shell can act on for the aborted navigation (the
        frame keeps about:blank), so the 30 s backstop detects it (`via` backstop), which is what the WebKit leg's wait is for.
        error_body (HIGH 2, review round 2 closeout): the fetch answers a 502 page instead, a proxy's body while the kernel restarts:
        same-origin at the pane's url, committed, load fired in every engine (`via` load), and no pane shim in its window, which is
        what tells it from the pane's own document; before this any committed same-origin document counted as loaded."""
        where = name + ": "
        a = r.get("abort") or {}
        self.assertEqual(a.get("mode"), "error-body" if error_body else "abort", where + "the driver ran the leg's failure mode: %r" % (a,))
        self.assertGreaterEqual(a.get("ms", -1), 0, where + "the shell said the pane failed (body.pane-failed) within the wait: %r" % (a,))
        self.assertEqual(a.get("display"), "flex", where + "#pane-load is painted in the failed state: %r" % (a,))
        self.assertEqual(a.get("loaderDisplay"), "none", where + "…with the loader itself down: %r" % (a,))
        self.assertEqual(a.get("msg"), "Couldn't load this pane. Tap to try again.", where + "the first failure's copy: %r" % (a,))
        self.assertEqual((a.get("src"), a.get("lazy")), (None, "/" + tap), where + "the pane is re-parked (no src, the url back under data-lazy-src): %r" % (a,))
        self.assertFalse(a.get("loading"), where + "the loading state is over: %r" % (a,))
        wid = r.get("wid") or ""
        mine = [x for x in rows if x.get("wid") == wid and x.get("surface") == "shell" and x.get("what") == "pane-load-failed"]
        self.assertEqual(len(mine), 1, where + "one pane-load-failed row for the one failure: %r" % (mine,))
        data = mine[0].get("data") or {}
        self.assertEqual((data.get("pane"), data.get("n")), (tap, 1), where + "the row names the pane and the count (the keys survive the allowlist): %r" % (data,))
        self.assertEqual(data.get("via"), "load" if (engine == "chromium" or error_body) else "backstop", where + "the detector per engine, as observed under the route's abort: Chromium commits an error page and fires load; Firefox and WebKit fire no load event the shell can act on (the frame keeps about:blank), so the 30 s backstop detects it; an HTTP error body is a committed navigation, so its load fires everywhere: %r" % (data,))
        la = r.get("loadingAfterTap") or {}
        self.assertFalse(la.get("failed"), where + "the re-tap cleared the failed state: %r" % (la,))
        self.assertEqual(la.get("failedPanes"), [], where + "no .pane carries `failed` after the re-tap: %r" % (la,))
        self.assertIn("/" + tap, r.get("frames") or [], where + "the re-tap loaded the pane's document (the frame at its url): %r" % (r.get("frames"),))

    # ---- stage 0's dial pins (review round 1, 2026-09-19): the phone's first chat dial takes the diet; the chain waits for the chat pane's show ----
    def _dial(self, name, r, boot_tab, tap):
        """The phone's first chat dial carries skeleton=1 (the kernel serves one full plus statuses), the desktop's does not (F5's rule end to
        end); and on a phone opened on another tab the chat pane's idle prefetch asks for nothing while the chat is display:none and asks
        for its first background full once the Chat tab is shown (F1: the visibility publisher's show hook and the panes word's belt)."""
        where = name + ": "
        boot_chat = [d for d in (r.get("dials") or []) if d.get("app") == "chat" and d.get("phase") == "boot"]
        self.assertTrue(boot_chat, where + "the chat pane dialed at boot")
        if r.get("shell") == "phone":
            self.assertTrue(boot_chat[0].get("skeleton"), where + "the phone's first chat dial carries skeleton=1: %r" % (boot_chat[0],))
        else:
            self.assertFalse(any(d.get("skeleton") for d in boot_chat), where + "the desktop's chat dials whole, as before: %r" % (boot_chat,))
        if boot_tab and tap == "chat":
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
            la = r.get("loadingAfterTap") or {}
            self.assertIn("panes", la, where + "the loading state was read after the tap: %r" % (la,))
            self.assertNotIn(tap + "-pane", la.get("panes") or [], where + "its document had loaded by the time its socket was up, so its .pane no longer carries the loading class: %r" % (la,))
            self.assertFalse(la.get("body"), where + "…and the shell's loader is down: %r" % (la,))
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

    def test_phone_hung_12s(self):
        self._leg("phone", "hung", 12)

    def test_phone_hung_12s_tab_tap(self):
        self._leg("phone", "hung", 12, tap="fleet", abort=True)   # stage 0: a lazy pane tapped before the suspend loads on the tap and parks at the return; its FIRST fetch is aborted (HIGH 2, review round 1): the shell says so and the re-tap loads it

    def test_phone_hung_12s_tab_tap_http_error_body(self):
        self._leg("phone", "hung", 12, tap="fleet", abort=True, error_body=True)   # HIGH 2, review round 2 closeout: the tapped pane's first fetch answers a 502 body (a proxy while the kernel restarts): same-origin at the pane's url, load fires, and the shell must call it failed (the pane's own document carries the shim), re-park it and load it on the re-tap

    def test_phone_opened_on_the_feed_tab_arms_the_chain_when_chat_is_shown(self):
        self._leg("phone", "hung", 12, tap="chat", boot_tab="feed")   # stage 0, review round 1 (F1): the chat display:none at boot asks nothing; its show arms the idle prefetch

    def test_firefox_phone_opened_on_the_feed_tab_arms_the_chain_when_chat_is_shown(self):
        self._leg("phone", "hung", 12, engine="firefox", tap="chat", boot_tab="feed")   # the F1 arm off Chromium: Firefox's observer over an iframe hidden since load, and the panes-word belt (review round 2)

    def test_webkit_phone_opened_on_the_feed_tab_arms_the_chain_when_chat_is_shown(self):
        self._leg("phone", "hung", 12, engine="webkit", tap="chat", boot_tab="feed")   # …and Safari's engine, where requestIdleCallback is absent and the chain runs on the 16 ms fallback

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


if __name__ == "__main__":
    unittest.main()
