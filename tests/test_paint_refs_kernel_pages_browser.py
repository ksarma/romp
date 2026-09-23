#!/usr/bin/env python3
"""What an inline svg's paint references send from the kernel's own pages, under the kernel's real headers (2026-09-23).

A hermetic lab kernel (the served labs' environment, tests/test_ship_reship_served.py kernel_env: its own state root,
port and token) serves one synthetic session and the real /feed, /chat and / pages from a copy of the built bundle. A
request logger on 127.0.0.1:Q records each request's path, Referer, Sec-Fetch-Dest, Sec-Fetch-Site, Cookie and Host. The
browser reaches it under two names, each another origin and another site to the pages (served from 127.0.0.1):
http://localhost:Q, a name Chromium counts as trustworthy and so sends its Sec-Fetch headers to, and
http://remote.invalid:Q (Chromium's --host-resolver-rules maps the name to 127.0.0.1), a host the file viewer's figure
gate does not list (the gear's figureHosts default names github.com's hosts, localhost and 127.0.0.1). Two scenes:

test_a_notice_card_s_paint_references_reach_no_other_host: a notice card's body on the feed page (feed.ts
noticeBodyNodes: a session writes it through POST /notice, and the feed runs it through sanitizeMd and then
stripRemoteLoads with an empty base). The body carries an inline svg with each of the eight paint attributes (fill,
stroke, filter, clip-path, mask, marker-start, marker-mid, marker-end) and an inline style's mask-image, each aimed at
the logger as localhost. The feed page is opened bare, /feed?token=, so its own address carries the token. Asserted: no
request reaches the logger, and no remote reference stands in the card. Two controls say an empty log is the removal's
work. The body's absolute same-origin reference (a fill naming the kernel's own /media/romp-swirl-glyph.svg?own=notice)
must stand in the card and be requested from the kernel within a bound, which shows the card painted, its svg rendered,
and this browser fetched a paint reference the pass keeps (with the body fallen to plain text, or with the pass
admitting no own origin, it is neither requested nor in the card); the driver then drains 1.5 s more before the log is
read. It is absolute on purpose: the notice card's strip passes no base, so a relative same-origin reference is removed
there (a residual that fails closed, pinned in ui/webview/file-preview.test.ts). After the record the page fetches the
logger once (no-cors), which must be its one /reach-notice line, so the logger is one the page can reach. Red before the
fix, at 6cf6839ba (this file run over a copy of that tree, 2026-09-23): the logger received the fill, stroke, clip-path,
mask and the three markers, each Sec-Fetch-Dest image and cross-site, the mask with the page's origin as its Referer and
the rest with none; the filter and the style's mask-image sent nothing (the colour-only style rule removes the
declaration at that commit too).

test_a_figure_the_viewer_loads_on_a_click_sends_at_most_the_page_s_origin: the file viewer, a modal over the chat pane,
holds a figure on an unlisted host behind a placeholder, and one click loads it. The scene opens it twice: from a bare
/chat?token= page, whose own address carries the token, and from the framed shell (/?token=, which drops the token from
its address before it frames /chat without it). Each opens a markdown file whose figures are an img and an inline svg
with the same eight paint attributes, aimed at the logger as remote.invalid, clicks the placeholder, and waits (bounded)
until the img, the fill and the mask have arrived. Asserted: nothing reached the logger before the click, and each
request after it carries no Referer or the page's origin alone, never a path or the token. At this commit and at
6cf6839ba the img, the fill, the stroke, the clip-path and the three markers sent no Referer, the mask sent the page's
origin, and the filter sent nothing, from either page. Red under mutations (2026-09-23): with the kernel's
Referrer-Policy changed to unsafe-url the img and the six others carried the bare page's full URL with its token (the
mask still sent the origin alone, so Chromium does not take a mask's Referer from the page's policy), and with the gate
letting every host through the img and the seven paint references that fetch arrived before any click.

Skips LOUDLY without the extension deps or a Playwright browser; the CI extension job installs Chromium and runs served
files with ROMP_SERVED_TESTS_REQUIRE=1, which turns any skip into a failure there. SYNTHETIC fixtures only (session web,
the notes-api demo world, a placeholder uuid, the host remote.invalid)."""
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import lab_dist

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
EXT = os.path.join(ROOT, "vscode-extension")
sys.path.insert(0, HERE)
import test_ship_reship_served as _lab   # noqa: E402  the lab kernel's environment (the module, not its classes)

