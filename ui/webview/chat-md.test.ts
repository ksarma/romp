// The user's own words keep their line breaks in the chat (the user 2026-09-06): Shift+Enter in the
// composer inserts a newline, the text reaches the kernel and the transcript with it intact, and then the
// blue bubble rendered it through the shared `marked` singleton, `breaks: false`, right for authored
// markdown where a lone newline is a soft wrap, so the lines ran together into one paragraph. The fix is
// a SECOND marked instance for user text (chat-md.ts `userMarked`, `breaks: true`) built from the same
// extensions the singleton gets plus the chat's own pathAwareEmphasis, which the reply instance (chat-md.ts
// `chatMarked`, the one render.ts's md() parses through since 2026-09-19) takes too, so against a reply's
// rendering only the newlines change. Executed here for real (marked + katex are plain JS); the render.ts
// wiring is source-pinned, since the webview has no jsdom harness.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { Marked } from "marked";
import { chatMdHtml, userMdHtml } from "./chat-md";
import { mdExtensions } from "./md-config";

// the SINGLETON's configuration, rebuilt on a private instance: gfm, breaks OFF, the shared list and nothing else.
// This is the viewer's, the hover preview's and the anchor map's grammar, not a chat surface's: the chat's two
// instances take the list plus pathAwareEmphasis (chat-md.ts), so a path's underscores render differently here.
const singleton = new Marked({ gfm: true, breaks: false }, ...mdExtensions);
const singletonHtml = (src: string) => singleton.parse(src) as string;

// --- executed: the user renderer keeps newlines, the breaks:false grammars (the singleton's and the reply's) do not ---

test("a single newline in user text becomes a hard line break; the singleton's breaks:false grammar keeps it a soft wrap, and so does the reply instance", () => {
  const user = userMdHtml("line one\nline two");
  assert.match(user, /line one<br>\s*line two/, "the user's newline renders as <br>");
  const soft = singletonHtml("line one\nline two");
  assert.doesNotMatch(soft, /<br>/, "the singleton: a lone newline stays a soft wrap");
  assert.match(soft, /line one\nline two/);
  assert.equal(chatMdHtml("line one\nline two"), soft, "the reply instance is breaks:false too: on a row with no linkable token it renders as the singleton does");
});

test("a blank line is still a paragraph break, not a run of <br>", () => {
  const out = userMdHtml("para one\n\npara two");
  assert.equal((out.match(/<p>/g) || []).length, 2);
  assert.doesNotMatch(out, /<br>/);
});

test("a fenced code block keeps its literal newlines and gains no <br>", () => {
  const out = userMdHtml("```\nfirst\nsecond\n```");
  assert.match(out, /<pre><code>first\nsecond\n<\/code><\/pre>/);
  assert.doesNotMatch(out, /<br>/);
});

test("a list stays a list; an indented pasted snippet stays code", () => {
  const list = userMdHtml("- a\n- b");
  assert.equal((list.match(/<li>/g) || []).length, 2);
  assert.doesNotMatch(list, /<br>/);
  const snippet = userMdHtml("see:\n\n    x = 1\n    y = 2");
  assert.match(snippet, /<pre><code>x = 1\ny = 2\n<\/code><\/pre>/);
});

test("the chat grammar rides along: ~~double~~ strikes, a lone ~ stays literal", () => {
  assert.match(userMdHtml("this is ~~struck~~ out"), /<del>struck<\/del>/);
  const lone = userMdHtml("near the ~21 Wh budget, ~1.5 days");
  assert.doesNotMatch(lone, /<del>/);
  assert.match(lone, /~21/);
});

test("the chat grammar rides along: $x$ still becomes math, and a price stays a price", () => {
  // math.ts emits an inert placeholder carrying the TeX; KaTeX is rendered into it after the sanitizer, by
  // renderMathPlaceholders as a sanitizeMd post-pass this module registers at load (render.ts's userMd() calls
  // sanitizeMd and nothing of its own), so marked's own output holds the placeholder, never KaTeX's markup
  const out = userMdHtml("Euler: $e^{i\\pi}+1=0$\nnext line");
  assert.ok(out.includes('<span class="md-math-inline">e^{i\\pi}+1=0</span>'), "inline math becomes the placeholder: " + out);
  assert.match(out, /<br>\s*next line/, "…and the newline after it is still kept");
  const price = userMdHtml("costs $5 and $10 today");
  assert.ok(!price.includes("md-math"));
  assert.match(price, /\$5/);
});

test("the user renderer and the reply renderer produce identical HTML when there is no newline, a path's underscores included", () => {
  // the two chat instances (chat-md.ts: the contract that they agree on everything except line breaks), compared as
  // shipped: chatMdHtml is what render.ts's md() parses through, userMdHtml what userMd() does. The path row exercises
  // the override both take; the singleton pairs its underscores (the viewer's rendering, pinned in
  // md-emphasis-paths.test.ts's boundary test), so the row is not vacuous for the grammar the chat ships. The 75-row
  // form of this pin is md-emphasis-paths.test.ts (the user's own words take the same grammar); this is the short one.
  const PATH_ROW = "see /a-_b/c_/d.md today";
  for (const src of ["plain words", "**bold** and `code`", "a [link](https://example.test) here", "~~gone~~ $x$", PATH_ROW]) {
    assert.equal(userMdHtml(src), chatMdHtml(src), src);
  }
  assert.notEqual(singletonHtml(PATH_ROW), chatMdHtml(PATH_ROW), "the path row tells the chat's grammar from the singleton's: " + singletonHtml(PATH_ROW));
  assert.doesNotMatch(chatMdHtml(PATH_ROW), /<em>/, "the reply instance keeps the path's underscores literal");
});

