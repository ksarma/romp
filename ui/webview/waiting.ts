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
import { linkifyPrRefs, installPrLinkOpener } from "./pr-links";
import { perfFrameHandler } from "./perf-telemetry";
import { linkifyPathTokens } from "./path-links";

type Color = { bg: string; fg: string } | null;
interface UserTodo { id: string; text: string; createdT: number; detail?: string }
interface TodoRow { sid: string; name: string; color: Color; todos: UserTodo[] }
interface Waiting { sid: string; name: string; color: Color; todo: UserTodo }

const vscodeApi =
  typeof (window as any).acquireVsCodeApi === "function" ? (window as any).acquireVsCodeApi() : undefined;
// A `#123` in an ask links to the PR page of the repository its session works in (pr-links.ts; the user
// 2026-09-06). The repo per session rides the feed frame's `sessions` rows (owner/repo, or null). The
// link opens the PR and nothing else: capture-phase on the document, so the row's delegated toggle
// under it never fires. Web → the viewer's browser; VS Code → the host's openExternal (view-routing.ts).
let repoBySid = new Map<string, string | null>();
installPrLinkOpener(document, vscodeApi ? (m) => vscodeApi.postMessage(m) : undefined);

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

// ── the detail's file links (plans/file-review.md, Slice 0) ──────────────────────────────────────
// A file path in a todo's detail is a link: the note names the file the session wants looked at, and the
// reader reaches it in one click instead of copying the path into a chat. The SAME matcher a chat body
// gets (path-links.ts), marked with the todo's own session so a relative path resolves against the cwd
// the note was written from — the kernel's _resolve_open_path, on the /file the viewer fetches. Only
// when the shell frames this pane: the click goes to the Files pane through the shell's viewFile relay,
// and a pane opened on its own has nowhere to send it — the detail stays plain text rather than a link
// that does nothing (ui/CLAUDE.md, every control acknowledges). The matcher binds nothing; the click is
// the delegate's openpath in the list and one direct delegate in the Reply modal (showReply).
const framed = window.parent !== window;
function linkDetailPaths(node: HTMLElement, sid: string): void {
  if (!framed) return;
  linkifyPathTokens(node, sid);
}
// The click: {romp:"viewFile", pane:"pane"} — the shell's Files-pane branch brings that pane forward and
// forwards this whole message into it (kernel.py's landing shell; files.ts opens the viewer). The
// identity is the row's own chip (name + colour — the pane has no session list to name the file's
// session by; a row with no name sends null and the viewer falls to the kernel's stub); todoId names the
// user todo the file was opened from, so the viewer can tie its work back to it.
// Then focus moves to the Files pane. A keydown never crosses an iframe boundary, and the viewer's only
// keyboard close is a document-level Escape in the Files document — so with focus left here, the Escape a
// keyboard user pressed after opening a file (Enter on a focused link) closed the Reply modal and left the
// viewer up (the 2026-09-06 review). The panes are same-origin siblings, so this pane focuses the Files
// pane's window itself, the way the shell's Alt+Arrow nav does (focusPane in _LANDING_FOCUS_JS:
// contentWindow.focus(), which also moves the shell's focus ring). No text field loses anything: the link
// already held this document's focus (a click focuses the tabIndex span; Enter came from it). The pane
// must be ON SCREEN first: Firefox refuses to focus the window of a display:none frame (Chromium does not,
// which hid this), and the shell's relay brings the pane forward only when the posted message reaches it,
// a task after this call. So this pane brings it forward itself, through the shell's own pane toggle
// (window.__rompPaneToggle, the call the relay makes — the relay's then finds nothing to change), and
// focuses after that; a shell without the toggle gets the focus call as before (the review's round 3;
// waiting-pane-browser.test.ts drives this in Firefox and Chromium with the pane closed). Alt+Left comes
// back; an open Reply modal then takes the focus back into its box (showReply). The iframe check is against
// the PARENT document's HTMLIFrameElement: an element of another document is never an instance of this
// document's constructor, so a check against this one's would focus nothing. Plain JS in the body — no
// cast, no annotation — because user-todo-links.test.ts executes it as it stands; the shell's toggle is
// typed on Window below for that reason (palette-main.ts's chatPost reveals-then-focuses the same way).
declare global { interface Window { __rompPaneToggle?: (key: string, to?: boolean) => void } }
function openTodoPath(path: string, sid: string, todoId: string): void {
  const r = rows.find((x) => x.sid === sid);
  const identity = r && r.name ? { name: r.name, color: r.color } : null;
  try { window.parent.postMessage({ romp: "viewFile", pane: "pane", path, sid, identity, todoId }, "*"); } catch { /* not in the shell */ }
  try {
    const pd = window.parent.document, ff = pd.getElementById("f-files"), shell = pd.defaultView;
    if (shell && ff instanceof shell.HTMLIFrameElement) {
      if (typeof shell.__rompPaneToggle === "function") shell.__rompPaneToggle("files", true);
      ff.contentWindow?.focus();
    }
  } catch { /* a parent this pane cannot read is not the shell */ }
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
  if (dd) {
    dd.textContent = todoDetail;
    linkDetailPaths(dd, sid);
    // the modal lives outside #waiting-list and is built once per open, never rebuilt — so it carries
    // its own delegate for the same act (one listener on the quoted detail; the rows' is on the list)
    delegate(dd, { openpath: (x) => { const p = x.dataset.path; if (p) openTodoPath(p, sid, todoId); } });
  }
  const input = document.createElement("textarea");
  input.className = "ut-reply-input"; input.rows = 3;
  input.placeholder = "Your answer — it goes straight to the session…";
  const actions = el("div", "confirm-actions");
  const cancel = el("button", "picker-action confirm-btn"); cancel.textContent = "Cancel";
  const send = el("button", "picker-action confirm-btn"); send.textContent = "Send";
  const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") { e.stopPropagation(); close(); } };
  // A link in the quoted detail moves focus to the Files pane (openTodoPath). When focus comes back —
  // Alt+Left, a click into this pane — the document's focus has been reset to its body, BEHIND this
  // overlay, where Tab would walk the covered rows before reaching the box. The modal is the topmost thing
  // on the pane, so it takes the focus back into its box, where the answer goes (Shift+Tab still reaches
  // the link). Gone with the modal: close() drops it, and it drops itself if the overlay was removed some
  // other way (a second Reply replacing this one, above).
  const onFocus = () => { if (!overlay.isConnected) { window.removeEventListener("focus", onFocus); return; } input.focus(); };
  const close = () => { overlay.remove(); document.removeEventListener("keydown", onKey, true); window.removeEventListener("focus", onFocus); };
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
  window.addEventListener("focus", onFocus);
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
  linkifyPrRefs(txt, repoBySid.get(w.sid) || null);
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
    linkDetailPaths(d, w.sid);   // a path in the note opens in the Files pane (the delegate's openpath)
    linkifyPrRefs(d, repoBySid.get(w.sid) || null);   // then `#123` → its PR page; each linker skips the other's anchors
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

// While a pointer is PRESSED on the list, re-renders are HELD and flushed after the release (the tab
// strip's and the timeline's idiom: render.ts tabPointerHeld, romp-timeline-view.js _pointerHeld). render()
// does list.replaceChildren() on every call, and a rebuild between mousedown and mouseup on a row's control
// detaches the pressed node: the native click then never fires (the released node shares no ancestor with a
// detached one), so the delegate below never runs — the link, Reply or Dismiss flashes nothing and opens
// nothing (ui/CLAUDE.md, click safety; the 2026-09-06 review). Two rebuilds land mid-press: a feed frame
// (the pane rebuilds on any session's push while sessions work) and the disarm below, which re-renders
// SYNCHRONOUSLY on the pointerdown that starts the very press whose click it then loses. The flush waits a
// tick: the click dispatches right after pointerup, and must fire against the still-present node first.
// Every press must reach a release — pointerup, pointercancel, or the window losing focus (released over
// another frame, where this document sees no pointerup) — or the hold defers rebuilds until the next press.
let listPointerHeld = false;
let renderPendingWhilePressed = false;
function releaseList(): void {
  if (!listPointerHeld) return;
  listPointerHeld = false;
  if (renderPendingWhilePressed) { renderPendingWhilePressed = false; setTimeout(() => render(), 0); }
}

function render(): void {
  const head = document.getElementById("waiting-head");
  const list = document.getElementById("waiting-list");
  if (!head || !list) return;
  if (!loaded) return;   // the rows have not been built yet: leave the list empty so the romp loader holds
  if (listPointerHeld) { renderPendingWhilePressed = true; return; }   // pressed: the release flushes (releaseList)
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
  if (Array.isArray(m.sessions))
    repoBySid = new Map(m.sessions.filter((s: any) => s && typeof s.sid === "string")
      .map((s: any) => [s.sid as string, typeof s.githubRepo === "string" ? s.githubRepo : null] as const));
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
    // a file path in a row's detail: the ROW says which session and which todo, the same way the Reply
    // modal's delegate takes both from its closure. Not the span's own data-sid: path-links.ts stamps it
    // on a bare path (whose resolver needs a cwd) and not on a file:// URI (an absolute path names no
    // session), so a handler gated on the span's sid dropped every URI click right after the delegate's
    // press flash — a link that acknowledged and opened nothing (the 2026-09-06 review).
    openpath: (x) => {
      const row = x.closest<HTMLElement>(".ut-item");
      const p = x.dataset.path, sid = row?.dataset.sid, tid = row?.dataset.tid;
      if (p && sid && tid) openTodoPath(p, sid, tid);
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
  // arming tap is on the button (target is the armed .ut-dismiss), so it never self-cancels. A press on the
  // list is latched FIRST, in this same listener: the disarm's render() then defers to the release instead
  // of detaching the node under the pointer before its click (listPointerHeld, above render).
  document.addEventListener("pointerdown", (ev) => {
    const t = ev.target as HTMLElement | null;
    if (t && list.contains(t)) listPointerHeld = true;
    if (!armedDismiss.size) return;
    if (t && t.closest(".ut-dismiss.armed")) return;
    armedDismiss.clear(); render();
  }, true);
  window.addEventListener("pointerup", releaseList);
  window.addEventListener("pointercancel", releaseList);
  window.addEventListener("blur", releaseList);   // released over another frame: no pointerup reaches this document
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
