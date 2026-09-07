// Buttons inside the viewer's error dress compute to the ONE button size. The dress (.fileview-err) is 0.86em and
// .fileview-btn is 0.82em, both em, so a button placed in the dress — the viewer's Download and Reload file, the
// comments panel's Reload and ✕ on every error row — compounded to 0.705em: off the ladder, and visibly smaller
// than the Save / Cancel / Track changes buttons beside it (ui/CLAUDE.md, font sizes: nesting em compounds;
// prefer flat contexts or compensate explicitly). The panel-block resolver (styles-fc-computed-sizes.test.ts)
// could not see it: the dress's rule sits outside the block it parses, and the sheets' ladder tests read declared
// literals. This one resolves the cascade over the WHOLE sheet, along the real ancestry file-view.ts and
// file-comments.ts build, from the html root down. Both sheets — the feed page loads only feed.css.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const read = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const VIEW = read("file-view.ts");
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

// ── the chains, as file-view.ts and file-comments.ts build them (pinned below so the model cannot outlive the DOM) ──
const ROOT = "html > body.fileview-open > div#romp-fileview > div.fileview";
const BAR = ROOT + " > div.fileview-bar > div.fileview-acts";
const BODY = ROOT + " > div.fileview-main > div.fileview-body";
const ASIDE = ROOT + " > div.fileview-main > div.fc-panel.fileview-aside";
const HEAD = ASIDE + " > div.fc-sec-head > div.fc-head";
const COMPOSER = ASIDE + " > div.fc-composer";
const CARD = ASIDE + " > div.fc-sec-cards > div.fc-cards > div.fc-card";
const SEND = ASIDE + " > div.fc-sec-send > div.fc-send";
const ERR = " > div.fileview-err.fc-err";
// every .fileview-btn the viewer and its panel render: the ones OUTSIDE the error dress…
const PLAIN_BUTTONS: Record<string, string> = {
  "title bar Download / Copy path / ✕": BAR + " > button.fileview-btn",
  "title bar Comments toggle": BAR + " > span.fileview-fc > button.fileview-btn",
  "panel Track changes": HEAD + " > div.fc-row > button.fileview-btn.fc-toggle",
  "panel Comment on this file": HEAD + " > div.fc-row > button.fileview-btn",
  "composer Save / Cancel": COMPOSER + " > div.fc-actions > button.fileview-btn",
  "card Reply / Resolve / Reveal": CARD + " > div.fc-actions > button.fileview-btn",
  "send Send / Cancel": SEND + " > div.fc-confirm > div.fc-actions > button.fileview-btn",
};
// …and the ones INSIDE it, which used to compound
const DRESSED_BUTTONS: Record<string, string> = {
  "viewer refusal Download": BODY + " > div.fileview-err > button.fileview-btn.fileview-err-dl",
  "editor conflict Reload file": BODY + " > div.fileview-err > button.fileview-btn.fileview-err-dl",
  "head / track / poll error Reload": HEAD + ERR + " > button.fileview-btn",
  "head / track / poll error ✕": HEAD + ERR + " > button.fileview-btn.fc-x",
  "composer error ✕": COMPOSER + " > div" + ERR + " > button.fileview-btn.fc-x",
  "card error ✕": CARD + ERR + " > button.fileview-btn.fc-x",
  "send error Reload": SEND + ERR + " > button.fileview-btn",
  "send error ✕": SEND + ERR + " > button.fileview-btn.fc-x",
};
const WORDS: Record<string, string> = {
  "viewer refusal words": BODY + " > div.fileview-err",
  "panel error words": HEAD + ERR + " > span",
};

