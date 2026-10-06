#!/usr/bin/env python3
"""One source for the pane records: the panes defined with `romp pane define` reach the browser from GET /panes, the records
`romp pane list` reads, and the dashboard shell builds them there. Every page the route table renders, every static file and
every GET route in the kernel's route register reads byte for byte the same whatever panes are defined, and carries none of a
defined pane's fields (id, title, source, flags).

Each route is requested over the real handler on a loopback server, the way a signed-in browser's page navigation requests it:
first with no pane defined (twice, so a value that moves between two identical requests is told apart from one that moves with
the panes), then with five synthetic panes defined through the door's own check (kernel.py define_pane), one per record shape:
a URL source with a query and a fragment, a kernel route, a state-root page (`pane:<id>`, served at /pane/<id>/), an
experimental pane, and a pane off by default with its protocol named. Each field carries its own marker, built at run time from
lowercase letters, so no HTML, JSON or URL escaping can hide it and no credential scanner reads one. The byte comparison is the
census: it sees a flag, a count, an order or a digest as well as a field. The marker scan is its readable failure (which field,
on which route), and it reads the headers too.

The population is derived from the kernel's own tables, never listed here, and an empty one fails:
- the pages: every key of _PAGE_RENDERERS (the router and the request classifier, Handler._need, read that one table, so a page
  added later joins by construction), every renderer reached;
- the static files: _STATIC_EXACT, every file under the asset tree (MEDIA), and every file under the built-bundle tree (DIST)
  when it has been built, read from a private copy taken under the served labs' build lock so a rebuild on another worker
  cannot move a bundle between passes. The bundles are built from ui/ at build time and cannot hold a record written at run
  time; a run with no build reads every other file, and the served legs, which build the tree, read it too;
- the GET route register (_PERF_HTTP_ROUTES["GET"], held equal to do_GET's dispatches by tests/test_perf_stats.py) and one
  instance of each collapsed family (_PERF_HTTP_FAMILIES), whatever each answers, the routes served before the gate included.

The comparison leaves out exactly two values, each named in EXCLUSIONS with its reason: both move between two identical requests
whatever the registry holds. They are the Date header of every response (every other header is compared in full) and the
uptime_s member of /version's body, taken out of the body and so out of the body's length that its Content-Length header carries
(the rest of that body is compared byte for byte, so a value derived from the panes added to /version later is still caught). A
test holds that the comparison leaves out these two and nothing else.

Synthetic data only (TESTHOST; invented ids and titles). No credential value is printed, and a failure names the route and the
field, never a whole body (a difference no marker explains is located by its first differing byte, with a short window of each
side)."""
import hashlib
import json
import os
import re
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import lab_dist   # noqa: E402  the served labs' owner of the bundle build and its copies, registered by tests/__init__.py
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Hermetic state BEFORE the loads: they resolve their state root at import time, and only pytest runs conftest's floor
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
# a PRIVATE module name: load_source re-executes a name already loaded into the SAME module object, so a sibling module that
# loaded the kernel under a shared name with another serve token would rebind this one's
km = load_source("romp_kernel_panerecords", os.path.join(BIN, "romp-kernel"))

CN = km._SESSION_COOKIE        # this kernel's session-cookie name
SESS = km._mint_session()      # one signed-in browser's session (never printed)
KEY = km._page_key(SESS)       # its page key (never printed)

_PREFIX = "zq"                 # every marker starts here; each is lowercase letters only


def _m(*words):
    return _PREFIX + "".join(words)


def _plants():
    """[(pane label, definition, [(field, marker)])]: one pane per record shape, every field its own marker."""
    web = "http://TESTHOST:9/"
    out = []
    url = {"id": _m("idurl"), "title": _m("titleurl").capitalize(),
           "source": web + _m("urlpath") + "/?ref=" + _m("queryval") + "#" + _m("fragval"), "on": True}
    out.append(("the URL pane", url, [("id", url["id"]), ("title", _m("titleurl")), ("source's path", _m("urlpath")),
                                      ("source's query", _m("queryval")), ("source's fragment", _m("fragval"))]))
    route = {"id": _m("idroute"), "title": _m("titleroute").capitalize(), "source": "/" + _m("routepath"), "on": True}
    out.append(("the route pane", route, [("id", route["id"]), ("title", _m("titleroute")), ("source", _m("routepath"))]))
    state = {"id": _m("idstate"), "title": _m("titlestate").capitalize(), "source": "pane:" + _m("idstate"), "on": False}
    out.append(("the state-root pane", state, [("id and source", state["id"]), ("title", _m("titlestate"))]))
    exp = {"id": _m("idexp"), "title": _m("titleexp").capitalize(), "source": web + _m("exppath") + "/?ref=" + _m("expquery"),
           "experimental": True}
    out.append(("the experimental pane", exp, [("id", exp["id"]), ("title", _m("titleexp")), ("source's path", _m("exppath")),
                                               ("source's query", _m("expquery"))]))
    plain = {"id": _m("idplain"), "title": _m("titleplain").capitalize(), "source": "/" + _m("plainroute"), "protocol": "romp",
             "on": False}
    out.append(("the plain pane", plain, [("id", plain["id"]), ("title", _m("titleplain")), ("source", _m("plainroute"))]))
    return out


