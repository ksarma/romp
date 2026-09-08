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
import io
import json
import os
import socket
import threading
import time
import unittest
from http.client import HTTPMessage
from http.server import ThreadingHTTPServer
from pathlib import Path
from romp_load import load_source
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
# A PRIVATE module name: load_source re-executes a name already in sys.modules into the SAME module
# object, so a sibling module that loads "romp_kernel" after another sibling has set a different
# ROMP_SERVE_TOKEN rebinds km.TOKEN under this module and TOK below goes stale (36 gate tests answered
# 403 in one xdist worker, 2026-09-08). sb below already carries its own name for the same reason.
km = load_source("romp_kernel_authhard", os.path.join(BIN, "romp-kernel"))
sb = load_source("romp_sdk_backend_authhard", os.path.join(BIN, "romp_sdk_backend.py"))

TOK = km.TOKEN


def _inst(peer="127.0.0.1", headers=None):
    """A Handler with just enough state to call _authorize (no socket). `peer` is
    the TCP client IP (self.client_address[0]); `headers` are the request headers
    (Host / Origin / Cookie / X-Romp-Token)."""
    h = km.Handler.__new__(km.Handler)
    h.client_address = None if peer is None else (peer, 0)
    h.headers = dict(headers or {})
    return h


def _serve_get(path, headers=None):
    """Drive the REAL do_GET dispatcher over a fake socket and return (status, body).

    Asserting on a route's position in the source cannot catch a route served on the wrong side of
    the gate; asking the handler is the only thing that can."""
    h = km.Handler.__new__(km.Handler)
    h.client_address = ("127.0.0.1", 0)
    h.headers = dict(headers or {})
    h.path = path
    h.command = "GET"
    h.request_version = "HTTP/1.1"
    h.wfile = io.BytesIO()
    h.rfile = io.BytesIO()
    h.close_connection = True
    captured = {}

    def send_response(code, *a):
        captured["status"] = code

    def send_header(k, v):
        captured.setdefault("headers", {})[k] = v

    h.send_response = send_response
    h.send_header = send_header
    h.end_headers = lambda: None
    h.log_message = lambda *a: None
    h.do_GET()
    return captured.get("status"), h.wfile.getvalue().decode("utf-8", "replace")


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

    def test_unspent_codes_within_the_ttl_are_bounded(self):
        # The sweep above only reclaims EXPIRED codes; a flood inside the 300s window (a hostile
        # same-site loopback page riding the cookie hits /handoff in a loop) would otherwise grow the
        # dict without bound and turn the per-mint O(n) sweep quadratic. The cap holds the live set to
        # _HANDOFF_MAX no matter how many are minted before any expires.
        with km._HANDOFF_LOCK:
            km._HANDOFF.clear()
        for _ in range(km._HANDOFF_MAX * 3):
            km._mint_handoff()
        self.assertLessEqual(len(km._HANDOFF), km._HANDOFF_MAX,
                             "unspent codes must stay bounded within the TTL window")

    def test_an_uncredentialed_request_mints_no_handoff_code(self):
        """/handoff mints a credential, so reaching it must cost one.

        This replaces a source-position assertion that could not fail: it compared the route's
        offset against `src.index("ok, self._set_cookie, why = self._authorize(q)")`, and that line
        occurs three times — do_HEAD's copy comes first, so the anchor was another function's gate
        and the comparison held even with the route moved beside the auth-exempt /healthz. Drive
        the real dispatcher instead, and count the codes: a refusal that still minted one would
        leave a live credential behind for its whole TTL."""
        for headers in ({}, {"Origin": "http://127.0.0.1:5173", "Host": "127.0.0.1:%d" % km.PORT},
                        {"Cookie": "romp_token=wrong"}):
            before = len(km._HANDOFF)
            status, body = _serve_get("/handoff", headers)
            self.assertEqual(status, 403, "no credential must not reach /handoff (%r)" % headers)
            self.assertNotIn("code", body)
            self.assertEqual(len(km._HANDOFF), before, "a refused request must mint nothing")

    def test_a_credentialed_request_does_get_a_code(self):
        # The other half: the gate must not be so tight that `romp` cannot open a browser.
        before = len(km._HANDOFF)
        status, body = _serve_get("/handoff", {"X-Romp-Token": TOK})
        self.assertEqual(status, 200)
        self.assertIn("code", json.loads(body))
        self.assertEqual(len(km._HANDOFF), before + 1)

    def test_defaults_needs_a_credential_and_carries_the_path(self):
        status, _ = _serve_get("/defaults", {})
        self.assertEqual(status, 403, "a filesystem path must not ride an ungated route")
        status, body = _serve_get("/defaults", {"X-Romp-Token": TOK})
        self.assertEqual(status, 200)
        # ...and it really carries the value, so the gear's field is not silently empty.
        self.assertIsInstance(json.loads(body).get("defaultDir"), str)
        self.assertNotIn("defaultDir", km._version_info())

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


