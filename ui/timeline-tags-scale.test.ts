// THE SESSIONS & TAGS DIALOG WITH MANY TAGS (the user 2026-09-09, whose ten tags filled the dialog: each
// tag row carried the whole identity palette inline, twelve swatches in two rows, and "pane filters" was
// a five-pane matrix of every tag, so "the sessions", the working area, showed two rows under the fold).
// Now a tag row is one line (pill, delete, rename, ONE colour dot), the palette opens on demand as a
// popover anchored to the dot, the filters fold to one summary line per pane (open on the caption's
// caret, remembered for the page), the tag table caps its height and scrolls within itself, and the
// sessions table takes the rest. EXECUTED over the house fake-DOM shim with the real TimelinePanel: the
// dialog is opened, the dot clicked, a swatch picked, and the posted write is the one the inline
// swatches posted. Synthetic ids and names only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as path from "node:path";
import { createRequire } from "node:module";

function makeNode(tag: string): any {
  const n: any = {
    tag, _attrs: {}, children: [] as any[], style: {}, dataset: {}, _text: "", parentNode: null, value: "",
    get textContent() { return this._text; },
    set textContent(v: any) { this._text = v == null ? "" : String(v); for (const c of this.children) c.parentNode = null; this.children.length = 0; },
    classList: { _s: new Set<string>(), add(...a: string[]) { a.forEach((c) => this._s.add(c)); },
      remove(...a: string[]) { a.forEach((c) => this._s.delete(c)); },
      toggle(c: string, f?: boolean) { f ? this._s.add(c) : this._s.delete(c); }, contains(c: string) { return this._s.has(c); } },
    setAttribute(k: string, v: any) { this._attrs[k] = v; }, getAttribute(k: string) { return this._attrs[k]; },
    setAttributeNS(_n: any, k: string, v: any) { this._attrs[k] = v; }, removeAttribute(k: string) { delete this._attrs[k]; },
    appendChild(c: any) {
      if (c.parentNode) { const i = c.parentNode.children.indexOf(c); if (i >= 0) c.parentNode.children.splice(i, 1); }
      c.parentNode = n; this.children.push(c); return c;
    },
    insertBefore(c: any, ref: any) { c.parentNode = n; const i = this.children.indexOf(ref); i < 0 ? this.children.push(c) : this.children.splice(i, 0, c); return c; },
    removeChild(c: any) { const i = this.children.indexOf(c); if (i >= 0) { this.children.splice(i, 1); c.parentNode = null; } return c; },
    get firstChild() { return this.children[0] || null; },
    remove() { if (n.parentNode) n.parentNode.removeChild(n); },
    _listeners: {} as any,
    addEventListener(t: string, fn: any) { n._listeners[t] = fn; }, removeEventListener(t: string) { delete n._listeners[t]; },
    setPointerCapture() {}, releasePointerCapture() {},
    querySelector() { return null; }, querySelectorAll() { return []; },
    getBoundingClientRect() { return n._rect || { width: 200, height: 20, left: 0, top: 0, right: 200, bottom: 20 }; },
    closest() { return null; },
    // focus is OBSERVABLE: it records the active element on the fake document (the popover focuses the
    // current swatch on open and the dot again on close)
    focus() { g.document.activeElement = n; }, select() {},
    setSelectionRange() {}, selectionStart: 0, selectionEnd: 0,
    createEl(t: string, o: any) { const e = makeNode(t); if (o && o.cls) e.classList.add(o.cls); if (o && o.text) e.textContent = o.text; this.appendChild(e); return e; },
    createDiv(o: any) { return this.createEl("div", o); }, createSpan(o: any) { return this.createEl("span", o); },
  };
  return n;
}
const g: any = global;
g.document = {
  createElement(t: string) { return t === "canvas" ? { getContext() { return { font: "", measureText(s: string) { return { width: (s ? s.length : 0) * 6 }; } }; } } : makeNode(t); },
  createElementNS(_n: any, t: string) { return makeNode(t); },
  createTextNode(text: string) { const n = makeNode("#text"); n.textContent = text; return n; },
  body: makeNode("body"), documentElement: makeNode("html"), head: makeNode("head"),
  getElementById() { return null; },
  addEventListener() {}, removeEventListener() {},
  activeElement: null,
};
// a real store, so the feed row's echo (romp:feedTags-set) is readable back the way the dialog reads it
const stored: Record<string, string> = {};
g.localStorage = { getItem: (k: string) => (k in stored ? stored[k] : null), setItem: (k: string, v: any) => { stored[k] = String(v); }, removeItem: (k: string) => { delete stored[k]; } };
g.getComputedStyle = () => ({ backgroundColor: "rgb(30,30,30)", fontFamily: "sans-serif" });
g.requestAnimationFrame = () => 0;
g.setTimeout = (fn: any) => { try { fn(); } catch { /* focus on a fake node */ } return 0; };
g.addEventListener = () => {}; g.removeEventListener = () => {};
g.matchMedia = () => ({ matches: false, addEventListener() {}, addListener() {} });
g.window = g;
g.innerWidth = 1400; g.innerHeight = 1300;

