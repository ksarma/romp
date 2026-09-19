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
//     0.6, so in the light theme it computed the clay text inside a blue edge.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const read = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
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
