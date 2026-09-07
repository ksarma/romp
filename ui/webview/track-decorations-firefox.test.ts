// The touch policy (departure 6 in track-decorations.ts) on a second engine. PointerTracker relies on an event
// order: the pointerdown that names the touch reaches the editor root BEFORE the compatibility mousedown a tap
// produces, so both mousedown paths can ask which pointer pressed. The Chromium leg (track-decorations.test.ts)
// shows the outcome in Blink; this leg runs the same tap-then-click sequence in Firefox, whose compat-event
// synthesis is Gecko's own, and pins the order itself from listeners on the page, not only the outcome. A phone
// browser is not Blink in every case, and the order is the whole mechanism. WebKit is not exercised: its playwright
// build needs system libraries this box lacks (iOS Safari has fired pointer events since 13). Skips LOUDLY without
// playwright or the browser (CI installs none), as the other browser legs do.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

/** The editor chunk bundled with the shipped webview options (esbuild.js exports them without building). */
function chunkJs(): string {
  const { webview } = requireCjs(path.join(EXT, "esbuild.js")) as { webview: Record<string, unknown> };
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({ ...webview, entryPoints: [path.join(UI, "editor-chunk.ts")], write: false, sourcemap: false, logLevel: "silent" });
  const js = r.outputFiles.find((f: { path: string }) => f.path.endsWith(".js"));
  assert.ok(js, "the chunk bundle");
  return js.text;
}

// a synthetic tracked file: the notes-api world's `web` session inserted "big " and removed " a lot"
const DOC = "The big cat sat.";
const RECORDS = [
  { id: "a1", author: "web", ts: 1, kind: "ins", from: 4, newText: "big ", oldText: "" },
  { id: "d1", author: "web", ts: 1, kind: "del", from: 15, newText: "", oldText: " a lot" },
];
// the page logs the press events in the order the document sees them (capture phase, so the editor's own
// handlers cannot hide one), with the pointer type where the event carries one
const PAGE_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8>
<style>body{margin:0;font:16px/1.5 sans-serif}#host{margin:40px 8px 8px}.cm-editor{border:1px solid #888}</style></head>
<body><div id=host></div><script src=/dist/editor-chunk.js></script>
<script>
window.__order = [];
for (const t of ['pointerdown', 'touchstart', 'touchend', 'mousedown', 'mouseup', 'click'])
  document.addEventListener(t, function (e) { window.__order.push(t + (e.pointerType ? ':' + e.pointerType : '')); }, true);
window.__mount = function (text, records) {
  var host = document.getElementById('host'); host.replaceChildren();
  window.__decisions = null;
  window.__h = window.__rompEditor.mount(host, { text: text, ext: 'md', onChange: function () {}, onSave: function () {},
    track: { suggestions: records, onDecisions: function (l) { window.__decisions = l; } } });
};
window.__state = function () {
  return { ids: window.__h.track.suggestions().map(function (s) { return s.id; }), decisions: window.__decisions, order: window.__order.splice(0) };
};
</script></body></html>`;

type State = { ids: string[]; decisions: any; order: string[] };

test("in Firefox with touch: the pointerdown names the touch before the compat mousedown; a tap on a mark or a struck widget decides nothing; a mouse click accepts", async (t) => {
  if (!pw) { t.skip("playwright is not installed under vscode-extension — the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.firefox.launch(); }
  catch (e) { t.skip("no playwright firefox on this box — this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  try {
    // hasTouch only: playwright's Firefox has no isMobile emulation, and the policy is per pointer, not per device class
    const context = await browser.newContext({ hasTouch: true, viewport: { width: 390, height: 844 } });
    const page = await context.newPage();
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    const js = chunkJs();
    await page.route("http://romp.test/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE_HTML });
      if (u.pathname === "/dist/editor-chunk.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.evaluate(([d, r]: [string, unknown[]]) => (window as any).__mount(d, r), [DOC, RECORDS] as [string, unknown[]]);
    const state = () => page.evaluate(() => (window as any).__state()) as Promise<State>;
    const centre = async (sel: string) => {
      const b = await page.locator(sel).first().boundingBox();
      assert.ok(b, sel + " has a box");
      return { x: b.x + b.width / 2, y: b.y + b.height / 2 };
    };
    // a bounded wait on an event-driven outcome: the compat mouse events follow the tap in the page's next frames
    const settled = async (what: string) => {
      for (let i = 0; i < 60; i++) {
        const seen: string[] = await page.evaluate(() => (window as any).__order as string[]);
        if (seen.some((e) => e === "mouseup" || e === "click" || e.startsWith("click:"))) return;
        await page.waitForTimeout(50);
      }
      assert.fail(what + ": the press never completed");
    };
    const tapOrder = (order: string[], what: string) => {
      const pd = order.indexOf("pointerdown:touch");
      const md = order.indexOf("mousedown");
      assert.ok(pd >= 0, what + ": the touch's pointerdown reached the document — " + JSON.stringify(order));
      assert.ok(md >= 0, what + ": the tap produced a compat mousedown — " + JSON.stringify(order));
      assert.ok(pd < md, what + ": the pointerdown came first, so the tracker knew the pointer when the mousedown asked — " + JSON.stringify(order));
    };
    assert.deepEqual((await state()).ids, ["a1", "d1"]);

    const ins = await centre(".tc-diff-ins[data-hk-from='4']");
    await page.touchscreen.tap(ins.x, ins.y);
    await settled("tap on the mark");
    let s = await state();
    tapOrder(s.order, "tap on the mark");
    assert.deepEqual(s.ids, ["a1", "d1"], "the tap placed the caret; the insertion is still pending");
    assert.equal(s.decisions, null, "no decision was reported");

    const del = await centre(".tc-diff-del[data-hk-from='15']");
    await page.touchscreen.tap(del.x, del.y);
    await settled("tap on the struck widget");
    s = await state();
    tapOrder(s.order, "tap on the struck widget");
    assert.deepEqual(s.ids, ["a1", "d1"], "a tap on the struck widget (its own listener, outside CodeMirror's chain) decides nothing either");
    assert.equal(s.decisions, null);

    // the same page with a mouse: judged per pointer, so the click accepts
    await page.mouse.click(ins.x, ins.y);
    await settled("mouse click on the mark");
    s = await state();
    assert.ok(s.order.indexOf("pointerdown:mouse") >= 0 && s.order.indexOf("pointerdown:mouse") < s.order.indexOf("mousedown"), JSON.stringify(s.order));
    assert.deepEqual(s.ids, ["d1"], "a mouse click accepts");
    assert.deepEqual(s.decisions.accepted.map((e: { id: string }) => e.id), ["a1"]);
    assert.deepEqual(errors, []);
    await context.close();
  } finally { await browser.close(); }
});
