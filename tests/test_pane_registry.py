#!/usr/bin/env python3
"""The pane registry (plans/panes-as-data.md, phase one). A pane is a record in ONE schema: the shipped panes are the
kernel's code constants (_CODE_PANES, checked at import by _pane_check like the code boards), every other pane a JSON document
under STATE/panes/<id>.json behind define_pane (the board door's twin: POST /pane, GET /panes, `romp pane`). The shell renders
from _pane_order() per request, and the FIRST pin is that with an empty registry the code panes' RENDERING is unchanged: the
body tag, the rail, the phone tabs, the pane row, the column and gutter rules and the gutter calls, slice for slice against
the base kernel's rendering (tests/fixtures/landing-code-panes.json, tests/landing_slices.py). A data pane gets a rail
button, a phone tab (none when experimental), a lazy iframe (data-src), its column and gutter rules and a row in
body[data-panes] that the baked inline scripts read; a URL source is a plain sandboxed iframe with no token, no ?v= and no
protocol, and every shell listener, inline and bundled, drops a message that is not a protocol pane's own (the source
check, fail-closed). The pane set's revision rides every keepalive beside the build token and a page baked with another is
offered a reload.

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


def _rows(*defs):
    """The body attribute's rows for these data records (what the inline scripts read): the shipped Artifacts record first (the
    generic build renders every pane after the hand-written five), then the data panes by id."""
    return [ARTIFACTS_ROW] + [{"id": d["id"], "title": d["title"], "protocol": d["protocol"], "experimental": d["experimental"], "on": d["on"], "builtin": False}
                              for d in sorted((_full(x) for x in defs), key=lambda r: r["id"])]


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


# the pane-title-and-id sink census
# A pane title is free text within one line (_pane_check bounds its length and refuses a control character, a line or
# paragraph separator and an unpaired surrogate), so it may still hold a quote or a backslash. Every served output that
# carries a title must escape it for that output's context, or the title breaks the output (a shim that does not parse, a
# LABEL that is not the title). A pane id is confined to [a-z][a-z0-9_-] by the whole-string rule (_PANE_ID_RE, matched
# whole with fullmatch; the pattern keeps $, which ports to a JavaScript RegExp), so once that rule holds the id is inert
# in every sink it reaches. These helpers derive the title-reader population from the live source and run the served shim
# through node.
def _title_sites(src):
    """Every place a title is read to classify, derived from the live kernel source with ast (so string escapes and
    docstrings are decoded, never grepped), keyed by the nearest enclosing def (a nested function or a method by its own
    name; <module> for a module-level read): the _pane_label CALL sites and the ["title"] SUBSCRIPT reads. The nearest-def
    keying is the stricter choice: a new nested reader under a classified parent is filed under its OWN name and turns the
    census red, rather than being absorbed into the parent. The limit it keeps: a new nested def that REUSES a classified
    name is filed under that name and passes. The subscript walk reads ANY ["title"] on any record (a pane, a board, a
    goal), not only a pane record: over-reading a non-pane title read is the census's safe side, since it classifies the
    reader rather than mistaking it for a pane sink. The census asserts this is the classified set, so a NEW title reader
    (a new sink) under a new or an unclassified name fails it. Two forms this census does not read (stated limits): a title
    read spelled .get("title"), and a whole-record serialization that carries the title without naming it (a json.dumps of
    a pane or board record). The JSON API routes take the second form: GET /panes, GET /boards, the POST /pane and /board
    echoes and the /feed.json board frame serialize dict(d, ...) per record, title included, and serve application/json,
    where json.dumps escapes the title for that context, so they are inert. Every title reader in the live tree that places
    the title into an HTML or JavaScript context does so as a subscript or through _pane_label."""
    tree = ast.parse(src)
    label_calls, title_reads = set(), set()

    def walk(node, fn):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_pane_label":
            label_calls.add(fn)
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and node.slice.value == "title":
            title_reads.add(fn)
        cur = node.name if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else fn
        for child in ast.iter_child_nodes(node):
            walk(child, cur)

    walk(tree, "<module>")
    return label_calls, title_reads


_SHIM_PROBE_NODE = r"""
const fs = require('fs'), vm = require('vm');
const shim = fs.readFileSync(process.argv[2], 'utf8');
const out = {};
try { new vm.Script(shim, { filename: 'shim.js' }); out.parses = true; }   // a SyntaxError (a title's newline or trailing backslash) is caught here
catch (e) { out.parses = false; out.parseErr = String(e); }
if (out.parses) {
  const i = shim.indexOf('var APP='), j = shim.indexOf('var lastRecv=0;', i);
  if (i < 0 || j < 0) { out.declErr = 'markers missing'; }
  else {
    const decls = shim.slice(i, j);   // the baked var declarations: all literals, self-contained
    try { const ctx = {}; vm.runInNewContext(decls + '\nthis.__L = LABEL; this.__A = APP;', ctx); out.label = ctx.__L; out.app = ctx.__A; }
    catch (e) { out.declErr = String(e); }   // a title's quote closes the string and runs code: the throw lands here
  }
}
process.stdout.write(JSON.stringify(out));
"""


def _shim_probe(shim):
    """Run the served shim through node and read back whether it PARSES (no SyntaxError) and the APP and LABEL it
    evaluates to. {"parses": bool, optional "parseErr"/"declErr", "label", "app"}."""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as rf:
        rf.write(_SHIM_PROBE_NODE); runner = rf.name
    with tempfile.NamedTemporaryFile("w", suffix=".shim.js", delete=False) as sf:
        sf.write(shim); shimf = sf.name
    try:
        r = subprocess.run(["node", runner, shimf], capture_output=True, text=True, timeout=30)
    finally:
        os.unlink(runner); os.unlink(shimf)
    assert r.returncode == 0, "the shim probe threw: " + r.stderr[:1500]
    return json.loads(r.stdout.strip().splitlines()[-1])


def _proto_id_names():
    """The own-property names of JavaScript's Object.prototype that match the kernel's id rule, DERIVED by running node
    over the live pattern rather than hand-listed: Object.getOwnPropertyNames(Object.prototype) filtered by
    _PANE_ID_RE.pattern (today only "constructor"; the others carry capitals and fail [a-z][a-z0-9_-]). An id in this set
    is a name present on every plain object through the prototype chain, so it is not inert where the landing reads a pane
    id as an object key."""
    js = ("const re = new RegExp(process.argv[1]);"
          "process.stdout.write(JSON.stringify("
          "Object.getOwnPropertyNames(Object.prototype).filter(n => re.test(n))));")
    r = subprocess.run(["node", "-e", js, km._PANE_ID_RE.pattern], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, "the prototype-name probe threw: " + r.stderr[:1500]
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
        _lacks(self, " data-protocol=none sandbox=", h0); _lacks(self, "id=gv-notes", h0); _lacks(self, "/pane/", h0)
        self.w.seed(NOTES)
        h1 = km._landing()
        self.assertTrue(h1 != h0, "a pane file changes the page"); self.assertEqual([r["id"] for r in _attr_rows(h1)], ["artifacts", "notes"])
        s1 = slices(h1)
        self.assertTrue(s1["body_tag"] != got["body_tag"] and s1["rail_buttons"] != got["rail_buttons"], "the body tag and the rail carry the pane")
        self.w.unseed("notes")
        self.assertTrue(km._landing() == h0, "define then remove: the bytes are back")

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

    def _status(self, path, token=True):
        # the served status alone (200 when the landing builds, 500 when it cannot), no body read: the GET / check below
        # needs only the code, and reading no response body keeps the served-page reader census from counting this as a
        # page read (its helper-return follow gives a status-only return the empty set, so this call is no fetch to it)
        headers = {}
        if token:
            headers["X-Romp-Token"] = km.TOKEN
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code

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

    def test_an_id_with_a_trailing_newline_is_refused_at_every_install_road(self):
        # _PANE_ID_RE is matched whole with fullmatch: it refuses an id whose only extra character is a terminal newline,
        # which the old plain-$ match admitted (re.match with $ stops before a terminal \n). An id ending in a newline
        # otherwise reached the landing's unquoted attributes and CSS selectors raw (data-pane=, id=gv-, #<id>-pane). All
        # three install roads funnel through _pane_check and are exercised below, not read from the source: POST /pane and
        # the CLI door (bin/romp POSTs to /pane) both reach define_pane -> _pane_check, and a direct file write is governed
        # by the re-check _panes_snapshot runs on every file it reads. The refusal asserted is the ID RULE'S OWN reason
        # ("a lowercase word"), not the generic "id must" prefix the one-line rule also carries: reverting fullmatch to
        # match at the _pane_check site would let the id pass the regex and be caught instead by the one-line loop (an
        # "id must be one line of text" reason), which a bare "id must" assertion would miss.
        self.assertIsNone(km._pane_check({"id": "ab", "source": "/feed"})[1], "a normal id passes")
        for road, (defn, err) in (("_pane_check", km._pane_check({"id": "ab\n", "source": "/feed"})),
                                  ("define_pane", km.define_pane({"id": "ab\n", "source": "/feed"}))):
            self.assertIsNone(defn, road); self.assertIn("lowercase word", err or "", road)
        st, r = self._call("/pane", {"id": "ab\n", "source": "/feed"})
        self.assertEqual((st, r.get("ok")), (200, False), r); self.assertIn("lowercase word", r.get("error", ""))
        # the other fullmatch site: _pane_source_kind matches the id after "pane:" whole too, so pane:ab\n is not a state
        # source (a bare match with $ would have admitted it); a clean pane:<id> still reads as one.
        self.assertIsNone(km._pane_source_kind("pane:ab\n"), "pane:<id> is checked whole: a trailing newline is not a state source")
        self.assertEqual(km._pane_source_kind("pane:ab"), "state", "a clean pane:<id> still reads as a state source")
        # the direct-file road: a file whose id and name both end in a newline is read back and re-checked; refused, so
        # it never joins the pane set (at the base _pane_check accepted it and the matching name let it render). The
        # skipped file is named ONCE on stderr with its path repr'd, so a name holding a newline is one readable line
        # ending in a quoted "...\n.json", never split across two lines (the raw path would break the line in two).
        self.w.seed(NOTES)
        (self.w.pdir / "dnl\n.json").write_text(json.dumps(_full({"id": "dnl\n", "source": "/feed", "on": True})) + "\n")
        self.w.reset_memos()
        errs = io.StringIO()
        with contextlib.redirect_stderr(errs):
            data = km._panes_data()
        self.assertNotIn("dnl\n", data, "the disk re-check refuses the newline id"); self.assertNotIn("dnl", data)
        self.assertIn("notes", data, "a valid pane beside it still renders")
        self.assertEqual(len([ln for ln in errs.getvalue().splitlines() if ln.strip()]), 1,
                         "the skipped file is one stderr line, not split by the newline in its name: %r" % errs.getvalue())
        panes_lines = [ln for ln in errs.getvalue().splitlines() if "[panes] " in ln]
        self.assertEqual(len(panes_lines), 1, "one [panes] line names the skipped file: %r" % panes_lines)
        self.assertIn(repr(str(self.w.pdir / "dnl\n.json")), panes_lines[0],
                      "the path is repr'd, so the newline in the name is \\n inside one quoted token: %r" % panes_lines[0])

    def test_a_title_or_source_that_is_not_one_line_of_text_is_refused_at_every_install_road(self):
        # a title, an id and a source are each one line of text: _pane_check refuses a control character (Cc, the newline
        # included), a line or paragraph separator (U+2028/U+2029) and an unpaired surrogate (a code point that does not
        # encode to UTF-8), naming the field, the CLASS found, the offending code point and the POSITION (1-based: the
        # first character is position 1). Such a title otherwise rode the shim's LABEL and the landing's title sinks, and
        # an unpaired surrogate there served a 500 for the whole landing (the next test); a newline in a title folded the
        # bell row. The refused set is DERIVED from the predicate, not sampled: a high and a low surrogate, both
        # separators, and the control class (the start, DEL and a C1), with the offense at a different INDEX per form so a
        # constant-index reason is caught; every Cc code point is also driven through _pane_check so a predicate that
        # hard-codes a few controls still reds. Each form is refused at each install road (_pane_check, define_pane, POST
        # /pane and the disk re-check), and the allowed side (an accent, an emoji, CJK, a combining mark, a quote, a
        # backslash) is accepted on each road and joins the pane set when seeded. Red at the base and at the PR's first
        # head (nothing refused), on the separator form at this head (its cause was misnamed), and under a predicate that
        # refuses every non-ASCII character (the allowed side).
        def reason(field, s, idx, cause):
            return "%s must be one line of text (%s, U+%04X, at position %d)" % (field, cause, ord(s[idx]), idx + 1)
        # (name, title, 0-based offense index, cause): the index varies (0, 1, 2, 3) to kill a constant-position reason
        forms = [("a control character at the start", "\x01ab", 0, "a control character"),
                 ("a high surrogate", "x\ud800y", 1, "an unpaired surrogate"),
                 ("a low surrogate", "x\udc00y", 1, "an unpaired surrogate"),
                 ("a line separator", "ab\u2028c", 2, "a line or paragraph separator"),
                 ("a paragraph separator", "abc\u2029", 3, "a line or paragraph separator"),
                 ("DEL", "x\x7fy", 1, "a control character"),
                 ("a C1 control (NEL)", "x\x85y", 1, "a control character")]
        self.w.seed(NOTES)
        for name, title, idx, cause in forms:
            want = reason("title", title, idx, cause)
            for road, (defn, err) in (("_pane_check", km._pane_check({"id": "ab", "title": title, "source": "/feed"})),
                                      ("define_pane", km.define_pane({"id": "ab", "title": title, "source": "/feed"}))):
                self.assertIsNone(defn, (name, road)); self.assertIn(want, err or "", (name, road))
            st, r = self._call("/pane", {"id": "ab", "title": title, "source": "/feed"})
            self.assertEqual((st, r.get("ok")), (200, False), (name, r)); self.assertIn(want, r.get("error", ""), (name, r))
            # the disk re-check: a file carrying the bad title is read back and re-checked, so it never joins the pane set
            (self.w.pdir / "bad.json").write_text(json.dumps(_full({"id": "bad", "title": title, "source": "/feed", "on": True})) + "\n")
            self.w.reset_memos()
            errs = io.StringIO()
            with contextlib.redirect_stderr(errs):
                data = km._panes_data()
            self.assertNotIn("bad", data, (name, "the disk re-check refuses it"))
            self.assertIn(want, errs.getvalue(), (name, "the skipped-file line names the cause and position"))
            self.assertIn("notes", data, "a valid pane beside it still renders")
            self.w.unseed("bad")
        # a URL source carrying each form is refused too (it otherwise rode the iframe's data-src attribute), named with
        # the source field, the cause, the code point and the position (the offense sits at index 16 after "http://TESTHOST/")
        base = "http://TESTHOST/"
        for name, _title, _idx, cause in forms:
            bad = _title[_idx]
            src = base + bad
            defn, err = km._pane_check({"id": "ab", "title": "T", "source": src})
            self.assertIsNone(defn, name); self.assertIn(reason("source", src, len(base), cause), err or "", name)
        # every Cc code point is refused at _pane_check (cheaply, no road), so a predicate hard-coding a few controls reds
        for cp in list(range(0x00, 0x20)) + [0x7f] + list(range(0x80, 0xa0)):
            defn, err = km._pane_check({"id": "ab", "title": "a" + chr(cp) + "b", "source": "/feed"})
            self.assertIsNone(defn, "Cc U+%04X refused" % cp)
            self.assertIn("a control character", err or "", "Cc U+%04X named a control character" % cp)
        # the ALLOWED side: an accent, an emoji, CJK, a combining mark, a quote and a backslash are one line of text,
        # accepted on each road and joined to the pane set when seeded (red under a predicate that refuses every
        # non-ASCII character: the accent, emoji, CJK and combining mark would be refused)
        allowed = [("an accent", "Caf\u00e9"), ("an emoji", "a\U0001f600b"), ("CJK", "a\u4e2db"),
                   ("a combining mark", "e\u0301"), ("a quote", 'a"b'), ("a backslash", "a\\b")]
        for name, title in allowed:
            for road, (defn, err) in (("_pane_check", km._pane_check({"id": "ok", "title": title, "source": "/feed"})),
                                      ("define_pane", km.define_pane({"id": "ok", "title": title, "source": "/feed"}))):
                self.assertIsNone(err, (name, road)); self.assertEqual(defn["title"], title, (name, road))
            st, r = self._call("/pane", {"id": "ok", "title": title, "source": "/feed"})
            self.assertEqual((st, r.get("ok")), (200, True), (name, r)); self.assertEqual(r["pane"]["title"], title, (name, r))
            (self.w.pdir / "ok.json").write_text(json.dumps(_full({"id": "ok", "title": title, "source": "/feed", "on": True})) + "\n")
            self.w.reset_memos()
            with contextlib.redirect_stderr(io.StringIO()):
                data = km._panes_data()
            self.assertIn("ok", data, (name, "a seeded file with the allowed title joins the pane set"))
            self.assertEqual(data["ok"]["title"], title, (name, data.get("ok")))
            self.w.unseed("ok")

    def test_a_seeded_lone_surrogate_title_leaves_the_landing_at_200(self):
        # a pane already on disk with a title that does not encode to UTF-8 (a lone surrogate) is refused at the disk
        # re-check, so it never reaches the landing. At the base and at the PR's first head _pane_check accepted it, the
        # title rode _rail_buttons_html/_mtab_buttons_html through _html_esc unchanged, and _send's strict
        # body.encode('utf-8') then raised, so GET / served a 500 for every viewer until the pane was removed.
        self.w.seed(NOTES)
        (self.w.pdir / "sur.json").write_text(json.dumps(_full({"id": "sur", "title": "x\ud800y", "source": "/feed", "on": True})) + "\n")
        self.w.reset_memos()
        with contextlib.redirect_stderr(io.StringIO()):
            st = self._status("/")
        self.assertEqual(st, 200, "the landing stays at 200: the surrogate title is refused at the disk re-check, not served")

    def test_an_id_that_is_an_object_prototype_name_is_refused_at_every_install_road(self):
        # an id that is an own-property name of JavaScript's Object.prototype AND matches the id rule (today
        # "constructor") is refused: the landing reads a pane id as a plain-object key, and the prototype answers for such
        # a name even with no pane stored. The set is DERIVED by running node over the live pattern (not hand-listed
        # here), and must be non-empty or the pin proves nothing. Red at the BASE (0cfb961f0), where "constructor" is
        # accepted at every road. At the PR's earlier heads the pattern still ended in \Z, which node's RegExp reads as a
        # literal Z, so _proto_id_names() derived no name there and the non-empty guard below reds first, before the road
        # checks are reached.
        names = _proto_id_names()
        self.assertIn("constructor", names, "node derives constructor as an Object.prototype name matching the id rule")
        self.w.seed(NOTES)
        for pid in names:
            for road, (defn, err) in (("_pane_check", km._pane_check({"id": pid, "source": "/feed"})),
                                      ("define_pane", km.define_pane({"id": pid, "source": "/feed"}))):
                self.assertIsNone(defn, (pid, road)); self.assertIn("Object.prototype", err or "", (pid, road))
            st, r = self._call("/pane", {"id": pid, "source": "/feed"})
            self.assertEqual((st, r.get("ok")), (200, False), (pid, r)); self.assertIn("Object.prototype", r.get("error", ""), (pid, r))
            (self.w.pdir / (pid + ".json")).write_text(json.dumps(_full({"id": pid, "source": "/feed", "on": True})) + "\n")
            self.w.reset_memos()
            with contextlib.redirect_stderr(io.StringIO()):
                data = km._panes_data()
            self.assertNotIn(pid, data, (pid, "the disk re-check refuses it"))
            self.w.unseed(pid)

    def test_define_replaces_a_pane_whole_remove_deletes_it_and_a_shipped_or_unknown_id_is_refused(self):
        st, r = self._call("/pane", NOTES); self.assertEqual((st, r.get("ok")), (200, True), r); self.assertEqual(r["pane"], _full(NOTES))
        rev = r["rev"]
        self.assertEqual(json.loads((self.w.pdir / "notes.json").read_text()), _full(NOTES), "the file holds the filled record, not the request")
        st, r = self._call("/panes"); self.assertEqual([p["id"] for p in r["panes"]], SHIPPED_IDS + ["notes"]); self.assertEqual(r["rev"], rev)
        self.assertEqual([p["builtin"] for p in r["panes"]], [True] * len(SHIPPED) + [False])
        self.assertEqual({k: v for k, v in r["panes"][len(SHIPPED)].items() if k != "builtin"}, _full(NOTES))
        st, r = self._call("/pane", dict(NOTES, title="Notebook")); self.assertEqual((st, r["ok"]), (200, True))
        self.assertEqual(_rail(km._landing())[-1], ("notes", "Notebook"), "a define replaces the pane whole and the rail says so")
        self._call("/pane", DOCS); self._call("/pane", LAB)
        st, r = self._call("/panes"); self.assertEqual([p["id"] for p in r["panes"]], SHIPPED_IDS + ["docs", "lab", "notes"], "data panes by id after the shipped panes")
        st, r = self._call("/pane", {"remove": "chat"}); self.assertEqual((st, r["ok"]), (200, False)); self.assertIn("shipped", r["error"])
        st, r = self._call("/pane", {"remove": "scratch"}); self.assertEqual((st, r["ok"]), (200, False)); self.assertIn("no pane", r["error"])
        for i in ("notes", "docs"):
            st, r = self._call("/pane", {"remove": i}); self.assertEqual((st, r["ok"]), (200, True))
        st, r = self._call("/pane", {"remove": "lab"}); self.assertEqual((st, r), (200, {"ok": True, "rev": "0"}))
        self.assertFalse((self.w.pdir / "notes.json").exists())
        st, r = self._call("/panes"); self.assertEqual([p["id"] for p in r["panes"]], SHIPPED_IDS)

    def test_remove_clears_a_record_the_current_schema_skips_by_its_file(self):
        # a record the base accepted but the stricter schema now SKIPS (an id that is an Object.prototype name, a title
        # with a control character, an id ending in a newline) is not in the pane set, so a remove gating on the pane set
        # alone could never clear it: the file stayed on disk, named on stderr at each listing, gone from the dashboards
        # but unremovable by any road. remove_pane now finds it by its FILE (a pid with no path separator whose <pid>.json
        # is a file directly under the panes directory) and unlinks it even when the snapshot skipped it. A pid holding a
        # path separator (a traversal like "../evil") never names a file here and stays refused. Red at this head, where
        # remove gates on _panes_data() alone.
        self.w.seed(NOTES)
        self.w.pdir.mkdir(parents=True, exist_ok=True)
        (self.w.pdir / "constructor.json").write_text(json.dumps(_full({"id": "constructor", "source": "/feed", "on": True})) + "\n")
        (self.w.pdir / "tabbed.json").write_text(json.dumps(_full({"id": "tabbed", "title": "a\tb", "source": "/feed", "on": True})) + "\n")
        (self.w.pdir / "dnl\n.json").write_text(json.dumps(_full({"id": "dnl\n", "source": "/feed", "on": True})) + "\n")
        self.w.reset_memos()
        with contextlib.redirect_stderr(io.StringIO()):
            data = km._panes_data()
        for skipped in ("constructor", "tabbed", "dnl\n"):
            self.assertNotIn(skipped, data, "%r is skipped by the stricter schema" % skipped)
        # the in-process door clears a skipped record by its file
        ok, err = km.remove_pane("constructor")
        self.assertEqual((ok, err), (True, None), "the door removes a skipped record by its file")
        self.assertFalse((self.w.pdir / "constructor.json").exists(), "constructor.json is gone")
        # the POST /pane {remove} road (the CLI POSTs the same body) clears another
        self.w.reset_memos()
        st, r = self._call("/pane", {"remove": "tabbed"})
        self.assertEqual((st, r.get("ok")), (200, True), r)
        self.assertFalse((self.w.pdir / "tabbed.json").exists(), "tabbed.json is gone")
        # the trailing-newline id's file is removed too (match(), not fullmatch(), would miss it: it is reached by file)
        ok, err = km.remove_pane("dnl\n")
        self.assertEqual((ok, err), (True, None), "the trailing-newline id's file is removed")
        self.assertFalse((self.w.pdir / "dnl\n.json").exists(), "the trailing-newline file is gone")
        # a traversal pid never names a file under the panes directory: a file beside it is untouched and the remove refused
        (km.jd.STATE / "evil.json").write_text("{}")
        self.w.reset_memos()
        ok, err = km.remove_pane("../evil")
        self.assertEqual(ok, False, "a traversal id is refused"); self.assertIn("no pane", err or "")
        self.assertTrue((km.jd.STATE / "evil.json").exists(), "the file outside the panes directory is untouched")
        (km.jd.STATE / "evil.json").unlink()

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

    def test_a_pane_file_written_by_hand_renders_a_bad_one_is_skipped_and_named_once_and_a_rewrite_in_place_is_read(self):
        self.w.seed(NOTES)
        self.assertEqual(_rail(km._landing())[-1], ("notes", "Notes"), "the directory is the registry: a file the door would write renders")
        (self.w.pdir / "bad.json").write_text("{")
        (self.w.pdir / "other.json").write_text(json.dumps(_full(dict(NOTES, id="notes2"))))   # names another pane than its file
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rail = _rail(km._landing()); km._landing()
        self.assertEqual([k for k, _ in rail], SHIPPED_IDS + ["notes"], "a bad file is skipped, never rendered")
        lines = [ln for ln in err.getvalue().splitlines() if "[panes]" in ln]
        self.assertEqual(len(lines), 2, "each bad file is named once, on stderr, however many builds: %r" % lines)
        self.assertTrue(any("bad.json" in ln for ln in lines) and any("other.json" in ln and "notes2" in ln for ln in lines), lines)
        # an in-place rewrite (an editor, a shell redirection) moves the file's stat: the next build reads it
        fp = self.w.pdir / "notes.json"
        fp.write_text(json.dumps(_full(dict(NOTES, title="Notebook"))))
        st = os.stat(fp); os.utime(fp, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000))
        self.assertEqual(_rail(km._landing())[-1], ("notes", "Notebook"))

    def test_the_landing_and_the_shim_bake_the_revision_of_the_one_listing_their_build_read(self):
        # the 1919 read: _landing listed the registry once for its builders and _stale_block listed it again through _reload_core,
        # so a define landing between the two baked the new revision into a page showing the old set, which was never offered a reload
        self.assertIn('PANES0="abc"', km._reload_core(3, pv="abc"), "the reload core bakes the revision it is handed")
        self.assertIn('PANES0="%s"' % km._panes_rev(), km._reload_core(3), "and this kernel's when handed none")
        src = inspect.getsource(km._landing)
        self.assertIn("snap = _panes_snapshot()", src); self.assertIn('panes = _pane_order(snap["data"]); pv = snap["rev"]', src, "one listing: the list and the revision from it")
        self.assertIn("_stale_block(v, pv)", src, "the reload core takes that revision")
        self.assertIn("def _stale_block(v, pv=None):", KSRC); self.assertIn("def _shim(app, v=0, caps=\"\", no_stale=False, pv=None, data=None):", KSRC)   # caps: the fork's wire capabilities a page announces; pv and data: upstream 1919/1952

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

    def test_one_listing_per_build_executed_a_define_forced_between_the_former_reads_changes_neither_the_set_nor_the_baked_revision(self):
        # the 1952 read (round two): the one-listing item was pinned by source strings alone; here the listing is HOOKED: the first
        # snapshot call defines a second record after it returns, so a build that listed again would render or bake the new set.
        # The landing: one call, the rows the first snapshot's, PANES0 its revision, one PANES0 occurrence. The shim: the route's
        # snapshot handed through, no further call, PANES0 and LOADEDPV equal; _shim handed nothing reads once and bakes both from it.
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
                self.w.seed(DOCS)   # a define landing between two listings, if a build made two
            return snap
        km._panes_snapshot = hooked
        try:
            html = km._landing()
        finally:
            km._panes_snapshot = real
        self.assertEqual(len(calls), 1, "one listing per landing build: %r" % calls)
        rows = json.loads(html_mod.unescape(re.search(r' data-panes="([^"]*)"', html).group(1)))
        self.assertEqual([r["id"] for r in rows if not r.get("builtin")], ["notes"], "the rendered set is the first snapshot's (the define landed after it): %r" % rows)
        self.assertEqual(html.count('PANES0="'), 1, "one baked revision on the page")
        self.assertIn('PANES0="%s"' % calls[0], html, "the reload core's revision is the same snapshot's")
        self.w.unseed("docs")
        # _shim handed no revision: ONE read, both slots from it
        calls.clear()
        km._panes_snapshot = hooked
        try:
            direct = km._shim("notes", 3)
        finally:
            km._panes_snapshot = real
        self.assertEqual(len(calls), 1, "one read when handed none: %r" % calls)
        self.assertIn('PANES0="%s"' % calls[0], direct); self.assertIn('var LOADEDPV="%s";' % calls[0], direct)
        self.w.unseed("docs")
        self.assertIn('var LOADEDPV="abc";', km._shim("notes", 3, pv="abc"), "handed a revision, the shim's gate bakes it too")

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


# ── the landing with data panes ───────────────────────────────────────────────────────────────────────────────────
class TheLanding(unittest.TestCase):
    def setUp(self): self.w = World()
    def tearDown(self): self.w.close()

    def test_a_data_pane_renders_a_rail_button_a_tab_a_lazy_iframe_its_rules_and_the_attribute(self):
        self.w.seed(NOTES, DOCS, LAB)
        page = km._landing()
        self.assertEqual(_rail(page), [(i, t) for i, t, _ in SHIPPED] + [("docs", "Docs"), ("lab", "Lab"), ("notes", "Notes")], "the shipped panes, then the data panes by id")
        _has(self, "<button data-pane=notes>Notes</button>", page, "a phone tab")
        _has(self, "<button data-pane=docs>Docs</button>", page)
        _lacks(self, "data-pane=lab>Lab</button>", page, "an experimental pane has no phone tab")
        _has(self, '<div class=gv id=gv-notes></div><div class=pane id=notes-pane><iframe id=f-notes data-src="/pane/notes/" data-protocol=romp></iframe></div>', page,
             "a state-root pane loads /pane/<id>/ when shown (data-src, the optional panes' rule)")
        _has(self, '<div class=gv id=gv-docs></div><div class=pane id=docs-pane><iframe id=f-docs data-src="http://TESTHOST:9/docs/" data-protocol=none sandbox="allow-scripts allow-forms allow-popups"></iframe></div>', page,
             "a URL pane: the URL as given (no ?v=, no token), sandboxed, marked protocol none")
        _has(self, '<iframe id=f-lab data-src="/feed" data-protocol=romp></iframe>', page, "a kernel route as given")
        # the data panes' gutters through _at: only this seeded render carries them (the helper's comment says why)
        self.assertLess(page.index("id=artifacts-pane"), _at(page, "id=gv-docs")); self.assertLess(_at(page, "id=gv-docs"), _at(page, "id=gv-notes"))
        self.assertLess(_at(page, "id=gv-notes"), page.index("<div id=gv-ghost>"), "the data panes sit in the pane row, after the shipped columns")
        _has(self, "#notes-pane{flex:var(--g-notes,40) 1 0}body:not(.po-notes) #notes-pane{display:none}", page)
        # .po-waiting: the fork's Waiting pane is a shipped column, so the records put it in each data gutter's chain (fold 4, slice 2)
        _has(self, "body:not(.po-docs) #gv-docs,body:not(.po-chat):not(.po-fleet):not(.po-feed):not(.po-waiting):not(.po-files):not(.po-artifacts) #gv-docs{display:none}", page,
             "the first data gutter hides with its pane off or with no shown column before it (the shipped columns from the records)")
        _has(self, "body:not(.po-notes) #gv-notes,body:not(.po-chat):not(.po-fleet):not(.po-feed):not(.po-waiting):not(.po-files):not(.po-artifacts):not(.po-docs):not(.po-lab) #gv-notes{display:none}", page)
        # the hand panes' phone block carries the fork's Waiting pane between the feed and the files (fold 4, slice 2)
        mob = page[page.index("#chat-pane,#fleet-pane,#feed-pane,#waiting-pane,#files-pane,#tl-pane{display:contents!important}"):]
        _has(self, "#artifacts-pane,#docs-pane,#lab-pane,#notes-pane{display:contents!important}#f-artifacts.m-on,#f-docs.m-on,#f-lab.m-on,#f-notes.m-on{display:block}", mob[:600],
             "the phone's rules for the generic panes ride the media block beside the hand five's: the tab, not the po flag, says which pane shows, and the shown tab's iframe displays")
        self.assertEqual(_attr_rows(page), _rows(NOTES, DOCS, LAB), "the attribute carries what the inline scripts and the pane bundles read, never the source")
        n_scripts = page.count("<script>")
        self.w.unseed("notes", "docs", "lab")
        self.assertEqual(n_scripts, km._landing().count("<script>"), "no inline script is added for a data pane: the baked ones read the attribute")

    def test_a_title_is_escaped_in_the_rail_the_tab_and_the_attribute(self):
        self.w.seed({"id": "x", "title": "A <b>&", "source": "/feed", "on": True})
        page = km._landing()
        _has(self, "<div class=rail-btn data-pane=x>A &lt;b&gt;&amp;</div>", page)
        _has(self, "<button data-pane=x>A &lt;b&gt;&amp;</button>", page)
        attr = re.search(r"data-panes=\"([^\"]*)\"", page).group(1)
        self.assertNotIn("<", attr); self.assertNotIn('"', attr)
        self.assertEqual(next(r["title"] for r in _attr_rows(page) if r["id"] == "x"), "A <b>&")


# ── the inline scripts read the attribute; the source check ─────────────────────────────────────────────────────────
_PANES_STUB = r"""
'use strict';
const ATTR = __ATTR__;
const KEYS = ['chat','timeline','fleet','feed','files'].concat(__DATA_IDS__);   // the hand five; the Artifacts record rides the rows like a data pane (the 1922 read: hand-listed too, it was built twice)
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
  querySelectorAll: (sel) => { if (sel === '.rail-btn[data-pane]') return KEYS.map((k) => BTNS[k]); const m = /data-pane=([\w-]+)/.exec(sel); return m && BTNS[m[1]] ? [BTNS[m[1]]] : []; },
  getElementById: (id) => frames[id] || null,
};
window.__rompMobileOn = () => MOBILE;
window.__rompMobileTab = (t) => { TABS.push(t); TAB = t; };
__SEED__
"""

# the ON-SCREEN gate, executed (the 1922 read: no row was enabled in the gear while off screen, the one state in which the gate acts,
# so a mutant copying src for every enabled generic pane passed the harness): the gear has the Artifacts pane enabled and a
# non-experimental data pane is on:false; at boot neither loads; the rail toggle loads each
_GATE_DRIVER = r"""
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


