// The feed page's copy of the PDF-page failure colour. styles-pdf-page-err.test.ts proves the fix on styles.css:
// a page pdf.js cannot draw carries its failure IN the white .fileview-pdf-page sheet, and the .fileview-err
// dress's --warn amber read at 2.3:1 there on the dark theme, so the sheet's dress wears --warn-on-white. But the
// feed page loads feed.css ALONE (never styles.css) and mounts the same viewer (feed.ts calls initFileView, and the
// pdf chunk derives its URL from feed.js too), so the token and the descendant rule have to exist in feed.css as
// well — the first fix added them to styles.css only, and fileview-parity.test.ts's head list did not name the new
// rule, so both sheets' tests stayed green while the feed page kept the 2.3:1 notice. This test resolves feed.css's
// actual cascade along the chunk's real DOM chain (the styles test's resolver, applied to the other sheet), and
// pins the rule byte-equal across the two sheets so the mirror cannot drift again.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const read = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const FEED = read("feed.css");
const CHAT = read("styles.css");
const FEED_TS = read("feed.ts");
const FLOOR = 4.5;   // the dress is 0.86em reading text, not large chrome

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
// none of the chain's classes and FAILS LOUDLY when it does, so a :hover / :has rule on the dress cannot slip past.
// (The same resolver as styles-pdf-page-err.test.ts: one measurement, two sheets.) ──
type Node = { tag: string; id: string | null; classes: string[] };
type Compound = { tag: string | null; id: string | null; classes: string[] };
type Rule = { head: string; selector: string; parts: Compound[]; combinators: string[]; spec: number; order: number; value: string; conditional: string | null };
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
      let value: string | null = null;
      for (const d of body.split(";")) {
        const colon = d.indexOf(":"); if (colon < 0) continue;
        if (d.slice(0, colon).trim().toLowerCase() !== prop) continue;
        value = d.slice(colon + 1).trim();
        assert.doesNotMatch(value, /!important/, "`" + head + "` sets " + prop + " !important; this resolver ranks by specificity");
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
          assert.ok(!chainClasses.some((c) => selector.includes("." + c)),
            "`" + selector + "` names a class on the chain with selector syntax this resolver does not model; extend it");
          continue;
        }
        const spec = parts.reduce((n, p) => n + (p.id ? 10000 : 0) + p.classes.length * 100 + (p.tag ? 1 : 0), 0);
        rules.push({ head, selector, parts, combinators, spec, order, value, conditional: cond });
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
    assert.equal(r.conditional, null, "`" + r.selector + "` colours the leaf under " + r.conditional + "; this resolver models at-rest rules only");
    if (!best || r.spec > best.spec || (r.spec === best.spec && r.order > best.order)) best = r;
  }
  return best;
}
function ruleOf(css: string, head: string): string {
  const at = css.indexOf(head);
  assert.ok(at >= 0, head + " present");
  return css.slice(at, css.indexOf("}", at) + 1);
}

// ── the chain, as pdf-chunk.ts builds it (styles-pdf-page-err.test.ts pins it against the chunk's source) ──
const SHEET_CLASS = "fileview-pdf-page";
const SHEET_RULE = "." + SHEET_CLASS + " .fileview-err {";
const NOTE = "div.fileview-pdf > div." + SHEET_CLASS + " > div.fileview-err.fileview-pdf-page-err";
const PANE_NOTE = "div.fileview > div.fileview-main > div.fileview-body > div.fileview-err";
const CHAIN_CLASSES = ["fileview-pdf", SHEET_CLASS, "fileview-err", "fileview-pdf-page-err"];

