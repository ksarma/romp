#!/usr/bin/env python3
"""The phone layout's bottom bar (#mtabs) keeps every control on screen and under a finger at every phone width (iOS item
4g, 2026-10-04).

THE BUG. The bar is one flex row: the pane tabs (each flex:1, never narrower than its label, 8px apart) and then the action
cluster, a divider and six buttons that never shrink (Usage, Remote kernels, Restart, the Log's triangle, the push bell and
Settings), each a glyph in 7px of side padding, 28 to 32px wide. The bell is not capability-gated: the shell's push script
reveals it on every page since the bell became the master switch (it shows where the Push API is missing too), so it is
always one of the six. With the default tabs (Chat, Sessions, Outline, Feed, Waiting) the row needs 418px in Chromium and
413px in WebKit and Firefox (454 and 448px with the Files tab on), nothing in it could shrink or wrap, and the bar does not
scroll (overflow visible, in the shell's overflow:hidden body), so on a narrower window the cluster ran past the right edge
of the screen out of reach. Measured before the fix in all three engines: at 390px Settings past the edge; at 375 the bell
cut and Settings past; at 360 the bell and Settings past; at 320 Restart cut and the Log's triangle, the bell and Settings
past, so the Log could not be opened from its triangle there; at 414 in Chromium Settings cut by 4px. With the Files tab on
Settings ran off at 430px too. Landscape phones fit.

THE FIX (kernel/kernel.py, the shell's markup and its phone media block). The action cluster is one element
(.mtabs-acts), and the bar may wrap: when the tabs and the cluster do not fit on one row, the cluster moves whole to a
second row under the tabs, at the right edge where it sat, and the tabs take the full first row. Where everything fits the
bar is the single row it was, every box where it was. The tabs keep the single row's height on a row of their own. A
wrapped bar is taller, and its height can change with no resize at all (the Files tab turned on in the gear, the webfont
arriving), so the shell re-measures the bar's height, the strip the panes leave for it, whenever the bar's box changes (a
ResizeObserver on the bar, beside the resize events that already re-measure it). The desktop is untouched: the bar is
display:none outside the phone media block and every rule of the fix is inside it.

WHAT IS MEASURED, in the pages the kernel serves, in a real engine (tests/mtabs_fit_browser.mjs): the iPhone 14 descriptor
(Firefox without isMobile, which Playwright does not support there) at 320, 360, 375, 390, 414 and 430px wide in portrait
and the same phones in landscape, on the default tab set and with the Files tab on. Wherever the phone layout applies, for
every control the bar shows: its box wholly inside the window, the element at its centre is that control, no two controls
overlap, a tab's label fits inside it, every control keeps at least its natural width (its width in the unsqueezed row:
an action button its glyph and padding) and the single row's height (the tap area the bar was designed with; ui/CLAUDE.md
states no figure), the bar spans the window at its bottom edge and nothing in it overflows, and the strip the panes leave
(--mtabs-h) equals the bar's height with the shown pane ending above it. Where the bar's natural one-row width (the bar
laid out at max-content without wrapping) fits the window, every control shares one row as before; where it does not, the
tabs fill the first row and the cluster sits together on the second at the right edge. Then the Files tab turned on with
no resize, at 430px where the default set fits one row and the Files set does not: the bar wraps and the strip follows it.
And a desktop window, where the bar is hidden. MTABS_FIT_DUMP, a directory, keeps each engine's raw readings there.

Red before the fix in each engine at the widths whose natural row overflows (the past-the-edge and centre-hit lines name
them); green after. Runs in the "Browser-backed served-page tests (pytest)" step of the served-pages job, "Served pages
(pytest, ubuntu-latest)" (ci.yml, ROMP_SERVED_TESTS_REQUIRE=1: a skip here is a failure), in Chromium; the WebKit and
Firefox legs are `optional:` skips where that engine is absent or not declared in ROMP_SERVED_TESTS_ENGINES (CI declares
chromium; a developer's box runs all three).

The lab: one kernel from test_ship_reship_served.kernel_env (a private XDG root, `session-hosts` floored off,
ROMP_MANAGER_PORT=1, no catalog or update fetch, a hermetic postal bus), its port from tests/lab_ports.py and proved its own
there, a private dist (lab_dist.copy_dist), no sessions. The driver asserts /healthz on the lab's port before any request.
Synthetic throughout.
"""
import json
import lab_dist
import lab_ports
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
EXT = os.path.join(ROOT, "vscode-extension")
sys.path.insert(0, HERE)
import test_ship_reship_served as _lab   # noqa: E402  (kernel_env: every lab kernel's environment; the module, not its classes)

