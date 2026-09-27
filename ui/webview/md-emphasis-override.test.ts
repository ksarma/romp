// The chat's path-aware emphasis (md-config.ts pathAwareEmphasis), its mechanism's edges, executed over the REAL marked
// on the chat's two instances (chat-md.ts). md-emphasis-paths.test.ts runs the population note's two tables; this file
// pins what the 2026-09-20 review found beside them:
//   - a `_` pair whose body holds a path with an UNBALANCED interior underscore run (`_see /tmp/_build/out.md now_`, a
//     closer-shaped `x_/` or an opener-shaped `/_build`) keeps its emphasis around the literal, linked path. Before, the
//     override let the built-in choose the pair first and refused the pair it chose (the path's `x_/` as the closer, or
//     no pair at all because `/_b` counted as a nested opener), and marked reads a refused opener as text and never
//     retries it, so the person's emphasis vanished and both underscores showed. Now a run strictly inside a linkable
//     token is hidden from the closer scan, so the opener pairs with the next closer outside the token;
//   - the built-in decides the pair on a stand-in `this` of `{ rules, lexer }` and nothing else, and the lexer half is a
//     fake with one member, inlineTokens. That is a contract with the installed marked, pinned here by a recording proxy
//     at BOTH levels, the reads of `this` and the reads of `this.lexer`: an upgrade whose emStrong reads more from
//     either goes red here by name, where a read the real half lacks would throw inside the override and land in
//     render.ts md()'s catch, which shows the whole reply as escaped text, and a read the faked half lacks would return
//     undefined without a throw and the override would return different pairs with nothing saying so. The pin promises
//     exactly that much: it records what the INSTALLED marked reads, it cannot know what a later version would read,
//     and it reds only once that version is installed and this file runs (the version is held by the lockfile, not
//     enforced by a build check: md-config.ts's DRY_LEXER comment has the fact);
//   - the override reads no punctuation class from marked: the wholeness test's class is its own, read by code point
//     (md-config.ts flankedInside), so a memo entry depends on the masked string alone and the string is the whole key.
//     At the 2026-09-20 head the override read marked's `punctuation` through the memo, so a second instance whose lexer
//     carried a different class could take, or leave behind, an entry computed under the other's class, and the render
//     order decided the output (the 2026-09-21 review, B); nothing reachable arms it on marked 12.0.2, whose inline
//     grammars share one punctuation RegExp, and a throwaway instance whose lexer carries a class of its own does;
//   - the override reaches the built-in through Tokenizer.prototype (marked's use() gives an override no handle to the
//     tokenizer it replaced), so an emStrong override registered EARLIER on the same instance would never see a `_` run.
//     Right while no extension in mdExtensions overrides emStrong, pinned by reading the list and by execution;
//   - cost: one linear scan per masked paragraph string per parse, remembered in a memo that lives with the parse's lexer
//     (md-config.ts linkableMemos: a link's label or a `*` pair's body lexed between two prose delimiters takes an entry
//     of its own and evicts nothing; the 2026-09-20 review's list of eight most-recently-used entries evicted the
//     paragraph's at eight distinct such strings and rescanned it once per gap, a quadratic term md-emphasis-atomic.test.ts
//     now counts and times on the shape that thrashed it), and a binary search per delimiter. Before, the whitespace bounds were walked on every call ahead of the memo (a 20 KB run with
//     no whitespace and a pair every eleven characters cost sixteen times the base grammar, a run of `(_a_)` thirty),
//     and a standing pair's body lex evicted the one-slot memo (`_(_a_)_.` repeated, fifty times the base). Measured
//     here as a ratio to the base grammar on the same string in the same process, the best of interleaved passes, as
//     anchor-map-raw-offset-to-line.test.ts measures its search.
// The walk runs over a small DOM stand-in fed marked's HTML (no jsdom), the chat's own options minus the fenced gate,
// with a map holding the wanted token, as the kernel's verdict would. Synthetic fixtures only: invented paths, a
// placeholder session id.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { Lexer, Marked, Tokenizer, type MarkedExtension } from "marked";
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

test("the dry-run stand-in is `{ rules, lexer }` and the installed marked's emStrong reads nothing else from `this`, and from the stand-in's lexer, the faked half with one member, it reads inlineTokens alone: measured by a recording proxy at both levels over every dry call a reply makes. The pin records what the INSTALLED marked reads and cannot know what a later version would read; it reds by name once that version is installed and this runs", () => {
  const orig = Tokenizer.prototype.emStrong;
  const dryCalls: string[][] = [];
  const read = new Set<string>();
  const lexerRead = new Set<string>();
  Tokenizer.prototype.emStrong = function (this: Tokenizer, ...args: [string, string, string?]) {
    // a real tokenizer arrives here from an instance that reads the prototype at CALL time (the singleton, this file's
    // `base`, any instance with no emStrong override) or from one whose use() captured this patch; the chat's instances
    // captured the built-in when they were built (marked's use() reads the previous tokenizer at registration), so a
    // `*` run falling through the override never reaches this patch. Kept, though no arrival takes it in this test's
    // order, so a parse on such an instance inside the patched window is attributed to it and not read as a
    // stand-in-contract failure: untouched
    if (this instanceof Tokenizer) return orig.apply(this, args);
    dryCalls.push(Object.keys(this));
    // the reads of `this`, and, when it reads `lexer`, the reads of that lexer: the faked half of the stand-in, whose one
    // member is inlineTokens, so a read of any other member returns undefined without a throw and only this records it
    const seen = new Proxy(this as object, {
      get(t, k, r) {
        read.add(String(k));
        const v = Reflect.get(t, k, r);
        if (k === "lexer" && v !== null && typeof v === "object") return new Proxy(v as object, { get(lt, lk, lr) { lexerRead.add(String(lk)); return Reflect.get(lt, lk, lr); } });
        return v;
      },
    });
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
    assert.deepEqual([...lexerRead].sort(), ["inlineTokens"], "the built-in read " + JSON.stringify([...lexerRead].sort()) + " from the stand-in's lexer, whose one member is inlineTokens (DRY_LEXER in md-config.ts): a read the fake lacks returns undefined without a throw, and the override would return different pairs with nothing else saying so");
  } finally {
    Tokenizer.prototype.emStrong = orig;
  }
  assert.equal(chatMd.chatMdHtml("see /a-_b/c_/d.md"), "<p>see /a-_b/c_/d.md</p>\n", "the prototype is restored");
});

