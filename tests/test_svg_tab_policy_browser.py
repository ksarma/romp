#!/usr/bin/env python3
"""An .svg opened in its own tab loads nothing from another host, in any engine (image mode, kernel.py _svg_image_page).

On the web dashboard a Cmd, Ctrl or middle click on a path link to an .svg in a viewed file opens the kernel's /file URL in
its own tab (ui/webview/preview.ts openFileTab, fileUrl), and for a remote session's file the /remote/<host>/file relay's
URL. Until 2026-09-23 the tab got the svg bytes as its DOCUMENT, under a policy of `sandbox` and four fetch directives
(kernel.py _media_policy_headers). That policy stopped the sixteen loads below in Chromium, but no fetch directive tells a
data: raster from a data: SVG document and none governs a preconnect: in Firefox 153 a fill, mask or filter naming a
data: SVG document fetched that document's own @import from another host, and in WebKit 26.5 a foreignObject
<link rel=preconnect> opened a TCP connection to its host. Now a navigation (and a frame, an object or an embed) gets the
image-mode page, which holds the file in an <img> of the same route with raw=1, and an svg drawn as an image loads nothing
external. The bytes the <img> reads keep the policy as a second layer.

This module runs two hermetic lab kernels (the served labs' environment, tests/test_ship_reship_served.py kernel_env, each
with its own state root, port and token): the hub, which serves one synthetic session's files on /file, and a second
kernel the hub relays to as host gpu1 (registered through the hub's own check-in handshake, POST /checkin), which serves
its session's files behind /remote/gpu1/file.

test_the_policy_rides_every_svg_success_on_the_route_and_the_relay asks both kernels' wire for the headers of the svg
BYTES, as the page's <img>, the viewer's fetch, a HEAD probe and a Range retry get them: a GET (200), a HEAD and a suffix
Range (206) each carry the policy, compared as the whole list of Content-Security-Policy values (the 200 also carries
_send's frame-ancestors policy), and a PNG carries neither. test_a_navigation_gets_the_image_mode_page_on_the_route_and_
the_relay asks the same wire as a navigation does (Sec-Fetch-Dest: document, and a plain-http dashboard's text/html Accept
with no Sec-Fetch-Dest): each gets the page under its own policy, and every svg answer names the two headers it varies on.

The tab witness drives Playwright's Chromium always, and Firefox and WebKit when ROMP_BROWSER_ENGINES names them (a comma
list of firefox and webkit; chromium may be named and always runs; any other name fails the module). CI's extension job
installs Chromium alone and sets no such variable, so it runs the Chromium leg with nothing skipped; the Firefox and WebKit
figures are runs on a machine that has those engines, with the variable set. ROMP_SERVED_TESTS_ENGINES is not read here: it
declares which engines a runner installed, and its other readers try every engine when it is unset. Each engine gets five
tabs, opened in this order and never closed:
- open: a real click on a button in a kernel-origin page whose handler makes ONE window.open of the file's /file URL and
  severs the opener, as openFileTab does. Before it, that page fetches the same URL, HEADs it and loads it in an <img>
  (the other consumers keep the svg bytes), so the tab's navigation also shows that an image the browser already holds
  for that URL does not answer it;
- ctrl and middle: a Ctrl click and a middle click on the viewer's path link to a file (the real /files page, the file
  viewer opened on a markdown file that names both svgs), so the tab's URL is the one the viewer builds;
- relay: the button's window.open of the /remote/gpu1/file URL of the second kernel's file;
- control: the button's window.open of the same markup served by a control server on 127.0.0.1 under the kernel's headers
  with `sandbox` alone as the svg's policy.
Every tab's svg names, under its own path prefix, the sixteen load shapes (an <image> href, an <image> xlink:href, a CSS
@import, a foreignObject <img>, a fill, a mask and a CSS fill paint reference, an <feImage> href, a CSS cursor, a background
image, an @font-face source, and in a foreignObject a stylesheet <link>, an image preload, a prefetch, an <iframe> and a
<video>) and three data: SVG paint documents, each with the fragment present and carrying an @import (named by a fill, a
mask and a filter), all aimed at the tab's own LOADS sink; and in a foreignObject two <link rel=preconnect> (plain and
crossorigin=anonymous) and a <link rel=dns-prefetch>, aimed at the tab's own LINKS sink. Then a 40 by 40 data: PNG raster at
the top left, and below it a rect filled by an inline <style> rule. Each sink is a pair of listeners, 127.0.0.1 and ::1 on
one port, that counts every accepted TCP connection and logs each request's path, Referer class and Sec-Fetch headers: a
second origin and a second site to the pages, which are served from 127.0.0.1.

Asserted per engine and witness tab (open, ctrl, middle, relay): the tab's document is the image-mode page under its policy
with one <img> of the same route, path and sid plus raw=1 and no token; that <img>'s answer is the svg bytes under the svg
policy; neither of the tab's sinks received a request or accepted a connection; the svg's styled rect and its data: raster
drew, read back as pixels from a screenshot of the tab; the tab's address carries no token. The driver waits (bounded, 20 s)
until the control tab's loads that the engine makes under a bare sandbox have arrived (CONTROL_ARRIVALS, measured with this
markup in Playwright 1.62.1 on 2026-09-23: Chromium 151 made all sixteen shapes and none of the data: documents' @imports
or the preconnects; Firefox 153 fourteen shapes, all but fill.svg and cssfill.svg, and the three @imports; WebKit 26.5
thirteen shapes, all but fill.svg, cssfill.svg and prefetch.txt, and a preconnect connection), then drains 3 s more before
the sinks are read, so a request or connection any witness tab had made would have arrived. A shape an engine did not make
in its control says nothing about that engine, and a name lookup (dns-prefetch) is not visible to an accept log in any
engine. Then the kernel-origin page fetches a reach sink once (no-cors), which must be its one request.

Red at b4f9139b8 (the svg as the tab's document under the fetch-directive policy): the page and <img> subtests in every
engine, Firefox's witness tabs fetching the three data: documents' @imports, and WebKit's witness tabs opening preconnect
connections. The drawing, consumer and control subtests are green there by design: the svg document drew too, the other
consumers were never changed, and the control is the harness.

Skips LOUDLY without the extension deps or Playwright's Chromium; the CI extension job installs Chromium and runs served
files with ROMP_SERVED_TESTS_REQUIRE=1, which turns any skip into a failure there. An engine ROMP_BROWSER_ENGINES names that
does not launch is a failure, never a skip. SYNTHETIC fixtures only (session web, the notes-api demo world, placeholder
uuids, host gpu1)."""
import base64
import errno
import html
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
# The policies, written out here and never read from the kernel: a pin that compared the response with the kernel's
# own value would move with it (tests/test_kernel_preview.py holds the same text in process).
SVG_DOCUMENT_POLICY = "sandbox; default-src 'none'; img-src data: blob:; style-src 'unsafe-inline'; font-src data:"
PAGE_POLICY = ("sandbox allow-same-origin; default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; "
               "base-uri 'none'; form-action 'none'")