class CookieDoesNotBypassOrigin(unittest.TestCase):
    """The cookie is the one credential the browser attaches for you, so it is the one that must
    NOT bypass the Origin gate. Cookies are host- not port-scoped (RFC 6265 §8.5), so every
    http://127.0.0.1:<port> page is same-site with the dashboard and rides this cookie — SameSite
    included. Without the Origin check, any page served by anything else on loopback (a dev server
    in a repo an agent cloned) reached /ws, which streams every session and accepts sendMessage."""

    def test_cookie_denied_from_a_foreign_loopback_origin(self):
        # the drive-by case: a page on another loopback PORT is same-site, so the browser attaches
        # the cookie, but its Origin is not ours → the cookie must not authorize
        ok, _, why = _auth(headers={"Cookie": "romp_token=" + TOK,
                                    "Origin": "http://127.0.0.1:59999",
                                    "Host": "127.0.0.1:%d" % km.PORT})
        self.assertFalse(ok, "a cookie from another loopback port must not authorize")
        self.assertEqual(why, "cross-site origin")

    def test_cookie_denied_from_an_offsite_origin(self):
        ok, _, why = _auth(headers={"Cookie": "romp_token=" + TOK, "Origin": "http://evil.example"})
        self.assertFalse(ok)
        self.assertEqual(why, "cross-site origin")

    def test_cookie_still_authorizes_absent_origin(self):
        # a same-origin GET omits Origin; that path (and non-browser clients) is unchanged
        ok, _, _ = _auth(headers={"Cookie": "romp_token=" + TOK})
        self.assertTrue(ok, "a cookie with no Origin (same-origin nav / curl) still authorizes")

    def test_cookie_still_authorizes_the_dashboards_own_origin(self):
        ok, _, _ = _auth(headers={"Cookie": "romp_token=" + TOK,
                                  "Origin": "http://127.0.0.1:%d" % km.PORT,
                                  "Host": "127.0.0.1:%d" % km.PORT})
        self.assertTrue(ok)

    def test_cookie_still_authorizes_the_vscode_webview(self):
        ok, _, _ = _auth(headers={"Cookie": "romp_token=" + TOK,
                                  "Origin": "vscode-webview://0p9m1abc"})
        self.assertTrue(ok, "the VS Code webview origin is allowed by _origin_ok")

    def test_explicit_token_still_bypasses_origin_for_federation(self):
        # the escape hatch a cross-site page cannot use: only an EXPLICIT token bypasses origin,
        # and a drive-by page can't obtain one (it rides only the cookie)
        ok, _, _ = _auth(headers={"Origin": "http://evil.example"}, token=TOK)
        self.assertTrue(ok)


class ResponseHardeningHeaders(unittest.TestCase):
    """Every response declares its type as final (nosniff) and refuses cross-origin framing
    (clickjacking). Source-pinned: the header set lives in _send, exercised on every route."""

    def test_send_sets_nosniff_and_frame_guards(self):
        import inspect
        src = inspect.getsource(km.Handler._send)
        self.assertIn('"X-Content-Type-Options", "nosniff"', src)
        self.assertIn('"X-Frame-Options", "SAMEORIGIN"', src)
        self.assertIn("frame-ancestors 'self'", src)

    def test_remote_relay_derives_its_own_mime_and_discards_the_remotes(self):
        # the /remote/<host>/file relay must decide the Content-Type from the requested extension
        # (_PREVIEW_MIME) and never mirror the remote's — a remote answering text/html for a .pdf
        # the lightbox opens in a same-origin iframe would be script on the dashboard's origin
        import inspect
        src = inspect.getsource(km.Handler._remote_file)
        self.assertIn("_PREVIEW_MIME.get(os.path.splitext", src)
        self.assertIn("status, ctype = resp.status, mime", src)
        # the type must not be READ from the remote (a comment may still name it as "never this")
        self.assertNotIn("ctype = resp.getheader", src)
        self.assertNotIn('resp.status, resp.getheader("Content-Type")', src)


class _DrainSpy:
    """A stand-in SDK backend: reports a busy count and records every drain-hold arm, like the
    real SdkBackend's busy_count / refresh_drain_hold / drain_holding."""

    def __init__(self):
        self.refreshed = 0
        self.holding = False

    def busy_count(self):
        return 3

    def refresh_drain_hold(self, park=None):
        self.refreshed += 1
        self.park = park
        self.holding = True

    def note_parked_poll(self, park):
        self.parks = getattr(self, "parks", []) + [park]

    def drain_holding(self):
        return self.holding