test("the chains above are the real DOM: the builders in file-view.ts and file-comments.ts", () => {
  // the viewer: wrap#romp-fileview > .fileview > (.fileview-bar > .fileview-acts | .fileview-main > .fileview-body)
  assert.match(VIEW, /wrap\.id = "romp-fileview";/);
  assert.match(VIEW, /const box = el\("div", "fileview"\);/);
  assert.match(VIEW, /const bar = el\("div", "fileview-bar"\);/);
  assert.match(VIEW, /const acts = el\("div", "fileview-acts"\);/);
  assert.match(VIEW, /const main = el\("div", "fileview-main"\);\n\s*const body = el\("div", "fileview-body"\);/);
  assert.match(VIEW, /main\.appendChild\(body\);/);
  assert.match(VIEW, /bar\.appendChild\(acts\);/);
  assert.match(VIEW, /box\.appendChild\(bar\); box\.appendChild\(main\);/);
  assert.match(VIEW, /if \(node\) \{ node\.classList\.add\("fileview-aside"\); main\.appendChild\(node\); \}/, "the panel's root IS the aside");
  // the title bar's buttons, and the Comments toggle inside its .fileview-fc unit
  assert.match(VIEW, /const dl = el\("button", "fileview-btn"\) as HTMLButtonElement;[\s\S]*?acts\.appendChild\(dl\);/);
  assert.match(PANEL, /const unit = el\("span", "fileview-fc"\);/);
  // the dressed buttons: the refusal's Download and the editor's Reload file, both .fileview-btn.fileview-err-dl in a .fileview-err
  assert.match(VIEW, /const why = el\("div", "fileview-err"\);[\s\S]*?const offer = el\("button", "fileview-btn fileview-err-dl"\) as HTMLButtonElement;[\s\S]*?why\.appendChild\(offer\);\n\s*\}\n\s*body\.replaceChildren\(why\);/);
  assert.match(VIEW, /const bar2 = noteBar\(err\);[\s\S]*?const re = el\("button", "fileview-btn fileview-err-dl"\) as HTMLButtonElement;[\s\S]*?bar2\.appendChild\(re\);/);
  assert.match(VIEW, /const bar2 = el\("div", "fileview-err"\);\n\s*bar2\.id = "fileview-save-err";\n\s*bar2\.textContent = msg;\n\s*body\.prepend\(bar2\);/);
  // the panel: .fc-panel.fileview-aside > (.fc-sec-head > .fc-head | .fc-composer | .fc-sec-cards > .fc-cards > .fc-card | .fc-sec-send > .fc-send)
  assert.match(PANEL, /this\.root = el\("div", "fc-panel"\);\n\s*this\.ctx\.aside\(this\.root\);/);
  assert.match(PANEL, /sections = \{ head: el\("div", "fc-sec-head"\), cards: el\("div", "fc-sec-cards"\), send: el\("div", "fc-sec-send"\), log: el\("div", "fc-sec-log"\) \};/);
  assert.match(PANEL, /composerBox = el\("div", "fc-composer"\);/);
  assert.match(PANEL, /composerActs = el\("div", "fc-actions"\);/);
  assert.match(PANEL, /composerErr = el\("div"\);/, "the composer's error slot is a class-less div");
  assert.match(PANEL, /this\.root\.replaceChildren\(head, this\.composerBox, cards, send, log\);/);
  assert.match(PANEL, /head\.replaceChildren\(this\.renderHead\(s\)\);[\s\S]*?cards\.replaceChildren\(this\.renderCards\(s\)\);\n\s*send\.replaceChildren\(this\.renderSend\(s\)\);/);
  assert.match(PANEL, /const head = el\("div", "fc-head"\);\n\s*const row = el\("div", "fc-row"\);\n\s*const t = btn\("Track changes", "fctrack", "fileview-btn fc-toggle"\);/);
  assert.match(PANEL, /row\.appendChild\(btn\("Comment on this file", "fcfile"\)\);\n\s*head\.appendChild\(row\);/);
  assert.match(PANEL, /const list = el\("div", "fc-cards"\);/);
  assert.match(PANEL, /const card = el\("div", "fc-card"/);
  assert.match(PANEL, /const acts = el\("div", "fc-actions"\);\n\s*const reply = btn\("Reply", "fcreply"\);[\s\S]*?card\.appendChild\(acts\);/);
  assert.match(PANEL, /const box = el\("div", "fc-send"\);/);
  assert.match(PANEL, /const cf = el\("div", "fc-confirm"\);[\s\S]*?const acts = el\("div", "fc-actions"\);\n\s*acts\.appendChild\(btn\("Send", "fcsendgo", "fileview-btn fc-primary"\)\);[\s\S]*?cf\.appendChild\(acts\);\n\s*box\.appendChild\(cf\);/);
  // every error row: the dress + .fc-err, its words in a span, Reload a default-class button, ✕ a .fileview-btn.fc-x
  assert.match(PANEL, /function btn\(label: string, act: string, cls = "fileview-btn"\)/);
  assert.match(PANEL, /const row = el\("div", "fileview-err fc-err" \+ \(e\.warn \? " fc-err-warn" : ""\)\);/);
  assert.match(PANEL, /el\("span", undefined, e\.text\)/, "the words are a class-less span");
  assert.match(PANEL, /row\.appendChild\((?:text|el\("span", undefined, e\.text\))\);/, "…appended to the row");
  assert.match(PANEL, /if \(e\.reload\) \{ const b = btn\("Reload", "fcreload"\);[^\n]*row\.appendChild\(b\); \}/);
  assert.match(PANEL, /const x = btn\("✕", "fcerrx", "fileview-btn fc-x"\);[^\n]*row\.appendChild\(x\);/);
  // …and where each slot's row lands
  assert.match(PANEL, /\[this\.loader\("track"\), this\.errRow\("track"\), this\.errRow\("head"\), this\.errRow\("poll"\)\]\) if \(n\) head\.appendChild\(n\);/);
  assert.match(PANEL, /const err = this\.composerErr;\n\s*err\.replaceChildren\(\.\.\.\[this\.loader\("composer"\), this\.errRow\("composer"\)\]/);
  assert.match(PANEL, /box\.replaceChildren\(ref, this\.input, acts, err\);/);
  assert.match(PANEL, /\[this\.loader\("card:" \+ c\.id\), this\.errRow\("card:" \+ c\.id\)\]\) if \(n\) card\.appendChild\(n\);/);
  assert.match(PANEL, /\[this\.loader\("send"\), this\.errRow\("send"\)\]\) if \(x\) box\.appendChild\(x\);/);
  // Reload rows exist to be sized: the head fetch, the poll's 413/415 stop, and the moved-store codes offer one
  assert.ok((PANEL.match(/reload: (?:true|MOVED\.has\(e\.code\))/g) || []).length >= 3, "rows with a Reload button");
});

