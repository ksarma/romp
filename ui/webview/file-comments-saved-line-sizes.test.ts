// The saved line's COMPUTED em sizes (hiddenSavedRow; the filter follow-on to plans/file-review.md, 2026-09-07). The row
// first wore .fc-note itself (0.86em) with its ✕, a .fileview-btn (0.82em), inside it, so the button rendered at 0.705em:
// off the sheets' ladder, and visibly smaller than every other panel button — the err row's ✕ the same list can show a
// line below is compensated (.fileview-err .fileview-btn) and Track changes sits in an unsized row (ui/CLAUDE.md, font
// sizes: nesting em compounds; prefer flat contexts or compensate explicitly). The class is on the words' span now, the row
// unsized, as the confirm rows have it. styles-fc-computed-sizes.test.ts could not see this: it parses the panel block
// alone, and .fileview-btn's rule sits outside it; the sheets' ladder tests read declared literals. This resolves the
// cascade over the WHOLE sheet along the real ancestry, the way styles-fileview-err-sizes.test.ts does (its resolver,
// copied), for the saved row's ✕ and words beside the buttons and words they must match. Both sheets — the feed page loads
// only feed.css. The about follow-on (plans/file-review.md decision 46, 2026-09-10) put Resolve answered in the head's
// action row after Comment on this file, a default-class button, with its confirm a .fc-row.fc-choice under the toggles
// like the Track choice: both are on the chains below, and the DOM pin reads the row with that block between the last
// button and the row's append. Synthetic: only the repo's own text.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const read = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const PANEL = read("file-comments.ts");
const SHEETS = [["styles.css", read("styles.css")], ["feed.css", read("feed.css")]] as const;
const LADDER = [0.66, 0.7, 0.72, 0.82, 0.86, 0.92];   // the sheets' em ladder (css-vocab.test.ts)

// ── a whole-sheet cascade resolver: the selector grammar the sheets' font-size rules use, loud about the rest ──
type Compound = { tag: string | null; id: string | null; classes: string[]; nots: Compound[]; pseudoElement: boolean };
type Complex = { parts: Compound[]; combinators: string[]; specificity: number };   // combinators[k] sits between parts[k] and parts[k + 1]
type Size = { kind: "em"; factor: number } | { kind: "abs"; text: string };
type Rule = { selectors: Complex[]; size: Size; order: number; conditional: string | null; text: string };
type Node = { tag: string; id: string | null; classes: string[] };

