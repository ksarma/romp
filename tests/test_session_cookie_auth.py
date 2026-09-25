#!/usr/bin/env python3
"""The login cookie holds a per-kernel SESSION ID, not the serve token (kernel/kernel.py _authorize).

What the login cookie authenticates, and how, pinned by asking the real handler over a loopback
server (the auth-hardening doctrine: a source-position assertion cannot catch a route on the wrong
side of the gate). The model:

  * The session cookie ALONE opens the PAGE class (a page document) and the STATIC class (/dist,
    /media, /sw.js): code, no session data. Both classes are read off the shared route table
    (kernel.py _PAGE_RENDERERS / _static_route) that the router itself dispatches from, so the
    router and the classifier (_need) never disagree.
  * Every other route needs a second value the cookie never carries: the PAGE KEY K (the X-Romp-Key
    header, or k= on a socket dial) for the full and socket classes, or a per-file CAP for the file
    class.
  * The serve token (X-Romp-Token, ?token=, the one-time ?c= code) authenticates from any Origin as
    before, and a page navigation carrying one seeds a session.
  * The session id, K and the cap are domain-separated HMACs under distinct fixed labels, compared in
    constant time; a value minted for one role never validates for another.

Synthetic only: an invented serve token, invented session ids. No token, session id, page key or cap
VALUE is printed; the assertions are equality booleans and status codes. No session state is touched.
"""
import ast
import io
import json
import os
import socket
import threading
import unittest
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
from romp_load import load_source
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
KERNEL_PY = os.path.join(os.path.dirname(HERE), "kernel", "kernel.py")

# Hermetic state BEFORE the loads: they resolve their state root at import time, and only pytest
# runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
# A PRIVATE module name (see test_kernel_auth_hardening.py's note): load_source re-executes a name
# already in sys.modules into the SAME module object, so a sibling that loaded "romp_kernel" under a
# different token would rebind km.TOKEN here.
km = load_source("romp_kernel_sessioncookie", os.path.join(BIN, "romp-kernel"))

TOK = km.TOKEN
CN = km._SESSION_COOKIE                       # this kernel's own session-cookie name
SLOT = km._PAGE_KEY_SLOT                      # this kernel's localStorage slot for the page key (keyed by CN)
SEED_SET = "localStorage.setItem(" + json.dumps(SLOT)   # how the login seed writes the key into that slot
SESS = km._mint_session()                     # one browser's session id (never printed)
KEY = km._page_key(SESS)                      # its page key K
SESS2 = km._mint_session()                    # a second browser's session
KEY2 = km._page_key(SESS2)                    # its page key


def _cap(sess, path, sid, host=""):
    return km._file_cap(sess, host, path, sid)


class _Server(unittest.TestCase):
    """A real Handler over a loopback server, driven by urllib (GET/POST/HEAD/OPTIONS) and a raw
    socket (the /ws upgrade). The credentials are built from the kernel's own derivations."""

    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.origin = "http://127.0.0.1:%d" % cls.port
        # a real file so an AUTHORIZED /file read returns 200, not a 404 that could mask an auth pass
        fd, cls.fpath = tempfile.mkstemp(suffix=".png")
        os.write(fd, b"\x89PNG\r\n\x1a\nsynthetic")
        os.close(fd)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        try:
            os.unlink(cls.fpath)
        except OSError:
            pass

    def _req(self, path, method="GET", cookie=None, key=None, xtoken=None, origin=None,
             accept=None, sec_fetch=None, extra_cookie=None):
        req = urllib.request.Request(self.origin + path, method=method,
                                     data=b"" if method == "POST" else None)
        cookies = []
        if cookie is not None:
            cookies.append("%s=%s" % (CN, cookie))
        if extra_cookie is not None:
            cookies.append(extra_cookie)
        if cookies:
            req.add_header("Cookie", "; ".join(cookies))
        if key is not None:
            req.add_header("X-Romp-Key", key)
        if xtoken is not None:
            req.add_header("X-Romp-Token", xtoken)
        if origin is not None:
            req.add_header("Origin", origin)
        if accept is not None:
            req.add_header("Accept", accept)
        if sec_fetch is not None:
            req.add_header("Sec-Fetch-Dest", sec_fetch)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, r.read(), r.headers
        except urllib.error.HTTPError as e:
            return e.code, e.read(), e.headers

    def _status(self, *a, **kw):
        return self._req(*a, **kw)[0]

    def _set_cookies(self, headers):
        return headers.get_all("Set-Cookie") or []

    def _session_cookie_value(self, headers):
        for sc in self._set_cookies(headers):
            name, _, rest = sc.partition("=")
            if name.strip() == CN:
                return rest.split(";", 1)[0]
        return None

    def _any_new_cookie_value(self, headers):
        """The value of a freshly SET cookie other than a clear (Max-Age=0); None if none set."""
        for sc in self._set_cookies(headers):
            if "Max-Age=0" in sc:
                continue
            return sc.partition("=")[2].split(";", 1)[0]
        return None

    def _ws_status(self, query, cookie=None, key=None, xtoken=None, origin=None):
        """Send a /ws upgrade over a raw socket, return the numeric status of the reply's status line.
        403 comes back immediately; a 101 (gate passed) is read off the status line and the socket is
        closed before any frame, so nothing hangs."""
        s = socket.create_connection(("127.0.0.1", self.port), timeout=10)
        try:
            lines = ["GET /ws?%s HTTP/1.1" % query, "Host: 127.0.0.1:%d" % self.port,
                     "Upgrade: websocket", "Connection: Upgrade",
                     "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==", "Sec-WebSocket-Version: 13"]
            if cookie is not None:
                lines.append("Cookie: %s=%s" % (CN, cookie))
            if key is not None:
                lines.append("X-Romp-Key: %s" % key)
            if xtoken is not None:
                lines.append("X-Romp-Token: %s" % xtoken)
            if origin is not None:
                lines.append("Origin: %s" % origin)
            s.sendall(("\r\n".join(lines) + "\r\n\r\n").encode())
            s.settimeout(10)
            buf = b""
            while b"\r\n" not in buf:
                b = s.recv(256)
                if not b:
                    break
                buf += b
            first = buf.split(b"\r\n", 1)[0]
            return int(first.split(b" ")[1]) if b" " in first else 0
        finally:
            s.close()


class NoResponseSetsACookieEqualToTheToken(_Server):
    def test_no_response_ever_sets_a_cookie_whose_value_is_the_serve_token(self):
        for path, accept in (("/?token=" + TOK, "text/html"),        # a page navigation
                             ("/sessions?token=" + TOK, "*/*"),      # a JSON read
                             ("/no-such-route?token=" + TOK, "*/*"), # an unknown path
                             ("/?token=" + TOK, "*/*")):             # / as a fetch, not a navigation
            _, _, headers = self._req(path, accept=accept)
            for sc in self._set_cookies(headers):
                value = sc.partition("=")[2].split(";", 1)[0]
                self.assertFalse(value == TOK, "no Set-Cookie may equal the serve token (%s)" % path.split("?")[0])


