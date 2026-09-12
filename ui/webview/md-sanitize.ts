// ONE sanitizer for every piece of markdown the dashboard renders as HTML: the chat's md() and userMd()
// (render.ts) and the file viewer's mdBlock (file-view.ts). The two used to spell the same DOMPurify
// profile in two places, and that profile was DOMPurify's default html list, which keeps <style>, <form>,
// <button>, <dialog>, inline `style`, `id`, `name` and the `background` attribute. A markdown file is
// arbitrary bytes off a disk and a chat message is untrusted text, so the rules their HTML lives under sit
// here, once, and both call sanitizeMd (plans/markdown-viewer.md, Slice 1: sanitize as GitHub does, 2026-09-07).
//
// What a note's or a message's HTML may do, modelled on GitHub's rules for a README (GitHub strips an inline
// `style` whole and allows no inline SVG; both survive here in the narrowed form described below):
//   • no <style> block, no <dialog>, and no form-associated element: a <style> blanked the whole viewer
//     (`.fileview { display: none }`), and a `<form action=...><button>` navigated the pane's document to
//     the action URL. style's text goes with it (DOMPurify's default FORBID_CONTENTS); a form's or a
//     button's TEXT stays as prose (KEEP_CONTENT), so a note reads the same minus the control.
//   • <input> survives ONLY as marked's task-list checkbox, `- [x] done` becomes <input checked disabled
//     type=checkbox>: every other input goes, and a checkbox that lacks `disabled` gets it, so nothing in
//     a note is a live control.
//   • an author's id and name are PREFIXED `user-content-` (SANITIZE_NAMED_PROPS, the rule GitHub applies):
//     a `<p id="tabs">` can no longer dress itself in the page's #tabs CSS or shadow getElementById for the
//     page's own controls, and `<a name="install">` still exists under its prefixed name. An `href="#install"`
//     is NOT rewritten to match: the chat's click delegate (render.ts) resolves a message's `#` click through
//     userContentTarget below, since the browser's default lookup reads the bare name and finds nothing, and
//     the viewer's fragmentTarget (file-view-links.ts) reads a section link inside a note through the same
//     lookup, adding its heading-slug arm. Rewriting hrefs here would break the viewer's section links: its
//     heading ids (`md-<slug>`, minted by mdBlock AFTER the sanitize) never gain the prefix, so a rewritten
//     `#user-content-results` would name nothing, where `[results](#results)` over `## Results` with no
//     `<a name>` above it lands on the heading id `md-results` (fragmentTarget's slug arm); with an
//     `<a name="results">` above the heading the link lands on that anchor under its prefixed name, whichever
//     spelling the href carries.
//   • an inline `style` keeps only `color` and `background-color` declarations whose value is a literal
//     colour: coloured spans in existing notes and transcripts survive; positioning, sizing and layout never
//     reach the page. Everything else in the attribute is dropped, and the attribute goes when nothing is
//     left: colorOnlyStyle below is the whole grammar, applied by a DOMPurify uponSanitizeAttribute hook on
//     every element, inline SVG included.
//   • data-* never rides in (ALLOW_DATA_ATTR: false): both pages key their delegated actions off data-act.
//   • an html comment is dropped, as GitHub drops it, and dropped BEFORE the element holding it is judged. DOMPurify
//     removes every comment on its own (no profile lists `#comment`), but its walk judges a parent before it reaches
//     the comment inside, and the parent's markup guard (SAFE_FOR_XML, its mXSS defence) reads the comment's `<!--`
//     in the innerHTML: a `<p>` or `<td>` holding a comment and a literal `<word` (`&lt;x&gt;`, which reads `<x` in
//     the textContent) matched the guard from two different children and vanished whole with its prose.
//     dropCommentChildren below, on the uponSanitizeElement hook, empties an element of its comments first; every
//     other output is unchanged, since no comment ever survived (Slice 5 review, round 4).
//   • an HTML `<title>` in the body is dropped with its text: the browser shows a title nowhere outside the page's head,
//     and DOMPurify's svg profile kept one as a hidden element whose text stood in the DOM. dropBodyTitle below, on the
//     same hook, removes the element before DOMPurify judges it; an inline svg's own `<title>` stays (Slice 5 review,
//     round 5).
//   • the `background` attribute is forbidden outright (FORBID_ATTR): `<td background=URL>` makes the browser
//     fetch the URL the moment the note renders, a tracking pixel with no click and no gate; DOMPurify's html
//     list keeps it, GitHub's allowlist does not, and it has no safe value here. `bgcolor` fetches nothing and
//     stays, as a colour-only inline style does. Remote figures (`<img src>`, video, audio, source) are decision
//     8's (plans/markdown-viewer.md): gated in Slice 4, where their src is rewritten.
//   • no image map: `<map>`, `<area>` and `usemap` go (FORBID_TAGS, FORBID_ATTR), as GitHub drops them. The
//     prefix rule renames `<map name="nav">` to user-content-nav and leaves `usemap="#nav"` as written, so no
//     map an author writes could bind to its picture anyway, and an <area> is a link element neither page's
//     link handling reaches. Dropped, the picture is inert prose.
//   • html + svg profiles (KaTeX's stretchy glyphs used to come through here as inline <svg>; a note's own
//     inline SVG still does), data: URIs on <img> (the CSP allows them; inline transcript images rely on them).
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
import type { Config, DOMPurify as DOMPurifyInstance, UponSanitizeAttributeHookEvent, UponSanitizeElementHookEvent } from "dompurify";

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
const COLOR_FN = /^(rgba?|hsla?)\(([^()]*)\)$/i;
const COLOR_ARG = /^(?:[+-]?(?:\d+\.?\d*|\.\d+)(?:%|deg|grad|rad|turn)?|none)$/i;
const KEPT_PROPERTIES = new Set(["color", "background-color"]);

