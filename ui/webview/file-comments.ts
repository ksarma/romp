// File comments and tracked changes — the viewer's Comments panel (plans/file-review.md, Slice 1).
//
// The person who directs the sessions reads their output as files, and until now a comment on a file
// left romp: GitHub, a chat quote that scrolled away, or a note typed into the file itself. This panel
// keeps a comment WITH the file, in the track-changents sidecar the agent's own CLIs read and write
// (`.trackchanges/` beside the project's root; docs/adr/0002), and hands everything unsent to the
// session in ONE message — so a morning's reading costs one interruption, not one per remark.
//
// Shape (the plan's Shape of the feature):
//   • The action-row entry is the glance ("Comments · 2 · 5 changes"); the panel is one click; a card
//     expands on click, keyed by comment id in a set that survives every re-render.
//   • The kernel does the disk work on the OWNING kernel (the `fileComments` op runs a node host
//     script over the vendored track-changents store); this module renders JSON and never holds a
//     sidecar it writes back. Both ops carry `sid`, so federation routes a remote session's file to
//     the kernel that owns the disk with no new relay code.
//   • Change awareness by POLLING (2.5 s while the panel is open and the tab visible): HEAD /file on
//     the file, the sidecar the kernel named, and the project's config.json, comparing X-Romp-Mtime-Ns
//     as STRINGS. The Files pane has no filesystem watcher; the poll stands in for that event, and the
//     person's own writes never fire it because every verb reply re-baselines it. Replies land in the
//     order their asks were issued (applyStatus): the kernel runs each ask concurrently and answers when
//     it finishes, and a status that read the disk before a write — asked before it, or asked while it was
//     in flight — must not put the panel back a step once the write's reply is showing.
//   • The panel's controls hang off the viewer's body row, which also holds the FILE's rendered markup; an
//     activation is routed only when the panel made the element (own / owns), never for a data-act the
//     file's author wrote.
//   • What is unsent is derived from the comments log on the owning kernel, never from browser state
//     (decision 10): the `status` reply carries it, the button's count is that number.
//   • Every write sits behind the one file-editing consent, shared with Save (decision 5).
// The pure half (view model, message preview, poll verdicts) is file-comments-model.ts; the
// selection→anchor mapping and the highlight painters are anchor-map.ts (contract C4).
//
// This module imports only TYPES from file-view.ts and is registered there (registerFileViewAction
// in file-view.ts), so the two never form a runtime import cycle.
import type { FileViewAction, FileViewActionCtx, FileViewIdentity } from "./file-view";
import { delegate, flash, type ActionHandler } from "./actions";
import { fileUrl } from "./preview";
import { kernelUrl } from "./media";
import { hostOf, bareId } from "./host-prefix";
import { mapRawSelection, mapRenderedSelection, makeAnchor, locateComment, paintRaw, paintRendered, rawOffsetToLine } from "./anchor-map";
import type { MapRefusal, SourceRange, Located } from "./anchor-map";
import {
  type Status, type Card, type SendParts, actionLabel, cardModel, sendParts, buildSendMessage, unsentCount,
  logRowText, pollBaseline, pollTargets, headVerdict, mtimeMoved, editBlockedReason, lineStartOffset, folderOf,
  type PollBaseline,
} from "./file-comments-model";

const POLL_MS = 2500;
const MOVED = new Set(["store-moved", "file-moved", "config-moved"]);
// How long a `status` ask may stay unanswered before the panel says so. A kernel that has the op answers
// within its own bound: the host script is cut off at 10 s (contract C2, _FILE_COMMENTS_TIMEOUT) and the
// refusal is sent then, so an ask still open past that plus the relay was never received by a kernel with
// the handler — a kernel from before this feature matches no `type` and sends nothing, not even a warn, and
// federation's drop notice covers only an UNREACHABLE host, not a reachable one that has no answer. There is
// no event to key on because the older kernel emits none; the timer speaks only when the answer never comes
// (feed.ts's redistill watch is the same shape, and ui/CLAUDE.md wants every wait to have a backstop).
// `status` only: a mutating verb that is failed here could have landed on disk, and the kept note would
// invite a duplicate — those keep waiting for the kernel's own answer.
const STATUS_DEADLINE_MS = 15000;
// One send answers a todo (decision 28): a todo naming several files is answered by the FIRST send, and
// later sends for its other files show no checkbox. A viewer is built per open, so the memory of which
// todos THIS page has sent for lives at module level — a second file opened from the same todo, a Reload
// (which re-opens with the same todoId), or the Reply modal's other link all find it. Another device or
// document has no view of this set; the kernel's own settled check (plan: the reply warns, nothing is
// stamped) stays the backstop there.
const answeredTodos = new Set<string>();

