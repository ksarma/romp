// The pane docking kit and the panes defined at the kernel (panedock-main.ts; plans/pane-docking.md, plans/panes-as-data.md). The
// shell builds those panes in the browser from its GET /panes read, one source for the pane records, so they join the row after
// the kit's bundle may have booted. Executed here:
//   - the boot: while the read is loading (window.__rompPaneRecords.state) the kit does not start, since a start then would
//     reconcile the stored layout without those panes and persist it, dropping their docked places; it starts on the builder's
//     romp-pane-records, which comes for a failed read too. A read already settled, or no read at all, starts it at once;
//   - the start: the kit hears romp-pane-records and wires each frame the event names (detail.frames), then reconciles, as it does
//     for a new chat column (romp-chat-cols).
//   - the stored layout is never written while the read is not in, nor after a start made without it: persist(), the
//     one write, refuses, so each of its roads (the start, the reconcile, a pane's drop, a tab's drop, a divider's
//     commit) on a failed-read page leaves the stored layout, and the defined panes' places in it, as it was; the same
//     roads on a page whose read is in write. A read that comes in after a start without it starts the kit again from
//     the stored layout.
// The engine boots on import in a browser top document and its start drives the whole layout, so both parts are LIFTED (esbuild's
// ts loader, the browse-route idiom): the boot block over a stand-in Engine, the start method's body over a stand-in engine and
// document. The stored-layout roads run the REAL Engine class (the module bundled with an export of it, over a stand-in
// window, document and store; only the methods that read or paint the page's geometry are stand-ins: what the shell
// shows, the render, the frames). panedock-main.test.ts has the kit's pure exports.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { hideEdges } from "../test-dom-shim";   // the fake-DOM rule (ui/test-dom-shim.test.ts): a window stand-in's parent edge hides like a node's
import { move, parse, serialise, leaves, type Layout } from "./pane-tree";
import { seedLayout } from "./pane-dock";

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
    "recordsUnread",   // the start notes whether the read is in (the stored-layout tests below run it for real)
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
  start(win, doc, { getItem: () => null }, Observer, () => null, (sh: string[]) => ({ tree: sh }), (l: unknown) => l,
    "romp:pane-layout", "pane-docking", "pd-css", "", () => true, () => false).call(engine);
  assert.equal(engine.on, true, "the stand-in document let the kit start");
  calls.length = 0;
  win.dispatchEvent(new CustomEvent("romp-pane-records", { detail: { state: "ok", rows: [], frames: [{ id: "f-notes" }, { id: "f-docs" }], error: "" } }));
  assert.deepEqual(calls, ["wire f-notes", "wire f-docs", "reconcile"], "each built frame is wired (its grab detector and marks), then the layout takes the new panes in");
  calls.length = 0;
  win.dispatchEvent(new CustomEvent("romp-pane-records", { detail: { state: "failed", rows: [], frames: [], error: "/panes answered HTTP 500" } }));
  assert.deepEqual(calls, ["reconcile"], "a failed read names no frame: nothing to wire");
});

// ---- the stored layout on a page whose read is not in ----
/** The real Engine class: panedock-main.ts bundled with an export of it, evaluated with no window (its boot stays
 *  inert). */
function realEngine(): any {
  const dir = path.resolve(process.cwd(), "..", "ui", "webview");
  const out = requireCjs("esbuild").buildSync({
    stdin: { contents: ENGINE + "\nexport { Engine };\n", resolveDir: dir, sourcefile: "panedock-main.ts",
      loader: "ts" },
    bundle: true, format: "cjs", platform: "node", write: false, logLevel: "silent",
  });
  const mod: { exports: any } = { exports: {} };
  new Function("module", "exports", "require", out.outputFiles[0].text)(mod, mod.exports, requireCjs);
  return mod.exports.Engine;
}
const ROW = { band: false, bandPx: 0, grow: {} as Record<string, number> };
const ALL4 = ["chat-pane", "feed-pane", "notes-pane", "docs-pane"];
// the stored layout a page whose read was in saved: the defined pane notes docked LEFT of the chat (its default place
// is the row's right end, so a layout rebuilt without it and opened again puts it elsewhere), docs at the end
const STORED = serialise({ v: 1, parked: [],
  tree: move(seedLayout({ ...ROW, row: ALL4 }).tree, "notes-pane", "chat-pane", "left") });
const FULL = { ...ROW, row: ALL4, present: ALL4 };
// the panes the page has when the read did not come in: the shipped ones, the defined panes not built
const SHIPPED = { ...ROW, row: ["chat-pane", "feed-pane"], present: ["chat-pane", "feed-pane"] };

