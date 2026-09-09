// The file viewer — a big modal over the CHAT pane (the user 2026-08-15: the first cut filled the
// FEED pane, and reading a file cost the cards; the click came out of the chat, so the file presents
// over the chat, ~95% of the pane behind a dimmed backdrop, ✕ top right — and the feed is never touched).
//
// Clicking a file path in the chat used to post `openFile`, which the kernel served by running an
// opener on ITS machine (the user 2026-08-08). Read the dashboard from another device — a laptop
// across the internet, a phone — and that is the wrong screen entirely; on a kernel with no desktop it
// did nothing at all, silently, which is how the user found it. The only place a file can actually be
// shown is the browser you are looking at, so the bytes come over the same `/file` route the image
// previews already use (federation-aware via fileUrl, so a remote session's file is relayed from the
// host that owns it).
//
// Living in the CHAT page also removes a whole relay: the click and the viewer are the same document
// now, so there is no shell forwarding, no feed-pane bring-forward/put-back, and the standalone /chat
// page views files exactly like the framed one. The module stays pane-agnostic on purpose: the file
// BROWSER (file-browse.ts, feed bundle) opens files through this same viewer in the FEED document, so
// whichever bundle imports it gets the identical modal.
import hljs from "highlight.js/lib/core";
import { marked, type Tokens } from "marked";
import { sanitizeMd } from "./md-sanitize";
import { hostOf, bareId, hostNameNodes } from "./host-prefix";
import { fileUrl } from "./preview";
import { openPdfTab, wantsOwnTab } from "./preview";   // a PDF's own tab, and the gesture that asks for it
import { openFileTab, canPreview } from "./preview";   // any file's own tab, for the links inside a shown file, and the web-vs-webview test
import { kernelUrl } from "./media";
import { quoteSrcLabel } from "./docreview";
import { fileCommentsAction, panelMark } from "./file-comments";
import { readPlace, seatPlaceOutcome, type Place } from "./reader-place";   // the reader's place across a paint (Slice 2 of plans/markdown-viewer.md)
import { linkifyFileText, linkMarkdownAnchors, viewerWalkTokens, fragmentTarget, URL_LINK_CLASS, FRAG_LINK_CLASS } from "./file-view-links";
import { selectionOpenIn } from "./path-links";
import { PDF_MAX_BYTES, pdfCapMessage } from "./pdf-cap";   // the pages cap, pure (Slice 4); never the chunk itself
// eslint-disable-next-line @typescript-eslint/no-var-requires
const gclock = require("./gesture-clock.js");   // the gesture clock every settings post stamps through
import { delegate, pressHold } from "./actions";   // pressHold: a fetch landing waits while a pointer is pressed over the body (the reload under a press)
import { resolveDocRelative, joinDocPath, urlTitleParts, headingSlug, uniqueSlugs, LINK_SEL, XLINK_NS, linkHref } from "./md-links";
import { readTextCapped, overCapWords, settleUrlResponse } from "./capped-read";
import { wrapCodeLines, addCopyBtn } from "./code-block";   // a fence's per-line rows and Copy button, the chat's own (code-block.ts; Slice 3 of plans/markdown-viewer.md)
import { fenceCopyQueue, type Fence } from "./fence-source";   // what Copy copies: the fence's text as the note holds it, tabs and all (the Slice 3 review)
import "./viewer-grammars";   // decision 5's six grammars, registered on the bundle's hljs core (rust, go, c, java, sql, toml)

// How long the romp loader may stand over a PDF's pages attempt (showPdfPages) before the viewer gives up on it and shows
// the browser's frame with a line saying so — ui/CLAUDE.md's loading-state rule: the loader fades on the event, with a
// backstop timeout so it can never trap the user. Every other end of that attempt is an event; a render that never
// settles has none (pdf.js puts no deadline on opening a document), so this is the failsafe, sized never to fire in the
// load path. The bytes are already in memory, so the wait is the chunk and its worker fetched once (about two megabytes,
// over a tunnel to a phone at worst) plus pdf.js opening the document and drawing page 1: seconds. The pane loader's
// record sets the floor (kernel.py _pane_spin: an 8 s failsafe fired during normal cold starts, 30 s never has); this
// wait includes a fetch, so twice that.
export const PDF_RENDER_BACKSTOP_MS = 60_000;

// hljs is registered per-bundle. Same language set (and grammar registrations) the chat's fence
// highlighting uses, dup-guarded, so importing this module alongside render.ts costs nothing.
import bash from "highlight.js/lib/languages/bash";
import python from "highlight.js/lib/languages/python";
import javascript from "highlight.js/lib/languages/javascript";
import typescript from "highlight.js/lib/languages/typescript";
import json from "highlight.js/lib/languages/json";
import xml from "highlight.js/lib/languages/xml";
import cssLang from "highlight.js/lib/languages/css";
import markdown from "highlight.js/lib/languages/markdown";
import diff from "highlight.js/lib/languages/diff";
import yaml from "highlight.js/lib/languages/yaml";

for (const [name, lang] of Object.entries({
  bash, sh: bash, shell: bash, python, py: python, javascript, js: javascript,
  typescript, ts: typescript, json, xml, html: xml, css: cssLang, markdown, md: markdown,
  diff, yaml, yml: yaml,
})) {
  try { hljs.registerLanguage(name, lang as any); } catch { /* dup alias */ }
}

// Extension → the hljs language to force. Anything absent is shown unhighlighted rather than guessed:
// highlightAuto on a config file or a log picks a language at random and paints it misleadingly, and a
// wrong highlight reads as information the file does not contain. The last row is decision 5's six grammars
// (viewer-grammars.ts): a `.rs` file's code view reads as a rust fence in a note does.
const LANG: Record<string, string> = {
  py: "python", pyi: "python", js: "javascript", jsx: "javascript", mjs: "javascript",
  cjs: "javascript", ts: "typescript", tsx: "typescript", json: "json", jsonc: "json",
  yaml: "yaml", yml: "yaml", sh: "bash", bash: "bash", zsh: "bash", bats: "bash",
  html: "xml", htm: "xml", xml: "xml", svg: "xml", vue: "xml", css: "css", scss: "css",
  md: "markdown", markdown: "markdown", diff: "diff", patch: "diff",
  rs: "rust", go: "go", c: "c", h: "c", java: "java", sql: "sql", toml: "ini", ini: "ini",
};

function langFor(path: string): string | null {
  const ext = path.slice(path.lastIndexOf(".") + 1).toLowerCase();
  return LANG[ext] || null;
}

// marked is a per-bundle singleton. render.ts makes the SAME calls with the SAME choices — GFM without
// hard breaks, strikethrough only on DOUBLE tildes (marked's stock GFM `del` tokenizer fires on a
// single ~, so prose between two "approximately" tildes renders struck through; GitHub itself only
// strikes ~~double~~) — so configuring here too is an idempotent no-op in the chat bundle, and keeps
// this module correct anywhere it's bundled without render.ts.
marked.setOptions({ gfm: true, breaks: false });
marked.use({
  tokenizer: {
    del(src: string) {
      const m = /^~~(?=\S)([\s\S]*?\S)~~/.exec(src);
      if (!m) return undefined;
      return { type: "del", raw: m[0], text: m[1], tokens: (this as { lexer: { inlineTokens(s: string): unknown[] } }).lexer.inlineTokens(m[1]) };
    },
  },
} as Parameters<typeof marked.use>[0]);

// ── view-format preferences ────────────────────────────────────────────────────────────────────────
// The Raw ⇄ Rendered choice for markdown and the word-wrap toggle persist in localStorage, NOT a kernel
// file — per-browser view state, the same call feed-view-state.ts makes for the feed's open sections (it
// must survive a kernel restart without a round-trip to the thing that just restarted). RENDERED is the
// default for markdown (the user 2026-08-09); Raw stays one click away.
/** Run a paint pass of the viewer as one timed frame of the page's performance collector (ui/webview/perf-telemetry.ts,
 *  window.__rompPerf), under the type `fileview:<why>`: `paint` for a text body painted anew, `reflow` for the panel's
 *  re-paint after the body's width moved. The Files pane gets no frames pushed to it, so this is the only work its
 *  collector times; the cost of a large reviewed file (the panel re-wraps every highlight per pass) then shows per
 *  minute in `romp perf client` under app "files", with the main-thread-free sample the collector takes after an
 *  outermost bracket, instead of a long frame nobody attributed (2026-09-09: a divider drag with a big note open
 *  blocked the main thread for about 20 s and no pane recorded it). On the chat page the same brackets count under the
 *  chat's collector. No collector (a page without one, a stand-in): the pass runs untimed, exactly as before. */
export function perfTimed<T>(why: string, fn: () => T): T {
  let p: any = null;
  try { p = typeof window !== "undefined" ? (window as any).__rompPerf : null; } catch { p = null; }
  return p && typeof p.timed === "function" ? p.timed("fileview:" + why, fn) : fn();
}

const FMT_KEY = "romp:fileviewFmt";
// wrap is GONE from the format state (the user 2026-08-24: "there doesn't need to be a button for
// that") — long lines always soft-wrap; a stored wrap key from the toggle era is simply ignored.
type FileViewFmt = { md: "rendered" | "raw" };

// Any malformed/foreign value reads as the defaults rather than throwing — a corrupt entry may cost the
// stored preference, never the viewer (feed-view-state's parseViewState contract).
function parseFmt(raw: string | null | undefined): FileViewFmt {
  const def: FileViewFmt = { md: "rendered" };
  if (!raw) return def;
  try {
    const o = JSON.parse(raw) as { md?: unknown };
    if (!o || typeof o !== "object") return def;
    return { md: o.md === "raw" ? "raw" : "rendered" };
  } catch { return def; }
}

function loadFmt(): FileViewFmt {
  try { return parseFmt(localStorage.getItem(FMT_KEY)); } catch { return parseFmt(null); }
}

function saveFmt(f: FileViewFmt): void {
  try { localStorage.setItem(FMT_KEY, JSON.stringify(f)); } catch { /* storage full */ }
}

// ── text size (the user 2026-09-07: the rendered markdown had to be zoomable) ──────────────────────
// The viewer's text sizes, as percentages of the page's own size: a FIXED table with ends, not a free
// multiplier, so the buttons, the wheel and the stored value all land on the same few sizes and a size can
// never run away or go negative. 100 is the default and leaves every size exactly as before. The chosen
// step rides the viewer root as `data-fv-text`, and the sheets turn it into the ONE property the text
// views read (`--fv-scale`; the "text size and measure" block in styles.css / feed.css). Persisted like
// the Rendered ⇄ Raw choice above: per browser, in localStorage, under its own key, and any malformed or
// foreign value reads as the default (parseFmt's contract). The value stays a percentage, never a
// multiplier, so the stored text and the readout say the same thing.
export const TEXT_SIZES: readonly number[] = [70, 80, 90, 100, 115, 130, 150, 175, 200];
export const TEXT_SIZE_DEFAULT = 100;
const TEXT_SIZE_KEY = "romp:fileviewTextSize";
/** A stored value back to a step of the table; anything else (absent, garbage, a size the table does not
 *  hold) is the default, so a corrupt entry may cost the preference, never the viewer. */
export function parseTextSize(raw: string | null | undefined): number {
  if (raw === null || raw === undefined) return TEXT_SIZE_DEFAULT;
  const n = Number(String(raw).trim());
  return TEXT_SIZES.includes(n) ? n : TEXT_SIZE_DEFAULT;
}
/** The next step from `pct` in `dir`, clamped at the table's ends: at 200 a +1 answers 200. A `pct` off the
 *  table (never stored, but the function is pure) steps from the default. */
export function stepTextSize(pct: number, dir: 1 | -1): number {
  const at = TEXT_SIZES.indexOf(TEXT_SIZES.includes(pct) ? pct : TEXT_SIZE_DEFAULT);
  return TEXT_SIZES[Math.max(0, Math.min(TEXT_SIZES.length - 1, at + dir))];
}
function loadTextSize(): number {
  try { return parseTextSize(localStorage.getItem(TEXT_SIZE_KEY)); } catch { return TEXT_SIZE_DEFAULT; }
}
function saveTextSize(pct: number): void {
  try { localStorage.setItem(TEXT_SIZE_KEY, String(pct)); } catch { /* storage full */ }
}
// Ctrl/Cmd + wheel over the text is the pointer's way to the same steps. A wheel notch is one event of about
// 100 pixels (Chrome) or a few LINES (Firefox, deltaMode 1); a trackpad pinch (which browsers report as a
// ctrlKey wheel) is a burst of events a few pixels each. Stepping once per event would run a pinch through the
// whole table in a moment, so the deltas are FOLDED: normalized to pixels, summed, and a step is taken each time
// the sum passes WHEEL_STEP_PX (then cleared); a change of direction clears it too, so a reversal does not have to
// pay off the other way's remainder first. Pure over the event's fields, so the fold is testable: `acc` is the
// running sum the caller keeps, `dir` the step to take now (0 for none). Events without the modifier are not
// the gesture (the caller lets them scroll) and never reach this.
export const WHEEL_STEP_PX = 40;
export function foldWheel(e: { deltaY: number; deltaMode: number }, acc: number): { acc: number; dir: 0 | 1 | -1 } {
  const px = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaMode === 2 ? e.deltaY * 400 : e.deltaY;
  if (!px) return { acc, dir: 0 };
  const sum = (acc === 0 || Math.sign(acc) === Math.sign(px)) ? acc + px : px;
  if (Math.abs(sum) < WHEEL_STEP_PX) return { acc: sum, dir: 0 };
  return { acc: 0, dir: sum < 0 ? 1 : -1 };   // wheel up (negative deltaY) is larger, as in every zooming surface
}

function el(tag: string, cls?: string): HTMLElement {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  return e;
}

// The romp loader (swirl + wordmark + three pulsing accent dots), per the loading-state rule: the
// FIRST thing up on any wait, fading the instant real content lands. The viewer's earlier waits
// build this markup inline; the URL viewer reaches for it here.
function loaderEl(): HTMLElement {
  const load = el("div", "fileview-load");
  load.innerHTML = '<img src="/media/romp-swirl-glyph.svg" alt=""><span>romp</span>'
    + '<i class="fileview-dot"></i><i class="fileview-dot"></i><i class="fileview-dot"></i>';
  return load;
}

// The 2 MB body cap for a URL document — a MIRROR of the kernel's _TEXT_MAX_BYTES (kernel.py), which
// is what a local .md is already held to on the /file route. The URL viewer fetches from the browser,
// so no kernel ever sees the body; the cap is applied here — a declared Content-Length refuses before
// the body is read, and otherwise the streaming reader (capped-read.ts) counts the bytes as they
// arrive and cancels the source the moment they pass it. md-url-view.test.ts pins the two numbers equal.
const URL_TEXT_MAX_BYTES = 2 * 1024 * 1024;

// ── raw-mode editing (the file browser's slice 2, the user 2026-08-14) ─────────────────────────────
// The save op rides the WS poster the pane's boot hands initFileView; replies route back to the OPEN
// viewer through these module-level hooks (the viewer itself is a per-open closure).
let post: (m: Record<string, unknown>) => void = () => { /* bound by initFileView */ };

// ── the session the file was opened from (the user 2026-09-03) ────────────────────────────────────
// The viewer knows only a sid, and its openers mostly know no more: the relay branch initFileView
// keeps and the conflict Reload live in this module, the file browser hands over a bare sid. So the
// session's name and colour are RESOLVED from the sid here, through a lookup each hosting document
// registers once at boot beside initFileView (render.ts reads its tab set, feed.ts its session list).
// Unregistered, or a sid the document cannot name, the title bar carries no chip: an identity is
// looked up, never invented.
export interface FileViewIdentity { name: string; color: { bg: string; fg: string } | null }
let identityOf: (sid: string) => FileViewIdentity | null = () => null;
export function setFileViewIdentity(fn: typeof identityOf): void { identityOf = fn; }
/** The tail of a resolver's ladder when its lists hold no row for the sid — the kernel's own
 *  _peer_identity fallback: the sid's first 8 characters as an uncolored stub, a remote sid's `host:`
 *  kept in front so hostNameNodes still renders the host quiet. An empty sid names nothing. */
export function hostStub(sid: string): FileViewIdentity | null {
  const bare = bareId(sid);
  if (!bare) return null;
  const host = hostOf(sid);
  return { name: (host ? host + ":" : "") + bare.slice(0, 8), color: null };
}
// Where a FILE LINK inside a shown file opens (file-view-links.ts marks them; the body's delegate in openFileView
// reads the click): this document's own open when the host registered one (initFileView's `openFile`: the Files
// pane's openHere, so the file enters its Recent list and names its session), else the shared viewer in place,
// replacing the file that carried the link. The same document either way: the person is reading here.
let openLinkedFile: (path: string, sid: string | null, line: number | null, frag: string | null) => void =
  (path, sid, line, frag) => { openFileView(path, sid, { line, frag }); };
let saveSeq = 0;
let editHooks: { reqId: number; logWarning: string | null; saved: (mtimeNs: string, logged: boolean) => void; failed: (err: string, code?: string) => void } | null = null;
// Set by the open viewer: returns false to VETO a close (an editor holding unsaved changes asks
// first). The guard must live in closeFileView itself, because the browser overlay and the Escape
// handler both close through it without knowing an edit is in progress. It runs the editor's own ask
// and then every ask an action registered through the seam (ctx.guardClose: the comments panel's, for a
// note typed and not yet saved), so a close or a replace-open (a link followed inside the shown file, a
// Files-pane row, the shell's relay) meets ONE code path whatever the person has unsaved, and nothing is
// dropped silently (the 2026-09-07 review: a link click under a comment draft replaced the file and the
// draft with it, with no ask).
let closeGuard: (() => boolean) | null = null;
let closeAsks: Array<() => CloseAsk | null> = [];
// ONE live Escape handler at a time. Every open registers its own document-level onKey closure, and
// the previous one must be UNREGISTERED when its viewer goes: the replace path used to leave it
// behind, where — with a NEW viewer up, so its `!getElementById` guard no longer no-ops — its stale
// closure (editing still true from before the replace) ran exitEdit against the new viewer's world
// and nulled the module-level editHooks an in-flight save was waiting on, wedging Save at "Saving…"
// (the conflict-Reload → re-edit → Escape-mid-save journey). Dropped by BOTH exits after their
// dirty guards — closeFileView and the replace path — mirroring the editHooks/gitHooks drops.
let onKeyLive: ((e: KeyboardEvent) => void) | null = null;
function dropOnKey(): void {
  if (onKeyLive) { document.removeEventListener("keydown", onKeyLive); onKeyLive = null; }
}
// ONE live media object URL at a time (images used to render as line-numbered mojibake; now an
// image/PDF view holds its bytes in an object URL). The URL is per-open state, but — like editHooks
// and onKeyLive above — the teardown must be reachable from BOTH exits (closeFileView and the replace
// path), so the open viewer registers its URL here and each exit revokes it. Without the revoke
// every image view leaks its blob for the page's life.
let mediaUrlLive: string | null = null;
function dropMediaUrl(): void {
  if (mediaUrlLive) {
    try { URL.revokeObjectURL(mediaUrlLive); } catch { /* already gone */ }
    mediaUrlLive = null;
  }
}
// Set when the open viewer arrived via the SHELL's viewFile relay (the chat's cards-pane preference,
// render.ts openPath → kernel.py's landing shell): that relay may have brought a toggled-off feed
// pane forward, and only the viewer knows when it closes — so a relay-opened close announces itself
// (viewFileClosed) and the shell restores the pane, the browser's browseClosed contract. In-document
// opens never announce: the browser overlay owns its own restore, and a chat-hosted viewer moved no
// pane. openFileView leaves the flag alone on purpose — a same-viewer replace (the conflict Reload)
// must not eat the restore, and the relay-opened modal covers the browser's rows, so no in-document
// open can slip in underneath before the close consumes it. The announce has ONE suppress — the
// browser handoff in closeFileView: with the browser overlay in this document, "close the viewer"
// means the browser is taking the pane over, and the shell moves the restore onto the browser's
// flag rather than hearing a close that would hide the pane mid-open.
let viaRelay = false;
// ONE in-flight URL read at a time, the same shape as mediaUrlLive: the URL viewer registers its
// AbortController here and BOTH exits (closeFileView and either replace path) abort it, so a modal
// torn down mid-body cancels its fetch and its stream — a stale read must never keep pulling bytes
// for a viewer that is gone.
let urlAbort: AbortController | null = null;
function dropUrlRead(): void {
  if (urlAbort) {
    try { urlAbort.abort(); } catch { /* already settled */ }
    urlAbort = null;
  }
}

// ── viewer action registry (the user 2026-08-22) ── INTERNAL SEAM, no compatibility promise:
// reshape freely. Anything acting on the OPEN file declares itself here instead of hand-wiring into
// openFileView's action row, where every file-viewer change used to collide. mount() runs once per
// open and returns the action's element for the row (or null to sit this file out); an action that
// answers asynchronously (the GitHub link's kernel ask) mounts a placeholder and fills it in when its
// reply lands. Ordering is registration order, after the built-ins.
// `todoId`: the user todo the file was opened FROM, when it was (the Waiting-on-you pane's detail link,
// plans/file-review.md Slice 0) — so an action can tie its work back to the todo; absent for every other open.
// The rest is THE VIEWER SEAM (plans/file-review.md, "The viewer seam", Slice 1): what the comments
// panel needs of the open viewer beyond its path and sid, handed over as closures over this open's
// state rather than as exports — the viewer stays a per-open closure and the panel never reaches into
// it. Every member is per open; a hook registered through one is dropped with the viewer (onClose).
export interface FileViewActionCtx {
  path: string; sid: string | null; todoId?: string | null;
  /** the `.fileview-body` element: the raw rows (`code.hljs` > `.fv-cl`) or the rendered `.fileview-md` live inside it */
  body(): HTMLElement;
  /** which view the body shows now; "media" for an image/PDF body (the SVG Source view counts as raw) */
  mode(): "raw" | "rendered" | "media";
  /** the text the current view shows (the SVG Source view's decoded XML included); null until the fetch lands, and for media */
  text(): string | null;
  /** the file's mtime at load, nanoseconds AS A STRING (the save fence's own value) */
  mtimeNs(): string;
  /** the kernel's media verdict off the Content-Type: an SVG is shown as an image but is TEXT to the kernel's allowlist */
  media(): "image" | "pdf" | "svg" | null;
  /** the media element the body shows now: the `<img>` for an image (an SVG shown as an image included), the frame
   *  for a PDF; null for every text view (the SVG Source view too), while the loader holds the body, and once a
   *  decode failure's pane has replaced the picture. Read from the body itself, so it is never a stale handle. A PDF
   *  whose pages the chunk is drawing (Slice 4: the Comments panel is open) answers the pages root, `div.fileview-pdf` */
  mediaElement(): HTMLImageElement | HTMLElement | null;
  /** a PDF's page shells while the chunk renders its pages (the Comments panel open): each `div.fileview-pdf-page`
   *  (data-page 1-based, `position: relative`, one `canvas.fileview-pdf-canvas` inside), in page order, as of the latest
   *  onRendered; [] for the browser's frame, for every other file, and while the loader holds the body. The panel puts
   *  one region overlay in each (Slice 4) */
  pdfPages(): HTMLElement[];
  /** the figures inside a Rendered markdown body, in document order, as of the latest onRendered; [] in every other
   *  view. A path figure's `src` (relative or absolute) is the kernel's /file URL by then and its authored value rides
   *  in `data-fv-src` (rewriteFigureSrcs); the figures' own load events are the caller's to await */
  renderedImages(): HTMLImageElement[];
  /** the session the file was opened from, as the hosting document resolves it (the title-bar chip's source) */
  identity(): FileViewIdentity | null;
  /** runs after every paint of the body: a text body at once (open, view switch, reload), a media body once it shows —
   *  an image after its load event (at once when it was already complete), a PDF frame at once (whenShown), a PDF's
   *  pages once page 1 is drawn and then again after every page the chunk draws (so an overlay can attach to each) and
   *  after every later page it could not draw (the chunk removes that page's canvas and puts its notice in the shell; the
   *  overlay leaves with the canvas on this paint, and the card says the page did not render). A Rendered body's figures
   *  are in the DOM by then with their own loads still pending. The panel re-runs its paint pass.
   *  Also once at Edit, as the editor takes the body (Slice 5), with editing() true: the panel's paint pass stands down
   *  then, and its cards, which read editing() at render time, take their edit-mode state from this render (the panel's
   *  own begin() ran before the flip, so its render could not). No other paint while the editor holds the body; the exit's
   *  repaint hands the read-mode state back.
   *  Also after a text view REFLOWS with its text unchanged: a text-size step (the A− / A+ buttons, the wheel) and a
   *  change of the body's width (the pane resized, the aside opening or closing; a ResizeObserver on the body, so the
   *  event is the layout's own, never a timer, folded to one call per animation frame and none when the width is back
   *  where the last call left it). Every position measured from the text has moved by then, so the panel's paint pass
   *  runs again; a media body's own observers (the figure layer's, the PDF chunk's) already cover theirs, and the
   *  editor lays out its own text, so neither reflow fires for those */
  onRendered(cb: () => void): void;
  /** runs on mouseup/touchend with a non-collapsed selection inside the body — BEFORE the quote-chip gate, so it works with no chat pane */
  onSelection(cb: (sel: Selection) => void): void;
  /** runs when a direct edit's save is acknowledged (fileSaved carries `logged` since Slice 1) */
  onSaved(cb: (info: { mtimeNs: string; logged: boolean }) => void): void;
  /** runs once when this open ends — close, Escape, or a replace-open — so per-open timers and listeners leave with it */
  onClose(cb: () => void): void;
  /** the pane's WS poster (saveFile's channel); replies come back as window `message` events, reqId-guarded by the caller */
  post(m: Record<string, unknown>): void;
  /** the file-editing consent, shared with Save (decision 5): see ensureEditingAllowed */
  ensureEditingAllowed(refusal?: string): Promise<boolean>;
  /** Edit refuses with this one-line reason while set (pending changes, Slice 1); null lifts it */
  setEditBlocked(reason: string | null): void;
  /** mount `el` beside the body as the viewer's aside (two columns, folding below on a narrow column); null removes it */
  aside(el: HTMLElement | null): void;
  /** switch a markdown file's view; a no-op for other files and in edit mode */
  setMode(mode: "raw" | "rendered"): void;
  /** scroll the Raw view's row holding source offset `n` into view (callers switch to Raw first) */
  scrollToOffset(n: number): void;
  /** re-fetch bytes and mtime and repaint, keeping the action row and the aside; a no-op in edit mode */
  reload(): void;
  /** whether the viewer is in edit mode: the editor then holds the truth (text() answers its buffer, the marks are its
   *  own), the body is its host, and reload() stands down (plans/file-review.md Slice 5) */
  editing(): boolean;
  /** the panel's half of editing over a tracked file (Slice 5): registered once per open, null removes it. Read at every
   *  Edit and Save, never cached — the panel's status is the truth about what is pending and where Save must go */
  setTrackedEdit(t: TrackedEdit | null): void;
  /** register an ask the viewer puts before this open ends by a close or a replace-open (a link followed inside the
   *  file, a Files-pane row, the shell's relay). The callback answers null when the action has nothing unsaved, else
   *  what to ask (CloseAsk); the VIEWER puts the ask, the way it puts the editor's own unsaved-changes ask, which runs
   *  first: a confirm dialog on the web, and in the VS Code webview (no dialog) the notice bar with `kept`, the thing
   *  kept. A declined ask vetoes the close and the viewer stays as it was. So nothing the person typed is dropped
   *  without a word, in one code path for every host. Per open; dropped with it */
  guardClose(ask: () => CloseAsk | null): void;
}
/** An action's answer to the close guard when it holds something unsaved: `question`, the yes/no put to the person where a
 *  dialog exists ("Discard the unsaved comment on app.py?"), and `kept`, the notice shown where none does and the thing is
 *  kept ("The unsaved comment on app.py is kept: ..."). */
