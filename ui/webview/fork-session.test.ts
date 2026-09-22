// Fork a session (the user 2026-08-13): a NEW parallel session branches from a chosen point — the
// hover "fork" BELOW each response run (the user 2026-08-19: forking conceptually cuts under the
// response, so the button left the prompt's msg-acts row) or from the tip (the palette's "Fork this
// session…", and the tip run's own spot); the parent
// is untouched and both continue as separate threads. The modal asks the new name — default
// "<session>-fork", editable — and the provisional tab is the instant acknowledgement, joined by NAME
// exactly like a picker create. Source-level pins (no jsdom for the chat renderer), plus the kernel
// side of the contract (node-tests-pin-kernel-source precedent).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "styles.css"), "utf8");
const PALETTE = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "palette-main.ts"), "utf8");
const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");
const BACKEND = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "sdk_backend.py"), "utf8");

test("the fork affordance rides BELOW each response run — delegated, with the cut the old bubble button passed", () => {
  // the spot map: the FIRST genuine editable prompt after a run is its cut; the tip run forks everything
  assert.match(RENDER, /function applyForkSpots\(sid: string, v: View\): void \{/);
  assert.match(RENDER, /&& senderKind\(ev\) === "user" && editable\?\.has\(ev\.uuid\)/);
  assert.match(RENDER, /if \(run && !spots\.has\(run\)\) spots\.set\(run, ""\);/);
  assert.match(RENDER, /\.turn-assistant\[data-uuid="\$\{cssEscape\(anchor\)\}"\]/);
  // …applied on the marks' hooks, like the branch chips (the transcript DOM rebuilds constantly)
  assert.match(RENDER, /applyForkSpots\(sid, v\);/);
});

test("the fork button sits INLINE, right of the worked-seconds label — never its own row below it", () => {
  // the user 2026-08-25: the elapsed footer is the flex host; a turn with no footer (the live tip)
  // keeps the button on its own row exactly as before. The remover walks closest(.turn-assistant)
  // because the spot may nest inside the elapsed row.
  assert.match(RENDER, /const elapsed = turn\.querySelector\(":scope > \.turn-elapsed"\) as HTMLElement \| null;/);
  assert.match(RENDER, /if \(elapsed\) elapsed\.appendChild\(row\);\s*\n\s*else turn\.appendChild\(row\);/);
  assert.match(RENDER, /const anchor = \(old\.closest\("\.turn-assistant"\) as HTMLElement \| null\)\?\.dataset\.uuid \|\| "";/);
  const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "styles.css"), "utf8");
  assert.match(CSS, /\.turn-elapsed \{[^}]*display: flex; align-items: center; gap: 8px; min-width: 0;/s);
  assert.match(CSS, /\.turn-elapsed \.fork-spot \{ margin-top: 0; \}/);
  // the OLD home is gone: the prompt's msg-acts row no longer carries a fork (the user 2026-08-19)
  assert.doesNotMatch(RENDER, /acts\.appendChild\(fk\);/);
  // the fork GLYPH beside the word, Fork in the accessible name (T381, the user 2026-09-12): the stroke family's
  // drawing from icons.ts, a line in from the left branching into two that run on to the right, no arrowheads
  assert.match(RENDER, /fk\.innerHTML = ICON_FORK \+ '<span class="msg-fork-word">fork<\/span>';/, "the glyph carried on the button, the word beside it");
  assert.match(RENDER, /fk\.setAttribute\("aria-label", "Fork"\);/);
  assert.match(RENDER, /import \{ GEAR_GLYPH, ICON_FORK \} from "\.\/icons";/);   // the strip's gear glyph shares the import (the lock icons left with the gear's menu, T415)
  assert.doesNotMatch(RENDER, /fk\.textContent = "fork";/, "no bare word any more");
  const ICONS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "icons.ts"), "utf8");
  const fork = ICONS.slice(ICONS.indexOf("export const ICON_FORK"), ICONS.indexOf(";", ICONS.indexOf("export const ICON_FORK")));
  assert.match(fork, /<polyline points="2 12 9 12 15 7 22 7"\/>/, "the trunk from the left edge to the fork point, then up-right to the right edge");
  assert.match(fork, /<polyline points="9 12 15 17 22 17"\/>/, "…and the second branch down-right to the right edge");
  assert.doesNotMatch(fork, /marker|arrow|#[0-9a-fA-F]{3,6}\b/, "no arrowheads, no raw hex: currentColor strokes in the shared family");
  assert.match(CSS, /\.msg-fork \{ display: inline-flex; align-items: center; gap: 4px; \}/);
  // click-safe: the button is DELEGATED (data-act), landing in the shared modal with the spot's own cut
  assert.match(RENDER, /fk\.dataset\.act = "forkspot";/);
  assert.match(RENDER, /forkspot: \(elx\) => \{/);
  assert.match(RENDER, /showForkPrompt\(activeId, cut\);/);
  // hover the RESPONSE to reveal it; not a rewind: no two-click arm, and never the destructive red
  assert.match(CSS, /\.turn-assistant:hover \.msg-fork, \.msg-fork:focus-visible \{ opacity: 0\.9; \}/);
  assert.match(CSS, /\.msg-fork:hover \{ color: var\(--fg\); border-color: var\(--accent\); \}/);
  assert.doesNotMatch(CSS, /\.msg-fork\.armed/);
  // the under-bubble button family wears the ONE button rest (the user 2026-08-23 made it neutral,
  // never the terracotta code tint; T141 2026-08-28 unified all button rests to the feed's — dark
  // ground, the mirrored --card-border hairline). Only .code-copy keeps the tint — it sits ON the
  // tinted code block and blends there.
  for (const block of [".msg-edit {", ".msg-del, .msg-restorefiles, .msg-fork {", ".notice-act {"]) {   // .undelivered-act → the notice word button (2026-09-08)
    const body = CSS.slice(CSS.indexOf(block), CSS.indexOf("}", CSS.indexOf(block)));
    assert.ok(body.includes("background: transparent"), block + " wears the one button rest");
    assert.ok(body.includes("var(--card-border)"), block + " wears the feed hairline");
    assert.ok(!body.includes("--code-bg"), block + " must not borrow the code tint");
  }
  const copy = CSS.slice(CSS.indexOf(".code-copy {"), CSS.indexOf("}", CSS.indexOf(".code-copy {")));
  assert.ok(copy.includes("var(--code-bg)"), ".code-copy stays tinted — it lives on the code block");
});

