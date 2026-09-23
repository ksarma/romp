#!/usr/bin/env python3
"""An .svg opened in its own tab loads nothing from another host (the 2026-09-23 policy, kernel.py _media_policy_headers).

On the web dashboard a Cmd, Ctrl or middle click on a path link to an .svg in a viewed file opens the kernel's /file URL in
its own tab (ui/webview/preview.ts openFileTab, fileUrl), and for a remote session's file the /remote/<host>/file relay's
URL. The kernel serves the file as image/svg+xml, so the tab is an svg DOCUMENT. Under the bare `sandbox` policy the kernel
sent before this change, that document ran no script but still fetched every host its markup named (executed in
Chromium, 2026-09-23). The policy now carries four fetch directives beside `sandbox` in one value: default-src
'none', and img-src data: blob:, style-src 'unsafe-inline' and font-src data:, which keep an exported figure's inline
raster, styles and fonts.

This module runs two hermetic lab kernels (the served labs' environment, tests/test_ship_reship_served.py kernel_env, each
with its own state root, port and token): the hub, which serves one synthetic session's docs/diagram.svg on /file, and a
second kernel the hub relays to as host gpu1 (registered through the hub's own check-in handshake, POST /checkin), which
serves its session's docs/diagram.svg behind /remote/gpu1/file. A request logger on http://localhost:Q is a second origin
and a second site to the pages (they are served from 127.0.0.1), and the browser holds two cookies for its host, one
SameSite=None and one Lax. Each diagram carries sixteen load shapes aimed at the logger under a per-tab path prefix: the
seven measured first (an <image> href, an <image> xlink:href, a CSS @import, a foreignObject <img>, a fill,
a mask and a CSS fill paint reference) and nine more that a probe of this change found loading under the bare `sandbox`
(an <feImage> href, a CSS cursor, a background image, an @font-face source, and in a foreignObject a stylesheet <link>, an
image preload, a prefetch, an <iframe> and a <video>); then a 40 by 40 data: PNG raster at the top left, and below it a
rect filled by an inline <style> rule.

test_the_policy_rides_every_svg_success_on_the_route_and_the_relay asks both kernels' wire for the headers: the hub's /file
and its relay each answer a GET (200), a HEAD and a suffix Range (206) for the diagram with the policy, compared as the
whole list of Content-Security-Policy values (the 200 also carries _send's frame-ancestors policy), and a PNG with neither.

test_an_svg_tab_on_the_route_and_the_relay_loads_nothing_external drives Playwright's Chromium the way the gesture does:
a kernel-origin page that holds the serve cookie window.opens each fileUrl (no token in the tab's URL) and severs the
opener. Asserted: each tab's document came with the policy, the logger received no request under either tab's prefix, the
data: raster DREW and the inline style APPLIED (both read back as pixels from a screenshot of the tab: default-src 'none'
alone refuses both). font-src data: and the blob: source are in the policy and not witnessed here (the markup carries no
embedded font, and a document that runs no script makes no blob:). Two controls say an empty log is the policy's work. A
third tab opens the same markup from a control server on 127.0.0.1 that sends the kernel's headers less the four fetch
directives (a bare `sandbox`), after the two witness tabs; the driver waits (bounded, 15 s) until every one of the
sixteen shapes has reached the logger from that tab, then drains 1.5 s more before it reads the log, so a request
either witness tab had made would have arrived. Then the kernel-origin page fetches the logger once (no-cors), which must
be its one /reach line. Red before this change (6e6ddf7d5's kernel, its bare `sandbox`, under this file, 2026-09-23): the
header test failed on all six svg responses, and the tab test's logger received all sixteen loads from each tab, the
paint references and the font with no cookie, the other twelve with the SameSite=None cookie, the Lax cookie on none,
and none with a Referer. Under default-src 'none' without img-src data: blob: the raster subtests go red, and without
style-src 'unsafe-inline' the style subtests do.

Skips LOUDLY without the extension deps or a Playwright browser; the CI extension job installs Chromium and runs served
files with ROMP_SERVED_TESTS_REQUIRE=1, which turns any skip into a failure there. SYNTHETIC fixtures only (session web,
the notes-api demo world, placeholder uuids, host gpu1)."""
import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
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

