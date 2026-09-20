// The chat's path-aware emphasis (md-config.ts pathAwareEmphasis), the rule for a token's EDGE runs, executed over the REAL
// marked on the chat's two instances (chat-md.ts). md-emphasis-paths.test.ts runs the population note's two tables and
// md-emphasis-override.test.ts the interior-run edge and the stand-in's contract; this file pins what the 2026-09-20
// review's round 2 found beside them:
//   - a linkable token with a `_` run beside punctuation strictly inside it (`__init__.py`, `_drafts/a_.md`, `/a/_b_`) is
//     one word to the emphasis rule, its edge runs included. Round 1 hid the run inside and left the edge run visible,
//     and the built-in's closer scan then paired the edge run across the hidden middle with a partner outside the token
//     (the spec pairs it with the run inside, which the protection had taken away): `_see __init__.py now_` lost its
//     emphasis, `see __init__.py and stop__` bolded half the sentence, `_see _drafts/a_.md now_` cut the path from its
//     start and lost the kernel's link. Every row here rendered right on the tree before round 1 and wrong at its head;
//   - a plain token, one with no such run inside, keeps the edge rule: its edge run opens or closes as the spec says, as
//     on the base grammar (`_see /tmp/x_`, `_x/y.md and more_`, `_see _posts/x.md now_`), also when another, protected
//     token stands in the same pair, and when the walk's ASCII word class splits an accented path into two tokens the
//     second of which begins with a run at its edge: recorded faces of the rule, pinned as they render;
//   - a backslash before an astral symbol masks three UTF-16 units as two; the override measures a run's position on the
//     unmasked tail with those escapes counted, so a run inside a token is refused whatever follows it;
//   - cost: one scan of the paragraph per masked string whatever the paragraph holds, the memo a short most-recently-used
//     list that the nested lexes marked runs on strings of their own (a link's label, a `*` pair's or a `~~` pair's body)
//     never evict (a one-slot memo rescanned the paragraph once per link, eight to twelve times the base grammar at
//     20 KB); a run inside a token refused before the built-in scans. Counted by execution, and measured as a ratio to
//     the base grammar on the same string in the same process, the best of interleaved passes, as
//     md-emphasis-override.test.ts measures.
// The walk runs over a small DOM stand-in fed marked's HTML (no jsdom), the chat's own options minus the fenced gate, with
// a map holding the kernel-shaped keys (the tokens the kernel's tokeniser reads over the raw markdown), as the kernel's
// verdict would. Synthetic fixtures only: invented paths, a placeholder session id.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { Marked } from "marked";
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

test("a linkable token with a `_` run beside punctuation inside it is one word whole, its edge runs too: a prose pair spanning it keeps its emphasis, a stray closer after it pairs with nothing, and the walk links the token whole under the kernel's key; the base grammar renders every row differently", () => {
  for (const r of WHOLE) {
    for (const [who, render] of RENDERERS) {
      const html = render(r.text);
      assert.equal(html, r.after, who + ": " + JSON.stringify(r.text));
      assert.deepEqual(walkLinks(html, r.keys), r.links, who + ": the walk over " + html);
    }
    assert.notEqual(baseHtml(r.text), r.after, "the base grammar renders it differently: " + JSON.stringify(r.text));
  }
  assert.equal(WHOLE.length, 24);
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
  // the rule's two composed faces, recorded: a protected token in the same pair does not change how the plain token's
  // edge run pairs, and the walk's ASCII word class (path-links.ts isWordCh, the third parity follow-up) splits an accented
  // path into two tokens whose second begins with a run at its edge
  const FACES: Array<[string, string, string[], string[]]> = [
    ["_see /tmp/_x/y.md and /tmp/z_ now_", "<p><em>see /tmp/_x/y.md and /tmp/z</em> now_</p>\n", ["/tmp/_x/y.md", "/tmp/z_"], ["/tmp/_x/y.md"]],
    ["_see /a-_b/cé_/d.md now_", "<p><em>see /a-_b/cé</em>/d.md now_</p>\n", ["/a-_b/cé_/d.md"], []],
  ];
  for (const [text, want, keys, links] of FACES) for (const [who, render] of RENDERERS) {
    const html = render(text);
    assert.equal(html, want, who + ": recorded, not changed: " + JSON.stringify(text));
    assert.deepEqual(walkLinks(html, keys), links, who + ": the walk over " + html);
  }
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

test("one scan of the paragraph per masked string whatever the paragraph holds: a link's label, a `*` pair's or a `~~` pair's body lexed between two prose delimiters leaves the paragraph's entry in the memo (a one-slot memo rescanned the paragraph once per such body)", () => {
  // the memo is keyed by the masked string's text and shared by the chat's two instances, so each render below gets a
  // paragraph no earlier render in this process has seen (a distinct first word), and the count it pins is the first parse's
  let seq = 0;
  for (const [what, src] of SHAPES) {
    for (const [who, render] of RENDERERS) {
      const fresh = "P" + (seq++) + " " + src;
      const n = paragraphScans(fresh, () => { render(fresh); });
      assert.equal(n.paragraph, 1, who + ", " + what + ": the paragraph (" + fresh.length + " characters) was scanned " + n.paragraph + " times");
      assert.ok(n.all <= 1 + fresh.length, who + ", " + what + ": scans in all " + n.all);
    }
  }
  // the memo holds the paragraph's entry across the standing pair's body lex too, and the same paragraph parsed again
  // (the other instance, or a repaint) is a hit, not a scan
  const again = "P" + (seq++) + " " + SHAPES[4][1];
  const twice = paragraphScans(again, () => { chatMd.chatMdHtml(again); chatMd.userMdHtml(again); chatMd.chatMdHtml(again); });
  assert.equal(twice.paragraph, 1, "the same paragraph parsed three times is scanned once");
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

test("the override costs at most a few times the base grammar on a 20 KB paragraph of each shape: links, `*` pairs or `~~` pairs with a `_` pair inside beside prose pairs (eight to twelve times before the memo survived them), a whitespace-free path run, and prose naming a path per sentence", () => {
  const BOUND = 4;   // about one; loose for a loaded box
  const LONG: Array<[string, string]> = [
    ["links with a pair in the label", "[_a_](u) _b_ ".repeat(1600)],
    ["`*` pairs with a pair in the body", "**_a_** _b_ ".repeat(1800)],
    ["`~~` pairs with a pair in the body", "~~_a_~~ _b_ ".repeat(1800)],
    ["a whitespace-free path run", "/abcdefgh-_".repeat(1819)],
    ["prose with a member path per sentence", "The build wrote /a-_b/c_/d.md and then ~/code/my_proj/_drafts/a.md, then foo/__pycache__/bar.pyc. ".repeat(200)],
    ["pairs whose bodies hold pairs, no whitespace", "_(_a_)_.".repeat(3125)],
  ];
  for (const [what, src] of LONG) {
    const r = ratio(src);
    assert.ok(r <= BOUND, what + ": the chat grammar took " + r.toFixed(1) + "x the base grammar on " + src.length + " characters");
  }
  for (const [, src] of LONG.slice(0, 3)) assert.equal(chatMd.chatMdHtml(src), baseHtml(src), "no path: the rendering is the base's");
});
