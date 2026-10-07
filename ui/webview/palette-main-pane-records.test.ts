// The palette's toggle commands for the panes defined at the kernel (palette-main.ts registerPane and recordPanes;
// plans/panes-as-data.md). The shell builds those panes in the browser from its GET /panes read, one source for the pane
// records, and the read can settle before or after the palette's bundle boots. So the palette registers a pane's command from the
// read's state object when the read is in at boot (window.__rompPaneRecords) and from the builder's romp-pane-records event when
// it lands later; registerCommand replaces by id, so the two paths leave one command per pane. The shipped generic panes keep
// their boot read of the body attribute. Both roads run at the end of the boot, so the panes defined at the kernel list
// after every command the boot registers, wherever the read lands; and recordPanes clears the dispatcher's cached chord
// map, so a key bound to such a pane's command works from the read's landing on, whatever was pressed before it.
// palette-main.ts boots the shell's whole palette on import, so its boot function is LIFTED whole (esbuild's ts loader,
// the browse-route idiom) and run with the real command registry, keybindings, settings and tab-keys modules over a
// stand-in window, document and store; the palette's and the shortcuts dialog's DOM are stand-ins too.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import * as C from "./commands";
import * as K from "./keybindings";
import * as S from "./settings";
import * as TK from "./tab-keys";
import { hostPrefix } from "./host-prefix";
import { paneSourceOk } from "./pane-source";
import { hideEdges } from "../test-dom-shim";   // the fake-DOM rule (ui/test-dom-shim.test.ts): its parent edge hides

const requireCjs = createRequire(__filename);
const MAIN = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "palette-main.ts"), "utf8");
const ts = (code: string): string => requireCjs("esbuild").transformSync(code, { loader: "ts" }).code;
// the shell's body attribute: the shipped Artifacts record's row alone (tests/test_pane_registry.py ARTIFACTS_ROW)
const ARTIFACTS_ROW = { id: "artifacts", title: "Artifacts", protocol: "romp", experimental: true, on: false, builtin: true };
// rows as the shell's builder keeps them in the read's state (rows)
const NOTES = { id: "notes", title: "Notebook", on: true, experimental: false, protocol: "romp", src: "/pane/notes/" };
const LAB = { id: "lab", title: "Lab", on: false, experimental: true, protocol: "none", src: "/feed" };

type Records = { state: string; rows: unknown; error: string };
/** The palette's boot lifted whole from palette-main.ts and run once, as the bundle runs it, with `rr` as the read's
 *  state and `store` as localStorage (romp:settings for the gear's panes, romp:keys for the bindings). */
