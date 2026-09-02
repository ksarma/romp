// T226 (the user 2026-09-02, screenshot: in the light theme the settings' Theme select opened a
// near-black card with dark-on-dark options — the way back to dark was unreadable). The menu
// vocabulary (CLAUDE.md "Menus and dropdowns wear ONE vocabulary") had been pinned as LITERAL hex
// in every inline menu string (the settings pickers, the tag menu), so the light block could never
// reach it. The skin is TOKENS now — --menu-bg / --menu-fg / --menu-border / --menu-hover beside the
// existing --radius-menu / --shadow-menu / --check-bg — defined in both theme blocks of both
// self-sufficient sheets; dark resolves byte-for-byte to the literals the rule always named, the
// light block re-skins in its own palette, and inline strings carry the dark literal only as the
// var() FALLBACK (a file:// harness / a foreign host loads no sheet). The ✓ mark is themed too (the
// manager's ruling): dark keeps #1EA1EB, light wears the clay the timeline's palette already drew.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const ui = (...p: string[]) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", ...p), "utf8");
const CHAT = ui("webview", "styles.css");
const FEED = ui("webview", "feed.css");
const GEAR = ui("webview", "gear.js");
const MENU = ui("webview", "tag-menu.ts");
const TIMELINE = ui("romp-timeline-view.js");

/** The body of the FIRST rule whose selector line starts with `selector {` — brace-depth scan, so a
 *  comment containing braces inside the block cannot end it early. */
function block(css: string, selector: string): string {
  const at = css.indexOf("\n" + selector + " {");
  assert.ok(at >= 0, "rule present: " + selector);
  let i = css.indexOf("{", at), depth = 0;
  for (let j = i; j < css.length; j++) {
    if (css[j] === "{") depth++;
    else if (css[j] === "}" && --depth === 0) return css.slice(i + 1, j);
  }
  throw new Error("unterminated rule: " + selector);
}
/** `var(--x, <fallback>)` → `var(--x)`: the fallback is the DARK literal every inline string may
 *  carry for sheet-less hosts; what is left must reference tokens only. One level of nested parens
 *  (an rgba() fallback) is understood. */
const stripFallbacks = (s: string) => s.replace(/var\((--[\w-]+)\s*,\s*(?:[^()]|\([^()]*\))*\)/g, "var($1)");
const slice = (src: string, from: string, to: string) => {
  const a = src.indexOf(from), b = src.indexOf(to, a + 1);
  assert.ok(a >= 0 && b > a, "slice anchors present: " + from.slice(0, 40) + " … " + to.slice(0, 40));
  return src.slice(a, b);
};
const norm = (s: string) => s.replace(/\s+/g, "").toLowerCase();

const MENU_TOKENS = ["--menu-bg", "--menu-fg", "--menu-border", "--menu-hover"];
// the dark spec — the literals the CLAUDE.md rule always named, now the dark theme's token values
const DARK = {
  "--menu-bg": "var(--vscode-menu-background, #252526)",
  "--menu-fg": "var(--vscode-menu-foreground, #cccccc)",
  "--menu-border": "rgba(255, 255, 255, 0.12)",
  "--menu-hover": "rgba(255, 255, 255, 0.09)",
  "--check-bg": "#1EA1EB",
};
const LIGHT = {
  "--menu-bg": "#FBF6EF",           // the light block's own menu card (its --vscode-menu-background stand-in)
  "--menu-fg": "#1F1E1D",
  "--menu-border": "rgba(0, 0, 0, 0.12)",
  "--menu-hover": "rgba(0, 0, 0, 0.06)",
  "--check-bg": "#C2410C",          // the light theme's clay — the mark the timeline's PAL_LIGHT already drew
};

test("the menu skin tokens live in BOTH theme blocks of BOTH sheets — dark byte-for-byte the old literals", () => {
  for (const [name, css] of [["styles.css", CHAT], ["feed.css", FEED]] as const) {
    const root = block(css, ":root"), light = block(css, "body.theme-light");
    for (const [tok, val] of Object.entries(DARK))
      assert.ok(root.includes(`${tok}: ${val};`), `${name} :root ${tok} = ${val}`);
    for (const [tok, val] of Object.entries(LIGHT))
      assert.ok(light.includes(`${tok}: ${val};`), `${name} body.theme-light ${tok} = ${val}`);
    // key parity for the menu set: a token one block defines and the other forgets is a theme leak
    for (const tok of MENU_TOKENS) {
      assert.equal((root.match(new RegExp(tok + ":", "g")) || []).length, 1, `${name} :root defines ${tok} once`);
      assert.equal((light.match(new RegExp(tok + ":", "g")) || []).length, 1, `${name} light defines ${tok} once`);
    }
  }
});

