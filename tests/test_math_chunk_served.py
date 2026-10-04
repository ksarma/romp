#!/usr/bin/env python3
"""KaTeX on demand in the served chat (iOS item 6, 2026-10-02): the chat's bundle carries no KaTeX, the kernel serves the
chunk like every bundle, and a formula renders once the chunk lands with the reader's place kept.

KaTeX left render.js, feed.js, files.js and waiting.js for its own bundle, dist/math-chunk.js, which math.ts loads at the
first formula a page meets through a script tag beside the page's own bundle (chunk-url.ts: same directory, same ?v= token).
Against a hermetic kernel serving the checkout's own build (tests/lab_dist.py), this module checks:
  - the chunk is served as the generic /dist route serves every bundle: text/javascript, gzip when asked, an ETag that a
    revalidation answers with a 304, Cache-Control no-cache, Vary on the encoding; the chat's render.js carries no KaTeX;
    and the dist token every page stamps counts the chunk, so a rebuild that changed the chunk alone still moves the ?v=
    the chunk's URL is derived with;
  - in the real /chat page (Chromium; WebKit where the runner declares it): a transcript with no formula fetches no chunk;
    a reply with formulas arriving live fetches it once, from the bundle's own ?v=, and shows each formula's TeX while the
    chunk is held; then, with the reader scrolled up so the formulas sit above the viewport and the scroller's own scroll
    anchoring off (overflow-anchor: none, as on the phone's WebKit, which has none), the swap to KaTeX's taller layout
    leaves the reader's top turn within 1 px of where it was, while the formulas' turn grew; and in a second page life a
    reader at the bottom when formulas arrive at the tail is still at the bottom after the swap grows the tail;
  - in the chat on a phone (Playwright's iPhone 15 context, Chromium and WebKit), with the reader partway down the reply that
    HOLDS the formulas, every formula above the viewport top in that same turn: the swap leaves the paragraph being read
    within 1 px, with the scroller's scroll anchoring off and on (render.ts keeps the reader's line inside the anchor turn,
    reading-point.ts; keeping the turn's top let the formulas push the text down by their growth, the review of iOS item 6);
    and a reload in that place, whose record is taken over KaTeX's layout, lands the paragraph within 2 px of where it was
    while the fresh page's formulas still wait (whole-pixel scroll offsets, written more than once as the fresh page settles),
    and keeps it there through the swap;
  - the same reload in a LONG transcript (the reply followed by more replies than the fresh page's tail window holds, so the
    restore lands the reply through the deep-link land's keep offset: render.ts scrollToAnchor), in both engines on the phone:
    the paragraph within 2 px while the formulas wait and after the swap (the keep offset carries the reader's line too);
  - a hidden tab (a second session, `api`, beside `web`), in both engines on the phone: the reader on the paragraph in `web`, every formula
    above it waiting, switches to `api`; the chunk lands and the swap lays the formulas out while `web` is hidden; back on `web` the
    paragraph is within 1 px of where they left it (render.ts keeps the reader's line at the switch and lands it on the next show).
  - a comment thread over a passage from prose into a formula, in both engines: while the formula waits its mark is cut at the
    formula; read right after the arrival (no frame between), the mark covers the whole passage and the formula's KaTeX root wears
    its tint (render.ts unwraps every mark in a view the arrival laid out and puts each thread back over the laid-out text);
  - a failed load and its retry, in both engines on the phone: the chunk's first answer is a 404, so every formula of the reply is its
    source, each display formula's source block with its Copy button; with the reader on a paragraph below them, a new reply's formula
    uses the retry the failure armed (the second request,
    held: nothing waits, the sources stand), and when it is served every formula is laid out, the failure's fallbacks included, with
    the paragraph within 1 px (math.ts retries a failed load; render.ts keeps the line across the success as across a first arrival).
SYNTHETIC fixtures only; skips LOUDLY without the extension deps or a Playwright browser (CI's served job installs both)."""
import gzip
import html
import json
import lab_dist
import lab_ports
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
EXT = os.path.join(ROOT, "vscode-extension")
sys.path.insert(0, HERE)
import test_ship_reship_served as _lab   # noqa: E402  the lab kernel's environment (the module, not its classes)

SID = "aaaaaaaa-1111-2222-3333-555555555555"
SID2 = "bbbbbbbb-1111-2222-3333-555555555555"   # the second session of the tests marked with_api_session
FIRST_REPLY = "The notes-api README covers install and usage; the cost is $5-$10 and $HOME stays literal."
MATH_INTRO = "Here are the three identities the tests check:"
FORMULAS = [r"\sum_{i=0}^{n} i^2 = \frac{n(n+1)(2n+1)}{6}",
            r"\int_0^1 \frac{x^2}{\sqrt{1+x^3}}\,dx = \frac{2}{3}\left(\sqrt{2}-1\right)",
            r"\prod_{k=2}^{m} \left(1 - \frac{1}{k^2}\right) = \frac{m+1}{2m}"]
FILLERS = 24
FILLER = ("Filler reply %d: the web session reran the notes-api tests and the api session read the logs; nothing here is a "
          "formula, only prose long enough to wrap across a few lines of a narrow phone column so the transcript scrolls.")
# the reply the reader is partway down: steps with inline formulas, a short display formula after each, then plain paragraphs
STEP_FORMULAS = [r"\frac{a}{b}", r"\sum_{i=1}^{n} x_i", r"\int_0^1 f(x)\,dx", r"\binom{n}{k}", r"\sqrt{\frac{a}{b}}",
                 r"\prod_{k=1}^{m} p_k", r"\frac{\partial f}{\partial x}", r"\lim_{x\to 0} g(x)"]
READS = 10
LONG_FILLERS = 110   # more replies after the math reply than the chat's tail window (render.ts WINDOW_TAIL, 80 units) renders
MARK_TID = "tid-math-1"   # the thread of the tests marked with_comment_thread
MARK_HEAD = "the ranking term"   # the prose its passage starts with, before STEP-01's first formula
MARK_TAIL = "weighs the api session"   # and the prose it ends with, after that formula
MARK_TEX = r"w_1 = \frac{a_1}{b_1}"   # STEP-01's first formula (ranking_reply)
# the user's own message in the retry case: a display formula and a fence, neither of which the highlighter dresses in a bubble
BUBBLE_ASK = "walk me through the ranking math, starting from\n\n$$s(d) = \\sum_i w_i\\,f_i(d)$$\n\n```\nscore = bm25 + 0.3 * pagerank\n```\n"


def ranking_reply():
    parts = ["Here is the notes-api ranking derivation, step by step."]
    for i, f in enumerate(STEP_FORMULAS, 1):
        parts.append("STEP-%02d: the ranking term $w_%d = \\frac{a_%d}{b_%d}$ weighs the api session's hits against the web "
                     "session's, and $\\sqrt{n_%d}$ damps the long tail of rarely read notes." % (i, i, i, i, i))
        parts.append("$$%s$$" % f)
    for j in range(1, READS + 1):
        parts.append("READ-%02d: this paragraph has no formula; it is the text a reader would be looking at further down the "
                     "same reply, after every identity above has been laid out, long enough to wrap on a phone." % j)
    return "\n\n".join(parts) + "\n"


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def reply(uuid, parent, t, text):
    return {"type": "assistant", "timestamp": iso(t), "uuid": uuid, "parentUuid": parent, "sessionId": SID,
            "message": {"role": "assistant", "model": "claude-opus-5", "stop_reason": "end_turn",
                        "content": [{"type": "text", "text": text}]}}


def jsonl(records):
    return "".join(json.dumps(r) + "\n" for r in records)


def with_api_session(test):
    """Mark a test whose kernel also serves a second session, `api` (setUp seeds it before the kernel starts; every other test's chat
    holds `web` alone, so its first formula is the first the page meets)."""
    test.api_session = True
    return test


def with_comment_thread(test):
    """Mark a test whose kernel starts with one open comment thread on the math reply `r1`: a passage running from prose (MARK_HEAD)
    through STEP-01's first formula as KaTeX lays it out into the prose after it (MARK_TAIL), as a reader's selection over the
    laid-out reply records it (setUp writes the comments store before the kernel starts)."""
    test.comment_thread = True
    return test


