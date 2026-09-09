// ONE sanitizer for every piece of markdown the dashboard renders as HTML: the chat's md() and userMd()
// (render.ts) and the file viewer's mdBlock (file-view.ts). The two used to spell the same DOMPurify
// profile in two places; the rules a note's own HTML lives under now sit here, once, and both call
// sanitizeMd (plans/markdown-viewer.md, Slice 1: sanitize as GitHub does, 2026-09-07).
//
// What a note's HTML may do, GitHub's rules:
//   • no <style> block, no <dialog>, and no form-associated element: a <style> blanked the page and a
//     <form action=…><button> navigated the Files document away (the audit's two High defects). style's
//     text goes with it (DOMPurify's default FORBID_CONTENTS); a form's or a button's TEXT stays as prose
//     (KEEP_CONTENT), so a note reads the same minus the control.
//   • <input> survives ONLY as marked's task-list checkbox, `- [x] done` → <input checked disabled
//     type=checkbox>: every other input goes, and a checkbox that lacks `disabled` gets it, so nothing in
//     a note is a live control.
//   • an author's id and name are PREFIXED `user-content-` (SANITIZE_NAMED_PROPS, the rule GitHub applies):
//     a `<p id="tabs">` can no longer dress itself in the page's #tabs CSS or shadow getElementById for the
//     page's own controls, and `<a name="install">` still exists under its prefixed name. An `href="#install"`
//     is NOT rewritten to match: the two click handlers compare the prefixed form instead, through one lookup
//     (userContentTarget below: the viewer's fragmentTarget in file-view-links.ts, and the chat's delegate in
//     render.ts, which resolves a message's `#` click the way GitHub's page script does, since the browser's
//     default lookup reads the bare name and finds nothing). Rewriting hrefs here would break the viewer's
//     section link to a plain heading: `[results](#results)` over `## Results` with no `<a name>` above it lands
//     on the heading id `md-results` (fragmentTarget's slug arm), and the viewer's heading ids (`md-<slug>`,
//     mdBlock) are minted AFTER the sanitize and never gain the prefix, so a rewritten `#user-content-results`
//     would name nothing; the viewer's `Go to <fragment>` title would show the prefix too. With an
//     `<a name="results">` above the heading the link lands on that anchor under its prefixed name, through
//     userContentTarget, whichever spelling the href carries (the bare arm reads an ask that already holds the
//     prefix).
//   • an inline `style` keeps only `color` and `background-color` declarations whose value is a literal
//     colour (the user 2026-09-07, decision 6: coloured spans in existing notes survive; positioning and
//     layout never reach the page). Everything else in the attribute is dropped, and the attribute goes
//     when nothing is left: colourOnlyStyle below is the whole grammar, applied by a DOMPurify
//     uponSanitizeAttribute hook on every element, inline SVG included.
//   • data-* never rides in (ALLOW_DATA_ATTR: false): both pages key their delegated actions off data-act.
//   • the `background` attribute is forbidden outright (FORBID_ATTR): `<td background=URL>` makes the browser fetch
//     the URL the moment the note renders, a tracking pixel with no click and no gate, on both pages; DOMPurify's
//     html list keeps it, GitHub's allowlist does not, and it has no safe value here. `bgcolor` fetches nothing and
//     stays, as a colour-only inline style does. Remote figures (`<img src>`, video, audio, source) are decision
//     8's: gated in Slice 4, where their src is rewritten.
//   • no image map: `<map>`, `<area>` and `usemap` go (FORBID_TAGS, FORBID_ATTR), as GitHub drops them. The prefix
//     rule above renames `<map name="nav">` to user-content-nav and leaves `usemap="#nav"` as written, so no map an
//     author writes can bind to its picture (review round 1, found in the tests' own fixtures, which had spelled the
//     prefix by hand); an <area> that did bind was a link element neither page's link passes reached until round 1
//     (md-links.ts LINK_SEL), and in a file document it is a shape the module that dresses the file's links
//     (file-view-links.ts linkMarkdownAnchors, an `a` walk) does not see. Dropped, the picture is inert prose.
//   • html + svg profiles (the user 2026-08-19, when KaTeX's stretchy glyphs came through here as inline <svg>;
//     a note's own inline SVG still does), data: URIs on <img> (the CSP allows them; inline transcript images
//     rely on them).
//
// What does NOT pass through here: KaTeX. Its layout is all inline style, which the colour-only rule would
// strip, so the math extensions emit an inert placeholder and KaTeX is rendered into it on the sanitized
// DOM afterwards (math.ts renderMathPlaceholders), as a POST-PASS this module runs at the end of sanitizeMd
// for every caller: the module that installs the math grammar (md-config.ts) registers the fill at load
// (registerMdPostPass), and every bundle that hosts the chat or the viewer (render.js, files.js, feed.js)
// imports that module, so the chat's md() and userMd() and the viewer's mdBlock render math on every surface
// (Slice 4 of plans/markdown-viewer.md; before it files.js and feed.js had neither the grammar nor the pass
// nor the library). A renderer romp itself runs never goes through the sanitizer; only what an author wrote does.
import DOMPurify from "dompurify";
import type { Config, DOMPurify as DOMPurifyInstance, UponSanitizeAttributeHookEvent } from "dompurify";

