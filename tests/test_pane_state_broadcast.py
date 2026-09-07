#!/usr/bin/env python3
"""The shell tells its panes which panes are on (the user 2026-09-04). A file link clicked in the
chat while the Files pane was OPEN still opened as a modal over the chat, because the route was
decided by the fileLinkPane setting alone — and the chat had no way to know the pane was up. The
shell owns pane state (_LANDING_COLLAPSE_JS: the po object, apply(), __rompPaneToggle), so the shell
now broadcasts it: {romp:'panes',on:{key:bool}} into every pane iframe on every apply() — the exact
event of the set changing (a toggle, the boot apply, another tab's storage event) — and again on each
iframe's own load, so a pane that boots or reloads after the shell hears the current set. The chat
caches it and routes by it (render.ts fileLinkRoute, pinned in ui/webview/file-view.test.ts).

The key set is _PANE_ORDER's, spliced by _landing() — the ONE list of panes — so a future pane is
broadcast without anyone remembering this block. Iframe-load over a request/answer handshake: it is
the shell-side event the focus ring and Esc wiring already key on ("wire now + on every (re)load"),
it needs no new vocabulary in every pane, and it covers a pane's own reload too."""
import json
import os
import re
import tempfile
import unittest
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
SourceFileLoader("romp_event_model", os.path.join(BIN, "romp-event-model")).load_module()
SourceFileLoader("romp_judge", os.path.join(BIN, "romp-judge")).load_module()
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
km = SourceFileLoader("romp_kernel_psb", os.path.join(BIN, "romp-kernel")).load_module()


def _collapse_js(html):
    """The pane controller's script as the landing page ships it (keys spliced)."""
    start = html.index("var PK='romp-panes'")
    return html[start:html.index("</script>", start)]


def _fn(js, name):
    """The body of a top-level `function name(...){...}` in the controller, up to the next `function`."""
    head = "function %s(" % name
    body = js[js.index(head):]
    nxt = body.find("\n  function ", 1)
    return body if nxt < 0 else body[:nxt]


class Broadcast(unittest.TestCase):
    def setUp(self):
        self.html = km._landing()
        self.js = _collapse_js(self.html)
        self.keys = [k for k, _ in km._PANE_ORDER]

    def test_the_message_shape_is_romp_panes_with_a_key_to_bool_map(self):
        # the shape: one bool per KEY, under `on` (what each bool MEANS per layout is MobileVisibility's pin)
        msg = _fn(self.js, "panesMsg")
        self.assertIn("var on={};KEYS.forEach(function(k){on[k]=", msg)
        self.assertIn("return {romp:'panes',on:on};}", msg)

    def test_apply_broadcasts_to_every_pane_iframe(self):
        # apply() is the one place the set changes take effect (every toggle, the boot apply, storage) —
        # keying the broadcast on it makes it the exact event of a pane changing, never a poll
        apply = _fn(self.js, "apply")
        self.assertTrue(apply.rstrip().endswith("broadcast();\n  }"), "apply() ends by broadcasting the set:\n" + apply)
        self.assertIn("function broadcast(){var m=panesMsg();KEYS.forEach(function(k){tell(document.getElementById('f-'+k),m);});}", self.js)
        self.assertIn("function tell(f,m){try{f&&f.contentWindow&&f.contentWindow.postMessage(m,'*');}catch(e){}}", self.js)
        # the boot apply runs (so the panes already loaded hear the initial set)
        self.assertIn("\n  apply();\n", self.js)

    def test_a_pane_that_loads_after_the_shell_hears_the_set(self):
        # the iframe-load path: a chat that boots (or reloads) after the shell's boot apply would otherwise
        # never learn the set until the next toggle
        self.assertIn("KEYS.forEach(function(k){var f=document.getElementById('f-'+k);if(f)f.addEventListener('load',function(){tell(f,panesMsg());});});", self.js)
        # …wired AFTER the boot apply, so both orders (iframe loaded first / shell first) are covered
        self.assertLess(self.js.index("\n  apply();\n"), self.js.index("f.addEventListener('load',function(){tell(f,panesMsg());})"))

    def test_the_key_set_is_pane_order_spliced_by_the_landing(self):
        # derived from the one list, never a second hand-written one: the shipped KEYS literal IS _PANE_ORDER's
        # keys, the placeholder is gone, and the splice is the landing's (not a module-level copy)
        self.assertIn("var KEYS=" + json.dumps(self.keys) + ";", self.js)
        self.assertNotIn("__PANE_KEYS__", self.html)
        self.assertIn("__PANE_KEYS__", km._LANDING_COLLAPSE_JS, "the template keeps the placeholder")
        src = open(os.path.join(BIN, "romp-kernel")).read()
        self.assertIn('_LANDING_COLLAPSE_JS.replace("__PANE_KEYS__", json.dumps([k for k, _ in _PANE_ORDER]))', src)
        self.assertEqual(len(self.keys), 6)

    def test_every_key_has_the_iframe_the_broadcast_addresses(self):
        # the broadcast derives each target as 'f-'+key; every pane in _PANE_ORDER must ship an iframe by
        # that id, or a pane is silently never told (and a future pane added off-scheme would be missed)
        ids = set(re.findall(r"<iframe id=(f-\w+)", self.html))
        for k in self.keys:
            self.assertIn("f-" + k, ids, "no iframe for pane key %r" % k)
        # …and the po object names the same keys, so !!po[k] is a real bit for each
        po = re.search(r"po=\{([^}]*)\}", self.js).group(1)
        self.assertEqual(sorted(re.findall(r"(\w+):", po)), sorted(self.keys))

    def test_a_no_change_toggle_is_silent(self):
        # the viewFile relay brings the Files pane forward with __rompPaneToggle('files',true) on every click
        # routed there — on an already-open pane that is no change, so no re-apply and no broadcast
        # claiming one (a message is a claim that something changed; the panes must be able to trust it)
        toggle = _fn(self.js, "togglePane")
        self.assertIn("var nv=(to===undefined)?!po[k]:!!to;\n    if(nv===!!po[k])return;", toggle)
        self.assertLess(toggle.index("if(nv===!!po[k])return;"), toggle.index("po[k]=nv;apply();saveP();"))

    def test_the_files_relay_still_brings_a_closed_pane_forward(self):
        # the receiving end is unchanged: the setting "pane" on a CLOSED Files pane opens it (idempotent on an
        # open one, per the guard above) and forwards the click — nothing here touches the feed route's
        # was-off / ack / restore machinery
        js = km._LANDING_SETTINGS_JS
        head = "if(m.romp==='viewFile'&&m.pane==='pane'){var ff=document.getElementById('f-files');"
        branch = js.split(head)[1].split("else if(m.romp==='viewFile')")[0]
        self.assertIn("window.__rompPaneToggle&&window.__rompPaneToggle('files',true)", branch)
        for tok in ("__rompFeedWasOff", "viewFileOpened", "viewFileClosed"):
            self.assertNotIn(tok, "\n".join(l for l in branch.splitlines() if not l.lstrip().startswith("//")))