// the two host bridges, recording every post (the ack test's shape)
const posted: any[] = [];
g.__rompTimelineSetViews = (v: any, writeId: string, edited: string[]) => posted.push({ kind: "views", v: JSON.parse(JSON.stringify(v)), writeId, edited });
g.__rompTimelineTagEdit = (writeId: string, e: any) => posted.push({ kind: "tag", e: Object.assign({ writeId }, JSON.parse(JSON.stringify(e))) });

const VIEW_PATH = path.resolve(process.cwd(), "..", "ui", "romp-timeline-view.js");
const { TimelinePanel, viewTagUnion, lensSummary } = createRequire(__filename)(VIEW_PATH);

const now = 1_781_000_000;
// the twelve identity colours the kernel serves (any twelve distinct hexes; the dialog draws what it is given)
const PALETTE = ["#1EA1EB", "#54B204", "#4EA8A9", "#DD42FF", "#E87221", "#4EC9B0", "#E0AF68", "#F7768E", "#7AA2F7", "#9ECE6A", "#BB9AF7", "#FF9E64"];
const sess = (id: string, name: string, color: string) => ({
  id, name, color, state: "working", live: true, model: "Opus", effort: "high",
  context: 40, since: now - 60, awaiting: [], compacting: [], pendingMail: 0, compactions: [], faded: false, stale: false,
});
const copy = (v: any) => JSON.parse(JSON.stringify(v));
// three tags, each pane holding a different filter, so the folded summary has something to say
const THREE = {
  active: "all", at: 100, seq: 1000,
  actives: { chat: { tags: ["gamma", "alpha"] }, timeline: { all: true }, outline: { none: true } },
  tags: [
    { id: "g1", name: "alpha", color: "#DD42FF", members: ["s1"], mtime: 100 },
    { id: "g2", name: "beta", color: "#4EC9B0", members: ["s2"], mtime: 100 },
    { id: "g3", name: "gamma", color: "#E0AF68", members: [], mtime: 100 },
  ],
};
const THREE_SESSIONS = [sess("s1", "web", "#f7768e"), sess("s2", "api", "#7aa2f7"), sess("s3", "tests", "#9ece6a")];
// thirty tags and forty sessions: the scale every tag or session surface is checked against (ui/CLAUDE.md)
const NAMES30 = Array.from({ length: 30 }, (_, i) => "t" + String(i + 1).padStart(2, "0"));
const THIRTY = {
  active: "all", at: 100, seq: 1000,
  actives: { chat: { tags: NAMES30.slice().reverse() }, timeline: { all: true }, outline: { none: true } },
  tags: NAMES30.map((name, i) => ({ id: "g" + (i + 1), name, color: PALETTE[i % PALETTE.length], members: i < 20 ? ["s" + (i + 1)] : [], mtime: 100 })),
};
const FORTY_SESSIONS = Array.from({ length: 40 }, (_, i) => sess("s" + (i + 1), "job-" + String(i + 1).padStart(2, "0"), PALETTE[i % PALETTE.length]));