class CookieOpensPageAndStaticOnly(_Server):
    def test_the_route_table_is_the_page_class(self):
        # page and static are DERIVED from the one route table the router dispatches from
        self.assertEqual(set(km._PAGE_RENDERERS),
                         {"", "/", "/chat", "/feed", "/timeline", "/fleet", "/waiting", "/files", "/settings"},
                         "the page route table (both the router and _need read this)")
        for p in km._PAGE_RENDERERS:
            self.assertEqual(km.Handler._need(p), ("page", ""), "%r classes as page" % p)
        for p in ("/sw.js", "/dist/x.js", "/media/icon.svg"):
            self.assertEqual(km.Handler._need(p)[0], "static", "%r classes as static" % p)
        # the static class, frozen by value as the page table is: a path or a prefix added to either tuple would
        # open on the session cookie alone, so it is judged here before it ships
        self.assertEqual(km._STATIC_EXACT, ("/sw.js",), "the static class's exact paths: the push worker alone")
        self.assertEqual(km._STATIC_PREFIXES, ("/dist/", "/media/"), "the static class's trees: the built bundles and the assets")

    def test_the_cookie_alone_opens_the_page_and_static_classes(self):
        for p in ("/", "/chat", "/feed", "/timeline", "/fleet", "/waiting", "/files", "/settings"):
            status, body, headers = self._req(p, cookie=SESS)
            self.assertEqual(status, 200, "cookie alone serves the page %s" % p)
            self.assertIn("text/html", headers.get("Content-Type", ""))
        self.assertEqual(self._status("/sw.js", cookie=SESS), 200, "cookie alone serves the worker")
        self.assertEqual(self._status("/media/icon.svg", cookie=SESS), 200, "cookie alone serves a static asset")

    def test_the_cookie_alone_is_refused_everywhere_outside_page_and_static(self):
        for p in ("/sessions", "/handoff", "/update-check", "/push/pending?endpoint=x",
                  "/tunnels", "/file?path=%s" % self.fpath, "/file?path=%s&download=1" % self.fpath,
                  "/no-such-route"):
            self.assertEqual(self._status(p, cookie=SESS), 403, "cookie alone is refused on %s" % p)
        # a POST (full class) with the cookie and its own Origin: refused without the key
        self.assertEqual(self._status("/views", method="POST", cookie=SESS, origin=self.origin), 403)
        # the socket (ws class) with the cookie alone: refused
        self.assertEqual(self._ws_status("app=chat", cookie=SESS, origin=self.origin), 403)

    def test_a_forged_foreign_origin_is_refused_even_on_a_page(self):
        # the cookie still passes the Origin gate; an in-browser page on another origin is refused
        self.assertEqual(self._status("/chat", cookie=SESS, origin="http://evil.example"), 403)


class CookiePlusKey(_Server):
    def test_cookie_plus_key_opens_the_full_class(self):
        self.assertEqual(self._status("/sessions", cookie=SESS, key=KEY), 200)
        self.assertNotEqual(self._status("/views", method="POST", cookie=SESS, key=KEY, origin=self.origin), 403)
        self.assertEqual(self._ws_status("app=chat&k=" + KEY, cookie=SESS, origin=self.origin), 101)

    def test_the_key_without_the_cookie_is_refused(self):
        self.assertEqual(self._status("/sessions", key=KEY), 403)

    def test_the_key_of_another_session_is_refused(self):
        self.assertEqual(self._status("/sessions", cookie=SESS, key=KEY2), 403)

    def test_the_key_with_a_forged_foreign_origin_is_refused(self):
        self.assertEqual(self._status("/sessions", cookie=SESS, key=KEY, origin="http://evil.example"), 403)

    def test_the_socket_dial_checks_the_origin_as_the_other_routes_do(self):
        # the cookie and k= that open the socket from the dashboard's own origin (the 101 above) are
        # refused on an upgrade whose Origin is another site's: the Origin gate covers the upgrade too
        self.assertEqual(self._ws_status("app=chat&k=" + KEY, cookie=SESS, origin="http://other.example"), 403)


