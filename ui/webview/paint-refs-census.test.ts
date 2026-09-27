// The sanitizer's surviving attributes held to the derived url() sets (paint-refs.ts URL_ATTRS and URL_PROPERTIES), read off the
// installed DOMPurify's own attribute lists, under node. The paint strip reads the names an engine takes a url() from; this
// census says that every such name the sanitizer lets through is one the strip reads (or is `style`, whose declarations it reads
// by property), that the viewer gate's own list is the same set cut to what survives, that no `<style>` sheet survives (the
// module has no rule parser), and that the colour-only style hook keeps no url()-taking property. It reads the dist by the three
// arrays' literal heads and fails by name when one is missing, so a DOMPurify upgrade that moves them is a red, never an empty
// set; and its predicate is run against a widened set, so the census is seen to bite. The browser half, the two sets re-derived
// in the installed Chromium, is the render-path leg's. Synthetic only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { MD_FORBID_ATTR, MD_FORBID_TAGS, MD_PURIFY, colorOnlyStyle, isLiteralColor } from "./md-sanitize";
import { URL_ATTRS, URL_PROPERTIES } from "./paint-refs";
import { PAINT_ATTRS } from "./figure-gate";

const DP = path.resolve(process.cwd(), "node_modules", "dompurify");
const VERSION = (JSON.parse(fs.readFileSync(path.join(DP, "package.json"), "utf8")) as { version: string }).version;
const DIST_FILE = "dist/purify.es.mjs";
const DIST = fs.readFileSync(path.join(DP, DIST_FILE), "utf8");
const TAG = "dompurify " + VERSION + " " + DIST_FILE + ": ";

/** One of the dist's attribute arrays, read by its literal head (`const svg = freeze([`) as the names it holds. Loud by name:
 *  a head that is missing, or found twice, is a red naming it, so an upgrade that renames or moves the lists cannot hand the
 *  census an empty set. */
