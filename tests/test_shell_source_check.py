#!/usr/bin/env python3
"""The dashboard shell's window message listeners act only on a message from one of its own panes (2026-09-25).

The shell page (kernel.py _landing) runs about a dozen inline listeners for its panes' words: the boot splash's
ready, the Log's notify and wsState, the settings relay (openSettings, viewFile, editorSelection, ...), the usage
bars, the split columns' drags. A window message listener hears every window that can post to the page, and the
only legitimate senders of these words are the shell's own pane iframes. Each listener reads the shell's one source
check, window.__rompPaneSourceOk, FAIL-CLOSED as its first statement: a message counts only when its immediate
source is an iframe of the shell and its origin is the shell's location.origin.

The check is ADOPTED from the romp project's repository, github.com/romp-on/romp, at commit
f4a57200894ede72a4d4469570490aa64fbf9e94 (kernel/kernel.py there, lines 65382-65384, the opening lines of
_LANDING_BOOT_JS), byte for byte. AdoptedCheck pins those three lines by the sha256 of their text, so an edit inside
them reds; recompute the recorded digest from that commit, never from the fork's copy:

    git show f4a57200894ede72a4d4469570490aa64fbf9e94:kernel/kernel.py | sed -n '65382,65384p' | head -c -1 | sha256sum

NoOtherWriter holds that nothing else names the check: no file in the tree but the kernel and ui/webview/pane-source.ts,
the reader the shell's bundled palette goes through, whose code lines are the project's at the same commit byte for byte
(pinned by sha256) and only read it; and in the kernel's code nothing but the adopted lines, the lock and the gates. The
listener censuses and the runs that follow read the pages' inline scripts, not the /dist bundles the shell loads: the
palette's two window listeners (palette-main.js) are ui/webview/foreign-sender-listeners.test.ts's census and executed
legs. The rest runs the served landing: the census of every window message listener in its inline scripts
(addEventListener for a message or a messageerror; every onmessage assignment, whatever its receiver, which must be one
of the sockets and the channel ONMESSAGE_RECEIVERS lists; and no onmessageerror handler on any receiver), the same
census over all of kernel.py and every page it serves (KernelListenerCensus), and node executing the scripts in a
stand-in browser. The run goes through every callback they leave for later (timers, animation frames, idle callbacks,
microtasks, load listeners) and an exercise: every other listener and handler they register (on the window, the
document, a frame or an element), handed a stand-in event; every callback they hand to a stand-in (an observer's, a
fetch's then); and every word a message listener's arms compare against, from each pane. Then it forges a message from
each sender the shell must refuse (a page that opened it, on another origin or on its location.origin, a sandboxed
frame, a window it does not hold, a frame nested in a pane, sandboxed or on its location.origin, a window on its
location.origin nested in a pane that replaced its window.parent with the shell, a window it opened, on another origin
or on its location.origin, itself, its own dispatch, a sourceless post with the opaque origin) and from a pane, over
windows that carry the edges a browser gives them (parent, top, opener, and the shell's frames), and reads which
function the check is when each message is delivered. The other pages' scripts run through the same exercise for their
census (ServedPagesExecuted). ServedScriptPopulation derives the pages every census here reads (SERVED_BUILDERS) from
kernel.py's syntax tree, each read as the kernel's _send writes it (_as_served: a page of the page class carries the
sign-in seed and the page-key script _send puts first in its head), and ui/webview/served-script-scopes.test.ts parses
every script on them (_served_scripts) and refuses a direct eval or a with statement, the two ways code can add a
binding at run time to a scope between a listener and the global scope. Synthetic only: no session data, a loopback
origin.

The line after the adopted three is the fork's LOCK (2026-09-26): it makes the check's property read-only and
non-configurable once defined, so a later write of it, under any name and on any road (a road the stand-in does not
drive, a ui/ bundle's computed name), does not land. CheckLocked reads the property's descriptor after boot and tries
each way a script can replace it; without the lock line, each of those attempts replaces the check.

What no leg here runs: code behind a condition the stand-in does not meet (a secure-context test, a user agent, a stored
setting, a key the stand-in event does not carry), an arm keyed other than by comparing a field with a string, and a
registration through another object's method. A listener registered under a computed name on such a road is caught by
none of these tests; the text censuses catch only the names they can read. A write of the check on such a road is
refused by the lock when it runs after the boot script; one that runs before it (every script ahead of the boot script
on the shell as served: the sign-in seed and the page-key script _send puts first in the head, then the shell's own
scripts before the boot script; all of them run here) would show in the descriptor CheckLocked reads, when it is on a
road the stand-in drives.
"""
import ast
import functools
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from html.parser import HTMLParser
from urllib.parse import unquote
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads (they resolve their state root at import time; only pytest runs conftest's floor,
# and a bare unittest or script run would otherwise write REAL state). No session connects here; session-hosts is
# written off anyway, as for every root a test mints.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
os.makedirs(os.path.join(os.environ["XDG_STATE_HOME"], "romp"), exist_ok=True)
with open(os.path.join(os.environ["XDG_STATE_HOME"], "romp", "session-hosts"), "w") as _f:
    _f.write("off")
km = load_source("romp_kernel_shell_source_check", os.path.join(BIN, "romp-kernel"))

UPSTREAM_REPO = "github.com/romp-on/romp"
UPSTREAM_SHA = "f4a57200894ede72a4d4469570490aa64fbf9e94"
# sha256 of the adopted region's text at UPSTREAM_SHA (kernel/kernel.py lines 65382-65384, joined by newlines, no
# trailing newline): from its first character, "window.__rompPaneSourceOk=function(e){", through its last,
# "return false;}catch(x){return false;}};". 319 characters.
ADOPTED_SHA256 = "97e0342292b56cf7b1df96a91d40c7bf8db3ee3a0949abc681c0e3457908f7bb"
ADOPTED_LEN = 319
REGION_HEAD = "window.__rompPaneSourceOk=function(e){"
REGION_TAIL = "return false;}catch(x){return false;}};"
# The shell's bundled palette reads the check through ui/webview/pane-source.ts (paneSourceOk), ADOPTED from the same
# commit: its code lines, from its first line that is not a // comment to the file's end, are that commit's
# ui/webview/pane-source.ts lines 7-11 byte for byte, final newline included (298 bytes), and the fork's header stands
# where the project's six comment lines stand. sha256 of that text at UPSTREAM_SHA; recompute from that commit, never
# from the fork's copy:
#     git show f4a57200894ede72a4d4469570490aa64fbf9e94:ui/webview/pane-source.ts | sed -n '7,$p' | sha256sum
PANE_SOURCE = "ui/webview/pane-source.ts"
PANE_SOURCE_SHA256 = "e57ac6389e2498adc241574e7d7c8270b852fd82c6a5b54247915e67124c6208"
PANE_SOURCE_LEN = 298

# The read every inline shell listener opens with, spelled as the project spells it (so a fold's lines match). The shell's
# bundled palette reads the check through ui/webview/pane-source.ts instead (foreign-sender-listeners.test.ts's census).
GATE = "if(!window.__rompPaneSourceOk||!window.__rompPaneSourceOk(e))return;"
# The fork's line right after the adopted three (2026-09-26): it locks the check, read-only and non-configurable, so no
# later script replaces, redefines or deletes it. Not the project's text: a fold that takes the project's side of
# _LANDING_BOOT_JS keeps this line after the project's definition (CheckLocked fails without it).
LOCK = "try{Object.defineProperty(window,'__rompPaneSourceOk',{writable:false,configurable:false});}catch(x){}"

# Every window message listener the shell's inline scripts run, by a phrase only its own body carries. A listener added
# to them must join this list (the census below fails until it does), which is where its senders get decided. The two in
# the palette bundle the shell loads (palette-main.js) are not read here: ui/webview/foreign-sender-listeners.test.ts takes
# their census and runs them.
LISTENERS = {
    "activeTab relay (_LANDING_FOCUS_JS)": "m.romp!=='activeTab'",
    "toggleFleet (_LANDING_FLEET_JS)": "m.romp!=='toggleFleet'",
    "boot splash ready (_LANDING_BOOT_JS)": "e.data.romp==='ready')hide()",
    "log count ask (_LANDING_ERRS_JS)": "m.romp==='logUnseenQuery')tell()",
    "notify (_LANDING_ERRS_JS)": "m.romp==='notify'&&m.text",
    "connection state (_LANDING_ERRS_JS)": "m.romp!=='wsState'",
    "usage bars (_LANDING_USAGE_JS)": "m.romp==='usage')render(m.usage)",
    "settings and file relay (_LANDING_SETTINGS_JS)": "if(m.romp==='openSettings')window.__rompOpenSettings(",
    "pending hosts (_LANDING_REMOTES_JS)": "m.romp!=='hostsPending'",
    "phone tab switch (_LANDING_MOBILE_JS)": "if(m.romp==='reveal'&&m.pane)reveal(m.pane)",
    "push reveal (_LANDING_REVEAL_JS)": "m.romp==='ready'&&m.app==='feed'",
    "reload prompt (_STALE_JS)": "m.romp==='wsStale'",
    "split columns (_LANDING_SPLIT_JS)": "m.romp==='tabDrag'",
}

LISTEN_OPEN = "addEventListener('message',function(e){"

# Every onmessage or onmessageerror assignment in a text, whatever its receiver. The receiver is the dotted chain before
# .onmessage or ['onmessage'], its spaces taken out: "" for a bare name (the window's own handler), None for a chain the
# census cannot read (one that follows a call, an index or another member: foo().d.onmessage=,
# document.querySelector('body').onmessage=, window[0].onmessage=). A plain `=` only: == and === compare.
_ONMESSAGE_ANY = re.compile(r"(?:(?<![\w$])(onmessage(?:error)?)|\[\s*(['\"`])(onmessage(?:error)?)\2\s*\])\s*=(?!=)")
_CHAIN_BEFORE = re.compile(r"(?<![\w$.)\]])((?:[\w$]+\s*\.\s*)*[\w$]+)\s*$")
# The onmessage handlers kernel.py sets, by receiver, and how many: the three detaches of a dead socket (the shim's park
# and abandon, `var d=ws;`, and the shell's shAbandon, `var d=shWs;`, each d.onopen=d.onmessage=...=null), the shim's and
# the shell's sockets (ws.onmessage=function(ev){), and the shim's dispatch channel, a MessageChannel
# (ch.port1.onmessage=flush). None is a window, and no other page can post on a socket or on the channel. Any other
# receiver (the window by any name, a frame, a document's window, the body element, whose handler is its window's), a
# bare onmessage, or a chain the census cannot read fails until it is listed here, which is where its senders get
# decided. An onmessageerror handler fails on every receiver, a listed one included: no entry here admits one. The table
# counts receivers by name, not by binding: a listed name rebound to a window keeps its count and passes here, and only
# the executed stand-in catches it (ShellListenersExecuted, ServedPagesExecuted), on the roads it drives.
ONMESSAGE_RECEIVERS = {"d": 3, "ws": 2, "ch.port1": 1}


def _onmessage_writes(text):
    """[(receiver, handler name, the write's surroundings)] for every onmessage or onmessageerror assignment in `text`."""
    out = []
    for m in _ONMESSAGE_ANY.finditer(text):
        handler = m.group(1) or m.group(3)
        before = text[max(0, m.start() - 160):m.start()].rstrip()
        ctx = text[max(0, m.start() - 40):m.end() + 20]
        if m.group(1) and not before.endswith("."):
            out.append(("", handler, ctx))   # a bare name: the window's own handler
            continue
        r = _CHAIN_BEFORE.search(before[:-1] if m.group(1) else before)
        out.append((re.sub(r"\s+", "", r.group(1)) if r else None, handler, ctx))
    return out


def _unlisted_onmessage(text):
    """The surroundings of every onmessage assignment in `text` on a receiver ONMESSAGE_RECEIVERS does not list, and of
    every onmessageerror assignment."""
    return [ctx for r, h, ctx in _onmessage_writes(text) if h != "onmessage" or r not in ONMESSAGE_RECEIVERS]


def _inline_scripts(html):
    """The bodies of the page's inline <script> elements, in page order, whatever attributes the tag carries (a
    <script src=...> is a bundle, not here)."""
    return re.findall(r"<script(?![^>]*\bsrc\s*=)[^>]*>(.*?)</script>", html, re.S | re.I)


# Every page the kernel writes and serves as a document, by route, and /sw.js (the service worker's script), each by the
# kernel function or constant that builds it: what every census in this module reads as the kernel's pages, each read as
# Handler._send writes it (_as_served). ServedScriptPopulation derives the builders from kernel.py itself (a page route's
# builder through the route table _PAGE_RENDERERS), so a page a new builder serves fails there until it is listed here.
SERVED_BUILDERS = {"/": "_landing", "/chat": "_chat_page", "/feed": "_feed_page", "/fleet": "_fleet_page",
                   "/waiting": "_waiting_page", "/files": "_files_page", "/settings": "_settings_page",
                   "/timeline": "_timeline_page", "the sign-in page": "_TOKEN_LOGIN_HTML",
                   "the too-large page": "_too_large_page", "/sw.js": "_sw_js"}
_BUILDER_ARGS = {"_too_large_page": ("too large", "a.pdf", {})}


# One browser's session, minted once for the module, so a page read twice is read the same: _as_served reads a page
# renderer's document as the response that signs this session in, whose seed holds the session's page key.
_SESSION = km._mint_session()


def _as_served(builder, text):
    """`text`, the document `builder` built, as Handler._send writes it: run through the kernel's own _send on a handler with
    no socket, under the type the kernel serves `builder`'s document with (_typed_responses), and read back off the bytes
    it writes. _send puts scripts first in an authorized page's head, a page of the page class (a builder the route table
    _PAGE_RENDERERS routes to): the page-key script (_PAGE_KEY_JS), and on the response that signs a browser in the seed
    ahead of it. A page renderer's document is read as that sign-in response, which carries both; every other document
    as _send writes it outside the page class."""
    types = _typed_responses()[0][builder]
    assert len(types) == 1, "%s is served under one type, which _as_served reads it as: %r" % (builder, types)
    h = km.Handler.__new__(km.Handler)
    h.request_version, h.command, h.requestline = "HTTP/1.1", "GET", "GET / HTTP/1.1"
    h.client_address, h.wfile = ("127.0.0.1", 0), io.BytesIO()
    h._page_ok = builder in {f.__name__ for f in km._PAGE_RENDERERS.values()}
    h._set_cookie = _SESSION if h._page_ok else None
    h._send(200, text, next(iter(types)))
    _head, sep, body = h.wfile.getvalue().partition(b"\r\n\r\n")
    assert sep, "_send wrote a head and a body"
    return body.decode("utf-8")


def _served_pages():
    """Every page the kernel serves as a document, by route, and /sw.js (the service worker's script): what a script on
    romp's origin that the kernel writes can be. Built by SERVED_BUILDERS' functions and read as _send writes each one
    (_as_served), the scripts _send puts first in a page's head included."""
    out = {}
    for name, builder in SERVED_BUILDERS.items():
        b = getattr(km, builder)
        out[name] = _as_served(builder, b(*_BUILDER_ARGS.get(builder, ())) if callable(b) else b)
    return out


def _served_shell():
    """The shell as the kernel serves it (_served_pages' "/", read alone): what the shell's tests below read and run."""
    return _as_served(SERVED_BUILDERS["/"], getattr(km, SERVED_BUILDERS["/"])())


class _PageScripts(HTMLParser):
    """Every script a document's markup carries, in order, as (where, kind, code): the body of each <script> with no src
    ("script"; a src loads a /dist bundle, whose sources are the ui/ census's), each event handler attribute ("handler",
    run as the body of a function), each javascript: URL in an attribute ("url", the code after the scheme, decoded as a
    browser decodes it), and the same again inside an srcdoc attribute's document."""

    def __init__(self, where=""):
        super().__init__(convert_charrefs=True)
        self.where, self.found, self._script = where, [], None

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            name, value = name.lower(), value or ""
            if name.startswith("on"):
                self.found.append(("%s<%s %s>" % (self.where, tag, name), "handler", value))
            m = re.match(r"[\x00-\x20]*javascript:", value, re.I)
            if m:
                self.found.append(("%s<%s %s>" % (self.where, tag, name), "url", unquote(value[m.end():])))
            if name == "srcdoc":
                inner = _PageScripts("%sthe srcdoc of <%s> " % (self.where, tag))
                inner.feed(value)
                inner.close()
                self.found.extend(inner.found)
        if tag == "script" and not any(n.lower() == "src" for n, _v in attrs):
            self._script = []

    def handle_data(self, data):
        if self._script is not None:
            self._script.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._script is not None:
            self.found.append(("%s<script> %d" % (self.where, sum(k == "script" for _w, k, _c in self.found) + 1), "script",
                               "".join(self._script)))
            self._script = None


def _page_scripts(html):
    """[(where, kind, code)] for every script `html` carries (_PageScripts)."""
    p = _PageScripts()
    p.feed(html)
    p.close()
    return p.found


def _served_documents():
    """{name: text} for every page the kernel writes (each page SERVED_BUILDERS builds) and /sw.js, and each SVG under
    /media (a document a browser runs script in when it is opened). The /dist bundles, which the kernel serves too, are
    not here: the ui/ census (ui/webview/foreign-sender-listeners.test.ts) reads their sources."""
    out = _served_pages()
    for f in sorted(os.listdir(km.MEDIA)):
        if f.endswith(".svg"):
            with open(os.path.join(km.MEDIA, f), encoding="utf-8") as fh:
                out["/media/" + f] = fh.read()
    return out


def _served_scripts():
    """Every script in _served_documents, as {page, where, kind, code}: /sw.js whole, and each other document's scripts as
    _page_scripts finds them. ui/webview/served-script-scopes.test.ts parses each one."""
    out = []
    for name, text in _served_documents().items():
        pieces = [("the script", "script", text)] if name == "/sw.js" else _page_scripts(text)
        out.extend({"page": name, "where": w, "kind": k, "code": c} for w, k, c in pieces)
    return out


def _kernel_code():
    """kernel.py's text less the Python comment lines that describe the served JavaScript (every served line is code)."""
    with open(os.path.join(os.path.dirname(HERE), "kernel", "kernel.py"), encoding="utf-8") as f:
        src = f.read()
    return "\n".join(l for l in src.split("\n") if not l.lstrip().startswith("#"))


class AdoptedCheck(unittest.TestCase):
    """window.__rompPaneSourceOk is the project's text at UPSTREAM_SHA, byte for byte, defined once, ahead of every
    shell listener."""

    def _region(self, text):
        i = text.index(REGION_HEAD)
        j = text.index(REGION_TAIL, i) + len(REGION_TAIL)
        return text[i:j]

    def test_the_adopted_lines_are_the_projects_text_at_the_recorded_commit(self):
        region = self._region(km._LANDING_BOOT_JS)
        self.assertEqual(len(region), ADOPTED_LEN, "the region's length at %s %s" % (UPSTREAM_REPO, UPSTREAM_SHA))
        self.assertEqual(hashlib.sha256(region.encode("utf-8")).hexdigest(), ADOPTED_SHA256,
                         "the adopted lines were edited: they must stay the project's text at %s %s (every fork "
                         "adjustment goes outside them; a fold resolves them as identical)" % (UPSTREAM_REPO, UPSTREAM_SHA))
        self.assertEqual(region.count("\n"), 2, "three lines, as at the recorded commit")
        self.assertTrue(km._LANDING_BOOT_JS.startswith("\n" + region + "\n"),
                        "the region opens _LANDING_BOOT_JS, where the project has it (after its own comment lines)")
        # the fork's lock sits outside the region, as the next line, so the region stays the project's text
        self.assertTrue(km._LANDING_BOOT_JS.startswith("\n" + region + "\n" + LOCK + "\n"),
                        "the lock is the line right after the adopted definition")

    def test_it_is_defined_once_on_the_served_shell_ahead_of_every_listener(self):
        html = _served_shell()
        self.assertEqual(html.count(REGION_HEAD), 1)
        self.assertEqual(html.count("window.__rompPaneSourceOk="), 1, "one definition, no second copy to drift")
        self.assertEqual(html.count(LOCK), 1, "the lock, once")
        # every mention of the name on the page is the definition, the lock, or one listener's fail-closed read (two
        # mentions each), so no assignment in another spelling, and no other reader, sits anywhere in the served shell
        self.assertEqual(html.count("__rompPaneSourceOk"), 2 + 2 * len(LISTENERS),
                         "the name appears only in the adopted definition, the lock and each named listener's gate")
        self.assertEqual(html.count(GATE), len(LISTENERS), "each named listener's gate, once (its spelling; "
                         "ShellListenersExecuted runs the listeners and the check)")
        scripts = _inline_scripts(html)
        where = [n for n, s in enumerate(scripts) if REGION_HEAD in s]
        self.assertEqual(len(where), 1)
        first_listener = min(n for n, s in enumerate(scripts) if LISTEN_OPEN in s)
        self.assertLessEqual(where[0], first_listener, "defined before (or in) the first script that listens (its place; "
                             "ShellListenersExecuted finds the check defined when each listener registers)")
        self.assertLess(scripts[where[0]].index(REGION_HEAD), scripts[where[0]].index(LISTEN_OPEN),
                        "and ahead of that script's first listener (its place; ShellListenersExecuted finds the check defined "
                        "when each listener registers)")
        self.assertLess(html.index("<body"), html.index(REGION_HEAD), "a body script, after the markup it reads (its place; "
                        "ShellListenersExecuted runs the served page)")


# Where the tree is walked for the census below: every file but the repository's own records and tests (a test names
# the check to stand it in, a record names it to describe it) and what is built or cached from the sources.
_CENSUS_SKIP_DIRS = {".git", "node_modules", "dist", "out-tests", "__pycache__", ".pytest_cache", ".venv",
                     "tests", "docs", "plans", "upstream"}
_TEST_FILE = re.compile(r"\.test\.(ts|js|mjs|cjs|tsx)$")


def _files_naming(name):
    """Every file under the repository root, outside _CENSUS_SKIP_DIRS and not a test or a Markdown record, whose bytes
    hold `name`, as paths relative to the root, and the set of files read."""
    root = os.path.dirname(HERE)
    hits, read = [], set()
    needle = name.encode("utf-8")
    for d, subdirs, files in os.walk(root):
        subdirs[:] = sorted(x for x in subdirs if x not in _CENSUS_SKIP_DIRS)
        for f in sorted(files):
            if f.endswith(".md") or _TEST_FILE.search(f):
                continue
            path = os.path.join(d, f)
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            with open(path, "rb") as fh:
                data = fh.read()
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            read.add(rel)
            if needle in data:
                hits.append(rel)
    return hits, read


class NoOtherWriter(unittest.TestCase):
    """Nothing outside the adopted lines, the lock, the thirteen gates and the palette bundle's reader names the check:
    no other code in the kernel (the pane shim, another page's script, a string it serves), and no file anywhere else in
    the tree (a ui/ bundle the shell or a pane loads, the timeline view) but ui/webview/pane-source.ts. That one file is
    the reader the shell's bundled palette calls (paneSourceOk), and its code lines are the project's text at
    UPSTREAM_SHA byte for byte, pinned by sha256 (PANE_SOURCE_SHA256), which read the check and write nothing. So no code
    in the tree replaces the shell's check under its name, on its own window or on a pane's window.parent. This census
    reads text. A replacement the landing makes under a computed name is what the executed legs below catch, on the roads
    their stand-in drives (ShellListenersExecuted says which), and so is a pane page's inline script's through
    window.parent (ServedPagesExecuted). One on a road the stand-in does not drive, or one a ui/ bundle makes under a
    computed name, is refused by the lock once the boot script has run (CheckLocked)."""

    def test_no_file_but_the_kernel_and_the_palettes_reader_names_the_check(self):
        hits, read = _files_naming("__rompPaneSourceOk")
        # the walk reads the sources a script on romp's origin comes from: the kernel's pages, the bundles built from
        # ui/webview (the shell's palette and the reader it calls, every pane's), the timeline view the kernel injects,
        # the extension's source
        for must in ("kernel/kernel.py", "ui/webview/palette-main.ts", PANE_SOURCE, "ui/webview/render.ts",
                     "ui/webview/gear.js", "ui/webview/frame-listener.ts", "ui/romp-timeline-view.js",
                     "vscode-extension/src/extension.ts"):
            self.assertIn(must, read, "the walk read " + must)
        self.assertGreater(len([f for f in read if f.startswith("ui/")]), 100, "the walk read ui/ (%d files)" % len(read))
        self.assertEqual(hits, ["kernel/kernel.py", PANE_SOURCE],
                         "a file names the shell's check that is neither the kernel nor the palette's reader, "
                         "ui/webview/pane-source.ts (test_the_palettes_reader_is_the_projects_text_and_writes_nothing "
                         "holds that one to the project's text)")

    def test_the_palettes_reader_is_the_projects_text_and_writes_nothing(self):
        with open(os.path.join(os.path.dirname(HERE), PANE_SOURCE), encoding="utf-8") as f:
            text = f.read()
        lines = text.split("\n")
        head = 0
        while head < len(lines) and lines[head].startswith("//"):
            head += 1
        code = "\n".join(lines[head:])
        self.assertGreater(head, 0, "the fork's header, // comment lines only, ahead of the code")
        self.assertEqual(len(code.encode("utf-8")), PANE_SOURCE_LEN, "the code's length at %s %s" % (UPSTREAM_REPO, UPSTREAM_SHA))
        self.assertEqual(hashlib.sha256(code.encode("utf-8")).hexdigest(), PANE_SOURCE_SHA256,
                         "pane-source.ts's code lines were edited: they must stay the project's text at %s %s (a fold "
                         "resolves them as identical; the fork's words go in the header)" % (UPSTREAM_REPO, UPSTREAM_SHA))
        self.assertEqual(code.count("__rompPaneSourceOk"), 2, "the name, in the code, only in the reader's type and its read")
        self.assertIsNone(re.search(r"__rompPaneSourceOk\s*=(?!=)", code), "and no write of it")

    def test_the_kernel_names_it_only_in_the_adopted_lines_the_lock_and_the_gates(self):
        # the Python comment lines that describe it aside, every mention is in the served JavaScript
        code = _kernel_code()
        self.assertEqual(code.count(REGION_HEAD), 1, "the adopted definition, once")
        self.assertEqual(code.count(LOCK), 1, "the lock, once")
        self.assertEqual(code.count(GATE), len(LISTENERS), "each gate, once")
        self.assertEqual(code.count("__rompPaneSourceOk"), 2 + 2 * len(LISTENERS),
                         "the name appears in kernel.py's code only in the adopted definition, the lock and the gates")

    def test_no_page_but_the_shell_carries_it(self):
        pages = _served_pages()
        del pages["/"]
        for name, page in pages.items():
            with self.subTest(page=name):
                self.assertGreater(len(page), 100, "the page was built")
                self.assertNotIn("__rompPaneSourceOk", page)
        self.assertEqual(_served_shell().count("__rompPaneSourceOk"), 2 + 2 * len(LISTENERS))


class ShellListenerCensus(unittest.TestCase):
    """Every window message listener in the served shell's inline scripts reads the check fail-closed as its first
    statement; the service worker's channel, which no window can post on, is the one listener without it. This census
    reads the page's inline scripts only: the two window listeners of the palette bundle it loads (palette-main.js) read
    the check through ui/webview/pane-source.ts, and ui/webview/foreign-sender-listeners.test.ts takes their census and
    runs them."""

    def setUp(self):
        self.html = _served_shell()

    def test_every_window_listener_in_the_shell_is_named_and_gated(self):
        opens = [m.start() for m in re.finditer(re.escape("window." + LISTEN_OPEN), self.html)]
        self.assertEqual(len(opens), len(LISTENERS),
                         "a window message listener in the shell that LISTENERS does not name (or a named one gone): "
                         "name it there and decide its senders")
        for at in opens:
            head = self.html[at + len("window." + LISTEN_OPEN):][:len(GATE)]
            with self.subTest(at=self.html[at:at + 160]):
                self.assertEqual(head, GATE, "the check, fail-closed, is the listener's first statement (its spelling; "
                                 "ShellListenersExecuted runs each listener against every sender)")
        # no listener in another spelling slips past the census: every message listener on the page is one of the
        # thirteen above or the service worker's channel
        every = _MESSAGE_LISTEN.findall(self.html)
        self.assertEqual(len(every), len(LISTENERS) + 1, "the thirteen window listeners and the service worker's")
        self.assertEqual(self.html.count("swc.addEventListener('message',function(ev){"), 1,
                         "the service worker's own channel: exempt, a window cannot post on it")
        # nor as an onmessage handler: every onmessage assignment on the page, by any receiver, is on one of the sockets
        # or the channel ONMESSAGE_RECEIVERS lists (a socket's and a MessageChannel port's are no window listener, and no
        # other page can post on them), and none sets an onmessageerror handler
        self.assertEqual(_unlisted_onmessage(self.html), [], "an onmessage handler on a receiver ONMESSAGE_RECEIVERS does not list")

    def test_the_onmessage_census_reads_each_spelling(self):
        # every onmessage assignment is read with its receiver, and one on a receiver the table does not list fails: the
        # window by each name a script reaches it by, its frames, a document's window, the body element, a chain the
        # census cannot read, and an onmessageerror handler on any receiver
        for src, receiver in (("window.onmessage=function(e){}", "window"), ("self.onmessage = f", "self"),
                              ("globalThis['onmessage']=f", "globalThis"), ("window [\"onmessage\"] =f", "window"),
                              ("window[`onmessage`]=f", "window"), (";onmessage=function(e){}", ""), ("\n  onmessage = f", ""),
                              ("window . onmessage = f", "window"), ("frames.onmessage=function(e){go(e.data)};", "frames"),
                              ("window.frames.onmessage=f", "window.frames"), ("self.frames.onmessage=f", "self.frames"),
                              ("document.defaultView.onmessage=f", "document.defaultView"), ("document.body.onmessage=f", "document.body"),
                              ("var w0=window;w0.onmessage=f", "w0"), ("top.onmessage=f", "top"), ("x.d.onmessage=f", "x.d"),
                              ("document.querySelector('body').onmessage=f", None), ("window[0].onmessage=f", None),
                              ("foo().d.onmessage=f", None), ("window.onmessageerror=f", "window"), ("ws.onmessageerror=f", "ws")):
            with self.subTest(src=src):
                self.assertEqual([r for r, _h, _c in _onmessage_writes(src)], [receiver])
                self.assertEqual(len(_unlisted_onmessage(src)), 1, "a receiver the table does not list, or an onmessageerror handler")
        for src in ("ws.onmessage=function(ev){}", "d.onopen=d.onmessage=d.onclose=null", "ch.port1.onmessage=flush"):
            with self.subTest(src=src):
                self.assertEqual(_unlisted_onmessage(src), [], "a listed socket or channel")
        for src in ("if(window.onmessage===f)go()", "var x_onmessage=1", "a==onmessage", "// onmessage/onclose"):
            with self.subTest(src=src):
                self.assertEqual(_onmessage_writes(src), [], "no assignment")

    def test_each_named_listener_opens_with_the_check(self):
        for name, phrase in LISTENERS.items():
            with self.subTest(listener=name):
                self.assertEqual(self.html.count(phrase), 1, "the phrase names one place in the shell (the locator this test "
                                 "and ShellListenersExecuted name the listener by)")
                at = self.html.rindex(LISTEN_OPEN, 0, self.html.index(phrase))
                self.assertEqual(self.html[at + len(LISTEN_OPEN):][:len(GATE)], GATE,
                                 "%s opens with the source check (its spelling; ShellListenersExecuted runs it against every "
                                 "sender)" % name)

    def test_the_active_tab_relay_reads_the_shared_check_instead_of_its_own(self):
        # the relay had the one inline origin check in the shell; it reads the shared check now, as the project's does
        js = km._LANDING_FOCUS_JS
        self.assertIn("window.addEventListener('message',function(e){" + GATE +
                      "var m=e&&e.data;if(!m||m.romp!=='activeTab')return;", js,
                      "the activeTab relay opens with the shared check (its spelling; ShellListenersExecuted runs it against "
                      "every sender)")
        self.assertNotIn("e.origin!==location.origin)return;", js,
                         "no origin check of the relay's own is left (its spelling; ShellListenersExecuted runs the relay)")


# ── every window message listener the kernel serves (2026-09-26) ──
# The census above reads the served shell. This one reads all of kernel.py and every page it serves, so a listener added
# to any other page (the chat page's phone script, a small inline script on /feed or /settings, the sign-in page), or a
# third listener in the pane shim, in any quoting, fails here too, and so does an onmessage assignment on any receiver
# ONMESSAGE_RECEIVERS does not list. Each window message listener in kernel.py's code
# opens with one of the heads below, from its receiver through its first statement, and each head occurs the number of
# times listed. A new listener, or a listed one gone, fails until this table names it, which is where its senders get
# decided.
KERNEL_LISTENER_KINDS = {
    "shell (the adopted source check)": ("window.", "addEventListener('message',function(e){" + GATE, len(LISTENERS)),
    "pane shim (fromShell; tests/test_pane_shim_return.py)":
        ("window.", 'addEventListener("message",function(e){if(!fromShell(e))return;', 2),
    "timeline boot (heardSender; tests/test_timeline_boot_shim.py)":
        ("window.", 'addEventListener("message",function(e){if(!heardSender(e))return;', 1),
    "the service worker's channel (exempt: no window posts on it)": ("swc.", "addEventListener('message',function(ev){", 1),
}
# What each served page carries, by kind: the shell's listeners and the service worker channel on the shell, the pane
# shim's two on every pane page, and the timeline boot's beside them on /timeline.
PAGE_LISTENERS = {
    "/": {"shell (the adopted source check)": len(LISTENERS),
          "the service worker's channel (exempt: no window posts on it)": 1},
    "/timeline": {"pane shim (fromShell; tests/test_pane_shim_return.py)": 2,
                  "timeline boot (heardSender; tests/test_timeline_boot_shim.py)": 1},
    "the sign-in page": {}, "the too-large page": {}, "/sw.js": {},
}
for _page in ("/chat", "/feed", "/fleet", "/waiting", "/files", "/settings"):
    PAGE_LISTENERS[_page] = {"pane shim (fromShell; tests/test_pane_shim_return.py)": 2}

# A message listener in any spelling text can show: the method named or reached by a computed member, the event type in
# any quotes, a message or a messageerror (which carries the sender's origin and source as a message does, and which a
# sender causes by posting what the page cannot deserialize; no listed kind hears one, so a messageerror listener fails
# until it is listed). (A registration that reaches the method with no such text, window['add'+'EventListener'], is the executed
# legs' to catch: the shell's and every served page's below, and the shim's in tests/test_pane_shim_return.py.)
_MESSAGE_LISTEN = re.compile(r"(?:(?<![\w$])addEventListener|\[\s*(['\"`])addEventListener\1\s*\])\s*\(\s*(['\"`])message(?:error)?\2")
# Every addEventListener in the kernel's code, named: each must be a call with a literal event type, so that the census
# above reads the type (a bind, a call or apply, a comma-operator call, a variable holding the method, or a computed type
# are the ways around it). Two other shapes stand: a feature test followed at once by the same receiver's literal call
# (`x.addEventListener)x.addEventListener('load',...)`), and the calls with a computed type below, each over a literal
# list that holds no "message".
_ADD_TOKEN = re.compile(r"(?<![\w$])addEventListener(?![\w$])")
_LITERAL_CALL = re.compile(r"\s*\(\s*(['\"`])[\w:.-]*\1")
COMPUTED_TYPE_CALLS = {
    "document.addEventListener(END[k],ended,true)":
        "var END=['pointerup','touchend','touchcancel','scrollend','dragend','drop','selectionchange','input','focusout'];",
}


def _listener_kind(text, at):
    """The KERNEL_LISTENER_KINDS name of the message listener whose match starts at `at` in `text`, or None."""
    for name, (receiver, head, _n) in KERNEL_LISTENER_KINDS.items():
        if text.startswith(head, at) and text[max(0, at - len(receiver)):at] == receiver:
            return name
    return None


def _message_listeners(text):
    """[(kind or None, the call's first 160 characters)] for every message listener `text` spells."""
    return [(_listener_kind(text, m.start()), text[max(0, m.start() - 8):m.start() + 160])
            for m in _MESSAGE_LISTEN.finditer(text)]


_RECEIVER = re.compile(r"(?<![\w$.])([\w$]+(?:\.[\w$]+)*)\.$")


def _feature_test(code, m):
    """True when the addEventListener token matched by `m` is a feature test followed at once by the same receiver's call
    with a literal event type: `x.addEventListener)x.addEventListener('load',...)`."""
    if not code.startswith(")", m.end()):
        return False
    r = _RECEIVER.search(code, max(0, m.start() - 200), m.start())
    if not r:
        return False
    call = r.group(1) + ".addEventListener"
    return code.startswith(call, m.end() + 1) and bool(_LITERAL_CALL.match(code, m.end() + 1 + len(call)))


def _loose_add_tokens(code):
    """Every addEventListener in `code` that is not a call with a literal event type, a feature test ahead of one, or a
    listed computed-type call, with its surroundings."""
    loose = []
    for m in _ADD_TOKEN.finditer(code):
        if _LITERAL_CALL.match(code, m.end()) or _feature_test(code, m):
            continue
        if any(code.startswith(site, m.start() - site.index("addEventListener")) for site in COMPUTED_TYPE_CALLS):
            continue
        loose.append(code[max(0, m.start() - 40):m.end() + 40])
    return loose


class KernelListenerCensus(unittest.TestCase):
    """Every window message listener in kernel.py, and in the inline scripts of every page it serves, is one of the listed
    kinds: the shell's (the adopted check), the pane shim's (fromShell), the timeline boot's (heardSender), and the
    service worker's channel (the /dist bundles the pages load are ui/webview/foreign-sender-listeners.test.ts's census).
    Every onmessage assignment in the kernel's code and its pages, whatever its receiver, is on one of the sockets or the
    channel ONMESSAGE_RECEIVERS lists, by the receiver's name, and none sets an onmessageerror handler; and no
    addEventListener in the kernel's code escapes the census by an alias or a computed event type."""

    def test_every_message_listener_in_the_kernels_code_is_a_listed_kind(self):
        found = _message_listeners(_kernel_code())
        unknown = [at for kind, at in found if kind is None]
        self.assertEqual(unknown, [], "a message listener in kernel.py that KERNEL_LISTENER_KINDS does not list: list its "
                                      "kind there, which is where its senders are decided")
        for name, (_receiver, _head, n) in KERNEL_LISTENER_KINDS.items():
            with self.subTest(kind=name):
                self.assertEqual(sum(1 for kind, _ in found if kind == name), n, "how many listeners of this kind the kernel has")
        self.assertEqual(len(found), sum(n for _r, _h, n in KERNEL_LISTENER_KINDS.values()))

    def test_every_onmessage_assignment_in_the_kernels_code_is_a_listed_socket_or_channel(self):
        got = {}
        for r, h, _ctx in _onmessage_writes(_kernel_code()):
            key = r if h == "onmessage" else "%s (%s)" % (r, h)
            got[key] = got.get(key, 0) + 1
        self.assertEqual(got, ONMESSAGE_RECEIVERS, "an onmessage assignment in kernel.py on a receiver ONMESSAGE_RECEIVERS does "
                         "not list, or a listed one gone: %r" % _unlisted_onmessage(_kernel_code()))

    def test_every_add_event_listener_in_the_kernels_code_names_its_event_type(self):
        code = _kernel_code()
        self.assertEqual(_loose_add_tokens(code), [],
                         "an addEventListener in kernel.py that is not a call with a literal event type (an alias, a bind, "
                         "a call or apply, a computed type): the message census cannot read it")
        for site, defn in COMPUTED_TYPE_CALLS.items():
            with self.subTest(site=site):
                self.assertEqual(code.count(site), 1, "the computed-type call, once")
                self.assertEqual(code.count(defn), 1, "its literal list of event types, once")
                self.assertNotIn("message", defn)
                name = defn[len("var "):defn.index("=")]
                self.assertIsNone(re.search(r"(?<![\w$.])%s\s*(?:\.\s*(?:push|unshift|splice|concat)|\[[^\]]*\]\s*=(?!=))" % name, code),
                                  "the list is never added to")
        self.assertGreater(len(_ADD_TOKEN.findall(code)), 150, "the census read the kernel's listeners")

    def test_every_served_page_carries_only_its_listed_listeners(self):
        pages = _served_pages()
        self.assertEqual(set(pages), set(PAGE_LISTENERS), "every page the census reads has its expected kinds listed")
        for name, page in pages.items():
            with self.subTest(page=name):
                found = _message_listeners(page)
                self.assertEqual([at for kind, at in found if kind is None], [], "a message listener of no listed kind")
                got = {}
                for kind, _ in found:
                    got[kind] = got.get(kind, 0) + 1
                self.assertEqual(got, PAGE_LISTENERS[name])
                self.assertEqual(_unlisted_onmessage(page), [], "an onmessage handler on a receiver ONMESSAGE_RECEIVERS does not list")
                self.assertIsNone(re.search(r"<[a-z][^>]*\sonmessage\s*=", page, re.I), "an onmessage attribute on an element")

    def test_the_census_reads_each_spelling(self):
        listener = "function(e){var m=e&&e.data;}"
        for src in ("window.addEventListener('message'," + listener + ");",
                    'window.addEventListener("message",' + listener + ");",
                    "window.addEventListener(`message`," + listener + ");",
                    "addEventListener ( 'message' ," + listener + ");",
                    "window['addEventListener']('message'," + listener + ");",
                    "self [ \"addEventListener\" ] (\"message\"," + listener + ");",
                    "try{window.addEventListener('message',function(e){if(!fromShell(e))return;});}catch(e){}",
                    "window.addEventListener('messageerror'," + listener + ");",
                    "window.addEventListener(\"messageerror\",function(e){" + GATE + "});"):
            with self.subTest(src=src):
                self.assertEqual([k for k, _ in _message_listeners(src)], [None], "one listener, of no listed kind")
        for name, (receiver, head, _n) in KERNEL_LISTENER_KINDS.items():
            with self.subTest(kind=name):
                self.assertEqual([k for k, _ in _message_listeners(receiver + head + "});")], [name])
                self.assertEqual([k for k, _ in _message_listeners("x." + head + "});")], [None], "on another receiver")
        for src in ("window.addEventListener('resize'," + listener + ");", "var s='messages';", "removeEventListener('message',f)"):
            with self.subTest(src=src):
                self.assertEqual(_message_listeners(src), [])

    def test_the_add_event_listener_census_refuses_every_way_around_the_literal(self):
        for src in ("var add=window.addEventListener;add('message',f);",
                    "window.addEventListener.bind(window)('message',f);",
                    "window.addEventListener.call(window,'message',f);",
                    "(0,window.addEventListener)('message',f);",
                    "window.addEventListener(TYPES[i],f);",
                    "if(x.addEventListener)y.addEventListener('load',f);",
                    "if(x.addEventListener)x.addEventListener(t,f);"):
            with self.subTest(src=src):
                self.assertGreaterEqual(len(_loose_add_tokens(src)), 1, "refused")
        for src in ("window.addEventListener('load',f);", "el.addEventListener( \"click\" ,f);",
                    "if(swc&&swc.addEventListener)swc.addEventListener('message',f);",
                    "if(MQ.addEventListener)MQ.addEventListener('change',f);",
                    "for(var k=0;k<END.length;k++)document.addEventListener(END[k],ended,true);"):
            with self.subTest(src=src):
                self.assertEqual(_loose_add_tokens(src), [], "accepted")


# The types a response can carry that a browser runs script in, or that are script: a _send with one of these as a literal
# type serves a page SERVED_BUILDERS must list.
_SCRIPT_TYPES = {"text/html", "application/xhtml+xml", "image/svg+xml", "text/xml", "application/xml", "text/javascript",
                 "application/javascript"}
# Every _send, and every Content-Type header outside _send, whose type is not a literal, by the function it sits in and
# the type's expression: how many there are, and why none is a script the kernel writes.
OTHER_TYPED_RESPONSES = {
    ("_file_slice", "ctype"): (1, "the file popover's answer, JSON or a text slice (_slice_body)"),
    ("_file_preview", "mime"): (4, "a file of the user's, typed by the view allowlists (_PREVIEW_MIME, text as text/plain; an "
                                   "SVG with a sandbox policy)"),
    ("_remote_file", "ctype"): (3, "a remote's file, typed by the same allowlists"),
    ("do_GET", "ct + '; charset=utf-8'"): (2, "/dist and /media: the bundles a page loads by src, whose sources the ui/ "
                                               "census reads, and the media files, whose SVGs _served_scripts reads"),
}
# The files under /media, by extension: none but the SVGs can hold script, and _served_scripts reads those.
MEDIA_KINDS = {".svg", ".png", ".woff2", ".ttf", ".txt"}


def _route_tables(tree):
    """{name: [value names]} for every module-level assignment in `tree` of a dict literal whose values are all names: a
    route table, such as _PAGE_RENDERERS."""
    out = {}
    for st in tree.body:
        if (isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name)
                and isinstance(st.value, ast.Dict) and st.value.values
                and all(isinstance(v, ast.Name) for v in st.value.values)):
            out[st.targets[0].id] = [v.id for v in st.value.values]
    return out


