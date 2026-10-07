#!/usr/bin/env python3
"""The pane registry on the REAL dashboard (plans/panes-as-data.md, phase one, section 7's served leg). A hermetic kernel
starts with three data panes on disk: a state-root pane (pane:notes, a page under STATE/panes/notes/ that loads shim.js and
theme.css from /pane/notes/), a URL pane (a page a second, foreign origin serves: protocol none) and an experimental
route pane. The shell renders the shipped panes and builds the data panes in the browser from GET /panes (one source for
the pane records). A driver opens the dashboard and reads:
  1. the rail carries the shipped five then the data panes, the experimental one hidden until the gear asks; the body
     wears po-notes and po-docs, its attribute carries the shipped generic pane alone, and the shell's GET /panes read
     holds the data panes;
  2. the notes pane is a shown column loading /pane/notes/: its page has the shim (window.__rompReload), the theme, and
     hears the pane-set broadcast naming it;
  3. the URL pane is a sandboxed iframe with its URL as given (no ?v=, no token), marked protocol none; the forged
     toggleFleet, notify and reveal it posts on load change nothing, and it is told nothing (its beacons say so); its
     frame wears the sandbox from the moment it is in the document, before any address is set (a mutation observer on
     the top document, desktop and phone);
  4. the gear's Panes section has a row per data pane, the experimental one off; turning it on brings the pane on screen;
  5. a define at the kernel while the page is open: the pane-set revision on the next keepalive stands the reload OFFER
     with the panes' wording, the page does not reload on its own, and the Reload click shows the new pane;
  6-8. the docking kit and two phone sizes (a data pane's tab loads its page once, by the tap alone);
  9. GET /panes answering 500: no data pane is built, and the failure is shown (the Log's entry of its own kind and the
     gear's line on the desktop, the bar's Log mark on the phone), never an empty list passed off as the whole set;
  10. a phone whose remembered tab is a data pane: the tab is shown once the list lands, and its page loads once;
  11. a define landing while the shell's GET /panes read is in flight (the read held by the driver until the define is
     in): the page shows the new pane and offers no reload for the revision it already shows, and a later define's offer
     arrives (the witness that the keepalive path was live);
  12. a press on a gear row held while the shell's GET /panes read lands (held past the splash's backstop, the gear open on its
     still-reading line): the Panes section renders the read's rows after the release, and the press still toggles the box.
The legs run in Chromium and, in a subclass, in WebKit (an `optional:` skip where the runner declares no WebKit or the
engine is not installed; CI declares Chromium only, ROMP_SERVED_TESTS_ENGINES), each class with a kernel of its own, so a
define in one engine's legs changes nothing the other reads.
On this fork step 2's page does not load yet: the /pane/<id>/ routes are in the kernel's full auth class until the owner
rules (PANE_ROUTE_CLASS_APPROVED below), so the shell's frame, which carries only the session cookie, is refused, and the
reads that need the page are held in their own test, which pins the refusal until then.
Runs when ROMP_SERVED_TESTS_REQUIRE=1 (CI); skips where no Chromium is installed. Synthetic fixtures only."""
import http.server
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
EXT = os.path.join(ROOT, "vscode-extension")
SID = "11111111-2222-4333-8444-000000000301"

# Hermetic state BEFORE anything: this module loads no romp code in-process (the kernel is a subprocess under kernel_env's
# roots), but the floor costs two lines and a later edit that adds a load must not write real state.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
# ...and that root's per-session hosts off (the Testing rule for a test that mints its own state root): nothing resolves this
# root as STATE today (the lab kernel's root is floored by kernel_env and written below), so this is the belt for a later load
os.makedirs(os.path.join(os.environ["XDG_STATE_HOME"], "romp"), exist_ok=True)
Path(os.environ["XDG_STATE_HOME"], "romp", "session-hosts").write_text("off\n")

# the sandbox a URL pane's frame wears (kernel/kernel.py _data_pane_markup, and the shell's builder for a pane defined at the kernel)
URL_SANDBOX = "allow-scripts allow-forms allow-popups"

import sys
sys.path.insert(0, HERE)
import lab_dist                          # noqa: E402
import lab_ports                         # noqa: E402
import test_ship_reship_served as _lab   # noqa: E402  the lab kernel's environment (the module, not its classes)

REQUIRE = os.environ.get("ROMP_SERVED_TESTS_REQUIRE") == "1"

# The state-root pane's routes and the fork's auth classes (fold 4, slice 2, 2026-10-03). The project serves a state-root pane's
# page, shim.js, theme.css and files under GET /pane/<id>/..., which the shell loads in a frame. The fork's classifier
# (kernel/kernel.py Handler._need) lets the session cookie alone open only the page class (_PAGE_RENDERERS) and the static class
# (_static_route); /pane/... is in neither, so it is "full", which also needs the page key or the token, and a frame's
# navigation carries neither: the kernel answers 403 "forbidden: session key required" with X-Romp-Reauth. Whether a
# producer-written page under the state root may open on the cookie alone is the owner's call, so the class is held on the
# safe side and test_a_state_root_pane_page_loads_only_once_its_auth_class_is_ruled pins the refusal. Written to revert: once
# the owner rules and the kernel's class for /pane/<id>/ is restored, set this to the date of the ruling, and that test holds
# the page loading again with every read the project's lab made of it.
PANE_ROUTE_CLASS_APPROVED = None


def _transcript(cwd, pairs):
    out, parent, t = [], None, 1_700_000_000
    for i in range(pairs):
        u = "11111111-2222-4333-8444-0000000c%04x" % i
        a = "11111111-2222-4333-8444-0000000d%04x" % i
        ts = lambda k: time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(t + i * 60 + k))
        out.append({"type": "user", "uuid": u, "parentUuid": parent, "timestamp": ts(0), "sessionId": SID, "cwd": cwd,
                    "message": {"role": "user", "content": "please keep the notes index fresh (part %d)" % (i + 1)}})
        out.append({"type": "assistant", "uuid": a, "parentUuid": u, "timestamp": ts(5), "sessionId": SID, "cwd": cwd,
                    "message": {"id": "msg_lab_%04d" % i, "type": "message", "role": "assistant", "model": "claude-sonnet-5",
                                "content": [{"type": "text", "text": "Note %d refreshed." % (i + 1)}], "stop_reason": "end_turn"}})
        parent = a
    return "\n".join(json.dumps(r) for r in out) + "\n"


NOTES_PAGE = """<!doctype html><html><head><meta charset=utf-8><link rel=stylesheet href=theme.css><script src=shim.js></script></head>
<body><h1 id=t>Notes</h1><div id=empty data-pane-empty style="height:260px"></div><iframe id=inner src=inner.html></iframe><script>
window.__labMsgs=[];window.addEventListener('message',function(e){window.__labMsgs.push(e.data);});
</script></body></html>"""

# a frame NESTED inside the notes pane (same origin as the shell, served from the pane's own directory): it forges the
# shell's messages to the top window; the check rules on the immediate frame, so a nested frame is not a pane and nothing acts
INNER_PAGE = """<!doctype html><html><body><script>
try{top.postMessage({romp:'toggleFleet',to:'fleet'},'*');top.postMessage({romp:'notify',kind:'error',text:'forged from a nested frame'},'*');
top.postMessage({romp:'openKeys'},'*');top.postMessage({romp:'hotkeyConfigure',sid:'11111111-2222-4333-8444-000000000301',name:'nested'},'*');}catch(e){}
</script></body></html>"""

# the URL pane's page, served by a SECOND origin: on load it forges three shell messages, and it beacons every message it
# receives back to its own server (an image load needs no CORS), so the test can read that it was told nothing
DOCS_PAGE = """<!doctype html><html><head><meta charset=utf-8></head><body><h1>Docs</h1><script>
try{parent.postMessage({romp:'toggleFleet',to:'fleet'},'*');parent.postMessage({romp:'notify',kind:'error',text:'forged from the docs pane'},'*');parent.postMessage({romp:'reveal',pane:'fleet'},'*');
parent.postMessage({romp:'openKeys'},'*');parent.postMessage({romp:'hotkeyConfigure',sid:'11111111-2222-4333-8444-000000000301',name:'forged'},'*');}catch(e){}
window.addEventListener('message',function(e){var i=new Image();i.src='/beacon?m='+encodeURIComponent(JSON.stringify(e.data)).slice(0,300);});
</script></body></html>"""


class _DocsServer(http.server.BaseHTTPRequestHandler):
    beacons = []   # each lab class serves through a subclass holding a list of its own (setUpClass), so one engine's beacons never reach another's read

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/beacon"):
            type(self).beacons.append(self.path)
            self.send_response(204); self.end_headers(); return
        body = DOCS_PAGE.encode()
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)


