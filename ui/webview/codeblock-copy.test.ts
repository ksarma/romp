// Every rendered code block in the chat carries an automatic "Copy" button (the user 2026-06-22). It's
// added inside highlight() — the one post-processor over `pre code` — so it covers ALL render paths
// (assistant body, agent report, postal body, diffs) for free. The RAW source is captured BEFORE the
// markup is rewritten (line-wrapping drops the \n joins, so the on-screen textContent isn't copy-safe).
// No jsdom harness here — like codeblock-wrap.test.ts, pin the behaviour at the source level. addCopyBtn and copyText
// live in code-block.ts since Slice 3 of plans/markdown-viewer.md (the viewer's mdBlock shares them; code-block.test.ts
// runs the module), and highlight() imports them.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "styles.css"), "utf8");

const HL = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "highlight-cache.ts"), "utf8");
const BLOCK = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "code-block.ts"), "utf8");

test("highlight() captures the raw source then adds a Copy button to each <pre>", () => {
  // raw is captured BEFORE innerHTML is rewritten, and hljs highlights that same captured string — through
  // the (language, source) cache since 2026-09-06 (highlight-cache.ts), which still names a grammar for a
  // labeled fence and auto-detects an unlabeled one
  assert.match(RENDER, /const raw = code\.textContent \|\| "";/);
  assert.match(RENDER, /code\.innerHTML = highlightHtml\(hljs, lang, raw\);/);
  assert.match(HL, /hl\.highlight\(raw, \{ language: lang as string \}\)/);
  assert.match(HL, /hl\.highlightAuto\(raw, AUTO_LANGUAGES\)/);   // among the chat's ten, not the viewer's sixteen (code-block.test.ts pins the list)
  // the button is added per code block, to its parent <pre>, with the captured raw
  assert.match(RENDER, /if \(pre && pre\.tagName === "PRE"\) addCopyBtn\(pre as HTMLElement, raw\)/);
  assert.match(RENDER, /import \{ wrapCodeLines, addCopyBtn \} from "\.\/code-block";/, "the two live in code-block.ts (the viewer shares them)");
  assert.doesNotMatch(RENDER, /function (addCopyBtn|wrapCodeLines|copyText|fallbackCopy)\(/, "render.ts keeps no copy of its own");
});

test("addCopyBtn builds a .code-copy button, is idempotent, and shows Copied feedback", () => {
  assert.match(BLOCK, /export function addCopyBtn\(pre: HTMLElement, raw: string\)/);
  assert.match(BLOCK, /if \(pre\.querySelector\(":scope > \.code-copy"\)\) return;/);  // never doubles up on a re-render
  assert.match(BLOCK, /el\("button", "code-copy"\)/);
  assert.match(BLOCK, /copyText\(raw\)/);
  assert.match(BLOCK, /btn\.textContent = ok \? "Copied" : "Copy failed"/);
  assert.match(BLOCK, /btn\.classList\.toggle\("copied", ok\)/);
});

test("copyText uses the async Clipboard API with an execCommand fallback", () => {
  assert.match(BLOCK, /navigator\.clipboard\.writeText\(text\)/);
  assert.match(BLOCK, /function fallbackCopy\(text: string\)/);
  assert.match(BLOCK, /document\.execCommand\("copy"\)/);
});

test("the Copy button is styled: anchored top-right, faint until hover, green when copied", () => {
  assert.match(CSS, /pre\.has-copy \{[^}]*position: relative/);                 // anchors the absolute button
  assert.match(CSS, /\.code-copy \{[^}]*position: absolute/);
  assert.match(CSS, /\.code-copy \{[^}]*opacity: 0;/);                          // hidden by default
  assert.match(CSS, /pre\.has-copy:hover \.code-copy[^{]*\{[^}]*opacity: 0\.9/); // revealed on block hover
  assert.match(CSS, /\.code-copy\.copied \{[^}]*color: var\(--green\)/);        // success = green
  assert.match(CSS, /@media \(hover: none\) \{ \.code-copy \{ opacity: 0\.8/);  // touch has no hover → stays visible
});
