// "Waiting on you" — every session's open USER TODOS (plans/user-todos.md) across every attached
// machine, one row each, oldest (longest waiting) first, with Reply / Dismiss / open-session. The
// person the sessions work for answers them from ONE place instead of visiting each transcript's
// split card (the user 2026-09-03). It rides the FEED payload (connects app=waiting, reads the frame's
// `userTodoRows` + `userTodosOn` — build_feed ships both beside the `userTodos` count map, from the
// same read, so the badge and this list agree by construction) and reuses the split card's two kernel
// ops unchanged: userTodoAnswer injects the reply into the session as a message from the person it
// works for AND stamps the todo answered (reviving a dormant session on the way); userTodoDismiss
// clears it with no message. Replies to either come back on THIS socket as {type:"warn"} — the pane
// shows them itself. Rows never read `asks`: the feed's rolled-up placeholder card stays where it is,
// and nothing is listed twice.
//
// Three loud states, never a blank (CLAUDE.md, fail loudly): before the first frame CARRYING the rows
// the list stays empty so the page's romp loader (_pane_spin) holds — gated on the field being an
// ARRAY, so a frame from a kernel that predates the pane reads "not built", never "nothing waiting";
// switch on + no rows → "Nothing is waiting on you"; switch OFF on the local machine → the off-notice
// with the gear one click away (the switch is per install: remote hosts' rows list regardless, and
// federation's pendingHosts/pendingDead name a host whose rows are still coming / unreachable).
import { delegate } from "./actions";
import { applyTheme } from "./theme";
import { loadSettings, installSettingsSync, onExternalSettingsChange } from "./settings";
import { hostNameNodes } from "./host-prefix";
import { liveNow, liveRefresher, stampAge, refreshAges } from "./feed-age";
import { ageColorReadable } from "./age-color";
import { utDetailHint, utHintFor, applyUtHint, UT_HINT_CLASS } from "./user-todo-hint";
import { perfFrameHandler } from "./perf-telemetry";

type Color = { bg: string; fg: string } | null;
interface UserTodo { id: string; text: string; createdT: number; detail?: string }
interface TodoRow { sid: string; name: string; color: Color; todos: UserTodo[] }
interface Waiting { sid: string; name: string; color: Color; todo: UserTodo }

const vscodeApi =
  typeof (window as any).acquireVsCodeApi === "function" ? (window as any).acquireVsCodeApi() : undefined;

// Whether a frame CARRYING userTodoRows has arrived (the Outline pane's `loaded` idiom): until then the list
// stays empty and the romp loader holds — a feed push can reach us from a kernel that never built the
// rows, and treating that as loaded would drop the loader onto a false "nothing waiting".
let loaded = false;
let rows: TodoRow[] = [];
// the LOCAL kernel's switch; null = the frame did not say (no local frame yet). Per install by design:
// federation keeps the local frame's scalar, so this never speaks for a remote host.
let localOn: boolean | null = null;
let pendingHosts: string[] = [];
let pendingDead: string[] = [];
// the kernel's clock and when its frame landed (feed-age.ts): every age is the kernel's, never the browser's
let hostNow = Math.floor(Date.now() / 1000), hostNowAt = Date.now();
const openDetail = new Set<string>();   // detail folds open, keyed sid|todo id — survives every re-render
const armedDismiss = new Set<string>(); // Dismiss buttons showing "Really dismiss?", same key — also survives
//   a re-render (the review's 2026-09-03 finding: the board rebuilds on ANY session's feed push, so the
//   arm state cannot live only on the DOM node the way render.ts's chat card can, or a push landing in the
//   arm window silently reverts the confirm to a re-arm)

function el(tag: string, cls?: string): HTMLElement { const e = document.createElement(tag); if (cls) e.className = cls; return e; }
function nowSec(): number { return liveNow(hostNow, hostNowAt, Date.now()); }
function foldKey(sid: string, tid: string): string { return sid + "|" + tid; }
// the feed's own age words: sub-minute reads "<1m ago" (a counting label is churn without information)
function relAge(sec: number): string {
  const s = Math.max(0, sec);
  if (s < 60) return "<1m ago";
  if (s < 3600) return `${Math.round(s / 60)}m ago`;
  if (s < 86400) return `${Math.round(s / 3600)}h ago`;
  return `${Math.round(s / 86400)}d ago`;
}

