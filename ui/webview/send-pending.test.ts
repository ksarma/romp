// Send durability on the client (the 2026-09-05/06 audits). Two things went wrong at once: a send fed
// into a running turn is taken by the CLI at a later tool boundary and placed at its SEND time, so the
// pending bubble at the bottom vanished and the message reappeared higher up with no cue; and the
// client's bubble had a 20 s lifetime, so when the kernel's own echo was pruned early the send simply
// looked delivered. Now: (1) a pending send has NO lifetime — it ends on a landing, the kernel's
// never-delivered verdict, or the user's ✕; (2) a landed absorbed atom wears a "joined mid-turn" header
// and, when it landed above the tail, leaves a cue where the bubble sat ("delivered into the running
// turn at HH:MM · jump"); (3) every composer send posts a clientDiag breadcrumb (never the text).
// The decisions are executed through send-pending.ts; the DOM half is pinned in render.ts/styles.css.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { newPending, pendingBody, reconcilePending, cueAnchor, landedIn, type TailEvent } from "./send-pending";

const read = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const RENDER = read("render.ts");
const CSS = read("styles.css");
const T0 = 1_700_000_000_000;

// ── (1) no lifetime ──────────────────────────────────────────────────────────────────────────────

test("a pending send survives past 20 s — and past any time — without confirmation", () => {
  const list = [newPending("rename this to fetch_notes", undefined, T0)];
  // a first reconcile stamps base; then nothing happens for a minute, then an hour
  reconcilePending([{ kind: "assistant", md: "still working on the earlier step" }], list);
  for (const later of [T0 + 21_000, T0 + 60_000, T0 + 3_600_000]) {
    const r = reconcilePending([{ kind: "assistant", md: "…" }], list);
    assert.equal(r.keep.length, 1, `still pending at +${(later - T0) / 1000}s`);
    assert.equal(r.inject.length, 1, "…and still shown: nothing in the payload accounts for it");
  }
  assert.doesNotMatch(RENDER, /OPT_TTL_MS/, "the 20 s backstop is gone from render.ts");
});

test("it clears on the kernel's echo (suppressed) and ends on the landing (retired, with the index)", () => {
  const list = [newPending("rename this to fetch_notes", undefined, T0)];
  let r = reconcilePending([{ kind: "user", md: "rename this to fetch_notes", uuid: "echo:1" }], list);
  assert.equal(r.keep.length, 1, "the kernel's provisional never retires the entry");
  assert.equal(r.inject.length, 0, "…but ours steps aside while it is visible");
  r = reconcilePending([
    { kind: "user", md: "rename this to fetch_notes", uuid: "att1", absorbed: true },
    { kind: "tool", uuid: "t9" },
  ], list);
  assert.equal(r.keep.length, 0, "a landed user atom ends it");
  assert.deepEqual(r.landed.map((l) => l.idx), [0], "…naming the landed event, for the cue");
});

test("an image send lands even though the paths are gone from the text", () => {
  // the composer appends the dragged paths to the typed text; the CLI rewrites them to "[Image #N]" and the
  // kernel strips the placeholders and renders the pictures — so the sent text can never match verbatim
  const text = 'compare with the old one\n/tmp/notes-api/docs/before.png "/tmp/notes-api/docs/after one.png"';
  const imgs = ["/tmp/notes-api/docs/before.png", "/tmp/notes-api/docs/after one.png"];
  assert.equal(pendingBody(text, imgs), "compare with the old one");
  const p = newPending(text, imgs, T0);
  const landed: TailEvent = { kind: "user", uuid: "u7", md: "compare with the old one", images: [{}, {}] };
  assert.equal(landedIn(landed, p), true);
  assert.equal(landedIn({ kind: "user", uuid: "u8", md: "compare with the old one" }, p), false,
    "the body alone is not enough — the landing must carry the pictures");
  reconcilePending([{ kind: "assistant", md: "…" }], [p]);   // the press: base stamped against a tail without it
  const r = reconcilePending([landed], [p]);
  assert.equal(r.keep.length, 0, "the pictures-bearing atom beyond base is the landing");
});