FRAMING_POLICY = "frame-ancestors 'self'"   # _send's, on every 200 it sends
VARY = "Sec-Fetch-Dest, Accept"
NAV_ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"   # a navigation's Accept, as Firefox sends it
IMG_ACCEPT = "image/avif,image/webp,image/png,image/svg+xml,image/*;q=0.8,*/*;q=0.5"
RASTER_RGB = (0, 160, 80)                   # the data: raster's one colour, read back from the tab's pixels
STYLED_RGB = (40, 40, 200)                  # the fill an inline <style> rule gives one rect (unstyled, it would be black)
SHAPES = ("import.css", "image.png", "ximage.png", "fo-img.png", "fill.svg", "mask.svg", "cssfill.svg",
          "feimage.png", "cursor.png", "bgimg.png", "font.woff", "link.css", "preload.png", "prefetch.txt",
          "frame.html", "video.mp4")
DATA_IMPORTS = ("fill-import.css", "mask-import.css", "filter-import.css")   # the data: paint documents' own @imports
ENGINES = ("chromium", "firefox", "webkit")
# What each engine loaded from the control tab's markup under a bare `sandbox` (measured 2026-09-23, Playwright 1.62.1, see
# the module docstring): the loads-sink paths, less the tab prefix, and whether a preconnect connection reached the links sink.
CONTROL_ARRIVALS = {
    "chromium": (SHAPES, False),
    "firefox": (tuple(s for s in SHAPES if s not in ("fill.svg", "cssfill.svg")) + DATA_IMPORTS, False),
    "webkit": (tuple(s for s in SHAPES if s not in ("fill.svg", "cssfill.svg", "prefetch.txt")), True),
}
WITNESS_TABS = ("open", "ctrl", "middle", "relay")
TABS = WITNESS_TABS + ("control",)


def _engines():
    """The engines this run drives: Chromium always, then each engine ROMP_BROWSER_ENGINES names, in its order. A name
    outside ENGINES raises, so a misspelling fails the module instead of quietly running Chromium alone."""
    asked = [e.strip() for e in (os.environ.get("ROMP_BROWSER_ENGINES") or "").split(",") if e.strip()]
    bad = [e for e in asked if e not in ENGINES]
    if bad:
        raise AssertionError("ROMP_BROWSER_ENGINES names %r, outside %s" % (bad, ", ".join(ENGINES)))
    out = ["chromium"]
    for e in asked:
        if e not in out:
            out.append(e)
    return out


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


