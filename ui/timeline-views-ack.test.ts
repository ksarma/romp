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
    tag, _attrs: {}, children: [] as any[], style: {}, dataset: {}, _text: "", parentNode: null, value: "",
    // the real DOM's setter REPLACES the children; the builders clear a container with `textContent = ''`
    // before repainting it, so a fake that kept the children let post-rebuild assertions match stale nodes
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
    removeChild(c: any) { const i = this.children.indexOf(c); if (i >= 0) this.children.splice(i, 1); return c; },
    get firstChild() { return this.children[0] || null; },
    remove() { if (n.parentNode) n.parentNode.removeChild(n); },
    _listeners: {} as any,
    addEventListener(t: string, fn: any) { n._listeners[t] = fn; }, removeEventListener(t: string) { delete n._listeners[t]; },
    setPointerCapture() {}, releasePointerCapture() {},
    querySelector() { return null; }, querySelectorAll() { return []; },
    getBoundingClientRect() { return n._rect || { width: 200, height: 20, left: 0, top: 0, right: 200, bottom: 20 }; },
    closest() { return null; },
    // focus and caret are OBSERVABLE (the rename-draft assertions read them): focus records the active
    // element on the fake document; select() and setSelectionRange() record the selection
    focus() { g.document.activeElement = n; }, select() { n._sel = "all"; n.selectionStart = 0; n.selectionEnd = String(n.value || "").length; },
    setSelectionRange(a: number, b: number) { n._sel = [a, b]; n.selectionStart = a; n.selectionEnd = b; },
    selectionStart: 0, selectionEnd: 0,
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
// (writeId, edit) — recorded flat as {writeId, ...edit} for the assertions
const posted: any[] = [];
g.__rompTimelineSetViews = (v: any, writeId: string, edited: string[]) => posted.push({ kind: "views", v: JSON.parse(JSON.stringify(v)), writeId, edited });
g.__rompTimelineTagEdit = (writeId: string, e: any) => posted.push({ kind: "tag", e: Object.assign({ writeId }, JSON.parse(JSON.stringify(e))) });

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
// the kernel's last echo: one stamped tag, the store's `at`, and its write sequence (`seq` — every
// frame and ack carries the blob's own; a client adopts a blob only when its seq is at least the held one)
const S0 = { active: "all", actives, at: 100, seq: 1000, tags: [{ id: "gA", name: "web", color: "#3b82f6", members: [SID1], mtime: 100 }] };
const copy = (v: any) => JSON.parse(JSON.stringify(v));

