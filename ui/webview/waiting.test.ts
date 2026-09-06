// The "Waiting on you" pane (waiting.ts): every session's open user todos across every attached
// machine, one row each, with Reply / Dismiss / open-session. No jsdom harness, so the render is
// pinned at source (the fleet.test.ts idiom); the pieces that are importable run for real
// (federation's prefix + merge of the rows live in feed-user-todos.test.ts; the age words here).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const UI = path.resolve(process.cwd(), "..", "ui", "webview");
const read = (f: string) => fs.readFileSync(path.join(UI, f), "utf8");
const SRC = read("waiting.ts");
const CSS = read("waiting-pane.css");
const ESBUILD = fs.readFileSync(path.resolve(process.cwd(), "esbuild.js"), "utf8");

test("the pane rides the FEED payload and gates its loader on the rows being an ARRAY", () => {
  assert.match(SRC, /if \(m\.type === "feed"\) \{ applyFrame\(m\); return; \}/);
  // "loaded" = the kernel BUILT the rows (the key is present, even if []), never merely "a frame arrived":
  // a frame from a kernel that predates the pane must read "not built", not "nothing waiting"
  assert.match(SRC, /if \(!Array\.isArray\(m\.userTodoRows\)\) return;\s*\n\s*loaded = true;/);
  assert.match(SRC, /if \(!loaded\) return;/, "render leaves the list empty so _pane_spin holds");
  assert.match(SRC, /const _keepLoader = setInterval\(\(\) => \{/);
  assert.match(SRC, /if \(loaded\) \{ clearInterval\(_keepLoader\); return; \}/);
  assert.match(SRC, /vscodeApi\?\.postMessage\(\{ type: "ready" \}\)/, "the ready handshake serves the cached frame");
});

test("a raw feedDelta reaching the pane is loud and re-bases: the feed pane's guard (the 2026-09-05 review)", () => {
  // federation.js applies deltas and re-emits whole `feed` frames; with it absent the shim dispatches the raw
  // frame, and a handler that only matched `feed` sat on its last rows in silence. fleet-live-clock.test.ts
  // runs the Outline's copy of this guard for real; here the source is pinned.
  assert.match(SRC, /if \(m\.type === "feedDelta"\) \{[\s\S]*?console\.error\("waiting: a feedDelta frame reached the pane unapplied[\s\S]*?"feedDelta-unapplied"[\s\S]*?\{ type: "needFullFeed" \}[\s\S]*?return;\n\s*\}/);
  assert.doesNotMatch(SRC, /applyFeedDelta|from "\.\/feed-delta"/, "…and it applies no delta itself");
});

test("the switch is read per frame and per HOST: the local kernel's scalar only", () => {
  assert.match(SRC, /localOn = typeof m\.userTodosOn === "boolean" \? m\.userTodosOn : null;/);
  assert.match(SRC, /let localOn: boolean \| null = null;/);
});

test("three loud states, never a blank: loader / nothing waiting / off on this machine", () => {
  assert.match(SRC, /"Nothing is waiting on you"/);
  assert.match(SRC, /"User todos are off on this machine\. Turn them on in the gear\."/);
  // the empty wordmark never shows while the switch is off (both states ship [] rows — they must read differently)
  assert.match(SRC, /\} else if \(localOn !== false\) \{/);
  assert.match(SRC, /if \(localOn === false\) \{/);
  // the gear one click away: the modal lives in the feed iframe; the shell's own openSettings post
  assert.match(SRC, /getElementById\("f-feed"\)/);
  assert.match(SRC, /postMessage\(\{ romp: "openSettings" \}, "\*"\)/);
  // a host whose rows are pending / unreachable is named, like the feed's per-host strip
  assert.match(SRC, /pendingHosts = Array\.isArray\(m\.pendingHosts\)/);
  assert.match(SRC, /pendingDead = Array\.isArray\(m\.pendingDead\)/);
  assert.match(SRC, /"can’t reach " \+ h \+ ": its rows return when it reconnects"/);
  assert.match(SRC, /"loading rows from " \+ h \+ "…"/);
});

test("rows reuse the split card's two kernel ops UNCHANGED, and open-session brings the chat forward", () => {
  assert.match(SRC, /postMessage\(\{ type: "userTodoAnswer", id: sid, todoId, text \}\)/);
  assert.match(SRC, /postMessage\(\{ type: "userTodoDismiss", id: sid, todoId: tid \}\)/);
  assert.match(SRC, /postMessage\(\{ type: "openSession", id: sid, live: true \}\)/);
  assert.match(SRC, /postMessage\(\{ romp: "reveal", pane: "chat" \}, "\*"\)/);
});

test("the kernel's warn comes back on THIS socket: toast + shell Log + an honest re-sync", () => {
  // feed.ts handles only `err`; the chat's warnToast is lifted here since the ops answer with {type:"warn"}
  assert.match(SRC, /if \(m\.type === "warn" && typeof m\.text === "string" && m\.text\) \{/);
  assert.match(SRC, /function warnToast\(msg: string\): void \{/);
  assert.match(SRC, /notifyShell\("warn", m\.text/);
  assert.match(SRC, /postMessage\(\{ type: "needFullFeed" \}\)/, "a row removed optimistically comes back if still open");
  assert.match(SRC, /window\.parent\?\.postMessage\(\{ romp: "notify", kind, text, sid \}, "\*"\)/);
});

test("one row per todo, OLDEST first; the age is the kernel's clock on the recency ramp", () => {
  assert.match(SRC, /out\.sort\(\(a, b\) => \(a\.todo\.createdT - b\.todo\.createdT\)/);
  assert.match(SRC, /stampAge\(age, w\.todo\.createdT, "plain", true, now, relAge, ageColorReadable\)/);
  assert.match(SRC, /return liveNow\(hostNow, hostNowAt, Date\.now\(\)\);/);
  assert.match(SRC, /hostNowAt = typeof m\.nowAt === "number" \? m\.nowAt : Date\.now\(\);/);
  assert.match(SRC, /const live = liveRefresher\(\{ hidden: paneHidden, pass: \(\) => \{\n\s*refreshAges\(document\.querySelectorAll<HTMLElement>\("\[data-age-t\]"\), nowSec\(\), relAge, ageColorReadable\);/,
    "the 15 s pass runs through the shared visibility gate (feed-age.ts liveRefresher)");
  assert.match(SRC, /setInterval\(live\.tick, 15000\);\n\s*document\.addEventListener\("visibilitychange", live\.catchUp\);\n\s*window\.addEventListener\("resize", live\.catchUp\);/);
  // the session chip: host-prefixed name in the session's identity colour; click opens the chat
  assert.match(SRC, /sess\.replaceChildren\(\.\.\.hostNameNodes\(w\.name \|\| w\.sid, w\.sid\)\)/);
  assert.match(SRC, /sess\.dataset\.act = "open"; sess\.dataset\.sid = w\.sid;/);
  // detail one click away, keyed so the fold survives re-renders, the row SAYS there is more
  assert.match(SRC, /const hint = utDetailHint\(w\.todo\.detail, openDetail\.has\(key\)\)/);
  assert.match(SRC, /function foldKey\(sid: string, tid: string\): string \{ return sid \+ "\|" \+ tid; \}/);
});

test("click-safe: delegated on the stable #waiting-list; Dismiss arm survives a re-render; a tap elsewhere disarms", () => {
  assert.match(SRC, /const list = document\.getElementById\("waiting-list"\);\s*\n\s*if \(!list\) return;\s*\n\s*delegate\(list, \{/);
  for (const act of ["open", "gear", "uttoggle", "utreply", "utdismiss", "openpath"]) assert.match(SRC, new RegExp("\\n    " + act + ": "), act);
  // the armed state lives in a Set keyed like openDetail, NOT on the DOM node, so a feed push that rebuilds
  // the list mid-arm keeps "Really dismiss?" (the 2026-09-03 review: the board re-renders on ANY session's
  // push, so a node-only arm reverted the confirm to a re-arm). rowEl paints the button from the Set.
  assert.match(SRC, /const armedDismiss = new Set<string>\(\);/);
  assert.match(SRC, /const armed = armedDismiss\.has\(key\);\s*\n\s*if \(armed\) dis\.classList\.add\("armed"\);/);
  assert.match(SRC, /dis\.textContent = armed \? "Really dismiss\?" : "Dismiss";/);
  // first tap ARMS via the Set + re-render; second tap confirms; both branches key on the Set, not the node
  assert.match(SRC, /if \(!armedDismiss\.has\(key\)\) \{/);
  assert.match(SRC, /armedDismiss\.add\(key\); render\(\);/);
  assert.match(SRC, /armedDismiss\.delete\(key\);/);
  assert.match(SRC, /vscodeApi\?\.postMessage\(\{ type: "userTodoDismiss"/);
  // one persistent document listener disarms on a tap that is not on an armed button — survives re-renders
  assert.match(SRC, /if \(t && t\.closest\("\.ut-dismiss\.armed"\)\) return;\s*\n\s*armedDismiss\.clear\(\); render\(\);/);
  // a row the user acted on leaves the STATE, not just the DOM, so a re-render before the next frame agrees
  assert.match(SRC, /function dropTodo\(sid: string, tid: string\): void \{/);
  assert.equal((SRC.match(/dropTodo\(sid, (todoId|tid)\)/g) || []).length, 2, "after Reply and after Dismiss");
});

test("the pane never reads `asks` (the feed's placeholder card stays; nothing is listed twice) and never imports federation", () => {
  assert.doesNotMatch(SRC, /\.asks\b/);
  assert.doesNotMatch(SRC, /from "\.\/federation"/, "importing it boots a second FederationManager");
  assert.doesNotMatch(SRC, /fleet/i, "no new fleet identifiers or prose (repo vocabulary rule)");
});

test("the sheet and the bundle are wired: esbuild entries, page layout classes on tokens", () => {
  assert.match(ESBUILD, /"\.\.\/ui\/webview\/waiting\.ts",/);
  assert.match(ESBUILD, /"\.\.\/ui\/webview\/waiting-pane\.css",/);
  for (const sel of ["#waiting-head{", "#waiting-list{", ".wt-item{", ".wt-sess{", ".wt-age{", ".wt-empty,.wt-notice{", ".wt-hostload{"])
    assert.ok(CSS.includes(sel), sel);
  assert.doesNotMatch(CSS, /fleet/i, "no fleet vocabulary in the new sheet");
});

test("the age words are the feed's: sub-minute reads '<1m ago'", () => {
  // run the pane's own copy: lift it out of the source so a drift from feed.ts's shows here
  const m = SRC.match(/function relAge\(sec: number\): string \{[\s\S]*?\n\}/);
  assert.ok(m, "relAge found");
  const relAge = new Function("sec", m![0].replace(/^function relAge\(sec: number\): string /, "")) as (s: number) => string;
  assert.equal(relAge(5), "<1m ago");
  assert.equal(relAge(59), "<1m ago");
  assert.equal(relAge(180), "3m ago");
  assert.equal(relAge(7200), "2h ago");
  assert.equal(relAge(3 * 86400), "3d ago");
});
