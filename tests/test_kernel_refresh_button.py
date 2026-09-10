"""The ↻ kernel-restart button is decoupled from Debug mode (the user 2026-06-24).

It used to be hidden unless Debug mode was on (an `applyDebug()` helper in the gear JS toggled its
`style.display` off `s.debug`). The user wanted it ALWAYS visible, so that gating is gone — Debug now
only governs the timeline's judging band. Source-level pin against the kernel's embedded gear chrome.
"""
import os
import unittest
from romp_load import load_source
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))


class RefreshButtonDecoupledTest(unittest.TestCase):
    def test_refresh_button_is_always_present(self):
        # the ↻ moved to the shell's far-left rail (the user 2026-06-25) so it persists regardless of which
        # panes are open — always present, still POSTs /restart then polls /healthz and reloads.
        html = km._landing()
        self.assertIn("id=rail-refresh", html)
        self.assertIn("fetch('/restart',{method:'POST'})", html)
        self.assertNotIn("id=rrefresh", _gear_src())   # gone from the feed gear
        # …and it draws a REAL browser-style reload icon (the user 2026-07-27: the ↻ TEXT glyph stopped
        # its arc short at 11 o'clock and never read as refresh, and its size rode the fallback font).
        # One shared svg — a near-full clockwise arc with the arrowhead at 1 o'clock — used by the rail
        # AND the mobile bar, sized 18px like its icon neighbors.
        self.assertIn("aria-label=Refresh>" + km._REFRESH_SVG, html)
        self.assertIn("A 5.2 5.2 0 1 1", km._REFRESH_SVG)   # the 270-degree arc (large-arc, clockwise)
        self.assertNotIn(">↻<", html)                        # the text glyph is gone from every surface

    def test_refresh_button_is_not_gated_on_debug(self):
        # the old applyDebug() helper (which hid #rrefresh unless s.debug) is gone entirely …
        self.assertNotIn("applyDebug", _gear_src())
        # … and nothing else hides the refresh button by toggling its display off the debug flag
        self.assertNotRegex(_gear_src(), r"rf\.style\.display\s*=")
        self.assertNotRegex(_gear_src(), r"rrefresh[^\n]*display:none")

    def test_judge_toggles_do_not_touch_the_refresh_button(self):
        # the judge-set toggles (which replaced the single Debug toggle) save the pref + emit, but never
        # re-run any refresh-button visibility logic — the ↻ is always visible
        self.assertIn("s.showIndexJudges = jix.checked", _gear_src())
        self.assertIn("s.showTriageJudges = jtr.checked", _gear_src())
        self.assertNotRegex(_gear_src(), r"checked;[^\n]*applyDebug")


class RestartReloadRaceTest(unittest.TestCase):
    """The restart flow reloads on the NEW kernel's answer, never a bare 200 (the user 2026-07-27).

    The old poll reloaded on the first /healthz 200 — but the OLD kernel keeps answering for a beat
    after the /restart ack (the manager SIGTERMs it asynchronously), so the reload routinely landed on
    a dying server and the browser sat on its connection-error page until a manual refresh. Now the
    page embeds the boot id it was served under, /healthz stamps every answer with X-Romp-Boot, and
    the poll reloads only when the id FLIPS — an exact process-identity event, not a timing guess.
    While it waits, the romp boot splash is rebuilt over the page (the loading rule), with a reload
    backstop so the splash can never trap the user."""

    def test_reload_waits_for_the_boot_id_to_flip(self):
        import json
        html = km._landing()
        # the page knows its own kernel's boot id, and the poll compares against it
        self.assertIn("b!==" + json.dumps(km._BOOT_ID), html)
        self.assertIn("r.headers.get('X-Romp-Boot')", html)
        # both splice placeholders were resolved
        self.assertNotIn("__ROMP_BOOT__", html)
        self.assertNotIn("__ROMP_LOADER__", html)
        # the racy first-200 reload is gone
        self.assertNotIn("if(r&&r.ok)location.reload()", html)

    def test_wait_wears_the_boot_splash(self):
        import json
        html = km._landing()
        # the splash element is rebuilt (the boot JS removed it from the DOM after startup) from the
        # SAME server-rendered loader markup the boot splash uses — one source, no drifting copy
        self.assertIn("boot.id='romp-boot'", html)
        self.assertIn("boot.innerHTML=" + json.dumps(km._loader_inner()), html)

    def test_healthz_and_restart_carry_the_boot_id(self):
        # source-level pins (the HTTP-level check lives in test_kernel.py's ServeSecurity): /healthz
        # stamps X-Romp-Boot, and the /restart ack reports which kernel acked
        import inspect
        src = inspect.getsource(km.Handler)
        self.assertIn('"X-Romp-Boot": _BOOT_ID', src)
        self.assertIn('"restarting": True, "boot": _BOOT_ID', src)


