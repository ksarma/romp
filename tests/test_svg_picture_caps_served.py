#!/usr/bin/env python3
"""An svg picture on a signed-in page, in a real browser: its src is the page's own /file address with its per-file cap,
and it loads.

A header-less /file load (an img, a detached probe of a picture) passes only with the per-file cap in its URL
(ui/webview/file-cap.ts; fileUrl in ui/webview/preview.ts adds it, and capAuthoredFileUrls adds it to a /file URL an
author wrote), and the cap is made with the page key the sign-in stores. The node browser legs that pin an svg picture's
address (ui/webview/file-view-svg-reask-browser.test.ts and md-img-park-browser.test.ts) run with no page key, so the
address they pin is the one a page with no key builds, with no cap in it. This lab is the witness under the page key: it
signs in through the kernel's own sign-in page of a hermetic kernel, drives the REAL chat page in playwright's Chromium
(the harness of tests/test_file_caps_browser.py: the lab kernel's environment, the built bundles' copy, the driver's
head) and reads the picture on every road the page takes to an svg's bytes:

  A. the chat's preview box of a mentioned .svg (previewFull), inside the box's data mark
  B. an svg an author links in a message by its /file address (the cap pass)
  C. the markdown heal's re-request in the message: a figure whose file is absent parks, the file is written, romp:wsup
  D. the file viewer's picture on its first open, inside the picture box's data mark, with its version key
  E. the Source toggle pressed and pressed back
  F. the viewer's Reload after the file changed on disk (the window's focus raises the bar)
  G. bytes that do not decode (the Reload, the picture fails, the re-ask's fetch and its picture, then the failure pane),
     then valid bytes, a kernel message and, if the picture is not back yet, romp:wsup (which probe brings it is not checked)
  H. the markdown heal's re-request of a figure in a note the viewer renders
  I. a page reload, then A and D again

On every road the picture's src is this page's own /file address, never a blob: or data: URL, it carries a cap, and the
picture loads (complete, with its natural width); the viewer's picture (D to G, and I's) carries the version key. No /file
request the page makes is refused (401 or 403), and every image request to /file carries a cap.

C and H assert only the eventual heal: the figure comes back at its capped address, and the answer to its re-request is a
capped 200. They do not check which probe brought it back, and nothing the driver records can tell. The per-message path
sends at most one probe of a parked figure's address at a time: a kernel message that arrives while that probe is still
loading sends nothing, and the budget is three probes, one per kernel message that finds no probe of the address in flight
(opening the viewer brings such messages). An event that arrives while a probe of the address is loading shares that
probe's answer instead of asking again, so when that answer is the 404 from before the write the figure waits for the next
kernel message or event; the heal does not yet probe again after such a shared failure, with or without the caps. So each
of C and H gives the figure the event, then, while it is not back, a kernel message and the event once more, and asserts
that it came back in one of those waits.

Nothing here prints a credential, a page key or a cap: the driver compares them in memory and reports booleans, statuses
and counts, and the lab's sign-in secret is minted at run time. SVG_CAPS_REPORT names a directory for the driver's report.
Skips LOUDLY without the extension deps or a playwright browser; the CI extension job installs Chromium and runs served
files with ROMP_SERVED_TESTS_REQUIRE=1, which turns any skip into a failure there. SYNTHETIC fixtures only (session web,
the notes-api demo world, placeholder uuids, host TESTHOST)."""
import json
import lab_dist
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
EXT = os.path.join(ROOT, "vscode-extension")
sys.path.insert(0, HERE)
import test_file_caps_browser as fc      # noqa: E402  the served file-caps lab's helpers (the module, not its classes)
import test_ship_reship_served as _lab   # noqa: E402  the lab kernel's environment (the module, not its classes)

SID = fc.SID
SKIP_DEPS = "extension deps absent (npm ci not run here): the served lab needs them; CI's extension job has them and requires this file to run"
SKIP_BROWSER = "no playwright browser on this box: the served lab needs one; CI's extension job installs Chromium and requires this file to run"


