#!/usr/bin/env python3
"""The shell tells its panes which panes are on screen, and relays a file click into the Files pane.

A file link clicked in the chat while the Files pane is open must open there whatever the "File links
open in" setting says (the pane being open is the intent), and the chat has no way to see the pane on
its own. The shell owns pane state (_LANDING_COLLAPSE_JS: the po object, apply(), __rompPaneToggle), so
the shell broadcasts it: {romp:'panes',on:{key:bool}} into every pane iframe on every apply(), the
exact event of the set changing (a toggle, the boot apply, another tab's storage event), again on each
iframe's own load, so a pane that boots or reloads after the shell hears the current set, and from the
mobile script on a tab switch or a layout flip. On a phone "on" means the tab showing, not the po flag,
so a po.files left true by a desktop session cannot steer a phone's file links into a tab nobody is
looking at. The chat caches the set and routes by it (render.ts panesOn; ui/webview/file-route.ts).

The three shell scripts involved are the kernel's own inline JavaScript, so they run here under node
against a fake window and document, and the messages they post are read back: the collapse controller,
the mobile script (__rompMobileOn, __rompMobileTab, the re-tell, and the switches the person makes, a tab
tap, a reveal, the chat header's Outline pill, which drop the relay's remembered tab) and the settings
listener's arms (viewFile with pane:'pane', filesViewerClosed, and the browseFiles arm the feed's browser
keeps; that arm's Files-pane branch, a browseFiles with pane:'pane', runs in tests/test_files_pane.py
BrowseRelay).
Synthetic only: placeholder sids, the notes-api demo world, TESTHOST.
"""
import inspect
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Hermetic state BEFORE the loads: they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
km = load_source("romp_kernel_psb", os.path.join(BIN, "romp-kernel"))

SID = "11111111-2222-3333-4444-555555555555"


def _run(js):
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(js)
        path = f.name
    try:
        r = subprocess.run(["node", path], capture_output=True, text=True, timeout=30)
    finally:
        os.unlink(path)
    assert r.returncode == 0, "the shell script threw: " + r.stderr[:1200]
    return json.loads(r.stdout.strip().splitlines()[-1])


# ── the pane controller ───────────────────────────────────────────────────────────────────────────
# One iframe per pane key; the desktop shell (no rail buttons: querySelectorAll is empty), the feed and
# chat and timeline on, the Outline and the Files pane off, the way the served body class starts.
_COLLAPSE_HARNESS = r"""
'use strict';
const POSTED = {}, LOADS = {}, CLS = new Set(['po-chat', 'po-feed', 'po-timeline']), STORE = {}, STORAGE = [], SETS = {}, TABS = [];
const KEYS = __KEYS__;
// the served markup: the chat alone carries src; every other pane carries data-src (the controller copies it to src for an
// optional pane this browser shows; the mobile script, not run here, promotes the Waiting and Files panes)
const frames = {};
KEYS.forEach((k) => { const attrs = (k === 'chat') ? { src: '/' + k } : { 'data-src': '/' + k }; frames['f-' + k] = {
  attrs,
  getAttribute: (a) => (a in attrs ? attrs[a] : null),
  setAttribute: (a, v) => { attrs[a] = v; SETS[k] = (SETS[k] || 0) + 1; },
  contentWindow: { postMessage: (m) => { (POSTED[k] = POSTED[k] || []).push(JSON.parse(JSON.stringify(m))); } },
  addEventListener: (ev, f) => { if (ev === 'load') (LOADS[k] = LOADS[k] || []).push(f); } }; });
// one button per pane stands for its rail button AND its phone tab (both are found by data-pane)
const BTNS = {};
KEYS.forEach((k) => { BTNS[k] = { hidden: false, title: '', getAttribute: (a) => (a === 'data-pane' ? k : null), classList: { toggle() {} }, addEventListener() {} }; });
let TAB = 'chat', MOBILE = false;
global.window = global;
global.localStorage = { getItem: (k) => (k in STORE ? STORE[k] : null), setItem: (k, v) => { STORE[k] = v; } };
global.location = { search: '' };
global.URLSearchParams = class { get() { return null; } };
global.Event = class { constructor(t) { this.type = t; } };
global.addEventListener = (ev, f) => { if (ev === 'storage') STORAGE.push(f); };
global.dispatchEvent = () => true;
global.document = {
  body: { classList: { toggle: (c, on) => { if (on) CLS.add(c); else CLS.delete(c); }, contains: (c) => CLS.has(c) },
          getAttribute: (a) => (a === 'data-tab' ? TAB : null) },
  querySelectorAll: (sel) => { if (sel === '.rail-btn[data-pane]') return KEYS.map((k) => BTNS[k]); const m = /data-pane=(\w+)/.exec(sel); return m && BTNS[m[1]] ? [BTNS[m[1]]] : []; },
  getElementById: (id) => frames[id] || null,
};
window.__rompMobileOn = () => MOBILE;
window.__rompMobileTab = (t) => { TABS.push(t); TAB = t; };
__SEED__
"""
_COLLAPSE_DRIVER = r"""
const counts = () => Object.fromEntries(KEYS.map((k) => [k, (POSTED[k] || []).length]));
const last = (k) => (POSTED[k] || []).slice(-1)[0];
const out = {};
out.boot = { counts: counts(), chat: last('chat'), files: last('files') };
window.__rompPaneToggle('files', true);
out.on = { counts: counts(), chat: last('chat'), cls: CLS.has('po-files'), store: JSON.parse(STORE['romp-panes'] || 'null') };
window.__rompPaneToggle('files', true);        // already so: no change, so no message claiming one
out.same = { counts: counts() };
(LOADS.chat || []).forEach((f) => f());        // the chat iframe reloads: it hears the current set again
out.reload = { counts: counts(), chat: last('chat') };
MOBILE = true; TAB = 'chat'; window.__rompPanesTell();
out.phoneChat = last('chat');
TAB = 'files'; window.__rompPanesTell();
out.phoneFiles = last('files');
MOBILE = false;
window.__rompPaneToggle('files');              // no `to`: flips it off
out.off = { chat: last('chat'), cls: CLS.has('po-files'), store: JSON.parse(STORE['romp-panes'] || 'null') };
out.teller = typeof window.__rompPanesTell;
console.log(JSON.stringify(out));
"""


# ── the Files control hidden by its gear setting (T317) ─────────────────────────────────────────────────
# The store holds NO romp:settings at all (a fresh install: the control is OFF by default since T317b, the user
# 2026-09-10) and the Files pane is ON (a desktop session of the shown-by-default era left it open):
# the boot apply hides the control (body.no-files-control), closes the pane and saves that, tells the panes the
# pane is unavailable (avail.files false), and refuses to bring it forward; a phone left on the Files tab is
# switched to the chat. Flipping the store back on (the gear's write, heard through the storage listener) shows
# the control again and the pane can open.
_HIDDEN_DRIVER = r"""
const last = (k) => (POSTED[k] || []).slice(-1)[0];
const counts = () => Object.fromEntries(KEYS.map((k) => [k, (POSTED[k] || []).length]));
const out = {};
out.boot = { cls: CLS.has('no-files-control'), poFiles: CLS.has('po-files'), store: JSON.parse(STORE['romp-panes'] || 'null'), chat: last('chat'), counts: counts() };
window.__rompPaneToggle('files', true);          // a relay's bring-forward, the palette's command: refused
out.refused = { poFiles: CLS.has('po-files'), chat: last('chat'), counts: counts() };
MOBILE = true; TAB = 'files'; SWITCHED.length = 0; window.__rompPaneToggle('feed');   // any apply (here a feed flip) on a phone left on the Files tab
out.phone = { switched: SWITCHED.slice() };
MOBILE = false;
STORE['romp:settings'] = JSON.stringify({ showFilesControl: true }); STORAGE_LISTENERS.forEach((f) => f());   // the gear turns it back on
out.shown = { cls: CLS.has('no-files-control'), chat: last('chat') };
window.__rompPaneToggle('files', true);
out.reopened = { poFiles: CLS.has('po-files'), chat: last('chat') };
console.log(JSON.stringify(out));
"""


_BOOKMARK_DRIVER = r"""
const out = { poFiles: CLS.has('po-files'), cls: CLS.has('no-files-control'), store: STORE['romp-panes'], chat: (POSTED.chat || []).slice(-1)[0] };
console.log(JSON.stringify(out));
"""


class HiddenControlBookmark(unittest.TestCase):
    """A ?panes=chat,files bookmark opened with the control hidden: the view shows the chat alone (the pane is closed
    on the boot apply), but the stored pane set is NOT rewritten with the bookmark's — a bookmark was always a view,
    never a write (review find: the forced close's save would have replaced the person's stored set)."""

    @classmethod
    def setUpClass(cls):
        keys = [k for k, _ in km._PANE_ORDER]
        stored = json.dumps({"chat": True, "fleet": False, "feed": True, "timeline": True, "files": False})
        # the store is seeded through the harness's __SEED__ slot (the OptionalPanes convention): the declaration
        # line it once rewrote grew the optional-pane collections and no longer matched, leaving the slot unfilled
        harness = (_COLLAPSE_HARNESS.replace("__KEYS__", json.dumps(keys))
                   .replace("__SEED__", "STORE['romp:settings'] = JSON.stringify({ filesControl: true }); STORE['romp-panes'] = " + json.dumps(stored) + ";")   # the T317-era key's true (a whole-object save merged it in): never read, the control stays hidden (T317b)
                   .replace("global.location = { search: '' };", "global.location = { search: '?panes=chat,files' };")
                   .replace("global.URLSearchParams = class { get() { return null; } };", "global.URLSearchParams = class { get(k) { return k === 'panes' ? 'chat,files' : null; } };"))
        cls.stored = stored
        cls.out = _run(harness + km._LANDING_COLLAPSE_JS + _BOOKMARK_DRIVER)

    def test_the_bookmark_shows_the_chat_alone_and_writes_nothing(self):
        self.assertFalse(self.out["poFiles"], "the bookmark's files pane is closed: the control is hidden")
        self.assertTrue(self.out["cls"])
        self.assertEqual(self.out["store"], self.stored, "the stored pane set is untouched: a bookmark is a view")
        self.assertEqual(self.out["chat"]["on"], {"chat": True, "timeline": False, "fleet": False, "feed": False, "waiting": False, "files": False})
        self.assertEqual(self.out["chat"]["avail"], {"files": False})


