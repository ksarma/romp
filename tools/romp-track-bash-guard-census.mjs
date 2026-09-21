// The census of the lists that remain in hooks/romp-track-bash-guard.mjs, DERIVED from its source (round 5 of the review of
// fork PR #780, 2026-09-20). The hook's header used to carry a hand-written census of its hand-maintained lists, each with
// the side its gap falls on; round 4 found it omitted the two lists whose gap falls on the write side (the compound-head
// frame push and CLOSERS), the very lists a missing `select` had slipped through, so the instrument built to bound the
// lists was itself a list with a gap on the dangerous side. This module enumerates the lists by reading the module's text
// and classifies each against the line that consumes it; tools/romp-track-bash-guard.test.mjs runs it and reds when a
// list exists that the census does not name, when a named list is gone, when a side is not one of the three, or when the
// consumer line a side rests on is no longer in the source.
//
// THE METHOD. No parser is vendored (acorn is not in this tree), so the enumeration is a disciplined regex over the
// module's top-level declarations: a line at column 0 of the form `const NAME = <init>`, `let NAME = <init>`, `var NAME =
// <init>` or `export const NAME = <init>`, any spacing after the keyword and around the `=` (a second space after `const` was
// not read until round 5's second addendum, 2026-09-20, and was not among the blind spots below), the initializer on the same line or on the next when
// the line ends at the `=`, whose initializer opens a Set (`new Set(`), an array (`[`), an object table (`{`), an
// `Object.fromEntries(` or a `new RegExp(` (the interpreter write functions live in regex alternations). Two pseudo-lists
// are read from inside extract: the writer cases (the `case '...'` labels of `switch (name) {` up to that switch's own
// `default:`, at its indentation) and the root markers (the array markerAt iterates). THE BLIND SPOTS, stated (round 5's
// addendum, 2026-09-20: the census lens planted fourteen list shapes in scratch copies of the hook, each live on the write
// side, and twelve landed green; three of those are read since, `var`, the split declaration and the spacing drift, and the
// rest are named here): a list declared inside a function or a block (indented; the read and mapfile option letters in
// assembledNameOperand, the cd option pattern, sedTargets's and perlTargets's option handling, shellScript's option
// letters), a regex literal or a string holding an alternation (RESOLVED_NAME, ARITH_ASSIGNED_EXPANSION, PY_ARG, the
// interpreter-name test), a `let` filled in later, a list built by a call (`Object.keys(...)`, `Object.freeze(...)`, a
// spread copy) whose initializer does not open with one of the five forms, an inline literal at its point of use
// (`['a', 'b'].includes(x)`, a list with no name), a second declarator on one line (`const A = 1, B = new Set(...)`), a
// second `switch` over a word (only `switch (name) {` in extract is read), and Maps and WeakMaps, which this file excludes
// on purpose (they are caches, not hand-maintained lists). A list added to the hook in any of those shapes is not
// enumerated here, so the hook header's sentence that a planted list reds the test holds for the shapes this file reads
// and for no other; the enumeration is pinned against a synthetic source in the test so the shapes it DOES read stay read.
//
// THE SIDES. A list's gap is the element nobody added. WRITE: a missing element makes the guard read a write as plain
// sequence, as no write, or as a construct it need not follow, so the shell writes a tracked file the guard allowed.
// REFUSE: a missing element makes the guard refuse (a false refusal, recoverable in one step). NONE: a text table whose
// gap changes no verdict. Each side rests on a consumer line quoted here as `consumer`, which must appear in the source:
// the classification is tied to the code that decides it, and a consumer rewritten without this table reds the test.
// The side of a NEW entry is the author's to state (the census cannot derive it from the consumer), and the census reads
// lists, never their elements: a missing element of a named list is what the side describes, not what the test catches.
export const CENSUS = {
  WRITE_REDIRECTS: { side: 'WRITE', consumer: 'if (WRITE_REDIRECTS.has(r.op)) add(r.target,', why: 'an operator not listed is read as no write' },
  STDIN_NAMES: { side: 'WRITE', consumer: '(operand.literal && isStdinName(operand.text))) return done({ stdin: true });', why: 'a script operand naming the standard input that is not listed is read as a script file whose contents are not in the command, so the piped or here-document script passes unread (round 5\'s fifth addendum, third fix-up: `bash /dev/stdin` and `bash /dev/fd/0` ran the piped copy in bash, zsh and dash); since round 6\'s third commit the consumer reads the set through isStdinName, which adds every numbered descriptor (`/dev/fd/N`, `/proc/self/fd/N`) by pattern, so a spelling of the standard input outside both is the gap' },
  SHELLS: { side: 'WRITE', consumer: 'if (SHELLS.has(name)) {', why: 'a shell not listed is a command like any other and the script it runs is not read (measured: `ksh93 -c \'cp base/report.md docs/report.md\'` is allowed), the contract\'s unmodelled writer' },
  ZSH_MODIFIERS: { side: 'WRITE', consumer: "'chrt', 'numactl', ...ZSH_MODIFIERS]);", why: 'a modifier not listed is read as a command named so and hides the writer behind it (F1)' },
  PREFIXES: { side: 'WRITE', consumer: 'if (!PREFIXES.has(name)) return { name, args: words.slice(k + 1), chdirs, writes, wrapped, wrappers };', why: 'an unlisted wrapper is read as its own command, an unmodelled writer by the contract, so the set is stated on the four surfaces and the unlisted wrappers the passes found are on the contract\'s list' },
  RESERVED: { side: 'WRITE', consumer: 'while (k < words.length && plainWord(words[k]) && RESERVED.has(words[k].text)) k++;', why: 'a reserved word not listed at a segment\'s head is read as the command name and hides the command after it (unquoted since round 5\'s fourth addendum: a quoted one IS the command)' },
  FRAME_PEEL: { side: 'WRITE', consumer: 'if (plainWord(w) && ((FRAME_PEEL.has(w.text)', why: 'a word the shell reads past that is not peeled hides the compound head, so no frame opens and a body that may not run is read as plain sequence (round 4\'s defect)' },
  TIME_OPTIONS: { side: 'WRITE', consumer: 'if (plainWord(w) && afterTime && TIME_OPTIONS.has(w.text))', why: 'a `time` option not listed stops the peel before the head' },
  BODY_CLOSER: { side: 'WRITE', consumer: 'else if (head != null && Object.hasOwn(BODY_CLOSER, head)) {', why: 'a compound head not listed opens no frame: the body\'s names stay readable and its cd is followed (the round-4 highs; round 5\'s addendum added zsh\'s repeat and foreach, and each entry\'s opener and list flag, read by compoundBody: an opener wrong for its head would make a `{` in the body a brace body, closing the frame at the next `}`, a WRITE too)' },
  CLOSERS: { side: 'WRITE', consumer: 'if (head != null && Object.hasOwn(CLOSERS, head)) closeCompound(CLOSERS[head]);', why: 'derived from BODY_CLOSER, so a closer is missing only when its head is, the same gap; a closer edited out by hand would leave the frame open to the end of the command, a refusal' },
  COMPOUND_HEADS: { side: 'WRITE', consumer: 'COMPOUND_HEADS.has(compoundHeadOf(seg.words))) opened = true;', why: 'derived from BODY_CLOSER; readableHomeWrites stops reading a plain HOME= after a compound (the conservative side), so the derived set carries the table\'s gap' },
  ANSI_C_SHELLS: { side: 'REFUSE', consumer: 'const ansiCQuoting = shell == null || ANSI_C_SHELLS.has(shell);', why: 'a shell not listed gets the restricted reading of $\'...\', a word the hook cannot read' },
  TEST_ARITH_SHELLS: { side: 'REFUSE', consumer: "const testGrammar = shell == null || shell === 'sh' || TEST_ARITH_SHELLS.has(shell);", why: 'a shell not listed takes the dash reading alone: `[[` a command whose `>` is a redirection, `((` two `(` running the body, each judged as a write (round 5\'s fifth addendum); a shell listed that lacks the words would be a wrong entry, not a gap' },
  CONSTRUCT_HEADS: { side: 'WRITE', consumer: "seg.redirects.push({ op: r.op, target: r.target, how: `${r.op} redirection${CONSTRUCT_HEADS['[['].via}` });", why: 'the constructs read in both grammars (round 5\'s fifth addendum): a construct bash and zsh read as non-redirecting that the table does not carry is read under their grammar alone, the fourth addendum\'s finding; the lexer reads the heads at their characters and takes each reading\'s text from here, and the matrix generator derives its head population from the command-position entries and the key-set pin beside it lists both kinds from the fixture, so a head added here without a matrix kind reds a pin: a command-position head changes the fixture\'s row count, an `expansion: true` head the key set (round 6\'s second commit, ruling F: before, an expansion head landed with nothing red)' },
  NUMERIC_EXPANSIONS: { side: 'REFUSE', consumer: 'if (!NUMERIC_EXPANSIONS.includes(text.slice(i, j))) return false;', why: 'an expansion not listed is unreadable' },
  POSIX_CLASSES: { side: 'REFUSE', consumer: 'if (m && POSIX_CLASSES[m[1]]) { cls += POSIX_CLASSES[m[1]];', why: 'a class not listed is read as literal bracket text, so the pattern matches other names or none, and a glob with no match is a word the hook cannot read; bash and zsh themselves match nothing for an unknown class' },
  WRAPPER_OPT: { side: 'REFUSE', consumer: 'const spec = WRAPPER_OPT[name];', why: 'an option not in a wrapper\'s table refuses naming it (rule (b))' },
  COPY_OPT: { side: 'REFUSE', consumer: 'const spec = COPY_OPT[verb];', why: 'an option not in a writer\'s table refuses, on every path (rule (f))' },
  INERT_SET_LETTERS_WHY: { side: 'REFUSE', consumer: 'if (!INERT_SET_LETTERS.includes(ch)) return reason(t);', why: 'a letter not listed makes the directory unknown (rule (d)); THE CRITERION at the table decides each entry' },
  INERT_SET_OPTIONS_WHY: { side: 'REFUSE', consumer: 'if (!inertOption(t, INERT_SET_OPTIONS)) return reason(w.raw);', why: 'a `set -o` option not listed makes the directory unknown' },
  INERT_SHOPT_WHY: { side: 'REFUSE', consumer: 'inertOption(w.text, setO ? INERT_SET_OPTIONS : INERT_SHOPT)', why: 'a shopt option not listed makes the directory unknown' },
  INERT_SET_OPTIONS: { side: 'REFUSE', consumer: 'const INERT_SET_OPTIONS = new Set([...Object.keys(INERT_SET_OPTIONS_WHY)]);', why: 'the key set of INERT_SET_OPTIONS_WHY, derived' },
  INERT_SHOPT: { side: 'REFUSE', consumer: 'const INERT_SHOPT = new Set([...Object.keys(INERT_SHOPT_WHY)]);', why: 'the key set of INERT_SHOPT_WHY, derived' },
  INERT_OPTIONS: { side: 'NONE', consumer: 'export const INERT_OPTIONS = { letters: INERT_SET_LETTERS_WHY, set: INERT_SET_OPTIONS_WHY, shopt: INERT_SHOPT_WHY };', why: 'a read-only view of the three tables for the tests; nothing in the hook consumes it' },
  INTERPRETER_OPERANDS: { side: 'WRITE', consumer: 'if (INTERPRETER_OPERANDS[kind].has(a.text)) { k++; continue; }', why: 'an option not listed that takes a value makes the guard read the value as the script file and stop scanning, while the interpreter goes on to its -e or -c code (measured 2026-09-20: `node --inspect-port 9229 -e "...writeFileSync(\'docs/report.md\',...)"` is allowed and node writes the file); the hand-written census called this an over-count on the refuse side, which it is not; disclosed in round 5\'s body, unfixed there' },
  EXPANDED_NAMES: { side: 'WRITE', consumer: 'const valueOf = (name) => {', why: 'a name valueOf substitutes that the list lacks is read while the command may reassign it (B2\'s first draft, PWD)' },
  NAME_OPERAND_COMMANDS: { side: 'WRITE', consumer: "|| !NAME_OPERAND_COMMANDS.has(cmd.name)) continue;", why: 'a reader or declaration not listed whose name operand the shell fills in poisons nothing, so a reassigned HOME, PWD or OLDPWD is read (M1)' },
  VAR_ASSIGNERS: { side: 'REFUSE', consumer: "if (cmd && (VAR_ASSIGNERS.has(cmd.name) || cmd.name === 'local')) {", why: 'an unlisted declaration command\'s NAME=VALUE operand is read by taintWord\'s lvalue shape and taints the name (zsh\'s `integer x=5`, the rule pin)' },
  VAR_POISONERS: { side: 'WRITE', consumer: 'if (cmd && (VAR_POISONERS.has(cmd.name) ||', why: 'a command not listed that runs text as shell (trap, a sourced file by another name) poisons nothing, so a name it may have written stays readable; the contract\'s scripts-read-from-elsewhere clause' },
  ATTRIBUTE_ONLY_FLAGS: { side: 'NONE', consumer: '![...w.text.slice(1)].every((c) => ATTRIBUTE_ONLY_FLAGS.has(c))', why: 'since round 5\'s addendum no declaration flag keeps the name readable (bash rejects -r, -x and -g on export and readonly; declare and typeset are no commands of dash), so the table picks the refusal\'s text alone: a letter not listed names the flag, a listed one the shells\' disagreement, and either taints the name' },
  WRAPPED_CD_WHY: { side: 'NONE', consumer: 'block = WRAPPED_CD_WHY[w]', why: 'a text table: a wrapper not listed gets the external-cd text and the same unknown-directory verdict' },
  PY_OPEN: { side: 'WRITE', consumer: 'for (const m of t.matchAll(PY_OPEN)) {', why: 'a python write call not in the alternation is out of model (the contract\'s interpreter clause)' },
  PY_PATH_OPEN: { side: 'WRITE', consumer: 'for (const m of t.matchAll(PY_PATH_OPEN)) {', why: 'as PY_OPEN' },
  PY_PATH_WRITE: { side: 'WRITE', consumer: 'for (const m of t.matchAll(PY_PATH_WRITE)) take(', why: 'as PY_OPEN' },
  PY_SHUTIL: { side: 'WRITE', consumer: 'for (const m of t.matchAll(PY_SHUTIL)) {', why: 'as PY_OPEN' },
  NODE_WRITE: { side: 'WRITE', consumer: 'for (const m of t.matchAll(NODE_WRITE)) take(', why: 'a node write function not in the alternation is out of model' },
  NODE_OPEN: { side: 'WRITE', consumer: 'for (const m of t.matchAll(NODE_OPEN)) if (', why: 'as NODE_WRITE' },
  NODE_COPY: { side: 'WRITE', consumer: 'for (const m of t.matchAll(NODE_COPY)) take(', why: 'as NODE_WRITE' },
  WRITER_CASES: { side: 'WRITE', consumer: 'switch (name) {', why: 'the writer cases of extract\'s switch: a writer not listed falls to `default`, the contract\'s allow-by-default for an unmodelled writer, stated on the four surfaces with the list of the ones the passes found' },
  ESCAPE_READERS: { side: 'WRITE', consumer: 'const r = ESCAPE_READERS[reader];', why: 'a reader missing an escape a shell interprets (an octal form, a hex digit count, `\\u` in dash) yields a text the union lacks, so a script the shell runs under that text is read under another (round 5\'s regression-2: the bare octal dash\'s echo reads); the readers are pinned by execution over the escape grammar, and a reading reaches a target only when plain (THE RESOLVER\'S CONTRACT)' },
  ECHO_SHELLS: { side: 'WRITE', consumer: "const spelled = ECHO_SHELLS.map((sh) => echoOperands(words, sh).join(' '));", why: 'a shell missing from the union has no reading of its echo, so a text it alone prints is not read as a script' },
  PRINTF_SHELLS: { side: 'WRITE', consumer: 'for (const sh of PRINTF_SHELLS) {', why: 'a shell missing from the union has no reading of its printf, so a text it alone prints is not read as a script' },
  SILENT_COMMANDS: { side: 'REFUSE', consumer: 'if (SILENT_COMMANDS.has(cmd.name) && !cmd.wrapped) continue;', why: 'a command that prints nothing on the stream and is not listed puts a list beside an echo or a printf outside THE OUTPUT MODEL, UNRESOLVABLE (a false refusal of the piped or substituted script; round 6\'s second commit)' },
  ROOT_MARKERS: { side: 'WRITE', consumer: "for (const m of ['.obsidian', '.git', '.trackchanges'])", why: 'markerAt mirrors store-io\'s root markers; a marker store-io adds and this list lacks would make family 5 miss a nested root, a WRITE only if store-io adds one' },
};
export const SIDES = new Set(['WRITE', 'REFUSE', 'NONE']);

