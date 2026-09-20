// The plan's link-navigation follow-on (plans/markdown-viewer.md, "## Follow-on: Link navigation (2026-09-19)") records
// what the build did, and this module holds the record to the tree. The follow-on gave the file viewer a navigation
// trail (ui/webview/file-trail.ts, moved by ui/webview/file-view.ts through one door its own openers take), Back and
// Forward as two glyph buttons at the left of the bar with Alt+Left, Alt+Right and the Mac's Cmd+[ and Cmd+] as chords,
// and an "Open the picture" control on the figures of a rendered file (with the exceptions L3 names) that opens the picture
// through the same trail push. The record names each decision's key sentence, the words the bar and the control show, the sheets' rules, the
// guide's two sentences, the browser plan's pointer and the test modules. Each of those is read here from its source:
// the section is present once, after "## Out of scope", and carries the ask, what existed, the six decision heads, the
// tests and the open points in that order; the trail module exists with the functions L1 names and the viewer calls it
// where L1 and L2 say (the one tag read before the close guard, the move after the leave write, both exits ending the
// trail, the reload keeping it, the delegate's push, the buttons' open with no target, the capture-phase chord
// listener); the words quoted in the section and the guide are the sources' literals; both sheets carry L3's rules
// under `screen` and the print block names the control nowhere; no history API call stands in the trail or the viewer
// (L5); the trail module imports nothing and fetches nothing, and L6's two verifications are run from the merge-base with
// origin/main wherever that ref is known (L6); the guide's two sentences are whole, the old wording
// is gone, and the sentence that says a link opens the file in place still stands (it is still true); the browser
// plan's pointer stands in its navigation-stack section; and the module list is two-way (every module the section's
// `ls` produces is named in the section and the count the section gives is the listing's, read from its sentence rather
// than fixed here; every test module that names the follow-on in its own text, under ui/webview, tools or tests, is
// named too; and every module the section names exists, this one included). The section is not held to be the plan's
// last: the print follow-on (branch filereview-print, in flight) lands at the same place and its pin holds that one
// last (the section's open point 8). Synthetic: only the repo's own text.
// Run: node --test tools/markdown-viewer-plan-linknav.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');
const exists = (...parts) => fs.existsSync(path.join(REPO, ...parts));
const flat = (s) => s.replace(/\s+/g, ' ');

const plan = read('plans', 'markdown-viewer.md');
const browserPlan = read('plans', 'file-browser.md');
const guide = read('docs', 'guide.md');
const trail = read('ui', 'webview', 'file-trail.ts');
const viewer = read('ui', 'webview', 'file-view.ts');
const icons = read('ui', 'webview', 'icons.ts');
const sheets = { 'styles.css': read('ui', 'webview', 'styles.css'), 'feed.css': read('ui', 'webview', 'feed.css') };

// The section, hard wraps collapsed so an assertion survives a rewrap: from its heading to the next `## ` heading or
// the end of the plan. It follows "## Out of scope" and appears once.
const HEAD = '## Follow-on: Link navigation (2026-09-19)';
const headAt = plan.indexOf('\n' + HEAD + '\n');
assert.ok(headAt >= 0, 'the follow-on section is in the plan');
assert.equal(plan.indexOf('\n' + HEAD + '\n', headAt + 1), -1, 'the section appears once');
const scopeAt = plan.indexOf('\n## Out of scope\n');
assert.ok(scopeAt >= 0 && scopeAt < headAt, 'the section follows "## Out of scope"');
const nextAt = plan.indexOf('\n## ', headAt + 1);
const section = flat(plan.slice(headAt, nextAt < 0 ? plan.length : nextAt));

/** A string literal's text from the source: the first `"..."` after `marker`. */
function literalAfter(src, marker) {
  const at = src.indexOf(marker);
  assert.ok(at >= 0, marker + ' is in the source');
  const m = /"((?:[^"\\]|\\.)*)"/.exec(src.slice(at + marker.length));
  assert.ok(m, 'a string literal follows ' + marker);
  return m[1];
}
/** The text of `src` from `from` to the first `to` after it, both present. */
function between(src, from, to) {
  const a = src.indexOf(from);
  assert.ok(a >= 0, from + ' is in the source');
  const b = src.indexOf(to, a + from.length);
  assert.ok(b > a, to + ' follows ' + from);
  return src.slice(a, b);
}
const DECISIONS = ['L1. **A trail.**', 'L2. **Back and Forward.**', 'L3. **A figure opens in detail.**',
  'L4. **The picture view reached from a report.**', 'L5. **Browser history: not integrated.**',
  'L6. **No kernel change, no new route; one new kind of request leaves the machine.**'];

// ── the section's shape ─────────────────────────────────────────────────────────────────────────────