/** Tags a note may not keep: the style sheet, the dialog, every form-associated element, and the image map. */
export const MD_FORBID_TAGS: readonly string[] = [
  "style", "dialog",
  "form", "button", "select", "option", "optgroup", "textarea", "fieldset", "legend", "label", "datalist", "output", "meter", "progress",
  "map", "area",
];

/** Attributes a note may not keep at all: `background`, a remote fetch on render with no safe value, and `usemap`, the
 *  image map's binding (the map itself is forbidden above). Every other attribute the profiles allow either is safe as
 *  written or is rewritten (id and name prefixed, style filtered). */
export const MD_FORBID_ATTR: readonly string[] = ["background", "usemap"];

/** The prefix SANITIZE_NAMED_PROPS puts on an author's id and name (DOMPurify's own constant is not exported). A
 *  section link inside a note and a `#fragment` clicked in a chat message are looked up under it (userContentTarget
 *  below); the viewer's minted `md-` heading ids are set after the sanitize and never carry it. */
export const USER_CONTENT_PREFIX = "user-content-";

/** The element an author's `#id` names in `root` after the sanitize: the first whose `id` is the prefixed spelling or
 *  the bare one, else the first `<a name>` with either, in document order (the browser's own fragment rule, applied to
 *  both spellings). The bare arm serves ids the sanitizer never saw: the viewer's minted `md-` heading ids, the page's
 *  own ids when `root` is the document (what the browser's default would have scrolled to), and an author who typed
 *  the prefix. Nothing when neither is found. The viewer's fragmentTarget (file-view-links.ts) adds its heading-slug arm
 *  to this; the chat's click delegate (render.ts) reads it as is, the message's body first and then the document. */
export function userContentTarget(root: ParentNode, id: string): Element | undefined {
  const own = USER_CONTENT_PREFIX + id;
  return Array.from(root.querySelectorAll("[id]")).find((e) => { const v = e.getAttribute("id"); return v === own || v === id; })
    || Array.from(root.querySelectorAll("a[name]")).find((e) => { const v = e.getAttribute("name"); return v === own || v === id; });
}

/** The one profile. Spread `RETURN_DOM: true` onto it to take the sanitized <body> back (sanitizeMd does). */
export const MD_PURIFY: Config = {
  USE_PROFILES: { html: true, svg: true },
  ADD_DATA_URI_TAGS: ["img"],
  ALLOW_DATA_ATTR: false,
  FORBID_TAGS: [...MD_FORBID_TAGS],
  FORBID_ATTR: [...MD_FORBID_ATTR],
  SANITIZE_NAMED_PROPS: true,
};

