// Pinned notes (the user 2026-09-08): a session pins short notes above its own transcript for the
// person it works for; the strip between the tab bar and the transcript shows them. The strip's
// builder (pinned-notes.ts) is EXECUTED here against a small DOM stand-in (the pr-links.test.ts
// convention): order, the three-row fold, the detail fold, the linkers, the escaping and the unpin
// control; the wiring into render.ts, the two page skeletons, the kernel's frames and the styles are
// pinned at the source, the way the other webview tests pin the chat renderer.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { buildPinnedNotes, pinnedNotesKey, pinnedMoreLabel, pinnedSplit, PINNED_VISIBLE, PINNED_ACT,
  PINNED_UNPIN_LABEL, PINNED_UNPIN_ARMED, type PinnedNote, type PinnedFoldState, type PinnedLinkers } from "./pinned-notes";
import { linkifyPrRefs } from "./pr-links";

const read = (...p: string[]) => fs.readFileSync(path.resolve(process.cwd(), "..", ...p), "utf8");
const RENDER = read("ui", "webview", "render.ts");
const MODULE = read("ui", "webview", "pinned-notes.ts");
const CSS = read("ui", "webview", "styles.css");
const KERNEL = read("kernel", "kernel.py");
const SKELETON = fs.readFileSync(path.resolve(process.cwd(), "src", "page-skeleton.ts"), "utf8");
const RENDER_FN = RENDER.slice(RENDER.indexOf("function renderPinnedNotes"), RENDER.indexOf("function renderLedger"));
const dStart = RENDER.indexOf("// PINNED NOTES (the user 2026-09-08): the strip rebuilds");
const DELEGATE = RENDER.slice(dStart, RENDER.indexOf("\n})();", dStart));

// ── a DOM stand-in: text and element nodes with the members the builder and the PR linker touch ──
class T {
  nodeType = 3;
  parentNode: E | null = null;
  constructor(public textContent: string) {}
  get data(): string { return this.textContent; }
  get parentElement(): E | null { return this.parentNode; }
}
class E {
  nodeType = 1;
  parentNode: E | null = null;
  childNodes: Array<E | T> = [];
  href = ""; target = ""; rel = ""; title = ""; className = "";
  style: Record<string, string> = {};
  dataset: Record<string, string | undefined> = {};
  attrs: Record<string, string> = {};
  constructor(public tagName: string) {}
  setAttribute(n: string, v: string): void { if (n === "class") this.className = v; else if (n === "title") this.title = v; else this.attrs[n] = v; }
  getAttribute(n: string): string | null { if (n === "class") return this.className || null; if (n === "title") return this.title || null; return n in this.attrs ? this.attrs[n] : null; }
  get parentElement(): E | null { return this.parentNode; }
  get classList() {
    const self = this;
    const list = () => self.className.split(/\s+/).filter(Boolean);
    return {
      contains: (c: string) => list().includes(c),
      add: (c: string) => { if (!list().includes(c)) self.className = [...list(), c].join(" "); },
      remove: (c: string) => { self.className = list().filter((x) => x !== c).join(" "); },
    };
  }
  get textContent(): string { return this.childNodes.map((c) => c.textContent).join(""); }
  set textContent(v: string) { for (const c of this.childNodes) c.parentNode = null; this.childNodes = []; if (v) this.appendChild(new T(v)); }
  appendChild<N extends E | T>(c: N): N { c.parentNode = this; this.childNodes.push(c); return c; }
  insertBefore<N extends E | T>(n: N, ref: E | T | null): N {
    const i = ref ? this.childNodes.indexOf(ref) : -1;
    n.parentNode = this;
    this.childNodes.splice(i < 0 ? this.childNodes.length : i, 0, n);
    return n;
  }
  removeChild(c: E | T): E | T { const i = this.childNodes.indexOf(c); if (i >= 0) this.childNodes.splice(i, 1); c.parentNode = null; return c; }
  matches(sel: string): boolean {
    return sel.split(",").some((one) => { const s = one.trim(); return s.startsWith(".") ? this.classList.contains(s.slice(1)) : s.toUpperCase() === this.tagName.toUpperCase(); });
  }
  closest(sel: string): E | null {
    for (let n: E | null = this; n; n = n.parentNode) if (n.matches(sel)) return n;
    return null;
  }
  all(sel: string): E[] {
    const out: E[] = [];
    const walk = (n: E) => { for (const c of n.childNodes) if (c instanceof E) { if (c.matches(sel)) out.push(c); walk(c); } };
    walk(this);
    return out;
  }
  elements(): E[] { return this.childNodes.filter((c): c is E => c instanceof E); }
}
(globalThis as any).document = {
  createElement: (tag: string) => new E(tag.toUpperCase()),
  createTextNode: (s: string) => new T(s),
};
const doc = { createElement: (tag: string) => new E(tag.toUpperCase()) as unknown as HTMLElement };

