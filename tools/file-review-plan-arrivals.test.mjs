// The arrivals follow-on's paragraph (plans/file-review.md, under Slice 2) held to the code and the modules it names.
//
// The paragraph records two rules from the user's reports of 2026-09-09: the line under the panel's header naming the
// session's changes, comments and replies the person has not seen (with a dot on each card until a gesture finds it on
// screen), and the save's scroll standing down once the person has moved on. A record that names a function the panel no
// longer has, an event the constructor no longer listens for, or a module that is not in the tree costs the next reader
// the search it was meant to save, so every identifier the paragraph carries in backticks is checked against the source,
// the events it lists against the listeners, its "never a timer" against the gesture's body, and the modules it names
// against the tree and the Tests section. Synthetic: only the repo's own text.
// Run: node --test tools/file-review-plan-arrivals.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');

const plan = read('plans', 'file-review.md');
const panel = read('ui', 'webview', 'file-comments.ts');
const model = read('ui', 'webview', 'file-comments-model.ts');
const guide = read('docs', 'guide.md');

function between(doc, from, to) {
  const a = doc.indexOf(from);
  assert.ok(a >= 0, `${JSON.stringify(from)} not found`);
  const b = doc.indexOf(to, a + from.length);
  assert.ok(b > a, `${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return doc.slice(a, b).replace(/\s+/g, ' ');
}
const LABEL = 'The arrivals follow-on (2026-09-09):';
const note = between(plan, LABEL, '### Slice 3: region comments on images');
const tests = between(plan, '\n## Tests', '\n## Docs');
const docs = between(plan, '\n## Docs', '\n## Deliberately not in v1');

test('the paragraph stands under Slice 2 and records both reports in the user\'s terms, paraphrased', () => {
  assert.ok(between(plan, '### Slice 2: the session', '### Slice 3: region comments on images').includes(LABEL));
  assert.ok(note.includes('the session answered with eleven changes and seven replies while they kept commenting'));
  assert.ok(note.includes('the next Send accepting the changes by default'));
  assert.ok(note.includes('they saved a reply, scrolled on while the host answered, and the reply\'s landing pulled the text back to the card'));
  assert.ok(!/"[^"]*\b(I|my|me)\b[^"]*"/.test(note.replace(/"api made [^"]*"/, '').replace(/"accept the [^"]*"/, '')), 'no quoted utterance of the user\'s');
});

test('every identifier the paragraph names in backticks is in the panel, the model or the tree', () => {
  const names = Array.from(note.matchAll(/`([^`]+)`/g), (m) => m[1]);
  assert.ok(names.length >= 15, 'the paragraph names its code: ' + names.length);
  for (const n of names) {
    if (/\.(test\.ts|py|mjs)$/.test(n)) {
      const rel = n.includes('/') ? n : path.join('ui', 'webview', n);
      assert.ok(fs.existsSync(path.join(REPO, rel)), `${n} is in the tree`);
    } else if (n === 'file-comments-model.ts') {
      assert.ok(fs.existsSync(path.join(REPO, 'ui', 'webview', n)));
    } else if (n === 'you') {
      assert.ok(model.includes('export const YOU = "you";'), 'decision 6\'s label is the model\'s constant');
    } else if (n === 'data-new') {
      assert.ok(panel.includes('card.dataset.new = "1"'), 'the attribute the cards wear');
    } else if (n === 'fcarrivals') {
      assert.ok(panel.includes('fcarrivals: () => this.goToArrival(),'), 'the delegate entry');
    } else {
      assert.ok(panel.includes(n + '(') || model.includes(n + '(') || panel.includes(n + ' ') || panel.includes(n + ';') || panel.includes(n + ','), `${n} is a function or a field of the panel or the model`);
    }
  }
});

test('the events the paragraph lists are the constructor\'s listeners, and the gesture has no timer', () => {
  assert.ok(note.includes('A gesture is a pointer press or a key anywhere in the body row, a wheel or a touch move'));
  assert.ok(panel.includes('for (const ev of ["pointerdown", "keydown"]) row.addEventListener(ev, (e) => this.gesture(e), true);'));
  assert.ok(panel.includes('for (const ev of ["wheel", "touchmove"]) row.addEventListener(ev, (e) => this.gesture(e), { capture: true, passive: true });'));
  assert.ok(note.includes('a save, a send; never a timer'));
  const body = panel.slice(panel.indexOf('gesture(ev?: Event): void {'), panel.indexOf('private entryShown('));
  assert.ok(!/setTimeout|setInterval|Date\.now/.test(body), 'no timer in the gesture');
  assert.ok(panel.includes('this.gesture();\n    const pressed = this.gestures;'), 'the save counts itself and samples the count');
  assert.ok(panel.includes('this.gesture();                                    // a send is a gesture'), 'the send counts itself');
});

