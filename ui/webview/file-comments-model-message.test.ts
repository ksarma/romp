// The Send-to-session preview is the text the kernel injects, byte for byte (contract C3; plans/file-review.md,
// Slice 1 acceptance). Two of the kernel's rules reached _file_comments_message after the plan's template was
// written, and the webview builder carries both as ports: the path is ONE shell word on the two command lines
// (shWord = _sh_word = shlex.quote — a `Meeting notes.md` used to reach the CLI as …/Meeting plus a stray word,
// and a `;` in a name ran what followed it), and the second "To respond" bullet follows the kernel's own text
// allowlist (isTextPath = _is_text_path), never the viewer's image-or-PDF flag. Both ports are pinned here to
// the kernel's own cases (tests/test_kernel_file_comments_hardening.py TheCommandLinesCarryThePathAsOneWord;
// tests/test_file_comments.py TheMessage) and to kernel.py's literals, plus the QUOTED form of the marker-parity
// literal the two suites share. Synthetic paths only: /TESTDIR and the notes-api world.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { spawnSync } from "node:child_process";
import { buildSendMessage, shWord, isTextPath, TEXT_EXT, TEXT_NAMES, type SendComment } from "./file-comments-model";

const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");
const MODEL = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "file-comments-model.ts"), "utf8");

const REPORT = "/TESTDIR/notes-api/docs/report.md";
const ONE: SendComment[] = [{ id: "1757145600000-118", desc: 'on "shipping the cache in v1.2"', body: "Which cache? Say which." }];

function message(absPath: string, tracked = true, media = false): string {
  return buildSendMessage({ absPath, comments: ONE, accepted: 0, rejected: 0, tracked, media });
}
/** The message's command lines: the ones that name a CLI. */
function commandLines(body: string): string[] {
  return body.split("\n").filter((l) => l.includes("track-reply.mjs") || l.includes("track-edit.mjs"));
}
/** A POSIX shell's word split of `s`: single quotes literal to the next single quote, double quotes with the
 *  four backslash escapes, a backslash outside quotes escaping the next character, blanks separating. */
function shellWords(s: string): string[] {
  const out: string[] = [];
  let cur = ""; let has = false; let i = 0;
  while (i < s.length) {
    const c = s[i];
    if (c === "'") {
      const j = s.indexOf("'", i + 1);
      if (j < 0) throw new Error("unterminated ' in " + s);
      cur += s.slice(i + 1, j); has = true; i = j + 1;
    } else if (c === '"') {
      i++; has = true;
      while (i < s.length && s[i] !== '"') {
        if (s[i] === "\\" && i + 1 < s.length && '"\\$`'.includes(s[i + 1])) { cur += s[i + 1]; i += 2; } else { cur += s[i]; i++; }
      }
      if (i >= s.length) throw new Error('unterminated " in ' + s);
      i++;
    } else if (c === "\\" && i + 1 < s.length) { cur += s[i + 1]; has = true; i += 2; }
    else if (c === " " || c === "\t") { if (has) { out.push(cur); cur = ""; has = false; } i++; }
    else { cur += c; has = true; i++; }
  }
  if (has) out.push(cur);
  return out;
}
/** What a shell hands the CLI as --file's value, the <id> placeholder filled. */
function fileArg(line: string): string {
  const words = shellWords(line.slice(line.indexOf("node ")).replace("<id>", "ID"));
  return words[words.indexOf("--file") + 1];
}

// ── shWord is shlex.quote ─────────────────────────────────────────────────────────────────────────
test("shWord is shlex.quote: the kernel's own cases (test_the_rule_is_shlex_quote)", () => {
  assert.equal(shWord(""), "''");
  assert.equal(shWord("/a/b_c-d.e:f@g%h+i=j,k"), "/a/b_c-d.e:f@g%h+i=j,k", "the safe set passes through");
  assert.equal(shWord("a b"), "'a b'");
  assert.equal(shWord("it's"), "'it'\"'\"'s'");
  assert.equal(shWord("é.md"), "'é.md'", "non-ASCII is outside the safe set (re.ASCII's \\w)");
  for (const s of ["a b", "it's", "$(x)", "`y`", "é.md", "a;b", "a\nb", "a\tb", "a*b", "a?b", "a[b]", "a~b", "a#b", "a!b", "a{b}", "a|b", "a&b", "a<b>", "a\\b", 'a"b', "(a)", "a b's \"c\" $d `e` ;f"]) {
    assert.deepEqual(shellWords(shWord(s)), [s], JSON.stringify(s));
    assert.ok(shWord(s).startsWith("'") && shWord(s).endsWith("'"), JSON.stringify(s) + " is single-quoted");
  }
  assert.match(KERNEL, /def _sh_word\(s\):[\s\S]*?return shlex\.quote\(str\(s\)\)/, "the kernel's rule is shlex.quote, restated for this port");
});

