#!/usr/bin/env python3
"""The premise the shell's layoutH() rests on, read in real engines at rest (2026-09-21): the served landing page is
in standards mode, its root is overflow:hidden, and the root element's clientHeight equals window.innerHeight and the
viewport's height at page scale 1, so a shell read that moved from innerHeight to layoutH() publishes the same value
there (the no-op half of tests/test_layout_viewport_height.py, in an engine). Measured as a desktop (a mouse, 1280 by
820: the fine-pointer fit publishes the layout height as --app-h) and as a phone (390 by 844, touch: the fit publishes
the visual viewport's layout-scaled height, the keyboard-open test reads closed so the tab bar's strip is reserved, and
a bell tap places the popover where innerHeight would have placed it).

What this cannot read, said plainly: a page scale above 1. Playwright's WebKit holds none on Linux (no CDP, a
tap-only touchscreen, the zoom chord changes nothing), so the pinch itself stays in the node models. Skips LOUDLY
without a playwright (set ROMP_PLAYWRIGHT_NODE_PATH to a node_modules holding it; CI's extension job runs Chromium and
declares ROMP_SERVED_TESTS_ENGINES, so the WebKit leg is an `optional:` skip there). The page is the kernel module's own
_landing() served from a thread, over blank pane pages: no kernel boots and no session data exists."""
import json
import os
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the load: the kernel resolves its state root at import time.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
km = load_source("romp_kernel_layouth_served", os.path.join(BIN, "romp-kernel"))


def _node_path():
    for cand in (os.environ.get("ROMP_PLAYWRIGHT_NODE_PATH", ""), os.path.join(ROOT, "vscode-extension", "node_modules")):
        if cand and os.path.isdir(os.path.join(cand, "playwright")):
            return cand
    return ""


class LayoutHeightServed(unittest.TestCase):
    def setUp(self):
        np = _node_path()
        if not np:
            self.skipTest("no playwright: set ROMP_PLAYWRIGHT_NODE_PATH to a node_modules that holds it")
        self.node_path = np
        html = km._landing().encode()
        self.assertNotIn(b"__ROMP_LAYOUT_H__", html, "the helper's marker is replaced at definition")
        blank = b"<!doctype html><html><body style='margin:0;background:#1e1e1e'></body></html>"
        pane_pages = {"/" + key for key, _label in km._PANE_ORDER} | {"/settings", "/dashboard"}   # the iframes' pages: blank here

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _out(self, code, body, ctype):
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                p = self.path.split("?", 1)[0]
                if p == "/":
                    return self._out(200, html, "text/html; charset=utf-8")
                if p.startswith("/media/") or p.startswith("/dist/"):
                    f = os.path.join(ROOT, p.lstrip("/"))
                    if os.path.isfile(f):
                        ct = "image/svg+xml" if f.endswith(".svg") else "application/javascript" if f.endswith(".js") else "application/octet-stream"
                        return self._out(200, open(f, "rb").read(), ct)
                    return self._out(404, b"", "text/plain")
                if p in pane_pages:
                    return self._out(200, blank, "text/html; charset=utf-8")
                return self._out(200, b"{}", "application/json")

            def do_POST(self):
                return self._out(200, b"{}", "application/json")

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self):
        if hasattr(self, "srv"):
            self.srv.shutdown()
            self.srv.server_close()

    def _drive(self, browser):
        env = dict(os.environ, NODE_PATH=self.node_path)
        r = subprocess.run(["node", os.path.join(HERE, "layout_height_browser.js"), "http://127.0.0.1:%d/" % self.port, browser],
                           capture_output=True, text=True, timeout=240, env=env)
        self.assertEqual(r.returncode, 0, "the driver failed:\n" + r.stderr[-3000:])
        o = json.loads(r.stdout.strip().splitlines()[-1])
        if o.get("skipped"):
            declared = os.environ.get("ROMP_SERVED_TESTS_ENGINES", "")
            if declared and browser not in [e.strip() for e in declared.split(",")]:
                # a runner that says which engines it installed leaves the other legs as skips even under
                # ROMP_SERVED_TESTS_REQUIRE=1, which honours this prefix (tests/conftest.py)
                self.skipTest("optional: this runner declares no %s (ROMP_SERVED_TESTS_ENGINES=%s): %s" % (browser, declared, o["skipped"]))
            self.skipTest("no playwright %s on this machine; this leg needs it: %s" % (browser, o["skipped"]))
        return o

    def _check(self, browser, o):
        for shell, height in (("desktop", 820), ("phone", 844)):
            s = o[shell]
            where = "%s, %s: " % (browser, shell)
            self.assertEqual(s["errors"], [], where + "no script error on the landing page")
            # the premise: standards mode and a root that never scrolls, so clientHeight is the layout viewport's height
            self.assertEqual(s["compatMode"], "CSS1Compat", where + "the landing is in standards mode (its doctype)")
            self.assertEqual((s["rootOverflow"], s["bodyOverflow"]), ("hidden", "hidden"), where + "the root and body are overflow:hidden")
            # the no-op half at scale 1: the two reads agree with each other and with the viewport the context set
            self.assertEqual(s["vvScale"], 1, where + "page scale 1 (this leg holds no pinch)")
            self.assertEqual((s["clientHeight"], s["innerHeight"], s["vvHeight"]), (height, height, height),
                             where + "clientHeight, innerHeight and the visual viewport agree at rest: " + json.dumps(s))
            if shell == "desktop":
                self.assertFalse(s["coarse"], where + "a mouse: the fine road")
                self.assertEqual(s["appH"], "%dpx" % height, where + "the fine road published the layout height")
            else:
                self.assertTrue(s["coarse"], where + "touch: the coarse road")
                self.assertTrue(s["barShown"], where + "the phone shell shows the tab bar")
                self.assertEqual(s["appH"], "%dpx" % height, where + "the coarse road published the visual viewport's layout-scaled height")
                self.assertNotEqual(s["barH"], "0px", where + "the keyboard reads closed at rest, so the bar's strip is reserved: " + json.dumps(s))
                b = s["bell"]
                self.assertTrue(b["open"], where + "the bell tap opened the popover")
                self.assertEqual(b["bottom"], b["fromClient"], where + "the popover's bottom is measured from the layout viewport: " + json.dumps(b))
                self.assertEqual(b["bottom"], b["fromInner"], where + "and equals what innerHeight gave at scale 1, the no-op half: " + json.dumps(b))

    def test_chromium(self):
        self._check("chromium", self._drive("chromium"))

    def test_webkit(self):
        self._check("webkit", self._drive("webkit"))


if __name__ == "__main__":
    unittest.main()
