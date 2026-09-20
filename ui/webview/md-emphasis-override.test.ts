// The chat's path-aware emphasis (md-config.ts pathAwareEmphasis), its mechanism's edges, executed over the REAL marked
// on the chat's two instances (chat-md.ts). md-emphasis-paths.test.ts runs the population note's two tables; this file
// pins what the 2026-09-20 review found beside them:
//   - a `_` pair whose body holds a path with an UNBALANCED interior underscore run (`_see /tmp/_build/out.md now_`, a
//     closer-shaped `x_/` or an opener-shaped `/_build`) keeps its emphasis around the literal, linked path. Before, the
//     override let the built-in choose the pair first and refused the pair it chose (the path's `x_/` as the closer, or
//     no pair at all because `/_b` counted as a nested opener), and marked reads a refused opener as text and never
//     retries it, so the person's emphasis vanished and both underscores showed. Now a run strictly inside a linkable
//     token is hidden from the closer scan, so the opener pairs with the next closer outside the token;
//   - the built-in decides the pair on a stand-in `this` of `{ rules, lexer }` and nothing else. That is a contract with
//     the installed marked, pinned here by a recording proxy: an upgrade whose emStrong reads more from `this` goes red
//     here by name, where it would otherwise throw inside the override and land in render.ts md()'s catch, which shows
//     the whole reply as escaped text;
//   - the override reaches the built-in through Tokenizer.prototype (marked's use() gives an override no handle to the
//     tokenizer it replaced), so an emStrong override registered EARLIER on the same instance would never see a `_` run.
//     Right while no extension in mdExtensions overrides emStrong, pinned by reading the list and by execution;
//   - cost: one linear scan per masked paragraph string, remembered across a standing pair's body lex, and a binary
//     search per delimiter. Before, the whitespace bounds were walked on every call ahead of the memo (a 20 KB run with
//     no whitespace and a pair every eleven characters cost sixteen times the base grammar, a run of `(_a_)` thirty),
//     and a standing pair's body lex evicted the one-slot memo (`_(_a_)_.` repeated, fifty times the base). Measured
//     here as a ratio to the base grammar on the same string in the same process, the best of interleaved passes, as
//     anchor-map-raw-offset-to-line.test.ts measures its search.
// The walk runs over a small DOM stand-in fed marked's HTML (no jsdom), the chat's own options minus the fenced gate,
// with a map holding the wanted token, as the kernel's verdict would. Synthetic fixtures only: invented paths, a
// placeholder session id.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { Marked, Tokenizer, type MarkedExtension } from "marked";
import { hideEdges } from "../test-dom-shim";
import * as chatMd from "./chat-md";
import { mdExtensions, pathAwareEmphasis } from "./md-config";
import { linkifyPathTokens } from "./path-links";

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

// ── a pair around a path with an unbalanced interior run ─────────────────────────────────────────────────────────────

type Row = { text: string; after: string; link: string };
/** A prose `_` (or `__`) pair whose body holds a linkable path with a closer-shaped run (`x_/`), an opener-shaped run
 *  (`/_build`), or one of each, and a closer in prose after the path. `after` is the chat's HTML; `link` the path the
 *  walk must link whole inside the emphasis. */
const SPANNING: Row[] = [
  { text: "_see /tmp/_build/out.md now_", after: "<p><em>see /tmp/_build/out.md now</em></p>\n", link: "/tmp/_build/out.md" },
  { text: "_see notes_/todo.md for details_", after: "<p><em>see notes_/todo.md for details</em></p>\n", link: "notes_/todo.md" },
  { text: "_x c_/d.md y_", after: "<p><em>x c_/d.md y</em></p>\n", link: "c_/d.md" },
  { text: "_read docs/x_/y.md first_", after: "<p><em>read docs/x_/y.md first</em></p>\n", link: "docs/x_/y.md" },
  { text: "_Note: the file is at /tmp/x_/y.md, check it_", after: "<p><em>Note: the file is at /tmp/x_/y.md, check it</em></p>\n", link: "/tmp/x_/y.md" },
  { text: "_private /a-b/c_/d.md is here_", after: "<p><em>private /a-b/c_/d.md is here</em></p>\n", link: "/a-b/c_/d.md" },
  { text: "_the run wrote /out/run_1_/log.txt today_", after: "<p><em>the run wrote /out/run_1_/log.txt today</em></p>\n", link: "/out/run_1_/log.txt" },
  { text: "_see a_/b-_c/d.md now_", after: "<p><em>see a_/b-_c/d.md now</em></p>\n", link: "a_/b-_c/d.md" },
  { text: "_see ~/code/my_proj/_drafts/a.md now_", after: "<p><em>see ~/code/my_proj/_drafts/a.md now</em></p>\n", link: "~/code/my_proj/_drafts/a.md" },
  { text: "_see /tmp/x_/notes.md now_ and _more_", after: "<p><em>see /tmp/x_/notes.md now</em> and <em>more</em></p>\n", link: "/tmp/x_/notes.md" },
  { text: "__Note: see /tmp/x__/y.md, done__", after: "<p><strong>Note: see /tmp/x__/y.md, done</strong></p>\n", link: "/tmp/x__/y.md" },
  { text: "__see /tmp/_build/out.md now__", after: "<p><strong>see /tmp/_build/out.md now</strong></p>\n", link: "/tmp/_build/out.md" },
];

