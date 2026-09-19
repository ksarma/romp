// Decisions 47 and 48 (plans/file-review.md) and the Vendoring paragraph's guard sentences held to the
// Bash-side track guard, the installer, the uninstaller, the vendored patch series and the tests they name.
//
// Decision 47 records the guard on the Bash tool: why (the dry run's compound command), what it reads (the
// grammar: the verbs, the redirections, the interpreters), what it lets through, and where it is registered.
// Decision 48 records that sessions are asked to commit the comments folder and where the ask lives. A record
// that names a verb the hook no longer reads, a matcher the installer no longer writes, or a module that is
// not in the tree costs the next reader the search it was meant to save, so every such claim is checked
// against the source. The three prose surfaces beside the plan that state the numeric exception's boundary
// (docs/install.md, the hook's row in hooks/README.md, the ledger entry) are held to the hook's set here too,
// since round 3's mutation pass (2026-09-19) inverted each and nothing went red. Synthetic: only the repo's own text.
// Run: node --test tools/file-review-plan-bash-guard.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');

const plan = read('plans', 'file-review.md');
const hook = read('hooks', 'romp-track-bash-guard.mjs');
const install = read('install.sh');
const uninstall = read('bin', 'romp-uninstall');
const hooksReadme = read('hooks', 'README.md');
const guide = read('docs', 'guide.md').replace(/\s+/g, ' ');
const prompt = read('claude', 'romp-session-prompt.md').replace(/\s+/g, ' ');

function between(doc, from, to) {
  const a = doc.indexOf(from);
  assert.ok(a >= 0, `${JSON.stringify(from)} not found`);
  const b = doc.indexOf(to, a + from.length);
  assert.ok(b > a, `${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return doc.slice(a, b).replace(/\s+/g, ' ');
}
const d47 = between(plan, '47. **A guard on the Bash tool too**', '48. **');
const d48 = between(plan, '48. **Sessions commit the comments folder**', '\n## Open questions');
const vendoring = between(plan, '### Vendoring', '### The comments log');
const tests = between(plan, '\n## Tests', '\n## Docs');
const docs = between(plan, '\n## Docs', '\n## Deliberately not in v1');

test('decision 47 paraphrases the dry run, dates itself, and quotes no one', () => {
  assert.ok(d47.includes('(2026-09-10)'));
  assert.ok(d47.includes('track-config and cp in a single compound command on a tracked file'), 'the finding, paraphrased');
  assert.ok(d47.includes('the copy landed raw'));
  assert.ok(d47.includes('recovered from its own base copy'));
  for (const text of [d47, d48]) assert.ok(!/"[^"]*\b(I|my|me)\b[^"]*"/.test(text), 'no quoted utterance of the user\'s');
  assert.ok(!/\u2014/.test(d47) && !/\u2014/.test(d48), 'no em dash in the new decisions');
});

test('decision 47 names the hook, and the hook reads every verb, redirection and interpreter the decision says it reads', () => {
  assert.ok(d47.includes('`hooks/romp-track-bash-guard.mjs`'));
  assert.ok(fs.existsSync(path.join(REPO, 'hooks', 'romp-track-bash-guard.mjs')));
  for (const verb of ['cp', 'mv', 'install', 'ln', 'tee', 'sponge', 'truncate', 'dd', 'sort', 'sed', 'perl', 'python', 'node', 'cd']) {
    assert.ok(d47.includes(verb), `decision 47 names ${verb}`);
    assert.ok(new RegExp(`case '${verb}'`).test(hook), `the hook has a case for ${verb}`);
  }
  for (const op of ['>', '>>', '>|', '&>']) {
    assert.ok(d47.includes(`\`${op}\``), `decision 47 names the ${op} redirection`);
    assert.ok(hook.includes(`'${op}'`), `WRITE_REDIRECTS holds ${op}`);
  }
  assert.ok(/const WRITE_REDIRECTS = new Set\(\['>', '>>', '>\|', '&>', '&>>', '>&', '<>'\]\)/.test(hook));
  assert.ok(d47.includes('descriptor-prefixed redirection'));
  assert.ok(/\/\^\[0-9\]\+\$\/\.test\(buf\)/.test(hook), 'the lexer drops a digits-only word glued to < or > as the descriptor');
  assert.ok(d47.includes('a literal path a python or node inline script opens with a write mode'));
  assert.ok(hook.includes('export function scriptWriteTargets(kind, text)'));
  // the verdict: store-io's findVaultRoot, then isTrackedFile's three steps run by the hook's own trackedIn so the
  // closure is built once per call (the review's consolidation, 2026-09-10: the decision had said the hook called
  // isTrackedFile itself), and the real path judged beside the name given
  assert.ok(d47.includes('store-io\'s `findVaultRoot` and the three steps of its `isTrackedFile` (the veto list, the explicit list by name, then the link closure), which the hook runs itself as `trackedIn`'));
  assert.ok(hook.includes("import { findVaultRoot, isTrackedFile, isNonTextPath, hasNulBytes } from '../vendor/track-changents/store-io.mjs'"));
  assert.ok(hook.includes('function trackedIn(root, file, closures)') && hook.includes('const root = rootOf(file);') && hook.includes('const root = findVaultRoot(file);'));
  assert.ok(d47.includes('judged under the name given and under the real path the kernel opens, so a symlink to a tracked file carries no write past it'));
  assert.ok(hook.includes('function realPathOf(file') && hook.includes('return real != null && real !== file && guardedByName(real, closures);'));
  // a link is one entry: ln names its link and walks no source
  assert.ok(d47.includes('a directory source walked to the files it carries, a link one entry whatever it points at'));
  assert.ok(hook.includes("const land = (s, d) => (verb === 'ln' ? [d] : landing(s, d, cwd));"));
});