def katex_text(tex):
    """The text KaTeX's layout of `tex` reads as, which a reader's selection over the laid-out formula records: katex.renderToString
    under the fill's options with its tags stripped and its entities decoded, the text nodes the DOM builder writes (math.ts's fill
    uses katex.render; both serialize one tree)."""
    js = ("const k=require(process.argv[1]);process.stdout.write(k.renderToString(process.argv[2],"
          "{output:'html',trust:false,maxSize:50,throwOnError:false}));")
    p = subprocess.run(["node", "-e", js, os.path.join(EXT, "node_modules", "katex"), tex], capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise AssertionError("katex could not render %r: %s" % (tex, p.stderr[-500:]))
    return html.unescape(re.sub(r"<[^>]+>", "", p.stdout))


def mark_exact():
    return MARK_HEAD + " " + katex_text(MARK_TEX) + " " + MARK_TAIL


def norm_ws(t):
    """Whitespace runs to one space, as comments.ts matches a thread's text (a zero-width space is not whitespace there either)."""
    return re.sub(r"\s+", " ", t or "").strip()


DRIVER = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const pw = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
let browser;
try { browser = await pw[cfg.engine].launch(); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const out = {};
try {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const errors = []; page.on("pageerror", (e) => errors.push(e.message));
  const chunkReqs = [];
  let release; const held = new Promise((r) => { release = r; });
  await page.route((u) => u.pathname === "/dist/math-chunk.js", async (route) => { chunkReqs.push(route.request().url()); await held; await route.continue(); });
  await page.goto(cfg.chat);
  await page.waitForFunction((t) => (document.body.innerText || "").includes(t), cfg.firstReply, { timeout: 30000 });
  const roundTrip = () => page.evaluate(() => fetch("/healthz", { cache: "no-store" }).then(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))));
  await roundTrip();
  const count = () => page.evaluate(() => ({
    scripts: document.querySelectorAll('script[src*="math-chunk"]').length,
    waiting: document.querySelectorAll("#content .md-math-inline, #content .md-math-display").length,
    katex: document.querySelectorAll("#content .katex").length,
  }));
  out.a = Object.assign(await count(), { requests: chunkReqs.length });
  // a reply with three display formulas arrives live: the first formula asks for the chunk, held here
  const asked = page.waitForRequest((r) => new URL(r.url()).pathname === "/dist/math-chunk.js", { timeout: 30000 }).then(() => true, () => false);
  fs.appendFileSync(cfg.transcript, cfg.mathLines);
  // the formulas' turn, waiting (placeholders) or already laid out (a bundle that carries KaTeX lays them out at once)
  await page.waitForFunction((n) => document.querySelectorAll("#content .md-math-display, #content .katex-display").length >= n, cfg.formulas.length, { timeout: 30000 });
  out.b = await page.evaluate(() => {
    const els = Array.from(document.querySelectorAll("#content .md-math-display"));
    return { texts: els.map((e) => e.textContent || ""), heights: els.map((e) => e.getBoundingClientRect().height), katex: document.querySelectorAll("#content .katex").length };
  });
  if (out.b.texts.length) await asked;   // a formula that waits has asked for the chunk: the request is in, held
  out.b.requests = chunkReqs.length;
  out.chunkUrl = chunkReqs[0] || "";
  if (!chunkReqs.length) throw new Error("no formula asked for the chunk");
  // replies after it, so the formulas can sit above the reader
  fs.appendFileSync(cfg.transcript, cfg.fillerLines);
  await page.waitForFunction((t) => (document.body.innerText || "").includes(t), cfg.lastFiller, { timeout: 30000 });
  await roundTrip();
  // the phone's WebKit has no scroll anchoring: model it, then put the reader a few turns below the formulas' turn
  const placed = await page.evaluate((k) => {
    const content = document.getElementById("content");
    content.style.overflowAnchor = "none";
    const turns = Array.from(content.querySelectorAll("[data-uuid]")).filter((t) => t.offsetParent !== null);
    const mi = turns.findIndex((t) => t.querySelector(".md-math-display"));
    if (mi < 0 || mi + k >= turns.length) return { error: "turns " + turns.length + ", formulas at " + mi };
    const anchor = turns[mi + k];
    content.scrollTop += anchor.getBoundingClientRect().top - content.getBoundingClientRect().top;
    window.__anchorUuid = anchor.dataset.uuid; window.__mathUuid = turns[mi].dataset.uuid;
    return { ok: true };
  }, 4);
  if (placed.error) { out.died = placed.error; throw new Error(placed.error); }
  await roundTrip();
  const measure = () => page.evaluate(() => {
    const content = document.getElementById("content");
    const ct = content.getBoundingClientRect().top;
    const a = content.querySelector('[data-uuid="' + window.__anchorUuid + '"]');
    const m = content.querySelector('[data-uuid="' + window.__mathUuid + '"]');
    return { anchorTop: a ? a.getBoundingClientRect().top - ct : null, mathBottom: m ? m.getBoundingClientRect().bottom - ct : null,
      mathHeight: m ? m.getBoundingClientRect().height : null, scrollTop: content.scrollTop,
      atBottom: content.scrollHeight - content.clientHeight - content.scrollTop < 4 };
  });
  out.before = await measure();
  release();
  await page.waitForFunction(() => !document.querySelector("#content .md-math-inline, #content .md-math-display") && document.querySelectorAll("#content .katex").length >= 3, null, { timeout: 30000 });
  await roundTrip();
  out.after = await measure();
  out.end = Object.assign(await count(), { requests: chunkReqs.length });
  // a second page life, the reader at the bottom: formulas arriving at the tail while the chunk is held, then the swap, which
  // grows the tail under a reader in follow mode; they stay at the bottom (render.ts onMathSettled's math-fill write)
  const page2 = await browser.newPage({ viewport: { width: 390, height: 844 } });
  page2.on("pageerror", (e) => errors.push(e.message));
  let release2; const held2 = new Promise((r) => { release2 = r; });
  await page2.route((u) => u.pathname === "/dist/math-chunk.js", async (route) => { await held2; await route.continue(); });
  await page2.goto(cfg.chat);
  await page2.waitForFunction((t) => (document.body.innerText || "").includes(t), cfg.lastFiller, { timeout: 30000 });
  await page2.evaluate(() => { document.getElementById("content").style.overflowAnchor = "none"; });
  const tail = () => page2.evaluate(() => {
    const c = document.getElementById("content");
    const turns = Array.from(c.querySelectorAll("[data-uuid]")).filter((t) => t.offsetParent !== null && t.querySelector(".md-math-display, .katex-display"));
    const last = turns[turns.length - 1];
    return { atBottom: c.scrollHeight - c.clientHeight - c.scrollTop < 4, tailHeight: last ? last.getBoundingClientRect().height : null, turns: turns.length };
  });
  await page2.waitForFunction(() => { const c = document.getElementById("content"); return c.scrollHeight - c.clientHeight - c.scrollTop < 4; }, null, { timeout: 30000 });
  fs.appendFileSync(cfg.transcript, cfg.tailMathLines);
  await page2.waitForFunction((n) => document.querySelectorAll("#content .md-math-display").length >= n, 2 * cfg.formulas.length, { timeout: 30000 });
  await page2.evaluate(() => fetch("/healthz", { cache: "no-store" }).then(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))));
  out.d = { before: await tail() };
  release2();
  await page2.waitForFunction((n) => !document.querySelector("#content .md-math-inline, #content .md-math-display") && document.querySelectorAll("#content .katex").length >= n, 2 * cfg.formulas.length, { timeout: 30000 });
  await page2.evaluate(() => fetch("/healthz", { cache: "no-store" }).then(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))));
  out.d.after = await tail();
  out.errors = errors;
} catch (e) {
  out.died = out.died || String(e && e.message || e);
}
fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
await browser.close();
process.exit(0);
"""

# The reader inside the reply that holds the formulas, on a phone: Playwright's iPhone 15 context in either engine. Each variant
# is a new page life, so the formulas wait for the chunk (held here) and the swap happens with the reader in place.
DRIVER_IN_TURN = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const pw = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
let browser;
try { browser = await pw[cfg.engine].launch(); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const out = { variants: {} };
const PENDING = "#content .md-math-inline, #content .md-math-display";
try {
  const device = Object.assign({}, pw.devices["iPhone 15"]);
  delete device.defaultBrowserType;
  const ctx = await browser.newContext(device);
  const errors = [];
  const settle = (page) => page.evaluate(() => fetch("/healthz", { cache: "no-store" }).then(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))));
  const shown = (page, t) => page.waitForFunction((t) => (document.body.innerText || "").includes(t), t, { timeout: 30000 });
  const swapped = (page) => page.waitForFunction((sel) => !document.querySelector(sel) && document.querySelectorAll("#content .katex").length > 0, PENDING, { timeout: 30000 });
  // the paragraph being read, its turn and that turn's last display formula, against #content's top
  const measure = (page) => page.evaluate((marker) => {
    const c = document.getElementById("content");
    const ct = c.getBoundingClientRect().top;
    const p = Array.from(c.querySelectorAll("p")).find((e) => e.offsetParent !== null && (e.textContent || "").startsWith(marker));
    const turn = p ? p.closest("[data-uuid]") : null;
    const shown = turn ? Array.from(turn.querySelectorAll(".md-math-display, .katex-display")) : [];
    const last = shown[shown.length - 1];
    return { markerTop: p ? p.getBoundingClientRect().top - ct : null, turnTop: turn ? turn.getBoundingClientRect().top - ct : null,
      turnHeight: turn ? turn.getBoundingClientRect().height : null, lastFormulaBottom: last ? last.getBoundingClientRect().bottom - ct : null,
      pending: document.querySelectorAll("#content .md-math-inline, #content .md-math-display").length,
      katex: document.querySelectorAll("#content .katex").length, scrollTop: c.scrollTop, anchoring: getComputedStyle(c).overflowAnchor };
  }, cfg.marker);
  // the paragraph put `offset` px under #content's top, the scroller's scroll anchoring set to `mode` ("" leaves the browser's own)
  const place = (page, mode) => page.evaluate(({ marker, off, mode }) => {
    const c = document.getElementById("content");
    if (mode) c.style.overflowAnchor = mode;
    const p = Array.from(c.querySelectorAll("p")).find((e) => e.offsetParent !== null && (e.textContent || "").startsWith(marker));
    if (!p) return "no paragraph starting " + marker;
    c.scrollTop += p.getBoundingClientRect().top - c.getBoundingClientRect().top - off;
    return "";
  }, { marker: cfg.marker, off: cfg.offset, mode });
  for (const mode of ["none", ""]) {
    const page = await ctx.newPage();
    page.on("pageerror", (e) => errors.push(e.message));
    const reqs = [];
    let release; const held = new Promise((r) => { release = r; });
    await page.route((u) => u.pathname === "/dist/math-chunk.js", async (route) => { reqs.push(route.request().url()); await held; await route.continue(); });
    await page.goto(cfg.chat);
    await shown(page, cfg.lastFiller);
    await settle(page);
    const placed = await place(page, mode);
    if (placed) throw new Error(placed);
    await settle(page);
    const v = { before: await measure(page) };
    release();
    await swapped(page);
    await settle(page);
    v.after = await measure(page);
    v.requests = reqs.length;
    out.variants["in-turn-" + (mode || "auto")] = v;
    await page.close();
  }
  // a reload in the same place: the record is taken over KaTeX's layout and landed over formulas waiting for the chunk, held
  {
    const page = await ctx.newPage();
    page.on("pageerror", (e) => errors.push(e.message));
    const reqs = [];
    let gate = null;
    await page.route((u) => u.pathname === "/dist/math-chunk.js", async (route) => { reqs.push(route.request().url()); if (gate) await gate.p; await route.continue(); });
    await page.goto(cfg.chat);
    await shown(page, cfg.lastFiller);
    await swapped(page);
    await settle(page);
    const placed = await place(page, "none");
    if (placed) throw new Error(placed);
    await settle(page);
    const v = { preReload: await measure(page) };
    gate = {}; gate.p = new Promise((r) => { gate.r = r; });
    await page.reload();
    await shown(page, cfg.marker);
    await page.waitForFunction(() => document.querySelectorAll('script[src*="math-chunk.js"]').length > 0, null, { timeout: 30000 });
    await page.evaluate(() => { document.getElementById("content").style.overflowAnchor = "none"; });
    await settle(page);
    v.pending = await measure(page);
    gate.r();
    await swapped(page);
    await settle(page);
    v.after = await measure(page);
    v.requests = reqs.length;
    out.variants.reload = v;
    await page.close();
  }
  out.errors = errors;
} catch (e) {
  out.died = String(e && e.message || e);
}
fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
await browser.close();
process.exit(0);
"""