function drawnPanel(views: any, sessions: any[]): any {
  posted.length = 0;
  const panel = new TimelinePanel(makeNode("div"));
  panel.update({ now, sessions, turns: {}, messages: [], judging: [], views: copy(views), palette: PALETTE.slice() });
  panel.setCaps({ type: "caps", caps: ["tagEdit"], viewsSeq: views.seq });
  return panel;
}
function walk(x: any, out: any[] = []): any[] { for (const c of x.children || []) { out.push(c); walk(c, out); } return out; }
const textOf = (n: any): string => (n.textContent || "") + (n.children || []).map(textOf).join("");
const styleOf = (n: any): string => String(n._attrs.style || "");
const dots = (panel: any) => walk(panel._viewsDialog).filter((n) => n.dataset.tagDot);
const dotFor = (panel: any, key: string) => dots(panel).find((n) => n.dataset.tagDot === key);
const swatches = (pop: any) => walk(pop).filter((n) => n._attrs.role === "radio");
// the popovers in the HOST document (the dialog's own body), beside the dialog rather than in it
const popsInBody = () => g.document.body.children.filter((n: any) => n._attrs.role === "dialog");
const caption = (panel: any) => walk(panel._viewsDialog).find((n) => String(n.textContent).startsWith("pane filters"));
// the filter pills by their own style signature (the session rows' tag chips share the radius, not the padding)
const chips = (panel: any) => walk(panel._viewsDialog).filter((n) => styleOf(n).startsWith("cursor:pointer;padding:1px 8px;border-radius:9px;font-size:0.82em;"));
// the folded summary: the pane label's row, [label, summary]
const paneLines = (panel: any) => {
  const out: Record<string, any> = {};
  for (const row of walk(panel._viewsDialog)) {
    const lb = row.children && row.children[0];
    if (lb && ["All surfaces", "Chat", "Sessions", "Outline", "Feed"].includes(lb.textContent) && styleOf(lb).includes("flex:0 0 88px")) out[lb.textContent] = row;
  }
  return out;
};
function tagOps() { return posted.filter((p) => p.kind === "tag").map((p) => p.e); }
function openDialog(views: any = THREE, sessions: any[] = THREE_SESSIONS) {
  const panel = drawnPanel(views, sessions);
  panel._openViewsDialog(null);
  assert.ok(panel._viewsDialog, "the dialog opened");
  return panel;
}

test("executed: lensSummary says what a pane shows, in the user's tag order, cut with a count when long", () => {
  const order = ["alpha", "beta", "gamma"];
  assert.equal(lensSummary({ all: true }, order), "All");
  assert.equal(lensSummary(null, order), "All", "no lens yet reads as All, like lensAll");
  assert.equal(lensSummary({ none: true }, order), "no tags");
  assert.equal(lensSummary({ tags: ["gamma", "alpha"] }, order), "alpha, gamma", "the USER'S order, not the order the chips were clicked in");
  assert.equal(lensSummary({ tags: ["beta"], none: true }, order), "beta, no tags", "'no tags' last, as lensLabel puts it");
  assert.equal(lensSummary({ tags: ["zeta", "alpha"] }, order), "alpha, zeta", "a name the union no longer lists sorts last");
  assert.equal(lensSummary({ tags: NAMES30.slice().reverse() }, NAMES30), "t01, t02, t03, t04, t05, t06 +24 more", "six names, then the count");
  assert.equal(lensSummary({ tags: NAMES30.slice(0, 6) }, NAMES30), "t01, t02, t03, t04, t05, t06", "six is not long");
  assert.equal(lensSummary({ tags: NAMES30.slice(0, 7) }, NAMES30, 3), "t01, t02, t03 +4 more", "the cut is a parameter");
  assert.equal(lensSummary({ tags: NAMES30.slice().reverse() }, NAMES30, Infinity), NAMES30.join(", "), "Infinity: the full list (the hover)");
});

