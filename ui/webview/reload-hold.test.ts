// The chat page's hold on the reload core and the notices that ride the reload (reload-hold.ts). The hold is
// upstream's T272 shape since the 2026-09-09 fold: render.ts answers the core's window.__rompPaneBusy ('upload' while a
// ship awaits its ack, 'held-send' while the ship gate holds a send) and tells it the ending event through
// window.__rompReload.ended(); the fork's 60 s deadline stays in the core as the backstop behind that event (the fold's
// ruling; the last test here pins its shape, tests/test_dashboard_auto_reload.py UploadHoldExecuted runs it). The wiring
// is pinned at the source level the way the other webview tests pin render.ts (no jsdom harness), in render.ts and in
// the core's busyHere. The core's own deferral runs in node in tests/test_dashboard_auto_reload.py; the served order
// (the heal, then the reload) is tests/test_ship_reship.py ServedWedge. The notices half is pure here and runs
// executably. Synthetic only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { liveNotices, releasedNotices, takePendingNotices } from "./reload-hold";

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
  assert.match(RENDER, /import \{ liveNotices, releasedNotices, takePendingNotices \} from "\.\/reload-hold";/, "the module's three readings; the hold is __rompPaneBusy (the test above)");
  assert.match(RENDER, /^function persistNoticesForReload\(\): void \{\n\s*try \{ if \(vscodeApi\?\.setState\) vscodeApi\.setState\(\{ \.\.\.\(vscodeApi\.getState\(\) \|\| \{\}\), pendingNotices: liveNotices\(document\.getElementById\("warn-toasts"\)\)\.concat\(releasedNotices\(\(window as any\)\.__rompReload\)\) \}\); \} catch \{ \/\* ignore \*\/ \}\n\}/m,
    "the texts of the live toasts, then the core's release note if a hold ran past its deadline, into the same state the drafts and shipsInFlight ride");
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

test("the core's release note reads as one notice, and as none from no core, an older core, a silent one or a throwing one", () => {
  // the fold's deadline backstop: the core hands the pane the reason it reloaded over a hold that never ended, through
  // window.__rompReload.released(); persistNoticesForReload appends this reading to the live toasts (the pinned wiring below)
  assert.deepEqual(releasedNotices(null), [], "a page without the core (the VS Code webview)");
  assert.deepEqual(releasedNotices(undefined), []);
  assert.deepEqual(releasedNotices({ request() { /* no released() */ } }), [], "an older core without the accessor");
  assert.deepEqual(releasedNotices({ released: () => "" }), [], "a reload that fired on the hold's own event");
  assert.deepEqual(releasedNotices({ released: () => null }), []);
  assert.deepEqual(releasedNotices({ released: "not a function" }), []);
  assert.deepEqual(releasedNotices({ released: () => { throw new Error("cross-origin"); } }), [], "a foreign parent's refusal is none, not a throw");
  const core = { note: "An upload had not finished after 60 s, so the page reloaded without waiting longer.", released() { return this.note; } };
  assert.deepEqual(releasedNotices(core), [core.note], "read on the core itself (the accessor reaches its shell through the core's own closure)");
});

