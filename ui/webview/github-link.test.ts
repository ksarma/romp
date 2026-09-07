// The viewer's GitHub link (the user 2026-08-15): a lazy fileGitLink ask per open, answered by the
// file-OWNING kernel (git on ITS disk is the authority). The action shows on EVERY answer (the user
// 2026-09-05): a real URL is an anchor; no URL is a real disabled button with the kernel's reason as
// a caption beside it and in its tooltip; a URL whose branch is not on origin is a dashed anchor
// with the note as its caption. The three states run FOR REAL against a small DOM stand-in (the
// Outline pane's live-clock test is the precedent): the module mounts through document.createElement
// and hears the reply off a window message, so plain objects carrying the handful of DOM members it
// touches stand in for the page. What the DOM cannot show (the CSS, the kernel's side) stays pinned
// at source.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx } from "./file-view";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const VIEW = web("file-view.ts");
const RENDER = web("render.ts");
const CHAT_CSS = web("styles.css");
const FEED_CSS = web("feed.css");
const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");

// ── a DOM stand-in: the members the GitHub action touches at mount and on the reply ───────────────
class El {
  id = ""; title = ""; hidden = false; type = ""; disabled = false; tabIndex = -1;
  href = ""; target = ""; rel = "";
  childNodes: Array<El | string> = [];
  private attrs = new Map<string, string>();
  private classes = new Set<string>();
  classList = {
    add: (...c: string[]) => { for (const x of c) this.classes.add(x); },
    contains: (c: string) => this.classes.has(c),
  };
  constructor(public tagName: string) {}
  get className(): string { return [...this.classes].join(" "); }
  set className(v: string) { this.classes = new Set(v.split(/\s+/).filter(Boolean)); }
  get textContent(): string { return this.childNodes.map((c) => (typeof c === "string" ? c : c.textContent)).join(""); }
  set textContent(v: string) { this.childNodes = v === "" ? [] : [v]; }
  appendChild<T extends El>(c: T): T { this.childNodes.push(c); return c; }
  setAttribute(k: string, v: string): void { this.attrs.set(k, v); }
  getAttribute(k: string): string | null { return this.attrs.get(k) ?? null; }
  hasAttribute(k: string): boolean { return this.attrs.has(k); }
  addEventListener(): void {}
  removeEventListener(): void {}
}
const win: any = new EventTarget();       // window: the reply arrives as a message event
win.parent = win;
(globalThis as any).window = win;
(globalThis as any).document = {
  createElement: (tag: string) => new El(tag),
  createTextNode: (s: string) => s,
  getElementById: () => null,
  addEventListener: () => {},
  removeEventListener: () => {},
  body: new El("body"),
};
const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); },
  removeItem: (k: string) => { store.delete(k); },
};

const posted: any[] = [];
// the viewer seam (plans/file-review.md Slice 1): every action mounts with the FULL ctx; the GitHub
// link reads only path and sid, so the rest is inert here
const noop = () => { /* inert */ };
const stubCtx = (): FileViewActionCtx => ({
  path: "/tmp/notes-api/src/app.py", sid: null,
  body: () => new El("div") as unknown as HTMLElement, mode: () => "raw", text: () => null, mtimeNs: () => "",
  media: () => null, identity: () => null, onRendered: noop, onSelection: noop, onSaved: noop, onClose: noop,
  post: noop, ensureEditingAllowed: async () => true, setEditBlocked: noop, aside: noop, setMode: noop,
  scrollToOffset: noop, reload: noop,
});
async function mountAndAnswer(url: string, reason: string): Promise<El> {
  const fv = await import("./file-view");
  fv.initFileView((m) => posted.push(m));
  const unit = fv.githubLinkAction.mount(stubCtx()) as unknown as El;
  assert.equal(unit.className, "fileview-gh");
  assert.equal(unit.hidden, true, "hidden until the kernel answers");
  assert.equal(unit.childNodes.length, 0, "no control exists before the answer — never an hrefless flash");
  const ask = posted[posted.length - 1];
  assert.deepEqual(ask, { type: "fileGitLink", path: "/tmp/notes-api/src/app.py", sid: undefined, reqId: ask.reqId });
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileGitLink", reqId: ask.reqId, url, reason } }));
  assert.equal(unit.hidden, false, "the answer always shows the action");
  return unit;
}
const parts = (unit: El) => ({
  cap: unit.childNodes.find((c) => c instanceof El && c.className === "fileview-gh-why") as El | undefined,
  ctl: unit.childNodes.find((c) => c instanceof El && c.classList.contains("fileview-btn")) as El,
});

