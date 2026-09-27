// The chat's path-aware emphasis (md-config.ts pathAwareEmphasis), the rule for a token's EDGE runs, executed over the REAL
// marked on the chat's two instances (chat-md.ts). md-emphasis-paths.test.ts runs the population note's two tables and
// md-emphasis-override.test.ts the interior-run edge and the stand-in's contract; this file pins what the 2026-09-20
// review's round 2 found beside them:
//   - a linkable token with a `_` run strictly inside it beside a character that can flank a delimiter run (`__init__.py`,
//     `_drafts/a_.md`, `/a/_b_`) is one word to the emphasis rule, its edge runs included. Round 1 hid the run inside and left the edge run visible,
//     and the built-in's closer scan then paired the edge run across the hidden middle with a partner outside the token
//     (the spec pairs it with the run inside, which the protection had taken away): `_see __init__.py now_` lost its
//     emphasis, `see __init__.py and stop__` bolded half the sentence, `_see _drafts/a_.md now_` cut the path from its
//     start and lost the kernel's link. Every row here rendered right on the tree before round 1 and wrong at its head;
//   - the class that test asks is the override's own, CommonMark 0.31.2 section 6.2's (Unicode whitespace, punctuation
//     or a symbol, `*` and `_` among them), read by CODE POINT on either side of the run (md-config.ts flankedInside).
//     The 2026-09-20 review's head asked marked's `punctuation` rule instead, written to exclude the delimiters and read
//     over one UTF-16 code unit, and the rule had two holes, both the failure it was added to stop (the 2026-09-21
//     review, A): an interior run whose only neighbour is a `*` (ASCII, excluded by design; the URI arm admits `*`) and
//     one whose neighbour is an astral punctuation mark or symbol (a lone surrogate to a one-unit read) left the token
//     un-whole, its end-edge run paired with a prose opener before it, and the walk linked a piece that is not the token.
//     The rows are in the URI arm alone: the path and bare arms are ASCII (path-links.ts CLICKABLE_PATH_RE, isWordCh),
//     so a `*` or a non-ASCII character splits a path token there and no row can arm either hole (the controls);
//   - a plain token, one with no such run inside, keeps the edge rule: its edge run opens or closes as the spec says, as
//     on the base grammar (`_see /tmp/x_`, `_x/y.md and more_`, `_see _posts/x.md now_`), also when another, protected
//     token stands in the same pair, and when the walk's ASCII word class splits an accented path into two tokens the
//     second of which begins with a run at its edge: recorded faces of the rule, pinned as they render;
//   - a backslash before an astral symbol masks three UTF-16 units as two; the override measures a run's position on the
//     unmasked tail with those escapes counted, so a run inside a token is refused whatever follows it. Only the escapes
//     marked masked count: one inside a link, a reflink, a code span or a tag is letters in the mask (marked masks those
//     before its escape rule runs), so it shortened nothing. Round 2 counted every escape in the tail and read a run one
//     position too far when a construct after it held an escaped emoji, refusing a plain token's start-edge opener and
//     letting a whole token's end-edge run pair (the review's closing pass); and it ran marked's escape rule over the
//     tail once per delimiter, where the override now reads the forms at the masked string's `++` positions and runs
//     the rule not at all;
//   - cost: one scan of the paragraph per masked string per parse, whatever the nested lexes marked runs on strings of
//     their own (a link's label, a `*` pair's or a `~~` pair's body) bring between two of the paragraph's delimiters: the
//     memo lives with the parse's lexer, keyed by masked string (md-config.ts linkableMemos). The 2026-09-20 review's
//     memo was a module-global most-recently-used list of eight: eight distinct such strings between two delimiters
//     evicted the paragraph's entry and every later prose delimiter rescanned the whole paragraph, a term quadratic in
//     its length that no cost row of the time could see, since every row hit the memo (the 2026-09-21 review, B: a 20 KB
//     paragraph of eight distinct `*` bodies per prose pair cost 13.8 to 16.9 times the base grammar with 571 rescans,
//     against a stated bound of four; the row is in the cost test below and read about one after the per-parse memo).
//     A run inside a token is refused before the built-in scans. Counted by execution, and measured as a ratio to the
//     base grammar on the same string in the same process, the best of interleaved passes, as
//     md-emphasis-override.test.ts measures; the bound, four, is a round number chosen with headroom for a loaded box
//     over the measured worst shape, the whitespace-free path run at 1.4 to 1.7 (loads 6 to 33), not a derived figure.
// The walk runs over a small DOM stand-in fed marked's HTML (no jsdom), the chat's own options minus the fenced gate, with
// a map holding the kernel-shaped keys (the tokens the kernel's tokeniser reads over the raw markdown), as the kernel's
// verdict would. Synthetic fixtures only: invented paths, a placeholder session id.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { Lexer, Marked } from "marked";
import { hideEdges } from "../test-dom-shim";
import * as chatMd from "./chat-md";
import { mdExtensions } from "./md-config";
import { linkifyPathTokens, PathTokenScanner } from "./path-links";

const SID = "11111111-2222-3333-4444-555555555555";
// the road before the fix: the singleton's configuration on a private instance
const base = new Marked({ gfm: true, breaks: false }, ...mdExtensions);
const baseHtml = (src: string): string => base.parse(src) as string;
const RENDERERS: Array<[string, (src: string) => string]> = [["a reply (chatMdHtml)", chatMd.chatMdHtml], ["the user's own words (userMdHtml)", chatMd.userMdHtml]];

