#!/usr/bin/env python3
"""Every read in the dashboard shell's inline scripts that MEANS the layout viewport's height reads it in WebKit under
a standing pinch, through layoutH() (the root element's clientHeight), not window.innerHeight (2026-09-21).

The limit of what this pins, first: the WebKit half of the mechanism rests on a reading of WebKit's source
(LocalDOMWindow::innerHeight returns the unobscured content rect's height, which on iOS
WebPage::updateVisibleContentRects sets from the visual viewport) and on one Chromium run (an iPhone 14 descriptor at
page scale 2: visualViewport.height 422, innerHeight 844, documentElement.clientHeight 844). Playwright's WebKit on a
Linux box holds no page scale above 1 (no CDP, a tap-only touchscreen, the zoom chord changes nothing), so no WebKit
engine run and no on-device read under a pinch backs the model, and whether a pinch is reachable on iOS Safari under
the page's user-scalable=no meta is unconfirmed. The swap is a no-op wherever innerHeight was right (standards mode,
the root overflow:hidden: clientHeight equals innerHeight there), which is why it is made without the device read.

So the tests drive the shell's OWN functions under node against two window MODELS, both a 390 by 844 layout viewport
under a standing pinch at scale 2 (the visual viewport 422 CSS px tall at rest; the keyboard, 336 px on that
descriptor, takes it to 254 and pans it): WebKit, whose innerHeight is the visual viewport's height (422; with the
keyboard up the unobscured rect is modelled unchanged, and the other reading, 254, gives every verdict below the same
way, both being under the layout height), and Chromium, whose innerHeight stays the layout height (844). One test per
read: what the read publishes under each model. Under the Chromium model every expected value is what the unfixed
script published (the no-op half, asserted: the same literals were green at the head before the fix); under the WebKit
model the same values are what the fix publishes and the unfixed script did not. The census test then classifies every
innerHeight the shell serves: the helper's own fallback, the pane shim's zero test (a display:none frame reads 0 in
both engines, not a layout-viewport stand-in), and nothing else. tests/test_layout_height_served.py reads the premise
(standards mode, the root's overflow, clientHeight equal to innerHeight at rest) in real engines at scale 1.

Synthetic stand-ins only: no real session data."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the load: the kernel resolves its state root at import time.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
km = load_source("romp_kernel_layouth", os.path.join(BIN, "romp-kernel"))
sys.path.insert(0, HERE)
import test_kernel_mobile as _tm   # noqa: E402  the phone stand-ins (the fit harness, the bell harness): the module, not its classes

NODE = shutil.which("node")

# The two engine models (the module docstring says what each rests on).
WEBKIT = {"name": "webkit", "innerHeight": 422, "clientHeight": 844}
CHROMIUM = {"name": "chromium", "innerHeight": 844, "clientHeight": 844}
VV_REST = {"height": 422, "scale": 2, "offsetTop": 0}
VV_KB = {"height": 254, "scale": 2, "offsetTop": 168}    # the keyboard's pan: the visual viewport slides to the focused input


def _node(src):
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(src)
        path = f.name
    try:
        r = subprocess.run([NODE, path], capture_output=True, text=True, timeout=60)
    finally:
        os.unlink(path)
    assert r.returncode == 0, "the script threw:\n" + r.stderr[-2000:]
    return json.loads(r.stdout.strip().splitlines()[-1])


def _fn(js, name):
    """The source of `function name(...){...}` in a served script, from its keyword through the brace that closes it
    (string literals skipped), or '' when the script declares no such function."""
    head = "function " + name + "("
    i = js.find(head)
    if i < 0:
        return ""
    j = js.index("{", i)
    depth, k, quote = 0, j, None
    while k < len(js):
        c = js[k]
        if quote:
            if c == "\\":
                k += 1
            elif c == quote:
                quote = None
        elif c in "'\"":
            quote = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return js[i:k + 1]
        k += 1
    raise AssertionError("unbalanced braces after " + head)


def _model_prelude(model, vv, coarse=True):
    """Set the window stand-in to a model, after the harness has built it and before the shell script runs."""
    return ("global.innerHeight = %d; global.innerWidth = 390;\n"
            "document.documentElement.clientHeight = %d;\n"
            "visualViewport.height = %d; visualViewport.scale = %d; visualViewport.offsetTop = %d;\n"
            "global.matchMedia = () => ({ matches: %s });\n"
            % (model["innerHeight"], model["clientHeight"], vv["height"], vv["scale"], vv["offsetTop"],
               "true" if coarse else "false"))


@unittest.skipUnless(NODE, "node not installed on this machine")
class LayoutHeightUnderAPinch(unittest.TestCase):
    """One test per shell read of the layout viewport's height, driven under both models."""

    # ── the mobile script: the keyboard-open test and the fine-pointer fit, through the fit harness ──
    _FIT_DRIVER = r"""
const fire = (book, k) => (book[k] || []).forEach((f) => f({}));
const flush = () => { RAF.splice(0).forEach((f) => f(0)); };
const read = () => ({ appH: PROPS['--app-h'], barH: PROPS['--mtabs-h'] });
const out = { boot: read() };
// the keyboard slides up under the standing pinch: the visual viewport shrinks by the keyboard's height over the scale and pans
visualViewport.height = KB.height; visualViewport.offsetTop = KB.offsetTop; fire(VV, 'resize'); flush();
out.kbUp = read();
visualViewport.height = REST.height; visualViewport.offsetTop = REST.offsetTop; fire(VV, 'resize'); flush();
out.kbDown = read();
console.log(JSON.stringify(out));
"""

    def _fit(self, model, coarse=True):
        src = (_tm._FIT_HARNESS + _model_prelude(model, VV_REST, coarse)
               + "const KB = %s, REST = %s;\n" % (json.dumps(VV_KB), json.dumps(VV_REST))
               + km._LANDING_MOBILE_JS + self._FIT_DRIVER)
        return _node(src)

    def test_the_keyboard_open_test_reads_the_layout_height(self):
        # kbOpen: the layout height less the visual viewport's layout-scaled height, over 120 px. Under the WebKit
        # model innerHeight is the visual viewport's own height, so the difference was at most 0 with the keyboard up
        # (422 less 508 under the pinch; or 254 less 508 on the other reading of the rect) and the bar's reserved strip
        # (--mtabs-h) stayed at the bar's height while the keyboard covered the bar: a dead band above the keyboard,
        # the very defect the test exists to prevent. The layout height reads 844 in both models: 844 less 508 is 336.
        for model in (WEBKIT, CHROMIUM):
            with self.subTest(model=model["name"]):
                o = self._fit(model)
                self.assertEqual(o["boot"], {"appH": "844px", "barH": "44px"}, "at rest under the pinch: the keyboard is closed, the bar reserved")
                self.assertEqual(o["kbUp"], {"appH": "508px", "barH": "0px"}, "the keyboard up: the reservation collapses; --app-h is the visual viewport's layout-scaled height")
                self.assertEqual(o["kbDown"], {"appH": "844px", "barH": "44px"}, "the keyboard gone: the bar is reserved again")

    def test_the_fine_pointer_fit_reads_the_layout_height(self):
        # fit()'s fine-pointer road publishes the layout height as --app-h (its comment: pinch-immune by definition of
        # the layout viewport). Whether a fine-pointer WebKit parts innerHeight from the layout height under a trackpad
        # pinch is not known (the iOS road is the one read); the read means the layout viewport, so it takes the same
        # helper, and reads 844 under both models.
        for model in (WEBKIT, CHROMIUM):
            with self.subTest(model=model["name"]):
                o = self._fit(model, coarse=False)
                self.assertEqual(o["boot"]["appH"], "844px", "the fine road's --app-h is the layout height")

    # ── the bell script: the popover's bottom, through the bell harness ──
    _BELL_DRIVER = r"""
(0, eval)(PUSH_JS);
mbell.fire('click');
console.log(JSON.stringify({ bottom: pop.style.bottom, right: pop.style.right, open: !back.hidden }));
"""

    def test_the_bell_popover_bottom_is_measured_from_the_layout_viewport(self):
        # place(): a position:fixed box's `bottom` is the layout viewport's height less the anchor's rect.top, plus 6;
        # the harness's bell sits at top 800 in an 844 layout, so the popover's bottom edge belongs 50 px up. Under the
        # WebKit model innerHeight is 422 and the popover fell to the floor (8 px, the clamp).
        for model in (WEBKIT, CHROMIUM):
            with self.subTest(model=model["name"]):
                src = (_tm._BELL_HARNESS + _model_prelude(model, VV_REST)
                       + "const PUSH_JS=%s;\n" % json.dumps(km._LANDING_PUSH_JS) + self._BELL_DRIVER)
                o = _node(src)
                self.assertTrue(o["open"], "the tap opened the popover")
                self.assertEqual(o["bottom"], "50px", "the popover's bottom is measured from the layout viewport's bottom edge")
                self.assertEqual(o["right"], "10px", "the right edge is unchanged")

    # ── the pure functions: each extracted from its script and run alone, in a context that is the model ──
    _EXTRACT_RUNNER = r"""
const vm = require('vm');
const FN = %s, HELPERS = %s, MODELS = %s;
const ctx = (m, extra) => Object.assign({
  window: { innerHeight: m.innerHeight, innerWidth: 390 },
  document: { documentElement: { clientHeight: m.clientHeight }, getElementById: (id) => (extra.byId || {})[id] || null },
  getComputedStyle: () => ({ paddingTop: '10px', paddingBottom: '10px' }),
}, extra.vars || {});
const run = (script, m, extra, call) => vm.runInNewContext(HELPERS[script] + '\n' + FN[script] + '\n' + call, ctx(m, extra));
const out = {};
for (const m of MODELS) {
  const pane = { offsetTop: 100, style: {} }, spTip = { style: {}, offsetWidth: 200, offsetHeight: 100 };
  out[m.name] = {
    cap: run('cap', m, {}, 'cap()'),
    spendCap: (run('spSizePane', m, { byId: { 'rsp-table': pane }, vars: { spPanel: { offsetTop: 0, clientTop: 0 } } }, 'spSizePane()'), pane.style.maxHeight),
    tipTop: (run('spTipPlace', m, { vars: { spTip } }, 'spTipPlace(10, 500, { top: 300 })'), { top: spTip.style.top, left: spTip.style.left }),
    clamp: run('clampXY', m, { vars: { box: { getBoundingClientRect: () => ({ width: 300, height: 20 }) } } }, 'clampXY(0, 5000)'),
  };
}
console.log(JSON.stringify(out));
"""

    @classmethod
    def setUpClass(cls):
        homes = {"cap": km._LANDING_JS, "spSizePane": km._LANDING_USAGE_JS, "spTipPlace": km._LANDING_USAGE_JS,
                 "clampXY": km._STALE_JS}
        fns = {name: _fn(js, name) for name, js in homes.items()}
        for name, src in fns.items():
            assert src, "the shell no longer declares function " + name
        helpers = {name: _fn(js, "layoutH") for name, js in homes.items()}   # '' where the script declares none
        cls.pure = _node(cls._EXTRACT_RUNNER % (json.dumps(fns), json.dumps(helpers), json.dumps([WEBKIT, CHROMIUM])))

    def test_the_timeline_band_cap_is_70_percent_of_the_layout_viewport(self):
        # cap(): the band's ceiling, 70% of the layout viewport (the comment beside it says 70vh). 295 under the WebKit
        # model's innerHeight; 591 of the layout height.
        for m in ("webkit", "chromium"):
            self.assertEqual(self.pure[m]["cap"], 591, m)

    def test_the_spend_list_cap_is_the_layout_viewports(self):
        # spSizePane(): the list pane's room is a cap of 92% of the viewport (the card's own max-height:92vh) less the
        # card's padding (22 here), what is rendered above the pane (100) and 8. The WebKit model's innerHeight gave a
        # cap of 388 and a pane of 258 px inside a card that is 776 px tall; the layout height gives 646 px.
        for m in ("webkit", "chromium"):
            self.assertEqual(self.pure[m]["spendCap"], "646px", m)

    def test_the_spend_tooltip_flips_against_the_layout_viewport(self):
        # spTipPlace(): the tooltip sits below the pointer unless its bottom would pass the viewport's; a pointer at
        # y 500 with a 100 px box ends at 624, inside an 844 layout, so it stays below (top 518). Under the WebKit
        # model's innerHeight (422) it flipped above the chart (top 194) with 220 px of viewport to spare.
        for m in ("webkit", "chromium"):
            self.assertEqual(self.pure[m]["tipTop"], {"top": "518px", "left": "24px"}, m)

    def test_the_drift_banner_clamps_to_the_layout_viewport(self):
        # clampXY(): the draggable banner is kept on screen against the viewport's edges; a 20 px box dragged far down
        # stops at 824 in an 844 layout. Under the WebKit model's innerHeight it stopped at 402, mid-screen.
        for m in ("webkit", "chromium"):
            self.assertEqual(self.pure[m]["clamp"], [0, 824], m)