PLANTS = _plants()
FIELDS = [("%s's %s" % (label, field), marker) for label, _, fields in PLANTS for field, marker in fields]
STATE_ID = PLANTS[2][1]["id"]

# The comparison's two exclusions, each named with its reason (see the module docstring); the stability test holds that nothing
# else moves between two identical requests, and test_the_comparison_leaves_out_the_two_named_values_and_nothing_else that the
# comparison leaves out nothing else
_DATE_HEADER = "date"                               # a header name, lower-case
_UPTIME_ROUTE, _UPTIME_KEY = "/version", "uptime_s"
EXCLUSIONS = (   # (what is left out, why): each moves between two identical requests whatever panes are defined
    ("the Date header of every response", "the time the response was sent, to the second"),
    ("the uptime_s member of /version's body", "the kernel's uptime, in whole seconds; it is taken out of the body and so out of "
     "the body's length (Content-Length), and the rest of the body is compared"),
)
# /version's body is json.dumps of a dict: the member and the separator beside it, wherever it stands
_UPTIME_RE = re.compile(rb', "' + _UPTIME_KEY.encode() + rb'": -?\d+(?=[,}])|"' + _UPTIME_KEY.encode() + rb'": -?\d+, ')


def _comparable(path, body):
    """(the bytes the census compares for a route, the number of members taken out): the whole body, but /version's with its
    uptime_s member taken out."""
    if path != _UPTIME_ROUTE:
        return body, 0
    return _UPTIME_RE.subn(b"", body)


def _hits(body, headers):
    """The fields whose marker the response carries, in the body or a header (case-insensitive)."""
    low = body.lower()
    head = "\n".join("%s: %s" % kv for kv in headers).lower()
    return [what for what, marker in FIELDS if marker.encode() in low or marker in head]


def _population():
    """(pages, static, wide): the pages the route table renders, the static files, and every route the census requests (the
    pages, the static files, the GET register and one instance per collapsed family), each list derived from the kernel's own
    tables."""
    pages = sorted(p for p in km._PAGE_RENDERERS if p)          # "" is the bare-path spelling of "/"
    media = sorted("/media/" + n for n in os.listdir(km.MEDIA) if os.path.isfile(os.path.join(km.MEDIA, n)))
    dist = (sorted("/dist/" + f.relative_to(km.DIST).as_posix() for f in km.DIST.rglob("*") if f.is_file())
            if km.DIST.is_dir() else [])
    static = list(km._STATIC_EXACT) + media + dist
    families = [f[:-1] + (STATE_ID + "/" if f == "/pane/*" else "x") for f in km._PERF_HTTP_FAMILIES]
    wide = list(dict.fromkeys(pages + static + sorted(km._PERF_HTTP_ROUTES["GET"]) + families))
    return pages, static, wide


