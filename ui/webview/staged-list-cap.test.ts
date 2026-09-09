// The staged strip above the composer (the user 2026-09-08, whose twelve staged comments filled the page
// below the tab strip and the background-wait box and pushed the transcript out of view): the items sit
// in their own list under the head, about four items tall, scrolling beyond; the head with the count and
// Send now stays outside the scroll; a caret folds the strip to the head line. And the run goes out as
// ONE message (the same user, who wanted staged comments to land as one message, not a series):
// flushStaged routes the posts stagedPosts folds the staged items and the typed message into. Review round
// 1 (2026-09-09): staging reveals the new item, the kept scroll offset is per tab, the caret keeps focus
// across the rebuild, an expanded long token wraps instead of scrolling the list sideways, and a slash
// command or a goal follow-up goes on its own at its place in stage order. No jsdom for the chat
// renderer, so the DOM and CSS are pinned at the source; the post list itself is executed in
// staged-messages.test.ts.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "styles.css"), "utf8");
const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const STRIP = RENDER.split("function renderStagedStrip(")[1].split("\nfunction ")[0];
const FLUSH = RENDER.split("function flushStaged(")[1].split("\nfunction ")[0];
const LIST = (CSS.match(/\.staged-list \{[^}]*\}/) || [""])[0];

test("the staged items live in .staged-list, capped at about four items (209px) with its own scroll", () => {
  assert.match(LIST, /max-height: 209px;/, "four items of 50px (a quote pill and a comment row each) plus three 3px gaps");
  assert.match(LIST, /overflow-y: auto;/, "the scroll is the list's own");
  assert.match(LIST, /overflow-x: hidden;/, "never sideways: the pane's rule for every scroll container (body overflow-x hidden no longer reaches inside the list)");
  assert.match(LIST, /overscroll-behavior: contain;/, "a wheel at the end never scrolls the page");
  assert.match(LIST, /display: flex; flex-direction: column; gap: 3px;/, "the chips keep the strip's column and gap");
  // the cap is on the LIST, never on the strip or the head: the head must stay visible above the scroll.
  // Any rule whose selector list names the strip or the head, the shared width rule included ([^{}]*
  // spans a selector list, not a rule boundary); a descendant rule under the strip id would trip it too,
  // so nest the list under the id only with the pin narrowed, never loosened
  assert.doesNotMatch(CSS, /#composer-staged[^{}]*\{[^}]*max-height/);
  assert.doesNotMatch(CSS, /\.staged-head[^{}]*\{[^}]*max-height/);
  // the arithmetic's inputs, so a geometry change here fails loudly instead of quietly showing three or five
  assert.match(CSS, /\.staged-chip \{[^}]*border: 1px dashed[^}]*padding: 2px 6px; font-size: 12px;/);
  assert.match(CSS, /\.staged-chip \{[^}]*gap: 2px;/);
  assert.match(CSS, /\.composer-chip \{[^}]*padding: 2px 4px 2px 8px; font-size: 12px; line-height: 1\.4;/);
  assert.match(CSS, /html, body \{[^}]*line-height: 1\.6;/);
  assert.match(CSS, /#composer-staged \{ flex-direction: column; gap: 3px;/);
});

test("the head (count + Send now) is appended to the strip, the chips to the list, the list after the head", () => {
  assert.match(STRIP, /head\.append\(car, lbl, go\);\s*\n\s*strip\.appendChild\(head\);/);
  assert.match(STRIP, /const box = el\("div", "staged-list"\);/);
  assert.match(STRIP, /box\.appendChild\(chip\);\s*\n\s*\}\);\s*\n\s*strip\.appendChild\(box\);/);
  assert.doesNotMatch(STRIP, /strip\.appendChild\(chip\)/, "no chip lands outside the scrolling list");
});

