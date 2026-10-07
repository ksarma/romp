// The gear's Panes section and the panes defined at the kernel (gear.js registryPanes, recordsLine and its romp-pane-records
// listener; plans/panes-as-data.md). The shell builds those panes in the browser from its GET /panes read, one source for the
// pane records, and keeps the read's outcome in window.__rompPaneRecords; the gear reads it from its parent (the settings page is
// a same-origin frame of the shell), so the section and the rail come from the same read. Executed here:
//   - the rows: the shipped Artifacts row from the shell's body attribute, then each row the read lists, by id, title and flags,
//     the title as text; a row the attribute already lists, or one without a string id, is not added;
//   - a failed read says so in place of the rows, with its reason and the way out; a read still loading says that;
//   - a gear opened before the read lands renders the rows again on the builder's romp-pane-records;
//   - that render waits out a press on the section (actions.ts pressHold, ui/CLAUDE.md's click-safety rule): a rebuild while the
//     pointer is down takes the pressed box away and its click with it, so the rows are rendered after the release, from the
//     store the click has just written. A key held on the section holds it the same way until its keyup (Space
//     toggles a box on its keyup), and the rebuild puts the focus back on the control that had it;
//   - the read's line is a status in the section's flow (rs-note), never a row's hover text (gear.css hides an rs-sub
//     until its row is hovered or focused), read here from the classes and gear.css's rules; the served leg reads it on
//     screen.
// initGear builds the whole modal, so the section's code is LIFTED from gear.js (the browse-route idiom) and run over a small fake
// DOM, a stand-in shell window holding the read's state and the settings frame's own window. The served leg
// (tests/test_pane_registry_served.py) drives the same section in Chromium and WebKit.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { pressHold } from "./actions";
import { hideEdges } from "../test-dom-shim";   // the fake-DOM rule (ui/test-dom-shim.test.ts): a node enumerates its primitives alone, so a failing dump never walks the tree

const GEAR = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "gear.js"), "utf8");
const GEAR_CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "gear.css"), "utf8");
// the shell's body attribute: the shipped Artifacts record's row alone (tests/test_pane_registry.py ARTIFACTS_ROW)
const ARTIFACTS_ROW = { id: "artifacts", title: "Artifacts", protocol: "romp", experimental: true, on: false, builtin: true };
// rows as the shell's builder keeps them in the read's state (rows), one per record shape
const NOTES = { id: "notes", title: "Notebook", on: true, experimental: false, protocol: "romp", src: "/pane/notes/" };
const DOCS = { id: "docs", title: "A <b>&", on: true, experimental: false, protocol: "none", src: "http://TESTHOST:9/docs/?ref=readme" };
const LAB = { id: "lab", title: "Lab", on: false, experimental: true, protocol: "none", src: "/feed" };
const TAIL = ", its column and its button are gone from this browser; on, the rail's toggle shows it.";
const ARTIFACTS_SUB = "Experimental. A session's written, shown and dropped files as a list and a grid of large thumbnails. Off (the default for an experimental pane)" + TAIL;
const DEFINED_SUB = "A pane defined at the kernel (romp pane). Off" + TAIL;
const DEFINED_EXP_SUB = "Experimental. A pane defined at the kernel (romp pane). Off (the default for an experimental pane)" + TAIL;

/** A node of the section: its tag, id, class, the box's type and checked state, its own text and its children. */
class El extends EventTarget {
  tag: string; id = ""; className = ""; type = ""; checked = false; hidden = false; own = "";
  attrs: Record<string, string> = {};
  children: El[] = [];
  parentNode: El | null = null;
  constructor(tag: string) { super(); this.tag = tag; hideEdges(this); }
  get textContent(): string { return this.own + this.children.map((c) => c.textContent).join(""); }
  // the DOM's setter replaces the children: the section clears its box with textContent = '' before it renders again
  set textContent(v: string) { this.own = String(v); for (const c of this.children) c.parentNode = null; this.children.length = 0; }
  setAttribute(k: string, v: string): void { this.attrs[k] = String(v); }
  getAttribute(k: string): string | null { return k in this.attrs ? this.attrs[k] : null; }
  appendChild(c: El): El { this.children.push(c); c.parentNode = this; return c; }
  focus(): void { focused.el = this; }
  contains(o: El | null): boolean { for (let n = o; n; n = n.parentNode) if (n === this) return true; return false; }
}
/** The settings frame's focused node (document.activeElement); section() clears it. */
const focused: { el: El | null } = { el: null };
const all = (e: El): El[] => e.children.flatMap((c) => [c, ...all(c)]);
const hasClass = (e: El, c: string): boolean => e.className.split(/\s+/).includes(c);

