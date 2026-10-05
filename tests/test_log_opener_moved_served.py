#!/usr/bin/env python3
"""The Log opens from the gear, not the bottom bar (T290, the user 2026-09-09: the bar keeps only its few
important controls). The desktop bar's action cluster no longer carries the Log's triangle; the settings panel's
Updates & debug section ends with an "Open log" button that closes the modal and asks the shell for the Log panel
({romp:'openLog'} → window.__rompOpenErrs), the same centered modal over the dimmed dashboard. The command
palette's log.open and the mobile bar's #merr are unchanged; the Log's own behaviour is untouched.

Two guards: SourcePins runs everywhere; ServedOpener boots the hermetic kernel, loads the dashboard, and drives
the gear's button in the settings iframe, the /settings page that hosts the gear since 2026-09-10 (skips loudly
without the extension deps or a Playwright browser). It also reads the button's unread count in both themes: the phone
triangle's red in each (feed.css --log-unread, 2026-10-04), at 3:1 or better on the count's ground. Any box from the count
up to the settings page's root whose drawing composites it with what lies behind it or dims it fails that read loudly (the
round-2 review's rule, 2026-10-05): an opacity under 1, a filter or a backdrop-filter other than none, a mix-blend-mode
other than normal, or a mask-image or a mask-border other than none, each read in its -webkit- form too where the engine
reports one (the mask-border's is -webkit-mask-box-image; Firefox supports neither form, so it has none to read), since
each can change how the colours the read takes are drawn. A mutant that plants an opacity of 0.3 on the count, on its
button (the count's ground), on body or on html, or `filter: opacity(.45)`, `backdrop-filter: brightness(.45)`,
`mix-blend-mode: multiply` or a `mask-image` gradient at alpha .45 on the count, on its button or on html, or the same
gradient as a mask-border (`-webkit-mask-box-image` in Chromium and WebKit, `mask-border` in WebKit) on those three
boxes, turns it red through the ground error that names the box and the property, not through the ratio.
All fixtures synthetic.
"""
import inspect
import json
import lab_dist
import lab_ports
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
EXT = os.path.join(ROOT, "vscode-extension")
sys.path.insert(0, HERE)
import test_ship_reship_served as _lab   # noqa: E402  the lab kernel's environment (the module, not its classes: an
#                                   imported TestCase would be collected here a second time)
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
km = load_source("romp_kernel_logopener", os.path.join(BIN, "romp-kernel"))
GEAR = open(os.path.join(ROOT, "ui", "webview", "gear.js")).read()
PALETTE = open(os.path.join(ROOT, "ui", "webview", "palette-main.ts")).read()


