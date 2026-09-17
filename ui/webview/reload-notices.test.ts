// The notices a page is showing when the reload core takes it (reload-notices.ts). The core's restart reload follows
// the last pending ship's retirement on the next task (render.ts endReloadHoldIfIdle, __rompReload.ended()), and the
// nack, the dismissal or the other-tab ack raised in that same task is appended one task before the page goes: the
// toast was never read, and the fresh page's loss toast reads shipsInFlight, which the retirement already emptied. So
// render.ts keeps the texts of the toasts on screen in this tab's sessionStorage on the core's synchronous hook and the
// fresh page shows them once. The readings are pure and execute here. render.ts has import-time DOM side effects, so
// its wiring is pinned to source the way reload-restore.test.ts pins the scroll record's, and the toast family with the
// refusals that report a state (the staging refusals, the branch jump's, the send on a disconnected host, the send into
// a tab whose create failed, the queued edit's send on a session that cannot be reached) is lifted out of it and
// executed over a fake DOM the way chat-exact-tail-exec.test.ts lifts chatTail. The served scenario (a nack on the last
// ship across a kernel restart; the fresh page says it again, once) is tests/test_ship_reship_served.py
// NackNoticeSurvivesReload. Synthetic only.
//
// This fork's file also carries the chat page's HOLD on the reload core (the three cases after the notices). The file
// and its module were reload-hold.test.ts / reload-hold.ts until the 2026-09-09 fold, slice 2, when upstream's #1134
// took that name for its hold-reason module (ui/webview/reload-hold.ts, tested by reload-hold.test.ts); upstream's
// #1217 then landed the notices module under this name, and the file follows its text. The hold is upstream's T272
// shape: render.ts answers the core's window.__rompPaneBusy ('upload' while a ship whose ack can still arrive awaits
// it, 'held-send' while the ship gate holds a send) and tells it the ending event through window.__rompReload.ended();
// the fork's 60 s deadline stays in the core as the backstop behind that event (the fold's ruling; the last case here
// pins its shape, tests/test_dashboard_auto_reload.py UploadHoldExecuted runs it) and hands the pane a release note,
// which persistNoticesForReload appends to the kept list (reload-notices.ts releasedNotices, the one divergence from
// upstream's module). The hold's wiring is pinned to source in render.ts and in the core's busyHere; the core's own
// deferral runs in node in tests/test_dashboard_auto_reload.py; the served order (the heal, then the reload) is
// tests/test_ship_reship.py ServedWedge.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { RELOAD_NOTICES_KEY, liveNotices, releasedNotices, keepReloadNotices, takeReloadNotices } from "./reload-notices";
import { mintProvisionalId, isProvisionalId } from "./provisional";
import { hideEdges } from "../test-dom-shim";

const requireCjs = createRequire(__filename);
const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");

const SEL = ".warn-toast:not([data-ephemeral]) .warn-toast-msg";
const box = (texts: (string | null)[]) => ({
  querySelectorAll: (sel: string) => { assert.equal(sel, SEL); return texts.map((t) => ({ textContent: t })); },
});

/** A sessionStorage stand-in: the three calls the module makes over a Map, with a log of them. */
function fakeStore(init: Record<string, string> = {}) {
  const m = new Map(Object.entries(init));
  const calls: string[] = [];
  return {
    m, calls,
    getItem: (k: string) => { calls.push("get " + k); return m.has(k) ? m.get(k)! : null; },
    setItem: (k: string, v: string) => { calls.push("set " + k); m.set(k, v); },
    removeItem: (k: string) => { calls.push("remove " + k); m.delete(k); },
  };
}

test("the toasts on screen read as their texts, in order, blanks dropped; none without the container", () => {
  assert.deepEqual(liveNotices(null), [], "the container is created by the first toast; none yet");
  assert.deepEqual(liveNotices(undefined), []);
  assert.deepEqual(liveNotices(box([])), []);
  assert.deepEqual(liveNotices(box(["shot.png couldn't be saved on the kernel, so it was not attached. Your message was NOT sent.",
                                    "  ", null, "The pending upload was dismissed. Your held message was NOT sent."])),
    ["shot.png couldn't be saved on the kernel, so it was not attached. Your message was NOT sent.",
     "The pending upload was dismissed. Your held message was NOT sent."]);
  assert.deepEqual(liveNotices(box(["  padded  "])), ["padded"], "the text as the toast shows it");
});

test("the reading asks for the toasts without the ephemeral mark: a refusal about a state the fresh page shows for itself stays behind", () => {
  // a refusal that reports a state (the staged sends' "Can't send yet": the host unreachable, the tab still being
  // created; the plain send on a disconnected host; the send into a tab whose create failed; the queued edit's send on
  // a session that cannot be reached; the staging refusals; the branch jump to a session not on this dashboard) is
  // about something the fresh page shows for itself or no longer has; render.ts marks those toasts where they are
  // raised (executed below) and the selector skips the mark. The mark's effect on a real DOM is executed by
  // tests/test_ship_reship_served.py NackNoticeSurvivesReload.
  const asked: string[] = [];
  assert.deepEqual(liveNotices({ querySelectorAll: (sel: string) => { asked.push(sel); return [{ textContent: "kept" }]; } }), ["kept"]);
  assert.deepEqual(asked, [SEL]);
});

