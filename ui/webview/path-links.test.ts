// path-links.ts's two promises beyond its matches (plans/file-review.md, Slice 0; fixed 2026-09-06):
//
// 1. A link is a CONTROL from the keyboard too. The span it emits is a tab stop announced as a link, and
//    Enter or Space on it clicks it — the click the host already handles (waiting.ts's delegates, render.ts's
//    per-span binder). Without that, the links in the Waiting-on-you fold and its Reply modal — whose focus
//    sits in a textarea — could be reached only with a pointer.
// 2. The walk costs time LINEAR in the text. CLICKABLE_PATH_RE run with the g flag restarts at every
//    position and rescans an unbroken word run to its end each time: one slash plus a 40K-character run
//    cost seconds per text node, and the Waiting-on-you pane re-links every session's todo detail — which
//    the kernel does not cap — on every feed frame. PathTokenScanner drives the same regex in linear time;
//    the trailing-punctuation trim, quadratic for the same reason on a long token of dots, scans backwards.
//    The regex's TEXT is the kernel's parity contract (tests/fixtures/path_token_parity.json), so what is
//    pinned here is that the scanner finds exactly what the regex finds — from every start position, over
//    fuzzed and adversarial texts — and that the pathological inputs finish in milliseconds.
//
// The matcher runs for real over a small DOM stand-in (the user-todo-links.test.ts idiom — no jsdom).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const UI = path.resolve(process.cwd(), "..", "ui", "webview");
const LINKS = fs.readFileSync(path.join(UI, "path-links.ts"), "utf8");

// synthetic world: the notes-api demo, a placeholder sid
const SID = "11111111-2222-3333-4444-555555555555";

// ── a DOM stand-in just big enough for the walk and the key handler ────────────────────────────────
class TextNode {
  parentElement: Elm | null = null;
  constructor(public data: string) {}
  replaceWith(frag: Frag): void {
    const p = this.parentElement!;
    const i = p.childNodes.indexOf(this);
    const kids = frag.childNodes.map((c) => (typeof c === "string" ? new TextNode(c) : c));
    for (const k of kids) k.parentElement = p;
    p.childNodes.splice(i, 1, ...kids);
  }
}
class Frag { childNodes: (Elm | TextNode | string)[] = []; appendChild(c: Elm | TextNode | string) { this.childNodes.push(c); } }
class Elm {
  className = ""; title = ""; dataset: Record<string, string> = {}; parentElement: Elm | null = null;
  childNodes: (Elm | TextNode)[] = [];
  tabIndex = -1; role: string | null = null; onkeydown: ((e: unknown) => void) | null = null;
  clicks = 0;
  constructor(public tagName: string) {}
  click(): void { this.clicks++; }
  set textContent(s: string) { const t = new TextNode(s); t.parentElement = this; this.childNodes = [t]; }
  get textContent(): string { return this.childNodes.map((c) => (c instanceof TextNode ? c.data : c.textContent)).join(""); }
  appendChild(c: Elm | TextNode): Elm | TextNode { c.parentElement = this; this.childNodes.push(c); return c; }
  closest(sel: string): Elm | null {
    const alts = sel.split(",").map((s) => s.trim());
    for (let n: Elm | null = this; n; n = n.parentElement) {
      for (const a of alts) {
        if (a.startsWith(".") ? n.className.split(/\s+/).includes(a.slice(1)) : n.tagName === a) return n;
      }
    }
    return null;
  }
  get spans(): Elm[] { return this.childNodes.filter((c): c is Elm => c instanceof Elm); }
  get texts(): string[] { return this.childNodes.filter((c): c is TextNode => c instanceof TextNode).map((c) => c.data); }
}
function textNodesOf(root: Elm): TextNode[] {
  const out: TextNode[] = [];
  const walk = (n: Elm) => { for (const c of n.childNodes) { if (c instanceof TextNode) out.push(c); else walk(c); } };
  walk(root);
  return out;
}
(globalThis as any).NodeFilter = { SHOW_TEXT: 4 };
(globalThis as any).document = {
  createElement: (tag: string) => new Elm(tag),
  createTextNode: (s: string) => s,
  createDocumentFragment: () => new Frag(),
  createTreeWalker: (root: Elm) => { const nodes = textNodesOf(root); let i = 0; return { nextNode: () => (i < nodes.length ? nodes[i++] : null) }; },
};
// a keydown as the browser would deliver it to the span's own handler
function press(a: Elm, key: string): boolean {
  let prevented = false;
  a.onkeydown!({ key, currentTarget: a, preventDefault: () => { prevented = true; } });
  return prevented;
}

