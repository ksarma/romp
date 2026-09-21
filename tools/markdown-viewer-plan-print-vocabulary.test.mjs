// The plan's print follow-on (plans/markdown-viewer.md, "## Follow-on: Print (2026-09-19)") calls what the Comments
// panel draws over a PDF page "comments", the noun CONTEXT.md's File comment entry gives it, and never "annotation",
// a word that entry lists under _Avoid_. The section's P4 first read "never the annotated canvases" of the pdf.js
// pages the panel lays its region comments over (a review finding, 2026-09-19: the plan that governs the viewer had
// taken up the avoided noun for a file comment, and a later section or UI copy could carry it on). It now reads "never
// the canvases with their comments", and this module holds that: CONTEXT.md still lists the word under Avoid (the
// premise, read from its source the way tools/file-review-plan-kind-cue.test.mjs reads it), the section's prose has no
// form of the word (code spans set aside, as the print pin sets them aside: a code span is a name, and the section
// names the word once as a word), the P4 sentence says what the print is not in the entry's noun, and the section
// names this module. Synthetic: only the repo's own text.
// Run: node --test tools/markdown-viewer-plan-print-vocabulary.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');

const plan = read('plans', 'markdown-viewer.md');
const context = read('CONTEXT.md');

// The section, from its head to the next `## ` heading or the plan's end (the round-6 review's cluster F of the print PR; the
// round-7 review's extra5-2 found the slice running to the plan's end in the three modules that read the section, this one
// among them), hard wraps collapsed so an assertion survives a rewrap, and its prose alone: code spans are names.
const HEAD = '## Follow-on: Print (2026-09-19)';
function printSectionOf(text) {
  const at = text.indexOf('\n' + HEAD + '\n');
  assert.ok(at >= 0, 'the follow-on section is in the plan');
  const next = text.indexOf('\n## ', at + 1);
  return text.slice(at, next >= 0 ? next : text.length).replace(/\s+/g, ' ');
}
const section = printSectionOf(plan);
const prose = section.replace(/`[^`]*`/g, '');

// The words CONTEXT.md's `**term**:` entry lists under _Avoid_, parentheticals dropped; the Avoid line wraps, so it is
// read to the entry's end (the blank line).
function avoidWords(term) {
  const entry = new RegExp('^\\*\\*' + term + '\\*\\*:\\n([\\s\\S]*?)(?=\\n\\n)', 'm').exec(context);
  assert.ok(entry, 'CONTEXT.md has the ' + term + ' entry');
  const at = entry[1].indexOf('_Avoid_:');
  assert.ok(at >= 0, 'the ' + term + ' entry has an Avoid line');
  return entry[1].slice(at + '_Avoid_:'.length).replace(/\([^)]*\)/g, '').split(',').map((w) => w.trim()).filter(Boolean);
}

test('the premise: CONTEXT.md lists "annotation" under Avoid for a file comment', () => {
  const avoid = avoidWords('File comment');
  assert.ok(avoid.includes('annotation'), 'File comment avoids "annotation" (' + avoid.join(', ') + ')');
});

test('P4 calls the pdf.js pages the canvases with their comments, and no form of the avoided word is in the section\'s prose', () => {
  assert.ok(section.includes('so Print opens the /file tab and the PDF prints from there, never the canvases with their comments'),
    'P4 names the canvases by the comments on them');
  const hits = [...prose.matchAll(/\S*annotat\S*/gi)].map((m) => m[0]);
  assert.deepEqual(hits, [], 'no form of "annotation" in the section\'s prose');
});

test('the section read here ends at the next `## ` heading: a decoy section appended after the Print head, naming the avoided word, is outside the prose read (FAILS BEFORE: the slice ran to the plan\'s end, so a later section\'s word would have red this module as the Print section\'s)', () => {
  const decoy = '\n## Decoy follow-on (this case\'s own synthetic section)\n\nA decoy sentence after the next heading naming an annotation.\n';
  assert.equal(printSectionOf(plan + decoy), section, 'the section is the same text with a section appended after it');
  assert.ok(!printSectionOf(plan + decoy).includes('naming an annotation'), 'the decoy\'s sentence is outside it (the section itself names the word once, as a word in a code span)');
  assert.ok((plan + decoy).replace(/\s+/g, ' ').includes('naming an annotation'), '...where an unbounded read holds it');
});

test('the section names this module and what it holds', () => {
  assert.ok(section.includes(path.basename(fileURLToPath(import.meta.url)) + ' holds this section\'s words to CONTEXT.md\'s File comment entry'),
    'the section names this pin');
});