test("the record is kept only when there is something to say; a page with no toast clears a record left behind", () => {
  const s = fakeStore();
  keepReloadNotices(s, ["one", "two"]);
  assert.deepEqual([...s.m.entries()], [[RELOAD_NOTICES_KEY, JSON.stringify(["one", "two"])]]);
  assert.equal(RELOAD_NOTICES_KEY, "romp:reloadNotices", "this tab's sessionStorage, beside the scroll record's key");
  // a reload the browser refused leaves the record in place; the next core reload with nothing on screen clears it
  keepReloadNotices(s, []);
  assert.equal(s.m.has(RELOAD_NOTICES_KEY), false, "cleared, not written empty");
  assert.deepEqual(s.calls, ["set " + RELOAD_NOTICES_KEY, "remove " + RELOAD_NOTICES_KEY]);
  keepReloadNotices(null, ["x"]);
  keepReloadNotices(undefined, []);
});

test("the record comes out once: strings only, and the key is gone whatever it held", () => {
  const s = fakeStore({ [RELOAD_NOTICES_KEY]: JSON.stringify(["one", "", 3, null, "two"]), other: "kept" });
  assert.deepEqual(takeReloadNotices(s), ["one", "two"]);
  assert.deepEqual([...s.m.keys()], ["other"], "the key is removed; nothing else is touched");
  assert.deepEqual(takeReloadNotices(s), [], "a second take finds nothing");
  assert.deepEqual(s.calls, ["get " + RELOAD_NOTICES_KEY, "remove " + RELOAD_NOTICES_KEY, "get " + RELOAD_NOTICES_KEY],
    "no record, no removal");
  for (const junk of ["not json", JSON.stringify("a string"), JSON.stringify({ a: 1 }), JSON.stringify(null), ""]) {
    const j = fakeStore({ [RELOAD_NOTICES_KEY]: junk });
    assert.deepEqual(takeReloadNotices(j), [], JSON.stringify(junk) + " reads as none");
    assert.equal(j.m.has(RELOAD_NOTICES_KEY), false, JSON.stringify(junk) + " is still cleared");
  }
  assert.deepEqual(takeReloadNotices(null), []);
  assert.deepEqual(takeReloadNotices(undefined), []);
});

test("kept on the page that reloads, taken on the page that follows: the same texts, then nothing", () => {
  const s = fakeStore();
  const texts = liveNotices(box(["shot.png couldn't be saved on the kernel, so it was not attached. Your message was NOT sent."]));
  keepReloadNotices(s, texts);
  assert.deepEqual(takeReloadNotices(s), texts);
  assert.deepEqual(takeReloadNotices(s), []);
});

test("a store that refuses is left alone: nothing thrown from either side", () => {
  const broken = {
    getItem: () => { throw new Error("SecurityError"); },
    setItem: () => { throw new Error("QuotaExceededError"); },
    removeItem: () => { throw new Error("SecurityError"); },
  };
  assert.doesNotThrow(() => keepReloadNotices(broken, ["x"]));
  assert.doesNotThrow(() => keepReloadNotices(broken, []));
  assert.deepEqual(takeReloadNotices(broken), []);
});

// ── The refusals that report a state, executed ───────────────────────────────────────────────────────────────────────

/** A slice of render.ts between two anchors, transpiled (TS to JS) with esbuild at run time and required dynamically so
 *  the test bundle does not bundle esbuild itself (the chat-exact-tail-exec.test.ts pattern). `wrap` closes a slice
 *  that is not a statement on its own (a property of an object literal) before it is transpiled. */
function liftBetween(startAnchor: string, endAnchor: string, wrap: (ts: string) => string = (s) => s): string {
  const a = RENDER.indexOf(startAnchor), b = RENDER.indexOf(endAnchor, a);
  assert.ok(a > 0 && b > a, `anchors not found: ${startAnchor.slice(0, 40)} or ${endAnchor.slice(0, 40)} moved; re-anchor`);
  return requireCjs("esbuild").transformSync(wrap(RENDER.slice(a, b)), { loader: "ts" }).code;
}

/** Enough of Element for the toast family and the reading: a class, a dataset, children, an id, and the container's
 *  querySelectorAll for the reading's selector shape (.a:not([data-x]) .b), evaluated as the DOM would: a one-word
 *  data attribute names its dataset key as is, whether it was set through dataset or setAttribute. */
class FakeEl {
  children: FakeEl[] = []; parent: FakeEl | null = null; dataset: Record<string, string> = {}; attrs: Record<string, string> = {};
  textContent = ""; title = ""; id = "";
  constructor(public tag: string, public className = "") { hideEdges(this); }   // the projection (ui/test-dom-shim.ts): children and parent are non-enumerable, so a failing assertion dumps no tree
  has(c: string): boolean { return this.className.split(/\s+/).includes(c); }
  appendChild(c: FakeEl): FakeEl { c.parent?.removeChild(c); c.parent = this; this.children.push(c); return c; }
  append(...cs: FakeEl[]): void { for (const c of cs) this.appendChild(c); }
  removeChild(c: FakeEl): void { this.children = this.children.filter((x) => x !== c); c.parent = null; }
  remove(): void { this.parent?.removeChild(this); }
  setAttribute(k: string, v: string): void { this.attrs[k] = v; if (k.startsWith("data-")) this.dataset[k.slice(5)] = v; }
  addEventListener(): void {}
  querySelectorAll(sel: string): FakeEl[] {
    const m = /^\.([\w-]+):not\(\[data-([\w-]+)\]\) \.([\w-]+)$/.exec(sel);
    if (!m) throw new Error("unsupported selector " + sel);
    return this.children.filter((c) => c.has(m[1]) && !(m[2] in c.dataset)).flatMap((c) => c.children.filter((s) => s.has(m[3])));
  }
}
/** document as warnToast uses it: a body to append the container to, getElementById to find it again, a key listener. */
function fakeDocument() {
  const body = new FakeEl("body");
  return { body, getElementById: (id: string) => body.children.find((c) => c.id === id) ?? null, addEventListener: () => {} };
}

