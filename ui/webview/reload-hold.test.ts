// The chat page's hold on the reload core (reload-hold.ts): pure, so the word's truth table runs executably, and
// the wiring is pinned at the source level the way the other webview tests pin render.ts (no jsdom harness): the
// three places pendingShips changes publish it, the load-time publish, and the core's read of the word. The
// core's own deferral (the re-check timer, the deadline) runs in node in tests/test_dashboard_auto_reload.py;
// the served order (the heal, then the reload) is tests/test_ship_reship.py ServedWedge. Synthetic only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { publishReloadHold, liveNotices, takePendingNotices, type ReloadHoldHost } from "./reload-hold";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");

test("the word is true while any ship awaits its ack and false otherwise, and it exists once published", () => {
  const w: ReloadHoldHost = {};
  assert.equal("__rompReloadHold" in w, false, "nothing published yet");
  assert.equal(publishReloadHold(0, w), false);
  assert.equal(w.__rompReloadHold, false, "published as false, not left unset: the core's read is a strict === true");
  assert.equal(publishReloadHold(1, w), true);
  assert.equal(w.__rompReloadHold, true);
  assert.equal(publishReloadHold(3, w), true, "more ships, still one hold");
  assert.equal(publishReloadHold(0, w), false, "the last ack clears it");
  assert.equal(w.__rompReloadHold, false);
});

test("render.ts publishes it at every change to pendingShips and once at load", () => {
  // a ship starts
  assert.match(RENDER, /pendingShips\.set\(id, list\);\n\s*publishReloadHold\(pendingShips\.size\);/);
  // an ack, a nack or a FileReader failure retires one
  assert.match(RENDER, /if \(!list\.length\) pendingShips\.delete\(id\);\n\s*publishReloadHold\(pendingShips\.size\);/);
  // the user dismisses a pending chip
  assert.match(RENDER, /if \(!list\.length && id\) pendingShips\.delete\(id\);\n\s*publishReloadHold\(pendingShips\.size\);/);
  // the load-time publish follows the loss toast's block, so a ship the page lost never holds a reload owed at startup
  assert.match(RENDER, /shipsInFlight: \[\] \}\);\n\s*\}\n\s*\}\n\} catch \{ \/\* ignore \*\/ \}\n(\/\/.*\n)*publishReloadHold\(pendingShips\.size\);/);
  assert.equal((RENDER.match(/publishReloadHold\(/g) || []).length, 4, "four publishes: three changes and the load");
});

// The notices a reload wipes (the fourth fold's review, F2): the ack and nack toasts raised when the LAST pending ship
// retires die with the reload that follows within the core's re-check, so render.ts snapshots the toasts on screen into
// the persisted state on the pre-reload hook and shows them again once at load. The served scenario (a nack on the last
// ship across a restart; the fresh page shows the notice, once) is tests/test_ship_reship.py NackNoticeSurvivesReload.
test("the toasts on screen read as their texts, in order, blanks dropped; none without the container", () => {
  const box = (texts: (string | null)[]) => ({ querySelectorAll: (sel: string) => { assert.equal(sel, ".warn-toast-msg"); return texts.map((t) => ({ textContent: t })); } });
  assert.deepEqual(liveNotices(null), [], "the container is created by the first toast; none yet");
  assert.deepEqual(liveNotices(undefined), []);
  assert.deepEqual(liveNotices(box([])), []);
  assert.deepEqual(liveNotices(box(["shot.png was not saved on the kernel. Your message was NOT sent.", "  ", null, "the held message was not sent"])),
    ["shot.png was not saved on the kernel. Your message was NOT sent.", "the held message was not sent"]);
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
  assert.match(RENDER, /import \{ publishReloadHold, liveNotices, takePendingNotices \} from "\.\/reload-hold";/);
  assert.match(RENDER, /^function persistNoticesForReload\(\): void \{\n\s*try \{ if \(vscodeApi\?\.setState\) vscodeApi\.setState\(\{ \.\.\.\(vscodeApi\.getState\(\) \|\| \{\}\), pendingNotices: liveNotices\(document\.getElementById\("warn-toasts"\)\) \}\); \} catch \{ \/\* ignore \*\/ \}\n\}/m,
    "the texts of the live toasts, into the same state the drafts and shipsInFlight ride");
  // the core's hook writes both records; pagehide writes the scroll record alone (reload-restore.test.ts pins those two lines
  // too), so a reload the user asks for does not replay a toast they were already looking at: ReloadLossToast's one warning
  assert.match(RENDER, /function persistForReload\(\): void \{ persistScrollForReload\(\); persistNoticesForReload\(\); \}[^\n]*\n\(window as any\)\.__rompPersistForReload = persistForReload;\nwindow\.addEventListener\("pagehide", persistScrollForReload\);/);
  assert.equal((RENDER.match(/persistNoticesForReload\(\)/g) || []).length, 2, "defined once, called from the core's hook alone");
  const scroll = RENDER.match(/^function persistScrollForReload\(\): void \{([\s\S]*?)\n\}/m);
  assert.ok(scroll && !scroll[1].includes("persistNoticesForReload"), "upstream's scroll record is untouched");
  assert.equal((RENDER.match(/pendingNotices:/g) || []).length, 1, "written in one place; the reading goes through takePendingNotices");
  // the replay follows the load-time publish, which follows the loss toast's block: the loss first, then what the last
  // page was saying; the record is cleared in the same block, before the toasts are raised (one reload, one replay)
  assert.match(RENDER, /publishReloadHold\(pendingShips\.size\);\n(\/\/.*\n)*try \{\n\s*const taken = takePendingNotices\(vscodeApi\?\.getState\?\.\(\)\);\n\s*if \(taken\.notices\.length\) \{\n\s*vscodeApi\?\.setState\?\.\(taken\.rest\);\n\s*for \(const text of taken\.notices\) warnToast\(text\);\n\s*\}\n\} catch \{ \/\* ignore \*\/ \}/);
  assert.equal((RENDER.match(/takePendingNotices\(/g) || []).length, 1, "consumed once, at load");
});

test("the reload core reads the word as its 'ships' hold, after the gesture holds, and defers instead of reloading", () => {
  const core = KERNEL.slice(KERNEL.indexOf("/*reload-core*/"), KERNEL.indexOf("/*end-reload-core*/"));
  assert.ok(core.length > 0, "the core's anchors exist");
  assert.match(core, /return 'composer';\}catch\(e\)\{\}\ntry\{if\(window\.__rompReloadHold===true\)return 'ships';\}catch\(e\)\{\}/);
  assert.match(core, /if\(b==='ships'\)b=shipsHold\(\);/, "tryFire defers on the hold instead of reloading now");
  assert.match(core, /HOLD_MAX=60000/, "the bounded wait");
});
