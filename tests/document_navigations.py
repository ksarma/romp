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

A navigation authenticates the way a browser's does (credential and navigation_path below): with the session cookie a
signed-in browser holds, which a top-level GET carries with no Origin header and which opens the page and static
classes on its own, and on /file and /remote/<host>/file also with the per-file cap in the URL, as the dashboard's own
tab's URL carries one (ui/webview/preview.ts fileUrl); the cookie alone opens no file. A kernel whose header depended
on how a request was authorized would pass a test that authorized every request by the X-Romp-Token header.

Imports nothing at load (navigation_path imports urllib.parse when it is called), so a test module may import it
anywhere, its state preamble included.
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


def credential(nav, token, session_cookie):
    """The credential headers a request of this kind presents: a navigation (a non-empty entry of NAVIGATIONS) the
    browser's session cookie (`session_cookie`, the Cookie header's value: the kernel's cookie name and a session it
    minted), as a browser does; a bare request the X-Romp-Token header, as the CLI and the hooks do."""
    return {"Cookie": session_cookie} if nav else {"X-Romp-Token": token}


def navigation_path(nav, path, file_cap):
    """`path` as a request of this kind asks for it: a navigation to /file or /remote/<host>/file adds the cap its URL
    carries, `file_cap(host, file path, sid)` (the caller binds kernel.py's _file_cap to the session its cookie holds;
    host is "" for /file, the path and sid are the query's decoded values, "" when absent), as the dashboard's own tab's
    URL does; every other request asks for `path` as given."""
    from urllib.parse import parse_qs, unquote, urlsplit
    u = urlsplit(path)
    if not nav:
        return path
    if u.path == "/file":
        host = ""
    elif u.path.startswith("/remote/") and u.path.endswith("/file"):
        host = unquote(u.path[len("/remote/"):-len("/file")])
    else:
        return path
    q = parse_qs(u.query)
    return path + ("&" if u.query else "?") + "cap=" + file_cap(host, (q.get("path") or [""])[0], (q.get("sid") or [""])[0])
