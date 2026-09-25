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
                self.assertNotEqual(value, TOK, "no Set-Cookie may equal the serve token (%s)" % path)


class CookieOpensPageAndStaticOnly(_Server):
    def test_the_route_table_is_the_page_class(self):
        # condition 3: page and static are DERIVED from the one route table the router dispatches from.
        self.assertEqual(set(km._PAGE_RENDERERS),
                         {"", "/", "/chat", "/feed", "/timeline", "/fleet", "/waiting", "/files", "/settings"},
                         "the page route table (both the router and _need read this)")
        for p in km._PAGE_RENDERERS:
            self.assertEqual(km.Handler._need(p), ("page", ""), "%r classes as page" % p)
        for p in ("/sw.js", "/dist/x.js", "/media/icon.svg"):
            self.assertEqual(km.Handler._need(p)[0], "static", "%r classes as static" % p)

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


class DomainSeparation(_Server):
    """Condition 1: a value minted for one role is refused where another role's value is required.
    Each pin is green here and red under the label-sharing mutant its name states (see
    build-checklist.md); the sid-as-token pin is red at fa3ef54b5 (FailingBefore, above)."""

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

    def test_the_page_key_presented_as_a_session_is_refused(self):   # B11: K is not a valid session id
        self.assertFalse(km._session_ok(KEY), "the page key is not a session id")
        self.assertEqual(self._status("/chat", cookie=KEY), 403, "K in the cookie opens no page")

    def test_the_session_cookies_value_is_refused_in_every_credential_slot(self):
        # The session cookie's VALUE and its tag half (the HMAC after the ".") are neither a page
        # key, a cap nor the serve token, so presenting either in any of those slots authorizes
        # nothing. (The value's one use, as the session cookie, opens only the page and static
        # classes, covered above.)
        tag = SESS.split(".", 1)[1]
        for v in (SESS, tag):
            self.assertEqual(self._status("/sessions", cookie=SESS, key=v), 403, "not the page key")
            self.assertEqual(self._ws_status("app=chat&k=" + v, cookie=SESS, origin=self.origin), 403, "not k=")
            self.assertEqual(self._status("/file?path=%s&cap=%s" % (self.fpath, v), cookie=SESS), 403, "not a cap")
            self.assertEqual(self._status("/sessions?token=" + v), 403, "not the ?token=")
            self.assertEqual(self._status("/sessions", xtoken=v), 403, "not the X-Romp-Token")


class RouteClassesDerivedFromTheRegister(_Server):
    """B10 / condition 3: the page and static classes are DERIVED from the route table the router reads,
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
    """B2: a valid session whose stored key no longer matches gets a DISTINCT 403 (X-Romp-Reauth) so
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
    """B9 / critic C2: the login's cookie and seed are per-request. A data request that reuses the same
    keep-alive connection after a login navigation must carry no Set-Cookie and no key seed."""

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


class CookieOnlyClassBare500(_Server):
    """B15: a page or static render that raises answers a BARE 500, never a traceback that could name an
    internal path or state, because the session cookie alone reaches those classes. A class that needs
    the page key keeps its traceback for the operator."""

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
        self.assertEqual(self._session_cookie_value(headers), SESS, "the existing session is kept")

    def test_login_page_is_exempt(self):
        self.assertEqual(self._status("/login"), 200)


class LegacyCookieMigration(_Server):
    def test_the_old_token_cookie_migrates_on_a_page_navigation_and_is_cleared(self):
        status, _, headers = self._req("/", extra_cookie="romp_token=" + TOK,
                                       accept="text/html", sec_fetch="document")
        self.assertEqual(status, 200, "the old cookie authorizes the page navigation, once")
        self.assertTrue(km._session_ok(self._session_cookie_value(headers) or ""),
                        "and this response mints a session")
        self.assertTrue(any(sc.startswith("romp_token=") and "Max-Age=0" in sc
                            for sc in self._set_cookies(headers)), "the old cookie is cleared")

    def test_the_old_token_cookie_is_refused_on_a_json_read_and_not_cleared(self):
        # B1: the old cookie opens no data route, and it is NOT cleared here. Clearing it on a
        # non-migrating response would sign out a dashboard left open across the upgrade (its next
        # poll or redial is not a navigation, so it would clear without migrating) and a second, older
        # kernel on the same host. It is cleared ONLY in the migrating page navigation (above).
        status, _, headers = self._req("/sessions", extra_cookie="romp_token=" + TOK)
        self.assertEqual(status, 403, "the old cookie opens no data route")
        self.assertFalse(any(sc.startswith("romp_token=") and "Max-Age=0" in sc
                             for sc in self._set_cookies(headers)),
                         "the old cookie is not cleared outside the migrating navigation")

    def test_a_different_kernels_old_cookie_is_not_cleared_on_the_migrating_navigation(self):
        # B1: the clear fires only when the old cookie's value is THIS kernel's token. A romp_token
        # holding a DIFFERENT value (a second, older kernel on the same host) survives a login here.
        status, _, headers = self._req("/?token=" + TOK, extra_cookie="romp_token=another-kernels-token",
                                       accept="text/html", sec_fetch="document")
        self.assertEqual(status, 200)
        self.assertTrue(km._session_ok(self._session_cookie_value(headers) or ""), "a session is minted")
        self.assertFalse(any(sc.startswith("romp_token=") and "Max-Age=0" in sc
                             for sc in self._set_cookies(headers)),
                         "another kernel's romp_token is not cleared")


class NoPageDataInlined(_Server):
    """Condition 3 census: a page or bundle served on the cookie alone carries no secret; the page
    key reaches the browser only in the login seed. Red under a mutant that seeds the key on every
    page (see build-checklist.md)."""

    def test_a_cookie_only_page_carries_the_reader_but_neither_the_seed_nor_any_secret(self):
        _, body, _ = self._req("/chat", cookie=SESS)
        text = body.decode("utf-8", "replace")
        self.assertIn("__rompPageKey", text, "the page-key reader is present")
        self.assertNotIn(SEED_SET, text, "the key seed is not on a cookie-only page")
        for secret in (KEY, SESS, TOK):
            self.assertNotIn(secret, text, "no session id, page key or serve token is inlined")

    def test_the_worker_and_a_bundle_carry_no_secret_and_the_worker_caches_nothing(self):
        _, sw, _ = self._req("/sw.js", cookie=SESS)
        swtext = sw.decode("utf-8", "replace")
        for secret in (KEY, SESS, TOK):
            self.assertNotIn(secret, swtext, "the service worker inlines no secret")
        self.assertNotIn("caches.", swtext, "the service worker caches nothing (no page data cached)")
        self.assertNotIn("cache.addAll", swtext)


if __name__ == "__main__":
    unittest.main()
