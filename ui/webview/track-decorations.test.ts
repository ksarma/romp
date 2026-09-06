// The decorations module's behavior beyond the marks (editor-track.test.ts covers those and the ledger): which
// pointer may decide a change, where focus goes after a decision, and the hover cue's life across a destroy —
// departures 6, 7 and 8 in track-decorations.ts (plans/file-review.md, Slice 5; the 2026-09-06 review).
//
// Two legs. The executed leg drives the exported handler object and PointerTracker under node with stand-in
// views, targets and documents (no DOM here, which is why the module's `closest` is duck-typed). The browser leg
// mounts the real chunk in Chromium and checks the same three things end to end: under touch emulation a tap on a
// mark or on a struck widget decides nothing while a mouse click in the same context accepts; a click from outside
// the editor accepts AND focuses it, so Control-Z undoes; a destroy under the pointer leaves the next mount's hover
// cue working. The browser leg skips LOUDLY without playwright or the browser (CI installs none), as the other
// browser legs do; the executed leg runs everywhere.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import type { EditorView } from "@codemirror/view";
import { changeHandlers, pointerDecides, PointerTracker, releaseHover, CLS, type TrackHost } from "./track-decorations";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const DECO = fs.readFileSync(path.join(UI, "track-decorations.ts"), "utf8");

// ── the pure policy ───────────────────────────────────────────────────────────────────────────────

test("pointerDecides: a mouse decides; a finger or a pen does not; an unknown pointer keeps the mouse rule", () => {
  assert.equal(pointerDecides("mouse"), true);
  assert.equal(pointerDecides("touch"), false, "a tap carries no modifier: it could only accept, silently");
  assert.equal(pointerDecides("pen"), false);
  assert.equal(pointerDecides(null), true, "no pointerdown seen (a browser without pointer events, a synthetic press)");
  assert.equal(pointerDecides(undefined), true);
  assert.equal(pointerDecides(""), true, "the spec's empty string for a device the browser cannot name");
});

// ── stand-ins: what the handlers read, what the cue writes ───────────────────────────────────────

