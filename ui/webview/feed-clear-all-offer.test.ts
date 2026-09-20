// The footer's Clear all is offered only while a card on the board would take the clear (the held-mail readers PR's
// review, 2026-09-20). The kernel declines a held message's id at the cleared-ledger write (a hold is decided by
// Approve or Deny, never dismissed) and lists a placeholder again on every build, so on a board of holds alone, or of
// placeholders alone, the press moved nothing, offered no Undo and said nothing: a visible click the kernel ignored,
// while the button was gated on the card COUNT (showCA) like the view menu, the tag lens and the session box. The
// button now has its own gate, clearAllOffered (asks.some(clearable), the predicate the card's Clear and the session
// header's Clear already read), and the three count-gated controls keep theirs. The kernel's half: a press that
// cleared fewer cards than it asked, or none, is answered on this page's socket with a clearAllResult frame, which the
// pane toasts (a refusal rings the shell's bell too), and the chat's chip drop follows the ids the write took.
// The review's round 2 (2026-09-20) added three things pinned here too: on a merged board the press reaches every
// host and each kernel answers about its OWN board, so a remote kernel's frame arrives host-stamped (federation.ts
// prefixInbound, as settingStale does), the pane labels each answer with its machine (the local kernel's as this
// machine, the gear's word) on the toast and the bell row, and folds one press's answers into one toast keyed on the
// press and the toast on screen, never a clock; the Task tracking switch's off frame hides the button and a latch
// holds it hidden through a renderBody a settings change re-runs (Undo stays); and the footer's right-hand dock
// rides the session box's margin-right:auto (feed.css) instead of the button that can now be hidden.
// Source pins, in the style of the other feed tests (feed-sess-clear.test.ts); the behaviour runs under the DOM
// stand-in in feed-render-incremental.test.ts (its last cases).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const FEED = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "feed.ts"), "utf8");
const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");
const FED = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "federation.ts"), "utf8");
const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "feed.css"), "utf8");

const footer = FEED.slice(FEED.indexOf("function renderBody(list: HTMLElement) {"), FEED.indexOf("if (!asks.length) {", FEED.indexOf("function renderBody(list: HTMLElement) {")));

test("the Clear all button is gated on a card a clear would take, never on the card count or showCA", () => {
  assert.match(footer, /ensureClearAll\(\)\.style\.display = clearAllOffered\(asks, boardCardsUnknown\) && !feedOff \? "" : "none";/,
    "the button's own gate, read at render time, and never while the switch is off");
  assert.doesNotMatch(footer, /ensureClearAll\(\)\.style\.display = showCA/, "no longer the has-cards gate");
  assert.doesNotMatch(footer, /ensureClearAll\(\)\.style\.display = (?:!!)?asks\.length/, "and not a bare card count");
  // the predicate the pane already owns: not a placeholder, not a held message (the card's Clear and the header's Clear)
  assert.match(FEED, /function clearable\(it: AskItem\): boolean \{\s*\n\s*return !it\.provisional && it\.blocked\?\.state !== "quarantine";/);
  assert.match(FEED, /function clearAllOffered\(items: AskItem\[\], cardsUnknown: CardsUnknown\): boolean \{\s*\n\s*return items\.some\(clearable\) \|\| \(items\.length > 0 && !!cardsUnknown\);\s*\n\}/,
    "asks.some(clearable), held while a host's cards are unknown, never on an empty board");
});

test("the view menu, the tag lens, the session box and the footer stay keyed on the card count (showCA)", () => {
  // the refuters' correction: gating showCA wholesale would have hidden these on a board of holds alone
  assert.match(footer, /const showCA = !!asks\.length;/);
  assert.match(footer, /ensureViewMenuBtn\(\)\.style\.display = showCA \? "" : "none";/);
  assert.match(footer, /ensureTagLensBtn\(\)\.style\.display = showCA \? "" : "none";/);
  assert.match(footer, /ensureSessionBox\(\)\.style\.display = showCA \? "" : "none";/);
  assert.match(footer, /ensureUndoClear\(\)\.style\.display = canUndoClear \? "" : "none";/);
  assert.match(footer, /if \(foot\) foot\.style\.display = \(showCA \|\| canUndoClear\) \? "" : "none";/, "the footer itself: cards or an Undo");
});

test("while a host's cards are unknown the button is offered, from the last payload's own gate, on a board that has a card", () => {
  // the merged-board edge the refuters flagged: a host attached with no frame yet has its clearable cards absent from
  // `asks`, so a gate on the cards alone would hide the button just before that frame lands, then show it: a move on
  // an inference flap, and a hidden button saying nothing is clearable when that host's cards are. The payload gate
  // (T404 round seven) already says an absence proves nothing while cards are unknown; the Clear all reads the same
  // fact, recorded when the frame lands. Never on an empty board: the button appears nowhere the card count hid it.
  assert.match(FEED, /let boardCardsUnknown: CardsUnknown = false;/, "the recorded fact");
  assert.match(FEED, /const cardsUnknown = frameCardsUnknown\(m\);\s*\n\s*boardCardsUnknown = cardsUnknown;/, "recorded where the frame's gate is read");
  assert.match(FEED, /import \{[^}]*frameCardsUnknown[^}]*type CardsUnknown[^}]*\} from "\.\/badge-mirror";/, "one reader of the frame's unknown-hosts fields");
});

