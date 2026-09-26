// THE BUTTON VOCABULARY (2026-08-28): one word-button system across the sheets.
//  1. TOKENS — three boxes (--btn-pad-sm/md/lg) + two type sizes (--btn-fs-sm/md), declared in all
//     FOUR self-sufficient blocks (styles.css + feed.css, :root AND body.theme-light — theme-parity
//     enforces the light re-declaration; this pins the VALUES, same in both themes: geometry is not
//     a theme choice).
//  2. HOVER — every migrated action-button family wears pattern A, the ONE action hover documented
//     at feed.css's .fdismiss:hover: accent border + accent text + --accent-wash fill. The legacy
//     white-wash / border-only / opacity-only hovers on these families are retired.
//  3. Destructive stays RED (.fdismiss.fretry, .fdismiss.fq-no, .confirm-btn.danger) and a SELECTED
//     .on keeps the reverse-highlight — accent is never the resting dress.
//  4. PRESS — the families share ONE transition string (color/border/background 0.12s + transform
//     0.08s) and the .stop-btn's :active scale press cue (0.96 for word buttons).
//  5. ACCENT CHROME FOLLOWS THE THEME (2026-09-19): a button whose text is var(--accent) draws its border
//     from the same token in both theme blocks, never from a dark-accent literal. The held-mail card's
//     Approve button (.fdismiss.fq-ok) wrote its border as rgba(156, 210, 255, 0.6), the dark accent at
//     0.6, so in the light theme it computed the clay text inside a blue edge. The census at the end
//     (2026-09-20) holds the rule for every rule of every sheet under ui/webview, not one selector: no
//     rule, and no keyframe taken whole, names an accent token beside a dark-accent literal outside a
//     var() fallback. The same class had two more members when the Approve button was fixed: revealPulse's
//     glow in feed.css and .staged-chip's dashed edge in styles.css, both written through the token now.
//     The census read three named sheets at first and left five unread, three of which paint from the
//     tokens (fresh-3, the same review): it reads the directory now, so a sheet added later joins by
//     construction.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const WEBVIEW = path.resolve(process.cwd(), "..", "ui", "webview");
const read = (f: string) => fs.readFileSync(path.join(WEBVIEW, f), "utf8");
const CHAT = read("styles.css");
const FEED = read("feed.css");
const GEAR = read("gear.css");

const TOKENS: Array<[string, string]> = [
  ["--btn-pad-sm", "1px 8px"], ["--btn-pad-md", "3px 10px"], ["--btn-pad-lg", "5px 13px"],
  ["--btn-fs-sm", "0.72em"], ["--btn-fs-md", "0.82em"],
];

function block(css: string, opener: string): string {
  const at = css.indexOf(opener);
  assert.ok(at >= 0, opener + " present");
  return css.slice(at, css.indexOf("\n}", at));
}

test("the pad/fs tokens exist with the SAME values in all four blocks (both sheets × both themes)", () => {
  for (const [sheet, css] of [["styles.css", CHAT], ["feed.css", FEED]] as const) {
    for (const opener of [":root {", "body.theme-light {"]) {
      const b = block(css, opener);
      for (const [tok, val] of TOKENS) {
        assert.ok(b.includes(`${tok}: ${val};`), `${sheet} ${opener} declares ${tok}: ${val}`);
      }
    }
  }
});

const TRIPLE = "border-color: var\\(--accent\\); color: var\\(--accent\\); background: var\\(--accent-wash\\)";
// gear.css loads standalone (no :root to share) — its triple carries the documented fallbacks
const TRIPLE_FB = "border-color: var\\(--accent, #9cd2ff\\);\\s+color: var\\(--accent, #9cd2ff\\);\\s+background: var\\(--accent-wash, rgba\\(156, 210, 255, 0\\.12\\)\\)";