# Hermetic state BEFORE anything: this module loads no romp code in-process (the kernel is a subprocess under kernel_env's
# roots), but the floor costs two lines and a later edit that adds a load must not write real state.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
os.makedirs(os.path.join(os.environ["XDG_STATE_HOME"], "romp"), exist_ok=True)
Path(os.environ["XDG_STATE_HOME"], "romp", "session-hosts").write_text("off\n")   # the Testing rule for a test that mints its own root

DRIVER = os.path.join(HERE, "mtabs_fit_browser.mjs")
# the phones: width by height in portrait (320 the narrowest, 430 the widest), and the same phones turned to landscape
PORTRAIT = ((320, 568), (360, 640), (375, 667), (390, 844), (414, 896), (430, 932))
LANDSCAPE = tuple((h, w) for w, h in PORTRAIT)
DYNAMIC = (430, 932)   # the default tabs fit one row here and the Files set does not (asserted, so the leg proves a wrap)
DESKTOP = (1280, 800)
DUMP = os.environ.get("MTABS_FIT_DUMP", "")   # a directory: each engine's raw readings are copied there (evidence for a run)
EPS = 0.5


def _px(v):
    """'31px' -> 31.0; an empty or malformed value is a failure, not a zero."""
    v = (v or "").strip()
    assert v.endswith("px"), "not a px value: %r" % (v,)
    return float(v[:-2])


def _problems(where, row):
    """Every way the bar fails one reading, as lines naming the controls; empty when the bar holds."""
    out = []
    vw, vh, bar, cs = row["vw"], row["vh"], row["bar"], row["controls"]
    past = [c["key"] for c in cs if c["left"] < -EPS or c["right"] > vw + EPS]
    if past:
        out.append("%s: past the window's edge (%dpx): %s (rights %s)" % (
            where, vw, ", ".join(past), ", ".join("%g" % c["right"] for c in cs if c["key"] in past)))
    missed = [c["key"] for c in cs if not c["hit"]]
    if missed:
        out.append("%s: the element at the centre is not the control: %s" % (where, ", ".join(missed)))
    for i, a in enumerate(cs):
        for b in cs[i + 1:]:
            if min(a["right"], b["right"]) - max(a["left"], b["left"]) > EPS and min(a["bottom"], b["bottom"]) - max(a["top"], b["top"]) > EPS:
                out.append("%s: %s and %s overlap" % (where, a["key"], b["key"]))
    clipped = [c["key"] for c in cs if c["tab"] and not c["labelFits"]]
    if clipped:
        out.append("%s: a tab's label is wider than the tab: %s" % (where, ", ".join(clipped)))
    if abs(bar["left"]) > EPS or abs(bar["right"] - vw) > EPS or abs(bar["bottom"] - vh) > EPS:
        out.append("%s: the bar does not span the window at its bottom edge: %r" % (where, bar))
    if bar["scrollW"] > bar["clientW"] + EPS:
        out.append("%s: the bar's content overflows it (scrollWidth %s, clientWidth %s)" % (where, bar["scrollW"], bar["clientW"]))
    if row["docScrollW"] > vw + EPS:
        out.append("%s: the document is wider than the window (%s)" % (where, row["docScrollW"]))
    acts = [c for c in cs if not c["tab"]]
    one_h = max((c["h"] for c in acts), default=0)
    narrow = ["%s (%g, natural %g)" % (c["key"], c["w"], c["naturalW"]) for c in cs if c["w"] < c["naturalW"] - EPS]
    if narrow:
        out.append("%s: narrower than its natural width: %s" % (where, ", ".join(narrow)))
    short = [c["key"] for c in cs if c["h"] < one_h - EPS]
    if short:
        out.append("%s: shorter than the single row's %gpx: %s" % (where, one_h, ", ".join(short)))
    try:
        reserved = _px(row["mtabsH"])
        if abs(reserved - bar["offsetH"]) > EPS:
            out.append("%s: the panes' strip (--mtabs-h %s) is not the bar's height (%s)" % (where, row["mtabsH"], bar["offsetH"]))
    except AssertionError as e:
        out.append("%s: --mtabs-h unreadable: %s" % (where, e))
    if not row["pane"] or row["pane"]["bottom"] > bar["top"] + EPS:
        out.append("%s: the shown pane runs under the bar: %r against the bar's top %s" % (where, row["pane"], bar["top"]))
    tabs = [c for c in cs if c["tab"]]
    if row["natural"] <= vw + EPS:
        # it fits: the single row it always was, every control on it and the bar one control tall
        if max(c["top"] for c in cs) - min(c["top"] for c in cs) > EPS:
            out.append("%s: the natural row (%gpx) fits, yet the controls are not on one row" % (where, row["natural"]))
        if abs(bar["offsetH"] - (one_h + bar["borderTop"] + bar["padBottom"])) > EPS:
            out.append("%s: the natural row fits, yet the bar is %spx tall, not one row of %gpx" % (where, bar["offsetH"], one_h))
    else:
        # it does not fit: the tabs fill the first row, the cluster sits together on the second, at the right edge
        if tabs and max(c["top"] for c in tabs) - min(c["top"] for c in tabs) > EPS:
            out.append("%s: the tabs are not on one row" % where)
        if acts and max(c["top"] for c in acts) - min(c["top"] for c in acts) > EPS:
            out.append("%s: the action buttons are not on one row" % where)
        if tabs and acts and min(c["top"] for c in acts) < max(c["bottom"] for c in tabs) - EPS:
            out.append("%s: the natural row (%gpx) does not fit, yet the actions are not on a row under the tabs" % (where, row["natural"]))
        if acts and abs(acts[-1]["right"] - vw) > EPS:
            out.append("%s: the last action button does not sit at the right edge (%s)" % (where, acts[-1]["right"]))
        if any(abs(b["left"] - a["right"]) > EPS for a, b in zip(acts, acts[1:])):
            out.append("%s: the action buttons are not side by side" % where)
    return out


