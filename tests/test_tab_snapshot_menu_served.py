#!/usr/bin/env python3
"""THE SECTION VIEW'S ROW MENU ON THE REAL PAGE (round 1 of the review, 2026-09-18): a right-click on a row of a tag's
at-a-glance view opens the tab's context menu for that row's session, and Rename from a hidden row's menu edits the name
on the row (ui/webview/render.ts snapshotHost's contextmenu listener, startTabRename's row seat). The node test
(ui/webview/tab-snapshot-menu.test.ts) executes the slices over a fake DOM and the browser leg (tab-hide-browser.test.ts)
drives a composed probe page, which CI never runs (Playwright is installed after that step); this module is the road CI
walks for the feature: the served /chat page of a hermetic kernel, the boot tests/test_tab_overview_mode_served.py uses
(the notes-api world: four SDK-registered sessions with closed transcripts under two tags, web and api under infra, tests
under ui, docs untagged; hosts off through kernel_env), driven by Playwright's chromium with real mouse gestures.

One browser run, read by the tests below:
  1. the view of infra opened through the header's own door (the open header's count); api's tab right-clicked on the
     strip while shown, its menu's rows recorded; api hidden with the row's own Hide button and the Hidden fold opened
     by its head (the store is never seeded by hand); a right-click on the hidden row opens the .ctx-menu card with the
     tab menu's rows, row for row, the Hide tab row reading Show tab;
  2. Rename picked from that menu seats the strip's editor (.tab-rename) inside the row's item, after the row's button
     and before the Hide or Show button, with its computed flex and margins, the auto right margin leaving the button at
     the item's right edge (the sheet's .snap-item > .tab-rename rule; round 1 of the review, 2026-09-18: the button had
     sat 6px after the field), the name seeded and selected, the input focused;
  3. a new name and Enter post renameSession with the bare name; the kernel renames (the names/ entry, the authoritative
     store, carries it) and its push renames the row; Show tab from the row's menu puts the tab back on the strip under
     the new name, and the row moves out of the fold with it.
Every wait is on DOM state (waitForFunction, waitForSelector), never a fixed sleep. Skips LOUDLY without the extension
deps or a Playwright browser, the way the siblings do. The kernel runs in its own process group and the class ends the
whole group. SYNTHETIC fixtures only (the notes-api demo world, TESTHOST)."""
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import lab_dist

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
EXT = os.path.join(ROOT, "vscode-extension")
sys.path.insert(0, HERE)
import test_ship_reship_served as _lab   # noqa: E402  the lab kernel's environment: a list of names, never a copy of the runner's

SIDS = {"web": "aaaaaaaa-1111-2222-3333-555555555555", "api": "bbbbbbbb-1111-2222-3333-555555555555",
        "tests": "cccccccc-1111-2222-3333-555555555555", "docs": "dddddddd-1111-2222-3333-555555555555"}
COLORS = {"web": ("#9cd2ff", "#0c1a2e"), "api": ("#1EA1EB", "#ffffff"), "tests": ("#54B204", "#ffffff"), "docs": ("#c98cff", "#1a0c2e")}
TAGS = [{"id": "tag-infra", "name": "infra", "color": "#4EC9B0", "members": [SIDS["web"], SIDS["api"]]},
        {"id": "tag-ui", "name": "ui", "color": "#e5a50a", "members": [SIDS["tests"]]}]
NEW_NAME = "api-two"


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