class BusyDrainWriteGate(unittest.TestCase):
    """The /busy READ stays auth-EXEMPT (a bare count leaks nothing and healthz-style probes rely
    on it), but the ?drain=1 arm is a WRITE — it arms a lease that holds EVERY session's new turn
    starts (T121) — so it is gated on an EXPLICITLY PRESENTED serve token (?token= or the manager's
    X-Romp-Token), never the ambient romp_token cookie. Before this gate the arm ran
    unconditionally in the exempt block: a drive-by loopback page's no-cors GET, or any tailnet
    client, could loop /busy?drain=1 and freeze all turn starts — the exact drive-by-loopback
    adversary _authorize's docstring names. The cookie is NOT sufficient here because a cross-origin
    subresource GET (an <img>/<script> to this route) carries it with no Origin, and _authorize
    accepts that pair for a READ; a state-changing GET must demand a token no such load can attach.
    Synthetic only — the gate touches no session state."""

    def setUp(self):
        self._saved_sdk = km._sdk
        self.spy = _DrainSpy()
        km._sdk = lambda: self.spy

    def tearDown(self):
        km._sdk = self._saved_sdk

    def test_a_tokenless_drain_reads_the_count_but_arms_nothing(self):
        status, body = _serve_get("/busy?drain=1")
        self.assertEqual(status, 200, "the READ stays auth-exempt")
        self.assertEqual(json.loads(body).get("busy"), 3, "…and still returns the count")
        self.assertEqual(self.spy.refreshed, 0,
                         "a token-less drive-by GET must not arm the turn-start hold")

    def test_the_cookie_alone_does_not_arm_the_drain(self):
        # the <img>/subresource drive-by: cookies are host- not port-scoped, so a page served by
        # anything else on loopback rides the dashboard's romp_token cookie with NO Origin header.
        status, body = _serve_get("/busy?drain=1", headers={"Cookie": "romp_token=" + TOK})
        self.assertEqual(status, 200)
        self.assertEqual(self.spy.refreshed, 0,
                         "the ambient cookie is not proof the caller is not a drive-by page")

    def test_a_cross_origin_fetch_does_not_arm_the_drain(self):
        # the no-cors fetch() form: it DOES carry a cross-site Origin (and cannot set X-Romp-Token —
        # no-cors forbids custom headers), so even with the cookie it must not arm.
        status, _ = _serve_get("/busy?drain=1",
                               headers={"Cookie": "romp_token=" + TOK,
                                        "Origin": "http://127.0.0.1:5173",
                                        "Host": "127.0.0.1:%d" % km.PORT})
        self.assertEqual(status, 200, "the read still answers")
        self.assertEqual(self.spy.refreshed, 0, "a cross-site drive-by GET arms nothing")

    def test_an_explicit_header_token_arms_the_drain(self):
        # the LEGITIMATE caller: the manager reads the 0600 serve-token and sends X-Romp-Token.
        status, body = _serve_get("/busy?drain=1", headers={"X-Romp-Token": TOK})
        self.assertEqual(status, 200)
        self.assertEqual(self.spy.refreshed, 1, "the manager's X-Romp-Token authorizes the write")
        self.assertTrue(json.loads(body).get("draining"), "…and the arm shows in the read")

    def test_a_query_token_also_arms_the_drain(self):
        status, _ = _serve_get("/busy?drain=1&token=" + TOK)
        self.assertEqual(status, 200)
        self.assertEqual(self.spy.refreshed, 1, "an explicit ?token= arms it too")

    def test_the_park_identity_rides_the_same_token_as_the_arm(self):
        # T240c review find: the park identity drives the drain EPISODE — its clock and its 5-minute
        # problem ring — which is writable state a tokenless drive-by GET must not reach
        status, _ = _serve_get("/busy?park=1700000000")
        self.assertEqual(status, 200, "the read still answers")
        self.assertEqual(getattr(self.spy, "parks", []), [], "a tokenless park is bookkeeping nobody asked for")
        status, _ = _serve_get("/busy?park=1700000000", headers={"X-Romp-Token": TOK})
        self.assertEqual(status, 200)
        self.assertEqual(self.spy.parks, ["1700000000"], "the manager's X-Romp-Token carries it")
        status, _ = _serve_get("/busy?drain=1&park=1700000000", headers={"X-Romp-Token": TOK})
        self.assertEqual(status, 200)
        self.assertEqual(self.spy.refreshed, 1)
        self.assertEqual(self.spy.park, "1700000000", "…and the arm carries it too")

    # ── T224: a REFUSED drain is the one event the gate exists for — it must read LOUDLY ──
    def _refusals(self):
        return km._DRAIN_REFUSED

    def test_a_refused_drain_logs_once_per_episode_and_counts_every_request(self):
        import io, contextlib
        km._DRAIN_REFUSED.update(count=0, episodeCount=0, episode=False, lastT=0)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            _serve_get("/busy?drain=1")
            _serve_get("/busy?drain=1")
            _serve_get("/busy?drain=1")
        self.assertEqual(self._refusals()["count"], 3, "every refused request counts")
        self.assertTrue(self._refusals()["episode"])
        self.assertEqual(err.getvalue().count("REFUSED a drain hold"), 1,
                         "one loud line per refusal EPISODE — an old manager hammering a new "
                         "kernel is one event, not a storm")

    def test_an_armed_drain_ends_the_episode_and_a_later_refusal_logs_again(self):
        import io, contextlib
        km._DRAIN_REFUSED.update(count=0, episodeCount=0, episode=False, lastT=0)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            _serve_get("/busy?drain=1")                                  # refused → episode opens
            _serve_get("/busy?drain=1", headers={"X-Romp-Token": TOK})   # armed → episode closes, recovery line
            _serve_get("/busy?drain=1")                                  # refused again → a NEW episode
        self.assertTrue(self._refusals()["episode"], "the third request RE-OPENED the episode — "
                        "the flag must flip back, not just the counter (the review's vacuous-pin catch)")
        self.assertEqual(err.getvalue().count("REFUSED a drain hold"), 2,
                         "the successful arm re-arms the notice: a second episode is new information")
        self.assertIn("armed again after 1 refused request(s)", err.getvalue(),
                      "the recovery names the EPISODE's count (one refusal), never the running total "
                      "(T227: a second episode of one refusal used to read 'after 2')")
        self.assertEqual(self._refusals()["count"], 2, "…while the lifetime total keeps counting")
        self.assertEqual(self._refusals()["episodeCount"], 1, "the re-opened episode restarts at one")

    def test_a_longer_first_episode_reports_its_own_count_on_recovery(self):
        import io, contextlib
        km._DRAIN_REFUSED.update(count=0, episodeCount=0, episode=False, lastT=0)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            _serve_get("/busy?drain=1"); _serve_get("/busy?drain=1"); _serve_get("/busy?drain=1")
            _serve_get("/busy?drain=1", headers={"X-Romp-Token": TOK})
            _serve_get("/busy?drain=1")
        self.assertIn("armed again after 3 refused request(s)", err.getvalue())
        self.assertEqual(self._refusals()["count"], 4)
        self.assertEqual(self._refusals()["episodeCount"], 1)

    def test_the_refusal_facts_ride_the_version_route(self):
        km._DRAIN_REFUSED.update(count=0, episodeCount=0, episode=False, lastT=0)
        import io, contextlib
        with contextlib.redirect_stderr(io.StringIO()):
            _serve_get("/busy?drain=1")
        status, body = _serve_get("/version?token=" + TOK)
        self.assertEqual(status, 200)
        facts = json.loads(body).get("drainRefused")
        self.assertEqual(facts.get("count"), 1, "the counter rides /version like the parse counters")
        self.assertTrue(facts.get("episode"))

    def test_the_bare_busy_read_stays_exempt_and_never_arms(self):
        status, body = _serve_get("/busy")
        self.assertEqual(status, 200, "the count is a healthz-style probe — no token needed")
        self.assertEqual(json.loads(body).get("busy"), 3)
        self.assertEqual(self.spy.refreshed, 0, "a plain /busy never holds")