DRIVER = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const playwright = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
const engine = cfg.engine || "chromium";
let browser;
try { browser = await playwright[engine].launch(); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
// The URL pane's frame and its sandbox, read by a mutation observer on the TOP document from before any page script: at the frame's
// insertion into the document and at its first src, the value each attribute had at that moment. A batch of records is read in order,
// and an attribute's value at record i is the old value of the first LATER record for it in the same batch, else its live value, so
// a sandbox set after the insertion (or after the src) in the same task still reads as absent where it was absent.
const SANDBOX_WATCH = () => {
  if (window.top !== window) return;
  const W = window.__labSandbox = { insert: null, firstSrc: null };
  const valAt = (recs, i, el, name) => { for (let j = i + 1; j < recs.length; j++) { const r = recs[j]; if (r.type === "attributes" && r.target === el && r.attributeName === name) return r.oldValue; } return el.getAttribute(name); };
  const docsIn = (n) => (!n || n.nodeType !== 1) ? null : (n.id === "f-docs" ? n : (n.querySelector ? n.querySelector("#f-docs") : null));
  new MutationObserver((recs) => { recs.forEach((r, i) => {
    if (r.type === "childList") { for (const n of r.addedNodes) { const el = docsIn(n); if (el && !W.insert) W.insert = { sandbox: valAt(recs, i, el, "sandbox"), src: valAt(recs, i, el, "src") }; } }
    else if (r.type === "attributes" && r.target.id === "f-docs" && r.attributeName === "src" && !W.firstSrc && r.oldValue === null)
      W.firstSrc = { sandbox: valAt(recs, i, r.target, "sandbox"), src: valAt(recs, i, r.target, "src") };
  }); }).observe(document, { subtree: true, childList: true, attributes: true, attributeOldValue: true, attributeFilter: ["src", "sandbox"] });
};
// Every state the reload core hands the shell's offer hook (window.__rompReload.offer, which the stale banner's script installs and
// the core calls on every change of its standing offer), recorded from the page's first script: the core's object is caught as it
// is published and its hook wrapped in place, so no offer can stand and fall between two reads of the banner.
const OFFER_WATCH = () => {
  if (window.top !== window) return;
  const log = window.__labOffers = [];
  let core;
  Object.defineProperty(window, "__rompReload", { configurable: true, enumerable: true, get() { return core; }, set(v) {
    core = v;
    if (!v || typeof v !== "object") return;
    let hook = v.offer;
    Object.defineProperty(v, "offer", { configurable: true, enumerable: true, set(f) { hook = f; }, get() {
      if (typeof hook !== "function") return hook;
      return function (o) { log.push({ t: Date.now(), offer: o ? { pv: String(o.pv || ""), dv: Number(o.dv) || 0, code: String(o.code || ""), text: String(o.text || "") } : null }); return hook.apply(this, arguments); };
    } });
  } });
};
const page = await browser.newPage({ viewport: { width: 1500, height: 900 } });
await page.addInitScript(SANDBOX_WATCH);
const out = { engine };
// the state-root pane's document responses, status and the re-sign-in mark (the fork holds the route's auth class: PANE_ROUTE_CLASS_APPROVED)
const docsOf = (pg, into) => pg.on("response", (rs) => { if (rs.request().resourceType() === "document" && /\/pane\/notes\/(\?|$)/.test(rs.url()))
  into.push({ status: rs.status(), reauth: rs.headers()["x-romp-reauth"] || null }); });
out.notesDocs = [];
docsOf(page, out.notesDocs);
const die = async (why) => { fs.writeSync(1, "RESULT:" + JSON.stringify({ ...out, died: why }) + "\n"); await browser.close(); process.exit(0); };
const rail = () => page.evaluate(() => Array.from(document.querySelectorAll(".rail-btn[data-pane]")).map((b) => ({ pane: b.getAttribute("data-pane"), text: b.textContent, hidden: b.hidden, on: b.classList.contains("on") })));
const body = () => page.evaluate(() => ({ cls: document.body.className.split(/\s+/).filter((c) => /^po-/.test(c)).sort(), attr: JSON.parse(document.body.getAttribute("data-panes") || "null"),
  records: (() => { const rr = window.__rompPaneRecords; return rr ? { state: rr.state, rows: (rr.rows || []).map((p) => ({ id: p.id, protocol: p.protocol, experimental: p.experimental, on: p.on })) } : null; })() }));   // the panes defined at the kernel, as the shell built them from GET /panes
const banner = () => page.evaluate(() => { const b = document.getElementById("rstale"); if (!b) return null;
  return { shown: b.classList.contains("show"), offer: b.classList.contains("offer"), text: b.querySelector(".rs-msg").textContent, reload: document.getElementById("rstale-reload").textContent }; }).catch(() => null);
const waitOffer = (ms) => page.waitForFunction(() => { const b = document.getElementById("rstale"); return !!b && b.classList.contains("show") && b.classList.contains("offer"); }, null, { timeout: ms }).then(() => true).catch(() => false);
const frameEnding = async (suffix) => { let fr = null; for (let i = 0; i < 150 && !fr; i++) { fr = page.frames().find((f) => f.url().split("?")[0].endsWith(suffix)); if (!fr) await page.waitForTimeout(100); } return fr; };

// BUILT(sel): the shell's GET /panes read has settled and the element named exists. A synchronous predicate handed its selector as the
// argument (waitForFunction serialises the function, not its closure); a page with no read is judged by the element alone, and step 1
// reads the state object itself
const BUILT = (sel) => { const rr = window.__rompPaneRecords; return (!rr || rr.state !== "loading") && !!document.querySelector(sel); };
const readState = (pg) => pg.evaluate(() => { const rr = window.__rompPaneRecords; return rr ? { state: rr.state, status: rr.status || 0, error: rr.error || "", rows: (rr.rows || []).map((p) => p.id) } : null; });
// the read's line in the gear's Panes section as a reader meets it, read in the settings frame: its text and role;
// rendered, the line has a box and checkVisibility passes; textShown, its rendered text is all of its text (innerText
// leaves out what is not rendered, and equals textContent for an element not rendered at all, so rendered is read with
// it); sectionShown, the section is on screen (the General tab open), so inSection, the section's rendered text holding
// the line's, is not read off a hidden section
const GEAR_LINE = () => { const l = document.querySelector("#rs-panes-data .rs-panes-read"); if (!l) return null;
  const box = document.getElementById("rs-panes-data"), r = l.getBoundingClientRect();
  const seen = (el) => (typeof el.checkVisibility === "function" ? el.checkVisibility() : true)
    && el.getClientRects().length > 0;
  return { text: l.textContent, role: l.getAttribute("role"), rendered: seen(l) && r.width > 0 && r.height > 0,
    textShown: l.innerText.trim() === l.textContent.trim(), sectionShown: !!box && seen(box),
    inSection: !!box && box.innerText.indexOf(l.textContent) >= 0 }; };
// the settings frame once its Panes section is in it (the gear opened on a tab first), or null
const gearFrame = async (pg) => { for (let i = 0; i < 150; i++) { for (const f of pg.frames()) {
  if (await f.$("#rs-pane-artifacts").catch(() => null)) return f; } await pg.waitForTimeout(100); } return null; };


// ---- 1. the landing ----
await page.goto(cfg.url);
await page.waitForFunction(BUILT, ".rail-btn[data-pane=notes]", { timeout: 20000 }).catch(async () => { await die("no notes rail button"); });
await page.waitForTimeout(500);
out.rail = await rail();
out.body = await body();

// ---- 2. the state-root pane ----
const nf = await frameEnding("/pane/notes/");
if (!nf) await die("no /pane/notes/ frame");
await nf.waitForFunction(() => !!window.__rompReload, null, { timeout: 15000 }).catch(() => {});
out.notesHeard = await nf.waitForFunction(() => (window.__labMsgs || []).some((m) => m && m.romp === "panes"), null, { timeout: 15000 }).then(() => true).catch(() => false);
out.notesPage = await nf.evaluate(() => ({ title: (document.getElementById("t") || {}).textContent, shim: typeof window.__rompReload, text: ((document.body || {}).innerText || "").slice(0, 120),
  theme: Array.from(document.styleSheets).some((s) => (s.href || "").endsWith("/pane/notes/theme.css")),
  on: (((window.__labMsgs || []).filter((m) => m && m.romp === "panes").slice(-1)[0]) || {}).on || null }));
out.notesRect = await page.evaluate(() => { const r = document.getElementById("notes-pane").getBoundingClientRect(); const c = document.getElementById("chat-pane").getBoundingClientRect();
  return { w: Math.round(r.width), h: Math.round(r.height), rightOfChat: r.left >= c.right, gutter: getComputedStyle(document.getElementById("gv-notes")).display }; });
out.notesSrc = await page.evaluate(() => document.getElementById("f-notes").getAttribute("src"));

// ---- 3. the URL pane ----
out.docs = await page.evaluate(() => { const f = document.getElementById("f-docs"); return { src: f.getAttribute("src"), sandbox: f.getAttribute("sandbox"), proto: f.getAttribute("data-protocol"), shown: document.body.classList.contains("po-docs"), w: Math.round(f.getBoundingClientRect().width) }; });
out.docsSandbox = await page.evaluate(() => window.__labSandbox || null);   // the frame's sandbox at its insertion and at its first src (SANDBOX_WATCH)
await page.waitForTimeout(2500);   // the docs page's and the nested frame's forged posts on load, and any broadcast the docs page would beacon
out.nestedLoaded = await nf.evaluate(() => { const f = document.getElementById("inner"); return !!(f && f.contentDocument && f.contentDocument.readyState === "complete"); }).catch(() => false);
out.afterForged = await page.evaluate(() => ({ fleet: document.body.classList.contains("po-fleet"),
  keysOpen: (() => { const b = document.getElementById("rkeys-back"); return !!b && !b.hidden; })(),   // the shortcuts modal (palette-main openKeys / hotkeyConfigure)
  tabKeys: localStorage.getItem("romp:tabkeys"),                                                     // a forged hotkeyConfigure would have remembered the chosen sid here
  notices: (() => { try { return JSON.parse(localStorage.getItem("romp:notices") || "[]").map((n) => n.text); } catch (e) { return []; } })() }));

if (cfg.shot) await page.screenshot({ path: cfg.shot });   // a picture for a reviewer (ROMP_LAB_SHOT names the file; unset in CI)

// ---- 4. the gear's rows ----
await page.evaluate(() => window.__rompOpenSettings && window.__rompOpenSettings());
let gf = null;
for (let i = 0; i < 150 && !gf; i++) { for (const f of page.frames()) { if (await f.$("#rs-pane-notes").catch(() => null)) { gf = f; break; } } if (!gf) await page.waitForTimeout(100); }
if (!gf) await die("no settings frame with the registry rows");
out.gear = await gf.evaluate(() => Array.from(document.querySelectorAll("#rs-panes-data input")).map((i) => ({ id: i.id, checked: i.checked, label: i.parentNode.querySelector("b").textContent })));
out.gearLine = await gf.evaluate(() => { const l = document.querySelector("#rs-panes-data .rs-panes-read"); return l ? l.textContent : null; });   // the read's own line, shown only while the read has not given its rows
await gf.evaluate(() => { for (const id of ["rs-pane-lab", "rs-pane-artifacts"]) { const i = document.getElementById(id); i.checked = true; i.dispatchEvent(new Event("change", { bubbles: true })); } });
out.labAfterGear = await page.waitForFunction(() => { const b = document.querySelector(".rail-btn[data-pane=lab]"); return !!b && !b.hidden && document.body.classList.contains("po-lab"); }, null, { timeout: 10000 }).then(() => true).catch(() => false);
out.labSrc = await page.evaluate(() => document.getElementById("f-lab").getAttribute("src"));
out.artifactsAfterGear = await page.evaluate(() => { const b = document.querySelector(".rail-btn[data-pane=artifacts]"); const f = document.getElementById("f-artifacts");
  return { hidden: !!b && b.hidden, on: document.body.classList.contains("po-artifacts"), src: f ? f.getAttribute("src") : "absent" }; });
out.settingsPanes = await page.evaluate(() => { try { return JSON.parse(localStorage.getItem("romp:settings") || "{}").panes || null; } catch (e) { return null; } });
// ---- 4b. a HAND row flipped keeps the registry keys (the 1919 read, still standing at 1922: the hand rows' handler rewrote the set from
// three keys, so flipping Sessions, the Outline or the Feed dropped every registry key: the Artifacts control hid and its column
// closed while its row read checked, and a data pane's stored false came back on) ----
await gf.evaluate(() => { const i = document.getElementById("rs-pane-notes"); i.checked = false; i.dispatchEvent(new Event("change", { bubbles: true })); });   // a data pane hidden by its row: stored false
await page.waitForFunction(() => document.querySelector(".rail-btn[data-pane=notes]").hidden, null, { timeout: 5000 }).catch(() => {});
await gf.evaluate(() => { const i = document.getElementById("rs-pane-feed"); i.checked = false; i.dispatchEvent(new Event("change", { bubbles: true })); });   // a HAND row flipped
await page.waitForFunction(() => document.querySelector(".rail-btn[data-pane=feed]").hidden, null, { timeout: 5000 }).catch(() => {});
await page.waitForTimeout(300);
out.afterFeedFlip = await page.evaluate(() => ({ panes: (() => { try { return JSON.parse(localStorage.getItem("romp:settings") || "{}").panes || null; } catch (e) { return null; } })(),
  feedHidden: document.querySelector(".rail-btn[data-pane=feed]").hidden, notesHidden: document.querySelector(".rail-btn[data-pane=notes]").hidden,
  artifactsHidden: document.querySelector(".rail-btn[data-pane=artifacts]").hidden, labOn: document.body.classList.contains("po-lab"), notesOn: document.body.classList.contains("po-notes") }));
await gf.evaluate(() => { for (const id of ["rs-pane-feed", "rs-pane-notes"]) { const i = document.getElementById(id); i.checked = true; i.dispatchEvent(new Event("change", { bubbles: true })); } });   // both back
await page.waitForFunction(() => !document.querySelector(".rail-btn[data-pane=notes]").hidden && !document.querySelector(".rail-btn[data-pane=feed]").hidden, null, { timeout: 5000 }).catch(() => {});

// ---- 5. a define while the page is open ----
await page.evaluate(() => { window.__probe = 1; });
const res = await fetch(cfg.api + "/pane", { method: "POST", headers: { "Content-Type": "application/json", "X-Romp-Token": cfg.token },
  body: JSON.stringify({ id: "later", title: "Later", source: "/feed", on: true }) });
out.define = await res.json();
out.offerShown = await waitOffer(15000);           // one keepalive (ROMP_WS_KEEPALIVE=2) carries the moved revision
out.banner = await banner();
await page.waitForTimeout(4500);                   // two more keepalives: a self-reload would have fired by now
out.probeAlive = await page.evaluate(() => window.__probe === 1);
out.laterBeforeReload = await page.evaluate(() => !!document.querySelector(".rail-btn[data-pane=later]"));
await page.click("#rstale-reload");
out.reloaded = await page.waitForFunction(() => window.__probe !== 1, null, { timeout: 15000 }).then(() => true).catch(() => false);
await page.waitForSelector(".rail-btn[data-pane=later]", { timeout: 20000 }).catch(() => {});
await page.waitForTimeout(500);
out.afterReload = { later: !!(await page.$(".rail-btn[data-pane=later]")), body: await body(), banner: await banner() };

// ---- 6. the docking kit reads the list (plans/panes-as-data.md section 4): a data pane is a tree leaf with a ring, drops into a half-zone ----
const frame = () => page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => r(1)))));
await page.evaluate(() => { const s = JSON.parse(localStorage.getItem("romp:settings") || "{}"); s.paneDocking = true; s.panes = Object.assign({}, s.panes || {}, { artifacts: true }); localStorage.setItem("romp:settings", JSON.stringify(s)); });   // the kit on; the Artifacts pane enabled in the gear (step 4 clicked its row; said here, not relied on)
await page.reload();
await page.waitForSelector(".rail-btn[data-pane=notes]", { timeout: 20000 }).catch(async () => { await die("no notes rail button after the kit's reload"); });
out.kitOn = await page.waitForFunction(() => !!(window.__rompPaneDock && window.__rompPaneDock.on() && window.__rompPaneDock.layout()), null, { timeout: 15000 }).then(() => true).catch(() => false);
if (!out.kitOn) await die("the docking kit did not come on");
await frame();
const leavesOf = () => page.evaluate(() => { const lay = window.__rompPaneDock.layout(); const lv = (n) => n.pane ? [n.pane] : n.kids.flatMap(lv); return lay ? lv(lay.tree) : []; });
const rectsOf = () => page.evaluate(() => Object.fromEntries(window.__rompPaneDock.rects().map((r) => { const el = document.getElementById(r.pane); const f = el && el.querySelector(":scope > iframe"); const b = f ? f.getBoundingClientRect() : null;
  return [r.pane, Object.assign({}, r.rect, { frame: b ? { x: b.left, y: b.top, w: b.width, h: b.height } : null })]; })));
