#!/usr/bin/env python3
"""The timeline page's inline boot script (kernel _TIMELINE_BOOT) dispatches each frame type ONCE.

The boot's else-if chain mirrors ui/webview/timeline-boot.ts's dispatchFrame (the browser's copy and the VS
Code webview's; timeline-boot.test.ts pins the bridge set they share). The 2026-09-08 fold's first catch-up
merge kept BOTH sides' copies of three branches (tagEditAck/viewsAck, caps, unknownOp) around upstream's new
settingRefused line: dead in an else-if chain (the first match wins), but a chain that matched neither
parent, read as two intended handlers, and would re-conflict on the next fold. Pinned here: every frame
type has one branch, the chain is upstream's, and the fork's fed-direct registration follows it."""
import os
import re
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


if __name__ == "__main__":
    unittest.main()
