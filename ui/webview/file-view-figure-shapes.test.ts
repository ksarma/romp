// The figure control over the shapes the first review of the link-navigation follow-on (plans/markdown-viewer.md, L3) found
// it wrong on: the source pins beside the Chromium leg (file-view-figure-shapes-browser.test.ts, which lays the shapes out and
// clicks them). Three defects, one rule each: (1) a protocol-relative source (`//host/pic.svg`) reached the model's join
// before the web test, and figurePath reads any `/`-led source as an absolute path of the disk, so the web arm was dead and
// the control opened the viewer on the kernel's /file route at that path (a 404 and a bogus entry on the trail) in place of
// a tab: figureTarget now tests the web address FIRST; (2) a figure inside a link that holds more than the figure (text
// beside it, `[![alt](src) caption](target)`) had its control INSIDE the author's link, because figureAnchor climbs a link
// only when it holds the figure alone, and one click on the button fired the links listener (the link's open) and the
// figure listener (the picture's open), two opens and a phantom entry on the trail: no control goes inside a link
// (linkAbove); and the bare figure's own click yields to an anchor with an href too (a web address of the markdown carries
// no class, so linkOf read none and the plain click opened the tab AND the picture); (3) a figure under 48px on either side
// (a badge, an inline icon) wore a control the sheets' fixed margins laid over its neighbours, transparent, taking the click
// meant for the badge's link or the prose before the icon: a floor (FIGOPEN_MIN_PX) read from the loaded figure. Since the
// file review the control is decided from the figure's CURRENT state by one function (decideFigureControl, the verdict
// figureWantsControl over figureState) at the paint, at the load and the error, and at each change of the figure's OWN
// laid-out box (watchFigureBoxes, one ResizeObserver per open over the figures of the Rendered box; the file review's round 2:
// decided from the width watch's repaint alone, a text-size step, which reflows the 80ch column at a constant body width,
// never re-decided), so a fetching or a failed figure wears none and opens nothing (figureTarget refuses both states), a figure
// the column narrowed under the floor loses its control and one it widened past gets it back (read once, at the load, a figure
// the pane narrowed to 323 by 32 kept a control that hung over it, file-view-figure-floor-browser.test.ts; the other states in
// file-view-figure-state-browser.test.ts); a control removed while it holds the keyboard hands it to the viewer's body first
// (removeFigureControl). (2)'s exclusion reads ANY anchor above the figure (linkAbove), a dead link too.
// Every pin reads the tree's own source, so a rename fails loudly; the leg executes each rule in a browser. Synthetic values
// only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { literals, type Unit } from "./source-units";

const VIEW = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "file-view.ts"), "utf8");
/** The units among `units` that name a refused member: a string or template literal whose whole value is the member, or a
 *  regular expression literal whose text names the word (its escape classes, `\b` `\w` `\s` and the rest, read as gaps first,
 *  since the `b` of a `\b` before the word is a word character to the tester and hid `/\bfailed\b/` from it, the boundary
 *  test's plant); each as the member, the line and the kind. */
const readersOf = (units: Unit[], refused: string[]): string[] =>
  refused.flatMap((m) => units.filter((l) => (l.kind === "regex" ? new RegExp("\\b" + m + "\\b").test(l.text.replace(/\\[A-Za-z]/g, " ")) : l.text === m)).map((l) => JSON.stringify(m) + " at line " + l.line + " (" + l.kind + ")"));
/** What the refused-state pin reads and what stands outside it, in the pin's message and pinned by execution below. */
const BOUNDARY_NOTE = "the pin reads WHOLE literal values, so an identifier used as a key, a word assembled from parts, a prefix or substring test and a case-folded comparison stand outside it, which the boundary test pins by execution";
/** The text from one anchor to the next, both present. */
const between = (src: string, from: string, to: string): string => {
  const a = src.indexOf(from); assert.ok(a >= 0, from + " present");
  const b = src.indexOf(to, a); assert.ok(b > a, to + " present after " + from);
  return src.slice(a, b);
};
/** `lines` stand in `src` in this order (each sought after the one before it: a line that recurs, `return null;`, is read at its place). */
const inOrder = (src: string, lines: string[], what: string): void => {
  let last = -1;
  for (const l of lines) {
    const at = src.indexOf(l, last + 1);
    assert.ok(at > last, what + ": " + l + " in order");
    last = at;
  }
};