# A failed load and its retry, on a phone: the chunk's first answer is a 404, so every formula of the reply the reader is partway
# down is its source; the reader is put on the paragraph below them; a new reply with a formula arrives, and the fill that meets it
# uses the retry the failure armed (math.ts), the second request, held here while the formulas stay source; then it is served and
# the success lays out every formula, the failure's fallbacks included, with the reader's line kept (render.ts onMathSettled counts
# a view holding the failure's fallbacks as one that held a waiting formula; the review of iOS item 6, round 1). The user's own
# message above the reply carries a display formula and a fence: the reply's source blocks take the Copy button its body's other
# blocks have, and the bubble's stay bare, as its fence does (the highlighter never dresses a bubble).
DRIVER_RETRY = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const pw = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
let browser;
try { browser = await pw[cfg.engine].launch(); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const out = {};
const PENDING = "#content .md-math-inline, #content .md-math-display";
try {
  const device = Object.assign({}, pw.devices["iPhone 15"]);
  delete device.defaultBrowserType;
  const ctx = await browser.newContext(device);
  const errors = [];
  const settle = (page) => page.evaluate(() => fetch("/healthz", { cache: "no-store" }).then(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))));
  const shown = (page, t) => page.waitForFunction((t) => (document.body.innerText || "").includes(t), t, { timeout: 30000 });
  const measure = (page) => page.evaluate(({ marker, bubbleMarker }) => {
    const c = document.getElementById("content");
    const ct = c.getBoundingClientRect().top;
    const p = Array.from(c.querySelectorAll("p")).find((e) => e.offsetParent !== null && (e.textContent || "").startsWith(marker));
    const turn = p ? p.closest("[data-uuid]") : null;
    const shownF = turn ? Array.from(turn.querySelectorAll(".md-math-display, .katex-display, pre:has(> code.md-math-src)")) : [];
    const last = shownF[shownF.length - 1];
    const pres = turn ? Array.from(turn.querySelectorAll("pre > code.md-math-src")).map((x) => x.parentElement) : [];
    // the user's own bubble above the reply: its display formula and its fence, and the Copy buttons on them
    const ub = Array.from(c.querySelectorAll(".user-bubble")).find((e) => (e.textContent || "").includes(bubbleMarker));
    const bubble = ub ? { src: ub.querySelectorAll("pre > code.md-math-src").length, fences: ub.querySelectorAll("pre > code:not(.md-math-src)").length,
      copy: ub.querySelectorAll("pre > .code-copy").length, katex: ub.querySelectorAll(".katex").length } : null;
    return { markerTop: p ? p.getBoundingClientRect().top - ct : null, turnHeight: turn ? turn.getBoundingClientRect().height : null,
      lastFormulaBottom: last ? last.getBoundingClientRect().bottom - ct : null,
      pending: document.querySelectorAll("#content .md-math-inline, #content .md-math-display").length,
      src: turn ? turn.querySelectorAll("code.md-math-src").length : -1, pres: pres.length,
      copy: pres.filter((x) => !!x.querySelector(":scope > .code-copy")).length,
      katex: turn ? turn.querySelectorAll(".katex").length : -1, allSrc: document.querySelectorAll("#content code.md-math-src").length,
      bubble, scrollTop: c.scrollTop };
  }, { marker: cfg.marker, bubbleMarker: cfg.bubbleMarker });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => errors.push(e.message));
  const reqs = [];
  let release; const held = new Promise((r) => { release = r; });
  await page.route((u) => u.pathname === "/dist/math-chunk.js", async (route) => {
    const n = reqs.push(route.request().url());
    if (n === 1) return route.fulfill({ status: 404, contentType: "text/plain", body: "not found" });
    await held; await route.continue();
  });
  await page.goto(cfg.chat);
  await shown(page, cfg.lastFiller);
  await page.waitForFunction((sel) => !document.querySelector(sel) && !!document.querySelector("#content code.md-math-src"), PENDING, { timeout: 30000 });
  await settle(page);
  out.failed = Object.assign(await measure(page), { requests: reqs.length });
  const placed = await page.evaluate(({ marker, off }) => {
    const c = document.getElementById("content");
    c.style.overflowAnchor = "none";
    const p = Array.from(c.querySelectorAll("p")).find((e) => e.offsetParent !== null && (e.textContent || "").startsWith(marker));
    if (!p) return "no paragraph starting " + marker;
    c.scrollTop += p.getBoundingClientRect().top - c.getBoundingClientRect().top - off;
    return "";
  }, { marker: cfg.marker, off: cfg.offset });
  if (placed) throw new Error(placed);
  await settle(page);
  out.before = await measure(page);
  fs.appendFileSync(cfg.transcript, cfg.retryLines);
  await shown(page, cfg.retryMarker);
  for (let i = 0; i < 100 && reqs.length < 2; i++) await settle(page);
  await settle(page);
  out.during = Object.assign(await measure(page), { requests: reqs.length });
  release();
  await page.waitForFunction((sel) => !document.querySelector(sel) && !document.querySelector("#content code.md-math-src"), PENDING, { timeout: 30000 }).catch(() => {});
  await settle(page);
  out.after = Object.assign(await measure(page), { requests: reqs.length });
  out.errors = errors;
} catch (e) {
  out.died = String(e && e.message || e);
}
fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
await browser.close();
process.exit(0);
"""

# A comment thread over a passage that runs from prose into a formula, while the formula waits: the mark is cut at the formula (its
# text there is the TeX); when the chunk lands, the arrival unwraps every mark in the view and puts the thread back over the laid-out
# text, so the whole passage is marked and the formula's KaTeX root wears the mark's tint (render.ts onMathSettled; before, a mark
# placed while the formula waited survived the fill and applyCommentMarks never searched again for a thread that had one). The
# arrival's own result is read by a MutationObserver, in the microtask after the task that laid the formulas out, so no frame the
# kernel sends, which would re-run the marks pass over a rebuilt turn, can land between the arrival and the read.
DRIVER_MARK = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const pw = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
let browser;
try { browser = await pw[cfg.engine].launch(); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const out = {};
try {
  const page = await browser.newPage({ viewport: { width: 900, height: 900 } });
  const errors = []; page.on("pageerror", (e) => errors.push(e.message));
  const reqs = [];
  let release; const held = new Promise((r) => { release = r; });
  await page.route((u) => u.pathname === "/dist/math-chunk.js", async (route) => { reqs.push(route.request().url()); await held; await route.continue(); });
  await page.goto(cfg.chat);
  await page.waitForFunction((t) => (document.body.innerText || "").includes(t), cfg.marker, { timeout: 30000 });
  const sel = 'mark.cmt-hl[data-tid="' + cfg.tid + '"]';
  await page.waitForFunction((s) => !!document.querySelector(s), sel, { timeout: 30000 });
  await page.evaluate(() => fetch("/healthz", { cache: "no-store" }).then(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))));
  // what the thread's marks cover, and the reply's formulas, read in the page (installed once: the page's policy allows no eval)
  await page.evaluate(() => {
    window.__readMarks = (s, uuid) => {
      const turn = document.querySelector('#content .turn[data-uuid="' + uuid + '"]');
      const marks = Array.from(document.querySelectorAll(s));
      return { text: marks.map((m) => m.textContent || "").join(""), segs: marks.length, inTurn: !!turn && marks.every((m) => turn.contains(m)),
        pending: turn ? turn.querySelectorAll(".md-math-inline, .md-math-display").length : -1,
        katex: turn ? turn.querySelectorAll(".katex").length : -1, hosts: turn ? turn.querySelectorAll(".katex.cmt-hl-host").length : -1 };
    };
  });
  out.waiting = await page.evaluate(([s, uuid]) => window.__readMarks(s, uuid), [sel, cfg.uuid]);
  await page.evaluate(([s, uuid]) => {
    window.__atArrival = null;
    new MutationObserver(() => {
      const turn = document.querySelector('#content .turn[data-uuid="' + uuid + '"]');
      if (window.__atArrival === null && turn && turn.querySelector(".katex")) window.__atArrival = window.__readMarks(s, uuid);
    }).observe(document.getElementById("content"), { childList: true, subtree: true });
  }, [sel, cfg.uuid]);
  release();
  await page.waitForFunction(() => window.__atArrival !== null, null, { timeout: 30000 });
  out.arrival = await page.evaluate(() => window.__atArrival);
  out.requests = reqs.length;
  out.errors = errors;
} catch (e) {
  out.died = String(e && e.message || e);
}
fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
await browser.close();
process.exit(0);
"""