def _diagram(loads, links, prefix):
    """An exported-figure-shaped svg: the data: raster at the top left, a rect below it filled by an inline <style> rule,
    every shape in SHAPES and the three data: paint documents aimed at the `loads` sink under `prefix`, and the preconnect
    and dns-prefetch links aimed at the `links` sink, each drawn clear of the raster and the styled rect."""
    r = loads + "/" + prefix
    raster = base64.b64encode(_png(40, 40, RASTER_RGB)).decode("ascii")

    def paintdoc(inner, name):
        doc = '<svg xmlns="http://www.w3.org/2000/svg"><style>@import url("%s%s");</style><defs>%s</defs></svg>' % (r, name, inner)
        return "data:image/svg+xml," + urllib.parse.quote(doc, safe="")
    dfill = paintdoc('<pattern id="p" width="1" height="1"><rect width="1" height="1" fill="blue"/></pattern>', "fill-import.css") + "#p"
    dmask = paintdoc('<mask id="m"><rect width="1" height="1" fill="white"/></mask>', "mask-import.css") + "#m"
    dfilt = paintdoc('<filter id="f"><feFlood flood-color="blue"/></filter>', "filter-import.css") + "#f"
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
            "<rect x=\"0\" y=\"100\" width=\"12\" height=\"12\" fill=\"url('%(dfill)s')\"/>"
            "<rect x=\"14\" y=\"100\" width=\"12\" height=\"12\" fill=\"red\" mask=\"url('%(dmask)s')\"/>"
            "<rect x=\"28\" y=\"100\" width=\"12\" height=\"12\" fill=\"red\" filter=\"url('%(dfilt)s')\"/>"
            '<foreignObject x="60" y="50" width="330" height="100"><div xmlns="http://www.w3.org/1999/xhtml">'
            '<link rel="stylesheet" href="%(r)slink.css"/><link rel="preload" as="image" href="%(r)spreload.png"/>'
            '<link rel="prefetch" href="%(r)sprefetch.txt"/>'
            '<link rel="preconnect" href="%(links)s"/><link rel="preconnect" href="%(links)s" crossorigin="anonymous"/>'
            '<link rel="dns-prefetch" href="%(links)s"/>'
            '<div style="width:20px;height:20px;background-image:url(%(r)sbgimg.png)"></div>'
            '<iframe src="%(r)sframe.html" width="20" height="20"></iframe>'
            '<video src="%(r)svideo.mp4" width="20" height="20"></video>'
            '</div></foreignObject>'
            '</svg>') % {"r": r, "raster": raster, "st": ", ".join(str(c) for c in STYLED_RGB),
                         "dfill": dfill, "dmask": dmask, "dfilt": dfilt, "links": links}


