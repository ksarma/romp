#!/usr/bin/env python3
"""The "Files" pane (app=files): the file VIEWER as its own column of the dashboard, beside Chat,
Sessions, Outline, Feed and Waiting, with the gear's "File links open in" gaining a third value
("pane") that routes a chat file-link click into it. Kernel side, pinned here:

- the pane is NOT a feed consumer. The viewer is request/response (HTTP /file for the bytes; the
  saveFile / fileGitLink / listDir ops answer the SENDING client), so app=files is absent from the
  feed send set, the send loop and the ready fast-serve — _push builds nothing for it — and present
  only where a live pane must count: the conserve-memory viewer list.
- the /files page: the chat's styles.css for the viewer's dress, files-pane.css read live for the
  layout and the pane-resident variant (body.fileview-pane), NO romp loader (an empty pane is not a
  loading state), the shim with the ready hold alone, federation.js before files.js.
- the shell: a sixth pane after Waiting, default OFF, with its gutter, grow var, focus/Esc/mobile
  wiring and the _PANE_ORDER label "Files"; the viewFile relay's `pane` branch, which brings the
  pane forward and forwards the click (identity included) into it — with none of the feed route's
  was-off / ack / restore machinery, since the pane stays up.

SYNTHETIC fixtures only (the notes-api demo world); no session data is minted here.
"""
import os
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ["ROMP_SERVE_TOKEN"] = "testtok"
km = SourceFileLoader("romp_kernel_fpane", os.path.join(BIN, "romp-kernel")).load_module()
SRC = open(os.path.join(BIN, "romp-kernel")).read()
UI = Path(BIN).parent / "ui" / "webview"


class Plumbing(unittest.TestCase):
    """app=files is a viewer to the kernel, not a feed client: keepalives and its own op replies ride
    its socket, nothing is built for it, and it counts as a live dashboard for conserve-memory."""

    def test_files_is_not_in_the_feed_send_set_loop_or_ready_serve(self):
        # the feed-consumer tuples are verbatim from before the pane: adding "files" to any of them would
        # build and ship a feed frame nobody reads
        self.assertIn('want_feed = any(c["app"] in ("feed", "fleet", "waiting", "chat") for c in targets)', SRC)
        self.assertIn('if c["app"] in ("feed", "fleet", "waiting"):', SRC)
        self.assertIn('served = client.get("app") in ("feed", "fleet", "waiting") and _send_feed_now(client)', SRC)
        self.assertIn('if not (served and client.get("app") in ("feed", "waiting")):', SRC)
        push = SRC[SRC.index("def _push(targets"):]
        push = push[:push.index("\ndef ")]
        self.assertNotIn('"files"', push, "_push names every app it builds for; the Files pane is not one")

    def test_the_socket_accepts_any_app_name(self):
        # the handshake has no allowlist, so app=files connects on a kernel exactly as the other panes do
        self.assertIn('app = (q.get("app") or ["chat"])[0]', SRC)

    def test_an_open_files_pane_counts_as_a_viewer_for_conserve_memory(self):
        self.assertIn('c.get("app") in ("chat", "fleet", "timeline", "feed", "waiting", "files")', SRC)

    def test_the_page_carries_the_hold_alone_the_shared_dress_and_no_loader(self):
        page = km._files_page()
        self.assertIn('_shim("files", v, caps=READY_GATE_CAP)', SRC)
        self.assertNotIn('_shim("files", v, caps=FEED_DELTA_CAP', SRC)
        self.assertIn("app=files", page)
        self.assertIn('var CAPS="readyGate"', page)
        self.assertIn("/dist/styles.css", page)                     # the viewer's .fileview-* dress
        self.assertIn("<body class=fileview-pane>", page)           # keys the pane-resident variant
        self.assertIn("<div id=files-empty></div>", page)
        self.assertIn("/dist/federation.js", page)
        self.assertIn("/dist/files.js", page)
        self.assertLess(page.index("/dist/federation.js"), page.index("/dist/files.js"), "manager before the bundle")
        self.assertNotIn("id=pane-spin", page, "an empty pane is not a loading state")
        self.assertNotIn("rel=manifest", page)
        self.assertIn('if p == "/files":', SRC)
        self.assertIn("_files_page()", SRC)
        # the sheet is read live, like fleet-pane.css; a missing one fails loudly on the page, never blank
        css = (UI / "files-pane.css").read_text()
        self.assertIn(css.splitlines()[-1], page)
        with mock.patch.object(Path, "read_text", side_effect=OSError("gone")):
            self.assertIn("needs the ui/ modules", km._files_page())

    def test_the_pane_resident_variant_lives_only_in_the_pane_sheet(self):
        # the modal variant is mirrored byte-equal in styles.css and feed.css (fileview-parity.test.ts);
        # the pane's override must not enter either, or the mirrors drift
        css = (UI / "files-pane.css").read_text()
        self.assertIn("body.fileview-pane #romp-fileview{position:relative;inset:auto;flex:1 1 auto;min-height:0;background:none}", css)
        self.assertIn("body.fileview-pane .fileview{width:100%;height:100%;border:0;border-radius:0;box-shadow:none}", css)
        for sheet in ("styles.css", "feed.css"):
            self.assertNotIn("fileview-pane", (UI / sheet).read_text(), sheet)
        self.assertNotIn("fleet", css.lower(), "no fleet vocabulary in the new sheet")


if __name__ == "__main__":
    unittest.main()