test("migrated families hover in pattern A — the one accent triple", () => {
  // styles.css
  assert.match(CHAT, new RegExp("\\.ask-btn:not\\(\\.ask-btn-primary\\):hover \\{ " + TRIPLE));
  assert.match(CHAT, new RegExp("\\.bg-stop:hover \\{ " + TRIPLE));
  assert.match(CHAT, new RegExp("\\.notice-act:hover:not\\(:disabled\\) \\{ " + TRIPLE));   // the notice word button (2026-09-08)
  // .fileview-btn hovers identically in BOTH sheets (fileview-parity pins them byte-equal)
  for (const css of [CHAT, FEED]) {
    assert.match(css, new RegExp("\\.fileview-btn:hover \\{ " + TRIPLE));
  }
  // feed.css
  assert.match(FEED, new RegExp("\\.fconfirm-btn:not\\(\\.primary\\):hover \\{ " + TRIPLE));
  assert.match(FEED, /\.fitem\.ask \.fask-bellbtn:hover \{ opacity: 1; color: var\(--accent\); background: var\(--accent-wash\); \}/);
  // gear.css (fallback literals)
  assert.match(GEAR, new RegExp("#rs-keys-btn:hover \\{ " + TRIPLE_FB));
  assert.match(GEAR, new RegExp("\\.ra-openbtn:hover \\{ " + TRIPLE_FB));
  assert.match(GEAR, new RegExp("\\.ra-periods button:hover, \\.ra-group button:hover, \\.ra-metric button:hover \\{ " + TRIPLE_FB));
  // …and the analytics toggles' SELECTED state keeps the VS Code blue, declared AFTER the hover so
  // equal specificity resolves to .on under the cursor too
  const hoverAt = GEAR.indexOf(".ra-periods button:hover");
  const onAt = GEAR.indexOf(".ra-periods button.on,");
  assert.ok(onAt > hoverAt, ".on rule follows the hover rule (source order carries the selected state)");
  assert.match(GEAR, /\.ra-periods button\.on, \.ra-group button\.on, \.ra-metric button\.on \{ background: #0e639c;/);
});

test("migrated families sit on the tokens (where main's T141/T151 rest didn't reclaim them)", () => {
  // the 2026-08-30 merge: main converged .composer-stage-btn / .ask-btn / .fileview-btn onto its
  // OWN T141/T151 rest (transparent ground, --card-border hairline, literal paddings) — main's
  // rest chrome wins there; our transition/:active/hover additions ride on top. The families main
  // didn't touch keep the token metrics.
  assert.match(FEED, /\.ftree-act-btn \{[^}]*font-size: var\(--btn-fs-sm\);[^}]*padding: var\(--btn-pad-sm\);/s);
  assert.match(FEED, /\.fask-secbtn \{[^}]*padding: var\(--btn-pad-sm\);[^}]*font-size: var\(--btn-fs-sm\);/s);
  assert.match(FEED, /\.fconfirm-btn \{[^}]*padding: var\(--btn-pad-lg\);/s);
  assert.match(CHAT, /\.bg-stop \{[^}]*font-size: var\(--btn-fs-sm\); padding: var\(--btn-pad-sm\);/s);
  for (const css of [CHAT, FEED]) {
    assert.match(css, /\.fileview-btn \{[^}]*T151: the one button rest/s);
  }
});