test("executed: a tag row is one line: the pill, delete, rename and ONE colour dot; no inline swatches anywhere", () => {
  const panel = openDialog();
  const ds = dots(panel);
  assert.deepEqual(ds.map((d) => d.dataset.tagDot), ["g1", "g2", "g3"], "one dot per tag row, keyed by the tag");
  for (const [d, tg] of ds.map((d, i) => [d, THREE.tags[i]] as const)) {
    assert.ok(styleOf(d).includes("background:" + tg.color + ";"), "the dot wears the tag's own colour");
    assert.equal(d._attrs.role, "button");
    assert.equal(d._attrs.tabindex, "0", "reachable by keyboard");
    assert.equal(d._attrs["aria-haspopup"], "dialog");
    assert.equal(d._attrs["aria-expanded"], "false");
    assert.ok(String(d._attrs.title).includes(tg.name), "the hover names the tag");
  }
  assert.equal(walk(panel._viewsDialog).filter((n) => n._attrs.role === "radio").length, 0, "no swatch in any row");
  assert.equal(popsInBody().length, 0, "…and no popover until a dot is clicked");
  // the row still drags to reorder (the pill cell keeps its handle) and still offers delete and rename
  const cells = walk(panel._viewsDialog).filter((n) => n._tname);
  assert.deepEqual(cells.map((c) => c._tname), ["alpha", "beta", "gamma"]);
  assert.ok(cells.every((c) => c._listeners.pointerdown), "the reorder drag stays on the pill");
  assert.equal(walk(panel._viewsDialog).filter((n) => n.textContent === "delete").length, 3);
  assert.equal(walk(panel._viewsDialog).filter((n) => n.textContent === "rename").length, 3);
  // the table caps its height and scrolls within itself; the sessions table keeps the flex share
  const tgrid = walk(panel._viewsDialog).find((n) => styleOf(n).startsWith("display:grid;grid-template-columns:max-content max-content max-content 1fr;"));
  assert.ok(tgrid, "the tag table");
  assert.ok(styleOf(tgrid).includes("flex:0 0 auto;max-height:35vh;overflow-y:auto;"), "capped, scrolling within, never shrinking below the cap");
  const gridBox = walk(panel._viewsDialog).find((n) => styleOf(n) === "flex:1 1 auto;min-height:0;overflow-y:auto;");
  assert.ok(gridBox, "the sessions table owns the rest of the height and its own scroll");
  panel._closeViewsDialog();
});

test("executed: the dot opens the palette as a popover beside the dialog, the current swatch marked and focused", () => {
  const panel = openDialog();
  const dot = dotFor(panel, "g2");
  dot._listeners.click();
  const pop = panel._tagColorPop;
  assert.ok(pop, "the popover is open");
  assert.deepEqual(popsInBody(), [pop], "it lives in the host document beside the dialog, not inside the card");
  assert.ok(styleOf(pop).startsWith("position:fixed;z-index:1003;"), "one layer above the dialog's backdrop (1002)");
  assert.ok(styleOf(pop).includes("font:12px/1.4"), "the shared menu vocabulary");
  assert.equal(pop._key, "g2");
  assert.equal(dot._attrs["aria-expanded"], "true");
  const sws = swatches(pop);
  assert.equal(sws.length, 12, "the same twelve swatches the rows carried inline");
  assert.deepEqual(sws.map((s) => s._attrs["aria-label"]), PALETTE, "the kernel's palette, in its order");
  const cur = sws.filter((s) => s._attrs["aria-checked"] === "true");
  assert.equal(cur.length, 1, "exactly one current swatch");
  assert.ok(styleOf(cur[0]).includes("background:#4EC9B0;"), "…the tag's colour");
  assert.ok(styleOf(cur[0]).includes("outline:2px solid"), "…ringed");
  assert.equal(g.document.activeElement, cur[0], "…and focused on open");
  assert.deepEqual(sws.map((s) => s._attrs.tabindex), PALETTE.map((c) => (c === "#4EC9B0" ? "0" : "-1")), "one tab stop, on the current swatch");
  assert.ok(styleOf(walk(pop).find((n) => n._attrs.role === "radiogroup")).includes("grid-template-columns:repeat(6,18px)"), "twelve swatches in two balanced rows of six (T164)");
  panel._closeViewsDialog();
});