// ── actions ───────────────────────────────────────────────────────────────────────────────────────
// open the session's chat at its live bottom (where the split card with the same row lives) AND bring
// the chat pane forward — a click into a pane toggled off must never land invisibly (the shell's
// {romp:'reveal'} un-hides the pane before the mobile tab switch; feed.ts's card badge does the same)
function openSession(sid: string): void {
  vscodeApi?.postMessage({ type: "openSession", id: sid, live: true });
  try { if (window.parent !== window) window.parent.postMessage({ romp: "reveal", pane: "chat" }, "*"); } catch { /* not in the shell */ }
}
// the shell's Log keeps what a toast only shows for a while (the feed.ts {romp:'notify'} bridge)
function notifyShell(kind: string, text: string, sid = ""): void {
  try { window.parent?.postMessage({ romp: "notify", kind, text, sid }, "*"); } catch { /* no shell */ }
}
// the gear modal lives in the feed iframe; the shell opens it by posting openSettings there (the mobile
// rail's settings action does exactly this). Same-origin, so this pane can reach the frame itself.
function openGear(): boolean {
  try {
    const f = window.parent.document.getElementById("f-feed") as HTMLIFrameElement | null;
    if (!f || !f.contentWindow) return false;
    f.contentWindow.postMessage({ romp: "openSettings" }, "*");
    return true;
  } catch { return false; }
}
// a row the user just answered or dismissed goes NOW (the kernel's op clears it; the next frame confirms —
// the store write busts the feed cache, so it comes within a cycle). Dropped from the state, not the DOM:
// any re-render between here and that frame (a host mark, a theme change) then agrees with the click.
function dropTodo(sid: string, tid: string): void {
  for (const r of rows) r.todos = r.todos.filter((t) => t.id !== tid || r.sid !== sid);
  render();
}

// The kernel's answer to a stale or refused op comes back as {type:"warn"} — the toast the chat shows
// for the same ops (render.ts warnToast), on the styles.css dress this page links.
function warnToast(msg: string): void {
  let box = document.getElementById("warn-toasts");
  if (!box) {
    box = el("div", "");
    box.id = "warn-toasts";
    document.body.appendChild(box);
    box.addEventListener("click", (e) => { (e.target as HTMLElement | null)?.closest(".warn-toast")?.remove(); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") for (const w of Array.from(box!.children)) w.remove(); });
  }
  const t = el("div", "warn-toast");
  const txt = el("span", "warn-toast-msg"); txt.textContent = msg;
  const x = el("button", "warn-toast-x"); x.setAttribute("aria-label", "Dismiss"); x.title = "dismiss (Esc)"; x.textContent = "✕";
  t.append(txt, x);
  t.title = "click to dismiss";
  box.appendChild(t);
  setTimeout(() => t.classList.add("fade"), 11000);
  setTimeout(() => t.remove(), 12000);
}

// REPLY (render.ts showUserTodoReply, lifted): the need quoted, a box for the answer, Enter to send. A
// modal, not an inline input on the row — the list rebuilds on every frame, which would clobber a
// half-typed box; the overlay lives outside #waiting-list and survives. ONE kernel op (userTodoAnswer)
// both injects the reply and stamps the todo answered at the send, so the two cannot diverge.
function showReply(sid: string, todoId: string, todoText: string, todoDetail = ""): void {
  document.getElementById("ut-reply-prompt")?.remove();
  const overlay = el("div", "picker-overlay confirm-overlay"); overlay.id = "ut-reply-prompt";
  const box = el("div", "picker-box confirm-box");
  const h = el("div", "confirm-title"); h.textContent = "Reply";
  const d = el("div", "confirm-detail ut-reply-quote"); d.textContent = todoText;
  const dd = todoDetail.trim() ? el("div", "ut-detail open") : null;
  if (dd) dd.textContent = todoDetail;
  const input = document.createElement("textarea");
  input.className = "ut-reply-input"; input.rows = 3;
  input.placeholder = "Your answer — it goes straight to the session…";
  const actions = el("div", "confirm-actions");
  const cancel = el("button", "picker-action confirm-btn"); cancel.textContent = "Cancel";
  const send = el("button", "picker-action confirm-btn"); send.textContent = "Send";
  const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") { e.stopPropagation(); close(); } };
  const close = () => { overlay.remove(); document.removeEventListener("keydown", onKey, true); };
  const go = () => {
    const text = input.value.trim();
    if (!text) { input.classList.add("bad"); input.focus(); return; }
    vscodeApi?.postMessage({ type: "userTodoAnswer", id: sid, todoId, text });
    close();
    dropTodo(sid, todoId);   // optimistic; a stale click gets the kernel's loud warn, never a silent nothing
  };
  cancel.addEventListener("click", close);
  send.addEventListener("click", go);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); go(); } });
  input.addEventListener("input", () => input.classList.remove("bad"));
  overlay.addEventListener("click", (e) => { if (e.target === overlay) close(); });
  box.append(h, d); if (dd) box.appendChild(dd); box.append(input, actions);
  actions.append(cancel, send);
  overlay.appendChild(box);
  document.body.appendChild(overlay);
  document.addEventListener("keydown", onKey, true);
  input.focus();
}