SID = "aaaaaaaa-1111-2222-3333-555555555555"
U_UUID = "11111111-2222-3333-4444-555555555555"
A_UUID = "22222222-3333-4444-5555-666666666666"
REMOTE_HOST = "remote.invalid"   # the logger's name in the viewer scene, mapped to 127.0.0.1 by the launch flag below
# the eight paint attributes, by the file name each asks the logger for (the scene's prefix goes in front)
PAINT = ("fill.svg", "stroke.svg", "clip.svg", "mask.svg", "filter.svg", "ms.svg", "mm.svg", "me.svg")
VIEWER_AWAITED = ("img.png", "fill.svg", "mask.svg")   # what the viewer scene waits for after the click (bounded)


def _png(w=2, h=2, rgb=(200, 60, 60)):
    """A tiny valid PNG (RGB, no filter) without a binary fixture."""
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _svgs(r):
    """One inline svg per paint attribute, each aimed at `r` (the logger's URL and the scene's prefix)."""
    def svg(inner):
        return '<svg width="40" height="40">%s</svg>' % inner
    return [
        svg('<rect width="40" height="40" fill="url(%sfill.svg#p)"/>' % r),
        svg('<rect width="40" height="40" fill="none" stroke="url(%sstroke.svg#p)" stroke-width="4"/>' % r),
        svg('<rect width="40" height="40" fill="red" clip-path="url(%sclip.svg#c)"/>' % r),
        svg('<rect width="40" height="40" fill="red" mask="url(%smask.svg#m)"/>' % r),
        svg('<rect width="40" height="40" fill="red" filter="url(%sfilter.svg#f)"/>' % r),
        svg('<path d="M5 5 L20 30 L35 5" stroke="red" fill="none" marker-start="url(%sms.svg#a)" marker-mid="url(%smm.svg#b)" '
            'marker-end="url(%sme.svg#c)"/>' % (r, r, r)),
    ]


def _notice_body(remote, origin):
    """The notice's markdown: the eight paint attributes and an inline style's mask-image aimed at the logger, and the
    absolute same-origin control."""
    r = remote + "/N-"
    return "\n\n".join(
        ["A new version of the accuracy figure is ready."] + _svgs(r) +
        ['<span style="color: red; mask-image: url(%sstyle.png)">a masked word</span>' % r,
         '<svg width="40" height="40"><rect width="40" height="40" fill="url(%s/media/romp-swirl-glyph.svg?own=notice#p)"/></svg>' % origin,
         "The end."])


def _figures(remote, prefix):
    """A viewed markdown file whose figures sit on the logger's host: an img and the eight paint attributes."""
    r = remote + "/" + prefix
    return "\n\n".join(["# Figures", "The figures from the sweep.", '<img src="%simg.png" alt="a remote figure">' % r]
                       + _svgs(r) + ["The end.", ""])