test('the section states the ask, what existed, six decisions, the tests and the open points, in that order, with no em dash', () => {
  const marks = ['The user asked (2026-09-19) for a way back after following a link inside a file', '**What existed.**', '**Decisions.**',
    ...DECISIONS, '**Tests.**', '**Open points for the owner.**'];
  let last = -1;
  for (const m of marks) {
    const at = section.indexOf(m);
    assert.ok(at > last, JSON.stringify(m) + ' follows the mark before it');
    last = at;
  }
  assert.ok(section.includes('with the build\'s deliberate departures from that contract recorded as the decisions'));
  assert.ok(section.includes('re-opening replaced whatever was up and never stacked'), 'what existed: the replace');
  assert.ok(section.includes('No navigation stack, no Back or Forward, and no history API use anywhere in the webview'), 'what existed: no Back');
  assert.ok(!section.includes(String.fromCharCode(0x2014)), 'no em dash (U+2014) in the section');
  for (let i = 1; i <= 8; i++) assert.ok(section.includes(' ' + i + '. '), 'open point ' + i + ' is numbered');
});

// ── L1: the trail module and the one door ──────────────────────────────────────────────────────────

test('L1: the trail module exports the functions the section names, the viewer imports it, its own openers take one door whose tag openFileView reads before its close guard, the move runs after the leave write, both exits end the trail, the reload keeps it, and a same-file target pushes nothing', () => {
  for (const fn of ['trailRoot', 'trailPush', 'trailBack', 'trailForward', 'trailSetView', 'trailEnd', 'trailBackTarget', 'trailForwardTarget', 'liveTrail', 'setTrail']) {
    assert.ok(trail.includes('export function ' + fn + '('), 'file-trail.ts exports ' + fn);
    assert.ok(section.includes('`' + fn + '`'), 'the section names ' + fn);
  }
  assert.match(trail, /^export type TrailState = \{ back: TrailEntry\[\]; current: TrailEntry \| null; forward: TrailEntry\[\] \};$/m, 'the state the section spells');
  assert.match(trail, /^export type TrailEntry = \{ path: string; sid: string \| null; view: TrailView \| null \};$/m, 'the entry');
  assert.match(viewer, /^import \{ [^}]*\bliveTrail\b[^}]*\} from "\.\/file-trail";/m, 'file-view.ts imports the trail module');
  assert.match(viewer, /^let trailNext: TrailHow \| null = null;$/m, 'the tag');
  assert.match(viewer, /^function openFromViewer\(how: TrailHow, path: string, sid: string \| null, at: At \| null\): void \{\n  trailNext = how;\n  try \{ openLinkedFile\(path, sid, at\); \} finally \{ trailNext = null; \}\n\}$/m, 'the one door');
  assert.ok(section.includes('the viewer\'s own opens go through one door, `openFromViewer` in file-view.ts'));
  assert.equal((viewer.match(/openLinkedFile\(/g) || []).length, 1, 'openLinkedFile is called from the door alone');
  assert.equal((viewer.match(/openFileView\(/g) || []).length, 6, 'openFileView( sites in file-view.ts: the declaration, the delegate\'s default, openFileClick, the conflict Reload, the relay and the figure door openFigureInViewer (file-trail.test.ts names each with its side of the door; the same universal the section states)');
  const open = between(viewer, 'export function openFileView(', '  const wrap = el("div");\n  wrap.id = "romp-fileview";');
  const tagAt = open.indexOf('const how = trailNext; trailNext = null;');
  const guardAt = open.indexOf('if (document.getElementById("romp-fileview") && closeGuard && !closeGuard()) return false;');
  assert.ok(tagAt >= 0 && guardAt > tagAt, 'openFileView reads and clears the tag before its close guard');
  assert.ok(section.includes('reads and clears the tag at its top, before its close guard'));
  const leaveAt = open.indexOf('runLeave();');
  const moveAt = open.indexOf('const trailView = moveTrail(how, path, sid ?? null);');
  assert.ok(leaveAt >= 0 && moveAt > leaveAt, 'the move runs after runLeave wrote the leaving file\'s place');
  const move = between(viewer, 'function moveTrail(how: TrailHow | null, path: string, sid: string | null): TrailView | null {', '\n}\n');
  assert.ok(move.includes('if (cur) s = trailSetView(s, rememberedPlaces.get(placeKey(cur.path, cur.sid))?.view ?? null);'), 'the entry\'s view is the leaving place\'s, by the file\'s key');
  assert.ok(move.includes('case "reload": setTrail(s); return null;'), 'a reload moves nothing');
  assert.ok(move.includes('if (cur && placeKey(cur.path, cur.sid) === placeKey(path, sid)) { setTrail(s); return null; }'), 'a target inside the shown file pushes nothing');
  assert.ok(move.includes('default: setTrail(trailRoot(entry)); return null;'), 'an untagged open roots a new trail');
  assert.ok(section.includes('A target inside the shown file (`report.md:40` followed from report.md) replaces the card and pushes nothing'));
  assert.ok(section.includes('an untagged open is from outside by construction'));
  assert.ok(viewer.includes('trailNext = "reload"; openFileView(path, sid, opts);'), 'the conflict Reload tags itself');
  assert.equal((viewer.match(/setTrail\(trailEnd\(\)\);/g) || []).length, 2, 'the trail ends in closeFileView and in openUrlView');
  const close = between(viewer, 'export function closeFileView(', 'export function openFileClick(');
  assert.ok(close.indexOf('if (closeGuard && !closeGuard()) return;') < close.indexOf('setTrail(trailEnd());'), 'closeFileView ends the trail once its guard has passed');
  assert.ok(section.includes('Closing the viewer ENDS the trail (closeFileView, once its guard has passed)'));
  assert.ok(section.includes('The alternative, keeping the trail for the page\'s life so that such a reopen finds its Back again, was not taken'));
  assert.ok(section.includes('A URL document replacing the viewer (openUrlView) ends the trail the same way'));
  assert.ok(viewer.includes('openFromViewer("push", p, sid || null, ln > 0 ? { line: ln } : x.dataset.frag ? { heading: x.dataset.frag } : null);'), 'the delegate\'s path link is a push');
});

