// The pane docking kit and the panes defined at the kernel (panedock-main.ts; plans/pane-docking.md, plans/panes-as-data.md). The
// shell builds those panes in the browser from its GET /panes read, one source for the pane records, so they join the row after
// the kit's bundle may have booted. Executed here:
//   - the boot: while the read is loading (window.__rompPaneRecords.state) the kit does not start, since a start then would
//     reconcile the stored layout without those panes and persist it, dropping their docked places; it starts on the builder's
//     romp-pane-records, which comes for a failed read too. A read already settled, or no read at all, starts it at once;
//   - the start: the kit hears romp-pane-records and wires each frame the event names (detail.frames), then reconciles, as it does
//     for a new chat column (romp-chat-cols).
// The engine boots on import in a browser top document and its start drives the whole layout, so both parts are LIFTED (esbuild's
// ts loader, the browse-route idiom): the boot block over a stand-in Engine, the start method's body over a stand-in engine and
// document. panedock-main.test.ts has the kit's pure exports.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { hideEdges } from "../test-dom-shim";   // the fake-DOM rule (ui/test-dom-shim.test.ts): a window stand-in's parent edge hides like a node's

const requireCjs = createRequire(__filename);
const ENGINE = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "panedock-main.ts"), "utf8");
const ts = (code: string): string => requireCjs("esbuild").transformSync(code, { loader: "ts" }).code;

type Records = { state: string };
/** The boot block lifted from panedock-main.ts and run in a top document whose read's state is `rr` (undefined: no read). */
function bootKit(rr: Records | undefined) {
  const a = ENGINE.indexOf('if (typeof window !== "undefined" && typeof document !== "undefined" && (!window.parent || window.parent === window)) {');
  assert.ok(a > 0, "panedock-main.ts: the boot block's anchor not found; re-anchor");
  let starts = 0;
  class Engine { apply(): void { starts++; } }   // the kit's start and its later reconciles all go through apply
  const win: any = new EventTarget();
  if (rr) win.__rompPaneRecords = rr;
  win.parent = win;   // a top document is its own parent
  hideEdges(win);
  const doc: any = new EventTarget();
  doc.body = {};
  new Function("window", "document", "Engine", "SETTINGS_KEY", ts(ENGINE.slice(a)))(win, doc, Engine, "romp:settings");
  return {
    starts: () => starts,
    fire: (type: string) => win.dispatchEvent(new Event(type)),
    land: () => win.dispatchEvent(new CustomEvent("romp-pane-records", { detail: { state: rr ? rr.state : "", rows: [], frames: [], error: "" } })),
  };
}

test("the kit does not start while the shell's GET /panes read is loading, and starts on the builder's romp-pane-records", () => {
  const rr: Records = { state: "loading" };
  const k = bootKit(rr);
  assert.equal(k.starts(), 0, "no start at boot while the read is loading: the defined panes are not in the row yet");
  k.fire("romp:settings");
  assert.equal(k.starts(), 0, "a gear save while the read is loading waits too");
  rr.state = "ok";
  k.land();
  assert.equal(k.starts(), 1, "the read's event starts the kit, with the defined panes in the row");
  k.fire("romp:settings");
  assert.equal(k.starts(), 2, "after it, a gear save applies as before");
  const failed: Records = { state: "loading" };
  const f = bootKit(failed);
  failed.state = "failed";
  f.land();
  assert.equal(f.starts(), 1, "a failed read's event starts the kit without them");
  assert.equal(bootKit({ state: "ok" }).starts(), 1, "a read already in at boot: the kit starts at once");
  assert.equal(bootKit(undefined).starts(), 1, "no read at all (a page without the shell's head read): the kit starts at once");
});

test("the started kit wires each frame the builder's romp-pane-records names, then reconciles", () => {
  const a = ENGINE.indexOf("  private start(): void {");
  const b = ENGINE.indexOf("\n  }\n", a);
  assert.ok(a > 0 && b > a, "panedock-main.ts: start()'s anchors not found; re-anchor");
  const start = new Function("window", "document", "localStorage", "MutationObserver", "parse", "seedLayout", "reconcileShown", "LAYOUT_KEY", "PANE_DOCKING_CLASS", "STYLE_ID", "SHELL_CSS", "paneSourceOk",
    ts("function start() {" + ENGINE.slice(ENGINE.indexOf("{", a) + 1, b) + "\n}") + "\nreturn start;");
  const win = new EventTarget();
  const col = new EventTarget(); const row = new EventTarget();
  const doc: any = new EventTarget();
  doc.querySelector = (sel: string) => (sel === ".col" ? col : sel === ".row" ? row : null);
  doc.body = { classList: { add: () => {} }, appendChild: () => {} };
  doc.head = { appendChild: () => {} };
  doc.createElement = () => ({ id: "", textContent: "" });
  const calls: string[] = [];
  const engine = {
    on: false, col: null, row: null, style: null, outline: null, ghost: null, lay: null, obs: null, offs: [] as Array<() => void>,
    shown: () => ["chat-pane"], persist: () => { calls.push("persist"); }, render: () => { calls.push("render"); }, reconcile: () => { calls.push("reconcile"); },
    wire: (f: { id: string }) => { calls.push("wire " + f.id); }, allFrames: () => [], standDownGrowWriters: () => {}, mobile: () => false, apply: () => {},
    onShellPress: () => {}, onKey: () => {}, setAlt: () => {}, onGrabMessage: () => {},
  };
  class Observer { observe(): void {} disconnect(): void {} }
  start(win, doc, { getItem: () => null }, Observer, () => null, (sh: string[]) => ({ tree: sh }), (l: unknown) => l, "romp:pane-layout", "pane-docking", "pd-css", "", () => true).call(engine);
  assert.equal(engine.on, true, "the stand-in document let the kit start");
  calls.length = 0;
  win.dispatchEvent(new CustomEvent("romp-pane-records", { detail: { state: "ok", rows: [], frames: [{ id: "f-notes" }, { id: "f-docs" }], error: "" } }));
  assert.deepEqual(calls, ["wire f-notes", "wire f-docs", "reconcile"], "each built frame is wired (its grab detector and marks), then the layout takes the new panes in");
  calls.length = 0;
  win.dispatchEvent(new CustomEvent("romp-pane-records", { detail: { state: "failed", rows: [], frames: [], error: "/panes answered HTTP 500" } }));
  assert.deepEqual(calls, ["reconcile"], "a failed read names no frame: nothing to wire");
});
