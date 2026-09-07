// The feed page's copy of the PDF page's PER-PAGE WAIT CUE colours. styles-pdf-page-load.test.ts proves the fix on
// styles.css: pdf-chunk.ts cue() puts the viewer's own loader (div.fileview-load.fileview-pdf-page-load — swirl, "romp"
// wordmark, three .fileview-dot) INSIDE the white .fileview-pdf-page sheet, and the loader's colours are tuned for the
// pane's ground, so on the sheet in the dark theme the wordmark read at 2.8:1 and the dots at 1.6:1 — the cue that
// tells a waiting sheet from a blank one was itself near-invisible. The sheet's cue wears two on-white tokens instead,
// the light theme's own --dim and --accent. But the feed page loads feed.css ALONE (never styles.css) and mounts the
// same viewer (feed.ts calls initFileView, and the pdf chunk derives its URL from feed.js too), so the tokens and the
// two descendant rules have to exist in feed.css as well — the first fix added them to styles.css only, while the
// styles test's SHEETS listed styles.css alone and fileview-parity.test.ts's head list did not name the new rules, so
// every test stayed green while the feed page kept the faint cue (the same drift feed-pdf-page-err.test.ts caught for
// the failure notice one round earlier). This is the feed sheet's own pin, beside the styles test the way the err pair
// sits: it resolves feed.css's actual cascade along the chunk's real DOM chain (the styles test's resolver, applied to
// the other sheet), computes the ratios against the literal white sheet, and pins the tokens and both rules
// byte-equal across the two sheets so the mirror cannot drift again.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const read = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const FEED = read("feed.css");
const CHAT = read("styles.css");
const FEED_TS = read("feed.ts");
const WORD_FLOOR = 4.5;   // the wordmark is 0.86em reading text
const DOT_FLOOR = 3;      // the dots are 4px chrome, not text (WCAG's non-text floor)

// ── colours (the theme-parity helpers, with 3-digit hex for the sheet's #fff) ──
type RGB = [number, number, number];
function rgbOf(v: string, over: RGB, tokens: Map<string, string>, depth = 0): RGB | null {
  assert.ok(depth < 8, "a var() chain deeper than eight: " + v);
  v = v.trim();
  let m = v.match(/^#([0-9a-f]{3})$/i);
  if (m) return [0, 1, 2].map((i) => parseInt(m![1][i] + m![1][i], 16)) as RGB;
  m = v.match(/^#([0-9a-f]{6})$/i);
  if (m) return [0, 2, 4].map((i) => parseInt(m![1].slice(i, i + 2), 16)) as RGB;
  m = v.match(/^var\((--[a-z0-9-]+)(?:,\s*(.+))?\)$/i);
  if (m) {
    const t = tokens.get(m[1]);
    if (t) return rgbOf(t, over, tokens, depth + 1);
    assert.ok(m[2], m[1] + " is undefined and carries no fallback (a phantom token)");
    return rgbOf(m[2]!, over, tokens, depth + 1);
  }
  m = v.match(/^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+))?\s*\)$/);
  if (m) {
    const a = m[4] === undefined ? 1 : parseFloat(m[4]);
    return [1, 2, 3].map((i) => Math.round(parseInt(m![i], 10) * a + over[i - 1] * (1 - a))) as RGB;
  }
  return null;
}
function lum(c: RGB): number {
  const ch = (x: number) => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); };
  return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2]);
}
function contrast(a: RGB, b: RGB): number {
  const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}