// ── the colour grammar ──────────────────────────────────────────────────────────────────────────────
// A value is a literal colour when it is one of: a bare keyword (a named colour, `transparent`,
// `currentcolor`, a CSS-wide keyword such as `inherit` or `unset`; an unknown word is a declaration the
// browser ignores, never a function or a URL; a hyphenated word such as `revert-layer` fails the pattern),
// `#` and 3 to 8 hex digits, or rgb()/rgba()/hsl()/hsla() whose arguments are 3 or 4 plain numbers or
// percentages (an angle unit, deg/grad/rad/turn, is accepted on any argument by the one shared pattern,
// though only an hsl hue can carry one and the browser discards an rgb() written with one; `none` is CSS
// Color 4's missing component), separated by commas, spaces or a slash. Nothing else: no nested
// parentheses (so no url(, var(, expression(, calc(), no `!important`, no quotes, no backslash escapes,
// no comments.
const KEYWORD = /^[a-z]+$/i;
const HEX = /^#[0-9a-f]{3,8}$/i;
const COLOUR_FN = /^(rgba?|hsla?)\(([^()]*)\)$/i;
const COLOUR_ARG = /^(?:[+-]?(?:\d+\.?\d*|\.\d+)(?:%|deg|grad|rad|turn)?|none)$/i;
const KEPT_PROPERTIES = new Set(["color", "background-color"]);

/** Whether `v` (already trimmed) is a literal colour under the grammar above. */
export function isLiteralColour(v: string): boolean {
  if (KEYWORD.test(v) || HEX.test(v)) return true;
  const m = COLOUR_FN.exec(v);
  if (!m) return false;
  const args = m[2].trim().split(/\s*[,/]\s*|\s+/).filter((a) => a.length > 0);
  return args.length >= 3 && args.length <= 4 && args.every((a) => COLOUR_ARG.test(a));
}

/** The declarations of a `style` attribute that survive: `color` and `background-color` with a literal
 *  colour, in their order, as `name: value` joined by `; `. Empty when nothing survives (the caller drops
 *  the attribute). Splitting on `;` is safe because no surviving value can contain one. */
export function colourOnlyStyle(style: string): string {
  const kept: string[] = [];
  for (const decl of style.split(";")) {
    const at = decl.indexOf(":");
    if (at < 0) continue;
    const name = decl.slice(0, at).trim().toLowerCase();
    const value = decl.slice(at + 1).trim();
    if (!KEPT_PROPERTIES.has(name) || !value || !isLiteralColour(value)) continue;
    kept.push(name + ": " + value);
  }
  return kept.join("; ");
}

/** The DOMPurify uponSanitizeAttribute hook body: rewrites a `style` attribute to its colour
 *  declarations, drops it when none survive, and leaves every other attribute to DOMPurify. */
export function styleAttributeHook(ev: Pick<UponSanitizeAttributeHookEvent, "attrName" | "attrValue" | "keepAttr">): void {
  if (ev.attrName !== "style") return;
  const kept = colourOnlyStyle(ev.attrValue);
  if (kept) ev.attrValue = kept;
  else ev.keepAttr = false;
}

let hooksInstalled = false;
/** Install the style hook on the (module-global) DOMPurify instance, once. Idempotent: DOMPurify's hooks
 *  are a list, and a second registration would run the same rewrite twice per attribute. `purify` is a
 *  seam for the node tests, which have no window for the real instance to sanitize in. */
export function installMdSanitizeHooks(purify: Pick<DOMPurifyInstance, "addHook"> = DOMPurify): void {
  if (hooksInstalled) return;
  hooksInstalled = true;
  purify.addHook("uponSanitizeAttribute", (_node, ev) => { styleAttributeHook(ev); });
}

/** marked's task checkbox is the one control a note keeps, inert: every other <input> goes, and a
 *  checkbox without `disabled` gets it. Runs on the sanitized DOM, after DOMPurify. */
function keepOnlyInertCheckboxes(root: ParentNode): void {
  root.querySelectorAll("input").forEach((node) => {
    const input = node as HTMLInputElement;
    if ((input.getAttribute("type") || "").toLowerCase() !== "checkbox") { input.remove(); return; }
    if (!input.hasAttribute("disabled")) input.setAttribute("disabled", "");
  });
}