_AH_KEY_MATERIAL = "test-key-material-" + "z" * 28   # invented; not shaped like any provider's key
_AH_KEY_FP = sb._keysrc.fingerprint(_AH_KEY_MATERIAL)   # what a keyed launch records (_launched_key_fp)


class _ApiHealthBackend:
    """A stand-in SDK backend carrying a REAL aggregator (sdk_backend.ApiHealth) over a temp state
    dir, seeded with one storm filed under a label digested from synthetic key material — so the
    served payload is the real shape and the leak checks have something to catch."""

    def __init__(self):
        self.ah = sb.ApiHealth(tempfile.mkdtemp(), boot_at=km._STARTED)     # seeded the way _sdk_locked seeds the live one
        label = sb.api_health_auth_label("ANTHROPIC_API_KEY", salt=self.ah.salt(),
                                         key_fp=_AH_KEY_FP, launched_keyed=True)
        now = time.time()
        for i in range(20):
            is429 = i % 5 in (3, 4)
            self.ah._push(sb.AhEvent(now - 290 + i * 14, label, "fable", "retry" if is429 else "ok",
                                     "429" if is429 else "ok", 429 if is429 else None,
                                     "11111111-2222-3333-4444-555555555555", 0))

    def api_health_snapshot(self, now=None, uptime_s=None):
        out = self.ah.snapshot(now, uptime_s=uptime_s)
        out["coverage"].update({"sdkSessionsLive": 1, "inTurn": 1, "retrying": 1})
        return out


def _strings(o):
    """Every string value in a JSON-shaped payload (keys included)."""
    if isinstance(o, dict):
        for k, v in o.items():
            yield k
            yield from _strings(v)
    elif isinstance(o, (list, tuple)):
        for v in o:
            yield from _strings(v)
    elif isinstance(o, str):
        yield o