class PaneRecordsReachTheBrowserFromTheirRoute(unittest.TestCase):
    """The census over the route table: see the module docstring."""

    @classmethod
    def setUpClass(cls):
        # the registry this class defines into: its own state root (session-hosts off), the pane memo cleared; jd is the shared
        # judge module even under a private kernel name, so the rebind is undone on the way out
        td = tempfile.mkdtemp()
        cls.addClassCleanup(shutil.rmtree, td, True)
        orig_state = km.jd.STATE
        km.jd._rebind_state(Path(td) / "state")
        cls.addClassCleanup(km.jd._rebind_state, orig_state)
        km.jd.STATE.mkdir(parents=True, exist_ok=True)
        (km.jd.STATE / "session-hosts").write_text("off\n")
        cls._reset_memos()
        cls.addClassCleanup(cls._reset_memos)
        # /busy, served before the gate, would build the session backend (with its boot reconcile) in this process: the census
        # reads what the route answers with no backend, both times alike
        sdk0 = km._sdk
        km._sdk = lambda: None
        cls.addClassCleanup(setattr, km, "_sdk", sdk0)
        cls._freeze_dist(td)
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        cls.srv.daemon_threads = True
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.addClassCleanup(cls.srv.server_close)
        cls.addClassCleanup(cls.srv.shutdown)
        cls.pages, cls.static, cls.wide = _population()
        cls.empty = cls._pass()
        cls.again = cls._pass()
        cls.defined = []
        for _label, defn, _fields in PLANTS:
            got, err = km.define_pane(dict(defn))
            if err:
                raise AssertionError("a synthetic pane failed the door's check: %s" % err)
            cls.defined.append(got)
        cls._reset_memos()
        cls.planted = cls._pass()
        ids = ",".join(d["id"] for _, d, _ in PLANTS)
        cls.queried = {p: cls._get(p + "?panes=" + ids)[:2] for p in cls.pages}
        cls.keyed = cls._get("/panes", key=True)

    @classmethod
    def _freeze_dist(cls, td):
        # the built-bundle tree, when there is one, is read from the served labs' own private copy (tests/lab_dist.py: built if
        # stale, then copied, both under the build lock): a served class on another worker that rebuilds the checkout's bundles in
        # place would otherwise move a bundle, and the build token every page carries, between this class's passes. Where this
        # checkout cannot build (lab_dist skips with the reason), no worker can rebuild the tree either, so it is read in place
        if not km.DIST.is_dir():
            return
        dest = os.path.join(td, "bundles")
        try:
            if os.path.realpath(lab_dist.default().dist) != os.path.realpath(str(km.DIST)):
                raise AssertionError("the served labs' bundle tree %s is not the kernel's %s" % (lab_dist.default().dist, km.DIST))
            lab_dist.copy_dist(dest)
        except unittest.SkipTest:
            return
        cls.addClassCleanup(setattr, km, "DIST", km.DIST)
        km.DIST = Path(dest)

    @staticmethod
    def _reset_memos():
        km._PANES_MEMO["slot"] = None
        km._PANES_BAD.clear()

    @classmethod
    def _get(cls, path, key=False):
        """(status, body, headers) for a GET carrying this browser's session cookie, and its page key when `key`."""
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (cls.port, path))
        req.add_header("Cookie", "%s=%s" % (CN, SESS))
        if key:
            req.add_header("X-Romp-Key", KEY)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, r.read(), list(r.headers.items())
        except urllib.error.HTTPError as e:
            return e.code, e.read(), list(e.headers.items())

    @classmethod
    def _pass(cls):
        """{path: record} for every route in the population: the status, the body's length and digest, the digest of the bytes
        compared (_comparable) and how many members they leave out, the compared bytes themselves for the pages and /version (for
        a failure's location; /version's whole body too), the headers compared (all but Date; where a member was taken out, the
        Content-Length is the length of the bytes compared, since the whole body's length carries the member's digits), the Date
        header, the Content-Length as sent, the count of every header, and the fields whose marker the response carries."""
        out = {}
        for p in cls.wide:
            status, body, headers = cls._get(p)
            cmp, taken = _comparable(p, body)
            out[p] = {"status": status, "len": len(body), "sha": hashlib.sha256(body).hexdigest(),
                      "cmp": hashlib.sha256(cmp).hexdigest(), "taken": taken,
                      "body": cmp if (p in cls.pages or p == _UPTIME_ROUTE) else None,
                      "whole": body if p == _UPTIME_ROUTE else None,
                      "headers": [(k, str(len(cmp)) if (taken and k.lower() == "content-length") else v)
                                  for k, v in headers if k.lower() != _DATE_HEADER],
                      "date": [v for k, v in headers if k.lower() == _DATE_HEADER],
                      "clen": [v for k, v in headers if k.lower() == "content-length"],
                      "nhead": len(headers),
                      "hits": _hits(body, headers)}
        return out

    @staticmethod
    def _where(a, b):
        """Where two bodies first part, and a short window of each, for a difference no marker explains."""
        i = next((i for i in range(min(len(a), len(b))) if a[i] != b[i]), min(len(a), len(b)))
        return "first difference at byte %d: %r vs %r" % (i, a[max(0, i - 24):i + 24], b[max(0, i - 24):i + 24])

    def _population_read(self):
        # every test below reads the passes over the derived population; an empty or partial one fails each test on its own
        # (the population test says which part is missing), never a scan that passes because it read nothing
        self.assertGreaterEqual(len(self.pages), 2, "the route table renders pages: %r" % self.pages)
        self.assertTrue(any(p.startswith("/media/") for p in self.static), "the static files are read")
        self.assertTrue(set(km._PERF_HTTP_ROUTES["GET"]) <= set(self.wide), "every GET route in the register is requested")
        self.assertTrue(set(self.wide) <= set(self.empty) and set(self.wide) <= set(self.planted), "every route was read in both passes")

    def test_a_keyed_get_panes_lists_every_planted_pane(self):
        # the plant took: GET /panes, read with the page key, answers every field of every planted pane
        status, body, _ = self.keyed
        self.assertEqual(status, 200, "GET /panes with the page key")
        low = body.lower()
        missing = [what for what, marker in FIELDS if marker.encode() not in low]
        self.assertEqual(missing, [], "GET /panes lists every planted field")
        self.assertEqual(len(self.defined), len(PLANTS))

    def test_the_population_is_every_page_static_file_and_get_route_the_route_table_serves(self):
        self.assertGreaterEqual(len(self.pages), 2, "the route table renders pages: %r" % self.pages)
        self.assertIn("/", self.pages)
        for p in self.pages:
            self.assertEqual(km.Handler._need(p), ("page", ""), "%s classes as a page" % p)
        reached = {km._PAGE_RENDERERS[p] for p in self.pages}
        self.assertEqual(reached, set(km._PAGE_RENDERERS.values()), "every renderer the table maps is requested")
        self.assertIn(km._landing, reached, "the dashboard shell among them")
        media = [p for p in self.static if p.startswith("/media/")]
        self.assertGreater(len(media), 3, "the asset tree is read: %d files" % len(media))
        if km.DIST.is_dir():
            self.assertTrue(any(p.startswith("/dist/") for p in self.static), "a built bundle tree is read whole")
        for p in self.static:
            self.assertEqual(km.Handler._need(p), ("static", ""), "%s classes as static" % p)
        register = set(km._PERF_HTTP_ROUTES["GET"])
        self.assertTrue(register and register <= set(self.wide), "every GET route in the register is requested")
        self.assertTrue(set(self.pages) <= register, "every page is a registered GET route")
        for fam in km._PERF_HTTP_FAMILIES:
            self.assertTrue(any(p.startswith(fam[:-1]) for p in self.wide), "%s has an instance" % fam)
        for p in self.pages + self.static:
            self.assertEqual(self.empty[p]["status"], 200, "%s answers the signed-in browser" % p)
        answered = {p for p in self.wide if self.empty[p]["status"] != 403}
        self.assertTrue((set(self.pages) | set(km._STATIC_EXACT)) <= answered)
        self.assertTrue(answered - set(self.pages) - set(self.static), "the routes served before the gate answer too: %r" % sorted(answered))

    def test_every_route_reads_the_same_twice_with_no_pane_defined(self):
        # the premise of the comparison below: two identical requests read the same bytes, but for the two named values
        self._population_read()
        moved = []
        for p in self.wide:
            a, b = self.empty[p], self.again[p]
            if a["status"] != b["status"]:
                moved.append("%s: status %d vs %d" % (p, a["status"], b["status"]))
            elif a["cmp"] != b["cmp"]:
                moved.append("%s: %s" % (p, self._where(a["body"], b["body"]) if a["body"] is not None else "%d vs %d bytes" % (a["len"], b["len"])))
            elif a["headers"] != b["headers"]:
                moved.append("%s: a header: %r vs %r" % (p, [h for h in a["headers"] if h not in b["headers"]],
                                                         [h for h in b["headers"] if h not in a["headers"]]))
        self.assertEqual(moved, [], "a response moved between two identical requests with nothing defined:\n" + "\n".join(moved))
        self.assertIn(_UPTIME_ROUTE, self.wide, "%s is a route the census requests" % _UPTIME_ROUTE)
        self.assertEqual(self.empty[_UPTIME_ROUTE]["status"], 200, _UPTIME_ROUTE)
        self.assertTrue(all(len(self.empty[p]["date"]) == 1 for p in self.wide), "every response carries one Date header")

    def test_the_comparison_leaves_out_the_two_named_values_and_nothing_else(self):
        # the instrument itself: in every pass, every route is compared on all of its headers but the one Date header and on its
        # whole body, but /version, compared on its body less exactly one member, uptime_s, and on that body's length
        self._population_read()
        self.assertEqual(len(EXCLUSIONS), 2, "the comparison's exclusions are the two named ones")
        for name, rec in (("with nothing defined", self.empty), ("again", self.again), ("with panes defined", self.planted)):
            for p in self.wide:
                r = rec[p]
                self.assertEqual((len(r["date"]), len(r["headers"]) + 1), (1, r["nhead"]), "%s %s: every header compared but one Date header" % (p, name))
                if p == _UPTIME_ROUTE:
                    whole, rest = json.loads(r["whole"]), json.loads(r["body"])
                    self.assertEqual(r["taken"], 1, "%s %s: one %s member taken out" % (p, name, _UPTIME_KEY))
                    self.assertIsInstance(whole.pop(_UPTIME_KEY), int, "%s %s: %s is a count of seconds" % (p, name, _UPTIME_KEY))
                    self.assertEqual(rest, whole, "%s %s: the compared body is the whole body less %s, nothing else" % (p, name, _UPTIME_KEY))
                    self.assertEqual(r["clen"], [str(len(r["whole"]))], "%s %s: the Content-Length sent is the whole body's" % (p, name))
                    self.assertIn(("Content-Length", str(len(r["body"]))), r["headers"], "%s %s: compared as the length of the bytes compared" % (p, name))
                else:
                    self.assertEqual((r["taken"], r["cmp"]), (0, r["sha"]), "%s %s: the whole body compared" % (p, name))
                    self.assertEqual(r["clen"], [v for k, v in r["headers"] if k.lower() == "content-length"], "%s %s: the Content-Length compared as sent" % (p, name))

    def test_version_reads_byte_for_byte_the_same_whatever_panes_are_defined_but_its_uptime(self):
        # /version's body less its uptime_s member, byte for byte: a value derived from the panes added to /version's body later is
        # caught here, as the comparison below catches it, with the route named
        self._population_read()
        a, b = self.empty[_UPTIME_ROUTE], self.planted[_UPTIME_ROUTE]
        self.assertEqual((a["status"], b["status"]), (200, 200), _UPTIME_ROUTE)
        self.assertEqual((a["taken"], b["taken"]), (1, 1), "%s: its %s member taken out of each body" % (_UPTIME_ROUTE, _UPTIME_KEY))
        self.assertTrue(a["body"] == b["body"], "%s changes when panes are defined: %s" % (_UPTIME_ROUTE, self._where(a["body"], b["body"])))

    def test_no_page_or_static_response_carries_a_defined_panes_fields(self):
        self._population_read()
        for p in self.pages + self.static:
            self.assertEqual([], self.empty[p]["hits"], "%s carries a marker with nothing defined: the marker collides with code" % p)
        found = ["%s: %s" % (p, ", ".join(self.planted[p]["hits"])) for p in self.pages + self.static if self.planted[p]["hits"]]
        self.assertEqual(found, [], "a page or static response carries a defined pane's fields:\n" + "\n".join(found))
        for p in self.pages + self.static:
            self.assertEqual(self.planted[p]["status"], 200, "%s answers the signed-in browser with panes defined" % p)

    def test_every_route_reads_byte_for_byte_the_same_whatever_panes_are_defined(self):
        self._population_read()
        self.assertGreater(len(self.wide), len(self.pages) + len(self.static), "the comparison covers the register too")
        differ = []
        for p in self.wide:
            a, b = self.empty[p], self.planted[p]
            if a["status"] != b["status"]:
                differ.append("%s: status %d vs %d" % (p, a["status"], b["status"]))
            elif a["cmp"] != b["cmp"]:
                why = ", ".join(b["hits"]) if b["hits"] else (
                    self._where(a["body"], b["body"]) if a["body"] is not None else "%d vs %d bytes, no field marker" % (a["len"], b["len"]))
                differ.append("%s: %s" % (p, why))
            elif a["headers"] != b["headers"]:
                differ.append("%s: a header: %r vs %r" % (p, [h for h in a["headers"] if h not in b["headers"]],
                                                          [h for h in b["headers"] if h not in a["headers"]]))
        self.assertEqual(differ, [], "a response changes when panes are defined:\n" + "\n".join(differ))

    def test_no_get_route_in_the_register_answers_with_a_defined_panes_fields(self):
        self._population_read()
        self.assertEqual([p for p in self.wide if self.empty[p]["hits"]], [], "no route carries a marker with nothing defined")
        found = ["%s (%d): %s" % (p, self.planted[p]["status"], ", ".join(self.planted[p]["hits"]))
                 for p in self.wide if self.planted[p]["hits"]]
        self.assertEqual(found, [], "a GET route answers with a defined pane's fields:\n" + "\n".join(found))

    def test_a_query_naming_the_defined_panes_changes_no_page(self):
        # the dashboard's own address key for panes (?panes=) names every planted id: no page reads it into its bytes
        self._population_read()
        for p in self.pages:
            status, body = self.queried[p]
            self.assertEqual(status, 200, p)
            self.assertTrue(hashlib.sha256(body).hexdigest() == self.planted[p]["sha"],
                            "%s with ?panes= naming the defined panes reads the bare bytes (%d vs %d)" % (p, len(body), self.planted[p]["len"]))


if __name__ == "__main__":
    unittest.main()