// ── render ────────────────────────────────────────────────────────────────────────────────────────
// every open todo across every session, OLDEST FIRST — the longest-waiting ask leads (the store's own
// order within a session; across sessions by the same createdT, ties broken stably so nothing jumps)
function flatten(): Waiting[] {
  const out: Waiting[] = [];
  for (const r of rows) for (const t of r.todos) out.push({ sid: r.sid, name: r.name, color: r.color, todo: t });
  out.sort((a, b) => (a.todo.createdT - b.todo.createdT) || a.sid.localeCompare(b.sid) || a.todo.id.localeCompare(b.todo.id));
  return out;
}

function rowEl(w: Waiting, now: number): HTMLElement {
  const item = el("div", "wt-item ut-item");
  item.dataset.sid = w.sid; item.dataset.tid = w.todo.id;
  const line = el("div", "ut-line");
  // the session chip: identity colour, "host:" quiet for a remote one (and marked while its link is down)
  const sess = el("span", "wt-sess");
  sess.dataset.act = "open"; sess.dataset.sid = w.sid;
  sess.replaceChildren(...hostNameNodes(w.name || w.sid, w.sid));
  if (w.color) { sess.style.background = w.color.bg; sess.style.color = w.color.fg; }
  sess.title = "open this session's chat";
  // the one-line ask; detail one click away, and the row SAYS there is more (user-todo-hint.ts)
  const txt = el("span", "ut-text");
  txt.textContent = w.todo.text;
  const key = foldKey(w.sid, w.todo.id);
  const hint = utDetailHint(w.todo.detail, openDetail.has(key));
  if (hint) {
    txt.classList.add("ut-has-detail");
    txt.dataset.act = "uttoggle"; txt.dataset.key = key;
    txt.title = hint.title;
    const more = el("span", UT_HINT_CLASS); applyUtHint(more, hint); txt.appendChild(more);
  }
  // how long it has waited, on the kernel's clock, tinted on the recency ramp like the ledger's times
  const age = el("span", "wt-age");
  stampAge(age, w.todo.createdT, "plain", true, now, relAge, ageColorReadable);
  age.title = "asked " + new Date(w.todo.createdT * 1000).toLocaleString();
  const reply = el("button", "ut-btn ut-reply");
  reply.dataset.act = "utreply"; reply.dataset.tid = w.todo.id; reply.dataset.sid = w.sid;
  (reply as any)._uttext = w.todo.text;          // the modal quotes the need it answers…
  (reply as any)._utdetail = w.todo.detail || "";   // …and its detail, so the whole need is in view
  reply.textContent = "Reply";
  reply.title = "answer this — your reply goes straight to the session";
  const dis = el("button", "ut-btn ut-dismiss");
  dis.dataset.act = "utdismiss"; dis.dataset.tid = w.todo.id; dis.dataset.sid = w.sid;
  dis.dataset.key = key;
  // armed state comes from the set, not this fresh node, so a feed push mid-arm keeps "Really dismiss?"
  const armed = armedDismiss.has(key);
  if (armed) dis.classList.add("armed");
  dis.textContent = armed ? "Really dismiss?" : "Dismiss";
  dis.title = "clear this without a reply (for moot or stale asks)";
  line.append(sess, txt, age, reply, dis);
  item.appendChild(line);
  if (hint) {
    const d = el("div", "ut-detail" + (openDetail.has(key) ? " open" : ""));
    d.textContent = w.todo.detail || "";
    item.appendChild(d);
  }
  return item;
}

function hostLine(h: string): HTMLElement {
  const line = el("div", "wt-hostload");
  const swirl = document.createElement("img");
  swirl.src = "/media/romp-swirl-glyph.svg"; swirl.alt = "";
  const txt = el("span", "");
  txt.textContent = pendingDead.includes(h)
    ? "can’t reach " + h + ": its rows return when it reconnects"
    : "loading rows from " + h + "…";
  line.append(swirl, txt);
  return line;
}

