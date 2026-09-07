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
import { marked } from "marked";
import DOMPurify from "dompurify";
import { fileUrl } from "./preview";
import { hostOf, bareId, hostNameNodes } from "./host-prefix";
import { kernelUrl } from "./media";
import { quoteSrcLabel } from "./docreview";
import { fileCommentsAction } from "./file-comments";

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
// wrong highlight reads as information the file does not contain.
const LANG: Record<string, string> = {
  py: "python", pyi: "python", js: "javascript", jsx: "javascript", mjs: "javascript",
  cjs: "javascript", ts: "typescript", tsx: "typescript", json: "json", jsonc: "json",
  yaml: "yaml", yml: "yaml", sh: "bash", bash: "bash", zsh: "bash", bats: "bash",
  html: "xml", htm: "xml", xml: "xml", svg: "xml", vue: "xml", css: "css", scss: "css",
  md: "markdown", markdown: "markdown", diff: "diff", patch: "diff",
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

// ── raw-mode editing (the file browser's slice 2, the user 2026-08-14) ─────────────────────────────
// The save op rides the WS poster the pane's boot hands initFileView; replies route back to the OPEN
// viewer through these module-level hooks (the viewer itself is a per-open closure).
let post: (m: Record<string, unknown>) => void = () => { /* bound by initFileView */ };

// ── the session the file was opened from (the user 2026-09-03) ────────────────────────────────────
// The viewer knows only a sid, and its openers mostly know no more: the shell's viewFile relay and the
// conflict Reload live in this module, the file browser hands over a bare sid. So the session's name
// and colour are RESOLVED from the sid here, through a lookup each hosting document registers once
// at boot beside initFileView (render.ts reads its tab set, feed.ts its session list). Unregistered,
// or a sid the document cannot name, the title bar carries no chip: an identity is looked up, never
// invented.
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
let saveSeq = 0;
let editHooks: { reqId: number; logWarning: string | null; saved: (mtimeNs: string, logged: boolean) => void; failed: (err: string) => void } | null = null;
// Set by the open viewer: returns false to VETO a close (an editor holding unsaved changes asks
// first). The guard must live in closeFileView itself, because the browser overlay and the Escape
// handler both close through it without knowing an edit is in progress.
let closeGuard: (() => boolean) | null = null;
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

// ── viewer action registry (the user 2026-08-22) ── INTERNAL SEAM, no compatibility promise:
// reshape freely. Anything acting on the OPEN file declares itself here instead of hand-wiring into
// openFileView's action row, where every file-viewer change used to collide. mount() runs once per
// open and returns the action's element for the row (or null to sit this file out); an action that
// answers asynchronously (the GitHub link's kernel ask) mounts hidden and reveals itself when its
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
   *  decode failure's pane has replaced the picture. Read from the body itself, so it is never a stale handle */
  mediaElement(): HTMLImageElement | HTMLElement | null;
  /** the figures inside a Rendered markdown body, in document order, as of the latest onRendered; [] in every other
   *  view. A path figure's `src` (relative or absolute) is the kernel's /file URL by then and its authored value rides
   *  in `data-fv-src` (rewriteFigureSrcs); the figures' own load events are the caller's to await */
  renderedImages(): HTMLImageElement[];
  /** the session the file was opened from, as the hosting document resolves it (the title-bar chip's source) */
  identity(): FileViewIdentity | null;
  /** runs after every paint of the body: a text body at once (open, view switch, reload), a media body once it shows —
   *  an image after its load event (at once when it was already complete), a PDF frame at once (whenShown). A Rendered
   *  body's figures are in the DOM by then with their own loads still pending. The panel re-runs its paint pass */
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
// beside it. Hidden until the OWNING kernel answers the lazy fileGitLink ask, and the answer ALWAYS
// shows it (the user 2026-09-05, who could not tell "not committed yet" from "the link is broken" when
// the button simply never appeared). A real URL is an anchor — the browser owns the new tab. No URL is
// a real disabled <button>: assistive tech reads the state and the label, and there is no href to
// follow or to go stale. The reason rides in the tooltip AND as the caption, because a tooltip alone
// needs a mouse — touch has no hover, and a disabled button takes no focus — so the caption is what
// makes the reason glanceable; the sheet truncates it and the tooltip carries the full text. A URL
// whose branch is not on origin stays an anchor, dashed, with the note as its caption, since GitHub
// 404s it until the push. One question per open, reqId-guarded. Exported for the DOM-shape test.
const GH_REASONLESS = "this kernel predates link reasons; restart it after updating";
let gitSeq = 0;
let gitHooks: { reqId: number; apply: (url: string, reason: string) => void } | null = null;
export const githubLinkAction: FileViewAction = {
  id: "github-link",
  mount({ path, sid }) {
    const unit = el("span", "fileview-gh");
    unit.hidden = true;
    gitHooks = {
      reqId: ++gitSeq,
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
        if (why) {
          const cap = el("span", "fileview-gh-why");
          cap.textContent = why; cap.title = why;            // the sheet truncates; the full text one hover away
          unit.appendChild(cap);                             // before the control: it annotates what follows
        }
        unit.appendChild(ctl);
        unit.hidden = false;
      },
    };
    post({ type: "fileGitLink", path, sid: sid || undefined, reqId: gitSeq });
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
 *  The `gt` stamp is the consent's own click time: federation queues the setting per host across a
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
    post({ type: "setFileEditing", enabled: true, gt: Date.now() });
    return true;
  }
  let on = false;
  try { on = !!(await (await fetch(kernelUrl("/version"), { cache: "no-store" })).json()).fileEditing; } catch { /* ask below */ }
  if (on) return true;
  if (!window.confirm(COPY)) return false;
  post({ type: "setFileEditing", enabled: true, gt: Date.now() });
  return true;
}