test("executed: a pick posts the SAME recolor the inline swatch posted, closes the popover, repaints, and puts focus back on the dot", () => {
  const panel = openDialog();
  const dot = dotFor(panel, "g1");
  dot._listeners.click();
  const sw = swatches(panel._tagColorPop).find((s) => s._attrs["aria-label"] === "#54B204");
  sw._listeners.click();
  // the write: a targeted recolor by tid, no name, one writeId (what timeline-views-ack.test.ts asserts of _editTagUnion color)
  const ops = tagOps();
  assert.equal(ops.length, 1, "one post for the pick");
  assert.deepEqual([ops[0].op, ops[0].tid, ops[0].color, ops[0].name], ["recolor", "g1", "#54B204", undefined]);
  assert.ok(typeof ops[0].writeId === "string" && ops[0].writeId, "the write carries its writeId for the ack");
  assert.equal(posted.filter((p) => p.kind === "views").length, 0, "no whole-blob write");
  // the optimistic copy shows the colour at once, held until the ack
  assert.ok(panel._pendingViews, "the optimistic copy is pending");
  assert.equal(panel._curViews().tags.find((t: any) => t.id === "g1").color, "#54B204");
  assert.equal(panel._tagColorPop, null, "the popover closed on the pick");
  assert.equal(popsInBody().length, 0);
  // the dialog repainted: a fresh dot wearing the new colour, focused
  const dot2 = dotFor(panel, "g1");
  assert.ok(dot2 && dot2 !== dot, "the row was rebuilt");
  assert.ok(styleOf(dot2).includes("background:#54B204;"), "the dot wears the picked colour");
  assert.equal(g.document.activeElement, dot2, "focus is back on the dot, not lost in the removed popover");
  assert.equal(dot2._attrs["aria-expanded"], "false");
  // the ack settles it exactly as before
  const S1 = copy(THREE); S1.seq = 1001; S1.at = 113; S1.tags[0].color = "#54B204"; S1.tags[0].mtime = 113;
  panel.viewsAck({ type: "tagEditAck", writeId: ops[0].writeId, ok: true, seq: 1001, tid: "g1", views: copy(S1) });
  assert.equal(panel._pendingViews, null, "the ack clears the optimistic copy");
  assert.equal(panel._curViews().tags[0].color, "#54B204");
  // a REFUSED pick reverts and says why, in the dialog
  dotFor(panel, "g1")._listeners.click();
  swatches(panel._tagColorPop).find((s) => s._attrs["aria-label"] === "#E87221")._listeners.click();
  assert.equal(panel._curViews().tags[0].color, "#E87221", "optimistic");
  const why = "that tag no longer exists";
  panel.viewsAck({ type: "tagEditAck", writeId: tagOps()[1].writeId, ok: false, error: why, tid: "g1", seq: 1001, views: copy(S1) });
  assert.equal(panel._curViews().tags[0].color, "#54B204", "the refused copy is dropped at once");
  assert.ok(styleOf(dotFor(panel, "g1")).includes("background:#54B204;"), "the dot shows the store's truth");
  const shown = walk(panel._viewsDialog).map(textOf).find((s) => s.startsWith("\u26A0 "));
  assert.ok(shown && shown.startsWith("\u26A0 " + why), "the refusal shows in the dialog");
  panel._closeViewsDialog();
});