// ── a DOM stand-in: text nodes, elements with attributes and a tag-and-class selector engine, fragments, a tree walker;
// every node hides its edges at creation (ui/test-dom-shim.ts hideEdges), so a failing assertion dumps a node's primitives
// and never its tree ──
type Compound = { tag: string | null; classes: string[] };
function parseSel(sel: string): Compound[] {
  return sel.split(",").map((s) => s.trim()).filter(Boolean).map((s) => {
    const m = /^([a-zA-Z][\w-]*)?((?:\.[\w-]+)*)$/.exec(s);
    if (!m) throw new Error("stand-in: unsupported selector " + s);
    return { tag: m[1] ? m[1].toUpperCase() : null, classes: (m[2].match(/\.[\w-]+/g) || []).map((c) => c.slice(1)) };
  });
}
class Txt {
  nodeType = 3;
  parentNode: El | null = null;
  constructor(public data: string) { hideEdges(this); }
  get textContent(): string { return this.data; }
  get parentElement(): El | null { return this.parentNode; }
  replaceWith(n: El | Txt | Frag): void {
    const p = this.parentNode!;
    const i = p.childNodes.indexOf(this);
    const kids = n instanceof Frag ? n.childNodes.slice() : [n];
    for (const k of kids) { if (k.parentNode) k.parentNode.removeChild(k); k.parentNode = p; }
    p.childNodes.splice(i, 1, ...kids);
    this.parentNode = null;
  }
}
class Frag { childNodes: Array<El | Txt> = []; constructor() { hideEdges(this); } appendChild(c: El | Txt): void { this.childNodes.push(c); } }
const kebab = (k: string): string => k.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
class El {
  nodeType = 1;
  tagName: string;
  parentNode: El | null = null;
  childNodes: Array<El | Txt> = [];
  attrs = new Map<string, string>();
  role: string | null = null;
  onkeydown: unknown = null; onmousedown: unknown = null; onmouseup: unknown = null; onmouseleave: unknown = null; oncontextmenu: unknown = null; ondragstart: unknown = null;
  constructor(tag: string) { this.tagName = tag.toUpperCase(); hideEdges(this); }
  get tabIndex(): number { return this.attrs.has("tabindex") ? Number(this.attrs.get("tabindex")) : -1; } set tabIndex(v: number) { this.attrs.set("tabindex", String(v)); }
  get parentElement(): El | null { return this.parentNode; }
  get className(): string { return this.attrs.get("class") || ""; } set className(v: string) { this.attrs.set("class", v); }
  get classes(): string[] { return this.className.split(/\s+/).filter(Boolean); }
  dataset: Record<string, string> = new Proxy({} as Record<string, string>, {
    get: (_, k) => this.attrs.get("data-" + kebab(String(k))) as string,
    set: (_, k, v) => { this.attrs.set("data-" + kebab(String(k)), String(v)); return true; },
    has: (_, k) => this.attrs.has("data-" + kebab(String(k))),
  });
  get textContent(): string { return this.childNodes.map((c) => c.textContent).join(""); }
  set textContent(v: string) { for (const c of this.childNodes) c.parentNode = null; this.childNodes = []; if (v !== "") this.appendChild(new Txt(v)); }
  private detach(n: El | Txt): void { const p = n.parentNode; if (p) { const i = p.childNodes.indexOf(n); if (i >= 0) p.childNodes.splice(i, 1); n.parentNode = null; } }
  appendChild<T extends El | Txt>(n: T): T { this.detach(n); this.childNodes.push(n); n.parentNode = this; return n; }
  removeChild<T extends El | Txt>(n: T): T { this.detach(n); return n; }
  setAttribute(k: string, v: string): void { this.attrs.set(k, v); }
  getAttribute(k: string): string | null { return this.attrs.has(k) ? (this.attrs.get(k) as string) : null; }
  hasAttribute(k: string): boolean { return this.attrs.has(k); }
  removeAttribute(k: string): void { this.attrs.delete(k); }
  matches(sel: string): boolean { return parseSel(sel).some((c) => (!c.tag || c.tag === this.tagName) && c.classes.every((k) => this.classes.includes(k))); }
  closest(sel: string): El | null { for (let x: El | null = this; x; x = x.parentNode) if (x.matches(sel)) return x; return null; }
  querySelectorAll(sel: string): El[] {
    const out: El[] = [];
    const visit = (n: El) => { for (const c of n.childNodes) if (c instanceof El) { if (c.matches(sel)) out.push(c); visit(c); } };
    visit(this);
    return out;
  }
}
/** Document-order nodes under `root`, as a browser's tree walker answers them (SHOW_ELEMENT = 1, SHOW_TEXT = 4). */
function walkNodes(root: El, what: number): Array<El | Txt> {
  const out: Array<El | Txt> = [];
  const walk = (n: El) => { for (const c of n.childNodes) { if (c instanceof Txt) { if (what & 4) out.push(c); } else { if (what & 1) out.push(c); walk(c); } } };
  walk(root);
  return out;
}
(globalThis as any).NodeFilter = { SHOW_ELEMENT: 1, SHOW_TEXT: 4 };
(globalThis as any).document = {
  createElement: (tag: string) => new El(tag),
  createTextNode: (s: string) => new Txt(s),
  createDocumentFragment: () => new Frag(),
  createTreeWalker: (root: El, what = 4) => { const nodes = walkNodes(root, what); let i = 0; return { nextNode: () => (i < nodes.length ? nodes[i++] : null) }; },
  activeElement: null as El | null,
};
// marked's HTML read into the stand-in: tags and text, the class attribute kept, the entities marked writes decoded
const VOID_TAGS = new Set(["BR", "HR", "IMG", "INPUT", "WBR"]);
const ENTITIES: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: "\"", "#39": "'" };
const unescapeHtml = (s: string): string => s.replace(/&(amp|lt|gt|quot|#39);/g, (_, k: string) => ENTITIES[k]);
function fromHtml(html: string): El {
  const root = new El("DIV");
  let cur = root;
  const re = /<\/([A-Za-z][\w-]*)\s*>|<([A-Za-z][\w-]*)([^>]*)>|([^<]+)/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(html))) {
    if (m[1]) { cur = cur.parentNode || root; continue; }
    if (m[2]) {
      const e = cur.appendChild(new El(m[2]));
      const c = /class="([^"]*)"/.exec(m[3] || "");
      if (c) e.className = c[1];
      if (!VOID_TAGS.has(e.tagName) && !/\/\s*$/.test(m[3] || "")) cur = e;
      continue;
    }
    cur.appendChild(new Txt(unescapeHtml(m[4])));
  }
  return root;
}

/** The chat's walk over `html`, the kernel's verdict standing in as a map that holds `keys`: what it linked, by target, in
 *  document order (render.ts's FENCE_WALK minus its fenced gate). */
function walkLinks(html: string, keys: string[]): string[] {
  const root = fromHtml(html);
  const map: Record<string, string> = {};
  for (const k of keys) map[k] = k;
  linkifyPathTokens(root as unknown as HTMLElement, SID, map, { inPre: true, preVerified: true, unit: ".cl" });
  return root.querySelectorAll(".file-uri-link").map((a) => a.dataset.path);
}

// ── a token with a run beside punctuation inside it is one word whole ────────────────────────────────────────────────

/** `text` the reply; `after` the chat's HTML; `keys` the kernel's keys over the raw markdown (a bare name in prose among
 *  them: protected, and still not linked, since the bare gate needs a code span); `links` what the walk links, in order. */