const SID = "11111111-2222-3333-4444-555555555555";
const T0 = 1781200000;
const note = (i: number, extra: Partial<PinnedNote> = {}): PinnedNote =>
  ({ id: "pn-0000000" + i, text: "note " + i, createdT: T0 + i, ...extra });
const notes = (n: number) => Array.from({ length: n }, (_, i) => note(i));
const state = (): PinnedFoldState => ({ openDetails: new Set(), moreOpen: new Set() });
function spies() {
  const line: E[] = [], detail: E[] = [];
  const link: PinnedLinkers = { line: (n) => { line.push(n as unknown as E); }, detail: (n) => { detail.push(n as unknown as E); } };
  return { line, detail, link };
}
const build = (ns: PinnedNote[], st = state(), link = spies().link) =>
  buildPinnedNotes(doc, SID, ns, st, link) as unknown as E | null;
const rowsOf = (strip: E) => strip.all(".pn-item");
const textOf = (row: E) => row.all(".pn-text")[0];

test("nothing pinned renders nothing, and the strip takes no space", () => {
  assert.equal(build([]), null);
  assert.match(RENDER_FN, /host\.style\.display = strip \? "" : "none";/, "hidden, not an empty box");
  assert.match(KERNEL, /<div id="pinned-notes" style="display:none"><\/div>/, "hidden until notes arrive");
});

test("one compact row per note, in pin order (newest last), every note as text", () => {
  const raw = "<b>&amp; not markup</b> & a < b";
  const strip = build([note(0), note(1, { text: raw }), note(2)])!;
  const rows = rowsOf(strip);
  assert.deepEqual(rows.map((r) => r.dataset.nid), ["pn-00000000", "pn-00000001", "pn-00000002"]);
  assert.deepEqual(rows.map((r) => textOf(r).textContent), ["note 0", raw, "note 2"]);
  const t = textOf(rows[1]);
  assert.equal(t.childNodes.length, 1, "one text node: nothing parsed as markup");
  assert.ok(t.childNodes[0] instanceof T);
  const code = MODULE.split("\n").filter((l) => !l.trim().startsWith("//") && !l.trim().startsWith("*")).join("\n");
  assert.doesNotMatch(code, /innerHTML|outerHTML|insertAdjacentHTML/, "a note is untrusted text: textContent only");
});

test("at most three rows show, the newest; the older fold behind one '+N more' row where they live", () => {
  assert.equal(PINNED_VISIBLE, 3);
  assert.deepEqual(pinnedSplit([1, 2, 3]), { hidden: [], shown: [1, 2, 3] });
  assert.deepEqual(pinnedSplit([1, 2, 3, 4, 5]), { hidden: [1, 2], shown: [3, 4, 5] });
  const strip = build(notes(5))!;
  const top = strip.elements();
  assert.equal(top[0].className, "pn-fold");
  assert.equal(top[0].textContent, "+2 more");
  assert.equal(top[0].dataset.act, PINNED_ACT.more);
  assert.equal(top[0].dataset.sid, SID);
  assert.equal(top[1].className, "pn-rest", "the fold body sits with the fold, above the visible rows");
  assert.deepEqual(rowsOf(top[1]).map((r) => r.dataset.nid), ["pn-00000000", "pn-00000001"], "the two oldest hide");
  assert.deepEqual(top.slice(2).map((r) => r.dataset.nid), ["pn-00000002", "pn-00000003", "pn-00000004"], "the newest three show, in order");
  // open: the label flips and the body opens (the state the delegate writes; the repaint reads it)
  const st = state(); st.moreOpen.add(SID);
  const open = build(notes(5), st)!.elements();
  assert.equal(open[0].textContent, "hide 2 more");
  assert.ok(open[1].classList.contains("open"));
  assert.equal(pinnedMoreLabel(4, false), "+4 more");
  assert.equal(pinnedMoreLabel(4, true), "hide 4 more");
  // three or fewer: no fold at all (a fold over one row costs a click for nothing)
  assert.equal(build(notes(3))!.all(".pn-fold").length, 0);
  assert.equal(build(notes(3))!.all(".pn-rest").length, 0);
});