test("a `_` pair whose body holds a path with an unbalanced interior underscore run keeps its emphasis on both chat renderers, the path literal inside it and linked whole; the base grammar cuts the path or misplaces the emphasis on every row", () => {
  for (const r of SPANNING) {
    for (const [who, render] of RENDERERS) {
      const html = render(r.text);
      assert.equal(html, r.after, who + ": " + JSON.stringify(r.text));
      assert.deepEqual(walkLinks(html, [r.link]), [r.link], who + ": the walk links the path whole inside the emphasis: " + html);
    }
    const b = baseHtml(r.text);
    assert.notEqual(b, r.after, "the base grammar renders it differently: " + JSON.stringify(r.text));
    assert.match(b, /<(em|strong)>/, "the base grammar paired the opener with a run inside the path, or a run inside it with the closer: " + b);
    assert.deepEqual(walkLinks(b, [r.link]), [], "and its walk never sees the token whole: " + b);
  }
  assert.equal(SPANNING.length, 12);
});

test("the shapes around it stand: a balanced interior pair, a pair with no closer in prose, the accepted loss, a `*` twin, a strong closing at a token's edge, and a run at a token's edge longer than the pair spends", () => {
  const KEPT: Array<[string, string, string]> = [
    ["_em /a-_b/c_/d.md here_", "<p><em>em /a-_b/c_/d.md here</em></p>\n", "a balanced pair inside the path: the outer emphasis stands, the inner is refused"],
    ["_the foo/__pycache__/bar.pyc file is stale_", "<p><em>the foo/__pycache__/bar.pyc file is stale</em></p>\n", "a balanced strong inside the path"],
    ["_private /a-b/c_/d.md", "<p>_private /a-b/c_/d.md</p>\n", "C38: no closer outside the path, so the opener is text"],
    ["_foo_-bar/baz.md", "<p>_foo_-bar/baz.md</p>\n", "A08, the accepted loss: emphasis glued to a path"],
    ["see -_b/c_/d.md", "<p>see -_b/c_/d.md</p>\n", "both runs inside the path"],
    ["*see /tmp/x_/notes.md now*", "<p><em>see /tmp/x_/notes.md now</em></p>\n", "a `*` pair is the built-in's as it stands"],
    ["_see /tmp/x/notes.md now_", "<p><em>see /tmp/x/notes.md now</em></p>\n", "no run inside the path: as before"],
    ["__x /a/b/c__ now", "<p><strong>x /a/b/c</strong> now</p>\n", "a strong closing at a token's end edge: the edge rule"],
    ["see _x /a/b/c__ now", "<p>see _x /a/b/c__ now</p>\n", "an em closer that spends one of the two at the edge: the spent run is inside, refused"],
    ["_x_ /a-_b/c_/d.md _y_", "<p><em>x</em> /a-_b/c_/d.md <em>y</em></p>\n", "emphasis on either side of a path"],
    ["_see _posts/x.md now_", "<p>_see <em>posts/x.md now</em></p>\n", "a run at a token's start edge opens (the edge rule, as on the base): recorded, not changed"],
    ["_see /tmp/x_", "<p><em>see /tmp/x</em></p>\n", "a run at a token's end edge closes (the edge rule, as on the base): recorded, not changed"],
  ];
  for (const [text, want, why] of KEPT) for (const [who, render] of RENDERERS) assert.equal(render(text), want, who + ": " + why + ": " + JSON.stringify(text));
  for (const [who, render] of RENDERERS) {
    const out = render("_private [^1] /a-b/c_/d.md\n\n[^1]: the note");
    assert.match(out, /^<p>_private <sup class="md-fnref"><a href="#fn-1" id="fnref-1">1<\/a><\/sup> \/a-b\/c_\/d\.md<\/p>\n/, who + ": a footnote inside a pair with no closer outside the path is numbered once: " + out);
  }
});

// ── the stand-in's contract ──────────────────────────────────────────────────────────────────────────────────────────