class DomainSeparation(_Server):
    """A value minted for one role is refused where another role's value is required. Each
    substitution pin is red under a mutant that collapses the derivation its comment names (the page
    key derived as the session id, the cap as the page key, either as the serve token); the labels
    themselves are pinned distinct below. The session cookie's value refused as the serve token is
    tests/test_login_cookie_not_token.py, red at fa3ef54b5."""

    def test_the_labels_are_distinct_and_differ_before_their_first_nul(self):
        # every HMAC label the kernel defines, derived from its module (a *_LABEL string), not listed here
        labels = {k: v for k, v in vars(km).items() if k.endswith("_LABEL") and isinstance(v, str)}
        self.assertEqual(sorted(labels), ["_COOKIE_NAME_LABEL", "_FILE_CAP_LABEL", "_MIGRATION_LABEL",
                                          "_PAGE_KEY_LABEL", "_SESSION_LABEL"], "the kernel's HMAC labels")
        for k, v in labels.items():
            self.assertTrue(v.endswith("\0") and v.count("\0") == 1, "%s ends in its one NUL" % k)
        heads = [v.split("\0", 1)[0] for v in labels.values()]
        self.assertEqual(len(set(heads)), len(heads), "the labels differ before their first NUL")
        for a in labels.values():
            for b in labels.values():
                if a is not b:
                    self.assertFalse(b.startswith(a), "no label is a prefix of another")

    def test_every_credential_compare_is_constant_time(self):
        # A census over kernel.py's syntax tree: no ==, !=, in or is compares a credential. A credential is the
        # serve token (TOKEN), a value the four derivations or the session reader make, or a credential slot the
        # request carries (?token=, ?cap=, ?k=, ?c=, X-Romp-Token, X-Romp-Key, a cookie). Every such compare goes
        # through _ct_eq, which is hmac.compare_digest. The census must also SEE the credential compares, so the
        # _ct_eq calls over credentials are counted: a census that matched nothing would prove nothing.
        tree = ast.parse(open(KERNEL_PY, encoding="utf-8").read())
        calls = {"_page_key", "_file_cap", "_hmac_b64", "_mint_session", "_migration_session",
                 "_browser_session", "_cookie"}

        def credential(n):
            for x in ast.walk(n):
                if isinstance(x, ast.Name) and x.id == "TOKEN":
                    return True
                if isinstance(x, ast.Call):
                    f = x.func
                    name = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
                    if name in calls:
                        return True
                    if name == "get" and x.args and isinstance(x.args[0], ast.Constant) and isinstance(f, ast.Attribute):
                        v, base = x.args[0].value, f.value
                        if isinstance(base, ast.Name) and base.id == "q" and v in ("token", "cap", "k", "c"):
                            return True
                        if isinstance(base, ast.Attribute) and base.attr == "headers" and v in ("X-Romp-Token", "X-Romp-Key"):
                            return True
            return False

        eq_ops = (ast.Eq, ast.NotEq, ast.In, ast.NotIn, ast.Is, ast.IsNot)
        plain = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Compare)
                 and any(isinstance(o, eq_ops) for o in n.ops)
                 and any(credential(x) for x in [n.left] + list(n.comparators))]
        self.assertEqual(plain, [], "a credential compared with ==, !=, in or is (kernel.py lines): use _ct_eq")
        ct = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
              and n.func.id == "_ct_eq" and any(credential(a) for a in n.args)]
        self.assertGreaterEqual(len(ct), 7, "the census sees the credential compares (the session tag, ?token=, "
                                "X-Romp-Token, the page key, the cap, the old cookie twice): %d" % len(ct))
        ct_def = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_ct_eq")
        self.assertTrue(any(isinstance(x, ast.Attribute) and x.attr == "compare_digest" for x in ast.walk(ct_def)),
                        "_ct_eq compares with hmac.compare_digest")

    def test_the_session_id_is_refused_as_the_page_key(self):        # mutant: page key derivation shares the session id
        self.assertEqual(self._status("/sessions", cookie=SESS, key=SESS), 403)

    def test_the_page_key_is_refused_as_a_file_cap(self):            # mutant: cap derivation collapses to the page key
        self.assertEqual(self._status("/file?path=%s&cap=%s" % (self.fpath, KEY), cookie=SESS), 403)

    def test_a_file_cap_is_refused_as_the_page_key(self):            # mutant: cap derivation collapses to the page key
        cap = _cap(SESS, self.fpath, "")
        self.assertEqual(self._status("/sessions", cookie=SESS, key=cap), 403)

    def test_the_page_key_is_refused_as_the_serve_token(self):       # mutant: page key derivation equals the serve token
        pk = km._page_key(SESS)                                      # computed here, so the mutant's K is what is presented
        self.assertEqual(self._status("/sessions?token=" + pk), 403)
        self.assertEqual(self._status("/sessions", xtoken=pk), 403)

    def test_a_file_cap_is_refused_as_the_serve_token(self):         # mutant: cap derivation equals the serve token
        cap = _cap(SESS, self.fpath, "")                            # computed here, so the mutant's cap is what is presented
        self.assertEqual(self._status("/sessions?token=" + cap), 403)
        self.assertEqual(self._status("/sessions", xtoken=cap), 403)

    def test_the_page_key_presented_as_a_session_is_refused(self):   # K is not a valid session id
        self.assertFalse(km._session_ok(KEY), "the page key is not a session id")
        self.assertEqual(self._status("/chat", cookie=KEY), 403, "K in the cookie opens no page")

    def test_the_session_cookies_value_is_refused_in_every_credential_slot(self):
        # The session cookie's VALUE and its tag half (the HMAC after the ".") are neither a page
        # key, a cap nor the serve token, so presenting either in any of those slots authorizes
        # nothing. (The value's one use, as the session cookie, opens only the page and static
        # classes, covered above.)
        tag = SESS.split(".", 1)[1]
        for kind, v in (("the session id", SESS), ("its tag half", tag)):
            self.assertEqual(self._status("/sessions", cookie=SESS, key=v), 403, "%s is not the page key" % kind)
            self.assertEqual(self._ws_status("app=chat&k=" + v, cookie=SESS, origin=self.origin), 403, "%s is not k=" % kind)
            self.assertEqual(self._status("/file?path=%s&cap=%s" % (self.fpath, v), cookie=SESS), 403, "%s is not a cap" % kind)
            self.assertEqual(self._status("/sessions?token=" + v), 403, "%s is not the ?token=" % kind)
            self.assertEqual(self._status("/sessions", xtoken=v), 403, "%s is not the X-Romp-Token" % kind)


class RouteClassesDerivedFromTheRegister(_Server):
    """The page and static classes are DERIVED from the route table the router reads,
    checked two ways against the checked-in route register (_PERF_HTTP_ROUTES / _PERF_HTTP_FAMILIES),
    and the file class is GET and HEAD only."""

    def test_page_and_static_agree_with_the_route_register_both_ways(self):
        get_routes = set(km._PERF_HTTP_ROUTES["GET"])
        page = set(km._PAGE_RENDERERS) - {""}         # "" is the bare-path spelling of "/"
        # forward: every page route and the static exact route are registered GET routes; the /dist and
        # /media families are collapsed families in the register
        self.assertTrue(page <= get_routes, "page routes outside the GET register: %s" % (page - get_routes))
        for s in km._STATIC_EXACT:
            self.assertIn(s, get_routes, "%s is a registered GET route" % s)
        self.assertTrue({p.rstrip("/") + "/*" for p in km._STATIC_PREFIXES} <= set(km._PERF_HTTP_FAMILIES),
                        "the static prefixes are collapsed families in the register")
        # backward: no GET route that is neither page nor static answers to the cookie alone
        for r in sorted(get_routes):
            cls = km.Handler._need(r)[0]
            if r in page or km._static_route(r):
                self.assertIn(cls, ("page", "static"), "%s should be a cookie-only class" % r)
            else:
                self.assertNotIn(cls, ("page", "static"), "%s must need more than the cookie" % r)

    def test_the_file_class_is_get_and_head_only(self):
        cap = _cap(SESS, self.fpath, "")
        # GET with the cap serves the file (the file class)
        self.assertEqual(self._status("/file?path=%s&cap=%s" % (self.fpath, cap), cookie=SESS), 200)
        # HEAD with the cap passes the gate too
        self.assertEqual(self._status("/file?path=%s&cap=%s" % (self.fpath, cap), method="HEAD", cookie=SESS), 200)
        # a POST carrying the SAME cap is the FULL class (needs the key), so the cap does not authorize it
        self.assertEqual(self._status("/file?path=%s&cap=%s" % (self.fpath, cap),
                                      method="POST", cookie=SESS, origin=self.origin), 403,
                         "a non-GET/HEAD /file is the full class, refused on cookie+cap alone")


