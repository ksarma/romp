#!/usr/bin/env python3
"""A signed-in dashboard, in a real browser, loads what it loads over the page key and the per-file caps.

The browser's login cookie holds a session id that opens the page documents and the static bundles; a JSON read, a POST
or a socket also needs the page key (this origin's localStorage; the X-Romp-Key header from the fetch wrapper, k= on a
socket dial), and a header-less /file load carries a per-file cap in its URL (ui/webview/file-cap.ts). This lab drives
the REAL chat page of a hermetic kernel in playwright's Chromium and checks every road a page takes to the kernel:

  1. Signing in through `?token=` leaves one session cookie named for this kernel, no legacy cookie, no `token=` in the
     address, and the page key in this kernel's own storage slot (keyed by the cookie's name). Every socket the page
     dials carries k= equal to that key; a fetch reads /sessions. A message's authored /file image loads, capped; the
     inline preview of a mentioned figure loads through fileUrl, capped; the authored download link downloads the
     file's bytes; a PDF mention's own tab (a Ctrl-click) opens its capped /file URL with a 200; the viewer's figure
     (a relative src rewritten through fileUrl) loads; the viewer's Download button downloads; the PDF hover card's frame
     loads; a Ctrl-click on a link inside the shown note opens the .svg in its own tab. No /file request the page makes
     is refused.
  2. A stale key never leaves a silent dead page. The cookie of one sign-in beside the key of another (the state two
     racing sign-ins can leave) sends the page to /login and drops the stale key, when the refused fetch is the top
     frame's and when it is a pane's (a pane never navigates itself: it sends the top frame). A page with no key at all
     goes to /login too. Signing in again through the /login form brings the page back.
  3. Two sign-ins racing in one browser end, in each tab, either signed in or on /login, never on a page whose requests
     are all refused.

Nothing here prints a token, a session id, a key or a cap: the driver compares them in memory and reports booleans,
statuses and lengths. The lab token is minted at run time. Skips LOUDLY without the extension deps or a playwright
browser; the CI extension job installs Chromium and runs served files with ROMP_SERVED_TESTS_REQUIRE=1, which turns any
skip into a failure there. SYNTHETIC fixtures only (session web, the notes-api demo world, placeholder uuids)."""
import json
import os
import re
import secrets
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
import zlib
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


def _png(w=2, h=2, rgb=(60, 120, 200)):
    """A tiny valid PNG (RGB, no filter) without a binary fixture."""
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def _pdf():
    """A one-page blank PDF with a correct cross-reference table."""
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 72 72] >>"]
    out, offs = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    x = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1) + b"".join(b"%010d 00000 n \n" % o for o in offs)
    return out + b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, x)


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