// ── quote a passage into the composer (the user 2026-08-23, the three-verbs consolidation) ────────
// Selecting text in the viewer seeds the SAME labeled quote chip a VS Code editor highlight does:
// the selection posts to our own window in the editorSelection shape, so render.ts's existing
// handler owns the chip end to end (no import cycle — the browseFiles precedent), labeled path:line
// via quoteSrcLabel. From there the flow is the chat's own: type a note (or none), Stage, keep
// going, send once. This REPLACED the viewer's separate review layer — the per-file comment store
// (romp:fileviewComments), the painted marks, and the one-shot Submit that assembled a message —
// because batching notes for one hand-off is exactly what quote chips + ⌘⏎ staging already do,
// and "comment" now means only the transcript's live threads.

// The retired store's data would otherwise sit in localStorage forever on every browser that
// ever commented — sweep it on load.
try { localStorage.removeItem("romp:fileviewComments"); } catch { /* storage may be denied */ }

// Where a quote seed lands (2026-09-03, with the Files pane): the composer in THIS document when there
// is one (the chat-hosted viewer posts to its own window, and render.ts's editorSelection handler owns
// the chip end to end); otherwise the SHELL, when this document is framed by one. The Files pane and
// the feed host the viewer without a composer, and the shell forwards the seed into the chat pane (the
// editorSelection arm in kernel.py's landing shell). Before this, a selection in the feed-hosted viewer
// was dead air by design. No composer and no shell (a VS Code webview's cross-origin parent throws; a
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
  if (closeGuard && !closeGuard()) return;   // unsaved edits, and the user chose to keep them
  closeGuard = null;
  editHooks = null;
  gitHooks = null;                                     // a reply landing after the close decorates nothing
  dropOnKey();                                         // the closing viewer's handler leaves with it
  dropMediaUrl();                                      // an image/PDF view's bytes leave with the viewer
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

/** Show `path` in a modal over this pane. Re-opening replaces whatever is up — never stacks.
 *  Returns whether the open actually happened: false means the dirty-edit guard kept the PREVIOUS
 *  viewer, whose provenance the caller must not touch (initFileView's relay branch keys viaRelay
 *  and the shell's viewFileOpened ack on this verdict — a vetoed relay must neither re-tag the
 *  survivor as relay-opened nor arm a restore for an open that never happened). */
