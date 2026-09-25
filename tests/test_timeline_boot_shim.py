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
        # the fork's registration with federation's frame registry (fed-direct) sits after the chain, once
        self.assertEqual(boot.count('window.addEventListener("message",frameListener);'), 1)
        self.assertEqual(boot.count('if(window.__rompFed&&window.__rompFed.onFrame)window.__rompFed.onFrame(frameListener);'), 1)
        self.assertLess(boot.index("_openViewsDialog(null);};"), boot.index("__rompFed.onFrame(frameListener)"))


# The boot, run in node: stand-ins for the few browser names it touches (HTMLElement for the DOM shims, the host
# bridge acquireVsCodeApi, the shell as window.parent), a fake panel, and the one window message listener it registers.
_BOOT_HARNESS = r"""
'use strict';
const ORIGIN = 'http://127.0.0.1:7777', OTHER = 'https://elsewhere.example';
const LISTENERS = [], UPDATES = [];
global.HTMLElement = function () {};
global.window = global;
const SHELL = { name: 'shell' };
global.parent = SHELL;
const OPENER = { name: 'a page on another origin that opened /timeline' };
global.opener = OPENER;
global.location = { origin: ORIGIN };
global.acquireVsCodeApi = () => ({ postMessage() {} });
global.addEventListener = (t, f) => { if (t === 'message') LISTENERS.push(f); };
BOOT
window.__rompConnectTimeline({ update: (d) => UPDATES.push(d.from) });
const SENDERS = {
  dispatch: [null, ''],          // the shim's and federation.js's frames: a MessageEvent with no source and no origin
  fedDirect: [undefined, undefined],   // federation.js's direct call with a bare event
  self: [window, ORIGIN],
  embedder: [SHELL, ORIGIN],      // the shell, this frame's parent
  peer: [{}, ORIGIN],             // another window on this origin
  opener: [OPENER, OTHER],        // the page on another origin that opened /timeline: this window's opener
  stranger: [{}, OTHER],          // a window on another origin this one does not know
  sandboxed: [{}, 'null'],        // a sandboxed frame
  sandboxedSibling: [{ parent: SHELL }, 'null'],   // a sandboxed frame beside this one in the shell
  sandboxedChild: [{ parent: window }, 'null'],    // a sandboxed frame inside this one
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
process.stdout.write(JSON.stringify({ listeners: LISTENERS.length, updates: UPDATES }));
"""


class TimelineBootSenders(unittest.TestCase):
    """The browser timeline's frame listener acts on a frame only from the senders windowSender hears
    (ui/webview/window-sender.ts): this page's own dispatch, this window, its parent (the shell), a window on this
    origin (2026-09-25). A frame from any other sender (a page on another origin, a sandboxed frame) is ignored.
    ui/webview/timeline-boot-senders.test.ts pins the rule to windowSender itself, over a grid of receiving windows,
    senders and origins; the rows here keep the kernel's own suite red on the widenings that grid names."""

    def test_a_data_frame_is_drawn_from_every_heard_sender_and_from_no_other(self):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("node not installed")
        fx = tempfile.mkdtemp()
        try:
            path = os.path.join(fx, "boot.js")
            with open(path, "w") as f:
                f.write(_BOOT_HARNESS.replace("BOOT", km._TIMELINE_BOOT))
            r = subprocess.run([node, path], capture_output=True, text=True, timeout=60)
        finally:
            shutil.rmtree(fx, ignore_errors=True)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        got = json.loads(r.stdout)
        self.assertEqual(got["listeners"], 1, "the boot registers one window message listener")
        self.assertEqual(got["updates"], ["dispatch", "fedDirect", "self", "embedder", "peer"],
                         "drawn once from each heard sender, never from a page on another origin (the one that opened "
                         "this page included), a sandboxed frame (beside or inside this one, or gone after it posted), "
                         "an origin that overlaps this one's text or differs only in its port, or a sourceless post "
                         "that names another origin")

    def test_source_the_check_heads_the_frame_listener(self):
        boot = km._TIMELINE_BOOT
        self.assertIn('var onFrame=function(ev){if(!heardSender(ev))return;var m=ev.data;if(!m||!panel)return;', boot)
        self.assertEqual(boot.count("function heardSender(e){"), 1)
        self.assertLess(boot.index("function heardSender(e){"), boot.index("var onFrame=function(ev){"))


if __name__ == "__main__":
    unittest.main()