/** A started engine over a stand-in page: `state` the read's (undefined: no read), the store holding STORED. */
function page(Engine: any, state: string | undefined, shown: unknown) {
  const store: Record<string, string> = { "romp-layout": STORED };
  const win: any = new EventTarget(); win.parent = win; hideEdges(win);
  if (state) win.__rompPaneRecords = { state };
  const el = () => ({ id: "", textContent: "", style: {} as Record<string, string>, remove: () => {},
    classList: { add: () => {}, remove: () => {}, toggle: () => {} } });
  const col: any = new EventTarget(); col.style = { getPropertyValue: () => "", setProperty: () => {} };
  const doc: any = new EventTarget();
  doc.querySelector = (sel: string) => (sel === ".col" ? col : sel === ".row" ? new EventTarget() : null);
  doc.querySelectorAll = () => [];
  doc.body = { classList: { add: () => {}, remove: () => {}, toggle: () => {}, contains: () => false },
    appendChild: () => {} };
  doc.head = { appendChild: () => {} };
  doc.createElement = el;
  doc.getElementById = () => null;
  const g = globalThis as any;
  const keep = ["window", "document", "localStorage", "MutationObserver"].map((k) => [k, k in g, g[k]] as const);
  g.window = win; g.document = doc;
  g.localStorage = { getItem: (k: string) => (k in store ? store[k] : null),
    setItem: (k: string, v: string) => { store[k] = String(v); }, removeItem: (k: string) => { delete store[k]; } };
  g.MutationObserver = class { observe(): void {} disconnect(): void {} };
  const e = new Engine();
  let now = shown;
  e.shown = () => now; e.render = () => {}; e.allFrames = () => []; e.allPaneEls = () => [];
  e.wire = () => {}; e.unwire = () => {};
  e.start();
  return {
    e, win, store, stored: () => store["romp-layout"],
    show: (sh: unknown) => { now = sh; },
    done: () => { for (const [k, had, v] of keep) { if (had) g[k] = v; else delete g[k]; } },
  };
}
const rowOf = (s: string): string[] => leaves((parse(s) as Layout).tree);

/** Each road that saves, run on a started page: what it changes in memory, as the browser would after the gesture. */
const ROADS: Array<[string, (p: ReturnType<typeof page>) => void]> = [
  ["the reconcile (a pane toggled off on the rail)", (p) => {
    p.show({ ...p.e.shown(), row: ["chat-pane"] }); p.e.reconcile();
  }],
  ["a pane's drop", (p) => { p.e.drop("feed-pane", "chat-pane", "left"); }],
  ["a tab's drop (its lone column moved to an edge)", (p) => {
    p.win.__rompChatSets = () => ({ "2": ["s1"] });
    const sh: any = p.e.shown();
    p.show({ ...sh, row: sh.row.concat(["chat-pane-2"]), present: (sh.present || []).concat(["chat-pane-2"]) });
    p.e.dropTab({ sid: "s1", name: "web" }, { target: "chat-pane", edge: "left" });
  }],
  ["a divider's commit", (p) => {
    const edge = { dir: "row", path: [], i: 0, avail: 1000, fixed: false, rect: { x: 0, y: 0, w: 4, h: 800 } };
    p.e.div = { edge, live: false, x0: 0, y0: 0, last: 60 };
    p.e.endDiv(true);
  }],
];

test("on a failed-read page the stored layout is never written: the start and each road that saves leave it", () => {
  const Engine = realEngine();
  const ok = page(Engine, "ok", FULL);
  try {
    assert.equal(rowOf(ok.stored())[0], "notes-pane", "the contrast: a start whose read is in keeps the stored places");
  } finally { ok.done(); }
  for (const state of ["failed", "loading"]) {
    const p = page(Engine, state, SHIPPED);
    try {
      assert.equal(p.stored(), STORED, state + ": the start leaves the stored layout, the defined panes' places in it");
      assert.deepEqual(rowOf(serialise(p.e.lay)), ["chat-pane", "feed-pane"],
        state + ": in memory, the panes the page has");
    } finally { p.done(); }
  }
  for (const [name, road] of ROADS) {
    const p = page(Engine, "failed", SHIPPED);
    try {
      const before = serialise(p.e.lay);
      road(p);
      assert.notEqual(serialise(p.e.lay), before, name + ": the road changed the layout in memory");
      assert.equal(p.stored(), STORED, name + " on a failed-read page: the stored layout is as it was");
    } finally { p.done(); }
    const q = page(Engine, "ok", FULL);
    try {
      const at = q.stored();
      road(q);
      assert.notEqual(q.stored(), at, name + " on a page whose read is in: the road writes the stored layout");
    } finally { q.done(); }
  }
});

test("a read that comes in after the kit started without it starts the kit again from the stored layout", () => {
  const Engine = realEngine();
  const p = page(Engine, "failed", SHIPPED);   // the backstop's failure; the answer is still on its way
  try {
    p.e.drop("feed-pane", "chat-pane", "left");   // a move made meanwhile is not stored
    p.win.__rompPaneRecords.state = "ok";
    p.show(FULL);
    p.win.dispatchEvent(new CustomEvent("romp-pane-records",
      { detail: { state: "ok", rows: [], frames: [], error: "" } }));
    assert.equal(rowOf(serialise(p.e.lay))[0], "notes-pane",
      "the defined pane is back in its stored place, left of the chat");
    assert.deepEqual(rowOf(p.stored()), rowOf(STORED), "the stored layout is the one the earlier page saved");
  } finally { p.done(); }
  const q = page(Engine, "failed", SHIPPED);
  try {
    q.win.__rompPaneRecords.state = "ok";
    q.show(FULL);
    q.e.drop("feed-pane", "chat-pane", "left");   // a road that saves, before the kit heard of the read
    assert.equal(q.stored(), STORED, "until the kit starts again, a layout made without the read is not stored");
    q.e.reconcile();   // the boot block's road: its apply hears the event first and reconciles
    assert.equal(rowOf(q.stored())[0], "notes-pane",
      "a reconcile after the read came in restarts the kit the same way");
  } finally { q.done(); }
});