test("figureTarget reads the web address before the model's join, so a protocol-relative source is a tab (figurePath would read it as an absolute path of the disk)", () => {
  const fn = between(VIEW, "function figureTarget(img: Element, filePath: string): FigureTarget | null {", "\n}\n");
  inOrder(fn, [
    "const dest = chosenSource(img);",
    "if (dest === null) return null;",
    'if (/^https?:/i.test(dest) || dest.startsWith("//")) return { kind: "web", href: absUrl(dest) };',
    "const p = figurePath(filePath, dest);",
    'if (p !== null) return { kind: "file", path: p };',
    "return null;",
  ], "figureTarget");
  assert.match(fn, /figurePath reads a protocol-relative source \(`\/\/host\/pic\.svg`\) as an\n\s*\/\/ absolute path of the disk/, "the comment says why the order matters");
});

test("the one decision: figureWantsControl reads the figure's state by one rule (figureHasPicture: a control only for a state with a picture to name, loaded or a stand-in; fetching, failed and any later state get none), then the floor, the target and any link above; decideFigureControl adds or removes against the control standing, handing the keyboard to the viewer's body before a removal; the floor is 48px on either side, read from the loaded picture's laid-out box as it is while the figure is in the document (or its own size before it is); linkAbove is any anchor; the load, the error and the figures' own ResizeObserver all run the decision, a 0 by 0 report runs none, no arm precedes the first paint, and the width watch's repaint runs none; figureTarget refuses on the same rule, and no reader names a refused state", () => {
  const want = between(VIEW, "function figureWantsControl(img: Element, anchor: Element, filePath: string): boolean {", "function decideFigureControl(");
  inOrder(want, [
    "if (img.closest('[data-act=\"' + GATE_ACT + '\"]')) return false;",
    "const state = figureState(img);",
    "if (!figureHasPicture(state)) return false;",
    "if (figureTooSmall(img)) return false;",
    "if (figureTarget(img, filePath) === null) return false;",
    "return linkAbove(anchor) === null;",
  ], "figureWantsControl");
  const decide = between(VIEW, "function decideFigureControl(img: Element, filePath: string): void {", "function addFigureControls(");
  inOrder(decide, [
    "const anchor = figureAnchor(img);",
    "const standing = figureControlAfter(anchor);",
    "const want = figureWantsControl(img, anchor, filePath);",
    "if (standing) { if (!want) removeFigureControl(standing); return; }",
    "if (!want) return;",
    'const b = el("button", "fileview-btn fileview-icon " + FIGOPEN_CLASS) as HTMLButtonElement;',
    "parent.insertBefore(b, anchor.nextSibling);",
  ], "decideFigureControl: the verdict against the control standing, one place that adds or removes");
  // the removal hands the keyboard on first (the file review's round 2, ui-4): the holder read before the control goes, the
  // viewer body's takeKeyboard (registered per open) called after it, with the ring the holder wore
  const remove = between(VIEW, "function removeFigureControl(control: HTMLElement): void {", "\n}\n");
  inOrder(remove, ["const a = document.activeElement;", "const held = !!a && control.contains(a);", "const ring = held ? ringOf(a) : false;", "control.remove();", "if (take) take(ring);"], "removeFigureControl: the keyboard read before the removal and handed to the viewer's body after it");
  assert.match(VIEW, /\nconst keyboardTakers = new WeakMap<HTMLElement, \(ring\?: boolean\) => void>\(\);\n/, "the per-open register of the body's takeKeyboard");
  assert.match(VIEW, /keyboardTakers\.set\(body, takeKeyboard\);[^\n]*\n\s*closeHooks\.push\(\(\) => \{ keyboardTakers\.delete\(body\); \}\);/, "registered once per open where takeKeyboard is defined, dropped with the viewer");
  assert.equal((VIEW.match(/setAttribute\(FIGOPEN_MARK, ""\)/g) || []).length, 1, "one place mints a control");
  assert.doesNotMatch(VIEW, /function ensureFigureControl|function dropFigureControl/, "the add-only builder and the drop arm are gone: one decision");
  const state = between(VIEW, "function figureState(img: Element): FigureState {", "\n}\n");
  inOrder(state, ['if (typeof i.complete !== "boolean") return "standin";', 'if (!i.complete) return "fetching";', 'return i.naturalWidth > 0 ? "loaded" : "failed";'], "figureState: the browser's own record on the element");
  // the one rule both readers refuse on, a rule over the states and not a list of the two refused: the domain is the four
  // values of FigureState, the allowance names the two with a picture to name, and any value outside it (a state the type gains
  // later) falls on the refusing side with no edit to either reader
  assert.match(VIEW, /\ntype FigureState = "standin" \| "fetching" \| "loaded" \| "failed";\n/, "the domain: four states");
  const rule = between(VIEW, "function figureHasPicture(state: FigureState): boolean {", "\n}\n");
  assert.match(rule, /\n\s*return state === "loaded" \|\| state === "standin";$/, "the allowance: loaded (the browser answered with a picture) or a stand-in (no browser to ask); every other value refused");
  // the guard against a list is keyed on the property, not on one spelling of the list (the file review's round 3, tests-3: a pin
  // over `state === "fetching" || state === "failed"` passed the same two in the other order; its round 4, regression-2 with
  // extra6-1: the rebuilt pin matched the double-quoted literal and passed a single-quoted comparison, while its message, L3 and
  // the body claimed no member's literal stood anywhere): the refused set is derived, the domain's members less the ones the
  // allowance names, and the file's string literals are read as the compiler reads them (source-units.ts: either quote, a
  // template span, escapes resolved, and a regular expression literal by its text), so no literal equal to a refused member
  // stands outside the type line and figureState's body, the two places that must name every member, and a reader that names
  // one by its whole literal (a comparison in either order, a `case`, an array or a Set, a template, an escaped spelling) or by
  // a regular expression over the word fails here; comments are not literals, so prose may quote the word. The pin's boundary,
  // stated because the comment here had claimed any spelling (the author's closing pass after the file review's round 4,
  // guards-1 with records-11): it reads whole values equal to a member, so a reader that uses the word as an identifier key
  // (`{ failed: true }`, a lookup table), assembles it from parts (`'fai' + 'led'`), tests a prefix or a substring of it
  // (`startsWith('fail')`, `/^fetch/`) or compares case-folded (`toUpperCase() === 'FAILED'`) stands outside it; the identifier
  // form is left unread on purpose, since file-view.ts names a save hook `failed` (editHooks), which a key reader would red at
  // rest or force a rename of product code for a pin. The boundary test below plants every form and pins which side each
  // falls on. The pin is file-wide on purpose (the author's closing pass after the file review's round 3, records-3), so a
  // literal "failed" or "fetching" for anything else in the module must be spelled another way
  const typeLine = VIEW.match(/\ntype FigureState = [^\n]*;\n/);
  assert.ok(typeLine, "the FigureState type line");
  const typeAt = VIEW.indexOf(typeLine![0]);
  const ruleAt = VIEW.indexOf(rule);
  const stateAt = VIEW.indexOf(state);
  const within = (l: Unit, from: number, to: number): boolean => l.pos >= from && l.end <= to;
  const lits = literals(VIEW, "file-view.ts");
  const members = lits.filter((l) => within(l, typeAt, typeAt + typeLine![0].length)).map((l) => l.text);
  const allowed = lits.filter((l) => within(l, ruleAt, ruleAt + rule.length)).map((l) => l.text);
  const refused = members.filter((m) => !allowed.includes(m));
  assert.ok(members.length >= 3 && allowed.length >= 1 && refused.length >= 1 && allowed.every((a) => members.includes(a)), "a derived refused set: " + JSON.stringify({ members, allowed, refused }));
  const elsewhere = lits.filter((l) => !within(l, typeAt, typeAt + typeLine![0].length) && !within(l, stateAt, stateAt + state.length));
  const readers = readersOf(elsewhere, refused);
  assert.deepEqual(readers, [], "no reader names a refused state (" + refused.map((m) => JSON.stringify(m)).join(", ") + "): its literal stands only on the type line and in figureState (read by the compiler: a string in either quote, a template span or an escaped spelling is the same literal, and a regular expression naming the word counts; comments are not read, so prose may quote it; " + BOUNDARY_NOTE + "; the pin is file-wide on purpose, so a literal for anything else in file-view.ts must be spelled another way)");
  assert.match(VIEW, /\nconst FIGOPEN_MIN_PX = 48;\n/, "the floor: the control's 22px box, its 6px inset and as much figure again");
  const small = between(VIEW, "function figureTooSmall(img: Element): boolean {", "\n}\n");
  assert.match(small, /const b = figureBox\(img\);\n\s*return b !== null && \(b\.w < FIGOPEN_MIN_PX \|\| b\.h < FIGOPEN_MIN_PX\);/, "under the floor on EITHER side (a badge is wide and short)");
  const box = between(VIEW, "function figureBox(img: Element): { w: number; h: number } | null {", "\n}\n");
  assert.match(box, /if \(figureState\(img\) !== "loaded"\) return null;/, "a loaded figure alone has a box to measure: the fetching and failed verdicts are figureWantsControl's, a stand-in has no picture to ask");
  // the laid-out box of a figure IN the document as it is, 0 by 0 included (an author's `hidden` or `width="0"`: under the floor, no
  // control), the picture's own size for a figure not in it (mdBlock's box at the paint); the file review's round 3
  // (correctness-1): the fallback ran for ANY zero-sided rect, so a loaded figure with no box was measured over the floor and wore
  // a control 28 px into the prose before it (file-view-figure-floor-browser.test.ts drives both authored shapes)
  assert.match(box, /const r = i\.isConnected && typeof i\.getBoundingClientRect === "function" \? i\.getBoundingClientRect\(\) : null;\n\s*return r \? \{ w: r\.width, h: r\.height \} : \{ w: i\.naturalWidth, h: i\.naturalHeight \};/,
    "the laid-out box, whatever it is, for a figure in the document (an author's width attribute counts, and so does no box at all), else the picture's own size (a detached box)");
  assert.doesNotMatch(box, /r\.width > 0|r\.height > 0/, "no fallback keyed on a zero side: a 0 by 0 box in the document is the figure's box");
  const above = between(VIEW, "function linkAbove(anchor: Element): Element | null {", "\n}\n");
  assert.match(above, /const p = anchor\.parentElement;\n\s*return p \? p\.closest\('a, \[data-act="openpath"\]'\) : null;/,
    "ANY anchor above the anchor (a link holding the figure alone IS the anchor and is not read): with an href or without one (a dead link, a named target), or a path link whose href mark time took off");
  // the load and the error re-run the decision: one capture-phase pair per open
  const arm = between(VIEW, "function armFigureControls(body: HTMLElement, filePath: string): () => void {", "\n}\n");
  assert.match(arm, /const decide = \(e: Event\): void => \{ const img = figureOf\(e\); if \(img && figureState\(img\) !== "standin"\) decideFigureControl\(img, filePath\); \};/, "the events' road into the decision, for an element carrying the browser's record (a stand-in stays as the paint decided it)");
  assert.match(arm, /body\.addEventListener\("load", decide, true\);\n\s*body\.addEventListener\("error", decide, true\);/, "the load and the error, both capture (neither bubbles)");
  // each figure's OWN box re-runs it (the file review's round 2): one ResizeObserver per open over the figures of the Rendered
  // box, re-armed at each text paint (never at a reflow, whose figures are the same nodes), dropped with the viewer; the
  // observer hears every reflow of the figure, the body's width and a text-size step alike, so no road calls the decision
  // itself; absent ResizeObserver (a stand-in outside a browser) nothing is armed and the paint's decision stands
  const watch = between(VIEW, "function watchFigureBoxes(body: HTMLElement, filePath: string, onRendered: (cb: (why?: FileViewRenderWhy) => void) => void): (() => void) | null {", "\n}\n");
  inOrder(watch, [
    'if (typeof ResizeObserver !== "function") return null;',
    "const ro = new ResizeObserver((entries) => {",
    "if (e.contentRect.width === 0 || e.contentRect.height === 0) continue;",
    'if (img.isConnected && figureState(img) !== "standin") decideFigureControl(img, filePath);',
    'body.querySelectorAll(".fileview-md img").forEach((img) => { ro.observe(img); });',
    'onRendered((why) => { if (why !== "reflow") rearm(); });',
    "return () => { ro.disconnect(); };",
  ], "watchFigureBoxes: the guard, the observer over the figures, the 0 by 0 report skipped before the decision, the arm at each paint, the drop");
  // no standalone arm between the paint's arm and the drop (the file review's round 3, tests-4): the open runs this before its
  // first paint, over an empty body, so a `rearm();` there observed nothing on any road (measured in Chromium over the fresh open,
  // the replace, Back, Forward and a reopen); the mark is anchored to the whole line, since a bare "rearm();" was satisfied by the
  // substring inside the onRendered line before it
  assert.doesNotMatch(watch, /^\s*rearm\(\);\s*$/m, "no standalone arm: the paint's arm is the only one, and a line that observes nothing carries no pin");
  assert.equal((watch.match(/rearm\(\)/g) || []).length, 1, "rearm is called from the onRendered hook alone (its definition aside)");
  // a 0 by 0 report is skipped, and the comment states the skip as a rule over the report, whatever produced it (the file
  // review's round 4, regression-3: the reason before it, narrowed in the file review's round 3 and stated with its residual by
  // the author's closing pass after the file review's round 3, behaviour-4, still named its roads as a closed list, and a loaded
  // figure the author gave no box was a road outside it): the transient reports (the viewer's hide, a gated placeholder's img),
  // whose show or restore reports the real box; the final one (a figure whose REAL box is 0 by 0, which the floor refuses at
  // its load; the file review's round 3, correctness-1); and the residual, a figure hidden after its load by any other road
  // keeping its control, with the product's one road to it, an expanded callout folded by the reader, and why the control is
  // harmless there (the file review's round 4, ui-1). The residual sentence is pinned whole, through the code line after it, so
  // a clause appended to it cannot go stale unpinned; the comment's prose is read with its line breaks collapsed, so a rewrap
  // holds; file-view-figure-floor-browser.test.ts drives the hide, the show and both authored shapes
  const skipProse = watch.replace(/^\s*\/\/ ?/gm, "").replace(/\s+/g, " ");
  assert.match(skipProse, /A 0 by 0 report is skipped: a 0 by 0 report decides nothing, whatever produced it; the figure is decided by its load or its error \(armFigureControls\), by the gate's restore, or by its next report with a box/, "the skip is a rule over the report, not a list of roads to it");
  assert.match(skipProse, /The viewer's hide \(display:none on the pane or its page, the dashboard at a viewport where the pane hides\) and a gated placeholder's img before its click are transient: the show or the restore reports the real box, which is decided/, "the transient reports, examples and not the roads");
  assert.match(skipProse, /A loaded figure whose real box is 0 by 0 \(an author's `hidden` or `width="0"`\) is final: it reports 0 by 0 for as long as it stands, and the skip is no guard for it and needs to be none, since the floor refused it at its load/, "the final report: the loaded figure with no box is the floor's");
  assert.match(skipProse, /The residual the skip leaves: a figure hidden after its load by any other road keeps a standing control until its next report with a box; the product's one such road, an expanded callout folded by the reader, reports nothing while folded and folds the control with the figure, and the first report with a box after the reopen decides the figure again \(the docstring above; the file review's round 4, ui-1\)\. if \(e\.contentRect\.width === 0/, "the residual, whole, with the product's road to it and why it is harmless there, and nothing after it");
  assert.match(VIEW, /const figureWatch = watchFigureBoxes\(body, path, ctx\.onRendered\);\n\s*if \(figureWatch\) ctx\.onClose\(figureWatch\);/, "set up once per open and armed at each text paint through the seam's onRendered, the first paint's included (nothing is observed at the open: the body is empty then); dropped through the close hooks");
  const paint = between(VIEW, "function addFigureControls(box: HTMLElement, filePath: string): void {", "\n}\n");
  assert.match(paint, /box\.querySelectorAll\("img"\)\.forEach\(\(img\) => \{ decideFigureControl\(img, filePath\); \}\);/, "the paint runs the same decision (a stand-in's only one)");
  // the width watch's repaint decides no figure: a call there ran on one road of two (the file review's round 2), and the
  // figures' observer hears that reflow as it hears the text-size step's
  const repaint = between(VIEW, "const repaint = () => {", "\n  };\n");
  inOrder(repaint, ["if (seenWidth === paintedWidth) return;", "paintedWidth = seenWidth;", "if (!textShowing()) return;", "if (unmeasurable()) return;", "landRemembered(); landTarget();", "retakeAfterHide();"], "the repaint as it was before the figures had a decision of their own");
  assert.doesNotMatch(repaint, /igureControl/, "no figure decision in the width watch's repaint");
  assert.doesNotMatch(VIEW, /refigureControls/, "the width-only road is gone");
  // the target waits for the browser's answer too, and refuses a failed figure as the control does (the file review's round 2,
  // regression-3 with extra5-4): a plain click on a fetching or a failed figure opens nothing, and the two readers agree
  const target = between(VIEW, "function figureTarget(img: Element, filePath: string): FigureTarget | null {", "\n}\n");
  inOrder(target, ["const state = figureState(img);", "if (!figureHasPicture(state)) return null;", "const dest = chosenSource(img);"], "figureTarget: a target only for a state with a picture to name, read before the candidate (no candidate before the browser has picked, nothing to open after a failure, nothing for a state the type gains later)");
});

test("the refused-state pin's boundary, by execution over an assembled probe: a whole literal in either quote, a template, a `case`, a Set member with an escaped spelling and a regular expression over the word are read; an identifier key, a word assembled from parts, a prefix or substring test and a case-folded comparison are not, as the pin's message says", () => {
  // the author's closing pass after the file review's round 4 (guards-1 with records-11): four planted readers of a refused
  // state passed the pin silently while its comment claimed any spelling; the boundary is stated in the message and held here
  const src = [
    "const s: string = String(Math.random());",
    "const a = s === 'failed' || s === 'fetching';",
    "const b = `failed`;",
    "switch (s) { case 'fetching': break; }",
    "const c = new Set(['fai\\x6ced']);",
    "const d = /\\bfailed\\b/.test(s);",
    "const e: Record<string, boolean> = { failed: true, fetching: true };",
    "const f = s === 'fai' + 'led';",
    "const g = s.startsWith('fail') || /^fetch/.test(s);",
    "const h = s.toUpperCase() === 'FAILED';",
  ].join("\n");
  const found = readersOf(literals(src, "probe.ts"), ["failed", "fetching"]);
  assert.deepEqual(found.map((r) => Number(/ at line (\d+) /.exec(r)![1])).sort((x, y) => x - y), [2, 2, 3, 4, 5, 6], "read: the two comparisons, the template, the case, the escaped Set member and the regular expression: " + JSON.stringify(found));
  assert.ok(found.every((r) => !/ at line (?:7|8|9|10) /.test(r)), "not read, the boundary the message states: the identifier keys, the assembled word, the prefix tests and the case-folded comparison: " + JSON.stringify(found));
  assert.match(BOUNDARY_NOTE, /identifier used as a key, a word assembled from parts, a prefix or substring test and a case-folded comparison stand outside it/, "the message names the four forms outside the pin");
});

test("the sheets' figure-control comment names the builder that exists (decideFigureControl), not the one the one decision replaced", () => {
  const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
  for (const name of ["styles.css", "feed.css"]) {
    const css = web(name);
    assert.doesNotMatch(css, /ensureFigureControl|dropFigureControl/, name + ": no name of the retired builder or drop arm");
    assert.match(css, /file-view\.ts\n\s+decideFigureControl\): a glyph button of the bar's family/, name + ": the comment names decideFigureControl");
  }
});

test("the figure listener: the bare figure's plain click yields to an anchor with an href as it yields to the links listener's links; the control's branch and the pinned guards stand as they were", () => {
  const listeners = VIEW.split('body.addEventListener("click", (ev) => {');
  assert.equal(listeners.length, 3, "two click listeners on the viewer's body: the links' and the figures'");
  const fig = listeners[2].split("\n  });\n")[0];
  inOrder(fig, [
    "const control = figureControlOf(t, body);",
    "const img = bareFigureOf(t, body);",
    "if (!img || linkOf(t)) return;",
    'if (img.closest("a[href]")) return;',
    "if (panelMark(t) && !wantsOwnTab(ev)) return;",
    "if (asideOpen && !wantsOwnTab(ev)) return;",
    "if (selectionOpenIn(box)) return;",
    "openFigure(img, ev);",
  ], "the figure listener");
  assert.doesNotMatch(fig, /ev\.stopPropagation\(\)/, "a plain click is never stopped here");
  // the links listener is as it was (file-view-links.test.ts pins its text): the fix is in the DOM (no control inside a link) and in the figure listener's yield
  const links = listeners[1].split("\n  });\n")[0];
  assert.doesNotMatch(links, /figure/, "the links' listener knows nothing of figures");
});