type Row = { id: string; title: string; sub: string; checked: boolean };
/** The section as a reader sees it: one entry per pane row (its box's id less the prefix, the bold title, the hint, the box). */
function rowsOf(box: El): Row[] {
  return box.children.filter((c) => c.tag === "label").map((lab) => {
    const cb = all(lab).find((n) => n.tag === "input")!; const b = all(lab).find((n) => n.tag === "b")!; const sub = all(lab).find((n) => hasClass(n, "rs-sub"))!;
    return { id: cb.id.replace(/^rs-pane-/, ""), title: b.textContent, sub: sub.textContent, checked: cb.checked };
  });
}
/** The read's own line in the section (its text and role), or null when there is none. */
function lineOf(box: El): { text: string; role: string | null } | null {
  const ln = box.children.find((c) => hasClass(c, "rs-panes-read"));
  return ln ? { text: ln.textContent, role: ln.getAttribute("role") } : null;
}
/** gear.css's rules that hide what they select: [selector, declarations] for each rule setting display: none. */
const HIDING = Array.from(GEAR_CSS.replace(/\/\*[\s\S]*?\*\//g, "").matchAll(/([^{}]+)\{([^}]*)\}/g))
  .filter((m) => /display:\s*none/.test(m[2])).flatMap((m) => m[1].split(",").map((sel) => sel.trim()));
const boxOf = (box: El, id: string): El | undefined => all(box).find((n) => n.tag === "input" && n.id === "rs-pane-" + id);

type Records = { state: string; rows: unknown; error: string };
type Store = { panes?: Record<string, boolean> };
/** The Panes section lifted from gear.js and run in a settings frame whose parent is a shell holding `rr` as its read's state. */
function section(rr: Records, store: Store = {}) {
  const a = GEAR.indexOf("  var BUILTIN_HINTS = {");
  const b = GEAR.indexOf("  // the section is the dashboard's: VS Code's panels", a);
  assert.ok(a > 0 && b > a, "gear.js: the Panes section's anchors not found; re-anchor");
  const box = new El("div"); box.id = "rs-panes-data";
  let attached = true;
  const byId = (id: string): El | null =>
    (id === "rs-panes-data" ? (attached ? box : null) : all(box).find((n) => n.id === id) || null);
  const doc = { getElementById: byId, createElement: (tag: string) => new El(tag),
    get activeElement() { return focused.el; } };
  focused.el = null;
  const shell: any = new EventTarget();
  shell.document = { body: { getAttribute: (k: string) => (k === "data-panes" ? JSON.stringify([ARTIFACTS_ROW]) : null) } };
  shell.__rompPaneRecords = rr;
  const frame: any = new EventTarget();
  frame.parent = shell;
  hideEdges(frame);
  let st: Store = JSON.parse(JSON.stringify(store));
  const saved: Store[] = [];
  const load = (): Store => JSON.parse(JSON.stringify(st));
  const save = (s: Store): void => { st = JSON.parse(JSON.stringify(s)); saved.push(st); };
  const panesOf = (s: Store): Record<string, boolean> => Object.assign({}, s && s.panes);
  const g = globalThis as any; const had = "window" in g; const prev = g.window;
  g.window = frame;   // pressHold's release target defaults to the page's window: the settings frame's, as in the browser
  let api: { renderRegistryRows: (s: Store) => void };
  try {
    api = new Function("window", "document", "AC", "load", "save", "panesOf", GEAR.slice(a, b) + "\nreturn { renderRegistryRows: renderRegistryRows };")(frame, doc, { pressHold }, load, save, panesOf);
  } finally { if (had) g.window = prev; else delete g.window; }
  return {
    box, saved, store: () => st,
    open: () => api.renderRegistryRows(load()),   // what the gear's open does for the section (renderRegistryRows(s))
    land: () => shell.dispatchEvent(new CustomEvent("romp-pane-records", { detail: { state: rr.state, rows: rr.rows || [], frames: [], error: rr.error } })),
    press: () => box.dispatchEvent(Object.assign(new Event("pointerdown"), { button: 0 })),
    release: () => frame.dispatchEvent(new Event("pointerup")),
    keydown: () => box.dispatchEvent(new Event("keydown")),   // the section hears a key go down on any of its controls
    keyup: () => frame.dispatchEvent(new Event("keyup")),
    blur: () => frame.dispatchEvent(new Event("blur")),
    detach: () => { attached = false; },
  };
}
const afterTimers = (): Promise<void> => new Promise((r) => setTimeout(r, 0));

test("the Panes rows: the shipped Artifacts row from the shell's attribute, then each pane the shell's read lists, by its title as text and its flags", () => {
  const s = section({ state: "ok", rows: [NOTES, DOCS, LAB, { id: "artifacts", title: "Artifacts again", on: true, experimental: false }, { id: 7, title: "x" }, null], error: "" }, { panes: { notes: false } });
  s.open();
  assert.deepEqual(rowsOf(s.box), [
    { id: "artifacts", title: "Artifacts", sub: ARTIFACTS_SUB, checked: false },
    { id: "notes", title: "Notebook", sub: DEFINED_SUB, checked: false },
    { id: "docs", title: "A <b>&", sub: DEFINED_SUB, checked: true },
    { id: "lab", title: "Lab", sub: DEFINED_EXP_SUB, checked: false },
  ], "the attribute's row, then the read's rows in its order: a stored false holds, a normal pane defaults on, an experimental one off; " +
    "the title is the text of the row as written; a row the attribute already lists is not added again, a row without a string id is dropped");
  assert.equal(lineOf(s.box), null, "a read that is in has no line of its own");
  const cb = boxOf(s.box, "docs")!; cb.checked = false; cb.dispatchEvent(new Event("change"));
  assert.deepEqual(s.store().panes, { notes: false, docs: false }, "a defined pane's box writes settings.panes[id], as the shipped rows' boxes do");
});

test("a read that failed says so in the Panes section, with its reason and the way out; a read still loading says it is still reading", () => {
  const failed = section({ state: "failed", rows: null, error: "/panes answered HTTP 500" });
  failed.open();
  assert.deepEqual(lineOf(failed.box), { text: "Couldn't read the panes defined at the kernel (/panes answered HTTP 500). Reload to try again.", role: "status" },
    "the failed read's line, in place of the defined panes' rows");
  assert.deepEqual(rowsOf(failed.box).map((r) => r.id), ["artifacts"], "the shipped row stands beside it");
  const loading = section({ state: "loading", rows: null, error: "" });
  loading.open();
  assert.deepEqual(lineOf(loading.box), { text: "Still reading the panes defined at the kernel.", role: "status" }, "the read still under way says so");
  assert.deepEqual(rowsOf(loading.box).map((r) => r.id), ["artifacts"]);
  const reasonless = section({ state: "failed", rows: null, error: "" });
  reasonless.open();
  assert.equal(lineOf(reasonless.box)!.text, "Couldn't read the panes defined at the kernel. Reload to try again.", "a failure with no reason carries no empty parentheses");
});

test("a gear opened before the read lands renders its rows again when the builder's romp-pane-records arrives on the shell", () => {
  const rr: Records = { state: "loading", rows: null, error: "" };
  const s = section(rr, { panes: { lab: true } });
  s.open();
  assert.deepEqual(rowsOf(s.box).map((r) => r.id), ["artifacts"], "before the read lands: the shipped row");
  rr.state = "ok"; rr.rows = [NOTES, LAB];
  s.land();
  assert.deepEqual(rowsOf(s.box).map((r) => [r.id, r.checked]), [["artifacts", false], ["notes", true], ["lab", true]],
    "the read's rows are in once its event arrives, with the stored settings read again");
  assert.equal(lineOf(s.box), null, "and the still-reading line is gone");
  s.detach();
  assert.doesNotThrow(() => s.land(), "a section no longer on the page ignores the event");
});

test("a read landing while a Panes row is pressed renders after the release, so the pressed box keeps its click and the rows show what it saved", async () => {
  const rr: Records = { state: "loading", rows: null, error: "" };
  const s = section(rr);
  s.open();
  const pressed = boxOf(s.box, "artifacts")!;
  s.press();
  rr.state = "ok"; rr.rows = [NOTES];
  s.land();
  assert.ok(all(s.box).includes(pressed), "under the press the section is not rebuilt: the pressed box is still in it, so its click can land");
  pressed.checked = true; pressed.dispatchEvent(new Event("change"));   // the click the release brings
  assert.deepEqual(s.saved.map((x) => x.panes), [{ artifacts: true }], "the click saved the box's change");
  s.release();
  await afterTimers();
  assert.deepEqual(rowsOf(s.box).map((r) => [r.id, r.checked]), [["artifacts", true], ["notes", true]],
    "after the release the rows are rendered from the read, and the pressed row shows what its click saved");
  assert.ok(!all(s.box).includes(pressed), "the render ran: the old box is gone");
  assert.equal(lineOf(s.box), null);
});

test("the read's line is a status in the section's flow, not a row's hover text: an rs-note gear.css shows", () => {
  const reads = [{ state: "failed", rows: null, error: "/panes answered HTTP 500" },
    { state: "loading", rows: null, error: "" }];
  for (const rr of reads) {
    const s = section(rr);
    s.open();
    const ln = s.box.children.find((c) => hasClass(c, "rs-panes-read"))!;
    assert.ok(ln, rr.state + ": the section has the read's line");
    assert.ok(hasClass(ln, "rs-note"), rr.state + ": the line is an rs-note, the inline status class: " + ln.className);
    assert.ok(!hasClass(ln, "rs-row") && !all(ln).some((n) => hasClass(n, "rs-sub")),
      rr.state + ": not a row and no rs-sub inside it (gear.css shows an rs-sub only while its row is hovered or "
      + "focused)");
    assert.equal(ln.getAttribute("role"), "status", rr.state + ": announced as a status");
    assert.ok(ln.textContent.length > 0, rr.state + ": it carries its text, so the :empty rule does not hide it");
  }
  const hiders = HIDING.filter((sel) => /\.rs-note\b|\.rs-panes-read\b|\.rs-panes-row\b/.test(sel));
  assert.deepEqual(hiders, ["#rsettings .rs-note:empty"],
    "the one gear.css rule that hides the line's classes hides an empty note");
});

test("a rebuild when the read lands puts the focus back on the Panes row that had it", () => {
  const rr: Records = { state: "loading", rows: null, error: "" };
  const s = section(rr);
  s.open();
  const old = boxOf(s.box, "artifacts")!;
  old.focus();
  rr.state = "ok"; rr.rows = [NOTES];
  s.land();
  const now = boxOf(s.box, "artifacts")!;
  assert.ok(now !== old, "the rows were rebuilt");
  assert.ok(focused.el === now, "the focus is on the rebuilt Artifacts box, not left on the box the rebuild removed");
  const elsewhere = new El("input"); elsewhere.id = "rs-compact";
  const t = section({ state: "loading", rows: null, error: "" });
  t.open();
  elsewhere.focus();
  t.land();
  assert.ok(focused.el === elsewhere, "a focus outside the section is left where it is");
});

test("a key held on a Panes row holds the rebuild until its keyup: a Space across the landing toggles it", async () => {
  const rr: Records = { state: "loading", rows: null, error: "" };
  const s = section(rr);
  s.open();
  const pressed = boxOf(s.box, "artifacts")!;
  pressed.focus();
  s.keydown();
  rr.state = "ok"; rr.rows = [NOTES];
  s.land();
  assert.ok(all(s.box).includes(pressed),
    "under the key the section is not rebuilt: the box that saw the keydown is still in it");
  pressed.checked = true; pressed.dispatchEvent(new Event("change"));   // the click Space brings with its keyup
  s.keyup();
  assert.ok(all(s.box).includes(pressed), "the render waits a tick past the keyup, so the keyup's click lands first");
  await afterTimers();
  assert.deepEqual(rowsOf(s.box).map((r) => [r.id, r.checked]), [["artifacts", true], ["notes", true]],
    "after the keyup the rows are rendered from the read, the toggled row as its click saved it");
  assert.deepEqual(s.saved.map((x) => x.panes), [{ artifacts: true }], "the toggle was saved");
  assert.ok(focused.el === boxOf(s.box, "artifacts"), "and the focus is on the rebuilt box");
  const brr: Records = { state: "loading", rows: null, error: "" };
  const b = section(brr);
  b.open();
  b.keydown();
  brr.state = "ok"; brr.rows = [NOTES];
  b.land();
  assert.deepEqual(rowsOf(b.box).map((r) => r.id), ["artifacts"], "held: not rebuilt yet");
  b.blur();
  await afterTimers();
  assert.deepEqual(rowsOf(b.box).map((r) => r.id), ["artifacts", "notes"], "the window's blur releases the hold too");
});
