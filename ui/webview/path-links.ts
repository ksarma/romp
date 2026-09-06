// The file-path matcher the chat's transcript links are made from, as a module ANY pane can import
// (plans/file-review.md, Slice 0). It lived inside render.ts, the chat's entry, which exports nothing —
// so the Waiting-on-you pane, an iframe of its own, rendered a todo's detail path as plain text while the
// chat's card for the same todo linked it. Lifted, not copied: one regex, one set of gates, one span
// shape, so the kernel's tokenizer parity (tests/fixtures/path_token_parity.json) and the chat's link
// behaviour have a single source.
//
// This module MATCHES and MARKS; it binds no action. Every link it emits is a `.file-uri-link` span
// carrying data-act="openpath" (PATH_LINK_ACT), data-path (what a click opens — for a shortened mention
// the kernel's fixed target, not the token), data-rel="1" when the token was a bare path rather than a
// file:// URI (so a resolver uses a session's cwd), and data-sid when the caller named the session the
// text belongs to. What a click DOES is the hosting document's call: render.ts binds openPath per span
// (the editor in VS Code; the viewer, or the shell's relay, on the web) and paints its figure previews
// from the hits; waiting.ts routes the act through its delegate to the shell's viewFile relay. The
// listeners this module puts on a span are about focus, not the action: Enter or Space on a focused link
// clicks it, so the host's click handler is reached from the keyboard too (pathLinkKey, below), and a
// mouse press does not focus the link, so a click leaves focus where a click on plain text leaves it
// (pathLinkPress / pathLinkRelease, below). A document that cannot act on a click should not call this —
// a link that does nothing is worse than text (ui/CLAUDE.md, every control acknowledges).

export const PATH_LINK_ACT = "openpath";

function el(tag: string, cls?: string): HTMLElement { const e = document.createElement(tag); if (cls) e.className = cls; return e; }