DRIVER = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const playwright = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const redact = (u) => String(u).replace(/token=[^&#]*/g, "token=REDACTED");
let browser;
try { browser = await playwright[cfg.engine].launch(); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const out = { engine: playwright[cfg.engine].name(), version: browser.version(), tabs: {}, responses: [], errors: [] };
const context = await browser.newContext({ viewport: { width: 800, height: 600 }, deviceScaleFactor: 1 });
// every answer the kernels gave this browser for a file: the tab documents and their <img>s, and the consumers' requests
const pending = [];
context.on("response", (r) => {
  const u = r.url();
  if (!u.startsWith(cfg.origin) || !(u.includes("/file?") || u.includes("/remote/"))) return;
  pending.push((async () => {
    let hs = [];
    try { hs = await r.headersArray(); } catch (e) { /* the page went away */ }
    const get = (n) => hs.filter((h) => h.name.toLowerCase() === n).map((h) => h.value);
    const row = { url: redact(u), status: r.status(), type: get("content-type")[0] || null, csp: get("content-security-policy"),
                  vary: get("vary"), resourceType: r.request().resourceType(), body: null };
    if ((row.type || "").startsWith("text/html")) { try { row.body = redact(await r.text()); } catch (e) { row.body = "unread: " + e; } }
    out.responses.push(row);
  })());
});
context.on("page", (p) => p.on("pageerror", (e) => out.errors.push(redact(p.url()) + ": " + String(e).slice(0, 200))));
// a kernel-origin page, opened once with the token in its address as the dashboard's first load is
const opener = await context.newPage();
await opener.goto(cfg.openerPage);
const helper = await context.newPage();   // reads a screenshot's pixels back on a canvas (a data: image taints nothing)
const pixel = async (png, x, y) => helper.evaluate(async ([b64, x, y]) => {
  const img = new Image(); img.src = "data:image/png;base64," + b64; await img.decode();
  const c = document.createElement("canvas"); c.width = img.width; c.height = img.height;
  const g = c.getContext("2d"); g.drawImage(img, 0, 0);
  return Array.from(g.getImageData(x, y, 1, 1).data);
}, [png.toString("base64"), x, y]);
// the other consumers of the open tab's URL, from the kernel-origin page, BEFORE that tab: a fetch() as the viewer makes,
// a HEAD as the chip's probe makes, and an <img> as the chat's thumbnail and the lightbox load (left in the browser's cache)
out.consumers = await opener.evaluate(async (u) => {
  const r = await fetch(u, { cache: "no-store" }); const b = new Uint8Array(await r.arrayBuffer());
  const h = await fetch(u, { method: "HEAD", cache: "no-store" });
  const im = new Image(); im.src = u; let dec = "ok"; try { await im.decode(); } catch (e) { dec = String(e); }
  return { fetchStatus: r.status, fetchType: r.headers.get("content-type"), fetchLen: b.byteLength, fetchVary: r.headers.get("vary"),
           headStatus: h.status, headType: h.headers.get("content-type"), imgDecode: dec, imgNatural: [im.naturalWidth, im.naturalHeight] };
}, cfg.tabs.open.url);
// the viewer: the real /files page, the file viewer opened on the markdown file that names the ctrl and middle svgs
const viewer = await context.newPage();
await viewer.goto(cfg.filesPage);
await viewer.waitForFunction(() => document.readyState === "complete", null, { timeout: 30000 });
await viewer.evaluate(([path, sid]) => window.postMessage({ romp: "viewFile", path, sid }, "*"), [cfg.viewFile, cfg.sid]);
const linkSel = (suffix) => '#romp-fileview .file-uri-link[data-path$="' + suffix + '"]';
await viewer.waitForSelector(linkSel(cfg.tabs.ctrl.suffix), { timeout: 30000 });
await viewer.waitForSelector(linkSel(cfg.tabs.middle.suffix), { timeout: 30000 });
// the gesture from the kernel-origin page: a real click on a button whose handler makes ONE window.open and severs the opener
const viaButton = async (url) => {
  await opener.evaluate((u) => {
    let b = document.getElementById("svg-tab-go");
    if (!b) { b = document.createElement("button"); b.id = "svg-tab-go"; b.textContent = "open"; b.style.cssText = "position:fixed;top:0;left:0;width:200px;height:60px;z-index:2147483647"; document.body.appendChild(b); }
    b.onclick = () => { const w = window.open(u, "_blank"); if (w) { try { w.opener = null; } catch (e) {} } };
  }, url);
  const [tab] = await Promise.all([context.waitForEvent("page", { timeout: 20000 }), opener.click("#svg-tab-go")]);
  return tab;
};
const viaViewer = async (suffix, how) => {
  const act = how === "ctrl" ? () => viewer.click(linkSel(suffix), { modifiers: ["Control"] }) : () => viewer.click(linkSel(suffix), { button: "middle" });
  const [tab] = await Promise.all([context.waitForEvent("page", { timeout: 20000 }), act()]);
  return tab;
};
for (const name of cfg.order) {
  const t = cfg.tabs[name];
  try {
    const tab = t.how === "button" ? await viaButton(t.url) : await viaViewer(t.suffix, t.how);
    await tab.waitForLoadState("load", { timeout: 20000 });
    await sleep(500);
    const shot = await tab.screenshot({ clip: { x: 0, y: 0, width: 60, height: 100 } });
    out.tabs[name] = { url: redact(tab.url()), raster: await pixel(shot, 20, 20), beside: await pixel(shot, 50, 20), styled: await pixel(shot, 20, 70) };
  } catch (e) { out.tabs[name] = { error: String(e).slice(0, 500) }; }
}
// the control's arrivals, bounded; then a drain before the sinks are read (the tabs stay open until the browser closes)
const t0 = Date.now();
let st = null;
while (Date.now() - t0 < 20000) {
  st = await (await fetch(cfg.admin + "/state")).json();
  if (cfg.controlExpect.every((p) => st.paths.includes(p)) && (!cfg.controlPreconnect || st.linkAccepts > 0)) break;
  await sleep(200);
}
out.controlWaitMs = Date.now() - t0;
await sleep(3000);
// the reach control, after the record: one no-cors fetch from the kernel-origin page to a sink of its own
out.reach = await opener.evaluate((u) => fetch(u, { mode: "no-cors", cache: "no-store" }).then(() => "ok", (e) => String(e)), cfg.reach);
await Promise.all(pending);
fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
await browser.close();
process.exit(0);
"""


def _referer_class(ref):
    if not ref:
        return "none"
    u = urllib.parse.urlparse(ref)
    return "origin" if u.path in ("", "/") and not u.query else "url"


class _Sink:
    """One second server: every accepted TCP connection counted and every request's path, Referer class and Sec-Fetch
    headers logged, over a pair of listeners on 127.0.0.1 and ::1 at one port (::1 left out where the box has no IPv6
    loopback, which `v6` records)."""

    def __init__(self):
        self.requests, self.accepts, self.lock, self.servers = [], 0, threading.Lock(), []
        self.port, self.v6 = None, False

    def state(self):
        with self.lock:
            return {"requests": list(self.requests), "accepts": self.accepts, "v6": self.v6}


class _SinkHandler(BaseHTTPRequestHandler):
    sink = None
    timeout = 5                  # an idle preconnected socket frees its thread (its accept is already counted)
    protocol_version = "HTTP/1.0"

    def _answer(self, body_ok=True):
        with self.sink.lock:
            self.sink.requests.append({"path": self.path, "referer": _referer_class(self.headers.get("Referer")),
                                       "dest": self.headers.get("Sec-Fetch-Dest"), "site": self.headers.get("Sec-Fetch-Site"),
                                       "mode": self.headers.get("Sec-Fetch-Mode")})
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
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if body_ok:
            self.wfile.write(body)

    def do_GET(self):
        self._answer()

    def do_HEAD(self):
        self._answer(False)

    def do_OPTIONS(self):
        self._answer(False)

    def log_message(self, *a):   # quiet: the sink's own log is the record
        pass


class _SinkServer4(ThreadingHTTPServer):
    daemon_threads = True
    address_family = socket.AF_INET
    sink = None

    def get_request(self):
        conn, addr = super().get_request()
        with self.sink.lock:
            self.sink.accepts += 1
        return conn, addr


class _SinkServer6(_SinkServer4):
    address_family = socket.AF_INET6


def _start_sink(cls):
    """A _Sink listening on 127.0.0.1 and, when the box has it, ::1 at the same port; its stop is registered with `cls`."""
    sink = _Sink()
    handler = type("H", (_SinkHandler,), {"sink": sink})
    for _ in range(50):
        s4 = type("S4", (_SinkServer4,), {"sink": sink})(("127.0.0.1", 0), handler)
        servers = [s4]
        try:
            servers.append(type("S6", (_SinkServer6,), {"sink": sink})(("::1", s4.server_address[1]), handler))
            sink.v6 = True
        except OSError as e:
            if e.errno == errno.EADDRINUSE:
                s4.server_close()
                continue
        break
    else:
        raise AssertionError("no port was free on both loopback families")
    sink.port = s4.server_address[1]
    for srv in servers:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        sink.servers.append(srv)

        def end(srv=srv):
            srv.shutdown()
            srv.server_close()
        cls.addClassCleanup(end)
    return sink


class _Control(BaseHTTPRequestHandler):
    """The control server: each engine's control diagram at /control-<engine>.svg under the kernel's 200 headers with
    `sandbox` alone as the svg's policy, so the control tab's loads are what the markup makes when nothing blocks them."""
    bodies = None

    def do_GET(self):
        body = self.bodies.get(self.path.split("?")[0])
        if body is None:
            self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers(); return
        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Content-Security-Policy", FRAMING_POLICY)
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "sandbox")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


class _Admin(BaseHTTPRequestHandler):
    """What the driver's bounded wait reads: the control tab's loads-sink paths (less its prefix) and its links-sink accepts."""
    control = None      # {"loads": _Sink, "links": _Sink, "prefix": str}, set per engine

    def do_GET(self):
        c = _Admin.control
        pre = "/" + c["prefix"]
        paths = [q["path"][len(pre):] for q in c["loads"].state()["requests"] if q["path"].startswith(pre)]
        body = json.dumps({"paths": paths, "linkAccepts": c["links"].state()["accepts"]}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

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


def _close(px, rgb):
    return all(abs(a - b) <= 8 for a, b in zip(px[:3], rgb))


def _vary(values):
    """The header names a Vary answer lists, as the browser reported them: Firefox and WebKit hand Playwright one entry per
    name and Chromium one entry per header line, which say the same thing."""
    return [t.strip() for v in values for t in v.split(",") if t.strip()]


class SvgTabPolicy(unittest.TestCase):
    maxDiff = None
    _runs = None        # the per-engine driver runs, made once and shared by the tab-witness tests
    _runs_error = None  # ...or the one failure that stopped them, raised again in each

    @classmethod
    def setUpClass(cls):
        try:
            cls._boot()
        except BaseException:          # a skip OR a failure: never leave a kernel or a lab behind
            cls.tearDownClass()
            raise

    @classmethod
    def _kernel(cls, name, dist, host_name):
        """One lab kernel under <lab>/<name>: a state root with one session (`web`) whose cwd holds docs/readme.md and
        plots/figure.png. Returns (port, token, cwd)."""
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
        Path(cwd, "docs", "readme.md").write_text("# notes-api\n\nThe diagrams are under docs/.\n")
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
        cls.engines = _engines()        # before anything boots: a misspelled engine fails here
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            raise unittest.SkipTest("extension deps absent (npm ci not run here): the served lab needs them; CI's extension job has them and requires this file to run")
        probe = subprocess.run(["node", "-e", "const p=require(process.argv[1]);process.stdout.write(p.chromium.executablePath())",
                                os.path.join(EXT, "node_modules", "playwright")], capture_output=True, text=True)
        if probe.returncode != 0 or not os.path.exists(probe.stdout.strip()):
            raise unittest.SkipTest("no playwright browser on this box: the served lab needs one; CI's extension job installs Chromium and requires this file to run")
        cls.lab = tempfile.mkdtemp(prefix="svg-tab-")
        cls.control_bodies = {}
        cls.control_srv = _serve(cls, "127.0.0.1", type("Control", (_Control,), {"bodies": cls.control_bodies}))
        cls.admin_srv = _serve(cls, "127.0.0.1", _Admin)
        dist = os.path.join(cls.lab, "dist")
        lab_dist.copy_dist(dist)   # the checkout's ONE build of the bundles, copied under its lock (tests/lab_dist.py)
        cls.port, cls.token, cls.hub_cwd = cls._kernel("hub", dist, "TESTHOST")
        cls.port_b, cls.token_b, cls.b_cwd = cls._kernel("gpu1", dist, "gpu1")
        # the wire tests' file: no browser opens it, so its loads aim at the discard port
        Path(cls.hub_cwd, "docs", "diagram.svg").write_text(_diagram("http://localhost:9", "http://localhost:9", "W-"))
        Path(cls.b_cwd, "docs", "diagram.svg").write_text(_diagram("http://localhost:9", "http://localhost:9", "W-"))
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

    def _answer(self, url, method="GET", headers=None):
        """(status, header message, body) for one request with the hub's token in X-Romp-Token. The raw header MESSAGE, not a
        dict: a dict keeps one value per name, and the svg policy rides beside _send's framing policy under one name."""
        req = urllib.request.Request(url, method=method, headers=dict(headers or {}, **{"X-Romp-Token": self.token}))
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status, r.headers, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read()

    def _policies(self, url, method="GET", headers=None):
        status, msg, _ = self._answer(url, method, headers)
        return status, msg.get("Content-Type"), msg.get_all("Content-Security-Policy") or []

    @staticmethod
    def _page_img(body):
        """The image-mode page's <img> sources, unescaped, read from its markup (the page runs no script to ask)."""
        return [html.unescape(m) for m in re.findall(r'<img\b[^>]*\bsrc="([^"]*)"', body or "")]

    def _assert_page_img(self, srcs, tab_url, where):
        """The page holds ONE <img>, of the tab's own route for the tab's path and sid plus raw=1, and nothing else."""
        self.assertEqual(len(srcs), 1, "%s: the page holds one <img>: %r" % (where, srcs))
        img, tab = urllib.parse.urlsplit(srcs[0]), urllib.parse.urlsplit(tab_url)
        self.assertEqual((img.scheme, img.netloc), ("", ""), "%s: the <img> is a same-origin path: %r" % (where, srcs[0]))
        self.assertEqual(img.path, tab.path, "%s: the <img> reads the tab's own route" % where)
        iq, tq = urllib.parse.parse_qs(img.query), urllib.parse.parse_qs(tab.query)
        self.assertEqual(iq, {"path": tq["path"], "sid": tq["sid"], "raw": ["1"]},
                         "%s: the <img> carries the tab's path and sid plus raw=1, and no token: %r" % (where, srcs[0]))

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

    def test_a_navigation_gets_the_image_mode_page_on_the_route_and_the_relay(self):
        # the real relay to a real second kernel, which never sees the browser's headers: the hub decides, from them
        for arm, route, sid in (("route", "/file", SID), ("relay", "/remote/gpu1/file", SID_B)):
            url = self._url(route, "docs/diagram.svg", sid)
            for how, headers in (("Sec-Fetch-Dest document", {"Sec-Fetch-Dest": "document", "Accept": NAV_ACCEPT}),
                                 ("a plain-http navigation: text/html, no Sec-Fetch-Dest", {"Accept": NAV_ACCEPT})):
                with self.subTest(arm=arm, request=how):
                    status, msg, body = self._answer(url, headers=headers)
                    self.assertEqual((status, msg.get("Content-Type")), (200, "text/html; charset=utf-8"),
                                     "%s, %s: the image-mode page, not the svg as the tab's document%s" % (arm, how, self._logs()))
                    self.assertEqual(sorted(msg.get_all("Content-Security-Policy") or []), sorted([PAGE_POLICY, FRAMING_POLICY]),
                                     "%s, %s: the page's own policy beside _send's framing one" % (arm, how))
                    self.assertEqual(msg.get_all("Vary"), [VARY], "%s, %s: the page varies on the two deciding headers" % (arm, how))
                    text = body.decode("utf-8")
                    self.assertNotIn("token", text, "%s, %s: the page carries no token of either kernel" % (arm, how))
                    self._assert_page_img(self._page_img(text), url, "%s, %s" % (arm, how))
            for method, headers, want in (("GET", {"Sec-Fetch-Dest": "image", "Accept": IMG_ACCEPT}, 200),
                                          ("HEAD", {"Sec-Fetch-Dest": "document", "Accept": NAV_ACCEPT}, 200),
                                          ("GET", {"Sec-Fetch-Dest": "image", "Range": "bytes=1-"}, 206)):
                with self.subTest(arm=arm, bytes_for="%s %s" % (method, headers)):
                    status, msg, _ = self._answer(url, method, headers)
                    self.assertEqual((status, msg.get("Content-Type")), (want, "image/svg+xml"), "%s: the svg bytes" % arm)
                    self.assertEqual(msg.get_all("Vary"), [VARY], "%s %s: the bytes vary on the two deciding headers" % (arm, method))
        with self.subTest("a PNG a tab navigates to is the PNG"):
            status, msg, _ = self._answer(self._url("/file", "plots/figure.png", SID),
                                          headers={"Sec-Fetch-Dest": "document", "Accept": NAV_ACCEPT})
            self.assertEqual((status, msg.get("Content-Type"), msg.get_all("Vary")), (200, "image/png", None),
                             "a picture is never a document: no page and no Vary")

    # ---- the tab witness: one driver run per engine, shared by the tests below

    def _run_engine(self, engine):
        cls = type(self)
        sinks = {t: {"loads": _start_sink(cls), "links": _start_sink(cls)} for t in TABS}
        reach = _start_sink(cls)
        prefix = {t: "%s-%s-" % (engine, t) for t in TABS}
        mark = lambda t: _diagram("http://localhost:%d" % sinks[t]["loads"].port, "http://localhost:%d" % sinks[t]["links"].port,
                                  prefix[t]).encode()
        files = {t: mark(t) for t in TABS}
        for t in ("open", "ctrl", "middle"):
            Path(self.hub_cwd, "docs", "%s-%s.svg" % (engine, t)).write_bytes(files[t])
        Path(self.b_cwd, "docs", "%s-relay.svg" % engine).write_bytes(files["relay"])
        self.control_bodies["/control-%s.svg" % engine] = files["control"]
        viewed = os.path.join(self.hub_cwd, "docs", "%s-tabs.md" % engine)
        Path(viewed).write_text("# Diagrams\n\nThe first diagram is %s here.\n\nThe second diagram is %s here.\n"
                                % (os.path.join(self.hub_cwd, "docs", "%s-ctrl.svg" % engine),
                                   os.path.join(self.hub_cwd, "docs", "%s-middle.svg" % engine)))
        _Admin.control = {"loads": sinks["control"]["loads"], "links": sinks["control"]["links"], "prefix": prefix["control"]}
        expect, preconnect = CONTROL_ARRIVALS[engine]
        origin = "http://127.0.0.1:%d" % self.port
        tabs = {"open": {"how": "button", "url": self._url("/file", "docs/%s-open.svg" % engine, SID)},
                "ctrl": {"how": "ctrl", "suffix": "%s-ctrl.svg" % engine},
                "middle": {"how": "middle", "suffix": "%s-middle.svg" % engine},
                "relay": {"how": "button", "url": self._url("/remote/gpu1/file", "docs/%s-relay.svg" % engine, SID_B)},
                "control": {"how": "button", "url": "http://127.0.0.1:%d/control-%s.svg" % (self.control_srv.server_address[1], engine)}}
        cfg = {"engine": engine, "origin": origin, "sid": SID, "viewFile": viewed, "tabs": tabs, "order": list(TABS),
               "openerPage": self._url("/file", "docs/readme.md", SID) + "&token=" + self.token,
               "filesPage": "%s/files?token=%s" % (origin, self.token),
               "admin": "http://127.0.0.1:%d" % self.admin_srv.server_address[1],
               "controlExpect": list(expect), "controlPreconnect": preconnect, "reach": "http://localhost:%d/reach" % reach.port}
        cfgp = os.path.join(self.lab, "cfg-%s.json" % engine)
        with open(cfgp, "w") as f:
            json.dump(cfg, f)
        driver = os.path.join(self.lab, "driver.mjs")
        with open(driver, "w") as f:
            f.write(DRIVER)
        p = subprocess.run(["node", driver], capture_output=True, text=True, timeout=300,
                           env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfgp))
        if p.returncode == 3 and engine == "chromium":
            raise unittest.SkipTest("no playwright browser on this box: the served lab needs one; CI's extension job installs Chromium and requires this file to run")
        if p.returncode == 3:
            raise AssertionError("ROMP_BROWSER_ENGINES names %s, and it did not launch here (a named engine is a failure, never a skip):\n%s"
                                 % (engine, p.stderr[-2000:]))
        if p.returncode != 0:
            raise AssertionError("the %s driver failed:\n%s%s%s" % (engine, p.stdout[-3000:], p.stderr[-3000:], self._logs()))
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
        if line is None:
            raise AssertionError("the %s driver printed no result:\n%s" % (engine, p.stdout[-3000:]))
        time.sleep(0.5)          # the sinks' handler threads finish logging the last request before they are read
        return {"result": json.loads(line[len("RESULT:"):]), "files": files, "prefix": prefix, "reach": reach.state(),
                "sinks": {t: {k: s.state() for k, s in sinks[t].items()} for t in TABS},
                "tabUrls": {t: tabs[t].get("url") for t in TABS}}

    def _all(self):
        cls = type(self)
        if cls._runs_error is not None:
            raise cls._runs_error
        if cls._runs is None:
            try:
                cls._runs = {engine: self._run_engine(engine) for engine in cls.engines}
            except (AssertionError, unittest.SkipTest) as e:
                cls._runs_error = e
                raise
            print("SVG-TAB ENGINES RAN: %s (ROMP_BROWSER_ENGINES=%r)" % (", ".join(cls._runs), os.environ.get("ROMP_BROWSER_ENGINES", "")),
                  file=sys.stderr)
            print("SVG-TAB RESULTS: " + json.dumps({e: {"sinks": r["sinks"], "tabs": r["result"]["tabs"], "controlWaitMs": r["result"]["controlWaitMs"],
                                                         "version": r["result"]["version"]} for e, r in cls._runs.items()}), file=sys.stderr)
        return cls._runs

    def test_the_engines_that_ran(self):
        # Chromium always; Firefox and WebKit only when ROMP_BROWSER_ENGINES names them. The engine each result names is the
        # one that launched (browserType().name()), so a driver that launched another engine than asked cannot pass
        runs = self._all()
        ran = [runs[e]["result"]["engine"] for e in runs]
        self.assertEqual(ran, self.engines, "engines that ran: %s, versions %s (ROMP_BROWSER_ENGINES=%r; Firefox and WebKit run only "
                                            "when it names them)" % (", ".join(ran), [runs[e]["result"]["version"] for e in runs],
                                                                     os.environ.get("ROMP_BROWSER_ENGINES", "")))

    def test_each_tab_is_the_image_mode_page_and_its_img_reads_the_svg_bytes(self):
        for engine, run in self._all().items():
            r = run["result"]
            for t in WITNESS_TABS:
                where = "%s, %s tab" % (engine, t)
                tab = r["tabs"].get(t, {})
                docs = [x for x in r["responses"] if x["resourceType"] == "document" and x["url"] == tab.get("url")]
                srcs = self._page_img(docs[0]["body"]) if docs else []
                with self.subTest(engine=engine, tab=t, check="the tab's document is the image-mode page"):
                    self.assertNotIn("error", tab, where + ": the tab opened")
                    self.assertEqual(len(docs), 1, "%s: one document answer for the tab's URL %r among %r"
                                     % (where, tab.get("url"), [(x["resourceType"], x["url"]) for x in r["responses"]]))
                    doc = docs[0]
                    self.assertEqual((doc["status"], doc["type"]), (200, "text/html; charset=utf-8"),
                                     "%s: the image-mode page, not the svg as the tab's document: %r"
                                     % (where, {k: doc[k] for k in ("status", "type", "csp")}))
                    self.assertEqual(sorted(doc["csp"]), sorted([PAGE_POLICY, FRAMING_POLICY]), where + ": the page's policy beside the framing one")
                    self.assertEqual(_vary(doc["vary"]), ["Sec-Fetch-Dest", "Accept"], where + ": the page varies on the two deciding headers")
                    self._assert_page_img(srcs, tab["url"], where)
                with self.subTest(engine=engine, tab=t, check="the page's img reads the svg bytes under the svg policy"):
                    self.assertEqual(len(srcs), 1, "%s: the tab's document holds one <img> to read" % where)
                    img_url = "http://127.0.0.1:%d%s" % (self.port, srcs[0])
                    imgs = [x for x in r["responses"] if x["resourceType"] == "image" and x["url"] == img_url]
                    self.assertTrue(imgs, "%s: the browser loaded the page's <img> %r" % (where, img_url))
                    self.assertEqual((imgs[0]["status"], imgs[0]["type"]), (200, "image/svg+xml"), where)
                    self.assertEqual(sorted(imgs[0]["csp"]), sorted([SVG_DOCUMENT_POLICY, FRAMING_POLICY]),
                                     where + ": the svg bytes keep the document policy as a second layer")
                    self.assertEqual(_vary(imgs[0]["vary"]), ["Sec-Fetch-Dest", "Accept"], where + ": the bytes vary on the two deciding headers")

    def test_no_tab_reaches_another_server(self):
        for engine, run in self._all().items():
            r, sinks = run["result"], run["sinks"]
            expect, preconnect = CONTROL_ARRIVALS[engine]
            ctl = [q["path"] for q in sinks["control"]["loads"]["requests"]]
            # the harness first: without these an empty sink could be a server the browser cannot reach, or markup that loads nothing
            with self.subTest(engine=engine, check="the control tab's loads reached its sink"):
                self.assertNotIn("error", r["tabs"].get("control", {}), engine + ": the control tab opened")
                missing = [s for s in expect if "/" + run["prefix"]["control"] + s not in ctl]
                self.assertEqual(missing, [], "%s: every load this engine makes under a bare sandbox reached the control's sink within "
                                              "the bound (%s ms); it received %r" % (engine, r["controlWaitMs"], sorted(ctl)))
                if preconnect:
                    self.assertGreater(sinks["control"]["links"]["accepts"], 0,
                                       engine + ": the control's preconnect link opened a connection to its sink")
            with self.subTest(engine=engine, check="the reach control"):
                self.assertEqual(r["reach"], "ok", engine + ": the kernel-origin page's no-cors fetch to the reach sink completed")
                self.assertEqual([q["path"] for q in run["reach"]["requests"]], ["/reach"], engine + ": the reach sink logged it once")
            for t in WITNESS_TABS:
                with self.subTest(engine=engine, tab=t, check="nothing reached the tab's sinks"):
                    self.assertNotIn("error", r["tabs"].get(t, {}), "%s, %s tab: the tab opened" % (engine, t))
                    got = {k: {"requests": [q["path"] for q in s["requests"]], "accepts": s["accepts"]} for k, s in sinks[t].items()}
                    self.assertEqual(got, {"loads": {"requests": [], "accepts": 0}, "links": {"requests": [], "accepts": 0}},
                                     "%s, %s tab (%s): requests and TCP connections at another server: %s"
                                     % (engine, t, r["tabs"][t].get("url"), json.dumps({k: s["requests"] for k, s in sinks[t].items()})))

    def test_the_svg_and_its_data_raster_draw_in_each_tab(self):
        for engine, run in self._all().items():
            for t in TABS:
                tab = run["result"]["tabs"].get(t, {})
                with self.subTest(engine=engine, tab=t):
                    self.assertNotIn("error", tab, "%s, %s tab: the tab opened" % (engine, t))
                    self.assertTrue(_close(tab["raster"], RASTER_RGB) and tab["raster"][3] == 255,
                                    "%s, %s tab: the data: raster drew at the top left: pixel %r, want %r" % (engine, t, tab["raster"], RASTER_RGB))
                    self.assertFalse(_close(tab["beside"], RASTER_RGB), "the pixel beside the raster is not the raster's colour: %r" % tab["beside"])
                    self.assertTrue(_close(tab["styled"], STYLED_RGB),
                                    "%s, %s tab: the inline <style> rule filled its rect: pixel %r, want %r" % (engine, t, tab["styled"], STYLED_RGB))

    def test_the_other_consumers_keep_the_svg_bytes(self):
        # a fetch, a HEAD and an <img> of the open tab's URL, from the kernel-origin page before that tab opened
        for engine, run in self._all().items():
            c = run["result"]["consumers"]
            with self.subTest(engine=engine):
                self.assertEqual((c["fetchStatus"], c["fetchType"], c["fetchLen"]), (200, "image/svg+xml", len(run["files"]["open"])),
                                 engine + ": a fetch() gets the file's bytes whole: %r" % c)
                self.assertEqual((c["headStatus"], c["headType"]), (200, "image/svg+xml"), engine + ": a HEAD answers for the svg: %r" % c)
                self.assertEqual((c["imgDecode"], c["imgNatural"]), ("ok", [400, 160]), engine + ": an <img> decodes the svg: %r" % c)

    def test_the_tab_address_carries_no_token(self):
        for engine, run in self._all().items():
            for t in WITNESS_TABS:
                tab = run["result"]["tabs"].get(t, {})
                with self.subTest(engine=engine, tab=t):
                    self.assertNotIn("error", tab)
                    self.assertNotIn("token=", tab["url"], "%s, %s tab: fileUrl's address, no token" % (engine, t))
                    if run["tabUrls"][t]:
                        self.assertEqual(tab["url"], run["tabUrls"][t], "%s, %s tab: the address the gesture opened" % (engine, t))


if __name__ == "__main__":
    unittest.main()
