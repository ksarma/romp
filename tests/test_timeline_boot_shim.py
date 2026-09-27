#!/usr/bin/env python3
"""The timeline page's inline boot script (kernel _TIMELINE_BOOT) dispatches each frame type ONCE.

The boot's else-if chain mirrors ui/webview/timeline-boot.ts's dispatchFrame (the browser's copy and the VS
Code webview's; timeline-boot.test.ts pins the bridge set they share). The 2026-09-08 fold's first catch-up
merge kept BOTH sides' copies of three branches (tagEditAck/viewsAck, caps, unknownOp) around upstream's new
settingRefused line: dead in an else-if chain (the first match wins), but a chain that matched neither
parent, read as two intended handlers, and would re-conflict on the next fold. Pinned here: every frame
type has one branch, the chain is upstream's, and the fork's fed-direct registration follows it."""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads (they resolve their state root at import time; only pytest runs
# conftest's floor, and a bare unittest or script run would otherwise write REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_timeline_boot_shim", os.path.join(BIN, "romp-kernel"))

FRAME_TYPES = ("data", "bars", "activeChat", "hover", "revealEvent", "models", "settingRefused",
               "tagEditAck", "viewsAck", "caps", "unknownOp", "tagEditFailed", "openViewsDialog")


class TimelineBootDispatch(unittest.TestCase):
    def _chain(self):
        boot = km._TIMELINE_BOOT
        i = boot.index("var onFrame=function(ev){")
        j = boot.index("};", i)
        return boot[i:j]

    def test_every_frame_type_has_exactly_one_branch(self):
        chain = self._chain()
        types = re.findall(r'm\.type==="([A-Za-z]+)"', chain)
        self.assertEqual(sorted(t for t in set(types) if types.count(t) > 1), [],
                         "a frame type with two branches: the second is unreachable and reads as intended")
        for t in FRAME_TYPES:
            self.assertEqual(types.count(t), 1, t)
        self.assertEqual(sorted(set(types)), sorted(FRAME_TYPES), "the chain's set is the dispatcher's")

    def test_the_caps_line_is_counted_once_and_the_fed_direct_registration_follows(self):
        boot = km._TIMELINE_BOOT
        self.assertEqual(boot.count('else if(m.type==="caps"&&panel.setCaps)panel.setCaps(m);'), 1)
        self.assertEqual(boot.count('else if(m.type==="settingRefused"&&panel.settingRefused)panel.settingRefused(m);'), 1)
        self.assertEqual(boot.count('else if(m.type==="unknownOp"&&panel.unknownOp)panel.unknownOp(m);'), 1)
        # the fork's registration with federation's frame registry (fed-direct) sits after the chain, once, after the
        # window listener (the sender check in front of the same listener)
        self.assertEqual(boot.count('window.addEventListener("message",function(e){if(!heardSender(e))return;frameListener(e);});'), 1)
        self.assertEqual(boot.count('if(window.__rompFed&&window.__rompFed.onFrame)window.__rompFed.onFrame(frameListener);'), 1)
        self.assertLess(boot.index("_openViewsDialog(null);};"), boot.index("__rompFed.onFrame(frameListener)"))


# The boot, run in node: stand-ins for the few browser names it touches (HTMLElement for the DOM shims, the host
# bridge acquireVsCodeApi, the shell as window.parent, the shell's own parent as window.top, and window.frames, which
# is the window itself, whose length and indexes list the two frames inside this one), a fake panel, and the one
# window message listener it registers. ROMP_TEST_OWN is the page's own origin ("-" for a page with no location);
# ROMP_TEST_PERF=1 publishes a performance collector on window.__rompPerf first, as federation.js does on the kernel's
# page, in the shape of perf-telemetry.ts's wrapFrameHandler, counting every message it is handed.
_BOOT_HARNESS = r"""
'use strict';
const ORIGIN = 'http://127.0.0.1:7777', OTHER = 'https://elsewhere.example';
const OWN = process.env.ROMP_TEST_OWN;
const LISTENERS = [], UPDATES = [], COUNTED = [];
global.HTMLElement = function () {};
global.window = global;
const GRAND = { name: "the shell's own parent" };
const SHELL = { name: 'shell', parent: GRAND };
global.parent = SHELL;
global.top = GRAND;
const OPENER = { name: 'a page on another origin that opened /timeline' };
global.opener = OPENER;
// the frames in this tab besides this one and the shell: each shares this window's top, the shell's own parent
const SIBLING_SAME_TOP = { name: 'a sandboxed frame beside this one', parent: SHELL, top: GRAND };
const CHILD_SAME_TOP = { name: 'a sandboxed frame inside this one', parent: window, top: GRAND };
const OWN_ORIGIN_CHILD = { name: 'a frame inside this one on its origin', parent: window, top: GRAND };
// the frames inside this one, as a browser lists them: window.frames is the window itself, with a length and an index each
global.frames = global;
global.length = 2;
global[0] = CHILD_SAME_TOP;
global[1] = OWN_ORIGIN_CHILD;
global.location = OWN === '-' ? undefined : { origin: OWN };
global.acquireVsCodeApi = () => ({ postMessage() {} });
global.addEventListener = (t, f) => { if (t === 'message') LISTENERS.push(f); };
if (process.env.ROMP_TEST_PERF === '1') {
  global.__rompPerf = { wrapFrameHandler: (h) => (e) => { COUNTED.push(e && e.data && e.data.data && e.data.data.from); return h(e); } };
}
BOOT
window.__rompConnectTimeline({ update: (d) => UPDATES.push(d.from) });
const SENDERS = {
  dispatch: [null, ''],          // the shim's and federation.js's frames: a MessageEvent with no source and no origin
  fedDirect: [undefined, undefined],   // federation.js's direct call with a bare event
  self: [window, ORIGIN],
  embedder: [SHELL, ORIGIN],      // the shell, this frame's parent
  peer: [{}, ORIGIN],             // another window on this origin
  ownOriginChild: [OWN_ORIGIN_CHILD, ORIGIN],      // a frame inside this one on this origin, in its frames: a peer
  opener: [OPENER, OTHER],        // the page on another origin that opened /timeline: this window's opener
  top: [GRAND, OTHER],            // the top window, the shell's own parent on another origin: not this frame's parent
  stranger: [{}, OTHER],          // a window on another origin this one does not know
  sandboxed: [{}, 'null'],        // a sandboxed frame
  sandboxedSibling: [{ parent: SHELL }, 'null'],   // a sandboxed frame beside this one in the shell
  sandboxedChild: [{ parent: window }, 'null'],    // a sandboxed frame inside this one
  sandboxedSiblingSameTop: [SIBLING_SAME_TOP, 'null'],   // a sandboxed frame beside this one, sharing its top
  sandboxedChildInFrames: [CHILD_SAME_TOP, 'null'],      // a sandboxed frame inside this one, sharing its top, in its frames
  overlappingOrigin: [{}, ORIGIN + '0'],           // another port whose text begins with this origin
  noPort: [{}, 'http://127.0.0.1'],                // this origin's scheme and host on another port (the default)
  otherPort: [{}, 'http://127.0.0.1:7778'],        // this origin's scheme and host on another port
  sourcelessElsewhere: [null, OTHER],
  sourcelessOpaque: [null, 'null'],                // a sandboxed frame gone after it posted
};
Object.keys(SENDERS).forEach((k) => {
  const e = { data: { type: 'data', data: { from: k } } };
  if (SENDERS[k][0] !== undefined) { e.source = SENDERS[k][0]; e.origin = SENDERS[k][1]; }
  LISTENERS.forEach((f) => f(e));
});
process.stdout.write(JSON.stringify({ listeners: LISTENERS.length, updates: UPDATES, counted: COUNTED,
                                      perf: typeof global.__rompPerf === 'object' }));
"""
_OWN_ORIGIN = "http://127.0.0.1:7777"   # the harness's ORIGIN
_HEARD = ["dispatch", "fedDirect", "self", "embedder", "peer", "ownOriginChild"]
_HEARD_NO_PEER = ["dispatch", "fedDirect", "self", "embedder"]


def _run_boot(own, perf):
    node = shutil.which("node")
    if not node:
        raise unittest.SkipTest("node not installed")
    fx = tempfile.mkdtemp()
    try:
        path = os.path.join(fx, "boot.js")
        with open(path, "w") as f:
            f.write(_BOOT_HARNESS.replace("BOOT", km._TIMELINE_BOOT))
        r = subprocess.run([node, path], capture_output=True, text=True, timeout=60,
                           env=dict(os.environ, ROMP_TEST_OWN=own, ROMP_TEST_PERF="1" if perf else "0"))
    finally:
        shutil.rmtree(fx, ignore_errors=True)
    if r.returncode != 0:
        raise AssertionError("node failed:\n" + r.stderr[-2000:])
    got = json.loads(r.stdout)
    if got["perf"] != perf:
        raise AssertionError("the harness published a collector: %r, asked for %r" % (got["perf"], perf))
    return got


class TimelineBootSenders(unittest.TestCase):
    """The browser timeline's window listener hands a message on only from the senders windowSender hears
    (ui/webview/window-sender.ts): this page's own dispatch, this window, its parent (the shell), a window on this
    origin (2026-09-25). A message from any other sender (a page on another origin, the top window above the shell, a
    sandboxed frame) is dropped there, before the page's performance collector sees it: neither drawn nor counted.
    ui/webview/timeline-boot-senders.test.ts pins the rule to windowSender itself, over a grid of receiving windows,
    senders and origins, with and without a real collector. The rows here hold the same rule in the kernel's own suite
    over named senders, on a page on a loopback origin, on a page whose own origin is opaque (no window is a peer of it)
    and on a page with no location; the receivers only that grid holds are VS Code's webview frames, whose parent is
    the frame itself or deleted."""

    def test_a_data_frame_is_drawn_from_every_heard_sender_and_from_no_other(self):
        got = _run_boot(_OWN_ORIGIN, perf=False)
        self.assertEqual(got["listeners"], 1, "the boot registers one window message listener")
        self.assertEqual(got["updates"], _HEARD,
                         "drawn once from each heard sender (a frame inside this one on its origin included), never "
                         "from a page on another origin (the one that opened this page included), the top window above "
                         "the shell, a sandboxed frame (beside or inside this one, sharing its top or not, listed in its "
                         "frames or not, or gone after it posted), an origin that overlaps this one's text or differs "
                         "only in its port, or a sourceless post that names another origin")

    def test_with_the_pages_collector_a_foreign_message_is_neither_drawn_nor_counted(self):
        # the collector wraps the frame listener; the sender check runs outside it, so the collector counts exactly
        # the frames the page draws
        got = _run_boot(_OWN_ORIGIN, perf=True)
        self.assertEqual(got["listeners"], 1)
        self.assertEqual(got["updates"], _HEARD)
        self.assertEqual(got["counted"], _HEARD, "the collector counted only the heard senders' frames")

    def test_on_a_page_whose_own_origin_is_opaque_no_window_is_a_peer(self):
        # a sandboxed page's origin is "null", and so is every sandboxed frame's: the same text is no shared origin
        for perf in (False, True):
            with self.subTest(perf=perf):
                got = _run_boot("null", perf=perf)
                self.assertEqual(got["updates"], _HEARD_NO_PEER, "a sandboxed frame (origin \"null\") is no peer")
                self.assertEqual(got["counted"], _HEARD_NO_PEER if perf else [])

    def test_on_a_page_with_no_location_no_window_is_a_peer(self):
        for perf in (False, True):
            with self.subTest(perf=perf):
                got = _run_boot("-", perf=perf)
                self.assertEqual(got["updates"], _HEARD_NO_PEER)
                self.assertEqual(got["counted"], _HEARD_NO_PEER if perf else [])

    def test_source_the_check_heads_the_window_listener_outside_the_collector(self):
        boot = km._TIMELINE_BOOT
        self.assertIn('window.addEventListener("message",function(e){if(!heardSender(e))return;frameListener(e);});', boot)
        self.assertEqual(boot.count("function heardSender(e){"), 1)
        self.assertEqual(boot.count("heardSender("), 2, "defined once, called once: by the window listener")
        self.assertLess(boot.index("function heardSender(e){"), boot.index('window.addEventListener("message",'))
        # the registry path takes the listener as it is: only federation.js calls it, with a MessageEvent it built
        self.assertIn("window.__rompFed.onFrame(frameListener);", boot)


if __name__ == "__main__":
    unittest.main()