test('the save\'s stand-down is as the paragraph states it: the count stood AND the card not whole in the box; the card the focus either way', () => {
  assert.ok(note.includes('scrolls only if the count stood'));
  assert.ok(note.includes('AND the saved card is not already whole in the track\'s box (`cardWhole`'));
  assert.ok(/if \(still && !this\.cardWhole\(key\)\) \{ this\.scrollCard\(key\); return; \}\n\s*if \(this\.margin\) this\.focusOn\(key\);/.test(panel));
  assert.ok(note.includes('the card still becomes the focus for the layout (`focusOn`)'));
});

test('the Send confirm\'s words and the notice\'s are the model\'s', () => {
  assert.ok(note.includes('"accept the N pending changes (M arrived since you last looked)"'));
  // decision 41 (2026-09-09) moved the option to the seen split: the unseen pending changes are named as staying pending, and
  // the arrivals' count is the line's alone (the same set, said once). The paragraph's quoted words are the option as the
  // follow-on built it; the seen follow-on's paragraph carries the words as they are now
  assert.ok(model.includes('unseen + " unseen " + (unseen === 1 ? "stays" : "stay") + " pending)"'));
  assert.ok(!model.includes('" arrived since you last looked"'), 'the option no longer says arrived: the line under the header does');
  assert.ok(note.includes('"api made 11 changes and 7 replies since you last looked"'));
  assert.ok(model.includes('return listWords(names) + " made " + listWords(parts) + " since you last looked";'));
});

test('the Tests section and the Docs section carry the follow-on, naming the same modules and the guide\'s sentences', () => {
  const bullet = tests.slice(tests.indexOf('- The arrivals follow-on (2026-09-09):'));
  assert.ok(bullet.length > 0, 'the Tests bullet');
  for (const m of ['file-comments-model-arrivals.test.ts', 'file-comments-arrivals.test.ts', 'file-comments-arrivals-browser.test.ts', 'tests/test_guide_files_arrivals.py', 'tools/file-review-plan-arrivals.test.mjs']) {
    assert.ok(bullet.includes('`' + m + '`'), `the bullet names ${m}`);
    assert.ok(note.includes('`' + m + '`'), `the paragraph names ${m}`);
  }
  assert.ok(docs.includes('With the arrivals follow-on (2026-09-09), that a line under the panel\'s header counts what the session added since you last looked'));
  const files = guide.replace(/\s+/g, ' ');
  assert.ok(files.includes('A line under the panel\'s header counts the changes, comments, and replies the session added since you last looked'));
  // The save sentence is taken from the guide by its opening, not quoted whole: the arrivals review's first round rewrote
  // it to name every gesture the panel counts (a click, a tap, a key, not scrolling alone), and a pin holding the first
  // wording went red for a sentence that had only got more accurate. tests/test_guide_files_save_standdown.py derives
  // the words from the constructor's listeners; this pin holds the sentence's opening and its round-1 clause, and
  // refuses the first wording, so the two suites agree on which sentence the guide carries.
  const save = files.match(/Saving brings the new card into view[^.]*\./);
  assert.ok(save, 'the guide\'s save sentence');
  assert.ok(save[0].includes('unless you scrolled, clicked, tapped, or pressed a key while the save was under way'), save[0]);
  assert.ok(!save[0].includes('unless you scrolled on'), 'the first wording named scrolling as the only stand-down: ' + save[0]);
});

test('the seed is stated as built: the first render and the first status with the panel open both seed the set, and the rule reads the author label alone', () => {
  // the review's consolidation (2026-09-09): the round made the open's first status all seen too (a panel first opened
  // minutes after the probe had named everything since as arrivals) and the paragraph still described the render's seed
  // alone; and the author-label limit the review asked to be stated is stated
  assert.ok(note.includes('seeded at its first render with a status from everything in it and again from the first status to land with the panel open (`seenOpen`'));
  assert.ok(note.includes('so a file opened fresh has no arrivals, whatever the session added between the probe and the open'));
  assert.ok(panel.includes('seenOpen = false;'), 'the flag');
  assert.ok(panel.includes('if (!this.seenOpen) {\n      if (!this.open) return;\n      this.seenOpen = true;\n      for (const e of entries) seen.add(e.key);\n      return;\n    }'), 'the first status with the panel open seeds the set and files no arrival');
  assert.ok(note.includes('a record labelled `you` is the person\'s whoever wrote it, and one under any other label is not, whatever its `authorId`'));
  assert.ok(model.includes('return entries.filter((e) => e.author !== YOU && !seen.has(e.key));'), 'the model\'s rule reads the label');
  assert.ok(panel.includes('if (e.author === YOU) seen.add(e.key);'), 'and so does the panel\'s');
});