function boot(rr: Records, store: Record<string, string> = {}) {
  for (const c of C.commandList()) C.unregisterCommand(c.id);   // the registry is this file's process-wide one
  const a = MAIN.indexOf("(function boot() {");
  const b = MAIN.indexOf("\n})();", a);
  assert.ok(a > 0 && b > a, "palette-main.ts: the boot function's anchors not found; re-anchor");
  const win: any = new EventTarget();
  win.parent = win;   // the top document is its own parent
  win.__rompPaneRecords = rr;
  const toggled: string[] = [];
  win.__rompPaneToggle = (id: string) => { toggled.push(id); };
  hideEdges(win);
  const doc: any = new EventTarget();
  doc.body = { getAttribute: (k: string) => (k === "data-panes" ? JSON.stringify([ARTIFACTS_ROW]) : null),
    classList: { contains: () => false } };
  doc.getElementById = () => null;
  doc.querySelectorAll = () => [];
  const ls = { getItem: (k: string) => (k in store ? store[k] : null),
    setItem: (k: string, v: string) => { store[k] = String(v); }, removeItem: (k: string) => { delete store[k]; } };
  const palette = { toggle: () => {}, close: () => {}, openPick: () => {} };
  const keys = { open: () => {}, close: () => false, isOpen: () => false, feed: () => {}, onClose: () => {},
    openFor: () => {} };
  const g = globalThis as any;
  const had = { window: "window" in g, localStorage: "localStorage" in g };
  const prev = { window: g.window, localStorage: g.localStorage };
  g.window = win; g.localStorage = ls;   // the modules read the page's window and store at call time
  const restore = () => {
    if (had.window) g.window = prev.window; else delete g.window;
    if (had.localStorage) g.localStorage = prev.localStorage; else delete g.localStorage;
  };
  const deps: Record<string, unknown> = {
    window: win, document: doc, navigator: { platform: "Linux" }, localStorage: ls,
    registerCommand: C.registerCommand, unregisterCommand: C.unregisterCommand, runCommand: C.runCommand,
    commandList: C.commandList, initPalette: () => palette, initShortcutsModal: () => keys,
    chordMap: K.chordMap, chordOf: K.chordOf, dispatchable: K.dispatchable, displayChord: K.displayChord,
    effectiveChord: K.effectiveChord, keyHint: K.keyHint, loadOverrides: K.loadOverrides, saveOverride: K.saveOverride,
    titleWithKey: K.titleWithKey, KEYS_EVENT: K.KEYS_EVENT, hostPrefix, loadSettings: S.loadSettings,
    OPTIONAL_PANES: S.OPTIONAL_PANES, hotkeyCommandId: TK.hotkeyCommandId, loadTabKeys: TK.loadTabKeys,
    rememberTabKey: TK.rememberTabKey, forgetTabKey: TK.forgetTabKey, tabChord: TK.tabChord,
    unboundTabKeys: TK.unboundTabKeys, TABKEYS_KEY: TK.TABKEYS_KEY, paneSourceOk,
  };
  try { new Function(...Object.keys(deps), ts(MAIN.slice(a, b) + "\n})();"))(...Object.values(deps)); }
  catch (e) { restore(); throw e; }
  const bootIds = C.commandList().map((c) => c.id);
  return {
    toggled, bootIds, restore,
    ids: () => C.commandList().map((c) => c.id),
    panes: () => C.commandList().filter((c) => c.id.startsWith("pane.")),
    land: (r: Records) => win.dispatchEvent(new CustomEvent("romp-pane-records",
      { detail: { state: r.state, rows: r.rows || [], frames: [], error: r.error } })),
    // a keydown on the shell document, as the dispatcher hears it (its capture listener on the document)
    key: (k: string, mods: { alt?: boolean } = {}) => doc.dispatchEvent(Object.assign(new Event("keydown"),
      { key: k, altKey: !!mods.alt, ctrlKey: false, shiftKey: false, metaKey: false, repeat: false })),
  };
}

test("a read in when the palette boots: each pane it lists gets a toggle command under its title and setting", () => {
  const p = boot({ state: "ok", rows: [NOTES, LAB, { id: 7, title: "x" }, null], error: "" },
    { "romp:settings": JSON.stringify({ panes: { notes: false } }) });
  try {
    const named = ["pane.artifacts", "pane.notes", "pane.lab"];
    assert.deepEqual(p.panes().map((c) => [c.id, c.title]).filter(([id]) => named.includes(id)),
      [["pane.artifacts", "Show or hide the Artifacts pane"], ["pane.notes", "Show or hide the Notebook pane"],
        ["pane.lab", "Show or hide the Lab pane"]],
      "the attribute's pane, then the read's in its order");
    assert.ok(!p.ids().includes("pane.7"), "a row without a string id gets no command");
    const cmd = (id: string) => p.panes().find((c) => c.id === id)!;
    cmd("pane.notes").run();
    assert.deepEqual(p.toggled, ["notes"], "the command toggles the pane by its id, through the shell's controller");
    assert.equal(cmd("pane.notes").when!(), false, "a pane hidden in the gear is not listed");
    assert.equal(cmd("pane.lab").when!(), false, "an experimental pane is not listed until the gear asks for it");
  } finally { p.restore(); }
});