type Row = { text: string; after: string; keys: string[]; links: string[] };
const WHOLE: Row[] = [
  { text: "_see __init__.py now_", after: "<p><em>see __init__.py now</em></p>\n", keys: ["__init__.py"], links: [] },
  { text: "_the __init__.py file_", after: "<p><em>the __init__.py file</em></p>\n", keys: ["__init__.py"], links: [] },
  { text: "_see __init__.py and __main__.py now_", after: "<p><em>see __init__.py and __main__.py now</em></p>\n", keys: ["__init__.py", "__main__.py"], links: [] },
  { text: "__see __init__.py now__", after: "<p><strong>see __init__.py now</strong></p>\n", keys: ["__init__.py"], links: [] },
  { text: "_see __init__.py now_ and _more_", after: "<p><em>see __init__.py now</em> and <em>more</em></p>\n", keys: ["__init__.py"], links: [] },
  { text: "_see __pycache__/x.pyc now_", after: "<p><em>see __pycache__/x.pyc now</em></p>\n", keys: ["__pycache__/x.pyc"], links: ["__pycache__/x.pyc"] },
  { text: "see __init__.py and stop__", after: "<p>see __init__.py and stop__</p>\n", keys: ["__init__.py"], links: [] },
  { text: "edit __init__.py, then run it__", after: "<p>edit __init__.py, then run it__</p>\n", keys: ["__init__.py"], links: [] },
  { text: "__pycache__/x.pyc and stop__", after: "<p>__pycache__/x.pyc and stop__</p>\n", keys: ["__pycache__/x.pyc"], links: ["__pycache__/x.pyc"] },
  { text: "_see _drafts/a_.md now_", after: "<p><em>see _drafts/a_.md now</em></p>\n", keys: ["_drafts/a_.md"], links: ["_drafts/a_.md"] },
  { text: "_see _posts/x_/y.md now_", after: "<p><em>see _posts/x_/y.md now</em></p>\n", keys: ["_posts/x_/y.md"], links: ["_posts/x_/y.md"] },
  { text: "_see _drafts/a-_b/c.md now_", after: "<p><em>see _drafts/a-_b/c.md now</em></p>\n", keys: ["_drafts/a-_b/c.md"], links: ["_drafts/a-_b/c.md"] },
  { text: "_see _drafts/a_.md and _more_ now_", after: "<p><em>see _drafts/a_.md and <em>more</em> now</em></p>\n", keys: ["_drafts/a_.md"], links: ["_drafts/a_.md"] },
  { text: "_the _final_.pdf file_", after: "<p><em>the _final_.pdf file</em></p>\n", keys: ["_final_.pdf"], links: [] },
  { text: "_run _tmp_/a.md now_", after: "<p><em>run _tmp_/a.md now</em></p>\n", keys: ["_tmp_/a.md"], links: ["_tmp_/a.md"] },
  { text: "see _build/x.py and /out/_run_ now", after: "<p>see _build/x.py and /out/_run_ now</p>\n", keys: ["_build/x.py", "/out/_run_"], links: ["_build/x.py", "/out/_run_"] },
  { text: "see _drafts/a.md; the log is /tmp/_run_ (empty)", after: "<p>see _drafts/a.md; the log is /tmp/_run_ (empty)</p>\n", keys: ["_drafts/a.md", "/tmp/_run_"], links: ["_drafts/a.md", "/tmp/_run_"] },
  { text: "_see /a/_b_ now_", after: "<p><em>see /a/_b_ now</em></p>\n", keys: ["/a/_b_"], links: ["/a/_b_"] },
  { text: "_see /tmp/lab-_k7/preview-m3_ now_", after: "<p><em>see /tmp/lab-_k7/preview-m3_ now</em></p>\n", keys: ["/tmp/lab-_k7/preview-m3_"], links: ["/tmp/lab-_k7/preview-m3_"] },
  { text: "_the run dir is /tmp/lab-_k7/preview-m3_, check it_", after: "<p><em>the run dir is /tmp/lab-_k7/preview-m3_, check it</em></p>\n", keys: ["/tmp/lab-_k7/preview-m3_"], links: ["/tmp/lab-_k7/preview-m3_"] },
  { text: "_see /tmp/lab-_abc/preview-xyz_ and /tmp/lab-_abc/preview-xyz_/outside/notes.md now_", after: "<p><em>see /tmp/lab-_abc/preview-xyz_ and /tmp/lab-_abc/preview-xyz_/outside/notes.md now</em></p>\n", keys: ["/tmp/lab-_abc/preview-xyz_", "/tmp/lab-_abc/preview-xyz_/outside/notes.md"], links: ["/tmp/lab-_abc/preview-xyz_", "/tmp/lab-_abc/preview-xyz_/outside/notes.md"] },
  { text: "_see /tmp/x_/out.md_ now_", after: "<p><em>see /tmp/x_/out.md_ now</em></p>\n", keys: ["/tmp/x_/out.md_"], links: ["/tmp/x_/out.md_"] },
  { text: "_see __init__.py and /a-_b/c_/d.md now_", after: "<p><em>see __init__.py and /a-_b/c_/d.md now</em></p>\n", keys: ["__init__.py", "/a-_b/c_/d.md"], links: ["/a-_b/c_/d.md"] },
  { text: "_see __note/a.md__~~x.py~~ now_", after: "<p><em>see __note/a.md__<del>x.py</del> now</em></p>\n", keys: ["__note/a.md__~~x.py"], links: [] },
];
// The wholeness class by code point (the 2026-09-21 review, A; its class derivation's rows), inside the URI arm, the one arm
// that admits `*` and a non-ASCII character (the path and bare arms are ASCII by CLICKABLE_PATH_RE and isWordCh, so no row
// there can arm either hole: the controls at the end). A URI token begins with `file:` and so has no start-edge run; its end
// edge can be a `_` run (trailingPunct trims no `_`), so the shape is a URI ending in a `_` run, holding an interior run
// whose only neighbour is the character under test, with a prose `_` opener before it. Two faces. ASCII, by design: the
// 2026-09-20 head asked marked's punctuation rule, which excludes `*` on purpose, so a `*` beside the interior run left the
// token un-whole. Astral, by accident: that rule read one UTF-16 code unit, so an astral punctuation mark (U+10100, Po) or
// symbol (U+1F600, U+1F449, So) beside the run was a lone surrogate to it. On both faces the end-edge run stayed visible,
// the prose opener paired with it across the hidden middle, and the walk linked a piece that is not the token (`/x/a*_b/c`
// for `file:///x/a*_b/c_`). Positions: before the run, after it, between two runs, two symbols, at the paragraph's start
// and end, with a later closer, glued to the URI, as a strong, two URIs in one pair, and with two, three and five escaped
// astral symbols before the opener (each shortens marked's mask by one unit, so shiftedEscapes' correction accumulates).
// A URI is ungated to the walk (never in the kernel's map), so `keys` is empty and `links` is the URI's path, whole.
const URI = (tail: string): string => "file:///x/" + tail;
const CODE_POINT: Row[] = [
  // the `*` face (ASCII, by design)
  { text: "_see " + URI("a*_b/c_") + " now", after: "<p>_see " + URI("a*_b/c_") + " now</p>\n", keys: [], links: ["/x/a*_b/c_"] },
  { text: "_see " + URI("a_*b/c_") + " now", after: "<p>_see " + URI("a_*b/c_") + " now</p>\n", keys: [], links: ["/x/a_*b/c_"] },
  { text: "_see " + URI("a*_b/c_") + " now_", after: "<p><em>see " + URI("a*_b/c_") + " now</em></p>\n", keys: [], links: ["/x/a*_b/c_"] },
  { text: "__see " + URI("a*_b/c__") + " now", after: "<p>__see " + URI("a*_b/c__") + " now</p>\n", keys: [], links: ["/x/a*_b/c__"] },
  { text: "see _" + URI("a*_b/c_") + " now", after: "<p>see _" + URI("a*_b/c_") + " now</p>\n", keys: [], links: ["/x/a*_b/c_"] },
  { text: "_see \u{1F600}" + URI("a*_b/c_") + " now", after: "<p>_see \u{1F600}" + URI("a*_b/c_") + " now</p>\n", keys: [], links: ["/x/a*_b/c_"] },
  // the astral face (by accident): a symbol or a punctuation mark before the run, after it, between two runs, two of them
  { text: "_see " + URI("a\u{1F600}_b/c_") + " now", after: "<p>_see " + URI("a\u{1F600}_b/c_") + " now</p>\n", keys: [], links: ["/x/a\u{1F600}_b/c_"] },
  { text: "_see " + URI("a\u{10100}_b/c_") + " now", after: "<p>_see " + URI("a\u{10100}_b/c_") + " now</p>\n", keys: [], links: ["/x/a\u{10100}_b/c_"] },
  { text: "_see " + URI("a_\u{1F600}b/c_") + " now", after: "<p>_see " + URI("a_\u{1F600}b/c_") + " now</p>\n", keys: [], links: ["/x/a_\u{1F600}b/c_"] },
  { text: "_see " + URI("a_\u{10100}b/c_") + " now", after: "<p>_see " + URI("a_\u{10100}b/c_") + " now</p>\n", keys: [], links: ["/x/a_\u{10100}b/c_"] },
  { text: "_see " + URI("a_\u{1F600}_b/c_") + " now", after: "<p>_see " + URI("a_\u{1F600}_b/c_") + " now</p>\n", keys: [], links: ["/x/a_\u{1F600}_b/c_"] },
  { text: "_see " + URI("a\u{1F600}\u{1F449}_b/c_") + " now", after: "<p>_see " + URI("a\u{1F600}\u{1F449}_b/c_") + " now</p>\n", keys: [], links: ["/x/a\u{1F600}\u{1F449}_b/c_"] },
  // at the paragraph's start and end, with a later closer, two URIs in one pair
  { text: "\u{1F600} _see " + URI("a\u{1F600}_b/c_") + " now \u{1F600}", after: "<p>\u{1F600} _see " + URI("a\u{1F600}_b/c_") + " now \u{1F600}</p>\n", keys: [], links: ["/x/a\u{1F600}_b/c_"] },
  { text: "_see " + URI("a\u{1F600}_b/c_") + " now_", after: "<p><em>see " + URI("a\u{1F600}_b/c_") + " now</em></p>\n", keys: [], links: ["/x/a\u{1F600}_b/c_"] },
  { text: "_see " + URI("a*_b/c_") + " and file:///y/d\u{1F600}_e/f_ now_", after: "<p><em>see " + URI("a*_b/c_") + " and file:///y/d\u{1F600}_e/f_ now</em></p>\n", keys: [], links: ["/x/a*_b/c_", "/y/d\u{1F600}_e/f_"] },
  // two, three and five escaped astral symbols before the opener: the mask is that many units short, the correction accumulates
  { text: "\\\u{1F600} ".repeat(2) + "_see " + URI("a\u{1F600}_b/c_") + " now", after: "<p>" + "\\\u{1F600} ".repeat(2) + "_see " + URI("a\u{1F600}_b/c_") + " now</p>\n", keys: [], links: ["/x/a\u{1F600}_b/c_"] },
  { text: "\\\u{1F600} ".repeat(3) + "_see " + URI("a\u{1F600}_b/c_") + " now", after: "<p>" + "\\\u{1F600} ".repeat(3) + "_see " + URI("a\u{1F600}_b/c_") + " now</p>\n", keys: [], links: ["/x/a\u{1F600}_b/c_"] },
  { text: "\\\u{1F600} ".repeat(5) + "_see " + URI("a\u{1F600}_b/c_") + " now", after: "<p>" + "\\\u{1F600} ".repeat(5) + "_see " + URI("a\u{1F600}_b/c_") + " now</p>\n", keys: [], links: ["/x/a\u{1F600}_b/c_"] },
  // the controls that were whole at the 2026-09-20 head too, one BMP code unit each: `\u00bb` (Pf), `-`, `\u20ac` (Sc), `+` (Sm),
  // and two escaped astral symbols before a whole token
  { text: "_see " + URI("a\u00bb_b/c_") + " now", after: "<p>_see " + URI("a\u00bb_b/c_") + " now</p>\n", keys: [], links: ["/x/a\u00bb_b/c_"] },
  { text: "_see " + URI("a-_b/c_") + " now", after: "<p>_see " + URI("a-_b/c_") + " now</p>\n", keys: [], links: ["/x/a-_b/c_"] },
  { text: "_see " + URI("a\u20ac_b/c_") + " now", after: "<p>_see " + URI("a\u20ac_b/c_") + " now</p>\n", keys: [], links: ["/x/a\u20ac_b/c_"] },
  { text: "_see " + URI("a+_b/c_") + " now", after: "<p>_see " + URI("a+_b/c_") + " now</p>\n", keys: [], links: ["/x/a+_b/c_"] },
  { text: "\\\u{1F600} ".repeat(2) + "_see " + URI("a\u00bb_b/c_") + " now", after: "<p>" + "\\\u{1F600} ".repeat(2) + "_see " + URI("a\u00bb_b/c_") + " now</p>\n", keys: [], links: ["/x/a\u00bb_b/c_"] },
];
// The class's other edge, identical to the base grammar on both renderers and NOT whole: an astral LETTER (U+10400 Lu,
// U+1D400 Lu) is neither punctuation nor a symbol, so a rule keyed on "astral" rather than on the class would be wrong here;
// an unpaired surrogate is a character of no class, and the residual for the left-side read is a lone LOW surrogate with a
// `.` before it, which a read that stepped back one unit without checking for the high half would take for punctuation;
// the path arm splits its token at a `*` or a non-ASCII character, so those rows never reach the test; U+3000 is
// whitespace to the URI arm and ends the token before the run.
const NOT_WHOLE: string[] = [
  "_see " + URI("a\u{10400}_b/c_") + " now",
  "_see " + URI("a\u{1D400}_b/c_") + " now",
  "_see " + URI("a.\uDE00_b/c_") + " now",
  "_see " + URI("a_\uD83Db/c_") + " now",
  "_see " + URI("a\uD83D_b/c_") + " now",
  "_see /tmp/a*_b/c_ now",
  "_see /tmp/a\u{1F600}_b/c_ now",
  "_see " + URI("a\u3000_b/c_") + " now",
];