class ApiHealthRouteGate(unittest.TestCase):
    """GET /api-health is a READ gated by the plain _authorize — never in the pre-auth exempt block.
    The exempt reads (/healthz, /version, /busy) carry only bare counters; this payload names auth
    labels and model families, so it costs a credential. Same drive-the-real-dispatcher approach as
    the drain-gate tests above: a source-position pin cannot catch a route served on the wrong side."""

    def setUp(self):
        self._saved_sdk = km._sdk
        self.be = _ApiHealthBackend()
        km._sdk = lambda: self.be

    def tearDown(self):
        km._sdk = self._saved_sdk

    def test_no_credential_no_signal(self):
        for headers in ({}, {"Cookie": "romp_token=wrong"}, {"X-Romp-Token": "wrong"},
                        {"Cookie": "romp_token=" + TOK, "Origin": "http://127.0.0.1:5173",
                         "Host": "127.0.0.1:%d" % km.PORT}):
            status, body = _serve_get("/api-health", headers)
            self.assertEqual(status, 403, "no credential must not reach /api-health (%r)" % headers)
            self.assertNotIn("buckets", body)

    def test_the_header_token_reads_the_signal(self):
        status, body = _serve_get("/api-health", {"X-Romp-Token": TOK})
        self.assertEqual(status, 200)
        out = json.loads(body)
        self.assertEqual(out["schema"], 1)
        self.assertIs(out["coverage"]["sidechainExcluded"], True)
        self.assertEqual(out["rate429Basis"], "attempts")
        self.assertEqual(len(out["buckets"]), 1)
        (b,) = out["buckets"].values()
        self.assertEqual(b["state"], "thrashing")
        self.assertEqual(out["overall"]["state"], "thrashing")
        self.assertEqual(b["windows"]["300"]["rate429"], 0.4)

    def test_the_cookie_reads_it_from_the_dashboards_own_origin(self):
        host = "127.0.0.1:%d" % km.PORT
        status, _ = _serve_get("/api-health", {"Cookie": "romp_token=" + TOK,
                                               "Origin": "http://" + host, "Host": host})
        self.assertEqual(status, 200, "a read: the plain gate, not the stricter write token")

    def test_the_route_sits_after_the_gate_in_the_source_too(self):
        # belt to the dispatcher's braces: within do_GET the gate line occurs once, and the route must
        # follow it — never among /healthz, /version, /busy and the manifest
        import inspect
        src = inspect.getsource(km.Handler.do_GET)
        gate = "ok, self._set_cookie, why = self._authorize(q)"
        self.assertEqual(src.count(gate), 1)
        self.assertGreater(src.index('p == "/api-health"'), src.index(gate))
        self.assertLess(src.index('p == "/manifest.webmanifest"'), src.index(gate), "sanity: the exempt block IS above the gate")

    def test_the_payload_carries_no_paths_and_no_key_material(self):
        status, body = _serve_get("/api-health", {"X-Romp-Token": TOK})
        self.assertEqual(status, 200)
        for s in _strings(json.loads(body)):
            self.assertNotIn("/", s, "no filesystem path may ride the signal: %r" % s)
            self.assertFalse(s.startswith("~"), s)
        for i in range(len(_AH_KEY_MATERIAL) - 4):
            self.assertNotIn(_AH_KEY_MATERIAL[i:i + 5], body, "a fragment of the key material leaked")
        self.assertNotIn(_AH_KEY_FP, body, "salted: the key's fingerprint is not the bucket's name either")
        self.assertNotIn(os.path.expanduser("~"), body)

    def test_boot_identity_is_versions_own(self):
        status, body = _serve_get("/api-health", {"X-Romp-Token": TOK})
        out = json.loads(body)
        v = km._version_info()
        self.assertEqual(out["bootId"], km._BOOT_ID)
        self.assertEqual(out["bootId"], v["boot"], "the same id /version and X-Romp-Boot carry — never a third")
        self.assertEqual(out["bootAt"], self.be.ah.boot_stamp, "bootAt is the aggregator's own seed stamp")
        self.assertEqual(int(out["bootAt"]), v["started"], "the same start: bootAt truncated to the millisecond (the payload's "
                         "stamp precision, so a bucket the boot seeded carries the very number), started to the whole second; "
                         "a fresh state dir, so nothing moved the stamp")
        self.assertLessEqual(out["bootAt"], km._STARTED)
        self.assertLess(km._STARTED - out["bootAt"], 0.001)
        self.assertAlmostEqual(out["uptimeS"], v["uptime_s"], delta=2.0)
        self.assertIsInstance(out["complete"], bool)
        self.assertEqual(out["complete"], out["uptimeS"] >= 900)
        import inspect
        src = inspect.getsource(km.Handler.do_GET)
        self.assertIn('out["bootId"] = _BOOT_ID', src)
        self.assertIn("uptime_s=now - _STARTED", src)

    def test_no_backend_is_a_loud_503_not_an_empty_signal(self):
        km._sdk = lambda: None
        status, body = _serve_get("/api-health", {"X-Romp-Token": TOK})
        self.assertEqual(status, 503)
        self.assertIn("error", json.loads(body))

    def test_coverage_counts_the_tmux_sessions_the_signal_does_not_see(self):
        # the kernel's half of `coverage`: tmux-backed sessions have no SDK stream; the backend's
        # half (sdkSessionsLive / inTurn / retrying) arrives with the payload
        saved = km.Sessions.live
        km.Sessions.live = staticmethod(lambda: {"11111111-2222-3333-4444-555555555555": {"backend": "tmux"},
                                                 "11111111-2222-3333-4444-666666666666": {"backend": "sdk"},
                                                 "11111111-2222-3333-4444-777777777777": {"backend": "tmux"}})
        try:
            status, body = _serve_get("/api-health", {"X-Romp-Token": TOK})
        finally:
            km.Sessions.live = saved
        self.assertEqual(status, 200)
        cov = json.loads(body)["coverage"]
        self.assertEqual(cov["tmuxSessionsUncovered"], 2)
        self.assertEqual((cov["sdkSessionsLive"], cov["inTurn"], cov["retrying"]), (1, 1, 1))
        # …and a failed enumeration is a visible null, never a silent zero
        km.Sessions.live = staticmethod(lambda: (_ for _ in ()).throw(RuntimeError("no tmux")))
        try:
            status, body = _serve_get("/api-health", {"X-Romp-Token": TOK})
        finally:
            km.Sessions.live = saved
        self.assertEqual(status, 200)
        self.assertIsNone(json.loads(body)["coverage"]["tmuxSessionsUncovered"])


class _RfileSpy:
    """A request body that RECORDS every read: the gate under test must refuse before reading any of it."""

    def __init__(self, data=b""):
        self.data, self.reads = data, []

    def read(self, n=-1):
        self.reads.append(n)
        out, self.data = self.data[:n], self.data[n:]
        return out


def _serve_post(path, headers=None, body=b"", rfile=None, connection=None):
    """Drive the REAL do_POST dispatcher over a fake socket -> (status, response headers, body text,
    handler). `headers` is a dict or an http.client.HTTPMessage -- the type the live server parses
    into, and the one that can carry a header TWICE (a dict cannot). `connection`, when given, stands
    in for the socket the body read puts its timeout on."""
    h = km.Handler.__new__(km.Handler)
    h.client_address = ("127.0.0.1", 0)
    if connection is not None:
        h.connection = connection
    h.headers = headers if headers is not None else {}
    h.path = path
    h.command = "POST"
    h.request_version = "HTTP/1.1"
    h.wfile = io.BytesIO()
    h.rfile = rfile if rfile is not None else io.BytesIO(body)
    h.close_connection = False                       # keep-alive until the handler says otherwise
    captured = {"headers": {}}

    def send_response(code, *a):
        captured["status"] = code

    def send_header(k, v):
        captured["headers"][k] = v

    h.send_response = send_response
    h.send_header = send_header
    h.end_headers = lambda: None
    h.log_message = lambda *a: None
    h.do_POST()
    return captured.get("status"), captured["headers"], h.wfile.getvalue().decode("utf-8", "replace"), h


