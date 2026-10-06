#!/usr/bin/env python3
"""The pane registry (plans/panes-as-data.md, phase one). A pane is a record in ONE schema: the shipped panes are the
kernel's code constants (_CODE_PANES, checked at import by _pane_check like the code boards), every other pane a JSON document
under STATE/panes/<id>.json behind define_pane (the board door's twin: POST /pane, GET /panes, `romp pane`). The shell renders
the shipped panes, and the FIRST pin is that their RENDERING is unchanged from the base kernel's, whatever the registry holds:
the body tag, the rail, the phone tabs, the pane row, the column and gutter rules and the gutter calls, slice for slice
(tests/fixtures/landing-code-panes.json, tests/landing_slices.py). The panes defined at the kernel are built by the shell in
the browser from GET /panes, the records `romp pane list` reads (one source for the pane records): each gets a rail button, a
phone tab (none when experimental), a lazy iframe (data-src), its column and gutter rules, and joins every inline consumer and
bundle; a URL source is a plain sandboxed iframe whose address is the URL as given (nothing appended) and which names no
protocol, and every shell listener, inline and bundled, drops a message that is not a protocol pane's own (the source
check, fail-closed). The pane set's revision rides every keepalive beside the build token, and a page whose revision
(the one it read from GET /panes) differs is offered a reload.

Every test here reds at the base on BEHAVIOUR (the 1919 read): a pane's file is written by hand the way the door writes it,
and what is asserted is the landing, the routes, the keepalive frame and the executed scripts, never a name.
Synthetic fixtures only (the notes-api demo world; TESTHOST)."""
import ast
import contextlib
import html as html_mod
import inspect
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
EXT = os.path.join(ROOT, "vscode-extension")
sys.path.insert(0, HERE)
import landing_slices   # noqa: E402  the slicer the fixture was made with; slices() below is its copy, held to it by TheCodePanesRender
import pane_records_stub   # noqa: E402  the shell's GET /panes road over a stub page (the head read's state, the builder's DOM calls)

os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
_XDG = tempfile.mkdtemp()
os.environ["XDG_STATE_HOME"] = _XDG
os.environ.pop("ROMP_STATE_DIR", None)
os.makedirs(os.path.join(_XDG, "romp"), exist_ok=True)
open(os.path.join(_XDG, "romp", "session-hosts"), "w").write("off\n")
km = load_source("romp_kernel_pane_registry", os.path.join(BIN, "romp-kernel"))
KSRC = open(os.path.join(BIN, "romp-kernel")).read()
FIXTURE = json.load(open(os.path.join(HERE, "fixtures", "landing-code-panes.json")))

SHIPPED = [("chat", "Chat", True), ("timeline", "Sessions", True), ("fleet", "Outline", False), ("feed", "Feed", True),
           ("waiting", "Waiting", False),   # the fork's Waiting on you pane, a shipped record between the Feed and the Files pane (fold 4, slice 2)
           ("files", "Files", False), ("artifacts", "Artifacts", False)]   # id, title, today's rail default (the Artifacts pane since 2026-09-19)
EXPERIMENTAL = {"artifacts"}   # the shipped records the gear asks for before showing (plans/panes-as-data.md phase three: the Artifacts pane)
ARTIFACTS_ROW = {"id": "artifacts", "title": "Artifacts", "protocol": "romp", "experimental": True, "on": False, "builtin": True}   # the generic build's row for the shipped record
SHIPPED_IDS = [s[0] for s in SHIPPED]
NOTES = {"id": "notes", "title": "Notes", "source": "pane:notes", "on": True}
DOCS = {"id": "docs", "title": "Docs", "source": "http://TESTHOST:9/docs/", "on": True}          # a URL: protocol none
LAB = {"id": "lab", "title": "Lab", "source": "/feed", "experimental": True}                       # a kernel route, experimental
OFFPANE = {"id": "offpane", "title": "Off", "source": "/feed", "on": False}                        # a kernel route, off by rail default, not experimental
GUARD = "if(!window.__rompPaneSourceOk||!window.__rompPaneSourceOk(e))return;"                    # the inline listeners' read, fail-closed


def _full(d):
    """The record as the door fills it."""
    out = {"title": d["id"].capitalize(), "on": False, "experimental": False,
           "protocol": "none" if d["source"].startswith("http") else "romp"}
    out.update(d)
    return out


class World:
    """A hermetic state root, the kernel rebound to it, the pane memo cleared; pane files written by hand, as the door writes
    them, so every assertion is on what the kernel RENDERS from the directory."""
    def __init__(self):
        self.td = tempfile.TemporaryDirectory()
        root = Path(self.td.name)
        self.orig_state = km.jd.STATE
        km.jd._rebind_state(root / "state")
        (km.jd.STATE / "session-hosts").parent.mkdir(parents=True, exist_ok=True)
        (km.jd.STATE / "session-hosts").write_text("off\n")
        self.reset_memos()

    @property
    def pdir(self):
        return km.jd.STATE / "panes"

    def seed(self, *defs):
        self.pdir.mkdir(parents=True, exist_ok=True)
        for d in defs:
            (self.pdir / (d["id"] + ".json")).write_text(json.dumps(_full(d), indent=1, sort_keys=True) + "\n")

    def unseed(self, *ids):
        for i in ids:
            (self.pdir / (i + ".json")).unlink()

    @staticmethod
    def reset_memos():
        # guarded: at a base without the registry these names are absent, and each test reds on its own behaviour
        memo = getattr(km, "_PANES_MEMO", None)
        if isinstance(memo, dict):
            memo["slot"] = None
        getattr(km, "_PANES_BAD", set()).clear()

    def close(self):
        km.jd._rebind_state(self.orig_state)
        self.reset_memos()
        self.td.cleanup()


def _run(js):
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(js)
        path = f.name
    try:
        r = subprocess.run(["node", path], capture_output=True, text=True, timeout=30)
    finally:
        os.unlink(path)
    assert r.returncode == 0, "the shell script threw: " + r.stderr[:1500]
    return json.loads(r.stdout.strip().splitlines()[-1])


def _has(tc, needle, page, msg=""):
    # assertTrue, not assertIn: a failure must never print the landing
    tc.assertTrue(needle in page, "missing from the page: %r %s" % (needle, msg))


def _lacks(tc, needle, page, msg=""):
    tc.assertTrue(needle not in page, "present in the page: %r %s" % (needle, msg))


def _at(page, needle):
    # page.index(needle) for a marker only a render with data panes carries: the served-pins census judges a literal position pin
    # over the landing against the hermetic render, which has no data pane, so such a pin reads through this helper as _has does
    # (a missing marker still raises)
    return page.index(needle)


def slices(html):
    """tests/landing_slices.py's slices(), the slicer the fixture was made with, copied here: the served-pins census
    (tests/test_served_pins_read_elements.py) follows a function this module defines one level and reads what it reads of the
    landing, while a landing handed to an imported helper is a read it cannot classify. Every statement but this docstring is the
    slicer's own, held to it by TheCodePanesRender's copy test. {name: text}; a slice that cannot be found is the empty string,
    so a comparison against the fixture fails on the slice by name."""
    body = re.search(r"<body class='[^']*'[^>]*>", html)
    row_a, row_b = html.find("<div class=row>"), html.find("<div id=gv-ghost>")
    return {
        "body_tag": body.group(0) if body else "",
        "rail_buttons": "".join(re.findall(r"<div class=rail-btn data-pane=[^>]*>[^<]*</div>", html)),
        "phone_tabs": "".join(re.findall(r"<button data-pane=[^>]*>[^<]*</button>", html)),
        "pane_row": html[row_a:row_b] if 0 <= row_a < row_b else "",
        "column_css": "".join(r for css in re.findall(r"<style>(.*?)</style>", html, re.S)
                              for r in re.findall(r"(?<=[};])[^{};]*(?:-pane\b|#gv-|\.m-on)[^{}]*\{[^}]*\}", css)),   # -pane\b: never -panel (the 1919 read: four unrelated panels' rules rode in the panes' slice)   # the STYLE blocks only: the inline scripts name panes too; .m-on: the phone's shown-frame rules (the 1922 read: #f-artifacts.m-on fell outside the slice)
        "gutter_calls": "\n".join(re.findall(r"gutter\('gv-[a-z]',[^\n]*", html)),
    }


def _RECORDS_JS():
    # the shell's builder of the panes defined at the kernel (kernel.py _LANDING_PANE_RECORDS_JS), read with a default so a kernel without
    # it (the base) reds on BEHAVIOUR in the executed harnesses (nothing built, nothing joined), never on a missing name
    return getattr(km, "_LANDING_PANE_RECORDS_JS", "")


def _ADOPT_JS():
    # the landing's adoption of the read's revision into its reload core (kernel.py _PANES_ADOPT_JS), defaulted the same way
    return getattr(km, "_PANES_ADOPT_JS", "")


def _attr_rows(page):
    m = re.search(r"<body class='po-chat po-feed po-timeline' data-panes=\"([^\"]*)\">", page)
    return json.loads(html_mod.unescape(m.group(1))) if m else None


def _rail(page):
    return re.findall(r"<div class=rail-btn data-pane=([a-z0-9_-]+)>([^<]*)</div>", page)


# ── the first pin: the code panes render as before ───────────────────────────────────────────────────────────────
class TheCodePanesRender(unittest.TestCase):
    def setUp(self): self.w = World()
    def tearDown(self): self.w.close()

    def test_00_the_code_panes_rendering_is_unchanged_with_an_empty_registry_and_after_a_define_and_remove(self):
        # THE FIRST PIN (plans/panes-as-data.md, section 7): with no data pane the kernel renders the code panes as the base
        # kernel did, slice for slice (the fixture names the base); the page as a whole gains the guards and the attribute
        # reads, deliberately. A pane file written by hand changes the page; removing it brings the bytes back exactly.
        h0 = km._landing()
        self.assertTrue(h0 == km._landing(), "the landing is a pure function of the registry and the build")
        got = slices(h0)
        for name, text in FIXTURE["slices"].items():
            self.assertTrue(got.get(name) == text, "the %s slice differs from the base rendering (fixture from %s): %d vs %d chars"
                            % (name, FIXTURE["made_from"], len(got.get(name, "")), len(text)))
        # with no data pane the attribute carries exactly the shipped record the generic build renders (the Artifacts pane), and
        # none of a data pane's markers
        self.assertEqual(_attr_rows(h0), [ARTIFACTS_ROW], "the attribute: the Artifacts record alone")
        _lacks(self, " data-protocol=none sandbox=", h0); _lacks(self, "id=gv-notes", h0); _lacks(self, 'data-src="/pane/', h0)
        # a pane file changes NO byte of the landing: the shell builds the panes defined at the kernel from GET /panes (the
        # client build is executed in TheLanding; every page the route table renders and every static file is held to
        # this by tests/test_pane_records_one_source.py)
        self.w.seed(NOTES)
        h1 = km._landing()
        self.assertTrue(h1 == h0, "a pane file changes no byte of the landing (%d vs %d chars)" % (len(h1), len(h0)))
        self.assertEqual(_attr_rows(h1), [ARTIFACTS_ROW], "the attribute still carries the Artifacts record alone")
        self.w.unseed("notes")
        self.assertTrue(km._landing() == h0, "define then remove: the bytes stay")

    def test_01_the_slicer_this_module_runs_is_the_one_the_fixture_was_made_with(self):
        # slices() above is tests/landing_slices.py's copy (its docstring says why): statement for statement the same function, the
        # docstrings apart, so the pin compares the rendering with the slicer that made its fixture
        def statements(fn):
            node = ast.parse(inspect.getsource(fn)).body[0]
            self.assertIsInstance(node.body[0].value, ast.Constant, "%s opens with its docstring" % fn.__module__)
            return [ast.dump(st) for st in node.body[1:]], [a.arg for a in node.args.args]
        mine, theirs = statements(slices), statements(landing_slices.slices)
        self.assertTrue(mine[0], "the copy has statements")
        self.assertEqual(mine, theirs, "slices() here differs from tests/landing_slices.py's: copy the slicer's change here (or the "
                                       "reverse) and regenerate the fixture if the slices changed")


