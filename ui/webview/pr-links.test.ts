// PR references link to GitHub (the user 2026-09-06): `#123`, `PR #123` and `owner/repo#123` in a
// session's chat, its feed cards, its user todos and the outline's goal rows become links to the PR page
// of the repository the session works in — the kernel's `githubRepo` (owner/repo, or null). The text
// rule and the DOM applier are EXECUTED here (pr-links.ts is pure but for createElement/createTextNode,
// which a small plain-object DOM stand-in provides); the wiring into render.ts's md(), feed.ts and
// fleet.ts is pinned at the source, the way the other webview tests pin the chat renderer.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

// ── a DOM stand-in: text and element nodes with the handful of members the applier touches ─────────
class T {
  nodeType = 3;
  parentNode: E | null = null;
  constructor(public textContent: string) {}
}
class E {
  nodeType = 1;
  parentNode: E | null = null;
  childNodes: Array<E | T> = [];
  href = ""; target = ""; rel = ""; title = ""; className = "";
  constructor(public tagName: string) {}
  get classList() { const cs = this.className.split(/\s+/).filter(Boolean); return { contains: (c: string) => cs.includes(c) }; }
  get textContent(): string { return this.childNodes.map((c) => c.textContent).join(""); }
  set textContent(v: string) { for (const c of this.childNodes) c.parentNode = null; this.childNodes = []; if (v) this.appendChild(new T(v)); }
  appendChild<N extends E | T>(c: N): N { c.parentNode = this; this.childNodes.push(c); return c; }
  insertBefore<N extends E | T>(n: N, ref: E | T | null): N {
    const i = ref ? this.childNodes.indexOf(ref) : -1;
    n.parentNode = this;
    this.childNodes.splice(i < 0 ? this.childNodes.length : i, 0, n);
    return n;
  }
  removeChild(c: E | T): E | T { const i = this.childNodes.indexOf(c); if (i >= 0) this.childNodes.splice(i, 1); c.parentNode = null; return c; }
  closest(sel: string): E | null {
    const tags = sel.split(",").map((s) => s.trim().toUpperCase());
    for (let n: E | null = this; n; n = n.parentNode) if (tags.includes(n.tagName.toUpperCase())) return n;
    return null;
  }
  /** a compact serialization for assertions: tags lower-case, anchors with their href only */
  html(): string {
    const inner = this.childNodes.map((c) => c instanceof T ? c.textContent : c.html()).join("");
    const t = this.tagName.toLowerCase();
    const attrs = (this.className ? ` class="${this.className}"` : "") + (this.href ? ` href="${this.href}"` : "");
    return `<${t}${attrs}>${inner}</${t}>`;
  }
}
(globalThis as any).document = {
  createElement: (tag: string) => new E(tag.toUpperCase()),
  createTextNode: (s: string) => new T(s),
};
/** build a tree from a tiny tag language: el("p", "text", el("code", "#12")) */
function el(tag: string, ...kids: Array<string | E>): E {
  const e = new E(tag.toUpperCase());
  for (const k of kids) e.appendChild(typeof k === "string" ? new T(k) : k);
  return e;
}
function cls(e: E, c: string): E { e.className = c; return e; }
const anchors = (root: E): E[] => {
  const out: E[] = [];
  const walk = (n: E) => { for (const c of n.childNodes) if (c instanceof E) { if (c.tagName === "A") out.push(c); walk(c); } };
  walk(root);
  return out;
};

// eslint-disable-next-line @typescript-eslint/no-var-requires
const { prRefSegments, linkifyPrRefs, installPrLinkOpener, validPrRepo, PR_LINK_CLASS } = require("./pr-links") as typeof import("./pr-links");

const REPO = "example-org/notes-api";
const url = (n: number | string, repo = REPO) => `https://github.com/${repo}/pull/${n}`;
const links = (text: string, repo: string | null = REPO) => prRefSegments(text, repo).filter((s) => s.href);

// ── the text rule ────────────────────────────────────────────────────────────────────────────────

test("a bare #123 links to the session repo's PR page, the surrounding text untouched", () => {
  assert.deepEqual(prRefSegments("merged #199 today", REPO), [
    { text: "merged " },
    { text: "#199", href: url(199), label: REPO + "#199" },
    { text: " today" },
  ]);
});