# window.__rompRestart run for real under node's vm module (the shape of tests/test_inline_js_parses.py: the
# RUNTIME value of the blob, not its source text), with a stub document, a stub fetch and a recording
# __rompNotify. `scenario` is what the kernel answers POST /restart: refused (502, the manager's refusal in the
# body) or taken (200). The probe reports after 1.2 s, past the poll's first 500 ms tick.
_RESTART_PROBE_JS = r"""
const vm = require('node:vm');
const blob = require('node:fs').readFileSync(process.argv[2], 'utf8');
const scenario = process.argv[3];
const log = { healthz: 0, notices: [], reloads: 0, restarts: 0 };
function el(id) {
  const cls = new Set();
  return { id, tag: '', style: {}, innerHTML: '', children: [], onclick: null, _cls: cls,
    classList: { add: (c) => cls.add(c), remove: (c) => cls.delete(c), contains: (c) => cls.has(c),
                 toggle: (c, on) => (on ? cls.add(c) : cls.delete(c)) },
    appendChild(x) { this.children.push(x); }, remove() {}, addEventListener() {},
    getAttribute() { return null; }, setAttribute() {} };
}
const rail = el('rail-refresh');
const byId = { 'rail-refresh': rail };
const body = el('body');
body.appendChild = function (x) { this.children.push(x); if (x.id) byId[x.id] = x; };
const document = { body, getElementById: (id) => byId[id] || null,
  createElement: (tag) => { const e = el(''); e.tag = tag; return e; }, addEventListener() {} };
const restartAnswer = scenario === 'refused'
  ? { ok: false, status: 502, json: () => Promise.resolve({ ok: false, restarting: false, error: 'The restart did not happen: the manager refused (HTTP 401): it does not hold the serve token this kernel sent. Run romp refresh from a shell whose state root (ROMP_STATE_DIR or XDG_STATE_HOME) is the manager\'s.' }) }
  : { ok: true, status: 200, json: () => Promise.resolve({ ok: true, restarting: true }) };
const sandbox = { console, setTimeout, clearTimeout, JSON, Math, Date, String, Number, Array, Object, Error, Promise,
  document, addEventListener() {},
  localStorage: { getItem: () => null, setItem() {} }, sessionStorage: { getItem: () => null, setItem() {} },
  location: { reload() { log.reloads++; } },
  __ROMP_LOADER__: '<i>loader</i>', __ROMP_BOOT__: 'boot-old',
  __rompNotify: (kind, text) => log.notices.push({ kind, text }),
  fetch(url) {
    if (url === '/fleet-restart') return Promise.resolve({ ok: true, json: () => Promise.resolve({ rows: [] }) });
    if (url === '/healthz') { log.healthz++; return Promise.resolve({ ok: true, headers: { get: () => 'boot-old' } }); }
    if (url === '/restart') { log.restarts++; return Promise.resolve(restartAnswer); }
    return Promise.reject(new Error('unexpected fetch ' + url));
  } };
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(blob, sandbox);
rail.onclick();                       // the rail button's click: dims itself, then window.__rompRestart()
setTimeout(() => {
  const boot = byId['romp-boot'];
  console.log(JSON.stringify({ healthz: log.healthz, notices: log.notices, reloads: log.reloads, restarts: log.restarts,
    bootGone: boot ? boot._cls.has('gone') : null, railPointer: rail.style.pointerEvents, railOpacity: rail.style.opacity }));
  process.exit(0);
}, 1200);
"""


class RestartRefusalProbeTest(unittest.TestCase):
    """The web shell's Restart discarded the kernel's answer (review round 2, 2026-09-10): a 502 (the manager
    refused the restart) left the boot splash up for the two-minute backstop and then reloaded onto the same
    kernel, hiding the dashboard and the bell the whole time. Now a not-ok answer skips the /healthz poll,
    drops the splash and restores the rail button; a 2xx polls as before. The page files NO notice of its
    own (review round 3, 2026-09-10): the kernel's /restart handler filed the refusal under the refused kind
    before it answered, and the feed pane mirrors that into the same bell, so a page-side copy of the text
    made one refused click read as two rows."""

    def _probe(self, scenario):
        import json
        import shutil
        import subprocess
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed on this machine")
        with tempfile.TemporaryDirectory() as tmp:
            blob = os.path.join(tmp, "landing-settings.js")
            probe = os.path.join(tmp, "probe.js")
            with open(blob, "w") as f:
                f.write(km._LANDING_SETTINGS_JS)
            with open(probe, "w") as f:
                f.write(_RESTART_PROBE_JS)
            r = subprocess.run([node, probe, blob, scenario], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[:2000])
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_a_refused_restart_polls_nothing_drops_the_splash_restores_the_button_and_files_no_notice_of_its_own(self):
        got = self._probe("refused")
        self.assertEqual(got["restarts"], 1)
        self.assertEqual(got["healthz"], 0, "nothing is restarting: no poll for a new boot id")
        self.assertEqual(got["reloads"], 0)
        self.assertIs(got["bootGone"], True, "the splash comes down")
        self.assertEqual((got["railPointer"], got["railOpacity"]), ("", ""), "the rail button is back")
        self.assertEqual(got["notices"], [], "the kernel's own notice is the one row in the bell, through the feed mirror")
        self.assertNotIn("__rompNotify('refused'", km._LANDING_SETTINGS_JS, "no page-side copy of the kernel's text")

    def test_a_taken_restart_polls_for_the_new_boot_id_under_the_splash_as_before(self):
        got = self._probe("taken")
        self.assertEqual(got["restarts"], 1)
        self.assertGreaterEqual(got["healthz"], 1, "the poll runs")
        self.assertEqual(got["reloads"], 0, "the same boot id: no reload yet")
        self.assertIs(got["bootGone"], False, "the splash stays up while the restart lands")
        self.assertEqual((got["railPointer"], got["railOpacity"]), ("none", "0.5"), "the button stays dimmed")
        self.assertEqual(got["notices"], [])


if __name__ == "__main__":
    unittest.main()


# The gear moved from kernel-inline strings into the shared feed bundle
# (2026-07-13): ui/webview/gear.js is the single source both hosts render, so
# the gear pins read THAT file (and feed.css for its styling).
def _gear_src():
    import pathlib
    return (pathlib.Path(__file__).resolve().parent.parent / "ui" / "webview" / "gear.js").read_text()


def _gear_css_src():
    import pathlib
    return (pathlib.Path(__file__).resolve().parent.parent / "ui" / "webview" / "gear.css").read_text()