# ── the doors ─────────────────────────────────────────────────────────────────────────────────────────────────────
class TheDoors(unittest.TestCase):
    """POST /pane, GET /panes and GET /pane/<id>/... in /board's shape; the schema is the door's, so it is pinned through it."""
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self): self.w = World()
    def tearDown(self): self.w.close()

    def _req(self, path, body=None, token=True):
        headers = {"Content-Type": "application/json"}
        if token:
            # the token this module's kernel bound at import (km.TOKEN), never the environment read now: every module's module-level
            # writes run at collection, before any test, and a later module that sets ROMP_SERVE_TOKEN outright (tests/test_waiting_pane.py
            # does) leaves the environment naming a token this kernel never loaded, so every request here was refused 403
            headers["X-Romp-Token"] = km.TOKEN
        data = None if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path), data=data, headers=headers, method="POST" if data is not None else "GET")
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, r.headers.get("Content-Type", ""), r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get("Content-Type", ""), e.read()

    def _call(self, path, body=None, token=True):
        st, _, raw = self._req(path, body, token)
        try:
            return st, json.loads(raw.decode() or "{}")
        except ValueError:
            return st, {"raw": raw.decode(errors="replace")}

    def test_the_shipped_panes_are_records_the_door_lists_and_the_rail_renders_from(self):
        st, r = self._call("/panes")
        self.assertEqual(st, 200, "GET /panes answers")
        rows = r["panes"]
        self.assertEqual([(p["id"], p["title"], p["on"]) for p in rows], SHIPPED, "the shipped panes, in the rail's order, with today's rail defaults as `on`")
        self.assertTrue(all(p["builtin"] and p["protocol"] == "romp" and p["experimental"] == (p["id"] in EXPERIMENTAL) and p["source"] == "/" + p["id"] for p in rows), rows)
        self.assertEqual(r["rev"], "0", "no data pane: the set's revision is zero")
        self.assertEqual(_rail(km._landing()), [(p["id"], p["title"]) for p in rows], "the rail renders the same records")

    def test_the_door_fills_the_defaults_and_refuses_by_member(self):
        st, r = self._call("/pane", {"id": "notes", "source": "/feed"})
        self.assertEqual(st, 200, "POST /pane answers")
        self.assertEqual(r, {"ok": True, "pane": {"id": "notes", "title": "Notes", "source": "/feed", "on": False, "experimental": False, "protocol": "romp"}, "rev": r.get("rev")})
        self.assertNotEqual(r["rev"], "0")
        st, r = self._call("/pane", dict(DOCS)); self.assertEqual(r["pane"]["protocol"], "none", "a URL source is a plain iframe: protocol none by default")
        st, r = self._call("/pane", {"id": "notes", "title": "  Notes  ", "source": "pane:notes", "on": True, "experimental": True, "protocol": "romp"})
        self.assertEqual((r["pane"]["title"], r["pane"]["on"], r["pane"]["experimental"]), ("Notes", True, True))
        for bad, word in (
                ({"id": "notes", "source": "/feed", "colour": "red"}, "unknown member colour"),
                ({"id": "Notes", "source": "/feed"}, "id must"),
                ({"id": "n" * 33, "source": "/feed"}, "id must"),
                ({"id": "feed", "source": "/feed"}, "reserved"),
                ({"id": "waiting", "source": "/feed"}, "reserved"),      # the fork's shipped Waiting pane: a data pane would render a second waiting-pane
                ({"id": "tl", "source": "/feed"}, "derives"),            # the band renders id=tl-pane: a data pane tl would render it twice (the 1920 read)
                ({"id": "ghost", "source": "/feed"}, "derives"),
                ({"id": "col", "source": "/feed"}, "derives"),           # the tab drag's rectangle is #col-ghost
                ({"id": "a", "source": "/feed"}, "derives"),             # the hand-written gutters are gv-a to gv-d
                ({"id": "chat-notes", "source": "/feed"}, "chat column"),   # f-chat-<n> is a chat column's frame shape
                ({"id": "settings", "source": "/feed"}, "reserved"),
                ({"id": "artifacts", "source": "/feed"}, "reserved"),
                ({"id": "notes", "title": "x" * 25, "source": "/feed"}, "title must"),
                ({"id": "notes", "title": "   ", "source": "/feed"}, "title must"),
                ({"id": "notes"}, "source must"),
                ({"id": "notes", "source": "feed"}, "source must"),
                ({"id": "notes", "source": "//TESTHOST/x"}, "source must"),
                ({"id": "notes", "source": "ftp://TESTHOST/x"}, "source must"),
                ({"id": "notes", "source": "pane:other"}, "pane:notes"),
                ({"id": "notes", "source": "/feed", "on": "yes"}, "on must"),
                ({"id": "notes", "source": "/feed", "experimental": 1}, "experimental must"),
                ({"id": "notes", "source": "/feed", "protocol": "http"}, "protocol must"),
                (dict(DOCS, protocol="romp"), "protocol none")):
            st, r = self._call("/pane", bad)
            self.assertEqual((st, r.get("ok")), (200, False), (bad, r)); self.assertIn(word, r.get("error", ""), (bad, r))
        self.assertFalse((self.w.pdir / "feed.json").exists(), "a refusal writes nothing")
        st, r = self._call("/pane", b"[]"); self.assertEqual(st, 400, "a malformed body")
        st, r = self._call("/pane", {}); self.assertEqual(st, 400); self.assertIn("pane definition", r["error"])
        self.assertNotEqual(self._call("/pane", NOTES, token=False)[0], 200, "no token: refused")
        self.assertNotEqual(self._call("/panes", token=False)[0], 200)

    def test_define_replaces_a_pane_whole_remove_deletes_it_and_a_shipped_or_unknown_id_is_refused(self):
        st, r = self._call("/pane", NOTES); self.assertEqual((st, r.get("ok")), (200, True), r); self.assertEqual(r["pane"], _full(NOTES))
        rev = r["rev"]
        self.assertEqual(json.loads((self.w.pdir / "notes.json").read_text()), _full(NOTES), "the file holds the filled record, not the request")
        st, r = self._call("/panes"); self.assertEqual([p["id"] for p in r["panes"]], SHIPPED_IDS + ["notes"]); self.assertEqual(r["rev"], rev)
        self.assertEqual([p["builtin"] for p in r["panes"]], [True] * len(SHIPPED) + [False])
        self.assertEqual({k: v for k, v in r["panes"][len(SHIPPED)].items() if k != "builtin"}, _full(NOTES))
        st, r = self._call("/pane", dict(NOTES, title="Notebook")); self.assertEqual((st, r["ok"]), (200, True))
        st, r = self._call("/panes"); self.assertEqual((r["panes"][-1]["id"], r["panes"][-1]["title"]), ("notes", "Notebook"), "a define replaces the pane whole and GET /panes, the shell's source for it, says so")
        _lacks(self, "Notebook", km._landing(), "the landing renders the shipped panes alone: the shell builds this one from GET /panes")
        self._call("/pane", DOCS); self._call("/pane", LAB)
        st, r = self._call("/panes"); self.assertEqual([p["id"] for p in r["panes"]], SHIPPED_IDS + ["docs", "lab", "notes"], "data panes by id after the shipped panes")
        st, r = self._call("/pane", {"remove": "chat"}); self.assertEqual((st, r["ok"]), (200, False)); self.assertIn("shipped", r["error"])
        st, r = self._call("/pane", {"remove": "scratch"}); self.assertEqual((st, r["ok"]), (200, False)); self.assertIn("no pane", r["error"])
        for i in ("notes", "docs"):
            st, r = self._call("/pane", {"remove": i}); self.assertEqual((st, r["ok"]), (200, True))
        st, r = self._call("/pane", {"remove": "lab"}); self.assertEqual((st, r), (200, {"ok": True, "rev": "0"}))
        self.assertFalse((self.w.pdir / "notes.json").exists())
        st, r = self._call("/panes"); self.assertEqual([p["id"] for p in r["panes"]], SHIPPED_IDS)

    def test_the_state_root_serves_a_panes_page_its_shim_and_the_theme_and_nothing_outside_it(self):
        self.assertEqual(self._req("/pane/notes/")[0], 404, "an undefined pane has no page")
        self.w.seed(NOTES, LAB)
        pdir = self.w.pdir / "notes"; pdir.mkdir(parents=True, exist_ok=True)
        (pdir / "index.html").write_text("<!doctype html><script src=shim.js></script><link rel=stylesheet href=theme.css><h1>Notes</h1>")
        (pdir / "app.js").write_text("window.notesApp=1;")
        (km.jd.STATE / "secret.txt").write_text("not served")
        st, ct, body = self._req("/pane/notes/")
        self.assertEqual((st, ct), (200, "text/html; charset=utf-8")); self.assertIn(b"<h1>Notes</h1>", body)
        self.assertEqual(self._req("/pane/notes/index.html")[2], body)
        st, ct, body = self._req("/pane/notes/app.js"); self.assertEqual((st, ct, body), (200, "text/javascript", b"window.notesApp=1;"))
        st, ct, body = self._req("/pane/notes/shim.js"); self.assertEqual((st, ct), (200, "text/javascript"))
        shim = body.decode()
        self.assertIn('var APP="notes";var LABEL="Notes";', shim, "the pane shim for this id: the page speaks the protocol by one script tag")
        st, r = self._call("/panes")
        self.assertIn('var LOADEDPV="%s";' % r["rev"], shim, "baked with the pane set's revision the door reports")
        self.assertIn("notePanes", shim, "and it hands a moved revision to the reload core")
        self.assertIn("var NOSTALE=true;", shim, "no pushed view reaches a state-root page, so the stale prompt is never armed for it (the 1919 read: the banner after every reconnect, never retired); the Files pane's rule, tests/test_files_pane.py")
        self.assertIn('_shim(pid, _dist_ver(), no_stale=True, pv=snap["rev"], data=snap["data"])', KSRC, "served with the stale prompt off and the same listing's revision")
        st, ct, body = self._req("/pane/notes/theme.css"); self.assertEqual((st, ct), (200, "text/css")); self.assertTrue(body.startswith(b"@font-face"), body[:40])
        self.assertEqual(self._req("/pane/notes/missing.js")[0], 404)
        self.assertEqual(self._req("/pane/notes/..%2F..%2Fsecret.txt")[0], 404, "no path leaves the pane's directory")
        self.assertEqual(self._req("/pane/notes/%2E%2E/%2E%2E/secret.txt")[0], 404)
        self.assertEqual(self._req("/pane/lab/")[0], 404, "a route-source pane has no state-root page")
        self.assertEqual(self._req("/pane/feed/")[0], 404, "nor a shipped one")
        self.assertNotEqual(self._req("/pane/notes/", token=False)[0], 200, "behind the token like every route")

    def test_the_state_root_shim_bakes_the_routes_one_snapshot_into_both_its_revision_slots(self):
        # the 1952 read (round two): the shim's keepalive gate LOADEDPV was baked from a second read while the reload core's PANES0
        # took the route's snapshot, so across a define the two disagreed and the gate never called notePanes for the very revision
        # that changed. Executed: the listing is hooked to define a second record after its first call; the route lists once, and the
        # shim's two slots carry that one revision
        self.w.seed(NOTES)
        pdir = self.w.pdir / "notes"; pdir.mkdir(parents=True, exist_ok=True)
        (pdir / "index.html").write_text("<!doctype html><script src=shim.js></script>")
        real = km._panes_snapshot
        calls, who = [], []

        def hooked():
            snap = real()
            if not who:
                who.append(threading.get_ident())
            if threading.get_ident() != who[0]:   # the keepalive thread's own listing is not the route's
                return snap
            calls.append(snap["rev"])
            if len(calls) == 1:
                self.w.seed(DOCS)
            return snap
        km._panes_snapshot = hooked
        try:
            st, ct, body = self._req("/pane/notes/shim.js")
        finally:
            km._panes_snapshot = real
        shim = body.decode()
        self.assertEqual(st, 200); self.assertEqual(len(calls), 1, "the route lists once and hands the revision down: %r" % calls)
        self.assertIn('PANES0="%s"' % calls[0], shim, "the reload core's revision is the route's snapshot's")
        self.assertIn('var LOADEDPV="%s";' % calls[0], shim, "and so is the keepalive gate's (a second read would have baked the define's revision here)")
        self.w.unseed("docs")

    def test_a_page_baked_with_one_revision_is_offered_a_reload_when_the_keepalive_carries_another(self):
        # the reload core the shim embeds, executed: notePanes with the baked revision says nothing, another revision stands
        # the OFFER worded for the panes (never a self-reload); the shell's own socket and the shim hand the keepalive's pv to it
        st, r = self._call("/panes"); pv0 = r.get("rev", "0")
        core = km._reload_core(3)
        out = _run(_RELOAD_STUB + core + _RELOAD_DRIVER.replace("__PV0__", json.dumps(pv0)))
        self.assertIsNone(out["before"], "nothing offered on a current page")
        self.assertIsNone(out["same"], "the baked revision on the keepalive: nothing to say")
        self.assertEqual((out["moved"] or {}).get("text"), "The set of panes changed. Reload to see it.", "a moved revision: the offer, worded for the panes: %r" % out)
        self.assertEqual(((out["moved"] or {}).get("pv"), (out["moved"] or {}).get("code")), ("abc123", ""), "the revision rides its own slot, the build's code untouched (the 1919 read)")
        self.assertFalse(out["reloaded"], "an OFFER, never a self-reload")
        self.assertIn("if(m&&m.type==='ka'&&m.pv&&window.__rompReload&&window.__rompReload.notePanes)window.__rompReload.notePanes(m.pv);", km._LANDING_MOBILE_JS, "the shell's own socket hands pv to the core")
        self.assertIn('if(msg&&msg.type==="ka"&&LOADEDPV&&msg.pv&&msg.pv!==LOADEDPV){var RP=window.__rompReload;if(RP&&RP.notePanes)RP.notePanes(msg.pv);}', KSRC,
                      "the pane shim hands a moved revision to the reload core, before the pinned ka branch")