out.kitLeaves = await leavesOf();
out.kitRects = await rectsOf();
out.kitTitleRail = await page.evaluate(() => Array.from(document.querySelectorAll(".rail-btn[data-pane]")).map((b) => [b.getAttribute("data-pane"), b.textContent]));
// the notes page's own empty surface: a press there forwards to the shell and arms exactly the ring's press (the detector honours data-pane-empty)
const nf2 = await frameEnding("/pane/notes/");
if (!nf2) await die("no notes frame after the kit's reload");
out.kitInjected = await nf2.waitForFunction(() => document.body.classList.contains("pane-docking") && !!window.__rompPaneGrab, null, { timeout: 15000 }).then(() => true).catch(() => false);
const nOrigin = await page.evaluate(() => { const f = document.getElementById("f-notes"); const b = f.getBoundingClientRect(); return { x: b.left + f.clientLeft, y: b.top + f.clientTop }; });
const spot = await nf2.evaluate(() => { const e = document.getElementById("empty"); if (!e) return null;   // a refused document (the held auth class) has no surface to press
  const r = e.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2, under: (document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2) || {}).id || "" }; });
out.kitSpot = spot;
if (spot) {
  await page.mouse.move(nOrigin.x + spot.x, nOrigin.y + spot.y); await frame();
  out.kitHover = await nf2.evaluate(() => ({ cls: document.body.className, cursor: getComputedStyle(document.body).cursor }));
  await page.mouse.down(); await frame();
  out.kitPressed = await page.evaluate(() => ({ pressed: window.__rompPaneDock.pressed(), dragging: window.__rompPaneDock.dragging() }));
  await page.keyboard.press("Escape"); await frame(); await page.mouse.up(); await frame();
}
// a REAL drag from the notes pane's ring into the feed's left half: the layout changes, notes docks left of the feed
const before = await rectsOf();
const nr = before["notes-pane"], fr2 = before["feed-pane"];
if (!nr || !fr2) await die("notes or feed is not a leaf: " + JSON.stringify(Object.keys(before)));
const x0 = nr.x + 3, y0 = nr.y + nr.h / 2;   // the ring: the pane element's left padding
await page.mouse.move(x0, y0); await page.mouse.down(); await frame();
// what the press landed on, for a red's message: the element under the ring's point and the kit's press, read after the down
out.kitDown = await page.evaluate(([x, y]) => { const e = document.elementFromPoint(x, y); const n = document.getElementById("notes-pane"); const b = n ? n.getBoundingClientRect() : null;
  return { under: e ? (e.id || String(e.className || e.tagName)) : null, pressed: window.__rompPaneDock.pressed(), notesNow: b ? { x: Math.round(b.left), y: Math.round(b.top), w: Math.round(b.width) } : null }; }, [x0, y0]).catch((e) => String(e));
await page.mouse.move(x0 + 14, y0 + 14, { steps: 3 }); await frame();
out.kitArmed = await page.evaluate(() => window.__rompPaneDock.dragging());
await page.mouse.move(fr2.x + fr2.w * 0.2, fr2.y + fr2.h / 2, { steps: 8 }); await frame();
out.kitZone = await page.evaluate(() => window.__rompPaneDock.zone());
out.kitOutline = await page.evaluate(() => { const o = document.getElementById("pd-outline"); return o ? { on: o.classList.contains("on"), text: o.textContent } : null; });
await page.mouse.up(); await frame();
out.kitAfterDrop = { leaves: await leavesOf(), rects: await rectsOf(), layout: await page.evaluate(() => localStorage.getItem("romp-layout")) };
if (cfg.shot) await page.screenshot({ path: cfg.shot.replace(/\.png$/, "-kit.png") });   // the kit on, the data pane docked left of the feed
// the Artifacts pane (a shipped pane the kit's old lists never named) toggled on is a leaf too
await page.evaluate(() => window.__rompPaneToggle("artifacts", true)); await frame(); await frame();
out.kitArtifacts = { leaves: await leavesOf(), rect: (await rectsOf())["artifacts-pane"] || null };

// ---- 7. a PHONE (the mobile layout: one pane at a time, the bottom tabs): a data pane's tab shows its page, loaded once by the tap ----
const mctx = await browser.newContext({ viewport: { width: 420, height: 860 }, hasTouch: true, isMobile: true });
// the pane's desktop flag OFF in this browser (a rail toggle from an earlier desktop visit): on a phone the pane shows by its TAB alone,
// so its iframe must load from the tap, never from the desktop flag (the 1922 read: a tab tapped showed a blank pane)
await mctx.addInitScript(() => { if (window.top !== window) return; try { localStorage.setItem("romp-panes", JSON.stringify({ notes: false })); } catch (e) {} });   // the top document only: an init script runs in every same-origin frame too, and would re-seed after the shell's own writes
const mp = await mctx.newPage();
out.phoneNotesDocs = [];
docsOf(mp, out.phoneNotesDocs);
const notesRequests = [];
mp.on("request", (rq) => { if (/\/pane\/notes\/(\?|$)/.test(rq.url())) notesRequests.push(rq.url()); });
await mp.goto(cfg.url);
await mp.waitForFunction(BUILT, "#mtabs button[data-pane=notes]", { timeout: 20000 }).catch(async () => { await die("no notes tab on the phone"); });
await mp.waitForTimeout(800);
out.phoneBefore = await mp.evaluate(() => ({ mobile: !!(window.__rompMobileOn && window.__rompMobileOn()), tab: document.body.getAttribute("data-tab"),
  notesSrc: document.getElementById("f-notes").getAttribute("src"), tabs: Array.from(document.querySelectorAll("#mtabs button[data-pane]")).filter((b) => !b.hidden).map((b) => b.getAttribute("data-pane")),
  notices: (() => { try { return JSON.parse(localStorage.getItem("romp:notices") || "[]").map((n) => n.kind); } catch (e) { return ["unreadable"]; } })() }));
await mp.click("#mtabs button[data-pane=notes]");
out.phoneLoaded = await mp.waitForFunction(() => { const f = document.getElementById("f-notes"); return f && f.getAttribute("src") === "/pane/notes/" && f.classList.contains("m-on"); }, null, { timeout: 10000 }).then(() => true).catch(() => false);
const mnf = await (async () => { for (let i = 0; i < 100; i++) { const f = mp.frames().find((fr) => fr.url().split("?")[0].endsWith("/pane/notes/")); if (f) return f; await mp.waitForTimeout(100); } return null; })();
if (mnf) await mnf.waitForFunction(() => !!document.getElementById("t") && !!window.__rompReload, null, { timeout: 15000 }).catch(() => {});   // the page's document and its shim, not the navigation's blank
out.phonePage = mnf ? await mnf.evaluate(() => ({ title: (document.getElementById("t") || {}).textContent || null, shim: typeof window.__rompReload, text: ((document.body || {}).innerText || "").slice(0, 120) })).catch(() => null) : null;
out.phoneAfterTap = await mp.evaluate(() => ({ tab: document.body.getAttribute("data-tab"), notesSrc: document.getElementById("f-notes").getAttribute("src"),
  visible: (() => { const r = document.getElementById("f-notes").getBoundingClientRect(); return r.width > 100 && r.height > 100; })() }));
await mp.click("#mtabs button[data-pane=chat]"); await mp.waitForTimeout(300);
await mp.click("#mtabs button[data-pane=notes]"); await mp.waitForTimeout(600);
out.phoneRequests = notesRequests.length;
await mctx.close();

// ---- 8. a PHONE at 390 by 844 with NOTHING stored: a generic pane loads by its TAB alone (the 1922 read: the gear's row tap loaded the
// tabless Artifacts page into a hidden 0x0 frame, and a reload loaded it again from the persisted rail flag) ----
const artRequests = [];
const pctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
const pp = await pctx.newPage();
pp.on("request", (rq) => { if (/\/artifacts(\?|$)/.test(rq.url())) artRequests.push(rq.url()); });
await pp.goto(cfg.url);
await pp.waitForSelector("#mtabs button[data-pane=chat]", { timeout: 20000 }).catch(async () => { await die("no phone tab bar at 390"); });
await pp.waitForTimeout(800);
await pp.evaluate(() => window.__rompOpenSettings && window.__rompOpenSettings());
let pgf = null;
for (let i = 0; i < 150 && !pgf; i++) { for (const f of pp.frames()) { if (await f.$("#rs-pane-artifacts").catch(() => null)) { pgf = f; break; } } if (!pgf) await pp.waitForTimeout(100); }
if (!pgf) await die("no settings frame on the phone");
await pgf.evaluate(() => { const i = document.getElementById("rs-pane-artifacts"); i.checked = true; i.dispatchEvent(new Event("change", { bubbles: true })); });
await pp.waitForTimeout(800);
out.phoneRowTap = await pp.evaluate(() => ({ src: document.getElementById("f-artifacts").getAttribute("src"), tab: document.body.getAttribute("data-tab"), on: document.body.classList.contains("po-artifacts"),
  panes: (() => { try { return JSON.parse(localStorage.getItem("romp:settings") || "{}").panes || null; } catch (e) { return null; } })(), requests: 0 }));
out.phoneRowTap.requests = artRequests.length;
await pctx.close();
// both flags stored and the tab remembered: a boot loads nothing and lands on the chat (the fallback for a pane with no tab)
const qctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
await qctx.addInitScript(() => { if (window.top !== window) return; try { localStorage.setItem("romp:settings", JSON.stringify({ panes: { artifacts: true } })); localStorage.setItem("romp-panes", JSON.stringify({ artifacts: true, notes: true })); localStorage.setItem("romp-mobile-tab", "artifacts"); } catch (e) {} });   // the top document only (an iframe's load would re-seed the remembered tab after the shell repaired it)
const qp = await qctx.newPage();
const bootRequests = [];
qp.on("request", (rq) => { if (/\/artifacts(\?|$)|\/pane\/notes\/(\?|$)/.test(rq.url())) bootRequests.push(rq.url()); });
await qp.goto(cfg.url);
await qp.waitForSelector("#mtabs button[data-pane=chat]", { timeout: 20000 }).catch(async () => { await die("no phone tab bar at 390 (second boot)"); });
await qp.waitForTimeout(1000);
out.phoneBoot = await qp.evaluate(() => ({ artSrc: document.getElementById("f-artifacts").getAttribute("src"), notesSrc: document.getElementById("f-notes").getAttribute("src"), tab: document.body.getAttribute("data-tab"),
  artOn: document.body.classList.contains("po-artifacts"), chatShown: document.getElementById("f-chat").classList.contains("m-on"), remembered: localStorage.getItem("romp-mobile-tab") }));
out.phoneBoot.requests = bootRequests.slice();
// the notes tab tapped (built by the shell from GET /panes: waited for, not assumed): its page loads then, once
await qp.waitForFunction(BUILT, "#mtabs button[data-pane=notes]", { timeout: 20000 }).catch(async () => { await die("no notes tab on the phone (second boot)"); });
await qp.click("#mtabs button[data-pane=notes]"); await qp.waitForTimeout(800);
out.phoneNotesTap = { notesSrc: await qp.evaluate(() => document.getElementById("f-notes").getAttribute("src")), requests: bootRequests.slice() };
await qctx.close();