/** Whether `v` (already trimmed) is a literal colour under the grammar above. */
export function isLiteralColor(v: string): boolean {
  if (KEYWORD.test(v) || HEX.test(v)) return true;
  const m = COLOR_FN.exec(v);
  if (!m) return false;
  const args = m[2].trim().split(/\s*[,/]\s*|\s+/).filter((a) => a.length > 0);
  return args.length >= 3 && args.length <= 4 && args.every((a) => COLOR_ARG.test(a));
}

/** The declarations of a `style` attribute that survive: `color` and `background-color` with a literal
 *  colour, in their order, as `name: value` joined by `; `. Empty when nothing survives (the caller drops
 *  the attribute). Splitting on `;` is safe because no surviving value can contain one. */
export function colorOnlyStyle(style: string): string {
  const kept: string[] = [];
  for (const decl of style.split(";")) {
    const at = decl.indexOf(":");
    if (at < 0) continue;
    const name = decl.slice(0, at).trim().toLowerCase();
    const value = decl.slice(at + 1).trim();
    if (!KEPT_PROPERTIES.has(name) || !value || !isLiteralColor(value)) continue;
    kept.push(name + ": " + value);
  }
  return kept.join("; ");
}

/** The DOMPurify uponSanitizeAttribute hook body: rewrites a `style` attribute to its colour
 *  declarations, drops it when none survive, and leaves every other attribute to DOMPurify. */
export function styleAttributeHook(ev: Pick<UponSanitizeAttributeHookEvent, "attrName" | "attrValue" | "keepAttr">): void {
  if (ev.attrName !== "style") return;
  const kept = colorOnlyStyle(ev.attrValue);
  if (kept) ev.attrValue = kept;
  else ev.keepAttr = false;
}

/** The DOMPurify uponSanitizeElement hook body: an element's html comment children go before DOMPurify judges the
 *  element. DOMPurify drops every comment itself (`#comment` is in no profile, so the walk removes one when it reaches
 *  it), but the walk is in document order, so a parent is judged with its comments still inside it, and one of the
 *  judgments reads them: the markup guard DOMPurify runs under SAFE_FOR_XML (its `_isUnsafeNode`, an mXSS defence)
 *  force-removes an element that has child nodes but no element child when BOTH its textContent and its innerHTML
 *  read as markup (`/<[/\w!]/`), the shape of a raw-text element whose text would re-parse as tags. A `<p>` or a
 *  `<td>` holding a comment and a literal `<word` matched both probes from two different children (marked emits
 *  `&lt;x&gt;` as the entity, so the textContent reads `<x`, and the comment verbatim, so the innerHTML reads `<!--`)
 *  and vanished whole with its prose: the table cell `a <!-- c --> b &lt;x&gt;` rendered as a row with one cell, and
 *  a comment on it painted nothing (the Slice 5 review, round 4, 2026-09-11; identical on main). With the comments
 *  gone first the guard reads the innerHTML DOMPurify would have produced anyway, so the element stays; for every
 *  other input the output is what it always was, since no comment ever survived the sanitize. The guard itself is
 *  untouched: a raw-text element's text is one text node, with no comment in it to drop. Reads `childNodes` as a
 *  snapshot and touches nothing but comments; DOMPurify removes a clobbered form before this hook runs for the names
 *  it probes (removeChild and nodeType among them), and `childNodes`, which it does not probe, is stepped back from
 *  here when a form's `<input name="childNodes">` has made it no list. */