for (const [name, css] of SHEETS) {
  const rules = parseSheet(css);
  const own = () => {
    const r = rules.find((x) => x.text === ".fileview-btn");
    assert.ok(r && r.size.kind === "em", "the .fileview-btn rule sizes in em");
    return (r!.size as { factor: number }).factor;
  };

  test(name + ": every .fileview-btn computes to the one button size, inside the error dress or out", () => {
    const button = own();
    for (const [label, chain] of Object.entries({ ...PLAIN_BUTTONS, ...DRESSED_BUTTONS })) {
      const { size, sized } = computed(rules, chainOf(chain));
      assert.ok(Math.abs(size - button) < 1e-9, label + " renders at " + size.toFixed(4) + "em of the viewer, not the " + button + "em every other button wears (sized by: " + sized.join(" · ") + ")");
    }
  });

  test(name + ": the dress keeps its own size for its words, and every leaf lands on the sheets' ladder", () => {
    const dress = rules.find((x) => x.text === ".fileview-err");
    assert.ok(dress && dress.size.kind === "em", "the .fileview-err rule sizes in em");
    for (const [label, chain] of Object.entries(WORDS)) {
      const { size, sized } = computed(rules, chainOf(chain));
      assert.ok(Math.abs(size - (dress!.size as { factor: number }).factor) < 1e-9, label + " render at " + size.toFixed(4) + "em (sized by: " + sized.join(" · ") + ")");
      assert.equal(sized.length, 1, label + ": one size on the chain");
    }
    for (const [label, chain] of Object.entries({ ...PLAIN_BUTTONS, ...DRESSED_BUTTONS, ...WORDS })) {
      const { size } = computed(rules, chainOf(chain));
      assert.ok(LADDER.some((v) => Math.abs(v - size) < 1e-9), label + " computes to " + size.toFixed(4) + "em, off the ladder " + LADDER.join("/"));
    }
  });

  test(name + ": the compensation is ONE rule beside the dress — the viewer's own buttons reach it, not only the panel's", () => {
    // outside the panel block (byte-equal across the sheets in file-comments.test.ts), so a viewer without the
    // panel — the refusal's Download, the editor's Reload file — is compensated the same way
    const at = css.indexOf(".fileview-err .fileview-btn {");
    const block = css.indexOf("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)");
    assert.ok(at >= 0, "the .fileview-err .fileview-btn rule");
    assert.ok(block < 0 || at < block, "the rule sits with the dress, before the panel block");
    const sizing = rules.filter((r) => r.selectors.some((cx) => cx.parts.length >= 2 && cx.parts[cx.parts.length - 1].classes.includes("fileview-btn")));
    assert.deepEqual(sizing.map((r) => r.text), [".fileview-err .fileview-btn"], "no other descendant rule re-sizes a .fileview-btn");
  });
}