test("the premise: the feed page mounts the viewer, so its sheet must dress the PDF page's failure too", () => {
  // feed.ts hosts the same file-view module the chat page does (initFileView), and the feed page loads feed.css
  // alone (ui/CLAUDE.md, the .romp-acted precedent) — a rule that lives in styles.css only never reaches it
  assert.match(FEED_TS, /\binitFileView\(/, "feed.ts mounts the file viewer");
  assert.ok(FEED.includes("." + SHEET_CLASS + " {"), "feed.css dresses the PDF page sheet (the layout rules landed)");
});

const dark = tokensOf(FEED, ":root {");
const light = tokensOf(FEED, "body.theme-light {");
const themes: Array<[string, Map<string, string>]> = [["dark", dark], ["light", light]];

test("feed.css: the page sheet is a literal white in every theme — the ground this test measures against", () => {
  const body = ruleOf(FEED, "." + SHEET_CLASS + " {");
  assert.match(body, /background: #fff;/, "the sheet is #fff (a bitmap's paper), not a theme token");
  assert.doesNotMatch(strip(FEED), /body\.theme-light[^{]*\.fileview-pdf-page\b[^{]*\{[^}]*background/, "no theme re-grounds the sheet; if one does, measure against it here");
});

test("feed.css: --warn-on-white is a real token in BOTH theme blocks, the same value — and styles.css's value", () => {
  assert.ok(dark.has("--warn-on-white"), ":root declares it");
  assert.ok(light.has("--warn-on-white"), "body.theme-light re-declares it");
  assert.equal(dark.get("--warn-on-white"), light.get("--warn-on-white"), "white is white in both themes");
  assert.equal(dark.get("--warn-on-white"), light.get("--warn"), "it IS the light theme's own heads-up amber, not a third one");
  // one amber across the two documents: the chat page's sheet is the reference, feed.css mirrors it
  assert.equal(dark.get("--warn-on-white"), tokensOf(CHAT, ":root {").get("--warn-on-white"), "feed.css mirrors styles.css's :root value");
  assert.equal(light.get("--warn-on-white"), tokensOf(CHAT, "body.theme-light {").get("--warn-on-white"), "feed.css mirrors styles.css's light value");
});

test("feed.css: the note's colour, resolved along the chunk's real chain, clears " + FLOOR + ":1 on the sheet in both themes", () => {
  const rules = rulesFor(FEED, "color", CHAIN_CLASSES);
  const w = winner(rules, chainOf(NOTE));
  assert.ok(w, "some rule colours the note");
  assert.equal(w!.selector, "." + SHEET_CLASS + " .fileview-err", "the dress-on-a-sheet rule wins, by specificity, over the dress's own");
  assert.equal(w!.value, "var(--warn-on-white)");
  const sheet: RGB = [255, 255, 255];
  for (const [theme, tokens] of themes) {
    const ink = rgbOf(w!.value, sheet, tokens);
    assert.ok(ink, theme + ": the value resolves to a colour");
    const ratio = contrast(ink!, sheet);
    assert.ok(ratio >= FLOOR, theme + ": the failure note reads at " + ratio.toFixed(2) + ":1 on the white sheet, below " + FLOOR);
  }
});

test("feed.css: the dress OUTSIDE a sheet is untouched — the pane's refusal still wears --warn on the pane", () => {
  const w = winner(rulesFor(FEED, "color", CHAIN_CLASSES), chainOf(PANE_NOTE));
  assert.ok(w, "the dress colours the pane's refusal");
  assert.equal(w!.selector, ".fileview-err");
  assert.equal(w!.value, "var(--warn)");
});

test("the dress-on-a-sheet rule is byte-equal in both sheets (the mirror fileview-parity's head list does not name)", () => {
  assert.equal(ruleOf(FEED, SHEET_RULE), ruleOf(CHAT, SHEET_RULE), SHEET_RULE + " mirrors exactly");
  // and it sits where the chat sheet keeps it: after the page's layout rules, so a reader of either sheet
  // finds the sheet's dress next to the sheet
  for (const [name, css] of [["feed.css", FEED], ["styles.css", CHAT]] as const) {
    assert.ok(css.indexOf(SHEET_RULE) > css.indexOf(".fileview-pdffall .fileview-frame {"), name + ": the rule follows the page layout rules");
  }
});
