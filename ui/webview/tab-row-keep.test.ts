// The inline tab strip's row pass EXECUTED (the strip-inline follow-ups, 2026-09-09): paintTabRowLines and
// ensureTabRowObserver lifted from render.ts (esbuild at run time, tab-strip-skip-exec.test.ts's pattern) and driven
// over a fake #tabs whose layout is a flex-wrap model, the way dragslot.test.ts models rows: every item has a width,
// the bar a width and one row height; an item that does not fit opens the next row; a .tab-group-break is a
// zero-height line of its own, so the item after it starts a row at the same y. Two rules ride the painter, keyed on
// the three events that run it (a strip rebuild, the strip's width observer, the document's fonts finishing a load):
//  - a group keeps with its first tab: a header, or the untagged trail's divider, whose first tab wrapped to the
//    next row gets a break ahead of it, so a group never opens at a row's end with its tabs below; not while a tab
//    is dragged (the breaks are the drag's row openers), and not for a pair no row can hold;
//  - the divider is a row member for the hairlines, like a tab (the pre-T264 rule, back).
// The observer watches a zero-height width sentinel, not #tabs, so its own row changes never re-trigger it.
// tab-row-keep-browser.test.ts runs the same code in Chromium. Synthetic ids only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "styles.css"), "utf8");

const ROW_H = 31;

/** A strip item: a class list, a width, and the layout the bar computes for it. */
class Item {
  cls: string; w: number; parent: Bar | null = null;
  dataset: Record<string, string> = {}; style: Record<string, string> = {}; attrs: Record<string, string> = {};
  title = "";
  classList: { contains: (c: string) => boolean; add: (...c: string[]) => void };
  constructor(cls: string, w: number) {
    this.cls = cls; this.w = w;
    const self = this;
    this.classList = {
      contains: (c) => self.cls.split(/\s+/).includes(c),
      add: (...c) => { for (const x of c) if (!self.classList.contains(x)) self.cls = (self.cls + " " + x).trim(); },
    };
  }
  get isBreak(): boolean { return this.classList.contains("tab-group-break"); }
  get isLine(): boolean { return this.classList.contains("tab-row-line"); }
  get isSentinel(): boolean { return this.classList.contains("tab-row-sentinel"); }
  get isConnected(): boolean { return this.parent !== null; }
  private box() { return this.parent!.layout().get(this)!; }
  get offsetTop(): number { return this.box().top; }
  get offsetLeft(): number { return this.box().left; }
  get offsetHeight(): number { return this.box().h; }
  get previousElementSibling(): Item | null { const k = this.parent!.children; return k[k.indexOf(this) - 1] ?? null; }
  get nextElementSibling(): Item | null { const k = this.parent!.children; return k[k.indexOf(this) + 1] ?? null; }
  setAttribute(k: string, v: string): void { this.attrs[k] = v; }
  remove(): void { if (this.parent) { this.parent.children = this.parent.children.filter((c) => c !== this); this.parent.dirty(); this.parent = null; } }
}

