// The notices a page is showing when the reload core takes it (reload-notices.ts). The core's restart reload follows
// the last pending ship's retirement on the next task (render.ts endReloadHoldIfIdle, __rompReload.ended()), and the
// nack, the dismissal or the other-tab ack raised in that same task is appended one task before the page goes: the
// toast was never read, and the fresh page's loss toast reads shipsInFlight, which the retirement already emptied. So
// render.ts keeps the
// texts of the toasts on screen in this tab's sessionStorage on the core's synchronous hook and the fresh page shows
// them once. The readings are pure and execute here; render.ts has import-time DOM side effects, so its wiring is
// pinned to source the way reload-restore.test.ts pins the scroll record's. The served scenario (a nack on the last
// ship across a kernel restart; the fresh page says it again, once) is tests/test_ship_reship.py
// NackNoticeSurvivesReload. Synthetic only.
//
// This fork's file also carries the chat page's HOLD on the reload core (the three cases after the notices). The file
// and its module were reload-hold.test.ts / reload-hold.ts until the 2026-09-09 fold, slice 2, when upstream's #1134
// took that name for its hold-reason module (ui/webview/reload-hold.ts, tested by reload-hold.test.ts); upstream's
// #1217 then landed the notices module under this name, and the file follows its text. The hold is upstream's T272
// shape: render.ts answers the core's window.__rompPaneBusy ('upload' while a ship whose ack can still arrive awaits
// it, 'held-send' while the ship gate holds a send) and tells it the ending event through window.__rompReload.ended();
// the fork's 60 s deadline stays in the core as the backstop behind that event (the fold's ruling; the last case here
// pins its shape, tests/test_dashboard_auto_reload.py UploadHoldExecuted runs it) and hands the pane a release note,
// which persistNoticesForReload appends to the kept list (reload-notices.ts releasedNotices, the one divergence from
// upstream's module). The hold's wiring is pinned to source in render.ts and in the core's busyHere; the core's own
// deferral runs in node in tests/test_dashboard_auto_reload.py; the served order (the heal, then the reload) is
// tests/test_ship_reship.py ServedWedge.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { RELOAD_NOTICES_KEY, liveNotices, releasedNotices, keepReloadNotices, takeReloadNotices } from "./reload-notices";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");

const SEL = ".warn-toast:not([data-ephemeral]) .warn-toast-msg";
const box = (texts: (string | null)[]) => ({
  querySelectorAll: (sel: string) => { assert.equal(sel, SEL); return texts.map((t) => ({ textContent: t })); },
});

/** A sessionStorage stand-in: the three calls the module makes over a Map, with a log of them. */
function fakeStore(init: Record<string, string> = {}) {
  const m = new Map(Object.entries(init));
  const calls: string[] = [];
  return {
    m, calls,
    getItem: (k: string) => { calls.push("get " + k); return m.has(k) ? m.get(k)! : null; },
    setItem: (k: string, v: string) => { calls.push("set " + k); m.set(k, v); },
    removeItem: (k: string) => { calls.push("remove " + k); m.delete(k); },
  };
}

test("the toasts on screen read as their texts, in order, blanks dropped; none without the container", () => {
  assert.deepEqual(liveNotices(null), [], "the container is created by the first toast; none yet");
  assert.deepEqual(liveNotices(undefined), []);
  assert.deepEqual(liveNotices(box([])), []);
  assert.deepEqual(liveNotices(box(["shot.png couldn't be saved on the kernel, so it was not attached. Your message was NOT sent.",
                                    "  ", null, "The pending upload was dismissed. Your held message was NOT sent."])),
    ["shot.png couldn't be saved on the kernel, so it was not attached. Your message was NOT sent.",
     "The pending upload was dismissed. Your held message was NOT sent."]);
  assert.deepEqual(liveNotices(box(["  padded  "])), ["padded"], "the text as the toast shows it");
});

test("the reading asks for the toasts without the ephemeral mark: a refusal about a state the fresh page shows for itself stays behind", () => {
  // the staged sends' "Can't send yet" reports a state (the host unreachable, the tab still being created), which the
  // fresh page shows for itself; render.ts marks that toast where it is raised and the selector skips the mark. The
  // mark's effect on a real DOM is executed by tests/test_ship_reship.py NackNoticeSurvivesReload.
  const asked: string[] = [];
  assert.deepEqual(liveNotices({ querySelectorAll: (sel: string) => { asked.push(sel); return [{ textContent: "kept" }]; } }), ["kept"]);
  assert.deepEqual(asked, [SEL]);
});