SID = "aaaaaaaa-1111-2222-3333-444444444444"          # the hub's session
SID_B = "bbbbbbbb-1111-2222-3333-444444444444"        # the relayed kernel's session
# The policy, written out here and never read from the kernel: a pin that compared the response with the kernel's
# own value would move with it (tests/test_kernel_preview.py SVG_DOCUMENT_POLICY holds the same text in process).
SVG_DOCUMENT_POLICY = "sandbox; default-src 'none'; img-src data: blob:; style-src 'unsafe-inline'; font-src data:"
FRAMING_POLICY = "frame-ancestors 'self'"   # _send's, on every 200
RASTER_RGB = (0, 160, 80)                   # the data: raster's one colour, read back from the tab's pixels
STYLED_RGB = (40, 40, 200)                  # the fill an inline <style> rule gives one rect (unstyled, it would be black)
# the load shapes, by the file name each asks the logger for (the tab's prefix goes in front): the seven measured
# first, and nine more that a probe of this change found loading under the bare `sandbox` too (2026-09-23;
# an <object> loaded in the probe and not in every run of this tab, so it is not among them)
RULED_SHAPES = ("import.css", "image.png", "ximage.png", "fo-img.png", "fill.svg", "mask.svg", "cssfill.svg")
MORE_SHAPES = ("feimage.png", "cursor.png", "bgimg.png", "font.woff", "link.css", "preload.png", "prefetch.txt",
               "frame.html", "video.mp4")
SHAPES = RULED_SHAPES + MORE_SHAPES


def _png(w, h, rgb):
    """A valid PNG of one colour (RGB, no filter) without a binary fixture."""
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


def _diagram(remote, prefix):
    """An exported-figure-shaped svg: the data: raster at the top left, a rect below it filled by an inline <style> rule,
    and every load shape in SHAPES aimed at the logger (`remote`, http://localhost:Q) under `prefix`, each drawn clear of
    both."""
    r = remote + "/" + prefix
    raster = base64.b64encode(_png(40, 40, RASTER_RGB)).decode("ascii")
    return ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="400" height="160">'
            '<style><![CDATA[@import url("%(r)simport.css"); rect.cf { fill: url("%(r)scssfill.svg#p"); } '
            'rect.st { fill: rgb(%(st)s); } @font-face { font-family: F; src: url("%(r)sfont.woff"); } '
            'text { font-family: F; } rect.cu { cursor: url("%(r)scursor.png"), auto; }]]></style>'
            '<image id="raster" x="0" y="0" width="40" height="40" xlink:href="data:image/png;base64,%(raster)s"/>'
            '<image x="60" y="0" width="20" height="20" href="%(r)simage.png"/>'
            '<image x="90" y="0" width="20" height="20" xlink:href="%(r)sximage.png"/>'
            '<foreignObject x="120" y="0" width="30" height="30">'
            '<img xmlns="http://www.w3.org/1999/xhtml" src="%(r)sfo-img.png" width="20" height="20"/></foreignObject>'
            '<rect x="160" y="0" width="20" height="20" fill="url(%(r)sfill.svg#p)"/>'
            '<rect x="190" y="0" width="20" height="20" fill="red" mask="url(%(r)smask.svg#m)"/>'
            '<rect class="cf" x="220" y="0" width="20" height="20"/>'
            '<rect class="st" x="0" y="50" width="40" height="40"/>'
            '<filter id="fi"><feImage href="%(r)sfeimage.png"/></filter>'
            '<rect x="250" y="0" width="20" height="20" filter="url(#fi)"/>'
            '<rect class="cu" x="280" y="0" width="20" height="20"/>'
            '<text x="310" y="15">F</text>'
            '<foreignObject x="60" y="50" width="330" height="100"><div xmlns="http://www.w3.org/1999/xhtml">'
            '<link rel="stylesheet" href="%(r)slink.css"/><link rel="preload" as="image" href="%(r)spreload.png"/>'
            '<link rel="prefetch" href="%(r)sprefetch.txt"/>'
            '<div style="width:20px;height:20px;background-image:url(%(r)sbgimg.png)"></div>'
            '<iframe src="%(r)sframe.html" width="20" height="20"></iframe>'
            '<video src="%(r)svideo.mp4" width="20" height="20"></video>'
            '</div></foreignObject>'
            '</svg>') % {"r": r, "raster": raster, "st": ", ".join(str(c) for c in STYLED_RGB)}