class ReauthSignalOnAStaleKey(_Server):
    """A valid session whose stored key no longer matches gets a DISTINCT 403 (X-Romp-Reauth) so
    the page-key script drops the stale key and hops to /login; a denial for any other reason does not
    carry the marker."""

    def test_a_valid_session_with_a_wrong_key_gets_the_reauth_marker(self):
        status, _, headers = self._req("/sessions", cookie=SESS, key=KEY2)
        self.assertEqual(status, 403)
        self.assertEqual(headers.get("X-Romp-Reauth"), "1", "the distinct re-sign-in marker")

    def test_a_valid_session_with_no_key_gets_the_reauth_marker(self):
        status, _, headers = self._req("/sessions", cookie=SESS)
        self.assertEqual(status, 403)
        self.assertEqual(headers.get("X-Romp-Reauth"), "1")

    def test_a_page_on_the_cookie_alone_carries_no_reauth_marker(self):
        _, _, headers = self._req("/chat", cookie=SESS)
        self.assertIsNone(headers.get("X-Romp-Reauth"), "the cookie opens the page; no re-sign-in")

    def test_a_denial_with_no_session_carries_no_reauth_marker(self):
        status, _, headers = self._req("/sessions")
        self.assertEqual(status, 403)
        self.assertIsNone(headers.get("X-Romp-Reauth"), "no session, so nothing to re-sign-in")

    def test_the_page_key_script_drops_the_key_and_hops_on_the_marker(self):
        js = km._PAGE_KEY_JS
        self.assertIn("X-Romp-Reauth", js, "the script reads the marker off the fetch response")
        self.assertIn("removeItem", js, "it drops the stale key")
        self.assertIn("/login", js, "and hops to /login")


class KeepAliveConnectionReuse(_Server):
    """A sign-in's cookie, key seed, no-store and traceback permission are per-request. The handler object
    lives for the whole keep-alive connection, and the routes served before the gate (/login, /healthz,
    /version, POST /push/ack) never run _authorize, so only the resets at the top of do_GET, do_POST and
    do_OPTIONS clear what a sign-in on the same connection set. Each request after the sign-in must carry
    no Set-Cookie, no seed, no no-store and no traceback."""

    def _read_one(self, s):
        """Read exactly one HTTP/1.1 response off `s`: the head, then Content-Length body bytes."""
        buf = b""
        while b"\r\n\r\n" not in buf:
            b = s.recv(4096)
            if not b:
                break
            buf += b
        head, _, rest = buf.partition(b"\r\n\r\n")
        clen = 0
        for line in head.split(b"\r\n"):
            if line[:15].lower() == b"content-length:":
                clen = int(line.split(b":", 1)[1].strip())
        body = rest
        while len(body) < clen:
            b = s.recv(4096)
            if not b:
                break
            body += b
        return head, body

    def test_a_data_request_after_a_login_on_one_connection_sets_no_cookie_and_no_seed(self):
        s = socket.create_connection(("127.0.0.1", self.port), timeout=10)
        try:
            s.sendall(("GET /?token=%s HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nAccept: text/html\r\n"
                       "Sec-Fetch-Dest: document\r\n\r\n" % (TOK, self.port)).encode())
            head1, body1 = self._read_one(s)
            self.assertIn(b"200", head1.split(b"\r\n", 1)[0], "the login response")
            self.assertIn(CN.encode() + b"=", head1, "the login set the session cookie")
            self.assertIn(SEED_SET.encode(), body1, "the login seeded the key")
            # a data request on the SAME connection, with the session cookie and the key
            s.sendall(("GET /sessions HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nCookie: %s=%s\r\n"
                       "X-Romp-Key: %s\r\n\r\n" % (self.port, CN, SESS, KEY)).encode())
            head2, body2 = self._read_one(s)
            self.assertIn(b"200", head2.split(b"\r\n", 1)[0], "the data read")
            self.assertNotIn(b"Set-Cookie", head2, "the data response sets no cookie")
            self.assertNotIn(b"X-Romp-Reauth", head2, "and no re-sign-in marker")
            self.assertNotIn(SEED_SET.encode(), body2, "and carries no key seed")
        finally:
            s.close()

    def _sign_in(self, s):
        s.sendall(("GET /?token=%s HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nAccept: text/html\r\n"
                   "Sec-Fetch-Dest: document\r\n\r\n" % (TOK, self.port)).encode())
        head, body = self._read_one(s)
        self.assertIn(CN.encode() + b"=", head, "the sign-in set the session cookie")
        self.assertIn(SEED_SET.encode(), body, "the sign-in seeded the key")

    def _assert_clean(self, head, body, what):
        self.assertNotIn(b"Set-Cookie", head, what + ": no cookie from the earlier sign-in")
        self.assertNotIn(b"no-store", head.lower(), what + ": not the sign-in's no-store")
        self.assertNotIn(SEED_SET.encode(), body, what + ": no key seed")
        self.assertNotIn(b"__rompPageKey", body, what + ": no page-key script")
        self.assertNotIn(b"Traceback", body, what + ": no traceback")

    def test_the_routes_before_the_gate_after_a_sign_in_on_one_connection_set_nothing(self):
        # each case on a connection of its own, straight after the sign-in, so no request between them resets the flags
        cases = (
            ("GET /login", "GET /login HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nAccept: text/html\r\n\r\n", b" 200 "),
            ("GET /healthz", "GET /healthz HTTP/1.1\r\nHost: 127.0.0.1:%d\r\n\r\n", b" 200 "),
            ("POST /push/ack", "POST /push/ack HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nContent-Type: application/json\r\n"
                               "Content-Length: 2\r\n\r\n{}", b" 400 "),
            ("OPTIONS /sessions", "OPTIONS /sessions HTTP/1.1\r\nHost: 127.0.0.1:%d\r\n\r\n", b" 403 "),
        )
        for what, raw, want in cases:
            s = socket.create_connection(("127.0.0.1", self.port), timeout=10)
            try:
                self._sign_in(s)
                s.sendall((raw % self.port).encode())
                head, body = self._read_one(s)
                self.assertIn(want, head.split(b"\r\n", 1)[0] + b" ", what + ": answered as it would be on a connection of its own")
                self._assert_clean(head, body, what)
            finally:
                s.close()

    def test_a_route_before_the_gate_that_raises_after_a_token_request_on_one_connection_sends_no_traceback(self):
        def _boom(*a, **k):
            raise RuntimeError("operator-only-detail")
        for name in ("_version_info", "_push_ledger_stamp"):
            saved = getattr(km, name)
            setattr(km, name, _boom)
            self.addCleanup(setattr, km, name, saved)
        s = socket.create_connection(("127.0.0.1", self.port), timeout=10)
        try:
            # a request authorized by the serve token may see a traceback; the next one on the connection may not
            s.sendall(("GET /no-such-route?token=%s HTTP/1.1\r\nHost: 127.0.0.1:%d\r\n\r\n" % (TOK, self.port)).encode())
            self._read_one(s)
            s.sendall(("GET /version HTTP/1.1\r\nHost: 127.0.0.1:%d\r\n\r\n" % self.port).encode())
            head, body = self._read_one(s)
            self.assertIn(b" 500 ", head.split(b"\r\n", 1)[0] + b" ", "the raising /version")
            self._assert_clean(head, body, "GET /version")
            s.sendall(("GET /no-such-route?token=%s HTTP/1.1\r\nHost: 127.0.0.1:%d\r\n\r\n" % (TOK, self.port)).encode())
            self._read_one(s)
            ack = json.dumps({"pid": "p" * 22, "stage": "shown"}).encode()
            s.sendall(("POST /push/ack HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nContent-Type: application/json\r\n"
                       "Content-Length: %d\r\n\r\n" % (self.port, len(ack))).encode() + ack)
            head, body = self._read_one(s)
            self.assertIn(b" 500 ", head.split(b"\r\n", 1)[0] + b" ", "the raising /push/ack")
            self._assert_clean(head, body, "POST /push/ack")
        finally:
            s.close()