export interface CloseAsk { question: string; kept: string }
/** One decision taken inside the editor (an accept or a reject of a pending change), as the chunk's decisions report
 *  it. "Decisions" is the plan's word for the save verb's two lists and the chunk's canonical name (editor-chunk.ts,
 *  TrackDecisions); the comments log is the OTHER record of these same decisions, on disk, in the host's hands. */
export type EditDecision = { id: string; oldText: string; newText: string };
export type EditDecisions = { accepted: EditDecision[]; rejected: EditDecision[] };
/** What the comments panel hands the viewer for editing over a tracked file (plans/file-review.md Slice 5; the Slice 5
 *  contract, H3 and H4). The viewer knows nothing of sidecars: it mounts the editor with what `begin` returns, and sends
 *  a Save through `save` when `routesSave` says so, `saveFile` otherwise (that path is unchanged byte for byte). */
export interface TrackedEdit {
  /** At Edit: the file's pending changes for the editor to carry as marks — the sidecar's records as the panel's status
   *  holds them, the author → session colour map for the marks (null for a neutral mark), and the words Edit refuses
   *  with when the editor cannot carry them (the Slice 2 wording: an older editor bundle, or a bundle that failed to load).
   *  null when nothing is pending: the editor mounts as for any file. The panel fences the later save on the sidecar as
   *  it stands at this call, since the records ride from it. Asked twice per Edit, both times with editing() still false
   *  (a refusal at either leaves the read view untouched): at the click, before the consent round-trip, and at the mount,
   *  whose records the editor takes. A render the panel does here is therefore a read-mode one; its edit-mode render is
   *  the onRendered the viewer fires once edit mode is entered (enterEdit). */
  begin(): { records: unknown[]; authorColor: (author: string) => string | null; refusal: string } | null;
  /** Whether Save goes through the comments host: the file is tracked or has a sidecar (a comment, a change). */
  routesSave(): boolean;
  /** The save through the host (the `save` verb: the text, the records as the editor holds them, the decisions taken in
   *  it, fenced on sidecar, config and file): resolves the reply's saved fields, rejects with the host's refusal
   *  {code, error}. The panel applies the reply as its status. The resolved value ALSO carries the host's `logWarning`
   *  when a comments-log append failed (or the log could not be read back) on a save that LANDED (file-comments.ts,
   *  saveThroughComments): the viewer puts it in its note bar, as it does the fileSaved reply's — the panel says it in its
   *  head too, but the head is painted only while the aside is open, and a tracked file is edited with the aside closed
   *  by default (the review's dropped-warning finding). The field is read off the value where the ack runs, not named in
   *  this type: file-comments.test.ts pins the member's text below, so the type widens when that pin moves with it. */
  save(content: string, records: unknown[], decided: EditDecisions): Promise<{ mtimeNs: string; logged: boolean }>;
}
export interface FileViewAction { id: string; mount: (ctx: FileViewActionCtx) => HTMLElement | null; }
const fileViewActions: FileViewAction[] = [];
export function registerFileViewAction(a: FileViewAction): void {
  if (!fileViewActions.some((x) => x.id === a.id)) fileViewActions.push(a);
}
// The open viewer's close hooks (the seam's onClose): drained by BOTH exits — closeFileView and the
// replace path — like dropOnKey and dropMediaUrl, so a panel's poll timer cannot outlive its viewer.
let closeHooks: Array<() => void> = [];
function runCloseHooks(): void {
  const hooks = closeHooks; closeHooks = [];
  for (const cb of hooks) { try { cb(); } catch { /* a hook must never keep the viewer from closing */ } }
}

// ── the GitHub link (the user 2026-08-15) — the registry's first entry ─────────────────────────────
// One unit in the action row: the control and, when the kernel gave one, its reason as a caption
// beside it. The OWNING kernel answers the lazy fileGitLink ask, and until it does the unit holds a
// PLACEHOLDER — a dimmed disabled button and the loader's pulsing dots where the caption will go —
// because the check takes up to 3 s when the kernel must ask origin, and an empty slot for that long
// read as the old no-button state (found in review; the loading-state rule). The answer ALWAYS fills
// the slot (the user 2026-09-05, who could not tell an uncommitted file from a broken link when the
// button simply never appeared). A real URL is an anchor — the browser owns the new tab. No URL is
// a real disabled <button>: assistive tech reads the state and the label, and there is no href to
// follow or to go stale. The reason rides in the tooltip AND as the caption, because a tooltip alone
// needs a mouse — touch has no hover, and a disabled button takes no focus — so the caption is what
// makes the reason glanceable, and it is shown whole: the sheet wraps it inside a bounded width, since
// nothing in the unit takes a tap, click or focus that could finish a truncated sentence. A URL
// whose branch is not on origin stays an anchor, dashed, with the note as its caption, since GitHub
// 404s it until the push. One question per open, reqId-guarded; a socket drop while it is out is
// the one thing that loses the reply, and the shim's reconnect event re-asks (initFileView), so the
// placeholder never outlives its wait. Exported for the DOM-shape test.
const GH_REASONLESS = "this kernel predates link reasons; restart it after updating";
/** The note bar's words when a save's late ack finds a new editor mounted over the pre-save file (doSave, the late-ack
 *  branch): what happened, then what Save and Cancel do from here. The bar carries the Reload offer itself. */
export const SAVE_LANDED_UNDER_NEW_EDITOR = "Your earlier save landed after you reopened the editor, so this editor shows the file as it was before that save. "
  + "Save from it will refuse; Cancel shows the saved file.";
let gitSeq = 0;
let gitHooks: { reqId: number; apply: (url: string, reason: string) => void; ask: () => void } | null = null;
export const githubLinkAction: FileViewAction = {
  id: "github-link",
  mount({ path, sid }) {
    const unit = el("span", "fileview-gh");
    // pending: a real disabled button (never an hrefless anchor, which has no role to read) and the
    // loader's three dots in the caption's place; aria-busy names the wait for assistive tech
    const wait = el("button", "fileview-btn") as HTMLButtonElement;
    wait.type = "button"; wait.disabled = true; wait.textContent = "GitHub ↗";
    wait.title = "Checking GitHub…"; wait.setAttribute("aria-label", wait.title);
    const dots = el("span", "fileview-gh-dots");
    for (let i = 0; i < 3; i++) dots.appendChild(el("i", "fileview-dot"));
    unit.setAttribute("aria-busy", "true");
    unit.appendChild(dots); unit.appendChild(wait);
    const reqId = ++gitSeq;
    const ask = () => post({ type: "fileGitLink", path, sid: sid || undefined, reqId });
    gitHooks = {
      reqId,
      ask,
      apply: (url, reason) => {
        let ctl: HTMLElement;
        if (url) {
          const a = el("a", "fileview-btn") as HTMLAnchorElement;
          a.href = url; a.target = "_blank"; a.rel = "noopener";
          a.title = reason ? url + "\n" + reason : url;      // the full URL one hover away, and the note with it
          if (reason) { a.classList.add("fileview-gh-note"); a.setAttribute("aria-label", "GitHub: " + reason); }
          ctl = a;
        } else {
          // an older kernel answers without a reason — say what that means, rather than invent one
          const b = el("button", "fileview-btn") as HTMLButtonElement;
          b.type = "button"; b.disabled = true;
          b.title = "No GitHub link: " + (reason || GH_REASONLESS);
          b.setAttribute("aria-label", b.title);
          ctl = b;
        }
        ctl.textContent = "GitHub ↗";
        const why = reason || (url ? "" : GH_REASONLESS);
        const parts: HTMLElement[] = [];
        if (why) {
          const cap = el("span", "fileview-gh-why");
          cap.textContent = why;                             // whole, wrapped by the sheet — no tooltip to reach for
          parts.push(cap);                                   // before the control: it annotates what follows
        }
        parts.push(ctl);
        unit.replaceChildren(...parts);                      // the placeholder leaves with the wait
        unit.removeAttribute("aria-busy");
      },
    };
    ask();
    return unit;
  },
};
registerFileViewAction(githubLinkAction);
// The comments panel (plans/file-review.md, Slice 1) is the registry's second entry. It is REGISTERED
// HERE, not in its own module: file-comments.ts imports only types from this module, so the two never
// form a runtime cycle (a top-level registerFileViewAction call over there would run before this
// module's table exists in the bundled order).
registerFileViewAction(fileCommentsAction);

/** The file-editing consent, shared by Save and every comment verb (plans/file-review.md, the viewer
 *  seam; decision 5: one consent, the sidecar is a file in the user's project too). Two paths:
 *  - no `refusal`: the FIRST-consent path. The kernel's live flag is read first — never cached, since
 *    another machine's gear may have flipped it meanwhile — and only when it is off does the one popup
 *    ask; a yes broadcasts setFileEditing through the settings mesh (KERNEL_SETTING), so every attached
 *    kernel's write routes open together. A decline changes nothing and is asked again next time —
 *    consent latches only on yes. If /version is unreachable the popup still asks: the kernel-side gate
 *    refuses regardless, so the worst a wrongly-granted yes can do is draw one refused write with its
 *    plain-words error.
 *  - `refusal`: the RE-CONSENT path, for a gate refusal from the kernel that OWNS the file (its error
 *    text contains "file editing is off"). The first path's /version read sees only the LOCAL flag: a
 *    mesh kernel attached AFTER the one yes never heard the broadcast, so it refuses every write with
 *    copy pointing at a popup the local flag keeps from ever re-showing. The same consent is re-offered
 *    here naming the refusing machine; a yes re-broadcasts and the caller retries. Any other refusal
 *    text resolves false at once: there is nothing to re-offer.
 *  The `gt` stamp is the consent's own click, minted through the gesture clock (gesture-clock.js) so it
 *  lands above every stamp this page has seen for the file-editing store (the /version read on the first
 *  path teaches the clock every store's current stamp): federation queues the setting per host across a
 *  down socket, and the kernel orders applies by the stamp, so a flush hours later cannot outrank a
 *  newer gesture. Resolves true when the caller may proceed (or retry). */
export async function ensureEditingAllowed(sid: string | null | undefined, refusal?: string): Promise<boolean> {
  // the copy stays true for comments (decision 5): saves AND comments write disk; only a save is
  // traced to the session at once — comments reach it when sent
  const COPY = "Allow editing files from the dashboard?\n\n"
    + "Saves and comments write straight to disk on the file's machine — and this applies on every machine "
    + "connected here. A session working in that folder is told when you save under it; your comments reach "
    + "it when you send them.\n\n"
    + "You can turn this off later in the settings gear.";
  if (refusal !== undefined) {
    if (!/file editing is off/.test(refusal)) return false;
    const host = sid ? hostOf(sid) : "";
    if (!window.confirm(
      "Editing is off on " + (host ? "“" + host + "”" : "this machine")
      + (host ? " — it may have connected after you allowed editing here" : "") + ".\n\n" + COPY)) return false;
    post({ type: "setFileEditing", enabled: true, gt: gclock.stamp("file-editing") });
    return true;
  }
  let on = false;
  try {
    const v = await (await fetch(kernelUrl("/version"), { cache: "no-store" })).json();
    on = !!v.fileEditing;
    gclock.learnAll(v.settingsGt);   // the same read teaches the clock every store's current stamp
  } catch { /* ask below */ }
  if (on) return true;
  if (!window.confirm(COPY)) return false;
  post({ type: "setFileEditing", enabled: true, gt: gclock.stamp("file-editing") });
  return true;
}

// ── quote a passage into the composer (the user 2026-08-23, the three-verbs consolidation) ────────
// Selecting text in the viewer seeds the SAME labeled quote chip a VS Code editor highlight does:
// the selection posts in the editorSelection shape to the composer's window — this document's, or
// the shell's chat pane (composerWindow below) — so render.ts's existing handler owns the chip end
// to end (no import cycle — the browseFiles precedent), labeled path:line via quoteSrcLabel. From
// there the flow is the chat's own: type a note (or none), Stage, keep going, send once. This
// REPLACED the viewer's separate review layer — the per-file comment store (romp:fileviewComments),
// the painted marks, and the one-shot Submit that assembled a message — because batching notes for
// one hand-off is exactly what quote chips + ⌘⏎ staging already do, and "comment" now means only
// the transcript's live threads.

// The retired store's data would otherwise sit in localStorage forever on every browser that
// ever commented — sweep it on load.
try { localStorage.removeItem("romp:fileviewComments"); } catch { /* storage may be denied */ }

// Where a quote seed lands (2026-09-03, with the Files pane): the composer in THIS document when there
// is one (the chat-hosted viewer posts to its own window, and render.ts's editorSelection handler owns
// the chip end to end); otherwise the SHELL, when this document is framed by one. The Files pane and
// the feed (the file browser's document) host the viewer without a composer, and the shell forwards
// the seed into the chat pane (the editorSelection arm in kernel.py's landing shell). Before this, a
// selection in the feed-hosted viewer was dead air. No composer and no shell (a VS Code webview's
// cross-origin parent throws; a
// standalone pane has none) → null, and the gesture stands down without a fresh read. Presence is the
// DOM id, the Back button's import-free idiom (render.ts's inRompShell keys on the same node).
function composerWindow(): Window | null {
  if (document.getElementById("composer-input")) return window;
  try { if (window.parent !== window && window.parent.document.getElementById("chat-pane")) return window.parent; }
  catch { /* a cross-origin parent (VS Code) is not the romp shell */ }
  return null;
}

export function closeFileView(): void {
  const wrap = document.getElementById("romp-fileview");
  if (!wrap) return;
  if (closeGuard && !closeGuard()) return;   // unsaved edits (or an unsaved comment), and the user chose to keep them
  closeGuard = null;
  closeAsks = [];
  editHooks = null;
  gitHooks = null;                                     // a reply landing after the close decorates nothing
  dropOnKey();                                         // the closing viewer's handler leaves with it
  dropMediaUrl();                                      // an image/PDF view's bytes leave with the viewer
  dropUrlRead();                                       // …and a URL view's in-flight read is cancelled
  runCloseHooks();                                     // the panel's poll and listeners leave with the viewer
  wrap.remove();
  document.body.classList.remove("fileview-open");
  if (viaRelay) {
    viaRelay = false;
    // Ownership handoff (the pre-2026-08-15 suppress, back for the relay era): the BROWSER overlay
    // in this document means this close is openFileBrowse surfacing the listing — the browser owns
    // the pane now (its box is built before it closes us, exactly so this check can see it).
    // Announcing would hand the shell a viewFileClosed at the very moment the browser opens inside
    // the pane and hide it; staying silent lets the shell move the restore obligation onto the
    // browser's own flag (the browseFiles transfer / browseClosed union in kernel.py's landing
    // shell), so the pane still goes back when the browser closes. The tag still clears above: a
    // viewer opened later from the browser's rows is the browser's, not the relay's.
    if (document.getElementById("romp-filebrowse")) return;
    // the shell may have brought the feed pane forward for this view — tell it the view is over;
    // it restores only what IT turned on (__rompFeedWasOffView, kernel.py's landing shell)
    try { if (window.parent !== window) window.parent.postMessage({ romp: "viewFileClosed" }, "*"); }
    catch { /* no shell — then nothing was brought forward */ }
  }
}

/** A click on a file — a path in the chat, a file-browser row — WITH its gesture. A Cmd/Ctrl- or
 *  middle-click on a PDF (or Cmd/Ctrl+Enter on a file-browser row) opens the browser's own tab (preview.ts
 *  openPdfTab); a plain click opens the
 *  viewer below, like an image (the user 2026-09-07). Decided by EXTENSION, synchronously, inside the
 *  gesture: deciding on the fetched Content-Type would lose the gesture, and every browser would then
 *  block the tab. Every clicked file lands here, so this is the one place the choice lives; a relayed
 *  viewFile or a Reload has no gesture and opens the viewer directly. A BLOCKED popup falls through to
 *  the viewer, so the PDF is never unreachable, and a non-PDF is simply not the opener's business.
 *  `open`: the plain click's opener when the hosting document has its own (the file browser's BrowseHost.openFile,
 *  which the Files pane routes through files.ts openHere); absent, the viewer here. The gesture is read first either
 *  way, so a modified click on a PDF means the tab whichever document hosts the browser. */
export function openFileClick(ev: MouseEvent | KeyboardEvent | null | undefined, path: string, sid?: string | null,
                              open?: (path: string, sid: string | null) => void): void {
  if (wantsOwnTab(ev) && openPdfTab(path, sid ?? null)) return;
  if (open) open(path, sid ?? null); else openFileView(path, sid);
}

/** Show `path` in a modal over this pane. Re-opening replaces whatever is up — never stacks.
 *  Returns whether the open actually happened: false means the dirty-edit guard kept the PREVIOUS
 *  viewer, whose provenance the caller must not touch (initFileView's relay branch keys viaRelay
 *  and the shell's viewFileOpened ack on this verdict — a vetoed relay must neither re-tag the
*  survivor as relay-opened nor arm a restore for an open that never happened).
 *  `opts.todoId`: the user todo the file was opened from (the Waiting-on-you pane's detail link).
 *  `opts.line`: a line the open should show (a `path:12` link in another file, file-view-links.ts): the code view
 *  scrolls its row into view once the text lands; a markdown file opens in its Raw view for THIS open (the Rendered
 *  view has no rows), without touching the saved preference.
 *  `opts.frag`: a sibling link's `#fragment` (`[see](report.md#results)`) to land on after the first rendered paint. */