const strip = (css: string) => css.replace(/\/\*[\s\S]*?\*\//g, "");
function tokensOf(css: string, opener: string): Map<string, string> {
  const at = css.indexOf(opener);
  assert.ok(at >= 0, opener + " present");
  const body = strip(css.slice(at, css.indexOf("\n}", at)));
  const out = new Map<string, string>();
  for (const m of body.matchAll(/(--[a-z0-9-]+):\s*([^;]+);/gi)) out.set(m[1], m[2].trim());
  assert.ok(out.size >= 30, opener + " parsed only " + out.size + " tokens — parser broken?");
  return out;
}

// ── a small cascade resolver for one property along one chain: class/id/tag compounds joined by descendant or child
// combinators — the grammar the viewer's colour rules use. A selector using anything else is skipped when it names
// none of the chain's classes and FAILS LOUDLY when it does, so a :hover / :has rule on the cue cannot slip past.
// (The same resolver as styles-pdf-page-load.test.ts: one measurement, two sheets.) ──
type Node = { tag: string; id: string | null; classes: string[] };
type Compound = { tag: string | null; id: string | null; classes: string[] };
type Rule = { head: string; selector: string; parts: Compound[]; combinators: string[]; spec: number; order: number; value: string; conditional: string | null; important: boolean };
/** does `selector` name `cls` as a whole class — `.fileview` in `.fileview:hover`, not in `.fileview-btn` */
const namesClass = (selector: string, cls: string) => new RegExp("\\." + cls.replace(/[-]/g, "\\-") + "(?![\\w-])").test(selector);
const chainOf = (s: string): Node[] => s.split(">").map((p) => {
  const m = /^([a-z][\w-]*)(#[\w-]+)?((?:\.[\w-]+)*)$/.exec(p.trim());
  assert.ok(m, "a chain element this test cannot read: " + p);
  return { tag: m![1], id: m![2] ? m![2].slice(1) : null, classes: m![3] ? m![3].slice(1).split(".") : [] };
});
const SIMPLE = /^(?:[a-z][\w-]*)?(?:[.#][\w-]+)*$/i;
function compoundOf(s: string): Compound {
  const c: Compound = { tag: null, id: null, classes: [] };
  const t = /^[a-z][\w-]*/i.exec(s);
  if (t) c.tag = t[0].toLowerCase();
  for (const m of s.matchAll(/([.#])([\w-]+)/g)) { if (m[1] === ".") c.classes.push(m[2]); else c.id = m[2]; }
  return c;
}
function splitList(sel: string): string[] {
  const out: string[] = []; let depth = 0, cur = "";
  for (const ch of sel) {
    if (ch === "(") depth++; else if (ch === ")") depth--;
    if (ch === "," && depth === 0) { out.push(cur); cur = ""; } else cur += ch;
  }
  out.push(cur);
  return out.map((x) => x.trim()).filter(Boolean);
}
/** every rule that sets `prop`, with the rules under @media/@supports remembered as conditional */
function rulesFor(css: string, prop: string, chainClasses: string[]): Rule[] {
  const rules: Rule[] = []; let order = 0;
  const walk = (s: string, cond: string | null) => {
    let i = 0;
    while (i < s.length) {
      if (/\s/.test(s[i])) { i++; continue; }
      const open = s.indexOf("{", i);
      assert.ok(open > i, "a rule without braces at `" + s.slice(i, i + 40) + "`");
      const head = s.slice(i, open).trim();
      let depth = 0, j = open;
      for (; j < s.length; j++) { if (s[j] === "{") depth++; else if (s[j] === "}" && --depth === 0) break; }
      assert.ok(j < s.length, "unbalanced braces after `" + head + "`");
      const body = s.slice(open + 1, j); i = j + 1;
      if (head.startsWith("@")) {
        if (/^@(media|container|supports)\b/.test(head)) walk(body, cond ? cond + " " + head : head);
        continue;
      }
      order++;
      let value: string | null = null; let important = false;
      for (const d of body.split(";")) {
        const colon = d.indexOf(":"); if (colon < 0) continue;
        if (d.slice(0, colon).trim().toLowerCase() !== prop) continue;
        value = d.slice(colon + 1).trim();
        // remembered, and refused in winner() only if the rule reaches the chain: the sheet may carry !important
        // rules on surfaces far from the viewer, which are no concern of the cue's
        important = /!important/.test(value);
        value = value.replace(/\s*!important\s*$/, "");
      }
      if (value === null) continue;
      for (const selector of splitList(head)) {
        const toks = selector.replace(/\s*>\s*/g, " > ").split(/\s+/);
        const parts: Compound[] = []; const combinators: string[] = []; let pending: string | null = null; let simple = true;
        for (const tok of toks) {
          if (tok === ">") { pending = ">"; continue; }
          if (!SIMPLE.test(tok)) { simple = false; break; }
          if (parts.length) combinators.push(pending || " ");
          parts.push(compoundOf(tok)); pending = null;
        }
        if (!simple || pending !== null) {
          assert.ok(!chainClasses.some((c) => namesClass(selector, c)),
            "`" + selector + "` names a class on the chain with selector syntax this resolver does not model; extend it");
          continue;
        }
        const spec = parts.reduce((n, p) => n + (p.id ? 10000 : 0) + p.classes.length * 100 + (p.tag ? 1 : 0), 0);
        rules.push({ head, selector, parts, combinators, spec, order, value, conditional: cond, important });
      }
    }
  };
  walk(strip(css), null);
  return rules;
}
const matchCompound = (c: Compound, n: Node) => (c.tag === null || c.tag === n.tag) && (c.id === null || c.id === n.id) && c.classes.every((k) => n.classes.includes(k));
function matchAt(r: Rule, chain: Node[], i: number, k: number): boolean {
  if (!matchCompound(r.parts[k], chain[i])) return false;
  if (k === 0) return true;
  if (r.combinators[k - 1] === ">") return i > 0 && matchAt(r, chain, i - 1, k - 1);
  for (let j = i - 1; j >= 0; j--) if (matchAt(r, chain, j, k - 1)) return true;
  return false;
}
/** the rule that wins `prop` on the chain's leaf: highest specificity, then latest in source */
function winner(rules: Rule[], chain: Node[]): Rule | null {
  let best: Rule | null = null;
  for (const r of rules) {
    if (!matchAt(r, chain, chain.length - 1, r.parts.length - 1)) continue;
    assert.equal(r.conditional, null, "`" + r.selector + "` styles the leaf under " + r.conditional + "; this resolver models at-rest rules only");
    assert.ok(!r.important, "`" + r.selector + "` styles the leaf !important; this resolver ranks by specificity");
    if (!best || r.spec > best.spec || (r.spec === best.spec && r.order > best.order)) best = r;
  }
  return best;
}
function ruleOf(css: string, head: string): string {
  const at = css.indexOf(head);
  assert.ok(at >= 0, head + " present");
  return css.slice(at, css.indexOf("}", at) + 1);
}

// ── the chains, as pdf-chunk.ts and file-view.ts build them (styles-pdf-page-load.test.ts pins them against the
// chunk's source; the feed page runs the same chunk, so the same chains hold here) ──
const SHEET_CLASS = "fileview-pdf-page";
const WORD_RULE = "." + SHEET_CLASS + " .fileview-load {";
const DOT_RULE = "." + SHEET_CLASS + " .fileview-dot {";
const CUE = "div.fileview-pdf > div." + SHEET_CLASS + " > div.fileview-load.fileview-pdf-page-load";
const CUE_WORD = CUE + " > span";
const CUE_DOT = CUE + " > i.fileview-dot";
const PANE_LOAD = "div.fileview > div.fileview-main > div.fileview-body > div.fileview-load";
const PANE_WORD = PANE_LOAD + " > span";
const PANE_DOT = PANE_LOAD + " > i.fileview-dot";
const CHAIN_CLASSES = ["fileview", "fileview-main", "fileview-body", "fileview-pdf", SHEET_CLASS, "fileview-load", "fileview-pdf-page-load", "fileview-dot"];
const SHEET: RGB = [255, 255, 255];
const TOKENS = ["--dim-on-white", "--accent-on-white"] as const;

test("the premise: the feed page mounts the viewer, so its sheet must dress the PDF page's wait cue too", () => {
  // feed.ts hosts the same file-view module the chat page does (initFileView), and the feed page loads feed.css
  // alone (ui/CLAUDE.md, the .romp-acted precedent) — a rule that lives in styles.css only never reaches it
  assert.match(FEED_TS, /\binitFileView\(/, "feed.ts mounts the file viewer");
  assert.ok(FEED.includes("." + SHEET_CLASS + " {"), "feed.css dresses the PDF page sheet (the layout rules landed)");
  assert.ok(FEED.includes(".fileview-load {") && FEED.includes(".fileview-dot {"), "feed.css carries the viewer's loader (the cue's own classes)");
});

const dark = tokensOf(FEED, ":root {");
const light = tokensOf(FEED, "body.theme-light {");
const themes: Array<[string, Map<string, string>]> = [["dark", dark], ["light", light]];

test("feed.css: the page sheet is a literal white in every theme — the ground this test measures against", () => {
  const body = ruleOf(FEED, "." + SHEET_CLASS + " {");
  assert.match(body, /background: #fff;/, "the sheet is #fff (a bitmap's paper), not a theme token");
  assert.doesNotMatch(strip(FEED), /body\.theme-light[^{]*\.fileview-pdf-page\b[^{]*\{[^}]*background/, "no theme re-grounds the sheet; if one does, measure against it here");
});

test("feed.css: --dim-on-white and --accent-on-white are real tokens in BOTH theme blocks, the same value — and styles.css's values", () => {
  const chatDark = tokensOf(CHAT, ":root {");
  const chatLight = tokensOf(CHAT, "body.theme-light {");
  for (const tok of TOKENS) {
    assert.ok(dark.has(tok), ":root declares " + tok);
    assert.ok(light.has(tok), "body.theme-light re-declares " + tok);
    assert.equal(dark.get(tok), light.get(tok), tok + " is one value — white is white in both themes");
    // one sheet colour across the two documents: the chat page's sheet is the reference, feed.css mirrors it
    assert.equal(dark.get(tok), chatDark.get(tok), "feed.css mirrors styles.css's :root " + tok);
    assert.equal(light.get(tok), chatLight.get(tok), "feed.css mirrors styles.css's light " + tok);
  }
  assert.equal(dark.get("--dim-on-white"), light.get("--dim"), "the on-white dim IS the light theme's own dim tier, not a third one");
  assert.equal(dark.get("--accent-on-white"), light.get("--accent"), "the on-white accent IS the light theme's own accent, not a third one");
});

test("feed.css: the wordmark's colour, resolved along the chunk's real chain, clears " + WORD_FLOOR + ":1 on the sheet in both themes", () => {
  const rules = rulesFor(FEED, "color", CHAIN_CLASSES);
  assert.equal(winner(rules, chainOf(CUE_WORD)), null, "nothing colours the span itself — it inherits the cue's colour, which is what this test resolves");
  const w = winner(rules, chainOf(CUE));
  assert.ok(w, "some rule colours the cue");
  assert.equal(w!.selector, "." + SHEET_CLASS + " .fileview-load", "the loader-on-a-sheet rule wins, by specificity, over the loader's own");
  assert.equal(w!.value, "var(--dim-on-white)");
  for (const [theme, tokens] of themes) {
    const ink = rgbOf(w!.value, SHEET, tokens);
    assert.ok(ink, theme + ": the value resolves to a colour");
    const ratio = contrast(ink!, SHEET);
    assert.ok(ratio >= WORD_FLOOR, theme + ": the wordmark reads at " + ratio.toFixed(2) + ":1 on the white sheet, below " + WORD_FLOOR);
  }
});

test("feed.css: the dots' fill, resolved along the chunk's real chain, clears " + DOT_FLOOR + ":1 on the sheet in both themes", () => {
  assert.equal(winner(rulesFor(FEED, "background-color", CHAIN_CLASSES), chainOf(CUE_DOT)), null, "no background-color rule competes with the dot's background shorthand");
  const w = winner(rulesFor(FEED, "background", CHAIN_CLASSES), chainOf(CUE_DOT));
  assert.ok(w, "some rule fills the dot");
  assert.equal(w!.selector, "." + SHEET_CLASS + " .fileview-dot", "the dot-on-a-sheet rule wins, by specificity, over the dot's own");
  assert.equal(w!.value, "var(--accent-on-white)");
  for (const [theme, tokens] of themes) {
    const fill = rgbOf(w!.value, SHEET, tokens);
    assert.ok(fill, theme + ": the value resolves to a colour");
    const ratio = contrast(fill!, SHEET);
    assert.ok(ratio >= DOT_FLOOR, theme + ": a dot sits at " + ratio.toFixed(2) + ":1 on the white sheet, below " + DOT_FLOOR);
  }
});

test("feed.css: the loader OUTSIDE a sheet is untouched — the pane's own wait still wears --dim and --accent on the pane", () => {
  const color = rulesFor(FEED, "color", CHAIN_CLASSES);
  assert.equal(winner(color, chainOf(PANE_WORD)), null, "the pane loader's span inherits too");
  const w = winner(color, chainOf(PANE_LOAD));
  assert.ok(w, "the loader colours the pane's wait");
  assert.equal(w!.selector, ".fileview-load");
  assert.equal(w!.value, "var(--dim)");
  const d = winner(rulesFor(FEED, "background", CHAIN_CLASSES), chainOf(PANE_DOT));
  assert.ok(d, "the dot fills the pane's wait");
  assert.equal(d!.selector, ".fileview-dot");
  assert.equal(d!.value, "var(--accent)");
});

test("the two cue-on-a-sheet rules are byte-equal in both sheets (the mirror fileview-parity's head list does not name)", () => {
  for (const head of [WORD_RULE, DOT_RULE]) {
    assert.equal(ruleOf(FEED, head), ruleOf(CHAT, head), head + " mirrors exactly");
    // and it sits where the chat sheet keeps it: after the page's layout rules and the sheet's failure dress, so a
    // reader of either sheet finds every on-white rule next to the sheet
    for (const [name, css] of [["feed.css", FEED], ["styles.css", CHAT]] as const) {
      assert.ok(css.indexOf(head) > css.indexOf("." + SHEET_CLASS + " .fileview-err {"), name + ": " + head + " follows the sheet's failure dress");
    }
  }
});