# ── the store, read through the landing and the keepalive ─────────────────────────────────────────────────────────
class TheStore(unittest.TestCase):
    def setUp(self): self.w = World()
    def tearDown(self): self.w.close()

    def test_a_pane_file_written_by_hand_is_listed_a_bad_one_is_skipped_and_named_once_and_a_rewrite_in_place_is_read(self):
        # the store is the subject: read through _pane_order(), the listing GET /panes answers from (the landing renders the shipped
        # panes alone, so it is no window on the store)
        listed = lambda: [(p["id"], p["title"]) for p in km._pane_order()]
        self.w.seed(NOTES)
        self.assertEqual(listed()[-1], ("notes", "Notes"), "the directory is the registry: a file the door would write is listed")
        _lacks(self, "data-pane=notes", km._landing(), "and the landing does not render it: the shell builds it from GET /panes")
        (self.w.pdir / "bad.json").write_text("{")
        (self.w.pdir / "other.json").write_text(json.dumps(_full(dict(NOTES, id="notes2"))))   # names another pane than its file
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rail = listed(); km._pane_order()
        self.assertEqual([k for k, _ in rail], SHIPPED_IDS + ["notes"], "a bad file is skipped, never listed")
        lines = [ln for ln in err.getvalue().splitlines() if "[panes]" in ln]
        self.assertEqual(len(lines), 2, "each bad file is named once, on stderr, however many builds: %r" % lines)
        self.assertTrue(any("bad.json" in ln for ln in lines) and any("other.json" in ln and "notes2" in ln for ln in lines), lines)
        # an in-place rewrite (an editor, a shell redirection) moves the file's stat: the next build reads it
        fp = self.w.pdir / "notes.json"
        fp.write_text(json.dumps(_full(dict(NOTES, title="Notebook"))))
        st = os.stat(fp); os.utime(fp, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000))
        self.assertEqual(listed()[-1], ("notes", "Notebook"))

    def test_the_landing_and_the_pages_bake_no_revision_and_the_state_root_shim_bakes_its_routes_listing(self):
        # Where the pane set's revision lives (the 1919 read made it one listing per build; it is now NO listing per page build).
        # SOURCE pins, keyed on where the code lives: _landing renders the shipped panes (list(_CODE_PANES)), lists no registry, and
        # hands the reload core the empty baseline through _stale_block(v), which adopts the GET /panes read's revision
        # (_PANES_ADOPT_JS). The executed proofs: test_00 above (a pane file changes no byte of the landing),
        # test_no_listing_per_page_build_executed... below (no listing, the empty baseline on the page) and TheRevisionBaseline (the core
        # takes the read's revision); every page the route table renders and every static file is held byte for byte by
        # tests/test_pane_records_one_source.py.
        self.assertIn('PANES0="abc"', km._reload_core(3, pv="abc"), "the reload core bakes the revision it is handed")
        self.assertIn('PANES0="%s"' % km._panes_rev(), km._reload_core(3), "and this kernel's when handed none")
        src = inspect.getsource(km._landing)
        self.assertIn("panes = list(_CODE_PANES)", src, "the landing renders the shipped panes alone")
        self.assertNotIn("_panes_snapshot()", src, "and lists no registry")
        self.assertIn("_stale_block(v)", src, "the reload core takes no revision from the build")
        self.assertIn("def _stale_block(v):", KSRC); self.assertIn('"<script>" + _reload_core(v, "") + _PANES_ADOPT_JS + "</script>"', KSRC, "the empty baseline, then the read's revision adopted")
        self.assertIn("def _shim(app, v=0, caps=\"\", no_stale=False, pv=None, data=None):", KSRC)   # caps: the fork's wire capabilities a page announces; pv and data: upstream 1919/1952 (the state-root route hands both)

    def test_a_build_offer_and_a_pane_set_offer_stand_together_and_a_decline_covers_both(self):
        core = km._reload_core_js(3, boot="b1", code="C0")
        r = _run(_RELOAD_STUB + core.replace('PANES0="%s"' % km._panes_rev(), 'PANES0="P0"') + _RELOAD_TWO_DRIVER)
        self.assertEqual((r["build"]["code"], r["build"]["text"]), ("C1", km.RELOAD_OFFER_MSG), "a build offer: %r" % r["build"])
        self.assertEqual(r["behind"]["text"], km.RELOAD_OFFER_BEHIND_MSG)
        self.assertEqual((r["panesBeside"]["code"], r["panesBeside"]["pv"], r["panesBeside"]["text"]), ("C1", "B", km.RELOAD_OFFER_BEHIND_MSG),
                         "the pane set moving beside a standing build offer keeps the build's words and rides the revision: %r" % r["panesBeside"])
        self.assertEqual(r["buildAgain"], r["panesBeside"]); self.assertEqual(r["panesAgain"], r["panesBeside"], "nothing new: the one offer stands")
        self.assertIsNone(r["declined"], "Not now clears the offer")
        self.assertIsNone(r["buildAfterDecline"], "the declined build is not re-offered")
        self.assertIsNone(r["panesAfterDecline"], "nor the declined revision")
        self.assertEqual((r["newRevision"]["pv"], r["newRevision"]["code"]), ("C", "C1"), "a NEW revision is new information: offered again, the build beside it: %r" % r["newRevision"])
        r2 = _run(_RELOAD_STUB + core.replace('PANES0="%s"' % km._panes_rev(), 'PANES0="P0"') + _RELOAD_PANES_ONLY_DRIVER)
        self.assertEqual((r2["panes"]["pv"], r2["panes"]["code"], r2["panes"]["text"]), ("B", "", km.RELOAD_OFFER_PANES_MSG), "the revision alone: the panes words: %r" % r2["panes"])
        self.assertIsNone(r2["declined"], "declined, the same revision offers nothing")
        self.assertEqual((r2["moved"]["pv"], r2["moved"]["text"]), ("C", km.RELOAD_OFFER_PANES_MSG), "another revision offers again")

    def test_no_listing_per_page_build_executed_the_landing_and_the_pages_carry_no_record_and_no_revision(self):
        # the 1952 read hooked the listing to prove one listing per build; the page builds now list NONE: the landing renders the
        # shipped panes and bakes the empty baseline (the shell takes the set and its revision from GET /panes), and a page the route
        # table renders (_shim handed no listing) bakes the empty baseline in both slots. The hook still defines a second record after
        # a first call, so a build that listed would render or bake a set. The state-root route's own one listing (it hands its
        # snapshot down) is test_the_state_root_shim_bakes_the_routes_one_snapshot_into_both_its_revision_slots above.
        self.w.seed(NOTES)
        real = km._panes_snapshot
        calls, who = [], []

        def hooked():
            snap = real()
            if not who:
                who.append(threading.get_ident())
            if threading.get_ident() != who[0]:   # the keepalive thread's own listing is not this build's
                return snap
            calls.append(snap["rev"])
            if len(calls) == 1:
                self.w.seed(DOCS)
            return snap
        km._panes_snapshot = hooked
        try:
            html = km._landing()
            direct = km._shim("notes", 3)
            chat = km._chat_page()
        finally:
            km._panes_snapshot = real
        self.assertEqual(calls, [], "no listing per landing or page build: %r" % calls)
        self.assertEqual(_attr_rows(html), [ARTIFACTS_ROW], "the landing renders the shipped generic pane alone, whatever the registry holds")
        self.assertEqual(html.count('PANES0="'), 1, "one reload core on the page")
        _has(self, 'PANES0=""', html, "baked with the empty baseline: the shell adopts the revision its GET /panes read returns")
        for name, page in (("_shim", direct), ("_chat_page", chat)):
            _has(self, 'PANES0=""', page, "%s: the reload core's baseline is empty" % name)
            _has(self, 'var LOADEDPV="";', page, "%s: and so is the keepalive gate's" % name)
            _lacks(self, real()["rev"], page, "%s: no pane-set revision in the page" % name)
        self.assertIn('var LOADEDPV="abc";', km._shim("notes", 3, pv="abc"), "handed a revision (the state-root route), the shim's gate bakes it")

    def test_get_panes_answers_its_rows_and_its_revision_from_one_listing(self):
        # GET /panes is where the shell reads both the rows it builds and the revision its reload offer compares against, so the two
        # must describe ONE set. A define landing between two listings, made deterministic: the listing function the handler calls
        # defines a second pane right after its first call returns (and clears the memo, so a later listing reads the directory
        # again). The real do_GET runs on this thread, and the hook acts on this thread's calls alone.
        self.w.seed(NOTES)
        real = km._panes_snapshot
        me = threading.get_ident()
        listings = []

        def hooked():
            snap = real()
            if threading.get_ident() != me:
                return snap
            listings.append((sorted(snap["data"]), snap["rev"]))
            if len(listings) == 1:
                self.w.seed(DOCS)
                self.w.reset_memos()
            return snap
        h = km.Handler.__new__(km.Handler)
        h.client_address = ("127.0.0.1", 0)
        h.headers = {"X-Romp-Token": km.TOKEN}
        h.path, h.command, h.request_version, h.close_connection = "/panes", "GET", "HTTP/1.1", True
        h.rfile, h.wfile = io.BytesIO(), io.BytesIO()
        got = {}
        h.send_response = lambda code, *a: got.setdefault("status", code)
        h.send_header = lambda k, v: None
        h.end_headers = lambda: None
        h.log_message = lambda *a: None
        km._panes_snapshot = hooked
        try:
            h.do_GET()
        finally:
            km._panes_snapshot = real
        self.assertEqual(got.get("status"), 200)
        body = json.loads(h.wfile.getvalue().decode())
        rows = sorted(r["id"] for r in body["panes"] if r["builtin"] is False)
        after = real()
        self.assertTrue(listings, "the handler listed the registry")
        self.assertEqual(sorted(after["data"]), ["docs", "notes"], "the define landed while the handler answered")
        known = listings + [(sorted(after["data"]), after["rev"])]
        self.assertIn((rows, body["rev"]), known, "the rows %r and the revision %r come from one listing; the listings were %r" % (rows, body["rev"], known))

    def test_the_revision_rides_the_keepalive_beside_the_build_token_and_moves_on_a_change(self):
        def frame():
            got = []
            saved = list(km._clients)
            km._clients[:] = [{"app": "feed", "wid": "", "send": got.append, "alive": True}]
            try:
                km._keepalive_all()
            finally:
                km._clients[:] = saved
            return json.loads(got[0])
        f0 = frame()
        self.assertEqual((f0["type"], f0["dv"], f0.get("pv")), ("ka", km._dist_ver(), "0"), "pv rides beside dv; zero with no data pane: %r" % f0)
        self.w.seed(NOTES); r1 = frame().get("pv")
        self.assertNotEqual(r1, "0"); self.assertEqual(r1, frame().get("pv"), "stable while nothing changes")
        # the revision is a digest of the CHECKED records (the 1919 read): an identical re-define, a bare touch and a malformed file
        # the listing skips move the files' stats and nothing a page can be stale against, so none of them offers a reload
        self.w.seed(NOTES); self.assertEqual(frame().get("pv"), r1, "an identical re-define leaves the revision")
        os.utime(self.w.pdir / "notes.json", None); self.assertEqual(frame().get("pv"), r1, "a touch leaves it")
        (self.w.pdir / "bad.json").write_text("{not json"); self.assertEqual(frame().get("pv"), r1, "a malformed file the listing skips leaves it")
        (self.w.pdir / "bad.json").unlink()
        self.w.seed(dict(NOTES, title="Notebook")); r1b = frame().get("pv"); self.assertNotEqual(r1b, r1, "a changed record moves it"); self.w.seed(NOTES); self.assertEqual(frame().get("pv"), r1)
        self.w.seed(DOCS); r2 = frame().get("pv"); self.assertNotEqual(r2, r1)
        self.w.unseed("docs", "notes")
        self.assertEqual(frame().get("pv"), "0")