test("staging reveals the new item; expand, collapse, discard and the fold keep the list's place, kept per tab", () => {
  // the STAGE path is the one caller with the reveal intent (the new item is the event that justifies the
  // move); with the kept offset, every item staged past the fourth landed below the list's edge, unseen
  assert.match(STRIP, /^id: string \| null, opts\?: \{ reveal\?: "last" \}\): void \{/);
  assert.match(RENDER, /stagedMsgs\.push\(activeId, \{ text: typed, cites: \(composerCitations\.get\(activeId\) \|\| \[\]\)\.slice\(\) \}\);[\s\S]*?renderStagedStrip\(activeId, \{ reveal: "last" \}\);/);
  assert.equal((RENDER.match(/renderStagedStrip\(\w+, \{ reveal/g) || []).length, 1, "only the stage path reveals; every other rebuild keeps the place");
  // written after the new list is in the DOM (a detached node has no layout); the reveal clamps to the end
  assert.match(STRIP, /strip\.appendChild\(box\);\s*\n\s*box\.scrollTop = opts\?\.reveal === "last" \? box\.scrollHeight : \(stagedScroll\.get\(id\) \|\| 0\);/);
  // the kept offset is PER TAB: read off the list the strip holds BEFORE replaceChildren and stored under
  // the sid that built it (strip.dataset.sid), so a switch never writes the leaving tab's offset onto the
  // entering tab's list; an emptied list forgets its place
  assert.match(RENDER, /const stagedScroll = new Map<string, number>\(\);/);
  assert.match(STRIP, /const prevList = strip\.querySelector\("\.staged-list"\) as HTMLElement \| null;\s*\n\s*if \(prevList && strip\.dataset\.sid\) stagedScroll\.set\(strip\.dataset\.sid, prevList\.scrollTop\);\s*\n\s*strip\.replaceChildren\(\);/);
  assert.match(STRIP, /if \(!id \|\| !list\.length\) \{ if \(id\) stagedScroll\.delete\(id\); delete strip\.dataset\.sid; strip\.style\.display = "none"; return; \}\s*\n\s*strip\.dataset\.sid = id;/);
  assert.equal((STRIP.match(/prevList\.scrollTop/g) || []).length, 1, "the previous list's offset is read once, into the map, never straight onto the new list");
});

test("the cap breaks nothing the items do: expand keeps its keyed fold, the x keeps its stopPropagation, and there is no drag to break", () => {
  assert.match(STRIP, /const open = stagedOpen\.has\(id \+ ":" \+ i\);\s*\n\s*if \(open\) chip\.classList\.add\("open"\);/);
  // an expanded item grows inside the scroll, and a long unbroken token in it (a digest, a query string)
  // wraps instead of widening the list: the list's overflow-x is hidden, so unwrapped it was unreadable
  assert.match(CSS, /\.staged-chip\.open \.staged-row \.composer-chip-label \{ white-space: pre-wrap; overflow: visible; overflow-wrap: anywhere; \}/);
  assert.match(CSS, /\.staged-cite\.open \.composer-chip-label \{ white-space: pre-wrap; overflow: visible; overflow-wrap: anywhere; \}/);
  assert.doesNotMatch(LIST, /:has\(/, "no cap lift: the expanded item scrolls inside the list");
  assert.match(STRIP, /x\.addEventListener\("click", \(ev\) => \{ ev\.stopPropagation\(\); stagedMsgs\.removeAt\(id, i\);/);
  assert.doesNotMatch(STRIP, /draggable|dragstart|dragover|drop"/, "the staged items have no drag and drop");
});

test("the fold is the user's: a caret button (keyboard-reachable) and the label toggle it, a page-lifetime Set remembers it, the list starts shown", () => {
  assert.match(RENDER, /const stagedFolded = new Set<string>\(\);/, "empty at load: the list shows until the user folds it");
  assert.match(STRIP, /const folded = stagedFolded\.has\(id\);/);
  assert.match(STRIP, /const car = el\("button", "staged-fold"\) as HTMLButtonElement;\s*\n\s*car\.textContent = folded \? "▸" : "▾";/);
  assert.match(STRIP, /car\.setAttribute\("aria-expanded", folded \? "false" : "true"\);/);
  assert.match(STRIP, /if \(stagedFolded\.has\(id\)\) stagedFolded\.delete\(id\); else stagedFolded\.add\(id\);/);
  assert.match(STRIP, /car\.addEventListener\("click", toggleFold\);\s*\n\s*lbl\.addEventListener\("click", toggleFold\);/);
  // folded: the head line alone, the count still on it (the label is built before the return)
  assert.match(STRIP, /lbl\.textContent = list\.length \+ " staged [^"]*sends with your next message";[\s\S]*?strip\.appendChild\(head\);\s*\n\s*if \(folded\) return;/);
  // the renderer never folds or unfolds on its own: the two writers above are the only ones in the file
  assert.equal((RENDER.match(/stagedFolded\.(add|delete|clear)\(/g) || []).length, 2);
  // the rebuild destroys the caret that had focus; the keyboard user stays on the new one (Enter or Space
  // on the caret, then Enter again, folded and unfolded; dropped to body it focused the composer instead)
  assert.match(STRIP, /const had = document\.activeElement === car;\s*\n\s*renderStagedStrip\(id\);\s*\n\s*if \(had\) \(strip\.querySelector\("\.staged-fold"\) as HTMLElement \| null\)\?\.focus\(\);/);
  // Send now's click never reaches the fold toggle (it is a sibling, not a child, of the label)
  assert.match(STRIP, /head\.append\(car, lbl, go\);/);
  assert.match(CSS, /\.staged-head \.staged-fold \{[^}]*cursor: pointer;/);
  assert.match(CSS, /\.staged-head \.staged-lbl \{ cursor: pointer; \}/);
});

test("the staged run and the typed message go as ONE message: flushStaged routes the posts stagedPosts folds them into (the user 2026-09-08)", () => {
  assert.match(RENDER, /import \{ StagedStack, quoteReplyBody, stagedPosts \} from "\.\/staged-messages";/);
  // ONE routing call, once per post. The post list is the module's and executed in staged-messages.test.ts:
  // the fold, and the two kinds of item that go alone at their place in stage order (a goal follow-up, the
  // kernel wrapping one goal per message; a slash command, which the kernel fires only at the head of its
  // own text, so folded in it was prose or took the sections after it as its argument)
  assert.match(FLUSH, /for \(const p of stagedPosts\(batch, typed\)\) routeUserMessage\(sid, p\.text, p\.cites as Citation\[\] \| undefined, p\.imgPaths\);/);
  assert.equal((FLUSH.match(/routeUserMessage\(/g) || []).length, 1, "no send outside the post list");
  assert.doesNotMatch(FLUSH, /stagedBatchBody|citesGoal|isSlashCommand/, "the fold and its exceptions are decided in the module, not re-derived here");
  // the flush is one-shot: the stack is taken before anything routes
  assert.match(FLUSH, /^sid: string, typed\?: \{ text: string; cites\?: Citation\[\]; imgPaths\?: string\[\] \}\): number \{\s*\n\s*const batch = stagedMsgs\.takeAll\(sid\);/);
});

test("both send paths use the fold: deliver hands the typed message to flushStaged, Send now and the empty-box go release alone", () => {
  // deliver: the typed message rides the flush as the batch's last item, and no second send follows it
  assert.match(RENDER, /const cites = composerCitations\.get\(activeId\);\s*\n\s*flushStaged\(sid, \{ text, cites, imgPaths: attached\.filter\(\(p\) => previewKind\(p\) === "img"\) \}\);/);
  const deliverBody = RENDER.split("const deliver = () => {")[1].split("setComposerAskMode();")[0];
  assert.doesNotMatch(deliverBody, /routeUserMessage\(/, "deliver sends only through flushStaged");
  assert.equal((deliverBody.match(/flushStaged\(/g) || []).length, 1);
  // Send now (the strip's button) and the empty-box go release the stack alone
  assert.match(STRIP, /go\.addEventListener\("click", \(\) => \{[\s\S]*?flushStaged\(id\);/);
  assert.match(RENDER, /if \(!typed && !\(composerFiles\.get\(activeId\) \|\| \[\]\)\.length && stagedMsgs\.count\(activeId\)\) \{[\s\S]*?flushStaged\(activeId\);\s*\n\s*return;/);
  // the head's count and its tooltip say what happens, the two exceptions included
  assert.match(STRIP, /lbl\.textContent = list\.length \+ " staged [^"]*sends with your next message";/);
  assert.match(STRIP, /A plain send releases them as one message, in order, with your new message last; a card follow-up or a slash command goes on its own, in its place\. "/);
  assert.match(STRIP, /\+ "Send now releases them alone\."/);
});