class HiddenControl(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        keys = [k for k, _ in km._PANE_ORDER]
        # seeded through __SEED__ (see HiddenControlBookmark); the harness already collects the storage listeners
        # (STORAGE) and the phone's tab switches (TABS), which the driver reads under its own names
        harness = (_COLLAPSE_HARNESS.replace("__KEYS__", json.dumps(keys))
                   .replace("__SEED__", "STORE['romp-panes'] = JSON.stringify({ chat: true, fleet: false, feed: true, timeline: true, files: true });"   # no romp:settings: the default hides (T317b)
                            "const STORAGE_LISTENERS = STORAGE, SWITCHED = TABS;"))
        cls.out = _run(harness + km._LANDING_COLLAPSE_JS + _HIDDEN_DRIVER)

    def test_the_boot_apply_hides_the_control_and_closes_the_open_pane(self):
        b = self.out["boot"]
        self.assertTrue(b["cls"], "body.no-files-control: the rail's toggle and the phone's tab are hidden by CSS")
        self.assertFalse(b["poFiles"], "the pane a desktop session left open closes on the same apply")
        self.assertEqual(b["store"]["files"], False, "…and the close is saved, so a reload stays closed")
        self.assertEqual(b["chat"]["avail"], {"files": False}, "the panes are told the pane is unavailable: file links open over the pane clicked")
        self.assertEqual(b["chat"]["on"]["files"], False)

    def test_the_pane_cannot_be_brought_forward_while_the_control_is_hidden(self):
        r = self.out["refused"]
        self.assertFalse(r["poFiles"], "a relay's bring-forward or the palette's command is refused")
        self.assertEqual(r["counts"], self.out["boot"]["counts"], "…silently: no message claiming a change")
        self.assertEqual(self.out["boot"]["counts"], {k: 1 for k in [k for k, _ in km._PANE_ORDER]}, "the boot apply told each pane once")

    def test_a_phone_left_on_the_files_tab_is_switched_to_the_chat(self):
        self.assertEqual(self.out["phone"]["switched"], ["chat"])

    def test_the_gears_write_shows_the_control_again_and_the_pane_can_open(self):
        s = self.out["shown"]
        self.assertFalse(s["cls"], "the storage event re-applies: the control shows")
        self.assertEqual(s["chat"]["avail"], {"files": True})
        r = self.out["reopened"]
        self.assertTrue(r["poFiles"], "and the pane opens again")
        self.assertEqual(r["chat"]["on"]["files"], True)


class Broadcast(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.keys = [k for k, _ in km._PANE_ORDER]
        # the control turned ON by its gear setting (off by default since T317b): the toggles the driver makes are the
        # user's clicks on a control they asked for; seeded through the harness's __SEED__ slot
        cls.out = _run(_COLLAPSE_HARNESS.replace("__KEYS__", json.dumps(cls.keys)).replace("__SEED__", "STORE['romp:settings'] = JSON.stringify({ showFilesControl: true });") + km._LANDING_COLLAPSE_JS + _COLLAPSE_DRIVER)

    def test_the_boot_apply_tells_every_pane_the_set_as_the_flags_stand(self):
        self.assertEqual(self.out["boot"]["counts"], {k: 1 for k in self.keys}, "one message per pane at boot")
        self.assertEqual(self.out["boot"]["chat"], {"romp": "panes", "on": {"chat": True, "timeline": True, "fleet": False, "feed": True, "waiting": False, "files": False},
                                                     "avail": {"files": True}, "link": "down", "mob": False})   # avail: the Files control's setting rides every tell (T317); link (D3, 2026-09-18): the shell socket's state, 'down' here since this harness runs no shell socket; mob (review round 3, extra8-1): the layout word, the desktop here (window.__rompLink absent)
        self.assertEqual(self.out["boot"]["files"], self.out["boot"]["chat"], "every pane hears the same set")

    def test_a_toggle_is_the_event_and_a_no_change_toggle_is_silent(self):
        self.assertEqual(self.out["on"]["counts"], {k: 2 for k in self.keys})
        self.assertTrue(self.out["on"]["chat"]["on"]["files"], "the Files pane is on after the toggle")
        self.assertTrue(self.out["on"]["cls"], "and the body class the CSS shows the column by")
        self.assertEqual((self.out["on"]["store"] or {}).get("files"), True, "and the set persists")
        # a repeated bring-forward (the viewFile relay on an already-open pane) changes nothing, so it says
        # nothing: a message is a claim that something changed, and the panes must be able to trust it
        self.assertEqual(self.out["same"]["counts"], {k: 2 for k in self.keys})

    def test_a_pane_that_loads_after_the_shell_hears_the_set(self):
        self.assertEqual(self.out["reload"]["counts"]["chat"], 3, "the chat's load handler re-tells it")
        self.assertEqual(self.out["reload"]["counts"]["files"], 2, "and nobody else")
        self.assertEqual(self.out["reload"]["chat"]["on"]["files"], True, "with the current set")

    def test_on_a_phone_on_means_the_tab_showing_not_the_flag(self):
        # po.files is true here (the toggle above), yet the phone on the chat tab reports it off
        self.assertEqual(self.out["phoneChat"]["on"], {"chat": True, "timeline": False, "fleet": False, "feed": False, "waiting": False, "files": False})
        self.assertEqual(self.out["phoneFiles"]["on"], {"chat": False, "timeline": False, "fleet": False, "feed": False, "waiting": False, "files": True})

    def test_a_toggle_off_reports_the_pane_off(self):
        self.assertFalse(self.out["off"]["chat"]["on"]["files"])
        self.assertFalse(self.out["off"]["cls"])
        self.assertEqual((self.out["off"]["store"] or {}).get("files"), False)

    def test_the_mobile_script_can_re_tell(self):
        self.assertEqual(self.out["teller"], "function", "window.__rompPanesTell is the mobile script's hook")

    def test_the_key_set_is_the_one_pane_list(self):
        # derived from _PANE_ORDER, never a second hand-written list: a pane added there is broadcast
        js = km._LANDING_COLLAPSE_JS
        self.assertIn("var KEYS=" + json.dumps(self.keys) + ";", js)
        self.assertIn('var KEYS=""" + json.dumps([k for k, _ in _PANE_ORDER]) + """;', open(os.path.join(BIN, "romp-kernel")).read())
        self.assertEqual(len(self.keys), 6, "six panes on this kernel: the Waiting on you pane is a column of its own")
        # every key ships an iframe by the id the broadcast addresses, or a pane is silently never told
        html = km._landing()
        for k in self.keys:
            self.assertIn("<iframe id=f-%s " % k, html, "no iframe for pane key %r" % k)

    def test_the_files_relay_still_brings_a_closed_pane_forward(self):
        # the receiving end is unchanged: a viewFile naming the pane on a CLOSED Files pane opens it (idempotent on an
        # open one, per the guard above) and forwards the click; nothing here touches the feed's browser route (its
        # was-off flag and browseClosed restore)
        js = km._LANDING_SETTINGS_JS
        head = "if(m.romp==='viewFile'&&m.pane==='pane'){var ff=document.getElementById('f-files');"
        branch = js.split(head)[1].split("if(m.romp==='filesViewerClosed')")[0]
        self.assertIn("window.__rompPaneToggle&&window.__rompPaneToggle('files',true)", branch)
        for tok in ("__rompFeedWasOff", "'f-feed'", "browseClosed"):
            self.assertNotIn(tok, "\n".join(l for l in branch.splitlines() if not l.lstrip().startswith("//")))


# ── the optional panes (the user 2026-09-10) ──────────────────────────────────────────────────────
# The gear's Panes section (romp:settings.panes) hides Sessions (timeline), the Outline (fleet) or the Feed
# from this browser's dashboard altogether. The controller reads it at boot and on the storage event: a pane
# off there leaves po and KEYS (togglePane refuses it, the broadcast omits it), wears hidden on its rail
# button and phone tab, and never gets its src (the markup carries data-src); a pane on gets its src once.
_OPT_DRIVER = r"""
const counts = () => Object.fromEntries(KEYS.map((k) => [k, (POSTED[k] || []).length]));
const last = (k) => (POSTED[k] || []).slice(-1)[0];
const src = () => Object.fromEntries(KEYS.map((k) => [k, frames['f-' + k].getAttribute('src')]));
const hidden = () => Object.fromEntries(KEYS.map((k) => [k, BTNS[k].hidden]));
const out = {};
out.boot = { counts: counts(), chat: last('chat'), src: src(), hidden: hidden(), cls: CLS.has('po-feed'), tabs: TABS.slice(), sets: Object.assign({}, SETS) };
window.__rompPaneToggle('feed', true);           // the rail cannot bring a pane back that the gear took out
out.refused = { counts: counts(), cls: CLS.has('po-feed'), chat: last('chat') };
window.__rompPaneToggle('files', true);          // the other panes toggle as ever, and the set persisted omits the hidden one
out.files = { chat: last('chat'), store: JSON.parse(STORE['romp-panes'] || 'null') };
// the gear turns the feed back on: its save lands here as a storage event for romp:settings
STORE['romp:settings'] = JSON.stringify({ showFilesControl: true, panes: { feed: true } });
STORAGE.forEach((f) => f({ key: 'romp:settings' }));
out.enabled = { counts: counts(), chat: last('chat'), feed: last('feed'), src: src(), hidden: hidden(), cls: CLS.has('po-feed'), sets: Object.assign({}, SETS) };
(LOADS.feed || []).forEach((f) => f());          // the feed page loads now, after the shell: it hears the set on its load
out.loaded = { counts: counts(), feed: last('feed') };
// and off again, then on: the src is never reassigned (no reload of a live pane), the flag it had comes back
STORE['romp:settings'] = JSON.stringify({ showFilesControl: true, panes: { feed: false } });
STORAGE.forEach((f) => f({ key: 'romp:settings' }));
out.off = { chat: last('chat'), cls: CLS.has('po-feed'), hidden: hidden(), src: src() };
STORE['romp:settings'] = JSON.stringify({ showFilesControl: true, panes: {} });
STORAGE.forEach((f) => f({ key: 'romp:settings' }));
out.back = { chat: last('chat'), cls: CLS.has('po-feed'), sets: Object.assign({}, SETS) };
// a storage event for another key re-applies but does not re-read the panes
STORE['romp:settings'] = JSON.stringify({ showFilesControl: true, panes: { fleet: false } });
STORAGE.forEach((f) => f({ key: 'romp-pane-grow' }));
out.otherKey = { chat: last('chat'), hidden: hidden() };
STORAGE.forEach((f) => f({ key: null }));       // a cleared store is read again
out.cleared = { chat: last('chat'), hidden: hidden() };
// the gear turns the Outline on, whose rail default is OFF: it comes on screen (the reason to turn it on), at a
// fair width, and the set persists so a reload keeps it; the pane's own rail toggle hides it from there
const GREW = []; window.__rompGrowFair = (k) => GREW.push(k);
out.fleetBefore = { cls: CLS.has('po-fleet'), store: JSON.parse(STORE['romp-panes'] || 'null') };
STORE['romp:settings'] = JSON.stringify({ showFilesControl: true, panes: {} });
STORAGE.forEach((f) => f({ key: 'romp:settings' }));
out.fleetOn = { cls: CLS.has('po-fleet'), chat: last('chat'), hidden: hidden(), grew: GREW.slice(), store: JSON.parse(STORE['romp-panes'] || 'null'), src: src() };
window.__rompPaneToggle('fleet');
out.fleetRailOff = { cls: CLS.has('po-fleet'), chat: last('chat'), store: JSON.parse(STORE['romp-panes'] || 'null') };
STORAGE.forEach((f) => f({ key: 'romp:settings' }));   // a save that changes no pane's setting moves nothing
out.fleetStays = { cls: CLS.has('po-fleet'), grew: GREW.slice() };
console.log(JSON.stringify(out));
"""


# ── the link reaches every shim-bearing iframe (D3, review round 1, 2026-09-18) ──────────────────────────
# The boot and toggle apply (broadcast) tell the six pane frames the panes word, whose link field is the shell socket's
# state. The re-tell the shell socket makes on its open, close and abandon (__rompPanesTell, also the mobile script's
# tab switch) is the one that carries a CHANGED link, so it reaches every iframe in the document: the pane frames as
# the panes word, the others (the settings frame, a split chat column) as a link word of their own, {romp:'link',link},
# since a panes word would replace a chat column's pane set wholesale (render.ts). Before this the shell's link-up
# reached the six pane frames alone and a split column or the settings frame ended its await on the shim's 5 s poll.
# The two later-loading frames get load hooks: the settings frame (in the markup at boot, loaded when the gear opens)
# and a split column (made by _LANDING_SPLIT_JS, which dispatches romp-chat-cols with the frame at creation).
_LINK_SEED = r"""
STORE['romp:settings'] = JSON.stringify({ showFilesControl: true });
const EXTRA = {};
const recorder = (id) => ({ id, contentWindow: { postMessage: (m) => { (POSTED[id] = POSTED[id] || []).push(JSON.parse(JSON.stringify(m))); } },
  addEventListener: (ev, f) => { if (ev === 'load') (LOADS[id] = LOADS[id] || []).push(f); } });
['f-settings', 'f-chat-2'].forEach((id) => { EXTRA[id] = recorder(id); });
KEYS.forEach((k) => { frames['f-' + k].id = 'f-' + k; });   // the served iframes carry their ids
document.querySelectorAll = (sel) => (sel === 'iframe' ? KEYS.map((k) => frames['f-' + k]).concat(Object.values(EXTRA)) : []);
document.getElementById = (id) => frames[id] || EXTRA[id] || null;
const WINL = {};
global.addEventListener = (ev, f) => { if (ev === 'storage') STORAGE.push(f); (WINL[ev] = WINL[ev] || []).push(f); };
let LINK = false; window.__rompLink = () => ({ up: LINK, connT: 0 });   // the shell socket's publication (_LANDING_MOBILE_JS)
"""
_LINK_DRIVER = r"""
const out = {};
const posted = (id) => (POSTED[id] || []).slice();
const counts = () => Object.fromEntries(KEYS.map((k) => [k, (POSTED[k] || []).length]));
out.boot = { settings: posted('f-settings'), chat2: posted('f-chat-2'), chatLink: (POSTED.chat || []).slice(-1)[0].link, counts: counts() };
LINK = true; window.__rompPanesTell();   // the shell socket opens: its re-tell carries the link to EVERY iframe
out.up = { settings: posted('f-settings'), chat2: posted('f-chat-2'), chat: (POSTED.chat || []).slice(-1)[0], counts: counts() };
LINK = false; window.__rompPanesTell();  // and closes
out.down = { settings: posted('f-settings').slice(-1)[0], chat2: posted('f-chat-2').slice(-1)[0], chatLink: (POSTED.chat || []).slice(-1)[0].link };
(LOADS['f-settings'] || []).forEach((f) => f());   // the gear opens: the settings frame loads
out.settingsLoad = posted('f-settings').slice(-1)[0];
LINK = true;
const f3 = recorder('f-chat-3');
(WINL['romp-chat-cols'] || []).forEach((f) => f({ detail: { frame: f3, col: 3, open: true } }));   // the split script makes a column after boot
(LOADS['f-chat-3'] || []).forEach((f) => f());   // it loads
out.col3 = posted('f-chat-3');
(WINL['romp-chat-cols'] || []).forEach((f) => f({ detail: { col: 3, open: false } }));   // a close carries no frame: nothing to wire, nothing thrown
out.hooks = { settings: (LOADS['f-settings'] || []).length, col3: (LOADS['f-chat-3'] || []).length };
console.log(JSON.stringify(out));
"""


class LinkReachesEveryIframe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.keys = [k for k, _ in km._PANE_ORDER]
        cls.out = _run(_COLLAPSE_HARNESS.replace("__KEYS__", json.dumps(cls.keys)).replace("__SEED__", _LINK_SEED) + km._LANDING_COLLAPSE_JS + _LINK_DRIVER)

    def test_the_boot_apply_tells_the_pane_frames_alone(self):
        b = self.out["boot"]
        self.assertEqual(b["counts"], {k: 1 for k in self.keys}, "one panes word per pane frame at boot, as before")
        self.assertEqual(b["chatLink"], "down", "no shell socket open yet: the word reads the link down")
        self.assertEqual([b["settings"], b["chat2"]], [[], []], "the settings frame and the split column hear nothing at the boot apply (nothing changed for them)")

    def test_the_shell_sockets_re_tell_reaches_every_iframe_once_each(self):
        u = self.out["up"]
        self.assertEqual(u["chat"]["link"], "up", "a pane frame hears the panes word with the link up")
        self.assertEqual(u["chat"]["romp"], "panes")
        self.assertEqual(u["counts"], {k: 2 for k in self.keys}, "one word per pane frame per re-tell: the panes word, not a second link word")
        self.assertEqual(u["settings"], [{"romp": "link", "link": "up", "mob": False}], "the settings frame hears a link word of its own, once; it carries the layout too (review round 4, kernel-3), the desktop here")
        self.assertEqual(u["chat2"], [{"romp": "link", "link": "up", "mob": False}], "a split chat column too (no pane set on it: its routing set stays its own; the layout term is what its render.ts reads for the return hold)")
        d = self.out["down"]
        self.assertEqual([d["settings"], d["chat2"], d["chatLink"]], [{"romp": "link", "link": "down", "mob": False}, {"romp": "link", "link": "down", "mob": False}, "down"], "the close's re-tell reads down everywhere")

    def test_the_settings_frame_and_a_column_made_later_hear_the_link_when_they_load(self):
        self.assertEqual(self.out["settingsLoad"], {"romp": "link", "link": "down", "mob": False}, "the settings frame's load hook tells it the link as it stands")
        self.assertEqual(self.out["col3"], [{"romp": "link", "link": "up", "mob": False}], "a column the split script made after boot is wired by romp-chat-cols and hears the link at its load")
        self.assertEqual(self.out["hooks"], {"settings": 1, "col3": 1}, "one load hook each; a column close (no frame) wires nothing")


class OptionalPanes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.keys = [k for k, _ in km._PANE_ORDER]
        # this browser hid the Feed pane in the gear, and a phone was left on the Feed tab
        # the Files control is ON in this browser (off by default since T317b), so the driver's Files toggle is a control the
        # user asked for; every gear save below carries the key too, as the gear's whole-object save does
        seed = "STORE['romp:settings'] = JSON.stringify({ showFilesControl: true, panes: { feed: false } }); TAB = 'feed';"
        cls.out = _run(_COLLAPSE_HARNESS.replace("__KEYS__", json.dumps(cls.keys)).replace("__SEED__", seed) + km._LANDING_COLLAPSE_JS + _OPT_DRIVER)

    def test_a_pane_hidden_in_the_gear_is_not_in_the_dashboard_at_boot(self):
        b = self.out["boot"]
        self.assertEqual(b["chat"]["on"], {"chat": True, "timeline": True, "fleet": False, "waiting": False, "files": False}, "the broadcast omits the hidden pane's key")
        self.assertEqual(b["counts"], {"chat": 1, "timeline": 1, "fleet": 1, "feed": 0, "waiting": 1, "files": 1}, "the hidden pane is told nothing (it has no document)")
        self.assertEqual(b["src"], {"chat": "/chat", "timeline": "/timeline", "fleet": "/fleet", "feed": None, "waiting": None, "files": None},   # waiting and files: not optional (item 7 B), so the reconcile sets no src on the harness's frames; the mobile script, not run here, promotes them (LazyPanes)
                         "the shown optional panes load from data-src; the hidden one never gets a src")
        self.assertEqual(b["hidden"], {"chat": False, "timeline": False, "fleet": False, "feed": True, "waiting": False, "files": False}, "its rail button and phone tab are hidden")
        self.assertFalse(b["cls"], "no po-feed body class: the column is not shown")
        self.assertEqual(b["tabs"], ["chat"], "a phone left on the hidden pane's tab goes back to the chat")
        self.assertEqual(b["sets"], {"timeline": 1, "fleet": 1}, "src set once per shown pane")

    def test_the_rail_toggle_refuses_a_hidden_pane_and_the_persisted_set_omits_it(self):
        r = self.out["refused"]
        self.assertEqual(r["counts"]["chat"], 1, "no re-apply, no broadcast: nothing changed")
        self.assertFalse(r["cls"])
        f = self.out["files"]
        self.assertEqual(f["chat"]["on"], {"chat": True, "timeline": True, "fleet": False, "waiting": False, "files": True})
        self.assertNotIn("feed", f["store"], "romp-panes persists the set without the hidden key")

    def test_enabling_in_the_gear_loads_the_pane_and_restores_its_button_tab_and_key(self):
        e = self.out["enabled"]
        self.assertEqual(e["src"]["feed"], "/feed", "the storage event copies data-src to src")
        self.assertEqual(e["hidden"]["feed"], False)
        self.assertTrue(e["cls"], "the pane comes back with its default flag (on)")
        self.assertEqual(e["chat"]["on"], {"chat": True, "timeline": True, "fleet": False, "feed": True, "waiting": False, "files": True}, "the broadcast carries the key again")
        self.assertEqual(e["counts"]["feed"], 1, "the re-apply's broadcast reaches the iframe element (the page is still loading)")
        l = self.out["loaded"]
        self.assertEqual(l["counts"]["feed"], 2, "and its own load re-tells it, like any pane that boots after the shell")
        self.assertEqual(l["feed"]["on"]["feed"], True)

    def test_off_again_hides_without_unloading_and_on_again_never_reassigns_the_src(self):
        o = self.out["off"]
        self.assertNotIn("feed", o["chat"]["on"])
        self.assertFalse(o["cls"])
        self.assertTrue(o["hidden"]["feed"])
        self.assertEqual(o["src"]["feed"], "/feed", "a loaded pane keeps its document until the next dashboard load")
        b = self.out["back"]
        self.assertTrue(b["cls"], "the flag it had comes back")
        self.assertEqual(b["chat"]["on"]["feed"], True)
        self.assertEqual(b["sets"], {"timeline": 1, "fleet": 1, "feed": 1}, "src was set exactly once per pane across the whole run")

    def test_only_the_settings_key_or_a_cleared_store_re_reads_the_panes(self):
        self.assertEqual(self.out["otherKey"]["hidden"]["fleet"], False, "a storage event for another key does not re-read")
        self.assertIn("fleet", self.out["otherKey"]["chat"]["on"])
        self.assertEqual(self.out["cleared"]["hidden"]["fleet"], True, "a cleared store (key null) is read again")
        self.assertNotIn("fleet", self.out["cleared"]["chat"]["on"])

    def test_a_pane_turned_on_in_the_gear_comes_on_screen_and_the_rail_hides_it_from_there(self):
        # the Outline's rail default is off, so before this a re-enabled Outline got its button back and nothing else,
        # while the gear's row says the column and its button are gone when off (so back when on). At boot the stored
        # rail flag still rules (a pane the gear shows keeps the state the rail left it in)
        b = self.out["fleetBefore"]
        self.assertFalse(b["cls"], "the Outline was off screen (the boot default, then hidden by the cleared store)")
        self.assertEqual((b["store"] or {}).get("fleet"), False, "and its stored rail flag is off (the Files toggle's save wrote the set)")
        o = self.out["fleetOn"]
        self.assertTrue(o["cls"], "turned on in the gear: the column comes on screen")
        self.assertEqual(o["chat"]["on"]["fleet"], True, "and the panes are told")
        self.assertFalse(o["hidden"]["fleet"], "its rail button and phone tab are back")
        self.assertEqual(o["grew"], ["fleet"], "at a fair width, as the rail's bring-forward gives")
        self.assertEqual(o["store"]["fleet"], True, "persisted, so a reload keeps it")
        self.assertEqual(o["src"]["fleet"], "/fleet", "loaded at boot already: the src is not touched")
        r = self.out["fleetRailOff"]
        self.assertFalse(r["cls"], "the rail toggle hides it from there")
        self.assertEqual(r["store"]["fleet"], False)
        s = self.out["fleetStays"]
        self.assertFalse(s["cls"], "a gear save that changes no pane's setting does not bring it back")
        self.assertEqual(s["grew"], ["fleet"])
        self.assertEqual(self.out["boot"]["chat"]["on"]["fleet"], False, "at boot the stored rail flag rules (off by default)")
        js = km._LANDING_COLLAPSE_JS
        self.assertIn("po[k]=live?true:flagOf(k);", js)
        self.assertIn("reconcile(true);apply();", js, "the storage listener's reconcile is the live one")
        self.assertIn("reconcile();   // the optional panes", js, "the boot one is not")

    def test_the_markup_and_the_mechanism(self):
        html = km._landing()
        for k in ("fleet", "feed", "timeline"):
            self.assertIn("<iframe id=f-%s data-src=/%s>" % (k, k), html, "the optional pane is served without a src")
            self.assertNotIn("<iframe id=f-%s src=" % k, html)
        self.assertIn("<iframe id=f-chat class=m-on src=/chat>", html, "the chat is required and loads at once")
        self.assertIn("<iframe id=f-files data-src=/files>", html, "the Files pane keeps its rail toggle, not this switch; served without a src since stage 0 (2026-09-18), the mobile script promotes it (LazyPanes below)")
        self.assertIn("<iframe id=f-waiting data-src=/waiting>", html, "the Waiting pane is served without a src too (stage 0, 2026-09-18): the mobile script promotes it, at boot on the desktop and on its first tap on the phone (LazyPanes below)")
        js = km._LANDING_COLLAPSE_JS
        self.assertIn("OPT=['timeline','fleet','feed']", js)
        self.assertIn("SK='romp:settings'", js)
        self.assertIn("on[k]=p[k]!==false", js, "only an explicit false hides (settings.ts paneSet)")
        self.assertIn("f.setAttribute('src',f.getAttribute('data-src'))", js)
        self.assertIn("KEYS=ALL.filter(function(k){return k in po;})", js)
        self.assertLess(js.index("reconcile();   // the optional panes"), js.index("\n  apply();\n"), "reconciled before the first apply")
        self.assertIn(".rail-btn[hidden]{display:none}", html, "the author display:flex would otherwise defeat hidden")
        self.assertIn("#mtabs button[hidden]{display:none}", html)


# ── the mobile script ─────────────────────────────────────────────────────────────────────────────
_MOBILE_HARNESS = r"""
'use strict';
const TOGGLES = [], TELLS = [], MQL = [], MSGS = [], STORE = {};
let MATCHES = true, TAB = null;
global.window = global;
global.innerHeight = 844; global.innerWidth = 390; global.scrollY = 0;
global.scrollTo = () => {};
global.matchMedia = (q) => ({ get matches() { return MATCHES; }, query: q, addEventListener: (ev, f) => { if (ev === 'change') MQL.push(f); } });   // matches reads live, as a MediaQueryList's does
global.requestAnimationFrame = (f) => 1;
global.addEventListener = (ev, f) => { if (ev === 'message') MSGS.push(f); };   // the script's window-message arms (reveal, toggleFleet), driven below
global.visualViewport = { height: 844, scale: 1, addEventListener: () => {} };
const WSS = [], BADGES = [];   // the shell sockets the script dials; the icon badge calls (0 = cleared)
global.WebSocket = class { constructor() { this.readyState = 0; WSS.push(this); } send() {} };
Object.defineProperty(global, 'navigator', { configurable: true, value: {   // an installed app: badging exists (node's own navigator is getter-only)
  setAppBadge: (n) => { BADGES.push(n); return Promise.resolve(); }, clearAppBadge: () => { BADGES.push(0); return Promise.resolve(); } } });
let FEED_OFF = false;   // the gear's Panes section has the Feed pane off in this browser (the head script's reader, stubbed)
global.__rompPaneEnabled = (k) => !(k === 'feed' && FEED_OFF);
global.encodeURIComponent = (s) => s;
global.location = { protocol: 'http:', host: 'TESTHOST:1' };
global.sessionStorage = { getItem: () => 'wid1' };
global.setTimeout = () => 0;
global.setInterval = () => 0;   // D3 (2026-09-18): the shell socket's watchdog tick, a no-op here so node exits
const pane = (id) => ({ id, classList: { toggle: (c, on) => { TOGGLES.push([id, c, !!on]); } }, contentDocument: {},
  contentWindow: { addEventListener: () => {} }, addEventListener: () => {} });
const PANES = {};
['f-chat', 'f-fleet', 'f-feed', 'f-files', 'f-timeline'].forEach((id) => { PANES[id] = pane(id); });
const TAPS = {}, BUTTONS = {};
const button = (key) => BUTTONS[key] || (BUTTONS[key] = { hidden: false, getAttribute: (a) => (a === 'data-pane' ? key : null), classList: { toggle() {} },
  addEventListener: (ev, f) => { if (ev === 'click') TAPS[key] = f; } });
const BAR = { offsetHeight: 44, querySelectorAll: (sel) => (sel === 'button[data-pane]' ? [button('chat'), button('feed'), button('files')] : []) };
global.document = {
  visibilityState: 'visible',
  addEventListener: () => {},
  documentElement: { scrollTop: 0, style: { setProperty() {} } },
  body: { setAttribute: (a, v) => { if (a === 'data-tab') TAB = v; }, getAttribute: (a) => (a === 'data-tab' ? TAB : null) },
  getElementById: (id) => (id === 'mtabs' ? BAR : (PANES[id] || null)),
};
global.localStorage = { getItem: (k) => (k in STORE ? STORE[k] : null), setItem: (k, v) => { STORE[k] = v; } };
window.__rompPanesTell = () => TELLS.push(TAB);
"""
_MOBILE_DRIVER = r"""
const out = {};
out.boot = { tab: TAB, on: window.__rompMobileOn(), tells: TELLS.slice() };
TOGGLES.length = 0; TELLS.length = 0;
window.__rompMobileTab('files');
out.files = { tab: TAB, mOn: TOGGLES.filter((t) => t[1] === 'm-on' && t[2]).map((t) => t[0]), tells: TELLS.slice(), store: STORE['romp-mobile-tab'] };
TELLS.length = 0;
MQL.forEach((f) => f({}));                                 // the layout flips (a rotation across the breakpoint)
out.flip = { tells: TELLS.slice(), listeners: MQL.length };
MATCHES = false;
out.desktop = window.__rompMobileOn();
window.__rompMobileTab('nowhere');
out.unknown = { tab: TAB };
// the relay remembered a tab; the person's own tap on another tab drops that memory, the relay's own switch keeps it
window.__rompFilesTabFrom = 'chat'; TAPS.feed();
out.tap = { tab: TAB, from: window.__rompFilesTabFrom };
window.__rompFilesTabFrom = 'chat'; window.__rompMobileTab('files');
out.relaySwitch = { tab: TAB, from: window.__rompFilesTabFrom };
// a reveal aimed at the person (a feed card's tap into a session, the kernel's reveal) and the chat header's
// Outline pill (toggleFleet) arrive as window messages and are switches they made too
const arrive = (m) => MSGS.forEach((f) => f({ data: m }));
window.__rompFilesTabFrom = 'chat'; arrive({ romp: 'reveal', pane: 'feed' });
out.reveal = { tab: TAB, from: window.__rompFilesTabFrom, listeners: MSGS.length };
window.__rompFilesTabFrom = 'chat'; arrive({ romp: 'toggleFleet', to: 'chat' });
out.pill = { tab: TAB, from: window.__rompFilesTabFrom };
window.__rompFilesTabFrom = 'chat'; arrive({ romp: 'toggleFleet' });
out.pillOutline = { tab: TAB, from: window.__rompFilesTabFrom };
// a tab the pane controller hid (its pane is off in the gear's Panes section): not a place to go
TELLS.length = 0; BUTTONS.feed.hidden = true; window.__rompMobileTab('feed');
out.hiddenTab = { tab: TAB, tells: TELLS.slice(), store: STORE['romp-mobile-tab'] };
BUTTONS.feed.hidden = false; window.__rompMobileTab('feed');
out.shownAgain = { tab: TAB };
// the kernel's badge frame on the shell socket: the needs-you count paints the icon while the Feed pane is in this
// dashboard; with the pane off here (the gear's Panes section) the same frame clears it instead
const ws = WSS[0]; const frame = (m) => ws.onmessage({ data: JSON.stringify(m) });
frame({ type: 'badge', n: 3 });
FEED_OFF = true; frame({ type: 'badge', n: 4 });
frame({ type: 'badge', n: 0 });
FEED_OFF = false; frame({ type: 'badge', n: 2 });
frame({ type: 'badge', n: 0 });
out.badges = { sockets: WSS.length, calls: BADGES.slice() };
console.log(JSON.stringify(out));
"""


class MobileScriptDefault(unittest.TestCase):
    """The phone script with NO settings store (a fresh install): the Files control is off by default (T317b, the user
    2026-09-10), so its tab is hidden and a switch aimed at it (a relay, a stored tab) shows the chat instead."""
    @classmethod
    def setUpClass(cls):
        driver = r"""
const out = {};
out.boot = { tab: TAB };
window.__rompMobileTab('files');
out.files = { tab: TAB, store: STORE['romp-mobile-tab'] || null };
window.__rompMobileTab('feed');
out.feed = { tab: TAB };
console.log(JSON.stringify(out));
"""
        cls.out = _run(_MOBILE_HARNESS + km._LANDING_MOBILE_JS + driver)

    def test_a_switch_to_the_hidden_files_tab_shows_the_chat(self):
        self.assertEqual(self.out["files"]["tab"], "chat", "the Files tab is hidden by default: the chat shows instead")
        self.assertEqual(self.out["feed"]["tab"], "feed", "every other tab switches as ever")


class MobileScript(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # the Files control turned ON by its gear setting (off by default since T317b): the taps below land on a tab
        # the person asked for
        harness = _MOBILE_HARNESS.replace('const TOGGLES = [], TELLS = [], MQL = [], MSGS = [], STORE = {};', "const TOGGLES = [], TELLS = [], MQL = [], MSGS = [], STORE = { 'romp:settings': JSON.stringify({ showFilesControl: true }) };")
        assert harness != _MOBILE_HARNESS
        cls.out = _run(harness + km._LANDING_MOBILE_JS + _MOBILE_DRIVER)

    def test_the_layout_probe_answers_the_stylesheets_own_media_query(self):
        # one constant lays out the grid AND answers the JS, never two strings that can drift
        self.assertIn("@media " + km._MOBILE_MQ + "{", km._landing())
        self.assertIn("matchMedia(" + json.dumps(km._MOBILE_MQ) + ")", km._LANDING_MOBILE_JS)
        self.assertTrue(self.out["boot"]["on"], "the fake matchMedia matches: the phone layout")
        self.assertFalse(self.out["desktop"], "and reads live: unmatched is the desktop")
        # defined ABOVE the tab-bar lookup, so a desktop shell (no bar) still answers
        js = km._LANDING_MOBILE_JS
        self.assertLess(js.index("window.__rompMobileOn=mobileOn;"), js.index("\nvar bar=document.getElementById('mtabs');if(!bar)return;\n"))

    def test_the_boot_show_lands_on_the_chat_and_the_tab_switch_re_tells_the_panes(self):
        self.assertEqual(self.out["boot"]["tab"], "chat")
        self.assertEqual(self.out["boot"]["tells"], ["chat"], "the boot show re-tells too (a no-op before the collapse script parses)")
        self.assertEqual(self.out["files"]["tab"], "files")
        self.assertEqual(self.out["files"]["mOn"], ["f-files"], "exactly one pane wears m-on")
        self.assertEqual(self.out["files"]["tells"], ["files"], "the switch is the event: re-told once, after data-tab moved")
        self.assertEqual(self.out["files"]["store"], "files")
        self.assertEqual(self.out["unknown"]["tab"], "files", "a key the shell has no pane for switches nothing")

    def test_a_layout_flip_re_tells_the_panes(self):
        self.assertEqual(self.out["flip"]["listeners"], 2, "two change listeners on the media query: the re-tell, and the lazy panes' promotion on a flip to the desktop (stage 0, 2026-09-18)")
        self.assertEqual(self.out["flip"]["tells"], ["files"])

    def test_a_tab_tap_drops_the_relays_remembered_tab_and_the_relays_own_switch_keeps_it(self):
        # phone: the relay remembered 'chat' and switched to Files; the person taps Feed, works there, comes back
        # to Files and closes the file. Without this the close would jump them to Chat, a tab they left on their own.
        self.assertEqual(self.out["tap"], {"tab": "feed", "from": None})
        self.assertEqual(self.out["relaySwitch"], {"tab": "files", "from": "chat"}, "__rompMobileTab itself is the relay's path and keeps the memory")

    def test_a_reveal_and_the_chat_headers_outline_pill_drop_the_remembered_tab_too(self):
        # the same rule as the tap: the relay's memory serves the file's close only while the person has not
        # moved on their own; a reveal (the feed's tap into a session) and the header pill are their moves
        self.assertEqual(self.out["reveal"], {"tab": "feed", "from": None, "listeners": 1})
        self.assertEqual(self.out["pill"], {"tab": "chat", "from": None})
        self.assertEqual(self.out["pillOutline"], {"tab": "fleet", "from": None})

    def test_a_hidden_tab_is_skipped(self):
        # the pane controller hides the tab of a pane this browser does not show (the gear's Panes section, the
        # user 2026-09-10); a switch to it (a stale romp-mobile-tab, a reveal) must not land on a blank pane
        self.assertEqual(self.out["hiddenTab"], {"tab": "fleet", "tells": [], "store": "fleet"}, "nothing moved, nothing told, nothing persisted")
        self.assertEqual(self.out["shownAgain"]["tab"], "feed", "unhidden, the same switch lands")

    def test_the_badge_frame_paints_the_icon_only_while_the_feed_pane_is_here(self):
        # the user 2026-09-10: the count is the feed's needs-you column; a browser with the Feed pane off in the
        # gear's Panes section wears no badge from it. The kernel sends the frame as ever (nothing kernel-side
        # changes); the shell clears the icon on it here, so a count set before the pane was hidden does not linger
        b = self.out["badges"]
        self.assertEqual(b["sockets"], 1, "one shell socket")
        self.assertEqual(b["calls"], [3, 0, 0, 2, 0], "3 painted; 4 with the pane off clears; 0 clears; the pane back: 2 painted, 0 cleared")
        js = km._LANDING_MOBILE_JS
        self.assertIn("var bn=(window.__rompPaneEnabled&&!window.__rompPaneEnabled('feed'))?0:m.n;", js)
        self.assertIn("try{(bn?navigator.setAppBadge(bn):navigator.clearAppBadge())['catch'](function(e){});}catch(e){}}", js)

    def test_the_hook_is_exported_for_the_relay(self):
        self.assertIn("window.__rompMobileTab=show;", km._LANDING_MOBILE_JS)
        # the mobile script parses BEFORE the collapse script (its boot show() finds no teller yet; the boot
        # apply that follows tells the panes), and the relay's tab switch happens at message time, after both
        html = km._landing()
        self.assertLess(html.index("window.__rompMobileTab=show;"), html.index("window.__rompPanesTell=broadcastAll;"))   # broadcastAll since review round 1 of D3 (2026-09-18): the re-tell reaches every iframe


# ── the settings listener's arms ──────────────────────────────────────────────────────────────────
# The whole settings script runs (it registers the one message listener this drives); the rest of it
# finds no elements and does nothing. `mobile` answers __rompMobileOn; `tab` is the tab showing.
_ARMS_HARNESS = r"""
'use strict';
const LISTENERS = [], TOGGLES = [], TABS = [];
const POSTED = { 'f-files': [], 'f-feed': [], 'f-chat': [], 'f-settings': [] };
const FOCUSED = [], CLASSES = [];   // contentWindow.focus() calls by iframe id; body class toggles as [class, on]
let MOBILE = false, TAB = 'chat', FILES_READY = 'complete', FILES_LOADS = [], SETTINGS_LOADS = [];
// the served markup's attributes, per iframe id (getElementById hands out a fresh stub each call, so they live here):
// the settings iframe carries data-src, no src, and its document is the empty one until the page loads
const ATTRS = { 'f-settings': { 'data-src': '/settings' } };
let SETTINGS_URL = 'about:blank', FILES_URL = 'http://TESTHOST:1/files';   // FILES_URL: about:blank while the Files pane is a just-promoted lazy iframe (stage 0)
let SETTINGS_DEAD = false, SETTINGS_SETS = 0;   // SETTINGS_DEAD: the gear's frame committed an error page (contentDocument null, Chromium's failed fetch); SETTINGS_SETS: src assignments on the gear's iframe (review round 3, kernel-3)
let SETTINGS_APP;   // the settings page's shim marker (window.__rompApp, 'settings' once the real page has parsed; undefined for an error body the origin served at the url, review round 4, kernel-2)
const frame = (id) => ({ contentWindow: { postMessage: (m) => POSTED[id].push(JSON.parse(JSON.stringify(m))), focus: () => FOCUSED.push(id), get __rompApp() { return id === 'f-settings' ? SETTINGS_APP : id.slice(2); } },
  contentDocument: (id === 'f-settings' && SETTINGS_DEAD) ? null : { get readyState() { return id === 'f-files' ? FILES_READY : 'complete'; }, get URL() { return id === 'f-settings' ? SETTINGS_URL : id === 'f-files' ? FILES_URL : 'http://TESTHOST:1/' + id.slice(2); } },
  getAttribute: (a) => (ATTRS[id] && a in ATTRS[id] ? ATTRS[id][a] : null),
  setAttribute: (a, v) => { (ATTRS[id] = ATTRS[id] || {})[a] = v; if (id === 'f-settings' && a === 'src') SETTINGS_SETS++; },
  removeAttribute: (a) => { if (ATTRS[id]) delete ATTRS[id][a]; },
  addEventListener: (ev, f) => { if (ev === 'load' && id === 'f-files') FILES_LOADS.push(f); if (ev === 'load' && id === 'f-settings') SETTINGS_LOADS.push(f); },
  removeEventListener: (ev, f) => { if (id === 'f-files') FILES_LOADS = FILES_LOADS.filter((g) => g !== f); } });
global.window = global;
global.addEventListener = (ev, f) => { if (ev === 'message') LISTENERS.push(f); };
global.__rompPaneToggle = (k, on) => TOGGLES.push([k, on]);
global.__rompMobileTab = (t) => TABS.push(t);
global.__rompMobileOn = () => MOBILE;
let FEED_OFF = false;   // the gear's Panes section has the Feed pane off in this browser (the head script's reader, stubbed)
global.__rompPaneEnabled = (k) => !(k === 'feed' && FEED_OFF);
const stub = () => ({ style: {}, classList: { add() {}, remove() {}, toggle() {}, contains: () => false }, appendChild() {}, setAttribute() {}, addEventListener() {}, remove() {} });
global.document = {
  body: { classList: { toggle: (c, on) => CLASSES.push([c, !!on]), contains: (c) => c === 'po-chat' || c === 'po-feed' || c === 'po-timeline' },
          getAttribute: (a) => (a === 'data-tab' ? TAB : null), appendChild() {} },
  getElementById: (id) => (id in POSTED ? frame(id) : null),
  createElement: stub, documentElement: { style: { setProperty() {} } },
  querySelectorAll: () => [], querySelector: () => null, addEventListener() {},
};
global.localStorage = { getItem: () => null, setItem() {} };
global.sessionStorage = { getItem: () => 'wid1', setItem() {} };
global.location = { protocol: 'http:', host: 'TESTHOST:1', search: '', reload() {} };
global.fetch = () => new Promise(() => {});
global.setTimeout = () => 0; global.setInterval = () => 0; global.clearTimeout = () => {};
global.Event = class { constructor(t) { this.type = t; } };
"""
_ARMS_DRIVER = r"""
const send = (m) => LISTENERS.forEach((f) => f({ data: m }));
const snap = () => ({ toggles: TOGGLES.slice(), tabs: TABS.slice(), files: POSTED['f-files'].slice(), feed: POSTED['f-feed'].slice(),
  chat: POSTED['f-chat'].slice(), settings: POSTED['f-settings'].slice(), from: window.__rompFilesTabFrom === undefined ? 'undef' : window.__rompFilesTabFrom });
const reset = () => { TOGGLES.length = 0; TABS.length = 0; for (const k in POSTED) POSTED[k].length = 0; delete window.__rompFilesTabFrom; };
const SID = '__SID__';
const identity = { name: 'web', color: { bg: '#123456', fg: '#ffffff' } };
const out = { listeners: LISTENERS.length };
send({ romp: 'viewFile', pane: 'pane', path: '/repo/notes-api/src/app.py', sid: SID, identity });
out.desktop = snap(); reset();
send({ romp: 'viewFile', pane: 'pane', path: '/repo/notes-api/README.md', sid: 'TESTHOST:' + SID });
out.bare = snap(); reset();
MOBILE = true; TAB = 'chat';
send({ romp: 'viewFile', pane: 'pane', path: '/repo/notes-api/src/app.py', sid: SID, identity });
out.phone = snap();
send({ romp: 'filesViewerClosed' });
out.phoneClosed = snap();
send({ romp: 'filesViewerClosed' });
out.phoneClosedAgain = snap(); reset();
TAB = 'files';
send({ romp: 'viewFile', pane: 'pane', path: '/p', sid: SID });
out.already = snap(); reset();
MOBILE = false; window.__rompFilesTabFrom = 'chat';
send({ romp: 'filesViewerClosed' });
out.deskClosed = snap(); reset();
const probe = window.__rompMobileOn; delete window.__rompMobileOn;
send({ romp: 'viewFile', pane: 'pane', path: '/p', sid: SID });
out.noProbe = snap(); reset(); window.__rompMobileOn = probe;
send({ romp: 'viewFile', path: '/p', sid: SID });
out.noPane = snap(); reset();
send({ romp: 'browseFiles', path: '/repo/notes-api', sid: SID });
out.browse = snap(); reset();
// the Files page is still loading when the click arrives: the forward waits for the iframe's load, once
FILES_READY = 'loading';
send({ romp: 'viewFile', pane: 'pane', path: '/repo/notes-api/src/app.py', sid: SID, identity });
out.early = { toggles: TOGGLES.slice(), files: POSTED['f-files'].slice(), waiting: FILES_LOADS.length };
FILES_READY = 'complete'; FILES_LOADS.slice().forEach((f) => f());
out.loaded = { files: POSTED['f-files'].slice(), waiting: FILES_LOADS.length };
FILES_LOADS.slice().forEach((f) => f());
out.reloaded = { files: POSTED['f-files'].slice() }; reset();
// a LAZY Files pane on the phone (stage 0, 2026-09-18): the click's tab switch promotes the src, but the iframe still holds its initial
// about:blank (readyState complete) until the page commits: the forward waits for the page's load, never posts into the empty document
MOBILE = true; TAB = 'chat'; FILES_URL = 'about:blank'; FILES_READY = 'complete';
send({ romp: 'viewFile', pane: 'pane', path: '/repo/notes-api/src/app.py', sid: SID, identity });
out.lazyEarly = { tabs: TABS.slice(), files: POSTED['f-files'].slice(), waiting: FILES_LOADS.length };
FILES_URL = 'http://TESTHOST:1/files'; FILES_LOADS.slice().forEach((f) => f());
out.lazyLoaded = { files: POSTED['f-files'].slice(), waiting: FILES_LOADS.length }; reset();
FILES_URL = 'about:blank';   // …and the browse arm the same way
send({ romp: 'browseFiles', pane: 'pane', path: '/repo/notes-api', sid: SID, identity });
out.lazyBrowseEarly = { files: POSTED['f-files'].slice(), waiting: FILES_LOADS.length };
FILES_URL = 'http://TESTHOST:1/files'; FILES_LOADS.slice().forEach((f) => f());
out.lazyBrowseLoaded = { files: POSTED['f-files'].slice(), waiting: FILES_LOADS.length }; reset(); MOBILE = false;
send({ type: 'editorSelection', text: 'the auth check', sid: SID, src: 'src/app.py:12' });
out.seed = snap(); reset();
// the gear: a pane's ask and the shell's own opener both land in the settings iframe, never the feed's. The
// iframe is served with data-src: the FIRST ask gives it its src and waits for the page's load; a second ask
// while it waits is not queued (the page's opener toggles); the load delivers one open; from then on asks post
out.opener = typeof window.__rompOpenSettings;
send({ romp: 'openSettings' });
out.gearAsk = Object.assign(snap(), { src: ATTRS['f-settings'].src, waiting: SETTINGS_LOADS.length }); reset();
window.__rompOpenSettings();
out.gearAskAgain = Object.assign(snap(), { src: ATTRS['f-settings'].src, waiting: SETTINGS_LOADS.length }); reset();
SETTINGS_LOADS.slice().forEach((f) => f());   // the empty document's own load, if it comes late: not the page's
out.gearBlankLoad = snap(); reset();
SETTINGS_URL = 'http://TESTHOST:1/settings'; SETTINGS_APP = 'settings'; SETTINGS_LOADS.slice().forEach((f) => f());   // the page loads: committed at its url, its shim's marker set (window.__rompApp, the read the tap-time check makes since review round 4)
out.gearLoaded = snap(); reset();
window.__rompOpenSettings();
out.gearOpen = Object.assign(snap(), { src: ATTRS['f-settings'].src }); reset();
SETTINGS_LOADS.slice().forEach((f) => f());   // a later reload of the page replays nothing
out.gearReloaded = snap(); reset();
// kernel-3 (review round 3, 2026-09-19): the gear over a DEAD document. (a) Chromium's road: the fetch failed and the frame committed a
// cross-origin error page (contentDocument null; its load fired and posted into it, unheard); the next tap reads no document at TAP time,
// drops the src and fetches again, and the page's load delivers the open. (b) Firefox's and WebKit's road: no load event, the frame at its
// initial about:blank with the pending flag still up; the next tap reads about:blank and does the same. (c) the mirror: a committed document
// at /settings is never re-fetched, the ask posts at once.
SETTINGS_DEAD = true; const setsBefore = SETTINGS_SETS;
window.__rompOpenSettings();
out.gearDeadTap = Object.assign(snap(), { src: ATTRS['f-settings'].src, sets: SETTINGS_SETS - setsBefore, waiting: SETTINGS_LOADS.length });
SETTINGS_DEAD = false; SETTINGS_URL = 'http://TESTHOST:1/settings'; SETTINGS_APP = 'settings'; SETTINGS_LOADS.slice().forEach((f) => f());   // the re-fetched page loads (its shim's marker set)
out.gearDeadLoaded = Object.assign(snap(), { sets: SETTINGS_SETS - setsBefore }); reset();
SETTINGS_URL = 'about:blank'; SETTINGS_APP = undefined;   // (b) the never-committed frame (a failed navigation on Firefox or WebKit: no load event came)
window.__rompOpenSettings();
out.gearBlankTap = Object.assign(snap(), { src: ATTRS['f-settings'].src, sets: SETTINGS_SETS - setsBefore, waiting: SETTINGS_LOADS.length });
SETTINGS_URL = 'http://TESTHOST:1/settings'; SETTINGS_APP = 'settings'; SETTINGS_LOADS.slice().forEach((f) => f());
out.gearBlankLoaded = Object.assign(snap(), { sets: SETTINGS_SETS - setsBefore }); reset();
window.__rompOpenSettings();   // (c) the mirror: a committed document with the marker (the settings page) is not re-fetched
out.gearLiveTap = Object.assign(snap(), { sets: SETTINGS_SETS - setsBefore }); reset();
// (d) review round 4 (kernel-2): a same-origin document AT /settings with no marker, what the origin served in place of the page (the kernel's
// own 403 line under a stale cookie, a proxy's 502 body): not the page, so the tap drops the src and fetches again; the page's load delivers
// the open once its shim has set the marker. Before this the url alone read as live and the gear stayed dead across every tap.
ATTRS['f-settings'].src = '/settings'; SETTINGS_URL = 'http://TESTHOST:1/settings'; SETTINGS_APP = undefined;
window.__rompOpenSettings();
out.gearErrorBodyTap = Object.assign(snap(), { src: ATTRS['f-settings'].src, sets: SETTINGS_SETS - setsBefore, waiting: SETTINGS_LOADS.length });
SETTINGS_APP = 'settings'; SETTINGS_LOADS.slice().forEach((f) => f());   // the re-fetched page loads, marker set
out.gearErrorBodyLoaded = Object.assign(snap(), { sets: SETTINGS_SETS - setsBefore }); reset();
window.__rompOpenSettings();   // the mirror again over the marked page
out.gearErrorBodyMirror = Object.assign(snap(), { sets: SETTINGS_SETS - setsBefore }); reset();
// (e) review round 4 (correctness-2, extra6-2): the ask the re-fetched page's load delivers is the LATEST tap's, its tab and section with it. Before
// this the one load listener closed over the FIRST tap's open (and so its bare msg), so every re-fetch opened the gear at the first tap's tab and
// section whatever the tap that caused it named. A dead document, then a tap naming a tab and a section (the strip's tab-widgets gear, T379):
SETTINGS_DEAD = true;
window.__rompOpenSettings('chat', 'tab-widgets');
out.gearDeadTapNamed = Object.assign(snap(), { src: ATTRS['f-settings'].src, sets: SETTINGS_SETS - setsBefore, waiting: SETTINGS_LOADS.length });
SETTINGS_DEAD = false; SETTINGS_URL = 'http://TESTHOST:1/settings'; SETTINGS_APP = 'settings'; SETTINGS_LOADS.slice().forEach((f) => f());   // the re-fetched page loads
out.gearDeadNamedLoaded = Object.assign(snap(), { sets: SETTINGS_SETS - setsBefore }); reset();
// (f) a tap while the first fetch is still in flight (the frame at about:blank, no marker yet) that names a tab and a section: the restart's load
// posts the second tap's message, not the first's bare one (the same fix; the earlier code dropped the second tap's names entirely)
delete ATTRS['f-settings'].src; SETTINGS_URL = 'about:blank'; SETTINGS_APP = undefined;   // the gear as served, data-src alone, before any tap
window.__rompOpenSettings();
out.gearInFlightFirst = Object.assign(snap(), { src: ATTRS['f-settings'].src, sets: SETTINGS_SETS - setsBefore });
window.__rompOpenSettings('panes', 'files');
out.gearInFlightSecond = Object.assign(snap(), { src: ATTRS['f-settings'].src, sets: SETTINGS_SETS - setsBefore, waiting: SETTINGS_LOADS.length });
SETTINGS_URL = 'http://TESTHOST:1/settings'; SETTINGS_APP = 'settings'; SETTINGS_LOADS.slice().forEach((f) => f());   // the restarted fetch's page loads
out.gearInFlightLoaded = Object.assign(snap(), { sets: SETTINGS_SETS - setsBefore }); reset();
// the Feed pane off in this browser (the gear's Panes section): a browse ask naming no pane takes the Files pane's
// arm (the feed cannot be lifted), a browseClosed puts nothing back, and a phone gets the Files tab, not the feed's
FEED_OFF = true;
send({ romp: 'browseFiles', path: '/repo/notes-api', sid: SID });
out.browseFeedOff = Object.assign(snap(), { wasOff: window.__rompFeedWasOff === undefined ? 'undef' : window.__rompFeedWasOff }); reset();
window.__rompFeedWasOff = true;   // a browser lifted the feed, then the gear hid the pane before it closed
send({ romp: 'browseClosed' });
out.closedFeedOff = Object.assign(snap(), { wasOff: window.__rompFeedWasOff }); reset(); delete window.__rompFeedWasOff;
MOBILE = true; TAB = 'chat';
send({ romp: 'browseFiles', path: '/repo/notes-api', sid: SID });
out.browseFeedOffPhone = snap(); reset(); MOBILE = false;
FEED_OFF = false;
window.__rompFeedWasOff = true;
send({ romp: 'browseClosed' });
out.closedFeedOn = Object.assign(snap(), { wasOff: window.__rompFeedWasOff }); reset(); delete window.__rompFeedWasOff;
send({ romp: 'browseFiles', path: '/repo/notes-api', sid: SID });
out.browseFeedOn = snap(); reset();
// the gear's lift bridge: opening lifts the settings iframe and leaves the keyboard where it is; closing hides that
// iframe (the keyboard's document) and puts focus back in the chat
send({ romp: 'settings', on: true });
out.gearLifted = { focused: FOCUSED.slice(), classes: CLASSES.slice() }; FOCUSED.length = 0; CLASSES.length = 0;
send({ romp: 'settings', on: false });
out.gearClosed = { focused: FOCUSED.slice(), classes: CLASSES.slice() };
console.log(JSON.stringify(out));
"""


class RelayArms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        js = km._LANDING_SETTINGS_JS.replace("__ROMP_BOOT__", json.dumps("boot-1")).replace("__ROMP_LOADER__", json.dumps(""))
        cls.out = _run(_ARMS_HARNESS + js + _ARMS_DRIVER.replace("__SID__", SID))

    def test_the_script_registers_one_message_listener(self):
        self.assertEqual(self.out["listeners"], 1)

    def test_a_just_promoted_lazy_files_pane_gets_its_forward_after_its_page_loads_never_into_the_empty_document(self):
        # stage 0 (2026-09-18): on the phone the Files pane is lazy; the relay's tab switch promotes its src, but the iframe still holds
        # its initial about:blank, whose readyState is complete, until the page commits. Both arms wait for the page's load then.
        e = self.out["lazyEarly"]
        self.assertEqual(e["tabs"], ["files"], "the relay switched to the Files tab (which promotes the pane)")
        self.assertEqual(e["files"], [], "nothing posted into the empty document")
        self.assertEqual(e["waiting"], 1, "one load listener waits for the page")
        l = self.out["lazyLoaded"]
        self.assertEqual(len(l["files"]), 1, "the page's load delivers the one forward")
        self.assertEqual(l["files"][0]["path"], "/repo/notes-api/src/app.py")
        self.assertEqual(l["waiting"], 0, "the listener came off")
        b = self.out["lazyBrowseEarly"]
        self.assertEqual((b["files"], b["waiting"]), ([], 1), "the browse arm waits the same way")
        self.assertEqual([m["romp"] for m in self.out["lazyBrowseLoaded"]["files"]], ["browseFiles"])
        js = km._LANDING_SETTINGS_JS
        self.assertIn("try{if(ff&&ff.contentDocument&&ff.contentDocument.URL==='about:blank')rd='loading';}catch(e){}", js)
        self.assertIn("try{if(fb&&fb.contentDocument&&fb.contentDocument.URL==='about:blank')rdb='loading';}catch(e){}", js)
        self.assertIn("var rd='';try{rd=(ff&&ff.contentDocument)?ff.contentDocument.readyState:'';}catch(e){}\n  try{if(ff&&", js, "inserted after the upstream readiness read, before its wait")

    def test_desktop_a_pane_click_brings_the_files_pane_forward_and_forwards_the_identity(self):
        d = self.out["desktop"]
        self.assertEqual(d["toggles"], [["files", True]], "the Files pane comes forward; the feed is not touched")
        self.assertEqual(d["tabs"], [], "desktop: no mobile tab switch (the column is already visible)")
        self.assertEqual(d["from"], "undef", "and nothing to remember")
        self.assertEqual(d["files"], [{"romp": "viewFile", "path": "/repo/notes-api/src/app.py", "sid": SID,
                                       "identity": {"name": "web", "color": {"bg": "#123456", "fg": "#ffffff"}},
                                       "todoId": None, "at": None, "frag": None}], "a chat click names no todo, no place and no section; the forward says so")
        self.assertEqual(d["feed"], [], "nothing reaches the feed")
        self.assertEqual(d["chat"], [])
        # no identity on the relay: the forward carries null (never undefined), and the pane falls to the stub;
        # a remote session's prefixed sid rides through untouched
        b = self.out["bare"]
        self.assertEqual(b["files"], [{"romp": "viewFile", "path": "/repo/notes-api/README.md", "sid": "TESTHOST:" + SID, "identity": None,
                                       "todoId": None, "at": None, "frag": None}])

    def test_phone_the_relay_switches_to_the_files_tab_and_the_close_puts_the_person_back_once(self):
        p = self.out["phone"]
        self.assertEqual(p["tabs"], ["files"])
        self.assertEqual(p["from"], "chat", "the tab the click came from is remembered")
        self.assertEqual(p["toggles"], [["files", True]], "the desktop bring-forward still runs (keeps po in step)")
        c = self.out["phoneClosed"]
        self.assertEqual(c["tabs"], ["files", "chat"], "close: back to the remembered tab")
        self.assertIsNone(c["from"], "and the memory is consumed")
        self.assertEqual(self.out["phoneClosedAgain"]["tabs"], ["files", "chat"], "a second close with nothing remembered switches nothing")
        a = self.out["already"]
        self.assertEqual(a["tabs"], [], "already on the Files tab: nothing to switch")
        self.assertEqual(a["from"], "undef", "and nothing to remember")

    def test_desktop_close_drops_a_stale_memory_without_replaying_it(self):
        d = self.out["deskClosed"]
        self.assertEqual(d["tabs"], [])
        self.assertIsNone(d["from"], "dropped, never replayed later (a rotation to desktop between open and close)")

    def test_a_shell_without_the_layout_probe_does_not_throw(self):
        n = self.out["noProbe"]
        self.assertEqual(n["tabs"], [])
        self.assertEqual(len(n["files"]), 1, "the forward still happens")

    def test_a_view_file_naming_no_pane_is_not_relayed(self):
        # the chat opens in place for "here"; a message with no target is not this arm's and goes nowhere
        n = self.out["noPane"]
        self.assertEqual(n["files"], [])
        self.assertEqual(n["feed"], [])
        self.assertEqual(n["toggles"], [])

    def test_a_click_before_the_files_page_has_loaded_is_delivered_on_its_load_once(self):
        # the dashboard just opened (or a phone's hidden iframe boots late): a postMessage into a document whose
        # files.js has not registered its listener would be dropped with the pane brought forward empty
        e = self.out["early"]
        self.assertEqual(e["toggles"], [["files", True]], "the pane still comes forward at once")
        self.assertEqual(e["files"], [], "nothing is posted into a document that cannot hear it yet")
        self.assertEqual(e["waiting"], 1, "one load listener holds the click")
        l = self.out["loaded"]
        self.assertEqual(len(l["files"]), 1, "the load delivers it")
        self.assertEqual(l["files"][0]["path"], "/repo/notes-api/src/app.py")
        self.assertEqual(l["waiting"], 0, "and the listener is gone")
        self.assertEqual(len(self.out["reloaded"]["files"]), 1, "a later reload of the pane does not replay it")

    def test_the_gear_opens_in_the_settings_iframe_never_in_the_feed(self):
        # the gear lives on the /settings page (the user 2026-09-10): the shell's one opener posts into that
        # iframe, and a pane asking for the gear (the feed's login card, gear-host.ts openGear) is forwarded
        # there; the feed hears nothing and no pane is toggled (the settings iframe is not a pane)
        self.assertEqual(self.out["opener"], "function", "__rompOpenSettings is the shell's one opener")
        for k in ("gearAsk", "gearAskAgain", "gearBlankLoad", "gearLoaded", "gearOpen", "gearReloaded"):
            g = self.out[k]
            self.assertEqual(g["feed"], [], k + ": the feed page hosts no gear")
            self.assertEqual(g["toggles"], [], k + ": no pane moves")
            self.assertEqual(g["tabs"], [], k)
        self.assertEqual(self.out["gearLoaded"]["settings"], [{"romp": "openSettings"}], "the page's load delivers the open")
        self.assertEqual(self.out["gearOpen"]["settings"], [{"romp": "openSettings"}], "a later ask posts at once")

    def test_the_settings_page_loads_on_the_first_open_and_the_ask_waits_for_it(self):
        # the iframe is served with data-src (an eagerly loaded gear cost a kernel socket plus one per attached host on
        # every dashboard load, idle until opened): the first ask copies it to src and holds the open for the page's
        # load, since a message into a document still on its way is dropped and the first click would show nothing
        a = self.out["gearAsk"]
        self.assertEqual(a["src"], "/settings", "the first ask gives the iframe its src")
        self.assertEqual(a["settings"], [], "nothing is posted into a page that has not loaded")
        self.assertEqual(a["waiting"], 1, "one load listener holds the ask")
        b = self.out["gearAskAgain"]
        self.assertEqual(b["settings"], [], "a second ask while the page loads is not queued: the page's opener toggles, two would open and close it")
        self.assertEqual(b["waiting"], 1, "and adds no listener (one load listener for the element's life, review round 3)")
        self.assertEqual(b["src"], "/settings", "the src stands (a second tap over a frame still at about:blank restarts the fetch, round 3's dead-document rule; the page still opens once, at its load)")
        self.assertEqual(self.out["gearBlankLoad"]["settings"], [], "the empty document's own load event is not the page's")
        self.assertEqual(self.out["gearLoaded"]["settings"], [{"romp": "openSettings"}], "the page's load delivers the open, once")
        self.assertEqual(self.out["gearOpen"]["src"], "/settings")
        self.assertEqual(self.out["gearReloaded"]["settings"], [], "a later load replays nothing")
        self.assertIn("<iframe id=f-settings data-src=/settings title=Settings></iframe>", km._landing(), "served without a src")

    def test_the_gear_over_a_dead_document_fetches_again_at_the_next_tap_and_a_live_document_is_not_re_fetched(self):
        # kernel-3 (review round 3, 2026-09-19): HIGH 2's failed-load class reaches the settings gear, the one other data-src iframe in the
        # shell. Before: one failed fetch left the gear unopenable for the page's life (Chromium: src set, contentDocument null, sPend
        # cleared by the error page's load, every later ask posted into the dead document; Firefox and WebKit: no load event, sPend true
        # forever, every later ask returned). Now the tap reads the document: none, or about:blank, drops the src and fetches again; the
        # page's load delivers the open. No timer: the next tap is the event. A committed document is never re-fetched (the mirror).
        d = self.out["gearDeadTap"]
        self.assertEqual((d["src"], d["sets"], d["settings"], d["waiting"]), ("/settings", 1, [], 1), "no document at the tap: the src is dropped and set again (one more assignment), nothing posted into the dead frame, still one load listener")
        l = self.out["gearDeadLoaded"]
        self.assertEqual((l["settings"], l["sets"]), ([{"romp": "openSettings"}], 1), "the re-fetched page's load delivers the open, once")
        b = self.out["gearBlankTap"]
        self.assertEqual((b["src"], b["sets"], b["settings"]), ("/settings", 2, []), "the frame at about:blank (Firefox's and WebKit's failed navigation: no load event ever came): the same re-fetch")
        self.assertEqual(self.out["gearBlankLoaded"]["settings"], [{"romp": "openSettings"}], "…and its load delivers the open")
        m = self.out["gearLiveTap"]
        self.assertEqual((m["sets"], m["settings"]), (2, [{"romp": "openSettings"}]), "the mirror: a committed document at /settings with the shim's marker (the settings page) is not re-fetched, the ask posts at once")
        # review round 4 (kernel-2): the tap-time check reads the marker too, the read docState makes for its `app` answer (kernel.py, function
        # docState): a same-origin document at
        # /settings with no marker (an error body the origin served: the kernel's 403 line, a proxy's 502) is not the page and is re-fetched;
        # before this the url alone read as live and the gear stayed dead across every tap while the body stood
        e = self.out["gearErrorBodyTap"]
        self.assertEqual((e["src"], e["sets"], e["settings"], e["waiting"]), ("/settings", 3, [], 1), "a same-origin document at /settings without the marker at the tap: the src is dropped and set again (one more assignment), nothing posted into it, still one load listener")
        self.assertEqual((self.out["gearErrorBodyLoaded"]["settings"], self.out["gearErrorBodyLoaded"]["sets"]), ([{"romp": "openSettings"}], 3), "the re-fetched page's load, its marker set, delivers the open once")
        self.assertEqual((self.out["gearErrorBodyMirror"]["sets"], self.out["gearErrorBodyMirror"]["settings"]), (3, [{"romp": "openSettings"}]), "the marked page is not re-fetched")
        js = km._LANDING_SETTINGS_JS
        self.assertIn("if(f.getAttribute('src')){var live=false;try{var sd=f.contentDocument;live=!!(sd&&sd.URL&&sd.URL!=='about:blank'&&f.contentWindow&&typeof f.contentWindow.__rompApp==='string');}catch(e){}", js, "the tap-time read, before the promotion branch: the url and the marker")
        self.assertIn("if(!live){try{f.removeAttribute('src');}catch(e){}sPend=false;}}", js)
        self.assertLess(js.index("var live=false;"), js.index("if(!f.getAttribute('src')){var u=f.getAttribute('data-src');"), "…so the promotion below re-fetches in the same tap")

    def test_the_re_fetched_pages_load_delivers_the_latest_taps_ask_with_its_tab_and_section(self):
        # review round 4 (2026-09-19, correctness-2 and extra6-2): the gear's one load listener (armed for the element's life since round 3) closed
        # over the FIRST tap's open, and so its msg, so a re-fetch after a dead document, or the restart a tap during the first fetch makes, opened
        # the gear at the first tap's tab and section whatever the later tap named. The tap that fetches records its own poster (sOpen, written on
        # a fork line beside the upstream promotion line) and the listener posts and clears it: the load delivers the LATEST tap's ask.
        d = self.out["gearDeadTapNamed"]
        self.assertEqual((d["src"], d["sets"], d["settings"], d["waiting"]), ("/settings", 4, [], 1), "a dead document, then a tap naming a tab and a section: re-fetched (one more assignment), nothing posted into the dead frame, still one listener: %r" % (d,))
        self.assertEqual(self.out["gearDeadNamedLoaded"]["settings"], [{"romp": "openSettings", "tab": "chat", "section": "tab-widgets"}], "the re-fetched page's load delivers THAT tap's ask, tab and section with it (before: the first tap's bare message)")
        f1 = self.out["gearInFlightFirst"]
        self.assertEqual((f1["src"], f1["sets"], f1["settings"]), ("/settings", 5, []), "a first tap on the parked gear fetches: %r" % (f1,))
        f2 = self.out["gearInFlightSecond"]
        self.assertEqual((f2["src"], f2["sets"], f2["settings"], f2["waiting"]), ("/settings", 6, [], 1), "a second tap while the fetch is in flight (about:blank, no marker) restarts it and posts nothing yet: %r" % (f2,))
        self.assertEqual(self.out["gearInFlightLoaded"]["settings"], [{"romp": "openSettings", "tab": "panes", "section": "files"}], "the restarted fetch's load delivers the SECOND tap's ask (before: the first's, its names dropped)")
        js = km._LANDING_SETTINGS_JS
        self.assertIn("var sPend=false,sArmed=false,sOpen=null;", js, "the pending ask's poster lives in the shared scope the listener reads")
        self.assertIn("if(sPend){sPend=false;var o=sOpen;sOpen=null;if(o)o();}});}return;}", js, "the one listener posts the recorded ask and clears it")
        up = "if(!f.getAttribute('src')){var u=f.getAttribute('data-src');if(!u)return;sPend=true;f.setAttribute('src',u);"
        self.assertIn(up, js, "the upstream promotion line is intact")
        self.assertLess(js.index(up), js.index("\n  sOpen=open;"), "the ask is recorded on the fork's own line right after it")
        self.assertLess(js.index("\n  sOpen=open;"), js.index("if(!sArmed){sArmed=true;"), "…and before the listener is armed")

    def test_closing_the_gear_puts_the_keyboard_back_in_the_chat(self):
        # the gear's document is the hidden settings iframe, lifted while open; closing hides it, which drops focus
        # onto the shell body (a keystroke there reaches no pane), so the bridge focuses the chat, the dashboard's
        # default focus. Opening moves nothing: the gear takes the keyboard itself.
        o = self.out["gearLifted"]
        self.assertEqual(o["classes"], [["settings-open", True]])
        self.assertEqual(o["focused"], [], "opening leaves focus alone")
        c = self.out["gearClosed"]
        self.assertEqual(c["classes"], [["settings-open", False]])
        self.assertEqual(c["focused"], ["f-chat"], "closing focuses the chat iframe's window, once")

    def test_the_feeds_browse_relay_and_the_quote_seed_forward_are_untouched(self):
        b = self.out["browse"]
        self.assertEqual(b["feed"], [{"romp": "browseFiles", "path": "/repo/notes-api", "sid": SID}])
        self.assertEqual(b["tabs"], ["feed"], "the feed's browser still switches a phone to the Feed tab")
        self.assertEqual(b["files"], [])
        s = self.out["seed"]
        self.assertEqual(s["chat"], [{"type": "editorSelection", "text": "the auth check", "sid": SID, "src": "src/app.py:12"}])

    def test_with_the_feed_pane_off_here_a_browse_ask_takes_the_files_pane_and_nothing_lifts_or_restores_the_feed(self):
        # the user 2026-09-10: the Feed pane hidden in the gear's Panes section is not in this dashboard, so the browse
        # relay cannot lift it; the ask goes to the one file browser the dashboard has, the Files pane, and the was-off
        # restore (a flag set while the pane was still here) moves no pane. The kernel is not party to any of this.
        b = self.out["browseFeedOff"]
        self.assertEqual(b["files"], [{"romp": "browseFiles", "path": "/repo/notes-api", "sid": SID, "identity": None}], "the Files pane's arm takes it")
        self.assertEqual(b["feed"], [], "nothing is posted into a pane that is not here")
        self.assertEqual(b["toggles"], [["files", True]], "the Files pane comes forward; the feed is never lifted")
        self.assertEqual(b["wasOff"], "undef", "no was-off flag: there is nothing to put back later")
        self.assertEqual(b["tabs"], [], "desktop: no tab switch")
        c = self.out["closedFeedOff"]
        self.assertEqual(c["toggles"], [], "browseClosed with the pane off: no pane moves")
        self.assertFalse(c["wasOff"], "…and the stale flag is dropped, never replayed")
        p = self.out["browseFeedOffPhone"]
        self.assertEqual(p["tabs"], ["files"], "a phone goes to the Files tab, not the feed's")
        self.assertEqual(len(p["files"]), 1)
        self.assertEqual(p["feed"], [])
        # the pane back on: the feed's route is as it was, the restore included
        self.assertEqual(self.out["closedFeedOn"]["toggles"], [["feed", False]])
        self.assertFalse(self.out["closedFeedOn"]["wasOff"])
        self.assertEqual(self.out["browseFeedOn"]["feed"], [{"romp": "browseFiles", "path": "/repo/notes-api", "sid": SID}])
        self.assertEqual(self.out["browseFeedOn"]["files"], [])
        # the source: the pane arm's head admits a pane-less ask while the feed is off here; the restore is guarded
        js = km._LANDING_SETTINGS_JS
        self.assertIn("if(m.romp==='browseFiles'&&(m.pane==='pane'||!feedHere())){var fb=document.getElementById('f-files');", js)
        self.assertIn("if(feedHere())try{window.__rompPaneToggle&&window.__rompPaneToggle('feed',false);}catch(e){}}", js)
        self.assertIn("function feedHere(){return !(window.__rompPaneEnabled&&!window.__rompPaneEnabled('feed'));}", js)


# ── the head script's reader of the gear's Panes setting ─────────────────────────────────────────
# window.__rompPaneEnabled(k): is pane k in this browser's dashboard at all (romp:settings.panes, the gear's
# Panes section; only an explicit false hides). Every shell script that acts on the feed at an event asks it:
# the badge frame, a Log entry's click, a notification's landing, a browse ask. Defined in the HEAD, before any
# iframe or body script, and read from the store on every call.
HELPER = ("window.__rompPaneEnabled=function(k){try{var s=JSON.parse(localStorage.getItem('romp:settings')||'{}'),p=s&&s.panes;"
          "return !(p&&typeof p==='object'&&p[k]===false);}catch(e){return true;}};")
_HELPER_DRIVER = r"""
'use strict';
const STORE = {};
global.window = global;
global.localStorage = { getItem: (k) => (k in STORE ? STORE[k] : null) };
__HELPER__
const ask = () => ['timeline', 'fleet', 'feed', 'chat'].map((k) => window.__rompPaneEnabled(k));
const out = {};
out.empty = ask();                                                       // no store: every pane shown
STORE['romp:settings'] = JSON.stringify({ theme: 'dark' });              // an older store without panes
out.older = ask();
STORE['romp:settings'] = JSON.stringify({ panes: { feed: false } });     // the gear hid the feed
out.feedOff = ask();
STORE['romp:settings'] = JSON.stringify({ panes: { feed: 0, fleet: null, timeline: 'no' } });   // falsy but not false: shown
out.falsy = ask();
STORE['romp:settings'] = '{not json';                                    // a corrupt store: every pane shown
out.corrupt = ask();
STORE['romp:settings'] = JSON.stringify({ panes: 'feed' });              // a non-object panes value: shown
out.notObject = ask();
console.log(JSON.stringify(out));
"""


class PaneEnabledReader(unittest.TestCase):
    def test_the_head_defines_it_before_any_iframe_and_the_scripts_ask_it(self):
        html = km._landing()
        self.assertEqual(html.count(HELPER), 1)
        self.assertLess(html.index(HELPER), html.index("<iframe"), "defined in the head, before the first iframe")
        self.assertLess(html.index(HELPER), html.index("<body"))
        self.assertEqual(html.count("<script>"), 22, "the head's existing script carries it: no new script element "
                         "(main's 20 + the chat split's own script, tests/test_chat_split.py — 2026-09-11; +1 2026-09-19: the desktop promotion of the "
                         "Waiting and Files panes, _LANDING_DESKTOP_PANES_JS, its own script so a throw in the mobile script cannot strand a desktop pane, review round 1 of the lazy panes)")
        for js in (km._LANDING_ERRS_JS, km._LANDING_MOBILE_JS, km._LANDING_REVEAL_JS, km._LANDING_SETTINGS_JS):
            self.assertIn("window.__rompPaneEnabled&&!window.__rompPaneEnabled('feed')", js, "absent helper = every pane shown")

    def test_only_an_explicit_false_hides_and_a_corrupt_store_hides_nothing(self):
        out = _run(_HELPER_DRIVER.replace("__HELPER__", HELPER))
        self.assertEqual(out["empty"], [True, True, True, True])
        self.assertEqual(out["older"], [True, True, True, True])
        self.assertEqual(out["feedOff"], [True, True, False, True])
        self.assertEqual(out["falsy"], [True, True, True, True])
        self.assertEqual(out["corrupt"], [True, True, True, True])
        self.assertEqual(out["notObject"], [True, True, True, True])


# ── the lazy panes (stage 0 of the reconnect design, 2026-09-18) ─────────────────────────────────────────
# On the phone layout only the chat, the feed and the stored tab load at boot; every other pane loads on its first show (a tap,
# a reveal, a relay's switch), with the src set BEFORE the re-tell and exactly once, and the shell paints its loader over the
# pane area until the iframe's load event. The desktop keeps its eager boot. Both scripts run here in the served order (the
# mobile script, then the pane controller) against fakes with attributes, a .pane parent per iframe and a body class list, so
# the promotion, the parking of data-src under data-lazy-src, the controller's untouched promotion line and the loading state
# are all executed. Synthetic only: TESTHOST, no session data.
_LAZY_HARNESS = r"""
'use strict';
const STORE = {}, SETS = {}, LOG = [], POSTED = {}, LOADS = {}, TIMERS = [], MQL = [], MSGS = [], STORAGE = [], SOCKS = [], CLICKS = [];
const MSG = { textContent: '', role: 'alert' }, LOADEL = { addEventListener: (ev, f) => { if (ev === 'click') CLICKS.push(f); } };   // #pane-load-msg and #pane-load (the failed state's message and its tap-to-retry, review round 1)
let ACTIVE = 'body';   // document.activeElement's stand-in (review round 4, ui-1): 'retry' once the button's focus() lands on a SHOWN button; back to 'body' when the button is hidden, the way every engine drops focus off a hidden control (the served keyboard witness reads BODY there)
const RETRY = { _h: true, clicks: [], focus: () => { if (!RETRY._h) ACTIVE = 'retry'; }, get hidden() { return RETRY._h; }, set hidden(v) { RETRY._h = !!v; if (RETRY._h && ACTIVE === 'retry') ACTIVE = 'body'; },
  addEventListener: (ev, f) => { if (ev === 'click') RETRY.clicks.push(f); } };   // #pane-load-retry, the failed state's button (review round 3, ui-1): hidden until the failed paint
let MATCHES = __PHONE__;
const KEYS = __KEYS__;
const attrsOf = (k) => ((k === 'chat') ? { src: '/' + k } : { 'data-src': '/' + k });   // the served markup: the chat alone ships src
const cls = (set) => ({ add: (c) => set.add(c), remove: (c) => set.delete(c), contains: (c) => set.has(c),
  toggle: (c, on) => { if (on === undefined) on = !set.has(c); if (on) set.add(c); else set.delete(c); return on; } });
const frames = {}, DIVS = {};
KEYS.forEach((k) => {
  const attrs = attrsOf(k); const divCls = new Set(['pane']);
  DIVS[k] = { classList: cls(divCls), cls: divCls };
  frames['f-' + k] = { id: 'f-' + k, attrs, parentNode: DIVS[k], contentDocument: {}, classList: cls(new Set()),
    contentWindow: { postMessage: (m) => { (POSTED[k] = POSTED[k] || []).push(JSON.parse(JSON.stringify(m))); }, addEventListener() {} },
    getAttribute: (a) => (a in attrs ? attrs[a] : null),
    setAttribute: (a, v) => { attrs[a] = v; if (a === 'src') { SETS[k] = (SETS[k] || 0) + 1; LOG.push('src:' + k); } },
    removeAttribute: (a) => { delete attrs[a]; },
    addEventListener: (ev, f) => { if (ev === 'load') (LOADS[k] = LOADS[k] || []).push(f); } };
});
const BTNS = {};
KEYS.forEach((k) => { BTNS[k] = { hidden: false, title: '', getAttribute: (a) => (a === 'data-pane' ? k : null), classList: cls(new Set()), addEventListener() {} }; });
const BODY_CLS = new Set(['po-chat', 'po-feed', 'po-timeline']); let TAB = null;
global.window = global;
global.innerHeight = 844; global.innerWidth = 390; global.scrollY = 0; global.scrollTo = () => {};
global.matchMedia = (q) => ({ get matches() { return MATCHES; }, query: q, addEventListener: (ev, f) => { if (ev === 'change') MQL.push(f); } });
global.requestAnimationFrame = (f) => 1;
global.addEventListener = (ev, f) => { if (ev === 'message') MSGS.push(f); if (ev === 'storage') STORAGE.push(f); };
global.dispatchEvent = () => true;
global.Event = class { constructor(t) { this.type = t; } };
global.visualViewport = { height: 844, scale: 1, addEventListener: () => {} };
global.WebSocket = class { constructor(u) { this.url = u; this.readyState = 0; this.sent = []; SOCKS.push(this); } send(s) { this.sent.push(s); } close() {} };   // the shell socket: its sends are kept (a client-diag row, once a driver opens it)
global.location = { protocol: 'http:', host: 'TESTHOST:1', search: '' };
global.URLSearchParams = class { get() { return null; } };
global.sessionStorage = { getItem: () => 'wid1' };
global.setTimeout = (f, ms) => { TIMERS.push({ f, ms }); return TIMERS.length; };
global.setInterval = () => 0;
global.localStorage = { getItem: (k) => (k in STORE ? STORE[k] : null), setItem: (k, v) => { STORE[k] = v; } };
global.__rompPaneEnabled = (k) => { try { const s = JSON.parse(STORE['romp:settings'] || '{}'), p = s && s.panes; return !(p && typeof p === 'object' && p[k] === false); } catch (e) { return true; } };   // the head script's reader, as served
const BAR = { offsetHeight: 44, querySelectorAll: (sel) => (sel === 'button[data-pane]' ? KEYS.map((k) => BTNS[k]) : []) };
global.document = {
  visibilityState: 'visible', addEventListener: () => {},
  documentElement: { scrollTop: 0, style: { setProperty() {} } },
  body: { classList: cls(BODY_CLS), setAttribute: (a, v) => { if (a === 'data-tab') TAB = v; }, getAttribute: (a) => (a === 'data-tab' ? TAB : null) },
  querySelectorAll: (sel) => { if (sel === '.rail-btn[data-pane]') return KEYS.map((k) => BTNS[k]); if (sel === 'iframe') return KEYS.map((k) => frames['f-' + k]); const m = /data-pane=(\w+)/.exec(sel); return m && BTNS[m[1]] ? [BTNS[m[1]]] : []; },
  getElementById: (id) => (id === 'mtabs' ? BAR : id === 'pane-load-msg' ? MSG : id === 'pane-load' ? LOADEL : id === 'pane-load-retry' ? RETRY : (frames[id] || null)),
};
__SEED__
"""
_LAZY_TOOLS = r"""
const src = () => Object.fromEntries(KEYS.map((k) => [k, frames['f-' + k].getAttribute('src')]));
const lazy = () => Object.fromEntries(KEYS.map((k) => [k, frames['f-' + k].getAttribute('data-lazy-src')]));
const dataSrc = () => Object.fromEntries(KEYS.map((k) => [k, frames['f-' + k].getAttribute('data-src')]));
const loading = () => KEYS.filter((k) => DIVS[k].cls.has('loading')).sort();
const hidden = () => Object.fromEntries(KEYS.map((k) => [k, BTNS[k].hidden]));
const words = (k) => (POSTED[k] || []).map((m) => m.on && m.on[k]);
const divCls = (k) => Array.from(DIVS[k].cls).filter((c) => c !== 'pane').sort();
const diagRows = (what) => SOCKS.flatMap((s) => s.sent.map((x) => JSON.parse(x))).filter((m) => m.type === 'clientDiag' && m.surface === 'shell' && m.what === what).map((m) => m.data);
const backstops = () => TIMERS.filter((t) => t.ms === 30000).forEach((t) => t.f());   // every 30 s backstop armed so far (a stale promotion's is inert on its token)
const shimUp = (k, url) => { frames['f-' + k].contentDocument = { URL: url || ('http://TESTHOST:1/' + k) }; frames['f-' + k].contentWindow.__rompApp = k; };   // the pane's OWN document: committed at its url with the pane shim run in its window (window.__rompApp, as the served shim sets it while parsing); docState's 'app'
const servedDoc = (k) => { frames['f-' + k].contentDocument = { URL: 'http://TESTHOST:1/' + k, documentElement: { getAttribute: (a) => (a === 'data-romp-served' ? '200' : null) } }; };   // a 200 the kernel served at the pane's url with NO shim (its "needs the ui/ modules" page): the stamp Handler._send writes on every text/html 200 (data-romp-served=200 on <html>); docState's 'doc', shown as served and said (review round 4 narrowed the shown-as-served rule to this)
const otherDoc = (k) => { frames['f-' + k].contentDocument = { URL: 'http://TESTHOST:1/' + k, documentElement: { getAttribute: () => null } }; };   // a same-origin document at the pane's url with neither the marker nor the stamp: what the kernel did not serve as a 200 (its 403 line under a stale cookie, a text/plain body the browser wraps in a bare <html>; its 500 page; a proxy's 502 body); docState's 'other', a failure (review round 4, kernel-1)
const out = {};
const origTell = window.__rompPanesTell; window.__rompPanesTell = () => { LOG.push('tell'); origTell(); };
"""
_LAZY_PHONE_DRIVER = _LAZY_TOOLS + r"""
out.boot = { tab: TAB, src: src(), lazy: lazy(), dataSrc: dataSrc(), sets: Object.assign({}, SETS), loading: loading(), bodyLoading: BODY_CLS.has('pane-loading'), hidden: hidden(), promote: typeof window.__rompPanePromote };
LOG.length = 0;
window.__rompMobileTab('waiting');   // the first tap on the Waiting tab
out.tap = { tab: TAB, src: src(), lazy: lazy(), log: LOG.slice(), loading: loading(), bodyLoading: BODY_CLS.has('pane-loading'), words: words('waiting'), timers: TIMERS.filter((t) => t.ms === 30000).length };
shimUp('waiting');
(LOADS.waiting || []).forEach((f) => f());   // the document loads: the controller's load hook re-tells it, the loading state ends
out.loaded = { loading: loading(), bodyLoading: BODY_CLS.has('pane-loading'), words: words('waiting') };
window.__rompMobileTab('chat'); window.__rompMobileTab('waiting');   // back and forth: the src is never reassigned
out.again = { sets: Object.assign({}, SETS), src: src(), bodyLoading: BODY_CLS.has('pane-loading') };
LOG.length = 0; MSGS.forEach((f) => f({ data: { romp: 'reveal', pane: 'fleet' } }));   // a reveal aimed at a lazy pane (the kernel's, a feed card's tap)
out.reveal = { tab: TAB, src: src(), log: LOG.slice(), loading: loading(), bodyLoading: BODY_CLS.has('pane-loading') };
window.__rompMobileTab('chat');
out.awayFromLoading = { bodyLoading: BODY_CLS.has('pane-loading'), loading: loading() };   // the Outline still loads off screen: no loader over the chat
window.__rompMobileTab('fleet');
out.backToLoading = { bodyLoading: BODY_CLS.has('pane-loading') };
shimUp('fleet'); shimUp('feed');   // both documents committed with their shims run, neither fired load yet: slow loads (the bundle still downloading)
backstops();   // the backstop: a load event that never comes cannot trap the loader; a committed document is a slow load, not a failure (review round 1: the failed road is LazyPanes' failed-load case)
out.backstop = { loading: loading(), bodyLoading: BODY_CLS.has('pane-loading'), failed: KEYS.filter((k) => DIVS[k].cls.has('failed')), src: src() };
window.__rompMobileTab('timeline');
out.timeline = { src: src(), lazy: lazy(), sets: Object.assign({}, SETS) };
window.__rompMobileTab('files');   // the Files tab (its control is on in the seed): the same first-tap load
out.filesTap = { tab: TAB, src: src(), lazy: lazy(), sets: Object.assign({}, SETS) };
// the gear turns the Outline off, then on again: on the phone the re-enabled pane waits for a tap (it loaded already here, so nothing moves)
STORE['romp:settings'] = JSON.stringify({ showFilesControl: true, panes: { fleet: false } }); STORAGE.forEach((f) => f({ key: 'romp:settings' }));
STORE['romp:settings'] = JSON.stringify({ showFilesControl: true, panes: {} }); STORAGE.forEach((f) => f({ key: 'romp:settings' }));
out.gearCycle = { sets: Object.assign({}, SETS), tab: TAB };
console.log(JSON.stringify(out));
"""
_LAZY_STORED_DRIVER = _LAZY_TOOLS + r"""
out.boot = { tab: TAB, src: src(), lazy: lazy(), sets: Object.assign({}, SETS), loading: loading(), bodyLoading: BODY_CLS.has('pane-loading') };
// the promoted iframe's INITIAL about:blank document fires its own load after the promotion (Chromium dispatches it asynchronously):
// promote()'s guard tells it from the page's load, so the loading state stands until the page itself has loaded (executed: review round 1)
frames['f-timeline'].contentDocument = { URL: 'about:blank' }; (LOADS.timeline || []).forEach((f) => f());
out.blankLoad = { loading: loading(), bodyLoading: BODY_CLS.has('pane-loading') };
shimUp('timeline'); (LOADS.timeline || []).forEach((f) => f());
out.pageLoad = { loading: loading(), bodyLoading: BODY_CLS.has('pane-loading') };
console.log(JSON.stringify(out));
"""
_LAZY_FLIP_DISABLED_DRIVER = _LAZY_TOOLS + r"""
out.boot = { src: src(), lazy: lazy(), dataSrc: dataSrc(), hidden: hidden() };
MATCHES = false; MQL.forEach((f) => f({}));   // the rotation to the desktop layout
out.flipped = { src: src(), lazy: lazy(), dataSrc: dataSrc(), sets: Object.assign({}, SETS), cls: BODY_CLS.has('po-fleet') };
STORE['romp:settings'] = JSON.stringify({ showFilesControl: true, panes: {} }); STORAGE.forEach((f) => f({ key: 'romp:settings' }));   // the gear turns the Outline on
out.enabled = { src: src(), lazy: lazy(), sets: Object.assign({}, SETS), cls: BODY_CLS.has('po-fleet'), hidden: hidden() };
console.log(JSON.stringify(out));
"""
_LAZY_FLIP_BACK_DRIVER = _LAZY_TOOLS + r"""
out.boot = { src: src(), lazy: lazy(), dataSrc: dataSrc() };
MATCHES = false; MQL.forEach((f) => f({}));   // the rotation to the desktop layout: the gear-off Outline is handed back to data-src and not promoted
out.flipped = { src: src(), lazy: lazy(), dataSrc: dataSrc() };
MATCHES = true; MQL.forEach((f) => f({}));    // …and back to the phone layout (review round 2): every unloaded pane but the chat and the feed is parked again
out.back = { src: src(), lazy: lazy(), dataSrc: dataSrc(), sets: Object.assign({}, SETS) };
STORE['romp:settings'] = JSON.stringify({ showFilesControl: true, panes: {} }); STORAGE.forEach((f) => f({ key: 'romp:settings' }));   // the gear turns the Outline on, on the phone
out.enabled = { src: src(), lazy: lazy(), dataSrc: dataSrc(), sets: Object.assign({}, SETS), hidden: hidden() };
window.__rompMobileTab('fleet');
out.tapped = { tab: TAB, src: src(), lazy: lazy(), sets: Object.assign({}, SETS) };
console.log(JSON.stringify(out));
"""
_LAZY_STORED_DISABLED_DRIVER = _LAZY_TOOLS + r"""
out.boot = { tab: TAB, src: src(), lazy: lazy(), dataSrc: dataSrc(), hidden: hidden(), sets: Object.assign({}, SETS) };
STORE['romp:settings'] = JSON.stringify({ showFilesControl: true, panes: {} }); STORAGE.forEach((f) => f({ key: 'romp:settings' }));   // the gear turns the Sessions band on again
out.enabled = { tab: TAB, src: src(), lazy: lazy(), hidden: hidden(), sets: Object.assign({}, SETS) };
window.__rompMobileTab('timeline');
out.tapped = { tab: TAB, src: src(), lazy: lazy(), sets: Object.assign({}, SETS), loading: loading(), bodyLoading: BODY_CLS.has('pane-loading') };
console.log(JSON.stringify(out));
"""
_LAZY_FEED_OFF_DRIVER = _LAZY_TOOLS + r"""
out.boot = { tab: TAB, src: src(), lazy: lazy(), sets: Object.assign({}, SETS), hidden: hidden(), loading: loading() };
STORE['romp:settings'] = JSON.stringify({ showFilesControl: true, panes: {} }); STORAGE.forEach((f) => f({ key: 'romp:settings' }));   // the gear turns the Feed back on
out.feedOn = { src: src(), sets: Object.assign({}, SETS), hidden: hidden(), tab: TAB };
window.__rompMobileTab('feed');
out.feedTab = { tab: TAB, sets: Object.assign({}, SETS) };
console.log(JSON.stringify(out));
"""
# D3 (review round 2, 2026-09-19): show() calls the shown pane's own synchronous show hook (contentWindow.__rompPaneShown) after the
# m-on toggle and BEFORE the re-tell, on the phone layout alone
_LAZY_SHOWN_DRIVER = _LAZY_TOOLS + r"""
frames['f-feed'].contentWindow.__rompPaneShown = () => { LOG.push('shown:feed'); };   // the feed bundle's hook (feed.ts); the other frames define none
LOG.length = 0;
window.__rompMobileTab('feed');
out.feedTap = { tab: TAB, log: LOG.slice(), mOn: frames['f-feed'].classList.contains('m-on') };
LOG.length = 0;
window.__rompMobileTab('waiting');   // a pane whose document defines no hook (or has no document yet): nothing called, the tell stands
out.waitingTap = { log: LOG.slice() };
LOG.length = 0;
MATCHES = false;   // the desktop layout: show() (a relay's switch) calls no hook
window.__rompMobileTab('feed');
out.desktopShow = { log: LOG.slice() };
console.log(JSON.stringify(out));
"""
# D7 (review round 1, 2026-09-19, regression-5): the mobile script throws before its last line; the desktop panes still load
_LAZY_ABORT_DRIVER = _LAZY_TOOLS + r"""
out.threw = global.__labThrew || null;
out.boot = { src: src(), sets: Object.assign({}, SETS), mobileTab: typeof window.__rompMobileTab };
console.log(JSON.stringify(out));
"""
_LAZY_DESKTOP_DRIVER = _LAZY_TOOLS + r"""
out.boot = { tab: TAB, src: src(), lazy: lazy(), sets: Object.assign({}, SETS), loading: loading(), bodyLoading: BODY_CLS.has('pane-loading') };
window.__rompMobileTab('waiting');
out.tap = { sets: Object.assign({}, SETS), loading: loading(), bodyLoading: BODY_CLS.has('pane-loading') };
console.log(JSON.stringify(out));
"""
_LAZY_FLIP_DRIVER = _LAZY_TOOLS + r"""
out.boot = { src: src(), lazy: lazy() };
MATCHES = false; MQL.forEach((f) => f({}));   // a rotation across the breakpoint: the grid shows every pane the rail has on
out.flipped = { src: src(), lazy: lazy(), sets: Object.assign({}, SETS), listeners: MQL.length, loading: loading() };
console.log(JSON.stringify(out));
"""
# HIGH 2 (review round 1, 2026-09-19): a lazy pane whose document fails to load is re-parked, says so where the user looks, and
# loads again on the next tap. Both detectors are driven: the load event over an error page (Chromium, Firefox: the document
# reads null) and the 30 s backstop over a never-committed frame (WebKit: no load event, about:blank); the retry road twice (the
# tab's re-tap, the tap on #pane-load); the mirror (a committed document's backstop clears the loader, re-parks nothing).
_LAZY_FAILED_DRIVER = _LAZY_TOOLS + r"""
SOCKS.forEach((s) => { s.readyState = 1; s.onopen && s.onopen(); });   // the shell socket opens: a client-diag row goes out at once from here (the queue is for a socket not yet open)
shimUp('feed'); (LOADS.feed || []).forEach((f) => f());   // the exempt feed's document loaded at boot
const snap = () => ({ src: src().waiting, lazy: lazy().waiting, div: divCls('waiting'), bodyLoading: BODY_CLS.has('pane-loading'), bodyFailed: BODY_CLS.has('pane-failed'), msg: MSG.textContent, sets: Object.assign({}, SETS), rows: diagRows('pane-load-failed') });
window.__rompMobileTab('waiting');   // the first tap: the document starts loading
out.tap = snap();
frames['f-waiting'].contentDocument = null;   // the fetch failed: Chromium and Firefox commit an error page, cross-origin, so the document reads null...
(LOADS.waiting || []).forEach((f) => f());   // ...and fire load
out.failedLoad = snap();
window.__rompMobileTab('waiting');   // the tab's re-tap: the pane promotes again, as a first tap would
out.retap = snap();
frames['f-waiting'].contentDocument = { URL: 'about:blank' };   // WebKit's road: the failed navigation fires no load event and the frame keeps its initial about:blank...
backstops();   // ...so only the 30 s backstop sees it (the first promotion's backstop is inert: its token is stale)
out.backstopFailed = snap();
CLICKS.forEach((f) => f());   // the tap on the message itself (#pane-load) retries too
out.loaderTap = snap();
shimUp('waiting');
(LOADS.waiting || []).forEach((f) => f());   // the good load: every promotion's listener fires, the live one alone acts
out.goodLoad = snap();
backstops();   // the mirror: a loaded pane's backstop finds no loading state and re-parks nothing
out.mirror = snap();
window.__rompMobileTab('chat'); window.__rompMobileTab('waiting');
out.again = snap();
out.feed = { src: src().feed, div: divCls('feed') };
console.log(JSON.stringify(out));
"""
# Family two (review round 3, 2026-09-19; narrowed in review round 4, kernel-1 and tests-1): docState() classifies the frame's document,
# and a same-origin document at the pane's url with NO pane shim that carries the kernel's stamp of a 200 (`doc`: the kernel's own
# "needs the ui/ modules" fallback page; the stamp is data-romp-served=200 on its <html> tag, written by Handler._send on every text/html
# 200) is a 200 the kernel served that this reader cannot classify. It is shown as served (the loading state ends, the src stays, no failed
# state, no re-park) and said once (one shell client-diag row `pane-load-unmarked` {pane, via}); a reader that cannot classify a 200 never
# reports absent. Round 2 called it a failure, which re-parked the kernel's own diagnostic behind an overlay no tap could clear; round 3
# then showed EVERY same-origin document as served, the kernel's 403 line (its body naming the serve-token file's path) included, with no
# retry road: the round-4 rule is "a 200 the kernel served", read off the stamp. The refused inputs stay refused: no document (an error
# page) fails via load; a frame never committed fails via the backstop; a document with neither marker nor stamp fails (the driver below).
_LAZY_UNMARKED_DRIVER = _LAZY_TOOLS + r"""
SOCKS.forEach((s) => { s.readyState = 1; s.onopen && s.onopen(); });
shimUp('feed'); (LOADS.feed || []).forEach((f) => f());
const snapK = (k) => ({ src: src()[k], lazy: lazy()[k], div: divCls(k), bodyLoading: BODY_CLS.has('pane-loading'), bodyFailed: BODY_CLS.has('pane-failed'), msg: MSG.textContent, sets: Object.assign({}, SETS), unmarked: diagRows('pane-load-unmarked'), failed: diagRows('pane-load-failed') });
window.__rompMobileTab('waiting');
out.tap = snapK('waiting');
servedDoc('waiting');   // a 200 the kernel served AT the pane's url with no shim run in its window (its "needs the ui/ modules" page), the stamp on its <html> tag
out.unmarkedDoc = { url: frames['f-waiting'].contentDocument.URL, shim: typeof frames['f-waiting'].contentWindow.__rompApp, stamp: frames['f-waiting'].contentDocument.documentElement.getAttribute('data-romp-served') };   // the input the reader cannot classify by the marker, and the stamp that says the kernel served it as a 200
(LOADS.waiting || []).forEach((f) => f());   // ...and its load fired, as every engine does for a committed response
out.unmarkedLoad = snapK('waiting');
window.__rompMobileTab('chat'); window.__rompMobileTab('waiting');   // the tab again: the src stands, nothing promotes twice, no loader
out.retap = snapK('waiting');
backstops();   // the backstop over the shown document: nothing moves (no loading state to end)
out.backstopAfter = snapK('waiting');
window.__rompMobileTab('fleet');   // the same stamped 200 with NO load event by the backstop (a slow parser-blocking sheet): shown and said via the backstop, not a failure
servedDoc('fleet');
backstops();
out.unmarkedBackstop = snapK('fleet');
window.__rompMobileTab('timeline');   // the refused input still refused: no document at all (Chromium's error page) fails via load
frames['f-timeline'].contentDocument = null; (LOADS.timeline || []).forEach((f) => f());
out.noneLoad = snapK('timeline');
console.log(JSON.stringify(out));
"""
# Review round 4 (2026-09-19, kernel-1 and tests-1): a same-origin document at the pane's url with neither the pane shim's marker nor the
# kernel's 200 stamp is NOT shown as served: the kernel's 403 line for a token-gated route once the cookie is stale (text/plain: the browser
# wraps it in a bare <html> the kernel never wrote, so no stamp), its 500 page, a proxy's 502 body while it restarts. Round 3 showed every
# such document as served, which put the 403 body (it names the serve-token file's path) on the phone's screen with no retry road for the
# page's life. Now it is a failure like an error page, on both detectors: the load listener (the 403 and the 500 commit a document and fire
# load in every engine) and the 30 s backstop (a document with no load event); re-parked under data-lazy-src, the failed state painted, one
# pane-load-failed row and no pane-load-unmarked row; and every retry road promotes it again: the tab's re-tap, the overlay tap
# (#pane-load) and the Try again button (#pane-load-retry), the last ending in a good load.
_LAZY_OTHER_DRIVER = _LAZY_TOOLS + r"""
SOCKS.forEach((s) => { s.readyState = 1; s.onopen && s.onopen(); });
shimUp('feed'); (LOADS.feed || []).forEach((f) => f());
const snapK = (k) => ({ src: src()[k], lazy: lazy()[k], div: divCls(k), bodyLoading: BODY_CLS.has('pane-loading'), bodyFailed: BODY_CLS.has('pane-failed'), msg: MSG.textContent, retryHidden: RETRY.hidden, sets: Object.assign({}, SETS), unmarked: diagRows('pane-load-unmarked'), failed: diagRows('pane-load-failed') });
window.__rompMobileTab('waiting');
otherDoc('waiting');   // the 403 line at the pane's url: same-origin, no marker, no stamp
out.otherDoc = { url: frames['f-waiting'].contentDocument.URL, shim: typeof frames['f-waiting'].contentWindow.__rompApp, stamp: frames['f-waiting'].contentDocument.documentElement.getAttribute('data-romp-served') };
(LOADS.waiting || []).forEach((f) => f());   // its load fired (a committed document fires load in every engine)
out.otherLoad = snapK('waiting');
CLICKS.forEach((f) => f());   // the overlay tap: the retry road (a tap anywhere on #pane-load)
out.overlayTap = snapK('waiting');
otherDoc('waiting');   // the retry's document: the same denial, this time with no load event by the backstop (WebKit's road for a slow commit)
backstops();
out.otherBackstop = snapK('waiting');
RETRY.clicks.forEach((f) => f({ stopPropagation() {} }));   // the Try again button: the retry road
out.buttonTap = snapK('waiting');
frames['f-waiting'].contentDocument = { URL: 'about:blank' };   // still loading...
out.loadingAgain = snapK('waiting');
shimUp('waiting'); (LOADS.waiting || []).forEach((f) => f());   // ...and the good load (the cookie fresh again): the episode ends
out.goodLoad = snapK('waiting');
window.__rompMobileTab('fleet');   // the tab's re-tap road, on a second pane: fail via load, re-tap, load
otherDoc('fleet'); (LOADS.fleet || []).forEach((f) => f());
out.secondPaneOther = snapK('fleet');
window.__rompMobileTab('chat'); window.__rompMobileTab('fleet');   // the tab again: promoted again as a first tap would
out.secondPaneRetap = snapK('fleet');
shimUp('fleet'); (LOADS.fleet || []).forEach((f) => f());
out.secondPaneLoaded = snapK('fleet');
console.log(JSON.stringify(out));
"""
# Family one (review round 3, 2026-09-19: regression-1, extra7-2, kernel-2): a promotion armed on the phone keeps judging after a flip to the
# desktop. Driven across the media query itself with mobileOn() REAL (the MediaQueryList fake's live `matches` and its change listeners fire
# the shell's own lazyFlip and retell): a failure detected on the desktop hands the url back to data-src and promotes once (before: re-parked
# under data-lazy-src whatever the layout, a desktop column with neither src nor data-src and no road to promote it); the phone-armed listener
# and backstop are inert over the desktop's re-promotion (the token minted per promotion: without it the stale listener re-failed the desktop's
# load and the cycle never ended); the failed class never survives onto the desktop, so the flip back paints no lie over a pane that loaded.
_LAZY_FLIP_FAILED_DRIVER = _LAZY_TOOLS + r"""
SOCKS.forEach((s) => { s.readyState = 1; s.onopen && s.onopen(); });
shimUp('feed'); (LOADS.feed || []).forEach((f) => f());
const snap = () => ({ src: src().waiting, lazy: lazy().waiting, dataSrc: dataSrc().waiting, div: divCls('waiting'), bodyFailed: BODY_CLS.has('pane-failed'), bodyLoading: BODY_CLS.has('pane-loading'), sets: Object.assign({}, SETS), rows: diagRows('pane-load-failed'), mobile: window.__rompMobileOn() });
// (A) fail on the phone, then flip: the phone's failed state is handed to the desktop as a promotion, no failed class rides along
window.__rompMobileTab('waiting');
frames['f-waiting'].contentDocument = null; (LOADS.waiting || []).forEach((f) => f());   // Chromium's error page: failed on the phone
out.phoneFailed = snap();
MATCHES = false; MQL.forEach((f) => f({}));   // the rotation to the desktop: the shell's own lazyFlip and retell listeners run
out.flippedA = snap();
shimUp('waiting'); (LOADS.waiting || []).forEach((f) => f());   // the desktop's load: every listener on the element fires, the phone's is inert (its token is stale)
out.desktopLoadedA = snap();
MATCHES = true; MQL.forEach((f) => f({}));   // back to the phone
window.__rompMobileTab('waiting');
out.backA = snap();
console.log(JSON.stringify(out));
"""
# (B) the flip WHILE loading, the failure detected on the desktop: its own run, since (A)'s flip to the desktop promotes EVERY parked pane (the
# grid shows them all), so no pane is left for a phone tap afterwards. Review round 4 (regression-1, correctness-1, extra6-1: one defect): the
# desktop's re-promotion has its own detector now, its failure is bounded to one re-promotion per episode (EPI) with the src kept at the bound
# and the failure recorded (DEAD), and the flip back parks the recorded pane with the failed state, so the phone's three retry roads recover it.
_LAZY_FLIP_MIDLOAD_DRIVER = _LAZY_TOOLS + r"""
SOCKS.forEach((s) => { s.readyState = 1; s.onopen && s.onopen(); });
shimUp('feed'); (LOADS.feed || []).forEach((f) => f());
window.__rompMobileTab('fleet');   // the phone tap: loading, the listener and backstop armed on the phone
const setsAtTap = SETS.fleet;
const snapF = () => ({ src: src().fleet, lazy: lazy().fleet, dataSrc: dataSrc().fleet, div: divCls('fleet'), sets: SETS.fleet - setsAtTap, rows: diagRows('pane-load-failed').filter((r) => r.pane === 'fleet'), bodyFailed: BODY_CLS.has('pane-failed'), bodyLoading: BODY_CLS.has('pane-loading'), msg: MSG.textContent, retryHidden: RETRY.hidden, mobile: window.__rompMobileOn(), listeners: (LOADS.fleet || []).length, backstops: TIMERS.filter((t) => t.ms === 30000).length });
MATCHES = false; MQL.forEach((f) => f({}));   // the flip mid-load: lazyFlip refuses a pane with a src; the phone's listener stands
out.flippedB = snapF();
['timeline', 'waiting', 'files'].forEach((k) => { shimUp(k); (LOADS[k] || []).forEach((f) => f()); });   // the grid's other three panes, promoted by the flip, load (their own detectors, armed on the desktop since round 4, are satisfied; left unloaded, their backstops would judge a never-committed document and re-promote them once, which is right and not this case's subject)
frames['f-fleet'].contentDocument = null; (LOADS.fleet || []).forEach((f) => f());   // the abort lands after the flip: failed() reads the DESKTOP and promotes again, arming its own listener and backstop (review round 4)
out.desktopFailedB = snapF();
frames['f-fleet'].contentDocument = { URL: 'about:blank' }; backstops();   // the desktop's re-promotion fails too, with NO load event (WebKit's road: the frame never commits): ITS OWN 30 s backstop judges it (the phone's is inert on its stale token; the desktop wears no loading class, so the guard is the pending verdict); the episode's bound: the src stays, nothing promotes a third time, the failure recorded
out.secondFailB = snapF();
backstops();   // every 30 s backstop again: the phone's (a stale token) and the desktop's (its verdict is in): inert
out.backstopB = snapF();
MATCHES = true; MQL.forEach((f) => f({}));   // the flip back to the phone: the recorded failure parks the pane under data-lazy-src with the failed state, painted (its tab is the shown one)
out.backB = snapF();
window.__rompMobileTab('fleet');   // road (i): the tab tap promotes it again
out.tabTapB = snapF();
frames['f-fleet'].contentDocument = null; (LOADS.fleet || []).forEach((f) => f());   // ...and it fails again on the phone: the failed state
out.phoneFailB = snapF();
CLICKS.forEach((f) => f());   // road (ii): the overlay tap (#pane-load)
out.overlayTapB = snapF();
frames['f-fleet'].contentDocument = null; (LOADS.fleet || []).forEach((f) => f());
out.phoneFailB2 = snapF();
RETRY.clicks.forEach((f) => f({ stopPropagation() {} }));   // road (iii): the Try again button (#pane-load-retry)
out.buttonTapB = snapF();
shimUp('fleet'); (LOADS.fleet || []).forEach((f) => f());   // the good load: recovered, the episode over
out.recoveredB = snapF();
MATCHES = false; MQL.forEach((f) => f({})); MATCHES = true; MQL.forEach((f) => f({}));   // the mirror: a flip there and back over the LOADED pane parks nothing (no failure recorded)
out.mirrorB = snapF();
console.log(JSON.stringify(out));
"""
# correctness-1 and ui-1 (review round 3, 2026-09-19): the failed copy is chosen by the failures of THIS episode (EPI, reset by a load), not the
# page-life count the row carries (FAILS); and the retry is a real button, hidden while loading, shown in the failed state, whose click
# retries. The second failure after a good load has no road in the shipped shell (a loaded pane's src is never reassigned, so promote()
# refuses it; the round-2 refuter found the defect latent), so the load listener is fired by hand over a swapped document, the
# refuter's reproduction, to pin the counter's meaning.
_LAZY_EPISODE_DRIVER = _LAZY_TOOLS + r"""
SOCKS.forEach((s) => { s.readyState = 1; s.onopen && s.onopen(); });
shimUp('feed'); (LOADS.feed || []).forEach((f) => f());
const snap = () => ({ src: src().waiting, div: divCls('waiting'), bodyFailed: BODY_CLS.has('pane-failed'), msg: MSG.textContent, retryHidden: RETRY.hidden, sets: Object.assign({}, SETS), rows: diagRows('pane-load-failed') });
window.__rompMobileTab('waiting');
out.loading = snap();   // the button is hidden while the document loads
frames['f-waiting'].contentDocument = null; (LOADS.waiting || []).forEach((f) => f());   // the first failure
out.failed1 = snap();
RETRY.clicks.forEach((f) => f({ stopPropagation() {} }));   // the button's click: the retry (a real button runs it on Enter and Space too)
out.retried = snap();
shimUp('waiting'); (LOADS.waiting || []).forEach((f) => f());   // the good load: the episode ends
out.loaded = snap();
frames['f-waiting'].contentDocument = null; (LOADS.waiting || []).forEach((f) => f());   // a later failure on the same page (hand-fired: no shipped road re-navigates a loaded pane)
out.failed2 = snap();
console.log(JSON.stringify(out));
"""
# HIGH 2, review round 2 closeout: the per-promotion token (TOK). The iframe element keeps every promotion's load listener and
# every promotion arms its own 30 s backstop, so a retry after a failure has the FIRST promotion's listener and backstop still
# live beside its own. Each guard is proven by the input it refuses: the stale backstop fired over the loading retry (without
# its guard it re-parks the retry), the stale listener fired beside the live one on the retry's failure (without its guard a
# second row is filed and the count runs by two).
_LAZY_TOKEN_DRIVER = _LAZY_TOOLS + r"""
SOCKS.forEach((s) => { s.readyState = 1; s.onopen && s.onopen(); });
shimUp('feed'); (LOADS.feed || []).forEach((f) => f());
const snap = () => ({ src: src().waiting, lazy: lazy().waiting, div: divCls('waiting'), bodyFailed: BODY_CLS.has('pane-failed'), msg: MSG.textContent, sets: Object.assign({}, SETS), rows: diagRows('pane-load-failed'), listeners: (LOADS.waiting || []).length, backstops: TIMERS.filter((t) => t.ms === 30000).length });
const t30 = () => TIMERS.filter((t) => t.ms === 30000);
window.__rompMobileTab('waiting');   // the first promotion: one listener, one backstop (beside the feed's)
const firstBackstops = t30().length;
frames['f-waiting'].contentDocument = null; (LOADS.waiting || []).forEach((f) => f());   // the first fetch fails on its load (an error page)
out.firstFailure = snap();
window.__rompMobileTab('waiting');   // the retry: a second listener on the same element, a second backstop; the first promotion's stay live
out.retry = snap();
frames['f-waiting'].contentDocument = { URL: 'about:blank' };   // the retry's document has not committed yet...
t30().slice(0, firstBackstops).forEach((t) => t.f());   // ...when the FIRST promotion's backstop fires (the feed's too, inert over a loaded pane)
out.staleBackstop = snap();
frames['f-waiting'].contentDocument = null; (LOADS.waiting || []).forEach((f) => f());   // the retry fails on its load too: BOTH listeners fire
out.secondFailure = snap();
window.__rompMobileTab('waiting');   // the third promotion
shimUp('waiting'); (LOADS.waiting || []).forEach((f) => f());   // the good load: three listeners fire, the live one alone acts
out.goodLoad = snap();
backstops();   // every backstop armed so far, the two stale ones included, over the loaded pane
out.mirror = snap();
console.log(JSON.stringify(out));
"""

# review round 4 verify (2026-09-19): the FEED through the recorded-failure road. The feed is exempt from the phone's off-screen parking (it
# loads at boot) and lazyFlip's phone branch skipped it with the chat, before the DEAD check, so a feed recorded DEAD on the desktop (the phone
# boot's promotion failed, the flip promoted it again, that failed too: the bound) kept its src over the dead document on the flip back, and
# the Feed tab tap ran promote() against a src and painted nothing: the ruled dead end, for the feed alone. The DEAD check runs for every key
# but the chat now (the chat never goes through promote()); the feed's exemption gates the unloaded parking alone.
_LAZY_FEED_DEAD_DRIVER = _LAZY_TOOLS + r"""
SOCKS.forEach((s) => { s.readyState = 1; s.onopen && s.onopen(); });
const snapFd = () => ({ src: src().feed, lazy: lazy().feed, dataSrc: dataSrc().feed, div: divCls('feed'), sets: SETS.feed || 0, rows: diagRows('pane-load-failed').filter((r) => r.pane === 'feed'), bodyFailed: BODY_CLS.has('pane-failed'), bodyLoading: BODY_CLS.has('pane-loading'), mobile: window.__rompMobileOn(), tab: TAB });
out.boot = snapFd();   // the phone boot promoted the feed off screen (its exemption); the chat is the shown tab
frames['f-feed'].contentDocument = null; (LOADS.feed || []).forEach((f) => f());   // the boot's fetch fails (the kernel unreachable): parked under data-lazy-src with the failed state, off screen
out.bootFailed = snapFd();
MATCHES = false; MQL.forEach((f) => f({}));   // the flip to the desktop: the grid shows the feed, lazyFlip hands the url to data-src and promotes it
out.flipped = snapFd();
['fleet', 'timeline', 'waiting', 'files'].forEach((k) => { shimUp(k); (LOADS[k] || []).forEach((f) => f()); });   // the grid's other panes load
frames['f-feed'].contentDocument = null; (LOADS.feed || []).forEach((f) => f());   // the desktop's promotion fails too: the episode's bound (the phone's failure counted), the src kept, the failure recorded
out.desktopFailed = snapFd();
MATCHES = true; MQL.forEach((f) => f({}));   // back to the phone: the recorded failure parks the feed like any pane
out.back = snapFd();
window.__rompMobileTab('feed');   // the Feed tab tap promotes it again
out.tabTap = snapFd();
shimUp('feed'); (LOADS.feed || []).forEach((f) => f());   // the good load
out.recovered = snapFd();
console.log(JSON.stringify(out));
"""
# review round 4 verify: a desktop promotion judged on the phone. lazyFlip's desktop branch sets data-src and promote() removes data-lazy-src
# alone, so when the verdict landed on the phone (the flip back before it) failed() parked the pane under data-lazy-src with data-src still on
# the frame; the controller's reconcile (the gear's storage event) then set its src from data-src with no token, listener or backstop, a
# promotion nothing judged: on an engine that fires no load event for a failed navigation the failed state stood for the page's life while
# every retry road ran promote() against a src. failed() drops the attribute the other layout reads now.
_LAZY_BOTH_ATTRS_DRIVER = _LAZY_TOOLS + r"""
SOCKS.forEach((s) => { s.readyState = 1; s.onopen && s.onopen(); });
shimUp('feed'); (LOADS.feed || []).forEach((f) => f());
const snapBa = () => ({ src: src().fleet, lazy: lazy().fleet, dataSrc: dataSrc().fleet, div: divCls('fleet'), sets: SETS.fleet || 0, listeners: (LOADS.fleet || []).length, backstops: TIMERS.filter((t) => t.ms === 30000).length, bodyFailed: BODY_CLS.has('pane-failed'), mobile: window.__rompMobileOn() });
MATCHES = false; MQL.forEach((f) => f({}));   // the flip to the desktop: the Outline gets data-src and the grid's promotion (data-src stays on the frame while it loads, as on every desktop pane)
['timeline', 'waiting', 'files'].forEach((k) => { shimUp(k); (LOADS[k] || []).forEach((f) => f()); });
out.desktop = snapBa();
MATCHES = true; MQL.forEach((f) => f({}));   // the flip back BEFORE the verdict (WebKit: up to 30 s with no load event): a frame with a src and its verdict owed stands, wearing the loader
out.backEarly = snapBa();
frames['f-fleet'].contentDocument = null; (LOADS.fleet || []).forEach((f) => f());   // the verdict lands on the phone: parked under data-lazy-src with the failed state, data-src dropped
out.phoneVerdict = snapBa();
STORE['romp:settings'] = JSON.stringify({ showFilesControl: true, panes: {} }); STORAGE.forEach((f) => f({ key: 'romp:settings' }));   // a gear save: the controller's reconcile sets src from data-src for every enabled pane without one
out.afterSave = snapBa();
backstops();   // every backstop armed so far: nothing pending
out.afterBackstops = snapBa();
window.__rompMobileTab('fleet');   // the tab tap: the one promotion road, with its detectors
out.tabTap = snapBa();
console.log(JSON.stringify(out));
"""
# review round 4 verify: the flip back while the DESKTOP's own promotion is in flight. The grid's promote() paints no loading class, lazyFlip's
# phone branch left a frame with a src alone, and the tab tap's promote() refuses a src, so paintLoading found nothing: a blank pane whose
# taps did nothing until the verdict (WebKit: up to 30 s, the backstop). The phone branch paints the loader for a promotion still owed its
# verdict (PEND), keyed on the recorded promotion and never on a read of the document.
_LAZY_FLIP_INFLIGHT_DRIVER = _LAZY_TOOLS + r"""
SOCKS.forEach((s) => { s.readyState = 1; s.onopen && s.onopen(); });
shimUp('feed'); (LOADS.feed || []).forEach((f) => f());
window.__rompMobileTab('fleet');   // the phone tap: loading, the detectors armed
const snapIf = () => ({ src: src().fleet, lazy: lazy().fleet, dataSrc: dataSrc().fleet, div: divCls('fleet'), sets: SETS.fleet, bodyLoading: BODY_CLS.has('pane-loading'), bodyFailed: BODY_CLS.has('pane-failed'), mobile: window.__rompMobileOn(), rows: diagRows('pane-load-failed').filter((r) => r.pane === 'fleet') });
MATCHES = false; MQL.forEach((f) => f({}));   // the flip mid-load
['timeline', 'waiting', 'files'].forEach((k) => { shimUp(k); (LOADS[k] || []).forEach((f) => f()); });
frames['f-fleet'].contentDocument = null; (LOADS.fleet || []).forEach((f) => f());   // the abort lands on the desktop: re-parked under data-src and promoted again, no loading class (the grid paints none)
out.desktopRepromoted = snapIf();
MATCHES = true; MQL.forEach((f) => f({}));   // the flip back BEFORE the re-promotion's verdict: the loader is painted for the shown tab
out.backInFlight = snapIf();
window.__rompMobileTab('fleet');   // the tab tap: promote() refuses a frame with a src; the loader stands
out.tapInFlight = snapIf();
frames['f-fleet'].contentDocument = null; (LOADS.fleet || []).forEach((f) => f());   // the verdict: a failure, judged on the phone, the failed state
out.verdict = snapIf();
window.__rompMobileTab('fleet');   // the re-tap promotes it again
out.retap = snapIf();
shimUp('fleet'); (LOADS.fleet || []).forEach((f) => f());
out.recovered = snapIf();
console.log(JSON.stringify(out));
"""


# ui-1 (review round 4, 2026-09-19): the keyboard's retry keeps its focus. paintLoading hides the button while the retry loads, which drops focus to the
# body in every engine (the served leg's witness); the failed paint that shows it again must put focus back, and nothing else may move focus onto it.
_LAZY_FOCUS_DRIVER = _LAZY_TOOLS + r"""
SOCKS.forEach((s) => { s.readyState = 1; s.onopen && s.onopen(); });
shimUp('feed'); (LOADS.feed || []).forEach((f) => f());
const snap = (k) => ({ tab: TAB, src: src()[k], div: divCls(k), bodyFailed: BODY_CLS.has('pane-failed'), msg: MSG.textContent, retryHidden: RETRY.hidden, active: ACTIVE, rows: diagRows('pane-load-failed').length });
const fail = (k) => { frames['f-' + k].contentDocument = null; (LOADS[k] || []).forEach((f) => f()); };   // the fetch fails: the error page's load (Chromium's road)
const pressEnter = () => RETRY.clicks.forEach((f) => f({ stopPropagation() {} }));   // Enter on the focused button: a real <button> runs its click natively
window.__rompMobileTab('waiting'); fail('waiting');
RETRY.focus();   // the keyboard walk lands on the button (the served leg's Tab witness)
out.focused = snap('waiting');
pressEnter();   // the retry: the button hidden while the retry loads, the focus dropped to the body
out.retrying = snap('waiting');
fail('waiting');   // the re-failure: the failed paint shows the button again and puts the focus back on it
out.refailed = snap('waiting');
pressEnter(); shimUp('waiting'); (LOADS.waiting || []).forEach((f) => f());   // the retry loads: the button hidden, the load retires the flag
out.loaded = snap('waiting');
fail('waiting');   // a later failure of the SAME shown pane, hand-fired (no shipped road re-navigates a loaded pane; the episode case's shape): no tab switch between, so the load alone retired the flag
out.sameLater = snap('waiting');
window.__rompMobileTab('fleet'); fail('fleet');   // a later pane's FIRST failure: no gesture on the button, so it takes no focus (the amendment's negative)
out.laterFirst = snap('fleet');
CLICKS.forEach((f) => f()); fail('fleet');   // the overlay tap retries too, a pointer gesture: the re-failure focuses nothing
out.overlayRefail = snap('fleet');
RETRY.focus(); pressEnter();   // the keyboard's retry again...
window.__rompMobileTab('chat'); window.__rompMobileTab('fleet');   // ...but the user switches tabs before the verdict (and comes back): the switch retired the flag
fail('fleet');
out.switchedRefail = snap('fleet');
console.log(JSON.stringify(out));
"""
def _lazy(seed, driver, phone=True, abort_mobile=False):
    """The three shell scripts in the served order: the desktop promotion (_LANDING_DESKTOP_PANES_JS, review round 1), the mobile
    script, the pane controller. `abort_mobile` wraps the mobile script in a try so the harness's seed can make it throw partway
    (BAR.querySelectorAll) and the test reads what the other two scripts still did; the throw is recorded in global.__labThrew."""
    keys = [k for k, _ in km._PANE_ORDER]
    harness = _LAZY_HARNESS.replace("__KEYS__", json.dumps(keys)).replace("__PHONE__", "true" if phone else "false").replace("__SEED__", seed)
    mobile = ("try{" + km._LANDING_MOBILE_JS + "}catch(e){global.__labThrew=String(e);}") if abort_mobile else km._LANDING_MOBILE_JS
    return _run(harness + km._LANDING_DESKTOP_PANES_JS + mobile + km._LANDING_COLLAPSE_JS + driver)


class LazyPanes(unittest.TestCase):
    """T1 (stage 0, 2026-09-18), the shell side: on the phone an off-screen pane other than the feed has no src, so no document and
    no socket, until its first tap; the tap sets it once, before the re-tell; the desktop still loads every pane at boot."""

    @classmethod
    def setUpClass(cls):
        cls.seed = "STORE['romp:settings'] = JSON.stringify({ showFilesControl: true }); STORE['romp-mobile-tab'] = 'chat';"
        cls.out = _lazy(cls.seed, _LAZY_PHONE_DRIVER)

    def test_at_boot_on_the_phone_only_the_chat_the_feed_and_the_stored_tab_have_a_src(self):
        b = self.out["boot"]
        self.assertEqual(b["tab"], "chat")
        self.assertEqual(b["src"], {"chat": "/chat", "feed": "/feed", "files": None, "timeline": None, "fleet": None, "waiting": None},
                         "the chat ships src, the feed is promoted (exempt); the Outline, the Sessions band, the Waiting pane and the Files pane have no document")
        self.assertEqual(b["lazy"], {"chat": None, "feed": None, "files": "/files", "timeline": "/timeline", "fleet": "/fleet", "waiting": "/waiting"},
                         "the lazy panes' data-src is parked under data-lazy-src before the controller parses")
        self.assertEqual(b["dataSrc"], {"chat": None, "feed": "/feed", "files": None, "timeline": None, "fleet": None, "waiting": None},
                         "…so the controller's own promotion line (upstream's text) finds nothing to copy for them; the feed keeps its data-src beside its src, as any promoted pane does (a src is never reassigned)")
        self.assertEqual(b["sets"], {"feed": 1}, "one src set at boot: the feed's")
        self.assertEqual(b["loading"], ["feed"], "the feed's .pane carries the loading class until its document loads")
        self.assertFalse(b["bodyLoading"], "the shown tab (the chat) is not loading: no loader over it")
        self.assertEqual(sorted(b["hidden"]), ["chat", "feed", "files", "fleet", "timeline", "waiting"], "the six panes (the read's keys, before a comprehension over them stands in for an expectation)")
        self.assertEqual(b["hidden"], {k: False for k in b["hidden"]}, "every tab is a place to go")
        self.assertEqual(b["promote"], "undefined", "no export: the three promotion roads call promote() directly (round 3, fresh-3); a re-add would be an unused seam")

    def test_the_first_tap_sets_the_src_once_before_the_re_tell_and_paints_the_loader_until_the_load(self):
        t = self.out["tap"]
        self.assertEqual(t["tab"], "waiting")
        self.assertEqual(t["src"]["waiting"], "/waiting", "the tap promotes the pane")
        self.assertIsNone(t["lazy"]["waiting"], "…and consumes the parked attribute")
        self.assertEqual(t["log"], ["src:waiting", "tell"], "the src is set BEFORE the re-tell (a word posted into a document not yet there is dropped; the pane hears it on its load)")
        self.assertEqual(sorted(t["loading"]), ["feed", "waiting"], "the tapped pane's .pane carries the loading class")
        self.assertTrue(t["bodyLoading"], "the shown tab is loading: the shell paints its loader (body.pane-loading)")
        self.assertEqual(t["words"][-1], True, "the re-tell says the pane is on screen")
        self.assertEqual(t["timers"], 2, "a 30 s backstop per promotion so far (the feed's and this one)")
        l = self.out["loaded"]
        self.assertEqual(l["loading"], ["feed"], "the load event ends the loading state")
        self.assertFalse(l["bodyLoading"], "…and the loader goes")
        self.assertEqual(l["words"][-1], True, "the controller's load hook tells the new document the set")
        a = self.out["again"]
        self.assertEqual(a["sets"], {"feed": 1, "waiting": 1}, "src set exactly once per pane: a second show never reassigns it")
        self.assertFalse(a["bodyLoading"])

    def test_a_reveal_promotes_too_and_the_loader_follows_the_shown_tab_with_a_backstop(self):
        r = self.out["reveal"]
        self.assertEqual(r["tab"], "fleet")
        self.assertEqual(r["src"]["fleet"], "/fleet", "a reveal aimed at a lazy pane loads it")
        self.assertEqual(r["log"][:2], ["src:fleet", "tell"], "the same order: the src, then the word")
        self.assertIn("fleet", r["loading"]); self.assertTrue(r["bodyLoading"])
        self.assertFalse(self.out["awayFromLoading"]["bodyLoading"], "a switch away from a loading pane takes the loader with it (the Outline keeps loading off screen)")
        self.assertIn("fleet", self.out["awayFromLoading"]["loading"])
        self.assertTrue(self.out["backToLoading"]["bodyLoading"], "…and back to it, the loader is back")
        self.assertEqual(self.out["backstop"], {"loading": [], "bodyLoading": False, "failed": [], "src": {"chat": "/chat", "feed": "/feed", "files": None, "timeline": None, "fleet": "/fleet", "waiting": "/waiting"}},
                         "the 30 s backstop ends a loading state whose load event never came: the loader can never trap the user; a document that committed is a slow load, so nothing is re-parked or marked failed (review round 1)")
        self.assertEqual(self.out["timeline"]["src"]["timeline"], "/timeline")
        self.assertEqual(self.out["timeline"]["sets"], {"feed": 1, "waiting": 1, "fleet": 1, "timeline": 1})
        ft = self.out["filesTap"]
        self.assertEqual((ft["tab"], ft["src"]["files"], ft["lazy"]["files"]), ("files", "/files", None), "the Files tab loads its pane on the first tap like the others")
        self.assertEqual(ft["sets"], {"feed": 1, "waiting": 1, "fleet": 1, "timeline": 1, "files": 1})
        self.assertEqual(self.out["gearCycle"]["sets"], {"feed": 1, "waiting": 1, "fleet": 1, "timeline": 1, "files": 1}, "a gear cycle on a loaded pane reassigns nothing")

    def test_the_stored_tab_loads_at_boot_and_wears_the_loader(self):
        out = _lazy("STORE['romp:settings'] = JSON.stringify({ showFilesControl: true }); STORE['romp-mobile-tab'] = 'timeline';", _LAZY_STORED_DRIVER)
        o = out["boot"]
        self.assertEqual(sorted(out["blankLoad"]["loading"]), ["feed", "timeline"], "the initial about:blank document's own load is not the page's: the loading state stands (promote()'s guard, executed)")
        self.assertTrue(out["blankLoad"]["bodyLoading"], "…and the loader stays up over the shown tab")
        self.assertEqual(out["pageLoad"], {"loading": ["feed"], "bodyLoading": False}, "the page's own load ends it")
        self.assertEqual(o["tab"], "timeline")
        self.assertEqual(o["src"], {"chat": "/chat", "feed": "/feed", "files": None, "timeline": "/timeline", "fleet": None, "waiting": None}, "the stored tab is eager; the other three wait for a tap")
        self.assertEqual(o["lazy"], {"chat": None, "feed": None, "files": "/files", "timeline": None, "fleet": "/fleet", "waiting": "/waiting"})
        self.assertEqual(o["sets"], {"feed": 1, "timeline": 1})
        self.assertEqual(sorted(o["loading"]), ["feed", "timeline"])
        self.assertTrue(o["bodyLoading"], "the shown tab is loading its document: the loader is up (under the boot splash at this point)")

    def test_a_gear_disabled_pane_parked_at_a_phone_boot_loads_after_a_flip_to_the_desktop_and_a_gear_enable(self):
        # F3 (review round 1, 2026-09-19): the flip hands every parked pane back to the controller's attribute; the gear's later
        # enable then promotes it through the controller's own line. Before: parked with no data-src, the enable showed an empty column.
        o = _lazy("STORE['romp:settings'] = JSON.stringify({ showFilesControl: true, panes: { fleet: false } }); STORE['romp-mobile-tab'] = 'chat';", _LAZY_FLIP_DISABLED_DRIVER)
        b = o["boot"]
        self.assertEqual((b["src"]["fleet"], b["lazy"]["fleet"], b["dataSrc"]["fleet"], b["hidden"]["fleet"]), (None, "/fleet", None, True), "parked at the phone boot, hidden by the gear")
        f = o["flipped"]
        self.assertEqual((f["src"]["fleet"], f["lazy"]["fleet"], f["dataSrc"]["fleet"]), (None, None, "/fleet"), "the flip hands the disabled pane back to data-src and promotes it not (the gear's word)")
        self.assertEqual(f["src"]["waiting"], "/waiting", "…while an enabled parked pane is promoted by the same flip")
        self.assertFalse(f["cls"])
        e = o["enabled"]
        self.assertEqual((e["src"]["fleet"], e["sets"].get("fleet"), e["cls"], e["hidden"]["fleet"]), ("/fleet", 1, True, False), "the gear enable on the desktop loads the pane through the controller's line and shows the column")

    def test_a_flip_to_the_desktop_and_back_parks_the_unloaded_panes_again_so_a_gear_enable_on_the_phone_loads_nothing_off_screen(self):
        # review round 2 (2026-09-19): the flip to the desktop hands parked panes back to data-src (F3); without the flip back
        # re-parking them, a gear-off pane sat on data-src on the phone and the controller's enable loaded it hidden (F9's outcome)
        o = _lazy("STORE['romp:settings'] = JSON.stringify({ showFilesControl: true, panes: { fleet: false } }); STORE['romp-mobile-tab'] = 'chat';", _LAZY_FLIP_BACK_DRIVER)
        self.assertEqual((o["boot"]["lazy"]["fleet"], o["boot"]["dataSrc"]["fleet"]), ("/fleet", None), "parked at the phone boot")
        self.assertEqual((o["flipped"]["lazy"]["fleet"], o["flipped"]["dataSrc"]["fleet"], o["flipped"]["src"]["fleet"]), (None, "/fleet", None), "handed back on the desktop, not promoted (the gear)")
        b = o["back"]
        self.assertEqual((b["lazy"]["fleet"], b["dataSrc"]["fleet"], b["src"]["fleet"]), ("/fleet", None, None), "parked again on the flip back to the phone")
        self.assertEqual((b["lazy"]["chat"], b["lazy"]["feed"], b["src"]["feed"]), (None, None, "/feed"), "the chat and the feed are never parked; a loaded pane keeps its src")
        e = o["enabled"]
        self.assertEqual((e["src"]["fleet"], e["lazy"]["fleet"], e["hidden"]["fleet"], e["sets"].get("fleet")), (None, "/fleet", False, None), "the gear enable on the phone unhides the tab and loads nothing off screen")
        t = o["tapped"]
        self.assertEqual((t["tab"], t["src"]["fleet"], t["lazy"]["fleet"], t["sets"].get("fleet")), ("fleet", "/fleet", None, 1), "its first tap loads it, once")

    def test_a_stored_tab_the_gear_has_off_stays_parked_so_a_later_enable_does_not_load_it_off_screen(self):
        # F9 (review round 1, 2026-09-19): the parking no longer skips the stored tab; promote() refuses a disabled pane, so it stays
        # parked and loads on its first tap like every other lazy pane (before: it kept its data-src and the enable loaded it hidden)
        o = _lazy("STORE['romp:settings'] = JSON.stringify({ showFilesControl: true, panes: { timeline: false } }); STORE['romp-mobile-tab'] = 'timeline';", _LAZY_STORED_DISABLED_DRIVER)
        b = o["boot"]
        self.assertEqual(b["tab"], "chat", "a phone left on the hidden pane's tab goes back to the chat")
        self.assertEqual((b["src"]["timeline"], b["lazy"]["timeline"], b["dataSrc"]["timeline"], b["hidden"]["timeline"]), (None, "/timeline", None, True), "parked, not loaded")
        self.assertEqual(b["sets"], {"feed": 1})
        e = o["enabled"]
        self.assertEqual((e["src"]["timeline"], e["lazy"]["timeline"], e["hidden"]["timeline"], e["sets"]), (None, "/timeline", False, {"feed": 1}), "the gear enable on the phone unhides the tab and loads nothing off screen")
        t = o["tapped"]
        self.assertEqual((t["tab"], t["src"]["timeline"], t["lazy"]["timeline"], t["sets"]), ("timeline", "/timeline", None, {"feed": 1, "timeline": 1}), "its first tap loads it, once")
        self.assertIn("timeline", t["loading"]); self.assertTrue(t["bodyLoading"])

    def test_a_pane_off_in_the_gear_is_never_promoted_and_the_exempt_feed_loads_when_the_gear_turns_it_on(self):
        o = _lazy("STORE['romp:settings'] = JSON.stringify({ showFilesControl: true, panes: { feed: false } }); STORE['romp-mobile-tab'] = 'feed';", _LAZY_FEED_OFF_DRIVER)
        b = o["boot"]
        self.assertEqual(b["tab"], "chat", "a phone left on the hidden pane's tab goes back to the chat (the controller's rule)")
        self.assertEqual(b["src"], {"chat": "/chat", "feed": None, "files": None, "timeline": None, "fleet": None, "waiting": None}, "the gear's off word wins over the feed's exemption: no document")
        self.assertEqual(b["sets"], {}, "nothing promoted at boot")
        self.assertTrue(b["hidden"]["feed"])
        f = o["feedOn"]
        self.assertEqual(f["src"]["feed"], "/feed", "the gear turns the Feed on: the controller's own line promotes it (its data-src was never parked, the feed being exempt), so the bell's pane loads off screen as designed")
        self.assertEqual(f["sets"], {"feed": 1}); self.assertFalse(f["hidden"]["feed"])
        self.assertEqual(o["feedTab"], {"tab": "feed", "sets": {"feed": 1}})

    def test_a_failed_document_load_is_re_parked_named_where_the_user_looks_and_loads_again_on_the_next_tap(self):
        # HIGH 2 (review round 1, 2026-09-19: extra6-1, kernel-1). Before: promote() set src once and its first guard read it, so a
        # document that failed at the first tap left the pane blank for the life of the page, the backstop clearing the loader over
        # nothing. Now a load that committed no readable document (an error page), or no document by the backstop, re-parks the pane
        # (src removed, the url back under data-lazy-src), marks its div `failed`, paints the message under body.pane-failed and files
        # one shell client-diag row; the next show() promotes it again.
        o = _lazy(self.seed, _LAZY_FAILED_DRIVER)
        t = o["tap"]
        self.assertEqual((t["src"], t["lazy"], t["div"], t["bodyLoading"], t["bodyFailed"], t["msg"]), ("/waiting", None, ["loading"], True, False, ""), "the first tap: loading, no message")
        f = o["failedLoad"]
        self.assertEqual((f["src"], f["lazy"]), (None, "/waiting"), "the error page's load re-parks the pane: no src (promote's guard reads it), the url back where a first tap finds it")
        self.assertEqual(f["div"], ["failed"], "the div swaps loading for failed")
        self.assertEqual((f["bodyLoading"], f["bodyFailed"]), (False, True), "the shown tab's pane failed: body.pane-failed paints #pane-load with the message, the loader itself is down")
        self.assertEqual(f["msg"], "Couldn't load this pane.", "the first failure's copy (the affordance is the button's own text, review round 3, ui-2)")
        self.assertEqual(f["rows"], [{"pane": "waiting", "via": "load", "n": 1}], "one shell client-diag row names the pane, the detector and the count")
        self.assertEqual(f["sets"], {"feed": 1, "waiting": 1})
        r = o["retap"]
        self.assertEqual((r["src"], r["lazy"], r["div"], r["bodyLoading"], r["bodyFailed"], r["msg"]), ("/waiting", None, ["loading"], True, False, ""), "the re-tap promotes again: loading, the failed state cleared")
        self.assertEqual(r["sets"], {"feed": 1, "waiting": 2}, "a second src set (the one exception to a src never being reassigned: the first never became a document)")
        b = o["backstopFailed"]
        self.assertEqual((b["src"], b["lazy"], b["div"], b["bodyFailed"]), (None, "/waiting", ["failed"], True), "WebKit's road: no load event, the frame at about:blank when the 30 s backstop fires: re-parked and failed again")
        self.assertEqual(b["msg"], "Still not loading. Try again, or reload the page.", "the second failure's copy offers the page reload")
        self.assertEqual(b["rows"], [{"pane": "waiting", "via": "load", "n": 1}, {"pane": "waiting", "via": "backstop", "n": 2}], "a second row, via the backstop, counted")
        lt = o["loaderTap"]
        self.assertEqual((lt["src"], lt["div"], lt["bodyLoading"], lt["bodyFailed"], lt["sets"]), ("/waiting", ["loading"], True, False, {"feed": 1, "waiting": 3}), "a tap on the message retries as the tab's re-tap does")
        g = o["goodLoad"]
        self.assertEqual((g["src"], g["div"], g["bodyLoading"], g["bodyFailed"], g["msg"]), ("/waiting", [], False, False, ""), "a good load ends it: no loading, no failed, no message")
        self.assertEqual(o["mirror"], g, "a loaded pane's backstop changes nothing (the mirror: no re-park of a healthy pane)")
        self.assertEqual(o["again"]["sets"], {"feed": 1, "waiting": 3}, "a later show of the loaded pane reassigns nothing")
        self.assertEqual(o["feed"], {"src": "/feed", "div": []}, "the feed's document, committed at boot, is untouched throughout")

    def test_a_document_the_origin_served_with_no_shim_is_shown_as_served_and_said_never_a_failure(self):
        # Family two (review round 3, 2026-09-19; narrowed in round 4, kernel-1): the detector must not claim failure for a 200 the kernel served
        # that it cannot classify. A same-origin document at the pane's url with no pane shim that carries the kernel's 200 stamp (its own
        # "needs the ui/ modules" page: data-romp-served=200 on the <html> tag, Handler._send's mark on every text/html 200) is what the
        # kernel served, so the loading state ends, the src stays, no failed state paints and one pane-load-unmarked row says what was seen.
        # Round 2 called this a failure and re-parked the kernel's own diagnostic behind an overlay no tap could clear. The input is recorded
        # beside the verdict; the refused inputs (no document; a frame never committed by the backstop; a document with neither marker nor
        # stamp, the case below) stay refused.
        o = _lazy(self.seed, _LAZY_UNMARKED_DRIVER)
        t = o["tap"]
        self.assertEqual((t["src"], t["div"], t["bodyLoading"], t["unmarked"]), ("/waiting", ["loading"], True, []), "the first tap: loading")
        self.assertEqual(o["unmarkedDoc"], {"url": "http://TESTHOST:1/waiting", "shim": "undefined", "stamp": "200"}, "the input: a same-origin document at the pane's own url with no shim in its window and the kernel's 200 stamp on its <html> tag")
        u = o["unmarkedLoad"]
        self.assertEqual((u["src"], u["lazy"], u["div"], u["bodyLoading"], u["bodyFailed"], u["msg"]), ("/waiting", None, [], False, False, ""), "its load: shown as served (the loader clears, the src stays, no failed state, no re-park)")
        self.assertEqual(u["unmarked"], [{"pane": "waiting", "via": "load"}], "…and said once: the reader reports what it saw, never absent")
        self.assertEqual(u["failed"], [], "no pane-load-failed row")
        r = o["retap"]
        self.assertEqual((r["src"], r["div"], r["sets"]["waiting"], r["bodyLoading"]), ("/waiting", [], 1, False), "the tab again: one src set for the page's life, no loader (the document stands as served; a reload is the retry road)")
        self.assertEqual(o["backstopAfter"], r, "the backstop over the shown document moves nothing and says nothing more")
        b = o["unmarkedBackstop"]
        self.assertEqual((b["src"], b["div"], b["bodyFailed"]), ("/fleet", [], False), "the same stamped 200 with no load event by the 30 s backstop: shown, not the failed road")
        self.assertEqual(b["unmarked"], [{"pane": "waiting", "via": "load"}, {"pane": "fleet", "via": "backstop"}], "…and said via the backstop")
        n = o["noneLoad"]
        self.assertEqual((n["src"], n["lazy"], n["div"], n["bodyFailed"]), (None, "/timeline", ["failed"], True), "the refused input stays refused: no document (an error page) fails via load and re-parks")
        self.assertEqual(n["failed"], [{"pane": "timeline", "via": "load", "n": 1}])
        self.assertEqual(n["unmarked"], b["unmarked"], "a failure files no unmarked row")
        js = km._LANDING_MOBILE_JS
        self.assertIn("function docState(f){try{var d=f.contentDocument;if(!d)return 'none';var u=d.URL;if(!u||u==='about:blank')return 'blank';var w=f.contentWindow;if(w&&typeof w.__rompApp==='string')return 'app';var h=d.documentElement;return (h&&h.getAttribute&&h.getAttribute('data-romp-served')==='200')?'doc':'other';}catch(e){return 'none';}}", js, "the classifier's five answers: the stamp read off the <html> tag tells a 200 the kernel served (doc) from what it did not (other)")
        self.assertNotIn("function committed(", js, "the one-marker boolean is gone: no failure claim for a 200 the reader cannot classify")
        self.assertIn("if(s==='app')loaded(k);else if(s==='doc')unmarked(k,'load');else failed(k,'load');", js, "the load listener: doc alone is shown as served; other fails like none")
        self.assertIn("if(s==='app')loaded(k);else if(s==='doc')unmarked(k,'backstop');else failed(k,'backstop');", js, "the backstop: the same")
        self.assertTrue({"pane", "via"} <= set(km.CLIENT_DIAG_KEYS["shell"]), "the row's keys survive the shell allowlist (its fixture row is test_client_diag_allowlist's)")

    def test_a_document_the_kernel_did_not_serve_as_a_200_is_a_failure_with_the_retry_road_never_shown_as_served(self):
        # Review round 4 (2026-09-19, kernel-1 and tests-1): round 3's inversion showed ANY same-origin document as served, the kernel's 403
        # line included (its body names the serve-token file's path), with no retry road for the page's life; the round-2 ruling it rested on
        # is scoped to a 200 the kernel served. A document with neither the marker nor the kernel's 200 stamp (the 403 line, a 500 page, a
        # proxy's 502 body: none can carry the stamp) is a failure on both detectors, and the three retry roads promote it again.
        o = _lazy(self.seed, _LAZY_OTHER_DRIVER)
        self.assertEqual(o["otherDoc"], {"url": "http://TESTHOST:1/waiting", "shim": "undefined", "stamp": None}, "the input: same-origin at the pane's url, no shim, no stamp")
        f = o["otherLoad"]
        self.assertEqual((f["src"], f["lazy"], f["div"], f["bodyLoading"], f["bodyFailed"], f["retryHidden"]), (None, "/waiting", ["failed"], False, True, False), "its load: a failure, not a served document: re-parked under data-lazy-src, the failed state painted, the button shown")
        self.assertEqual(f["msg"], "Couldn't load this pane.", "the first failure's copy (the denial's own text is NOT on show)")
        self.assertEqual(f["failed"], [{"pane": "waiting", "via": "load", "n": 1}], "one pane-load-failed row via load")
        self.assertEqual(f["unmarked"], [], "no pane-load-unmarked row: nothing was shown as served")
        ot = o["overlayTap"]
        self.assertEqual((ot["src"], ot["lazy"], ot["div"], ot["sets"]["waiting"]), ("/waiting", None, ["loading"], 2), "the overlay tap retries: a second promotion")
        b = o["otherBackstop"]
        self.assertEqual((b["src"], b["lazy"], b["div"], b["bodyFailed"]), (None, "/waiting", ["failed"], True), "the same denial with no load event by the 30 s backstop: a failure via the backstop, not shown")
        self.assertEqual(b["failed"], [{"pane": "waiting", "via": "load", "n": 1}, {"pane": "waiting", "via": "backstop", "n": 2}])
        self.assertEqual(b["msg"], "Still not loading. Try again, or reload the page.", "the episode's second failure offers the reload")
        bt = o["buttonTap"]
        self.assertEqual((bt["src"], bt["div"], bt["retryHidden"], bt["sets"]["waiting"]), ("/waiting", ["loading"], True, 3), "the Try again button retries: a third promotion, the button hidden while it loads")
        self.assertEqual(o["loadingAgain"]["div"], ["loading"], "the backstop's guard: still loading at about:blank is not judged by the load listener")
        g = o["goodLoad"]
        self.assertEqual((g["src"], g["div"], g["bodyFailed"], g["bodyLoading"], g["msg"], g["unmarked"]), ("/waiting", [], False, False, "", []), "the good load ends the episode: the pane loaded, no overlay, no message, nothing ever said served")
        self.assertEqual(g["failed"], b["failed"], "no further row")
        fo = o["secondPaneOther"]
        self.assertEqual((fo["src"], fo["lazy"], fo["div"], fo["bodyFailed"]), (None, "/fleet", ["failed"], True), "a second pane, the same denial via load: failed")
        fr = o["secondPaneRetap"]
        self.assertEqual((fr["src"], fr["div"], fr["sets"]["fleet"], fr["bodyFailed"]), ("/fleet", ["loading"], 2, False), "the tab's re-tap promotes it again as a first tap would")
        self.assertEqual((o["secondPaneLoaded"]["src"], o["secondPaneLoaded"]["div"], o["secondPaneLoaded"]["unmarked"]), ("/fleet", [], []), "...and its good load ends it")

    def test_the_kernel_stamps_every_200_html_document_it_writes_and_nothing_else(self):
        # The writer's side of the round-4 rule (kernel-1): Handler._send marks every text/html 200 with data-romp-served=200 on the <html>
        # tag (a rule over the writer, so no list of pages can go stale), and nothing else: the seven pane routes' pages, the four fallback
        # pages a missing ui/ module yields all carry it; a 403 or a 500 text/plain body (what the kernel's denial and its traceback are), a
        # text/plain 200 and a body with no <html> tag (the paste-the-token page at /, disclosed below) pass through untouched, bytes or str.
        stamp = km._stamp_served_html
        pages = {"chat": km._chat_page, "feed": km._feed_page, "timeline": km._timeline_page, "fleet": km._fleet_page, "waiting": km._waiting_page, "files": km._files_page, "settings": km._settings_page}
        self.assertEqual(sorted(pages), sorted([k for k, _ in km._PANE_ORDER] + ["settings"]), "the census: every pane key of _PANE_ORDER has its page here, plus the gear's")
        bodies = {k: fn() for k, fn in pages.items()}
        real_ui = km.UI
        try:
            km.UI = Path(tempfile.mkdtemp()) / "absent"   # the fallback branches: the ui/ modules missing
            fallbacks = {k: pages[k]() for k in ("fleet", "waiting", "files", "timeline")}
        finally:
            km.UI = real_ui
        self.assertTrue(all("needs the ui/ modules" in b for b in fallbacks.values()), "the four fallback pages were produced: %r" % ({k: b[:60] for k, b in fallbacks.items()},))
        for k, b in list(bodies.items()) + [("fallback-" + k, b) for k, b in fallbacks.items()]:
            self.assertNotIn("data-romp-served", b, k + ": the page function writes no stamp of its own (the writer does)")
            out = stamp(200, b, "text/html; charset=utf-8")
            self.assertEqual(out.count("<html data-romp-served=200"), 1, k + ": one stamp on the <html> tag of a text/html 200")
            self.assertEqual(len(out), len(b) + len(" data-romp-served=200"), k + ": nothing else changes")
        self.assertNotIn("<html", km._TOKEN_LOGIN_HTML, "the token-less landing (the paste-the-token page at /) writes no root tag, so it is the one 200 the writer cannot stamp: disclosed here; it is served at / alone, never at a pane url, so no pane frame's reader meets it")
        self.assertEqual(stamp(200, km._TOKEN_LOGIN_HTML, "text/html"), km._TOKEN_LOGIN_HTML, "...and it passes through as it came")
        self.assertEqual(stamp(200, b"<!DOCTYPE html><html lang=en><body>x</body></html>", "text/html"), b"<!DOCTYPE html><html data-romp-served=200 lang=en><body>x</body></html>", "a bytes body is stamped the same")
        self.assertEqual(stamp(200, "<HTML><body>x</body></HTML>", "text/html"), "<HTML data-romp-served=200><body>x</body></HTML>", "the tag's case does not matter")
        for code, body, ctype in [(403, "forbidden: token required", "text/plain"), (500, "Traceback (most recent call last):\n", "text/plain"), (502, "<html><body>bad gateway</body></html>", "text/html"),
                                  (200, "forbidden-looking text", "text/plain"), (200, '{"ok": true}', "application/json"), (200, "<!DOCTYPE html>no root tag here", "text/html"), (404, "<html><body>not found</body></html>", "text/html; charset=utf-8")]:
            self.assertEqual(stamp(code, body, ctype), body, "%d %s: untouched (a stamp on this would call a non-200, a non-document or a rootless body a 200 the kernel served)" % (code, ctype))
        self.assertIn("body = _stamp_served_html(code, body, ctype)", inspect.getsource(km.Handler._send), "the one call, at the top of the one place every response leaves")

    def test_a_failure_judged_after_a_flip_to_the_desktop_re_promotes_there_and_the_phone_armed_detectors_are_inert(self):
        # Family one (review round 3): the layout is read when the failure is JUDGED, not when the promotion was armed, across an actual media-query
        # flip (mobileOn() real over the MediaQueryList fake). (A) fail on the phone, flip: the flip hands the parked url to data-src and promotes,
        # the phone's failed class is cleared by the promotion, the phone's listener is inert on the desktop's load, and the flip back shows a
        # loaded pane with no failed overlay. (B) flip while loading, the abort landing after it: failed() reads the desktop, parks under data-src
        # and promotes once, with its own detectors (review round 4, regression-1); when that fails too the bound holds (the src stays, nothing
        # promotes a third time, the phone's backstop is inert on its token) and the flip back parks the recorded pane with the failed state, from
        # which the tab tap, the overlay tap and the Try again button each promote it again; before round 3 the pane was left with neither src
        # nor data-src, and at round 3's head with a src over a dead document and every road dead.
        o = _lazy(self.seed, _LAZY_FLIP_FAILED_DRIVER)
        pf = o["phoneFailed"]
        self.assertEqual((pf["mobile"], pf["src"], pf["lazy"], pf["div"], pf["bodyFailed"]), (True, None, "/waiting", ["failed"], True), "failed on the phone: re-parked under data-lazy-src, the failed state painted")
        fa = o["flippedA"]
        self.assertEqual((fa["mobile"], fa["src"], fa["lazy"], fa["dataSrc"], fa["div"]), (False, "/waiting", None, "/waiting", []), "the flip to the desktop: lazyFlip hands the url back to data-src and promotes it, and the promotion clears the phone's failed class")
        self.assertEqual(fa["sets"]["waiting"], 2, "the desktop's promotion is the second src set")
        self.assertFalse(fa["bodyLoading"], "the desktop promotion paints no loader")
        da = o["desktopLoadedA"]
        self.assertEqual((da["src"], da["div"], da["rows"]), ("/waiting", [], pf["rows"]), "the desktop's load: the phone's listener (token 1) is inert over the second promotion; no new row, nothing re-parked")
        ba = o["backA"]
        self.assertEqual((ba["mobile"], ba["src"], ba["div"], ba["bodyFailed"], ba["bodyLoading"], ba["sets"]["waiting"]), (True, "/waiting", [], False, False, 2), "back on the phone the tab shows a loaded pane: no failed overlay, no loader, no third promotion")
        o = _lazy(self.seed, _LAZY_FLIP_MIDLOAD_DRIVER)   # (B), its own run: a desktop flip promotes every parked pane, so (A) leaves none to tap
        fb = o["flippedB"]
        self.assertEqual((fb["mobile"], fb["src"], fb["div"], fb["sets"], fb["bodyLoading"]), (False, "/fleet", ["loading"], 0, True), "the flip mid-load leaves the loading promotion standing (lazyFlip refuses a pane with a src)")
        db = o["desktopFailedB"]
        self.assertEqual((db["src"], db["lazy"], db["dataSrc"], db["div"]), ("/fleet", None, "/fleet", []), "the failure judged on the desktop: the url back under data-src (the attribute the desktop reads), promoted again at once, no failed class, no loading class (the grid paints none) (before round 3: neither src nor data-src, an empty column with no road)")
        self.assertEqual(db["sets"], 1, "one re-promotion")
        self.assertEqual(db["rows"], [{"pane": "fleet", "via": "load", "n": 1}], "the failure is counted and said")
        self.assertEqual((db["listeners"], db["backstops"]), (fb["listeners"] + 1, fb["backstops"] + 1), "the desktop's re-promotion armed its own load listener and its own 30 s backstop (review round 4: round 3 armed none off the phone, so its failure went unjudged)")
        sb = o["secondFailB"]
        self.assertEqual((sb["src"], sb["lazy"], sb["dataSrc"], sb["div"], sb["sets"]), ("/fleet", None, "/fleet", [], 1), "the desktop's re-promotion fails too, never committing (no load event): judged by its own 30 s backstop (round 3 armed none off the phone, and a class-guarded backstop would return on the desktop's missing loading class), and the episode's bound holds: the src stays (the browser's own page, as a desktop failure always showed), no third promotion (without the bound: promote, fail, promote, without end)")
        self.assertEqual(sb["rows"], [{"pane": "fleet", "via": "load", "n": 1}, {"pane": "fleet", "via": "backstop", "n": 2}], "the second failure is counted and said too, via the backstop (round 3 left it unsaid)")
        self.assertEqual(o["backstopB"], sb, "every backstop fires again: the phone's is inert on its stale token, the desktop's on its verdict already given (PEND)")
        bb = o["backB"]
        self.assertEqual((bb["mobile"], bb["src"], bb["lazy"], bb["dataSrc"], bb["div"], bb["bodyFailed"], bb["bodyLoading"], bb["sets"]), (True, None, "/fleet", None, ["failed"], True, False, 1), "the flip back to the phone: the recorded failure parks the pane under data-lazy-src with the failed state painted over the shown tab (before: a src over a dead document, no state, and every road dead for the page's life)")
        self.assertEqual((bb["msg"], bb["retryHidden"]), ("Still not loading. Try again, or reload the page.", False), "the episode's second failure and later: the copy offers the reload, the button is shown")
        tb = o["tabTapB"]
        self.assertEqual((tb["src"], tb["lazy"], tb["div"], tb["bodyFailed"], tb["bodyLoading"], tb["sets"]), ("/fleet", None, ["loading"], False, True, 2), "road (i), the tab tap: promoted again as a first tap would")
        pf = o["phoneFailB"]
        self.assertEqual((pf["src"], pf["div"], pf["bodyFailed"], pf["rows"][-1]), (None, ["failed"], True, {"pane": "fleet", "via": "load", "n": 3}), "...its failure on the phone paints the failed state")
        ob = o["overlayTapB"]
        self.assertEqual((ob["src"], ob["div"], ob["sets"]), ("/fleet", ["loading"], 3), "road (ii), the overlay tap: promoted again")
        self.assertEqual(o["phoneFailB2"]["rows"][-1], {"pane": "fleet", "via": "load", "n": 4})
        ub = o["buttonTapB"]
        self.assertEqual((ub["src"], ub["div"], ub["retryHidden"], ub["sets"]), ("/fleet", ["loading"], True, 4), "road (iii), the Try again button: promoted again, the button hidden while it loads")
        rb = o["recoveredB"]
        self.assertEqual((rb["src"], rb["div"], rb["bodyFailed"], rb["bodyLoading"], rb["msg"], rb["sets"], rb["rows"]), ("/fleet", [], False, False, "", 4, o["phoneFailB2"]["rows"]), "the good load: recovered, no overlay, no new row")
        self.assertEqual(o["mirrorB"], dict(rb, mobile=True), "the mirror: a flip there and back over the loaded pane parks nothing (nothing recorded)")
        js = km._LANDING_MOBILE_JS
        self.assertIn("function failed(k,via){var f=F[k];if(!f)return;var mob=mobileOn();", js, "the layout is read at fire time")
        self.assertIn("f.setAttribute(mob?LAZY:'data-src',URLS[k]);", js)
        self.assertIn("var again=!mob&&EPI[k]<2,keep=!mob&&!again;", js, "the desktop's bound: one re-promotion per episode, the src kept at the bound")
        self.assertIn("DEAD[k]=keep?TOK[k]:0;", js, "the failure at the bound is recorded under its promotion's token")
        self.assertIn("else if(DEAD[lk3]&&DEAD[lk3]===TOK[lk3]){", js, "lazyFlip's phone branch parks the recorded pane")
        self.assertIn("if(TOK[k]!==tok||PEND[k]!==tok)return;var s=docState(f);", js, "the backstop's guard is the pending verdict, not the phone's paint class")
        self.assertNotIn("if(mobileOn()){try{var d=paneDiv(f);if(d)d.classList.add('loading');}catch(e){}\nf.addEventListener", js, "the detectors are not under the phone gate")
        self.assertIn("if(mob)d.classList.add('failed');else d.classList.remove('failed');", js)
        self.assertIn("if(again)promote(k);}", js, "the desktop promotes once per episode (review round 4: the bound)")
        self.assertIn("URLS[k]=u;var tok=TOK[k]=(TOK[k]||0)+1;", js, "the token is minted on every promotion, before the layout branch")

    def test_a_feed_recorded_dead_on_the_desktop_is_parked_by_the_flip_back_and_its_tab_tap_promotes_it(self):
        # review round 4 verify (2026-09-19): the feed goes through promote() (the phone boot's, the desktop flip's) and so can be recorded DEAD,
        # but lazyFlip's phone branch skipped it with the chat before the DEAD check, so the ruled dead end (the tab tap inert for the page's
        # life over a src on a dead document) survived for the feed alone. Its exemption is from the off-screen parking, not from a failure.
        o = _lazy(self.seed, _LAZY_FEED_DEAD_DRIVER)
        b = o["boot"]
        self.assertEqual((b["mobile"], b["src"], b["lazy"], b["sets"], b["tab"]), (True, "/feed", None, 1, "chat"), "the phone boot promoted the feed off screen (its exemption), the chat showing")
        bf = o["bootFailed"]
        self.assertEqual((bf["src"], bf["lazy"], bf["dataSrc"], bf["div"], bf["rows"], bf["bodyFailed"]), (None, "/feed", None, ["failed"], [{"pane": "feed", "via": "load", "n": 1}], False), "the boot's fetch failed: parked under data-lazy-src with the failed state (data-src dropped too), nothing painted over the chat")
        fl = o["flipped"]
        self.assertEqual((fl["mobile"], fl["src"], fl["lazy"], fl["dataSrc"], fl["div"], fl["sets"]), (False, "/feed", None, "/feed", [], 2), "the flip to the desktop: the grid shows the feed, so the url goes back to data-src and it is promoted")
        df = o["desktopFailed"]
        self.assertEqual((df["src"], df["dataSrc"], df["div"], df["sets"], df["rows"][-1]), ("/feed", "/feed", [], 2, {"pane": "feed", "via": "load", "n": 2}), "the desktop's promotion fails too: the episode's bound (the phone's failure counted), the src kept, the failure recorded")
        bk = o["back"]
        self.assertEqual((bk["mobile"], bk["src"], bk["lazy"], bk["dataSrc"], bk["div"], bk["sets"], bk["bodyFailed"]), (True, None, "/feed", None, ["failed"], 2, False), "the flip back parks the recorded feed like any pane: no src over the dead document, the url under data-lazy-src, the failed state on its div (not painted: the chat is the shown tab) (before: skipped with the chat, the src stood)")
        tt = o["tabTap"]
        self.assertEqual((tt["tab"], tt["src"], tt["lazy"], tt["div"], tt["sets"], tt["bodyLoading"], tt["bodyFailed"]), ("feed", "/feed", None, ["loading"], 3, True, False), "the Feed tab tap promotes it again, the loader painted (before: promote() refused the src and the tap painted nothing)")
        r = o["recovered"]
        self.assertEqual((r["div"], r["sets"], r["bodyLoading"], r["bodyFailed"], r["rows"]), ([], 3, False, False, df["rows"]), "the good load: recovered, no new row")
        js = km._LANDING_MOBILE_JS
        self.assertIn("if(!lf3||lk3==='chat')continue;", js, "the phone branch skips the chat alone (the chat never goes through promote(), so it is never recorded)")
        self.assertIn("if(lk3!=='feed'&&lu3&&!lf3.getAttribute('src')){lf3.setAttribute(LAZY,lu3);lf3.removeAttribute('data-src');}", js, "the feed's exemption gates the unloaded parking alone")

    def test_a_failure_judged_on_the_phone_after_a_desktop_promotion_leaves_no_data_src_for_the_gears_reconcile_to_promote_unjudged(self):
        # review round 4 verify: lazyFlip's desktop branch sets data-src and promote() removes data-lazy-src alone, so a desktop-promoted pane
        # whose verdict landed on the phone held BOTH attributes after failed()'s re-park; the controller's reconcile then set its src from
        # data-src on any gear save, a promotion with no token, listener or backstop, and on an engine with no load event for a failed
        # navigation the failed state stood for the page's life while every retry road ran promote() against a src. failed() drops the
        # attribute the other layout reads, so promote() with its detectors is the one promotion road for a failed pane.
        o = _lazy(self.seed, _LAZY_BOTH_ATTRS_DRIVER)
        d = o["desktop"]
        self.assertEqual((d["mobile"], d["src"], d["lazy"], d["dataSrc"], d["div"], d["sets"]), (False, "/fleet", None, "/fleet", [], 1), "the flip to the desktop: promoted from data-src, which stays on the frame while it loads")
        be = o["backEarly"]
        self.assertEqual((be["mobile"], be["src"], be["dataSrc"], be["div"], be["sets"]), (True, "/fleet", "/fleet", ["loading"], 1), "the flip back before the verdict leaves the promotion standing, wearing the loader (its verdict is owed)")
        pv = o["phoneVerdict"]
        self.assertEqual((pv["src"], pv["lazy"], pv["dataSrc"], pv["div"], pv["sets"]), (None, "/fleet", None, ["failed"], 1), "the verdict on the phone: parked under data-lazy-src with the failed state, and data-src dropped (before: both attributes)")
        self.assertEqual(o["afterSave"], pv, "a gear save (the romp:settings storage event): the controller's reconcile finds no data-src and sets no src (before: a second src set with no listener and no backstop added)")
        self.assertEqual(o["afterBackstops"], pv, "every backstop: nothing pending")
        tt = o["tabTap"]
        self.assertEqual((tt["src"], tt["lazy"], tt["div"], tt["sets"], tt["listeners"], tt["backstops"]), ("/fleet", None, ["loading"], 2, pv["listeners"] + 1, pv["backstops"] + 1), "the tab tap is the promotion road, with its own listener and backstop")
        js = km._LANDING_MOBILE_JS
        self.assertIn("if(URLS[k]){f.setAttribute(mob?LAZY:'data-src',URLS[k]);f.removeAttribute(mob?'data-src':LAZY);}", js, "failed() re-parks under this layout's attribute and drops the other's")

    def test_a_flip_back_while_the_desktops_promotion_is_in_flight_paints_the_loader_for_the_shown_tab(self):
        # review round 4 verify: the grid's promote() paints no loading class, lazyFlip's phone branch left a frame with a src alone, and the
        # tab tap's promote() refuses a src, so paintLoading found nothing: a blank pane whose taps did nothing until the verdict (WebKit: up to
        # 30 s, the backstop). The phone branch paints the loader for a promotion still owed its verdict (PEND), keyed on the recorded
        # promotion, never on a read of the document; loaded() and failed() take it off as ever.
        o = _lazy(self.seed, _LAZY_FLIP_INFLIGHT_DRIVER)
        dr = o["desktopRepromoted"]
        self.assertEqual((dr["mobile"], dr["src"], dr["dataSrc"], dr["div"], dr["sets"], dr["bodyLoading"], dr["rows"]), (False, "/fleet", "/fleet", [], 2, False, [{"pane": "fleet", "via": "load", "n": 1}]), "the abort landed on the desktop: re-promoted there with no loading class (the grid paints none)")
        bi = o["backInFlight"]
        self.assertEqual((bi["mobile"], bi["src"], bi["div"], bi["sets"], bi["bodyLoading"], bi["bodyFailed"]), (True, "/fleet", ["loading"], 2, True, False), "the flip back before the verdict: the loader painted over the shown Outline tab (before: nothing, a blank pane)")
        self.assertEqual(o["tapInFlight"], bi, "the tab tap: promote() refuses the src, no new promotion, the loader stands")
        v = o["verdict"]
        self.assertEqual((v["src"], v["lazy"], v["dataSrc"], v["div"], v["bodyFailed"], v["bodyLoading"], v["sets"], v["rows"][-1]), (None, "/fleet", None, ["failed"], True, False, 2, {"pane": "fleet", "via": "load", "n": 2}), "the verdict on the phone: the failed state, the loader off")
        rt = o["retap"]
        self.assertEqual((rt["src"], rt["div"], rt["sets"], rt["bodyLoading"]), ("/fleet", ["loading"], 3, True), "the re-tap promotes it again")
        self.assertEqual((o["recovered"]["div"], o["recovered"]["bodyLoading"], o["recovered"]["bodyFailed"], o["recovered"]["sets"]), ([], False, False, 3))
        js = km._LANDING_MOBILE_JS
        self.assertIn("else if(PEND[lk3]&&PEND[lk3]===TOK[lk3]&&lf3.getAttribute('src')){var pd3=paneDiv(lf3);if(pd3)pd3.classList.add('loading');}", js, "the loader for a promotion still owed its verdict, keyed on PEND")

    def test_the_failed_copy_counts_this_episode_and_the_retry_is_a_button_shown_in_the_failed_state_alone(self):
        # correctness-1 (review round 3): FAILS, the page-life count, never resets, so a pane that failed, loaded and failed again read the
        # second copy ("Still not loading… reload the page") about a pane that had worked a moment ago; EPI counts the failures since the last
        # load and picks the copy, while the row keeps n from FAILS (docs/read-side.md pins its meaning). ui-1: the retry is a real button.
        o = _lazy(self.seed, _LAZY_EPISODE_DRIVER)
        self.assertEqual((o["loading"]["div"], o["loading"]["retryHidden"], o["loading"]["msg"]), (["loading"], True, ""), "while the document loads the button is hidden (no focusable control under the loader)")
        f1 = o["failed1"]
        self.assertEqual((f1["div"], f1["bodyFailed"], f1["retryHidden"]), (["failed"], True, False), "the failed state shows the button")
        self.assertEqual(f1["msg"], "Couldn't load this pane.", "the first failure's copy")
        self.assertEqual(f1["rows"], [{"pane": "waiting", "via": "load", "n": 1}])
        r = o["retried"]
        self.assertEqual((r["src"], r["div"], r["retryHidden"], r["sets"]["waiting"]), ("/waiting", ["loading"], True, 2), "the button's click retries: a second promotion, the button hidden again")
        l = o["loaded"]
        self.assertEqual((l["div"], l["bodyFailed"], l["msg"], l["retryHidden"]), ([], False, "", True), "the good load ends the episode")
        f2 = o["failed2"]
        self.assertEqual(f2["msg"], "Couldn't load this pane.", "a failure after a good load is this episode's FIRST: the first copy (before: the second, from the page-life count)")
        self.assertEqual(f2["rows"], f1["rows"] + [{"pane": "waiting", "via": "load", "n": 2}], "…while the row's n keeps counting the page's failures (FAILS is untouched by the load)")
        self.assertEqual((f2["div"], f2["retryHidden"]), (["failed"], False))

    def test_the_keyboards_retry_keeps_its_focus_across_the_re_failure_and_nothing_else_moves_focus_onto_the_button(self):
        # ui-1 (review round 4, 2026-09-19): paintLoading hides #pane-load-retry while the retry loads, and hiding the focused button moves focus
        # to the document body in all three engines with nothing restoring it when the failed state repaints, so round 3's keyboard road survived
        # exactly one activation. The button's click sets a flag; the failed paint that shows the button again focuses it once on that flag; a
        # load and a tab switch clear the flag (the refuter's amendment: without that a later pane's first failure stole focus onto the button).
        # The harness models document.activeElement over the button alone; the served leg reads the real one (test_return_from_background_served.py).
        o = _lazy(self.seed, _LAZY_FOCUS_DRIVER)
        self.assertEqual((o["focused"]["retryHidden"], o["focused"]["active"]), (False, "retry"), "the failed state's button, focused by the keyboard walk")
        self.assertEqual((o["retrying"]["retryHidden"], o["retrying"]["active"], o["retrying"]["div"]), (True, "body", ["loading"]), "Enter retries: the button is hidden while the retry loads and the focus falls to the body, as every engine does")
        r = o["refailed"]
        self.assertEqual((r["bodyFailed"], r["retryHidden"], r["msg"], r["active"]), (True, False, "Still not loading. Try again, or reload the page.", "retry"), "the re-failure's paint shows the button again and puts the focus back on it (before: the body, so the keyboard road survived one activation)")
        self.assertEqual((o["loaded"]["retryHidden"], o["loaded"]["active"]), (True, "body"), "the good load hides the button")
        sl = o["sameLater"]
        self.assertEqual((sl["bodyFailed"], sl["retryHidden"], sl["active"]), (True, False, "body"), "a later failure of the same pane after its load, with no tab switch between: the LOAD retired the flag, so the failed paint focuses nothing (the refuter's amendment)")
        lf = o["laterFirst"]
        self.assertEqual((lf["tab"], lf["bodyFailed"], lf["retryHidden"], lf["active"]), ("fleet", True, False, "body"), "a later pane's first failure shows the button and takes no focus: no gesture asked for it (the load retired the flag)")
        self.assertEqual(o["overlayRefail"]["active"], "body", "the overlay tap is a pointer gesture: its re-failure moves no focus")
        self.assertEqual((o["switchedRefail"]["msg"], o["switchedRefail"]["active"]), ("Still not loading. Try again, or reload the page.", "body"), "a tab switch after the keyboard's retry retires it: the failure that lands after the switch focuses nothing")
        js = km._LANDING_MOBILE_JS
        self.assertIn("var rb=document.getElementById('pane-load-retry');if(rb){rb.hidden=!bad;if(bad&&RFOC){RFOC=false;try{rb.focus();}catch(e){}}}", js, "the failed paint restores the focus once, on the flag")
        self.assertIn("retry();RFOC=true;});", js, "the button's click sets the flag after its retry (whose show() clears it)")
        self.assertIn("function loaded(k){EPI[k]=0;PEND[k]=0;DEAD[k]=0;RFOC=false;", js, "a load clears it")
        sw = "\nRFOC=false;   // [fork] review round 4 (2026-09-19, ui-1)"
        self.assertIn(sw, js, "a tab switch clears it, on a fork line of its own inside show()")
        self.assertLess(js.index("pw.__rompPaneShown();}catch(e){}"), js.index(sw), "…after the show hook's line")
        self.assertLess(js.index(sw), js.index("for(var i=0;i<B.length;i++)B[i].classList.toggle('on',B[i].getAttribute('data-pane')===p);"), "…and before the upstream tab-class line, which is untouched")

    def test_the_promotion_token_makes_a_stale_listener_and_a_stale_backstop_inert_across_a_retry(self):
        # HIGH 2, review round 2 closeout: the two `if(TOK[k]!==tok)return;` guards were unpinned (the failed-load case above reaches its
        # second failure through the backstop, whose loading guard masks a stale timer). Here the stale backstop fires over a retry that
        # is still loading, and the stale listener fires beside the live one on the retry's own failure.
        o = _lazy(self.seed, _LAZY_TOKEN_DRIVER)
        f1 = o["firstFailure"]
        self.assertEqual((f1["src"], f1["rows"], f1["backstops"]), (None, [{"pane": "waiting", "via": "load", "n": 1}], 2), "the first failure: one row, two backstops (the feed's and this promotion's)")
        self.assertGreaterEqual(f1["listeners"], 1, "the element carries load listeners (the promotion's beside the boot wirings' own: the panes-word hook, the focus ring, Escape)")
        r = o["retry"]
        self.assertEqual((r["src"], r["div"], r["listeners"], r["backstops"]), ("/waiting", ["loading"], f1["listeners"] + 1, 3), "the retry adds a second promotion listener to the same element and a third backstop; the first promotion's stay live")
        s = o["staleBackstop"]
        self.assertEqual((s["src"], s["lazy"], s["div"], s["rows"]), ("/waiting", None, ["loading"], f1["rows"]), "the first promotion's backstop fires over the still-loading retry (its document at about:blank): inert on its stale token; without the guard it re-parks the retry via backstop")
        s2 = o["secondFailure"]
        self.assertEqual(s2["rows"], [{"pane": "waiting", "via": "load", "n": 1}, {"pane": "waiting", "via": "load", "n": 2}], "the retry's failure fires BOTH listeners: one new row, n 2; without the guard the stale listener files a third row and n runs to 3")
        self.assertEqual((s2["src"], s2["div"], s2["msg"]), (None, ["failed"], "Still not loading. Try again, or reload the page."))
        g = o["goodLoad"]
        self.assertEqual((g["src"], g["div"], g["bodyFailed"], g["sets"]["waiting"], g["rows"], g["listeners"]), ("/waiting", [], False, 3, s2["rows"], f1["listeners"] + 2), "the third promotion's good load: three promotion listeners fire, the pane loads, no new row")
        self.assertEqual(o["mirror"], g, "every backstop armed so far fires over the loaded pane: nothing moves")

    def test_the_show_calls_the_shown_panes_hook_before_the_re_tell_on_the_phone_alone(self):
        # D3 (review round 2, 2026-09-19): the feed's held first paint lands in the tap's own task (feed.ts window.__rompPaneShown), so the
        # compositor never shows the empty pane; the re-tell that follows is the belt for a document with no hook yet
        o = _lazy(self.seed, _LAZY_SHOWN_DRIVER)
        self.assertEqual(o["feedTap"], {"tab": "feed", "log": ["shown:feed", "tell"], "mOn": True}, "the hook runs after the m-on toggle and before the re-tell")
        self.assertEqual(o["waitingTap"]["log"], ["src:waiting", "tell"], "a pane without the hook: the promotion and the tell, nothing else")
        self.assertEqual(o["desktopShow"]["log"], ["tell"], "off the phone layout show() calls no hook (the desktop grid paints its first frame on its own)")

    def test_the_desktop_loads_every_pane_at_boot_as_before_with_no_loading_state(self):
        o = _lazy("STORE['romp:settings'] = JSON.stringify({ showFilesControl: true });", _LAZY_DESKTOP_DRIVER, phone=False)
        b = o["boot"]
        self.assertEqual(sorted(b["src"]), ["chat", "feed", "files", "fleet", "timeline", "waiting"], "the six panes were read")
        self.assertEqual(b["src"], {k: "/" + k for k in b["src"]}, "every pane has its document at boot on the desktop")
        self.assertEqual(b["lazy"], {k: None for k in b["lazy"]}, "nothing is parked")
        self.assertEqual(b["sets"], {"waiting": 1, "files": 1, "timeline": 1, "fleet": 1, "feed": 1}, "the desktop-panes script promotes the Waiting and Files panes (no gear row; its own script since review round 1), the controller the three optional panes")
        self.assertEqual(b["loading"], []); self.assertFalse(b["bodyLoading"])
        self.assertEqual(o["tap"], {"sets": b["sets"], "loading": [], "bodyLoading": False}, "a switch on the desktop layout promotes nothing and paints no loader")

    def test_the_desktop_promotion_of_waiting_and_files_survives_a_throw_in_the_mobile_script(self):
        # D7 (review round 1, 2026-09-19, regression-5): before, the promotion was the mobile script's last line, so a throw anywhere in
        # its 295 lines (here the tab bar's button lookup) left both panes with no src on the desktop. The seed makes the bar's
        # querySelectorAll throw; the isolation is proven by the recorded throw, not by a run that happened to reach the end.
        o = _lazy("STORE['romp:settings'] = JSON.stringify({ showFilesControl: true }); BAR.querySelectorAll = () => { throw new Error('lab abort'); };",
                  _LAZY_ABORT_DRIVER, phone=False, abort_mobile=True)
        self.assertIn("lab abort", o["threw"] or "", "the mobile script threw before its last line (the seed's abort took)")
        self.assertEqual(o["boot"]["mobileTab"], "undefined", "…and never reached show(): its exports are absent")
        self.assertEqual((o["boot"]["src"]["waiting"], o["boot"]["src"]["files"]), ("/waiting", "/files"), "the Waiting and Files panes load all the same: their promotion is its own script")
        self.assertEqual(o["boot"]["sets"], {"waiting": 1, "files": 1, "timeline": 1, "fleet": 1, "feed": 1}, "…and the controller's three optional panes load through its own line")

    def test_a_flip_to_the_desktop_layout_promotes_every_lazy_pane(self):
        o = _lazy("STORE['romp:settings'] = JSON.stringify({ showFilesControl: true }); STORE['romp-mobile-tab'] = 'chat';", _LAZY_FLIP_DRIVER)
        self.assertEqual(o["boot"]["lazy"], {"chat": None, "feed": None, "files": "/files", "timeline": "/timeline", "fleet": "/fleet", "waiting": "/waiting"})
        f = o["flipped"]
        self.assertEqual(sorted(f["src"]), ["chat", "feed", "files", "fleet", "timeline", "waiting"], "the six panes were read")
        self.assertEqual(f["src"], {k: "/" + k for k in f["src"]}, "the grid shows the panes without a tap: all promoted on the media query's change event")
        self.assertEqual(f["lazy"], {k: None for k in f["lazy"]})
        self.assertEqual(f["sets"], {"feed": 1, "timeline": 1, "fleet": 1, "waiting": 1, "files": 1})
        self.assertEqual(f["listeners"], 2, "the re-tell and the promotion, one listener each")
        self.assertEqual(f["loading"], ["feed"], "the flip's promotions add no loading state off the phone layout (the feed's is the boot's, until its load event)")


if __name__ == "__main__":
    unittest.main()
