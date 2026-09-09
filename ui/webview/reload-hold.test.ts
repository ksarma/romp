// The chat page's hold on the reload core and the notices that ride the reload (reload-hold.ts). The hold is
// upstream's T272 shape since the 2026-09-09 fold: render.ts answers the core's window.__rompPaneBusy ('upload' while a
// ship awaits its ack, 'held-send' while the ship gate holds a send) and tells it the ending event through
// window.__rompReload.ended(); the wiring is pinned at the source level the way the other webview tests pin render.ts
// (no jsdom harness), in render.ts and in the core's busyHere. The core's own deferral runs in node in
// tests/test_dashboard_auto_reload.py; the served order (the heal, then the reload) is tests/test_ship_reship.py
// ServedWedge. The notices half is pure here and runs executably. Synthetic only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { liveNotices, takePendingNotices } from "./reload-hold";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");

// RETIRED at the 2026-09-09 upstream fold (the auto-reload series ruling; the fold's kernel-code log H20-H22 and the
// chat-code log's flag (a)): "the word is true while any ship awaits its ack and false otherwise, and it exists once
// published" ran reload-hold.ts publishReloadHold's truth table (window.__rompReloadHold, the fork's fold-4 word). The
// core (kernel.py _RELOAD_CORE_JS) no longer reads that word: upstream's T272 hold asks the pane's window.__rompPaneBusy
// instead, so the publisher had no reader and the export went with it. The hold's truth is the test below now.