test("destructive stays RED; a SELECTED .on keeps the reverse-highlight", () => {
  assert.match(FEED, /\.fdismiss\.fretry:hover:not\(:disabled\) \{ color: #fff; background: #e5484d; border-color: #e5484d; \}/);
  assert.match(FEED, /\.fdismiss\.fq-no:hover:not\(:disabled\) \{ color: #fff; background: #e5484d; border-color: #e5484d; \}/);
  assert.match(CHAT, /\.confirm-btn\.danger:hover \{ background: rgba\(244, 135, 113, 0\.15\); \}/);
  for (const css of [CHAT, FEED]) {
    assert.match(css, /\.fileview-btn\.on:hover \{ background: var\(--accent\); color: var\(--accent-fg\); border-color: var\(--accent\); \}/);
  }
});

test("ONE transition string + the :active press cue on every touched family", () => {
  const T = "transition: color 0.12s ease, border-color 0.12s ease, background 0.12s ease, transform 0.08s ease;";
  // styles.css: .bg-stop, .composer-stage-btn, .ask-btn, .fileview-btn, .snap-act (the section snapshot's Hide / Show, 2026-09-08) and .notice-act (the notice word button, 2026-09-08)
  assert.equal(CHAT.split(T).length - 1, 6, "styles.css: the six touched families share the one string");
  // feed.css: .fask-secbtn, .ftree-act-btn, .fconfirm-btn, .fdismiss, .fileview-btn
  assert.equal(FEED.split(T).length - 1, 5, "feed.css: the five touched families share the one string");
  // gear.css: #rs-keys-btn, .ra-openbtn, the .ra-* toggles
  assert.equal(GEAR.split(T).length - 1, 3, "gear.css: the three touched families share the one string");
  for (const sel of [".bg-stop", ".composer-stage-btn", ".ask-btn", ".fileview-btn", ".snap-act", ".notice-act"]) {
    assert.ok(CHAT.includes(sel + ":active { transform: scale(0.96); }"), sel + " press cue (styles.css)");
  }
  for (const sel of [".fask-secbtn", ".ftree-act-btn", ".fconfirm-btn", ".fdismiss", ".fileview-btn"]) {
    assert.ok(FEED.includes(sel + ":active { transform: scale(0.96); }"), sel + " press cue (feed.css)");
  }
  assert.ok(GEAR.includes("#rs-keys-btn:active { transform: scale(0.96); }"));
  assert.ok(GEAR.includes(".ra-openbtn:active { transform: scale(0.96); }"));
  assert.ok(GEAR.includes(".ra-periods button:active, .ra-group button:active, .ra-metric button:active { transform: scale(0.96); }"));
});

/** A theme block's tokens, comments stripped first (a declaration after a multi-line comment must still count). */
function tokens(css: string, opener: string): Map<string, string> {
  const out = new Map<string, string>();
  for (const m of block(css, opener).replace(/\/\*[\s\S]*?\*\//g, "").matchAll(/(--[a-z0-9-]+):\s*([^;]+);/gi)) out.set(m[1], m[2].trim());
  return out;
}
type RGBA = [number, number, number, number];
/** A declared colour under one theme's tokens: a hex, an rgb()/rgba(), var(--x) through the block, or the sheet's
 *  accent-tint idiom color-mix(in srgb, <colour> N%, transparent). Anything else fails by name. */
function resolve(v: string, theme: Map<string, string>): RGBA {
  v = v.trim();
  const hex = v.match(/^#([0-9a-f]{6})$/i);
  if (hex) return [0, 2, 4].map((i) => parseInt(hex[1].slice(i, i + 2), 16)).concat(1) as RGBA;
  const ra = v.match(/^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+))?\s*\)$/);
  if (ra) return [+ra[1], +ra[2], +ra[3], ra[4] === undefined ? 1 : parseFloat(ra[4])];
  const vr = v.match(/^var\((--[a-z0-9-]+)\)$/i);
  if (vr) { const t = theme.get(vr[1]); assert.ok(t, vr[1] + " is declared in the theme block"); return resolve(t!, theme); }
  const mix = v.match(/^color-mix\(in srgb, (.+) (\d+)%, transparent\)$/);
  if (mix) { const c = resolve(mix[1], theme); return [c[0], c[1], c[2], c[3] * (+mix[2] / 100)]; }
  assert.fail("not a colour this pin can read: " + v);
}

test("the held-mail Approve button's edge follows the theme's accent: no dark-accent literal, the clay in light", () => {
  const rule = FEED.match(/\n\.fdismiss\.fq-ok \{([^}]*)\}/);
  assert.ok(rule, ".fdismiss.fq-ok rule present");
  const decl = rule![1];
  const color = decl.match(/(?:^|[;\s])color:\s*([^;]+);/), border = decl.match(/border-color:\s*([^;]+);/);
  assert.ok(color && border, "the rule declares color and border-color");
  assert.equal(color![1].trim(), "var(--accent)", "the text is the accent token");
  assert.doesNotMatch(border![1], /156,\s*210,\s*255|#9cd2ff/i, "the border carries no dark-accent literal: " + border![1]);
  for (const [name, opener, accent] of [["dark", ":root {", [156, 210, 255]], ["light", "body.theme-light {", [194, 65, 12]]] as const) {
    const theme = tokens(FEED, opener);
    const text = resolve(color![1], theme), edge = resolve(border![1], theme);
    assert.deepEqual(text.slice(0, 3), accent, name + ": the text resolves to the theme's accent");
    assert.deepEqual(edge.slice(0, 3), accent, name + ": the edge is the same hue as the text");
    assert.equal(edge[3], 0.6, name + ": the edge keeps the 0.6 tint the dark theme always drew");
  }
});

/** THE RULE-SCOPED CENSUS (2026-09-20). A rule that paints from an accent token and from the dark accent written out draws
 *  two hues in the light theme, whichever declarations carry them: .staged-chip put the token on border-left and the literal
 *  on border, so a read scoped to one declaration missed it. The unit is the RULE: a plain rule's whole body; a @keyframes
 *  block taken whole, since one stop's ring and another stop's glow paint on one element; a rule inside an @media block on
 *  its own. Not a literal, by construction: the dark accent inside a var() fallback (the no-sheet value, never the light
 *  theme's); the accent tokens' own definitions (--accent and --accent-wash in a :root, in body.theme-light, or in a surface
 *  that stays dark in both themes, styles.css #romp-lightbox); and a literal at alpha 0, which paints no hue (feed.css
 *  romp-card-pulse fades the outline out to rgba(156, 210, 255, 0)). This pins the WRITTEN form: a text scan cannot tell a
 *  painted mismatch from an inert one, so the written form is what it holds, and a new rule resolves through the token. */
type Rule = { sheet: string; head: string; body: string };
/** Every rule of a sheet, comments stripped first; a block at-rule that wraps rules (@media, @supports, @container, @layer) is
 *  walked into, any other block (a plain rule, @keyframes, @font-face, @property) is one rule. */
function rulesOf(css: string, sheet: string): Rule[] {
  const out: Rule[] = [];
  const walk = (text: string, from: number, to: number) => {
    let i = from;
    while (i < to) {
      const open = text.indexOf("{", i);
      if (open < 0 || open >= to) break;
      const head = text.slice(i, open).trim();
      let depth = 1, j = open + 1;
      while (j < to && depth > 0) { if (text[j] === "{") depth++; else if (text[j] === "}") depth--; j++; }
      if (/^@(media|supports|container|layer)\b/.test(head)) walk(text, open + 1, j - 1);
      else out.push({ sheet, head, body: text.slice(open + 1, j - 1) });
      i = j;
    }
  };
  const text = css.replace(/\/\*[\s\S]*?\*\//g, "");
  walk(text, 0, text.length);
  return out;
}
/** The dark accent in any spelling: the 156, 210, 255 triple in either rgb() syntax, or its hex, each with an optional alpha. */
const DARK_ACCENT = [
  /rgba?\(\s*156\s*,\s*210\s*,\s*255\s*(?:,\s*([\d.]+)(%?))?\s*\)/gi,
  /rgba?\(\s*156\s+210\s+255\s*(?:\/\s*([\d.]+)(%?))?\s*\)/gi,
  /#9cd2ff([0-9a-f]{2})?(?![0-9a-z-])/gi,
];
function darkAccentLiterals(body: string): Array<{ text: string; alpha: number }> {
  const out: Array<{ text: string; alpha: number }> = [];
  for (const re of DARK_ACCENT) {
    for (const m of body.matchAll(re)) {
      let alpha = 1;
      if (re === DARK_ACCENT[2]) { if (m[1]) alpha = parseInt(m[1], 16) / 255; }
      else if (m[1] !== undefined) alpha = parseFloat(m[1]) / (m[2] === "%" ? 100 : 1);
      out.push({ text: m[0], alpha });
    }
  }
  return out;
}
/** var(--x, <fallback>) read as var(--x): the fallback paints only where no sheet defines the token, so never under a theme.
 *  Two levels of parentheses inside the fallback (a color-mix carrying a var()). */
const withoutFallbacks = (s: string) => s.replace(/var\((--[a-z0-9-]+)\s*,\s*(?:[^()]|\((?:[^()]|\([^()]*\))*\))*\)/gi, "var($1)");
/** The accent's tokens: the hue, the text on it and the wash, every one re-inked by the light theme. */
const ACCENT_TOKEN = /var\(--accent(?:-fg|-wash)?\)/;
/** The rules of one sheet that name an accent token beside a painted dark-accent literal, each as "<sheet> <head>: <literals>". */
function mixedAccentRules(css: string, sheet: string): string[] {
  const out: string[] = [];
  for (const r of rulesOf(css, sheet)) {
    const body = withoutFallbacks(r.body).replace(/--accent(?:-wash)?\s*:\s*[^;]+;/g, "");
    if (!ACCENT_TOKEN.test(body)) continue;
    const painted = darkAccentLiterals(body).filter((l) => l.alpha > 0).map((l) => l.text);
    if (painted.length) out.push(`${sheet} ${r.head}: ${painted.join(", ")}`);
  }
  return out;
}

test("the census reader: the rule is the unit, a keyframe is one rule, and a fallback, an alpha-0 stop or the token's own definition is no literal", () => {
  // a synthetic sheet in the sheets' own shapes: the two members' forms, the exemptions, and the spellings
  const css = [
    ":root { --accent: #9cd2ff; --accent-wash: rgba(156, 210, 255, 0.12); --kind: var(--accent); }",
    "/* a comment naming rgba(156, 210, 255, 0.6) beside var(--accent) */",
    ".two-decls { border: 1px dashed rgba(156, 210, 255, 0.45);\n  border-left: 2px solid var(--accent); }",
    "@keyframes two-stops {\n  0% { outline-color: var(--accent); }\n  100% { outline-color: #9CD2FF; }\n}",
    "@keyframes fades-out {\n  0% { outline-color: var(--accent, #9cd2ff); }\n  100% { outline-color: rgba(156, 210, 255, 0); }\n}",
    ".fallback { outline: 2px solid var(--accent, #9cd2ff); background: var(--accent-wash, rgba(156, 210, 255, 0.12)); }",
    ".nested-fallback { border-color: var(--edge, color-mix(in srgb, var(--accent) 60%, transparent)); color: #9cd2ff00; }",
    "@media (prefers-reduced-motion: reduce) {\n  .nested { color: var(--accent-fg); background: rgb(156 210 255 / 50%); }\n}",
    ".literal-alone { color: #9cd2ff; }",
    ".wash { background: var(--accent-wash); border: 1px solid rgb(156 210 255 / 40%); }",
    ".fixed { color: var(--accent); border-color: color-mix(in srgb, var(--accent) 60%, transparent); }",
  ].join("\n");
  assert.deepEqual(mixedAccentRules(css, "t"), [
    "t .two-decls: rgba(156, 210, 255, 0.45)",
    "t @keyframes two-stops: #9CD2FF",
    "t .nested: rgb(156 210 255 / 50%)",
    "t .wash: rgb(156 210 255 / 40%)",
  ]);
  assert.deepEqual(rulesOf(css, "t").map((r) => r.head).filter((h) => h.startsWith("@")), ["@keyframes two-stops", "@keyframes fades-out"], "a keyframe is one rule and an @media wrap is walked into");
});

// The census's population: every sheet under ui/webview, by readdir, so a sheet added later joins by construction; the
// three the census began on (styles.css, feed.css, gear.css) left five unread, three of which (the sessions pane's, the
// strip's and the waiting pane's) paint from the tokens. CSS sheets only: accent chrome inlined in a Python or JS string
// (kernel/kernel.py's served pages carry such rules) is outside this census.
const SHEETS = fs.readdirSync(WEBVIEW).filter((f) => f.endsWith(".css")).sort();
const ANCHORS = ["styles.css", "feed.css", "gear.css"];

test("no rule of any sheet under ui/webview names an accent token beside the dark accent written out (two hues on one element in the light theme)", () => {
  // the floor, so a resolve at the wrong directory or a filter that drops sheets reds instead of passing over nothing:
  // the three sheets the census began on are among those read, and at least the eight that stood here when the floor
  // was set (lower it only for a sheet retired on purpose)
  for (const a of ANCHORS) assert.ok(SHEETS.includes(a), a + " is among the sheets read: " + SHEETS.join(", "));
  assert.ok(SHEETS.length >= 8, "eight sheets stood under ui/webview when this floor was set; found " + SHEETS.length + ": " + SHEETS.join(", "));
  const found = SHEETS.flatMap((sheet) => mixedAccentRules(read(sheet), sheet));
  assert.deepEqual(found, [], "rules mixing an accent token with the dark accent written out:\n  " + found.join("\n  "));
  // the reader saw the sheets: the Approve button, the two rules the census widened onto and the alpha-0 keyframe are rules it read
  const heads = new Set([...rulesOf(FEED, "feed.css"), ...rulesOf(CHAT, "styles.css")].map((r) => r.head));
  for (const head of [".fdismiss.fq-ok", "@keyframes revealPulse", ".staged-chip", "@keyframes romp-card-pulse", ":root", "body.theme-light"]) {
    assert.ok(heads.has(head), head + " is a rule the census read");
  }
});
