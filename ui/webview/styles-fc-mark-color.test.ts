// The ink of a file-comment highlight. anchor-map.ts paints every located comment, and the composer's pending
// selection, as a <mark> element, and the UA stylesheet gives a mark its OWN ink: `mark { color: MarkText }`
// (black in Chromium, Firefox and WebKit). That is a declaration on the element itself, so it beats anything the
// passage would inherit — the body's text colour, an hljs token colour, the link ink under .fileview-md a — and an
// author rule of ANY specificity beats it back, because author origin wins over UA origin in the cascade. The
// .fc-hl / .fc-presel rules first shipped with background, ring, radius and padding only, so in the dark theme a
// commented passage read as near-black glyphs over a 14% amber wash (about 1.6:1), and a code token or a link
// under the ring lost its colour. The chat's own highlight had solved this (mark.cmt-hl { color: inherit }).
//
// The sheets' other tests read declared literals along a rule; this one resolves `color` on the mark the way an
// engine would — UA default unless an author rule matching the element declares it — over the WHOLE sheet, since a
// stray `mark { color: … }` or a view-scoped rule anywhere would decide the ink just the same. Both sheets, since
// the feed page loads only feed.css. The class strings come from file-comments.ts's paint call sites and the
// element name from anchor-map's makeMark, pinned below so the model cannot outlive the DOM it describes.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const read = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = read("file-comments.ts");
const MAP = read("anchor-map.ts");
const SHEETS = [["styles.css", read("styles.css")], ["feed.css", read("feed.css")]] as const;

/** what the UA sheet declares on a bare <mark>, in every engine — the value an unstyled highlight computes to */
const UA_MARK_COLOR = "MarkText";

// ── the marks, as the code builds them ────────────────────────────────────────────────────────────────────────
type Node = { tag: string; classes: string[] };

/** the class strings file-comments.ts hands anchor-map for a comment's highlight (located; located by context) and
 *  for the composer's pending target — read from the source, so a renamed or added class reaches the model */
function markClasses(): Record<string, string[]> {
  const hl = /const cls = "([\w-]+)" \+ \(loc\.state === "context" \? " ([\w-]+)" : ""\);/.exec(SRC);
  assert.ok(hl, "the highlight pass builds its class string as base + optional context class");
  const raw = /paintRaw\(root, src, c\.range, "([\w-]+)"\)/.exec(SRC);
  const rendered = /paintRendered\(root, src, c\.range, "([\w-]+)"\)/.exec(SRC);
  assert.ok(raw && rendered, "the presel paints in both views");
  assert.equal(raw![1], rendered![1], "one presel class for both views");
  return { "comment highlight": [hl![1]], "highlight located by context": [hl![1], hl![2]], "composer presel": [raw![1]] };
}