/** Matches the module's selectors: simple selectors of `.class` and `[attr]` / `[attr="v"]` parts, joined by commas. */
function matches(el: El, sel: string): boolean {
  return sel.split(",").some((s) => {
    const parts = s.trim().match(/\.[\w-]+|\[[^\]]+\]/g) || [];
    return parts.length > 0 && parts.every((p) => {
      if (p[0] === ".") return el.classes.has(p.slice(1));
      const m = /^\[([\w-]+)(?:="([^"]*)")?\]$/.exec(p);
      assert.ok(m, "selector part the stand-in cannot read: " + p);
      const v = el.getAttribute(m[1]);
      return v !== null && (m[2] === undefined || v === m[2]);
    });
  });
}
class El {
  classes = new Set<string>();
  parent: El | null = null;
  ownerDocument: Doc | null = null;
  readonly classList = {
    add: (c: string) => { this.classes.add(c); },
    remove: (c: string) => { this.classes.delete(c); },
    contains: (c: string) => this.classes.has(c),
  };
  constructor(readonly attrs: Record<string, string> = {}, cls: string[] = []) { cls.forEach((c) => this.classes.add(c)); }
  getAttribute(n: string): string | null { return n in this.attrs ? this.attrs[n] : null; }
  closest(sel: string): El | null { for (let e: El | null = this; e; e = e.parent) if (matches(e, sel)) return e; return null; }
  contains(other: unknown): boolean { for (let e = other as El | null; e; e = e.parent) if (e === this) return true; return false; }
  /** Descendants only, the way relightHover queries the editor root. */
  querySelectorAll(sel: string): El[] { return (this.ownerDocument ? this.ownerDocument.els : []).filter((e) => e !== this && this.contains(e) && matches(e, sel)); }
  /** PointerTracker wires its pointerdown here; the executed leg feeds pressType directly, so these record nothing. */
  addEventListener(): void {}
  removeEventListener(): void {}
}
class Doc {
  els: El[] = [];
  add(...els: El[]): this { for (const e of els) { e.ownerDocument = this; this.els.push(e); } return this; }
  drop(...els: El[]): void { this.els = this.els.filter((e) => !els.includes(e)); }
  querySelectorAll(sel: string): El[] { return this.els.filter((e) => matches(e, sel)); }
  querySelector(sel: string): El | null { return this.querySelectorAll(sel)[0] || null; }
}
type Press = { pressType: string | null } | null;
/** An editor as the handlers see it: its root, focus, and the PointerTracker plugin (or none). */
function view(doc: Doc, o: { press?: Press; hasFocus?: boolean } = {}) {
  const dom = new El({}, ["cm-editor"]);
  doc.add(dom);
  const calls: string[] = [];
  const v = {
    dom, calls,
    hasFocus: o.hasFocus ?? false,
    focus() { calls.push("focus"); v.hasFocus = true; },
    plugin: () => (o.press === undefined ? { pressType: "mouse" } : o.press),
  };
  return v;
}
type V = ReturnType<typeof view>;
const asView = (v: V) => v as unknown as EditorView;
function host(resolvable: number[]) {
  const resolved: Array<[number, boolean]> = [];
  const h: TrackHost = {
    onOpenPanel: () => {},
    resolveInline: (from, reject) => { resolved.push([from, reject]); },
    hasResolvableAt: (_v, from) => resolvable.includes(from),
    onOpsChanged: () => {},
    hydrateView: () => {},
  };
  return { h, resolved };
}
function press(target: El, o: { button?: number; altKey?: boolean } = {}) {
  const ev = { target, button: o.button ?? 0, altKey: !!o.altKey, metaKey: false, ctrlKey: false, prevented: false, stopped: false,
    preventDefault() { ev.prevented = true; }, stopPropagation() { ev.stopped = true; } };
  return ev;
}
type Ev = ReturnType<typeof press>;
const inMark = (v: V, from = 4) => { const e = new El({ "data-hk-from": String(from), "data-hk-side": "new" }, [CLS.ins]); e.parent = v.dom; v.dom.ownerDocument!.add(e); return e; };
const inWidget = (v: V, from = 4) => { const e = new El({ "data-hk-from": String(from), "data-hk-side": "old" }, [CLS.del]); e.parent = v.dom; v.dom.ownerDocument!.add(e); return e; };
const run = (h: TrackHost, name: "mousedown" | "click" | "mouseover", ev: Ev | { target: El | null }, v: V) =>
  (changeHandlers(h, false)[name] as (this: unknown, e: unknown, view: EditorView) => boolean | void)(ev, asView(v));

// ── departure 6: only a mouse press decides ──────────────────────────────────────────────────────

test("a touch press on a mark decides nothing: mousedown falls through untouched, and so does its click", () => {
  const { h, resolved } = host([4]);
  const v = view(new Doc(), { press: { pressType: "touch" } });
  const mark = inMark(v);
  const md = press(mark);
  assert.equal(run(h, "mousedown", md, v), false, "not ours: CodeMirror and the browser place the caret");
  assert.equal(md.prevented, false);
  assert.deepEqual(resolved, [], "no accept");
  assert.deepEqual(v.calls, [], "no focus stolen either: the native tap focuses");
  const ck = press(mark);
  assert.equal(run(h, "click", ck, v), false, "nothing was decided, so the click is not swallowed");
  assert.equal(ck.prevented, false);
});

test("a pen press is left to the browser the same way", () => {
  const { h, resolved } = host([4]);
  const v = view(new Doc(), { press: { pressType: "pen" } });
  assert.equal(run(h, "mousedown", press(inMark(v)), v), false);
  assert.deepEqual(resolved, []);
});