class PostBodyGate(unittest.TestCase):
    """POST bodies are read only AFTER _authorize passes, and only within bounds. do_POST used to read
    the whole body FIRST -- `int(Content-Length or 0)` inside a bare except, no cap -- so a token-less
    loopback or tailnet client could make the kernel buffer any number of bytes and pin one handler
    thread per oversize POST (the server is threaded); a non-decimal or duplicate Content-Length was
    silently read as no body; a Transfer-Encoding request had its chunk framing parsed as the next
    request; and a denied request left its unread body on a keep-alive socket. Every refusal here
    wears the route family's JSON shape and closes the connection."""
    TEN_MB = str(10 * 1024 * 1024)

    def test_an_unauthenticated_post_is_denied_before_its_body_is_read(self):
        spy = _RfileSpy()
        st, hdrs, body, h = _serve_post("/send", {"Content-Length": self.TEN_MB}, rfile=spy)
        self.assertEqual(st, 403)
        self.assertEqual(spy.reads, [], "no byte of an unauthenticated body is read")
        self.assertTrue(h.close_connection, "an unread body cannot stay on a keep-alive socket")
        self.assertEqual(hdrs.get("Connection"), "close")

    def test_an_oversize_post_is_413_before_any_read_and_a_bounded_one_is_served(self):
        spy = _RfileSpy()
        st, hdrs, body, h = _serve_post("/perf", {"X-Romp-Token": TOK,
                                                 "Content-Length": str(km._POST_MAX_BYTES + 1)}, rfile=spy)
        self.assertEqual(st, 413)
        r = json.loads(body)
        self.assertIs(r["ok"], False)
        self.assertIn(str(km._POST_MAX_BYTES), r["error"], "the refusal names the limit")
        self.assertEqual(spy.reads, [], "refused on the declared length, before a byte is read")
        self.assertTrue(h.close_connection)
        self.assertEqual(hdrs.get("Connection"), "close")
        # the same route, an in-bounds body: read, parsed and served (the cap is a cap, not a lockout)
        raw = b'{"log": false}'
        st, hdrs, body, h = _serve_post("/perf", {"X-Romp-Token": TOK, "Content-Length": str(len(raw))}, body=raw)
        self.assertEqual(st, 200)
        self.assertEqual(json.loads(body), {"ok": True, "log": False})

    def test_a_non_decimal_content_length_is_400_and_unread(self):
        for cl in ("12abc", "-1", "0x10", " ", "1e3", "\u0661\u0662"):   # the last: Arabic-Indic digits, which str.isdigit accepts
            spy = _RfileSpy(b"{}")
            st, hdrs, body, h = _serve_post("/perf", {"X-Romp-Token": TOK, "Content-Length": cl}, rfile=spy)
            self.assertEqual(st, 400, cl)
            self.assertIn("Content-Length", json.loads(body)["error"], cl)
            self.assertEqual(spy.reads, [], cl)
            self.assertTrue(h.close_connection, cl)

    def test_two_content_length_headers_are_400_and_unread(self):
        m = HTTPMessage()
        m["X-Romp-Token"] = TOK
        m["Content-Length"] = "2"
        m["Content-Length"] = "4"                        # Message.__setitem__ APPENDS: two headers, as on the wire
        spy = _RfileSpy(b"{}{}")
        st, hdrs, body, h = _serve_post("/perf", m, rfile=spy)
        self.assertEqual(st, 400)
        self.assertIn("more than one Content-Length", json.loads(body)["error"])
        self.assertEqual(spy.reads, [], "neither length is trusted")
        self.assertTrue(h.close_connection)

    def test_transfer_encoding_is_411_and_unread(self):
        spy = _RfileSpy(b"2\r\n{}\r\n0\r\n\r\n")
        st, hdrs, body, h = _serve_post("/perf", {"X-Romp-Token": TOK, "Transfer-Encoding": "chunked"}, rfile=spy)
        self.assertEqual(st, 411)
        self.assertIn("Transfer-Encoding", json.loads(body)["error"])
        self.assertEqual(spy.reads, [], "chunk framing is never read as a body")
        self.assertTrue(h.close_connection)

    def test_a_digit_run_past_any_byte_count_is_400_not_a_conversion_error(self):
        # 5000 digits pass a bare [0-9]+ and then int() raises past the interpreter's conversion limit
        # (4300 digits on 3.11+) -- into do_POST's catch-all as a 500 traceback with the socket left open
        spy = _RfileSpy(b"{}")
        st, hdrs, body, h = _serve_post("/perf", {"X-Romp-Token": TOK, "Content-Length": "9" * 5000}, rfile=spy)
        self.assertEqual(st, 400)
        err = json.loads(body)["error"]
        self.assertIn("Content-Length", err)
        self.assertLess(len(err), 200, "the offending value echoes clipped, not in full")
        self.assertEqual(spy.reads, [])
        self.assertTrue(h.close_connection)

    def test_a_body_that_stalls_is_408_and_closes_and_the_socket_timeout_is_restored(self):
        # review find, 2026-09-08: the in-bounds read had no socket timeout, so an AUTHORIZED client
        # that announced a body and trickled it pinned a handler thread for as long as it liked
        class Stall:
            reads = []

            def read(self, n=-1):
                self.reads.append(n)
                raise socket.timeout("timed out")           # what the real rfile raises past the deadline

        class Sock:
            def __init__(self):
                self.timeouts, self._t = [], None

            def gettimeout(self):
                return self._t

            def settimeout(self, t):
                self.timeouts.append(t)
                self._t = t
        sock = Sock()
        st, hdrs, body, h = _serve_post("/perf", {"X-Romp-Token": TOK, "Content-Length": "100"},
                                        rfile=Stall(), connection=sock)
        self.assertEqual(st, 408)
        r = json.loads(body)
        self.assertIs(r["ok"], False)
        self.assertEqual(r["error"], "body could not be read: 100 bytes announced, not all of it arrived within %g s"
                         % km._POST_BODY_TIMEOUT)
        self.assertTrue(h.close_connection, "a half-arrived body cannot stay on a keep-alive socket")
        self.assertEqual(hdrs.get("Connection"), "close")
        self.assertEqual(sock.timeouts, [km._POST_BODY_TIMEOUT, None],
                         "the read ran under the body timeout, and the socket's own (none) came back")
        self.assertEqual(Stall.reads, [100], "the read was attempted once, for the announced length")
        # a body that ARRIVES under the same timeout is served, and the timeout is restored just the same
        sock = Sock()
        raw = b'{"log": false}'
        st, hdrs, body, h = _serve_post("/perf", {"X-Romp-Token": TOK, "Content-Length": str(len(raw))},
                                        body=raw, connection=sock)
        self.assertEqual((st, json.loads(body)), (200, {"ok": True, "log": False}))
        self.assertEqual(sock.timeouts, [km._POST_BODY_TIMEOUT, None])
        self.assertFalse(h.close_connection)

    def test_an_absent_content_length_is_an_empty_body_never_a_read(self):
        # the hook's bodiless POST /tick, and any bodiless POST: served on an empty body without a read
        spy = _RfileSpy(b"")
        st, hdrs, body, h = _serve_post("/tick", {"X-Romp-Token": TOK}, rfile=spy)
        self.assertEqual((st, json.loads(body)), (200, {"ok": True, "woke": True}))
        self.assertEqual(spy.reads, [], "nothing to read: no read")
        self.assertFalse(h.close_connection, "a served request keeps its keep-alive")
        spy = _RfileSpy(b"")
        st, hdrs, body, h = _serve_post("/perf", {"X-Romp-Token": TOK}, rfile=spy)
        self.assertEqual(st, 400)
        self.assertEqual(json.loads(body)["error"], 'body must be {"log": true|false}',
                         "the route saw an EMPTY body (its own refusal), not a gate refusal")
        self.assertEqual(spy.reads, [])


