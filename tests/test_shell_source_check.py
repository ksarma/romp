#!/usr/bin/env python3
"""The dashboard shell's window message listeners act only on a message from one of its own panes (2026-09-25).

The shell page (kernel.py _landing) runs about a dozen inline listeners for its panes' words: the boot splash's
ready, the Log's notify and wsState, the settings relay (openSettings, viewFile, editorSelection, ...), the usage
bars, the split columns' drags. A window message listener hears every window that can post to the page, and the
only legitimate senders of these words are the shell's own pane iframes. Each listener reads the shell's one source
check, window.__rompPaneSourceOk, FAIL-CLOSED as its first statement: a message counts only when its immediate
source is a same-origin iframe of the shell.

The check is ADOPTED from the romp project's repository, github.com/romp-on/romp, at commit
f4a57200894ede72a4d4469570490aa64fbf9e94 (kernel/kernel.py there, lines 65382-65384, the opening lines of
_LANDING_BOOT_JS), byte for byte. AdoptedCheck pins those three lines by the sha256 of their text, so an edit inside
them reds; recompute the recorded digest from that commit, never from the fork's copy:

    git show f4a57200894ede72a4d4469570490aa64fbf9e94:kernel/kernel.py | sed -n '65382,65384p' | head -c -1 | sha256sum

NoOtherWriter holds that nothing else names the check: no file in the tree but the kernel, and in the kernel's code
nothing but the adopted lines and the gates. The rest runs the served landing: the census of every window message
listener in its inline scripts (addEventListener, and an onmessage handler on the window), and node executing those
scripts in a stand-in browser, then every callback they leave for later (timers, animation frames, microtasks, load
listeners), then forging a message from each sender the shell must refuse (a page that opened it, a sandboxed frame,
a window it does not hold, itself, its own dispatch, a sourceless post with the opaque origin) and from a pane, and
reading which function the check is when each message is delivered. Synthetic only: no session data, a loopback
origin.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
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

# The read every shell listener opens with, spelled as the project spells it (so a fold's lines match).
GATE = "if(!window.__rompPaneSourceOk||!window.__rompPaneSourceOk(e))return;"

# Every window message listener the shell runs, by a phrase only its own body carries. A listener added to the
# shell must join this list (the census below fails until it does), which is where its senders get decided.
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

# An onmessage handler assigned to the window: window., self. or globalThis. (or a computed ['onmessage'] member of
# one of them), or a bare onmessage with no receiver. A plain `=` only: == and === compare.
_ONMESSAGE = re.compile(r"(?:(?<![\w$.])(?:window|self|globalThis)\s*(?:\.\s*onmessage|\[\s*['\"]onmessage['\"]\s*\])"
                        r"|(?<![\w$.])onmessage)\s*=(?!=)")


def _window_onmessage(text):
    """Every onmessage handler assigned to the window in `text` (the matches, for the failure message)."""
    return [m.group(0) for m in _ONMESSAGE.finditer(text)]


def _inline_scripts(html):
    """The bodies of the page's inline <script> elements, in page order (a <script src=...> is a bundle, not here)."""
    return re.findall(r"<script>(.*?)</script>", html, re.S)


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

    def test_it_is_defined_once_on_the_served_shell_ahead_of_every_listener(self):
        html = km._landing()
        self.assertEqual(html.count(REGION_HEAD), 1)
        self.assertEqual(html.count("window.__rompPaneSourceOk="), 1, "one definition, no second copy to drift")
        # every mention of the name on the page is the definition or one listener's fail-closed read (two mentions
        # each), so no assignment in another spelling, and no other reader, sits anywhere in the served shell
        self.assertEqual(html.count("__rompPaneSourceOk"), 1 + 2 * len(LISTENERS),
                         "the name appears only in the adopted definition and in each named listener's gate")
        self.assertEqual(html.count(GATE), len(LISTENERS), "each named listener's gate, once")
        scripts = _inline_scripts(html)
        where = [n for n, s in enumerate(scripts) if REGION_HEAD in s]
        self.assertEqual(len(where), 1)
        first_listener = min(n for n, s in enumerate(scripts) if LISTEN_OPEN in s)
        self.assertLessEqual(where[0], first_listener, "defined before (or in) the first script that listens")
        self.assertLess(scripts[where[0]].index(REGION_HEAD), scripts[where[0]].index(LISTEN_OPEN))
        self.assertLess(html.index("<body"), html.index(REGION_HEAD), "a body script, after the markup it reads")


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
    """Nothing outside the adopted lines and the thirteen gates names the check: no other code in the kernel (the pane
    shim, another page's script, a string it serves), and no file anywhere else in the tree (a ui/ bundle the shell or a
    pane loads, the timeline view). So no code in the tree replaces the shell's check under its name, on its own window
    or on a pane's window.parent. This census reads text; a replacement the landing makes in any spelling, at load or
    deferred, is what the executed legs below catch."""

    def test_no_file_but_the_kernel_names_the_check(self):
        hits, read = _files_naming("__rompPaneSourceOk")
        # the walk reads the sources a script on romp's origin comes from: the kernel's pages, the bundles built from
        # ui/webview (the shell's palette, every pane's), the timeline view the kernel injects, the extension's source
        for must in ("kernel/kernel.py", "ui/webview/palette-main.ts", "ui/webview/render.ts", "ui/webview/gear.js",
                     "ui/webview/frame-listener.ts", "ui/romp-timeline-view.js", "vscode-extension/src/extension.ts"):
            self.assertIn(must, read, "the walk read " + must)
        self.assertGreater(len([f for f in read if f.startswith("ui/")]), 100, "the walk read ui/ (%d files)" % len(read))
        self.assertEqual(hits, ["kernel/kernel.py"], "a file outside the kernel names the shell's check")

    def test_the_kernel_names_it_only_in_the_adopted_lines_and_the_gates(self):
        with open(os.path.join(os.path.dirname(HERE), "kernel", "kernel.py"), encoding="utf-8") as f:
            src = f.read()
        # the Python comment lines that describe it aside, every mention is in the served JavaScript
        code = "\n".join(l for l in src.split("\n") if not l.lstrip().startswith("#"))
        self.assertEqual(code.count(REGION_HEAD), 1, "the adopted definition, once")
        self.assertEqual(code.count(GATE), len(LISTENERS), "each gate, once")
        self.assertEqual(code.count("__rompPaneSourceOk"), 1 + 2 * len(LISTENERS),
                         "the name appears in kernel.py's code only in the adopted definition and the gates")

    def test_no_page_but_the_shell_carries_it(self):
        pages = {"/chat": km._chat_page(), "/feed": km._feed_page(), "/fleet": km._fleet_page(),
                 "/waiting": km._waiting_page(), "/files": km._files_page(), "/settings": km._settings_page(),
                 "/timeline": km._timeline_page(), "the sign-in page": km._TOKEN_LOGIN_HTML,
                 "the too-large page": km._too_large_page("too large", "a.pdf", {})}
        for name, page in pages.items():
            with self.subTest(page=name):
                self.assertIn("<", page, "the page was built")
                self.assertNotIn("__rompPaneSourceOk", page)
        self.assertEqual(km._landing().count("__rompPaneSourceOk"), 1 + 2 * len(LISTENERS))