class MtabsFit(unittest.TestCase):
    """One lab kernel for every leg (setUpClass); each leg is one driver run in one engine."""
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            raise unittest.SkipTest("extension deps absent (npm ci not run here): the served leg needs them")
        cls.lab = tempfile.mkdtemp(prefix="mtabs-fit-")
        cls.addClassCleanup(lab_ports.release, cls.lab)   # runs on a failed setUpClass too, which skips tearDownClass
        dist = os.path.join(cls.lab, "dist")
        lab_dist.copy_dist(dist)   # the checkout's ONE build of the bundles, copied under its lock (tests/lab_dist.py)
        os.makedirs(os.path.join(cls.lab, "xdg", "romp"), exist_ok=True)
        cls.port, cls.token = lab_ports.reserve(cls.lab), "testtok-mtabsfit"
        cls.env = _lab.kernel_env(cls.lab, os.path.join(cls.lab, "claude"), dist, cls.port, cls.token)
        cls.klog = os.path.join(cls.lab, "kernel.log")
        cls.kernel = subprocess.Popen([os.path.join(BIN, "romp-kernel")], stdout=open(cls.klog, "w"),
                                      stderr=subprocess.STDOUT, env=cls.env)
        why = lab_ports.wait_owned(cls.kernel, cls.env)
        if why:
            cls.kernel.kill()
            cls.kernel.wait()
            raise unittest.SkipTest("hermetic kernel never served /healthz here: " + why)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "kernel", None):
            cls.kernel.kill()
            cls.kernel.wait()
        lab_ports.release(getattr(cls, "lab", ""))
        shutil.rmtree(getattr(cls, "lab", ""), ignore_errors=True)

    def _drive(self, engine):
        declared = os.environ.get("ROMP_SERVED_TESTS_ENGINES", "")
        if engine != "chromium" and declared and engine not in [e.strip() for e in declared.split(",")]:
            self.skipTest("optional: this runner declares no %s (ROMP_SERVED_TESTS_ENGINES=%s)" % (engine, declared))
        cfg = {"engine": engine, "url": "http://127.0.0.1:%d/?token=%s" % (self.port, self.token),
               "healthz": "http://127.0.0.1:%d/healthz" % self.port, "settleMs": 100,
               "viewports": [list(v) for v in PORTRAIT + LANDSCAPE], "dynamicViewport": list(DYNAMIC),
               "desktopViewport": list(DESKTOP), "result": os.path.join(self.lab, "result-%s.json" % engine)}
        cfg_path = os.path.join(self.lab, "cfg-%s.json" % engine)
        Path(cfg_path).write_text(json.dumps(cfg))
        try:
            p = subprocess.run(["node", DRIVER], capture_output=True, text=True, timeout=300,
                               env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg_path))
        except subprocess.TimeoutExpired as e:
            so = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode()
            self.fail("driver timed out; partial output:\n%s" % so[-3000:])
        if p.returncode == 3:
            if engine == "chromium":
                self.skipTest("no playwright chromium on this box: the served leg needs one (CI installs it)")
            self.skipTest("optional: no playwright %s on this machine: %s" % (engine, p.stderr.strip()[-300:]))
        self.assertEqual(p.returncode, 0, "driver failed:\n" + p.stdout[-3000:] + p.stderr[-3000:])
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT-FILE:")), None)
        self.assertIsNotNone(line, "driver printed no result:\n" + p.stdout[-3000:] + p.stderr[-3000:])
        self.assertEqual(line[len("RESULT-FILE:"):], cfg["result"], "the driver wrote the file it was given")
        raw = Path(cfg["result"]).read_text()
        if DUMP:
            os.makedirs(DUMP, exist_ok=True)
            Path(DUMP, engine + ".json").write_text(raw)
        r = json.loads(raw)
        self.assertNotIn("died", r, "driver aborted early: %r (kernel log tail: %s)" % (r.get("died"), Path(self.klog).read_text()[-800:]))
        self.assertEqual(r.get("errors"), [], "page errors")
        return r

    def _leg(self, engine):
        r = self._drive(engine)
        problems, phones = [], 0
        for name in ("default", "files"):
            rows = r["sets"][name]
            self.assertEqual([tuple(x["vp"]) for x in rows], list(PORTRAIT + LANDSCAPE), engine + ": every phone was read")
            for row in rows:
                where = "%s %s %dx%d" % (engine, name, row["vp"][0], row["vp"][1])
                if not row["mobile"]:
                    # only a landscape phone wider than the query's 820px, in an engine whose emulation gives no coarse pointer
                    self.assertGreater(row["vw"], 820, where + ": the phone layout is off only past 820px: %r" % (row,))
                    self.assertEqual(row["display"], "none", where + ": no phone layout, no bar")
                    continue
                phones += 1
                self.assertTrue(row["fonts"], where + ": the webfont is in, so the labels have their served widths")
                self.assertEqual((row["bell"] or {}).get("hidden"), False, where + ": the bell shows (the shell reveals it on every page): %r" % (row["bell"],))
                self.assertEqual(len([c for c in row["controls"] if not c["tab"]]), 6, where + ": six action buttons, the bell among them: %r" % (row["controls"],))
                self.assertEqual(len([c for c in row["controls"] if c["tab"]]), 6 if name == "files" else 5, where + ": the tab set")
                problems += _problems(where, row)
        self.assertGreaterEqual(phones, 2 * len(PORTRAIT), engine + ": every portrait phone was read on the phone layout")
        d = r["dynamic"]
        where = "%s files turned on at %dx%d" % (engine, d["vp"][0], d["vp"][1])
        self.assertLessEqual(d["before"]["natural"], d["before"]["vw"], where + ": the default set fits one row here (the leg's premise): %r" % (d["before"],))
        self.assertGreater(d["after"]["natural"], d["after"]["vw"], where + ": the Files set does not fit one row here (the leg's premise): %r" % (d["after"],))
        problems += _problems(where + " (before)", d["before"])
        problems += _problems(where, d["after"])
        self.assertEqual(r["desktop"]["display"], "none", engine + ": the desktop shows no phone bar: %r" % (r["desktop"],))
        self.assertIs(r["desktop"]["mobile"], False, engine + ": the desktop window is not the phone layout: %r" % (r["desktop"],))
        self.assertEqual(problems, [], "\n".join(problems))

    def test_chromium_every_control_on_screen_at_every_phone_width(self):
        self._leg("chromium")

    # WebKit is Safari's engine and Firefox the third; `optional:` skips where the browser is absent (CI installs Chromium alone)
    def test_webkit_every_control_on_screen_at_every_phone_width(self):
        self._leg("webkit")

    def test_firefox_every_control_on_screen_at_every_phone_width(self):
        self._leg("firefox")


if __name__ == "__main__":
    unittest.main()