class CookieOnlyClassBare500(_Server):
    """A traceback can name an internal path or state, so a 500 carries it only to a caller that presented
    the serve token or the page key. A page render on the session cookie alone, a file load on its cap, and
    a route served before the gate (/version, POST /push/ack) answer a BARE 500."""

    def test_a_page_render_that_raises_answers_a_bare_500(self):
        def _boom():
            raise RuntimeError("secret-internal-detail-in-the-render")
        saved = km._PAGE_RENDERERS.get("/chat")
        km._PAGE_RENDERERS["/chat"] = _boom
        self.addCleanup(lambda: km._PAGE_RENDERERS.__setitem__("/chat", saved))
        status, body, _ = self._req("/chat", cookie=SESS)
        self.assertEqual(status, 500)
        text = body.decode("utf-8", "replace")
        self.assertNotIn("Traceback", text, "no traceback on the cookie-only class")
        self.assertNotIn("secret-internal-detail", text, "no internal detail in the body")

    def test_a_full_class_route_that_raises_keeps_its_traceback(self):
        saved = km._sessions_listing_serve
        def _boom(*a, **k):
            raise RuntimeError("operator-visible-detail")
        km._sessions_listing_serve = _boom
        self.addCleanup(lambda: setattr(km, "_sessions_listing_serve", saved))
        status, body, _ = self._req("/sessions", cookie=SESS, key=KEY)
        self.assertEqual(status, 500)
        self.assertIn("Traceback", body.decode("utf-8", "replace"),
                      "the full class needs the page key as well; the operator gets the trace")

    def test_a_token_request_that_raises_keeps_its_traceback(self):
        saved = km._sessions_listing_serve
        def _boom(*a, **k):
            raise RuntimeError("operator-visible-detail")
        km._sessions_listing_serve = _boom
        self.addCleanup(lambda: setattr(km, "_sessions_listing_serve", saved))
        status, body, _ = self._req("/sessions", xtoken=TOK)
        self.assertEqual(status, 500)
        self.assertIn("Traceback", body.decode("utf-8", "replace"), "the CLI's request, on the serve token, gets the trace")

    def test_a_route_served_before_the_gate_that_raises_answers_a_bare_500(self):
        saved = km._version_info
        def _boom(*a, **k):
            raise RuntimeError("secret-internal-detail-in-the-probe")
        km._version_info = _boom
        self.addCleanup(lambda: setattr(km, "_version_info", saved))
        status, body, _ = self._req("/version")
        self.assertEqual(status, 500)
        text = body.decode("utf-8", "replace")
        self.assertNotIn("Traceback", text, "/version asks for no credential, so it gets no traceback")
        self.assertNotIn("secret-internal-detail", text)

    def test_the_push_ack_that_raises_answers_a_bare_500(self):
        saved = km._push_ledger_stamp
        def _boom(*a, **k):
            raise RuntimeError("secret-internal-detail-in-the-ack")
        km._push_ledger_stamp = _boom
        self.addCleanup(lambda: setattr(km, "_push_ledger_stamp", saved))
        req = urllib.request.Request(self.origin + "/push/ack", method="POST",
                                     data=json.dumps({"pid": "p" * 22, "stage": "shown"}).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                status, body = r.status, r.read()
        except urllib.error.HTTPError as e:
            status, body = e.code, e.read()
        self.assertEqual(status, 500)
        text = body.decode("utf-8", "replace")
        self.assertNotIn("Traceback", text, "the ack is admitted by its push id alone, so it gets no traceback")
        self.assertNotIn("secret-internal-detail", text)

    def test_a_file_load_on_its_cap_that_raises_answers_a_bare_500(self):
        saved = km.Handler._file_preview
        def _boom(*a, **k):
            raise RuntimeError("secret-internal-detail-in-the-file")
        km.Handler._file_preview = _boom
        self.addCleanup(lambda: setattr(km.Handler, "_file_preview", saved))
        status, body, _ = self._req("/file?path=%s&cap=%s" % (self.fpath, _cap(SESS, self.fpath, "")), cookie=SESS)
        self.assertEqual(status, 500)
        self.assertNotIn("Traceback", body.decode("utf-8", "replace"), "a cap opens one file, not the trace")


class SocketKeyQueryIsSocketOnly(_Server):
    def test_k_is_honoured_on_the_socket_route_only(self):
        # k= stands in for the header the socket dial cannot send; it is read on /ws alone
        self.assertEqual(self._ws_status("app=chat&k=" + KEY, cookie=SESS, origin=self.origin), 101)
        # the same k= on a non-socket route does not authorize (that route reads X-Romp-Key)
        self.assertEqual(self._status("/sessions?k=" + KEY, cookie=SESS), 403)


class LoginHandoff(_Server):
    def test_a_token_navigation_seeds_the_session_and_the_key_once(self):
        status, body, headers = self._req("/?token=" + TOK, accept="text/html", sec_fetch="document")
        self.assertEqual(status, 200)
        sc = [c for c in self._set_cookies(headers) if c.startswith(CN + "=")]
        self.assertEqual(len(sc), 1, "one session cookie set")
        value = sc[0].partition("=")[2].split(";", 1)[0]
        self.assertTrue(km._session_ok(value), "the cookie carries a valid session id")
        self.assertIn("Path=/", sc[0])
        self.assertIn("Max-Age=31536000", sc[0])
        self.assertIn("SameSite=Lax", sc[0])
        self.assertIn("HttpOnly", sc[0])
        self.assertNotIn("Strict", sc[0])
        text = body.decode("utf-8", "replace")
        # the seed carries this session's page key, exactly once, into the per-kernel slot, and the
        # page-key reader is present
        self.assertEqual(text.count(SEED_SET), 1, "the key is seeded once, into the per-kernel slot")
        self.assertIn("__rompPageKey", text, "the page-key reader is injected")

    def test_the_key_bearing_login_response_is_no_store(self):
        # The response that carries the page key must not be stored, so the key stays out of the
        # browser's cache (defence in depth). A page served on the cookie alone stays no-cache.
        _, _, headers = self._req("/?token=" + TOK, accept="text/html", sec_fetch="document")
        self.assertEqual((headers.get("Cache-Control") or "").lower(), "no-store", "the login response is no-store")
        _, _, h2 = self._req("/chat", cookie=SESS)
        self.assertEqual((h2.get("Cache-Control") or "").lower(), "no-cache", "a cookie-only page stays no-cache")

    def test_a_c_navigation_also_seeds_a_session(self):
        code = km._mint_handoff()
        status, body, headers = self._req("/?c=" + code, accept="text/html", sec_fetch="document")
        self.assertEqual(status, 200)
        self.assertTrue(km._session_ok(self._session_cookie_value(headers) or ""))

    def test_a_non_navigation_token_sets_no_cookie_and_seeds_no_key(self):
        status, body, headers = self._req("/sessions?token=" + TOK, accept="*/*")
        self.assertEqual(status, 200)
        self.assertEqual(self._set_cookies(headers), [], "a fetch with the token sets no cookie")
        self.assertNotIn("romp.pageKey", body.decode("utf-8", "replace"))

    def test_a_signed_in_browser_keeps_its_session_on_a_second_login(self):
        status, _, headers = self._req("/?token=" + TOK, cookie=SESS, accept="text/html", sec_fetch="document")
        self.assertEqual(status, 200)
        self.assertTrue(self._session_cookie_value(headers) == SESS, "the existing session is kept")

    def test_login_page_is_exempt(self):
        self.assertEqual(self._status("/login"), 200)


class LegacyCookieMigration(_Server):
    def test_two_tabs_migrating_at_once_get_the_same_session_and_the_same_key(self):
        # Tabs a browser restores after the upgrade each send the old cookie before either response lands. Each
        # is handed the same session and the same page key, so whichever response the browser keeps last, the
        # cookie and the stored key are in step. (Compared as booleans: no value is printed.)
        got = []
        for page in ("/", "/chat"):
            status, body, headers = self._req(page, extra_cookie="romp_token=" + TOK,
                                              accept="text/html", sec_fetch="document")
            self.assertEqual(status, 200, "the old cookie migrates on %s" % page)
            got.append((self._session_cookie_value(headers) or "", body.decode("utf-8", "replace")))
        (s1, b1), (s2, b2) = got
        self.assertTrue(km._session_ok(s1) and km._session_ok(s2), "both responses carry a valid session")
        self.assertTrue(s1 == s2, "both tabs are handed the same session")
        seed = json.dumps(km._page_key(s1))
        self.assertTrue(seed in b1 and seed in b2, "and each seeds that session's page key")
        self.assertFalse(s1 == TOK, "the migration session is not the serve token")

    def test_a_fresh_sign_in_mints_a_session_of_its_own(self):
        # the shared session is the migration's alone: two ?token= sign-ins each mint their own
        vals = []
        for _ in range(2):
            _, _, headers = self._req("/?token=" + TOK, accept="text/html", sec_fetch="document")
            vals.append(self._session_cookie_value(headers) or "")
        self.assertTrue(all(km._session_ok(v) for v in vals))
        self.assertFalse(vals[0] == vals[1], "two sign-ins, two sessions")
        self.assertFalse(km._migration_session() in vals, "neither is the migration session")

    def test_the_old_token_cookie_migrates_on_a_page_navigation_and_is_cleared(self):
        status, _, headers = self._req("/", extra_cookie="romp_token=" + TOK,
                                       accept="text/html", sec_fetch="document")
        self.assertEqual(status, 200, "the old cookie authorizes the page navigation, once")
        self.assertTrue(km._session_ok(self._session_cookie_value(headers) or ""),
                        "and this response mints a session")
        self.assertTrue(any(sc.startswith("romp_token=") and "Max-Age=0" in sc
                            for sc in self._set_cookies(headers)), "the old cookie is cleared")

    def test_the_old_token_cookie_is_refused_on_a_json_read_and_not_cleared(self):
        # The old cookie opens no data route, and with no session beside it, it is NOT cleared here.
        # Clearing it on such a response would sign out a dashboard left open across the upgrade (its
        # next poll or redial is not a navigation, so it would clear without migrating). It is cleared in
        # the migrating page navigation (above), and on any response to a request that carries a valid
        # session beside it (LegacyCookieClearedBesideASession).
        status, _, headers = self._req("/sessions", extra_cookie="romp_token=" + TOK)
        self.assertEqual(status, 403, "the old cookie opens no data route")
        self.assertFalse(any(sc.startswith("romp_token=") and "Max-Age=0" in sc
                             for sc in self._set_cookies(headers)),
                         "the old cookie is not cleared outside the migrating navigation")

    def test_a_different_kernels_old_cookie_is_not_cleared_on_the_migrating_navigation(self):
        # The clear fires only when the old cookie's value is THIS kernel's token. A romp_token
        # holding a DIFFERENT value (a second, older kernel on the same host) survives a login here.
        status, _, headers = self._req("/?token=" + TOK, extra_cookie="romp_token=another-kernels-token",
                                       accept="text/html", sec_fetch="document")
        self.assertEqual(status, 200)
        self.assertTrue(km._session_ok(self._session_cookie_value(headers) or ""), "a session is minted")
        self.assertFalse(any(sc.startswith("romp_token=") and "Max-Age=0" in sc
                             for sc in self._set_cookies(headers)),
                         "another kernel's romp_token is not cleared")


class _OneShotPeer(threading.Thread):
    """An attached host's kernel for the socket relay: accept one connection, read the forwarded upgrade,
    answer a 101 head carrying only the handshake headers, close."""
    daemon = True
    HEAD = b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n\r\n"

    def __init__(self):
        super().__init__()
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]

    def run(self):
        try:
            self.sock.settimeout(10)
            conn, _ = self.sock.accept()
            try:
                conn.settimeout(5)
                conn.recv(65536)
                conn.sendall(self.HEAD)
            finally:
                conn.close()
        except OSError:
            pass

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


