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
        self.assertIn("function panesMsg(){var on={};KEYS.forEach(function(k){on[k]=!!po[k];});return {romp:'panes',on:on};}", self.js)

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


class Copy(unittest.TestCase):
    """The setting's help text says the rule: an open Files pane takes file links; the setting decides
    where they go while it is closed."""

    def test_gear_and_guide_say_the_open_pane_wins(self):
        ui = os.path.join(os.path.dirname(HERE), "ui", "webview")
        gear = open(os.path.join(ui, "gear.js")).read()
        self.assertIn("While the Files pane is open, file links open there. When it is closed:", gear)
        guide = open(os.path.join(os.path.dirname(HERE), "docs", "guide.md")).read()
        self.assertIn("While the pane is open, a file\nlink clicked in the chat opens here. When it is closed, the gear's **File\nlinks open in** setting decides where a link opens", guide)
        settings = open(os.path.join(ui, "settings.ts")).read()
        self.assertIn("while the Files pane is CLOSED", settings)


if __name__ == "__main__":
    unittest.main()