DRIVER = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const { chromium } = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
let browser;
try { browser = await chromium.launch(); } catch (e) { fs.writeSync(2, "no browser: " + e + "\n"); process.exit(3); }
const out = { errors: [] };
const finish = async () => { fs.writeFileSync(cfg.out, JSON.stringify(out)); await browser.close(); process.exit(0); };
const die = async (why) => { out.died = why; await finish(); };
process.on("unhandledRejection", async (e) => { await die("unhandled: " + String(e).split("\n")[0]); });
const page = await browser.newPage({ viewport: { width: 1100, height: 760 } });
page.on("pageerror", (e) => out.errors.push(String(e)));
// what the page posts to its host (the strip's renameSession), recorded as the Sessions pane's served test records it
await page.addInitScript(() => {
  window.__posted = [];
  let real;
  Object.defineProperty(window, "acquireVsCodeApi", { configurable: true,
    get() { return function () { const api = real ? real() : {}; const post = api.postMessage ? api.postMessage.bind(api) : () => {};
      api.postMessage = (m) => { window.__posted.push(m); return post(m); }; return api; }; },
    set(fn) { real = fn; } });
});
const T = 20000;
// a condition that never comes is recorded as the step that failed, so the test reads red on that step and not on a dead driver
const waitFn = async (fn, arg, why) => page.waitForFunction(fn, arg, { timeout: T }).catch(async (e) => { await die(why + " (" + String(e).split("\n")[0] + ")"); });
const waitSel = async (sel, why) => page.waitForSelector(sel, { timeout: T }).catch(async (e) => { await die(why + " (" + String(e).split("\n")[0] + ")"); });
const itemSel = (id) => '#tab-snapshot .snap-item[data-id="' + id + '"]';
const rowSel = (id) => itemSel(id) + " > .snap-row";
// the open card's rows, top-level, each by its label; a divider, the colour swatches and any other row by its class, so a row
// added, removed or reworded on one side shows on the other (the node test's menuLabel)
const menuShape = () => page.evaluate(() => {
  const m = document.querySelector(".ctx-menu");
  if (!m) return null;
  return Array.from(m.children).map((c) => {
    const l = c.querySelector(".ctx-item-label");
    if (c.classList.contains("ctx-item") && l) return l.textContent;
    if (c.classList.contains("ctx-sep")) return "<divider>";
    if (c.classList.contains("ctx-colors")) return "<colour swatches>";
    return "<" + c.className + ">";
  });
});
const hideRowLabel = () => page.evaluate(() => { const r = document.querySelector(".ctx-menu .ctx-item-hide .ctx-item-label"); return r ? r.textContent : null; });
const noMenu = () => waitFn(() => !document.querySelector(".ctx-menu"), null, "the menu never closed");

// ---- load: the four tabs, then the view of infra through the header's door (an open header's count is the door, a button) ----
await page.goto(cfg.chat);
await waitFn((sids) => { const ids = Array.from(document.querySelectorAll("#tabs .tab[data-id]")).map((t) => t.dataset.id); return sids.every((s) => ids.includes(s)); },
  Object.values(cfg.sids), "the strip never showed the four tabs");
await page.locator('#tabs .tab-group-head[data-group="infra"] .tab-group-door').click();
await waitFn(() => { const h = document.getElementById("tab-snapshot"); return !!h && getComputedStyle(h).display !== "none" && document.body.classList.contains("snap-mode"); }, null, "the view of infra never showed");
// api's row painted from its frame: a loading row (no frame yet) would open the menu for a skeleton alone and startTabRename needs the session
await waitFn((id) => { const r = document.querySelector('#tab-snapshot .snap-item[data-id="' + id + '"] > .snap-row'); return !!r && !r.classList.contains("loading"); }, cfg.sids.api, "api's row never left its loading state");
out.heading = await page.evaluate(() => { const h = document.querySelector("#tab-snapshot h2.snap-head"); return h ? h.textContent.trim() : null; });
out.rowsShown = await page.evaluate(() => Array.from(document.querySelectorAll("#tab-snapshot > .snap-list > .snap-item")).map((i) => i.dataset.id));
// ---- 1. the tab's own menu for api while shown: the rows the row's menu must carry ----
await page.locator('#tabs .tab[data-id="' + cfg.sids.api + '"]').click({ button: "right" });
await waitSel(".ctx-menu", "a right-click on api's tab never opened the tab's menu");
out.tabMenu = await menuShape();
out.tabHideRow = await hideRowLabel();
await page.keyboard.press("Escape");
await noMenu();
// hide api with the view's own Hide button: its tab leaves the strip, its row moves under the Hidden fold, which starts closed
await page.locator(itemSel(cfg.sids.api) + ' > .snap-act[data-act="hide"]').click();
await waitFn((id) => !!document.querySelector('#tab-snapshot .snap-hidden-list .snap-item[data-id="' + id + '"]') && !document.querySelector('#tabs .tab[data-id="' + id + '"]'),
  cfg.sids.api, "api never moved under the Hidden fold with its tab gone from the strip");
