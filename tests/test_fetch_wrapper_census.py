#!/usr/bin/env python3
"""Every fetch the kernel's own page scripts make runs after the page-key script's fetch wrapper.

The kernel puts one script first in the head of every page document (kernel.py _PAGE_KEY_JS, placed by Handler._send when
it serves a page-class document). That script replaces the page's window.fetch with a wrapper that adds this origin's page
key, as X-Romp-Key, to each request whose URL resolves to this origin. A fetch the page makes after it carries the key; a
fetch in a document without it carries none and is refused. The pages' bundles are censused in
ui/webview/fetch-wrapper-census.test.ts. This module censuses the kernel's inline scripts, which live in kernel.py as Python
string literals, by asking the real handler for the documents it serves (an in-process server, signed in with a session
this module mints). Every population is DERIVED from the source and the served bytes, not listed:

  1. Every page-class document (each route of _PAGE_RENDERERS, the table the router dispatches from) opens its head with
     the wrapper: the first script in the document is the page-key script, right after <head>, and no fetch call, and no
     other script, comes before it. The login response (the one that seeds the key) holds the seed and then the wrapper.
  2. Every fetch call in a kernel.py string literal (read with the ast module, so escapes are decoded and docstrings are
     not code) is served verbatim, and every page-class document that serves it serves it after that document's own
     wrapper. A call that no page-class document serves must be the service worker's; otherwise it would run in a
     document the wrapper is not in, or nowhere.
  3. Every fetch the service worker makes names its route as a literal, and that route answers a request that carries no
     credential at all (probed here, not listed): a worker has no wrapper.
  4. The only member reference to fetch in any served page document or the worker, dotted (`.fetch`) or by a string key
     (`["fetch"]`), is the wrapper's own two (it reads window.fetch and replaces it); another window's fetch (a frame made
     by script) is one nothing wrapped. Stated limit, on the precondition that the sources are written in good faith: a
     key that is not written as a string (`w["fe" + "tch"]`, a key held in a variable) is not read; CensusShapes'
     test_the_member_reader_takes_the_dotted_and_the_string_key_forms is its witness.
  5. Every other text/html document the kernel sends (derived from the _send calls whose content type is text/html) is
     listed below with a way to render it, and makes no fetch and loads no bundle, because nothing puts the wrapper in it.
     A computed content type never says html: the static trees' map is read here, and the /file route and its relay are
     held to their own types in tests/test_file_view.py and tests/test_kernel_remote_file_relay.py.

What the wrapper does to each request form is executed in a browser by tests/test_page_key_dashboard_browser.py. Synthetic
only: an invented serve token assembled at run time, invented session ids. No token, session id or page key VALUE is printed.
"""
import ast
import json
import os
import re
import secrets
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
KERNEL_PY = os.path.join(ROOT, "kernel", "kernel.py")

# Hermetic state BEFORE the loads: they resolve their state root at import time. This module's own root, with per-session
# hosts off (nothing here connects a session, and none may start a host if something did).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
os.makedirs(os.path.join(os.environ["XDG_STATE_HOME"], "romp"), exist_ok=True)
with open(os.path.join(os.environ["XDG_STATE_HOME"], "romp", "session-hosts"), "w") as _fh:
    _fh.write("off\n")
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "census-" + secrets.token_hex(12))
# A PRIVATE module name (test_kernel_auth_hardening.py's note): a sibling that loaded the kernel under a shared name and
# another token would rebind TOKEN here.
km = load_source("romp_kernel_fetchcensus", os.path.join(BIN, "romp-kernel"))

CALL = re.compile(r"(?<![\w$.])fetch\s*\(")      # a call of the global fetch, written as script text
# a %-format conversion: where a literal is formatted, the served text holds the value there, not the spec
PCT = re.compile(r"%(?:\([^)]*\))?[-#0 +]*(?:\*|\d+)?(?:\.(?:\*|\d+))?[diouxXeEfFgGcrsa%]")
# a fetch reached as a member of some object, dotted or by a string key (a class, not a group, so findall returns the matches)
MEMBER = re.compile(r"\.\s*fetch\b|\[\s*['\"`]fetch['\"`]\s*\]")
WRAPPER = "<script>" + km._PAGE_KEY_JS + "</script>"
SID = "aaaaaaaa-1111-2222-3333-444444444444"