class InnerHeightCensus(unittest.TestCase):
    """Every innerHeight the shell serves is classified: the helper's fallback, the pane shim's zero test, nothing else."""

    ZERO_TEST = "window.parent!==window&&(window.innerWidth===0||window.innerHeight===0)"
    READERS = {"_LANDING_JS", "_LANDING_USAGE_JS", "_LANDING_MOBILE_JS", "_LANDING_PUSH_JS", "_STALE_JS"}

    def _served(self):
        blobs = {n: v for n, v in vars(km).items() if n.endswith("_JS") and isinstance(v, str)}
        for app, _label in km._PANE_ORDER:                 # every shipped pane page carries the shim
            blobs["_shim(%r)" % app] = km._shim(app)
        blobs["_landing()"] = km._landing()
        return blobs

    def test_every_innerheight_read_the_shell_serves_is_classified(self):
        # The rule over writers: a read of window.innerHeight that means the layout viewport's height is layoutH();
        # a read that means something else is named here with its reason. A new read that is neither reds with its
        # line, so the author classifies it rather than the reviewer.
        helper = km._LAYOUT_H_JS.strip()
        unclassified = []
        for name, js in sorted(self._served().items()):
            for i, line in enumerate(js.split("\n"), 1):
                if "innerHeight" not in line:
                    continue
                if line.strip().startswith("//"):
                    continue                                   # prose
                rest = line
                for known in (helper, self.ZERO_TEST):
                    rest = rest.replace(known, "")
                if "innerHeight" not in rest:
                    continue                                   # the helper's fallback, or the shim's zero test
                col = rest.index("innerHeight")
                unclassified.append("%s line %d: ...%s..." % (name, i, rest[max(0, col - 70):col + 40]))
        self.assertEqual(unclassified, [], "an innerHeight read the census does not know: a layout-viewport read is layoutH(); "
                         "another meaning is named in this test with its reason:\n" + "\n".join(unclassified))

    def test_the_helper_lives_in_every_script_that_reads_the_layout_height(self):
        # the composition: a script that calls layoutH() declares it (each is its own IIFE, and the node harnesses run
        # one at a time), the declaration appears once per script, and the served landing carries no unreplaced marker
        blobs = {n: v for n, v in vars(km).items() if n.endswith("_JS") and isinstance(v, str) and n != "_LAYOUT_H_JS"}
        homes = {n for n, v in blobs.items() if km._LAYOUT_H_JS in v}
        callers = {n for n, v in blobs.items() if v.replace(km._LAYOUT_H_JS, "").count("layoutH()")}
        self.assertEqual(homes, self.READERS, "the scripts that read the layout height (a new reader adds itself here)")
        self.assertEqual(callers, homes, "every script that calls layoutH() declares it, and none declares it idle")
        for n in homes:
            self.assertEqual(blobs[n].count(km._LAYOUT_H_JS), 1, n + ": the helper once, at the IIFE's top")
            self.assertTrue(blobs[n].lstrip().startswith("(function(){" + km._LAYOUT_H_JS.rstrip("\n")), n + ": declared first")
        self.assertNotIn("__ROMP_LAYOUT_H__", km._landing(), "the marker is replaced at definition, never served")

    def test_the_pane_shims_hidden_probe_stays_a_zero_test_on_innerheight(self):
        # paneHidden() asks whether a framed pane's viewport reads 0 (a display:none iframe, in Chromium since load and
        # in Firefox after every hide): a ZERO test, true or false identically for innerHeight and the layout height in
        # both engines, and a pinch never makes a shown frame read 0. Not a layout-viewport stand-in: left on
        # innerHeight, as tests/test_kernel_disconnect_banner.py drives it.
        fn = _fn(km._shim("chat"), "paneHidden")
        self.assertIn(self.ZERO_TEST, fn)
        self.assertNotIn("layoutH", fn)


if __name__ == "__main__":
    unittest.main()
