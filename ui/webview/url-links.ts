// An http(s) URL in running text becomes a link, on the surfaces whose text never goes through the Markdown
// renderer (the user 2026-09-08, whose todo titles carried pull-request URLs that stayed plain text): a user
// todo's one-line text and its detail, on the chat's todo card, in its Reply modal, and in the Waiting-on-you
// pane; a pinned note's line and detail, which share the todo row's linkers (render.ts). The chat's own
// messages never needed this: md() renders them, and marked's GFM autolink makes an <a> of every bare URL
// before the path walk runs, which is why path-links.ts's gate refuses a token holding `:` or `//` with the
// note that http(s) links "are already <a>". A todo's text is set with textContent, so nothing had made them.
//
// The grammar is the file viewer's (it lived in file-view-links.ts and moved here; the viewer imports it back):
// the scheme, then everything up to whitespace or a character no URL carries unescaped in prose (a quote, an
// angle bracket, a backtick), then trailing sentence punctuation left out (`see https://x.y/z.` links
// https://x.y/z), and a closing bracket left out when the URL holds no opening partner for it
// (`(see https://x.y/z)` ends before the paren; a Wikipedia-style `https://x.y/Foo_(bar)` keeps its own).
//
// linkifyUrls walks the TEXT NODES of an element the caller already built (path-links.ts textUnits: the same
// walk the path linkifier uses), so no text is ever parsed as markup: the anchor's textContent is the URL as
// typed, its href the same string, target _blank with rel noopener noreferrer, the URL as its title. Text
// already inside a link (DEAD_TEXT) is read but never marked, so a caller that runs this BEFORE the path walk
// (the todo linkers do) leaves the walk a URL as dead text: a path-shaped query value inside it
// (`https://x.y/q?f=/docs/a.md`) is not a path. What a click DOES is the hosting document's: the chat's
// document-level a[href] delegate opens every absolute-scheme anchor (web: the browser's tab; VS Code: the
// host's openExternal), and a pane without that delegate installs installUrlLinkOpener (the PR opener's
// click-safe mechanics, link-opener.ts), so the click never reaches the row's fold beneath the link.
import { textUnits, spanHolding, rewriteSpan, DEAD_TEXT } from "./path-links";
import type { TextSpan } from "./path-links";
import { installLinkOpener, anchorHrefAt } from "./link-opener";
import type { OpenerDoc, OpenerPost, OpenerEnv } from "./link-opener";

/** The class the URL anchors this module mints in prose wear; the sheets and the pane opener key on it. */
export const URL_LINK_CLASS = "url-link";