def _render_login():
    return km._TOKEN_LOGIN_HTML


def _render_too_large():
    q = {"path": ["/tmp/notes-api/paper.pdf"], "sid": [SID], "cap": ["synthetic-cap"]}
    return km._too_large_page("too large to show", "paper.pdf", q) + km._too_large_page(
        "too large to show", "paper.pdf", q, route="/remote/TESTHOST/file")


# The text/html documents the kernel sends outside the page class, by the name its _send call builds the body from, with a
# renderer for each. Nothing puts the wrapper in them, so each must make no fetch and load no bundle.
NON_PAGE_HTML = {
    "_TOKEN_LOGIN_HTML": _render_login,     # the sign-in page: its form navigates to /?token=, it makes no request of its own
    "_too_large_page": _render_too_large,   # an oversize PDF's own tab: a sentence and a download link, no script
}


def _kernel_tree():
    with open(KERNEL_PY, encoding="utf-8") as f:
        return ast.parse(f.read())


def _docstring_ids(tree):
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body:
            first = n.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                out.add(id(first.value))
    return out


def _fetch_calls_in_literals(tree):
    """[(line, fragment)] for every fetch call written in a kernel.py string literal that is not a docstring. The fragment is
    the literal's text around the call, cut at any %-format placeholder on either side, so it is the text the served
    document carries verbatim."""
    docs = _docstring_ids(tree)
    out = []
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Constant) and isinstance(n.value, str)) or id(n) in docs:
            continue
        s = n.value
        for m in CALL.finditer(s):
            left, right = s[max(0, m.start() - 40):m.start()], s[m.start():m.end() + 40]
            specs = list(PCT.finditer(left))
            if specs:
                left = left[specs[-1].end():]
            spec = PCT.search(right)
            if spec:
                right = right[:spec.start()]
            out.append((n.lineno, left + right))
    return out


def _call_args(text, open_paren):
    """The argument text of the call whose opening parenthesis is at `open_paren`, by bracket depth (quotes skipped)."""
    depth, i, q = 0, open_paren, None
    while i < len(text):
        c = text[i]
        if q:
            if c == "\\":
                i += 2
                continue
            if c == q:
                q = None
        elif c in "'\"`":
            q = c
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                return text[open_paren + 1:i]
        i += 1
    return text[open_paren + 1:]


class _Served(unittest.TestCase):
    """The real Handler over a loopback server; the documents it serves to a signed-in page, fetched once per class."""

    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.sess = km._mint_session()
        cls.cookie = "%s=%s" % (km._SESSION_COOKIE, cls.sess)
        cls.pages = {}
        for route in sorted(set(km._PAGE_RENDERERS) - {""}):     # "" and "/" are one route (the router classes both as "/")
            st, body, _ = cls._get(route, {"Cookie": cls.cookie})
            cls.pages[route] = (st, body)
        cls.worker = cls._get("/sw.js", {"Cookie": cls.cookie})

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    @classmethod
    def _get(cls, path, headers, method="GET", data=None):
        rq = urllib.request.Request("http://127.0.0.1:%d%s" % (cls.port, path), method=method, data=data)
        for k, v in headers.items():
            rq.add_header(k, v)
        try:
            with urllib.request.urlopen(rq, timeout=30) as r:
                return r.status, r.read().decode("utf-8", "replace"), r.headers
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace"), e.headers


class PageDocumentsOpenWithTheWrapper(_Served):
    def test_every_page_document_is_served(self):
        self.assertGreaterEqual(len(self.pages), 8, "the page class is the route table's: %r" % sorted(self.pages))
        for route, (st, body) in self.pages.items():
            self.assertEqual(st, 200, route + " is served to a signed-in page")
            self.assertGreater(len(body), 1000, route + " is a real document")

    def test_the_first_script_of_every_page_document_is_the_wrapper(self):
        for route, (_, body) in self.pages.items():
            head = body.find("<head>")
            self.assertGreaterEqual(head, 0, route + " has a <head> for the wrapper to open")
            first = body.find("<script")
            self.assertEqual(first, head + len("<head>"), route + ": the first script comes right after <head>, with no script before it")
            self.assertTrue(body.startswith(WRAPPER, first), route + ": and it is the page-key script")
            wrap_end = first + len(WRAPPER)
            early = [m.start() for m in CALL.finditer(body) if m.start() < wrap_end]
            self.assertEqual(early, [], route + ": no fetch call comes before the wrapper is in place")

    def test_the_login_response_holds_the_seed_and_then_the_wrapper(self):
        st, body, _ = self._get("/?token=" + urllib.request.quote(km.TOKEN, safe=""),
                                {"Accept": "text/html", "Sec-Fetch-Dest": "document"})
        self.assertEqual(st, 200)
        head = body.find("<head>")
        self.assertTrue(body.startswith("<script>", head + len("<head>")), "the seed opens the login response's head")
        seed_end = body.index("</script>", head) + len("</script>")
        self.assertIn("localStorage.setItem(" + json.dumps(km._PAGE_KEY_SLOT), body[head:seed_end], "the first script is the seed")
        self.assertIsNone(CALL.search(body[head:seed_end]), "the seed makes no fetch")
        self.assertTrue(body.startswith(WRAPPER, seed_end), "and the wrapper follows it, before any other script")


