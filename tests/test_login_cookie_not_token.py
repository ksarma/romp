#!/usr/bin/env python3
"""The login cookie's value is refused as the explicit token (kernel/kernel.py _authorize).

The ruling's failing-before test, kept self-contained (it names none of the session-cookie helpers)
so it runs against a kernel before OR after the change. A ?token= navigation returns the login
cookie. Its value is read in-process and never printed; presenting that value as the explicit token
(the X-Romp-Token header, or ?token=) authenticates nothing. At fa3ef54b5 the cookie's value IS the
serve token and is accepted, so both assertions are red there; after the change the cookie carries a
session id that is not the token, so they hold.

Synthetic only: an invented serve token, no session state touched.
"""
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

# Hermetic state BEFORE the loads: they resolve their state root at import time.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
km = load_source("romp_kernel_logincookie", os.path.join(BIN, "romp-kernel"))

TOK = km.TOKEN


class LoginCookieValue(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def _req(self, path, headers=None):
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path), headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, r.headers
        except urllib.error.HTTPError as e:
            return e.code, e.headers

    def test_the_login_cookies_value_is_refused_as_the_explicit_token(self):
        # a ?token= navigation returns the login cookie
        status, headers = self._req("/?token=" + TOK,
                                    {"Accept": "text/html", "Sec-Fetch-Dest": "document"})
        self.assertEqual(status, 200)
        setc = headers.get_all("Set-Cookie") or []
        value = None
        for sc in setc:
            v = sc.partition("=")[2].split(";", 1)[0]
            if v and "Max-Age=0" not in sc:
                value = v
                break
        self.assertIsNotNone(value, "the login navigation sets a cookie")
        # the cookie's value is not the serve token, and is refused as the explicit token
        self.assertNotEqual(value, TOK, "the login cookie must not carry the serve token")
        self.assertEqual(self._req("/sessions", {"X-Romp-Token": value})[0], 403,
                         "the cookie value is not the X-Romp-Token")
        self.assertEqual(self._req("/sessions?token=" + value)[0], 403,
                         "the cookie value is not the ?token=")


if __name__ == "__main__":
    unittest.main()
