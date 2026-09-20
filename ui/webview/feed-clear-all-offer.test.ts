// The footer's Clear all is offered only while a card on the board would take the clear (the held-mail readers PR's
// review, 2026-09-20). The kernel declines a held message's id at the cleared-ledger write (a hold is decided by
// Approve or Deny, never dismissed) and lists a placeholder again on every build, so on a board of holds alone, or of
// placeholders alone, the press moved nothing, offered no Undo and said nothing: a visible click the kernel ignored,
// while the button was gated on the card COUNT (showCA) like the view menu, the tag lens and the session box. The
// button now has its own gate, clearAllOffered (asks.some(clearable), the predicate the card's Clear and the session
// header's Clear already read), and the three count-gated controls keep theirs. The kernel's half: a press that
// cleared fewer cards than it asked, or none, is answered on this page's socket with a clearAllResult frame, which the
// pane toasts (a refusal rings the shell's bell too), and the chat's chip drop follows the ids the write took.
// Source pins, in the style of the other feed tests (feed-sess-clear.test.ts); the behaviour runs under the DOM
// stand-in in feed-render-incremental.test.ts (its last two cases).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const FEED = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "feed.ts"), "utf8");
const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");

const footer = FEED.slice(FEED.indexOf("function renderBody(list: HTMLElement) {"), FEED.indexOf("if (!asks.length) {", FEED.indexOf("function renderBody(list: HTMLElement) {")));

test("the Clear all button is gated on a card a clear would take, never on the card count or showCA", () => {
  assert.match(footer, /ensureClearAll\(\)\.style\.display = clearAllOffered\(asks, boardCardsUnknown\) \? "" : "none";/,
    "the button's own gate, read at render time");
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
  assert.match(h, /if \(!m\.ok\) window\.parent\?\.postMessage\(\{ romp: "notify", kind: "refused", text: m\.text, sid: "", itemId: "" \}, "\*"\);/,
    "a refusal (nothing cleared) keeps a durable record, the settingRefused shape");
  assert.match(h, /\n\s*feedToast\(m\.text\);/, "both answers are said out loud");
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
