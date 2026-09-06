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
  dataset: Record<string, string | undefined> = {};
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
const { prRefSegments, linkifyPrRefs, setLinkedText, senderPrRepo, installPrLinkOpener, validPrRepo, PR_LINK_CLASS } = require("./pr-links") as typeof import("./pr-links");

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

test("a word boundary before the reference: start, whitespace, brackets, quotes, punctuation, dashes", () => {
  for (const t of ["#5", " #5", "(#5)", "[#5]", "{#5}", "\"#5\"", "'#5'", ",#5", ";#5", "re:#5", "<#5>", "“#5”", "‘#5’", "«#5»", "—#5", "–#5"]) {
    assert.equal(links(t).length, 1, JSON.stringify(t));
    assert.equal(links(t)[0].text, "#5", JSON.stringify(t));
  }
});

test("an em or en dash glued to the reference is a boundary (prose habitually writes one); the ASCII hyphen is not", () => {
  // the dashes never end a URL path or an identifier, so nothing is lost by admitting them
  assert.deepEqual(links("Two PRs are up—#12 and #13.").map((s) => s.text), ["#12", "#13"]);
  assert.deepEqual(links("landed–#199 is merged").map((s) => s.text), ["#199"]);
  assert.deepEqual(links("merged—example-org/other#3").map((s) => s.href), [url(3, "example-org/other")]);
  // a hyphen does end them: `https://example.com/a-#12` is a URL with a fragment, `foo-#12` an identifier
  for (const t of ["https://example.com/a-#12", "x -#12", "foo-#12", "-#12"]) assert.equal(links(t).length, 0, t);
});

test("a # glued to a word, a path or a URL is not a reference", () => {
  for (const t of ["foo#12", "docs/x.html#12", "https://example.com/page#12", "github.com/example-org/notes-api#12",
                   "a/b/c#12", "&#12;", "C#12", "v1.2#3"]) {
    assert.equal(links(t).length, 0, JSON.stringify(t));
  }
});

test("the cross-repo form follows GitHub's name grammar: owner = alphanumerics and single inner hyphens, repo may add . and _", () => {
  // valid owners link, into the repository named
  for (const [t, repo] of [["a-b/c-d#1", "a-b/c-d"], ["a1/b_2-v3#1", "a1/b_2-v3"], ["x/y#1", "x/y"], ["ab/c.d.e-f#1", "ab/c.d.e-f"]] as const)
    assert.equal(links("see " + t)[0]?.href, url(1, repo), t);
  // (a dotted repo whose tail is extension-shaped — `b_2.3`, `c.d.e` — is the filename refusal below, not the grammar)
  // two plain words around a slash ARE GitHub's syntax (a directory path never carries a bare numeric
  // fragment — a line reference is `file.py#L12`), so they link; pinned as the documented reading
  assert.equal(links("see src/lib#3")[0]?.href, url(3, "src/lib"));
  assert.equal(links("see kernel/kernel#12")[0]?.href, url(12, "kernel/kernel"));
  // owners GitHub does not allow never link — and the number after them does not fall through to a bare #n
  for (const t of ["my.org/repo#1", "-owner/repo#1", "owner-/repo#1", "ow--ner/repo#1", "own_er/repo#1", "a/b/c#1"])
    assert.equal(links("see " + t).length, 0, t);
  // an owner longer than GitHub's 39 characters is no owner
  assert.equal(links("see " + "a".repeat(40) + "/repo#1").length, 0);
  assert.equal(links("see " + "a".repeat(39) + "/repo#1").length, 1);
});

test("`.` and `..` are never a repo: a/..#12 and a/.#12 stay plain, in the text rule and in validPrRepo", () => {
  for (const t of ["a/..#12", "a/.#12", "example-org/..#7"]) assert.equal(links("see " + t).length, 0, t);
  assert.equal(validPrRepo("a/.."), null);
  assert.equal(validPrRepo("a/."), null);
  assert.equal(validPrRepo("a/..."), "a/...", "three dots are an odd but legal repo name");
});

