// BLOCK_BOXES (anchor-map.ts), the tags a whitespace-only text node is skipped beside, held in node in both directions: the set
// equals the tags the HTML Standard's Rendering section lays out as block-level boxes or as a table's parts
// (anchor-map-fixtures/block-tags.json, the section's own display rules) that the sanitizer keeps (DOMPurify's html allowlist,
// read off the installed module's source, less md-sanitize.ts's MD_FORBID_TAGS), html and body left out, which the parser
// never places in a fragment. md-config-paint-whitespace-browser.test.ts leg 1 derives the same set live (the allowlist through
// a DOMPurify instance's hook, the display from Chromium) and holds the fixture to Chromium, but skips without a playwright
// browser, which CI does not install, so a tag added or dropped by hand passed every test CI ran: round 8's list named form and
// fieldset, which the sanitizer strips, and lacked center, dir, menu, search, hgroup, col and colgroup, and anchor-map-obsidian's
// scenes pin a tag only when one of them holds it (the Slice 4 review, round 10). Nothing here needs a browser: a hand edit
// fails on CI, the tags that differ named, and a DOMPurify upgrade that allows a block tag it strips today (listing, say)
// fails the same way until the set has it. The section's blocks the sanitizer strips are pinned both ways against
// MD_FORBID_TAGS too, so a fixture that omits one of them fails by name (round 10's lacked option; the Slice 4 review, round 11).
// Tag names only, no prose fixture.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import DOMPurify from "dompurify";
import { BLOCK_BOXES } from "./anchor-map";
import { MD_FORBID_TAGS, MD_PURIFY } from "./md-sanitize";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
type Fixture = { note: string[]; tags: Record<string, string> };
const FIXTURE = JSON.parse(fs.readFileSync(path.join(UI, "anchor-map-fixtures", "block-tags.json"), "utf8")) as Fixture;
/** The displays the section's rules give the fixture's tags: block-level boxes and the table and its parts (the browser leg's
 *  BLOCK_DISPLAYS names Chromium's, flow-root, flex and grid among them, which no rule of the section uses). */
const BLOCK_DISPLAYS = ["block", "list-item", "table", "table-caption", "table-column", "table-column-group", "table-header-group", "table-row-group", "table-footer-group", "table-row", "table-cell"];
/** The document's own elements, which the HTML parser never places in a fragment (a `<body>` in a note's html is dropped). */
const NEVER_IN_A_FRAGMENT = ["html", "body"];
/** The tags of MD_FORBID_TAGS the section lays out as blocks: dialog, form and legend (15.3.3 Flow content), fieldset (15.3.12
 *  The fieldset and legend elements), option and optgroup (15.5.16 The select element, a bare `option { display: block }` rule
 *  above optgroup's). The rest of the forbid list it renders inline-block (button, select), hides (style, datalist, area) or
 *  gives no display rule (textarea, label, output, meter, progress, map), so none of those is a block by the section. */
const STRIPPED_BLOCKS = ["dialog", "fieldset", "form", "legend", "optgroup", "option"];

/** DOMPurify's html allowlist, read off the installed module's own source (the package's main file, resolved from the
 *  extension): the frozen array of tag names its html profile allows. The library exports no list and, without a window, no
 *  instance to ask (isSupported is false in node; the browser leg reads the same list through an instance's hook). The array
 *  is the one holding every tag of a small probe set, so the build's variable names do not matter and a changed shape fails
 *  here, loudly, naming the file. */
