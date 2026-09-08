// Pinned notes (the user 2026-09-08): a session pins short notes above its own transcript for the
// person it works for; the strip between the tab bar and the transcript shows them. The strip's
// builder (pinned-notes.ts) is EXECUTED here against a small DOM stand-in (the pr-links.test.ts
// convention): order, the three-row fold, the detail fold (with a cut line's full text, the cut MEASURED
// on the painted row through stand-in widths, never counted), the linkers, the escaping and the unpin
// control, plus the armed Unpin's event-driven disarm (armUnpin) and the unpin latch (latchedNotes)
// against stand-ins; the wiring into render.ts, the two page skeletons, the kernel's frames and the
// styles are pinned at the source, the way the other webview tests pin the chat renderer. The strip's
// height cap, the one-line rows and the real cut on a phone's width are measured in a real browser by
// pinned-notes-browser.test.ts; here the sheet's rules are pinned as text.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { buildPinnedNotes, pinnedNotesKey, pinnedMoreLabel, pinnedSplit, pinnedMeasureCut, pinnedRowOverflows, pinnedHasFold,
  armUnpin, latchUnpinAt, latchedNotes,
  PINNED_VISIBLE, PINNED_ACT, PINNED_UNPIN_LABEL, PINNED_UNPIN_ARMED, PINNED_CUT_CLASS, PINNED_BREAK_CLASS, PINNED_DETAIL_CLASS, PINNED_FOLD_CLASSES,
  type PinnedNote, type PinnedFoldState, type PinnedLinkers, type UnpinLatch, type PinnedStripRoot } from "./pinned-notes";
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
  scrollWidth = 0; clientWidth = 0;   // the measured widths (a test sets them to stand for a layout)
  style: Record<string, string> = {};
  dataset: Record<string, string | undefined> = {};
  attrs: Record<string, string> = {};
  listeners: Record<string, Array<(ev: any) => void>> = {};
  constructor(public tagName: string) {}
  addEventListener(type: string, fn: (ev: any) => void): void { (this.listeners[type] ||= []).push(fn); }
  removeEventListener(type: string, fn: (ev: any) => void): void { this.listeners[type] = (this.listeners[type] || []).filter((f) => f !== fn); }
  fire(type: string, ev: any = {}): void { for (const f of [...(this.listeners[type] || [])]) f(ev); }
  listening(): string[] { return Object.keys(this.listeners).filter((k) => this.listeners[k].length).sort(); }
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
  querySelectorAll(sel: string): E[] { return this.all(sel); }
  querySelector(sel: string): E | null { return this.all(sel)[0] || null; }
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
const measure = (strip: E) => pinnedMeasureCut(strip as unknown as PinnedStripRoot);   // the stand-in's widths stand for a layout
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