class ForkRoutesReadBodiesThroughTheValidator(unittest.TestCase):
    """The fork's own POST routes read their body through the same _json_object_body as upstream's
    session-management routes (the 2026-09-08 fold of upstream's body validation): a JSON array, string
    or number is a 400 naming what arrived, an undecodable body is "body is not JSON", and the route
    acts on neither. Before the fold /usertodo, /usertodo/withdraw and /usertodo/context raised
    AttributeError into do_POST's catch-all (a 500 carrying a traceback) on a truthy non-object, /emoji
    collapsed one to {} and answered as if the fields were missing, and /pinnote and /unpinnote carried
    a validator of their own with a different text. One validator, one text, on every route."""
    ROUTES = ("/usertodo", "/usertodo/withdraw", "/usertodo/context", "/pinnote", "/unpinnote", "/emoji")

    def _post(self, path, raw):
        st, hdrs, body, h = _serve_post(path, {"X-Romp-Token": TOK, "Content-Length": str(len(raw))}, body=raw)
        self.assertNotIn("Traceback", body, (path, raw))
        return st, json.loads(body)

    def test_a_non_object_body_is_400_naming_what_arrived_never_a_500(self):
        for path in self.ROUTES:
            for raw, echo in ((b"[]", "[]"), (b'"x"', '"x"'), (b"1", "1"), (b"null", "null"), (b"[1]", "[1]")):
                with self.subTest(path=path, raw=raw):
                    st, r = self._post(path, raw)
                    self.assertEqual(st, 400, (path, raw, r))
                    self.assertIs(r.get("ok"), False)
                    self.assertEqual(r.get("error"), "body must be a JSON object, got " + echo,
                                     "the validator answered, not the route's own field check")

    def test_an_undecodable_body_is_400_too_not_a_guess_at_its_fields(self):
        for path in self.ROUTES:
            with self.subTest(path=path):
                st, r = self._post(path, b"{not json")
                self.assertEqual((st, r), (400, {"ok": False, "error": "body is not JSON"}))

    def test_an_object_body_reaches_the_routes_own_field_check(self):
        # the validator is a gate, not a lockout: an object with the fields missing gets the route's
        # own refusal, the text each route had before the fold
        for path, own in (("/usertodo", "id and text required"), ("/usertodo/withdraw", "id and todoId required"),
                          ("/unpinnote", "id and noteId required"), ("/emoji", 'target and emoji required ("" clears)')):
            with self.subTest(path=path):
                st, r = self._post(path, b"{}")
                self.assertEqual((st, r.get("ok")), (400, False), (path, r))
                self.assertEqual(r.get("error"), own)


