// tools/track-comment-race.test.mjs speaks CONTEXT.md's word for a comment with its replies. The slice's review
// (round 3, 2026-09-11) found the module still calling the comment its replies go to a "thread" (its header's
// replies case and the message on the check that the comment is in the sidecar) after the round before had
// taken that word out of the plan's records and pinned them
// (tools/file-review-plan-sidecar-adr-modules.test.mjs), a pin that reads the module for its test names cut one
// word short of the noun, so it never read the word there. CONTEXT.md's File comment entry sets "thread"
// aside: in romp a comment thread is a forked side session anchored to the chat, so the record (replies "to
// one earlier comment") and the module (replies "to one thread") described two different things. The module
// says "the earlier comment" now, the record's words, and the identifier that carried the id under the flag's
// name is `earlier`.
// Two uses stay, and are the vendored CLI's own: `--thread`, the flag track-reply takes the comment id under,
// and `Reply posted to thread.`, the line it prints; both are read from the CLI here so the exclusion is exactly
// its words and nothing wider. The module's "note" is the file (docs/report.md in the notes-api world, the
// vendored tool's word for one), which the entry does not set aside: it avoids "note" for a file comment,
// the send's paragraph, and the module never calls a comment that.
// Synthetic: only the repo's text.
// Run: node --test tools/track-comment-race-vocabulary.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const MODULE = 'tools/track-comment-race.test.mjs';
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');

const race = read(...MODULE.split('/'));
const context = read('CONTEXT.md');
const plan = read('plans', 'file-review.md');
const replyCli = read('vendor', 'track-changents', 'cli', 'track-reply.mjs');

const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

// The words CONTEXT.md's File comment entry lists under _Avoid_, parentheticals dropped.
function avoidWords(term) {
  const entry = new RegExp(`^\\*\\*${esc(term)}\\*\\*:\\n([\\s\\S]*?)(?=\\n\\n)`, 'm').exec(context);
  assert.ok(entry, `CONTEXT.md has the ${term} entry`);
  const at = entry[1].indexOf('_Avoid_:');
  assert.ok(at >= 0, `the ${term} entry has an Avoid line`);
  return entry[1].slice(at + '_Avoid_:'.length).replace(/\([^)]*\)/g, '').split(',').map((w) => w.trim()).filter(Boolean);
}

// The plan's Tests bullet describes the module in one parenthetical after its name; that text, whitespace
// collapsed.
function recordOf(module) {
  const name = `\`${module}\` (`;
  const a = plan.indexOf(name);
  assert.ok(a >= 0, `the plan's Tests bullet names ${module}`);
  const b = plan.indexOf(')', a + name.length);
  assert.ok(b > a, 'and closes the parenthetical');
  return plan.slice(a + name.length, b).replace(/\s+/g, ' ');
}

// The vendored CLI's two words for the comment a reply goes to: the flag it takes the id under and the line it
// prints.
const FLAG = '--thread';
const LINE = 'Reply posted to thread.';

test('the vendored track-reply takes the comment id as --thread and prints its one line with the same word; the module holds both, as the CLI\'s words', () => {
  assert.ok(replyCli.includes(`if (!args.thread) fail('${FLAG} <id> is required.');`), 'the CLI requires the flag');
  assert.ok(replyCli.includes(`process.stdout.write('${LINE}\\n');`), 'the CLI prints the line');
  assert.ok(race.includes(`'${FLAG}', earlier`), 'the module passes the earlier comment\'s id under the flag');
  assert.ok(race.includes(`'track-reply': '${LINE}\\n'`), 'and expects the line as the reply\'s one line');
});

test('outside the CLI\'s flag and line, the module never calls a comment with its replies by the word CONTEXT.md sets aside for a file comment', () => {
  assert.ok(avoidWords('File comment').includes('thread'), 'File comment avoids "thread"');
  assert.ok(plan.includes('a **file comment** is the object (never "thread", which in\nromp is a forked side session anchored to the chat)'), 'the plan binds itself to that word');
  const own = race.split(FLAG).join(' ').split(LINE).join(' ');
  assert.doesNotMatch(own, /\bthreads?\b/i, 'the module calls the comment its replies go to a comment (the earlier comment), not by the forked side session\'s word');
  assert.ok(race.includes('//   * the same with track-reply beside it: three comments and three replies to one earlier comment at once.'), 'the header\'s replies case');
  assert.ok(race.includes('const earlier = loadStore(w.storePath, NOTE).comments[0].id;'), 'the id is held as the earlier comment');
  assert.ok(race.includes('const head = store.comments.find((c) => c.id === earlier);'), 'and looked up as it');
  assert.ok(race.includes('assert.ok(head, `round ${r}: the earlier comment is in the sidecar`);'), 'the check names it so');
});

test('the module and the plan\'s Tests bullet describe the replies case in the same words', () => {
  const record = recordOf(MODULE);
  const phrase = 'three comments and three replies to one earlier comment at once';
  assert.ok(record.includes(phrase), `the record says ${JSON.stringify(phrase)}: ${record}`);
  assert.ok(race.includes(phrase), 'and so does the module');
  assert.doesNotMatch(record.replace(/`[^`]*`/g, ''), /\bthreads?\b/i, 'neither by the set-aside word');
});