// ── L2: the two buttons and the chords ─────────────────────────────────────────────────────────────

test('L2: two glyph buttons of the icon family stand first in the bar before the Files link, titled with the target\'s name or the word alone under aria-disabled, re-open their entry with no target in the entry\'s view, and the chords run through one capture-phase listener that stands down as the section says', () => {
  assert.match(icons, /^export const ICON_BACK = svg\('/m); assert.match(icons, /^export const ICON_FORWARD = svg\('/m);
  assert.ok(viewer.includes('const nav = el("span", "fileview-group fileview-nav");'), 'the group the section names');
  assert.ok(viewer.includes('b.innerHTML = dir === "back" ? ICON_BACK : ICON_FORWARD; b.dataset.icon = "1";'), 'the family\'s drawings');
  const navBtn = between(viewer, 'const navBtn = (dir: "back" | "forward"): HTMLButtonElement => {', '\n  };\n');
  assert.ok(navBtn.includes('if (!target) b.setAttribute("aria-disabled", "true");'), 'aria-disabled with nothing that way');
  assert.ok(!navBtn.includes('.disabled = '), 'never the disabled property');
  assert.ok(viewer.includes('nav.hidden = !trailBackTarget(trailNow) && !trailForwardTarget(trailNow);'), 'the group hidden when neither direction has a target (T367; the file review\'s round 2)');
  assert.ok(section.includes('The GROUP is HIDDEN when neither direction has a target'), 'as L2 says');
  assert.ok(navBtn.includes('openFromViewer(dir, target.path, target.sid, null);'), 'a press re-opens the entry with NO target');
  assert.ok(viewer.includes('bar.appendChild(nav);\n  // BACK to the listing'), 'the group is the bar\'s first child, the Files link after it');
  assert.ok(viewer.includes('back.textContent = "‹ Files"; back.title = "Back to the file listing";'), 'the Files link unchanged');
  assert.ok(trail.includes('const word = dir === "back" ? "Back" : "Forward";') && trail.includes('return target ? word + " to " + fileNameOf(target.path) : word;'), 'navTitle: the word and the file name, or the word alone');
  assert.ok(section.includes('("Back to report.md", `navTitle`)'));
  assert.ok(viewer.includes('if (trailView !== null) fmt.md = trailView;'), 'the entry\'s view is the view for that open');
  assert.ok(section.includes('the entry\'s recorded view is the view for that open (this open\'s `fmt.md` copy, unsaved'));
  // the chord table: Alt+Left and Alt+Right everywhere, Cmd+[ and Cmd+] on a Mac
  const chord = between(trail, 'export function navChord(', '\n}\n');
  assert.ok(chord.includes('if (e.altKey && !e.metaKey && !e.ctrlKey && !e.shiftKey) {') && chord.includes('if (e.key === "ArrowLeft") return "back";') && chord.includes('if (e.key === "ArrowRight") return "forward";'));
  assert.ok(chord.includes('if (mac && e.metaKey && !e.altKey && !e.ctrlKey && !e.shiftKey) {') && chord.includes('if (e.key === "[") return "back";') && chord.includes('if (e.key === "]") return "forward";'));
  assert.ok(section.includes('Alt+Left and Alt+Right, and on a Mac Cmd+[ and Cmd+] as well (`navChord`, pure over the event\'s fields)'));
  // one capture-phase listener, removed by the close hooks; the stand-downs, then the default taken, then the step
  assert.ok(viewer.includes('document.addEventListener("keydown", onNavKey, true);\n  closeHooks.push(() => document.removeEventListener("keydown", onNavKey, true));'));
  const onNav = between(viewer, 'const onNavKey = (e: KeyboardEvent) => {', 'document.addEventListener("keydown", onNavKey, true);');
  const order = ['if (e.defaultPrevented || !document.getElementById("romp-fileview")) return;', 'const dir = navChord(e, IS_MAC);', 'if (a && a !== document.body && isTypingTarget(a)) return;', 'if (editing) return;', 'e.preventDefault();', 'if (target) openFromViewer(dir, target.path, target.sid, null);'];
  let last = -1;
  for (const line of order) { const at = onNav.indexOf(line); assert.ok(at > last, 'onNavKey: ' + line + ' in order'); last = at; }
  assert.ok(section.includes('takes the browser\'s default (its history step, which would leave the page under an open viewer) whether or not the trail has a step that way'));
});

// ── L3: the figure control ─────────────────────────────────────────────────────────────────────────

test('L3: the control\'s words are the viewer\'s literal, quoted by the section and the guide; the one decision puts a marked glyph button after the anchor and never a wrapper; the target is the model\'s join or a tab; the click listener yields as the section says; the walks skip it; both sheets carry the rules under screen and the print block names it nowhere', () => {
  const words = literalAfter(viewer, 'export const FIGURE_OPEN_TITLE = ');
  assert.equal(words, 'Open the picture');
  assert.ok(section.includes('wears an "' + words + '" control (file-view.ts `decideFigureControl`, the one place a control is added or removed, over the verdict `figureWantsControl`)'), 'L3 names the one decision and its verdict');
  assert.ok(viewer.includes('function decideFigureControl(img: Element, filePath: string): void {') && viewer.includes('function figureWantsControl(img: Element, anchor: Element, filePath: string): boolean {'), 'which the source defines');
  assert.ok(guide.includes('**' + words + '**'), 'the guide names the button by the same words');
  assert.equal(literalAfter(viewer, 'const FIGOPEN_MARK = '), 'data-fv-figopen');
  assert.ok(section.includes('found by its mark `data-fv-figopen` and never by its class'));
  assert.match(icons, /^export const ICON_EXPAND = svg\('/m, 'the glyph in the icon family');
  const build = between(viewer, 'function decideFigureControl(img: Element, filePath: string): void {', 'function addFigureControls(');
  const want = between(viewer, 'function figureWantsControl(img: Element, anchor: Element, filePath: string): boolean {', 'function decideFigureControl(');
  assert.ok(want.includes('if (img.closest(\'[data-act="\' + GATE_ACT + \'"]\')) return false;'), 'a gated placeholder waits for its load');
  assert.ok(want.includes('if (figureTarget(img, filePath) === null) return false;'), 'nothing to open, no control');
  assert.ok(build.includes('b.title = FIGURE_OPEN_TITLE; b.setAttribute("aria-label", FIGURE_OPEN_TITLE);'));
  assert.ok(build.includes('parent.insertBefore(b, anchor.nextSibling);'), 'a sibling after the anchor, never a wrapper');
  assert.ok(build.includes('b.classList.add(FIGOPEN_CLASS + "-" + align);'), 'a floated figure\'s control floats with it');
  assert.ok(section.includes('It is the img\'s SIBLING, inserted right after `figureAnchor`\'s climb'));
  const target = between(viewer, 'function figureTarget(img: Element, filePath: string): FigureTarget | null {', '\n}\n');
  assert.ok(target.includes('const p = figurePath(filePath, dest);') && target.includes('if (p !== null) return { kind: "file", path: p };'), 'the model\'s join');
  assert.ok(target.includes('if (/^https?:/i.test(dest) || dest.startsWith("//")) return { kind: "web", href: absUrl(dest) };'), 'a remote picture is a tab');
  assert.ok(viewer.includes('import { headVerdict, mtimeMoved, ABSENT, figurePath } from "./file-comments-model";'), 'figurePath from the model');
  assert.equal((viewer.match(/addFigureControls\(box, doc\.path\);/g) || []).length, 1, 'added in mdBlock\'s file arm alone');
  assert.ok(viewer.includes('ctx.onClose(armFigureControls(body, path));'), 'the load listener, armed per open and dropped with the viewer');
  const clicks = viewer.split('body.addEventListener("click", (ev) => {');
  assert.equal(clicks.length, 3, 'two click listeners on the body: the links\' and the figures\'');
  const fig = clicks[2].split('\n  });\n')[0];
  for (const line of ['if (ev.defaultPrevented) return;', 'if (!img || linkOf(t)) return;', 'if (panelMark(t) && !wantsOwnTab(ev)) return;', 'if (asideOpen && !wantsOwnTab(ev)) return;', 'if (selectionOpenIn(box)) return;', 'openFigure(img, ev);']) assert.ok(fig.includes(line), 'the figure listener: ' + line);
  const openFig = between(viewer, 'const openFigure = (img: Element, ev: MouseEvent): void => {', '\n  };\n');
  assert.ok(openFig.includes('if (target.kind === "web") { openUrlTab(target.href); return; }'));
  assert.ok(openFig.includes('if (wantsOwnTab(ev) && openFileTab(target.path, sid || null)) return;'));
  assert.ok(openFig.includes('openFigureInViewer(target.path, sid || null);'), 'the plain click is the trail\'s push with no target, through the figure\'s own door (no Recent row)');
  assert.ok(section.includes('the figure\'s own click yields to a figure inside a link'));
  assert.ok(section.includes('the floor is read again at each change of the figure\'s own laid-out box (`watchFigureBoxes`'), 'the re-read at each reflow of the figure, by its function');
  assert.ok(viewer.includes('const figureWatch = watchFigureBoxes(body, path, ctx.onRendered);'), 'which the open arms once, beside the load and error pair');
  // the walks
  assert.match(read('ui', 'webview', 'anchor-map.ts'), /"fv-figerr",[^\n]*\n\s*"fv-figopen",/, 'anchor-map.ts CONTROL_CLASSES');
  assert.match(read('ui', 'webview', 'anchor-map.ts').replace(/\n \*  /g, ' '), /is not the note's\), and since the link-navigation follow-on the figure's Open the picture control \(`button\.fv-figopen`, a glyph with no text of its own\)\. \*\//, 'anchor-map.ts CONTROL_CLASSES header names the control, as reader-place.ts\'s twin does');
  assert.ok(read('ui', 'webview', 'anchor-map.ts').includes('const isFigureCompanion = (n: DNode): boolean => hasClass(n, "fv-figerr") || hasClass(n, "fv-figopen");'));
  assert.ok(read('ui', 'webview', 'reader-place.ts').includes('const CONTROL_CLASSES = ["code-copy", "katex", "md-fnback", "md-frontmatter-head", "fv-gate", "fv-figerr", "fv-figopen"];'));
  assert.ok(viewer.includes('const n = (figureControlAfter(anchor) || anchor).nextSibling;'), 'the label lookup steps past the control');
  // the sheets: the same fv-figopen rule lines in both, every reveal under screen, none in the print block
  const REST = '.fileview-md .fv-figopen { position: relative; z-index: 1; vertical-align: top; margin: 0 6px 0 -28px; top: 6px; padding: 3px; background: var(--bg); opacity: 0; }';
  const REVEAL = '@media screen { .fileview-md :hover + .fv-figopen, .fileview-md .fv-figopen:hover, .fileview-md .fv-figopen:focus-visible { opacity: 1; } }';
  const NOHOVER = '@media screen and (hover: none) { .fileview-md .fv-figopen { opacity: 0.8; } }';
  const ruleLines = (css) => css.split('\n').filter((l) => /fv-figopen/.test(l) && /\{/.test(l) && !/^\s/.test(l) && !l.startsWith('/*'));
  const lines = Object.fromEntries(Object.entries(sheets).map(([n, css]) => [n, ruleLines(css)]));
  assert.deepEqual(lines['styles.css'], lines['feed.css'], 'the rule lines are the same in both sheets');
  for (const [name, css] of Object.entries(sheets)) {
    assert.ok(css.includes('\n' + REST + '\n'), name + ': the rest');
    assert.ok(css.includes('\n.fileview-md .fv-figopen-left { float: left; }\n.fileview-md .fv-figopen-right { float: right; margin: 0 -28px 0 6px; }\n'), name + ': the float twins');
    assert.ok(css.includes('\n' + REVEAL + '\n'), name + ': the reveal under screen');
    assert.ok(css.includes('\n' + NOHOVER), name + ': no hover keeps it visible, under screen');
    for (const l of lines[name]) if (/opacity: (?:1|0\.8)/.test(l)) assert.ok(l.startsWith('@media screen'), name + ': a reveal outside screen: ' + l);
    const printAt = css.indexOf('\n@media print {');
    assert.ok(printAt >= 0, name + ': the print block');
    assert.ok(!css.slice(printAt, css.indexOf('\n}', printAt)).includes('fv-figopen'), name + ': the print block names the control nowhere');
    assert.ok(css.includes('.fileview-btn.fileview-icon { display: inline-flex;'), name + ': the family\'s inline-flex box the section names');
  }
  assert.ok(section.includes('every reveal under `screen`, so a print shows none of it and the print block carries no line for it'));
  assert.ok(section.includes('a right float\'s at the top-LEFT corner (`fv-figopen-left`, `fv-figopen-right`'));
});

// ── L4: the picture view reached from a report ─────────────────────────────────────────────────────

test('L4: the browser leg reads the bar\'s name and the Back title after Enter on the control, and the section defers the zoom control', () => {
  const leg = read('ui', 'webview', 'file-figure-open-browser.test.ts');
  assert.ok(leg.includes('enabledTo(n.back, "Back to report.md", "L4: the picture view reached from the report names the report on Back");'));
  assert.ok(leg.includes('assert.equal(await base(page), "plot.svg", "the bar shows the picture\'s name");'));
  assert.ok(section.includes('Back is enabled with the report\'s name in its title ("Back to report.md"), L1\'s push'));
  assert.ok(section.includes('No zoom control in this slice: a Fit / 1:1 toggle on the picture view is recorded as a follow-on for the owner (open point 2)'));
  assert.ok(section.includes('2. A Fit / 1:1 toggle on the picture view (L4)'));
});

// ── L5 and L6: no history API, nothing new leaves the machine ──────────────────────────────────────

test('L5 and L6: no history API call in the trail or the viewer; the trail module imports nothing and fetches nothing; L6 names its two verifications from the merge-base with origin/main, and they hold here wherever that ref is known', (t) => {
  for (const [name, src] of [['file-trail.ts', trail], ['file-view.ts', viewer]]) {
    assert.ok(!/\b(?:pushState|replaceState|hashchange)\b/.test(src), name + ': no pushState, replaceState or hashchange');
    assert.ok(!/\bhistory\.(?:back|forward|go)\(/.test(src), name + ': no history step of its own');
  }
  assert.ok(section.includes('no pushState, no hashchange, no history API call in file-trail.ts or file-view.ts'));
  assert.ok(section.includes('1. Browser history. The trail is the viewer\'s own (L5)'));
  assert.equal([...trail.matchAll(/^import /gm)].length, 0, 'file-trail.ts imports nothing');
  assert.ok(!/\bfetch\(/.test(trail), 'and fetches nothing');
  // L6's verifications are derived from the merge-base with main, never from a fixed sha: the build's record read the branch
  // point (34142c262), which the merge of main into the branch made an ancestor of main, so the same command named four kernel
  // files at the merged head (the file review, fresh-1). The prose names the command; here it is run, wherever origin/main is
  // known (a clone with the ref; a shallow CI checkout of a pull request has none and holds the prose alone, said so below).
  assert.ok(section.includes('`git diff --stat $(git merge-base origin/main HEAD) HEAD -- kernel/` is empty'), 'L6 names the kernel stat from the merge-base');
  assert.ok(section.includes('`git diff --name-only $(git merge-base origin/main HEAD) HEAD` lists files under ui/webview, docs, plans, tools, upstream or tests alone'), 'and the listing from the merge-base');
  assert.ok(!section.includes('git diff --stat 34142c262') && !section.includes('git diff --name-only 34142c262'), 'no verification against the branch point remains');
  const count = /upstream or tests alone \((\d+) files, the ledger entry's where line/.exec(section);
  assert.ok(count, 'L6 counts the listing beside the command');
  assert.ok(exists('upstream', '2026-09-19-linknav-trail-back-forward.md'), 'the ledger entry the section names');
  const git = (...args) => execFileSync('git', args, { cwd: REPO, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
  let base = null;
  try { base = git('merge-base', 'origin/main', 'HEAD'); } catch { base = null; }
  if (!base) { t.diagnostic('origin/main is not known in this checkout: L6\'s verifications are held by their prose alone here'); return; }
  const head = git('rev-parse', 'HEAD');
  assert.equal(git('diff', '--stat', base, 'HEAD', '--', 'kernel/'), '', 'no kernel change since the merge-base ' + base);
  const files = git('diff', '--name-only', base, 'HEAD').split('\n').filter(Boolean);
  const DIRS = ['ui/webview/', 'docs/', 'plans/', 'tools/', 'upstream/', 'tests/'];
  for (const f of files) assert.ok(DIRS.some((d) => f.startsWith(d)), f + ' lies under one of the six directories L6 names');
  if (base === head) { t.diagnostic('HEAD is the merge-base (the branch is merged, or this is main): the count is not re-derived'); return; }
  assert.equal(files.length, Number(count[1]), 'L6 says the listing since the merge-base has ' + count[1] + ' files; it has ' + files.length + ': ' + files.join(', '));
});

// ── the guide and the browser plan ─────────────────────────────────────────────────────────────────

const FIRST = 'The viewer keeps a trail of the files you reach through the links inside a file. Two arrow buttons appear at the left of its title bar once you have followed a link (there are none before that): **Back** returns you to the file you followed a link from, and **Forward** to the file you came back from, each at the place and in the view you left it (while you are not editing the file and no text box holds the keyboard, Cmd+[ and Cmd+] on a Mac do the same, and so do Alt+Left and Alt+Right on a Files or chat page open in a browser tab of its own; in the dashboard those two keys move the keyboard between the panes); a file opened from the chat, from a listing or from the Files pane\'s **Recent** list starts the trail over, and closing the viewer ends it.';
const SECOND = 'A picture in a rendered file that comes from a file or a web address has an **Open the picture** button at its top-right corner (top-left for a picture floated to the right), shown while the pointer is over the picture or the button holds the keyboard focus, that opens the picture on its own in the viewer, with Back returning you to the file at that place; a plain click on the picture does the same while the Comments panel is closed (with the panel open, a click offers a comment as before, and a drag draws a rectangle unless it starts on the button, which takes the press), a Cmd-click (Ctrl on Windows and Linux) opens the picture in a browser tab, and a picture from the web opens its address in a new tab, as a link to that site does; a figure waiting behind its host\'s box gets its button once it has loaded, as does one still on its way (a click on it before then opens nothing), and once the browser has answered for a picture, four kinds have none: a picture that failed to load, which opens nothing either; a `data:` picture, whose bytes are written into the file itself and which does not open; a picture smaller than 48 pixels on either side (a badge, an inline icon), which the button would cover, and which a plain click still opens when no link holds it; and a picture inside a link that holds more than the picture (a caption beside it), where a click follows the link (a link with no address left, or an anchor that only marks a place, leaves the click to the picture, which opens), while a picture that is all its link holds keeps its button beside the link.';
const POINTER = 'Since 2026-09-19 the viewer keeps a trail of its own beneath this stack, the files reached through the links inside a shown file and the pictures opened from its figures, with Back and Forward glyphs at the left of its bar once a step exists either way (the pair hidden until then), and the two do not meet: a file picked from the listing starts the trail over, the "‹ Files" link keeps closing the viewer to the listing, and closing the viewer ends the trail (plans/markdown-viewer.md, "Follow-on: Link navigation", L1 to L4).';

test('the guide\'s Links in a file paragraph ends with the two sentences, whole, after the drag sentence; the old wording is gone; the in-place sentence still stands; the browser plan\'s pointer is one sentence in its navigation-stack section', () => {
  const label = '**Links in a file.**';
  const at = guide.indexOf(label);
  assert.ok(at >= 0, 'the paragraph');
  const para = flat(guide.slice(at, guide.indexOf('\n\n', at)));
  assert.ok(para.endsWith('rather than opens. ' + FIRST + ' ' + SECOND), 'the two sentences close the paragraph: ' + JSON.stringify(para.slice(-300)));
  // the first record's six-sentence wording: its figure sentence read "corner, shown while ... focus: it opens", its Back sentence "go back to the file ... and forward again"
  assert.ok(!flat(guide).includes('top-right corner, shown while the pointer is over the picture or the button holds the keyboard focus: it opens'), 'the first record\'s figure sentence is gone');
  assert.ok(!flat(guide).includes('go back to the file you followed the link from and forward again'), 'and its Back sentence with it');
  // the records commit's wording, rewritten in the review (Forward stated, the Recent list placed in the Files pane, the gated and
  // data: pictures named): its trail sentence opened "inside a file: **Back** and **Forward**, the two arrow buttons", its figure
  // sentence "Every picture in a rendered file has an"
  assert.ok(!flat(guide).includes('inside a file: **Back** and **Forward**, the two arrow buttons'), 'the records commit\'s trail sentence is gone');
  assert.ok(!flat(guide).includes('Every picture in a rendered file has an **Open the picture**'), 'and its figure sentence with it');
  assert.ok(!flat(guide).includes('from the **Recent** list starts the trail over'), 'the Recent list is the Files pane\'s');
  // the review's round 1 wording, found false by execution in round 2 (the arrow chords with no dashboard exception; the button
  // on every picture from a file or the web): its chord clause and its figure sentence's opening
  assert.ok(!flat(guide).includes('(Alt+Left and Alt+Right, or Cmd+[ and Cmd+] on a Mac, do the same while no text box holds the keyboard)'), 'the round-1 chord clause is gone');
  assert.ok(!flat(guide).includes('Every picture in a rendered file that comes from a file or a web address has an'), 'and the round-1 figure sentence with it');
  // the file review's round 3 (regression-1 with ui-1): the trail sentence promised the two arrow buttons with no condition, while
  // the pair is hidden until a step exists either way (every open from outside the viewer), so it now says when they appear
  assert.ok(!flat(guide).includes('with two arrow buttons at the left of its title bar'), 'the unconditioned arrow clause is gone');
  assert.equal((flat(guide).match(/once you have followed a link \(there are none before that\)/g) || []).length, 1, 'the condition is stated once');
  assert.equal((flat(guide).match(/keeps a trail of the files you reach/g) || []).length, 1, 'the trail is described once in the guide');
  assert.ok(para.includes('A file path opens that file in the viewer, in place of the one you were reading'), 'the replace sentence stands: a link still opens in place, and now there is a way back');
  assert.ok(section.includes('The guide\'s Links in a file paragraph gained two sentences, the trail\'s and the figure control\'s, and the browser plan\'s navigation-stack section (plans/file-browser.md) a pointer sentence.'), 'the section says what the guide and the browser plan gained');
  // the browser plan: one sentence between the navigation-stack heading and the next
  const bp = flat(browserPlan);
  const stack = between(bp, '### Browser ↔ viewer: the navigation stack', '### Waiting, staleness, click-safety');
  assert.ok(stack.includes(POINTER), 'the pointer stands in the navigation-stack section: ' + JSON.stringify(stack.slice(-500)));
  assert.equal((stack.match(/Since 2026-09-19/g) || []).length, 1, 'one pointer');
  assert.ok(stack.includes('The viewer is a replace-never-stack singleton'), 'the paragraph\'s history is as written');
  assert.ok(!POINTER.includes(String.fromCharCode(0x2014)) && !FIRST.includes(String.fromCharCode(0x2014)) && !SECOND.includes(String.fromCharCode(0x2014)), 'no em dash');
});

// ── the tests the section names, two-way ───────────────────────────────────────────────────────────

const NUMBER_WORDS = { one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10 };
/** A test module's text with its comment wraps joined (a `//` or ` * ` line continues the sentence before it), so a
 *  claim wrapped across two comment lines is read as one. */
const claimText = (...parts) => flat(read(...parts).replace(/\r?\n[ \t]*(?:\/\/|\*(?!\/)) ?/g, ' '));
/** The test modules under `dir` whose names match `re` and whose own text names the follow-on: a module that says it
 *  tests the follow-on is one the record must name. */
const CLAIM = /link-navigation follow-on|Follow-on: Link navigation/;
const claimants = (dir, re) => fs.readdirSync(path.join(REPO, ...dir)).filter((f) => re.test(f) && CLAIM.test(claimText(...dir, f))).sort();

test('every ui/webview/file-trail*.test.ts and file-figure-open*.test.ts is named in the section and the count the section gives is the listing\'s, every module the section names exists, and the section names this module', () => {
  const tests = section.slice(section.indexOf('**Tests.**'));
  const onDisk = fs.readdirSync(path.join(REPO, 'ui', 'webview')).filter((f) => /^(?:file-trail|file-figure-open).*\.test\.ts$/.test(f)).sort();
  assert.ok(onDisk.length >= 4, 'the follow-on\'s modules are on disk: ' + onDisk.join(', '));
  for (const f of onDisk) assert.ok(tests.includes('ui/webview/' + f), f + ' is named in the Tests paragraph');
  const count = /`ls ui\/webview\/file-trail\*\.test\.ts ui\/webview\/file-figure-open\*\.test\.ts` lists the follow-on's (\w+) modules/.exec(section);
  assert.ok(count, 'the section names the command that produces the list and counts its modules');
  assert.equal(NUMBER_WORDS[count[1]] ?? Number(count[1]), onDisk.length, 'the section says the listing produces ' + count[1] + ' modules; today it produces ' + onDisk.length + ': ' + onDisk.join(', '));
  const named = [...new Set([...section.matchAll(/\b([\w-]+\.test\.(?:ts|mjs))\b/g)].map((m) => m[1]))];
  assert.ok(named.length >= onDisk.length + 8, 'the section names the follow-on\'s modules, the re-aimed suites and this pin (' + named.length + ')');
  for (const f of named) {
    const where = f.endsWith('.mjs') ? ['tools', f] : ['ui', 'webview', f];
    assert.ok(exists(...where), f + ' exists under ' + where.slice(0, -1).join('/'));
  }
  for (const f of new Set([...section.matchAll(/\btests\/(test_\w+\.py)\b/g)].map((m) => m[1]))) assert.ok(exists('tests', f), f + ' exists under tests');
  assert.ok(named.includes(path.basename(fileURLToPath(import.meta.url))), 'the section names this pin');
});

test('every test module that names the follow-on in its own text is named in the section\'s Tests paragraph: the re-aimed suites outside the two stems among them', () => {
  const tests = section.slice(section.indexOf('**Tests.**'));
  const legs = claimants(['ui', 'webview'], /\.test\.ts$/);
  const pins = claimants(['tools'], /\.test\.mjs$/);
  const py = claimants(['tests'], /^test_\w+\.py$/);
  assert.ok(legs.length >= 4 && pins.length >= 1, 'the claimants are on disk: ' + [...legs, ...pins, ...py].join(', '));
  assert.ok(legs.some((f) => !/^(?:file-trail|file-figure-open)/.test(f)), 'at least one leg lies outside the two stems, which is why this test exists');
  for (const f of legs) assert.ok(tests.includes('ui/webview/' + f), 'ui/webview/' + f + ' names the follow-on and is named in the Tests paragraph');
  for (const f of pins) assert.ok(tests.includes('tools/' + f), 'tools/' + f + ' names the follow-on and is named in the Tests paragraph');
  for (const f of py) assert.ok(tests.includes('tests/' + f), 'tests/' + f + ' names the follow-on and is named in the Tests paragraph');
});