class SourcePins(unittest.TestCase):
    def test_the_bar_no_longer_carries_the_opener_and_the_panel_still_stands(self):
        land = inspect.getsource(km._landing)
        self.assertNotIn("id=rail-errs", land, "the Log's triangle left the bottom bar's action cluster")
        for keep in ("id=rail-refresh", "id=rail-net", "id=rail-gear", "id=rerr-back", "id=rerr-list", "id=rerr-clear"):
            self.assertIn(keep, land, keep + " stays")
        self.assertIn("if(!back||!list)return;", km._LANDING_ERRS_JS, "the center's script no longer needs the bar icon")
        self.assertIn("if(icon)icon.addEventListener('click'", km._LANDING_ERRS_JS)
        self.assertIn("window.__rompOpenErrs=open;", km._LANDING_ERRS_JS)

    def test_the_gear_button_is_the_last_row_of_updates_and_debug_and_opens_the_shell_panel(self):
        self.assertIn("<button id=rs-log-open class=ra-openbtn hidden>Open log<span class=rs-log-n hidden></span></button>", GEAR, "the same button chrome as Token usage analytics")
        self.assertLess(GEAR.index("id=ra-open"), GEAR.index("id=rs-log-open"))
        self.assertLess(GEAR.index("id=rs-log-open"), GEAR.index("id=rsver"), "the section's last row, before the version block")
        self.assertIn("lg.onclick = function () { closeSettings(); try { window.parent.postMessage({ romp: 'openLog' }, '*'); }", GEAR,
                      "the modal closes first, then asks the shell (the panels never stack)")
        self.assertIn("lg.hidden = !web;", GEAR, "web shell only: VS Code's parent has no Log panel")
        self.assertIn("if(m.romp==='openLog'&&window.__rompOpenErrs)window.__rompOpenErrs();", km._LANDING_SETTINGS_JS)

    def test_the_unread_count_rides_the_open_log_button(self):
        # the bar's opener drew the unread count; with it gone the count travels to the gear's button (the manager's
        # review nit, 2026-09-09): the shell posts it on every repaint and on the panel's query, the button renders
        # "Open log · N" with the count in the triangle's red
        k = open(os.path.join(ROOT, "kernel", "kernel.py"), encoding="utf-8").read()
        g = open(os.path.join(ROOT, "ui", "webview", "gear.js"), encoding="utf-8").read()
        css = open(os.path.join(ROOT, "ui", "webview", "gear.css"), encoding="utf-8").read()
        self.assertIn("tell(n);if(!back.hidden)renderList();}", k, "paint() tells the settings iframe")
        self.assertIn("function tell(n){var f=document.getElementById('f-settings');", k, "…the document the gear lives in")
        self.assertIn("postMessage({romp:'logUnseen',n:(n===undefined?unseen():n)},'*')", k)
        self.assertIn("if(m&&m.romp==='logUnseenQuery')tell();", k, "…and answers the panel's query")
        self.assertIn("<button id=rs-log-open class=ra-openbtn hidden>Open log<span class=rs-log-n hidden></span></button>", g)
        self.assertIn("if (m && m.romp === 'logUnseen') window.__rompSetLogCount(m.n);", g)
        self.assertIn("lgn.textContent = n <= 0 ? '' : ' \\u00b7 ' + (n > 9 ? '9+' : String(n));", g)
        self.assertIn("window.parent.postMessage({ romp: 'logUnseenQuery' }, '*');", g, "the panel asks when it opens")
        # the count wears the triangle's red in each theme (2026-10-04): through feed.css's --log-unread, whose dark and light
        # values are the shell's two triangle rules' (the light count sat at 2.1:1 on its surface in the dark red). These are
        # spelling pins; ServedOpener reads the computed colour, and its contrast, in both themes
        self.assertIn(".rs-log-n { color: var(--log-unread, #ff6b6b); font-weight: 600; }", css, "the triangle's red, per theme")
        feed = open(os.path.join(ROOT, "ui", "webview", "feed.css"), encoding="utf-8").read()
        dark = feed[feed.index(":root {"):feed.index("\n}", feed.index(":root {"))]
        light = feed[feed.index("body.theme-light {"):feed.index("\n}", feed.index("body.theme-light {"))]
        self.assertIn("--log-unread: #ff6b6b;", dark, "the dark count's red")
        self.assertIn('"#mtabs #merr.has{color:#ff6b6b}"', k, "…is the dark triangle's")
        self.assertIn("--log-unread: #B02A1C;", light, "the light count's red")
        self.assertIn('"body.theme-light #mtabs #merr.has{color:#B02A1C}"', k, "…is the light triangle's")

    def test_the_other_openers_are_unchanged(self):
        self.assertIn('registerCommand({ id: "log.open", title: "Open the log", run: () => { if (w.__rompOpenErrs) w.__rompOpenErrs(); } });', PALETTE)
        self.assertIn("data-act=errs data-keycmd=log.open", inspect.getsource(km._landing), "the mobile bar keeps its opener")