test("a linkable token with a `_` run beside punctuation inside it is one word whole, its edge runs too: a prose pair spanning it keeps its emphasis, a stray closer after it pairs with nothing, and the walk links the token whole under the kernel's key; the base grammar renders every row differently. The class is read by code point: a `*` (excluded by marked's rule on purpose) and an astral punctuation mark or symbol (a lone surrogate to a one-unit read) beside the interior run of a URI token make it whole too, where the 2026-09-20 head cut the token from its edge", () => {
  for (const r of [...WHOLE, ...CODE_POINT]) {
    for (const [who, render] of RENDERERS) {
      const html = render(r.text);
      assert.equal(html, r.after, who + ": " + JSON.stringify(r.text));
      assert.deepEqual(walkLinks(html, r.keys), r.links, who + ": the walk over " + html);
    }
    assert.notEqual(baseHtml(r.text), r.after, "the base grammar renders it differently: " + JSON.stringify(r.text));
  }
  for (const r of CODE_POINT) {
    const b = baseHtml(r.text);
    assert.match(b, /<em>/, "the base grammar pairs a run inside the URI: " + b);
    assert.ok(!walkLinks(b, r.keys).includes(r.links[0]), "and its walk never sees the token whole: " + JSON.stringify(walkLinks(b, r.keys)) + " over " + b);
  }
  for (const text of NOT_WHOLE) {
    const b = baseHtml(text);
    assert.match(b, /<em>/, "not whole: the run beside a letter, a lone surrogate or outside the token pairs as the spec says: " + b);
    for (const [who, render] of RENDERERS) assert.equal(render(text), b, who + ": identical to the base grammar: " + JSON.stringify(text));
  }
  assert.equal(WHOLE.length, 24); assert.equal(CODE_POINT.length, 23); assert.equal(NOT_WHOLE.length, 8);
  assert.ok(WHOLE.some((r) => r.after.includes("<em>")) && WHOLE.some((r) => r.after.includes("<strong>")) && WHOLE.some((r) => !/<(em|strong)>/.test(r.after)), "the rows hold an em, a strong and a literal outcome");
});