def svg(w, h, fill):
    """A plain svg of one rectangle; its natural width tells the picture shown apart from the ones before it."""
    return '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d"><rect width="%d" height="%d" fill="%s"/></svg>\n' % (w, h, w, h, fill)


# The roads, in one page's life. The driver reports one RESULT line of booleans, statuses and counts.
DRIVER = fc.HEAD + r"""
const ctx = await browser.newContext(VIEW);
const page = await ctx.newPage();
const fileOf = (s) => { let u; try { u = new URL(s); } catch (e) { return null; } return u.pathname === "/file" || /^\/remote\/[^/]+\/file$/.test(u.pathname) ? u : null; };
const leafOf = (u) => (u.searchParams.get("path") || "").split("/").pop();
const asked = [];      // every /file request of the context: its kind, whether it carries a cap, the file's leaf
const answered = [];   // every /file answer: its status, whether its request carried a cap, its kind, the leaf, when it came
ctx.on("request", (q) => { const u = fileOf(q.url()); if (u) asked.push({ kind: q.resourceType(), cap: u.searchParams.has("cap"), leaf: leafOf(u) }); });
ctx.on("response", (r) => { const u = fileOf(r.url()); if (u) answered.push({ at: Date.now(), status: r.status(), cap: u.searchParams.has("cap"), kind: r.request().resourceType(), leaf: leafOf(u) }); });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));
/** The picture at `sel`: where its src points (this page's own host and the path, whether a cap and a version key ride in its
 *  query, whether it is a blob: or data: URL), whether it loaded, whether the heal parked it and the parked address carries a
 *  cap, and which data-marked box holds it. */
const pic = (sel) => page.evaluate((s) => {
  const i = document.querySelector(s);
  if (!i) return null;
  const a = i.getAttribute("src") || "";
  let u = null; try { u = new URL(a, location.href); } catch (e) { u = null; }
  let parkedCap = false; try { parkedCap = new URL(i.dataset.mdSrc || "", location.href).searchParams.has("cap"); } catch (e) { parkedCap = false; }
  return { hasSrc: a !== "", here: !!u && u.protocol === location.protocol && u.host === location.host, path: u ? u.pathname : "",
           cap: !!u && u.searchParams.has("cap"), v: !!u && u.searchParams.has("v"), blobOrData: /^(blob|data):/i.test(a),
           complete: i.complete, natural: i.naturalWidth, parked: i.classList.contains("md-img-failed"), parkedCap,
           inViewerBox: !!i.closest("[data-fv-picture]"), inPreviewBox: !!i.closest("[data-preview-full]") };
}, sel);
const loadedAt = (sel, want, ms) => page.waitForFunction(([s, w]) => { const i = document.querySelector(s); return !!i && i.complete && i.naturalWidth > 0 && (!w || i.naturalWidth === w); }, [sel, want || 0], { timeout: ms || cfg.deadline }).then(() => true, () => false);
const parkedAt = (sel) => page.waitForFunction((s) => { const i = document.querySelector(s); return !!i && i.classList.contains("md-img-failed"); }, sel, { timeout: cfg.deadline }).then(() => true, () => false);
const since = (t) => answered.filter((f) => f.at >= t).map(({ at, ...f }) => f);
const kernelMessage = () => page.evaluate(() => window.postMessage({ type: "probeTick" }, "*"));
const reconnect = () => page.evaluate(() => window.dispatchEvent(new Event("romp:wsup")));
const PREVIEW = '#content [data-preview-full] img[src*="diagram.svg"]';
const VIEWER = '#romp-fileview img.fileview-img';
async function openChat() {
  await page.waitForSelector('#tabs .tab[data-id="' + cfg.sid + '"]', { timeout: cfg.deadline });
  await page.click('#tabs .tab[data-id="' + cfg.sid + '"]');
}
async function openViewerOn(p) {
  await page.locator('#content .file-uri-link[data-path="' + p + '"]').first().click();
  await page.waitForSelector("#romp-fileview", { timeout: cfg.deadline });
}
async function reloadFromBar() {
  await page.evaluate(() => window.dispatchEvent(new Event("focus")));   // the viewer's check of the file on disk raises the bar
  const btn = page.locator('#romp-fileview button:text-is("Reload")').first();
  const up = await btn.waitFor({ timeout: cfg.deadline }).then(() => true, () => false);
  if (up) await btn.click();
  return up;
}
/** The markdown heal's re-request of the figure at `sel` (its file `file`, its leaf `leaf`), parked now: the file is written,
 *  then romp:wsup. The event's own probe can share a load of the address still in flight and ask nothing (the module's doc), so
 *  the figure gets the event, then a kernel message, then the event once more. `wait` is the wait it came back in (1, 2 or 3;
 *  0 if none), not which probe brought it back: a probe a kernel frame sends can land in any of the three, and the driver
 *  cannot tell them apart. */
async function heal(sel, file, leaf) {
  const r = { parked: await parkedAt(sel) };
  r.parkedPic = await pic(sel);
  fs.writeFileSync(file, cfg.lateSvg);
  const t = Date.now();
  await reconnect();
  r.wait = (await loadedAt(sel, 0, cfg.short)) ? 1 : 0;
  if (!r.wait) { await kernelMessage(); r.wait = (await loadedAt(sel, 0, cfg.short)) ? 2 : 0; }
  if (!r.wait) { await reconnect(); r.wait = (await loadedAt(sel)) ? 3 : 0; }
  r.pic = await pic(sel);
  r.answers = since(t).filter((f) => f.leaf === leaf);
  return r;
}
// the sign-in, through the kernel's own sign-in page; then the chat
await page.goto(cfg.base + "/login");
await page.fill("#t", cfg.secret);
await page.click("form button");
await page.waitForURL((u) => new URL(u).pathname === "/", { timeout: cfg.deadline });
await page.goto(cfg.base + "/chat");
await openChat();
out.keyed = await page.evaluate(() => Object.keys(localStorage).some((k) => k.startsWith("romp.pageKey")));
out.reads = await status(page, "/sessions");
// A. the preview box
out.A = { loaded: await loadedAt(PREVIEW), pic: await pic(PREVIEW) };
// B. the svg the author linked by its /file address
out.B = { loaded: await loadedAt('#content img[alt="authored svg"]'), pic: await pic('#content img[alt="authored svg"]') };
// C. the heal's re-request in the message
out.C = await heal('#content img[alt="late svg"]', cfg.late, "late.svg");
// D. the viewer's first open
let t = Date.now();
await openViewerOn("plots/diagram.svg");
out.D = { loaded: await loadedAt(VIEWER, 40), pic: await pic(VIEWER), answers: since(t).filter((f) => f.leaf === "diagram.svg") };
// E. the Source toggle and back
const SRC = '#romp-fileview button.fileview-btn:text-is("Source")';
await page.click(SRC);
out.E = { sourceUp: await page.waitForFunction((s) => { const b = document.querySelector('#romp-fileview button.fileview-btn.on'); return !!b && !document.querySelector(s); }, VIEWER, { timeout: cfg.deadline }).then(() => true, () => false) };
await page.click(SRC);
out.E.loaded = await loadedAt(VIEWER, 40);
out.E.pic = await pic(VIEWER);
// F. the viewer's Reload after a change on disk
fs.writeFileSync(cfg.diagram, cfg.svgB);
t = Date.now();
out.F = { bar: await reloadFromBar() };
out.F.loaded = await loadedAt(VIEWER, 50);
out.F.pic = await pic(VIEWER);
out.F.answers = since(t).filter((f) => f.leaf === "diagram.svg");
// G. bytes that do not decode: the re-ask, then the pane; the way back: a kernel message, then romp:wsup if still not back
fs.writeFileSync(cfg.diagram, cfg.svgBroken);
t = Date.now();
out.G = { bar: await reloadFromBar() };
out.G.pane = await page.waitForFunction(() => Array.from(document.querySelectorAll("#romp-fileview .fileview-err")).some((e) => (e.textContent || "").startsWith("this image failed to load or decode")), null, { timeout: cfg.deadline }).then(() => true, () => false);
out.G.reask = since(t).filter((f) => f.leaf === "diagram.svg");
fs.writeFileSync(cfg.diagram, cfg.svgC);
await kernelMessage();
out.G.wait = (await loadedAt(VIEWER, 60)) ? 1 : 0;   // the wait it came back in, as heal's `wait`: not which probe brought it
if (!out.G.wait) { await reconnect(); out.G.wait = (await loadedAt(VIEWER, 60)) ? 2 : 0; }
out.G.pic = await pic(VIEWER);
// H. the heal's re-request inside a note the viewer renders
await page.keyboard.press("Escape").catch(() => {});
await openViewerOn("docs/figs.md");
out.H = { figure: await loadedAt('#romp-fileview img[alt="note svg"]'), figurePic: await pic('#romp-fileview img[alt="note svg"]') };
Object.assign(out.H, await heal('#romp-fileview img[alt="note late"]', cfg.lateNote, "late-note.svg"));
// I. a page reload, then the preview box and the viewer's first open again
await page.keyboard.press("Escape").catch(() => {});
await page.reload();
await openChat();
out.I = { preview: await loadedAt(PREVIEW), previewPic: await pic(PREVIEW) };
await openViewerOn("plots/diagram.svg");
out.I.viewer = await loadedAt(VIEWER, 60);
out.I.viewerPic = await pic(VIEWER);
out.refused = answered.filter((f) => f.status === 401 || f.status === 403).map(({ at, ...f }) => f);
out.imagesWithoutCap = asked.filter((f) => f.kind === "image" && !f.cap);
out.images = asked.filter((f) => f.kind === "image").length;
out.errors = errors;
fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
await browser.close();
process.exit(0);
"""