function dompurifyHtmlTags(): { tags: string[]; file: string } {
  const file = createRequire(path.join(EXT, "package.json")).resolve("dompurify");
  const src = fs.readFileSync(file, "utf8");
  const arrays: string[][] = [];
  for (const m of src.matchAll(/freeze\(\[((?:\s*'[^']*'\s*,?)+)\]\)/g)) arrays.push(Array.from(m[1].matchAll(/'([^']*)'/g), (a) => a[1]));
  const probe = ["a", "blockquote", "img", "summary", "table"];
  const hits = arrays.filter((a) => probe.every((t) => a.includes(t)));
  assert.equal(hits.length, 1, "one frozen array in " + file + " holds every html tag of the probe set (" + probe.join(", ") + "), the html allowlist: " + hits.length + " of " + arrays.length + " arrays do");
  return { tags: hits[0], file };
}
const upper = (tags: Iterable<string>): string[] => Array.from(tags, (t) => t.toUpperCase()).sort();
const minus = (a: string[], b: string[]): string[] => a.filter((t) => !b.includes(t));

test("the fixture is the rendering section's list: html and body on it, every value a block-level or table display, the section's blocks the sanitizer strips or DOMPurify never allows on it too (the list is the spec's, not the set's)", () => {
  const tags = Object.keys(FIXTURE.tags);
  assert.ok(FIXTURE.note.join(" ").includes("html.spec.whatwg.org/multipage/rendering.html"), "the note names the source");
  for (const t of NEVER_IN_A_FRAGMENT) assert.equal(FIXTURE.tags[t], "block", t + " is a block by the page's rule and is left out of the set by name, not by the fixture");
  for (const [t, d] of Object.entries(FIXTURE.tags)) {
    assert.equal(t, t.toLowerCase(), "tag names as the section spells them: " + t);
    assert.ok(BLOCK_DISPLAYS.includes(d), t + " has a block-level or table display: " + d);
  }
  // the section's blocks the sanitizer strips, both ways: every MD_FORBID_TAGS tag the section lays out as a block is on the
  // fixture, no other forbidden tag is, and the note names each one, so a block the fixture omits, or carries without saying so,
  // fails here by name (round 10's fixture had optgroup and not option, the rule directly above it in the section)
  const stripped = tags.filter((t) => MD_FORBID_TAGS.includes(t)).sort();
  assert.deepEqual(stripped, [...STRIPPED_BLOCKS].sort(), "the fixture's tags the sanitizer strips are the section's block form controls and the dialog: missing " + JSON.stringify(minus(STRIPPED_BLOCKS, stripped)) + ", extra " + JSON.stringify(minus(stripped, STRIPPED_BLOCKS)));
  const note = FIXTURE.note.join(" ");
  for (const t of STRIPPED_BLOCKS) assert.ok(new RegExp("\\b" + t + "\\b").test(note), "the note names " + t + " among the stripped blocks the fixture carries on purpose");
  for (const t of ["listing", "plaintext", "xmp"]) assert.ok(tags.includes(t), t + " is a block by the section: on the fixture, off the set because DOMPurify's allowlist lacks it");
  for (const t of ["li", "table", "caption", "colgroup", "col", "thead", "tbody", "tfoot", "tr", "td", "th", "details", "summary", "hgroup", "search", "center", "dir", "menu"]) assert.ok(tags.includes(t), t + " is on the fixture");
  assert.equal(new Set(tags).size, tags.length);
});

test("BLOCK_BOXES equals the fixture's tags the sanitizer keeps, html and body left out: every such tag is in the set and nothing else is (round 8's hand list, form and fieldset in, center, dir, menu, search, hgroup, col and colgroup out, fails here)", () => {
  const { tags: allowed, file } = dompurifyHtmlTags();
  assert.ok(allowed.length > 100, "the allowlist read from " + file + " holds " + allowed.length + " tags");
  assert.deepEqual(MD_PURIFY.USE_PROFILES, { html: true, svg: true }, "the profile is DOMPurify's html list (and svg, whose elements are no block boxes in an html document: the browser leg reads both and derives no block from the svg one)");
  assert.equal((MD_PURIFY as { ADD_TAGS?: string[] }).ADD_TAGS, undefined, "no tag added past the profiles, so the allowlist is the html profile's");
  assert.deepEqual([...(MD_PURIFY.FORBID_TAGS || [])].sort(), [...MD_FORBID_TAGS].sort(), "the profile forbids MD_FORBID_TAGS and no other tag");
  for (const t of MD_FORBID_TAGS) assert.ok(allowed.includes(t) || t === "style", t + " is a tag the profile would allow, forbidden on purpose (a forbid of a tag DOMPurify never allowed is a stale entry)");
  const forbid = new Set(MD_FORBID_TAGS);
  const kept = allowed.filter((t) => !forbid.has(t));
  const expected = upper(kept.filter((t) => t in FIXTURE.tags && !NEVER_IN_A_FRAGMENT.includes(t)));
  const shipped = upper(BLOCK_BOXES);
  assert.deepEqual(shipped, expected, "BLOCK_BOXES differs from the fixture's kept tags: missing " + JSON.stringify(minus(expected, shipped)) + ", extra " + JSON.stringify(minus(shipped, expected)) + " (DOMPurify " + DOMPurify.version + ")");
  // the members the finding named, each way: kept blocks in, stripped blocks out, blocks the allowlist lacks out, inline tags out
  for (const t of ["center", "dir", "menu", "search", "hgroup", "col", "colgroup", "details", "summary", "figure", "figcaption", "dl", "dt", "dd", "pre", "hr", "li"]) {
    assert.ok(allowed.includes(t) && !forbid.has(t), t + " is kept by the sanitizer");
    assert.ok(BLOCK_BOXES.has(t.toUpperCase()), t + " is in the set");
  }
  for (const t of ["form", "fieldset", "legend", "dialog", "optgroup", "option"]) assert.ok(!BLOCK_BOXES.has(t.toUpperCase()) && forbid.has(t), t + " is stripped by the sanitizer, so it is no neighbour a note can have and is not in the set");
  for (const t of ["listing", "plaintext", "xmp"]) assert.ok(!BLOCK_BOXES.has(t.toUpperCase()) && !allowed.includes(t), t + " is a block the allowlist lacks: not in the set");
  for (const t of NEVER_IN_A_FRAGMENT) assert.ok(allowed.includes(t) && t in FIXTURE.tags && !BLOCK_BOXES.has(t.toUpperCase()), t + " is allowed and a block, left out of the set by name");
  for (const t of ["span", "a", "em", "strong", "b", "i", "code", "img", "br", "mark", "sup", "sub", "del", "ins", "kbd", "q", "time", "data", "abbr", "small", "u", "s", "wbr", "picture", "video", "audio", "canvas", "ruby", "rt", "rp", "marquee", "input", "template", "slot"]) {
    assert.ok(allowed.includes(t), t + " is on the allowlist (the probe names a real tag)");
    assert.ok(!(t in FIXTURE.tags) && !BLOCK_BOXES.has(t.toUpperCase()), t + " is no block by the section and not in the set: a space beside it is the passage's own, painted");
  }
});