// The enumeration: [{ name, line, init }] for every top-level declaration the method reads, plus the two pseudo-lists.
const DECL = /^(?:export )?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(new Set\(|\[|\{|Object\.fromEntries\(|new RegExp\()/;   // `\s+` after the keyword: `const  NAME =` was not enumerated (round 5's second addendum)
const DECL_SPLIT = /^(?:export )?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*$/;   // the initializer on the next line
const INIT = /^\s*(new Set\(|\[|\{|Object\.fromEntries\(|new RegExp\()/;
export function enumerateLists(source) {
  const out = [];
  const lines = source.split('\n');
  lines.forEach((l, i) => {
    const m = l.match(DECL);
    if (m) { out.push({ name: m[1], line: i + 1, init: m[2] }); return; }
    const split = l.match(DECL_SPLIT);
    const next = split && i + 1 < lines.length ? lines[i + 1].match(INIT) : null;
    if (split && next) out.push({ name: split[1], line: i + 1, init: next[1] });
  });
  const sw = source.indexOf('    switch (name) {');
  const defAt = sw >= 0 ? source.slice(sw).search(/\n {6}default:/) : -1;   // that switch's own default, at its indentation, not a deeper one inside a case
  const def = defAt >= 0 ? sw + defAt : -1;
  if (sw >= 0 && def > sw) {
    const cases = [...source.slice(sw, def).matchAll(/case '([^']+)':/g)].map((m) => m[1]);
    out.push({ name: 'WRITER_CASES', line: source.slice(0, sw).split('\n').length, init: 'switch', items: cases });
  }
  const mk = source.match(/function markerAt\(root\) \{\n\s*for \(const m of \[([^\]]*)\]\)/);
  if (mk) out.push({ name: 'ROOT_MARKERS', line: source.slice(0, mk.index).split('\n').length, init: 'markerAt', items: mk[1].split(',').map((s) => s.trim().replace(/^'|'$/g, '')) });
  return out;
}

// The census over a source: the lists, and what is wrong (each array empty when the census holds).
export function census(source) {
  const lists = enumerateLists(source);
  const names = new Set(lists.map((l) => l.name));
  const unnamed = lists.filter((l) => !Object.hasOwn(CENSUS, l.name)).map((l) => `${l.name} (line ${l.line})`);
  const stale = Object.keys(CENSUS).filter((n) => !names.has(n));
  const unclassified = Object.entries(CENSUS).filter(([, c]) => !SIDES.has(c.side) || !c.why).map(([n]) => n);
  const missingConsumer = Object.entries(CENSUS).filter(([, c]) => !c.consumer || !source.includes(c.consumer)).map(([n]) => n);
  return { lists, unnamed, stale, unclassified, missingConsumer };
}