class LegacyCookieClearedBesideASession(_Server):
    """The legacy romp_token cookie holding THIS kernel's token is cleared on ANY response to a request that
    also carries a valid session cookie of this kernel. The session shows the browser signed in without the old
    cookie. A request carries both when an earlier version, run after this one, set the old cookie again and this
    version then came back with the same token; the next response clears it. Apart from the response that signs
    the browser in, a request with no valid session keeps the old cookie (a dashboard that has not migrated still
    signs in with it), and a romp_token holding any other value is never cleared. The kinds below reach the browser by
    every road a response takes: _send, the file route's own headers (GET and HEAD), the preflight's, the
    socket upgrade's, and the socket relay's raw head. Counts, kinds and statuses only; no value is printed."""

    FORGED = SESS.partition(".")[0] + ".not-this-kernels-tag"     # this kernel's cookie name, a tag that does not match
    # each kind's status with a valid session: the road it names was taken (a refusal answers through _send, and
    # would prove nothing about the file route's, the preflight's or a socket's own headers)
    SIGNED_IN = {"a page navigation": 200, "a sign-in navigation": 200, "a page fetch": 200, "a static read": 200,
                 "a data read with the key": 200, "a data read without the key": 403, "a file load on its cap": 200,
                 "a file probe on its cap": 200, "a POST with the key": 404, "a preflight": 204,
                 "the sign-in page": 200, "the health probe": 200, "a socket upgrade": 101,
                 "a relayed socket upgrade": 101}

    def _clears(self, set_cookies):
        return sum(1 for sc in set_cookies if sc.startswith("romp_token=") and "Max-Age=0" in sc)

    def _upgrade(self, path, cookies):
        """A socket upgrade over a raw socket: (status, the Set-Cookie values of its head)."""
        s = socket.create_connection(("127.0.0.1", self.port), timeout=10)
        try:
            lines = ["GET %s HTTP/1.1" % path, "Host: 127.0.0.1:%d" % self.port, "Upgrade: websocket",
                     "Connection: Upgrade", "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==",
                     "Sec-WebSocket-Version: 13", "Cookie: " + cookies]
            s.sendall(("\r\n".join(lines) + "\r\n\r\n").encode())
            buf = b""
            while b"\r\n\r\n" not in buf:
                b = s.recv(4096)
                if not b:
                    break
                buf += b
            head = buf.split(b"\r\n\r\n", 1)[0].decode("latin-1").split("\r\n")
            status = int(head[0].split(" ")[1]) if head[0].count(" ") >= 1 else 0
            return status, [ln.split(":", 1)[1].strip() for ln in head[1:] if ln.lower().startswith("set-cookie:")]
        finally:
            s.close()

    def _relay_upgrade(self, cookies):
        peer = _OneShotPeer()
        peer.start()
        saved = dict(km._remotes)
        with km._remotes_lock:
            km._remotes["TESTHOST"] = {"host": "TESTHOST", "kernel_port": 29855, "local_port": peer.port,
                                       "token": "", "status": "up"}
        try:
            return self._upgrade("/remote/TESTHOST/ws?k=" + KEY, cookies)
        finally:
            with km._remotes_lock:
                km._remotes.clear()
                km._remotes.update(saved)
            peer.close()
            peer.join(timeout=5)

    def _answers(self, cookies, sign_ins=True):
        """(kind, status, clears) for one request of each kind, each carrying the Cookie header `cookies` and,
        where the kind takes one, this session's page key or cap. `sign_ins` adds the two navigations that
        sign a browser in (a page navigation, and a ?token= one), which migrate a legacy cookie on their own."""
        cap = "/file?path=%s&cap=%s" % (self.fpath, _cap(SESS, self.fpath, ""))
        out = []

        def http(kind, path, **kw):
            status, _, headers = self._req(path, extra_cookie=cookies, **kw)
            out.append((kind, status, self._clears(self._set_cookies(headers))))
        if sign_ins:
            http("a page navigation", "/", accept="text/html", sec_fetch="document")
            http("a sign-in navigation", "/?token=" + TOK, accept="text/html", sec_fetch="document")
        http("a page fetch", "/chat")
        http("a static read", "/sw.js")
        http("a data read with the key", "/sessions", key=KEY)
        http("a data read without the key", "/sessions")
        http("a file load on its cap", cap)
        http("a file probe on its cap", cap, method="HEAD")
        http("a POST with the key", "/no-such-route", method="POST", key=KEY)
        http("a preflight", "/sessions", method="OPTIONS", origin=self.origin, key=KEY)
        http("the sign-in page", "/login")
        http("the health probe", "/healthz")
        status, sc = self._upgrade("/ws?k=" + KEY, cookies)
        out.append(("a socket upgrade", status, self._clears(sc)))
        status, sc = self._relay_upgrade(cookies)
        out.append(("a relayed socket upgrade", status, self._clears(sc)))
        return out

    def test_a_retained_old_cookie_beside_a_valid_session_is_cleared_on_any_response(self):
        got = self._answers("%s=%s; romp_token=%s" % (CN, SESS, TOK))
        self.assertEqual({k: s for k, s, _ in got}, self.SIGNED_IN, "each kind reached the road it names")
        self.assertEqual([(k, s, c) for k, s, c in got if c != 1], [],
                         "each kind's response clears the old cookie once: (kind, status, clears) of those that do not")

    def test_a_request_with_no_valid_session_keeps_the_old_cookie(self):
        # a dashboard that has not migrated: its polls, reads and socket redials carry the old cookie and no
        # session, and none of their responses clears it (the navigation that migrates it clears it: above)
        for what, cookies in (("no session cookie", "romp_token=%s" % TOK),
                              ("a session cookie whose tag does not match", "%s=%s; romp_token=%s" % (CN, self.FORGED, TOK))):
            got = self._answers(cookies, sign_ins=False)
            self.assertEqual(len(got), 12)
            self.assertEqual([(k, s, c) for k, s, c in got if c], [],
                             "%s: the old cookie is kept: (kind, status, clears) of the responses that clear it" % what)

    def test_another_kernels_old_cookie_beside_a_valid_session_is_never_cleared(self):
        # a romp_token holding another value (a second, older kernel on the same host) beside this kernel's
        # valid session: no response clears it, the sign-in navigations included. The values close to this
        # kernel's token are there for the compare: the token's letters in the other case, the token with a
        # trailing "=", the token in double quotes, and the token after a space are other values, so a compare
        # that ignores case, or that trims quotes, spaces or "=" before it compares, clears one of them.
        for what, value in (("another kernel's value", "another-kernels-token"), ("the other case", TOK.swapcase()),
                            ("a trailing '='", TOK + "="), ("double quotes", '"%s"' % TOK), ("a leading space", " " + TOK)):
            self.assertNotEqual(value, TOK, "%s: a value other than this kernel's token" % what)
            got = self._answers("%s=%s; romp_token=%s" % (CN, SESS, value))
            self.assertEqual({k: s for k, s, _ in got}, self.SIGNED_IN, "%s: each kind reached the road it names" % what)
            self.assertEqual([(k, s, c) for k, s, c in got if c], [],
                             "%s: the cookie is not cleared: (kind, status, clears) of the responses that clear it" % what)

    def test_an_error_before_a_request_is_read_carries_no_clear_left_from_the_request_before_it(self):
        # One keep-alive connection: a request carrying the old cookie beside a valid session, whose response clears
        # it, then a request with more header lines than the server reads, which the server answers with a 431
        # before it has read that request's headers. The 431 reads nothing of the request before it, so it
        # carries no clear.
        s = socket.create_connection(("127.0.0.1", self.port), timeout=10)
        try:
            host = "Host: 127.0.0.1:%d\r\n" % self.port
            s.sendall(("GET /chat HTTP/1.1\r\n%sCookie: %s=%s; romp_token=%s\r\n\r\n" % (host, CN, SESS, TOK)).encode())
            s.sendall(("GET /chat HTTP/1.1\r\n" + host).encode() + b"".join(b"X-Filler-%d: 1\r\n" % i for i in range(120)) + b"\r\n")
            buf = b""
            while True:
                try:
                    b = s.recv(65536)
                except socket.timeout:
                    break
                if not b:
                    break
                buf += b
        finally:
            s.close()
        answers = []       # (status, clears) of each response on the connection, read head by head
        while buf.startswith(b"HTTP/"):
            end = buf.find(b"\r\n\r\n")
            if end < 0:
                break
            lines = buf[:end].decode("latin-1").split("\r\n")
            fields = [ln.split(":", 1) for ln in lines[1:] if ":" in ln]
            length = int(next((v for k, v in fields if k.strip().lower() == "content-length"), "0"))
            answers.append((int(lines[0].split(" ")[1]), self._clears([v.strip() for k, v in fields if k.strip().lower() == "set-cookie"])))
            buf = buf[end + 4 + length:]
        self.assertEqual(answers, [(200, 1), (431, 0)],
                         "the first response clears the old cookie, and the 431 after it on the same connection does not")


