#!/usr/bin/env python3
"""The todo Reply sheet on a phone with the keyboard up, in the pages the kernel SERVES, in a real engine (PR 859, the
maintainer's round 1 ruling: a layout fix with no executed leg in CI cannot be reviewed).

The two node browser legs (ui/webview/waiting-reply-sheet-browser.test.ts, render-reply-sheet-browser.test.ts) measure
the sheet in three engines where a box has them, and skip where it does not. None of the extension job's browser-backed
steps runs them: the job's Test step (`npm test`) runs them before the job installs its browser, so they skip there, and
they are not on the roster of "Browser legs (node --test over ci-browser-legs.txt)" (each launches its own engines and
skips an absent one, which that step's roster rule refuses). This leg runs in the job's "Browser-backed served-page tests
(pytest)" step (ci.yml, ROMP_SERVED_TESTS_REQUIRE=1: a skip here is a failure), against the
pages as the kernel serves them from a private dist, with the REAL builders (waiting.ts showReply in /waiting, render.ts
showUserTodoReply in /chat), so it is the guard the node legs name where they skip.

The composition the ruling asked for, per pane, asserted FIRST so that on a tree without the fix the tap's own outcome
is the red (on the round-1 tree the first red used to be a computed-style read before it): a viewport of 390 by 508
(inside the shell the pane iframe is sized to the visible height, so the pane's own innerHeight is the fold's signal;
508 is a phone's visible height with the keyboard up, above the fold's 480px threshold), a todo with a
near-300-character ask, a file chip, a link chip and a forty-line detail whose first line carries an address and whose
last line is an unbreakable token; Reply tapped, fourteen lines typed, then a real click at Send's painted centre.
Asserted: the click puts a userTodoAnswer frame for the todo on the page's socket and the sheet closes by that send
(never by the backdrop: on the round-1 tree the answer box, capped at a share of the WINDOW, laid the buttons out below
an overflow hidden box; a tap there fell on the backdrop, which closes the sheet with no save, and nothing was sent),
Send and Cancel inside the box's clip and the frame, elementFromPoint at Send's centre IS Send, the detail at its floor
of two lines in that state (it resolved to 0px before).

Then the states the fix's other rules and handlers are for, each read from the engine here because the node legs that
read them skip in CI: at 300px (the fold on) the sheet is pinned to the top under the picker's 12px frame
(#ut-reply-prompt.kb-tight), the detail keeps two lines and scrolls within itself, its first line's address is under a
finger once the box is scrolled to it, the box scrolls, Send is inside the clip and under a finger at the box's bottom;
at 420px with the same todo the pane's two chip rows put the floors alone past the fold's cap, so its box scrolls a few
pixels and Send's centre stays under a finger (the backstop state, measured as it is), while the chat's column fits (the
fitted state); the unbreakable token wraps, so the detail's scrollWidth is no wider than its offsetWidth, the border box
(overflow-wrap: anywhere); the answer typed at 900px and the window then shrunk to 508 re-fits the answer box (kbFit
re-runs grow on the resize); and on the other todo's sheet an inline height written as the resize grip writes it stands
through a keystroke (the drag guard); written to 215px and the frame taken to 420, the dragged height is clamped to the
room the box has under the fold, not to the content, and returns to 215px at 508 (a dragged height is the person's
preference on the resize path); then the grip pulled past the box's bottom edge and released over the backdrop,
and a text selection dragged from inside the box onto the backdrop, each leave the sheet up with its text (a click whose
press began inside the sheet is not a backdrop tap: Chromium and WebKit dispatch it to the overlay, the common ancestor
of the press and the release, and before the guard both gestures closed the sheet with the answer; Firefox retargets it
to the textarea), and a plain tap on the backdrop, press and release both on it, then dismisses. And the tree each
builder emits, read from the real pages: the pane's chips are
flex children of the box, the chat's sit inside the quoted line, and the elements the fix's four rules key on match
their selectors in both.

The detail's cap at rest (the maintainer's ruling at the merge with main): with the keyboard down it is the larger of
12em and 34.8% of the window's height, with the keyboard up 12em, as before. Asserted at rest at 900, 1080 and the
installed app's pane on a 390x844 phone, 732, on the composition's todo with its answer box cleared (the viewport term:
the cap is 34.8% of the window's height and the long detail is laid out at it, under the room, so in the pane, where
that todo's two chip rows leave the least room, a share past the band the maintainer ruled (up to 0.354 at 732) is
its red, the sheet fitting with Send under a finger); at Safari's panes, 709 (the toolbars collapsed), 633 (the common
one) and 620, where that todo's room in the pane is under the cap, the cap is the viewport term, the shrink sets the
detail's height under it and the sheet fits the same way; under the keyboard at 508 on the other todo's sheet at open
(12em); and the stated boundary on a third todo whose detail is the recorded 8-line one (styles.css: in full from a
720px pane): in full at 732 and at 720, not in full one pixel under the engine's own boundary (719 in Chromium, 716 in
WebKit, 717 in Firefox) and at 633, where it shows the cap and scrolls the rest. The page is served with its webfont, as a
phone gets it, so these are the geometries styles.css states. The detail's cap reads the keyboard where the shell
does (restCap; kernel.py kbOpen): these pages are top-level, so the driver stubs the page's visualViewport.height a
keyboard's height under its innerHeight while the keyboard is up and removes the stub at rest.

After the composition's send the chat page's card is rebuilt by the kernel's pushes that follow it (the other todo's
Reply button becomes a new node), so the driver waits for that rebuild before it opens the other todo's sheet and records
a button that vanished under its click as its own failure line naming the element (PR 859's CI red at the pass's pushed
head, chromium chat: a scroll-into-view on a handle resolved before the rebuild). The sheet's own node survives the
rebuild in both panes (the reviewer's forcing, in the review record).

The lab: one kernel from test_ship_reship_served.kernel_env (a private XDG root, `session-hosts` floored off,
ROMP_MANAGER_PORT=1, no catalog or update fetch, a hermetic postal bus), a private dist (lab_dist.copy_dist), the three
synthetic notes-api sessions test_return_from_background_served seeds (placeholder uuids, host TESTHOST), the todo store
and the feature switch written in the shapes the kernel writes them (kernel.py _register_user_todo: {sid: [record]};
user-todos-enabled.json: {"enabled": true, "gt": ms}). The kernel's answer to the send is not asserted (no backend owns
a lab session; a parked or refused send is the kernel's business and is pinned elsewhere): what is asserted is the page's
side, the frame it sent and the sheet it closed. Skips LOUDLY without the extension deps or a Chromium (CI runs the
*_served.py files under ROMP_SERVED_TESTS_REQUIRE=1); the Firefox and WebKit legs are `optional:` skips where that engine
is absent or not declared in ROMP_SERVED_TESTS_ENGINES (CI declares chromium; a developer's box runs all three). The lab
kernel uses its own port; the driver asserts /healthz on that port before any request. Synthetic sessions only.
"""
import json
import lab_dist
import os
import shutil
import signal
import socket
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
import test_ship_reship_served as _lab                      # noqa: E402  (kernel_env: every lab kernel's environment)
import test_return_from_background_served as _ret          # noqa: E402  (_seed: the notes-api demo's three synthetic sessions)