class ForkGearSwitchesRefuseNonBooleanFlags(unittest.TestCase):
    """setUserTodos `enabled` and setJudgeFast `on` (the fork's gear switches) take a boolean the way
    upstream's setConserve, setFileEditing and setThinkingSummaries do since the 2026-09-08 fold: a string
    is refused through _refuse_ws_flag (a warn frame to the sender, one stderr line naming the op) and
    nothing is written. bool("false") is True, so a string here used to turn the switch ON."""

    def setUp(self):
        self._saved = km._set_user_todos, km._set_judge_fast, km._mark_views_dirty
        self.calls = []
        km._set_user_todos = lambda enabled, gt=None: self.calls.append(("setUserTodos", enabled)) or 1
        km._set_judge_fast = lambda v: self.calls.append(("setJudgeFast", v))
        km._mark_views_dirty = lambda: None

    def tearDown(self):
        km._set_user_todos, km._set_judge_fast, km._mark_views_dirty = self._saved

    def _dispatch(self, frame):
        import contextlib
        sent = []
        client = {"app": "chat", "wid": "w1", "alive": True, "send": lambda raw: sent.append(json.loads(raw))}
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km.Handler._dispatch_ws(None, frame, client)
        return sent, err.getvalue()

    def test_a_string_flag_is_refused_on_the_socket_and_the_log_and_writes_nothing(self):
        for frame, field in (({"type": "setUserTodos", "enabled": "yes"}, "enabled"),
                             ({"type": "setUserTodos", "enabled": "false"}, "enabled"),
                             ({"type": "setJudgeFast", "on": "true"}, "on"),
                             ({"type": "setJudgeFast", "on": 1}, "on")):
            with self.subTest(frame=frame):
                sent, log = self._dispatch(frame)
                self.assertEqual(sent, [{"type": "warn", "text": "%s: '%s' must be true or false, got %s"
                                         % (frame["type"], field, json.dumps(frame[field]))}])
                self.assertIn("romp-kernel: refused %s:" % frame["type"], log)
                self.assertNotIn(json.dumps(frame[field]), log, "the log names the type, never the value")
        self.assertEqual(self.calls, [], "a refused flag writes nothing")

    def test_a_real_boolean_applies(self):
        sent, log = self._dispatch({"type": "setUserTodos", "enabled": True})
        self.assertEqual((sent, log), ([], ""))
        sent, log = self._dispatch({"type": "setJudgeFast", "on": False})
        self.assertEqual((sent, log), ([], ""))
        self.assertEqual(self.calls, [("setUserTodos", True), ("setJudgeFast", "")])


def _raw_post(port, path, headers, body=b"", half_close=True):
    """One hand-built POST over a real socket -> (status, JSON body, response head). `headers` is a list
    of (name, value) pairs, so a header can be sent twice; `half_close` ends the client's sending side
    after `body`, so the server's read of an announced-but-short body sees EOF rather than hanging.
    Connection: close on the request, so the response is followed by EOF and the read loop ends."""
    lines = ["POST %s HTTP/1.1" % path, "Host: 127.0.0.1", "Connection: close"] + \
            ["%s: %s" % kv for kv in headers]
    req = ("\r\n".join(lines) + "\r\n\r\n").encode() + body
    s = socket.create_connection(("127.0.0.1", port), timeout=10)
    try:
        s.sendall(req)
        if half_close:
            s.shutdown(socket.SHUT_WR)
        data = b""
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            data += chunk
    finally:
        s.close()
    head, _, payload = data.partition(b"\r\n\r\n")
    return int(head.split(b" ", 2)[1]), json.loads(payload.decode() or "{}"), head.decode()


class PostBodyGateOverTheWire(unittest.TestCase):
    """The same gate against the REAL server and a real socket: the header object is the HTTPMessage
    the live server parses into, and the body arrives (or does not) over TCP."""

    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def test_a_body_shorter_than_announced_is_refused_naming_the_shortfall(self):
        # a dead client / short read: 100 bytes announced, 10 arrive, then EOF. The 10 bytes must not
        # pass as the body (here they would have been "body is not JSON" -- a guess at a truncated
        # request); the refusal names the shortfall and closes.
        st, r, head = _raw_post(self.port, "/rename", [("X-Romp-Token", TOK), ("Content-Length", "100")],
                                body=b'{"target":')
        self.assertEqual(st, 400, r)
        self.assertEqual(r, {"ok": False, "error": "body could not be read: read 10 of the 100 bytes Content-Length announced"})
        self.assertIn("Connection: close", head)

    def test_two_content_length_headers_on_the_wire_are_400(self):
        st, r, head = _raw_post(self.port, "/rename",
                                [("X-Romp-Token", TOK), ("Content-Length", "2"), ("Content-Length", "4")],
                                body=b"{}{}")
        self.assertEqual(st, 400, r)
        self.assertEqual(r["error"], "body could not be read: more than one Content-Length header")
        self.assertIn("Connection: close", head)

    def test_a_trickling_body_is_408_over_the_wire_and_the_connection_closes(self):
        # 100 bytes announced, 10 sent, the sending side left OPEN (no half-close, so no EOF): before the
        # body timeout this read blocked for as long as the client cared to hold the socket
        saved = km._POST_BODY_TIMEOUT
        km._POST_BODY_TIMEOUT = 0.5
        try:
            t0 = time.monotonic()
            st, r, head = _raw_post(self.port, "/rename", [("X-Romp-Token", TOK), ("Content-Length", "100")],
                                    body=b'{"target":', half_close=False)
            took = time.monotonic() - t0
        finally:
            km._POST_BODY_TIMEOUT = saved
        self.assertEqual(st, 408, r)
        self.assertEqual(r, {"ok": False, "error": "body could not be read: 100 bytes announced, not all of it arrived within 0.5 s"})
        self.assertIn("Connection: close", head)
        self.assertLess(took, 5, "answered on the body timeout, not on the client giving up")
        # the server is still serving: the next request lands
        st, r, head = _raw_post(self.port, "/rename", [("X-Romp-Token", TOK), ("Content-Length", "2")], body=b"{}")
        self.assertEqual(st, 400, r)
        self.assertNotIn("announced", r.get("error", ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