/** #tabs: children in DOM order, a width, and a flex-wrap layout recomputed lazily after every mutation. */
class Bar {
  children: Item[] = []; width: number;
  paints = 0;   // the painter's first read is its sweep of the old lines: one per paint
  private boxes: Map<Item, { top: number; left: number; h: number }> | null = null;
  constructor(width: number) { this.width = width; }
  dirty(): void { this.boxes = null; }
  resize(width: number): void { this.width = width; this.dirty(); }
  appendChild(c: Item): Item { c.parent = this; this.children.push(c); this.dirty(); return c; }
  insertBefore(c: Item, ref: Item | null): Item {
    c.parent = this;
    const i = ref ? this.children.indexOf(ref) : -1;
    if (i < 0) this.children.push(c); else this.children.splice(i, 0, c);
    this.dirty();
    return c;
  }
  /** the rebuild's replaceChildren: every child out, the sentinel with them */
  replaceChildren(): void { for (const c of this.children) c.parent = null; this.children = []; this.dirty(); }
  querySelectorAll(sel: string): Item[] {
    const m = sel.match(/^:scope > \.([\w-]+)$/);
    assert.ok(m, "the painter selects its own children by one class: " + sel);
    if (m![1] === "tab-row-line") this.paints++;
    return this.children.filter((c) => c.classList.contains(m![1]));
  }
  layout(): Map<Item, { top: number; left: number; h: number }> {
    if (this.boxes) return this.boxes;
    const out = new Map<Item, { top: number; left: number; h: number }>();
    let x = 0, top = 0, open = false;   // open: the current row holds an item
    for (const c of this.children) {
      if (c.isLine) { out.set(c, { top: parseFloat(c.style.top || "0"), left: -8, h: 1 }); continue; }   // absolute: out of flow
      if (c.isSentinel) { out.set(c, { top: 0, left: 0, h: 0 }); continue; }   // absolute, zero-height: out of flow, as wide as the bar
      if (c.isBreak) {   // flex: 0 0 100%: a line of its own, zero tall; whatever follows starts a row at the same y
        if (open) { top += ROW_H; x = 0; open = false; }
        out.set(c, { top, left: 0, h: 0 });
        continue;
      }
      if (open && x + c.w > this.width) { top += ROW_H; x = 0; }
      out.set(c, { top, left: x, h: ROW_H });   // align-items: stretch: every item is as tall as its row
      x += c.w; open = true;
    }
    this.boxes = out;
    return out;
  }
  /** The strip as rows of class-or-id labels, the way a reader sees it. */
  rows(): string[][] {
    const by = new Map<number, string[]>();
    for (const c of this.children) {
      if (c.isLine || c.isBreak || c.isSentinel) continue;
      const label = c.dataset.id || c.dataset.group || c.cls;
      (by.get(c.offsetTop) ?? by.set(c.offsetTop, []).get(c.offsetTop)!).push(label);
    }
    return [...by.entries()].sort((a, b) => a[0] - b[0]).map(([, v]) => v);
  }
  lines(): number[] { return this.children.filter((c) => c.isLine).map((c) => parseFloat(c.style.top)); }
  keeps(): Item[] { return this.children.filter((c) => c.classList.contains("tab-keep-break")); }
}

const tab = (id: string, w = 100) => { const t = new Item("tab", w); t.dataset.id = id; return t; };
const head = (group: string, w = 60) => { const h = new Item("tab-group-head", w); h.dataset.group = group; return h; };
const sep = () => new Item("tab-group-sep", 13);
const add = () => new Item("tab tab-add", 30);

/** The page's ResizeObserver, recorded: which targets, and a way to deliver its event. */
class FakeRO {
  static made: FakeRO[] = [];
  targets: Item[] = [];
  constructor(public cb: () => void) { FakeRO.made.push(this); }
  observe(t: Item): void { this.targets.push(t); }
  fire(): void { this.cb(); }
}
/** document.fonts, controllable: listeners by type, a dispatch, and a ready promise the test resolves. */
class FakeFonts {
  listeners: Record<string, Array<() => void>> = {};
  resolveReady!: () => void;
  ready: Promise<void> = new Promise((r) => { this.resolveReady = r; });
  addEventListener(type: string, fn: () => void): void { (this.listeners[type] ??= []).push(fn); }
  dispatch(type: string): void { for (const fn of this.listeners[type] ?? []) fn(); }
}

type Api = {
  paintTabRowLines: (bar: Bar) => void;
  ensureTabRowObserver: (bar: Bar) => void;
  drag: (id: string | null) => void;
  observer: () => FakeRO | null;
  sentinel: () => Item | null;
};

/** makeRowBreak, paintTabRowLines, keepGroupsWithTabs and ensureTabRowObserver, transpiled, over the fakes. The
 *  strip's drag state (draggedId, a render.ts module variable the painter reads) is declared in the prelude and
 *  set through `drag`. */