# ── the landing renders the shipped panes; the shell builds the defined ones from GET /panes ──────────────────────────
def _get_panes(port):
    """GET /panes from the real handler, with the headers TheDoors._req sends."""
    req = urllib.request.Request("http://127.0.0.1:%d/panes" % port, headers={"X-Romp-Token": km.TOKEN})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


# The builder (_LANDING_PANE_RECORDS_JS) over a stub page: the body attribute as the landing renders it, every consumer's join a
# recorder (each named hook, in the order called, with the ids it was handed), the reload core's adoptPanes a recorder, the Log a
# recorder, timers captured. PRESENT: ids already on the page. The DOM the builder makes is tests/pane_records_stub.py's.
_BUILD_STUB = r"""
'use strict';
global.window = global;
const NOTES_LOG = [], CALLS = [], TIMERS = [];
window.__rompNotify = (k, t) => { NOTES_LOG.push([k, t]); };
global.setTimeout = (f, ms) => { TIMERS.push({ f, ms, cleared: false }); return TIMERS.length; };
global.clearTimeout = (i) => { if (TIMERS[i - 1]) TIMERS[i - 1].cleared = true; };
const PRESENT = __PRESENT__;
global.document = { body: { getAttribute: (a) => (a === 'data-panes' ? __ATTR__ : null) }, getElementById: (id) => (PRESENT.indexOf(id) >= 0 ? { id } : null), querySelector: () => null };
const BAR = { querySelectorAll: () => [] };
__JOIN_NAMES__.forEach((n) => { window[n] = function (a) { CALLS.push([n, Array.isArray(a) ? a.map((p) => p.id) : (a && a.attrs ? a.attrs.id : null)]); }; });
window.__rompReload = { adoptPanes: (rev) => { CALLS.push(['adoptPanes', rev]); } };
""" + pane_records_stub.RECORDS_DOM + r"""
const R = installRecordsDom(document, { bar: BAR });
"""
_BUILD_OUT = r"""
const snapOut = () => JSON.parse(JSON.stringify({ frames: R.inserted.filter((e) => e.tagName === 'IFRAME').map((f) => ({ id: f.attrs.id, attrs: f.attrs, parent: f.parentNode ? f.parentNode.attrs.id : null })),
  rail: R.rail.children.map((b) => ({ pane: b.attrs['data-pane'] || null, id: b.attrs.id || null, cls: b.attrs.class || null, text: b.textContent })),
  tabs: (BAR._kids || []).map((b) => ({ tag: b.tagName, pane: b.attrs['data-pane'], text: b.textContent })),
  row: R.row.children.map((c) => ({ tag: c.tagName, id: c.attrs.id, cls: c.attrs.class })),
  attrs: R.attrs, styles: R.styles, events: R.events, notes: NOTES_LOG, calls: CALLS, created: R.created.length,
  rr: { state: window.__rompPaneRecords.state, rev: window.__rompPaneRecords.rev, rows: window.__rompPaneRecords.rows, error: window.__rompPaneRecords.error },
  timers: TIMERS.map((t) => ({ ms: t.ms, cleared: t.cleared })) }));   // a copy: a later step must not rewrite an earlier snapshot
"""
_JOIN_ORDER = ["__rompPaneJoinErrs", "__rompPaneJoinColumns", "__rompPaneJoinFocus", "__rompWireEsc", "__rompPaneJoinMobile",
               "__rompPaneJoinController", "__rompPaneRestoreTab"]   # the go point's order (the Log's titles, the columns, the focus ring, Escape, the phone before the controller, the controller, the phone's restore)


def _build_js(state_js, driver="console.log(JSON.stringify(snapOut()));", present=(), attr=(ARTIFACTS_ROW,)):
    """The builder's harness: the stub, the head read's state `state_js`, the builder, then `driver` (run it with _run)."""
    return (_BUILD_STUB.replace("__PRESENT__", json.dumps(list(present))).replace("__ATTR__", json.dumps(json.dumps(list(attr))))
            .replace("__JOIN_NAMES__", json.dumps(_JOIN_ORDER)) + state_js + _RECORDS_JS() + _BUILD_OUT + driver)


def _css_rules(text):
    """{selector: declarations} for a run of plain rules (no nesting)."""
    return {sel: decl for sel, decl in re.findall(r"([^{}]+)\{([^{}]*)\}", text)}