// ── the memo's key ───────────────────────────────────────────────────────────────────────────────────────────────────

test("the override reads no punctuation class from marked, so a memo entry depends on the masked string alone: a throwaway instance whose lexer carries a whitespace-only punctuation class renders `_see __init__.py now_` as the chat does, whichever instance renders the paragraph first (at the 2026-09-20 head the override asked marked's class and the render order decided the output: the second instance took the first's entry)", () => {
  // nothing reachable arms this today: marked 12.0.2 builds one punctuation RegExp and every inline grammar spreads it, so the
  // chat's two instances hand emStrong the same object; a marked that split the class per grammar would have armed the hole
  const inline = (Lexer as unknown as { rules: { inline: Record<string, { punctuation: RegExp }> } }).rules.inline;
  assert.ok(inline.normal.punctuation === inline.gfm.punctuation && inline.gfm.punctuation === inline.breaks.punctuation, "marked's inline grammars share one punctuation RegExp");
  // the mutation: an emStrong registered LAST (so marked runs it first) gives this parse's lexer a copy of the inline rules
  // with a whitespace-only class and falls through to the override; the shared grammar object is untouched
  const ODD = /^\s/u;
  let mutated = 0;
  const odd = {
    tokenizer: {
      emStrong(this: Tokenizer) {
        const rules = this.rules as unknown as { inline: Record<string, unknown> };
        if (rules.inline.punctuation !== ODD) { rules.inline = { ...rules.inline, punctuation: ODD }; mutated++; }
        return false as const;
      },
    },
  } as MarkedExtension;
  const oddMarked = new Marked({ gfm: true, breaks: true }, ...mdExtensions, pathAwareEmphasis, odd);
  const oddHtml = (src: string): string => oddMarked.parse(src) as string;
  // the class is in force for the built-in on that instance: a run followed by punctuation must be preceded by whitespace
  // or punctuation, and `(` is neither to a whitespace-only class
  assert.equal(chatMd.chatMdHtml("(_(a)_)"), "<p>(<em>(a)</em>)</p>\n", "the chat's class admits `(` before the opener");
  assert.equal(oddHtml("(_(a)_)"), "<p>(_(a)_)</p>\n", "the mutated class does not: the mutation reaches the built-in's own read");
  assert.ok(mutated > 0, "the mutation ran");
  // a fresh paragraph per render (no render is a hit from an earlier one); `__init__.py` is whole under the override's own
  // class (`.` beside its interior run), so both instances emphasise the sentence around the literal name
  let n = 0;
  const fresh = (): [string, string] => { const k = "k" + (n++); return ["_see __init__.py now_ " + k, "<p><em>see __init__.py now</em> " + k + "</p>\n"]; };
  // the mutated instance renders first, then the chat renders the same paragraph: the chat's answer is its own
  const [first, wantFirst] = fresh();
  const oddFirst = oddHtml(first);
  assert.equal(chatMd.chatMdHtml(first), wantFirst, "the chat, after the mutated instance rendered the same paragraph: at the 2026-09-20 head the chat took the mutated instance's entry from the shared memo, computed under that instance's class, and rendered the sentence literal (the memo was keyed on the string alone while its value read marked's class)");
  assert.equal(chatMd.userMdHtml(first), wantFirst, "and the user's instance");
  assert.equal(oddFirst, wantFirst, "the mutated instance itself: the override's own class decides, not the class its lexer carries (at the head this rendered literal: `__init__.py` was not whole under a class without `.`)");
  // the other order
  const [second, wantSecond] = fresh();
  assert.equal(chatMd.chatMdHtml(second), wantSecond, "the chat first");
  assert.equal(oddHtml(second), wantSecond, "then the mutated instance: the same (at the head it took the chat's entry, so the order, not the class, decided its output)");
  const [alone, wantAlone] = fresh();
  assert.equal(oddHtml(alone), wantAlone, "the mutated instance alone");
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
  // a round number CHOSEN with headroom for a loaded box, not derived (the 2026-09-21 review, B): the memo held, so these
  // shapes read about one to one and a half (the bounds walk before it read sixteen and more); the measured worst shape
  // across every cost row is `paths` here, the whitespace-free run at 1.4 to 1.7 at loads 6 to 33, and the shape that
  // violated the bound, the rescan after an eviction, is timed in md-emphasis-atomic.test.ts and gone with the per-parse memo
  const BOUND = 4;
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