# Every field of Python's syntax tree that holds an identifier, sorted by whether the identifier is a name the node binds
# (or declares, for global and nonlocal) in the scope it sits in. _bound_names reads the first table: Name.id binds only
# as a store, and an import binds the first part of its dotted name unless it has an as name. The second table's fields
# hold an attribute's name, a module's dotted name or a call's keyword, none a binding. A node an older interpreter lacks
# (the type parameters, 3.12 on) is skipped there. test_every_identifier_field_of_the_grammar_is_sorted re-derives the
# fields from the running interpreter's ast module, so a field a later grammar adds fails there until it is sorted here.
_BINDING_FIELDS = {"Name": ("id",), "arg": ("arg",), "alias": ("name", "asname"), "FunctionDef": ("name",),
                   "AsyncFunctionDef": ("name",), "ClassDef": ("name",), "ExceptHandler": ("name",), "MatchAs": ("name",),
                   "MatchStar": ("name",), "MatchMapping": ("rest",), "Global": ("names",), "Nonlocal": ("names",),
                   "TypeVar": ("name",), "ParamSpec": ("name",), "TypeVarTuple": ("name",)}
_NON_BINDING_FIELDS = {"Attribute": ("attr",), "ImportFrom": ("module",), "MatchClass": ("kwd_attrs",), "keyword": ("arg",)}


