// GitHub pull-request references in rendered text become links to the PR page of the repository the
// session works in (the user 2026-09-06: a session's chat, its feed cards and its notes rendered
// "merged #199" and "fork PR #197" as plain text). The kernel names the repository per session —
// `githubRepo` (owner/repo, or null) on the session frame and on the feed's session rows, derived from
// the session tree's origin remote by the same parser the file viewer's GitHub link uses — and this
// module does the text work in ONE place for every surface: the chat's markdown (render.ts md()), its
// plain-text user-todo rows, the feed's card titles, distiller lines, checklists and modal (feed.ts),
// and the outline's goal rows (fleet.ts).
//
// Shapes that link — each needs a word boundary BEFORE it (start of text, whitespace, an opening
// bracket or quote, a comma/semicolon/colon), so a `#` glued to letters, a path or a URL never does:
//   #123               → https://github.com/<session repo>/pull/123
//   PR #123 / pull #123 (any case, the space optional) → the same; the whole phrase is the link
//   owner/repo#123     → https://github.com/owner/repo/pull/123 — a reference into another repository
// GitHub answers /pull/<n> for an ISSUE number with a redirect to /issues/<n>, so one form covers both.
//
// What never links: text inside <code> or <pre> (a colour `#fff`, a CSS id, a shell comment), text
// already inside an <a> (a GitHub URL marked autolinked, a [text](url)), a path link (.file-uri-link),
// and any `#` that is part of a word, a URL fragment or a colour literal — `#1EA1EB` and `#0c1a2e`
// fail the number shape (hex letters after the digits, or a leading zero; a PR number has neither).
// The cross-repo form also refuses a "repo" that reads like a FILENAME (`docs/x.html#12`, `src/app.py#3`
// — an extension-shaped tail after a dot): that is a path with a fragment, and a wrong link is worse
// than none. The cost is a repository literally named `something.js`, which stays plain text.
// A session with no GitHub repository (`githubRepo` null: no repo, no origin, or an origin elsewhere)
// links NOTHING, the cross-repo form included — the honest rendering is the plain text, never a
// guessed host.

/** One run of text; `href` marks a link, `label` its repo-qualified reference for the hover title. */
export interface PrRefSegment { text: string; href?: string; label?: string }

export const PR_LINK_CLASS = "pr-link";

// GitHub's own name rules: an owner is alphanumerics and hyphens (≤ 39), a repo may also carry `.`
// and `_`. A PR number has no leading zero and (with room to spare) at most seven digits.
const OWNER = "[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})";
const REPO = "[A-Za-z0-9_.-]{1,100}";
const NUM = "[1-9]\\d{0,6}";
// group 1 = the boundary character (re-emitted as text; empty at the start of the text)
// groups 2/3/4 = owner / repo / number of the cross-repo form
// group 5 = the number of a `PR #n` / `pull #n` phrase; group 6 = the number of a bare `#n`
// the trailing lookahead refuses a word character, another `#` or a `/` right after the number, which
// is what keeps `#12abc`, `#1EA1EB` and a `#12/x` path fragment out
const REF_SRC =
  "(^|[\\s(\\[{<,;:\"'“‘«])(?:" +
  "(" + OWNER + ")/(" + REPO + ")#(" + NUM + ")" +
  "|(?:PR|pull)\\s?#(" + NUM + ")" +
  "|#(" + NUM + ")" +
  ")(?![\\w#/])";

const REPO_SHAPE = /^[A-Za-z0-9][A-Za-z0-9-]{0,38}\/[A-Za-z0-9_.-]{1,100}$/;
const FILENAME_TAIL = /\.[A-Za-z0-9]{1,5}$/;   // `x.html`, `app.py`, `notes.md`: a path fragment, not a repo

/** The session repo as the kernel ships it, or null when it is absent or not owner/repo-shaped — a
 *  URL is only ever built from a value that passed this. */
export function validPrRepo(repo: string | null | undefined): string | null {
  return typeof repo === "string" && REPO_SHAPE.test(repo) ? repo : null;
}

export function prUrl(repo: string, n: string): string {
  return "https://github.com/" + repo + "/pull/" + n;
}

/** Split `text` into plain runs and PR-reference links against `repo`. Pure: no DOM. With no valid
 *  repo, or no reference in the text, the whole text comes back as one plain segment. */
export function prRefSegments(text: string, repo: string | null | undefined): PrRefSegment[] {
  const r = validPrRepo(repo);
  if (!r || !text || text.indexOf("#") < 0) return [{ text }];
  const re = new RegExp(REF_SRC, "gi");
  const out: PrRefSegment[] = [];
  let last = 0, m: RegExpExecArray | null;
  while ((m = re.exec(text))) {
    const start = m.index + m[1].length;          // the boundary character stays plain text
    const end = m.index + m[0].length;
    let target: string, n: string;
    if (m[4]) {
      if (FILENAME_TAIL.test(m[3])) continue;   // `docs/x.html#12`: a path's fragment; the scan resumes after it
      target = m[2] + "/" + m[3]; n = m[4];
    }
    else if (m[5]) { target = r; n = m[5]; }
    else { target = r; n = m[6]; }
    if (start > last) out.push({ text: text.slice(last, start) });
    out.push({ text: text.slice(start, end), href: prUrl(target, n), label: target + "#" + n });
    last = end;
  }
  if (!out.length) return [{ text }];
  if (last < text.length) out.push({ text: text.slice(last) });
  return out;
}