// ---- 9. GET /panes answers 500: no custom pane is built, and the failure is SHOWN (desktop: the Log's entry and the gear's line;
// phone: the bar's Log mark), never an empty list passed off as the whole set. Fresh contexts, the kernel's /panes answered by the driver ----
const panesRoute = (u) => u.pathname === "/panes";
const failWith500 = (route) => route.fulfill({ status: 500, contentType: "application/json", body: "{}" });
const FAILED = () => { const rr = window.__rompPaneRecords; return !!rr && rr.state === "failed"; };
// every kind the Log's filter chips name, muted but the panes kind, and the Log emptied (the Log's own stores: its filters, its entries)
const MUTE_ALL_BUT_PANES = () => { const kinds = Array.from(document.querySelectorAll("#rerr-fgrid .rerr-fbtn")).map((b) => (Array.from(b.classList).find((c) => /^k-/.test(c)) || "").slice(2)).filter(Boolean);
  const f = {}; kinds.forEach((k) => { if (k !== "panes") f[k] = 1; }); localStorage.setItem("romp:errFilters", JSON.stringify(f)); localStorage.removeItem("romp:notices"); return kinds; };
const LOG_MARK = () => ({ lit: (() => { const m = document.getElementById("merr"); return !!m && m.classList.contains("has"); })(),
  notices: (() => { try { return JSON.parse(localStorage.getItem("romp:notices") || "[]").map((n) => n.kind); } catch (e) { return ["unreadable"]; } })() });
const fctx = await browser.newContext({ viewport: { width: 1500, height: 900 } });
await fctx.route(panesRoute, failWith500);
const fp = await fctx.newPage();
await fp.goto(cfg.url);
out.failedRead = { settled: await fp.waitForFunction(FAILED, null, { timeout: 15000 }).then(() => true).catch(() => false) };
await fp.waitForFunction(() => !!document.querySelector(".rail-btn[data-pane=chat]"), null, { timeout: 10000 }).catch(() => {});
out.failedRead.read = await readState(fp);
out.failedRead.page = await fp.evaluate(() => ({ rail: Array.from(document.querySelectorAll(".rail-btn[data-pane]")).map((b) => b.getAttribute("data-pane")),
  frames: ["docs", "lab", "notes"].filter((id) => !!document.getElementById("f-" + id)), cls: document.body.className.split(/\s+/).filter((c) => /^po-/.test(c)).sort() }));
await fp.evaluate(() => window.__rompOpenErrs && window.__rompOpenErrs());   // the Log, through the one opener every door routes to (the gear's Open log, the palette, the phone's bar)
out.failedRead.log = await fp.evaluate(() => { const back = document.getElementById("rerr-back"); return { open: !!back && !back.hidden,
  rows: Array.from(document.querySelectorAll("#rerr-list .rerr-row")).map((r) => { const c = r.querySelector(".rerr-chip");
    return { kind: c ? (Array.from(c.classList).find((k) => /^k-/.test(k)) || "") : "", chip: c ? c.textContent : "", text: (r.querySelector(".rerr-msg") || {}).textContent || "" }; }) }; });
await fp.evaluate(() => { const x = document.getElementById("rerr-x"); if (x) x.click(); });
await fp.evaluate(() => window.__rompOpenSettings && window.__rompOpenSettings("general"));   // the Panes section's tab
const fgf = await gearFrame(fp);
if (fgf) await fgf.waitForSelector("#rs-pane-artifacts", { state: "visible", timeout: 8000 }).catch(() => {});
const ROW_IDS = () => Array.from(document.querySelectorAll("#rs-panes-data input")).map((i) => i.id);
out.failedRead.gear = fgf ? { rows: await fgf.evaluate(ROW_IDS), line: await fgf.evaluate(GEAR_LINE) } : null;
await fctx.close();
const fmctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
await fmctx.route(panesRoute, failWith500);
const fmp = await fmctx.newPage();
await fmp.goto(cfg.url);
// the lab's other entries (the sdk, the usage limit) light the same mark, so every Log kind but the panes one is muted in the Log's own
// filters, the kinds read from its filter chips, and the Log emptied; then a reload. The mark lit after it is the failed read's
// alone, and leg 10's phone, whose read answers, reads the same filters unlit
out.failedPhone = { muted: await fmp.waitForFunction(() => document.querySelectorAll("#rerr-fgrid .rerr-fbtn").length > 0, null, { timeout: 10000 }).then(() => fmp.evaluate(MUTE_ALL_BUT_PANES)).catch((e) => "no filter chips: " + e) };
await fmp.reload();
out.failedPhone.settled = await fmp.waitForFunction(FAILED, null, { timeout: 15000 }).then(() => true).catch(() => false);
await fmp.waitForFunction(() => { const m = document.getElementById("merr"); return !!m && m.classList.contains("has"); }, null, { timeout: 5000 }).catch(() => {});
out.failedPhone.page = await fmp.evaluate(() => ({ mobile: !!(window.__rompMobileOn && window.__rompMobileOn()), merr: (() => { const m = document.getElementById("merr"); return !!m && m.classList.contains("has"); })(),
  tabs: Array.from(document.querySelectorAll("#mtabs button[data-pane]")).map((b) => b.getAttribute("data-pane")),
  notices: (() => { try { return JSON.parse(localStorage.getItem("romp:notices") || "[]").map((n) => n.kind); } catch (e) { return ["unreadable"]; } })() }));
await fmctx.close();

// ---- 10. a PHONE whose remembered tab is a pane defined at the kernel (the URL pane, which loads): after a reload the tab is shown once
// the read lands, and its page loads once ----
const rctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
await rctx.addInitScript(SANDBOX_WATCH);
const rp = await rctx.newPage();
const docsLoads = [];
rp.on("request", (rq) => { if (rq.resourceType() === "document" && rq.url().split("?")[0] === cfg.docsUrl) docsLoads.push(rq.url()); });
await rp.goto(cfg.url);
await rp.waitForFunction(BUILT, "#mtabs button[data-pane=docs]", { timeout: 20000 }).catch(async () => { await die("no docs tab on the phone"); });
out.restore = { firstBoot: await rp.evaluate(() => ({ tab: document.body.getAttribute("data-tab"), docsSrc: document.getElementById("f-docs").getAttribute("src") })), loadsBefore: docsLoads.length };
await rp.evaluate(() => localStorage.setItem("romp-mobile-tab", "docs"));
out.restore.muted = await rp.evaluate(MUTE_ALL_BUT_PANES);   // leg 9's filters, for the contrast: a read that answers leaves the bar's Log mark unlit
docsLoads.length = 0;
await rp.reload();
out.restore.shown = await rp.waitForFunction(() => document.body.getAttribute("data-tab") === "docs", null, { timeout: 20000 }).then(() => true).catch(() => false);
const dfr = await (async () => { for (let i = 0; i < 100; i++) { const f = rp.frames().find((fr) => fr.url().split("?")[0] === cfg.docsUrl); if (f) return f; await rp.waitForTimeout(100); } return null; })();
out.restore.frameLoaded = dfr ? await dfr.waitForLoadState("load", { timeout: 10000 }).then(() => true).catch(() => false) : false;
await rp.waitForTimeout(1500);   // a second load of the page would come in this window
out.restore.after = await rp.evaluate(() => { const f = document.getElementById("f-docs"); const b = f.getBoundingClientRect();
  return { tab: document.body.getAttribute("data-tab"), on: f.classList.contains("m-on"), src: f.getAttribute("src"), remembered: localStorage.getItem("romp-mobile-tab"), visible: b.width > 100 && b.height > 100,
    read: (window.__rompPaneRecords || {}).state || null }; });
out.restore.loads = docsLoads.slice();
out.restore.logMark = await rp.evaluate(LOG_MARK);
out.restore.sandbox = await rp.evaluate(() => window.__labSandbox || null);
await rctx.close();

// ---- 11. a define landing while the shell's GET /panes read is in flight: the driver holds the read until the define is in, then lets
// it reach the kernel. The page shows the new pane and offers no reload for the revision it shows; then a later define's offer
// arrives, the witness that the keepalive path was live all along. Every offer state is recorded from the page's first script
// (OFFER_WATCH) and every keepalive the shell's socket receives is read off the wire ----
const api = (path, init) => fetch(cfg.api + path, Object.assign({}, init || {}, { headers: Object.assign({ "X-Romp-Token": cfg.token }, (init && init.headers) || {}) })).then((r) => r.json());
const define = (rec) => api("/pane", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(rec) });
const hctx = await browser.newContext({ viewport: { width: 1500, height: 900 } });
await hctx.addInitScript(OFFER_WATCH);
let release, sawRead;
const held = new Promise((r) => { release = r; });
const readSeen = new Promise((r) => { sawRead = r; });
await hctx.route(panesRoute, async (route) => { sawRead(true); await held; await route.continue(); });
const hp = await hctx.newPage();
const kas = [];
hp.on("websocket", (ws) => { if (!/\/ws\?app=shell/.test(ws.url())) return;
  ws.on("framereceived", (fr) => { try { const m = JSON.parse(typeof fr.payload === "string" ? fr.payload : fr.payload.toString()); if (m && m.type === "ka") kas.push({ t: Date.now(), pv: String(m.pv || "") }); } catch (e) { /* not json */ } }); });
out.held = { rev0: (await api("/panes")).rev };
const nav = hp.goto(cfg.url).catch((e) => "goto: " + e);
out.held.readHeld = await Promise.race([readSeen, new Promise((r) => setTimeout(() => r(false), 15000))]);
out.held.define = await define({ id: "held", title: "Held", source: "/feed", on: true });
const afterHeld = await api("/panes");
out.held.rev1 = afterHeld.rev;
out.held.listed = afterHeld.panes.map((p) => p.id);
release();
const navDone = await nav;
out.held.nav = typeof navDone === "string" ? navDone : "ok";
out.held.built = await hp.waitForFunction(BUILT, ".rail-btn[data-pane=held]", { timeout: 20000 }).then(() => true).catch(() => false);
const builtAt = Date.now();
out.held.read = await readState(hp);
out.held.page = await hp.evaluate(() => { const b = document.querySelector(".rail-btn[data-pane=held]"); const f = document.getElementById("f-held");
  return { rail: !!b, hidden: b ? b.hidden : null, on: document.body.classList.contains("po-held"), src: f ? f.getAttribute("src") : "absent" }; });
// two keepalives carrying the held define's revision reach the page after the build: the first has been handled by the time the second arrives
for (let i = 0; i < 100 && kas.filter((k) => k.t > builtAt && k.pv === out.held.rev1).length < 2; i++) await hp.waitForTimeout(100);
out.held.kasAfterBuild = kas.filter((k) => k.t > builtAt).map((k) => (k.pv === out.held.rev1 ? "rev1" : k.pv === out.held.rev0 ? "rev0" : k.pv ? "other" : "none"));
out.held.offersBeforeWitness = await hp.evaluate(() => (window.__labOffers || []).map((e) => e.offer));
out.held.witness = await define({ id: "witness", title: "Witness", source: "/feed", on: false });
out.held.rev2 = (await api("/panes")).rev;
out.held.witnessOffer = await hp.waitForFunction((rev) => (window.__labOffers || []).some((e) => e.offer && e.offer.pv === rev), out.held.rev2, { timeout: 15000 }).then(() => true).catch(() => false);
out.held.offers = await hp.evaluate(() => (window.__labOffers || []).map((e) => e.offer));
out.held.banner = await hp.evaluate(() => { const b = document.getElementById("rstale"); if (!b) return null;
  return { shown: b.classList.contains("show"), offer: b.classList.contains("offer"), text: b.querySelector(".rs-msg").textContent }; }).catch(() => null);
await hctx.close();