def _identifier_fields():
    """{(node class name, field)} for every field the running interpreter's ast module types as an identifier, read off
    each concrete node class's signature (its __doc__: `FunctionDef(identifier name, arguments args, ...)`)."""
    out = set()
    for name in dir(ast):
        c = getattr(ast, name)
        if isinstance(c, type) and issubclass(c, ast.AST) and getattr(c, "_fields", ()) and c.__doc__:
            for m in re.finditer(r"\bidentifier[?*]? (\w+)", c.__doc__.split("\n")[0]):
                if m.group(1) in c._fields:
                    out.add((name, m.group(1)))
    return out


def _bound_names(n):
    """The names node `n` binds or declares in the scope it sits in, read by _BINDING_FIELDS."""
    if isinstance(n, ast.Name):
        return [n.id] if isinstance(n.ctx, ast.Store) else []
    if isinstance(n, ast.alias):
        return [(n.asname or n.name).split(".")[0]]
    out = []
    for f in _BINDING_FIELDS.get(type(n).__name__, ()):
        v = getattr(n, f, None)
        out.extend(v if isinstance(v, list) else [v] if v else [])
    return out


def _table_reads(fn, tables):
    """{local name: [value names]} for each name `fn` binds only by reading a route table, `x = TABLE.get(...)` or
    `x = TABLE[...]` (each value of the table is what it can hold). A name bound or declared any other way as well, in
    `fn` or in a function or class nested in it, is not here, so a body that calls it stays unresolved: every binding
    _bound_names reads counts (another assignment, a parameter, a loop, a with, an import, a walrus, a def or a class of
    that name, an except's as name, a match capture, star or mapping rest, a type parameter, a global or nonlocal
    declaration). The name of `fn` itself binds in the scope around it, not in `fn`, and does not count."""
    reads, stores = {}, {}
    for n in ast.walk(fn):
        for k in ([] if n is fn else _bound_names(n)):
            stores[k] = stores.get(k, 0) + 1
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            v, table = n.value, None
            if isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr == "get" \
                    and isinstance(v.func.value, ast.Name):
                table = v.func.value.id
            elif isinstance(v, ast.Subscript) and isinstance(v.value, ast.Name):
                table = v.value.id
            if table in tables:
                reads.setdefault(n.targets[0].id, []).append(table)
    return {k: [b for t in ts for b in tables[t]] for k, ts in reads.items() if stores.get(k) == len(ts)}