// A pane id can be an Object member's name (constructor): the stored set compares its own keys, so that pane's gear
// choice is read as any other's
test("a pane whose id is an Object member's name is listed by its stored choice", () => {
  const CTOR = { id: "constructor", title: "Ctor", on: true, experimental: false, protocol: "romp", src: "/feed" };
  const hidden = boot({ state: "ok", rows: [CTOR], error: "" },
    { "romp:settings": JSON.stringify({ panes: { constructor: false } }) });
  try {
    const cmd = hidden.panes().find((c) => c.id === "pane.constructor");
    assert.ok(cmd, "the pane gets its command");
    assert.equal(cmd!.when!(), false, "a constructor pane hidden in the gear is not listed");
  } finally { hidden.restore(); }
  const shown = boot({ state: "ok", rows: [CTOR], error: "" });
  try {
    assert.equal(shown.panes().find((c) => c.id === "pane.constructor")!.when!(), true,
      "with no stored choice the pane's own default lists it");
  } finally { shown.restore(); }
});

test("a read that lands after the palette booted: its event registers the panes then, one command per pane", () => {
  const p = boot({ state: "loading", rows: null, error: "" });
  try {
    const defined = () => p.ids().filter((id) => id === "pane.notes" || id === "pane.lab");
    assert.deepEqual(defined(), [], "while the read is loading: none of the defined panes");
    p.land({ state: "failed", rows: null, error: "/panes answered HTTP 500" });
    p.land({ state: "failed", rows: [LAB], error: "no answer within 30 s" });
    assert.deepEqual(defined(), [], "a failed read adds nothing, whatever rows its event carries");
    p.land({ state: "ok", rows: [NOTES], error: "" });
    assert.deepEqual(defined(), ["pane.notes"], "the read's pane is in once its event arrives");
    p.land({ state: "ok", rows: [NOTES, LAB], error: "" });
    assert.deepEqual(defined(), ["pane.notes", "pane.lab"], "a later event adds the new pane and repeats none");
  } finally { p.restore(); }
  const seen = boot({ state: "ok", rows: [NOTES], error: "" });
  try {
    seen.land({ state: "ok", rows: [NOTES], error: "" });
    assert.equal(seen.ids().filter((id) => id === "pane.notes").length, 1,
      "a read seen at boot and its event after it: one command");
  } finally { seen.restore(); }
});

test("the defined panes' commands list after every command the boot registers, read in at boot or later", () => {
  const atBoot = boot({ state: "ok", rows: [NOTES, LAB], error: "" });
  let early: string[] = [], late: string[] = [], shipped: string[] = [];
  try { early = atBoot.ids(); } finally { atBoot.restore(); }
  const later = boot({ state: "loading", rows: null, error: "" });
  try {
    shipped = later.bootIds;
    later.land({ state: "ok", rows: [NOTES, LAB], error: "" });
    late = later.ids();
  } finally { later.restore(); }
  assert.ok(shipped.length > 10 && shipped.includes("keys.open") && shipped.includes("pane.chat"),
    "the boot registered its commands: " + shipped.length);
  assert.deepEqual(late, shipped.concat(["pane.notes", "pane.lab"]), "landing later: after every command of the boot");
  assert.deepEqual(early, late, "a read in at boot lists them in the same place as one that lands later");
});

test("a key bound to a defined pane's command works once the read lands, though a key was pressed before it", () => {
  const rr: Records = { state: "loading", rows: null, error: "" };
  const p = boot(rr, { "romp:keys": JSON.stringify({ "pane.notes": "Alt+N" }) });
  try {
    p.key("j", { alt: true });   // any key before the read lands builds the dispatcher's chord map
    p.key("n", { alt: true });
    assert.deepEqual(p.toggled, [], "before the read lands the pane has no command: the bound key does nothing");
    rr.state = "ok"; rr.rows = [NOTES];
    p.land(rr);
    p.key("n", { alt: true });
    assert.deepEqual(p.toggled, ["notes"], "after the read lands the bound key runs the pane's command");
  } finally { p.restore(); }
  const q = boot({ state: "ok", rows: [NOTES], error: "" }, { "romp:keys": JSON.stringify({ "pane.notes": "Alt+N" }) });
  try {
    q.key("n", { alt: true });
    assert.deepEqual(q.toggled, ["notes"], "the contrast: a read in at boot, the key works at once");
  } finally { q.restore(); }
});