def _stub(rows, seed=""):
    """The pane controller's DOM stub for `rows` (the body attribute as the landing carries it), with `seed` run before the script."""
    return (_PANES_STUB.replace("__ATTR__", json.dumps(json.dumps(rows))).replace("__DATA_IDS__", json.dumps([r["id"] for r in rows]))
            .replace("__PROTO__", json.dumps({r["id"]: r["protocol"] for r in rows})).replace("__SEED__", seed))


class TheInlineScripts(unittest.TestCase):
    def setUp(self): self.w = World()
    def tearDown(self): self.w.close()

    def test_the_pane_controller_shows_a_data_pane_by_its_flag_hides_an_experimental_one_until_the_gear_asks_and_tells_no_url_pane(self):
        rows = _rows(NOTES, DOCS, LAB)   # the attribute as the landing carries it, for the executed script
        stub = _stub(rows)
        r = _run(stub + km._LANDING_COLLAPSE_JS + _PANES_DRIVER)
        b = r["boot"]
        self.assertTrue(b["notes"], "on: true puts the pane on screen at boot: %r" % b)
        self.assertEqual(b["notesSrc"], "/notes", "a shown data pane's iframe gets its src (the optional panes' rule)")
        self.assertFalse(b["notesHidden"]); self.assertTrue(b["docs"], b)
        self.assertFalse(b["lab"]); self.assertTrue(b["labHidden"], "experimental: not in this dashboard until the gear's row asks")
        self.assertIsNone(b["labSrc"], "an experimental pane never loads until asked for")
        self.assertEqual(b["told"], {"chat": True, "timeline": True, "fleet": False, "feed": True, "waiting": False, "files": False, "docs": True, "notes": True},
                         "the broadcast names the data panes beside the shipped ones (the experimental ones, the Artifacts record and the lab pane, are not in this dashboard until the gear asks)")
        self.assertEqual(b["docsTold"], 0, "a URL pane (protocol none) is told nothing")
        self.assertEqual((r["off"]["notes"], r["off"]["store"]["notes"], r["off"]["told"]), (False, False, False), "the rail toggle, persisted, broadcast")
        self.assertFalse(r["labRefused"]["lab"])
        self.assertEqual((r["labOn"]["hidden"], r["labOn"]["lab"], r["labOn"]["labSrc"]), (False, True, "/lab"),
                         "the gear's row turning a pane on brings it on screen and loads it (the optional panes' live reconcile)")
        self.assertEqual((r["labShown"]["lab"], r["labShown"]["told"], r["labShown"]["docsTold"]), (True, True, 0), "and the panes are told; the URL pane still nothing")
        self.assertEqual((r["notesGone"]["hidden"], r["notesGone"]["notes"], r["notesGone"]["inTold"]), (True, False, False), "a gear-hidden data pane is gone from the dashboard and from the broadcast")

    def test_a_generic_pane_enabled_in_the_gear_loads_only_when_it_comes_on_screen(self):
        rows = _rows(NOTES, DOCS, LAB, OFFPANE)
        r = _run(_stub(rows, "STORE['romp:settings'] = JSON.stringify({ panes: { artifacts: true } });") + km._LANDING_COLLAPSE_JS + _GATE_DRIVER)
        b = r["boot"]
        self.assertEqual((b["artHidden"], b["artOn"], b["artSrc"]), (False, False, None), "the Artifacts pane enabled in the gear: its button back, off screen by its rail default, NOT loaded: %r" % b)
        self.assertEqual((b["offHidden"], b["offOn"], b["offSrc"]), (False, False, None), "a non-experimental on:false data pane: in the dashboard, off screen, not loaded")
        o = r["on"]
        self.assertEqual((o["artOn"], o["artSrc"], o["offOn"], o["offSrc"]), (True, "/artifacts", True, "/offpane"), "the rail toggle brings each on screen and loads it once: %r" % o)

    def test_on_a_phone_a_generic_pane_loads_by_its_tab_alone_and_the_current_tab_loads_on_the_apply(self):
        rows = _rows(NOTES, DOCS, LAB)
        r = _run(_stub(rows, "MOBILE = true; TAB = 'chat'; STORE['romp-panes'] = JSON.stringify({ notes: true, docs: true });") + km._LANDING_COLLAPSE_JS + _PHONE_DRIVER)
        b = r["boot"]
        self.assertEqual((b["notesOn"], b["notesSrc"], b["artSrc"]), (True, None, None), "the desktop flag on, the phone on the chat tab: the notes pane is NOT loaded into a frame the phone never shows: %r" % b)
        generic = lambda sets: {k: v for k, v in sets.items() if k not in ("chat", "timeline", "fleet", "feed", "files")}   # the hand-written optional panes load by their flag on every layout (unchanged)
        self.assertEqual(generic(b["sets"]), {}, "no generic pane's src written at boot on a phone: %r" % b["sets"])
        self.assertEqual((r["tabNotes"]["notesSrc"], generic(r["tabNotes"]["sets"])), ("/notes", {"notes": 1}), "the current tab's frame loads on the apply (the boot, the layout flip): %r" % r["tabNotes"])
        self.assertEqual(generic(r["again"]["sets"]), {"notes": 1}, "and once")
        self.assertEqual(r["tabChat"]["docsSrc"], None, "another tab current: the docs pane (flag on) still not loaded")
        self.assertEqual(r["desktop"]["docsSrc"], "/docs", "the layout flipped to the desktop: the flag loads it: %r" % r["desktop"])

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
        # executed in every CI cell (the 1922 read: these pins sat behind a dist gate that skipped them everywhere but a built checkout)
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