DRIVER = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const { chromium } = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
let browser;
try { browser = await chromium.launch(); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const context = await browser.newContext({ viewport: { width: 800, height: 600 }, deviceScaleFactor: 1 });
// the logger's host holds two cookies in this browser: SameSite=None (sent on a cross-site subresource load) and Lax (never)
await context.addCookies([
  { name: "xs_none", value: "1", domain: "localhost", path: "/", sameSite: "None", secure: true },
  { name: "xs_lax", value: "1", domain: "localhost", path: "/", sameSite: "Lax" },
]);
const docs = {};       // the tab documents' responses as the browser received them: status, type and every CSP value
context.on("response", async (r) => {
  const u = r.url();
  const name = Object.keys(cfg.tabs).find((k) => u === cfg.tabs[k]);
  if (!name) return;
  const hs = await r.headersArray();
  docs[name] = { status: r.status(), type: (hs.find((h) => h.name.toLowerCase() === "content-type") || {}).value || null,
                 csp: hs.filter((h) => h.name.toLowerCase() === "content-security-policy").map((h) => h.value) };
});
const seen = [];       // every request the browser issued to the logger, for the record (the logger's own log is the assertion)
context.on("request", (r) => { if (r.url().startsWith(cfg.remote)) seen.push(r.url()); });
const console_ = [];
context.on("console", (m) => console_.push(m.text().slice(0, 300)));
// a kernel-origin page holding the serve cookie, as the dashboard does: the token once in its address, the cookie after
const opener = await context.newPage();
await opener.goto(cfg.cookiePage);
const helper = await context.newPage();   // reads a screenshot's pixels back on a canvas (a data: image taints nothing)
const pixel = async (png, x, y) => helper.evaluate(async ([b64, x, y]) => {
  const img = new Image(); img.src = "data:image/png;base64," + b64; await img.decode();
  const c = document.createElement("canvas"); c.width = img.width; c.height = img.height;
  const g = c.getContext("2d"); g.drawImage(img, 0, 0);
  return Array.from(g.getImageData(x, y, 1, 1).data);
}, [png.toString("base64"), x, y]);
// the gesture: ONE window.open of the file's URL from the kernel-origin page, the opener severed on the handle
const openTab = async (name) => {
  const [tab] = await Promise.all([
    context.waitForEvent("page", { timeout: 15000 }),
    opener.evaluate((u) => { const w = window.open(u, "_blank"); if (w) { try { w.opener = null; } catch (e) {} } return !!w; }, cfg.tabs[name]),
  ]);
  await tab.waitForLoadState("load", { timeout: 15000 });
  await tab.waitForTimeout(300);
  const shot = await tab.screenshot({ clip: { x: 0, y: 0, width: 60, height: 100 } });
  return { url: tab.url(), raster: await pixel(shot, 20, 20), beside: await pixel(shot, 50, 20), styled: await pixel(shot, 20, 70) };
};
const out = { tabs: {} };
out.tabs.local = await openTab("local");
out.tabs.relay = await openTab("relay");
// the control tab, opened AFTER the witnesses: the same markup under the kernel's headers less the fetch directives. Every
// shape it names must reach the logger (bounded), and the log is read only after a further drain
out.tabs.control = await openTab("control");
const logNow = async () => (await (await fetch(cfg.remote + "/__log")).json());
const t0 = Date.now();
let arrived = [];
while (Date.now() - t0 < 15000) {
  arrived = (await logNow()).map((l) => l.path).filter((p) => p.startsWith("/" + cfg.controlPrefix));
  if (cfg.shapes.every((s) => arrived.includes("/" + cfg.controlPrefix + s))) break;
  await new Promise((r) => setTimeout(r, 100));
}
out.controlWaitMs = Date.now() - t0;
await new Promise((r) => setTimeout(r, 1500));
// the logger's reach control, after the record: one no-cors fetch from the kernel-origin page
out.reach = await opener.evaluate((u) => fetch(u, { mode: "no-cors", cache: "no-store" }).then(() => "ok", (e) => String(e)), cfg.remote + "/reach");
out.docs = docs;
out.seen = seen;
out.console = console_;
fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
await browser.close();
process.exit(0);
"""


class _Logger(BaseHTTPRequestHandler):
    """The second server: logs every request's path and the headers that say who asked and what rode along (Cookie,
    Referer, Sec-Fetch-Dest, Sec-Fetch-Site) into the class's list, answers a paint document for any .svg, a PNG for any
    .png and a stylesheet for any .css, and serves its own log at /__log (not logged: the driver's wait reads it)."""
    log = None

    def do_GET(self):
        if self.path == "/__log":
            body = json.dumps(self.log).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
        self.log.append({"path": self.path, "cookie": self.headers.get("Cookie"), "referer": self.headers.get("Referer"),
                         "dest": self.headers.get("Sec-Fetch-Dest"), "site": self.headers.get("Sec-Fetch-Site")})
        p = self.path.split("?")[0]
        if p.endswith(".svg"):
            body, ctype = (b'<svg xmlns="http://www.w3.org/2000/svg"><defs><pattern id="p" width="1" height="1"><rect width="1" '
                           b'height="1" fill="blue"/></pattern><mask id="m"><rect width="1" height="1" fill="white"/></mask></defs>'
                           b'</svg>'), "image/svg+xml"
        elif p.endswith(".png"):
            body, ctype = _png(2, 2, (200, 60, 60)), "image/png"
        elif p.endswith(".css"):
            body, ctype = b"rect { stroke: none; }", "text/css"
        else:
            body, ctype = b"", "text/plain"
        self.send_response(200); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)

    def log_message(self, *a):   # quiet: the log above is the record
        pass