// --- source pins: the wiring in render.ts ---

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");

test("the singleton is configured in one place and stays breaks:false; render.ts configures nothing of its own; the user instance takes the singleton's list plus the chat's override", () => {
  // the singleton's options live in md-config.ts since Slice 4 of plans/markdown-viewer.md (one configuration for every
  // bundle); render.ts applies them and configures nothing of its own, and the user instance takes the same list plus
  // pathAwareEmphasis, as the reply instance does (chat-md.ts; render.ts's md() parses through chatMdHtml since 2026-09-19)
  const CONFIG = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "md-config.ts"), "utf8");
  assert.match(CONFIG, /marked\.setOptions\(\{ gfm: true, breaks: false \}\);\n\s*marked\.use\(\.\.\.mdExtensions\);/, "the one place the singleton is configured");
  assert.match(RENDER, /^applyMdConfig\(\);/m, "render.ts applies the one configuration");
  assert.doesNotMatch(RENDER, /marked\.(setOptions|use)\(/, "…and configures nothing of its own");
  const GRAMMAR = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "chat-md.ts"), "utf8");
  assert.match(GRAMMAR, /export const userMarked = new Marked\(\{ gfm: true, breaks: true \}, \.\.\.mdExtensions, pathAwareEmphasis\);/, "the user instance takes the same grammar the singleton does, with hard breaks and the chat's path-aware emphasis (md-emphasis-paths.test.ts)");
});

test("userMd() renders through the breaks:true instance and the SAME sanitizer as md()", () => {
  // both renderers take the sanitized DOM back to link PR references before serializing (pr-links.ts); the
  // sanitizer is sanitizeMd (md-sanitize.ts, since Slice 1 of plans/markdown-viewer.md), one call shared with the
  // file viewer, which returns the sanitized <body>; the profile is spelled there and nowhere in render.ts. Both
  // signatures carry an optional repo parameter for the PR links, so the match on them is loose.
  const fn = RENDER.match(/function userMd\(src: string[^\n]*?\): string \{[\s\S]*?\n\}/)?.[0] || "";
  assert.ok(fn, "userMd() must exist");
  assert.match(fn, /const clean = sanitizeMd\(userMdHtml\(src\)\);/);
  const mdFn = RENDER.match(/function md\(src: string[^\n]*?\): string \{[\s\S]*?\n\}/)?.[0] || "";
  assert.match(mdFn, /const clean = sanitizeMd\(dirty\);/, "md() sanitizes through the same shared call");
  assert.match(RENDER, /import \{[^}]*\bsanitizeMd\b[^}]*\} from "\.\/md-sanitize";/);
  assert.doesNotMatch(RENDER, /from "dompurify"|DOMPurify\.sanitize|MD_PURIFY/, "render.ts holds no sanitizer of its own");
  const SAN = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "md-sanitize.ts"), "utf8");
  assert.match(SAN, /USE_PROFILES: \{ html: true, svg: true \},\n\s*ADD_DATA_URI_TAGS: \["img"\],\n\s*ALLOW_DATA_ATTR: false,/);
  assert.doesNotMatch(fn + mdFn, /USE_PROFILES|ALLOW_DATA_ATTR/, "neither renderer spells its own profile: every option comes through md-sanitize.ts");
});

test("the user bubble renders the user's OWN words with userMd, harness notes and everything else with md", () => {
  // the landed bubble: kind "user" → userMd; the harness-injected note sharing the branch → md
  assert.match(RENDER, /bubble\.innerHTML = kind === "user" \? userMd\(ev\.md\) : md\(ev\.md\);\n\s*linkifyFileUris\(bubble, imgPaths, ev\.spacePaths, ev\.pathLinks, ev\.pathPins, ev\.pathPreview, ev\.pathPreviewWhy\);/);
  assert.doesNotMatch(RENDER, /bubble\.innerHTML = md\(ev\.md\);/, "no user bubble left on the soft-wrap grammar");
  // the queued / optimistic bubble is the same message a beat earlier — same renderer, so the swap to the
  // landed bubble changes nothing on screen
  assert.match(RENDER, /if \(!t\.romp && !isCmd\) bubble\.innerHTML = userMd\(t\.md\);/);
  assert.doesNotMatch(RENDER, /bubble\.innerHTML = md\(t\.md\);/);
  // romp-authored surfaces keep the assistant grammar: nudges, notices, the Continue gesture, tagged sends
  assert.match(RENDER, /full\.innerHTML = md\(raw\);/, "the romp nudge fold");
  assert.match(RENDER, /if \(more\) body\.innerHTML = md\(text\);[^\n]*\n\s*return notice\(\{ src: "romp", glyph: "romp", sev: "romp"/, "the romp system notice (a one-liner gets no body, T243; the one builder since 2026-09-08)");
});