class TheLanding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self): self.w = World()
    def tearDown(self): self.w.close()

    def test_the_landing_renders_the_shipped_panes_alone_whatever_the_registry_holds(self):
        # the six record-bearing slices equal the base rendering with three data panes defined (a state-root page, a URL, an
        # experimental route), and no inline script is added for them: the shell builds them from GET /panes
        self.w.seed(NOTES, DOCS, LAB)
        page = km._landing()
        got = slices(page)
        for name, text in FIXTURE["slices"].items():
            self.assertTrue(got.get(name) == text, "the %s slice differs from the shipped panes' rendering: %d vs %d chars" % (name, len(got.get(name, "")), len(text)))
        self.assertEqual(_attr_rows(page), [ARTIFACTS_ROW], "the attribute carries the shipped generic pane alone")
        for marker in ("data-pane=notes", "data-pane=docs", "f-lab", "http://TESTHOST:9/docs/", "/pane/notes/", ">Notes<"):
            _lacks(self, marker, page, "the landing renders no defined pane")
        n_scripts = page.count("<script>")
        self.w.unseed("notes", "docs", "lab")
        self.assertEqual(n_scripts, km._landing().count("<script>"), "no inline script is added for a data pane")

    def test_the_shell_builds_a_defined_pane_from_get_panes_its_frame_rail_button_tab_and_rules(self):
        self.w.seed(NOTES, DOCS, LAB)
        body = _get_panes(self.port)
        r = _run(_build_js(pane_records_stub.records_state(body=body)))
        # the frames: in GET /panes's order (by id), each in its own .pane after a gutter, at the row's end
        self.assertEqual([f["id"] for f in r["frames"]], ["f-docs", "f-lab", "f-notes"])
        self.assertEqual([(c["tag"], c["id"], c["cls"]) for c in r["row"]],
                         [("DIV", "gv-docs", "gv"), ("DIV", "docs-pane", "pane"), ("DIV", "gv-lab", "gv"), ("DIV", "lab-pane", "pane"), ("DIV", "gv-notes", "gv"), ("DIV", "notes-pane", "pane")])
        fr = {f["id"]: f for f in r["frames"]}
        self.assertEqual(fr["f-notes"]["attrs"], {"id": "f-notes", "data-src": "/pane/notes/", "data-protocol": "romp"}, "a state-root pane loads /pane/<id>/ when shown, never its pane: source")
        self.assertEqual(fr["f-docs"]["attrs"], {"id": "f-docs", "data-src": "http://TESTHOST:9/docs/", "data-protocol": "none", "sandbox": "allow-scripts allow-forms allow-popups"},
                         "a URL pane: the URL as given (nothing appended), sandboxed, protocol none")
        self.assertEqual(fr["f-lab"]["attrs"], {"id": "f-lab", "data-src": "/feed", "data-protocol": "romp"}, "a kernel route as given")
        self.assertEqual(fr["f-docs"]["parent"], "docs-pane")
        # ruling B and the sandbox: data-src and never src or the lazy panes' attribute; every attribute set before the frame is in the document
        frame_attrs = [(i, a, on) for i, a, on in r["attrs"] if i.startswith("f-")]
        self.assertFalse(any(a in ("src", "data-lazy-src") for _, a, _ in frame_attrs), frame_attrs)
        self.assertEqual([x for x in frame_attrs if x[2]], [], "every frame attribute (the sandbox among them) is set before the frame is in the document: %r" % frame_attrs)
        self.assertIn(("f-docs", "sandbox", False), [tuple(x) for x in frame_attrs])
        # the rail: before #rail-usage, in order, titles as text; the tabs: before the divider, none for the experimental pane
        self.assertEqual([(b["pane"], b["cls"], b["text"]) for b in r["rail"]],
                         [("docs", "rail-btn", "Docs"), ("lab", "rail-btn", "Lab"), ("notes", "rail-btn", "Notes"), (None, None, "")])
        self.assertEqual(r["rail"][-1]["id"], "rail-usage")
        self.assertEqual([(t["tag"], t["pane"], t["text"]) for t in r["tabs"]], [("BUTTON", "docs", "Docs"), ("BUTTON", "notes", "Notes")], "an experimental pane has no phone tab")
        # the rules equal what the kernel's builders render for the same records (the desktop part a suffix of the shipped render's,
        # the phone part rule for rule inside the media block)
        recs = km._pane_order()[len(km._CODE_PANES):]
        self.assertEqual([p["id"] for p in recs], ["docs", "lab", "notes"])
        self.assertEqual(len(r["styles"]), 1, "one style element")
        css = r["styles"][0]
        desk, _, mob = css.partition("@media " + km._MOBILE_MQ + "{")
        code = km._data_pane_css(list(km._CODE_PANES))
        both = km._data_pane_css(list(km._CODE_PANES) + recs)
        self.assertTrue(both.startswith(code)); self.assertEqual(desk, both[len(code):], "the desktop rules are the kernel's for these records")
        self.assertTrue(mob.endswith("}"), mob)
        want = {s: d for s, d in _css_rules(km._data_pane_mobile_css(list(km._CODE_PANES) + recs)).items()}
        mine = _css_rules(mob[:-1])
        strip = lambda m: {",".join(x for x in s.split(",") if "artifacts" not in x): d for s, d in m.items()}
        self.assertEqual(mine, strip(want), "the phone rules are the kernel's for these records")
        # the state, then the read's revision adopted and the bundles told
        self.assertEqual((r["rr"]["state"], r["rr"]["rev"]), ("ok", body["rev"]))
        self.assertEqual([x["id"] for x in r["rr"]["rows"]], ["docs", "lab", "notes"])
        self.assertEqual(r["calls"][-1], ["adoptPanes", body["rev"]], "the reload core takes the read's revision")
        self.assertEqual(r["events"], [{"state": "ok", "rows": r["rr"]["rows"], "error": "", "frames": ["f-docs", "f-lab", "f-notes"]}])
        self.assertEqual(r["notes"], [], "nothing logged")
        self.assertEqual(r["timers"], [], "a settled read arms no backstop")
        self.assertNotIn("innerHTML", _RECORDS_JS(), "titles go in as text, never as markup")

    def test_a_title_lands_as_text(self):
        self.w.seed({"id": "x", "title": "A <b>&", "source": "/feed", "on": True})
        page = km._landing()
        _lacks(self, "A &lt;b&gt;&amp;", page, "the landing does not render it")
        r = _run(_build_js(pane_records_stub.records_state(body=_get_panes(self.port))))
        self.assertEqual(([b["text"] for b in r["rail"] if b["pane"] == "x"], [t["text"] for t in r["tabs"]]), (["A <b>&"], ["A <b>&"]), "the title as text, verbatim")

    def test_the_joins_run_in_their_order_and_each_hook_is_defined_once_on_the_page(self):
        self.w.seed(NOTES, DOCS)
        body = _get_panes(self.port)
        r = _run(_build_js(pane_records_stub.records_state(body=body)))
        rows = ["docs", "notes"]
        self.assertEqual(r["calls"], [["__rompPaneJoinErrs", rows], ["__rompPaneJoinColumns", rows], ["__rompPaneJoinFocus", rows],
                                      ["__rompWireEsc", "f-docs"], ["__rompWireEsc", "f-notes"], ["__rompPaneJoinMobile", rows],
                                      ["__rompPaneJoinController", rows], ["__rompPaneRestoreTab", None], ["adoptPanes", body["rev"]]],
                         "the go point's order: the phone joins before the controller (its apply copies a shown frame's src), the restore last")
        listed = re.search(r"var JOINS=(\[[^\]]*\]);", _RECORDS_JS())
        self.assertIsNotNone(listed); self.assertEqual(json.loads(listed.group(1).replace("'", '"')), _JOIN_ORDER, "the builder's list is the order pinned here")
        page = km._landing()
        for n in _JOIN_ORDER:
            self.assertEqual(page.count("window.%s=function" % n), 1, "%s is defined by exactly one of the landing's scripts" % n)

    def test_a_row_the_kernel_would_refuse_is_left_out_and_named_and_a_url_source_is_protocol_none(self):
        ok = pane_records_stub.door_rows(dict(NOTES, source="/feed"))
        bad = pane_records_stub.door_rows(
            {"id": "Bad", "source": "/feed"}, {"id": "xjs", "source": "javascript:alert(1)"}, {"id": "xdata", "source": "data:text/html,hi"},
            {"id": "xhost", "source": "//TESTHOST/x"}, {"id": "feed", "source": "/feed"}, {"id": "chat-x", "source": "/feed"}, {"id": "tl", "source": "/feed"},
            {"id": "xlong", "title": "x" * 25, "source": "/feed"}, {"id": "xflag", "on": "yes", "source": "/feed"}, {"id": "xstate", "source": "pane:other"},
            {"id": "dup", "source": "/feed"}, {"id": "notes", "source": "/feed"})
        forced = pane_records_stub.door_rows({"id": "xproto", "source": "http://TESTHOST:9/x/", "protocol": "romp"})   # a URL whose row claims the protocol
        shipped = [dict(p, builtin=True) for p in km._CODE_PANES]
        r = _run(_build_js(pane_records_stub.records_state(rows=shipped + ok + bad + forced), present=("f-dup",)))
        self.assertEqual([f["id"] for f in r["frames"]], ["f-notes", "f-xproto"], "the shipped rows are the page's own, every refused row is left out: %r" % r["notes"])
        self.assertEqual(next(f for f in r["frames"] if f["id"] == "f-xproto")["attrs"]["data-protocol"], "none", "a URL source is protocol none whatever the row says")
        left = [t for k, t in r["notes"] if k == "panes"]
        self.assertEqual(len(left), len(bad), "each refused row named once in the Log: %r" % left)
        for row, line in zip(bad, left):
            self.assertIn("Left out a pane defined at the kernel", line); self.assertIn("'%s'" % row["id"], line)
        # the source shapes agree with the kernel's (_pane_source_kind; a state-root source must name its own pane)
        sources = ["/feed", "/a/b.c-d_e", "/", "//x", "/x?y", "http://TESTHOST:9/a?b#c", "https://x", "HTTP://X", "ftp://x", "javascript:x",
                   "pane:src", "pane:other", "", "feed", "http://x y"]
        rows = pane_records_stub.door_rows(*({"id": "src%d" % i, "source": s} for i, s in enumerate(sources)))
        for row in rows:
            if row["source"] == "pane:src":
                row["source"] = "pane:" + row["id"]
        r2 = _run(_build_js(pane_records_stub.records_state(rows=rows)))
        built = {f["id"][2:] for f in r2["frames"]}
        kernel = {row["id"] for row in rows if km._pane_check({k: v for k, v in row.items() if k != "builtin"})[1] is None}
        self.assertEqual(built, kernel, "the builder takes exactly the sources the kernel's check takes: %r" % sorted(built ^ kernel))

    def test_a_failed_read_is_shown_never_silently_empty_and_a_late_answer_still_builds(self):
        self.w.seed(NOTES)
        body = _get_panes(self.port)
        r = _run(_build_js(pane_records_stub.records_state(state="failed", status=500, error="/panes answered HTTP 500")))
        self.assertEqual(r["notes"], [["panes", "Couldn't read the panes defined at the kernel (/panes answered HTTP 500), so they are missing from this page. Reload to try again."]])
        self.assertEqual((r["frames"], r["rail"][:-1], r["tabs"], r["styles"]), ([], [], [], []), "no defined pane's DOM")
        self.assertEqual([c[0] for c in r["calls"]], [], "no join and no revision adopted")
        self.assertEqual(r["events"], [{"state": "failed", "rows": [], "error": "/panes answered HTTP 500", "frames": []}], "the bundles hear the failure too")
        # a 403 carrying X-Romp-Reauth: another script on the page is already navigating the top frame away, so the Log
        # stays quiet
        r = _run(_build_js(pane_records_stub.records_state(state="failed", status=403, reauth=True, error="/panes answered HTTP 403")))
        self.assertEqual(r["notes"], []); self.assertEqual(r["events"][0]["state"], "failed")
        # an answer that is not a pane list
        r = _run(_build_js(pane_records_stub.records_state(body={"panes": "x", "rev": "r"})))
        self.assertEqual([t for _, t in r["notes"]], ["Couldn't read the panes defined at the kernel (the answer was not a pane list), so they are missing from this page. Reload to try again."])
        # no answer within the backstop: said as such; a late answer still builds
        drive = ("const o = {}; o.armed = snapOut(); TIMERS.forEach((t) => { if (!t.cleared) t.f(); }); o.timedOut = snapOut();"
                 "settleRecords('ok', " + json.dumps(body) + "); o.late = snapOut(); console.log(JSON.stringify(o));")
        r = _run(_build_js(pane_records_stub.records_state(state="loading"), driver=drive))
        self.assertEqual((r["armed"]["timers"], r["armed"]["frames"], r["armed"]["notes"]), ([{"ms": 30000, "cleared": False}], [], []), "loading: the backstop armed, nothing built yet")
        self.assertEqual([t for _, t in r["timedOut"]["notes"]], ["Couldn't read the panes defined at the kernel (no answer within 30 s), so they are missing from this page. Reload to try again."])
        self.assertEqual(r["timedOut"]["rr"]["state"], "failed")
        self.assertEqual(([f["id"] for f in r["late"]["frames"]], r["late"]["rr"]["state"], [e["state"] for e in r["late"]["events"]]), (["f-notes"], "ok", ["failed", "ok"]),
                         "the late answer builds and says so; the Log keeps the timeout it reported")

    def test_a_second_run_of_the_builder_builds_nothing(self):
        self.w.seed(NOTES)
        state = pane_records_stub.records_state(body=_get_panes(self.port))
        r = _run(_build_js(state, driver="const once = R.created.length;" + _RECORDS_JS() + "console.log(JSON.stringify({ once, twice: R.created.length, frames: snapOut().frames.length }));"))
        self.assertEqual((r["once"], r["twice"], r["frames"]), (r["once"], r["once"], 1), "the duplicate-build guard: once per page")