test("a mouse press accepts, Alt rejects, and the click after a decision is swallowed; a view without the tracker keeps the mouse rule", () => {
  const { h, resolved } = host([4]);
  const v = view(new Doc(), { press: { pressType: "mouse" }, hasFocus: true });
  const mark = inMark(v);
  const md = press(mark);
  assert.equal(run(h, "mousedown", md, v), true);
  assert.equal(md.prevented, true);
  assert.deepEqual(resolved, [[4, false]]);
  const ck = press(mark);
  assert.equal(run(h, "click", ck, v), true);
  assert.equal(ck.prevented && ck.stopped, true, "the click is swallowed so nothing above the editor acts on it");
  run(h, "mousedown", press(mark, { altKey: true }), v);
  assert.deepEqual(resolved.at(-1), [4, true], "Alt rejects");
  // the tracker crashed or was never installed (a stand-in view): the policy is the mouse's, as before
  const bare = view(new Doc(), { press: null, hasFocus: true });
  const { h: h2, resolved: r2 } = host([4]);
  assert.equal(run(h2, "mousedown", press(inMark(bare)), bare), true);
  assert.deepEqual(r2, [[4, false]]);
});

test("a struck widget's click is swallowed after a mouse press and left alone after a tap (CHANGE_SEL covers both halves)", () => {
  const { h } = host([9]);
  const mouse = view(new Doc(), { press: { pressType: "mouse" } });
  const ck = press(inWidget(mouse, 9));
  assert.equal(run(h, "click", ck, mouse), true);
  const touch = view(new Doc(), { press: { pressType: "touch" } });
  const tk = press(inWidget(touch, 9));
  assert.equal(run(h, "click", tk, touch), false);
  assert.equal(tk.prevented, false);
});

// ── departure 7: a decision focuses the editor ───────────────────────────────────────────────────

test("a mouse decision on an unfocused editor focuses it, so the undo chord reaches CodeMirror; a focused one is left alone", () => {
  const { h, resolved } = host([4]);
  const cold = view(new Doc(), { press: { pressType: "mouse" }, hasFocus: false });
  assert.equal(run(h, "mousedown", press(inMark(cold)), cold), true);
  assert.deepEqual(resolved, [[4, false]]);
  assert.deepEqual(cold.calls, ["focus"], "the prevented mousedown moves no focus natively and stops CodeMirror's own handler: we focus");
  const warm = view(new Doc(), { press: { pressType: "mouse" }, hasFocus: true });
  run(h, "mousedown", press(inMark(warm)), warm);
  assert.deepEqual(warm.calls, [], "already focused: nothing to do");
  // a drifted mark (nothing resolves there) falls through WITHOUT focusing: CodeMirror's own handler runs and does
  const { h: none, resolved: r0 } = host([]);
  const drift = view(new Doc(), { press: { pressType: "mouse" }, hasFocus: false });
  assert.equal(run(none, "mousedown", press(inMark(drift)), drift), false);
  assert.deepEqual(r0, []);
  assert.deepEqual(drift.calls, []);
});

// ── departure 8: the hover cache is released with the editor ─────────────────────────────────────

/** Both halves of the change at `from` in `v`'s document, and a plain-text target for resetting the cue. */
function pair(v: V, from = 2) { return { ins: inMark(v, from), del: inWidget(v, from), text: (() => { const t = new El({}, ["cm-line"]); t.parent = v.dom; return t; })() }; }
const lit = (doc: Doc) => doc.querySelectorAll(`.${CLS.hover}`).length;

test("hovering lights both halves; a destroy under the pointer releases the cache so the re-mounted change lights on its first mouseover", () => {
  const { h } = host([2]);
  const doc = new Doc();
  const v = view(doc);
  const a = pair(v);
  run(h, "mouseover", press(a.ins), v);
  assert.equal(lit(doc), 2, "the mark and its struck widget light together");
  // the editor is destroyed under the pointer (Ctrl-S, or Cancel): its elements go, no mouseout ever fires
  const tracker = new PointerTracker(asView(v));
  tracker.destroy();
  doc.drop(v.dom, a.ins, a.del);
  // Edit again: a new editor shows the same change at the same offset
  const v2 = view(doc);
  const b = pair(v2);
  run(h, "mouseover", press(b.ins), v2);
  assert.equal(lit(doc), 2, "without the release, the same key short-circuited and neither half lit");
  assert.ok(b.ins.classes.has(CLS.hover) && b.del.classes.has(CLS.hover));
  run(h, "mouseover", press(b.text), v2);
  assert.equal(lit(doc), 0);
});

