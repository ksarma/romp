// The inline tab strip's row pass EXECUTED (the strip-inline follow-ups, 2026-09-09): paintTabRowLines lifted
// from render.ts (esbuild at run time, tab-strip-skip-exec.test.ts's pattern) and driven over a fake #tabs whose
// layout is a flex-wrap model, the way dragslot.test.ts models rows: every item has a width, the bar a width and
// one row height; an item that does not fit opens the next row; a .tab-group-break is a zero-height line of its
// own, so the item after it starts a row at the same y. Two rules ride the painter, both keyed on the events that
// already run it (a strip rebuild, the strip's ResizeObserver):
//  - a group keeps with its first tab: a header, or the untagged trail's divider, whose first tab wrapped to the
//    next row gets a break ahead of it, so a group never opens at a row's end with its tabs below;
//  - the divider is a row member for the hairlines, like a tab (the pre-T264 rule, back).
// Synthetic ids only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");

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
  querySelectorAll(sel: string): Item[] {
    const m = sel.match(/^:scope > \.([\w-]+)$/);
    assert.ok(m, "the painter selects its own children by one class: " + sel);
    return this.children.filter((c) => c.classList.contains(m![1]));
  }
  layout(): Map<Item, { top: number; left: number; h: number }> {
    if (this.boxes) return this.boxes;
    const out = new Map<Item, { top: number; left: number; h: number }>();
    let x = 0, top = 0, open = false;   // open: the current row holds an item
    for (const c of this.children) {
      if (c.isLine) { out.set(c, { top: parseFloat(c.style.top || "0"), left: -8, h: 1 }); continue; }   // absolute: out of flow
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
      if (c.isLine || c.isBreak) continue;
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

type Api = { paintTabRowLines: (bar: Bar) => void };

/** makeRowBreak + paintTabRowLines (and whatever the painter calls between it and the observer), transpiled. */
function lift(): Api {
  const a = RENDER.indexOf("function makeRowBreak("), b = RENDER.indexOf("function makeTrailSep(");
  const c = RENDER.indexOf("function paintTabRowLines("), d = RENDER.indexOf("let tabRowObserver");
  assert.ok(a > 0 && b > a && c > b && d > c, "anchors not found: makeRowBreak, makeTrailSep, paintTabRowLines or tabRowObserver moved; re-anchor");
  const js = requireCjs("esbuild").transformSync(RENDER.slice(a, b) + RENDER.slice(c, d), { loader: "ts" }).code;
  const prelude = `const el = (tag, cls) => new ITEM(cls || "", 0);\n`;
  return new Function("ITEM", prelude + js + "\nreturn { paintTabRowLines };") (Item) as Api;
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

test("event-keyed only: the pass rides the painter, which the rebuild and the ResizeObserver already run; no timer, no frame callback", () => {
  const painter = RENDER.slice(RENDER.indexOf("function paintTabRowLines("), RENDER.indexOf("let tabRowObserver"));
  assert.match(painter, /keepGroupsWithTabs\(bar\);/, "the keep pass runs inside the painter, before the rows are read for the lines");
  assert.ok(painter.indexOf("keepGroupsWithTabs(bar);") < painter.indexOf("const rows = new Map"), "breaks first: they move the rows the lines are laid under");
  assert.doesNotMatch(painter, /setTimeout|setInterval|requestAnimationFrame|Date\.now|performance\.now/, "exact events over time heuristics (repo rule)");
  assert.match(RENDER, /paintTabRowLines\(bar\);\s*\n\s*ensureTabRowObserver\(bar\);/, "the rebuild's call");
  assert.match(RENDER, /tabRowObserver = new ResizeObserver\(\(\) => paintTabRowLines\(bar\)\);/, "the observer's call");
});