test("PR #123 and pull #123 link as a whole phrase, any case, the space optional", () => {
  for (const t of ["PR #197", "pr #197", "Pr#197", "pull #197", "Pull #197", "PULL#197"]) {
    const segs = prRefSegments("fork " + t + ".", REPO);
    assert.deepEqual(segs, [{ text: "fork " }, { text: t, href: url(197), label: REPO + "#197" }, { text: "." }], t);
  }
});

test("owner/repo#123 links into THAT repository", () => {
  const segs = prRefSegments("see example-org/other-tool#42 for the fix", REPO);
  assert.deepEqual(segs, [
    { text: "see " },
    { text: "example-org/other-tool#42", href: url(42, "example-org/other-tool"), label: "example-org/other-tool#42" },
    { text: " for the fix" },
  ]);
  // a repo name may carry dots and underscores; an owner may not
  assert.equal(links("x my-org/my.repo_v2#7")[0].href, url(7, "my-org/my.repo_v2"));
});

test("several references in one run each link, in order", () => {
  const ls = links("#1, #2 and example-org/other#3; PR #4");
  assert.deepEqual(ls.map((s) => s.text), ["#1", "#2", "example-org/other#3", "PR #4"]);
  assert.deepEqual(ls.map((s) => s.href), [url(1), url(2), url(3, "example-org/other"), url(4)]);
});

test("a word boundary before the reference: start, whitespace, brackets, quotes, punctuation", () => {
  for (const t of ["#5", " #5", "(#5)", "[#5]", "{#5}", "\"#5\"", "'#5'", ",#5", ";#5", "re:#5", "<#5>"]) {
    assert.equal(links(t).length, 1, JSON.stringify(t));
    assert.equal(links(t)[0].text, "#5", JSON.stringify(t));
  }
});

test("a # glued to a word, a path or a URL is not a reference", () => {
  for (const t of ["foo#12", "docs/x.html#12", "https://example.com/page#12", "github.com/example-org/notes-api#12",
                   "a/b/c#12", "&#12;", "C#12", "v1.2#3"]) {
    assert.equal(links(t).length, 0, JSON.stringify(t));
  }
});

test("a cross-repo form whose repo reads like a filename is a path fragment, not a reference", () => {
  for (const t of ["docs/x.html#12", "src/app.py#3", "notes/todo.md#7", "a/b.c#1"]) assert.equal(links("see " + t).length, 0, t);
  // a dotted repo name whose tail is not extension-shaped still links; and the scan resumes after a refused one
  assert.equal(links("see my-org/my.repo_v2#7")[0].href, url(7, "my-org/my.repo_v2"));
  assert.deepEqual(links("docs/x.html#12 then #13").map((s) => s.text), ["#13"]);
});

test("a GitHub URL with a fragment stays as it is (its #issuecomment is no number)", () => {
  assert.equal(links("https://github.com/example-org/notes-api/pull/12#issuecomment-99").length, 0);
});

test("colour literals never link: hex letters after the digits, or a leading zero, fail the number shape", () => {
  for (const t of ["#fff", "#FFF", "#000", "#1EA1EB", "#0c1a2e", "#9cd2ff", "#12ab", "#12abcd", "#0", "#01"]) {
    assert.equal(links("color " + t).length, 0, t);
  }
});

test("a number glued to letters, another # or a slash after it is not a reference", () => {
  for (const t of ["#12abc", "#12_x", "#12#13", "#12/x"]) assert.equal(links("x " + t).length, 0, t);
  // sentence punctuation after it is fine
  for (const t of ["#12.", "#12,", "#12)", "#12;", "#12!", "#12?"]) assert.equal(links("x " + t)[0]?.text, "#12", t);
});

test("without a GitHub repo for the session NOTHING links — the cross-repo form included", () => {
  for (const repo of [null, undefined, "", "not a repo", "a/b/c", "https://github.com/x/y"]) {
    assert.deepEqual(prRefSegments("merged #1 and example-org/other#2", repo as any), [{ text: "merged #1 and example-org/other#2" }], String(repo));
  }
  assert.equal(validPrRepo("example-org/notes-api"), "example-org/notes-api");
  assert.equal(validPrRepo("owner/repo.js"), "owner/repo.js");
  assert.equal(validPrRepo("-owner/repo"), null, "an owner cannot start with a hyphen");
  assert.equal(validPrRepo("owner/re po"), null);
});

test("text with no # at all comes back as one plain segment, fast", () => {
  assert.deepEqual(prRefSegments("nothing to see", REPO), [{ text: "nothing to see" }]);
  assert.deepEqual(prRefSegments("", REPO), [{ text: "" }]);
});

