#!/usr/bin/env python3
"""Regression guards for the romp-kernel serve-layer auth gate (_authorize):

  L2 — the serve token is compared in constant time (hmac.compare_digest), not
       with ==, so a network (tailnet) client gets no timing oracle on the token.
  Token-everywhere — the serve token is REQUIRED on every gated route, loopback
       included (Jupyter's model: loopback is reachable by every local user on
       the machine, so the 0600 token file — not the socket — is the same-user
       trust boundary). The old loopback bypass (and with it the whole notion of
       "locality") is gone: a token-less loopback request is denied, and the Host
       header carries no authorization weight in any direction. Accepted forms:
       ?token= (browser bootstrap, seeds the cookie), the romp_token cookie, and
       the X-Romp-Token header (CLI/hooks/daemons).

Synthetic only — no real session data; the gate decision touches no session state.
Mirrors tests/test_kernel_ws_auth.py's module load order.
"""
import os
import time
import unittest
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

SourceFileLoader("romp_event_model", os.path.join(BIN, "romp-event-model")).load_module()
SourceFileLoader("romp_judge", os.path.join(BIN, "romp-judge")).load_module()
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
km = SourceFileLoader("romp_kernel", os.path.join(BIN, "romp-kernel")).load_module()

TOK = km.TOKEN


def _inst(peer="127.0.0.1", headers=None):
    """A Handler with just enough state to call _authorize (no socket). `peer` is
    the TCP client IP (self.client_address[0]); `headers` are the request headers
    (Host / Origin / Cookie / X-Romp-Token)."""
    h = km.Handler.__new__(km.Handler)
    h.client_address = None if peer is None else (peer, 0)
    h.headers = dict(headers or {})
    return h


def _auth(peer="127.0.0.1", headers=None, token=None):
    q = {"token": [token]} if token is not None else {}
    return _inst(peer, headers)._authorize(q)


class TokenCompare(unittest.TestCase):
    def test_ct_eq_matches_and_differs(self):
        self.assertTrue(km._ct_eq("abc", "abc"))
        self.assertFalse(km._ct_eq("abc", "abd"))
        self.assertFalse(km._ct_eq("abc", "abcd"))   # length differs

    def test_ct_eq_never_raises_on_odd_input(self):
        self.assertFalse(km._ct_eq(None, "x"))
        self.assertFalse(km._ct_eq("x", None))