class NoPageDataInlined(_Server):
    """What a request on the session cookie alone can read holds code and no session data, and the page key
    reaches the browser only in the sign-in response. A census over every page route in the route table, on
    both response paths (the cookie alone, and a ?token= sign-in navigation), over /sw.js, and over every file
    under /media/. A synthetic session is planted in the kernel's session registry and names store, and a
    keyed /sessions read shows it, so the plant took; no cookie-only response carries its name, id or folder,
    nor the page key, the session id or the serve token. The built bundles under /dist/ are not assumed here
    (this module runs without a build); tests/test_file_caps_browser.py runs the same census over them on a
    lab kernel serving its dist."""

    PLANT_SID = "77777777-8888-9999-aaaa-bbbbbbbbbbbb"
    PLANT_NAME = "zqx-planted-web"
    PLANT_DIR = "/srv/zqx-planted-notes-api"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        km.NAMES.mkdir(parents=True, exist_ok=True)
        (km.NAMES / cls.PLANT_SID).write_text("%s\t%s\t#9cd2ff\t#0c1a2e\n" % (cls.PLANT_NAME, cls.PLANT_DIR))
        cls._live = km.Sessions.__dict__["live"]
        km.Sessions.live = staticmethod(lambda: {cls.PLANT_SID: {"state": "idle", "backend": "sdk"}})
        km._SESSIONS_LISTING["json"] = None

    @classmethod
    def tearDownClass(cls):
        km.Sessions.live = cls._live
        km._SESSIONS_LISTING["json"] = None
        try:
            (km.NAMES / cls.PLANT_SID).unlink()
        except OSError:
            pass
        super().tearDownClass()

    def _forbidden(self):
        return (("the page key", KEY), ("the session id", SESS), ("the serve token", TOK),
                ("a session's name", self.PLANT_NAME), ("a session's id", self.PLANT_SID),
                ("a session's folder", self.PLANT_DIR))

    def _pages(self):
        return sorted(p for p in km._PAGE_RENDERERS if p)       # "" is the bare-path spelling of "/"

    def test_the_planted_session_is_visible_to_a_keyed_read(self):
        status, body, _ = self._req("/sessions", cookie=SESS, key=KEY)
        self.assertEqual(status, 200)
        text = body.decode("utf-8", "replace")
        self.assertIn(self.PLANT_NAME, text, "the plant took: the listing names the planted session")
        self.assertIn(self.PLANT_SID, text)

    def test_no_cookie_only_response_carries_session_data_or_a_credential(self):
        media = sorted("/media/" + n for n in os.listdir(km.MEDIA) if os.path.isfile(os.path.join(km.MEDIA, n)))
        self.assertGreater(len(media), 3, "the census reads the asset tree: %d files" % len(media))
        paths = self._pages() + list(km._STATIC_EXACT) + media
        for path in paths:
            status, body, headers = self._req(path, cookie=SESS)
            self.assertEqual(status, 200, "the cookie alone serves %s" % path)
            text = body.decode("latin-1")
            for what, value in self._forbidden():
                self.assertFalse(value in text, "%s carries %s" % (path, what))
            self.assertFalse(SEED_SET in text, "%s carries the key seed" % path)
            self.assertEqual(self._set_cookies(headers), [], "%s sets no cookie" % path)
        _, sw, _ = self._req("/sw.js", cookie=SESS)
        swtext = sw.decode("utf-8", "replace")
        self.assertNotIn("caches.", swtext, "the service worker caches nothing (no page data cached)")
        self.assertNotIn("cache.addAll", swtext)

    def test_the_page_key_is_in_the_sign_in_response_alone_and_once(self):
        for path in self._pages():
            status, body, headers = self._req(path + "?token=" + TOK, accept="text/html", sec_fetch="document")
            self.assertEqual(status, 200, "a sign-in on %s" % path)
            sv = self._session_cookie_value(headers) or ""
            self.assertTrue(km._session_ok(sv), "%s: the sign-in set a session" % path)
            text = body.decode("utf-8", "replace")
            self.assertEqual(text.count(json.dumps(km._page_key(sv))), 1, "%s: the page key, exactly once" % path)
            self.assertEqual(text.count(SEED_SET), 1, "%s: one seed" % path)
            for what, value in self._forbidden()[2:]:
                self.assertFalse(value in text, "%s's sign-in response carries %s" % (path, what))
            self.assertFalse(sv in text, "%s's sign-in response carries its session id" % path)


if __name__ == "__main__":
    unittest.main()