class MobileVisibility(unittest.TestCase):
    """On a phone (the mobile layout: one tab at a time, no rail, the po-* classes ignored) po.files is an
    invisible, sticky bit — an iPad rotated from desktop-with-Files-open to portrait, or an earlier
    __rompPaneToggle('files',true), leaves it true with nothing on screen showing it, and every chat
    file link would silently override the setting into the Files tab (the 2026-09-04 review). RULING:
    the broadcast reports VISIBILITY, not the flag — desktop → po[k]; mobile → k is the current tab
    (the value show() sets) — and fires from show() and on the layout flipping too, since both change
    what is on screen with no toggle. The layout is detected the way the shell already decides it: the
    stylesheet's own mobile media query, one constant spliced into both."""

    def setUp(self):
        self.html = km._landing()
        self.js = _collapse_js(self.html)
        self.mob = self.html[self.html.index("var bar=document.getElementById('mtabs');"):]
        self.mob = self.mob[:self.mob.index("</script>")]

    def test_on_means_on_screen_in_either_layout(self):
        self.assertIn("function panesMsg(){var mob=!!(window.__rompMobileOn&&window.__rompMobileOn()),tab=mob?document.body.getAttribute('data-tab'):null;\n"
                      "    var on={};KEYS.forEach(function(k){on[k]=mob?(k===tab):!!po[k];});return {romp:'panes',on:on};}", self.js)
        # executed: the rule as the source spells it, over the rows that motivated it
        def on(keys, po, mob, tab):
            return {k: (k == tab) if mob else bool(po.get(k)) for k in keys}
        keys = [k for k, _ in km._PANE_ORDER]
        po = {"chat": True, "feed": True, "timeline": True, "fleet": False, "waiting": False, "files": True}
        self.assertTrue(on(keys, po, False, None)["files"], "desktop: the toggled-on Files column IS on screen")
        self.assertFalse(on(keys, po, True, "chat")["files"], "the rotated iPad: po.files true, phone on the chat tab → not on screen")
        self.assertTrue(on(keys, po, True, "files")["files"], "phone on the Files tab → on screen")
        self.assertFalse(on(keys, {**po, "files": False}, True, "files")["chat"], "phone: only the showing tab is on, whatever po says")
        self.assertEqual(sum(on(keys, po, True, "feed").values()), 1, "mobile: exactly one pane on screen")

    def test_the_layout_is_the_stylesheets_own_media_query(self):
        # one constant lays out the grid AND answers the JS — never two strings that can drift
        self.assertIn("@media " + km._MOBILE_MQ + "{", self.html)
        self.assertIn("var MQ=(window.matchMedia&&matchMedia(" + json.dumps(km._MOBILE_MQ) + "))||null;", self.mob)
        self.assertIn("function mobileOn(){return !!(MQ&&MQ.matches);}\nwindow.__rompMobileOn=mobileOn;\nif(!bar)return;", self.mob,
                      "__rompMobileOn exists even when the tab bar is missing (answers false)")
        self.assertNotIn("__MOBILE_MQ__", self.html)
        self.assertIn("__MOBILE_MQ__", km._LANDING_MOBILE_JS, "the template keeps the placeholder")
        src = open(os.path.join(BIN, "romp-kernel")).read()
        self.assertIn('_LANDING_MOBILE_JS.replace("__MOBILE_MQ__", json.dumps(_MOBILE_MQ))', src)
        self.assertEqual(src.count('"@media " + _MOBILE_MQ + "{"'), 1)
        self.assertNotIn('"@media (max-width:820px),(pointer:coarse) and (max-width:1024px){"', src, "the old literal is gone")

    def test_a_tab_switch_and_a_layout_flip_retell_the_panes(self):
        show = self.mob[self.mob.index("function show(p){"):self.mob.index("window.__rompMobileTab=show;")]
        show = "\n".join(l for l in show.splitlines() if not l.lstrip().startswith("//"))
        self.assertIn("try{localStorage.setItem(KT,p);}catch(e){}\n", show)
        self.assertTrue(show.rstrip().endswith("try{window.__rompPanesTell&&window.__rompPanesTell();}catch(e){}}"),
                        "show() ends by re-telling the panes:\n" + show)
        self.assertIn("window.__rompPanesTell=broadcast;", self.js)
        self.assertIn("var retell=function(){try{window.__rompPanesTell&&window.__rompPanesTell();}catch(e){}};\n"
                      "if(MQ){if(MQ.addEventListener)MQ.addEventListener('change',retell);else if(MQ.addListener)MQ.addListener(retell);}", self.mob)
        # the mobile script parses BEFORE the collapse script (its boot show() finds no teller yet — the boot
        # apply that follows tells the panes), and the relay's tab switch happens at message time, after both
        self.assertLess(self.html.index("window.__rompMobileTab=show;"), self.html.index("window.__rompPanesTell=broadcast;"))

    def test_the_relay_switches_the_mobile_tab_only_in_the_mobile_layout_and_remembers_the_tab(self):
        js = km._LANDING_SETTINGS_JS
        head = "if(m.romp==='viewFile'&&m.pane==='pane'){var ff=document.getElementById('f-files');"
        branch = js.split(head)[1].split("else if(m.romp==='viewFile')")[0]
        code = "\n".join(l for l in branch.splitlines() if not l.lstrip().startswith("//"))
        self.assertIn("try{if(window.__rompMobileOn&&window.__rompMobileOn()){var cur=document.body.getAttribute('data-tab')||'chat';\n"
                      "    if(cur!=='files'){window.__rompFilesTabFrom=cur;window.__rompMobileTab&&window.__rompMobileTab('files');}}}catch(e){}", code)
        self.assertNotIn("try{window.__rompMobileTab&&window.__rompMobileTab('files');}catch(e){}", js,
                         "no unconditional tab switch left: on desktop it only persisted a stale romp-mobile-tab")
        self.assertEqual(code.count("__rompMobileTab('files')"), 1)
        self.assertIn("window.__rompPaneToggle&&window.__rompPaneToggle('files',true)", code, "the desktop bring-forward is unchanged")

    def test_the_files_viewers_close_restores_the_remembered_tab_mobile_only(self):
        js = km._LANDING_SETTINGS_JS
        handler = ("if(m.romp==='filesViewerClosed'){var back=window.__rompFilesTabFrom;window.__rompFilesTabFrom=null;\n"
                   "  if(back&&window.__rompMobileOn&&window.__rompMobileOn()){try{window.__rompMobileTab&&window.__rompMobileTab(back);}catch(e){}}}")
        self.assertIn(handler, js)
        # placement: NOT between the pane branch and its `else if` (that would re-attach the feed route's
        # else-if to this block and run the feed route for pane clicks too), and before the feed's ack
        self.assertLess(js.index("else if(m.romp==='viewFile'){var vf="), js.index(handler))
        self.assertLess(js.index(handler), js.index("if(m.romp==='viewFileOpened')"))
        # the sender: files.ts posts the close EDGE up (pinned executed in ui/webview/files.test.ts)
        files = open(os.path.join(os.path.dirname(HERE), "ui", "webview", "files.ts")).read()
        self.assertIn('if (viewerUp && !up && window.parent !== window) window.parent.postMessage({ romp: "filesViewerClosed" }, "*");', files)


class Copy(unittest.TestCase):
    """The setting's help text says the rule: an open Files pane takes file links; the setting decides
    where they go while it is closed."""

    def test_gear_and_guide_say_the_open_pane_wins(self):
        ui = os.path.join(os.path.dirname(HERE), "ui", "webview")
        gear = open(os.path.join(ui, "gear.js")).read()
        # "both": a file and a folder, since the folder click joined the ladder (2026-09-07)
        self.assertIn("While the Files pane is open, both open there. When it is closed, a file opens", gear)
        guide = open(os.path.join(os.path.dirname(HERE), "docs", "guide.md")).read()
        self.assertIn("While the pane is open, a file\nlink clicked in the chat opens here. When it is closed, the gear's **File\nlinks open in** setting decides where a link opens", guide)
        settings = open(os.path.join(ui, "settings.ts")).read()
        self.assertIn("while the Files pane is CLOSED", settings)


if __name__ == "__main__":
    unittest.main()