// ── the DOM applier ──────────────────────────────────────────────────────────────────────────────

test("a text node's references become pr-link anchors with href, target, rel and a repo-qualified title", () => {
  const p = el("p", "merged #12 today");
  assert.equal(linkifyPrRefs(p as unknown as Node, REPO), 1);
  assert.equal(p.html(), `<p>merged <a class="${PR_LINK_CLASS}" href="${url(12)}">#12</a> today</p>`);
  const a = anchors(p)[0];
  assert.equal(a.target, "_blank");
  assert.equal(a.rel, "noopener noreferrer");
  assert.equal(a.title, REPO + "#12 on GitHub");
  assert.equal(p.textContent, "merged #12 today", "the visible text is unchanged");
});

test("text inside <code> and <pre> is skipped; the prose around it still links", () => {
  const p = el("p", "use ", el("code", "#12"), " and #13");
  assert.equal(linkifyPrRefs(p as unknown as Node, REPO), 1);
  assert.equal(p.html(), `<p>use <code>#12</code> and <a class="pr-link" href="${url(13)}">#13</a></p>`);
  const pre = el("pre", el("code", "git log #12"));
  assert.equal(linkifyPrRefs(pre as unknown as Node, REPO), 0);
  assert.equal(pre.html(), "<pre><code>git log #12</code></pre>");
});

test("text already inside a link is never wrapped again", () => {
  const a = el("a", "#12"); a.href = "https://github.com/example-org/notes-api/pull/12";
  const p = el("p", "see ", a);
  assert.equal(linkifyPrRefs(p as unknown as Node, REPO), 0);
  assert.equal(anchors(p).length, 1);
});

test("the chat's path links are skipped, so a docs/x.md#12-shaped path stays the path it is", () => {
  const p = el("p", cls(el("span", "docs/x.md#12"), "file-uri-link"), " and ", cls(el("span", el("code", "https://x/#1")), "url-code-link"));
  assert.equal(linkifyPrRefs(p as unknown as Node, REPO), 0);
});

test("references inside emphasis and list items link (only code, pre and anchors are opaque)", () => {
  const li = el("li", el("strong", "PR #7"), " shipped; see ", el("em", "#8"));
  assert.equal(linkifyPrRefs(li as unknown as Node, REPO), 2);
  assert.equal(li.html(), `<li><strong><a class="pr-link" href="${url(7)}">PR #7</a></strong> shipped; see <em><a class="pr-link" href="${url(8)}">#8</a></em></li>`);
});

test("a root that itself sits inside code or a link is left alone", () => {
  const inner = el("span", "#12");
  el("code", inner);
  assert.equal(linkifyPrRefs(inner as unknown as Node, REPO), 0);
  const inA = el("span", "#12");
  el("a", inA);
  assert.equal(linkifyPrRefs(inA as unknown as Node, REPO), 0);
});

test("no repo → the DOM is not touched at all", () => {
  const p = el("p", "merged #12 and example-org/other#3");
  assert.equal(linkifyPrRefs(p as unknown as Node, null), 0);
  assert.equal(p.html(), "<p>merged #12 and example-org/other#3</p>");
  assert.equal(linkifyPrRefs(null, REPO), 0);
});

// ── the opener (feed + outline panes) ────────────────────────────────────────────────────────────

function fakeDoc() {
  let handler: ((e: Event) => void) | null = null; let capture: boolean | undefined;
  return {
    doc: { addEventListener: (type: string, fn: (e: Event) => void, cap?: boolean) => { assert.equal(type, "click"); handler = fn; capture = cap; } },
    fire(target: any) {
      const calls: string[] = [];
      const ev: any = { target, preventDefault: () => calls.push("preventDefault"), stopPropagation: () => calls.push("stopPropagation") };
      handler!(ev);
      return calls;
    },
    get capture() { return capture; },
  };
}
const prAnchor = (href: string) => ({ closest: (sel: string) => sel.startsWith("a.pr-link") ? { getAttribute: (k: string) => k === "href" ? href : null } : null });

test("the opener is installed on the capture phase and, on the web, opens the PR in the viewer's own browser", () => {
  const f = fakeDoc(); const opened: string[] = []; const posted: any[] = [];
  installPrLinkOpener(f.doc, (m) => posted.push(m), { protocol: () => "https:", open: (h) => opened.push(h) });
  assert.equal(f.capture, true, "capture phase — the card's own click handler under the link must not fire");
  const calls = f.fire(prAnchor(url(12)));
  assert.deepEqual(calls, ["preventDefault", "stopPropagation"]);
  assert.deepEqual(opened, [url(12)]);
  assert.deepEqual(posted, []);
});

