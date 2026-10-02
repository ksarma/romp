"""T416 (the user 2026-09-14, whose chat tab moved at once on a feed click while the feed's current-session section
took a long time to follow): THE SECTION FOLLOWS A TAB CHANGE AT ONCE, whatever surface the change came from.

Measured first on the served dashboard page (the shell with its chat and feed panes over a hermetic kernel), hop by
hop, from each of the switch's sources: a session name clicked in the feed (an openSession post), a card title
clicked in the feed (a showOnTimeline post), a tab clicked in the chat's strip, and a hot key in the chat (ArrowRight).
The hops are stamped on one clock across the frames (performance.timeOrigin + performance.now(), the same renderer):
the gesture, the feed's post, the chat's focus frame, the chat's activeTab post, the feed's activeChat frame, the
section head's name change, and the animation frame after it. The measurement at the merge base: the chat posts
within 3 ms of the gesture, the kernel relays within 4 to 22 ms of the post, the feed's rebuild takes 2 to 6 ms, and
a feed click's repaint waits for the pointer to LEAVE the clicked header or card (the hover-freeze parking the frame
as focusStale), 2.5 s in the lab and unbounded in use. The fix moves the section on the local signal: the feed's own
post (noted in the one place every jump passes) and the chat's tab change handed across the page by the shell; the
kernel's frame reconciles under a pending record.

Roads, on one landing page, in BOTH layouts (a wide viewport where the section's blocks sit in a row, a narrower one
where they stack):
  a. a session name clicked in the feed, the pointer left on the header (the natural gesture): the section repaints
     in the click's own task, before the animation frame after it and ahead of the kernel's frame, which flips nothing back;
  b. the same click, the pointer leaving the header at once;
  c. a card title clicked in the feed (the timeline jump), the pointer left on the card: as (a);
  d. a tab clicked in the chat's strip: the shell's relay of the tab reaches the feed and the section repaints between
     the first of the two signals to reach the feed's page code, the relay or the kernel's activeChat frame (handed on
     by the shim in a task of its own), and the animation frame after it (the three panes share one main thread, so
     nothing paints before the chat's switch handler and its post-switch frame return: locally the kernel's frame and
     the relay land in the same idle gap, in either order; the relay's worth is a link the frame crosses slowly; the
     claim reads the frame clock, which stretches with a loaded machine as a millisecond bound did not);
  e. ArrowRight in the chat (a hot key): as (d);
  d2, e2. the same two with the kernel's activeChat frames withheld from the feed's handler (a slow link stood in
     for): the shell's relay alone moves the section, before the animation frame after the relay;
  d3, d4. the strip click with each order forced, the other signal held until two animation frames after the first
     was handled, each road starting with no pending record (the feed's record of a switch it made whose kernel echo
     has not come; while one stands, a kernel frame for another session yields to it): the kernel's frame first (the
     section moves before the animation frame after it, and the relay, which comes after that frame, changes nothing),
     then the relay first (the relay alone moves the section, before the kernel's frame reaches the page code);
  d5. the relay first with a kernel frame built before the switch held behind it (the previous tab's echo, handed on
     after the relay): that frame disagrees with the record the relay left, yields, and moves the section by nothing;
  f. a card of a CLOSED session (the kernel knows it dead) clicked: the feed's card says closed, so the section stays;
     the chat gets its confirmRevive prompt (dismissed);
  s. the claim's shape: two shell relays in two tasks inside one animation frame (api, then web) move the head and return
     it; the observer's record reads api then web while a per-frame poll after the fact reads no move (the poll was the
     old claim on road g, red twice on CI's faster runners while the record held both values);
  g. the same click on a card the feed still marks live (its word stale by a moment): the section moves on the click
     and comes back on the kernel's answer (the chat's re-announce through the shell, the kernel's marked reaffirm
     frame), so the chat and the section agree again without a hand switch.
Red first at the merge base on (a), (b), (c), (d), (e), (d2) and (e2) in both layouts ((d) and (e) on the relay's
arrival; their frame bound held at the base too); (f) and (g) guard the closed-session path. All
fixtures synthetic (the notes-api world: web, api, tests, and a closed `old`). Skips loudly without the extension deps
or a browser.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import lab_dist
import lab_ports

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
EXT = os.path.join(ROOT, "vscode-extension")
sys.path.insert(0, HERE)
import test_ship_reship_served as _lab   # noqa: E402  the lab kernel's environment (the module, not its classes)

SID_WEB = "aaaaaaaa-4160-2222-3333-777777777777"
SID_API = "aaaaaaaa-4160-2222-3333-888888888888"
SID_TESTS = "aaaaaaaa-4160-2222-3333-999999999999"
SID_OLD = "aaaaaaaa-4160-2222-3333-000000000000"
WEB_WORKING = "cccccccc-4160-2222-3333-000000000001"
WEB_DONE = "cccccccc-4160-2222-3333-000000000002"
API_WORKING = "cccccccc-4160-2222-3333-000000000011"
API_DONE = "cccccccc-4160-2222-3333-000000000012"
TESTS_WORKING = "cccccccc-4160-2222-3333-000000000021"
OLD_DONE = "cccccccc-4160-2222-3333-000000000031"
WEB_ANCHOR = "dddddddd-4160-2222-3333-000000000001"
API_ANCHOR = "dddddddd-4160-2222-3333-000000000002"
OLD_ANCHOR = "dddddddd-4160-2222-3333-000000000003"
# The latency claims read the browser's frame clock, never a millisecond bound: the section repaints synchronously in the
# task of the signal that moves it (the click, or on a chat-side change the shell's relay or the kernel's frame), so the
# repaint lands before the animation frame that follows that signal. A bound in milliseconds (one frame for a click, two
# for a relay) held here and read 43.6 ms on a loaded CI runner for a repaint the record shows in the relay's own task;
# the frame clock stretches with the load, the bound did not. The table still prints the milliseconds for the record.


def _transcript(sid, tag, cwd, pairs):
    """`pairs` CLOSED user/assistant turns for `sid` (an open turn would invite the boot reconcile to resume it)."""
    out, parent, t = [], None, 1_700_000_000
    for i in range(pairs):
        u = "11111111-2222-4333-8444-%02x00004a%04x" % (tag, i)
        a = "11111111-2222-4333-8444-%02x00004b%04x" % (tag, i)
        ts = lambda k: time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(t + i * 60 + k))
        out.append({"type": "user", "uuid": u, "parentUuid": parent, "timestamp": ts(0), "sessionId": sid, "cwd": cwd,
                    "message": {"role": "user", "content": "please keep going with the notes-api search module (part %d)" % (i + 1)}})
        out.append({"type": "assistant", "uuid": a, "parentUuid": u, "timestamp": ts(5), "sessionId": sid, "cwd": cwd,
                    "message": {"id": "msg_lab_%d_%04d" % (tag, i), "type": "message", "role": "assistant", "model": "claude-sonnet-5",
                                "content": [{"type": "text", "text": "Note %d. The ranking pass reads its weights from the config now." % (i + 1)}],
                                "stop_reason": "end_turn"}})
        parent = a
    return "\n".join(json.dumps(r) for r in out) + "\n"


DRIVER = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const { chromium } = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
let browser;
try { browser = await chromium.launch(); } catch (e) { fs.writeSync(2, "no browser: " + e + "\n"); process.exit(3); }
const out = { layouts: {}, errors: [] };
const finish = async () => { fs.writeFileSync(cfg.out, JSON.stringify(out)); await browser.close(); process.exit(0); };
const die = async (why) => { out.died = why; await finish(); };
process.on("unhandledRejection", async (e) => { await die("unhandled: " + String(e).split("\n")[0]); });

const runLayout = async (tag, width) => {
  const L = { roads: {}, tag, width };
  out.layouts[tag] = L;
  const page = await browser.newPage({ viewport: { width, height: 900 } });
  page.on("pageerror", (e) => out.errors.push(tag + ": " + String(e)));
  // every frame: the hop clock (one clock across the frames), gesture capture, and the feed's section switched ON
  // before its first load (the view state's `focused`, the T347 switch)
  await page.addInitScript(() => {
    const abs = () => performance.timeOrigin + performance.now();
    const hops = (window.__hops = []);
    const tag = location.pathname;
    const note = (ev, extra) => hops.push(Object.assign({ f: tag, ev, t: abs() }, extra || {}));
    // the animation frame after a gesture or a relay in the feed frame: a repaint made in that task lands before it,
    // however slow the machine (the frame clock stretches with the load; a millisecond bound does not)
    const noteFrame = (ev, extra) => { if (tag === "/feed") requestAnimationFrame(() => note("frame-after:" + ev, extra)); };
    const S = WebSocket.prototype.send;
    WebSocket.prototype.send = function (d) {
      try { const m = JSON.parse(d); if (m && ["activeTab", "openSession", "showOnTimeline"].includes(m.type)) note("send:" + m.type, { id: m.id || m.sid || null }); } catch (e) {}
      return S.call(this, d);
    };
    // THE KERNEL'S FRAME HELD (a forced order: roads d4 and d5, and the settles before d3 and d4): while
    // window.__holdKernelFrame names a session, the socket's activeChat frames wait here, ahead of the shim, until
    // window.__openFrameGate runs (two animation frames after the shell's relay for that session was handled, below),
    // then go to the shim in their order, stamped recv as they do, one per animation frame: the shim hands on in one
    // task every frame it took before that task ran, and the head observer records only a name that differs from the
    // last it saw, so frames released in one task could move the section away and back with no record (d5 reads that
    // record). A frame that arrives before the animation frame after the last release joins the end of the line, so the
    // socket's order stands and the spacing holds however late a held frame's successor comes
    const heldFrames = [];
    let releasing = false;   // from a release to the first animation frame that finds nothing left to release
    window.__frameGate = null;   // null while frames are held; once open, the reason it opened
    const releaseNext = () => {
      if (!window.__frameGate) return;   // held again: what is left waits for the next opening
      const h = heldFrames.shift();
      releasing = !!h;
      if (!h) return;
      note("released:activeChat", { id: h.m.id || null, why: window.__frameGate });
      note("recv:activeChat", { id: h.m.id || null, reaffirm: !!h.m.reaffirm });
      h.fn.call(h.ws, h.ev);
      requestAnimationFrame(releaseNext);
    };
    window.__openFrameGate = (why) => {
      if (window.__frameGate) return;
      window.__frameGate = why;
      releaseNext();
    };
    const wrapIn = (fn) => function (ev) {
      try {
        const m = JSON.parse(ev.data);
        if (m && ["activeChat", "focus", "confirmRevive"].includes(m.type)) {
          if (m.type === "activeChat" && window.__dropActiveChat) { note("dropped:activeChat", { id: m.id || null }); return; }   // the socket's frame held back: a slow link
          if (m.type === "activeChat" && ((window.__holdKernelFrame && !window.__frameGate) || releasing)) { heldFrames.push({ ws: this, fn, ev, m }); note("held:activeChat", { id: m.id || null }); return; }
          note("recv:" + m.type, { id: m.id || null, reaffirm: !!m.reaffirm });
        }
      } catch (e) {}
      return fn.call(this, ev);
    };
    const AEL = WebSocket.prototype.addEventListener;
    WebSocket.prototype.addEventListener = function (type, fn, opts) { return AEL.call(this, type, type === "message" && typeof fn === "function" ? wrapIn(fn) : fn, opts); };
    const desc = Object.getOwnPropertyDescriptor(WebSocket.prototype, "onmessage");
    Object.defineProperty(WebSocket.prototype, "onmessage", { configurable: true, get() { return desc.get.call(this); },
      set(fn) { desc.set.call(this, typeof fn === "function" ? wrapIn(fn) : fn); } });
    document.addEventListener("click", (e) => { note("click", { tgt: String((e.target && (e.target.className || e.target.tagName)) || "").slice(0, 40) }); noteFrame("click"); }, true);
    // THE RELAY HELD (a forced order, road d3), on the shell page: while window.__holdShellRelay names a session, the
    // chat's activeTab posts wait here, ahead of the shell's own listener, until window.__openRelayGate runs (two animation
    // frames after the feed's page code handled the kernel's activeChat frame for that session, below), then go to the
    // shell's listener as they came (the same data, source and origin), so its relay reaches the feed after that frame
    if (tag === "/") {
      const heldPosts = [];
      window.__relayGate = null;   // null while posts are held; once open, the reason it opened
      window.__openRelayGate = (why) => {
        if (window.__relayGate) return;
        window.__relayGate = why;
        for (const h of heldPosts.splice(0)) {
          note("released:relay", { id: h.data.id || null, why });
          window.dispatchEvent(new MessageEvent("message", { data: h.data, origin: h.origin, source: h.source }));
        }
      };
      window.addEventListener("message", (e) => {
        const d = e && e.data;
        if (!window.__holdShellRelay || window.__relayGate || !d || d.romp !== "activeTab" || !e.source || e.source === window) return;
        e.stopImmediatePropagation();
        heldPosts.push({ data: d, origin: e.origin, source: e.source });
        note("held:relay", { id: d.id || null });
      }, true);
    }
    // THE FEED'S PENDING RECORD, as its messages show it (roads d3 and d4 start with none standing). feed.ts keeps the
    // record, and the session it has focused, in variables the page does not expose; every relay and every kernel frame
    // that moves them passes the listener below first, so the driver keeps a copy by the feed's own rule: a relay that
    // changes the focused session opens a record for that session and number, one for the session already focused only
    // renews a standing record's number; a kernel frame closes the record when it carries the record's session at or
    // above its number, or the kernel's reaffirm mark, and a kernel frame that finds no record standing focuses its
    // session. The feed's own clicks (roads a to c and g) open a record the copy does not see, and can leave the copy
    // and the feed disagreeing in either direction (a record standing in one and not the other) until a switch whose
    // kernel echo follows its relay, which settleEchoed makes before d3 and before d4
    const rec = (window.__feedRecord = { focused: null, pending: null });
    const idOf = (d) => (typeof d.id === "string" && d.id ? d.id : null), nonceOf = (d) => (typeof d.nonce === "number" ? d.nonce : null);
    // two signals carry a chat's tab change to the feed's page code, each in a task of its own, in either order: the
    // shell's relay ({romp:'activeChat'}, msg:activeChat) and the kernel's activeChat frame, which the shim takes in
    // ws.onmessage (recv above) and hands to the page code in a later task by a window dispatch (handoff:activeChat).
    // This capture listener runs first in either dispatch, ahead of the feed's own handler, in the same task
    window.addEventListener("message", (e) => {
      const d = e && e.data;
      if (!d) return;
      if (typeof d.romp === "string") {
        if (d.romp !== "activeTab" && d.romp !== "activeChat") return;
        note("msg:" + d.romp, { id: d.id || null });
        if (d.romp !== "activeChat") return;
        noteFrame("msg:activeChat", { id: d.id || null });
        if (tag === "/feed") {
          const id = idOf(d), nonce = nonceOf(d);
          if (id !== rec.focused) { rec.focused = id; rec.pending = { sid: id, nonce }; }
          else if (rec.pending && rec.pending.sid === id && nonce != null) rec.pending.nonce = nonce;
        }
        if (tag === "/feed" && window.__holdKernelFrame && window.__holdKernelFrame === d.id && !window.__frameGate)
          requestAnimationFrame(() => requestAnimationFrame(() => window.__openFrameGate("relay")));
      } else if (d.type === "activeChat") {
        note("handoff:activeChat", { id: d.id || null, reaffirm: !!d.reaffirm });
        noteFrame("handoff:activeChat", { id: d.id || null });
        if (tag === "/feed") {
          const id = idOf(d), nonce = nonceOf(d), p = rec.pending;
          if (p && (d.reaffirm || (id === p.sid && (p.nonce == null || nonce == null || nonce >= p.nonce)))) rec.pending = null;
          if (!rec.pending) rec.focused = id;
        }
        let top = null;
        try { top = window.parent !== window && window.parent.__holdShellRelay ? window.parent : null; } catch (x) {}
        if (tag === "/feed" && top && top.__holdShellRelay === d.id && !top.__relayGate)
          requestAnimationFrame(() => requestAnimationFrame(() => top.__openRelayGate("handoff")));
      }
    }, true);
    document.addEventListener("keydown", (e) => { note("key", { key: e.key }); noteFrame("key"); }, true);
    if (tag === "/feed" && !localStorage.getItem("romp:feedview")) localStorage.setItem("romp:feedview", JSON.stringify({ v: 1, focused: true }));
  });
  const T = 20000;
  const waitFn = async (fn, arg, why) => page.waitForFunction(fn, arg, { timeout: T }).catch(async (e) => { await die(tag + ": " + why + " (" + String(e).split("\n")[0] + ")"); });
  const waitTabs = (sids) => waitFn((sids) => {
    const f = document.getElementById("f-chat"); const d = f && f.contentDocument; if (!d) return false;
    const ids = Array.from(d.querySelectorAll("#tabs .tab[data-id]")).map((t) => t.dataset.id);
    return sids.every((s) => ids.includes(s));
  }, sids, "the chat never showed the tabs");
  const waitActive = (sid) => waitFn((sid) => {
    const f = document.getElementById("f-chat"); const d = f && f.contentDocument;
    const t = d && d.querySelector("#tabs .tab.active[data-id]"); return !!t && t.dataset.id === sid;
  }, sid, "the chat never activated " + sid);
  const chatFrame = async () => (await page.$("#f-chat")).contentFrame();
  const feedFrame = async () => (await page.$("#f-feed")).contentFrame();
  const clickTab = async (sid) => { const fr = await chatFrame(); await fr.locator('#tabs .tab[data-id="' + sid + '"]').first().click(); };
  const rectIn = (fid, sel) => page.evaluate(([fid, sel]) => {
    const f = document.getElementById(fid); const fr = f.getBoundingClientRect(); const el = f.contentDocument.querySelector(sel);
    if (!el) return null;
    const r = el.getBoundingClientRect(); return { x: fr.left + r.left, y: fr.top + r.top, w: r.width, h: r.height };
  }, [fid, sel]);
  const clickIn = async (fid, sel) => { const r = await rectIn(fid, sel); if (!r) await die("no " + sel + " in " + fid); await page.mouse.click(r.x + r.w / 2, r.y + Math.min(r.h / 2, 120)); };
  const headName = () => page.evaluate(() => { const f = document.getElementById("f-feed"); const d = f && f.contentDocument; const n = d && d.querySelector("#feed-focus .feed-focus-head .fname"); return n ? n.textContent : null; });
  const waitHead = (name, ms) => page.waitForFunction((name) => { const f = document.getElementById("f-feed"); const d = f && f.contentDocument; const n = d && d.querySelector("#feed-focus .feed-focus-head .fname"); return !!n && n.textContent === name; }, name, { timeout: ms }).then(() => true).catch(() => false);
  const clock = () => page.evaluate(() => performance.timeOrigin + performance.now());
  const hopsAll = () => page.evaluate(() => {
    const g = (id) => { const f = document.getElementById(id); return f && f.contentWindow && f.contentWindow.__hops ? f.contentWindow.__hops.slice() : []; };
    return [].concat(window.__hops || [], g("f-chat"), g("f-feed")).sort((a, b) => a.t - b.t);
  });
  const clearHops = () => page.evaluate(() => { for (const w of [window, document.getElementById("f-chat").contentWindow, document.getElementById("f-feed").contentWindow]) if (w && w.__hops) w.__hops.length = 0; });
  // the section head's name change, and the animation frame after it, stamped from inside the feed frame
  const observeHead = () => page.evaluate(() => {
    const w = document.getElementById("f-feed").contentWindow, d = w.document;
    const abs = () => w.performance.timeOrigin + w.performance.now();
    const read = () => { const n = d.querySelector("#feed-focus .feed-focus-head .fname"); return n ? n.textContent : null; };
    let last = read();
    new w.MutationObserver(() => {
      const nm = read();
      if (nm === last) return;
      last = nm;
      w.__hops.push({ f: "/feed", ev: "head", name: nm, t: abs() });
      w.requestAnimationFrame(() => w.__hops.push({ f: "/feed", ev: "head-frame", name: nm, t: abs() }));
    }).observe(d.body, { subtree: true, childList: true, characterData: true });
    return last;
  });
  // the chat's tab paint: the active tab's id changing on the strip, and the animation frame after it, from inside the chat frame
  const observeTabs = () => page.evaluate(() => {
    const w = document.getElementById("f-chat").contentWindow, d = w.document;
    const abs = () => w.performance.timeOrigin + w.performance.now();
    const read = () => { const t = d.querySelector("#tabs .tab.active[data-id]"); return t ? t.dataset.id : null; };
    let last = read();
    new w.MutationObserver(() => {
      const id = read();
      if (id === last) return;
      last = id;
      w.__hops.push({ f: "/chat", ev: "tab", id, t: abs() });
      w.requestAnimationFrame(() => w.__hops.push({ f: "/chat", ev: "tab-frame", id, t: abs() }));
    }).observe(d.getElementById("tabs") || d.body, { subtree: true, attributes: true, attributeFilter: ["class"], childList: true });
    return last;
  });
  const setDrop = (on) => page.evaluate((on) => { document.getElementById("f-feed").contentWindow.__dropActiveChat = on; }, on);
  // the forced orders' holds (roads d3 to d5, and the settles before d3 and d4), each naming the session whose other
  // signal opens it; switched off, a hold opens (anything it still holds goes on, in its order), so nothing waits past
  // its road
  const setHoldRelay = (sid) => page.evaluate((sid) => {
    if (sid) { window.__relayGate = null; window.__holdShellRelay = sid; } else { window.__openRelayGate("off"); window.__holdShellRelay = null; }
  }, sid);
  const setHoldFrame = (sid) => page.evaluate((sid) => {
    const w = document.getElementById("f-feed").contentWindow;
    if (sid) { w.__frameGate = null; w.__holdKernelFrame = sid; } else { w.__openFrameGate("off"); w.__holdKernelFrame = null; }
  }, sid);
  const waitFeedHop = (ev, sid, why) => waitFn(([ev, sid]) => (document.getElementById("f-feed").contentWindow.__hops || []).some((h) => h.ev === ev && h.id === sid), [ev, sid], why);
  // roads d3 and d4 read the order of the two signals, so each starts with no pending record standing in the feed (the
  // init script's copy): while one stands, the kernel's frame for another session yields to it and the relay moves the
  // section, whatever the order. A record standing at the start throws, naming the road, and the driver stops there
  const nameOf = (sid) => ({ [cfg.web]: "web", [cfg.api]: "api", [cfg.tests]: "tests", [cfg.old]: "old" })[sid] || String(sid);
  const mustStartClean = async (key) => {
    const p = await page.evaluate(() => document.getElementById("f-feed").contentWindow.__feedRecord.pending);
    if (p) throw new Error(tag + "/" + key + ": the road started with the feed's pending record for " + nameOf(p.sid) + " standing (number " + p.nonce + "): a switch before it had no kernel echo after its relay, and a kernel frame for another session yields to that record");
  };
  // the section's block layout: a row (the visible blocks side by side) or stacked (the container query's column direction)
  const layout = () => page.evaluate(() => {
    const f = document.getElementById("f-feed"); const d = f.contentDocument;
    const blocks = Array.from(d.querySelectorAll("#feed-focus .feed-focus-cols .feed-col")).filter((c) => { const r = c.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
    const lefts = blocks.map((c) => Math.round(c.getBoundingClientRect().left));
    const all = Array.from(d.querySelectorAll("#feed-focus .feed-focus-cols .feed-col")).map((c) => { const r = c.getBoundingClientRect(); return { cls: c.className, w: Math.round(r.width), h: Math.round(r.height), l: Math.round(r.left), t: Math.round(r.top), cards: c.querySelectorAll(".fitem").length }; });
    const cols = d.querySelector("#feed-focus .feed-focus-cols");
    const dir = cols ? getComputedStyle(cols).flexDirection : null;   // the stacked container query turns the row into a column
    const keys = (root) => root ? Array.from(root.querySelectorAll(".fitem[data-key]")).map((c) => c.dataset.key) : [];
    return { feedW: f.getBoundingClientRect().width, blocks: blocks.length, lefts, all, dir, stacked: dir === "column",
             secKeys: keys(d.getElementById("feed-focus")), boardKeys: keys(d.getElementById("feed-cols")).length };
  });
  // the synthetic board, delivered on the feed frame's own message path (the shim dispatches a socket frame the same way)
  const now = Math.floor(Date.now() / 1000);
  const ask = (itemId, sid, name, column, text, t, extra) => Object.assign({ itemId, sid, name, color: { bg: "#3a86ff", fg: "#ffffff" }, text, t, live: true,
    turnId: "turn-" + itemId.slice(-2), trgb: [30, 161, 235], column, tree: [] }, extra || {});
  const payloadOf = (oldLive) => ({ type: "feed", asks: [
      ask(cfg.webWorking, cfg.web, "web", "working", "notes-api: draft the search index", now - 60),
      ask(cfg.webDone, cfg.web, "web", "completed", "notes-api: write the index schema", now - 240, { summary: "The index schema is written; every note carries its tags as a sorted list.", summaryAnchorUuid: cfg.webAnchor }),
      ask(cfg.apiWorking, cfg.api, "api", "working", "notes-api: wire the tag filter", now - 120),
      ask(cfg.apiDone, cfg.api, "api", "completed", "notes-api: name the tag routes", now - 400, { summary: "The tag routes are named after the resource they filter.", summaryAnchorUuid: cfg.apiAnchor }),
      ask(cfg.testsWorking, cfg.tests, "tests", "working", "notes-api: cover the tag filter", now - 30),
      ask(cfg.oldDone, cfg.old, "old", "completed", "notes-api: the first index prototype", now - 9000, { live: oldLive, summary: "The first prototype indexed titles only.", summaryAnchorUuid: cfg.oldAnchor })],
    sessions: [{ sid: cfg.web, name: "web" }, { sid: cfg.api, name: "api" }, { sid: cfg.tests, name: "tests" }, { sid: cfg.old, name: "old" }],
    order: [cfg.web, cfg.api, cfg.tests, cfg.old] });
  const deliver = (m) => page.evaluate((m) => new Promise((res) => {
    const w = document.getElementById("f-feed").contentWindow;
    w.dispatchEvent(new w.MessageEvent("message", { data: m }));
    w.requestAnimationFrame(() => res(null));
  }), m);
  const park = async () => { await page.mouse.move(2, 2); await page.waitForTimeout(150); };
  const feedCard = (itemId) => '.fitem[data-key="a:' + itemId + '"]';
  // the reader's "session name in the feed": the session header's name
  const clickName = async (name) => { const fr = await feedFrame(); await fr.locator(".feed-sess-head .fname", { hasText: name }).first().click({ timeout: 8000 }); };
  const clickTitle = async (itemId) => { const fr = await feedFrame(); await fr.locator(feedCard(itemId) + " .fcard-title").first().click({ timeout: 8000 }); };
  // after a switch: the kernel's frame for `sid` has landed (or 3 s passed), then a beat; what the head says then
  const settled = async (sid) => {
    await page.waitForFunction((sid) => (document.getElementById("f-feed").contentWindow.__hops || []).some((h) => h.ev === "recv:activeChat" && h.id === sid), sid, { timeout: 3000 }).catch(() => null);
    await page.waitForTimeout(200);
    return headName();
  };
  const confirmShown = () => page.evaluate(() => { const d = document.getElementById("f-chat").contentDocument; const o = d && d.querySelector(".picker-overlay"); return o ? (o.textContent || "").slice(0, 120) : null; });
  const dismissConfirm = async () => {
    const fr = await chatFrame();
    await fr.getByRole("button", { name: "Cancel" }).first().click({ timeout: 8000 });
    await waitFn(() => { const d = document.getElementById("f-chat").contentDocument; return !(d && d.querySelector(".picker-overlay")); }, null, "the confirm never closed");
  };

  // ---- load: every live session a tab in the chat, the feed pane up with its section on ----
  await page.goto(cfg.url);
  await waitTabs([cfg.web, cfg.api, cfg.tests]);
  await waitFn(() => { const f = document.getElementById("f-feed"); const d = f && f.contentDocument; return !!(d && d.getElementById("feed-list") && f.contentWindow.acquireVsCodeApi); }, null, "the feed pane never loaded");
  await page.waitForTimeout(800);   // the feed's first payload and the activeChat frame of its ready
  await deliver(payloadOf(false));
  await waitFn((sel) => { const f = document.getElementById("f-feed"); const d = f && f.contentDocument; return !!(d && d.querySelector(sel)); }, feedCard(cfg.oldDone), "the board never showed the injected cards");
  L.sectionAtBoot = await page.evaluate(() => !!document.getElementById("f-feed").contentDocument.getElementById("feed-focus"));
  if (!L.sectionAtBoot) await die("the section is not on (the seeded view state did not take)");
  L.oldTab = await page.evaluate((old) => !!document.getElementById("f-chat").contentDocument.querySelector('#tabs .tab[data-id="' + old + '"]'), cfg.old);
  await clickTab(cfg.web); await waitActive(cfg.web); await park();
  L.headAfterBoot = await waitHead("web", 5000);
  L.headAtStart = await observeHead();
  L.tabAtStart = await observeTabs();
  L.layout = await layout();

  const road = async (key, run) => { await clearHops(); const r = await run(); r.hops = await hopsAll(); L.roads[key] = r; };
  // the section on `sid` through a real tab change: by way of another tab first when the chat already shows `sid` (after a
  // road whose section did not follow, at the merge base), so a kernel frame for `sid` always comes
  const settle = async (sid, name) => {
    const other = sid === cfg.api ? cfg.tests : cfg.api;
    await clickTab(other); await waitActive(other);
    await clickTab(sid); await waitActive(sid); await park();
    if (!(await waitHead(name, 5000))) await die("the section never settled on " + name);
    await deliver(payloadOf(false)); await park(); await clearHops();
  };
  // the section on `sid` again, by a switch away and back, every activeChat frame held from the first switch until two
  // animation frames after the relay into `sid`, and a wait for a kernel frame for `sid` handed on to the feed's page
  // code after that relay. The echo of the switch into `sid` reaches the page code after that relay as well, and closes
  // whatever record stood, whatever order the switches before it took. Without this switch a record can outlive a
  // settle: a relay that reaches the feed after its switch's kernel frame opens a record whose echo has already come
  // and gone (after a withheld echo, road e2's, the kernel frame that comes first also yields to the record still
  // standing)
  const settleEchoed = async (sid, name) => {
    const other = sid === cfg.api ? cfg.tests : cfg.api;
    await clearHops();
    await setHoldFrame(sid);
    await clickTab(other); await waitActive(other);
    await clickTab(sid); await waitActive(sid);
    await waitFn((sid) => {
      const hs = document.getElementById("f-feed").contentWindow.__hops || [];
      const i = hs.findIndex((h) => h.ev === "msg:activeChat" && h.id === sid);
      return i >= 0 && hs.slice(i + 1).some((h) => h.ev === "handoff:activeChat" && h.id === sid);
    }, sid, "the kernel's echo of the switch into " + name + " never reached the feed's page code after its relay");
    await setHoldFrame(null);
    await park();
    if (!(await waitHead(name, 5000))) await die("the section never settled on " + name);
    await deliver(payloadOf(false)); await park(); await clearHops();
  };

  // a. a session name clicked in the feed; the pointer stays on the header, as a click leaves it
  await settle(cfg.web, "web");
  await road("a_feed_name_pointer_stays", async () => {
    await clickName("api");
    const within = await waitHead("api", 2500);
    const tMove = await clock();
    const settledName = await settled(cfg.api);
    await page.mouse.move(2, 2);
    const afterLeave = await waitHead("api", 5000);
    return { within, tMove, settled: settledName, afterLeave, headNow: await headName() };
  });
  // b. the same click, the pointer leaving the header at once
  await settle(cfg.web, "web");
  await road("b_feed_name_pointer_leaves", async () => {
    await clickName("api");
    await page.mouse.move(2, 2);
    const within = await waitHead("api", 5000);
    return { within, settled: await settled(cfg.api), headNow: await headName() };
  });
  // c. a card title clicked in the feed (the timeline jump: showOnTimeline), the pointer left on the card
  await settle(cfg.web, "web");
  await road("c_feed_title_pointer_stays", async () => {
    await clickTitle(cfg.apiDone);
    const within = await waitHead("api", 2500);
    const tMove = await clock();
    const settledName = await settled(cfg.api);
    await page.mouse.move(2, 2);
    const afterLeave = await waitHead("api", 5000);
    return { within, tMove, settled: settledName, afterLeave, headNow: await headName() };
  });
  // d. a tab clicked in the chat's strip
  await settle(cfg.api, "api");
  await road("d_strip_click", async () => {
    await clickTab(cfg.web);
    const within = await waitHead("web", 5000);
    return { within, settled: await settled(cfg.web), headNow: await headName() };
  });
  // e. a hot key in the chat: ArrowRight steps to the next tab
  await settle(cfg.web, "web");
  await clickIn("f-chat", "#content");
  await page.waitForTimeout(200);
  await clearHops();
  await road("e_hot_key", async () => {
    const before = await headName();
    await page.keyboard.press("ArrowRight");
    const within = await page.waitForFunction((before) => { const d = document.getElementById("f-feed").contentDocument; const n = d && d.querySelector("#feed-focus .feed-focus-head .fname"); return !!n && n.textContent !== before; }, before, { timeout: 5000 }).then(() => true).catch(() => false);
    const to = await page.evaluate(() => { const d = document.getElementById("f-chat").contentDocument; const t = d.querySelector("#tabs .tab.active[data-id]"); return t ? t.dataset.id : null; });
    return { within, before, to, settled: await settled(to), headNow: await headName() };
  });
  // d2/e2. the same two with the kernel's activeChat frames withheld from the feed (a slow link): the shell's relay alone
  await settle(cfg.api, "api");
  await setDrop(true);
  await road("d2_strip_click_frame_withheld", async () => {
    await clickTab(cfg.web);
    const within = await waitHead("web", 1500);
    await page.waitForTimeout(300);
    return { within, headNow: await headName() };
  });
  await setDrop(false);
  await settle(cfg.web, "web");
  await clickIn("f-chat", "#content");
  await page.waitForTimeout(200);
  await setDrop(true);
  await clearHops();
  await road("e2_hot_key_frame_withheld", async () => {
    const before = await headName();
    await page.keyboard.press("ArrowRight");
    const within = await page.waitForFunction((before) => { const d = document.getElementById("f-feed").contentDocument; const n = d && d.querySelector("#feed-focus .feed-focus-head .fname"); return !!n && n.textContent !== before; }, before, { timeout: 1500 }).then(() => true).catch(() => false);
    const to = await page.evaluate(() => { const d = document.getElementById("f-chat").contentDocument; const t = d.querySelector("#tabs .tab.active[data-id]"); return t ? t.dataset.id : null; });
    await page.waitForTimeout(300);
    return { within, before, to, headNow: await headName() };
  });
  await setDrop(false);
  // d3/d4. the strip click with each order of the two signals forced, each road starting with no pending record (a
  // settle may leave one: after e2's withheld echo, or when its relays reach the feed after its kernel frames; the
  // settleEchoed after each settle closes it, and mustStartClean checks). d3, the kernel's
  // frame first: the shell holds the chat's post until two animation frames after the feed's page code handled the
  // kernel's frame, so the section moves before the animation frame after that frame and the relay, arriving later, finds
  // nothing to change. d4, the relay first: the feed's socket holds the kernel's frame until two animation frames after
  // the relay was handled, so the relay alone moves the section, before the kernel's frame reaches the page code. Two
  // frames apart because the page's clock steps by 0.1 ms: the next task could read the same stamp
  await settle(cfg.api, "api");
  await settleEchoed(cfg.api, "api");
  await setHoldRelay(cfg.web);
  await road("d3_strip_click_kernel_frame_first", async () => {
    await mustStartClean("d3");
    await clickTab(cfg.web);
    const within = await waitHead("web", 5000);
    await waitFeedHop("frame-after:msg:activeChat", cfg.web, "the held relay never reached the feed");
    return { within, settled: await settled(cfg.web), headNow: await headName() };
  });
  await setHoldRelay(null);
  await settle(cfg.api, "api");
  await settleEchoed(cfg.api, "api");
  await setHoldFrame(cfg.web);
  await road("d4_strip_click_relay_first", async () => {
    await mustStartClean("d4");
    await clickTab(cfg.web);
    const within = await waitHead("web", 5000);
    await waitFeedHop("frame-after:handoff:activeChat", cfg.web, "the held kernel frame never reached the feed's page code");
    return { within, settled: await settled(cfg.web), headNow: await headName() };
  });
  await setHoldFrame(null);
  // d5. the relay first with a kernel frame built before the switch behind it: the feed's socket holds every activeChat
  // frame from the switch into api on, so that switch's echo (api) waits with the strip click's own (web) until two
  // animation frames after the relay into web, and they reach the shim one per animation frame, api first. The road
  // starts with api's record standing, on purpose (its echo is the frame held), so it makes no start check
  await setHoldFrame(cfg.web);
  await clearHops();
  await clickTab(cfg.api); await waitActive(cfg.api); await park();
  if (!(await waitHead("api", 5000))) await die("the section never followed the switch into api before road d5");
  await waitFeedHop("held:activeChat", cfg.api, "the kernel's frame for the switch into api was never held");
  await road("d5_strip_click_relay_first_stale_frame_late", async () => {
    await clickTab(cfg.web);
    const within = await waitHead("web", 5000);
    await waitFeedHop("frame-after:handoff:activeChat", cfg.web, "the held kernel frames never reached the feed's page code");
    return { within, settled: await settled(cfg.web), headNow: await headName() };
  });
  await setHoldFrame(null);
  // f. a closed session's card, the feed's card saying closed: the section stays; the chat gets its confirmRevive
  await settle(cfg.web, "web");
  await road("f_closed_card_says_closed", async () => {
    await clickTitle(cfg.oldDone);
    await waitFn(() => !!document.getElementById("f-chat").contentDocument.querySelector(".picker-overlay"), null, "the chat never showed the confirmRevive prompt");
    const confirm = await confirmShown();
    await page.mouse.move(2, 2);
    await page.waitForTimeout(300);   // room for any movement the head would make: the observer's record is the claim
    const r = { confirm, headNow: await headName() };
    await dismissConfirm();
    return r;
  });
  // g. the same card while the feed still marks it live (stale by a moment): the section moves on the click and comes back on the kernel's answer
  await settle(cfg.web, "web");
  await deliver(payloadOf(true)); await park(); await clearHops();
  await road("g_closed_card_marked_live", async () => {
    await clickTitle(cfg.oldDone);
    // the movements are read off the observer's record, never sampled: the section moves to old and comes back to web
    // within a few milliseconds on a fast machine, inside one animation frame, where a per-frame poll never sees the
    // move (a CI runner read moved False twice while the record held both). Waiting on the record is a wait, not a claim.
    await waitFn(() => { const hs = (document.getElementById("f-feed").contentWindow.__hops || []).filter((h) => h.ev === "head").map((h) => h.name); return hs.indexOf("old") >= 0 && hs.lastIndexOf("web") > hs.indexOf("old"); }, null, "the section never moved to old and back to web");
    await waitFn(() => !!document.getElementById("f-chat").contentDocument.querySelector(".picker-overlay"), null, "the chat never showed the confirmRevive prompt");
    await page.mouse.move(2, 2);
    await page.waitForTimeout(300);
    const r = { headNow: await headName() };
    await dismissConfirm();
    return r;
  });
  await deliver(payloadOf(false));
  // s. the shape of the claim: a head that moves and returns inside one frame (two shell relays in two tasks, api then web,
  // before the next animation frame). The per-frame poll the road above used to make its claim with samples after both
  // and reads moved False for a movement that happened; the observer's record holds the sequence. Nothing but the feed
  // page is involved: the relays are synthetic and no kernel frame follows (the road is the layout's last).
  await settle(cfg.web, "web");
  await road("s_move_and_return_inside_one_frame", async () => {
    await page.evaluate(([api, web]) => new Promise((res) => {
      const w = document.getElementById("f-feed").contentWindow;
      w.dispatchEvent(new w.MessageEvent("message", { data: { romp: "activeChat", id: api, gesture: true, nonce: 91 } }));
      w.setTimeout(() => { w.dispatchEvent(new w.MessageEvent("message", { data: { romp: "activeChat", id: web, gesture: true, nonce: 92 } })); res(null); }, 0);
    }), [cfg.api, cfg.web]);
    const pollMoved = await waitHead("api", 300);   // the old claim's shape: one sample per animation frame, after the fact
    await page.waitForTimeout(100);
    return { pollMoved, headNow: await headName() };
  });
  await page.close();
};

await runLayout("row", cfg.rowWidth);
await runLayout("stacked", cfg.stackedWidth);
await finish();
"""


