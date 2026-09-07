// The comments panel's COMPUTED em sizes, along the DOM chains file-comments.ts actually builds. The sheets'
// ladder tests (file-comments.test.ts, css-vocab.test.ts) read declared literals, so a 0.72em .fc-time nested in
// a 0.86em .fc-log-row passed them while rendering at 0.62em: off the ladder, and visibly smaller than the same
// .fc-time on a card head, both stamped by the one clock() helper (ui/CLAUDE.md, font sizes: nesting em
// compounds; prefer flat contexts). This resolves the cascade by hand over the panel block: each element of a
// chain contributes the em factor of the best-matching font-size rule (specificity, then source order) and the
// product is the leaf's size in panel units. Both sheets, since the feed page loads only feed.css.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const read = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = read("file-comments.ts");
const SHEETS = [["styles.css", read("styles.css")], ["feed.css", read("feed.css")]] as const;
const LADDER = [0.66, 0.72, 0.82, 0.86];   // the block's own ladder (its header comment; file-comments.test.ts)

// ── a small cascade resolver: enough selector grammar for the block's font-size rules, loud about the rest ──
type Compound = { tag: string | null; classes: string[]; nots: Compound[] };
type Complex = { parts: Compound[]; combinators: string[] };   // combinators[k] sits between parts[k] and parts[k + 1]
type Rule = { selectors: Complex[]; factor: number; specificity: number; order: number; text: string };
type Node = { tag: string; classes: string[] };