test("in a VS Code webview the href goes to the host as openLink", () => {
  const f = fakeDoc(); const opened: string[] = []; const posted: any[] = [];
  installPrLinkOpener(f.doc, (m) => posted.push(m), { protocol: () => "vscode-webview:", open: (h) => opened.push(h) });
  f.fire(prAnchor(url(12)));
  assert.deepEqual(posted, [{ type: "openLink", href: url(12) }]);
  assert.deepEqual(opened, []);
});

test("clicks that are not on a pr-link, or whose href is not a GitHub URL, are left alone", () => {
  const f = fakeDoc(); const opened: string[] = [];
  installPrLinkOpener(f.doc, undefined, { protocol: () => "https:", open: (h) => opened.push(h) });
  assert.deepEqual(f.fire({ closest: () => null }), []);
  assert.deepEqual(f.fire(prAnchor("javascript:alert(1)")), []);
  assert.deepEqual(f.fire(prAnchor("https://example.com/x")), []);
  assert.deepEqual(f.fire(null), []);
  assert.deepEqual(opened, []);
});

// ── wiring pins ──────────────────────────────────────────────────────────────────────────────────

const read = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const RENDER = read("render.ts");
const FEED = read("feed.ts");
const OUTLINE = read("fleet.ts");

test("the chat links inside md(): the sanitized tree is walked before it serializes, against the owning session's repo", () => {
  assert.match(RENDER, /import \{ linkifyPrRefs \} from "\.\/pr-links";/);
  assert.match(RENDER, /function md\(src: string, repo: string \| null = prRepoFor\(\)\): string \{/);
  const mdFn = RENDER.match(/function md\(src: string[^\n]*?\): string \{[\s\S]*?\n\}/)?.[0] || "";
  assert.match(mdFn, /RETURN_DOM: true \}\) as HTMLElement;[^\n]*\n\s*linkifyPrRefs\(clean, repo\);\s*\n\s*return clean\.innerHTML;/,
    "DOMPurify's own serialization is replaced by ours, after the walk — the sanitizer's verdicts stand");
  assert.match(RENDER, /const id = sid \?\? renderingOwnerSid \?\? renderingSid \?\? activeId;/, "the owning session, as relative paths resolve");
  assert.doesNotMatch(RENDER, /installPrLinkOpener/, "the chat's own a[href] delegate already opens every absolute-scheme anchor");
});