def _typed_responses_of(tree):
    """_typed_responses over the syntax tree `tree`, the builders' types as sets."""
    tables = _route_tables(tree)
    builders, other = {}, {}

    def walk(node, fn, reads):
        for ch in ast.iter_child_nodes(node):
            inner, inner_reads = fn, reads
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)):
                inner, inner_reads = ch.name, _table_reads(ch, tables)
            if isinstance(ch, ast.Call) and isinstance(ch.func, ast.Attribute) and inner != "_send":
                typ = None
                if ch.func.attr == "_send":
                    typ = ch.args[2] if len(ch.args) > 2 else next((k.value for k in ch.keywords if k.arg == "ctype"), None)
                elif (ch.func.attr == "send_header" and len(ch.args) == 2 and isinstance(ch.args[0], ast.Constant)
                      and str(ch.args[0].value).lower() == "content-type"):
                    typ = ch.args[1]
                if typ is not None and not isinstance(typ, ast.Constant):
                    key = (inner, ast.unparse(typ))
                    other[key] = other.get(key, 0) + 1
                elif typ is not None and str(typ.value).split(";")[0].strip().lower() in _SCRIPT_TYPES:
                    body = ch.args[1] if ch.func.attr == "_send" else None
                    name = (body.func.id if isinstance(body, ast.Call) and isinstance(body.func, ast.Name)
                            else body.id if isinstance(body, ast.Name) else None)
                    found = (inner_reads.get(name) or [name]) if name is not None else [
                        "<%s in %s>" % (ast.unparse(body) if body is not None else ch.func.attr, inner)]
                    for b in found:
                        builders.setdefault(b, set()).add(typ.value)
            walk(ch, inner, inner_reads)

    walk(tree, None, {})
    return builders, other


@functools.lru_cache(maxsize=1)
def _typed_responses_cached():
    with open(os.path.join(os.path.dirname(HERE), "kernel", "kernel.py"), encoding="utf-8") as f:
        return _typed_responses_of(ast.parse(f.read()))


def _typed_responses():
    """({builder of each literal-script-typed _send's body: {the literal types it is sent with}}, {(function, type
    expression): count} for every other _send or Content-Type header whose type is not a literal, _send's own header
    aside), read from kernel.py's syntax tree. A body called or named through a local bound only by reading a route table
    (`_page = _PAGE_RENDERERS.get(p)`, _table_reads) counts as each builder the table holds; a local also bound or
    declared any other way (_bound_names) counts as its own name, which SERVED_BUILDERS lists no builder by."""
    builders, other = _typed_responses_cached()
    return {k: set(v) for k, v in builders.items()}, dict(other)


class ServedScriptPopulation(unittest.TestCase):
    """The pages the censuses here read, and the scripts ui/webview/served-script-scopes.test.ts parses, are every page and
    script the kernel writes: derived from kernel.py's syntax tree, every response typed as HTML, SVG, XML or JavaScript by a
    literal is built by a function SERVED_BUILDERS lists (a page route's builder read through the route table do_GET
    dispatches it by, _PAGE_RENDERERS), and every response typed by an expression is a listed one (OTHER_TYPED_RESPONSES:
    files of the user's or a remote's, the popover's answer, /dist and /media). Each page is read as _send writes it
    (_as_served), so the scripts _send puts first in a page's head (the sign-in seed and the page-key script) are read with
    the page's own. The reader of a page's scripts finds each <script> the other censuses read, and each handler attribute
    and javascript: URL besides."""

    def test_every_page_the_kernel_writes_is_read(self):
        builders, other = _typed_responses()
        self.assertEqual(set(builders), set(SERVED_BUILDERS.values()), "a response typed as a page or a script whose "
                         "builder SERVED_BUILDERS does not list, or a listed builder no response serves")
        self.assertEqual(other, {k: n for k, (n, _why) in OTHER_TYPED_RESPONSES.items()}, "a response typed by an "
                         "expression that OTHER_TYPED_RESPONSES does not list, or a listed one gone: say what it serves")
        self.assertEqual(set(_served_pages()), set(SERVED_BUILDERS))

    def test_each_page_route_is_listed_with_the_builder_the_route_table_names(self):
        # do_GET serves a page by looking its renderer up in _PAGE_RENDERERS, so SERVED_BUILDERS names the same builder for
        # each of its routes (its "" is the shell's bare path, which SERVED_BUILDERS lists as "/")
        renderers = {f.__name__ for f in km._PAGE_RENDERERS.values()}
        self.assertEqual({r or "/": f.__name__ for r, f in km._PAGE_RENDERERS.items()},
                         {r: b for r, b in SERVED_BUILDERS.items() if b in renderers})

    def test_a_body_through_a_route_table_counts_as_each_builder_the_table_holds(self):
        # the derivation, over sources of our own: a local bound only by a read of a module-level table of names counts as
        # every name in the table (.get or an index); a local bound or declared any other way as well counts as itself,
        # which SERVED_BUILDERS lists no builder by, so the census reds. One row per binding form _BINDING_FIELDS holds
        # (the type parameters only where the grammar has them), each in f's body ahead of the read, or in a function
        # nested in f
        table = "T = {'/a': _a, '/b': _b}\n"
        send = "    return self._send(200, g(), 'text/html')\n"
        for src, want in (
                ("def f(self, p):\n    g = T.get(p)\n" + send, {"_a", "_b"}),
                ("def f(self, p):\n    g = T[p]\n" + send, {"_a", "_b"}),
                ("def f(self, p):\n    g = T.get(p)\n    h = g\n" + send, {"_a", "_b"}),
                ("def g(self, p):\n    g = T.get(p)\n" + send, {"_a", "_b"}),
                ("def f(self, p):\n    g = U.get(p)\n" + send, {"g"})):
            with self.subTest(src=src):
                builders, _other = _typed_responses_of(ast.parse(table + src))
                self.assertEqual(set(builders), want)
        rebinds = [("a second assignment", "g = h"), ("a loop", "for g in x: pass"), ("a with", "with x as g: pass"),
                   ("an import", "import g"), ("a dotted import", "import g.h"), ("an import's as name", "from m import h as g"),
                   ("a walrus", "(g := h)"), ("a comprehension", "[g for g in x]"), ("a lambda's parameter", "lambda g: 0"),
                   ("a def", "def g(): pass"), ("an async def", "async def g(): pass"), ("a class", "class g: pass"),
                   ("an except's as name", "try: pass\n    except E as g: pass"),
                   ("a match capture", "match x:\n        case g: pass"),
                   ("a match capture's as name", "match x:\n        case [1] as g: pass"),
                   ("a match star", "match x:\n        case [*g]: pass"),
                   ("a mapping's rest", "match x:\n        case {**g}: pass"), ("a global declaration", "global g"),
                   ("a nested function's store", "def h():\n        g = 1")]
        if hasattr(ast, "TypeVar"):   # the type parameters, 3.12 on
            rebinds += [("a type parameter", "def h[g](): pass"), ("a ParamSpec", "def h[**g](): pass"),
                        ("a TypeVarTuple", "def h[*g](): pass")]
        for what, line in rebinds:
            with self.subTest(what=what):
                src = "def f(self, p):\n    %s\n    g = T.get(p)\n%s" % (line, send)
                builders, _other = _typed_responses_of(ast.parse(table + src))
                self.assertEqual(set(builders), {"g"}, what + ": a second binding leaves the local unresolved")
        with self.subTest(what="a parameter"):
            builders, _other = _typed_responses_of(ast.parse(table + "def f(self, g):\n    g = T.get(p)\n" + send))
            self.assertEqual(set(builders), {"g"})
        with self.subTest(what="a nonlocal declaration"):
            src = "def o():\n    g = h\n    def f(self, p):\n        nonlocal g\n        g = T.get(p)\n    " + send
            builders, _other = _typed_responses_of(ast.parse(table + src))
            self.assertEqual(set(builders), {"g"})

    def test_every_identifier_field_of_the_grammar_is_sorted(self):
        # _table_reads counts a second binding by _BINDING_FIELDS; a field of the running interpreter's grammar that holds an
        # identifier and sits in neither table is a binding form the count may not see
        fields = _identifier_fields()
        self.assertTrue({("Name", "id"), ("FunctionDef", "name"), ("keyword", "arg")} <= fields,
                        "the derivation reads the grammar's signatures: %r" % sorted(fields))
        self.assertEqual(fields, {(c, f) for t in (_BINDING_FIELDS, _NON_BINDING_FIELDS) for c, fs in t.items() for f in fs
                                  if hasattr(ast, c)}, "an identifier field sorted into neither table, or a listed one gone")

    def test_each_page_is_read_as_send_writes_it(self):
        # a page of the page class (a builder the route table routes to) carries the sign-in seed and then the page-key
        # script ahead of its own scripts, as _send writes it on the response that signs a browser in; every other document
        # is as built but for the stamp _send writes on a text/html 200 whose body carries an <html> tag (kernel.py
        # _stamp_served_html: ` data-romp-served=200` after the first `<html`), since _send adds nothing else outside the
        # page class. _as_served writes every document as a 200, whatever status the kernel sends it with, so the stamp
        # expected here on a document the kernel sends with another status (the too-large page, a 413) is this model's,
        # not the kernel's response
        pages = _served_pages()
        renderers = {f.__name__ for f in km._PAGE_RENDERERS.values()}
        self.assertEqual(len(renderers), 8, "the shell, the six pane pages and the timeline")
        for name, builder in SERVED_BUILDERS.items():
            b = getattr(km, builder)
            built = b(*_BUILDER_ARGS.get(builder, ())) if callable(b) else b
            with self.subTest(page=name):
                if builder not in renderers:
                    want = built
                    if next(iter(_typed_responses()[0][builder])).startswith("text/html"):
                        want = re.sub(r"(<html)(?=[\s>])", r"\1 data-romp-served=200", built, count=1, flags=re.I)
                    self.assertEqual(pages[name], want)
                    continue
                scripts = _inline_scripts(pages[name])
                self.assertIn(json.dumps(km._page_key(_SESSION)), scripts[0], "the seed first: it stores the page key")
                self.assertTrue(scripts[0].startswith("try{localStorage.setItem("), "the seed first")
                self.assertEqual(scripts[1], km._PAGE_KEY_JS, "then the page-key script")
                self.assertEqual(scripts[2:], _inline_scripts(built), "then the page's own scripts, as built")

    def test_the_media_files_are_svgs_read_as_pages_or_kinds_that_hold_no_script(self):
        files = os.listdir(km.MEDIA)
        self.assertEqual(sorted(f for f in files if os.path.splitext(f)[1] not in MEDIA_KINDS), [])
        self.assertGreater(sum(f.endswith(".svg") for f in files), 0, "the census reads the media SVGs")

    def test_the_reader_finds_the_scripts_the_other_censuses_read_on_every_page(self):
        for name, page in _served_pages().items():
            if name == "/sw.js":
                continue
            with self.subTest(page=name):
                self.assertEqual([c for _w, k, c in _page_scripts(page) if k == "script"], _inline_scripts(page))
        self.assertEqual([k for _w, k, _c in _page_scripts(km._TOKEN_LOGIN_HTML)], ["handler"], "the sign-in form's onsubmit")

    def test_the_reader_finds_every_kind_of_script_markup_carries(self):
        page = ('<script>a()</script><script src="/dist/x.js">x()</script><SCRIPT type="module">b()</SCRIPT>'
                '<form onsubmit="c();return false"><a href="javascript:d(%27x%27)">x</a><a HREF=" JavaScript:e()">y</a>'
                '<iframe srcdoc="&lt;script&gt;f()&lt;/script&gt;&lt;b OnClick=&quot;g()&quot;&gt;"></iframe></form>')
        self.assertEqual([(k, c) for _w, k, c in _page_scripts(page)],
                         [("script", "a()"), ("script", "b()"), ("handler", "c();return false"), ("url", "d('x')"),
                          ("url", "e()"), ("script", "f()"), ("handler", "g()")])