// a drawn panel, connected to a kernel that announced the `tagEdit` capability at `ready` (the caps
// frame, as the kernel sends it); `views` overrides the first frame's blob (a seq-less one = a legacy kernel)
function drawnPanel(views: any = S0, caps: string[] = ["tagEdit"]): any {
  posted.length = 0;
  const panel = new TimelinePanel(makeNode("div"));
  panel.update({
    now, sessions: [sess(SID1, "web", "#f7768e"), sess(SID2, "api", "#7aa2f7")],
    turns: { [SID1]: [{ id: "t1", start: now - 400, end: now - 100, prompt: "do the thing", tid: "f1", mids: [] }] },
    messages: [], judging: [], views: copy(views), palette: PALETTE.slice(),
  });
  panel.setCaps({ type: "caps", caps });
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
function findNameInput(panel: any) { return walk(panel._viewsDialog).find((n) => n.tag === "input" && n._listeners.change); }
function nameInput(panel: any) {
  const inp = findNameInput(panel);
  assert.ok(inp, "a new tag opens straight into its rename input");
  return inp;
}
function tagOps() { return posted.filter((p) => p.kind === "tag").map((p) => p.e); }
// the kernel answers a [+ New tag] create: the minted tid and default name, and the blob with the new row
const NEW_TID = "g7";
function ackCreate(panel: any, seq = 1001, name = "tag 1", color = "#1EA1EB") {
  const S1 = copy(S0); S1.at = 113; S1.seq = seq; S1.tags.push({ id: NEW_TID, name, color, members: [], mtime: 113 });
  const c = tagOps()[0];
  panel.viewsAck({ type: "tagEditAck", writeId: c.writeId, ok: true, seq, tid: NEW_TID, name, views: copy(S1) });
  return S1;
}

test("harness: setting textContent replaces the children, as the real DOM does — a rebuilt container holds no stale nodes", () => {
  const box = makeNode("div");
  const a = box.createSpan({ text: "old" }); box.createDiv({ text: "older" });
  assert.equal(walk(box).length, 2);
  box.textContent = "";
  assert.deepEqual(walk(box), [], "the builders clear a container this way before repainting it");
  assert.equal(a.parentNode, null, "…and the removed nodes no longer point at it");
  box.createSpan({ text: "new" });
  assert.deepEqual(walk(box).map((n) => n.textContent), ["new"], "a find() over the walk can only match the current build");
  box.textContent = "plain";
  assert.equal(box.textContent, "plain"); assert.deepEqual(walk(box), []);
});

test("executed: [+ New tag] posts a create the KERNEL names and ids; the ack's tid opens the rename input; typing posts a rename by tid", () => {
  const panel = drawnPanel();
  panel._openViewsDialog(null);
  clickNewTag(panel);
  assert.equal(posted.length, 1, "one post for the create");
  const c = posted[0];
  assert.equal(c.kind, "tag", "a tag gesture is a targeted edit, not a whole-blob write");
  assert.equal(c.e.op, "create");
  assert.equal(c.e.color, "#1EA1EB", "the first unused palette colour, as before");
  assert.equal(c.e.name, undefined, "no dialog-minted name: a 'tag N' from a row count collided with a leftover default-named tag");
  assert.equal(c.e.id, undefined, "no dialog-minted id either — the kernel mints it");
  assert.ok(typeof c.e.writeId === "string" && c.e.writeId, "every write carries a writeId the ack names");
  assert.equal(panel._pendingViews, null, "nothing is drawn optimistically — there is no id to draw it under");
  assert.equal(findNameInput(panel), undefined, "…and no rename input yet");
  const S1 = ackCreate(panel);
  assert.equal(panel._tagEditorFor, NEW_TID, "the ack's tid is where the rename input opens");
  assert.deepEqual(panel._views, S1);
  const inp = nameInput(panel);
  assert.equal(inp.value, "tag 1", "the kernel's default name, ready to be typed over");
  // the user types the name before ANY frame — the lost gesture
  inp.value = "notes-api"; inp._listeners.change();
  const ops = tagOps();
  assert.equal(ops.length, 2);
  assert.deepEqual([ops[1].op, ops[1].tid, ops[1].newName], ["rename", NEW_TID, "notes-api"],
    "the rename addresses the tag by its stored id — no `at`, nothing for the guard to judge stale, and no name to mistake");
  assert.equal(ops[1].name, undefined, "no name field on a rename");
  assert.notEqual(ops[1].writeId, ops[0].writeId);
  assert.equal(panel._curViews().tags.find((t: any) => t.id === NEW_TID).name, "notes-api", "the optimistic copy shows the typed name at once");
  assert.equal(posted.filter((p) => p.kind === "views").length, 0, "no whole-blob write anywhere in the burst");
});

test("executed: a rename posted before any frame SURVIVES — frames never yield the optimistic copy (no frame count)", () => {
  const panel = drawnPanel();
  panel._openViewsDialog(null);
  clickNewTag(panel);
  const S1 = ackCreate(panel);
  const inp = nameInput(panel); inp.value = "notes-api"; inp._listeners.change();
  // the pusher's frames of the CREATE land (the store: "tag 1", stamped, `at` moved — the rename not yet in them)
  frame(panel, S1);
  assert.ok(panel._pendingViews, "a frame that does not carry the rename says nothing about it → the pending copy stays");
  assert.equal(panel._curViews().tags.find((t: any) => t.id === NEW_TID).name, "notes-api");
  for (let i = 0; i < 6; i++) { const e = copy(S1); e.at = 120 + i; frame(panel, e); }
  assert.ok(panel._pendingViews, "six silent frames later the user's rename is STILL showing — nothing counts frames");
  assert.equal(panel._curViews().tags.find((t: any) => t.id === NEW_TID).name, "notes-api");
});

test("executed: the pending copy clears on the ACK — the rename's ack settles it, and the dialog reads the kernel's blob", () => {
  const panel = drawnPanel();
  panel._openViewsDialog(null);
  clickNewTag(panel);
  const S1 = ackCreate(panel);
  assert.equal(panel._pendingViews, null, "the create had no optimistic copy; its ack leaves nothing pending");
  const inp = nameInput(panel); inp.value = "notes-api"; inp._listeners.change();
  const w2 = tagOps()[1].writeId;
  assert.ok(panel._pendingViews, "the rename is in flight → its optimistic copy holds");
  const S2 = copy(S1); S2.at = 114; S2.seq = 1002; S2.tags[1].name = "notes-api"; S2.tags[1].mtime = 114;
  panel.viewsAck({ type: "tagEditAck", writeId: w2, ok: true, seq: 1002, tid: NEW_TID, name: "notes-api", views: copy(S2) });
  assert.equal(panel._pendingViews, null, "the last in-flight write's ack clears the pending copy");
  assert.deepEqual(panel._curViews(), S2, "…and the dialog now reads the kernel's blob, which holds the name");
  assert.equal(panel._viewsWrites.length, 0, "nothing left in flight");
});

test("executed: a refusal reverts the optimistic copy at once and shows the reason in the open dialog; the next gesture still addresses the SAME tag", () => {
  const panel = drawnPanel();
  panel._openViewsDialog(null);
  clickNewTag(panel);
  const S1 = ackCreate(panel);
  const inp = nameInput(panel); inp.value = "web"; inp._listeners.change();   // a name that already exists
  assert.equal(panel._curViews().tags.find((t: any) => t.id === NEW_TID).name, "web", "optimistic until the kernel rules");
  const why = 'a tag named "web" already exists';
  panel.viewsAck({ type: "tagEditAck", writeId: tagOps()[1].writeId, ok: false, error: why, tid: NEW_TID, seq: 1001, views: copy(S1) });
  assert.equal(panel._pendingViews, null, "the refused copy is dropped at once");
  assert.equal(panel._curViews().tags.find((t: any) => t.id === NEW_TID).name, "tag 1", "the dialog shows the store's truth");
  assert.deepEqual(panel._tagEditErr, { host: "", name: "tag 1", error: why }, "the refusal names the tag and the reason");
  const shown = walk(panel._viewsDialog).map(textOf).find((s) => s.startsWith("⚠ "));
  assert.ok(shown && shown.startsWith("⚠ " + why), "…in the dialog, rebuilt in place (the tagEditFailed door's rendering, dismiss ✕ beside it)");
  // finding 7: a recolor in the refusal window addresses the tag by ID — never by the name the
  // rename would have given it (which is the OTHER tag's name)
  const u = viewTagUnion(panel._curViews()).find((x: any) => x.ids.includes(NEW_TID));
  panel._editTagUnion(u, { color: "#DD42FF" });
  const rc = tagOps()[2];
  assert.deepEqual([rc.op, rc.tid, rc.color, rc.name], ["recolor", NEW_TID, "#DD42FF", undefined]);
  assert.equal(panel._curViews().tags.find((t: any) => t.id === "gA").color, "#3b82f6", "\"web\" is untouched in the copy too");
});

// ── DIALOG BEHAVIOUR (the 2026-09-05 review, findings 10/11)
test("executed: a refusal's rebuild preserves another row's in-progress rename — text, caret and focus", () => {
  const S = copy(S0); S.tags.push({ id: "gB", name: "api", color: "#54B204", members: [SID2], mtime: 100 });
  const panel = drawnPanel(S);
  panel._openViewsDialog(null);
  // the user opens the rename input on "api" and types a new name, caret mid-word
  const renameBtn = walk(panel._viewsDialog).filter((n) => n.textContent === "rename")[1];
  assert.ok(renameBtn, "the api row's rename action");
  renameBtn._listeners.click();
  assert.equal(panel._tagEditorFor, "gB");
  let inp = nameInput(panel);
  assert.equal(inp.value, "api");
  assert.equal(g.document.activeElement, inp, "the input took focus on open");
  assert.equal(inp._sel, "all", "…with the stored name selected, ready to be typed over");
  inp.value = "api-v2"; inp._listeners.input(); inp.setSelectionRange(4, 4);
  // meanwhile a recolor of "web" (another row) posted earlier is REFUSED — the dialog repaints
  panel._editTagUnion(viewTagUnion(panel._curViews()).find((x: any) => x.name === "web"), { color: "#DD42FF" });
  panel.viewsAck({ type: "tagEditAck", writeId: tagOps()[0].writeId, ok: false, tid: "gA", seq: 1000, error: "that tag no longer exists — it may have been deleted from another dashboard", views: copy(S) });
  const inp2 = nameInput(panel);
  assert.notEqual(inp2, inp, "the dialog WAS rebuilt (a fresh input)");
  assert.equal(inp2.value, "api-v2", "the typed text survives the rebuild");
  assert.equal(g.document.activeElement, inp2, "focus is back in the input");
  assert.deepEqual(inp2._sel, [4, 4], "the caret is where it was — not select-all, which the next keystroke would replace");
  assert.equal(panel._tagEditorFor, "gB", "the editor stays on the same row");
  // finishing the rename posts it by tid and clears the draft; the next open starts from the stored name
  inp2._listeners.change();
  const ren = tagOps()[1];
  assert.deepEqual([ren.op, ren.tid, ren.newName], ["rename", "gB", "api-v2"]);
  assert.equal(panel._tagRenameDraft, null);
  // Escape drops a draft too
  walk(panel._viewsDialog).filter((n) => n.textContent === "rename")[1]._listeners.click();
  inp = nameInput(panel); inp.value = "zzz"; inp._listeners.input();
  inp._listeners.keydown({ key: "Escape" });
  assert.equal(panel._tagRenameDraft, null);
  assert.equal(findNameInput(panel), undefined, "the editor closed");
});

test("executed: the lane gear menu shows a refusal inline, repaints on it, and ✕ dismisses it", () => {
  const panel = drawnPanel();
  const s = panel.data.sessions.find((x: any) => x.id === SID2);
  const anchor = makeNode("g"); anchor._rect = { left: 40, top: 60, right: 60, bottom: 76, width: 20, height: 16 };
  panel._openLaneMenu(s, anchor);
  assert.ok(panel._laneMenu, "the gear menu is open");
  assert.equal(typeof panel._laneMenu._build, "function", "…and exposes its repaint");
  const notices = () => walk(panel._laneMenu).map((n) => n.textContent as string).filter((t) => t.startsWith("⚠ "));   // the notice spans themselves
  assert.deepEqual(notices(), [], "no notice at rest");
  // a tag gesture made FROM the menu (the [+] join option) is refused by the kernel
  const plus = walk(panel._laneMenu).find((n) => n.textContent === "+" && n._attrs.title === "add a tag");
  assert.ok(plus, "the menu's [+]");
  plus._listeners.click({ stopPropagation() {} });
  const opt = walk(panel._laneMenu).find((n) => n.textContent === "web");
  assert.ok(opt, "the join option for the tag this session lacks");
  opt._listeners.click();
  const w = tagOps()[0];
  assert.deepEqual([w.op, w.tid, w.sids], ["addMember", "gA", [SID2]]);
  const why = "that tag no longer exists — it may have been deleted from another dashboard";
  panel.viewsAck({ type: "tagEditAck", writeId: w.writeId, ok: false, tid: "gA", seq: 1000, error: why, views: copy(S0) });
  const shown = notices();
  assert.equal(shown.length, 1, "the refusal shows in the open menu — the dialog is not the only surface that edits tags");
  assert.ok(shown[0].startsWith("⚠ " + why), shown[0]);
  assert.deepEqual(panel._curViews().tags[0].members, [SID1], "the optimistic add reverted");
  // ✕ dismisses it and repaints the menu without it
  const x = walk(panel._laneMenu).find((n) => n.textContent === "✕" && n.parentNode && textOf(n.parentNode).startsWith("⚠ "));
  assert.ok(x, "the notice has its dismiss");
  x._listeners.click({ stopPropagation() {} });
  assert.equal(panel._tagEditErr, null);
  assert.deepEqual(notices(), [], "gone");
  // a remote refusal (tagEditFailed) lands there too
  panel.tagEditFailed({ type: "tagEditFailed", host: "TESTHOST", name: "web", error: "refused" });
  assert.deepEqual(notices(), ["⚠ TESTHOST: refused"]);
  panel._closeLaneMenu();
  assert.equal(panel._laneMenu, null);
});

test("executed: membership edits are targeted too — the join menu's option adds by tid; its new-tag input is ONE create with members, no client id", () => {
  const panel = drawnPanel();
  const box = makeNode("div");
  let rebuilt = 0;
  panel._tagJoinMenu(box, [SID2], () => rebuilt++);
  const opt = walk(box).find((n) => n.textContent === "web");
  opt._listeners.click();
  assert.deepEqual([tagOps()[0].op, tagOps()[0].tid, tagOps()[0].sids], ["addMember", "gA", [SID2]]);
  assert.equal(rebuilt, 1);
  assert.deepEqual(panel._curViews().tags[0].members.slice().sort(), [SID1, SID2].sort(), "optimistic at once");
  const box2 = makeNode("div");
  panel._tagJoinMenu(box2, [SID1, SID2], () => rebuilt++);
  const ni = walk(box2).find((n) => n.tag === "input");
  ni.value = "qa"; ni._listeners.keydown({ key: "Enter" });
  const c = tagOps()[1];
  assert.deepEqual([c.op, c.name, c.sids, c.id, c.tid], ["create", "qa", [SID1, SID2], undefined, undefined], "one op: the tag and its first members together; the kernel mints the id");
  const drawn = panel._curViews().tags.find((t: any) => t.name === "qa");
  assert.match(drawn.id, /^pending-/, "the optimistic row wears a placeholder id until the ack's blob replaces it");
  // a chip's ✕ (remove-everywhere) and the row actions ride the same door, by tid
  const u = viewTagUnion(panel._curViews()).find((x: any) => x.name === "web");
  panel._editTagUnion(u, { remove: [SID2] });
  panel._editTagUnion(u, { color: "#DD42FF" });
  panel._editTagUnion(u, { delete: true });
  assert.deepEqual(tagOps().slice(2).map((e) => [e.op, e.tid, e.sids || e.color || null, e.name]),
    [["removeMember", "gA", [SID2], undefined], ["recolor", "gA", "#DD42FF", undefined], ["delete", "gA", null, undefined]]);
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
  assert.deepEqual(posted[0].edited, [], "…and naming no edited tag: a refusal on a stale, untouched tag is acked ok, no notice");
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
  const reason = "your copy predates a newer edit to it, so your change was not applied and the newer state was kept";
  panel._viewsDialog = makeNode("div"); let rebuilt = 0; panel._viewsDialogBuild = () => rebuilt++;
  panel.viewsAck({ type: "viewsAck", writeId: posted[1].writeId, ok: false, refused: [{ tid: "gA", name: "web", reason }], error: '"web": ' + reason, views: copy(S2) });
  assert.equal(panel._pendingViews, null);
  assert.deepEqual(panel._curViews(), S2, "reverted to the store's blob");
  assert.deepEqual(panel._tagEditErr, { host: "", name: "web", error: '"web": ' + reason }, "the kernel's line: the name once, what was refused, what was kept");
  assert.equal(rebuilt, 1, "the open dialog repaints with the refusal");
  // ok WITH refusals listed — a stale copy of a tag this write did not edit: settled, no notice
  panel._tagEditErr = null;
  panel._setViews(copy(S2));
  const S3 = copy(S2); S3.seq = 1003;
  panel.viewsAck({ type: "viewsAck", writeId: posted[2].writeId, ok: true, refused: [{ tid: "gA", name: "web", reason }], views: copy(S3) });
  assert.equal(panel._pendingViews, null);
  assert.equal(panel._tagEditErr, null, "nothing the user did was refused, so nothing is said");
});

// ── ORDERING (the 2026-09-05 review, findings 1/8/19): the store's write sequence decides which blob is
// newer, never the order the socket delivered them in. The pusher builds frames from a warmed cache that
// can predate a write whose ack already arrived; federation re-emits stored blobs; a net-zero burst leaves
// frames EQUAL to the copy while its writes are still in flight. The seq is exact where the exact-echo
// heuristic guessed.
test("executed: a frame carrying an OLDER write sequence than the ack's blob is ignored — store order, not wire order", () => {
  const panel = drawnPanel();                       // holds S0 (seq 1000)
  const warned: string[] = []; const cw = console.warn; console.warn = (s: any) => { warned.push(String(s)); };
  try {
    const S2 = copy(S0); S2.seq = 1002; S2.at = 120; S2.tags[0].members = [SID1, SID2]; S2.tags[0].mtime = 120;
    panel.viewsAck({ type: "tagEditAck", writeId: "w-x", ok: true, seq: 1002, views: copy(S2) });
    assert.equal(panel._views.seq, 1002);
    const stale = copy(S0); stale.seq = 1001;       // the pusher's warmed cache: built before the write, delivered after the ack
    frame(panel, stale);
    assert.equal(panel._views.seq, 1002, "the older blob does not replace the newer one");
    assert.deepEqual(panel._curViews().tags[0].members, [SID1, SID2], "the dialog keeps showing the write");
    frame(panel, stale);
    assert.equal(warned.length, 1, "the ignored blob is logged once per page, not once per frame");
    assert.match(warned[0], /older than the one held/);
    const S3 = copy(S2); S3.seq = 1003; frame(panel, S3);
    assert.equal(panel._views.seq, 1003, "a newer frame is adopted as before");
    const legacy = copy(S3); delete legacy.seq;
    frame(panel, legacy);
    assert.equal(panel._views.seq, undefined, "a blob without a seq (a kernel from before the stamp) still adopts — nothing is gated on a field it never sends");
  } finally { console.warn = cw; }
});

test("executed: a NET-ZERO burst (add, then remove) is not cleared early by frames that happen to equal the copy", () => {
  const panel = drawnPanel();
  const u = viewTagUnion(panel._curViews()).find((x: any) => x.name === "web");
  panel._editTagUnion(u, { add: [SID2] });
  const u2 = viewTagUnion(panel._curViews()).find((x: any) => x.name === "web");
  panel._editTagUnion(u2, { remove: [SID2] });
  assert.equal(panel._viewsWrites.length, 2, "two writes in flight");
  assert.deepEqual(panel._curViews().tags[0].members, [SID1], "the copy is back to the pre-burst state — net zero");
  frame(panel, copy(S0));                           // a frame equal to the copy: seq 1000, built before either write
  assert.equal(panel._viewsWrites.length, 2, "an exact match is NOT a write's echo when the blob carries a seq — nothing clears");
  assert.ok(panel._pendingViews);
  const S1 = copy(S0); S1.seq = 1001; S1.tags[0].members = [SID1, SID2];   // the add landed on the kernel
  frame(panel, S1);
  assert.deepEqual(panel._curViews().tags[0].members, [SID1], "the half-applied state never shows: the copy holds until the acks");
  const [w1, w2] = panel._viewsWrites.map((w: any) => w.id);
  panel.viewsAck({ type: "tagEditAck", writeId: w1, ok: true, seq: 1001, views: copy(S1) });
  assert.ok(panel._pendingViews, "the first ack leaves the second write pending");
  const S2 = copy(S0); S2.seq = 1002;
  panel.viewsAck({ type: "tagEditAck", writeId: w2, ok: true, seq: 1002, views: copy(S2) });
  assert.equal(panel._pendingViews, null, "the last ack settles the burst");
  assert.deepEqual(panel._curViews().tags[0].members, [SID1]);
});

test("executed: an ack whose blob a newer frame already overtook still settles its write, and does not roll the base back", () => {
  const panel = drawnPanel();
  const u = viewTagUnion(panel._curViews()).find((x: any) => x.name === "web");
  panel._editTagUnion(u, { color: "#DD42FF" });
  const w = panel._viewsWrites[0].id;
  const S2 = copy(S0); S2.seq = 1002; S2.tags[0].color = "#DD42FF"; S2.tags[0].members = [SID1, SID2];   // our recolor plus another dashboard's add
  frame(panel, S2);
  const S1 = copy(S0); S1.seq = 1001; S1.tags[0].color = "#DD42FF";
  panel.viewsAck({ type: "tagEditAck", writeId: w, ok: true, seq: 1001, views: copy(S1) });   // the ack, delivered after the newer frame
  assert.equal(panel._pendingViews, null, "the ack settles the write");
  assert.equal(panel._views.seq, 1002, "…without replacing the newer blob");
  assert.deepEqual(panel._curViews().tags[0].members, [SID1, SID2]);
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

// ── CAPABILITY (the 2026-09-05 review, findings 2/12): the kernel announces `tagEdit` at every `ready`;
// without it the panel takes the pre-cap path (the whole blob, reconciled by the legacy exact echo and
// three-frame yield, since no ack will come); an op the kernel does not know is answered unknownOp.
test("executed: against a kernel WITHOUT the tagEdit capability, a tag gesture posts the whole blob — the legacy path — and legacy frames settle it by exact echo or three silent frames", () => {
  const L0 = copy(S0); delete L0.seq;                    // an older kernel stamps no seq…
  const panel = drawnPanel(L0, []);                      // …and announces no tagEdit
  const u = viewTagUnion(panel._curViews()).find((x: any) => x.name === "web");
  panel._editTagUnion(u, { rename: "site" });
  assert.equal(posted.length, 1);
  assert.equal(posted[0].kind, "views", "no capability → the pre-cap whole-blob write");
  assert.equal(posted[0].v.tags[0].name, "site");
  assert.ok(typeof posted[0].writeId === "string", "the writeId rides anyway — an older kernel ignores it");
  assert.deepEqual(posted[0].edited, ["gA"], "…and the tag it changed, for a kernel new enough to read it");
  // LEGACY reconciliation, for this path only: a frame that echoes the edit clears it…
  const echo = copy(L0); echo.tags[0].name = "site";
  frame(panel, echo);
  assert.equal(panel._pendingViews, null, "the exact echo clears the copy (legacy)");
  // …and three silent seq-less frames yield an unechoed one (with no ack coming, it would pin forever)
  panel._editTagUnion(viewTagUnion(panel._curViews()).find((x: any) => x.name === "site"), { color: "#DD42FF" });
  assert.ok(panel._pendingViews);
  frame(panel, echo); frame(panel, echo);
  assert.ok(panel._pendingViews, "two silent frames: still holding");
  frame(panel, echo);
  assert.equal(panel._pendingViews, null, "the third yields — the legacy kernel's only clear");
  // [+ New tag] on the legacy path: a whole-blob create the dialog names and ids, the row opened for renaming
  panel._openViewsDialog(null);
  clickNewTag(panel);
  const last = posted[posted.length - 1];
  assert.equal(last.kind, "views");
  const added = last.v.tags.find((t: any) => t.name === "tag 1");
  assert.ok(added && /^g[0-9a-z]+$/.test(added.id), "legacy: the dialog mints the id and the lowest free 'tag N'");
  assert.deepEqual(last.edited, [added.id], "…names it as edited (a kernel that reads `edited` takes an unnamed unknown tag for a stale re-creation)");
  assert.equal(panel._tagEditorFor, added.id, "…and opens the rename input on it");
  // a New tag when the capability is present posts the targeted create (the same panel, the cap arriving)
  panel.setCaps({ type: "caps", caps: ["tagEdit"] });
  clickNewTag(panel);
  assert.equal(posted[posted.length - 1].kind, "tag");
});

test("executed: an unknownOp reply surfaces as a refusal, withdraws the capability, and the next gesture takes the older path", () => {
  const panel = drawnPanel();
  panel._openViewsDialog(null);
  const u = viewTagUnion(panel._curViews()).find((x: any) => x.name === "web");
  panel._editTagUnion(u, { rename: "site" });
  const w = tagOps()[0].writeId;
  assert.equal(panel._curViews().tags[0].name, "site", "optimistic");
  panel.unknownOp({ type: "unknownOp", op: "tagEdit", writeId: w });
  assert.equal(panel._pendingViews, null, "the copy reverts — the kernel did nothing with the write");
  assert.equal(panel._curViews().tags[0].name, "web");
  assert.match(panel._tagEditErr.error, /does not know the tagEdit operation/, "…and the dialog says why");
  assert.equal(panel._caps.has("tagEdit"), false, "the capability is withdrawn");
  panel._editTagUnion(viewTagUnion(panel._curViews())[0], { color: "#DD42FF" });
  assert.equal(posted[posted.length - 1].kind, "views", "the next gesture is a whole-blob write that kernel does know");
  // an unknownOp for a write this page never made changes nothing but the cap
  const n = posted.length; const before = panel._pendingViews;
  panel.unknownOp({ type: "unknownOp", op: "somethingElse", writeId: "w-not-ours" });
  assert.equal(posted.length, n); assert.equal(panel._pendingViews, before);
});

test("executed: a lost ack — the caps frame the kernel sends at every ready (a re-established socket) drops what was in flight, says so, and the next frame is adopted", () => {
  const panel = drawnPanel();
  panel._openViewsDialog(null);
  const u = viewTagUnion(panel._curViews()).find((x: any) => x.name === "web");
  panel._editTagUnion(u, { rename: "site" });
  assert.equal(panel._viewsWrites.length, 1, "the rename is in flight");
  // the socket dropped between the write and its ack; the shim reconnected and re-sent `ready`; the
  // kernel answered with its caps — the ONE event that says the in-flight answer may never come
  panel.setCaps({ type: "caps", caps: ["tagEdit"] });
  assert.deepEqual(panel._viewsWrites, [], "nothing pins: the writes are unknowable and are dropped");
  assert.equal(panel._pendingViews, null, "the copy reverts to the store's truth");
  assert.equal(panel._curViews().tags[0].name, "web");
  assert.match(panel._tagEditErr.error, /re-established.*may not have landed/, "the user is told — never a fake success, never a silent revert");
  const shown = walk(panel._viewsDialog).map(textOf).find((s) => s.startsWith("⚠ "));
  assert.ok(shown, "…in the open dialog");
  const S2 = copy(S0); S2.seq = 1002; S2.tags[0].name = "site";      // the write HAD landed: the next frame shows it
  frame(panel, S2);
  assert.equal(panel._curViews().tags[0].name, "site", "the next frame is adopted as the truth");
  // a caps frame with nothing in flight (the page's own load) changes nothing but the caps
  const before = panel._tagEditErr;
  panel.setCaps({ type: "caps", caps: ["tagEdit"] });
  assert.equal(panel._tagEditErr, before);
});

// ── ROUND 3 (the 2026-09-05 review, verification round): the in-flight create gate, the legacy create's
// id, the join input's draft, the create ack and an open editor, and a refusal reverting only its own write.
test("executed: [+ New tag] takes ONE click per create — the row reads creating… until the ack, then the button is back", () => {
  const panel = drawnPanel();
  panel._openViewsDialog(null);
  clickNewTag(panel);
  assert.equal(tagOps().length, 1, "one create posted");
  const busy = walk(panel._viewsDialog).find((n) => n.textContent === "creating…");
  assert.ok(busy, "the row says a create is in flight");
  assert.equal(busy._attrs["aria-disabled"], "true");
  assert.equal(busy._listeners.click, undefined, "…and takes no click");
  assert.equal(walk(panel._viewsDialog).find((n) => n.textContent === "+ New tag"), undefined, "the button is gone while one is in flight");
  assert.equal(tagOps().length, 1, "a second click before the ack posts nothing — no second tag");
  ackCreate(panel);
  assert.ok(walk(panel._viewsDialog).find((n) => n.textContent === "+ New tag"), "the ack's repaint brings the button back");
  assert.equal(walk(panel._viewsDialog).find((n) => n.textContent === "creating…"), undefined);
  clickNewTag(panel);
  assert.equal(tagOps().length, 2, "…and the next click is a new create");
  // a refusal re-arms it too
  panel.viewsAck({ type: "tagEditAck", writeId: tagOps()[1].writeId, ok: false, error: "the views blob caps at 32 tags", seq: 1001, views: copy(panel._views) });
  assert.ok(walk(panel._viewsDialog).find((n) => n.textContent === "+ New tag"));
});

test("executed: the join menu's new-tag input takes ONE Enter per create — disabled and saying so until the ack repaints the menu", () => {
  const panel = drawnPanel();
  const s = panel.data.sessions.find((x: any) => x.id === SID2);
  const anchor = makeNode("g"); anchor._rect = { left: 40, top: 60, right: 60, bottom: 76, width: 20, height: 16 };
  panel._openLaneMenu(s, anchor);
  const plus = () => walk(panel._laneMenu).find((n) => n.textContent === "+" && n._attrs.title === "add a tag");
  plus()._listeners.click({ stopPropagation() {} });
  const ni = walk(panel._laneMenu).find((n) => n.tag === "input");
  assert.ok(ni, "the join menu's input");
  assert.equal(ni.disabled, undefined);
  ni.value = "qa"; ni._listeners.keydown({ key: "Enter" });
  assert.equal(tagOps().length, 1);
  assert.deepEqual([tagOps()[0].op, tagOps()[0].name], ["create", "qa"]);
  ni._listeners.keydown({ key: "Enter" });                          // the same node, again, before the ack
  assert.equal(tagOps().length, 1, "a second Enter before the ack posts nothing");
  assert.equal(ni.disabled, true, "the input went dead on submit");
  // the menu was rebuilt without the join box (it closes on submit); opening it again while the
  // create is in flight shows a disabled input that says so
  plus()._listeners.click({ stopPropagation() {} });
  const ni2 = walk(panel._laneMenu).find((n) => n.tag === "input");
  assert.notEqual(ni2, ni);
  assert.equal(ni2.disabled, true);
  assert.equal(ni2.placeholder, "creating…");
  ni2.value = "docs"; ni2._listeners.keydown({ key: "Enter" });
  assert.equal(tagOps().length, 1, "Enter on the disabled input posts nothing");
  // the create's ack repaints the open menu: the input is live again
  const S1 = copy(S0); S1.seq = 1001; S1.tags.push({ id: "g8", name: "qa", color: "#1EA1EB", members: [SID2], mtime: 113 });
  panel.viewsAck({ type: "tagEditAck", writeId: tagOps()[0].writeId, ok: true, seq: 1001, tid: "g8", name: "qa", views: S1 });
  const ni3 = walk(panel._laneMenu).find((n) => n.tag === "input");
  assert.ok(ni3 && ni3 !== ni2, "the menu was rebuilt on the ack");
  assert.equal(ni3.disabled, undefined);
  assert.equal(ni3.placeholder, "new tag…");
  ni3.value = "docs"; ni3._listeners.keydown({ key: "Enter" });
  assert.equal(tagOps().length, 2, "…and takes the next create");
  panel._closeLaneMenu();
});

test("executed: the join menu's new-tag input keeps its text and caret across a repaint; submit and close drop the draft", () => {
  const panel = drawnPanel();
  const box = makeNode("div");
  panel._tagJoinMenu(box, [SID2], () => {});
  const ni = walk(box).find((n) => n.tag === "input");
  assert.equal(g.document.activeElement, ni, "the input took focus");
  ni.value = "do"; ni.selectionStart = 1; ni.selectionEnd = 1; ni._listeners.input();
  ni.value = "doc"; ni.selectionStart = 2; ni.selectionEnd = 2;            // the caret moved without an input event (arrow keys)
  // a refusal for some other write repaints the surface that holds the menu — here, the builder runs again
  const box2 = makeNode("div");
  panel._tagJoinMenu(box2, [SID2], () => {});
  const ni2 = walk(box2).find((n) => n.tag === "input");
  assert.notEqual(ni2, ni, "a fresh input");
  assert.equal(ni2.value, "doc", "the typed text survives — read from the live input, not the last input event");
  assert.deepEqual(ni2._sel, [2, 2], "the caret is where it was");
  assert.equal(g.document.activeElement, ni2, "focus is back in the input");
  // a menu for OTHER rows starts empty; the draft for these rows is kept
  const box3 = makeNode("div");
  panel._tagJoinMenu(box3, [SID1], () => {});
  assert.equal(walk(box3).find((n) => n.tag === "input").value, "", "another row's menu does not inherit the draft");
  const box4 = makeNode("div");
  panel._tagJoinMenu(box4, [SID2], () => {});
  const ni4 = walk(box4).find((n) => n.tag === "input");
  assert.equal(ni4.value, "doc");
  // submit posts the drafted name and drops the draft
  ni4.value = "docs"; ni4._listeners.input(); ni4._listeners.keydown({ key: "Enter" });
  assert.equal(tagOps()[0].name, "docs");
  assert.equal(panel._tagNewDraft, null);
  ackCreate(panel, 1001, "docs");
  // closing the menu from the lane gear's [+] drops a draft too
  const s = panel.data.sessions.find((x: any) => x.id === SID2);
  const anchor = makeNode("g"); anchor._rect = { left: 40, top: 60, right: 60, bottom: 76, width: 20, height: 16 };
  panel._openLaneMenu(s, anchor);
  const plus = () => walk(panel._laneMenu).find((n) => n.textContent === "+" && n._attrs.title === "add a tag");
  plus()._listeners.click({ stopPropagation() {} });
  const li = walk(panel._laneMenu).find((n) => n.tag === "input");
  li.value = "zz"; li._listeners.input();
  assert.equal(panel._tagNewDraft.value, "zz");
  plus()._listeners.click({ stopPropagation() {} });                       // toggles the join box closed
  assert.equal(panel._tagNewDraft, null, "closing the menu drops the draft");
  panel._closeLaneMenu();
});

test("executed: LEGACY (no cap): a create from the join menu ships a client-minted g… id, never the pending- placeholder, and names it as edited", () => {
  const L0 = copy(S0); delete L0.seq;
  const panel = drawnPanel(L0, []);
  const box = makeNode("div");
  panel._tagJoinMenu(box, [SID1, SID2], () => {});
  const ni = walk(box).find((n) => n.tag === "input");
  ni.value = "qa"; ni._listeners.keydown({ key: "Enter" });
  assert.equal(posted.length, 1);
  assert.equal(posted[0].kind, "views", "the whole blob — the store write itself on this path");
  const row = posted[0].v.tags.find((t: any) => t.name === "qa");
  assert.ok(row, "the new row is in the blob");
  assert.match(row.id, /^g[0-9a-z]+$/, "a proper id (the dialog's pre-2026-09-05 scheme) — nothing pending- is ever persisted");
  assert.deepEqual(row.members, [SID1, SID2]);
  assert.deepEqual(posted[0].edited, [row.id], "…and the write names it: a kernel that reads `edited` would otherwise keep an unknown tag out as a stale re-creation");
  assert.equal(panel._curViews().tags.find((t: any) => t.name === "qa").id, row.id, "the optimistic copy shows the same id");
  assert.equal(JSON.stringify(posted).indexOf("pending-"), -1, "no placeholder anywhere on the wire");
});

test("executed: a refusal reverts ONLY its own write — a later write still in flight keeps its optimistic change, and its own ack settles it", () => {
  const panel = drawnPanel();
  const u = viewTagUnion(panel._curViews()).find((x: any) => x.name === "web");
  panel._editTagUnion(u, { color: "#DD42FF" });                                           // A: recolor
  panel._editTagUnion(viewTagUnion(panel._curViews()).find((x: any) => x.name === "web"), { add: [SID2] });   // B: add, from the copy showing A
  const [wA, wB] = panel._viewsWrites.map((w: any) => w.id);
  assert.deepEqual([panel._curViews().tags[0].color, panel._curViews().tags[0].members], ["#DD42FF", [SID1, SID2]], "both show");
  // A is refused (say, the tag was recoloured elsewhere first — a targeted op the kernel refused)
  panel.viewsAck({ type: "tagEditAck", writeId: wA, ok: false, tid: "gA", seq: 1000, error: "that tag no longer exists — it may have been deleted from another dashboard", views: copy(S0) });
  assert.deepEqual(panel._viewsWrites.map((w: any) => w.id), [wB], "only A is dropped; B is still in flight");
  assert.ok(panel._pendingViews, "B's copy still shows");
  assert.equal(panel._curViews().tags[0].color, "#3b82f6", "A's recolor reverted");
  assert.deepEqual(panel._curViews().tags[0].members, [SID1, SID2], "B's add did NOT flap off");
  assert.match(panel._tagEditErr.error, /no longer exists/, "the refusal is still shown");
  // B's ack settles it
  const S1 = copy(S0); S1.seq = 1001; S1.tags[0].members = [SID1, SID2];
  panel.viewsAck({ type: "tagEditAck", writeId: wB, ok: true, seq: 1001, tid: "gA", views: S1 });
  assert.equal(panel._pendingViews, null);
  assert.deepEqual(panel._curViews().tags[0].members, [SID1, SID2]);
  // a whole-blob write in flight after a refused targeted one: the copy IS that write's blob
  panel._editTagUnion(viewTagUnion(panel._curViews()).find((x: any) => x.name === "web"), { rename: "site" });   // C
  const nv = copy(panel._curViews()); nv.actives = Object.assign({}, nv.actives, { timeline: { tags: ["site"] } });
  panel._setViews(nv);                                                                   // D: a lens write built from the copy showing C
  const wC = panel._viewsWrites[0].id;
  panel.viewsAck({ type: "tagEditAck", writeId: wC, ok: false, tid: "gA", seq: 1001, error: 'a tag named "site" already exists', views: copy(S1) });
  assert.equal(panel._viewsWrites.length, 1, "D is still in flight");
  assert.deepEqual(panel._curViews().actives.timeline, { tags: ["site"] }, "D's lens still shows");
  assert.equal(panel._curViews().tags[0].name, "site", "D posted the whole blob with C's rename in it — what the kernel will judge D by, so that is what shows");
});

test("pins: no frame count settles a stamped kernel's write; the legacy exact echo and three-frame yield live in the seq-less branch only", () => {
  assert.doesNotMatch(SRC, /_pendingViewsAge/, "the old counter is gone");
  const rec = SRC.slice(SRC.indexOf("  _reconcileViews() {"), SRC.indexOf("  // The LOCAL kernel's capabilities"));
  assert.match(rec, /viewsSeq\(this\._views\) === null\s*\n\s*&& \(this\._viewsKey\(this\._views\) === this\._viewsKey\(this\._pendingViews\)\s*\n\s*\|\| \(this\._legacyViewsAge = \(this\._legacyViewsAge \|\| 0\) \+ 1\) >= 3\)\)/,
    "both legacy clears sit under the seq-less condition — a blob with a seq comes from a kernel that acks, and only the ack settles");
  assert.equal((rec.match(/>= 3/g) || []).length, 1, "one legacy yield, nowhere else");
  assert.match(SRC, /_postTagEdit\(nv, edit, meta\) \{\s*\n\s*if \(!this\._tagEditsTargeted\(\)\) \{\s*\n\s*if \(!nv\) return;[\s\S]{0,1200}?const edited = \[edit\.tid, edit\.tid_from, edit\.tid_to\]\.filter\(Boolean\);[\s\S]{0,400}?this\._setViews\(nv, edited\);\s*\n\s*return;\s*\n\s*\}/,
    "a targeted op needs the capability AND a bridge; otherwise the whole-blob write, naming the tags it changed (a create's row included)");
  assert.match(SRC, /window\.__rompTimelineSetViews\(v, writeId, Array\.isArray\(edited\) \? edited : \[\]\);/, "the whole-blob hook carries the writeId and the edited tag ids");
  assert.match(SRC, /window\.__rompTimelineTagEdit\(writeId, edit\);/, "the targeted hook carries the writeId beside the NESTED op");
  assert.doesNotMatch(SRC, /op: '(?:rename|recolor|addMember|removeMember|delete)', name:/, "no op but create carries a name — every one addresses by tid");
});