test("the session frame's githubRepo rides the Session and survives a chatTail delta; a null from the kernel is honoured", () => {
  assert.match(RENDER, /interface Session \{[^\n]*githubRepo\?: string \| null;/);
  assert.match(RENDER, /githubRepo: \("githubRepo" in msg\) \? \(msg\.githubRepo \?\? null\) : \(prev \? prev\.githubRepo : null\),/);
});

test("postal bodies resolve the SENDER's repo when one open session carries the peer's name", () => {
  assert.match(RENDER, /full\.innerHTML = md\(ev\.body, postalRepoFor\(ev\)\)/);
  assert.match(RENDER, /body\.innerHTML = md\(ev\.body, postalRepoFor\(ev\)\);/);
  const fn = RENDER.match(/function postalRepoFor\([\s\S]*?\n\}/)?.[0] || "";
  assert.match(fn, /ev\.direction === "in"/);
  assert.match(fn, /named\.length === 1/);
  assert.match(fn, /return prRepoFor\(\);/, "otherwise the reading session's repo");
});

test("the chat's plain-text surfaces link too: user-todo rows, their detail folds, and the reply prompt's quote", () => {
  assert.match(RENDER, /txt\.textContent = t\.text;\s*\n\s*linkifyPrRefs\(txt, prRepoFor\(renderingSid\)\);/);
  assert.match(RENDER, /linkifyFileUris\(d, undefined, undefined, undefined, undefined, renderingSid \|\| null\);\s*\n\s*linkifyPrRefs\(d, prRepoFor\(renderingSid\)\);/);
  assert.match(RENDER, /d\.textContent = todoText;\s*\n\s*linkifyPrRefs\(d, prRepoFor\(sid\)\);/);
  assert.match(RENDER, /linkifyFileUris\(dd, undefined, undefined, undefined, undefined, sid\); linkifyPrRefs\(dd, prRepoFor\(sid\)\);/);
});

test("the feed links card titles, distiller lines, held-mail gists, group cards, checklists and the modal — per the card's session", () => {
  assert.match(FEED, /import \{ linkifyPrRefs, installPrLinkOpener \} from "\.\/pr-links";/);
  assert.match(FEED, /githubRepo\?: string \| null \}\[\] = \[\];/, "the session rows carry the repo");
  assert.match(FEED, /function prRepoOf\(sid: string \| undefined\): string \| null \{\s*\n\s*return \(sid && sessionsMeta\.find\(\(s\) => s\.sid === sid\)\?\.githubRepo\) \|\| null;/);
  assert.match(FEED, /a\._title\.textContent = it\.text;\s*\n\s*linkifyPrRefs\(a\._title, prRepoOf\(it\.sid\)\);/);
  assert.match(FEED, /if \(distillShown\) linkifyPrRefs\(a\._distill as HTMLElement, prRepoOf\(it\.sid\)\);/);
  assert.match(FEED, /linkifyPrRefsIn\(Object\.assign\(el\("div", "fq-gist"\)/);
  assert.match(FEED, /a\._title\.textContent = g\.title;\s*\n\s*linkifyPrRefs\(a\._title, prRepoOf\(g\.sid\)\);/);
  assert.match(FEED, /txt\.textContent = m\.text; linkifyPrRefs\(txt, prRepoOf\(m\.sid \|\| g\.sid\)\);/);
  assert.match(FEED, /el\("span", "fcheck-text"\); txt\.textContent = s\.text; linkifyPrRefs\(txt, prRepoOf\(it\.sid\)\);/);
  assert.match(FEED, /el\("span", "ftree-text"\); txt\.textContent = node\.text \|\| "\(node\)"; linkifyPrRefs\(txt, prRepoOf\(it\.sid\)\);/);
  assert.match(FEED, /bb\.textContent = modalBg; linkifyPrRefs\(bb, prRepoOf\(it\.sid\)\);/);
  assert.match(FEED, /sum\.textContent = nodeDistill;\s*\n\s*linkifyPrRefs\(sum, prRepoOf\(it\.sid\)\);/);
  assert.match(FEED, /installPrLinkOpener\(document, vscodeApi \? \(m\) => vscodeApi\.postMessage\(m\) : undefined\);/);
});

test("the outline links goal rows per session and opens them itself", () => {
  assert.match(OUTLINE, /import \{ linkifyPrRefs, installPrLinkOpener \} from "\.\/pr-links";/);
  assert.match(OUTLINE, /repoBySid = new Map\(m\.sessions\.filter/);
  assert.match(OUTLINE, /highlightInto\(txt, n\.text, curSearch\);[^\n]*\n\s*linkifyPrRefs\(txt, repoBySid\.get\(s\.sid\) \|\| null\);/);
  assert.match(OUTLINE, /installPrLinkOpener\(document, vscodeApi \? \(m\) => vscodeApi\.postMessage\(m\) : undefined\);/);
});

test("the Waiting-on-you pane links asks and their detail per session and opens them itself", () => {
  const WAITING = read("waiting.ts");
  assert.match(WAITING, /import \{ linkifyPrRefs, installPrLinkOpener \} from "\.\/pr-links";/);
  assert.match(WAITING, /repoBySid = new Map\(m\.sessions\.filter/);
  assert.match(WAITING, /txt\.textContent = w\.todo\.text;\s*\n\s*linkifyPrRefs\(txt, repoBySid\.get\(w\.sid\) \|\| null\);/);
  assert.match(WAITING, /d\.textContent = w\.todo\.detail \|\| "";\s*\n\s*linkifyPrRefs\(d, repoBySid\.get\(w\.sid\) \|\| null\);/);
  assert.match(WAITING, /installPrLinkOpener\(document, vscodeApi \? \(m\) => vscodeApi\.postMessage\(m\) : undefined\);/);
});

test("the pr-link anchor wears the hyperlink ink in both sheets", () => {
  for (const f of ["styles.css", "feed.css"]) {
    const css = read(f);
    assert.match(css, /\.pr-link \{ color: var\(--link\); text-decoration: none; \}/, f);
    assert.match(css, /\.pr-link:hover \{ text-decoration: underline; \}/, f);
  }
});