test("the dry-run stand-in is `{ rules, lexer }` and the installed marked's emStrong reads nothing else from `this`: measured by a recording proxy over every dry call a reply makes", () => {
  const orig = Tokenizer.prototype.emStrong;
  const dryCalls: string[][] = [];
  const read = new Set<string>();
  Tokenizer.prototype.emStrong = function (this: Tokenizer, ...args: [string, string, string?]) {
    if (this instanceof Tokenizer) return orig.apply(this, args);       // a real tokenizer (a `*` run falling through, the singleton): untouched
    dryCalls.push(Object.keys(this));
    const seen = new Proxy(this as object, { get(t, k, r) { read.add(String(k)); return Reflect.get(t, k, r); } });
    return orig.apply(seen as Tokenizer, args);
  };
  try {
    const reply = "## Plan\n\nRename `helper` in src/_private/util_.py and keep __init__.py; see /a-_b/c_/d.md and _the docs/notes.md_ file.\n\n- a snake_case_name and _em_\n- __strong__ and _see /tmp/_build/out.md now_\n";
    let threw: unknown = null;
    try { for (const [, render] of RENDERERS) render(reply); } catch (e) { threw = e; }   // a read the stand-in lacks throws inside the override: named below, before the throw is
    const outside = [...read].filter((k) => k !== "rules" && k !== "lexer");
    assert.deepEqual(outside, [], "the built-in read " + JSON.stringify(outside) + " from the stand-in: marked's emStrong reads more from `this` than the stand-in provides (the DRY_LEXER comment in md-config.ts)");
    assert.equal(threw, null, "the dry call threw: " + String(threw));
    assert.ok(dryCalls.length >= 8, "the reply reached the built-in on the stand-in " + dryCalls.length + " times");
    for (const keys of dryCalls) assert.deepEqual(keys.sort(), ["lexer", "rules"], "the stand-in carries rules and lexer, nothing else");
    assert.deepEqual([...read].sort(), ["lexer", "rules"], "and it read both");
  } finally {
    Tokenizer.prototype.emStrong = orig;
  }
  assert.equal(chatMd.chatMdHtml("see /a-_b/c_/d.md"), "<p>see /a-_b/c_/d.md</p>\n", "the prototype is restored");
});

// ── the chain ────────────────────────────────────────────────────────────────────────────────────────────────────────

test("no extension the chat's instances take overrides emStrong besides pathAwareEmphasis: the override reaches the built-in through Tokenizer.prototype, so an override registered earlier would never see a `_` run", () => {
  for (const ext of mdExtensions) {
    const t = (ext as { tokenizer?: Record<string, unknown> }).tokenizer;
    assert.equal(t?.emStrong, undefined, "an extension in mdExtensions overrides emStrong: register it AFTER pathAwareEmphasis on the chat's instances, or fold it in");
  }
  assert.equal(typeof (pathAwareEmphasis as { tokenizer?: Record<string, unknown> }).tokenizer?.emStrong, "function");
  // the reason, by execution: a pass-through spy before the override sees every `*` run and no `_` run; after it, both
  const seen = (order: "before" | "after"): string[] => {
    const log: string[] = [];
    const spy = { tokenizer: { emStrong(src: string) { if (src[0] === "_" || src[0] === "*") log.push(src[0]); return false as const; } } } as MarkedExtension;
    const m = order === "before" ? new Marked({ gfm: true, breaks: false }, ...mdExtensions, spy, pathAwareEmphasis) : new Marked({ gfm: true, breaks: false }, ...mdExtensions, pathAwareEmphasis, spy);
    m.parse("_x_ and *y* and /a-_b/c_/d.md");
    return [...new Set(log)].sort();
  };
  assert.deepEqual(seen("before"), ["*"], "registered before the override: `_` runs never reach it");
  assert.deepEqual(seen("after"), ["*", "_"], "registered after it: every run");
});

// ── cost ─────────────────────────────────────────────────────────────────────────────────────────────────────────────

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

test("the override costs at most a few times the base grammar whatever the paragraph's shape: a 20 KB run with no whitespace and a pair every eleven characters, a 20 KB run of nested pairs with no path, and a 25 KB run of pairs whose bodies hold pairs", () => {
  const BOUND = 4;   // the memo held: about one to two; the bounds walk before it: sixteen and more; loose for a loaded box
  const paths = "/abcdefgh-_".repeat(1819);         // one linkable token; every pair inside it is refused, so marked lexes twice the text tokens
  const nested = "(_a_)".repeat(4000);              // no path; every pair stands; two lookups per pair
  const bodies = "_(_a_)_.".repeat(3125);           // every outer pair's body holds a pair: the body lex takes its own masked string
  for (const [what, src] of [["paths", paths], ["nested", nested], ["bodies", bodies]] as Array<[string, string]>) {
    const r = ratio(src);
    assert.ok(r <= BOUND, what + ": the chat grammar took " + r.toFixed(1) + "x the base grammar on " + src.length + " characters (the bounds walk before the memo took sixteen times and more; the memo evicted by a body lex, fifty)");
  }
  assert.equal(chatMd.chatMdHtml(nested), baseHtml(nested), "no path: the rendering is the base's");
  assert.equal(chatMd.chatMdHtml(bodies), baseHtml(bodies), "no path: the rendering is the base's");
  assert.doesNotMatch(chatMd.chatMdHtml(paths), /<em>|<strong>/, "one token: every pair inside it is refused");
  assert.match(baseHtml(paths), /<em>/, "which the base grammar emphasised");
});