test("the modal defaults to <session>-fork and posts forkSession {id, uuid, name}", () => {
  assert.match(RENDER, /function showForkPrompt\(sid: string, uuid: string\): void \{/);
  assert.match(RENDER, /const base = defaultForkName\(sess\?\.name, sid\);/);   // <bare session>-fork (T289: never the viewer's host label)
  assert.match(RENDER, /input\.value = base;/);
  assert.match(RENDER, /if \(!\/\^\[A-Za-z0-9._-\]\+\$\/\.test\(name\)\) \{ input\.classList\.add\("bad"\); input\.focus\(\); return; \}/);
  assert.match(RENDER, /vscodeApi\?\.postMessage\(\{ type: "forkSession", id: sid, uuid, name \}\);/);
  // the instant acknowledgement is the provisional tab, name-joined like a picker create
  assert.match(RENDER, /openProvisional\(\{ name, backend: "sdk", dir: "", host: hostOf\(sid\) \}\);/);
  // both cut semantics are said in the dialog itself
  assert.match(RENDER, /continues the conversation to just below this response/);
  assert.match(RENDER, /continues this whole conversation/);
  assert.match(CSS, /\.fork-name \{ display: block; width: 100%;/);
});

test("the palette forks the ACTIVE session from the tip, via the chat pane", () => {
  assert.match(PALETTE, /id: "session\.fork", title: "Fork this session…"/);
  assert.match(PALETTE, /chatPane\(\)!\.contentWindow!\.postMessage\(\{ romp: "forkSession" \}, "\*"\)/);   // the chat column last worked in (split screen 2026-09-08)
  assert.match(RENDER, /if \(m\.romp === "forkSession"\) \{/);
  assert.match(RENDER, /if \(activeId && !isProvisionalId\(activeId\) && sessions\.get\(activeId\)\) showForkPrompt\(activeId, ""\);/);
});

test("kernel: forkSession is a session op; seeding precedes discoverability; the fsid is pinned to the sid", () => {
  assert.match(KERNEL, /"mcpAction", "forkSession",/);   // in ID_OPS — routed by session id like every session op
  assert.match(KERNEL, /elif t == "forkSession" and msg\.get\("name"\):/);
  // client rides through so only the ASKING dashboard's chat follows the fork (the per-viewer rule)
  assert.match(KERNEL, /def _fork_session\(parent_sid, cut_msg_uuid, new_name, now=None, client=None\):/);
  // the cut means the same thing the edit/delete rewind means: just before the clicked user message
  assert.match(KERNEL, /cut_uuid, err = _rewind_target\(sess\["path"\], parent_sid, str\(cut_msg_uuid\)\)/);
  // the judge stores are seeded BEFORE be.fork writes the names/ entry (discoverability)
  assert.match(KERNEL, /err = _seed_fork_stores\(parent_sid, sid, sess\["path"\], cut_uuid\)[\s\S]{0,200}be\.fork\(nm, parent_sid, cut_uuid, bg, fg, sid=sid\)/);
  // the backend rides the SDK's designed fork contract, with the new fsid PINNED to the romp sid
  assert.match(BACKEND, /kw\["fork_session"\] = True/);
  assert.match(BACKEND, /"forkOf": parent_sid, "forkAt": cut_uuid or ""/);
  // one-shot: the init's lastSid flip spends the flags, so a reconnect resumes the fork's own transcript
  assert.match(BACKEND, /if self\._fork_of and fsid == self\.sid:/);
  assert.match(BACKEND, /self\.backend\._update_reg\(self\.sid, forkOf="", forkAt=""\)/);
  // ...and the names/ entry is written LAST (it is the discoverability trigger): the register under _reg_lock, then the
  // publish inside `if not thread_of:` through _publish_name (the names lock), then the waiting state; until fork PR #813's
  // round 6 the register was _write_reg_locked and the publish a bare write_name, which this pin matched by name
  assert.match(BACKEND, /with self\._reg_lock:\s*\n\s*write_reg\(self\.state_dir, sid, reg\)[\s\S]{0,600}?if not thread_of:\s*\n\s*self\._publish_name\(sid, name, cwd, bg, fg\)\s*\n\s*append_state\(self\.state_dir, sid, "waiting"\)/,
    "fork writes its register under _reg_lock, then publishes the names/ entry inside `if not thread_of:` through _publish_name, then " +
    "appends the waiting state. This pin matches kernel/sdk_backend.py by source text and is the WEAKER guard; if a refactor moved the " +
    "calls, re-key it here and confirm tests/test_sdk_rename_ping.py::NamesFilePublicationsUnderTheLocks::" +
    "test_a_rename_arriving_at_a_forks_names_publish_waits_and_lands_after_it and " +
    "::test_a_forks_record_names_entry_and_waiting_state_land_in_that_order_and_a_thread_fork_skips_the_entry still pass, which is what " +
    "actually guards the property by execution: the names/ entry is the discoverability trigger, written after the register and before " +
    "the waiting state; a thread fork withholds it");
  // _publish_name is the backend's one names writer: write_name under the names lock (the kernel's _NAMES_LOCK when the kernel built it)
  const pubAt = BACKEND.indexOf("    def _publish_name(");
  assert.ok(pubAt >= 0, "_publish_name is defined in kernel/sdk_backend.py (a text pin, the weaker guard; the executed one is " +
    "tests/test_sdk_rename_ping.py::NamesFilePublicationsUnderTheLocks::test_the_constructor_wires_the_names_lock_the_kernel_hands_it)");
  const pub = BACKEND.slice(pubAt, BACKEND.indexOf("\n    def ", pubAt + 1));
  assert.match(pub, /with self\._names_lock:\s*\n\s*write_name\(self\.state_dir, sid, name, cwd, bg, fg\)/,
    "_publish_name calls write_name(self.state_dir, sid, name, cwd, bg, fg) under the names lock. This pin matches kernel/sdk_backend.py " +
    "by source text and is the WEAKER guard; if a refactor moved the write, re-key it here and confirm " +
    "tests/test_sdk_rename_ping.py::NamesFilePublicationsUnderTheLocks::" +
    "test_a_names_publication_waits_for_a_writer_holding_the_names_lock_and_carries_what_it_landed and " +
    "::test_the_constructor_wires_the_names_lock_the_kernel_hands_it still pass, which is what actually guards the property by " +
    "execution: every names/ write the backend makes holds the names lock");
});

// ── branch lineage (the user 2026-08-13: branching must SHOW) ───────────────────────────────────

test("a forked session renders its branch divider, deep-linked to the parent", () => {
  assert.match(RENDER, /\| \{ kind: "branch"; fromSid\?: string; fromName\?: string; cut\?: string/);
  assert.match(RENDER, /if \(ev\.kind === "branch"\) \{/);
  assert.match(RENDER, /label\.dataset\.act = "branchjump"/);
  assert.match(RENDER, /"Branched from " \+ \(ev\.fromName \|\| "another session"\)/);
});

test("the parent wears a chip where each branch departed, jumping to the child's divider", () => {
  assert.match(RENDER, /function applyBranchChips\(sid: string, v: View\)/);
  assert.match(RENDER, /chip\.dataset\.cut = "branch:" \+ k\.cut/);
  assert.match(RENDER, /applyBranchChips\(sid, v\);\s+\/\/ same driver, same hooks/);
  assert.match(RENDER, /branchjump: \(elx\) =>/);
});

test("kernel persists lineage durably and serves it on the session payload", () => {
  // forkOf/forkAt are one-shot launch flags — forkedFrom is the durable record
  assert.match(BACKEND, /reg\["forkedFrom"\] = \{"sid": parent_sid, "name": parent\.get\("name", ""\)/);
  assert.match(BACKEND, /lineage_cut = cut_uuid or last_record_uuid\(/);
  assert.match(BACKEND, /def fork_children\(self\)/);
  assert.match(KERNEL, /"branch": branch, "branches": _kids,/);
  assert.match(KERNEL, /"kind": "branch", "uuid": "branch:" \+ branch\["cut"\]/);
});

test("branch chrome wears the accent, like every highlight", () => {
  const css = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "styles.css"), "utf8");
  // 2026-09-08 (the notice-vocabulary pass): the child's divider is a slim BRANCH notice in the romp severity —
  // the accent on its rail/dot/glyph; the accent hairlines + pill are retired
  assert.match(css, /\.notice-sev-romp\s+\{ --notice-rail: var\(--accent\);/);
  assert.doesNotMatch(css, /\.branch-divider|\.branch-label/);
  assert.match(css, /\.branch-chip \{[^}]*color: var\(--accent\)/s);
});
