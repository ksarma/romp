// Review comments in the file viewer (the user 2026-08-14): comment on passages while you read, then
// ONE Submit hands the whole set to the session as a single message drafted into the composer.
//
// This layer rides ON the viewer main already had (file-view.ts) rather than shipping a second reader.
// No jsdom for these renderers (the repo convention), so the contract is pinned at source — with two
// tests that exist because source pins alone once let a completely unusable feature through: the menu
// has to be REACHABLE (bound on the viewer body) and VISIBLE (above the viewer's own backdrop).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const here = (...p: string[]) => path.resolve(process.cwd(), "..", ...p);
const VIEW = fs.readFileSync(here("ui", "webview", "file-view.ts"), "utf8");
const RENDER = fs.readFileSync(here("ui", "webview", "render.ts"), "utf8");
const FEED = fs.readFileSync(here("ui", "webview", "feed.ts"), "utf8");
const CSS = fs.readFileSync(here("ui", "webview", "styles.css"), "utf8");

test("the layer rides on main's viewer — no second reader, no second route", () => {
  assert.ok(!fs.existsSync(here("ui", "webview", "docreview-reader.ts")), "no rival reader module");
  assert.doesNotMatch(RENDER, /openDocReview/, "render.ts must not carry its own doc reader");
  const KERNEL = fs.readFileSync(here("kernel", "kernel.py"), "utf8");
  assert.doesNotMatch(KERNEL, /_doc_source|_DOC_EXT/, "/file already serves text — no rival /doc route");
});

test("comments are keyed per session AND per file, and persist across a reload", () => {
  assert.match(VIEW, /const key = docKey\(sid \|\| "", path\);/);
  assert.match(VIEW, /const CMT_KEY = "romp:fileviewComments";/);
  assert.match(VIEW, /localStorage\.setItem\(CMT_KEY, JSON\.stringify\(Object\.fromEntries\(comments\)\)\)/);
  assert.match(VIEW, /loadComments\(\);/);
});

test("right-click on a selection offers Comment — bound on the viewer body so it is REACHABLE", () => {
  // The regression: bound on the wrong element, the browser's native menu wins and the only gesture
  // that makes a comment does nothing at all (2026-08-18).
  assert.match(VIEW, /body\.addEventListener\("contextmenu"/);
  assert.match(VIEW, /!body\.contains\(sel\.anchorNode\)\) return;/);
  assert.match(VIEW, /item\("Comment", \(\) => askComment\(picked\)\);/);
});