export function openFileView(path: string, sid?: string | null, opts?: { todoId?: string | null; line?: number | null; frag?: string | null }): boolean {
  // The replace path bypasses closeFileView, so it needs the same dirty ask: opening file B over an
  // edited-but-unsaved file A must not silently eat A's buffer.
  if (document.getElementById("romp-fileview") && closeGuard && !closeGuard()) return false;
  closeGuard = null;
  closeAsks = [];
  editHooks = null;
  gitHooks = null;                                     // the replace path skips closeFileView — same drop
  dropOnKey();                                         // …and the same for the old viewer's Escape handler
  runCloseHooks();                                     // …and the old viewer's panel hooks
  dropMediaUrl();                                      // …and the old viewer's image bytes (the Reload path)
  dropUrlRead();                                       // …and a URL viewer's in-flight read, if that is what was up
  document.getElementById("romp-fileview")?.remove();
  // backdrop (the whole overlay carries the id every open/closed check targets) + the ~95% card.
  // The backdrop treatment matches the lightbox: dimmed, click outside the card closes, content
  // clicks don't (the user 2026-08-15: it must be obvious the chat is still right behind it).
  const wrap = el("div");
  wrap.id = "romp-fileview";
  wrap.onclick = (ev) => { if (ev.target === wrap) closeFileView(); };
  const box = el("div", "fileview");
  // A sibling link's `#fragment` (`[see](report.md#results)`: data-frag on the path link, file-view-links.ts
  // linkMarkdownAnchors) lands on its heading after the FIRST rendered paint — once; a Raw view has no ids to
  // land on, so the landing waits for the Rendered toggle rather than being spent (review find on #958, 2026-09-07).
  let pendingFrag: string | null = opts?.frag || null;
  document.body.classList.add("fileview-open");

  const bar = el("div", "fileview-bar");
  // BACK to the listing (the user 2026-08-24): a file opened FROM the browser overlays it with the
  // listing intact beneath (the one-directional stack above) — closing just the viewer IS the back.
  // The button renders only when a listing is actually underneath; a viewer opened from a path link
  // has nowhere to go back to and shows none. Import-free by design: presence is the DOM id (the
  // browser may not even be loaded in this document).
  if (document.getElementById("romp-filebrowse")) {
    const back = el("button", "fileview-btn fileview-back") as HTMLButtonElement;
    back.type = "button"; back.textContent = "‹ Files"; back.title = "Back to the file listing";
    back.addEventListener("click", () => closeFileView());
    bar.appendChild(back);
  }
  // Directory then basename as TWO elements, because only the directory may be truncated: the filename
  // is what identifies the file, so it never shrinks however deep the path is. (A single text node with
  // the rtl-ellipsis trick would truncate the right end — exactly the wrong half.)
  const name = el("div", "fileview-name");
  name.title = path;                                   // the full path, one hover away
  const cut = path.lastIndexOf("/");
  const dir = el("span", "fileview-dir");
  dir.textContent = cut >= 0 ? path.slice(0, cut + 1) : "";
  const base = el("span", "fileview-base");
  base.textContent = path.slice(cut + 1);
  if (cut >= 0) {
    // The discoverability path into the file BROWSER: the directory half of the title is a click
    // into its listing. Posted to our OWN window — initFileBrowse listens on the same channel the
    // shell relays into, so no import cycle between the two overlays.
    dir.classList.add("fileview-dir-link");
    dir.title = "Browse this file's folder";
    dir.addEventListener("click", () => {
      try { window.postMessage({ romp: "browseFiles", path: path.slice(0, cut) || "/", sid }, "*"); }
      catch { /* messaging our own window cannot really fail */ }
    });
  }
  name.appendChild(dir); name.appendChild(base);
  // The SESSION this file was opened from: a pill in the session's identity colour (the colour its
  // tab wears), "host:" quiet for a remote session (and marked while its link is down). Resolved
  // through the hosting document's registered lookup — no sid, or a sid it cannot name, and there is
  // no chip.
  const owner = sid ? identityOf(sid) : null;
  let sess: HTMLElement | null = null;
  if (owner) {
    sess = el("span", "fileview-sess");
    sess.replaceChildren(...hostNameNodes(owner.name, sid));
    if (owner.color) { sess.style.background = owner.color.bg; sess.style.color = owner.color.fg; }
    sess.title = "Opened from the " + owner.name + " session";
  }
  const acts = el("div", "fileview-acts");

  // ── format toggles (the user 2026-08-09) ── A markdown file opens RENDERED, its Raw form one click
  // away; everything else keeps the code view, whose long lines always soft-wrap (the user 2026-08-24 —
  // no Wrap toggle; edit mode wraps the same way, see enterEdit). The choice persists per browser
  // (FMT_KEY above). These buttons are built once per open and never
  // re-rendered by kernel pushes — the viewer is a static overlay — so direct listeners are click-safe
  // here, same as Copy path below.
  const fmt = loadFmt();
  let text: string | null = null;             // set once the fetch lands; earlier clicks just save the pref
  let mtimeNs = "";                           // the file's mtime at load, NANOSECONDS AS A STRING —
  //   saveFile's conflict floor (ns because whole seconds let a same-second agent write slip the
  //   guard; a string because ~1.7e18 exceeds JS's safe-integer range and a number would round)
  let isText = false;                         // the kernel's verdicts (text/plain AND faithful UTF-8)
  // ── the media verdicts: a .png used to open as line-numbered mojibake — the fetch pipeline called
  // r.text() on ANY 200. All read from the KERNEL's Content-Type, never a client-side extension
  // re-test (the authoritative-source rule; the kernel derives the mime locally and the relay
  // re-derives it, so the header is a verdict, not an echo).
  let isImage = false;                        // image/* → one <img> at an object URL
  let isPdf = false;                          // application/pdf → the lightbox's iframe treatment
  let isSvgImage = false;                     // image/svg+xml exactly — unlocks the Source toggle
  let svgSource = false;                      // the SVG Source view is up (the highlighted XML)
  let svgText: string | null = null;          // the decoded SVG bytes: read on the first toggle, a reload's replace or drop it
  let mediaBlob: Blob | null = null;          // the fetched bytes — the Source toggle decodes THESE, the PDF chunk renders them
  let objUrl: string | null = null;           // this open's object URL (registered as mediaUrlLive)
  // ── the PDF pages (plans/file-review.md Slice 4): with the Comments panel open, a PDF's body is the pages the pdf.js
  // chunk draws (one canvas per page, so a region comment has a page to sit on); closed, it is the browser's own frame
  // as before. `asideOpen` follows the seam's aside() — the panel mounting IS the event — and the body re-renders on the
  // flip. `pdfHandle` is the chunk's render handle (dispose() cancels the draws, releases the worker, removes the root);
  // `pdfSeq` invalidates a chunk load or a render still in flight when the body moved on (a close, a reload, the panel
  // closing), so a late resolution never mounts over what shows now — the editSeq guard's shape. A frame already
  // showing these bytes is kept through both flips (shownFrame, keepShownFrame, showPdfPages): rebuilding it reloads
  // the document at page 1.
  let asideOpen = false;
  let pdfHandle: { pages: number; dispose(): void } | null = null;
  let pdfSeq = 0;
  // The attempt IN FLIGHT — render() called and not yet settled — as the AbortController whose signal rides into
  // render() (`opts.signal`). render() returns no handle until it resolves, and pdf.js puts no deadline on opening a
  // document or drawing a page, so an open or a first-page draw that never settles (the case the backstop below exists
  // for) yields nothing to dispose: the backstop showed the frame and retired the attempt while the Worker pdf.js had
  // started for these bytes ran on at full CPU for the tab's life, one more per attempt on that file (the round-4
  // review). The chunk's side of the contract (pdf-chunk.ts): while render() is unsettled, an abort destroys the
  // loading task, terminates its Worker, leaves nothing in the container and rejects render() with the signal's reason.
  // The abort is part of dropPdf, so every retire of an unsettled attempt — the backstop, the panel closing under the
  // loader, a reload or a reopen over it, both of the viewer's exits — reaches the Worker. Cleared at the mount: from
  // there the handle's dispose() is the release, and the signal is spent.
  let pdfAttempt: AbortController | null = null;
  // showPdfPages's backstop timer (PDF_RENDER_BACKSTOP_MS), one per attempt: disarmed wherever the attempt ends — the
  // pages mounting, a refusal (fallback), or the attempt retired (dropPdf: the panel closing, a reload, both of the
  // viewer's exits) — so it fires only for an attempt that never settled.
  let pdfBackstop: ReturnType<typeof setTimeout> | undefined;
  const disarmBackstop = () => { clearTimeout(pdfBackstop); pdfBackstop = undefined; };
  const abortPdfAttempt = () => { if (pdfAttempt) { pdfAttempt.abort(); pdfAttempt = null; } };
  const dropPdf = () => { pdfSeq++; disarmBackstop(); abortPdfAttempt(); if (pdfHandle) { pdfHandle.dispose(); pdfHandle = null; } };
  // The reader's page, 1-based: the last page the PAGES showed, read off the shells each time they leave the body (the
  // panel closing, a reload) — so the frame the close builds opens on it (#page=N) and the pages a reopen draws scroll
  // to it, instead of both starting the document over at page 1. The browser's frame reports nothing back, so a
  // position taken up inside it is not known here; this is the last one the viewer itself showed.
  let pdfPage = 1;
  // The text the CURRENT view shows: the SVG Source view reads the decoded blob, every other text
  // view reads the fetch pipeline's text. The quote seed's failed-re-read fallback anchors against
  // THIS (a selection in the Source view must find its line in that XML; falling back to `text` —
  // null the whole time media mode is up — would strip every SVG quote's line label).
  const viewText = (): string | null => (svgSource && svgText !== null ? svgText : text);
  let editing = false;
  let dirty = false;
  let eolCRLF = false;                        // the file's dominant line ending — textareas normalize
  //   CRLF→LF on assignment, so an untouched CRLF file would otherwise save with every ending rewritten
  let ta: HTMLTextAreaElement | null = null;   // the FALLBACK surface (and the buffer pre-CodeMirror)
  // the CodeMirror handle when mounted; `track` is on it only when the chunk carried the mount's track option (Slice 5):
  // the records as the field holds them now and the decisions taken since the mount (editor-chunk.ts TrackHandle)
  let cm: { value(): string; focus(): void; destroy(): void; track?: { suggestions(): unknown[]; decisions(): EditDecisions } } | null = null;
  const bufValue = (): string | null => (cm ? cm.value() : ta ? ta.value : null);   // whichever surface owns the buffer
  // ── editing over pending changes (plans/file-review.md Slice 5) ── the comments panel registers its half through the
  // seam (setTrackedEdit); the viewer reads it at Edit and at Save and caches nothing. `chunkTracks` remembers what the
  // loaded editor bundle proved: null until a tracked mount was tried, false once a mount ignored the option (an older
  // bundle) — then Edit refuses in the panel's words while anything is pending, without loading the chunk again.
  let trackedEdit: TrackedEdit | null = null;
  let chunkTracks: boolean | null = null;
  // The chunk's decisions are a fold over every accept and reject since the MOUNT, with no reset (its handle reads
  // only), and a save whose ack lands over in-flight typing keeps the editor — and with it the decisions — alive
  // (hooks.saved). The host has applied what that save carried and written it to the comments log, so `applied`
  // remembers it and `unsent()` is what the next Save may send: the decisions beyond it. Before this the second Save
  // re-sent the same accept, the host logged it twice, and the Send confirm counted two accepted changes for one (the
  // review's duplicate-decision finding). An id is matched within its side: an accept undone and redone after the save
  // sends nothing; an accept undone and turned into a reject sends the reject, and the log then reads accept, reject —
  // what happened. A landed save moves each id it carried to that side (mergeApplied), so a third flip is sent again.
  // Reset with the editor (exitEdit): a fresh mount starts its decisions afresh. An undo that reaches back past a landed
  // save and stops there is the one thing the fold cannot express: see undoneLanded below.
  let applied: EditDecisions = { accepted: [], rejected: [] };
  const beyond = (all: EditDecision[], done: EditDecision[]): EditDecision[] => all.filter((e) => !done.some((d) => d.id === e.id));
  const unsent = (): EditDecisions => {
    const l = cm && cm.track ? cm.track.decisions() : null;
    return l ? { accepted: beyond(l.accepted, applied.accepted), rejected: beyond(l.rejected, applied.rejected) } : { accepted: [], rejected: [] };
  };
  const mergeApplied = (sent: EditDecisions): void => {
    const ids = new Set([...sent.accepted, ...sent.rejected].map((e) => e.id));
    const keep = (l: EditDecision[]) => l.filter((e) => !ids.has(e.id));
    applied = { accepted: [...keep(applied.accepted), ...sent.accepted], rejected: [...keep(applied.rejected), ...sent.rejected] };
  };
  // The records the editor holds that a landed save from this editor ALREADY decided: an undo reached back past that
  // save (the chunk's history has no boundary at a save; undoing a decision puts the record back in the field and takes
  // its entry out of the decisions, editor-chunk.ts). The disk does not follow — the host applied and logged the decision and
  // has no verb that takes one back — so such a record is neither pending nor sendable: among a save's suggestions the
  // host would write it back as pending over a log that says accepted (and count a later accept of it twice), or refuse
  // outright when that save pruned the sidecar (the review's undo-past-a-landed-save finding). So `dirty` counts it (no
  // Save exits over it as "nothing changed": decided() below counts it), the ack that first shows one keeps the editor
  // and says so (hooks.saved — before, an accept undone during the round-trip exited with the accept standing on disk
  // and not a word), and Save refuses in words instead of sending (doSave). The ways out are the person's: redo the
  // decision, decide the change again here (the reversal goes out, and the log reads accept, reject — what happened),
  // or Cancel.
  const undoneLanded = (): { accepted: number; rejected: number } => {
    const recs = cm && cm.track ? cm.track.suggestions() : [];
    const ids = new Set(recs.map((r) => String((r as { id?: unknown }).id)));
    const n = (l: EditDecision[]) => l.filter((e) => ids.has(e.id)).length;
    return { accepted: n(applied.accepted), rejected: n(applied.rejected) };
  };
  const anyUndoneLanded = (u: { accepted: number; rejected: number }): boolean => u.accepted + u.rejected > 0;
  // The words for it, at the ack (`landed`: this save carried the decision) and at a refused Save (an earlier one did).
  const undoneLandedNote = (u: { accepted: number; rejected: number }, landed: boolean): string => {
    const total = u.accepted + u.rejected;
    const what = total > 1 ? "the " + total + " decisions you undid" : u.accepted ? "the accept you undid" : "the reject you undid";
    const again = total > 1 ? "decide the changes again here" : u.accepted ? "reject the change here instead" : "accept the change here instead";
    const it = total > 1 ? "them" : "it";
    const ways = "redo " + it + " (Ctrl/Cmd+Shift+Z), " + again + ", or Cancel to see the file as it was saved.";
    return landed
      ? "Saved, but " + what + " had already landed with this save and cannot be taken back: " + ways
      : "Not saved: " + what + " had already landed with an earlier save and cannot be taken back. " + ways[0].toUpperCase() + ways.slice(1);
  };
  // the decisions the editor holds that disagree with the landed saves: one no save carried (an accept changes no text,
  // so the text comparison alone would call the buffer clean), or one a save carried that an undo took back (undoneLanded)
  const decided = (): boolean => { const u = unsent(); return u.accepted.length + u.rejected.length > 0 || anyUndoneLanded(undoneLanded()); };
  const isMd = langFor(path) === "markdown";  // .md/.markdown — the only kind with a Rendered form
  const segBtns: Array<["rendered" | "raw", HTMLButtonElement]> = [];
  if (isMd) {
    for (const mode of ["rendered", "raw"] as const) {
      const b = el("button", "fileview-btn") as HTMLButtonElement;
      b.type = "button";
      b.textContent = mode === "rendered" ? "Rendered" : "Raw";
      b.title = mode === "rendered" ? "The prose the markdown means" : "The file's actual bytes";
      b.addEventListener("click", () => { fmt.md = mode; saveFmt(fmt); renderBody(); });
      segBtns.push([mode, b]);
      acts.appendChild(b);
    }
  }
  // ── text size (the user 2026-09-07) ── A− and A+ step the text views through TEXT_SIZES; between them the
  // current size, said only once it is not the default, is the reset (progressive disclosure: at 100% there is
  // nothing to reset and nothing to say). The readout's SLOT is there from the start, empty at the default
  // (the sheet's .fileview-size-default, visibility not display): a slot that appeared after the first press
  // moved A− under the pointer, and the second press landed on the reset and undid the first (review
  // 2026-09-07). Built once per open like the format toggles above, so direct listeners are click-safe; each
  // click acknowledges in the same tick (the readout, the dimmed end, the reflow itself). An end of the table
  // is said with aria-disabled, not `disabled`: a button that disables under keyboard focus drops it (the ring
  // vanished on the third Enter, and a fourth did nothing with no visible reason), while an aria-disabled one
  // keeps the focus, wears the sheet's disabled dress, and its click is the no-op setTextSize already makes of
  // a step to the size in force. The three hide until a TEXT body is known (renderBody, off the fetch that
  // brought the kernel's Content-Type: a picture or a PDF opened over a slow link showed them beside the
  // loader and then took them away), with the format toggles in edit mode (the editor keeps its own size) and
  // over a media body (nothing there reads the property); the SVG Source view is a text view and keeps them.
  // The step is applied as `data-fv-text` on the viewer root, which the sheets read (the "text size and
  // measure" block).
  let sizePct = loadTextSize();
  const sizeDown = el("button", "fileview-btn fileview-size") as HTMLButtonElement;
  sizeDown.type = "button"; sizeDown.textContent = "A−"; sizeDown.title = "Smaller text (Ctrl/Cmd + wheel)";
  sizeDown.setAttribute("aria-label", "Smaller text");
  const sizeReset = el("button", "fileview-btn fileview-size fileview-size-reset") as HTMLButtonElement;
  sizeReset.type = "button"; sizeReset.title = "Reset the text size";
  const sizeUp = el("button", "fileview-btn fileview-size") as HTMLButtonElement;
  sizeUp.type = "button"; sizeUp.textContent = "A+"; sizeUp.title = "Larger text (Ctrl/Cmd + wheel)";
  sizeUp.setAttribute("aria-label", "Larger text");
  sizeDown.hidden = true; sizeReset.hidden = true; sizeUp.hidden = true;   // until renderBody knows a text body
  // an end of the table: dimmed and inert, focus kept (the sheet dresses [aria-disabled="true"] as :disabled)
  const atEnd = (b: HTMLButtonElement, end: boolean) => { if (end) b.setAttribute("aria-disabled", "true"); else b.removeAttribute("aria-disabled"); };
  // the property on the root, and the control's own state, from sizePct
  const applyTextSize = () => {
    box.dataset.fvText = String(sizePct);
    sizeReset.textContent = sizePct + "%";
    sizeReset.setAttribute("aria-label", "Text size " + sizePct + "%, reset to " + TEXT_SIZE_DEFAULT + "%");
    atEnd(sizeDown, sizePct === TEXT_SIZES[0]);
    atEnd(sizeUp, sizePct === TEXT_SIZES[TEXT_SIZES.length - 1]);
    sizeReset.classList.toggle("fileview-size-default", sizePct === TEXT_SIZE_DEFAULT);   // the empty slot
  };
  applyTextSize();
  acts.appendChild(sizeDown); acts.appendChild(sizeReset); acts.appendChild(sizeUp);

  // ── the SVG Source toggle ── an SVG is served (and shown) as an image, but it IS also XML worth
  // reading; the toggle swaps in the existing highlighted-code view (langFor maps svg → xml) built
  // from the SAME fetched bytes — no second request. Appears only once an image/svg+xml body landed.
  const srcBtn = el("button", "fileview-btn") as HTMLButtonElement;
  srcBtn.type = "button"; srcBtn.textContent = "Source"; srcBtn.title = "The SVG's XML, highlighted";
  srcBtn.hidden = true;
  srcBtn.addEventListener("click", () => {
    if (svgText === null) {
      if (!mediaBlob) return;
      void mediaBlob.text().then((t) => { svgText = t; svgSource = true; renderBody(); });
      return;
    }
    svgSource = !svgSource;
    renderBody();
  });
  acts.appendChild(srcBtn);

  // ── edit (the raw-mode slice) ── exactly what raw mode can show is what Edit can touch: the
  // button arms only when the kernel served text/plain WITH a Last-Modified to anchor the save's
  // conflict floor (an old remote kernel that mirrors neither gets no Edit rather than an unguarded
  // one). Markdown edits from its Raw view — what you edit is what raw shows.
  const editBtn = el("button", "fileview-btn") as HTMLButtonElement;
  editBtn.type = "button"; editBtn.textContent = "Edit"; editBtn.title = "Edit this file in place";
  editBtn.hidden = true;
  // The consent gate (the user 2026-08-22): editing is a kernel-side opt-in the SAVE ROUTE enforces —
  // the popup where the one yes happens is ensureEditingAllowed (module level, shared with the comments
  // panel's verbs since Slice 1 of plans/file-review.md; its consent post stamps through the gesture clock,
  // and its /version read teaches the clock every store's stamp). While a decision the panel sent is still
  // OUT the button refuses instead, in words, in place (setEditBlocked, held by the panel from the send to the
  // reply: an editor opened meanwhile would carry records that decision is dropping, and no Save from it
  // could land). Slices 2 to 4 held it for every pending change; Slice 5's editor carries those as marks.
  // The button stays a real button rather than a disabled one so the reason reaches touch and keyboard users too.
  let editBlocked: string | null = null;
  // Pending changes enter the editor as marks (Slice 5) — unless the loaded bundle already proved it cannot carry them
  // (chunkTracks false), or the file's CRLF endings would: the editor normalizes them to LF (norm), which moves every
  // offset the records hold, so a save could not fit them back. Both refuse in words, in place, like editBlocked. The
  // CRLF refusal states its consequence literally: it is copy the person acts on (docs/guide.md says the same). The
  // words for what `begin()` returned, or null when the editor may carry it — asked at the CLICK (so a refusal needs no
  // consent popup first) and again at the MOUNT over the begin() whose records the editor takes (enterEdit): the consent
  // read between the two is a kernel round-trip, and a status landing inside it (the poll's tick, the panel's mount-time
  // ask answered, a session's write) turns a click-time "nothing pending" into records. Guarded at the click alone,
  // those records mounted over the LF buffer with their CRLF-disk offsets: marks on the wrong text, a reject rewriting
  // the wrong span, and a save that fit a deletion at a shifted offset (the review's CRLF-at-mount finding).
  const CRLF_REFUSAL = "The editor rewrites this file's CRLF line endings as it loads the text, and that would move the pending changes. ";
  const trackedRefusal = (pending: { refusal: string } | null): string | null => {
    if (!pending) return null;
    if (chunkTracks === false) return pending.refusal;
    if (text !== null && /\r\n/.test(text)) return CRLF_REFUSAL + pending.refusal;
    return null;
  };
  editBtn.addEventListener("click", () => {
    if (editBlocked) { noteBar(editBlocked); return; }
    const refused = trackedRefusal(trackedEdit ? trackedEdit.begin() : null);
    if (refused) { noteBar(refused); return; }
    void ensureEditingAllowed(sid).then((ok) => {
      if (!ok) return;
      enterEdit();
    });
  });
  const saveBtn = el("button", "fileview-btn") as HTMLButtonElement;
  saveBtn.type = "button"; saveBtn.textContent = "Save"; saveBtn.title = "Write the file (Ctrl/Cmd+S)";
  saveBtn.hidden = true;
  saveBtn.addEventListener("click", () => doSave());
  const cancelBtn = el("button", "fileview-btn") as HTMLButtonElement;
  cancelBtn.type = "button"; cancelBtn.textContent = "Cancel"; cancelBtn.title = "Leave edit mode";
  cancelBtn.hidden = true;
  cancelBtn.addEventListener("click", () => { if (confirmDiscard()) exitEdit(); });
  acts.appendChild(editBtn); acts.appendChild(saveBtn); acts.appendChild(cancelBtn);

  // The body row: `.fileview-main` holds the body and, when the comments panel asks for one, the aside
  // beside it (two columns; the sheet folds the aside below the body on a narrow column). The body itself
  // stays the plain overflow block the editor's height: 100% relies on — the row wrapper is what changed.
  const main = el("div", "fileview-main");
  const body = el("div", "fileview-body");
  // A fetch landing rebuilds the body with no gesture of the reader's behind it (a reload the Comments panel's poll asked
  // for after a session's write). A press under way on a fence's Copy, or anywhere in the body, must outlive that swap: a
  // pressed node removed before the mouseup dispatches no click at all (actions.ts, the header), so the landing waits while
  // a pointer is pressed over the body and runs on the release (ui/CLAUDE.md, click-safe option 2;
  // file-view-copy-held-browser.test.ts). The reader's own paints (a view swap, the editor) follow clicks already released.
  const hold = pressHold(body);
  // A rendered document's RELATIVE links (`[notes](./notes.md)`, `[fig](plots/a.png)`) open the sibling file in
  // this same viewer, and its `[top](#evidence)` links land on their heading: mdBlock's file kind sorts every anchor
  // through file-view-links.ts (a path link with the joined path, a section link, a dead link that says why), and
  // ONE listener on the body reads the clicks (below, after the selection wiring: it is installed once per open, so
  // it is click-safe across the Rendered ⇄ Raw swaps that rebuild the body's children). The chat's document-level
  // anchor delegate (render.ts) leaves an anchor with no href alone, so the click reaches here in the chat document
  // and in the feed document alike. The URL viewer below keeps a delegate of its own for its fv-anchor stamp.
  // A submit inside the body never navigates the pane's document. The sanitizer drops <form> and every
  // form control (md-sanitize.ts), so this is the backstop for the one High defect it closes (a note's
  // `<form action=…><button>` took the Files document to the action URL): one listener per open on the
  // stable body, like the click listener below, so it survives every Rendered ⇄ Raw swap.
  body.addEventListener("submit", (ev) => { ev.preventDefault(); });
  // Per the loading-state rule the first thing up is the romp loader, not a blank pane — a file coming
  // over an ssh tunnel to a phone is a real wait.
  const load = el("div", "fileview-load");
  load.innerHTML = '<img src="/media/romp-swirl-glyph.svg" alt=""><span>romp</span>'
    + '<i class="fileview-dot"></i><i class="fileview-dot"></i><i class="fileview-dot"></i>';
  body.appendChild(load);
  main.appendChild(body);

  // ── the viewer seam (FileViewActionCtx) ── closures over THIS open's state. The hook lists are
  // per open; onClose is how a panel's timer or listener leaves with the viewer (runCloseHooks at
  // both exits). renderBody/fetchFile/doSave are declared below and only ever invoked later, never
  // during mount, so the closures may name them here.
  const renderHooks: Array<() => void> = [];
  const selHooks: Array<(sel: Selection) => void> = [];
  const savedHooks: Array<(info: { mtimeNs: string; logged: boolean }) => void> = [];
  const fireRendered = () => { for (const cb of renderHooks) { try { cb(); } catch { /* a hook must never cost the view */ } } };
  // A REFLOW's paint keeps the person's selection. The panel answers onRendered by unwrapping and re-wrapping every
  // highlight (file-comments.ts paintAll), and a selection with an end inside a mark lost that end with the mark's
  // node: 58 selected characters over a highlight came back as 21 after one A+, 45 as 7 after a pane resize (review
  // 2026-09-07, round 2). The text has not changed, only its elements, so each end is kept before the hooks run
  // (keepPoint: its node and offset, its offset into the body's text, and which side of a text node it sat on) and
  // put back after (pointBack), direction kept (setBaseAndExtent), but only when the paint cost the selection an
  // end. A selection the paint left standing (both ends in connected nodes, the same text between them) is not
  // touched: the browser's record of it is exact where the offsets are not. A selection holding NO text (a figure
  // alone, the shape a drag across a picture makes) has one offset for both ends, and put back from them it collapsed
  // after every reflow though the paint had touched nothing near it (review 2026-09-07, round 3); such a selection is
  // never rebuilt from offsets, so when a paint does disturb it, it stays as the paint left it. The test is the text,
  // not the offsets alone: a selection of one line break, from the end of a highlight's text to the next row's first
  // column, has one offset for both ends too, and skipped by the offsets its start was left where the repaint had put
  // it, outside the new mark, so the highlighted word showed and copied with the newline (round 5); its ends go back
  // like any other pair, the side bits below placing the start at the new mark's end. An end whose own node
  // came through the paint (moved into a mark, or untouched) goes back to that node, and only an end whose node is
  // gone is mapped from its offset (round 4: an end on a text-less line boundary, the end of a row's text or the first
  // column of the next, has the offset of both sides, and mapped by its role as start or end it landed on the wrong
  // one, losing the newline between). A collapsed selection, or one with an end outside the body (the bar, the
  // aside's input), is not over the repainted text and is left alone. The paints that REPLACE the body (renderBody)
  // keep nothing: there the text itself is new.
  // Both reflows (a text-size step, the body's width moving under a divider drag or the aside) run through here, so
  // this is where the pass is timed as one fileview:reflow frame of the page's collector (perfTimed): the panel's
  // re-wrap of every highlight is the cost a large reviewed file pays per drag frame, and it shows per minute.
  const fireRenderedKeepingSelection = () => perfTimed("reflow", () => {
    const sel = typeof window.getSelection === "function" ? window.getSelection() : null;
    const kept = sel && !sel.isCollapsed && sel.anchorNode && sel.focusNode && typeof sel.setBaseAndExtent === "function"
      && typeof document.createRange === "function"
      ? { a: keepPoint(body, sel.anchorNode, sel.anchorOffset), f: keepPoint(body, sel.focusNode, sel.focusOffset), text: sel.toString() } : null;
    fireRendered();
    if (!sel || !kept || !kept.a || !kept.f) return;
    if (!sel.isCollapsed && sel.anchorNode?.isConnected && sel.focusNode?.isConnected && sel.toString() === kept.text) return;   // the paint left it standing
    if (kept.a.at === kept.f.at && kept.text === "") return;   // a figure alone: the offsets cannot rebuild it, and would collapse it
    const a = pointBack(body, kept.a, kept.a.at < kept.f.at); const f = pointBack(body, kept.f, kept.f.at < kept.a.at);
    try { sel.setBaseAndExtent(a[0], a[1], f[0], f[1]); } catch { /* a point the layout refuses: the selection stays as the paint left it */ }
  });
  const ctx: FileViewActionCtx = {
    path, sid: sid || null, todoId: opts?.todoId ?? null,
    body: () => body,
    mode: () => (isImage || isPdf) && !(svgSource && svgText !== null) ? "media" : isMd && fmt.md === "rendered" ? "rendered" : "raw",
    text: () => (editing && bufValue() !== null ? bufValue() : viewText()),   // in edit mode the buffer is the text (Slice 5)
    mtimeNs: () => mtimeNs,
    media: () => (isPdf ? "pdf" : isSvgImage ? "svg" : isImage ? "image" : null),
    // both read the LIVE body under the mode gate rather than a handle kept at paint time: a reload swaps the
    // <img>, imgFailed's pane removes it, and a rendered README may itself carry an <img class="fileview-img">
    // through the sanitizer — the gate keeps such a figure from ever answering as the media element
    mediaElement: () => (ctx.mode() === "media" ? body.querySelector("img.fileview-img, iframe.fileview-frame, .fileview-pdf") as HTMLElement | null : null),
    renderedImages: () => (ctx.mode() === "rendered" ? Array.from(body.querySelectorAll(".fileview-md img")) as HTMLImageElement[] : []),
    pdfPages: () => (ctx.mode() === "media" && isPdf ? Array.from(body.querySelectorAll(".fileview-pdf .fileview-pdf-page")) as HTMLElement[] : []),
    identity: () => (sid ? identityOf(sid) : null),
    onRendered: (cb) => { renderHooks.push(cb); },
    onSelection: (cb) => { selHooks.push(cb); },
    onSaved: (cb) => { savedHooks.push(cb); },
    onClose: (cb) => { closeHooks.push(cb); },
    post: (m) => post(m),
    ensureEditingAllowed: (refusal) => ensureEditingAllowed(sid, refusal),
    setEditBlocked: (reason) => {
      editBlocked = reason;
      editBtn.title = reason || "Edit this file in place";
      editBtn.classList.toggle("fileview-btn-blocked", !!reason);
    },
    aside: (node) => {
      main.querySelector(".fileview-aside")?.remove();
      if (node) { node.classList.add("fileview-aside"); main.appendChild(node); }
      // the one width change the viewer sees made: this read lays the new width out, the browser's own scroll adjustment
      // in it, and the reader's place (below) skips the scroll event that reports this number
      asideScrollTop = body.scrollTop;
      // a PDF's body follows the panel (Slice 4): pages while it is open, the frame when it closes. The bytes not yet
      // landed: renderBody's fetch continuation reads the flag and chooses then.
      const was = asideOpen;
      asideOpen = !!node;
      if (isPdf && objUrl !== null && asideOpen !== was) renderBody();
    },
    setMode: (mode) => { if (!isMd || editing) return; fmt.md = mode; saveFmt(fmt); renderBody(); },
    scrollToOffset: (n) => {
      const src = viewText();
      const code = body.querySelector("code.hljs");
      if (src === null || !code) return;
      const rows = code.querySelectorAll(".fv-cl");
      if (!rows.length) return;
      const line = (src.slice(0, Math.max(0, n)).match(/\n/g) || []).length;   // one .fv-cl per logical line
      (rows[Math.min(line, rows.length - 1)] as HTMLElement).scrollIntoView({ block: "center" });
    },
    reload: () => { if (!editing) fetchFile(); },
    editing: () => editing,
    setTrackedEdit: (t) => { trackedEdit = t; },
    guardClose: (ask) => { closeAsks.push(ask); },
  };
  // A text view is showing: the editor does not hold the body, the body is not a picture or a PDF frame, and the
  // text has landed (the SVG Source view counts, its decoded XML being the text). The gate for both reflow
  // triggers below: a paint hook is for a body whose text has positions to re-measure.
  const textShowing = (): boolean => !editing && ctx.mode() !== "media" && viewText() !== null;
  // ── the reader's place (plans/markdown-viewer.md Slice 2; reader-place.ts) ── kept in the file's own terms, the
  // source span of the top-visible block and its height in the body, across every paint of a text view: the swap
  // (renderBody: a view switch, a reload), the width reflow (the observer below) and a text-size step. `shownText` is
  // the text the body's view was PAINTED from, the source readPlace reads it against: a reload has put the new bytes in
  // `text` before renderBody swaps the old view out. `place` is the reader's place under the layout last painted, read
  // again after every seat and, off the body's scroll event, once per frame as the reader moves; the width reflow
  // seats from it, since by the time the observer reports, the layout has changed and the old top block cannot be read.
  // A scroll under a body width the last read did not see, before that repaint, is the browser's own: its anchoring
  // keeping an anchor node's top edge through the reflow, or its clamp as the content got shorter (which reads as a
  // LATER block, the wrong place). Read as the reader's place, either stands in the NEW layout already, so the repaint's
  // seat moves nothing and the reader's depth into the top block is held in pixels where reader-place.ts keeps it as a
  // fraction of the block's height; the aside's close, whose padding write suppresses the anchoring, applied the
  // fraction, so each open of the Comments panel halved the depth and each close kept it (the Slice 2 review, round 2).
  // Skipped, the pre-reflow place stands for the repaint to seat, and the depth is the same fraction in both directions
  // and across a pane drag. One scroll in that window is made on purpose and must not be undone: the panel's reveal
  // (file-comments.ts fcopen: a click on a highlight with the panel closed mounts the aside and centers the mark in one
  // task), which the repaint used to scroll back to the pre-click place one frame later, the text jumping twice and a
  // mark low in the viewport pushed off the screen with its card (round 1). The viewer sees that width change made: the
  // panel mounts the aside through the seam's aside hook, the one place a toggle's width change happens, and the hook
  // reads the body's scrollTop after the mount, which lays the new width out with the browser's adjustment in it, and
  // keeps the number (asideScrollTop). A scroll under the new width that reports that number is the adjustment the hook
  // already saw, and skipped; one that reports another number is a script's after the mount (the reveal) or the
  // reader's, and read, unless it is the clamp, whose landing is the body's end reached from above it, which nothing
  // does on purpose. Under a new width no hook saw (the pane dragged, the window resized) nothing scrolls on purpose in
  // the same task, and every scroll before the repaint is skipped. Round 2 recognised the anchoring by a signature
  // instead, the kept block's top edge within a pixel of where it stood, which holds for a paragraph, a picture or a
  // code block, whose anchor node shares the block's top edge, and not for a table, a list or a blockquote, where the
  // browser anchors on a row, an item or an inner paragraph and the content above it inside the block reflows (round
  // 3: a 40-row table walked two rows up per toggle, 0.4 to 0.35 to 0.298 to 0.243 of its height; a 40-item list 0.4
  // to 0.422; a 12-paragraph blockquote 0.4 to 0.412), and on a drag the table held pixels where the paragraph held
  // the fraction. The hook's number is exact whatever the browser anchored on, and costs one layout per toggle, which
  // the panel's own measurements force in the same task anyway. file-view-place-reveal-browser.test.ts drives the
  // reveal, a width change no hook saw and the clamp; file-view-place-browser.test.ts the toggle and the drag with the
  // reader partway into a paragraph, a picture, a table, a list and a blockquote.
  let shownText: string | null = null;
  let place: Place | null = null;
  let placeWidth = -1;
  let placeScrollTop = -1;
  let placeHeld = false;   // `place` is the one a clamped seat was given, standing while the body stands where the clamp left it (seat, below)
  let asideScrollTop = -1;   // the body's scrollTop as the aside hook (ctx.aside, above) left it, -1 once a read has followed
  const keptPlace = (): Place | null => (shownText === null ? null : placeHeld && place && body.scrollTop === placeScrollTop ? place : readPlace(body, shownText));
  const notePlace = () => { if (shownText !== null && textShowing()) { place = readPlace(body, shownText); placeWidth = body.clientWidth; placeScrollTop = body.scrollTop; placeHeld = false; asideScrollTop = -1; } };
  // A seat the browser CLAMPED (reader-place.ts seatPlaceOutcome: the write asked for more scroll than the view has, and the
  // body stands at its end) keeps the place it was given instead of reading the body: the read would name the block the
  // clamp shows, a paragraph before the reader's, and the next swap would seat THAT, so the Rendered/Raw round trip from
  // the end of the taller view came back one paragraph early (the Slice 3 review: the top block changed and its edge moved
  // 65 to 107px; before the slice the Raw view was the taller and the same clamp drifted the other direction by up to
  // 264px). The held place stands while the body stands where the clamp left it (placeScrollTop): the seat's own scroll
  // event moves nothing and is skipped below, the first scroll that does move it is the reader's and is read, and a swap
  // or a reflow that finds the hold seats the reader's own passage, which the other view can show. Either branch consumes
  // the aside hook's number (asideScrollTop): the seat is the paint the hook's width change led to.
  const seat = (kept: Place | null) => {
    const clamped = kept && shownText !== null ? seatPlaceOutcome(body, shownText, kept).clamped : false;
    if (clamped && kept) { place = kept; placeWidth = body.clientWidth; placeScrollTop = body.scrollTop; placeHeld = true; asideScrollTop = -1; }
    else notePlace();
  };
  const clamped = (): boolean => body.scrollTop < placeScrollTop && body.scrollTop >= body.scrollHeight - body.clientHeight - 1;
  /** A scroll under a new width the aside hook saw made, reporting a scrollTop other than the one the hook read after the
   *  mount: a script's (the reveal) or the reader's, past the browser's own adjustment. */
  const pastAside = (): boolean => asideScrollTop >= 0 && body.scrollTop !== asideScrollTop;
  let placeFrame = 0;
  body.addEventListener("scroll", () => {
    if (placeFrame) return;
    const read = () => {
      placeFrame = 0;
      if (placeHeld && body.scrollTop === placeScrollTop) return;   // the clamped seat's own scroll event: the body has not moved since
      if (body.clientWidth === placeWidth || (pastAside() && !clamped())) notePlace();
    };
    if (typeof requestAnimationFrame === "function") placeFrame = requestAnimationFrame(read); else read();
  }, { passive: true });
  ctx.onClose(() => { if (placeFrame && typeof cancelAnimationFrame === "function") cancelAnimationFrame(placeFrame); placeFrame = 0; });
  // One step of the text size: store it, apply it, and let the panel re-measure over the reflowed text (the
  // seam's onRendered, the same event every text paint fires; the highlights are re-wrapped and the floating
  // Comment button hides, since the passage it sat by has moved; a standing selection is kept across the pass,
  // see fireRenderedKeepingSelection). A step that changes nothing (the table's end) fires nothing: a card may
  // move only on new information (CLAUDE.md), and no paint happened.
  const setTextSize = (pct: number) => {
    if (pct === sizePct) return;
    sizePct = pct;
    saveTextSize(pct);
    const kept = textShowing() ? keptPlace() : null;   // the top block before the text grows or shrinks around it
    applyTextSize();
    if (textShowing()) { fireRenderedKeepingSelection(); seat(kept); }
  };
  sizeDown.addEventListener("click", () => setTextSize(stepTextSize(sizePct, -1)));
  sizeUp.addEventListener("click", () => setTextSize(stepTextSize(sizePct, 1)));
  sizeReset.addEventListener("click", () => setTextSize(TEXT_SIZE_DEFAULT));
  // Ctrl/Cmd + wheel over the BODY (not the bar, not the aside): the browser's page zoom is the same gesture, so it
  // is taken over the viewer's text only, and only with the modifier held; a plain wheel scrolls as ever, and the
  // keyboard's Ctrl+plus/minus stays the browser's. Non-passive so the page zoom can be prevented; the fold is
  // foldWheel's (a pinch is a burst of small deltas).
  let wheelAcc = 0;
  body.addEventListener("wheel", (e: WheelEvent) => {
    if (!(e.ctrlKey || e.metaKey)) return;
    if (!textShowing()) return;
    e.preventDefault();
    const r = foldWheel(e, wheelAcc);
    wheelAcc = r.acc;
    if (r.dir) setTextSize(stepTextSize(sizePct, r.dir));
  }, { passive: false });
  // The body's WIDTH: the Files pane dragged narrower or wider, the aside opening or closing, the window resized.
  // The text reflows (the prose measure follows the pane up to its cap, a table takes the room or scrolls in its
  // own box) and every position measured from it has moved, so the panel's paint pass runs again, off the
  // layout's own report of the change (a ResizeObserver, never a timer). The observer's first report describes
  // the size at observe(), not a change. The repaint is ONE per animation frame: the reports are folded into the
  // next frame (requestAnimationFrame, the frame's own event) and the frame repaints only if the width it finds
  // differs from the one last painted over, so a burst of reports (several observers' entries, a width that
  // moved and came back, the body growing taller as a figure loaded) costs one paint pass or none. The panel's
  // pass re-wraps every highlight and rebuilds its cards (file-comments.ts paintAll, about 10ms with twenty
  // comments), so a drag at one report per frame still pays it per frame; a narrower reaction is the panel's to
  // choose. Media bodies have their own observers (the figure layer's, the PDF chunk's), and the editor its own
  // layout, so textShowing gates this too. Absent ResizeObserver (a stand-in, an old engine) there is no width
  // event to key on, so nothing fires; absent requestAnimationFrame the report itself is the frame.
  if (typeof ResizeObserver !== "undefined") {
    let paintedWidth = -1;   // the width the last repaint (or the first report) saw
    let seenWidth = -1;      // the latest report's width
    let frame = 0;           // the pending frame's handle, 0 for none
    const repaint = () => {
      frame = 0;
      if (seenWidth === paintedWidth) return;   // moved and came back within the frame: no text moved sideways
      paintedWidth = seenWidth;
      if (textShowing()) { fireRenderedKeepingSelection(); seat(place); }   // the place read before the width moved (see notePlace)
    };
    const widthObserver = new ResizeObserver((entries) => {
      const w = entries.length ? entries[entries.length - 1].contentRect.width : body.clientWidth;
      // the body's content width, for the sheets (the pane-wide table's cap, `.fileview-md > table`): on the BODY, which
      // stands for the open (mdBlock rebuilds .fileview-md on every render and no report follows a render), from the
      // layout's own report, one write per report; a scrollbar's width is taken, a reserved gutter is none (Slice 3 review,
      // round 2: `scrollbar-gutter: stable` reserved a blank strip on every body that never scrolls)
      body.style.setProperty("--fv-body-w", w + "px");
      if (paintedWidth < 0) { paintedWidth = w; seenWidth = w; return; }
      seenWidth = w;
      if (w === paintedWidth || frame) return;
      if (typeof requestAnimationFrame === "function") frame = requestAnimationFrame(repaint); else repaint();
    });
    widthObserver.observe(body);
    ctx.onClose(() => { widthObserver.disconnect(); if (frame && typeof cancelAnimationFrame === "function") cancelAnimationFrame(frame); frame = 0; });
  }

  // Registered actions render after the built-ins — the registry walk is the ONE place row
  // conventions live (see registerFileViewAction above). The GitHub link and Comments mount here.
  for (const a of fileViewActions) {
    const n = a.mount(ctx);
    if (n) acts.appendChild(n);
  }

  // ── download (the user 2026-08-09) ── Any linked file can be SAVED, including everything the pane
  // cannot show: the kernel's ?download=1 serves anything on disk (the rationale lives with
  // _file_download in kernel.py). Same-origin and cookie-authed like the view fetch, and
  // federation-aware for free — fileUrl already routes a remote session's file through the relay.
  const dlUrl = fileUrl(path, sid) + "&download=1";
  const dl = el("button", "fileview-btn") as HTMLButtonElement;
  dl.type = "button"; dl.textContent = "Download"; dl.title = "Save this file to your device";
  dl.addEventListener("click", () => startDownload(dlUrl, dl));
  acts.appendChild(dl);

  const copy = el("button", "fileview-btn") as HTMLButtonElement;
  copy.type = "button"; copy.textContent = "Copy path"; copy.title = path;
  copy.addEventListener("click", () => {
    navigator.clipboard?.writeText(path).then(
      () => { copy.textContent = "Copied"; setTimeout(() => { copy.textContent = "Copy path"; }, 1200); },
      () => { copy.textContent = "Copy failed"; });
  });
  const close = el("button", "fileview-btn fileview-close") as HTMLButtonElement;
  close.type = "button"; close.textContent = "✕"; close.title = "Close (Esc)";
  close.setAttribute("aria-label", "Close the file viewer");
  close.addEventListener("click", closeFileView);
  acts.appendChild(copy); acts.appendChild(close);
  bar.appendChild(name); if (sess) bar.appendChild(sess); bar.appendChild(acts);

  box.appendChild(bar); box.appendChild(main);
  wrap.appendChild(box);
  document.body.appendChild(wrap);

  // A one-line notice in the viewer's error dress (the edit-blocked reason, a save failure, a save whose
  // comments-log entry did not land, a line past the end): one at a time, replacing the last. Mounted ABOVE
  // the body row, between the title bar and .fileview-main, never inside the body (plans/markdown-viewer.md
  // Slice 2): inside it the notice scrolled away with the text (at scrollTop 400 it was 400px above the
  // body's top; the past-the-end notice was scrolled out of view by the very landing it explains) and went
  // with the next swap of the body's children. Here it shows at any scroll position and outlives a view
  // switch and a reload; the editor's entry and exit remove it themselves (enterEdit, exitEdit).
  const noteBar = (msg: string): HTMLElement => {
    document.getElementById("fileview-save-err")?.remove();
    const bar2 = el("div", "fileview-err");
    bar2.id = "fileview-save-err";
    bar2.textContent = msg;
    box.insertBefore(bar2, main);
    return bar2;
  };

  // A 200 whose bytes will not DECODE — a zero-byte file, a mid-write/truncated image — fires the
  // img's error event and used to leave the browser's mute broken-image glyph: no reason, no way
  // out. This is the 413/415 pane idiom instead: plain words naming what happened, the path, and
  // the Download the view could not be. Keyed on the img's own error event, the exact deciding
  // signal (never a timer, never a byte sniff). The PDF iframe has no equivalent failure event —
  // the browser's viewer owns that surface and reports inside it — so this covers images only,
  // deliberately.
  const imgFailed = () => {
    if (!wrap.isConnected) return;              // settled after a close/replace — paint nothing
    const why = el("div", "fileview-err");
    why.textContent = "this image failed to decode — it may be mid-write or truncated";
    const hint = el("div", "fileview-err-hint");
    hint.textContent = path;
    why.appendChild(hint);
    const offer = el("button", "fileview-btn fileview-err-dl") as HTMLButtonElement;
    offer.type = "button"; offer.textContent = "Download";
    offer.title = "Save this file to your device";
    offer.addEventListener("click", () => startDownload(dlUrl, offer));
    why.appendChild(offer);
    body.replaceChildren(why);
    // The pane is a paint of the body like any other, so the seam's hooks hear it: whenShown fires only for a
    // picture that decoded, and until this line the panel kept the layer it had built over the PREVIOUS picture
    // when a reload's bytes failed to decode — the overlay stood, armed, over a body with no picture, and the
    // empty state still named the drag — until some later paint happened to run (the 2026-09-06 review; the
    // panel's hook disposes a layer whose picture left: mediaElement() is null now).
    fireRendered();
  };

  // Chooses the body for the current prefs and syncs the buttons. The pressed state flips SYNCHRONOUSLY
  // in the click handler — the immediate acknowledgement ui/CLAUDE.md requires — and so does the content
  // swap, since the text is already in memory.
  const renderBody = () => {
    const rendered = isMd && fmt.md === "rendered";
    for (const [mode, b] of segBtns) {
      const on = fmt.md === mode;
      b.classList.toggle("on", on);
      b.setAttribute("aria-pressed", String(on));
      b.hidden = editing;                       // format choices leave with edit mode; Save/Cancel own the bar
    }
    editBtn.hidden = editing || text === null || !isText || !mtimeNs;
    // the text-size control shows over a text view only, and only once one is KNOWN (textShowing: the bytes and
    // the kernel's Content-Type landed, no editor, no picture or PDF frame; renderBody is every paint, so this
    // follows every flip: the fetch landing, Source on an SVG, the editor taking the body, the exit handing it
    // back). The readout's slot goes with the two buttons; the slot's own emptiness at the default is applyTextSize's
    const sizeHidden = !textShowing();
    sizeDown.hidden = sizeHidden; sizeUp.hidden = sizeHidden;
    sizeReset.hidden = sizeHidden;
    saveBtn.hidden = !editing;
    cancelBtn.hidden = !editing;
    if (isImage || isPdf) {
      // Media mode. The quote gesture gates off the RENDERED views only: a chip's label anchors to
      // text and an <img>/iframe body has none (affordance honesty: no real target, no affordance —
      // the mouseup seed below gates the same way). The SVG SOURCE view is a TEXT view — codeBlock
      // output, real text nodes — so selections there quote like any text view (a blanket media
      // gate would make an .svg's XML unquotable). Edit is already off through the isText arm
      // above; the md segs cannot exist (an .md is never served image/*); Download, Copy path, the
      // GitHub link, ✕ and the dir-link all keep working — none of them needs the text.
      srcBtn.hidden = !(isSvgImage && objUrl !== null);
      srcBtn.classList.toggle("on", svgSource);
      srcBtn.setAttribute("aria-pressed", String(svgSource));
      if (objUrl === null) return;            // the romp loader holds the body until the bytes land
      if (svgSource && svgText !== null) {
        // the Source view is a text view (textShowing), so it keeps the reader's place as the Raw view does: read, swap,
        // hooks, record the XML as the text painted, seat (the Slice 2 review, round 3: a reload under the Source view
        // and the Comments panel's close left the numeric scrollTop over the re-laid rows, 27 rows off)
        const kept = keptPlace();
        body.replaceChildren(codeBlock(svgText, path, true));   // long lines always soft-wrap (the user 2026-08-24)
        fireRendered();                         // a text body: the panel's highlight pass runs on it too
        shownText = svgText;
        seat(kept);
        return;
      }
      shownText = null;                         // a picture or a PDF frame: no text the body was painted from
      if (isPdf && asideOpen) { showPdfPages(); return; }   // the Comments panel is open: the chunk's pages, not the frame (Slice 4)
      if (keepShownFrame()) return;           // the panel closing over a frame at these bytes: the frame stays; the notice, or the attempt under way, goes
      notePdfPage();                          // the reader's page, off the shells, before dropPdf removes them
      dropPdf();                              // the frame (or a picture) replaces any pages a closed panel leaves behind
      const shown = isPdf ? pdfBlock(objUrl, path) : imgBlock(objUrl, path, imgFailed);
      body.replaceChildren(shown);
      whenShown(shown, fireRendered);         // the seam's onRendered for a media body: once the picture shows (Slice 3)
      aimFrame(shown);                        // …and the frame opens on the reader's page, not page 1
      return;
    }
    if (text === null || editing) return;   // loading, or the textarea owns the body right now
    perfTimed("paint", () => {                // the whole pass, the place read to the seat, as one fileview:paint frame of the page's collector (perfTimed)
      if (text === null) return;              // never taken (the guard above returned): TypeScript drops a reassignable variable's narrowing inside a closure
      const kept = keptPlace();               // the reader's place under the view about to go (null: the loader, or the editor, held the body)
      body.replaceChildren(rendered ? mdBlock(text, { kind: "file", path, sid: sid || null }) : codeBlock(text, path, true));   // long lines always soft-wrap (the user 2026-08-24)
      fireRendered();                         // the seam's onRendered: every text paint, so highlights follow the view
      shownText = text;
      seat(kept);                             // then the place, after the hooks as the selection keeper orders it: the same passage at the same height
    });
    if (rendered && pendingFrag) {
      const h = pendingFrag; pendingFrag = null;
      requestAnimationFrame(() => { if (wrap.isConnected) scrollToFragment(body, h); });
    }
  };

  // Selection → labeled quote chip (the user 2026-08-23): mouseup is the gesture's settle point.
  // The chip behaves exactly like a VS Code editor highlight's — one live source-labeled chip,
  // replaced by the next selection, persisting until sent, staged, or ✕'d — because it IS that
  // chip: render.ts's editorSelection handler seeds it. The post carries THIS viewer's sid, so the
  // chip lands in the session the file was opened FOR even if the active tab changed while the
  // modal was up (the 2026-08-19 routing rule: the gesture's session, never activeId-at-gesture).
  let seedSeq = 0;                                 // last gesture wins if two fresh reads race
  const onSelect = (ev: Event) => {
    if (editing) return;   // CodeMirror selections are edit gestures, not quotes
    // A press on a title-bar CONTROL (A−, A+, the readout, Raw, Copy path, the GitHub link...) settles no selection:
    // the mouseup lands on the button while a passage may still stand selected in the body, and running the hooks
    // again re-seeded the quote chip and re-fetched the file for its label on every step of the text size (review
    // 2026-09-07, round 1). The gate is the control under the lift, not the bar: a drag that starts in the body and
    // is released over the bar's path or its padding (the overshoot when selecting back to a file's first line) is a
    // selection like any other and settles (round 2: the round-1 guard read the whole bar and swallowed it, so the
    // passage stood selected with no Comment button and no quote chip). The listener sits on the viewer root so a
    // drag that ends over the aside or the margins settles too.
    const at = ev.target as Element | null;
    if (at && bar.contains(at) && typeof at.closest === "function" && at.closest("button, a")) return;
    // RENDERED media has no honest text to quote — an <img>/iframe body owns its own selection
    // surface; the SVG SOURCE view is a real text view and quotes like any other (renderBody's
    // media gate, same rule).
    if ((isImage || isPdf) && !(svgSource && svgText !== null)) return;
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.anchorNode || !box.contains(sel.anchorNode)) return;
    // The seam's selection hooks run FIRST (plans/file-review.md, Slice 1): the comments panel's
    // floating Comment button must work in a Files pane with no chat pane anywhere — the composer
    // gate below is the QUOTE CHIP's gate, not the selection's.
    for (const cb of selHooks) { try { cb(sel); } catch { /* a hook must never cost the chip */ } }
    // No chip target reachable → no seed (the no-sink gating, re-expressed for the chip era): the post
    // would be dead air and the label's fresh read dead work. The target is this document's composer
    // (the chat-hosted viewer) or, from a pane without one — the Files pane, the feed — the shell,
    // which forwards the seed into the chat pane (composerWindow above).
    const seedTarget = composerWindow();
    if (!seedTarget) return;
    const picked = sel.toString().trim();
    if (!picked) return;
    // The label's line is minted NOW, not at open: agents edit these same trees, so the open-time
    // snapshot's numbering may have quietly moved. Anchor against a fresh read; a FAILED re-read
    // falls back to the snapshot rather than fabricating drift nobody observed (the old Submit
    // guard's rule) — viewText, not text, because the SVG Source view's snapshot is the decoded
    // blob and `text` stays null in media mode. quoteSrcLabel itself degrades to the bare path
    // when the passage cannot be honestly found in whichever bytes it gets.
    const seq = ++seedSeq;
    fetch(fileUrl(path, sid), { cache: "no-store" })
      .then((r) => (r.ok ? r.text() : Promise.reject(new Error(String(r.status)))))
      .catch(() => viewText())
      .then((doc) => {
        if (seq !== seedSeq) return;
        try { seedTarget.postMessage({ type: "editorSelection", text: picked, sid: sid || undefined, src: quoteSrcLabel(path, doc, picked) }, "*"); }
        catch { /* messaging our own window or the same-origin shell cannot really fail */ }
      });
  };
  box.addEventListener("mouseup", onSelect);
  box.addEventListener("touchend", onSelect);   // the phone's selection settles on the lift, with no mouseup

  // Links inside the file (file-view-links.ts): one listener on the body, which every paint keeps and only
  // refills (click-safe, ui/CLAUDE.md). The gesture is the project's (the PDF and folder rule, preview.ts
  // wantsOwnTab): a PLAIN click acts inside the dashboard, and a Cmd/Ctrl-click or a middle-click opens the
  // link in a tab of its own. Plain: a path link opens the file through the host's opener, with this viewer's
  // session (a relative path was already joined onto this file's directory at mark time; the kernel reads `~`
  // and the session's machine); a URL anchor opens itself (target _blank) and is left to the browser (the
  // chat's document-level opener takes it first there, the same way); a section link scrolls to its target
  // in this document, or does nothing where there is none (its title says so), and never moves the hosting
  // document. Modified: a path link opens in the browser's own tab off the kernel's /file route (openFileTab;
  // a blocked popup falls through to the viewer, so the file is never unreachable), a URL anchor in a tab from
  // here. One click does one thing (ui/CLAUDE.md): a click on a mark the comments panel painted over the link
  // (a highlight, a change mark) is the card's opening and only that, so a plain one is cancelled here when
  // the link is an anchor (the anchor's own open would follow the card's otherwise) and left to the panel's
  // delegate on the row, as render.ts yields to panelMark (the 2026-09-06 precedent); a modified click on a
  // mark is the link's and only the link's, so it stops before the row. A PLAIN click is not stopped: it goes on
  // to the document's own listeners (the feed's window listener that returns focus to the chat, the chat's menu
  // closers), which a stop here starved (the 2026-09-07 review). The chat's body delegate routes the same
  // data-act="openpath" for the todo card's links (render.ts), and would have opened the file a second time from
  // a click that reached it (a plain open tears this viewer down first, but an open the close guard DECLINES, an
  // unsaved comment, leaves the span in the document); that delegate now serves only the todo card and its Reply
  // modal, checked at the click, so a viewer link that reaches it opens nothing there (file-view-links-browser.test.ts,
  // the chat page). A click that ends a drag which selected text (the selection is still open at click time; a
  // press on text collapses it first, so a plain click never sees one) selects and navigates nowhere; the chat's
  // capture-phase opener reads the same selection and yields too (path-links.ts selectionOpenIn). Enter on a
  // focused path link is its click (path-links.ts, with a held Cmd/Ctrl carried) and lands here too.
  const openUrlTab = (href: string) => {
    if (!href) return;
    if (canPreview()) window.open(href, "_blank", "noopener,noreferrer");   // the web dashboard: the browser's tab
    else post({ type: "openLink", href });                                  // the VS Code webview: the host's openExternal
  };
  const linkOf = (t: Element | null): HTMLElement | null => {
    const x = t && typeof t.closest === "function" ? t.closest('[data-act="openpath"], a.' + URL_LINK_CLASS + ", a." + FRAG_LINK_CLASS) as HTMLElement | null : null;
    return x && body.contains(x) ? x : null;
  };
  const openLink = (x: HTMLElement, ev: MouseEvent) => {
    const own = wantsOwnTab(ev);
    if (x.classList.contains(FRAG_LINK_CLASS)) {                // a section of this document: this document's scroll, never the page's
      ev.preventDefault();
      // the rendered document's own headings, ids and named anchors, as mark time read them (scrollToFragment, over the
      // .fileview-md box through file-view-links.ts fragmentTarget): the viewer's chrome carries ids of its own (the
      // notice bar), and a lookup over the whole box scrolled to one of those on a colliding name
      scrollToFragment(body, x.getAttribute("href") || "");
      return;
    }
    if (x.dataset.act !== "openpath") {                          // the URL anchor
      if (!own) return;                                          // a plain click: the browser's own open
      ev.preventDefault(); ev.stopPropagation();                 // a modified one: one tab, from here, and the row's delegate never sees it
      openUrlTab(x.getAttribute("href") || "");
      return;
    }
    ev.preventDefault();
    const p = x.dataset.path;
    if (!p) return;
    if (own) {
      ev.stopPropagation();                                      // the row's delegate never sees the modified click (the mark's card would open too)
      if (openFileTab(p, sid || null)) return;                   // its own tab; a blocked popup falls through to the viewer
    }
    const ln = Number(x.dataset.line);
    openLinkedFile(p, sid || null, ln > 0 ? ln : null, x.dataset.frag || null);
  };
  body.addEventListener("click", (ev) => {
    const t = ev.target as Element | null;
    const x = linkOf(t);
    if (!x) return;
    if (panelMark(t) && !wantsOwnTab(ev)) {                      // a plain click on the panel's mark: the card's, and only the card's
      if (x.dataset.act !== "openpath") ev.preventDefault();
      return;
    }
    if (selectionOpenIn(box)) { ev.preventDefault(); return; }   // a drag-select ended on the link
    openLink(x, ev);
  });
  // The middle button: its press would start the browser's autoscroll on a path link (a span, unlike an anchor)
  // and swallow the auxclick, so the press is cancelled there; the auxclick is the link's own tab. A URL anchor's
  // middle-click is the browser's (it opens the href in a new tab itself), so neither listener touches one. A
  // section link's middle-click is this document's scroll, as its plain click is: the browser's own opened a second
  // copy of the hosting page at `/files#id`, and a section of the shown file has no tab of its own (the 2026-09-07
  // review, round 3).
  body.addEventListener("mousedown", (ev) => {
    const x = ev.button === 1 ? linkOf(ev.target as Element | null) : null;
    if (x && x.dataset.act === "openpath") ev.preventDefault();
  });
  body.addEventListener("auxclick", (ev) => {
    if (ev.button !== 1) return;
    const x = linkOf(ev.target as Element | null);
    if (x && (x.dataset.act === "openpath" || x.classList.contains(FRAG_LINK_CLASS))) openLink(x, ev);
  });

  // ── edit mode (the raw-mode slice) ── a plain textarea holding the raw bytes: an embedded editor
  // is a different project, and a textarea that keeps your changes beats a half-editor. The kernel's
  // mtime floor does the real safety work (agents edit these same trees — see _save_file).
  // The ask before something typed and unsaved is dropped: the editor's buffer here, an action's draft through the
  // close guard (the comments panel's typed note, ctx.guardClose). ONE function for both. On the web dashboard it is a
  // confirm dialog. The VS Code webview shows no dialog: window.confirm returns false there without showing anything,
  // so the ask read as a dead click (the 2026-09-07 review; the editor's Cancel and every close met the same wall). There
  // the unsaved thing is kept and the notice bar says what is unsaved and what clears it, which is loud where the
  // dialog was silent (CLAUDE.md, fail loudly): saving or undoing the edit, sending or clearing the note.
  const askDiscard = (question: string, kept: string): boolean => {
    if (canPreview()) return window.confirm(question);
    noteBar(kept);
    return false;
  };
  const confirmDiscard = (): boolean =>
    !editing || !dirty || askDiscard("Discard unsaved changes to " + path.slice(cut + 1) + "?",
      "The editor stays open: " + path.slice(cut + 1) + " has unsaved changes. Save or undo them, then try again.");
  // the editor's ask, then the actions' (ctx.guardClose): each names what it would drop, and the ask is put here
  closeGuard = () => confirmDiscard() && closeAsks.every((ask) => { const q = ask(); return q === null || askDiscard(q.question, q.kept); });
  const norm = (s: string): string => s.replace(/\r\n/g, "\n");   // the textarea's own view of any text
  // The editing substrate is CodeMirror 6 (the user 2026-08-22), living in its OWN lazily-loaded
  // bundle so people who never edit download nothing (the main bundles import none of it — the
  // contract is the window global the chunk registers). The URL derives from the page's own running
  // bundle script — render.js (chat), feed.js (feed) or files.js (the Files pane; 2026-09-03, when a
  // pattern naming only the first two sent every Edit there to the textarea with a raw error) — same
  // directory, same ?v= cache token — so it resolves on the kernel pages and the VS Code webview
  // alike, and a rebuilt kernel always serves a matching chunk. A failed load rejects ONCE and clears
  // the latch so a later attempt retries fresh — and a tag whose `load` fires with NOTHING registered is a
  // failed load too: a script the kernel is rewriting mid-fetch (esbuild writes dist/ in place) parses to
  // nothing and fires `load`, not `error`. Until 2026-09-06 only `onerror` cleared the latch, so one such
  // delivery left the rejection cached for the viewer's life: every later attempt repeated the notice
  // without the fetch that would now succeed. Both loaders clear it in both branches now.
  let edChunk: Promise<{ mount: (host: HTMLElement, opts: object) => NonNullable<typeof cm> }> | null = null;
  const editorChunk = () => edChunk || (edChunk = new Promise((res, rej) => {
    const w = window as any;
    if (w.__rompEditor) return res(w.__rompEditor);
    const self = Array.from(document.querySelectorAll("script[src]"))
      .map((n) => (n as HTMLScriptElement).src).find((u) => /\/(render|feed|files)\.js/.test(u));
    if (!self) return rej(new Error("no bundle script tag to derive the editor chunk URL from"));
    const sc = document.createElement("script");
    sc.src = self.replace(/\/(render|feed|files)\.js/, "/editor-chunk.js");
    sc.onload = () => { const e = (window as any).__rompEditor; if (!e) edChunk = null; e ? res(e) : rej(new Error("editor chunk loaded but did not register")); };
    sc.onerror = () => { edChunk = null; rej(new Error("the editor bundle failed to load")); };
    document.head.appendChild(sc);
  }));
  // The PDF renderer is the same kind of chunk (pdf-chunk.ts; plans/file-review.md Slice 4, decision 12): its own
  // bundle, registered as a window global, loaded by a script tag derived from THIS page's bundle URL exactly as the
  // editor's is — same directory, same ?v= token, so the kernel serves a matching chunk and, through the chunk's own
  // src, a matching worker. The structural type is inline on purpose: even `import type` from the chunk would be an
  // import for the lazy-discipline pin (pdf-lazy.test.ts) to catch. A failed load rejects once and clears the latch — in
  // the load-without-register branch as in onerror (the editor loader's note above says why both), and so does the
  // backstop in showPdfPages giving up on a load that never answered, so the next open fetches afresh.
  let pdfChunk: Promise<{ render: (bytes: ArrayBuffer, container: HTMLElement, opts?: object) =>
    Promise<{ pages: number; dispose(): void }> }> | null = null;
  const pdfChunkLoad = () => pdfChunk || (pdfChunk = new Promise((res, rej) => {
    const w = window as any;
    if (w.__rompPdf) return res(w.__rompPdf);
    const self = Array.from(document.querySelectorAll("script[src]"))
      .map((n) => (n as HTMLScriptElement).src).find((u) => /\/(render|feed|files)\.js/.test(u));
    if (!self) return rej(new Error("no bundle script tag to derive the PDF chunk URL from"));
    // pdf.js 6's default build polyfills nothing, and two of the APIs it relies on are new enough that engines still in
    // use lack them: the `Iterator` global, dereferenced as the chunk's module body runs — on an engine without it the
    // script tag fires `load` with nothing registered, a megabyte fetched for a notice that blames the chunk — and
    // Promise.try, which its message handler calls for every document (Chrome 128, Firefox 134 and Safari 18.4 have
    // both). So the engine is checked HERE, before the fetch, and the notice names the browser, which is the reason.
    // (Rarer gaps pdf.js catches itself: a font rebuild's Math.sumPrecise falls back to a system font.)
    if (typeof (globalThis as any).Iterator !== "function" || typeof (Promise as any).try !== "function") {
      return rej(new Error("this browser is too old for the page renderer"));
    }
    const sc = document.createElement("script");
    sc.src = self.replace(/\/(render|feed|files)\.js/, "/pdf-chunk.js");
    sc.onload = () => { const p = (window as any).__rompPdf; if (!p) pdfChunk = null; p ? res(p) : rej(new Error("PDF chunk loaded but did not register")); };
    sc.onerror = () => { pdfChunk = null; rej(new Error("the PDF renderer failed to load")); };
    document.head.appendChild(sc);
  }));
  // ── the reader's page across the flip (pdfPage above) ── Read when the shells leave: the page under the MIDDLE of
  // the scroller, the one the reader is looking at (a page whose last lines show at the top is not it); a document
  // shorter than the scroller is at page 1. Zero rects (a stand-in with no layout) read as page 1 too.
  const notePdfPage = () => {
    const shells = body.querySelectorAll(".fileview-pdf .fileview-pdf-page");
    if (!shells.length) return;
    const r = body.getBoundingClientRect();
    const mid = r.top + r.height / 2;
    let at = 0;
    for (let i = 0; i < shells.length; i++) { if (shells[i].getBoundingClientRect().bottom >= mid) { at = i; break; } }
    pdfPage = Number((shells[at] as HTMLElement).dataset.page) || at + 1;
  };
  // Written back two ways. The FRAME takes the #page=N open parameter (Firefox's pdf.js viewer does on an object URL,
  // checked; Chromium's documents the same parameters; a viewer that ignores it opens at the top, as before), set as the
  // frame's src after pdfBlock's plain treatment — aimFrame takes the column pdfBlock builds, or the frame itself — a
  // frame not yet in the document just takes it; one already showing navigates again and the bare URL's load is
  // abandoned, the browser's viewer offering no other way to scroll it. Page 1 adds nothing and gets no fragment, so
  // the src is the bare object URL exactly as before. The PAGES scroll their shell into view once the shells exist
  // (they do when render() resolves), and the chunk draws that page as it scrolls in.
  const aimFrame = (shown: Element | null) => {
    const frame = shown && (shown.matches("iframe.fileview-frame") ? shown : shown.querySelector("iframe.fileview-frame"));
    if (!frame || objUrl === null || pdfPage <= 1) return;
    (frame as HTMLIFrameElement).src = objUrl + "#page=" + pdfPage;
  };
  const scrollToPdfPage = () => {
    if (pdfPage > 1) body.querySelector('.fileview-pdf-page[data-page="' + pdfPage + '"]')?.scrollIntoView({ block: "start" });
  };
  // The frame in the body at THESE bytes, when there is one — the open's own, or the one a failed pages attempt left
  // under its notice. A reload's frame shows other bytes (a fresh object URL) and answers null, so it is rebuilt like
  // every other body. Both the frame path below and showPdfPages keep the frame this finds, for the same reason: a
  // rebuilt frame reloads the document, and the place the reader had reached inside it — which the frame never
  // reports — would be lost.
  const shownFrame = (): HTMLIFrameElement | null => {
    if (!isPdf || objUrl === null) return null;
    const f = body.querySelector("iframe.fileview-frame") as HTMLIFrameElement | null;
    return f && f.src.replace(/#.*$/, "") === objUrl ? f : null;
  };
  // The panel closing over a frame at these bytes: the frame stays, the notice a fallback put above it goes, and an
  // attempt still under way over it (the panel closed under the loader) ends here — its loader and host removed, its
  // sequence retired, so a late resolution mounts nothing and a late failure notices nothing. Nothing is rebuilt.
  // True when the frame was kept, and the paint has fired.
  const keepShownFrame = (): boolean => {
    const kept = shownFrame();
    if (!kept) return false;
    dropPdf();
    const col = kept.parentElement!;
    col.querySelector(".fileview-err")?.remove();
    col.querySelector(".fileview-load")?.remove();
    body.querySelector(".fileview-pdfhost")?.remove();
    whenShown(kept, fireRendered);
    return true;
  };
  // The pages body: the romp loader first (the loading-state rule), the chunk's pages once page 1 is drawn, and the
  // seam's onRendered then, after every page the chunk draws, and after every later page it fails to draw (the overlays
  // attach per page, and leave with a failed page's canvas on that repaint). Every refusal is LOUD
  // and the same shape: the browser's frame, with a one-line notice above it saying why and that a comment on the
  // whole file still works — bytes over the cap (refused HERE, before a megabyte of renderer is fetched for nothing),
  // an engine too old for the renderer (also before the fetch), a chunk or worker that will not load, a document
  // pdf.js will not open, a document it opens with no pages in it, an attempt still unsettled at the backstop
  // (PDF_RENDER_BACKSTOP_MS — a hung worker, a chunk fetch that stalls). Never a blank pane, never a silent frame.
  // A frame already in the body at these bytes (shownFrame) is the frame those refusals show, IN PLACE: it stays
  // through the attempt, under the loader at the top of its column, and takes the notice above it when the attempt
  // fails; only the pages actually mounting remove it. Before this, every open of the panel over such a PDF (one over
  // the cap, one pdf.js refuses, an engine or a network the chunk will not load on) built a fresh frame, which
  // reloaded the document at page 1 — the place the reader had reached in the browser's viewer lost on every
  // Comments click (the review, 2026-09-06). An iframe re-inserted anywhere reloads the same way, so nothing here
  // moves the kept frame: the notice and the loader come and go around it inside pdfBlock's column, and the chunk's
  // host is laid out after the column rather than inside it.
  const showPdfPages = () => {
    notePdfPage();                             // a reload with the panel open: the pages come back where they were
    dropPdf();
    const blob = mediaBlob; const url = objUrl;
    if (!blob || url === null) return;
    const my = pdfSeq;
    const kept = shownFrame();
    const col = kept ? kept.parentElement : null;
    const fallback = (why: string) => {
      if (my !== pdfSeq || !wrap.isConnected) return;   // the body moved on: whatever shows now is not this render's
      disarmBackstop();                        // the attempt is over, whichever way it failed…
      abortPdfAttempt();                       // …and so is its signal: spent on a rejection, the Worker's end on a hang (the backstop)
      const note = el("div", "fileview-err");
      note.textContent = why + " — showing the browser's PDF viewer instead; comments on the whole file still work.";
      if (col) {                               // the kept frame: the attempt's loader and host go, the notice goes above it
        col.querySelector(".fileview-load")?.remove();
        body.querySelector(".fileview-pdfhost")?.remove();
        col.prepend(note);
        whenShown(col, fireRendered);
        return;
      }
      const fall = pdfBlock(url, path);        // no frame to keep (the pages were up, or the bytes just landed): a fresh one
      fall.prepend(note);
      aimFrame(fall);                          // the reader's page, here too, set before the frame is in the document
      body.replaceChildren(fall);
      whenShown(fall, fireRendered);
    };
    if (blob.size > PDF_MAX_BYTES) { fallback(pdfCapMessage(blob.size, PDF_MAX_BYTES)); return; }
    const wait = el("div", "fileview-load");
    wait.innerHTML = '<img src="/media/romp-swirl-glyph.svg" alt=""><span>romp</span>'
      + '<i class="fileview-dot"></i><i class="fileview-dot"></i><i class="fileview-dot"></i>';
    const host = el("div", "fileview-pdfhost");
    // the host is laid out before render(): the chunk fits pages to its width. Over a kept frame the loader heads the
    // frame's column and the host follows the column, so the frame itself is never moved.
    if (col) { col.prepend(wait); body.appendChild(host); }
    else body.replaceChildren(wait, host);
    // The backstop (ui/CLAUDE.md, loading states; the constant's comment sizes it). Every other end of this attempt is an
    // event — the resolve, a rejection, the panel or the viewer closing — but a render that never settles fires none: a
    // worker stuck in a pathological content stream, or a chunk fetch that stalls without erroring, leaves the promise
    // pending for good, and with no frame kept (the panel opened before the bytes landed; the pages were up and the file
    // reloaded) the loader would be the whole body, nothing saying why, nothing on screen pointing at a way out. So the
    // deadline gives up in the fallback's own shape: the frame with the notice; the attempt retired (dropPdf), so a resolution
    // landing later is disposed and mounts nothing, as after a closed panel; its signal aborted (fallback, dropPdf), so
    // the chunk destroys the loading task and terminates the Worker a hung open or draw held — the one thing here that
    // reaches it, since a render that never settles never yields a handle; and the chunk's latch cleared, so the next
    // open fetches a stalled chunk afresh (a loaded one is found again through its window global, with no fetch).
    pdfBackstop = setTimeout(() => {
      pdfBackstop = undefined;
      if (my !== pdfSeq || !wrap.isConnected) return;   // dropPdf disarms before either can hold; the guard is the others' shape
      pdfChunk = null;
      fallback("the page renderer did not finish within " + PDF_RENDER_BACKSTOP_MS / 1000 + " seconds");
      dropPdf();
    }, PDF_RENDER_BACKSTOP_MS);
    // this attempt's cancel (pdfAttempt above): aborted by dropPdf wherever the attempt is retired unsettled, so the chunk
    // destroys the loading task and its Worker — the one way to reach an open or a first-page draw that never settles
    const attempt = new AbortController();
    pdfAttempt = attempt;
    Promise.all([pdfChunkLoad(), blob.arrayBuffer()]).then(([pdf, bytes]) => {
      if (my !== pdfSeq || !wrap.isConnected) return;
      return pdf.render(bytes, host, {
        maxBytes: PDF_MAX_BYTES,
        signal: attempt.signal,
        // every draw after the first resolve (a page scrolling in, a redraw at a new width) is a repaint the panel hears
        onPage: () => { if (my === pdfSeq && pdfHandle) fireRendered(); },
        // …and so is a later page pdf.js refuses (the chunk removes its canvas and shows the failure in its shell): the
        // panel's overlay on that canvas, armed by the resolve's paint, leaves only on a repaint, and the card's
        // 'not rendered' tag comes with the same pass. Without this the failed shell kept an armed overlay above its
        // notice — undraggable, unselectable — until some other page drew or the window resized (the round-3 review).
        onPageError: () => { if (my === pdfSeq && pdfHandle) fireRendered(); },
      }).then((h) => {
        if (my !== pdfSeq || !wrap.isConnected) { h.dispose(); return; }   // a stale resolution mounts nothing
        disarmBackstop();                      // settled in time
        pdfAttempt = null;                     // …so the handle owns the release from here; the signal is spent
        // pdf.js opens a page-less document (an empty page tree) and resolves with nothing drawn: an empty root would be
        // the blank pane this function exists to prevent, so the frame with the notice, and the document released
        if (h.pages === 0) { h.dispose(); fallback("this PDF has no pages"); return; }
        pdfHandle = h;
        wait.remove();                         // page 1 is drawn: the loader is removed…
        col?.remove();                         // …and the frame kept through the load goes with its column: the pages are the body
        scrollToPdfPage();                     // …at the reader's page, when the pages had shown one before
        fireRendered();
      });
    }).catch((err) => fallback(String(err && (err as Error).message || err)));
  };
  closeHooks.push(dropPdf);                    // both exits (close, replace-open) release the document and its worker
  const enterFallback = () => {                 // the plain textarea: LOUD fallback, never a silent one
    ta = el("textarea", "fileview-editor") as HTMLTextAreaElement;
    ta.value = text!;                           // the browser normalizes CRLF→LF on assignment…
    ta.spellcheck = false;
    // long lines soft-wrap here as they do in the read view and the CodeMirror editor (the user
    // 2026-09-04; the view has always wrapped since 2026-08-24). SOFT: the wrap is visual only — the
    // value keeps its own newlines and nothing marks the buffer dirty (wrap=hard would insert them).
    // The sheet's white-space: pre-wrap on .fileview-editor does the wrapping; pre would defeat it.
    ta.wrap = "soft";
    ta.addEventListener("input", () => { dirty = ta!.value !== norm(text!); });   // …so compare normalized
    ta.addEventListener("keydown", (e) => {     // the editor's own save chord; Esc falls through to onKey
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); doSave(); }
    });
    body.replaceChildren(ta);
    ta.focus();
  };
  let editSeq = 0;                              // stale chunk resolutions (edit left before load) no-op
  const enterEdit = () => {
    if (text === null || editing) return;
    // The pending changes ride in as the mount's `track` option (Slice 5; decision 14): the panel's records and colour
    // map, and a decisions callback so an in-editor accept — which changes no text — still marks the buffer dirty. Asked
    // of the panel HERE, after the consent round-trip, not carried over from the click: the panel's status is the truth
    // about what is pending, and the panel fences the save on the sidecar as it stands at this call. So the click's
    // guards run over THIS result too (trackedRefusal): what they let through at the click may have become records since.
    // Refused before edit mode is entered — the read view stays, and the words go where the click's would have.
    const pending = trackedEdit ? trackedEdit.begin() : null;
    const refused = trackedRefusal(pending);
    if (refused) { noteBar(refused); return; }
    // markdown edits from its Raw view (what you edit is what raw shows): switched here, past the guard, so a refused
    // Edit leaves the Rendered view it was clicked from standing under the refusal, not a Raw choice saved and unpainted
    if (isMd && fmt.md === "rendered") { fmt.md = "raw"; saveFmt(fmt); }
    editing = true; dirty = false;
    eolCRLF = /\r\n/.test(text);
    renderBody();
    // The panel's edit-mode render. Its cards read editing() at render time (the caption that says to decide in the
    // editor, Accept and Reject dimmed with those words, no Reveal or link into a read view that is gone: setMode and
    // scrollToOffset are no-ops now), and nothing above rendered them with the flag set: begin() ran before it, as it must
    // (a refused begin() leaves the read view untouched), and renderBody paints nothing in edit mode. So the seam's
    // onRendered fires here, once, as the editor takes the body: the panel's paint pass stands down on editing() and its
    // cards take their edit-mode state. Without it a panel open at Edit kept its read-mode cards, live-looking controls
    // that did nothing, until some status happened to land (the review's cards-keep-read-mode finding). The exit's
    // repaint hands the read-mode state back.
    fireRendered();
    // a notice over the read view (a refusal since lifted, a line past the end) goes as the editor takes the body: the
    // swap below took it while the bar sat inside the body, and the bar now sits above the row (noteBar)
    document.getElementById("fileview-save-err")?.remove();
    // per the loading-state rule the chunk wait shows the romp loader, not a blank body
    const wait = el("div", "fileview-load");
    wait.innerHTML = '<img src="/media/romp-swirl-glyph.svg" alt=""><span>romp</span>'
      + '<i class="fileview-dot"></i><i class="fileview-dot"></i><i class="fileview-dot"></i>';
    body.replaceChildren(wait);
    const my = ++editSeq;
    editorChunk().then((ed) => {
      if (!editing || my !== editSeq) return;   // edit mode left (or re-entered) while the chunk loaded
      const host = el("div", "fileview-cm");
      body.replaceChildren(host);
      cm = ed.mount(host, {
        text: norm(text!), ext: path.slice(path.lastIndexOf(".") + 1),
        onChange: () => { dirty = cm!.value() !== norm(text!); if (!dirty) dirty = decided(); },
        onSave: () => doSave(),
        ...(pending ? { track: { suggestions: pending.records, authorColor: pending.authorColor, onDecisions: () => { dirty = cm!.value() !== norm(text!) || decided(); } } } : {}),
      });
      if (pending && !cm.track) {
        // an older editor bundle ignored the option: the buffer shows the text with no marks, and a save from it would
        // move every pending change. Refuse in the panel's words (the Slice 2 wording) and remember, so the next Edit
        // refuses at the click.
        chunkTracks = false;
        exitEdit();
        noteBar(pending.refusal);
        return;
      }
      if (pending) chunkTracks = true;
      cm.focus();
    }).catch((err) => {
      if (!editing || my !== editSeq) return;
      const why = String(err && (err as Error).message || err);
      if (pending) {
        // the plain fallback editor cannot carry the changes either: no edit mode, and the refusal says both things
        exitEdit();
        noteBar(why + " — " + pending.refusal);
        return;
      }
      enterFallback();
      noteBar(why + " — editing in the plain fallback editor.");   // loud: say the editor is degraded, never pretend
    });
  };
  const exitEdit = () => {
    editing = false; dirty = false; ta = null;
    cm?.destroy(); cm = null;
    applied = { accepted: [], rejected: [] };   // the decisions went with the editor; the next mount starts its own afresh
    editHooks = null;                           // a cancelled save's late ack must not touch a NEW session
    saveBtn.disabled = false; saveBtn.textContent = "Save";
    // the edit's notices (a refused save's, a declined close's, a fallback editor's) go with the editor: the repaint took
    // them while the bar sat inside the body, and a notice that must outlive the exit is raised again after it (noteLog)
    document.getElementById("fileview-save-err")?.remove();
    renderBody();
    // a fetch that landed while the editor was up painted nothing (fetchFile): now that the edit is over, read the file
    // as it is — the exit is the event the dropped bytes were waiting for
    if (refetchAfterEdit) { refetchAfterEdit = false; fetchFile(); }
  };
  const doSave = () => {
    const buf = bufValue();
    if (!editing || buf === null || saveBtn.disabled) return;
    if (!dirty) { exitEdit(); return; }         // nothing changed — leaving is the honest ack
    // A record back in the field that a landed save already decided (undoneLanded): the host cannot take that decision
    // back, so this Save sends nothing and says so, in place, with the buffer and the button as they were.
    const undone = undoneLanded();
    if (anyUndoneLanded(undone)) { noteBar(undoneLandedNote(undone, false)); return; }
    saveBtn.disabled = true; saveBtn.textContent = "Saving…";   // acknowledge before the round-trip
    // restore the file's own line endings — an untouched CRLF file must round-trip byte-identical
    const content = eolCRLF ? buf.replace(/\n/g, "\r\n") : buf;
    // the decisions this save carries (the tracked path below fills it): marked applied when the save lands, so a later
    // Save from the same editor sends only what came after
    let sent: EditDecisions | null = null;
    // Loud, in place, and the BUFFER SURVIVES: the error bar sits above the textarea. A conflict
    // (the disk moved — an agent wrote it) offers Reload, which re-opens fresh — behind the same
    // discard confirm, so the user's edits are never thrown away silently (never a merge UI).
    // `moved`: the comments host's store-moved / file-moved / config-moved refusals (Slice 5) offer the same Reload the
    // kernel's own conflict wording does; a desync or any other refusal shows its reason and keeps the buffer, no offer.
    const showSaveError = (err: string, moved = false) => {
      const bar2 = noteBar(err);
      if (/changed on disk/.test(err)) { moved = true; }   // saveFile's conflict, in the kernel's words
      if (moved) {
        const re = el("button", "fileview-btn fileview-err-dl") as HTMLButtonElement;
        re.type = "button"; re.textContent = "Reload file";
        re.title = "Fetch the file as it is now (asks before discarding your edits)";
        re.addEventListener("click", () => {
          if (!confirmDiscard()) return;
          dirty = false;                      // confirmed once — the replace guard must not ask twice
          openFileView(path, sid, opts);      // the same provenance (todoId) — a reload is still that open
        });
        bar2.appendChild(re);
      }
    };
    const hooks: NonNullable<typeof editHooks> = {
      reqId: ++saveSeq,
      // The kernel's account of a comments-log append that failed, or of a log it could not read back
      // after appending — filled from the fileSaved reply before `saved` runs (plans/file-review.md, The
      // comments log: a failed append is reported in the reply, never a failed save). The save landed,
      // so it is no error state — but the Log the panel shows then lacks (or cannot read back) the entry
      // this edit owed, and a person reading it later would take the silence for "nothing happened".
      logWarning: null,
      saved: (mtNs, logged) => {
        mtimeNs = mtNs;
        text = content;
        refetchAfterEdit = false;               // the reply is the file as it stands: a fetch dropped under this edit is moot
        if (sent) mergeApplied(sent);           // the host applied and logged these: no later Save from this editor re-sends them
        // the seam's onSaved: the panel refreshes its Log (the kernel appended the edit before replying)
        for (const cb of savedHooks) { try { cb({ mtimeNs: mtNs, logged }); } catch { /* a hook must never cost the save */ } }
        // The comments-log warning goes up in the note bar, in the kernel's own words (CLAUDE.md:
        // surface it, never degrade silently) — here, above the editor the in-flight stay below keeps,
        // and again after exitEdit's repaint on the other path, which takes this bar with the editor.
        const noteLog = () => { if (hooks.logWarning) noteBar(hooks.logWarning); };
        noteLog();
        // A decision UNDONE during the round-trip that this save carried: the record is back in the field, and the
        // disk holds the decision (undoneLanded). The ack is the moment the undo became irreversible: stay, and say
        // so above the editor (the person redoes it, decides it again, or cancels). Checked FIRST, whatever else the
        // buffer holds. An accept moves no text and leaves nothing beyond `applied`, so the text check below would
        // exit and drop the undo without a word; and when the buffer HAS moved (the save carried typing the undo took
        // back too, or the undone decision was a reject, which moves text), that check stays silently, and the person
        // would hear of the landed decision only at the next Save's refusal (the review's undone-during-round-trip
        // finding, both cases). decided() answers true for this too but says nothing. The bar carries the comments-log
        // warning as well when there is one: noteBar paints one bar, and the note must not take the warning down with
        // it (CLAUDE.md: surface it, never degrade silently).
        const undoneAtAck = undoneLanded();
        if (anyUndoneLanded(undoneAtAck)) {
          dirty = true; saveBtn.disabled = false; saveBtn.textContent = "Save";
          noteBar(undoneLandedNote(undoneAtAck, true) + (hooks.logWarning ? " Also: " + hooks.logWarning : ""));
          return;
        }
        // Keystrokes typed DURING the round-trip survive the ack (the review's in-flight-typing
        // finding): if the live buffer moved past the snapshot we saved, stay in edit mode with the
        // new baseline — never re-render over what the user is still typing.
        if (bufValue() !== null && bufValue() !== norm(content)) {
          dirty = true;
          saveBtn.disabled = false; saveBtn.textContent = "Save";
          return;
        }
        // A decision clicked during the round-trip is the same stay with no text moved (an accept changes
        // none): it is in the decisions beyond what this save carried, and leaving would destroy it with the editor.
        if (decided()) { dirty = true; saveBtn.disabled = false; saveBtn.textContent = "Save"; return; }
        exitEdit();                             // re-renders the highlighted view from the saved bytes
        noteLog();
      },
      failed: (err, code) => {
        saveBtn.disabled = false; saveBtn.textContent = "Save";
        // A GATE refusal from the kernel that OWNS this file: re-offer the SAME consent naming the
        // disagreeing machine (ensureEditingAllowed's re-consent path, shared with the comment verbs);
        // a yes re-broadcasts setFileEditing and retries the save — the broadcast and the save ride the
        // same ordered socket per host, so the flag lands first; on a host whose socket is down at that
        // moment, federation queues the setting and flushes it on the open event ahead of any later
        // traffic (federation.ts sendRemote/flushPending), so the flag still lands before a
        // post-reconnect retry. A no falls through to the plain error bar, buffer intact.
        if (/file editing is off/.test(err)) {
          void ensureEditingAllowed(sid, err).then((ok) => { if (ok) doSave(); else showSaveError(err); });
          return;
        }
        showSaveError(err, code === "store-moved" || code === "file-moved" || code === "config-moved");
      },
    };
    editHooks = hooks;
    if (trackedEdit && trackedEdit.routesSave()) {
      // A tracked file, or one with a sidecar (Slice 5): the save goes through the comments host, which writes the file
      // and the remapped sidecar together — the records as the editor holds them now and the decisions taken in it that
      // no earlier save from this editor carried (unsent; an editor that carried no changes sends none). The panel's
      // promise stands in for the fileSaved reply: the same hooks, guarded the same way (a Cancel nulls editHooks, so a
      // late answer touches nothing).
      const records = cm && cm.track ? cm.track.suggestions() : [];
      const decisions = unsent();
      sent = decisions;
      trackedEdit.save(content, records, decisions).then(
        (r) => {
          if (editHooks !== hooks) {
            // The edit ended while the host was writing (Cancel, Escape — confirmed, since the buffer was dirty), so
            // the ack finds no editor to tell: `saved` must not run over whatever is up now. But the write landed all
            // the same, and the panel applied the reply as its status before resolving — its poll's baseline is the
            // saved file already, so no later tick would notice that the view still shows the bytes from before (the
            // poll healed saveFile's dropped ack this way; a reply that re-bases the baseline takes that away — the
            // review's cancel-during-save finding). The late ack is the event: tell the panel's onSaved (it clears its
            // own bookkeeping for this reply) and read the file as it is now — at once if the view is showing it, at
            // the exit if a new editor already holds the truth (the fetch-under-edit rule). Nothing if the viewer is
            // gone: the next open reads the disk.
            if (!wrap.isConnected) return;
            for (const cb of savedHooks) { try { cb({ mtimeNs: r.mtimeNs, logged: r.logged }); } catch { /* a hook must never cost the heal */ } }
            if (!editing) { fetchFile(); return; }
            refetchAfterEdit = true;
            // A NEW editor is up: Edit after the Cancel mounted it over the bytes and mtime from BEFORE this save, with the
            // records of that time as its marks, and it holds whatever has been typed since. This ack is the one event that
            // says the disk moved under it: the panel applied the reply as its status before resolving, so its poll's
            // baseline is the saved file already and no later tick raises its moved-under-edit row, and keeping the buffer
            // (above) is right but silent. Said here, above the editor, with the Reload offer the next Save's file-moved
            // refusal would carry: that refusal is correct (mtimeNs is the file this editor loaded, so a Save from it refuses
            // rather than overwrite the person's own landed save), but the person heard of the move only then, from words
            // about a file some agent changed. The buffer stays; Cancel re-reads at the exit (refetchAfterEdit). Nothing is
            // said when the ack's file is the one this editor loaded (the review's cancelled-save-ack finding).
            if (r.mtimeNs && r.mtimeNs !== mtimeNs) showSaveError(SAVE_LANDED_UNDER_NEW_EDITOR, true);
            return;
          }
          editHooks = null;
          // The host's account of a comments-log append that failed on a save that landed, read off the resolved value
          // before the ack runs, as the fileSaved branch reads the kernel's (the same field, the same note bar). The panel
          // says it in its head too, but that is painted only while the aside is open, and a tracked file is edited with
          // the aside closed by default — so without this the Log the person opens later lacked the edit's entry and
          // nothing had said so (the review's dropped-warning finding; CLAUDE.md, never degrade silently). Read off the
          // value as the fileSaved branch reads its reply: the seam's type does not name the field (see TrackedEdit.save).
          const w = (r as { logWarning?: unknown }).logWarning;
          hooks.logWarning = typeof w === "string" && w ? w : null;
          hooks.saved(r.mtimeNs, r.logged);
        },
        (e: { code?: unknown; error?: unknown }) => {
          if (editHooks !== hooks) return; editHooks = null;
          hooks.failed(String(e && e.error || "the save failed"), typeof (e && e.code) === "string" ? String(e.code) : undefined);
        });
      return;
    }
    post({ type: "saveFile", path, sid: sid || undefined, content, baseMtimeNs: mtimeNs, reqId: saveSeq });
  };
  renderBody();   // buttons take their initial state now; the loader stays up until the fetch lands

  const onKey = (e: KeyboardEvent) => {
    if (e.key !== "Escape" || !document.getElementById("romp-fileview")) return;
    e.preventDefault();
    if (editing) {                              // Escape peels edit mode first, never the whole viewer
      if (confirmDiscard()) exitEdit();
      return;
    }
    closeFileView();                            // a real close unregisters this handler (dropOnKey);
    //                                             a vetoed one keeps it — the viewer is still up
  };
  document.addEventListener("keydown", onKey);
  onKeyLive = onKey;

  // The fetch pipeline, as a function: the open runs it once, and the seam's reload() runs it again
  // (the comments panel's poll saw the file's mtime move — an agent wrote it) with the action row
  // and the aside left standing; only the body and the mtime change.
  //
  // What lands is applied in ONE step, headers and bytes together, under two guards — and a fetch that
  // fails either guard changes nothing, not even the mtime:
  // - the newest fetch wins (fetchSeq, the quote seed's own idiom): two reloads in flight answer in
  //   any order, and an older response landing last would otherwise put ITS bytes in the body under
  //   the newer response's mtime — a view that claims the new text and shows the old, which the
  //   comments panel would then paint its marks over (it trusts mtimeNs() to say which text it sees).
  //   An overtaken response changes nothing: not the body, not the mtime, not the Edit verdicts, and
  //   no error row for a failure nobody awaits; one overtaken before its bytes were read reads none;
  // - the editor holds the truth while it is up (editing): its buffer is the text, and `mtimeNs` is the
  //   file the editor LOADED — the save fence's own value (plans/file-review.md Slice 5). The seam's
  //   reload() already stands down in edit mode, but a fetch started BEFORE Edit (the poll saw the file
  //   move, then the person clicked Edit) used to land inside it: `mtimeNs` moved to the newer file while
  //   the buffer came from the older bytes, so both save doors passed their fence and overwrote a
  //   session's write silently — the case the fence exists to refuse (the review's fetch-race finding).
  //   Reading the headers into the state before the bytes had landed opened the same window between the
  //   two continuations, which is why they are applied together. The dropped bytes are read again when
  //   the edit ends (exitEdit, refetchAfterEdit): the exit is the event, not a timer.
  let fetchSeq = 0;
  let refetchAfterEdit = false;
  // The row for a 1-based line of the code view, scrolled to the middle (scrollToOffset's own gesture); `pendingLine`
  // is the open's `line`, spent on the first text that lands. A reload keeps the reader's place and does not scroll.
  // A line past the end (a stale `x.py:400` in a file that shrank) lands on the last row AND says so in the viewer's
  // notice dress: a silent landing on the wrong row reads as the file's truth (CLAUDE.md, fail loudly).
  const scrollToLine = (n: number) => {
    const rows = body.querySelectorAll("code.hljs .fv-cl");
    if (!rows.length) return;
    if (n > rows.length) noteBar("Line " + n + " is past the end of this file, which has " + rows.length + (rows.length === 1 ? " line" : " lines") + "; showing the last line.");
    (rows[Math.min(Math.max(0, n - 1), rows.length - 1)] as HTMLElement).scrollIntoView({ block: "center" });
  };
  let pendingLine: number | null = opts && typeof opts.line === "number" && opts.line > 0 ? Math.floor(opts.line) : null;
  // The landing runs through the hold's defer, whose promise settles with the run (actions.ts pressHold): a run the hold
  // parks goes on a zero timer at the release, outside the fetch's chain, and a throw from it (renderBody's DOM passes,
  // after the landing has taken the new mtime) reached nobody in round 1: an uncaught page error, the old text standing
  // under the new mtime with no error row, while the same throw from an immediate landing reached the `.catch` below.
  // The promise rejects with the parked run's throw into that same `.catch` now (review round 2, 2026-09-08;
  // file-view-landing-throw-browser.test.ts); a parked run a later landing replaced resolves with nothing painted, which
  // is what the hold's header says of an overtaken landing.
  const fetchFile = () => {
    const my = ++fetchSeq;
    type Verdict = { isText: boolean; mtimeNs: string; isImage: boolean; isPdf: boolean; isSvgImage: boolean };
    // this fetch's verdicts off the headers, held here until its bytes land and applied with them below
    let v: Verdict | null = null;
    // Whether this fetch's answer STANDS to land: its viewer is up (wrap.isConnected: a close removes the wrap, and a
    // replace-open detaches it while the id the guards used to open with sits on the NEW viewer, so that check passed for
    // the wrong viewer) and no newer fetch is out (fetchSeq). `land` runs a landing through the hold's defer for an answer
    // that stands and drops one that does not, BEFORE the hold as well as inside the parked run: the hold parks in DEFER
    // order and a later defer replaces the parked run, so an overtaken answer that reached defer under a press displaced
    // the newer fetch's parked landing (resolved, unpainted) and then bailed itself at the release on fetchSeq: two writes
    // within a poll interval, the newer answer first, and the body kept the old text under the old mtime with nothing
    // re-asking (the Comments panel asks once per mtime). And a landing parked under a press whose viewer a replace-open
    // removed during the press painted into the detached body and fired the replaced viewer's hooks (the Slice 3 review,
    // round 3, 2026-09-09; file-view-landing-order-browser.test.ts). An answer that does not stand paints nothing, parks
    // nothing and displaces nothing; the guards re-run inside the parked run for what changes while it is parked.
    const stands = (): boolean => wrap.isConnected && my === fetchSeq;
    const land = (run: () => void): Promise<void> | void => { if (stands()) return hold.defer(run); };
    fetch(fileUrl(path, sid), { cache: "no-store" }).then((r): Promise<string | Blob> => {
      if (my !== fetchSeq) return Promise.resolve("");   // a newer fetch is out: read nothing, set nothing
      // Every failure says WHY, in the pane, rather than leaving a blank one: the kernel distinguishes
      // "not a type I serve" from "too big" from "not text after all", and that is exactly what the
      // person who clicked needs to know (a 413 names the size and the cap). The status rides along so
      // the catch below can tell "the file is there but I can't show it" from "there is no file".
      if (!r.ok) return r.text().then((t) => {
        throw Object.assign(new Error(t || ("HTTP " + r.status)), { status: r.status });
      });
      // Edit arms off the KERNEL's verdicts, never a client guess: text/plain AND a faithful UTF-8
      // round-trip (the latin-1 fallback re-decodes non-UTF-8 files — saving that back would rewrite
      // every non-ASCII byte, the review's executed repro), anchored by the ns mtime header (an old
      // kernel that sends neither simply gets no Edit button).
      v = { isText: false, mtimeNs: "", isImage: false, isPdf: false, isSvgImage: false };
      v.isText = (r.headers.get("Content-Type") || "").startsWith("text/plain")
        && r.headers.get("X-Romp-Text-Utf8") !== "0";
      v.mtimeNs = r.headers.get("X-Romp-Mtime-Ns") || "";
      // Media branches on the SAME kernel verdict (an image 200 wears image/* and no X-Romp-Text-Utf8 —
      // tests/test_kernel_preview.py pins that contract server-side). The bytes below are the one fetch
      // either way: media takes them as a blob for an object URL, never a second request.
      const ct = r.headers.get("Content-Type") || "";
      v.isImage = ct.startsWith("image/");
      v.isPdf = ct.startsWith("application/pdf");
      v.isSvgImage = ct === "image/svg+xml";
      // THIS fetch's flags choose the body's shape; the viewer's own isImage/isPdf still say what shows now
      const { isImage, isPdf } = v;
      return isImage || isPdf ? r.blob() : r.text();
    }).then((t) => land(() => {   // parked while a pointer is pressed over the body; the guards re-run at the release
      if (!stands()) return;                                    // closed, replaced or overtaken while it was parked
      if (editing) { refetchAfterEdit = true; return; }         // the editor holds the truth; read again when it ends
      const got = v!;                                           // set with the headers above; a failure never reaches here
      isText = got.isText; mtimeNs = got.mtimeNs; isImage = got.isImage; isPdf = got.isPdf; isSvgImage = got.isSvgImage;
      if (t instanceof Blob) {
        // Minted only now, after the guards above (stands: the wrap connected, this fetch the newest): a viewer closed or
        // REPLACED mid-flight creates nothing to leak, and never clobbers the new open's mediaUrlLive registration.
        if (objUrl !== null) dropMediaUrl();    // a reload: the previous bytes' URL goes before the new one is minted
        mediaBlob = t;
        objUrl = URL.createObjectURL(t);
        mediaUrlLive = objUrl;                   // registered so close/replace can revoke (dropMediaUrl)
        if (svgSource && svgText !== null) {
          // A reload under the Source view: the XML swaps in when the new bytes decode, and the old
          // text stands until then — nulling it first would flap mode() to "media" and flash the image
          // for the decode's duration. A decode a newer reload overtook, or one landing after the
          // viewer closed, paints nothing: the newest bytes are what show, and a drained panel hears
          // no onRendered.
          void t.text().then((s) => { if (mediaBlob !== t || !wrap.isConnected) return; svgText = s; renderBody(); });
          return;
        }
        svgText = null;   // any decode on hand was the OLD bytes': the next Source toggle decodes this blob
        renderBody();
        return;
      }
      text = t;
      // a line the link named: the Raw view for this open (unsaved: the preference stays), then the row
      if (pendingLine !== null && isMd && fmt.md === "rendered") fmt.md = "raw";
      renderBody();
      if (pendingLine !== null) { scrollToLine(pendingLine); pendingLine = null; }
    })).catch((err) => land(() => {
      if (!stands()) return;                                    // the same guards as a landing: an older failure, or a gone viewer's, paints over nothing…
      if (editing) { refetchAfterEdit = true; return; }         // …and never over the editor's host (the exit re-reads and says why then)
      const why = el("div", "fileview-err");
      const msg = String(err && err.message || err);
      why.textContent = msg;
      if (!msg.includes(path)) {
        // The kernel's 404/413/415 bodies name the RESOLVED path themselves now — the hint exists for
        // errors that don't (a network failure, an old kernel), not to say the same path twice.
        const hint = el("div", "fileview-err-hint");
        hint.textContent = path;
        why.appendChild(hint);
      }
      // A refusal-to-RENDER is not a dead end (ui/CLAUDE.md): when the file exists, the kernel's own
      // words are followed by the way out — the download the view could not be. A 404 stays offerless,
      // because offering to download a file that is not there would be a lie.
      if (offersDownload((err as { status?: number }).status)) {
        const offer = el("button", "fileview-btn fileview-err-dl") as HTMLButtonElement;
        offer.type = "button"; offer.textContent = "Download";
        offer.title = "Save this file to your device";
        offer.addEventListener("click", () => startDownload(dlUrl, offer));
        why.appendChild(offer);
      }
      body.replaceChildren(why);
    }));
  };
  fetchFile();
  return true;
}