const postPasses: Array<(root: ParentNode) => void> = [];
/** Register a DOM pass sanitizeMd runs on every sanitized body before handing it back. For the module that installs a
 *  marked extension whose output needs a render AFTER the sanitize (md-config.ts: the math placeholders KaTeX fills,
 *  math.ts renderMathPlaceholders), registered at load: the grammar and its fill travel together, so every sanitizeMd
 *  caller in a bundle that parses with the grammar renders the same way (the chat's md() and userMd(); the viewer's
 *  mdBlock on every surface, since Slice 4 of plans/markdown-viewer.md put the one configuration in every bundle that
 *  hosts the viewer; before it files.js and feed.js had neither the grammar nor the pass nor the library). One
 *  mechanism, no per-caller call to forget: the first cut had md() and userMd() call the fill by hand and the chat
 *  page's viewer showed bare TeX (the 2026-09-07 review, round 1). Idempotent: a pass registered twice runs once. */
export function registerMdPostPass(pass: (root: ParentNode) => void): void {
  if (!postPasses.includes(pass)) postPasses.push(pass);
}

/** Sanitize marked's HTML under the profile above and return the sanitized <body>: its children are the
 *  nodes to adopt (mdBlock) or its innerHTML the string to set (md, userMd), after any DOM post-pass of
 *  the caller's own (PR links, the viewer's link stamps). The registered passes (the math fill) have run by then.
 *  `own`, when given, is a pass of the caller's that must read the sanitized markup AS MARKED EMITTED IT, so it
 *  runs after the sanitizer's own rules and BEFORE the registered passes rewrite any of it: the viewer mints its
 *  heading ids there (file-view.ts mintHeadingIds), from each heading's text as the author wrote it, which for a
 *  formula is the placeholder's TeX. Read after the fill, a heading with math slugged KaTeX's glyphs instead, in
 *  layout order (a fraction's denominator before its numerator, a U+200B strut), so `# Ratio $\frac{a}{b}$` was
 *  `md-ratio-ba` where GitHub's slug of the text, and the id the Files pane minted before the fill reached its
 *  bundle, is `md-ratio-fracab`, and the note's own `[see](#ratio-fracab)` rendered dead (the Slice 4 review). The
 *  only DOMPurify.sanitize call in the dashboard's source. */
export function sanitizeMd(dirty: string, own?: (body: HTMLElement) => void): HTMLElement {
  installMdSanitizeHooks();
  const clean = DOMPurify.sanitize(dirty, { ...MD_PURIFY, RETURN_DOM: true }) as HTMLElement;   // the sanitized <body>
  keepOnlyInertCheckboxes(clean);
  if (own) own(clean);
  for (const pass of postPasses) pass(clean);
  return clean;
}

/** The HTML spec's ancestor revealing steps, which the browser's own fragment navigation runs before it scrolls and
 *  scrollIntoView does not: every closed <details> whose content holds `target` is opened (a target inside a details'
 *  own <summary> is in view already and opens nothing, as in the browser), and a `hidden="until-found"` on the target
 *  or an ancestor is removed. Both shapes pass the sanitizer (details, summary and hidden are kept), and a folded
 *  callout (`> [!type]-`, md-config.ts) is a closed details an author reaches from plain markdown, so a heading, a
 *  footnote definition or an anchor inside one is a `#` target that has to be revealed first: without this, the
 *  viewer's scrollToFragment (file-view.ts) scrolled to nothing and the fold stayed shut (the Slice 4 review); the
 *  chat's `#` delegate (render.ts) runs the same steps ahead of its scroll. */
export function revealFragmentTarget(target: Element): void {
  for (let n: Element | null = target; n; n = n.parentElement) {
    if ((n.getAttribute("hidden") || "").toLowerCase() === "until-found") n.removeAttribute("hidden");
    const p = n.parentElement;
    if (p && p.localName === "details" && n.localName !== "summary" && !p.hasAttribute("open")) p.setAttribute("open", "");
  }
}
