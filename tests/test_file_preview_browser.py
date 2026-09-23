#!/usr/bin/env python3
"""The file preview popover on the real chat page (T351 stage 1, the user 2026-09-11): hovering a local file link pops up
a card with the rendered head of the file, or the section a `path#slug` link names, near-instantly.

A hermetic kernel serves one synthetic session whose reply links six paths: a markdown guide (its head), the guide's
`#fold-rules` section (with a [[wikilink]] and a callout inside it), a `#no-such-section` anchor (the head with a one-line
note), a small PNG (the figure at its natural size, capped to the card), a Python file (a highlighted head), a `.env`
(a secrets-shaped name: text plus "open", no request), a markdown-named symlink to that `.env` (judged by its target:
text plus "open") and an absolute path outside the session's folder and the user's home (text plus "open", no request);
the route itself, asked by hand for a refused path, answers 403 with the reason and no text. The acceptance includes
latency: the card stamps the time from the dwell's end to its rendered content; a cached markdown slice (the guide,
warmed on the pusher's path) must render within 250 ms, and a cold one (a file whose time the test rewrites after the
build, so the hover misses the cache) is measured and reported (PV_LATENCY names a file for the numbers). The cold file
carries every remote-loading shape (img src and srcset, a picture's source, a video's poster and src, an audio, an SVG
image, backslash and tab spellings, a tab INSIDE the value, a markdown image): the card shows their alt text and nothing else, and the browser
makes no request to another origin during the whole run. A paint sample (docs/paint.md) carries an inline svg's paint references (fill,
stroke, mask, clip-path, filter, the three marker attributes, an escaped function name, an image-set, a group's fill, the same names on
an HTML span) aimed at a SECOND server this class runs, a request logger on http://localhost:Q, which the page reaches as another
origin; the card must strip them on the sanitizer's inert body (paint-refs.ts dropRemoteRefs, in sanitizeMd and in the preview strip),
so the logger records no request during the run, the offOrigin recorder holds none of its URLs, and the card's html carries no remote
url(). Two controls say an empty log is the strip's work: the sample's same-origin reference (`url(/plots/own.svg#p)`, relative, so it
resolves to the kernel's origin) is kept and requested from the kernel during the hover (the request is what the instrument sees; the
kernel answers it with a 404), and after the run's record is taken the page fetches the logger once (no-cors), which must be its one
line, so the logger is one the page can reach. Red before the fix, the same at the base 6cf6839ba (this file run over a copy of that
tree) and with both passes removed (2026-09-23): the logger recorded ten requests during the hover (fill, stroke, clip-path, mask, the
mask's image-set, the three markers, the escaped function name, the group's fill; the two masks with the page's origin as Referer,
the rest with none), the offOrigin recorder held eleven URLs (the filter's request event fired and no request reached the logger),
and the card held every value as written. Either pass alone keeps the run green: both run the one strip, dropRemoteRefs.
Asserted, dark and light: nothing opens before the dwell and the card is up after
it; leaving closes it after the grace; Escape closes it; the keyboard's focus opens it; the kernel's verdict rides each
link as data-preview and the refused links make NO request; the section card shows the section alone with the grammar
additions rendered; the missing anchor falls back to the head with its note; the image, code and text-only cards have
their kinds; "open" on the section card lands the file viewer scrolled to that heading; GET /perf counts the slices
(the warmed guide a hit, the code a miss). With PV_SHOTS=<dir> the driver writes the five cards in both themes. Skips
LOUDLY without the extension deps or a Playwright browser; the CI extension job installs Chromium and runs served files
with ROMP_SERVED_TESTS_REQUIRE=1, which turns any skip into a failure there. SYNTHETIC fixtures only (session web, the
notes-api demo world, placeholder uuids, an invented guide)."""
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

SID = "aaaaaaaa-1111-2222-3333-444444444444"
U_UUID = "11111111-2222-3333-4444-555555555555"
A_UUID = "22222222-3333-4444-5555-666666666666"
GUIDE = """# Guide

The guide's intro paragraph, the first thing a reader sees.

## Install

Run the installer, then restart the notes-api service.

## Fold Rules

A fold keeps the summary and hides the mechanics; see [[Glossary]] for the words.

> [!NOTE] Folds survive re-renders.

## Later

The part after the fold rules.
"""
APP_PY = "def main():\n    print('notes-api')\n\n\nif __name__ == '__main__':\n    main()\n"


def _png(w=2, h=2, rgb=(60, 120, 200)):
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


