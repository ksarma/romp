#!/usr/bin/env python3
"""Two kernels on one host keep two sign-ins: the session cookie's name and the page key's storage slot are each kernel's own.

Two kernels on one machine (a kernels.json profile beside the primary, a peer reached over an ssh forward) share the
browser's cookies for that host, one cookie jar. The session cookie's name is a function of the serve token
(kernel.py _SESSION_COOKIE), and the slot the page key is stored under follows it (_PAGE_KEY_SLOT), so each kernel's
sign-in is kept under a name of its own. With one fixed name, signing in to the second kernel would replace the first
kernel's session cookie, and every keyed read an open tab of the first kernel makes would be refused. With a name drawn
at random when the kernel starts, a restart would rename the cookie and sign every browser out. Site storage, unlike the
cookie jar, is partitioned by origin, port included, so two kernels on two ports never share a key slot whatever it is
named. The slot's name is for one address over time: a key minted under one serve token is never read under another
there (after a rotation, or when a reused port or an ssh forward is answered by another kernel).

This module loads the kernel twice in this process under two serve tokens (two private module names), and once more in
a child process under the first token (a restart), and asserts:

  1. the two tokens give two cookie names and two key slots;
  2. the first token gives the same cookie name and key slot again in the fresh process;
  3. with one cookie jar for the host (the stdlib's, which keys its cookies by host as a browser does), a keyed read
     of kernel A still answers 200 after a ?token= sign-in to kernel B, the jar holds one session cookie for each
     kernel, and B's keyed read answers 200 too.

Synthetic only: two invented serve tokens minted at run time. No token, session id or page key VALUE is printed.
"""
import http.cookiejar
import json
import os
import re
import secrets
import subprocess
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from romp_load import load_source
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

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

LOADS = [("romp_event_model", os.path.join(BIN, "romp-event-model")),
         ("romp_judge", os.path.join(BIN, "romp-judge")),
         ("romp_kernel_restarted", os.path.join(BIN, "romp-kernel"))]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **kw):
        return None