function lift(fonts: FakeFonts | null = new FakeFonts()): Api & { fonts: FakeFonts | null } {
  const a = RENDER.indexOf("function makeRowBreak("), b = RENDER.indexOf("function makeTrailSep(");
  const c = RENDER.indexOf("function paintTabRowLines("), d = RENDER.indexOf("function tabEmojiNode(");
  assert.ok(a > 0 && b > a && c > b && d > c, "anchors not found: makeRowBreak, makeTrailSep, paintTabRowLines or tabEmojiNode moved; re-anchor");
  const js = requireCjs("esbuild").transformSync(RENDER.slice(a, b) + RENDER.slice(c, d), { loader: "ts" }).code;
  const prelude = `const el = (tag, cls) => new ITEM(cls || "", 0);\nlet draggedId = null;\n`;
  const document = fonts ? { fonts } : {};
  const api = new Function("ITEM", "ResizeObserver", "document", prelude + js +
    "\nreturn { paintTabRowLines, ensureTabRowObserver, drag: (id) => { draggedId = id; }, observer: () => tabRowObserver, sentinel: () => tabRowSentinel };")
    (Item, FakeRO, document) as Api;
  return { ...api, fonts };
}

/** A bar with the given children, painted once. */
function strip(width: number, ...items: Item[]): Bar {
  const bar = new Bar(width);
  for (const it of items) bar.appendChild(it);
  return bar;
}

test("a header whose first tab wrapped gets a break ahead of it: the group opens the next row with its tabs", () => {
  const { paintTabRowLines } = lift();
  // 300 wide: web's header + two tabs fill 240; api's header (60) fits at the end of row 0 and its first tab does not
  const api = head("api"), b1 = tab("b1"), b2 = tab("b2");
  const bar = strip(300, head("web"), tab("a1"), tab("a2", 80), api, b1, b2, add());
  assert.deepEqual(bar.rows(), [["web", "a1", "a2", "api"], ["b1", "b2", "tab tab-add"]], "the premise: the header sits at row 0's end, its tabs on row 1");
  paintTabRowLines(bar);
  assert.equal(api.offsetTop, b1.offsetTop, "the header shares its first tab's row");
  assert.deepEqual(bar.rows(), [["web", "a1", "a2"], ["api", "b1", "b2", "tab tab-add"]]);
  const brk = api.previousElementSibling!;
  assert.ok(brk.classList.contains("tab-group-break") && brk.classList.contains("tab-keep-break"), "a row break the painter owns stands ahead of the header: " + brk.cls);
  assert.ok(!brk.classList.contains("tab-group-sep"), "not the untagged boundary: sectionHeadOf walks past it");
  assert.equal(brk.attrs["aria-hidden"], "true", "layout only");
  assert.deepEqual(bar.lines(), [ROW_H], "one hairline, under row 0: the lines are painted AFTER the break moved the rows");
});

test("the untagged trail's divider keeps with the trail's first tab the same way, and stays the boundary itself", () => {
  const { paintTabRowLines } = lift();
  // 260 wide: web's header + two tabs fill 240; the 13px divider fits at the end of row 0, the trail's tab does not
  const sp = sep(), t1 = tab("t1");
  const bar = strip(260, head("web"), tab("a1"), tab("a2", 80), sp, t1, add());
  assert.deepEqual(bar.rows(), [["web", "a1", "a2", "tab-group-sep"], ["t1", "tab tab-add"]], "the premise");
  paintTabRowLines(bar);
  assert.equal(sp.offsetTop, t1.offsetTop, "the divider opens the trail's row");
  assert.deepEqual(bar.rows(), [["web", "a1", "a2"], ["tab-group-sep", "t1", "tab tab-add"]]);
  assert.equal(bar.keeps().length, 1);
  assert.equal(sp.previousElementSibling, bar.keeps()[0], "the break stands ahead of the divider");
  assert.ok(!bar.keeps()[0].classList.contains("tab-group-sep"), "the divider, not the break, is the boundary sectionHeadOf reads");
});

test("the pass re-runs cleanly on the observer's event: idempotent at one width, and a widened strip takes the break back out", () => {
  const { paintTabRowLines } = lift();
  const api = head("api"), b1 = tab("b1");
  const bar = strip(300, head("web"), tab("a1"), tab("a2", 80), api, b1, tab("b2"), add());
  paintTabRowLines(bar);
  paintTabRowLines(bar);
  assert.equal(bar.keeps().length, 1, "a repaint at the same width leaves exactly one break, not two");
  assert.deepEqual(bar.rows(), [["web", "a1", "a2"], ["api", "b1", "b2", "tab tab-add"]]);
  assert.deepEqual(bar.lines(), [ROW_H]);
  // the ResizeObserver's case: the pane widened, the header and its tab fit on row 0 again
  bar.resize(400);
  paintTabRowLines(bar);
  assert.equal(bar.keeps().length, 0, "no stale break: the header fits with its tab, so it stays inline");
  assert.deepEqual(bar.rows(), [["web", "a1", "a2", "api", "b1"], ["b2", "tab tab-add"]]);
  assert.equal(api.offsetTop, b1.offsetTop);
  // narrowed again: the break is back, once
  bar.resize(300);
  paintTabRowLines(bar);
  assert.equal(bar.keeps().length, 1);
  assert.equal(api.offsetTop, b1.offsetTop);
});

