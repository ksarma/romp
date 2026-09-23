// The light theme's two structural guarantees (2026-08-28), so it cannot rot as features land
// dark-first:
//  1. KEY PARITY — body.theme-light re-declares EVERY custom property the sheet's :root defines
//     (a new token added to :root without a light value fails here, in the same commit).
//  2. CONTRAST — the designated (fg, bg) token pairs clear WCAG in BOTH themes; a feature that
//     adds a pair adds it to PAIRS.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { cssRules } from "./css-rules.mjs";   // the outbound dress's painted pin (the last test): the opacities the sheet declares, read as parsed rules with their at-rules

const read = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");

function block(css: string, opener: string): string {
  const at = css.indexOf(opener);
  assert.ok(at >= 0, opener + " present");
  // COMMENT-BLIND parsing swallowed tokens whose declarations follow a multi-line comment and
  // corrupted values that carry one inline (PR #763 item 6: --accent/--card-border/--err skipped
  // in silence and the suite stayed green) — strip comments FIRST, always
  return css.slice(at, css.indexOf("\n}", at)).replace(/\/\*[\s\S]*?\*\//g, "");
}
function props(blockText: string): Map<string, string> {
  const out = new Map<string, string>();
  for (const m of blockText.matchAll(/(--[a-z0-9-]+):\s*([^;]+);/gi)) out.set(m[1], m[2].trim());
  return out;
}

// resolve a declared value to solid RGB over a background: hex directly; var(x, fallback) via the
// fallback (the stand-ins are absent in this static read); rgba composited over the bg
function rgbOf(v: string, bg: [number, number, number]): [number, number, number] | null {
  const hex = v.match(/^#([0-9a-f]{6})$/i);
  if (hex) { const h = hex[1]; return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)) as [number, number, number]; }
  const vr = v.match(/^var\([^,]+,\s*(.+)\)$/);
  if (vr) return rgbOf(vr[1].trim(), bg);
  const ra = v.match(/^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+))?\s*\)$/);
  if (ra) {
    const a = ra[4] === undefined ? 1 : parseFloat(ra[4]);
    return [1, 2, 3].map((i) => Math.round(parseInt(ra[i], 10) * a + bg[i - 1] * (1 - a))) as [number, number, number];
  }
  return null;   // fonts, shadows, sizes — not a color
}
function lum(rgb: [number, number, number]): number {
  const ch = (c: number) => { c /= 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
  return 0.2126 * ch(rgb[0]) + 0.7152 * ch(rgb[1]) + 0.0722 * ch(rgb[2]);
}
/** OKLCH (L 0..1, C, hue in degrees) to sRGB channels 0..255, clamped to the gamut: the tinted ground of an incoming card. */
function oklchToRgb(L: number, C: number, hDeg: number): [number, number, number] {
  const h = (hDeg * Math.PI) / 180, a = C * Math.cos(h), b = C * Math.sin(h);
  const l_ = L + 0.3963377774 * a + 0.2158037573 * b, m_ = L - 0.1055613458 * a - 0.0638541728 * b, s_ = L - 0.0894841775 * a - 1.2914855480 * b;
  const l = l_ ** 3, m = m_ ** 3, s = s_ ** 3;
  const lin = [4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s, -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
               -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s];
  return lin.map((c) => { c = Math.max(0, Math.min(1, c)); const v = c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055; return Math.round(v * 255); }) as [number, number, number];
}

function contrast(a: [number, number, number], b: [number, number, number]): number {
  const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

// (fg token, ground token, floor) — 4.5 for reading text, 3 for large/secondary chrome
const PAIRS: Array<[string, string, number]> = [
  ["--fg", "--bg", 4.5],
  ["--dim", "--bg", 4.5],
  ["--fg", "--surface-raised", 4.5],
  ["--accent", "--bg", 3],
  ["--cmt-hl-outline", "--bg", 3],   // the comment notch (the rail tick's fill): a LINE, so it must read against the page (T310)
  ["--st-awaiting-bg", "--bg", 3],   // the unread passage's dashed box and ring, and the tick's halo (2026-09-12): a line in the needs-you red
  ["--accent-fg", "--accent", 3],
  ["--warn", "--bg", 3],
  ["--err", "--bg", 3],
  ["--green", "--bg", 3],
  ["--code-fg", "--bg", 4.5],
  ["--text-muted", "--surface-raised", 4.5],
  ["--postal-coordinate", "--bg", 4.5],   // the postal kind word's three-step ramp (T320): text, so 4.5:1 on the page in both themes...
  ["--postal-delegate", "--bg", 4.5],
  ["--postal-question", "--bg", 4.5],
  ["--postal-coordinate", "--box-bg", 4.5],   // ...and on a BOXED card (an incoming message paints --box-bg over --bg), where the
  ["--postal-delegate", "--box-bg", 4.5],     // review found the light coordination step at 4.33:1 (2026-09-10)
  ["--postal-question", "--box-bg", 4.5],
  ["--st-working-fg", "--st-working-bg", 3],
  ["--st-ready-fg", "--st-ready-bg", 3],
  ["--st-blocked-fg", "--st-blocked-bg", 3],
  ["--st-retrying-fg", "--st-retrying-bg", 3],       // 2026-09-08: the retrying amber tokenised (#e67e22/#2a1500 dark, #9C4A0C/#fff light)
  ["--st-ask-fg", "--st-ask-bg", 3],                 // 2026-09-13: the ask yellow (#f5d33f/#332600 dark, #7a6400/#fff light)
  ["--st-ask-bg", "--bg", 3],                        // …and the ask RING is a line on the page (the tab's dashed outline, the folded header's pip)
  ["--outbound-line", "--bg", 3],                    // the viewer's outbound dress (the web control's dashed border at rest, the under-floor web picture's dashed
                                                     // outline): a LINE, the only sign of the outbound state on touch, so 3:1 on the page in both themes, a property
                                                     // pin by ratio (the file review's round 13, ui-1 with extra6-1: the 10 percent hairline it wore read 1.35:1 dark
                                                     // and 1.25:1 light)
  // (--st-compacting-fg on --st-compacting-bg is deliberately NOT paired: the dark teal + white pairing predates
  // this file and sits at 2.49:1, and decision 3 of the 2026-09-08 notice audit keeps dark byte-identical; the
  // light re-ink — #0F766E, 4.30:1 on the card, white on it 5.47:1 — is pinned by value in notice-vocab.test.ts)
  ["--link", "--bg", 4.5],          // hyperlink ink (2026-09-02: the light theme's first link ink sat on --err)
  ["--hl-fg", "--bg", 4.5],         // the hljs syntax palette (tokenized 2026-09-02; was dark-only raw hex)
  ["--hl-kw", "--bg", 4.5],
  ["--hl-str", "--bg", 4.5],
  ["--hl-num", "--bg", 4.5],
  ["--hl-cmt", "--bg", 3],          // comments are deliberately quiet
  ["--hl-cmt", "--box-bg", 4.5],    // ...but readable on the code block they sit in (the fence's fill is --box-bg over --bg)
  ["--hl-title", "--bg", 4.5],
  ["--hl-meta", "--bg", 4.5],
  ["--hl-attr", "--bg", 4.5],
  ["--math-err", "--bg", 4.5],      // KaTeX's flagged text (math.ts MATH_ERROR_COLOR; Slice 4 of plans/markdown-viewer.md, review round 1)
  ["--callout-tip", "--bg", 3],     // a callout's rail, the type's one carrier (Slice 4, review round 5: the status fills the tip and
  ["--callout-important", "--bg", 3],   // important rails read before were 2.27:1 and 2.09:1 on the light page)
];

test("styles.css: the provisional wash the kind pairs are computed against is the one the sheet paints", () => {
  const css = read("styles.css");
  const SHARED = ".queued-bubble, .notice.queued-bubble, .notice.notice-slim.queued-bubble,";   // the list runs on to the echo of a slash command (T403)
  const bubble = css.slice(css.indexOf(SHARED), css.indexOf("\n}\n", css.indexOf(SHARED)));
  assert.ok(css.indexOf(SHARED) > 0, "the shared provisional rule is where the slice looks");
  assert.match(bubble, /background: color-mix\(in srgb, var\(--you\) 8\.5%, transparent\);/);
  assert.doesNotMatch(bubble, /opacity:/, "the fade is in the colours: no element opacity dims the words on the card");
});

for (const sheet of ["styles.css", "feed.css"]) {
  const css = read(sheet);
  const dark = props(block(css, ":root {"));
  const light = props(block(css, "body.theme-light {"));

  test(sheet + ": key parity — the light block re-declares every :root token", () => {
    const missing = [...dark.keys()].filter((k) => !light.has(k));
    assert.deepEqual(missing, [], sheet + " light block is missing tokens");
    // a silent parse regression must fail LOUDLY (PR #763 item 6): both blocks hold dozens of
    // tokens — a parser that suddenly sees fewer is broken, not a tidier sheet
    assert.ok(dark.size >= 30, sheet + " parsed only " + dark.size + " dark tokens — parser broken?");
    assert.ok(light.size >= dark.size, sheet + " parsed fewer light tokens than dark");
  });

  test(sheet + ": the designated pairs clear WCAG in BOTH themes — and the evaluated COUNT is pinned", () => {
    for (const [name, theme] of [["dark", dark], ["light", light]] as const) {
      const bgv = theme.get("--bg"); assert.ok(bgv, name + " --bg");
      const page = rgbOf(bgv!, [30, 30, 30])!;
      let evaluated = 0;
      for (const [fgTok, bgTok, floor] of PAIRS) {
        const f = theme.get(fgTok), g = theme.get(bgTok);
        if (!f || !g) continue;   // feed.css :root deliberately holds a SUBSET of tokens
        const ground = rgbOf(g, page); const fore = ground && rgbOf(f, ground);
        if (!ground || !fore) continue;
        evaluated++;
        assert.ok(contrast(fore, ground) >= floor,
          `${sheet} ${name}: ${fgTok} on ${bgTok} = ${contrast(fore, ground).toFixed(2)} < ${floor}`);
      }
      // a skip must be loud (PR #763 item 6): pin how many pairs actually ran per sheet/theme —
      // grow these numbers when PAIRS grows, never let them silently shrink
      const expected = sheet === "styles.css" ? PAIRS.length : 26;   // feed's :root holds a deliberate subset (no --box-bg in its dark block, so the code-block pair runs in styles.css and in feed's light block) plus the retrying pair (#1107), the two ask pairs (2026-09-14: the settings' ring demo reads the token there) and the outbound line (2026-09-23: the viewer mounts in the feed); the number is what a run evaluates against the resolved feed.css (26 in both themes, 2026-09-23)
      // T337: the postal kind words also sit on the PROVISIONAL card (a sent card not yet landed wears the pending
      // bubble's dress: an 8.5% wash of --you over the page, styles.css .queued-bubble, no element opacity since the
      // fade moved into the dress's colours), the darkest ground they meet; each reads at 4.5:1 there too
      if (sheet === "styles.css") {
        const you = rgbOf(theme.get("--you")!, page)!;
        const wash = [0, 1, 2].map((i) => Math.round(you[i] * 0.085 + page[i] * 0.915)) as [number, number, number];
        for (const tok of ["--postal-coordinate", "--postal-delegate", "--postal-question"]) {
          const fore = rgbOf(theme.get(tok)!, wash)!;
          assert.ok(contrast(fore, wash) >= 4.5, `${sheet} ${name}: ${tok} on the provisional wash = ${contrast(fore, wash).toFixed(2)} < 4.5`);
        }
      }
      // T337c: the INCOMING card no longer wears --box-bg but the peer's hue at the ground's lightness (styles.css: an oklch
      // relative colour from the rail, the tokens --postal-wash-l and --postal-wash-c), a different ground for every peer;
      // each kind word reads at 4.5:1 there for EVERY hue (the sent boxed card still wears --box-bg: those pairs stand)
      if (sheet === "styles.css") {
        const L = parseFloat(theme.get("--postal-wash-l")!), C = parseFloat(theme.get("--postal-wash-c")!);
        assert.ok(L > 0 && L < 1 && C > 0, `${sheet} ${name}: the wash tokens parse (${L}, ${C})`);
        for (const tok of ["--postal-coordinate", "--postal-delegate", "--postal-question"]) {
          let worst = Infinity, worstHue = -1;
          for (let h = 0; h < 360; h++) {
            const ground = oklchToRgb(L, C, h);
            const fore = rgbOf(theme.get(tok)!, ground)!;
            const c = contrast(fore, ground);
            if (c < worst) { worst = c; worstHue = h; }
          }
          assert.ok(worst >= 4.5, `${sheet} ${name}: ${tok} on the tinted ground = ${worst.toFixed(2)} at hue ${worstHue} < 4.5`);
        }
      }
      assert.ok(evaluated >= expected,
        `${sheet} ${name}: only ${evaluated}/${expected} contrast pairs evaluated — silent skip`);
    }
  });
}

// THE RING HUES, ALL PAIRS PER THEME (the rings-as-widgets change, 2026-09-14): the three dashed rings a tab can wear
// (the two reds, the yellow, the amber) are told apart by colour alone — same shape, same dash, on different tabs — so
// every pair of ring hues must stay apart for full-colour readers (OKLab distance x100 at least 15) AND under the two
// red-green deficiencies (at least 8 after the Machado, Oliveira and Fernandes 2009 simulation at severity 1.0), the
// floors the dataviz palette validator applies to categorical marks; the yellow ring against the two DOTS it can sit
// beside (the working gold and the await-green, a 7px disc inside a 2px outline: shape and position tell them apart
// too) needs the deficiency floor only. The light palette's convention (the same hue darkened to lightness 0.5 for 3:1
// on cream) puts a second yellow on the working gold, and hue alone does not survive a red-green deficiency, so the
// light ring yellow leaves by LIGHTNESS: #504100 (hue 94, lightness 0.38) is the only axis left that clears every
// pair; a lighter olive collides with the amber under a deficiency (the branch's #7a6400: 0.1 against #9C4A0C).
// The dark lemon stands as the author left it: 9.5 from the working gold to full-colour readers (a known pair, the
// dot and the ring differ in shape and position), every other pair well over the floors. The ring also reads at 3:1
// on the hovered tab and the selected tab's fill, the two washes a ring can sit on besides the page.
function oklab(rgb: [number, number, number]): [number, number, number] {
  const lin = rgb.map((c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }) as [number, number, number];
  return oklabFromLin(lin);
}
function oklabFromLin([r, g, b]: [number, number, number]): [number, number, number] {
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b), m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b), s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  return [0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s, 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s, 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s];
}
// Machado, Oliveira and Fernandes (2009), severity 1.0, on linear RGB
const CVD: Record<string, number[][]> = {
  protan: [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
  deutan: [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
};
function simulate(rgb: [number, number, number], kind: string): [number, number, number] {
  const lin = rgb.map((c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); });
  const M = CVD[kind];
  return [0, 1, 2].map((i) => Math.max(0, Math.min(1, M[i][0] * lin[0] + M[i][1] * lin[1] + M[i][2] * lin[2]))) as [number, number, number];
}
function deltaE(a: [number, number, number], b: [number, number, number], kind?: string): number {
  const x = kind ? oklabFromLin(simulate(a, kind)) : oklab(a), y = kind ? oklabFromLin(simulate(b, kind)) : oklab(b);
  return 100 * Math.hypot(x[0] - y[0], x[1] - y[1], x[2] - y[2]);
}
const cvdWorst = (a: [number, number, number], b: [number, number, number]) => Math.min(deltaE(a, b, "protan"), deltaE(a, b, "deutan"));

test("the ring hues stay apart in BOTH themes, every pair: rings against rings for full-colour readers and under red-green deficiencies, the yellow ring against the dots under the deficiencies; the yellow reads on every tab ground", () => {
  const css = read("styles.css");
  for (const [name, theme] of [["dark", props(block(css, ":root {"))], ["light", props(block(css, "body.theme-light {"))]] as const) {
    const page = rgbOf(theme.get("--bg")!, [30, 30, 30])!;
    const tok = (t: string) => rgbOf(theme.get(t)!, page)!;
    const rings: Record<string, [number, number, number]> = { awaiting: tok("--st-awaiting-bg"), blocked: tok("--st-blocked-bg"), ask: tok("--st-ask-bg"), retrying: tok("--st-retrying-bg") };
    const dots: Record<string, [number, number, number]> = { working: tok("--st-working-bg"), awaitbg: tok("--st-awaitbg-bg") };
    for (const other of ["awaiting", "blocked", "retrying"]) {
      const n = deltaE(rings.ask, rings[other]), c = cvdWorst(rings.ask, rings[other]);
      assert.ok(n >= 15, `${name}: the yellow ring against the ${other} ring reads ${n.toFixed(1)} to full-colour readers (floor 15)`);
      assert.ok(c >= 8, `${name}: the yellow ring against the ${other} ring reads ${c.toFixed(1)} under a red-green deficiency (floor 8)`);
    }
    for (const dot of Object.keys(dots)) {
      const c = cvdWorst(rings.ask, dots[dot]);
      assert.ok(c >= 8, `${name}: the yellow ring against the ${dot} dot reads ${c.toFixed(1)} under a red-green deficiency (floor 8)`);
    }
    // the light theme clears the full-colour floor against the dots too; the dark lemon's known 9.5 against the gold is pinned so it cannot slide
    const gold = deltaE(rings.ask, dots.working);
    assert.ok(gold >= (name === "light" ? 15 : 9), `${name}: the yellow ring against the working gold reads ${gold.toFixed(1)}`);
    // the grounds a ring sits on: the page (PAIRS above), the hovered tab (a 6% white wash) and the selected tab's fill
    const hover = [0, 1, 2].map((i) => Math.round(255 * 0.06 + page[i] * 0.94)) as [number, number, number];
    const active = rgbOf(theme.get("--tab-active-bg")!, page)!;
    for (const [g, ground] of [["hovered tab", hover], ["selected tab", active]] as const) {
      assert.ok(contrast(rings.ask, ground) >= 3, `${name}: the yellow ring on the ${g} = ${contrast(rings.ask, ground).toFixed(2)} < 3`);
    }
  }
  // the light value itself, so a re-ink is a deliberate change here and in feed.css (tab-rings.test.ts pins the two sheets equal)
  assert.match(block(css, "body.theme-light {"), /--st-ask-bg: #504100; --st-ask-fg: #ffffff;/);
});

// THE OUTBOUND DRESS, PAINTED (the painted-contrast ask of 2026-09-23). The pair in PAIRS reads --outbound-line over --bg as if
// nothing stood between them; the dress is painted through element opacities, the web control's own at rest and a dead link's
// (a.fv-dead) around a dress inside it, and the control paints its own background, var(--bg), under its line, so at an opacity under
// 1 the picture beneath the control shows through its line and its ground alike. Each state from which a gesture opens the outbound
// tab (a tap, a click, Enter on the control; an href-less dead link owns no click, file-view.ts FIGURE_LINK_SET, so the states inside
// one open the tab too) is composed here from the opacities the sheet DECLARES for the rules that reach the dress, and its line must
// clear 3:1 over the ground it paints on: the control's own background, composed the same way, for the worst picture beneath it (every
// grey and the eight corners of the colour cube), or the page for the mark, whose 1px offset shows the page between its dashes. The
// states: the web control at rest, alone and inside a dead link; the control revealed by the pointer over its picture or by a keyboard
// focus inside a dead link (the focus is composed here alone: in the browser Chromium's focus ring covers the border row); the accent
// border with the pointer on the control inside a dead link, against the hover wash; the mark, alone and inside a dead link. Every
// failing state is collected and asserted once, so a red names them all. Red at 61d69cba1, where the web control rested at 0.8 and a
// dead link's 0.7 dimmed the dress inside it. The read is a model with a stated bound: a rule reaches the dress here when its selector
// list carries one of the spellings named below (split at top-level commas), under the at-rules named; a rule reaching the dress under
// another spelling is outside this read, and the executed read is file-figure-open-browser.test.ts's paintedRatio, pixels off the real
// paint under touch emulation, on a touchscreen laptop and on a fine pointer.
function selectorList(sel: string): string[] {
  const out: string[] = []; let depth = 0, from = 0;
  for (let i = 0; i < sel.length; i++) { const c = sel[i]; if (c === "(") depth++; else if (c === ")") depth--; else if (c === "," && depth === 0) { out.push(sel.slice(from, i).trim()); from = i + 1; } }
  out.push(sel.slice(from).trim());
  return out;
}
/** The opacity the LAST rule reaching `spellings` under a chain `chainOk` accepts declares (sheet order: the spellings a caller
 *  names share one specificity), or null when no such rule declares one. */
function declaredOpacity(css: string, spellings: string[], chainOk: (chain: string[]) => boolean): number | null {
  let v: number | null = null;
  for (const r of cssRules(css)) {
    if (!chainOk(r.chain) || !selectorList(r.selector).some((s) => spellings.includes(s))) continue;
    const m = /(?:^|;\s*)opacity:\s*([\d.]+)\s*(?:;|$)/.exec(r.body.trim());
    if (m) v = parseFloat(m[1]);
  }
  return v;
}
const AT_REST = (chain: string[]) => chain.length === 1 && /\(hover: none\)/.test(chain[0]) && /\(any-pointer: coarse\)/.test(chain[0]);
const SCREEN = (chain: string[]) => chain.length === 1 && chain[0] === "@media screen";
const TOP = (chain: string[]) => chain.length === 0;
type RGBf = [number, number, number];
const over = (a: RGBf, b: RGBf, t: number): RGBf => [0, 1, 2].map((i) => a[i] * t + b[i] * (1 - t)) as RGBf;
const PICTURES: RGBf[] = [...Array.from({ length: 256 }, (_, g) => [g, g, g] as RGBf), ...[0, 1, 2, 3, 4, 5, 6, 7].map((k) => [k & 1 ? 255 : 0, k & 2 ? 255 : 0, k & 4 ? 255 : 0] as RGBf)];
/** The control's line `line` over its own ground `ground` (var(--bg), or the hover wash over it), the control at opacity `o` over a
 *  picture, the lot inside an anchor at opacity `a` over the page `bg`: the worst ratio over PICTURES (at o = 1 the picture drops out). */
function controlPainted(line: RGBf, ground: RGBf, bg: RGBf, o: number, a: number): number {
  let worst = Infinity;
  for (const p of (o === 1 ? [bg] : PICTURES)) worst = Math.min(worst, contrast(over(over(line, p, o), bg, a), over(over(ground, p, o), bg, a)));
  return worst;
}
const markPainted = (tok: RGBf, bg: RGBf, a: number): number => contrast(over(tok, bg, a), bg);
type Theme = { bg: RGBf; tok: RGBf; accent: RGBf; wash: RGBf };   // wash: --accent-wash already over bg, the control's hover background
/** Every state from which a gesture opens the outbound tab, painted over the theme's ground, from the sheet's declared opacities; each
 *  with whether its line is the dress's token (the VS Code bound's states) or the family's accent under the pointer. */
function dressStates(css: string, t: Theme): Array<[string, number, "token" | "accent"]> {
  const rest = declaredOpacity(css, [".fileview-md .fv-figopen", ".fileview-md .fv-figopen-web"], AT_REST);
  const reveal = declaredOpacity(css, [".fileview-md .fv-figopen:hover", ".fileview-md :hover + .fv-figopen", ".fileview-md .fv-figopen:focus-visible"], SCREEN);
  // the dead link around a dress: the rule keyed on the dress it holds outranks the plain dead rule (a :has() adds its argument's weight)
  const deadHolding = declaredOpacity(css, [".fileview-md a.fv-dead:has(.fv-figopen-web)", ".fileview-md a.fv-dead:has(img[data-fv-figweb])"], SCREEN);
  const dead = deadHolding !== null ? deadHolding : declaredOpacity(css, [".fileview-md a.fv-dead"], TOP);
  assert.ok(rest !== null && reveal !== null && dead !== null, "the three opacities are read off the sheet (rest " + rest + ", reveal " + reveal + ", dead link " + dead + "): a read that finds none is broken, not clean");
  return [
    ["the web control at rest (touch, or a coarse pointer beside a hovering one) at " + rest, controlPainted(t.tok, t.bg, t.bg, rest!, 1), "token"],
    ["the web control at rest inside a dead link, " + rest + " x " + dead, controlPainted(t.tok, t.bg, t.bg, rest!, dead!), "token"],
    ["the web control revealed by the pointer over its picture or by a keyboard focus inside a dead link, " + reveal + " x " + dead, controlPainted(t.tok, t.bg, t.bg, reveal!, dead!), "token"],
    ["the mark on a picture under the floor (at rest, or on hover)", markPainted(t.tok, t.bg, 1), "token"],
    ["the mark inside a dead link, at " + dead, markPainted(t.tok, t.bg, dead!), "token"],
    ["the accent border with the pointer on the control inside a dead link, against the hover wash, " + reveal + " x " + dead, controlPainted(t.accent, t.wash, t.bg, reveal!, dead!), "accent"],
  ];
}
test("the outbound dress PAINTED: every state from which a gesture opens the outbound tab, composed from the opacities the sheet declares (the web control's own at rest, a dead link's around the dress) over the ground it paints on (the control's own background over the worst picture, the page for the mark), clears 3:1 in both themes of both sheets, the accent border under the pointer inside a dead link among them; and in the dark theme, whose ground follows the VS Code editor, the token's states clear on every neutral editor ground up to #404040 and none past it, and from #efefef on a light one (the painted-contrast ask of 2026-09-23)", (t) => {
  const fails: string[] = [];
  for (const sheet of ["styles.css", "feed.css"]) {
    const css = read(sheet);
    const themeOf = (vars: Map<string, string>, bg: RGBf): Theme => ({ bg, tok: rgbOf(vars.get("--outbound-line")!, bg)!, accent: rgbOf(vars.get("--accent")!, bg)!, wash: rgbOf(vars.get("--accent-wash")!, bg)! });   // the wash composited over the ground (rgbOf), the hover background var(--bg) under the gradient
    for (const [name, blk] of [["dark", props(block(css, ":root {"))], ["light", props(block(css, "body.theme-light {"))]] as const) {
      const bg = rgbOf(blk.get("--bg")!, [30, 30, 30])!;
      for (const [state, ratio] of dressStates(css, themeOf(blk, bg))) t.diagnostic(`${sheet} ${name}: ${state} paints ${ratio.toFixed(3)}:1`);
      for (const [state, ratio] of dressStates(css, themeOf(blk, bg))) if (ratio < 3) fails.push(`${sheet} ${name}: ${state} paints ${ratio.toFixed(3)}:1, under the 3:1 floor for the only sign of the outbound state`);
    }
    // the VS Code bound, restated from the painted value: the dark --bg is the editor's background (var(--vscode-editor-background,
    // ...)), the light block's a literal; the token's states clear 3:1 on every neutral editor ground from the fallback up to #404040,
    // and at #414141 even their best (the token at full over the ground) falls under, so the stated bound is exact; on a light editor
    // ground from #efefef up, and not at #eeeeee. The accent border is the button family's hover colour, not the dress's token, and is
    // held above on each theme's own ground. The leg reads the same bound by pixels (file-figure-open-browser.test.ts).
    const dark = props(block(css, ":root {"));
    assert.match(dark.get("--bg")!, /^var\(--vscode-editor-background, #1e1e1e\)$/, sheet + ": the dark ground follows the editor");
    const onGrey = (g: number) => dressStates(css, themeOf(dark, [g, g, g])).filter(([, , k]) => k === "token");
    const hex = (g: number) => "#" + g.toString(16).padStart(2, "0").repeat(3);
    for (const g of [...Array.from({ length: 0x40 - 0x1e + 1 }, (_, i) => 0x1e + i), ...Array.from({ length: 0xff - 0xef + 1 }, (_, i) => 0xef + i)]) {
      const [state, worst] = onGrey(g).reduce((w, s) => (s[1] < w[1] ? s : w));
      if (worst < 3) fails.push(`${sheet}: on a VS Code editor ground ${hex(g)} the dress paints ${worst.toFixed(3)}:1 at its worst state (${state}), under the stated bound of #404040 (dark) or #efefef (light)`);
    }
    for (const g of [0x40, 0xef]) t.diagnostic(`${sheet}: on a VS Code editor ground ${hex(g)} the token's worst state paints ${Math.min(...onGrey(g).map(([, r]) => r)).toFixed(3)}:1`);
    for (const g of [0x41, 0xee]) {
      const best = Math.max(...onGrey(g).map(([, r]) => r));
      t.diagnostic(`${sheet}: at ${hex(g)} the token's best state paints ${best.toFixed(3)}:1`);
      if (best >= 3) fails.push(`${sheet}: at ${hex(g)} the dress's best state paints ${best.toFixed(3)}:1, past the stated bound, where it should fall under 3:1 (the bound #404040 and the light one #efefef are stated exact)`);
    }
  }
  assert.deepEqual(fails, [], "every state a gesture opens the outbound tab from paints the dress at 3:1, and the VS Code bound is exact:\n" + fails.join("\n"));
});