class TheRevisionBaseline(unittest.TestCase):
    """The reload core takes the pane set's revision from the page's GET /panes read (adoptPanes): the landing and the pages bake an
    empty baseline, which leaves notePanes inert until the read lands; the read's revision is then the page's, a keepalive or a pane's
    relay carrying it offers nothing, an offer whose only news was it is withdrawn, another revision offers, and a declined build stays
    declined. The landing's core adopts a read that landed before the core was made (_PANES_ADOPT_JS)."""

    def _core(self):
        return km._reload_core_js(3, boot="b1", code="C0").replace('PANES0="%s"' % km._panes_rev(), 'PANES0=""')

    def test_adopt_sets_the_baseline_the_same_revision_offers_nothing_another_offers(self):
        drive = r"""
const R = window.__rompReload; const out = {};
R.notePanes('P1'); out.beforeAdopt = R.offered();          // the empty baseline: inert
if (R.adoptPanes) R.adoptPanes('P1'); R.notePanes('P1'); out.same = R.offered();
R.propose(0, '', 'P1'); out.relayed = R.offered();          // a pane's relay of the revision the page shows
R.notePanes('P2'); out.moved = R.offered();
console.log(JSON.stringify(out));
"""
        r = _run(_RELOAD_STUB + self._core() + drive)
        self.assertIsNone(r["beforeAdopt"], "no baseline yet: nothing to compare, nothing offered")
        self.assertIsNone(r["same"], "the read's revision on the keepalive offers nothing")
        self.assertIsNone(r["relayed"], "nor relayed by a pane")
        self.assertEqual(((r["moved"] or {}).get("pv"), (r["moved"] or {}).get("text")), ("P2", km.RELOAD_OFFER_PANES_MSG), "another revision offers: %r" % r["moved"])

    def test_an_offer_whose_only_news_was_the_read_revision_is_withdrawn_and_a_declined_build_stays_declined(self):
        drive = r"""
const R = window.__rompReload; const out = {};
R.propose(0, '', 'P1'); out.stood = R.offered();           // an offer standing for P1 before the read landed
if (R.adoptPanes) R.adoptPanes('P1'); out.afterAdopt = R.offered();
R.noteVersion({ code_ident: 'C1' }); out.build = R.offered();
R.dismiss(); if (R.adoptPanes) R.adoptPanes('P3'); R.noteVersion({ code_ident: 'C1' }); out.declined = R.offered();
console.log(JSON.stringify(out));
"""
        r = _run(_RELOAD_STUB + self._core() + drive)
        self.assertEqual((r["stood"] or {}).get("pv"), "P1", r)
        self.assertIsNone(r["afterAdopt"], "the page now shows that set: the offer is withdrawn")
        self.assertEqual((r["build"] or {}).get("code"), "C1")
        self.assertIsNone(r["declined"], "adopting a revision does not re-offer a declined build")

    def test_a_build_declined_on_an_earlier_page_stays_declined_after_the_page_adopts_its_read_revision(self):
        # Not now is stored with the pane set as its page saw it (here: no pane-set news). A new page adopts the revision it read as
        # its baseline, not as news it has seen, so the declined build is not offered again; another build still is
        drive = r"""
LOCAL['romp:reloadNotNow'] = JSON.stringify({ dv: 0, code: 'C1', pv: '' });
const R = window.__rompReload; const out = {};
out.adopt = typeof R.adoptPanes;
if (R.adoptPanes) R.adoptPanes('P1');
R.propose(0, '', 'P1'); out.relayed = R.offered();
R.noteVersion({ code_ident: 'C1' }); out.declinedBuild = R.offered();
R.noteVersion({ code_ident: 'C2' }); out.newBuild = R.offered();
console.log(JSON.stringify(out));
"""
        r = _run(_RELOAD_STUB + self._core() + drive)
        self.assertIsNone(r["relayed"], "the adopted revision, relayed, offers nothing (adoptPanes: %s)" % r["adopt"])
        self.assertIsNone(r["declinedBuild"], "the build declined on an earlier page stays declined: %r" % r["declinedBuild"])
        self.assertEqual((r["newBuild"] or {}).get("code"), "C2", "another build is offered: %r" % r["newBuild"])

    def test_the_shells_core_adopts_a_read_that_landed_before_the_core_was_made(self):
        # the landing's reload core element (the empty baseline, then this adoption) is pinned by source in TheStore; executed here
        drive = r"""
const out = {}; const R = window.__rompReload;
R.notePanes('P1'); out.same = R.offered(); R.notePanes('P2'); out.moved = R.offered();
console.log(JSON.stringify(out));
"""
        r = _run(_RELOAD_STUB + "window.__rompPaneRecords = { state: 'ok', rev: 'P1' };\n" + self._core() + _ADOPT_JS() + drive)
        self.assertIsNone(r["same"], "adopted at the core's parse: the read's revision is the baseline")
        self.assertEqual((r["moved"] or {}).get("pv"), "P2", r)


# ── the inline scripts read the attribute; the source check ─────────────────────────────────────────────────────────
_PANES_STUB = r"""
'use strict';
const ATTR = __ATTR__;
const KEYS = ['chat','timeline','fleet','feed','files'].concat(__DATA_IDS__);   // the hand five, then the generic panes the page ships with (the Artifacts record, from the attribute; the 1922 read: hand-listed too, it was built twice); the panes defined at the kernel are built by the shell's GET /panes road (adoptRecord below)
const PROTO = __PROTO__;
const POSTED = {}, CLS = new Set(['po-chat', 'po-feed', 'po-timeline']), STORE = {}, STORAGE = [], TABS = [], SETS = {};
const frames = {};
KEYS.forEach((k) => { const attrs = (k === 'chat' || k === 'files') ? { src: '/' + k } : { 'data-src': '/' + k }; if (PROTO[k]) attrs['data-protocol'] = PROTO[k]; frames['f-' + k] = {
  attrs, getAttribute: (a) => (a in attrs ? attrs[a] : null), setAttribute: (a, v) => { attrs[a] = v; if (a === 'src') SETS[k] = (SETS[k] || 0) + 1; },
  contentWindow: { postMessage: (m) => { (POSTED[k] = POSTED[k] || []).push(JSON.parse(JSON.stringify(m))); } },
  addEventListener() {} }; });
const BTNS = {};
KEYS.forEach((k) => { BTNS[k] = { hidden: false, title: '', getAttribute: (a) => (a === 'data-pane' ? k : null), classList: { toggle() {} }, addEventListener() {} }; });
let TAB = 'chat', MOBILE = false;
global.window = global;
global.localStorage = { getItem: (k) => (k in STORE ? STORE[k] : null), setItem: (k, v) => { STORE[k] = v; } };
global.location = { search: '' };
global.URLSearchParams = class { get() { return null; } };
global.Event = class { constructor(t) { this.type = t; } };
global.addEventListener = (ev, f) => { if (ev === 'storage') STORAGE.push(f); };
global.dispatchEvent = () => true;
global.document = {
  body: { classList: { toggle: (c, on) => { if (on) CLS.add(c); else CLS.delete(c); }, contains: (c) => CLS.has(c) },
          getAttribute: (a) => (a === 'data-tab' ? TAB : a === 'data-panes' ? ATTR : null) },
  querySelectorAll: (sel) => { if (sel === '.rail-btn[data-pane]') return Object.keys(BTNS).map((k) => BTNS[k]); const m = /data-pane=([\w-]+)/.exec(sel); return m && BTNS[m[1]] ? [BTNS[m[1]]] : []; },
  getElementById: (id) => frames[id] || null,
};
window.__rompMobileOn = () => MOBILE;
window.__rompMobileTab = (t) => { TABS.push(t); TAB = t; };
// a pane the shell builds from GET /panes joins this stub's maps as it enters the document: its frame (src writes counted, posts kept)
// and its rail button
function adoptRecord(el) {
  const id = el.attrs.id || '';
  if (el.tagName === 'IFRAME' && id.indexOf('f-') === 0) { const k = id.slice(2), sa = el.setAttribute; el.setAttribute = (a, v) => { sa(a, v); if (a === 'src') SETS[k] = (SETS[k] || 0) + 1; };
    el.contentWindow = { postMessage: (m) => { (POSTED[k] = POSTED[k] || []).push(JSON.parse(JSON.stringify(m))); } }; frames[id] = el; }
  else if (el.attrs.class === 'rail-btn') BTNS[el.attrs['data-pane']] = el;
}
__SEED__
"""

# the ON-SCREEN gate, executed (the 1922 read: no row was enabled in the gear while off screen, the one state in which the gate acts,
# so a mutant copying src for every enabled generic pane passed the harness): the gear has the Artifacts pane enabled and a
# non-experimental data pane is on:false; at boot neither loads; the rail toggle loads each
_GATE_DRIVER = r"""
if (['notes', 'docs'].some((k) => !frames['f-' + k])) { console.log(JSON.stringify({ unbuilt: ['notes', 'docs'].filter((k) => !frames['f-' + k]) })); return; }   // the defined panes never reached the page: nothing to drive
const out = {};
const st = () => ({ artSrc: frames['f-artifacts'].attrs.src || null, artHidden: BTNS.artifacts.hidden, artOn: CLS.has('po-artifacts'), offSrc: frames['f-offpane'].attrs.src || null, offHidden: BTNS.offpane.hidden, offOn: CLS.has('po-offpane') });
out.boot = st();
window.__rompPaneToggle('artifacts', true); window.__rompPaneToggle('offpane', true);
out.on = st();
console.log(JSON.stringify(out));
"""

# a PHONE (the 1922 read): a generic pane loads by its TAB alone, never by the desktop flag; the current tab's frame loads on the
# controller's apply (the boot, the layout flip), once
_PHONE_DRIVER = r"""
if (['notes', 'docs'].some((k) => !frames['f-' + k])) { console.log(JSON.stringify({ unbuilt: ['notes', 'docs'].filter((k) => !frames['f-' + k]) })); return; }   // the defined panes never reached the page: nothing to drive
const out = {};
out.boot = { notesSrc: frames['f-notes'].attrs.src || null, notesOn: CLS.has('po-notes'), artSrc: frames['f-artifacts'].attrs.src || null, sets: Object.assign({}, SETS) };
const reapply = () => { if (window.__rompPaneApply) window.__rompPaneApply(); };   // absent at a base without it: the reads below red on behaviour, not on a missing name
TAB = 'notes'; reapply();
out.tabNotes = { notesSrc: frames['f-notes'].attrs.src || null, sets: Object.assign({}, SETS) };
reapply();
out.again = { sets: Object.assign({}, SETS) };
TAB = 'chat'; reapply();
out.tabChat = { docsSrc: frames['f-docs'].attrs.src || null, sets: Object.assign({}, SETS) };
MOBILE = false; reapply();   // the layout flips to the desktop: every pane whose flag is on loads
out.desktop = { docsSrc: frames['f-docs'].attrs.src || null, sets: Object.assign({}, SETS) };
console.log(JSON.stringify(out));
"""

