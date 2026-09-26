#!/usr/bin/env python3
"""The whole dashboard, signed in, in a real browser: every pane loads its data over the page key, and a tab whose key
fell out of step with its sign-in is refused and comes back through the sign-in page.

The browser's login cookie holds a session id that opens the page documents and the static bundles. A JSON read, a POST or
a socket also needs the page key, which the login seeded into this origin's storage: the page-key script (kernel.py
_PAGE_KEY_JS, first in every page's head) wraps window.fetch so a request to this origin carries it as X-Romp-Key, and
the socket dials append it as k=. This lab serves the REAL dashboard from a hermetic kernel and drives it in playwright's
browser (Chromium by default; PAGE_KEY_DASHBOARD_ENGINE=firefox or webkit runs the same scenes on another engine, and
fails, never skips, when that engine is missing):

  1. The dashboard boots from `/?token=` and every pane loads its data: the chat's session tab, the Outline's session, the
     Feed's session, the Waiting pane's open request, the timeline's lane, a note opened into the Files pane (its figure
     too), and the settings page's model lists. Every fetch any frame makes to the kernel carries X-Romp-Key equal to the
     stored key, every socket carries k= equal to it and hears from the kernel, no request is refused, and no page makes an
     XMLHttpRequest or an EventSource. The notification switch's POST, clicked in the bell's menu, is answered 200, and the
     kernel holds the new state.
  2. The wrapper keys every request form the Fetch API takes (a string, a URL, a Request with its own headers, a Request
     with init headers, init headers as an object, as pairs and as a Headers, a body), keeps the site's own headers the way
     the browser's fetch would, and leaves a request to another origin as it was: that origin sees no page key and no
     preflight asking to send one.
  3. A stale tab: the dashboard is open and the key in its storage changes to another sign-in's (the state two racing
     sign-ins can leave). Its next request, a POST, is refused with the re-sign-in 403 and changes nothing; the tab goes to
     /login and drops the stale key; signing in through the form brings the dashboard back, with every pane loading and the
     POST answered again. The same tab on an origin whose storage is full, filled until the storage probe's own write no
     longer fits, does the same: the re-sign-in branch drops the stale key before it probes, the probe's write fits in the
     room the key left, the tab goes to /login with no storage-refused sentence, and signing in through the form seeds the
     key again and the dashboard's requests are answered, with the rest of the storage still full.
  4. A browser that keeps cookies but refuses site storage (Firefox with dom.storage.enabled off; on the other engines an
     init script that makes localStorage throw) signs in through the /login form: the boot's requests come back with the
     re-sign-in 403, and the tab stays on the dashboard's address showing the sentence that says why, with no hop back to
     /login once they have come back. A pane that finds storage refused while the top frame does not writes the sentence
     into the top frame's document, and nothing navigates.
  5. That sentence is legible on every top-level page it can land on (every page route the kernel's table names: the
     dashboard and each pane page opened on its own): a contrast of at least 4.5:1, measured twice, from the computed
     styles and from the pixels of a screenshot, and set in from the window's edge.
  6. /login on a phone-sized screen (320x568 and 375x667) shows its default view with nothing to scroll: the sentence,
     the form and the pointer to `romp url`, with every fold closed; a click on a fold's summary opens it with the page's
     scripts turned off.

Nothing here prints a token, a session id or a key: the driver compares them in memory and reports booleans, statuses and
counts. The lab token is minted at run time. Skips LOUDLY without the extension deps or a Chromium; the CI extension job
installs Chromium and runs served files with ROMP_SERVED_TESTS_REQUIRE=1, which turns any skip into a failure there.
SYNTHETIC fixtures only (session web, the notes-api demo world, placeholder uuids)."""
import ast
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
import threading
import time
import unittest
import urllib.request
import zlib
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import lab_dist

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
EXT = os.path.join(ROOT, "vscode-extension")
sys.path.insert(0, HERE)
import test_ship_reship_served as _lab   # noqa: E402  the lab kernel's environment (the module, not its classes)

SID = "bbbbbbbb-1111-2222-3333-444444444444"
U_UUID = "11111111-2222-3333-4444-555555555555"
A_UUID = "22222222-3333-4444-5555-666666666666"
ENGINE = os.environ.get("PAGE_KEY_DASHBOARD_ENGINE") or "chromium"


def _png(w=2, h=2, rgb=(60, 120, 200)):
    """A tiny valid PNG (RGB, no filter) without a binary fixture."""
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def _png_rgb(path):
    """The pixels of an 8-bit RGB or RGBA non-interlaced PNG (the form a playwright screenshot takes), as rows of (r, g, b)."""
    data = Path(path).read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "a PNG"
    pos, idat, head = 8, b"", None
    while pos < len(data):
        n, tag = struct.unpack(">I", data[pos:pos + 4])[0], data[pos + 4:pos + 8]
        if tag == b"IHDR":
            head = struct.unpack(">IIBBBBB", data[pos + 8:pos + 8 + n])
        elif tag == b"IDAT":
            idat += data[pos + 8:pos + 8 + n]
        elif tag == b"IEND":
            break
        pos += 12 + n
    w, h, depth, ctype, _, _, interlace = head
    assert depth == 8 and ctype in (2, 6) and interlace == 0, "an 8-bit RGB or RGBA PNG, not interlaced: %r" % (head,)
    bpp = 3 if ctype == 2 else 4
    raw, stride, rows, prev, i = zlib.decompress(idat), w * bpp, [], bytearray(w * bpp), 0
    for _ in range(h):
        ft, line = raw[i], bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b, c = prev[x], (prev[x - bpp] if x >= bpp else 0)
            if ft == 1:
                line[x] = (line[x] + a) & 255
            elif ft == 2:
                line[x] = (line[x] + b) & 255
            elif ft == 3:
                line[x] = (line[x] + ((a + b) >> 1)) & 255
            elif ft == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append([tuple(line[x:x + 3]) for x in range(0, stride, bpp)])
        prev = line
    return rows


def _rgb(css):
    """(r, g, b) of a computed CSS colour: rgb()/rgba(), or color(srgb ...)."""
    m = re.search(r"color\(srgb ([\d.]+) ([\d.]+) ([\d.]+)", css or "")
    if m:
        return tuple(255 * float(m.group(k)) for k in (1, 2, 3))
    return tuple(float(x) for x in re.findall(r"\d+(?:\.\d+)?", css or "")[:3])


def _ratio(a, b):
    """The WCAG contrast ratio of two sRGB colours, each (r, g, b) in 0 to 255."""
    def lum(c):
        ch = [v / 255 for v in c]
        ch = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in ch]
        return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _pixel_contrast(path):
    """The contrast a screenshot of text measures: between its commonest colour (the ground behind the text) and the pixel
    farthest from it in contrast (the ink at the core of a stroke)."""
    counts = Counter(px for row in _png_rgb(path) for px in row)
    ground = counts.most_common(1)[0][0]
    ink = max(counts, key=lambda px: _ratio(px, ground))
    return _ratio(ink, ground)


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class _OtherOrigin(BaseHTTPRequestHandler):
    """Another origin: records the NAMES of the headers each request brings (never a value), answers CORS-open."""
    seen = []

    def log_message(self, *a):
        pass

    def _answer(self):
        names = sorted(k.lower() for k in self.headers.keys())
        asked = [h.strip().lower() for h in (self.headers.get("Access-Control-Request-Headers") or "").split(",") if h.strip()]
        type(self).seen.append({"method": self.command, "path": self.path.split("?")[0], "names": names, "asked": asked})
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"ok")

    do_GET = do_POST = do_OPTIONS = _answer