class _Control(BaseHTTPRequestHandler):
    """The control server: the control diagram at /control.svg under the kernel's 200 headers less the four fetch
    directives (a bare `sandbox`, the policy before this change), so the only difference between its tab and the
    witness tabs is what the change added."""
    body = b""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml")
        self.send_header("Content-Length", str(len(self.body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Content-Security-Policy", FRAMING_POLICY)
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "sandbox")
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *a):
        pass


def _serve(cls, host, handler):
    """Start `handler` on `host` at a free port with its stop registered first, so it runs on every exit path (a failed
    boot included); returns the server."""
    srv = ThreadingHTTPServer((host, 0), handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)

    def end():   # shutdown() waits for serve_forever to return, which a thread never started never does
        if thread.ident is not None:
            srv.shutdown()
        srv.server_close()
    cls.addClassCleanup(end)
    thread.start()
    return srv


class SvgTabPolicy(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        try:
            cls._boot()
        except BaseException:          # a skip OR a failure: never leave a kernel or a lab behind
            cls.tearDownClass()
            raise

    @classmethod
    def _kernel(cls, name, dist, host_name):
        """One lab kernel under <lab>/<name>: a state root with one session (`web`) whose cwd holds docs/diagram.svg,
        docs/readme.md and plots/figure.png. Returns (port, token, cwd)."""
        lab = os.path.join(cls.lab, name)
        state = os.path.join(lab, "xdg", "romp")
        cwd = os.path.join(lab, "proj")
        for d in ("names", "sdk", "states"):
            os.makedirs(os.path.join(state, d), exist_ok=True)
        for d in ("docs", "plots"):
            os.makedirs(os.path.join(cwd, d), exist_ok=True)
        sid = SID if name == "hub" else SID_B
        Path(state, "names", sid).write_text("web\t%s\t#9cd2ff\t#0c1a2e\n" % cwd)
        Path(state, "sdk", sid + ".json").write_text(json.dumps(
            {"sid": sid, "name": "web", "cwd": cwd, "mode": "auto", "effort": "high", "lastSid": sid, "alive": True,
             "model": "claude-opus-5", "liveModel": "Opus 5"}))
        Path(cwd, "docs", "readme.md").write_text("# notes-api\n\nThe diagram is docs/diagram.svg.\n")
        Path(cwd, "plots", "figure.png").write_bytes(_png(2, 2, (60, 120, 200)))
        claude = os.path.join(lab, "claude")
        os.makedirs(os.path.join(claude, "projects"), exist_ok=True)
        port, token = _free_port(), "testtok-svgtab-" + name
        env = _lab.kernel_env(lab, claude, dist, port, token, ROMP_HOST_NAME=host_name)
        klog = os.path.join(lab, "kernel.log")
        proc = subprocess.Popen([os.path.join(BIN, "romp-kernel")], stdout=open(klog, "w"), stderr=subprocess.STDOUT, env=env)
        cls.kernels.append((proc, klog))
        for _ in range(120):
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/healthz" % port, timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise unittest.SkipTest("hermetic kernel %s never served /healthz here" % name)
        return port, token, cwd

    @classmethod
    def _boot(cls):
        cls.kernels = []
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            raise unittest.SkipTest("extension deps absent (npm ci not run here): the served lab needs them; CI's extension job has them and requires this file to run")
        probe = subprocess.run(["node", "-e", "const p=require(process.argv[1]);process.stdout.write(p.chromium.executablePath())",
                                os.path.join(EXT, "node_modules", "playwright")], capture_output=True, text=True)
        if probe.returncode != 0 or not os.path.exists(probe.stdout.strip()):
            raise unittest.SkipTest("no playwright browser on this box: the served lab needs one; CI's extension job installs Chromium and requires this file to run")
        cls.lab = tempfile.mkdtemp(prefix="svg-tab-")
        # the logger: another origin and another site to the pages (http.server binds IPv4, where this box's `localhost`
        # resolves; the reach control in the driver is the check that the browser reaches it there)
        cls.remote_log = []
        cls.remote_srv = _serve(cls, "localhost", type("Logger", (_Logger,), {"log": cls.remote_log}))
        cls.remote = "http://localhost:%d" % cls.remote_srv.server_address[1]
        cls.control_srv = _serve(cls, "127.0.0.1", type("Control", (_Control,), {"body": _diagram(cls.remote, "C-").encode()}))
        dist = os.path.join(cls.lab, "dist")
        lab_dist.copy_dist(dist)   # the checkout's ONE build of the bundles, copied under its lock (tests/lab_dist.py)
        cls.port, cls.token, hub_cwd = cls._kernel("hub", dist, "TESTHOST")
        cls.port_b, cls.token_b, b_cwd = cls._kernel("gpu1", dist, "gpu1")
        Path(hub_cwd, "docs", "diagram.svg").write_text(_diagram(cls.remote, "L-"))
        Path(b_cwd, "docs", "diagram.svg").write_text(_diagram(cls.remote, "R-"))
        # the hub files the second kernel as host gpu1 through its own check-in handshake: the relay then dials
        # 127.0.0.1:<kernelPort> with that kernel's token, the row an attached host's tunnel would give it
        req = urllib.request.Request("http://127.0.0.1:%d/checkin" % cls.port, method="POST",
                                     data=json.dumps({"host": "gpu1", "kernelPort": cls.port_b, "busPort": _free_port(),
                                                      "token": cls.token_b}).encode(),
                                     headers={"X-Romp-Token": cls.token, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            got = json.loads(r.read() or b"{}")
        if not got.get("ok"):
            raise AssertionError("the hub refused the check-in: %r" % got)

    @classmethod
    def tearDownClass(cls):
        for proc, _ in getattr(cls, "kernels", []):
            proc.kill(); proc.wait()
        shutil.rmtree(getattr(cls, "lab", ""), ignore_errors=True)

    def _logs(self):
        return "".join("\n%s:\n%s" % (klog, open(klog).read()[-1500:]) for _, klog in self.kernels)

    def _url(self, route, path, sid):
        # fileUrl's shape (ui/webview/preview.ts): the path and the bare sid, never a token
        return "http://127.0.0.1:%d%s?path=%s&sid=%s" % (self.port, route, urllib.parse.quote(path, safe=""), sid)

    def _policies(self, url, method="GET", headers=None):
        req = urllib.request.Request(url, method=method, headers=dict(headers or {}, **{"X-Romp-Token": self.token}))
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status, r.headers.get("Content-Type"), r.headers.get_all("Content-Security-Policy") or []
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get("Content-Type"), e.headers.get_all("Content-Security-Policy") or []

    def test_the_policy_rides_every_svg_success_on_the_route_and_the_relay(self):
        # the whole list of policies each response carries, so a weakened or missing directive fails, as does a relay
        # that mirrored the remote kernel's header beside its own (the remote's own value would then appear twice)
        for arm, route, sid in (("route", "/file", SID), ("relay", "/remote/gpu1/file", SID_B)):
            url = self._url(route, "docs/diagram.svg", sid)
            for method, headers, want, policies in (("GET", None, 200, [SVG_DOCUMENT_POLICY, FRAMING_POLICY]),
                                                    ("HEAD", None, 200, [SVG_DOCUMENT_POLICY]),
                                                    ("GET", {"Range": "bytes=1-"}, 206, [SVG_DOCUMENT_POLICY])):
                with self.subTest(arm=arm, method=method, range=bool(headers)):
                    status, ctype, got = self._policies(url, method, headers)
                    self.assertEqual((status, ctype), (want, "image/svg+xml"), self._logs())
                    self.assertEqual(sorted(got), sorted(policies),
                                     "%s %s%s: every Content-Security-Policy value the svg's response carries"
                                     % (arm, method, " (range)" if headers else ""))
        with self.subTest("a PNG carries neither the sandbox nor a fetch directive"):
            status, _, got = self._policies(self._url("/file", "plots/figure.png", SID))
            self.assertEqual(status, 200)
            self.assertEqual(got, [FRAMING_POLICY], "a picture is never a document: _send's framing policy alone")

    def test_an_svg_tab_on_the_route_and_the_relay_loads_nothing_external(self):
        tabs = {"local": self._url("/file", "docs/diagram.svg", SID),
                "relay": self._url("/remote/gpu1/file", "docs/diagram.svg", SID_B),
                "control": "http://127.0.0.1:%d/control.svg" % self.control_srv.server_address[1]}
        cfg = os.path.join(self.lab, "cfg.json")
        with open(cfg, "w") as f:
            json.dump({"cookiePage": self._url("/file", "docs/readme.md", SID) + "&token=" + self.token, "tabs": tabs,
                       "remote": self.remote, "controlPrefix": "C-", "shapes": list(SHAPES)}, f)
        driver = os.path.join(self.lab, "driver.mjs")
        with open(driver, "w") as f:
            f.write(DRIVER)
        p = subprocess.run(["node", driver], capture_output=True, text=True, timeout=240,
                           env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg))
        if p.returncode == 3:
            raise unittest.SkipTest("no playwright browser on this box: the served lab needs one; CI's extension job installs Chromium and requires this file to run")
        self.assertEqual(p.returncode, 0, "driver failed:\n" + p.stdout[-3000:] + p.stderr[-3000:] + self._logs())
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
        self.assertIsNotNone(line, "driver printed no result:\n" + p.stdout[-3000:])
        r = json.loads(line[len("RESULT:"):])
        log = list(self.remote_log)
        by_prefix = lambda pre: [l for l in log if l["path"].startswith("/" + pre)]
        # the harness first: without these an empty log could be a logger the browser cannot reach, or markup that loads nothing
        with self.subTest("every load the control tab names reached the logger"):
            self.assertEqual(sorted({l["path"] for l in by_prefix("C-")}), sorted("/C-" + s for s in SHAPES),
                             "every shape the control tab names reached the logger within the bound (%s ms): %r"
                             % (r["controlWaitMs"], by_prefix("C-")))
        with self.subTest("the logger's reach control"):
            self.assertEqual(r["reach"], "ok", "the kernel-origin page's no-cors fetch to the logger completed")
            self.assertEqual([l["path"] for l in log if l["path"] == "/reach"], ["/reach"], "the logger logged the reach fetch once")
        for name, prefix in (("local", "L-"), ("relay", "R-")):
            doc = r["docs"].get(name)
            with self.subTest(name + ": the tab's document came with the policy"):
                self.assertIsNotNone(doc, "the browser received the %s tab's document: %r" % (name, r["docs"]))
                self.assertEqual((doc["status"], doc["type"]), (200, "image/svg+xml"), doc)
                self.assertEqual(sorted(doc["csp"]), sorted([SVG_DOCUMENT_POLICY, FRAMING_POLICY]),
                                 "the %s tab's Content-Security-Policy values, as the browser received them" % name)
            with self.subTest(name + ": no request reached the logger"):
                self.assertEqual(by_prefix(prefix), [],
                                 "the %s tab (%s) made requests to another host; each with its path, cookie, Referer, "
                                 "Sec-Fetch-Dest and Sec-Fetch-Site" % (name, r["tabs"][name]["url"]))
            with self.subTest(name + ": the data: raster drew"):
                px = r["tabs"][name]["raster"]
                self.assertTrue(all(abs(a - b) <= 8 for a, b in zip(px[:3], RASTER_RGB)) and px[3] == 255,
                                "the %s tab's data: raster drew at the top left: pixel %r, want %r" % (name, px, RASTER_RGB))
                self.assertFalse(all(abs(a - b) <= 8 for a, b in zip(r["tabs"][name]["beside"][:3], RASTER_RGB)),
                                 "the pixel beside the raster is not the raster's colour: %r" % r["tabs"][name]["beside"])
            with self.subTest(name + ": the inline style applied"):
                px = r["tabs"][name]["styled"]
                self.assertTrue(all(abs(a - b) <= 8 for a, b in zip(px[:3], STYLED_RGB)),
                                "the %s tab's inline <style> rule filled its rect: pixel %r, want %r (black is a refused style)"
                                % (name, px, STYLED_RGB))
        with self.subTest("the control tab's data: raster drew"):
            px = r["tabs"]["control"]["raster"]
            self.assertTrue(all(abs(a - b) <= 8 for a, b in zip(px[:3], RASTER_RGB)), px)
        self.assertEqual(r["tabs"]["local"]["url"], tabs["local"], "the tab's address is fileUrl's, with no token in it")
        self.assertNotIn("token=", r["tabs"]["relay"]["url"])


if __name__ == "__main__":
    unittest.main()
