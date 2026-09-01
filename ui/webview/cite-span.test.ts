// T218's render half (the manager's 87-pair anchor study): the summary deep link now carries the
// distiller's located supporting SPAN, and the landing scrolls to and highlights the sentence
// inside the (often long, multi-topic) cited message. Pins: the payload gate, the click's quote,
// the kernel focus passthrough, the highlight's zero-DOM-surgery mechanism with honest fallbacks,
// and the paint. The judge half (labels on substantive non-prose atoms, the QUOTE protocol, the
// write-time locate) lives in tests/test_cite_substance.py + the distill goldens.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const UI = path.resolve(process.cwd(), "..", "ui", "webview");
const FEED = fs.readFileSync(path.join(UI, "feed.ts"), "utf8");
const RENDER = fs.readFileSync(path.join(UI, "render.ts"), "utf8");
const CSS = fs.readFileSync(path.join(UI, "styles.css"), "utf8");
const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");
const JUDGE = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "judge.py"), "utf8");

test("the span rides the payload only while the cited atom IS the landing", () => {
  assert.match(KERNEL, /"summaryAnchorQuote": \(nodes\[nid\]\.get\("summaryQuote"\)\s*\n\s*if _sa_u and _sa_u == nodes\[nid\]\.get\("summaryAnchor"\) else None\)/,
    "a fallback-tier anchor lands elsewhere — its quote would highlight the wrong text");
  assert.match(FEED, /summaryAnchorQuote\?: string \| null;/);
  assert.match(FEED, /anchorUuid: it\.summaryAnchorUuid, quote: it\.summaryAnchorQuote \|\| undefined/,
    "the click carries the span");
  assert.match(KERNEL, /f\["anchorQuote"\] = str\(msg\["quote"\]\)\[:300\]/, "the focus frame passes it through");
});

test("the landing highlights with zero DOM surgery, and falls back honestly", () => {
  assert.match(RENDER, /pendingAnchorQuote = typeof \(m as \{ anchorQuote\?: string \}\)\.anchorQuote === "string"/);
  assert.match(RENDER, /if \(pendingAnchorQuote\) \{ highlightCiteSpan\(target, pendingAnchorQuote\); pendingAnchorQuote = null; \}/,
    "consumed exactly at the successful landing — an honest-fail never strands a stale span");
  const fn = RENDER.slice(RENDER.indexOf("function highlightCiteSpan"), RENDER.indexOf("function landOn"));
  assert.match(fn, /CSS as unknown as \{ highlights\?: Map<string, unknown> \}/,
    "the CSS Custom Highlight API — the ever-re-rendering turn list is never mutated");
  assert.match(fn, /if \(!H \|\| typeof Highlight === "undefined"\) return;/, "no API → today's whole-message landing");
  assert.match(fn, /if \(!m\) return;\s*\/\/ unfindable in the rendered text → no highlight, no guess/);
  assert.match(fn, /scrollIntoView\(\{ block: "center", behavior: "auto" \}\)/, "land ON the sentence, not the message top");
  assert.match(CSS, /::highlight\(cite-span\) \{ background-color: rgba\(156, 210, 255, 0\.30\);/,
    "accent-tinted, never a status colour");
});

test("substantive non-prose atoms are citable — the study's convicted classes", () => {
  assert.match(JUDGE, /isinstance\(a\.get\("author"\), dict\)/, "a PEER postal report takes a label at the prose floor");
  assert.match(JUDGE, /_PR_LINK_RE = re\.compile\(r"https:\/\/github\\\.com\/\\S\+\/\(\?:pull\|commit\|compare\)\/\\S\+"\)/,
    "a PR/commit-link tool result is substance by construction");
  assert.match(JUDGE, /out\.append\("RESULTS: " \+ " \| "\.join\(results\[:4\]\)\)/);
  assert.match(JUDGE, /def _store_cited_span\(nd, marks, src, quote\):/, "the span stores only with a RESOLVED citation");
});