// Elements whose text never links: an existing link, code (inline or fenced), form controls, and
// the chat's own path links (a `docs/x.md#12`-shaped path must stay the path it is).
const SKIP_TAGS = new Set(["A", "CODE", "PRE", "SCRIPT", "STYLE", "TEXTAREA", "INPUT", "BUTTON", "SELECT", "OPTION", "SVG"]);
const SKIP_CLASSES = ["file-uri-link", "url-code-link"];

function skipElement(e: Element): boolean {
  if (SKIP_TAGS.has(String(e.tagName || "").toUpperCase())) return true;
  const cl = e.classList;
  return !!cl && SKIP_CLASSES.some((k) => cl.contains(k));
}

/** Turn the PR references in `root`'s text nodes into anchors (class pr-link, target _blank, rel
 *  noopener noreferrer, a title naming the repo-qualified reference). Skips <a>/<code>/<pre> subtrees
 *  and the chat's path links; a root that itself sits inside one of those is left alone. Returns the
 *  number of links made. Walks childNodes and edits through insertBefore/removeChild only, so a
 *  test's plain-object DOM stand-in runs it as the browser does. */
export function linkifyPrRefs(root: Node | null | undefined, repo: string | null | undefined): number {
  const r = validPrRepo(repo);
  if (!r || !root) return 0;
  const rootEl = root as Element;
  if (root.nodeType === 1 && typeof rootEl.closest === "function" && rootEl.closest("a, code, pre")) return 0;
  let made = 0;
  const visit = (node: Node): void => {
    const kids = Array.from(node.childNodes || []);   // snapshot: text children are replaced as we go
    for (const c of kids) {
      if (c.nodeType === 3) { made += linkifyTextNode(c, r); continue; }
      if (c.nodeType !== 1 || skipElement(c as Element)) continue;
      visit(c);
    }
  };
  visit(root);
  return made;
}

function linkifyTextNode(tn: Node, repo: string): number {
  const text = tn.textContent || "";
  if (text.indexOf("#") < 0) return 0;
  const segs = prRefSegments(text, repo);
  if (!segs.some((s) => s.href)) return 0;
  const parent = tn.parentNode;
  if (!parent) return 0;
  const doc: Document = tn.ownerDocument || document;
  let made = 0;
  for (const s of segs) {
    let node: Node;
    if (s.href) {
      const a = doc.createElement("a");
      a.className = PR_LINK_CLASS;
      a.href = s.href;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.title = s.label + " on GitHub";
      a.textContent = s.text;
      node = a;
      made++;
    } else {
      node = doc.createTextNode(s.text);
    }
    parent.insertBefore(node, tn);
  }
  parent.removeChild(tn);
  return made;
}

/** Follow a PR link the way the chat follows its links (render.ts's a[href] delegate): on the web
 *  dashboard the viewer's own browser opens a tab; in a VS Code webview the href goes to the host,
 *  which openExternal()s it (view-routing.ts routes `openLink` for every pane). Installed ONCE per pane
 *  document on the CAPTURE phase, so the click never reaches the card or row handlers beneath the link
 *  — a link inside a feed card must open the PR, not also open the card's modal; one inside an outline
 *  row must not also jump the chat. No per-anchor listener: the anchors are rebuilt on every push, and
 *  a listener on a rebuilt node is the click-safety bug ui/CLAUDE.md names. The chat pane does NOT
 *  install this — its own delegate already opens every absolute-scheme anchor the same way. */
export function installPrLinkOpener(
  doc: { addEventListener(type: string, fn: (e: Event) => void, capture?: boolean): void },
  post: ((msg: { type: string; href: string }) => void) | undefined,
  env: { protocol: () => string; open: (href: string) => void } = {
    protocol: () => (typeof location !== "undefined" ? location.protocol : ""),
    open: (href) => { window.open(href, "_blank", "noopener,noreferrer"); },
  },
): void {
  doc.addEventListener("click", (e: Event) => {
    const t = e.target as Element | null;
    const a = t && typeof t.closest === "function" ? (t.closest("a." + PR_LINK_CLASS + "[href]") as HTMLAnchorElement | null) : null;
    if (!a) return;
    const href = a.getAttribute("href") || "";
    if (!/^https:\/\/github\.com\//.test(href)) return;   // only the hrefs this module writes
    e.preventDefault();
    e.stopPropagation();
    const p = env.protocol();
    if (p === "http:" || p === "https:") env.open(href);
    else if (post) post({ type: "openLink", href });
  }, true);
}