DRIVER = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const { chromium } = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
let browser;
try { browser = await chromium.launch(); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const page = await browser.newPage({ viewport: { width: 1100, height: 760 }, deviceScaleFactor: 2 });
let fileRequests = 0;
page.on("request", (r) => { if (/\/file\?/.test(r.url())) fileRequests++; });
await page.goto(cfg.chat);
await page.waitForSelector("#tabs .tab[data-id]", { timeout: 20000 });
await page.click('#tabs .tab[data-id="' + cfg.sid + '"]');
try { await page.waitForFunction(() => document.querySelectorAll("#content .file-uri-link").length >= 12, null, { timeout: 20000 }); }
catch (e) {   // say which links rendered, so a short count is diagnosable from the failure alone
  const got = await page.evaluate(() => Array.from(document.querySelectorAll("#content .file-uri-link")).map((a) => a.dataset.path + (a.dataset.frag ? "#" + a.dataset.frag : "")));
  console.error("links rendered (" + got.length + "): " + JSON.stringify(got)); process.exit(1);
}
await page.mouse.move(900, 720); await page.waitForTimeout(300);
const CARD = "#file-preview-pop";
const shown = () => page.evaluate(() => { const p = document.getElementById("file-preview-pop"); return !!p && getComputedStyle(p).display !== "none"; });
const links = await page.evaluate(() => Array.from(document.querySelectorAll("#content .file-uri-link")).map((a) => ({ text: a.textContent, path: a.dataset.path, frag: a.dataset.frag || null, preview: a.dataset.preview || null, rel: a.dataset.rel || null, why: a.dataset.previewWhy || null })));
const sel = (path, frag) => '#content .file-uri-link[data-path="' + path + '"]' + (frag ? '[data-frag="' + frag + '"]' : ":not([data-frag])");
const card = () => page.evaluate(() => {
  const p = document.getElementById("file-preview-pop"); if (!p || getComputedStyle(p).display === "none") return null;
  const body = p.querySelector(".fp-body"); const img = p.querySelector(".fp-img"); const code = p.querySelector(".fp-code code");
  const r = p.getBoundingClientRect();
  return { title: (p.querySelector(".fp-title") || {}).textContent ?? null, sub: (p.querySelector(".fp-sub") || {}).textContent ?? null,
           note: (p.querySelector(".fp-note") || {}).textContent ?? null, kind: body ? body.className : null, loader: !!p.querySelector(".rl-in"),
           text: body ? body.textContent.trim().slice(0, 400) : null, html: body ? body.innerHTML.slice(0, 2000) : null, hasOpen: !!p.querySelector(".fp-open"),
           img: img ? { src: img.getAttribute("src"), w: img.getBoundingClientRect().width, natural: img.naturalWidth, inCard: img.getBoundingClientRect().width <= r.width } : null,
           codeClass: code ? code.className : null, box: { w: r.width, h: r.height, top: r.top, left: r.left },
           renderMs: p.dataset.renderMs ? Number(p.dataset.renderMs) : null, sliceHit: p.dataset.sliceHit ?? null,
           theme: document.body.classList.contains("theme-light") ? "light" : "dark" };
});
const offOrigin = [];   // every http(s) request the page makes to another origin: there must be none (a hover is not a beacon)
page.on("request", (r) => { const u = r.url(); if (/^https?:/.test(u) && !u.startsWith("http://127.0.0.1:")) offOrigin.push(u); });
const hoverCard = async (path, frag) => {
  const before = fileRequests;
  const t0 = Date.now();
  await page.hover(sel(path, frag));
  await page.waitForTimeout(150);
  const early = await shown();
  await page.waitForFunction(() => { const p = document.getElementById("file-preview-pop"); return !!p && getComputedStyle(p).display !== "none" && !!p.querySelector(".fp-body"); }, null, { timeout: 5000 });
  const ms = Date.now() - t0;
  await page.waitForTimeout(150);
  const c = await card();
  return { early, ms, requests: fileRequests - before, card: c };
};
const shot = async (name) => { if (!cfg.shots) return; fs.mkdirSync(cfg.shots, { recursive: true }); const b = await (await page.$(CARD)).boundingBox(); await page.screenshot({ path: cfg.shots + "/" + name + ".png", clip: { x: Math.max(0, b.x - 40), y: Math.max(0, b.y - 60), width: Math.min(1100, b.width + 80), height: Math.min(760, b.height + 100) } }); };
const leave = async () => { await page.mouse.move(900, 720); await page.waitForTimeout(400); return await shown(); };
// the cold read: the build warmed docs/cold.md, so its time is rewritten before each hover (a new mtime is a new cache key).
// Whether the hover then reads COLD is the pusher's timing, not this driver's: a message build between the rewrite and
// the hover re-warms the new key (kernel.py _slice_warm, one `warm` per load), and under a slow full serial run one does
// slip in (a full run read a hit where CI and a run alone read a miss). So the kernel's own warm counter is sampled
// around the rewrite and the hover, and the assertion is keyed on it: a warm in between means a hit, none means a miss.
let coldBump = 0;
const bumpCold = () => { coldBump += 1; const s = Date.now() / 1000 + 5 * coldBump; fs.utimesSync(cfg.cold, s, s); };
const perfNow = async () => page.evaluate(async () => { const r = await fetch("/perf", { credentials: "same-origin" }); const j = await r.json(); return j.fileSlice || { warm: 0 }; });
const out = { links, themes: {} };
for (const theme of ["dark", "light"]) {
  if (theme === "light") { await page.evaluate(() => document.body.classList.add("theme-light")); await page.waitForTimeout(200); }
  const t = {};
  t.head = await hoverCard("docs/guide.md", null); await shot("romp_chat-file-preview-markdown-" + theme); t.headHidden = await leave();
  t.section = await hoverCard("docs/guide.md", "fold-rules"); await shot("romp_chat-file-preview-section-" + theme); t.sectionHidden = await leave();
  t.missing = await hoverCard("docs/guide.md", "no-such-section"); t.missingHidden = await leave();
  t.image = await hoverCard("plots/figure.png", null); await shot("romp_chat-file-preview-image-" + theme); t.imageHidden = await leave();
  t.code = await hoverCard("src/app.py", null); await shot("romp_chat-file-preview-code-" + theme); t.codeHidden = await leave();
  const warmBefore = (await perfNow()).warm; bumpCold(); t.cold = await hoverCard("docs/cold.md", null); t.coldWarmedAhead = (await perfNow()).warm > warmBefore; t.coldHidden = await leave();
  t.outside = await hoverCard(cfg.outside, null); await shot("romp_chat-file-preview-textonly-" + theme); t.outsideHidden = await leave();
  t.secret = await hoverCard("docs/.env", null); t.secretHidden = await leave();
  // a BARE filename the repo index resolved (tier 3): the preview comes from the resolved absolute path, the same path
  // the click opens (T364 step A); a notes file whose text is credential-shaped is text with the belt's own words
  // (a code-span link is keyed by its RESOLVED target, the path the click opens; the token is the span's text)
  t.bare = await hoverCard("docs/notes/rollup-notes.md", null); t.bareHidden = await leave();
  t.leaky = await hoverCard("docs/notes/leaky-notes.md", null); t.leakyHidden = await leave();
  out.themes[theme] = t;
}
await page.evaluate(() => document.body.classList.remove("theme-light")); await page.waitForTimeout(200);
// the paint sample: every request URL the page makes during its hover is recorded, the same-origin control's own request is
// awaited (bounded), the card stays up 500 ms more, and its whole html is read (card() cuts it at 2000 characters)
const paintRequests = [];
const onPaintRequest = (r) => paintRequests.push(r.url());
page.on("request", onPaintRequest);
const ownPaint = page.waitForRequest((r) => r.url().split("?")[0].endsWith("/plots/own.svg"), { timeout: 8000 }).then(() => true, () => false);
out.paint = await hoverCard("docs/paint.md", null);
out.paintOwnRequested = await ownPaint;
await page.waitForTimeout(500);
out.paintHtml = await page.evaluate(() => { const b = document.querySelector("#file-preview-pop .fp-body"); return b ? b.innerHTML : null; });
page.off("request", onPaintRequest);
out.paintRequests = paintRequests;
out.paintHidden = await leave();
// the keyboard's route: focus opens after the dwell; Escape closes
await page.focus(sel("docs/guide.md", null)); await page.waitForTimeout(150); out.focusEarly = await shown();
await page.waitForFunction(() => { const p = document.getElementById("file-preview-pop"); return !!p && getComputedStyle(p).display !== "none" && !!p.querySelector(".fp-body"); }, null, { timeout: 5000 });
out.focusCard = await card();
await page.keyboard.press("Escape"); await page.waitForTimeout(100); out.escapeHidden = !(await shown());
// the LINK opens the viewer scrolled to the heading it names (the card carries no open control, T369); the card was up
await hoverCard("docs/guide.md", "fold-rules");
await page.click(sel("docs/guide.md", "fold-rules"));
await page.waitForSelector("#romp-fileview", { timeout: 10000 });
await page.waitForFunction(() => !!document.querySelector('#romp-fileview [id="md-fold-rules"]'), null, { timeout: 10000 });   // the viewer's heading ids wear md- (file-view.ts)
await page.waitForTimeout(400);
out.opened = await page.evaluate(() => {
  const box = document.querySelector("#romp-fileview .fileview"); const h = document.querySelector('#romp-fileview [id="md-fold-rules"]');
  const b = box.getBoundingClientRect(), r = h.getBoundingClientRect();
  return { heading: h.textContent.trim(), top: r.top, boxTop: b.top, boxBottom: b.bottom, inView: r.top >= b.top - 1 && r.bottom <= b.bottom + 1, cardHidden: !(document.getElementById("file-preview-pop") && getComputedStyle(document.getElementById("file-preview-pop")).display !== "none") };
});
out.offOrigin = offOrigin.slice();   // the run's record, taken before the logger's control below adds its one request
out.perf = await page.evaluate(async () => { const r = await fetch("/perf", { credentials: "same-origin" }); const j = await r.json(); return j.fileSlice || null; });
// the route by hand (the client never asks for these): a refused path answers 403 with why, and never the text
out.refused = await page.evaluate(async (paths) => {
  const out = {};
  for (const [name, p] of Object.entries(paths)) {
    const r = await fetch("/file?path=" + encodeURIComponent(p) + "&slice=1&sid=" + encodeURIComponent(document.querySelector("#tabs .tab.active[data-id]").dataset.id), { credentials: "same-origin" });
    let j = null; try { j = await r.json(); } catch (e) { j = null; }
    out[name] = { status: r.status, why: j && j.why, allowed: j && j.allowed, hasText: !!(j && j.text) };
  }
  return out;
}, { outside: cfg.outside, secret: "docs/.env", dressed: "docs/report.md", missing: "docs/nope.md" });
// the logger's control, after the run's record: one no-cors fetch from the page, so an empty log is not a server it cannot reach
out.reach = await page.evaluate((u) => fetch(u, { mode: "no-cors", cache: "no-store" }).then(() => "ok", (e) => String(e)), cfg.remote + "/reach");
fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
await browser.close();
process.exit(0);
"""


# nothing in this file may resolve on the network: the strip must remove every one of these before the browser sees them
COLD = ("# Cold\n\nThe later note: the build warmed it, and the test rewrites its time so the hover reads it cold.\n\n"
        '<img srcset="https://remote.invalid/a.png 1x" alt="srcset-only">\n\n'
        '<picture><source srcset="https://remote.invalid/b.png"><img src="plots/figure.png" alt="pic"></picture>\n\n'
        '<video poster="https://remote.invalid/p.png" src="https://remote.invalid/v.mp4"></video>\n\n'
        '<audio src="https://remote.invalid/a.mp3"></audio>\n\n'
        '<svg><image href="https://remote.invalid/s.png"/></svg>\n\n'
        '<img src="\\\\remote.invalid/c.png" alt="backslashes">\n\n'
        '<img src="\thttps://remote.invalid/d.png" alt="tabbed">\n\n'
        '<img src="/\t/remote.invalid/f.png" alt="tab-inside">\n\n'
        "![markdown-remote](https://remote.invalid/e.png)\n")


def _paint(remote):
    """docs/paint.md: an inline svg's paint references aimed at the second server (`remote`, http://localhost:Q), every one of
    which the card must strip, and the controls it must keep: a same-document `url(#g)` and a same-origin relative reference."""
    def svg(inner, root=""):
        return '<svg width="12" height="12"%s>%s</svg>' % (root, inner)
    def rect(attrs):
        return '<rect width="12" height="12" %s/>' % attrs
    shapes = [
        svg(rect('fill="url(%s/h-fill.svg#p)"' % remote)),
        svg(rect('fill="none" stroke="url(%s/h-stroke.svg#p)" stroke-width="4"' % remote)),
        svg(rect('fill="red" clip-path="url(%s/h-clip.svg#c)"' % remote)),
        svg(rect('fill="red" mask="url(%s/h-mask.svg#m)"' % remote)),
        svg(rect('fill="red" mask="image-set(&quot;%s/h-maskset.png&quot; 1x)"' % remote)),
        svg('<path d="M1 1 L6 6 L11 11" stroke="red" fill="none" marker-start="url(%s/h-ms.svg#a)" marker-mid="url(%s/h-mm.svg#b)" '
            'marker-end="url(%s/h-me.svg#c)"/>' % (remote, remote, remote)),
        svg(rect('fill="red" filter="blur(2px) url(%s/h-filter.svg#f)"' % remote)),
        svg(rect('fill="\\75 rl(%s/h-escfn.svg#p)"' % remote)),
        svg('<g fill="url(%s/h-group.svg#p)">%s</g>' % (remote, rect(""))),
        '<span fill="url(%s/h-htmlfill.svg#p)" mask="url(%s/h-htmlmask.svg#m)">an HTML span</span>' % (remote, remote),
        svg('<defs><linearGradient id="g"><stop offset="0" stop-color="red"/></linearGradient></defs>' + rect('fill="url(#g)"')),
        svg(rect('fill="url(/plots/own.svg#p)"')),
    ]
    return "# Paint\n\nAn inline figure sample.\n\n" + "\n\n".join(shapes) + "\n\nThe end.\n"


class _Logger(BaseHTTPRequestHandler):
    """The second server: logs every request's method, path and the headers that say who asked (Referer, Sec-Fetch-Dest,
    Host) into the class's list, and answers a paint document for any .svg, a PNG for any .png, 404 otherwise."""
    log = None

    def do_GET(self):
        self.log.append({"method": self.command, "path": self.path, "referer": self.headers.get("Referer"),
                         "dest": self.headers.get("Sec-Fetch-Dest"), "host": self.headers.get("Host")})
        p = self.path.split("?")[0]
        if p.endswith(".svg"):
            body, ctype = (b'<svg xmlns="http://www.w3.org/2000/svg"><defs><pattern id="p" width="1" height="1"><rect width="1" height="1" '
                           b'fill="blue"/></pattern></defs></svg>'), "image/svg+xml"
        elif p.endswith(".png"):
            body, ctype = _png(), "image/png"
        else:
            self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers(); return
        self.send_response(200); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):   # quiet: the log above is the record
        pass