test("anchor-map paints highlights as <mark> elements carrying exactly the class string it is handed", () => {
  const makeMark = MAP.slice(MAP.indexOf("function makeMark("), MAP.indexOf("function wrapNode("));
  assert.match(makeMark, /const m = doc\.createElement\("mark"\);/, "the element the UA's mark rule applies to");
  assert.match(makeMark, /m\.setAttribute\("class", className\);/, "no class of its own — only the caller's");
  assert.match(MAP, /const m = makeMark\(\(parent as DElement\)\.ownerDocument, className, data\);/, "wrapNode routes the caller's class");
  assert.match(MAP, /export function paintRaw\(codeRoot: Element, source: string, range: SourceRange, className: string,/);
  assert.match(MAP, /export function paintRendered\(renderedRoot: Element, source: string, range: SourceRange, className: string,/);
  const classes = markClasses();
  assert.deepEqual(classes["comment highlight"], ["fc-hl"]);
  assert.deepEqual(classes["highlight located by context"], ["fc-hl", "fc-hl-context"]);
  assert.deepEqual(classes["composer presel"], ["fc-presel"]);
});

// ── a small cascade model for one property on one element: the sheet's `color` rules whose subject can be the mark ──
type Rule = { selector: string; value: string; important: boolean; specificity: number; order: number; gated: boolean };   // one selector each
type Subject = { tag: string | null; classes: string[]; ids: number; attrs: number; pseudos: string[]; pseudoElement: boolean };

const stripComments = (css: string) => css.replace(/\/\*[\s\S]*?\*\//g, "");

/** every rule with a `color` declaration, at-rule blocks descended (@media/@container gate a rule; @keyframes and
 *  @font-face hold no selectors and are skipped whole; statement at-rules end at their semicolon) */
function colorRules(css: string): Rule[] {
  const out: Rule[] = [];
  let order = 0;
  const walk = (block: string, gated: boolean) => {
    let i = 0;
    while (i < block.length) {
      if (/\s/.test(block[i])) { i++; continue; }
      const open = block.indexOf("{", i), semi = block.indexOf(";", i);
      if (block[i] === "@" && semi >= 0 && (open < 0 || semi < open)) { i = semi + 1; continue; }   // @import, @charset
      assert.ok(open > i, "a rule without an opening brace at: " + block.slice(i, i + 60));
      const close = matchingClose(block, open);
      const prelude = block.slice(i, open).trim(), body = block.slice(open + 1, close);
      i = close + 1;
      if (prelude.startsWith("@")) {
        if (/^@(keyframes|-webkit-keyframes|font-face|property|page|counter-style)\b/.test(prelude)) continue;
        assert.match(prelude, /^@(media|container|supports|layer|scope)\b/, "an at-rule this model does not know: " + prelude);
        walk(body, true);
        continue;
      }
      order++;
      for (const d of splitTop(body, ";")) {
        const m = /^color\s*:\s*([\s\S]+?)\s*(!important)?$/.exec(d.trim());
        if (!m) continue;
        for (const selector of splitTop(prelude, ",")) {   // one rule per selector: specificity is per selector, not per list
          const [b, t] = specificityOf(selector);
          out.push({ selector, value: m[1].trim(), important: !!m[2], specificity: b * 1000 + t, order, gated });
        }
      }
    }
  };
  walk(stripComments(css), false);
  return out;
}
function matchingClose(s: string, open: number): number {
  let depth = 0, quote: string | null = null;
  for (let j = open; j < s.length; j++) {
    const ch = s[j];
    if (quote) { if (ch === "\\") j++; else if (ch === quote) quote = null; continue; }
    if (ch === '"' || ch === "'") { quote = ch; continue; }
    if (ch === "{") depth++;
    else if (ch === "}" && --depth === 0) return j;
  }
  assert.fail("an unclosed block at " + s.slice(open, open + 60));
}
/** split at `sep` outside parentheses, brackets and quotes */
function splitTop(s: string, sep: string): string[] {
  const parts: string[] = [];
  let depth = 0, quote: string | null = null, start = 0;
  for (let j = 0; j < s.length; j++) {
    const ch = s[j];
    if (quote) { if (ch === "\\") j++; else if (ch === quote) quote = null; continue; }
    if (ch === '"' || ch === "'") { quote = ch; continue; }
    if (ch === "(" || ch === "[") depth++;
    else if (ch === ")" || ch === "]") depth--;
    else if (ch === sep && depth === 0) { parts.push(s.slice(start, j)); start = j + 1; }
  }
  parts.push(s.slice(start));
  return parts.map((p) => p.trim()).filter(Boolean);
}
/** the compound after the last top-level combinator: the element the rule styles */
function subjectOf(selector: string): { text: string; hasAncestors: boolean } {
  let depth = 0, quote: string | null = null, cut = -1;
  for (let j = 0; j < selector.length; j++) {
    const ch = selector[j];
    if (quote) { if (ch === "\\") j++; else if (ch === quote) quote = null; continue; }
    if (ch === '"' || ch === "'") { quote = ch; continue; }
    if (ch === "(" || ch === "[") depth++;
    else if (ch === ")" || ch === "]") depth--;
    else if (depth === 0 && /[\s>+~]/.test(ch)) cut = j;
  }
  return { text: selector.slice(cut + 1), hasAncestors: cut >= 0 };
}
function parseSubject(text: string): Subject {
  const s: Subject = { tag: null, classes: [], ids: 0, attrs: 0, pseudos: [], pseudoElement: false };
  let i = 0;
  const t = /^(\*|[a-zA-Z][\w-]*)/.exec(text);
  if (t) { s.tag = t[1].toLowerCase(); i = t[0].length; }
  while (i < text.length) {
    const rest = text.slice(i);
    let m: RegExpExecArray | null;
    if ((m = /^\.([\w-]+)/.exec(rest))) { s.classes.push(m[1]); i += m[0].length; continue; }
    if ((m = /^#([\w-]+)/.exec(rest))) { s.ids++; i += m[0].length; continue; }
    if (rest.startsWith("[")) { const end = closeOf(text, i, "[", "]"); s.attrs++; i = end + 1; continue; }
    if ((m = /^::?([\w-]+)/.exec(rest))) {
      const dbl = rest.startsWith("::"), name = m[1].toLowerCase();
      i += m[0].length;
      if (text[i] === "(") i = closeOf(text, i, "(", ")") + 1;
      if (dbl || ["before", "after", "first-line", "first-letter"].includes(name)) s.pseudoElement = true;
      else s.pseudos.push(name);
      continue;
    }
    assert.fail("a color rule's subject uses selector syntax this model does not read (" + text + "); extend it");
  }
  return s;
}
function closeOf(s: string, at: number, open: string, close: string): number {
  let depth = 0;
  for (let j = at; j < s.length; j++) { if (s[j] === open) depth++; else if (s[j] === close && --depth === 0) return j; }
  assert.fail("unbalanced " + open + " in " + s);
}
/** (ids, classes+attrs+pseudo-classes, tags) summed over a selector's compounds; one selector at a time */
function specificityOf(selector: string): [number, number] {
  let b = 0, t = 0;
  for (const compound of selector.replace(/\s*[>+~]\s*/g, " ").split(/\s+/).filter(Boolean)) {
    const sub = parseSubject(compound);
    b += sub.classes.length + sub.ids * 1000 + sub.attrs + sub.pseudos.filter((p) => !["not", "is", "where"].includes(p)).length;
    t += sub.tag && sub.tag !== "*" ? 1 : 0;
  }
  return [b, t];
}
/** can this selector's subject be the mark? "sure" needs no ancestor, state or attribute; "maybe" depends on one */
function matches(selector: string, node: Node): "sure" | "maybe" | "no" {
  const { text, hasAncestors } = subjectOf(selector);
  const sub = parseSubject(text);
  if (sub.pseudoElement) return "no";
  if (sub.tag && sub.tag !== "*" && sub.tag !== node.tag) return "no";
  if (sub.ids) return "no";
  if (!sub.classes.every((c) => node.classes.includes(c))) return "no";
  return hasAncestors || sub.attrs || sub.pseudos.length ? "maybe" : "sure";
}
/** the mark's computed `color`: the winning author declaration that surely applies, else the UA's */
function computedColor(rules: Rule[], node: Node): { value: string; by: string | null } {
  let best: Rule | null = null;
  for (const r of rules) {
    if (r.gated) continue;
    if (matches(r.selector, node) !== "sure") continue;
    const beats = !best || (r.important && !best.important) ||
      (r.important === best.important && (r.specificity > best.specificity || (r.specificity === best.specificity && r.order > best.order)));
    if (beats) best = r;
  }
  return best ? { value: best.value, by: best.selector } : { value: UA_MARK_COLOR, by: null };
}

for (const [name, css] of SHEETS) {
  test(name + ": every highlight mark keeps the passage's own ink (color: inherit), in either view, never the UA's MarkText", () => {
    const rules = colorRules(css);
    assert.ok(rules.length > 50, "the model read the sheet's color rules (" + rules.length + ")");
    for (const [label, classes] of Object.entries(markClasses())) {
      const node: Node = { tag: "mark", classes };
      const { value, by } = computedColor(rules, node);
      assert.notEqual(value, UA_MARK_COLOR, label + " (mark." + classes.join(".") + "): no author rule declares its color, so the UA's " +
        "mark { color: MarkText } wins over the passage's inherited ink — black glyphs over the wash");
      assert.equal(value, "inherit", label + ": `" + by + "` paints the ink " + value + "; a highlight is a ring around the passage's own " +
        "text (hljs tokens, link ink), so the only right value is inherit");
    }
  });

  test(name + ": no rule anywhere re-fixes a highlight mark's ink in one view or media state", () => {
    // a `.fileview-md .fc-hl { color: … }` or a gated twin would pass the check above and still turn the ink in the
    // one view it scopes to; states (:hover, :focus…) and attribute gates are a design choice and are not judged here
    const rules = colorRules(css);
    for (const [label, classes] of Object.entries(markClasses())) {
      const node: Node = { tag: "mark", classes };
      for (const r of rules) {
        if (matches(r.selector, node) === "no") continue;
        const sub = parseSubject(subjectOf(r.selector).text);
        if (sub.pseudos.length || sub.attrs) continue;
        assert.equal(r.value, "inherit", label + ": `" + r.selector + "`" + (r.gated ? " (inside an at-rule)" : "") + " sets color: " + r.value);
      }
    }
  });
}

test("the model itself: a sheet with a ring but no ink resolves to the UA's MarkText; a bare-class inherit beats it; ancestors and states do not count as sure", () => {
  const ringOnly = ".fc-hl { background: red; box-shadow: inset 0 0 0 1px red; }";
  assert.deepEqual(computedColor(colorRules(ringOnly), { tag: "mark", classes: ["fc-hl"] }), { value: UA_MARK_COLOR, by: null });
  const fixed = ringOnly + "\n.fc-hl { color: inherit; }";
  assert.deepEqual(computedColor(colorRules(fixed), { tag: "mark", classes: ["fc-hl", "fc-hl-context"] }), { value: "inherit", by: ".fc-hl" });
  // a view-scoped or hover rule is not a sure match, so it neither rescues nor decides the base ink
  const scoped = ringOnly + "\n.fileview-md .fc-hl { color: inherit; }\n.fc-hl:hover { color: inherit; }\nmark.cmt-hl { color: inherit; }";
  assert.deepEqual(computedColor(colorRules(scoped), { tag: "mark", classes: ["fc-hl"] }), { value: UA_MARK_COLOR, by: null });
  assert.equal(matches(".fileview-md .fc-hl", { tag: "mark", classes: ["fc-hl"] }), "maybe");
  assert.equal(matches("mark.cmt-hl", { tag: "mark", classes: ["fc-hl"] }), "no", "the chat's highlight class is not ours");
  assert.equal(matches("span.fc-hl", { tag: "mark", classes: ["fc-hl"] }), "no", "another element's rule");
  assert.equal(matches("::highlight(cite-span)", { tag: "mark", classes: ["fc-hl"] }), "no", "a pseudo-element is not the mark");
  assert.equal(matches("*", { tag: "mark", classes: ["fc-hl"] }), "sure");
  // specificity, then order; !important over both; a gated rule never decides the base ink
  const fight = ".fc-hl { color: inherit; }\nmark.fc-hl { color: red; }\n.fc-hl { color: blue; }";
  assert.equal(computedColor(colorRules(fight), { tag: "mark", classes: ["fc-hl"] }).by, "mark.fc-hl");
  assert.equal(computedColor(colorRules(".fc-hl { color: blue !important; }\nmark.fc-hl { color: red; }"), { tag: "mark", classes: ["fc-hl"] }).value, "blue");
  assert.equal(computedColor(colorRules("@media (max-width: 600px) { .fc-hl { color: inherit; } }"), { tag: "mark", classes: ["fc-hl"] }).value, UA_MARK_COLOR);
  // rules inside a gated block are still read (the second test judges them); keyframes and font-face are not selectors
  assert.equal(colorRules("@media (x) { .fc-hl { color: red; } }")[0].gated, true);
  assert.equal(colorRules("@keyframes k { from { color: red; } to { color: blue; } }\n@font-face { font-family: x; }\n@import \"x.css\";").length, 0);
});