test("the detail folds behind a click on the row, with the user-todo row's hint; a bare row has neither", () => {
  const strip = build([note(0, { detail: "The api tests flake on the auth step" }), note(1)])!;
  const [withDetail, bare] = rowsOf(strip);
  const t = textOf(withDetail);
  assert.ok(t.classList.contains("pn-has-detail"));
  assert.equal(t.dataset.act, PINNED_ACT.toggle);
  assert.equal(t.dataset.nid, "pn-00000000");
  assert.equal(t.all(".ut-more")[0].textContent, "▸ details", "the same hint vocabulary as a user-todo row");
  const d = withDetail.all(".pn-detail")[0];
  assert.equal(d.textContent, "The api tests flake on the auth step");
  assert.ok(!d.classList.contains("open"), "folded by default: the one-line version first");
  assert.equal(textOf(bare).dataset.act, undefined, "a bare row has no click target for a fold");
  assert.equal(bare.all(".pn-detail").length, 0);
  assert.equal(bare.all(".ut-more").length, 0);
  // open state survives a rebuild through the keyed set
  const st = state(); st.openDetails.add("pn-00000000");
  const again = rowsOf(build([note(0, { detail: "more" })], st)!)[0];
  assert.ok(again.all(".pn-detail")[0].classList.contains("open"));
  assert.equal(again.all(".ut-more")[0].textContent, "▾ details");
});