DRIVER = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const { chromium } = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
let browser;
try { browser = await chromium.launch({ args: ["--host-resolver-rules=MAP " + cfg.remoteHost + " 127.0.0.1"] }); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const context = await browser.newContext({ viewport: { width: 1400, height: 900 } });
const errors = [];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const logNow = async () => (await (await fetch(cfg.logUrl)).json());   // the logger's own record, read from node
const reach = (page) => page.evaluate((u) => fetch(u, { mode: "no-cors", cache: "no-store" }).then(() => "ok", (e) => String(e)), cfg.remote + "/reach-" + cfg.scene);
const out = { errors };
if (cfg.scene === "notice") {
  const page = await context.newPage();
  page.on("pageerror", (e) => errors.push(String(e).slice(0, 300)));
  const own = [];        // the same-origin control's responses: the kernel's answer, as the browser received it
  page.on("response", (r) => { if (r.url() === cfg.own) own.push({ status: r.status(), referrerPolicy: r.headers()["referrer-policy"] || null }); });
  await page.goto(cfg.feed);
  const sel = '[data-key="a:' + cfg.itemId + '"]';
  await page.waitForSelector(sel + " .fask-nbody svg", { timeout: 60000 }).catch(() => {});
  const t0 = Date.now();
  while (Date.now() - t0 < 15000 && !own.length) await sleep(50);
  out.ownWaitMs = Date.now() - t0;
  await sleep(1500);     // the drain: a remote paint request the card made would have reached the logger by now
  out.own = own.slice();
  out.card = await page.evaluate((s) => {
    const c = document.querySelector(s); if (!c) return null;
    const b = c.querySelector(".fask-nbody"); const cs = getComputedStyle(c);
    // every attribute of every element in the body, as `tag[name]` and its value: the DOM the page adopted, not its text
    const attrs = b ? Array.from(b.querySelectorAll("*")).flatMap((e) => Array.from(e.attributes).map((a) => ({ at: e.tagName.toLowerCase() + "[" + a.name + "]", value: a.value }))) : [];
    return { col: c.parentElement && c.parentElement.id, vis: c.offsetHeight > 0 && cs.display !== "none", html: b ? b.innerHTML : null,
             svgs: b ? b.querySelectorAll("svg").length : 0, attrs };
  }, sel);
  out.pageUrl = page.url();
  out.reach = await reach(page);
} else {
  // the viewer: the session's tab, the file link in its reply, the viewer's placeholder, one click, then the arrivals
  const viewer = async (frame, file, prefix) => {
    const r = {};
    await frame.waitForSelector("#tabs .tab[data-id]", { timeout: 30000 });
    await frame.click('#tabs .tab[data-id="' + cfg.sid + '"]');
    const link = '#content .file-uri-link[data-path="' + file + '"]';
    await frame.waitForSelector(link, { timeout: 30000 });
    await frame.click(link);
    // the file rendered: its heading is in the viewer, and the gate ran on the same inert body before it was adopted
    await frame.waitForSelector('#romp-fileview [id="md-figures"]', { timeout: 30000 });
    await sleep(1000);   // a request an ungated figure made on open would have landed by now
    r.gatedHosts = await frame.evaluate(() => Array.from(document.querySelectorAll('#romp-fileview [data-act="fv-load"]')).map((g) => g.getAttribute("data-fv-host")));
    r.beforeClick = (await logNow()).filter((l) => l.path.startsWith("/" + prefix)).map((l) => l.path);
    if (r.gatedHosts.length) await frame.click('#romp-fileview [data-act="fv-load"]');   // one click loads every figure of that host
    await sleep(200);
    r.leftGated = await frame.evaluate(() => document.querySelectorAll('#romp-fileview [data-act="fv-load"]').length);
    const t0 = Date.now();
    while (Date.now() - t0 < 15000) {
      const got = (await logNow()).map((l) => l.path);
      if (cfg.awaited.every((n) => got.includes("/" + prefix + n))) break;
      await sleep(100);
    }
    r.waitMs = Date.now() - t0;
    await sleep(1500);   // the drain: every request the click set off has landed
    r.url = frame.url();
    return r;
  };
  const bare = await context.newPage();
  bare.on("pageerror", (e) => errors.push("bare: " + String(e).slice(0, 300)));
  await bare.goto(cfg.chat);
  out.bare = await viewer(bare.mainFrame(), cfg.files.bare, "B-");
  const shell = await context.newPage();
  shell.on("pageerror", (e) => errors.push("shell: " + String(e).slice(0, 300)));
  await shell.goto(cfg.shell);
  let chat = null;
  const t0 = Date.now();
  while (!chat && Date.now() - t0 < 30000) {
    chat = shell.frames().find((f) => { try { return f !== shell.mainFrame() && new URL(f.url()).pathname === "/chat"; } catch (e) { return false; } }) || null;
    if (!chat) await sleep(100);
  }
  if (!chat) { console.error("the shell framed no /chat pane: " + JSON.stringify(shell.frames().map((f) => f.url()))); process.exit(1); }
  out.framed = await viewer(chat, cfg.files.framed, "F-");
  out.framed.shellUrl = shell.url();
  out.reach = await reach(bare);
}
fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
await browser.close();
process.exit(0);
"""


class _Logger(BaseHTTPRequestHandler):
    """The second server: logs every request's path and the headers that say who asked and what rode along (Referer,
    Sec-Fetch-Dest, Sec-Fetch-Site, Cookie, Host) into the class's list, answers a paint document for any .svg and a PNG
    for any .png, and serves its own log at /__log (not logged: the driver's wait reads it)."""
    log = None

    def do_GET(self):
        if self.path == "/__log":
            body = json.dumps(self.log).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
        self.log.append({"path": self.path, "referer": self.headers.get("Referer"), "dest": self.headers.get("Sec-Fetch-Dest"),
                         "site": self.headers.get("Sec-Fetch-Site"), "cookie": self.headers.get("Cookie"),
                         "host": self.headers.get("Host")})
        p = self.path.split("?")[0]
        if p.endswith(".svg"):
            body, ctype = (b'<svg xmlns="http://www.w3.org/2000/svg"><defs><pattern id="p" width="1" height="1"><rect width="1" '
                           b'height="1" fill="blue"/></pattern><mask id="m"><rect width="1" height="1" fill="white"/></mask></defs>'
                           b'</svg>'), "image/svg+xml"
        elif p.endswith(".png"):
            body, ctype = _png(), "image/png"
        else:
            body, ctype = b"", "text/plain"
        self.send_response(200); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)

    def log_message(self, *a):   # quiet: the log above is the record
        pass