test("the cache short-circuit is real (a same-key mouseover repaints nothing), which is what the release exists for", () => {
  const { h } = host([2]);
  const doc = new Doc();
  const v = view(doc);
  const a = pair(v);
  run(h, "mouseover", press(a.ins), v);
  a.ins.classes.delete(CLS.hover); a.del.classes.delete(CLS.hover);          // the elements were rebuilt without the cue
  run(h, "mouseover", press(a.del), v);
  assert.equal(lit(doc), 0, "same key, same document: the short-circuit skips the repaint — the upstream behavior");
  releaseHover(asView(v));                                                   // stale, in this editor: cleared
  run(h, "mouseover", press(a.del), v);
  assert.equal(lit(doc), 2);
  run(h, "mouseover", press(a.text), v);
});

test("releaseHover leaves another editor's lit cue in the same document alone, and ignores a cache that is another document's", () => {
  const { h } = host([2]);
  const doc = new Doc();
  const a = view(doc), b = view(doc);
  const pa = pair(a);
  run(h, "mouseover", press(pa.ins), a);
  assert.equal(lit(doc), 2);
  releaseHover(asView(b));                                                   // b is destroyed; the cue is a's
  assert.equal(lit(doc), 2, "not b's to clear");
  const other = view(new Doc());
  releaseHover(asView(other));                                               // a different document entirely
  assert.equal(lit(doc), 2);
  releaseHover(asView(a));
  assert.equal(lit(doc), 0);
  run(h, "mouseover", press(pa.ins), a);
  assert.equal(lit(doc), 2, "cleared: the next mouseover on the same key lights again");
  run(h, "mouseover", press(pa.text), a);
});

test("a redraw that rewrote the mark's class darkens that half; the tracker's docViewUpdate re-lights it, and only in the editor whose cue it is", () => {
  const { h } = host([2]);
  const doc = new Doc();
  const a = view(doc), b = view(doc);
  const pa = pair(a);
  run(h, "mouseover", press(pa.ins), a);
  assert.equal(lit(doc), 2);
  const pb = pair(b);                                                        // a second editor mounts a change at the same offset, unlit
  pa.ins.classes.delete(CLS.hover);                                          // Tile.sync → setAttrs rewrote the mark's class attribute
  assert.equal(lit(doc), 1, "the widget half keeps its DOM and its cue; the mark half went dark under a pointer that never left");
  new PointerTracker(asView(b)).docViewUpdate();
  assert.equal(lit(doc), 1, "b redrew: its same-offset change is not the hovered one");
  assert.ok(!pb.ins.classes.has(CLS.hover) && !pb.del.classes.has(CLS.hover));
  new PointerTracker(asView(a)).docViewUpdate();
  assert.equal(lit(doc), 2, "a redrew: the cue is back on both halves");
  assert.ok(pa.ins.classes.has(CLS.hover) && pa.del.classes.has(CLS.hover));
  // a pure insertion has ONE half: wiped, nothing stays lit, and the redraw hook still knows whose cue it is
  run(h, "mouseover", press(pa.text), a);
  const c = view(doc);
  const only = inMark(c, 7);
  run(h, "mouseover", press(only), c);
  assert.equal(lit(doc), 1);
  only.classes.delete(CLS.hover);
  new PointerTracker(asView(c)).docViewUpdate();
  assert.ok(only.classes.has(CLS.hover), "re-lit with no lit sibling to go by");
  run(h, "mouseover", press(pa.text), c);
  assert.equal(lit(doc), 0);
});

// ── PointerTracker: the pointerdown memo and its lifecycle ───────────────────────────────────────