/** The page state the lifted closures read: the composer (a typed draft, its citations, a picker waiting, an edit in
 *  progress to a past message or to a queued one, attachments), the session roster, the reach of the active session's
 *  host (hostDown), whether the active session lives on another host (remote: its id wears the host prefix, lab:web,
 *  the shape the disconnected-host refusal names the host from) and the active tab when it is provisional (tab:
 *  "pending", a create still in flight, so its id is the pending provisional id; "failed", a create that failed, so no
 *  create is pending), with what each gesture did recorded. The toasts' timers are recorded and not run, so a toast
 *  stays on screen for the reading. */
function pageWorld(state: { ask?: "custom" | "text" | null; edit?: boolean; files?: string[]; sessions?: string[];
                            hostDown?: boolean; remote?: boolean; tab?: "pending" | "failed" }) {
  const activeId = state.tab ? mintProvisionalId("web") : state.remote ? "lab:web" : "web";
  const roster = (state.sessions || []).map((id): [string, { id: string; name: string }] => [id, { id, name: id }]);
  if (state.tab || state.remote) roster.push([activeId, { id: activeId, name: "web" }]);
  return {
    FakeEl, document: fakeDocument(), timers: [] as number[],
    activeId, ta: { value: "what did the tests say", style: {} as Record<string, string> },
    composerCitations: new Map<string, { quote?: string }[]>(), ask: state.ask ?? null,
    composerEdits: new Map<string, { uuid: string; orig: string }>(state.edit ? [[activeId, { uuid: "e1", orig: "the old text" }]] : []),
    composerFiles: new Map<string, string[]>(state.files ? [[activeId, state.files]] : []),
    staged: [] as [string, unknown][], persists: 0,
    sessions: new Map<string, { id: string; name: string }>(roster),
    activated: [] as [string, string | undefined][],
    hostDown: !!state.hostDown, posted: [] as { type: string }[],
    isProvisionalId, provisionalId: state.tab === "pending" ? activeId : null, provisionalQueue: [] as string[],
    lastSent: new Map<string, string>(),
  };
}
type World = ReturnType<typeof pageWorld>;
type Lifted = { stageComposer: () => void; branchjump: (elx: { dataset: Record<string, string> }) => void; warnToast: (msg: string) => FakeEl;
                deliver: (sid: string, text: string, attached: string[]) => void };

/** warnToast and ephemeralWarnToast; stageComposer (the composer's staging, whose refusals say a picker is waiting on
 *  the composer, an edit is in progress to a past or a queued message, attachments are on the composer); the branch
 *  jump's delegated handler (whose refusal says the session is not on this dashboard); the refusing head of the send's
 *  deliver (the disconnected-host branch, whose refusal says the host is disconnected and asks for a re-dial, and the
 *  provisional branch, whose refusal says the tab's session never started), through the first step of a send that
 *  passed both guards (lastSent remembers the text), so a refusal that fell through would show as a remembered send;
 *  and the queued message's in-place Save (whose refusal says the session cannot be reached, so the edit was not saved),
 *  lifted from render.ts and run over the world. */
function liftToastSites(): (w: World) => Lifted {
  const toasts = liftBetween("function warnToast(msg: string): HTMLElement {", "// Tail-windowing (see the View comment)");
  const stage = liftBetween("const stageComposer = () => {", "const sendComposer = (");
  const jump = liftBetween("branchjump: (elx) => {", "// a below-response fork spot", (ts) => "const handlers = {\n" + ts + "};");
  const send = liftBetween("if (hostIsDown(sid)) {", "// The STAGED run and this message go together", (ts) => "const deliver = (sid, text, attached) => {\n" + ts + "};");
  const prelude = `
    const W = WORLD;
    const document = W.document;
    const el = (tag, cls) => new W.FakeEl(tag, cls);
    const setTimeout = (fn, ms) => { W.timers.push(ms); return 0; };   // the fade and the removal are not run
    let activeId = W.activeId;
    const ta = W.ta;
    const composerCitations = W.composerCitations;
    const composerAnswersAsk = () => W.ask;
    const composerEdits = W.composerEdits;
    const composerFiles = W.composerFiles;
    const stagedMsgs = { push: (id, s) => { W.staged.push([id, s]); } };
    const renderComposerChips = () => {};
    const drafts = new Map(), draftStartedAt = new Map();
    let composerManualH = null;
    const clearBox = () => { ta.value = ""; composerManualH = null; ta.style.height = ""; };   // the composer's one clear path; its menu refreshes are not lifted (composer-mention-pane.test.ts)
    const persistDrafts = () => { W.persists++; };
    const renderStagedStrip = () => {};
    const sessions = W.sessions;
    const setActive = (sid, cut) => { W.activated.push([sid, cut]); };
    const isProvisionalId = W.isProvisionalId, provisionalId = W.provisionalId, provisionalQueue = W.provisionalQueue;
    const lastSent = W.lastSent;
    const registerOptimistic = () => {}, previewKind = () => null, renderComposerFiles = () => {};
    const sendOnShip = new Set(), histWalk = new Map();
    const hostIsDown = () => W.hostDown;
    const vscodeApi = { postMessage: (m) => { W.posted.push(m); } };
    const SLASH_CMD_RE = /^[/][A-Za-z]/;   // a template literal: the real regex's escaped slash would not survive it
  `;
  return new Function("WORLD", prelude + toasts + stage + jump + send
    + "\nreturn { stageComposer, branchjump: handlers.branchjump, warnToast, deliver };") as (w: World) => Lifted;
}