test("the record is kept only when there is something to say; a page with no toast clears a record left behind", () => {
  const s = fakeStore();
  keepReloadNotices(s, ["one", "two"]);
  assert.deepEqual([...s.m.entries()], [[RELOAD_NOTICES_KEY, JSON.stringify(["one", "two"])]]);
  assert.equal(RELOAD_NOTICES_KEY, "romp:reloadNotices", "this tab's sessionStorage, beside the scroll record's key");
  // a reload the browser refused leaves the record in place; the next core reload with nothing on screen clears it
  keepReloadNotices(s, []);
  assert.equal(s.m.has(RELOAD_NOTICES_KEY), false, "cleared, not written empty");
  assert.deepEqual(s.calls, ["set " + RELOAD_NOTICES_KEY, "remove " + RELOAD_NOTICES_KEY]);
  keepReloadNotices(null, ["x"]);
  keepReloadNotices(undefined, []);
});

test("the record comes out once: strings only, and the key is gone whatever it held", () => {
  const s = fakeStore({ [RELOAD_NOTICES_KEY]: JSON.stringify(["one", "", 3, null, "two"]), other: "kept" });
  assert.deepEqual(takeReloadNotices(s), ["one", "two"]);
  assert.deepEqual([...s.m.keys()], ["other"], "the key is removed; nothing else is touched");
  assert.deepEqual(takeReloadNotices(s), [], "a second take finds nothing");
  assert.deepEqual(s.calls, ["get " + RELOAD_NOTICES_KEY, "remove " + RELOAD_NOTICES_KEY, "get " + RELOAD_NOTICES_KEY],
    "no record, no removal");
  for (const junk of ["not json", JSON.stringify("a string"), JSON.stringify({ a: 1 }), JSON.stringify(null), ""]) {
    const j = fakeStore({ [RELOAD_NOTICES_KEY]: junk });
    assert.deepEqual(takeReloadNotices(j), [], JSON.stringify(junk) + " reads as none");
    assert.equal(j.m.has(RELOAD_NOTICES_KEY), false, JSON.stringify(junk) + " is still cleared");
  }
  assert.deepEqual(takeReloadNotices(null), []);
  assert.deepEqual(takeReloadNotices(undefined), []);
});

test("kept on the page that reloads, taken on the page that follows: the same texts, then nothing", () => {
  const s = fakeStore();
  const texts = liveNotices(box(["shot.png couldn't be saved on the kernel, so it was not attached. Your message was NOT sent."]));
  keepReloadNotices(s, texts);
  assert.deepEqual(takeReloadNotices(s), texts);
  assert.deepEqual(takeReloadNotices(s), []);
});

test("a store that refuses is left alone: nothing thrown from either side", () => {
  const broken = {
    getItem: () => { throw new Error("SecurityError"); },
    setItem: () => { throw new Error("QuotaExceededError"); },
    removeItem: () => { throw new Error("SecurityError"); },
  };
  assert.doesNotThrow(() => keepReloadNotices(broken, ["x"]));
  assert.doesNotThrow(() => keepReloadNotices(broken, []));
  assert.deepEqual(takeReloadNotices(broken), []);
});