test("render.ts holds the reload through the core's own question: 'upload' while any ship awaits its ack, 'held-send' while the ship gate holds a send, and tells the core the ending event", () => {
  // re-aimed from the fork's four publishReloadHold publishes (the same fold ruling as the retirement above): the shim's
  // reasons first, then the pane's two, read by the core at every tryFire instead of published at every change
  assert.match(RENDER, /const shimBusy = \(window as any\)\.__rompPaneBusy as \(\(\) => string\) \| undefined;\n\s*\(window as any\)\.__rompPaneBusy = \(\): string => \{\n\s*const b = shimBusy \? shimBusy\(\) : "";\n\s*if \(b\) return b;\n\s*if \(pendingShips\.size\) return "upload";\n\s*if \(shipGateSid\) return "held-send";\n\s*return "";\n\s*\};/,
    "the pane wraps the shim's word and answers its own two reasons after it");
  assert.equal((RENDER.match(/\(window as any\)\.__rompPaneBusy/g) || []).length, 2, "read once, assigned once: the wrapper is the one place the pane touches the word (comments aside)");
  // the ENDING event: the core re-tries only on gesture ends, blur, a fresh request or the shell's poll, so the pane says
  // when its hold is over, and says nothing while a ship or a held send is still pending
  assert.match(RENDER, /^function endReloadHoldIfIdle\(\): void \{\n\s*if \(pendingShips\.size \|\| shipGateSid\) return;\n\s*try \{ \(window as any\)\.__rompReload\?\.ended\?\.\(\); \} catch \{[^\n]*\}\n\}/m);
  // an ack, a nack or a FileReader failure retires a ship
  assert.match(RENDER, /if \(!list\.length\) pendingShips\.delete\(id\);\n\s*persistDrafts\(\);\n\s*if \(id === activeId\) renderComposerFiles\(id\);\n\s*endReloadHoldIfIdle\(\);/, "a retired ship");
  // the user dismisses a pending chip (after the settle that clears the gate, so the one call reads both)
  assert.match(RENDER, /if \(!list\.length && id\) pendingShips\.delete\(id\);\n\s*persistDrafts\(\);[^\n]*\n(?:\s*\/\/[^\n]*\n)*\s*if \(id && !\(pendingShips\.get\(id\) \|\| \[\]\)\.length\) \{\n\s*const held = sendOnShip\.delete\(id\);\n\s*const gateWasOpen = shipGateSid === id;\n\s*if \(gateWasOpen\) \{ shipGateSid = null; closeConfirm\(null\); \}\n\s*if \(held \|\| gateWasOpen\) warnToast\([^\n]*\n\s*\}\n\s*endReloadHoldIfIdle\(\);/, "the dismissed chip, after the settle that clears the gate");
  // the ship gate lets go: the last ship's ack fires the held send, a nack cancels it, the user's own pick decides
  assert.match(RENDER, /if \(owner === activeId\) fireHeldSend\(\);\n\s*else warnToast\("attachments finished uploading on another tab[^\n]*\n\s*endReloadHoldIfIdle\(\);/, "the held send posted");
  assert.match(RENDER, /if \(gateWasOpen\) \{ shipGateSid = null; closeConfirm\(null\); \}[^\n]*\n\s*endReloadHoldIfIdle\(\);\n\s*warnToast\(m\.name \+ " couldn't be saved on the kernel/, "the nack");
  assert.match(RENDER, /shipGateSid = null; endReloadHoldIfIdle\(\);\n\s*if \(v === "now"\)/, "the gate's own dialog (composer-ship-gate.test pins the same line)");
  assert.equal((RENDER.match(/endReloadHoldIfIdle\(\)/g) || []).length, 6, "defined once, called at the five ending sites");
  // the fork's word is gone from the page, not published beside the pane's answer
  assert.ok(!RENDER.includes("__rompReloadHold") && !RENDER.includes("publishReloadHold"), "no second hold word");
});

// The notices a reload wipes (the fourth fold's review, F2): the ack and nack toasts raised when the LAST pending ship
// retires die with the reload that follows within the core's re-check, so render.ts snapshots the toasts on screen into
// the persisted state on the pre-reload hook and shows them again once at load. The served scenario (a nack on the last
// ship across a restart; the fresh page shows the notice, once) is tests/test_ship_reship.py NackNoticeSurvivesReload.
test("the toasts on screen read as their texts, in order, blanks dropped; none without the container", () => {
  const box = (texts: (string | null)[]) => ({ querySelectorAll: (sel: string) => { assert.equal(sel, ".warn-toast:not([data-ephemeral]) .warn-toast-msg"); return texts.map((t) => ({ textContent: t })); } });
  assert.deepEqual(liveNotices(null), [], "the container is created by the first toast; none yet");
  assert.deepEqual(liveNotices(undefined), []);
  assert.deepEqual(liveNotices(box([])), []);
  assert.deepEqual(liveNotices(box(["shot.png was not saved on the kernel. Your message was NOT sent.", "  ", null, "the held message was not sent"])),
    ["shot.png was not saved on the kernel. Your message was NOT sent.", "the held message was not sent"]);
});

test("a toast about the connection itself is not replayed: marked data-ephemeral where it is raised, left out by the reading", () => {
  // the restart reload fires from the reopened socket, so "the session isn't reachable" or "<host> is disconnected, romp is
  // re-dialing" shown again on the fresh page would tell a connected page it is disconnected; the nack and the other-tab
  // ack (F2's two notices) say things that stay true and ride the reload unmarked
  assert.match(RENDER, /^function warnToast\(msg: string\): HTMLElement \{/m, "the signature upstream's warn-toast.test.ts pins, with the toast handed back");
  assert.match(RENDER, /setTimeout\(\(\) => t\.remove\(\), 12000\);\n\s*return t;/);
  assert.match(RENDER, /^function ephemeralWarnToast\(msg: string\): void \{ warnToast\(msg\)\.dataset\.ephemeral = "1"; \}/m);
  assert.equal((RENDER.match(/dataset\.ephemeral/g) || []).length, 1, "marked in one place");
  assert.equal((RENDER.match(/ephemeralWarnToast\("Can't send yet \u2014 the session isn't reachable\. They stay staged\."\);/g) || []).length, 2, "the staged sends' two refusals");
  assert.match(RENDER, /ephemeralWarnToast\(host \+ " is disconnected, so this wasn't sent\./, "the down-host refusal");
  assert.equal((RENDER.match(/ephemeralWarnToast\(/g) || []).length, 4, "the definition and the three connectivity sites");
  assert.match(RENDER, /warnToast\(m\.name \+ " couldn't be saved on the kernel, so it was not attached/, "the nack rides the reload");
  assert.match(RENDER, /else warnToast\("attachments finished uploading on another tab/, "the other-tab ack rides the reload");
  // the reading asks the DOM for the toasts without the mark: the skip is the selector's
  const asked: string[] = [];
  assert.deepEqual(liveNotices({ querySelectorAll: (sel: string) => { asked.push(sel); return [{ textContent: "kept" }]; } }), ["kept"]);
  assert.deepEqual(asked, [".warn-toast:not([data-ephemeral]) .warn-toast-msg"]);
});

test("the persisted notices come out once: strings only, and the state handed back has no key left", () => {
  assert.deepEqual(takePendingNotices(null), { notices: [], rest: {} });
  assert.deepEqual(takePendingNotices(undefined), { notices: [], rest: {} });
  assert.deepEqual(takePendingNotices("junk"), { notices: [], rest: {} });
  assert.deepEqual(takePendingNotices({ drafts: { a: "x" } }), { notices: [], rest: { drafts: { a: "x" } } }, "nothing recorded: the state as it was");
  assert.deepEqual(takePendingNotices({ drafts: { a: "x" }, pendingNotices: "nope" }), { notices: [], rest: { drafts: { a: "x" } } }, "a wrong-typed record reads as none and still clears");
  assert.deepEqual(takePendingNotices({ pendingNotices: ["one", "", 3, null, "two"], shipsInFlight: [] }), { notices: ["one", "two"], rest: { shipsInFlight: [] } });
});

test("render.ts snapshots the toasts on the CORE's pre-reload hook only (not on pagehide: a navigation of the user's own says nothing twice) and shows them again once at load, after the loss toast", () => {
  assert.match(RENDER, /import \{ liveNotices, takePendingNotices \} from "\.\/reload-hold";/, "the module's two readings; the hold is __rompPaneBusy (the test above)");
  assert.match(RENDER, /^function persistNoticesForReload\(\): void \{\n\s*try \{ if \(vscodeApi\?\.setState\) vscodeApi\.setState\(\{ \.\.\.\(vscodeApi\.getState\(\) \|\| \{\}\), pendingNotices: liveNotices\(document\.getElementById\("warn-toasts"\)\) \}\); \} catch \{ \/\* ignore \*\/ \}\n\}/m,
    "the texts of the live toasts, into the same state the drafts and shipsInFlight ride");
  // the core's hook writes both records; pagehide writes the scroll record alone (reload-restore.test.ts pins those two lines
  // too), so a reload the user asks for does not replay a toast they were already looking at: ReloadLossToast's one warning
  assert.match(RENDER, /function persistForReload\(\): void \{ persistScrollForReload\(\); persistNoticesForReload\(\); \}[^\n]*\n\(window as any\)\.__rompPersistForReload = persistForReload;\nwindow\.addEventListener\("pagehide", persistScrollForReload\);/);
  assert.equal((RENDER.match(/persistNoticesForReload\(\)/g) || []).length, 2, "defined once, called from the core's hook alone");
  const scroll = RENDER.match(/^function persistScrollForReload\(\): void \{([\s\S]*?)\n\}/m);
  assert.ok(scroll && !scroll[1].includes("persistNoticesForReload"), "upstream's scroll record is untouched");
  assert.equal((RENDER.match(/pendingNotices:/g) || []).length, 1, "written in one place; the reading goes through takePendingNotices");
  // the replay follows the loss toast's block directly (the load-time publish that once sat between them retired with
  // the fork's hold word): the loss first, then what the last page was saying; the record is cleared in the same block,
  // before the toasts are raised (one reload, one replay). The record is cleared whenever the key is there (an empty
  // record too, so `pendingNotices: []` from a no-toast reload does not sit in the state), and the toasts are raised
  // after the write
  assert.match(RENDER, /shipsInFlight: \[\] \}\);\n\s*\}\n\s*\}\n\} catch \{ \/\* ignore \*\/ \}\n(\/\/.*\n)*try \{\n\s*const st = vscodeApi\?\.getState\?\.\(\);\n\s*const taken = takePendingNotices\(st\);\n\s*if \(st && typeof st === "object" && "pendingNotices" in st\) vscodeApi\?\.setState\?\.\(taken\.rest\);\n\s*for \(const text of taken\.notices\) warnToast\(text\);\n\} catch \{ \/\* ignore \*\/ \}/);
  assert.equal((RENDER.match(/takePendingNotices\(/g) || []).length, 1, "consumed once, at load");
});

test("the reload core asks the pane's word after the gesture holds, defers while it answers, and re-tries on the pane's ended()", () => {
  // re-aimed at the 2026-09-09 fold (kernel-code H20-H22): the core's busyHere ends on the pane's __rompPaneBusy, after
  // its own reasons (pointer, pan, drag, selection, typing); the fork's 'ships' read, its re-check timer and its 60 s
  // deadline are gone (upstream's hold has no deadline: a hold ends on the pane's event, the review's stated gap)
  const core = KERNEL.slice(KERNEL.indexOf("/*reload-core*/"), KERNEL.indexOf("/*end-reload-core*/"));
  assert.ok(core.length > 0, "the core's anchors exist");
  assert.match(core, /if\(editing\(\)\)return 'typing';\ntry\{if\(window\.__rompPaneBusy\)\{var b=window\.__rompPaneBusy\(\);if\(b\)return String\(b\);\}\}catch\(e\)\{\}\nreturn '';\}/,
    "the pane's word is the last reason busyHere gives");
  assert.match(core, /function tryFire\(\)\{[^\n]*var b=busy\(\);if\(b\)\{R\.waiting=b;return;\}R\.waiting='';fire\(\);\}/, "tryFire defers on any busy word instead of reloading now, and says which");
  assert.match(core, /function ended\(\)\{setTimeout\(function\(\)\{var s=shell\(\);if\(s\)s\.tryFire\(\);else tryFire\(\);\},0\);\}/, "the ending event re-tries, in the shell when there is one");
  assert.match(core, /var R=\{request:request,tryFire:tryFire,ended:ended,busyHere:busyHere,/, "ended() is the pane's door (render.ts endReloadHoldIfIdle calls it)");
  assert.ok(!core.includes("__rompReloadHold") && !core.includes("shipsHold") && !core.includes("HOLD_MAX"), "the fork's 'ships' route is gone from the core");
});