// ── the edge rule for a plain token, and its recorded faces ──────────────────────────────────────────────────────────

test("a plain token, one with no run beside punctuation inside it, keeps the edge rule as on the base grammar: its edge run opens or closes as the spec says; a bare name the scanner cuts before its trailing underscore keeps its wrapping emphasis (A02); an intraword run inside the token counts for nothing", () => {
  const EDGE: Array<[string, string]> = [
    ["_see _posts/x.md now_", "<p>_see <em>posts/x.md now</em></p>\n"],
    ["_see /tmp/x_", "<p><em>see /tmp/x</em></p>\n"],
    ["_x/y.md and more_", "<p><em>x/y.md and more</em></p>\n"],
    ["__x /a/b/c__ now", "<p><strong>x /a/b/c</strong> now</p>\n"],
    ["_see /tmp/my_proj/out_ now_", "<p><em>see /tmp/my_proj/out</em> now_</p>\n"],
    ["_see _posts/my_file.md now_", "<p>_see <em>posts/my_file.md now</em></p>\n"],
    ["see _posts/x.md now, done_", "<p>see <em>posts/x.md now, done</em></p>\n"],
    ["_notes.md_", "<p><em>notes.md</em></p>\n"],
    ["_docs/x_/notes.md_", "<p><em>docs/x</em>/notes.md_</p>\n"],
  ];
  for (const [text, want] of EDGE) {
    assert.equal(baseHtml(text), want, "the base grammar: " + JSON.stringify(text));
    for (const [who, render] of RENDERERS) assert.equal(render(text), want, who + ": as on the base: " + JSON.stringify(text));
  }
  // the rule's composed faces, recorded: a protected token in the same pair does not change how the plain token's edge
  // run pairs, at the end edge (the pair ends at the plain token) and at the start edge (the pair opens after the plain
  // token's `_`, so the walk under the kernel's keys links the protected token alone; main linked the plain one, and the
  // build's head, before interior runs were hidden, rendered the row literal and linked both), and the walk's ASCII word
  // class (path-links.ts isWordCh, the third parity follow-up) splits an accented path into two tokens whose second
  // begins with a run at its edge
  // and the WIDENING face of the whole-token rule's cost (md-config.ts states the class with both faces; the 2026-09-21
  // review, D): the run inside a whole token is hidden, so when another prose run stands past the token the surviving
  // prose run re-pairs across it and the chat emphasises a span the writer never marked, forward (the spec gave `<em>see
  // drafts/a</em>.md and old_ now`) and backward (the spec gave `_see x-<em>y.md now</em>`), and a widening can spend a
  // plain token's end-edge run (`/tmp/x_`, which main linked, is `/tmp/x` in the DOM, no longer the kernel's key). The
  // path arm buys the whole link in exchange; the bare-name arm in prose buys none
  const FACES: Array<[string, string, string[], string[]]> = [
    ["_see /tmp/_x/y.md and /tmp/z_ now_", "<p><em>see /tmp/_x/y.md and /tmp/z</em> now_</p>\n", ["/tmp/_x/y.md", "/tmp/z_"], ["/tmp/_x/y.md"]],
    ["_see _posts/x.md and /tmp/_y/z.md now_", "<p>_see <em>posts/x.md and /tmp/_y/z.md now</em></p>\n", ["_posts/x.md", "/tmp/_y/z.md"], ["/tmp/_y/z.md"]],
    ["_see /a-_b/cé_/d.md now_", "<p><em>see /a-_b/cé</em>/d.md now_</p>\n", ["/a-_b/cé_/d.md"], []],
    ["_see drafts/a_.md and old_ now", "<p><em>see drafts/a_.md and old</em> now</p>\n", ["drafts/a_.md"], ["drafts/a_.md"]],
    ["_see x-_y.md now_", "<p><em>see x-_y.md now</em></p>\n", ["x-_y.md"], []],
    ["_see final_.pdf and /tmp/x_ now", "<p><em>see final_.pdf and /tmp/x</em> now</p>\n", ["final_.pdf", "/tmp/x_"], []],
  ];
  for (const [text, want, keys, links] of FACES) for (const [who, render] of RENDERERS) {
    const html = render(text);
    assert.equal(html, want, who + ": recorded, not changed: " + JSON.stringify(text));
    assert.deepEqual(walkLinks(html, keys), links, who + ": the walk over " + html);
  }
  // the whole-token rule's face on a prose opener GLUED to the token (the closing pass): the opener is the token's own
  // start-edge run, hidden and refused with the rest, so the text is literal. For a path the token is linked whole under
  // the kernel's key, the rule's design; for a GFM www autolink whose path tail holds a run beside punctuation the walk
  // links nothing (text under an <a> is dead to it), so the rule costs the writer's emphasis there: recorded as it renders,
  // the base grammar cutting the URL or the path at its underscore instead
  const GLUED: Array<[string, string, string[], string[]]> = [
    ["_www.x.co/a_/b.md now_", "<p>_<a href=\"http://www.x.co/a_/b.md\">www.x.co/a_/b.md</a> now_</p>\n", ["_www.x.co/a_/b.md", "www.x.co/a_/b.md"], []],
    ["_drafts/a_.md is here_", "<p>_drafts/a_.md is here_</p>\n", ["_drafts/a_.md"], ["_drafts/a_.md"]],
  ];
  for (const [text, want, keys, links] of GLUED) {
    for (const [who, render] of RENDERERS) {
      const html = render(text);
      assert.equal(html, want, who + ": recorded as it renders: " + JSON.stringify(text));
      assert.deepEqual(walkLinks(html, keys), links, who + ": the walk over " + html);
    }
    assert.match(baseHtml(text), /<em>/, "the base grammar pairs the glued opener with the run inside the token: " + baseHtml(text));
  }
  assert.equal(baseHtml("_www.x.co/a/b.md now_"), chatMd.chatMdHtml("_www.x.co/a/b.md now_"), "a plain www token with a glued opener keeps its emphasis as on the base");
});