test("paths and PR references link through the caller's linkers: the line pass on every row, the detail pass on every detail", () => {
  const sp = spies();
  const strip = build([note(0, { detail: "see docs/plan.md" }), note(1)], state(), sp.link)!;
  assert.deepEqual(sp.line.map((n) => n.classList.contains("pn-text")), [true, true], "the one-line text of every row");
  assert.deepEqual(sp.line.map((n) => n.childNodes[0].textContent), ["note 0", "note 1"], "the text is in place when the linker runs");
  assert.deepEqual(sp.detail.map((n) => n.classList.contains("pn-detail")), [true], "the detail of the row that has one");
  assert.equal(strip.all(".pn-text").length, 2);
  // the real PR linker over a row: `#12` becomes an anchor into the session's repository
  const link: PinnedLinkers = { line: (n) => { linkifyPrRefs(n as unknown as Node, "acme/notes-api"); }, detail: () => {} };
  const row = rowsOf(build([note(0, { text: "Waiting on CI for #12" })], state(), link)!)[0];
  const a = textOf(row).all("a");
  assert.equal(a.length, 1);
  assert.match(a[0].href, /acme\/notes-api\/pull\/12$/);
  assert.equal(textOf(row).textContent, "Waiting on CI for #12", "the words are unchanged");
  // render.ts hands in the user-todo row's exact pair (one code path): the compact path pass + the PR
  // pass on the line, the full path pass + the PR pass on the detail, the note's own session resolving
  assert.match(RENDER_FN, /line: \(n\) => \{ linkTodoLinePaths\(n, s\.id\); linkifyPrRefs\(n, prRepoFor\(s\.id\)\); \},/);
  assert.match(RENDER_FN, /detail: \(n\) => \{ linkTodoDetailPaths\(n, s\.id\); linkifyPrRefs\(n, prRepoFor\(s\.id\)\); \},/);
  // …and a path link in the strip opens through the body delegate, like one on the todo card
  assert.match(RENDER, /openpath: \(elx, ev\) => \{ if \(elx\.closest\("\.todo-card, #ut-reply-prompt, #pinned-notes"\)\)/);
});

test("every row has an Unpin control that is click-safe: declared by data-act, handled on the stable host, no per-render listener", () => {
  const rows = rowsOf(build(notes(2))!);
  for (const r of rows) {
    const b = r.all(".pn-unpin")[0];
    assert.equal(b.tagName, "BUTTON");
    assert.equal(b.attrs.type, "button");
    assert.equal(b.dataset.act, PINNED_ACT.unpin);
    assert.equal(b.dataset.nid, r.dataset.nid);
    assert.equal(b.dataset.sid, SID);
    assert.equal(b.textContent, PINNED_UNPIN_LABEL);
  }
  assert.doesNotMatch(MODULE.split("\n").filter((l) => !l.trim().startsWith("//")).join("\n"), /addEventListener|onclick/,
    "the builder hangs no listener (ui/CLAUDE.md)");
  // the delegate: installed ONCE on the host fetched by id, which survives every replaceChildren()
  assert.match(DELEGATE, /const host = document\.getElementById\("pinned-notes"\);\s*\n\s*if \(!host\) return;\s*\n\s*delegate\(host, \{/);
  assert.match(DELEGATE, /\[PINNED_ACT\.toggle\]: \(elx\) => \{/);
  assert.match(DELEGATE, /\[PINNED_ACT\.more\]: \(elx\) => \{/);
  assert.match(DELEGATE, /\[PINNED_ACT\.unpin\]: \(elx\) => \{/);
  // arm, then confirm; the confirm posts the op and removes the row at once (the acknowledgement)
  assert.match(DELEGATE, /elx\.classList\.add\("armed"\); elx\.textContent = PINNED_UNPIN_ARMED;/);
  assert.equal(PINNED_UNPIN_ARMED, "Unpin?");
  assert.match(DELEGATE, /vscodeApi\?\.postMessage\(\{ type: "unpinNote", id: sid, noteId: nid \}\)/);
  assert.match(DELEGATE, /item\?\.remove\(\);/);
  assert.match(DELEGATE, /pnPainted = "";/, "the next frame repaints the truth, whatever the kernel answered");
  // the op lands on the same store function as the postal tool's route: one code path
  assert.match(KERNEL, /"userTodoAnswer", "userTodoDismiss", "unpinNote", "commentMerge"\)/);
  assert.match(KERNEL, /elif t == "unpinNote" and msg\.get\("noteId"\):[\s\S]{0,600}_unpin_note\(sid, str\(msg\["noteId"\]\)\)/);
  assert.match(KERNEL, /if u\.path == "\/unpinnote":[\s\S]{0,3000}acct = _unpin_note\(sid, nid\)/);
});

test("the strip sits below the tab strip and above the transcript, on BOTH page skeletons, with its own styles", () => {
  for (const [name, src] of [["kernel", KERNEL], ["extension", SKELETON]] as const) {
    const tabs = src.indexOf('id="tabbar"'), strip = src.indexOf('id="pinned-notes"'), content = src.indexOf('id="content"');
    assert.ok(tabs > 0 && strip > 0 && content > 0, name + " skeleton carries all three");
    assert.ok(tabs < strip && strip < content, name + ": tab bar, then the strip, then the transcript");
  }
  assert.match(SKELETON, /<div id="pinned-notes" style="display:none"><\/div>/);
  assert.match(CSS, /#pinned-notes \{ flex: 0 0 auto;/);
  assert.match(CSS, /\.pn-detail \{ display: none;/);
  assert.match(CSS, /\.pn-detail\.open \{ display: block; \}/);
  assert.match(CSS, /\.pn-rest \{ display: none; \}/);
  assert.match(CSS, /\.pn-unpin\.armed \{/);
  // the sizes are the user-todo row's, no new font size on the surface (ui/CLAUDE.md)
  const block = CSS.slice(CSS.indexOf("#pinned-notes {"), CSS.indexOf(".pn-unpin.armed"));
  const sizes = new Set((block.match(/font-size: [0-9.]+em/g) || []).map((s) => s.slice(11)));
  for (const s of sizes) assert.ok(["0.86em", "0.72em"].includes(s), "an existing size: " + s);
});

test("the rows reach the strip through the chat frames the pane already reads, and the strip repaints only on new information", () => {
  // the session field, the upsert merge (an empty array is a real value) and the chatTail merge
  assert.match(RENDER, /userTodos\?: UserTodo\[\]; pinnedNotes\?: PinnedNote\[\];/);
  assert.match(RENDER, /pinnedNotes: \("pinnedNotes" in msg\) \? msg\.pinnedNotes : \(prev \? prev\.pinnedNotes : undefined\)/);
  const tail = RENDER.slice(RENDER.indexOf("function chatTail"));
  assert.match(tail, /if \("pinnedNotes" in msg\) s\.pinnedNotes = msg\.pinnedNotes;/);
  assert.match(tail.slice(0, tail.indexOf("function ", 10)), /renderPinnedNotes\(\);/, "the strip rides the tail frame that carries the field");
  // the kernel: build_session's field from the store, the tail frame beside userTodos, the sig fold
  assert.match(KERNEL, /"pinnedNotes": _pinned_notes_for\(sid\),/);
  assert.match(KERNEL, /"pinnedNotes": m\.get\("pinnedNotes"\) or \[\]/);
  assert.match(KERNEL, /sig\.append\(_pinned_notes_fp\(sess\.get\("sid"\) or ""\)\)/);
  // showActive swaps it in with the other boxes; update() repaints the active session's
  assert.match(RENDER, /renderLedger\(\);  \/\/ swap in the active session's digest box \(or hide if none\)\s*\n\s*renderPinnedNotes\(\);/);
  // the gate: same rows, same key, no repaint; a pin, an unpin or a tab switch changes the key
  const rows = notes(2);
  assert.equal(pinnedNotesKey(SID, rows), pinnedNotesKey(SID, rows.map((n) => ({ ...n }))));
  assert.notEqual(pinnedNotesKey(SID, rows), pinnedNotesKey(SID, rows.slice(1)));
  assert.notEqual(pinnedNotesKey(SID, rows), pinnedNotesKey(SID, [...rows, note(2)]));
  assert.notEqual(pinnedNotesKey(SID, rows), pinnedNotesKey("22222222-3333-4444-5555-666666666666", rows));
  assert.equal(pinnedNotesKey(SID, undefined), pinnedNotesKey(SID, []));
  assert.match(RENDER_FN, /const key = pinnedNotesKey\(s \? s\.id : "", notes\);\s*\n\s*if \(!force && key === pnPainted\) return;/);
  assert.doesNotMatch(RENDER_FN, /setTimeout|setInterval|Date\.now/, "events, not timers");
});
