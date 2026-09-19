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
// too, and no longer calls the records commit the follow-on's last. Synthetic: only the repo's own text.
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
  for (const fn of ['figureBox', 'figureTooSmall', 'dropFigureControl', 'linkAbove']) {
    assert.ok(viewer.includes('function ' + fn + '('), 'the source defines ' + fn);
    assert.ok(L3.includes('`' + fn + '`'), 'L3 names ' + fn);
  }
  assert.ok(L3.includes('the paint, which runs before the load, adds the control and the load (armFigureControls, the same builder) removes the one on a figure the measure finds under the floor'));
  assert.ok(L3.includes('a figure inside a link that holds more than it (`[![alt](fig.png) caption](other.md)`'));
  assert.ok(L3.includes('a figure alone in a link keeps its control, after the link'));
  const build = between(viewer, 'function ensureFigureControl(img: Element, filePath: string): void {', 'function addFigureControls(');
  inOrder(build, ['if (figureTooSmall(img)) { dropFigureControl(img); return; }', 'const anchor = figureAnchor(img);', 'if (linkAbove(anchor)) return;', 'parent.insertBefore(b, anchor.nextSibling);'], 'ensureFigureControl');
  const small = between(viewer, 'function figureTooSmall(img: Element): boolean {', '\n}\n');
  assert.ok(small.includes('b.w < FIGOPEN_MIN_PX || b.h < FIGOPEN_MIN_PX'), 'under the floor on either side, as L3 says');
  const arm = between(viewer, 'function armFigureControls(body: HTMLElement, filePath: string): () => void {', '\n}\n');
  assert.ok(arm.includes('if (img) ensureFigureControl(img, filePath);'), 'the load runs the same builder, where the measure is read');
});

test('L3 puts the web test first in figureTarget, as the source does, and names the bare figure\'s yield to an anchor with an href, which the figure listener carries after the links\' yield', () => {
  const target = between(viewer, 'function figureTarget(img: Element, filePath: string): FigureTarget | null {', '\n}\n');
  inOrder(target, ['if (/^https?:/i.test(dest) || dest.startsWith("//")) return { kind: "web", href: absUrl(dest) };', 'const p = figurePath(filePath, dest);'], 'figureTarget');
  assert.ok(L3.includes('What it opens (`figureTarget`): a remote picture (an http or https source, a protocol-relative one) in a tab, never the viewer, the web test run FIRST, before the model\'s join'));
  const clicks = viewer.split('body.addEventListener("click", (ev) => {');
  assert.equal(clicks.length, 3, 'two click listeners on the body: the links\' and the figures\'');
  inOrder(clicks[2].split('\n  });\n')[0], ['if (!img || linkOf(t)) return;', 'if (img.closest("a[href]")) return;', 'openFigure(img, ev);'], 'the figure listener');
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