class PaintRefsOnKernelPages(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        try:
            cls._boot()
        except BaseException:          # a skip OR a failure: never leave a kernel or a lab behind
            cls.tearDownClass()
            raise

    @classmethod
    def _boot(cls):
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            raise unittest.SkipTest("extension deps absent (npm ci not run here): the served lab needs them; CI's extension job has them and requires this file to run")
        probe = subprocess.run(["node", "-e", "const p=require(process.argv[1]);process.stdout.write(p.chromium.executablePath())",
                                os.path.join(EXT, "node_modules", "playwright")], capture_output=True, text=True)
        if probe.returncode != 0 or not os.path.exists(probe.stdout.strip()):
            raise unittest.SkipTest("no playwright browser on this box: the served lab needs one; CI's extension job installs Chromium and requires this file to run")
        cls.lab = tempfile.mkdtemp(prefix="paint-pages-")
        # the logger, with its stop registered before its start so it runs on every exit path (a failed boot included)
        cls.remote_log = []
        srv = ThreadingHTTPServer(("127.0.0.1", 0), type("Logger", (_Logger,), {"log": cls.remote_log}))
        thread = threading.Thread(target=srv.serve_forever, daemon=True)

        def end_remote():   # shutdown() waits for serve_forever to return, which a thread never started never does
            if thread.ident is not None:
                srv.shutdown()
            srv.server_close()
        cls.addClassCleanup(end_remote)
        thread.start()
        cls.log_url = "http://127.0.0.1:%d/__log" % srv.server_address[1]
        cls.remote = "http://%s:%d" % (REMOTE_HOST, srv.server_address[1])   # the viewer scene's name for the logger
        cls.notice_remote = "http://localhost:%d" % srv.server_address[1]     # the notice scene's: Sec-Fetch headers ride to it
        dist = os.path.join(cls.lab, "dist")
        lab_dist.copy_dist(dist)   # the checkout's ONE build of the bundles, copied under its lock (tests/lab_dist.py)
        state = os.path.join(cls.lab, "xdg", "romp")
        cwd = os.path.join(cls.lab, "proj")
        for d in ("names", "sdk", "states"):
            os.makedirs(os.path.join(state, d), exist_ok=True)
        os.makedirs(os.path.join(cwd, "docs"), exist_ok=True)
        Path(cwd, "docs", "figs-bare.md").write_text(_figures(cls.remote, "B-"))
        Path(cwd, "docs", "figs-framed.md").write_text(_figures(cls.remote, "F-"))
        Path(state, "names", SID).write_text("web\t%s\t#9cd2ff\t#0c1a2e\n" % cwd)
        Path(state, "sdk", SID + ".json").write_text(json.dumps(
            {"sid": SID, "name": "web", "cwd": cwd, "mode": "auto", "effort": "high", "lastSid": SID, "alive": True,
             "model": "claude-opus-5", "liveModel": "Opus 5"}))
        claude = os.path.join(cls.lab, "claude")
        proj = os.path.join(claude, "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(cwd)))
        os.makedirs(proj, exist_ok=True)
        reply = "The sweep's figures are in docs/figs-bare.md, and the same set again in docs/figs-framed.md."
        Path(proj, SID + ".jsonl").write_text(
            json.dumps({"type": "user", "uuid": U_UUID, "parentUuid": None, "timestamp": "2026-09-05T00:00:00.000Z", "sessionId": SID,
                        "message": {"role": "user", "content": "Where are the figures from the sweep?"}}) + "\n" +
            json.dumps({"type": "assistant", "uuid": A_UUID, "parentUuid": U_UUID, "timestamp": "2026-09-05T00:00:05.000Z", "sessionId": SID,
                        "message": {"role": "assistant", "model": "claude-opus-5", "content": [{"type": "text", "text": reply}], "stop_reason": "end_turn"}}) + "\n")
        cls.port, cls.token = _free_port(), "testtok-paintpages"
        cls.origin = "http://127.0.0.1:%d" % cls.port
        env = _lab.kernel_env(cls.lab, claude, dist, cls.port, cls.token, ROMP_HOST_NAME="TESTHOST")
        cls.klog = os.path.join(cls.lab, "kernel.log")
        cls.kernel = subprocess.Popen([os.path.join(BIN, "romp-kernel")], stdout=open(cls.klog, "w"), stderr=subprocess.STDOUT, env=env)
        for _ in range(120):
            try:
                urllib.request.urlopen(cls.origin + "/healthz", timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise unittest.SkipTest("hermetic kernel never served /healthz here")

    @classmethod
    def tearDownClass(cls):
        k = getattr(cls, "kernel", None)
        if k:
            k.kill(); k.wait()
        shutil.rmtree(getattr(cls, "lab", ""), ignore_errors=True)

    def _drive(self, scene, extra):
        cfg = os.path.join(self.lab, "cfg-%s.json" % scene)
        with open(cfg, "w") as f:
            json.dump(dict({"scene": scene, "remote": self.remote, "remoteHost": REMOTE_HOST, "logUrl": self.log_url, "sid": SID}, **extra), f)
        driver = os.path.join(self.lab, "driver.mjs")
        with open(driver, "w") as f:
            f.write(DRIVER)
        p = subprocess.run(["node", driver], capture_output=True, text=True, timeout=300,
                           env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg))
        if p.returncode == 3:
            raise unittest.SkipTest("no playwright browser on this box: the served lab needs one; CI's extension job installs Chromium and requires this file to run")
        self.assertEqual(p.returncode, 0, "driver failed:\n" + p.stdout[-3000:] + p.stderr[-3000:] + "\nkernel:\n" + open(self.klog).read()[-1500:])
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
        self.assertIsNotNone(line, "driver printed no result:\n" + p.stdout[-3000:])
        return json.loads(line[len("RESULT:"):])

    def _logged(self, prefix):
        return [l for l in list(self.remote_log) if l["path"].startswith("/" + prefix)]

    def test_a_notice_card_s_paint_references_reach_no_other_host(self):
        req = urllib.request.Request(self.origin + "/notice", method="POST",
                                     data=json.dumps({"id": SID, "key": "paint", "title": "A new version of the accuracy figure is ready",
                                                      "producer": "figure", "body": _notice_body(self.notice_remote, self.origin)}).encode(),
                                     headers={"X-Romp-Token": self.token, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            posted = json.loads(resp.read() or b"{}")
        self.assertTrue(posted.get("ok"), "the kernel accepted the notice: %r" % posted)
        own = self.origin + "/media/romp-swirl-glyph.svg?own=notice"
        r = self._drive("notice", {"remote": self.notice_remote, "feed": self.origin + "/feed?token=" + self.token, "own": own,
                                   "itemId": "notice:%s:paint:%s" % (SID, posted["notice"]["rev"])})
        card = r["card"] or {}
        attrs = card.get("attrs") or []
        print("NOTICE:", json.dumps({"driver": r, "log": self._logged("N-")}), file=sys.stderr)
        with self.subTest("no page error"):
            self.assertEqual(r["errors"], [], "no page error")
        with self.subTest("the feed page was opened bare"):
            self.assertIn("token=" + self.token, r["pageUrl"], "the feed page's own address carries the token")
        with self.subTest("the card is on the board"):
            self.assertTrue(card.get("vis"), "the notice card is on the board and shown: %r" % r["card"])
        with self.subTest("the body's inline svgs survived the sanitizer"):
            self.assertGreaterEqual(card.get("svgs", 0), 7, "the body's seven inline svgs are in the card: %s" % card.get("html"))
        # the positive control: the card painted and this browser fetched the paint reference the pass keeps
        with self.subTest("the absolute same-origin control was requested from the kernel"):
            self.assertTrue(r["own"] and r["own"][0]["referrerPolicy"] == "same-origin",
                            "the same-origin paint reference was requested and the kernel answered it (%s ms): %r" % (r["ownWaitMs"], r["own"]))
        with self.subTest("the absolute same-origin control stands in the card as written"):
            self.assertIn({"at": "rect[fill]", "value": "url(%s#p)" % own}, attrs, "the same-origin reference stands in the card")
        # the fix: sanitizeMd's paint pass and the strip's paint arm removed every remote url() on the inert body
        with self.subTest("no request reached the logger"):
            self.assertEqual(self._logged("N-"), [], "the notice card's body made requests to another host; each with its path, "
                             "Referer, Sec-Fetch-Dest, Sec-Fetch-Site and Cookie")
        with self.subTest("no attribute in the card names the logger"):
            self.assertEqual([a for a in attrs if self.notice_remote in a["value"]], [], "an attribute in the card names the logger")
        with self.subTest("the page reached the logger"):
            self.assertEqual(r["reach"], "ok", "the feed page's no-cors fetch to the logger completed")
        with self.subTest("the logger logged the reach once"):
            self.assertEqual([l["path"] for l in self.remote_log if l["path"] == "/reach-notice"], ["/reach-notice"], "the logger logged the reach fetch once")

    def test_a_figure_the_viewer_loads_on_a_click_sends_at_most_the_page_s_origin(self):
        r = self._drive("viewer", {"chat": self.origin + "/chat?token=" + self.token, "shell": self.origin + "/?token=" + self.token,
                                   "files": {"bare": "docs/figs-bare.md", "framed": "docs/figs-framed.md"},
                                   "awaited": list(VIEWER_AWAITED)})
        print("VIEWER:", json.dumps({"driver": r, "log": {n: self._logged(p) for n, p in (("bare", "B-"), ("framed", "F-"))}}), file=sys.stderr)
        with self.subTest("no page error"):
            self.assertEqual(r["errors"], [], "no page error")
        with self.subTest("the bare chat page's address carries the token"):
            self.assertIn("token=" + self.token, r["bare"]["url"], "the bare chat page's own address carries the token")
        with self.subTest("the framed chat pane's address carries no token"):
            self.assertNotIn("token=", r["framed"]["url"], "the framed chat pane's address carries no token")
        with self.subTest("the shell dropped the token from its address"):
            self.assertNotIn("token=", r["framed"]["shellUrl"], "the shell dropped the token from its address")
        for name, prefix in (("bare", "B-"), ("framed", "F-")):
            s = r[name]
            logged = self._logged(prefix)
            paths = [l["path"] for l in logged]
            with self.subTest(name + ": the viewer gated the logger's host"):
                self.assertEqual(s["gatedHosts"][:1], [REMOTE_HOST], "the viewer gated the logger's host: %r" % s["gatedHosts"])
            with self.subTest(name + ": nothing reached the logger before the click"):
                self.assertEqual(s["beforeClick"], [], "no figure reached the logger before the click")
            with self.subTest(name + ": one click restored every figure of the host"):
                self.assertEqual(s["leftGated"], 0, "one click restored every figure of the host")
            with self.subTest(name + ": the awaited figures reached the logger after the click"):
                self.assertEqual([n for n in VIEWER_AWAITED if "/" + prefix + n not in paths], [],
                                 "figures that did not reach the logger after the click (%s ms): %r" % (s["waitMs"], logged))
            with self.subTest(name + ": each request carried no Referer or the page's origin alone"):
                self.assertEqual([l for l in logged if l["referer"] not in (None, self.origin + "/")], [],
                                 "a figure's request named more of the page than its origin (a path, a query, the token)")
        with self.subTest("the page reached the logger"):
            self.assertEqual(r["reach"], "ok", "the chat page's no-cors fetch to the logger completed")
        with self.subTest("the logger logged the reach once"):
            self.assertEqual([l["path"] for l in self.remote_log if l["path"] == "/reach-viewer"], ["/reach-viewer"], "the logger logged the reach fetch once")

if __name__ == "__main__":
    unittest.main()