# A stand-in browser for the shell's inline scripts: node's vm runs them in a context whose global answers every name it
# does not hold with an inert stub (callable, constructible, every property another stub, 0 as a number), so the scripts
# boot far enough to register their listeners without a DOM. What the checks read is real: location (its origin is the
# shell's location.origin), document.querySelectorAll('iframe') and window.frames (the shell's frames),
# window.parent/top (the shell is the top window), and each sending window's parent, top and opener. So are the objects
# through which the stand-in hears a window's onmessage handler: the shell's window by any name, document.defaultView
# (the shell's window), document.body itself (whose handler is its window's), window.frames and each frame's window; an
# onmessage or onmessageerror handler written on any of them, by a set or a define, is heard. A body reached any other
# way (a query for it, a frame's document, a contentDocument, document.documentElement.lastElementChild) is an inert
# stub, so a handler written on it is not heard here, and under a computed name no census here reads it. Before any
# message is tested it runs what the scripts left for later and the exercise (ShellListenersExecuted names the roads).
# The harness then hands each registered window message listener a message from each sender and counts how often the
# listener reads the message's data: a listener that returns before reading it acts on nothing.
_HARNESS = r"""
'use strict';
const vm = require('vm');
const fs = require('fs');
const SCRIPTS = JSON.parse(fs.readFileSync(process.env.ROMP_TEST_SCRIPTS, 'utf8'));
const ORIGIN = 'http://127.0.0.1:7777', ELSEWHERE = 'https://elsewhere.example';
// every other listener and handler the scripts register (on the window, the document, a frame or any element the
// stand-in hands them: resize, visibilitychange, storage, focus, keydown, click, a frame's load, ...) and every function
// they hand to a stand-in (an observer's callback, a fetch's then, a stand-in element's forEach): the exercise below runs
// each once. A window message listener is not here; it is heard by the window's own addEventListener
const OTHER = [];
// each once per event type and text: a render that runs again hands over fresh closures of the same code, which ran already
const OTHER_SEEN = new Set();
function other(type, f) {
  if (typeof f !== 'function') return;
  type = String(type);
  const key = type + '\u0000' + Function.prototype.toString.call(f);
  if (OTHER_SEEN.has(key)) return;
  OTHER_SEEN.add(key);
  OTHER.push({ type, f });
}
function onWrite(k, v) { if (typeof k === 'string' && /^on[a-z]/.test(k)) other(k.slice(2), v); }
function handedOn(args) { for (const a of args) other('callback', a); }
const ADD_ON_STUB = function (type, f) { other(type, f); };
const stubHandler = {
  get(t, k) {
    if (k === Symbol.toPrimitive) return () => 0;
    if (k === Symbol.iterator) return function* () {};
    if (typeof k === 'symbol') return undefined;
    if (k === 'length') return 0;
    if (k === 'addEventListener') return ADD_ON_STUB;
    return STUB;
  },
  set(t, k, v) { onWrite(k, v); return true; }, has() { return false; }, deleteProperty() { return true; },
  apply(t, self, args) { handedOn(args); return STUB; }, construct(t, args) { handedOn(args); return STUB; },
};
const STUB = new Proxy(function () {}, stubHandler);
function stubbed(o) {
  return new Proxy(o, { get(t, k) { return (k in t) ? t[k] : stubHandler.get(t, k); },
                        set(t, k, v) { onWrite(k, v); t[k] = v; return true; } });
}
// windows: a pane of the shell (the chat), the Files pane, a sandboxed frame of the shell, a frame of the shell on
// another origin, a window on the shell's location.origin the shell does not hold and that has no edge to it, the page
// that opened the shell, which posts from another origin and from the shell's location.origin (the shell's
// Cross-Origin-Opener-Policy, same-origin, keeps an opener on its own origin, and on a plain-http address a browser
// applies none, Handler._send); and, for the frames in the shell's tab and the windows it opened (their edges are set
// once the shell's window exists, below): a frame nested in the chat pane, sandboxed and on the shell's
// location.origin; a window on the shell's location.origin nested in a pane that replaced its own window.parent with
// the shell (no iframe of the shell holds it); a window the shell opened, on another origin and on the shell's
// location.origin
const POSTED = [];
function win(name) { return heardHandlers(stubbed({ name, postMessage(m) { POSTED.push([name, m]); }, focus() {} })); }
const CHAT = win('chat'), FILES = win('files'), SANDBOXED = win('sandboxed'), XFRAME = win('xframe'),
      STRAY = win('stray'), OPENER = win('opener');
const NESTED_SBX = win('nested-sandboxed'), NESTED = win('nested'), FORGED = win('parent-replaced'),
      POPUP = win('popup'), POPUP_SO = win('popup-same-origin');
function frame(id, w) { return stubbed({ id, contentWindow: w, getAttribute(n) { return n === 'id' ? id : null; },
                                         addEventListener(type, f) { other(type, f); }, removeEventListener() {} }); }
const FRAMES = [frame('f-chat', CHAT), frame('f-files', FILES), frame('f-url', SANDBOXED), frame('f-x', XFRAME)];
const BYID = {}; FRAMES.forEach((f) => { BYID[f.id] = f; });
// what the page leaves for later: timer, animation-frame, idle and microtask callbacks, and the listeners for the page's
// load events (window's and document's) and an on<load event> handler. All run after the scripts and before any
// message is delivered, so a write the page defers is in place when the listeners are tested
const LATE = [];
const LATE_EVENTS = new Set(['load', 'DOMContentLoaded', 'pageshow', 'readystatechange']);
function later(f) { if (typeof f === 'function') LATE.push(f); return LATE.length; }
// every value the scripts assign to a window's onmessage or onmessageerror handler, however spelled: an onmessage
// handler is a window message listener addEventListener never sees. The global's writes are heard at G below; these are
// the other objects a script reaches such a handler through: the body element, whose handler is its window's, the
// shell's frames list and each frame's window (win above), each by a set or a define
const HANDLERS = new Set(['onmessage', 'onmessageerror']);
const ONMESSAGE = [];
function heardHandlers(o) {
  return new Proxy(o, {
    set(t, k, v) { if (HANDLERS.has(k)) ONMESSAGE.push(textOf(v)); t[k] = v; return true; },
    defineProperty(t, k, d) { if (HANDLERS.has(k)) ONMESSAGE.push(textOf('value' in d ? d.value : d.set)); return Reflect.defineProperty(t, k, d); },
  });
}
const BODY = heardHandlers(stubbed({}));
const document = stubbed({
  body: BODY,
  querySelectorAll(sel) { return sel === 'iframe' ? FRAMES.slice() : []; },
  getElementById(id) { return BYID[id] || STUB; },
  addEventListener(type, f) { if (LATE_EVENTS.has(type)) later(f); else other(type, f); },
  removeEventListener() {},
});
const LISTENERS = [];
const target = {};
// every value the scripts assign to the check, whatever the assignment's spelling (window.x=, window['x']=, a bare
// global, a defineProperty): each lands on the context's global, so each is heard here. vm reports one assignment as
// more than one trap (creating the property is a set, a define and a set again), so a value is kept once, by identity,
// in the order first heard; an accessor's descriptor is kept as itself
const CHECK = '__rompPaneSourceOk', ASSIGNED = [];
function heard(v) { if (!ASSIGNED.includes(v)) ASSIGNED.push(v); }
// a write of the window's own onmessage or onmessageerror handler, however spelled (window.x=, a computed member, a bare
// global, a defineProperty), lands on the global and is heard here (ONMESSAGE, above)
function onGlobalWrite(k, v) {
  if (k === CHECK) heard(v);
  if (HANDLERS.has(k)) ONMESSAGE.push(textOf(v));
  if ((k === 'onload' || k === 'onpageshow') && typeof v === 'function') later(v);
  else if (!HANDLERS.has(k)) onWrite(k, v);
}
function textOf(v) { return typeof v === 'function' ? Function.prototype.toString.call(v) : typeof v; }
const BUILTINS = new Set(['Object', 'Array', 'JSON', 'Math', 'Date', 'String', 'Number', 'Boolean', 'RegExp', 'Error',
  'TypeError', 'RangeError', 'SyntaxError', 'ReferenceError', 'Map', 'Set', 'WeakMap', 'WeakSet', 'Symbol', 'Promise',
  'parseInt', 'parseFloat', 'isNaN', 'isFinite', 'encodeURIComponent', 'decodeURIComponent', 'encodeURI', 'decodeURI',
  'Infinity', 'NaN', 'undefined', 'Intl', 'URL', 'URLSearchParams', 'Reflect', 'Proxy', 'BigInt', 'Function']);
// The global keeps a browser's rules for a locked property (the shell's check after its lock): a write to a read-only
// property keeps the value (a strict-mode script's throws), and a define or delete the property refuses is refused.
// (vm's global answers most of these before a trap runs, from the property's descriptor, which is read through
// getOwnPropertyDescriptor below.) A define counts as a write only when it carries a value or an accessor; one that
// changes attributes alone, as the lock's {writable:false,configurable:false} does, writes nothing and the property keeps
// its value. vm hands this trap a define that carries no value as one whose value is undefined (node's contextify
// definer fills the missing value in), so on a data property an undefined value is taken as no value: the property
// keeps what it holds, as in a browser. (A define that really sets the check to undefined is taken the same way, and
// missed: an undefined check refuses every message, which is no widening for the tests here to catch.)
// One cost of that, in this harness only: the lock's own define throws here. The trap applies the lock with the value the
// property holds, and the proxy then checks the define it was handed (value undefined) against the property, now
// read-only with another value, and throws a TypeError (its invariant for a non-configurable property). The property is
// locked with its value by then, and the lock line's own try absorbs the throw, so the boot script runs on; a browser
// throws nothing there. A lock written without its try would abort the boot script here and not in a browser, so read
// such an abort as the harness, not the page (CheckLocked's trap test runs the define bare and pins both halves).
// The set trap's read-only clause below is a belt: vm refuses a write to a read-only property from its descriptor before
// the trap runs, so the clause is not reached today.
const G = new Proxy(target, {
  has() { return true; },
  get(t, k) { if (k in t) return t[k]; if (typeof k === 'symbol') return undefined; if (BUILTINS.has(k)) return globalThis[k]; return STUB; },
  set(t, k, v) {
    const d = Object.getOwnPropertyDescriptor(t, k);
    if (d && ('value' in d ? !d.writable : !d.set)) return false;
    onGlobalWrite(k, v); t[k] = v; return true;
  },
  defineProperty(t, k, d) {
    const held = Object.getOwnPropertyDescriptor(t, k);
    if ('value' in d && d.value === undefined && held && 'value' in held) d = Object.assign({}, d, { value: held.value });
    else if ('value' in d) onGlobalWrite(k, d.value);
    else if ('get' in d || 'set' in d) onGlobalWrite(k, d);
    return Reflect.defineProperty(t, k, d);
  },
  getOwnPropertyDescriptor(t, k) { return Object.getOwnPropertyDescriptor(t, k); },
  deleteProperty(t, k) { return Reflect.deleteProperty(t, k); },
});
Object.assign(target, {
  window: G, self: G, top: G, parent: G, globalThis: G, document,
  location: stubbed({ origin: ORIGIN, protocol: 'http:', host: '127.0.0.1:7777', hostname: '127.0.0.1', port: '7777',
                      pathname: '/', search: '', hash: '', href: ORIGIN + '/', reload() {}, replace() {}, assign() {} }),
  localStorage: stubbed({ getItem() { return null; }, setItem() {}, removeItem() {} }),
  sessionStorage: stubbed({ getItem() { return null; }, setItem() {}, removeItem() {} }),
  setTimeout: later, clearTimeout() {}, setInterval: later, clearInterval() {},
  requestAnimationFrame: later, cancelAnimationFrame() {}, requestIdleCallback: later, cancelIdleCallback() {},
  queueMicrotask: later,
  innerWidth: 1280, innerHeight: 800,
  addEventListener(type, f) {
    if (type === 'message' || type === 'messageerror') LISTENERS.push({ f, src: String(f), checkDefined: typeof target.__rompPaneSourceOk === 'function' });
    else if (LATE_EVENTS.has(type)) later(f);
    else other(type, f);
  },
  removeEventListener() {},
});
const ctx = vm.createContext(G);
// Each window's edges, as a browser gives them, set before the scripts run. The shell's page is the top of its tab: the
// target's window, parent and top are all G, which a script reads as the shell's window (vm hands the context's global
// back, not G, when a script reads a name that holds G, so the edges below point at the shell's window as its scripts see
// it). Its iframes are its children: each has the shell as parent and top, and window.frames lists them (in a browser
// window.frames is the window itself, indexed by its frames; vm's global reads window[i] but answers `i in window` false,
// so Array.prototype.indexOf over it finds nothing, and an array of the same windows stands in, with window.length and
// window[i] reading the same list; the array hears a handler written on it, as the window it stands for would, and each
// frame's window hears one written on it). The document's defaultView is the shell's window. A frame nested in a pane has the pane as parent and the shell as top. A window the
// shell opened has the shell as its opener, and the page that opened the shell is its opener.
// test_the_stand_in_windows_carry_the_edges_a_browser_gives_them reads these edges as the scripts see them.
const SHELL_WIN = vm.runInContext('window', ctx);
document.defaultView = SHELL_WIN;   // the shell's document's window is the shell's
[CHAT, FILES, SANDBOXED, XFRAME].forEach((w) => { w.parent = SHELL_WIN; w.top = SHELL_WIN; });
target.frames = heardHandlers([CHAT, FILES, SANDBOXED, XFRAME]);
target.length = target.frames.length;
target.frames.forEach((w, i) => { target[i] = w; });
[NESTED_SBX, NESTED].forEach((w) => { w.parent = CHAT; w.top = SHELL_WIN; });
FORGED.parent = SHELL_WIN; FORGED.top = SHELL_WIN;
POPUP.opener = SHELL_WIN; POPUP_SO.opener = SHELL_WIN;
target.opener = OPENER;
const ERRORS = [];
SCRIPTS.forEach((body, n) => {
  try { vm.runInContext(body, ctx, { filename: 'landing-script-' + n + '.js', timeout: 5000 }); }
  catch (e) { ERRORS.push([n, String(e && e.message || e).slice(0, 200)]); }
});
(async () => {
// then what the scripts left for later, in rounds (a callback may leave more), each callback once, every one bounded:
// the scripts' promise reactions first (a macrotask turn drains the microtask queue the context shares with this one),
// then the queued callbacks, each handed a stand-in load event
const LATE_RUN = { queued: 0, ran: 0, errors: 0, rounds: 0 };
async function drain() {
  for (let round = 0; round < 6 && (round === 0 || LATE.length); round++) {
    await new Promise((r) => setImmediate(r));
    const batch = LATE.splice(0, 5000);
    if (!batch.length) break;
    LATE_RUN.rounds++;
    LATE_RUN.queued += batch.length;
    for (const f of batch) {
      target.__b5late = f;
      LATE_RUN.ran++;
      try { vm.runInContext("__b5late.call(window,{type:'load',persisted:false,timeStamp:0})", ctx, { timeout: 2000 }); }
      catch (x) { LATE_RUN.errors++; }
    }
  }
  await new Promise((r) => setImmediate(r));
  LATE_RUN.left = LATE.length;
}
await drain();
// the senders: [name, source, origin]
const SENDERS = {
  opener: [OPENER, ELSEWHERE],             // a page on another origin that opened the dashboard
  openerSameOrigin: [OPENER, ORIGIN],     // a page on the shell's location.origin that opened the dashboard
  sandboxedFrame: [SANDBOXED, 'null'],    // a sandboxed iframe of the shell (opaque origin)
  otherOriginFrame: [XFRAME, ELSEWHERE],  // an iframe of the shell showing another origin
  strayWindow: [STRAY, ORIGIN],           // on the shell's location.origin, not a frame of this document, no edge to it
  nestedSandboxed: [NESTED_SBX, 'null'],  // a sandboxed frame nested in a pane: its top is the shell, no iframe of it
  // a frame on the shell's location.origin nested in a pane: the same top, no iframe of it
  nestedSameOrigin: [NESTED, ORIGIN],
  // a window on the shell's location.origin nested in a pane that set its window.parent to the shell
  nestedParentReplaced: [FORGED, ORIGIN],
  popup: [POPUP, ELSEWHERE],               // a page on another origin the shell opened: its opener is the shell
  popupSameOrigin: [POPUP_SO, ORIGIN],    // a window on the shell's location.origin the shell opened
  shellItself: [SHELL_WIN, ORIGIN],       // the shell's own window, as its scripts see it
  dispatch: [null, ''],                    // no source, no origin: an event this document dispatched
  sourcelessElsewhere: [null, ELSEWHERE], // no source, another origin
  sourcelessOpaque: [null, 'null'],       // no source, the opaque origin: a sandboxed frame gone after it posted
  pane: [CHAT, ORIGIN],                    // a pane of the shell: the one sender heard
};
const IN_EFFECT = new Set();   // the check's text at every delivery
function deliver(l, source, origin, data) {
  IN_EFFECT.add(textOf(target.__rompPaneSourceOk));
  let reads = 0;
  const e = { type: 'message', source, origin, get data() { reads++; return data; } };
  target.__b5f = l.f; target.__b5e = e;
  let threw = null;
  try { vm.runInContext('__b5f(__b5e)', ctx, { timeout: 2000 }); } catch (x) { threw = String(x && x.message || x).slice(0, 120); }
  return { reads, threw };
}
// the words a window message listener's arms compare against: every `.field === 'value'` (or !==, ==, !=) in its text,
// each handed over alone, with a filler of the fields arms commonly also read, and with the listener's other compared
// fields as well (the first value of each), so an arm keyed on two fields is reached too
const FILLER = { on: true, text: 'a line', kind: 'info', pane: 'chat', app: 'chat', tab: 'general', state: 'open', build: 1,
                 sid: '11111111-2222-3333-4444-555555555555', path: 'notes/a.md', usage: {} };
function wordsOf(src) {
  const pairs = [], seen = new Set(), first = {};
  const re = /\.\s*([A-Za-z_$][\w$]*)\s*[!=]==?\s*(['"])([^'"\\]*)\2/g;
  let m;
  while ((m = re.exec(src))) {
    const key = m[1] + '\u0000' + m[3];
    if (seen.has(key)) continue;
    seen.add(key); pairs.push([m[1], m[3]]);
    if (!(m[1] in first)) first[m[1]] = m[3];
  }
  const words = [];
  for (const [k, v] of pairs) words.push({ [k]: v }, Object.assign({}, FILLER, { [k]: v }), Object.assign({}, FILLER, first, { [k]: v }));
  return words;
}
function standIn(type) {
  return stubbed({ type, persisted: false, timeStamp: 0, isTrusted: true, key: '', code: '', data: undefined,
                   detail: undefined, relatedTarget: null, target: STUB, currentTarget: STUB,
                   preventDefault() {}, stopPropagation() {}, stopImmediatePropagation() {} });
}
const MODE = process.env.ROMP_TEST_MODE || 'reads';
// before any message is tested, what else the page does, once each: every other listener and handler the scripts
// registered, handed a stand-in event of its type; every function they handed to a stand-in; and every word each window
// message listener's arms compare against, from each pane; then whatever those left for later. In rounds, since one may
// register, hand over or queue more (a listener registered here is a listener the census and the reads below count)
const EXERCISE = { ran: 0, errors: 0, words: 0, rounds: 0, left: 0, types: {} };
if (MODE === 'reads' || MODE === 'census' || MODE === 'overwrite') {
  const worded = new Set();
  for (let round = 0; round < 6; round++) {
    const batch = OTHER.splice(0, OTHER.length);
    const fresh = LISTENERS.filter((l) => !worded.has(l));
    if (!batch.length && !fresh.length) break;
    EXERCISE.rounds++;
    for (const o of batch) {
      target.__b5late = o.f; target.__b5ev = standIn(o.type);
      EXERCISE.ran++; EXERCISE.types[o.type] = (EXERCISE.types[o.type] || 0) + 1;
      try { vm.runInContext('__b5late.call(window,__b5ev)', ctx, { timeout: 2000 }); } catch (x) { EXERCISE.errors++; }
    }
    for (const l of fresh) {
      worded.add(l);
      for (const w of wordsOf(l.src)) for (const p of [CHAT, FILES]) { EXERCISE.words++; deliver(l, p, ORIGIN, w); }
    }
    await drain();
  }
  EXERCISE.left = OTHER.length + LATE.length + LISTENERS.filter((l) => !worded.has(l)).length;
}
// the check the listeners will read, as the scripts, everything they left for later and the exercise left it
const AFTER_BOOT = textOf(target.__rompPaneSourceOk);
// the check's property as a script on the page reads it: its attributes, and whether it holds a value or an accessor
function descriptorSeen() {
  const d = vm.runInContext("Object.getOwnPropertyDescriptor(window,'__rompPaneSourceOk')", ctx);
  if (!d) return null;
  return { writable: 'value' in d ? d.writable : null, configurable: d.configurable, enumerable: d.enumerable,
           value: 'value' in d ? textOf(d.value) : null, accessor: 'get' in d || 'set' in d };
}
// the windows' edges as a script on the shell's page reads them (window, window.top, window.frames, a sender's parent,
// top and opener), after the scripts, what they left for later and the exercise
target.__b5w = { chat: CHAT, files: FILES, sandboxed: SANDBOXED, xframe: XFRAME, nested: NESTED_SBX, nestedSo: NESTED,
                 forged: FORGED, popup: POPUP, popupSo: POPUP_SO, opener: OPENER };
const EDGES = vm.runInContext(
  "(function(w){var f=window.frames,inF=function(x){return Array.prototype.indexOf.call(f,x)>=0;};" +
  "return {shellIsItsOwnParentAndTop:window.parent===window&&window.top===window," +
  "framesAreTheFourIframes:window.length===4&&inF(w.chat)&&inF(w.files)&&inF(w.sandboxed)&&inF(w.xframe)," +
  "iframesAreItsChildren:[w.chat,w.files,w.sandboxed,w.xframe].every(function(x){return x.parent===window&&x.top===window.top;})," +
  "nestedShareItsTopUnderThePane:[w.nested,w.nestedSo].every(function(x){return x.parent===w.chat&&x.top===window.top&&!inF(x);})," +
  "parentReplacedReadsAsItsChild:w.forged.parent===window&&w.forged.top===window.top&&!inF(w.forged)," +
  "popupsItOpened:w.popup.opener===window&&w.popupSo.opener===window," +
  "itsOpener:window.opener===w.opener};})(__b5w)", ctx);
const out = { errors: ERRORS, listeners: LISTENERS.map((l) => ({ src: l.src, checkDefined: l.checkDefined })),
              assigns: ASSIGNED.map(textOf), afterBoot: AFTER_BOOT, late: LATE_RUN, exercise: EXERCISE, onmessage: ONMESSAGE,
              descriptor: descriptorSeen(), edges: EDGES,
              // how often a planted road ran, by the counter a plant bumps (window.__b5reached): a road the lock leaves
              // nothing to hear on shows it ran here
              reached: typeof target.__b5reached === 'number' ? target.__b5reached : 0 };
const REFUSED_SENDERS = Object.keys(SENDERS).filter((k) => k !== 'pane');
if (MODE === 'reads' || MODE === 'nocheck') {
  // the check missing (held as undefined: a name the context lacks answers with a stub): fail-closed hears nothing
  if (MODE === 'nocheck') target.__rompPaneSourceOk = undefined;   // the page defined none (_without_check), so nothing is locked
  out.reads = LISTENERS.map((l) => {
    const r = {};
    Object.keys(SENDERS).forEach((k) => { r[k] = deliver(l, SENDERS[k][0], SENDERS[k][1], { romp: 'none-of-yours' }).reads; });
    return r;
  });
} else if (MODE === 'effects') {
  // two arms with an effect the harness can see: the relay forwarding an editorSelection into the chat pane, and a
  // pane's notify landing in the Log
  const NOTES = [];
  target.__rompNotify = function (kind, text) { NOTES.push([kind, text]); };
  target.__rompChatTarget = null;            // the split's column lookup: none, so the relay aims at #f-chat
  target.__rompPaneToggle = function () {};
  const relay = LISTENERS.find((l) => l.src.indexOf("m.type==='editorSelection'") >= 0);
  const notify = LISTENERS.find((l) => l.src.indexOf("m.romp==='notify'&&m.text") >= 0);
  const sel = { type: 'editorSelection', text: 'a quoted passage', sid: '11111111-2222-3333-4444-555555555555' };
  const note = { romp: 'notify', kind: 'info', text: 'a planted line' };
  const senders = Object.assign({}, SENDERS, { pane: [FILES, ORIGIN] });   // the Files pane's viewer posts it up
  out.effects = {};
  Object.keys(senders).forEach((k) => {
    POSTED.length = 0; NOTES.length = 0;
    deliver(relay, senders[k][0], senders[k][1], sel);
    deliver(notify, senders[k][0], senders[k][1], note);
    out.effects[k] = { toChat: POSTED.filter((p) => p[0] === 'chat').map((p) => p[1]), notes: NOTES.slice() };
  });
} else if (MODE === 'overwrite') {
  // after the scripts, what they left for later and the exercise: a script on the page tries to replace the check with
  // one that admits every sender, in each way a script can. Each attempt starts from the check as the boot left it (one
  // that replaced it on an unlocked page is undone first; on a locked page there is nothing to undo), then every listener
  // is handed a message from each refused sender and from a pane, and the check a script reads is compared with the
  // function the boot left
  const ADOPTED = target.__rompPaneSourceOk, ORIG = Object.getOwnPropertyDescriptor(target, CHECK);
  const same = (a, b) => !!a && !!b && ['value', 'get', 'set', 'writable', 'configurable', 'enumerable'].every((k) => a[k] === b[k]);
  const ANY = 'function(e){return true;}';
  const ATTEMPTS = {
    'an assignment on window': "window.__rompPaneSourceOk=" + ANY + ";",
    'an assignment by a computed name': "window['__romp'+'PaneSourceOk']=" + ANY + ";",
    'an assignment to the bare global': "__rompPaneSourceOk=" + ANY + ";",
    'an assignment on self': "self.__rompPaneSourceOk=" + ANY + ";",
    'an assignment in strict mode': "'use strict';window.__rompPaneSourceOk=" + ANY + ";",
    'a var declaration': "var __rompPaneSourceOk=" + ANY + ";",
    'Reflect.set': "Reflect.set(window,'__rompPaneSourceOk'," + ANY + ");",
    'Object.assign': "Object.assign(window,{__rompPaneSourceOk:" + ANY + "});",
    'defineProperty with a value': "Object.defineProperty(window,'__rompPaneSourceOk',{value:" + ANY + "});",
    'defineProperty with a getter': "Object.defineProperty(window,'__rompPaneSourceOk',{get:function(){return " + ANY + ";}});",
    'a delete, then an assignment': "delete window.__rompPaneSourceOk;window.__rompPaneSourceOk=" + ANY + ";",
    'an unlock, then an assignment': "Object.defineProperty(window,'__rompPaneSourceOk',{writable:true,configurable:true});" +
                                     "window.__rompPaneSourceOk=" + ANY + ";",
  };
  out.attempts = {};
  for (const name of Object.keys(ATTEMPTS)) {
    const now = Object.getOwnPropertyDescriptor(target, CHECK);
    if (!same(now, ORIG) && (!now || now.configurable)) Object.defineProperty(target, CHECK, ORIG);
    let threw = null;
    try { vm.runInContext(ATTEMPTS[name], ctx, { timeout: 2000 }); } catch (x) { threw = String(x && x.message || x).slice(0, 120); }
    const seen = vm.runInContext('window.__rompPaneSourceOk', ctx);
    let refused = 0, pane = 0;
    for (const l of LISTENERS) {
      for (const k of REFUSED_SENDERS) refused += deliver(l, SENDERS[k][0], SENDERS[k][1], { romp: 'none-of-yours' }).reads;
      pane += deliver(l, CHAT, ORIGIN, { romp: 'none-of-yours' }).reads;
    }
    out.attempts[name] = { threw: threw !== null, kept: seen === ADOPTED, refusedReads: refused, paneReads: pane };
  }
} else if (MODE === 'trap') {
  // the global's define trap, reached from a page's script through vm and driven directly: a define that carries a value
  // is a write, one that carries an accessor is a write, and one that changes attributes alone writes nothing and leaves
  // the value in place (vm hands it over with an undefined value; driven directly, it carries none)
  vm.runInContext("window.__rompPaneSourceOk=function(e){return false;};", ctx);
  vm.runInContext("Object.defineProperty(window,'__rompPaneSourceOk',{writable:true,enumerable:true});", ctx);
  Reflect.defineProperty(G, CHECK, { configurable: true });
  const kept = textOf(target.__rompPaneSourceOk);
  vm.runInContext("Object.defineProperty(window,'__rompPaneSourceOk',{get:function(){return function(e){return true;};}});", ctx);
  out.trap = { kept, writes: ASSIGNED.map((v) => (typeof v === 'function' ? textOf(v)
                                                  : (v && typeof v.get === 'function' ? 'an accessor' : 'another write: ' + String(v)))) };
  // the lock's define without its try, on a property of another name holding a function: it throws here (the proxy's
  // invariant, see the comment at G), and the property is locked with its value all the same
  vm.runInContext("window.__b5lockProbe=function(e){return false;};", ctx);
  let lockThrew = null;
  try { vm.runInContext("Object.defineProperty(window,'__b5lockProbe',{writable:false,configurable:false});", ctx); }
  catch (x) { lockThrew = (x && x.constructor && x.constructor.name) + ': ' + String(x && x.message || x).slice(0, 160); }
  const pd = Object.getOwnPropertyDescriptor(target, '__b5lockProbe');
  out.trap.bareLock = { threw: lockThrew, writable: pd.writable, configurable: pd.configurable, value: textOf(pd.value) };
}
out.inEffect = [...IN_EFFECT];
process.stdout.write('\n' + JSON.stringify(out));
})().catch((x) => { process.stderr.write(String(x && x.stack || x)); process.exit(1); });
"""


