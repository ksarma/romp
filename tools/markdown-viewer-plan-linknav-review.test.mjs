// The review's corrections to the record of the link-navigation follow-on (plans/markdown-viewer.md, "## Follow-on: Link
// navigation (2026-09-19)"), held to the tree beside tools/markdown-viewer-plan-linknav.test.mjs, which holds the record as
// the build wrote it. The review's round 1 changed the figure control's rules in ui/webview/file-view.ts (figureTarget tests
// the web address before the model's join; a floor of FIGOPEN_MIN_PX on either side, read from the loaded picture, with the
// control a paint added removed at the load; no control inside a link holding more than the figure, linkAbove; the bare
// figure's click yields to an anchor with an href) and added two test modules, and the record went on saying that every
// picture wears the control and that every file the branch changes lies under five directories, none of them tests/
// (round 2 found both). Each correction is read here from its source, so that the number or the name in the record is the
// source's: L3 names the floor's constant and the number the source gives it, both exclusions with their functions, the web
// test's place before the join and the click's yield; L3's Held-by sentence and the Tests paragraph name the two shapes
// modules, which exist; L6 names tests among the directories and the two files under it, which the Tests paragraph names
// too, and no longer calls the records commit the follow-on's last. The review's consolidation added the last test: round 2
// made figureTarget read the candidate the browser chose (chosenSource) and added two modules for it, and the record still
// said the authored source and named neither; L1's Held-by sentence named the pure cases and the wiring pins of a module that
// also drives the conflict Reload in Chromium; and open point 1 gave Alt+Left the trail's meaning under history integration
// where the dashboard's shell takes the key first. Synthetic: only the repo's own text.
// Run: node --test tools/markdown-viewer-plan-linknav-review.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');
const exists = (...parts) => fs.existsSync(path.join(REPO, ...parts));
const flat = (s) => s.replace(/\s+/g, ' ');

const plan = read('plans', 'markdown-viewer.md');
const viewer = read('ui', 'webview', 'file-view.ts');

const HEAD = '## Follow-on: Link navigation (2026-09-19)';
const headAt = plan.indexOf('\n' + HEAD + '\n');
assert.ok(headAt >= 0, 'the follow-on section is in the plan');
const nextAt = plan.indexOf('\n## ', headAt + 1);
const section = flat(plan.slice(headAt, nextAt < 0 ? plan.length : nextAt));

/** The text of `src` from `from` to the first `to` after it, both present. */
function between(src, from, to) {
  const a = src.indexOf(from);
  assert.ok(a >= 0, from + ' is in the source');
  const b = src.indexOf(to, a + from.length);
  assert.ok(b > a, to + ' follows ' + from);
  return src.slice(a, b);
}
/** `marks` stand in `src` in this order, each sought after the one before it. */
function inOrder(src, marks, what) {
  let last = -1;
  for (const m of marks) {
    const at = src.indexOf(m, last + 1);
    assert.ok(at > last, what + ': ' + JSON.stringify(m) + ' in order');
    last = at;
  }
}
const L3 = between(section, 'L3. **A figure opens in detail.**', 'L4. **The picture view reached from a report.**');
const L6 = between(section, 'L6. **Nothing leaves the machine that did not before.**', '**Tests.**');
const tests = between(section, '**Tests.**', '**Open points for the owner.**');
const SHAPES = ['file-view-figure-shapes.test.ts', 'file-view-figure-shapes-browser.test.ts'];