class InlineFetchCallsRunAfterTheWrapper(_Served):
    def test_every_fetch_call_in_a_kernel_literal_runs_after_the_wrapper_of_each_page_serving_it_or_in_the_worker(self):
        calls = _fetch_calls_in_literals(_kernel_tree())
        self.assertGreater(len(calls), 20, "the census found the inline scripts' fetch calls (a census of nothing proves nothing)")
        worker = self.worker[1]
        stray = []
        for line, frag in calls:
            self.assertGreaterEqual(len(frag), 16, "kernel.py:%d: the call's text is long enough to find: %r" % (line, frag))
            serving = [r for r, (_, body) in self.pages.items() if frag in body]
            if not serving and frag not in worker:
                stray.append("kernel.py:%d served by no page document and not the worker's: %r" % (line, frag))
            for r in serving:                   # EVERY page document that serves the call serves it after its own wrapper
                body = self.pages[r][1]
                if not 0 <= body.find(WRAPPER) < body.find(frag):
                    stray.append("kernel.py:%d served by %s before or without its wrapper: %r" % (line, r, frag))
        self.assertEqual(stray, [], "a fetch call in a document without the page-key script ahead of it carries no page key: "
                                    "move it into a page document, or give it the road its document has")

    def test_the_service_workers_fetches_go_to_routes_that_need_no_credential(self):
        st, sw, _ = self.worker
        self.assertEqual(st, 200)
        calls = list(CALL.finditer(sw))
        self.assertTrue(calls, "the worker's fetches were found")
        for m in calls:
            args = _call_args(sw, sw.index("(", m.start()))
            lit = re.match(r"\s*(['\"])(/[^'\"]*)\1", args)
            self.assertIsNotNone(lit, "a worker's fetch names its route as a literal, so the census can ask it: %r" % args[:60])
            method = (re.search(r"method\s*:\s*['\"](\w+)['\"]", args) or [None, "GET"])[1]
            status = self._get(lit.group(2), {"Content-Type": "application/json"}, method=method,
                               data=b"{}" if method == "POST" else None)[0]
            self.assertNotEqual(status, 403, "the worker has no wrapper, so %s %s must answer a request that carries no "
                                             "credential: it answered %d" % (method, lit.group(2), status))


class NoOtherWindowsFetch(_Served):
    def test_the_only_member_fetch_in_the_served_scripts_is_the_wrappers_own(self):
        for route, (_, body) in list(self.pages.items()) + [("/sw.js", self.worker[:2])]:
            start = body.find(WRAPPER)
            span = (start, start + len(WRAPPER)) if start >= 0 else (-1, -1)
            outside = [body[max(0, m.start() - 30):m.end() + 20] for m in MEMBER.finditer(body) if not span[0] <= m.start() < span[1]]
            self.assertEqual(outside, [], route + ": a fetch reached through another object is one the page-key script did not wrap")
        self.assertEqual(len(MEMBER.findall(km._PAGE_KEY_JS)), 2, "the wrapper reads window.fetch once and replaces it once")