function page(state: Parameters<typeof pageWorld>[0]) {
  const W = pageWorld(state);
  const api = liftToastSites()(W);
  const box = () => W.document.getElementById("warn-toasts");
  const shown = () => (box()?.children || []).map((t) => t.children[0].textContent);
  return { W, ...api, box, shown };
}
type Page = ReturnType<typeof page>;

const NACK = "shot.png couldn't be saved on the kernel, so it was not attached. Your message was NOT sent.";

test("staging with nothing owning the composer stages: the lifted composer is the real one, and it raises no toast", () => {
  const p = page({});
  p.stageComposer();
  assert.deepEqual(p.W.staged, [["web", { text: "what did the tests say", cites: [] }]]);
  assert.equal(p.W.ta.value, "", "the composer clears");
  assert.equal(p.W.persists, 1);
  assert.equal(p.box(), null, "no toast, so no container");
});

// The refusals that report a STATE rather than an event, raised through their real code paths. Each puts its toast on
// screen for the person at the page and refuses the gesture; the reading skips it, because the fresh page shows that
// state for itself (the picker, the attachments and the roster come back from the kernel and the persisted drafts; the
// host's reach comes back from the kernel's tunnel health and is shown as the tab mark and the transcript foot, and the
// re-dial the disconnected-host refusal speaks of is posted by the gesture, never by a replay) or no longer has it (an
// edit in progress, to a past message or to a queued one, lives in memory alone, so a replay would report an edit the
// fresh page has not got, and its "send again" would post the words as a new message; a provisional tab does not
// survive a reload, so a replay would name a session the fresh page does not show).
const STATE_REFUSALS: { name: string; state: Parameters<typeof pageWorld>[0]; raise: (p: Page) => void; text: string; refused: (p: Page) => void }[] = [
  { name: "staging while a picker waits on the composer", state: { ask: "text" }, raise: (p) => p.stageComposer(),
    text: "A picker is waiting on this box", refused: (p) => assert.deepEqual(p.W.staged, [], "nothing staged") },
  { name: "staging while an edit is in progress", state: { edit: true }, raise: (p) => p.stageComposer(),
    text: "An edit replaces a past message", refused: (p) => assert.deepEqual(p.W.staged, [], "nothing staged") },
  { name: "staging with attachments on the composer", state: { files: ["notes.md"] }, raise: (p) => p.stageComposer(),
    text: "Attachments can't be staged", refused: (p) => assert.deepEqual(p.W.staged, [], "nothing staged") },
  { name: "a branch jump to a session not on this dashboard", state: { sessions: ["web"] }, raise: (p) => p.branchjump({ dataset: { sid: "api" } }),
    text: "That session isn't on this dashboard right now.", refused: (p) => assert.deepEqual(p.W.activated, [], "no switch") },
  { name: "a send while the session's host is unreachable", state: { remote: true, hostDown: true }, raise: (p) => p.deliver(p.W.activeId, p.W.ta.value, []),
    text: "lab is disconnected, so this wasn't sent.", refused: (p) => {
      assert.deepEqual(p.W.posted.map((m) => m.type), ["redial"], "a re-dial of the host is asked for and nothing is sent");
      assert.deepEqual(p.W.provisionalQueue, [], "nothing queued");
      assert.equal(p.W.lastSent.size, 0, "nothing was remembered as sent");
    } },
  { name: "a send into a tab whose create failed", state: { tab: "failed" }, raise: (p) => p.deliver(p.W.activeId, p.W.ta.value, []),
    text: "“web” never started, so there's nowhere to send this.", refused: (p) => {
      assert.deepEqual(p.W.provisionalQueue, [], "nothing queued");
      assert.equal(p.W.lastSent.size, 0, "nothing was remembered as sent");
    } },
];
for (const r of STATE_REFUSALS) {
  test(r.name + ": the refusal is on screen and refuses, and the reading skips it", () => {
    const p = page(r.state);
    r.raise(p);
    const shown = p.shown();
    assert.equal(shown.length, 1, "the refusal put its toast on screen");
    assert.ok(shown[0].startsWith(r.text), shown[0]);
    r.refused(p);
    assert.equal(p.W.ta.value, "what did the tests say", "the draft stays where it was");
    assert.deepEqual(liveNotices(p.box()), [], "a state the fresh page shows for itself, or no longer has, does not ride the reload");
  });
}

test("a toast about what happened, raised beside the refusals, is read: the mark is on the state refusals alone", () => {
  const p = page({ edit: true, sessions: ["web"] });
  p.stageComposer();
  p.warnToast(NACK);
  p.branchjump({ dataset: { sid: "api" } });
  assert.equal(p.shown().length, 3, "all three are on screen for the person at the page");
  assert.deepEqual(liveNotices(p.box()), [NACK]);
});