DRIVER = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const { chromium } = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
let browser;
try { browser = await chromium.launch(); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const page = await browser.newPage({ viewport: { width: 1100, height: 800 } });
await page.goto(cfg.url);
await page.waitForSelector("#rail-gear", { timeout: 20000 });
const feedPane = page.frames().find((f) => f.url().includes("/feed"));
const feedGear = feedPane ? await feedPane.evaluate(() => !!document.getElementById("rsettings")) : null;
const before = await page.evaluate(() => ({ railErrs: !!document.getElementById("rail-errs"), logHidden: document.getElementById("rerr-back").hidden,
  acts: Array.from(document.querySelectorAll(".rail-acts .rail-act")).map((e) => e.id),
  settingsSrc: document.getElementById("f-settings").getAttribute("src") }));   // the settings page is not loaded until the gear is first opened
await page.click("#rail-gear");   // the shell's opener gives the settings iframe its src and opens the gear once the page has loaded
await page.waitForFunction(() => { const f = document.getElementById("f-settings"); return f && f.getAttribute("src") === "/settings"; }, null, { timeout: 8000 });
await page.waitForFunction(() => document.body.classList.contains("settings-open"), null, { timeout: 20000 });
const feed = page.frames().find((f) => f.url().includes("/settings"));   // the settings iframe hosts the gear (the feed page mounts none)
if (!feed) { console.error("no settings frame"); process.exit(1); }
await feed.waitForSelector("#rsettings:not([hidden])", { timeout: 15000 });
const btn = await feed.evaluate(() => { const b = document.getElementById("rs-log-open"); return { present: !!b, hidden: b ? b.hidden : null }; });
// the gear is in TABS since T379 (Open log sits on the System tab, hidden until that tab is picked): select it as a user would, by its pill
await feed.click("#rsettings .rs-tab[data-tab=debug]");   // Open log lives on the Debug tab since T400 (System dissolved into it)
await feed.waitForFunction(() => { const pn = document.querySelector("#rsettings .rs-pane[data-pane=debug]"); return !!pn && !pn.hidden; }, null, { timeout: 5000 });
// the count's colour in each theme (2026-10-04): one entry logged through the shell's write path, so the count shows (the lab
// may hold entries of its own, so the number is not fixed); the count read with its ground (the first box from the count up whose background is opaque, or why none could be read or measured); then
// the light theme picked the way the gear picks it (the settings object; the settings page hears the store's event), and the
// count read again
const readCount = () => feed.evaluate(async () => {
  const n = document.querySelector("#rs-log-open .rs-log-n");
  if (!n) return { missing: true };
  // a theme's colours reach the button through its 0.12 s background transition (.ra-openbtn), so the read waits for every
  // transition on the count and the boxes around it to finish: the ground read is the theme's, not a frame of the fade.
  // Bounded: an animation still running after 3 s is reported (settled false), and the Python side fails on it
  const mine = document.getAnimations().filter((a) => a.effect && a.effect.target && a.effect.target.contains && a.effect.target.contains(n));
  const settled = await Promise.race([Promise.all(mine.map((a) => a.finished.catch(() => null))).then(() => true),
                                      new Promise((r) => setTimeout(() => r(false), 3000))]);
  const tagOf = (el) => el.id ? "#" + el.id : el.tagName.toLowerCase() + (el.className ? "." + String(el.className).split(" ")[0] : "");
  let ground = null, groundOf = null, groundError = null;
  for (let el = n; el && !ground && !groundError; el = el.parentElement) {
    const st = getComputedStyle(el);
    const tag = tagOf(el);
    const bg = /^rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:\s*[,/]\s*([\d.]+)(%?))?\s*\)$/.exec(st.backgroundColor);
    if (st.backgroundImage && st.backgroundImage !== "none") groundError = "a background image on " + tag + ": " + st.backgroundImage.slice(0, 120);
    else if (!bg) groundError = "an unreadable background colour on " + tag + ": " + st.backgroundColor;
    else {
      const alpha = bg[4] === undefined ? 1 : parseFloat(bg[4]) / (bg[5] ? 100 : 1);
      if (alpha >= 1) { ground = st.backgroundColor; groundOf = tag; }
      else if (alpha > 0) groundError = "a translucent background on " + tag + ": " + st.backgroundColor;
    }
  }
  if (!ground && !groundError) groundError = "no box from the count up has an opaque background";
  // then the read of how the boxes are drawn, against one rule (ruled in the round-2 review, 2026-10-05): no box from the
  // count up to this document's root, body and html among them, may be drawn so that it composites with what lies behind
  // it or dims. Such drawing can change how the count is drawn against its ground, or the count and its ground together
  // against what is behind them, so the two computed colours may not be what the screen shows. The CSS that does, as this
  // read takes it: an opacity under 1, a filter or a backdrop-filter other than none, a mix-blend-mode other than normal,
  // a mask-image or a mask-border other than none. The first box with any of them is named with the property and its
  // value, whatever the value's effect (an identity filter fails too), and the ratio is never measured. Each property
  // after the opacity is read in its standard form and in its -webkit- form wherever the engine reports that form, so an
  // engine that reports only the prefixed one is read as well; the mask-border's -webkit- form is -webkit-mask-box-image,
  // the only form Chromium reports. A property reported in neither form, or an unreadable opacity, fails the same way,
  // except a mask-border in an engine that supports neither of its forms (CSS.supports), which draws none and is not
  // read: Firefox does not support it. Paint effects outside the rule, which change the drawn colour without compositing
  // the box, are not read: among them visibility, clip-path, an inset box-shadow on the ground box, a text-shadow or a
  // -webkit-text-stroke on the count, a text fill colour (-webkit-text-fill-color) and a box off this path drawn over the
  // count. The settings page is an iframe: the shell's boxes around it (#f-settings and up) belong to another document,
  // and this read does not reach them
  const DRAWN = [["filter", "none"], ["backdrop-filter", "none"], ["mix-blend-mode", "normal"], ["mask-image", "none"],
                 ["mask-border", "none", "-webkit-mask-box-image"]];
  const drawn = (st) => {
    if (!(parseFloat(st.opacity) >= 1)) return "an opacity of " + st.opacity;
    for (const [prop, flat, prefixed = "-webkit-" + prop] of DRAWN) {
      if (prop === "mask-border" && ![prop, prefixed].some((p) => CSS.supports(p, flat))) continue;
      const forms = [prop, prefixed].map((p) => [p, st.getPropertyValue(p)]).filter((f) => f[1] !== "");
      if (!forms.length) return "an unreadable " + prop;
      const off = forms.find((f) => f[1] !== flat);
      if (off) return "a " + off[0] + " of " + off[1].slice(0, 120);
    }
    return null;
  };
  for (let el = n; el && !groundError; el = el.parentElement) {
    const why = drawn(getComputedStyle(el));
    if (why) groundError = why + " on " + tagOf(el);
  }
  return { text: n.textContent, hidden: n.hidden, color: getComputedStyle(n).color, ground, groundOf, groundError,
           light: document.body.classList.contains("theme-light"), settled, animations: mine.length };
});
await page.evaluate(() => window.__rompNotify("warn", "Synthetic warning for the count's colour"));
await feed.waitForFunction(() => { const n = document.querySelector("#rs-log-open .rs-log-n"); return !!n && !n.hidden && /[0-9]/.test(n.textContent); }, null, { timeout: 8000 });
const countDark = await readCount();
await page.evaluate(() => {
  let s = {};
  try { s = JSON.parse(localStorage.getItem("romp:settings") || "{}") || {}; } catch (e) { s = {}; }
  s.theme = "yatharth-light";
  localStorage.setItem("romp:settings", JSON.stringify(s));
  window.dispatchEvent(new Event("romp:settings"));
});
await feed.waitForFunction(() => document.body.classList.contains("theme-light"), null, { timeout: 8000 });
const countLight = await readCount();
await feed.click("#rs-log-open");
await page.waitForFunction(() => !document.getElementById("rerr-back").hidden, null, { timeout: 8000 });
const after = await page.evaluate(() => ({ logHidden: document.getElementById("rerr-back").hidden, settingsOpen: document.body.classList.contains("settings-open") }));
const modal = await feed.evaluate(() => document.getElementById("rsettings").hidden);
fs.writeSync(1, "RESULT:" + JSON.stringify({ before, btn, after, settingsHidden: modal, feedGear, countDark, countLight }) + "\n");
await browser.close();
process.exit(0);
"""


class ServedOpener(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            raise unittest.SkipTest("extension deps absent (npm ci not run here) — the served guard needs them")
        cls.lab = tempfile.mkdtemp(prefix="logopener-")
        cls.addClassCleanup(lab_ports.release, cls.lab)   # runs on a failed setUpClass too, which skips tearDownClass
        dist = os.path.join(cls.lab, "dist")
        lab_dist.copy_dist(dist)   # the checkout's ONE build of the bundles, copied under its lock (tests/lab_dist.py)
        state = os.path.join(cls.lab, "xdg", "romp")
        os.makedirs(state, exist_ok=True)
        cls.port = lab_ports.reserve(cls.lab)
        cls.token = "testtok-logopener"
        env = _lab.kernel_env(cls.lab, os.path.join(cls.lab, "claude"), dist, cls.port, cls.token)
        cls.kernel = subprocess.Popen([os.path.join(BIN, "romp-kernel")], stdout=open(os.path.join(cls.lab, "kernel.log"), "w"),
                                      stderr=subprocess.STDOUT, env=env)
        why = lab_ports.wait_owned(cls.kernel, env)
        if why:
            cls.kernel.kill()
            raise unittest.SkipTest("hermetic kernel never served /healthz here: " + why)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "kernel", None):
            cls.kernel.kill()
            cls.kernel.wait()
        lab_ports.release(getattr(cls, "lab", ""))
        shutil.rmtree(getattr(cls, "lab", ""), ignore_errors=True)

    def test_the_bar_has_no_opener_and_the_gear_button_opens_the_panel(self):
        cfg = os.path.join(self.lab, "cfg.json")
        with open(cfg, "w") as f:
            json.dump({"url": "http://127.0.0.1:%d/?token=%s" % (self.port, self.token)}, f)
        driver = os.path.join(self.lab, "driver.mjs")
        with open(driver, "w") as f:
            f.write(DRIVER)
        p = subprocess.run(["node", driver], capture_output=True, text=True, timeout=300,
                           env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg))
        if p.returncode == 3:
            raise unittest.SkipTest("no playwright browser on this box — the served guard needs one (CI installs none)")
        self.assertEqual(p.returncode, 0, "driver failed:\n" + p.stdout[-3000:] + p.stderr[-3000:])
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
        self.assertIsNotNone(line, "driver printed no result:\n" + p.stdout[-3000:])
        r = json.loads(line[len("RESULT:"):])
        self.assertFalse(r["before"]["railErrs"], "no Log opener in the bottom bar: %r" % r["before"])
        self.assertTrue(r["before"]["logHidden"], "the panel starts closed")
        self.assertIsNone(r["before"]["settingsSrc"], "the settings page is not loaded before the gear is first opened")
        self.assertEqual(r["before"]["acts"], ["rail-refresh", "rail-net", "rail-bell", "rail-gear"], "the bar's action cluster keeps its few controls (the bell is present, hidden until it has something): %r" % r["before"]["acts"])
        self.assertEqual(r["btn"], {"present": True, "hidden": False}, "the gear shows Open log in the web shell")
        self.assertIs(r["feedGear"], False, "the feed page mounts no gear of its own (it lives on /settings)")
        self.assertFalse(r["after"]["logHidden"], "the click opened the shell's Log panel")
        self.assertFalse(r["after"]["settingsOpen"], "the settings modal closed first: the panels never stack")
        self.assertTrue(r["settingsHidden"])
        # the count wears the phone triangle's red in each theme and reads at 3:1 or better on its ground (2026-10-04): in the
        # light theme the dark red read 2.1:1 there
        for key, light, red in (("countDark", False, "rgb(255, 107, 107)"), ("countLight", True, "rgb(176, 42, 28)")):
            c = r[key]
            self.assertEqual((c.get("hidden"), c.get("light"), c.get("settled"), c.get("groundError", "the driver read no ground")),
                             (False, light, True, None), "%s: the count shown, the theme, its transitions done, its ground read: %r"
                             % (key, c))
            self.assertRegex(c["text"], r"[0-9]", key + ": the count shows a number: %r" % (c,))
            ratio = _contrast(c["color"], c["ground"])
            self.assertEqual(c["color"], red, "%s: the count wears the triangle's red in this theme (%.2f:1 on %s): %r"
                             % (key, ratio, c["ground"], c))
            self.assertGreaterEqual(ratio, 3.0, "%s: the count's red %s reads at %.2f:1 on its ground %s (%s), under 3:1"
                                    % (key, c["color"], ratio, c["ground"], c["groundOf"]))


def _rgb(css):
    """An engine's computed colour, rgb() or rgba() with an alpha of 1, as three channels; anything else is an error."""
    m = re.fullmatch(r"rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:\s*[,/]\s*([\d.]+)(%?))?\s*\)", css or "")
    if not m:
        raise AssertionError("not an rgb() colour: %r" % (css,))
    if m.group(4) is not None and float(m.group(4)) / (100 if m.group(5) else 1) < 1:
        raise AssertionError("a translucent colour cannot be measured alone: %r" % (css,))
    return tuple(float(m.group(i)) for i in (1, 2, 3))


def _contrast(fg, bg):
    """The WCAG 2 contrast ratio of two computed colours."""
    def lum(c):
        ch = [v / 255 for v in _rgb(c)]
        ch = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in ch]
        return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]
    hi, lo = sorted((lum(fg), lum(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


if __name__ == "__main__":
    unittest.main()
