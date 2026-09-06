// Live tab label/color/tag application from the kernel's recurring tabOrder push (the user
// 2026-08-24): a headless `romp rename` / `romp color` / `romp tag` used to update kernel state —
// and the timeline — while the CHAT strip held the old label/color until reload, because the pushed
// per-tab meta was applied only to placeholder tabs, never to existing sessions, and per-session
// frames ride a build cache whose sig (transcript+states) a rename/recolor never busts. The pure
// sync lives in tab-meta.ts (executable below); the render.ts wiring is pinned at the source
// (render.ts has no jsdom harness — the apierror-retry-now.test.ts idiom). Synthetic names only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { syncSessionsFromTabMeta, applyMetaToSession, notePendingMeta, emojiConfirmClosesDialog,
         PENDING_META_MAX_AGE, TabSessionMeta, PendingTabMeta } from "./tab-meta";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");

const sess = (name: string, bg?: string): TabSessionMeta =>
  ({ name, color: bg ? { bg, fg: "#ffffff" } : null });

test("a pushed rename and recolor land on the existing session — the strip follows the push, not a reload", () => {
  const s = sess("web", "#336699");
  const store = new Map([["S1", s]]);
  const changed = syncSessionsFromTabMeta(
    [{ id: "S1", name: "api", color: { bg: "#aa3366", fg: "#ffffff" } }],
    (id) => store.get(id), new Map());
  assert.equal(changed, true, "the caller learns it must repaint");
  assert.equal(s.name, "api", "the pushed rename lands");
  assert.deepEqual(s.color, { bg: "#aa3366", fg: "#ffffff" }, "the pushed recolor lands");
});

test("an unchanged push reports no visible change, and junk entries are ignored", () => {
  const s = sess("web", "#336699");
  const store = new Map([["S1", s]]);
  assert.equal(syncSessionsFromTabMeta(
    [{ id: "S1", name: "web", color: { bg: "#336699", fg: "#ffffff" } },
     { id: 42 as any, name: "junk" }, null as any, { name: "no-id" }],
    (id) => store.get(id), new Map()), false);
  assert.equal(s.name, "web");
});

test("an empty pushed name or malformed color never wipes what the session has", () => {
  const s = sess("web", "#336699");
  assert.equal(applyMetaToSession(s, { name: "", color: { bg: 7 } }), false);
  assert.equal(s.name, "web");
  assert.deepEqual(s.color, { bg: "#336699", fg: "#ffffff" });
});

test("a pending optimistic edit holds a stale in-flight push, and the kernel echo clears it", () => {
  const s = sess("web", "#336699");
  const store = new Map([["S1", s]]);
  const pending = new Map<string, PendingTabMeta>();
  notePendingMeta(pending, "S1", { colorBg: "#AA3366" });        // the swatch click, case differs on purpose
  s.color = { bg: "#AA3366", fg: "#ffffff" };                    // …applied optimistically by the caller
  // a push BUILT BEFORE the kernel processed the recolor still carries the old color → held
  syncSessionsFromTabMeta([{ id: "S1", name: "web", color: { bg: "#336699", fg: "#ffffff" } }],
    (id) => store.get(id), pending);
  assert.equal(s.color!.bg, "#AA3366", "the stale push cannot revert the optimistic swatch");
  assert.ok(pending.has("S1"), "the expectation stands until echoed");
  // the echo (case-insensitive on the hex) adopts and clears
  syncSessionsFromTabMeta([{ id: "S1", name: "web", color: { bg: "#aa3366", fg: "#ffffff" } }],
    (id) => store.get(id), pending);
  assert.equal(pending.has("S1"), false, "the echo retires the pending edit");
});

test("an unechoed pending edit yields to the kernel after " + PENDING_META_MAX_AGE + " pushes — the store of record wins", () => {
  const s = sess("web");
  const store = new Map([["S1", s]]);
  const pending = new Map<string, PendingTabMeta>();
  notePendingMeta(pending, "S1", { name: "api" });
  for (let i = 0; i < PENDING_META_MAX_AGE; i++)
    syncSessionsFromTabMeta([{ id: "S1", name: "tests" }], (id) => store.get(id), pending);
  assert.equal(pending.has("S1"), false, "the silent-push cap retires it");
  syncSessionsFromTabMeta([{ id: "S1", name: "tests" }], (id) => store.get(id), pending);
  assert.equal(s.name, "tests", "after yielding, the kernel's name lands");
});