test("executed: keyboard: Enter or Space on the dot opens; Space on a swatch picks; the arrows move the tab stop", () => {
  const panel = openDialog();
  const dot = dotFor(panel, "g3");
  let prevented = 0;
  dot._listeners.keydown({ key: "Enter", preventDefault() { prevented++; } });
  assert.ok(panel._tagColorPop, "Enter opens");
  assert.equal(prevented, 1);
  dot._listeners.keydown({ key: " ", preventDefault() { prevented++; } });
  assert.equal(panel._tagColorPop, null, "Space on the dot while its popover is open toggles it shut");
  dot._listeners.keydown({ key: " ", preventDefault() { prevented++; } });
  assert.ok(panel._tagColorPop, "…and opens it again");
  const sws = swatches(panel._tagColorPop);
  const curIdx = PALETTE.indexOf("#E0AF68");
  assert.equal(g.document.activeElement, sws[curIdx], "the current swatch has focus");
  sws[curIdx]._listeners.keydown({ key: "ArrowRight", preventDefault() {} });
  assert.equal(g.document.activeElement, sws[curIdx + 1], "ArrowRight moves focus");
  assert.equal(sws[curIdx + 1]._attrs.tabindex, "0"); assert.equal(sws[curIdx]._attrs.tabindex, "-1");
  sws[curIdx + 1]._listeners.keydown({ key: "ArrowDown", preventDefault() {} });
  assert.equal(g.document.activeElement, sws[Math.min(11, curIdx + 7)], "ArrowDown moves a row (six per row)");
  sws[curIdx + 1]._listeners.keydown({ key: "Tab", preventDefault() { prevented = -1; } });
  assert.notEqual(prevented, -1, "other keys pass through");
  sws[1]._listeners.keydown({ key: " ", preventDefault() {} });
  const ops = tagOps();
  assert.deepEqual([ops[0].op, ops[0].tid, ops[0].color], ["recolor", "g3", PALETTE[1]], "Space picks");
  assert.equal(panel._tagColorPop, null);
  panel._closeViewsDialog();
});

test("executed: Escape closes the popover first (focus back on the dot) and the dialog only on the next press", () => {
  const panel = openDialog();
  const dot = dotFor(panel, "g1");
  dot._listeners.click();
  assert.ok(panel._tagColorPop);
  panel._viewsDialogKey.fn({ key: "Escape" });
  assert.equal(panel._tagColorPop, null, "the popover closed");
  assert.equal(popsInBody().length, 0);
  assert.ok(panel._viewsDialog, "the dialog is still open");
  assert.equal(g.document.activeElement, dot, "focus returned to the dot");
  assert.equal(dot._attrs["aria-expanded"], "false");
  assert.equal(tagOps().length, 0, "nothing was written");
  panel._viewsDialogKey.fn({ key: "Escape" });
  assert.equal(panel._viewsDialog, null, "the second Escape closes the dialog");
});

test("executed: a press anywhere on the dialog outside the popover closes it; a press on its own dot leaves the toggle to the click; the backdrop closes both", () => {
  const panel = openDialog();
  const back = panel._viewsDialog;
  const card = back.children[0];
  const dot = dotFor(panel, "g2");
  dot._listeners.click();
  assert.ok(panel._tagColorPop);
  back._listeners.pointerdown({ target: card });
  assert.equal(panel._tagColorPop, null, "a press on the card (outside the popover) closes it");
  assert.ok(panel._viewsDialog, "…and the dialog stays");
  // the dot's own press: the popover stays for the click, which toggles it shut (no close-then-reopen)
  dot._listeners.click();
  assert.ok(panel._tagColorPop);
  back._listeners.pointerdown({ target: dot });
  assert.ok(panel._tagColorPop, "the anchor's press does not close it");
  dot._listeners.click();
  assert.equal(panel._tagColorPop, null, "…the click does");
  // the backdrop: dialog and popover go together
  dot._listeners.click();
  back._listeners.pointerdown({ target: back });
  assert.equal(panel._viewsDialog, null, "the backdrop press closes the dialog");
  assert.equal(panel._tagColorPop, null, "…and the popover with it");
  assert.equal(popsInBody().length, 0, "nothing is left in the host document");
});

