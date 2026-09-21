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
// (L5); the trail module imports nothing and fetches nothing, and the checks keyed on the delta (L6's two verifications, the
// re-aimed count's comparison with it, and the browser legs' comparison with it, below) are run from the merge-base with origin/main where that base tells this
// branch's delta from main's tip, behind a two-part gate read off git: the
// merge-base is not origin/main itself, and the diff since it adds this module (the file review's round 4, extra8-1: the
// verifications are claims about this follow-on's delta, and the diff since the merge-base is that delta only on the open
// PR branch in a clone where origin/main has moved past the branch's last merge of it; main itself, a batch head cut from
// main's tip and this branch right after merging origin/main have their merge-base at origin/main, and a later branch after
// the follow-on has landed adds its own files and not this module, so on each the checks stand down and the diagnostic
// names the part of the gate that held them; before the gate they ran there and failed on a delta that was not this one's;
// a batch head that main has moved under passes both parts and fails the count on the other PRs' files, the gate's
// residual, disclosed here and in the plan and not closed, with a third part named for the maintainer in the PR body: the
// author's closing pass after the file review's round 4, attribution-and-gates-2 with records-2; and the checks keyed on the
// delta run in no CI job and in none after the merge, since the shell job that runs this module checks the pull request out
// at depth 1 with no origin/main and a landed follow-on's diff is some later branch's, so where landing is gated the prose
// alone carries L6 and the re-aimed count, re-derived by hand at the merged head: the file review's round 5, correctness-4,
// the plan's Tests paragraph stating it once with the checkouts, as a rule over those checks whose count is derived (every
// check this module keys on the delta runs through one door, `gated`, which records it, and the attribution module exports
// the count of its own; the sentence's number word is held to the sum, and each check is named in it: the file review's
// round 8, extra6-1, the sentence had named two of three and its pin held the bytes, so a widened, truer sentence
// was red), and this module holding the two CI jobs that run the tools and the UI tests to a
// checkout with no fetch-depth: 0, so a change there names the plan's sentence; the gate itself is a pure function over git's
// answers, gateOf, pinned in all four cells, this module's own path asserted to exist in the tree, and the running shape and
// the three hold-offs run against a temp repo shaped as the open PR branch: the file review's round 5, tests-7, since a
// hold-off is a pass and a misspelt path would have held the checks off for good behind a green diagnostic); the guide's two sentences are whole, the old wording
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
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { cssRules, renderRule, underScreen } from './css-rules.mjs';
import { execFileSync } from 'node:child_process';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');
const exists = (...parts) => fs.existsSync(path.join(REPO, ...parts));
const flat = (s) => s.replace(/\s+/g, ' ');
/** This module's own path: L6's verifications run only where the diff since the merge-base adds it (the second part of their gate). */
const THIS_MODULE = 'tools/markdown-viewer-plan-linknav.test.mjs';

/** L6's gate, a pure function over what git answers (the file review's round 5, tests-7: the gate had no test of either
 *  hold-off or the running shape, and a hold-off is a PASS): `base` is the merge-base with origin/main and `main` origin/main
 *  itself, both null where the ref is unknown; `added` the paths the diff since the merge-base adds. The verifications run
 *  where origin/main is known, the merge-base is not origin/main itself, and the diff adds `module`; otherwise `held` names
 *  the part that held them. */
export function gateOf(base, main, added, module) {
  if (!base) return { ran: false, held: 'no origin/main' };
  if (base === main) return { ran: false, held: 'the merge-base is origin/main' };
  if (!added.includes(module)) return { ran: false, held: 'the diff does not add the module' };
  return { ran: true, held: null };
}
const NOWHERE = '; the checks keyed on the delta run in no CI job and in none after the merge (the plan\'s Tests paragraph)';
/** What the diagnostic says for each part of the gate that held a check off, naming the check (the file review's landing
 *  round, extra6-1: the re-aimed count's stand-down had reused L6's message, so it was reported as L6's). */
const HELD = {
  'no origin/main': (name) => name + ' did not run: origin/main is not known in this checkout (CI\'s default-depth checkout); the prose alone holds it here' + NOWHERE,
  'the merge-base is origin/main': (name) => name + ' did not run: the merge-base with origin/main is origin/main itself (main itself, a branch or a batch head cut from main\'s tip, or this branch just after merging origin/main), so the diff since it is the whole history over main\'s tip and not this follow-on\'s delta; it runs on the open PR branch once main has moved past the branch\'s last merge of it' + NOWHERE,
  'the diff does not add the module': (name, base, module) => name + ' did not run: the diff since the merge-base ' + base + ' does not add ' + module + ' (a later branch after this follow-on landed, whose fork point main has moved past; or HEAD is main), so the diff is that branch\'s delta and not this follow-on\'s; it runs on the open PR branch once main has moved past the branch\'s last merge of it' + NOWHERE,
};
/** The delta L6 speaks of, read off git in `repo`: the gate, and where it ran, every file the diff since the merge-base lists
 *  (HEAD against the merge-base, the committed delta) and the kernel stat over the same span. */