test("a cross-repo form whose repo reads like a filename is a path fragment, not a reference — except a GitHub Pages repo", () => {
  for (const t of ["docs/x.html#12", "src/app.py#3", "notes/todo.md#7", "a/b.c#1"]) assert.equal(links("see " + t).length, 0, t);
  // the documented cost: a repository literally named like a file stays plain in the cross-repo form
  for (const t of ["org/tool.dev#4", "org/something.js#4"]) assert.equal(links("see " + t).length, 0, t);
  // …but `owner/owner.github.io` is the one standard dotted repo name, and it links (any case)
  assert.equal(links("see org/org.github.io#4")[0]?.href, url(4, "org/org.github.io"));
  assert.equal(links("see Org/Org.GitHub.IO#4")[0]?.href, url(4, "Org/Org.GitHub.IO"));
  // a dotted repo name whose tail is not extension-shaped still links; and the scan resumes after a refused one
  assert.equal(links("see my-org/my.repo_v2#7")[0].href, url(7, "my-org/my.repo_v2"));
  assert.deepEqual(links("docs/x.html#12 then #13").map((s) => s.text), ["#13"]);
});

test("a session's OWN repo is never filename-filtered: a Pages or file-named checkout links its bare #n", () => {
  assert.equal(links("merged #4", "user/user.github.io")[0]?.href, url(4, "user/user.github.io"));
  assert.equal(links("merged #4", "org/something.js")[0]?.href, url(4, "org/something.js"));
});

test("a GitHub URL with a fragment stays as it is (its #issuecomment is no number)", () => {
  assert.equal(links("https://github.com/example-org/notes-api/pull/12#issuecomment-99").length, 0);
});