# The shared head of every driver: the browser, the config, and the helpers each scene uses. A driver reports one
# RESULT line of booleans, statuses and lengths; no credential value leaves the browser or this process.
HEAD = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const { chromium } = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
let browser;
try { browser = await chromium.launch(); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const VIEW = { viewport: { width: 1100, height: 760 } };
const sessionCookie = async (ctx) => (await ctx.cookies(cfg.origin)).filter((c) => c.name.startsWith("romp_s_"));
const slotOf = async (ctx) => { const s = await sessionCookie(ctx); return s.length === 1 ? "romp.pageKey." + s[0].name : ""; };
const status = (page, path) => page.evaluate(async (p) => (await fetch(p)).status, path);
const onLogin = (page) => new URL(page.url()).pathname === "/login";
const waitLogin = (page) => page.waitForURL((u) => new URL(u).pathname === "/login", { timeout: cfg.deadline }).then(() => true, () => false);
const out = {};
/** A download's outcome: its failure (null on success) and the saved size; a download that never started or was
 *  refused says so instead of throwing. */
const dlResult = async (dl) => {
  if (!dl) return { failure: "no download started", size: 0 };
  const failure = await dl.failure();
  return { failure, size: failure ? 0 : fs.statSync(await dl.path()).size };
};
"""

SIGNED_IN = HEAD + r"""
const ctx = await browser.newContext({ ...VIEW, acceptDownloads: true });
const page = await ctx.newPage();
const sockets = [];
page.on("websocket", (ws) => sockets.push(ws.url()));
const files = [];   // every /file request any page of this context made: its status, whether it carried a cap, its kind
ctx.on("response", (r) => { let u; try { u = new URL(r.url()); } catch (e) { return; } if (u.pathname === "/file" || /^\/remote\/[^/]+\/file$/.test(u.pathname)) { let fr = null; try { fr = r.request().frame(); } catch (e) { fr = null; } files.push({ status: r.status(), cap: u.searchParams.has("cap"), kind: r.request().resourceType(), download: u.searchParams.get("download") === "1", iframe: !!(fr && fr.parentFrame()), ext: ((u.searchParams.get("path") || "").match(/\.[a-z]+$/) || [""])[0] }); } });
await page.goto(cfg.origin + "/chat?token=" + encodeURIComponent(cfg.token));
await page.waitForSelector('#tabs .tab[data-id="' + cfg.sid + '"]', { timeout: cfg.deadline });
out.addressClean = !/[?&](token|c)=/.test(page.url());
const all = await ctx.cookies(cfg.origin);
const sess = all.filter((c) => c.name.startsWith("romp_s_"));
out.sessionCookies = sess.length;
out.legacyCookie = all.some((c) => c.name === "romp_token");
out.cookieIsToken = sess.some((c) => c.value === cfg.token);
out.cookieHttpOnly = sess.length === 1 && sess[0].httpOnly;
const slot = await slotOf(ctx);
const slots = await page.evaluate(() => Object.keys(localStorage).filter((k) => k.startsWith("romp.pageKey")));
out.slots = slots.length; out.slotIsPerKernel = slots.length === 1 && slots[0] === slot;
const key = await page.evaluate((s) => localStorage.getItem(s) || "", slot);
out.keyLen = key.length;
out.keyIsToken = key === cfg.token;
out.sessions = await status(page, "/sessions");
// the message: its authored image, the inline preview of the mentioned figure, the authored download link
await page.click('#tabs .tab[data-id="' + cfg.sid + '"]');
await page.waitForFunction(() => { const i = document.querySelector('#content img[alt="authored figure"]'); return !!i && i.complete; }, null, { timeout: cfg.deadline });
// read defensively: an image that failed may have been parked by the page (its src moved aside), which reads as no cap
const capIn = (s, base) => { try { return new URL(s || "", base).searchParams.has("cap"); } catch (e) { return false; } };
out.authored = await page.evaluate(() => { const i = document.querySelector('#content img[alt="authored figure"]'); const s = i.getAttribute("src") || ""; let p = "", cap = false; try { const u = new URL(s, location.href); p = u.pathname; cap = u.searchParams.has("cap"); } catch (e) { p = ""; } return { natural: i.naturalWidth, cap, path: p }; });
await page.waitForFunction(() => Array.from(document.querySelectorAll("#content .path-full img")).some((i) => i.complete && i.naturalWidth > 0 && /plots%2Ffigure\.png/.test(i.src)), null, { timeout: cfg.deadline }).catch(() => {});
out.inline = await page.evaluate(() => Array.from(document.querySelectorAll("#content .path-full img")).filter((i) => /plots%2Ffigure\.png/.test(i.src)).map((i) => { let cap = false; try { cap = new URL(i.getAttribute("src") || "", location.href).searchParams.has("cap"); } catch (e) { cap = false; } return { natural: i.naturalWidth, cap }; }));
const link = await page.$('#content a:text-is("the plot as a file")');
out.linkCap = link ? capIn(await link.getAttribute("href"), cfg.origin) : null;
if (link) {
  const [dl] = await Promise.all([page.waitForEvent("download", { timeout: cfg.deadline }).catch(() => null), link.click()]);
  out.download = await dlResult(dl);
}
// the PDF mention's own tab: a Ctrl-click on its card opens the capped /file URL in a new tab
const pdfCard = await page.$("#content .path-full.pdf");
out.pdfCard = !!pdfCard;
if (pdfCard) {
  const popup = ctx.waitForEvent("page", { timeout: cfg.deadline });
  await pdfCard.click({ modifiers: ["Control"] });
  const tab = await popup.catch(() => null);
  out.ownTab = !!tab;
  if (tab) {
    // the tab's own navigation, read off the context's /file log (headless Chromium may hand a PDF to its download path,
    // which leaves the tab's address blank; the request and its status are what the tab asked the kernel for)
    await tab.waitForLoadState("domcontentloaded").catch(() => {});
    await page.waitForFunction(() => true, null, { timeout: 500 }).catch(() => {});
    for (let i = 0; i < 50 && !files.some((f) => f.kind === "document"); i++) await page.waitForTimeout(100);
    const docs = files.filter((f) => f.kind === "document");
    out.ownTabUrlCap = docs.length > 0 && docs.every((f) => f.cap);
    await tab.close().catch(() => {});
  }
}
// the PDF mention's hover card: its first page in an iframe of the capped /file URL
await page.hover('#content .file-uri-link[data-path="docs/paper.pdf"]').catch(() => {});
await page.waitForFunction(() => !!document.querySelector("#file-preview-pop iframe.fp-pdf"), null, { timeout: cfg.deadline }).catch(() => {});
out.pdfFrameCap = await page.evaluate(() => { const f = document.querySelector("#file-preview-pop iframe.fp-pdf"); if (!f) return null; try { return new URL(f.getAttribute("src") || "", location.href).searchParams.has("cap"); } catch (e) { return "unparsable: " + (f.getAttribute("src") || "").slice(0, 12); } });
for (let i = 0; i < 50 && !files.some((f) => f.iframe && f.ext === ".pdf"); i++) await page.waitForTimeout(100);
await page.mouse.move(900, 720); await page.keyboard.press("Escape"); await page.waitForTimeout(300);
// the viewer: the note's relative figure rewritten through fileUrl, and its Download button
await page.click('#content .file-uri-link[data-path="docs/note.md"]');
await page.waitForSelector("#romp-fileview", { timeout: cfg.deadline });
await page.waitForFunction(() => { const i = document.querySelector('#romp-fileview img[alt="note figure"]'); return !!i && i.complete; }, null, { timeout: cfg.deadline }).catch(() => {});
out.viewerFigure = await page.evaluate(() => { const i = document.querySelector('#romp-fileview img[alt="note figure"]'); if (!i) return null; let cap = false; try { cap = new URL(i.getAttribute("src") || "", location.href).searchParams.has("cap"); } catch (e) { cap = false; } return { natural: i.naturalWidth, cap }; });
const dlBtn = await page.$('#romp-fileview button[aria-label="Download"]');
if (dlBtn) {
  const [dl2] = await Promise.all([page.waitForEvent("download", { timeout: cfg.deadline }).catch(() => null), dlBtn.click()]);
  out.viewerDownload = await dlResult(dl2);
}
// a link inside the shown note, Ctrl-clicked: the .svg in its own tab, off the capped /file URL
const svgLink = await page.$('#romp-fileview .fileview-md a:text-is("the diagram")');
out.svgLink = !!svgLink;
if (svgLink) {
  const popup = ctx.waitForEvent("page", { timeout: cfg.deadline });
  await svgLink.click({ modifiers: ["Control"] });
  const tab = await popup.catch(() => null);
  out.svgTab = !!tab;
  for (let i = 0; i < 50 && !files.some((f) => f.kind === "document" && f.ext === ".svg"); i++) await page.waitForTimeout(100);
  if (tab) await tab.close().catch(() => {});
}
await page.waitForTimeout(300);
out.sockets = sockets.length;
out.socketsCarryKey = sockets.every((u) => new URL(u).searchParams.get("k") === key);
out.files = files;
fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
await browser.close();
process.exit(0);
"""

STALE_KEY = HEAD + r"""
// two browsers sign in; the second's key goes into the first's slot: the cookie of one sign-in beside the key of the other
const a = await browser.newContext(VIEW), b = await browser.newContext(VIEW);
const pa = await a.newPage(), pb = await b.newPage();
for (const p of [pa, pb]) { await p.goto(cfg.origin + "/chat?token=" + encodeURIComponent(cfg.token)); await p.waitForSelector('#tabs .tab[data-id="' + cfg.sid + '"]', { timeout: cfg.deadline }); }
const slotA = await slotOf(a), slotB = await slotOf(b);
out.sameSlotName = slotA === slotB && slotA !== "";
const keyB = await pb.evaluate((s) => localStorage.getItem(s) || "", slotB);
const keyA = await pa.evaluate((s) => localStorage.getItem(s) || "", slotA);
out.keysDiffer = keyA !== keyB && keyA !== "" && keyB !== "";
out.inStep = await status(pa, "/sessions");
// (a) the top frame's own refused fetch
await pa.evaluate(([s, k]) => localStorage.setItem(s, k), [slotA, keyB]);
const topStatus = pa.evaluate(async () => (await fetch("/sessions")).status).catch(() => "navigated");
out.topHop = await waitLogin(pa);
out.topRefused = await topStatus;
out.topKeyDropped = (await pa.evaluate((s) => localStorage.getItem(s), slotA)) === null;
// signing in again through the /login form brings the page back
await pa.fill("#t", cfg.token);
await pa.click("form button");
await pa.waitForURL((u) => new URL(u).pathname === "/", { timeout: cfg.deadline }).catch(() => {});
await pa.waitForTimeout(500);
out.reSignInPath = new URL(pa.url()).pathname;
out.reSignInAddressClean = !/[?&](token|c)=/.test(pa.url());
out.reSignIn = await status(pa, "/sessions");
out.reSignInKeptSession = (await sessionCookie(a)).length === 1;
// (b) a PANE's refused fetch hops the top frame: a same-origin top document with no page-key script of its own (served
// by the harness, never by the kernel) holds the real /chat page in a frame
await pa.route("**/probe-top", (r) => r.fulfill({ status: 200, contentType: "text/html", body: "<!doctype html><title>top</title><iframe id=f src=/chat style=width:900px;height:600px></iframe>" }));
await pa.goto(cfg.origin + "/probe-top");
const frame = await (await pa.waitForSelector("#f")).contentFrame();
await frame.waitForSelector('#tabs .tab[data-id="' + cfg.sid + '"]', { timeout: cfg.deadline });
out.paneInStep = await frame.evaluate(async () => (await fetch("/sessions")).status);
await frame.evaluate(([s, k]) => localStorage.setItem(s, k), [slotA, keyB]);
frame.evaluate(() => fetch("/sessions")).catch(() => {});
out.paneHop = await waitLogin(pa);
out.paneKeyDropped = (await pa.evaluate((s) => localStorage.getItem(s), slotA)) === null;
// (c) no key at all: the top frame goes to /login as the page loads
await pa.goto(cfg.origin + "/login");
await pa.fill("#t", cfg.token); await pa.click("form button");
await pa.waitForURL((u) => new URL(u).pathname === "/", { timeout: cfg.deadline }).catch(() => {});
await pa.evaluate((s) => localStorage.removeItem(s), slotA);
await pa.goto(cfg.origin + "/chat");
out.noKeyHop = await waitLogin(pa);
fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
await browser.close();
process.exit(0);
"""

RACE = HEAD + r"""
// two tabs of ONE browser sign in at the same moment: each mints a session, the jar keeps the cookie of whichever response
// landed last and the slot keeps the key of whichever page ran last. Whatever order the race took, each tab must end
// signed in (a fetch reads /sessions) or on /login; never on a page whose every request is refused.
const runs = [];
for (let i = 0; i < cfg.rounds; i++) {
  const ctx = await browser.newContext(VIEW);
  const p1 = await ctx.newPage(), p2 = await ctx.newPage();
  const url = cfg.origin + "/chat?token=" + encodeURIComponent(cfg.token);
  await Promise.all([p1.goto(url), p2.goto(url)]);
  await Promise.all([p1, p2].map((p) => p.waitForSelector('#tabs .tab[data-id="' + cfg.sid + '"]', { timeout: cfg.deadline }).catch(() => {})));
  const ends = [];
  for (const p of [p1, p2]) {
    let st = onLogin(p) ? "login" : await p.evaluate(async () => (await fetch("/sessions")).status).catch(() => "navigated");
    if (st !== 200 && st !== "login") st = (await waitLogin(p)) ? "login" : st;
    ends.push(st);
  }
  runs.push(ends);
  await ctx.close();
}
out.runs = runs;
fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
await browser.close();
process.exit(0);
"""


class ServedFileCapsAndPageKey(unittest.TestCase):
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
        cls.lab = tempfile.mkdtemp(prefix="file-caps-")
        dist = os.path.join(cls.lab, "dist")
        lab_dist.copy_dist(dist)   # the checkout's ONE build of the bundles, copied under its lock (tests/lab_dist.py)
        state = os.path.join(cls.lab, "xdg", "romp")
        cwd = os.path.join(cls.lab, "proj")
        for d in ("names", "sdk", "states"):
            os.makedirs(os.path.join(state, d), exist_ok=True)
        for d in ("docs", "plots"):
            os.makedirs(os.path.join(cwd, d), exist_ok=True)
        cls.png = _png()
        Path(cwd, "plots", "figure.png").write_bytes(cls.png)
        Path(cwd, "docs", "paper.pdf").write_bytes(_pdf())
        Path(cwd, "plots", "diagram.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"><rect width="4" height="4" fill="#3c78c8"/></svg>\n')
        cls.note = ("# Note\n\nThe notes-api latency plot:\n\n![note figure](../plots/figure.png)\n\n"
                    "And [the diagram](../plots/diagram.svg).\n").encode()
        Path(cwd, "docs", "note.md").write_bytes(cls.note)
        fig = os.path.join(cwd, "plots", "figure.png")
        Path(state, "names", SID).write_text("web\t%s\t#9cd2ff\t#0c1a2e\n" % cwd)
        Path(state, "sdk", SID + ".json").write_text(json.dumps(
            {"sid": SID, "name": "web", "cwd": cwd, "mode": "auto", "effort": "high", "lastSid": SID, "alive": True,
             "model": "claude-opus-5", "liveModel": "Opus 5"}))
        claude = os.path.join(cls.lab, "claude")
        proj = os.path.join(claude, "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(cwd)))
        os.makedirs(proj, exist_ok=True)
        q = "path=%s&sid=%s" % (urllib.request.quote(fig, safe=""), SID)
        reply = ("The latency plot is at plots/figure.png, the write-up at docs/paper.pdf and the notes at docs/note.md.\n\n"
                 "![authored figure](/file?%s)\n\n[the plot as a file](/file?%s&download=1)\n" % (q, q))
        Path(proj, SID + ".jsonl").write_text(
            json.dumps({"type": "user", "uuid": U_UUID, "parentUuid": None, "timestamp": "2026-09-05T00:00:00.000Z", "sessionId": SID,
                        "message": {"role": "user", "content": "Where is the notes-api latency plot?"}}) + "\n" +
            json.dumps({"type": "assistant", "uuid": A_UUID, "parentUuid": U_UUID, "timestamp": "2026-09-05T00:00:05.000Z", "sessionId": SID,
                        "message": {"role": "assistant", "model": "claude-opus-5", "content": [{"type": "text", "text": reply}], "stop_reason": "end_turn"}}) + "\n")
        cls.port, cls.token = _free_port(), secrets.token_urlsafe(24)   # minted at run time, never printed
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

    def _klog_tail(self):
        """The kernel log's tail for a failure message, with the lab token masked (it never appears there; belt)."""
        try:
            return open(self.klog).read()[-1500:].replace(self.token, "<token>")
        except OSError:
            return ""

    def _drive(self, src, **extra):
        cfg = os.path.join(self.lab, "cfg.json")
        with open(cfg, "w") as f:
            json.dump(dict({"origin": "http://127.0.0.1:%d" % self.port, "token": self.token, "sid": SID, "deadline": 30000}, **extra), f)
        driver = os.path.join(self.lab, "driver.mjs")
        with open(driver, "w") as f:
            f.write(src)
        p = subprocess.run(["node", driver], capture_output=True, text=True, timeout=300,
                           env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg))
        os.unlink(cfg)
        if p.returncode == 3:
            raise unittest.SkipTest("no playwright browser on this box: the served lab needs one; CI's extension job installs Chromium and requires this file to run")
        mask = lambda s: s.replace(self.token, "<token>")
        self.assertEqual(p.returncode, 0, "driver failed:\n" + mask(p.stdout[-3000:] + p.stderr[-3000:]) + "\nkernel:\n" + self._klog_tail())
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
        self.assertIsNotNone(line, "driver printed no result:\n" + mask(p.stdout[-3000:]))
        self.assertNotIn(self.token, line, "the driver's report carries no credential")
        if os.environ.get("FILE_CAPS_REPORT"):     # a directory: each scene's report (booleans, statuses, lengths) for the record
            with open(os.path.join(os.environ["FILE_CAPS_REPORT"], self._testMethodName + ".json"), "w") as f:
                f.write(line[len("RESULT:"):] + "\n")
        return json.loads(line[len("RESULT:"):])

    def test_a_signed_in_page_loads_its_images_files_downloads_and_sockets(self):
        r = self._drive(SIGNED_IN)
        self.assertTrue(r["addressClean"], "the address keeps no token= once the page runs")
        self.assertEqual(r["sessionCookies"], 1, "one session cookie, named for this kernel")
        self.assertFalse(r["legacyCookie"], "the legacy token cookie is never set")
        self.assertFalse(r["cookieIsToken"], "the session cookie is not the serve token")
        self.assertTrue(r["cookieHttpOnly"], "the session cookie is HttpOnly")
        self.assertEqual(r["slots"], 1, "one page-key slot in this origin's storage")
        self.assertTrue(r["slotIsPerKernel"], "the slot is keyed by this kernel's cookie name")
        self.assertGreater(r["keyLen"], 20, "the login seeded the page key")
        self.assertFalse(r["keyIsToken"], "the page key is not the serve token")
        self.assertEqual(r["sessions"], 200, "a same-origin fetch carries the key through the wrapper")
        self.assertGreaterEqual(r["sockets"], 1, "the page dialed its socket")
        self.assertTrue(r["socketsCarryKey"], "every socket the page dialed carries k= equal to the stored key")
        self.assertEqual(r["authored"]["path"], "/file")
        self.assertTrue(r["authored"]["cap"], "the message's authored /file image carries this page's cap")
        self.assertGreater(r["authored"]["natural"], 0, "and it loads")
        self.assertTrue(r["inline"], "the mentioned figure rendered an inline preview")
        self.assertTrue(all(i["cap"] and i["natural"] > 0 for i in r["inline"]), "the inline preview loads through its capped fileUrl: %r" % r["inline"])
        self.assertTrue(r["linkCap"], "the authored download link carries the cap")
        self.assertIsNone(r["download"]["failure"], "the authored download link downloads")
        self.assertEqual(r["download"]["size"], len(self.png), "the downloaded bytes are the file's")
        self.assertTrue(r["pdfCard"], "the PDF mention rendered its card")
        self.assertTrue(r.get("ownTab"), "a Ctrl-click on the PDF card opened its own tab")
        self.assertTrue(r.get("ownTabUrlCap"), "the own tab's address is the capped /file URL")
        self.assertIsNotNone(r["viewerFigure"], "the viewer rendered the note's figure")
        self.assertTrue(r["viewerFigure"]["cap"] and r["viewerFigure"]["natural"] > 0, "the viewer's rewritten figure loads, capped: %r" % r["viewerFigure"])
        self.assertIsNone(r["viewerDownload"]["failure"], "the viewer's Download button downloads the shown note")
        self.assertEqual(r["viewerDownload"]["size"], len(self.note), "the note's bytes")
        files = r["files"]
        self.assertTrue(files, "the page made /file requests")
        self.assertEqual([f for f in files if f["status"] >= 400], [], "no /file request the page made was refused: %r" % files)
        header_less = [f for f in files if f["kind"] in ("image", "document") or f["download"]]
        self.assertTrue(header_less, "the header-less loads were seen: %r" % files)
        self.assertTrue(all(f["cap"] for f in header_less), "every header-less /file load carried a cap: %r" % files)
        self.assertTrue(any(f["kind"] == "document" and not f["iframe"] and f["ext"] == ".pdf" for f in files), "the PDF's own tab reached /file: %r" % files)
        self.assertTrue(r["pdfFrameCap"], "the PDF hover card's iframe URL carries the cap")
        self.assertTrue(any(f["iframe"] and f["ext"] == ".pdf" and f["status"] == 200 for f in files), "the PDF frame loaded: %r" % files)
        self.assertTrue(r["svgLink"] and r["svgTab"], "a Ctrl-click on the note's .svg link opened its own tab")
        self.assertTrue(any(f["kind"] == "document" and f["ext"] == ".svg" and f["status"] == 200 and f["cap"] for f in files), "the .svg's own tab loaded its capped /file URL: %r" % files)

    def test_a_stale_key_hops_to_login_from_the_top_or_a_pane_and_signing_in_again_recovers(self):
        r = self._drive(STALE_KEY)
        self.assertTrue(r["sameSlotName"], "two browsers of one kernel use the same slot name")
        self.assertTrue(r["keysDiffer"], "each sign-in has its own key")
        self.assertEqual(r["inStep"], 200)
        self.assertTrue(r["topHop"], "the top frame's refused fetch sent it to /login")
        self.assertTrue(r["topKeyDropped"], "and dropped the stale key")
        self.assertEqual(r["reSignInPath"], "/", "the /login form signs in and lands the dashboard")
        self.assertTrue(r["reSignInAddressClean"], "with no token= left in the address")
        self.assertEqual(r["reSignIn"], 200, "signed in again, the page's fetches pass")
        self.assertTrue(r["reSignInKeptSession"])
        self.assertEqual(r["paneInStep"], 200)
        self.assertTrue(r["paneHop"], "a pane's refused fetch sends the TOP frame to /login")
        self.assertTrue(r["paneKeyDropped"], "and drops the stale key")
        self.assertTrue(r["noKeyHop"], "a page with no key goes to /login as it loads")

    def test_two_concurrent_sign_ins_never_leave_a_silent_dead_page(self):
        r = self._drive(RACE, rounds=4)
        self.assertEqual(len(r["runs"]), 4)
        for ends in r["runs"]:
            for end in ends:
                self.assertIn(end, (200, "login"), "each tab ends signed in or on /login, never refused in place: %r" % r["runs"])


if __name__ == "__main__":
    unittest.main()