test('decision 47 states what passes, and the hook agrees: reads, opaque commands, non-text files, no ROMP_SID', () => {
  assert.ok(d47.includes('a read (cat, grep, diff, git, sed without -i) names no target'));
  assert.ok(d47.includes('a command behind eval, xargs or a shell -c it cannot read is unresolvable and passes'));
  // since 2026-09-18 a write target the hook cannot read (a variable, a substitution, a glob or brace list it cannot
  // expand) is refused while a project that tracks anything is in play, and the decision says so
  assert.ok(d47.includes('a write whose target the hook cannot read') && d47.includes('is refused while a project that tracks anything is in play'));
  assert.ok(hook.includes('function trackingRootAt(dir, memo)') && hook.includes('function inPlayFor(u, cwd, memo)') && hook.includes('const cannotRead = (w, how, why = null) => {'));
  assert.ok(hook.includes('which is not a literal path'), 'the refusal says the target is not literal');
  // the round-1 review (2026-09-18) bounded the rule in four places and named two residuals, and the decision
  // records each against the hook's own function
  assert.ok(d47.includes('holds an entry the literal rule could refuse') && hook.includes('function tracksRefusable(root, memo)'));
  assert.ok(d47.includes('the directory judged under its real path and its name') && hook.includes('for (const d of real && real !== dir ? [real, dir] : [dir]) {'));
  assert.ok(d47.includes('the landing folder counting only when a tracked file could land there') && hook.includes('function landingInPlay(hit, memo)'));
  // review round 2 (2026-09-18): the landing cap is recorded as the deliberate false refusal it is, the numeric
  // set is per shell with BASHPID out of it, the target's own prefix is asked and a fold still resolves, and the
  // environment clause says which value can reach a refusal
  assert.ok(d47.includes('or when it holds more than 2000 entries, past which the hook does not scan it and takes it as in play (`LANDING_SCAN_CAP`, a deliberate false refusal'));
  assert.ok(hook.includes('const LANDING_SCAN_CAP = 2000;') && hook.includes('if (names.length > LANDING_SCAN_CAP) return true;'), 'the cap the decision names');
  // review round 3 (2026-09-19): the numeric set is the process id alone, in every shell, and the decision says why;
  // the per-shell table is gone from the hook with the names it trusted
  assert.ok(d47.includes('a target whose only expansions are `$$` and `${$}`, the shell\'s process id, and whose text is an absolute path outside every project in play is allowed'));
  assert.ok(d47.includes('The numeric set is those two spellings and nothing else, in every shell: every other candidate can be unset or shadowed by the command and then hold a path'));
  assert.ok(!d47.includes('read-only integers in bash and in zsh'), 'the round-2 premise is gone from the decision');
  assert.ok(hook.includes("const NUMERIC_EXPANSIONS = ['$$', '${$}'];"), 'the numeric set is the two spellings of the process id');
  assert.ok(!/NUMERIC_EXPANSIONS = \[[^\]]*(RANDOM|SECONDS|BASHPID)/.test(hook) && !/['"](RANDOM|SECONDS|BASHPID)['"]/.test(hook), 'no other name is in the set, and no code names one');
  assert.ok(!hook.includes('KEEPS_NUMERIC_SPECIALS') && !hook.includes('POSIX_SH_NUMERIC') && !hook.includes('numericSetFor'), 'the per-shell table is gone');
  assert.ok(hook.includes('recurse(sh.script.text, name)') && hook.includes('recurse(body, name)') && hook.includes('lex(command, shell)') && hook.includes("const ANSI_C_SHELLS = new Set(['bash', 'zsh']);"), 'a script handed to a shell is lexed as that shell reads `$\'...\'`');
  assert.ok(d47.includes('`$\'...\'` is ANSI-C quoting in bash and zsh, a literal word') && hook.includes('function ansiC(body)') && hook.includes("if (e.kind === 'ansi') {"), 'ANSI-C quoting');
  // the target's own project, asked first for every target the hook can place (round 2 for a numeric one, round 3 for
  // every unreadable word and for a relative spelling), and the fold judged as the kernel opens the path
  assert.ok(d47.includes('the project the target\'s own literal directory part sits in is asked first, from any cwd, for every target the hook cannot read that it can place, absolute or relative to a write-time directory it knows'));
  assert.ok(hook.includes('function ownProjectFor(u, memo)') && hook.includes('const own = trackingRootAt(v.dir, memo);') && hook.includes('if (own && landingInPlay(own, memo)) return v.folder'));
  assert.ok(d47.includes('a fold that leaves no expansion handed to the literal rule') && hook.includes('function foldSegments(segs)') && hook.includes('if (v.literal != null && isGuardedPath(v.literal, memo.closures)) return { literal: v.literal };'));
  assert.ok(d47.includes('a `..` after a directory that exists climbs from that directory\'s real path, as the kernel does') && hook.includes('function resolveLiteral(text, dir)'));
  assert.ok(d47.includes('each entry of that directory that exists now and whose name the process id could spell') && hook.includes('function spelledCandidates(segs, idx, dir, memo, budget)') && hook.includes('function couldSpell(seg, name)'));
  // review round 2's addendum (2026-09-18) and round 3: the numeric folder name is a deliberate false refusal wherever
  // the landing gate on the literal directory part holds, not in the first segment only, and the refusal names the
  // unknown folder with a remedy the person can take
  assert.ok(d47.includes('the landing gate on that literal directory part is folder-granular, so a numeric name in any folder where a tracked file could land is refused from any cwd while its literal spelling may pass'));
  assert.ok(d47.includes('a deliberate false refusal ruled correct in round 2\'s addendum (2026-09-18) for the first segment (the folder\'s name does not exist at check time and is not derivable from the text'));
  assert.ok(d47.includes('names the unknown folder when the expansion names one, at any depth, and offers a literal folder name or a write outside the project, never the name the shell would give it'));
  assert.ok(!d47.includes('only the first segment behaves so') && !d47.includes('the class is the first segment only'), 'the first-segment boundary is gone');
  assert.ok(hook.includes('unknownFolder: v.folder') && hook.includes('unknownFolder: view.folder') && hook.includes('if (hit.unknownFolder) {'), 'the hook routes the case at any depth');
  assert.ok(hook.includes('I cannot tell which folder the write lands in') && hook.includes('Spell the folder out with a literal name of your own, or write outside that project') && !hook.includes('the name the shell would give it'), 'a refusal that names the folder and a remedy the person can take');
  assert.ok(hook.includes('function numericOutside(view, root)') && hook.includes('function numericView(u, memo)'));
  // round 3's other classes: a literal relative target after a cd the hook cannot follow, a landing folder no project
  // claims, the option clusters bash takes a word for, and the recursion caps
  assert.ok(d47.includes('a literal relative target after a `cd` the hook cannot follow') && hook.includes("{ kind: 'unknownDir', text: unknownWhy }") && hook.includes('function enterable(dir)'));
  assert.ok(d47.includes('a landing folder no project claims counts when an entry of it is or leads to a tracked file') && hook.includes('function guardedEntryIn(dir, memo)'));
  assert.ok(d47.includes('an entry named by the process id in a folder outside every project that holds more than 2000 entries, which is not listed') && hook.includes('if (!names || names.length > LANDING_SCAN_CAP) return out;'), 'the open scan is stated');
  assert.ok(d47.includes('`bash -O extglob -c') && hook.includes("(shell === 'bash' && (t === '-O' || t === '+O'))"));
  assert.ok(d47.includes('nested past 64 substitutions or brace lists') && hook.includes('const RECURSION_CAP = 64;') && hook.includes('const BRACE_DEPTH_CAP = 64;'));
  assert.ok(d47.includes('a `$(date)` in a log\'s name among them, a cost stated to the user rather than solved'), 'the residual false refusal is stated, not claimed solved');
  assert.ok(d47.includes('the hook reads no variable named in the command to resolve the word'));
  assert.ok(d47.includes('TRACKCHANGES_ROOT, which stands in for the root search only for a directory under it') && hook.includes('const fromEnv = !!env && !outside(d, env);'));
  assert.ok(d47.includes('of those only HOME\'s value can appear in a refusal, and only as a path the hook resolved through it') && d47.includes('TRACKCHANGES_ROOT is named by the variable, never by its value, and ROMP_SID is never printed') && hook.includes("hit.fromEnv ? 'the project TRACKCHANGES_ROOT names' : hit.root"));
  assert.ok(!d47.includes('no value read there reaches a refusal'), 'the round-1 clause, false for a `$HOME` target, is gone');
  assert.ok(d47.includes('a python or node one-liner whose write path is computed') && d47.includes('the interpreter scan reads a literal path only'), 'the interpreter residual is named');
  assert.ok(hook.includes('function installDirOnly(t)'), 'install -d writes no file');
  // a glob is no longer unresolvable: it is expanded as the shell expands it (the review's second round), as are a
  // brace list, a here-string and a process substitution, and the decision says so of each
  assert.ok(!d47.includes('a path built from a variable or a glob'), 'a glob is not listed among the unresolvable');
  assert.ok(d47.includes('or a glob that matches nothing or names more than the hook will list) is refused'));
  assert.ok(d47.includes('a glob is otherwise expanded against the filesystem as the shell expands it (a redirection onto several matches or brace alternatives names each, as zsh\'s multios writes them; bash writes none)'));
  assert.ok(hook.includes('function expandGlob(w, cwd)') && hook.includes('const GLOB_MATCH_CAP = ') && hook.includes('const GLOB_READ_CAP = '));
  assert.ok(d47.includes('a brace list is expanded before the operands are read') && hook.includes('function braceExpand(text, marks, depth = 0)'));
  assert.ok(d47.includes('a here-string is scanned like a heredoc') && hook.includes("expect = { kind: 'herestring' }"));
  assert.ok(d47.includes('a process substitution\'s command is read like a `$(...)`') && hook.includes("if ((c === '>' || c === '<') && src[i + 1] === '(') {"));
  assert.ok(d47.includes('`cd` moving the working directory for what follows, inside `( ... )` only up to the `)`'));
  assert.ok(hook.includes("frames.push({ kind: 'subshell', dir, unknownDir, unknownWhy });"));
  assert.ok(hook.includes("case 'eval': case 'xargs': sawOpaqueCommand = true; break;"));
  assert.ok(d47.includes('a tracked image or PDF passes by name'));
  assert.ok(hook.includes('if (isNonTextPath(file)) return false;'));
  assert.ok(d47.includes('a source copied out of a tracked file is a read'));
  assert.ok(d47.includes('rm, a mv of the tracked file elsewhere'), 'what the hook does not read is named as such');
  assert.ok(d47.includes('Without ROMP_SID it exits 0 before reading stdin (decision 24)'));
  assert.ok(hook.includes('if (!process.env.ROMP_SID) process.exit(0);'));
  assert.ok(d47.includes('exit 2 with one line naming the file and the track-edit command'));
  assert.ok(hook.includes("process.exit(2)") && hook.includes('node ~/.claude/hooks/track-edit.mjs --file'));
});

test('decision 47 says where the hook is registered, and install.sh and romp-uninstall do it so', () => {
  assert.ok(d47.includes('registered by the same installer merge on the `Bash` matcher (synchronous, timeout 10'));
  assert.ok(install.includes('("romp-track-bash-guard.mjs", 10, False, "Bash")'));
  assert.ok(/for h in [^;]*romp-track-bash-guard\.mjs; do\n\s+ln -sf "\$ROMP_DIR\/hooks\/\$h"/.test(install), 'linked from hooks/ with romp\'s own hooks');
  assert.ok(d47.includes('removed by the uninstaller with romp\'s hooks'));
  assert.ok(/for h in [^;]*romp-track-bash-guard\.mjs; do\n\s+rm -f "\$HOME\/\.claude\/hooks\/\$h"/.test(uninstall));
  assert.ok(uninstall.includes('"romp-track-bash-guard.mjs"}'), 'in the uninstaller\'s OURS set');
  assert.ok(hooksReadme.includes('| `romp-track-bash-guard.mjs` | PreToolUse on `Bash` |'), 'the hooks README table row');
});

test('the Vendoring paragraph on the guard gains the Bash hook, pointing at decision 47', () => {
  assert.ok(vendoring.includes('Anything a romp session itself spawns also carries the variable'), 'the paragraph as it stood');
  assert.ok(vendoring.includes('A second PreToolUse hook, romp\'s own (`hooks/romp-track-bash-guard.mjs`, on the `Bash` matcher'));
  assert.ok(vendoring.includes('decision 47'));
});

test('decision 48 records the finding, keeps decision 25, and names the places the ask lives', () => {
  assert.ok(d48.includes('(2026-09-10)'));
  assert.ok(d48.includes('never added `.trackchanges/` to git'));
  assert.ok(d48.includes('Decision 25 is unchanged'));
  assert.ok(d48.includes('`vendor/track-changents/patches/0007'));
  assert.ok(fs.existsSync(path.join(REPO, 'vendor', 'track-changents', 'patches', '0007-skill-no-bash-writes-commit-the-folder.patch')));
  assert.ok(d48.includes('`claude/romp-session-prompt.md`'));
  assert.ok(prompt.includes('include that folder in the commit'), 'the prompt carries the sentence');
  assert.ok(d48.includes('the user did not choose staging'));
  for (const text of [d47, d48]) assert.ok(!/\b(he|his|him|owner)\b/.test(text), 'the plan speaks of the user, they; never a gendered pronoun or the owner');
  assert.ok(guide.includes('Sessions are asked to include the folder when they commit their own work'));
});

test('the Tests and Docs sections name the modules and the doc sentences this slice adds', () => {
  for (const mod of ['tools/romp-track-bash-guard.test.mjs', 'tools/file-review-plan-bash-guard.test.mjs',
    'tests/test_guide_files_commit_folder.py', 'tests/test_guide_files_bash_guard.py']) {
    assert.ok(tests.includes(`\`${mod}\``), `the Tests section names ${mod}`);
    assert.ok(fs.existsSync(path.join(REPO, mod)), `${mod} exists`);
  }
  assert.ok(tests.includes('`tests/install-sh.bats`') && tests.includes('the Bash-side guard'));
  assert.ok(docs.includes('With the Bash guard follow-on (2026-09-10)'));
  assert.ok(docs.includes('`tests/test_guide_files_bash_guard.py`') && docs.includes('`tests/test_guide_files_commit_folder.py`'));
});

// ── the three prose surfaces beside the plan that state the numeric exception's boundary ──
//
// docs/install.md, the hook's row in hooks/README.md and the ledger entry for the offer each say, since round 3
// (2026-09-19), that a name built from `$RANDOM` or `$SECONDS` inside a tracked project is refused, in every shell, and
// why. The mutation pass over that round inverted each clause and nothing went red: the plan and the skill were pinned,
// these three were not. Held here to the hook's set, as decision 47's sentence is above; the shapes themselves are run
// in tools/romp-track-bash-guard.test.mjs (the numeric-set test).
const installDoc = read('docs', 'install.md').replace(/\s+/g, ' ');
const ledger = read('upstream', '2026-09-18-track-guard-non-literal-targets.md').replace(/\s+/g, ' ');

test('the install guide, the hook\'s README row and the ledger entry say a name built from $RANDOM or $SECONDS is refused inside a tracked project, in every shell, and the hook\'s numeric set is the process id alone', () => {
  assert.ok(installDoc.includes('A temp file named only by the shell\'s process id (`$$`), at an absolute path where no tracked file could land'), 'docs/install.md: the exception, as the code allows it');
  assert.ok(installDoc.includes('still runs; a name built from `$RANDOM` or `$SECONDS` is refused, since a script can reassign those'), 'docs/install.md: the refused names, with the reason');
  const row = hooksReadme.split('\n').find((l) => l.startsWith('| `romp-track-bash-guard.mjs` |'));
  assert.ok(row, 'the hook has a row in hooks/README.md');
  assert.ok(row.includes('a target whose only expansions are `$$` or `${$}`, the shell\'s process id, at an absolute path outside every project in play is allowed, and nothing else is'), 'hooks/README.md: the exception');
  assert.ok(row.includes('since `$RANDOM`, `$SECONDS` and every other name can be unset or shadowed by the command and then hold a path, so a `log.$RANDOM` inside a tracked project is refused in every shell, a deliberate false refusal recoverable in one step'), 'hooks/README.md: the refused names, with the reason');
  assert.ok(ledger.includes('a target whose only expansions are `$$` or `${$}`, the shell\'s process id, at an absolute path outside every project in play is allowed, and nothing else is'), 'the ledger entry: the exception');
  assert.ok(ledger.includes('so a `log.$RANDOM` inside a tracked project is refused in every shell, a deliberate false refusal recoverable in one step'), 'the ledger entry: the refused names');
  assert.ok(hook.includes("const NUMERIC_EXPANSIONS = ['$$', '${$}'];"), 'the set every clause describes');
});

// Round 4's contract paragraph (2026-09-19): the guard is best-effort against known write forms, its default on an
// unrecognised form is allow, and the unmodelled writers that pass are listed. The same paragraph and the SAME
// writer list sit on all four surfaces a user meets, so a user who knows the boundary can work with it; this test
// reads each file whitespace-normalised and fails if any lacks it or if the lists differ.
test('decision 47 records round 4 and each class is tied to the hook function that implements it', () => {
  assert.ok(d47.includes('Round 4 (2026-09-19, a walk-around lens) closed eight more in-model roads'));
  assert.ok(d47.includes('read a per-writer option table (`COPY_OPT`)') && hook.includes('const COPY_OPT = {') && hook.includes('function parseCopyOptions(args, verb)'));
  // since the third pass `commandOf` returns the chdirs in order (a nested `env -C` composes) and the wrapper tables live in WRAPPER_OPT
  assert.ok(d47.includes('`commandOf` returns its `chdir`') && hook.includes('return { name, args: words.slice(k + 1), chdirs, writes, wrapped };'));
  assert.ok(d47.includes('the `PREFIXES` set gained `setsid`, `flock`, `taskset`, `chrt` and `numactl`') && hook.includes("'setsid', 'flock', 'taskset', 'chrt', 'numactl'") && hook.includes('const WRAPPER_OPT = {'));
  assert.ok(d47.includes('the lexer marks a home expansion \'h\' and `extract` computes `homeAssigned`'));
  assert.ok(hook.includes("const home = (t) => { buf += t; marks += 'h'.repeat(t.length); };") && hook.includes('const homeAssigned = ctx.homeAssigned'));
  assert.ok(d47.includes('`parentTrackedRoots`') && hook.includes('function parentTrackedRoots(dir, segPrefix, memo)'));
  assert.ok(d47.includes('`foldSegments` folds a `..`') && hook.includes('const st = lstatOrNull(prefix);') && hook.includes('class UnknownPath extends Error'));
  assert.ok(d47.includes('`recordSymlink`, `applyInCommandLinks`') && hook.includes('function applyInCommandLinks(abs, links)') && hook.includes('const recordSymlink = (args, cwd) => {'));
  assert.ok(d47.includes('best-effort against known write forms, its default on an unrecognised form is allow'));
});

test('the best-effort contract and its unmodelled-writer list are stated identically on the hook header, the vendored SKILL.md, hooks/README.md and docs/install.md', () => {
  // strip the source's line-comment markers (`//` in the hook) so the paragraph reads the same whether it is a
  // comment, a markdown paragraph or a table cell, then collapse whitespace and case
  const norm = (s) => s.replace(/\/\//g, ' ').replace(/\s+/g, ' ').toLowerCase();
  // the whole paragraph, since the third pass (2026-09-19): the contract sentence, the allow-by-default sentence, the
  // sentence that says what IS refused, and the writer list (which gained the unlisted wrappers, shuf -o, the scripts the
  // shell reads from elsewhere and a cd through CDPATH the three passes found)
  const CONTRACT_PARAGRAPH = 'this guard is best-effort against known write forms: it refuses the shell writes it models and, by design, allows anything it does not recognise, so it never blocks ordinary work it cannot read; it is a backstop, not a complete boundary. the allow-by-default for an unmodelled writer is deliberately not flipped, since flipping it would refuse almost all normal work. what it does refuse, while a tracked project is in play, is a write it reads but cannot place: a target it cannot read, a path it cannot check (a stat error other than not-found), an option on a modelled writer or wrapper it does not parse in full, an env -s string, a shell option it does not know to be inert for paths, a link whose source it cannot read, and a `~` or `$home` write beside a mention of home. ';
  const LIST = 'these write forms are not modelled and still reach a tracked file: rsync; awk with a redirect inside its program; ed; ex; make; find with -delete or -exec; a git subcommand that writes the working tree (checkout, stash, apply, reset, rm, clean, mv); a computed path inside an interpreter (python3 -c, node -e); a script the shell reads from elsewhere (eval, xargs, a sourced file, trap, a command whose name is an expansion, a script held in a variable); a wrapper outside the guard\'s set (unshare, nsenter, script, setarch, setpriv); shuf -o; a cd through cdpath; and a leading opaque expansion from a cwd outside every project.';
  const CONTRACT = 'best-effort against known write forms';
  const surfaces = {
    'hook header': read('hooks', 'romp-track-bash-guard.mjs'),
    'the vendored SKILL.md': read('vendor', 'track-changents', 'skill', 'SKILL.md'),
    'hooks/README.md': read('hooks', 'README.md'),
    'docs/install.md': read('docs', 'install.md'),
  };
  for (const [name, text] of Object.entries(surfaces)) {
    const n = norm(text);
    assert.ok(n.includes(CONTRACT), `${name} states the check is best-effort against known forms`);
    assert.ok(n.includes(LIST), `${name} carries the identical unmodelled-writer list (a differing list fails here)`);
    assert.ok(n.includes('allows anything it does not recognise') || n.includes('allow') , `${name} says the default is allow`);
    // the third pass (2026-09-19): the WHOLE paragraph is identical on the four surfaces, the two sentences the hook
    // header alone carried (the allow-by-default is not flipped; what is refused) included
    assert.ok(n.includes(CONTRACT_PARAGRAPH + LIST), `${name} carries the identical contract paragraph, the allow-by-default sentence and the refused-class sentence included`);
  }
});

// The walk-around lens second pass (2026-09-19): decision 47 records the six families and each is tied to the hook
// function that implements it, so a family dropped from the code fails here by name.
test('decision 47 records the walk-around lens second pass, each family tied to its hook function', () => {
  assert.ok(d47.includes('The\n    walk-around lens second pass (2026-09-19) then closed six families') || d47.includes('walk-around lens second pass (2026-09-19) then closed six families'));
  // (1) option tables and env -S
  assert.ok(d47.includes('a glued short form\n    (`sort -oFILE`)') || d47.includes('a glued short form (`sort -oFILE`)'));
  // since the third pass env -S is refused outright (WRAPPER_OPT's `refuse`), never read as a shell string
  assert.ok(d47.includes('`env -S`/`--split-string` runs a shell string') && hook.includes("refuse: { short: 'S', long: ['split-string'] }"));
  assert.ok(/else if \(\/\^-o\.\/\.test\(t\)\) add\(sliceWord\(args\[k\], 2\), 'sort -o'\)/.test(hook), 'sort reads a glued -o');
  // (2) assignment forms, since the third pass the bare identifier anywhere (bareExpandedNames)
  assert.ok(d47.includes('as an lvalue in any form the shells offer') && hook.includes('function bareExpandedNames(segments)'));
  // (3) in-command prefix mutations
  assert.ok(d47.includes('IN-COMMAND PREFIX MUTATIONS') && hook.includes('const recordMutations = (name, args, cwd) =>') && hook.includes('const mutated = ctx.mutated || [];'));
  // (4) stat errors refuse
  assert.ok(d47.includes('STAT ERRORS\n    REFUSE') || d47.includes('STAT ERRORS REFUSE'));
  assert.ok(hook.includes('class UnknownPath extends Error') && hook.includes('function statErrorRefusal(how, raw, e)') && hook.includes('function readConfigChecked(root)'));
  // (5) nested markers
  assert.ok(d47.includes('NESTED MARKERS') && hook.includes('function outerTrackingRoot(inner, file, closures)'));
  // (6) a cd the guard cannot know
  assert.ok(d47.includes('A cd THE GUARD CANNOT KNOW') && hook.includes('function commandOf(words)') && hook.includes('const cdFunctions = ctx.cdFunctions || new Set();'));
  assert.ok(d47.includes('`env -C DIR` resolves its operand\n    physically') || d47.includes('`env -C DIR` resolves its operand physically'));
  assert.ok(!/\u2014/.test(d47), 'no em dash in decision 47');
});

// The walk-around lens third pass (2026-09-19): decision 47 records the six rules re-keyed on what the guard can see,
// each tied to the hook function or table that implements it, and the hook header carries the audit of the lists that
// remain with the side each list's gap falls on; a rule dropped from the code, or a list added without its gap stated,
// fails here by name.
test('decision 47 records the walk-around lens third pass, each rule tied to its hook function, and the hook header audits the lists that remain', () => {
  assert.ok(d47.includes('The walk-around lens third pass (2026-09-19) re-keyed six rules on what the guard can see'));
  // (a) the bare identifier
  assert.ok(d47.includes('BARE IDENTIFIER') && hook.includes('function bareExpandedNames(segments)') && hook.includes("const EXPANDED_NAMES = ['HOME'];"));
  assert.ok(!hook.includes('function assignsHome(') && !hook.includes('HOME_DECLARERS'), 'the enumeration of assignment forms is gone');
  // (b) fully parsed or refused
  assert.ok(d47.includes('FULLY PARSED OR REFUSED') && hook.includes('const WRAPPER_OPT = {') && hook.includes('({ unknown: { option, wrapper: name, value, rest: words.slice(k + 1) } })'));
  assert.ok(hook.includes("refuse: { short: 'S', long: ['split-string'] }") && hook.includes("kind: 'opaqueScript'"), 'env -S is refused outright');
  assert.ok(hook.includes('for (const c of cmd.chdirs) {'), 'a nested chdir composes');
  assert.ok(!hook.includes('PREFIX_OPERANDS') && !hook.includes('PREFIX_LEAD_OPERANDS'), 'the operand lists are gone with the tables');
  // (c) the non-literal link source
  assert.ok(d47.includes('NON-LITERAL LINK SOURCE') && hook.includes("markMutated(dstAbs, 'ln -s')"));
  // (d) the shell-option allowlist
  assert.ok(d47.includes('SHELL OPTIONS, AN ALLOWLIST') && hook.includes('function shellOptionChange(name, args)') && hook.includes('const INERT_SET_LETTERS = ') && hook.includes('const INERT_SET_OPTIONS = new Set([') && hook.includes('const INERT_SHOPT = new Set(['));
  assert.ok(!hook.includes('physicalMode'), 'the physical-option enumeration is gone');
  // (e) any depth
  assert.ok(d47.includes('ANY DEPTH') && hook.includes('const PARENT_SCAN_BUDGET = ') && hook.includes('function parentTrackedRoots(dir, segPrefix, memo)'));
  // (f) the unknown option refuses everywhere
  assert.ok(d47.includes('UNKNOWN OPTION REFUSES EVERYWHERE') && hook.includes('function optionCandidates(args)') && hook.includes("if (parsed.unknown) { markAllCandidates('mv'); return; }"));
  // the corpus and the lists audit
  assert.ok(d47.includes('`tools/romp-track-bash-guard-corpus.json`') && fs.existsSync(path.join(REPO, 'tools', 'romp-track-bash-guard-corpus.json')));
  assert.ok(hook.includes('THE LISTS THAT REMAIN, each with the side its GAP falls on'), 'the hook header audits the lists');
  for (const list of ['PREFIXES', 'WRAPPER_OPT', 'COPY_OPT', 'INERT_SET_LETTERS', 'EXPANDED_NAMES', 'NUMERIC_EXPANSIONS', 'ANSI_C_SHELLS']) {
    assert.ok(new RegExp(`//   ${list}[^\\n]*: gap = `).test(hook), `the audit names ${list} with its gap side`);
  }
  assert.ok(!/\u2014/.test(d47), 'no em dash in decision 47');
});