function render(): void {
  const head = document.getElementById("waiting-head");
  const list = document.getElementById("waiting-list");
  if (!head || !list) return;
  if (!loaded) return;   // the rows have not been built yet: leave the list empty so the romp loader holds
  const items = flatten();
  const now = nowSec();
  const title = el("span", ""); title.textContent = "Waiting on you";
  const count = el("span", "wt-count");
  count.textContent = items.length ? "· " + items.length : "";
  head.replaceChildren(title, count);
  const out: Node[] = pendingHosts.map(hostLine);
  if (localOn === false) {
    // the switch is off HERE: say so, with the gear one click away — the kernel's own refusal copy
    // (_USER_TODOS_OFF_WARN) says the same thing when an op is tried while off
    const n = el("div", "wt-notice");
    const t = el("span", ""); t.textContent = "User todos are off on this machine. Turn them on in the gear.";
    const b = el("button", "ut-btn"); b.dataset.act = "gear"; b.textContent = "Open the gear";
    b.title = "opens the dashboard settings, where the User todos switch is";
    n.append(t, b);
    out.push(n);
  }
  if (items.length) {
    for (const w of items) out.push(rowEl(w, now));
  } else if (localOn !== false) {
    // GENUINELY empty: the switch is on and no session is waiting on anything
    const e = el("div", "wt-empty"); e.textContent = "Nothing is waiting on you";
    out.push(e);
  }
  list.replaceChildren(...out);
}

// ── frames ────────────────────────────────────────────────────────────────────────────────────────
function applyFrame(m: any): void {
  if (typeof m.now === "number") {
    hostNow = m.now;
    hostNowAt = typeof m.nowAt === "number" ? m.nowAt : Date.now();   // the pair travels together
  }
  pendingHosts = Array.isArray(m.pendingHosts) ? m.pendingHosts.filter((h: any) => typeof h === "string") : [];
  pendingDead = Array.isArray(m.pendingDead) ? m.pendingDead.filter((h: any) => typeof h === "string") : [];
  localOn = typeof m.userTodosOn === "boolean" ? m.userTodosOn : null;
  // "loaded" means the kernel actually BUILT the rows (the key is present, even if []) — not merely
  // that some feed frame arrived. Until then the loader holds (render() bails on !loaded).
  if (!Array.isArray(m.userTodoRows)) return;
  loaded = true;
  rows = (m.userTodoRows as any[])
    .filter((r) => r && typeof r === "object" && typeof r.sid === "string" && Array.isArray(r.todos))
    .map((r) => ({
      sid: r.sid as string, name: typeof r.name === "string" ? r.name : "", color: r.color || null,
      todos: (r.todos as any[])
        .filter((t) => t && typeof t === "object" && typeof t.id === "string")
        .map((t) => ({ id: t.id as string, text: String(t.text || ""), createdT: Number(t.createdT) || 0,
                       detail: typeof t.detail === "string" ? t.detail : undefined })),
    }));
  render();
}

// every frame's synchronous handling time is measured (perf-telemetry.ts: one clientDiag row a
// minute, read by `romp perf client`); the handler itself is unchanged
window.addEventListener("message", perfFrameHandler("waiting", (m) => vscodeApi?.postMessage(m), (e: MessageEvent) => {
  const m = e.data;
  if (!m) return;
  if (m.type === "feed") { applyFrame(m); return; }   // this pane rides the FEED payload (reads userTodoRows / userTodosOn)
  if (m.type === "feedDelta") {
    // federation applies deltas onto the full frame it holds and re-emits whole `feed` frames; one reaching
    // this handler was not applied (federation.js absent, so the shim dispatched the raw frame): say so and
    // re-base on a full frame rather than sit on the last one (the feed pane's guard; fail loudly, never degrade)
    console.error("waiting: a feedDelta frame reached the pane unapplied — asking the kernel for a full frame");
    vscodeApi?.postMessage({ type: "clientDiag", surface: "waiting", what: "feedDelta-unapplied", data: { buildId: m.buildId } });
    vscodeApi?.postMessage({ type: "needFullFeed" });
    return;
  }
  if (m.type === "warn" && typeof m.text === "string" && m.text) {
    // the kernel refused or could not do what a click asked (a stale row, an ended session, the switch
    // off): show it, keep it in the shell's Log, and re-sync from the kernel's current frame so a row
    // this pane removed optimistically comes back if it is in fact still open (the fail-loudly rule)
    warnToast(m.text);
    notifyShell("warn", m.text, typeof m.sid === "string" ? m.sid : "");
    vscodeApi?.postMessage({ type: "needFullFeed" });
    return;
  }
  if (m.type === "err" && typeof m.text === "string" && m.text) {
    // a send that never landed (the kernel's undelivered path) — same two surfaces
    warnToast(m.text);
    notifyShell("undelivered", m.text, typeof m.sid === "string" ? m.sid : "");
  }
}));
window.addEventListener("romp-hosts", () => render());   // a host's link changed → the chips' down-marks repaint
window.addEventListener("storage", (e: StorageEvent) => { if (e.key === "romp:settings") { applyTheme(document, loadSettings()); render(); } });
applyTheme(document, loadSettings());
installSettingsSync();
onExternalSettingsChange((s) => { applyTheme(document, s); render(); });