# Hermetic state BEFORE anything: this module loads no romp code in-process (the kernel is a subprocess under
# kernel_env's roots), but the floor costs two lines and a later edit that adds a load must not write real state.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
os.makedirs(os.path.join(os.environ["XDG_STATE_HOME"], "romp"), exist_ok=True)
Path(os.environ["XDG_STATE_HOME"], "romp", "session-hosts").write_text("off\n")   # the Testing rule for a test that mints its own root

DRIVER = os.path.join(HERE, "reply_sheet_browser.mjs")
HOST = "TESTHOST"
SID = _ret.SESSIONS[0][0]   # the todos ride the first synthetic session (web)
# the composition fixture, the node legs' own: a wrapped ask near the kernel's 300-character cap, an invented file, an
# address, and a detail whose first line carries an address and whose last line is an unbreakable token wider than the
# sheet (without overflow-wrap: anywhere it made the detail a sideways scroller)
LONG_TEXT = ("Which layout should the quarterly report use for the regional tables, the summary section and the appendix, "
             "given that the notes under each table now run to several lines and the reviewers asked for the totals to "
             "lead every page rather than close it?")
FILE = "/srv/notes-api/docs/quarterly-report-layout.md"
LINK = "https://github.com/example-org/notes-api/pull/398"
DETAIL = "\n".join("Option %d: the summary section leads and the tables follow, with the notes folded under each table." % (i + 1)
                   for i in range(40)) + "\nreport-layout-" + "x" * 90
LINKED_DETAIL = "The earlier draft is at https://github.com/example-org/notes-api/pull/398 and the reviewers' notes follow.\n" + DETAIL
# the recorded 8-line detail (the review record's extra10-4, 251px at this width): the stated boundary is read on it
DETAIL8 = "\n".join("Option %d: the summary section leads and the tables follow, with the notes folded under each table." % (i + 1)
                    for i in range(8))
TID = "ut-0000a002"   # the record's id shape: "ut-" + 8 hex (kernel.py _register_user_todo)
TID_OTHER = "ut-0000a001"   # the short-ask todo: the drag guard is read on its sheet after the composition's send closed the other
TID_EIGHT = "ut-0000a003"   # a short ask and the 8-line detail: the stated boundary is read on its sheet, last
REST_SHARE = 0.348   # the detail's cap at rest: max(12em, 34.8% of the window's height) (styles.css, where the share is derived)
BOUNDARY = 720   # the stated boundary: the 8-line detail shows in full from a 720px pane (a 751px Safari window)
# one pixel under each engine's own boundary (720 in Chromium, 717 in WebKit, 718 in Firefox; measured in both panes)
BELOW_BOUNDARY = {"chromium": 719, "firefox": 717, "webkit": 716}


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def _todo_store(now):
    """The store as _register_user_todo writes it: sid to a LIST of records, id, text, createdT, and detail, file, link
    when present. Three todos: one with a short ask and the forty-line detail, the composition fixture, and a short ask with
    the 8-line detail."""
    return {SID: [
        {"id": TID_OTHER, "text": "Which layout should the quarterly report use?", "createdT": now - 400, "detail": DETAIL},
        {"id": TID, "text": LONG_TEXT, "createdT": now - 300, "detail": LINKED_DETAIL, "file": FILE, "link": LINK},
        {"id": TID_EIGHT, "text": "Which layout should the quarterly report use?", "createdT": now - 200, "detail": DETAIL8},
    ]}