// ── image embeds: the source text behind a rendered <img> ─────────────────────────────────────────
// A figure in a markdown file is commented on through its embed line (the plan's Images and PDFs): in
// Rendered view a click on the picture offers Comment, and the anchor is the embed's source text. The
// mapping walk records no positions for an image (it renders no text), so the embed is found here from
// the picture's own `src`: every embed form the source can hold, in order, fenced code skipped, matched
// against the attribute marked emitted (which percent-encodes the destination).
export type ImageEmbed = { start: number; end: number; dest: string };
const LABEL = "(?:\\\\.|[^\\[\\]\\\\])*";
const IMG_INLINE = new RegExp("!\\[(" + LABEL + ")\\]\\([ \\t]*(?:<([^<>\\n]*)>|([^\\s()]*(?:\\([^\\s()]*\\)[^\\s()]*)*))(?:[ \\t]+(?:\"[^\"]*\"|'[^']*'|\\([^()]*\\)))?[ \\t]*\\)", "g");
const IMG_FULL_REF = new RegExp("!\\[(" + LABEL + ")\\]\\[(" + LABEL + ")\\]", "g");
const IMG_SHORT_REF = new RegExp("!\\[(" + LABEL + ")\\](?![\\[(])", "g");
const IMG_HTML = /<img\b[^>]*?\bsrc[ \t]*=[ \t]*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))[^>]*>/gi;
const REF_DEF = /^ {0,3}\[((?:\\.|[^\[\]\\])+)\]:[ \t]*<?([^\s>]+)>?/gm;
const normLabel = (s: string): string => s.trim().replace(/\s+/g, " ").toLowerCase();
/** Offsets of the source's fenced code blocks, [start, end): an embed written inside one renders as text. */
function fencedRanges(src: string): Array<[number, number]> {
  const out: Array<[number, number]> = [];
  let open: { ch: string; n: number; at: number } | null = null;
  let at = 0;
  for (const line of src.split("\n")) {
    const m = /^ {0,3}(`{3,}|~{3,})/.exec(line);
    if (m) {
      if (!open) open = { ch: m[1][0], n: m[1].length, at };
      else if (m[1][0] === open.ch && m[1].length >= open.n && /^\s*$/.test(line.slice(m[0].length))) { out.push([open.at, at + line.length]); open = null; }
    }
    at += line.length + 1;
  }
  if (open) out.push([open.at, src.length]);
  return out;
}
/** Every image embed in the source, in order: `![alt](dest "title")`, `![alt][ref]` and `![ref]` resolved
 *  through `[ref]: dest` definitions, and a raw `<img src>` tag. Fenced code is skipped. */
export function imageEmbeds(src: string): ImageEmbed[] {
  const fences = fencedRanges(src);
  const inFence = (i: number): boolean => fences.some(([a, b]) => i >= a && i < b);
  const defs = new Map<string, string>();
  let m: RegExpExecArray | null;
  REF_DEF.lastIndex = 0;
  while ((m = REF_DEF.exec(src))) if (!inFence(m.index)) defs.set(normLabel(m[1]), m[2]);
  const out: ImageEmbed[] = [];
  const push = (start: number, len: number, dest: string | undefined): void => {
    if (dest !== undefined && !inFence(start)) out.push({ start, end: start + len, dest });
  };
  for (const re of [IMG_INLINE, IMG_FULL_REF, IMG_SHORT_REF, IMG_HTML]) re.lastIndex = 0;
  while ((m = IMG_INLINE.exec(src))) push(m.index, m[0].length, m[2] ?? m[3] ?? "");
  while ((m = IMG_FULL_REF.exec(src))) push(m.index, m[0].length, defs.get(normLabel(m[2] || m[1])));
  while ((m = IMG_SHORT_REF.exec(src))) push(m.index, m[0].length, defs.get(normLabel(m[1])));
  while ((m = IMG_HTML.exec(src))) push(m.index, m[0].length, m[1] ?? m[2] ?? m[3] ?? "");
  out.sort((a, b) => a.start - b.start);
  return out.filter((e, i) => !i || e.start >= out[i - 1].end);   // a shortcut form inside a longer one: the longer wins
}
/** Whether a source destination is the `src` marked emitted for it (marked percent-encodes; either side may be encoded). */
export function sameDest(dest: string, src: string): boolean {
  if (dest === src) return true;
  try { if (encodeURI(dest).replace(/%25/g, "%") === src) return true; } catch { /* a lone surrogate */ }
  try { return decodeURI(dest) === decodeURI(src); } catch { return false; }
}
const imgsIn = (root: Element): HTMLElement[] => Array.from(root.querySelectorAll("img")) as HTMLElement[];
/** The embed a rendered picture came from: by destination, and among twins by order. Null when the source holds none. */
export function embedFor(img: Element, root: Element, src: string): ImageEmbed | null {
  const want = img.getAttribute("src");
  if (want === null) return null;
  const hits = imageEmbeds(src).filter((e) => sameDest(e.dest, want));
  if (hits.length === 1) return hits[0];
  if (!hits.length) return null;
  const k = imgsIn(root).filter((i) => i.getAttribute("src") === want).indexOf(img as HTMLElement);
  return k >= 0 && k < hits.length ? hits[k] : null;
}
/** The rendered picture for an embed's exact source range — the inverse, for painting. */
export function imgForRange(root: Element, src: string, range: SourceRange): HTMLElement | null {
  const all = imageEmbeds(src);
  const e = all.find((x) => x.start === range.start && x.end === range.end);
  if (!e) return null;
  const k = all.filter((x) => x.dest === e.dest).indexOf(e);
  const twins = imgsIn(root).filter((i) => { const s = i.getAttribute("src"); return s !== null && sameDest(e.dest, s); });
  return twins[k] || null;
}
// A framed picture wears the mark classes itself — an <img> has no text to wrap — plus an inline outline,
// because the sheets' ring is an inset shadow the picture covers. `fc-img` tells unpaint to strip, not unwrap.
function styleFrame(img: HTMLElement): void {
  const presel = img.classList.contains("fc-presel");
  const dashed = !presel && img.classList.contains("fc-hl-context");
  img.style.outline = "2px " + (dashed ? "dashed" : "solid") + " " + (presel ? "var(--accent)" : "var(--warn)");
  img.style.outlineOffset = "2px";
}
function frameImage(img: HTMLElement, cls: string, data?: Record<string, string>): void {
  img.classList.add("fc-img", ...cls.split(" ").filter(Boolean));
  if (data) for (const k of Object.keys(data)) img.dataset[k] = data[k];
  styleFrame(img);
}
function unframeImage(img: HTMLElement, marks: string[]): void {
  img.classList.remove(...marks);
  if (img.classList.contains("fc-hl") || img.classList.contains("fc-presel")) { styleFrame(img); return; }
  img.classList.remove("fc-img", "fc-hl-context");
  img.style.outline = ""; img.style.outlineOffset = "";
  delete img.dataset.act; delete img.dataset.id;
}

function el(tag: string, cls?: string, text?: string): HTMLElement {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}
function btn(label: string, act: string, cls = "fileview-btn"): HTMLButtonElement {
  const b = el("button", cls, label) as HTMLButtonElement;
  b.type = "button";
  b.dataset.act = act;
  return b;
}
const clock = (t: number | string): string => {
  const d = new Date(t);
  if (isNaN(d.getTime())) return "";
  const today = new Date();
  const sameDay = d.getFullYear() === today.getFullYear() && d.getMonth() === today.getMonth() && d.getDate() === today.getDate();
  const hm = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return sameDay ? hm : d.toLocaleDateString([], { month: "short", day: "numeric" }) + " " + hm;
};
// a pane the shell has hidden gives its iframe a ZERO viewport (document.hidden stays false there) — the
// Sessions pane's gate, reused: skip the tick while hidden, catch up once on the first visible moment
const paneHidden = (): boolean => document.hidden || window.innerWidth === 0 || window.innerHeight === 0;

// `overlapped`: a status ask still unanswered when a write's reply landed (markOverlapped) — its host run may
// have read the disk before that write, whatever its place in line
type Pending = { verb: string; ok: (m: Record<string, unknown>) => void; fail: (e: { code: string; error: string }) => void; deadline?: ReturnType<typeof setTimeout>; overlapped?: boolean };
/** A status reply as the panel applies it: the kernel's fields plus the reqId of the ask it answers, and
 *  whether that ask overlapped a write (see Pending). */
type Reply = Status & { reqId: number; overlapped?: boolean };

// ── which of two status replies read the disk later ────────────────────────────────────────────────
// Mtimes are decimal nanosecond strings (~1.7e18 exceeds JS's safe integers, so they never become numbers):
// digit strings order by length, then by text. A value beats null (a sidecar or config that now exists is a
// later reading than one that says it does not); anything that is not digits is no clock and claims nothing.
function laterNs(a: string | null | undefined, b: string | null | undefined): boolean {
  if (!a) return false;
  if (!b) return true;
  if (!/^\d+$/.test(a) || !/^\d+$/.test(b)) return false;
  return a.length !== b.length ? a.length > b.length : a > b;
}
/** Did `a` read a LATER disk than `b`? True when any of the file, the sidecar or the config moved forward. */
export function newerStatus(a: Status, b: Status): boolean {
  return laterNs(a.fileMtimeNs, b.fileMtimeNs) || laterNs(a.storeMtimeNs, b.storeMtimeNs) || laterNs(a.configMtimeNs, b.configMtimeNs);
}

// ── a path the panel prints inline ─────────────────────────────────────────────────────────────────
// Chromium breaks a line at neither a slash nor anywhere inside an unbroken token, and a flex item's automatic
// minimum size is that token, so a path wider than the aside's 340px (about 55 characters) pushed .fc-panel
// into a horizontal scrollbar: the folder button of the tracking choice, the folder-off confirm, and any error
// row naming a path. The path is appended as text with a <wbr> after every `/` — a break where a reader would
// put one, and no change to textContent — with `overflow-wrap: anywhere` behind it for a single component
// wider than the aside (it also lets the item's minimum size shrink below the token).
/** The path split after every `/`: "/a/b/c.md" → ["/", "a/", "b/", "c.md"]. */
export function pathSegments(path: string): string[] {
  return path.match(/[^/]*\/|[^/]+$/g) || [];
}
function appendPath(node: HTMLElement, path: string): void {
  pathSegments(path).forEach((seg, i) => {
    if (i) node.appendChild(document.createElement("wbr"));
    node.appendChild(document.createTextNode(seg));
  });
  node.style.overflowWrap = "anywhere";
}
/** A .fileview-btn is `flex: 0 0 auto`, one line, right for "Reload" and wrong for a label carrying a path:
 *  this one may shrink to its row and wrap inside, its lines starting at the left like the text around it. */
function shrinkable(b: HTMLElement): void {
  b.style.flex = "0 1 auto"; b.style.minWidth = "0"; b.style.textAlign = "left";
}
// A passage comment's `range` indexes `text` — the source the selection was made over, or the reload the
// passage was re-found in (retargetComposer) — so the anchor is always built over the text the offsets
// belong to, never over whatever sits at those offsets now. `text` travels with every non-null range.
type Composer =
  | { kind: "comment"; range: SourceRange | null; quote: string | null; text?: string; refusal: (MapRefusal & { selText: string }) | null }
  | { kind: "reply"; commentId: string; ref: string };
type Err = { text: string; reload: boolean; warn?: boolean };

// ── the wire: ONE window listener for the module, dispatching to the live panel by reqId ───────────
// A reply is matched by reqId only — a REMOTE kernel's reply comes back with its sid host-prefixed
// (federation's prefixInbound), so sid equality would fail there. The one `warn` that means an
// outstanding request will never be answered is federation's drop notice (dropWarn: "<host> is
// unreachable (its kernel isn't answering) — “<type>” was not delivered"), and only when it names one
// of THIS module's ops: the kernel sends `warn` on the same socket for unrelated refusals — a rejected
// rename, a todo notice — with no reqId, and failing a request on those reported a comment that had
// succeeded on disk as failed, with the kept note inviting a duplicate. The shim's own drop event
// (romp:wsdown) fails everything outstanding, as before.
let live: Panel | null = null;
let listening = false;
const DROPPED_OPS = ["fileComments", "fileCommentsSend"];
/** The warn's text when it is federation's drop of one of this module's requests, else null. */
export function droppedRequestText(text: unknown): string | null {
  const t = typeof text === "string" ? text : "";
  return DROPPED_OPS.some((op) => t.includes("“" + op + "” was not delivered")) ? t : null;
}
function ensureListener(): void {
  if (listening) return;
  listening = true;
  window.addEventListener("message", (e: MessageEvent) => {
    const m = e.data;
    if (!m || !live) return;
    if (m.type === "fileCommentsResult" || m.type === "fileCommentsSent") live.settle(m, true);
    else if (m.type === "fileCommentsFailed" || m.type === "fileCommentsSendFailed") live.settle(m, false);
    else if (m.type === "warn") live.failAll(droppedRequestText(m.text));
  });
  window.addEventListener("romp:wsdown", () => { if (live) live.failAll("the connection dropped; try again once it returns"); });
}

// The controls that are not <button>s — a card's head, its passage link, a Log row, a painted highlight —
// and so take Enter and Space here, through the same root the clicks use: a collapsed card is otherwise a
// dead end for the keyboard (ui/CLAUDE.md, never dead-end a compact view).
const KEY_ACTS = new Set(["fccard", "fcgoto", "fcopen", "fclogrow"]);

/** Where a Rendered-view refusal's passage sits in the source, for the switch to Raw. The selection
 *  came from the REFUSED block, so the search starts at that block: a copy of the same words earlier in
 *  the file (prose saying "p95" above a table cell "p95") must not win. The text searched for is the
 *  mapper's own source slice when it has one (`rawRange`, found over the normalized text, so it carries
 *  the source's tabs and CRLFs where the DOM's selection string has spaces and LFs), else the trimmed
 *  selection; the mapper's slice stands when neither search hits. Null when the mapper saw no
 *  occurrence at all (the button then only scrolls to the block). */
export function rawTarget(src: string, r: MapRefusal & { selText: string }): SourceRange | null {
  if (!r.rawHasQuote) return null;
  const rr = r.rawRange && r.rawRange.start >= 0 && r.rawRange.end > r.rawRange.start && r.rawRange.end <= src.length ? r.rawRange : null;
  const q = rr ? src.slice(rr.start, rr.end) : r.selText.trim();
  if (!q) return rr;
  const from = typeof r.blockStartOffset === "number" ? Math.max(0, r.blockStartOffset) : 0;
  let i = src.indexOf(q, from);
  if (i < 0) i = src.indexOf(q);
  return i >= 0 ? { start: i, end: i + q.length } : rr;
}

let reqSeq = 0;

class Panel {
  status: Status | null = null;
  statusRefusal: { code: string; error: string } | null = null;   // why there is no status, when the kernel refused one
  root: HTMLElement | null = null;          // the aside, built on first open
  marks = new WeakSet<Element>();           // the highlights and picture frames THIS panel painted into the body (owns)
  open = false;
  pending = new Map<number, Pending>();
  appliedReq = 0;                           // the reqId of the newest ask whose reply is showing (applyStatus)
  openCards = new Set<string>();            // keyed expand state: survives every re-render (ui/CLAUDE.md)
  openLog = new Set<string>();              // expanded Log rows, keyed by entry (ts|kind) — the same rule
  logOpen = false;
  imageTarget: { range: SourceRange | null } | null = null;   // the picture the float's Comment is about, when it is one
  resolvedOpen = false;
  trackChoice = false;                      // the on-toggle's scope row (file / folder) is showing
  trackStop = false;                        // the folder-off confirm is showing
  composer: Composer | null = null;
  errors = new Map<string, Err>();          // per slot: the row sits under the control that asked
  busy = new Set<string>();
  sendConfirm = false;
  sending = false;
  sendOpts = { todo: true, track: true };   // both checked by default (decision 8)
  sentNote: string | null = null;
  todoAnswered = false;                     // one send answers the todo; later sends show no checkbox (seeded from answeredTodos)
  previewOpen = false;
  colors: Map<string, FileViewIdentity> | null = null;
  located = new Map<string, Located & { painted: boolean }>();
  base: PollBaseline | null = null;
  stopped = new Set<string>();              // poll targets a 413/415 retired
  timer: ReturnType<typeof setInterval> | null = null;
  polling = false;
  tickSkipped = false;
  // persistent section wrappers: render() swaps each section's CHILDREN, never the aside's own children —
  // replaceChildren on the aside would remove and re-insert the composer box, and a removed element
  // loses focus, so a poll-triggered re-render would drop the input's focus mid-word
  sections = { head: el("div", "fc-sec-head"), cards: el("div", "fc-sec-cards"), send: el("div", "fc-sec-send"), log: el("div", "fc-sec-log") };
  // persistent composer parts, for the same reason
  composerBox = el("div", "fc-composer");
  composerRef = el("div", "fc-composer-ref");
  input = el("input", "fc-input") as HTMLInputElement;
  composerActs = el("div", "fc-actions");
  composerErr = el("div");
  float = el("button", "fileview-btn fc-float", "Comment") as HTMLButtonElement;
  catchUp = () => { if (this.tickSkipped) void this.tick(); };
  hideFloatOnDown = (ev: Event) => { if (ev.target !== this.float) { this.float.hidden = true; this.imageTarget = null; } };

  constructor(readonly ctx: FileViewActionCtx, readonly button: HTMLButtonElement, readonly unit: HTMLElement) {
    ensureListener();
    live = this;
    this.todoAnswered = !!ctx.todoId && answeredTodos.has(ctx.todoId);
    this.input.type = "text";
    this.input.placeholder = "Your note (Enter saves, Esc cancels)";
    this.input.setAttribute("aria-label", "Comment text");
    this.input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); void this.saveComposer(); }
      else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); this.closeComposer(); }   // never the viewer's Escape
    });
    (this.float as HTMLButtonElement).type = "button";
    this.float.hidden = true;
    this.float.title = "Comment on the selected passage";
    // keep the selection alive across the click: a mousedown elsewhere would collapse it before the click lands
    for (const ev of ["mousedown", "touchstart"]) this.float.addEventListener(ev, (e) => e.preventDefault());
    const act = () => {
      flash(this.float);
      const picture = this.imageTarget; this.imageTarget = null;
      const sel = window.getSelection();
      this.float.hidden = true;
      if (picture) this.startImageComment(picture.range);
      else if (sel && !sel.isCollapsed) this.startComment(sel);
    };
    this.float.addEventListener("click", act);
    // a tap: the touchstart above is cancelled, and a cancelled touch synthesizes no mouse events and no
    // click (Touch Events, "mouse events"), so on a phone the button acted on nothing. The tap acts here, on
    // the lift, while the selection is still live; cancelling the touchend too stops any click a browser
    // would still synthesize from acting a second time.
    this.float.addEventListener("touchend", (e) => { e.preventDefault(); act(); });
    document.body.appendChild(this.float);
    for (const ev of ["mousedown", "touchstart"]) document.addEventListener(ev, this.hideFloatOnDown, true);   // a press anywhere else hides it, mouse or finger
    ctx.onSelection((sel) => this.onSelection(sel));
    ctx.onRendered(() => { this.float.hidden = true; this.retargetComposer(); this.paintAll(); });
    ctx.onSaved((info) => {
      if (this.base) this.base.file = info.mtimeNs;   // the poll must not re-fetch the person's own save
      if (this.status) void this.refresh();            // the Log gained the edit entry before the reply
    });
    ctx.onClose(() => this.dispose());
    // every control the panel ever renders hangs off ONE stable root (ui/CLAUDE.md, click-safe): the
    // viewer's body row, which also holds the painted highlights — so a highlight click routes here too.
    // The same row holds the FILE's rendered markdown, and the sanitizer keeps data-* attributes (DOMPurify's
    // ALLOW_DATA_ATTR default), so a file's author can write `<span data-act="fcsendgo">` or a
    // `data-act="fctrackstop"` into prose the session produced: a click there must not send the comments
    // or turn the guard off for a folder. `own` routes an activation only when the panel MADE the element —
    // a control in its aside, or a highlight it painted (owns) — never the file's own markup.
    const row = ctx.body().parentElement || ctx.body();
    delegate(row, {
      ...this.own({
        fctrack: () => { void this.onTrackClick(); },
        fctrackfile: () => { this.trackChoice = false; void this.mutate("set-tracked", { on: true, scope: "file" }, "track"); },
        fctrackfolder: () => { this.trackChoice = false; void this.mutate("set-tracked", { on: true, scope: "folder" }, "track"); },
        fctrackcancel: () => { this.trackChoice = false; this.trackStop = false; this.render(); },
        fctrackstop: () => { this.trackStop = false; void this.mutate("set-tracked", { on: false, scope: "folder" }, "track"); },
        fcfile: () => this.startFileComment(),
        fcsave: () => { void this.saveComposer(); },
        fccancel: () => this.closeComposer(),
        fcraw: () => this.switchToRaw(),
        fccard: (x) => { const id = x.dataset.id!; if (this.openCards.has(id)) this.openCards.delete(id); else this.openCards.add(id); this.render(); },
        fcgoto: (x, ev) => { ev.stopPropagation(); this.goTo(x.dataset.id!); },
        fcreveal: (x, ev) => { ev.stopPropagation(); this.reveal(x.dataset.id!); },
        fcreply: (x, ev) => { ev.stopPropagation(); this.startReply(x.dataset.id!); },
        fcresolve: (x, ev) => { ev.stopPropagation(); void this.mutate("resolve", { commentId: x.dataset.id!, on: x.dataset.on === "1" }, "card:" + x.dataset.id!); },
        fcresolved: () => { this.resolvedOpen = !this.resolvedOpen; this.render(); },
        fcsend: () => { if (this.statusRefusal) return; this.sendConfirm = true; this.sentNote = null; this.render(); },   // renderSend disables the button and says why; the guard holds if a click lands anyway
        fcsendcancel: () => { this.sendConfirm = false; this.previewOpen = false; this.render(); },
        fcsendgo: () => { void this.doSend(); },
        fcpreview: () => { this.previewOpen = !this.previewOpen; this.render(); },
        fclog: () => { this.logOpen = !this.logOpen; this.render(); },
        fclogrow: (x) => { const k = x.dataset.key!; if (this.openLog.has(k)) this.openLog.delete(k); else this.openLog.add(k); this.render(); },
        // Reload re-reads under the row that offered it: the slot wears the loader for the wait (refresh)
        fcreload: (x) => { const slot = x.dataset.slot || "head"; this.errors.delete(slot); this.stopped.clear(); void this.refresh(slot); this.ctx.reload(); },
        fcerrx: (x) => { this.errors.delete(x.dataset.slot || ""); this.render(); },
        fcopen: (x) => { this.openPanel(); const id = x.dataset.id!; this.openCards.add(id); this.render(); this.scrollCard(id); },
      }),
    });
    row.addEventListener("change", (ev) => {
      const t = ev.target as HTMLInputElement | null;
      if (!t || t.dataset.opt !== "todo" && t.dataset.opt !== "track" || !this.owns(t)) return;   // a checkbox the file's markup carries flips nothing
      this.sendOpts[t.dataset.opt as "todo" | "track"] = t.checked;
    });
    // a click on a rendered picture offers Comment on its embed line (the plan's Images and PDFs) — the same
    // stable root, a plain tag check rather than a data-act: the markdown's own <img> carries none
    row.addEventListener("click", (ev) => {
      const t = ev.target as HTMLElement | null;
      if (t && typeof t.tagName === "string" && t.tagName.toUpperCase() === "IMG") this.onImageClick(t);
    });
    // Enter or Space on a focused non-button control (KEY_ACTS) is its click, so it lands on the same root —
    // for the panel's own elements only, as with the clicks
    row.addEventListener("keydown", (ev) => {
      if (ev.key !== "Enter" && ev.key !== " ") return;
      const t = ev.target as HTMLElement | null;
      if (!t || typeof t.tagName !== "string" || t.tagName.toUpperCase() === "BUTTON" || t.tagName.toUpperCase() === "INPUT" || typeof t.closest !== "function") return;
      const x = t.closest("[data-act]") as HTMLElement | null;
      if (!x || !KEY_ACTS.has(x.dataset.act || "") || !this.owns(x)) return;
      ev.preventDefault();
      x.click();
    });
    this.button.addEventListener("click", () => { flash(this.button); if (this.open) this.closePanel(); else this.openPanel(); });
  }

  // ── provenance: which activations are the panel's ──────────────────────────────────────────────
  /** Whether the panel made `x`: a control inside its aside (none before the first open), or a highlight or
   *  picture frame it painted into the body (marks). Anything else under the delegate root is the file's own
   *  markup, whatever data-act it carries — the sanitizer keeps data-* attributes, and a class name proves
   *  nothing either. */
  owns(x: Element): boolean {
    return (this.root !== null && this.root.contains(x)) || this.marks.has(x);
  }
  /** The handlers, each routed only for an element the panel owns. The delegate helper has already flashed
   *  the element by then (a cosmetic pulse); nothing else happens for the file's markup. */
  private own(acts: Record<string, ActionHandler>): Record<string, ActionHandler> {
    const out: Record<string, ActionHandler> = {};
    for (const k of Object.keys(acts)) out[k] = (x, ev) => { if (this.owns(x)) acts[k](x, ev); };
    return out;
  }

  // ── the wire ───────────────────────────────────────────────────────────────────────────────────
  request(verb: string, args?: Record<string, unknown>, fence?: Record<string, string>): Promise<Reply> {
    const reqId = ++reqSeq;
    const { ctx } = this;
    const msg: Record<string, unknown> = { type: "fileComments", reqId, sid: ctx.sid || undefined, path: ctx.path, verb };
    if (args) msg.args = args;
    if (fence) msg.fence = fence;
    return new Promise<Reply>((ok, fail) => {
      // the reply carries the ask's own reqId (the client's, not the echo) so applyStatus can order it, and
      // whether the ask overlapped a write (set on the pending record by markOverlapped, read when it settles)
      const p: Pending = { verb, ok: (m) => ok({ ...m, reqId, overlapped: p.overlapped === true } as unknown as Reply), fail };
      if (verb === "status") p.deadline = setTimeout(() => this.expire(reqId), STATUS_DEADLINE_MS);   // STATUS_DEADLINE_MS: why, and why status only
      this.pending.set(reqId, p);
      ctx.post(msg);
    });
  }
  /** A status ask past its deadline: failed under `no-answer`, naming the machine whose kernel it went to. */
  private expire(reqId: number): void {
    const p = this.pending.get(reqId);
    if (!p) return;
    this.pending.delete(reqId);
    const machine = hostOf(this.ctx.sid || "") || "this machine";
    p.fail({ code: "no-answer", error: "No answer from the kernel on " + machine + " after " + STATUS_DEADLINE_MS / 1000
      + " s. It may predate file comments: update and restart it, then Reload to ask again." });
  }
  /** The kernel's reply carries two optional texts on a SENT message: `warning` (nothing stamped:
   *  the todo switch is off, or the todo was already settled) and `logWarning` (the comments log
   *  append failed, so the Log and the unsent count will not reflect this send). Both are shown; a
   *  send whose record is missing must never look fully done (CLAUDE.md, fail loudly). */
  requestSend(msg: Record<string, unknown>): Promise<{ queued: boolean; warning?: string; todoStamped: boolean }> {
    const reqId = ++reqSeq;
    const str = (v: unknown) => (typeof v === "string" && v ? v : undefined);
    return new Promise((ok, fail) => {
      // a SENT reply's `warning` is exclusively the nothing-stamped text (contract C2), so its absence is the stamp
      this.pending.set(reqId, { verb: "send", ok: (m) => ok({ queued: m.queued === true, warning: [str(m.warning), str(m.logWarning)].filter(Boolean).join(" ") || undefined,
        todoStamped: !str(m.warning) }), fail });
      this.ctx.post({ ...msg, type: "fileCommentsSend", reqId });
    });
  }
  settle(m: Record<string, unknown>, ok: boolean): void {
    const p = this.pending.get(Number(m.reqId));
    if (!p) return;                                    // an older open's reply, or a stale one — lands nowhere
    this.pending.delete(Number(m.reqId));
    if (p.deadline) clearTimeout(p.deadline);
    if (ok) p.ok(m);
    else p.fail({ code: String(m.code || "failed"), error: String(m.error || "the request failed") });
  }
  /** Fail everything outstanding with `text`; null (a warn that was not a drop of ours) leaves it all in flight. */
  failAll(text: string | null): void {
    if (text === null || !this.pending.size) return;
    const ps = [...this.pending.values()]; this.pending.clear();
    for (const p of ps) { if (p.deadline) clearTimeout(p.deadline); p.fail({ code: "unreachable", error: text }); }
  }

  // ── status ─────────────────────────────────────────────────────────────────────────────────────
  /** The first ask, at mount: mounted hidden, revealed when the kernel answers (the GitHub link's
   *  idiom). A `no-node` refusal keeps the action away for good — the gear's row says why. A kernel that
   *  never answers (one from before this feature, reached through federation for a remote session's file,
   *  or the VS Code extension's local one) is named after STATUS_DEADLINE_MS, the way any other refusal
   *  is: the action appears with the reason as its title and in the panel's head row. */
  probe(): void {
    this.request("status").then((s) => this.applyStatus(s), (e: { code: string; error: string }) => {
      if (e.code === "no-node") return;
      this.statusRefusal = e;
      this.unit.hidden = false;
      this.button.title = "Comments: " + e.error;
      this.errors.set("head", { text: e.error, reload: false });
    });
  }
  /** Replies land in the order their asks were ISSUED, not the order they arrive. The kernel runs each ask
   *  concurrently and answers as each finishes, so a `status` the poll asked (or onSaved, or Reload, or a
   *  send's refresh) can be answered after a later comment or toggle whose reply already carried the
   *  post-write state — and applying it as it came put the panel back a step (the new card gone, Send's count
   *  down) until the next tick saw the store moved against that regressed baseline and re-read it: a card
   *  move on no new information (CLAUDE.md). Two asks are suspect: one OLDER than the applied reply, and one
   *  issued after a write's ask but still unanswered when that write's reply landed (`overlapped`,
   *  markOverlapped) — the kernel runs the two concurrently and the host reads the sidecar without a lock,
   *  so the later ask's run can read the disk before the write and answer after it, and its reqId
   *  alone would have let it land. Either is dropped, unless its own clocks say it read a NEWER disk than what
   *  is showing (its run started late and saw a write the applied reply predates): then it IS new information
   *  and lands. Clocks alone cannot decide the overlapped case: a sidecar gone is a later reading that reads
   *  as older (laterNs), and the vendored CLIs do delete sidecars. Returns whether it was applied. */
  applyStatus(s: Reply): boolean {
    const suspect = s.reqId < this.appliedReq || s.overlapped === true;
    if (this.status && suspect && !newerStatus(s, this.status)) return false;
    this.appliedReq = Math.max(this.appliedReq, s.reqId);
    this.status = s;
    this.statusRefusal = null;
    this.errors.delete("head");                        // a status refusal's row (probe, refresh) is answered by a status
    this.base = pollBaseline(s);
    this.unit.hidden = false;
    this.button.textContent = actionLabel(s);
    this.button.title = s.store ? "Comments and changes kept beside this file" : "Comment on this file, or track a session's changes to it";
    this.ctx.setEditBlocked(editBlockedReason(s.hunks || []));
    this.paintAll();                                   // repaints the highlights and renders the panel
    return true;
  }
  /** Re-ask status. While the ask is out and no status has ever landed, the cards section shows the romp
   *  loader (ui/CLAUDE.md: a wait wears the loader, never a line claiming a read); a refusal leaves the
   *  head's row with Reload, the one way back in — nothing re-asks on its own while status is null.
   *  `slot`: the row whose Reload asked. Over a showing status the cards stay up, so that wait would show
   *  nowhere (the row is gone, the click's pulse goes with its rebuilt button, and the ask may run to
   *  STATUS_DEADLINE_MS) — the slot wears the loader instead, where the row was. The poll's and onSaved's own
   *  re-reads pass no slot: nobody is waiting on those, and a swirl in the head per change the session
   *  makes would only pull the eye. */
  async refresh(slot?: string): Promise<void> {
    const mark = slot && this.status ? slot : null;   // with no status the cards' own loader is the wait
    this.busy.add("status"); if (mark) this.busy.add(mark); this.render();
    try { this.applyStatus(await this.request("status")); }
    catch (err) {
      const e = err as { code: string; error: string };
      this.statusRefusal = e;
      this.errors.set("head", { text: e.error, reload: true });
    } finally { this.busy.delete("status"); if (mark) this.busy.delete(mark); this.render(); }
  }
  /** A write's reply just landed: every status ask still out was issued before it and may have read the disk
   *  before the write (applyStatus). The flag rides the pending record, so a failed or expired ask needs no
   *  cleanup. */
  private markOverlapped(): void {
    for (const p of this.pending.values()) if (p.verb === "status") p.overlapped = true;
  }
  /** A mutating verb needs a status behind it: the fence comes from there, and `""` for an unknown sidecar
   *  would claim it must not exist, so the host would refuse `store-moved` — a reason that is not the reason
   *  (a corrupt sidecar, say). Re-ask first, since the person may have fixed the file since the last answer;
   *  when the answer is still a refusal, refuse here, under the control that asked, with the host's own text.
   *  The caller (mutate) holds the slot busy for the whole call, loader included. */
  private async requireStatus(slot: string): Promise<boolean> {
    if (this.status) return true;
    try { this.applyStatus(await this.request("status")); return true; }
    catch (err) {
      const e = err as { code: string; error: string };
      this.statusRefusal = e;
      this.errors.set(slot, { text: "Nothing written: " + e.error, reload: false });
      return false;
    }
  }

  // ── open / close ───────────────────────────────────────────────────────────────────────────────
  openPanel(): void {
    if (this.open) return;
    this.open = true;
    if (!this.root) this.root = el("div", "fc-panel");
    this.ctx.aside(this.root);
    this.button.classList.add("on"); this.button.setAttribute("aria-pressed", "true");
    if (!this.colors) void this.loadColors();
    this.render();
    void this.refresh();
    this.startPoll();
  }
  closePanel(): void {
    if (!this.open) return;
    this.open = false;
    this.ctx.aside(null);
    this.button.classList.remove("on"); this.button.setAttribute("aria-pressed", "false");
    this.float.hidden = true;
    this.stopPoll();
  }
  dispose(): void {
    this.stopPoll();
    this.float.remove();
    for (const ev of ["mousedown", "touchstart"]) document.removeEventListener(ev, this.hideFloatOnDown, true);
    this.failAll("the file viewer closed");
    if (live === this) live = null;
  }

  // ── the session color map: one GET /sessions per panel open, authorId → name + colour ──────────
  // /sessions lists the LOCAL kernel's sessions; a remote session's authors get the neutral chip (there
  // is no /remote/<host>/sessions route today).
  async loadColors(): Promise<void> {
    this.colors = new Map();
    if (this.ctx.sid && hostOf(this.ctx.sid)) return;
    try {
      const rows = await (await fetch(kernelUrl("/sessions"), { cache: "no-store" })).json();
      if (Array.isArray(rows)) {
        for (const r of rows) {
          if (r && typeof r.id === "string" && typeof r.name === "string") {
            this.colors.set(r.id, { name: r.name, color: typeof r.bg === "string" && typeof r.fg === "string" ? { bg: r.bg, fg: r.fg } : null });
          }
        }
      }
    } catch { /* the chips fall back to their labels */ }
    this.render();
  }
  sessionName(): string {
    const id = this.ctx.identity();
    if (id && id.name) return id.name;
    const c = this.ctx.sid && this.colors ? this.colors.get(bareId(this.ctx.sid)) : null;
    return c ? c.name : "the session";
  }

  // ── the poll ───────────────────────────────────────────────────────────────────────────────────
  startPoll(): void {
    if (this.timer) return;
    this.timer = setInterval(() => { void this.tick(); }, POLL_MS);
    document.addEventListener("visibilitychange", this.catchUp);
    window.addEventListener("resize", this.catchUp);
  }
  stopPoll(): void {
    if (this.timer) { clearInterval(this.timer); this.timer = null; }
    document.removeEventListener("visibilitychange", this.catchUp);
    window.removeEventListener("resize", this.catchUp);
  }
  async tick(): Promise<void> {
    if (!this.open || !this.status || !this.base || this.polling) return;
    if (paneHidden()) { this.tickSkipped = true; return; }
    this.tickSkipped = false;
    this.polling = true;
    try {
      const t = pollTargets(this.status, this.ctx.path);
      const base = this.base;
      const checks: Array<[keyof PollBaseline, string]> = [["file", t.file]];
      if (t.store) checks.push(["store", t.store]);
      if (t.config) checks.push(["config", t.config]);
      let fileMoved = false, moved = false;
      for (const [key, target] of checks) {
        if (this.stopped.has(target)) continue;
        let r: Response;
        try { r = await fetch(fileUrl(target, this.ctx.sid), { method: "HEAD", cache: "no-store" }); }
        catch { continue; }                          // a network blip: the next tick tries again
        const v = headVerdict(r.status, r.headers.get("X-Romp-Mtime-Ns"));
        if (v.kind === "stop") {
          this.stopped.add(target);
          // "checking … for changes", the guide's own words for this loop — never "watching": the row sits under
          // the Track changes toggle, and a tracked file whose refresh stopped is still tracked
          this.errors.set("poll", { text: "Stopped checking " + target + " for changes: the kernel answered " + v.status
            + (v.status === 413 ? " (too large to serve)" : " (not a type it serves)") + ". Reload to try again.", reload: true });
          this.render();
          continue;
        }
        if (v.kind !== "value") continue;
        if (mtimeMoved(base[key], v.value)) { moved = true; if (key === "file") fileMoved = true; }
      }
      if (moved) {
        if (fileMoved) this.ctx.reload();            // the bytes changed under the view — repaint them
        await this.refresh();                        // fresh sidecar, log, and a new baseline
      }
    } finally { this.polling = false; }
  }

  // ── verbs ──────────────────────────────────────────────────────────────────────────────────────
  /** A mutating verb: consent first (decision 5), then the request with the fence from the current
   *  status; an `editing-off` refusal re-offers the consent and retries once; a moved fence re-issues
   *  status and retries once by the same args; a second refusal shows verbatim, with Reload when the
   *  store, file, or config moved. Resolves the fresh status, or null when nothing was written. */
  async mutate(verb: string, args: Record<string, unknown>, slot: string): Promise<Status | null> {
    // one write in flight per control: a second Enter or click during the round trip is not a second
    // write (the host mints a fresh id per `comment`, so a repeat would land twice); Save disables and
    // relabels itself meanwhile (renderComposer), the slot's loader shows for every other control
    if (this.busy.has(slot)) return null;
    this.busy.add(slot); this.errors.delete(slot); this.render();
    try {
      if (!(await this.requireStatus(slot))) return null;
      if (!(await this.ctx.ensureEditingAllowed())) { this.errors.set(slot, { text: "Nothing written: comments need file editing on.", reload: false }); return null; }
      return await this.mutateOnce(verb, args, slot, false);
    } finally { this.busy.delete(slot); this.render(); }
  }
  private async mutateOnce(verb: string, args: Record<string, unknown>, slot: string, retried: boolean): Promise<Status | null> {
    const s = this.status;
    const fence = { storeMtimeNs: s && s.storeMtimeNs !== null ? s.storeMtimeNs : "", configMtimeNs: s && s.configMtimeNs !== null ? s.configMtimeNs : "" };
    try {
      const r = await this.request(verb, args, fence);
      this.markOverlapped();                           // the status asks still out may have read the disk before this write
      this.applyStatus(r);
      return r;
    } catch (err) {
      const e = err as { code: string; error: string };
      if (!retried && e.code === "editing-off") {
        if (await this.ctx.ensureEditingAllowed(e.error)) return this.mutateOnce(verb, args, slot, true);
      } else if (!retried && MOVED.has(e.code)) {
        await this.refresh();
        return this.mutateOnce(verb, args, slot, true);
      }
      this.errors.set(slot, { text: e.error, reload: MOVED.has(e.code) });
      return null;
    }
  }

  // ── Track changes ──────────────────────────────────────────────────────────────────────────────
  /** With no status behind it (refused, or never answered) the toggle showed "off" on nothing: re-ask under
   *  this control the way every other mutating control does (requireStatus: a second refusal is the row under
   *  the toggle, "Nothing written: …"), with the slot's loader for the wait. On an answer, act on what the
   *  click meant — turning tracking ON, since off is what showed: an untracked file gets the scope row; one
   *  that turns out tracked now reads so, which was the ask, and a second click stops it as usual. Never a
   *  click that only pulses (ui/CLAUDE.md: the result follows the acknowledgement). */
  async onTrackClick(): Promise<void> {
    let s = this.status;
    if (!s) {
      if (this.busy.has("track")) return;
      this.busy.add("track"); this.errors.delete("track"); this.render();
      try { if (!(await this.requireStatus("track"))) return; }
      finally { this.busy.delete("track"); this.render(); }
      s = this.status;
      if (!s) return;
      if (!s.trackedBy) { this.trackChoice = true; this.trackStop = false; this.render(); }
      return;
    }
    if (!s.trackedBy) { this.trackChoice = !this.trackChoice; this.trackStop = false; this.render(); return; }
    if (s.trackedBy.kind === "folder") { this.trackStop = !this.trackStop; this.trackChoice = false; this.render(); return; }
    // a file entry turns off directly; an inherited one is refused by the kernel naming the parent — the row shows it
    void this.mutate("set-tracked", { on: false, scope: "file" }, "track");
  }

  // ── commenting ─────────────────────────────────────────────────────────────────────────────────
  onSelection(sel: Selection): void {
    if (!this.open || this.ctx.mode() === "media" || !sel.rangeCount) return;
    // the seam fires for any selection inside the viewer's box, the aside included: a passage is text of the
    // FILE, so a selection in a card, the Log or the message preview offers nothing (it would only be refused)
    const body = this.ctx.body();
    if (!body.contains(sel.anchorNode) || !body.contains(sel.focusNode)) return;
    const rect = sel.getRangeAt(sel.rangeCount - 1).getBoundingClientRect();
    if (!rect.width && !rect.height) return;
    this.imageTarget = null;                           // a text selection replaces a picture as the float's subject
    this.showFloat(rect);
  }
  private showFloat(rect: { right: number; top: number }): void {
    const x = Math.min(Math.max(8, rect.right + 6), window.innerWidth - 90);
    const y = Math.min(Math.max(8, rect.top - 30), window.innerHeight - 34);
    this.float.style.left = x + "px"; this.float.style.top = y + "px";
    this.float.hidden = false;
  }
  /** A click on a rendered picture (the plan's Images and PDFs): with the panel open, the float offers
   *  Comment beside it; the anchor will be the embed's source text. A picture the source holds no embed
   *  for (an `src` the sanitizer rewrote, say) still gets the offer, and the composer then says why it
   *  cannot be placed — the offer must not silently do nothing. */
  onImageClick(img: HTMLElement): void {
    if (!this.open || this.ctx.mode() !== "rendered") return;
    const root = this.contentRoot(); const src = this.ctx.text();
    if (!root || src === null || !root.contains(img)) return;
    const e = embedFor(img, root, src);
    this.imageTarget = { range: e ? { start: e.start, end: e.end } : null };
    this.showFloat(img.getBoundingClientRect());
  }
  startImageComment(range: SourceRange | null): void {
    const src = this.ctx.text();
    if (src === null) return;
    this.openPanel();
    this.composer = range
      ? { kind: "comment", range, quote: src.slice(range.start, range.end), text: src, refusal: null }
      : { kind: "comment", range: null, quote: null, refusal: { ok: false, rawHasQuote: false, selText: "",
          reason: "The line that embeds this image was not found in the source; select it in the Raw view." } };
    this.errors.delete("composer");
    this.repaintPresel();
    this.renderComposer();
    this.input.focus();
  }
  private contentRoot(): Element | null {
    const mode = this.ctx.mode();
    if (mode === "media") return null;
    return this.ctx.body().querySelector(mode === "rendered" ? ".fileview-md" : "code.hljs");
  }
  startComment(sel: Selection): void {
    const src = this.ctx.text(); const root = this.contentRoot();
    if (src === null || !root) return;
    const selText = sel.toString();
    const res = this.ctx.mode() === "rendered" ? mapRenderedSelection(sel, root, src) : mapRawSelection(sel, root, src);
    this.openPanel();
    if (res.ok) this.composer = { kind: "comment", range: res.range, quote: res.quote, text: src, refusal: null };
    else this.composer = { kind: "comment", range: null, quote: null, refusal: { ...res, selText } };
    this.errors.delete("composer");
    this.repaintPresel();
    this.renderComposer();
    this.input.focus();
  }
  startFileComment(): void {
    this.composer = { kind: "comment", range: null, quote: null, refusal: null };
    this.errors.delete("composer");
    this.repaintPresel();
    this.renderComposer();
    this.input.focus();
  }
  startReply(id: string): void {
    const card = this.cards().find((c) => c.id === id);
    if (!card) return;
    this.openCards.add(id);
    this.composer = { kind: "reply", commentId: id, ref: card.ref };
    this.errors.delete("composer");
    this.repaintPresel();
    this.render();
    this.input.focus();
  }
  closeComposer(): void {
    this.composer = null;
    this.input.value = "";
    this.errors.delete("composer");
    this.repaintPresel();
    this.renderComposer();
  }
  /** The mapping refused in Rendered: switch to Raw, and when the selected text occurs in the source,
   *  target that passage — the one in the refused block, not an earlier copy of the same words
   *  (rawTarget) — so the presel mark shows it; otherwise scroll to the block's first line and leave the
   *  note waiting for a Raw selection. */
  switchToRaw(): void {
    const c = this.composer;
    if (!c || c.kind !== "comment" || !c.refusal) return;
    this.ctx.setMode("raw");
    const src = this.ctx.text();
    if (src === null) return;
    const r = c.refusal;
    const range = rawTarget(src, r);
    if (range) {
      c.range = range; c.quote = src.slice(range.start, range.end); c.text = src; c.refusal = null;
      this.errors.delete("composer");                  // an Enter pressed under the refusal is answered now
      this.ctx.scrollToOffset(range.start);
      this.repaintPresel();
      this.renderComposer();
      this.input.focus();
      return;
    }
    if (typeof r.blockStartLine === "number") this.ctx.scrollToOffset(lineStartOffset(src, r.blockStartLine));
    this.renderComposer();
  }
  async saveComposer(): Promise<void> {
    const c = this.composer;
    const note = this.input.value.trim();
    if (!c || !note) return;
    if (c.kind === "comment" && c.refusal) {
      // nothing to save TO: the selection could not be placed, and a save here would silently become a
      // whole-file comment — the passage the person selected lost, and the session told "on this file"
      this.errors.set("composer", { text: "Nothing saved: select the passage in the Raw view first (Switch to Raw), or Cancel and use Comment on this file for a note on the whole file.", reload: false });
      this.renderComposer();
      return;
    }
    let r: Status | null;
    if (c.kind === "reply") r = await this.mutate("reply", { commentId: c.commentId, note }, "composer");
    else {
      const args: Record<string, unknown> = { note };
      // the anchor is built over the text the range indexes (the selection's own, or the reload the passage
      // was re-found in), never over whatever sits at those offsets now; the host re-reads the file and
      // relocates by this anchor and hint, or refuses — a note aimed at one passage never lands on another
      const src = c.text === undefined ? null : c.text;
      if (c.range && src !== null) { args.anchor = makeAnchor(src, c.range); args.hintOffset = c.range.start; }
      r = await this.mutate("comment", args, "composer");
    }
    if (r) this.closeComposer();                       // a refusal keeps the note where it was typed
  }

  // ── highlights ─────────────────────────────────────────────────────────────────────────────────
  cards(): Card[] { return this.status ? cardModel(this.status.store, this.status.hunks || []) : []; }
  /** Paint every open comment's anchor over the current view: located → the ring; quote gone but its
   *  context found → the text-changed ring; neither → card only, marked detached. Detached is a
   *  rendering state, never a stored flag. The composer's pending target is painted last. */
  paintAll(): void {
    this.located = new Map();
    this.unpaint(".fc-hl, .fc-presel");                // a status refresh repaints the SAME body: never wrap twice
    const src = this.ctx.text(); const root = this.contentRoot();
    if (src === null || !root) { this.render(); return; }
    const rendered = this.ctx.mode() === "rendered";
    for (const card of this.cards()) {
      if (card.resolved || !card.anchor) continue;
      const loc = locateComment(src, card.anchor);
      let painted = false;
      if (loc.state !== "detached" && loc.range) {
        const cls = "fc-hl" + (loc.state === "context" ? " fc-hl-context" : "");
        const out = rendered ? paintRendered(root, src, loc.range, cls, { act: "fcopen", id: card.id })
          : paintRaw(root, src, loc.range, cls, { act: "fcopen", id: card.id });
        painted = !!out && out.length > 0;
        // a highlight is a control (it opens the card): reachable by Tab, activated by Enter (KEY_ACTS), and
        // remembered as the panel's own (owns) — the one kind of control it puts among the file's markup
        for (const m of out || []) { (m as HTMLElement).tabIndex = 0; m.setAttribute("role", "button"); (m as HTMLElement).title = "Open the comment on this passage"; this.marks.add(m); }
        if (!painted && rendered) {                    // an embed line renders no text: the frame goes on its picture
          const img = imgForRange(root, src, loc.range);
          if (img) { frameImage(img, cls, { act: "fcopen", id: card.id }); this.marks.add(img); painted = true; }
        }
      }
      this.located.set(card.id, { ...loc, painted });
    }
    this.paintPresel(root, src, rendered);
    this.render();
  }
  private paintPresel(root: Element, src: string, rendered: boolean): void {
    const c = this.composer;
    if (!c || c.kind !== "comment" || !c.range || c.text !== src) return;   // the range indexes c.text; over other bytes it would paint the wrong span
    if (!rendered) { paintRaw(root, src, c.range, "fc-presel"); return; }
    const out = paintRendered(root, src, c.range, "fc-presel");
    if (!out || !out.length) { const img = imgForRange(root, src, c.range); if (img) frameImage(img, "fc-presel"); }
  }
  /** Unwrap painted marks: the text nodes go back in place and the parent is normalized. A framed
   *  picture is stripped of its marks instead — unwrapping an <img> would remove the picture. */
  private unpaint(selector: string): void {
    const marks = selector.split(",").map((s) => s.trim().replace(/^\./, ""));
    for (const n of Array.from(this.ctx.body().querySelectorAll(selector))) {
      if (n.classList.contains("fc-img")) { unframeImage(n as HTMLElement, marks); continue; }
      const p = n.parentNode; if (!p) continue;
      while (n.firstChild) p.insertBefore(n.firstChild, n);
      p.removeChild(n); p.normalize();
    }
  }
  private repaintPresel(): void {
    this.unpaint(".fc-presel");
    const src = this.ctx.text(); const root = this.contentRoot();
    if (src !== null && root) this.paintPresel(root, src, this.ctx.mode() === "rendered");
  }
  /** The body was repainted, possibly over NEW text (the poll saw the file move and reloaded it; Reload;
   *  a refresh): a pending passage is re-found through the anchor of its own text, so the presel, the
   *  chip and the hint follow the passage rather than its old offsets — a note typed while the session
   *  inserts a paragraph above still lands where it was aimed. Not re-found (the passage changed or went):
   *  the selection-time pair is kept, the chip says so, nothing is painted, and Save hands the host that
   *  anchor to rule on — it relocates, or refuses and the note stays. */
  private retargetComposer(): void {
    const c = this.composer; const src = this.ctx.text();
    if (!c || c.kind !== "comment" || !c.range || c.text === undefined || src === null || src === c.text) return;
    const loc = locateComment(src, makeAnchor(c.text, c.range), c.range.start);
    if (loc.state === "located" && loc.range) { c.range = loc.range; c.text = src; }
  }
  goTo(id: string): void {
    const mark = this.ctx.body().querySelector('.fc-hl[data-id="' + id + '"]');
    if (mark) { mark.scrollIntoView({ block: "center" }); return; }
    this.reveal(id);
  }
  /** Reveal: switch to Raw and scroll to the comment's located range — for a comment the Rendered
   *  view could not paint, so the compact card never dead-ends. */
  reveal(id: string): void {
    const loc = this.located.get(id);
    if (!loc || !loc.range) return;
    this.ctx.setMode("raw");
    this.ctx.scrollToOffset(loc.range.start);
  }
  scrollCard(id: string): void {
    this.root?.querySelector('.fc-card[data-id="' + id + '"]')?.scrollIntoView({ block: "nearest" });
  }
  /** The absolute path the kernel acts on, as far as the panel can know it. The kernel resolves the viewer's
   *  path (`~`, a relative chat or todo token against the session's cwd, then realpath) and builds the sent
   *  message from THAT, so the preview and the folder label must name it too (contract C3: identical text).
   *  No reply carries the resolved path itself; the store's own `path` is the file relative to the project
   *  root, written by the host from the resolved path (store-io's relPathFor, corrected on every load), so
   *  root + path IS it whenever a sidecar exists — and a preview needs unsent comments, so one does. With no
   *  sidecar, an absolute viewer path is the kernel's up to a symlink; a relative one names nothing, and the
   *  caller then says less rather than something wrong. */
  filePath(): string | null {
    const s = this.status;
    const rel = s && s.store ? s.store.path : null;
    if (s && s.root && typeof rel === "string" && rel && !rel.startsWith("/")) return s.root.replace(/\/$/, "") + "/" + rel;
    return this.ctx.path.startsWith("/") ? this.ctx.path : null;
  }

  // ── Send to session ────────────────────────────────────────────────────────────────────────────
  /** Fixed sequence (the plan's UX): the message is built from the CURRENT status, then set-tracked
   *  when asked, then fileCommentsSend with `tracked` set to the post-toggle verdict; a refusal at any
   *  step aborts before the send. The comments are already on disk, so a refusal loses nothing. */
  async doSend(): Promise<void> {
    const s = this.status;
    if (!s || this.statusRefusal || this.sending || !this.ctx.sid) return;   // statusRefusal: renderSend says why
    const parts: SendParts = sendParts(s);
    let tracked = !!s.trackedBy;
    this.sending = true; this.errors.delete("send"); this.render();
    try {
      if (this.sendOpts.track && !s.trackedBy) {
        const r = await this.mutate("set-tracked", { on: true, scope: "file" }, "send");
        if (!r) return;
        tracked = !!r.trackedBy;
      }
      const answerTodo = !!this.ctx.todoId && this.sendOpts.todo && !this.todoAnswered;
      const msg: Record<string, unknown> = {
        sid: this.ctx.sid, path: this.ctx.path, tracked, comments: parts.comments,
        accepted: parts.accepted, rejected: parts.rejected, watermark: parts.watermark,
      };
      if (answerTodo) msg.todoId = this.ctx.todoId;
      const reply = await this.sendOnce(msg, false);
      this.markOverlapped();                           // the send appended to the comments log: a status out meanwhile may predate it
      // the latch is the STAMP, not the attempt: a send the kernel warned it could not mark (user todos off,
      // the todo already settled) leaves the checkbox, so the todo is answerable from here once the switch
      // is back on; the settled case re-warns on a later send, honestly, until the kernel says which it was
      if (answerTodo && reply.todoStamped) { this.todoAnswered = true; answeredTodos.add(this.ctx.todoId!); }
      const who = this.sessionName();
      this.sentNote = reply.queued ? "Queued for " + who : "Sent to " + who + " at " + clock(Date.now());
      if (reply.warning) this.errors.set("send", { text: reply.warning, reload: false, warn: true });
      this.sendConfirm = false; this.previewOpen = false;
      await this.refresh();
    } catch (err) {
      this.errors.set("send", { text: (err as { error: string }).error, reload: false });
    } finally { this.sending = false; this.render(); }
  }

  /** The send itself, with the one retry every editing-off refusal gets (mutateOnce's branch): the kernel
   *  refuses a send while file editing is off, because the send's log entry is a disk write and a send the
   *  log cannot record would be offered again (kernel: _file_comments_send_op). The refusal's text carries
   *  the phrase the consent helper matches, so the panel re-offers the consent naming the machine and, on
   *  yes, sends once more; a no, or a second refusal, is the caller's error row. */
  private async sendOnce(msg: Record<string, unknown>, retried: boolean): Promise<{ queued: boolean; warning?: string; todoStamped: boolean }> {
    try { return await this.requestSend(msg); }
    catch (err) {
      const e = err as { code: string; error: string };
      if (!retried && e.code === "editing-off" && await this.ctx.ensureEditingAllowed(e.error)) return this.sendOnce(msg, true);
      throw err;
    }
  }

  // ── render ─────────────────────────────────────────────────────────────────────────────────────
  render(): void {
    if (!this.root || !this.open) return;
    const s = this.status;
    const { head, cards, send, log } = this.sections;
    if (!this.root.contains(head)) this.root.replaceChildren(head, this.composerBox, cards, send, log);   // built once per open
    const keep = this.focusKey();                      // the control holding focus, by identity: the rebuild detaches it
    head.replaceChildren(this.renderHead(s));
    this.renderComposer();
    cards.replaceChildren(this.renderCards(s));
    send.replaceChildren(this.renderSend(s));
    log.replaceChildren(this.renderLog(s));
    if (keep) this.refocus(keep);
  }
  // Every section's children are rebuilt per render, and a removed element loses its focus to the body — so
  // Enter on a card's head opened the card and left the keyboard nowhere: the second Enter did nothing (or
  // fell through to the chat's composer), and the person had to Tab back in after every toggle. The composer's
  // input persists for the same reason (the sections comment); the rebuilt controls are re-found instead, by
  // what they ARE — the action plus the id, key or slot that names its subject — never by their node, the way
  // render.ts refocuses the active tab after `#tabs` is rebuilt.
  private focusKey(): { act: string; id?: string; key?: string; slot?: string } | null {
    const a = document.activeElement as HTMLElement | null;
    if (!a || !this.root || !this.root.contains(a) || !a.dataset || !a.dataset.act) return null;
    return { act: a.dataset.act, id: a.dataset.id, key: a.dataset.key, slot: a.dataset.slot };
  }
  private refocus(k: { act: string; id?: string; key?: string; slot?: string }): void {
    if (!this.root || this.root.contains(document.activeElement)) return;   // still focused (the input): nothing to mend
    for (const n of Array.from(this.root.querySelectorAll("[data-act]")) as HTMLElement[]) {
      const d = n.dataset;
      if (d.act !== k.act || d.id !== k.id || d.key !== k.key || d.slot !== k.slot) continue;
      // the first FOCUSABLE match: a collapsed card carries the head's act and id too, but no tabindex
      if ((n.tabIndex >= 0 || n.tagName.toUpperCase() === "BUTTON") && !(n as HTMLButtonElement).disabled) { n.focus({ preventScroll: true }); return; }
    }
  }
  private errRow(slot: string): HTMLElement | null {
    const e = this.errors.get(slot);
    if (!e) return null;
    const row = el("div", "fileview-err fc-err" + (e.warn ? " fc-err-warn" : ""));
    row.dataset.slot = slot;
    const text = el("span", undefined, e.text);
    text.style.overflowWrap = "anywhere";              // the host names paths in its refusals; the poll names its target
    row.appendChild(text);
    if (e.reload) { const b = btn("Reload", "fcreload"); b.dataset.slot = slot; b.title = "Read the file and its comments again"; row.appendChild(b); }
    const x = btn("✕", "fcerrx", "fileview-btn fc-x"); x.dataset.slot = slot; x.setAttribute("aria-label", "Dismiss"); row.appendChild(x);
    return row;
  }
  private loader(slot: string): HTMLElement | null {
    if (!this.busy.has(slot)) return null;
    const w = el("div", "fileview-load fc-load");
    w.innerHTML = '<img src="/media/romp-swirl-glyph.svg" alt=""><span>romp</span>'
      + '<i class="fileview-dot"></i><i class="fileview-dot"></i><i class="fileview-dot"></i>';
    return w;
  }
  private chip(author: string, authorId: string | null): HTMLElement {
    if (author === "you") return el("span", "fc-chip fc-chip-you", "you");
    const c = authorId && this.colors ? this.colors.get(authorId) : null;
    const chip = el("span", "fc-chip", c ? c.name : author || "unknown");
    if (c && c.color) { chip.style.background = c.color.bg; chip.style.color = c.color.fg; }
    return chip;
  }
  private renderHead(s: Status | null): HTMLElement {
    const head = el("div", "fc-head");
    const row = el("div", "fc-row");
    const t = btn("Track changes", "fctrack", "fileview-btn fc-toggle");
    const tb = s?.trackedBy || null;
    t.dataset.on = tb ? "1" : "0";
    t.setAttribute("aria-pressed", tb ? "true" : "false");
    t.textContent = "Track changes" + (tb ? (tb.kind === "folder" ? " · folder" : tb.kind === "inherited" ? " · inherited" : " · on") : "");
    t.title = tb ? (tb.kind === "inherited" ? "Tracked through " + tb.entry + "; turn it off there" : "Tracked by the entry " + tb.entry + "; click to stop")
      : "Record this session's edits to the file as changes you accept or reject";
    row.appendChild(t);
    row.appendChild(btn("Comment on this file", "fcfile"));
    head.appendChild(row);
    if (this.trackChoice && s) {
      const pick = el("div", "fc-row fc-choice");
      pick.appendChild(el("span", "fc-note", "Track:"));
      pick.appendChild(btn("This file", "fctrackfile"));
      // the folder of the path the kernel acts on (filePath); when the panel cannot name it, the label says
      // "Its folder" and no more — the host computes the entry from the real path either way
      const abs = this.filePath();
      const f = btn(abs ? "Its folder " : "Its folder", "fctrackfolder");
      if (abs) { appendPath(f, folderOf(abs)); shrinkable(f); }
      f.title = "Everything under the folder, files not written yet included";
      pick.appendChild(f);
      pick.appendChild(btn("Cancel", "fctrackcancel"));
      head.appendChild(pick);
    }
    if (this.trackStop && s?.trackedBy) {
      const stop = el("div", "fc-row fc-choice");
      const ask = el("span", "fc-note", "Stop tracking everything under ");
      appendPath(ask, s.trackedBy.entry); ask.appendChild(document.createTextNode("?"));
      stop.appendChild(ask);
      stop.appendChild(btn("Stop", "fctrackstop"));
      stop.appendChild(btn("Cancel", "fctrackcancel"));
      head.appendChild(stop);
    }
    for (const n of [this.loader("track"), this.errRow("track"), this.errRow("head"), this.errRow("poll")]) if (n) head.appendChild(n);
    // a Reload from the head's or the poll's row: the slot wears the loader where the row was, until the answer (refresh)
    for (const n of [this.loader("head"), this.loader("poll")]) if (n) head.appendChild(n);
    if (s && s.agentTooling === "absent") {
      head.appendChild(el("div", "fc-warn", "The session cannot reply to comments yet: the track-changents tooling is not linked into ~/.claude on the file's machine. Run romp's install.sh there."));
    }
    return head;
  }
  private renderComposer(): void {
    const c = this.composer;
    const box = this.composerBox;
    box.hidden = !c;
    if (!c) return;
    const ref = this.composerRef;
    ref.replaceChildren();
    if (c.kind === "reply") ref.appendChild(el("span", "fc-note", "Reply on " + c.ref));
    else if (c.refusal) {
      ref.appendChild(el("span", "fc-note fc-refused", c.refusal.reason));
      const sw = btn("Switch to Raw", "fcraw");
      sw.title = c.refusal.rawHasQuote ? "Raw view, with this passage selected" : "Raw view, scrolled to the block; select the passage there";
      ref.appendChild(sw);
    } else if (c.quote) {
      const q = el("span", "fc-quote", c.quote.replace(/\s+/g, " ").trim());
      q.title = c.quote;
      ref.appendChild(el("span", "fc-note", "On "));
      ref.appendChild(q);
      if (c.range && c.text !== undefined && c.text !== this.ctx.text()) {   // the file changed and the passage was not re-found in it (retargetComposer)
        const t = el("span", "fc-tag", "passage changed");
        t.title = "The file changed and this passage was not found in it; Save asks the file's machine to place it, and refuses if it cannot";
        ref.appendChild(t);
      }
    } else ref.appendChild(el("span", "fc-note", "On this file"));
    const acts = this.composerActs;
    const saving = this.busy.has("composer");
    const save = btn(saving ? "Saving…" : "Save", "fcsave");
    save.disabled = saving;                            // posts-and-waits: disabled and relabeled for the round trip (ui/CLAUDE.md)
    this.input.readOnly = saving;                      // what is typed during the round trip would be lost with the note that lands
    // a refused mapping has nothing to save to — Raw or Cancel; Save would silently write a whole-file comment
    acts.replaceChildren(...(c.kind === "comment" && c.refusal ? [] : [save]), btn("Cancel", "fccancel"));
    const err = this.composerErr;
    err.replaceChildren(...[this.loader("composer"), this.errRow("composer")].filter((n): n is HTMLElement => !!n));
    if (!box.contains(this.input)) box.replaceChildren(ref, this.input, acts, err);   // built once; the input keeps its focus across renders
  }
  private renderCards(s: Status | null): HTMLElement {
    const list = el("div", "fc-cards");
    const cards = this.cards();
    if (!s) {
      // a wait wears the romp loader while a status ask is out (refresh); once the kernel refused, say what
      // follows — the reason and Reload are the head's row. Never a line claiming a read nothing is making.
      const w = this.loader("status");
      if (w) list.appendChild(w);
      else if (this.statusRefusal) list.appendChild(el("div", "fc-empty", "The comments could not be read, so none can be shown or written."));
      return list;
    }
    if (!cards.length) {
      list.appendChild(el("div", "fc-empty", this.ctx.mode() === "media"
        ? "No comments yet. Comment on this file to leave one."
        : "No comments yet. Select a passage and press Comment, or comment on this file."));
      return list;
    }
    const open = cards.filter((c) => !c.resolved), done = cards.filter((c) => c.resolved);
    for (const c of open) list.appendChild(this.renderCard(c));
    if (done.length) {
      const fold = btn((this.resolvedOpen ? "▾ " : "▸ ") + "Resolved (" + done.length + ")", "fcresolved", "fc-sec");
      list.appendChild(fold);
      if (this.resolvedOpen) for (const c of done) list.appendChild(this.renderCard(c));
    }
    return list;
  }
  private renderCard(c: Card): HTMLElement {
    const isOpen = this.openCards.has(c.id);
    const loc = this.located.get(c.id);
    const card = el("div", "fc-card" + (isOpen ? " open" : "") + (loc && loc.state === "detached" ? " fc-card-detached" : ""));
    card.dataset.id = c.id;
    // the expand/collapse target: the whole card while collapsed, the HEAD alone once open — the open body
    // is text to select and copy (the sheet gives it cursor: text), and a click there must not fold the card
    // away from under the selection. The head is a Tab stop and takes Enter/Space (KEY_ACTS).
    if (!isOpen) card.dataset.act = "fccard";
    const head = el("div", "fc-card-head");
    head.dataset.id = c.id; head.dataset.act = "fccard";
    head.tabIndex = 0; head.setAttribute("role", "button"); head.setAttribute("aria-expanded", isOpen ? "true" : "false");
    head.appendChild(this.chip(c.author, c.authorId));
    const ref = el("span", "fc-ref", c.kind === "passage" ? "“" + c.ref + "”" : c.ref);
    ref.title = c.kind === "passage" ? c.anchor?.quote || c.ref : c.ref;
    if (c.anchor && loc && loc.painted) {
      ref.dataset.act = "fcgoto"; ref.dataset.id = c.id; ref.classList.add("fc-link"); ref.title = "Scroll to the passage";
      ref.tabIndex = 0; ref.setAttribute("role", "button");
    }
    head.appendChild(ref);
    if (loc && loc.state === "context") head.appendChild(el("span", "fc-tag", "text changed"));
    if (loc && loc.state === "detached") head.appendChild(el("span", "fc-tag", "detached"));
    if (c.resolved) head.appendChild(el("span", "fc-tag", "resolved"));
    if (c.replies.length && !isOpen) head.appendChild(el("span", "fc-tag fc-count", String(c.replies.length)));
    head.appendChild(el("span", "fc-time", clock(c.ts)));
    card.appendChild(head);
    if (!isOpen) { card.appendChild(el("div", "fc-preview", c.body.replace(/\s+/g, " ").trim())); return card; }
    card.appendChild(el("div", "fc-body", c.body));
    if (c.replies.length) {
      const rs = el("div", "fc-replies");
      for (const r of c.replies) {
        const row = el("div", "fc-reply" + (r.author === "you" ? " fc-reply-you" : ""));
        const meta = el("div", "fc-meta");
        meta.appendChild(this.chip(r.author, r.authorId));
        meta.appendChild(el("span", "fc-time", clock(r.ts)));
        row.appendChild(meta);
        row.appendChild(el("div", "fc-body", r.body));
        rs.appendChild(row);
      }
      card.appendChild(rs);
    }
    const acts = el("div", "fc-actions");
    const reply = btn("Reply", "fcreply"); reply.dataset.id = c.id; acts.appendChild(reply);
    const res = btn(c.resolved ? "Reopen" : "Resolve", "fcresolve"); res.dataset.id = c.id; res.dataset.on = c.resolved ? "0" : "1"; acts.appendChild(res);
    const src = this.ctx.text();
    if (c.anchor && loc && loc.range && !loc.painted) {
      const rv = btn("Reveal", "fcreveal"); rv.dataset.id = c.id;
      rv.title = "Show the passage in the Raw view" + (src !== null ? " (line " + (rawOffsetToLine(src, loc.range.start) + 1) + ")" : "");
      acts.appendChild(rv);
    }
    card.appendChild(acts);
    for (const n of [this.loader("card:" + c.id), this.errRow("card:" + c.id)]) if (n) card.appendChild(n);
    return card;
  }
  private renderSend(s: Status | null): HTMLElement {
    const box = el("div", "fc-send");
    const n = s ? unsentCount(s.unsent) : 0;
    const b = btn(this.sending ? "Sending…" : "Send to session" + (n ? " (" + n + ")" : ""), "fcsend");
    // a status refusal (refresh, requireStatus) leaves the LAST status showing so the cards stay readable, but
    // what is unsent was derived from a disk the kernel can no longer read for us: a file deleted or moved
    // since, a sidecar gone corrupt. A send built from that would go out and be recorded (or re-recorded)
    // against a state that may no longer hold — the duplicate-send leg of the review's finding — so Send
    // stands down until a fresh status lands (applyStatus clears the refusal; Reload in the head asks).
    const stale = !!this.statusRefusal;
    b.disabled = !s || !n || this.sending || !this.ctx.sid || stale;
    b.title = !this.ctx.sid ? "No session owns this file; open it from a session's link or todo to send"
      : stale ? "The comments could not be re-read; Reload above, then send"
      : !n ? "Nothing unsent: every comment, reply, and decision has gone" : "Hand everything unsent to the session as one message";
    box.appendChild(b);
    // why Send is off, VISIBLE (the GitHub link's caption idiom): a tooltip never reaches touch, and a
    // disabled button takes no focus. Nothing-unsent is captioned only once there are comments to have sent.
    if (!this.ctx.sid) box.appendChild(el("div", "fc-note", "No session owns this file; open it from a session's link or todo to send."));
    else if (stale && s && n) box.appendChild(el("div", "fc-note", "The comments could not be re-read, so nothing can be sent until Reload above succeeds."));
    else if (s && !n && !this.sending && this.cards().length) box.appendChild(el("div", "fc-note", "Nothing unsent: every comment, reply, and decision has gone."));
    if (this.sendConfirm && s && n && !this.sending) {
      const parts = sendParts(s);
      const cf = el("div", "fc-confirm");
      cf.appendChild(el("div", "fc-note", "This goes to " + this.sessionName() + ":"));
      const ul = el("ul", "fc-list");
      for (const c of parts.comments) {
        const li = el("li");
        li.appendChild(el("span", "fc-list-desc", c.desc + ": "));
        li.appendChild(el("span", undefined, c.body.replace(/\s+/g, " ").trim()));
        ul.appendChild(li);
      }
      if (parts.accepted || parts.rejected) ul.appendChild(el("li", undefined, parts.accepted + " accepted, " + parts.rejected + " rejected"));
      cf.appendChild(ul);
      const opts = el("div", "fc-opts");
      if (this.ctx.todoId && !this.todoAnswered) opts.appendChild(this.opt("todo", "answer the todo this file was opened from"));
      if (!s.trackedBy) opts.appendChild(this.opt("track", "turn on tracking so the session's edits come back as changes"));
      if (opts.childNodes.length) cf.appendChild(opts);
      const pv = btn((this.previewOpen ? "▾ " : "▸ ") + "The message", "fcpreview", "fc-sec");
      cf.appendChild(pv);
      if (this.previewOpen) {
        const media = this.ctx.media() === "image" || this.ctx.media() === "pdf";
        const tracked = !!s.trackedBy || this.sendOpts.track;   // the post-toggle verdict the send will carry
        // the path the kernel will name (filePath), never the spelling the viewer was opened with: a relative
        // todo token or a `~/` link would preview a header and two --file arguments the session never receives
        const abs = this.filePath();
        if (abs === null) cf.appendChild(el("div", "fc-note", "The message names this file by its absolute path, which the kernel resolves from " + this.ctx.path + "; this panel cannot show it."));
        else cf.appendChild(el("pre", "fc-msg", buildSendMessage({ absPath: abs, comments: parts.comments, accepted: parts.accepted, rejected: parts.rejected, tracked, media })));
      }
      const acts = el("div", "fc-actions");
      acts.appendChild(btn("Send", "fcsendgo", "fileview-btn fc-primary"));
      acts.appendChild(btn("Cancel", "fcsendcancel"));
      cf.appendChild(acts);
      box.appendChild(cf);
    }
    if (this.sentNote) box.appendChild(el("div", "fc-note fc-sent", this.sentNote));
    for (const x of [this.loader("send"), this.errRow("send")]) if (x) box.appendChild(x);
    return box;
  }
  private opt(key: "todo" | "track", label: string): HTMLElement {
    const l = el("label", "fc-opt");
    const cb = el("input") as HTMLInputElement;
    cb.type = "checkbox"; cb.checked = this.sendOpts[key]; cb.dataset.opt = key;
    l.appendChild(cb); l.appendChild(el("span", undefined, label));
    return l;
  }
  private renderLog(s: Status | null): HTMLElement {
    const box = el("div", "fc-log");
    const rows = s?.log || [];
    box.appendChild(btn((this.logOpen ? "▾ " : "▸ ") + "Log" + (rows.length ? " (" + rows.length + (s?.logTruncated ? "+" : "") + ")" : ""), "fclog", "fc-sec"));
    if (!this.logOpen) return box;
    if (!rows.length) { box.appendChild(el("div", "fc-empty", "Nothing yet: sends, decisions, tracking changes, and direct edits land here.")); return box; }
    const nameOf = (sid: string): string | null => {
      if (this.ctx.sid && bareId(this.ctx.sid) === sid) return this.sessionName();
      const c = this.colors ? this.colors.get(sid) : null;
      return c ? c.name : null;
    };
    // one row per entry is the glance; what the entry holds underneath — the bodies a send carried, the diff of
    // a direct edit — is one click down, keyed so a poll re-render keeps it open (ui/CLAUDE.md: never dead-end)
    for (const e of [...rows].reverse()) {
      const key = String(e.ts) + "|" + String(e.kind);
      const detail = this.logDetail(e);
      const isOpen = !!detail && this.openLog.has(key);
      const row = el("div", "fc-log-row");
      row.appendChild(el("span", "fc-time", clock(e.ts)));
      row.appendChild(el("span", undefined, logRowText(e, nameOf)));
      if (detail) {
        // the row becomes a control; the fold glyph joins its text span, so the row stays time + text (the
        // sheets size it as exactly that) and a re-render keeps it open through openLog
        row.classList.toggle("open", isOpen);
        row.dataset.act = "fclogrow"; row.dataset.key = key;
        row.setAttribute("role", "button"); row.style.cursor = "pointer";
        row.tabIndex = 0; row.setAttribute("aria-expanded", isOpen ? "true" : "false");   // a Tab stop; Enter/Space through KEY_ACTS
        row.title = isOpen ? "Hide" : e.kind === "send" ? "Show what was sent" : "Show the edit";
        (row.childNodes[1] as HTMLElement).textContent = (isOpen ? "▾ " : "▸ ") + logRowText(e, nameOf);
      }
      box.appendChild(row);
      if (detail && isOpen) box.appendChild(detail);
    }
    if (s?.logTruncated) box.appendChild(el("div", "fc-note", "Showing the last " + rows.length + " entries."));
    return box;
  }
  /** What a Log row has underneath, or null when the line IS the whole entry (a tracking toggle). A send
   *  entry holds the comments as they went — each with what it referred to, in the confirm's own list dress;
   *  an edit entry holds the kernel's diff of the direct edit. */
  private logDetail(e: { kind: string; [k: string]: unknown }): HTMLElement | null {
    if (e.kind === "send" && Array.isArray(e.comments) && e.comments.length) {
      const box = el("div", "fc-log-detail");
      const ul = el("ul", "fc-list");
      for (const c of e.comments as Array<Record<string, unknown>>) {
        if (!c || typeof c !== "object") continue;
        const li = el("li");
        li.appendChild(el("span", "fc-list-desc", String(c.desc ?? "on this file") + ": "));
        li.appendChild(el("span", undefined, String(c.body ?? "")));
        ul.appendChild(li);
      }
      box.appendChild(ul);
      return box;
    }
    if (e.kind === "edit") {
      const f = (e.summary && typeof e.summary === "object" ? e.summary : e) as Record<string, unknown>;
      if (typeof f.diff !== "string" || !f.diff) return null;
      const box = el("div", "fc-log-detail");
      box.appendChild(el("pre", "fc-msg", f.diff));
      if (f.truncated === true) box.appendChild(el("div", "fc-note", "The diff was cut short; the file holds the rest."));
      return box;
    }
    return null;
  }
}

// ── the registry entry ─────────────────────────────────────────────────────────────────────────────
// Mounted hidden; the first `status` answer reveals it with the glance label (a `no-node` refusal never
// does — the gear's File comments row names the machine and the reason). Registered by file-view.ts.
export const fileCommentsAction: FileViewAction = {
  id: "file-comments",
  mount(ctx) {
    const unit = el("span", "fileview-fc");
    unit.hidden = true;
    const b = el("button", "fileview-btn", "Comments") as HTMLButtonElement;
    b.type = "button";
    b.setAttribute("aria-pressed", "false");
    unit.appendChild(b);
    new Panel(ctx, b, unit).probe();
    return unit;
  },
};
