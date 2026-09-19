// The to-do card's second section (plans/user-todos.md): the agent's plan (the existing checklist) and
// "Waiting on you" (the open requests the session filed with the person it works for) share ONE
// transcript-bottom card, each section auto-hiding when empty, so today's behavior is unchanged when no
// request exists. Per row: Reply (the answer goes into the session, anchored to the request) and Dismiss
// (clears without one); a row WITH detail says so at a glance and opens on click; a row whose answer is
// parked in the kernel reads "answer queued" in Reply's place; a blocking request wears a small mark; past
// twelve rows the rest hide behind a keyed toggle. Source pins (render.ts has no jsdom harness, the repo
// convention), plus the optimistic removal EXECUTED: el(), notice(), renderTodo and utDropRow lifted from
// render.ts and run over a fake DOM the way chat-exact-tail-exec.test.ts lifts chatTail.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "styles.css"), "utf8");
const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");
const TODO = RENDER.slice(RENDER.indexOf("function renderTodo"), RENDER.indexOf("function renderCompact"));
// the delegated Dismiss handler, bounded at the body delegate's close (never to end-of-file)
const DISMISS_AT = RENDER.indexOf("utdismiss: (elx) => {");
const HANDLER = RENDER.slice(DISMISS_AT, RENDER.indexOf("\n  });\n})();", DISMISS_AT));
const ARM_AT = HANDLER.indexOf("if (!utArmed.has(tid)) {");
const ARM_END = HANDLER.indexOf("\n        return;", ARM_AT);
const ARM = ARM_AT >= 0 && ARM_END > ARM_AT ? HANDLER.slice(ARM_AT, ARM_END) : "";
const CONFIRM = ARM_END > 0 ? HANDLER.slice(ARM_END) : "";
const MODAL_AT = RENDER.indexOf("function showUserTodoReply");
const MODAL = MODAL_AT > 0 ? RENDER.slice(MODAL_AT, RENDER.indexOf("\nfunction ", MODAL_AT + 10)) : "";

test("the todo ChatEvent and the session payload both carry the requests", () => {
  assert.match(RENDER, /kind: "todo"; tasks: TodoTask\[\]; userTodos\?: UserTodo\[\]; error\?: string; userTodosError\?: string/);
  assert.match(RENDER, /interface UserTodo \{ id: string; text: string; detail\?: string; createdT\?: number; blocking\?: boolean; queued\?: boolean \}/);
  const session = RENDER.slice(RENDER.indexOf("interface Session {"), RENDER.indexOf("\n", RENDER.indexOf("interface Session {")));
  assert.match(session, /userTodos\?: UserTodo\[\];/);
});

test("the session field merges through the upsert's prev-fallback (the bg-tasks payload idiom)", () => {
  assert.match(RENDER, /userTodos: \("userTodos" in msg\) \? msg\.userTodos : \(prev \? prev\.userTodos : undefined\)/);
});