// ── 1. the keyboard ───────────────────────────────────────────────────────────────────────────────
test("a path link is a tab stop announced as a link, and Enter or Space clicks it — the host's click, from the keyboard", async () => {
  const { openPathLink, fileUriLink } = await import("./path-links");
  const a = openPathLink("docs/design.md", "docs/design.md", true, SID) as unknown as Elm;
  assert.equal(a.tabIndex, 0, "reachable with Tab, like the <a> it stands in for");
  assert.equal(a.role, "link");
  assert.equal(typeof a.onkeydown, "function");
  assert.equal(press(a, "Enter"), true, "Enter is consumed…");
  assert.equal(a.clicks, 1, "…and becomes this span's click, which bubbles to whatever the host bound");
  assert.equal(press(a, " "), true, "Space too — prevented, so it does not also scroll the pane");
  assert.equal(a.clicks, 2);
  for (const k of ["Tab", "Escape", "a", "ArrowDown", "Shift"]) {
    assert.equal(press(a, k), false, k + " is left to the browser");
  }
  assert.equal(a.clicks, 2, "no other key activates");
  // every span the module mints takes the same route — a file:// URI's included
  const u = fileUriLink("file:///tmp/notes-api/a.pdf") as unknown as Elm;
  assert.equal(u.tabIndex, 0); assert.equal(u.role, "link"); press(u, "Enter"); assert.equal(u.clicks, 1);
  // the click stays the host's: the span carries the act and the target, and no route of its own
  assert.deepEqual(a.dataset, { act: "openpath", path: "docs/design.md", rel: "1", sid: SID });
  assert.match(LINKS, /a\.tabIndex = 0;/);
  assert.match(LINKS, /a\.role = "link";/);
  assert.match(LINKS, /a\.onkeydown = pathLinkKey;/);
  assert.match(LINKS, /function pathLinkKey\(e: KeyboardEvent\): void \{\n\s*if \(e\.key !== "Enter" && e\.key !== " "\) return;\n\s*e\.preventDefault\(\);\n\s*\(e\.currentTarget as HTMLElement\)\.click\(\);/);
});

test("the walk's links carry the keyboard route too", async () => {
  const { linkifyPathTokens } = await import("./path-links");
  const d = new Elm("div"); d.className = "ut-detail";
  d.textContent = "read docs/design.md and file:///tmp/notes-api/out.png";
  linkifyPathTokens(d as unknown as HTMLElement, SID);
  assert.equal(d.spans.length, 2);
  for (const s of d.spans) { assert.equal(s.tabIndex, 0); assert.equal(s.role, "link"); press(s, "Enter"); assert.equal(s.clicks, 1); }
});

// ── 2. the scanner is the regex, in linear time ───────────────────────────────────────────────────
// what CLICKABLE_PATH_RE.exec finds from `from` — the reference the scanner is held to
function refNext(re: RegExp, text: string, from: number): [number, number] | null {
  re.lastIndex = from;
  const m = re.exec(text);
  return m ? [m.index, m.index + m[0].length] : null;
}
// a small deterministic PRNG so a failure reproduces
function rng(seed: number): () => number {
  let s = seed >>> 0;
  return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
}
// every character class the regex distinguishes, plus a few it must not: non-ASCII letters that
// uppercase to ASCII (U+017F to S, the Kelvin sign U+212A to K) must stay outside \w under the i flag, and
// a no-break space (U+00A0) is \s
const ALPHABET = ["a", "b", "z", "A", "Z", "f", "F", "i", "l", "e", "E", "0", "9", "_", "-", ".", "~", "/", ":",
  "(", ")", "<", ">", "\"", "'", "`", " ", "\n", "%", "#", "\u00e9", "\u017f", "\u212a", "\u00a0"];
// weighted toward the run characters, where the reasoning lives
const WEIGHTED = ALPHABET.concat("a", "a", "b", "f", "e", "_", "-", "-", ".", ".", "~", "/", "/", " ", "0");

function sameAsRegexFromEveryPosition(text: string, PathTokenScanner: new (t: string) => { next(from: number): [number, number] | null }) {
  const re = new RegExp(/file:\/\/\/?[^\s<>"'`)]+|[~.\w\-]*\/[~.\w\-/]*[\w\-]|[\w\-][\w\-.]*\.[A-Za-z0-9]{1,8}/.source, "gi");
  // ONE scanner, asked from every position in turn — so what a failure taught it at an earlier position
  // is applied at the later ones, exactly as the walk uses it
  const scan = new PathTokenScanner(text);
  for (let from = 0; from <= text.length; from++) {
    assert.deepEqual(scan.next(from), refNext(re, text, from), JSON.stringify(text) + " from " + from);
  }
  // and the walk's own cadence: resume at each match's end
  const fresh = new PathTokenScanner(text);
  const got: [number, number][] = [], want: [number, number][] = [];
  for (let from = 0, m; (m = fresh.next(from)); from = m[1]) got.push(m);
  for (let from = 0, m; (m = refNext(re, text, from)); from = m[1]) want.push(m);
  assert.deepEqual(got, want, JSON.stringify(text) + " sequence");
}

test("the scanner's arms are cut from CLICKABLE_PATH_RE itself — three, and the regex's own text", async () => {
  const { CLICKABLE_PATH_RE } = await import("./path-links");
  const arms = CLICKABLE_PATH_RE.source.split("|");
  assert.equal(arms.length, 3, "a | inside a class would cut the regex wrong — the scanner reads the source");
  assert.match(arms[0], /^file:/); assert.match(arms[1], /^\[~\.\\w\\-\]\*/); assert.match(arms[2], /^\[\\w\\-\]/);
  assert.match(LINKS, /const \[URI_ARM, PATH_ARM, BARE_ARM\] = CLICKABLE_PATH_RE\.source\.split\("\|"\)\.map\(\(arm\) => new RegExp\(arm, "iy"\)\);/);
  assert.match(LINKS, /export const CLICKABLE_PATH_RE = \/file:\\\/\\\/\\\/\?\[\^\\s<>"'`\)\]\+\|\[~\.\\w\\-\]\*\\\/\[~\.\\w\\-\/\]\*\[\\w\\-\]\|\[\\w\\-\]\[\\w\\-\.\]\*\\\.\[A-Za-z0-9\]\{1,8\}\/gi;/,
    "the regex's text is the kernel's parity contract and is untouched");
});

test("the scanner finds exactly what the regex finds, from every start position: adversarial shapes", async () => {
  const { PathTokenScanner } = await import("./path-links");
  const cases = [
    "", "a", "/", ".", "~", "-", "f", "file", "file:", "file://", "file:///", "file:// x", "file://)", "FILE:///X/y.MD",
    "xfile:///a/b", "aaaafile:///a/b", "a.file:///a", "~/file:///a", "file:///a/b.md.", "file:///a%20b/c.md).",
    "a~a~a~a~a", "a~b.md~c", "~~~~", "~~~~/", "////", "////a", "....", "..../x", "a....", "-.-.-", "a.-b", "a-.b",
    "a.b_.c_.d_", "abc.defghijklmnop", "abc.defghijklmnop.q", "a.b.c", "x_.y", "_._", "1.2.3", ".gitignore", "./a", "../a/b.py",
    "and/or 24/7 TCP/IP", "see design/foo.md for details", "wrote report.md, then plot.png!", "np.array and pd.DataFrame",
    "a/b~/c", "~/x/y.md", "a//b", "a///b.c", "x/", "/x", "/x/", "a b/c d", "(a/b.md)", "`a.md`", "<a/b.md>", "\"a/b\"",
    "see /tmp/out.log " + "a".repeat(300), "x-".repeat(200) + "/y", "-".repeat(300), ".".repeat(300) + "/x",
    "a~".repeat(200), "/".repeat(300), "~".repeat(300) + "/", "aaaa" + "~".repeat(200) + "/" + "~".repeat(200),
    "aaaa" + "/".repeat(50) + "~~~~", "\u017f.md K.md \u00e9/x.md", "a\u00a0b/c.md", "file:///a\u00a0b",
    "ffff:///x", "fil:///x", "File:///x/y", "fILE://x",
  ];
  for (const c of cases) sameAsRegexFromEveryPosition(c, PathTokenScanner);
});

test("the scanner finds exactly what the regex finds, from every start position: fuzzed texts", async () => {
  const { PathTokenScanner } = await import("./path-links");
  const rand = rng(20260906);
  for (let n = 0; n < 6000; n++) {
    const len = Math.floor(rand() * 40);
    let s = "";
    for (let i = 0; i < len; i++) s += WEIGHTED[Math.floor(rand() * WEIGHTED.length)];
    sameAsRegexFromEveryPosition(s, PathTokenScanner);
  }
});

test("tokenizer parity: the scanner over the shared kernel fixture, on the kernel's own loop", async () => {
  const { PathTokenScanner, TRAILING_PUNCT_RE } = await import("./path-links");
  const fixture = JSON.parse(fs.readFileSync(path.resolve(process.cwd(), "..", "tests", "fixtures", "path_token_parity.json"), "utf8"));
  assert.ok(fixture.cases.length >= 10);
  for (const c of fixture.cases as { text: string; tokens: string[] }[]) {
    const toks: string[] = [];
    const scan = new PathTokenScanner(c.text);
    for (let pos = 0; ;) {
      const m = scan.next(pos);
      if (!m) break;
      const tok = c.text.slice(m[0], m[1]).replace(TRAILING_PUNCT_RE, "");
      pos = Math.max(m[0] + tok.length, pos + 1);
      if (tok && !toks.includes(tok)) toks.push(tok);
    }
    assert.deepEqual(toks, c.tokens, c.text);
  }
});

test("the trailing-punctuation set has one source: the regex is built from the characters the trim scans", async () => {
  const { TRAILING_PUNCT, TRAILING_PUNCT_RE } = await import("./path-links");
  assert.equal(TRAILING_PUNCT, ".,;:!?)]}>\"'`", "the kernel mirrors this set as _PATH_TRAIL_RE");
  for (let c = 0; c < 0x250; c++) {
    const ch = String.fromCharCode(c);
    assert.equal(TRAILING_PUNCT_RE.test(ch), TRAILING_PUNCT.includes(ch), "U+" + c.toString(16));
  }
  assert.equal("a/b.md.".replace(TRAILING_PUNCT_RE, ""), "a/b.md");
  assert.equal("x.md).".replace(TRAILING_PUNCT_RE, ""), "x.md");
  assert.match(LINKS, /function trailingPunct\(tok: string\): \[string\] \| null \{\n\s*let i = tok\.length;\n\s*while \(i > 0 && TRAILING_PUNCT\.includes\(tok\[i - 1\]\)\) i--;/);
  assert.match(LINKS, /const trail = trailingPunct\(tok\);/);
  assert.doesNotMatch(LINKS, /tok\.match\(TRAILING_PUNCT_RE\)/, "the regex's `+$` from every position is the quadratic form");
});

test("the walk, executed: the trim and the resume rules read exactly as before", async () => {
  const { linkifyPathTokens } = await import("./path-links");
  const d = new Elm("div");
  d.textContent = "see file:///tmp/notes-api/a.md). Then and/or docs/b.md, and x/y.";
  const hits = linkifyPathTokens(d as unknown as HTMLElement, SID);
  assert.deepEqual(hits.map((h) => h.open), ["/tmp/notes-api/a.md", "docs/b.md"]);
  assert.deepEqual(d.spans.map((s) => s.textContent), ["file:///tmp/notes-api/a.md", "docs/b.md"], "closing punctuation stays outside the link");
  assert.deepEqual(d.texts, ["see ", "). Then and/or ", ", and x/y."], "and/or and x/y stay prose; the text reads as written");
  // inline code: a bare known-extension filename links; a dotted identifier does not
  const code = new Elm("code"); code.textContent = "np.array vs power2_watts.pdf";
  const hits2 = linkifyPathTokens(code as unknown as HTMLElement, null);
  assert.deepEqual(hits2.map((h) => h.open), ["power2_watts.pdf"]);
  assert.deepEqual(code.texts, ["np.array vs "]);
});

test("a pathological detail costs milliseconds, not seconds: the finding's inputs through the real walk", async () => {
  const { linkifyPathTokens } = await import("./path-links");
  // each of these took 1.5-6 s under the g-flag loop or the regex trim (measured 2026-09-06, node 22)
  const inputs: [string, string, string[]][] = [
    ["one slash then a 40K word run", "see /tmp/out.log " + "a".repeat(40000), ["/tmp/out.log"]],
    ["a 40K hex hash", "see /tmp/out.log " + "0123456789abcdef".repeat(2500), ["/tmp/out.log"]],
    ["a 40K separator line", "see /tmp/out.log " + "-".repeat(40000), ["/tmp/out.log"]],
    ["a 60K a~ alternation", "see /tmp/out.log " + "a~".repeat(30000), ["/tmp/out.log"]],
    ["an 80K dotted token the path arm matches whole, left prose by the shape gate", ".".repeat(80000) + "/x", []],
    ["an 80K dotted token the path arm matches whole, linked", ".".repeat(80000) + "/x.md", [".".repeat(80000) + "/x.md"]],
    ["40K slashes", "/".repeat(40000) + " a/b.md", ["a/b.md"]],
    ["40K tildes then a slash", "~".repeat(40000) + "/ a/b.md", ["a/b.md"]],
    ["a word run ending in file", "a".repeat(40000) + "file:///tmp/notes-api/x.md", ["/tmp/notes-api/x.md"]],
  ];
  for (const [name, text, links] of inputs) {
    const d = new Elm("div"); d.textContent = text;
    const t0 = performance.now();
    const hits = linkifyPathTokens(d as unknown as HTMLElement, SID);
    const ms = performance.now() - t0;
    assert.ok(ms < 1000, name + ": " + ms.toFixed(0) + " ms — the g-flag loop took seconds here");
    assert.deepEqual(hits.map((h) => h.open), links, name);
    assert.equal(d.textContent, text, name + ": the text reads exactly as written");
  }
});