// Which fetch failures still deserve a Download offer? Exactly the ones that mean the file EXISTS:
// 413 (too large to render) and 415 (on disk but not viewable — a .zip, a binary named like text).
// A 404 is genuinely missing, and gets nothing.
function offersDownload(status: number | undefined): boolean {
  return status === 413 || status === 415;
}

// ── URL mode (the user 2026-09-06) ─────────────────────────────────────────────────────────────────
// A chat message linking a markdown file on the dashboard's OWN origin (`https://<this host>/figs/
// run-1/evidence.md` — a published report, an evidence doc) used to open the raw text in a new tab.
// It presents here instead: same modal, same Rendered ⇄ Raw preference (FMT_KEY), same loader-first
// wait, same mdBlock — fetched by the BROWSER from the URL itself, with no kernel in the loop. Zero new
// kernel surface is the point: the kernel's /file relay is a preview relay and has stayed one on
// purpose (_remote_file's docstring), and a same-origin URL needs no relay — the browser already has
// the cookie. Cross-origin .md links are never routed here (render.ts checks isMarkdownUrl first).
//
// The shell is built here rather than threaded through openFileView because almost everything in that
// row is keyed on the KERNEL's reply — Edit on the text/plain + mtime verdicts, Download on the
// ?download=1 route, the GitHub link on a fileGitLink ask, ‹ Files on the browser overlay — and none
// of it exists for a URL. What both modes share is shared by construction: el/loaderEl, the format
// pref, mdBlock/codeBlock, closeFileView and the module-level teardown registrations.
export function openUrlView(href: string): void {
  // The same replace path as openFileView: an editor holding unsaved changes is asked first, and
  // every module-level registration the old viewer made is dropped before it is torn down.
  if (document.getElementById("romp-fileview") && closeGuard && !closeGuard()) return;
  closeGuard = null;
  editHooks = null;
  gitHooks = null;
  dropOnKey();                                         // …and the old viewer's Escape handler (one live handler at a time)
  runCloseHooks();                                     // …and the old viewer's panel hooks
  dropMediaUrl();
  dropUrlRead();                                       // a previous URL viewer's read stops pulling bytes
  document.getElementById("romp-fileview")?.remove();
  // THIS open's read, registered for the teardowns above (the mediaUrlLive pattern): the fetch and the
  // streaming body read both ride ctrl.signal, so a close or a replace mid-body cancels them.
  const ctrl = new AbortController();
  urlAbort = ctrl;
  const wrap = el("div");
  wrap.id = "romp-fileview";
  wrap.onclick = (ev) => { if (ev.target === wrap) closeFileView(); };
  const box = el("div", "fileview");
  document.body.classList.add("fileview-open");

  // Title: host/dir/ dimmed then the basename, the local viewer's two-element treatment — but the
  // directory half is NOT a browse link here: there is no listing to open for a URL. Drawn from the
  // clicked href now and RE-DRAWN from the response's URL once it lands (a redirect moves the document).
  const bar = el("div", "fileview-bar");
  const name = el("div", "fileview-name");
  name.title = href;                                   // the full URL, one hover away
  let parts = urlTitleParts(href);
  let loc = href;                                      // where the document LIVES: the response URL once it lands
  const dir = el("span", "fileview-dir");
  dir.textContent = parts.dir;
  const base = el("span", "fileview-base");
  base.textContent = parts.base;
  name.appendChild(dir); name.appendChild(base);
  const acts = el("div", "fileview-acts");

  const fmt = loadFmt();
  let text: string | null = null;
  const segBtns: Array<["rendered" | "raw", HTMLButtonElement]> = [];
  for (const mode of ["rendered", "raw"] as const) {
    const b = el("button", "fileview-btn") as HTMLButtonElement;
    b.type = "button";
    b.textContent = mode === "rendered" ? "Rendered" : "Raw";
    b.title = mode === "rendered" ? "The prose the markdown means" : "The document's actual bytes";
    b.addEventListener("click", () => { fmt.md = mode; saveFmt(fmt); renderBody(); });
    segBtns.push([mode, b]);
    acts.appendChild(b);
  }
  // The way OUT to the URL itself, in a new tab — an anchor wearing the button treatment, the
  // GitHub link's dress: the browser owns the tab. It is also every failure pane's exit below.
  // data-new-tab: this href IS a same-origin .md, exactly what the chat's anchor delegate routes
  // back into this viewer — the marker tells it this one click means the tab.
  const linkOut = (): HTMLAnchorElement => {
    const a = el("a", "fileview-btn fileview-gh") as HTMLAnchorElement;
    a.href = href; a.target = "_blank"; a.rel = "noopener";
    a.dataset.newTab = "1";
    a.textContent = "Open ↗"; a.title = "Open the URL in a new tab";
    return a;
  };
  acts.appendChild(linkOut());
  const copy = el("button", "fileview-btn") as HTMLButtonElement;
  copy.type = "button"; copy.textContent = "Copy URL"; copy.title = href;
  copy.addEventListener("click", () => {
    navigator.clipboard?.writeText(href).then(
      () => { copy.textContent = "Copied"; setTimeout(() => { copy.textContent = "Copy URL"; }, 1200); },
      () => { copy.textContent = "Copy failed"; });
  });
  const close = el("button", "fileview-btn fileview-close") as HTMLButtonElement;
  close.type = "button"; close.textContent = "✕"; close.title = "Close (Esc)";
  close.setAttribute("aria-label", "Close the file viewer");
  close.addEventListener("click", closeFileView);
  acts.appendChild(copy); acts.appendChild(close);
  bar.appendChild(name); bar.appendChild(acts);

  const body = el("div", "fileview-body");
  // In-document links land on their heading (mdBlock's fv-anchor stamp): one delegated listener, the
  // local viewer's pattern. No fv-open here — a URL document's sibling links are made absolute and
  // the chat's own anchor delegate routes them.
  delegate(body, {
    "fv-anchor": (a, ev) => { ev.preventDefault(); scrollToFragment(body, a.getAttribute("href") || ""); },
  });
  body.addEventListener("submit", (ev) => { ev.preventDefault(); });   // the local viewer's backstop (openFileView), same reason
  body.appendChild(loaderEl());                        // loader first; the fetch below replaces it
  box.appendChild(bar); box.appendChild(body);
  wrap.appendChild(box);
  document.body.appendChild(wrap);

  // The URL's own #fragment (`evidence.md#results`) lands after the FIRST RENDERED paint — once. A
  // Raw view has no heading ids, so a saved Raw preference does not SPEND the landing: it waits for
  // the Rendered toggle (review find on #958, 2026-09-07: landed was set before the mode check).
  let landed = false;
  const landFragment = () => {
    if (landed) return;
    let hash = "";
    try { hash = new URL(href).hash; } catch { /* not a URL — nothing to land on */ }
    if (!hash) { landed = true; return; }
    if (fmt.md !== "rendered") return;                 // nothing to land on yet; the next rendered paint tries again
    landed = true;
    requestAnimationFrame(() => { if (wrap.isConnected) scrollToFragment(body, hash); });
  };
  let shownText: string | null = null;                // the text the body's view was painted from (the reader's place, below)
  // The reader's place across the Rendered/Raw switch, as the local viewer keeps it (openFileView's keptPlace and seat): read
  // before the swap, seated after it, and a seat the browser CLAMPED (reader-place.ts seatPlaceOutcome: the view swapped in
  // is shorter and the body stands at its end) holds the place it was given while the body stands where the clamp left it
  // (heldScrollTop) instead of reading the body back, which would name the block the clamp shows, so the swap back seats the
  // reader's passage. Without the hold the round trip from the end of the taller view came back a paragraph early or tens of
  // pixels off here after review round 1 had given it to the local viewer alone (the Slice 3 review, round 3, 2026-09-09;
  // file-view-url-place-bottom-browser.test.ts). The first scroll that moves the body ends the hold (the seat's own scroll
  // event reports the held scrollTop and changes nothing); no timers. The switch is the one swap this viewer's place crosses:
  // no reload, no aside, no text-size control, so none of the local viewer's reflow bookkeeping is needed here.
  let heldPlace: Place | null = null;
  let heldScrollTop = -1;
  const keptPlace = (): Place | null => (shownText === null ? null : heldPlace && body.scrollTop === heldScrollTop ? heldPlace : readPlace(body, shownText));
  const seat = (kept: Place | null) => {
    if (kept && shownText !== null && seatPlaceOutcome(body, shownText, kept).clamped) { heldPlace = kept; heldScrollTop = body.scrollTop; }
    else heldPlace = null;
  };
  body.addEventListener("scroll", () => { if (heldPlace && body.scrollTop !== heldScrollTop) heldPlace = null; }, { passive: true });
  const renderBody = () => {
    for (const [mode, b] of segBtns) {
      const on = fmt.md === mode;
      b.classList.toggle("on", on);
      b.setAttribute("aria-pressed", String(on));
    }
    if (text === null) return;                         // the loader holds the body until the bytes land
    const kept = keptPlace();                          // the reader's place under the view about to go (the held one across a clamp)
    body.replaceChildren(fmt.md === "rendered"
      ? mdBlock(text, { kind: "url", href: loc })      // relative refs resolve against where it LIVES
      : codeBlock(text, parts.base, true));            // basename → langFor → markdown highlighting
    shownText = text;
    seat(kept);                                        // the same passage at the same height across the Rendered/Raw switch, as in the local viewer
    landFragment();                                    // after the paint, and only a rendered one lands
  };
  renderBody();

  const onKey = (e: KeyboardEvent) => {
    if (e.key !== "Escape" || !document.getElementById("romp-fileview")) return;
    e.preventDefault();
    closeFileView();
    document.removeEventListener("keydown", onKey);
  };
  document.addEventListener("keydown", onKey);
  onKeyLive = onKey;                                   // registered for BOTH exits' dropOnKey, like the local viewer's

  // Every failure says WHY, in the pane, with the way out: never a console-only failure, never a
  // blank pane. The lines name the host and the URL rather than the viewer's mechanics.
  const fail = (words: string) => {
    if (!wrap.isConnected) return;                     // closed or replaced while in flight — paint nothing
    const why = el("div", "fileview-err");
    why.textContent = words;
    const hint = el("div", "fileview-err-hint");
    hint.textContent = href;
    why.appendChild(hint);
    why.appendChild(linkOut());
    body.replaceChildren(why);
  };
  const hostWord = (u: string) => urlTitleParts(u).dir.split("/")[0] || u;
  // Redraw the title from where the response actually CAME from: `/latest.md` → 302 →
  // `/reports/run-1/evidence.md` names the second, and relative figures resolve against it (loc feeds
  // mdBlock). The clicked href stays what Open ↗ and Copy URL hand back — the link the user was given.
  const relocate = (r: Response) => {
    loc = r.url || href;
    parts = urlTitleParts(loc);
    dir.textContent = parts.dir; base.textContent = parts.base; name.title = loc;
  };
  // Same-origin, cookie-authed, cache: no-store like every viewer fetch, on this open's abort signal.
  // mode: "same-origin" holds the rule through REDIRECTS too: the clicked URL passed isMarkdownUrl, but
  // a same-origin alias that 302s to a foreign host answering with a permissive CORS header would
  // otherwise be fetched and rendered with that host as the base for every relative figure (review
  // find on #958, 2026-09-07); the browser now rejects such a redirect and the .catch below says so.
  // No Content-Type sniffing beyond one refusal: the URL was intercepted because its PATH is markdown,
  // so the body is read as text and rendered as markdown whatever the server labelled it — except a
  // 200 labelled text/html, which is a web page standing in for the document (settleUrlResponse).
  fetch(href, { cache: "no-store", mode: "same-origin", signal: ctrl.signal }).then(async (r) => {
    // EVERY exit that stops short of consuming the body aborts this open's controller — once the
    // response has resolved that is what tears the transfer down (the review: a refused response's
    // bytes kept arriving for a modal already closed, because .finally had let go of the controller
    // and nothing had aborted it). settleUrlResponse fires the abort itself on each refusal verdict.
    if (!wrap.isConnected) { ctrl.abort(); return; }
    relocate(r);
    const v = settleUrlResponse(r, URL_TEXT_MAX_BYTES, () => ctrl.abort());
    if (v.kind === "http") { fail("HTTP " + v.status + " from " + hostWord(loc)); return; }
    if (v.kind === "not-document") { fail("the server answered with a web page, not a document (" + v.type + ")"); return; }
    if (v.kind === "declared-too-large") { fail(overCapWords(v.bytes, URL_TEXT_MAX_BYTES)); return; }
    if (v.kind === "no-body") { fail("this document could not be loaded from this page — the response carried no body"); return; }
    // Streamed under the cap: bytes counted as they arrive, the source cancelled the moment they pass
    // it (never the whole body buffered first), decoded as a stream so a codepoint split across two
    // chunks survives, and aborted with the viewer (ctrl.signal).
    const got = await readTextCapped(r.body!, URL_TEXT_MAX_BYTES, ctrl.signal);   // read verdict: the body is there
    if (!wrap.isConnected) { ctrl.abort(); return; }
    if ("tooLarge" in got) { ctrl.abort(); fail(overCapWords(null, URL_TEXT_MAX_BYTES)); return; }
    text = got.text;
    renderBody();                                      // paints, and lands the fragment if this paint is rendered
  }).catch((err) => {
    // Only the TEARDOWN's abort is silent (the modal is gone, or a refusal already painted its words);
    // an independently errored stream that merely wears the AbortError name still paints its failure.
    if (ctrl.signal.aborted) return;
    fail("this document could not be loaded from this page — " + String(err && (err as Error).message || err));
  }).finally(() => {
    if (urlAbort === ctrl) urlAbort = null;              // this read is over; a later open's registration stands
  });
}