# The reader inside the math reply of a LONG transcript, on a phone: the reply sits above the fresh page's tail window, so the reload
# restore finds no row of it in the fresh page, lands the raw top and arms the deep-link land, which builds a window around the reply and
# lands it at the record's offset (render.ts landActive's reload restore, scrollToAnchor's keep-offset branch). One page life to place the
# reader (the chunk served when asked), then the reload with the chunk held.
DRIVER_WINDOW = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const pw = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
let browser;
try { browser = await pw[cfg.engine].launch(); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const out = {};
const PENDING = "#content .md-math-inline, #content .md-math-display";
try {
  const device = Object.assign({}, pw.devices["iPhone 15"]);
  delete device.defaultBrowserType;
  const ctx = await browser.newContext(device);
  const errors = [];
  const settle = (page) => page.evaluate(() => fetch("/healthz", { cache: "no-store" }).then(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))));
  const swapped = (page) => page.waitForFunction((sel) => !document.querySelector(sel) && document.querySelectorAll("#content .katex").length > 0, PENDING, { timeout: 30000 });
  const rendered = (marker) => Array.from(document.querySelectorAll("#content p")).some((e) => e.offsetParent !== null && (e.textContent || "").startsWith(marker));
  const has = (page) => page.evaluate(rendered, cfg.marker);
  const measure = (page) => page.evaluate((marker) => {
    const c = document.getElementById("content");
    const ct = c.getBoundingClientRect().top;
    const p = Array.from(c.querySelectorAll("p")).find((e) => e.offsetParent !== null && (e.textContent || "").startsWith(marker));
    const turn = p ? p.closest("[data-uuid]") : null;
    const shown = turn ? Array.from(turn.querySelectorAll(".md-math-display, .katex-display")) : [];
    const last = shown[shown.length - 1];
    return { markerTop: p ? p.getBoundingClientRect().top - ct : null, turnTop: turn ? turn.getBoundingClientRect().top - ct : null,
      turnHeight: turn ? turn.getBoundingClientRect().height : null, lastFormulaBottom: last ? last.getBoundingClientRect().bottom - ct : null,
      pending: document.querySelectorAll("#content .md-math-inline, #content .md-math-display").length,
      katex: document.querySelectorAll("#content .katex").length, scrollTop: c.scrollTop };
  }, cfg.marker);
  const place = (page) => page.evaluate(({ marker, off }) => {
    const c = document.getElementById("content");
    c.style.overflowAnchor = "none";
    const p = Array.from(c.querySelectorAll("p")).find((e) => e.offsetParent !== null && (e.textContent || "").startsWith(marker));
    if (!p) return "no paragraph starting " + marker;
    c.scrollTop += p.getBoundingClientRect().top - c.getBoundingClientRect().top - off;
    return "";
  }, { marker: cfg.marker, off: cfg.offset });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => errors.push(e.message));
  const reqs = [];
  let gate = null;
  await page.route((u) => u.pathname === "/dist/math-chunk.js", async (route) => { reqs.push(route.request().url()); if (gate) await gate.p; await route.continue(); });
  await page.goto(cfg.chat);
  await page.waitForFunction((t) => (document.body.innerText || "").includes(t), cfg.lastFiller, { timeout: 30000 });
  await settle(page);
  out.boot = { marker: await has(page), pending: await page.evaluate((sel) => document.querySelectorAll(sel).length, PENDING) };
  // up to the reply: the window grows as the reader reaches its top
  for (let i = 0; i < 120 && !(await has(page)); i++) {
    await page.evaluate(() => { const c = document.getElementById("content"); c.scrollTop = 0; });
    await settle(page);
  }
  if (!(await has(page))) throw new Error("the reply never rendered as the reader scrolled up");
  await swapped(page);
  await settle(page);
  for (let i = 0; i < 2; i++) {   // twice: the window can still grow under the first placing
    const placed = await place(page);
    if (placed) throw new Error(placed);
    await settle(page);
  }
  out.preReload = await measure(page);
  gate = {}; gate.p = new Promise((r) => { gate.r = r; });
  await page.reload();
  await page.waitForFunction(rendered, cfg.marker, { timeout: 30000 });
  await page.waitForFunction(() => document.querySelectorAll('script[src*="math-chunk.js"]').length > 0, null, { timeout: 30000 });
  await page.evaluate(() => { document.getElementById("content").style.overflowAnchor = "none"; });
  await settle(page);
  out.pending = await measure(page);
  gate.r();
  await swapped(page);
  await settle(page);
  out.after = await measure(page);
  out.requests = reqs.length;
  out.errors = errors;
} catch (e) {
  out.died = String(e && e.message || e);
}
fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
await browser.close();
process.exit(0);
"""

# Two sessions on a phone: the reader on the paragraph in `web` with the reply's formulas waiting above it, a switch to `api`, the chunk
# released and the swap done while `web` is hidden, then the switch back.
DRIVER_TABS = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const pw = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
let browser;
try { browser = await pw[cfg.engine].launch(); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const out = {};
const PENDING = "#content .md-math-inline, #content .md-math-display";
try {
  const device = Object.assign({}, pw.devices["iPhone 15"]);
  delete device.defaultBrowserType;
  const ctx = await browser.newContext(device);
  const errors = [];
  const page = await ctx.newPage();
  page.on("pageerror", (e) => errors.push(e.message));
  const settle = () => page.evaluate(() => fetch("/healthz", { cache: "no-store" }).then(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))));
  // a tab's view on screen: the paragraph starting `marker` displayed (a hidden view's elements have no offsetParent)
  const showing = (marker) => page.waitForFunction((m) => Array.from(document.querySelectorAll("#content p")).some((e) => e.offsetParent !== null && (e.textContent || "").startsWith(m)), marker, { timeout: 30000 });
  const tab = (sid) => page.evaluate((sid) => { const t = document.querySelector('#tabs .tab[data-id="' + sid + '"]'); if (!t) return false; t.click(); return true; }, sid);
  const measure = () => page.evaluate((marker) => {
    const c = document.getElementById("content");
    const ct = c.getBoundingClientRect().top;
    const p = Array.from(c.querySelectorAll("p")).find((e) => (e.textContent || "").startsWith(marker));
    const turn = p ? p.closest("[data-uuid]") : null;
    const shown = turn ? Array.from(turn.querySelectorAll(".md-math-display, .katex-display")) : [];
    const last = shown[shown.length - 1];
    return { displayed: !!(p && p.offsetParent !== null), markerTop: p ? p.getBoundingClientRect().top - ct : null,
      turnHeight: turn ? turn.getBoundingClientRect().height : null, lastFormulaBottom: last ? last.getBoundingClientRect().bottom - ct : null,
      pendingInTurn: turn ? turn.querySelectorAll(".md-math-inline, .md-math-display").length : null,
      katexInTurn: turn ? turn.querySelectorAll(".katex").length : null, scrollTop: c.scrollTop,
      atBottom: c.scrollHeight - c.clientHeight - c.scrollTop < 4 };
  }, cfg.marker);
  const reqs = [];
  let release; const held = new Promise((r) => { release = r; });
  await page.route((u) => u.pathname === "/dist/math-chunk.js", async (route) => { reqs.push(route.request().url()); await held; await route.continue(); });
  await page.goto(cfg.chat);
  await page.waitForFunction(() => document.querySelectorAll("#tabs .tab[data-id]").length >= 2, null, { timeout: 30000 });
  out.clickWeb = await tab(cfg.sid);
  await showing(cfg.lastFiller);
  await settle();
  const placed = await page.evaluate(({ marker, off }) => {
    const c = document.getElementById("content");
    c.style.overflowAnchor = "none";   // the phone's WebKit has no scroll anchoring; Chromium's own is off so the page's keep is what holds
    const p = Array.from(c.querySelectorAll("p")).find((e) => e.offsetParent !== null && (e.textContent || "").startsWith(marker));
    if (!p) return "no paragraph starting " + marker;
    c.scrollTop += p.getBoundingClientRect().top - c.getBoundingClientRect().top - off;
    return "";
  }, { marker: cfg.marker, off: cfg.offset });
  if (placed) throw new Error(placed);
  await settle();
  out.before = await measure();
  out.clickApi = await tab(cfg.sid2);
  await showing(cfg.apiMarker);
  await settle();
  out.hidden = await measure();
  release();
  await page.waitForFunction((sel) => !document.querySelector(sel) && document.querySelectorAll("#content .katex").length > 0, PENDING, { timeout: 30000 });
  await settle();
  out.apiAfter = await page.evaluate(() => { const c = document.getElementById("content"); return { atBottom: c.scrollHeight - c.clientHeight - c.scrollTop < 4 }; });
  out.clickBack = await tab(cfg.sid);
  await showing(cfg.marker);
  await settle();
  out.after = await measure();
  out.requests = reqs.length;
  out.errors = errors;
} catch (e) {
  out.died = String(e && e.message || e);
}
fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
await browser.close();
process.exit(0);
"""


