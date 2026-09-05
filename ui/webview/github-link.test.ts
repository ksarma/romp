// The viewer's GitHub link (the user 2026-08-15): a lazy fileGitLink ask per open, answered by the
// file-OWNING kernel (git on ITS disk is the authority). The anchor shows on EVERY answer (the user
// 2026-09-05): a real URL links, no URL renders it disabled with the kernel's reason as tooltip, and
// a URL whose branch is not on origin links with the note. Source pins (no jsdom for these modules),
// the repo convention.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const VIEW = web("file-view.ts");
const RENDER = web("render.ts");
const CHAT_CSS = web("styles.css");
const FEED_CSS = web("feed.css");
const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");

test("the ask is lazy, per open, and sid-routed — never on the /file byte path", () => {
  assert.match(VIEW, /post\(\{ type: "fileGitLink", path, sid: sid \|\| undefined, reqId: gitSeq \}\);/);
  // thumbnails must not pay three git subprocesses each: /file itself is untouched
  assert.doesNotMatch(KERNEL, /_file_github_url\(fp/);
});

test("the poster is bound at the boot of the document that hosts the viewer", () => {
  assert.match(RENDER, /initFileView\(\(m\) => vscodeApi\?\.postMessage\(m\)\);/);
});

test("state 1 — a real URL: the anchor links, opens a new tab, and shows where it goes", () => {
  assert.match(VIEW, /const gh = el\("a", "fileview-btn fileview-gh"\) as HTMLAnchorElement;/);
  assert.match(VIEW, /gh\.target = "_blank"; gh\.rel = "noopener";/);
  assert.match(VIEW, /gh\.hidden = true;/, "hidden until the kernel answers — never an hrefless flash");
  assert.match(VIEW, /if \(url\) \{\n\s+gh\.href = url;\n\s+gh\.title = reason \? url \+ "\\n" \+ reason : url;/,
    "the full URL one hover away");
  // both sheets: the FEED hosts the same viewer (the file browser), so its anchor dresses the same
  assert.match(CHAT_CSS, /a\.fileview-btn \{ text-decoration: none;/);
  assert.match(FEED_CSS, /a\.fileview-btn \{ text-decoration: none;/);
});

test("state 2 — no URL: the anchor is DISABLED with the reason as its tooltip, never hidden", () => {
  // the user 2026-09-05 could not tell "not committed yet" from "the feature is broken" when the
  // button was simply absent; the repo rule is fail loudly, never degrade silently
  assert.doesNotMatch(VIEW, /if \(!url\) return;/, "an empty url no longer means an absent button");
  assert.match(VIEW, /gh\.setAttribute\("aria-disabled", "true"\);/);
  assert.match(VIEW, /gh\.tabIndex = 0;/, "reachable by keyboard, so the reason is too");
  assert.match(VIEW, /gh\.title = "No GitHub link: " \+ \(reason \|\| "no reason was given"\);/,
    "the kernel's phrase verbatim; an older kernel's reasonless reply is said, not invented");
  assert.match(VIEW, /gh\.setAttribute\("aria-label", gh\.title\);/);
  // the un-hide is unconditional — it follows BOTH branches
  assert.match(VIEW, /\}\n\s+gh\.hidden = false;\n\s+\},\n\s+\};/);
  // no href means nothing to follow; the sheets grey it and keep the accent hover off it
  for (const css of [CHAT_CSS, FEED_CSS]) {
    assert.match(css, /a\.fileview-btn\[aria-disabled="true"\] \{ opacity: 0\.55; cursor: default; \}/);
    assert.match(css, /a\.fileview-btn\[aria-disabled="true"\]:hover \{ border-color: var\(--card-border\); color: var\(--fg\); background: transparent; \}/);
    assert.match(css, /a\.fileview-btn\[aria-disabled="true"\]:active \{ transform: none; \}/);
  }
});

test("state 3 — a URL whose branch is not on origin: still a link, with the note in the tooltip", () => {
  assert.match(VIEW, /if \(reason\) \{ gh\.classList\.add\("fileview-gh-note"\); gh\.setAttribute\("aria-label", "GitHub: " \+ reason\); \}/);
  for (const css of [CHAT_CSS, FEED_CSS]) assert.match(css, /a\.fileview-gh-note \{ border-style: dashed; \}/);
});

test("the reply's reason travels with its url into the hooks", () => {
  assert.match(VIEW, /h\.apply\(String\(m\.url \|\| ""\), String\(m\.reason \|\| ""\)\);/);
});

test("replies are reqId-guarded and cannot touch a later open", () => {
  assert.match(VIEW, /m\.type === "fileGitLink" && gitHooks && m\.reqId === gitHooks\.reqId/);
  // both the close and the replace path drop the hooks, so a late reply lands nowhere
  const closes = VIEW.match(/gitHooks = null;/g) || [];
  assert.ok(closes.length >= 2, "cleared on close AND on replace-open");
});

test("the kernel's answer is a verdict from git itself, threaded off the recv loop", () => {
  assert.match(KERNEL, /def _file_github_url\(raw, sid\):/);
  assert.match(KERNEL, /def _file_github_link\(raw, sid, check_origin=True\):/, "the (url, reason) sibling the op uses");
  assert.match(KERNEL, /"url": url, "reason": reason\}\)/, "the reason rides the reply");
  // the fixed set of plain phrases the disabled button shows verbatim
  assert.match(KERNEL, /GH_NO_REPO = "not in a git repository"/);
  assert.match(KERNEL, /GH_UNTRACKED = "not committed \(untracked file\)"/);
  assert.match(KERNEL, /GH_NOT_GITHUB = "the origin remote is not on GitHub"/);
  assert.match(KERNEL, /GH_NOT_ON_ORIGIN = "branch %s is not on origin"/);
  // the local tracking ref answers first; ls-remote is the fallback, short-timed, never a prompt
  assert.match(KERNEL, /"refs\/remotes\/origin\/" \+ ref/);
  assert.match(KERNEL, /"ls-remote", "--heads", "origin", full\], top, timeout=GH_LS_REMOTE_S/);
  assert.match(KERNEL, /GIT_TERMINAL_PROMPT="0"/);
  assert.match(KERNEL, /elif msg and msg\.get\("type"\) == "fileGitLink":/);
  assert.match(KERNEL, /threading\.Thread\(target=_gl, daemon=True\)\.start\(\)/);
  // the spellings git actually writes for a GitHub origin — incl. ports and ssh.github.com
  assert.match(KERNEL, /ssh:\/\/git@\(\?:ssh\\\.\)\?github\\\.com\(\?::\\d\+\)\?/);
  assert.match(KERNEL, /ls-files", "--error-unmatch"/, "tracked files only — no link to a thing not there");
  // realpath, not normpath: a lexical '..' collapse linked a DIFFERENT file than the viewer shows
  assert.match(KERNEL, /p = os\.path\.realpath\(p\)\n    d = os\.path\.dirname\(p\)/);
});

test("the hidden anchor stays hidden — an author display must not beat [hidden]", () => {
  assert.match(CHAT_CSS, /a\.fileview-btn\[hidden\] \{ display: none; \}/);
  assert.match(FEED_CSS, /a\.fileview-btn\[hidden\] \{ display: none; \}/);
});

test("the GitHub link is the action REGISTRY's first entry, not another hand-wired button", () => {
  // the registry (the user 2026-08-22): internal seam, no compatibility promise — actions on the
  // open file declare a mount() instead of editing openFileView, so viewer PRs stop colliding there
  assert.match(VIEW, /export function registerFileViewAction\(a: FileViewAction\): void \{/);
  assert.match(VIEW, /if \(!fileViewActions\.some\(\(x\) => x\.id === a\.id\)\) fileViewActions\.push\(a\);/, "same id registered twice mounts once");
  assert.match(VIEW, /registerFileViewAction\(\{\n  id: "github-link",/);
  // openFileView renders registered actions by WALKING THE TABLE, after the built-ins
  assert.match(VIEW, /for \(const a of fileViewActions\) \{\n    const n = a\.mount\(\{ path, sid: sid \|\| null \}\);\n    if \(n\) acts\.appendChild\(n\);\n  \}/);
});