// Kick the browser's downloader at `url` without touching the pane: a clicked <a download> starts a
// same-origin, cookie-authed request the BROWSER owns (its progress UI, its save location), and since
// the kernel answers with Content-Disposition: attachment the page never navigates — the viewer, the
// feed behind it, and the scroll position all stay put. The button acknowledges the click itself
// (ui/CLAUDE.md), because the browser's download UI can take a beat to appear over a slow tunnel.
function startDownload(url: string, btn: HTMLButtonElement): void {
  const a = document.createElement("a");
  a.href = url;
  a.download = "";               // a hint; the kernel's attachment disposition is what actually decides
  document.body.appendChild(a);
  a.click();
  a.remove();
  const was = btn.textContent;
  btn.textContent = "Downloading…";
  setTimeout(() => { btn.textContent = was; }, 1500);
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// Wrap mode's numbering. The flat sibling gutter cannot survive soft-wrapping — one logical line becomes
// several visual lines and every number below it drifts — so wrap mode RESTRUCTURES instead of shipping a
// misaligned column: each logical line is its own row (.fv-cl) whose number is a CSS counter in ::before
// (the chat's .cl/.ct treatment, styles.css), so the numbers stay glued to their lines however tall a
// wrapped line grows, and being ::before content they still never copy with the code. hljs spans can
// cross newlines, so each row re-opens the spans the previous row left unclosed and closes its own —
// render.ts's wrapCodeLines balance walk.
function wrapNumberedHtml(html: string): string {
  const lines = html.split("\n");
  if (lines.length && lines[lines.length - 1] === "") lines.pop();   // a trailing newline is not a line
  let open: string[] = [];
  return lines.map((ln) => {
    const prefix = open.join("");
    const re = /<span[^>]*>|<\/span>/g; let m; const stack = open.slice();
    while ((m = re.exec(ln))) { if (m[0] === "</span>") stack.pop(); else stack.push(m[0]); }
    const suffix = "</span>".repeat(Math.max(0, stack.length));
    open = stack;
    return `<span class="fv-cl"><span class="fv-ct">${prefix}${ln}${suffix}</span></span>`;
  }).join("");
}

// Line-numbered <pre>. In the default (no-wrap) view the gutter is a sibling column rather than text in
// the same <pre>, so selecting the code and copying it does NOT drag the line numbers along with it; the
// wrap view keeps that copy-safety a different way (see wrapNumberedHtml above).
function codeBlock(text: string, path: string, wrapLines: boolean): HTMLElement {
  const wrap = el("div", "fileview-code");
  const lines = text.split("\n");
  if (lines.length && lines[lines.length - 1] === "") lines.pop();   // a trailing newline is not a line
  const lang = langFor(path);
  let hl: string | null = null;
  if (lang) {
    try { hl = hljs.highlight(text, { language: lang }).value; }
    catch { hl = null; }                               // a broken grammar must never cost the content
  }
  const pre = el("pre", "fileview-pre");
  const code = el("code", "hljs");
  if (wrapLines) {
    pre.classList.add("fileview-wrap");
    code.innerHTML = wrapNumberedHtml(hl !== null ? hl : escapeHtml(text));
    linkifyFileText(code, path);   // URLs and paths in the text, on the DOM the highlight built (file-view-links.ts)
    pre.appendChild(code);
    wrap.appendChild(pre);
    return wrap;
  }
  const gutter = el("div", "fileview-gutter");
  gutter.textContent = lines.map((_, i) => String(i + 1)).join("\n");
  gutter.setAttribute("aria-hidden", "true");
  if (hl !== null) code.innerHTML = hl; else code.textContent = text;
  linkifyFileText(code, path);
  pre.appendChild(code);
  wrap.appendChild(gutter); wrap.appendChild(pre);
  return wrap;
}

// Land an in-document fragment on its target. The fragment — as typed, percent-encoded or not — names an
// element of the RENDERED document (the .fileview-md box under `box`, never the viewer's chrome around it, whose
// notice bar wears an id of its own, and never the page's ids): an element with exactly that id, a GitHub-style
// `<a name>`, or a heading, through the slug the heading ids were minted with, so `#Evidence%20Results`,
// `#evidence-results` and `#Evidence Results` all find md-evidence-results (file-view-links.ts fragmentTarget is
// the one lookup; mark time reads it too). Nothing found → nothing happens: inert, never a scroll to the top and
// never a navigation. Both viewers land through here: the local one's section links and a sibling link's
// fragment, the URL one's fv-anchor links and the URL's own hash.
function scrollToFragment(box: HTMLElement, fragment: string): boolean {
  let frag = fragment.replace(/^#/, "");
  try { frag = decodeURIComponent(frag); } catch { /* a stray % — match the bytes as written */ }
  if (!frag) return false;
  const target = fragmentTarget(box.querySelector(".fileview-md") || box, frag);
  if (!target) return false;
  target.scrollIntoView({ block: "start" });
  return true;
}

// Where the rendered document LIVES, so its relative references can be resolved against it (the user
// 2026-09-06: a `![fig](fig.png)` in a viewed document pointed at the dashboard's root). Two homes:
//   • url  — the document was fetched from `href` by the browser (openUrlView); a relative src/href
//            resolves against that URL, exactly as it would have on the page itself.
//   • file — the document is `path` on the session's disk (openFileView); a relative image is the
//            sibling file over the kernel's /file route (fileUrl — federation-aware, never hand-built),
//            and a relative link opens the sibling in this same viewer.
// No location at all (a caller with nothing to say) leaves the markup as marked emitted it.
type MdDocLoc = { kind: "url"; href: string } | { kind: "file"; path: string; sid: string | null };

// Markdown rendered as the prose it means (the user 2026-08-09: Rendered is the default, Raw one click
// away). The file is arbitrary bytes off a disk and marked emits raw HTML verbatim, so — exactly like the
// chat's md() in render.ts — the output goes through DOMPurify before it ever reaches .innerHTML: an
// <img onerror> or a javascript: href in a README must never run in the dashboard.
function mdBlock(text: string, doc?: MdDocLoc): HTMLElement {
  const box = el("div", "fileview-md");
  let rendered = true;                                 // false on the fallback: the bare text, with nothing added to it
  const fences: Fence[] = [];                          // marked's code tokens in document order, for the fence pass's Copy (fence-source.ts)
  try {
    // A link's destination is put in the form the sanitizer keeps BEFORE the HTML exists (file-view-links.ts
    // viewerWalkTokens: `notes.md:7` reads as a scheme to DOMPurify, `file:///a.md` is a scheme it refuses, and an
    // anchor it strips is a label nothing can sort afterwards). Handed to THIS parse only: the marked singleton is
    // the chat's too, and the chat's anchors must not learn the viewer's forms. A walkTokens an extension put on
    // the defaults runs as well: per-call options replace, not compose. The link hook is the file kind's alone: a URL
    // document has no directory for `notes.md:7` to sit in, and its links resolve against the URL below. Every kind
    // collects the code tokens: the lexer expanded the note's leading tabs to spaces before it cut them, and the fence
    // pass below reads each fence's text back out of the note for its Copy button (fence-source.ts).
    const base = marked.defaults.walkTokens;
    const dirty = marked.parse(text, { walkTokens: (t) => {
      if (t.type === "code") { const c = t as Tokens.Code; fences.push({ text: c.text, indented: c.codeBlockStyle === "indented" }); }
      if (doc && doc.kind === "file") viewerWalkTokens(t);
      if (base) void base.call(marked, t);
    } }) as string;
    // The one sanitizer the chat's md() uses too (md-sanitize.ts): html + svg (a note's own inline SVG), no data-*
    // (a document's `<span data-act="stopRetrying">` would otherwise bubble to render.ts's document-level delegate
    // and interrupt the active session; review find on #958, 2026-09-07), and GitHub's rules for a note's own
    // HTML: no <style>, no form controls, ids and names prefixed user-content-, inline style reduced to its
    // colours (plans/markdown-viewer.md, Slice 1). The sanitized <body>'s children are adopted as they are, no
    // re-parse. The viewer's own stamps (heading ids, the file kind's path and section links, the URL kind's
    // fv-anchor stamp) are set AFTER this sanitize, so they are unaffected and never prefixed; a section link
    // finds an author's id or name under the prefix (file-view-links.ts fragmentTarget).
    box.replaceChildren(...Array.from(sanitizeMd(dirty).childNodes));
  } catch {
    box.textContent = text;                            // a marked bug must never cost the content
    rendered = false;
  }
  // Every heading gets an id first — marked 12 emits none, so a document's own `[top](#evidence)`
  // had nothing to land on. GitHub's slug (headingSlug, made unique in order by uniqueSlugs), and
  // PREFIXED `md-` on purpose: an unprefixed id="tabs" would dress a heading in the chat page's
  // #tabs CSS and shadow getElementById("tabs") for the page's own controls. Both modes, before the
  // anchors are sorted: a section link is live when its target is a heading, an element with that id
  // or a named anchor, each under the sanitizer's user-content- prefix (file-view-links.ts fragmentTarget
  // reads all three).
  const heads = Array.from(box.querySelectorAll("h1, h2, h3, h4, h5, h6")) as HTMLElement[];
  const slugs = uniqueSlugs(heads.map((h) => headingSlug(h.textContent || "")));
  heads.forEach((h, i) => { h.id = "md-" + slugs[i]; });
  // A pixel-sized <video> keeps the author's shape (keepVideoShape, below): the sheets give it `height: auto` so it
  // shrinks in ratio with the column, and the browser's own `aspect-ratio: auto W / H` would hand that ratio to the poster.
  keepVideoShape(box);
  // A task item wears GitHub's class (Slice 3 of plans/markdown-viewer.md): marked emits the checkbox as the li's first
  // child with no hook on the li (inside its first paragraph in a loose list), and the sheets' `li.task-list-item` rule
  // drops the bullet that sat beside the box and pulls the box into the gutter. After the sanitize, and only for the
  // disabled checkbox the sanitizer's post-pass leaves (every other input is removed there); an author who writes the
  // class on an li of their own gets the same bullet-less item GitHub would give them.
  box.querySelectorAll('li > input[type="checkbox"]:first-child:disabled, li > p:first-child > input[type="checkbox"]:first-child:disabled').forEach((input) => {
    const li = input.closest("li");
    if (li) li.classList.add("task-list-item");
  });
  // Relative references resolve against the DOCUMENT, after sanitisation (DOMPurify has already
  // dropped every dangerous scheme; what is left is either absolute — untouched — or relative to a
  // document the browser knows nothing about). getAttribute, never the .src/.href property: the
  // property is already resolved against the PAGE, which is the wrong base.
  // Which elements are links: LINK_SEL (md-links.ts), the selector the chat's click delegate keys on too. An HTML <a>
  // and an inline SVG <a>, spelled `href` or SVG 1.1's `xlink:href`, both navigate on a click, and DOMPurify's html
  // and svg profiles keep both; the passes below used to run over `a[href]`, which reached only the first (`[href]`
  // matches the null-namespace attribute alone), so an SVG <a xlink:href> in a note took the pane's document to its
  // URL, in the same frame (review of Slice 1, 2026-09-07). The XLink spelling is MOVED to a plain `href`: copied when
  // the anchor has no `href` of its own (an `href` the author wrote beside it wins, as it does in the browser), then
  // removed, so the SVG anchor carries one attribute and every reader below (linkMarkdownAnchors, the fv-anchor stamp,
  // the body's click listener) and the browser read the same one. The removal matters as much as the copy: a stamp
  // that takes `href` off the anchor (a path link, a dead link) relies on an anchor with no href being nothing the
  // browser follows and nothing LINK_SEL matches, and the browser follows `xlink:href` when `href` is absent. A copy
  // that left the XLink attribute in place navigated the Files document in the same frame from a dead SVG link, and
  // let the chat's delegate (render.ts, `a[*|href]`) open a path link's `sibling.md` as a URL document resolved against
  // the chat page instead of the sibling file (round 3 of the review; md-sanitize-viewer-links-browser.test.ts clicks
  // both shapes in both pages).
  box.querySelectorAll("a[*|href]").forEach((a) => {
    const xl = a.getAttributeNS(XLINK_NS, "href");
    if (xl === null) return;                            // an HTML anchor, or an SVG one spelled `href` alone
    if (!a.hasAttribute("href")) a.setAttribute("href", xl);
    a.removeAttributeNS(XLINK_NS, "href");
  });
  if (doc && doc.kind === "url") {
    box.querySelectorAll("img[src]").forEach((node) => {
      const img = node as HTMLImageElement;
      const src = img.getAttribute("src") || "";
      const abs = resolveDocRelative(src, doc.href);
      if (abs !== src) img.setAttribute("src", abs);
    });
    box.querySelectorAll(LINK_SEL).forEach((node) => {
      const a = node as HTMLElement | SVGElement;
      const href = linkHref(a);
      if (!href || href.startsWith("#") || /^[a-z][a-z0-9+.-]*:/i.test(href)) return;   // in-document, or already absolute
      // Absolute now, so the chat's document-level anchor delegate sees a scheme: a same-origin
      // .md target opens in this viewer (isMarkdownUrl), everything else in a new tab.
      a.setAttribute("href", resolveDocRelative(href, doc.href));
    });
  } else if (doc) {
    // Figures on the session's disk: re-pointed at the kernel's /file route by rewriteFigureSrcs (below), which
    // keeps the authored src in `data-fv-src` for the comments panel's embed matching and joins the path the way
    // every other reader of an embed's destination does (a relative src under the file's directory, an absolute
    // one as itself, `..` left to the kernel), so the picture shown is the file the poll watches.
    rewriteFigureSrcs(box, doc.path.slice(0, doc.path.lastIndexOf("/") + 1), doc.sid);
  }
  if (doc && doc.kind === "file") {
    // A file on the session's disk: its links are sorted by file-view-links.ts (linkMarkdownAnchors). A link to the
    // web opens a NEW tab: the viewer lives inside the chat pane's document, and letting a README link navigate it
    // away would silently eat the chat until a reload. A link whose target is a file relative to this one becomes a
    // path link that opens THAT file in the viewer (its `#fragment` or `:line` riding along); a section link
    // (`#results`) is the viewer's scroll; a target the sanitizer removed is a dead link that says why. The module
    // walks every `a`, the SVG anchor included (its xlink:href is a plain href by now, above), and writes each
    // attribute as one, so an SVG link is stamped like an HTML one.
    if (rendered) linkMarkdownAnchors(box, doc.path);
  } else {
    // A URL document (openUrlView), or a caller with no location: links open a NEW tab, for the same reason. One
    // kind stays in the viewer: an IN-DOCUMENT `#fragment` link, which lands on its heading through the body's
    // delegated fv-anchor handler — a forced _blank on those opened a REAL tab at the chat page's own URL plus
    // the fragment (found live, 2026-09-06). A URL document's sibling links are absolute by now, and the chat's
    // own anchor delegate routes them (a same-origin .md back into the viewer). Every link element (LINK_SEL,
    // above) is stamped, and with setAttribute rather than the `target` and `rel` properties: on an SVGAElement
    // `target` is a read-only SVGAnimatedString, so the property write was dropped without a word (the bundle is
    // not strict there) and an SVG link kept navigating the pane; the attribute is what the browser reads on every
    // one of these elements.
    box.querySelectorAll(LINK_SEL).forEach((node) => {
      const a = node as HTMLElement | SVGElement;
      if (linkHref(a).startsWith("#")) { a.dataset.act = "fv-anchor"; return; }
      a.setAttribute("target", "_blank");
      a.setAttribute("rel", "noopener");
    });
  }
  // Fenced blocks: highlight only a language the fence NAMES and this bundle registers — the same
  // no-guessing rule as langFor; an unnamed block stays plain rather than being painted at random. Then, for EVERY
  // fence, named or not, the chat's own dress (code-block.ts; Slice 3 of plans/markdown-viewer.md): the per-line rows
  // that number the lines and make a soft-wrap read distinctly from a real newline, and the Copy button. Copy copies
  // the fence's text AS THE NOTE HOLDS IT (fence-source.ts, off the code tokens the parse collected): the raw text
  // captured here is read before the rows drop the newlines, but after marked's lexer turned the note's leading tabs
  // into four spaces each, so a Makefile recipe copied from the rendered text pasted back with spaces (the Slice 3
  // review); a fence the module does not find in the note copies the raw text as before. The math fill's source
  // fallback (a code element wearing md-math-src, math.ts; spelled, not imported, since this module carries no KaTeX)
  // is not code: it keeps the Copy button and nothing else, as in the chat's highlight().
  const copySources = fenceCopyQueue(text, fences);
  box.querySelectorAll("pre code").forEach((node) => {
    const codeEl = node as HTMLElement;
    const raw = codeEl.textContent || "";
    const pre = codeEl.parentElement;
    const host = pre && pre.tagName === "PRE" ? pre : null;
    if (codeEl.classList.contains("md-math-src")) { if (host) addCopyBtn(host, raw); return; }
    const queued = copySources.get(raw);
    const toCopy = (queued && queued.length ? queued.shift() : null) ?? raw;
    const lang = (codeEl.className.match(/language-([\w-]+)/) || [])[1];
    if (lang && hljs.getLanguage(lang)) {
      try {
        codeEl.innerHTML = hljs.highlight(raw, { language: lang }).value;
        codeEl.classList.add("hljs");
      } catch { /* leave plain */ }
    }
    wrapCodeLines(codeEl);
    if (host) addCopyBtn(host, toCopy);
  });
  // URLs and paths written in the prose and the code blocks, after the highlight rewrote the blocks' markup
  // (a pass before it would be undone). marked already made the prose's URLs anchors; text inside one is skipped.
  // The fallback's bare text is left bare: it is the content and nothing else, which is that branch's promise.
  if (rendered && doc && doc.kind === "file") linkifyFileText(box, doc.path);
  return box;
}

/** A markdown file's path figures — `![](plot.png)`, `<img src="figs/a.png">`, `![](/srv/notes-api/figs/a.png)` — name
 *  files on the kernel's disk, and a browser resolving them against the page URL (/files, /chat, /feed) 404'd every
 *  one: a relative src against the page's directory, an absolute path against the dashboard ORIGIN, where no route
 *  serves it; only http(s), data: and other URLs ever rendered (plans/file-review.md, Images and PDFs; Slice 3). So
 *  each path `src` in the sanitized rendered DOM is re-pointed at the kernel's /file route — fileUrl: same-origin,
 *  cookie-authed, and a remote session's figure relays through /remote/<host>/file exactly as the file itself did.
 *  A relative src names `<dir of the open file>/<src>`; an absolute one (`/…`) names that path itself, which is how
 *  every other reader of an embed's destination already takes it — the panel's embed matching (embedPath, in
 *  file-comments.ts), the poll's figurePath (file-comments-model.ts) and the host's resolveSrc (file-comments-host.mjs)
 *  — so the picture shown is the file the poll watches and the host hashes (review round 2: the viewer alone left
 *  it a page-origin URL, and a region could be drawn on a broken-image box over a figure the person never saw).
 *  A `~/…` src is a relative one whose first segment is `~`: markdown has no home anchor, so every markdown reader
 *  and the two readers above take it as a directory named `~` beside the file, and the kernel's `~` expansion
 *  (_resolve_open_path) never sees it because the joined path no longer starts with it. A LINK's `~/…` is the
 *  opposite on purpose (joinDocPath leaves it for the kernel to expand): a link has one reader, the kernel at click
 *  time; a figure has three that must name one file (file-view-figures-absolute.test.ts pins both, and docs/guide.md
 *  states them). Untouched: a src with a scheme (http:, https:, data:, blob:, …), a protocol-relative URL
 *  (`//host/…`, which the browser and every markdown reader take as a web address), and an empty one. `..` segments and `./` pass through
 *  as written: the kernel resolves the path and gates it, and a client-side normalization would be a second, weaker
 *  opinion on what it serves. marked percent-encodes destinations (`six seven.png` renders as `six%20seven.png`), so
 *  the attribute is decoded back to a path first (decodeURI; a malformed escape is taken as written). The authored
 *  attribute value survives as `data-fv-src` on every rewritten figure: the panel's embed matching (embedFor /
 *  imgForRange in file-comments.ts) and a region comment's `src` need the source's own spelling, not a URL. An
 *  untouched figure's `src` IS that value, and an authored `data-fv-src` on one is dropped so the attribute means one
 *  thing: this viewer rewrote this src. Runs on the DOM after DOMPurify, never on marked's HTML string — a string
 *  rewrite would re-parse attribute syntax the sanitizer already settled, and a src the sanitizer removed must stay
 *  removed. `dir` carries its trailing slash ("" for a bare relative file name, which then resolves against the
 *  session's cwd like the file did). */
export function rewriteFigureSrcs(root: ParentNode, dir: string, sid: string | null | undefined): void {
  root.querySelectorAll("img[src]").forEach((node) => {
    const img = node as HTMLElement;
    const src = img.getAttribute("src") || "";
    if (!src || src.startsWith("//") || /^[a-z][a-z0-9+.-]*:/i.test(src)) { img.removeAttribute("data-fv-src"); return; }
    let rel = src;
    try { rel = decodeURI(src); } catch { /* a malformed escape: the spelling as written */ }
    img.setAttribute("data-fv-src", src);
    img.setAttribute("src", fileUrl(rel.startsWith("/") ? rel : dir + rel, sid));
  });
}

/** A pixel-sized `<video>` keeps the shape its `width` and `height` attributes give it, capped or not. The viewer's sheets
 *  (styles.css and feed.css, the .fileview-md media rules) cap an inline svg, canvas or video at the column and give a
 *  PIXEL-sized one `height: auto`, so it shrinks in its own ratio rather than into a letterbox of its height attribute.
 *  For an svg or a canvas that ratio is the attributes' by construction. For a video the browser maps the attributes to
 *  `aspect-ratio: auto W / H`, and `auto` there means the media's natural ratio wins once it has one: the poster's while
 *  the poster shows, the frames' once metadata loads. So a `<video width="640" height="360">` with a square poster laid
 *  out 640 by 640 in a pane that shrank nothing, and its box jumped to 640 by 360 when it played (review of Slice 1,
 *  round 2). The attributes' ratio is written as the element's aspect-ratio WITHOUT `auto`, so the box is the author's
 *  shape whether the cap shrinks it or not, and the media sits letterboxed inside it as a video always has (its default
 *  object-fit is contain). A percentage in either attribute is left alone, as the sheet's rule leaves a percentage
 *  width: the cap never shrinks it and the height attribute stands. Runs on the sanitized DOM: the declaration is the
 *  viewer's own, not an author's inline style, which the sanitizer reduces to its colours (md-sanitize.ts). Laid out
 *  over the real bundle in md-sanitize-wide-media-browser.test.ts, each spelling of a length included. */
function keepVideoShape(root: ParentNode): void {
  root.querySelectorAll("video[width][height]").forEach((node) => {
    const v = node as HTMLElement;
    const w = pxDimension(v.getAttribute("width")), h = pxDimension(v.getAttribute("height"));
    if (w > 0 && h > 0) v.style.aspectRatio = w + " / " + h;
  });
}

/** An HTML dimension attribute as a length, by HTML's rules for parsing dimension values: leading whitespace, digits, an
 *  optional fraction; a `%` right after the number makes it a percentage (0 here, as is anything that does not start
 *  with a number). `640`, `640.5` and `640px` are lengths, as they are to the browser, whose own mapping of the
 *  attributes reads them the same way; `50%` is not. Mirrors the sheet's `[width]:not([width$="%"])`. The whitespace
 *  skip is HTML's rule kept for fidelity: the value read here has been through the sanitizer, which trims every
 *  attribute value (DOMPurify, all but `value`), so the `%` test here and the sheet's `$="%"` never meet a padded one. */
function pxDimension(attr: string | null): number {
  const m = /^[ \t\n\f\r]*(\d+(?:\.\d*)?)(%?)/.exec(attr || "");
  return m && !m[2] ? Number(m[1]) : 0;
}

// ── a selection across a repaint (fireRenderedKeepingSelection): each end kept, and put back ──
/** One end of a selection as kept across a paint: the point itself (node, offset), its character offset into the body's
 *  text (at), and the side of a text-node boundary it sat on (side: "end" for the end of a text node, "start" for the
 *  beginning of one, null for a point inside one). The side is what the offset loses. The Raw view's rows (.fv-cl) carry
 *  no newline text and a markdown <br> is no text either, so the end of a row's text and the first column of the next
 *  have ONE offset; the point kept (a start after a row's last glyph, a triple-click's end at the next row's first
 *  column) says which. An element point (a triple-click's end, the browser's point before or after a <br> or a picture)
 *  is read by what stands beside it: before a child whose first leaf is text it is that text's start; before anything
 *  else (a <br>, a picture, an empty row) it is where the text before ends. With no child after it: after a child whose
 *  last leaf is text it is that text's end, after anything else the start of the text that follows. */
type KeptPoint = { node: Node; offset: number; at: number; side: "start" | "end" | null };
function keepPoint(root: Node, node: Node, offset: number): KeptPoint | null {
  if (offset > nodeLength(node)) return null;
  const at = textOffset(root, node, offset);
  return at === null ? null : { node, offset, at, side: boundarySide(node, offset) };
}
const nodeLength = (n: Node): number => (n.nodeType === 3 ? (n as Text).data.length : n.childNodes.length);
function boundarySide(node: Node, offset: number): "start" | "end" | null {
  if (node.nodeType === 3) return offset >= (node as Text).data.length ? "end" : offset === 0 ? "start" : null;
  const after = node.childNodes[offset]; const before = offset > 0 ? node.childNodes[offset - 1] : undefined;
  if (after) return leafIsText(after, true) ? "start" : "end";
  if (before) return leafIsText(before, false) ? "end" : "start";
  return null;
}
/** Whether the first (or last) leaf under n, through its elements, is a text node. */
function leafIsText(n: Node, first: boolean): boolean {
  let c: Node | null = n;
  while (c && c.nodeType !== 3) c = first ? c.firstChild : c.lastChild;
  return !!c;
}
/** A point (node, offset) as a character offset into root's text: the data of root's text nodes in document order up to
 *  the point (a Range's toString), the count the panel's re-wrapping of its marks leaves unchanged. null when the point
 *  lies outside root. */
function textOffset(root: Node, node: Node, offset: number): number | null {
  if (!root.contains(node)) return null;
  const r = document.createRange();
  r.setStart(root, 0); r.setEnd(node, offset);
  return r.toString().length;
}
/** The kept end, in the body as the paint left it. Its own point when that still stands: the node inside root, the
 *  offset within it, and the same text before it (a text node the paint moved into a mark, or left alone; an element
 *  whose children the paint split means something else at that index, and fails the last test). Otherwise the offset
 *  mapped back into the text nodes root holds NOW, the side of a boundary chosen by the side kept — an end that sat at
 *  the end of a text node goes to the end of the earlier node, one at the start to the start of the later — and, for a
 *  point that sat inside a text node the paint has since split there, by its role (`earlier`: the selection's start
 *  takes the later node, its end the earlier), the two homes holding the same text. */
function pointBack(root: Node, k: KeptPoint, earlier: boolean): [Node, number] {
  if (k.node.isConnected && root.contains(k.node) && k.offset <= nodeLength(k.node) && textOffset(root, k.node, k.offset) === k.at) return [k.node, k.offset];
  return textPoint(root, k.at, k.side === null ? earlier : k.side === "start");
}
/** The point at character offset n of root's text, in the text nodes root holds NOW: inside the text node that holds n,
 *  root's end when n lies past its text. A point BETWEEN two text nodes has two homes: `start` takes the beginning of the
 *  later one, else the end of the earlier. */
function textPoint(root: Node, n: number, start: boolean): [Node, number] {
  const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let seen = 0; let last: Text | null = null;
  for (let t = w.nextNode() as Text | null; t; t = w.nextNode() as Text | null) {
    if (start ? seen + t.data.length > n : seen + t.data.length >= n) return [t, n - seen];
    seen += t.data.length; last = t;
  }
  return last ? [last, last.data.length] : [root, root.childNodes.length];
}

// The media body's "shown" moment, for the seam's onRendered (Slice 3: the region overlay sizes itself against
// the picture, so it must run once there IS one). A PDF frame counts as shown the moment it is in the body — the
// browser's viewer owns everything inside it and gives no signal to wait for (the same reason pdfBlock arms no
// error listener). An <img> counts once it has decoded: at once when it already had (`complete` — a blob the
// browser still holds), else on its load event. A load that lands after the img left the document fires nothing:
// a reload replaced it, the decode failed and imgFailed's pane took the body (a paint of its own, which fires the
// hooks itself), or the viewer closed — what shows then is something else, and an overlay sized against the old
// picture would frame nothing anyone sees.
function whenShown(shown: HTMLElement, cb: () => void): void {
  const img = shown.querySelector("img.fileview-img") as HTMLImageElement | null;
  if (!img || img.complete) { cb(); return; }
  img.addEventListener("load", () => { if (img.isConnected) cb(); }, { once: true });
}

// The image body: ONE <img> aimed at the object URL — never innerHTML, never an iframe. That is the
// whole SVG-safety story (an <img> never runs SVG scripts — the same surface the kernel's preview
// comments and the relay's local type re-derivation rely on), and for every other image it is simply
// the right element. Centered and capped like the lightbox's image (.romp-lightbox-img), so a huge
// plot fits the card and a small icon renders at its own size. Bytes that will not decode fire the
// img's error event into onDecodeFail (armed before src, so no event can slip past), where the open
// viewer swaps in its failure pane — the caller owns the pane; this stays a pure element builder.
function imgBlock(objUrl: string, path: string, onDecodeFail: () => void): HTMLElement {
  const box = el("div", "fileview-imgbox");
  const img = el("img", "fileview-img") as HTMLImageElement;
  img.addEventListener("error", onDecodeFail, { once: true });
  img.src = objUrl;
  img.alt = path;
  box.appendChild(img);
  return box;
}

// The PDF body mirrors the lightbox's treatment exactly (openLightbox's pdf arm, preview.ts): the
// browser's own viewer in a PLAIN iframe — className, src, title, nothing more — aimed at the
// already-fetched bytes instead of a second network fetch. The frame comes in its column from the
// first paint (.fileview-pdffall in the sheets: a flex column the frame fills), so that a notice can
// go above it later WITHOUT the frame moving — an iframe re-inserted anywhere reloads its document,
// and with it the place the reader had reached. With the Comments panel closed this is the PDF's
// body; with it open it is what a failed pages attempt leaves showing, under showPdfPages's notice
// (Slice 4).
function pdfBlock(objUrl: string, path: string): HTMLElement {
  const col = el("div", "fileview-pdffall");
  const frame = el("iframe", "fileview-frame") as HTMLIFrameElement;
  frame.src = objUrl;
  frame.title = path;
  col.appendChild(frame);
  return col;
}

/** Bind the pane's WS poster and route saveFile + fileGitLink replies back to the open viewer.
 *  Called once, from the pane's boot (render.ts and feed.ts today — either document, one mechanism);
 *  every reply is reqId-guarded so one landing after a close or a replace-open touches nothing. The
 *  viewFile branch is the receiving end of the shell's relay of a chat file-link click — sent again
 *  since 2026-08-20, when the click site carries the cards-pane preference (fileLinkPane, render.ts
 *  openPath); the sid rides along so a remote session's file still resolves against the host that
 *  owns it. A REAL open answers the shell with viewFileOpened — the shell arms its pane-restore
 *  flag only on that ack, so a lost relay (or a dirty-edit veto, which opens nothing) can never
 *  leave a stale armed flag behind. That ack and viaRelay are the FEED's contract; a document with
 *  a relay contract of its own passes `onRelay` and takes the relayed message whole instead (the
 *  Files pane, 2026-09-03: it caches the identity the relay carries, keeps its recent list, and
 *  owes the shell no pane restore, since the pane stays up). */
export function initFileView(poster: (m: Record<string, unknown>) => void,
                             onRelay?: (m: { path: string; sid?: unknown; identity?: unknown; todoId?: unknown }) => void,
                             host?: { openFile?: (path: string, sid: string | null, line: number | null, frag: string | null) => void }): void {
  post = poster;
  if (host && host.openFile) openLinkedFile = host.openFile;   // a link inside a shown file opens through the host (the Files pane's Recent list)
  window.addEventListener("message", (e: MessageEvent) => {
    const m = e.data;
    if (!m) return;
    if (m.romp === "viewFile" && typeof m.path === "string" && m.path) {
      if (onRelay) { onRelay(m); return; }   // this document's own contract (the Files pane) — not the feed's
      // gated on the verdict: a dirty-edit veto keeps the PREVIOUS viewer, which must not be
      // re-tagged as relay-opened (a false announce on ITS close) and earns no ack (arm-on-ack —
      // the shell must not arm a restore for an open that never happened)
      if (openFileView(m.path, typeof m.sid === "string" ? m.sid : null)) {
        viaRelay = true;   // this open rode the shell's relay — the close must tell the shell (closeFileView)
        try { if (window.parent !== window) window.parent.postMessage({ romp: "viewFileOpened" }, "*"); }
        catch { /* no shell — nothing was brought forward, nothing to arm */ }
      }
    } else if (m.type === "fileGitLink" && gitHooks && m.reqId === gitHooks.reqId) {
      const h = gitHooks; gitHooks = null;
      h.apply(String(m.url || ""), String(m.reason || ""));
    } else if (m.type === "fileSaved" && editHooks && m.reqId === editHooks.reqId) {
      const h = editHooks; editHooks = null;
      // `logged`: the comments log took the edit (Slice 1; absent on an older kernel = false). `logWarning`:
      // the kernel's account of an append that failed or a log it could not read back — saveFile's reply
      // is the ONLY place that text exists, so a reader that dropped it would lose it for good.
      h.logWarning = typeof m.logWarning === "string" && m.logWarning ? m.logWarning : null;
      h.saved(String(m.mtimeNs || ""), m.logged === true);
    } else if (m.type === "fileSaveFailed" && editHooks && m.reqId === editHooks.reqId) {
      const h = editHooks; editHooks = null;
      h.failed(String(m.error || "the save failed"));
    } else if (m.type === "warn" && editHooks) {
      // A federation drop (the session's host unreachable) answers a saveFile with a warn instead
      // of a reply — the feed page renders no toasts, so without this the button spins forever
      // (the same hole the browse overlay closed for listDir).
      const h = editHooks; editHooks = null;
      h.failed(String(m.text || "the session's host is not answering — the save was not sent"));
    }
  });
  // A socket drop mid-save loses the ack, and the frame itself may or may not have reached the
  // kernel — the honest answer is to say exactly that and re-arm Save: a save that DID land will
  // refuse the retry as "changed on disk", and Reload resolves it from there. Keying on the shim's
  // own drop event (not a timer) is the house rule; the browse overlay set the precedent.
  window.addEventListener("romp:wsdown", () => {
    if (!editHooks) return;
    const h = editHooks; editHooks = null;
    h.failed("the connection dropped mid-save — it may or may not have landed; "
      + "Save again once the connection returns (a save that DID land will refuse as changed-on-disk)");
  });
  // A drop while the GitHub ask is out loses its reply (the frame went; nothing re-sends it), and the
  // placeholder would pulse for the rest of the open. The socket's RETURN is the event that re-asks —
  // same reqId, so a first reply that was merely late and the second are one answer (the browse
  // overlay's re-ask on romp:wsup is the precedent). A read-only query: asking twice costs nothing.
  window.addEventListener("romp:wsup", () => { if (gitHooks) gitHooks.ask(); });
}