_PANES_DRIVER = r"""
if (['notes', 'docs'].some((k) => !frames['f-' + k])) { console.log(JSON.stringify({ unbuilt: ['notes', 'docs'].filter((k) => !frames['f-' + k]) })); return; }   // the defined panes never reached the page: nothing to drive
const last = (k) => (POSTED[k] || []).slice(-1)[0];
const out = {};
out.boot = { notes: CLS.has('po-notes'), lab: CLS.has('po-lab'), docs: CLS.has('po-docs'), labHidden: BTNS.lab.hidden, notesHidden: BTNS.notes.hidden,
             notesSrc: frames['f-notes'].attrs.src || null, labSrc: frames['f-lab'].attrs.src || null,
             told: last('notes') ? last('notes').on : null, docsTold: (POSTED.docs || []).length };
window.__rompPaneToggle('notes');                 // the rail button: off
out.off = { notes: CLS.has('po-notes'), store: JSON.parse(STORE['romp-panes'] || 'null'), told: last('notes') ? last('notes').on.notes : null };
window.__rompPaneToggle('lab', true);             // not in this dashboard (experimental, the gear off): refused
out.labRefused = { lab: CLS.has('po-lab') };
STORE['romp:settings'] = JSON.stringify({ panes: { lab: true } }); STORAGE.forEach((f) => f({ key: 'romp:settings' }));   // the gear's row turns it on
out.labOn = { hidden: BTNS.lab.hidden, lab: CLS.has('po-lab'), labSrc: frames['f-lab'].attrs.src || null };
window.__rompPaneToggle('lab', true);
out.labShown = { lab: CLS.has('po-lab'), told: last('notes') ? last('notes').on.lab : null, docsTold: (POSTED.docs || []).length };
STORE['romp:settings'] = JSON.stringify({ panes: { notes: false } }); STORAGE.forEach((f) => f({ key: 'romp:settings' }));   // the gear hides the notes pane
out.notesGone = { hidden: BTNS.notes.hidden, notes: CLS.has('po-notes'), inTold: last('chat') ? ('notes' in last('chat').on) : null };
console.log(JSON.stringify(out));
"""

_SOURCE_STUB = r"""
'use strict';
const ORIGIN = 'http://TESTHOST:7432';
const W = { romp: {}, none: {}, stranger: {} };
const FR = [ { contentWindow: W.romp, getAttribute: (a) => (a === 'data-protocol' ? 'romp' : null) },
             { contentWindow: W.none, getAttribute: (a) => (a === 'data-protocol' ? 'none' : null) },
             { contentWindow: {}, getAttribute: () => null } ];
const HANDLERS = [], TOGGLES = [];
global.window = global;
global.location = { origin: ORIGIN };
global.addEventListener = (ev, f) => { if (ev === 'message') HANDLERS.push(f); };
global.document = { getElementById: () => null, querySelectorAll: (s) => (s === 'iframe' ? FR : []), addEventListener() {} };
global.setTimeout = () => 0;
window.__rompPaneToggle = (k, to) => { TOGGLES.push([k, to]); };
"""

_SOURCE_DRIVER = r"""
const ok = window.__rompPaneSourceOk;
const ev = (source, origin) => ({ source, origin: origin || ORIGIN, data: { romp: 'toggleFleet', to: 'fleet' } });
const out = { defined: typeof ok };
if (typeof ok === 'function') {
  out.romp = ok(ev(W.romp)); out.none = ok(ev(W.none)); out.shell = ok(ev(window)); out.stranger = ok(ev(W.stranger));
  out.otherOrigin = ok(ev(W.romp, 'http://TESTHOST:9')); out.noSource = ok({ origin: ORIGIN, data: {} }); out.nothing = ok(null);
  W.romp.parent = window; W.none.parent = window;
  out.nestedInRomp = ok(ev({ parent: W.romp })); out.nestedInNone = ok(ev({ parent: W.none }));
}
// the Outline's bridge handler, fed a forged toggle from the URL pane, one from a frame nested in a protocol pane, and a real one
HANDLERS.forEach((h) => h(ev(W.none)));
HANDLERS.forEach((h) => h(ev({ parent: W.romp })));
out.forgedToggles = TOGGLES.length;
HANDLERS.forEach((h) => h(ev(W.romp)));
out.realToggles = TOGGLES.length;
console.log(JSON.stringify(out));
"""

# the same bridge handler on a page WITHOUT the shell's check: fail-closed, nothing is acted on
_CLOSED_DRIVER = r"""
const ev = (source) => ({ source, origin: ORIGIN, data: { romp: 'toggleFleet', to: 'fleet' } });
HANDLERS.forEach((h) => h(ev(W.romp)));
console.log(JSON.stringify({ defined: typeof window.__rompPaneSourceOk, toggles: TOGGLES.length }));
"""


def _stub(defs, seed=""):
    """The pane controller's DOM stub: the body attribute as the landing carries it (the Artifacts record), the panes `defs` defined
    at the kernel answered by GET /panes (the head read settled) and built by the shell's road, `seed` run before the scripts. Run
    it before _LANDING_COLLAPSE_JS + _LANDING_PANE_RECORDS_JS: the controller parses, then the builder joins the defined panes."""
    rows = [ARTIFACTS_ROW]
    return (_PANES_STUB.replace("__ATTR__", json.dumps(json.dumps(rows))).replace("__DATA_IDS__", json.dumps([r["id"] for r in rows]))
            .replace("__PROTO__", json.dumps({r["id"]: r["protocol"] for r in rows})).replace("__SEED__", seed)
            + pane_records_stub.RECORDS_DOM + "const RD = installRecordsDom(document, { adopt: adoptRecord });\n"
            + pane_records_stub.records_state(rows=pane_records_stub.door_rows(*defs)))