export function dropCommentChildren(node: Node): void {
  if (node.nodeType !== 1 /* Node.ELEMENT_NODE */) return;
  const children = node.childNodes;
  if (!children || typeof children.length !== "number") return;
  for (const child of Array.from(children)) {
    if (child.nodeType === 8 /* Node.COMMENT_NODE */) node.removeChild(child);
  }
}

/** The HTML namespace, an element's `namespaceURI` when it is HTML's and not SVG's or MathML's. */
const HTML_NS = "http://www.w3.org/1999/xhtml";
/** The other DOMPurify uponSanitizeElement hook body: an HTML `<title>` in the body goes WITH its content. The browser never
 *  shows a title outside the page's head (the parser keeps one met in the body as an element the UA sheet hides, `title {
 *  display: none }`), but `title` is in DOMPurify's svg profile, so the namespace check kept a body `<title>` as a hidden
 *  element: a `<title>` block in a note, one inside a `<div>`, inline in a paragraph or in a table cell rendered nothing while
 *  its text stood in the DOM, in the comment painter's hay and in the fallback reader's text (which read it as shown), so a
 *  comment on that text painted a mark with no box and its card offered Scroll to nothing (the Slice 5 review, round 5). An
 *  svg's `<title>`, the drawing's own element in the SVG namespace, stays as it was. The hook removes the element itself, by
 *  the node's own `remove()`, right before DOMPurify judges it: the content goes with it (a title's content is one text node,
 *  the parser reading it as RCDATA), so no unwrapped text is left behind, and nothing shared is written. The first cut used
 *  the lever DOMPurify hands a hook, `allowedTags`, setting `title` off for a body title and on for an svg's; that set is
 *  DOMPurify's LIVE per-call ALLOWED_TAGS (`_sanitizeElements` passes the variable itself, no copy), so the write stood on every
 *  later element of the same call, and a hook reading the set after this one saw `title` false on the paragraphs after a body
 *  title. It reached no later `sanitize` call only because a call with a config rebuilds the set (`_parseConfig` clones the
 *  config and rebuilds ALLOWED_TAGS under USE_PROFILES), and under `setConfig`, which keeps one set across calls, it would
 *  have (the PR's review, round 1; md-sanitize-body-title-browser.test.ts pins both over the real DOMPurify). DOMPurify takes
 *  the removal as it takes its own: its walk's NodeIterator steps over a removed reference node (the DOM's pre-removing steps,
 *  the path `_forceRemove` relies on), and it goes on to judge the detached title as it goes on with every node it removes
 *  itself (3.4.10 reads no return value from `_sanitizeElements`), harmlessly: a title's innerHTML is escaped text, so the
 *  markup guard cannot match it, and an HTML title passes the namespace check under the stand-in parent DOMPurify uses for a
 *  parentless node, so neither branch reaches `_forceRemove`, which in 3.4.10 THROWS on a node it cannot detach (the browser
 *  leg sanitizes a title whose text reads as markup for this). `DOMPurify.removed` does not list the title; nothing here reads
 *  that list. The node's own `remove()` and not the parent's `removeChild`: only a form can be clobbered by a named control,
 *  so a title's method is the prototype's whatever its parent is. Reads `nodeType`, the hook's lower-cased tagName and
 *  `namespaceURI`. */
export function dropBodyTitle(node: Node, data: Pick<UponSanitizeElementHookEvent, "tagName">): void {
  if (data.tagName !== "title" || node.nodeType !== 1 /* Node.ELEMENT_NODE */ || (node as Element).namespaceURI !== HTML_NS) return;
  (node as Element).remove();
}

let hooksInstalled = false;
/** Install the two hooks on the (module-global) DOMPurify instance, once: the style rewrite on every attribute
 *  (styleAttributeHook) and, on every element, the comment drop (dropCommentChildren) and the body title's drop
 *  (dropBodyTitle). Idempotent: DOMPurify's hooks are a list, and a second registration would run the same rewrite twice
 *  per attribute. `purify` is a seam for the node tests, which have no window for the real instance to sanitize in. */
export function installMdSanitizeHooks(purify: Pick<DOMPurifyInstance, "addHook"> = DOMPurify): void {
  if (hooksInstalled) return;
  hooksInstalled = true;
  purify.addHook("uponSanitizeAttribute", (_node, ev) => { styleAttributeHook(ev); });
  purify.addHook("uponSanitizeElement", (node, data) => { dropCommentChildren(node); dropBodyTitle(node, data); });
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