test("a break moves the rows below it, so a later header is judged against the moved layout, never a stale read", () => {
  const { paintTabRowLines } = lift();
  // 300 wide, without breaks: row 0 = web a1 a2 api (300); row 1 = b1 b2 tests (260), t1 wraps: BOTH headers
  // end their rows. A break before api puts api b1 b2 on row 1 (260); tests (60) then wraps on its own and
  // starts row 2 with t1: it needs no break, and a pass reading the pre-break layout would have given it one
  const api = head("api"), tests = head("tests"), t1 = tab("t1");
  const bar = strip(300, head("web"), tab("a1"), tab("a2", 80), api, tab("b1"), tab("b2"), tests, t1, add());
  assert.deepEqual(bar.rows(), [["web", "a1", "a2", "api"], ["b1", "b2", "tests"], ["t1", "tab tab-add"]], "the premise");
  paintTabRowLines(bar);
  assert.deepEqual(bar.rows(), [["web", "a1", "a2"], ["api", "b1", "b2"], ["tests", "t1", "tab tab-add"]]);
  assert.equal(bar.keeps().length, 1, "one break, before api");
  assert.equal(api.previousElementSibling, bar.keeps()[0]);
  assert.ok(!tests.previousElementSibling!.isBreak, "tests opens its row by wrapping; no break was spent on it");
  assert.equal(tests.offsetTop, t1.offsetTop);
  assert.deepEqual(bar.lines(), [ROW_H, 2 * ROW_H]);
});

test("no break where one would change nothing: a header already first on its row, the strip's first item, a folded header, an empty trail, or a header the setting already broke", () => {
  const { paintTabRowLines } = lift();
  // 240 wide: web a1 fill 160; api (folded: the next item is a header, no tab) ends row 0 at 220; tests wraps on its own
  const bar = strip(240, head("web"), tab("a1"), head("api"), head("tests"), tab("c1"), add());
  assert.deepEqual(bar.rows(), [["web", "a1", "api"], ["tests", "c1", "tab tab-add"]], "the premise");
  paintTabRowLines(bar);
  assert.equal(bar.keeps().length, 0, "a folded header has no tab to keep with; a header that starts its row needs no break");
  assert.deepEqual(bar.rows(), [["web", "a1", "api"], ["tests", "c1", "tab tab-add"]]);
  // the strip's first item: a header alone on row 0 with its tab below (a strip narrower than the pair) cannot be helped
  const narrow = strip(120, head("web"), tab("a1"), tab("a2"));
  paintTabRowLines(narrow);
  assert.equal(narrow.keeps().length, 0, "nothing ahead of the first item to break from");
  assert.deepEqual(narrow.rows(), [["web"], ["a1"], ["a2"]]);
  // an empty trail: the divider followed by the + tab, which is no session; the divider may end its row
  const trail = strip(260, head("web"), tab("a1"), tab("a2", 80), sep(), add());
  paintTabRowLines(trail);
  assert.equal(trail.keeps().length, 0, "the + is not a tab of the trail's");
  // under stripGroupRows the setting's break already opens the header's row; a header that fills its row alone
  // (its tab below) gets no second break
  const setting = new Item("tab-group-break", 0); setting.attrs["aria-hidden"] = "true";
  const rows = strip(150, head("web"), tab("a1"), setting, head("api", 100), tab("b1"));
  assert.deepEqual(rows.rows(), [["web"], ["a1"], ["api"], ["b1"]], "the premise: api alone on its row, b1 below");
  paintTabRowLines(rows);
  assert.equal(rows.keeps().length, 0, "a break ahead of a break moves nothing");
  assert.equal(rows.children.filter((c) => c.isBreak).length, 1, "the setting's break stands");
});