// ── an escaped astral symbol ─────────────────────────────────────────────────────────────────────────────────────────

test("a backslash before an astral symbol masks three UTF-16 units as two, and a run inside a token is refused whatever follows it: the override measures the run's position on the unmasked tail with those escapes counted", () => {
  const ROWS: Array<[string, string]> = [
    ["see /_build/out_ \\\u{1F600}", "<p>see /_build/out_ \\\u{1F600}</p>\n"],
    ["see /_build/out_ \\\u{1F600} \\\u{1F449}", "<p>see /_build/out_ \\\u{1F600} \\\u{1F449}</p>\n"],
    ["see /_build/out.md now_ \\\u{1F600} \\\u{1F449}", "<p>see /_build/out.md now_ \\\u{1F600} \\\u{1F449}</p>\n"],
    ["see /_build/out_ \\\u{10100} \\\u{10100}", "<p>see /_build/out_ \\\u{10100} \\\u{10100}</p>\n"],
  ];
  for (const [text, want] of ROWS) {
    for (const [who, render] of RENDERERS) {
      const html = render(text);
      assert.equal(html, want, who + ": " + JSON.stringify(text));
      assert.deepEqual(walkLinks(html, ["/_build/out_", "/_build/out.md"]), [/\/out_/.test(text) ? "/_build/out_" : "/_build/out.md"], who + ": the path links whole");
    }
  }
  assert.match(baseHtml(ROWS[0][0]), /<em>/, "the base grammar cuts the path after one escape (marked's own arithmetic)");
  assert.equal(baseHtml(ROWS[1][0]), ROWS[1][1], "and left it literal after two, by accident of its shifted count");
  assert.equal(baseHtml("see /_build/out.md now_ x y"), "<p>see /<em>build/out.md now</em> x y</p>\n", "the control: no escape, the base grammar cuts");
  for (const [, render] of RENDERERS) assert.equal(render("see /_build/out.md now_ x y"), "<p>see /_build/out.md now_ x y</p>\n");
});

/** The passes marked's escape rule (rules.inline.anyPunctuation, one RegExp shared by every grammar in the process) made over
 *  a string starting at a `_` run while `fn` ran: the override's own, since marked's mask runs it over the paragraph, which
 *  starts elsewhere here. A pass begins with lastIndex at zero; the count of exec calls is reported beside it. */
function escapePasses(fn: () => void): { passes: number; execs: number } {
  const re: RegExp = (Lexer as unknown as { rules: { inline: { gfm: { anyPunctuation: RegExp } } } }).rules.inline.gfm.anyPunctuation;
  const orig = RegExp.prototype.exec;
  let passes = 0, execs = 0;
  (re as unknown as { exec: (s: string) => RegExpExecArray | null }).exec = function (this: RegExp, s: string) {
    if (s.charCodeAt(0) === 95) { execs++; if (this.lastIndex === 0) passes++; }
    return orig.call(this, s);
  };
  try { fn(); } finally { delete (re as unknown as { exec?: unknown }).exec; }
  return { passes, execs };
}