test("state 1 — a real URL: an anchor that opens a new tab, no caption, the URL as tooltip", async () => {
  const url = "https://github.com/TESTORG/notes-api/blob/main/src/app.py";
  const { cap, ctl } = parts(await mountAndAnswer(url, ""));
  assert.equal(ctl.tagName, "a");
  assert.equal(ctl.href, url); assert.equal(ctl.target, "_blank"); assert.equal(ctl.rel, "noopener");
  assert.equal(ctl.textContent, "GitHub ↗");
  assert.equal(ctl.title, url, "the full URL one hover away");
  assert.equal(ctl.classList.contains("fileview-gh-note"), false);
  assert.equal(cap, undefined, "nothing to say — no caption");
});

test("state 2 — no URL: a real disabled button, the reason visible beside it and in the tooltip", async () => {
  // the user 2026-09-05 could not tell "not committed yet" from "the feature is broken" when the
  // button was simply absent; and a reason only a mouse could reach (the tooltip) left touch and
  // keyboard users with the same question
  const unit = await mountAndAnswer("", "the file is not committed");
  const { cap, ctl } = parts(unit);
  assert.equal(ctl.tagName, "button", "a real button: assistive tech exposes disabled and the label");
  assert.equal(ctl.type, "button");
  assert.equal(ctl.disabled, true);
  assert.equal(ctl.href, "", "nothing to follow, nothing to go stale");
  assert.equal(ctl.textContent, "GitHub ↗");
  assert.equal(ctl.title, "No GitHub link: the file is not committed");
  assert.equal(ctl.getAttribute("aria-label"), ctl.title);
  assert.ok(cap, "the caption is the reason itself, without hover");
  assert.equal(cap!.textContent, "the file is not committed");
  assert.equal(cap!.title, "the file is not committed", "truncated by the sheet, whole in its tooltip");
  assert.ok(unit.childNodes.indexOf(cap!) < unit.childNodes.indexOf(ctl), "the caption annotates the control after it");
});

test("state 2b — a kernel that predates link reasons: the caption says so and what to do", async () => {
  const { cap, ctl } = parts(await mountAndAnswer("", ""));
  assert.equal(ctl.disabled, true);
  assert.equal(cap!.textContent, "this kernel predates link reasons; restart it after updating");
  assert.equal(ctl.title, "No GitHub link: this kernel predates link reasons; restart it after updating");
});

test("state 3 — a URL whose branch is not on origin: a dashed anchor with the note as its caption", async () => {
  const url = "https://github.com/TESTORG/notes-api/blob/wip/src/app.py";
  const { cap, ctl } = parts(await mountAndAnswer(url, "the branch has not been pushed"));
  assert.equal(ctl.tagName, "a"); assert.equal(ctl.href, url);
  assert.equal(ctl.classList.contains("fileview-gh-note"), true);
  assert.equal(ctl.title, url + "\nthe branch has not been pushed");
  assert.equal(ctl.getAttribute("aria-label"), "GitHub: the branch has not been pushed");
  assert.equal(cap!.textContent, "the branch has not been pushed");
});

test("a reply for an older open lands nowhere — the newer open keeps waiting for its own", async () => {
  const fv = await import("./file-view");
  fv.initFileView((m) => posted.push(m));
  const ctx = stubCtx();
  const first = fv.githubLinkAction.mount(ctx) as unknown as El;
  const firstReq = posted[posted.length - 1].reqId;
  const second = fv.githubLinkAction.mount(ctx) as unknown as El;   // a replace-open: its hooks supersede
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileGitLink", reqId: firstReq,
    url: "https://github.com/TESTORG/notes-api/blob/main/src/app.py", reason: "" } }));
  assert.equal(first.hidden, true); assert.equal(first.childNodes.length, 0, "the superseded open hears nothing");
  assert.equal(second.hidden, true); assert.equal(second.childNodes.length, 0, "a stale reply is not the newer open's answer");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileGitLink", reqId: posted[posted.length - 1].reqId,
    url: "", reason: "the file is not committed" } }));
  assert.equal(second.hidden, false); assert.equal(parts(second).ctl.disabled, true);
});

// ── what the DOM cannot show, pinned at source ─────────────────────────────────────────────────────

