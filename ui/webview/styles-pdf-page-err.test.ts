// A PDF page pdf.js cannot draw carries its failure IN the page (pdf-chunk.ts fail(): a .fileview-err note inside
// the .fileview-pdf-page wrapper). The wrapper is a WHITE sheet in every theme (.fileview-pdf-page's background is
// a literal #fff, the paper a bitmap sits on), but the dress's --warn amber is tuned for the pane's ground: on the
// dark theme it read at 2.3:1 on the sheet, below the 4.5:1 the sheets hold reading text to (theme-parity.test.ts),
// so the one loud, in-place error the PDF view has was its faintest text. The fix is a descendant rule — the dress
// on a sheet wears --warn-on-white, the light theme's own amber, declared in both theme blocks because white is
// white in both. theme-parity checks token-on-token pairs only, so a raw #fff ground escapes it; this test resolves
// the sheet's actual cascade along the chunk's real DOM chain and computes the ratio against the literal sheet.
// styles.css only: the feed page's mirror (feed.css) is held byte-equal by fileview-parity.test.ts's head list.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const read = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const CSS = read("styles.css");
const CHUNK = read("pdf-chunk.ts");
const SHEETS: Array<[string, string]> = [["styles.css", CSS]];
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
// none of the chain's classes and FAILS LOUDLY when it does, so a :hover / :has rule on the dress cannot slip past. ──
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

// ── the chain, as pdf-chunk.ts builds it (pinned so the model cannot outlive the DOM) ──
const SHEET_CLASS = "fileview-pdf-page";
const NOTE = "div.fileview-pdf > div." + SHEET_CLASS + " > div.fileview-err.fileview-pdf-page-err";
const PANE_NOTE = "div.fileview > div.fileview-main > div.fileview-body > div.fileview-err";
const CHAIN_CLASSES = ["fileview-pdf", SHEET_CLASS, "fileview-err", "fileview-pdf-page-err"];

test("pdf-chunk.ts puts the failure note, in the dress, INSIDE the white page wrapper", () => {
  assert.match(CHUNK, /const root = document\.createElement\("div"\);\n\s*root\.className = "fileview-pdf";/);
  assert.match(CHUNK, /const wrap = document\.createElement\("div"\);\n\s*wrap\.className = "fileview-pdf-page";/);
  // the note wears the dress (plus its own hook class) and lands in the page's wrapper — the two facts the
  // sheet's rule rests on; its words are pdf-chunk.test.ts's to pin
  assert.match(CHUNK, /note\.className = "fileview-err fileview-pdf-page-err";[^]*?p\.wrap\.appendChild\(note\);/);
});

for (const [name, css] of SHEETS) {
  const dark = tokensOf(css, ":root {");
  const light = tokensOf(css, "body.theme-light {");
  const themes: Array<[string, Map<string, string>]> = [["dark", dark], ["light", light]];

  test(name + ": the page sheet is a literal white in every theme — the ground this test measures against", () => {
    const at = css.indexOf("." + SHEET_CLASS + " {");
    assert.ok(at >= 0, "the sheet rule");
    const body = css.slice(at, css.indexOf("}", at));
    assert.match(body, /background: #fff;/, "the sheet is #fff (a bitmap's paper), not a theme token");
    assert.doesNotMatch(strip(css), /body\.theme-light[^{]*\.fileview-pdf-page\b[^{]*\{[^}]*background/, "no theme re-grounds the sheet; if one does, measure against it here");
  });

  test(name + ": --warn-on-white is a real token in BOTH theme blocks, the same value — white is white", () => {
    assert.ok(dark.has("--warn-on-white"), ":root declares it");
    assert.ok(light.has("--warn-on-white"), "body.theme-light re-declares it");
    assert.equal(dark.get("--warn-on-white"), light.get("--warn-on-white"));
    assert.equal(dark.get("--warn-on-white"), light.get("--warn"), "it IS the light theme's own heads-up amber, not a third one");
  });

  test(name + ": the note's colour, resolved along the chunk's real chain, clears " + FLOOR + ":1 on the sheet in both themes", () => {
    const rules = rulesFor(css, "color", CHAIN_CLASSES);
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

  test(name + ": the dress OUTSIDE a sheet is untouched — the pane's refusal still wears --warn on the pane", () => {
    const w = winner(rulesFor(css, "color", CHAIN_CLASSES), chainOf(PANE_NOTE));
    assert.ok(w, "the dress colours the pane's refusal");
    assert.equal(w!.selector, ".fileview-err");
    assert.equal(w!.value, "var(--warn)");
  });
}
