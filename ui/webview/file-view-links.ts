// Links inside a file the viewer shows (the user 2026-09-07): an http(s) URL in the text opens in a new tab, a
// file path opens in the viewer, and a Markdown link's target follows the same two rules. One pass over the TEXT
// NODES of a body the viewer has already built, never over its HTML string: hljs's markup and the sanitizer's
// verdicts stand, no raw file text is ever parsed as markup, and a row's text reads exactly as the file's after
// the pass (the comments panel's Raw index checks every row against the file character by character, anchor-map.ts
// rawIndex; a pass that changed one character would unmap every comment). The pass ADDS elements around runs of
// text and nothing else.
//
// The path grammar is the chat's (path-links.ts: the one matcher, the one span, the one click act), run with the
// walk's options for a surface that is code rather than prose, plus one gate of its own, viewerPathGate: a token
// links only when it has a slash AND its last segment has a letter-led extension. The chat links an anchored token
// without one (`./foo`, `/usr/bin`) and a bare filename inside backticks; in code those are import specifiers,
// routes and identifiers, and every false link is noise on a surface the person reads for hours. The chat has the
// kernel's stat verdict to narrow its matches; this surface has no verdict and narrows by shape. A relative token
// resolves against the shown file's own directory (a file's mentions are written from where the file is), an
// absolute or `~/` one passes to the kernel as written (it expands `~` and reads the file's session's machine),
// and `..` segments pass through unnormalized: the kernel resolves and gates them (rewriteFigureSrcs, same rule).
// A `:12` written after a path (or GitHub's `#L12`) rides in the link and the viewer scrolls to that line.
//
// What a click does is the viewer's (file-view.ts binds the body's delegate: the path act opens the file through
// the host's opener, a URL anchor opens itself). This module marks; it binds no action.
import { linkifyPathTokens, markPathLink, fileUriToPath, LINE_SUFFIX_RE } from "./path-links";

/** The URL anchors this module mints wear this class; the viewer's delegate and the sheets key on it. */
export const URL_LINK_CLASS = "fv-url";

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

/** The viewer's gate over a token the shared shape gates passed: a slash, and a last segment with a letter-led
 *  extension of one to eight letters or digits after a name (`docs/a.md`, `~/.zshrc` under an anchored start;
 *  not `./foo`, `/api/users`, `1/2.5`, `and/or`). A file:// URI is a link as written. */
export function viewerPathGate(tok: string): boolean {
  if (/^file:\/\//i.test(tok)) return true;
  if (!tok.includes("/")) return false;
  const base = tok.slice(tok.lastIndexOf("/") + 1);
  const dot = base.lastIndexOf(".");
  if (dot < 0 || !/^[A-Za-z][A-Za-z0-9]{0,7}$/.test(base.slice(dot + 1))) return false;
  if (dot === 0) return /^(?:~\/|\.{1,2}\/|\/)/.test(tok);   // a dotfile links under an anchored start only
  return true;
}

/** What a token in `filePath`'s text opens: a URI's own path; an absolute or `~/` path as written; a relative one
 *  joined onto the shown file's directory (`""` for a file named without one, which then resolves against the
 *  session's cwd on the kernel exactly as the file itself did). `./` and `..` pass through: the kernel resolves them. */
export function resolveViewerPath(tok: string, filePath: string): string {
  if (/^file:\/\//i.test(tok)) return fileUriToPath(tok);
  if (tok.startsWith("/") || tok.startsWith("~/")) return tok;
  return filePath.slice(0, filePath.lastIndexOf("/") + 1) + tok;
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
const inLink = (tn: Text): boolean => {
  const p = tn.parentElement;
  return !!(p && typeof p.closest === "function" && p.closest("a, .file-uri-link"));
};

/** Mark the URLs in `root`'s text as anchors that open a new tab (target _blank, rel noopener noreferrer, the
 *  URL as the title). Text already inside a link is left alone. Returns the anchors made. */
export function linkifyUrls(root: HTMLElement): HTMLAnchorElement[] {
  const made: HTMLAnchorElement[] = [];
  const doc = root.ownerDocument || document;
  for (const tn of textNodesOf(root)) {
    const text = tn.data;
    if (!/https?:\/\//i.test(text) || inLink(tn)) continue;
    const segs = urlSegments(text);
    if (!segs.some((s) => s.href)) continue;
    const parent = tn.parentNode;
    if (!parent) continue;
    for (const s of segs) {
      if (s.href) {
        const a = doc.createElement("a");
        a.className = URL_LINK_CLASS;
        a.href = s.href;
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        a.title = s.href;
        a.textContent = s.text;
        parent.insertBefore(a, tn);
        made.push(a);
      } else {
        parent.insertBefore(doc.createTextNode(s.text), tn);
      }
    }
    parent.removeChild(tn);
  }
  return made;
}

/** The whole pass over a text body the viewer built (the code view's <code>, a rendered markdown box): URLs first,
 *  so the path walk never sees the path-shaped tail of a URL, then the shared path walk under the viewer's gate and
 *  resolution. A body with no text (a stand-in that parses no HTML, an empty file) is left as it is. */
export function linkifyFileText(root: HTMLElement, filePath: string): void {
  if (!textNodesOf(root).length) return;
  linkifyUrls(root);
  linkifyPathTokens(root, null, undefined, {
    inPre: true,
    accept: viewerPathGate,
    resolve: (tok) => resolveViewerPath(tok, filePath),
    lineSuffix: true,
  });
}

/** A rendered Markdown link's target, sorted the way the text is: a scheme (http:, https:, mailto:, …) or a
 *  protocol-relative `//host` opens a new tab, as the viewer always had it; a fragment alone (`#section`) is left
 *  as the sanitizer gave it; anything else names a file, relative to the shown one, and the anchor becomes a path
 *  link (the shared shape on its own <a>, so `[**bold** text](docs/x.md)` keeps its label). marked percent-encodes
 *  a destination (`my%20notes.md`), so it is decoded first; a `#L12` or `:12` on the target is the line; a `?query`
 *  or other fragment is dropped from the path. The href comes off: a browser must not follow it, and the chat's
 *  document-level opener reads only anchors with one. */
export function linkMarkdownAnchors(root: HTMLElement, filePath: string): void {
  root.querySelectorAll("a[href]").forEach((node) => {
    const a = node as HTMLAnchorElement;
    const href = a.getAttribute("href") || "";
    if (!href || href.startsWith("#")) return;
    if (href.startsWith("//") || /^[a-z][a-z0-9+.-]*:/i.test(href)) {
      a.target = "_blank";
      a.rel = "noopener";
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
    if (!pathPart) return;
    a.removeAttribute("href");
    markPathLink(a, resolveViewerPath(pathPart, filePath), true);
    if (line) { a.dataset.line = line; a.title += ":" + line; }
  });
}
