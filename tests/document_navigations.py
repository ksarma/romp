"""The request headers a browser sends with a top-level document navigation, for the tests of a response header that a
browser reads on navigations only: Cross-Origin-Opener-Policy (tests/test_kernel_auth_hardening.py OpenerIsolation, on the
local routes, and tests/test_kernel_remote_file_relay.py, on the /remote/<host>/file relay). Browsers send the Sec-Fetch-*
headers at secure origins (https, localhost), which are also the only contexts that enforce the policy, so a kernel that
sent the header on a bare request but dropped or doubled it on a navigation would pass every test that sends none (a
review's mutants did, 2026-09-26). Each test serves every document shape once per entry here:
  - a bare request, which sends none of these headers (a fetch, an <img> load);
  - a navigation typed into the address bar or opened from a bookmark (Sec-Fetch-Site: none);
  - the dashboard opening a tab of its own, a /file image or PDF (ui/webview/preview.ts openFileTab; same-origin);
  - the case the policy exists for: a page on another origin opening a dashboard page with window.open (cross-site).

Imports nothing, so a test module may import it anywhere, its state preamble included.
"""

_NAVIGATE = {
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

NAVIGATIONS = (
    ("a bare request", {}),
    ("a navigation typed or opened from a bookmark", dict(_NAVIGATE, **{"Sec-Fetch-Site": "none"})),
    ("the dashboard opening a tab of its own", dict(_NAVIGATE, **{"Sec-Fetch-Site": "same-origin"})),
    ("a page on another origin opening it", dict(_NAVIGATE, **{"Sec-Fetch-Site": "cross-site"})),
)