class ServedMathChunk(unittest.TestCase):
    """One hermetic kernel per test, so each engine's chat opens on a transcript that has never held a formula (the chat
    prefetches every session's view, so a second session with math would fetch the chunk at boot)."""
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            raise unittest.SkipTest("extension deps absent (npm ci not run here): the served legs need them")

    def setUp(self):
        self.lab = tempfile.mkdtemp(prefix="math-chunk-")
        self.addCleanup(shutil.rmtree, self.lab, True)
        # the lab's ports (its kernel's serve port, and the postal port kernel_env reserves under the lab), freed after _stop
        # has killed and reaped the kernel and before the lab is removed: cleanups run last registered first
        self.addCleanup(lab_ports.release, self.lab)
        self.dist = os.path.join(self.lab, "dist")
        lab_dist.copy_dist(self.dist)   # the checkout's ONE build of the bundles, copied under its lock (tests/lab_dist.py)
        state = os.path.join(self.lab, "xdg", "romp")
        cwd = os.path.join(self.lab, "proj")
        for d in ("names", "sdk", "states"):
            os.makedirs(os.path.join(state, d), exist_ok=True)
        os.makedirs(cwd, exist_ok=True)
        Path(state, "names", SID).write_text("web\t%s\t\t\n" % cwd)
        Path(state, "sdk", SID + ".json").write_text(json.dumps(
            {"sid": SID, "name": "web", "cwd": cwd, "mode": "auto", "effort": "high",
             "lastSid": SID, "alive": True, "model": "claude-opus-5", "liveModel": "Opus 5"}))
        Path(state, "usage.json").write_text(json.dumps({"five_hour": {"pct": 10}, "seven_day": {"pct": 10}}))
        claude = os.path.join(self.lab, "claude")
        proj = os.path.join(claude, "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(cwd)))
        os.makedirs(proj, exist_ok=True)
        self.t0 = int(time.time()) - 900
        if getattr(getattr(self, self._testMethodName, None), "api_session", False):
            # the second session: a reply with display formulas at its top, then replies long enough that its reader sits at the bottom
            Path(state, "names", SID2).write_text("api\t%s\t\t\n" % cwd)
            Path(state, "sdk", SID2 + ".json").write_text(json.dumps(
                {"sid": SID2, "name": "api", "cwd": cwd, "mode": "auto", "effort": "high",
                 "lastSid": SID2, "alive": True, "model": "claude-opus-5", "liveModel": "Opus 5"}))
            recs = [{"type": "user", "timestamp": iso(self.t0 + 10), "uuid": "v1", "parentUuid": None, "promptSource": "typed",
                     "sessionId": SID2, "message": {"role": "user", "content": "what does the api tier cost?"}},
                    dict(reply("w0", "v1", self.t0 + 20, MATH_INTRO + "\n\n" + "\n\n".join("$$%s$$" % f for f in FORMULAS) + "\n"), sessionId=SID2)]
            for i in range(1, 16):
                recs.append(dict(reply("w%d" % i, "w%d" % (i - 1), self.t0 + 20 + i, "API-TAB " + FILLER % i), sessionId=SID2))
            Path(proj, SID2 + ".jsonl").write_text(jsonl(recs))
        if getattr(getattr(self, self._testMethodName, None), "comment_thread", False):
            os.makedirs(os.path.join(state, "comments"), exist_ok=True)
            self.mark_exact = mark_exact()
            Path(state, "comments", SID + ".json").write_text(json.dumps({"threads": [
                {"tid": MARK_TID, "sid": SID, "name": "web-comment-1", "anchorUuid": "r1", "cutUuid": "r1",
                 "exact": self.mark_exact, "status": "open", "createdT": self.t0 + 50}]}))
        self.transcript = os.path.join(proj, SID + ".jsonl")
        Path(self.transcript).write_text(jsonl([
            {"type": "user", "timestamp": iso(self.t0), "uuid": "u1", "parentUuid": None, "promptSource": "typed",
             "sessionId": SID, "message": {"role": "user", "content": "summarize the notes-api README"}},
            reply("a1", "u1", self.t0 + 5, FIRST_REPLY)]))
        self.port = lab_ports.reserve(self.lab)
        self.token = "testtok-mathchunk"
        env = _lab.kernel_env(self.lab, claude, self.dist, self.port, self.token)
        self.klog = os.path.join(self.lab, "kernel.log")
        self.kernel = subprocess.Popen([os.path.join(BIN, "romp-kernel")],
                                       stdout=open(self.klog, "w"), stderr=subprocess.STDOUT, env=env)
        self.addCleanup(self._stop)
        why = lab_ports.wait_owned(self.kernel, env)
        if why:
            raise unittest.SkipTest("hermetic kernel never served /healthz here: " + why)

    def _stop(self):
        self.kernel.kill()
        self.kernel.wait()

    def _get(self, path, headers=None):
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path),
                                     headers=dict({"X-Romp-Token": self.token}, **(headers or {})))
        try:
            r = urllib.request.urlopen(req, timeout=20)
            return r.status, dict((k.lower(), v) for k, v in r.headers.items()), r.read()
        except urllib.error.HTTPError as e:
            return e.code, dict((k.lower(), v) for k, v in e.headers.items()), e.read()

    def _token(self):
        status, _, html = self._get("/chat")
        self.assertEqual(status, 200)
        m = re.search(rb"/dist/render\.js\?v=(\d+)", html)
        self.assertIsNotNone(m, "the chat page stamps its bundle with the dist token")
        return int(m.group(1))

    def test_the_chunk_is_served_and_versioned_like_every_bundle_and_the_chat_bundle_carries_no_katex(self):
        ver = self._token()
        status, h, body = self._get("/dist/math-chunk.js?v=%d" % ver, {"Accept-Encoding": "gzip"})
        self.assertEqual(status, 200, "the kernel serves the chunk from the generic /dist route")
        self.assertEqual(h.get("content-type"), "text/javascript; charset=utf-8")
        self.assertEqual(h.get("cache-control"), "no-cache", "revalidated like every bundle, never served stale")
        self.assertEqual(h.get("content-encoding"), "gzip", "gzipped when asked, like every bundle over 1 KB")
        self.assertEqual(h.get("vary"), "Accept-Encoding")
        etag = h.get("etag") or ""
        self.assertTrue(etag.startswith('"') and etag.endswith('-gz"'), "the gzip form's validator: %r" % etag)
        js = gzip.decompress(body)
        self.assertIn(b"__rompKatex", js, "the chunk registers KaTeX as the global math.ts reads")
        self.assertIn(b"KaTeX parse error", js, "and carries KaTeX itself")
        status304, _, _ = self._get("/dist/math-chunk.js?v=%d" % ver, {"Accept-Encoding": "gzip", "If-None-Match": etag})
        self.assertEqual(status304, 304, "a revalidation with the validator costs a 304, not the chunk again")
        status, _, render = self._get("/dist/render.js?v=%d" % ver)
        self.assertEqual(status, 200)
        self.assertNotIn(b"KaTeX parse error", render, "the chat's bundle carries no KaTeX")
        self.assertIn(b"math-chunk.js", render, "it names the chunk it loads")
        # the token every page stamps is the newest mtime under dist/*.js, so a rebuild that changed the chunk alone moves it
        chunk = os.path.join(self.dist, "math-chunk.js")
        st = os.stat(chunk)
        later = int(time.time()) + 3600
        try:
            os.utime(chunk, (later, later))
            self.assertEqual(self._token(), later, "the chunk's own mtime moves the ?v= the chunk's URL is derived with")
        finally:
            os.utime(chunk, ns=(st.st_atime_ns, st.st_mtime_ns))

    def _drive(self, engine):
        declared = os.environ.get("ROMP_SERVED_TESTS_ENGINES", "")
        if engine != "chromium" and declared and engine not in [e.strip() for e in declared.split(",")]:
            self.skipTest("optional: this runner declares no %s (ROMP_SERVED_TESTS_ENGINES=%s)" % (engine, declared))
        tag = engine[0]
        math_text = MATH_INTRO + "\n\n" + "\n\n".join("$$%s$$" % f for f in FORMULAS) + "\n"
        math_lines = jsonl([reply("m-" + tag, "a1", self.t0 + 60, math_text)])
        fillers = [reply("f%d-%s" % (i, tag), ("m-" + tag) if i == 0 else "f%d-%s" % (i - 1, tag), self.t0 + 70 + i, FILLER % i)
                   for i in range(FILLERS)]
        cfg = os.path.join(self.lab, "cfg-%s.json" % engine)
        Path(cfg).write_text(json.dumps({
            "engine": engine, "chat": "http://127.0.0.1:%d/chat?token=%s" % (self.port, self.token),
            "firstReply": FIRST_REPLY, "transcript": self.transcript, "mathLines": math_lines, "formulas": FORMULAS,
            "fillerLines": jsonl(fillers), "lastFiller": "Filler reply %d:" % (FILLERS - 1),
            "tailMathLines": jsonl([reply("t-" + tag, "f%d-%s" % (FILLERS - 1, tag), self.t0 + 200, math_text)])}))
        return self._run(engine, DRIVER, cfg)

    def _run(self, engine, driver_text, cfg, name=None):
        """One node driver run against this test's kernel: the driver's RESULT line, parsed (and kept as `name`.json under
        MATH_CHUNK_SERVED_OUT, the engine's name by default); a missing browser skips."""
        driver = os.path.join(self.lab, "driver-%s.mjs" % engine)
        Path(driver).write_text(driver_text)
        try:
            p = subprocess.run(["node", driver], capture_output=True, text=True, timeout=240,
                               env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg))
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
        out = os.environ.get("MATH_CHUNK_SERVED_OUT", "")   # a directory to keep each engine's measured figures in, for a report
        if out:
            os.makedirs(out, exist_ok=True)
            Path(out, (name or engine) + ".json").write_text(json.dumps(r, indent=1))
        return r

    def _leg(self, engine):
        ver = self._token()
        r = self._drive(engine)
        w = engine + ": "
        self.assertIn("a", r, w + "the driver stopped before the first read: %r" % r.get("died"))
        self.assertEqual(r["a"], {"scripts": 0, "waiting": 0, "katex": 0, "requests": 0},
                         w + "a transcript with no formula fetches no chunk and holds no formula: %r" % r["a"])
        self.assertIn("b", r, w + "the driver stopped before the formulas' read: %r" % r.get("died"))
        b = r["b"]
        self.assertEqual(b["requests"], 1, w + "the first formula fetches the chunk once: %r" % b)
        self.assertNotIn("died", r, w + "the driver stopped early: %r\nkernel:\n%s" % (r.get("died"), Path(self.klog).read_text()[-1500:]))
        self.assertTrue(r["chunkUrl"].endswith("/dist/math-chunk.js?v=%d" % ver), w + "beside the bundle, with its token: %r" % r["chunkUrl"])
        self.assertEqual(b["katex"], 0, w + "nothing is laid out while the chunk is held")
        self.assertEqual(b["texts"], FORMULAS, w + "each formula shows its TeX while it waits")
        self.assertTrue(all(h > 0 for h in b["heights"]), w + "in a box of its own, never a blank: %r" % b["heights"])
        before, after = r["before"], r["after"]
        self.assertFalse(before["atBottom"], w + "the reader is scrolled up: %r" % before)
        self.assertLess(before["mathBottom"], 0, w + "the formulas' turn is above the viewport: %r" % before)
        self.assertGreater(after["mathHeight"] - before["mathHeight"], 20,
                           w + "the swap grew the formulas' turn, so the reader's place had something to survive: %r %r" % (before, after))
        self.assertLessEqual(abs(after["anchorTop"] - before["anchorTop"]), 1,
                             w + "the reader's top turn stays within 1 px across the swap: %r %r" % (before, after))
        end = r["end"]
        self.assertEqual((end["scripts"], end["requests"], end["waiting"]), (1, 1, 0), w + "one chunk, no formula left waiting: %r" % end)
        self.assertGreaterEqual(end["katex"], len(FORMULAS), w + "every formula laid out: %r" % end)
        d = r["d"]
        self.assertTrue(d["before"]["atBottom"], w + "the second page's reader sits at the bottom as the tail's formulas wait: %r" % d)
        self.assertGreater(d["after"]["tailHeight"] - d["before"]["tailHeight"], 20, w + "the swap grew the tail turn: %r" % d)
        self.assertTrue(d["after"]["atBottom"], w + "and the reader at the bottom is still at the bottom after it: %r" % d)
        self.assertEqual(r["errors"], [], w + "no page error")

    def test_chat_chromium(self):
        self._leg("chromium")

    def test_chat_webkit(self):
        self._leg("webkit")

    def _in_turn(self, engine):
        declared = os.environ.get("ROMP_SERVED_TESTS_ENGINES", "")
        if engine != "chromium" and declared and engine not in [e.strip() for e in declared.split(",")]:
            self.skipTest("optional: this runner declares no %s (ROMP_SERVED_TESTS_ENGINES=%s)" % (engine, declared))
        # the transcript before any page opens: a question, the reply with the formulas and the paragraphs below them, fillers
        recs = [{"type": "user", "timestamp": iso(self.t0 + 30), "uuid": "u2", "parentUuid": "a1", "promptSource": "typed",
                 "sessionId": SID, "message": {"role": "user", "content": "walk me through the ranking math"}},
                reply("r1", "u2", self.t0 + 40, ranking_reply())]
        for i in range(FILLERS):
            recs.append(reply("g%d" % i, "r1" if i == 0 else "g%d" % (i - 1), self.t0 + 60 + i, FILLER % i))
        with open(self.transcript, "a") as f:
            f.write(jsonl(recs))
        cfg = os.path.join(self.lab, "cfg-in-turn-%s.json" % engine)
        Path(cfg).write_text(json.dumps({
            "engine": engine, "chat": "http://127.0.0.1:%d/chat?token=%s" % (self.port, self.token),
            "lastFiller": "Filler reply %d:" % (FILLERS - 1), "marker": "READ-03", "offset": 80}))
        r = self._run(engine, DRIVER_IN_TURN, cfg, "in-turn-" + engine)
        w = engine + ": "
        self.assertNotIn("died", r, w + "the driver stopped early: %r\nkernel:\n%s" % (r.get("died"), Path(self.klog).read_text()[-1500:]))
        n = len(STEP_FORMULAS)
        for name in ("in-turn-none", "in-turn-auto"):
            v = r["variants"][name]
            b, a = v["before"], v["after"]
            x = w + name + ": "
            self.assertEqual(b["pending"], 3 * n, x + "every formula of the reply waits for the chunk: %r" % b)
            self.assertLess(b["turnTop"], 0, x + "the reply begins above the viewport: %r" % b)
            self.assertLess(b["lastFormulaBottom"], 0, x + "its last formula is above the viewport top, in the reader's own turn: %r" % b)
            self.assertGreater(b["markerTop"], 0, x + "the paragraph being read is on screen: %r" % b)
            self.assertEqual((a["pending"], v["requests"]), (0, 1), x + "one chunk, every formula laid out: %r" % v)
            self.assertGreaterEqual(a["katex"], 3 * n, x + "%r" % a)
            self.assertGreater(a["turnHeight"] - b["turnHeight"], 20,
                               x + "the swap grew the reader's own turn above them, so their place had something to survive: %r %r" % (b, a))
            self.assertLessEqual(abs(a["markerTop"] - b["markerTop"]), 1,
                                 x + "the paragraph being read stays within 1 px across the swap: %r %r" % (b, a))
        self.assertEqual(r["variants"]["in-turn-none"]["before"]["anchoring"], "none")
        v = r["variants"]["reload"]
        pre, pend, a = v["preReload"], v["pending"], v["after"]
        x = w + "reload: "
        self.assertEqual(pre["pending"], 0, x + "the place is taken over KaTeX's layout: %r" % pre)
        self.assertLess(pre["lastFormulaBottom"], 0, x + "with the reply's formulas above the viewport top: %r" % pre)
        self.assertEqual(pend["pending"], 3 * n, x + "the fresh page's formulas wait for the chunk: %r" % pend)
        # within 2 px, not 1: both engines hold the scroller's offset in whole pixels (every scrollTop read here is one), the fresh
        # page writes it more than once while it settles, and its line sits on another fraction of a pixel than the old page's
        # (measured: Chromium lands the turn's own top 1 px off this way, so the base's turn restore ended 1 px off too)
        self.assertLessEqual(abs(pend["markerTop"] - pre["markerTop"]), 2,
                             x + "the fresh page lands the paragraph being read where it was, over the waiting formulas: %r %r" % (pre, pend))
        self.assertGreater(a["turnHeight"] - pend["turnHeight"], 20, x + "the swap grew the turn: %r %r" % (pend, a))
        self.assertLessEqual(abs(a["markerTop"] - pre["markerTop"]), 2, x + "and keeps it there through the swap: %r %r" % (pre, a))
        self.assertEqual((a["pending"], v["requests"]), (0, 2), x + "one chunk per page life: %r" % v)
        self.assertEqual(r["errors"], [], w + "no page error")

    def test_reader_inside_the_math_reply_on_a_phone_chromium(self):
        self._in_turn("chromium")

    def test_reader_inside_the_math_reply_on_a_phone_webkit(self):
        self._in_turn("webkit")

    def _retry(self, engine):
        declared = os.environ.get("ROMP_SERVED_TESTS_ENGINES", "")
        if engine != "chromium" and declared and engine not in [e.strip() for e in declared.split(",")]:
            self.skipTest("optional: this runner declares no %s (ROMP_SERVED_TESTS_ENGINES=%s)" % (engine, declared))
        recs = [{"type": "user", "timestamp": iso(self.t0 + 30), "uuid": "u2", "parentUuid": "a1", "promptSource": "typed",
                 "sessionId": SID, "message": {"role": "user", "content": BUBBLE_ASK}},
                reply("r1", "u2", self.t0 + 40, ranking_reply())]
        for i in range(FILLERS):
            recs.append(reply("g%d" % i, "r1" if i == 0 else "g%d" % (i - 1), self.t0 + 60 + i, FILLER % i))
        with open(self.transcript, "a") as f:
            f.write(jsonl(recs))
        retry_text = "RETRY-REPLY: one more identity, $$\\sum_{k=1}^{m} k = \\frac{m(m+1)}{2}$$ for the api session's tally.\n"
        cfg = os.path.join(self.lab, "cfg-retry-%s.json" % engine)
        Path(cfg).write_text(json.dumps({
            "engine": engine, "chat": "http://127.0.0.1:%d/chat?token=%s" % (self.port, self.token), "transcript": self.transcript,
            "lastFiller": "Filler reply %d:" % (FILLERS - 1), "marker": "READ-03", "offset": 80, "retryMarker": "RETRY-REPLY", "bubbleMarker": "walk me through the ranking math",
            "retryLines": jsonl([reply("rr", "g%d" % (FILLERS - 1), self.t0 + 300, retry_text)])}))
        r = self._run(engine, DRIVER_RETRY, cfg, "retry-" + engine)
        w = engine + ": retry: "
        self.assertNotIn("died", r, w + "the driver stopped early: %r\nkernel:\n%s" % (r.get("died"), Path(self.klog).read_text()[-1500:]))
        n = len(STEP_FORMULAS)
        f, b, d, a = r["failed"], r["before"], r["during"], r["after"]
        self.assertEqual((f["requests"], f["pending"], f["katex"]), (1, 0, 0), w + "the first request failed and nothing waits: %r" % f)
        self.assertEqual(f["src"], 3 * n, w + "every formula of the reply is its source: %r" % f)
        self.assertEqual((f["pres"], f["copy"]), (n, n),
                         w + "each display formula the failure showed as a source block in the reply has the Copy button the reply's source blocks have: %r" % f)
        self.assertEqual(f["bubble"], {"src": 1, "fences": 1, "copy": 0, "katex": 0},
                         w + "your own bubble keeps its blocks bare: the display formula the failure showed as a source block has no Copy button, as the bubble's fence has none: %r" % f["bubble"])
        self.assertLess(b["lastFormulaBottom"], 0, w + "the reply's formulas are above the viewport top: %r" % b)
        self.assertGreater(b["markerTop"], 0, w + "the paragraph being read is on screen: %r" % b)
        self.assertEqual(d["requests"], 2, w + "the new reply's formula used the retry the failure armed: %r" % d)
        self.assertEqual((d["pending"], d["src"]), (0, 3 * n), w + "while the retry is out, nothing waits and the reply keeps its sources: %r" % d)
        self.assertLessEqual(abs(d["markerTop"] - b["markerTop"]), 1, w + "the new reply at the tail did not move the reader: %r %r" % (b, d))
        self.assertEqual((a["pending"], a["src"], a["allSrc"], a["requests"]), (0, 0, 0, 2), w + "the served retry laid out every formula, the failure's included: %r" % a)
        self.assertGreaterEqual(a["katex"], 3 * n, w + "%r" % a)
        self.assertEqual(a["bubble"], {"src": 0, "fences": 1, "copy": 0, "katex": 1}, w + "the bubble's formula is laid out by the success too: %r" % a["bubble"])
        self.assertGreater(abs(a["turnHeight"] - b["turnHeight"]), 5,
                           w + "the swap from the sources to KaTeX's layout changed the reader's own turn above them: %r %r" % (b, a))
        self.assertLessEqual(abs(a["markerTop"] - b["markerTop"]), 1,
                             w + "the paragraph being read stays within 1 px across the success: %r %r" % (b, a))
        self.assertEqual(r["errors"], [], w + "no page error")

    def test_a_failed_load_retried_keeps_the_reader_on_a_phone_chromium(self):
        self._retry("chromium")

    def test_a_failed_load_retried_keeps_the_reader_on_a_phone_webkit(self):
        self._retry("webkit")

    def _mark(self, engine):
        declared = os.environ.get("ROMP_SERVED_TESTS_ENGINES", "")
        if engine != "chromium" and declared and engine not in [e.strip() for e in declared.split(",")]:
            self.skipTest("optional: this runner declares no %s (ROMP_SERVED_TESTS_ENGINES=%s)" % (engine, declared))
        recs = [{"type": "user", "timestamp": iso(self.t0 + 30), "uuid": "u2", "parentUuid": "a1", "promptSource": "typed",
                 "sessionId": SID, "message": {"role": "user", "content": "walk me through the ranking math"}},
                reply("r1", "u2", self.t0 + 40, ranking_reply())]
        with open(self.transcript, "a") as f:
            f.write(jsonl(recs))
        cfg = os.path.join(self.lab, "cfg-mark-%s.json" % engine)
        Path(cfg).write_text(json.dumps({
            "engine": engine, "chat": "http://127.0.0.1:%d/chat?token=%s" % (self.port, self.token),
            "marker": "STEP-01", "tid": MARK_TID, "uuid": "r1"}))
        r = self._run(engine, DRIVER_MARK, cfg, "mark-" + engine)
        w = engine + ": comment mark: "
        self.assertNotIn("died", r, w + "the driver stopped early: %r\nkernel:\n%s" % (r.get("died"), Path(self.klog).read_text()[-1500:]))
        wt, ar = r["waiting"], r["arrival"]
        self.assertGreater(wt["pending"], 0, w + "the reply's formulas wait for the chunk: %r" % wt)
        self.assertEqual(norm_ws(wt["text"]), MARK_HEAD,
                         w + "while the formula waits, the thread's mark is cut at it, its text there being the TeX: %r" % wt)
        self.assertTrue(ar["inTurn"] and ar["katex"] > 0, w + "the arrival laid the reply out, the marks in its turn: %r" % ar)
        self.assertEqual(norm_ws(ar["text"]), norm_ws(self.mark_exact),
                         w + "after the arrival the mark covers the whole passage, the laid-out formula included: %r vs %r" % (ar, self.mark_exact))
        self.assertGreaterEqual(ar["hosts"], 1, w + "and the formula's KaTeX root wears the mark's tint: %r" % ar)
        self.assertEqual(r["requests"], 1, w + "one chunk: %r" % r)
        self.assertEqual(r["errors"], [], w + "no page error")

    @with_comment_thread
    def test_a_comment_mark_over_a_waiting_formula_covers_the_whole_passage_after_the_arrival_chromium(self):
        self._mark("chromium")

    @with_comment_thread
    def test_a_comment_mark_over_a_waiting_formula_covers_the_whole_passage_after_the_arrival_webkit(self):
        self._mark("webkit")

    def _window_reload(self, engine):
        declared = os.environ.get("ROMP_SERVED_TESTS_ENGINES", "")
        if engine != "chromium" and declared and engine not in [e.strip() for e in declared.split(",")]:
            self.skipTest("optional: this runner declares no %s (ROMP_SERVED_TESTS_ENGINES=%s)" % (engine, declared))
        recs = [{"type": "user", "timestamp": iso(self.t0 + 30), "uuid": "u2", "parentUuid": "a1", "promptSource": "typed",
                 "sessionId": SID, "message": {"role": "user", "content": "walk me through the ranking math"}},
                reply("r1", "u2", self.t0 + 40, ranking_reply())]
        for i in range(LONG_FILLERS):
            recs.append(reply("g%d" % i, "r1" if i == 0 else "g%d" % (i - 1), self.t0 + 60 + i, FILLER % i))
        with open(self.transcript, "a") as f:
            f.write(jsonl(recs))
        cfg = os.path.join(self.lab, "cfg-window-%s.json" % engine)
        Path(cfg).write_text(json.dumps({
            "engine": engine, "chat": "http://127.0.0.1:%d/chat?token=%s" % (self.port, self.token),
            "lastFiller": "Filler reply %d:" % (LONG_FILLERS - 1), "marker": "READ-03", "offset": 80}))
        r = self._run(engine, DRIVER_WINDOW, cfg, "window-" + engine)
        w = engine + ": long transcript: "
        self.assertNotIn("died", r, w + "the driver stopped early: %r\nkernel:\n%s" % (r.get("died"), Path(self.klog).read_text()[-1500:]))
        n = len(STEP_FORMULAS)
        self.assertEqual(r["boot"], {"marker": False, "pending": 0},
                         w + "the fresh page's tail window holds none of the reply, so the reload restore takes the windowed road: %r" % r["boot"])
        pre, pend, a = r["preReload"], r["pending"], r["after"]
        self.assertEqual(pre["pending"], 0, w + "the place is taken over KaTeX's layout: %r" % pre)
        self.assertLess(pre["lastFormulaBottom"], 0, w + "with the reply's formulas above the viewport top: %r" % pre)
        self.assertGreater(pre["markerTop"], 0, w + "and the paragraph being read on screen: %r" % pre)
        self.assertEqual(pend["pending"], 3 * n, w + "the fresh page's formulas wait for the chunk: %r" % pend)
        # within 2 px, as the in-window reload above (whole-pixel scroll offsets)
        self.assertLessEqual(abs(pend["markerTop"] - pre["markerTop"]), 2,
                             w + "the fresh page lands the paragraph being read where it was, over the waiting formulas: %r %r" % (pre, pend))
        self.assertGreater(a["turnHeight"] - pend["turnHeight"], 20, w + "the swap grew the turn: %r %r" % (pend, a))
        self.assertLessEqual(abs(a["markerTop"] - pre["markerTop"]), 2, w + "and keeps it there through the swap: %r %r" % (pre, a))
        self.assertEqual((a["pending"], r["requests"]), (0, 2), w + "one chunk per page life: %r" % r)
        self.assertEqual(r["errors"], [], w + "no page error")

    def test_reload_into_a_long_transcript_on_a_phone_chromium(self):
        self._window_reload("chromium")

    def test_reload_into_a_long_transcript_on_a_phone_webkit(self):
        self._window_reload("webkit")

    def _hidden_tab(self, engine):
        declared = os.environ.get("ROMP_SERVED_TESTS_ENGINES", "")
        if engine != "chromium" and declared and engine not in [e.strip() for e in declared.split(",")]:
            self.skipTest("optional: this runner declares no %s (ROMP_SERVED_TESTS_ENGINES=%s)" % (engine, declared))
        recs = [{"type": "user", "timestamp": iso(self.t0 + 30), "uuid": "u2", "parentUuid": "a1", "promptSource": "typed",
                 "sessionId": SID, "message": {"role": "user", "content": "walk me through the ranking math"}},
                reply("r1", "u2", self.t0 + 40, ranking_reply())]
        for i in range(FILLERS):
            recs.append(reply("g%d" % i, "r1" if i == 0 else "g%d" % (i - 1), self.t0 + 60 + i, FILLER % i))
        with open(self.transcript, "a") as f:
            f.write(jsonl(recs))
        cfg = os.path.join(self.lab, "cfg-tabs-%s.json" % engine)
        Path(cfg).write_text(json.dumps({
            "engine": engine, "chat": "http://127.0.0.1:%d/chat?token=%s" % (self.port, self.token), "sid": SID, "sid2": SID2,
            "lastFiller": "Filler reply %d:" % (FILLERS - 1), "apiMarker": "API-TAB", "marker": "READ-03", "offset": 80}))
        r = self._run(engine, DRIVER_TABS, cfg, "tabs-" + engine)
        w = engine + ": hidden tab: "
        self.assertNotIn("died", r, w + "the driver stopped early: %r\nkernel:\n%s" % (r.get("died"), Path(self.klog).read_text()[-1500:]))
        self.assertEqual((r["clickWeb"], r["clickApi"], r["clickBack"]), (True, True, True), w + "both tabs on the strip: %r" % r)
        n = len(STEP_FORMULAS)
        b, h, a = r["before"], r["hidden"], r["after"]
        self.assertTrue(b["displayed"], w + "the paragraph being read is on screen in web: %r" % b)
        self.assertEqual(b["pendingInTurn"], 3 * n, w + "every formula of the reply waits for the chunk: %r" % b)
        self.assertLess(b["lastFormulaBottom"], 0, w + "above the viewport top, in the reader's own turn: %r" % b)
        self.assertGreater(b["markerTop"], 0, w + "%r" % b)
        self.assertFalse(h["displayed"], w + "web is hidden behind api when the chunk lands: %r" % h)
        self.assertEqual(h["pendingInTurn"], 3 * n, w + "its formulas still waiting then: %r" % h)
        self.assertTrue(r["apiAfter"]["atBottom"], w + "api's reader, at its bottom, is still at its bottom after the swap: %r" % r["apiAfter"])
        self.assertTrue(a["displayed"], w + "%r" % a)
        self.assertEqual((a["pendingInTurn"], r["requests"]), (0, 1), w + "one chunk, every formula laid out: %r" % r)
        self.assertGreater(a["turnHeight"] - b["turnHeight"], 20, w + "the swap grew the reader's own turn while it was hidden: %r %r" % (b, a))
        self.assertLessEqual(abs(a["markerTop"] - b["markerTop"]), 1,
                             w + "back on web, the paragraph being read is within 1 px of where the reader left it: %r %r" % (b, a))
        self.assertEqual(r["errors"], [], w + "no page error")

    @with_api_session
    def test_a_tab_hidden_while_the_chunk_lands_on_a_phone_chromium(self):
        self._hidden_tab("chromium")

    @with_api_session
    def test_a_tab_hidden_while_the_chunk_lands_on_a_phone_webkit(self):
        self._hidden_tab("webkit")


if __name__ == "__main__":
    unittest.main()
