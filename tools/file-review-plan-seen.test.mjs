// The seen follow-on's paragraph and decisions 41 and 42 (plans/file-review.md, under Slice 2 and in Decisions) held to
// the code, the message builders, the vendored skill and the modules they name.
//
// The paragraph records two rulings of the user's on 2026-09-09: the Send's accept takes only the pending changes the
// person has seen (decision 41), and the edit-to-comment link leaves the loop, with decisions never resolving a comment
// (decision 42). A record that names a function the panel no longer has, a message line the builders no longer print, or a
// module that is not in the tree costs the next reader the search it was meant to save, so every identifier the paragraph
// carries in backticks is checked against the panel, the model, the kernel and the host; the builders' command lines
// against both builders; the retired clause against the model; and the modules it names against the tree and the Tests
// section. Synthetic: only the repo's own text.
// Run: node --test tools/file-review-plan-seen.test.mjs
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
const kernel = read('kernel', 'kernel.py');
const host = read('tools', 'file-comments-host.mjs');
const skill = read('vendor', 'track-changents', 'skill', 'SKILL.md');
const readme = read('vendor', 'track-changents', 'README.md');
const guide = read('docs', 'guide.md');
const context = read('CONTEXT.md');

function between(doc, from, to) {
  const a = doc.indexOf(from);
  assert.ok(a >= 0, `${JSON.stringify(from)} not found`);
  const b = doc.indexOf(to, a + from.length);
  assert.ok(b > a, `${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return doc.slice(a, b).replace(/\s+/g, ' ');
}
const LABEL = 'The seen follow-on (2026-09-09):';
const note = between(plan, LABEL, 'The arrivals follow-on (2026-09-09):');
const tests = between(plan, '\n## Tests', '\n## Docs');
const docs = between(plan, '\n## Docs', '\n## Deliberately not in v1');
const d41 = between(plan, '41. **The Send\'s accept takes the changes you have seen', '42. **');
const d42 = between(plan, '42. **The edit-to-comment link leaves the loop', '\n## Open questions');

test('the paragraph stands under Slice 2 and the two decisions in Decisions, each paraphrasing the user', () => {
  assert.ok(between(plan, '### Slice 2: the session', '### Slice 3: region comments on images').includes(LABEL));
  assert.ok(note.includes('a Send had accepted eleven changes they had not looked at'));
  assert.ok(note.includes('an unseen change is never accepted by a send'));
  assert.ok(note.includes('confused them and is gone'));
  for (const text of [note, d41, d42]) {
    assert.ok(!/"[^"]*\b(I|my|me)\b[^"]*"/.test(text.replace(/"accept the [^"]*"/g, '')), 'no quoted utterance of the user\'s');
  }
  assert.ok(d41.includes('(2026-09-09)') && d42.includes('(2026-09-09)'));
  assert.ok(d42.includes('the user found the link too confusing and asked for it to go'));
});

test('every identifier the paragraph names in backticks is in the panel, the model, the kernel, the host, the skill or the tree', () => {
  const names = Array.from(note.matchAll(/`([^`]+)`/g), (m) => m[1]);
  assert.ok(names.length >= 15, 'the paragraph names its code: ' + names.length);
  const sources = [panel, model, kernel, host];
  for (const n of names) {
    if (/\.(test\.ts|py|mjs)$/.test(n)) {
      const rel = n.includes('/') ? n : path.join('ui', 'webview', n);
      assert.ok(fs.existsSync(path.join(REPO, rel)), `${n} is in the tree`);
    } else if (n === 'file-comments-model.ts') {
      assert.ok(fs.existsSync(path.join(REPO, 'ui', 'webview', n)));
    } else if (n === 'mutate("accept", { ids })') {
      assert.ok(panel.includes('await this.mutate("accept", { ids: acceptIds }, "send")'), 'the send\'s accept call');
    } else if (n === 'track-edit --thread <id>' || n === 'track-edit' || n === 'track-reply') {
      assert.ok(skill.includes(n.split(' ')[0]), `${n} is a CLI the skill names`);
    } else if (n === 'sendOpts.accept') {
      assert.ok(panel.includes('this.sendOpts.accept'));
    } else if (n === 'accepted' || n === 'anchorAt') {
      assert.ok(host.includes(n), `${n} is a field the host writes`);
    } else {
      const bare = n.replace(/^_/, '_');
      assert.ok(sources.some((src) => src.includes(bare + '(') || src.includes(bare + ' ') || src.includes(bare + ';') || src.includes(bare + ',')),
        `${n} is a function or a field of the panel, the model, the kernel or the host`);
    }
  }
});