test("an escaped astral symbol inside a link, a reflink, a code span or a tag is letters in the mask and counts for nothing: a plain token's start-edge opener before it keeps its emphasis as on the base grammar, a whole token's end-edge run after it stays refused, and the override runs marked's escape rule over no tail at all", () => {
  // face (1): the emphasis around or after a plain token, an escaped BMP character in prose (the `++` in the mask) and
  // then a construct holding an escaped emoji; round 2 counted the construct's escape, read the token's start-edge run one
  // position in, and refused it, so both underscores showed literal where main showed the emphasis
  const IN_CONSTRUCT: string[] = [
    "_see _posts/x.md now_ \\. [\\\u{1F600}](u)",
    "see _posts/x.md now_ \\! [\\\u{1F600}](u)",
    "see _posts/x.md now_ \\! [\\\u{1F600}][r]\n\n[r]: u",
    "see _posts/x.md now_ \\! `\\\u{1F600}`",
    "see _posts/x.md now_ \\! <b title=\"\\\u{1F600}\">t</b>",
    "see _posts/x.md now_ \\! [\\\u{1F600}\\\u{1F449}](u)",
    "_posts/x.md is [\\\u{1F600}](u) here_ \\.",
  ];
  for (const text of IN_CONSTRUCT) {
    const want = baseHtml(text);
    assert.match(want, /<em>/, "the base grammar keeps the emphasis: " + want);
    for (const [who, render] of RENDERERS) {
      const html = render(text);
      assert.equal(html, want, who + ": as on the base: " + JSON.stringify(text));
      assert.deepEqual(walkLinks(html, ["_posts/x.md"]), [], who + ": nothing to link, the token's `_` spent on the emphasis, as on the base");
    }
  }
  // face (2): a whole token's end-edge run, or a closer spent inside a plain token, with the same construct after it; round
  // 2 read the run one position past the token and let the built-in pair it, cutting the token the walk links whole
  const WHOLE_EDGE: Array<[string, string, string]> = [
    ["see /a/_b/c-_(and stop_) \\! [\\\u{1F600}](u)", "<p>see /a/_b/c-_(and stop_) ! <a href=\"u\">\\\u{1F600}</a></p>\n", "/a/_b/c-_"],
    ["see /a/_b/c-_(and stop_) \\! [x](u)", "<p>see /a/_b/c-_(and stop_) ! <a href=\"u\">x</a></p>\n", "/a/_b/c-_"],
    ["see /a/_b/c-_(and stop_) . [\\\u{1F600}](u)", "<p>see /a/_b/c-_(and stop_) . <a href=\"u\">\\\u{1F600}</a></p>\n", "/a/_b/c-_"],
    ["_see /tmp/x__ [\\\u{1F600}](u) \\.", "<p>_see /tmp/x__ <a href=\"u\">\\\u{1F600}</a> .</p>\n", "/tmp/x__"],
    ["_see /tmp/x__ [x](u) \\.", "<p>_see /tmp/x__ <a href=\"u\">x</a> .</p>\n", "/tmp/x__"],
  ];
  for (const [text, want, key] of WHOLE_EDGE) {
    for (const [who, render] of RENDERERS) {
      const html = render(text);
      assert.equal(html, want, who + ": " + JSON.stringify(text));
      assert.deepEqual(walkLinks(html, [key]), [key], who + ": the token links whole: " + html);
    }
    assert.match(baseHtml(text), /<em>/, "the base grammar cuts the token: " + baseHtml(text));
  }
  // the controls render as the base: no BMP escape in the paragraph (nothing masked to `++`), the astral escape in prose
  // (masked, counted), the escapes before the delimiter, an escaped astral LETTER (no escape to marked's rule)
  for (const text of ["_see _posts/x.md now_ . [\\\u{1F600}](u)", "_see _posts/x.md now_ \\. \\\u{1F600}", "\\\u{1F600} \\. _see _posts/x.md now_", "_see _posts/x.md now_ \\. [\\\u{10400}](u)"]) {
    for (const [who, render] of RENDERERS) assert.equal(render(text), baseHtml(text), who + ": the control renders as the base: " + JSON.stringify(text));
  }
  // the rule is run over no tail: round 2 ran it over the whole tail once per `_` delimiter while the tail held a backslash
  // (2859 passes on this paragraph), a quadratic term the shape below measures as a ratio
  const shape = "E0 " + "\\! _a_ ".repeat(2860);
  const first = escapePasses(() => { chatMd.chatMdHtml(shape); });
  assert.equal(first.passes, 0, "the override ran marked's escape rule over a tail " + first.passes + " times (" + first.execs + " exec calls) on a 20 KB paragraph of escaped bangs and pairs");
  const again = escapePasses(() => { chatMd.userMdHtml(shape); });
  assert.equal(again.passes, 0, "and " + again.passes + " times on the other renderer");
  assert.equal(chatMd.chatMdHtml(shape), baseHtml(shape), "no path: the rendering is the base's");
});

// ── cost ─────────────────────────────────────────────────────────────────────────────────────────────────────────────

/** The scans the override started over strings of the paragraph's own length while `fn` ran: one, when the memo held. */
function paragraphScans(paragraph: string, fn: () => void): { paragraph: number; all: number } {
  const orig = PathTokenScanner.prototype.next;
  const lengths: number[] = [];
  PathTokenScanner.prototype.next = function (this: PathTokenScanner, from: number) {
    if (from === 0) lengths.push((this as unknown as { text: string }).text.length);
    return orig.call(this, from);
  };
  try { fn(); } finally { PathTokenScanner.prototype.next = orig; }
  return { paragraph: lengths.filter((n) => n === paragraph.length).length, all: lengths.length };
}
const SHAPES: Array<[string, string]> = [
  ["a link whose label holds a pair, then a prose pair", "[_a_](u) _b_ ".repeat(400)],
  ["a link whose label holds an intraword run, then one in prose", "[a_b](u) c_d ".repeat(400)],
  ["a `*` pair whose body holds a `_` pair, then a prose pair", "**_a_** _b_ ".repeat(400)],
  ["a `~~` pair whose body holds a `_` pair, then a prose pair", "~~_a_~~ _b_ ".repeat(400)],
  ["pairs whose bodies hold pairs, no whitespace", "_(_a_)_.".repeat(400)],
  ["a realistic paragraph of links to test files", "[test_foo_bar](tests/test_foo_bar.py) calls helper_one and helper_two; ".repeat(25)],
  ["one whitespace-free path run with a pair every eleven characters", "/abcdefgh-_".repeat(400)],
  ["prose naming a member path per sentence", "The build wrote /a-_b/c_/d.md and then ~/code/my_proj/_drafts/a.md, then foo/__pycache__/bar.pyc. ".repeat(40)],
];