test("the tooltip drops 'every' and carries no em or en dash; the sibling grammar stands (a lowercase verb phrase)", () => {
  const m = /b\.id = "feed-clearall";\s*\n\s*b\.textContent = "Clear all";\s*\n\s*b\.title = "([^"]*)";/.exec(FEED);
  assert.ok(m, "the button's title");
  const title = m![1];
  assert.doesNotMatch(title, /\bevery\b/, "the press no longer takes every open card: a held message and a placeholder stay");
  assert.doesNotMatch(title, /[\u2013\u2014]/, "no em or en dash (the added-line scan counts a pre-existing one on a rewritten line as new)");
  assert.match(title, /^clear the open cards \(inbox-zero\); Undo restores them\./, "a lowercase verb phrase, like the card's 'clear this task'");
  assert.match(title, /held message stays until you approve or deny it$/, "…and it names what stays");
});

test("the clearable comment names the footer: the pane never offers a click the kernel would decline", () => {
  const at = FEED.indexOf("function clearable(it: AskItem): boolean {");
  const comment = FEED.slice(FEED.lastIndexOf("\n\n", at), at);
  assert.match(comment, /the footer's Clear all \(clearAllOffered, below\) is offered only while a card\s*\n\/\/ on the board passes it/);
  assert.match(comment, /a board of held messages alone, or of placeholders alone, offers no click the\s*\n\/\/ kernel would decline/);
});

test("the kernel's clearAllResult is rendered: toasted, and a refusal rings the shell's bell under its refused kind", () => {
  const h = FEED.slice(FEED.indexOf('} else if (m.type === "clearAllResult"'), FEED.indexOf('} else if (m.type === "revealCards")'));
  assert.ok(h.length > 0, "the handler exists, beside undoClearResult");
  assert.match(h, /m\.type === "clearAllResult" && typeof m\.text === "string" && m\.text\) \{/);
  // the machine the answer is about (the review's round 2): the host federation stamped on a remote kernel's frame, else
  // this machine, the gear's word for the local kernel's frame (setting-stale.test.ts pins the gear's); the kernel's text
  // follows the label unchanged, on the toast and on the durable row alike
  assert.match(h, /const where = typeof m\.host === "string" && m\.host \? m\.host : "this machine";\s*\n\s*const line = where \+ ": " \+ m\.text;/,
    "the answer is labelled with the machine it is about");
  assert.match(h, /if \(!m\.ok\) window\.parent\?\.postMessage\(\{ romp: "notify", kind: "refused", text: line, sid: "", itemId: "" \}, "\*"\);/,
    "a refusal (nothing cleared) keeps a durable record, the settingRefused shape, under the same label");
  // one press's answers fold into one toast: an answer joins while the fold's toast is the one on screen, else starts a
  // new one; the press opens a fresh fold; no clock and no window anywhere in the fold (the gear's fold has the same pin)
  assert.match(h, /const lines = clearAllFold && clearAllFold\.toast === feedToastEl \? \[\.\.\.clearAllFold\.lines, line\] : \[line\];\s*\n\s*feedToast\(lines\.join\("\\n"\)\);\s*\n\s*clearAllFold = feedToastEl \? \{ toast: feedToastEl, lines \} : null;/,
    "the fold, keyed on the toast on screen");
  assert.match(FEED, /let clearAllFold: \{ toast: HTMLElement; lines: string\[\] \} \| null = null;/, "the fold's state");
  assert.match(FEED, /b\.onclick = \(ev\) => \{ ev\.stopPropagation\(\); clearAllFold = null; vscodeApi\?\.postMessage\(\{ type: "clearAll" \}\); \};/, "a press opens a fresh fold");
  assert.doesNotMatch(h, /Date\.now\(|setTimeout|setInterval/, "the fold keys on the press and the toast, never on a clock or a window");
  assert.match(CSS, /\.feed-toast \{[^}]*white-space: pre-line;/, "a folded toast shows one line per machine");
  assert.doesNotMatch(h, /pendingCleared|clearedStack|asks\.splice/, "nothing to put back: the footer's press is not optimistic");
  // the frame the pane renders is the one the kernel sends, on the delivering socket (never a broadcast), with `ok`
  // false for a press that cleared nothing; a press that cleared all it asked is answered by the next payload alone
  assert.match(KERNEL, /_reply\(client, \{"type": "clearAllResult", "ok": bool\(_n\), "cleared": _n, "left": len\(_left\), "held": _held, "text": _text\}\)/);
  const door = KERNEL.slice(KERNEL.indexOf('msg.get("type") == "clearAll"'), KERNEL.indexOf('msg.get("type") == "undoClear"'));
  assert.ok(door.length > 0, "the clearAll door");
  assert.doesNotMatch(door, /_send_to_app\("chat", \{"type": "dropCitationsAll"\}\)/,
    "the chat's chip drop follows the write (dropCitation over the ids taken), never the gesture: the old unconditional call is gone (its name survives in the door's comment)");
  assert.match(door, /_send_to_app\("chat", \{"type": "dropCitation", "itemId": str\(_written\[0\]\), "itemIds": _gone\}\)/);
});

test("guard, not a defect pin: the notice card's action door needs no pane change, its refusal already toasts the kernel's reason", () => {
  // fresh-1 (the same review): the kernel answers a read fault on the door's existing noticeActionDone frame, whose
  // `error` this handler already says; green before and after, kept so the frame's contract is pinned on this side
  assert.match(FEED, /if \(!m\.ok\) feedToast\("The card's action was refused: " \+ String\(m\.error \|\| "unknown error"\)\);/);
});

test("a remote kernel's clearAllResult is host-stamped by federation, beside settingStale's stamp; the local kernel's frame carries no host", () => {
  // the frame itself carries no host (the kernel answers the delivering socket about its own board), so the stamp is the
  // pane's only way to name the machine; setting-stale.test.ts drives prefixInbound over the frame
  const at = FED.indexOf('if (out.type === "clearAllResult") out.host = host;');
  assert.ok(at > 0, "the stamp");
  assert.ok(FED.lastIndexOf('if (out.type === "settingStale") out.host = host;', at) > 0, "placed after settingStale's stamp, in prefixInbound");
  assert.ok(at < FED.indexOf("function _prefixIdBearing("), "inside prefixInbound");
});

test("the Task tracking switch's off frame hides the footer's Clear all and latches it hidden until a built frame; Undo is not touched", () => {
  // extra8-2 (the review's round 2): the off arm returns before renderBody, so the button of the last render stood under
  // the notice and a press reached a kernel that clears nothing while off and answers nothing; a storage event on
  // romp:settings re-runs renderBody over the still-populated asks, so hiding the button once would not have held
  assert.match(FEED, /let feedOff = false;/, "the latch");
  const off = FEED.slice(FEED.indexOf("if (m.off) {"), FEED.indexOf("// HOVER-FREEZE:"));
  assert.match(off, /feedOff = true;\s*\n\s*ensureClearAll\(\)\.style\.display = "none";\s*\n\s*return;\s*\n\s*\}/, "set and hidden in the off arm, before its return");
  assert.doesNotMatch(off, /ensureUndoClear|feed-undoclear|foot\.style/, "Undo and the footer are left as the last render had them: the off frame carries canUndoClear and the undoClear door has no tracking gate");
  assert.match(FEED, /boardCardsUnknown = cardsUnknown;[^\n]*\n\s*feedOff = false;/, "cleared where a built frame lands (applyFeedPayload)");
  assert.equal(FEED.split("feedOff").length - 1, 6, "the latch is read at the gate and written on the two frames alone (the declaration, the off arm's comment and write, applyFeedPayload, the gate and its comment)");
});

test("the footer's right-hand dock rides the session box, not the button that can now be hidden (feed.css)", () => {
  // ui-2 (the review's round 2): the dock lived on #feed-clearall's margin-left:auto, so with Clear all hidden on a board
  // of held messages alone Undo slid left beside Search; margin-right:auto on #feed-search, the last left control that is
  // on the bar whenever any card is, keeps Undo right-docked whether Clear all is shown or not and leaves the empty
  // board's left-edge Undo as it was (the session box is hidden there too). feed-css-footer.test.ts measures it.
  assert.match(CSS, /#feed-search \{ display: inline-flex; align-items: center; gap: 5px; position: relative;\s*\n\s*margin-right: auto; \}/, "the split on the session box");
  assert.match(CSS, /#feed-clearall \{ order: 10; \}/, "the button keeps its order alone");
  assert.doesNotMatch(CSS, /#feed-clearall \{[^}]*margin-left: auto/, "no auto margin on a control that hides");
  assert.equal(CSS.split("margin-right: auto").length - 1, 3, "three right auto margins in the sheet: the session box's, the card modal's age and the file-comments composer's hint");
  // the state that made this reachable: the button's own gate at renderBody, not the card count the left cluster reads
  assert.match(footer, /ensureClearAll\(\)\.style\.display = clearAllOffered\(asks, boardCardsUnknown\)/);
});