class TwoKernelsOnOneHost(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        had = os.environ.get("ROMP_SERVE_TOKEN")
        cls.addClassCleanup(lambda: os.environ.__setitem__("ROMP_SERVE_TOKEN", had) if had is not None
                            else os.environ.pop("ROMP_SERVE_TOKEN", None))
        cls.tok_a = "percookie-a-" + secrets.token_hex(12)
        cls.tok_b = "percookie-b-" + secrets.token_hex(12)
        # PRIVATE module names (test_kernel_auth_hardening.py's note): load_source re-executes a name already in
        # sys.modules into the SAME module object, so each kernel gets a name no sibling uses, and the token is set
        # for each load (TOKEN is read at import).
        os.environ["ROMP_SERVE_TOKEN"] = cls.tok_a
        cls.ka = load_source("romp_kernel_percookie_a", os.path.join(BIN, "romp-kernel"))
        os.environ["ROMP_SERVE_TOKEN"] = cls.tok_b
        cls.kb = load_source("romp_kernel_percookie_b", os.path.join(BIN, "romp-kernel"))
        cls.servers = []
        for k in (cls.ka, cls.kb):
            srv = ThreadingHTTPServer(("127.0.0.1", 0), k.Handler)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            cls.servers.append(srv)
            cls.addClassCleanup(srv.server_close)
            cls.addClassCleanup(srv.shutdown)
        cls.origin_a, cls.origin_b = ("http://127.0.0.1:%d" % s.server_address[1] for s in cls.servers)

    def test_two_serve_tokens_give_two_cookie_names_and_two_key_slots(self):
        self.assertEqual((self.ka.TOKEN, self.kb.TOKEN), (self.tok_a, self.tok_b), "each load read its own token")
        self.assertTrue(self.ka._SESSION_COOKIE.startswith("romp_s_") and self.kb._SESSION_COOKIE.startswith("romp_s_"))
        self.assertNotEqual(self.ka._SESSION_COOKIE, self.kb._SESSION_COOKIE, "each kernel's session cookie has its own name")
        self.assertNotEqual(self.ka._PAGE_KEY_SLOT, self.kb._PAGE_KEY_SLOT, "and its page key its own storage slot")

    def test_the_same_serve_token_gives_the_same_name_and_slot_after_a_restart(self):
        """A second load under the first token, in a fresh process as a restart would be: the name and the slot come back
        unchanged, so a restart keeps every browser signed in. An inequality alone would also pass a name drawn at
        random for each start."""
        child = tempfile.mkdtemp()
        with open(os.path.join(child, "session-hosts"), "w") as fh:
            fh.write("off\n")
        env = dict(os.environ, ROMP_SERVE_TOKEN=self.tok_a, ROMP_STATE_DIR=child, ROMP_KERNEL_NO_OPEN="1")
        code = ("import json, sys; sys.path.insert(0, %r)\n"          # the tests dir, where romp_load lives
                "from romp_load import load_source\n"
                "for name, path in %r:\n"
                "    km = load_source(name, path)\n"
                "sys.stdout.write('NAMES:' + json.dumps([km._SESSION_COOKIE, km._PAGE_KEY_SLOT]) + '\\n')\n" % (HERE, LOADS))
        r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, "the restarted kernel loaded; stderr:\n%s" % r.stderr[-2000:])
        line = next((ln for ln in r.stdout.splitlines() if ln.startswith("NAMES:")), None)
        self.assertIsNotNone(line, "the child reported the two names")
        self.assertEqual(json.loads(line[len("NAMES:"):]), [self.ka._SESSION_COOKIE, self.ka._PAGE_KEY_SLOT],
                         "the same serve token names the same cookie and the same key slot in a fresh process")

    def _open(self, opener, url, key=None, navigation=False):
        req = urllib.request.Request(url)
        if key is not None:
            req.add_header("X-Romp-Key", key)
        if navigation:
            req.add_header("Accept", "text/html")
            req.add_header("Sec-Fetch-Dest", "document")
        try:
            with opener.open(req, timeout=15) as r:
                return r.status, r.read().decode("utf-8", "replace"), r.headers
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace"), e.headers

    def _sign_in(self, opener, origin, token, km):
        """A ?token= navigation to one kernel: the page key its seed stores, and the slot the seed stores it under."""
        status, body, _ = self._open(opener, origin + "/?token=" + token, navigation=True)
        self.assertEqual(status, 200, "the sign-in page loads")
        m = re.search(r"localStorage\.setItem\((\"[^\"]*\"),(\"[^\"]*\")\)", body)
        self.assertIsNotNone(m, "the sign-in response carries the seed that stores the page key")
        slot, key = json.loads(m.group(1)), json.loads(m.group(2))
        self.assertEqual(slot, km._PAGE_KEY_SLOT, "the seed stores the key under this kernel's own slot")
        return key

    def test_a_sign_in_to_a_second_kernel_on_the_host_leaves_the_first_signed_in(self):
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar), _NoRedirect())
        key_a = self._sign_in(opener, self.origin_a, self.tok_a, self.ka)
        # the jar is keyed by host, as a browser's is, so B's sign-in below writes into the same jar A's cookie lives in
        # (a jar that kept the two kernels apart would make this test pass on its own)
        probe = urllib.request.Request(self.origin_b + "/")
        jar.add_cookie_header(probe)
        self.assertIn(self.ka._SESSION_COOKIE + "=", probe.get_header("Cookie") or "",
                      "one jar for the host: kernel A's cookie is in the jar kernel B's sign-in writes to")
        self.assertEqual(self._open(opener, self.origin_a + "/sessions", key=key_a)[0], 200, "A's keyed read, signed in to A")
        key_b = self._sign_in(opener, self.origin_b, self.tok_b, self.kb)
        self.assertEqual(self._open(opener, self.origin_a + "/sessions", key=key_a)[0], 200,
                         "kernel A's keyed read still answers after the sign-in to kernel B")
        self.assertEqual(self._open(opener, self.origin_b + "/sessions", key=key_b)[0], 200, "and kernel B's answers too")
        self.assertEqual(sorted(c.name for c in jar if c.name.startswith("romp_s_")),
                         sorted([self.ka._SESSION_COOKIE, self.kb._SESSION_COOKIE]),
                         "the jar holds one session cookie for each kernel, under each kernel's own name")


if __name__ == "__main__":
    unittest.main()