function deltaOf(repo, module) {
  const git = (...args) => execFileSync('git', args, { cwd: repo, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
  let base = null;
  let main = null;
  try { base = git('merge-base', 'origin/main', 'HEAD'); main = git('rev-parse', 'origin/main'); } catch { base = null; }
  const status = base && base !== main ? git('diff', '--name-status', base, 'HEAD').split('\n').filter(Boolean).map((l) => l.split('\t')) : [];
  const gate = gateOf(base, main, status.filter((s) => s[0] === 'A').map((s) => s[1]), module);
  if (!gate.ran) return { gate, base, files: [], modified: [], kernel: '' };
  return { gate, base, files: status.map((s) => s[s.length - 1]), modified: status.filter((s) => s[0] === 'M').map((s) => s[1]), kernel: git('diff', '--stat', base, 'HEAD', '--', 'kernel/') };
}
/** The checks this module keys on the delta since the merge-base, by the names the plan's stand-down sentence gives them. */
const L6_CHECK = "L6's kernel stat and listing";
const REAIMED_CHECK = "the re-aimed count's comparison with the delta";
const LEGS_CHECK = "the browser legs' comparison with the delta";
/** Every check of this module keyed on the delta, by name, once it has been run or held off through `gated` below. */
const GATED_RAN = new Set();
/** The one door for a check keyed on the delta: deltaOf over this repository is called here and nowhere else (asserted in the
 *  last test), so GATED_RAN is the set of such checks and the plan's sentence counting them is held to it plus the
 *  attribution module's exported count. Where the gate holds, the diagnostic names the check that did not run. */
function gated(t, name, check, heldNote = '') {
  GATED_RAN.add(name);
  const d = deltaOf(REPO, THIS_MODULE);
  if (!d.gate.ran) { t.diagnostic(HELD[d.gate.held](name, d.base, THIS_MODULE) + heldNote); return; }
  check(d);
}

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
  assert.ok(viewer.includes('const figureWatch = watchFigureBoxes(body, path, ctx.onRendered);'), 'which the open sets up once, armed at each text paint through the seam\'s onRendered, the first paint\'s included (nothing is observed at the open: the body is empty then)');
  // the walks
  assert.match(read('ui', 'webview', 'anchor-map.ts'), /"fv-figerr",[^\n]*\n\s*"fv-figopen",/, 'anchor-map.ts CONTROL_CLASSES');
  assert.match(read('ui', 'webview', 'anchor-map.ts').replace(/\n \*  /g, ' '), /is not the note's\), and since the link-navigation follow-on the figure's Open the picture control \(`button\.fv-figopen`, a glyph with no text of its own\)\. \*\//, 'anchor-map.ts CONTROL_CLASSES header names the control, as reader-place.ts\'s twin does');
  assert.ok(read('ui', 'webview', 'anchor-map.ts').includes('const isFigureCompanion = (n: DNode): boolean => hasClass(n, "fv-figerr") || hasClass(n, "fv-figopen");'));
  // reader-place.ts's CONTROL_CLASSES is not copied here: a byte copy of the list pinned its contents and not whether a walk reads
  // them (the file review's round 8, correctness-1, dropped the two other copies; this third one went with
  // them). The entry's execution is md-config-figure-gate-place.test.ts's labelled scene, its count word file-figure-open.test.ts's
  // derived pin, and the structural exclusion file-view-place-blocks.test.ts's top-level figure.
  assert.ok(viewer.includes('const n = (figureControlAfter(anchor) || anchor).nextSibling;'), 'the label lookup steps past the control');
  // the sheets: the same fv-figopen rules in both, read as RULES through ./css-rules.mjs (the reader this home shares with
  // ui/webview/file-figure-open.test.ts: brace-matched over the comment-stripped sheet, each rule with the at-rules enclosing
  // it), every rule naming the control's class that reveals it under screen, none in the print block; the population is the
  // rules whose SELECTOR names the class, so a rule whose selector would match the control's element without naming the class
  // (`.fileview-md img + button`, an attribute selector, a universal) is outside what the set closes, a bound stated here, in
  // the messages, in L3 and in the reader's header rather than read (the author's closing pass after the file review's round 10,
  // mechanism-2)
  const REST = '.fileview-md .fv-figopen { position: relative; z-index: 1; vertical-align: top; margin: 0 6px 0 -28px; top: 6px; padding: 3px; background: var(--bg); opacity: 0; }';
  const REVEAL = '@media screen { .fileview-md :hover + .fv-figopen, .fileview-md .fv-figopen:hover, .fileview-md .fv-figopen:focus-visible { opacity: 1; } }';
  const NOHOVER = '@media screen and (hover: none) { .fileview-md .fv-figopen { opacity: 0.8; } }';
  const HOVER_BG = '.fileview-md .fv-figopen:hover { background: var(--bg) linear-gradient(var(--accent-wash), var(--accent-wash)); }';
  const LEFT = '.fileview-md .fv-figopen-left { float: left; }', RIGHT = '.fileview-md .fv-figopen-right { float: right; margin: 0 -28px 0 6px; }';
  /** The sheet's rules naming the control, each rendered on one line with whether a screen-only at-rule encloses it. */
  const controlRules = (css) => cssRules(css).filter((r) => /fv-figopen/.test(r.selector)).map((r) => ({ text: renderRule(r), screen: underScreen(r.chain) }));
  const rules = Object.fromEntries(Object.entries(sheets).map(([n, css]) => [n, controlRules(css)]));
  assert.deepEqual(rules['styles.css'], rules['feed.css'], 'the control\'s rules are the same in both sheets');
  for (const [name, css] of Object.entries(sheets)) {
    assert.ok(css.includes('\n' + REST + '\n'), name + ': the rest');
    assert.ok(css.includes('\n' + LEFT + '\n' + RIGHT + '\n'), name + ': the float twins');
    assert.ok(css.includes('\n' + REVEAL + '\n'), name + ': the reveal under screen');
    assert.ok(css.includes('\n' + NOHOVER), name + ': no hover keeps it visible, under screen');
    // the closed set over the parsed rules: outside a screen-only at-rule exactly the rest, the hover background and the float
    // twins, none a reveal, and every other rule naming the control under one, however the sheet writes it (the file review's
    // round 10, correctness-1 with tests-1 and ui-1: the set had been keyed on lines at column zero carrying the class and a
    // brace, so a reveal indented under an at-rule or on a grouped selector's continuation line stood outside it with every pin
    // green; the file review's round 8, fresh-4: the guard before the set matched two opacity spellings, so a reveal spelled any
    // other way outside screen passed it)
    assert.deepEqual(rules[name].filter((r) => !r.screen).map((r) => r.text), [REST, HOVER_BG, LEFT, RIGHT], name + ': the rules naming the control outside a screen-only at-rule, however the sheet writes them, are exactly the rest, the hover background and the float twins; any other rule naming the class there is one a print would apply (the population is the rules whose selector names the control\'s class; a rule whose selector would match the control\'s element without naming the class is outside what this set closes, a bound stated here and in the plan\'s L3, not read)');
    assert.deepEqual(rules[name].filter((r) => r.screen).map((r) => r.text), [REVEAL, NOHOVER], name + ': the rules under a screen-only at-rule are the reveal and the no-hover rule');
    const printAt = css.indexOf('\n@media print {');
    assert.ok(printAt >= 0, name + ': the print block');
    assert.ok(!css.slice(printAt, css.indexOf('\n}', printAt)).includes('fv-figopen'), name + ': the print block names the control nowhere');
    assert.ok(css.includes('.fileview-btn.fileview-icon { display: inline-flex;'), name + ': the family\'s inline-flex box the section names');
  }
  assert.ok(section.includes('every rule naming its class that reveals it under `screen`, so a print shows none of it and the print block carries no line for it (the set the two homes close is over the rules whose selector names the class'), 'L3 states the guard and the bound of the set that holds it');
  assert.ok(section.includes('a right float\'s at the top-LEFT corner (`fv-figopen-left`, `fv-figopen-right`'));
});

test('the rule reader the two homes of the closed set share (./css-rules.mjs): a sheet is read as rules with their enclosing at-rules, not as lines, so a rule indented under an at-rule, a grouped selector wrapped across lines, a one-line at-rule block and a column-zero rule read alike; a statement at-rule, a declaration-only at-rule and a comment yield no rule; a brace inside a string is text; whether a chain confines a rule to screens is a property of the whole query list; a nested block, an unbalanced brace and an open comment are refused (the file review\'s round 10, correctness-1 with tests-1 and ui-1)', () => {
  const sheet = [
    '/* a comment naming .fv-figopen { */',
    '.fileview-md .fv-figopen { opacity: 0; }',
    '@media (min-width: 1px) {',
    '  .fileview-md .fv-figopen { opacity: 1; }   /* indented under an at-rule a print matches too */',
    '}',
    '.fileview-md .fv-figerr,',
    '.fileview-md .fv-figopen { opacity: 1; }',
    '@media screen {',
    '  .fileview-md .fv-figopen:focus-visible { opacity: 1; }',
    '}',
    '@media screen and (hover: none) { .fileview-md .fv-figopen { opacity: 0.8; } }',
  ].join('\n');
  const control = cssRules(sheet).filter((r) => /fv-figopen/.test(r.selector));
  assert.deepEqual(control.map((r) => [renderRule(r), underScreen(r.chain)]), [
    ['.fileview-md .fv-figopen { opacity: 0; }', false],
    ['@media (min-width: 1px) { .fileview-md .fv-figopen { opacity: 1; } }', false],
    ['.fileview-md .fv-figerr, .fileview-md .fv-figopen { opacity: 1; }', false],
    ['@media screen { .fileview-md .fv-figopen:focus-visible { opacity: 1; } }', true],
    ['@media screen and (hover: none) { .fileview-md .fv-figopen { opacity: 0.8; } }', true],
  ], 'the column-zero rule, the indented reveal under (min-width: 1px) and the grouped selector\'s continuation-line reveal are rules outside screen, the indented rule inside the multi-line screen block and the one-line screen rule are under it, and the comment\'s brace is no rule');
  assert.deepEqual(cssRules('@supports (display: grid) { @media screen { .a { top: 0 } } }'), [{ selector: '.a', body: 'top: 0', chain: ['@supports (display: grid)', '@media screen'] }], 'the chain holds every enclosing at-rule, outermost first');
  assert.deepEqual(cssRules('.a::after { content: "{"; }\n.b[data-x="}"] { top: 0; }').map(renderRule), ['.a::after { content: "{"; }', '.b[data-x="}"] { top: 0; }'], 'a brace inside a string is text');
  assert.deepEqual(cssRules('@import "x.css";\n@font-face { font-family: F; src: url(f.woff2); }\n@keyframes k { from { opacity: 0; } to { opacity: 1; } }').map(renderRule), ['@keyframes k { from { opacity: 0; } }', '@keyframes k { to { opacity: 1; } }'], 'a statement at-rule and a declaration-only at-rule yield no rule; a keyframes step is a rule under its at-rule');
  assert.deepEqual(cssRules('.a,\n  .b\n{\n  top: 0;\n  left: 0;\n}').map(renderRule), ['.a, .b { top: 0; left: 0; }'], 'whitespace inside a selector list and a body is collapsed, so a rule renders the same however the sheet wrapped it');
  assert.throws(() => cssRules('.a { .b { top: 0; } }'), /CSS nesting/, 'a block inside a style rule is refused, not read');
  assert.throws(() => cssRules('.a { top: 0;'), /never closes/, 'an unclosed rule is refused');
  assert.throws(() => cssRules('@media screen { .a { top: 0; }'), /never closes/, 'an unclosed at-rule block is refused');
  assert.throws(() => cssRules('.a { top: 0; } }'), /no block open/, 'a stray close brace is refused');
  assert.throws(() => cssRules('/* open'), /never closes/, 'an open comment is refused');
  for (const chain of [['@media screen'], ['@media screen and (hover: none)'], ['@media only screen and (min-width: 1px) and (hover: none)'], ['@supports (display: grid)', '@media screen'], ['@media screen', '@media (min-width: 1px)']]) assert.equal(underScreen(chain), true, 'confined to screens: ' + JSON.stringify(chain));
  for (const chain of [[], ['@media (min-width: 1px)'], ['@media print'], ['@media print, screen'], ['@media screen, print'], ['@media screen and (hover: none), (min-width: 1px)'], ['@media not screen'], ['@media all'], ['@supports (display: grid)'], ['@container (max-width: 540px)']]) assert.equal(underScreen(chain), false, 'not confined to screens: ' + JSON.stringify(chain));
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

test('L5 and L6: no history API call in the trail or the viewer; the trail module imports nothing and fetches nothing; L6 names its two verifications from the merge-base with origin/main, and they hold on the open PR branch where main has moved past its last merge (the merge-base off origin/main and the diff adding this module), in no CI job and in none after the merge, which the plan says once and this module holds CI to', (t) => {
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
  // files at the merged head (the file review, fresh-1). The prose names the command; here it is run behind the two-part gate
  // the file review's round 4 (extra8-1) ruled for this module and the attribution test alike: the merge-base is not
  // origin/main itself, and the diff since it adds this module. Both parts hold on this follow-on's open PR branch in a clone
  // where origin/main has moved past the branch's last merge of it, and there the diff is the delta L6 speaks of; they hold
  // too on a batch head that main has moved under, where the diff is the batch's whole delta and the count fails on the
  // other PRs' files (the residual the header states). Elsewhere the diff is some other delta and the checks stand down,
  // saying which part held them: with the merge-base at origin/main (main itself, a branch or a batch head cut from main's
  // tip, this branch right after merging origin/main) the diff is the whole history over main's tip; on a later branch after the follow-on has landed the
  // diff adds that branch's files and not this module, however far main has moved. A checkout with no origin/main (CI's
  // default-depth checkout of a pull request) holds the prose alone. So the verifications run in no CI job and in none after
  // the merge (the file review's round 5, correctness-4): the plan's Tests paragraph says so once, with the checkouts, and the
  // premise is held here off ci.yml itself, the jobs whose steps run the tools tests and npm test checking out with no
  // fetch-depth: 0, so a job that starts fetching history names the plan's sentence to reword.
  // the plan's stand-down sentence, a rule over the checks keyed on the delta with their count, is held by the last test of
  // this module, once every gated check has run through `gated`
  const ci = read('.github', 'workflows', 'ci.yml');
  const jobsAt = ci.indexOf('\njobs:\n');
  assert.ok(jobsAt >= 0, 'ci.yml has a jobs: block');
  const jobs = ci.slice(jobsAt + 7).split(/\n(?=  [a-z][a-z-]*:\n)/).map((block) => block.replace(/^[ \t]*#.*$/gm, ''));
  const gating = jobs.filter((block) => /run: node --test tools\/\*\.test\.mjs/.test(block) || /run: npm test\b/.test(block));
  assert.equal(gating.length, 2, 'two CI jobs run the tools tests and npm test: ' + gating.map((b) => b.split('\n')[0].trim()).join(', '));
  for (const block of gating) {
    assert.ok(/uses: actions\/checkout@/.test(block), block.split('\n')[0].trim() + ' checks the repository out');
    assert.ok(!/fetch-depth:\s*0\b/.test(block), block.split('\n')[0].trim() + ' checks out at the default depth, with no origin/main, so the merge-base gate holds L6\'s verifications off there; a job that fetches history now runs them, and the plan\'s sentence that they run in no checkout that gates landing is to be reworded');
  }
  assert.ok(section.includes('`git diff --stat $(git merge-base origin/main HEAD) HEAD -- kernel/` is empty'), 'L6 names the kernel stat from the merge-base');
  assert.ok(section.includes('`git diff --name-only $(git merge-base origin/main HEAD) HEAD` lists files under ui/webview, docs, plans, tools, upstream or tests alone'), 'and the listing from the merge-base');
  assert.ok(!section.includes('git diff --stat 34142c262') && !section.includes('git diff --name-only 34142c262'), 'no verification against the branch point remains');
  const count = /upstream or tests alone[^()]*\((\d+) files, the ledger entry's where line/.exec(section);
  assert.ok(count, 'L6 counts the listing beside the command');
  assert.ok(exists('upstream', '2026-09-19-linknav-trail-back-forward.md'), 'the ledger entry the section names');
  assert.ok(exists(...THIS_MODULE.split('/')), 'THIS_MODULE names a file in the tree: ' + THIS_MODULE + ' (a misspelt path would hold the verifications off for good behind a green diagnostic; the file review\'s round 5, tests-7)');
  gated(t, L6_CHECK, (d) => {
    assert.equal(d.kernel, '', 'no kernel change since the merge-base ' + d.base);
    const DIRS = ['ui/webview/', 'docs/', 'plans/', 'tools/', 'upstream/', 'tests/'];
    for (const f of d.files) assert.ok(DIRS.some((dir) => f.startsWith(dir)), f + ' lies under one of the six directories L6 names');
    assert.equal(d.files.length, Number(count[1]), 'L6 says the listing since the merge-base has ' + count[1] + ' files; it has ' + d.files.length + ': ' + d.files.join(', '));
    t.diagnostic('L6\'s verifications ran: ' + d.files.length + ' files since the merge-base ' + d.base + ', none under kernel/, all under the six directories L6 names');
  });
});

// ── the guide and the browser plan ─────────────────────────────────────────────────────────────────

const FIRST = 'The viewer keeps a trail of the files you reach through the links inside a file and of the pictures you open from its figures. Two arrow buttons appear at the left of its title bar once there is a file to step back or forward to (after you follow a link or open a picture; there are none before that): **Back** returns you to the file you came from, and **Forward** to the file you came back from, each at the place and in the view you left it (while you are not editing the file and no text box holds the keyboard, Cmd+[ and Cmd+] on a Mac do the same, and so do Alt+Left and Alt+Right on a Files or chat page open in a browser tab of its own; in the dashboard those two keys move the keyboard between the panes); a file opened from the chat, from a listing or from the Files pane\'s **Recent** list starts the trail over, and closing the viewer ends it, as does, in the chat, following a link to a page on the dashboard\'s own web address that ends in .md: the page opens in the viewer in the file\'s place as a web document rather than a file of the session, and the trail ends there (in the Files pane such a link opens a tab, as any web address does, and the trail stands).';
const SECOND = 'A picture in a rendered file that comes from a file or a web address has an **Open the picture** button at its top-right corner (top-left for a picture floated to the right), shown while the pointer is over the picture or the button holds the keyboard focus, that opens the picture on its own in the viewer, with Back returning you to the file at that place; a plain click on the picture does the same while the Comments panel is closed (with the panel open, a click offers a comment as before, and so does a Cmd-click on the picture on a mouse or trackpad, and a drag draws a rectangle unless it starts on the button, which takes the press), a Cmd-click (Ctrl on Windows and Linux) on the picture while the panel is closed, or on the button at any time, opens the picture in a browser tab, and a picture from the web opens its address in a new tab, as a link to that site does; a figure waiting behind its host\'s box gets its button once it has loaded, as does one still on its way (a click on it before then opens nothing), and once the browser has answered for a picture, four kinds have none: a picture that failed to load, which opens nothing either; a `data:` picture, whose bytes are written into the file itself and which does not open; a picture smaller than 48 pixels on either side (a badge, an inline icon), which the button would cover, and which a plain click still opens when no link holds it; and a picture inside a link that holds more than the picture (a caption beside it), where a click follows the link (a link with no address left, or an anchor that only marks a place, leaves the click to the picture, which opens), while a picture that is all its link holds keeps its button beside the link.';
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
  assert.ok(!flat(guide).includes('(Alt+Left and Alt+Right, or Cmd+[ and Cmd+] on a Mac, do the same while no text box holds the keyboard)'), 'the review\'s round-1 chord clause is gone');
  assert.ok(!flat(guide).includes('Every picture in a rendered file that comes from a file or a web address has an'), 'and the review\'s round-1 figure sentence with it');
  // the file review's round 3 (regression-1 with ui-1): the trail sentence promised the two arrow buttons with no condition, while
  // the pair is hidden until a step exists either way (every open from outside the viewer), so it says when they appear; the
  // author's closing pass after the file review's round 3 (behaviour-2, records-1, coverage-1): the round-3 condition, a link followed, was false on the picture road (a
  // picture opened from a figure's control pushes the report onto the trail with no link followed, and the pair appears; the
  // figure-open leg executes it), so the condition is the trail's own, a file to step to, with both roads named
  assert.ok(!flat(guide).includes('with two arrow buttons at the left of its title bar'), 'the unconditioned arrow clause is gone');
  assert.ok(!flat(guide).includes('once you have followed a link (there are none before that)'), 'the file review\'s round-3 condition, false on the picture road, is gone');
  assert.equal((flat(guide).match(/once there is a file to step back or forward to \(after you follow a link or open a picture; there are none before that\)/g) || []).length, 1, 'the condition is stated once');
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

const NUMBER_WORDS = { one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10, eleven: 11, twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15, sixteen: 16, seventeen: 17, eighteen: 18, nineteen: 19, twenty: 20 };
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

test('the re-aimed sentence: its count is the number of pre-existing test modules the diff since the merge-base modifies, each named in it (behind L6\'s two-part gate, since the count is a claim about the branch\'s delta; the file review\'s landing round, tests-3: the text-keyed rule cannot see a module whose own text does not name the follow-on)', (t) => {
  const m = /(?:^| )(\w+) standing suites were re-aimed, not undone:/.exec(section);   // `section` is flat: one space where the line broke
  assert.ok(m, 'the Tests paragraph counts the re-aimed suites');
  const count = NUMBER_WORDS[m[1].toLowerCase()] ?? Number(m[1]);
  assert.ok(Number.isInteger(count) && count > 0, 'the count is a number word: ' + m[1]);
  const end = section.indexOf("The guide's Links in a file paragraph gained", m.index);
  assert.ok(end > m.index, 'the sentence runs to the guide\'s sentence');
  const sentence = flat(section.slice(m.index, end));
  const named = [...new Set([...sentence.matchAll(/\b((?:ui\/webview|tools|tests)\/[\w-]+\.(?:test\.ts|test\.mjs|py))\b/g)].map((x) => x[1]))];
  assert.equal(named.length, count, 'the sentence names as many test modules as it counts: ' + named.join(', '));
  gated(t, REAIMED_CHECK, (d) => {
    const TEST_MODULE = /^(?:ui\/webview\/[\w-]+\.test\.ts|tools\/[\w-]+\.test\.mjs|tests\/test_\w+\.py)$/;
    const reAimed = d.modified.filter((f) => TEST_MODULE.test(f)).sort();
    assert.equal(reAimed.length, count, 'the sentence says ' + m[1] + ' standing suites were re-aimed; the diff since the merge-base ' + d.base + ' modifies ' + reAimed.length + ' pre-existing test modules: ' + reAimed.join(', '));
    for (const f of reAimed) assert.ok(named.includes(f), f + ' is modified since the merge-base and named in the re-aimed sentence');
    t.diagnostic('the re-aimed count ran: ' + reAimed.length + ' pre-existing test modules modified since the merge-base ' + d.base);
  }, '; the re-aimed count is held to the sentence\'s own list alone here');
});

// ── the browser legs and the job that gates a landing (the file review's round 8, extra8-2) ────────────────────────────

/** The follow-on's browser legs, derived from the tree BY NAME: the `*-browser.test.ts` modules under ui/webview whose own text
 *  names the follow-on (claimants, above). A name, not the property that makes a module a browser leg (a call of the shared
 *  launcher's inBrowser through any binding, or a playwright package named), which PR 887's census reads off each module's tree
 *  with the compiler (vscode-extension/scripts/browser-legs-census.mjs, executed by the census test beside it under ui/webview
 *  in the vscode-extension job); this module runs in CI's Shell job with no compiler and reads no property, a spelling read here
 *  being a second definition, so once that census lands it is the one definition and this derivation stays a name. The plan's
 *  disclosure says so and names the modules of the follow-on's diff the property reaches and the name does not,
 *  ui/webview/file-trail.test.ts and ui/webview/file-view-text-size.test.ts, which nothing here holds (the file review's round
 *  10, extra6-1 and extra6-2). Two derivations must agree: the Tests paragraph's list of browser modules is the same set. */
const browserLegs = () => claimants(['ui', 'webview'], /-browser\.test\.ts$/);
/** A leg's source with its comments removed by their line shape, for the route checks below: a line whose text starts with `//`
 *  goes, and a block comment opened at a line's start goes through the line that closes it. The tools job runs this module with
 *  no node_modules, so the compiler's comment ranges (ui/test-code-only.ts) are out of reach here. A comment opened after code
 *  on its line stays: a `launch(` quoted there reds the launch check, the safe side and never a false green, and an import
 *  quoted there is not at a line's start, which the import check requires (the author's closing pass after the file review's
 *  round 8: the checks had read the raw source with an unanchored import regex and one launch spelling, so a
 *  leg with the import in a comment and a private `pw["chromium"]["launch"]()` was green). */
const codeLines = (src) => {
  const out = []; let inBlock = false;
  for (const line of src.split('\n')) {
    const t = line.trim();
    if (inBlock) { if (t.includes('*/')) inBlock = false; continue; }
    if (t.startsWith('//')) continue;
    if (t.startsWith('/*')) { if (!t.includes('*/', 2)) inBlock = true; continue; }
    out.push(line);
  }
  return out.join('\n');
};
/** Why a leg's code is not routed through the shared helper, or null: it imports inBrowser from real-viewer-leg.ts in an import
 *  statement at a line's start, calls launch on nothing, and stands itself down nowhere. A launch under any access spelling (a
 *  property access, an optional chain, a bracket holding a string literal) followed by a call is refused; a launch reached
 *  through a name computed at run time (`pw.chromium["la" + "unch"]()`) is outside this read, and a `launch` key in an object is
 *  no call and passes. A stand-down is the pair's other half (the file review's round 10, tests-2: the guard had refused the
 *  launch alone): a `skip` or `todo` call under the same spellings, a `skip:` or `todo:` option with its value written out,
 *  a `skip` or `todo` standing as a shorthand property between braces (node:test's `test(name, { skip }, fn)` form with the
 *  value declared under the option's own name, and the destructuring `const { skip } = t` that takes the method off the
 *  context), or a bare `skip(` or `todo(` call (the destructured method called; the author's closing pass after the file
 *  review's round 10, mechanism-1: the option read had needed the colon, so the shorthand the docstring itself named as the
 *  form passed, and so did the destructured call). Any of them defeats a roster's switch as a private launch does, since the
 *  switch turns the shared helper's launch skip into a failure and a leg that skips itself never reaches it; the convention's
 *  road for a leg that must not run is the exclusions file, not a private skip. The bound of the read: strings are not
 *  stripped, so `skip:` or `{ skip }` inside a message reds too, the safe side; a computed name is outside it as for launch,
 *  and so is the method bound to a name of its own (`const stop = t.skip; stop(...)`), a read without a call followed by a
 *  call of another name. The helper is the road a browser-legs
 *  roster's switch reaches (ci-browser-legs.txt's header names it), so a leg with a launch or a stand-down of its own would
 *  skip under such a step as it does without one. */
const offRoute = (code) => {
  if (!/^import \{[^}]*\binBrowser\b[^}]*\} from "\.\/real-viewer-leg";/m.test(code)) return 'no import of inBrowser from real-viewer-leg.ts at a line\'s start';
  const launch = /(?:\.|\?\.)\s*launch\s*\(|\[\s*(["'`])launch\1\s*\]\s*\(/.exec(code);
  if (launch) return 'a launch outside the helper: ' + launch[0];
  const standDown = /(?:\.|\?\.)\s*(?:skip|todo)\s*\(|\[\s*(["'`])(?:skip|todo)\1\s*\]\s*\(|\b(?:skip|todo)\s*:|[{,]\s*(?:skip|todo)\s*[,}]|\b(?:skip|todo)\s*\(/.exec(code);
  return standDown ? 'a stand-down outside the helper: ' + standDown[0] : null;
};
/** The browser legs among `files` (paths from the repo root, the delta's) that `legs` (the derived legs, basenames) does not hold:
 *  a leg the branch touched that names no follow-on, so no derivation above reaches it and no record names it. */
const legsOffRoster = (files, legs) => files.filter((f) => /^ui\/webview\/[\w-]+-browser\.test\.ts$/.test(f)).map((f) => f.replace(/^ui\/webview\//, '')).filter((f) => !legs.includes(f)).sort();

/** The shared convention for browser legs in the gating job, by the names fixed with the sibling PRs: the roster (one compiled
 *  bundle path per line, `#` comments), the exclusions (bundle path, a tab, a reason), the step in the vscode-extension job,
 *  directly after its Chromium install, and the switch ROMP_BROWSER_LEGS_REQUIRE the step sets, reached by the shared helper's
 *  inBrowser through ./browser-legs-require. None of the four is this branch's to add (the maintainer's ruling on the file
 *  review's round 8, extra8-2: the step lands once as its own change); this module reads the tree for them and pins the consuming side. */
const ROSTER = ['vscode-extension', 'ci-browser-legs.txt'];
const EXCLUDED = ['vscode-extension', 'ci-browser-legs-excluded.txt'];
const ROSTER_TEST = ['tools', 'ci-browser-legs.test.mjs'];
const STEP = 'Browser legs (node --test over ci-browser-legs.txt)';
const INSTALL_RUN = /^\s+run: npx playwright install chromium\s*$/;
const JOB = 'vscode-extension';
/** The vscode-extension job's block of a workflow text, comment lines blanked (a step name or an install line quoted in a comment
 *  is neither), from its key to the next job key at the jobs indent or the text's end, with the 0-based line its key stands on;
 *  null when the text has no jobs block or no such job. The step's state is read in this job alone: the convention places the
 *  step there, so a Chromium install in another job (a served-legs job, say) neither classifies nor refuses this pin (the
 *  author's closing pass after the file review's round 9, mechanism-3: read over the whole file, a second install line turned
 *  an intact state A into a refusal). */
function jobBlockOf(ci, job) {
  const stripped = ci.replace(/^[ \t]*#.*$/gm, '');
  const jobsAt = stripped.search(/(?:^|\n)jobs:\n/);
  if (jobsAt < 0) return null;
  const from = stripped.indexOf('jobs:\n', jobsAt) + 'jobs:\n'.length;
  const key = new RegExp('^  ' + job + ':\\n', 'm').exec(stripped.slice(from));
  if (!key) return null;
  const start = from + key.index;
  const next = /^  [a-z][a-z-]*:\n/m.exec(stripped.slice(start + key[0].length));
  const end = next ? start + key[0].length + next.index : stripped.length;
  return { text: stripped.slice(start, end), line: (stripped.slice(0, start).match(/\n/g) || []).length };
}
/** The step's state in a workflow text, read in the vscode-extension job: 'present' when exactly one step there carries the fixed
 *  name and it is the step directly after the one whose run line installs Chromium; 'absent' when no step there carries the
 *  name; otherwise a sentence saying what stands (a workflow with no such job among them: its place cannot be read). Line
 *  numbers in the sentences are the file's. */
function stepStateOf(ci) {
  const job = jobBlockOf(ci, JOB);
  if (!job) return 'unreadable: ci.yml has no ' + JOB + ' job, the job the convention places the step in';
  const lines = job.text.split('\n');
  const names = lines.flatMap((l, i) => { const m = /^\s+- name: (.*\S)\s*$/.exec(l); return m ? [{ name: m[1], line: job.line + i }] : []; });
  const at = names.filter((n) => n.name === STEP);
  if (at.length === 0) return 'absent';
  if (at.length > 1) return 'present ' + at.length + ' times (lines ' + at.map((n) => n.line + 1).join(', ') + '), where the convention has one step';
  const installs = lines.flatMap((l, i) => (INSTALL_RUN.test(l) ? [job.line + i] : []));
  if (installs.length !== 1) return 'present at line ' + (at[0].line + 1) + ' while the Chromium install line stands ' + installs.length + ' times, so its place cannot be read';
  const installStep = names.filter((n) => n.line < installs[0]).pop();
  const after = names[names.indexOf(installStep) + 1];
  if (!after || after.name !== STEP) return 'present at line ' + (at[0].line + 1) + ' but not directly after the Chromium install step (line ' + (installStep.line + 1) + '), which is followed by ' + (after ? JSON.stringify(after.name) + ' at line ' + (after.line + 1) : 'nothing');
  return 'present';
}
const HELPER = ['ui', 'webview', 'real-viewer-leg.ts'];
const SWITCH = 'ROMP_BROWSER_LEGS_REQUIRE';
const SWITCH_MODULE = './browser-legs-require';
/** The switch's state in the shared helper's code (real-viewer-leg.ts, comment-stripped): 'present' when the helper imports
 *  launchBrowser from ./browser-legs-require at a line's start and its inBrowser calls it (the shared module reads the switch,
 *  under which a launch skip is a failure), or when inBrowser reads the switch by its name itself; 'absent' when the code names
 *  none of the switch, the module and launchBrowser; otherwise a sentence saying what stands (an import never called, a call of
 *  what was not imported, the switch named outside inBrowser). The fourth part of the convention: the step runs the rostered
 *  legs under the switch, and a leg reaches it through this helper alone, so a tree with the roster, the exclusions and the
 *  step over an unswitched helper would run its rostered legs under the step exactly as without it, each skipping at launch
 *  (the author's closing pass after the file review's round 9, mechanism-1: state A had been classified by the three files alone). */
function helperSwitchStateOf(code) {
  const imports = new RegExp('^import \\{[^}]*\\blaunchBrowser\\b[^}]*\\} from "' + SWITCH_MODULE.replace(/[./]/g, '\\$&') + '";', 'm').test(code);
  const at = code.indexOf('export async function inBrowser(');
  if (at < 0) return 'unreadable: ' + HELPER.join('/') + ' exports no inBrowser, the helper the legs launch through';
  const bodyEnd = code.indexOf('\n}\n', at);
  const body = code.slice(at, bodyEnd < 0 ? code.length : bodyEnd);
  const calls = /\blaunchBrowser\s*\(/.test(body);
  const byName = body.includes(SWITCH);
  if ((imports && calls) || byName) return 'present';
  const named = [imports ? 'imports launchBrowser from ' + SWITCH_MODULE : '', calls ? 'calls launchBrowser in inBrowser without the import' : '', code.includes(SWITCH) ? 'names ' + SWITCH + ' outside inBrowser' : '', !imports && code.includes(SWITCH_MODULE) ? 'names ' + SWITCH_MODULE + ' outside an import of launchBrowser' : ''].filter(Boolean);
  if (named.length === 0) return 'absent';
  return 'unreadable: the helper ' + named.join(', ') + ', and its inBrowser reaches no switch';
}
/** The convention's four parts as the tree holds them, and the state they make: A (all four present), B (none of the four),
 *  or a refusal naming what is present and what is absent (some of the four: a tree this module cannot classify). */
function conventionStateOf(rosterExists, excludedExists, stepState, helperState) {
  const parts = [['the roster ' + ROSTER.join('/'), rosterExists ? 'present' : 'absent'], ['the exclusions ' + EXCLUDED.join('/'), excludedExists ? 'present' : 'absent'], ['the step ' + JSON.stringify(STEP) + ' in ci.yml', stepState], ['the switch ' + SWITCH + ' reached by ' + HELPER.join('/') + '\'s inBrowser', helperState]];
  if (parts.every(([, st]) => st === 'present')) return { state: 'A', parts };
  if (parts.every(([, st]) => st === 'absent')) return { state: 'B', parts };
  return { state: 'refuse', parts };
}
/** A roster's bundle lines: every line that is not blank and not a `#` comment, as written (the shared script refuses a
 *  malformed line, so a line that differs from a leg's bundle path by whitespace is not that leg's line here either). */
const rosterLines = (text) => text.split('\n').filter((l) => !/^\s*(?:#|$)/.test(l));
/** An exclusions file's bundles: the text before the first tab of each such line. */
const excludedBundles = (text) => rosterLines(text).map((l) => l.split('\t')[0]);
const bundleOf = (leg) => 'out-tests/ui/webview/' + leg.replace(/\.ts$/, '.js');
/** The count of legs `sentence` carries, or null: a number (a word of NUMBER_WORDS, or digits) that quantifies a legs noun (leg,
 *  legs, module, modules), the noun within three words after the number with no punctuation and no determiner between (`eight
 *  legs`, `eight browser legs`, `8 Chromium legs`; a cardinal stands before its noun with only its modifiers between, so `two of
 *  the eight legs`, a partitive of a subset, is not the legs' count), or the number
 *  a partitive after the noun within four words (`the legs, eight of them`). A number quantifying another noun is no count of
 *  the legs (`one compiled bundle path per line` is the roster's line shape), nor is a label a noun carries (`the file review's round 8,
 *  extra8-2: the legs`: the comma closes the window). Keyed on the property, whatever the wording (the author's closing pass after the
 *  file review's round 9, mechanism-2: the one-spelling guard `<number> browser legs` passed `the eight legs` and `the legs,
 *  eight of them`). Returns the words that make the count. */
function legsCount(sentence) {
  const raw = sentence.split(/\s+/).filter(Boolean);
  const words = raw.map((w) => w.replace(/^\W+|\W+$/g, ''));
  const isNumber = (w) => /^\d+$/.test(w) || Object.hasOwn(NUMBER_WORDS, w.toLowerCase());
  const isLegs = (w) => /^(?:legs?|modules?)$/i.test(w);
  const closes = (r) => /[,;:.)(]$/.test(r);
  const determiner = (w) => /^(?:the|a|an|its|this|that|these|those|their|no|every|each)$/i.test(w);
  for (let i = 0; i < words.length; i++) {
    if (!isNumber(words[i])) continue;
    for (let j = i + 1; j <= Math.min(i + 3, words.length - 1); j++) {
      if (isLegs(words[j])) return words.slice(i, j + 1).join(' ');
      if (closes(raw[j - 1]) || determiner(words[j])) break;
    }
    if (words[i + 1]?.toLowerCase() === 'of' && /^(?:them|these|those)$/i.test(words[i + 2] ?? '')) {
      for (let j = i - 1; j >= Math.max(0, i - 4); j--) {
        if (isLegs(words[j])) return words.slice(j, i + 3).join(' ');
        if (/[;:.)(]$/.test(raw[j])) break;
      }
    }
  }
  return null;
}
/** The Tests paragraph's disclosure, state B's sentence: its opening words, and the clauses it must carry. */
const DISCLOSURE = 'The browser legs named here skip at launch in the Test step of the job that gates a landing';
/** The clauses on the derivation's key (the file review's round 10, extra6-1 and extra6-2): that the legs are derived by the
 *  file name and not the property, PR 887's census as the property's one definition to come, and the two modules of the
 *  follow-on's diff the property reaches and the name does not (each held to exist on disk by the module-existence pin above,
 *  as every test module the section names is). Held here since the author's closing pass after the file review's round 10,
 *  mechanism-3: the corrected disclosure was in no pin, and the wording the round called false put back left every pin green. */
const NAME_CLAUSES = [
  ['derives the legs BY NAME', 'that the derivation of the legs is by the file name'],
  ['a name and not the property that makes a module a browser leg', 'that the name is not the property'],
  ['vscode-extension/scripts/browser-legs-census.mjs', 'PR 887\'s census by its path, the property\'s reader'],
  ['that census is the one definition of a browser leg once it lands', 'that the census is the one definition once it lands'],
  ['ui/webview/file-trail.test.ts', 'the first module the property reaches and the name does not'],
  ['ui/webview/file-view-text-size.test.ts', 'the second module the property reaches and the name does not'],
];
const DISCLOSURE_CLAUSES = [
  ['which runs before that job installs Chromium', 'why they skip there'],
  ['so none of their browser scenarios runs where landing is gated', 'that none of their browser scenarios runs where landing is gated (a source pin in a leg runs there without a browser)'],
  ['what gates the follow-on there is its source pins', 'what does gate the follow-on there'],
  ['the shared roster of browser legs, ' + ROSTER.join('/'), 'the road that runs them with a browser, the shared roster by its file name'],
  ['a change of its own that this branch does not carry', 'that the roster is not this branch\'s to add'],
  ...NAME_CLAUSES,
];
/** The clauses of DISCLOSURE_CLAUSES a disclosure sentence lacks, each with what it says. */
const missingClauses = (sentence) => DISCLOSURE_CLAUSES.filter(([clause]) => !sentence.includes(clause));

test('the follow-on\'s browser legs and the job that gates a landing, a two-state pin over the shared convention: the legs are derived by name from the tree (the -browser.test.ts modules whose own text names the follow-on; the property-keyed definition of a browser leg is PR 887\'s compiler census, once it lands) and each launches through real-viewer-leg.ts\'s inBrowser, the helper a roster\'s switch reaches, read comment-stripped under any launch spelling, with no launch and no stand-down (a skip or todo call or option) of its own; where the tree carries the roster, the exclusions, the step directly after the Chromium install in the vscode-extension job and the helper\'s switch (state A) every leg is a roster line and no exclusions line and the roster\'s tree test exists, and the Tests paragraph no longer says none of their browser scenarios runs where landing is gated; where it carries none of the four (state B) the Tests paragraph discloses that the legs skip in the gating job\'s Test step, what gates the follow-on there and the roster by name as the road, with no count of the legs in any wording; a tree with some of the four is refused, naming them; behind L6\'s gate every browser leg the delta adds or modifies is among the derived legs', (t) => {
  const legs = browserLegs();
  assert.ok(legs.length > 0, 'browser legs naming the follow-on are on disk');
  const tests = section.slice(section.indexOf('**Tests.**'));
  const named = [...new Set([...tests.matchAll(/ui\/webview\/([\w-]+-browser\.test\.ts)\b/g)].map((m) => m[1]))].sort();
  assert.deepEqual(named, legs, 'the browser modules the Tests paragraph names are the legs whose own text names the follow-on: the two derivations of the legs agree');
  // the route: each leg's code, comment-stripped, imports the helper at a line's start and launches nothing itself; the read is
  // armed on the shape that passed the raw read and on the spellings the one-spelling check missed
  assert.equal(offRoute(codeLines('import { inBrowser, openViewer } from "./real-viewer-leg";\ntest("x", (t) => inBrowser(t, async (b) => { const stub = { chromium: { launch: async () => {} } }; void stub; }));\n')), null, 'the head\'s shape passes: the import at a line\'s start, no launch call, a launch KEY in a stub allowed');
  assert.equal(offRoute(codeLines('// import { inBrowser as withBrowser } from "./real-viewer-leg";\nasync function withBrowser(t, body) { const pw = requireCjs("playwright"); const browser = await pw["chromium"]["launch"](); await body(browser); }\n')), 'no import of inBrowser from real-viewer-leg.ts at a line\'s start', 'the import moved into a comment is no import (the plant the raw read passed)');
  assert.equal(offRoute(codeLines('/*\nimport { inBrowser } from "./real-viewer-leg";\n*/\nconst x = 1;\n')), 'no import of inBrowser from real-viewer-leg.ts at a line\'s start', 'nor one quoted in a block comment');
  for (const [spelling, want] of [['const b = await pw.chromium.launch();', '.launch('], ['const b = await pw?.chromium?.launch();', '?.launch('], ['const b = await pw["chromium"]["launch"]();', '["launch"]('], ["const b = await pw.chromium['launch']();", "['launch']("]]) {
    assert.equal(offRoute(codeLines('import { inBrowser } from "./real-viewer-leg";\n' + spelling + '\n')), 'a launch outside the helper: ' + want, 'a private launch is refused under the spelling ' + spelling);
  }
  assert.equal(offRoute(codeLines('import { inBrowser } from "./real-viewer-leg";\nconst b = 1; // pw.chromium.launch()\n')), 'a launch outside the helper: .launch(', 'a launch quoted in a comment after code reds too: the stripper reads line shapes, and this is its safe side');
  // the pair's other half: a stand-down of the leg's own, under the launch spellings and node:test's option form (the file review's
  // round 10, tests-2)
  for (const [spelling, want] of [['test("y", (t) => { t.skip("no browser here"); });', '.skip('], ['t?.skip("no browser here");', '?.skip('], ['t["skip"]("no browser here");', '["skip"]('], ["t['todo']('later');", "['todo']("], ['test.todo("later");', '.todo('], ['test("y", { skip: !pw }, () => {});', 'skip:'], ['test("y", { todo: true }, () => {});', 'todo:'],
    // the shorthand property and the destructured call (the author's closing pass after the file review's round 10, mechanism-1:
    // both had passed the option read, which needed the colon)
    ['const skip = !process.env.PW;\ntest("y", { skip }, () => {});', '{ skip }'], ['test("y", { only: false, todo }, () => {});', ', todo }'], ['test("y", {skip,only: false}, () => {});', '{skip,'], ['const { skip } = t;\nskip("no browser here");', '{ skip }'], ['skip("no browser here");', 'skip('], ['todo ("later");', 'todo (']]) {
    assert.equal(offRoute(codeLines('import { inBrowser } from "./real-viewer-leg";\n' + spelling + '\n')), 'a stand-down outside the helper: ' + want, 'a private stand-down is refused under the spelling ' + spelling);
  }
  assert.equal(offRoute(codeLines('import { inBrowser } from "./real-viewer-leg";\nconst skip = !process.env.PW; const t = { todo: 1 }.todo; void skip; void t;\n')), 'a stand-down outside the helper: todo:', 'a bare declaration of the name is no stand-down by itself, and the object property with its colon is the option read (the read\'s bound is stated in offRoute\'s docstring: the method bound to a name of its own is outside it)');
  assert.equal(offRoute(codeLines('import { inBrowser } from "./real-viewer-leg";\nconst skip = !process.env.PW; void skip; const skipped = { skipTo: 1, myskip: 2 }; void skipped;\n')), null, 'the name declared or standing inside a longer identifier, with neither a call, an option colon nor a shorthand place between braces, is no stand-down');
  assert.equal(offRoute(codeLines('import { inBrowser } from "./real-viewer-leg";\n// Skips LOUDLY without a playwright browser: the helper calls t.skip(...) itself\ntest("x", (t) => inBrowser(t, async () => {}));\n')), null, 'prose about skipping on a comment line is no stand-down (the stripper drops the line)');
  assert.equal(offRoute(codeLines('import { inBrowser } from "./real-viewer-leg";\nconst why = "skipped where no browser is installed";\n')), null, 'the word skipped, and skip with neither a call nor an option colon, is no stand-down');
  assert.equal(offRoute(codeLines('import { inBrowser } from "./real-viewer-leg";\nconst b = 1; // t.skip("x")\n')), 'a stand-down outside the helper: .skip(', 'a stand-down quoted in a comment after code reds too, the stripper\'s safe side');
  assert.equal(offRoute(codeLines('import { inBrowser } from "./real-viewer-leg";\nconst b = await pw.chromium.launch();\nt.skip("x");\n')), 'a launch outside the helper: .launch(', 'a leg with both halves is refused for the launch first');
  for (const f of legs) assert.equal(offRoute(codeLines(read('ui', 'webview', f))), null, f + ' launches through the helper alone: it imports inBrowser from real-viewer-leg.ts at a line\'s start, calls launch on nothing and stands itself down nowhere (a private launch, skip or todo would skip under a roster\'s switch)');
  // the step's state, driven on synthetic workflows before the tree's is read
  const job = (name, steps) => '  ' + name + ':\n    steps:\n' + steps.map(([n, run]) => '      - name: ' + n + '\n' + (run ? '        run: ' + run + '\n' : '')).join('');
  const wf = (steps, ...more) => 'jobs:\n' + job(JOB, steps) + more.map(([name, steps]) => job(name, steps)).join('');
  const INSTALL = ['Install the pinned Playwright Chromium', 'npx playwright install chromium'];
  assert.equal(stepStateOf(wf([['Test', 'npm test'], INSTALL, [STEP, 'bash scripts/ci-browser-legs.sh'], ['Bench', 'node x']])), 'present', 'the step directly after the install');
  assert.equal(stepStateOf(wf([['Test', 'npm test'], INSTALL, ['Bench', 'node x']])), 'absent', 'no step of the name');
  assert.match(stepStateOf(wf([['Test', 'npm test'], INSTALL, ['Bench', 'node x'], [STEP, 'bash scripts/ci-browser-legs.sh']])), /^present at line \d+ but not directly after the Chromium install step \(line \d+\), which is followed by "Bench" at line \d+$/, 'the step present but a step later is neither present nor absent');
  assert.match(stepStateOf(wf([['Test', 'npm test'], [STEP, 'bash scripts/ci-browser-legs.sh'], INSTALL])), /but not directly after the Chromium install step/, 'nor one before the install');
  assert.match(stepStateOf(wf([INSTALL, [STEP, 'bash x'], [STEP, 'bash x']])), /^present 2 times/, 'nor two of them');
  assert.match(stepStateOf(wf([[STEP, 'bash x']])), /while the Chromium install line stands 0 times/, 'nor one in a workflow with no install to stand after');
  assert.equal(stepStateOf(wf([['Test', 'npm test'], INSTALL, [STEP, 'bash scripts/ci-browser-legs.sh']], ['served-legs', [INSTALL, ['Served', 'python -m pytest']]])), 'present', 'a second job installing Chromium is not read: the step is read in the vscode-extension job alone');
  assert.equal(stepStateOf(wf([['Test', 'npm test'], INSTALL, ['Bench', 'node x']], ['served-legs', [INSTALL, [STEP, 'bash x']]])), 'absent', 'nor is the step counted in another job');
  assert.equal(stepStateOf(wf([['Test', 'npm test'], INSTALL, ['Bench', 'node x'], [STEP, 'bash x']]).replace(/^      - name: Bench\n/m, '      # - name: Bench\n')), 'present', 'a step whose name line is a comment is no step, so the one after the install is the step');
  assert.match(stepStateOf('jobs:\n' + job('served-legs', [INSTALL, [STEP, 'bash x']])), /^unreadable: ci\.yml has no vscode-extension job/, 'a workflow without the job is neither present nor absent');
  assert.match(stepStateOf(wf([['Test', 'npm test'], INSTALL, ['Bench', 'node x'], [STEP, 'bash x']])), /^present at line 10 but not directly after the Chromium install step \(line 6\), which is followed by "Bench" at line 8$/, 'the sentences carry the file\'s line numbers (jobs: on line 1, the job key on 2, steps: on 3, each step two lines)');
  // the helper's switch, driven on the shared helper's shape and its refusals before the tree's helper is read
  const helper = (body, head = 'import { launchBrowser } from "./browser-legs-require";\n') => head + 'export async function inBrowser(t: any, body: (browser: any) => Promise<void>): Promise<void> {\n' + body + '\n}\n';
  assert.equal(helperSwitchStateOf(codeLines(helper('  const browser = await launchBrowser(t, pw, "chromium");\n  if (!browser) return;'))), 'present', 'the shared helper\'s shape: the import at a line\'s start and the call in inBrowser');
  assert.equal(helperSwitchStateOf(codeLines(helper('  if (process.env.' + SWITCH + ' === "1" && !pw) t.fail("no browser");', ''))), 'present', 'or inBrowser reads the switch by name');
  assert.equal(helperSwitchStateOf(codeLines(helper('  if (!pw) { t.skip("no playwright"); return; }\n  const browser = await pw.chromium.launch();', ''))), 'absent', 'a helper naming none of the switch, the module and launchBrowser: absent (the tree before the convention)');
  assert.match(helperSwitchStateOf(codeLines(helper('  const browser = await pw.chromium.launch();'))), /^unreadable: the helper imports launchBrowser from \.\/browser-legs-require, and its inBrowser reaches no switch$/, 'the import without the call is neither');
  assert.match(helperSwitchStateOf(codeLines(helper('  const browser = await launchBrowser(t, pw, "chromium");', ''))), /^unreadable: the helper calls launchBrowser in inBrowser without the import/, 'nor the call without the import');
  assert.match(helperSwitchStateOf(codeLines(helper('  const browser = await pw.chromium.launch();', 'const REQUIRE = "' + SWITCH + '";\n'))), /names ROMP_BROWSER_LEGS_REQUIRE outside inBrowser, and its inBrowser reaches no switch$/, 'nor the switch named where inBrowser does not read it');
  assert.equal(helperSwitchStateOf(codeLines(helper('  const browser = await launchBrowser(t, pw, "chromium");', '// import { launchBrowser } from "./browser-legs-require";\n'))).startsWith('unreadable'), true, 'an import in a comment is no import');
  assert.match(helperSwitchStateOf(codeLines('const x = 1;\n')), /^unreadable: .* exports no inBrowser/, 'a helper without inBrowser is neither');
  // the three states, driven
  assert.equal(conventionStateOf(true, true, 'present', 'present').state, 'A');
  assert.equal(conventionStateOf(false, false, 'absent', 'absent').state, 'B');
  for (const [r, e, st, h] of [[true, false, 'absent', 'absent'], [false, true, 'absent', 'absent'], [false, false, 'present', 'absent'], [true, true, 'absent', 'present'], [true, true, 'present', 'absent'], [false, false, 'absent', 'present'], [true, true, 'present at line 9 but not directly after the Chromium install step (line 5), which is followed by "Bench" at line 7', 'present'], [true, true, 'present', 'unreadable: the helper imports launchBrowser from ./browser-legs-require, and its inBrowser reaches no switch'], [true, true, 'unreadable: ci.yml has no vscode-extension job, the job the convention places the step in', 'present']]) assert.equal(conventionStateOf(r, e, st, h).state, 'refuse', 'some of the four: refused (' + [r, e, st, h].join(', ') + ')');
  // the count guard, driven: a count of the legs in any wording is one, a number quantifying another noun is not
  for (const counted of ['the eight browser legs skip', 'derives the eight legs from the tree', 'the legs, eight of them, skip', '8 Chromium legs', 'the two pytest modules it added', 'the modules, two of them,']) assert.ok(legsCount(counted), 'a count of the legs: ' + counted);
  for (const fine of ['one compiled bundle path per line', 'the legs skip at launch', 'no leg runs there', 'the roster of browser legs, vscode-extension/ci-browser-legs.txt, one compiled bundle path per line', 'three runs of the legs', "the file review's round 8, extra8-2: the legs were the feature's evidence", 'in 3 runs the legs passed', 'one of the modules the section names', 'two of the legs']) assert.equal(legsCount(fine), null, 'no count of the legs (a partitive of a subset is none, a label is none): ' + fine);
  // the clause read, driven: a synthetic disclosure carrying every clause lacks none, and the same sentence with the file review's round 9's
  // wording of the derivation in place of the name-keyed clauses (the wording the file review's round 10, extra6-2, called false) lacks
  // exactly those (the author's closing pass after the file review's round 10, mechanism-3)
  const synthetic = DISCLOSURE + ', ' + DISCLOSURE_CLAUSES.map(([clause]) => clause).join(', ') + ' as SKIP).';
  assert.deepEqual(missingClauses(synthetic), [], 'a disclosure carrying every clause lacks none');
  const round9 = DISCLOSURE + ', ' + DISCLOSURE_CLAUSES.filter((c) => !NAME_CLAUSES.includes(c)).map(([clause]) => clause).join(', ') + ', derives the legs from the tree, as the browser modules whose own text names this follow-on, holds each to a launch through inBrowser as SKIP).';
  assert.deepEqual(missingClauses(round9), NAME_CLAUSES, 'the file review\'s round 9\'s wording of the derivation lacks exactly the clauses on the key, the census and the two modules');
  assert.deepEqual(rosterLines('# a comment\n\nout-tests/ui/webview/a-browser.test.js\n  # indented comment\nout-tests/ui/webview/b-browser.test.js\n'), ['out-tests/ui/webview/a-browser.test.js', 'out-tests/ui/webview/b-browser.test.js'], 'roster lines: comments and blanks dropped, lines as written');
  assert.deepEqual(excludedBundles('# c\nout-tests/ui/webview/a-browser.test.js\tlaunches Firefox\n'), ['out-tests/ui/webview/a-browser.test.js'], 'exclusions: the bundle before the tab');
  // the tree's state
  const st = conventionStateOf(exists(...ROSTER), exists(...EXCLUDED), stepStateOf(read('.github', 'workflows', 'ci.yml')), helperSwitchStateOf(codeLines(read(...HELPER))));
  const picture = st.parts.map(([what, s]) => what + ': ' + s).join('; ');
  assert.notEqual(st.state, 'refuse', 'the tree carries some of the shared convention\'s four parts and not all, a state this module does not classify (the legs are held to the roster where all four stand, to the Tests paragraph\'s disclosure where none does): ' + picture);
  const disclosureAt = tests.indexOf(DISCLOSURE);
  if (st.state === 'A') {
    const roster = rosterLines(read(...ROSTER));
    const excluded = excludedBundles(read(...EXCLUDED));
    for (const f of legs) {
      assert.ok(roster.includes(bundleOf(f)), f + ' is a roster line (' + bundleOf(f) + ' in ' + ROSTER.join('/') + '): the gating job runs it with a browser through the step ' + JSON.stringify(STEP) + '; a leg of the follow-on missing from the roster runs where landing is gated only where it skips');
      assert.ok(!excluded.includes(bundleOf(f)), f + ' is not an exclusions line (' + bundleOf(f) + ' in ' + EXCLUDED.join('/') + '): a leg is in one file or the other, and the follow-on\'s legs run');
    }
    assert.ok(exists(...ROSTER_TEST), ROSTER_TEST.join('/') + ' exists: the convention\'s own tree test, which holds every browser leg in the tree to one file or the other');
    assert.equal(disclosureAt, -1, 'the Tests paragraph no longer says the legs skip in the gating job and none of their browser scenarios runs where landing is gated: with the roster in the tree and the legs its lines, that sentence is false and is reworded to say the roster runs them');
    t.diagnostic('state A: the roster, the exclusions, the step and the helper\'s switch are in the tree; ' + legs.length + ' legs are roster lines and no exclusions line');
  } else {
    assert.ok(disclosureAt >= 0, 'the Tests paragraph discloses that the legs skip in the gating job\'s Test step (the tree carries none of the roster, the exclusions, the step and the switch: ' + picture + '); the sentence opens ' + JSON.stringify(DISCLOSURE));
    const sentence = tests.slice(disclosureAt, tests.indexOf('as SKIP). ', disclosureAt) + 'as SKIP).'.length);
    assert.ok(sentence.length > DISCLOSURE.length && sentence.endsWith('as SKIP).'), 'the disclosure runs to its closing citation of the gating run\'s log: ' + sentence.slice(-120));
    assert.deepEqual(missingClauses(sentence).map(([clause, what]) => what + ' (' + JSON.stringify(clause) + ')'), [], 'the disclosure carries every clause; the ones it lacks say: ' + sentence);
    assert.equal(legsCount(sentence), null, 'the sentence counts no legs (the legs are derived here, never typed there): ' + legsCount(sentence) + ' in: ' + sentence);
    assert.equal((tests.match(new RegExp(ROSTER.join('\\/'), 'g')) || []).length, 1, 'the roster is named once in the Tests paragraph, as the road');
    t.diagnostic('state B: the tree carries none of the roster, the exclusions, the step and the switch; the Tests paragraph discloses the skip and names the roster as the road');
  }
  // the derived legs against the delta, behind L6's gate: a browser leg the branch adds or modifies whose text names no follow-on
  // is reached by no derivation above and named in no record while the two text-keyed derivations agree (the author's closing
  // pass after the file review's round 8: a committed quiet leg left this test green and only L6's count red)
  assert.deepEqual(legsOffRoster(['ui/webview/zz-quiet-browser.test.ts', 'ui/webview/file-trail-browser.test.ts', 'ui/webview/file-trail.test.ts', 'docs/guide.md'], ['file-trail-browser.test.ts']), ['zz-quiet-browser.test.ts'], 'the comparison, driven: a browser leg in the delta and not among the derived legs is named; a leg in both, a node module and a doc are not');
  gated(t, LEGS_CHECK, (d) => {
    const inTree = d.files.filter((f) => exists(...f.split('/')));
    const off = legsOffRoster(inTree, legs);
    assert.deepEqual(off, [], 'every browser leg the diff since the merge-base ' + d.base + ' adds or modifies names the follow-on and is among the derived legs (a quiet leg is held by no derivation here and named in no record): ' + off.join(', '));
    t.diagnostic('the browser legs\' comparison ran: ' + inTree.filter((f) => /-browser\.test\.ts$/.test(f)).length + ' browser legs in the delta since the merge-base ' + d.base + ', every one among the derived legs');
  }, '; the legs are held to the tree\'s text and the Tests paragraph alone here');
});

// ── the gate on L6's verifications ─────────────────────────────────────────────────────────────────

test('L6\'s gate (the file review\'s round 5, tests-7): a pure function over git\'s answers, pinned in all four cells; in a temp repo shaped as the open PR branch (origin/main moved past the branch\'s fork point, the branch adding this module\'s path) the verifications run and read the delta, a kernel edit there is what the kernel stat would red on; origin/main at the branch\'s head holds them off on the merge-base part, a later branch adding another file on the module part, no origin/main on the first', () => {
  const M = THIS_MODULE;
  assert.deepEqual(gateOf(null, null, [], M), { ran: false, held: 'no origin/main' });
  assert.deepEqual(gateOf('aaaa', 'aaaa', [M], M), { ran: false, held: 'the merge-base is origin/main' }, 'the module added and the base at main: the first part that holds names itself');
  assert.deepEqual(gateOf('aaaa', 'bbbb', ['other.ts'], M), { ran: false, held: 'the diff does not add the module' });
  assert.deepEqual(gateOf('aaaa', 'bbbb', ['other.ts', M], M), { ran: true, held: null });
  const repo = fs.mkdtempSync(path.join(os.tmpdir(), 'linknav-l6-gate-'));
  try {
    const git = (...args) => execFileSync('git', ['-C', repo, '-c', 'user.email=t@example.test', '-c', 'user.name=t', ...args], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
    const write = (rel, text) => { fs.mkdirSync(path.dirname(path.join(repo, rel)), { recursive: true }); fs.writeFileSync(path.join(repo, rel), text); };
    git('init', '-q', '-b', 'main', '.');
    write('docs/a.md', 'A paragraph.\n');
    write('kernel/k.py', 'x = 1\n');
    git('add', '-A'); git('commit', '-q', '-m', 'base');
    const forkPoint = git('rev-parse', 'HEAD');
    git('checkout', '-q', '-b', 'feature');
    write(M, '// the pin\n');
    write('ui/webview/x.ts', 'export const x = 1;\n');
    write('docs/a.md', 'A paragraph.\n\nAnother.\n');
    git('add', '-A'); git('commit', '-q', '-m', 'the branch');
    git('checkout', '-q', 'main');
    write('other.md', 'Main moved on.\n');
    git('add', 'other.md'); git('commit', '-q', '-m', 'main moves');
    const mainTip = git('rev-parse', 'HEAD');
    git('checkout', '-q', 'feature');
    assert.deepEqual(deltaOf(repo, M).gate, { ran: false, held: 'no origin/main' }, 'no ref: the first part');
    git('update-ref', 'refs/remotes/origin/main', mainTip);
    const ran = deltaOf(repo, M);
    assert.deepEqual(ran.gate, { ran: true, held: null }, 'the open PR branch\'s shape runs the verifications');
    assert.equal(ran.base, forkPoint);
    assert.deepEqual(ran.files, ['docs/a.md', M, 'ui/webview/x.ts'], 'the delta is the branch\'s files alone, main\'s own commit not among them');
    assert.equal(ran.kernel, '', 'no kernel change on the branch');
    write('kernel/k.py', 'x = 2\n');
    git('add', '-A'); git('commit', '-q', '-m', 'a kernel edit');
    assert.match(deltaOf(repo, M).kernel, /kernel\/k\.py \|/, 'a kernel edit on the branch shows in the stat the check reads');
    git('update-ref', 'refs/remotes/origin/main', git('rev-parse', 'HEAD'));
    assert.deepEqual(deltaOf(repo, M).gate, { ran: false, held: 'the merge-base is origin/main' }, 'origin/main at the branch\'s head: the merge-base part');
    git('checkout', '-q', '-b', 'later', mainTip);
    write('later.md', 'Later.\n');
    git('add', 'later.md'); git('commit', '-q', '-m', 'later');
    git('checkout', '-q', 'main');
    write('other.md', 'Main moved on.\n\nAnd again.\n');
    git('add', 'other.md'); git('commit', '-q', '-m', 'main moves again');
    git('update-ref', 'refs/remotes/origin/main', git('rev-parse', 'HEAD'));
    git('checkout', '-q', 'later');
    assert.deepEqual(deltaOf(repo, M).gate, { ran: false, held: 'the diff does not add the module' }, 'a later branch after the landing: the module part');
  } finally {
    fs.rmSync(repo, { recursive: true, force: true });
  }
});

// ── the stand-down sentence, held to the checks that stand down ────────────────────────────────────

test('the plan\'s stand-down sentence is a rule over the checks keyed on the delta since the merge-base, and its count is derived: the number word equals the checks this module ran through `gated` plus the attribution module\'s exported count, each check is named in it, and it says they run in no checkout that gates landing and in none after the merge; deltaOf over this repository is called through `gated` alone, and every held-off diagnostic names its check (the file review\'s round 8, extra6-1: the sentence had named two of three and its pin held the bytes, so the short enumeration could never go red)', () => {
  // this module's own source, its `//` comment lines dropped (the tools job runs without the compiler, so ui/test-code-only.ts is
  // out of reach); a block comment or a comment after code quoting one of the two calls counts here and reds this test, a false
  // red and never a false green, which the message then explains
  const own = read(...THIS_MODULE.split('/')).split('\n').filter((l) => !/^\s*\/\//.test(l)).join('\n');
  assert.equal((own.match(/deltaOf\(REPO, /g) || []).length, 1, 'deltaOf over the repository is called in gated alone, so GATED_RAN is every check this module keys on the delta (a comment after code quoting the call counts here too: read comment-stripped by line shape)');
  assert.equal((own.match(/\bgated\(t, [A-Z0-9_]+_CHECK, /g) || []).length, GATED_RAN.size, 'every gated call in this module ran before this test (a check declared and not run is red here): ' + [...GATED_RAN].join('; '));
  assert.ok(GATED_RAN.size >= 2, 'at least two checks ran through the door (an empty set cannot satisfy the count): ' + [...GATED_RAN].join('; '));
  const road2 = /^export const ROAD_TWO_GATED_CHECKS = (\d+);$/m.exec(read('ui', 'webview', 'linknav-records-attribution.test.ts'));
  assert.ok(road2, 'the attribution module exports the count of its checks keyed on the delta (ROAD_TWO_GATED_CHECKS)');
  const expected = GATED_RAN.size + Number(road2[1]);
  const m = /The (\w+) checks keyed on the diff since the merge-base with `origin\/main` \(([^()]*)\) run in no checkout that gates landing, and in none after the merge:/.exec(section);
  assert.ok(m, 'the plan states the stand-down once as a rule over the checks keyed on the delta, with their count and their names, saying they run in no checkout that gates landing and in none after the merge');
  assert.equal(NUMBER_WORDS[m[1].toLowerCase()], expected, 'the sentence counts the checks keyed on the delta: ' + GATED_RAN.size + ' in this module (' + [...GATED_RAN].join('; ') + ') and ' + road2[1] + ' in the attribution module, ' + expected + ' in all; it says ' + m[1]);
  for (const name of GATED_RAN) assert.ok(m[2].includes(name), 'the sentence names the check ' + JSON.stringify(name));
  assert.ok(m[2].includes("the attribution module's second road"), "the sentence names the attribution module's second road");
  assert.ok(m[2].includes("the re-aimed count's list-vs-count half is not among them and runs in every checkout"), 'and says which half of the re-aimed check is not gated (both refuters of extra6-1)');
  assert.ok(section.includes("and every claim about the delta, L6's two, the re-aimed count's comparison and the browser legs' comparison, holds by the prose alone, re-derived by hand at the merged head"), 'the closing clause covers every gated claim, the re-aimed count\'s and the browser legs\' among them');
  // the held-off diagnostics name the check, whichever part of the gate held it (extra6-1: the re-aimed count's stand-down had
  // been reported as L6's)
  for (const held of Object.keys(HELD)) for (const name of GATED_RAN) assert.ok(HELD[held](name, 'aaaa', THIS_MODULE).startsWith(name + ' did not run: '), 'the diagnostic for ' + JSON.stringify(held) + ' names ' + JSON.stringify(name));
});
