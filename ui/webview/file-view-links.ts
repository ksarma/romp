// Links inside a file the viewer shows (the user 2026-09-07): an http(s) URL in the text opens in a new tab, a
// file path opens in the viewer, and a Markdown link's target follows the same two rules. One pass over the TEXT
// NODES of a body the viewer has already built, never over its HTML string: hljs's markup and the sanitizer's
// verdicts stand, no raw file text is ever parsed as markup, and a row's text reads exactly as the file's after
// the pass (the comments panel's Raw index checks every row against the file character by character, anchor-map.ts
// rawIndex; a pass that changed one character would unmap every comment). The pass ADDS elements around runs of
// text and nothing else.
//
// The pass reads a LINE at a time, not a text node (path-links.ts textUnits, under LINE_UNITS): the highlight
// wraps a shell or template substitution in a span of its own, so `"$HOME/docs/a.md"` reaches the DOM as three
// text nodes, and a walk over the third alone read `/docs/a.md` as an absolute path that was never written (the
// 2026-09-07 review, the round's one high finding). Over the line's joined text the token is `HOME/docs/a.md`,
// glued to the `$` before it, and the gate below refuses a token glued to anything but an opener. A token the
// highlight cut through (its text in two nodes) is left as it is, never re-read as its pieces.
//
// The path grammar is the chat's (path-links.ts: the one matcher, the one span, the one click act), run with the
// walk's options for a surface that is code rather than prose, plus one gate of its own, viewerPathGate. The chat
// has the kernel's stat verdict to narrow its matches; this surface has no verdict and narrows by shape, and every
// false link is noise on a surface the person reads for hours. The gate's grammar, in full (docs/guide.md says the
// same in the user's words): a token links when it has a slash and its last segment has a letter-led extension of
// one to eight letters or digits (a dotfile only under an anchored start: `/`, `./`, `../`, `~/`); it is not glued
// to the character before it (the line's start, whitespace or an opener must precede it: a quote, a bracket, `=`,
// `,`, `;`, `|`), which is what cuts `$HOME/docs/a.md`, `${dir}/out.json`, `$(ROOT)/src/x.c`, `@scope/pkg/index.js`,
// `C:/Users/x/file.txt` and `git@host:user/repo.git` down to prose; an unanchored token's first segment does not read
// as a hostname (`www.` or dotted labels ending in two or more letters: `www.example.org/docs/index.html`,
// `example.com/index.html`); an unanchored token is not the specifier of an import (`import x from "lodash/fp.js"`,
// `require("pkg/sub.js")`); and a `~` start is `~/` (`~user/x.md` names a home the kernel does not expand). A local
// file:// URI (an empty authority, or `localhost`) links as written. A relative token resolves against the shown
// file's own directory (a file's mentions are written from where the file is), an absolute or `~/` one passes to the
// kernel as written (it expands `~` and reads the file's session's machine), and the resolved path is normalized
// once, here (`docs/../src/app.py` opens, and is titled, listed and browsed, as `src/app.py`). A `:12` written after
// a path (or GitHub's `#L12`) rides in the link and the viewer scrolls to that line.
//
// What a click does is the viewer's (file-view.ts binds the body's delegate: the path act opens the file through
// the host's opener, a URL anchor opens itself, a modified click opens either in a tab of its own). This module
// marks; it binds no action.
import { linkifyPathTokens, markPathLink, fileUriToPath, isFileUri, LINE_SUFFIX_RE, textUnits, spanHolding, rewriteSpan, type TextSpan } from "./path-links";

/** The URL anchors this module mints wear this class; the viewer's delegate and the sheets key on it. */
export const URL_LINK_CLASS = "fv-url";
/** A Markdown link to a section of the shown document (`#install`): the viewer's delegate scrolls to the target
 *  when the document has one, and never lets the click move the hosting document. */
export const FRAG_LINK_CLASS = "fv-frag";
/** An anchor with no target the viewer can follow (the sanitizer removed it; a section the document does not
 *  have): dressed as a dead link, with its title saying why (fail loudly, never a silent dead end). */
export const DEAD_LINK_CLASS = "fv-dead";
export const DEAD_LINK_TITLE = "Not a link the viewer can follow: its target is neither a web address nor a file on the session's machine";
export const noSectionTitle = (id: string): string => "No anchor named \u201c" + id + "\u201d in this document (headings carry none here)";

/** The elements whose text is one unit to the pass: a code view's row, a rendered block (a paragraph, a list item,
 *  a cell, a heading, a fenced block, a quote). Text under none of these is a unit of its own. */