test("a pending edit whose tab left the push ages out too", () => {
  const pending = new Map<string, PendingTabMeta>();
  notePendingMeta(pending, "S9", { name: "gone" });
  for (let i = 0; i < PENDING_META_MAX_AGE; i++)
    syncSessionsFromTabMeta([{ id: "S1", name: "web" }], () => undefined, pending);
  assert.equal(pending.size, 0);
});

test("a rename pending guard holds the NAME against a pre-rename push — a pushed recolor still lands (fields are independent)", () => {
  // the renamed confirm applied "api" optimistically; a push BUILT BEFORE the kernel's rename
  // still carries "web" — the guard must keep the confirm's label, never flap back
  const s = sess("api", "#336699");
  const store = new Map([["S1", s]]);
  const pending = new Map<string, PendingTabMeta>();
  notePendingMeta(pending, "S1", { name: "api" });
  syncSessionsFromTabMeta([{ id: "S1", name: "web", color: { bg: "#aa3366", fg: "#ffffff" } }],
    (id) => store.get(id), pending);
  assert.equal(s.name, "api", "the stale pre-rename push cannot revert the confirmed label");
  assert.equal(s.color!.bg, "#aa3366", "the color field is not hostage to the name's guard");
});

// ── render.ts wiring (source pins — no jsdom harness for the monolith) ─────────────────────────────
test("applyTabOrder syncs the pushed meta onto existing sessions inside the tabs branch", () => {
  assert.match(RENDER, /syncSessionsFromTabMeta\(tabs, \(id\) => sessions\.get\(id\), pendingTabMeta\);/);
  // inside the Array.isArray(tabs) rebuild — the same frame that refreshes the placeholders
  const block = (RENDER.match(/if \(Array\.isArray\(tabs\)\) \{[\s\S]*?\n  \}/) || [""])[0];
  assert.ok(block.includes("syncSessionsFromTabMeta"), "the sync rides the tabMeta rebuild");
});

test("a session frame cannot roll the strip back: upsert re-applies the freshest pushed meta", () => {
  assert.match(RENDER, /sessions\.set\(msg\.id, s\);\n[\s\S]{0,400}?const tm = tabMeta\.get\(msg\.id\);\n\s*if \(tm\) applyMetaToSession\(s, tm, pendingTabMeta\.get\(msg\.id\)\);/);
});

test("both optimistic paths note their expectation: the color swatch and the renamed confirm", () => {
  assert.match(RENDER, /notePendingMeta\(pendingTabMeta, id, \{ colorBg: bg \}\);/);
  assert.match(RENDER, /notePendingMeta\(pendingTabMeta, m\.id, \{ name: m\.name \}\);/);
});

test("the tabOrder frame's views land before the strip repaints — a CLI tag edit re-filters the tabs on the same push", () => {
  // captureViews (adopt the pushed views/tags blob) must run BEFORE applyTabOrder (whose renderTabs
  // re-filters via tabInView) in the tabOrder handler — the (c) leg of the live-update fix
  // the frame's provenance rides along since T233 (captureViews still runs FIRST)
  assert.match(RENDER, /else if \(m\.type === "tabOrder"\) \{\s*\n\s*if \(typeof m\.selfHost === "string" && m\.selfHost\) adoptSelfHost\(m\.selfHost\);[^\n]*\n\s*captureViews\(m\.views \|\| null\);\s*\n\s*applyTabOrder\(m\.order, m\.tabs, \{ reemit: m\.reemit === true, freshHost: typeof m\.freshHost === "string" \? m\.freshHost : undefined \}\);\s*\n\s*\}/);
  assert.match(RENDER, /const inViewIds = ids\.filter\(tabInView\);/);
});

// ── the tab emoji (the user 2026-09-06): the third field the push carries, beside name and color ──

test("a pushed emoji lands on the existing session; an empty string clears it; a kernel without the field leaves it alone", () => {
  const s = sess("web", "#336699");
  const store = new Map([["S1", s]]);
  assert.equal(syncSessionsFromTabMeta([{ id: "S1", name: "web", emoji: "\u{1F319}" }], (id) => store.get(id), new Map()), true);
  assert.equal(s.emoji, "\u{1F319}", "the pushed emoji lands");
  assert.equal(syncSessionsFromTabMeta([{ id: "S1", name: "web", emoji: "\u{1F319}" }], (id) => store.get(id), new Map()), false,
               "an unchanged push reports no visible change");
  assert.equal(syncSessionsFromTabMeta([{ id: "S1", name: "web" }], (id) => store.get(id), new Map()), false,
               "no emoji key (an older kernel) is not a clear");
  assert.equal(s.emoji, "\u{1F319}");
  assert.equal(syncSessionsFromTabMeta([{ id: "S1", name: "web", emoji: "" }], (id) => store.get(id), new Map()), true);
  assert.equal(s.emoji, "", "an explicit empty string clears — the kernel sends it for every tab without one");
  assert.equal(applyMetaToSession(s, { emoji: 7 as any }), false, "a malformed value is ignored");
});