class ShellListenerCensus(unittest.TestCase):
    """Every window message listener in the served shell reads the check fail-closed as its first statement; the
    service worker's channel, which no window can post on, is the one listener without it."""

    def setUp(self):
        self.html = km._landing()

    def test_every_window_listener_in_the_shell_is_named_and_gated(self):
        opens = [m.start() for m in re.finditer(re.escape("window." + LISTEN_OPEN), self.html)]
        self.assertEqual(len(opens), len(LISTENERS),
                         "a window message listener in the shell that LISTENERS does not name (or a named one gone): "
                         "name it there and decide its senders")
        for at in opens:
            head = self.html[at + len("window." + LISTEN_OPEN):][:len(GATE)]
            with self.subTest(at=self.html[at:at + 160]):
                self.assertEqual(head, GATE, "the check, fail-closed, is the listener's first statement")
        # no listener in another spelling slips past the census: every message listener on the page is one of the
        # thirteen above or the service worker's channel
        every = re.findall(r"addEventListener\(\s*['\"]message['\"]", self.html)
        self.assertEqual(len(every), len(LISTENERS) + 1, "the thirteen window listeners and the service worker's")
        self.assertEqual(self.html.count("swc.addEventListener('message',function(ev){"), 1,
                         "the service worker's own channel: exempt, a window cannot post on it")
        # nor as an onmessage handler on the window, by any name the page reaches it by: window.onmessage=,
        # self.onmessage=, globalThis['onmessage']=, a bare onmessage=. A socket's (ws.onmessage=, d.onmessage=) and a
        # MessageChannel port's are no window listener, and no other page can post on them
        self.assertEqual(_window_onmessage(self.html), [], "an onmessage handler on the shell's window")

    def test_the_onmessage_census_reads_each_spelling(self):
        for src in ("window.onmessage=function(e){}", "self.onmessage = f", "globalThis['onmessage']=f", "window [\"onmessage\"] =f",
                    ";onmessage=function(e){}", "\n  onmessage = f"):
            with self.subTest(src=src):
                self.assertEqual(len(_window_onmessage(src)), 1)
        for src in ("ws.onmessage=function(ev){}", "d.onopen=d.onmessage=d.onclose=null", "ch.port1.onmessage=flush",
                    "if(window.onmessage===f)go()", "var x_onmessage=1"):
            with self.subTest(src=src):
                self.assertEqual(_window_onmessage(src), [])

    def test_each_named_listener_opens_with_the_check(self):
        for name, phrase in LISTENERS.items():
            with self.subTest(listener=name):
                self.assertEqual(self.html.count(phrase), 1, "the phrase names one place in the shell")
                at = self.html.rindex(LISTEN_OPEN, 0, self.html.index(phrase))
                self.assertEqual(self.html[at + len(LISTEN_OPEN):][:len(GATE)], GATE,
                                 "%s acts on a message only after the source check admits it" % name)

    def test_the_active_tab_relay_reads_the_shared_check_instead_of_its_own(self):
        # the relay had the one inline origin check in the shell; it reads the shared check now, as the project's does
        js = km._LANDING_FOCUS_JS
        self.assertIn("window.addEventListener('message',function(e){" + GATE +
                      "var m=e&&e.data;if(!m||m.romp!=='activeTab')return;", js)
        self.assertNotIn("e.origin!==location.origin)return;", js)