test("executed: one popover at a time; closing the dialog any other way removes it too", () => {
  const panel = openDialog();
  dotFor(panel, "g1")._listeners.click();
  const first = panel._tagColorPop;
  dotFor(panel, "g2")._listeners.click();
  assert.notEqual(panel._tagColorPop, first, "the second dot's popover replaced the first");
  assert.equal(panel._tagColorPop._key, "g2");
  assert.deepEqual(popsInBody(), [panel._tagColorPop], "exactly one popover in the host document");
  assert.equal(dotFor(panel, "g1")._attrs["aria-expanded"], "false");
  assert.equal(dotFor(panel, "g2")._attrs["aria-expanded"], "true");
  panel._closeViewsDialog();
  assert.equal(panel._tagColorPop, null);
  assert.equal(popsInBody().length, 0);
});

test("executed: a repaint keeps the popover on its row (the anchor re-pointed) and closes it when the row is gone", () => {
  const panel = openDialog();
  const dot = dotFor(panel, "g2");
  dot._listeners.click();
  const pop = panel._tagColorPop;
  // a refusal for ANOTHER row repaints the dialog: the popover stays, hung on the rebuilt dot
  panel._editTagUnion(viewTagUnion(panel._curViews()).find((u: any) => u.name === "alpha"), { color: "#1EA1EB" });
  panel.viewsAck({ type: "tagEditAck", writeId: tagOps()[0].writeId, ok: false, error: "no", tid: "g1", seq: 1000, views: copy(THREE) });
  assert.equal(panel._tagColorPop, pop, "the popover survived the repaint");
  const dot2 = dotFor(panel, "g2");
  assert.notEqual(dot2, dot, "the dialog was rebuilt");
  assert.equal(panel._tagColorAnchor, dot2, "…and the popover hangs on the new dot");
  assert.equal(dot2._attrs["aria-expanded"], "true", "which knows it is open");
  // the tag deleted elsewhere: the frame that drops it, and the repaint that follows, close the popover with the row
  const gone = copy(THREE); gone.seq = 1002; gone.tags.splice(1, 1);
  panel.update({ now, sessions: THREE_SESSIONS, views: gone });
  assert.equal(panel._curViews().tags.length, 2, "the frame was adopted");
  panel._viewsDialogBuild();
  assert.equal(panel._tagColorPop, null, "no row, no popover");
  panel._closeViewsDialog();
});

