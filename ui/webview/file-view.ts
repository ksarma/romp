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
import { marked, type Token, type Tokens } from "marked";
import { sanitizeMd, revealFragmentTarget } from "./md-sanitize";
import { applyMdConfig } from "./md-config";   // the one markdown configuration (md-config.ts)
import { literalizeUnclosedTags } from "./md-literal-tags";   // an inline start tag with no end tag in its block renders as literal text, on this parse's tokens (plans/file-review.md, decision 52)
import { gateRemoteFigures, gateOf, loadGatedHost, figureRefs, parseSrcset, serializeSrcset, GATE_ACT } from "./figure-gate";   // decision 8: a figure on an unlisted host loads on a click (figure-gate.ts)
import { hostOf, bareId, hostNameNodes } from "./host-prefix";
import { fileUrl } from "./preview";
import { ICON_DOWNLOAD, ICON_COPY, ICON_EDIT, ICON_ZOOM, ICON_CHECK, ICON_CROSS } from "./icons";   // the bar's glyphs (T367)
import { openPdfTab, wantsOwnTab } from "./preview";   // a PDF's own tab, and the gesture that asks for it
import { openFileTab, canPreview } from "./preview";   // any file's own tab, for the links inside a shown file, and the web-vs-webview test
import { headVerdict, mtimeMoved, ABSENT } from "./file-comments-model";   // the panel's reading of a HEAD /file answer, shared by the changed-on-disk probe (Slice 6, item 5); ABSENT: a 404, the bar's deletion words
import { kernelUrl } from "./media";
import { quoteSrcLabel } from "./docreview";
import { fileCommentsAction, panelMark } from "./file-comments";
import { pictureDest } from "./file-comments";       // the authored source a failed figure's label names (armFigureLabels): the panel's own rule, not a second reading of data-fv-src
import { readPlace, seatPlaceOutcome, followPlace, blockHolding, blockIndexAt, type Place } from "./reader-place";   // the reader's place across a paint (Slice 2 of plans/markdown-viewer.md); blockHolding: the block an open's `{ offset }` names, blockIndexAt: the block a remembered place's span starts, followPlace: the last measured place into the text a reload landed under a boxless body (Slice 6)
import { sourceBlockSpans, renderedBlockElements } from "./anchor-map";   // the block table and its elements, for an open's `{ offset }` in the Rendered view (Slice 6 of plans/markdown-viewer.md)
import { rawRowForOffset } from "./anchor-map";   // the verified Raw row map, for scrollToOffset (Slice 7 of plans/markdown-viewer.md, item 7): the row whose source span holds an offset, following whatever split the rows were built on
import { linkifyFileText, linkMarkdownAnchors, viewerWalkTokens, fragmentTarget, URL_LINK_CLASS, FRAG_LINK_CLASS } from "./file-view-links";
import { selectionOpenIn } from "./path-links";
import { PDF_MAX_BYTES, pdfCapMessage } from "./pdf-cap";   // the pages cap, pure (Slice 4); never the chunk itself
// eslint-disable-next-line @typescript-eslint/no-var-requires
const gclock = require("./gesture-clock.js");   // the gesture clock every settings post stamps through
import { delegate, flash, pressHold } from "./actions";   // pressHold: a fetch landing waits while a pointer is pressed over the body (the reload under a press); flash: the Outline button's press pulse
import { resolveDocRelative, joinDocPath, urlTitleParts, headingSlug, uniqueSlugs, LINK_SEL, XLINK_NS, linkHref } from "./md-links";
import { readTextCapped, overCapWords, settleUrlResponse } from "./capped-read";
import { wrapCodeLines, addCopyBtn } from "./code-block";   // a fence's per-line rows and Copy button, the chat's own
import { fenceCopyQueue, type Fence } from "./fence-source";   // what Copy copies: the fence's text as the file holds it, tabs and all
import "./viewer-grammars";   // six more grammars for a viewed file, registered on the bundle's hljs core (rust, go, c, java, sql, toml)

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
  rs: "rust", go: "go", c: "c", h: "c", java: "java", sql: "sql", toml: "ini", ini: "ini",   // viewer-grammars.ts (toml is hljs's ini grammar)
};

function langFor(path: string): string | null {
  const ext = path.slice(path.lastIndexOf(".") + 1).toLowerCase();
  return LANG[ext] || null;
}

// marked is a per-bundle singleton, configured ONCE for every bundle by md-config.ts (Slice 4 of
// plans/markdown-viewer.md): GFM without hard breaks, strikethrough on DOUBLE tildes only, the math placeholders
// KaTeX fills after the sanitize, front matter, footnotes, callouts, ==mark==, wikilinks and embeds. render.ts and
// anchor-map.ts make the same call; the first configures and the rest are no-ops, so this module is correct in
// any bundle it lands in (files.js and feed.js carry the grammar, the fill and KaTeX through this import; the
// chat page's viewer parsed with the chat's grammar before, the other two with none).
applyMdConfig();

// ── view-format preferences ────────────────────────────────────────────────────────────────────────
// The Raw ⇄ Rendered choice for markdown and the word-wrap toggle persist in localStorage, NOT a kernel
// file — per-browser view state, the same call feed-view-state.ts makes for the feed's open sections (it
// must survive a kernel restart without a round-trip to the thing that just restarted). RENDERED is the
// default for markdown (the user 2026-08-09); Raw stays one click away.
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

function el(tag: string, cls?: string): HTMLElement {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  return e;
}

// ── the paint bracket ──────────────────────────────────────────────────────────────────────────────
// Runs one pass of the viewer as a timed frame of the page's performance collector (perf-telemetry.ts; the
// page publishes it as window.__rompPerf, federation.js on a kernel page and the pane's own bundle in VS Code),
// under the type `fileview:<why>`: `paint`, the text body painted anew, in the file view and the URL view alike,
// and `reflow`, the Comments panel's re-place of its cards over reflowed text (the body's width changed, or a
// text-size step; fireRenderedKeepingSelection). The viewer receives no frames of its own, so without this the
// cost of painting a large document (marked, the sanitizer, the highlight, the link pass) reached the pane's
// minute row only as a long animation frame attributed to whichever callback ran it, and `romp perf client`
// could not name the viewer.
// Counted under the pane that hosts the viewer (app chat, feed or files), with the main-thread-free sample the
// collector takes after an outermost bracket. No collector on the page (a page without one, a stand-in), or a
// slot holding something of another shape: the pass runs untimed, exactly as before.
function perfTimed<T>(why: string, fn: () => T): T {
  let p: any = null;
  try { p = typeof window !== "undefined" ? (window as any).__rompPerf : null; } catch { p = null; }
  return p && typeof p.timed === "function" ? p.timed("fileview:" + why, fn) : fn();
}

// ── text size (A−, A+, Ctrl/Cmd + wheel) ───────────────────────────────────────────────────────────
// The viewer's text sizes, as percentages of the page's own size: a FIXED table with ends, not a free
// multiplier, so the buttons, the wheel and the stored value all land on the same few sizes and a size can
// never run away. 100 is the default and leaves every size exactly as it was. The chosen step rides the
// viewer root as `data-fv-text`, and the sheets turn it into the ONE property the text views read
// (`--fv-scale`; the "text size and measure" block in styles.css and feed.css). Persisted like the
// Rendered ⇄ Raw choice above: per browser, in localStorage, under its own key, and any malformed or
// foreign value reads as the default (parseFmt's contract). The value stays a percentage, never a
// multiplier, so the stored text and the readout say the same thing.
export const TEXT_SIZES: readonly number[] = [70, 80, 90, 100, 115, 130, 150, 175, 200];
export const TEXT_SIZE_DEFAULT = 100;
const TEXT_SIZE_KEY = "romp:fileviewTextSize";
/** A stored value back to a step of the table; anything else (absent, garbage, a size the table does not
 *  hold, a multiplier) is the default, so a corrupt entry may cost the preference, never the viewer. */
export function parseTextSize(raw: string | null | undefined): number {
  const n = Number(raw ?? NaN);
  return TEXT_SIZES.includes(n) ? n : TEXT_SIZE_DEFAULT;
}
/** The step next to `pct` in `dir`, clamped at the table's ends (from 200, +1 answers 200). A `pct` the table
 *  does not hold (never stored, but the function is pure) steps from the default. */