test("the chatTail delta carries the field on both sides of the wire, and the kernel attaches it only while the switch is on", () => {
  assert.equal((KERNEL.match(/tail\["userTodos"\] = m\.get\("userTodos"\) or \[\]/g) || []).length, 2, "both chatTail frame shapes");
  assert.equal((KERNEL.match(/if _user_todos_on\(\):\s*\n\s*tail\["userTodos"\]/g) || []).length, 2,
    "gated on the switch: an install that never turned it on ships today's bytes");
  const tail = RENDER.slice(RENDER.indexOf("function chatTail"), RENDER.indexOf("\nfunction ", RENDER.indexOf("function chatTail") + 10));
  assert.match(tail, /if \("userTodos" in msg\) \{[^\n]*s\.userTodos = msg\.userTodos;/);
});

test("the kernel ships fixed store values on the field, never a per-build value", () => {
  assert.match(KERNEL, /"userTodos": _user_todos_open/);
  const helper = KERNEL.slice(KERNEL.indexOf("def _open_user_todos(sid):"), KERNEL.indexOf("def _user_todo_session_ended"));
  assert.ok(helper.length > 0, "_open_user_todos exists");
  assert.doesNotMatch(helper, /time\.time\(\)/, "no build-time clock reaches the payload");
});

test("the switch needs no client gate: the kernel ships no rows while it is off", () => {
  const helper = KERNEL.slice(KERNEL.indexOf("def _open_user_todos(sid):"), KERNEL.indexOf("def _user_todo_session_ended"));
  assert.match(helper, /if not _user_todos_on\(\):\s+return \[\]/);
  assert.ok(!/userTodos_on|_user_todos_on|userTodosEnabled/.test(RENDER), "no switch logic in the renderer");
});

test("both sections auto-hide when empty", () => {
  assert.match(TODO, /else if \(ev\.tasks\.length\) \{/);
  assert.match(TODO, /if \(uts\.length\) \{/);
});

test("a task-store error still shows the waiting-on-you section (no early return)", () => {
  const returns = TODO.match(/return notice\(/g) || [];
  assert.equal(returns.length, 1, "one exit: the error branch no longer returns before the requests section");
  assert.doesNotMatch(TODO.slice(0, TODO.indexOf("return notice(")), /\n  return\b/, "no earlier exit at the function's own depth");
  assert.ok(TODO.indexOf("if (ev.error)") < TODO.indexOf("Waiting on you"), "the error section precedes the requests");
});

test("a request-store error keeps the agent's checklist and heads its own section", () => {
  assert.match(TODO, /if \(ev\.userTodosError\) \{/);
  assert.ok(TODO.indexOf("if (ev.userTodosError)") > TODO.indexOf("else if (ev.tasks.length)"), "follows the checklist branch");
  const sect = TODO.slice(TODO.indexOf("if (ev.userTodosError)"), TODO.indexOf("return notice("));
  assert.match(sect, /"Waiting on you · unavailable"/, "headed as the section it stands in for");
  assert.match(sect, /el\("div", "ut-head"\)/);
  assert.match(sect, /sev = "err";/, "in the error dress: the severity rides the rail and dot");
  assert.match(sect, /el\("div", "notice-md"\); m\.textContent = ev\.userTodosError;/);
  assert.doesNotMatch(TODO, /if \(ev\.error \|\| ev\.userTodosError\)/, "never merged into the task store's branch");
});

test("reply and dismiss are delegated to the stable root, never per-render listeners", () => {
  assert.match(TODO, /reply\.dataset\.act = "utreply"/);
  assert.match(TODO, /dis\.dataset\.act = "utdismiss"/);
  assert.doesNotMatch(TODO, /reply\.addEventListener|dis\.addEventListener\("click"/, "no per-node click handler");
  assert.match(RENDER, /utreply: \(elx\) => \{/);
  assert.match(RENDER, /utdismiss: \(elx\) => \{/);
  assert.match(RENDER, /uttoggle: \(elx\) => \{/);
  assert.match(RENDER, /utrest: \(elx\) => \{/);
});

test("dismiss arms then confirms in place, posts the op, and removes the row optimistically", () => {
  assert.ok(HANDLER.length > 0, "the utdismiss handler exists and is bounded");
  assert.ok(ARM && CONFIRM, "the handler has an arm branch that returns, then a confirm branch");
  assert.match(ARM, /utArmed\.add\(tid\)/, "the first click arms");
  assert.match(ARM, /paintUtDismiss\(elx, true\)/, "and says so on the button");
  assert.match(CONFIRM, /utArmed\.delete\(tid\)/, "the confirming click disarms");
  assert.match(CONFIRM, /vscodeApi\?\.postMessage\(\{ type: "userTodoDismiss", id: sid, todoId: tid \}\)/);
  assert.match(CONFIRM, /utDropRow\(elx\.closest\("\.ut-item"\)\)/, "the row goes now; the next push confirms");
});

test("the armed state is keyed, never on the node: the card rebuilds on every push while the session streams", () => {
  assert.match(RENDER, /const utArmed = new Set<string>\(\)/);
  assert.match(TODO, /paintUtDismiss\(dis, utArmed\.has\(t\.id\)\)/, "renderTodo repaints the arm from the Set");
  assert.match(HANDLER, /if \(!utArmed\.has\(tid\)\) \{/, "the handler reads the Set, never the node's class");
  assert.doesNotMatch(HANDLER, /classList\.contains\("armed"\)/);
  assert.match(RENDER, /const utDisarmers = new Map<string, EventListener>\(\)/);
  assert.match(HANDLER, /utDisarmers\.set\(tid, disarm\)/);
  assert.match(HANDLER, /closest\?\.\(`\[data-act="utdismiss"\]\[data-tid="\$\{tid\}"\]`\)\) return;/,
    "a press ON the button, this node or the rebuild that replaced it, leaves the arm and the listener alone");
  assert.doesNotMatch(HANDLER, /ev\.target === elx/);
});

test("the two-step dismiss completes on coarse pointers (no hover to leave)", () => {
  assert.match(TODO, /if \(!isCoarsePointer\(\)\)\s*\n\s*dis\.addEventListener\("pointerleave"/, "the hover disarm is gated to fine pointers");
  assert.match(HANDLER, /if \(isCoarsePointer\(\)\) \{/);
  assert.match(HANDLER, /document\.addEventListener\("pointerdown", disarm, true\);/);
  const retire = RENDER.slice(RENDER.indexOf("function utRetireDisarmer("), RENDER.indexOf("\n}", RENDER.indexOf("function utRetireDisarmer(")));
  assert.match(retire, /document\.removeEventListener\("pointerdown", one, true\)/);
  assert.match(HANDLER, /\) return;\s*\n\s*utDisarm\(tid\);/, "a press ON the button leaves the arm AND the listener for the click handler to settle");
});

test("a scroll that starts ON the armed button neither disarms nor spends the one-shot", () => {
  const oneShot = HANDLER.slice(HANDLER.indexOf("const disarm = "), HANDLER.indexOf("utDisarmers.set("));
  assert.match(oneShot, /return;/, "the on-button guard RETURNS");
  assert.ok(oneShot.indexOf("return;") < oneShot.indexOf("utDisarm(tid)"), "before the disarm that removes the one-shot");
  const confirm = CONFIRM.slice(0, CONFIRM.indexOf("userTodoDismiss"));
  assert.match(confirm, /utRetireDisarmer\(tid\)/, "the confirm branch retires the armed one-shot before posting the dismiss");
  const disarm = RENDER.slice(RENDER.indexOf("function utDisarm("), RENDER.indexOf("\n}", RENDER.indexOf("function utDisarm(")));
  assert.match(disarm, /utArmed\.delete\(tid\)/);
  assert.match(disarm, /utRetireDisarmer\(tid\)/);
  assert.match(disarm, /paintUtDismiss\(node, false\)/, "a cancel repaints whichever rebuild of the button is on screen");
});

test("a kernel warn re-syncs every view holding a pending removal, only while one is pending", () => {
  assert.match(RENDER, /const utPendingRemoval = new Map<string, string>\(\)/);
  assert.match(MODAL, /utPendingRemoval\.set\(todoId, sid\)/, "Reply's send marks the id pending, with its session");
  assert.match(CONFIRM, /utPendingRemoval\.set\(tid, sid\)/, "Dismiss's confirm marks the id pending, with its session");
  assert.equal((RENDER.match(/utPendingRemoval\.set\(/g) || []).length, 2, "the two removal sites, no other writer");
  const warn = RENDER.slice(RENDER.indexOf('m.type === "warn"'), RENDER.indexOf('m.type === "err"'));
  assert.match(warn, /if \(utPendingRemoval\.size\) \{/, "gated on the pending set");
  assert.match(warn, /for \(const sid of new Set\(utPendingRemoval\.values\(\)\)\) \{ const v = views\.get\(sid\); if \(v\) v\.stale = true; \}/);
  assert.match(warn, /appendActive\(\)/, "the active view rebuilds now; a hidden one rebuilds on its next switch");
  assert.match(warn, /utPendingRemoval\.clear\(\)/, "the re-sync settles whatever was pending");
  const settle = RENDER.slice(RENDER.indexOf("function utSettlePending("), RENDER.indexOf("\n}", RENDER.indexOf("function utSettlePending(")));
  assert.match(settle, /utPendingRemoval\.delete\(/);
  const tail = RENDER.slice(RENDER.indexOf("function chatTail"), RENDER.indexOf("\nfunction ", RENDER.indexOf("function chatTail") + 10));
  assert.match(tail, /utSettlePending\(s\.userTodos, msg\.userTodos\)/, "the chatTail delta settles it");
  const up = RENDER.slice(RENDER.indexOf("function upsert("), RENDER.indexOf("\nfunction ", RENDER.indexOf("function upsert(") + 10));
  assert.match(up, /utSettlePending\(prev\.userTodos, msg\.userTodos\)/, "and so does a full session frame");
});

test("optimistic removal keeps the heading's count honest: one helper for both sites", () => {
  const helper = RENDER.slice(RENDER.indexOf("function utDropRow("), RENDER.indexOf("\n}", RENDER.indexOf("function utDropRow(")));
  assert.ok(helper.length > 0, "utDropRow exists");
  assert.match(helper, /row\.remove\(\)/);
  assert.match(helper, /querySelectorAll\("\.ut-item"\)\.length/, "recounts the rows left in the same card");
  assert.match(helper, /head\.textContent = `Waiting on you · \$\{n\}`/, "rewrites the heading the way renderTodo paints it");
  assert.match(helper, /head\.remove\(\)/, "and drops it with the last row");
  assert.equal((RENDER.match(/utDropRow\(/g) || []).length, 3, "the definition plus the two removal sites");
  assert.doesNotMatch(RENDER, /closest\("\.ut-item"\)\?\.remove\(\)/, "no site removes a row on its own");
  assert.match(helper, /if \(!card\.childElementCount\) \(card\.closest\("\.turn-todo"\) as HTMLElement \| null\)\?\.style\.setProperty\("display", "none"\)/);
  assert.doesNotMatch(helper, /turn-todo"\)[^\n]*\.remove\(\)/, "hidden, not removed");
});

// ── the card, executed ───────────────────────────────────────────────────────────────────────────────

/** A render.ts slice, transpiled (TS to JS) with esbuild at run time and required dynamically so the test bundle
 *  does not bundle esbuild itself (the chat-exact-tail-exec.test.ts pattern). */
function liftBetween(startAnchor: string, endAnchor: string): string {
  const a = RENDER.indexOf(startAnchor), b = RENDER.indexOf(endAnchor, a);
  assert.ok(a > 0 && b > a, `anchors not found: ${startAnchor.slice(0, 40)} or ${endAnchor.slice(0, 40)} moved; re-anchor`);
  return requireCjs("esbuild").transformSync(RENDER.slice(a, b), { loader: "ts" }).code;
}

type Compound = { tag: string | null; classes: string[]; attrs: [string, string | null][] };
function parseCompound(s: string): Compound {
  const c: Compound = { tag: null, classes: [], attrs: [] };
  const re = /^([a-z][\w-]*)|\.([\w-]+)|\[([\w-]+)(?:="([^"]*)")?\]/y;
  let last = 0;
  for (let m = re.exec(s); m; m = re.exec(s)) {
    if (m[1]) c.tag = m[1]; else if (m[2]) c.classes.push(m[2]); else c.attrs.push([m[3], m[4] ?? null]);
    last = re.lastIndex;
  }
  if (last !== s.length) throw new Error("unsupported selector " + s);
  return c;
}

/** Enough of Element for el(), notice(), renderTodo and utDropRow: a class list, children, a dataset, text, an inline
 *  style, and closest / querySelector / querySelectorAll over class and data-attribute selectors with the descendant
 *  combinator. Assertions compare primitives read off the tree, never a node: a failing deep comparison over
 *  parent-linked nodes is what node's differ chokes on. */
class FakeEl {
  childNodes: FakeEl[] = []; parentNode: FakeEl | null = null;
  get parentElement(): FakeEl | null { return this.parentNode; }
  classes = new Set<string>(); dataset: Record<string, string> = {}; attrs: Record<string, string> = {};
  textContent = ""; title = ""; type = ""; placeholder = ""; rows = 0; value = ""; tabIndex = -1;
  listeners: Record<string, ((ev: any) => void)[]> = {};
  style: { props: Record<string, string>; setProperty: (k: string, v: string) => void };
  constructor(public tagName: string) {
    const props: Record<string, string> = {};
    this.style = { props, setProperty: (k, v) => { props[k] = v; } };
  }
  get className(): string { return [...this.classes].join(" "); }
  set className(v: string) { this.classes = new Set(v.split(/\s+/).filter(Boolean)); }
  get classList() {
    const c = this.classes;
    return {
      add: (...ks: string[]) => { for (const k of ks) c.add(k); },
      remove: (...ks: string[]) => { for (const k of ks) c.delete(k); },
      contains: (k: string) => c.has(k),
      toggle: (k: string, force?: boolean) => { const on = force ?? !c.has(k); if (on) c.add(k); else c.delete(k); return on; },
    };
  }
  get childElementCount(): number { return this.childNodes.length; }
  appendChild(c: FakeEl): FakeEl { c.parentNode?.removeChild(c); c.parentNode = this; this.childNodes.push(c); return c; }
  append(...cs: FakeEl[]): void { for (const c of cs) this.appendChild(c); }
  removeChild(c: FakeEl): void { this.childNodes = this.childNodes.filter((x) => x !== c); c.parentNode = null; }
  remove(): void { this.parentNode?.removeChild(this); }
  setAttribute(k: string, v: string): void { this.attrs[k] = v; if (k.startsWith("data-")) this.dataset[k.slice(5)] = v; }
  getAttribute(k: string): string | null {
    if (k.startsWith("data-")) { const d = k.slice(5).replace(/-([a-z])/g, (_, ch: string) => ch.toUpperCase()); return d in this.dataset ? this.dataset[d] : null; }
    return k in this.attrs ? this.attrs[k] : null;
  }
  addEventListener(type: string, f: (ev: any) => void): void { (this.listeners[type] ??= []).push(f); }
  /** A keydown on this node, as the browser would deliver it; returns whether a listener called preventDefault. */
  keydown(key: string): boolean { const ev = { key, defaultPrevented: false, preventDefault() { ev.defaultPrevented = true; }, target: this }; for (const f of this.listeners.keydown ?? []) f(ev); return ev.defaultPrevented; }
  /** The body delegate's road: a click walks up to the nearest [data-act] and runs the action (the test installs them). */
  click(): void { for (let n: FakeEl | null = this; n; n = n.parentNode) { const act = n.dataset.act; if (act && DELEGATES[act]) { DELEGATES[act](n); return; } } }
  matchesCompound(c: Compound): boolean {
    if (c.tag && c.tag !== this.tagName) return false;
    for (const k of c.classes) if (!this.classes.has(k)) return false;
    for (const [name, value] of c.attrs) { const v = this.getAttribute(name); if (v === null) return false; if (value !== null && v !== value) return false; }
    return true;
  }
  matches(sel: string): boolean {
    const parts = sel.trim().split(/\s+/).map(parseCompound);
    if (!this.matchesCompound(parts[parts.length - 1])) return false;
    let anc: FakeEl | null = this.parentNode;
    for (let i = parts.length - 2; i >= 0; i--) {
      while (anc && !anc.matchesCompound(parts[i])) anc = anc.parentNode;
      if (!anc) return false;
      anc = anc.parentNode;
    }
    return true;
  }
  closest(sel: string): FakeEl | null { for (let n: FakeEl | null = this; n; n = n.parentNode) if (n.matches(sel)) return n; return null; }
  querySelector(sel: string): FakeEl | null { for (const e of this.walk()) if (e.matches(sel)) return e; return null; }
  querySelectorAll(sel: string): FakeEl[] { return [...this.walk()].filter((e) => e.matches(sel)); }
  *walk(): Generator<FakeEl> { for (const c of this.childNodes) { yield c; yield* c.walk(); } }
}

const DELEGATES: Record<string, (elx: FakeEl) => void> = {};   // the delegated actions a test lifts (uttoggle), keyed by data-act
type Row = { id: string; text: string; detail?: string; blocking?: boolean; queued?: boolean };
type Task = { subject: string; status: string; activeForm?: string };
type Lifted = { renderTodo: (ev: { kind: "todo"; tasks: Task[]; userTodos: Row[] }) => FakeEl; utDropRow: (row: FakeEl | null) => void };
/** el(), notice(), paintUtDismiss and the run from utDropRow through renderTodo, lifted from render.ts and run over the
 *  fake DOM. The module state they read and the helpers beside the point are stubbed. */
function liftTodoCard(opts: { openFolds?: string[] } = {}): Lifted {
  const elFn = liftBetween("function el(tag: string, cls?: string): HTMLElement {", "\n// ONE sanitizer for both renderers");
  const noticeFn = liftBetween("function notice(spec: NoticeSpec): HTMLElement {", "\n// A word button for a notice's action slot");
  const paint = liftBetween("function paintUtDismiss(node: HTMLElement, armed: boolean): void {", "function utRetireDisarmer(");
  const todo = liftBetween("function utDropRow(row: Element | null): void {", "\nfunction todoFoldLabel(");
  const prelude = `
    const W = WORLD;
    const document = { createElement: (tag) => new W.FakeEl(tag) };
    const openFolds = new Set(W.openFolds), noticeSeeded = new Set();
    const applyFold = (target, cls, key) => { if (key && openFolds.has(key)) target.classList.add(cls); };
    const dot = (kind) => el("span", "dot " + kind);
    const noticeGlyph = (kind) => el("span", "notice-glyph notice-glyph-" + kind);
    const setTip = () => {};
    let renderingSid = W.sid;
    const utArmed = new Set(), utDetailOpen = new Set();
    const isCoarsePointer = () => false;
    const linkifyFileUris = () => {};
    const todoFoldLabel = () => {};
    const UT_INLINE_ROWS = 12;
  `;
  // the delegated uttoggle action (the body delegate's member), lifted with the card so the keyboard road can run it; a
  // bare object member is not a program, so it is wrapped in a literal before the transpile
  const t0 = RENDER.indexOf("uttoggle: (elx) => {"), t1 = RENDER.indexOf("utreply: (elx) => {", t0);
  assert.ok(t0 > 0 && t1 > t0, "anchors not found: the uttoggle or utreply delegate moved; re-anchor");
  const acts = requireCjs("esbuild").transformSync("const ACTS = { " + RENDER.slice(t0, t1) + " };", { loader: "ts" }).code;
  const make = new Function("WORLD", prelude + elFn + noticeFn + paint + todo + "\n" + acts + "\nW.DELEGATES.uttoggle = ACTS.uttoggle;\nreturn { renderTodo, utDropRow };") as
    (w: { FakeEl: typeof FakeEl; sid: string; openFolds: string[]; DELEGATES: typeof DELEGATES }) => Lifted;
  return make({ FakeEl, sid: "web", openFolds: opts.openFolds || [], DELEGATES });
}

function todoCard(rows: Row[], tasks: Task[] = [], opts: { openFolds?: string[] } = {}) {
  const api = liftTodoCard(opts);
  const turn = api.renderTodo({ kind: "todo", tasks, userTodos: rows });
  return {
    turn,
    gist: () => turn.querySelector(".notice-gist")?.textContent ?? null,
    head: () => turn.querySelector(".ut-head")?.textContent ?? null,
    items: () => turn.querySelectorAll(".ut-item").length,
    listCount: () => turn.querySelector(".todo-list")?.childElementCount ?? -1,
    hidden: () => turn.style.props.display === "none",
    row: (id: string) => turn.querySelector(`.ut-item [data-tid="${id}"]`)?.closest(".ut-item") ?? null,
    drop: (id: string) => api.utDropRow(turn.querySelector(`.ut-item [data-tid="${id}"]`)?.closest(".ut-item") ?? null),
  };
}

test("executed: removing a row recounts the section head AND the notice head's gist; the last row hides the notice", () => {
  const c = todoCard([{ id: "u1", text: "which name for the new tab" }, { id: "u2", text: "ok to delete the old branch" }]);
  assert.equal(c.turn.classList.contains("turn-todo"), true, "renderTodo rendered the to-do turn");
  assert.equal(c.items(), 2);
  assert.equal(c.head(), "Waiting on you · 2");
  assert.equal(c.gist(), "waiting on you · 2", "with no checklist the notice head names the section");
  c.drop("u9");
  assert.equal(c.items(), 2, "an id the card does not hold removes nothing");
  c.drop("u1");
  assert.equal(c.items(), 1, "the row goes now");
  assert.equal(c.head(), "Waiting on you · 1", "the section head follows the count");
  assert.equal(c.gist(), "waiting on you · 1", "and so does the notice head");
  assert.equal(c.hidden(), false);
  c.drop("u2");
  assert.equal(c.items(), 0);
  assert.equal(c.head(), null, "the section head goes with the last row");
  assert.equal(c.listCount(), 0, "nothing is left in the list");
  assert.equal(c.hidden(), true, "the empty notice is hidden until the next push replaces it");
  assert.doesNotMatch(c.gist() || "", /· 0$/, "never a zero count on the notice head");
});

test("executed: with a checklist standing, the notice head keeps its 'n of m done' and the notice stays up after the last row", () => {
  const c = todoCard([{ id: "u1", text: "which name for the new tab" }, { id: "u2", text: "ok to delete the old branch" }],
                     [{ subject: "write the tests", status: "pending" }]);
  assert.equal(c.gist(), "0 of 1 done");
  assert.equal(c.listCount(), 4, "one checklist row, the section head, two rows");
  c.drop("u1");
  assert.equal(c.head(), "Waiting on you · 1");
  assert.equal(c.gist(), "0 of 1 done", "the notice head is rewritten only when it names the section");
  c.drop("u2");
  assert.equal(c.head(), null);
  assert.equal(c.listCount(), 1, "the checklist row stands");
  assert.equal(c.hidden(), false, "a notice with a checklist stays up");
});

test("executed: a row whose answer is parked reads 'answer queued' in Reply's place, and Dismiss stays", () => {
  const c = todoCard([{ id: "u1", text: "which name for the new tab", queued: true }, { id: "u2", text: "ok to delete the old branch" }]);
  const parked = c.row("u1")!, plain = c.row("u2")!;
  assert.equal(parked.querySelector(".ut-queued")?.textContent, "answer queued");
  assert.equal(parked.querySelector('[data-act="utreply"]'), null, "no Reply while the answer waits in line");
  assert.ok(parked.querySelector('[data-act="utdismiss"]'), "Dismiss stays");
  assert.ok(plain.querySelector('[data-act="utreply"]'), "a plain row keeps its Reply");
  assert.equal(plain.querySelector(".ut-queued"), null);
  assert.equal(c.head(), "Waiting on you · 2", "a parked answer is still an open request");
});

test("executed: a blocking request wears a small mark after the text; a bare row renders nothing extra", () => {
  const c = todoCard([{ id: "u1", text: "which name for the new tab", blocking: true }, { id: "u2", text: "ok to delete the old branch" }]);
  const mark = c.row("u1")!.querySelector(".ut-blocking");
  assert.ok(mark, "the mark exists");
  assert.equal(mark!.textContent, "blocking");
  assert.equal(c.row("u2")!.querySelector(".ut-blocking"), null);
  assert.equal(c.row("u2")!.querySelectorAll(".ut-more").length, 0, "no details hint on a row without detail");
  assert.equal(c.row("u2")!.querySelector(".ut-text")!.textContent, "ok to delete the old branch");
});

test("executed: past twelve open rows the rest hide behind a keyed toggle; at twelve the toggle is absent", () => {
  const rows = (n: number) => Array.from({ length: n }, (_, i) => ({ id: "u" + (i + 1), text: "request " + (i + 1) }));
  const twelve = todoCard(rows(12));
  assert.equal(twelve.items(), 12);
  assert.equal(twelve.turn.querySelector('[data-act="utrest"]'), null, "twelve rows: all inline, no toggle");
  const thirteen = todoCard(rows(13));
  assert.equal(thirteen.items(), 13, "every row is rendered (the count stays honest)");
  const tog = thirteen.turn.querySelector('[data-act="utrest"]')!;
  assert.ok(tog, "the toggle exists");
  assert.equal(tog.textContent, "+ 1 more waiting");
  assert.equal(tog.dataset.nkey, "ut-rest:web", "keyed per session so the state survives re-renders");
  const box = thirteen.turn.querySelector(".ut-rest")!;
  assert.ok(box, "the hidden rows sit in their own block");
  assert.equal(box.querySelectorAll(".ut-item").length, 1, "the thirteenth row is the hidden one");
  assert.equal(box.classList.contains("todo-open"), false, "hidden by default");
  assert.equal(thirteen.items() - box.querySelectorAll(".ut-item").length, 12, "the twelve oldest stay inline");
  assert.equal(thirteen.turn.querySelectorAll(".ut-item")[0].querySelector(".ut-text")!.textContent, "request 1", "oldest first");
  thirteen.drop("u13");
  assert.equal(thirteen.head(), "Waiting on you · 12", "a removal inside the hidden block recounts the head");
  assert.equal(thirteen.turn.querySelector('[data-act="utrest"]'), null, "the last hidden row takes the toggle with it");
  assert.equal(thirteen.turn.querySelector(".ut-rest"), null, "and the empty block");
  assert.equal(thirteen.items(), 12);
  const open = todoCard(rows(14), [], { openFolds: ["ut-rest:web"] });
  const openTog = open.turn.querySelector('[data-act="utrest"]')!;
  assert.equal(openTog.textContent, "hide 2", "an open toggle's label says how many it hides");
  assert.equal(open.turn.querySelector(".ut-rest")!.classList.contains("todo-open"), true, "the keyed state opens it");
  open.drop("u14");
  assert.equal(open.head(), "Waiting on you · 13", "a removal inside the hidden block recounts the head too");
  assert.equal(openTog.textContent, "hide 1", "and the toggle's count follows the rows it still hides");
  assert.equal(openTog.dataset.n, "1", "the delegate's own count too, so a click relabels with the right number");
  open.drop("u1");
  assert.equal(openTog.textContent, "hide 1", "an inline row's removal leaves the toggle alone");
  assert.equal(open.head(), "Waiting on you · 12");
  open.drop("u13");
  assert.equal(open.turn.querySelector('[data-act="utrest"]'), null, "the open block's last row takes its toggle too");
  assert.equal(open.turn.querySelector(".ut-rest"), null);
  assert.equal(open.head(), "Waiting on you · 11");
});

test("executed: the details toggle is keyboard-reachable: the row's text is a focusable button that says whether it is open, and Enter or Space open and close the details through the one delegated action", () => {
  // the text IS the toggle (progressive disclosure: the one-line version by default, detail one click away); a span with a
  // delegated click was reachable by pointer alone, so it gains tabIndex, a role, aria-expanded and a keydown that calls
  // click(), and the delegated uttoggle handler stays the one road (no second handler to drift from it)
  const c = todoCard([{ id: "u1", text: "which name for the new tab", detail: "the two names in play are notes and journal" }, { id: "u2", text: "ok to delete the old branch" }]);
  const txt = c.row("u1")!.querySelector(".ut-text")!, det = c.row("u1")!.querySelector(".ut-detail")!;
  assert.equal(txt.tabIndex, 0, "in the tab order");
  assert.equal(txt.getAttribute("role"), "button");
  assert.equal(txt.getAttribute("aria-expanded"), "false", "closed by default");
  assert.equal(det.classList.contains("open"), false);
  assert.equal(txt.keydown("Enter"), true, "Enter is the toggle's, not the page's");
  assert.equal(det.classList.contains("open"), true, "Enter opened the detail through the delegated action");
  assert.equal(txt.getAttribute("aria-expanded"), "true", "and the state follows");
  assert.equal(txt.querySelector(".ut-more")!.textContent, "▾ details");
  assert.equal(txt.keydown(" "), true);
  assert.equal(det.classList.contains("open"), false, "Space closed it again");
  assert.equal(txt.getAttribute("aria-expanded"), "false");
  assert.equal(txt.keydown("a"), false, "another key is not the toggle's");
  assert.equal(det.classList.contains("open"), false);
  const bare = c.row("u2")!.querySelector(".ut-text")!;
  assert.equal(bare.tabIndex, -1, "a row without detail has nothing to open: not a button");
  assert.equal(bare.getAttribute("role"), null);
  assert.equal(bare.keydown("Enter"), false);
});

test("the toggle past twelve is delegated and relabels through one helper (the checklist's idiom)", () => {
  assert.match(TODO, /const UT_INLINE_ROWS = 12/);
  assert.match(TODO, /uts\.slice\(0, UT_INLINE_ROWS\)/);
  assert.match(TODO, /tog\.dataset\.act = "utrest"; tog\.dataset\.nkey = utRestKey; tog\.dataset\.n = String\(rest\.length\)/);
  assert.match(TODO, /applyFold\(box, "todo-open", utRestKey\)/);
  const helper = RENDER.slice(RENDER.indexOf("function utRestLabel("), RENDER.indexOf("\n}", RENDER.indexOf("function utRestLabel(")));
  assert.match(helper, /open \? `hide \$\{n\}` : `\+ \$\{n\} more waiting`/);
  const handler = RENDER.slice(RENDER.indexOf("utrest: (elx) => {"), RENDER.indexOf("uttoggle: (elx) => {"));
  assert.match(handler, /rememberFold\(box, "todo-open", elx\.dataset\.nkey \|\| undefined\)/);
  assert.match(handler, /utRestLabel\(elx, box\.classList\.contains\("todo-open"\), Number\(elx\.dataset\.n\) \|\| 0\)/);
});

test("a dismissed session takes its keyed state with it", () => {
  const forget = RENDER.slice(RENDER.indexOf("function utForgetSession("), RENDER.indexOf("\n}", RENDER.indexOf("function utForgetSession(")));
  assert.ok(forget.length > 0, "utForgetSession exists");
  assert.match(forget, /if \(utArmed\.has\(t\.id\)\) utDisarm\(t\.id\)/, "an arm goes with its one-shot");
  assert.match(forget, /for \(const \[tid, owner\] of utPendingRemoval\) if \(owner === sid\) utPendingRemoval\.delete\(tid\)/);
  const dismiss = RENDER.slice(RENDER.indexOf("function dismissSession("), RENDER.indexOf("\n}", RENDER.indexOf("function dismissSession(")));
  assert.match(dismiss, /utForgetSession\(id, sessions\.get\(id\)\?\.userTodos\);/);
  assert.ok(dismiss.indexOf("utForgetSession(") < dismiss.indexOf("sessions.delete(id)"), "read before the map forgets the rows");
});

test("reply opens a modal (outside the rebuilt transcript) and posts one answer op", () => {
  assert.match(RENDER, /function showUserTodoReply\(sid: string, todoId: string, todoText: string, todoDetail = ""\): void/);
  assert.match(RENDER, /vscodeApi\?\.postMessage\(\{ type: "userTodoAnswer", id: sid, todoId, text \}\)/);
  assert.match(MODAL, /overlay\.id = "ut-reply-prompt"/, "the confirm chrome, its own id");
  const enterAt = MODAL.indexOf('e.key === "Enter"');
  assert.ok(enterAt > 0, "the modal handles Enter");
  const enter = MODAL.slice(enterAt, MODAL.indexOf("go()", enterAt));
  assert.match(enter, /!e\.shiftKey/, "Shift+Enter keeps a newline");
  assert.match(enter, /!isCoarsePointer\(\)/, "Enter sends on a fine pointer only");
  assert.match(MODAL, /utDropRow\(document\.querySelector\(`\.ut-item \[data-tid="\$\{todoId\}"\]`\)\?\.closest\("\.ut-item"\)/,
    "optimistic: the row goes now, the next push confirms");
  assert.match(TODO, /\(reply as any\)\._utdetail = t\.detail \|\| "";/);
  assert.match(MODAL, /const dd = todoDetail\.trim\(\) \? el\("div", "ut-detail open"\) : null;/);
  assert.match(MODAL, /if \(dd\) box\.appendChild\(dd\)/);
  const handler = RENDER.slice(RENDER.indexOf("utreply: (elx) => {"), RENDER.indexOf("utdismiss: (elx) => {"));
  assert.match(handler, /showUserTodoReply\(sid, tid, \(\(elx as any\)\._uttext as string\) \|\| "", \(\(elx as any\)\._utdetail as string\) \|\| ""\);/);
});

test("the section head, the modal's title and every button word say request, never todo", () => {
  assert.match(TODO, /head\.textContent = `Waiting on you · \$\{uts\.length\}`/);
  assert.match(MODAL, /h\.textContent = "Reply"/);
  for (const lit of (TODO + MODAL).match(/(?:textContent|title|placeholder) = (?:"[^"]*"|`[^`]*`)/g) || [])
    assert.ok(!/todo/i.test(lit), `a user-facing string says todo: ${lit}`);
});

test("detail hides behind a keyed disclosure that survives re-renders (progressive disclosure)", () => {
  assert.match(RENDER, /const utDetailOpen = new Set<string>\(\)/);
  const handler = RENDER.slice(RENDER.indexOf("uttoggle: (elx) => {"), RENDER.indexOf("utreply: (elx) => {"));
  assert.match(handler, /if \(open\) utDetailOpen\.add\(tid\); else utDetailOpen\.delete\(tid\);/);
  assert.match(handler, /det\?\.classList\.toggle\("open", open\);/);
});

test("a row WITH detail says so at a glance; a bare row renders nothing extra", () => {
  assert.match(TODO, /const detail = \(t\.detail \|\| ""\)\.trim\(\);/);
  assert.match(TODO, /if \(detail\) \{\s*\n\s*txt\.classList\.add\("ut-has-detail"\);\s*\n\s*txt\.dataset\.act = "uttoggle"; txt\.dataset\.tid = t\.id;/);
  assert.match(TODO, /const more = el\("span", "ut-more"\); paintUtHint\(more, utDetailOpen\.has\(t\.id\)\); txt\.appendChild\(more\);/);
  assert.doesNotMatch(TODO, /more\.addEventListener|more\.onclick|more\.dataset\.act/);
  assert.match(TODO, /if \(detail\) \{\s*\n\s*const d = el\("div", "ut-detail"/, "the detail body renders on the same gate");
  assert.match(RENDER, /\{ text: "▾ details", title: "click to hide the details" \}/);
  assert.match(RENDER, /\{ text: "▸ details", title: "has details: click to read" \}/);
  assert.match(RENDER, /node\.textContent = h\.text; node\.title = h\.title; node\.setAttribute\("aria-label", h\.title\);/);
  const handler = RENDER.slice(RENDER.indexOf("uttoggle: (elx) => {"), RENDER.indexOf("utreply: (elx) => {"));
  assert.match(handler, /const more = elx\.querySelector<HTMLElement>\("\.ut-more"\);\s*\n\s*if \(more\) paintUtHint\(more, open\);/);
  assert.match(handler, /elx\.title = utHint\(open\)\.title;/);
});

test("detail renders as plain text, with paths clickable the way a transcript's are", () => {
  const detailBlock = TODO.slice(TODO.indexOf('el("div", "ut-detail"'));
  assert.match(detailBlock, /d\.textContent = t\.detail \|\| "";\s*\n\s*linkifyFileUris\(d\);/);
  assert.doesNotMatch(TODO, /innerHTML|md\(/, "no markdown render on the card");
});

test("the waiting-on-you styles reuse the todo card vocabulary", () => {
  assert.match(CSS, /\.ut-head \{/);
  assert.match(CSS, /\.ut-item \{/);
  assert.match(CSS, /\.ut-detail \{ display: none;/);
  assert.match(CSS, /\.ut-detail\.open \{ display: block; \}/);
  assert.match(CSS, /\.ut-dismiss\.armed \{ border-color: var\(--err\); color: var\(--err\); \}/);
  assert.match(CSS, /\.ut-rest \{ display: none; \}/);
  assert.match(CSS, /\.ut-rest\.todo-open \{ display: block; \}/);
  const bad = (CSS.match(/\.ut-reply-input\.bad \{[^}]*\}/) || [""])[0];
  assert.ok(bad, ".ut-reply-input.bad rule exists");
  assert.match(bad, /border-color: var\(--err\)/);
  assert.doesNotMatch(bad, /#[0-9a-f]{3,8}\b/i, "tokens only");
  const rule = (CSS.match(/\.ut-more \{[^}]*\}/) || [""])[0];
  assert.ok(rule, ".ut-more rule exists");
  assert.match(rule, /font-size: 0\.72em;/);
  assert.match(rule, /color: var\(--dim\);/);
  assert.doesNotMatch(rule, /#[0-9a-f]{3,8}\b|var\(--accent/i, "tokens only, and not the accent");
  // the queued word and the blocking mark are dim words in the row's chrome rung: no colour of status
  for (const sel of [".ut-queued", ".ut-blocking"]) {
    const r = (CSS.match(new RegExp(sel.replace(".", "\\.") + " \\{[^}]*\\}")) || [""])[0];
    assert.ok(r, sel + " rule exists");
    assert.match(r, /font-size: 0\.72em;/);
    assert.match(r, /color: var\(--dim\);/);
    assert.doesNotMatch(r, /--st-|--err|--accent|#[0-9a-f]{3,8}\b/i, sel + " wears no status colour");
  }
  // the tab's request flag arrived with the ambient surfaces (the request flag widget of tab-widgets.ts); its rule is
  // pinned in tab-usertodo.test.ts and is not this card's business beyond existing
  assert.ok(/\.tab-usertodo \{/.test(CSS), "the tab's request flag has its rule");
});