test("the inline divider is a row member for the hairlines, like a tab (the pre-T264 rule, back); a break is not", () => {
  const { paintTabRowLines } = lift();
  // 200 wide: a 190 tab fills row 0; the divider wraps to row 1 on its own (its tab does not fit beside it, so the
  // keep rule has nothing to move); the trail's tab is row 2. Three rows, two hairlines: one under the divider's row
  const bar = strip(200, tab("a1", 190), sep(), tab("t1", 190));
  paintTabRowLines(bar);
  assert.deepEqual(bar.rows(), [["a1"], ["tab-group-sep"], ["t1"]], "the premise: the divider stands on a row of its own");
  assert.deepEqual(bar.lines(), [ROW_H, 2 * ROW_H], "a hairline under the divider's row: the divider is a visible item of it");
  assert.equal(bar.keeps().length, 0);
  // the setting's zero-height break is no row: counting one drew a hairline at the strip's top edge (T264)
  const brk = new Item("tab-group-break tab-group-sep", 0);
  const rows = strip(400, head("web"), tab("a1"), brk, tab("t1"));
  paintTabRowLines(rows);
  assert.deepEqual(rows.rows(), [["web", "a1"], ["t1"]]);
  assert.deepEqual(rows.lines(), [ROW_H], "no line at 0 for the break's own zero-height line");
});

test("no break for a pair no row can hold (review round 1): a header, or the divider, whose first tab is wider than the room beside it at a row's start stays where it wrapped, and the strip gains no row", () => {
  const { paintTabRowLines } = lift();
  // 200 wide: a0 (100) and g1's header (60) share row 0; g10 (190) fits beside no header, so a break ahead of g1 would
  // put g1 alone on row 1 with g10 still below it: a row spent, the pair still apart. The pass reads the pair back
  // after placing the break and takes it out
  const g1 = head("g1"), g10 = tab("g10", 190);
  const bar = strip(200, tab("a0"), g1, g10, add());
  assert.deepEqual(bar.rows(), [["a0", "g1"], ["g10"], ["tab tab-add"]], "the premise: the header ends row 0 above its tab");
  paintTabRowLines(bar);
  assert.equal(bar.keeps().length, 0, "a break would add a row without joining the pair");
  assert.deepEqual(bar.rows(), [["a0", "g1"], ["g10"], ["tab tab-add"]], "the rows as they wrapped");
  assert.deepEqual(bar.lines(), [ROW_H, 2 * ROW_H]);
  // the divider (13) and a 195 tab: 208 > 200
  const sp = sep(), t1 = tab("t1", 195);
  const trail = strip(200, tab("a0"), sp, t1, add());
  assert.deepEqual(trail.rows(), [["a0", "tab-group-sep"], ["t1"], ["tab tab-add"]], "the premise");
  paintTabRowLines(trail);
  assert.equal(trail.keeps().length, 0);
  assert.deepEqual(trail.rows(), [["a0", "tab-group-sep"], ["t1"], ["tab tab-add"]]);
  // a later header behind such a pair is still judged on the restored layout: g2's header ends row 2 with h1 below
  // (60 + 100 fits a row), so it gets its break
  const g2 = head("g2"), h1 = tab("h1");
  const two = strip(200, tab("a0"), head("g1"), tab("g10", 190), tab("g11", 140), g2, h1, add());
  assert.deepEqual(two.rows(), [["a0", "g1"], ["g10"], ["g11", "g2"], ["h1", "tab tab-add"]], "the premise");
  paintTabRowLines(two);
  assert.equal(two.keeps().length, 1, "one break, for g2");
  assert.equal(g2.previousElementSibling, two.keeps()[0]);
  assert.deepEqual(two.rows(), [["a0", "g1"], ["g10"], ["g11"], ["g2", "h1", "tab tab-add"]]);
});