class SvgPictureUnderThePageKey(unittest.TestCase):
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
            raise unittest.SkipTest(SKIP_DEPS)
        probe = subprocess.run(["node", "-e", "const p=require(process.argv[1]);process.stdout.write(p.chromium.executablePath())",
                                os.path.join(EXT, "node_modules", "playwright")], capture_output=True, text=True)
        if probe.returncode != 0 or not os.path.exists(probe.stdout.strip()):
            raise unittest.SkipTest(SKIP_BROWSER)
        cls.lab = tempfile.mkdtemp(prefix="svg-caps-")
        cls.port, cls.secret = fc._free_port(), os.urandom(18).hex()   # minted at run time, never printed
        dist = os.path.join(cls.lab, "dist")
        lab_dist.copy_dist(dist)   # the checkout's ONE build of the bundles, copied under its lock (tests/lab_dist.py)
        state = os.path.join(cls.lab, "xdg", "romp")
        cwd = os.path.join(cls.lab, "proj")
        for d in ("names", "sdk", "states"):
            os.makedirs(os.path.join(state, d), exist_ok=True)
        for d in ("docs", "plots"):
            os.makedirs(os.path.join(cwd, d), exist_ok=True)
        cls.diagram = os.path.join(cwd, "plots", "diagram.svg")
        Path(cls.diagram).write_text(svg(40, 30, "#3c78c8"))
        cls.late = os.path.join(cwd, "plots", "late.svg")             # absent until road C writes it
        cls.late_note = os.path.join(cwd, "plots", "late-note.svg")   # absent until road H writes it
        Path(cwd, "docs", "figs.md").write_text("# Figures\n\nThe notes-api diagram:\n\n![note svg](../plots/diagram.svg)\n\n"
                                                "The one still being drawn:\n\n![note late](../plots/late-note.svg)\n")
        q = lambda p: "path=%s&sid=%s" % (urllib.request.quote(p, safe=""), SID)
        Path(state, "names", SID).write_text("web\t%s\t#9cd2ff\t#0c1a2e\n" % cwd)
        Path(state, "sdk", SID + ".json").write_text(json.dumps(
            {"sid": SID, "name": "web", "cwd": cwd, "mode": "auto", "effort": "high", "lastSid": SID, "alive": True,
             "model": "claude-opus-5", "liveModel": "Opus 5"}))
        claude = os.path.join(cls.lab, "claude")
        proj = os.path.join(claude, "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(cwd)))
        os.makedirs(proj, exist_ok=True)
        reply = ("The notes-api diagram is at plots/diagram.svg and the figure notes at docs/figs.md.\n\n"
                 "![authored svg](/file?%s)\n\n![late svg](/file?%s)\n" % (q(cls.diagram), q(cls.late)))
        Path(proj, SID + ".jsonl").write_text(
            json.dumps({"type": "user", "uuid": fc.U_UUID, "parentUuid": None, "timestamp": "2026-09-05T00:00:00.000Z", "sessionId": SID,
                        "message": {"role": "user", "content": "Where is the notes-api diagram?"}}) + "\n" +
            json.dumps({"type": "assistant", "uuid": fc.A_UUID, "parentUuid": fc.U_UUID, "timestamp": "2026-09-05T00:00:05.000Z", "sessionId": SID,
                        "message": {"role": "assistant", "model": "claude-opus-5", "content": [{"type": "text", "text": reply}], "stop_reason": "end_turn"}}) + "\n")
        env = _lab.kernel_env(cls.lab, claude, dist, cls.port, cls.secret, ROMP_HOST_NAME="TESTHOST")
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
        """The kernel log's tail for a failure message, the lab's secret masked (it never appears there; belt)."""
        try:
            return open(self.klog).read()[-1500:].replace(self.secret, "<secret>")
        except OSError:
            return ""

    def _drive(self):
        cfg = os.path.join(self.lab, "cfg.json")
        with open(cfg, "w") as f:
            json.dump({"base": "http://127.0.0.1:%d" % self.port, "secret": self.secret, "sid": SID, "deadline": 30000, "short": 5000,
                       "engine": "chromium", "diagram": self.diagram, "late": self.late, "lateNote": self.late_note,
                       "lateSvg": svg(30, 20, "#2a8a4a"), "svgB": svg(50, 30, "#c83c3c"), "svgC": svg(60, 30, "#8a2ac8"),
                       "svgBroken": '<svg xmlns="http://www.w3.org/2000/svg" width="50" height="30"><rect width="50"'}, f)
        driver = os.path.join(self.lab, "driver.mjs")
        with open(driver, "w") as f:
            f.write(DRIVER)
        p = subprocess.run(["node", driver], capture_output=True, text=True, timeout=600,
                           env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg))
        os.unlink(cfg)
        if p.returncode == 3:
            raise unittest.SkipTest(SKIP_BROWSER)
        mask = lambda s: s.replace(self.secret, "<secret>")
        self.assertEqual(p.returncode, 0, "driver failed:\n" + mask(p.stdout[-3000:] + p.stderr[-3000:]) + "\nkernel:\n" + self._klog_tail())
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
        self.assertIsNotNone(line, "driver printed no result:\n" + mask(p.stdout[-3000:]))
        self.assertNotIn(self.secret, line, "the driver's report carries no credential")
        if os.environ.get("SVG_CAPS_REPORT"):     # a directory: the report (booleans, statuses, counts) for the record
            with open(os.path.join(os.environ["SVG_CAPS_REPORT"], "svg-picture-caps.json"), "w") as f:
                f.write(line[len("RESULT:"):] + "\n")
        return json.loads(line[len("RESULT:"):])

    def _on_address(self, pc, road, v=False):
        """The property on one road: the picture is there, its src is this page's own /file address and never a blob: or data:
        URL, it carries a cap (and the version key where `v`), and it loaded."""
        self.assertIsNotNone(pc, road + ": the picture is on the page")
        self.assertTrue(pc["here"] and pc["path"] == "/file", road + ": src is this page's own /file address: %r" % pc)
        self.assertFalse(pc["blobOrData"], road + ": never an object or data URL: %r" % pc)
        self.assertTrue(pc["cap"], road + ": the address carries its cap: %r" % pc)
        if v:
            self.assertTrue(pc["v"], road + ": the address carries the version key: %r" % pc)
        self.assertGreater(pc["natural"], 0, road + ": the picture loaded: %r" % pc)

    def _healed(self, h, road):
        """The heal's re-request on road C or H: the figure parked at a capped address, came back at its capped /file address
        in one of the waits (after the event, then a kernel message, then the event once more, each sent only while it is not
        back), and the answer to its re-request was a capped 200. Which probe brought it back is not checked."""
        self.assertTrue(h["parked"], road + ": the figure parked while its file was absent")
        self.assertTrue(h["parkedPic"]["parkedCap"], road + ": the parked address carries its cap: %r" % h["parkedPic"])
        self.assertTrue(h["wait"], road + ": the figure came back in one of the waits (after the event, a kernel message, the event once more): %r" % h)
        self._on_address(h["pic"], road)
        self.assertTrue(any(f["status"] == 200 and f["cap"] for f in h["answers"]), road + ": its re-request was answered 200, capped: %r" % h["answers"])

    def test_every_road_shows_the_svg_at_its_capped_file_address(self):
        r = self._drive()
        self.assertTrue(r["keyed"], "the sign-in stored a page key, so the page's /file addresses carry caps")
        self.assertEqual(r["reads"], 200, "the page is signed in: a fetch through its wrapper reads /sessions")
        with self.subTest("A preview box"):
            self.assertTrue(r["A"]["loaded"], "the preview box's picture loaded")
            self._on_address(r["A"]["pic"], "A")
            self.assertTrue(r["A"]["pic"]["inPreviewBox"], "the picture is inside the preview box's data mark")
        with self.subTest("B authored"):
            self.assertTrue(r["B"]["loaded"], "the authored svg loaded")
            self._on_address(r["B"]["pic"], "B")
        with self.subTest("C heal in the message"):
            self._healed(r["C"], "C")
        with self.subTest("D viewer first open"):
            self.assertTrue(r["D"]["loaded"], "the viewer's picture loaded")
            self._on_address(r["D"]["pic"], "D", v=True)
            self.assertTrue(r["D"]["pic"]["inViewerBox"], "the picture is inside the viewer's picture box's data mark")
        with self.subTest("E Source and back"):
            self.assertTrue(r["E"]["sourceUp"], "the Source view came up")
            self.assertTrue(r["E"]["loaded"], "the picture came back")
            self._on_address(r["E"]["pic"], "E", v=True)
        with self.subTest("F Reload"):
            self.assertTrue(r["F"]["bar"], "the changed-on-disk bar offered Reload")
            self.assertTrue(r["F"]["loaded"], "the new picture loaded")
            self._on_address(r["F"]["pic"], "F", v=True)
            self.assertTrue(any(f["kind"] == "image" and f["status"] == 200 and f["cap"] for f in r["F"]["answers"]), r["F"]["answers"])
        with self.subTest("G re-ask and the way back"):
            self.assertTrue(r["G"]["bar"], "the changed-on-disk bar offered Reload")
            self.assertTrue(r["G"]["pane"], "the re-ask ended on the failure pane")
            imgs = [f for f in r["G"]["reask"] if f["kind"] == "image"]
            self.assertGreaterEqual(len(imgs), 2, "the picture and the re-ask's picture were both asked: %r" % r["G"]["reask"])
            self.assertTrue(all(f["cap"] and f["status"] == 200 for f in imgs), r["G"]["reask"])
            self.assertTrue(r["G"]["wait"], "the picture came back in one of the waits (after the kernel message, then romp:wsup): %r" % r["G"])
            self._on_address(r["G"]["pic"], "G", v=True)
        with self.subTest("H heal in the note"):
            self.assertTrue(r["H"]["figure"], "the note's svg figure loaded")
            self._on_address(r["H"]["figurePic"], "H's figure")
            self._healed(r["H"], "H")
        with self.subTest("I page reload"):
            self.assertTrue(r["I"]["preview"], "the preview box's picture loaded after the reload")
            self._on_address(r["I"]["previewPic"], "I's preview box")
            self.assertTrue(r["I"]["viewer"], "the viewer's picture loaded after the reload")
            self._on_address(r["I"]["viewerPic"], "I's viewer", v=True)
        self.assertGreater(r["images"], 10, "the roads asked their pictures")
        self.assertEqual(r["refused"], [], "no /file request was refused")
        self.assertEqual(r["imagesWithoutCap"], [], "every image request to /file carried its cap")
        self.assertEqual(r["errors"], [], "the page threw nothing")


if __name__ == "__main__":
    unittest.main()