export const LINE_UNITS = ".fv-cl, p, li, td, th, dt, dd, h1, h2, h3, h4, h5, h6, pre, blockquote, caption, figcaption, summary";

// An http(s) URL in running text: the scheme, then everything up to whitespace or a character no URL carries
// unescaped in prose or code (a quote, an angle bracket, a backtick).
const URL_RE = /https?:\/\/[^\s<>"'`]+/gi;
// Sentence punctuation a URL is followed by, not part of: trimmed from the end, then a closing bracket that
// has no opening partner inside the URL (`(see https://x.y/z)` ends before the paren; a Wikipedia-style
// `https://x.y/Foo_(bar)` keeps its own).
const URL_TRAIL = ".,;:!?'\"";
const PAIRS: Record<string, string> = { ")": "(", "]": "[", "}": "{" };
function trimUrl(u: string): string {
  for (;;) {
    const last = u[u.length - 1];
    if (URL_TRAIL.includes(last)) { u = u.slice(0, -1); continue; }
    const open = PAIRS[last];
    if (open) {
      let depth = 0;
      for (const c of u) { if (c === open) depth++; else if (c === last) depth--; }
      if (depth < 0) { u = u.slice(0, -1); continue; }   // one more closer than opener: it closes the sentence's bracket
    }
    return u;
  }
}
/** `text` cut into runs, each a URL (`href` set) or plain text; the URLs trimmed of trailing punctuation. */
export function urlSegments(text: string): Array<{ text: string; href?: string }> {
  const out: Array<{ text: string; href?: string }> = [];
  let last = 0;
  URL_RE.lastIndex = 0;
  for (let m: RegExpExecArray | null; (m = URL_RE.exec(text));) {
    const u = trimUrl(m[0]);
    if (!u || !/^https?:\/\/[^/?#]+/i.test(u)) { URL_RE.lastIndex = m.index + m[0].length; continue; }   // a bare scheme, no host
    if (m.index > last) out.push({ text: text.slice(last, m.index) });
    out.push({ text: u, href: u });
    last = m.index + u.length;
    URL_RE.lastIndex = last;
  }
  if (!out.length) return [{ text }];
  if (last < text.length) out.push({ text: text.slice(last) });
  return out;
}

// The gate's pieces (the grammar is written out in the header). What may stand right before a token: nothing (the
// line's start), whitespace, or an opener; a token glued to anything else is the tail of something the matcher
// cut through.
const OPENERS = " \t\"'`(<[{=,;|\u201c\u2018\u00ab";
const ANCHORED_RE = /^(?:~\/|\.{1,2}\/|\/)/;
// a first segment that reads as a hostname
const WWW_RE = /^www\./i;
const HOST_RE = /^[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}$/i;
// the text before a bare specifier in an import: `import x from "`, `import "`, `export * from "`, `require("`, `import("`
const IMPORT_BEFORE_RE = /\b(?:import|export|from|require)\s*\(?\s*["'`]$/;

/** The viewer's gate over a token the shared shape gates passed; `ctx` is the line's text and the token's offset in
 *  it (the walk hands both over), without which only the token's own shape is judged. */
export function viewerPathGate(tok: string, ctx?: { text: string; at: number }): boolean {
  if (isFileUri(tok)) return true;
  if (!tok.includes("/")) return false;
  if (tok.startsWith("~") && !tok.startsWith("~/")) return false;      // `~user/x.md`: a home the kernel does not expand
  const base = tok.slice(tok.lastIndexOf("/") + 1);
  const dot = base.lastIndexOf(".");
  if (dot < 0 || !/^[A-Za-z][A-Za-z0-9]{0,7}$/.test(base.slice(dot + 1))) return false;
  const anchored = ANCHORED_RE.test(tok);
  if (dot === 0 && !anchored) return false;                            // a dotfile links under an anchored start only
  if (!anchored) {
    const first = tok.slice(0, tok.indexOf("/"));
    if (WWW_RE.test(first) || HOST_RE.test(first)) return false;       // a site, not a folder
  }
  if (ctx) {
    const before = ctx.at > 0 ? ctx.text[ctx.at - 1] : "";
    if (before && !OPENERS.includes(before)) return false;             // glued to a substitution, a scope, a drive, a host
    if (!anchored && IMPORT_BEFORE_RE.test(ctx.text.slice(0, ctx.at))) return false;   // a package specifier
  }
  return true;
}

/** `p` with its `.` and `..` segments resolved and doubled slashes dropped, lexically: `/a/b/../c.md` is `/a/c.md`,
 *  `docs/../src/app.py` is `src/app.py`. A `..` above the root stays at the root; one above `~` or above a relative
 *  path's start is kept (`~/../x.md`, `../../x.md`: the kernel resolves those against the session). */
export function normalizePath(p: string): string {
  const abs = p.startsWith("/");
  const segs = p.split("/").filter((s, i, a) => s !== "." && (s !== "" || (i > 0 && i === a.length - 1)));   // a trailing "" keeps a directory's slash
  const out: string[] = [];
  for (const s of segs) {
    if (s === "..") {
      const top = out[out.length - 1];
      if (out.length && top !== ".." && top !== "~") { out.pop(); continue; }
      if (abs) continue;
    }
    out.push(s);
  }
  return (abs ? "/" : "") + out.join("/");
}

/** What a token in `filePath`'s text opens: a URI's own path; an absolute or `~/` path as written; a relative one
 *  joined onto the shown file's directory (`""` for a file named without one, which then resolves against the
 *  session's cwd on the kernel exactly as the file itself did). Normalized once, here. */
export function resolveViewerPath(tok: string, filePath: string): string {
  if (isFileUri(tok)) return normalizePath(fileUriToPath(tok));
  if (tok.startsWith("/") || tok.startsWith("~/")) return normalizePath(tok);
  return normalizePath(filePath.slice(0, filePath.lastIndexOf("/") + 1) + tok);
}

/** Mark the URLs in `root`'s text as anchors that open a new tab (target _blank, rel noopener noreferrer, the
 *  URL as the title), a line at a time (LINE_UNITS). Text already inside a link, and a URL the highlight cut
 *  into two nodes, are left alone. The anchors are not draggable (draggable=false here, `-webkit-user-drag: none`
 *  and `user-select: text` in the sheets): a press-drag that starts on one selects the text under it, as it does on
 *  a path link, instead of starting the browser's link drag; the click that ends the drag is the one the viewer's
 *  delegate cancels for an open selection. Returns the anchors made. */
export function linkifyUrls(root: HTMLElement): HTMLAnchorElement[] {
  const made: HTMLAnchorElement[] = [];
  const doc = root.ownerDocument || document;
  for (const u of textUnits(root, LINE_UNITS, "a, .file-uri-link")) {
    if (!/https?:\/\//i.test(u.text)) continue;
    const marks = new Map<TextSpan, Array<{ start: number; end: number; el: Node }>>();
    let at = 0;
    for (const s of urlSegments(u.text)) {
      const start = at;
      at += s.text.length;
      if (!s.href) continue;
      const span = spanHolding(u, start, at);
      if (!span) continue;
      const a = doc.createElement("a");
      a.className = URL_LINK_CLASS;
      a.href = s.href;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.title = s.href;
      a.setAttribute("draggable", "false");
      a.textContent = s.text;
      let list = marks.get(span);
      if (!list) { list = []; marks.set(span, list); }
      list.push({ start, end: at, el: a });
      made.push(a);
    }
    for (const [span, list] of marks) rewriteSpan(u, span, list);
  }
  return made;
}

/** Every text node under `root`, document order, through childNodes alone (a stand-in without a tree walker
 *  runs it as the browser does). */
function textNodesOf(root: Node): Text[] {
  const out: Text[] = [];
  const visit = (n: Node) => {
    for (const c of Array.from(n.childNodes || [])) { if (c.nodeType === 3) out.push(c as Text); else if (c.nodeType === 1) visit(c); }
  };
  visit(root);
  return out;
}

/** The whole pass over a text body the viewer built (the code view's <code>, a rendered markdown box): URLs first,
 *  so the path walk never sees the path-shaped tail of a URL, then the shared path walk under the viewer's gate and
 *  resolution, both a line at a time. A body with no text (a stand-in that parses no HTML, an empty file) is left as
 *  it is. */
export function linkifyFileText(root: HTMLElement, filePath: string): void {
  if (!textNodesOf(root).length) return;
  linkifyUrls(root);
  linkifyPathTokens(root, null, undefined, {
    inPre: true,
    accept: viewerPathGate,
    resolve: (tok) => resolveViewerPath(tok, filePath),
    lineSuffix: true,
    unit: LINE_UNITS,
  });
}

/** A Markdown link's destination, put in the form the sanitizer keeps and this module reads, BEFORE marked makes
 *  the HTML (mdBlock hands viewerWalkTokens to marked). DOMPurify drops an href whose first segment holds a colon
 *  (`notes.md:7` reads as a scheme) and one whose scheme is `file:`, and an anchor it stripped is a dead label the
 *  module can no longer sort. So a same-directory `name.ext:12` becomes `./name.ext:12`, and a local file:// URI
 *  becomes its path. Anything else is left as written: a real scheme is the browser's, and a URI on another host
 *  is not a path (path-links.ts isFileUri); those the sanitizer still removes render as dead links that say why. */
export function viewerLinkTarget(href: string): string {
  if (isFileUri(href)) return fileUriToPath(href);
  if (/^[^/:?#]*\.[A-Za-z][A-Za-z0-9]{0,7}:\d+(?::\d+)?(?:[?#].*)?$/.test(href)) return "./" + href;
  return href;
}
export function viewerWalkTokens(token: { type: string; href?: string | null }): void {
  if (token.type === "link" && typeof token.href === "string") token.href = viewerLinkTarget(token.href);
}

const withClass = (a: Element, cls: string): void => {
  const have = a.getAttribute("class") || "";
  if (!(" " + have + " ").includes(" " + cls + " ")) a.setAttribute("class", (have ? have + " " : "") + cls);
};

/** A rendered Markdown link's target, sorted the way the text is: a scheme (http:, https:, mailto:, …) or a
 *  protocol-relative `//host` opens a new tab, as the viewer always had it; a query alone (`?x=1`) is a web-style
 *  link to the page's own address and opens a new tab too (the viewer's document is never navigated); a fragment
 *  alone (`#section`) is the viewer's (FRAG_LINK_CLASS: the delegate scrolls to the element with that id when the
 *  document holds one, else the title says there is none, since marked gives headings no ids); anything else names
 *  a file, relative to the shown one, and the anchor becomes a path link (the shared shape on its own <a>, so
 *  `[**bold** text](docs/x.md)` keeps its label). marked percent-encodes a destination (`my%20notes.md`), so it is
 *  decoded first; a `#L12` or `:12` on the target is the line; a `?query` or other fragment is dropped from the
 *  path. The href comes off a path link: a browser must not follow it, and the chat's document-level opener reads
 *  only anchors with one. An anchor the sanitizer left without an href (a scheme it refuses, a file on another
 *  host) is dressed dead with the reason in its title, unless it is a named target and never was a link. Every
 *  attribute is set as one (an inline SVG's <a> has no target, rel, className or title property to write). */
export function linkMarkdownAnchors(root: HTMLElement, filePath: string): void {
  root.querySelectorAll("a").forEach((node) => {
    const a = node as HTMLElement;
    const href = a.getAttribute("href");
    if (href === null) {
      if (a.hasAttribute("name") || a.hasAttribute("id")) return;
      withClass(a, DEAD_LINK_CLASS);
      a.setAttribute("title", DEAD_LINK_TITLE);
      return;
    }
    if (href.startsWith("#")) {
      let id = href.slice(1);
      try { id = decodeURIComponent(id); } catch { /* a malformed escape: the spelling as written */ }
      const hit = id ? Array.from(root.querySelectorAll("[id]")).find((e) => e.getAttribute("id") === id) : undefined;
      withClass(a, FRAG_LINK_CLASS);
      if (hit) { a.dataset.frag = id; a.setAttribute("title", "Go to " + id); }
      else { withClass(a, DEAD_LINK_CLASS); a.setAttribute("title", noSectionTitle(id)); }
      return;
    }
    if (href.startsWith("//") || /^[a-z][a-z0-9+.-]*:/i.test(href)) {
      a.setAttribute("target", "_blank");
      a.setAttribute("rel", "noopener");
      return;
    }
    let dest = href;
    try { dest = decodeURI(href); } catch { /* a malformed escape: the spelling as written */ }
    const cut = dest.search(/[?#]/);
    const tail = cut >= 0 ? dest.slice(cut) : "";
    let pathPart = cut >= 0 ? dest.slice(0, cut) : dest;
    // a line on the path itself (`a.md:12`) or in the fragment (`a.md#L12`)
    let line: string | null = null;
    const colon = /:(\d+)(?::\d+)?$/.exec(pathPart);
    if (colon) { line = colon[1]; pathPart = pathPart.slice(0, colon.index); }
    else if (tail.startsWith("#")) { const m = LINE_SUFFIX_RE.exec(tail); if (m && m[2]) line = m[2]; }
    if (!pathPart) {
      a.setAttribute("target", "_blank");
      a.setAttribute("rel", "noopener noreferrer");
      return;
    }
    a.removeAttribute("href");
    markPathLink(a, resolveViewerPath(pathPart, filePath), true);
    if (line) { a.dataset.line = line; a.setAttribute("title", a.getAttribute("title") + ":" + line); }
  });
}