test('L3 opens on the exceptions it names, and names the floor by the source\'s constant and number, the measure, the drop at the load, and the link exclusion by its function, in the order the builder runs them', () => {
  assert.ok(L3.includes('with the exceptions this decision names (a picture with nothing to open, a gated placeholder until its load, a figure under the size floor, a figure inside a link holding more than it), wears an "Open the picture" control'),
    'the first sentence carries the exceptions rather than claiming every picture');
  const floor = /^const FIGOPEN_MIN_PX = (\d+);$/m.exec(viewer);
  assert.ok(floor, 'the source declares the floor');
  const px = floor[1];
  assert.ok(L3.includes('a figure under ' + px + ' CSS px on either side (`FIGOPEN_MIN_PX`'), 'L3 gives the floor the source\'s number, ' + px);
  assert.ok(L3.includes('a figure at the floor (' + px + ' by ' + px + ') keeps its control inside its own box'), 'and the figure at the floor keeps its control');
  for (const fn of ['figureBox', 'figureTooSmall', 'linkAbove']) {
    assert.ok(viewer.includes('function ' + fn + '('), 'the source defines ' + fn);
    assert.ok(L3.includes('`' + fn + '`'), 'L3 names ' + fn);
  }
  assert.ok(L3.includes('the paint, which runs before the load, adds the control and the load (armFigureControls, the same builder) removes the one on a figure the measure finds under the floor'));
  assert.ok(L3.includes('a figure inside a link that holds more than it (`[![alt](fig.png) caption](other.md)`'));
  assert.ok(L3.includes('a figure alone in a link keeps its control, after the link'));
  const want = between(viewer, 'function figureWantsControl(img: Element, anchor: Element, filePath: string): boolean {', 'function decideFigureControl(');
  inOrder(want, ['if (state === "fetching" || state === "failed") return false;', 'if (figureTooSmall(img)) return false;', 'if (figureTarget(img, filePath) === null) return false;', 'return linkAbove(anchor) === null;'], 'figureWantsControl: the state, the floor, the target, the link');
  const build = between(viewer, 'function decideFigureControl(img: Element, filePath: string): void {', 'function addFigureControls(');
  inOrder(build, ['const anchor = figureAnchor(img);', 'if (standing) { if (!want) standing.remove(); return; }', 'parent.insertBefore(b, anchor.nextSibling);'], 'decideFigureControl: the one place a control is added or removed');
  const small = between(viewer, 'function figureTooSmall(img: Element): boolean {', '\n}\n');
  assert.ok(small.includes('b.w < FIGOPEN_MIN_PX || b.h < FIGOPEN_MIN_PX'), 'under the floor on either side, as L3 says');
  const arm = between(viewer, 'function armFigureControls(body: HTMLElement, filePath: string): () => void {', '\n}\n');
  assert.ok(arm.includes('if (img && figureState(img) !== "standin") decideFigureControl(img, filePath);'), 'the load and the error run the one decision, where the measure is read');
  assert.ok(arm.includes('body.addEventListener("error", decide, true);'), 'the error too: a failed figure is decided (no control)');
  // the re-read at each change of the body's width (the review's measurement: read once at the load, a narrowed figure kept its control)
  assert.ok(L3.includes('the floor is read again at each change of the body\'s width (`refigureControls`'), 'L3 names the re-read and its function');
  assert.ok(L3.includes('a value measured once against a condition that can change is re-read on the event that changes it'), 'L3 states the class');
  const refigure = between(viewer, 'function refigureControls(body: HTMLElement, filePath: string): void {', '\n}\n');
  assert.ok(refigure.includes('body.querySelectorAll(".fileview-md img").forEach((img) => { decideFigureControl(img, filePath); });'), 'the source decides every figure of the box again through the one decision');
  const repaint = between(viewer, 'const repaint = () => {', '\n  };\n');
  inOrder(repaint, ['if (unmeasurable()) return;', 'landRemembered(); landTarget();', 'retakeAfterHide();', 'refigureControls(body, path);'], 'the width watch\'s repaint runs the re-read over a body with a box, after the seat');
  const FLOOR_LEG = 'file-view-figure-floor-browser.test.ts';
  assert.ok(exists('ui', 'webview', FLOOR_LEG), FLOOR_LEG + ' exists');
  assert.ok(L3.slice(L3.indexOf('Held by')).includes(FLOOR_LEG), 'L3\'s Held-by sentence names ' + FLOOR_LEG);
  assert.ok(tests.includes('ui/webview/' + FLOOR_LEG), 'the Tests paragraph names ui/webview/' + FLOOR_LEG);
});

test('L3 puts the web test first in figureTarget, as the source does, and names the bare figure\'s yield to an anchor with an href, which the figure listener carries after the links\' yield', () => {
  const target = between(viewer, 'function figureTarget(img: Element, filePath: string): FigureTarget | null {', '\n}\n');
  inOrder(target, ['if (/^https?:/i.test(dest) || dest.startsWith("//")) return { kind: "web", href: absUrl(dest) };', 'const p = figurePath(filePath, dest);'], 'figureTarget');
  assert.ok(L3.includes('What it opens (`figureTarget`): a remote picture (an http or https source, a protocol-relative one) in a tab, never the viewer, the web test run FIRST, before the model\'s join'));
  const clicks = viewer.split('body.addEventListener("click", (ev) => {');
  assert.equal(clicks.length, 3, 'two click listeners on the body: the links\' and the figures\'');
  inOrder(clicks[2].split('\n  });\n')[0], ['if (ev.defaultPrevented) return;', 'if (!img || linkOf(t)) return;', 'if (img.closest("a[href]")) return;', 'openFigure(img, ev);'], 'the figure listener');
  assert.ok(L3.includes('stands down on a click another listener already answered (`ev.defaultPrevented`, its first line)'), 'L3 names the stand-down on an answered click');
  assert.ok(L3.includes('the figure\'s own click yields to a figure inside a link (the author\'s link, through the links listener; and an anchor with an href that listener leaves to the browser'));
});

test('the two shapes modules the round added exist, name the follow-on, and are named in L3\'s Held-by sentence and in the Tests paragraph', () => {
  for (const f of SHAPES) {
    assert.ok(exists('ui', 'webview', f), f + ' exists');
    assert.match(read('ui', 'webview', f), /link-navigation follow-on/, f + ' names the follow-on');
    assert.ok(L3.slice(L3.indexOf('Held by')).includes(f), 'L3\'s Held-by sentence names ' + f);
    assert.ok(tests.includes('ui/webview/' + f), 'the Tests paragraph names ui/webview/' + f);
  }
  assert.ok(tests.includes('The review\'s round 1 added two modules outside those two stems:'), 'the paragraph tells them from the build\'s four');
  assert.ok(tests.includes('tools/' + path.basename(fileURLToPath(import.meta.url))), 'the Tests paragraph names this pin');
});