test("frozen while a tab is dragged (review round 1): with draggedId set, the observer's paint and a direct paint leave the keep breaks where the drag found them though the layout changed; the paint after dragend re-places them", () => {
  const { paintTabRowLines, ensureTabRowObserver, drag, observer } = lift();
  const api = head("api"), b1 = tab("b1");
  const bar = strip(300, head("web"), tab("a1"), tab("a2", 80), api, b1, tab("b2"), add());
  paintTabRowLines(bar); ensureTabRowObserver(bar);
  const brk = bar.keeps()[0];
  assert.equal(api.previousElementSibling, brk, "the premise: api's break stands at dragstart");
  drag("a1");
  bar.resize(400);   // the layout changed under the drag: without the break, api and b1 would share row 0
  observer()!.fire();   // the strip's width observer, mid-drag
  assert.equal(bar.keeps().length, 1, "the break count is unchanged");
  assert.equal(bar.keeps()[0], brk, "the same break, not a re-placed one");
  assert.equal(api.previousElementSibling, brk, "still ahead of api: the drag's `br` input did not move");
  assert.deepEqual(bar.rows(), [["web", "a1", "a2"], ["api", "b1", "b2", "tab tab-add"]], "the rows the drag started with");
  assert.deepEqual(bar.lines(), [ROW_H], "the hairlines still follow the rows");
  paintTabRowLines(bar);   // a direct paint mid-drag (a rebuild flushed early) is covered the same way: the guard is in the painter
  assert.equal(bar.keeps()[0], brk);
  // the other direction: no break stands, a narrowing mid-drag places none; a header may end a row above its tab
  // until the drop, when dragend's rebuild repairs it
  const api2 = head("api"), c1 = tab("b1");
  const two = strip(400, head("web"), tab("a1"), tab("a2", 80), api2, c1, tab("b2"), add());
  paintTabRowLines(two);
  assert.equal(two.keeps().length, 0, "the premise: at 400 the pair shares row 0");
  two.resize(300); paintTabRowLines(two);
  assert.equal(two.keeps().length, 0, "mid-drag: no new break");
  assert.notEqual(api2.offsetTop, c1.offsetTop, "the header ends row 0 above its tab, accepted until the drop");
  // dragend: the next paint (the rebuild) re-places the breaks from the layout as it stands
  drag(null);
  paintTabRowLines(bar);
  assert.equal(bar.keeps().length, 0, "at 400 api fits with b1: the frozen break comes out");
  assert.equal(api.offsetTop, b1.offsetTop);
  paintTabRowLines(two);
  assert.equal(two.keeps().length, 1, "at 300 api needs its break: placed");
  assert.equal(api2.offsetTop, c1.offsetTop);
});