function panelBlock(css: string): string {
  const a = css.indexOf("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)");
  const b = css.indexOf("/* ── end file comments panel ── */");
  assert.ok(a >= 0 && b > a, "the block and its end marker");
  return css.slice(a, b).replace(/\/\*[\s\S]*?\*\//g, "");
}

function parseCompound(s: string): Compound {
  const c: Compound = { tag: null, classes: [], nots: [] };
  let i = 0;
  const t = /^[a-zA-Z][\w-]*/.exec(s);
  if (t) { c.tag = t[0].toLowerCase(); i = t[0].length; }
  while (i < s.length) {
    const rest = s.slice(i);
    const cls = /^\.([\w-]+)/.exec(rest);
    if (cls) { c.classes.push(cls[1]); i += cls[0].length; continue; }
    if (rest.startsWith(":not(")) {
      const end = s.indexOf(")", i);
      assert.ok(end > i, "unterminated :not( in " + s);
      const inner = s.slice(i + 5, end);
      assert.doesNotMatch(inner, /,/, ":not() with a list is not resolved here: " + s);
      c.nots.push(parseCompound(inner)); i = end + 1; continue;
    }
    assert.fail("a font-size rule uses selector syntax this resolver does not model (" + s + "); extend it");
  }
  return c;
}
function parseComplex(sel: string): Complex {
  const toks = sel.trim().replace(/\s*>\s*/g, " > ").split(/\s+/);
  const cx: Complex = { parts: [], combinators: [] };
  let pending: string | null = null;
  for (const tok of toks) {
    if (tok === ">") { pending = ">"; continue; }
    if (cx.parts.length) cx.combinators.push(pending || " ");
    cx.parts.push(parseCompound(tok)); pending = null;
  }
  assert.ok(cx.parts.length > 0 && pending === null, "a bare combinator in " + sel);
  return cx;
}
const specOf = (c: Compound): [number, number] => {
  let b = c.classes.length, t = c.tag ? 1 : 0;
  for (const n of c.nots) { const [nb, nt] = specOf(n); b += nb; t += nt; }
  return [b, t];
};
function parseRules(block: string): Rule[] {
  const rules: Rule[] = [];
  let i = 0, order = 0;
  while (i < block.length) {
    if (/\s/.test(block[i])) { i++; continue; }
    if (block[i] === "@") {   // an at-rule (the narrow-fold container query): layout only, skipped whole
      let depth = 0, j = block.indexOf("{", i);
      for (; j < block.length; j++) { if (block[j] === "{") depth++; else if (block[j] === "}" && --depth === 0) break; }
      i = j + 1; continue;
    }
    const open = block.indexOf("{", i), close = block.indexOf("}", open);
    assert.ok(open > i && close > open, "a rule without braces at " + block.slice(i, i + 40));
    const selText = block.slice(i, open).trim(), body = block.slice(open + 1, close);
    i = close + 1; order++;
    let factor: number | null = null;
    for (const d of body.split(";").map((x) => x.trim()).filter(Boolean)) {
      if (/^font\s*:/.test(d)) assert.equal(d.replace(/\s+/g, " "), "font: inherit", "a font shorthand with a size is not resolved here: " + d);
      const fs = /^font-size\s*:\s*(.+)$/.exec(d);
      if (!fs) continue;
      const em = /^(\d*\.?\d+)em$/.exec(fs[1].trim());
      assert.ok(em, "a font-size the resolver cannot multiply (" + fs[1] + ") in `" + selText + "`; the block speaks em");
      factor = parseFloat(em![1]);
    }
    if (factor === null) continue;
    const selectors = selText.split(",").map(parseComplex);
    // one specificity per rule keeps the model simple; the block's font-size rules have one selector each
    assert.equal(selectors.length, 1, "a selector list on a font-size rule: split it so specificity is per selector (" + selText + ")");
    const [b, t] = selectors[0].parts.map(specOf).reduce(([ab, at], [nb, nt]) => [ab + nb, at + nt], [0, 0]);
    rules.push({ selectors, factor, specificity: b * 1000 + t, order, text: selText });
  }
  return rules;
}
const matchCompound = (c: Compound, n: Node): boolean =>
  (c.tag === null || c.tag === n.tag) && c.classes.every((k) => n.classes.includes(k)) && c.nots.every((x) => !matchCompound(x, n));
function matchAt(cx: Complex, chain: Node[], i: number, k: number): boolean {
  if (!matchCompound(cx.parts[k], chain[i])) return false;
  if (k === 0) return true;
  if (cx.combinators[k - 1] === ">") return i > 0 && matchAt(cx, chain, i - 1, k - 1);
  for (let j = i - 1; j >= 0; j--) if (matchAt(cx, chain, j, k - 1)) return true;
  return false;
}
/** the winning font-size rule for chain[i], or null when the element inherits */
function ruleFor(rules: Rule[], chain: Node[], i: number): Rule | null {
  let best: Rule | null = null;
  for (const r of rules) {
    if (!r.selectors.some((cx) => matchAt(cx, chain, i, cx.parts.length - 1))) continue;
    if (!best || r.specificity > best.specificity || (r.specificity === best.specificity && r.order > best.order)) best = r;
  }
  return best;
}
/** "div.fc-panel > span.fc-time" → nodes, root first */
const chainOf = (s: string): Node[] => s.split(">").map((p) => {
  const [tag, ...classes] = p.trim().split(".");
  return { tag, classes };
});
function computed(rules: Rule[], chain: Node[]): { size: number; sized: string[] } {
  let size = 1; const sized: string[] = [];
  chain.forEach((_, i) => { const r = ruleFor(rules, chain, i); if (r) { size *= r.factor; sized.push(r.text); } });
  return { size, sized };
}

// ── the chains, as file-comments.ts builds them (pinned below so the model cannot outlive the DOM) ──
const CARD = "div.fc-panel > div.fc-sec-cards > div.fc-cards > div.fc-card";
const HEAD = CARD + " > div.fc-card-head";
const REPLY = CARD + " > div.fc-replies > div.fc-reply";
const LOG = "div.fc-panel > div.fc-sec-log > div.fc-log";
const CONFIRM = "div.fc-panel > div.fc-sec-send > div.fc-send > div.fc-confirm";
const TIMES: Record<string, string> = {
  "card head time": HEAD + " > span.fc-time",
  "reply time": REPLY + " > div.fc-meta > span.fc-time",
  "log row time": LOG + " > div.fc-log-row > span.fc-time",
};
const LEAVES: Record<string, string> = {
  ...TIMES,
  "card head chip": HEAD + " > span.fc-chip",
  "card head ref": HEAD + " > span.fc-ref",
  "card head tag": HEAD + " > span.fc-tag",
  "card preview": CARD + " > div.fc-preview",
  "card body": CARD + " > div.fc-body",
  "reply chip": REPLY + " > div.fc-meta > span.fc-chip",
  "reply body": REPLY + " > div.fc-body",
  "log row text": LOG + " > div.fc-log-row > span",
  "log empty": LOG + " > div.fc-empty",
  "log note": LOG + " > div.fc-note",
  "log fold": LOG + " > button.fc-sec",
  "send list item": CONFIRM + " > ul.fc-list > li > span",
  "send list desc": CONFIRM + " > ul.fc-list > li > span.fc-list-desc",
  "send option": CONFIRM + " > div.fc-opts > label.fc-opt > span",
  "send message": CONFIRM + " > pre.fc-msg",
};

test("the chains above are the panel's real DOM: the builders in file-comments.ts", () => {
  assert.match(SRC, /sections = \{ head: el\("div", "fc-sec-head"\), cards: el\("div", "fc-sec-cards"\), send: el\("div", "fc-sec-send"\), log: el\("div", "fc-sec-log"\) \};/);
  for (const [tag, cls] of [["div", "fc-panel"], ["div", "fc-cards"], ["div", "fc-card"], ["div", "fc-card-head"], ["div", "fc-replies"],
    ["div", "fc-reply"], ["div", "fc-meta"], ["div", "fc-preview"], ["div", "fc-body"], ["span", "fc-ref"], ["span", "fc-tag"],
    ["div", "fc-log"], ["div", "fc-log-row"], ["div", "fc-empty"], ["div", "fc-note"], ["div", "fc-send"], ["div", "fc-confirm"],
    ["ul", "fc-list"], ["li"], ["span", "fc-list-desc"], ["div", "fc-opts"], ["label", "fc-opt"], ["pre", "fc-msg"]]) {
    assert.match(SRC, new RegExp('el\\("' + tag + '"' + (cls ? ', "' + cls + '[" ]' : "\\)")), tag + (cls ? "." + cls : ""));
  }
  assert.match(SRC, /el\("span", "fc-chip( fc-chip-you)?"/, "chips are spans");
  assert.match(SRC, /"fclog", "fc-sec"\)/, "the Log fold is a .fc-sec button");
  // the three times come from the ONE clock() helper: the same kind of information, so the same size
  assert.match(SRC, /head\.appendChild\(el\("span", "fc-time", clock\(c\.ts\)\)\);/);
  assert.match(SRC, /meta\.appendChild\(el\("span", "fc-time", clock\(r\.ts\)\)\);/);
  assert.match(SRC, /const row = el\("div", "fc-log-row"\);\n\s*row\.appendChild\(el\("span", "fc-time", clock\(e\.ts\)\)\);\n\s*row\.appendChild\(el\("span", undefined, logRowText\(e, nameOf\)\)\);/,
    "a log row is the time and a class-less text span, nothing else");
});

for (const [name, css] of SHEETS) {
  test(name + ": every .fc-time computes to the same size, the bare .fc-time rule's own", () => {
    const rules = parseRules(panelBlock(css));
    const own = rules.find((r) => r.text === ".fc-time");
    assert.ok(own, "the .fc-time rule");
    for (const [label, chain] of Object.entries(TIMES)) {
      const { size, sized } = computed(rules, chainOf(chain));
      assert.ok(Math.abs(size - own!.factor) < 1e-9, label + " renders at " + size.toFixed(4) + "em of the panel, not " + own!.factor + "em (sized by: " + sized.join(" · ") + ")");
    }
  });

  test(name + ": one size per chain, and every leaf lands on the block's ladder", () => {
    const rules = parseRules(panelBlock(css));
    for (const [label, chain] of Object.entries(LEAVES)) {
      const { size, sized } = computed(rules, chainOf(chain));
      assert.ok(sized.length <= 1, label + ": " + sized.length + " nested em sizes compound along " + sized.join(" > ") + "; size ONE element of the chain");
      assert.ok(LADDER.some((v) => Math.abs(v - size) < 1e-9), label + " computes to " + size.toFixed(4) + "em, off the ladder " + LADDER.join("/"));
    }
  });
}