class ServedFilePreview(unittest.TestCase):
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
            raise unittest.SkipTest("extension deps absent (npm ci not run here) — the served lab needs them; CI's extension job has them and requires this file to run")
        probe = subprocess.run(["node", "-e", "const p=require(process.argv[1]);process.stdout.write(p.chromium.executablePath())",
                                os.path.join(EXT, "node_modules", "playwright")], capture_output=True, text=True)
        if probe.returncode != 0 or not os.path.exists(probe.stdout.strip()):
            raise unittest.SkipTest("no playwright browser on this box — the served lab needs one; CI's extension job installs Chromium and requires this file to run")
        cls.lab = tempfile.mkdtemp(prefix="file-preview-")
        # the second server, another origin to the page (http.server binds IPv4, where this box's `localhost` resolves; the
        # logger's control in the driver is the check that the browser reaches it there)
        cls.remote_log = []
        cls.remote_srv = srv = ThreadingHTTPServer(("localhost", 0), type("Logger", (_Logger,), {"log": cls.remote_log}))
        thread = threading.Thread(target=srv.serve_forever, daemon=True)

        def end_remote():   # registered before the start, so it runs on every exit path (a failed boot included)
            if thread.ident is not None:   # shutdown() waits for serve_forever to return, which a thread never started never does
                srv.shutdown()
            srv.server_close()
        cls.addClassCleanup(end_remote)
        thread.start()
        cls.remote = "http://localhost:%d" % cls.remote_srv.server_address[1]
        dist = os.path.join(cls.lab, "dist")
        lab_dist.copy_dist(dist)   # the checkout's ONE build of the bundles, copied under its lock (tests/lab_dist.py)
        state = os.path.join(cls.lab, "xdg", "romp")
        cwd = os.path.join(cls.lab, "proj")
        for d in ("names", "sdk", "states"):
            os.makedirs(os.path.join(state, d), exist_ok=True)
        for d in ("docs", "plots", "src"):
            os.makedirs(os.path.join(cwd, d), exist_ok=True)
        os.makedirs(os.path.join(cls.lab, "outside"), exist_ok=True)
        subprocess.run(["git", "init", "-q"], cwd=cwd, check=True, capture_output=True)   # the repo index behind a bare filename (tier 3)
        os.makedirs(os.path.join(cwd, "docs", "notes"), exist_ok=True)
        Path(cwd, "docs", "notes", "rollup-notes.md").write_text("# Rollup notes\n\nThe rollup gathers every open task into one line per session.\n")
        # a notes file whose TEXT is credential-shaped (assembled here, never a literal: the scanner reads this repo too):
        # the content belt refuses its warm, and the card must say so (T364: it blamed the confinement instead)
        Path(cwd, "docs", "notes", "leaky-notes.md").write_text("# Leaky notes\n\n" + "api" + "_key" + " = " + "Q" * 24 + "\n")
        Path(cwd, "docs", "guide.md").write_text(GUIDE)
        Path(cwd, "docs", ".env").write_text("SETTING=not-a-real-value\n")
        Path(cwd, "docs", "cold.md").write_text(COLD)
        Path(cwd, "docs", "paint.md").write_text(_paint(cls.remote))
        os.symlink(os.path.join(cwd, "docs", ".env"), os.path.join(cwd, "docs", "report.md"))   # an innocent name over a secret
        Path(cwd, "plots", "figure.png").write_bytes(_png())
        Path(cwd, "src", "app.py").write_text(APP_PY)
        cls.outside = os.path.join(cls.lab, "outside", "notes.md")
        cls.cold = os.path.join(cwd, "docs", "cold.md")
        Path(cls.outside).write_text("# Outside\n\nnot under the session's folder\n")
        Path(state, "names", SID).write_text("web\t%s\t#9cd2ff\t#0c1a2e\n" % cwd)
        Path(state, "sdk", SID + ".json").write_text(json.dumps(
            {"sid": SID, "name": "web", "cwd": cwd, "mode": "auto", "effort": "high", "lastSid": SID, "alive": True,
             "model": "claude-opus-5", "liveModel": "Opus 5"}))
        claude = os.path.join(cls.lab, "claude")
        proj = os.path.join(claude, "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(cwd)))
        os.makedirs(proj, exist_ok=True)
        reply = ("Read docs/guide.md first, then the rule at docs/guide.md#fold-rules (docs/guide.md#no-such-section is not a section).\n\n"
                 "The plot is at plots/figure.png and the code at src/app.py; the secrets live in docs/.env (and docs/report.md is a link to them); "
                 "the later note is docs/cold.md and the figure sample docs/paint.md; notes outside the project sit at %s. "
                 "The rollup is written up in `rollup-notes.md` and the leak in `leaky-notes.md`." % cls.outside)   # bare filenames as a session writes them: in code spans
        Path(proj, SID + ".jsonl").write_text(
            json.dumps({"type": "user", "uuid": U_UUID, "parentUuid": None, "timestamp": "2026-09-05T00:00:00.000Z", "sessionId": SID,
                        "message": {"role": "user", "content": "Where do I start with the notes-api docs?"}}) + "\n" +
            json.dumps({"type": "assistant", "uuid": A_UUID, "parentUuid": U_UUID, "timestamp": "2026-09-05T00:00:05.000Z", "sessionId": SID,
                        "message": {"role": "assistant", "model": "claude-opus-5", "content": [{"type": "text", "text": reply}], "stop_reason": "end_turn"}}) + "\n")
        cls.port, cls.token = _free_port(), "testtok-filepreview"
        env = _lab.kernel_env(cls.lab, claude, dist, cls.port, cls.token, ROMP_HOST_NAME="TESTHOST")
        cls.klog = os.path.join(cls.lab, "kernel.log")
        cls.kernel = subprocess.Popen([os.path.join(BIN, "romp-kernel")], stdout=open(cls.klog, "w"), stderr=subprocess.STDOUT, env=env)
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
        k = getattr(cls, "kernel", None)
        if k:
            k.kill(); k.wait()
        shutil.rmtree(getattr(cls, "lab", ""), ignore_errors=True)

    def test_a_hover_previews_the_file_or_its_section_after_the_dwell_and_a_refused_path_is_text_with_no_request(self):
        cfg = os.path.join(self.lab, "cfg.json")
        with open(cfg, "w") as f:
            json.dump({"chat": "http://127.0.0.1:%d/chat?token=%s" % (self.port, self.token), "sid": SID, "outside": self.outside, "cold": self.cold,
                       "remote": self.remote, "shots": os.environ.get("PV_SHOTS", "")}, f)
        driver = os.path.join(self.lab, "driver.mjs")
        with open(driver, "w") as f:
            f.write(DRIVER)
        p = subprocess.run(["node", driver], capture_output=True, text=True, timeout=300,
                           env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg))
        if p.returncode == 3:
            raise unittest.SkipTest("no playwright browser on this box — the served lab needs one; CI's extension job installs Chromium and requires this file to run")
        self.assertEqual(p.returncode, 0, "driver failed:\n" + p.stdout[-3000:] + p.stderr[-3000:] + "\nkernel:\n" + open(self.klog).read()[-1500:])
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
        self.assertIsNotNone(line, "driver printed no result:\n" + p.stdout[-3000:])
        r = json.loads(line[len("RESULT:"):])
        # the paint sample (the docstring's paragraph): the card strips every paint reference to another origin before its nodes
        # reach the page, so the second server hears nothing during the run
        paint_log = [l for l in self.remote_log if l["path"] != "/reach"]
        html = r["paintHtml"] or ""
        # the positive control: the card rendered and a paint fetch it keeps is visible to the recorder
        with self.subTest("the same-origin control was requested from the kernel during the hover"):
            self.assertTrue(r["paintOwnRequested"] and any(u.split("?")[0].endswith("/plots/own.svg") for u in r["paintRequests"]),
                            "the same-origin paint reference was kept and requested from the kernel during the hover: %r" % r["paintRequests"])
        # the STAYS rule: a strip that took these too would be an over-strip the second server cannot see
        with self.subTest("the same-origin reference stands in the card as written"):
            self.assertIn('fill="url(/plots/own.svg#p)"', html, "the same-origin reference stands in the card as written")
        with self.subTest("the same-document reference stands in the card as written"):
            self.assertIn('fill="url(#g)"', html, "the same-document reference stands in the card as written")
        # the fix on the hover path: the paint pass removed every remote url() on the inert body, so nothing was fetched
        with self.subTest("no request reached the second server"):
            self.assertEqual(paint_log, [], "no request reached the second server during the run (a hover must not be a beacon)")
        with self.subTest("the offOrigin recorder holds none of the second server's URLs"):
            self.assertEqual([u for u in r["offOrigin"] if u.startswith(self.remote)], [], "the offOrigin recorder holds none of the second server's URLs")
        # the DOM half: the attributes are gone from the card, not merely unfetched
        with self.subTest("the card's html names the second server nowhere"):
            self.assertIsNotNone(r["paintHtml"], "the paint card rendered a body")
            self.assertNotIn("localhost:", html, "no reference to the second server stands in the card: %s" % html)
        with self.subTest("the card's html holds no absolute url()"):
            self.assertNotIn("url(http", html, "no absolute url() stands in the card: %s" % html)
        # the harness: without it an empty log could be a server the page cannot reach
        with self.subTest("the second server's control"):
            self.assertEqual(r["reach"], "ok", "the page's no-cors fetch to the second server completed")
            self.assertEqual([l["path"] for l in self.remote_log if l["path"] == "/reach"], ["/reach"], "the second server logged the control's fetch once")
        # the links, as the kernel's verdict dressed them
        by = {}
        for l in r["links"]:
            by[(l["path"], l["frag"])] = l
        self.assertEqual(by[("docs/guide.md", None)]["preview"], "markdown")
        self.assertEqual(by[("docs/guide.md", "fold-rules")]["preview"], "markdown", "the anchored link is the same file: %r" % by)
        self.assertEqual(by[("docs/guide.md", "fold-rules")]["text"], "docs/guide.md#fold-rules", "the slug moved into the link, the token reads whole")
        self.assertEqual(by[("plots/figure.png", None)]["preview"], "image")
        self.assertEqual(by[("src/app.py", None)]["preview"], "code")
        self.assertIsNone(by[("docs/.env", None)]["preview"], "a secrets-shaped name: no preview")
        self.assertIsNone(by[("docs/report.md", None)]["preview"], "a markdown name over a secret: judged by what it points at, no preview")
        self.assertIsNone(by[(self.outside, None)]["preview"], "outside the session's folder and home: no preview")
        self.assertEqual(by[("docs/cold.md", None)]["preview"], "markdown")
        latency = {"cached": [], "cold": [], "code": []}      # dwell end → rendered card, ms, per theme
        for theme in ("dark", "light"):
            t = r["themes"][theme]
            for name in ("head", "section", "missing", "image", "code", "cold", "outside", "secret"):
                h = t[name]
                self.assertFalse(h["early"], "%s/%s: nothing before the dwell" % (theme, name))
                self.assertGreaterEqual(h["ms"], 300, "%s/%s: the card came up only after the dwell: %r ms" % (theme, name, h["ms"]))
                self.assertIsNotNone(h["card"], "%s/%s: the card is up" % (theme, name))
                self.assertEqual(h["card"]["theme"], theme)
                self.assertFalse(h["card"]["hasOpen"], "%s/%s: a file card carries no open control; the link opens the file (T369)" % (theme, name))
                self.assertGreaterEqual(h["card"]["box"]["w"], 300); self.assertGreaterEqual(h["card"]["box"]["h"], 120)
                self.assertFalse(t[name + "Hidden"], "%s/%s: leaving closes the card after the grace" % (theme, name))
            head, sec, miss = t["head"]["card"], t["section"]["card"], t["missing"]["card"]
            self.assertEqual((head["title"], head["sub"], head["note"]), ("guide.md", None, None))
            self.assertIn("fp-markdown", head["kind"]); self.assertIn("<h1", head["html"]); self.assertIn("intro paragraph", head["text"])
            self.assertEqual((sec["title"], sec["sub"]), ("guide.md", "#fold-rules"))
            self.assertIn("fp-section", sec["kind"]); self.assertIn("A fold keeps the summary", sec["text"])
            self.assertNotIn("intro paragraph", sec["text"], "the section alone"); self.assertNotIn("after the fold rules", sec["text"])
            # ruling 14 (one grammar, the 2026-09-15 pull-in): the preview card renders through md-config.ts, whose decision 2
            # shows an unresolved wikilink outside a file document as a dead span KEEPING its brackets; upstream's md-wiki.ts
            # (the twin, which rendered [[Glossary]] as its plain text) is in the tree and unreferenced
            self.assertIn("[[Glossary]]", sec["text"], "the wikilink rendered as a dead span with its brackets (md-config.ts decision 2)")
            self.assertIn("md-callout-title", sec["html"], "the callout's label rendered (md-config.ts, the one grammar: CALLOUT_TITLE_CLASS; md-wiki.ts is unreferenced)")
            # latency (the acceptance, the user 2026-09-11): the guide was warmed on the pusher's path so its slice is a hit,
            # and a cached markdown slice renders well inside the near-instant band; the cold one (its time rewritten after
            # the build) is a miss, measured and reported, not bounded (a disk read on a shared box is not ours to promise)
            cold = t["cold"]["card"]
            self.assertIn("fp-markdown", cold["kind"]); self.assertIn("later note", cold["text"])
            self.assertEqual(head["sliceHit"], "1", "%s: the guide's slice came from the cache" % theme)
            if t["coldWarmedAhead"]:   # a pusher cycle re-warmed the rewritten key before the hover (the kernel's warm counter moved): a hit, honestly
                self.assertEqual(cold["sliceHit"], "1", "%s: the pusher warmed the rewritten file ahead of the hover, so the slice was a hit" % theme)
            else:
                self.assertEqual(cold["sliceHit"], "0", "%s: no warm between the rewrite and the hover, so the rewritten file was read cold" % theme)
            self.assertIsNotNone(head["renderMs"]); self.assertIsNotNone(cold["renderMs"])
            # the remote loads in the cold file: stripped on the inert DOM, so the card shows alt text and nothing else
            self.assertNotIn("remote.invalid", cold["html"], "%s: no remote URL reaches the card: %r" % (theme, cold["html"]))
            for gone in ("<video", "<audio", "<source", "<image"):
                self.assertNotIn(gone, cold["html"], "%s: %s stripped" % (theme, gone))
            for alt in ("srcset-only", "backslashes", "tabbed", "tab-inside", "markdown-remote"):
                self.assertIn(alt, cold["text"], "%s: the remote image reads as its alt text" % theme)
            self.assertIn('alt="pic"', cold["html"], "the picture's local img stays")
            self.assertLessEqual(head["renderMs"], 250, "%s: dwell end to rendered card, cached: %r ms" % (theme, head["renderMs"]))
            latency["cached"].append(head["renderMs"]); latency["cold"].append(cold["renderMs"]); latency["code"].append(t["code"]["card"]["renderMs"])
            self.assertIn("fp-markdown", miss["kind"]); self.assertEqual(miss["sub"], None)
            self.assertEqual(miss["note"], 'no section "no-such-section" in this file; its head instead'); self.assertIn("intro paragraph", miss["text"])
            img = t["image"]["card"]
            self.assertEqual(img["title"], "figure.png"); self.assertIn("fp-image", img["kind"])
            self.assertTrue(img["img"] and "/file?path=" in img["img"]["src"] and img["img"]["inCard"], "the figure from the bytes route, inside the card: %r" % img["img"])
            code = t["code"]["card"]
            self.assertEqual(code["title"], "app.py"); self.assertIn("fp-code", code["kind"]); self.assertIn("print", code["text"])
            self.assertIn("language-python", code["codeClass"] or "", "highlighted as Python: %r" % code["codeClass"])
            # the text card says exactly which condition refused (T364: a four-way guess blamed the confinement for everything)
            for name, expect_title, why in (("outside", "notes.md", "outside the session's folder and your home"), ("secret", ".env", "a secrets-shaped name"),
                                            ("leaky", "leaky-notes.md", "looks like a secret")):
                c = t[name]["card"]
                self.assertEqual(c["title"], expect_title); self.assertIn("fp-text", c["kind"])
                self.assertEqual(c["note"], "shown as text: " + why, "%s/%s: the kernel's own refusal on the card" % (theme, name))
                self.assertEqual(t[name]["requests"], 0, "%s/%s: no request at all" % (theme, name))
            # a bare filename the repo index resolved previews from its resolved path (step A: the local kernel)
            bare = t["bare"]["card"]
            self.assertEqual(bare["title"], "rollup-notes.md"); self.assertIn("fp-markdown", bare["kind"]); self.assertIn("one line per session", bare["text"])
            self.assertGreaterEqual(t["bare"]["requests"], 1, "%s: the slice fetched from the resolved path" % theme)
            self.assertGreaterEqual(t["head"]["requests"], 1, "a text preview is one fetch")
        # the keyboard's route and Escape
        if os.environ.get("PV_LATENCY"):
            with open(os.environ["PV_LATENCY"], "w") as f:
                json.dump(latency, f)
        self.assertFalse(r["focusEarly"]); self.assertIsNotNone(r["focusCard"]); self.assertEqual(r["focusCard"]["title"], "guide.md")
        self.assertTrue(r["escapeHidden"], "Escape closes the card")
        # the link lands the viewer on the section it names, and the card closes
        # the link attributes: the kind on the previewable links, the why on the refused ones (the next report reads it off the DOM)
        by = {(l["path"], l["frag"]): l for l in r["links"]}
        bare_link, leaky_link = by[("docs/notes/rollup-notes.md", None)], by[("docs/notes/leaky-notes.md", None)]
        self.assertEqual((bare_link["text"], bare_link["preview"]), ("rollup-notes.md", "markdown"), "a bare name the index resolved links to its resolved path and carries the kind: %r" % r["links"])
        self.assertEqual((leaky_link["text"], leaky_link["preview"], leaky_link["why"]), ("leaky-notes.md", None, "looks like a secret"))
        self.assertEqual(by[(self.outside, None)]["why"], "outside the session's folder and your home")
        self.assertEqual(by[("docs/.env", None)]["why"], "a secrets-shaped name")
        self.assertEqual(by[("docs/report.md", None)]["why"], "a secrets-shaped name", "the symlink named as markdown over the secrets file: the REAL path is judged first, so the reason names the secret: %r" % by[("docs/report.md", None)])
        o = r["opened"]
        self.assertEqual(o["heading"], "Fold Rules"); self.assertTrue(o["inView"], "the heading is in the viewer's view: %r" % o)
        self.assertTrue(o["cardHidden"], "the card closed when the viewer opened")
        # the counters: the guide was warmed on the pusher's path (a hit at the first hover); the code file was a miss
        pf = r["perf"]
        self.assertIsNotNone(pf, "GET /perf carries fileSlice")
        self.assertGreaterEqual(pf["warm"], 1, "the markdown the reply linked was warmed ahead of the hover: %r" % pf)
        self.assertGreaterEqual(pf["hit"], 1, "…so its first slice was a hit: %r" % pf)
        self.assertGreaterEqual(pf["miss"], 1, "the code file is read on demand: %r" % pf)
        self.assertGreater(pf["bytes"], 0)
        # the route refuses by hand: 403 with why, no text
        self.assertEqual(r["offOrigin"], [], "no request left this kernel during the whole run (the review: a hover must not be a beacon)")
        rf = r["refused"]
        self.assertEqual((rf["outside"]["status"], rf["outside"]["why"], rf["outside"]["hasText"]), (403, "outside the session's folder and your home", False), rf)
        self.assertEqual((rf["secret"]["status"], rf["secret"]["why"]), (403, "a secrets-shaped name"), rf)
        self.assertEqual((rf["dressed"]["status"], rf["dressed"]["why"]), (403, "a secrets-shaped name"), "the symlink is judged by its target: %r" % rf)
        self.assertEqual((rf["missing"]["status"], rf["missing"]["why"]), (403, "not a file"), rf)


if __name__ == "__main__":
    unittest.main()