class NonPageDocumentsMakeNoFetch(unittest.TestCase):
    def _html_sends(self):
        """[(line, key, enclosing function)] for every self._send(...) whose content type is a text/html literal."""
        tree = _kernel_tree()
        out = []

        def walk(node, fn):
            for ch in ast.iter_child_nodes(node):
                f = ch if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)) else fn
                if (isinstance(ch, ast.Call) and isinstance(ch.func, ast.Attribute) and ch.func.attr == "_send"
                        and len(ch.args) >= 3 and isinstance(ch.args[2], ast.Constant)
                        and isinstance(ch.args[2].value, str) and ch.args[2].value.startswith("text/html")):
                    b = ch.args[1]
                    key = b.id if isinstance(b, ast.Name) else (
                        b.func.id if isinstance(b, ast.Call) and isinstance(b.func, ast.Name) else ast.unparse(b))
                    out.append((ch.lineno, key, fn))
                walk(ch, f)
        walk(tree, None)
        return out

    def test_every_html_document_outside_the_page_class_is_listed(self):
        sends = self._html_sends()
        self.assertTrue(sends, "the census found the text/html responses")
        page = [(ln, fn) for ln, key, fn in sends if key == "_page"]
        self.assertEqual(len(page), 1, "one _send renders the page class: %r" % [(ln, k) for ln, k, _ in sends])
        fn = page[0][1]
        binds = [n for n in ast.walk(fn) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_page" for t in n.targets)]
        self.assertTrue(binds and all("_PAGE_RENDERERS.get(" in ast.unparse(n.value) for n in binds),
                        "the page dispatch renders the route table's renderer, the one the wrapper goes into")
        others = sorted({key for _, key, _ in sends if key != "_page"})
        self.assertEqual(others, sorted(NON_PAGE_HTML), "a text/html document outside the page class gets no wrapper: list it "
                                                        "in NON_PAGE_HTML with a renderer, so the census reads it")

    def test_no_document_outside_the_page_class_makes_a_fetch_or_loads_a_bundle(self):
        for key, render in NON_PAGE_HTML.items():
            body = render()
            self.assertIsNone(CALL.search(body), key + " makes no fetch: nothing puts the wrapper in it")
            self.assertIsNone(MEMBER.search(body), key + " reaches no fetch as a member either")
            self.assertNotRegex(body, r"<script[^>]*\bsrc=", key + " loads no bundle, which would run without the wrapper")

    def test_the_static_trees_never_serve_html(self):
        maps = [n for n in ast.walk(_kernel_tree()) if isinstance(n, ast.Dict)
                and any(isinstance(v, ast.Constant) and v.value == "text/javascript" for v in n.values)]
        self.assertTrue(maps, "the static trees' content-type map was found")
        for d in maps:
            self.assertFalse([v.value for v in d.values if isinstance(v, ast.Constant) and "html" in str(v.value)],
                             "a bundle or an asset served as html would be a document with no wrapper")


class CensusShapes(unittest.TestCase):
    """The census's own readers, on synthetic sources, so a reader that stopped seeing a shape shows here."""

    def test_the_literal_reader_takes_calls_and_leaves_prose_and_members(self):
        tree = ast.parse('A = "x;fetch(\'/a\',{cache:1});"\n'
                         'B = "a fetch that fails; remote.origin.fetch"\n'
                         'C = "w.contentWindow.fetch(\'/b\')"\n'
                         'D = "var n=%d;fetch(\'/c\')" % 1\n'
                         'def f():\n    "fetch(\'/docstring\')"\n')
        frags = [frag for _, frag in _fetch_calls_in_literals(tree)]
        self.assertEqual(frags, ["x;fetch('/a',{cache:1});", ";fetch('/c')"])

    def test_the_member_reader_takes_the_dotted_and_the_string_key_forms(self):
        text = "w.fetch('/a'); w . fetch; w['fetch']('/b'); w[ \"fetch\" ]; w[`fetch`]; fetch('/c'); x.fetcher; f('fetch');"
        self.assertEqual(MEMBER.findall(text), [".fetch", ". fetch", "['fetch']", '[ "fetch" ]', "[`fetch`]"])
        # the stated limit: a key that is not written as a string is not read
        self.assertEqual(MEMBER.findall("w['fe'+'tch']('/a'); var k='fetch'; w[k]('/b');"), [])

    def test_the_argument_reader_matches_brackets_and_skips_quotes(self):
        s = "fetch('/push/ack',{method:'POST',body:JSON.stringify({p:')'})}).then(x)"
        self.assertEqual(_call_args(s, s.index("(")), "'/push/ack',{method:'POST',body:JSON.stringify({p:')'})}")


if __name__ == "__main__":
    unittest.main()