test("PointerTracker records the press's pointer type from a capture-phase pointerdown on the editor root and removes it on destroy", () => {
  const listeners: Array<{ type: string; fn: (e: { pointerType: string }) => void; opts: unknown }> = [];
  const removed: Array<{ type: string; fn: unknown; opts: unknown }> = [];
  const dom = {
    addEventListener: (type: string, fn: (e: { pointerType: string }) => void, opts: unknown) => { listeners.push({ type, fn, opts }); },
    removeEventListener: (type: string, fn: unknown, opts: unknown) => { removed.push({ type, fn, opts }); },
    ownerDocument: new Doc(), contains: () => false,
  };
  const t = new PointerTracker({ dom } as unknown as EditorView);
  assert.equal(t.pressType, null, "nothing pressed yet");
  assert.equal(listeners.length, 1);
  assert.equal(listeners[0].type, "pointerdown");
  assert.deepEqual(listeners[0].opts, { capture: true, passive: true }, "capture: a press on a widget that ignores events must count; passive: it cancels nothing");
  listeners[0].fn({ pointerType: "touch" });
  assert.equal(t.pressType, "touch");
  listeners[0].fn({ pointerType: "mouse" });
  assert.equal(t.pressType, "mouse", "the memo is the CURRENT press: every mousedown is preceded by its own pointerdown");
  listeners[0].fn({ pointerType: "" });
  assert.equal(t.pressType, null, "an unnamed device is unknown, not a finger");
  t.destroy();
  assert.equal(removed.length, 1);
  assert.equal(removed[0].fn, listeners[0].fn, "the same function, so it really comes off");
  assert.equal(removed[0].opts, true, "the capture flag, matching how it went on");
});

// ── source pins: the three departures are named, wired, and the tracker rides in the extension set ──