// Clicks are DELEGATED to the stable #waiting-list (installed once): render() rebuilds its children on
// every frame, so a handler hung on a row is destroyed mid-click (the click-safety rule, ui/CLAUDE.md).
(() => {
  const list = document.getElementById("waiting-list");
  if (!list) return;
  delegate(list, {
    open: (x) => { const sid = x.dataset.sid; if (sid) openSession(sid); },
    gear: () => {
      if (!openGear()) warnToast("Open the settings gear on the dashboard's bottom bar to turn user todos on.");
    },
    uttoggle: (x) => {
      const key = x.dataset.key;
      if (!key) return;
      const open = !openDetail.has(key);
      if (open) openDetail.add(key); else openDetail.delete(key);
      x.closest(".ut-item")?.querySelector(".ut-detail")?.classList.toggle("open", open);
      const more = x.querySelector<HTMLElement>("." + UT_HINT_CLASS);
      if (more) applyUtHint(more, utHintFor(open));
      x.title = utHintFor(open).title;
    },
    utreply: (x) => {
      const tid = x.dataset.tid, sid = x.dataset.sid;
      if (!tid || !sid) return;
      showReply(sid, tid, ((x as any)._uttext as string) || "", ((x as any)._utdetail as string) || "");
    },
    // Dismiss arms then confirms in place (render.ts's utdismiss, lifted): clearing an ask the agent
    // still waits on deserves a second click, but is light enough to skip a modal.
    utdismiss: (x) => {
      const tid = x.dataset.tid, sid = x.dataset.sid, key = x.dataset.key;
      if (!tid || !sid || !key) return;
      if (!armedDismiss.has(key)) {           // first tap: ARM (state in the set, so a re-render keeps it)
        armedDismiss.add(key); render();
        return;
      }
      armedDismiss.delete(key);               // second tap: confirm
      vscodeApi?.postMessage({ type: "userTodoDismiss", id: sid, todoId: tid });
      dropTodo(sid, tid);
    },
  });
  // A tap anywhere that is NOT an armed Dismiss button disarms — one persistent listener, so it survives
  // every re-render (a per-node listener would die with the rebuilt row). Covers both pointer kinds: the
  // arming tap is on the button (target is the armed .ut-dismiss), so it never self-cancels.
  document.addEventListener("pointerdown", (ev) => {
    if (!armedDismiss.size) return;
    const t = ev.target as HTMLElement | null;
    if (t && t.closest(".ut-dismiss.armed")) return;
    armedDismiss.clear(); render();
  }, true);
})();

// keep every "Xm ago" honest between frames: a quiet board sends a delta client nothing, so the ages
// move on the local clock's deltas (feed-age.ts), on the feed's own cadence. paintAge writes only the
// labels whose text changed; a pane nobody can see (a hidden tab, or the zero viewport of an iframe the
// shell has display:none'd — this pane is hidden by default on desktop) skips the pass and catches up
// once when shown (liveRefresher, the Outline pane's pattern).
const paneHidden = () => document.hidden || window.innerWidth === 0 || window.innerHeight === 0;
const live = liveRefresher({ hidden: paneHidden, pass: () => {
  refreshAges(document.querySelectorAll<HTMLElement>("[data-age-t]"), nowSec(), relAge, ageColorReadable);
} });
setInterval(live.tick, 15000);
document.addEventListener("visibilitychange", live.catchUp);
window.addEventListener("resize", live.catchUp);

render();
vscodeApi?.postMessage({ type: "ready" });   // the kernel serves the cached feed frame at once (the ready handshake)

// Hold the romp loader up until the rows actually land (the Outline pane's idiom): the shared _pane_spin
// loader has a backstop that would otherwise hide it over an EMPTY pane while a cold kernel is still
// building; re-assert it until `loaded`, and stop the instant the data arrives (event-based).
const _keepLoader = setInterval(() => {
  if (loaded) { clearInterval(_keepLoader); return; }
  const spin = document.getElementById("pane-spin");
  if (spin) spin.classList.remove("gone");
}, 1000);

export {};   // module scope