# The shared head of every driver: the browser, the config, and the helpers each scene uses. A driver reports one RESULT
# line of booleans, statuses and counts; no credential value leaves the browser or this process.
HEAD = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const pw = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
let browser;
try { browser = await pw[cfg.engine].launch(); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const VIEW = { viewport: { width: 1600, height: 1000 } };
const out = {};
const pathOf = (u) => { try { return new URL(u).pathname; } catch (e) { return "?"; } };
/** p, or "timeout" after ms: a step that waits on the page is bounded, so a scene reports what it saw rather than hanging. */
const bounded = (p, ms) => Promise.race([p, new Promise((r) => setTimeout(() => r("timeout"), ms))]);
const onKernel = (u) => { try { return new URL(u).origin === cfg.origin; } catch (e) { return false; } };
const sessionCookies = async (ctx) => (await ctx.cookies(cfg.origin)).filter((c) => c.name.startsWith("romp_s_"));
const slotOf = async (ctx) => { const s = await sessionCookies(ctx); return s.length === 1 ? "romp.pageKey." + s[0].name : ""; };
const keyIn = (page, slot) => page.evaluate((s) => localStorage.getItem(s), slot);
// the Files control on, as the gear's setting would have it, so a file link routes into the Files pane
const filesControl = (ctx) => ctx.addInitScript(() => { try { if (!localStorage.getItem("romp:settings")) localStorage.setItem("romp:settings", JSON.stringify({ showFilesControl: true })); } catch (e) {} });
/** Every request a context makes to the kernel: its path, kind, method and frame; its X-Romp-Key (held here, in memory
 *  only: a report names it through `label`, never by value); its status and whether a refusal carried the re-sign-in
 *  marker. */
function recorder(ctx, label) {
  const log = [], pending = [];
  ctx.on("request", (rq) => { if (!onKernel(rq.url())) return; const t = Date.now(); pending.push((async () => {
    const h = await rq.allHeaders().catch(() => ({}));
    let frame = "(none)"; try { frame = pathOf(rq.frame().url()); } catch (e) { frame = "(worker)"; }
    const resp = await rq.response().catch(() => null);
    const rh = resp ? await resp.allHeaders().catch(() => ({})) : {};
    const kv = h["x-romp-key"];
    log.push({ path: pathOf(rq.url()), type: rq.resourceType(), method: rq.method(), frame, get key() { return label(kv); },
               status: resp ? resp.status() : null, reauth: !!rh["x-romp-reauth"], t });
  })()); });
  return { log, settle: () => Promise.all(pending) };
}
/** Every socket a page dials: its route and app, its k= (named through `label`, like the recorder's key), when it was
 *  dialed, and how many frames the kernel sent on it. */
function sockets(page, label) {
  const socks = [];
  page.on("websocket", (ws) => { let u; try { u = new URL(ws.url()); } catch (e) { return; }
    const kv = u.searchParams.get("k");
    const rec = { path: u.pathname, app: u.searchParams.get("app") || "", get key() { return label(kv); }, frames: 0, t: Date.now() };
    socks.push(rec); ws.on("framereceived", () => { rec.frames++; }); });
  return socks;
}
const frameAt = async (page, p) => { for (let i = 0; i < 300; i++) { const f = page.frames().find((f) => pathOf(f.url()) === p); if (f) return f; await page.waitForTimeout(100); } return null; };
const waitIn = (frame, fn, arg) => frame ? frame.waitForFunction(fn, arg, { timeout: cfg.deadline }).then(() => true, () => false) : Promise.resolve(false);
/** The dashboard's panes as its own rail lists them (each toggle's pane key and the word it wears), with the route each
 *  pane's frame loads, plus the settings page (the gear's frame, which is no pane). Read off the page, so a pane added to
 *  the rail is one this lab has to give a data check below. */
async function paneTable(page) {
  const rail = await page.evaluate(() => Array.from(document.querySelectorAll(".rail-btn[data-pane]")).map((b) => {
    const key = b.getAttribute("data-pane"), f = document.getElementById("f-" + key);
    return { key, label: (b.textContent || "").trim(), route: f ? (f.getAttribute("src") || f.getAttribute("data-src") || "") : "" }; }));
  const st = await page.evaluate(() => { const f = document.getElementById("f-settings"); return f ? (f.getAttribute("src") || f.getAttribute("data-src") || "") : ""; });
  return rail.concat([{ key: "settings", label: "Settings", route: st }]);
}
/** Each pane's proof that it loaded its data, by the word the rail gives it. Chat, Outline, Feed and Waiting name the
 *  session; Sessions (the timeline) draws its lane; Files shows the note a chat link opened into it, figure and all;
 *  Settings fills its model lists from /models. */
const LOADED = {
  Chat: (sid) => !!document.querySelector('#tabs .tab[data-id="' + sid + '"]'),
  Outline: (sid) => !!document.querySelector('.fl-head[data-sid="' + sid + '"]'),
  Feed: (sid) => !!document.querySelector('.feed-sess-head[data-fsid="' + sid + '"]'),
  Waiting: (sid) => !!document.querySelector('.wt-item[data-sid="' + sid + '"]'),
  Sessions: () => Array.from(document.querySelectorAll("svg text")).some((t) => t.textContent === "web"),
  Files: () => { const v = document.getElementById("romp-fileview"); const i = v && v.querySelector('img[alt="note figure"]');
    return !!v && /notes-api latency plot/.test(v.textContent || "") && !!i && i.complete && i.naturalWidth > 0; },
  Settings: () => { const s = document.getElementById("rs-judgemodel"); return !!s && s.options.length > 1; },
};
/** Close the settings modal the way the shell's Escape chain does (the settings frame's own __rompSettingsClose), until
 *  the shell's body drops settings-open, which lifts the frame over the whole window. The frame reports the modal's state
 *  by message, so one close can race a late "open" report: ask again until the class is gone. True when it is gone. */
async function closeSettings(page) {
  for (let i = 0; i < 40; i++) {
    if (!(await page.evaluate(() => document.body.classList.contains("settings-open")))) return true;
    await page.evaluate(() => { const f = document.getElementById("f-settings"); try { const w = f && f.contentWindow; if (w && w.__rompSettingsClose) w.__rompSettingsClose(); } catch (e) {} });
    await page.waitForTimeout(250);
  }
  return false;
}
/** Every pane on, then each one's data check: {label: true | false | "no check"}. The Files pane is checked after a chat
 *  file link opens a note into it; Settings is opened through the shell's own opener and closed again. */
async function panesLoaded(page, table) {
  const res = {};
  for (const p of table) if (p.key !== "settings") await page.evaluate((k) => window.__rompPaneToggle(k, true), p.key);
  const chat = await frameAt(page, (table.find((p) => p.label === "Chat") || {}).route);
  for (const p of table) {
    if (!LOADED[p.label]) { res[p.label] = "no check"; continue; }
    if (p.label === "Files" && chat) await chat.click('#content .file-uri-link[data-path="docs/note.md"]').catch(() => {});
    if (p.label === "Settings") await page.evaluate(() => window.__rompOpenSettings());
    const fr = await frameAt(page, p.route);
    res[p.label] = await waitIn(fr, LOADED[p.label], cfg.sid);
    if (p.label === "Settings") await closeSettings(page);
  }
  return res;
}
/** A frame's route as the pane word it belongs to ("shell" for the dashboard's own document). */
const wordOf = (table, route) => route === "/" ? "shell" : ((table.find((p) => p.route === route) || {}).label || route);
/** The notification switch's own POST, clicked the way a person does: the bell, then its main row. */
async function bellPost(page) {
  const settingsClosed = await closeSettings(page);   // the settings frame, lifted over the window while open, would take the click
  await page.click("#rail-bell");
  await page.waitForFunction(() => { const b = document.getElementById("rbell-back"); return !!b && !b.hidden; }, null, { timeout: cfg.deadline });
  const was = await page.evaluate(() => document.querySelector('#rbell-pop [data-act="all"]').getAttribute("aria-checked"));
  const resp = page.waitForResponse((r) => pathOf(r.url()) === "/notify-all" && r.request().method() === "POST", { timeout: cfg.deadline }).catch(() => null);
  await page.click('#rbell-pop [data-act="all"]');
  const r = await resp;
  const flipped = await page.waitForFunction((w) => document.querySelector('#rbell-pop [data-act="all"]').getAttribute("aria-checked") !== w, was, { timeout: cfg.deadline }).then(() => true, () => false);
  const readBack = await page.evaluate(async () => { const r = await fetch("/notify-all"); return r.ok ? (await r.json()).on : "HTTP " + r.status; });
  await page.keyboard.press("Escape").catch(() => {});
  return { status: r ? r.status() : null, flipped, held: readBack === (was !== "true"), settingsClosed };
}
/** A summary of a request log: the kernel-bound fetch/xhr requests by the key they carried, the refusals, and the kinds
 *  seen. */
function summary(log, from, table) {
  const rows = log.filter((r) => r.t >= (from || 0));
  const data = rows.filter((r) => r.type === "fetch" || r.type === "xhr" || r.type === "eventsource");
  const byKey = {}; for (const r of data) byKey[r.key] = (byKey[r.key] || 0) + 1;
  const frames = {}; for (const r of data) { const w = wordOf(table, r.frame); frames[w] = (frames[w] || 0) + 1; }
  return { data: data.length, byKey, frames, xhr: rows.filter((r) => r.type === "xhr" || r.type === "eventsource").length,
           refused: rows.filter((r) => r.status === 403).map((r) => r.frame + " " + r.method + " " + r.path + " key=" + r.key),
           unkeyed: data.filter((r) => r.key !== "mine").map((r) => r.frame + " " + r.method + " " + r.path + " key=" + r.key + " " + r.status) };
}
"""

DASHBOARD = HEAD + r"""
const ctx = await browser.newContext(VIEW);
await filesControl(ctx);
let mine = "";
const label = (k) => k === undefined || k === null ? "none" : (mine && k === mine ? "mine" : "other");
const rec = recorder(ctx, label);
const page = await ctx.newPage();
const socks = sockets(page, label);
await page.goto(cfg.origin + "/?token=" + encodeURIComponent(cfg.token));
await page.waitForFunction(() => !!window.__rompPaneToggle, null, { timeout: cfg.deadline });
const slot = await slotOf(ctx);
mine = (await keyIn(page, slot)) || "";
out.keyLen = mine.length;
out.keyIsToken = mine === cfg.token;
out.addressClean = !/[?&](token|c)=/.test(page.url());
const table = await paneTable(page);
out.panes = await panesLoaded(page, table);
out.documents = Array.from(new Set(page.frames().map((f) => wordOf(table, pathOf(f.url()))))).sort();
out.post = await bellPost(page);
await page.waitForTimeout(1500);   // the panes' own polls after the POST
await rec.settle();
out.requests = summary(rec.log, 0, table);
const appWord = (a) => a === "shell" ? "shell" : ((table.find((p) => p.key === a) || {}).label || a);
out.sockets = socks.map((s) => ({ pane: appWord(s.app), path: s.path, key: s.key, heard: s.frames > 0 }));
fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
await browser.close();
process.exit(0);
"""

FORMS = HEAD + r"""
const ctx = await browser.newContext(VIEW);
let mine = "";
const label = (k) => k === undefined || k === null ? "none" : (mine && k === mine ? "mine" : "other");
const seen = {};   // the headers each probe's request carried, by probe number: names only, and which key
ctx.on("request", async (rq) => { let u; try { u = new URL(rq.url()); } catch (e) { return; } const n = u.searchParams.get("probe"); if (!n || u.origin !== cfg.origin) return;
  const h = await rq.allHeaders().catch(() => ({})); seen[n] = { key: label(h["x-romp-key"]), probe: h["x-probe"] || null, probeInit: h["x-probe-init"] || null, method: rq.method() }; });
const page = await ctx.newPage();
await page.goto(cfg.origin + "/chat?token=" + encodeURIComponent(cfg.token));
await page.waitForSelector('#tabs .tab[data-id="' + cfg.sid + '"]', { timeout: cfg.deadline });
mine = (await keyIn(page, await slotOf(ctx))) || "";
out.keyLen = mine.length;
out.status = await page.evaluate(async (other) => {
  const s = async (p) => { try { return (await p).status; } catch (e) { return "threw " + String(e).slice(0, 60); } };
  return {
    string: await s(fetch("/sessions?probe=1")),
    url: await s(fetch(new URL("/sessions?probe=2", location.href))),
    absolute: await s(fetch(location.origin + "/sessions?probe=3")),
    request: await s(fetch(new Request("/sessions?probe=4", { headers: { "X-Probe": "r" } }))),
    requestInit: await s(fetch(new Request("/sessions?probe=5", { headers: { "X-Probe": "r" } }), { headers: { "X-Probe-Init": "i" } })),
    object: await s(fetch("/sessions?probe=6", { headers: { "X-Probe": "o" } })),
    pairs: await s(fetch("/sessions?probe=7", { headers: [["X-Probe", "p"]] })),
    headers: await s(fetch("/sessions?probe=8", { headers: new Headers({ "X-Probe": "h" }) })),
    initNoHeaders: await s(fetch("/sessions?probe=9", { cache: "no-store" })),
    requestInitNoHeaders: await s(fetch(new Request("/sessions?probe=10", { headers: { "X-Probe": "r" } }), { cache: "no-store" })),
    post: await s(fetch("/notify-turns?probe=11", { method: "POST", body: JSON.stringify({ on: false }) })),
    postRequest: await s(fetch(new Request("/notify-turns?probe=12", { method: "POST", body: JSON.stringify({ on: false }) }))),
    other: await s(fetch(other + "/elsewhere?probe=13")),
    otherHeaders: await s(fetch(other + "/elsewhere?probe=14", { headers: { "X-Probe": "x" } })),
    otherRequest: await s(fetch(new Request(other + "/elsewhere?probe=15"))),
  };
}, cfg.other);
await page.waitForTimeout(500);
out.seen = seen;
fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
await browser.close();
process.exit(0);
"""

STALE = HEAD + r"""
// browser A holds the dashboard; browser B signs in on its own, and B's key is what A's storage ends up holding
const a = await browser.newContext(VIEW), b = await browser.newContext(VIEW);
await filesControl(a);
let keyA = "", keyB = "";
const label = (k) => k === undefined || k === null ? "none" : (k === keyA ? "mine" : (k === keyB ? "theirs" : "other"));
const rec = recorder(a, label);
const pa = await a.newPage(), pb = await b.newPage();
const socks = sockets(pa, label);
await pa.goto(cfg.origin + "/?token=" + encodeURIComponent(cfg.token));
await pa.waitForFunction(() => !!window.__rompPaneToggle, null, { timeout: cfg.deadline });
const slotA = await slotOf(a);
keyA = (await keyIn(pa, slotA)) || "";
const table = await paneTable(pa);
out.before = await panesLoaded(pa, table);
await pb.goto(cfg.origin + "/chat?token=" + encodeURIComponent(cfg.token));
await pb.waitForSelector('#tabs .tab[data-id="' + cfg.sid + '"]', { timeout: cfg.deadline });
keyB = (await keyIn(pb, await slotOf(b))) || "";
out.keysDiffer = keyA !== "" && keyB !== "" && keyA !== keyB;
out.sameSlot = slotA === (await slotOf(b)) && slotA !== "";
out.switchBefore = await pb.evaluate(async () => (await (await fetch("/notify-all")).json()).on);
// the key changes under the open dashboard, and the tab's next request is a POST
await rec.settle();
const swapT = Date.now();
out.postStatus = await pa.evaluate(async ([s, k, want]) => { localStorage.setItem(s, k);
  const r = await fetch("/notify-all", { method: "POST", body: JSON.stringify({ on: want }) });
  return { status: r.status, reauth: !!r.headers.get("X-Romp-Reauth") }; }, [slotA, keyB, !out.switchBefore]).catch(() => "navigated");
out.hop = await pa.waitForURL((u) => new URL(u).pathname === "/login", { timeout: cfg.deadline }).then(() => true, () => false);
out.keyDropped = (await keyIn(pa, slotA)) === null;
await rec.settle();
const stale = rec.log.filter((r) => r.t >= swapT && r.key === "theirs");
out.stale = { count: stale.length, answered: stale.filter((r) => r.status !== 403).map((r) => r.frame + " " + r.method + " " + r.path + " " + r.status),
              unmarked: stale.filter((r) => r.status === 403 && !r.reauth).map((r) => r.frame + " " + r.method + " " + r.path),
              post: stale.filter((r) => r.method === "POST" && r.path === "/notify-all").map((r) => ({ status: r.status, reauth: r.reauth })) };
out.switchAfterRefusal = await pb.evaluate(async () => (await (await fetch("/notify-all")).json()).on);
// signing in again through the /login form brings the dashboard back
await pa.fill("#t", cfg.token);
const backT = Date.now();
await pa.click("form button");
out.backAt = await pa.waitForURL((u) => new URL(u).pathname === "/", { timeout: cfg.deadline }).then(() => pathOf(pa.url()), () => pathOf(pa.url()));
out.backAddressClean = !/[?&](token|c)=/.test(pa.url());
await pa.waitForFunction(() => !!window.__rompPaneToggle, null, { timeout: cfg.deadline }).catch(() => {});
out.keyBack = label((await keyIn(pa, slotA)) || undefined);
out.after = await panesLoaded(pa, await paneTable(pa));
out.post = await bellPost(pa);
await pa.waitForTimeout(1500);
await rec.settle();
out.afterRequests = summary(rec.log, backT, table);
out.afterSockets = socks.filter((s) => s.path === "/ws" && s.t >= backT).map((s) => ({ app: s.app, key: s.key, heard: s.frames > 0 }));
fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
await browser.close();
process.exit(0);
"""

# An origin whose storage is full: the dashboard is signed in, then, in one task of the page (so no response is handled in
# between), its key changes to another sign-in's of the same length, this origin's storage is filled in halving chunks until
# not one more character fits, and the storage probe's own write is tried and refused. A request with the stale key comes
# back with the re-sign-in 403. The state is read once the tab has gone to /login or shows the storage-refused sentence;
# then, from /login, the form signs in again. The fill stays in place throughout.
FULL_QUOTA = HEAD + r"""
const ctx = await browser.newContext(VIEW);
let mine = "", stale = "";
const label = (k) => k === undefined || k === null ? "none" : (mine && k === mine ? "mine" : (stale && k === stale ? "stale" : "other"));
const held = async (page, slot) => { const k = await keyIn(page, slot).catch(() => undefined); return k === undefined ? "unread" : (k === null ? "dropped" : label(k)); };
const says = (page) => page.evaluate(() => !!document.body && (document.body.innerText || "").includes("which this browser refuses")).catch(() => false);
const fillKept = (page, n) => page.evaluate((n) => { let c = 0; for (let i = 0; i < localStorage.length; i++) if (String(localStorage.key(i)).startsWith("romp.fill.")) c++; return c === n; }, n).catch(() => "unread");
const rec = recorder(ctx, label);
const page = await ctx.newPage();
const navs = [];
page.on("framenavigated", (f) => { if (f === page.mainFrame()) navs.push(pathOf(f.url())); });
await page.goto(cfg.origin + "/?token=" + encodeURIComponent(cfg.token));
await page.waitForFunction(() => !!window.__rompPaneToggle, null, { timeout: cfg.deadline });
const slot = await slotOf(ctx);
mine = (await keyIn(page, slot)) || "";
stale = Array.from(mine, (c) => c === "A" ? "B" : "A").join("");   // every character differs, the length is the same
out.keyLen = mine.length;
const t0 = Date.now();
out.fill = await page.evaluate(([s, v]) => {
  const was = localStorage.getItem(s);
  localStorage.setItem(s, v);
  let n = 0;
  for (let c = "x".repeat(1 << 20); c.length && n < 10000; ) { try { localStorage.setItem("romp.fill." + n, c); n++; } catch (e) { c = c.slice(0, c.length >> 1); } }
  let probe = "took";
  try { localStorage.setItem(s + ".probe", "1"); localStorage.removeItem(s + ".probe"); } catch (e) { probe = e.name; }
  return { items: n, probe, swapped: was !== v && localStorage.getItem(s) === v };
}, [slot, stale]);
out.request = await page.evaluate(async () => { const r = await fetch("/sessions"); return { status: r.status, reauth: !!r.headers.get("X-Romp-Reauth") }; })
  .catch(() => "navigated");
const decided = async () => pathOf(page.url()) === "/login" || (await says(page));
for (const end = Date.now() + cfg.deadline; Date.now() < end && !(await decided()); ) await page.waitForTimeout(200);
await page.waitForTimeout(2000);
out.refusals = rec.log.filter((r) => r.t >= t0 && r.status === 403 && r.reauth && r.key === "stale").length;
out.navs = navs.slice();
out.at = pathOf(page.url());
out.says = await says(page);
out.key = await held(page, slot);
out.fillKept = await fillKept(page, out.fill.items);
out.back = null;
if (out.at === "/login") {
  await page.fill("#t", cfg.token);
  await page.click("form button");
  const at = await page.waitForURL((u) => new URL(u).pathname === "/", { timeout: cfg.deadline }).then(() => pathOf(page.url()), () => pathOf(page.url()));
  await page.waitForFunction(() => !!window.__rompPaneToggle, null, { timeout: cfg.deadline }).catch(() => {});
  out.back = { at, key: await held(page, slot), answered: await page.evaluate(async () => (await fetch("/sessions")).status).catch(() => "navigated"),
               says: await says(page), fillKept: await fillKept(page, out.fill.items) };
}
fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
await browser.close();
process.exit(0);
"""

# A browser that keeps cookies but refuses site storage, and the storage-refused sentence as a page shows it. Firefox runs
# it for real, with dom.storage.enabled off; the other engines take an init script that makes localStorage throw the
# SecurityError a refusing browser throws.
REFUSING = r"""
let refusing = browser;
if (cfg.engine === "firefox") {
  await browser.close();
  try { browser = refusing = await pw.firefox.launch({ firefoxUserPrefs: { "dom.storage.enabled": false } }); }
  catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
}
async function refusingContext() {
  const ctx = await refusing.newContext(VIEW);
  if (cfg.engine !== "firefox") await ctx.addInitScript(() => { Object.defineProperty(window, "localStorage", { configurable: true,
    get() { throw new DOMException("The operation is insecure.", "SecurityError"); } }); });
  return ctx;
}
const storageRefused = (page) => page.evaluate(() => { try { localStorage.setItem("romp.probe", "1"); localStorage.removeItem("romp.probe"); return false; }
  catch (e) { return true; } }).catch(() => "unknown");
/** The sentence as the page shows it: whether the body says it, its ink and the first opaque background behind it (computed
 *  styles), the box its text fills, and a screenshot of that box (written to `shot`) for the pixel check. */
async function sentenceLook(page, shot) {
  const m = await bounded(page.evaluate(() => {
    const b = document.body;
    if (!b) return null;
    let ground = "";
    for (let el = b; el && !ground; el = el.parentElement) {
      const c = getComputedStyle(el).backgroundColor;
      if (c && c !== "transparent" && !/^rgba\([^)]*,\s*0\)$/.test(c)) ground = c;
    }
    const r = document.createRange(); r.selectNodeContents(b); const box = r.getBoundingClientRect();
    return { said: (b.innerText || "").includes("which this browser refuses"), ink: getComputedStyle(b).color, ground: ground || "rgb(255, 255, 255)",
             box: { x: box.x, y: box.y, width: box.width, height: box.height } };
  }).catch(() => null), 10000);
  if (m === "timeout") return null;
  if (m && m.said && m.box.width > 0 && m.box.height > 0) { await page.screenshot({ path: shot, clip: m.box }); m.shot = true; }
  return m;
}
"""

STORAGE_REFUSED = HEAD + REFUSING + r"""
const ctx = await refusingContext();
const rec = recorder(ctx, (k) => k === undefined || k === null ? "none" : "some");
const page = await ctx.newPage();
const navs = [];
page.on("framenavigated", (f) => { if (f === page.mainFrame()) navs.push(pathOf(f.url())); });
await page.goto(cfg.origin + "/login");
out.refused = await storageRefused(page);
await page.fill("#t", cfg.token);
const t0 = Date.now();
await page.click("form button");
await page.waitForURL((u) => new URL(u).pathname === "/", { timeout: cfg.deadline }).catch(() => {});
// the boot's requests: wait until a re-sign-in refusal has come back to the page, then give the page time to act on it
for (const end = Date.now() + cfg.deadline; Date.now() < end && !rec.log.some((r) => r.t >= t0 && r.reauth); ) await page.waitForTimeout(200);
await page.waitForTimeout(4000);
out.settled = (await bounded(rec.settle(), 10000)) !== "timeout";
out.reauth = rec.log.filter((r) => r.t >= t0 && r.reauth).length;
out.cookies = (await sessionCookies(ctx)).length;
out.navs = navs;
out.at = pathOf(page.url());
out.look = await sentenceLook(page, cfg.shots + "/after-sign-in.png");
fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
await browser.close();
process.exit(0);
"""

# A pane is refused while the top frame is not: the dashboard signs in with working storage, then the chat pane's document
# alone stops reaching this origin's storage (the init script's refusal, applied to that one frame), and the pane makes a
# request. The pane's re-sign-in branch finds storage refused and writes the sentence into the TOP frame's document; nothing
# navigates. The top frame's own load check never ran refused, so only the pane's branch can put the sentence there.
PANE_REFUSED = HEAD + r"""
const ctx = await browser.newContext(VIEW);
const rec = recorder(ctx, () => "n/a");
const page = await ctx.newPage();
const navs = [];
page.on("framenavigated", (f) => { if (f === page.mainFrame()) navs.push(pathOf(f.url())); });
await page.goto(cfg.origin + "/?token=" + encodeURIComponent(cfg.token));
await page.waitForFunction(() => !!window.__rompPaneToggle, null, { timeout: cfg.deadline });
const table = await paneTable(page);
const chatRoute = (table.find((p) => p.label === "Chat") || {}).route;
await page.evaluate((k) => window.__rompPaneToggle(k, true), (table.find((p) => p.label === "Chat") || {}).key);
const chat = await frameAt(page, chatRoute);
out.chat = !!chat;
out.topBefore = await page.evaluate(() => (document.body.innerText || "").includes("which this browser refuses"));
if (chat) {
  await chat.evaluate(() => Object.defineProperty(window, "localStorage", { configurable: true,
    get() { throw new DOMException("The operation is insecure.", "SecurityError"); } }));
  out.pane = await chat.evaluate(async () => { const r = await fetch("/sessions"); return { status: r.status, reauth: !!r.headers.get("X-Romp-Reauth") }; })
    .catch(() => "frame gone");
}
await page.waitForTimeout(2000);
out.settled = (await bounded(rec.settle(), 10000)) !== "timeout";
out.paneRefusals = rec.log.filter((r) => r.path === "/sessions" && r.frame === chatRoute && r.status === 403 && r.reauth).length;
out.navs = navs;
out.at = pathOf(page.url());
out.topSays = await bounded(page.evaluate(() => (document.body.innerText || "").includes("which this browser refuses")).catch(() => false), 10000);
fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
await browser.close();
process.exit(0);
"""

# The sentence as each page's own load check shows it, with the kernel's data requests held back, so no refusal reaches the
# page and the sentence stays whatever the re-sign-in branch does. It runs on every page route the kernel's table names
# (_PAGE_RENDERERS, read from kernel.py's source), since the page-key script runs in each of them and their stylesheets
# differ: the settings page's ground is light, so ink set without its own background reads at about 1.25:1 there.


def _sentence_pages():
    """Every page route in kernel.py's _PAGE_RENDERERS, the bare path aside (it classes as "/"), read by ast so the kernel
    is not imported. An empty or shellless table is an error, never a shorter list."""
    tree = ast.parse(Path(ROOT, "kernel", "kernel.py").read_text())
    tables = [n.value for n in tree.body if isinstance(n, ast.Assign) and isinstance(n.value, ast.Dict)
              and any(isinstance(t, ast.Name) and t.id == "_PAGE_RENDERERS" for t in n.targets)]
    assert len(tables) == 1, "kernel.py assigns _PAGE_RENDERERS once, as a dict literal: %d found" % len(tables)
    routes = [k.value for k in tables[0].keys if isinstance(k, ast.Constant) and isinstance(k.value, str) and k.value]
    assert len(routes) == len(tables[0].keys) - 1, "every key of _PAGE_RENDERERS but the bare path is a string route"
    assert "/" in routes and "/chat" in routes, "the table names the shell and the chat page: %r" % routes
    return routes


SENTENCE = HEAD + REFUSING + r"""
out.pages = {};
for (const p of cfg.pages) {
  const ctx = await refusingContext();
  await ctx.route((u) => onKernel(String(u)), (route) => route.request().resourceType() === "fetch" ? route.abort() : route.continue());
  const page = await ctx.newPage();
  await page.goto(cfg.origin + p + "?token=" + encodeURIComponent(cfg.token));
  const refused = await storageRefused(page);
  await page.waitForFunction(() => !!document.body && (document.body.innerText || "").includes("which this browser refuses"), null, { timeout: cfg.deadline }).catch(() => {});
  await page.waitForTimeout(1000);
  out.pages[p] = { refused, at: pathOf(page.url()), look: await sentenceLook(page, cfg.shots + "/sentence" + p.replace(/\W/g, "-") + ".png") };
  await ctx.close();
}
fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
await browser.close();
process.exit(0);
"""

# /login on phone-sized screens, with the page's scripts turned off: the default view fits, every fold starts closed, and a
# click on the first fold's summary opens it.
LOGIN_SIZES = ((320, 568), (375, 667))
LOGIN_SMALL = HEAD + r"""
out.sizes = {};
for (const [w, h] of cfg.sizes) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, javaScriptEnabled: false });
  const page = await ctx.newPage();
  await page.goto(cfg.origin + "/login");
  const m = await page.evaluate(() => {
    const below = (el) => !el || el.getBoundingClientRect().bottom > innerHeight;
    const pointer = Array.from(document.querySelectorAll("form > div")).find((d) => /romp url/.test(d.textContent || ""));
    return { scroll: document.documentElement.scrollHeight, view: innerHeight, folds: document.querySelectorAll("details").length,
             open: document.querySelectorAll("details[open]").length, inputBelow: below(document.getElementById("t")),
             buttonBelow: below(document.querySelector("form button")), pointerBelow: below(pointer) };
  });
  m.opened = null;
  if (m.folds) {
    await page.click("details summary");
    m.opened = await page.evaluate(() => { const d = document.querySelector("details"); return !!d.open && (d.innerText || "").includes("cleared site data"); });
  }
  out.sizes[w + "x" + h] = m;
  await ctx.close();
}
fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
await browser.close();
process.exit(0);
"""

# Every pane the rail lists, by the word it wears, and the settings page: each has a data check in the driver's LOADED.
PANES = ("Chat", "Sessions", "Outline", "Feed", "Waiting", "Files", "Settings")


class ServedDashboardOverThePageKey(unittest.TestCase):
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
        explicit = "PAGE_KEY_DASHBOARD_ENGINE" in os.environ    # an engine asked for by name fails when it is missing
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            if explicit:
                raise AssertionError("PAGE_KEY_DASHBOARD_ENGINE is set but the extension deps are absent")
            raise unittest.SkipTest("extension deps absent (npm ci not run here): the served lab needs them; CI's extension job has them and requires this file to run")
        probe = subprocess.run(["node", "-e", "const p=require(process.argv[1]);process.stdout.write(p[process.argv[2]].executablePath())",
                                os.path.join(EXT, "node_modules", "playwright"), ENGINE], capture_output=True, text=True)
        if probe.returncode != 0 or not os.path.exists(probe.stdout.strip()):
            if explicit:
                raise AssertionError("PAGE_KEY_DASHBOARD_ENGINE=%s is not installed on this box" % ENGINE)
            raise unittest.SkipTest("no playwright browser on this box: the served lab needs one; CI's extension job installs Chromium and requires this file to run")
        cls.lab = tempfile.mkdtemp(prefix="page-key-dash-")
        dist = os.path.join(cls.lab, "dist")
        lab_dist.copy_dist(dist)   # the checkout's ONE build of the bundles, copied under its lock (tests/lab_dist.py)
        state = os.path.join(cls.lab, "xdg", "romp")
        cwd = os.path.join(cls.lab, "proj")
        for d in ("names", "sdk", "states"):
            os.makedirs(os.path.join(state, d), exist_ok=True)
        for d in ("docs", "plots"):
            os.makedirs(os.path.join(cwd, d), exist_ok=True)
        Path(cwd, "plots", "figure.png").write_bytes(_png())
        Path(cwd, "docs", "note.md").write_text("# Note\n\nThe notes-api latency plot:\n\n![note figure](../plots/figure.png)\n")
        Path(state, "names", SID).write_text("web\t%s\t#9cd2ff\t#0c1a2e\n" % cwd)
        Path(state, "sdk", SID + ".json").write_text(json.dumps(
            {"sid": SID, "name": "web", "cwd": cwd, "mode": "auto", "effort": "high", "lastSid": SID, "alive": True,
             "model": "claude-opus-5", "liveModel": "Opus 5"}))
        # one open request for the Waiting pane to show, with its switch on
        Path(state, "user-todos-enabled.json").write_text(json.dumps({"enabled": True, "gt": 1}))
        Path(state, "user-todos.json").write_text(json.dumps(
            {SID: [{"id": "t1", "text": "Pick the notes-api release date.", "createdT": 1757000000000}]}))
        claude = os.path.join(cls.lab, "claude")
        proj = os.path.join(claude, "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(cwd)))
        os.makedirs(proj, exist_ok=True)
        reply = "The notes-api latency plot is written up in docs/note.md."
        Path(proj, SID + ".jsonl").write_text(
            json.dumps({"type": "user", "uuid": U_UUID, "parentUuid": None, "timestamp": "2026-09-05T00:00:00.000Z", "sessionId": SID,
                        "message": {"role": "user", "content": "Where is the notes-api latency plot?"}}) + "\n" +
            json.dumps({"type": "assistant", "uuid": A_UUID, "parentUuid": U_UUID, "timestamp": "2026-09-05T00:00:05.000Z", "sessionId": SID,
                        "message": {"role": "assistant", "model": "claude-opus-5", "content": [{"type": "text", "text": reply}], "stop_reason": "end_turn"}}) + "\n")
        _OtherOrigin.seen = []
        cls.other = ThreadingHTTPServer(("127.0.0.1", 0), _OtherOrigin)
        threading.Thread(target=cls.other.serve_forever, daemon=True).start()
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
            k.kill()
            k.wait()
        if getattr(cls, "other", None):
            cls.other.shutdown()                      # ends the other origin's serve_forever thread
            cls.other.server_close()
        shutil.rmtree(getattr(cls, "lab", ""), ignore_errors=True)

    def _klog_tail(self):
        """The kernel log's tail for a failure message, with the lab token masked (it never appears there; belt)."""
        try:
            return open(self.klog).read()[-1500:].replace(self.token, "<token>")
        except OSError:
            return ""

    def _drive(self, src, **extra):
        cfg = os.path.join(self.lab, "cfg.json")
        self.shots = os.path.join(self.lab, "shots-" + self._testMethodName)
        os.makedirs(self.shots, exist_ok=True)
        with open(cfg, "w") as f:
            json.dump(dict({"origin": "http://127.0.0.1:%d" % self.port, "token": self.token, "sid": SID, "deadline": 30000,
                            "engine": ENGINE, "other": "http://127.0.0.1:%d" % self.other.server_address[1],
                            "shots": self.shots}, **extra), f)
        driver = os.path.join(self.lab, "driver.mjs")
        with open(driver, "w") as f:
            f.write(src)
        p = subprocess.run(["node", driver], capture_output=True, text=True, timeout=400,
                           env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg))
        os.unlink(cfg)
        if p.returncode == 3:
            if "PAGE_KEY_DASHBOARD_ENGINE" in os.environ:
                self.fail("the %s engine did not launch" % ENGINE)
            raise unittest.SkipTest("no playwright browser on this box: the served lab needs one; CI's extension job installs Chromium and requires this file to run")
        mask = lambda s: s.replace(self.token, "<token>")
        self.assertEqual(p.returncode, 0, "driver failed:\n" + mask(p.stdout[-3000:] + p.stderr[-3000:]) + "\nkernel:\n" + self._klog_tail())
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
        self.assertIsNotNone(line, "driver printed no result:\n" + mask(p.stdout[-3000:]))
        self.assertNotIn(self.token, line, "the driver's report carries no credential")
        if os.environ.get("PAGE_KEY_DASHBOARD_REPORT"):   # a directory: each scene's report (booleans, statuses, counts) for the record
            with open(os.path.join(os.environ["PAGE_KEY_DASHBOARD_REPORT"], ENGINE + "-" + self._testMethodName + ".json"), "w") as f:
                f.write(line[len("RESULT:"):] + "\n")
            for name in os.listdir(self.shots):      # and the scene's screenshots, which the pixel checks read
                shutil.copy(os.path.join(self.shots, name),
                            os.path.join(os.environ["PAGE_KEY_DASHBOARD_REPORT"], ENGINE + "-" + self._testMethodName + "-" + name))
        return json.loads(line[len("RESULT:"):])

    def _assert_panes(self, panes, when):
        self.assertEqual(panes, {k: True for k in PANES}, when + ": every pane the rail lists, and settings, loaded its data "
                                                                 "(a pane with no check is named \"no check\")")

    def _assert_requests(self, req, when):
        self.assertGreater(req["data"], 10, when + ": the pages made their data requests: %r" % req)
        self.assertEqual(req["unkeyed"], [], when + ": every fetch to the kernel carried X-Romp-Key equal to the stored key")
        self.assertEqual(req["refused"], [], when + ": no request the pages made was refused")
        self.assertEqual(req["xhr"], 0, when + ": no XMLHttpRequest or EventSource: the wrapper covers fetch alone")

    def test_the_dashboard_boots_and_every_pane_loads_its_data_over_the_page_key(self):
        r = self._drive(DASHBOARD)
        self.assertGreater(r["keyLen"], 20, "the login seeded the page key")
        self.assertFalse(r["keyIsToken"], "the page key is not the serve token")
        self.assertTrue(r["addressClean"], "the address keeps no token= once the page runs")
        self._assert_panes(r["panes"], "signed in")
        docs = ("shell",) + PANES
        self.assertTrue(set(docs) <= set(r["documents"]), "every pane's document loaded: %r" % r["documents"])
        self._assert_requests(r["requests"], "signed in")
        for p in docs:
            self.assertIn(p, r["requests"]["frames"], "the %s document made its own keyed fetches: %r" % (p, r["requests"]["frames"]))
        panes = {s["pane"] for s in r["sockets"] if s["path"] == "/ws"}
        self.assertTrue(set(docs) <= panes, "every pane dialed its socket: %r" % sorted(panes))
        self.assertEqual([s for s in r["sockets"] if s["key"] != "mine"], [], "every socket carries k= equal to the stored key")
        self.assertEqual([s for s in r["sockets"] if not s["heard"]], [], "and the kernel answered on every one")
        self.assertEqual(r["post"]["status"], 200, "the notification switch's POST is answered")
        self.assertTrue(r["post"]["flipped"], "the switch shows the new state")
        self.assertTrue(r["post"]["held"], "and the kernel holds it")

    def test_the_fetch_wrapper_keys_every_request_form_for_this_origin_and_no_other(self):
        _OtherOrigin.seen = []
        r = self._drive(FORMS)
        st, seen = r["status"], r["seen"]
        same = ("string", "url", "absolute", "request", "requestInit", "object", "pairs", "headers", "initNoHeaders",
                "requestInitNoHeaders", "post", "postRequest")
        self.assertEqual({k: st[k] for k in same}, {k: 200 for k in same}, "the kernel answers every form of same-origin fetch: %r" % st)
        self.assertEqual({n: seen.get(str(n), {}).get("key") for n in range(1, 13)}, {n: "mine" for n in range(1, 13)},
                         "each carried X-Romp-Key equal to the stored key: %r" % seen)
        self.assertEqual(seen["4"]["probe"], "r", "a Request keeps its own headers")
        self.assertEqual((seen["5"]["probe"], seen["5"]["probeInit"]), (None, "i"),
                         "init headers replace a Request's, as the browser's fetch has them")
        self.assertEqual([seen[n]["probe"] for n in ("6", "7", "8")], ["o", "p", "h"], "init headers as an object, pairs or a Headers are kept")
        self.assertEqual(seen["10"]["probe"], "r", "a Request with an init that names no headers keeps its own")
        self.assertEqual([seen[n]["method"] for n in ("11", "12")], ["POST", "POST"])
        self.assertEqual([st[k] for k in ("other", "otherHeaders", "otherRequest")], [200, 200, 200], "the other origin was reached")
        other = _OtherOrigin.seen
        self.assertTrue(other, "the other origin saw the requests")
        self.assertEqual([x for x in other if "x-romp-key" in x["names"] or "x-romp-key" in x["asked"]], [],
                         "a request to another origin carries no page key and no preflight asks to send one: %r" % other)
        self.assertEqual([x for x in other if x["method"] == "OPTIONS" and x["asked"] != ["x-probe"]], [],
                         "the one preflight is the site's own header's: %r" % other)

    def test_a_stale_dashboard_tab_is_refused_and_signing_in_again_brings_it_back(self):
        r = self._drive(STALE)
        self._assert_panes(r["before"], "before the key changed")
        self.assertTrue(r["keysDiffer"] and r["sameSlot"], "two sign-ins of one kernel: one slot name, two keys")
        self.assertIn(r["switchBefore"], (True, False))
        post = r["stale"]["post"]
        self.assertEqual(post, [{"status": 403, "reauth": True}], "the stale tab's POST is refused with the re-sign-in 403: %r" % r["postStatus"])
        self.assertEqual(r["stale"]["answered"], [], "no request with the stale key was answered")
        self.assertEqual(r["stale"]["unmarked"], [], "every refusal carried the re-sign-in marker")
        self.assertIs(r["switchAfterRefusal"], r["switchBefore"], "the refused POST, which asked for the other state, changed nothing")
        self.assertTrue(r["hop"], "the tab went to /login")
        self.assertTrue(r["keyDropped"], "and dropped the stale key")
        self.assertEqual(r["backAt"], "/", "the /login form signs in and lands the dashboard")
        self.assertTrue(r["backAddressClean"], "with no token= left in the address")
        self.assertEqual(r["keyBack"], "mine", "the sign-in kept this browser's session and seeded its own key again")
        self._assert_panes(r["after"], "signed in again")
        self._assert_requests(r["afterRequests"], "signed in again")
        self.assertTrue(r["afterSockets"], "the dashboard dialed its sockets again")
        self.assertEqual([s for s in r["afterSockets"] if s["key"] != "mine" or not s["heard"]], [], "the sockets carry the key again and are answered")
        self.assertEqual(r["post"]["status"], 200, "the POST is answered again")
        self.assertTrue(r["post"]["flipped"] and r["post"]["held"], "and takes effect")

    def test_a_stale_tab_on_an_origin_whose_storage_is_full_drops_the_key_and_signs_in_again(self):
        r = self._drive(FULL_QUOTA)
        self.assertGreater(r["keyLen"], 20, "the dashboard signed in and holds its key")
        self.assertTrue(r["fill"]["swapped"], "the stored key changed to another sign-in's")
        self.assertEqual(r["fill"]["probe"], "QuotaExceededError",
                         "the origin's storage is full: the storage probe's own write does not fit before the refusal: %r" % r["fill"])
        self.assertGreater(r["refusals"], 0, "a request with the stale key came back with the re-sign-in 403: %r" % (r["request"],))
        self.assertEqual((r["at"], r["says"], r["key"]), ("/login", False, "dropped"),
                         "the re-sign-in branch dropped the stale key, the storage probe's write fit in the room it left, and the tab "
                         "went to /login with no storage-refused sentence (at, sentence, key; navs %r)" % r["navs"])
        self.assertIs(r["fillKept"], True, "the rest of the storage is still full")
        b = r["back"]
        self.assertEqual(b["at"], "/", "the /login form signs in and lands the dashboard: %r" % b)
        self.assertEqual(b["key"], "mine", "the sign-in seeded this browser's key into the room the stale key left: %r" % b)
        self.assertEqual(b["answered"], 200, "and the dashboard's requests are answered: %r" % b)
        self.assertIs(b["says"], False, "with no storage-refused sentence: %r" % b)
        self.assertIs(b["fillKept"], True, "while the rest of the storage is still full: %r" % b)

    def _assert_legible(self, look, shot, where):
        """The storage-refused sentence reads: its ink on the first opaque background behind it clears 4.5:1 by the computed
        styles and by the screenshot's pixels, and the text is set in from the window's edge."""
        self.assertTrue(look and look.get("said"), where + ": the page shows the sentence: %r" % (look,))
        self.assertTrue(look.get("shot"), where + ": the sentence's box was captured")
        styled = _ratio(_rgb(look["ink"]), _rgb(look["ground"]))
        self.assertGreaterEqual(styled, 4.5, where + ": the computed ink %s on %s is %.2f:1" % (look["ink"], look["ground"], styled))
        seen = _pixel_contrast(os.path.join(self.shots, shot))
        self.assertGreaterEqual(seen, 4.5, where + ": the screenshot's text measures %.2f:1" % seen)
        self.assertGreaterEqual(min(look["box"]["x"], look["box"]["y"]), 16, where + ": the text is set in from the edge: %r" % look["box"])

    def test_a_browser_that_refuses_site_storage_stays_on_the_sentence_and_never_hops_to_login(self):
        r = self._drive(STORAGE_REFUSED)
        self.assertIs(r["refused"], True, "the browser refuses site storage")
        self.assertEqual(r["cookies"], 1, "and keeps the session cookie the sign-in set")
        self.assertGreater(r["reauth"], 0, "the boot's requests came back with the re-sign-in 403, the answer that sends a tab to /login")
        self.assertEqual(r["navs"][0], "/login", "the scene starts on /login: %r" % r["navs"])
        self.assertNotIn("/login", r["navs"][1:], "no hop back to /login after the sign-in: %r" % r["navs"])
        self.assertEqual(r["at"], "/", "the tab stays on the dashboard's address")
        self._assert_legible(r["look"], "after-sign-in.png", "after the sign-in")

    def test_a_pane_that_finds_storage_refused_shows_the_sentence_in_the_top_frame_and_nothing_navigates(self):
        r = self._drive(PANE_REFUSED)
        self.assertTrue(r["chat"], "the chat pane loaded")
        self.assertIs(r["topBefore"], False, "the dashboard signed in with working storage: no sentence before the pane's request")
        self.assertGreaterEqual(r["paneRefusals"], 1, "the pane's keyless request came back with the re-sign-in 403: %r" % (r.get("pane"),))
        self.assertNotIn("/login", r["navs"], "nothing navigated to /login: %r" % r["navs"])
        self.assertEqual(r["at"], "/", "the tab stays on the dashboard's address")
        self.assertIs(r["topSays"], True, "the top frame's document shows the sentence the pane's branch wrote there")

    def test_the_storage_refused_sentence_is_legible_on_every_top_level_page(self):
        pages = _sentence_pages()
        r = self._drive(SENTENCE, pages=pages)
        self.assertEqual(sorted(r["pages"]), sorted(pages), "the driver measured every page route")
        for p in pages:
            m = r["pages"][p]
            self.assertIs(m["refused"], True, p + ": the browser refuses site storage")
            self.assertEqual(m["at"], p, p + ": the page stays where it was opened")
            self._assert_legible(m["look"], "sentence" + re.sub(r"\W", "-", p) + ".png", p)

    def test_the_sign_in_page_fits_a_phone_screen_with_its_folds_closed(self):
        r = self._drive(LOGIN_SMALL, sizes=[list(s) for s in LOGIN_SIZES])
        for w, h in LOGIN_SIZES:
            m = r["sizes"]["%dx%d" % (w, h)]
            self.assertGreaterEqual(m["folds"], 1, "%dx%d: the page has a fold: %r" % (w, h, m))
            self.assertEqual(m["open"], 0, "%dx%d: every fold starts closed" % (w, h))
            self.assertLessEqual(m["scroll"], m["view"], "%dx%d: the default view fits, nothing to scroll: %r" % (w, h, m))
            self.assertEqual((m["inputBelow"], m["buttonBelow"], m["pointerBelow"]), (False, False, False),
                             "%dx%d: the token field, the Open button and the romp url pointer are on screen: %r" % (w, h, m))
            self.assertIs(m["opened"], True, "%dx%d: a click on the first fold's summary opens it, with the page's scripts off" % (w, h))


if __name__ == "__main__":
    unittest.main()