test("the reload core asks the pane's word after the gesture holds, defers while it answers, re-tries on the pane's ended(), and releases the word at its deadline (the shim's 'sends' excepted)", () => {
  // re-aimed at the 2026-09-09 fold (kernel-code H20-H22, then the fold's ruling on the fork's deadline): the core's busyHere
  // ends on the pane's __rompPaneBusy, after its own reasons (pointer, pan, drag, selection, typing); the fork's 'ships' read
  // and its 500 ms re-check are gone, and its 60 s deadline is the BACKSTOP inside upstream's shape: tryFire runs the word
  // through clock(), which arms one timer for the time left and releases the word past DEADLINE with a console line and the
  // note released() hands the pane. After the fold's review (F1/UI-1, UI-2, F2): the clock is the pane word's, read from the
  // paneWord busy()'s walk records, so a gesture (the GESTURE set) neither clocks nor resets it and only defers a release
  // past the deadline to its own ending event; the shim's 'sends' (the NOCLOCK set) is a pane word with no deadline; a
  // refused reload persists once more without the note; busy() still ranks a gesture anywhere above a pane word for the
  // word it reports (the fold-4 review's K1)
  const core = KERNEL.slice(KERNEL.indexOf("/*reload-core*/"), KERNEL.indexOf("/*end-reload-core*/"));
  assert.ok(core.length > 0, "the core's anchors exist");
  assert.match(core, /if\(editing\(\)\)return 'typing';\ntry\{if\(window\.__rompPaneBusy\)\{var b=window\.__rompPaneBusy\(\);if\(b\)return String\(b\);\}\}catch\(e\)\{\}\nreturn '';\}/,
    "the pane's word is the last reason busyHere gives");
  assert.match(core, /function tryFire\(\)\{[^\n]*var b=clock\(busy\(\)\);if\(b\)\{R\.waiting=b;return;\}R\.waiting='';fire\(\);\}/, "tryFire defers on the word clock() hands back, and says which; an empty answer (nothing holds, or the word was released) fires");
  assert.match(core, /function ended\(\)\{setTimeout\(function\(\)\{var s=shell\(\);if\(s\)s\.tryFire\(\);else tryFire\(\);\},0\);\}/, "the ending event re-tries, in the shell when there is one");
  assert.match(core, /var R=\{request:request,tryFire:tryFire,ended:ended,busyHere:busyHere,/, "ended() is the pane's door (render.ts endReloadHoldIfIdle calls it)");
  // the backstop's shape
  assert.match(core, /^var DEADLINE=60000,heldKind='',heldT=0,heldTimer=null,overdueNote='',paneWord='',GESTURE=\{pointer:1,pan:1,drag:1,selection:1,typing:1\},NOCLOCK=\{sends:1\};/m,
    "one deadline, one clock, the pane word behind a gesture, the core's five gesture words exempt, the shim's 'sends' with no deadline");
  assert.match(core, /^function clock\(b\)\{var kind=\(paneWord&&!NOCLOCK\[paneWord\]\)\?paneWord:'';if\(kind!==heldKind\)\{unclock\(\);heldKind=kind;heldT=kind\?Date\.now\(\):0;\}\n/m,
    "the clock is the pane word's whatever busy() reported: a change of pane word (or nothing) resets it, a no-deadline word runs none");
  assert.match(core, /if\(age<DEADLINE\)\{if\(!heldTimer\)heldTimer=setTimeout\(function\(\)\{heldTimer=null;tryFire\(\);\},DEADLINE-age\);return b;\}\nif\(GESTURE\[b\]\)return b;/, "one timer for the time left, never a re-check; past the deadline a gesture defers the release to its own ending event");
  assert.match(core, /function what\(k\)\{return k==='upload'\?'An upload':k==='held-send'\?'A message held behind an upload':"A '"\+k\+"' hold";\}/, "no note words 'sends': it is never released");
  assert.doesNotMatch(core, /'sends'\?/, "no 'sends' arm in what()");
  assert.match(core, /catch\(e\)\{fired=false;refusedFor=key\(owed\);unclock\(\);if\(overdueNote\)\{overdueNote='';persist\(\);\}R\.waiting='refused';/, "a refused reload drops the note and the clock and persists once more, so the panes' stored toasts drop the note (the fold's review, F2)");
  assert.match(core, /console\.warn\("romp: the '"\+kind\+"' hold did not end within "\+secs\+" s; reloading anyway"\)/, "the console line names the word");
  assert.match(core, /overdueNote=what\(kind\)\+' had not finished after '\+secs\+' s, so the page reloaded without waiting longer\.';/, "the note the pane persists");
  assert.match(core, /^released:function\(\)\{var s=shell\(\);return \(s&&s\.released\)\?s\.released\(\):overdueNote;\},/m, "released() answers with the shell's note when a shell decided");
  assert.match(core, /^function busy\(\)\{var g='',held='',b=busyHere\(\);if\(b&&GESTURE\[b\]\)g=b;else held=b;[^\n]*paneWord=held;return g\|\|held;\}/m, "a gesture anywhere outranks a pane word for the word reported, and the walk runs to its end to record the pane word for clock()");
  assert.doesNotMatch(core, /,500\)/, "no 500 ms re-check");
  assert.ok(!core.includes("__rompReloadHold") && !core.includes("shipsHold") && !core.includes("HOLD_MAX"), "the fork's 'ships' route is gone from the core; the backstop has its own names");
});