test("one scan of the paragraph per masked string per parse, whatever the nested lexes between two of its delimiters bring: a link's label, a `*` pair's or a `~~` pair's body takes an entry beside the paragraph's and evicts nothing, any number of distinct such strings included (the eight-slot list the 2026-09-20 review shipped evicted the paragraph's entry at eight and rescanned it once per gap); the same paragraph parsed three times is scanned three times, once per parse", () => {
  // the memo lives with the parse's lexer and is keyed by the masked string's text, so a paragraph is scanned once per
  // parse; each render below still gets a paragraph no earlier render has seen (a distinct first word), so the count it
  // pins is one parse's and never a hit from an earlier test
  let seq = 0;
  for (const [what, src] of SHAPES) {
    for (const [who, render] of RENDERERS) {
      const fresh = "P" + (seq++) + " " + src;
      const n = paragraphScans(fresh, () => { render(fresh); });
      assert.equal(n.paragraph, 1, who + ", " + what + ": the paragraph (" + fresh.length + " characters) was scanned " + n.paragraph + " times");
      assert.ok(n.all <= 1 + fresh.length, who + ", " + what + ": scans in all " + n.all);
    }
  }
  // the memo holds the paragraph's entry across the standing pair's body lex too; the same paragraph parsed again (the
  // other instance, or a repaint) is a new parse with a memo of its own, so it scans once more, beside marked's whole parse
  const again = "P" + (seq++) + " " + SHAPES[4][1];
  const twice = paragraphScans(again, () => { chatMd.chatMdHtml(again); chatMd.userMdHtml(again); chatMd.chatMdHtml(again); });
  assert.equal(twice.paragraph, 3, "the same paragraph parsed three times is scanned three times, once per parse (the module-global list scanned it once and held it across parses)");
  // no bound: k distinct nested strings holding a `_` run between two prose pairs leave the paragraph's entry in place for
  // every k (the eight-slot list evicted it at eight and the second prose pair rescanned the paragraph), each distinct
  // string scanned once itself; twelve IDENTICAL labels are one entry, a hit
  const distinct = (k: number, shape: (i: number) => string): string => Array.from({ length: k }, (_, i) => shape(i)).join("");
  for (const [what, k] of [["seven distinct link labels", 7], ["eight distinct link labels", 8], ["nine distinct link labels", 9], ["forty distinct link labels", 40]] as Array<[string, number]>) {
    const p = "P" + (seq++) + " _x_ " + distinct(k, (i) => "[_a" + i + "_](u) ") + "_y_";
    const n = paragraphScans(p, () => { chatMd.chatMdHtml(p); });
    assert.equal(n.paragraph, 1, what + " between two prose pairs: the paragraph was scanned " + n.paragraph + " time(s)");
    assert.equal(n.all, 1 + k, what + ": one scan per distinct masked string, the paragraph and each label: " + n.all);
  }
  for (const [what, k] of [["seven distinct `*` bodies", 7], ["nine distinct `*` bodies", 9]] as Array<[string, number]>) {
    const p = "P" + (seq++) + " _x_ " + distinct(k, (i) => "*_a" + i + "_* ") + "_y_";
    assert.equal(paragraphScans(p, () => { chatMd.chatMdHtml(p); }).paragraph, 1, what + " between two prose pairs: the paragraph was scanned once");
  }
  const same = "P" + (seq++) + " _x_ " + "[_a_](u) ".repeat(12) + "_y_";
  assert.equal(paragraphScans(same, () => { chatMd.chatMdHtml(same); }).paragraph, 1, "twelve identical labels are one entry: one scan");
  // the shape that evicted the eight-slot list at EVERY prose pair (eight distinct `*` bodies between every two of them),
  // 571 times over, 20 KB: one scan of the paragraph and one of each of the eight distinct bodies, 4,568 body lexes in
  // all (the list scanned the paragraph 571 times here, once per gap)
  const thrash = "P" + (seq++) + " " + ("_x_" + "*_0**_1**_2**_3**_4**_5**_6**_7*").repeat(571);
  const t = paragraphScans(thrash, () => { chatMd.chatMdHtml(thrash); });
  assert.equal(t.paragraph, 1, "the thrashing paragraph (" + thrash.length + " characters) was scanned " + t.paragraph + " times");
  assert.equal(t.all, 9, "scans in all, the paragraph and eight distinct bodies: " + t.all);
});

/** The chat grammar's time over the base grammar's on the same string, the best of `passes` interleaved passes: the
 *  structural ratio, a pass the scheduler interrupted ignored. */
function ratio(src: string, passes = 4): number {
  let best = Infinity;
  for (let p = 0; p < passes; p++) {
    const t0 = performance.now(); baseHtml(src); const t1 = performance.now(); chatMd.chatMdHtml(src); const t2 = performance.now();
    best = Math.min(best, (t2 - t1) / Math.max(t1 - t0, 0.05));
  }
  return best;
}

test("the override costs at most a few times the base grammar on a 20 KB paragraph of each shape: links, `*` pairs or `~~` pairs with a `_` pair inside beside prose pairs (eight to twelve times before the memo survived them), a whitespace-free path run, prose naming a path per sentence, escaped bangs beside pairs (2.3 times when the escape rule ran once per delimiter), and eight distinct nested bodies between EVERY two prose pairs, the shape that evicted the eight-slot memo at every gap (13.8 to 16.9 times before the per-parse memo)", () => {
  // The bound is a round number, CHOSEN with headroom for a loaded box, not derived: the measured worst shape across the
  // rows is the whitespace-free path run at 1.4 to 1.7 (the 2026-09-21 review's runs at loads 6 to 33 on a 60-core box;
  // marked lexes twice the text tokens there), every other row near one. It is honest because the cost is linear: the
  // one superlinear term, the rescan after an eviction, is gone with the per-parse memo, and its shape is the last row
  // (red at 13.8 to 31.8 with the eight-slot list across those runs, 571 rescans of the paragraph, doubling per doubling
  // of length: no constant could bound it). The ratio is the best of interleaved passes in one process (ratio), so the box's load is a
  // noise term the headroom absorbs; a red here at about one on a loaded box is the noise, at four and more the term.
  const BOUND = 4;
  const LONG: Array<[string, string]> = [
    ["links with a pair in the label", "[_a_](u) _b_ ".repeat(1600)],
    ["`*` pairs with a pair in the body", "**_a_** _b_ ".repeat(1800)],
    ["`~~` pairs with a pair in the body", "~~_a_~~ _b_ ".repeat(1800)],
    ["a whitespace-free path run", "/abcdefgh-_".repeat(1819)],
    ["prose with a member path per sentence", "The build wrote /a-_b/c_/d.md and then ~/code/my_proj/_drafts/a.md, then foo/__pycache__/bar.pyc. ".repeat(200)],
    ["pairs whose bodies hold pairs, no whitespace", "_(_a_)_.".repeat(3125)],
    ["an escaped bang before every pair", "\\! _a_ ".repeat(2860)],
    ["pairs, then as many escaped bangs", "_a_ ".repeat(2500) + "\\! ".repeat(2500)],
    ["eight distinct nested `_` bodies between every two prose pairs", ("_x_" + "*_0**_1**_2**_3**_4**_5**_6**_7*").repeat(571)],
  ];
  for (const [what, src] of LONG) {
    const r = ratio(src);
    assert.ok(r <= BOUND, what + ": the chat grammar took " + r.toFixed(1) + "x the base grammar on " + src.length + " characters");
  }
  for (const [, src] of [...LONG.slice(0, 3), ...LONG.slice(6)]) assert.equal(chatMd.chatMdHtml(src), baseHtml(src), "no path: the rendering is the base's");
});