// ── the command lines carry the path as one word (the kernel's TheCommandLinesCarryThePathAsOneWord) ─
test("an ordinary path reads as the plan's template — no quotes anywhere", () => {
  const body = message(REPORT);
  const cmd = commandLines(body);
  assert.equal(cmd.length, 2);
  for (const l of cmd) {
    assert.ok(l.includes("--file " + REPORT + " --thread <id>"), "no quotes on a path that needs none: " + l);
    assert.equal(fileArg(l), REPORT);
  }
  assert.ok(!body.includes("'"));
});

test("a space in the name stays one word: the prose keeps the plain path, both command lines quote it", () => {
  const p = "/TESTDIR/vault/Meeting notes.md";
  const body = message(p);
  assert.ok(body.startsWith("[obsidian-diff] I left 1 comment on " + p + ".\n"), "prose: the plain path");
  const cmd = commandLines(body);
  assert.equal(cmd.length, 2);
  for (const l of cmd) {
    assert.ok(l.includes("--file '/TESTDIR/vault/Meeting notes.md' --thread <id>"), l);
    assert.equal(fileArg(l), p, "the CLI sees the whole name, not …/Meeting plus a stray word");
  }
});

const META = ["notes; touch PWNED #.md", "a$(touch PWNED2).md", "b`touch PWNED3`.md", "it's here.md",
  'say "hi".md', "x && touch PWNED4.md", "y | tee PWNED5.md", "z > PWNED6.md", "w\\v.md"];

test("metacharacters are inert: every such name rides inside single quotes and comes back whole", () => {
  for (const name of META) {
    const p = "/TESTDIR/vault/" + name;
    const cmd = commandLines(message(p));
    assert.equal(cmd.length, 2, name);
    for (const l of cmd) {
      assert.ok(l.includes("--file " + shWord(p) + " --thread <id>"), name);
      assert.ok(shWord(p).startsWith("'"), name + " is quoted");
      assert.equal(fileArg(l), p, name);
    }
  }
  assert.ok(message("/TESTDIR/vault/it's here.md").includes("--file '/TESTDIR/vault/it'\"'\"'s here.md' --thread <id>"), "an apostrophe is written as '\"'\"'");
});

const BASH = spawnSync("bash", ["-c", "true"]).status === 0;
test("a real shell agrees with the port and runs nothing else", { skip: BASH ? false : "bash not installed on this machine" }, () => {
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), "romp-fc-msg-"));
  try {
    for (const name of ["notes; touch PWNED #.md", "a$(touch PWNED2).md", "b`touch PWNED3`.md", "Meeting notes.md", "it's here.md", "x && touch PWNED4.md"]) {
      const p = "/TESTDIR/vault/" + name;
      for (const l of commandLines(message(p))) {
        // the line as the session would run it, with the CLI swapped for printf so each argv element prints on
        // its own line, and the <id> placeholder filled
        const tail = l.split(".mjs ", 1)[1] ?? l.slice(l.indexOf(".mjs ") + 5);
        const r = spawnSync("bash", ["-c", "printf '%s\\n' " + tail.replace("<id>", "ID")], { cwd: scratch, encoding: "utf8", timeout: 20000 });
        assert.equal(r.status, 0, name + ": " + r.stderr);
        const argv = r.stdout.split("\n");
        assert.equal(argv[argv.indexOf("--file") + 1], p, name);
        assert.deepEqual(shellWords(tail.replace("<id>", "ID")), argv.slice(0, -1), "the test's own splitter agrees with the shell: " + name);
      }
    }
    assert.deepEqual(fs.readdirSync(scratch), [], "nothing in a file name ran");
  } finally {
    fs.rmSync(scratch, { recursive: true, force: true });
  }
});