class ThePaneTitleAndIdSinkCensus(unittest.TestCase):
    """Every served sink a pane title or id reaches is escaped for its context, or inert by the whole-string id rule.
      - the shim's LABEL (the title) and APP (the id) slots are JavaScript string literals, baked with json.dumps so
        the shim parses and LABEL equals the title (the behavioural pin, red at the base on the LABEL slot); the
        differential pin adds that the title's ONLY footprint in the shim is that one LABEL literal;
      - the rail, the phone tab and the body attribute wrap the title in _html_esc (the attribute in _html_esc of its
        json.dumps);
      - the WS-drop bell row carries the raw title in a plain sentence, shipped as a JSON string field (json.dumps
        escapes the quote) and rendered client-side through textContent, so it is inert for its context;
      - every id sink (the shim's /ws?app= and romp-vscode-state- slots, and the landing's unquoted attributes and CSS
        selectors) is inert once the id is confined to the whole-string rule (_PANE_ID_RE, matched whole with fullmatch).
    The title-reader population is derived from the live source and fails closed: a NEW title reader fails the census."""
    def setUp(self): self.w = World()
    def tearDown(self): self.w.close()

    def test_the_title_reader_population_over_the_live_tree_is_the_classified_set(self):
        label_calls, title_reads = _title_sites(KSRC)
        self.assertEqual(label_calls, {"_shim", "_note_ws_drop"},
                         "_pane_label is called only where the title is a JS-string literal (the shim's LABEL slot, "
                         "json.dumps'd) and the bell row (textContent): %r" % sorted(label_calls))
        self.assertEqual(title_reads, {"_panes_attr", "_rail_buttons_html", "_mtab_buttons_html", "_pane_label", "<module>"},
                         "a title read (any record's [\"title\"], over-read on purpose) is classified here; the known "
                         "readers are the escaped landing builders (_panes_attr, the rail and tab buttons), _pane_label's "
                         "own id->title map, and the _PANE_ORDER code-pane constant: %r" % sorted(title_reads))

    def test_the_id_pattern_is_portable_to_a_javascript_regexp(self):
        # PR 989 builds a browser RegExp from _PANE_ID_RE.pattern to check an id client-side, so the pattern must read the
        # same rule in JavaScript. It anchors with $ (not the Python-only whole-string anchor, which JavaScript reads as a
        # literal Z): a valid id matches, an id with a trailing newline does not (JavaScript's $ matches only at the end,
        # never before a newline), and an uppercase id and a leading-digit id do not. Red if the pattern reverts to the
        # Python-only anchor, which makes every id fail the browser check (a literal Z is required at the end).
        pat = km._PANE_ID_RE.pattern
        js = ("const re = new RegExp(process.argv[1]);"
              "process.stdout.write(JSON.stringify(['notes','a','a-b_c','notes\\n','Notes','1x'].map(s => re.test(s))));")
        r = subprocess.run(["node", "-e", js, pat], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, "node built a RegExp from _PANE_ID_RE.pattern: " + r.stderr[:500])
        got = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(got, [True, True, True, False, False, False],
                         "the pattern reads the same rule in JavaScript (a valid id matches; a trailing newline, an "
                         "uppercase id and a leading digit do not): %r for %r" % (got, pat))

    def test_the_shim_bakes_an_allowed_title_with_a_quote_or_a_backslash_so_it_parses_and_label_equals_the_title(self):
        # a quote and a backslash are allowed in a title (only control characters, the separators and surrogates are
        # refused at the schema), and both still need escaping for the JS-string context: a raw quote closed the LABEL
        # string and a trailing backslash made the shim a SyntaxError. The shim is rendered with the route's own
        # arguments (pv and data from the snapshot, the shape /pane/<id>/shim.js passes). Red at the base, where the quote
        # title does not parse.
        for i, title in enumerate(('a"b', "a\\b")):   # a quote, a backslash
            pid = "cp%d" % i
            self.w.seed({"id": pid, "title": title, "source": "/feed", "on": True})
            snap = km._panes_snapshot()
            out = _shim_probe(km._shim(pid, pv=snap["rev"], data=snap["data"]))
            self.assertTrue(out.get("parses"), "the shim parses for %r: %s" % (title, out.get("parseErr")))
            self.assertNotIn("declErr", out, "the APP/LABEL declarations run for %r: %s" % (title, out.get("declErr")))
            self.assertEqual(out.get("label"), title, "LABEL equals the title for %r" % title)
            self.assertEqual(out.get("app"), pid, "APP equals the id for %r" % title)
            self.w.unseed(pid)

    def test_the_second_layer_escapes_a_non_ascii_title_so_the_served_shim_encodes_to_utf8(self):
        # the shim's json.dumps(ensure_ascii=True) is a second layer under the schema. The pin reads the KERNEL's own
        # output, never a literal the test rebuilds: the LABEL literal extracted from the served shim is ASCII (ensure_ascii
        # rewrote the accent or emoji to a \uXXXX escape), so the served body encodes to UTF-8, and LABEL still evaluates to
        # the title. An accent and an emoji are ALLOWED titles (so these could be seeded), but the shim is rendered through
        # _shim directly to isolate the LABEL slot. Red under an ensure_ascii=False kernel, which bakes the raw non-ASCII
        # character into the LABEL literal (the extracted literal is then not ASCII). (The whole shim is never pure ASCII:
        # its template carries non-ASCII prose, so the pin reads the LABEL literal, not the whole body.)
        def label_literal(shim):
            i = shim.index("var LABEL=")
            return shim[i:shim.index(";", i) + 1]
        for title in ("Caf\u00e9", "a\U0001f600b"):   # an accented letter, an emoji
            rec = _full({"id": "nz", "title": title, "source": "/feed", "on": True})
            shim = km._shim("nz", pv="7", data={"nz": rec})
            shim.encode("utf-8")   # the served body encodes to UTF-8
            lit = label_literal(shim)
            self.assertTrue(lit.isascii(), "the kernel bakes the LABEL literal as ASCII (ensure_ascii) for %r: %r" % (title, lit))
            out = _shim_probe(shim)
            self.assertTrue(out.get("parses") and "declErr" not in out, (title, out))
            self.assertEqual(out.get("label"), title, "LABEL equals the title for %r" % title)
        # the one case where ensure_ascii changes BEHAVIOUR, not just the spelling: a lone surrogate (refused at every
        # door, so this never happens in service) reaches _shim directly. With ensure_ascii it is baked as a \uXXXX escape,
        # so the served body still encodes to UTF-8 and LABEL round-trips; an ensure_ascii=False kernel would bake the raw
        # surrogate, which .encode('utf-8') cannot encode (red there, on the encode below).
        rec = _full({"id": "sg", "title": "a\ud800b", "source": "/feed", "on": True})
        shim = km._shim("sg", pv="7", data={"sg": rec})
        shim.encode("utf-8")   # does not raise: ensure_ascii kept the surrogate out of the served bytes
        self.assertTrue(label_literal(shim).isascii(), "the surrogate is baked as an ASCII \\uXXXX escape")
        out = _shim_probe(shim)
        self.assertTrue(out.get("parses") and "declErr" not in out, out)
        self.assertEqual(out.get("label"), "a\ud800b", "LABEL round-trips the escaped surrogate")

    def test_the_titles_only_footprint_in_the_shim_is_the_label_literal(self):
        # the differential pin (the title reaches the served shim in exactly one place, the LABEL string literal): render
        # the shim for a probe title and for a placeholder, blank the one `var LABEL=<json.dumps(title)>;` literal in each,
        # and the two must be identical. A second footprint of the title (a copy in a comment, a template literal, another
        # string) would survive the blanking and differ. The backtick-${x}, */ and </script><!-- probes stand in for the
        # template-literal and comment contexts a second sink could land in; U+2028 and U+2029 are rendered through _shim
        # directly (the schema refuses them at input). pv is fixed, so the only difference between the two renders is the
        # title. Red at the base, where the escaped LABEL literal is not what the shim bakes for a quote, a newline or a
        # separator title.
        def blanked(title):
            rec = _full({"id": "dif", "title": title, "source": "/feed", "on": True})
            shim = km._shim("dif", pv="7", data={"dif": rec})
            lit = "var LABEL=" + json.dumps(title, ensure_ascii=True) + ";"
            return shim.replace(lit, "var LABEL=@L@;", 1), (lit in shim)
        ref, ref_ok = blanked("Placeholdr")
        self.assertTrue(ref_ok, "the shim bakes the placeholder title as a single LABEL literal")
        for title in ('a"b', "a\\b", "a\nb", "`x${y}`", "*/", "</script><!--", "\u2028", "\u2029"):
            got, ok = blanked(title)
            self.assertTrue(ok, "the title is baked as the LABEL literal for %r" % title)
            self.assertEqual(got, ref, "the title's only footprint in the shim is the LABEL literal, for %r" % title)

    def test_each_served_title_sink_escapes_or_is_inert_for_its_context(self):
        probe = 'A"<b>&'   # a quote (JS and the attribute), angle brackets and an ampersand (HTML text), within the 24-char bound
        self.w.seed({"id": "sink", "title": probe, "source": "/feed", "on": True})
        # the shim's LABEL slot (red at the base): the shim parses and LABEL equals the title, rendered with the route's
        # own arguments (pv and data from the snapshot, as /pane/<id>/shim.js passes)
        snap = km._panes_snapshot()
        out = _shim_probe(km._shim("sink", pv=snap["rev"], data=snap["data"]))
        self.assertTrue(out.get("parses") and "declErr" not in out and out.get("label") == probe and out.get("app") == "sink", out)
        # the rail, the phone tab, the body attribute: the title only in its escaped form, never raw
        page = km._landing()
        esc = km._html_esc(probe)
        _has(self, "<div class=rail-btn data-pane=sink>%s</div>" % esc, page, "the rail escapes the title")
        _has(self, "<button data-pane=sink>%s</button>" % esc, page, "the phone tab escapes the title")
        attr = re.search(r'data-panes="([^"]*)"', page).group(1)
        self.assertNotIn("<", attr); self.assertNotIn('"', attr)
        self.assertEqual(next(r["title"] for r in _attr_rows(page) if r["id"] == "sink"), probe, "the attribute round-trips the title")
        self.assertNotIn(probe, page, "the raw title reaches no sink in the landing page")
        # the WS-drop bell row: the raw title in a plain sentence. The row the feed ships comes from _sdk_problem_rows (the
        # served row), not the unserved _WS_DROPS ring; it passes through _sdk_problem_text, which folds a multi-line title
        # to its first and last lines. Control characters (the newline included) and U+2028/U+2029 are refused at the
        # schema, so an ordinary title is one line and reaches the served row verbatim. The feed ships the row as a JSON
        # string field (json.dumps escapes the quote) and the shell renders n.text through textContent, so it is inert.
        km._WS_DROPS.clear()
        with contextlib.redirect_stderr(io.StringIO()):
            km._note_ws_drop({"app": "sink", "qbytes": 2_000_000, "dropLogged": False}, "bytes behind", 0)
        rows = km._sdk_problem_rows()
        self.assertTrue(any(probe in row["text"] for row in rows),
                        "the served bell row carries the title verbatim as text, not interpolated into markup or a script: %r"
                        % [r["text"] for r in rows])


if __name__ == "__main__":
    unittest.main()