// The wiring, pinned to source (render.ts executes nothing under node --test).
test("render.ts: warnToast hands back its toast, and the refusals about a state are marked ephemeral where they are raised", () => {
  assert.match(RENDER, /^function warnToast\(msg: string\): HTMLElement \{/m);
  assert.match(RENDER, /setTimeout\(\(\) => t\.remove\(\), 12000\);\n\s*return t;/);
  assert.match(RENDER, /^function ephemeralWarnToast\(msg: string\): void \{ warnToast\(msg\)\.dataset\.ephemeral = "1"; \}/m);
  assert.match(RENDER, /^function ephemeralNoteToast\(msg: string\): void \{ const t = warnToast\(msg\); t\.classList\.add\("note"\); t\.dataset\.ephemeral = "1"; \}/m,
    "the quiet twin (review 2026-09-14): the same toast dressed .note, marked the same way");
  assert.equal((RENDER.match(/dataset\.ephemeral/g) || []).length, 2, "marked at the two ephemeral helpers and nowhere else");
  assert.equal((RENDER.match(/ephemeralWarnToast\("Can't send yet — the session isn't reachable\. They stay staged\."\);/g) || []).length, 2,
    "the staged sends' refusal at both of its sites (the strip's Send now and the empty send)");
  // the staging refusals (stageComposer) and the branch jump's: states the fresh page shows for itself or no longer has
  assert.match(RENDER, /if \(composerAnswersAsk\(\)\) \{ ephemeralWarnToast\("A picker is waiting on this box/);
  assert.match(RENDER, /if \(composerEdits\.has\(activeId\)\) \{ ephemeralWarnToast\("An edit replaces a past message/);
  assert.match(RENDER, /if \(\(composerFiles\.get\(activeId\) \|\| \[\]\)\.length\) \{ ephemeralWarnToast\("Attachments can't be staged/);
  assert.match(RENDER, /if \(!sessions\.get\(sid\)\) \{ ephemeralWarnToast\("That session isn't on this dashboard right now\."\); return; \}/);
  // the send into a tab whose create failed (a provisional tab does not survive a reload): a state the fresh page no
  // longer has
  assert.match(RENDER, /if \(sid !== provisionalId\) \{\n\s*ephemeralWarnToast\("“" \+ \(sessions\.get\(sid\)\?\.name \|\| "this session"\) \+ "” never started, so there's "/);
  // the plain send's refusal on a disconnected host: the host's reach is a state the fresh page reads from the kernel's
  // tunnel health (the tab mark, the transcript foot), and the re-dial that makes "re-dialing now" true is posted by
  // the gesture, never by a replay
  assert.match(RENDER, /if \(hostIsDown\(sid\)\) \{\n\s*const host = String\(sid\)\.slice\(0, String\(sid\)\.indexOf\(":"\)\);\n(\s*\/\/[^\n]*\n)*\s*vscodeApi\?\.postMessage\(\{ type: "redial", host \}\);\n(\s*\/\/[^\n]*\n)*\s*ephemeralWarnToast\(host \+ " is disconnected, so this wasn't sent\. It's still in the box/);
  assert.equal((RENDER.match(/ephemeralWarnToast\(/g) || []).length, 9, "the definition, the two reachability sites and the six state refusals (the queued edit's two went with the in-place editor, T373); the bell toggle's word on the new state is the NOTE twin's (review 2026-09-14), counted below");
  assert.equal((RENDER.match(/ephemeralNoteToast\(/g) || []).length, 2, "the definition and the bell toggle (2026-09-11: a confirmation for a flip whose only other witness is the tab menu's row; a state the fresh page reads from the kernel, so not replayed)");
  // what the nack, the dismissal and the other-tab ack say stays true after the reload, so they ride it unmarked
  assert.match(RENDER, /warnToast\(m\.name \+ " couldn't be saved on the kernel, so it was not attached/);
  assert.match(RENDER, /warnToast\("The pending upload was dismissed — your held message was NOT sent\."\)/);
  assert.match(RENDER, /warnToast\("attachments finished uploading on another tab — the held message was not sent; review it there\."\)/);
});

test("render.ts keeps the notices on the core's hook alone, pagehide keeps the scroll record alone, and the fresh page shows them once after the loss toast", () => {
  assert.match(RENDER, /^import \{ liveNotices, keepReloadNotices, releasedNotices, takeReloadNotices \} from "\.\/reload-notices";/m,
    "upstream's three readings plus this fork's releasedNotices (the core's release note; R-a)");
  // the ONE divergence from upstream's call (R-a, the 4d-1 fold): the core's release note (releasedNotices: the 60 s backstop
  // released a hold that never ended; none when the reload fired on the hold's own event) is appended to the kept list
  assert.match(RENDER, /^function persistNoticesForReload\(\): void \{\n\s*try \{ keepReloadNotices\(sessionStorage, liveNotices\(document\.getElementById\("warn-toasts"\)\)\.concat\(releasedNotices\(\(window as any\)\.__rompReload\)\)\); \} catch \{ \/\* ignore \*\/ \}\n\}/m);
  assert.equal((RENDER.match(/releasedNotices\(/g) || []).length, 1, "the release note is read in that one place");
  // the core's synchronous hook writes both records; a navigation of the user's own (pagehide) writes the scroll record
  // alone, so a load they asked for does not replay a toast they were already looking at
  assert.match(RENDER, /^function persistForReload\(\): void \{ persistScrollForReload\(\); persistNoticesForReload\(\); \}[^\n]*\n\(window as any\)\.__rompPersistForReload = persistForReload;\nwindow\.addEventListener\("pagehide", persistScrollForReload\);/m);
  assert.equal((RENDER.match(/persistNoticesForReload\(\)/g) || []).length, 2, "defined once, called from the core's hook alone");
  const scroll = RENDER.match(/^function persistScrollForReload\(\): void \{([\s\S]*?)\n\}/m);
  assert.ok(scroll && !scroll[1].includes("Notices"), "the scroll record is untouched");
  // the replay follows the loss toast's block directly: the loss first, then what the last page was saying
  assert.match(RENDER, /shipsInFlight: \[\] \}\);\n\s*\}\n\s*\}\n\} catch \{ \/\* ignore \*\/ \}\n(\/\/[^\n]*\n)*try \{ for \(const text of takeReloadNotices\(sessionStorage\)\) warnToast\(text\); \} catch \{ \/\* ignore \*\/ \}/);
  assert.equal((RENDER.match(/takeReloadNotices\(/g) || []).length, 1, "consumed once, at load");
  assert.equal((RENDER.match(/keepReloadNotices\(/g) || []).length, 1, "written from one place");
});

// The chat page's HOLD on the reload core (this fork's cases; see the header). RETIRED at the 2026-09-09 upstream fold
// (the auto-reload series ruling): the fork's publishReloadHold truth table (window.__rompReloadHold) had no reader once the
// core asked the pane's window.__rompPaneBusy instead; the hold's truth is the first case below.
test("render.ts holds the reload through the core's own question: 'upload' while a ship whose ack can still arrive awaits it, 'held-send' while the ship gate holds a send, and tells the core the ending event", () => {
  // re-aimed from the fork's four publishReloadHold publishes (the same fold ruling as the retirement above): the shim's
  // reasons first, then the pane's two, read by the core at every tryFire instead of published at every change. Re-aimed
  // again at the 2026-09-09 fold (slice 2, upstream #1134; R4, the pin follows the resolved code): the pane's two reasons
  // come from reload-hold.ts reloadHoldReason, which answers 'upload' only for a ship whose host can still deliver the
  // ack (reload-hold.test.ts pins its table); the words handed to the core are unchanged, so the core's 60 s backstop
  // (the last test here) clocks the same words
  assert.match(RENDER, /const shimBusy = \(window as any\)\.__rompPaneBusy as \(\(\) => string\) \| undefined;\n\s*\(window as any\)\.__rompPaneBusy = \(\): string => \{\n\s*const b = shimBusy \? shimBusy\(\) : "";\n\s*if \(b\) return b;\n(?:\s*\/\/[^\n]*\n)*\s*return reloadHoldReason\(\[\.\.\.pendingShips\.keys\(\)\], shipGateSid, \(window as any\)\.__rompFed\);\n\s*\};/,
    "the pane wraps the shim's word and answers its own two reasons after it, through reload-hold.ts's reason");
  assert.match(RENDER, /^import \{ reloadHoldReason \} from "\.\/reload-hold";/m, "upstream's hold module beside this one");
  assert.ok(!/return "upload";|return "held-send";/.test(RENDER), "the pane's own two-line answer is gone: the reason is the module's");
  assert.equal((RENDER.match(/\(window as any\)\.__rompPaneBusy/g) || []).length, 2, "read once, assigned once: the wrapper is the one place the pane touches the word (comments aside)");
  // the ENDING event: the core re-tries only on gesture ends, blur, a fresh request or the shell's poll, so the pane says
  // when its hold is over, and says nothing while a ship or a held send is still pending
  assert.match(RENDER, /^function endReloadHoldIfIdle\(\): void \{\n\s*if \(pendingShips\.size \|\| shipGateSid\) return;\n\s*try \{ \(window as any\)\.__rompReload\?\.ended\?\.\(\); \} catch \{[^\n]*\}\n\}/m);
  // an ack, a nack or a FileReader failure retires a ship
  assert.match(RENDER, /if \(!list\.length\) pendingShips\.delete\(id\);\n\s*persistDrafts\(\);\n\s*if \(id === activeId\) renderComposerFiles\(id\);\n\s*endReloadHoldIfIdle\(\);/, "a retired ship");
  // the user dismisses a pending chip (after the settle that clears the gate, so the one call reads both)
  assert.match(RENDER, /if \(!list\.length && id\) pendingShips\.delete\(id\);\n\s*persistDrafts\(\);[^\n]*\n(?:\s*\/\/[^\n]*\n)*\s*if \(id && !\(pendingShips\.get\(id\) \|\| \[\]\)\.length\) \{\n\s*const held = sendOnShip\.delete\(id\);\n\s*const gateWasOpen = shipGateSid === id;\n\s*if \(gateWasOpen\) \{ shipGateSid = null; closeConfirm\(null\); \}\n\s*if \(held \|\| gateWasOpen\) warnToast\([^\n]*\n\s*\}\n\s*endReloadHoldIfIdle\(\);/, "the dismissed chip, after the settle that clears the gate");
  // the ship gate lets go: the last ship's ack fires the held send, a nack cancels it, the user's own pick decides
  assert.match(RENDER, /if \(owner === activeId\) fireHeldSend\(\);\n\s*else warnToast\("attachments finished uploading on another tab[^\n]*\n\s*endReloadHoldIfIdle\(\);/, "the held send posted");
  assert.match(RENDER, /if \(gateWasOpen\) \{ shipGateSid = null; closeConfirm\(null\); \}[^\n]*\n\s*endReloadHoldIfIdle\(\);\n\s*warnToast\(m\.name \+ " couldn't be saved on the kernel/, "the nack");
  assert.match(RENDER, /shipGateSid = null; endReloadHoldIfIdle\(\);\n\s*if \(v === "now"\)/, "the gate's own dialog (composer-ship-gate.test pins the same line)");
  assert.equal((RENDER.match(/endReloadHoldIfIdle\(\)/g) || []).length, 6, "defined once, called at the five ending sites");
  // the fork's word is gone from the page, not published beside the pane's answer
  assert.ok(!RENDER.includes("__rompReloadHold") && !RENDER.includes("publishReloadHold"), "no second hold word");
});

test("the core's release note reads as one notice, and as none from no core, an older core, a silent one or a throwing one", () => {
  // the fold's deadline backstop: the core hands the pane the reason it reloaded over a hold that never ended, through
  // window.__rompReload.released(); persistNoticesForReload appends this reading to the live toasts (the .concat pin in the render.ts case above)
  assert.deepEqual(releasedNotices(null), [], "a page without the core (the VS Code webview)");
  assert.deepEqual(releasedNotices(undefined), []);
  assert.deepEqual(releasedNotices({ request() { /* no released() */ } }), [], "an older core without the accessor");
  assert.deepEqual(releasedNotices({ released: () => "" }), [], "a reload that fired on the hold's own event");
  assert.deepEqual(releasedNotices({ released: () => null }), []);
  assert.deepEqual(releasedNotices({ released: "not a function" }), []);
  assert.deepEqual(releasedNotices({ released: () => { throw new Error("cross-origin"); } }), [], "a foreign parent's refusal is none, not a throw");
  const core = { note: "An upload had not finished after 60 s, so the page reloaded without waiting longer.", released() { return this.note; } };
  assert.deepEqual(releasedNotices(core), [core.note], "read on the core itself (the accessor reaches its shell through the core's own closure)");
});

test("the reload core asks the pane's word after the gesture holds, defers while it answers, re-tries on the pane's ended(), and releases the word at its deadline (the shim's 'sends' excepted)", () => {
  // re-aimed at the 2026-09-09 fold (kernel-code H20-H22, then the fold's ruling on the fork's deadline): the core's busyHere
  // ends on the pane's __rompPaneBusy, after its own reasons (pointer, pan, drag, selection, typing); the fork's 'ships' read
  // and its 500 ms re-check are gone, and its 60 s deadline is the BACKSTOP inside upstream's shape: tryFire runs the word
  // through clock(), which arms one timer for the time left and releases the word past DEADLINE with a console line and the
  // note released() hands the pane. After the fold's review (F1/UI-1, UI-2, F2) and its verification (findings A and D): the
  // clock is the clocked pane word's, read from the paneWord busy()'s walk records; busy() reads each window's gesture
  // (busyHere) and its pane word (paneHere, the window's __rompPaneBusy alone) apart, so a gesture (the GESTURE set) in any
  // window, the word's own pane included, neither clocks nor resets it and only defers a release past the deadline to its
  // own ending event; the shim's 'sends' and the pane's 'upload' (the NOCLOCK set; 'upload' joined it on the user's
  // 2026-09-17 ruling, following upstream: the upload word holds until its own end, the pane's ended() when the last ack
  // lands or the ship gives up) are pane words with no deadline, reported ahead of a clocked word and deferring a release
  // past the deadline like a gesture; a refused reload persists once more without the note;
  // busy() still ranks a gesture anywhere above every pane word for the word it reports (the fold-4 review's K1); the
  // 2026-09-15 pull-in adds upstream's 'fresh' hold beneath every word (a page window's stamps, freshHeld; a pane that
  // answers 'fresh' is asked again for its other holds) and reads a pane detached mid-walk as holding nothing
  const core = KERNEL.slice(KERNEL.indexOf("/*reload-core*/"), KERNEL.indexOf("/*end-reload-core*/"));
  assert.ok(core.length > 0, "the core's anchors exist");
  assert.match(core, /if\(editing\(\)\)return 'typing';\nreturn paneHere\(\);\}\nfunction paneHere\(\)\{try\{if\(window\.__rompPaneBusy\)\{var b=window\.__rompPaneBusy\(\);if\(b\)return String\(b\);\}\}catch\(e\)\{\}return '';\}/,
    "the pane's word is the last reason busyHere gives, and paneHere reads that word alone (the one reader of __rompPaneBusy)");
  assert.equal((core.match(/window\.__rompPaneBusy/g) || []).length, 2, "read in paneHere alone (the existence check and the call)");
  // the 2026-09-09 fold, slice 2 (upstream #1134): inside the deferral the core also tells the page it is held, once per
  // reason and word (heldFor, keyed on owed.reason since the 2026-09-15 pull-in), through R.held; the clock still wraps the word first, so a held reload wears
  // upstream's line at once and the fork's backstop releases it past 60 s. Two mechanisms, no third.
  assert.match(core, /^var heldFor=null;\nfunction tryFire\(\)\{[^\n]*var b=clock\(busy\(\)\);\nif\(b\)\{R\.waiting=b;var hk=owed\.reason\+'\|'\+b;if\(hk!==heldFor\)\{heldFor=hk;if\(R\.held\)R\.held\(b,owed\);\}[^\n]*\nif\(!holdStart\)holdStart=Date\.now\(\);armBackstop\(\);\nreturn;\}R\.waiting='';holdDiag=false;holdStart=0;fire\(\);\}/m,
    "tryFire defers on the word clock() hands back, says which, and tells the held hook once per (reason, word): upstream keys the hold on owed.reason since the 2026-09-15 pull-in (a second restart inside one hold moves the detail without re-announcing), stamps holdStart and arms its own backstop; an empty answer (nothing holds, or the word was released) clears the hold's marks and fires");
  assert.match(core, /,refused:null,held:null,offer:null,waiting:'',/, "the held hook sits on R beside the refusal latch and upstream's offer hook (the 2026-09-16 offer model, taken at the 2026-09-17 fold), unset until a page installs them");
  assert.match(core, /function ended\(\)\{setTimeout\(function\(\)\{var s=shell\(\);if\(s\)s\.tryFire\(\);else tryFire\(\);\},0\);\}/, "the ending event re-tries, in the shell when there is one");
  assert.match(core, /var R=\{request:request,propose:propose,accept:accept,dismiss:dismiss,behind:behind,require:demand,tryFire:tryFire,ended:ended,busyHere:busyHere,paneHere:paneHere,busy:busy,/, "upstream's offer doors (propose, accept, dismiss, behind, require) follow request (the 2026-09-16 offer model); ended() is the pane's door (render.ts endReloadHoldIfIdle calls it); paneHere is the fork's, exported after busyHere, so a shell reads a pane's word behind its gesture");
  // the backstop's shape
  assert.match(core, /^var DEADLINE=60000,heldKind='',heldT=0,heldTimer=null,overdueNote='',paneWord='',GESTURE=\{pointer:1,pan:1,drag:1,selection:1,typing:1\},NOCLOCK=\{sends:1,upload:1\};/m,
    "one deadline, one clock, the clocked pane word behind any gesture, the core's five gesture words exempt, the shim's 'sends' and the pane's 'upload' with no deadline (the upload word holds until its own end: the user's 2026-09-17 ruling, following upstream)");
  assert.match(core, /^function clock\(b\)\{var kind=paneWord;if\(kind!==heldKind\)\{unclock\(\);heldKind=kind;heldT=kind\?Date\.now\(\):0;\}\n/m,
    "the clock is the clocked pane word's whatever busy() reported (paneWord holds only clocked words): a change of pane word (or nothing) resets it");
  assert.match(core, /if\(age<DEADLINE\)\{if\(!heldTimer\)heldTimer=setTimeout\(function\(\)\{heldTimer=null;tryFire\(\);\},DEADLINE-age\);return b;\}\nif\(GESTURE\[b\]\|\|NOCLOCK\[b\]\)return b;/, "one timer for the time left, never a re-check; past the deadline a gesture or a no-deadline word defers the release to its own ending event");
  assert.match(core, /function what\(k\)\{return k==='upload'\?'An upload':k==='held-send'\?'A message held behind an upload':"A '"\+k\+"' hold";\}/, "no note words 'sends': it is never released");
  assert.doesNotMatch(core, /'sends'\?/, "no 'sends' arm in what()");
  assert.match(core, /catch\(e\)\{fired=false;refusedFor=key\(owed\);unclock\(\);if\(overdueNote\)\{overdueNote='';persist\(\);\}R\.waiting='refused';/, "a refused reload drops the note and the clock and persists once more, so the panes' stored toasts drop the note (the fold's review, F2)");
  assert.match(core, /console\.warn\("romp: the '"\+kind\+"' hold did not end within "\+secs\+" s; reloading anyway"\)/, "the console line names the word");
  assert.match(core, /overdueNote=what\(kind\)\+' had not finished after '\+secs\+' s, so the page reloaded without waiting longer\.';/, "the note the pane persists");
  assert.match(core, /^released:function\(\)\{var s=shell\(\);return \(s&&s\.released\)\?s\.released\(\):overdueNote;\},/m, "released() answers with the shell's note when a shell decided");
  assert.match(core, /^function busy\(\)\{var g='',nc='',held='',stamps=\[\];function take\(b,p\)\{if\(b&&GESTURE\[b\]\)\{if\(!g\)g=b;b=p;\}if\(!b\)return;if\(NOCLOCK\[b\]\)\{if\(!nc\)nc=b;\}else if\(!held\)held=b;\}\nvar hold=busyHere\(\);if\(hold==='fresh'\)\{stamps\.push\(freshStamp\(window\)\);hold=busyHere\(true\)\|\|'';if\(hold==='fresh'\)hold='';\}else freshSeenClear\(window\);take\(hold,paneHere\(\)\);var ps=panes\(\);\nfor\(var i=0;i<ps\.length;i\+\+\)\{var r=null,b='';try\{r=ps\[i\]\.__rompReload;b=r\.busyHere\(\)\|\|'';\}catch\(e\)\{b='';\}[^\n]*\nif\(b==='fresh'\)\{stamps\.push\(freshStamp\(ps\[i\]\)\);b=otherHold\(ps\[i\]\);\}else freshSeenClear\(ps\[i\]\);var p='';try\{p=\(r&&r\.paneHere\)\?r\.paneHere\(\):'';\}catch\(e\)\{p='';\}take\(b,p\);\}\npaneWord=held;lastStamps=stamps;var fresh=freshHeld\(stamps\);return g\|\|nc\|\|held\|\|\(fresh\?'fresh':''\);\}/m,
    "each window's gesture and its pane word are taken apart (a gesture stands aside for the paneHere word behind it; a pane without paneHere falls back to its busyHere word; a pane detached between panes() and the call holds nothing), paneWord is the first clocked pane word, and the word reported is a gesture anywhere, then a no-deadline word, then the clocked word, then upstream's fresh window (a 'fresh' answer joins the page's stamps and that pane is asked again for its other holds, never clocked; the 2026-09-15 pull-in)");
  assert.doesNotMatch(core, /,500\)/, "no 500 ms re-check");
  assert.ok(!core.includes("__rompReloadHold") && !core.includes("shipsHold") && !core.includes("HOLD_MAX"), "the fork's 'ships' route is gone from the core; the backstop has its own names");
});