def _run_landing(mode):
    return _run_scripts(_inline_scripts(_served_shell()), mode)


def _without(html, text):
    """`html` with `text`, which it holds once, taken out."""
    assert html.count(text) == 1, "the page holds it once"
    return html.replace(text, "", 1)


def _without_lock(html):
    """The shell with the fork's lock line taken out: what the page would be without it."""
    return _without(html, LOCK + "\n")


def _without_check(html):
    """The shell with the adopted definition and the lock taken out: a page on which no script defines the check."""
    i = html.index(REGION_HEAD)
    return _without(html, html[i:html.index(REGION_TAIL, i) + len(REGION_TAIL)] + "\n" + LOCK + "\n")


def _run_scripts(bodies, mode):
    """Run `bodies` (a page's inline scripts, in order) in the stand-in browser under `mode`: reads (the exercise, then each
    listener handed each sender's message), nocheck (each listener handed each sender's message with the check held as
    undefined, no exercise; for a page that does not define it), effects (two arms' visible effects, no exercise), census
    (the exercise and nothing delivered after it), overwrite (the exercise, then each way a script can try to replace the
    check, and every listener handed each sender's message after each) or trap (the global's define trap alone)."""
    node = shutil.which("node")
    if not node:
        raise unittest.SkipTest("node not installed")
    fx = tempfile.mkdtemp()
    try:
        scripts = os.path.join(fx, "scripts.json")
        with open(scripts, "w") as f:
            json.dump(bodies, f)
        path = os.path.join(fx, "run.js")
        with open(path, "w") as f:
            f.write(_HARNESS)
        r = subprocess.run([node, path], capture_output=True, text=True, timeout=120,
                           env=dict(os.environ, ROMP_TEST_SCRIPTS=scripts, ROMP_TEST_MODE=mode))
    finally:
        shutil.rmtree(fx, ignore_errors=True)
    if r.returncode != 0:
        raise AssertionError("node failed:\n" + r.stderr[-3000:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def _name_of(src):
    names = [n for n, phrase in LISTENERS.items() if phrase in src]
    return names[0] if len(names) == 1 else "unnamed listener: " + src[:120]


class ShellListenersExecuted(unittest.TestCase):
    """The served shell's inline scripts, run: no listener reads a message from a sender that is not one of its panes.
    The /dist bundles the page loads are not run here: the palette bundle's two window listeners are run from every
    sender by ui/webview/foreign-sender-listeners.test.ts, and in real browsers by tests/test_palette_senders_browser.py.

    The run drives these roads before any message is tested: the scripts themselves; every callback they queue (a timer,
    an animation frame, an idle callback, a microtask, a load or pageshow listener), each once; every other listener or
    handler they register on the window, the document, a frame or an element, once per distinct text, with a stand-in
    event of its type; every function they hand to a stand-in (an observer's callback, a fetch's then), once per distinct
    text; and, from each pane, every word a window message listener's text compares a field of with a string literal
    (m.romp==='settings'); in rounds until none is left. So a write of the check in any spelling that lands on the window
    (window[...]=, a bare global, a defineProperty), or a registration through the window's own addEventListener however
    it is reached, is caught on those roads (test_the_exercise_reaches_a_write_planted_on_each_road, run on the shell
    without its lock, where such a write lands; on the shell as served the lock refuses it). Not run: a road behind a
    condition the stand-in does not meet (location.protocol === 'https:', a user agent, a stored setting, a key its
    stand-in event lacks), an arm keyed some other way than such a comparison (a switch, a lookup table), and a
    registration through another object's method (EventTarget.prototype.addEventListener.call). A registration there is
    caught only when its text names addEventListener (KernelListenerCensus); under a computed name, no test catches it. A
    write of the check there is refused by the lock (CheckLocked)."""

    REFUSED = ("opener", "openerSameOrigin", "sandboxedFrame", "otherOriginFrame", "strayWindow", "nestedSandboxed",
               "nestedSameOrigin", "nestedParentReplaced", "popup", "popupSameOrigin", "shellItself", "dispatch",
               "sourcelessElsewhere", "sourcelessOpaque")

    @classmethod
    def setUpClass(cls):
        cls.run_ = _run_landing("reads")

    def test_the_stand_in_windows_carry_the_edges_a_browser_gives_them(self):
        # the refused senders above are refused over windows related to the shell as a browser relates them, read the way
        # a script on the shell reads them: so a check that took a window in the shell's frames, one sharing its top, one
        # whose parent reads as the shell, or one the shell opened, for a pane, hears a sender here (a sandboxed frame of
        # the shell, a frame nested in a pane, the window that replaced its parent, a popup) and fails the reads test
        self.assertEqual(self.run_["edges"], {
            "shellIsItsOwnParentAndTop": True, "framesAreTheFourIframes": True, "iframesAreItsChildren": True,
            "nestedShareItsTopUnderThePane": True, "parentReplacedReadsAsItsChild": True, "popupsItOpened": True,
            "itsOpener": True})

    def test_every_listener_registers_with_the_check_already_defined(self):
        got = sorted(_name_of(l["src"]) for l in self.run_["listeners"])
        self.assertEqual(got, sorted(LISTENERS), "every named listener registered (script errors: %r)" % self.run_["errors"])
        for l in self.run_["listeners"]:
            with self.subTest(listener=_name_of(l["src"])):
                self.assertTrue(l["checkDefined"], "the boot script defines the check before any listener registers")

    def test_no_listener_reads_a_message_from_a_sender_that_is_not_a_pane(self):
        self.assertEqual(len(self.run_["reads"]), len(LISTENERS))
        for l, reads in zip(self.run_["listeners"], self.run_["reads"]):
            name = _name_of(l["src"])
            for sender in self.REFUSED:
                with self.subTest(listener=name, sender=sender):
                    self.assertEqual(reads[sender], 0, "%s read a message from %s" % (name, sender))
            with self.subTest(listener=name, sender="pane"):
                self.assertGreater(reads["pane"], 0, "%s still hears its panes" % name)

    def test_the_check_every_listener_reads_is_the_adopted_function(self):
        # whatever spelling a second assignment used (window['...']=, a bare global, a defineProperty), it lands on the
        # page's global, if it runs on a road the stand-in drives (at load; from a timer, animation frame, idle callback,
        # microtask or load listener the scripts left for later; from any other listener or handler they registered,
        # handed a stand-in event; from a callback they handed a stand-in; in a message listener's arm, reached by a word
        # it compares against, from a pane): the scripts assign the check once, the adopted function, and it is the
        # function in effect at every delivery, so a later wrapper that widens it for some senders cannot stand in for it.
        # A write behind a condition the stand-in does not meet is not run here; the lock refuses it (CheckLocked). The
        # lock's own define carries no new value, so it is no second assignment
        html = _served_shell()
        i = html.index(REGION_HEAD)
        region = html[i:html.index(REGION_TAIL, i) + len(REGION_TAIL)]
        fn = region[len("window.__rompPaneSourceOk="):-1]
        self.assertTrue(fn.startswith("function(e){") and fn.endswith("}"), "the adopted region assigns one function expression")
        self.assertEqual(self.run_["assigns"], [fn], "the scripts assign the check once, and assign the adopted function")
        self.assertEqual(self.run_["afterBoot"], fn, "after the scripts run, the check is the adopted function")
        self.assertEqual(self.run_["inEffect"], [fn], "at every delivery, the check is the adopted function")

    def test_the_run_includes_what_the_page_leaves_for_later(self):
        # the timers, animation frames, microtasks and load listeners the scripts queue all ran before the first
        # delivery, so a write the page defers to one of them is what the check tests above read
        late = self.run_["late"]
        self.assertGreater(late["ran"], 0, "the scripts queue callbacks for later, and the harness ran them: %r" % late)
        self.assertEqual(late["left"], 0, "every callback queued, one queued by another included, ran: %r" % late)

    def test_the_run_includes_every_other_listener_handler_callback_and_arm(self):
        # and before it, the exercise: every other listener and handler the scripts registered, every callback they handed
        # to a stand-in, and every word a message listener's arms compare against, from each pane, until none was left
        ex = self.run_["exercise"]
        self.assertGreater(ex["ran"], 0, "the scripts register listeners and handlers, and the harness ran them: %r" % ex)
        self.assertGreater(ex["words"], 0, "the listeners' arms were reached from a pane: %r" % ex)
        self.assertEqual(ex["left"], 0, "every listener, handler, callback and message listener was exercised: %r" % ex)

    def test_no_script_assigns_an_onmessage_handler_to_the_window(self):
        # an onmessage handler is a window message listener that addEventListener never sees. However a script spells the
        # write, on the roads the stand-in drives it is heard: on the window by any name (window.onmessage=, a computed
        # member, a bare global, top, a local holding it, a define), on document.defaultView, on document.body, whose
        # handler is its window's, and on window.frames or a frame's window; an onmessageerror handler the same
        # (test_the_stand_in_hears_a_handler_written_on_every_road_to_a_window plants each)
        self.assertEqual(self.run_["onmessage"], [], "an onmessage or onmessageerror handler on the shell's window, its body or a frame's window")

    # Every road to a window's onmessage handler the stand-in hears, each planted as one more script after the shell's:
    # the window by its own name, as the bare global and by other names (frames, window.frames, self.frames, top,
    # parent, a local holding it), a document's window (document.defaultView, and one held in a local), the body
    # element, whose handler is its window's, and a frame's window (frames[0], window[0], a pane iframe's
    # contentWindow), by a plain write, under a computed name, by a define or by Object.assign; and an onmessageerror
    # handler. The stand-in hears the body only as document.body itself: a body reached any other way (a query for it, a
    # frame's document, a contentDocument, document.documentElement.lastElementChild) is a stub, so a write on it is not
    # heard here. KernelListenerCensus's text census reads such a write when it spells onmessage
    # (document.querySelector('body').onmessage=), and under a computed name no census here reads it. A write on the
    # html element, which reflects no window handler, is heard nowhere (the control).
    HANDLER_ROADS = {
        "the window by its name": "window.onmessage=function(e){go(e.data)};",
        "the window by its name, under a computed name": "window['on'+'message']=function(e){go(e.data)};",
        "the bare global": "onmessage=function(e){go(e.data)};",
        "frames": "frames.onmessage=function(e){go(e.data)};",
        "window.frames": "window.frames.onmessage=function(e){go(e.data)};",
        "self.frames": "self.frames.onmessage=function(e){go(e.data)};",
        "document.defaultView": "document.defaultView.onmessage=function(e){go(e.data)};",
        "document.body": "document.body.onmessage=function(e){go(e.data)};",
        "frames, under a computed name": "frames['on'+'message']=function(e){go(e.data)};",
        "document.defaultView, under a computed name": "document.defaultView['on'+'message']=function(e){go(e.data)};",
        "document.body, under a computed name": "document.body['on'+'message']=function(e){go(e.data)};",
        "a local holding the window": "var w0=window;w0.onmessage=function(e){go(e.data)};",
        "top": "top.onmessage=function(e){go(e.data)};",
        "parent, under a computed name": "parent['on'+'message']=function(e){go(e.data)};",
        "a local holding document.defaultView, under a computed name":
            "var dv=document.defaultView;dv['on'+'message']=function(e){go(e.data)};",
        "a local holding the document, its body under a computed name": "var dd=document;dd.body['on'+'message']=function(e){go(e.data)};",
        "a frame's window by index, under a computed name": "frames[0]['on'+'message']=function(e){go(e.data)};",
        "window[0]": "window[0].onmessage=function(e){go(e.data)};",
        "a pane iframe's contentWindow, under a computed name":
            "document.getElementById('f-chat').contentWindow['on'+'message']=function(e){go(e.data)};",
        "the window, by a define": "Object.defineProperty(window,'on'+'message',{value:function(e){go(e.data)}});",
        "frames, by a define": "Object.defineProperty(frames,'on'+'message',{value:function(e){go(e.data)}});",
        "document.body, by a define": "Object.defineProperty(document.body,'on'+'message',{value:function(e){go(e.data)}});",
        "document.body, by Reflect.defineProperty": "Reflect.defineProperty(document.body,'on'+'message',{value:function(e){go(e.data)}});",
        "document.body, by Object.assign": "Object.assign(document.body,{['on'+'message']:function(e){go(e.data)}});",
        "the window's onmessageerror": "window.onmessageerror=function(e){go(e.data)};",
        "document.body's onmessageerror, under a computed name": "document.body['onmessage'+'error']=function(e){go(e.data)};",
        "a frame's window's onmessageerror": "frames[1].onmessageerror=function(e){go(e.data)};",
    }

    def test_the_stand_in_hears_a_handler_written_on_every_road_to_a_window(self):
        base = _inline_scripts(_served_shell())
        for road, plant in self.HANDLER_ROADS.items():
            with self.subTest(road=road):
                run = _run_scripts(base + [plant], "census")
                self.assertEqual([e for e in run["errors"] if e[0] == len(base)], [], "the planted script ran")
                # heard at least once (vm can report one write as more than one trap), and nothing but the planted handler
                self.assertEqual(sorted(set(run["onmessage"])), ["function(e){go(e.data)}"], "the stand-in heard the handler")
        control = _run_scripts(base + ["document.documentElement['on'+'message']=function(e){go(e.data)};"], "census")
        self.assertEqual(control["onmessage"], [], "the html element reflects no window handler, and none is heard")

    # A write of the check under a computed name, planted on each road the exercise drives. On the shell without its lock,
    # each is heard and replaces the adopted function before the listeners are tested (what the tests above would then
    # red on), so the exercise reaches every road. On the shell as served, each road runs (the plant's counter says so)
    # and the lock leaves the adopted function in place (CheckLocked tries every other spelling)
    PLANT_WRITE = "window['__romp'+'PaneSourceOk']=function(e){return !!e;};"
    PLANT_REACH = "window.__b5reached=(window.__b5reached||0)+1;"
    PLANTS = {
        "a window listener (resize)": "window.addEventListener('resize',function(){WRITE});",
        "a document listener (visibilitychange)": "document.addEventListener('visibilitychange',function(){WRITE});",
        "an element's listener (click)": "document.getElementById('none').addEventListener('click',function(){WRITE});",
        "a handler property on the window (onstorage)": "window.onstorage=function(){WRITE};",
        "a fetch's then": "fetch('/version').then(function(r){WRITE});",
        "an observer's callback": "new MutationObserver(function(){WRITE});",
        "a message listener's arm, after the check": "window.addEventListener('message',function(e){" + GATE +
            "var m=e.data;if(m&&m.romp==='planted'){WRITE}});",
        "a timer set by a listener": "window.addEventListener('focus',function(){setTimeout(function(){WRITE},0);});",
    }

    def test_the_exercise_reaches_a_write_planted_on_each_road(self):
        fn = self.run_["assigns"][0]
        unlocked = _inline_scripts(_without_lock(_served_shell()))
        for road, plant in self.PLANTS.items():
            with self.subTest(road=road):
                run = _run_scripts(unlocked + [plant.replace("WRITE", self.PLANT_WRITE)], "reads")
                self.assertEqual(run["assigns"][0], fn)
                # heard once per time its road ran (an arm is reached by more than one word, from each pane)
                self.assertGreaterEqual(len(run["assigns"]), 2, "the planted write was heard")
                self.assertNotEqual(run["afterBoot"], fn, "and replaced the check before the listeners were tested")
                self.assertNotEqual(run["inEffect"], [fn], "so a delivery read a check that is not the adopted function")

    def test_with_the_lock_a_write_planted_on_each_road_leaves_the_adopted_function(self):
        fn = self.run_["assigns"][0]
        base = _inline_scripts(_served_shell())
        for road, plant in self.PLANTS.items():
            with self.subTest(road=road):
                run = _run_scripts(base + [plant.replace("WRITE", self.PLANT_REACH + self.PLANT_WRITE)], "reads")
                self.assertGreater(run["reached"], 0, "the planted road ran")
                self.assertEqual(run["assigns"], [fn], "no write but the adopted definition landed")
                self.assertEqual(run["afterBoot"], fn)
                self.assertEqual(run["inEffect"], [fn], "every delivery read the adopted function")

    def test_a_listener_registered_from_a_later_road_is_counted(self):
        run = _run_scripts(_inline_scripts(_served_shell()) + [
            "window.addEventListener('resize',function(){window['add'+'EventListener']('message',function(e){});});"], "reads")
        self.assertEqual(len(run["listeners"]), len(LISTENERS) + 1, "the listener the resize handler registered is counted")
        self.assertEqual([n for n in (_name_of(l["src"]) for l in run["listeners"]) if n.startswith("unnamed listener")],
                         ["unnamed listener: function(e){}"])

    def test_a_messageerror_listener_is_counted_as_a_window_message_listener(self):
        # a messageerror event carries the sender's origin and source as a message does, and a sender causes one by posting
        # what the page cannot deserialize: the stand-in counts a listener for it, under any name, with the page's message
        # listeners, so the census tests above fail on it
        run = _run_scripts(_inline_scripts(_served_shell()) + ["window['add'+'EventListener']('messageerror',function(e){});"], "reads")
        self.assertEqual(len(run["listeners"]), len(LISTENERS) + 1, "the messageerror listener is counted")
        self.assertEqual([n for n in (_name_of(l["src"]) for l in run["listeners"]) if n.startswith("unnamed listener")],
                         ["unnamed listener: function(e){}"])

    def test_without_the_check_no_listener_reads_anything(self):
        run = _run_scripts(_inline_scripts(_without_check(_served_shell())), "nocheck")
        self.assertEqual(len(run["reads"]), len(LISTENERS))
        for l, reads in zip(run["listeners"], run["reads"]):
            with self.subTest(listener=_name_of(l["src"])):
                self.assertEqual(sum(reads.values()), 0, "fail-closed: no check, no message, not even a pane's")


class ServedPagesExecuted(unittest.TestCase):
    """Every other page the kernel serves, its inline scripts run in the same stand-in, the exercise included: the window
    message listeners each registers, by whatever spelling reaches the window's addEventListener, are its listed kinds
    (PAGE_LISTENERS); none writes an onmessage or onmessageerror handler on any road the stand-in hears (the window by any
    name, document.defaultView, document.body, window.frames or a frame's window); and none writes the shell's check,
    under any name, on its window or its parent (in the stand-in they are one window). The shell's run is ShellListenersExecuted's; /sw.js
    runs in a worker, where no window posts. The roads run and the residual are ShellListenersExecuted's."""

    # a registered listener's text opens with its kind's head from the function on
    HEADS = {name: head[head.index(",") + 1:] for name, (receiver, head, _n) in KERNEL_LISTENER_KINDS.items()
             if receiver == "window."}

    @classmethod
    def setUpClass(cls):
        cls.runs = {name: _run_scripts(_inline_scripts(page), "census")
                    for name, page in _served_pages().items() if name not in ("/", "/sw.js")}

    def test_each_page_registers_only_its_listed_listeners(self):
        for name, run in self.runs.items():
            with self.subTest(page=name):
                got = {}
                for l in run["listeners"]:
                    kind = next((k for k, h in self.HEADS.items() if l["src"].startswith(h)), "unlisted: " + l["src"][:160])
                    got[kind] = got.get(kind, 0) + 1
                self.assertEqual(got, PAGE_LISTENERS[name], "script errors: %r" % run["errors"])
                self.assertEqual(run["onmessage"], [], "an onmessage or onmessageerror handler on the page's window, its body or a frame's window")
                # the stand-in's window is its own parent and top, so a write of the shell's check through
                # window.parent, under any name, lands where the harness hears it
                self.assertEqual(run["assigns"], [], "a pane page writes the shell's check")

    def test_each_run_went_through_the_page_and_what_it_leaves(self):
        for name, run in self.runs.items():
            with self.subTest(page=name):
                self.assertEqual(run["late"]["left"], 0, "every callback the page queued ran: %r" % run["late"])
                self.assertEqual(run["exercise"]["left"], 0, "every listener, handler and handed-over callback ran: %r"
                                 % run["exercise"])
        for name in ("/chat", "/feed", "/timeline"):
            with self.subTest(page=name):
                self.assertGreater(self.runs[name]["exercise"]["ran"], 0, "the pane page's handlers ran")


class ShellArmsExecuted(unittest.TestCase):
    """Two arms whose effect is visible: the relay forwards a Files-pane selection into the chat's composer, and a
    pane's notify lands in the Log; from any other sender neither happens."""

    @classmethod
    def setUpClass(cls):
        cls.effects = _run_landing("effects")["effects"]

    def test_the_relay_forwards_an_editor_selection_only_from_a_pane(self):
        sel = {"type": "editorSelection", "text": "a quoted passage", "sid": "11111111-2222-3333-4444-555555555555"}
        self.assertEqual(self.effects["pane"]["toChat"], [sel], "the Files pane's selection reaches the chat once")
        for sender in ShellListenersExecuted.REFUSED:
            with self.subTest(sender=sender):
                self.assertEqual(self.effects[sender]["toChat"], [], "nothing forwarded into the chat from " + sender)

    def test_a_log_line_is_planted_only_by_a_pane(self):
        self.assertEqual(self.effects["pane"]["notes"], [["info", "a planted line"]])
        for sender in ShellListenersExecuted.REFUSED:
            with self.subTest(sender=sender):
                self.assertEqual(self.effects[sender]["notes"], [], "no Log line from " + sender)


class CheckLocked(unittest.TestCase):
    """The fork's lock (2026-09-26), the line right after the adopted definition: once the boot script has run, the
    check's property is read-only and non-configurable and holds the adopted function, so no later script replaces,
    redefines or deletes it, however it spells the attempt, and every listener still reads the adopted function after
    each. The lock is outside the adopted region (AdoptedCheck); a fold that takes the project's side of
    _LANDING_BOOT_JS keeps it. The same attempts on the shell without its lock each replace the check, so the harness
    can see a replacement when one lands. A script that runs BEFORE the boot script is not refused by the lock: every
    script ahead of it on the shell as served (the sign-in seed and the page-key script _send puts first in the head, then
    the shell's own earlier scripts) is run here, and the descriptor read after boot would show what they left."""

    ATTEMPTS = ("an assignment on window", "an assignment by a computed name", "an assignment to the bare global",
                "an assignment on self", "an assignment in strict mode", "a var declaration", "Reflect.set", "Object.assign",
                "defineProperty with a value", "defineProperty with a getter", "a delete, then an assignment",
                "an unlock, then an assignment")

    @classmethod
    def setUpClass(cls):
        # the served shell, as it is: the pins below read this run alone, so they fail on their own assertions when the
        # lock is missing or weakened (the contrast builds its page in its own test)
        html = _served_shell()
        cls.locked = _run_scripts(_inline_scripts(html), "overwrite")
        i = html.index(REGION_HEAD)
        cls.fn = html[i:html.index(REGION_TAIL, i) + len(REGION_TAIL)][len("window.__rompPaneSourceOk="):-1]

    def test_after_boot_the_check_is_read_only_non_configurable_and_the_adopted_function(self):
        self.assertEqual(self.locked["errors"], [], "the shell's scripts ran")
        self.assertEqual(self.locked["descriptor"], {"writable": False, "configurable": False, "enumerable": True,
                                                     "value": self.fn, "accessor": False})

    def test_no_attempt_to_replace_the_check_leaves_anything_but_the_adopted_function(self):
        got = self.locked["attempts"]
        self.assertEqual(sorted(got), sorted(self.ATTEMPTS), "every attempt ran")
        for name in self.ATTEMPTS:
            with self.subTest(attempt=name):
                self.assertTrue(got[name]["kept"], "the check a script reads is still the adopted function")
                self.assertEqual(got[name]["refusedReads"], 0, "no listener reads a message from a sender that is not a pane")
                self.assertGreater(got[name]["paneReads"], 0, "and the listeners still hear their panes")
                # a browser refuses some of these with a TypeError and the rest without a word; node's vm global drops
                # a strict-mode write without one, so whether it threw is not read here, only that nothing landed
        self.assertEqual(self.locked["inEffect"], [self.fn], "every delivery read the adopted function")

    def test_without_the_lock_each_attempt_replaces_the_check(self):
        # the contrast: the same page less its lock line. Each attempt runs without an error and lands, and the listeners
        # then read messages from senders the adopted check refuses: so every attempt above is a working replacement,
        # and a replacement that lands is one these tests see
        unlocked = _run_scripts(_inline_scripts(_without_lock(_served_shell())), "overwrite")
        self.assertEqual(unlocked["descriptor"], {"writable": True, "configurable": True, "enumerable": True,
                                                  "value": self.fn, "accessor": False})
        got = unlocked["attempts"]
        self.assertEqual(sorted(got), sorted(self.ATTEMPTS))
        for name in self.ATTEMPTS:
            with self.subTest(attempt=name):
                self.assertFalse(got[name]["threw"], "nothing refused it")
                self.assertFalse(got[name]["kept"], "it replaced the check")
                self.assertGreater(got[name]["refusedReads"], 0, "and a listener read a message the adopted check refuses")

    def test_the_harness_counts_a_define_as_a_write_only_when_it_carries_a_value_or_an_accessor(self):
        # the lock's define changes attributes alone ({writable:false,configurable:false}): no write, and the check keeps
        # its value, so a page that locks the check still assigns it once and its listeners still read the adopted
        # function (ShellListenersExecuted). vm fills a missing value in as undefined before the trap sees it
        trap = _run_scripts([], "trap")["trap"]
        self.assertEqual({k: trap[k] for k in ("kept", "writes")}, {"kept": "function(e){return false;}",
                                                                    "writes": ["function(e){return false;}", "an accessor"]})

    def test_in_this_harness_the_lock_define_throws_and_still_locks_so_its_try_is_what_lets_the_boot_run_on(self):
        # the harness quirk the comment at the stand-in global describes, pinned so the comment cannot go stale: run bare,
        # the lock's define throws a TypeError here (a browser's does not), and the property is locked with its value
        bare = _run_scripts([], "trap")["trap"]["bareLock"]
        self.assertIsNotNone(bare["threw"], "the define throws in this harness")
        self.assertTrue(bare["threw"].startswith("TypeError: "), bare["threw"])
        self.assertIn("defineProperty", bare["threw"], "the proxy's defineProperty invariant, not a script error")
        self.assertEqual({k: bare[k] for k in ("writable", "configurable", "value")},
                         {"writable": False, "configurable": False, "value": "function(e){return false;}"},
                         "locked, and holding the function it held")
        self.assertIn("try{", LOCK, "the served lock line carries the try that absorbs it")


# The adopted check alone, over stand-in windows: the truth table of what it admits. The windows carry the edges a
# browser gives them: the shell's page is the top of its tab (its own parent and top); its iframes (a pane, a pane marked
# data-protocol=none, a sandboxed frame) have it as parent and top and are listed in window.frames, which is the window
# itself with a length and an index per frame; a frame nested in the pane has the pane as parent and the shell as top; a
# window on the shell's location.origin nested in the pane can replace its own window.parent with the shell; a window
# the shell opened has it as opener, and the page that opened the shell is its opener; the stray window has no edge to
# the shell.
_CHECK_HARNESS = r"""
'use strict';
const ORIGIN = 'http://127.0.0.1:7777', ELSEWHERE = 'https://elsewhere.example';
global.window = global;
global.parent = global;
global.top = global;
const pane = { n: 'pane', parent: window, top: window }, urlPane = { n: 'urlPane', parent: window, top: window },
      sandboxed = { n: 'sandboxed', parent: window, top: window }, nested = { n: 'nested', parent: pane, top: window },
      parentReplaced = { n: 'parentReplaced', parent: window, top: window }, popup = { n: 'popup', opener: window },
      opener = { n: 'opener' }, stray = { n: 'stray' };
global.opener = opener;
let FRAMES = [{ contentWindow: pane, getAttribute: () => null },
              { contentWindow: urlPane, getAttribute: (k) => (k === 'data-protocol' ? 'none' : null) },
              { contentWindow: sandboxed, getAttribute: () => null }];
global.frames = global;
global.length = FRAMES.length;
FRAMES.forEach((f, i) => { global[i] = f.contentWindow; });
let THROW = false;
global.location = { origin: ORIGIN };
global.document = { querySelectorAll: (s) => { if (THROW) throw new Error('detached'); return s === 'iframe' ? FRAMES : []; } };
REGION
const ok = window.__rompPaneSourceOk;
const rows = {
  pane: ok({ source: pane, origin: ORIGIN }),
  paneOtherOrigin: ok({ source: pane, origin: 'https://elsewhere.example' }),
  paneOpaqueOrigin: ok({ source: pane, origin: 'null' }),
  urlPaneMarkedNone: ok({ source: urlPane, origin: ORIGIN }),
  sandboxedFrame: ok({ source: sandboxed, origin: 'null' }),
  nestedFrame: ok({ source: nested, origin: ORIGIN }),
  nestedFrameOpaqueOrigin: ok({ source: nested, origin: 'null' }),
  parentReplaced: ok({ source: parentReplaced, origin: ORIGIN }),
  popup: ok({ source: popup, origin: ELSEWHERE }),
  popupSameOrigin: ok({ source: popup, origin: ORIGIN }),
  opener: ok({ source: opener, origin: ELSEWHERE }),
  openerSameOrigin: ok({ source: opener, origin: ORIGIN }),
  strayWindow: ok({ source: stray, origin: ORIGIN }),
  itself: ok({ source: window, origin: ORIGIN }),
  noSource: ok({ source: null, origin: ORIGIN }),
  noSourceNoOrigin: ok({ source: null, origin: '' }),
  noSourceOpaqueOrigin: ok({ source: null, origin: 'null' }),
  noEvent: ok(null),
};
THROW = true; rows.throws = ok({ source: pane, origin: ORIGIN });
// the edges, read as the check would read them
const inFrames = (x) => Array.prototype.indexOf.call(window.frames, x) >= 0;
rows.edges = { framesListTheIframes: window.length === 3 && inFrames(pane) && inFrames(urlPane) && inFrames(sandboxed),
               nestedSharesTheTop: nested.top === window.top && nested.parent === pane && !inFrames(nested),
               parentReplacedReadsAsAChild: parentReplaced.parent === window && !inFrames(parentReplaced),
               popupOpenedByIt: popup.opener === window, itsOpener: window.opener === opener,
               ownParentAndTop: window.parent === window && window.top === window };
process.stdout.write(JSON.stringify(rows));
"""


class AdoptedCheckExecuted(unittest.TestCase):
    """The adopted lines, run: true only for an iframe of this document, posting on its location.origin, that is not
    marked data-protocol=none; false for every other sender (a sandboxed iframe of the shell, listed in its frames; a frame
    nested in a pane, which shares the shell's top; a window whose parent reads as the shell but that no iframe holds; a
    window the shell opened; the page that opened it, on another origin or on the shell's location.origin) and when the
    frame walk throws."""

    def test_the_truth_table(self):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("node not installed")
        html = _served_shell()
        i = html.index(REGION_HEAD)
        region = html[i:html.index(REGION_TAIL, i) + len(REGION_TAIL)]
        fx = tempfile.mkdtemp()
        try:
            path = os.path.join(fx, "check.js")
            with open(path, "w") as f:
                f.write(_CHECK_HARNESS.replace("REGION", region))
            r = subprocess.run([node, path], capture_output=True, text=True, timeout=60)
        finally:
            shutil.rmtree(fx, ignore_errors=True)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        rows = json.loads(r.stdout)
        self.assertEqual(rows.pop("edges"), {
            "framesListTheIframes": True, "nestedSharesTheTop": True, "parentReplacedReadsAsAChild": True,
            "popupOpenedByIt": True, "itsOpener": True, "ownParentAndTop": True,
        }, "the stand-in windows carry the edges a browser gives them")
        self.assertEqual(rows, {
            "pane": True, "paneOtherOrigin": False, "paneOpaqueOrigin": False, "urlPaneMarkedNone": False,
            "sandboxedFrame": False, "nestedFrame": False, "nestedFrameOpaqueOrigin": False, "parentReplaced": False,
            "popup": False, "popupSameOrigin": False, "opener": False, "openerSameOrigin": False, "strayWindow": False,
            "itself": False, "noSource": False, "noSourceNoOrigin": False, "noSourceOpaqueOrigin": False,
            "noEvent": False, "throws": False,
        })


if __name__ == "__main__":
    unittest.main()