def _launch_failure(stderr):
    """The driver's own line for a browser that did not launch (`browser-launch-failed: ...`), else the first non-empty
    line of its stderr: playwright's box-drawn install hint follows the line, and a tail of it read as blanks and bars."""
    lines = [ln.strip() for ln in stderr.splitlines() if ln.strip()]
    for ln in lines:
        if ln.startswith("browser-launch-failed:"):
            return ln[:300]
    return lines[0][:300] if lines else "(no stderr)"


class ReplySheetServed(unittest.TestCase):
    """One lab kernel for every leg (setUpClass); each leg is one driver run in one engine against one pane."""
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.kernel, cls.lab = None, None
        try:
            cls._boot()
        except BaseException:
            cls.tearDownClass()
            raise

    @classmethod
    def _boot(cls):
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            raise unittest.SkipTest("extension deps absent (npm ci not run here): the served leg needs them")
        cls.lab = tempfile.mkdtemp(prefix="reply-sheet-")
        dist = os.path.join(cls.lab, "dist")
        lab_dist.copy_dist(dist)   # the checkout's ONE build of the bundles, copied under its lock (tests/lab_dist.py)
        cls.state, claude = _ret._seed(cls.lab)
        now = int(time.time())
        Path(cls.state, "user-todos.json").write_text(json.dumps(_todo_store(now)))
        Path(cls.state, "user-todos-enabled.json").write_text(json.dumps({"enabled": True, "gt": now * 1000}))   # the switch, on
        cls.port, cls.token = _free_port(), "testtok-replysheet"
        cls.env = _lab.kernel_env(cls.lab, claude, dist, cls.port, cls.token, ROMP_HOST_NAME=HOST)
        cls.klog = os.path.join(cls.lab, "kernel.log")
        cls.kernel = subprocess.Popen([os.path.join(BIN, "romp-kernel")], stdout=open(cls.klog, "w"),
                                      stderr=subprocess.STDOUT, env=cls.env)
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
        if cls.kernel:
            try:
                os.kill(cls.kernel.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            cls.kernel.wait()
        if cls.lab:
            shutil.rmtree(cls.lab, ignore_errors=True)

    def _drive(self, engine, pane):
        declared = os.environ.get("ROMP_SERVED_TESTS_ENGINES", "")
        if engine != "chromium" and declared and engine not in [e.strip() for e in declared.split(",")]:
            self.skipTest("optional: this runner declares no %s (ROMP_SERVED_TESTS_ENGINES=%s)" % (engine, declared))
        url = "http://127.0.0.1:%d/%s?token=%s" % (self.port, "waiting" if pane == "waiting" else "chat", self.token)
        cfg = {"engine": engine, "pane": pane, "url": url, "healthz": "http://127.0.0.1:%d/healthz" % self.port,
               "sid": SID, "tid": TID, "tid2": TID_OTHER, "tid3": TID_EIGHT, "belowBoundary": BELOW_BOUNDARY[engine],
               "bootTimeoutMs": 30000}
        cfg_path = os.path.join(self.lab, "cfg-%s-%s.json" % (pane, engine))
        Path(cfg_path).write_text(json.dumps(cfg))
        try:
            p = subprocess.run(["node", DRIVER], capture_output=True, text=True, timeout=180,
                               env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg_path))
        except subprocess.TimeoutExpired as e:
            so = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode()
            self.fail("driver timed out; partial output:\n%s" % so[-3000:])
        if p.returncode == 3:
            if engine == "chromium":
                self.skipTest("no playwright chromium on this box: the served leg needs one (CI installs it)")
            self.skipTest("optional: no playwright %s on this machine: %s" % (engine, _launch_failure(p.stderr)))
        self.assertEqual(p.returncode, 0, "driver failed:\n" + p.stdout[-3000:] + p.stderr[-3000:] + "\nkernel:\n" + Path(self.klog).read_text()[-1500:])
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
        self.assertIsNotNone(line, "driver printed no result:\n" + p.stdout[-3000:] + p.stderr[-3000:])
        r = json.loads(line[len("RESULT:"):])
        self.assertNotIn("died", r, "driver aborted early: %r; hidden by: %r (kernel log tail: %s)" % (r.get("died"), r.get("hiddenBy"), Path(self.klog).read_text()[-800:]))
        self.assertTrue(r.get("ready"), "the sheet never opened in the served page: %r" % (r,))
        self.assertEqual(r.get("errors"), [], "page errors")
        return r

    @staticmethod
    def _inside_clip(m, b):
        return m[b]["top"] >= m["box"]["top"] - 0.5 and m[b]["bottom"] <= m["box"]["bottom"] + 0.5

    def _leg(self, engine, pane):
        r = self._drive(engine, pane)
        where = "%s, %s: " % (engine, pane)
        o, t, s, a4, a4b, t4, t4b, tall = (r["opened"], r["typed"], r["short"], r["at420"], r["at420Bottom"], r["typed420"],
                                            r["typed420Bottom"], r["tall"])
        floor = lambda m: 2 * m["detailLineH"] - 1   # two of the detail's lines, less a pixel of rounding
        rec = json.dumps({"opened": o, "typed": t, "tapAt": r["tapAt"], "after": r["after"]})
        # THE COMPOSITION FIRST, its outcome before its geometry: at 508 with the answer at the room, the tap put ONE
        # userTodoAnswer frame for the todo on the page's socket, and the sheet closed by that send. On the round-1 tree
        # the tap point lay outside the frame in both panes and nothing was sent: this driver fills at 900 and returns to
        # 508, and with no re-fit the box kept its 900 height, so Send laid out below the 508 frame; the node legs, which
        # type at 508, are where the chat's tap found the backdrop
        self.assertEqual(r["sentBefore"], 0, where + "nothing was sent before the tap: " + rec)
        self.assertEqual(len(r["after"]["sent"]), 1, where + "the tap SENT the answer (one userTodoAnswer frame for the todo on the socket); on the round-1 tree the tap fell on the backdrop or outside the frame and sent nothing: " + rec)
        self.assertIn('"type": "userTodoAnswer"', r["after"]["sent"][0].replace('"type":"', '"type": "'), where + "the frame's type: " + rec)
        self.assertFalse(r["after"]["overlayUp"], where + "the sheet closed by the send: " + rec)
        self.assertTrue(r["tapInFrame"], where + "the tap point is inside the frame: " + rec)
        # the geometry that explains it: the buttons inside the box's clip and the frame, a finger at Send reaches Send, the
        # detail keeps its floor, the answer took the room and no more
        for b in ("send", "cancel"):
            self.assertTrue(self._inside_clip(t, b), where + "typed: %s is inside the box's clip (on the round-1 tree the box grown to 40%% of the window laid it out below): %s" % (b, rec))
        self.assertTrue(t["box"]["top"] >= -0.5 and t["box"]["bottom"] <= t["frameH"] + 0.5, where + "typed: the box is inside the frame: " + rec)
        self.assertEqual(t["hitAtSend"], "target", where + "typed: a finger at Send's painted centre reaches Send, not the backdrop: " + rec)
        self.assertEqual(t["hitAtCancel"], "target", where + "typed: and Cancel: " + rec)
        self.assertGreaterEqual(t["detailH"], floor(t), where + "typed: the detail keeps its two-line floor in the deficit state (0px on the round-1 tree): " + rec)
        self.assertGreaterEqual(t["inputH"], t["floorH"] - 1, where + "typed: three rows at least: " + rec)
        self.assertLessEqual(t["boxScrollH"], t["boxClientH"] + 1, where + "typed: the answer took the room and no more, nothing is a scroll away: " + rec)
        # the room, not a share of the window: with the chips and the wrapped ask the box is nearly full at open (in the
        # pane, where the chips are flex rows, the room is a few pixels), so fourteen lines grow the answer box by exactly
        # what the box has left and the rest of the answer is a scroll INSIDE the box, never a row past the clip
        self.assertGreaterEqual(t["inputH"], o["inputH"] - 1, where + "typed: the box never shrinks under typing: " + rec)
        self.assertGreater(t["inputScrollH"], t["inputH"] + 8, where + "typed: fourteen lines exceed the room, so the answer scrolls inside its box (the text is a scroll away, not lost): " + rec)
        # the resize re-fit (kbFit re-runs grow): typed at 900 the box grew well past the floor; shrunk to 508 it re-fitted
        # to the room, under the height it had, never under three rows
        self.assertFalse(tall["tight"], where + "900px: no fold: %r" % (tall,))
        self.assertGreater(tall["inputH"], tall["floorH"] + 60, where + "900px, fourteen lines: the answer box grew well past the floor: %r" % (tall,))
        self.assertLess(t["inputH"], tall["inputH"], where + "900 then 508: the window's shrink re-fitted the answer box (grow ran on the resize): %d at 900, %d at 508: %s" % (tall["inputH"], t["inputH"], rec))
        # the detail's cap at rest (the maintainer's ruling at the merge with main): with the keyboard down it is the larger of
        # 12em and 34.8% of the window's height, here the viewport term (313.2px at 900, 375.8px at 1080 and 254.7px at the
        # installed app's 732, against 12em's 134px), read on the composition's todo with its answer box cleared. The share
        # holds this todo's room at 732 (the maintainer's ruling on the share): the detail is laid out at its cap, not at the
        # room, which in the pane, under two chip rows, is 4.4px over the cap there
        em12 = lambda m: 12 * m["detailFontPx"]
        room_bound = ("up to 0.354 at 732, the ruled bound" if pane == "waiting"
                      else "up to about 0.42 at 732; the ruled bound, 0.354, is the pane sheet's")
        for label, m in (("at rest at 900", r["restTall"]), ("at rest at 1080", r["restTaller"]), ("at rest at 732", r["restApp"])):
            with self.subTest(window=label):   # each window its own red or green
                term = REST_SHARE * m["frameH"]
                self.assertFalse(m["tight"], where + label + ": no fold: %r" % (m,))
                self.assertGreater(term, em12(m) + 20, where + label + ": 34.8%% of the window (%.1fpx) is the larger term against 12em (%.1fpx): %r" % (term, em12(m), m))
                self.assertAlmostEqual(m["detailMaxH"], term, delta=0.5, msg=where + label + ": the cap is 34.8%% of the window's height, %.1fpx (the head's cap was 12em at every height, %.1fpx): %r" % (term, em12(m), m))
                self.assertGreaterEqual(m["detailRectH"], m["detailMaxH"] - 0.5, where + label + ": the detail is laid out at its cap (%.2fpx under a %.2fpx cap): the room is the smaller, so the share is past what this todo's room holds here (this sheet's room holds a share %s): %r" % (m["detailRectH"], m["detailMaxH"], room_bound, m))
                self.assertAlmostEqual(m["detailH"], term, delta=1.5, msg=where + label + ": the long detail shows at the cap, %.1fpx: %r" % (term, m))
                self.assertGreaterEqual(m["inputH"], m["floorH"] - 1, where + label + ": three rows: %r" % (m,))
                self.assertLessEqual(m["boxScrollH"], m["boxClientH"] + 1, where + label + ": the sheet fits with the detail at its cap, nothing is a scroll away: %r" % (m,))
                for b in ("send", "cancel"):
                    self.assertTrue(self._inside_clip(m, b), where + label + ": %s is inside the box's clip: %r" % (b, m))
                self.assertEqual(m["hitAtSend"], "target", where + label + ": a finger at Send's painted centre reaches Send: %r" % (m,))
        # Safari's panes, 709 (the toolbars collapsed), 633 (the common one) and 620: the cap is still the viewport term, but in
        # the pane this todo's room is under it (the chips and the wrapped ask leave 147 to 236px), so the shrink sets the
        # detail's height under the cap and over its floor; the sheet fits all the same (no share both shows the recorded 8-line
        # detail in full at 633 and holds this room at 732: styles.css)
        for h, key in ((709, "restSafariTop"), (633, "restSafari"), (620, "restSafari16e")):
            m = r[key]
            label = "at rest at %d" % h
            with self.subTest(window=label):
                term = REST_SHARE * m["frameH"]
                self.assertEqual(m["frameH"], h, where + label + ": %r" % (m,))
                self.assertFalse(m["tight"], where + label + ": no fold: %r" % (m,))
                self.assertGreater(term, em12(m) + 20, where + label + ": 34.8%% of the window (%.1fpx) is the larger term against 12em (%.1fpx): %r" % (term, em12(m), m))
                self.assertAlmostEqual(m["detailMaxH"], term, delta=0.5, msg=where + label + ": the cap is 34.8%% of the window's height, %.1fpx: %r" % (term, m))
                self.assertLessEqual(m["detailH"], m["detailMaxH"] + 1.5, where + label + ": the detail is under its cap: %r" % (m,))
                self.assertGreaterEqual(m["detailH"], floor(m), where + label + ": and over its floor of two lines: %r" % (m,))
                self.assertGreaterEqual(m["inputH"], m["floorH"] - 1, where + label + ": three rows: %r" % (m,))
                self.assertLessEqual(m["boxScrollH"], m["boxClientH"] + 1, where + label + ": the sheet fits, nothing is a scroll away: %r" % (m,))
                for b in ("send", "cancel"):
                    self.assertTrue(self._inside_clip(m, b), where + label + ": %s is inside the box's clip: %r" % (b, m))
                self.assertEqual(m["hitAtSend"], "target", where + label + ": a finger at Send's painted centre reaches Send: %r" % (m,))
        # the stated boundary on the third todo, the recorded 8-line detail (styles.css: in full from a 720px pane, 717 in
        # WebKit, 718 in Firefox): in full at the app's 732 and at 720; not in full one pixel under this engine's own boundary and
        # at Safari's common 633, where it shows the cap (about 220 of its 251px) and scrolls the rest. Read whole first, so a
        # share that moves the boundary is named as that
        e = r.get("eight", {"error": "the boundary step did not run"})
        with self.subTest(window="the 8-line detail at the stated boundary"):
            self.assertNotIn("error", e, where + "the boundary step ran to its end: %r" % (e,))
            below = BELOW_BOUNDARY[engine]
            for label, m, h in (("at rest at 732", e["app"], 732), ("at rest at the boundary, 720", e["boundary"], BOUNDARY)):
                self.assertEqual(m["frameH"], h, where + label + ": %r" % (m,))
                self.assertGreater(m["detailScrollH"], em12(m) + 60, where + label + ": the 8-line detail is longer than 12em: %r" % (m,))
                self.assertGreaterEqual(m["detailH"], m["detailScrollH"], where + label + ": the recorded 8-line detail shows in full, %s of %spx under a %.2fpx cap (the stated boundary is 720px): %r" % (m["detailH"], m["detailScrollH"], m["detailMaxH"], m))
                self.assertGreaterEqual(m["inputH"], m["floorH"] - 1, where + label + ": three rows: %r" % (m,))
                self.assertLessEqual(m["boxScrollH"], m["boxClientH"] + 1, where + label + ": the sheet fits: %r" % (m,))
                self.assertEqual(m["hitAtSend"], "target", where + label + ": a finger at Send's painted centre reaches Send: %r" % (m,))
            for label, m, h in (("at rest one pixel under this engine's boundary, %d" % below, e["below"], below), ("at rest at 633", e["safari"], 633)):
                term = REST_SHARE * m["frameH"]
                self.assertEqual(m["frameH"], h, where + label + ": %r" % (m,))
                self.assertLess(m["detailH"], m["detailScrollH"], where + label + ": not in full, %s of %spx under a %.2fpx cap: the pane is under the stated boundary (in full from 720px, %d in this engine); in full here, the share moved the boundary that styles.css and the ledger entry state: %r" % (m["detailH"], m["detailScrollH"], m["detailMaxH"], below + 1, m))
                self.assertAlmostEqual(m["detailH"], term, delta=1.5, msg=where + label + ": it shows at the cap, %.1fpx: %r" % (term, m))
                self.assertGreaterEqual(m["inputH"], m["floorH"] - 1, where + label + ": three rows: %r" % (m,))
                self.assertLessEqual(m["boxScrollH"], m["boxClientH"] + 1, where + label + ": the sheet fits: %r" % (m,))
                self.assertEqual(m["hitAtSend"], "target", where + label + ": a finger at Send's painted centre reaches Send: %r" % (m,))
        # the tree each builder emits, and the elements the fix's rules key on: the pane's chips are flex children of the
        # box (waiting.ts showReply), the chat's sit inside the quoted line (render.ts showUserTodoReply); the shared
        # skeleton is the title, the quoted line, the detail, the answer box and the buttons, in that order
        if pane == "waiting":
            self.assertEqual(o["kinds"], ["confirm-title", "confirm-detail", "wt-file", "wt-link", "ut-detail", "ut-reply-input", "confirm-actions"], where + "the pane's tree")
            self.assertEqual(o["quoteChips"], [], where + "the pane's chips are not inside the quoted line")
        else:
            self.assertEqual(o["kinds"], ["confirm-title", "confirm-detail", "ut-detail", "ut-reply-input", "confirm-actions"], where + "the chat's tree")
            self.assertEqual(o["quoteChips"], ["ut-file", "ut-link"], where + "the chat's chips trail the quoted line, the file's first")
        self.assertEqual([k for k in o["kinds"] if not k.startswith("wt-")], ["confirm-title", "confirm-detail", "ut-detail", "ut-reply-input", "confirm-actions"],
                         where + "the skeleton the CSS keys on is the same in both panes")
        self.assertTrue(o["inputSel"] and o["detailSel"] and o["boxSel"], where + "the three scoped selectors each reach their element: %r" % (o,))
        # opened at 508: no fold, three rows, the detail a scroll container over its cap, the box scrolling at this height
        # too, the unbreakable token wrapped so the detail's scrollWidth is no wider than its border box
        self.assertEqual(o["frameH"], 508, where + "the pane's window is the phone's visible height with the keyboard up")
        self.assertFalse(o["tight"], where + "508px is above the fold's threshold")
        self.assertGreater(o["floorH"], 30, where + "the three-row probe laid out: %r" % (o,))
        self.assertGreaterEqual(o["inputH"], o["floorH"] - 1, where + "the answer box holds three rows: %r" % (o,))
        self.assertEqual(o["detailOverflowY"], "auto", where + "the detail scrolls within itself")
        self.assertGreater(o["detailScrollH"], o["detailH"] + 8, where + "the forty-line detail overflows its cap: %r" % (o,))
        self.assertEqual(o["boxOverflowY"], "auto", where + "the box scrolls at every height (#ut-reply-prompt .picker-box), not only under the fold")
        self.assertLessEqual(o["detailScrollW"], o["detailOffsetW"], where + "no sideways scroller: the unbreakable token wraps inside the detail (overflow-wrap: anywhere), so its content is no wider than its box (scrollWidth %s against offsetWidth %s; without the wrap the token ran hundreds of pixels past it): %r" % (o["detailScrollW"], o["detailOffsetW"], o))
        self.assertEqual(o["detailOverflowX"], "hidden", where + "overflow-x: hidden, #pinned-notes's companion declaration")
        # the short window (300px, the fold on): the frame rule, the floor, the scroll, the address under a finger, Send at
        # the box's bottom
        self.assertTrue(s["tight"], where + "300px folds: %r" % (s,))
        self.assertEqual(s["alignItems"], "flex-start", where + "300px: folded, the sheet sits at the top rather than centering into the keyboard (#ut-reply-prompt.kb-tight): %r" % (s,))
        self.assertEqual(s["paddingTop"], "12px", where + "300px: under the picker's 12px frame: %r" % (s,))
        self.assertGreaterEqual(s["detailH"], floor(s), where + "300px: the detail keeps two lines (the floor); it resolved to 0px before: %r" % (s,))
        self.assertTrue(s["detailScrolls"], where + "300px: the detail scrolls within itself: %r" % (s,))
        self.assertEqual(s["linkHit"], "target", where + "300px: the address on the detail's first line is under a finger: %r" % (s,))
        self.assertTrue(s["boxScrollH"] > s["boxClientH"] + 1 and s["boxScrollTop"] > 0, where + "300px: the box scrolls to the rest: %r" % (s,))
        self.assertTrue(s["sendInBoxAtBottom"] and s["sendHitAtBottom"] == "target", where + "300px: at the box's bottom Send is inside the clip and under a finger: %r" % (s,))
        # 420px with the chip todo, at open and with fourteen lines: the pane's two chip rows put the floors alone a few
        # pixels past the fold's cap (the backstop state: the box scrolls the difference, Send's centre under a finger at
        # open, Send inside the clip once the box is scrolled to its bottom); the chat's column fits (the fitted state)
        for label, m, mb in (("420px, at open", a4, a4b), ("420px, fourteen lines", t4, t4b)):
            self.assertTrue(m["tight"], where + label + ": under the fold: %r" % (m,))
            self.assertGreaterEqual(m["detailH"], floor(m), where + label + ": the detail keeps its floor: %r" % (m,))
            self.assertGreaterEqual(m["inputH"], m["floorH"] - 1, where + label + ": three rows at least: %r" % (m,))
            self.assertTrue(m["box"]["top"] >= -0.5 and m["box"]["bottom"] <= m["frameH"] + 0.5, where + label + ": the box is inside the frame: %r" % (m,))
            self.assertEqual(m["hitAtSend"], "target", where + label + ": Send's centre is under a finger: %r" % (m,))
            if pane == "waiting":
                self.assertTrue(m["boxClientH"] + 1 < m["boxScrollH"] < m["boxClientH"] + 40,
                                where + label + ": the pane's floors alone overflow the fold's cap by a few pixels (%d of %dpx; two chip rows the chat's column does not have) and the box scrolls the difference; a chrome change that makes the pane fit here, or overflow by more, changes what the PR body says of this window: %r" % (m["boxScrollH"], m["boxClientH"], m))
                self.assertTrue(mb["sendInBoxAtBottom"] and mb["sendHitAtBottom"] == "target", where + label + ": scrolled to the box's bottom, Send is inside the clip and under a finger: %r" % (mb,))
            else:
                self.assertLessEqual(m["boxScrollH"], m["boxClientH"] + 1, where + label + ": the chat's column fits the fold's cap, nothing is a scroll away: %r" % (m,))
                for b in ("send", "cancel"):
                    self.assertTrue(self._inside_clip(m, b), where + label + ": %s is inside the box's clip: %r" % (b, m))
        # the drag guard, on the other todo's sheet: an inline height written as the grip writes it stands through a
        # keystroke (before the guard every keystroke snapped a dragged box back to its content's height)
        d = r["drag"]
        self.assertNotIn("skipped", d, where + "the drag step ran (the composition's sheet had closed by the send): %r" % (d,))
        self.assertNotIn("error", d, where + "the drag step ran to its end: %r" % (d,))
        self.assertEqual(d["draggedStyleH"], "150px", where + "the inline height was written: %r" % (d,))
        self.assertGreater(d["draggedH"], d["openH"] + 30, where + "the written height laid out taller than the floor: %r" % (d,))
        self.assertEqual(d["afterKeyStyleH"], "150px", where + "one keystroke after the drag: the inline height the person set stands, grow stood down (before the guard it snapped back to the content's height): %r" % (d,))
        self.assertGreaterEqual(d["afterKeyH"], d["draggedH"] - 1, where + "and the box keeps the dragged height: %r" % (d,))
        # the detail's cap under the keyboard, on that sheet at open at 508 (a short ask, no chips, the forty-line detail, so the
        # room would hold more than 12em): 12em, as before; no viewport term enters with the keyboard up
        k = r["kbCap"]
        self.assertEqual(k["frameH"], 508, where + "the keyboard up at 508: %r" % (k,))
        self.assertFalse(k["tight"], where + "508px: no fold: %r" % (k,))
        self.assertAlmostEqual(k["detailMaxH"], em12(k), delta=0.5, msg=where + "the keyboard up at 508: the cap is 12em, %.1fpx, no viewport term (34.8%% of 508 would be %.1fpx): %r" % (em12(k), REST_SHARE * 508, k))
        self.assertAlmostEqual(k["detailH"], em12(k), delta=1.5, msg=where + "the keyboard up at 508: the forty-line detail shows 12em, its height before the change; a cap that let the viewport term in would show it taller here: %r" % (k,))
        # the dragged height is a PREFERENCE clamped to the room (the author's pass after the maintainer's round 1,
        # composition-3): written to 215px as the grip leaves it, on this todo's sheet it stands at 508 (the room holds it); the
        # frame at 420 clamps it to the room the box has, not to the content's height, the box fitting its cap and Send inside
        # the clip under a finger; back at 508 the box returns to the 215px the person set, not stuck at the clamp. Before, the
        # dragged height stood through the resize and the box overflowed its cap
        p = r.get("pref", {"error": "the preference step did not run"})
        self.assertNotIn("error", p, where + "the preference step ran to its end: %r" % (p,))
        self.assertEqual(p["set"]["inputStyleH"], "215px", where + "508px: the dragged 215px stands, the room holds it: %r" % (p["set"],))
        c = p["clamped"]
        self.assertTrue(c["tight"], where + "420px after the drag: under the fold: %r" % (c,))
        self.assertLess(c["inputH"], p["set"]["inputH"] - 8, where + "420px after the drag: the box is clamped to the room (%d against the %d the drag laid out); before the clamp the dragged height stood through the resize and the box overflowed its cap: %r" % (c["inputH"], p["set"]["inputH"], c))
        self.assertGreater(c["inputH"], c["floorH"] + 20, where + "420px after the drag: clamped to the room, not reset to the content's height (%d against the %d floor): %r" % (c["inputH"], c["floorH"], c))
        self.assertLessEqual(c["boxScrollH"], c["boxClientH"] + 1, where + "420px after the drag: the clamp gave the box's overflow back exactly, nothing is a scroll away: %r" % (c,))
        for b in ("send", "cancel"):
            self.assertTrue(self._inside_clip(c, b), where + "420px after the drag: %s is inside the box's clip: %r" % (b, c))
        self.assertEqual(c["hitAtSend"], "target", where + "420px after the drag: a finger at Send's painted centre reaches Send: %r" % (c,))
        self.assertEqual(p["back"]["inputStyleH"], "215px", where + "back at 508: the box returns to the height the person set, not stuck at the clamp: %r" % (p["back"],))
        # a click whose press began inside the sheet is not a backdrop tap (the author's pass after the maintainer's round 1,
        # composition-2, and the reviewer's ruling on the selection: a backdrop tap is press and release both on the backdrop):
        # after a grip drag released over the backdrop, and after a text selection dragged from inside the box onto it, the
        # sheet stands with its text in every engine (Chromium and WebKit dispatch the click to the overlay, the common ancestor
        # of the press and the release; Firefox to the textarea), and a plain tap on the backdrop still dismisses (what a
        # dismiss does with the text is the filed discard item's, untouched)
        rel = r.get("release", {"error": "the release step did not run"})
        self.assertNotIn("error", rel, where + "the release step ran to its end: %r" % (rel,))
        self.assertTrue(rel["overlayUp"], where + "a grip drag released over the backdrop (%s; the clicks' targets %r) is not a backdrop tap: the sheet stands; before the guard Chromium and WebKit closed it with the answer: %r" % (rel["road"], rel["clicks"], rel))
        self.assertEqual(rel["value"], "a", where + "the answer is intact through the release: %r" % (rel,))
        sel = r.get("selectRelease", {"error": "the selection step did not run"})
        self.assertNotIn("error", sel, where + "the selection step ran to its end: %r" % (sel,))
        self.assertTrue(sel["overlayUp"], where + "a text selection dragged from inside the box onto the backdrop (the clicks' targets %r) is not a backdrop tap either: the sheet stands; before the widened predicate Chromium and WebKit closed it with the answer, the same common-ancestor click with the box's height unchanged: %r" % (sel["clicks"], sel))
        self.assertEqual(sel["value"], "a", where + "the answer is intact through the selection's release: %r" % (sel,))
        self.assertFalse(r["backdropTap"]["overlayUp"], where + "a plain tap on the backdrop still dismisses: %r" % (r["backdropTap"],))

    def test_waiting_chromium(self):
        self._leg("chromium", "waiting")

    def test_chat_chromium(self):
        self._leg("chromium", "chat")

    def test_waiting_firefox(self):
        self._leg("firefox", "waiting")

    def test_chat_firefox(self):
        self._leg("firefox", "chat")

    def test_waiting_webkit(self):
        self._leg("webkit", "waiting")

    def test_chat_webkit(self):
        self._leg("webkit", "chat")


if __name__ == "__main__":
    unittest.main()