class TheInlineScripts(unittest.TestCase):
    def setUp(self): self.w = World()
    def tearDown(self): self.w.close()

    def test_the_pane_controller_shows_a_data_pane_by_its_flag_hides_an_experimental_one_until_the_gear_asks_and_tells_no_url_pane(self):
        stub = _stub((NOTES, DOCS, LAB))   # defined at the kernel: built by the shell from GET /panes, joined to the controller after its boot
        r = _run(stub + km._LANDING_COLLAPSE_JS + _RECORDS_JS() + _PANES_DRIVER)
        self.assertIsNone(r.get("unbuilt"), "the panes defined at the kernel reach the page through GET /panes: %r" % r.get("unbuilt"))
        b = r["boot"]
        self.assertTrue(b["notes"], "on: true puts the pane on screen at boot: %r" % b)
        self.assertEqual(b["notesSrc"], "/pane/notes/", "a shown data pane's iframe gets its src (the optional panes' rule): the state-root page's address")
        self.assertFalse(b["notesHidden"]); self.assertTrue(b["docs"], b)
        self.assertFalse(b["lab"]); self.assertTrue(b["labHidden"], "experimental: not in this dashboard until the gear's row asks")
        self.assertIsNone(b["labSrc"], "an experimental pane never loads until asked for")
        self.assertEqual(b["told"], {"chat": True, "timeline": True, "fleet": False, "feed": True, "waiting": False, "files": False, "docs": True, "notes": True},
                         "the broadcast names the data panes beside the shipped ones (the experimental ones, the Artifacts record and the lab pane, are not in this dashboard until the gear asks)")
        self.assertEqual(b["docsTold"], 0, "a URL pane (protocol none) is told nothing")
        self.assertEqual((r["off"]["notes"], r["off"]["store"]["notes"], r["off"]["told"]), (False, False, False), "the rail toggle, persisted, broadcast")
        self.assertFalse(r["labRefused"]["lab"])
        self.assertEqual((r["labOn"]["hidden"], r["labOn"]["lab"], r["labOn"]["labSrc"]), (False, True, "/feed"),
                         "the gear's row turning a pane on brings it on screen and loads it (the optional panes' live reconcile)")
        self.assertEqual((r["labShown"]["lab"], r["labShown"]["told"], r["labShown"]["docsTold"]), (True, True, 0), "and the panes are told; the URL pane still nothing")
        self.assertEqual((r["notesGone"]["hidden"], r["notesGone"]["notes"], r["notesGone"]["inTold"]), (True, False, False), "a gear-hidden data pane is gone from the dashboard and from the broadcast")

    def test_a_generic_pane_enabled_in_the_gear_loads_only_when_it_comes_on_screen(self):
        r = _run(_stub((NOTES, DOCS, LAB, OFFPANE), "STORE['romp:settings'] = JSON.stringify({ panes: { artifacts: true } });") + km._LANDING_COLLAPSE_JS + _RECORDS_JS() + _GATE_DRIVER)
        self.assertIsNone(r.get("unbuilt"), "the panes defined at the kernel reach the page through GET /panes: %r" % r.get("unbuilt"))
        b = r["boot"]
        self.assertEqual((b["artHidden"], b["artOn"], b["artSrc"]), (False, False, None), "the Artifacts pane enabled in the gear: its button back, off screen by its rail default, NOT loaded: %r" % b)
        self.assertEqual((b["offHidden"], b["offOn"], b["offSrc"]), (False, False, None), "a non-experimental on:false data pane: in the dashboard, off screen, not loaded")
        o = r["on"]
        self.assertEqual((o["artOn"], o["artSrc"], o["offOn"], o["offSrc"]), (True, "/artifacts", True, "/feed"), "the rail toggle brings each on screen and loads it once: %r" % o)

    def test_on_a_phone_a_generic_pane_loads_by_its_tab_alone_and_the_current_tab_loads_on_the_apply(self):
        r = _run(_stub((NOTES, DOCS, LAB), "MOBILE = true; TAB = 'chat'; STORE['romp-panes'] = JSON.stringify({ notes: true, docs: true });") + km._LANDING_COLLAPSE_JS + _RECORDS_JS() + _PHONE_DRIVER)
        self.assertIsNone(r.get("unbuilt"), "the panes defined at the kernel reach the page through GET /panes: %r" % r.get("unbuilt"))
        b = r["boot"]
        self.assertEqual((b["notesOn"], b["notesSrc"], b["artSrc"]), (True, None, None), "the desktop flag on, the phone on the chat tab: the notes pane is NOT loaded into a frame the phone never shows: %r" % b)
        generic = lambda sets: {k: v for k, v in sets.items() if k not in ("chat", "timeline", "fleet", "feed", "files")}   # the hand-written optional panes load by their flag on every layout (unchanged)
        self.assertEqual(generic(b["sets"]), {}, "no generic pane's src written at boot on a phone: %r" % b["sets"])
        self.assertEqual((r["tabNotes"]["notesSrc"], generic(r["tabNotes"]["sets"])), ("/pane/notes/", {"notes": 1}), "the current tab's frame loads on the apply (the boot, the layout flip): %r" % r["tabNotes"])
        self.assertEqual(generic(r["again"]["sets"]), {"notes": 1}, "and once")
        self.assertEqual(r["tabChat"]["docsSrc"], None, "another tab current: the docs pane (flag on) still not loaded")
        self.assertEqual(r["desktop"]["docsSrc"], "http://TESTHOST:9/docs/", "the layout flipped to the desktop: the flag loads it: %r" % r["desktop"])

    def test_the_source_check_takes_a_protocol_frame_and_drops_the_shell_a_stranger_a_foreign_origin_a_url_pane_and_a_nested_frame(self):
        r = _run(_SOURCE_STUB + km._LANDING_BOOT_JS + km._LANDING_FLEET_JS + _SOURCE_DRIVER)
        self.assertEqual(r.get("forgedToggles"), 0, "a toggleFleet forged by the URL pane or by a frame nested in a pane must not toggle: %r" % r)
        self.assertEqual(r.get("realToggles"), 1, "a protocol pane's own toggle lands: %r" % r)
        self.assertEqual({k: r.get(k) for k in ("romp", "none", "shell", "stranger", "otherOrigin", "noSource", "nothing", "nestedInRomp", "nestedInNone")},
                         {"romp": True, "none": False, "shell": False, "stranger": False, "otherOrigin": False, "noSource": False, "nothing": False,
                          "nestedInRomp": False, "nestedInNone": False}, "the check rules on the IMMEDIATE source frame (plans/panes-as-data.md section 5)")

    def test_a_listener_on_a_page_without_the_check_acts_on_nothing(self):
        # fail-closed (the 1919 read): the bridge handler executed without the boot script that defines the check
        r = _run(_SOURCE_STUB + km._LANDING_FLEET_JS + _CLOSED_DRIVER)
        self.assertEqual(r, {"defined": "undefined", "toggles": 0}, "no check on the page, no message acted on: %r" % r)

    def test_every_shell_listener_reads_the_one_check_inline_and_bundled_and_the_baked_maps_read_the_attribute(self):
        # the census: every `message` listener the landing registers (except the service worker's, which is the worker's own
        # channel), every listener in the sources of the bundles the landing loads, and the built bundles themselves
        html = km._landing()
        regs = [m.start() for m in re.finditer(r"addEventListener\('message',", html)]
        self.assertGreaterEqual(len(regs), 14, "the shell's message listeners: %d" % len(regs))
        open_ones, sw = [], 0
        for i in regs:
            if html[max(0, i - 4):i] == "swc.":
                sw += 1; continue
            m = re.match(r"addEventListener\('message',function\(e\)\{", html[i:i + 80])   # the guard reads `e`, so the listener is a function of e
            if not m or not html[i + m.end():].startswith(GUARD):   # the FIRST statement, not anywhere in the next 200 characters (the 1919 read)
                open_ones.append(i)   # the offset: the listener's text is sliced below, where the served-pins census classifies the read
        self.assertEqual(sw, 1, "the service worker's notificationClick listener, on the worker's channel")
        self.assertEqual([html[i:i + 140] for i in open_ones], [], "every inline listener reads the check, fail-closed, as its first statement")
        self.assertIn("window.__rompPaneSourceOk=function(e)", km._LANDING_BOOT_JS, "defined by the first script on the page")
        self.assertLess(html.index("window.__rompPaneSourceOk=function(e)"), regs[0], "before any listener is registered")
        names = sorted(set(re.findall(r"src=/dist/([a-z-]+)\.js", html)))
        self.assertIn("palette-main", names); self.assertIn("panedock-main", names)
        listeners = {}
        for n in names:
            fp = os.path.join(ROOT, "ui", "webview", n + ".ts")
            if not os.path.exists(fp):
                continue
            src = open(fp).read()
            for m in re.finditer(r'addEventListener\(\s*"message"|on\(\s*window\s*,\s*"message"', src):
                tail = src[m.start():m.start() + 400]
                listeners.setdefault(n, []).append("paneSourceOk(" in tail or "protocolFrame(" in tail)
        self.assertEqual(sorted(listeners), ["palette-main", "panedock-main"], "the shell bundles with message listeners: %r" % listeners)
        self.assertTrue(all(all(v) for v in listeners.values()), "every bundled listener reads the one check: %r" % listeners)
        self.assertIn("if (!paneSourceOk(e)) return null;", open(os.path.join(ROOT, "ui", "webview", "panedock-main.ts")).read(), "the kit's frame lookup reads it first")
        # the BUILT bundles are read by tests/test_pane_registry_served.py (TheBuiltBundles), which CI's browser job runs with the extension
        # built; here that leg skipped in every pytest cell and its pass was invisible (the 1919 read)

    def test_the_baked_maps_read_the_attribute(self):
        # executed in every CI cell (the 1922 read: these pins sat behind a dist gate that skipped them everywhere but a built checkout).
        # SOURCE pins on the parse-time reads, which now carry the generic panes the page ships with (the Artifacts record): the panes
        # defined at the kernel reach the same maps through the joins, executed in TheLanding (the go point's order and hooks) and in
        # TheInlineScripts above (the controller fed by the road)
        self.assertIn("PANE['f-'+p.id]=p.id+'-pane';COLS.push('f-'+p.id);", km._LANDING_FOCUS_JS, "the focus ring's map and column list")
        self.assertIn("if(!(p.id in PN))PN[p.id]=String(p.title||p.id);", km._LANDING_ERRS_JS, "the bell's titles")
        self.assertIn("F[p.id]=document.getElementById('f-'+p.id);", km._LANDING_MOBILE_JS, "the phone's frames")
        self.assertIn("var sf=F[p];if(mobileOn()&&window.__rompPaneToggle&&sf&&sf.getAttribute&&!sf.getAttribute('src')&&sf.getAttribute('data-src'))sf.setAttribute('src',sf.getAttribute('data-src'));", km._LANDING_MOBILE_JS,
                      "a phone shows a pane by its tab: the tap loads the shown pane's iframe once, generically (the 1922 read: a data pane's tab showed a blank pane), on a phone only and once the pane controller has parsed (its boot apply copies the current tab's frame)")
        self.assertIn("if(!btn)p='chat';", km._LANDING_MOBILE_JS, "a pane with no tab button falls to the chat, never a bare return (a stale remembered key)")
        self.assertIn("window.__rompPaneApply=apply;", km._LANDING_COLLAPSE_JS, "the controller's apply is re-run on the layout flip")
        self.assertIn("try{window.__rompPaneApply&&window.__rompPaneApply();}catch(e){}try{window.__rompPanesTell&&window.__rompPanesTell();}catch(e){}", km._LANDING_MOBILE_JS, "the media query's change event re-applies, then re-tells")
        self.assertIn("var load=mob?(tab===k&&(k in po)):!!po[k];", km._LANDING_COLLAPSE_JS, "on a phone a generic pane loads by its tab alone, never by the desktop flag")
        self.assertIn("KEYS[p.id+'-pane']=p.id;", km._LANDING_JS, "a data pane's grow key")
        self.assertIn("gutter('gv-'+p.id,function(){for(var j=i-1;j>=0;j--){if(document.body.classList.contains('po-'+key(seq[j])))return seq[j];}return lastChat();},me);", km._LANDING_JS,
                      "one gutter per data pane, its left neighbour the rightmost shown column before it")
        self.assertIn('var seq=["fleet-pane", "feed-pane", "waiting-pane", "files-pane"].concat(', km._LANDING_JS, "the hand-written columns (the fork's Waiting pane among them), then every generic pane (the Artifacts record, the data panes) from the attribute")


_RELOAD_STUB = r"""
// the browser the reload core thinks it runs in (tests/test_dashboard_auto_reload.py's harness, the members this scenario touches)
var LISTENERS = {}, STORE = {}, LOCAL = {}, RELOADS = 0, WLISTENERS = {};
var document = {
  createElement: function () { return { id: "", innerHTML: "", classList: { add: function () {}, remove: function () {} } }; },
  addEventListener: function (t, f) { (LISTENERS[t] = LISTENERS[t] || []).push(f); },
  getSelection: function () { return { rangeCount: 0, isCollapsed: true, toString: function () { return ""; } }; },
  hasFocus: function () { return true; },
  getElementById: function () { return null; },
  activeElement: null,
  body: { classList: { remove: function () {}, add: function () {} }, appendChild: function () {} },
  querySelectorAll: function () { return []; }
};
var _setTimeout = globalThis.setTimeout;
function setTimeout(f, ms) { if (ms > 0) return 1; return _setTimeout(f, ms); }
function clearTimeout() {}
var window = { addEventListener: function (t, f) { (WLISTENERS[t] = WLISTENERS[t] || []).push(f); } };
window.parent = window;
var location = { pathname: "/", reload: function () { RELOADS++; } };
var sessionStorage = { setItem: function (k, v) { STORE[k] = v; }, getItem: function (k) { return k in STORE ? STORE[k] : null; }, removeItem: function (k) { delete STORE[k]; } };
var localStorage = { setItem: function (k, v) { LOCAL[k] = v; }, getItem: function (k) { return k in LOCAL ? LOCAL[k] : null; }, removeItem: function (k) { delete LOCAL[k]; } };
function fetch() { return new Promise(function () {}); }
"""
_RELOAD_DRIVER = r"""
const R = window.__rompReload; const out = {};
out.before = R.offered();
if (R.notePanes) { R.notePanes(__PV0__); out.same = R.offered(); R.notePanes('abc123'); out.moved = R.offered(); }
else { out.same = null; out.moved = null; }
out.reloaded = RELOADS > 0;
console.log(JSON.stringify(out));
"""

# the two offers side by side (the 1919 read: one seen.code slot, so the panes offer and the build offer overwrote each other's
# standing offer on every keepalive, and a declined build was re-offered once a panes offer had been declined too)
_RELOAD_TWO_DRIVER = r"""
const R = window.__rompReload; const out = {};
R.noteVersion({ code_ident: 'C1' }); out.build = R.offered();
R.behind(); out.behind = R.offered();
R.notePanes('B'); out.panesBeside = R.offered();            // the pane set moved too: the standing BUILD offer keeps its words, and carries the revision
R.noteVersion({ code_ident: 'C1' }); out.buildAgain = R.offered();   // nothing new: the same offer stands
R.notePanes('B'); out.panesAgain = R.offered();
R.dismiss(); out.declined = R.offered();                    // Not now: covers the build AND the revision it was made against
R.noteVersion({ code_ident: 'C1' }); out.buildAfterDecline = R.offered();
R.notePanes('B'); out.panesAfterDecline = R.offered();
R.notePanes('C'); out.newRevision = R.offered();            // a NEW revision is new information: offered, with the panes words alone? no: the build is still new beside it
console.log(JSON.stringify(out));
"""

_RELOAD_PANES_ONLY_DRIVER = r"""
const R = window.__rompReload; const out = {};
R.notePanes('B'); out.panes = R.offered();                  // the revision the sole new information: the panes words
R.dismiss(); R.notePanes('B'); out.declined = R.offered();  // declined, the same revision offers nothing
R.notePanes('C'); out.moved = R.offered();                  // another revision offers again
console.log(JSON.stringify(out));
"""


if __name__ == "__main__":
    unittest.main()