test("executed: pane filters render FOLDED, one summary line per pane in the user's tag order; the caret opens the matrix; the choice holds for the page", () => {
  stored["romp:feedTags-set"] = JSON.stringify({ lens: { tags: ["beta"], none: true }, t: 1 });
  const panel = openDialog();
  const cap = caption(panel);
  assert.ok(cap, "the section caption");
  assert.ok(cap.textContent.endsWith(" \u25B8"), "folded: a right-pointing caret");
  assert.equal(cap._attrs["aria-expanded"], "false");
  assert.equal(cap._attrs.role, "button"); assert.equal(cap._attrs.tabindex, "0");
  let lines = paneLines(panel);
  assert.deepEqual(Object.keys(lines), ["Chat", "Sessions", "Outline", "Feed"], "one line per PANE; the bulk row is a control, not a pane");
  const summary = (k: string) => lines[k].children[1].textContent;
  assert.equal(summary("Chat"), "alpha, gamma", "the tags it shows, in the user's tag order (the lens lists gamma first)");
  assert.equal(summary("Sessions"), "All");
  assert.equal(summary("Outline"), "no tags");
  assert.equal(summary("Feed"), "beta, no tags", "the feed row reads its echo");
  assert.equal(lines.Chat.children[1]._attrs.title, "alpha, gamma", "the hover carries the full list");
  assert.equal(chips(panel).length, 0, "no chip while folded");
  // the caret opens the matrix: five rows of All / no tags / every tag
  cap._listeners.click();
  const cap2 = caption(panel);
  assert.ok(cap2.textContent.endsWith(" \u25BE"), "open: a down-pointing caret");
  assert.equal(cap2._attrs["aria-expanded"], "true");
  lines = paneLines(panel);
  assert.deepEqual(Object.keys(lines), ["All surfaces", "Chat", "Sessions", "Outline", "Feed"]);
  assert.equal(chips(panel).length, 5 * (2 + 3), "All, no tags and three tags on each of five rows");
  assert.ok(walk(panel._viewsDialog).some((n) => n.textContent === "(mixed)"), "the panes differ, so the bulk row says so");
  const cell = lines.Chat.children[1];
  assert.ok(styleOf(cell).includes("flex-wrap:wrap;flex:1 1 auto;min-width:0;"), "the chips wrap inside their own cell, under the first chip");
  assert.equal(cell.children.length, 5);
  // a chip still edits its pane (the matrix is the same control it was)
  const noTags = cell.children.find((n: any) => n.textContent === "no tags");
  noTags._listeners.click();
  const w = posted.filter((p) => p.kind === "views");
  assert.equal(w.length, 1, "one whole-blob lens write");
  assert.deepEqual(w[0].v.actives.chat, { none: true, tags: ["gamma", "alpha"] }, "toggled onto the chat lens");
  // the choice holds for the page: a fresh open finds the matrix open
  panel._closeViewsDialog();
  panel._openViewsDialog(null);
  assert.ok(caption(panel).textContent.endsWith(" \u25BE"), "still open on the next open");
  assert.equal(chips(panel).length, 25);
  // Enter on the caption folds it back (and leaves the module default for the tests that follow)
  caption(panel)._listeners.keydown({ key: "Enter", preventDefault() {} });
  assert.ok(caption(panel).textContent.endsWith(" \u25B8"));
  assert.equal(chips(panel).length, 0);
  panel._closeViewsDialog();
  delete stored["romp:feedTags-set"];
});

test("executed: thirty tags and forty sessions: every row, every chip and the sessions section render; the summary cuts with a count", () => {
  const panel = openDialog(THIRTY, FORTY_SESSIONS);
  const dlg = panel._viewsDialog;
  assert.deepEqual(walk(dlg).filter((n) => n._tname).map((n) => n._tname), NAMES30, "thirty one-line tag rows, in order");
  assert.equal(dots(panel).length, 30, "one dot each");
  assert.equal(walk(dlg).filter((n) => n._attrs.role === "radio").length, 0, "and not a swatch among them (360 before)");
  assert.ok(walk(dlg).some((n) => n.textContent === "+ New tag"), "the table's final row");
  // folded filters: four lines, the long one cut
  const lines = paneLines(panel);
  assert.equal(lines.Chat.children[1].textContent, "t01, t02, t03, t04, t05, t06 +24 more");
  assert.equal(lines.Chat.children[1]._attrs.title, NAMES30.join(", "), "the hover has all thirty");
  assert.equal(lines.Sessions.children[1].textContent, "All");
  // open: five rows of thirty-two chips
  caption(panel)._listeners.click();
  assert.equal(chips(panel).length, 5 * 32, "All, no tags and thirty tags on each of five rows");
  caption(panel)._listeners.click();
  assert.equal(chips(panel).length, 0);
  // the sessions section: search, tag all, and every live session
  assert.ok(walk(dlg).some((n) => n.tag === "input" && n.placeholder === "search name or host\u2026"), "the search box");
  assert.ok(walk(dlg).some((n) => n.textContent === "tag all"), "tag all");
  assert.equal(walk(dlg).filter((n) => n._sid).length, 40, "forty session rows");
  // the popover works on the last row too
  dotFor(panel, "g30")._listeners.click();
  assert.equal(swatches(panel._tagColorPop).length, 12);
  swatches(panel._tagColorPop)[0]._listeners.click();
  assert.deepEqual([tagOps()[0].op, tagOps()[0].tid, tagOps()[0].color], ["recolor", "g30", PALETTE[0]]);
  panel._closeViewsDialog();
});