// Every menu SURFACE: the sheets' menu rules and the inline-styled menus. Each is stripped of its
// var() fallbacks and must then carry none of the dark spec's literals — those belong to the theme
// definitions (the two blocks above; PAL_DARK in the timeline) and nowhere else.
const DARK_LITERALS: Array<[string, RegExp]> = [
  ["#252526 card", /#252526/i],
  ["rgba(255,255,255,0.12) hairline", /rgba\(\s*255\s*,\s*255\s*,\s*255\s*,\s*0?\.12\s*\)/],
  ["rgba(255,255,255,0.09) hover", /rgba\(\s*255\s*,\s*255\s*,\s*255\s*,\s*0?\.09\s*\)/],
  ["rgba(0,0,0,0.35) shadow", /rgba\(\s*0\s*,\s*0\s*,\s*0\s*,\s*0?\.35\s*\)/],
  ["#cccccc text", /#cccccc\b/i],
  ["#ccc text", /#ccc\b/i],
  ["#1EA1EB check", /#1EA1EB/i],
  ["#1e1e1e input", /#1e1e1e\b/i],
  ["#3a3a3a input border", /#3a3a3a\b/i],
];
const SURFACES: Array<[string, string]> = [
  ["styles.css .ctx-menu", block(CHAT, ".ctx-menu")],
  ["styles.css .ctx-item:hover", block(CHAT, ".ctx-item:hover")],
  ["styles.css .ctx-tag-input", CHAT.slice(CHAT.indexOf("\n.ctx-tag-input {"), CHAT.indexOf("}", CHAT.indexOf("\n.ctx-tag-input {")))],
  ["styles.css .meta-menu", block(CHAT, ".meta-menu")],
  ["styles.css .meta-item", block(CHAT, ".meta-item")],
  ["styles.css .meta-item:hover", CHAT.slice(CHAT.indexOf("\n.meta-item:hover {"), CHAT.indexOf("}", CHAT.indexOf("\n.meta-item:hover {")))],
  ["styles.css .meta-item.current::after", block(CHAT, ".meta-item.current::after")],
  ["styles.css .ctx-sub .ctx-item.current::after", block(CHAT, ".ctx-sub .ctx-item.current::after")],
  ["feed.css .ctx-menu", block(FEED, ".ctx-menu")],
  ["feed.css .ctx-item:hover", block(FEED, ".ctx-item:hover")],
  ["gear.js housePick (the settings pickers — the Theme select)", slice(GEAR, "function housePick(", "var SCHEMES = [")],
  ["gear.js versionMenu (model pickers + version submenus)", slice(GEAR, "function versionMenu(", "versionMenu(jm);")],
  ["tag-menu.ts openTagMenu", slice(MENU, "export function openTagMenu", "export function tagMenuButton")],
  ["timeline menuStyleFor/menuCheckStyleFor", slice(TIMELINE, "const menuStyleFor", "let MENU_STYLE")],
];

test("no menu surface carries a raw dark literal outside the theme definitions (the fallback slot excepted)", () => {
  for (const [name, src] of SURFACES) {
    const bare = stripFallbacks(src);
    for (const [what, re] of DARK_LITERALS)
      assert.doesNotMatch(bare, re, `${name}: ${what} written raw — it belongs in the theme blocks; reference the token`);
  }
});

test("the inline menus wear the tokens — card, text, hairline, hover, radius, shadow, ✓ — with the dark literal as fallback", () => {
  const pick = slice(GEAR, "function housePick(", "var SCHEMES = [");
  const vers = slice(GEAR, "function versionMenu(", "versionMenu(jm);");
  const tag = slice(MENU, "export function openTagMenu", "export function tagMenuButton");
  for (const [name, src] of [["housePick", pick], ["versionMenu", vers], ["tag menu", tag]] as const) {
    assert.match(src, /background:\s*var\(--menu-bg, #252526\)/, name + " card");
    assert.match(src, /color:\s*var\(--menu-fg, #cccccc\)/, name + " text");
    assert.match(src, /border:\s*1px solid var\(--menu-border, rgba\(255,255,255,0\.12\)\)/, name + " hairline");
    assert.match(src, /border-radius:\s*var\(--radius-menu, 6px\)/, name + " radius");
    assert.match(src, /box-shadow:\s*var\(--shadow-menu, 0 4px 12px rgba\(0,0,0,0\.35\)\)/, name + " shadow");
    assert.match(src, /var\(--menu-hover, rgba\(255,255,255,0\.09\)\)/, name + " row hover");
    assert.match(src, /background:\s*var\(--check-bg, #1EA1EB\)/, name + " ✓ mark");
  }
  // fallback PARITY: every inline fallback equals the dark theme's resolved value (whitespace aside),
  // so a sheet-less host renders exactly the dark spec — never a third skin
  // a token whose dark value COMPOSES a VS Code var (--menu-bg/--menu-fg) resolves, sheet-less, to its own
  // innermost fallback; a literal value (rgba/hex) is already the resolved value
  const innermost = (v: string) => { const m = v.startsWith("var(") ? v.match(/,\s*(.+)\)\s*$/) : null; return m ? m[1] : v; };
  for (const src of [pick, vers, tag]) {
    for (const m of src.matchAll(/var\((--menu-[\w-]+|--check-bg|--radius-menu|--shadow-menu),\s*((?:[^()]|\([^()]*\))*)\)/g)) {
      const tok = m[1] as keyof typeof DARK, fb = m[2];
      const want = tok === "--radius-menu" ? "6px" : tok === "--shadow-menu" ? "0 4px 12px rgba(0, 0, 0, 0.35)" : innermost(DARK[tok]);
      assert.equal(norm(fb), norm(want), `${tok} fallback ${fb} must equal the dark token value ${want}`);
    }
  }
});

test("the ✓ mark is themed through --check-bg on every surface: dark #1EA1EB, light the clay the timeline draws", () => {
  // the sheets' checks read the token
  assert.match(block(CHAT, ".meta-item.current::after"), /background: var\(--check-bg\)/);
  assert.match(block(CHAT, ".ctx-sub .ctx-item.current::after"), /background: var\(--check-bg\)/);
  assert.match(FEED, /\.feed-viewmenu \.ctx-item\.current::after \{[^}]*var\(--check-bg\)/s, "the feed's view menu check");
  // the timeline's palette IS its theme definition — its two values are the two blocks' values
  assert.match(TIMELINE, /const PAL_DARK = \{[\s\S]*?accentSolid: '#1EA1EB'/, "PAL_DARK ✓ = the dark token");
  assert.match(TIMELINE, /const PAL_LIGHT = \{[\s\S]*?accentSolid: '#C2410C'/, "PAL_LIGHT ✓ = the light token");
  assert.match(TIMELINE, /background:' \+ p\.accentSolid \+ '/, "menuCheckStyleFor reads the palette, never a literal");
  for (const [name, css] of [["styles.css", CHAT], ["feed.css", FEED]] as const) {
    assert.ok(block(css, ":root").includes("--check-bg: #1EA1EB;"), name + " dark ✓ pinned byte-for-byte");
    assert.ok(block(css, "body.theme-light").includes("--check-bg: #C2410C;"), name + " light ✓ = the clay accent");
    assert.ok(block(css, "body.theme-light").includes("--accent: #C2410C;"), name + " …which IS the light accent (one clay)");
  }
});

test("the CLAUDE.md rule names the tokens and keeps the hex as the dark theme's values", () => {
  const md = fs.readFileSync(path.resolve(process.cwd(), "..", "CLAUDE.md"), "utf8");
  const rule = md.slice(md.indexOf("### Menus and dropdowns wear ONE vocabulary"), md.indexOf("The romp accent is light blue"));
  for (const tok of ["--menu-bg", "--menu-fg", "--menu-border", "--menu-hover", "--radius-menu", "--shadow-menu", "--check-bg"])
    assert.ok(rule.includes("`" + tok + "`"), "the rule names " + tok);
  assert.ok(rule.includes("`#252526`") && rule.includes("`#1EA1EB`"), "the dark values stay documented");
  assert.match(rule, /FALLBACK/, "the one sanctioned place for a raw hex in a menu string");
});
