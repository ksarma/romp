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
//     is NOT rewritten to match: the viewer's fragment handler is the place that compares the prefixed form
//     (the #347 fold), and in the chat a `#` click falls to the browser's default lookup, which searches the
//     raw name and finds nothing (GitHub resolves the same gap in its page script). Rewriting hrefs here
//     would break the viewer's `<a name="results">` before `## Results` pattern, whose `#results` link lands
//     on the heading id `md-results`. The viewer's own heading ids (`md-<slug>`, mdBlock) are minted AFTER
//     the sanitize and never gain the prefix.
//   • an inline `style` keeps only `color` and `background-color` declarations whose value is a literal
//     colour (the user 2026-09-07, decision 6: coloured spans in existing notes survive; positioning and
//     layout never reach the page). Everything else in the attribute is dropped, and the attribute goes
//     when nothing is left: colourOnlyStyle below is the whole grammar, applied by a DOMPurify
//     uponSanitizeAttribute hook on every element, inline SVG included.
//   • data-* never rides in (ALLOW_DATA_ATTR: false): both pages key their delegated actions off data-act.
//   • the `background` attribute is forbidden outright (FORBID_ATTR, the profile's one forbidden attribute):
//     `<td background=URL>` makes the browser fetch the URL the moment the note renders, a tracking pixel with
//     no click and no gate, on both pages; DOMPurify's html list keeps it, GitHub's allowlist does not, and it
//     has no safe value here. `bgcolor` fetches nothing and stays, as a colour-only inline style does. Remote
//     figures (`<img src>`, video, audio, source) are decision 8's: gated in Slice 4, where their src is rewritten.
//   • html + svg profiles (the user 2026-08-19, when KaTeX's stretchy glyphs came through here as inline <svg>;
//     a note's own inline SVG still does), data: URIs on <img> (the CSP allows them; inline transcript images
//     rely on them).
//
// What does NOT pass through here: KaTeX. Its layout is all inline style, which the colour-only rule would
// strip, so the math extensions emit an inert placeholder and the caller renders KaTeX into it on the
// sanitized DOM afterwards (math.ts renderMathPlaceholders; the chat's md() and userMd() today, the viewer
// once KaTeX ships in its bundle). A renderer romp itself runs never goes through the sanitizer; only what
// an author wrote does.
import DOMPurify from "dompurify";
import type { Config, DOMPurify as DOMPurifyInstance, UponSanitizeAttributeHookEvent } from "dompurify";

/** Tags a note may not keep: the style sheet, the dialog, and every form-associated element. */
export const MD_FORBID_TAGS: readonly string[] = [
  "style", "dialog",
  "form", "button", "select", "option", "optgroup", "textarea", "fieldset", "legend", "label", "datalist", "output", "meter", "progress",
];

/** Attributes a note may not keep at all: `background`, a remote fetch on render with no safe value. Every other
 *  attribute the profiles allow either is safe as written or is rewritten (id and name prefixed, style filtered). */
export const MD_FORBID_ATTR: readonly string[] = ["background"];

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

/** Sanitize marked's HTML under the profile above and return the sanitized <body>: its children are the
 *  nodes to adopt (mdBlock) or its innerHTML the string to set (md, userMd), after any DOM post-pass of
 *  the caller's own (the math placeholders, PR links, heading ids). The only DOMPurify.sanitize call in
 *  the dashboard's source. */
export function sanitizeMd(dirty: string): HTMLElement {
  installMdSanitizeHooks();
  const clean = DOMPurify.sanitize(dirty, { ...MD_PURIFY, RETURN_DOM: true }) as HTMLElement;   // the sanitized <body>
  keepOnlyInertCheckboxes(clean);
  return clean;
}