test("the kernel's never-delivered verdict ends the entry — its bubble carries the text and the resend", () => {
  const list = [newPending("rename this to fetch_notes", undefined, T0)];
  const r = reconcilePending([{ kind: "user", md: "rename this to fetch_notes", uuid: "echo:1", undelivered: true }], list);
  assert.equal(r.keep.length, 0);
  assert.equal(r.lost.length, 1);
  assert.equal(r.inject.length, 0, "never a 'sending…' bubble beside a 'never delivered' one");
  // the kernel's undelivered bubble is the resend path: copy to composer / dismiss (undelivered-echo.test.ts)
  assert.match(RENDER, /re\.dataset\.act = "echorestore";/);
});

test("a connection drop marks unconfirmed sends 'not confirmed' — an event, and reversible by a confirmation", () => {
  assert.match(RENDER, /window\.addEventListener\("romp:wsdown", \(\) => markPendingLost\("connection"\)\);/);
  assert.match(RENDER, /if \(m\.type === "pipeState"\) \{ if \(!m\.up\) awaitingFull\.clear\(\); if \(!m\.up\) markPendingLost\("connection"\);/,
    "the VS Code pipe's down edge too — it never fires romp:wsdown");
  assert.match(RENDER, /function markPendingLost\(why: string\): void \{[\s\S]{0,600}?for \(const p of list\) if \(!p\.lost\) p\.lost = why;/);
  // the bubble says so, in the bare group's own label and on the bubble; ✕ stays the way back
  assert.match(RENDER, /if \(ev\.texts\.some\(\(t\) => t\.lost\)\) \{[\s\S]{0,700}?label\.textContent = ev\.texts\.length === 1 \? "not confirmed" : `\$\{ev\.texts\.length\} not confirmed`;/);
  assert.match(RENDER, /if \(t\.optimistic && t\.lost\) bubble\.title = "not confirmed — the connection dropped after this was sent; ✕ moves it back to the composer to send again";/);
  assert.match(RENDER, /if \(label\.classList\.contains\("lost"\)\) \{ label\.textContent = bubbles\.length === 1 \? "not confirmed"/, "the ✕ reflow keeps the vocabulary");
  assert.match(CSS, /\.queued-head \.queued-count\.lost \{ color: var\(--warn\); \}/);
  // a confirmation after the reconnect retires it like any other: the flag is display-only
  const list = [newPending("go ahead", undefined, T0)];
  reconcilePending([], list);
  list[0].lost = "connection";
  const r = reconcilePending([{ kind: "user", md: "go ahead", uuid: "u1" }], list);
  assert.equal(r.keep.length, 0);
});

// ── (2) the absorbed header and the mid-turn cue ─────────────────────────────────────────────────

test("cueAnchor: the last kernel event after the landed atom, or null when it landed at the tail", () => {
  const events: TailEvent[] = [
    { kind: "user", uuid: "u1", md: "first comment" },
    { kind: "user", uuid: "att1", md: "second comment", absorbed: true },
    { kind: "tool", uuid: "t1" },
    { kind: "tool", uuid: "t2" },
    { kind: "user", uuid: "echo:9", md: "a third send, still pending at the kernel" },
    { kind: "queued", uuid: "optimistic:123", texts: [{ md: "ours" }] },
  ];
  assert.equal(cueAnchor(events, 1), "t2", "under the event the bubble sat under — never our injection or the kernel's echo");
  assert.equal(cueAnchor(events.slice(0, 2), 1), null, "landed AT the tail: the swap was in place, no cue owed");
  assert.equal(cueAnchor([events[0], events[1], { kind: "tool" }], 1), null, "nothing stable to hang it on");
});

test("the landed absorbed atom wears the 'joined mid-turn' header, with the taken-at time one level deeper", () => {
  assert.match(RENDER, /if \(\(ev as any\)\.absorbed && !romp && !injected && !tagged\) turn\.appendChild\(absorbedHeader\(\(ev as any\)\.landedAt\)\);/);
  assert.match(RENDER, /function absorbedHeader\(landedAt\?: number \| null\): HTMLElement \{\s*\n\s*const h = el\("div", "absorbed-tag"\);\s*\n\s*h\.textContent = "joined mid-turn";/);
  assert.match(RENDER, /h\.title = "Sent while the session was working[^"]*"\s*\n\s*\+ \(typeof landedAt === "number" \? ", and the session took it at " \+ hhmm\(landedAt\) : ""\)/,
    "the time rides the tooltip, not the one-line head");
  // one header family: the follow-up header's size and alignment, dim rather than accent
  assert.match(CSS, /\.absorbed-tag \{ max-width: 72%; margin-bottom: 1px; font-size: 0\.82em; color: var\(--dim\); \}/);
});

test("a landing above the tail leaves the cue where the bubble sat; jump scrolls to the atom; both actions retire it", () => {
  // recorded at the landing that retired the bubble (never re-derived per build), keyed to the anchor event
  assert.match(RENDER, /for \(const \{ idx \} of r\.landed\) noteAbsorbedLanding\(s, idx\);/);
  assert.match(RENDER, /function noteAbsorbedLanding\(s: Session, idx: number\): void \{[\s\S]{0,400}?if \(!ev \|\| !ev\.absorbed \|\| !ev\.uuid\) return;\s*\n\s*const after = cueAnchor\(s\.events as TailEvent\[\], idx\);\s*\n\s*if \(!after\) return;/);
  assert.match(RENDER, /cues\.push\(\{ after, target: ev\.uuid, landedAt: typeof ev\.landedAt === "number" \? ev\.landedAt : null \}\);/);
  // rendered with the anchor item on every window build (single events, tool groups, retry groups), so it keeps its place
  assert.equal((RENDER.match(/appendAbsorbedCues\(v, s, /g) || []).length, 3, "hung under every item shape appendItem renders");
  assert.match(RENDER, /line\.appendChild\(document\.createTextNode\("delivered into the running turn"\s*\n\s*\+ \(c\.landedAt != null \? " at " \+ hhmm\(c\.landedAt\) : ""\)\)\);/);
  // click-safe: data-act on the body delegate; jump = scrollToAnchor on the atom's uuid, and the cue is done
  assert.match(RENDER, /jump\.dataset\.act = "abjump"; jump\.dataset\.target = c\.target;/);
  assert.match(RENDER, /x\.dataset\.act = "abdismiss"; x\.dataset\.target = c\.target;/);
  assert.match(RENDER, /abjump: \(elx\) => \{[\s\S]{0,400}?dismissAbsorbedCue\(sidC, target\);[\s\S]{0,200}?if \(target\) scrollToAnchor\(target\);/);
  assert.match(RENDER, /abdismiss: \(elx\) => \{[\s\S]{0,300}?dismissAbsorbedCue\(sidC, elx\.dataset\.target \|\| ""\);/);
  // the interrupt marker's chrome, shared by selector rather than copied
  assert.match(CSS, /\.turn-absorbed-cue \.dot, \.turn-interrupt \.dot \{ background: var\(--dim\); border: none; \}/);
  assert.match(CSS, /\.absorbed-cue-line, \.interrupt-line \{[^}]*font-style: italic/);
  assert.match(CSS, /\.absorbed-cue-act,\n\.undelivered-act \{/);
  // the cue leaves with its tab, like the pending sends
  assert.equal((RENDER.match(/absorbedCues\.delete\(id\);/g) || []).length, 2);
});

// ── (3) the breadcrumb ───────────────────────────────────────────────────────────────────────────

test("every composer send posts a clientDiag breadcrumb — sid, time, length, route; never the text", () => {
  const m = RENDER.match(/vscodeApi\.postMessage\(\{ type: "clientDiag", surface: "chat", what: "send",\s*\n\s*data: \{ ([^}]*) \} \}\);/);
  assert.ok(m, "the breadcrumb is posted from routeUserMessage");
  const fields = m![1];
  assert.match(fields, /\bsid\b/); assert.match(fields, /ts: Date\.now\(\)/); assert.match(fields, /len: text\.length/); assert.match(fields, /route:/);
  assert.doesNotMatch(fields, /\btext\b(?!\.length)/, "the text itself never leaves the client");
  assert.doesNotMatch(fields, /\bbody\b|\bmd\b/);
  // one owner: the breadcrumb sits in routeUserMessage, which every send path (plain, quote, follow-up, staged flush) goes through
  const fn = RENDER.slice(RENDER.indexOf("function routeUserMessage("), RENDER.indexOf("\n}\n", RENDER.indexOf("function routeUserMessage(")));
  assert.ok(fn.includes('what: "send"'));
});