class TokenRequiredEverywhere(unittest.TestCase):
    def test_tokenless_loopback_denied(self):
        # THE hardening this file pins: a loopback peer with no credential is DENIED —
        # loopback is shared by every local user, so it can't be a trust boundary. This
        # is what keeps a same-host co-tenant out of every authed route reached through
        # _authorize, incl. POST /send (prompt injection into live agents).
        for peer in ("127.0.0.1", "::1", "::ffff:127.0.0.1"):
            ok, _, why = _auth(peer=peer)
            self.assertFalse(ok, "token-less loopback (%s) must be denied" % peer)
            self.assertIn("token", why)

    def test_forged_local_host_headers_do_not_authorize(self):
        # The old M3 bypass, now moot by construction: Host carries no auth weight at all.
        for host in ("localhost", "127.0.0.1", "localhost:29855", "::1"):
            ok, _, _ = _auth(peer="203.0.113.9", headers={"Host": host})
            self.assertFalse(ok, "Host: %s must not authorize" % host)
        ok, _, _ = _auth(peer="127.0.0.1", headers={"Host": "localhost"})
        self.assertFalse(ok, "a local Host on a loopback peer still needs the token")

    def test_query_token_authorizes_and_seeds_cookie(self):
        ok, cookie, _ = _auth(token=TOK)
        self.assertTrue(ok)
        self.assertEqual(cookie, TOK)     # ?token= sets the cookie so the browser never re-prompts

    def test_cookie_authorizes(self):
        ok, cookie, _ = _auth(headers={"Cookie": "romp_token=" + TOK})
        self.assertTrue(ok)
        self.assertIsNone(cookie)         # already has it — no re-set

    def test_cookie_denied_from_a_foreign_origin(self):
        """The loopback-dev-server hole. Cookies are scoped by host and NOT by port
        (RFC 6265 8.5), so a page served by anything else on 127.0.0.1 — an agent-cloned
        repo's dev server — is same-site with the dashboard and the browser attaches this
        cookie for it, SameSite=Strict included. Before this gate that page could open /ws
        (which streams every session and accepts sendMessage) with no credential of its own."""
        ok, _, why = _auth(headers={"Cookie": "romp_token=" + TOK,
                                    "Origin": "http://127.0.0.1:5173",
                                    "Host": "127.0.0.1:%d" % km.PORT})
        self.assertFalse(ok)
        self.assertEqual(why, "cross-site origin")

    def test_cookie_still_authorizes_the_dashboards_own_origin(self):
        # The shipped dashboard socket (kernel.py's connect(): location.host, no token)
        # rides the cookie same-origin — the gate must not cost it anything.
        host = "127.0.0.1:%d" % km.PORT
        ok, _, _ = _auth(headers={"Cookie": "romp_token=" + TOK,
                                  "Origin": "http://" + host, "Host": host})
        self.assertTrue(ok)

    def test_cookie_still_authorizes_tailnet_self_access(self):
        # Reaching the dashboard from the phone over the tailnet: Origin and Host are both
        # the tailnet name, which is same-origin and must keep working.
        ok, _, _ = _auth(headers={"Cookie": "romp_token=" + TOK,
                                  "Origin": "http://TESTHOST:%d" % km.PORT,
                                  "Host": "TESTHOST:%d" % km.PORT})
        self.assertTrue(ok)

    def test_cookie_still_authorizes_the_vscode_webview(self):
        ok, _, _ = _auth(headers={"Cookie": "romp_token=" + TOK,
                                  "Origin": "vscode-webview://abc123"})
        self.assertTrue(ok)

    def test_explicit_token_still_bypasses_origin_for_federation(self):
        # The bypass that must SURVIVE: a foreign-origin browser presenting the token
        # explicitly is federation, not a drive-by page. Both explicit forms keep it.
        ok, _, _ = _auth(headers={"Origin": "http://evil.example"}, token=TOK)
        self.assertTrue(ok)
        ok, _, _ = _auth(headers={"Origin": "http://evil.example", "X-Romp-Token": TOK})
        self.assertTrue(ok)

    def test_a_one_time_handoff_code_authorizes_and_sets_the_cookie(self):
        """What `romp` puts in the browser's argv. The URL we open is readable by every other
        account on the machine (/proc/<pid>/cmdline) for the browser's whole lifetime, so it
        carries a code that does one job — seed the cookie — instead of the long-lived token."""
        code = km._mint_handoff()
        ok, cookie, _ = _auth(headers={}, token=None)
        self.assertFalse(ok, "sanity: no credential without the code")
        h = _inst("127.0.0.1", {})
        ok, cookie, _ = h._authorize({"c": [code]})
        self.assertTrue(ok)
        self.assertEqual(cookie, TOK, "the handoff's whole purpose is to seed the cookie")

    def test_a_handoff_code_works_exactly_once(self):
        # The leak this defends against is a URL that persists; a code someone reads later must
        # already be spent.
        code = km._mint_handoff()
        self.assertTrue(_inst("127.0.0.1", {})._authorize({"c": [code]})[0])
        ok, _, why = _inst("127.0.0.1", {})._authorize({"c": [code]})
        self.assertFalse(ok)
        self.assertIn("token", why)

    def test_an_expired_handoff_code_is_refused(self):
        code = km._mint_handoff()
        with km._HANDOFF_LOCK:
            km._HANDOFF[code] = time.time() - 1        # as if the browser took too long to open
        self.assertFalse(_inst("127.0.0.1", {})._authorize({"c": [code]})[0])

    def test_an_unminted_code_is_refused(self):
        self.assertFalse(_inst("127.0.0.1", {})._authorize({"c": ["not-a-real-code"]})[0])
        self.assertFalse(_inst("127.0.0.1", {})._authorize({"c": [""]})[0])

    def test_the_handoff_is_not_the_token(self):
        # A code must never be the token itself, or the leak it exists to prevent is unchanged.
        self.assertNotEqual(km._mint_handoff(), TOK)

    def test_expired_codes_do_not_accumulate(self):
        # A browser that never opens leaves its code behind; minting must sweep them.
        before = len(km._HANDOFF)
        stale = km._mint_handoff()
        with km._HANDOFF_LOCK:
            km._HANDOFF[stale] = time.time() - 1
        km._mint_handoff()
        self.assertNotIn(stale, km._HANDOFF)
        self.assertLessEqual(len(km._HANDOFF), before + 1)

    def test_header_authorizes(self):
        # X-Romp-Token: the CLI/hook/daemon form (read from the 0600 file). Safe to accept
        # regardless of Origin: a cross-site page's custom header forces a CORS preflight,
        # which runs this same gate and fails without the token.
        ok, cookie, _ = _auth(headers={"X-Romp-Token": TOK})
        self.assertTrue(ok)
        self.assertIsNone(cookie)

    def test_wrong_credentials_denied(self):
        self.assertFalse(_auth(token="wrong")[0])
        self.assertFalse(_auth(headers={"Cookie": "romp_token=wrong"})[0])
        self.assertFalse(_auth(headers={"X-Romp-Token": "wrong"})[0])

    def test_valid_token_bypasses_origin_gate_wrong_token_does_not(self):
        # Federation: a foreign-Origin browser (served by ANOTHER kernel) carrying this
        # kernel's token through the tunnel must authorize; without it the Origin gate holds.
        ok, _, _ = _auth(headers={"Origin": "http://evil.example"}, token=TOK)
        self.assertTrue(ok)
        ok, _, why = _auth(headers={"Origin": "http://evil.example"}, token="wrong")
        self.assertFalse(ok)
        self.assertEqual(why, "cross-site origin")

    def test_remote_peer_denied_without_token(self):
        ok, _, why = _auth(peer="100.92.170.123")
        self.assertFalse(ok)
        self.assertIn("token", why)


if __name__ == "__main__":
    unittest.main(verbosity=2)