test("track-decorations.ts names departures 6-8, gates both mousedown paths on the press, focuses after a decision, and ships the tracker", () => {
  assert.match(DECO, /^\/\/\s*6\. Only a MOUSE press decides/m);
  assert.match(DECO, /^\/\/\s*7\. A decision focuses the editor/m);
  assert.match(DECO, /^\/\/\s*8\. FIX: the hover cue survives the editor's own DOM work/m);
  assert.match(DECO, /docViewUpdate\(\): void \{ relightHover\(this\.view\); \}/, "the redraw hook re-lights the cached change");
  // the widget's own listener: the view first, the press gate before the click policy, focus after the decision
  assert.match(DECO, /const view = EditorView\.findFromDOM\(el\);\n\s*if \(view && !pressDecides\(view\)\) return;/);
  assert.match(DECO, /if \(view\) this\.host\.resolveInline\(this\.offset, action === "reject", view\);\n\s*if \(view && !view\.hasFocus\) view\.focus\(\);/);
  // the editor-level handlers: the same gate on mousedown AND click, focus after the decision
  assert.match(DECO, /mousedown: \(event, view\) => \{\n\s*const add = closest\(event\.target, `\.\$\{CLS\.ins\}\[data-hk-from\]`\);\n\s*if \(add\) \{\n\s*if \(!pressDecides\(view\)\) return false;/);
  assert.match(DECO, /host\.resolveInline\(from, action === "reject", view\);\n\s*if \(!view\.hasFocus\) view\.focus\(\);[^\n]*\n\s*return true;/);
  assert.match(DECO, /click: \(event, view\) => \{\n\s*const hit = closest\(event\.target, CHANGE_SEL\);\n\s*if \(hit\) \{\n\s*if \(!pressDecides\(view\)\) return false;/);
  // the tracker is a ViewPlugin in the returned set, and its destroy releases the hover cache
  assert.match(DECO, /const pointerTracker = ViewPlugin\.fromClass\(PointerTracker\);/);
  assert.match(DECO, /return \[metaField, decoField, persist, clicks, pointerTracker, hydrateOnMount\];/);
  assert.match(DECO, /destroy\(\): void \{\n\s*this\.view\.dom\.removeEventListener\("pointerdown", this\.note, true\);\n\s*releaseHover\(this\.view\);/);
  // no time window anywhere: the press is keyed on the pointerdown event, not on a touch timestamp
  assert.doesNotMatch(DECO, /lastTouchTime|Date\.now\(\)|setTimeout/, "event-based, never a time heuristic");
});

// ── the browser leg: the real chunk in Chromium ──────────────────────────────────────────────────

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
const SUB_DOC = "I like cats.";
const SUB_RECORDS = [{ id: "s1", author: "web", ts: 1, kind: "sub", from: 2, newText: "like", oldText: "love" }];
const PAGE_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8>
<style>body{margin:0;font:16px/1.5 sans-serif}#host{margin:40px 8px 8px}.cm-editor{border:1px solid #888}</style></head>
<body><button id=outside>outside</button><div id=host></div><script src=/dist/editor-chunk.js></script>
<script>
window.__mount = function (text, records) {
  var host = document.getElementById('host'); host.replaceChildren();
  window.__ledger = null;
  window.__h = window.__rompEditor.mount(host, { text: text, ext: 'md', onChange: function () {}, onSave: function () {},
    track: { suggestions: records, onLedger: function (l) { window.__ledger = l; } } });
};
window.__state = function () {
  var a = document.activeElement;
  return { ids: window.__h.track.suggestions().map(function (s) { return s.id; }), ledger: window.__ledger,
    active: a ? (a.className || a.tagName) : '', lit: document.querySelectorAll('.tc-diff-hover').length };
};
</script></body></html>`;

async function boot(context: any, js: string) {
  const errors: string[] = [];
  const page = await context.newPage();
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  await page.route("http://romp.test/**", (route: any) => {
    const u = new URL(route.request().url());
    if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE_HTML });
    if (u.pathname === "/dist/editor-chunk.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
    return route.fulfill({ status: 404, body: "" });
  });
  await page.goto("http://romp.test/page");
  const mount = (text: string, records: unknown[]) => page.evaluate(([t, r]: [string, unknown[]]) => (window as any).__mount(t, r), [text, records] as [string, unknown[]]);
  const state = () => page.evaluate(() => (window as any).__state()) as Promise<{ ids: string[]; ledger: any; active: string; lit: number }>;
  const centre = async (sel: string) => {
    const b = await page.locator(sel).first().boundingBox();
    assert.ok(b, sel + " has a box");
    return { x: b.x + b.width / 2, y: b.y + b.height / 2 };
  };
  // a bounded wait on an event-driven outcome (the pointer events settle in the page's next frames)
  const until = async (pred: (s: { ids: string[]; ledger: any; active: string; lit: number }) => boolean, what: string) => {
    for (let i = 0; i < 60; i++) { const s = await state(); if (pred(s)) return s; await page.waitForTimeout(50); }
    const s = await state();
    assert.fail(what + " — last state " + JSON.stringify(s));
    return s;
  };
  return { page, errors, mount, state, centre, until };
}
const skipWhy = (t: any) => {
  if (!pw) { t.skip("playwright is not installed under vscode-extension — the browser leg needs it (CI installs no browsers)"); return true; }
  return false;
};
async function launch(t: any): Promise<any> {
  try { return await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright chromium on this box — this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return null; }
}

test("in Chromium with touch: a tap on a mark or a struck widget decides nothing, a mouse click in the same context accepts", async (t) => {
  if (skipWhy(t)) return;
  const browser = await launch(t); if (!browser) return;
  try {
    const context = await browser.newContext({ hasTouch: true, isMobile: true, viewport: { width: 390, height: 844 } });
    const { page, errors, mount, state, centre } = await boot(context, chunkJs());
    await mount(DOC, RECORDS);
    assert.deepEqual((await state()).ids, ["a1", "d1"]);
    const ins = await centre(".tc-diff-ins[data-hk-from='4']");
    await page.touchscreen.tap(ins.x, ins.y);
    await page.waitForTimeout(150);                                          // the compat mouse events follow the tap
    let s = await state();
    assert.deepEqual(s.ids, ["a1", "d1"], "the tap placed the caret; the insertion is still pending");
    assert.equal(s.ledger, null, "no decision reached the ledger");
    const del = await centre(".tc-diff-del[data-hk-from='15']");
    await page.touchscreen.tap(del.x, del.y);
    await page.waitForTimeout(150);
    s = await state();
    assert.deepEqual(s.ids, ["a1", "d1"], "a tap on the struck widget decides nothing either");
    assert.equal(s.ledger, null);
    // the same device with a mouse attached: the press is judged per pointer, not per device class
    await page.mouse.click(ins.x, ins.y);
    await page.waitForTimeout(100);
    s = await state();
    assert.deepEqual(s.ids, ["d1"], "a mouse click accepts");
    assert.deepEqual(s.ledger.accepted.map((e: { id: string }) => e.id), ["a1"]);
    assert.deepEqual(errors, []);
    await context.close();
  } finally { await browser.close(); }
});

test("in Chromium: a click from outside the editor accepts AND focuses it, so Control-Z undoes — on a mark and on a struck widget", async (t) => {
  if (skipWhy(t)) return;
  const browser = await launch(t); if (!browser) return;
  try {
    const context = await browser.newContext({ viewport: { width: 800, height: 500 } });
    const { page, errors, mount, state, centre, until } = await boot(context, chunkJs());
    await mount(DOC, RECORDS);
    for (const [sel, id, rest] of [[".tc-diff-ins[data-hk-from='4']", "a1", ["d1"]], [".tc-diff-del[data-hk-from='15']", "d1", ["a1"]]] as Array<[string, string, string[]]>) {
      await page.click("#outside");                                          // focus leaves the editor
      assert.equal((await state()).active, "BUTTON", "the toolbar stand-in holds focus");
      const c = await centre(sel);
      await page.mouse.click(c.x, c.y);
      let s = await until((x) => x.ids.length === 1, "the click on " + sel + " accepts");
      assert.deepEqual(s.ids, rest);
      assert.deepEqual(s.ledger.accepted.map((e: { id: string }) => e.id), [id]);
      assert.match(s.active, /cm-content/, "the editor took focus with the decision");
      await page.keyboard.press("Control+z");
      s = await until((x) => x.ids.length === 2, "undo reaches the editor");
      assert.deepEqual(s.ids, ["a1", "d1"], "the accept is undone, the change is pending again");
      assert.deepEqual(s.ledger, { accepted: [], rejected: [] }, "the ledger is net of undo");
    }
    assert.deepEqual(errors, []);
    await context.close();
  } finally { await browser.close(); }
});

test("in Chromium: hover lights both halves; destroyed under the pointer and mounted again, the same change lights on the first mouseover", async (t) => {
  if (skipWhy(t)) return;
  const browser = await launch(t); if (!browser) return;
  try {
    const context = await browser.newContext({ viewport: { width: 800, height: 500 } });
    const { page, errors, mount, state, centre, until } = await boot(context, chunkJs());
    await mount(SUB_DOC, SUB_RECORDS);
    const c = await centre(".tc-diff-ins[data-hk-from='2']");
    await page.mouse.move(c.x, c.y);
    await until((s) => s.lit === 2, "both halves light under the pointer");
    // Ctrl-S or Cancel: the viewer destroys the editor with the pointer still on the change, then Edit mounts again
    await page.evaluate(() => { (window as any).__h.destroy(); });
    assert.equal((await state().catch(() => ({ lit: -1 }))).lit, 0, "the old elements are gone with the view");
    await mount(SUB_DOC, SUB_RECORDS);
    await page.mouse.move(c.x + 1, c.y);                                     // the first mouseover inside the new editor is the change itself
    const s = await until((x) => x.lit === 2, "the re-mounted change lights on its first mouseover (the cache was released with the old editor)");
    assert.equal(s.lit, 2);
    assert.deepEqual(errors, []);
    await context.close();
  } finally { await browser.close(); }
});