// ---- 12. a press on a gear row held while the shell's GET /panes read lands: the driver holds the read past the splash's backstop, opens
// the gear (its Panes section says it is still reading), presses the Artifacts row's box, lets the read through and releases once the
// read has landed. The section renders the read's rows again, and the press still toggles the box ----
const gctx = await browser.newContext({ viewport: { width: 1500, height: 900 } });
let releaseRead;
const readHeld = new Promise((r) => { releaseRead = r; });
await gctx.route(panesRoute, async (route) => { await readHeld; await route.continue(); });
const gp = await gctx.newPage();
await gp.goto(cfg.url);
out.press = { splashGone: await gp.waitForFunction(() => { const b = document.getElementById("romp-boot"); return !b || b.classList.contains("gone"); }, null, { timeout: 12000 }).then(() => true).catch(() => false) };
await gp.evaluate(() => window.__rompOpenSettings && window.__rompOpenSettings("general"));
let pgf2 = null;
for (let i = 0; i < 150 && !pgf2; i++) { for (const f of gp.frames()) { if (await f.$("#rs-pane-artifacts").catch(() => null)) { pgf2 = f; break; } } if (!pgf2) await gp.waitForTimeout(100); }
if (!pgf2) await die("no settings frame for the press across the read");
await pgf2.waitForSelector("#rs-pane-artifacts", { state: "visible", timeout: 8000 }).catch(() => {});
out.press.lineBefore = await pgf2.evaluate(GEAR_LINE);
out.press.before = await pgf2.evaluate(() => document.getElementById("rs-pane-artifacts").checked);
const pbox = await (await pgf2.$("#rs-pane-artifacts")).boundingBox();
await gp.mouse.move(pbox.x + pbox.width / 2, pbox.y + pbox.height / 2); await gp.mouse.down();
releaseRead();
out.press.landed = await gp.waitForFunction(() => { const rr = window.__rompPaneRecords; return !!rr && rr.state === "ok" && !!document.querySelector(".rail-btn[data-pane=notes]"); }, null, { timeout: 15000 }).then(() => true).catch(() => false);
await gp.mouse.up();
out.press.rowsAfter = await pgf2.waitForFunction(() => !!document.getElementById("rs-pane-notes"), null, { timeout: 5000 }).then(() => pgf2.evaluate(() => Array.from(document.querySelectorAll("#rs-panes-data input")).map((i) => i.id))).catch(() => null);
out.press.after = await pgf2.evaluate(() => document.getElementById("rs-pane-artifacts").checked);
out.press.saved = await gp.evaluate(() => { try { return (JSON.parse(localStorage.getItem("romp:settings") || "{}").panes || {}).artifacts === true; } catch (e) { return null; } });
await gctx.close();

// ---- 12b. the same with the keyboard: the Artifacts row's box focused, Space held while the read lands and released
// after. Space toggles a box on its keyup, so a rebuild between the keydown and the keyup loses the toggle unless the
// section holds it; the rebuild then puts the focus back on the box ----
const SPLASH_GONE = () => { const b = document.getElementById("romp-boot");
  return !b || b.classList.contains("gone"); };
const LANDED = () => { const rr = window.__rompPaneRecords;
  return !!rr && rr.state === "ok" && !!document.querySelector(".rail-btn[data-pane=notes]"); };
const settles = (p) => p.then(() => true).catch(() => false);   // a wait as a verdict: true, or false when it timed out
const kctx = await browser.newContext({ viewport: { width: 1500, height: 900 } });
let releaseKeyRead;
const keyReadHeld = new Promise((r) => { releaseKeyRead = r; });
await kctx.route(panesRoute, async (route) => { await keyReadHeld; await route.continue(); });
const kp = await kctx.newPage();
await kp.goto(cfg.url);
out.keys = { splashGone: await settles(kp.waitForFunction(SPLASH_GONE, null, { timeout: 12000 })) };
await kp.evaluate(() => window.__rompOpenSettings && window.__rompOpenSettings("general"));
const kgf = await gearFrame(kp);
if (!kgf) await die("no settings frame for the key across the read");
await kgf.waitForSelector("#rs-pane-artifacts", { state: "visible", timeout: 8000 }).catch(() => {});
out.keys.before = await kgf.evaluate(() => document.getElementById("rs-pane-artifacts").checked);
await kgf.focus("#rs-pane-artifacts");
await kp.keyboard.down("Space");
releaseKeyRead();
out.keys.landed = await settles(kp.waitForFunction(LANDED, null, { timeout: 15000 }));
await kp.keyboard.up("Space");
out.keys.rowsAfter = await kgf.waitForFunction(() => !!document.getElementById("rs-pane-notes"), null,
  { timeout: 5000 }).then(() => kgf.evaluate(ROW_IDS)).catch(() => null);
out.keys.after = await kgf.evaluate(() => document.getElementById("rs-pane-artifacts").checked);
out.keys.focus = await kgf.evaluate(() => { const a = document.activeElement; return a ? (a.id || a.tagName) : null; });
const ARTIFACTS_SAVED = () => {
  try { return (JSON.parse(localStorage.getItem("romp:settings") || "{}").panes || {}).artifacts === true; }
  catch (e) { return null; } };
out.keys.saved = await kp.evaluate(ARTIFACTS_SAVED);
await kctx.close();

// ---- 13. every consumer of the records on a page whose GET /panes read failed: the stores they write keep what a
// page whose read was in left for the panes defined at the kernel (nothing derived from the missing list is written),
// and the failure is shown (the Log's entry, the gear's line). The stores are seeded as such a page left them, the
// docking kit on and the stored layout leg 6's (the notes pane docked left of the feed); then each consumer's road that
// saves runs: the rail (a shipped pane toggled off and on), the docking kit (its start, and a real drag of the feed
// into the chat's left half), the palette (its boot, and the key bound to a defined pane's command), the gear (a hand
// row flipped off and on) and, on a phone, the tab bar (its boot, the remembered tab a defined pane's) ----
if (!out.kitAfterDrop || !out.kitAfterDrop.layout) await die("leg 6 stored no layout to seed leg 13 with");
const SEED = { "romp:settings": JSON.stringify({ paneDocking: true, panes: { lab: true, docs: false } }),
  "romp-panes": JSON.stringify({ notes: true, docs: true, lab: true }),
  "romp-pane-grow": JSON.stringify({ notes: 55, docs: 45 }), "romp-layout": out.kitAfterDrop.layout,
  "romp:keys": JSON.stringify({ "pane.notes": "Alt+N" }), "romp-mobile-tab": "docs" };
const SEEDED = (seed) => { if (window.top !== window || sessionStorage.getItem("lab-seeded")) return;
  sessionStorage.setItem("lab-seeded", "1"); for (const k of Object.keys(seed)) localStorage.setItem(k, seed[k]); };
const storesOf = (pg) => pg.evaluate((keys) => Object.fromEntries(keys.map((k) => [k, localStorage.getItem(k)])),
  Object.keys(SEED));
const KIT_ON = () => !!(window.__rompPaneDock && window.__rompPaneDock.on() && window.__rompPaneDock.layout());
const LEAVES = () => { const lay = window.__rompPaneDock.layout();
  const lv = (n) => (n.pane ? [n.pane] : n.kids.flatMap(lv)); return lay ? lv(lay.tree) : []; };
const NOTICES = () => { try { return JSON.parse(localStorage.getItem("romp:notices") || "[]").map((n) => n.kind); }
  catch (e) { return ["unreadable"]; } };
const cctx = await browser.newContext({ viewport: { width: 1500, height: 900 } });
await cctx.route(panesRoute, failWith500);
await cctx.addInitScript(SEEDED, SEED);
const cp = await cctx.newPage();
const cframe = () => cp.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
await cp.goto(cfg.url);
out.census = { settled: await settles(cp.waitForFunction(FAILED, null, { timeout: 15000 })) };
out.census.kitOn = await settles(cp.waitForFunction(KIT_ON, null, { timeout: 15000 }));
await cframe(); await cp.waitForTimeout(300);
out.census.afterBoot = await storesOf(cp);
await cp.evaluate(() => window.__rompPaneToggle("feed")); await cframe();
await cp.evaluate(() => window.__rompPaneToggle("feed")); await cframe(); await cp.waitForTimeout(200);
out.census.afterRail = await storesOf(cp);
const crects = await cp.evaluate(() => Object.fromEntries(window.__rompPaneDock.rects().map((r) => [r.pane, r.rect])));
const cfr = crects["feed-pane"], cch = crects["chat-pane"];
out.census.drag = { rects: !!(cfr && cch), before: await cp.evaluate(LEAVES) };
if (cfr && cch) {
  await cp.mouse.move(cfr.x + 3, cfr.y + cfr.h / 2); await cp.mouse.down(); await cframe();
  await cp.mouse.move(cfr.x + 17, cfr.y + cfr.h / 2 + 14, { steps: 3 }); await cframe();
  await cp.mouse.move(cch.x + cch.w * 0.2, cch.y + cch.h / 2, { steps: 8 }); await cframe();
  await cp.mouse.up(); await cframe();
}
out.census.drag.after = await cp.evaluate(LEAVES);
out.census.afterDrag = await storesOf(cp);
await cp.keyboard.press("Alt+KeyN"); await cp.waitForTimeout(200);
out.census.afterKey = await storesOf(cp);
await cp.evaluate(() => window.__rompOpenSettings && window.__rompOpenSettings("general"));
const cgf = await gearFrame(cp);
if (!cgf) await die("no settings frame on the census page");
await cgf.waitForSelector("#rs-pane-artifacts", { state: "visible", timeout: 8000 }).catch(() => {});
out.census.gearLine = await cgf.evaluate(GEAR_LINE);
for (const on of [false, true]) {
  await cgf.evaluate((v) => { const i = document.getElementById("rs-pane-timeline"); i.checked = v;
    i.dispatchEvent(new Event("change", { bubbles: true })); }, on);
  await cp.waitForTimeout(200);
}
out.census.afterGear = await storesOf(cp);
out.census.log = await cp.evaluate(NOTICES);
await cctx.close();
const cmctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
await cmctx.route(panesRoute, failWith500);
await cmctx.addInitScript(SEEDED, SEED);
const cmp = await cmctx.newPage();
await cmp.goto(cfg.url);
out.census.phone = { settled: await settles(cmp.waitForFunction(FAILED, null, { timeout: 15000 })) };
await cmp.waitForTimeout(800);
out.census.phone.page = await cmp.evaluate(() => { const m = document.getElementById("merr");
  return { mobile: !!(window.__rompMobileOn && window.__rompMobileOn()), tab: document.body.getAttribute("data-tab"),
    merr: !!m && m.classList.contains("has") }; });
out.census.phone.stores = await storesOf(cmp);
out.census.phone.log = await cmp.evaluate(NOTICES);
await cmctx.close();

fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
await browser.close();
process.exit(0);
"""


# the read's line in the gear's Panes section, on screen with its section's tab open (GEAR_LINE in the driver), but
# for its text
_LINE_SHOWN = {"role": "status", "rendered": True, "textShown": True, "sectionShown": True, "inSection": True}


class ServedPaneRegistry(unittest.TestCase):
    maxDiff = None
    ENGINE = "chromium"   # the playwright engine the driver launches; a subclass per further engine, each with a kernel of its own

    @classmethod
    def setUpClass(cls):
        if cls.ENGINE != "chromium":
            # an engine the runner does not declare is an optional leg, skipped BEFORE a kernel boots (tests/conftest.py keeps an
            # `optional:` skip a skip under ROMP_SERVED_TESTS_REQUIRE; CI declares chromium alone)
            declared = os.environ.get("ROMP_SERVED_TESTS_ENGINES", "")
            if declared and cls.ENGINE not in [e.strip() for e in declared.split(",")]:
                raise unittest.SkipTest("optional: this runner declares no %s (ROMP_SERVED_TESTS_ENGINES=%s)" % (cls.ENGINE, declared))
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            if REQUIRE:
                raise AssertionError("ROMP_SERVED_TESTS_REQUIRE=1 but the extension deps are absent")
            raise unittest.SkipTest("extension deps absent (npm ci not run here): the served leg needs them")
        cls.lab = tempfile.mkdtemp(prefix="pane-registry-")
        cls.addClassCleanup(lab_ports.release, cls.lab)   # runs on a failed setUpClass too, which skips tearDownClass
        dist = os.path.join(cls.lab, "dist")
        lab_dist.copy_dist(dist)   # the checkout's ONE build of the bundles, copied under its lock (tests/lab_dist.py)
        state = os.path.join(cls.lab, "xdg", "romp")
        cwd = os.path.join(cls.lab, "proj")
        os.makedirs(os.path.join(state, "names"), exist_ok=True)
        os.makedirs(os.path.join(state, "sdk"), exist_ok=True)
        os.makedirs(cwd, exist_ok=True)
        Path(state, "session-hosts").write_text("off\n")
        Path(state, "names", SID).write_text("web\t%s\t\t\n" % cwd)
        Path(state, "sdk", SID + ".json").write_text(json.dumps(
            {"sid": SID, "name": "web", "cwd": cwd, "mode": "auto", "effort": "high", "lastSid": SID, "alive": True}))
        Path(state, "usage.json").write_text(json.dumps({"five_hour": {"pct": 100}, "seven_day": {"pct": 10}}))
        claude = os.path.join(cls.lab, "claude")
        proj = os.path.join(claude, "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(cwd)))
        os.makedirs(proj, exist_ok=True)
        Path(proj, SID + ".jsonl").write_text(_transcript(cwd, 4))
        # the second origin: the URL pane's page
        cls.beacons = []
        cls.docs = http.server.ThreadingHTTPServer(("127.0.0.1", 0), type("_DocsServer_" + cls.ENGINE, (_DocsServer,), {"beacons": cls.beacons}))
        cls.addClassCleanup(cls.docs.server_close)
        cls.addClassCleanup(cls.docs.shutdown)   # before the start, so a failed setUpClass (which skips tearDownClass) stops the serve loop too; LIFO, then the close
        cls.docs_port = cls.docs.server_address[1]
        threading.Thread(target=cls.docs.serve_forever, daemon=True).start()
        cls.docs_url = "http://127.0.0.1:%d/docs/" % cls.docs_port
        # the registry on disk before the kernel starts: the files the define door would write
        panes = Path(state, "panes"); (panes / "notes").mkdir(parents=True)
        (panes / "notes.json").write_text(json.dumps({"id": "notes", "title": "Notes", "source": "pane:notes", "on": True, "experimental": False, "protocol": "romp"}))
        (panes / "docs.json").write_text(json.dumps({"id": "docs", "title": "Docs", "source": cls.docs_url, "on": True, "experimental": False, "protocol": "none"}))
        (panes / "lab.json").write_text(json.dumps({"id": "lab", "title": "Lab", "source": "/feed", "on": False, "experimental": True, "protocol": "romp"}))
        (panes / "notes" / "index.html").write_text(NOTES_PAGE)
        (panes / "notes" / "inner.html").write_text(INNER_PAGE)
        cls.port = lab_ports.reserve(cls.lab)
        cls.token = "testtok-paneregistry"
        cls.env = _lab.kernel_env(cls.lab, claude, dist, cls.port, cls.token,
                                  ROMP_WS_KEEPALIVE="2")                       # the pv rides the keepalive: keep the wait short
        cls.klog = os.path.join(cls.lab, "kernel.log")
        cls.kernel = subprocess.Popen([os.path.join(BIN, "romp-kernel")], stdout=open(cls.klog, "w"), stderr=subprocess.STDOUT, env=cls.env)
        why = lab_ports.wait_owned(cls.kernel, cls.env)
        if why:
            cls.kernel.kill()
            raise unittest.SkipTest("hermetic kernel never served /healthz here: " + why)

    @classmethod
    def tearDownClass(cls):
        k = getattr(cls, "kernel", None)
        if k:
            try:
                os.kill(k.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            k.wait()
        d = getattr(cls, "docs", None)
        if d:
            d.shutdown()
        lab_ports.release(getattr(cls, "lab", ""))
        shutil.rmtree(getattr(cls, "lab", ""), ignore_errors=True)

    _res = None

    def _drive(self):
        cfg = os.path.join(self.lab, "cfg.json")
        with open(cfg, "w") as f:
            json.dump({"url": "http://127.0.0.1:%d/?token=%s" % (self.port, self.token), "api": "http://127.0.0.1:%d" % self.port, "token": self.token,
                       "engine": self.ENGINE, "docsUrl": self.docs_url, "shot": os.environ.get("ROMP_LAB_SHOT") or ""}, f)
        driver = os.path.join(self.lab, "driver.mjs")
        with open(driver, "w") as f:
            f.write(DRIVER)
        try:
            p = subprocess.run(["node", driver], capture_output=True, text=True, timeout=480,
                               env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg))
        except subprocess.TimeoutExpired as e:
            so = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode()
            self.fail("driver timed out; partial output:\n%s" % so[-3000:])
        if p.returncode == 3:
            if self.ENGINE != "chromium":
                raise unittest.SkipTest("optional: no playwright %s on this machine: %s" % (self.ENGINE, p.stderr.strip()[-300:]))
            if REQUIRE:
                self.fail("ROMP_SERVED_TESTS_REQUIRE=1 but no Chromium launched: " + p.stderr[-500:])
            raise unittest.SkipTest("no playwright browser on this box: the served leg needs one")
        self.assertEqual(p.returncode, 0, "driver failed:\n" + p.stdout[-3000:] + p.stderr[-3000:])
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
        self.assertIsNotNone(line, "driver printed no result:\n" + p.stdout[-3000:])
        r = json.loads(line[len("RESULT:"):])
        self.assertNotIn("died", r, "driver aborted early: %r" % r)
        return r

    def _result(self):
        # one drive per class (the driver runs every leg in one browser session); a failure, a skip or a launch error is cached
        # and re-raised by every test, so the record is measured once and each leg's verdict stands on its own
        cls = type(self)
        if cls._res is None:
            try:
                cls._res = ("ok", self._drive())
            except Exception as e:
                cls._res = ("err", e)
        kind, val = cls._res
        if kind == "err":
            raise val
        return val

    def test_data_panes_render_dock_and_speak_the_protocol_a_url_pane_is_sandboxed_and_mute_and_a_define_offers_a_reload(self):
        r = self._result()
        # 1. the landing
        self.assertEqual([b["pane"] for b in r["rail"]], ["chat", "timeline", "fleet", "feed", "waiting", "files", "artifacts", "docs", "lab", "notes"], r["rail"])   # the fork's Waiting pane is a code pane of the registry, between the feed and the files
        by = {b["pane"]: b for b in r["rail"]}
        self.assertEqual((by["notes"]["text"], by["notes"]["hidden"], by["notes"]["on"]), ("Notes", False, True))
        self.assertEqual((by["docs"]["hidden"], by["docs"]["on"]), (False, True))
        self.assertTrue(by["lab"]["hidden"], "experimental: not in this dashboard until the gear asks: %r" % by["lab"])
        self.assertTrue(by["artifacts"]["hidden"], "the Artifacts record is experimental too (plans/panes-as-data.md phase three): hidden until the gear asks: %r" % by["artifacts"])
        # the forged messages (the URL pane's on load; a same-origin frame nested in the notes pane's): read FIRST, so a red
        # names the door that opened (the 1919 read: the shortcuts modal opened in recording mode on a forged row)
        self.assertFalse(r["afterForged"]["keysOpen"], "a forged openKeys or hotkeyConfigure must not open the shortcuts modal: %r" % r["afterForged"])
        self.assertIsNone(r["afterForged"]["tabKeys"], "a forged hotkeyConfigure must not remember a session the foreign page chose: %r" % r["afterForged"]["tabKeys"])
        # (the nested frame lives inside the notes page, so while that page's auth class is held only the URL pane's forgeries
        # run here; its load is read in test_a_state_root_pane_page_loads_only_once_its_auth_class_is_ruled)
        self.assertFalse(r["afterForged"]["fleet"], "a forged toggleFleet (the URL pane's, the nested frame's) must not open the Outline")
        self.assertFalse(any("forged" in t for t in r["afterForged"]["notices"]), "a forged notify must not reach the notification center: %r" % r["afterForged"])
        self.assertEqual(r["body"]["cls"], ["po-chat", "po-docs", "po-feed", "po-notes", "po-timeline"], r["body"])
        self.assertEqual([(a["id"], a["protocol"], a["experimental"], a["on"], a["builtin"]) for a in r["body"]["attr"]], [("artifacts", "romp", True, False, True)],
                         "the body attribute carries the shipped record the generic build renders, alone")
        self.assertEqual((r["body"]["records"] or {}).get("state"), "ok", r["body"]["records"])
        self.assertEqual([(a["id"], a["protocol"], a["experimental"], a["on"]) for a in r["body"]["records"]["rows"]],
                         [("docs", "none", False, True), ("lab", "romp", True, False), ("notes", "romp", False, True)],
                         "the data panes by id, built by the shell from GET /panes")
        # 2. the state-root pane: a shown column loading its page (the page's own reads, the shim, the theme and the broadcast, are in
        # test_a_state_root_pane_page_loads_only_once_its_auth_class_is_ruled: on this fork the route's auth class is held)
        self.assertEqual(r["notesSrc"], "/pane/notes/")
        self.assertGreater(r["notesRect"]["w"], 60, r["notesRect"]); self.assertGreater(r["notesRect"]["h"], 100)
        self.assertTrue(r["notesRect"]["rightOfChat"], "a column after the chat: %r" % r["notesRect"])
        self.assertNotEqual(r["notesRect"]["gutter"], "none", "its gutter shows between two shown columns")
        # 3. the URL pane: sandboxed, the URL as given, protocol none; its forged messages change nothing; it is told nothing
        self.assertEqual(r["docs"], {"src": self.docs_url, "sandbox": "allow-scripts allow-forms allow-popups", "proto": "none", "shown": True, "w": r["docs"]["w"]})
        self.assertGreater(r["docs"]["w"], 60)
        told = [b for b in self.beacons if "panes" in b]
        self.assertEqual(told, [], "the URL pane is outside the protocol: no broadcast reaches it")
        # 4. the gear's rows
        self.assertEqual(r["gear"], [{"id": "rs-pane-artifacts", "checked": False, "label": "Artifacts"}, {"id": "rs-pane-docs", "checked": True, "label": "Docs"},
                                     {"id": "rs-pane-lab", "checked": False, "label": "Lab"}, {"id": "rs-pane-notes", "checked": True, "label": "Notes"}],
                         "the generic rows: the shipped Artifacts record (off by default, experimental) and the data panes")
        self.assertIsNone(r["gearLine"], "the read gave its rows, so the section carries no line about the read: %r" % r["gearLine"])
        self.assertTrue(r["labAfterGear"], "the gear's row brings the experimental pane into the dashboard and on screen: %r" % {k: r[k] for k in ("labAfterGear", "labSrc", "settingsPanes")})
        self.assertEqual(r["labSrc"], "/feed", "loaded when shown")
        self.assertEqual((r["settingsPanes"] or {}).get("lab"), True, "saved under its own id in the pane set")
        self.assertEqual(r["artifactsAfterGear"], {"hidden": False, "on": True, "src": "/artifacts"},
                         "the Artifacts row turned on: the rail button shows and the pane comes on screen (the live reconcile), and only then does its iframe load: %r" % r["artifactsAfterGear"])
        # 5. a define while the page is open: the offer with the panes' wording, no self-reload, the Reload click shows it
        self.assertEqual(r["define"].get("ok"), True, r["define"])
        self.assertTrue(r["offerShown"], "the moved pane-set revision on the keepalive stands the offer: %r" % r.get("banner"))
        self.assertEqual(r["banner"], {"shown": True, "offer": True, "text": "The set of panes changed. Reload to see it.", "reload": "Reload"})
        self.assertTrue(r["probeAlive"], "an offer, never a self-reload")
        self.assertFalse(r["laterBeforeReload"], "the open page is not rewritten under the reader")
        self.assertTrue(r["reloaded"], "the Reload click reloads")
        self.assertTrue(r["afterReload"]["later"], "the fresh page carries the new pane: %r" % r["afterReload"])
        self.assertIn("po-later", r["afterReload"]["body"]["cls"], "on: true, on screen")
        self.assertFalse((r["afterReload"]["banner"] or {}).get("shown"), "nothing to say on the current page")
        # 6. the docking kit reads the list: a data pane toggled on is a tree leaf with a ring (the phase-one 0x0 fact closes)
        self.assertTrue(r["kitOn"])
        lv = r["kitLeaves"]
        self.assertIn("notes-pane", lv, "the notes pane is a leaf: %r" % lv); self.assertIn("docs-pane", lv, "the URL pane is a leaf too (only the ring, no detector)"); self.assertIn("later-pane", lv)
        self.assertEqual(lv.index("feed-pane") < lv.index("docs-pane") < lv.index("later-pane") < lv.index("notes-pane"), True, "the row's order, the rail's: %r" % lv)
        for pid in ("notes-pane", "docs-pane"):
            rc = r["kitRects"][pid]
            self.assertGreater(rc["w"], 60, "%s has a rectangle: %r" % (pid, rc)); self.assertGreater(rc["h"], 100)
            self.assertEqual((round(rc["frame"]["x"] - rc["x"]), round(rc["frame"]["y"] - rc["y"])), (6, 6), "the iframe sits inside the 6 px ring: %r" % rc)
        self.assertIn(["notes", "Notes"], r["kitTitleRail"])
        self.assertTrue(r["kitInjected"], "the detector is injected into the protocol pane's page and the kit's class is on its body")
        # (the press on the notes page's declared empty surface needs the page: held with step 2's reads)
        self.assertTrue(r["kitArmed"], "the ring's press lifts the pane after the slop: the press %r; the notes rect read before it %r; the zone %r"
                        % (r.get("kitDown"), (r.get("kitRects") or {}).get("notes-pane"), r.get("kitZone")))
        self.assertEqual(r["kitZone"], {"target": "feed-pane", "edge": "left"}, "the feed's left half-zone: %r" % r["kitZone"])
        self.assertEqual(r["kitOutline"], {"on": True, "text": "Notes"}, "the live outline names the pane by its record's title: %r" % r["kitOutline"])
        after = r["kitAfterDrop"]["leaves"]
        self.assertLess(after.index("notes-pane"), after.index("feed-pane"), "dropped into the feed's left half: notes docks left of the feed: %r" % after)
        self.assertLess(r["kitAfterDrop"]["rects"]["notes-pane"]["x"], r["kitAfterDrop"]["rects"]["feed-pane"]["x"])
        self.assertIn("notes-pane", r["kitAfterDrop"]["layout"] or "", "the layout store holds the data pane's leaf")
        self.assertIn("artifacts-pane", r["kitArtifacts"]["leaves"], "the Artifacts pane toggled on is a leaf too: %r" % r["kitArtifacts"]["leaves"])
        # 7. the phone: a data pane's tab shows its page, loaded once by the tap (the 1922 read: the tab showed a blank pane)
        pb = r["phoneBefore"]
        self.assertTrue(pb["mobile"], "the phone layout: %r" % pb); self.assertEqual(pb["tab"], "chat")
        self.assertIsNone(pb["notesSrc"], "the pane's desktop flag is off in this browser: nothing loaded before the tap, the iframe waits for its tab")
        self.assertIn("notes", pb["tabs"]); self.assertNotIn("lab", pb["tabs"], "an experimental pane has no tab")
        self.assertTrue(r["phoneLoaded"], "the tap loads the pane's page and shows it: %r" % r.get("phoneAfterTap"))
        self.assertEqual(r["phoneAfterTap"]["tab"], "notes"); self.assertTrue(r["phoneAfterTap"]["visible"], "the pane fills the phone's screen: %r" % r["phoneAfterTap"])
        # (the page's own document on the phone, its title and shim, is read with step 2's in the held test: the kernel refuses it until
        # the owner rules on the route's auth class)
        self.assertEqual(r["phoneRequests"], 1, "the page is requested once, however many times its tab is tapped: %r" % r["phoneRequests"])
        self.assertGreater((r["kitArtifacts"]["rect"] or {"w": 0})["w"], 60, "the Artifacts leaf has a rectangle: %r; after the drop: %r" % (r["kitArtifacts"], r["kitAfterDrop"]["rects"]))

    def test_a_state_root_pane_page_loads_only_once_its_auth_class_is_ruled(self):
        r = self._result()
        if PANE_ROUTE_CLASS_APPROVED is None:
            # the held class: every document load of /pane/notes/ is the kernel's refusal, on the desktop and on the phone, and the
            # frame shows the refusal's text, not the page (no title, no shim, no surface to press, no nested frame inside it)
            got = {"desktop": sorted({d["status"] for d in r["notesDocs"]}), "phone": sorted({d["status"] for d in r["phoneNotesDocs"]}),
                   "reauth": sorted({d["reauth"] for d in r["notesDocs"] + r["phoneNotesDocs"]}, key=str),
                   "text": r["notesPage"]["text"], "title": r["notesPage"].get("title"), "shim": r["notesPage"]["shim"],
                   "phoneTitle": (r["phonePage"] or {}).get("title"), "spot": r["kitSpot"], "nested": r["nestedLoaded"]}
            self.assertEqual(got, {"desktop": [403], "phone": [403], "reauth": ["1"], "text": "forbidden: session key required",
                                   "title": None, "shim": "undefined", "phoneTitle": None, "spot": None, "nested": False},
                             "the /pane/<id>/ routes stay in the fork's full auth class, held for the owner's word (fold 4 slice 2): the "
                             "shell's frame carries only the session cookie, which opens the page and static classes alone, so the kernel "
                             "refuses the state-root pane's page. When the owner rules and the kernel's class for the route is restored, set "
                             "PANE_ROUTE_CLASS_APPROVED to the ruling's date and this test expects the page to load again. Read: %r" % got)
            return
        # the class restored on the owner's word: the page loads, desktop and phone, and every read the project's lab made of it holds
        self.assertEqual(sorted({d["status"] for d in r["notesDocs"] + r["phoneNotesDocs"]}), [200], "the page loads: %r" % (r["notesDocs"] + r["phoneNotesDocs"]))
        self.assertTrue(r["nestedLoaded"], "the nested frame inside the notes pane loaded and posted: %r" % r.get("nestedLoaded"))
        self.assertEqual((r["notesPage"]["title"], r["notesPage"]["shim"], r["notesPage"]["theme"]), ("Notes", "object", True), r["notesPage"])
        self.assertTrue(r["notesHeard"], "the pane-set broadcast reaches a protocol pane: %r" % r["notesPage"])
        self.assertEqual(r["notesPage"]["on"].get("notes"), True, r["notesPage"]["on"])
        self.assertNotIn("lab", r["notesPage"]["on"], "the experimental pane is not in this dashboard's set")
        self.assertEqual(r["kitSpot"]["under"], "empty", "the press lands on the page's declared empty surface: %r" % r["kitSpot"])
        self.assertIn("pd-grab-hover", r["kitHover"]["cls"], "the open hand over the declared surface: %r" % r["kitHover"]); self.assertEqual(r["kitHover"]["cursor"], "grab")
        self.assertTrue(r["kitPressed"]["pressed"], "a press on the page's declared empty surface arms the shell's press (data-pane-empty honoured for any app): %r" % r["kitPressed"])
        self.assertEqual((r["phonePage"] or {}).get("title"), "Notes", "the page is up, its shim with it: %r" % r["phonePage"])

    def test_a_hand_row_flipped_in_the_gear_keeps_the_registry_keys(self):
        r = self._result()
        # 4b. a hand row flipped keeps the registry keys (the 1919 read): the Feed off leaves the Artifacts control and the hidden Notes pane as they were
        f = r["afterFeedFlip"]
        self.assertEqual({k: f["panes"].get(k) for k in ("feed", "artifacts", "lab", "notes")}, {"feed": False, "artifacts": True, "lab": True, "notes": False}, "the whole set survives the hand row's flip: %r" % f["panes"])
        self.assertTrue(f["feedHidden"], "the Feed's button hidden by its row")
        self.assertFalse(f["artifactsHidden"], "the Artifacts control stays (its key survived)"); self.assertTrue(f["labOn"], "the Lab pane stays on screen")
        self.assertTrue(f["notesHidden"], "the Notes pane stays hidden (its stored false survived)"); self.assertFalse(f["notesOn"])

    def test_on_a_phone_a_generic_pane_loads_by_its_tab_alone_never_by_the_desktop_flag(self):
        r = self._result()
        # 8. the phone at 390 by 844 (the 1922 read): the gear's row tap enables the tabless Artifacts pane and loads NOTHING; a boot with both
        # flags stored and the tab remembered loads nothing and lands on the chat; a tabbed pane's tap loads its page, once
        pt = r["phoneRowTap"]
        self.assertEqual((pt["panes"] or {}).get("artifacts"), True, "the row enabled the pane: %r" % pt)
        self.assertIsNone(pt["src"], "no src: a pane with no tab is never loaded on a phone: %r" % pt); self.assertEqual(pt["requests"], 0, "and nothing requested")
        self.assertEqual(pt["tab"], "chat")
        pb2 = r["phoneBoot"]
        self.assertEqual((pb2["artSrc"], pb2["notesSrc"], pb2["tab"], pb2["chatShown"]), (None, None, "chat", True), "a boot with both flags stored and artifacts remembered: nothing loaded, the chat shown: %r" % pb2)
        self.assertEqual(pb2["requests"], [], "no page requested at boot: %r" % pb2["requests"])
        self.assertEqual(pb2["remembered"], "chat", "the remembered tab is repaired to the chat")
        self.assertEqual(r["phoneNotesTap"]["notesSrc"], "/pane/notes/", "the notes tab tapped loads its page")
        self.assertEqual(len(r["phoneNotesTap"]["requests"]), 1, "once: %r" % r["phoneNotesTap"]["requests"])

    def test_a_url_panes_frame_wears_its_sandbox_before_it_has_an_address(self):
        r = self._result()
        # 3. the URL pane's frame, read by a mutation observer on the top document from before any page script (SANDBOX_WATCH): at its
        # insertion into the document it already wears the sandbox and has no src, and at its first src the sandbox is still in place
        # (the frame is made with data-src and loads when it comes on screen); the desktop column and the phone's restored tab
        for where, s in (("desktop", r["docsSandbox"]), ("phone", r["restore"]["sandbox"])):
            self.assertEqual(s, {"insert": {"sandbox": URL_SANDBOX, "src": None}, "firstSrc": {"sandbox": URL_SANDBOX, "src": self.docs_url}},
                             "%s, %s: the URL pane's frame is sandboxed from its insertion, before any address: %r" % (self.ENGINE, where, s))

    def test_a_failed_read_of_the_pane_list_builds_no_custom_pane_and_is_shown(self):
        r = self._result()
        # 9. GET /panes answered 500 (the driver's route, fresh contexts): the read is marked failed with the status, no custom pane is built
        # (no rail button, no frame, no column), the Log holds one entry of the panes kind naming the status, the gear's Panes section shows
        # the Artifacts row and the failed line in place of the defined panes' rows; on the phone the bar's Log mark is lit by that entry
        fr = r["failedRead"]
        self.assertTrue(fr["settled"], "%s: the shell's read is marked failed: %r" % (self.ENGINE, fr))
        self.assertEqual((fr["read"] or {}).get("state"), "failed", fr["read"])
        self.assertEqual((fr["read"]["status"], fr["read"]["error"], fr["read"]["rows"]), (500, "/panes answered HTTP 500", []), fr["read"])
        self.assertEqual(fr["page"]["rail"], ["chat", "timeline", "fleet", "feed", "waiting", "files", "artifacts"], "the shipped panes alone: %r" % fr["page"])
        self.assertEqual(fr["page"]["frames"], [], "no frame for a pane the read did not give: %r" % fr["page"])
        self.assertEqual([c for c in fr["page"]["cls"] if c in ("po-docs", "po-lab", "po-notes")], [], fr["page"])
        self.assertTrue(fr["log"]["open"], "the Log opened: %r" % fr["log"])
        panes = [row for row in fr["log"]["rows"] if row["kind"] == "k-panes"]
        self.assertEqual(panes, [{"kind": "k-panes", "chip": "panes missing",
                                  "text": "Couldn't read the panes defined at the kernel (/panes answered HTTP 500), so they are missing from this page. Reload to try again."}],
                         "%s: one Log entry of its own kind names the failure: %r" % (self.ENGINE, fr["log"]["rows"]))
        said = "Couldn't read the panes defined at the kernel (/panes answered HTTP 500). Reload to try again."
        self.assertEqual(fr["gear"], {"rows": ["rs-pane-artifacts"], "line": dict(_LINE_SHOWN, text=said)},
                         "%s: the gear's Panes section, open on its tab, shows the shipped row and, on screen, says "
                         "the defined panes could not be read: %r" % (self.ENGINE, fr["gear"]))
        fm = r["failedPhone"]
        self.assertTrue(fm["settled"], "%s: the phone's read is marked failed: %r" % (self.ENGINE, fm))
        self.assertTrue(fm["page"]["mobile"], fm["page"])
        self.assertIn("panes", fm["muted"], "the Log's filter chips name the panes kind, the one kind left unmuted: %r" % fm["muted"])
        self.assertIn("panes", fm["page"]["notices"], "the Log holds the failure: %r" % fm["page"])
        self.assertTrue(fm["page"]["merr"], "%s: the phone bar's Log mark is lit, every other kind muted: %r" % (self.ENGINE, fm["page"]))
        self.assertEqual((r["restore"]["logMark"]["lit"], "panes" in r["restore"]["logMark"]["notices"]), (False, False),
                         "%s: the contrast, leg 10's phone under the same filters, whose read answers: the mark unlit, no entry of the kind: %r" % (self.ENGINE, r["restore"]["logMark"]))
        self.assertEqual([t for t in fm["page"]["tabs"] if t in ("docs", "lab", "notes")], [], "no tab for a pane the read did not give: %r" % fm["page"])
        self.assertNotIn("panes", r["phoneBefore"]["notices"], "a read that answers logs nothing of the kind (step 7's phone): %r" % r["phoneBefore"])

    def test_on_a_phone_a_remembered_tab_on_a_defined_pane_is_shown_once_the_list_lands(self):
        r = self._result()
        # 10. the phone: the URL pane's tab remembered, then a reload. The tab is shown once the shell has built the pane from its read, the
        # remembered key still names it, and the pane's page loads once
        rs = r["restore"]
        self.assertEqual((rs["firstBoot"], rs["loadsBefore"]), ({"tab": "chat", "docsSrc": None}, 0), "before: the chat, the URL pane unloaded: %r" % rs)
        self.assertTrue(rs["shown"], "%s: the remembered tab is shown after the reload: %r" % (self.ENGINE, rs))
        self.assertEqual(rs["after"], {"tab": "docs", "on": True, "src": self.docs_url, "remembered": "docs", "visible": True, "read": "ok"},
                         "%s: the URL pane's tab is the one shown, its page on screen: %r" % (self.ENGINE, rs["after"]))
        self.assertTrue(rs["frameLoaded"], "the page loaded: %r" % rs)
        self.assertEqual(len(rs["loads"]), 1, "%s: the page is requested once: %r" % (self.ENGINE, rs["loads"]))

    def test_a_pane_defined_while_the_list_is_read_is_built_and_offers_no_reload(self):
        r = self._result()
        # 11. a define landing while the shell's GET /panes read was held by the driver: the page shows the new pane, built from the read,
        # and no offer stands for the revision the page shows (two keepalives carrying it reached the page after the build); a later
        # define's offer then arrives, the witness that the keepalive path was live, with the panes' wording
        h = r["held"]
        self.assertIs(h["readHeld"], True, "%s: the shell's GET /panes read was in flight, held until the define was in: %r" % (self.ENGINE, h))
        self.assertEqual(h["define"].get("ok"), True, h["define"])
        self.assertIn("held", h["listed"]); self.assertNotEqual(h["rev1"], h["rev0"], "the define moved the pane set's revision")
        self.assertTrue(h["built"], "%s: the page shows the pane defined during its read: %r" % (self.ENGINE, h))
        self.assertEqual(((h["read"] or {}).get("state"), "held" in ((h["read"] or {}).get("rows") or [])), ("ok", True), h["read"])
        self.assertEqual(h["page"], {"rail": True, "hidden": False, "on": True, "src": "/feed"}, "on: true, on screen: %r" % h["page"])
        self.assertGreaterEqual(h["kasAfterBuild"].count("rev1"), 2, "%s: keepalives carrying the revision the page shows reached it after the build: %r" % (self.ENGINE, h["kasAfterBuild"]))
        self.assertEqual([o for o in h["offersBeforeWitness"] if o], [], "%s: no offer stood before the later define: %r" % (self.ENGINE, h["offersBeforeWitness"]))
        self.assertEqual([o for o in h["offers"] if o and o["pv"] == h["rev1"]], [], "%s: never an offer for the revision the page shows: %r" % (self.ENGINE, h["offers"]))
        self.assertEqual(h["witness"].get("ok"), True, h["witness"]); self.assertNotEqual(h["rev2"], h["rev1"])
        self.assertTrue(h["witnessOffer"], "%s: the later define's revision stands an offer (the keepalive path was live): %r" % (self.ENGINE, h["offers"]))
        self.assertEqual([o["text"] for o in h["offers"] if o and o["pv"] == h["rev2"]][-1:], ["The set of panes changed. Reload to see it."], h["offers"])
        self.assertEqual(h["banner"], {"shown": True, "offer": True, "text": "The set of panes changed. Reload to see it."}, h["banner"])

    def test_a_press_on_a_gear_row_held_while_the_list_lands_still_toggles_it(self):
        r = self._result()
        # 12. the read held past the splash's backstop, the gear open on its still-reading line, a press on the Artifacts row's box held
        # while the read lands: the section renders the read's rows (it re-renders on the builder's event) and the press is not lost
        # to that render (ui/CLAUDE.md, click-safe across re-renders: the render waits out the press)
        p = r["press"]
        self.assertEqual((p["lineBefore"], p["before"], p["landed"]),
                         (dict(_LINE_SHOWN, text="Still reading the panes defined at the kernel."), False, True),
                         "%s: the still-reading line is on screen before the read lands: %r" % (self.ENGINE, p))
        self.assertIn("rs-pane-notes", p["rowsAfter"] or [], "%s: the rows the read gave are rendered once the press is released: %r" % (self.ENGINE, p))
        self.assertEqual((p["after"], p["saved"]), (True, True), "%s: the press held while the read landed still toggles the row's box and saves it: %r" % (self.ENGINE, p))


    def test_a_space_held_on_a_gear_row_while_the_list_lands_still_toggles_it_and_keeps_the_focus(self):
        r = self._result()
        # 12b. the read held past the splash's backstop, the Artifacts row's box focused, Space held while the read
        # lands and released after: the section waits for the keyup, so the toggle Space makes on its keyup lands, and
        # the rebuild puts the focus back on the box
        k = r["keys"]
        self.assertEqual((k["before"], k["landed"]), (False, True), k)
        self.assertIn("rs-pane-notes", k["rowsAfter"] or [], "%s: the read's rows are rendered: %r" % (self.ENGINE, k))
        self.assertEqual((k["after"], k["saved"]), (True, True),
                         "%s: the Space held across the landing toggles the box and saves it: %r" % (self.ENGINE, k))
        self.assertEqual(k["focus"], "rs-pane-artifacts", "%s: the focus is back on the rebuilt box: %r"
                         % (self.ENGINE, k))

    def test_every_consumer_of_the_records_on_a_failed_read_shows_it_and_stores_nothing_derived_from_it(self):
        r = self._result()
        # 13. GET /panes answered 500 on a page whose stores a page with the read in left (the docking kit on, the
        # stored layout leg 6's). Each consumer's road that saves ran: the rail, the docking kit's start and a real
        # drag, the palette's boot and a bound key, the gear's hand row, the phone's tab bar. Every store still holds
        # what was seeded for the panes defined at the kernel, and the failure is shown: the Log's panes entry, the
        # gear's line on screen, the phone's mark
        c, e = r["census"], self.ENGINE
        self.assertEqual((c["settled"], c["kitOn"]), (True, True), "%s: the read failed, the kit came on: %r" % (e, c))
        self.assertEqual(c["afterBoot"]["romp-layout"], r["kitAfterDrop"]["layout"],
                         "%s: the census page's stored layout is leg 6's, the docking kit's start wrote none" % e)
        self.assertIn("notes-pane", c["afterBoot"]["romp-layout"] or "", "the seeded layout holds the notes pane")
        self.assertTrue(c["drag"]["rects"] and c["drag"]["after"] != c["drag"]["before"],
                        "%s: the drag moved the feed in the layout on screen: %r" % (e, c["drag"]))
        for step in ("afterBoot", "afterRail", "afterDrag", "afterKey", "afterGear"):
            got = c[step]
            with self.subTest(step=step):
                self.assertEqual(got["romp-layout"], r["kitAfterDrop"]["layout"],
                                 "%s, %s: the docking kit stored no layout built without the defined panes" % (e, step))
                self.assertEqual((got["romp:keys"], got["romp-pane-grow"], got["romp-mobile-tab"]),
                                 ('{"pane.notes":"Alt+N"}', '{"notes":55,"docs":45}', "docs"),
                                 "%s, %s: the bindings, the grows and the remembered tab as seeded" % (e, step))
                rail = json.loads(got["romp-panes"] or "{}")
                self.assertEqual({k: rail.get(k) for k in ("notes", "docs", "lab")},
                                 {"notes": True, "docs": True, "lab": True},
                                 "%s, %s: the rail's flags for the defined panes as seeded: %r" % (e, step, rail))
                gear = (json.loads(got["romp:settings"] or "{}") or {}).get("panes") or {}
                self.assertEqual({k: gear.get(k) for k in ("lab", "docs")}, {"lab": True, "docs": False},
                                 "%s, %s: the gear's flags for the defined panes as seeded: %r" % (e, step, gear))
        self.assertIn("panes", c["log"], "%s: the Log holds the failed read's entry: %r" % (e, c["log"]))
        line = dict(c["gearLine"] or {})
        self.assertTrue(line.pop("text", "").startswith("Couldn't read the panes defined at the kernel"), c["gearLine"])
        self.assertEqual(line, _LINE_SHOWN, "%s: the gear's line is on screen: %r" % (e, c["gearLine"]))
        ph = c["phone"]
        self.assertEqual((ph["settled"], ph["page"]["mobile"], ph["page"]["merr"], "panes" in ph["log"]),
                         (True, True, True, True),
                         "%s: the phone's read failed, the Log holds its entry, the bar's mark is lit: %r" % (e, ph))
        self.assertEqual((ph["page"]["tab"], ph["stores"]["romp-mobile-tab"]), ("chat", "docs"),
                         "%s: the phone shows the chat and keeps the remembered tab for the next load: %r" % (e, ph))
        self.assertEqual(ph["stores"]["romp-layout"], r["kitAfterDrop"]["layout"], "%s: the phone's stored layout" % e)
        rail = json.loads(ph["stores"]["romp-panes"] or "{}")
        self.assertEqual({k: rail.get(k) for k in ("notes", "docs", "lab")}, {"notes": True, "docs": True, "lab": True},
                         "%s: the phone's rail flags: %r" % (e, rail))


class ServedPaneRegistryWebKit(ServedPaneRegistry):
    """The same legs in WebKit, with a kernel of its own (setUpClass is per class), so the defines its legs make change nothing the
    Chromium class reads. An optional leg: skipped, with a reason starting `optional:`, where the runner declares no webkit in
    ROMP_SERVED_TESTS_ENGINES or the engine does not launch."""
    ENGINE = "webkit"
    _res = None


class TheBuiltBundles(unittest.TestCase):
    """The BUILT shell bundles read the shell's source check (plans/panes-as-data.md section 5): the palette and the docking kit. This
    module runs in CI's browser job with the extension built, where tests/test_pane_registry.py's source-level census cannot (the 1919
    read: its bundle leg skipped in every pytest cell, so its pass was invisible)."""

    def test_the_built_palette_and_docking_bundles_read_the_shells_check(self):
        names = ["palette-main", "panedock-main"]
        if not os.path.isdir(os.path.join(EXT, "node_modules")):
            if REQUIRE:
                raise AssertionError("ROMP_SERVED_TESTS_REQUIRE=1 but the extension deps are absent")
            raise unittest.SkipTest("extension deps absent (npm ci not run here): the built bundles cannot be read")
        tmp = tempfile.mkdtemp(prefix="pane-registry-bundles-")
        self.addCleanup(shutil.rmtree, tmp, True)
        dist = os.path.join(tmp, "dist")
        lab_dist.copy_dist(dist)   # the checkout's ONE build of the bundles, current with the sources, copied under its lock (tests/lab_dist.py)
        for n in names:
            self.assertIn("__rompPaneSourceOk", open(os.path.join(dist, n + ".js")).read(), "the built %s bundle reads the shell's check" % n)


if __name__ == "__main__":
    unittest.main()