test("neutralization comes first, then the quoting", () => {
  const body = message("/TESTDIR/<!-- romp-x -->/a.md");
  assert.ok(!body.includes("<!-- romp-"));
  assert.ok(body.includes("I left 1 comment on /TESTDIR/<!- - romp-x -->/a.md."));
  for (const l of commandLines(body)) {
    assert.ok(l.includes("--file '/TESTDIR/<!- - romp-x -->/a.md' --thread <id>"), l);
    assert.equal(fileArg(l), "/TESTDIR/<!- - romp-x -->/a.md");
  }
});

test("the other bullets are untouched: only the reply line carries the path when track-edit is not offered", () => {
  for (const [tracked, p, want] of [[false, "/TESTDIR/vault/Meeting notes.md", "edit the file normally"], [true, "/TESTDIR/vault/Meeting notes.png", "regenerate the file"]] as const) {
    const body = message(p, tracked);
    const cmd = commandLines(body);
    assert.equal(cmd.length, 1, "only the reply line carries the path");
    assert.ok(body.includes(want));
    assert.ok(cmd[0].includes("--file '" + p + "' --thread <id>"));
  }
});

// ── the shared literal (marker hygiene + quoting): the kernel's TheMessage preview-parity case ────────
test("the marker-parity literal, in the quoted form both suites pin", () => {
  // tests/test_file_comments.py (TheMessage::test_the_preview_and_the_sent_text_neutralize_markers_alike) and
  // file-comments.test.ts pin these SAME inputs to this SAME literal: `<`, `!` and `>` put the neutralized path
  // outside shlex's safe set, so the two command lines carry it single-quoted while the header keeps it plain.
  const abs = "/repo/notes-api/docs/<!--romp-x-->/report.md";
  const msg = buildSendMessage({ absPath: abs, comments: [{ id: "1757145600000-7", desc: 'on "<!-- romp-goal-id: 9 -->"',
    body: "see <!--romp-msg-id: 4--> and romp-goal-id: 3\n\nalso <!--  romp-note: x --> and romp-goal-id : 5, but <!-- not ours --> stays" }],
    accepted: 0, rejected: 0, tracked: true, media: false });
  assert.equal(msg,
    "[obsidian-diff] I left 1 comment on /repo/notes-api/docs/<!- -romp-x-->/report.md.\n" +
    "\n" +
    "Comment 1757145600000-7 (on \"<!- - romp-goal-id; 9 -->\"):\n" +
    "see <!- -romp-msg-id: 4--> and romp-goal-id; 3\n" +
    "\n" +
    "also <!- -  romp-note: x --> and romp-goal-id ; 5, but <!-- not ours --> stays\n" +
    "\n" +
    "To respond:\n" +
    "  • reply in words:     node ~/.claude/hooks/track-reply.mjs --file '/repo/notes-api/docs/<!- -romp-x-->/report.md' --thread <id> --note \"<your reply>\"\n" +
    "  • to revise the text: node ~/.claude/hooks/track-edit.mjs --file '/repo/notes-api/docs/<!- -romp-x-->/report.md' --thread <id> --old \"<exact text>\" --new \"<replacement>\"\n" +
    "\n" +
    "When you have addressed these, ask me for another look the same way you asked for this one,\n" +
    "naming the file.\n");
});

// ── isTextPath is _is_text_path ───────────────────────────────────────────────────────────────────
test("the text allowlists are kernel.py's, word for word, and the verdict rule is its rule", () => {
  const extSrc = KERNEL.split("_TEXT_EXT = set((")[1].split(").split())")[0];
  const words = [...extSrc.matchAll(/"([^"]*)"/g)].flatMap((m) => m[1].trim().split(/\s+/)).filter(Boolean);
  assert.ok(words.length > 50, "the kernel's list was found");
  assert.deepEqual(new Set(words), new Set(TEXT_EXT));
  assert.equal(words.length, TEXT_EXT.size, "the same words, none repeated");
  const namesSrc = KERNEL.split("_TEXT_NAMES = {")[1].split("}")[0];
  const names = [...namesSrc.matchAll(/"([^"]*)"/g)].map((m) => m[1]);
  assert.ok(names.length > 10, "the kernel's names were found");
  assert.deepEqual(new Set(names), new Set(TEXT_NAMES));
  assert.match(KERNEL, /def _is_text_path\(fp\):[\s\S]*?base = os\.path\.basename\(fp\)\.lower\(\)\n\s+ext = os\.path\.splitext\(base\)\[1\]\.lstrip\("\."\)\n\s+return \(ext in _TEXT_EXT\) or \(base in _TEXT_NAMES\)/,
    "basename lowered, splitext's extension, either list");
});