test("the emojiSet confirm's pending guard holds a stale push, the echo clears it, and the name and color still land", () => {
  const s = sess("web", "#336699");
  const store = new Map([["S1", s]]);
  const pending = new Map<string, PendingTabMeta>();
  notePendingMeta(pending, "S1", { emoji: "\u{1F319}" });   // the kernel confirmed the moon
  s.emoji = "\u{1F319}";
  // a push built BEFORE the store had it carries the old (empty) emoji and a fresh rename
  assert.equal(syncSessionsFromTabMeta([{ id: "S1", name: "api", emoji: "" }], (id) => store.get(id), pending), true);
  assert.equal(s.name, "api", "the rename lands — fields are independent");
  assert.equal(s.emoji, "\u{1F319}", "the stale emoji cannot roll the strip back");
  assert.equal(pending.has("S1"), true, "unechoed, the guard stands");
  assert.equal(syncSessionsFromTabMeta([{ id: "S1", name: "api", emoji: "\u{1F319}" }], (id) => store.get(id), pending), false);
  assert.equal(pending.has("S1"), false, "the echo clears the guard");
  // and a pending CLEAR holds against a push that still carries the old glyph
  notePendingMeta(pending, "S1", { emoji: "" });
  s.emoji = "";
  syncSessionsFromTabMeta([{ id: "S1", name: "api", emoji: "\u{1F319}" }], (id) => store.get(id), pending);
  assert.equal(s.emoji, "", "a pending clear stands until the push agrees");
});

test("the emojiSet confirm closes the dialog that asked: while pending whatever the kernel stored, after the backstop when the value is the one it asked for", () => {
  const moon = "\u{1F319}", rocket = "\u{1F680}";
  // pending: the kernel answers only the client that asked, so this IS the answer — the validator may have
  // trimmed the value, so the value is not compared
  assert.equal(emojiConfirmClosesDialog({ sid: "S1", pending: true, asked: " " + moon + " " }, "S1", moon), true);
  assert.equal(emojiConfirmClosesDialog({ sid: "S1", pending: true, asked: "" }, "S1", ""), true, "a Clear's confirm");
  // not pending: the 30 s backstop (or an unrelated warn taken for the refusal) had already un-pended the
  // dialog when the real answer arrived; the tab wears the value, so a red "still waiting" under it would be a
  // lie — it used to stay open until Cancel (review round 3, 2026-09-06)
  assert.equal(emojiConfirmClosesDialog({ sid: "S1", pending: false, asked: moon }, "S1", moon), true);
  assert.equal(emojiConfirmClosesDialog({ sid: "S1", pending: false, asked: "" }, "S1", ""), true, "a late Clear confirm");
  // what leaves an open dialog alone
  assert.equal(emojiConfirmClosesDialog({ sid: "S1", pending: false, asked: moon }, "S1", rocket), false,
               "some other value for this session — not what it asked");
  assert.equal(emojiConfirmClosesDialog({ sid: "S1", pending: false }, "S1", ""), false,
               "a dialog that has asked nothing yet: an undefined ask is not a Clear");
  assert.equal(emojiConfirmClosesDialog({ sid: "S1", pending: false }, "S1", moon), false);
  assert.equal(emojiConfirmClosesDialog({ sid: "S1", pending: true, asked: moon }, "S2", moon), false,
               "another session's confirm, even while pending");
  assert.equal(emojiConfirmClosesDialog(null, "S1", moon), false, "no dialog open");
  assert.equal(emojiConfirmClosesDialog(undefined, "S1", moon), false);
});

test("render.ts wires the emoji like name and color: tabMeta stores it, the confirm notes it, the strip reads it", () => {
  assert.match(RENDER, /emoji: typeof t\.emoji === "string" \? t\.emoji : undefined/);   // applyTabOrder → tabMeta
  assert.match(RENDER, /emoji: \("emoji" in msg\) \? String\(msg\.emoji \|\| ""\) : \(prev \? prev\.emoji : undefined\)/);   // the session frame
  assert.match(RENDER, /m\.type === "emojiSet" && m\.id && typeof m\.emoji === "string"/);
  assert.match(RENDER, /notePendingMeta\(pendingTabMeta, m\.id, \{ emoji: m\.emoji \}\);/);
});