# A stand-in browser for the shell's inline scripts: node's vm runs them in a context whose global answers every name
# it does not hold with an inert stub (callable, constructible, every property another stub, 0 as a number), so the
# scripts boot far enough to register their listeners without a DOM. What the checks read is real: location (the
# shell's origin), document.querySelectorAll('iframe') (the shell's frames), window.parent/top (the shell is the top
# window). The harness then hands each registered window message listener a message from each sender and counts how
# often the listener reads the message's data: a listener that returns before reading it acts on nothing.
_HARNESS = r"""
'use strict';
const vm = require('vm');
const fs = require('fs');
const SCRIPTS = JSON.parse(fs.readFileSync(process.env.ROMP_TEST_SCRIPTS, 'utf8'));
const ORIGIN = 'http://127.0.0.1:7777', ELSEWHERE = 'https://elsewhere.example';
const stubHandler = {
  get(t, k) {
    if (k === Symbol.toPrimitive) return () => 0;
    if (k === Symbol.iterator) return function* () {};
    if (typeof k === 'symbol') return undefined;
    if (k === 'length') return 0;
    return STUB;
  },
  set() { return true; }, has() { return false; }, deleteProperty() { return true; },
  apply() { return STUB; }, construct() { return STUB; },
};
const STUB = new Proxy(function () {}, stubHandler);
function stubbed(o) { return new Proxy(o, { get(t, k) { return (k in t) ? t[k] : stubHandler.get(t, k); } }); }
// windows: a pane of the shell (the chat), the Files pane, a sandboxed frame of the shell, a frame of the shell on
// another origin, a same-origin window the shell does not hold (a popup, a frame nested in a pane), a page on another
// origin that opened the shell
const POSTED = [];
function win(name) { return stubbed({ name, postMessage(m) { POSTED.push([name, m]); }, focus() {} }); }
const CHAT = win('chat'), FILES = win('files'), SANDBOXED = win('sandboxed'), XFRAME = win('xframe'),
      STRAY = win('stray'), OPENER = win('opener');
function frame(id, w) { return stubbed({ id, contentWindow: w, getAttribute(n) { return n === 'id' ? id : null; },
                                         addEventListener() {}, removeEventListener() {} }); }
const FRAMES = [frame('f-chat', CHAT), frame('f-files', FILES), frame('f-url', SANDBOXED), frame('f-x', XFRAME)];
const BYID = {}; FRAMES.forEach((f) => { BYID[f.id] = f; });
// what the page leaves for later: timer, animation-frame, idle and microtask callbacks, and the listeners for the page's
// load events (window's and document's) and an on<load event> handler. All run after the scripts and before any
// message is delivered, so a write the page defers is in place when the listeners are tested
const LATE = [];
const LATE_EVENTS = new Set(['load', 'DOMContentLoaded', 'pageshow', 'readystatechange']);
function later(f) { if (typeof f === 'function') LATE.push(f); return LATE.length; }
const document = stubbed({
  querySelectorAll(sel) { return sel === 'iframe' ? FRAMES.slice() : []; },
  getElementById(id) { return BYID[id] || STUB; },
  addEventListener(type, f) { if (LATE_EVENTS.has(type)) later(f); },
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
// every value the scripts assign to the window's onmessage, however spelled: an onmessage handler is a window message
// listener addEventListener never sees
const ONMESSAGE = [];
function onGlobalWrite(k, v) {
  if (k === CHECK) heard(v);
  if (k === 'onmessage') ONMESSAGE.push(textOf(v));
  if ((k === 'onload' || k === 'onpageshow') && typeof v === 'function') later(v);
}
function textOf(v) { return typeof v === 'function' ? Function.prototype.toString.call(v) : typeof v; }
const BUILTINS = new Set(['Object', 'Array', 'JSON', 'Math', 'Date', 'String', 'Number', 'Boolean', 'RegExp', 'Error',
  'TypeError', 'RangeError', 'SyntaxError', 'ReferenceError', 'Map', 'Set', 'WeakMap', 'WeakSet', 'Symbol', 'Promise',
  'parseInt', 'parseFloat', 'isNaN', 'isFinite', 'encodeURIComponent', 'decodeURIComponent', 'encodeURI', 'decodeURI',
  'Infinity', 'NaN', 'undefined', 'Intl', 'URL', 'URLSearchParams', 'Reflect', 'Proxy', 'BigInt', 'Function']);
const G = new Proxy(target, {
  has() { return true; },
  get(t, k) { if (k in t) return t[k]; if (typeof k === 'symbol') return undefined; if (BUILTINS.has(k)) return globalThis[k]; return STUB; },
  set(t, k, v) { onGlobalWrite(k, v); t[k] = v; return true; },
  defineProperty(t, k, d) { onGlobalWrite(k, 'value' in d ? d.value : d); Object.defineProperty(t, k, d); return true; },
  getOwnPropertyDescriptor(t, k) { return Object.getOwnPropertyDescriptor(t, k); },
  deleteProperty(t, k) { delete t[k]; return true; },
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
    if (type === 'message') LISTENERS.push({ f, src: String(f), checkDefined: typeof target.__rompPaneSourceOk === 'function' });
    else if (LATE_EVENTS.has(type)) later(f);
  },
  removeEventListener() {},
});
const ctx = vm.createContext(G);
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
// the check the listeners will read, as the scripts and everything they left for later left it
const AFTER_BOOT = textOf(target.__rompPaneSourceOk);
// the senders: [name, source, origin]
const SENDERS = {
  opener: [OPENER, ELSEWHERE],             // a page on another origin that opened the dashboard
  sandboxedFrame: [SANDBOXED, 'null'],    // a sandboxed iframe of the shell (opaque origin)
  otherOriginFrame: [XFRAME, ELSEWHERE],  // an iframe of the shell showing another origin
  strayWindow: [STRAY, ORIGIN],           // same origin, but not a frame of this document (a popup, a nested frame)
  shellItself: [vm.runInContext('window', ctx), ORIGIN],   // the shell's own window, as its scripts see it
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
const MODE = process.env.ROMP_TEST_MODE || 'reads';
const out = { errors: ERRORS, listeners: LISTENERS.map((l) => ({ src: l.src, checkDefined: l.checkDefined })),
              assigns: ASSIGNED.map(textOf), afterBoot: AFTER_BOOT, late: LATE_RUN, onmessage: ONMESSAGE };
if (MODE === 'reads' || MODE === 'nocheck') {
  // the check missing (held as undefined: a name the context lacks answers with a stub): fail-closed hears nothing
  if (MODE === 'nocheck') target.__rompPaneSourceOk = undefined;
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
}
out.inEffect = [...IN_EFFECT];
process.stdout.write('\n' + JSON.stringify(out));
})().catch((x) => { process.stderr.write(String(x && x.stack || x)); process.exit(1); });
"""