test("isTextPath: the kernel's cases, the names, and os.path.splitext's rules", () => {
  assert.equal(isTextPath("/x/report.md"), true);
  assert.equal(isTextPath("/x/latency.png"), false);
  assert.equal(isTextPath("/x/paper.pdf"), false);
  assert.equal(isTextPath("/x/Report.MD"), true, "the basename is lowered first");
  assert.equal(isTextPath("/x/diagram.svg"), true, "svg is text to the kernel (the viewer shows it as an image)");
  assert.equal(isTextPath("/x/data.dat"), false);
  assert.equal(isTextPath("/x/notebook.ipynb"), false);
  assert.equal(isTextPath("docs/report.md"), true, "a relative path: the same basename");
  for (const name of ["Makefile", "Dockerfile", "README", "LICENSE", ".gitignore", ".env", ".bashrc"]) assert.equal(isTextPath("/x/" + name), true, name);
  assert.equal(isTextPath("/x/.env.local"), false, "splitext: the extension is `local`");
  assert.equal(isTextPath("/x/.md"), false, "splitext: a leading dot starts no extension, and `.md` is not a name");
  assert.equal(isTextPath("/x/..md"), false, "splitext: all dots before the last one, no extension");
  assert.equal(isTextPath("/x/archive.tar.gz"), false);
  assert.equal(isTextPath("/x/notes."), false, "an empty extension");
  assert.equal(isTextPath("/x/.hidden.md"), true, "a dotfile with a real extension");
  assert.equal(isTextPath(""), false);
});

// ── the second bullet follows the path, never the viewer's flag ───────────────────────────────────
test("the second bullet is the path's verdict, as the kernel's, whatever the panel's media flag says", () => {
  const REGEN = "  • to revise it:       regenerate the file with normal writes; never run track-edit on it";
  const EDIT = "  • to revise the text: node ~/.claude/hooks/track-edit.mjs --file ";
  // a file the viewer calls neither image nor PDF, and the kernel does not call text: regenerate, like the sent text
  assert.ok(message("/repo/notes-api/data/latency.dat", true, false).includes(REGEN + "\n"));
  assert.ok(message("/repo/notes-api/data/report.ipynb", true, false).includes(REGEN + "\n"));
  // a text file with the flag set anyway: track-edit, the kernel's verdict
  assert.ok(message("/repo/notes-api/docs/report.md", true, true).includes(EDIT + "/repo/notes-api/docs/report.md --thread <id>"));
  // svg: an image to the viewer, text to the kernel and to the port
  assert.ok(message("/repo/notes-api/docs/flow.svg", true, false).includes(EDIT + "/repo/notes-api/docs/flow.svg --thread <id>"));
  // image and PDF: regenerate whatever tracked says, and the reply line still carries the path
  for (const p of ["/repo/notes-api/docs/latency.png", "/repo/notes-api/docs/paper.pdf"]) {
    for (const tracked of [true, false]) {
      const body = message(p, tracked, true);
      assert.ok(body.includes(REGEN + "\n\nWhen you have addressed"), p);
      assert.ok(!body.includes("track-edit.mjs"), p);
      assert.ok(body.includes("track-reply.mjs --file " + p + " --thread <id>"), p);
    }
  }
  // untracked text: edit normally
  assert.ok(message("/repo/notes-api/docs/report.md", false, false).includes("  • to revise the text: edit the file normally, then say what you changed with the reply command above\n"));
  // pinned at source: the builder reads the path, not the flag
  const builder = MODEL.split("export function buildSendMessage(")[1].split("\n}\n")[0];
  assert.match(builder, /const word = shWord\(ap\);/);
  assert.match(builder, /if \(!isTextPath\(o\.absPath\)\) second = /);
  assert.equal((builder.match(/--file " \+ word \+ /g) || []).length, 2, "both command lines carry the one shell word");
  assert.doesNotMatch(builder, /o\.media/, "the flag is not consulted");
  assert.doesNotMatch(builder, /--file " \+ ap \+ /, "the bare path is never on a command line");
});