export function openFileView(path: string, sid?: string | null, opts?: { todoId?: string | null }): boolean {
  // The replace path bypasses closeFileView, so it needs the same dirty ask: opening file B over an
  // edited-but-unsaved file A must not silently eat A's buffer.
  if (document.getElementById("romp-fileview") && closeGuard && !closeGuard()) return false;
  closeGuard = null;
  editHooks = null;
  gitHooks = null;                                     // the replace path skips closeFileView — same drop
  dropOnKey();                                         // …and the same for the old viewer's Escape handler
  dropMediaUrl();                                      // …and the old viewer's image bytes (the Reload path)
  runCloseHooks();                                     // …and the old viewer's panel hooks
  document.getElementById("romp-fileview")?.remove();
  // backdrop (the whole overlay carries the id every open/closed check targets) + the ~95% card.
  // The backdrop treatment matches the lightbox: dimmed, click outside the card closes, content
  // clicks don't (the user 2026-08-15: it must be obvious the chat is still right behind it).
  const wrap = el("div");
  wrap.id = "romp-fileview";
  wrap.onclick = (ev) => { if (ev.target === wrap) closeFileView(); };
  const box = el("div", "fileview");
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
  // The SESSION this file was opened from, in the waiting pane's chip idiom: identity colour, "host:"
  // quiet for a remote session (and marked while its link is down). Resolved through the hosting
  // document's registered lookup — no sid, or a sid it cannot name, and there is no chip.
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
  let mediaBlob: Blob | null = null;          // the fetched bytes — the Source toggle decodes THESE
  let objUrl: string | null = null;           // this open's object URL (registered as mediaUrlLive)
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
  let cm: { value(): string; focus(): void; destroy(): void } | null = null;   // the CodeMirror handle when mounted
  const bufValue = (): string | null => (cm ? cm.value() : ta ? ta.value : null);   // whichever surface owns the buffer
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
  // panel's verbs since Slice 1 of plans/file-review.md). While changes are PENDING in the file the
  // button refuses instead, in words, in place: a raw save over pending changes rewrites their offsets
  // (setEditBlocked, set by the panel from the kernel's hunks; Slice 5 lifts it). The button stays a
  // real button rather than a disabled one so the reason reaches touch and keyboard users too.
  let editBlocked: string | null = null;
  editBtn.addEventListener("click", () => {
    if (editBlocked) { noteBar(editBlocked); return; }
    void ensureEditingAllowed(sid).then((ok) => {
      if (!ok) return;
      if (isMd && fmt.md === "rendered") { fmt.md = "raw"; saveFmt(fmt); }
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
  const ctx: FileViewActionCtx = {
    path, sid: sid || null, todoId: opts?.todoId ?? null,
    body: () => body,
    mode: () => (isImage || isPdf) && !(svgSource && svgText !== null) ? "media" : isMd && fmt.md === "rendered" ? "rendered" : "raw",
    text: () => viewText(),
    mtimeNs: () => mtimeNs,
    media: () => (isPdf ? "pdf" : isSvgImage ? "svg" : isImage ? "image" : null),
    // both read the LIVE body under the mode gate rather than a handle kept at paint time: a reload swaps the
    // <img>, imgFailed's pane removes it, and a rendered README may itself carry an <img class="fileview-img">
    // through the sanitizer — the gate keeps such a figure from ever answering as the media element
    mediaElement: () => (ctx.mode() === "media" ? body.querySelector("img.fileview-img, iframe.fileview-frame") as HTMLElement | null : null),
    renderedImages: () => (ctx.mode() === "rendered" ? Array.from(body.querySelectorAll(".fileview-md img")) as HTMLImageElement[] : []),
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
  };
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

  // A one-line notice above the body in the viewer's error dress (the edit-blocked reason, a save
  // failure, a save whose comments-log entry did not land): one at a time, replacing the last, and
  // the body content underneath survives.
  const noteBar = (msg: string): HTMLElement => {
    document.getElementById("fileview-save-err")?.remove();
    const bar2 = el("div", "fileview-err");
    bar2.id = "fileview-save-err";
    bar2.textContent = msg;
    body.prepend(bar2);
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
        body.replaceChildren(codeBlock(svgText, path, true));   // long lines always soft-wrap (the user 2026-08-24)
        fireRendered();                         // a text body: the panel's highlight pass runs on it too
        return;
      }
      const shown = isPdf ? pdfBlock(objUrl, path) : imgBlock(objUrl, path, imgFailed);
      body.replaceChildren(shown);
      whenShown(shown, fireRendered);         // the seam's onRendered for a media body: once the picture shows (Slice 3)
      return;
    }
    if (text === null || editing) return;   // loading, or the textarea owns the body right now
    body.replaceChildren(rendered ? mdBlock(text, path, sid) : codeBlock(text, path, true));   // long lines always soft-wrap (the user 2026-08-24)
    fireRendered();                             // the seam's onRendered: every text paint, so highlights follow the view
  };

  // Selection → labeled quote chip (the user 2026-08-23): mouseup is the gesture's settle point.
  // The chip behaves exactly like a VS Code editor highlight's — one live source-labeled chip,
  // replaced by the next selection, persisting until sent, staged, or ✕'d — because it IS that
  // chip: render.ts's editorSelection handler seeds it. The post carries THIS viewer's sid, so the
  // chip lands in the session the file was opened FOR even if the active tab changed while the
  // modal was up (the 2026-08-19 routing rule: the gesture's session, never activeId-at-gesture).
  let seedSeq = 0;                                 // last gesture wins if two fresh reads race
  const onSelect = () => {
    if (editing) return;   // CodeMirror selections are edit gestures, not quotes
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

  // ── edit mode (the raw-mode slice) ── a plain textarea holding the raw bytes: an embedded editor
  // is a different project, and a textarea that keeps your changes beats a half-editor. The kernel's
  // mtime floor does the real safety work (agents edit these same trees — see _save_file).
  const confirmDiscard = (): boolean =>
    !editing || !dirty || window.confirm("Discard unsaved changes to " + path.slice(cut + 1) + "?");
  closeGuard = confirmDiscard;
  const norm = (s: string): string => s.replace(/\r\n/g, "\n");   // the textarea's own view of any text
  // The editing substrate is CodeMirror 6 (the user 2026-08-22), living in its OWN lazily-loaded
  // bundle so people who never edit download nothing (the main bundles import none of it — the
  // contract is the window global the chunk registers). The URL derives from the page's own running
  // bundle script — render.js (chat), feed.js (feed) or files.js (the Files pane; 2026-09-03, when a
  // pattern naming only the first two sent every Edit there to the textarea with a raw error) — same
  // directory, same ?v= cache token — so it resolves on the kernel pages and the VS Code webview
  // alike, and a rebuilt kernel always serves a matching chunk. A failed load rejects ONCE and clears
  // the latch so a later attempt retries fresh.
  let edChunk: Promise<{ mount: (host: HTMLElement, opts: object) => { value(): string; focus(): void; destroy(): void } }> | null = null;
  const editorChunk = () => edChunk || (edChunk = new Promise((res, rej) => {
    const w = window as any;
    if (w.__rompEditor) return res(w.__rompEditor);
    const self = Array.from(document.querySelectorAll("script[src]"))
      .map((n) => (n as HTMLScriptElement).src).find((u) => /\/(render|feed|files)\.js/.test(u));
    if (!self) return rej(new Error("no bundle script tag to derive the editor chunk URL from"));
    const sc = document.createElement("script");
    sc.src = self.replace(/\/(render|feed|files)\.js/, "/editor-chunk.js");
    sc.onload = () => { const e = (window as any).__rompEditor; e ? res(e) : rej(new Error("editor chunk loaded but did not register")); };
    sc.onerror = () => { edChunk = null; rej(new Error("the editor bundle failed to load")); };
    document.head.appendChild(sc);
  }));
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
    editing = true; dirty = false;
    eolCRLF = /\r\n/.test(text);
    renderBody();
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
        onChange: () => { dirty = cm!.value() !== norm(text!); },
        onSave: () => doSave(),
      });
      cm.focus();
    }).catch((err) => {
      if (!editing || my !== editSeq) return;
      document.getElementById("fileview-save-err")?.remove();
      const bar2 = el("div", "fileview-err");   // loud: say the editor is degraded, never pretend
      bar2.id = "fileview-save-err";
      bar2.textContent = String(err && (err as Error).message || err) + " — editing in the plain fallback editor.";
      enterFallback();
      body.prepend(bar2);
    });
  };
  const exitEdit = () => {
    editing = false; dirty = false; ta = null;
    cm?.destroy(); cm = null;
    editHooks = null;                           // a cancelled save's late ack must not touch a NEW session
    saveBtn.disabled = false; saveBtn.textContent = "Save";
    renderBody();
  };
  const doSave = () => {
    const buf = bufValue();
    if (!editing || buf === null || saveBtn.disabled) return;
    if (!dirty) { exitEdit(); return; }         // nothing changed — leaving is the honest ack
    saveBtn.disabled = true; saveBtn.textContent = "Saving…";   // acknowledge before the round-trip
    // restore the file's own line endings — an untouched CRLF file must round-trip byte-identical
    const content = eolCRLF ? buf.replace(/\n/g, "\r\n") : buf;
    // Loud, in place, and the BUFFER SURVIVES: the error bar sits above the textarea. A conflict
    // (the disk moved — an agent wrote it) offers Reload, which re-opens fresh — behind the same
    // discard confirm, so the user's edits are never thrown away silently (never a merge UI).
    const showSaveError = (err: string) => {
      const bar2 = noteBar(err);
      if (/changed on disk/.test(err)) {
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
        // the seam's onSaved: the panel refreshes its Log (the kernel appended the edit before replying)
        for (const cb of savedHooks) { try { cb({ mtimeNs: mtNs, logged }); } catch { /* a hook must never cost the save */ } }
        // The comments-log warning goes up in the note bar, in the kernel's own words (CLAUDE.md:
        // surface it, never degrade silently) — here, above the editor the in-flight stay below keeps,
        // and again after exitEdit's repaint on the other path, which takes this bar with the editor.
        const noteLog = () => { if (hooks.logWarning) noteBar(hooks.logWarning); };
        noteLog();
        // Keystrokes typed DURING the round-trip survive the ack (the review's in-flight-typing
        // finding): if the live buffer moved past the snapshot we saved, stay in edit mode with the
        // new baseline — never re-render over what the user is still typing.
        if (bufValue() !== null && bufValue() !== norm(content)) {
          dirty = true;
          saveBtn.disabled = false; saveBtn.textContent = "Save";
          return;
        }
        exitEdit();                             // re-renders the highlighted view from the saved bytes
        noteLog();
      },
      failed: (err) => {
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
        showSaveError(err);
      },
    };
    editHooks = hooks;
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
  // and the aside left standing; only the body and the mtime change. The newest fetch wins
  // (fetchSeq, the quote seed's own idiom): two reloads in flight answer in any order, and an older
  // response landing last would otherwise put ITS bytes in the body under the newer response's mtime —
  // a view that claims the new text and shows the old, which the comments panel would then paint its
  // marks over (it trusts mtimeNs() to say which text it sees). An overtaken response changes nothing:
  // not the body, not the mtime, not the Edit verdicts, and no error row for a failure nobody awaits.
  let fetchSeq = 0;
  const fetchFile = () => {
    const seq = ++fetchSeq;
    const overtaken = () => seq !== fetchSeq;
    fetch(fileUrl(path, sid), { cache: "no-store" }).then((r): Promise<string | Blob> => {
      if (overtaken()) return Promise.resolve("");   // a newer fetch is out: read nothing, set nothing
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
      isText = (r.headers.get("Content-Type") || "").startsWith("text/plain")
        && r.headers.get("X-Romp-Text-Utf8") !== "0";
      mtimeNs = r.headers.get("X-Romp-Mtime-Ns") || "";
      // Media branches on the SAME kernel verdict (an image 200 wears image/* and no X-Romp-Text-Utf8 —
      // tests/test_kernel_preview.py pins that contract server-side). The bytes below are the one fetch
      // either way: media takes them as a blob for an object URL, never a second request.
      const ct = r.headers.get("Content-Type") || "";
      isImage = ct.startsWith("image/");
      isPdf = ct.startsWith("application/pdf");
      isSvgImage = ct === "image/svg+xml";
      return isImage || isPdf ? r.blob() : r.text();
    }).then((t) => {
      if (overtaken()) return;                                   // a newer fetch's bytes are what show
      if (!document.getElementById("romp-fileview")) return;    // closed while it was in flight
      if (t instanceof Blob) {
        // Minted only now — a viewer closed (above) or REPLACED mid-flight creates nothing to leak,
        // and never clobbers the new open's mediaUrlLive registration.
        if (!wrap.isConnected) return;
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
      renderBody();
    }).catch((err) => {
      if (overtaken()) return;                                   // the newer fetch answers for the view, success or failure
      if (!document.getElementById("romp-fileview")) return;
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
    });
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
    pre.appendChild(code);
    wrap.appendChild(pre);
    return wrap;
  }
  const gutter = el("div", "fileview-gutter");
  gutter.textContent = lines.map((_, i) => String(i + 1)).join("\n");
  gutter.setAttribute("aria-hidden", "true");
  if (hl !== null) code.innerHTML = hl; else code.textContent = text;
  pre.appendChild(code);
  wrap.appendChild(gutter); wrap.appendChild(pre);
  return wrap;
}

// Markdown rendered as the prose it means (the user 2026-08-09: Rendered is the default, Raw one click
// away). The file is arbitrary bytes off a disk and marked emits raw HTML verbatim, so — exactly like the
// chat's md() in render.ts — the output goes through DOMPurify before it ever reaches .innerHTML: an
// <img onerror> or a javascript: href in a README must never run in the dashboard.
function mdBlock(text: string, path: string, sid: string | null | undefined): HTMLElement {
  const box = el("div", "fileview-md");
  try {
    const dirty = marked.parse(text) as string;
    // html + svg, in lockstep with the chat's md(): KaTeX draws stretchy glyphs (\sqrt radicals,
    // wide accents) as inline <svg> even in html output, and the html-only profile ate them.
    box.innerHTML = DOMPurify.sanitize(dirty, { USE_PROFILES: { html: true, svg: true }, ADD_DATA_URI_TAGS: ["img"] });
  } catch {
    box.textContent = text;                            // a marked bug must never cost the content
  }
  // Figures: a relative src is re-pointed at the kernel, on the SANITIZED DOM (rewriteFigureSrcs, below) — after
  // DOMPurify, so it touches only the attributes the sanitizer let stand and never re-parses marked's HTML.
  rewriteFigureSrcs(box, path.slice(0, path.lastIndexOf("/") + 1), sid);
  // Links open a NEW tab: the viewer lives inside the chat pane's document, and letting a README link
  // navigate it away would silently eat the chat until a reload.
  box.querySelectorAll("a[href]").forEach((a) => {
    (a as HTMLAnchorElement).target = "_blank";
    (a as HTMLAnchorElement).rel = "noopener";
  });
  // Fenced blocks: highlight only a language the fence NAMES and this bundle registers — the same
  // no-guessing rule as langFor; an unnamed block stays plain rather than being painted at random.
  box.querySelectorAll("pre code").forEach((node) => {
    const codeEl = node as HTMLElement;
    const lang = (codeEl.className.match(/language-([\w-]+)/) || [])[1];
    if (!lang || !hljs.getLanguage(lang)) return;
    try {
      codeEl.innerHTML = hljs.highlight(codeEl.textContent || "", { language: lang }).value;
      codeEl.classList.add("hljs");
    } catch { /* leave plain */ }
  });
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
 *  Untouched: a src with a scheme (http:, https:, data:, blob:, …), a protocol-relative URL (`//host/…`, which the
 *  browser and every markdown reader take as a web address), and an empty one. `..` segments and `./` pass through
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
// already-fetched bytes instead of a second network fetch.
function pdfBlock(objUrl: string, path: string): HTMLElement {
  const frame = el("iframe", "fileview-frame") as HTMLIFrameElement;
  frame.src = objUrl;
  frame.title = path;
  return frame;
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
                             onRelay?: (m: { path: string; sid?: unknown; identity?: unknown; todoId?: unknown }) => void): void {
  post = poster;
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
}