// The wiring, pinned to source (render.ts executes nothing under node --test).
test("render.ts: warnToast hands back its toast, and the send refusal about reachability is marked ephemeral where it is raised", () => {
  assert.match(RENDER, /^function warnToast\(msg: string\): HTMLElement \{/m);
  assert.match(RENDER, /setTimeout\(\(\) => t\.remove\(\), 12000\);\n\s*return t;/);
  assert.match(RENDER, /^function ephemeralWarnToast\(msg: string\): void \{ warnToast\(msg\)\.dataset\.ephemeral = "1"; \}/m);
  assert.equal((RENDER.match(/dataset\.ephemeral/g) || []).length, 1, "marked in one place");
  assert.equal((RENDER.match(/ephemeralWarnToast\("Can't send yet — the session isn't reachable\. They stay staged\."\);/g) || []).length, 2,
    "the staged sends' refusal at both of its sites (the strip's Send now and the empty send)");
  // this fork marks a third site (the fold of 2026-09-09, offered upstream as their #1270): the refusal on a disconnected
  // host is true on the page that raised it and false on the page that follows, since the core's restart reload
  // fires from the reopened socket; the count follows the resolved render.ts (R4)
  assert.match(RENDER, /ephemeralWarnToast\(host \+ " is disconnected, so this wasn't sent\./, "the disconnected-host refusal, marked on this fork");
  assert.equal((RENDER.match(/ephemeralWarnToast\(/g) || []).length, 4, "the definition, the two staged-send sites and this fork's disconnected-host site (#1270)");
  // what the nack, the dismissal and the other-tab ack say stays true after the reload, so they ride it unmarked
  assert.match(RENDER, /warnToast\(m\.name \+ " couldn't be saved on the kernel, so it was not attached/);
  assert.match(RENDER, /warnToast\("The pending upload was dismissed — your held message was NOT sent\."\)/);
  assert.match(RENDER, /warnToast\("attachments finished uploading on another tab — the held message was not sent; review it there\."\)/);
});

test("render.ts keeps the notices on the core's hook alone, pagehide keeps the scroll record alone, and the fresh page shows them once after the loss toast", () => {
  assert.match(RENDER, /^import \{ liveNotices, keepReloadNotices, releasedNotices, takeReloadNotices \} from "\.\/reload-notices";/m,
    "upstream's three readings plus this fork's releasedNotices (the core's release note; R-a)");
  // the ONE divergence from upstream's call (R-a, the 4d-1 fold): the core's release note (releasedNotices: the 60 s backstop
  // released a hold that never ended; none when the reload fired on the hold's own event) is appended to the kept list
  assert.match(RENDER, /^function persistNoticesForReload\(\): void \{\n\s*try \{ keepReloadNotices\(sessionStorage, liveNotices\(document\.getElementById\("warn-toasts"\)\)\.concat\(releasedNotices\(\(window as any\)\.__rompReload\)\)\); \} catch \{ \/\* ignore \*\/ \}\n\}/m);
  assert.equal((RENDER.match(/releasedNotices\(/g) || []).length, 1, "the release note is read in that one place");
  // the core's synchronous hook writes both records; a navigation of the user's own (pagehide) writes the scroll record
  // alone, so a load they asked for does not replay a toast they were already looking at
  assert.match(RENDER, /^function persistForReload\(\): void \{ persistScrollForReload\(\); persistNoticesForReload\(\); \}[^\n]*\n\(window as any\)\.__rompPersistForReload = persistForReload;\nwindow\.addEventListener\("pagehide", persistScrollForReload\);/m);
  assert.equal((RENDER.match(/persistNoticesForReload\(\)/g) || []).length, 2, "defined once, called from the core's hook alone");
  const scroll = RENDER.match(/^function persistScrollForReload\(\): void \{([\s\S]*?)\n\}/m);
  assert.ok(scroll && !scroll[1].includes("Notices"), "the scroll record is untouched");
  // the replay follows the loss toast's block directly: the loss first, then what the last page was saying
  assert.match(RENDER, /shipsInFlight: \[\] \}\);\n\s*\}\n\s*\}\n\} catch \{ \/\* ignore \*\/ \}\n(\/\/[^\n]*\n)*try \{ for \(const text of takeReloadNotices\(sessionStorage\)\) warnToast\(text\); \} catch \{ \/\* ignore \*\/ \}/);
  assert.equal((RENDER.match(/takeReloadNotices\(/g) || []).length, 1, "consumed once, at load");
  assert.equal((RENDER.match(/keepReloadNotices\(/g) || []).length, 1, "written from one place");
});

// The chat page's HOLD on the reload core (this fork's cases; see the header). RETIRED at the 2026-09-09 upstream fold
// (the auto-reload series ruling): the fork's publishReloadHold truth table (window.__rompReloadHold) had no reader once the
// core asked the pane's window.__rompPaneBusy instead; the hold's truth is the first case below.
test("render.ts holds the reload through the core's own question: 'upload' while a ship whose ack can still arrive awaits it, 'held-send' while the ship gate holds a send, and tells the core the ending event", () => {
  // re-aimed from the fork's four publishReloadHold publishes (the same fold ruling as the retirement above): the shim's
  // reasons first, then the pane's two, read by the core at every tryFire instead of published at every change. Re-aimed
  // again at the 2026-09-09 fold (slice 2, upstream #1134; R4, the pin follows the resolved code): the pane's two reasons
  // come from reload-hold.ts reloadHoldReason, which answers 'upload' only for a ship whose host can still deliver the
  // ack (reload-hold.test.ts pins its table); the words handed to the core are unchanged, so the core's 60 s backstop
  // (the last test here) clocks the same words
  assert.match(RENDER, /const shimBusy = \(window as any\)\.__rompPaneBusy as \(\(\) => string\) \| undefined;\n\s*\(window as any\)\.__rompPaneBusy = \(\): string => \{\n\s*const b = shimBusy \? shimBusy\(\) : "";\n\s*if \(b\) return b;\n(?:\s*\/\/[^\n]*\n)*\s*return reloadHoldReason\(\[\.\.\.pendingShips\.keys\(\)\], shipGateSid, \(window as any\)\.__rompFed\);\n\s*\};/,
    "the pane wraps the shim's word and answers its own two reasons after it, through reload-hold.ts's reason");
  assert.match(RENDER, /^import \{ reloadHoldReason \} from "\.\/reload-hold";/m, "upstream's hold module beside this one");
  assert.ok(!/return "upload";|return "held-send";/.test(RENDER), "the pane's own two-line answer is gone: the reason is the module's");
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

test("the core's release note reads as one notice, and as none from no core, an older core, a silent one or a throwing one", () => {
  // the fold's deadline backstop: the core hands the pane the reason it reloaded over a hold that never ended, through
  // window.__rompReload.released(); persistNoticesForReload appends this reading to the live toasts (the .concat pin in the render.ts case above)
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
  // note released() hands the pane. After the fold's review (F1/UI-1, UI-2, F2) and its verification (findings A and D): the
  // clock is the clocked pane word's, read from the paneWord busy()'s walk records; busy() reads each window's gesture
  // (busyHere) and its pane word (paneHere, the window's __rompPaneBusy alone) apart, so a gesture (the GESTURE set) in any
  // window, the word's own pane included, neither clocks nor resets it and only defers a release past the deadline to its
  // own ending event; the shim's 'sends' (the NOCLOCK set) is a pane word with no deadline, reported ahead of a clocked
  // word and deferring a release past the deadline like a gesture; a refused reload persists once more without the note;
  // busy() still ranks a gesture anywhere above every pane word for the word it reports (the fold-4 review's K1)
  const core = KERNEL.slice(KERNEL.indexOf("/*reload-core*/"), KERNEL.indexOf("/*end-reload-core*/"));
  assert.ok(core.length > 0, "the core's anchors exist");
  assert.match(core, /if\(editing\(\)\)return 'typing';\nreturn paneHere\(\);\}\nfunction paneHere\(\)\{try\{if\(window\.__rompPaneBusy\)\{var b=window\.__rompPaneBusy\(\);if\(b\)return String\(b\);\}\}catch\(e\)\{\}return '';\}/,
    "the pane's word is the last reason busyHere gives, and paneHere reads that word alone (the one reader of __rompPaneBusy)");
  assert.equal((core.match(/window\.__rompPaneBusy/g) || []).length, 2, "read in paneHere alone (the existence check and the call)");
  // the 2026-09-09 fold, slice 2 (upstream #1134): inside the deferral the core also tells the page it is held, once per
  // owed request and reason (heldFor), through R.held; the clock still wraps the word first, so a held reload wears
  // upstream's line at once and the fork's backstop releases it past 60 s. Two mechanisms, no third.
  assert.match(core, /^var heldFor=null;\nfunction tryFire\(\)\{[^\n]*var b=clock\(busy\(\)\);if\(b\)\{R\.waiting=b;var hk=key\(owed\)\+'\|'\+b;if\(hk!==heldFor\)\{heldFor=hk;if\(R\.held\)R\.held\(b,owed\);\}return;\}R\.waiting='';fire\(\);\}/m,
    "tryFire defers on the word clock() hands back, says which, and tells the held hook once per (request, reason); an empty answer (nothing holds, or the word was released) fires");
  assert.match(core, /,refused:null,held:null,waiting:'',/, "the held hook sits on R beside the refusal latch, unset until a page installs it");
  assert.match(core, /function ended\(\)\{setTimeout\(function\(\)\{var s=shell\(\);if\(s\)s\.tryFire\(\);else tryFire\(\);\},0\);\}/, "the ending event re-tries, in the shell when there is one");
  assert.match(core, /var R=\{request:request,tryFire:tryFire,ended:ended,busyHere:busyHere,paneHere:paneHere,busy:busy,/, "ended() is the pane's door (render.ts endReloadHoldIfIdle calls it); paneHere is exported after busyHere, so a shell reads a pane's word behind its gesture");
  // the backstop's shape
  assert.match(core, /^var DEADLINE=60000,heldKind='',heldT=0,heldTimer=null,overdueNote='',paneWord='',GESTURE=\{pointer:1,pan:1,drag:1,selection:1,typing:1\},NOCLOCK=\{sends:1\};/m,
    "one deadline, one clock, the clocked pane word behind any gesture, the core's five gesture words exempt, the shim's 'sends' with no deadline");
  assert.match(core, /^function clock\(b\)\{var kind=paneWord;if\(kind!==heldKind\)\{unclock\(\);heldKind=kind;heldT=kind\?Date\.now\(\):0;\}\n/m,
    "the clock is the clocked pane word's whatever busy() reported (paneWord holds only clocked words): a change of pane word (or nothing) resets it");
  assert.match(core, /if\(age<DEADLINE\)\{if\(!heldTimer\)heldTimer=setTimeout\(function\(\)\{heldTimer=null;tryFire\(\);\},DEADLINE-age\);return b;\}\nif\(GESTURE\[b\]\|\|NOCLOCK\[b\]\)return b;/, "one timer for the time left, never a re-check; past the deadline a gesture or a no-deadline word defers the release to its own ending event");
  assert.match(core, /function what\(k\)\{return k==='upload'\?'An upload':k==='held-send'\?'A message held behind an upload':"A '"\+k\+"' hold";\}/, "no note words 'sends': it is never released");
  assert.doesNotMatch(core, /'sends'\?/, "no 'sends' arm in what()");
  assert.match(core, /catch\(e\)\{fired=false;refusedFor=key\(owed\);unclock\(\);if\(overdueNote\)\{overdueNote='';persist\(\);\}R\.waiting='refused';/, "a refused reload drops the note and the clock and persists once more, so the panes' stored toasts drop the note (the fold's review, F2)");
  assert.match(core, /console\.warn\("romp: the '"\+kind\+"' hold did not end within "\+secs\+" s; reloading anyway"\)/, "the console line names the word");
  assert.match(core, /overdueNote=what\(kind\)\+' had not finished after '\+secs\+' s, so the page reloaded without waiting longer\.';/, "the note the pane persists");
  assert.match(core, /^released:function\(\)\{var s=shell\(\);return \(s&&s\.released\)\?s\.released\(\):overdueNote;\},/m, "released() answers with the shell's note when a shell decided");
  assert.match(core, /^function busy\(\)\{var g='',nc='',held='';function take\(b,p\)\{if\(b&&GESTURE\[b\]\)\{if\(!g\)g=b;b=p;\}if\(!b\)return;if\(NOCLOCK\[b\]\)\{if\(!nc\)nc=b;\}else if\(!held\)held=b;\}\ntake\(busyHere\(\),paneHere\(\)\);var ps=panes\(\);for\(var i=0;i<ps\.length;i\+\+\)\{var r=ps\[i\]\.__rompReload;take\(r\.busyHere\(\),r\.paneHere\?r\.paneHere\(\):''\);\}paneWord=held;return g\|\|nc\|\|held;\}/m,
    "each window's gesture and its pane word are taken apart (a gesture stands aside for the paneHere word behind it; a pane without paneHere falls back to its busyHere word), paneWord is the first clocked pane word, and the word reported is a gesture anywhere, then a no-deadline word, then the clocked word");
  assert.doesNotMatch(core, /,500\)/, "no 500 ms re-check");
  assert.ok(!core.includes("__rompReloadHold") && !core.includes("shipsHold") && !core.includes("HOLD_MAX"), "the fork's 'ships' route is gone from the core; the backstop has its own names");
});