def _legs(hops):
    """The hop times relative to the gesture (ms), in order: the first click/key is the gesture."""
    g = next((h for h in hops if h["ev"] in ("click", "key")), hops[0] if hops else None)   # a synthetic road has no gesture: its first hop is the clock's zero
    if not g:
        return []
    return [(h["f"], h["ev"], h.get("id") or h.get("name") or h.get("key") or "", round(h["t"] - g["t"], 1), h.get("reaffirm")) for h in hops]


def _heads(road):
    """The section head's recorded names, in order: every change the feed frame's observer saw during the road."""
    return [h["name"] for h in road["hops"] if h["ev"] == "head"]


def _t(road, ev, **match):
    for h in road["hops"]:
        if h["ev"] == ev and all(h.get(k) == v for k, v in match.items()):
            return h["t"]
    return None


class FeedFocusLatencyServed(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            raise unittest.SkipTest("extension deps absent (npm ci not run here) — the served leg needs them")
        cls.lab = tempfile.mkdtemp(prefix="feedlat-")
        cls.addClassCleanup(lab_ports.release, cls.lab)   # runs on a failed setUpClass too, which skips tearDownClass
        dist = os.path.join(cls.lab, "dist")
        lab_dist.copy_dist(dist)   # the checkout's ONE build of the bundles, copied under its lock (tests/lab_dist.py)
        state = os.path.join(cls.lab, "xdg", "romp")
        cwd = os.path.join(cls.lab, "proj")
        os.makedirs(os.path.join(state, "names"), exist_ok=True)
        os.makedirs(os.path.join(state, "sdk"), exist_ok=True)
        os.makedirs(cwd, exist_ok=True)
        with open(os.path.join(state, "session-hosts"), "w") as fh:   # a lab root of its own pins the hosts OFF (CLAUDE.md 2026-09-11)
            fh.write("off\n")
        claude = os.path.join(cls.lab, "claude")
        proj = os.path.join(claude, "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(cwd)))
        os.makedirs(proj, exist_ok=True)
        # three synthetic live SDK sessions so the chat page has three tabs, and a CLOSED one (a name and a transcript, no
        # live record) for the confirmRevive roads; closed turns only, so nothing is ever resumed
        for sid, name, tag, live in [(SID_WEB, "web", 1, True), (SID_API, "api", 2, True), (SID_TESTS, "tests", 3, True), (SID_OLD, "old", 4, False)]:
            Path(state, "names", sid).write_text("%s\t%s\t\t\n" % (name, cwd))
            if live:
                Path(state, "sdk", sid + ".json").write_text(json.dumps(
                    {"sid": sid, "name": name, "cwd": cwd, "mode": "auto", "effort": "high", "lastSid": sid, "alive": True}))
            Path(proj, sid + ".jsonl").write_text(_transcript(sid, tag, cwd, 6))
        Path(state, "usage.json").write_text(json.dumps({"five_hour": {"pct": 100}, "seven_day": {"pct": 10}}))   # park sends
        cls.port = lab_ports.reserve(cls.lab)
        cls.token = "testtok-feedlat"
        env = _lab.kernel_env(cls.lab, claude, dist, cls.port, cls.token)
        cls.klog = os.path.join(cls.lab, "kernel.log")
        cls.kernel = subprocess.Popen([os.path.join(BIN, "romp-kernel")],
                                      stdout=open(cls.klog, "w"), stderr=subprocess.STDOUT, env=env)
        why = lab_ports.wait_owned(cls.kernel, env)
        if why:
            cls.kernel.kill()
            raise unittest.SkipTest("hermetic kernel never served /healthz here: " + why)
        cls.result, cls.driver_error = None, None
        cls._drive()

    @classmethod
    def _drive(cls):
        cfg = os.path.join(cls.lab, "cfg.json")
        res = os.path.join(cls.lab, "result.json")
        with open(cfg, "w") as f:
            json.dump({"url": "http://127.0.0.1:%d/?token=%s" % (cls.port, cls.token), "out": res,
                       "web": SID_WEB, "api": SID_API, "tests": SID_TESTS, "old": SID_OLD,
                       "webWorking": WEB_WORKING, "webDone": WEB_DONE, "apiWorking": API_WORKING, "apiDone": API_DONE,
                       "testsWorking": TESTS_WORKING, "oldDone": OLD_DONE, "webAnchor": WEB_ANCHOR, "apiAnchor": API_ANCHOR, "oldAnchor": OLD_ANCHOR,
                       "rowWidth": 2600, "stackedWidth": 1250}, f)
        driver = os.path.join(cls.lab, "driver.mjs")
        with open(driver, "w") as f:
            f.write(DRIVER)
        try:
            p = subprocess.run(["node", driver], capture_output=True, text=True, timeout=300,
                               env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg))
        except subprocess.TimeoutExpired as e:
            so = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode()
            cls.driver_error = "driver timed out; partial output:\n%s" % so
            return
        if p.returncode == 3:
            raise unittest.SkipTest("no playwright browser on this box — the served leg needs one (CI installs none)")
        if p.returncode != 0 or not os.path.exists(res):
            cls.driver_error = "driver failed:\n" + p.stdout[-3000:] + p.stderr[-3000:]
            return
        with open(res) as f:
            r = json.load(f)
        keep = os.environ.get("ROMP_T416_RESULT")
        if keep:
            shutil.copy(res, keep)
        if "died" in r:
            cls.driver_error = "driver aborted early: %s\n%s" % (r["died"], json.dumps(r, indent=1)[-3000:])
            return
        cls.result = r

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "kernel", None):
            cls.kernel.kill()
            cls.kernel.wait()
        lab_ports.release(getattr(cls, "lab", ""))
        shutil.rmtree(getattr(cls, "lab", ""), ignore_errors=True)

    def setUp(self):
        if self.driver_error:
            self.fail(self.driver_error)

    def test_0_measurement(self):
        """The hop table, printed for the record (pytest -s); the assertions ride the roads below."""
        r = self.result
        lines = [""]
        for tag, L in r["layouts"].items():
            lines.append("== layout %s (viewport %d): feed pane %s px, %s; headAfterBoot=%r headAtStart=%r oldTab=%r" % (
                tag, L["width"], L["layout"]["feedW"], "stacked" if L["layout"]["stacked"] else "row", L.get("headAfterBoot"), L.get("headAtStart"), L.get("oldTab")))
            for key, road in L["roads"].items():
                lines.append("-- %s: within=%r settled=%r afterLeave=%r headNow=%r" % (key, road.get("within"), road.get("settled"), road.get("afterLeave"), road.get("headNow")))
                g = next((h for h in road["hops"] if h["ev"] in ("click", "key")), None)
                for f, ev, ident, dt, re_ in _legs(road["hops"]):
                    lines.append("   %+9.1f ms  %-6s %-18s %s%s" % (dt, f, ev, ident[-12:], " (reaffirm)" if re_ else ""))
                if g and road.get("tMove"):
                    lines.append("   %+9.1f ms  (pointer moved off the card)" % (road["tMove"] - g["t"]))
        print("\n".join(lines))
        self.assertEqual(r.get("errors"), [], "the pages threw nothing: %r" % r.get("errors"))

    def _layouts(self):
        r = self.result
        row, stacked = r["layouts"]["row"], r["layouts"]["stacked"]
        self.assertFalse(row["layout"]["stacked"], "the wide viewport lays the section's blocks in a row: %r" % row["layout"])
        self.assertTrue(stacked["layout"]["stacked"], "the narrower viewport stacks them: %r" % stacked["layout"])
        return [("row", row), ("stacked", stacked)]

    def _local(self, tag, key, road, target, gesture_ev):
        """The section repainted to `target` in the gesture's own task (before the animation frame after the click) and AHEAD
        of the kernel's frame; the frame flipped nothing back. The gesture is the feed's own click: the section moves on it."""
        legs = "\n".join("%+9.1f ms %s %s %s%s" % (dt, f, ev, ident, " reaffirm" if re_ else "") for f, ev, ident, dt, re_ in _legs(road["hops"]))
        head = _t(road, "head", name=target)
        self.assertIsNotNone(head, "%s/%s: the section never repainted to %s while the pointer stayed put:\n%s" % (tag, key, target, legs))
        ref = _t(road, gesture_ev, f="/feed")
        self.assertIsNotNone(ref, "%s/%s: no %s hop:\n%s" % (tag, key, gesture_ev, legs))
        after = _t(road, "frame-after:" + gesture_ev)
        self.assertIsNotNone(after, "%s/%s: no animation frame recorded after the %s:\n%s" % (tag, key, gesture_ev, legs))
        self.assertTrue(ref <= head <= after, "%s/%s: the repaint did not land in the %s's own task, before the animation frame after it (%.1f ms after it):\n%s" % (tag, key, gesture_ev, head - ref, legs))
        recvs = [h["t"] for h in road["hops"] if h["ev"] == "recv:activeChat" and h["f"] == "/feed"]
        self.assertTrue(recvs, "%s/%s: the kernel's frame never arrived:\n%s" % (tag, key, legs))
        self.assertLess(head, min(recvs), "%s/%s: the section moved on the kernel's frame, not on the local signal:\n%s" % (tag, key, legs))
        self.assertEqual(road["settled"], target, "%s/%s: the kernel's frame flipped the section back: %r" % (tag, key, road["settled"]))

    def test_1_a_session_name_clicked_in_the_feed_moves_the_section_at_once_with_the_pointer_left_on_the_header(self):
        for tag, L in self._layouts():
            road = L["roads"]["a_feed_name_pointer_stays"]
            self.assertTrue(road["within"], "%s: the section repainted while the pointer stayed on the clicked header (it used to wait for the pointer to leave):\n%s" % (tag, _legs(road["hops"])))
            self._local(tag, "a", road, "api", "click")
            b = L["roads"]["b_feed_name_pointer_leaves"]
            self._local(tag, "b", b, "api", "click")

    def test_2_a_card_title_clicked_in_the_feed_moves_the_section_at_once_with_the_pointer_left_on_the_card(self):
        for tag, L in self._layouts():
            road = L["roads"]["c_feed_title_pointer_stays"]
            self.assertTrue(road["within"], "%s: the section repainted while the pointer stayed on the clicked card:\n%s" % (tag, _legs(road["hops"])))
            self._local(tag, "c", road, "api", "click")

    def _chat_side(self, tag, key, road, target, sid, withheld=False):
        """A tab change made in the chat: the shell's relay reached the feed with the new tab, and the section repainted
        between the FIRST of the two signals to reach the feed's page code and the animation frame after it. The bound reads
        that frame, not the task: a repaint in a later task inside the same frame passes. The chat sends its tab on its
        socket and posts it to the shell in the same call; the shell hands the post to the feed in a task of its own (the
        relay), and the kernel relays the socket's copy back as an activeChat frame, which the feed's shim hands to the page
        code in a later task of its own (the handoff). Either task can run first. With no pending record standing (the
        latest switch the feed made has had its kernel echo, or a reaffirm), no card held under the pointer and no card
        menu open, which is how every road here drives it, the feed's handler moves the section on whichever runs first
        and the other then finds nothing to change and paints nothing, so the bound reads the first signal and not the
        relay alone (test_3c forces each order). Outside that case the rule does not hold: while a record stands, a
        kernel frame for another session yields to it and the relay moves the section; under a held card a kernel frame
        that comes first only parks the paint (feed.ts's activeChat arm marks the section stale), and the relay's
        gesture releases the park and paints in the relay's task (applyLocalFocus); with a card menu open neither signal
        paints until the menu closes. The three panes share one main thread, so nothing paints before the chat's switch
        handler and its post-switch frame return, and on a loaded machine that wait stretches; the claim reads the frame
        clock, which stretches with it. The relay's worth is a link the kernel's frame crosses slowly, which `withheld`
        stands in for (the frame never reaches the feed's handler, the relay is the only signal, and the section must
        still follow before the animation frame after the relay)."""
        legs = "\n".join("%+9.1f ms %s %s %s%s" % (dt, f, ev, ident, " reaffirm" if re_ else "") for f, ev, ident, dt, re_ in _legs(road["hops"]))
        head = _t(road, "head", name=target)
        self.assertIsNotNone(head, "%s/%s: the section never repainted to %s:\n%s" % (tag, key, target, legs))
        relay = _t(road, "msg:activeChat", id=sid, f="/feed")
        self.assertIsNotNone(relay, "%s/%s: the shell's relay of the chat's tab never reached the feed:\n%s" % (tag, key, legs))
        paint = _t(road, "tab-frame", id=sid) or _t(road, "tab", id=sid)
        self.assertIsNotNone(paint, "%s/%s: the chat's strip never showed the new tab:\n%s" % (tag, key, legs))
        after_relay = _t(road, "frame-after:msg:activeChat", id=sid)
        self.assertIsNotNone(after_relay, "%s/%s: no animation frame recorded after the relay:\n%s" % (tag, key, legs))
        handoff = _t(road, "handoff:activeChat", id=sid, f="/feed")
        # the first signal, and the animation frame after it: a frame requested in an earlier task never runs after one
        # requested in a later task, so on a tie of the page's coarse clock the earlier of the two frames is the bound
        first = relay if handoff is None else min(relay, handoff)
        afters = []
        if relay == first:
            afters.append(after_relay)
        if handoff == first:
            after_handoff = _t(road, "frame-after:handoff:activeChat", id=sid)
            self.assertIsNotNone(after_handoff, "%s/%s: no animation frame recorded after the kernel frame's handoff:\n%s" % (tag, key, legs))
            afters.append(after_handoff)
        after = min(afters)
        by = "the relay" if relay == first else "the kernel's frame"
        kernel = "absent" if handoff is None else "%+.1f ms from the relay" % (handoff - relay)
        self.assertTrue(first <= head <= after, "%s/%s: the repaint did not land between the first signal to reach the feed (%s) and the animation frame after it (the head %.1f ms after that signal; the kernel's frame %s):\n%s" % (tag, key, by, head - first, kernel, legs))
        if withheld:
            self.assertIsNotNone(_t(road, "dropped:activeChat", id=sid), "%s/%s: the kernel's frame was withheld as the road meant:\n%s" % (tag, key, legs))
            self.assertIsNone(_t(road, "recv:activeChat", id=sid), "%s/%s: no kernel frame for the new tab reached the feed's handler:\n%s" % (tag, key, legs))
            self.assertIsNone(handoff, "%s/%s: no kernel frame for the new tab was handed to the feed's page code:\n%s" % (tag, key, legs))
        else:
            self.assertEqual(road["settled"], target, "%s/%s: the kernel's frame flipped the section back: %r" % (tag, key, road["settled"]))

    def test_3_a_strip_click_and_a_hot_key_in_the_chat_move_the_section_within_one_frame_of_the_tab_change(self):
        for tag, L in self._layouts():
            d = L["roads"]["d_strip_click"]
            self._chat_side(tag, "d", d, "web", SID_WEB)
            e = L["roads"]["e_hot_key"]
            self.assertTrue(e["to"] and e["to"] != SID_WEB, "%s: ArrowRight stepped to another tab: %r" % (tag, e["to"]))
            self._chat_side(tag, "e", e, e["headNow"], e["to"])

    def test_3b_with_the_kernels_frame_withheld_the_shells_relay_alone_moves_the_section(self):
        for tag, L in self._layouts():
            d = L["roads"]["d2_strip_click_frame_withheld"]
            self.assertTrue(d["within"], "%s: the section followed the strip click with no kernel frame: %r" % (tag, d["headNow"]))
            self._chat_side(tag, "d2", d, "web", SID_WEB, withheld=True)
            e = L["roads"]["e2_hot_key_frame_withheld"]
            self.assertTrue(e["within"] and e["to"], "%s: the section followed the hot key with no kernel frame: %r" % (tag, e))
            self._chat_side(tag, "e2", e, e["headNow"], e["to"], withheld=True)

    def test_3c_whichever_signal_reaches_the_feed_first_moves_the_section(self):
        """Each order of the two signals forced on a strip click, each road starting with no pending record: the settles
        before d3 and d4 each end on a switch whose kernel echo reaches the feed after its relay, which closes any record
        left before it (e2 withholds its echo; a settle whose relays reach the feed after its kernel frames leaves one),
        and d3 and d4 stop the driver at their start if a record stands. The kernel's frame first (d3: the shell holds
        the chat's post until two animation frames after the feed's page code handled the kernel's frame): the section
        moves between that frame's handoff and the animation frame after it,
        ahead of the relay, which arrives with nothing to change; that is the order in which a bound on the relay alone
        failed though the section moved within the frame. The relay first (d4: the feed's socket holds the kernel's frame
        until two animation frames after the relay was handled): the relay alone moves the section, before the kernel's
        frame reaches the page code; with d2 and e2 (the frame never arrives) this keeps the local signal's claim proven.
        The holds keep the two signals two frames apart, so the page's clock, which steps by 0.1 ms, cannot give the
        second signal the first one's stamp."""
        for tag, L in self._layouts():
            k = L["roads"]["d3_strip_click_kernel_frame_first"]
            legs = "\n".join("%+9.1f ms %s %s %s%s" % (dt, f, ev, ident, " reaffirm" if re_ else "") for f, ev, ident, dt, re_ in _legs(k["hops"]))
            self.assertTrue(k["within"], "%s/d3: the section followed the strip click: %r" % (tag, k["headNow"]))
            self._chat_side(tag, "d3", k, "web", SID_WEB)
            handoff, after_handoff = _t(k, "handoff:activeChat", id=SID_WEB, f="/feed"), _t(k, "frame-after:handoff:activeChat", id=SID_WEB)
            relay = _t(k, "msg:activeChat", id=SID_WEB, f="/feed")
            self.assertTrue(handoff is not None and after_handoff is not None and after_handoff < relay,
                            "%s/d3: the order was forced: the relay reached the feed only after the animation frame that followed the kernel frame's handoff:\n%s" % (tag, legs))
            self.assertLess(_t(k, "head", name="web"), relay, "%s/d3: the section had moved before the relay reached the feed:\n%s" % (tag, legs))
            r = L["roads"]["d4_strip_click_relay_first"]
            legs = "\n".join("%+9.1f ms %s %s %s%s" % (dt, f, ev, ident, " reaffirm" if re_ else "") for f, ev, ident, dt, re_ in _legs(r["hops"]))
            self.assertTrue(r["within"], "%s/d4: the section followed the strip click: %r" % (tag, r["headNow"]))
            self._chat_side(tag, "d4", r, "web", SID_WEB)
            after_relay = _t(r, "frame-after:msg:activeChat", id=SID_WEB)
            handoff = _t(r, "handoff:activeChat", id=SID_WEB, f="/feed")
            self.assertTrue(handoff is not None and after_relay < handoff,
                            "%s/d4: the order was forced: the kernel's frame reached the feed's page code only after the animation frame that followed the relay:\n%s" % (tag, legs))
            self.assertLess(_t(r, "head", name="web"), handoff, "%s/d4: the relay moved the section before the kernel's frame reached the feed's page code:\n%s" % (tag, legs))

    def test_3d_a_kernel_frame_for_the_previous_tab_arriving_after_the_relay_flips_nothing_back(self):
        """What the pending record is for, driven: the relay into web first, and behind it the kernel's frame for the switch
        before (api), built before the kernel took the switch into web. The feed's socket holds every activeChat frame from
        the switch into api on and hands them to the shim one per animation frame after the relay, so the feed handles
        each in a task of its own and the head observer records any move either makes. The api frame disagrees with the
        record the relay left and yields; web's echo then closes the record; the observer records web and nothing after
        it. d4 cannot show this: its only late frame is web's own echo, which the feed skips as the session already
        focused, whether or not a disagreeing frame would yield."""
        for tag, L in self._layouts():
            r = L["roads"]["d5_strip_click_relay_first_stale_frame_late"]
            legs = "\n".join("%+9.1f ms %s %s %s%s" % (dt, f, ev, ident, " reaffirm" if re_ else "") for f, ev, ident, dt, re_ in _legs(r["hops"]))
            self.assertTrue(r["within"], "%s/d5: the section followed the strip click: %r" % (tag, r["headNow"]))
            relay = _t(r, "msg:activeChat", id=SID_WEB, f="/feed")
            stale, echo = _t(r, "handoff:activeChat", id=SID_API, f="/feed"), _t(r, "handoff:activeChat", id=SID_WEB, f="/feed")
            self.assertTrue(relay is not None and _t(r, "released:activeChat", id=SID_API) is not None and stale is not None and relay < stale,
                            "%s/d5: the kernel's frame for api was held and handed to the feed's page code after the relay into web:\n%s" % (tag, legs))
            after_stale = _t(r, "frame-after:handoff:activeChat", id=SID_API)
            self.assertTrue(echo is not None and after_stale is not None and after_stale <= echo,
                            "%s/d5: web's echo reached the page code after the animation frame that followed the api frame's handoff:\n%s" % (tag, legs))
            self.assertEqual((_heads(r), r["headNow"]), (["web"], "web"),
                             "%s/d5: the api frame, arriving after the relay into web, moved the section by nothing (the observer's record of the head reads web alone):\n%s" % (tag, legs))

    def test_4_a_closed_sessions_card_switches_nothing_and_a_stale_live_mark_comes_back_on_the_kernels_answer(self):
        for tag, L in self._layouts():
            self.assertFalse(L["oldTab"], "%s: the closed session has no tab" % tag)
            f = L["roads"]["f_closed_card_says_closed"]
            self.assertEqual((_heads(f), f["headNow"]), ([], "web"), "%s: a card the feed knows closed moves the section by nothing (the observer recorded no head change): %r" % (tag, f))
            self.assertIn("closed", f["confirm"] or "", "%s: the chat got its confirmRevive prompt: %r" % (tag, f["confirm"]))
            self.assertIsNone(_t(f, "recv:activeChat", id=SID_OLD), "%s: no frame for the closed session" % tag)
            g = L["roads"]["g_closed_card_marked_live"]
            self.assertEqual((_heads(g), g["headNow"]), (["old", "web"], "web"),
                             "%s: a card still marked live moves the section on the click and the kernel's answer brings it back, the observer's record of the head reading exactly old then web:\n%s" % (tag, _legs(g["hops"])))
            self.assertTrue(any(h["ev"] == "recv:activeChat" and h.get("reaffirm") and h["id"] == SID_WEB for h in g["hops"]),
                            "%s: the kernel's marked reaffirm frame for the standing session arrived:\n%s" % (tag, _legs(g["hops"])))

    def test_5_the_head_claim_is_the_observers_sequence_not_a_per_frame_sample(self):
        """The shape of the claim (a peer's read of two CI reds on unrelated heads): the section can move and return
        inside one animation frame, and a per-frame poll after the fact reads the move as never having happened while the
        observer's record holds both values. The road drives that case with two shell relays in two tasks."""
        for tag, L in self._layouts():
            s = L["roads"]["s_move_and_return_inside_one_frame"]
            self.assertEqual((_heads(s), s["headNow"]), (["api", "web"], "web"), "%s: the observer recorded the move and the return: %r" % (tag, _legs(s["hops"])))
            self.assertFalse(s["pollMoved"], "%s: the per-frame poll, sampling after both, never saw the move: the old claim's shape reads a real movement as none" % tag)


if __name__ == "__main__":
    unittest.main()