export function stepTextSize(pct: number, dir: 1 | -1): number {
  const from = TEXT_SIZES.includes(pct) ? pct : TEXT_SIZE_DEFAULT;
  const i = TEXT_SIZES.indexOf(from) + dir;
  return TEXT_SIZES[Math.min(TEXT_SIZES.length - 1, Math.max(0, i))];
}
function loadTextSize(): number {
  try { return parseTextSize(localStorage.getItem(TEXT_SIZE_KEY)); } catch { return TEXT_SIZE_DEFAULT; }
}
function saveTextSize(pct: number): void {
  try { localStorage.setItem(TEXT_SIZE_KEY, String(pct)); } catch { /* storage full */ }
}
// Ctrl/Cmd + wheel over the text is the pointer's way to the same steps. A wheel notch is one event of about
// 100 pixels (Chrome) or a few LINES (Firefox, deltaMode 1); a trackpad pinch, which browsers report as a
// ctrlKey wheel, is a burst of events a few pixels each. Stepping once per event would run a pinch through
// the whole table in a moment, so the deltas are SUMMED: normalized to pixels, added up, and a step is taken
// each time the sum passes WHEEL_STEP_PX (then cleared); a change of direction clears it too, so a reversal
// does not first pay off the other way's remainder. Pure over the event's fields, so the summing is testable:
// `acc` is the running sum the caller keeps, `dir` the step to take now (0 for none). Events without the
// modifier are not the gesture (the caller lets them scroll) and never reach this.
export const WHEEL_STEP_PX = 40;
export function foldWheel(e: { deltaY: number; deltaMode: number }, acc: number): { acc: number; dir: 0 | 1 | -1 } {
  const px = e.deltaY * (e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? 400 : 1);   // lines and pages as pixels
  if (px === 0) return { acc, dir: 0 };
  const sum = acc !== 0 && Math.sign(acc) !== Math.sign(px) ? px : acc + px;         // a reversal starts over
  if (Math.abs(sum) < WHEEL_STEP_PX) return { acc: sum, dir: 0 };
  return { acc: 0, dir: sum < 0 ? 1 : -1 };                                           // wheel up is larger
}
// The control: A−, the current size as the reset between them, A+. Built once per open by BOTH viewers (a
// file on disk and a document opened from a link on the dashboard's own address), so the two honour one
// stored size and a step in either is kept for both. The readout is said only once the size is off the
// default (at 100% there is nothing to reset and nothing to say), but its SLOT is there from the start: the
// sheet empties it by visibility, not display, so neither A− nor A+ moves under the pointer when it fills
// after the first press, and the empty slot leaves the tab order. An end of the table is said with
// aria-disabled, not `disabled`: a button that disables under keyboard focus drops it (the ring would vanish
// on the press that reached the end), while an aria-disabled one keeps the focus, wears the sheet's disabled
// dress, and its press is the no-op set() already makes of a step to the size in force. The three hide until
// `textShowing` says a text body is up: each viewer's renderBody calls sync() on every paint, the first of them
// before the fetch, so the loader, a picture, a PDF and the editor never show them. Direct listeners are
// click-safe here: the buttons are built once and never rebuilt by a paint (the format toggles' idiom), and
// every press acknowledges in the same tick (the attribute, the readout, the dimmed end; the sheets reflow
// from the attribute alone). A caller may bracket the apply (the third argument; the identity default runs it bare): both
// viewers read the reader's place before it and seat it after, and the local viewer's bracket also re-places the comments
// panel's cards (the seam's reflow).
function textSizeControl(root: HTMLElement, textShowing: () => boolean, step: (apply: () => void, keyboard: boolean) => void = (apply) => apply()): { buttons: HTMLButtonElement[]; wrap: HTMLElement; trigger: HTMLButtonElement; menu: HTMLElement; sync: () => void; bindWheel: (body: HTMLElement) => void } {
  let pct = loadTextSize();
  const down = el("button", "fileview-btn fileview-size") as HTMLButtonElement;
  down.type = "button"; down.textContent = "A−"; down.title = "Smaller text (Ctrl/Cmd + wheel)";
  down.setAttribute("aria-label", "Smaller text");
  const reset = el("button", "fileview-btn fileview-size fileview-size-reset") as HTMLButtonElement;
  reset.type = "button"; reset.title = "Reset the text size";
  const up = el("button", "fileview-btn fileview-size") as HTMLButtonElement;
  up.type = "button"; up.textContent = "A+"; up.title = "Larger text (Ctrl/Cmd + wheel)";
  up.setAttribute("aria-label", "Larger text");
  const buttons = [down, reset, up];
  // T367 (the user 2026-09-12): the three ride a FLYOUT behind one zoom glyph, the bar's one control for the text
  // size (a magnifier with a plus; the words in its title and aria-label). The flyout wears the menu vocabulary
  // (the menu tokens, ui/CLAUDE.md) and opens under the glyph; the glyph again, Escape or a press outside closes
  // it (one document listener pair for every control, wired once), and it closes with the glyph when no text
  // shows. Built once per open with the buttons: click-safe, and the wheel binding is untouched.
  const wrap = el("span", "fileview-zoom");
  const trigger = el("button", "fileview-btn fileview-icon fileview-zoom-btn") as HTMLButtonElement;
  trigger.type = "button"; trigger.innerHTML = ICON_ZOOM; trigger.dataset.icon = "1";
  trigger.setAttribute("aria-label", "Text size");   // the title carries the size too, set by apply() below
  trigger.setAttribute("aria-haspopup", "true"); trigger.setAttribute("aria-expanded", "false");
  const menu = el("div", "fileview-zoom-menu");
  menu.hidden = true;
  menu.setAttribute("role", "group"); menu.setAttribute("aria-label", "Text size");
  for (const b of buttons) menu.appendChild(b);
  wrap.appendChild(trigger); wrap.appendChild(menu);
  const setOpen = (open: boolean) => {
    if (open && zoomOpen && zoomOpen.wrap !== wrap) zoomOpen.close();   // one flyout at a time, by rule (review)
    const focusInside = !open && !menu.hidden && !!document.activeElement && typeof menu.contains === "function" && menu.contains(document.activeElement);
    menu.hidden = !open;
    trigger.setAttribute("aria-expanded", open ? "true" : "false");
    trigger.classList.toggle("on", open);
    zoomOpen = open ? { wrap, close: () => setOpen(false) } : (zoomOpen && zoomOpen.wrap === wrap ? null : zoomOpen);
    if (focusInside) trigger.focus();   // Escape, or an outside press with the focus inside: back to the glyph, never left on a hidden button (review)
  };
  trigger.addEventListener("click", () => setOpen(menu.hidden));
  wireZoomDismiss();
  const atEnd = (b: HTMLButtonElement, end: boolean) => { if (end) b.setAttribute("aria-disabled", "true"); else b.removeAttribute("aria-disabled"); };
  // the property on the root, and the control's own state, from pct
  const apply = () => {
    root.dataset.fvText = String(pct);
    reset.textContent = pct + "%";
    trigger.title = "Text size " + pct + "% (Ctrl/Cmd + wheel)";   // the readout is a click away, so the hover says it (review)
    reset.setAttribute("aria-label", "Text size " + pct + "%, reset to " + TEXT_SIZE_DEFAULT + "%");
    reset.classList.toggle("fileview-size-default", pct === TEXT_SIZE_DEFAULT);   // the empty slot
    atEnd(down, pct === TEXT_SIZES[0]);
    atEnd(up, pct === TEXT_SIZES[TEXT_SIZES.length - 1]);
  };
  apply();                                                    // on the root before the bytes land: the first paint is at size
  // one step: store it and apply it; a step that changes nothing (an end of the table, a reset at the default) does nothing.
  // `keyboard`: the step came from a key on the focused button (Enter, Space: the browser's synthesized click carries
  // detail 0, a pointer's click its count), which the viewer's keyboard rule reads (openFileView takeKeyboard): a keyboard
  // user pressing A+ three times must find the button still under the focus for the second and third press
  // (file-view-text-size.test.ts); a pointer's step and a wheel step hand the keyboard to the body.
  const set = (n: number, keyboard = false) => { if (n === pct) return; pct = n; saveTextSize(n); step(apply, keyboard); };
  down.addEventListener("click", (e) => set(stepTextSize(pct, -1), e.detail === 0));
  up.addEventListener("click", (e) => set(stepTextSize(pct, 1), e.detail === 0));
  reset.addEventListener("click", (e) => set(TEXT_SIZE_DEFAULT, e.detail === 0));
  // Ctrl/Cmd + wheel over the BODY (not the bar): the browser's page zoom is the same gesture, so it is taken
  // over the viewer's text only, and only with the modifier held over a text body; a plain wheel scrolls as
  // ever, and the keyboard's Ctrl+plus/minus stays the browser's. Non-passive, so the page zoom can be
  // prevented; the summing is foldWheel's.
  let acc = 0;
  const bindWheel = (body: HTMLElement) => {
    body.addEventListener("wheel", (e: WheelEvent) => {
      if (!(e.ctrlKey || e.metaKey) || !textShowing()) return;
      e.preventDefault();
      const r = foldWheel(e, acc);
      acc = r.acc;
      if (r.dir) set(stepTextSize(pct, r.dir));
    }, { passive: false });
  };
  const sync = () => { const hide = !textShowing(); trigger.hidden = hide; if (hide) setOpen(false); };
  return { buttons, wrap, trigger, menu, sync, bindWheel };
}
// one text-size flyout open at a time, dismissed by Escape (in the capture phase, before the viewer's own Escape
// closes the file) or a press outside it; the pair of document listeners is wired once, for every control
let zoomOpen: { wrap: HTMLElement; close: () => void } | null = null;
let zoomDismissWired = false;
function wireZoomDismiss(): void {
  if (zoomDismissWired) return;
  zoomDismissWired = true;
  // a viewer closed with its flyout open (the close cross from the keyboard) leaves no reference behind that could
  // swallow the next viewer's Escape: closeFileView clears it, and a detached wrap is dropped here as well (review)
  const live = () => { if (zoomOpen && !zoomOpen.wrap.isConnected) zoomOpen = null; return zoomOpen; };
  document.addEventListener("mousedown", (e) => { const z = live(); if (z && !z.wrap.contains(e.target as Node)) z.close(); });
  document.addEventListener("keydown", (e) => { const z = live(); if (e.key === "Escape" && z) { z.close(); e.stopPropagation(); } }, true);
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
/** Where an open lands (plans/markdown-viewer.md Slice 6, item 4): one target per open. `line`: a 1-based line of the Raw
 *  view (the row centred; a markdown file opens in Raw for that open); `offset`: a source offset (the block holding it
 *  centred in the Rendered view, the row in Raw); `heading`: a `#fragment` as written, percent-encoded or not, landed
 *  after the first Rendered paint through scrollToFragment (the author's id, then the heading's slug). The viewFile relay
 *  carries it as `at` at every hop and readAt validates what crossed the frame boundary. */
export type At = { line: number } | { offset: number } | { heading: string };
/** The relay's `at`, read where it lands: the message crossed a frame boundary, so its shape is nobody's promise. A
 *  `line` a positive integer, an `offset` a non-negative integer, a `heading` a non-empty string, in that order of
 *  precedence when a message carries more than one; anything else is no target (null), and the file opens at its top. */
export function readAt(x: unknown): At | null {
  if (!x || typeof x !== "object") return null;
  const o = x as Record<string, unknown>;
  if (typeof o.line === "number" && Number.isInteger(o.line) && o.line > 0) return { line: o.line };
  if (typeof o.offset === "number" && Number.isInteger(o.offset) && o.offset >= 0) return { offset: o.offset };
  if (typeof o.heading === "string" && o.heading) return { heading: o.heading };
  return null;
}
/** The reader's place in a file, kept when they leave it (plans/markdown-viewer.md Slice 6, item 3): the top-visible
 *  block's source span (`start`, `end`) and its top edge's offset from the body's top in px (`top`, negative when the
 *  reader is partway into it), whether the body stood at its very top (`atTop`), the view it was read in, the file's
 *  mtime string when it was read (a match means the span is exact), the body's numeric `scrollTop` (the fallback when
 *  the span is no block of the file any more) and `t`, when; and, for a place read in the Rendered view, `folds`, the
 *  ordinals in document order of the `<details>` the reader had OPEN (an author's fold, a `[!type]-` callout, the front
 *  matter; an empty list when every fold was shut; absent when there is nothing to record: a Raw read, whose rows have no
 *  folds, a note with no fold, a record an older store wrote), put back on the reopen before the seat when the file's
 *  mtime is the record's (the same bytes render the same
 *  folds; the review's round 3: a reopen painted every fold as authored, so a fold the reader had open with its summary
 *  at or just above the body's edge came back shut and the passage under it gone); a Raw read of an open that held a
 *  Rendered record's folds for a Rendered paint that never came carries them on at the same mtime (the review's round 5).
 *  No text field, ever: the Files pane
 *  persists this record in localStorage beside its Recent entry, and a block's words there would put file content into
 *  the store. The record is in the file's own terms, as the reader's place across a paint is (reader-place.ts Place). */
export type RememberedPlace = { start: number; end: number; top: number; atTop: boolean; view: "rendered" | "raw"; mtimeNs: string; scrollTop: number; t: number; folds?: number[] };
/** The changed-on-disk bar's words (plans/markdown-viewer.md Slice 6, item 5): raised above the body row when a HEAD on the
 *  window's focus or the document's return to visibility finds the file's mtime moved under a reader whose Comments panel is
 *  closed (with it open, the panel's poll reloads by itself). Two words and a Reload button, in the person's terms. */
export const CHANGED_ON_DISK = "Changed on disk.";
/** The same bar's words when the HEAD answers 404: the file is gone, not changed (the PR review's round 1: the build read a
 *  deletion as a move and said "Changed on disk."). Reload paints the 404 pane, under the one-bar rule as before. */
export const DELETED_ON_DISK = "Deleted on disk.";
/** The kernel's one-word cause on a /file 404 (the PR review's round 2): the header, and the one value that means the file is
 *  gone (an absolute path, as given or `~`-rooted, with no regular file at it). Its other values (`relative`, `unresolved`,
 *  `unreadable`, `detached`, `unviewable`) name a 404 the file may still exist behind, so the bar keeps to CHANGED_ON_DISK for
 *  them, as it does for a 404 with no header at all (a kernel from before the header, a remote kernel without it); `unreadable`
 *  (the PR review's round 3) is an absolute path the kernel could not stat, EACCES on a parent directory, the file possibly
 *  still there. */
export const REASON_HEADER = "X-Romp-Reason";
export const REASON_MISSING = "missing";
/** The notice for a heading target under a plain `hidden` wrapper (plans/markdown-viewer.md Slice 6, item 4; the PR review's
 *  round 1): the section is in the file and has no box to land on, so the open lands at the top and says why, where "No
 *  section named" would be false of it. */
export const HIDDEN_SECTION = "That section is hidden in the rendered view; opened at the top.";
/** The Outline button's label (plans/markdown-viewer.md Slice 6, item 2): the action that lists a rendered note's headings by
 *  depth and lands the picked one at the top of the body. The plan's word, a document viewer's usual one; the guide says
 *  "the file's headings" beside it so the sessions pane's outline is never confused with it (the brief's open question 2). */
export const OUTLINE_LABEL = "Outline";
/** The line a failed render stands under (plans/markdown-viewer.md Slice 7, item 1): when marked, the sanitizer or a DOM pass
 *  of mdBlock throws, or the swap itself does, renderBody paints this sentence and the error's message in the `.fileview-err`
 *  dress as the body's first child (its second, under EMPTY_FILE's line, over an empty file whose render still threw:
 *  renderFellLine), and the file's text as Raw rows under it (codeBlock), so a render that fell shows the text
 *  and says why, where the old catch wrote the source into the Rendered box as one unannounced paragraph. No hint row (the
 *  title bar names the path) and no Download (the text is showing). Without a terminal period so the guide can carry the words;
 *  the line's text is this constant, the message in parentheses, then the period (renderFellLine). */
export const RENDER_FELL = "This file could not be shown as rendered Markdown, so its text is shown as written";
/** The `.fileview-err` line for a render that fell (RENDER_FELL, above), naming what threw: the body's first child above the
 *  Raw rows in both viewers, with one exception, an empty file whose render still threw (a sanitizer or DOM-pass fault over
 *  ""), where item 6's EMPTY_FILE line stands above this one, since its prepend runs after the catch; both sentences true,
 *  the order recorded in the plan's Slice 7 note (item 6, the review's round 6) and not changed. Outside `code.hljs`, so the
 *  anchor map's rawIndex never reads it as a row, and outside `.fileview-md`, which that body does not hold. */
function renderFellLine(msg: string): HTMLElement {
  const why = el("div", "fileview-err");
  why.textContent = RENDER_FELL + " (" + msg + ").";
  return why;
}
/** The sentence marked appends to every message it rethrows (marked 12's `#onError`, wrapping its lexer, the per-call
 *  walkTokens and its parser): a request to report the failure to marked's own tracker, with that URL. A throw at that
 *  stage, one of item 1's four sources, put the sentence and the URL inside romp's own failure line, telling the person to
 *  report a romp file's render failure to marked (the Slice 7 review's round 2). Keyed on the sentence's text alone. */
const MARKED_REPORT_TAIL = /\n?Please report this to https:\/\/github\.com\/markedjs\/marked\.?\s*$/;
/** The message a render catch records (renderFell) and the RENDER_FELL line prints: an Error's message with marked's
 *  appended sentence cut (MARKED_REPORT_TAIL), its name when nothing else is left (`new Error("")`: "Error", as String(err)
 *  answers for one), any other thrown value by its string. A message that carries something else after a newline is kept
 *  whole: the cut is the one sentence, never the first line. */
function fellMessage(err: unknown): string {
  if (!(err instanceof Error)) return String(err);
  return err.message.replace(MARKED_REPORT_TAIL, "") || err.name || "Error";
}
/** The label a figure that failed to load wears beside itself (plans/markdown-viewer.md Slice 7, item 2; armFigureLabels): the
 *  fact, then the authored source and the alt in parentheses when there is one, in one line (`Image failed to load: figs/p95.png
 *  (p95 by day)`), where the browser drew a wordless broken-image glyph or nothing. The img's `error` event carries no status, so
 *  the label names the fact and the source, never a reason, and the viewer makes no second request to learn one (the Comments
 *  panel's poll already HEADs the figure and its card says absent). Without a terminal period so the guide can carry the words. */
export const FIGURE_FAILED = "Image failed to load:";
/** The line an empty file shows in place of its text (plans/markdown-viewer.md Slice 7, item 6). A zero-byte file painted zero
 *  Raw rows or an empty Rendered box and nothing else, a blank pane with Edit shown, so nothing told the reader an empty file from
 *  a paint that had not happened. Now both viewers' text paints put this sentence, in the `.fileview-err` dress, ABOVE the block
 *  the view would paint (the empty `div.fileview-code` or the empty `.fileview-md`): a sibling of that root, never inside
 *  `code.hljs` and never classed `fv-cl`, so the anchor map's rawIndex still sees zero rows over "" and accepts them, and the
 *  Rendered pairing sees no block. `text` stays "" (never null: null means not landed, to the seam and the panel), Edit stays
 *  shown (an empty file is editable; the editor mounts over ""), the Outline button hides (no heading), error() is null (the
 *  content, all none of it, shows) and mode() follows the buttons; a reload that lands bytes repaints without the line. Keyed on
 *  the text the landing applied, never on a byte count or a timer. The one constant of the slice with its own terminal period:
 *  the line shows it alone (contract C5), and the guide carries the words. */
export const EMPTY_FILE = "This file is empty.";
/** The `.fileview-err` line for an empty file (EMPTY_FILE, above): prepended to the body right after the text paint's swap in
 *  both viewers, so it stands above the empty root and outside it. */
function emptyFileLine(): HTMLElement {
  const why = el("div", "fileview-err");
  why.textContent = EMPTY_FILE;
  return why;
}
/** The line for a file whose only bytes are a UTF-8 byte order mark (plans/markdown-viewer.md Slice 7, item 6; the Slice 7
 *  review's round 1). The kernel serves such a file as one U+FEFF and the browser's UTF-8 decode strips that one character
 *  (Chromium 151, the round 4 record: fetch().text(), the Response constructor and TextDecoder agree), so the view's text is ""
 *  exactly as an empty file's is, while the file is not empty: EMPTY_FILE would be untrue of its bytes. The two are told apart
 *  by the answer's byte count, the served body's Content-Length (the kernel's own field; tests/test_kernel_preview.py pins it as
 *  the body's length, 0 for an empty file), since UTF-8 bytes that decode to nothing and number more than zero are exactly the
 *  three of a BOM; the URL viewer's streamed read counts its bytes itself (readTextCapped). The line takes EMPTY_FILE's shape
 *  and place (bomOnlyLine, below); `text` stays "" and Edit stays shown (a save writes the bytes back through the doors' BOM
 *  rule, item 4). An answer with no Content-Length (a kernel from before the header, a proxy that dropped it) gets the empty
 *  file's words, as before. */
export const BOM_ONLY_FILE = "This file holds only a byte order mark.";
/** The `.fileview-err` line for a BOM-only file (BOM_ONLY_FILE, above): the empty file's shape and place. */
function bomOnlyLine(): HTMLElement {
  const why = el("div", "fileview-err");
  why.textContent = BOM_ONLY_FILE;
  return why;
}
/** The pane's sentence over a picture whose bytes would not decode (imgFailed; plans/markdown-viewer.md Slice 7, item 3): the
 *  seam's error() answers it while the pane shows, and the guide's pin reads it here (hoisted from the pane's builder in the
 *  Slice 7 review's round 1). The pane shows it with the path as the hint and the Download offer under it; error() is the
 *  sentence alone. */
export const DECODE_FAILED = "this image failed to decode: it may be mid-write or truncated";
/** The note bar's line over a file the kernel decoded as Latin-1 (plans/markdown-viewer.md Slice 7, item 5): the kernel serves
 *  such a file re-encoded as UTF-8 under `X-Romp-Text-Utf8: 0`, and the Edit gate hides its button on that verdict, which said
 *  nothing to the reader. The line names the fact and its consequence in one sentence. Raised at every text landing whose
 *  answer wears the "0" (notUtf8): before landTarget, so an open's own target notice takes the row under the one-bar rule, and
 *  again after a reload's landing has dropped the changed-on-disk bar; and raised again by a format pick whose paint puts the text
 *  back over a failure pane (pickFormat: the pane's paint drops the line, and the pick's repaint is no landing). Shown alone in
 *  the bar (contract C5). */
export const LATIN1_NOTICE = "This file is not UTF-8 on disk, so it can be read here but not edited: a save would rewrite its bytes as UTF-8.";
/** The refusal Edit gives over pending changes on a file whose text holds a CR anywhere (plans/markdown-viewer.md Slice 7, item
 *  7; trackedRefusal): the editor rewrites the file's line endings as it loads the text. A CRLF and a lone CR are both rewritten
 *  by norm before the mount, as the editor's own document model would rewrite them (CodeMirror's EditorState.create, in its
 *  state package: a string document is split on CRLF, a lone CR or LF alike and its lines are joined back with LF), so both
 *  come back LF. Under pending changes
 *  that is a save no record survives: a CRLF loses a character per ending, so every offset after it moves; a lone CR keeps its
 *  offset but becomes another character, so a record whose text crosses one no longer matches, and the save writes LF where
 *  the file had CR under records anchored to the disk bytes. Before this slice the refusal named CRLF alone and keyed on CRLF
 *  alone, so a CR-only file's pending changes went into an editor that rewrote every ending under them. Shown with the panel's
 *  own refusal after it (contract C5: `CR_REFUSAL + " " + pending.refusal`); the guide carries the words. Without pending
 *  changes the editor mounts as before, over the LF view of the text (norm), and the save door writes the lone CRs back where
 *  the buffer has LF (eolCR, the CRLF restore's shape), so a CR-only file keeps its endings through an edit (the Slice 7
 *  review's round 1; before, a save wrote LF where the file had CR, a data change the reader did not make). */
export const CR_REFUSAL = "The editor rewrites this file's CR or CRLF line endings as it loads the text, and that would move the pending changes.";

// The Raw view's line split (plans/markdown-viewer.md Slice 7, item 7): a CRLF (one ending, tried first), a lone CR or an
// LF each end a row, in wrapNumberedHtml over the highlighted HTML and in codeBlock's gutter count, so the two stay in
// step and no row's text carries a "\r"; the anchor map's rawIndex consumes whichever ending stands between two rows
// (anchor-map.ts) and verifies every row against the source, and scrollToOffset counts a row over the source with the
// same split when the map refuses. Before, both split on "\n" alone: a CR-only file was ONE row (the HTML parser turned
// its CRs into breaks inside it), and a CRLF file's rows ended in a "\r" the parser rewrote. Declared here, above the
// openFileView closure whose scrollToOffset reads it, and not beside the two builders below it (the Slice 7 review's round 1).
const RAW_ROW_SPLIT = /\r\n|\r|\n/;
/** The record of a place read from the body (readPlace), at the file's `mtimeNs` and the body's `scrollTop`: the
 *  place's span, offset, top-of-body flag and view, and nothing of its source, its neighbours or its lines. */
export function rememberedPlaceOf(place: Place, mtimeNs: string, scrollTop: number): RememberedPlace {
  return { start: place.start, end: place.end, top: place.top, atTop: place.atTop, view: place.view, mtimeNs, scrollTop, t: Date.now() };
}
/** The Rendered view's folds as the reader has them: the ordinals, in document order among the body's `<details>`, of those
 *  OPEN (RememberedPlace.folds). Numbers only, never text. null when there is nothing to record: no Rendered body (a Raw
 *  view, the SVG Source view), or a note with no fold, whose record then stays the eight fields it was. */
export function openFoldOrdinals(body: HTMLElement): number[] | null {
  const md = body.querySelector(".fileview-md");
  if (!md) return null;
  const all = Array.from(md.querySelectorAll("details"));
  if (!all.length) return null;
  const out: number[] = [];
  all.forEach((d, i) => { if (d.hasAttribute("open")) out.push(i); });
  return out;
}
/** The record back as a Place over `source`, the file's text as it is NOW, for seatPlaceOutcome to seat: the block of
 *  `source` that starts where the remembered block started (the same block, whatever an edit inside or below it did to
 *  its end; sourceBlockSpans), with the record's offset and flag, a `height` of 0 (unknown: the box was not kept) and
 *  no neighbours. null when no block of `source` starts there (text inserted or removed above the block moved it, and
 *  the old source is not kept to follow it through the edit as a reload's place is): the caller falls to the record's
 *  numeric scrollTop. */
export function placeFromRemembered(rec: RememberedPlace, source: string): Place | null {
  const spans = sourceBlockSpans(source);
  const b = blockIndexAt(spans, rec.start);
  if (b < 0 || spans[b].start !== rec.start) return null;
  return { source, view: rec.view, start: spans[b].start, end: spans[b].end, top: rec.top, height: 0, atTop: rec.atTop, prev: null, next: null };
}
// The memory: one record per file for the page's lifetime, keyed by the path as openFileView receives it (placeKey, below:
// the same bytes are the same file for every session that names an absolute path; a relative path, which the kernel resolves
// against the session's cwd, carries the session in its key), written at the moments the reader leaves a file
// (closeFileView, the replace path of either open, the window's pagehide) and read at the next open of the path with
// no target. The Files pane persists what it hears through `onLeave` (initFileView's host) in its Recent entry and
// hands it back as `opts.place`; the chat modal and the feed viewer persist nothing, and this map covers a switch
// between files there. `leaveLive` is the open viewer's write, registered as onKeyLive and mediaUrlLive are so both
// exits reach it (runLeave); the window's pagehide listener (initFileView) runs it without retiring it, since the page
// may come back from the cache with the viewer up.
const rememberedPlaces = new Map<string, RememberedPlace>();
let leaveHost: ((path: string, sid: string | null, rec: RememberedPlace) => void) | null = null;
let leaveLive: (() => void) | null = null;
function runLeave(): void { const f = leaveLive; leaveLive = null; if (f) f(); }
/** Of two records for one path, the one read later (the pane's entry is per path and session, the map per path, so a
 *  Recent row's record can be older than the map's for the same file); null when there is neither. */
function newerPlace(a: RememberedPlace | null | undefined, b: RememberedPlace | null | undefined): RememberedPlace | null {
  if (!a) return b ?? null;
  if (!b) return a;
  return b.t > a.t ? b : a;
}
/** The memory's key for a file: the path as openFileView receives it, and for a RELATIVE path the session too, since the kernel
 *  resolves such a path against the SESSION's cwd (_resolve_open_path: neither `/`- nor `~`-rooted), so `docs/report.md` in two
 *  sessions on two repos names two files (the review's round 2: the second session's file, never read, opened at the first's
 *  place). An absolute or `~` path is the key alone for a session of THIS kernel: the same bytes are the same file for every
 *  such session that names it. A session attached from another kernel (a `host:` sid, hostOf, whose read fileUrl routes to
 *  `/remote/<host>/file` and that kernel's disk) reads another file under the same spelling, so its key carries the host (the
 *  PR review's round 1: the review's round 6 had recorded two files under one key, a reopen of either seating the other's later
 *  record and either leave overwriting the key for both; correctness over sharing). A relative path's key already tells the
 *  kernels apart, the sid it carries being the prefixed one. */
export function placeKey(path: string, sid: string | null | undefined): string {
  if (!/^[/~]/.test(path)) return path + "\u0000" + (sid ?? "");
  const host = hostOf(sid ?? "");
  return host ? host + "\u0000" + path : path;
}
// The keyboard rule's reach into a sibling frame (plans/markdown-viewer.md Slice 6, item 1: the body takes the keyboard unless
// the composer holds it). In the Files iframe the chat composer is in another document, and this document's activeElement is
// its own body whenever the page's focus is elsewhere, so the same-document gate saw nothing to yield to and body.focus()
// pulled the page's focus into this frame, out of a box being typed in (the review's round 2: a relayed open, a Reload's
// landing and a Save's ack each cut a sentence). So when this document does not hold the focus, the focused frame is read
// through the top window down to its own active element, and a typing target there keeps the keyboard; any other holder
// (the chat's body after a plain click) yields as the document's body does. Frames the read cannot see (another origin, a
// host with no top) or a read that throws take the keyboard as before.
const NON_TEXT_INPUTS = new Set(["button", "checkbox", "radio", "submit", "reset", "file", "range", "color", "image", "hidden"]);
function isTypingTarget(a: Element): boolean {
  if (a.localName === "textarea" || a.localName === "select") return true;   // type-ahead in a dropdown is typing too (render.ts's isTypingTarget reads the same; the review's round 3)
  if (a.localName === "input") return !NON_TEXT_INPUTS.has((a.getAttribute("type") || "text").toLowerCase());
  return (a as HTMLElement).isContentEditable === true;
}
function typingInPeerFrame(): boolean {
  try {
    if (typeof document.hasFocus !== "function" || document.hasFocus()) return false;
    const top = window.top;
    if (!top || top === window) return false;
    let a: Element | null = top.document.activeElement;
    for (let hops = 0; a && a.localName === "iframe" && hops < 16; hops++) {
      const inner = (a as HTMLIFrameElement).contentDocument;
      if (!inner || inner === document) return false;
      a = inner.activeElement;
    }
    return a !== null && isTypingTarget(a);
  } catch { return false; }
}
/** Whether `a` wears the focus ring (`:focus-visible`): no holder, or the document's body, wears none, and a matches() without
 *  the selector (the test stand-ins) reads none. Read off a holder before a hand-over, it names the ring for the body
 *  (openFileView's takeKeyboard). Module-level since the review's round 4: the replace path reads it before the old card goes. */
function ringOf(a: Element | null): boolean {
  if (a === null || a === document.body) return false;
  try { return a.matches(":focus-visible"); } catch { return false; }
}
/** The ring of the keyboard's holder INSIDE `old` (the viewer a replace-open is about to remove: a Tab-focused path link in the
 *  note, activated by Enter), read before the removal for the landing's hand-over; null when the holder is elsewhere or there
 *  is none, so the landing reads its own (the review's round 4: the link was gone at the landing and the new body got no ring). */
function ringInOld(old: Element | null): boolean | null {
  const a = document.activeElement;
  return old && a && old.contains(a) ? ringOf(a) : null;
}
// The last input's kind, for a hand-over with NO holder to read the ring from (the review's round 4). Chromium's :focus-visible
// heuristic for a script focus is "a key was pressed since the last mouse press", which is right, plus "nothing focusable was
// last pressed", the misfire round 3 closed by naming the ring off the holder and passing none when there was none. That also
// cost the ring at a keyboard-driven open whose opener is no element, or is gone at the landing: Enter on the file browser's
// active row (the rows are not focusable, the document's body holds the keyboard throughout) and Enter on a Tab-focused path
// link inside the note (the replace path removes the old viewer with the link before the fetch lands; ringInOld reads that one).
// So the document records the kind of its last press, a key that is not a modifier alone or a pointer, on the two events
// themselves, and a hand-over with no holder passes that while this document holds the page's focus (a relayed open's click was
// in another frame, which this document's record knows nothing of, and the frame's own record is stale then): the browser's
// rule for the case, read from the gestures, without its misfire. Installed once by initFileView beside the module's other
// document listeners; a document that never called it, or one whose last press was a pointer, passes none, as round 3 did.
let lastInputKey = false;
const MODIFIER_KEYS = new Set(["Shift", "Control", "Alt", "Meta", "AltGraph", "CapsLock", "Fn", "NumLock", "ScrollLock"]);
function watchInputKind(): void {
  document.addEventListener("keydown", (e: KeyboardEvent) => { if (!MODIFIER_KEYS.has(e.key)) lastInputKey = true; }, true);
  document.addEventListener("pointerdown", () => { lastInputKey = false; }, true);
}
/** The ring for a hand-over with no holder: the last press in this document was a key, and this document holds the page's focus. */
function ringWithNoHolder(): boolean {
  if (!lastInputKey) return false;
  try { return typeof document.hasFocus !== "function" || document.hasFocus(); } catch { return false; }
}
// Where a FILE LINK inside a shown file opens (file-view-links.ts marks them; the body's delegate in openFileView
// reads the click): this document's own open when the host registered one (initFileView's `openFile`: the Files
// pane's openHere, so the file enters its Recent list and names its session), else the shared viewer in place,
// replacing the file that carried the link. The same document either way: the person is reading here. The link's
// target rides as `at` (the link's data-line as `{ line }`, its data-frag as `{ heading }`; null for a bare path).
let openLinkedFile: (path: string, sid: string | null, at: At | null) => void =
  (path, sid, at) => { openFileView(path, sid, { at }); };
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
// ONE live changed-on-disk probe at a time (plans/markdown-viewer.md Slice 6, item 5): the open viewer's window `focus` and
// document `visibilitychange` listeners, registered here so BOTH exits remove them (dropProbe), as onKeyLive is: a replaced
// viewer's probe must not HEAD a file that no longer shows or raise a bar in a card that is gone.
let probeLive: (() => void) | null = null;
function dropProbe(): void {
  if (probeLive) { const f = probeLive; probeLive = null; f(); }
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

/** Why the seam's onRendered fired: "paint", the body's nodes are new; "reflow", the same nodes at a new width or text size
 *  (a hook keeps its wraps and re-measures). */
export type FileViewRenderWhy = "paint" | "reflow";

// ── the body's content width, for the sheets ──────────────────────────────────────────────────────
// A table of the rendered document's own (a direct child of the .fileview-md root) may grow past the prose column, up to
// the body's content width less the root's inset (`.fileview-md > table` in both sheets reads --fv-body-w; the rule there
// says how). The value is the body's content width as its ResizeObserver reports it (the layout's own event, never a
// timer; a scrollbar's width is taken), written on EACH TOP-LEVEL TABLE rather than on the body it describes: the property
// is registered non-inherited (`@property --fv-body-w { inherits: false }`), so a write restyles the tables alone and not
// every node under the body, as a write to an inherited property on the body would. mdBlock rebuilds the root on every
// paint and no report follows a paint, so renderBody stamps the fresh tables itself (the returned function)
// with the width last reported; before the first report the property is unset and the sheet's fallback holds (the cap is
// the column). Absent ResizeObserver (a stand-in, an old engine) nothing is written and the fallback holds. One watch at a
// time: the next open, or the close, drops the last. An optional `onWidth` runs after each changed report with the new
// width: the local viewer's reflow, which re-places the comments panel's cards once per animation frame, hangs on it; the
// URL viewer passes none.
let dropWidthWatch: () => void = () => { /* no watch up */ };
function watchBodyWidth(body: HTMLElement, onWidth?: (width: number) => void): () => void {
  dropWidthWatch();
  let width = -1;                                      // the body's content width as last reported, -1 before the first report
  const stamp = (): void => {
    if (width < 0) return;
    const md = body.querySelector(".fileview-md");
    if (!md) return;
    for (const n of Array.from(md.children)) if (n.tagName === "TABLE") (n as HTMLElement).style.setProperty("--fv-body-w", width + "px");
  };
  if (typeof ResizeObserver === "function") {
    const ro = new ResizeObserver((entries) => {
      const w = entries.length ? entries[entries.length - 1].contentRect.width : body.clientWidth;
      if (w === width) return;
      width = w;
      stamp();
      if (onWidth) onWidth(w);
    });
    ro.observe(body);
    dropWidthWatch = () => { ro.disconnect(); dropWidthWatch = () => { /* dropped */ }; };
  }
  return stamp;
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
  /** the text the current view shows (the SVG Source view's decoded XML included); null until the fetch lands, and for media.
   *  After a failed reload it still answers the last landing's text, and error() tells the pane the body shows in its place.
   *  An empty file answers "" (never null: the body shows the EMPTY_FILE line above its empty root, and that is the content) */
  text(): string | null;
  /** the file's mtime at load, nanoseconds AS A STRING (the save fence's own value) */
  mtimeNs(): string;
  /** the words of the pane the body shows IN PLACE of the file: a fetch refused or failed (the kernel's 404, 413 or 415 body, a
   *  network failure's message: the `msg` the catch paints), or a picture that failed to decode (that pane's own sentence,
   *  without its hint and its Download button); null while a text or media view shows, the loader included, and null over the
   *  Raw rows a failed render falls back to (mode() answers "raw" for that paint: the rows are the content). Closure state
   *  (`viewError`) set at the two pane paints and cleared at every content paint (the text paint once its swap stands, so a
   *  fallback swap that throws leaves a standing pane's words; the media arm before whenShown, the SVG Source view, the
   *  editor's entry), never read from the body; text() and mtimeNs() keep answering the last landing's */
  error(): string | null;
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
  /** runs after every paint of the body, with `why` saying which kind: a text body at once (open, view switch, reload), a media body once it shows —
   *  an image after its load event (at once when it was already complete), a PDF frame at once (whenShown), a PDF's
   *  pages once page 1 is drawn and then again after every page the chunk draws (so an overlay can attach to each) and
   *  after every later page it could not draw (the chunk removes that page's canvas and puts its notice in the shell; the
   *  overlay leaves with the canvas on this paint, and the card says the page did not render). A Rendered body's figures
   *  are in the DOM by then with their own loads still pending. The panel re-runs its paint pass.
   *  A failure pane is a paint too (plans/markdown-viewer.md Slice 7, item 3): the fetch chain's catch (a refused or failed
   *  fetch, a reload's or a first open's, text() null then) and a picture's decode failure (imgFailed) fire the hooks after
   *  their swap, with error() the pane's words, so a hook waiting on a reload hears it fail at the paint and never at a deadline.
   *  Also once at Edit, as the editor takes the body (Slice 5), with editing() true: the panel's paint pass stands down
   *  then, and its cards, which read editing() at render time, take their edit-mode state from this render (the panel's
   *  own begin() ran before the flip, so its render could not). No other paint while the editor holds the body; the exit's
   *  repaint hands the read-mode state back.
   *  Every call above is a PAINT (`why` "paint", the default a caller passing nothing gets): the body's nodes are new, and a
   *  hook that wraps or measures them starts over.
   *  Also after a text view REFLOWS with its text unchanged (`why` "reflow"): a text-size step (the A− / A+ buttons, the
   *  wheel) and a change of the body's width (the pane resized, the aside opening or closing; a ResizeObserver on the body,
   *  so the event is the layout's own, never a timer, folded to one call per animation frame and none when the width is
   *  back where the last call left it). The nodes stand: a highlight wrapped into the text is still around the same
   *  characters, so a hook keeps its wraps and re-MEASURES only (the panel re-places its cards; before 2026-09-09 it ran
   *  its whole paint pass, unwrapping and re-wrapping every mark, once per frame of a pane drag, which at a big reviewed
   *  file blocked the page for seconds a frame). A media body's own observers (the figure layer's, the PDF chunk's)
   *  already cover theirs, and the editor lays out its own text, so neither reflow fires for those */
  onRendered(cb: (why?: FileViewRenderWhy) => void): void;
  /** runs on mouseup/touchend with a non-collapsed selection inside the body, BEFORE the quote-chip gate, so it works with no chat pane.
   *  A selection made or changed from the keyboard reaches no mouseup and runs no hook here: the comments panel listens to the
   *  document's selectionchange itself for those (file-comments.ts onSelectionChange), so the chip's per-gesture fetch never runs per keystroke */
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
// One unit in the action row: the link, when the OWNING kernel's lazy fileGitLink ask resolves to a URL,
// and NOTHING otherwise (T367, the user 2026-09-12, who wanted the greyed link and its explanation gone
// from a file outside a repository: the 2026-09-05 always-fill-the-slot rule gave way to the tidier bar).
// A real URL is an anchor — the browser owns the new tab — with the full URL as its tooltip; a URL whose
// branch is not on origin stays an anchor, dashed, with the kernel's note in the tooltip and aria-label,
// since GitHub 404s it until the push. No URL (no repo, uncommitted, no GitHub origin, an older kernel)
// leaves the unit hidden: the verdict still rides the reply, it is just not rowed. The unit stays in the
// row hidden while the check is out, so the answer lands in place; aria-busy marks the pending unit in the
// DOM (the tests read it), and hidden it sits outside the accessibility tree, so no wait is announced for a
// link nobody sees yet. One question
// per open, reqId-guarded; a socket drop while it is out is the one thing that loses the reply, and the
// shim's reconnect event re-asks (initFileView), so the wait never outlives the socket. Exported for the
// DOM-shape test.
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
    unit.hidden = true;
    unit.setAttribute("aria-busy", "true");
    const reqId = ++gitSeq;
    const ask = () => post({ type: "fileGitLink", path, sid: sid || undefined, reqId });
    gitHooks = {
      reqId,
      ask,
      apply: (url, reason) => {
        unit.removeAttribute("aria-busy");
        if (!url) { unit.replaceChildren(); unit.hidden = true; return; }   // nothing to link to: nothing shown
        const a = el("a", "fileview-btn") as HTMLAnchorElement;
        a.href = url; a.target = "_blank"; a.rel = "noopener";
        a.textContent = "GitHub ↗";
        a.title = reason ? url + "\n" + reason : url;       // the full URL one hover away, and the note with it
        a.setAttribute("aria-label", reason ? "GitHub: " + reason : "GitHub");
        if (reason) a.classList.add("fileview-gh-note");    // the branch is not on origin yet: dashed
        unit.replaceChildren(a);
        unit.hidden = false;
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
  runLeave();                                          // the reader's place, remembered for the next open of the path (RememberedPlace, above), read while the body stands
  editHooks = null;
  gitHooks = null;                                     // a reply landing after the close decorates nothing
  dropOnKey();                                         // the closing viewer's handler leaves with it
  dropProbe();                                         // …and its changed-on-disk probe (the window and document listeners)
  if (zoomOpen) { zoomOpen.close(); zoomOpen = null; }   // the text-size flyout's reference leaves with the viewer (review: a keyboard close kept it, and the next viewer's first Escape was swallowed)
  dropMediaUrl();                                      // an image/PDF view's bytes leave with the viewer
  dropWidthWatch();                                    // …and the body's width watch (watchBodyWidth)
  dropUrlRead();                                       // …and a URL view's in-flight read is cancelled
  runCloseHooks();                                     // the panel's poll and listeners leave with the viewer
  wrap.remove();
  document.body.classList.remove("fileview-open");
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
 *  way, so a modified click on a PDF means the tab whichever document hosts the browser. `at`: where the open lands (At:
 *  a todo link's line or heading, render.ts openPath; Slice 6 of plans/markdown-viewer.md), handed to whichever opener
 *  takes the plain click; absent, the file's top. */
export function openFileClick(ev: MouseEvent | KeyboardEvent | null | undefined, path: string, sid?: string | null,
                              open?: (path: string, sid: string | null, at: At | null) => void, at?: At | null): void {
  if (wantsOwnTab(ev) && openPdfTab(path, sid ?? null)) return;
  if (open) open(path, sid ?? null, at ?? null); else openFileView(path, sid, { at: at ?? null });
}

/** Show `path` in a modal over this pane. Re-opening replaces whatever is up — never stacks.
 *  Returns whether the open happened: false when the dirty-edit guard kept the previous viewer, so a caller
 *  that records the open (the Files pane's recent list) records only real ones.
 *  `opts.todoId`: the user todo the file was opened from (the Waiting-on-you pane's detail link).
 *  `opts.at`: where the open lands (At; plans/markdown-viewer.md Slice 6, item 4). `{ line }` (a `path:12` link in another
 *  file, file-view-links.ts, or after a path in a todo, path-links.ts): the code view scrolls its row into view once the
 *  text lands, and a markdown file opens in its Raw view for THIS open (the Rendered view has no rows) without touching
 *  the saved preference. `{ heading }` (a `#fragment`: `[see](report.md#results)` in a sibling file, `docs/report.md#results`
 *  in a todo): landed after the first rendered paint, the notice bar saying so when the note has no such section.
 *  `{ offset }` (a source offset): the block holding it centred in the Rendered view, the row in Raw. The viewFile relay
 *  carries it as `at` (initFileView, readAt). The former `opts.line` and `opts.frag` are two of its arms: replaced, not
 *  aliased, so there is one shape for one thing.
 *  `opts.place`: the reader's place in this file when they last left it, as the host persisted it (RememberedPlace; the
 *  Files pane's Recent entry, plans/markdown-viewer.md Slice 6, item 3), seated on the first text paint; the viewer's
 *  own memory of the path is read too, and the later of the two wins. An `at` lands where it points and ignores both. */
export function openFileView(path: string, sid?: string | null, opts?: { todoId?: string | null; at?: At | null; place?: RememberedPlace | null }): boolean {
  // The replace path bypasses closeFileView, so it needs the same dirty ask: opening file B over an
  // edited-but-unsaved file A must not silently eat A's buffer.
  if (document.getElementById("romp-fileview") && closeGuard && !closeGuard()) return false;
  closeGuard = null;
  closeAsks = [];
  const priorRing = ringInOld(document.getElementById("romp-fileview"));   // the ring of a holder inside the old card (a Tab-focused path link activated by Enter), read before anything below moves the focus or removes the card, for the landing's hand-over (takeKeyboard)
  runLeave();                                          // …and the same leave write: the old file's place, before its body goes
  editHooks = null;
  gitHooks = null;                                     // the replace path skips closeFileView — same drop
  dropOnKey();                                         // …and the same for the old viewer's Escape handler
  dropProbe();                                         // …and its changed-on-disk probe: the new open arms its own
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
  // The open's target (`at`, one of At: a line, a source offset or a heading; plans/markdown-viewer.md Slice 6, item 4).
  // A heading (a sibling link's `#fragment`, `[see](report.md#results)`: data-frag on the path link, file-view-links.ts
  // linkMarkdownAnchors; a todo's `docs/report.md#results` through the relay) lands after the FIRST rendered paint, once,
  // through scrollToFragment; a Raw view of a markdown file has no ids to land on, so the landing waits for the Rendered
  // toggle rather than being spent (review find on #958, 2026-09-07), while a file that is not markdown has no Rendered
  // toggle to wait for and its first text paint spends the heading (the review's round 2: `src/app.py#l12`, the section
  // spelling of a line slip, opened the file silently at its top). A heading the file does not have lands nowhere and says
  // so in the notice bar (CLAUDE.md, fail loudly: a silent open at the top would read as the file's truth). The line and
  // the offset are spent on the first text landing instead (pendingLine and pendingOffset, with the fetch below).
  const at: At | null = opts?.at ?? null;
  let pendingHeading: string | null = at !== null && "heading" in at && at.heading ? at.heading : null;
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
  let renderFell: string | null = null;       // the message of the throw the last text paint fell on (renderBody's catch: the RENDER_FELL line over Raw rows); null once a paint stands, so mode() answers "raw" over those rows and "rendered" again after the Rendered click's retry
  let viewError: string | null = null;        // the seam's error(): the words of the pane the body shows in place of the file, set where the two panes paint (the fetch chain's catch, imgFailed) and cleared where content paints (the text paint once its swap stands, the media arm, the editor's entry); never read off the body (plans/markdown-viewer.md Slice 7, item 3)
  let mtimeNs = "";                           // the file's mtime at load, NANOSECONDS AS A STRING —
  //   saveFile's conflict floor (ns because whole seconds let a same-second agent write slip the
  //   guard; a string because ~1.7e18 exceeds JS's safe-integer range and a number would round)
  let isText = false;                         // the kernel's verdicts (text/plain AND faithful UTF-8)
  let textBytes: number | null = null;        // the last landing's body byte count, the answer's Content-Length (null when absent): read by the text paint for one question the decoded text cannot answer, whether a text that reads "" was a BOM alone (BOM_ONLY_FILE; plans/markdown-viewer.md Slice 7, item 6)
  let notUtf8 = false;                        // text/plain whose X-Romp-Text-Utf8 is exactly "0": the kernel decoded the bytes as Latin-1, so the text landing raises LATIN1_NOTICE (plans/markdown-viewer.md Slice 7, item 5). Its own flag, never !isText: an image or a PDF carries no header at all, and an old kernel that sends none leaves isText true (Edit off through !mtimeNs)
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
  let eolCR = false;                          // a CR-only file (a lone CR at every ending, no LF anywhere): the editor's document model and the
  //   textarea alike read a lone CR as a line break and give it back as LF, so the save door writes the CR back where the buffer has
  //   LF, as it does a CRLF (Slice 7 of plans/markdown-viewer.md, item 7; the review's round 1: before, an edited CR-only file saved
  //   with every ending rewritten, a data change the reader did not make). Exact by construction: with no LF in the file, every LF
  //   the editor gives back came from a CR or a typed line break. A file mixing CR and LF has no one ending to restore.
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
  // T367 (the user 2026-09-12): the row reads as GROUPS. The view group holds the Rendered|Raw pair (one
  // segmented control), the SVG Source toggle and the text-size glyph; the file group holds edit (and Save
  // and Cancel while editing), the GitHub link when it resolves, download and copy path; the close cross
  // stands alone at the end. Word buttons became glyphs with their words in the title and aria-label.
  const viewGroup = el("span", "fileview-group fileview-group-view");
  const fileGroup = el("span", "fileview-group fileview-group-file");
  // The format pick, from the bar's Rendered and Raw buttons and from the seam's setMode alike (the Comments panel switches to
  // Raw through it for a refused comment and for a Reveal): the saved choice, the paint, and one repair the paint does not make
  // itself. Over a failure pane (a reload refused after a deletion or a growth past the cap; error() the pane's words) the paint
  // puts the last landing's text back in the body, the pre-existing repaint (plans/markdown-viewer.md Slice 7, item 3), and on a
  // file the kernel decoded as Latin-1 (notUtf8) that text stood with Edit off and, since the pane's paint drops the line that
  // says why (dropLatin1Line, the review's round 2), nothing saying so until the next "0" landing (the review's round 3). So a
  // pick whose paint replaced a pane raises the line again, when no other notice took the row meanwhile (a re-armed
  // changed-on-disk bar, say, whose Reload answers the person's own click and stands). Keyed on the pane the paint replaced and
  // the landing's header, never on the body's text or a timer; a pick over content raises nothing (the line stands from the
  // landing, or another notice does), and a landing raises its own line below. The URL viewer has no such pick: no header.
  const pickFormat = (mode: "rendered" | "raw"): void => {
    const overPane = viewError !== null;      // read before the paint: the paint clears the record once its swap stands
    fmt.md = mode; saveFmt(fmt); renderBody();
    if (overPane && notUtf8 && viewError === null && note === null) noteBar(LATIN1_NOTICE);
  };
  const segBtns: Array<["rendered" | "raw", HTMLButtonElement]> = [];
  if (isMd) {
    const seg = el("span", "fileview-seg");                 // the pair joined: one hairline between, the outer corners rounded
    seg.setAttribute("role", "group"); seg.setAttribute("aria-label", "Markdown view");
    for (const mode of ["rendered", "raw"] as const) {
      const b = el("button", "fileview-btn") as HTMLButtonElement;
      b.type = "button";
      b.textContent = mode === "rendered" ? "Rendered" : "Raw";
      b.title = mode === "rendered" ? "The prose the markdown means" : "The file's actual bytes";
      b.addEventListener("click", () => { pickFormat(mode); takeKeyboard(); });   // the paint (pickFormat), then the keyboard (takeKeyboard: the button holds it)
      segBtns.push([mode, b]);
      seg.appendChild(b);
    }
    viewGroup.appendChild(seg);
  }
  // ── the Outline (plans/markdown-viewer.md Slice 6, item 2) ── A rendered note's headings, listed so a section is one pick
  // away where the audit found no list at all ("No heading ids, no outline"). The button shows over a markdown file's
  // Rendered view once its paint holds a heading (syncOutline, from renderBody) and hides otherwise: in Raw (the rows carry
  // no heading elements, and the toggle is one click away), in the editor, and while the loader holds the body; a
  // non-markdown file never gets it, like the toggles. The list is read off the Rendered DOM when the popover OPENS, never
  // per paint: every h1 to h6 under .fileview-md in document order, the elements mintHeadingIds gave ids (a heading inside
  // a fold, open or closed, a quote or a list item is listed as the DOM holds it; the front-matter block is a details with
  // no heading and mints none), each row the heading's text on one line, indented by its depth under the shallowest
  // heading of the note (a note that starts at h2 indents nothing for its h2s), with the heading's id. A 500-heading note
  // costs one query and 500 rows when the reader asks, nothing at a paint. The popover is a pane-local dropdown under the
  // button in the menu vocabulary (the sheets' .fileview-outline rules read the --menu-* tokens; ui/CLAUDE.md), a child of
  // the card positioned from the button's box, capped at the body's height less a margin and the card's width less a
  // margin, scrolling within itself. It takes the focus at the open, with the section under the reader's eye current (the
  // last heading whose top sits at or above the body's top edge, less the heading's scroll margin, the gap a landing leaves
  // above it, so a heading a pick just put at the top is the section; a heading with no box, inside a shut fold, is passed
  // over, and with none at or above the edge the first row is current; the PR review's round 1: the build started at the
  // first row, so a reader forty sections in opened the list at the title every time), and closes on a pick, on Escape
  // (stopped here, so the document's onKey below never sees it and the viewer stays up; the keyboard goes back on the
  // Outline button, as a menu button's Escape puts it, which its aria-haspopup="menu" announces; the PR review's round 1:
  // the build handed it to the body), on a press outside it (a capture-phase pointerdown on the document; a press on the
  // button is the toggle's own and not "outside"), on the keyboard leaving it (focusout to anything but the button), on a
  // window resize (the button's box moved), on every paint of the body (renderBody: the view switch, a reload; the rows
  // were read off a DOM that is going) and with the viewer (closeHooks). Keys on the popover: ArrowDown and ArrowUp move
  // the current row, Home and End jump, Enter and Space pick it, Escape closes; the current row is kept in the popover's
  // own view by its scrollTop, never scrollIntoView, which would reach the body and the page. The pick lands the heading
  // through the fragment landing's own steps (scrollToFragment: revealFragmentTarget opens the folds above it, then
  // scrollIntoView block "start", so the heading's top sits at the body's edge less its scroll margin, where a `#` link
  // puts it), and the keyboard returns to the body (takeKeyboard: the popover's removal left it on the document's body),
  // so PageDown reads on from the section. While it is up the button wears the bar's selected dress, `.on`, the class the
  // Rendered/Raw toggle wears when pressed (the PR review's round 1: the build gave the button a rule of its own on
  // aria-expanded, a near-twin of that dress without its weight and its hover). The popover is a child of the card, and
  // the card is the surface the landing's press hold reads (pressHold(box), below), so a fetch landing while a row is
  // pressed waits for the release and the pick lands (the PR review's round 1: held on the body alone, the landing's paint
  // ran closeOutline and removed the pressed row before the mouseup, and the click was lost; ui/CLAUDE.md, click-safe).
  // Nothing is stored; nothing is read from the source; the popover is built and discarded per open of it.
  const outlineBtn = el("button", "fileview-btn fileview-outline-btn") as HTMLButtonElement;
  outlineBtn.type = "button"; outlineBtn.textContent = OUTLINE_LABEL; outlineBtn.title = "The file's headings";
  outlineBtn.setAttribute("aria-haspopup", "menu"); outlineBtn.setAttribute("aria-expanded", "false");
  outlineBtn.hidden = true;                            // shown by the first Rendered paint that holds a heading (syncOutline)
  if (isMd) viewGroup.appendChild(outlineBtn);           // a view control: it rides the view group beside the Rendered|Raw pair (T367's grouping)
  let outline: HTMLElement | null = null;              // the open popover
  let dropOutline: (() => void) | null = null;         // its document and window listeners, removed with it
  const headingsOf = (): HTMLElement[] => {
    const md = body.querySelector(".fileview-md");
    // a heading inside a wrapper carrying a plain `hidden` (an author's stashed section: the sanitizer keeps the attribute, and the
    // fragment landing lifts `hidden="until-found"` alone, as the browser's own does) has no box to land on, so it has no row (the
    // review's round 3: the row was offered, and its pick closed the popover and moved nothing, with no word why)
    return md ? (Array.from(md.querySelectorAll("h1, h2, h3, h4, h5, h6")) as HTMLElement[]).filter((h) => !underHidden(h, md)) : [];
  };
  // The popover takes the focus at its open, so a closer that removes it while it holds the keyboard would leave the keyboard
  // on the document's body by the browser's fixup, where PageDown, Space and the arrows scroll nothing until a click and the
  // chat's bare-area Enter reaches the composer behind the modal (the review's round 1: the window resize closer, a zoom; the
  // paint closer, the Comments panel's poll reloading the file). So the removal hands the keyboard to the body when the
  // popover held it, or when the Outline button did (the toggle's second click focused the button, and the popover's own
  // focusout stood aside for it), through takeKeyboard's gate as the pick does; a keyboard held anywhere else is left where
  // the reader put it. `handOver` false: the focusout closer, after the keyboard has moved to another element (a Tab out, a
  // press in the aside): that element keeps it; and Escape and Tab, which put the keyboard on the Outline button themselves.
  const closeOutlineKeeping = (handOver: boolean): void => {
    if (!outline) return;
    const pop = outline; outline = null;
    if (dropOutline) { const f = dropOutline; dropOutline = null; f(); }
    const a = document.activeElement;
    const held = handOver && a !== null && (pop.contains(a) || a === outlineBtn);
    const ring = held && ringOf(a);              // read before the removal drops the focus to the document's body (takeKeyboard, the ring)
    pop.remove();
    outlineBtn.setAttribute("aria-expanded", "false"); outlineBtn.classList.remove("on");
    if (held) takeKeyboard(ring);
  };
  const closeOutline = (): void => closeOutlineKeeping(true);
  const syncOutline = (): void => {
    outlineBtn.hidden = editing || ctx.mode() !== "rendered" || headingsOf().length === 0;
    viewGroup.hidden = !(segBtns.some(([, b]) => !b.hidden) || !textSize.trigger.hidden || !srcBtn.hidden || !outlineBtn.hidden);   // the group follows the button it holds: renderBody's bar sync ran before this paint decided the Outline (T367's all-hidden rule)
  };
  const openOutline = (): void => {
    const heads = headingsOf();
    if (!heads.length) return;
    const pop = el("div", "fileview-outline");
    pop.setAttribute("role", "menu"); pop.setAttribute("aria-label", "The file's headings"); pop.tabIndex = -1;
    const shallowest = Math.min(...heads.map((h) => Number(h.tagName[1])));
    const seq = ++outlineOpens;                        // the rows' ids, unique per open of the popover (aria-activedescendant names one)
    const rows = heads.map((h, i) => {
      const r = el("div", "fileview-outline-row");
      r.setAttribute("role", "menuitem"); r.dataset.id = h.id; r.id = "fileview-outline-" + seq + "-" + i;
      r.style.setProperty("--fv-ol-depth", String(Number(h.tagName[1]) - shallowest));
      // the heading's words with each picture read as its alt text where it stands (`## ![Figure 3: latency](figs/l.png) (detail)`
      // reads "Figure 3: latency (detail)", the name a screen reader gives the heading; the review's round 1 read the alt for a
      // heading with no text at all, an 8 px padding-only strip before it, and round 3 for one with text beside the picture,
      // whose row had dropped the figure's name); KaTeX's strut is a U+200B; with no words and no alt, one non-breaking space
      // keeps the row's height so the list's rhythm shows a heading is there
      const words = headingWords(h).replace(/\u200b/g, "").replace(/\s+/g, " ").trim();
      r.textContent = words || "\u00a0"; r.title = words;
      pop.appendChild(r);
      return r;
    });
    // the section under the reader's eye (the header): the last heading with a box whose top is at or above the body's top edge, the
    // heading's scroll margin allowed (read once: every heading wears the sheets' one rule; a stand-in without getComputedStyle reads 0)
    const underEye = (): number => {
      const edge = body.getBoundingClientRect().top;
      let at = 0, margin = -1;
      heads.forEach((h, i) => {
        const r = h.getBoundingClientRect();
        if (r.height === 0 && r.width === 0) return;                 // no box: inside a shut fold
        if (margin < 0) margin = typeof getComputedStyle === "function" ? parseFloat(getComputedStyle(h).scrollMarginTop) || 0 : 0;
        if (r.top <= edge + margin + 0.5) at = i;
      });
      return at;
    };
    let cur = -1;
    const setCur = (i: number): void => {
      if (cur >= 0) rows[cur].classList.remove("current");
      cur = Math.max(0, Math.min(i, rows.length - 1));
      const r = rows[cur]; r.classList.add("current");
      pop.setAttribute("aria-activedescendant", r.id);   // the current row, for assistive technology: the popover holds the focus and the rows never do (the review's round 3: the menu opened and every move and the pick were silent)
      if (r.offsetTop < pop.scrollTop) pop.scrollTop = r.offsetTop;
      else if (r.offsetTop + r.offsetHeight > pop.scrollTop + pop.clientHeight) pop.scrollTop = r.offsetTop + r.offsetHeight - pop.clientHeight;
    };
    const pick = (i: number): void => {
      const id = rows[i] ? rows[i].dataset.id : undefined;
      closeOutline();
      if (id) scrollToFragment(body, id);
      takeKeyboard();
    };
    pop.addEventListener("click", (ev) => {
      const t = ev.target as Element | null;
      const r = t && typeof t.closest === "function" ? t.closest(".fileview-outline-row") as HTMLElement | null : null;
      if (r) pick(rows.indexOf(r));
    });
    pop.addEventListener("keydown", (e: KeyboardEvent) => {
      const take = (): void => { e.preventDefault(); e.stopPropagation(); };
      if (e.key === "Escape") { take(); closeOutlineKeeping(false); outlineBtn.focus({ preventScroll: true }); }   // the menu-button pattern: the keyboard back on the button (the header)
      else if (e.key === "ArrowDown") { take(); setCur(cur + 1); }
      else if (e.key === "ArrowUp") { take(); setCur(cur - 1); }
      else if (e.key === "Home") { take(); setCur(0); }
      else if (e.key === "End") { take(); setCur(rows.length - 1); }
      else if (e.key === "Enter" || e.key === " ") { take(); pick(cur); }
      // Tab and Shift+Tab leave the menu as a menu button's do: the popover closes, the keyboard goes back on the Outline button, and
      // the key's own default, left to run, moves it from there to the next or the previous control in the bar (the review's round
      // 3: the popover was the card's last child, so a Tab from it left the viewer for the first focusable behind the dimmed modal,
      // the chat's composer, which then took the letters typed). The focusout closer reads the button as the destination and stands down.
      else if (e.key === "Tab") { closeOutlineKeeping(false); outlineBtn.focus({ preventScroll: true }); }
    });
    pop.addEventListener("focusout", (e: FocusEvent) => {
      const to = e.relatedTarget as Node | null;
      if (to && (pop.contains(to) || outlineBtn.contains(to))) return;
      // to another element: it stays there. A null relatedTarget names two moves: the window losing the focus, where this
      // document's activeElement still reads the popover during focusout and the body takes the keyboard for the return, and a
      // move into another frame (the chat composer beside the Files pane), where the browser has cleared this document's active
      // element before focusout fires, so `held` reads false and the frame's own holder keeps it (the review's round 2;
      // file-view-keyboard-frames-browser.test.ts pins the second, closeOutlineKeeping reads the holder and never a flag)
      closeOutlineKeeping(to === null);
    });
    const onDown = (e: Event): void => {
      const t = e.target as Node | null;
      if (t && (pop.contains(t) || outlineBtn.contains(t))) return;
      closeOutline();
    };
    document.addEventListener("pointerdown", onDown, true);
    window.addEventListener("resize", closeOutline);
    dropOutline = () => { document.removeEventListener("pointerdown", onDown, true); window.removeEventListener("resize", closeOutline); };
    // Under the button, inside the card. The offsets are from the padding edge of the box's CONTAINING BLOCK, read after the
    // append as its offsetParent: the viewer's fixed overlay (#romp-fileview), since the card's `container-type` gives it no
    // layout containment in Chromium (the build placed the box from the card's edges, and in the chat and feed modals, where
    // the card is inset from the overlay, the popover sat 18 px too high over the button's lower half and 25 px left of its
    // anchor; the review's round 1). The caps are the body's height and the card's width, each less a margin, and never
    // past the card's bottom. The button's dress goes on BEFORE the boxes are read: the selected dress is bold, so the button
    // widens by a few px, and where the actions row was within that margin of a wrap step the row re-wraps and the button moves
    // down a line; read first, the box would place the popover over the button's old line (measured in the chat modal at
    // 1000 px: the popover 20 px above the button's bottom).
    outlineBtn.setAttribute("aria-expanded", "true"); outlineBtn.classList.add("on");
    box.appendChild(pop);
    const br = outlineBtn.getBoundingClientRect(), cr = box.getBoundingClientRect(), bd = body.getBoundingClientRect();
    const cb = (pop.offsetParent as HTMLElement | null) || box, pb = cb.getBoundingClientRect();
    const ox = pb.left + (cb.clientLeft || 0), oy = pb.top + (cb.clientTop || 0);
    pop.style.top = (br.bottom + 4 - oy) + "px";
    pop.style.right = Math.max(0, pb.right - (cb.clientLeft || 0) - br.right) + "px";
    pop.style.maxWidth = Math.max(0, cr.width - 16) + "px";
    pop.style.maxHeight = Math.max(0, Math.min(bd.height - 16, cr.bottom - br.bottom - 12)) + "px";
    // Anchored by its right edge with `left` auto, the box shrinks to fit its rows, and the rows are one line each
    // (nowrap), so its width is the longest heading's, capped by maxWidth alone: when that is wider than the room between
    // the card's left padding edge and the button's right edge (a 45-character heading at a 900 px pane, 33 at 380 px)
    // the browser solves `left` negative and the card's overflow clips the START of every row, the short ones to blank
    // strips (the review's round 1). Read after the placement (one more layout, per open of the popover): a box that
    // starts left of the card's margin is anchored at the margin instead, its width still capped at the card's less 16 px,
    // so every row starts inside the card and a heading wider than the card takes the rows' ellipsis. A box with no layout
    // (a stand-in) is left as placed.
    const pr = pop.getBoundingClientRect(), margin = cr.left + (box.clientLeft || 0) + 8;
    if (pr.width > 0 && pr.left < margin) { pop.style.left = (margin - ox) + "px"; pop.style.right = "auto"; }
    outline = pop;
    setCur(underEye());
    pop.focus({ preventScroll: true });
  };
  outlineBtn.addEventListener("click", () => { flash(outlineBtn); if (outline) closeOutline(); else openOutline(); });   // the press pulse, then the toggle (ui/CLAUDE.md: acknowledge at once)
  // ── text size ── A− and A+ step every text view through TEXT_SIZES, Ctrl/Cmd + wheel over the body
  // does the same, and the percentage between them (said once the size is off the default) is the reset;
  // textSizeControl above has the shape. Shown over a TEXT view only: the editor does not hold the body,
  // and the text the current view shows has landed (viewText: the fetch pipeline's text, or the decoded
  // XML while the SVG Source view is up; a picture or a PDF frame leaves both null). The text lands with
  // the kernel's Content-Type verdict, so a picture opened over a slow link never shows the control
  // beside the loader and then takes it away.
  // The step is bracketed by this viewer's place and reflow keeping (the third argument): the reader's place is read
  // before the size changes, and after it the seam's onRendered runs with `why` "reflow" (fireRenderedKeepingSelection)
  // and the place is seated again. One step of the text size lets the panel re-measure over the reflowed text (the
  // seam's onRendered with `why` "reflow": the highlights stand and the cards are re-placed over them, and the floating
  // Comment button hides, since the passage it sat by has moved; a standing selection is kept across the pass, see
  // fireRenderedKeepingSelection). A step that changes nothing (the table's end) fires nothing: a card may move only on
  // new information (CLAUDE.md), and no paint happened (the factory's set returns before the bracket on an unchanged step).
  // textShowing, the predicate the control and the bracket read, is declared below with the seam (its media gate is the
  // clause upstream's lacks); the thunks defer the reads to the first paint and the first press.
  const textSize = textSizeControl(box, () => textShowing(), (apply, keyboard) => {
    const kept = textShowing() ? keptPlace() : null;   // the top block before the text grows or shrinks around it
    apply();
    if (textShowing()) { fireRenderedKeepingSelection(); seat(kept); if (!keyboard) takeKeyboard(); }   // then the keyboard, after the seat: a pointer's or a wheel's step hands it to the body (a wheel step leaves a mark that holds it); a key on the button keeps it there, so the next press steps again
  });
  viewGroup.appendChild(textSize.wrap);          // the zoom glyph and its flyout (the three buttons inside)
  // ── the SVG Source toggle ── an SVG is served (and shown) as an image, but it IS also XML worth
  // reading; the toggle swaps in the existing highlighted-code view (langFor maps svg → xml) built
  // from the SAME fetched bytes — no second request. Appears only once an image/svg+xml body landed.
  const srcBtn = el("button", "fileview-btn") as HTMLButtonElement;
  srcBtn.type = "button"; srcBtn.textContent = "Source"; srcBtn.title = "The SVG's XML, highlighted";
  srcBtn.hidden = true;
  srcBtn.addEventListener("click", () => {
    if (svgText === null) {
      if (!mediaBlob) return;
      void mediaBlob.text().then((t) => { svgText = t; svgSource = true; renderBody(); takeKeyboard(); });
      return;
    }
    svgSource = !svgSource;
    renderBody();
    takeKeyboard();
  });
  viewGroup.appendChild(srcBtn);

  // ── edit (the raw-mode slice) ── exactly what raw mode can show is what Edit can touch: the
  // button arms only when the kernel served text/plain WITH a Last-Modified to anchor the save's
  // conflict floor (an old remote kernel that mirrors neither gets no Edit rather than an unguarded
  // one). Markdown edits from its Raw view — what you edit is what raw shows.
  const editBtn = el("button", "fileview-btn") as HTMLButtonElement;
  editBtn.type = "button"; editBtn.innerHTML = ICON_EDIT; editBtn.classList.add("fileview-icon"); editBtn.dataset.icon = "1";
  editBtn.title = "Edit this file in place"; editBtn.setAttribute("aria-label", "Edit");
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
  // (chunkTracks false), or the file's line endings would: a CRLF or a lone CR anywhere in the text (Slice 7 of
  // plans/markdown-viewer.md, item 7; CR_REFUSAL says how: norm rewrites a CRLF or a lone CR to LF before the mount, as
  // CodeMirror's document model would as it loads the string), which moves or mismatches the offsets the records
  // hold, so a save could not fit them back. Both refuse in words, in place, like editBlocked. The
  // CR refusal states its consequence literally: it is copy the person acts on (docs/guide.md says the same). The
  // words for what `begin()` returned, or null when the editor may carry it — asked at the CLICK (so a refusal needs no
  // consent popup first) and again at the MOUNT over the begin() whose records the editor takes (enterEdit): the consent
  // read between the two is a kernel round-trip, and a status landing inside it (the poll's tick, the panel's mount-time
  // ask answered, a session's write) turns a click-time "nothing pending" into records. Guarded at the click alone,
  // those records mounted over the LF buffer with their CRLF-disk offsets: marks on the wrong text, a reject rewriting
  // the wrong span, and a save that fit a deletion at a shifted offset (the review's CRLF-at-mount finding).
  const trackedRefusal = (pending: { refusal: string } | null): string | null => {
    if (!pending) return null;
    if (chunkTracks === false) return pending.refusal;
    if (text !== null && /\r/.test(text)) return CR_REFUSAL + " " + pending.refusal;
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
  fileGroup.appendChild(editBtn); fileGroup.appendChild(saveBtn); fileGroup.appendChild(cancelBtn);

  // The body row: `.fileview-main` holds the body and, when the comments panel asks for one, the aside
  // beside it (two columns; the sheet folds the aside below the body on a narrow column). The body itself
  // stays the plain overflow block the editor's height: 100% relies on — the row wrapper is what changed.
  const main = el("div", "fileview-main");
  const body = el("div", "fileview-body");
  // A Tab stop, so the scroll box can hold the keyboard (plans/markdown-viewer.md Slice 6, item 1): PageDown, Space, the
  // arrows, Home and End then scroll it natively, and takeKeyboard below gives it the keyboard after a paint the reader asked
  // for. Set once per open and never touched again: the Comments panel's press-time strip (file-comments.ts pressedMarks)
  // takes the tabindex off the MARKS it walks up from a press, never off this body, so the attribute stands through a press
  // and a press inside the body lands the browser's focus here, the nearest focusable ancestor, where it used to fall to
  // the document's body (file-view-focus-body-browser.test.ts reads both mid-press).
  body.tabIndex = 0;
  // A fetch landing rebuilds the body with no gesture of the reader's behind it (a reload the Comments panel's poll asked
  // for after a session's write). A press under way on a fence's Copy, or anywhere in the body, must outlive that swap: a
  // pressed node removed before the mouseup dispatches no click at all (actions.ts, the header), so the landing waits while
  // a pointer is pressed over the CARD and runs on the release (ui/CLAUDE.md, click-safe option 2;
  // file-view-copy-held-browser.test.ts). The card, not the body alone, since the PR review's round 1: the Outline popover is a
  // child of the card outside the body, and a landing during a press on one of its rows painted at once, its closeOutline
  // removing the pressed row before the mouseup, so the pick was lost (file-view-outline-browser.test.ts); a press on the
  // title bar's controls parks a landing the same way, and their clicks run before the parked run does (the hold's zero
  // timer), so a landing parked under a press on the Outline button ran after the click had opened the popover and its
  // paint closed it again: the text landing opens the popover again after its paint when the hold parked it (fetchFile,
  // reopenOutline; the PR review's round 2). The reader's own paints (a view swap, the editor) follow clicks already released.
  const hold = pressHold(box);
  // ── the keyboard (plans/markdown-viewer.md Slice 6, item 1) ── The body takes the keyboard after a paint the reader did
  // not type through: the open's first landing (keyboardOnLanding, text or media, spent once) and a paint the reader asked
  // for from the viewer's own chrome (the Rendered/Raw toggle, a text-size step, the SVG Source toggle). The gate is who
  // holds the keyboard at that moment, read from document.activeElement and never from a flag: nothing, the document's body,
  // or a control in the viewer's own bar (the button whose click caused the paint) yields to the body; anything else keeps
  // it: the chat's composer, the Comments panel's boxes and controls in the aside, the editor's textarea or CodeMirror (the
  // editor owns the body while it is up), a highlight or a card, a link inside the body, an element outside the card. A
  // reload's landing (the panel's poll asked it), the panel's own repaints (setMode) and a settings pick never call this:
  // the reader may be tabbed onto a mark or typing. preventScroll: the seat has placed the body and the focus must not move
  // it. Escape still closes through the document's onKey below, from the body as from the document's body.
  // `takingKeyboard`: the body's focus() is under way. In a Files iframe that did not hold the page's focus (a relay open from
  // the chat or the Waiting pane, the reader's last click in another pane) the call moves the focus into this frame and its
  // window fires `focus` synchronously inside it, which the changed-on-disk probe below would read as the reader's return
  // and answer with a HEAD of the file the landing just fetched (the review's round 1: GET then HEAD for every cross-frame
  // open, one GET for a same-frame one); the probe stands aside for a focus event the viewer's own call fired.
  // The chat composer beside a Files iframe is the composer too: this document's activeElement is its own body whenever the
  // page's focus is in another frame, so the gate also reads the focused frame's own active element through the top window
  // (typingInPeerFrame, above the open) and yields to a typing target there; a non-typing holder there yields as the
  // document's body does. Every hand-over runs through this one gate: the open's landing, the toggles, the Outline's closers,
  // the editor's exit at a Save's ack and the changed-on-disk bar's drop at a Reload's landing (the review's round 2).
  // The ring at a hand-over (the review's round 3). Both sheets draw no ring on the body's :focus and the accent ring on its
  // :focus-visible, for the keyboard user; Chromium's heuristic for a script focus does not draw that line by itself. It
  // matches :focus-visible on the new holder when the old one wore it and when a key was pressed since the last mouse press,
  // which is right, and ALSO when nothing focusable was last pressed (a fresh page, a click on plain text or on a chat pill
  // whose press strips its tabindex, a Recent row that is a plain div, a relayed open whose click was in another frame),
  // which framed the whole note in the accent on the common pointer opens. So the hand-over names the ring through the focus
  // call's focusVisible option, read off the holder the body takes the keyboard from (ringOf, module-level): a holder wearing
  // the ring (a Tab-focused toggle activated by Enter, the Outline popover after its arrow keys) passes it on; a mouse-focused
  // control passes none; and with no holder (the document's body holds the keyboard) the kind of this document's last press
  // decides, a key passing the ring and a pointer none (ringWithNoHolder, the review's round 4: round 3 passed none for every
  // holderless hand-over, and Enter on the file browser's active row, whose rows are not focusable, lost the ring the browser
  // had drawn for that keyboard user). A Tab into the body is a native focus and earns the ring on its own (a verdict passed
  // here is sticky for that focus, so the body's keydown below lifts it on the first plain key after a ringless hand-over). A
  // caller that removes the holder before the hand-over reads the ring first and passes it (the Outline's closers;
  // the disk bar's Reload records it at the click, before the disable drops the focus; the replace path reads a holder inside
  // the old card before the removal, ringInOld, and the open's first landing passes it). Chromium honours the option and a
  // browser without it ignores it; lib.dom's FocusOptions lacks the field, so the options object is typed here
  // (file-view-focus-ring-browser.test.ts and file-view-focus-ring-openers-browser.test.ts measure the ring over real presses
  // on every surface; file-view.test.ts pins the call's shape).
  let takingKeyboard = false;
  const takeKeyboard = (ring?: boolean): void => {
    if (editing || !wrap.isConnected) return;
    const a = document.activeElement;
    if (a && a !== document.body && !bar.contains(a)) return;
    if (typingInPeerFrame()) return;
    takingKeyboard = true;
    const opts: FocusOptions & { focusVisible: boolean } = { preventScroll: true, focusVisible: ring ?? (a === null || a === document.body ? ringWithNoHolder() : ringOf(a)) };
    try { body.focus(opts); } finally { takingKeyboard = false; }
  };
  // The ring after a key (the review's round 4). Chromium keeps the verdict a focus call named for the life of that focus, so a
  // body handed the keyboard without the ring (a pointer open, a mouse click on a toggle or a text-size step) showed none after
  // any number of keys, where the heuristic gives a mouse-focused element the ring on its first key. The body's own keydown
  // lifts it: the first key that is not a modifier alone and carries no Ctrl, Alt or Meta (a chord is a shortcut: Ctrl+C over a
  // selection in the body copies and shows no ring, as the heuristic has it) takes the keyboard again naming the ring, when the
  // body holds it without one. A re-focus of the element that already holds the focus changes nothing in Chromium (measured:
  // the verdict stands), so the body is blurred first and focused again in the same handler; the key's default runs after it
  // (nothing is prevented, so PageDown scrolls as it did), the selection stands (it is the document's, and a blur moves none
  // of it), and the focusout and focusin the pair fires stay on the body, which nothing in the viewer or the panel listens to
  // (the panel's press bookkeeping reads the window's blur alone). The probe's gate stands aside as for every own focus call.
  body.addEventListener("keydown", (e: KeyboardEvent) => {
    if (e.ctrlKey || e.altKey || e.metaKey || MODIFIER_KEYS.has(e.key) || editing) return;
    if (document.activeElement !== body || ringOf(body)) return;
    takingKeyboard = true;
    try { body.blur(); body.focus({ preventScroll: true, focusVisible: true } as FocusOptions & { focusVisible: boolean }); } finally { takingKeyboard = false; }
  });
  /** Nothing holds the keyboard: this document's activeElement is null or its body, and no box in a sibling frame is being typed
   *  in (the disable's drop and a click elsewhere both land the focus on a document's body; the bar's re-armed Reload reads this). */
  const keyboardIdle = (): boolean => { const a = document.activeElement; return (a === null || a === document.body) && !typingInPeerFrame(); };
  let keyboardPending = true;                          // the open's first landing takes the keyboard; a reload's does not
  const keyboardOnLanding = (): void => { if (!keyboardPending) return; keyboardPending = false; takeKeyboard(priorRing ?? undefined); };   // with the ring of the holder the replace path removed, when it had one
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
  const renderHooks: Array<(why?: FileViewRenderWhy) => void> = [];
  const selHooks: Array<(sel: Selection) => void> = [];
  const savedHooks: Array<(info: { mtimeNs: string; logged: boolean }) => void> = [];
  const fireRendered = (why: FileViewRenderWhy = "paint") => { for (const cb of renderHooks) { try { cb(why); } catch { /* a hook must never cost the view */ } } };
  // A REFLOW's paint keeps the person's selection. The hooks run with `why` "reflow": the panel answers that by re-placing
  // its cards and leaves its marks standing (file-comments.ts), so the selection now outlives the panel untouched; the
  // keeping below stands for any hook that does re-wrap on a reflow (a test's marks action does, and the panel did until
  // 2026-09-09: unwrapping and re-wrapping every highlight in paintAll, and a selection with an end inside a mark lost that
  // end with the mark's node: 58 selected characters over a highlight came back as 21 after one A+, 45 as 7 after a pane
  // resize (review 2026-09-07, round 2)). The text has not changed, only its elements, so each end is kept before the hooks run
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
  // Both reflows (a text-size step, the body's width changing) run through here, so this is where the pass is timed
  // as one fileview:reflow frame of the page's collector (perfTimed): the panel's re-place of its cards over the
  // reflowed text is what a large reviewed file pays per reflow, and it shows per minute.
  const fireRenderedKeepingSelection = () => perfTimed("reflow", () => {
    const sel = typeof window.getSelection === "function" ? window.getSelection() : null;
    const kept = sel && !sel.isCollapsed && sel.anchorNode && sel.focusNode && typeof sel.setBaseAndExtent === "function"
      && typeof document.createRange === "function"
      ? { a: keepPoint(body, sel.anchorNode, sel.anchorOffset), f: keepPoint(body, sel.focusNode, sel.focusOffset), text: sel.toString() } : null;
    fireRendered("reflow");
    if (!sel || !kept || !kept.a || !kept.f) return;
    if (!sel.isCollapsed && sel.anchorNode?.isConnected && sel.focusNode?.isConnected && sel.toString() === kept.text) return;   // the paint left it standing
    if (kept.a.at === kept.f.at && kept.text === "") return;   // a figure alone: the offsets cannot rebuild it, and would collapse it
    const a = pointBack(body, kept.a, kept.a.at < kept.f.at); const f = pointBack(body, kept.f, kept.f.at < kept.a.at);
    try { sel.setBaseAndExtent(a[0], a[1], f[0], f[1]); } catch { /* a point the layout refuses: the selection stays as the paint left it */ }
  });
  const ctx: FileViewActionCtx = {
    path, sid: sid || null, todoId: opts?.todoId ?? null,
    body: () => body,
    mode: () => (isImage || isPdf) && !(svgSource && svgText !== null) ? "media" : isMd && fmt.md === "rendered" && renderFell === null ? "rendered" : "raw",
    text: () => (editing && bufValue() !== null ? bufValue() : viewText()),   // in edit mode the buffer is the text (Slice 5)
    mtimeNs: () => mtimeNs,
    error: () => viewError,
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
    setMode: (mode) => { if (!isMd || editing) return; pickFormat(mode); },
    scrollToOffset: (n) => {
      const src = viewText();
      const code = body.querySelector("code.hljs");
      if (src === null || !code) return;
      const rows = code.querySelectorAll(".fv-cl");
      if (!rows.length) return;
      // The row through the anchor map's verified row map (rawRowForOffset: the last row whose source span starts at or
      // before the offset, so an offset past the end lands on the last row), which follows whatever split the rows were
      // built on: CRLF, a lone CR or LF (RAW_ROW_SPLIT; Slice 7 of plans/markdown-viewer.md, item 7). Before, a second
      // counter here counted LF alone, so every offset in a CR-only file landed on row 0. When the map refuses (rows that
      // do not match the source, which only a bug produces) the row is counted over the source with the viewer's own
      // split, exact by construction and clamped to the last row: never a guess, never a silent last row.
      const row = rawRowForOffset(code, src, n);
      const target = row ?? rows[Math.min(src.slice(0, Math.max(0, n)).split(RAW_ROW_SPLIT).length - 1, rows.length - 1)];
      (target as HTMLElement).scrollIntoView({ block: "center" });
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
  /** A picture or a PDF frame is showing: the editor does not hold the body, the body is a media body and its bytes have landed
   *  (the loader holds it before that). The gate for landTarget's media arm and the show's repaint over a media body. */
  const mediaShowing = (): boolean => !editing && ctx.mode() === "media" && objUrl !== null;
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
  const folds = foldKeeper(body);   // every fold's open or closed state across a paint (foldKeeper, below): noted before the swap, restored after it
  let place: Place | null = null;
  let placeWidth = -1;
  let placeScrollTop = -1;
  let placeHeld = false;   // `place` is the one a clamped seat was given, standing while the body stands where the clamp left it (seat, below)
  let asideScrollTop = -1;   // the body's scrollTop as the aside hook (ctx.aside, above) left it, -1 once a read has followed
  // A scroll whose frame found the body with no box (the pane hidden in the scroll's own task: a wheel tick, or a fling's last frame
  // as the rail is clicked or a phone swaps tabs): nothing can measure it, the place stands a frame stale, and the show's repaint
  // reads the offset the browser restores instead of seating over it (repaint, below; the review's round 6: the seat moved the
  // body back to the place before that scroll, where the tree before round 5, its place cleared by the hide, had seated nothing).
  // Set by the scroll listener's frame read (below) and cleared by the measurement it stands in for, a read of the place (notePlace)
  // or a clamped seat's hold (seat), each of which makes the place current (the review's closing pass: the repaint alone had cleared
  // it, past its early returns, so a flag set while the show's repaint stood down, the editor up or a media body shown, stayed armed
  // for a later show with no scroll behind it, which then read the offset in place of seating and dropped a clamped seat's hold).
  let scrollUnread = false;
  /** The clamped seat's place stands: the body stands where the clamp left it (seat, below). */
  const held = (): boolean => placeHeld && place !== null && body.scrollTop === placeScrollTop;
  const keptPlace = (): Place | null => (shownText === null ? null : held() ? place : readPlace(body, shownText));
  /** The body has no box (its pane's document is display:none: the Files pane toggled off, a phone's tab swap): every rect reads
   *  zero and scrollTop 0, so nothing reads or seats until it shows. notePlace keeps the place as last measured, the width hook's
   *  repaint seats and lands nothing on the report of the box going (its reflow still reaches the panel's hooks) and seats at the
   *  show's, landRemembered and landTarget wait for that repaint, and the leave writes the last measured place (liveRecord). A stand-in without getClientRects is measured as before. */
  const unmeasurable = (): boolean => typeof body.getClientRects === "function" && body.getClientRects().length === 0;
  // a boxless body reads no place, so the last measured one stands (the review's round 5: the hide's own width report had run this
  // over the hidden layout and cleared it, and a leave under the hidden pane, a restart's pagehide, then wrote nothing)
  const notePlace = () => { if (shownText !== null && textShowing() && !unmeasurable()) { place = readPlace(body, shownText); placeWidth = body.clientWidth; placeScrollTop = body.scrollTop; placeHeld = false; asideScrollTop = -1; scrollUnread = false; } };
  // A seat the browser CLAMPED (reader-place.ts seatPlaceOutcome: the write asked for more scroll than the view has, and the
  // body stands at its end) keeps the place it was given instead of reading the body: the read would name the block the
  // clamp shows, a paragraph before the reader's, and the next swap would seat THAT, so the Rendered/Raw round trip from
  // the end of the taller view came back one paragraph early (the Slice 3 review: the top block changed and its edge moved
  // 65 to 107px; before the slice the Raw view was the taller and the same clamp drifted the other direction by up to
  // 264px). The held place stands while the body stands where the clamp left it (placeScrollTop): the seat's own scroll
  // event moves nothing and is skipped below, the first scroll that does move it is the reader's and is read, and a swap
  // or a reflow that finds the hold seats the reader's own passage, which the other view can show, and a leave writes it
  // followed into the text that shows (liveRecord). Either branch consumes the aside hook's number (asideScrollTop): the seat
  // is the paint the hook's width change led to, and either makes the place current, so the unread-scroll flag falls (scrollUnread).
  const seat = (kept: Place | null) => {
    const clamped = kept && shownText !== null ? seatPlaceOutcome(body, shownText, kept).clamped : false;
    if (clamped && kept) { place = kept; placeWidth = body.clientWidth; placeScrollTop = body.scrollTop; placeHeld = true; asideScrollTop = -1; scrollUnread = false; }
    else notePlace();
  };
  const clamped = (): boolean => body.scrollTop < placeScrollTop && body.scrollTop >= body.scrollHeight - body.clientHeight - 1;
  /** A scroll under a new width the aside hook saw made, reporting a scrollTop other than the one the hook read after the
   *  mount: a script's (the reveal) or the reader's, past the browser's own adjustment. */
  const pastAside = (): boolean => asideScrollTop >= 0 && body.scrollTop !== asideScrollTop;
  // ── the reader's place, remembered across opens (plans/markdown-viewer.md Slice 6, item 3; RememberedPlace, above) ──
  // The record for this path when the open names no target (an `at` lands where the person pointed and the memory stands
  // aside): the host's (a Recent row's, opts.place) or the module's, whichever was read later. Seated once, on the FIRST
  // text paint, right after that paint's own seat (renderBody: seat(kept) runs notePlace over the fresh body at scrollTop
  // 0, and landRemembered then moves it), through seatPlaceOutcome as a reload's place is, with two things a record
  // cannot carry. Its height is unknown, so the record's depth into the block cannot be a fraction of the height
  // (seatedTop's rule for a view switch or a reflow) and is applied in pixels instead, after the block's top edge is
  // seated at the body's edge, and only when the view is the one the record was read in (the same pixels mean the same
  // passage there; in the other view the block's height is another number, and the block's top at the edge is what is
  // known). And its source is not kept, so a block the text moved (placeFromRemembered null) is not followed: the
  // numeric scrollTop is written and the browser clamps it. An unchanged file at the same width comes back to the pixel
  // the browser snaps to; the seat's clamp, if any, is not held (a place at the file's end reads as what shows there).
  const memKey = placeKey(path, sid);                 // the path, and the session for a relative one (placeKey)
  let pendingPlace: RememberedPlace | null = at === null ? newerPlace(opts?.place, rememberedPlaces.get(memKey)) : null;
  // A record read inside a fold the reader had opened (an author's <details>, a folded `[!type]-` callout, the front matter)
  // meets a reopen that paints every fold as authored (foldKeeper is per open, and the record carries no fold state), so the
  // remembered block has no shown box: seatPlaceOutcome's last resort walked back through the fold's hidden paragraphs to
  // the wrapper's refused block and seated nothing, and the numeric scrollTop from the OPEN fold's layout was written over
  // a document the shut fold made thousands of pixels shorter, a passage thirty paragraphs past the reader's shown as their
  // place (the review's round 1); and a block that IS a shut fold (a callout is one block) seated its summary at the edge
  // and then took the reader's depth into its open content over a box a summary tall. So the folds above the block's
  // elements are opened first, as the offset landing and a `#` link open them (revealFragmentTarget), and a fold that is
  // the block itself is opened when the record's edge lay in its content (a depth in the record's view past the shut box
  // the reopen paints, its summary): the reader had those folds open, since a shut fold's content is never at the edge, and
  // the seat is then the exact one; a depth inside the summary's own height says nothing, since the summary straddles the edge
  // the same open or shut, and the fold stays as authored (the review's round 2: a shut callout whose summary straddled the
  // edge came back open, thirty paragraphs taller). A record read in the other view (a Raw row inside a fold Rendered shuts)
  // opens the fold too, and shows the passage the reader had, every Raw row having shown, unless the body stood at the file's
  // very top (the record's `atTop`: the state a close from the editor leaves a reader in, nothing chosen, where the front
  // matter's block starts under the edge; the review's round 4: round 3's rule had read no sign, and every Rendered reopen after a
  // Raw leave at the top unfolded the front matter) or the block starts below the body's height (a Raw row read as the block after
  // a run of comment or closing-tag rows can name a block under the view's bottom). The review's round 5: round 4 had keyed the
  // rule on the block's top sign, `top` at most 0, which also covered the blank row before a shut callout at the edge, the
  // callout's rows all in view under it, and left that callout shut where round 3 had opened it; the record's own flag names
  // the one state round 4 meant. Since the review's
  // round 3 the record carries the Rendered view's open folds by ordinal (restoreFolds, below), so at the record's mtime every
  // fold comes back as the reader left it before any of this runs (an open fold whose summary sat at or just above the edge,
  // a fold read at another pane width), and the rules here are the fallback: a changed file, a record with no fold state;
  // when the record's folds WERE put back, the block's own fold stands as they say and the depth rule does not run over it
  // (the review's round 4: a fold left SHUT at 380 px with the edge 50 px into its two-line shut box, reopened at 900 where
  // the box is one line, met a depth past the shut box and came back open, the reverse face of the width window round 3
  // closed; restoreFolds says whether it applied, and revealRemembered takes that; the other-view rule runs whatever it says, a
  // Raw record's carried folds being older evidence than its place, the review's round 6).
  const revealRemembered = (p: Place, depth: number, otherView: boolean, restored: boolean): void => {
    const md = body.querySelector(".fileview-md");
    if (!md || shownText === null) return;
    const b = blockIndexAt(sourceBlockSpans(shownText), p.start);
    if (b < 0) return;
    for (const e of renderedBlockElements(md, shownText, b)) {
      revealFragmentTarget(e);
      // the fold's own shut box (its summary) shows the same open or shut, so only a depth past it says the content was showing;
      // a record read in the other view, Raw, where every row shows, names the fold's rows unless the body stood at the file's
      // very top (atTop: nothing chosen, the state a close from the editor leaves) or the block starts below the body's height (a
      // row read as the block after a run of comment or closing-tag rows can name one under the view) (the review's round 3: a Raw
      // record inside a folded callout reopened under the Rendered preference seated the shut summary at the edge; round 4: a Raw
      // record at the file's top had opened the front matter; round 5: round 4's sign test, the block's top at most 0, had left a
      // callout shut whose rows the reader had in view under the blank row at the edge); a fold the record's own state put back
      // (restored) is as the reader left it, and the depth rule does not run over it; the other-view rule does, since a Raw record's
      // folds are older evidence than its place: read at a Rendered paint before the Raw read named the fold's rows, and carried on
      // by the Raw leave (heldFolds; the review's round 6: a Rendered read with the callout shut as authored, Edit, a Raw read into
      // its rows and a Rendered reopen put the callout back shut, its summary at the edge over the passage the rows had shown)
      if (e.localName === "details" && !e.hasAttribute("open") && (otherView ? !p.atTop && p.top < body.clientHeight : !restored && depth > 0 && depth >= e.getBoundingClientRect().height - 0.5)) e.setAttribute("open", "");
    }
  };
  // The record's folds (RememberedPlace.folds), put back before the seat: every `<details>` of the Rendered body open or shut as
  // the reader left it, by ordinal, when the file's mtime is the record's (the same bytes render the same folds, so the
  // ordinals are exact; a changed file keeps the rules above, which read the block and its depth). A record with no fold
  // state (a Raw read, a note with no fold, an older store's record) changes nothing here. Returns whether it applied, so the
  // rules above stand down over a fold it put back (the review's round 4).
  const restoreFolds = (rec: RememberedPlace): boolean => {
    if (!rec.folds || rec.mtimeNs !== mtimeNs || ctx.mode() !== "rendered") return false;
    const md = body.querySelector(".fileview-md");
    if (!md) return false;
    const open = new Set(rec.folds);
    Array.from(md.querySelectorAll("details")).forEach((d, i) => { if (open.has(i)) d.setAttribute("open", ""); else d.removeAttribute("open"); });
    return true;
  };
  // A record's folds met by a RAW first paint (Edit saves the Raw preference, so the reopen after a close from the editor paints
  // Raw over a Rendered record; the preference switched elsewhere between the leave and the reopen the same) are held here for
  // the open's first Rendered paint, the toggle, and put back there at the record's mtime before that paint's seat
  // (renderBody, right after foldKeeper's restore, whose only note in such an open was taken over the Raw body and holds no
  // fold). The review's round 4: restoreFolds stood down over the Raw paint, landRemembered spent the record, and the toggle
  // painted every fold as authored, so the fold the reader had open came back shut with its summary at the edge over the
  // passage the Raw row had named (the same sequence with a Rendered first paint restores it exactly). Spent once; a changed
  // mtime by then leaves the folds as authored (restoreFolds' own gate). The same shape as pendingHeading, item 4's target held
  // for the Rendered toggle under the Raw preference.
  let pendingFolds: RememberedPlace | null = null;
  const restoreHeldFolds = (): void => { if (!pendingFolds || ctx.mode() !== "rendered") return; const r = pendingFolds; pendingFolds = null; restoreFolds(r); };
  const landRemembered = () => {
    if (pendingPlace === null || shownText === null) return;
    // A first text paint under a body with no box (the Files pane hidden while the fetch was in flight, a phone's tab swap, the
    // pane toggled off): every rect reads zero, so the span seat finds nothing and the numeric write is a no-op on a zero-height
    // scroller. The record stays pending for the next paint over a body that has a box: the width hook's repaint at the show
    // (the ResizeObserver's report of the width moving from 0, below) calls this again (the review's round 4: the note stood at
    // its top once the pane showed, the record spent under the hidden layout).
    if (unmeasurable()) return;
    const rec = pendingPlace; pendingPlace = null;
    const restored = restoreFolds(rec);
    if (!restored && rec.folds && rec.mtimeNs === mtimeNs && ctx.mode() !== "rendered") pendingFolds = rec;   // a Raw first paint: held for the first Rendered paint (pendingFolds)
    const kept = placeFromRemembered(rec, shownText);
    const depth = kept && kept.top < 0 && ctx.mode() === rec.view ? -kept.top : 0;
    if (kept) revealRemembered(kept, depth, ctx.mode() !== rec.view, restored);
    const seated = kept ? seatPlaceOutcome(body, shownText, depth ? { ...kept, top: 0 } : kept).seated : false;
    if (seated) { if (depth) body.scrollTop += depth; }
    else body.scrollTop = rec.scrollTop;
    notePlace();
    armReseat(rec, kept, depth);
  };
  // A picture that loads after the seat (a reopen after a page reload fetches the note's pictures anew, and an `<img>` has no
  // height at the first paint) grows the layout above the block by its height. Chromium's scroll anchoring then moves the
  // scrollTop to keep the top block where it was, so the span path stays exact, but the numeric fallback, written over the
  // shorter layout, then stands a picture's height past the record and shows what sat at that pixel in the short layout (the
  // review's round 2, measured: 384 px for one figure); an engine without anchoring would show both paths a picture's height
  // off. So the seat is written again at each picture's load while the body stands where the seat and the browser's own
  // adjustments left it: the same top block at the same offset (an anchored engine moved the scrollTop, not the reader) or the
  // same scrollTop (an engine without anchoring moved the content, not the reader). A scroll of the reader's changes both and
  // retires the re-seat, as the next text paint and the close do. The event is the picture's own load, heard on the body in
  // the capture phase (an img's load does not bubble); no timer (the review's round 3).
  let dropReseat: (() => void) | null = null;
  const armReseat = (rec: RememberedPlace, kept: Place | null, depth: number): void => {
    if (dropReseat) dropReseat();
    const loading = (): boolean => Array.from(body.querySelectorAll("img")).some((i) => !(i as HTMLImageElement).complete);
    if (!loading()) return;
    let at = { place, scrollTop: body.scrollTop };   // as the seat and notePlace left them
    const onLoad = (e: Event): void => {
      if (!e.target || (e.target as Element).localName !== "img" || shownText === null) return;
      const now = readPlace(body, shownText);
      const stands = body.scrollTop === at.scrollTop || (now !== null && at.place !== null && now.start === at.place.start && Math.abs(now.top - at.place.top) < 0.5);
      if (!stands) { retire(); return; }
      const seated = kept ? seatPlaceOutcome(body, shownText, depth ? { ...kept, top: 0 } : kept).seated : false;
      if (seated) { if (depth) body.scrollTop += depth; }
      else body.scrollTop = rec.scrollTop;
      notePlace();
      at = { place, scrollTop: body.scrollTop };
      if (!loading()) retire();
    };
    const retire = (): void => { body.removeEventListener("load", onLoad, true); dropReseat = null; };
    body.addEventListener("load", onLoad, true);
    dropReseat = retire;
  };
  ctx.onClose(() => { if (dropReseat) dropReseat(); });
  // A figure of the Rendered box that fails to load says so beside itself (armFigureLabels, module level): the body's `error`
  // and `load` capture listeners, armed once per open like the re-seat's above and never per paint, dropped with the viewer.
  ctx.onClose(armFigureLabels(body));
  // The write, at the moments the reader leaves the file (runLeave: closeFileView and both replace paths; the window's
  // pagehide listener in initFileView runs it too): the place as the body stands, read once here and never per frame (the Slice 5 review's cost
  // lesson), at this file's mtime and scrollTop, with the Rendered view's open folds by ordinal, into the module's map and the
  // host's ear. Never without a text view (a picture, a PDF frame, the loader, a failed fetch): a host that hears onLeave
  // always has a record to store, and the path's last record stands until a text view is left. While the editor is up its
  // buffer is not the text, so the leave writes the place of the text view the editor replaced, read at Edit (editPlace, set
  // by enterEdit before the Raw switch and cleared by exitEdit): a close from the editor with a clean buffer, a page hidden
  // while editing and the conflict bar's Reload wrote nothing before, and the next open fell to the top, or to the place of
  // the read before this one (the review's round 2; round 3 removed the sentence here that still said the leave wrote
  // nothing while editing).
  let editPlace: RememberedPlace | null = null;
  /** A record's folds held past a Raw first paint (pendingFolds) and not painted yet, at this file's mtime: a leave from that Raw
   *  view carries them on, so the next Rendered reopen puts them back (the review's round 5: the Raw leave wrote a record with no
   *  fold state, and the held state died with the open). */
  const heldFolds = (): number[] | null => (pendingFolds && pendingFolds.folds && pendingFolds.mtimeNs === mtimeNs ? pendingFolds.folds : null);
  /** The place as last measured, in the text that shows: `place` itself while nothing landed since the read; else (a reload landed
   *  under a body with no box, whose paint could read and seat nothing, so `place` still names its block in the text it was read
   *  from, `place.source`) the block of shownText that followPlace puts the reader's block at, its neighbour's when the write
   *  rewrote it, as the seat steps (seatPlaceOutcome), with the record's depth and flag; null when no block of shownText stands at
   *  or before it. The review's round 6: the leave under the hide wrote the old text's span under the new mtime, a record that
   *  claimed exactness and named a block the new text did not have at that offset, where the visible leave read the body anew; since the
   *  review's closing pass the visible leave reads this too while a clamped seat's place is held (liveRecord). */
  const measuredPlace = (): Place | null => {
    if (!place || shownText === null || place.source === shownText) return place;
    const spans = sourceBlockSpans(shownText);
    const { at, step } = followPlace(place, shownText);
    const found = blockIndexAt(spans, at);
    if (found < 0) return null;
    const b = Math.max(0, Math.min(spans.length - 1, found + step));
    return { ...place, source: shownText, start: spans[b].start, end: spans[b].end, prev: null, next: null, line: null, row: null, after: undefined, pic: null, lead: null };
  };
  const liveRecord = (): RememberedPlace | null => {
    if (shownText === null || !textShowing()) return null;
    // a body with no box (the pane hidden at a restart's pagehide, or at a close) reads no place and a scrollTop of 0: the place as
    // last measured stands, with its scrollTop (the review's round 5: the leave wrote nothing and the row kept the leave before it),
    // followed into the text a reload landed under the hide (measuredPlace; round 6); a clamped seat's held place, which a reload's
    // paint read over the text BEFORE the swap (renderBody reads `kept`, then replaces the body and seats it over the new text), is
    // followed the same way (the review's closing pass: the visible leave after a reload whose seat clamped, the new text ending at
    // or near the reader's block, wrote the old text's span under the new mtime through keptPlace's held arm, round 6's boxless
    // defect on its other branch)
    const boxless = unmeasurable();
    const p = boxless || held() ? measuredPlace() : readPlace(body, shownText);
    if (!p) return null;
    const rec = rememberedPlaceOf(p, mtimeNs, boxless ? placeScrollTop : body.scrollTop);
    const folds = openFoldOrdinals(body) ?? heldFolds();   // the Rendered view's open folds, by ordinal (none for a Raw read or a note with no fold), else the ones a Raw first paint holds for a Rendered paint that has not come; put back by landRemembered
    return folds ? { ...rec, folds } : rec;
  };
  leaveLive = () => {
    const rec = editing ? editPlace : liveRecord();
    if (!rec) return;
    rememberedPlaces.set(memKey, rec);
    if (leaveHost) { try { leaveHost(path, sid ?? null, rec); } catch { /* a host's store must never cost the leave */ } }
  };
  let placeFrame = 0;   // the pending frame read's handle, 0 for none (a read pending at the show's repaint is a scroll event since the hide's read: repaint, below)
  body.addEventListener("scroll", () => {
    if (placeFrame) return;
    const read = () => {
      placeFrame = 0;
      if (unmeasurable()) { scrollUnread = true; return; }         // the body lost its box since the scroll: read at the show (scrollUnread)
      if (placeHeld && body.scrollTop === placeScrollTop) return;   // the clamped seat's own scroll event: the body has not moved since
      if (body.clientWidth === placeWidth || (pastAside() && !clamped())) notePlace();
    };
    if (typeof requestAnimationFrame === "function") placeFrame = requestAnimationFrame(read); else read();
  }, { passive: true });
  ctx.onClose(() => { if (placeFrame && typeof cancelAnimationFrame === "function") cancelAnimationFrame(placeFrame); placeFrame = 0; });
  textSize.bindWheel(body);                            // Ctrl/Cmd + wheel over the text steps the size (textSizeControl)
  // The body's WIDTH: the Files pane dragged narrower or wider, the aside opening or closing, the window resized.
  // The text reflows (the prose measure follows the pane up to its cap, a table takes the room or scrolls in its
  // own box) and every position measured from it has moved, so the hooks run again with `why` "reflow", off the
  // layout's own report of the change (a ResizeObserver, never a timer). The observer's first report describes
  // the size at observe(), not a change. The repaint is ONE per animation frame: the reports are folded into the
  // next frame (requestAnimationFrame, the frame's own event) and the frame repaints only if the width it finds
  // differs from the one last painted over, so a burst of reports (several observers' entries, a width that
  // moved and came back, the body growing taller as a figure loaded) costs one pass or none. The panel answers a
  // reflow by re-placing its cards and nothing more (file-comments.ts): until 2026-09-09 it ran its whole paint
  // pass here, unwrapping and re-wrapping every highlight and rebuilding the cards, once per frame of a pane drag,
  // and at a big reviewed file (15,000 lines, hundreds of comments and changes) that pass took seconds a frame and
  // blocked the whole dashboard for the drag. Media bodies have their own observers (the figure layer's, the PDF chunk's), and the editor its own
  // layout, so textShowing gates this too. Absent ResizeObserver (a stand-in, an old engine) there is no width
  // event to key on, so nothing fires; absent requestAnimationFrame the report itself is the frame.
  // The body's CONTENT WIDTH, for the sheets (the pane-wide table's cap, `.fileview-md > table` reads --fv-body-w): the one
  // observer is watchBodyWidth's above, which stamps each top-level table (its comment says why) and hands back the stamp.
  // Until 2026-09-09 it sat on the body as an ordinary (inherited) custom property, and Chromium recomputed the style of every
  // node under the body on each write: 27 ms a step at 24k nodes, 138 ms at 79k, 259 ms at 134k (a fence-heavy note), on every
  // width change of the pane (M4 of the 2026-09-09 viewer-resize measurements).
  let paintedWidth = -1;   // the width the last repaint (or the first report) saw
  let seenWidth = -1;      // the latest report's width
  let frame = 0;           // the pending frame's handle, 0 for none
  const repaint = () => {
    frame = 0;
    if (seenWidth === paintedWidth) return;   // moved and came back within the frame: no text moved sideways
    // a media body: no text to seat, but the show's report is the one event after a boxless first paint, so the target and the
    // keyboard such a paint left pending land here (landMedia), and the keyboard the hide dropped comes back (retakeAfterHide)
    if (mediaShowing()) { paintedWidth = seenWidth; landMedia(); retakeAfterHide(); return; }
    paintedWidth = seenWidth;
    if (!textShowing()) return;
    fireRenderedKeepingSelection();   // the panel's hooks hear every report of a text view, the hide's (no width) included: its trim keeps every mark there and re-trims at the show's report (plans/markdown-viewer.md Slice 4, the retrim events)
    // the report of the box going (the pane hidden: no rects) seats and lands nothing, since nothing is measurable and the reader's
    // place stands as last read (notePlace: before the review's round 5 the seat below ran over the hidden layout and cleared it,
    // and a leave under the hidden pane then wrote nothing); the show's report seats over the box
    if (unmeasurable()) return;
    // the show's report over a scroll the hide kept from being read (scrollUnread): the offset the browser restored is the reader's, so
    // it is read, not seated over, while the text and the width are the ones the place was read under (a seat would move the body
    // back to the place a frame stale; the review's round 6) and the body is not back at 0 (an engine that restores no offset comes
    // back there, and the seat is what puts the place back; a reader who reached the file's top in that frame is seated a frame
    // back, the one case the two cannot be told apart); a text or a width that changed under the hide keeps the seat, which follows
    // the block into the new text or the new layout. And the restore is trusted only where it did not move the body: a scroll event
    // since the hide's read, its own frame read still pending (placeFrame), is the restore's, since nothing scrolls a body with no
    // box and an exact restore fires none (measured in headless Chromium: the Raw view's restore lands SHORT when the reader stood in
    // the note's last 144 px at 900x520, a clamp against a layout pass shorter than the final one, where the Rendered view's is
    // exact), and a restore that moved the body to below the place last measured is a bound under the reader's offset, not the offset,
    // so the place is seated, the reader having stood there a frame before the unread scroll, and a clamped seat's hold stands (the
    // review's closing pass: the show read the short offset as the reader's, 116 px short of the scroll and 86 px behind the place,
    // and dropped the hold the Raw swap from the Rendered view's end had taken, so the swap back landed four blocks off); a restore
    // that moved the body to or past the place is read, the reader having scrolled at least that far. A reader's own scroll in the
    // frame between the show's layout and this repaint reads as the restore's. Either branch clears the flag (notePlace, seat)
    const moved = placeFrame !== 0;
    const restored = scrollUnread && body.scrollTop > 0 && place !== null && place.source === shownText && body.clientWidth === placeWidth && !(moved && body.scrollTop < placeScrollTop);
    if (restored) notePlace(); else seat(place);   // the restored offset read, or the place read before the width moved (see notePlace) seated
    landRemembered(); landTarget();                // then a remembered place a first paint under a boxless body left pending (landRemembered), and the target and the keyboard such a paint left pending (landTarget)
    retakeAfterHide();                             // and the keyboard the hide's focus fixup dropped off the body, if the body held it (retakeAfterHide)
  };
  // The Files pane toggled off and on (the shell's display:none on the pane; a phone's tab swap): the browser's focus fixup drops
  // the keyboard off a body that has no box, to the document's body, and nothing re-took it at the show, since keyboardOnLanding
  // is spent at the first landing, so PageDown scrolled nothing until a click (the review's round 6 recorded it; the PR review's
  // round 1 fixed it). The body's own focus and blur keep the record: a blur while the body has a box is a move the reader made,
  // to another element, another frame or nowhere, and clears it; the fixup's, if the engine fires one at all, finds the body
  // boxless and leaves the record standing. The show's repaint then hands the keyboard back through takeKeyboard's gate, so a box
  // the reader is typing in meanwhile, the chat composer beside the pane, keeps it. No flag is set by the viewer's own code paths:
  // the body's focus event is the record, whoever focused it.
  let bodyHeld = false;
  body.addEventListener("focus", () => { bodyHeld = true; });
  body.addEventListener("blur", () => { if (!unmeasurable()) bodyHeld = false; });
  const retakeAfterHide = (): void => {
    if (!bodyHeld || unmeasurable() || document.activeElement === body) return;
    bodyHeld = false;
    takeKeyboard();
  };
  const stampBodyWidth = watchBodyWidth(body, (w) => {
    if (paintedWidth < 0) { paintedWidth = w; seenWidth = w; return; }   // the first report describes the size at observe(), not a change
    seenWidth = w;
    if (w === paintedWidth || frame) return;
    if (typeof requestAnimationFrame === "function") frame = requestAnimationFrame(repaint); else repaint();
  });
  ctx.onClose(() => { dropWidthWatch(); if (frame && typeof cancelAnimationFrame === "function") cancelAnimationFrame(frame); frame = 0; });

  // Registered actions render after the built-ins — the registry walk is the ONE place row
  // conventions live (see registerFileViewAction above). The GitHub link and Comments mount here.
  for (const a of fileViewActions) {
    const n = a.mount(ctx);
    if (n) fileGroup.appendChild(n);
  }

  // ── download (the user 2026-08-09) ── Any linked file can be SAVED, including everything the pane
  // cannot show: the kernel's ?download=1 serves anything on disk (the rationale lives with
  // _file_download in kernel.py). Same-origin and cookie-authed like the view fetch, and
  // federation-aware for free — fileUrl already routes a remote session's file through the relay.
  const dlUrl = fileUrl(path, sid) + "&download=1";
  const dl = el("button", "fileview-btn") as HTMLButtonElement;
  dl.type = "button"; dl.innerHTML = ICON_DOWNLOAD; dl.classList.add("fileview-icon"); dl.dataset.icon = "1";   // the tray glyph the lightbox wears (icons.ts)
  dl.title = "Download"; dl.setAttribute("aria-label", "Download");
  dl.addEventListener("click", () => startDownload(dlUrl, dl));
  fileGroup.appendChild(dl);

  // ── copy path (a glyph since T367) ── the acknowledgement is a glyph swap with the words in the tooltip and
  // aria-label: the press dims the button in the same tick (click-safe: every press acknowledges), then a check
  // and "Copied" for a moment, or a cross and "Copy failed" until the next press. No clipboard here (an insecure
  // origin drops navigator.clipboard) is said at once as the failure.
  const copy = el("button", "fileview-btn fileview-icon") as HTMLButtonElement;
  copy.type = "button"; copy.innerHTML = ICON_COPY; copy.dataset.icon = "1";
  copy.title = "Copy path"; copy.setAttribute("aria-label", "Copy path");
  let copyTimer: ReturnType<typeof setTimeout> | null = null;
  const copySay = (icon: string, word: string, cls: string, ms: number | null) => {
    copy.innerHTML = icon; copy.title = word; copy.setAttribute("aria-label", word);
    copy.classList.remove("ok", "err", "fileview-busy"); if (cls) copy.classList.add(cls);
    if (copyTimer) { clearTimeout(copyTimer); copyTimer = null; }
    if (ms !== null) copyTimer = setTimeout(() => copySay(ICON_COPY, "Copy path", "", null), ms);
  };
  copy.addEventListener("click", () => {
    copy.classList.add("fileview-busy");                     // the same-tick acknowledgement
    const w = navigator.clipboard?.writeText(path);
    if (!w) { copySay(ICON_CROSS, "Copy failed", "err", null); return; }
    w.then(() => copySay(ICON_CHECK, "Copied", "ok", 1200), () => copySay(ICON_CROSS, "Copy failed", "err", null));
  });
  const close = el("button", "fileview-btn fileview-close") as HTMLButtonElement;
  close.type = "button"; close.textContent = "✕"; close.title = "Close (Esc)";
  close.setAttribute("aria-label", "Close the file viewer");
  close.addEventListener("click", closeFileView);
  fileGroup.appendChild(copy);
  acts.appendChild(viewGroup); acts.appendChild(fileGroup); acts.appendChild(close);
  bar.appendChild(name); if (sess) bar.appendChild(sess); bar.appendChild(acts);

  box.appendChild(bar); box.appendChild(main);
  wrap.appendChild(box);
  document.body.appendChild(wrap);

  // The edit-mode notice (a degraded editor, a refused save): one at a time, replacing the last, mounted as
  // a child of the card between the title bar and the body. It used to be prepended inside the body, above
  // an editor whose height is 100% of that same body, so the body's content was the bar plus the whole body:
  // the editor's bottom rows were cut off by the bar's height, and the body's own scroll carried the bar
  // out of view. As a row of the card (a column flex container; .fileview > .fileview-err keeps its height)
  // the body shrinks under it and the editor's 100% resolves against what is left. Nothing swaps the card's
  // children, so leaving edit mode removes the notice itself (exitEdit). Held by reference, THIS card's
  // notice and no other: a viewer that was replaced (Reload file re-opens fresh) keeps its keydown handler
  // and still runs its exitEdit on Escape, and a lookup by id from there would strip the live card's notice
  // while that card is still in edit mode.
  // In this tree the same bar carries the viewer's other one-line notices too (a blocked edit, a refused save, a
  // comments-log warning, a line past the end; plans/markdown-viewer.md Slice 2), so it shows at any scroll
  // position and outlives a view switch and a reload; and the body row it sits above is .fileview-main, the row
  // the body shares with the panel (upstream's card has the body directly under the title bar).
  let note: HTMLElement | null = null;
  const noteBar = (msg: string): HTMLElement => {
    note?.remove();
    const bar2 = el("div", "fileview-err");
    bar2.id = "fileview-save-err";
    bar2.textContent = msg;
    box.insertBefore(bar2, main);
    bar2.setAttribute("role", "status");   // a polite live region: the changed-on-disk bar is raised with no gesture of the reader's, so assistive technology hears it (the PR review's round 1); every other notice follows a click and is announced the same
    note = bar2;
    return bar2;
  };
  // The Latin-1 line (the raise at the text landing, item 5 of Slice 7) says why Edit is off; a landing whose header says the
  // file is UTF-8 now (a session re-saved it) brings Edit back through the gate, so that landing drops the line when it is the
  // notice standing, the settleDiskBar shape (the review's round 1: the line stood over a shown Edit button until the next
  // notice). The failure pane's paint (the fetch chain's catch: a 404 after a deletion, a 413 after a growth past the cap, a
  // network failure) drops it too: the line says the file can be read here and the pane says it could not be, and nothing else
  // removed the line over the pane until some other notice replaced it (the review's round 2); a later landing whose header
  // says "0" raises it again, and so does a format pick whose paint puts the text back over the pane (pickFormat; the
  // review's round 3). Known by its words, the one notice shown alone with them; a notice standing in its place (a
  // target's, a warning's, the changed-on-disk bar with its button) is not touched.
  const dropLatin1Line = (): void => {
    if (note !== null && note.textContent === LATIN1_NOTICE) { note.remove(); note = null; }
  };
  /** The line is the notice standing (the same words): a landing that would raise it again leaves the element as it is. */
  const latin1LineStands = (): boolean => note !== null && note.textContent === LATIN1_NOTICE;

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
    why.textContent = DECODE_FAILED;            // the exported sentence (the guide's pin reads it there)
    const words = why.textContent;              // the sentence alone, taken before the hint and the button join the pane: error()'s answer, never read back off the body
    const hint = el("div", "fileview-err-hint");
    hint.textContent = path;
    why.appendChild(hint);
    const offer = el("button", "fileview-btn fileview-err-dl") as HTMLButtonElement;
    offer.type = "button"; offer.textContent = "Download";
    offer.title = "Save this file to your device";
    offer.addEventListener("click", () => startDownload(dlUrl, offer));
    why.appendChild(offer);
    body.replaceChildren(why);
    viewError = words;                          // the pane's paint: the seam's error() answers its sentence until a content paint clears it (Slice 7, item 3)
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
    textSize.sync();                          // the text-size control follows every paint: shown over a text view only
    closeOutline();                           // the Outline's rows were read off the DOM this paint replaces (the popover is out of the flow: no layout moves)
    if (dropReseat) dropReseat();             // a remembered seat's re-seat on the pictures' loads ends with the body it was armed on (armReseat)
    // The Outline button's visibility is the ONE bar control that differs between the two text views, and a bar whose height
    // changes (the actions row wraps at the pane's width with one more button) moves the body's height: hidden here, before
    // the paint below reads the reader's place, it re-clamped a body standing at the document's end and the held place was
    // lost (the Slice 6 consolidation: the Rendered/Raw round trip from the end came back one paragraph early, a fold's row
    // 523px low). So a text paint decides it inside the paint, after the swap and before the hooks measure and the seat
    // writes (syncOutline, below); only the paths that paint no text hide it here (the loader, the editor's entry).
    if (editing || text === null) outlineBtn.hidden = true;
    viewGroup.hidden = !(segBtns.some(([, b]) => !b.hidden) || !textSize.trigger.hidden || !srcBtn.hidden || !outlineBtn.hidden);   // an all-hidden group takes no gap (edit mode hides the pair too); the Outline button is decided inside the paint, so syncOutline re-reads this
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
      viewGroup.hidden = !(segBtns.some(([, b]) => !b.hidden) || !textSize.trigger.hidden || !srcBtn.hidden || !outlineBtn.hidden);   // the media branch decides the Source button after the group's first sync above, so the group is re-read here: the SVG Source view is the one media control in the view group (T367's grouping)
      if (objUrl === null) return;            // the romp loader holds the body until the bytes land
      viewError = null;                       // a media view paints below (the SVG Source view, the chunk's pages, the frame or the picture before whenShown; a kept frame stands): no pane shows once it does (Slice 7, item 3)
      // a target on a picture or a PDF (a heading, a line, an offset) is judged by the landing, not here: landMedia, over a body
      // with a box, names it in the notice bar (the PR review's round 1; the review's round 3 had the heading judged here)
      if (svgSource && svgText !== null) {
        // the Source view is a text view (textShowing), so it keeps the reader's place as the Raw view does: read, swap,
        // hooks, record the XML as the text painted, seat (the Slice 2 review, round 3: a reload under the Source view
        // and the Comments panel's close left the numeric scrollTop over the re-laid rows, 27 rows off)
        const kept = keptPlace();
        body.replaceChildren(codeBlock(svgText, path, true));   // long lines always soft-wrap (the user 2026-08-24)
        fireRendered();                         // a text body: the panel's highlight pass runs on it too
        shownText = svgText;
        seat(kept);
        landRemembered();                       // the first text paint of an open with a remembered place seats it (once)
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
    // the folds' state under the view about to go, read before the editor's early return too: Edit paints nothing here and
    // then takes the body itself, so this is the one read between the person's last click and the loader (foldKeeper)
    folds.note();
    if (text === null || editing) return;   // loading, or the textarea owns the body right now
    // The pass below builds the block and swaps it in one try (plans/markdown-viewer.md Slice 7, item 1): a marked bug must never
    // cost the content, and this is where the content is kept now that mdBlock carries no catch of its own. A throw from marked,
    // from the sanitizer, from any DOM pass of mdBlock or from replaceChildren itself takes the one road: the body gets the
    // RENDER_FELL line first and the text as Raw rows under it, the line saying what happened where the person is looking
    // (fellMessage: the error's message, marked's appended report-this sentence cut), instead of the source written into the
    // Rendered box as one unannounced paragraph, and the message is recorded once that fallback stands (renderFell, which mode()
    // reads as "raw" for this paint). The fallback runs in the catch, and a throw from THAT propagates (into the fetch chain's
    // own catch at a landing): a second failure is a bug, not a file; the previous paint stands and its record with it, so
    // mode() still answers what the body shows (the review's round 2: recorded before the swap, a fallback throw from a click
    // left mode() saying "raw" over a standing Rendered box) and so does error(), cleared after the swap for the same reason
    // (the review's round 3: cleared before the pass, a fallback throw over a standing failure pane left error() null while
    // the pane stood, and the Comments panel's next pass would have said the view still showed the earlier text). The rest of
    // the pass runs as for any text paint, so the
    // hooks fire once and read the rows through mode(); the Rendered button stays pressed (fmt.md is the person's saved choice;
    // the line says why rows show), the Raw click paints rows without the line, the Rendered click tries again. The editor's
    // entry sets fmt.md to raw before its own paint and returns above, so its exit repaints Raw and clears the record as any
    // paint that stands does.
    perfTimed("paint", () => {                // the whole pass, the place read to the seat, as one fileview:paint frame of the page's collector (perfTimed)
      if (text === null) return;              // never taken (the guard above returned): TypeScript drops a reassignable variable's narrowing inside a closure
      const kept = keptPlace();               // the reader's place under the view about to go (null: the loader, or the editor, held the body)
      try {
        body.replaceChildren(rendered ? mdBlock(text, { kind: "file", path, sid: sid || null }) : codeBlock(text, path, true));   // long lines always soft-wrap (the user 2026-08-24)
        renderFell = null;
      } catch (err) {
        const fell = fellMessage(err);
        body.replaceChildren(renderFellLine(fell), codeBlock(text, path, true));
        renderFell = fell;                    // recorded once the fallback stands (the header): a throw from the fallback leaves the previous paint and its record
      }
      if (text === "") body.prepend(textBytes !== null && textBytes > 0 ? bomOnlyLine() : emptyFileLine());   // an empty file says so above its empty root (plans/markdown-viewer.md Slice 7, item 6): a sibling outside code.hljs and .fileview-md, so the map sees zero rows and the pairing no block; text stays "" and Edit shown; a landing that brings bytes repaints without it; over a render that fell it stands above the RENDER_FELL line and the rows, the stacked order item 6 records (the review's round 6); a file whose bytes were a BOM alone (more than zero bytes decoding to "") says that instead, in the same place (BOM_ONLY_FILE; the review's round 1)
      viewError = null;                       // the paint stands (the Rendered box, the rows, or the line over the rows a failed render fell back to, whose word is mode() "raw"): no pane shows (Slice 7, item 3). After the swap, as renderFell is recorded: a throw from the fallback's own swap propagates past this line and leaves the previous paint, a failure pane's included, with its record, so error() keeps answering the pane the body still shows (the review's round 3)
      folds.restore(); restoreHeldFolds();    // each fold as the person left it, then a record's folds held past a Raw first paint (pendingFolds), before the hooks measure and the seat reads the heights (a Raw paint has none)
      stampBodyWidth();                       // the fresh root's tables take the body's width (no report follows a render)
      syncOutline();                          // the Outline button over this paint (shown over a Rendered paint that holds a heading): the bar's layout settles before the hooks measure and the seat writes
      fireRendered();                         // the seam's onRendered: every text paint, so highlights follow the view
      shownText = text;
      seat(kept);                             // then the place, after the hooks as the selection keeper orders it: the same passage at the same height
      landRemembered();                       // the first text paint of an open with a remembered place seats it (once; RememberedPlace)
    });
    if ((rendered || !isMd) && pendingHeading !== null) spendHeading();   // a file that is not markdown has no sections and no Rendered toggle to wait for: its first text paint judges the target (the review's round 2)
  };
  // Item 4's heading, spent at a paint that can land it (a note's Rendered paint, any text paint of a file that is not markdown)
  // and landed one frame later through scrollToFragment, or named in the notice bar as no section of the file. Never spent over
  // the rows a failed render fell back to (renderFell; Slice 7 of plans/markdown-viewer.md, item 1, the review's round 1): the
  // rows hold no section to look for, so the target waits for the Rendered retry as it waits under the Raw preference; before,
  // the frame judged the rows and raised "No section named" under the failure line, of a section the file has. Landed over a body
  // with a box alone: under a hidden pane scrollIntoView moves nothing and the landing would count as done, so the frame parks the
  // target again for the width hook's repaint at the show, which spends it through landTarget (the review's round 5, with the
  // line, the offset and the keyboard). Spent once per call: a second call before the frame (the landing's, after renderBody's own)
  // finds nothing pending and queues no frame.
  const spendHeading = (): void => {
    if (renderFell !== null) return;          // the paint fell to the Raw rows: the target stays pending for the Rendered retry (the header)
    const h = pendingHeading; pendingHeading = null;
    if (h === null) return;
    requestAnimationFrame(() => {
      if (wrap.isConnected && unmeasurable()) { pendingHeading = h; return; }   // no box yet: held for the show's repaint (landTarget)
      if (!wrap.isConnected || scrollToFragment(body, h)) return;
      // the section is there but under a plain `hidden` wrapper (an author's stashed section; the landing lifts `until-found` alone, as
      // the browser's own does): no box to land on (scrollToFragment lands nothing), so the note stays at its top and the notice says so
      // (the PR review's round 1: the open landed at the top with no word; "No section named" would be false of it, and the Outline
      // offers it no row, headingsOf)
      if (sectionHidden(body, h)) { noteBar(HIDDEN_SECTION); return; }
      // no such section: named as the link wrote it, decoded where the browser's encoding allows
      const name = h.replace(/^#/, "");
      let shown = name; try { shown = decodeURIComponent(name); } catch { /* a stray %: named as written */ }
      noteBar('No section named "' + shown + '" in this file.');
    });
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
    // A press on a title-bar CONTROL (A−, A+, the readout, Raw, Copy path, the GitHub link) settles no
    // selection: the mouseup lands on the button while a passage may still stand selected in the body,
    // and the seed below would re-read the file and re-seed the quote chip on every step of the text
    // size. The gate is the control under the lift, not the bar: a drag that starts in the body and is
    // released over the bar's path or its padding (the overshoot when selecting back to a file's first
    // line) is a selection like any other and settles.
    // The listener sits on the viewer root so a drag that ends over the aside or the margins settles too.
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
    openLinkedFile(p, sid || null, ln > 0 ? { line: ln } : x.dataset.frag ? { heading: x.dataset.frag } : null);
  };
  // A gated figure's placeholder (figure-gate.ts; decision 8 of plans/markdown-viewer.md): the click loads every figure
  // of that host in the document and remembers the host for the page. Read here, on the stable body, since every paint
  // rebuilds the placeholder (ui/CLAUDE.md, click-safe controls); Enter and Space do the same for a focused one, as its
  // role says they should (gateKeys, shared with the URL viewer). The restore is the acknowledgement: the picture stands
  // where the placeholder was, at once.
  gateKeys(body);
  body.addEventListener("click", (ev) => {
    const t = ev.target as Element | null;
    const g = gateOf(t, body);
    if (g) { ev.preventDefault(); loadGate(g); return; }
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
  const norm = (s: string): string => s.replace(/\r\n?/g, "\n");   // the editor's own view of any text: CodeMirror's document model and the textarea alike read a CRLF or a lone CR as a line break and give it back as LF (Slice 7 of plans/markdown-viewer.md, item 7)
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
  closeHooks.push(closeOutline);               // …and drop the Outline popover's document and window listeners with the viewer
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
    editPlace = liveRecord();                   // the reader's place in the text view the editor replaces, for a leave while it is up (leaveLive); read before the Raw switch below, of the view they read
    // markdown edits from its Raw view (what you edit is what raw shows): switched here, past the guard, so a refused
    // Edit leaves the Rendered view it was clicked from standing under the refusal, not a Raw choice saved and unpainted
    if (isMd && fmt.md === "rendered") { fmt.md = "raw"; saveFmt(fmt); }
    editing = true; dirty = false;
    eolCRLF = /\r\n/.test(text);
    eolCR = /\r/.test(text) && !/\n/.test(text);   // every ending a lone CR (eolCR's comment): the save door writes them back
    renderBody();
    // The panel's edit-mode render. Its cards read editing() at render time (the caption that says to decide in the
    // editor, Accept and Reject dimmed with those words, no Reveal or link into a read view that is gone: setMode and
    // scrollToOffset are no-ops now), and nothing above rendered them with the flag set: begin() ran before it, as it must
    // (a refused begin() leaves the read view untouched), and renderBody paints nothing in edit mode. So the seam's
    // onRendered fires here, once, as the editor takes the body: the panel's paint pass stands down on editing() and its
    // cards take their edit-mode state. Without it a panel open at Edit kept its read-mode cards, live-looking controls
    // that did nothing, until some status happened to land (the review's cards-keep-read-mode finding). The exit's
    // repaint hands the read-mode state back.
    viewError = null;                           // the editor takes the body: no pane shows (a failed reload's pane over the text, say; the exit repaints the earlier text, or re-reads when a fetch landed under the editor, and the panel's row says what happened)
    fireRendered();
    // a notice over the read view (a refusal since lifted, a line past the end) goes as the editor takes the body: the
    // swap below took it while the bar sat inside the body, and the bar now sits above the row (noteBar), THIS card's
    note?.remove(); note = null;
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
      // loud: say the editor is degraded, never pretend
      noteBar(why + " — editing in the plain fallback editor.");
    });
  };
  const exitEdit = () => {
    editing = false; dirty = false; ta = null;
    editPlace = null;                           // the text view is back: a leave reads it live again
    cm?.destroy(); cm = null;
    applied = { accepted: [], rejected: [] };   // the decisions went with the editor; the next mount starts its own afresh
    editHooks = null;                           // a cancelled save's late ack must not touch a NEW session
    saveBtn.disabled = false; saveBtn.textContent = "Save";
    // the notice is a row of the card (noteBar), so the body swap below no longer takes it: a save that
    // landed, Cancel and Escape all leave through here, and none may leave a stale notice standing. The
    // edit's notices (a refused save's, a declined close's, a fallback editor's) go with the editor, and a
    // notice that must outlive the exit is raised again after it (noteLog).
    note?.remove(); note = null;
    renderBody();
    // a fetch that landed while the editor was up painted nothing (fetchFile): now that the edit is over, read the file
    // as it is — the exit is the event the dropped bytes were waiting for
    if (refetchAfterEdit) { refetchAfterEdit = false; fetchFile(); }
    // …or, with nothing to re-read, the changed-on-disk bar the editor's entry took with the other notices comes back with
    // the read view when the file it was raised under is still the one that shows (a save that landed moved the mtime; the
    // re-read above settles it at its landing): the reader is shown the old text again, and the line says so without a HEAD
    // (the review's round 1: after Cancel the old text stood with no line above it until the next focus)
    else if (diskBar && diskBar.under === mtimeNs && mtimeNs) raiseDiskBar(diskBar.words);
    // the exit's repaint is a paint the reader asked for from the viewer's own chrome (Cancel, Save, Escape in the editor),
    // so the body takes the keyboard as after the Rendered/Raw toggle (takeKeyboard's gate: the button that was clicked, or
    // the document's body the editor's removal left it on, yields; the panel's box keeps it); before the review's round 1
    // PageDown after Cancel scrolled nothing until a click
    takeKeyboard();
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
    // (and a CR-only file's lone CRs the same way, eolCR: the editor gave every one back as LF)
    const content = eolCRLF ? buf.replace(/\n/g, "\r\n") : eolCR ? buf.replace(/\n/g, "\r") : buf;
    // the decisions this save carries (the tracked path below fills it): marked applied when the save lands, so a later
    // Save from the same editor sends only what came after
    let sent: EditDecisions | null = null;
    // Loud, in place, and the BUFFER SURVIVES: the error bar sits above the body that holds the
    // textarea. A conflict (the disk moved: an agent wrote it) carries a Reload button, which re-opens
    // fresh behind the same discard confirm, so the user's edits are never thrown away silently (never
    // a merge UI).
    // `moved`: the comments host's store-moved / file-moved / config-moved refusals (Slice 5), and its `busy` (another
    // writer held its lock past the wait; decision 49), offer the same Reload the kernel's own conflict wording does; a
    // desync or any other refusal shows its reason and keeps the buffer, no offer.
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
        showSaveError(err, code === "store-moved" || code === "file-moved" || code === "config-moved" || code === "busy");
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

  // ── changed on disk (plans/markdown-viewer.md Slice 6, item 5) ── With the Comments panel closed nothing watched the
  // file: a session's write went unnoticed until something else reloaded it. A `focus` on this window and a
  // `visibilitychange` to visible, the moments the dashboard has the reader's attention again, each run ONE
  // `HEAD /file` (the kernel answers the GET's headers and no bytes; fileUrl, the URL the GET used) while the viewer
  // shows a fetched file (mtimeNs set: text or media) and the editor is not up. The answer is read as the panel's poll
  // reads its own (headVerdict, then mtimeMoved: a string compare, the contract the panel and the save fence keep). A
  // move raises the one-line bar above the body row, CHANGED_ON_DISK with a Reload button: the click runs fetchFile,
  // which keeps the reader's place as every reload does, and the bar goes at the landing that applies a different
  // mtime from the one it was raised under, whoever asked for that reload (with the panel open its poll asks within
  // 2.5 s, and the later landing rules), or at the landing of the bar's own ask whatever mtime it brings (a HEAD
  // answered after a newer landing had already put the moved file in the body raised it over the file that shows).
  // One HEAD in flight: a second event while it is out is folded into it, no timer. A 413 or 415 retires the probe for
  // this open (the panel's `stopped`, per target); a network failure paints nothing and says nothing, since nothing the
  // reader sees has changed, and the next event asks again. While editing the probe stands down (the save's fence
  // refuses a stale save and offers its own Reload) and the editor's entry takes the bar with every other notice.
  // The listeners leave with the viewer by both exits (probeLive, dropProbe: the onKey idiom). Exact events throughout:
  // the reader's return, the answer, the landing.
  // The bar's raise waits out a press on the body ROW (the probe's answer, below): `main`, the row the bar is inserted above
  // (noteBar), so a raise moves the body AND the Comments aside beside or below it, and a press on either is held (the
  // review's round 4: round 3 held the body alone, and a press on a card's head, on Resolve or a drag in the reply box in the
  // aside while the HEAD landed had the control move out from under the pointer; the click was lost and the drag selected
  // nothing). Its own hold, since the landing's (`hold`, on the card since the PR review's round 1, the body before) parks one
  // run at a time and a raise must never displace a parked landing.
  const raiseHold = pressHold(main);
  // A landing the card's hold parked under the press now under way (fetchFile's land), null when none is: settled once it has run,
  // was replaced or threw. The raise's parked run reads it at the release and runs after it, so a landing parked under the same
  // press runs first and the raise's guards read the file it brought, whichever hold heard the press first (the review's round 5:
  // the row's hold, on `main`, heard the press before the body's, both in the capture phase, so its release listener was installed
  // first and its parked run went on the zero timer first; the raise then inserted the bar over the old mtime and the landing's
  // settle removed it in the next task; before round 4, with both holds on the body, the landing's ran first by the same listener
  // order; since the landing's hold moved to the card, the card's ancestor listener hears the press first, and the order below
  // holds by the settle, not by the listeners).
  let parkedLanding: Promise<void> | null = null;
  const noteParkedLanding = (p: Promise<void>): void => {
    const settled = p.then(() => undefined, () => undefined);
    parkedLanding = settled;
    void settled.then(() => { if (parkedLanding === settled) parkedLanding = null; });
  };
  let probeOut = false;                        // a HEAD is out: the next event is folded into it
  let probeStopped = false;                    // a 413/415 retired the probe for this open
  let diskBar: { el: HTMLElement; btn: HTMLButtonElement; under: string; asked: number; held: boolean; ring: boolean; words: string } | null = null;   // the bar, the mtime it was raised under, its own ask's fetch, whether the bar held the keyboard at its Reload's click and whether with the ring, and its words (CHANGED_ON_DISK or DELETED_ON_DISK, for the editor's exit to re-raise)
  const diskBarUp = (): boolean => diskBar !== null && note === diskBar.el;   // still the card's notice (enterEdit or a later notice may have taken it)
  // The bar's Reload held the keyboard when a click put it there (a click focuses a button; Enter on the focused button is
  // the same press), and the landing removes the bar: the body takes the keyboard then (takeKeyboard, the brief's call-site
  // list names the button), so PageDown reads on after the Reload; a keyboard held anywhere else is left where it is. Who
  // held it is read AT THE CLICK, before the acknowledgement disables the button: a browser drops the focus off a control
  // the moment it is disabled (Chromium, synchronously, to the document's body), so a read at the landing found the body
  // and handed nothing over, and PageDown after every Reload scrolled nothing until a click (the review's round 1; the
  // consolidation's read at the landing modelled a removal's fixup the click never reached). A failed Reload removes
  // nothing and re-arms the button, and puts the keyboard back on it when the click had it and nothing holds it since
  // (rearmDiskBar). The hand-over here runs through takeKeyboard's gate, so a box the reader moved to during the GET's flight,
  // in this document or in the chat frame beside a Files pane, keeps the keyboard (the review's round 2).
  const dropDiskBar = (): void => {
    if (diskBarUp()) {
      const held = diskBar!.held || diskBar!.el.contains(document.activeElement);
      const ring = diskBar!.ring || ringOf(document.activeElement);   // the click's record, or a holder still in the bar (takeKeyboard, the ring)
      diskBar!.el.remove(); note = null;
      if (held) takeKeyboard(ring);
    }
    diskBar = null;
  };
  const raiseDiskBar = (words: string): void => {
    if (diskBarUp()) return;                   // one bar: a second move, or a deletion, while it stands replaces nothing
    const bar2 = noteBar(words);               // CHANGED_ON_DISK, or DELETED_ON_DISK for a 404 (the probe reads the verdict)
    const re = el("button", "fileview-btn fileview-err-act") as HTMLButtonElement;   // on the words' line (.fileview-err-act), not the refusal pane's block Download (the review's round 5: the bar was two rows, 89 px)
    re.type = "button"; re.textContent = "Reload";
    re.title = "Read the file as it is now; your place is kept";
    re.addEventListener("click", () => {
      if (editing || !diskBar || diskBar.btn !== re || re.disabled) return;
      diskBar.held = bar2.contains(document.activeElement);   // who holds the keyboard, before the disable below drops it (dropDiskBar, the header)
      diskBar.ring = diskBar.held && ringOf(document.activeElement);   // and whether with the ring (Enter on the Tab-focused button), for the landing's hand-over
      re.disabled = true; re.textContent = "Reloading";   // the acknowledgement: the body shows nothing new until the landing (the place rule)
      fetchFile();
      diskBar.asked = fetchSeq;                // this ask's landing clears the bar whatever mtime it brings
    });
    bar2.appendChild(re);
    diskBar = { el: bar2, btn: re, under: mtimeNs, asked: 0, held: false, ring: false, words };
  };
  // A landing that stands (fetchFile, text or media), `my` its fetch: the bar goes when the landed mtime differs from the
  // one it was raised under, or when the landing is the bar's own ask; another ask's landing under the same mtime (a GET
  // that was out before the write) keeps it, since the moved file is still not what shows.
  // The bar's own ask, or any fetch newer than it: fetchSeq is monotonic and a fetch a newer one overtook reads nothing and never
  // lands (fetchFile's `my !== fetchSeq`), so once the Comments panel's poll asks its own reload during the bar's flight the bar's
  // ask can land only through that newer fetch, whose bytes or failure are the bar's answer too (the review's round 2: the poll's
  // GET after a deletion met the 404 pane, and the bar stood over it with its button disabled at "Reloading" for the rest of the
  // open, every later focus HEAD returning on the standing bar).
  const ownAsk = (my: number): boolean => diskBar !== null && diskBar.asked > 0 && my >= diskBar.asked;
  const settleDiskBar = (my: number): void => {
    if (diskBar && (mtimeMoved(diskBar.under, mtimeNs) || ownAsk(my))) dropDiskBar();
  };
  // The bar's ask failed (the failure pane in the body says why): the button is armed again, so the bar is no dead end. The click's
  // keyboard, dropped by the disable, goes back on the re-armed button only while nothing holds it (keyboardIdle): a reader who
  // moved to a box during the flight, in this document or the chat's, keeps it (the review's round 2: the re-armed button took the
  // keyboard from the box, and the next Space fired Reload again).
  const rearmDiskBar = (my: number): void => {
    const d = diskBar;
    if (!d || !ownAsk(my) || !diskBarUp()) return;
    d.btn.disabled = false; d.btn.textContent = "Reload"; d.asked = 0;
    if (d.held && keyboardIdle()) d.btn.focus({ preventScroll: true });
    d.held = false; d.ring = false;
  };
  const probe = (): void => {
    if (takingKeyboard || probeOut || probeStopped || editing || !mtimeNs || !wrap.isConnected || document.hidden) return;   // takingKeyboard: a window focus the viewer's own body.focus() fired (takeKeyboard, above), not the reader's return
    probeOut = true;
    fetch(fileUrl(path, sid), { method: "HEAD", cache: "no-store" }).then((r) => {
      const v = headVerdict(r.status, r.headers.get("X-Romp-Mtime-Ns"));
      if (v.kind === "stop") { probeStopped = true; return; }
      if (v.kind !== "value" || editing || !mtimeNs || !wrap.isConnected) return;   // an unknown answer, or the world moved while the HEAD was out
      const moved = v.value;
      if (!mtimeMoved(mtimeNs, moved)) return;
      // A 404 is a deletion, not a change (the PR review's round 1), but only when the kernel says the file is gone: its 404 carries
      // REASON_HEADER, and REASON_MISSING alone means no regular file is at the absolute path (the PR review's round 2; the route
      // also answers 404 for a relative path the session's cwd moved from under, for one it can join to no cwd, and, through the
      // relay, for a detached host, the file still on disk in each, and, since the PR review's round 3, for an absolute path it
      // cannot stat, EACCES on a parent, the file possibly still there). Any other reason, or none (a kernel from before the
      // header), falls back to the change's words; Reload then paints the kernel's own pane for whatever the GET answers, and
      // re-arms.
      const words = moved === ABSENT && r.headers.get(REASON_HEADER) === REASON_MISSING ? DELETED_ON_DISK : CHANGED_ON_DISK;
      const was = mtimeNs;                       // the mtime the answer was compared against: the file the body shows
      // The raise waits out a press on the body row (raiseHold: the body and the aside). The mousedown that begins a drag in a
      // Files iframe that did not hold the page's focus is itself the window focus that ran this HEAD, and the bar is a row of
      // the card above that row, so a raise while the pointer was down moved the body under the press and the drag's selection
      // ended on other text (the review's round 3: with the Comments panel open the composer quoted the wrong passage; round 4:
      // a press in the aside was not held, and the card head under it moved before the release). The guards re-run at the
      // release for what moved while the raise was parked: a landing that brought a file, the editor's entry, the close; a
      // landing parked under the same press runs first, the raise waiting for its settle (parkedLanding; round 5). The guard is
      // that the body still shows the file the HEAD compared against (`was`): any landing since makes the HEAD's evidence stale,
      // whatever mtime it brought, and the next focus asks again (the review's round 6: a landing parked under the press that
      // brought a SECOND write, newer than the HEAD's answer, read as moved against that answer and raised the bar over the
      // newest file, where it stood until Reload; the trade, recorded in the plan: a parked landing that brought an OLDER mtime
      // than the HEAD saw, a GET served before a write the HEAD saw, stands the raise down too, and with the Comments panel open,
      // the one source of a parked landing, its poll re-asks within its interval).
      raiseHold.defer(() => {
        const go = (): void => { if (!editing && wrap.isConnected && mtimeNs === was) raiseDiskBar(words); };
        const landing = parkedLanding;   // a landing parked under the same press settles first, and the guards read the file it brought (parkedLanding)
        if (landing) void landing.then(go); else go();
      });
    }).catch(() => { /* a network failure: nothing the reader sees has changed; the next event asks again */ })
      .finally(() => { probeOut = false; });
  };
  const onWindowFocus = (): void => { probe(); };
  const onVisibility = (): void => { if (!document.hidden) probe(); };
  window.addEventListener("focus", onWindowFocus);
  document.addEventListener("visibilitychange", onVisibility);
  probeLive = () => { window.removeEventListener("focus", onWindowFocus); document.removeEventListener("visibilitychange", onVisibility); };

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
    // Over an empty file (zero rows under the EMPTY_FILE line, item 6) the notice still says the line is not in the file, in the
    // same one-line shape an offset open uses, and stops short of "showing the last line", since there is none (the Slice 7
    // review's round 1: a line open of an empty file said nothing while an offset open raised its notice).
    if (n > rows.length) noteBar("Line " + n + " is past the end of this file, which has " + rows.length + (rows.length === 1 ? " line" : " lines") + (rows.length ? "; showing the last line." : "."));
    if (!rows.length) return;
    (rows[Math.min(Math.max(0, n - 1), rows.length - 1)] as HTMLElement).scrollIntoView({ block: "center" });
  };
  let pendingLine: number | null = at !== null && "line" in at && at.line > 0 ? Math.floor(at.line) : null;
  // A source offset (an open's `{ offset }`; plans/markdown-viewer.md Slice 6, item 4): spent on the first text that lands
  // like `line`, and scrolled one frame after that paint, the heading landing's timing (the Rendered pairing below reads
  // the painted DOM). In the Rendered view the block holding the offset (the anchor map's block table, read as the
  // reader's place reads it: blockHolding) scrolls its first element to the centre, a block with no element of its own
  // (a comment) standing aside for the nearest that has one, a fold above it opened first as a heading's is; in the Raw
  // view the row at the offset, through the seam's own scrollToOffset. An offset past the end of the text lands on the
  // last block or row AND says so in the notice bar, the `line` rule's shape (CLAUDE.md, fail loudly: a silent landing on
  // the last block would read as the file's truth).
  const scrollToSourceOffset = (n: number) => {
    const src = viewText();
    if (src === null) return;
    // The view as the paint left it, mode()'s word, not the pressed button: over the rows a failed render fell back to (renderFell;
    // Slice 7 of plans/markdown-viewer.md, item 1) fmt.md still says "rendered" while the body holds code.hljs rows, and a read of
    // the button took the Rendered branch, found no .fileview-md and returned with nothing scrolled and a notice naming a block
    // (the review's round 1: the person's own click landed at the top in silence).
    const rendered = ctx.mode() === "rendered";
    if (n > src.length) noteBar("Offset " + n + " is past the end of this file, which has " + src.length + (src.length === 1 ? " character" : " characters") + "; showing the last " + (rendered ? "block." : "line."));
    const at = Math.min(n, src.length);
    if (!rendered) { ctx.scrollToOffset(at); return; }
    const md = body.querySelector(".fileview-md");
    if (!md) return;
    const spans = sourceBlockSpans(src);
    if (!spans.length) return;
    const held = blockHolding(spans, at);
    const b = held < 0 ? spans.length - 1 : held;   // past the last block's text (a trailing blank line): the last block
    let target: Element | undefined;
    let own = false;                                 // the element is the offset's OWN block's, not a stand-in for a block with none (a comment)
    for (let k = b; k >= 0 && !target; k--) { target = renderedBlockElements(md, src, k)[0]; own = k === b && held >= 0; }
    for (let k = b + 1; k < spans.length && !target; k++) target = renderedBlockElements(md, src, k)[0];
    if (!target) return;
    revealFragmentTarget(target);                                                                          // the folds above the block (a `#` link's revealing steps)
    if (own && target.localName === "details" && !target.hasAttribute("open")) target.setAttribute("open", "");   // …and the block that IS a fold (a callout is one block): the offset names its content, which the shut summary hides (the review's round 2); a stand-in's fold stays as authored, since the offset names a comment after it or the trailing blank line, not its content (round 3)
    target.scrollIntoView({ block: "center" });
  };
  let pendingOffset: number | null = at !== null && "offset" in at && at.offset >= 0 ? Math.floor(at.offset) : null;
  // The open's target and its keyboard at the first text landing (items 4 and 1), over a body with a box: the line's row centred at
  // once, the offset's block or row one frame later (scrollToSourceOffset's comment), a heading a hidden paint's frame left pending
  // (renderBody's own spendHeading runs at each paint that can land one), then the body takes the keyboard (keyboardOnLanding, spent
  // once). Under a body with no box (the pane's document display:none while the fetch was in flight: a phone's tab swap, the pane
  // toggled off) every scrollIntoView moves nothing and body.focus() is a no-op, so each stays pending for the width hook's repaint
  // at the show, which calls this again (the review's round 5: the target was spent over the zero layout, the note stood at its top
  // with no notice once the pane showed, and nothing held the keyboard until a click; item 3's remembered place has had the same
  // guard since round 4, landRemembered). A reflow after the spends runs nothing here: the pendings are null and the keyboard taken.
  // A picture or a PDF frame has no rows, no blocks and no sections, so a target on one is judged at its first paint with bytes,
  // over a body with a box, and named in the notice bar: the heading as the text branch names it (the review's round 3:
  // `figs/a.svg#layer1` and `docs/report.pdf#page=3` opened silently at the top; the PDF viewer's own page grammar is outside the
  // plan's scope, so `page=3` is a section the file lacks), and the line and the offset in the same one-line shape (the PR review's
  // round 1: both were dropped in silence, the text arm below being their only spender, and the media landing spent the keyboard
  // take without the box guard, so under a hidden pane nothing held the keyboard at the show). Nothing scrolls: there is nothing to
  // open at. A media paint has no width repaint of its own to wait for, so the show's repaint calls landMedia for a media body too.
  const spendOnMedia = (): void => {
    const kind = isPdf ? "a PDF" : "a picture";
    if (pendingLine !== null) { const n = pendingLine; pendingLine = null; noteBar("No line " + n + " in this file: it is " + kind + "."); }
    if (pendingOffset !== null) { const n = pendingOffset; pendingOffset = null; noteBar("No offset " + n + " in this file: it is " + kind + "."); }
    if (pendingHeading !== null) {
      const h = pendingHeading; pendingHeading = null;
      const name = h.replace(/^#/, "");
      let shown = name; try { shown = decodeURIComponent(name); } catch { /* a stray %: named as written */ }
      noteBar('No section named "' + shown + '" in this file.');
    }
  };
  const landMedia = (): void => {
    if (unmeasurable()) return;              // the same guard as the text landing's: a body with no box lands nothing, and the show's repaint calls again
    spendOnMedia();
    keyboardOnLanding();
  };
  const landTarget = (): void => {
    if (unmeasurable()) return;
    if (pendingLine !== null) { const n = pendingLine; pendingLine = null; scrollToLine(n); }
    if (pendingOffset !== null) { const n = pendingOffset; pendingOffset = null; requestAnimationFrame(() => { if (wrap.isConnected) scrollToSourceOffset(n); }); }
    if (pendingHeading !== null && (!isMd || fmt.md === "rendered")) spendHeading();
    keyboardOnLanding();
  };
  // The landing runs through the hold's defer, whose promise settles with the run (actions.ts pressHold): a run the hold
  // parks goes on a zero timer at the release, outside the fetch's chain, and a throw from it (after the landing has taken
  // the new mtime) reached nobody in round 1: an uncaught page error, the old text standing under the new mtime with no
  // error row, while the same throw from an immediate landing reached the `.catch` below. The promise rejects with the
  // parked run's throw into that same `.catch` now (review round 2, 2026-09-08), a parked run a later landing replaced
  // resolves with nothing painted, which is what the hold's header says of an overtaken landing. Since Slice 7 of
  // plans/markdown-viewer.md (item 1) the common throw never gets that far: a throw from the block's build or the swap is
  // caught inside renderBody's own try, parked or immediate, which paints the RENDER_FELL line over the text's Raw rows
  // (file-view-landing-throw-browser.test.ts drives both landings). What still rejects into the `.catch` below is a throw
  // from the fallback itself or from the passes after the try that can throw through (the folds' restore, the width stamp,
  // the Outline's sync, the seat): a bug, not a file. Never a hook's own throw: fireRendered runs each hook in its own
  // try and swallows it (the review's round 2 corrected this list, which named the hooks).
  const fetchFile = () => {
    const my = ++fetchSeq;
    type Verdict = { isText: boolean; notUtf8: boolean; mtimeNs: string; isImage: boolean; isPdf: boolean; isSvgImage: boolean; bytes: number | null };
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
    // `parked`: the hold parks this landing under a press now under way, read once before the defer and handed to the run, which
    // learns from it whether it ran at once or at a release (the Outline's re-open below reads it; the PR review's round 2).
    const land = (run: (parked: boolean) => void): Promise<void> | void => {
      if (!stands()) return;
      const parked = hold.held();
      const p = hold.defer(() => run(parked));
      if (parked) noteParkedLanding(p);   // parked under a press: the bar's raise parked under the same press waits for this one's settle (parkedLanding)
      return p;
    };
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
      v = { isText: false, notUtf8: false, mtimeNs: "", isImage: false, isPdf: false, isSvgImage: false, bytes: null };
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
      // The Latin-1 verdict keys on the header's VALUE with the text type, never on !isText: an image or a PDF carries no
      // X-Romp-Text-Utf8 at all (tests/test_kernel_preview.py pins that absence), and an old kernel that sends none leaves
      // isText true with Edit off through !mtimeNs. The text landing below says so in the note bar (LATIN1_NOTICE;
      // plans/markdown-viewer.md Slice 7, item 5).
      v.notUtf8 = ct.startsWith("text/plain") && r.headers.get("X-Romp-Text-Utf8") === "0";
      // The served body's byte count, the kernel's Content-Length (tests/test_kernel_preview.py pins it as the body's length, 0 for
      // an empty file), read for the one question the decoded text cannot answer: whether a text that reads "" was a BOM alone
      // (BOM_ONLY_FILE; the browser's decode strips the one U+FEFF the kernel serves). Null when the header is absent or not a
      // number: the empty file's words then, as before.
      const len = r.headers.get("Content-Length");
      v.bytes = len !== null && /^\d+$/.test(len) ? Number(len) : null;
      // THIS fetch's flags choose the body's shape; the viewer's own isImage/isPdf still say what shows now
      const { isImage, isPdf } = v;
      return isImage || isPdf ? r.blob() : r.text();
    }).then((t) => land((parked) => {   // parked while a pointer is pressed over the card; the guards re-run at the release
      if (!stands()) return;                                    // closed, replaced or overtaken while it was parked
      if (editing) { refetchAfterEdit = true; return; }         // the editor holds the truth; read again when it ends
      const got = v!;                                           // set with the headers above; a failure never reaches here
      isText = got.isText; notUtf8 = got.notUtf8; mtimeNs = got.mtimeNs; isImage = got.isImage; isPdf = got.isPdf; isSvgImage = got.isSvgImage; textBytes = got.bytes;
      settleDiskBar(my);                                        // the changed-on-disk bar goes with the landing that brings the moved file (or its own ask's)
      if (!notUtf8) dropLatin1Line();                           // a UTF-8 answer (or a media one) drops a Latin-1 line a previous landing raised: Edit is back, or the file is no text at all (Slice 7, item 5)
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
        landMedia();                             // the open's first paint (a picture, a PDF frame): the target named and the body taking the keyboard, over a body with a box
        return;
      }
      text = t;
      // A landing the hold parked under a press on the Outline BUTTON runs after the release's click, on the hold's zero timer, and
      // that click opened the popover: the paint below closes it (every paint does: its rows were read off the DOM the paint
      // replaces), so the click appeared to do nothing (the PR review's round 2). The popover is opened again after the paint, on
      // the landed body, its rows and its current row read afresh and the keyboard on it as the click left it. A landing that ran
      // at once (a plain reload, the panel's poll with no press under way) closes the popover as before: the reader did not just
      // ask for it. A landing parked under a press on a ROW finds the popover closed by the pick, and one parked under a press on
      // the button while the popover was up finds it closed by the toggle, so neither opens it again (file-view-outline.test.ts
      // and file-view-outline-browser.test.ts, the PR review's round 2 cases).
      const reopenOutline = parked && outline !== null;
      // the open's target: a line takes the Raw view for this open (unsaved: the preference stays), then the row; an offset the next frame
      if (pendingLine !== null && isMd && fmt.md === "rendered") fmt.md = "raw";
      renderBody();
      // A file the kernel decoded as Latin-1 says why Edit is off (plans/markdown-viewer.md Slice 7, item 5; open question 13):
      // one noteBar line, raised at every text landing that wears the "0" and BEFORE landTarget, so an open's own target notice
      // (the past-the-end line, raised inside landTarget; the offset and missing-section notices a frame later) takes the row
      // under the one-bar rule, being the answer to the person's own click. A reload's landing has no target and raises the
      // line again, after settleDiskBar above has dropped the changed-on-disk bar, so a Reload brings it back. Keyed on the
      // answer's header, never on the body or a timer; the one other raise is a format pick's, when its paint puts this text
      // back over a failure pane whose paint dropped the line (pickFormat; the review's round 3). A landing that finds the line
      // already standing with the same words (the Comments panel's poll-driven reload of the same file, the seam's reload)
      // leaves that element as it is (latin1LineStands): the bar is a role=status live region, so a fresh element with the
      // same words would be announced again by assistive technology at every reload (the review's round 1); the words are
      // unchanged, so nothing is said again. The disk bar's Reload drops its bar first (settleDiskBar), so that landing raises
      // afresh: the line's return is new information.
      if (notUtf8 && !latin1LineStands()) noteBar(LATIN1_NOTICE);
      landTarget();                              // the open's target (the line's row, the offset's block a frame later) and its keyboard, over a body with a box; a reload's landing has neither
      if (reopenOutline) openOutline();
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
      closeOutline();                                           // the popover's rows were read off the DOM the pane replaces (the paint closer's rule; the review's round 2: a popover open at a failed reload stood over the pane, the hidden button reading expanded)
      dropLatin1Line();                                         // a Latin-1 line a previous landing raised says the file can be read here; the pane says it could not be, so the line goes with the pane's paint, and a later "0" landing raises it again (the Slice 7 review's round 2), as does a format pick that puts the text back over the pane (pickFormat; round 3)
      body.replaceChildren(why);
      syncOutline();                                            // the pane holds no heading: the Outline button goes with the text it listed (the review's round 1: it stayed, and a click opened nothing)
      viewError = msg;                                          // the seam's error(): the pane's words, until the next content paint clears them (plans/markdown-viewer.md Slice 7, item 3; contract C1)
      fireRendered();                                           // the pane is a paint of the body like imgFailed's: fired AFTER the swap (a hook reading the body finds the pane) and before the re-arm (the re-arm reads the keyboard after the hooks), on every failure path, a first open's included, so a hook waiting on a reload hears it fail at the paint (before: no hook fired, and the Comments panel's loader stood until its 15 s deadline)
      rearmDiskBar(my);                                         // the changed-on-disk bar's own Reload failed: its button is armed again above the pane, AFTER the pane's paint: a keyboard the reader put on the old body's content during the flight (a link, a fold's summary), which that paint removed, then reads as nothing holding it and goes back on the button (the review's round 3: read before the paint, the link held it, the re-arm stood down, and the removal left the keyboard on the document's body)
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
  runLeave();                                          // a file viewer's place is remembered when a URL replaces it (RememberedPlace)
  editHooks = null;
  gitHooks = null;
  dropProbe();                                         // …and the old viewer's changed-on-disk probe (a URL view has no mtime to watch)
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
  let bytes = 0;                                       // the streamed read's byte count (readTextCapped): a text reading "" from more than zero bytes was a BOM alone (BOM_ONLY_FILE; Slice 7, item 6)
  let renderFell: string | null = null;                // the message of the throw the last text paint fell on (renderBody's catch, as the local viewer's); null once a paint stands
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
  // the text-size control the local viewer has (textSizeControl): a document opened from a link honours
  // the same stored size as a file on disk, and a step here is kept for both. The step is bracketed by this viewer's own
  // keptPlace and seat (declared below; the closure defers the reads to the press): a text-size step is a reflow the reader
  // did not ask to lose their place over, as in the local viewer (file-view-url-place-bottom-browser.test.ts).
  const textSize = textSizeControl(box, () => text !== null, (apply) => {
    const kept = keptPlace();                          // the reader's place before the text grows or shrinks around it
    apply();
    seat(kept);                                        // the same passage at the same height, as across the Rendered/Raw switch
  });
  acts.appendChild(textSize.wrap);   // the zoom glyph and its flyout (T367)
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
  const stampBodyWidth = watchBodyWidth(body);        // the body's content width, for a top-level table's cap (the sheets read --fv-body-w)
  textSize.bindWheel(body);                            // Ctrl/Cmd + wheel over the text steps the size
  // In-document links land on their heading (mdBlock's fv-anchor stamp): one delegated listener, the
  // local viewer's pattern. No fv-open here — a URL document's sibling links are made absolute and
  // the chat's own anchor delegate routes them.
  delegate(body, {
    "fv-anchor": (a, ev) => { ev.preventDefault(); scrollToFragment(body, a.getAttribute("href") || ""); },
    [GATE_ACT]: (g, ev) => { ev.preventDefault(); loadGate(g); },   // a gated figure's placeholder (figure-gate.ts): the same click as the local viewer's
  });
  gateKeys(body);                                      // and the same Enter and Space: the delegate reads clicks alone, and the placeholder is a role=button span
  closeHooks.push(armFigureLabels(body));              // a figure that fails to load says so beside itself, as in the local viewer (Slice 7, item 2)
  body.addEventListener("submit", (ev) => { ev.preventDefault(); });   // the local viewer's backstop (openFileView), same reason
  body.appendChild(loaderEl());                        // loader first; the fetch below replaces it
  box.appendChild(bar); box.appendChild(body);
  wrap.appendChild(box);
  document.body.appendChild(wrap);

  // The URL's own #fragment (`evidence.md#results`) lands after the FIRST RENDERED paint — once. A
  // Raw view has no heading ids, so a saved Raw preference does not SPEND the landing: it waits for
  // the Rendered toggle (review find on #958, 2026-09-07: landed was set before the mode check). A
  // render that fell to the Raw rows (renderFell; Slice 7 of plans/markdown-viewer.md, item 1) does
  // not spend it either: the healed Rendered paint lands it (the Slice 7 review's round 1).
  let landed = false;
  const landFragment = () => {
    if (landed) return;
    let hash = "";
    try { hash = new URL(href).hash; } catch { /* not a URL — nothing to land on */ }
    if (renderFell !== null) return;                   // the paint fell to the Raw rows (Slice 7, item 1): no section to land on; the healed Rendered paint tries again, the fragment kept
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
  // event reports the held scrollTop and changes nothing); no timers. The switch and a text-size step are the swaps this
  // viewer's place crosses: no reload and no aside, so a width change re-places nothing; a text-size step keeps the reader's
  // place as the local viewer's does (the bracket on textSizeControl above), and none of the local viewer's comments-panel
  // bookkeeping is needed here.
  let heldPlace: Place | null = null;
  let heldScrollTop = -1;
  const folds = foldKeeper(body);                      // the folds' state across the switch, as the local viewer keeps it (foldKeeper)
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
    textSize.sync();                                   // shown once the document's text is up
    if (text === null) return;                         // the loader holds the body until the bytes land
    perfTimed("paint", () => {                         // the whole pass, the place read to the seat, as one fileview:paint frame of the page's collector (perfTimed above)
      if (text === null) return;                       // never taken (the guard above): a let's narrowing does not reach into the closure
      folds.note();                                    // the folds under the view about to go
      const kept = keptPlace();                        // the reader's place under the view about to go (the held one across a clamp)
      // The build and the swap in one try, the local viewer's shape (plans/markdown-viewer.md Slice 7, item 1): a render that
      // throws paints the RENDER_FELL line and the document's text as Raw rows under it, the message recorded once that fallback
      // stands (fellMessage; the local viewer's header), and a throw from that fallback propagates over the previous paint.
      try {
        body.replaceChildren(fmt.md === "rendered"
          ? mdBlock(text, { kind: "url", href: loc })  // relative refs resolve against where it LIVES
          : codeBlock(text, parts.base, true));        // basename → langFor → markdown highlighting
        renderFell = null;
      } catch (err) {
        const fell = fellMessage(err);
        body.replaceChildren(renderFellLine(fell), codeBlock(text, parts.base, true));
        renderFell = fell;
      }
      if (text === "") body.prepend(bytes > 0 ? bomOnlyLine() : emptyFileLine());   // an empty document says so above its empty root (Slice 7, item 6): a document read through capped-read.ts can be ""; above the RENDER_FELL line too when the render fell (the local viewer's comment); one whose bytes were a BOM alone (the read counted them) says that instead (BOM_ONLY_FILE)
      folds.restore();                                 // each fold as the person left it, before the seat reads the heights
      if (fmt.md === "rendered") stampBodyWidth();     // a fresh root's tables take the width last reported, before the seat and the landing measure (the local viewer's order)
      shownText = text;
      seat(kept);                                      // the same passage at the same height across the Rendered/Raw switch, as in the local viewer
      landFragment();                                  // after the paint, and only a rendered one lands
    });
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
    text = got.text; bytes = got.bytes;
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
  // the acknowledgement: a glyph button says it in its tooltip and a busy dress (T367), a word button in its text
  if (btn.dataset.icon) {
    const was = btn.title;
    btn.title = "Downloading…"; btn.classList.add("fileview-busy");
    setTimeout(() => { btn.title = was; btn.classList.remove("fileview-busy"); }, 1500);
  } else {
    const was = btn.textContent;
    btn.textContent = "Downloading…";
    setTimeout(() => { btn.textContent = was; }, 1500);
  }
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
// render.ts's wrapCodeLines balance walk. A CR is such a newline too (RAW_ROW_SPLIT): hljs escapes markup
// characters alone, so a CR passes through its output and a span across one is re-opened on the next row.
function wrapNumberedHtml(html: string): string {
  const lines = html.split(RAW_ROW_SPLIT);
  if (lines.length && lines[lines.length - 1] === "") lines.pop();   // a trailing line ending is not a line
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
  const lines = text.split(RAW_ROW_SPLIT);
  if (lines.length && lines[lines.length - 1] === "") lines.pop();   // a trailing line ending is not a line
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
  linkifyFileText(code, path);   // the same pass on the gutter layout, which no caller in the viewer asks for (every call passes wrapLines)
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
// fragment, the URL one's fv-anchor links and the URL's own hash. Found, the target is REVEALED before the scroll
// (md-sanitize.ts revealFragmentTarget: every closed <details> on its ancestor path opened, a hidden="until-found"
// removed), the steps the browser's own fragment navigation takes and scrollIntoView does not: a heading, a footnote
// definition or an anchor inside a folded callout (`> [!type]-`, a closed details since Slice 4 of
// plans/markdown-viewer.md) was scrolled to nothing, with the fold still shut (the Slice 4 review).
/** `el`, or an ancestor of it below `root`, carries a plain `hidden` (not `until-found`, which a landing lifts): the element has no box. */
function underHidden(el: Element, root: Element): boolean {
  for (let n: Element | null = el; n && n !== root; n = n.parentElement) {
    const h = n.getAttribute("hidden");
    if (h !== null && h.toLowerCase() !== "until-found") return true;
  }
  return false;
}
/** A heading's words for the Outline's row: its text with each picture read as its alt text in place (an image has no text of its
 *  own, so `textContent` alone dropped a captioned figure's name). */
function headingWords(n: Node): string {
  if (n.nodeType === 3) return (n as Text).data;
  const e = n as Element;
  if (e.localName === "img") return " " + (e.getAttribute("alt") || "") + " ";
  if (e.hasAttribute(FIGERR_MARK)) return "";   // a failed figure's label (armFigureLabels) is the viewer's text, not the heading's: the row reads the alt alone
  return Array.from(n.childNodes).map(headingWords).join("");
}
let outlineOpens = 0;   // openOutline's count across the module, for the rows' ids
/** The fragment names an element of the note that sits under a plain `hidden` wrapper (underHidden): found, and with no box to land
 *  on, so an open at it says so instead of landing (HIDDEN_SECTION; the PR review's round 1). scrollToFragment's own lookup. */
function sectionHidden(box: HTMLElement, fragment: string): boolean {
  let frag = fragment.replace(/^#/, "");
  try { frag = decodeURIComponent(frag); } catch { /* a stray %: match the bytes as written */ }
  if (!frag) return false;
  const root = box.querySelector(".fileview-md") || box;
  const target = fragmentTarget(root, frag);
  return !!target && underHidden(target, root);
}
/** Lands the fragment's element at the top of the body: false when the body has no such element, or has it under a plain `hidden`
 *  wrapper, where scrollIntoView on the boxless element would move nothing (the PR review's round 1: the landing counted as done). */
function scrollToFragment(box: HTMLElement, fragment: string): boolean {
  let frag = fragment.replace(/^#/, "");
  try { frag = decodeURIComponent(frag); } catch { /* a stray % — match the bytes as written */ }
  if (!frag) return false;
  const target = fragmentTarget(box.querySelector(".fileview-md") || box, frag);
  if (!target) return false;
  if (underHidden(target, box.querySelector(".fileview-md") || box)) return false;   // no box to land on (sectionHidden names it)
  revealFragmentTarget(target);
  target.scrollIntoView({ block: "start" });
  return true;
}

// A fold's open or closed state across a paint. The front matter and a `[!type]-` or `[!type]+` callout render as a
// <details> (md-config.ts; Slice 4 of plans/markdown-viewer.md), and so does an author's own. Every text paint rebuilds the
// body from marked (renderBody's swap, both viewers), and a <details>' only state is the DOM, so every fold went back to
// what the source says (`[!type]+` open, everything else closed) on the Rendered/Raw switch, on a reload's landing, on
// the editor's take and handback and on a sibling's Reveal: a fold the person had opened to read shut again, one they had
// closed opened again, a fold a `#` click had just revealed (scrollToFragment, above) shut on the next paint, and the block
// under the eye changed height under the reader's place, 72px open to 39px closed (the Slice 4 review; ui/CLAUDE.md: an
// expand's state survives re-renders). Each viewer keeps one keeper: `note` reads every fold under the rendered box, in
// order, before the swap, and `restore` re-applies each state after it to the fold it was read from, found in two passes.
// The first pass matches a new fold to a noted one with the same class, summary text AND body text, in order; the second
// matches what is left by class and summary text alone, in order. For an unchanged text the first pass finds every fold
// by index. For a text a reload or an edit changed, a fold whose body a session rewrote while the person read it keeps
// its state through the second pass, and a fold that stands as it was keeps its own even when a fold of the same class
// and title was removed or inserted ahead of it: with class and title alone as the key, two `> [!note]- Same title`
// callouts, or two untitled folded callouts of one type (whose generated title is the type, the common Obsidian shape),
// shared one queue, so removing the first handed its state to the second, and a new one inserted ahead took the state of
// the fold behind it (the Slice 4 review, round 3). A fold whose title changed, or a new one, shows as authored. The
// first pass pairs an exact key only when it names AS MANY noted folds as new folds, the k-th new to the k-th noted: two
// folds identical in class, title and body (two `> [!note]- Todo` placeholders a template left) share a key the pass has
// nothing to tell them apart by. While their count stands, the twins pair in order and each keeps its own state, whatever
// a same-titled fold with a body of its own did around them: inserted or removed ahead of them, between them or after
// them, it pairs by title in the second pass or shows as authored. When their count changed, a session filled one in,
// added one or removed one, the whole key falls to the second pass and its order, whose k-th noted state of that title
// goes to the k-th new fold of that title. So the fold the person reads keeps its state through a fill anywhere (the
// count and the order stand, so every fold keeps its own state, the filled one included) and through a twin added or
// removed BEHIND it when the same write adds or removes no fold of its title ahead of it. A twin added or removed AHEAD
// of it shifts the states by one, the fold the person reads taking the state of the twin that stood where it now stands,
// or the authored state when none did (the last twin, with one added ahead of it): three identical `> [!note]- Todo`
// placeholders, the second open, the first deleted by a session, paint the new first (the fold the person was reading)
// shut and the new second open; and the open twin itself removed hands its open to the twin behind it, if any. Once the
// twins' count changed, the title queue holds every same-titled fold the first pass left unpaired, so a same-titled fold
// with a body of its own removed or added AHEAD of them in the same write shifts the states the same way, the number of
// twins ahead unchanged (the Slice 4 review, round 7). Three folds byte-identical in class, title and body give no
// content rule anything to decide on, so those are order-only cases, accepted (the Slice 4 review, round 6). Paired in
// the first pass anyway, as before round 4, the one fold still carrying the shared body took the queue's first state
// whichever fold that was, so the two placeholders swapped states when the person read the second while a session wrote
// into the first (the Slice 4 review, round 4). Round 4's rule, an exact key pairs only when it names ONE noted fold and
// ONE new fold, sent untouched twins whole to the second pass, where a same-titled fold inserted ahead of them took the
// first twin's state and every twin took the next one's, and one removed from ahead of them shifted the states the other
// way, so the twin the person read shut either way (the Slice 4 review, round 5). Order alone decides what content
// cannot: a twin added or removed ahead of the twin the person reads (above), the leftovers of an edit that both removes
// one same-titled fold and rewrites another's body, and a twin rewritten in the same write that inserts a same-titled
// fold, whose text change is the insertion's and reads as it (the likelier single edit, and the reading the round-3
// sentence above states). A Raw paint has no folds and neither reads nor writes, so the state read when the rendered
// view left stands until it is painted again. The state moves on the person's own clicks and the `#` reveal alone: no
// per-paint derivation, no timer (CLAUDE.md, cards move on new information). md-config-fold-state-browser.test.ts drives
// the gestures, the same-title reloads, the identical twins and the twins' same-titled neighbours included.
type Fold = { key: string; body: string; open: boolean };
function foldKey(d: Element): string {
  let summary = "";
  for (const c of Array.from(d.children)) if (c.tagName === "SUMMARY") { summary = c.textContent || ""; break; }
  return d.className + "\n" + summary;
}
/** The fold's body text: everything under it but its summary, which tells two same-titled folds apart. */
function foldBody(d: Element): string {
  let text = "";
  for (const c of Array.from(d.childNodes)) if ((c as Element).tagName !== "SUMMARY") text += c.textContent || "";
  return text;
}
function foldKeeper(body: HTMLElement): { note: () => void; restore: () => void } {
  let folds: Fold[] = [];
  const box = () => body.querySelector(".fileview-md");
  const exactKey = (key: string, text: string) => key + "\u0000" + text;
  return {
    note: () => {
      const md = box();
      if (md) folds = Array.from(md.querySelectorAll("details")).map((d) => ({ key: foldKey(d), body: foldBody(d), open: d.hasAttribute("open") }));
    },
    restore: () => {
      const md = box();
      if (!md || !folds.length) return;
      const now = Array.from(md.querySelectorAll("details"));
      const taken = new Set<Fold>();                     // noted folds the first pass matched
      const state = new Map<Element, boolean>();
      // pass 1: the same fold, by class, title and body text, when that exact key names AS MANY noted folds as new folds,
      // the k-th new paired with the k-th noted in document order; a key whose count changed (a fold filled in, added or
      // removed among folds identical in class, title and body) is left whole to pass 2 and its order
      const byExact = new Map<string, Fold[]>();
      for (const f of folds) { const k = exactKey(f.key, f.body); const q = byExact.get(k); if (q) q.push(f); else byExact.set(k, [f]); }
      const nowKeys = now.map((d) => exactKey(foldKey(d), foldBody(d)));
      const nowExact = new Map<string, number>();
      for (const k of nowKeys) nowExact.set(k, (nowExact.get(k) || 0) + 1);
      const paired = new Set<string>();                  // the exact keys with equal counts, read before the queues shrink
      byExact.forEach((q, k) => { if (nowExact.get(k) === q.length) paired.add(k); });
      now.forEach((d, i) => {
        const k = nowKeys[i];
        const q = byExact.get(k);
        if (!q || !paired.has(k)) return;
        const f = q.shift();
        if (!f) return;
        taken.add(f); state.set(d, f.open);
      });
      // pass 2: the leftovers by class and title, in order: a fold whose body an edit changed keeps its state
      const byKey = new Map<string, Fold[]>();
      for (const f of folds) { if (taken.has(f)) continue; const q = byKey.get(f.key); if (q) q.push(f); else byKey.set(f.key, [f]); }
      for (const d of now) {
        if (state.has(d)) continue;
        const q = byKey.get(foldKey(d));
        const f = q && q.shift();
        if (f) state.set(d, f.open);
      }
      state.forEach((open, d) => { if (open) d.setAttribute("open", ""); else d.removeAttribute("open"); });
    },
  };
}

// A gated figure's placeholder (figure-gate.ts; decision 8 of plans/markdown-viewer.md) activates from BOTH viewers'
// bodies the same way: the click through each body's own listener, and Enter or Space through gateKeys, installed once
// on the stable body (never on the placeholder, which every paint rebuilds; ui/CLAUDE.md, click-safe controls). The
// placeholder is a span with role=button and tabindex=0, so the browser synthesizes no click for its keys: without
// this listener the URL viewer, whose click is a `delegate` (actions.ts, clicks alone), showed a focusable button that
// ignored Enter and Space (the Slice 4 review). The restore is the acknowledgement.
function loadGate(g: HTMLElement): void { loadGatedHost(g.dataset.fvHost || "", document); }
function gateKeys(body: HTMLElement): void {
  body.addEventListener("keydown", (ev) => {
    if (ev.key !== "Enter" && ev.key !== " ") return;
    const g = gateOf(ev.target, body);
    if (!g) return;
    ev.preventDefault();
    loadGate(g);
  });
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

/** marked's HTML for `text` as the viewer parses it: marked.parse's three steps called one by one (its lexer, the per-call
 *  walkTokens, its parser, over a copy of the singleton's defaults as marked.parse copies them), so the token tree is in hand
 *  between the lexer and the walk, where an inline start tag with no end tag in its block becomes literal text
 *  (md-literal-tags.ts literalizeUnclosedTags, the rule the anchor map applies to its own lex of the same text in placeTokens;
 *  plans/file-review.md, decision 52), on THIS parse's tokens alone: the chat's md() parses the same singleton with marked.parse
 *  and renders as before. `walk` is the caller's per-call token walk, run after the rule and before the parser (mdBlock's collects
 *  the code tokens, runs the file kind's link hook and the defaults' walk, in that order); no walk, no walkTokens call. The
 *  return is the dirty HTML: the sanitizer (sanitizeMd) is the caller's step. A throw from the lexer or the parser reaches the
 *  caller as marked's own error, without the report-this sentence marked.parse appended to its message (fellMessage still cuts
 *  one). Exported for the test suites that stand a Rendered body in for the viewer's: they render through this one recipe, not
 *  through marked.parse alone, whose HTML for a block holding such a tag is not the viewer's (decision 52's review, 2026-09-19). */
export function viewerHtml(text: string, walk?: (token: Token) => void): string {
  const opts = { ...marked.defaults };
  const tokens = marked.lexer(text, opts);
  literalizeUnclosedTags(tokens);
  if (walk) marked.walkTokens(tokens, walk);
  return marked.parser(tokens, opts);
}
// Markdown rendered as the prose it means (the user 2026-08-09: Rendered is the default, Raw one click
// away). The file is arbitrary bytes off a disk and marked emits raw HTML verbatim, so, exactly like the
// chat's md() in render.ts, the output goes through the shared sanitizer (sanitizeMd, md-sanitize.ts)
// before it ever reaches the DOM: an <img onerror> or a javascript: href in a README must never run in
// the dashboard, and a README's <style>, form or fixed-positioned div must never reach the viewer's chrome.
// No catch here (plans/markdown-viewer.md Slice 7, item 1): a throw from marked, from the sanitizer or from any DOM pass
// below propagates to the caller, each viewer's renderBody, whose try around the build and the swap keeps the content as
// Raw rows under a line that says what happened (RENDER_FELL); the catch that lived here wrote the source into the box as
// one unannounced paragraph, and the link passes at the end ran on a render that stood and skipped the fallback, so both
// run on every render now.
function mdBlock(text: string, doc?: MdDocLoc): HTMLElement {
  const box = el("div", "fileview-md");
  const fences: Fence[] = [];                          // marked's code tokens in document order, for the fence pass's Copy (fence-source.ts)
  // A link's destination is put in the form the sanitizer keeps BEFORE the HTML exists (file-view-links.ts
  // viewerWalkTokens: `notes.md:7` reads as a scheme to DOMPurify, `file:///a.md` is a scheme it refuses, and an
  // anchor it strips is a label nothing can sort afterwards). Handed to THIS parse only: the marked singleton is
  // the chat's too, and the chat's anchors must not learn the viewer's forms. A walkTokens an extension put on
  // the defaults runs as well: per-call options replace, not compose. The link hook is the file kind's alone: a URL
  // document has no directory for `notes.md:7` to sit in, and its links resolve against the URL below. Every kind
  // collects the code tokens: the lexer expanded the note's leading tabs to spaces before it cut them, and the fence
  // pass below reads each fence's text back out of the note for its Copy button (fence-source.ts).
  const base = marked.defaults.walkTokens;
  // The parse is viewerHtml's (above): the lexer, the literal-tags rule, this walk, the parser. The walk runs unchanged and in the
  // same order it ran inside marked.parse.
  const dirty = viewerHtml(text, (t) => {
    if (t.type === "code") { const c = t as Tokens.Code; fences.push({ text: c.text, indented: c.codeBlockStyle === "indented" }); }
    if (doc && doc.kind === "file") viewerWalkTokens(t);
    if (base) void base.call(marked, t);
  });
  // The one sanitizer the chat's md() uses too (md-sanitize.ts): html + svg (a note's own inline SVG), no data-*
  // (a document's `<span data-act="stopRetrying">` would otherwise bubble to render.ts's document-level delegate
  // and interrupt the active session; review find on #958, 2026-09-07), and rules modelled on GitHub's for a
  // note's own HTML: no <style>, no form controls, ids and names prefixed user-content-, inline style reduced to
  // its colours, no background attribute (plans/markdown-viewer.md, Slice 1). The sanitized <body>'s children
  // are adopted as they are, no re-parse. The viewer's own stamps (the file kind's path and section links, the
  // URL kind's fv-anchor stamp) are set AFTER this sanitize, so they are unaffected and never prefixed; a section
  // link finds an author's id or name under the prefix (file-view-links.ts fragmentTarget). The heading ids are
  // the one stamp set INSIDE the call, as sanitizeMd's own pass (mintHeadingIds, below): after DOMPurify, so they
  // are never prefixed either, and ahead of the registered passes, since the math fill replaces a formula's
  // placeholder with KaTeX's glyphs and a slug read after it slugged those (`# Ratio $\frac{a}{b}$` minted
  // md-ratio-ba); read before it, the heading's text is the text as written, the TeX included, which is GitHub's
  // slug and the id the note's own links spell. One heading diverges from GitHub's slug, recorded as left in decision 52
  // of plans/file-review.md: one holding an inline start tag with no end tag in it (`## Results <b>`), which the rule
  // above renders as literal text, so the slug takes the tag's characters too (md-results-b), where GitHub reads the
  // tag as HTML (results).
  // `remoteRefs: "keep"`: the one sanitizeMd caller that keeps a paint reference to another origin (an svg's `fill="url(...)"`
  // and its kin) in the body. The sanitizer's paint pass removes one for every other caller (md-sanitize.ts); this body is
  // gated before the adoption instead (gateRemoteFigures, below, which moves the reference aside behind a click that names
  // its host and restores it), and a strip here would delete what that click restores.
  const clean = sanitizeMd(dirty, mintHeadingIds, { remoteRefs: "keep" });   // the sanitized <body>: DOMPurify's own document's, which never loads (below)
  // Fenced blocks: highlight only a language the fence NAMES and this bundle registers (the same no-guessing rule as
  // langFor; an unnamed block stays plain rather than being painted at random). Then, for EVERY fence, named or not, the
  // chat's own dress (code-block.ts): the per-line rows that number the lines and make a soft-wrap read distinctly from a
  // real newline, and the Copy button. Copy copies the fence's text AS THE FILE HOLDS IT (fence-source.ts, off the code
  // tokens the parse collected): the raw text captured here is read before the rows drop the newlines, but after marked's
  // lexer turned the file's leading tabs into four spaces each, so a Makefile recipe copied from the rendered text pasted
  // back with spaces; a fence the module does not find in the file copies the raw text as before.
  // The math fill's source fallback (a code element wearing md-math-src, math.ts; spelled, not imported, since this module
  // carries no KaTeX) is not code: it keeps the Copy button and nothing else, as in the chat's highlight().
  // The pass runs HERE, on the sanitizer's body, before the figure chain below (2026-09-20), because it is the one pass that
  // re-parses markup: wrapCodeLines (code-block.ts) serializes each code element through innerHTML and parses it back, and its
  // line splitter carries only <span> tags across a newline, so an author's raw multi-line fence `<pre><code><svg>` / `<image
  // src="...">` / `</svg></code></pre>` comes back with the image outside its svg, where the HTML parser makes it an HTML <img>.
  // The chain reads src and srcset on an img and never on an svg image (figure-gate.ts FETCH_ATTRS.image is href and xlink:href),
  // so with this pass after the adoption the img was created in the live document after the chain had judged the svg, and its src
  // or srcset fetched from the unlisted host in Chromium, Firefox and WebKit with no click (the fourth scene of
  // file-view-figures-gate-adopt-browser.test.ts: red with this pass over `box` after the adoption, green here, measured
  // 2026-09-20). Before the chain, the chain judges what the re-parse created, once; a placeholder placed before this pass was
  // repeated by the line splitter, three for one gated svg. What the re-parse in body makes of every element the sanitizer keeps
  // inside an svg, and which of those fetch, is the namespace table under "The fence hole" in the plan section the chain block
  // names: `image` alone becomes a fetching element the chain judges through other attributes (an HTML img, src and srcset); a
  // nested `svg` stays an svg, its paint references judged by paintRefs. The same move corrected a second product of the re-parse:
  // an svg <a xlink:href> split across lines in such a fence comes back an HTML <a> whose xlink:href is a plain attribute, and
  // under the old order that anchor was followable for the reason the image leaked, the fold below (`a[*|href]`) and
  // linkMarkdownAnchors having stamped href and class on the svg anchor before the re-parse copied them into the HTML <a> it made;
  // judged after the re-parse it has no href and still carries the plain xlink:href, which the fold below (`a[*|href]`, a
  // namespaced match) does not select, and linkMarkdownAnchors (file-view-links.ts) marks it dead (fv-dead, the title saying why)
  // whether or not the author gave it an id or a name: the module exempts an href-less anchor target (an author's name or id,
  // never a link) from the dead dressing, and the split anchor with an author's id sat in that exemption unclassed and untitled,
  // painted in the link ink by the sheet's bare `.fileview-md a` rule and doing nothing on a click, a silent dead link in the
  // three engines (the fork PR review's round 2, findings correctness-2, extra7-1 and tests-4, 2026-09-20; the mark is keyed on
  // that attribute and not on the fence, so an author's HTML anchor spelled with xlink:href in prose, which the sanitizer keeps
  // with the attribute plain and no href, is marked too, and the exemption for a target carrying no xlink:href is unchanged; the
  // sixth case of the same leg holds the three shapes, red for the id-bearing one at the head before the mark), so a link inside a
  // code fence stopped being live and says so, which is what every other link inside a fenced code block already does, its markup
  // shown as text; an svg anchor on one line keeps its namespace and folds as before (measured 2026-09-20 in the three engines by
  // the fork PR review's verification, at the moved head and at a copy with the pass moved back). The Copy button (code-block.ts
  // addCopyBtn) is created in the live document, appended into this body's <pre> and adopted with it below; its listeners ride
  // both adoptions, and the same leg clicks each fence's button for real in the three engines.
  const copySources = fenceCopyQueue(text, fences);
  clean.querySelectorAll("pre code").forEach((node) => {
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
  // The figure chain runs HERE, on the sanitizer's body, BEFORE its nodes are adopted into `box` (2026-09-20). That body is
  // DOMPurify's (md-sanitize.ts sanitizeMd, RETURN_DOM): its _initDocument parses the markup with `new
  // DOMParser().parseFromString`, or into `implementation.createDocument` when that fails, and either document has no
  // browsing context (`defaultView` is null), so nothing in it loads whatever attributes its elements carry; the math fill
  // has always run there. `box` is the LIVE document's, and WebKit starts an <img>'s fetch synchronously the moment the
  // element's node document becomes one with a render tree (adoption is enough; a place in the tree is not needed), so
  // with the chain after the adoption the bytes had left for the unlisted host by the time the gate's placeholder said
  // "Click to load", and a figure of the file's folder was requested against the PAGE, as the attribute read before
  // rewriteFigureSrcs repointed it, and then again through /file. In Chromium and Firefox the servers' logs held no line
  // for either of those <img> figures before the chain ran (measured at the base, 2026-09-20, by the first leg named
  // below). An inline svg's <image> is loaded by another path, and there the gate held in Chromium alone: Firefox requested
  // a gated svg image, in either spelling, while its placeholder stood when the chain's work between the adoption and that
  // element's strip was long (the second leg's 3000-paragraph note, both figures, 3 of 3 runs; 400 plain paragraphs, 1 of 3;
  // every count is under "Run counts, the svg vectors" in the plan section named below; measured at the base by the second leg
  // named below), and WebKit requested the `xlink:href` spelling in every run and the `href` spelling in none. So the
  // kernel-served pages (the dashboard, in Safari and in Firefox, and the iOS web app, which is the same page in Safari's
  // engine) were reachable, the VS Code panes not (their CSP names no remote img-src; found by the review of the
  // link-navigation follow-on, 2026-09-20; file-view-figures-gate-adopt-browser.test.ts, an HTML img in three scenes and the
  // fence re-parse in a fourth, and file-view-figures-gate-adopt-svg-browser.test.ts, two inline svg images at the end of a
  // long note, read real servers' request logs in all three engines, and file-view-figures-gate-adopt.test.ts executes this
  // order under plain node, where those legs skip; the section "Fix: the gate before adoption (2026-09-20)" of
  // plans/markdown-viewer.md records the hole, the instrument and the scope). The rule this block keeps: every pass of mdBlock
  // that sets, repoints, moves or creates a fetching element runs before the adoption (the hooks renderBody runs after mdBlock
  // returns wrap, move or label elements the chain has judged, inside the live document, and set no fetching attribute; the plan
  // section names them). The fence pass (above) is the one pass
  // that re-parses markup, so it runs before this block and this block judges what its re-parse creates (its comment says
  // what that is). The passes after the adoption write a video's style, a list item's class, anchors' attributes (class,
  // title, data-*, target, rel, tabindex, role, an href set, resolved or removed) and new anchors and spans in place of the
  // prose's and the code blocks' text nodes, and none re-parses: after the adoption line this function, and every module a pass
  // after it reaches (the callees' modules and their imports, derived from the code), holds no write of innerHTML or outerHTML
  // and no insertAdjacentHTML, insertAdjacentElement, createContextualFragment, DOMParser, document.write, setHTML,
  // setHTMLUnsafe, parseHTMLUnsafe or template element; file-view-seam.test.ts derives that population from the
  // comment-stripped code (its RE_PARSE pattern) and pins it, so a new such site after the adoption is red there until it is
  // judged.
  if (doc && doc.kind === "url") {
    // Every attribute a figure fetches through resolves against the document (resolveFigureRefs, below): this arm read
    // `img[src]` alone, so a relative `srcset` candidate, a video's `src` or `poster`, an audio's, a `source`'s or a
    // track's `src` in a URL document stayed relative and the browser resolved it against the PAGE, fetching the
    // dashboard's directory instead of the document's and 404ing, the gap rewriteFigureSrcs closed for the file kind
    // (the Slice 4 review, round 2).
    resolveFigureRefs(clean, doc.href);
    // Decision 8 for a URL document: the document's own host loads on open beside the gear's list; every other host
    // is gated behind a click that names it (figure-gate.ts; the same placeholder, restored by the same action).
    let own = "";
    try { own = new URL(doc.href, document.baseURI).hostname; } catch { /* an unparseable location: the list alone */ }
    gateRemoteFigures(clean, document.baseURI, [own]);
  } else if (doc) {
    // Figures on the session's disk: re-pointed at the kernel's /file route by rewriteFigureSrcs (below), which
    // keeps the authored src in `data-fv-src` for the comments panel's embed matching and joins the path the way
    // every other reader of an embed's destination does (a relative src under the file's directory, an absolute
    // one as itself, `..` left to the kernel), so the picture shown is the file the poll watches.
    rewriteFigureSrcs(clean, doc.path.slice(0, doc.path.lastIndexOf("/") + 1), doc.sid);
    // Then decision 8 (plans/markdown-viewer.md; figure-gate.ts): a figure whose source is on a host the gear's list
    // does not name, and that the person has not loaded in this document, is wrapped in a placeholder naming the host
    // and fetches nothing until the placeholder is clicked. The kernel's own route, being the page's origin, is never
    // gated, so a file's own attachments load on open; the list is read at every paint (loadSettings inside), so a
    // change in the gear reaches the next paint, and an open document through the settings listener the gate installs.
    gateRemoteFigures(clean, document.baseURI);
  }
  // Adopted as they are, no re-parse here or after (the fence pass's re-parse ran above, before the chain), every fetching
  // attribute gated or repointed above, so the adoption starts no fetch to an unlisted host and none at a pre-rewrite URL, in
  // any engine; what it does start is the fetch of every figure left with a live attribute, the folder's through /file and an
  // allowed host's as written (the legs' logs: no line for a gated host, one line through /file for the folder's figure).
  box.replaceChildren(...Array.from(clean.childNodes));
  // A pixel-sized <video> keeps the author's shape (keepVideoShape, below): the sheets give it `height: auto` so it
  // shrinks in ratio with the column, and the browser's own `aspect-ratio: auto W / H` would hand that ratio to the poster.
  keepVideoShape(box);
  // A task item wears GitHub's class (Slice 3 of plans/markdown-viewer.md): marked emits the checkbox as the li's first
  // child with no hook on the li (inside its first paragraph in a loose list), and the sheets' `li.task-list-item` rule
  // drops the bullet that sat beside the box and pulls the box into the gutter. After the sanitize, and only for the
  // disabled checkbox the sanitizer's post-pass leaves (every other input is removed there), and only for a checkbox that
  // is the item's FIRST NODE: :first-child counts elements alone, so a checkbox an author's raw HTML puts after the item's
  // text matches the selector, and the previousSibling check leaves it, and its item's bullet, where the file put them.
  // An author who writes the class on an li of their own gets the same bullet-less item GitHub would give them.
  box.querySelectorAll('li > input[type="checkbox"]:first-child:disabled, li > p:first-child > input[type="checkbox"]:first-child:disabled').forEach((input) => {
    if (input.previousSibling) return;                 // text before the box: an author's checkbox mid-item, not a task item
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
    // A URL document's links resolve against the document too (its figures did above, before the adoption).
    box.querySelectorAll(LINK_SEL).forEach((node) => {
      const a = node as HTMLElement | SVGElement;
      const href = linkHref(a);
      if (!href || href.startsWith("#") || /^[a-z][a-z0-9+.-]*:/i.test(href)) return;   // in-document, or already absolute
      // Absolute now, so the chat's document-level anchor delegate sees a scheme: a same-origin
      // .md target opens in this viewer (isMarkdownUrl), everything else in a new tab.
      a.setAttribute("href", resolveDocRelative(href, doc.href));
    });
  }
  if (doc && doc.kind === "file") {
    // A file on the session's disk: its links are sorted by file-view-links.ts (linkMarkdownAnchors). A link to the
    // web opens a NEW tab: the viewer lives inside the chat pane's document, and letting a README link navigate it
    // away would silently eat the chat until a reload. A link whose target is a file relative to this one becomes a
    // path link that opens THAT file in the viewer (its `#fragment` or `:line` riding along); a section link
    // (`#results`) is the viewer's scroll; a target the sanitizer removed is a dead link that says why. The module
    // walks every `a`, the SVG anchor included (its xlink:href is a plain href by now, above), and writes each
    // attribute as one, so an SVG link is stamped like an HTML one.
    linkMarkdownAnchors(box, doc.path);
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
  // URLs and paths written in the prose and the code blocks, after the highlight rewrote the blocks' markup
  // (a pass before it would be undone). marked already made the prose's URLs anchors; text inside one is skipped.
  if (doc && doc.kind === "file") linkifyFileText(box, doc.path);
  return box;
}

/** Every heading gets an id first: marked 12 emits none, so a document's own `[top](#evidence)` had nothing to land
 *  on. GitHub's slug of the heading's text (headingSlug, made unique in order by uniqueSlugs), and PREFIXED `md-` on
 *  purpose: an unprefixed id="tabs" would dress a heading in the chat page's #tabs CSS and shadow
 *  getElementById("tabs") for the page's own controls. Both modes, every caller, before the anchors are sorted: a
 *  section link is live when its target is a heading, an element with that id or a named anchor, each under the
 *  sanitizer's user-content- prefix (file-view-links.ts fragmentTarget reads all three). Run by sanitizeMd as
 *  mdBlock's own pass, on the sanitized body (so SANITIZE_NAMED_PROPS never prefixes these ids) and BEFORE the
 *  registered passes (md-sanitize.ts): the math fill is one of those, and it replaces a formula's placeholder, whose
 *  text is the TeX as written, with KaTeX's glyphs, whose text is layout order (a fraction's denominator before its
 *  numerator, a U+200B strut). A slug read after the fill gave `# Ratio $\frac{a}{b}$ and energy $E=mc^2$` the id
 *  md-ratio-ba-and-energy-emc2, so the note's own `[see](#ratio-fracab-and-energy-emc2)` and a `[[#Ratio ...]]`
 *  wikilink rendered dead on the Files pane and the feed the moment Slice 4 brought the fill to their bundles (the
 *  chat page's viewer had it before); read before it, the slug is GitHub's, md-ratio-fracab-and-energy-emc2, as the
 *  Files pane minted it while it had no fill (md-config-fragment-landing-browser.test.ts). A heading holding an inline
 *  start tag with no end tag in it is slugged with the tag's characters, which the literal-tags rule rendered as text
 *  (`## Results <b>` mints md-results-b, GitHub's slug being results): decision 52 of plans/file-review.md records that
 *  divergence as left. */
function mintHeadingIds(root: ParentNode): void {
  const heads = Array.from(root.querySelectorAll("h1, h2, h3, h4, h5, h6")) as HTMLElement[];
  const slugs = uniqueSlugs(heads.map((h) => headingSlug(h.textContent || "")));
  heads.forEach((h, i) => { h.id = "md-" + slugs[i]; });
}

/** The authored candidates of a srcset rewriteFigureSrcs rewrote, kept on the element beside the rewrite (the label of a figure
 *  that failed names the candidate the browser asked for by them, failedSource). */
const FV_SRCSET = "data-fv-srcset";
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
 *  it a page-origin URL, and a region could be drawn on a broken-image box over a figure the person never saw; since
 *  Slice 7 a figure that fails to load wears a label naming its source beside the img, armFigureLabels below).
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
  // Every attribute a figure fetches through (figure-gate.ts figureRefs; Slice 4 of plans/markdown-viewer.md): an img's
  // src and srcset, a `<source>`'s src and srcset (inside a picture, a video or an audio), a video's src and poster, an
  // audio's and a track's src, and an inline svg's `<image>` or `<feImage>` href, SVG 1.1's `xlink:href` spelling
  // included (the feImage arm is a guard for a wider sanitizer profile: MD_PURIFY drops filter primitives today, so none
  // reaches this walk in the product). Before this the rewrite read `img[src]` alone, so `<video src="clip.mp4">` and `<audio src="a.mp3">` in a
  // file were fetched from the PAGE's origin and 404'd, exactly as `![](plot.png)` once did. A srcset is rewritten
  // candidate by candidate, its descriptors kept (`1x`, `100w`); the authored spelling stays in `data-fv-src` for the
  // img's src alone, the one attribute the comments panel pairs an embed by, and in `data-fv-srcset` (FV_SRCSET) for a
  // rewritten srcset, the img's or a `<source>`'s, so a failed figure's label can name the candidate the browser asked for
  // as the author wrote it (failedSource; Slice 7 of plans/markdown-viewer.md, item 2, the review's round 1). An svg
  // image's xlink:href is moved to the plain `href` as the anchors' is in mdBlock, so the element carries one attribute
  // every reader agrees on.
  const path = (src: string): string | null => {
    if (!src || src.startsWith("//") || /^[a-z][a-z0-9+.-]*:/i.test(src)) return null;   // a web address, a data: URL, an empty src: as written
    let rel = src;
    try { rel = decodeURI(src); } catch { /* a malformed escape: the spelling as written */ }
    return fileUrl(rel.startsWith("/") ? rel : dir + rel, sid);
  };
  for (const ref of figureRefs(root)) {
    const el = ref.el as HTMLElement;
    if (ref.attr === "srcset") {
      const cands = parseSrcset(ref.value);
      let changed = false;
      for (const c of cands) { const p = path(c.url); if (p !== null) { c.url = p; changed = true; } }
      if (changed) { el.setAttribute(FV_SRCSET, ref.value); el.setAttribute("srcset", serializeSrcset(cands)); }   // the authored candidates beside the rewritten ones, in the same order (parseSrcset reads both back candidate for candidate)
      else el.removeAttribute(FV_SRCSET);                // the attribute means this viewer rewrote this srcset, as data-fv-src does for a src
      continue;
    }
    const p = path(ref.value);
    if (el.tagName === "IMG" && ref.attr === "src") {
      if (p === null) { el.removeAttribute("data-fv-src"); continue; }
      el.setAttribute("data-fv-src", ref.value);
    }
    if (ref.attr === "xlink:href") {
      // SVG 2's rule when both spellings stand: `href` wins. The xlink one goes either way, so the element carries the one
      // attribute every reader (the gate's figureRefs included) agrees on; its value moves to `href` only when no href stood.
      el.removeAttributeNS(XLINK_NS, "href");
      if (!el.hasAttribute("href")) el.setAttribute("href", p === null ? ref.value : p);
      continue;
    }
    if (p === null) continue;
    el.setAttribute(ref.attr, p);
  }
}

// ── a figure that failed to load says so beside itself (plans/markdown-viewer.md Slice 7, item 2) ─────────
// A picture the browser could not fetch or decode drew a wordless broken-image glyph, or nothing at all: the kernel's
// answers for a figure that fails (a 404 for a missing file or a path outside its roots, a 415, a 413, a text file named
// as a figure that a 200 hands the decoder) all fire the img's `error` event with no status on it, and nothing in the
// Rendered box listened (the media view's imgBlock arms its own img; a figure inside a note had no listener), so the
// person saw a glyph with no word of what happened or which file. Now ONE capture-phase `error` listener on the body per
// open hears every figure of the box (an img's error does not bubble, so the body hears it in the capture phase, armReseat's
// idiom for `load`; the events fire after the swap, since the img's fetch is queued as a task and the swap is synchronous in
// the paint's own task, the fact the seam's onRendered doc relies on) and parks a label after the img naming the fact and
// the source (FIGURE_FAILED, the authored src by pictureDest's rule, the alt when there is one). Its twin, a capture-phase
// `load` listener, removes the label when a retry lands. Installed once per open beside the body's other listeners and
// dropped with the viewer, never per paint, so the chat page's heal (preview.ts installMdImgHeal, which re-fetches every
// failed `<img>` per kernel message and on romp:wsup) re-fires into the same listener; the heal skips an img with an
// `onerror` property, and none is set here: the img is only listened to. The img stays in the DOM as the browser draws it
// with every attribute untouched: the Comments panel pairs pictures by img order and `data-fv-src` (file-comments.ts
// embedFor), the regions layer wraps THE img (file-comments-regions.ts) and the reader's place counts `<img` tags in a row,
// and a label as the img's SIBLING leaves all three alone; it is one per img (a second `error`, the heal's retry failing
// again, rewrites the one label's text) and found by its data mark, never by its class (figure-gate.ts's rule: an author
// can type the class, and the sanitizer keeps `class` while its profile forbids every data-* attribute, so a data-* mark
// is the viewer's own). Both text walks skip it as a control (anchor-map.ts and reader-place.ts CONTROL_CLASSES: its text is the
// viewer's, not the note's, and a control's text in a block once refused the block's pairing and seated the reader's place
// fourteen paragraphs off), and headingWords skips it so a heading's Outline row reads the alt alone. The insertion fires
// no paint hook: the body's nodes stand and the panel's marks are unaffected, and a hook per failed figure would re-run
// the panel's whole pass. A gated figure (figure-gate.ts) has no src and never errors, and a label inside its placeholder
// would leave with restore, so an img under one is left alone. Images only, as the media body covers images alone: a
// `<picture>` is heard through its img, whose error fires when the ONE candidate the browser chose (a matching `<source>`,
// else the img's own srcset or src) fails, with no fall back to another, and its label goes after the picture element (a span
// is not a picture's content) when the picture holds that img alone, naming that candidate (failedSource); video, audio and an
// inline svg's `<image>` are recorded as a follow-up. A link holding the figure alone (`[![alt](src)](url)`) is climbed too, so
// the label is not a click target that follows the link (the review's round 1).
/** The mark on the label: the label is found by it (figureLabelAfter) and never by its class. */
const FIGERR_MARK = "data-fv-figerr";
/** The label's class, for the sheets alone (`.fileview-md .fv-figerr`: the gate's dress in the error dress's ink). */
const FIGERR_CLASS = "fv-figerr";
/** The element the label follows: the img, or the outermost of the wrappers standing between it and its block that the label
 *  must not go inside, climbed while one stands: a `<picture>` (a span is not a picture's content), the regions layer's
 *  `span.fc-imgwrap` (file-comments-regions.ts wraps THE img while the Comments panel is open, before the error fires, and its
 *  dispose puts the img back in the wrap's place and removes the wrap with everything else in it, so a label inside would
 *  leave with the panel's close; anchor-map.ts reads that span as the IMG, so the label's place in the block is the same), and
 *  a link holding the figure alone (`[![alt](src)](url)`, a README's linked badge or picture: inside the `<a>` the label wore
 *  the link's pointer and a click on it, to read it, followed the link; the review's round 1). A link with more in it (text
 *  beside the figure, a second figure) keeps the label beside its img, as the browser's own alt text is. A wrapper is climbed
 *  only when it holds exactly one img (oneImg): the layer's wrap holds THE img and a `<picture>`'s content model holds one, but
 *  an author can type two imgs into one `<picture>` or one `<span class="fc-imgwrap">` (the sanitizer keeps the element and
 *  `class`), and until the review's closing pass the two shared that anchor, so one label after it named the last of them to
 *  fail and a `load` of either removed it while the other still failed, that figure left to the browser's bare glyph; now such
 *  a wrapper is not the anchor, each img's label is its own next sibling inside it, and a heal removes its own alone (the
 *  plan's Slice 7 note, item 2). */
function figureAnchor(img: Element): Element {
  let a: Element = img;
  for (let p = a.parentElement; p && oneImg(p) && (p.localName === "picture" || p.classList.contains("fc-imgwrap") || linkAround(p, a)); p = a.parentElement) a = p;
  return a;
}
/** Whether `p` holds exactly one img: the wrappers above are climbed for the one figure they hold, and one holding two is left
 *  as the img's parent so that each img's label is its own. */
function oneImg(p: Element): boolean {
  return p.querySelectorAll("img").length === 1;
}
/** Whether `p` is a link holding `a` alone: an `<a>` whose one element child is `a` and whose text is blank. */
function linkAround(p: Element, a: Element): boolean {
  return p.localName === "a" && p.children.length === 1 && p.children[0] === a && (p.textContent || "").trim() === "";
}
/** The label standing right after `anchor` (its next sibling carrying the mark), when one does. */
function figureLabelAfter(anchor: Element): Element | null {
  const n = anchor.nextSibling;
  return n && n.nodeType === 1 && (n as Element).hasAttribute(FIGERR_MARK) ? n as Element : null;
}
/** `u` resolved against the document, as the browser resolves a figure's candidates for `currentSrc`; as written when it cannot be. */
function absUrl(u: string): string {
  try { return new URL(u, document.baseURI).href; } catch { return u; }
}
/** The source the browser asked for and could not load, as the author wrote it. The browser picks ONE candidate for an img (the
 *  first `<source>` of an enclosing `<picture>` whose media and type match, else the img's own srcset by density, else its
 *  src), fetches that one and fires the img's `error` when it fails, with no fall back to another candidate or to the src; so
 *  a label naming `src` for a picture or a srcset img named a file the browser never asked for, one that may well be there
 *  (the review's round 1). `img.currentSrc` is the browser's answer: when it is set and is not the img's own src, the
 *  candidate it names is matched against the srcset carriers (the picture's sources, then the img) and named by the authored
 *  spelling rewriteFigureSrcs kept beside the rewritten candidates (FV_SRCSET), or as written when the candidates were left as
 *  written (a remote host's absolute ones; a URL document's relative candidates are rewritten to absolute URLs by
 *  resolveFigureRefs with no data-fv-src and no FV_SRCSET stamp, so its label names the resolved URL). The img's own src, or an
 *  img with no currentSrc to read (the node stand-in), keeps pictureDest's rule: `data-fv-src` when the viewer rewrote the src,
 *  else `src`; a figure with neither names nothing. */
function failedSource(img: Element): string | null {
  const cur = (img as HTMLImageElement).currentSrc || "";
  if (!cur || cur === absUrl(img.getAttribute("src") || "")) return pictureDest(img);
  const picture = img.closest("picture");
  const carriers: Element[] = picture ? [...Array.from(picture.querySelectorAll("source")), img] : [img];
  for (const c of carriers) {
    const now = parseSrcset(c.getAttribute("srcset") || "");
    const was = c.hasAttribute(FV_SRCSET) ? parseSrcset(c.getAttribute(FV_SRCSET) || "") : now;
    for (let i = 0; i < now.length; i++) if (absUrl(now[i].url) === cur) return (was[i] ?? now[i]).url;
  }
  return pictureDest(img);
}
/** The source as the label shows it: a `data:` URI is an inline image's whole encoded payload, thousands of characters that
 *  the sheet's wrap turns into a box the height of the column (the review's round 1: a label 1518 px tall at 380 px, two
 *  screens of base64 where the note should go on), so it is cut to its head, the scheme and the media type through the
 *  comma, with an ellipsis; any other source as written. */
function shownSource(src: string): string {
  if (!/^data:/i.test(src)) return src;
  const comma = src.indexOf(",");
  return (comma >= 0 ? src.slice(0, comma + 1) : src.slice(0, 40)) + "…";
}
/** The words in the source's place when the figure names none (the Slice 7 review's round 2): an empty destination
 *  (`![alt]()`, which marked renders as `<img src="" alt="alt">`, or an authored `<img src="">`) fires the img's `error` with
 *  no request made (the HTML spec's empty-src rule), figure-gate.ts's figureRefs skips the empty value so nothing rewrote or
 *  gated it, and failedSource answers the empty string (or null for a figure with no source attribute at all); before, the
 *  label printed that string, "Image failed to load:  (alt)", a dangling colon before two spaces and nothing named. */
const FIGURE_NO_SOURCE = "the source is empty";
/** The label's words (the slice's contract C2, and its round 1 line): FIGURE_FAILED, the source the browser asked for as the
 *  author wrote it (failedSource: pictureDest's rule, `data-fv-src` when rewriteFigureSrcs rewrote the src, else `src`, or
 *  the srcset candidate the browser chose; a data: source cut to its head, shownSource) or FIGURE_NO_SOURCE when there is
 *  none to name, and the alt in parentheses when it is not empty. */
function figureLabelText(img: Element): string {
  const alt = img.getAttribute("alt");
  const src = failedSource(img);
  return FIGURE_FAILED + " " + (src ? shownSource(src) : FIGURE_NO_SOURCE) + (alt ? " (" + alt + ")" : "");
}
/** The figure an `error` or `load` heard on the body is about: an img inside the Rendered box and outside a gate's
 *  placeholder (`[data-act="fv-load"]`); null for anything else (the media view's own img, a control's, a gated figure). */
function figureOf(e: Event): Element | null {
  const t = e.target as Element | null;
  if (!t || t.nodeType !== 1 || t.localName !== "img") return null;
  if (!t.closest(".fileview-md")) return null;
  if (t.closest('[data-act="' + GATE_ACT + '"]')) return null;
  return t;
}
/** Arm the two capture listeners on a viewer's body (the header above); the function returned drops them. */
function armFigureLabels(body: HTMLElement): () => void {
  const onError = (e: Event): void => {
    const img = figureOf(e);
    if (!img) return;
    const anchor = figureAnchor(img);
    const words = figureLabelText(img);
    const had = figureLabelAfter(anchor);
    if (had) { had.textContent = words; return; }   // the one label per img: a retry that failed again rewrites its text
    const label = el("span", FIGERR_CLASS);
    label.setAttribute(FIGERR_MARK, "");
    label.textContent = words;
    const parent = anchor.parentNode;
    if (parent) parent.insertBefore(label, anchor.nextSibling);
  };
  const onLoad = (e: Event): void => {
    const img = figureOf(e);
    if (!img) return;
    const had = figureLabelAfter(figureAnchor(img));
    if (had) had.remove();                          // a retry landed: the picture shows, the label goes
  };
  body.addEventListener("error", onError, true);
  body.addEventListener("load", onLoad, true);
  return () => { body.removeEventListener("error", onError, true); body.removeEventListener("load", onLoad, true); };
}

/** A URL document's figures resolve against where the document LIVES, through every attribute a figure fetches through
 *  (figure-gate.ts figureRefs, the walk rewriteFigureSrcs takes for a file on disk): an img's `src` and `srcset`, a
 *  `source`'s `src` and `srcset`, a video's `src` and `poster`, an audio's and a track's `src`, an svg `image`'s `href` and
 *  `xlink:href`. Before this the URL kind resolved `img[src]` alone, and every other relative reference was left to the
 *  browser, which resolves it against the PAGE (the Slice 4 review, round 2: `<video src="clip.mp4" poster="poster.png">`
 *  in a document at /notes/note.md was fetched from the dashboard's root and 404'd; a `srcset` candidate the same). A
 *  srcset is resolved candidate by candidate with its descriptors kept; an `xlink:href` is folded into `href` as
 *  rewriteFigureSrcs folds it (`href` wins when both stand), so the element carries the one attribute every reader
 *  agrees on. resolveDocRelative (md-links.ts) leaves a scheme, a `#fragment` and an empty value as written, so an
 *  absolute figure is untouched and the gate judges it as before; a protocol-relative `//host/…` takes the document's
 *  scheme, as the browser would give it against the document. No `data-fv-src`: that stamp is the comments panel's
 *  pairing key and a URL document has no panel. Runs on the sanitized DOM, after DOMPurify, as the file kind's rewrite
 *  does; the attribute is read and written, never the property, which is already resolved against the page. */
function resolveFigureRefs(root: ParentNode, base: string): void {
  for (const ref of figureRefs(root)) {
    const el = ref.el;
    if (ref.attr === "srcset") {
      const cands = parseSrcset(ref.value);
      let changed = false;
      for (const c of cands) { const abs = resolveDocRelative(c.url, base); if (abs !== c.url) { c.url = abs; changed = true; } }
      if (changed) el.setAttribute("srcset", serializeSrcset(cands));
      continue;
    }
    const abs = resolveDocRelative(ref.value, base);
    if (ref.attr === "xlink:href") {
      el.removeAttributeNS(XLINK_NS, "href");
      if (!el.hasAttribute("href")) el.setAttribute("href", abs);
      continue;
    }
    if (abs !== ref.value) el.setAttribute(ref.attr, abs);
  }
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
 *  Called once, from the pane's boot (render.ts, feed.ts and files.ts: any document, one mechanism);
 *  every reply is reqId-guarded so one landing after a close or a replace-open touches nothing. The
 *  viewFile branch honors a shell's relay of a chat file-link click: the Files pane is its receiver
 *  (kernel.py's landing shell forwards the click there with the session's identity), and a document
 *  with a relay contract of its own passes `onRelay` and takes the relayed message whole instead of
 *  the plain open (files.ts caches the identity for its chip and keeps its recent list). The relayed message carries `at` since Slice 6 of
 *  plans/markdown-viewer.md (a todo link's line or heading: render.ts openPath and waiting.ts openTodoPath post it,
 *  the shell's two forwarders in kernel.py copy it), and both receivers read it through readAt, since it crossed a
 *  frame boundary. `host.openFile`: this document's own opener for a link inside a shown file (the Files pane's
 *  openHere), handed the link's target the same way (At). `host.onLeave`: the reader's place in a file as they leave it
 *  (RememberedPlace; a close, a replace-open, the page hidden), for the host to persist and hand back as an open's
 *  `place` (the Files pane's Recent entry; Slice 6, item 3). */
export function initFileView(poster: (m: Record<string, unknown>) => void,
                             onRelay?: (m: { path: string; sid?: unknown; identity?: unknown; todoId?: unknown; at?: unknown }) => void,
                             host?: { openFile?: (path: string, sid: string | null, at: At | null) => void; onLeave?: (path: string, sid: string | null, rec: RememberedPlace) => void }): void {
  post = poster;
  if (host && host.openFile) openLinkedFile = host.openFile;   // a link inside a shown file opens through the host (the Files pane's Recent list)
  if (host && host.onLeave) leaveHost = host.onLeave;          // the reader's place when a file is left, for the host's store (the Files pane's Recent entry)
  // The page going away (a reload, a navigation) is a leave too: the open viewer's place is written before it goes, and
  // the write is not retired (a page restored from the back-forward cache still shows the viewer, and its close writes
  // again). The chat's persistScrollForReload (render.ts) keeps its own place the same way.
  window.addEventListener("pagehide", () => { if (leaveLive) leaveLive(); });
  watchInputKind();   // the kind of the document's last press, for a hand-over of the keyboard with no holder to read the ring from (ringWithNoHolder)
  window.addEventListener("message", (e: MessageEvent) => {
    const m = e.data;
    if (!m) return;
    if (m.romp === "viewFile" && typeof m.path === "string" && m.path) {
      if (onRelay) { onRelay(m); return; }   // this document's own contract (the Files pane) takes the message whole
      openFileView(m.path, typeof m.sid === "string" ? m.sid : null, { at: readAt(m.at) });
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