test("color literals never link: hex letters after the digits, or a leading zero, fail the number shape", () => {
  for (const t of ["#fff", "#FFF", "#000", "#1EA1EB", "#0c1a2e", "#9cd2ff", "#12ab", "#12abcd", "#0", "#01"]) {
    assert.equal(links("color " + t).length, 0, t);
  }
  // the documented cost: an all-decimal six-digit color is indistinguishable from a PR number in prose
  // (in code or a code-like element it never links — see the applier tests)
  assert.equal(links("color #123456")[0]?.text, "#123456");
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
  assert.equal(validPrRepo("user/user.github.io"), "user/user.github.io");
  assert.equal(validPrRepo("-owner/repo"), null, "an owner cannot start with a hyphen");
  assert.equal(validPrRepo("owner-/repo"), null, "or end with one");
  assert.equal(validPrRepo("ow--ner/repo"), null, "or double one");
  assert.equal(validPrRepo("my.org/repo"), null, "or carry a dot");
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

test("the other code-like elements are opaque too: kbd, samp, var, tt — a quoted key or token is not a reference", () => {
  for (const tag of ["kbd", "samp", "var", "tt"]) {
    const p = el("p", "see ", el(tag, "#12"), " and #13");
    assert.equal(linkifyPrRefs(p as unknown as Node, REPO), 1, tag);
    assert.equal(anchors(p).length, 1, tag);
    assert.equal(anchors(p)[0].textContent, "#13", tag);
  }
  // typographic wrappers are walked: a superscripted or emphasized #n is still a reference
  for (const tag of ["sup", "sub", "em", "strong", "span", "small"]) {
    const p = el("p", "see ", el(tag, "#12"));
    assert.equal(linkifyPrRefs(p as unknown as Node, REPO), 1, tag);
  }
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

test("references inside emphasis and list items link (only anchors and code-like elements are opaque)", () => {
  const li = el("li", el("strong", "PR #7"), " shipped; see ", el("em", "#8"));
  assert.equal(linkifyPrRefs(li as unknown as Node, REPO), 2);
  assert.equal(li.html(), `<li><strong><a class="pr-link" href="${url(7)}">PR #7</a></strong> shipped; see <em><a class="pr-link" href="${url(8)}">#8</a></em></li>`);
});

test("a root that itself sits inside code, a code-like element or a link is left alone", () => {
  for (const tag of ["code", "pre", "kbd", "samp", "var", "tt", "a"]) {
    const inner = el("span", "#12");
    el(tag, inner);
    assert.equal(linkifyPrRefs(inner as unknown as Node, REPO), 0, tag);
  }
});

test("a root whose whole text has no # is not walked at all — one textContent read, no childNodes access", () => {
  const p = el("p", "a long body ", el("em", "with markup"), " but no reference");
  let reads = 0;
  const kids = p.childNodes;
  // the stand-in's own textContent getter walks childNodes; a browser's is one native read, so stand it in too
  Object.defineProperty(p, "textContent", { get() { return "a long body with markup but no reference"; } });
  Object.defineProperty(p, "childNodes", { get() { reads++; return kids; } });
  assert.equal(linkifyPrRefs(p as unknown as Node, REPO), 0);
  assert.equal(reads, 0, "the walk was skipped");
  // …and one WITH a reference is walked as before
  const q = el("p", "a body ", el("em", "with #12"));
  assert.equal(linkifyPrRefs(q as unknown as Node, REPO), 1);
});

test("no repo → the DOM is not touched at all", () => {
  const p = el("p", "merged #12 and example-org/other#3");
  assert.equal(linkifyPrRefs(p as unknown as Node, null), 0);
  assert.equal(p.html(), "<p>merged #12 and example-org/other#3</p>");
  assert.equal(linkifyPrRefs(null, REPO), 0);
});

// ── setLinkedText: the keyed in-place update the feed's card titles use ─────────────────────────

test("setLinkedText writes the text with its links once, and leaves the SAME anchor nodes in place while (text, repo) is unchanged", () => {
  const title = el("div");
  setLinkedText(title as unknown as HTMLElement, "merged #12 today", REPO);
  assert.equal(title.html(), `<div>merged <a class="pr-link" href="${url(12)}">#12</a> today</div>`);
  const first = anchors(title)[0];
  setLinkedText(title as unknown as HTMLElement, "merged #12 today", REPO);   // the next push, nothing changed
  setLinkedText(title as unknown as HTMLElement, "merged #12 today", REPO);
  assert.equal(anchors(title)[0], first, "identity survives the pushes — the press and the release meet one node");
  assert.deepEqual(title.dataset, { prText: "merged #12 today", prRepo: REPO });
});

test("setLinkedText re-renders when the text or the repo changes, and renders plain text with no repo", () => {
  const title = el("div");
  setLinkedText(title as unknown as HTMLElement, "merged #12", REPO);
  const first = anchors(title)[0];
  setLinkedText(title as unknown as HTMLElement, "merged #12 and #13", REPO);
  assert.equal(anchors(title).length, 2);
  assert.notEqual(anchors(title)[0], first, "new text, new nodes");
  setLinkedText(title as unknown as HTMLElement, "merged #12 and #13", "example-org/other");
  assert.equal(anchors(title)[0].href, url(12, "example-org/other"), "a repo change re-links");
  setLinkedText(title as unknown as HTMLElement, "merged #12 and #13", null);
  assert.equal(title.html(), "<div>merged #12 and #13</div>");
  assert.equal(title.dataset.prRepo, "");
  setLinkedText(title as unknown as HTMLElement, "merged #12 and #13", "not a repo");
  assert.equal(title.html(), "<div>merged #12 and #13</div>", "an invalid repo is no repo");
});

// ── senderPrRepo: a message links against its SENDER's frame-known repo, never a guess ──────────

const U = "11111111-2222-3333-4444-555555555555";
const V = "99999999-8888-7777-6666-555555555555";
const rows = [
  { sid: U, name: "web", githubRepo: "example-org/notes-web" },
  { sid: V, name: "api", githubRepo: "example-org/notes-api" },
  { sid: "TESTHOST:" + U, name: "TESTHOST:tests", githubRepo: "example-org/notes-tests" },
  { sid: "TESTHOST:" + V, name: "TESTHOST:api", githubRepo: "other-org/api" },
  { sid: "22222222-2222-3333-4444-555555555555", name: "norepo", githubRepo: null },
];

test("with no host named (the chat's postal cards): the one session answering to the name, local or federated by its bare name", () => {
  assert.equal(senderPrRepo(rows, "web"), "example-org/notes-web");
  assert.equal(senderPrRepo(rows, "tests"), "example-org/notes-tests", "a federated row matches on its bare name");
  assert.equal(senderPrRepo(rows, "api"), null, "a homonym on another attached host makes the sender ambiguous: no guess");
  assert.equal(senderPrRepo(rows, "norepo"), null, "a sender the kernel gave no repo links nothing");
  assert.equal(senderPrRepo(rows, "nobody"), null, "an unknown sender links nothing — the reader's repo is never substituted");
  assert.equal(senderPrRepo(rows, ""), null);
  assert.equal(senderPrRepo(rows, "TESTHOST:api"), null, "the kernel writes the bare name; a prefixed one matches no row");
});

test("with the sender's host named (the feed's held-mail cards): exactly that host's row", () => {
  assert.equal(senderPrRepo(rows, "api", ""), "example-org/notes-api", "the viewing kernel's own host → the local row");
  assert.equal(senderPrRepo(rows, "api", "TESTHOST"), "other-org/api", "another host → its federated row");
  assert.equal(senderPrRepo(rows, "tests", ""), null, "no local row of that name");
  assert.equal(senderPrRepo(rows, "web", "OTHERHOST"), null, "a host not in the frame");
});

test("senderPrRepo tolerates malformed rows and an invalid repo value", () => {
  assert.equal(senderPrRepo([{ sid: U, name: "web", githubRepo: "https://github.com/x/y" }], "web"), null);
  assert.equal(senderPrRepo([null as any, { sid: 5 as any, name: "web" }, { sid: U, name: "web", githubRepo: "x/y" }], "web"), "x/y");
});

// ── the opener (feed + outline + waiting panes) ─────────────────────────────────────────────────

/** a document stand-in recording one capture-phase listener per event type */
function fakeDoc() {
  const handlers = new Map<string, (e: Event) => void>();
  const captures = new Map<string, boolean | undefined>();
  return {
    doc: { addEventListener: (type: string, fn: (e: Event) => void, cap?: boolean) => { handlers.set(type, fn); captures.set(type, cap); } },
    /** dispatch one event; returns the default-prevention calls it made */
    fire(type: string, target: any, extra: Record<string, unknown> = {}) {
      const calls: string[] = [];
      const ev: any = { target, button: 0, isPrimary: true, ...extra,
        preventDefault: () => calls.push("preventDefault"), stopPropagation: () => calls.push("stopPropagation") };
      const h = handlers.get(type);
      assert.ok(h, "a listener for " + type);
      h!(ev);
      return calls;
    },
    types: () => Array.from(handlers.keys()).sort(),
    capture: (type: string) => captures.get(type),
  };
}
/** a fresh node standing for a pr-link anchor with `href` — a new object each call, as a rebuilt node is */
const prAnchor = (href: string) => ({ closest: (sel: string) => sel.startsWith("a.pr-link") ? { getAttribute: (k: string) => k === "href" ? href : null } : null });
const plain = { closest: () => null };
const SPENT = ["preventDefault", "stopPropagation"];

function install(protocol = "https:") {
  const f = fakeDoc(); const opened: string[] = []; const posted: any[] = [];
  installPrLinkOpener(f.doc, (m) => posted.push(m), { protocol: () => protocol, open: (h) => opened.push(h) });
  return { f, opened, posted };
}

test("the opener hangs on the stable document, capture phase, for the press, the release, the click and the clearing events", () => {
  const { f } = install();
  assert.deepEqual(f.types(), ["click", "keydown", "pointercancel", "pointerdown", "pointerup"]);
  for (const t of f.types()) assert.equal(f.capture(t), true, t + " — the card's own handler under the link must not fire");
});

test("press and release on a pr-link with the same href open it ONCE — through a rebuilt node — and the click that follows is spent", () => {
  const { f, opened, posted } = install();
  assert.deepEqual(f.fire("pointerdown", prAnchor(url(12))), []);
  assert.deepEqual(opened, [], "nothing opens on the press");
  f.fire("pointerup", prAnchor(url(12)));            // a DIFFERENT node object: the push rebuilt the anchor
  assert.deepEqual(opened, [url(12)]);
  // the native click (here on the common ancestor, the pressed node being gone) is spent: the card's modal never opens
  assert.deepEqual(f.fire("click", plain), SPENT);
  assert.deepEqual(opened, [url(12)], "no second open");
  assert.deepEqual(posted, []);
  // the next click is an ordinary click again
  assert.deepEqual(f.fire("click", plain), []);
});

test("when the anchor survives, the same press/release/click sequence still opens exactly once", () => {
  const { f, opened } = install();
  const a = prAnchor(url(12));
  f.fire("pointerdown", a); f.fire("pointerup", a);
  assert.deepEqual(f.fire("click", a), SPENT);
  assert.deepEqual(opened, [url(12)]);
});

test("a release elsewhere, a release on a different link, or a press elsewhere opens nothing — and the click is not touched", () => {
  const { f, opened } = install();
  f.fire("pointerdown", prAnchor(url(12))); f.fire("pointerup", plain);
  assert.deepEqual(f.fire("click", plain), [], "the card's click stands");
  f.fire("pointerdown", prAnchor(url(12))); f.fire("pointerup", prAnchor(url(13)));
  assert.deepEqual(f.fire("click", plain), []);
  f.fire("pointerdown", plain); f.fire("pointerup", prAnchor(url(12)));
  assert.deepEqual(opened, []);
});

test("a click on a pr-link with no pointer press behind it (a keyboard activation) opens it through the click path", () => {
  const { f, opened } = install();
  assert.deepEqual(f.fire("click", prAnchor(url(12))), SPENT);
  assert.deepEqual(opened, [url(12)]);
});

test("the spent flag never eats an unrelated click: a new press or a key clears it when no click followed the open", () => {
  const { f, opened } = install();
  f.fire("pointerdown", prAnchor(url(12))); f.fire("pointerup", prAnchor(url(12)));
  assert.deepEqual(opened, [url(12)]);
  // the browser fired no click (the pressed node was detached); the user presses a card next
  f.fire("pointerdown", plain); f.fire("pointerup", plain);
  assert.deepEqual(f.fire("click", plain), [], "the card's click lands");
  // …or activates something by keyboard
  f.fire("pointerdown", prAnchor(url(12))); f.fire("pointerup", prAnchor(url(12)));
  f.fire("keydown", plain);
  assert.deepEqual(f.fire("click", plain), []);
  assert.deepEqual(opened, [url(12), url(12)]);
});

test("a cancelled pointer, a secondary button or a non-primary pointer never opens", () => {
  const { f, opened } = install();
  f.fire("pointerdown", prAnchor(url(12))); f.fire("pointercancel", prAnchor(url(12))); f.fire("pointerup", prAnchor(url(12)));
  f.fire("pointerdown", prAnchor(url(12)), { button: 2 }); f.fire("pointerup", prAnchor(url(12)), { button: 2 });
  f.fire("pointerdown", prAnchor(url(12)), { isPrimary: false }); f.fire("pointerup", prAnchor(url(12)), { isPrimary: false });
  f.fire("pointerdown", prAnchor(url(12))); f.fire("pointerup", prAnchor(url(12)), { button: 1 });
  assert.deepEqual(opened, []);
});

test("in a VS Code webview the href goes to the host as openLink, from the release and from a keyboard click alike", () => {
  const { f, opened, posted } = install("vscode-webview:");
  f.fire("pointerdown", prAnchor(url(12))); f.fire("pointerup", prAnchor(url(12))); f.fire("click", plain);
  f.fire("click", prAnchor(url(13)));
  assert.deepEqual(posted, [{ type: "openLink", href: url(12) }, { type: "openLink", href: url(13) }]);
  assert.deepEqual(opened, []);
});

test("targets that are not a pr-link, or whose href is not a GitHub URL, are left alone at every phase", () => {
  const f = fakeDoc(); const opened: string[] = [];
  installPrLinkOpener(f.doc, undefined, { protocol: () => "https:", open: (h) => opened.push(h) });
  for (const t of [plain, prAnchor("javascript:alert(1)"), prAnchor("https://example.com/x"), null]) {
    f.fire("pointerdown", t); f.fire("pointerup", t);
    assert.deepEqual(f.fire("click", t), [], String(t && (t as any).closest?.("a.pr-link")?.getAttribute("href")));
  }
  assert.deepEqual(opened, []);
});

// ── wiring pins ──────────────────────────────────────────────────────────────────────────────────

const read = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const RENDER = read("render.ts");
const FEED = read("feed.ts");
const OUTLINE = read("fleet.ts");

test("the chat links inside md(): the sanitized tree is walked before it serializes, against the owning session's repo", () => {
  assert.match(RENDER, /import \{ linkifyPrRefs, senderPrRepo \} from "\.\/pr-links";/);
  assert.match(RENDER, /function md\(src: string, repo: string \| null = prRepoFor\(\)\): string \{/);
  const mdFn = RENDER.match(/function md\(src: string[^\n]*?\): string \{[\s\S]*?\n\}/)?.[0] || "";
  assert.match(mdFn, /RETURN_DOM: true \}\) as HTMLElement;[^\n]*\n\s*linkifyPrRefs\(clean, repo\);\s*\n\s*return clean\.innerHTML;/,
    "DOMPurify's own serialization is replaced by ours, after the walk — the sanitizer's verdicts stand");
  assert.match(RENDER, /const id = sid \?\? renderingOwnerSid \?\? renderingSid \?\? activeId;/, "the owning session, as relative paths resolve");
  assert.doesNotMatch(RENDER, /installPrLinkOpener/, "the chat's own a[href] delegate already opens every absolute-scheme anchor");
});

test("the session frame's githubRepo rides the Session and survives a chatTail delta; a null from the kernel is honored", () => {
  assert.match(RENDER, /interface Session \{[^\n]*githubRepo\?: string \| null;/);
  assert.match(RENDER, /githubRepo: \("githubRepo" in msg\) \? \(msg\.githubRepo \?\? null\) : \(prev \? prev\.githubRepo : null\),/);
});

test("postal bodies link against the SENDER's frame-known repo only: outbound = the writer's own, inbound = senderPrRepo over the session map, never the reader's as a fallback", () => {
  assert.match(RENDER, /full\.innerHTML = md\(ev\.body, postalRepoFor\(ev\)\)/);
  assert.match(RENDER, /body\.innerHTML = md\(ev\.body, postalRepoFor\(ev\)\);/);
  const fn = RENDER.match(/function postalRepoFor\([\s\S]*?\n\}/)?.[0] || "";
  assert.match(fn, /if \(ev\.direction === "out"\) return prRepoFor\(\);/);
  assert.match(fn, /return senderPrRepo\(Array\.from\(sessions\.values\(\), \(s\) => \(\{ sid: s\.id, name: s\.name, githubRepo: s\.githubRepo \}\)\), ev\.peer\);/);
  assert.equal((fn.match(/prRepoFor\(/g) || []).length, 1, "the reading session's repo is used for OUTBOUND mail only");
});

test("the chat's plain-text surfaces link too: user-todo rows, their detail folds, and the reply prompt's quote", () => {
  assert.match(RENDER, /txt\.textContent = t\.text;\s*\n\s*linkifyPrRefs\(txt, prRepoFor\(renderingSid\)\);/);
  assert.match(RENDER, /linkifyFileUris\(d, undefined, undefined, undefined, undefined, renderingSid \|\| null\);\s*\n\s*linkifyPrRefs\(d, prRepoFor\(renderingSid\)\);/);
  assert.match(RENDER, /d\.textContent = todoText;\s*\n\s*linkifyPrRefs\(d, prRepoFor\(sid\)\);/);
  assert.match(RENDER, /linkifyFileUris\(dd, undefined, undefined, undefined, undefined, sid\); linkifyPrRefs\(dd, prRepoFor\(sid\)\);/);
});

test("the feed links card titles (keyed), distiller lines, held-mail gists (by sender), group cards, checklists and the modal — per the card's session", () => {
  assert.match(FEED, /import \{ linkifyPrRefs, setLinkedText, senderPrRepo, installPrLinkOpener \} from "\.\/pr-links";/);
  assert.match(FEED, /githubRepo\?: string \| null \}\[\] = \[\];/, "the session rows carry the repo");
  assert.match(FEED, /function prRepoOf\(sid: string \| undefined\): string \| null \{\s*\n\s*return \(sid && sessionsMeta\.find\(\(s\) => s\.sid === sid\)\?\.githubRepo\) \|\| null;/);
  // the two in-place titles are KEYED: an unchanged title keeps its anchor nodes across pushes
  assert.match(FEED, /setLinkedText\(a\._title, it\.text, prRepoOf\(it\.sid\)\);/);
  assert.match(FEED, /setLinkedText\(a\._title, g\.title, prRepoOf\(g\.sid\)\);/);
  assert.doesNotMatch(FEED, /a\._title\.textContent = /, "no per-push rewrite of a title");
  assert.match(FEED, /if \(distillShown\) linkifyPrRefs\(a\._distill as HTMLElement, prRepoOf\(it\.sid\)\);/);
  // the held message's gist links against its SENDER's repo (blocked.frm on blocked.origin), not the recipient card's
  assert.match(FEED, /linkifyPrRefsIn\(Object\.assign\(el\("div", "fq-gist"\)[^\n]*prRepoOfSender\(it\.blocked\.frm, it\.blocked\.origin\)\)\);/);
  const sender = FEED.match(/function prRepoOfSender\([\s\S]*?\n\}/)?.[0] || "";
  assert.match(sender, /const host = !origin \|\| origin === "\?" \? undefined : origin === feedSelfHost \? "" : origin;/);
  assert.match(sender, /return senderPrRepo\(sessionsMeta, frm \|\| "", host\);/);
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