test("the drag's slot before a header, or before the inline divider, standing behind a break is the end of the previous row (executed: render.ts's two redirects); the trail's break under the setting is not redirected", () => {
  const over = RENDER.slice(RENDER.indexOf('tabs.addEventListener("dragover"'), RENDER.indexOf('tabs.addEventListener("drop"'));
  const lines = over.split("\n").filter((l) => /^\s*if \(ref && ref\.classList\.contains\("tab-group-(head|sep)"\)/.test(l));
  assert.equal(lines.length, 2, "one redirect for the header (T264), one for the divider (review round 1): " + lines.join(" | "));
  assert.match(lines[1], /ref\.classList\.contains\("tab-group-sep"\) && !isBreak\(ref\) && isBreak\(before\(ref as HTMLElement\)\)/, "the divider's: a divider, not a break, behind a break");
  const js = requireCjs("esbuild").transformSync(lines.join("\n"), { loader: "ts" }).code;
  const redirect = new Function("ref", "isBreak", "before", js + "\nreturn ref;") as (ref: Item | null, isBreak: (n: Item | null) => boolean, before: (t: Item) => Item | null) => Item | null;
  const isBreak = (n: Item | null) => !!n && n.classList.contains("tab-group-break");
  const before = (t: Item) => t.previousElementSibling;
  // an inline strip after the painter: a keep break ahead of api's header, another ahead of the divider
  const keepA = new Item("tab-group-break tab-keep-break", 0), keepS = new Item("tab-group-break tab-keep-break", 0);
  const api = head("api"), sp = sep(), t1 = tab("t1");
  strip(300, head("web"), tab("a1"), keepA, api, tab("b1"), keepS, sp, t1, add());
  assert.equal(redirect(api, isBreak, before), keepA, "the slot before the header is ahead of its break");
  assert.equal(redirect(sp, isBreak, before), keepS, "the slot before the divider is ahead of its keep break: never between them");
  assert.equal(redirect(t1, isBreak, before), t1, "a tab is not redirected");
  assert.equal(redirect(null, isBreak, before), null);
  // no break ahead: the slot stays before the divider, and before the header
  const plainSep = sep(), plainHead = head("api");
  strip(300, head("web"), tab("a1"), plainHead, tab("b1"), plainSep, tab("t1"));
  assert.equal(redirect(plainSep, isBreak, before), plainSep);
  assert.equal(redirect(plainHead, isBreak, before), plainHead);
  // the trail's break under the setting wears .tab-group-sep and is itself a break: no redirect (its `before` is a tab anyway)
  const trailBrk = new Item("tab-group-break tab-group-sep", 0);
  strip(300, head("web"), tab("a1"), trailBrk, tab("t1"));
  assert.equal(redirect(trailBrk, isBreak, before), trailBrk);
});

test("the third event (review round 1): the document's fonts finishing a load repaints, once per loadingdone and once when fonts.ready settles; the listener stands for later swaps; a host without FontFaceSet is left alone", async () => {
  const { paintTabRowLines, ensureTabRowObserver, fonts } = lift();
  const api = head("api"), a2 = tab("a2", 80);
  const bar = strip(300, head("web"), tab("a1"), a2, api, tab("b1"), tab("b2"), add());
  paintTabRowLines(bar); ensureTabRowObserver(bar);
  assert.equal(bar.keeps().length, 1, "the premise: the fallback font's layout put api at row 0's end");
  const n = bar.paints;
  assert.deepEqual(Object.keys(fonts!.listeners), ["loadingdone"], "one listener, on loadingdone");
  // the swap re-widths a2 (80 to 100) with no box change of the strip's: web a1 a2 fill 260, api wraps on its own
  a2.w = 100; bar.dirty();
  fonts!.dispatch("loadingdone");
  assert.equal(bar.paints, n + 1, "one repaint per loadingdone");
  assert.equal(bar.keeps().length, 0, "the pass re-ran on the new widths: api opens row 1 by wrapping, the break is gone");
  assert.deepEqual(bar.rows(), [["web", "a1", "a2"], ["api", "b1", "b2", "tab tab-add"]]);
  fonts!.resolveReady(); await fonts!.ready;
  assert.equal(bar.paints, n + 2, "one repaint when the fonts are ready");
  fonts!.dispatch("loadingdone");
  assert.equal(bar.paints, n + 3, "a later swap (the light theme's face) repaints again: the listener stands");
  ensureTabRowObserver(bar);   // the once-guard: a second call adds no listener and no observer
  fonts!.dispatch("loadingdone");
  assert.equal(bar.paints, n + 4);
  assert.equal(fonts!.listeners.loadingdone.length, 1);
  // a document without fonts (a stand-in host): the observer alone, no throw
  const bare = lift(null);
  const b2 = strip(300, head("web"), tab("a1"), add());
  bare.paintTabRowLines(b2); bare.ensureTabRowObserver(b2);
  assert.ok(bare.observer(), "the observer is armed without a FontFaceSet");
});

test("the observer watches the strip's WIDTH through a zero-height sentinel, not #tabs (review round 1): a rebuild's replaceChildren sweeps it and ensure puts the same element back; the sentinel is no row, no break, no line", () => {
  FakeRO.made = [];
  const { paintTabRowLines, ensureTabRowObserver, observer, sentinel } = lift();
  const api = head("api"), b1 = tab("b1");
  const bar = strip(300, head("web"), tab("a1"), tab("a2", 80), api, b1, tab("b2"), add());
  paintTabRowLines(bar); ensureTabRowObserver(bar);
  const s = sentinel()!;
  assert.ok(s && s.classList.contains("tab-row-sentinel"), "a sentinel of its own class");
  assert.equal(s.parent, bar, "a child of the strip");
  assert.equal(s.attrs["aria-hidden"], "true", "layout only");
  assert.deepEqual(observer()!.targets, [s], "observe(sentinel): the strip's height, which the pass changes, is not watched");
  assert.ok(!s.isBreak && !s.isLine && !s.classList.contains("tab-group-sep") && !s.classList.contains("tab"),
    "none of the classes the pass's previous-sibling read, the painter's line sweep, dragslot's boxes or sectionHeadOf key on");
  assert.deepEqual(bar.rows(), [["web", "a1", "a2"], ["api", "b1", "b2", "tab tab-add"]], "the rows ignore it");
  assert.deepEqual(bar.lines(), [ROW_H]);
  // the rebuild: replaceChildren, the plan appended, the painter, then ensure; one sentinel, the same one, one observer
  const items = bar.children.filter((c) => !c.isLine && !c.isSentinel);
  bar.replaceChildren();
  for (const it of items) bar.appendChild(it);
  paintTabRowLines(bar); ensureTabRowObserver(bar);
  assert.equal(sentinel(), s, "the same element: the observation stands");
  assert.equal(bar.children.filter((c) => c.isSentinel).length, 1, "back in the strip, once");
  assert.equal(FakeRO.made.length, 1, "one observer for the page");
  assert.equal(bar.keeps().length, 1);
  // the sheet: absolute, full width, zero height, in every theme
  assert.match(CSS, /#tabs \.tab-row-sentinel \{ position: absolute; top: 0; left: 0; right: 0; height: 0; pointer-events: none; \}/,
    "a zero-height child spanning #tabs: its width is the strip's, its height never changes");
  assert.match(RENDER, /tabRowObserver = new ResizeObserver\(\(\) => paintTabRowLines\(bar\)\);\s*\n\s*tabRowObserver\.observe\(tabRowSentinel\);/, "the observer's target is the sentinel");
  assert.doesNotMatch(RENDER, /tabRowObserver\.observe\(bar\)/, "never #tabs itself");
});

test("event-keyed only: the pass rides the painter, which the rebuild, the width observer and the fonts events run, and nothing else does; no timer, no frame callback", () => {
  const painter = RENDER.slice(RENDER.indexOf("function paintTabRowLines("), RENDER.indexOf("let tabRowObserver"));
  const arming = RENDER.slice(RENDER.indexOf("let tabRowObserver"), RENDER.indexOf("function tabEmojiNode("));
  assert.match(painter, /if \(!draggedId\) keepGroupsWithTabs\(bar\);/, "the keep pass runs inside the painter, frozen mid-drag, before the rows are read for the lines");
  assert.ok(painter.indexOf("keepGroupsWithTabs(bar);") < painter.indexOf("const rows = new Map"), "breaks first: they move the rows the lines are laid under");
  for (const [name, text] of [["the painter and the pass", painter], ["the observer and the fonts events", arming]] as const)
    assert.doesNotMatch(text, /setTimeout|setInterval|requestAnimationFrame|Date\.now|performance\.now/, name + ": exact events over time heuristics (repo rule)");
  assert.match(RENDER, /paintTabRowLines\(bar\);\s*\n\s*ensureTabRowObserver\(bar\);/, "the rebuild's call");
  assert.match(arming, /tabRowObserver = new ResizeObserver\(\(\) => paintTabRowLines\(bar\)\);/, "the observer's call");
  assert.match(arming, /fonts\.addEventListener\("loadingdone", \(\) => paintTabRowLines\(bar\)\);/, "the fonts' call");
  // EVERY caller, by shape: the code lines naming each function, comments filtered. A new caller shows up here and
  // must name the event it fires on; a setTimeout or requestAnimationFrame wrapper anywhere in render.ts fails this
  const sites = (name: string) => RENDER.split("\n").map((l) => l.replace(/\s*\/\/.*$/, "").trim()).filter((l) => l.includes(name + "(") && !/^\*/.test(l)).sort();
  assert.deepEqual(sites("keepGroupsWithTabs"), [
    "function keepGroupsWithTabs(bar: HTMLElement): void {",
    "if (!draggedId) keepGroupsWithTabs(bar);",
  ], "the pass is called from the painter and nowhere else");
  assert.deepEqual(sites("paintTabRowLines"), [
    'fonts.addEventListener("loadingdone", () => paintTabRowLines(bar));',
    "function paintTabRowLines(bar: HTMLElement): void {",
    'if (fonts.ready && typeof fonts.ready.then === "function") fonts.ready.then(() => paintTabRowLines(bar));',
    "paintTabRowLines(bar);",
    "tabRowObserver = new ResizeObserver(() => paintTabRowLines(bar));",
  ], "the painter is called from the rebuild, the width observer and the two fonts events, and nowhere else");
});