test("the ask is lazy, per open, and sid-routed — never on the /file byte path", () => {
  assert.match(VIEW, /post\(\{ type: "fileGitLink", path, sid: sid \|\| undefined, reqId: gitSeq \}\);/);
  // thumbnails must not pay three git subprocesses each: /file itself is untouched
  assert.doesNotMatch(KERNEL, /_file_github_url\(fp/);
});

test("the poster is bound at the boot of the document that hosts the viewer", () => {
  assert.match(RENDER, /initFileView\(\(m\) => vscodeApi\?\.postMessage\(m\)\);/);
});

test("the sheets dress the unit: the caption at button size, the disabled button inert, the note dashed", () => {
  // both sheets: the FEED hosts the same viewer (the file browser), so its unit dresses the same
  for (const css of [CHAT_CSS, FEED_CSS]) {
    assert.match(css, /a\.fileview-btn \{ text-decoration: none;/);
    assert.match(css, /\.fileview-gh \{ display: inline-flex; align-items: center; gap: 5px; min-width: 0; \}/);
    assert.match(css, /\.fileview-gh\[hidden\] \{ display: none; \}/, "an author display must not beat [hidden]");
    // same size as the buttons it annotates (labels match labels), truncated with the tooltip whole
    assert.match(css, /\.fileview-gh-why \{ font-size: 0\.82em; color: var\(--dim\); max-width: 18em; overflow: hidden;\n\s+text-overflow: ellipsis; white-space: nowrap; \}/);
    assert.match(css, /\.fileview-btn \{ font: inherit; font-size: 0\.82em;/);
    assert.match(css, /\.fileview-gh \.fileview-btn:disabled \{ opacity: 0\.55; cursor: default; \}/);
    assert.match(css, /\.fileview-gh \.fileview-btn:disabled:hover \{ border-color: var\(--card-border\); color: var\(--fg\); background: transparent; \}/);
    assert.match(css, /\.fileview-gh \.fileview-btn:disabled:active \{ transform: none; \}/);
    assert.match(css, /a\.fileview-gh-note \{ border-style: dashed; \}/);
    assert.doesNotMatch(css, /aria-disabled="true"\]/, "the disabled state is the button's own, not an aria bit on an anchor");
  }
});

test("replies are reqId-guarded and cannot touch a later open", () => {
  assert.match(VIEW, /m\.type === "fileGitLink" && gitHooks && m\.reqId === gitHooks\.reqId/);
  assert.match(VIEW, /h\.apply\(String\(m\.url \|\| ""\), String\(m\.reason \|\| ""\)\);/, "the reply's reason travels with its url");
  // both the close and the replace path drop the hooks, so a late reply lands nowhere
  const closes = VIEW.match(/gitHooks = null;/g) || [];
  assert.ok(closes.length >= 2, "cleared on close AND on replace-open");
});

test("the kernel's answer is a verdict from git itself, threaded off the recv loop", () => {
  // the phrases themselves are the kernel's (tests/test_file_github.py pins them); the viewer shows
  // whatever string arrives
  assert.match(KERNEL, /def _file_github_url\(raw, sid\):/);
  assert.match(KERNEL, /def _file_github_link\(raw, sid, check_origin=True\):/, "the (url, reason) sibling the op uses");
  assert.match(KERNEL, /"url": url, "reason": reason\}\)/, "the reason rides the reply");
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

test("the GitHub link is the action REGISTRY's first entry, not another hand-wired button", () => {
  // the registry (the user 2026-08-22): internal seam, no compatibility promise — actions on the
  // open file declare a mount() instead of editing openFileView, so viewer PRs stop colliding there
  assert.match(VIEW, /export function registerFileViewAction\(a: FileViewAction\): void \{/);
  assert.match(VIEW, /if \(!fileViewActions\.some\(\(x\) => x\.id === a\.id\)\) fileViewActions\.push\(a\);/, "same id registered twice mounts once");
  assert.match(VIEW, /export const githubLinkAction: FileViewAction = \{\n  id: "github-link",/);
  assert.match(VIEW, /registerFileViewAction\(githubLinkAction\);/);
  // openFileView renders registered actions by WALKING THE TABLE, after the built-ins, handing each the
  // one per-open seam ctx (plans/file-review.md Slice 1: path, sid, todoId plus the viewer closures)
  assert.match(VIEW, /const ctx: FileViewActionCtx = \{\n    path, sid: sid \|\| null, todoId: opts\?\.todoId \?\? null,/);
  assert.match(VIEW, /for \(const a of fileViewActions\) \{\n    const n = a\.mount\(ctx\);\n    if \(n\) acts\.appendChild\(n\);\n  \}/);
});