// A file:// URI → its local filesystem path: strip the scheme, percent-decode. file:///a/b → /a/b.
export function fileUriToPath(uri: string): string {
  let p = uri.replace(/^file:\/\//i, "");   // file:///Users/… → /Users/… (host is empty for file:///)
  try { p = decodeURIComponent(p); } catch { /* malformed %-escape — use verbatim */ }
  return p;
}
// A <span> is not a control: it has no tab stop and no activation key, so a keyboard user could reach the
// links in the Waiting-on-you pane's row fold and its Reply modal — where the focus already sits in a
// textarea — only by leaving for the pointer (2026-09-06). Enter or Space on a focused link clicks it;
// the click is still the host's (a delegate on a stable root in waiting.ts, render.ts's per-span binder),
// this only gives the keyboard the route a pointer has. Both keys, as the dashboard's other keyboard-
// activated rows take them (render.ts); Space is prevented so it does not also scroll the pane.
function pathLinkKey(e: KeyboardEvent): void {
  if (e.key !== "Enter" && e.key !== " ") return;
  e.preventDefault();
  (e.currentTarget as HTMLElement).click();
}
// A tab stop is focusable by the pointer too, and that is the one thing the plain span it replaced was
// not: a mouse click left focus on the body, a click on a tabindex span leaves it on the link. The chat's
// keyboard model reads the difference — Enter from the bare transcript (nothing focused) drops the cursor
// into the message box (render.ts, the user 2026-06-26) — and the viewer a click opens takes no focus, so
// after Escape closed it the next Enter found the link still focused and opened the file AGAIN instead of
// the message box; a selection dragged FROM a link met the same fate on Enter, re-opening the file rather
// than seeding the quote, and in Chromium the focus change itself ended that drag's selection before it
// began (2026-09-06). So a mouse press does not focus the link at all: the browser focuses the span as the
// mousedown's default action, run after its listeners, so the press drops the tabindex attribute — a span
// without one is not focusable — and focus lands where a click on plain text puts it, the body, as
// before, with the click and the selection the press starts untouched. The attribute comes back on the
// events that end the press on this span: mouseup (a click), mouseleave (a drag that goes on elsewhere),
// contextmenu and dragstart (a menu or a native drag took the pointer, and the mouseup may never reach
// the page). Between them the link is out of the tab order, for the length of a press; a keyboard focus
// meets no press and stays — Enter and Space then activate, as an <a> does. Not mousedown.preventDefault(),
// which would also keep a selection from starting on the link (the text is meant to be selectable in
// place); not a blur on the focus event, which in Chromium clears the selection the press made (a
// double-click's word). A span already focused (by Tab, then clicked) is blurred by the press itself,
// since the browser fires no focus for it.
function pathLinkPress(e: MouseEvent): void {
  const a = e.currentTarget as HTMLElement;
  a.removeAttribute("tabindex");                // not focusable for the rest of this press
  if (document.activeElement === a) a.blur();   // the press ends a keyboard focus too: the browser would not re-focus it
}
function pathLinkRelease(e: Event): void {
  const a = e.currentTarget as HTMLElement;
  if (!a.hasAttribute("tabindex")) a.tabIndex = 0;
}
// A VERBATIM file link, marked for whoever hosts it. `raw` is shown as written (selectable/copyable in
// place); `open` is what gets opened. A bare file:// can't be followed by the browser from the http
// dashboard (blocked scheme) and a VS Code editor won't render a PDF, so it is routed, never navigated.
// `relative` bare paths are resolved against a session's cwd by whoever opens them — a relative
// `design/foo.md` is relative to the repo the agent runs in, not the kernel's cwd (the user 2026-07-06);
// `sid` names that session when the text belongs to one other than the host's active one — a todo's
// detail is written by the session that filed it, wherever it is read.
export function openPathLink(raw: string, open: string, relative = false, sid?: string | null): HTMLElement {
  const a = el("span", "file-uri-link");
  a.textContent = raw;                       // shown exactly as written, selectable/copyable in place
  a.title = "Open " + open;
  a.tabIndex = 0;                            // in the tab order, like the <a> it stands in for…
  a.role = "link";                           // …and announced as one (the ARIA IDL attribute)
  a.onkeydown = pathLinkKey;                 // Enter / Space → this span's click, whoever handles it
  a.onmousedown = pathLinkPress;             // a mouse press does not focus it: the tabindex is off for the press…
  a.onmouseup = a.onmouseleave = a.oncontextmenu = a.ondragstart = pathLinkRelease;   // …and back once the press has ended on this span
  a.dataset.act = PATH_LINK_ACT;
  a.dataset.path = open;
  if (relative) a.dataset.rel = "1";
  if (sid) a.dataset.sid = sid;
  return a;
}
export function fileUriLink(uri: string): HTMLElement { return openPathLink(uri, fileUriToPath(uri)); }
// Is this bare token (trailing punctuation already stripped) a file path worth linkifying? Requires a slash
// and EITHER an absolute/anchored start (/, ~/, ./, ../) OR a file extension on the final segment — so
// "and/or", "TCP/IP", "24/7", "read/write" stay as prose. URL-ish tokens (a ':' or '//') are rejected;
// http(s) links are already <a> (skipped) — this just guards a rare un-autolinked one.
export function looksLikeFilePath(tok: string): boolean {
  if (tok.includes(":") || tok.includes("//") || !tok.includes("/")) return false;
  if (/^(?:~\/|\.{1,2}\/|\/)/.test(tok)) return true;                        // absolute or anchored (/, ~/, ./, ../)
  return /\.[A-Za-z0-9]{1,8}$/.test(tok.slice(tok.lastIndexOf("/") + 1));    // relative → the last segment has an extension
}
// A BARE filename (no slash — `power2_watts.pdf`) is linkified ONLY inside inline <code> (the user
// 2026-07-17: a reply listing its output files wasn't clickable). Backticks are where agents put
// filenames, and the KNOWN-extension gate keeps backticked dotted identifiers (`np.array`, `s.color`,
// `romp.kernelPort`) and version numbers (`0.4.293`) reading as prose — an unknown extension stays text.
export const BARE_FILE_EXTS = new Set([
  "md", "txt", "rst", "py", "ts", "tsx", "js", "jsx", "mjs", "cjs", "json", "jsonl", "csv", "tsv",
  "pdf", "png", "jpg", "jpeg", "gif", "svg", "webp", "html", "htm", "css", "scss", "sh", "bash", "zsh",
  "bats", "yaml", "yml", "toml", "ini", "cfg", "conf", "xml", "ipynb", "rs", "go", "java", "c", "h",
  "cpp", "hpp", "cc", "rb", "php", "sql", "log", "lock", "tex", "bib", "zip", "tar", "gz", "tgz",
  "mp4", "mov", "mp3", "wav", "vsix", "plist", "diff", "patch",
]);
export function looksLikeBareFileName(tok: string): boolean {
  if (tok.includes("/") || tok.includes(":")) return false;
  const dot = tok.lastIndexOf(".");
  if (dot <= 0) return false;                                                // needs a name before the extension
  return BARE_FILE_EXTS.has(tok.slice(dot + 1).toLowerCase());
}
// One finder covers the file: scheme, the slashed-path alternative, and the bare-filename alternative.
// The kernel's _path_tokens is a port of it (kernel.py), and both sides run the same fixture — a token
// the kernel never saw is a verdict the client can never look up. Its TEXT is that contract; how it is
// run is PathTokenScanner's business (below) — the g-flag loop it was written for is quadratic.
export const CLICKABLE_PATH_RE = /file:\/\/\/?[^\s<>"'`)]+|[~.\w\-]*\/[~.\w\-/]*[\w\-]|[\w\-][\w\-.]*\.[A-Za-z0-9]{1,8}/gi;
// Trailing sentence punctuation is left out of a token, not swallowed by it ("see a/b.md." links a/b.md).
// The characters are the source; the regex is built from them (the kernel mirrors it as _PATH_TRAIL_RE).
export const TRAILING_PUNCT = ".,;:!?)]}>\"'`";
export const TRAILING_PUNCT_RE = new RegExp("[" + TRAILING_PUNCT.replace(/[\\\]^-]/g, "\\$&") + "]+$");
// The token's trailing punctuation, found from the END. TRAILING_PUNCT_RE's `+$` is tried from every
// position of the token and backs off one character at a time when the end is not there, which is
// quadratic on a long token made of punctuation: a token of 40K dots and a slash (the path arm matches
// it whole) cost 1.5 s in the trim alone. Shaped like the regex's match — [the run] or null — because
// that is how the walk reads it.
function trailingPunct(tok: string): [string] | null {
  let i = tok.length;
  while (i > 0 && TRAILING_PUNCT.includes(tok[i - 1])) i--;
  return i < tok.length ? [tok.slice(i)] : null;
}

// ── a linear-time driver for CLICKABLE_PATH_RE ────────────────────────────────────────────────────
// Run with the g flag, the engine restarts at every position, and on an unbroken run of word characters
// both path arms scan to the run's end and back before failing — quadratic in the run's length: one
// slash plus a 40K-character run of hex, words or dashes (a hash, a separator line, a minified dump)
// cost 3-5 s, per text node, on the main thread. A todo's detail has no length cap, and the
// Waiting-on-you pane re-links every session's detail on every feed frame, so one session's detail could
// freeze the pane for every reader. The regex's text is the kernel's parity contract and stays; this
// drives it in linear time. It tries the three arms in the regex's own order at each position, as
// sticky regexes cut from the one source, and remembers what a failure PROVES about the positions ahead:
//   - the path arm `[~.\w\-]*\/[~.\w\-/]*[\w\-]` failing at i fails at every later position of the same
//     run of [~.\w\-/] characters — the first slash it can reach from there is the same one or a later
//     one, and the word character it needs after that slash is drawn from a smaller suffix of the run;
//   - the bare arm `[\w\-][\w\-.]*\.[A-Za-z0-9]{1,8}` failing at i fails at every later position of the
//     same run of [\w\-.] characters — the dot-then-alphanumeric it needs is drawn from a smaller suffix;
//   - the URI arm starts only at an f or F, and its `file:` cannot lie inside either run (a colon is in
//     neither class), so a dead run's positions are tried for it as cheaply as any other.
// Each arm therefore scans a run at most once beyond its matches in it, and the text costs time linear
// in its length. The matches are exactly the regex's — pinned by a differential test over the regex
// itself at every start position, and by the kernel parity fixture (path-links.test.ts).
const [URI_ARM, PATH_ARM, BARE_ARM] = CLICKABLE_PATH_RE.source.split("|").map((arm) => new RegExp(arm, "iy"));
const isWordCh = (c: number): boolean => (c >= 48 && c <= 57) || (c >= 65 && c <= 90) || (c >= 97 && c <= 122) || c === 95;   // \w
const isBareStartCh = (c: number): boolean => isWordCh(c) || c === 45;              // [\w\-]
const isBareCh = (c: number): boolean => isBareStartCh(c) || c === 46;              // [\w\-.]
const isPathCh = (c: number): boolean => isBareCh(c) || c === 126 || c === 47;      // [~.\w\-/]
function runEnd(text: string, i: number, inRun: (c: number) => boolean): number {
  while (i < text.length && inRun(text.charCodeAt(i))) i++;
  return i;
}
export class PathTokenScanner {
  private pathDead = 0;   // the path arm is proven to fail at every position before this one
  private bareDead = 0;   // the bare arm likewise
  constructor(private readonly text: string) {}
  /** The first match at or after `from`, as [start, end) — what CLICKABLE_PATH_RE.exec finds with
   *  lastIndex = from — or null. Successive calls must not move `from` backwards. */
  next(from: number): [number, number] | null {
    const t = this.text, n = t.length;
    for (let i = from; i < n; i++) {
      const c = t.charCodeAt(i);
      if (c === 0x66 || c === 0x46) {                       // f / F — the only characters a URI can start at
        URI_ARM.lastIndex = i;
        if (URI_ARM.test(t)) return [i, URI_ARM.lastIndex];
      }
      if (!isPathCh(c)) continue;                           // neither path arm can start here
      if (i >= this.pathDead) {
        PATH_ARM.lastIndex = i;
        if (PATH_ARM.test(t)) return [i, PATH_ARM.lastIndex];
        this.pathDead = runEnd(t, i, isPathCh);
      }
      if (isBareStartCh(c) && i >= this.bareDead) {
        BARE_ARM.lastIndex = i;
        if (BARE_ARM.test(t)) return [i, BARE_ARM.lastIndex];
        this.bareDead = runEnd(t, i, isBareCh);
      }
    }
    return null;
  }
}

/** One link the walk emitted: the span, what it opens, and whether the kernel stat'd that target this
 *  build (a fixed mention) — the chat's figure pass wants exactly these. */
export interface PathLinkHit { el: HTMLElement; open: string; verified: boolean }

// Mark bare file:// URLs AND bare file paths inside `root`'s text — a relative `design/foo.md` too,
// resolved against a session's cwd by whoever opens it (the user 2026-07-06). Inside INLINE <code> a
// slash-less filename with a known extension marks too; only FENCED <pre> blocks and text already inside
// a link are skipped. Text nodes only: an element the caller already made a link stays one.
// `pathLinks` (the user 2026-08-09): the kernel's verdict on every path-shaped token in this text
// (build_session's _path_links — tier 1 exact stat, tiers 2/3 a unique repo-list match that FIXES a
// shortened mention to its real file). When the map is present, a token links ONLY if it's in the map,
// and it opens the map's value — so `render.js` in prose stops 404ing, and hover shows the real target.
// Every shape gate still applies; the map only ever narrows. No map at all (an old kernel, a cached
// payload, a surface the kernel never judged — a todo's detail) keeps shape-only linking.
// file:// URIs are explicit absolute paths — never gated on the map.
// Returns the hits in document order, so a caller's "first mention" is the walk's first.
export function linkifyPathTokens(root: HTMLElement, sid?: string | null, pathLinks?: Record<string, string>): PathLinkHit[] {
  const hits: PathLinkHit[] = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes: Text[] = [];
  let n: Node | null;
  while ((n = walker.nextNode())) nodes.push(n as Text);
  for (const tn of nodes) {
    if (tn.parentElement?.closest("a, .file-uri-link, pre")) continue;   // already a link, or a fenced code block
    const inCode = !!tn.parentElement?.closest("code");                  // inline code — where bare filenames may link
    const text = tn.data;
    if (!text.includes("/") && !(inCode && text.includes("."))) continue;   // cheap pre-filter: no slash (and, in code, no dot) → nothing here
    const scan = new PathTokenScanner(text);
    const frag = document.createDocumentFragment();
    let last = 0, any = false, from = 0, m: [number, number] | null;
    while ((m = scan.next(from))) {
      const [start, end] = m;
      from = end;                                   // a token that stays prose: the scan resumes after all of it
      let tok = text.slice(start, end);
      const trail = trailingPunct(tok);             // don't grab a sentence's closing punctuation
      if (trail) tok = tok.slice(0, tok.length - trail[0].length);
      if (!tok) continue;
      const isUri = /^file:\/\//i.test(tok);
      if (!isUri && !looksLikeFilePath(tok) && !(inCode && looksLikeBareFileName(tok))) continue;   // "and/or", `np.array` etc. — leave as prose
      const fixed = !isUri && pathLinks ? pathLinks[tok] : undefined;   // the kernel's verdict, when it rendered one
      if (!isUri && pathLinks && typeof fixed !== "string") continue;   // checked against the filesystem: no such file (or several) → prose
      if (start > last) frag.appendChild(document.createTextNode(text.slice(last, start)));
      const open = isUri ? fileUriToPath(tok) : (fixed ?? tok);
      const link = isUri ? fileUriLink(tok) : openPathLink(tok, open, true, sid);
      frag.appendChild(link);
      hits.push({ el: link, open, verified: !isUri && typeof fixed === "string" });   // the kernel stat'd a fixed one this build
      last = start + tok.length;
      from = last;                                  // a linked token: resume right after what was linked — its trimmed tail is prose
      any = true;
    }
    if (!any) continue;
    if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
    tn.replaceWith(frag);
  }
  return hits;
}