test("the detail folds behind a click on the row or its hint BUTTON (the keyboard's way in), with the user-todo row's words; a bare row offers neither", () => {
  const strip = build([note(0, { detail: "The api tests flake on the auth step" }), note(1)])!;
  const [withDetail, bare] = rowsOf(strip);
  assert.equal(PINNED_DETAIL_CLASS, "pn-with-detail");
  assert.ok(withDetail.classList.contains(PINNED_DETAIL_CLASS), "the row wears the class the sheet keys the offer on");
  assert.ok(pinnedHasFold(withDetail));
  const t = textOf(withDetail);
  assert.equal(t.dataset.act, PINNED_ACT.toggle);
  assert.equal(t.dataset.nid, "pn-00000000");
  assert.equal(t.title, "note 0", "the text's title is the text itself, whole");
  assert.equal(t.all(".ut-more").length, 0, "the hint is not inside the text: a long line's ellipsis must not swallow it");
  const more = withDetail.all(".ut-more")[0];
  assert.equal(more.tagName, "BUTTON", "a real button: Enter and Space are its own click, and Tab reaches it");
  assert.equal(more.attrs.type, "button");
  assert.equal(more.dataset.act, PINNED_ACT.toggle);
  assert.equal(more.dataset.nid, "pn-00000000");
  assert.equal(more.attrs["aria-expanded"], "false");
  assert.equal(more.textContent, "▸ details", "the same hint vocabulary as a user-todo row");
  assert.deepEqual(withDetail.all(".pn-line")[0].elements().map((e) => e.className.split(" ")[0]), ["pn-text", "ut-more", "pn-unpin"], "text, hint, Unpin, in the line");
  const d = withDetail.all(".pn-detail")[0];
  assert.equal(d.all(".pn-more")[0].textContent, "The api tests flake on the auth step");
  assert.equal(d.all(".pn-full")[0].textContent, "note 0", "the fold carries the full text too, shown only when the row is cut");
  assert.ok(!d.classList.contains("open"), "folded by default: the one-line version first");
  // a bare row: built with the same hint and fold (so a later measure can offer them without a rebuild),
  // wearing none of the fold classes, so the sheet hides both and the text is no click target
  assert.equal(textOf(bare).dataset.act, undefined, "a bare row has no click target for a fold");
  assert.ok(!pinnedHasFold(bare));
  assert.deepEqual(PINNED_FOLD_CLASSES, ["pn-over", "pn-break", "pn-with-detail"]);
  for (const c of PINNED_FOLD_CLASSES) assert.ok(!bare.classList.contains(c), "bare: no " + c);
  assert.equal(bare.all(".ut-more").length, 1);
  assert.equal(bare.all(".pn-detail").length, 1);
  assert.equal(bare.all(".pn-more").length, 0, "no detail, no detail node");
  assert.match(CSS, /\.pn-line \.ut-more \{ display: none;/, "the hint is hidden (and out of the tab order) unless the row offers a fold");
  assert.match(CSS, /\.pn-over \.ut-more, \.pn-break \.ut-more, \.pn-with-detail \.ut-more \{ display: inline-block; \}/);
  assert.match(CSS, /\.pn-over \.pn-detail\.open, \.pn-break \.pn-detail\.open, \.pn-with-detail \.pn-detail\.open \{ display: block; \}/);
  assert.match(CSS, /\.pn-full \{ display: none; \}\n\.pn-over \.pn-full, \.pn-break \.pn-full \{ display: block; \}/, "the full text shows in the fold of a cut row only");
  // open state survives a rebuild through the keyed set
  const st = state(); st.openDetails.add("pn-00000000");
  const again = rowsOf(build([note(0, { detail: "more" })], st)!)[0];
  assert.ok(again.all(".pn-detail")[0].classList.contains("open"));
  assert.equal(again.all(".ut-more")[0].textContent, "▾ details");
  assert.equal(again.all(".ut-more")[0].attrs["aria-expanded"], "true");
  // the delegate finds the row from either target and flips the hint's state with the fold
  assert.match(DELEGATE, /const item = elx\.closest\("\.pn-item"\);\s*\n\s*item\?\.querySelector\("\.pn-detail"\)\?\.classList\.toggle\("open", open\);/);
  assert.match(DELEGATE, /more\.setAttribute\("aria-expanded", open \? "true" : "false"\)/);
});

test("a row is one line: a text the layout cuts is carried in full inside the fold and as the title; the cut is MEASURED after paint, never counted", () => {
  const long = "The staging deploy is blocked on the schema migration: run docs/migrate.md step 3 first, then re-run the api suite";
  const strip = build([note(0, { text: long }), note(1, { text: "two\nlines" }), note(2)])!;
  const [cut, broken, fits] = rowsOf(strip);
  assert.equal(textOf(cut).textContent, long, "the line carries the text; the sheet cuts it, not the builder");
  assert.equal(textOf(cut).title, long, "the whole text on hover, on every row");
  assert.equal(textOf(fits).title, "note 2");
  assert.match(CSS, /\.pn-text \{ flex: 1 1 auto; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; \}/, "one line, cut with an ellipsis");
  // built: nothing is cut yet (no layout has happened), except the line break the builder does know
  assert.equal(PINNED_CUT_CLASS, "pn-over");
  assert.equal(PINNED_BREAK_CLASS, "pn-break");
  assert.ok(!cut.classList.contains(PINNED_CUT_CLASS));
  assert.equal(textOf(cut).dataset.act, undefined, "no fold offered before the measure");
  assert.ok(broken.classList.contains(PINNED_BREAK_CLASS), "a line break the one-line row shows as a space: a cut the builder knows");
  assert.equal(textOf(broken).dataset.act, PINNED_ACT.toggle);
  assert.equal(broken.all(".pn-full")[0].textContent, "two\nlines");
  // measured: the layout says the first row overflows (stand-in widths), the others fit
  assert.equal(pinnedRowOverflows({ scrollWidth: 318, clientWidth: 302 }), true);
  assert.equal(pinnedRowOverflows({ scrollWidth: 302, clientWidth: 302 }), false);
  textOf(cut).scrollWidth = 318; textOf(cut).clientWidth = 302;
  textOf(broken).scrollWidth = 60; textOf(broken).clientWidth = 302;
  textOf(fits).scrollWidth = 40; textOf(fits).clientWidth = 302;
  assert.equal(measure(strip), 1, "one row changed");
  assert.ok(cut.classList.contains(PINNED_CUT_CLASS));
  assert.ok(pinnedHasFold(cut));
  assert.equal(textOf(cut).dataset.act, PINNED_ACT.toggle, "so the row folds open");
  assert.equal(cut.all(".pn-full")[0].textContent, long, "the fold carries the full text");
  assert.ok(!fits.classList.contains(PINNED_CUT_CLASS));
  assert.equal(textOf(fits).dataset.act, undefined);
  assert.equal(measure(strip), 0, "idempotent: the same layout changes nothing");
  // the pane widens: the row fits, the offer is withdrawn (the hint and the fold hide, the text is no target)
  textOf(cut).scrollWidth = 302;
  assert.equal(measure(strip), 1);
  assert.ok(!cut.classList.contains(PINNED_CUT_CLASS));
  assert.equal(textOf(cut).dataset.act, undefined);
  assert.ok(broken.classList.contains(PINNED_BREAK_CLASS), "the measure never takes the builder's break away");
  // no character count anywhere in the module: the cut is a layout fact (review round 2, 2026-09-08)
  const code = MODULE.split("\n").filter((l) => !l.trim().startsWith("//") && !l.trim().startsWith("*")).join("\n");
  assert.doesNotMatch(code, /PINNED_LINE_CHARS|text\.length|textContent\.length/, "no count of the text decides the fold");
  // render.ts measures at every paint that shows rows, and watches the strip's width (once), no timer
  assert.match(RENDER_FN, /host\.style\.display = strip \? "" : "none";\s*\n\s*if \(strip\) \{[\s\S]*?pinnedMeasureCut\(host\);\s*\n\s*pinnedWatchWidth\(host\);\s*\n\s*\}/);
  assert.match(MODULE, /new ResizeObserver\(\(\) => \{ pinnedMeasureCut\(host\); \}\)\.observe\(host\)/);
  assert.doesNotMatch(code, /setTimeout|setInterval|requestAnimationFrame/, "events, not timers");
});

test("paths and PR references link through the caller's linkers: the line pass on every row, the detail pass on every row's fold", () => {
  const sp = spies();
  const strip = build([note(0, { detail: "see docs/plan.md" }), note(1)], state(), sp.link)!;
  assert.deepEqual(sp.line.map((n) => n.classList.contains("pn-text")), [true, true], "the one-line text of every row");
  assert.deepEqual(sp.line.map((n) => n.childNodes[0].textContent), ["note 0", "note 1"], "the text is in place when the linker runs");
  assert.deepEqual(sp.detail.map((n) => n.classList.contains("pn-detail")), [true, true], "the fold of every row: its full text, and the detail when there is one");
  assert.deepEqual(sp.detail.map((n) => n.all(".pn-more").length), [1, 0]);
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
  const builder = MODULE.slice(0, MODULE.indexOf("// ── the armed Unpin"));
  assert.ok(builder.includes("export function buildPinnedNotes"), "the builder is the module's first part");
  assert.doesNotMatch(builder.split("\n").filter((l) => !l.trim().startsWith("//")).join("\n"), /addEventListener|onclick/,
    "the builder hangs no listener (ui/CLAUDE.md); armUnpin's are hung on a gesture and taken down by the disarm");
  // the delegate: installed ONCE on the host fetched by id, which survives every replaceChildren()
  assert.match(DELEGATE, /const host = document\.getElementById\("pinned-notes"\);\s*\n\s*if \(!host\) return;\s*\n\s*delegate\(host, \{/);
  assert.match(DELEGATE, /\[PINNED_ACT\.toggle\]: \(elx\) => \{/);
  assert.match(DELEGATE, /\[PINNED_ACT\.more\]: \(elx\) => \{/);
  assert.match(DELEGATE, /\[PINNED_ACT\.unpin\]: \(elx\) => \{/);
  // arm through armUnpin (one armed control at a time), then confirm: the confirm retires the arm, posts
  // the op, latches the removal and repaints from the latched list (no direct DOM surgery, no cleared key)
  assert.match(DELEGATE, /pnDisarm\(\);\s*\/\/ one armed control at a time\s*\n\s*pnArmed = armUnpin\(elx, document, isCoarsePointer\(\)\);\s*\n\s*return;/);
  assert.equal(PINNED_UNPIN_ARMED, "Unpin?");
  assert.match(DELEGATE, /pnDisarm\(\);\s*\n\s*vscodeApi\?\.postMessage\(\{ type: "unpinNote", id: sid, noteId: nid \}\)/);
  assert.match(DELEGATE, /if \(s\) pnLatch = latchUnpinAt\(pnLatch, sid, s\.pinnedNotes \|\| \[\], nid\);/,
    "armed against the list as the last frame carried it, never a filtered copy: a second unpin in the same cycle extends the latch");
  assert.doesNotMatch(DELEGATE, /s\.pinnedNotes = /, "the session's list is the kernel's; the latch filters it at every paint");
  assert.match(DELEGATE, /renderPinnedNotes\(true\);\s*\n\s*\},\s*\n\s*\}\);/, "the confirm ends in a forced repaint under the latch");
  assert.doesNotMatch(DELEGATE, /pnPainted = ""|item\?\.remove\(\)|setTimeout/, "no cleared key, no optimistic DOM removal, no timer");
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
  assert.match(CSS, /\.pn-with-detail \.pn-detail\.open \{ display: block; \}/);
  assert.match(CSS, /\.pn-rest \{ display: none; \}/);
  assert.match(CSS, /\.pn-unpin\.armed \{/);
  // the sizes are the user-todo row's, no new font size on the surface (ui/CLAUDE.md)
  const block = CSS.slice(CSS.indexOf("#pinned-notes {"), CSS.indexOf(".pn-unpin.armed"));
  const sizes = new Set((block.match(/font-size: [0-9.]+em/g) || []).map((s) => s.slice(11)));
  for (const s of sizes) assert.ok(["0.86em", "0.72em"].includes(s), "an existing size: " + s);
  // the cap (review round 1, 2026-09-08): a few rows, then the strip scrolls, so #content and the
  // composer keep their room whatever a session pins; measured in pinned-notes-browser.test.ts
  const host = block.slice(0, block.indexOf("}"));
  assert.match(host, /max-height: min\(11em, 30vh\); overflow-y: auto; overflow-x: hidden; overscroll-behavior: contain;/);
});

test("the row mark is a neutral pin mark, not the flag every other surface reserves for 'waiting on you'", () => {
  const block = CSS.slice(CSS.indexOf("#pinned-notes {"), CSS.indexOf(".pn-unpin.armed"));
  const m = /\.pn-line::before \{ content: "\\([0-9A-Fa-f]{4})";/.exec(block);
  assert.ok(m, "the mark is a CSS escape on .pn-line::before");
  const mark = String.fromCodePoint(parseInt(m![1], 16));
  assert.equal(mark, "\u25AA", "a small square in the dim chrome color");
  const flag = "\u2691";
  assert.notEqual(mark, flag);
  assert.doesNotMatch(block, /2691/, "no flag anywhere in the strip's rules");
  // the flag IS the user-todo mark elsewhere (the tab glyph, the feed's label), which is why the strip must not wear it
  assert.ok(RENDER.includes(flag), "the flag glyph is in use for the user-todo tab mark");
  assert.match(RENDER, /waiting on you/);
});

test("armUnpin: the arm ends on an event (a press elsewhere, a blur, the pointer leaving), never a timer; a press on the control keeps it", () => {
  const docStandIn = () => {
    const l: Record<string, Array<(ev: any) => void>> = {};
    return {
      addEventListener: (t: string, fn: (ev: any) => void) => { (l[t] ||= []).push(fn); },
      removeEventListener: (t: string, fn: (ev: any) => void) => { l[t] = (l[t] || []).filter((f) => f !== fn); },
      fire: (t: string, ev: any) => { for (const f of [...(l[t] || [])]) f(ev); },
      listening: () => Object.keys(l).filter((k) => l[k].length).sort(),
    };
  };
  const btn = () => { const b = new E("BUTTON"); b.textContent = PINNED_UNPIN_LABEL; return b; };
  // coarse pointer (a phone): the next press anywhere else disarms and takes every listener down
  let d = docStandIn(); let b = btn();
  let disarm = armUnpin(b as unknown as HTMLElement, d, true);
  assert.ok(b.classList.contains("armed")); assert.equal(b.textContent, PINNED_UNPIN_ARMED);
  assert.deepEqual(d.listening(), ["pointerdown"]);
  assert.deepEqual(b.listening(), ["blur"], "no pointerleave on a coarse pointer: there is no hover to leave");
  d.fire("pointerdown", { target: b });                      // the confirming tap (or a scroll that started on the button)
  assert.ok(b.classList.contains("armed"), "a press ON the control keeps the arm");
  d.fire("pointerdown", { target: new E("DIV") });           // a tap on the transcript
  assert.ok(!b.classList.contains("armed")); assert.equal(b.textContent, PINNED_UNPIN_LABEL);
  assert.deepEqual(d.listening(), []); assert.deepEqual(b.listening(), [], "nothing lingers on the document or the control");
  disarm();                                                  // idempotent
  assert.equal(b.textContent, PINNED_UNPIN_LABEL);
  // fine pointer: the pointer leaving disarms too
  d = docStandIn(); b = btn();
  disarm = armUnpin(b as unknown as HTMLElement, d, false);
  assert.deepEqual(b.listening(), ["blur", "pointerleave"]);
  b.fire("pointerleave", {});
  assert.ok(!b.classList.contains("armed")); assert.deepEqual(d.listening(), []); assert.deepEqual(b.listening(), []);
  // keyboard: Enter armed it and Tab moved on (blur)
  d = docStandIn(); b = btn();
  disarm = armUnpin(b as unknown as HTMLElement, d, false);
  b.fire("blur", {});
  assert.ok(!b.classList.contains("armed")); assert.deepEqual(d.listening(), []);
  // the caller's disarm (a repaint drops the row) takes the listeners down as well
  d = docStandIn(); b = btn();
  disarm = armUnpin(b as unknown as HTMLElement, d, true);
  disarm();
  assert.deepEqual(d.listening(), []); assert.deepEqual(b.listening(), []); assert.equal(b.textContent, PINNED_UNPIN_LABEL);
  assert.doesNotMatch(MODULE, /setTimeout|setInterval|Date\.now/, "events, not timers");
  // render.ts disarms before every repaint, and the arm is the module's, not a hand-rolled one
  assert.match(RENDER_FN, /pnDisarm\(\);\s*\/\/ the armed row, if any, is about to be replaced[^\n]*\n\s*const strip = /);
  assert.match(RENDER, /function pnDisarm\(\): void \{ const f = pnArmed; pnArmed = null; if \(f\) f\(\); \}/);
});

test("the unpin latch: a frame still carrying the pre-unpin list is old news; any other list for the session is new information", () => {
  const rows = notes(3);
  const other = "22222222-3333-4444-5555-666666666666";
  const latch: UnpinLatch = latchUnpinAt(null, SID, rows, "pn-00000001");
  assert.deepEqual(latch, { sid: SID, key: pinnedNotesKey(SID, rows), nids: ["pn-00000001"] });
  // the same list again (a cycle already in flight when the confirm landed): the row stays gone, the latch holds
  let r = latchedNotes(latch, SID, rows.map((n) => ({ ...n })));
  assert.deepEqual(r.notes.map((n) => n.id), ["pn-00000000", "pn-00000002"]);
  assert.equal(r.latch, latch);
  // the kernel's list after the unpin: new information, the latch has served
  r = latchedNotes(latch, SID, [rows[0], rows[2]]);
  assert.deepEqual(r.notes.map((n) => n.id), ["pn-00000000", "pn-00000002"]);
  assert.equal(r.latch, null);
  // a new pin arriving before the unpin landed is new information too (the strip shows what the kernel says)
  r = latchedNotes(latch, SID, [...rows, note(3)]);
  assert.equal(r.notes.length, 4); assert.equal(r.latch, null);
  // another session's frame says nothing about this one
  r = latchedNotes(latch, other, rows);
  assert.equal(r.notes.length, 3); assert.equal(r.latch, latch);
  // a second unpin against the same stale list extends the latch rather than forgetting the first
  const two = latchUnpinAt(latch, SID, rows, "pn-00000002");
  assert.deepEqual(two.nids, ["pn-00000001", "pn-00000002"]);
  assert.deepEqual(latchedNotes(two, SID, rows).notes.map((n) => n.id), ["pn-00000000"]);
  // against a different list it starts over
  assert.deepEqual(latchUnpinAt(latch, SID, [rows[0]], "pn-00000000").nids, ["pn-00000000"]);
  assert.deepEqual(latchedNotes(null, SID, rows), { notes: rows, latch: null });
  // render.ts reads the frame's list through the latch, and computes the repaint key from what it shows
  assert.match(RENDER_FN, /const seen = latchedNotes\(pnLatch, s \? s\.id : "", s && !s\.sub \? \(s\.pinnedNotes \|\| \[\]\) : \[\]\);/);
  assert.match(RENDER_FN, /pnLatch = seen\.latch;\s*\n\s*const notes = seen\.notes;\s*\n\s*const key = pinnedNotesKey\(s \? s\.id : "", notes\);/);
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
  // showActive swaps it in with the other boxes; update() repaints the active session's; upsert() too
  // (a full frame on an existing tab, for a client that fell behind the tail)
  assert.match(RENDER, /renderLedger\(\);  \/\/ swap in the active session's digest box \(or hide if none\)\s*\n\s*renderPinnedNotes\(\);/);
  const upsert = RENDER.slice(RENDER.indexOf("function upsert(msg: any"), RENDER.indexOf("function update(msg: any)"));
  assert.match(upsert, /renderBgTasks\(\);\s*\n\s*renderPinnedNotes\(\);\s*\/\/ a full frame on an existing tab/);
  const update = RENDER.slice(RENDER.indexOf("function update(msg: any)"), RENDER.indexOf("function ", RENDER.indexOf("function update(msg: any)") + 10));
  assert.match(update, /if \(msg\.id === activeId\) \{\s*\n\s*appendActive\(\);\s*\n\s*renderLedger\(\);[^\n]*\n\s*renderPinnedNotes\(\);/);
  // the chatTail merge: the pinnedNotes line sits ABOVE the userTodos comment block, so that comment
  // stays with the userTodos line it explains (and tab-group-flags.test.ts's window after that line holds)
  assert.match(tail, /if \("pinnedNotes" in msg\) s\.pinnedNotes = msg\.pinnedNotes;[^\n]*\n\s*\/\/ the top-level userTodos seam rides every delta[\s\S]{0,400}?reads this field, not the event\n\s*if \("userTodos" in msg\) s\.userTodos = msg\.userTodos;/);
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