def _run_landing(mode):
    node = shutil.which("node")
    if not node:
        raise unittest.SkipTest("node not installed")
    fx = tempfile.mkdtemp()
    try:
        scripts = os.path.join(fx, "scripts.json")
        with open(scripts, "w") as f:
            json.dump(_inline_scripts(km._landing()), f)
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
    """The served shell's scripts, run: no listener reads a message from a sender that is not one of its panes."""

    REFUSED = ("opener", "sandboxedFrame", "otherOriginFrame", "strayWindow", "shellItself", "dispatch",
               "sourcelessElsewhere", "sourcelessOpaque")

    @classmethod
    def setUpClass(cls):
        cls.run_ = _run_landing("reads")

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
        # whatever spelling a second assignment used (window['...']=, a bare global, a defineProperty), and whenever it
        # ran (at load, or from a timer, a microtask or a load listener the scripts left for later), it lands on the
        # page's global: the scripts assign the check once, the adopted function, and it is the function in effect at
        # every delivery, so a later wrapper that widens it for some senders cannot stand in for it
        html = km._landing()
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

    def test_no_script_assigns_an_onmessage_handler_to_the_window(self):
        # an onmessage handler is a window message listener that addEventListener never sees; however a script spells
        # the write (window.onmessage=, a computed member, a bare global, a defineProperty), it lands on the global
        self.assertEqual(self.run_["onmessage"], [], "an onmessage handler on the shell's window")

    def test_without_the_check_no_listener_reads_anything(self):
        run = _run_landing("nocheck")
        self.assertEqual(len(run["reads"]), len(LISTENERS))
        for l, reads in zip(run["listeners"], run["reads"]):
            with self.subTest(listener=_name_of(l["src"])):
                self.assertEqual(sum(reads.values()), 0, "fail-closed: no check, no message, not even a pane's")


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