test('decision 41 as built: the split, the words, the by-id accept after the send\'s gesture, the reply\'s count, the disabled box', () => {
  assert.ok(model.includes('export function partitionPending(hunks: Hunk[], seen: ReadonlySet<string> | null): { seen: Hunk[]; unseen: Hunk[] } {'));
  assert.ok(model.includes('(seen && seen.has("chg:" + h.id) ? out.seen : out.unseen).push(h);'), 'the split reads statusEntries\' key for a change');
  assert.ok(model.includes('out.push({ key: "chg:" + h.id, kind: "change"'), 'which is the key statusEntries writes');
  assert.ok(note.includes('"accept the N pending changes you have seen"'));
  assert.ok(model.includes('" you have seen"'));
  assert.ok(note.includes('"(K unseen stay pending)"'));
  assert.ok(model.includes('unseen + " unseen " + (unseen === 1 ? "stays" : "stay") + " pending)"'));
  assert.ok(note.includes('nothing is accepted until you look'));
  assert.ok(model.includes('"; nothing is accepted until you look)"'));
  assert.ok(!model.includes('" arrived since you last looked"'), 'the option no longer says arrived; the arrivals line does');
  const send = panel.slice(panel.indexOf('async doSend(): Promise<void> {'), panel.indexOf('private async sendOnce('));
  assert.ok(send.indexOf('this.gesture();') < send.indexOf('const acceptIds = this.sendOpts.accept ? this.pendingSplit(s).seen.map((h) => String(h.id)) : [];'), 'the split is read after the send\'s gesture');
  assert.ok(send.includes('await this.mutate("accept", { ids: acceptIds }, "send")'));
  assert.ok(!send.includes('"accept-all"'), 'never an accept-all from the send');
  assert.ok(send.includes('accepted = decided.length;'), 'the message\'s count is the reply\'s');
  const sync = panel.slice(panel.indexOf('private syncAcceptOption('), panel.indexOf('private todoOpts('));
  assert.ok(sync.includes('cb.disabled = split.seen.length === 0;'));
  assert.ok(sync.includes('cb.checked = split.seen.length > 0 && this.sendOpts.accept;'));
  assert.ok(panel.includes('if (cb && this.status) this.syncAcceptOption(cb, this.status);'), 'the in-place update after a gesture');
  assert.ok(panel.includes('if (split.seen.length + split.unseen.length) opts.appendChild(this.acceptOption(s));'), 'the render');
});

test('decision 42 as built: both builders print plain track-edit and track-reply <id>, byte for byte; the skill patch; the host never resolves', () => {
  const EDIT_TS = '"  • to revise the text: node ~/.claude/hooks/track-edit.mjs --file " + word + \' --old "<exact text>" --new "<replacement>"\'';
  const EDIT_PY = '"  • to revise the text: node ~/.claude/hooks/track-edit.mjs --file %s --old \\"<exact text>\\" --new \\"<replacement>\\""';
  assert.ok(model.includes(EDIT_TS), 'the webview builder\'s edit line: plain track-edit');
  assert.ok(kernel.includes('lines.append("  • to revise the text: node ~/.claude/hooks/track-edit.mjs --file %s "\n                     "--old \\"<exact text>\\" --new \\"<replacement>\\"" % word)') || kernel.includes(EDIT_PY),
    'the kernel builder\'s edit line: plain track-edit');
  assert.ok(!model.includes('track-edit.mjs --file " + word + \' --thread'), 'no --thread on the webview builder\'s edit line');
  assert.ok(!kernel.includes('track-edit.mjs --file %s --thread'), 'no --thread on the kernel builder\'s edit line');
  assert.ok(model.includes('track-reply.mjs --file " + word + \' --thread <id> --note "<your reply>"\''), 'the reply line keeps the comment id');
  assert.ok(kernel.includes('track-reply.mjs --file %s --thread <id> "'), 'and so does the kernel\'s');
  assert.ok(fs.existsSync(path.join(REPO, 'vendor', 'track-changents', 'patches', '0006-skill-plain-track-edit-no-comment-link.patch')), 'patch 0006');
  assert.ok(readme.includes('0006-skill-plain-track-edit-no-comment-link.patch'), 'the README row');
  assert.ok(!skill.includes('track-edit --thread'), 'the vendored skill no longer names the link');
  assert.ok(skill.includes('Do NOT pass `--thread`'));
  assert.ok(host.includes('function requireCommentsUntouched(ctx, store, loadedComments, verb) {'));
  assert.ok(host.includes("requireCommentsUntouched(ctx, store, loadedComments, all ? 'accept-all' : 'accept');"), 'checked in doAccept');
  assert.ok(host.includes("requireCommentsUntouched(ctx, store, loadedComments, 'save');"), 'and in doSave');
  assert.ok(!host.includes('c.resolved = true;'), 'no decision sets resolved');
});

test('the retired clause is gone: the model has no resolve count and no acknowledgment tail, and the panel names neither', () => {
  assert.ok(note.includes('"resolves M comments" clause and the acknowledgment line\'s tail are retired'));
  assert.ok(!model.includes('export function resolvedByAccept('), 'resolvedByAccept is gone');
  assert.ok(!model.includes('export function sentNoteWords('), 'sentNoteWords is gone');
  assert.ok(!model.includes('"resolves "'), 'no resolve words in the option');
  assert.ok(!panel.includes('resolvedByAccept') && !panel.includes('sentNoteWords'));
  assert.ok(!panel.includes('moved to Resolved'));
});

test('the Tests section and the Docs section carry the follow-on, naming the same modules and the guide\'s sentence; CONTEXT.md says the accept takes the seen changes', () => {
  const bullet = tests.slice(tests.indexOf('- The seen follow-on (2026-09-09):'));
  assert.ok(bullet.length > 0, 'the Tests bullet');
  for (const m of ['file-comments-model-seen.test.ts', 'file-comments-send-seen.test.ts', 'file-comments-send-seen-browser.test.ts', 'tests/test_guide_files_seen.py', 'tools/file-review-plan-seen.test.mjs']) {
    assert.ok(bullet.includes('`' + m + '`'), `the bullet names ${m}`);
    assert.ok(note.includes('`' + m + '`'), `the paragraph names ${m}`);
  }
  assert.ok(docs.includes('With the seen follow-on (2026-09-09), that the Send\'s checkbox accepts only the pending changes you have seen'));
  const files = guide.replace(/\s+/g, ' ');
  assert.ok(files.includes('**accept the pending changes you have seen**, accepts before the send the pending changes you have looked at'));
  assert.ok(!files.includes('resolves comments the session had answered'), 'the guide no longer describes the resolve');
  assert.ok(context.replace(/\s+/g, ' ').includes('The accept it offers takes only the pending changes the person has seen; an unseen change stays pending.'));
});