// An http(s) URL in running text: the scheme, then everything up to whitespace or a character no URL carries
// unescaped in prose or code (a quote, an angle bracket, a backtick).
const URL_RE = /https?:\/\/[^\s<>"'`]+/gi;
// Sentence punctuation a URL is followed by, not part of: trimmed from the end, then a closing bracket that
// has no opening partner inside the URL.
const URL_TRAIL = ".,;:!?'\"";
const PAIRS: Record<string, string> = { ")": "(", "]": "[", "}": "{" };
const OPENERS: Record<string, string> = Object.fromEntries(Object.entries(PAIRS).map(([close, open]) => [open, close]));
// The trim reads the candidate ONCE: a count of closers minus openers per bracket kind, then a walk back from the
// end that strips a trail character (no bracket, so the counts stand) or a closer whose kind still has more closers
// than openers (and takes one off that kind's count), and stops at anything else. The loop it replaced re-counted
// the whole candidate for every closer it stripped, quadratic on a URL followed by a run of closers: 40K of them
// took five seconds, and a todo's text runs through this on every Waiting pane frame and every chat push (the
// 2026-09-09 review). Same verdicts: a strip changes exactly the count the walk keeps.
function trimUrl(u: string): string {
  const net: Record<string, number> = { ")": 0, "]": 0, "}": 0 };   // closers minus openers, per kind
  for (const c of u) { if (c in net) net[c]++; else if (c in OPENERS) net[OPENERS[c]]--; }
  let end = u.length;
  while (end > 0) {
    const last = u[end - 1];
    if (URL_TRAIL.includes(last)) { end--; continue; }
    if (last in net && net[last] > 0) { net[last]--; end--; continue; }   // one more closer than opener: it closes the sentence's bracket
    break;
  }
  return end === u.length ? u : u.slice(0, end);
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
/** The URLs in `text` as [start, end) ranges of it: exactly what urlSegments would wrap. */
export function urlRanges(text: string): Array<[number, number]> {
  const out: Array<[number, number]> = [];
  let at = 0;
  for (const s of urlSegments(text)) { if (s.href) out.push([at, at + s.text.length]); at += s.text.length; }
  return out;
}

export interface UrlLinkOptions {
  /** the anchors' class (URL_LINK_CLASS unless the surface has its own: the viewer's fv-url) */
  className?: string;
  /** the elements whose text is one unit to the pass (the viewer's LINE_UNITS); absent, each text node is its own */
  unit?: string;
  /** the ancestors whose text is read but never marked (DEAD_TEXT: a link already made, an inline SVG) */
  skip?: string;
  /** false: the anchor is not draggable, so a press-drag on it selects the text under it (the viewer's rule) */
  draggable?: boolean;
}

/** Mark the URLs in `root`'s text as anchors that open a new tab (target _blank, rel noopener noreferrer, the
 *  URL as the title, the URL as typed as the text). Text already inside a link, and a URL cut across two text
 *  nodes, are left alone. Returns the anchors made, in document order. */
export function linkifyUrls(root: HTMLElement, opts: UrlLinkOptions = {}): HTMLAnchorElement[] {
  const made: HTMLAnchorElement[] = [];
  const doc = root.ownerDocument || document;
  const cls = opts.className || URL_LINK_CLASS;
  for (const u of textUnits(root, opts.unit, opts.skip || DEAD_TEXT)) {
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
      a.className = cls;
      a.setAttribute("href", s.href);   // as an attribute: the openers read getAttribute("href"), and a stand-in without a reflecting property then agrees with the browser
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.title = s.href;
      if (opts.draggable === false) a.setAttribute("draggable", "false");
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

/** An http(s) address, and nothing else: what this module's anchors and the todo's own `link` may carry. */
export const isWebUrl = (href: string): boolean => /^https?:\/\/[^\s/?#]+/i.test(href);
/** The href of a URL link this module wrote, at or above `t`; null for any other element. */
export const urlLinkHrefAt = (t: EventTarget | null): string | null => anchorHrefAt(t, "a." + URL_LINK_CLASS + "[href]", isWebUrl);

/** Follow a URL link the way the panes follow a PR link (link-opener.ts): installed ONCE per pane document, on
 *  the capture phase, so the click never reaches the row handler beneath the link. The chat pane does NOT
 *  install this; its own a[href] delegate already opens every absolute-scheme anchor. */
export function installUrlLinkOpener(doc: OpenerDoc, post: OpenerPost, env?: OpenerEnv): void {
  installLinkOpener(doc, post, urlLinkHrefAt, env);
}

// A GitHub pull request or issue: the owner, the repository and the number, whatever follows the number (a tab,
// a comment's fragment, a query).
const GITHUB_REF_RE = /^https?:\/\/github\.com\/([^/?#]+)\/([^/?#]+)\/(?:pull|issues)\/(\d+)(?:[/?#]|$)/i;
/** A URL as a chip's label, the part that tells two links apart kept in view: a GitHub pull request or issue reads
 *  `owner/repo#N` (the form pr-links.ts titles a `#N` reference with; the owner stays, since a fork and its
 *  upstream share a name and their numbers overlap); any other address is the host and the last two path
 *  segments with the middle elided (`example.invalid/…/docs/plan`), or the whole address without its scheme and
 *  trailing slash when the path is that short. The chip's pill cuts a long label from the END (32% of the row,
 *  text-overflow ellipsis), so the old label, the address minus its scheme, lost exactly its distinguishing tail
 *  (`github.com/example-org/notes-…` for two todos on two pull requests; the 2026-09-09 review). The whole address
 *  is the chip's title, and the Reply modal shows the label whole. */
export function urlChipLabel(href: string): string {
  const gh = GITHUB_REF_RE.exec(href);
  if (gh) return gh[1] + "/" + gh[2] + "#" + gh[3];
  const bare = href.replace(/^https?:\/\//i, "").replace(/\/+$/, "");
  if (!bare) return href;
  const cut = bare.search(/[?#]/);                                  // the query and fragment ride the last segment
  const head = cut < 0 ? bare : bare.slice(0, cut), tail = cut < 0 ? "" : bare.slice(cut);
  const segs = head.split("/");                                     // the host, then the path's segments
  if (segs.length <= 3) return bare;
  return segs[0] + "/…/" + segs.slice(-2).join("/") + tail;
}
/** The chip itself: an anchor with URL_LINK_CLASS (so the pane opener serves it) plus the caller's chip class,
 *  the label above as its text, the full address as its title, opening in a new tab. */
export function urlChip(href: string, chipClass: string): HTMLAnchorElement {
  const a = document.createElement("a");
  a.className = URL_LINK_CLASS + " " + chipClass;
  a.setAttribute("href", href);
  a.target = "_blank";
  a.rel = "noopener noreferrer";
  a.title = href;
  a.textContent = urlChipLabel(href);
  return a;
}