out.foldBefore = await page.evaluate(() => getComputedStyle(document.querySelector("#tab-snapshot .snap-hidden-list")).display);
await page.locator("#tab-snapshot .snap-hidden-head").click();
await waitFn(() => getComputedStyle(document.querySelector("#tab-snapshot .snap-hidden-list")).display !== "none", null, "the Hidden fold never opened");
// the hidden row, right-clicked with the mouse
await page.locator(rowSel(cfg.sids.api)).click({ button: "right" });
await waitSel(".ctx-menu", "a right-click on the hidden row never opened a menu");
out.rowMenu = await menuShape();
out.rowHideRow = await hideRowLabel();
// ---- 2. Rename: the editor on the row, its box ----
await page.locator('.ctx-menu .ctx-item:has(.ctx-item-label:text-is("Rename"))').click();
await waitFn((id) => !!document.querySelector('#tab-snapshot .snap-item[data-id="' + id + '"] > .tab-rename'), cfg.sids.api, "Rename never seated the editor on the row");
out.editor = await page.evaluate((id) => {
  const item = document.querySelector('#tab-snapshot .snap-item[data-id="' + id + '"]');
  const input = item.querySelector(":scope > .tab-rename"), row = item.querySelector(":scope > .snap-row"), act = item.querySelector(":scope > .snap-act");
  const box = (e) => { const b = e.getBoundingClientRect(); return { left: b.left, right: b.right, top: b.top, bottom: b.bottom, width: b.width, height: b.height }; };
  const cs = getComputedStyle(input), ics = getComputedStyle(item);
  return { children: Array.from(item.children).map((c) => c.className.split(" ")[0]), value: input.value, focused: document.activeElement === input,
           selected: input.selectionEnd - input.selectionStart, flex: [cs.flexGrow, cs.flexShrink, cs.flexBasis],
           margin: [cs.marginTop, cs.marginRight, cs.marginBottom, cs.marginLeft], rowDisplay: getComputedStyle(row).display,
           itemDisplay: ics.display, itemGap: ics.columnGap, itemPaddingRight: ics.paddingRight, actText: act.textContent,
           item: box(item), input: box(input), act: box(act), strip: !!document.querySelector("#tabs .tab-rename") };
}, cfg.sids.api);
// ---- 3. a new name (the seeded one is selected: the typing replaces it), Enter: the post, the kernel's push, Show tab ----
await page.keyboard.type(cfg.newName);
await page.keyboard.press("Enter");
await waitFn(() => (window.__posted || []).some((m) => m && m.type === "renameSession"), null, "Enter never posted renameSession");
out.posted = await page.evaluate(() => window.__posted.filter((m) => m && m.type === "renameSession").map((m) => [m.id, m.name]));
out.afterEnter = await page.evaluate((id) => { const item = document.querySelector('#tab-snapshot .snap-item[data-id="' + id + '"]'); const row = item.querySelector(":scope > .snap-row");
  return { input: !!item.querySelector(":scope > .tab-rename"), rowHidden: getComputedStyle(row).display === "none", focusedRow: document.activeElement === row }; }, cfg.sids.api);
await waitFn((a) => { const n = document.querySelector('#tab-snapshot .snap-hidden-list .snap-item[data-id="' + a.id + '"] .snap-sess'); return !!n && n.textContent === a.name; },
  { id: cfg.sids.api, name: cfg.newName }, "the kernel's push never renamed the hidden row");
out.rowName = await page.evaluate((id) => document.querySelector('#tab-snapshot .snap-item[data-id="' + id + '"] .snap-sess').textContent, cfg.sids.api);
await page.locator(rowSel(cfg.sids.api)).click({ button: "right" });
await waitSel(".ctx-menu", "a second right-click on the renamed hidden row never opened a menu");
out.showRowLabel = await hideRowLabel();
await page.locator(".ctx-menu .ctx-item-hide").click();
await waitFn((a) => { const t = document.querySelector('#tabs .tab[data-id="' + a.id + '"] .tab-label'); const r = document.querySelector('#tab-snapshot > .snap-list > .snap-item[data-id="' + a.id + '"] .snap-sess');
  return !!t && t.textContent.trim() === a.name && !!r && r.textContent === a.name; }, { id: cfg.sids.api, name: cfg.newName }, "Show tab never put the renamed tab back on the strip");
