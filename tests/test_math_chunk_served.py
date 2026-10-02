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
    reader at the bottom when formulas arrive at the tail is still at the bottom after the swap grows the tail.
SYNTHETIC fixtures only; skips LOUDLY without the extension deps or a Playwright browser (CI's served job installs both)."""
import gzip
import json
import lab_dist
import os
import re
import shutil
import socket
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
FIRST_REPLY = "The notes-api README covers install and usage; the cost is $5-$10 and $HOME stays literal."
MATH_INTRO = "Here are the three identities the tests check:"
FORMULAS = [r"\sum_{i=0}^{n} i^2 = \frac{n(n+1)(2n+1)}{6}",
            r"\int_0^1 \frac{x^2}{\sqrt{1+x^3}}\,dx = \frac{2}{3}\left(\sqrt{2}-1\right)",
            r"\prod_{k=2}^{m} \left(1 - \frac{1}{k^2}\right) = \frac{m+1}{2m}"]
FILLERS = 24
FILLER = ("Filler reply %d: the web session reran the notes-api tests and the api session read the logs; nothing here is a "
          "formula, only prose long enough to wrap across a few lines of a narrow phone column so the transcript scrolls.")


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def reply(uuid, parent, t, text):
    return {"type": "assistant", "timestamp": iso(t), "uuid": uuid, "parentUuid": parent, "sessionId": SID,
            "message": {"role": "assistant", "model": "claude-opus-5", "stop_reason": "end_turn",
                        "content": [{"type": "text", "text": text}]}}


def jsonl(records):
    return "".join(json.dumps(r) + "\n" for r in records)


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
        self.transcript = os.path.join(proj, SID + ".jsonl")
        Path(self.transcript).write_text(jsonl([
            {"type": "user", "timestamp": iso(self.t0), "uuid": "u1", "parentUuid": None, "promptSource": "typed",
             "sessionId": SID, "message": {"role": "user", "content": "summarize the notes-api README"}},
            reply("a1", "u1", self.t0 + 5, FIRST_REPLY)]))
        self.port = _free_port()
        self.token = "testtok-mathchunk"
        env = _lab.kernel_env(self.lab, claude, self.dist, self.port, self.token)
        self.klog = os.path.join(self.lab, "kernel.log")
        self.kernel = subprocess.Popen([os.path.join(BIN, "romp-kernel")],
                                       stdout=open(self.klog, "w"), stderr=subprocess.STDOUT, env=env)
        self.addCleanup(self._stop)
        for _ in range(120):
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/healthz" % self.port, timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise unittest.SkipTest("hermetic kernel never served /healthz here")

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
        driver = os.path.join(self.lab, "driver.mjs")
        Path(driver).write_text(DRIVER)
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
            Path(out, engine + ".json").write_text(json.dumps(r, indent=1))
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


if __name__ == "__main__":
    unittest.main()
