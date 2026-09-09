// Every rendered code block in the chat carries an automatic "Copy" button (the user 2026-06-22). It's
// added inside highlight() — the one post-processor over `pre code` — so it covers ALL render paths
// (assistant body, agent report, postal body, diffs) for free. The RAW source is captured BEFORE the
// markup is rewritten (line-wrapping drops the \n joins, so the on-screen textContent isn't copy-safe).
// No jsdom harness here: like codeblock-wrap.test.ts, pin the behaviour at the source level. addCopyBtn and copyText
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
  // the (language, source) cache (highlight-cache.ts), which still names a grammar for a labeled fence and
  // auto-detects an unlabeled one
  assert.match(RENDER, /const raw = code\.textContent \|\| "";/);
  assert.match(RENDER, /code\.innerHTML = highlightHtml\(hljs, lang, raw\);/);
  assert.match(HL, /hl\.highlight\(raw, \{ language: lang as string \}\)/);
  assert.match(HL, /hl\.highlightAuto\(raw, AUTO_LANGUAGES\)/);   // among the chat's ten, not the viewer's sixteen (code-block.test.ts pins the list)
  // the button is added per code block, to its parent <pre>, with the captured raw
  assert.match(RENDER, /if \(pre && pre\.tagName === "PRE"\) addCopyBtn\(pre as HTMLElement, raw\)/);
  assert.match(RENDER, /import \{ wrapCodeLines, addCopyBtn \} from "\.\/code-block";/, "the two live in code-block.ts (the viewer shares them)");
  assert.doesNotMatch(RENDER, /function (addCopyBtn|wrapCodeLines|copyText|fallbackCopy)\(/, "render.ts keeps no copy of its own");
});

test("addCopyBtn builds a .code-copy button, is idempotent, and shows Copied feedback on the button on screen", () => {
  assert.match(BLOCK, /export function addCopyBtn\(pre: HTMLElement, raw: string\)/);
  assert.match(BLOCK, /if \(pre\.querySelector\(":scope > \.code-copy"\)\) return;/);  // never doubles up on a re-render
  assert.match(BLOCK, /el\("button", "code-copy"\)/);
  // the fence's source (the text its Copy copies) and its ancestors are read at the press, while the button is in the
  // document, and the acknowledgement goes to the button on screen of the fence with that source: a held landing swaps
  // the pressed one out a tick after its click, and the async Clipboard API answers after the swap (Slice 3 review,
  // round 3; file-view-copy-ack-browser.test.ts runs it). By source, not by index among the fenced blocks: a write that
  // put a fence above the pressed one marked the new fence (the final fixes; file-view-copy-held-browser.test.ts scenes
  // 5 and 6)
  assert.match(BLOCK, /const SOURCES = new WeakMap<Element, string>\(\);/);
  assert.match(BLOCK, /pre\.classList\.add\("has-copy"\);\n\s*SOURCES\.set\(pre, raw\);/, "every dressed fence records its source");
  assert.match(BLOCK, /const slot = fenceSlot\(pre, raw\);[^\n]*\n\s*copyText\(raw\)\.then\(\(ok\) => acknowledge\(btn, slot, ok\)\);/);
  assert.match(BLOCK, /function shownButton\(pressed: HTMLButtonElement, slot: Slot\): HTMLButtonElement \| null \{\n\s*if \(pressed\.isConnected\) return pressed;/);
  assert.match(BLOCK, /const same = sameSource\(s\.root, slot\.source\);\n\s*const pre = same\[Math\.min\(s\.nth, same\.length - 1\)\];/, "the fence with the pressed fence's source; of several, the pressed one's ordinal among them; none, no button");
  assert.match(BLOCK, /const b = shownButton\(pressed, slot\);\n\s*if \(!b \|\| b === shown\) return;\n\s*shown = b;\n\s*b\.textContent = ok \? "Copied" : "Copy failed";\n\s*b\.classList\.toggle\("copied", ok\);/);
  // a swap inside the window carries the label to the replacement on the swap's own event, and the window's close
  // resets the button last acknowledged
  assert.match(BLOCK, /const swaps = new MutationObserver\(place\);\n\s*for \(const \{ root \} of slot\.at\) swaps\.observe\(root, \{ childList: true \}\);/);
  assert.match(BLOCK, /swaps\.disconnect\(\);\n\s*if \(shown\) \{ shown\.textContent = "Copy"; shown\.classList\.remove\("copied"\); \}/);
  assert.match(BLOCK, /for \(let a = pre\.parentElement; a && a !== document\.body; a = a\.parentElement\)/, "the walk stops under document.body: a surface swapped out whole is nothing to acknowledge on");
});

test("addCopyBtn: Space acts on the keydown, the key's default prevented on the keydown and the keyup, a held key's repeats the same press", () => {
  // a button's Space click is native to the keyup, so a rebuild between the keydown and the keyup took the focused button
  // and the keyup clicked nothing (Slice 3 review, round 2); the button acts on the keydown, as Enter does, and the
  // prevented keydown keeps it out of :active for the key (file-view-copy-space-browser.test.ts runs it over the viewer)
  assert.match(BLOCK, /btn\.addEventListener\("keydown", \(ev\) => \{\n\s*if \(ev\.key !== " "\) return;\n\s*ev\.preventDefault\(\);\n\s*if \(ev\.repeat\) return;\n\s*copy\(\);\n\s*\}\);/);
  assert.match(BLOCK, /btn\.addEventListener\("keyup", \(ev\) => \{ if \(ev\.key === " "\) ev\.preventDefault\(\); \}\);/);
  assert.match(BLOCK, /btn\.addEventListener\("click", \(ev\) => \{\n\s*ev\.preventDefault\(\); ev\.stopPropagation\(\);\n\s*copy\(\);\n\s*\}\);/, "the click and the key share one copy()");
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