function parseCompound(s: string, where: string): Compound {
  const c: Compound = { tag: null, id: null, classes: [], nots: [], pseudoElement: false };
  let i = 0;
  const t = /^[a-zA-Z][\w-]*/.exec(s);
  if (t) { c.tag = t[0].toLowerCase(); i = t[0].length; }
  while (i < s.length) {
    const rest = s.slice(i);
    let m: RegExpExecArray | null;
    if ((m = /^\.([\w-]+)/.exec(rest))) { c.classes.push(m[1]); i += m[0].length; continue; }
    if ((m = /^#([\w-]+)/.exec(rest))) { c.id = m[1]; i += m[0].length; continue; }
    if ((m = /^::?(before|after|placeholder|marker|selection)\b/.exec(rest))) { c.pseudoElement = true; i += m[0].length; continue; }
    if (rest.startsWith(":not(")) {
      const end = s.indexOf(")", i);
      assert.ok(end > i, "unterminated :not( in `" + where + "`");
      const inner = s.slice(i + 5, end);
      assert.doesNotMatch(inner, /,/, ":not() with a list is not resolved here: `" + where + "`");
      c.nots.push(parseCompound(inner, where)); i = end + 1; continue;
    }
    assert.fail("a font-size rule uses selector syntax this resolver does not model (`" + where + "`); extend it");
  }
  return c;
}
const specOf = (c: Compound): number => (c.id ? 10000 : 0) + c.classes.length * 100 + (c.tag ? 1 : 0) + c.nots.reduce((n, x) => n + specOf(x), 0);
function parseComplex(sel: string, where: string): Complex {
  const toks = sel.trim().replace(/\s*>\s*/g, " > ").split(/\s+/);
  const cx: Complex = { parts: [], combinators: [], specificity: 0 };
  let pending: string | null = null;
  for (const tok of toks) {
    if (tok === ">") { pending = ">"; continue; }
    if (cx.parts.length) cx.combinators.push(pending || " ");
    cx.parts.push(parseCompound(tok, where)); pending = null;
  }
  assert.ok(cx.parts.length > 0 && pending === null, "a bare combinator in `" + where + "`");
  cx.specificity = cx.parts.reduce((n, p) => n + specOf(p), 0);
  return cx;
}
/** a selector list split on its top-level commas */
function splitList(sel: string): string[] {
  const out: string[] = []; let depth = 0, cur = "";
  for (const ch of sel) {
    if (ch === "(") depth++; else if (ch === ")") depth--;
    if (ch === "," && depth === 0) { out.push(cur); cur = ""; } else cur += ch;
  }
  out.push(cur);
  return out.map((x) => x.trim()).filter(Boolean);
}
/** the size a declaration block sets, if any: an em factor (a plain em, or calc(<em> / <number>)), else absolute */
function sizeOf(body: string): Size | null {
  let size: Size | null = null;
  for (const d of body.split(";").map((x) => x.trim()).filter(Boolean)) {
    const colon = d.indexOf(":"); if (colon < 0) continue;
    const prop = d.slice(0, colon).trim().toLowerCase(), val = d.slice(colon + 1).trim();
    if (prop === "font") { if (val !== "inherit") size = { kind: "abs", text: d }; continue; }   // a shorthand with a size resets
    if (prop !== "font-size") continue;
    let m: RegExpExecArray | null;
    if ((m = /^(\d*\.?\d+)em$/.exec(val))) size = { kind: "em", factor: parseFloat(m[1]) };
    else if ((m = /^calc\(\s*(\d*\.?\d+)em\s*\/\s*(\d*\.?\d+)\s*\)$/.exec(val))) size = { kind: "em", factor: parseFloat(m[1]) / parseFloat(m[2]) };
    else size = { kind: "abs", text: d };
  }
  return size;
}
/** every rule in the sheet that sets a font size, at-rules descended (and remembered: a conditional size is not at-rest) */
function parseSheet(css: string): Rule[] {
  const rules: Rule[] = []; let order = 0;
  const walk = (s: string, cond: string | null) => {
    let i = 0;
    while (i < s.length) {
      if (/\s/.test(s[i])) { i++; continue; }
      const open = s.indexOf("{", i);
      assert.ok(open > i, "a rule without braces at `" + s.slice(i, i + 40) + "`");
      const head = s.slice(i, open).trim();
      let depth = 0, j = open;
      for (; j < s.length; j++) { if (s[j] === "{") depth++; else if (s[j] === "}" && --depth === 0) break; }
      assert.ok(j < s.length, "unbalanced braces after `" + head + "`");
      const body = s.slice(open + 1, j); i = j + 1;
      if (head.startsWith("@")) {
        if (/^@(media|container|supports)\b/.test(head)) walk(body, cond ? cond + " " + head : head);
        continue;   // @keyframes, @font-face, @property: no element rules inside
      }
      order++;
      const size = sizeOf(body);
      if (!size) continue;
      rules.push({ selectors: splitList(head).map((x) => parseComplex(x, head)), size, order, conditional: cond, text: head });
    }
  };
  walk(css.replace(/\/\*[\s\S]*?\*\//g, ""), null);
  return rules;
}
const matchCompound = (c: Compound, n: Node): boolean => !c.pseudoElement
  && (c.tag === null || c.tag === n.tag) && (c.id === null || c.id === n.id)
  && c.classes.every((k) => n.classes.includes(k)) && c.nots.every((x) => !matchCompound(x, n));
function matchAt(cx: Complex, chain: Node[], i: number, k: number): boolean {
  if (!matchCompound(cx.parts[k], chain[i])) return false;
  if (k === 0) return true;
  if (cx.combinators[k - 1] === ">") return i > 0 && matchAt(cx, chain, i - 1, k - 1);
  for (let j = i - 1; j >= 0; j--) if (matchAt(cx, chain, j, k - 1)) return true;
  return false;
}
/** the winning font-size rule for chain[i] (specificity of the matching selector, then source order), or null */
function ruleFor(rules: Rule[], chain: Node[], i: number): Rule | null {
  let best: Rule | null = null, bestSpec = -1;
  for (const r of rules) {
    for (const cx of r.selectors) {
      if (!matchAt(cx, chain, i, cx.parts.length - 1)) continue;
      if (!best || cx.specificity > bestSpec || (cx.specificity === bestSpec && r.order > best.order)) { best = r; bestSpec = cx.specificity; }
    }
  }
  return best;
}
/** "html > body.fileview-open > div#romp-fileview > div.fileview" → nodes, root first */
const chainOf = (s: string): Node[] => s.split(">").map((p) => {
  const m = /^([a-z][\w-]*)(#[\w-]+)?((?:\.[\w-]+)*)$/.exec(p.trim());
  assert.ok(m, "a chain element this test cannot read: " + p);
  return { tag: m![1], id: m![2] ? m![2].slice(1) : null, classes: m![3] ? m![3].slice(1).split(".") : [] };
});
const describe = (n: Node) => n.tag + (n.id ? "#" + n.id : "") + n.classes.map((c) => "." + c).join("");
/** the leaf's size in units of the page base (html/body's own), and the rules that sized the chain */
function computed(rules: Rule[], chain: Node[]): { size: number; sized: string[] } {
  let size = 1; const sized: string[] = [];
  chain.forEach((n, i) => {
    const r = ruleFor(rules, chain, i);
    if (!r) return;
    assert.equal(r.conditional, null, "`" + r.text + "` sizes " + describe(n) + " under " + r.conditional + "; this resolver models at-rest sizes only");
    if (r.size.kind === "abs") {
      assert.ok(n.tag === "html" || n.tag === "body", "`" + r.text + "` sets " + describe(n) + " to `" + r.size.text + "`, a size this resolver cannot multiply");
      size = 1; return;   // the page base
    }
    size *= r.size.factor; sized.push(r.text);
  });
  return { size, sized };
}

// ── the chains, as file-comments.ts builds them (the ancestry above the panel is styles-fileview-err-sizes.test.ts's, pinned there) ──
const ROOT = "html > body.fileview-open > div#romp-fileview > div.fileview";
const ASIDE = ROOT + " > div.fileview-main > div.fc-panel.fileview-aside";
const HEAD = ASIDE + " > div.fc-sec-head > div.fc-head";
const LIST = ASIDE + " > div.fc-sec-cards > div.fc-cards";
const SAVED = LIST + " > div.fc-row.fc-saved-hidden";
// the ✕ beside the buttons it must match: the head's toggles in their unsized row, the confirms' buttons, and the err row's
// ✕ that the Changes empty state shows under the saved line after a refused Accept all (strayRows)
const BUTTONS: Record<string, string> = {
  "saved line ✕": SAVED + " > button.fileview-btn.fc-x",
  "panel Track changes": HEAD + " > div.fc-row > button.fileview-btn.fc-toggle",
  "panel Comment on this file": HEAD + " > div.fc-row > button.fileview-btn",
  "panel Resolve answered (N)": HEAD + " > div.fc-row > button.fileview-btn",
  "Track scope / Stop / Resolve answered confirm buttons": HEAD + " > div.fc-row.fc-choice > button.fileview-btn",
  "list error ✕ (Nothing decided, under the Changes empty line)": LIST + " > div.fileview-err.fc-err > button.fileview-btn.fc-x",
};
// the words beside the words they must match: every .fc-note in the panel is the one size
const WORDS: Record<string, string> = {
  "saved line words": SAVED + " > span.fc-note",
  "Stop confirm words": HEAD + " > div.fc-row.fc-choice > span.fc-note",
  "Resolve answered confirm words": HEAD + " > div.fc-row.fc-choice > span.fc-note",
  "Changes empty line": LIST + " > div.fc-empty",
};
// the shape the slice first built, which no test resolved: the class on the row, the ✕ under it
const ROW_DRESSED = LIST + " > div.fc-row.fc-note.fc-saved-hidden > button.fileview-btn.fc-x";

test("the chains above are the real DOM: hiddenSavedRow, renderCards, the head's rows and the confirms in file-comments.ts", () => {
  assert.match(PANEL, /const list = el\("div", "fc-cards"\);/);
  assert.match(PANEL, /const saved = this\.hiddenSavedRow\(filter\);[^\n]*\n\s*if \(saved\) list\.appendChild\(saved\);/, "the saved row is the list's child");
  assert.match(PANEL, /const row = el\("div", "fc-row fc-saved-hidden"\);\n\s*row\.dataset\.id = card\.id;\n\s*row\.appendChild\(el\("span", "fc-note", "Your comment is saved; its card"/, "the row unsized, .fc-note on the words' span");
  assert.match(PANEL, /const x = btn\("✕", "fchiddenx", "fileview-btn fc-x"\); x\.setAttribute\("aria-label", "Dismiss"\); row\.appendChild\(x\);/, "the ✕ is the row's own child");
  assert.match(PANEL, /list\.appendChild\(el\("div", "fc-empty", "No changes are pending\. All or Comments above shows the comments\."\)\);\n\s*for \(const n of this\.strayRows\(list, \["change:", "changes", "card:"\]\)\) list\.appendChild\(n\);/, "the empty line and the stray err rows are the list's children too");
  assert.match(PANEL, /const row = el\("div", "fileview-err fc-err" \+ \(e\.warn \? " fc-err-warn" : ""\)\);[\s\S]*?const x = btn\("✕", "fcerrx", "fileview-btn fc-x"\);[^\n]*row\.appendChild\(x\);/, "an err row's ✕");
  assert.match(PANEL, /const head = el\("div", "fc-head"\);\n\s*const row = el\("div", "fc-row"\);\n\s*const t = btn\("Track changes", "fctrack", "fileview-btn fc-toggle"\);/);
  // the action row's tail: Comment on this file, then the Resolve answered block (decision 46), its button default-class and
  // appended to the SAME row inside the block's braces, and then the row goes to the head; nothing else stands between
  assert.match(PANEL, /row\.appendChild\(btn\("Comment on this file", "fcfile"\)\);\n(?:\s*\/\/[^\n]*\n)*\s*const answered = s \? answeredComments\(this\.cards\(\)\) : \[\];\n\s*if \(answered\.length \|\| this\.resolvingAnswered\) \{\n\s*const ra = btn\([^\n]*, "fcresolveanswered"\);\n(?:\s*ra\.[^\n]*\n)*\s*row\.appendChild\(ra\);\n\s*\}\n\s*head\.appendChild\(row\);/, "Comment on this file and Resolve answered are the action row's children, and the row is the head's");
  assert.match(PANEL, /const ask = el\("div", "fc-row fc-choice"\);\n\s*ask\.appendChild\(el\("span", "fc-note", resolveAnsweredAsk\(answered\.length\)\)\);\n\s*ask\.appendChild\(btn\("Resolve", "fcresolveanswereddo"\)\);\n\s*ask\.appendChild\(btn\("Cancel", "fcresolveansweredcancel"\)\);\n\s*underToggles\(ask\);/, "the Resolve answered confirm: the class on its span, its buttons the row's children, the row the head's");
  assert.match(PANEL, /const stop = el\("div", "fc-row fc-choice"\);\n\s*const ask = el\("span", "fc-note", "Stop tracking everything under "\);/, "the Stop confirm: the class on its span");
  assert.match(PANEL, /stop\.appendChild\(btn\("Stop", "fctrackstop"\)\);\n\s*stop\.appendChild\(btn\("Cancel", "fctrackcancel"\)\);\n\s*underToggles\(stop\);/, "…its buttons the row's children, the row the head's");
  assert.match(PANEL, /function btn\(label: string, act: string, cls = "fileview-btn"\)/);
});

for (const [name, css] of SHEETS) {
  const rules = parseSheet(css);
  const factor = (sel: string): number => {
    const r = rules.find((x) => x.text === sel);
    assert.ok(r && r.size.kind === "em", "the " + sel + " rule sizes in em");
    return (r!.size as { factor: number }).factor;
  };

  test(name + ": the saved line's ✕ computes to the one button size, the size of Track changes and of the err row's ✕ under it", () => {
    const button = factor(".fileview-btn");
    for (const [label, chain] of Object.entries(BUTTONS)) {
      const { size, sized } = computed(rules, chainOf(chain));
      assert.ok(Math.abs(size - button) < 1e-9, label + " renders at " + size.toFixed(4) + "em of the viewer, not the " + button + "em every other button wears (sized by: " + sized.join(" · ") + ")");
      assert.ok(LADDER.some((v) => Math.abs(v - size) < 1e-9), label + " computes to " + size.toFixed(4) + "em, off the ladder " + LADDER.join("/"));
    }
  });

  test(name + ": the saved line's words compute to the size .fc-note sets, one size on the chain, as the confirm's words and the empty line do", () => {
    const note = factor(".fc-note");
    for (const [label, chain] of Object.entries(WORDS)) {
      const { size, sized } = computed(rules, chainOf(chain));
      assert.ok(Math.abs(size - note) < 1e-9, label + " render at " + size.toFixed(4) + "em (sized by: " + sized.join(" · ") + ")");
      assert.equal(sized.length, 1, label + ": one size on the chain");
      assert.ok(LADDER.some((v) => Math.abs(v - size) < 1e-9), label + " computes to " + size.toFixed(4) + "em, off the ladder " + LADDER.join("/"));
    }
  });

  test(name + ": the shape the slice first built would compound — the class on the row puts its ✕ off the ladder — so the row stays unsized rather than a compensating rule being added for it", () => {
    const { size, sized } = computed(rules, chainOf(ROW_DRESSED));
    assert.ok(Math.abs(size - factor(".fileview-btn") * factor(".fc-note")) < 1e-9, "a .fileview-btn under a .fc-note row: both rules size the chain (" + sized.join(" · ") + ")");
    assert.ok(!LADDER.some((v) => Math.abs(v - size) < 1e-9), "…and " + size.toFixed(4) + "em is on no rung");
    assert.doesNotMatch(css, /\.fc-saved-hidden[^{]*\{[^}]*font-size/, "no rule sizes the saved row or anything under it: the flat context is the fix (ui/CLAUDE.md), not a second compensation");
  });
}