function distArray(name: string): string[] {
  const head = "const " + name + " = freeze([";
  const at = DIST.indexOf(head);
  assert.ok(at >= 0, TAG + "no `" + head + "`: the attribute list the census reads by its literal head is gone or renamed (an upgrade moved DOMPurify's lists); re-derive this reader against the new dist before trusting the census");
  assert.equal(DIST.indexOf(head, at + 1), -1, TAG + "`" + head + "` occurs twice: the census cannot tell which list the profile reads");
  const end = DIST.indexOf("]);", at);
  assert.ok(end > at, TAG + "`" + head + "` has no closing `]);`");
  const body = DIST.slice(at + head.length, end);
  assert.equal(body.replace(/'[^'\\]*'/g, "").replace(/[\s,]/g, ""), "", TAG + "the " + name + " list holds quoted names and nothing else (a spread or a call in it would hide names from this reader)");
  const names = [...body.matchAll(/'([^'\\]*)'/g)].map((m) => m[1]);
  assert.ok(names.length > 0, TAG + "the " + name + " list read empty");
  return names;
}

/** The attributes the sanitizer lets through: DOMPurify's html, svg and xml lists (the html and svg profiles' ALLOWED_ATTR,
 *  pinned below) minus MD_FORBID_ATTR. One flat set: DOMPurify judges an attribute by its name alone, on every element. */
function survivingSet(): Set<string> {
  return new Set([...distArray("html"), ...distArray("svg"), ...distArray("xml")].filter((a) => !MD_FORBID_ATTR.includes(a)));
}

/** Names that survive and share a name with a url()-taking CSS property, measured NOT to carry a url() as an attribute: the
 *  attribute derivation (paint-refs.ts's header) set each on an svg `<rect>` in Chromium 151, Firefox 153 and WebKit 26.5 and
 *  read no url() back from its computed style. Each entry is a measurement with its reason, never a way to green the census. */
const MEASURED_INERT: Record<string, string> = {
  offset: "a gradient stop's `offset`, a number: `offset=\"url(...)\"` on a rect left no url() in its computed style in any of the three engines (2026-09-23); the CSS `offset` shorthand, which takes one, is another thing of the same name",
};
const inert = (a: string): boolean => Object.prototype.hasOwnProperty.call(MEASURED_INERT, a);

/** The census predicate: names in `surviving` that an engine may read a url() from (by URL_ATTRS, or by a URL_PROPERTIES name)
 *  and that the strip does not read as an attribute (not in URL_ATTRS), other than `style` and the measured-inert names. */
function unreadUrlCarriers(surviving: Set<string>): string[] {
  return [...surviving].filter((a) => (URL_ATTRS.includes(a) || URL_PROPERTIES.includes(a)) && !URL_ATTRS.includes(a) && a !== "style" && !inert(a)).sort();
}

test("1. the surviving set is DOMPurify's html, svg and xml attribute lists minus MD_FORBID_ATTR, read off the installed dist under the profile's own branch; `style` is in it, so the strip's style arm is live", () => {
  // guards the census's input: the set it judges is the one the sanitizer applies, derived from the installed library
  assert.deepEqual(MD_PURIFY.USE_PROFILES, { html: true, svg: true }, "the profile: html and svg");
  for (const k of ["ADD_ATTR", "ALLOWED_ATTR"]) assert.ok(!(k in MD_PURIFY), "the profile widens no attribute list by " + k);
  assert.match(DIST, /if \(USE_PROFILES\) \{\n\s*ALLOWED_TAGS = addToSet\(\{\}, text\);\n\s*ALLOWED_ATTR = create\(null\);\n\s*if \(USE_PROFILES\.html === true\) \{\n\s*addToSet\(ALLOWED_TAGS, html\$1\);\n\s*addToSet\(ALLOWED_ATTR, html\);\n\s*\}\n\s*if \(USE_PROFILES\.svg === true\) \{\n\s*addToSet\(ALLOWED_TAGS, svg\$1\);\n\s*addToSet\(ALLOWED_ATTR, svg\);\n\s*addToSet\(ALLOWED_ATTR, xml\);\n\s*\}/,
    TAG + "under USE_PROFILES the allowed attributes are rebuilt from nothing: the html profile adds the html list, the svg profile the svg and xml lists");
  const surviving = survivingSet();
  for (const a of MD_FORBID_ATTR) assert.ok(!surviving.has(a), a + " is forbidden and does not survive");
  for (const a of ["fill", "stroke", "mask", "clip-path", "filter", "marker-start", "marker-mid", "marker-end", "xlink:href", "href", "src"]) assert.ok(surviving.has(a), a + " survives (the reader found the lists' contents)");
  assert.ok(surviving.has("style"), "`style` survives (the colour-only hook rewrites it), so the style arm reads live input");
});

test("2. every surviving name an engine may read a url() from is one the strip reads as an attribute (URL_ATTRS) or is `style`; a measured-inert name is listed with its measurement, and each listed one does survive", () => {
  // guards the population: a widened allowlist that lets a url()-taking name through reds here until the strip reads it
  const surviving = survivingSet();
  assert.deepEqual(unreadUrlCarriers(surviving), [], "a surviving attribute the engines may read a url() from, which the strip does not read: add it to URL_ATTRS in paint-refs.ts (after a derivation run shows the engines read it) or, when the derivation measured it inert, to MEASURED_INERT with the measurement");
  for (const a of Object.keys(MEASURED_INERT)) {
    assert.ok(surviving.has(a) && URL_PROPERTIES.includes(a) && !URL_ATTRS.includes(a), a + ": a measured-inert entry names a surviving attribute that shares a url()-taking property's name (a stale entry is removed, not kept)");
  }
  assert.deepEqual(Object.keys(MEASURED_INERT), ["offset"], "one measured-inert name today");
});

test("3. the viewer gate's PAINT_ATTRS is URL_ATTRS cut to the surviving set: the gate's list is derived too", () => {
  // guards the gate's list against drifting from the derivation: a name the engines read that survives is gated in the viewer
  const surviving = survivingSet();
  assert.deepEqual([...PAINT_ATTRS].sort(), URL_ATTRS.filter((a) => surviving.has(a)).sort(), "PAINT_ATTRS (figure-gate.ts) equals the derived URL_ATTRS intersected with what survives");
  assert.ok(!surviving.has("cursor") && URL_ATTRS.includes("cursor"), "cursor is the one derived name that does not survive today: carried by the strip, absent from the gate");
});

test("4. no `<style>` element survives: a sheet can hold any URL_PROPERTIES declaration and the strip has no rule parser", () => {
  // guards the boundary the strip relies on: allowing <style> would need a rule parser here first
  assert.ok(MD_FORBID_TAGS.includes("style"), "`style` is in MD_FORBID_TAGS (md-sanitize.ts): a later allowance of <style> reds here, since paint-refs.ts reads attributes and declarations, never a sheet's rules");
});

test("5. the colour-only style hook keeps no property in URL_PROPERTIES, and its colour grammar admits no url()", () => {
  // guards the tie between the hook and the set: colorOnlyStyle is why the style arm finds nothing in today's tree
  assert.ok(!URL_PROPERTIES.includes("color") && !URL_PROPERTIES.includes("background-color"), "the two kept properties take no url()");
  for (const p of URL_PROPERTIES) {
    assert.equal(colorOnlyStyle(p + ": url(https://remote.invalid/x.png)"), "", p + ": a url() declaration is dropped by the hook");
    assert.equal(colorOnlyStyle(p + ": red"), "", p + ": the property is not kept even with a colour value");
  }
  assert.equal(isLiteralColor("url(x)"), false, "url(x) is no literal colour");
});

test("6. the census bites: its predicate over the surviving set plus a synthetic `background-image` names it, while a widening to `cursor`, which the strip already reads, passes", () => {
  // the positive control: without it a predicate that could never fire would green item 2 on every tree
  const surviving = survivingSet();
  assert.deepEqual(unreadUrlCarriers(new Set([...surviving, "background-image"])), ["background-image"], "a widened allowlist that let `background-image` through is red until the strip reads it");
  assert.deepEqual(unreadUrlCarriers(new Set([...surviving, "cursor"])), [], "a widening to `cursor` passes: URL_ATTRS carries it");
});
