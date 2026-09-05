// THE TAGS DIALOG'S WRITES ARE ACKNOWLEDGED (the user 2026-09-05, who lost a batch of renames and
// assignments made in "Manage tags"). Before: every gesture posted the WHOLE views blob built from
// the dialog's own un-echoed optimistic copy, so a burst carried the pre-burst `at` stamp; the
// kernel's stale-writer guard refused the second edit to a tag (a create, then typing its name)
// against the client's OWN first write, told only stderr, and the client — which cleared its
// optimistic copy on an exact echo match or after THREE frames — kept re-posting the refused copy
// until the user paused, when the dialog snapped to the store: "tag N", no members.
// Now: tag gestures post TARGETED ops ({op, name, …, writeId}) the kernel applies by name and
// answers on the same socket ({tagEditAck, writeId, ok, views}); lens and order edits keep the
// whole-blob post, answered by viewsAck. The optimistic copy clears on the ACK (an event), never
// on a frame count; a refusal reverts it at once and shows the reason in the dialog.
// EXECUTED over the house fake-DOM shim with the real TimelinePanel: the dialog is opened, the
// [+ New tag] row clicked, the name typed — the exact gestures that were lost. Synthetic ids only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

function makeNode(tag: string): any {
  const n: any = {
    tag, _attrs: {}, children: [] as any[], style: {}, dataset: {}, textContent: "", parentNode: null, value: "",
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
    removeChild(c: any) { const i = this.children.indexOf(c); if (i >= 0) this.children.splice(i, 1); return c; },
    get firstChild() { return this.children[0] || null; },
    remove() { if (n.parentNode) n.parentNode.removeChild(n); },
    _listeners: {} as any,
    addEventListener(t: string, fn: any) { n._listeners[t] = fn; }, removeEventListener(t: string) { delete n._listeners[t]; },
    setPointerCapture() {}, releasePointerCapture() {},
    querySelector() { return null; }, querySelectorAll() { return []; },
    getBoundingClientRect() { return n._rect || { width: 200, height: 20, left: 0, top: 0, right: 200, bottom: 20 }; },
    closest() { return null; }, focus() {}, select() {}, setSelectionRange() {},
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
};
g.localStorage = { getItem() { return null; }, setItem() {}, removeItem() {} };
g.getComputedStyle = () => ({ backgroundColor: "rgb(30,30,30)", fontFamily: "sans-serif" });
g.requestAnimationFrame = () => 0;
g.setTimeout = (fn: any) => { try { fn(); } catch { /* focus on a fake node */ } return 0; };
g.addEventListener = () => {}; g.removeEventListener = () => {};
g.matchMedia = () => ({ matches: false, addEventListener() {}, addListener() {} });
g.window = g;
g.innerWidth = 1400; g.innerHeight = 800;

// the two host bridges, recording every post: whole-blob writes (views, writeId) and targeted edits
const posted: any[] = [];
g.__rompTimelineSetViews = (v: any, writeId: string) => posted.push({ kind: "views", v: JSON.parse(JSON.stringify(v)), writeId });
g.__rompTimelineTagEdit = (e: any) => posted.push({ kind: "tag", e: JSON.parse(JSON.stringify(e)) });

const VIEW_PATH = path.resolve(process.cwd(), "..", "ui", "romp-timeline-view.js");
const SRC = fs.readFileSync(VIEW_PATH, "utf8");
const { TimelinePanel, viewTagUnion } = createRequire(__filename)(VIEW_PATH);

const now = 1_781_000_000;
const SID1 = "11111111-2222-3333-4444-555555555501";
const SID2 = "11111111-2222-3333-4444-555555555502";
const PALETTE = ["#1EA1EB", "#54B204", "#4EA8A9", "#DD42FF", "#E87221"];
const sess = (id: string, name: string, color: string) => ({
  id, name, color, state: "working", live: true, model: "Opus", effort: "high",
  context: 40, since: now - 60, awaiting: [], compacting: [], pendingMail: 0, compactions: [], faded: false, stale: false,
});
const actives = { chat: { all: true }, outline: { all: true }, timeline: { all: true } };
// the kernel's last echo: one stamped tag, the store's `at`
const S0 = { active: "all", actives, at: 100, tags: [{ id: "gA", name: "web", color: "#3b82f6", members: [SID1], mtime: 100 }] };
const copy = (v: any) => JSON.parse(JSON.stringify(v));

function drawnPanel(): any {
  posted.length = 0;
  const panel = new TimelinePanel(makeNode("div"));
  panel.update({
    now, sessions: [sess(SID1, "web", "#f7768e"), sess(SID2, "api", "#7aa2f7")],
    turns: { [SID1]: [{ id: "t1", start: now - 400, end: now - 100, prompt: "do the thing", tid: "f1", mids: [] }] },
    messages: [], judging: [], views: copy(S0), palette: PALETTE.slice(),
  });
  return panel;
}
// a kernel push carrying a views blob (the two-message path's skeleton frame)
function frame(panel: any, views: any) {
  panel.update({ now, sessions: [sess(SID1, "web", "#f7768e"), sess(SID2, "api", "#7aa2f7")], views: copy(views) });
}
function walk(x: any, out: any[] = []): any[] { for (const c of x.children || []) { out.push(c); walk(c, out); } return out; }
const textOf = (n: any): string => (n.textContent || "") + (n.children || []).map(textOf).join("");
function clickNewTag(panel: any) {
  const btn = walk(panel._viewsDialog).find((n) => n.textContent === "+ New tag");
  assert.ok(btn, "the [+ New tag] row renders");
  btn._listeners.click();
}
function nameInput(panel: any) {
  const inp = walk(panel._viewsDialog).find((n) => n.tag === "input" && n._listeners.change);
  assert.ok(inp, "a new tag opens straight into its rename input");
  return inp;
}
function tagOps() { return posted.filter((p) => p.kind === "tag").map((p) => p.e); }

test("executed: [+ New tag] then typing its name posts two TARGETED ops by tag NAME — never the whole blob", () => {
  const panel = drawnPanel();
  panel._openViewsDialog(null);
  clickNewTag(panel);
  assert.equal(posted.length, 1, "one post for the create");
  const c = posted[0];
  assert.equal(c.kind, "tag", "a tag gesture is a targeted edit, not a whole-blob write");
  assert.equal(c.e.op, "create");
  assert.equal(c.e.name, "tag 2");
  assert.equal(c.e.color, "#1EA1EB", "the first unused palette colour, as before");
  assert.match(c.e.id, /^g[0-9a-z]+$/, "the dialog's own id rides along (the kernel honors it)");
  assert.ok(typeof c.e.writeId === "string" && c.e.writeId, "every write carries a writeId the ack names");
  // the user types the name before ANY echo — the lost gesture
  const inp = nameInput(panel);
  inp.value = "notes-api"; inp._listeners.change();
  const ops = tagOps();
  assert.equal(ops.length, 2);
  assert.deepEqual([ops[1].op, ops[1].name, ops[1].newName], ["rename", "tag 2", "notes-api"],
    "the rename addresses the tag by its current NAME — no `at`, nothing for the guard to judge stale");
  assert.notEqual(ops[1].writeId, ops[0].writeId);
  assert.equal(panel._curViews().tags.find((t: any) => t.id === c.e.id).name, "notes-api", "the optimistic copy shows the typed name at once");
  assert.equal(posted.filter((p) => p.kind === "views").length, 0, "no whole-blob write anywhere in the burst");
});

test("executed: a rename posted before the echo SURVIVES — frames never yield the optimistic copy (no frame count)", () => {
  const panel = drawnPanel();
  panel._openViewsDialog(null);
  clickNewTag(panel);
  const tid = tagOps()[0].id;
  const inp = nameInput(panel); inp.value = "notes-api"; inp._listeners.change();
  // the kernel's echo of the CREATE lands (the store: "tag 2", stamped, `at` moved)
  const S1 = copy(S0); S1.at = 113; S1.tags.push({ id: tid, name: "tag 2", color: "#1EA1EB", members: [], mtime: 113 });
  frame(panel, S1);
  assert.ok(panel._pendingViews, "no exact match (the copy holds the rename) → the pending copy stays");
  assert.equal(panel._curViews().tags.find((t: any) => t.id === tid).name, "notes-api");
  for (let i = 0; i < 6; i++) { const e = copy(S1); e.at = 120 + i; frame(panel, e); }
  assert.ok(panel._pendingViews, "six silent frames later the user's rename is STILL showing — nothing counts frames");
  assert.equal(panel._curViews().tags.find((t: any) => t.id === tid).name, "notes-api");
});

test("executed: the pending copy clears on the ACK — the create's ack leaves the in-flight rename pending; the rename's ack settles it", () => {
  const panel = drawnPanel();
  panel._openViewsDialog(null);
  clickNewTag(panel);
  const inp = nameInput(panel); inp.value = "notes-api"; inp._listeners.change();
  const [w1, w2] = tagOps().map((e) => e.writeId);
  const tid = tagOps()[0].id;
  const S1 = copy(S0); S1.at = 113; S1.tags.push({ id: tid, name: "tag 2", color: "#1EA1EB", members: [], mtime: 113 });
  panel.viewsAck({ type: "tagEditAck", writeId: w1, ok: true, views: copy(S1) });
  assert.deepEqual(panel._views, S1, "the ack's blob is adopted as the new base (stamps included)");
  assert.ok(panel._pendingViews, "the rename is still in flight → its optimistic copy holds");
  assert.equal(panel._curViews().tags.find((t: any) => t.id === tid).name, "notes-api");
  const S2 = copy(S1); S2.at = 114; S2.tags[1].name = "notes-api"; S2.tags[1].mtime = 114;
  panel.viewsAck({ type: "tagEditAck", writeId: w2, ok: true, views: copy(S2) });
  assert.equal(panel._pendingViews, null, "the last in-flight write's ack clears the pending copy");
  assert.deepEqual(panel._curViews(), S2, "…and the dialog now reads the kernel's blob, which holds the name");
  assert.equal(panel._viewsWrites.length, 0, "nothing left in flight");
});

test("executed: a refusal reverts the optimistic copy at once and shows the reason in the open dialog", () => {
  const panel = drawnPanel();
  panel._openViewsDialog(null);
  clickNewTag(panel);
  const tid = tagOps()[0].id;
  const S1 = copy(S0); S1.at = 113; S1.tags.push({ id: tid, name: "tag 2", color: "#1EA1EB", members: [], mtime: 113 });
  panel.viewsAck({ type: "tagEditAck", writeId: tagOps()[0].writeId, ok: true, views: copy(S1) });
  const inp = nameInput(panel); inp.value = "web"; inp._listeners.change();   // a name that already exists
  assert.equal(panel._curViews().tags.find((t: any) => t.id === tid).name, "web", "optimistic until the kernel rules");
  const why = 'a tag named "web" already exists';
  panel.viewsAck({ type: "tagEditAck", writeId: tagOps()[1].writeId, ok: false, error: why, views: copy(S1) });
  assert.equal(panel._pendingViews, null, "the refused copy is dropped at once");
  assert.equal(panel._curViews().tags.find((t: any) => t.id === tid).name, "tag 2", "the dialog shows the store's truth");
  assert.deepEqual(panel._tagEditErr, { host: "", name: "tag 2", error: why }, "the refusal names the tag and the reason");
  const shown = walk(panel._viewsDialog).map(textOf).find((s) => s.startsWith("⚠ "));
  assert.ok(shown && shown.startsWith("⚠ " + why), "…in the dialog, rebuilt in place (the tagEditFailed door's rendering, dismiss ✕ beside it)");
});

test("executed: membership edits are targeted too — the join menu's option adds by name; its new-tag input is ONE create with members", () => {
  const panel = drawnPanel();
  const box = makeNode("div");
  let rebuilt = 0;
  panel._tagJoinMenu(box, [SID2], () => rebuilt++);
  const opt = walk(box).find((n) => n.textContent === "web");
  opt._listeners.click();
  assert.deepEqual([tagOps()[0].op, tagOps()[0].name, tagOps()[0].sids], ["addMember", "web", [SID2]]);
  assert.equal(rebuilt, 1);
  assert.deepEqual(panel._curViews().tags[0].members.slice().sort(), [SID1, SID2].sort(), "optimistic at once");
  const box2 = makeNode("div");
  panel._tagJoinMenu(box2, [SID1, SID2], () => rebuilt++);
  const ni = walk(box2).find((n) => n.tag === "input");
  ni.value = "qa"; ni._listeners.keydown({ key: "Enter" });
  const c = tagOps()[1];
  assert.deepEqual([c.op, c.name, c.sids], ["create", "qa", [SID1, SID2]], "one op: the tag and its first members together");
  assert.match(c.id, /^g[0-9a-z]+$/);
  // a chip's ✕ (remove-everywhere) and the row actions ride the same door
  const u = viewTagUnion(panel._curViews()).find((x: any) => x.name === "web");
  panel._editTagUnion(u, { remove: [SID2] });
  panel._editTagUnion(u, { color: "#DD42FF" });
  panel._editTagUnion(u, { delete: true });
  assert.deepEqual(tagOps().slice(2).map((e) => [e.op, e.name, e.sids || e.color || null]),
    [["removeMember", "web", [SID2]], ["recolor", "web", "#DD42FF"], ["delete", "web", null]]);
  assert.equal(posted.filter((p) => p.kind === "views").length, 0, "still no whole-blob write for any tag gesture");
});

test("executed: lens and order edits keep the whole-blob post, now with a writeId, and the viewsAck settles or reverts them", () => {
  const panel = drawnPanel();
  const nv = copy(S0); nv.actives = Object.assign({}, nv.actives, { timeline: { tags: ["web"] } });
  panel._setViews(nv);
  assert.equal(posted.length, 1);
  assert.equal(posted[0].kind, "views", "a lens edit is still the whole blob (the kernel owns no lens op)");
  assert.deepEqual(posted[0].v.actives.timeline, { tags: ["web"] });
  assert.ok(typeof posted[0].writeId === "string" && posted[0].writeId, "…carrying its writeId");
  assert.ok(panel._pendingViews);
  frame(panel, S0); frame(panel, S0); frame(panel, S0); frame(panel, S0);
  assert.ok(panel._pendingViews, "stale frames never yield it");
  const S1 = copy(nv); S1.at = 130;
  panel.viewsAck({ type: "viewsAck", writeId: posted[0].writeId, ok: true, refused: [], views: copy(S1) });
  assert.equal(panel._pendingViews, null, "the viewsAck clears it");
  assert.deepEqual(panel._views, S1);
  // a genuinely stale whole-blob write (another dashboard edited `web` meanwhile): the guard kept
  // the store's copy and the ack says so; the dialog shows the kernel's blob and the reason
  const nv2 = copy(S1); nv2.tags[0].members = [];
  panel._setViews(nv2);
  const S2 = copy(S1); S2.at = 140; S2.tags[0].members = [SID1, SID2]; S2.tags[0].mtime = 140;
  const reason = 'your copy of "web" predates a newer edit to it; the newer state was kept';
  panel._viewsDialog = makeNode("div"); let rebuilt = 0; panel._viewsDialogBuild = () => rebuilt++;
  panel.viewsAck({ type: "viewsAck", writeId: posted[1].writeId, ok: false, refused: [{ name: "web", reason }], error: reason, views: copy(S2) });
  assert.equal(panel._pendingViews, null);
  assert.deepEqual(panel._curViews(), S2, "reverted to the store's blob");
  assert.deepEqual(panel._tagEditErr, { host: "", name: "web", error: reason });
  assert.equal(rebuilt, 1, "the open dialog repaints with the refusal");
});

test("executed: an ack for a write this page never made still refreshes the base and never strands a pending copy", () => {
  const panel = drawnPanel();
  const S1 = copy(S0); S1.at = 150;
  panel.viewsAck({ type: "viewsAck", writeId: "w-from-a-previous-load", ok: true, refused: [], views: copy(S1) });
  assert.deepEqual(panel._views, S1);
  assert.equal(panel._pendingViews, null);
});

test("executed: without the targeted-edit bridge (an Obsidian panel), a tag gesture falls back to the whole-blob write", () => {
  const panel = drawnPanel();
  const saved = g.__rompTimelineTagEdit;
  delete g.__rompTimelineTagEdit;
  try {
    const u = viewTagUnion(panel._curViews()).find((x: any) => x.name === "web");
    panel._editTagUnion(u, { rename: "site" });
    assert.equal(posted.length, 1);
    assert.equal(posted[0].kind, "views");
    assert.equal(posted[0].v.tags[0].name, "site");
  } finally {
    g.__rompTimelineTagEdit = saved;
  }
});

test("pins: the three-frame yield is gone; the pending copy clears on the echo's exact match or the ack, nothing else", () => {
  assert.doesNotMatch(SRC, /_pendingViewsAge/, "no frame counter anywhere in the panel");
  const rec = SRC.slice(SRC.indexOf("  _reconcileViews() {"), SRC.indexOf("  _postTagEdit("));
  assert.doesNotMatch(rec, />= 3/, "_reconcileViews counts nothing");
  assert.match(rec, /this\._viewsKey\(this\._views\) === this\._viewsKey\(this\._pendingViews\)/, "the exact-match clear stays (the write's own echo IS an event)");
  assert.match(SRC, /window\.__rompTimelineSetViews\(v, writeId\);/, "the whole-blob hook carries the writeId");
  assert.match(SRC, /window\.__rompTimelineTagEdit\(Object\.assign\(\{ writeId \}, edit\)\);/, "the targeted hook too");
});