test('L6 names tests among the directories the branch changes and the two files under it, which the Tests paragraph names too and which exist, and no longer calls the records commit the follow-on\'s last', () => {
  assert.ok(L6.includes('every file the branch changes is under ui/webview, docs, plans, tools, upstream or tests (`git diff --name-only 34142c262 HEAD`'), 'the directory list carries tests beside the command');
  assert.ok(!L6.includes('the last commit of the follow-on'), 'the records commit is not the branch\'s last');
  for (const f of ['test_guide_files_failures.py', 'test_guide_trail_chords_and_figure_button.py']) {
    assert.ok(L6.includes('tests/' + f), 'L6 names tests/' + f);
    assert.ok(exists('tests', f), 'tests/' + f + ' exists');
    assert.ok(tests.includes('tests/' + f), 'the Tests paragraph names tests/' + f);
  }
  assert.ok(L6.includes('both named in the Tests paragraph below'));
  assert.ok(!section.includes(String.fromCharCode(0x2014)), 'no em dash in the section');
});

// ── the consolidation's corrections ────────────────────────────────────────────────────────────────

const CHOSEN = ['file-view-figure-chosen.test.ts', 'file-view-figure-chosen-browser.test.ts'];
const L1 = between(section, 'L1. **A trail.**', 'L2. **Back and Forward.**');
const trailTest = read('ui', 'webview', 'file-trail.test.ts');

test('L3 names the candidate the browser chose by its function, which figureTarget reads first and the failed label delegates to, and names the two chosen modules, as the Tests paragraph does; both exist and name the follow-on', () => {
  assert.ok(viewer.includes('function chosenSource(img: Element): string | null {'), 'the source defines chosenSource');
  const target = between(viewer, 'function figureTarget(img: Element, filePath: string): FigureTarget | null {', '\n}\n');
  inOrder(target, ['const dest = chosenSource(img);', 'if (/^https?:/i.test(dest) || dest.startsWith("//")) return { kind: "web", href: absUrl(dest) };', 'const p = figurePath(filePath, dest);'], 'figureTarget');
  assert.ok(!target.includes('pictureDest(img)'), 'figureTarget reads the src alone nowhere: chosenSource applies that rule when the browser chose the src or has not picked');
  assert.ok(viewer.includes('function failedSource(img: Element): string | null {\n  return chosenSource(img);\n}'), 'the failed label delegates');
  assert.ok(L3.includes('else the file named by the candidate the browser chose for the figure, as the author wrote it (`chosenSource`'), 'L3 names chosenSource where the join was the authored source');
  assert.ok(L3.includes('the failed figure\'s label, `failedSource`, delegates to it'), 'and the delegation');
  assert.ok(!L3.includes('the file the authored source names'), 'the round-2 wording, the authored source, is gone');
  for (const f of CHOSEN) {
    assert.ok(exists('ui', 'webview', f), f + ' exists');
    assert.match(read('ui', 'webview', f), /Follow-on: Link navigation/, f + ' names the follow-on');
    assert.ok(L3.slice(L3.indexOf('Held by')).includes(f), 'L3\'s Held-by sentence names ' + f);
    assert.ok(tests.includes('ui/webview/' + f), 'the Tests paragraph names ui/webview/' + f);
  }
});

test('L1\'s Held-by sentence names the conflict Reload driven in Chromium, which file-trail.test.ts carries through the real viewer leg, and open point 1 keeps Alt+Left outside the dashboard, where the shell takes the key first', () => {
  assert.ok(L1.includes('Held by file-trail.test.ts (the pure cases, the three wiring pins, and the conflict bar\'s Reload file driven in Chromium at the module\'s end'), 'L1 names the Reload leg');
  assert.match(trailTest, /import \{[^}]*\} from "\.\/real-viewer-leg";/, 'file-trail.test.ts drives the real viewer');
  assert.ok(trailTest.includes('the conflict bar\'s Reload file keeps the trail'), 'and carries the Reload leg by that name');
  assert.ok(trailTest.includes('"Reload file"'), 'the bar\'s button, read in the leg');
  const op1 = between(section, '1. Browser history. The trail is the viewer\'s own (L5).', '2. A Fit / 1:1 toggle');
  assert.ok(op1.includes('would give the browser\'s Back and a back-swipe the trail\'s meaning, and Alt+Left too outside the dashboard, whose shell takes the key first (open point 10)'), 'the premise names the dashboard exception');
  assert.ok(!op1.includes('a back-swipe and Alt+Left the trail\'s meaning'), 'the unconditional wording is gone');
  const op10 = between(section, '10. The chords inside the dashboard shell (L2).', 'is a ruling');
  assert.ok(op10.includes('takes Alt+Left and Alt+Right first on every pane document'), 'open point 10 is the one it points at');
});