out.shown = await page.evaluate((id) => ({ tab: document.querySelector('#tabs .tab[data-id="' + id + '"] .tab-label').textContent.trim(),
  row: document.querySelector('#tab-snapshot > .snap-list > .snap-item[data-id="' + id + '"] .snap-sess').textContent,
  hiddenRows: document.querySelectorAll("#tab-snapshot .snap-hidden-list .snap-item").length }), cfg.sids.api);
await finish();
"""


class ServedTabSnapshotMenu(unittest.TestCase):
    maxDiff = None   # the methods are lettered, not numbered: the runner redacts a long token that holds a digit as a credential, which blanks a failure's name

    @classmethod
    def setUpClass(cls):
        try:
            cls._boot()
            cls._drive()
        except BaseException:
            cls.tearDownClass()
            raise

    @classmethod
    def _boot(cls):
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            raise unittest.SkipTest("extension deps absent (npm ci not run here): the served guard needs them")
        probe = subprocess.run(["node", "-e", "const p=require(process.argv[1]);process.stdout.write(p.chromium.executablePath())",
                                os.path.join(EXT, "node_modules", "playwright")], capture_output=True, text=True)
        if probe.returncode != 0 or not os.path.exists(probe.stdout.strip()):
            raise unittest.SkipTest("no playwright browser on this box: the served guard needs one (CI installs none)")
        cls.lab = tempfile.mkdtemp(prefix="tab-snapmenu-")
        dist = os.path.join(cls.lab, "dist")
        lab_dist.copy_dist(dist)   # the checkout's ONE build of the bundles, copied under its lock (tests/lab_dist.py)
        cls.state = os.path.join(cls.lab, "xdg", "romp")
        claude = os.path.join(cls.lab, "claude")
        cwd = os.path.join(cls.lab, "proj")
        for d in ("names", "sdk"):
            os.makedirs(os.path.join(cls.state, d), exist_ok=True)
        os.makedirs(cwd, exist_ok=True)
        proj = os.path.join(claude, "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(cwd)))
        os.makedirs(proj, exist_ok=True)
        t0 = int(time.time()) - 900
        for i, (name, sid) in enumerate(SIDS.items()):
            bg, fg = COLORS[name]
            Path(cls.state, "names", sid).write_text("%s\t%s\t%s\t%s\n" % (name, cwd, bg, fg))
            # registered SDK records with closed transcripts: the tabs are loaded sessions (the tab menu's gate), nothing is spawned
            Path(cls.state, "sdk", sid + ".json").write_text(json.dumps(
                {"sid": sid, "name": name, "cwd": cwd, "mode": "auto", "effort": "high", "lastSid": sid, "alive": True,
                 "model": "claude-opus-5", "liveModel": "Opus 5"}))
            recs = [{"type": "user", "timestamp": iso(t0 + i), "uuid": "u1", "parentUuid": None, "promptSource": "typed", "sessionId": sid,
                     "message": {"role": "user", "content": "what does the %s session do in notes-api?" % name}},
                    {"type": "assistant", "timestamp": iso(t0 + i + 5), "uuid": "a1", "parentUuid": "u1", "sessionId": sid,
                     "message": {"role": "assistant", "model": "claude-opus-5", "stop_reason": "end_turn",
                                 "content": [{"type": "text", "text": "It keeps the %s side of the notes-api tidy." % name}]}}]
            Path(proj, sid + ".jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs))
        # the tags: two, holding three of the four sessions; the fourth is the untagged trail
        Path(cls.state, "timeline-views.json").write_text(json.dumps({"active": "all", "tags": TAGS}))
        Path(cls.state, "usage.json").write_text(json.dumps({"five_hour": {"pct": 10}, "seven_day": {"pct": 10}}))
        cls.port, cls.token = _free_port(), "testtok-snapmenu"
        env = _lab.kernel_env(cls.lab, claude, dist, cls.port, cls.token, ROMP_HOST_NAME="TESTHOST")   # floors the lab root's session-hosts off
        cls.klog = os.path.join(cls.lab, "kernel.log")
        # its own process group: the class ends the kernel WITH every child it spawned (tearDownClass), not the one pid
        cls.kernel = subprocess.Popen([os.path.join(BIN, "romp-kernel")], stdout=open(cls.klog, "w"), stderr=subprocess.STDOUT, env=env,
                                      start_new_session=True)
        for _ in range(120):
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/healthz" % cls.port, timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise unittest.SkipTest("hermetic kernel never served /healthz here")

    @classmethod
    def _drive(cls):
        cls.result, cls.driver_error = None, None
        cfg = os.path.join(cls.lab, "cfg.json")
        res = os.path.join(cls.lab, "result.json")
        with open(cfg, "w") as f:
            json.dump({"chat": "http://127.0.0.1:%d/chat?token=%s" % (cls.port, cls.token), "out": res, "sids": SIDS, "newName": NEW_NAME}, f)
        driver = os.path.join(cls.lab, "driver.mjs")
        with open(driver, "w") as f:
            f.write(DRIVER)
        # the driver in its own process group too: a driver that hangs is ended with its browser, never left behind
        p = subprocess.Popen(["node", driver], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True,
                             env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg))
        try:
            so, _ = p.communicate(timeout=300)
        except subprocess.TimeoutExpired:
            _end_group(p)
            so, _ = p.communicate()
            cls.driver_error = "driver timed out; partial output:\n%s" % (so or "")[-3000:]
            return
        if p.returncode == 3:
            raise unittest.SkipTest("no playwright browser on this box: the served guard needs one (CI installs none)")
        if p.returncode != 0 or not os.path.exists(res):
            cls.driver_error = "driver failed:\n" + (so or "")[-3000:] + "\nkernel:\n" + open(cls.klog).read()[-1500:]
            return
        with open(res) as f:
            r = json.load(f)
        if "died" in r:
            cls.driver_error = "driver aborted early: %s\n%s\nkernel:\n%s" % (r["died"], json.dumps(r, indent=1)[-3000:], open(cls.klog).read()[-1500:])
            return
        # the kernel's own record of the name, read after the page showed the push: the names/ entry the backend rewrites (the
        # authoritative store; the page's label is what it rendered from the push)
        r["namesEntry"] = Path(cls.state, "names", SIDS["api"]).read_text().split("\t")[0]
        cls.result = r

    @classmethod
    def tearDownClass(cls):
        k = getattr(cls, "kernel", None)
        if k:
            _end_group(k)
        shutil.rmtree(getattr(cls, "lab", ""), ignore_errors=True)

    def setUp(self):
        if self.driver_error:
            self.fail(self.driver_error)

    def test_a_the_page_threw_nothing_and_the_view_of_infra_showed_its_two_rows(self):
        r = self.result
        self.assertEqual(r["errors"], [], "the page threw nothing: %r" % r["errors"])
        self.assertTrue(r["heading"] and r["heading"].startswith("Overview of"), "the view's heading: %r" % r["heading"])
        self.assertEqual(sorted(r["rowsShown"]), sorted([SIDS["web"], SIDS["api"]]), "infra's two members as shown rows: %r" % r["rowsShown"])

    def test_b_a_right_click_on_the_hidden_row_opens_the_tab_menu_with_the_tabs_rows_and_show_tab(self):
        r = self.result
        self.assertIsNotNone(r["tabMenu"], "api's tab opened its menu on the strip while shown")
        self.assertEqual(r["tabHideRow"], "Hide tab", "the shown copy's row: %r" % r["tabMenu"])
        self.assertEqual(r["foldBefore"], "none", "the Hidden fold starts closed after the hide; the head's click opens it")
        self.assertIsNotNone(r["rowMenu"], "the hidden row opened a menu")
        self.assertGreater(len(r["rowMenu"]), 8, "a full menu: %r" % r["rowMenu"])
        self.assertIn("Rename", r["rowMenu"])
        self.assertIn("Show tab", r["rowMenu"], "the hidden copy's Hide tab row reads Show tab: %r" % r["rowMenu"])
        self.assertEqual(r["rowHideRow"], "Show tab")
        want = ["Show tab" if lbl == "Hide tab" else lbl for lbl in r["tabMenu"]]
        self.assertEqual(r["rowMenu"], want, "the row's menu is the tab's, row for row, the hide row's word for the hidden copy apart:\n row: %r\n tab: %r" % (r["rowMenu"], r["tabMenu"]))

    def test_c_rename_seats_the_strips_editor_in_the_row_with_the_sheets_box_and_the_button_at_the_right_edge(self):
        e = self.result["editor"]
        self.assertEqual(e["children"], ["snap-row", "tab-rename", "snap-act"], "after the row's button, before the Hide or Show button: %r" % e["children"])
        self.assertEqual((e["value"], e["focused"], e["selected"], e["rowDisplay"], e["strip"]), ("api", True, 3, "none", False),
                         "the name seeded and selected, the input focused, the row's button hidden, no editor on the strip: %r" % e)
        self.assertEqual(e["actText"], "Show", "the hidden row's button")
        # the sheet's rule (.snap-item > .tab-rename): the strip's input as a flex item that neither grows nor takes a basis of its
        # own, 4px down and 8px in, and an AUTO right margin
        self.assertEqual(e["flex"], ["0", "1", "auto"], "flex: 0 1 auto: %r" % e["flex"])
        self.assertEqual((e["margin"][0], e["margin"][2], e["margin"][3]), ("4px", "0px", "8px"), "margin: 4px _ 0 8px: %r" % e["margin"])
        self.assertEqual((e["itemDisplay"], e["itemGap"], e["itemPaddingRight"]), ("flex", "6px", "0px"), "the item's own box: %r" % e)
        # the auto right margin takes the free space, so the Hide or Show button stays at the item's right edge while the name is
        # edited (round 1 of the review, 2026-09-18: the button had sat 6px after the field, a visual misplacement); the used
        # margin is what the engine resolved it to, the gap between the field and the button
        used = float(e["margin"][1].rstrip("px"))
        self.assertGreater(used, 0, "the auto margin resolved to the free space: %r" % e["margin"])
        self.assertLessEqual(abs(e["act"]["right"] - e["item"]["right"]), 1, "the button's right edge is the item's: act %r item %r" % (e["act"], e["item"]))
        self.assertLessEqual(abs(e["input"]["right"] + used + 6 - e["act"]["left"]), 1, "field, its auto margin, the gap, the button: %r" % e)
        self.assertGreater(e["act"]["left"] - e["input"]["right"], 6 + 1, "free space stands between the field and the button, not after the button: %r" % e)

    def test_d_enter_posts_the_rename_the_kernel_records_it_and_the_row_and_the_strips_tab_carry_the_new_name(self):
        r = self.result
        self.assertEqual(r["posted"], [[SIDS["api"], NEW_NAME]], "one renameSession post, the bare id and the new name: %r" % r["posted"])
        self.assertEqual(r["afterEnter"], {"input": False, "rowHidden": False, "focusedRow": True}, "the editor gone, the row's button back with the focus: %r" % r["afterEnter"])
        self.assertEqual(r["namesEntry"], NEW_NAME, "the kernel's names/ entry carries the new name: %r" % r["namesEntry"])
        self.assertEqual(r["rowName"], NEW_NAME, "the kernel's push renamed the hidden row: %r" % r["rowName"])
        self.assertEqual(r["showRowLabel"], "Show tab", "the renamed row's menu still reads Show tab")
        self.assertEqual(r["shown"], {"tab": NEW_NAME, "row": NEW_NAME, "hiddenRows": 0},
                         "Show tab put the tab back on the strip under the new name and the row among the shown rows: %r" % r["shown"])


def _end_group(p):
    """End a lab process WITH its process group (the kernel and whatever it spawned; the driver and its browser): SIGTERM the
    group, wait, then SIGKILL what is left; the Popen itself is reaped either way."""
    for sig in (signal.SIGTERM, signal.SIGKILL):   # the group first, whether or not its leader still runs: a dead leader can leave children
        try:
            os.killpg(p.pid, sig)
        except ProcessLookupError:
            pass
        try:
            p.wait(timeout=5)
            return
        except subprocess.TimeoutExpired:
            continue
    p.wait()


if __name__ == "__main__":
    unittest.main()