# The adopted check alone, over stand-in windows: the truth table of what it admits.
_CHECK_HARNESS = r"""
'use strict';
const ORIGIN = 'http://127.0.0.1:7777';
const pane = { n: 'pane' }, urlPane = { n: 'urlPane' }, nested = { n: 'nested' }, stray = { n: 'stray' };
let FRAMES = [{ contentWindow: pane, getAttribute: () => null },
              { contentWindow: urlPane, getAttribute: (k) => (k === 'data-protocol' ? 'none' : null) }];
let THROW = false;
global.window = global;
global.location = { origin: ORIGIN };
global.document = { querySelectorAll: (s) => { if (THROW) throw new Error('detached'); return s === 'iframe' ? FRAMES : []; } };
REGION
const ok = window.__rompPaneSourceOk;
const rows = {
  pane: ok({ source: pane, origin: ORIGIN }),
  paneOtherOrigin: ok({ source: pane, origin: 'https://elsewhere.example' }),
  paneOpaqueOrigin: ok({ source: pane, origin: 'null' }),
  urlPaneMarkedNone: ok({ source: urlPane, origin: ORIGIN }),
  nestedFrame: ok({ source: nested, origin: ORIGIN }),
  strayWindow: ok({ source: stray, origin: ORIGIN }),
  itself: ok({ source: window, origin: ORIGIN }),
  noSource: ok({ source: null, origin: ORIGIN }),
  noSourceNoOrigin: ok({ source: null, origin: '' }),
  noSourceOpaqueOrigin: ok({ source: null, origin: 'null' }),
  noEvent: ok(null),
};
THROW = true; rows.throws = ok({ source: pane, origin: ORIGIN });
process.stdout.write(JSON.stringify(rows));
"""


class AdoptedCheckExecuted(unittest.TestCase):
    """The adopted lines, run: true only for a same-origin iframe of this document that is not marked
    data-protocol=none; false for every other sender and when the frame walk throws."""

    def test_the_truth_table(self):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("node not installed")
        html = km._landing()
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
        self.assertEqual(rows, {
            "pane": True, "paneOtherOrigin": False, "paneOpaqueOrigin": False, "urlPaneMarkedNone": False,
            "nestedFrame": False, "strayWindow": False, "itself": False, "noSource": False, "noSourceNoOrigin": False,
            "noSourceOpaqueOrigin": False, "noEvent": False, "throws": False,
        })


if __name__ == "__main__":
    unittest.main()