test("that menu clears the viewer's own backdrop, or it is invisible", () => {
  // The other half of the same regression: .ctx-menu is z-100, the viewer's backdrop far above it,
  // so an unlifted menu renders BEHIND the panel it belongs to. Compare the two, never hardcode.
  const menuZ = Number(CSS.match(/\.ctx-menu\.fv-menu \{ z-index: (\d+); \}/)![1]);
  const backZ = Number(CSS.match(/#romp-fileview \{ position: fixed; inset: 0; z-index: (\d+);/)![1]);
  assert.ok(menuZ > backZ, `menu z-index ${menuZ} must exceed the viewer backdrop's ${backZ}`);
});

test("Submit DRAFTS one assembled message — it never sends, and never clobbers a draft", () => {
  const fn = VIEW.slice(VIEW.indexOf('submitBtn.addEventListener("click"'));
  const body = fn.slice(0, fn.indexOf("\n  });"));
  assert.match(body, /buildReviewMessage\(path, list\)/);
  assert.match(body, /commentSink!\(/);
  assert.doesNotMatch(body, /sendMessage/, "Submit drafts; the person sends");
  // the composer side appends and remembers the draft (sid-routed since 2026-08-19 —
  // docreview.test.ts pins the routing + the preserve-on-failure contract)
  const sink = RENDER.slice(RENDER.indexOf("setCommentSink((sid, text) => {"));
  const sinkBody = sink.slice(0, sink.indexOf("\n});"));
  assert.match(sinkBody, /ta\.value = ta\.value \+ sep \+ text;/);
  assert.match(sinkBody, /drafts\.set\(sid, ta\.value\);/);
  assert.match(sinkBody, /persistDrafts\(\);/);
});

test("the click is acknowledged before the round trip", () => {
  assert.match(VIEW, /submitBtn\.disabled = true;\s*\n\s*submitBtn\.textContent = "Submitting/);
});

test("a file that changed under the reader is called out, not silently mis-numbered", () => {
  // …compared against the text THE VIEW SHOWS — the SVG Source view's decoded XML, or the text
  // pipeline's bytes (viewText, pinned below) — so an SVG review isn't declared stale against null
  assert.match(VIEW, /\.then\(\(fresh\) => fresh !== viewText\(\)\)/);
  assert.match(VIEW, /the file changed while I was reading it/);
  // a failed re-read must not fabricate staleness nobody observed
  assert.match(VIEW, /\.catch\(\(\) => false\)/);
});

test("marks reuse the chat threads' re-anchoring, so a span found in Rendered survives Raw", () => {
  assert.match(VIEW, /findAnchorRange\(nodes\.map\(\(t\) => t\.data\)\.join\(""\), c\.quote\)/);
  assert.match(VIEW, /sliceRanges\(nodes\.map\(\(t\) => t\.data\.length\), r\.start, r\.end\)/);
  assert.match(VIEW, /markComments\(\);/);
  assert.match(CSS, /mark\.fv-hl \{/);
});

test("the comment's text is one click under its number (progressive disclosure)", () => {
  assert.match(VIEW, /function showNote\(c: DocComment, at: HTMLElement\)/);
  assert.match(VIEW, /const same = open\?\.dataset\.dcid === c\.id;/);   // same marker toggles it shut
  assert.match(CSS, /\.fv-note \{/);
});

test("the review controls stay hidden until this file actually has a comment", () => {
  assert.match(VIEW, /cmtCount\.hidden = !n;\s*\n\s*submitBtn\.hidden = !n;/);
});

test("the viewer does not import render.ts — the sink is registered inward", () => {
  assert.doesNotMatch(VIEW, /from "\.\/render"/, "that would be an import cycle");
  assert.match(VIEW, /export function setCommentSink/);
  assert.match(RENDER, /import \{ openFileView, setCommentSink \} from "\.\/file-view";/);
});

// ── sink gating (2026-08-19): the FEED document hosts this same viewer (the file browser opens
// through it) but never registers a sink — Submit there had nowhere to deliver and was a dead
// button. The fix is honest gating, not a fake relay: no sink, no comment affordances at all —
// no real target, no control. ──

test("no sink registered → the viewer offers NO comment affordances (the feed-hosted viewer)", () => {
  // the feed boots the viewer for saves but never registers a sink; render.ts does
  assert.match(FEED, /initFileView\(/);
  assert.doesNotMatch(FEED, /setCommentSink/, "the feed has no composer to draft into");
  assert.match(RENDER, /setCommentSink\(\(sid, text\) => \{/, "the chat bundle keeps the full behavior");
  // the contextmenu never opens (the native menu already carries Copy), the marks never paint,
  // and the count/Submit stay hidden however many comments the store holds for this file
  assert.match(VIEW, /body\.addEventListener\("contextmenu", \(ev\) => \{\s*\n\s*if \(!commentSink\) return;/);
  assert.match(VIEW, /syncReview\(\);\s*\n\s*if \(!commentSink\) return;/);
  assert.match(VIEW, /const n = commentSink \? \(comments\.get\(key\) \|\| \[\]\)\.length : 0;/);
});

// executed: syncReview's visibility rule — a stored count surfaces only where a sink can carry it
test("review controls: hidden without a sink even when the store already holds comments", () => {
  const visible = (sink: unknown, stored: number): boolean => !!(sink ? stored : 0);
  assert.equal(visible(null, 3), false, "authored-elsewhere comments stay invisible here");
  assert.equal(visible(() => { /* sink */ }, 3), true, "with a sink, the count shows as before");
  assert.equal(visible(() => { /* sink */ }, 0), false, "…and still hides until a comment exists");
});

// ── media gating is RENDERED-media gating (review 2026-08-25): pre-image-mode an .svg rendered as
// highlighted XML with a WORKING comment layer, and image mode's blanket media gate stranded any
// stored un-submitted comments on it invisible. The gate's rationale — "no text nodes" — is true
// of the img/PDF surfaces only: the SVG SOURCE view is codeBlock output, real text nodes, so there
// the contextmenu Comment, the marks, the count and Submit work exactly as any text view. ──

test("comments gate off RENDERED media only — the SVG Source view is a text view like any other", () => {
  // executed: the contextmenu offer across the view states (the sink gate holds throughout)
  const commentable = (sink: boolean, isImage: boolean, isPdf: boolean, srcView: boolean): boolean =>
    sink && !((isImage || isPdf) && !srcView);
  assert.equal(commentable(true, true, false, true), true, "SVG Source view: Comment is offered");
  assert.equal(commentable(true, true, false, false), false, "the img view has no text nodes to anchor to");
  assert.equal(commentable(true, false, true, false), false, "the PDF iframe owns its own surface");
  assert.equal(commentable(false, true, false, true), false, "no sink still gates everything off");
  assert.equal(commentable(true, false, false, false), true, "plain text views are untouched");
  // source: the media arm of the contextmenu gate carves out the Source view — sitting AFTER the
  // no-sink gate, whose first-line position the sink-gating test above pins
  assert.match(VIEW, /if \(!commentSink\) return;.*\n\s*if \(\(isImage \|\| isPdf\) && !\(svgSource && svgText !== null\)\) return;/);
  // the Source view renders codeBlock THEN runs the comment pass — marks, count, Submit, delivering
  // any stranded stored comments; the img/PDF arm below it stays comment-free (file-view.test.ts
  // pins that arm's side)
  const mediaBranch = VIEW.split("if (isImage || isPdf) {")[1].split("if (text === null || editing) return;")[0];
  const srcArm = (mediaBranch.split("if (svgSource && svgText !== null) {")[1] || "").split("\n      }")[0];
  assert.ok(srcArm, "the Source-view arm exists inside the media branch");
  assert.match(srcArm, /body\.replaceChildren\(codeBlock\(svgText, path, fmt\.wrap\)\);/);
  assert.match(srcArm, /markComments\(\);/, "the comment pass runs in the Source view");
  // anchoring and Submit read the text THE VIEW SHOWS — the Source view's decoded XML, never the
  // text pipeline's null — so a comment on the XML anchors to its line, and Submit's staleness
  // check compares like against like
  assert.match(VIEW, /const viewText = \(\): string \| null => \(svgSource && svgText !== null \? svgText : text\);/);
  assert.match(VIEW, /anchorFor\(viewText\(\) \|\| "", picked\)/);
  assert.match(VIEW, /\.then\(\(fresh\) => fresh !== viewText\(\)\)/);
});

// ── Submit during an edit: the delivery tail used to closeFileView() unconditionally, so a dirty
// editor's close guard popped "Discard unsaved changes?" over a SUBMIT — and Cancel then stranded
// the button at "Submitting…" with a stale count (renderBody early-returns while editing, so
// syncReview never reran). Two arms (landed / failed) × two states (editing / not) — all four
// cells pinned here and below. ──

test("Submit while editing delivers and resets IN PLACE — never the courtesy close or its confirm", () => {
  const fn = VIEW.slice(VIEW.indexOf('submitBtn.addEventListener("click"'));
  const body = fn.slice(0, fn.indexOf("\n  });"));
  // the store clears ONLY on the landed arm — the comments were delivered
  assert.match(body, /comments\.delete\(key\);\s*\n\s*saveComments\(\);/);
  // the editing arm re-arms the button and re-syncs the two controls, then STOPS: closeFileView
  // (and with it the discard confirm) is reachable only from the non-editing arm
  assert.match(body, /if \(editing\) \{\s*\n\s*submitBtn\.disabled = false;\s*\n\s*syncReview\(\);\s*\n\s*return;\s*\n\s*\}\s*\n\s*closeFileView\(\);/);
  // no confirm can originate from Submit, and the edit buffer is never read or written
  assert.doesNotMatch(body, /confirmDiscard|window\.confirm/);
  assert.doesNotMatch(body, /\bta\b/, "the submit path leaves the editor's textarea untouched");
});

test("a FAILED handoff mid-edit keeps the comments AND the buffer — the arm touches only the button", () => {
  // the fourth cell of the 2x2 (failed × editing), covered nowhere else: the !landed arm must not
  // close, re-render, or clear — any of those would eat the textarea (renderBody) or the review
  // (comments.delete) on a handoff that delivered NOTHING
  const fn = VIEW.slice(VIEW.indexOf('submitBtn.addEventListener("click"'));
  const body = fn.slice(0, fn.indexOf("\n  });"));
  const at = body.indexOf("if (!landed) {");
  assert.ok(at >= 0, "the failed-handoff arm exists");
  const arm = body.slice(at, body.indexOf("comments.delete(key);"));
  assert.ok(at < body.indexOf("comments.delete(key);"), "…ahead of the delivery tail");
  assert.match(arm, /submitBtn\.disabled = false;/);
  assert.match(arm, /Couldn't draft it — comments kept, try again/);
  assert.match(arm, /return;/);
  assert.doesNotMatch(arm, /closeFileView|renderBody|exitEdit|comments\.delete|saveComments/,
    "no close, no re-render, no store clear — mid-edit the buffer survives a failed handoff");
});
