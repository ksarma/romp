// The ink of KaTeX's flagged text. renderMathPlaceholders (math.ts) renders a formula KaTeX cannot parse a second time
// under throwOnError: false, which leaves a span.katex-error holding the TeX, and an unsupported command inside a formula
// renders its text the same way; both take their colour from KaTeX's errorColor option, written verbatim into an inline
// style. KaTeX's default, #cc0000, read at 2.8:1 on the dark page (rgb 30,30,30), under the 4.5:1 the sheets hold reading
// text to (theme-parity.test.ts), and Slice 4 of plans/markdown-viewer.md brought the fill to the Files pane and the feed,
// where a note's bad formula had shown as plain TeX before. So the option names a theme token, --math-err (math.ts
// MATH_ERROR_COLOR), declared in the :root and body.theme-light blocks of BOTH sheets: the chat page loads styles.css
// alone, the feed page feed.css alone, and each mounts the viewer. Two tests: the fill's side, executed through KaTeX's
// string renderer (the same pipeline minus the node building; the browser legs run the real call), and the sheets'
// side, the token present in both blocks of both sheets, mirrored, readable on --bg in each theme, and listed among
// theme-parity's designated pairs, so a sheet that lost the declaration fails here and not in a reader's eye.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import katex from "katex";
import { MATH_ERROR_COLOR, MATH_MAX_SIZE_EM } from "./math";

const read = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const TOKEN = "--math-err";
const FLOOR = 4.5;   // the flagged TeX is reading text at the formula's size

test("the fill hands KaTeX a theme token for its error ink, and KaTeX writes it on the flagged span and on an unsupported command's text", () => {
  assert.equal(MATH_ERROR_COLOR, "var(" + TOKEN + ")", "a var() with no fallback: where no sheet defines the token the text inherits the page's ink and stays readable");
  assert.match(read("math.ts"), /const KATEX_OPTIONS = \{ output: "html", trust: false, maxSize: MATH_MAX_SIZE_EM, errorColor: MATH_ERROR_COLOR \} as const;/,
    "every katex.render call carries the ink (render-math.test.ts pins the two calls spread it)");
  const opts = { output: "html", trust: false, maxSize: MATH_MAX_SIZE_EM, errorColor: MATH_ERROR_COLOR, throwOnError: false, displayMode: false } as const;
  const flagged = katex.renderToString("\\frac{1}{", opts);
  assert.match(flagged, /<span class="katex-error" title="[^"]*" style="color:var\(--math-err\)">/, "the syntax-error span wears the token, not KaTeX's #cc0000: " + flagged);
  assert.doesNotMatch(flagged, /#cc0000/i);
  const unsupported = katex.renderToString("x \\BROKEN y", opts);
  assert.match(unsupported, /style="color:var\(--math-err\);?"/, "an unsupported command's text takes the same ink: " + unsupported);
  assert.doesNotMatch(unsupported, /#cc0000/i);
  assert.match(katex.renderToString("x^2", opts), /^<span class="katex">/, "a formula that parses is untouched by the option");
});

// ── the sheets' side ──
type RGB = [number, number, number];
const strip = (css: string) => css.replace(/\/\*[\s\S]*?\*\//g, "");
/** The custom properties a token block declares, comments stripped first (theme-parity.test.ts's reading). */
function tokensOf(css: string, opener: string): Map<string, string> {
  const at = css.indexOf(opener);
  assert.ok(at >= 0, opener + " present");
  const out = new Map<string, string>();
  for (const m of strip(css.slice(at, css.indexOf("\n}", at))).matchAll(/(--[a-z0-9-]+):\s*([^;]+);/gi)) out.set(m[1], m[2].trim());
  assert.ok(out.size >= 30, opener + " parsed only " + out.size + " tokens: parser broken?");
  return out;
}
/** A six-digit hex, or a var() read through its hex fallback (the stand-ins are absent in this static read). */
function rgbOf(v: string): RGB | null {
  const hex = v.match(/^#([0-9a-f]{6})$/i);
  if (hex) return [0, 2, 4].map((i) => parseInt(hex[1].slice(i, i + 2), 16)) as RGB;
  const vr = v.match(/^var\([^,]+,\s*(.+)\)$/);
  return vr ? rgbOf(vr[1].trim()) : null;
}
function lum(c: RGB): number {
  const ch = (x: number) => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); };
  return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2]);
}
function contrast(a: RGB, b: RGB): number {
  const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

test("both sheets declare --math-err in both theme blocks, the same values, readable on --bg in each theme, and theme-parity lists the pair", () => {
  const inks: Record<string, string[]> = { dark: [], light: [] };
  for (const sheet of ["styles.css", "feed.css"]) {
    const css = read(sheet);
    for (const [theme, opener] of [["dark", ":root {"], ["light", "body.theme-light {"]] as const) {
      const tokens = tokensOf(css, opener);
      const ink = tokens.get(TOKEN);
      assert.ok(ink, `${sheet}, the ${opener} block, declares no ${TOKEN}: KaTeX's flagged text then inherits the page's ink, readable but not flagged. Declare it beside --err in that block (a literal hex, so theme-parity.test.ts can read it).`);
      const fg = rgbOf(ink!), bg = rgbOf(tokens.get("--bg") || "");
      assert.ok(fg && bg, `${sheet} ${theme}: ${TOKEN} (${ink}) and --bg must be a hex or a var() with a hex fallback`);
      const ratio = contrast(fg!, bg!);
      assert.ok(ratio >= FLOOR, `${sheet} ${theme}: ${TOKEN} ${ink} on --bg reads at ${ratio.toFixed(2)}:1, under ${FLOOR}`);
      assert.notEqual(ink!.toLowerCase(), "#cc0000", `${sheet} ${theme}: KaTeX's default, the 2.8:1 ink this token replaces`);
      inks[theme].push(ink!);
    }
  }
  for (const theme of ["dark", "light"]) assert.equal(inks[theme][0], inks[theme][1], theme + ": the two sheets mirror the token (the feed page loads feed.css alone)");
  assert.match(read("theme-parity.test.ts"), /\["--math-err", "--bg", 4\.5\]/, "the pair is among theme-parity's designated pairs, which hold it in both themes as the sheets change");
});
