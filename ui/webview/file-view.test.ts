// The file viewer — a modal over the CHAT pane (the user 2026-08-15; the first cut filled the FEED
// pane, and reading a file cost the cards). Clicking a file path in the chat used to post `openFile`,
// which the kernel served by running an opener on ITS OWN machine — the wrong screen when the
// dashboard is read from another device, and nothing at all on a kernel with no desktop, because the
// opener was macOS-only (the user 2026-08-08). The bytes have to reach the browser, so the click routes
// to a viewer fed by the same /file route the image previews use — now in the SAME document as the
// click, so the chat needs no shell relay. The FEED still hosts the viewer too: the file BROWSER
// (file-browse.ts) opens files through the same module in its own document, which is why the feed
// sheet mirrors the viewer CSS instead of dropping it. Source pins (no jsdom for these modules) +
// executed replicas of the pure helpers.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const VIEW = web("file-view.ts");
const RENDER = web("render.ts");
const FEED = web("feed.ts");
const FEED_CSS = web("feed.css");
const CHAT_CSS = web("styles.css");

test("openPath routes by HOST: the in-pane viewer modal on the web, the editor in VS Code", () => {
  assert.match(RENDER, /function openPath\(path: string, sid\?: string \| null\): void/);
  // web default → the viewer opens in THIS document; the cards-pane preference relays instead (below)
  assert.match(RENDER, /openFileView\(path, sid \|\| activeId \|\| null\);/);
  // (setCommentSink left the import with the review layer, 2026-08-23 — quote chips replaced it.
  // Upstream also asserts the viewFile relay is GONE from render.ts; here it is alive on purpose —
  // the fork's fileLinkPane preference sends it since 2026-08-20, pinned by fileLinkRoute below.)
  assert.match(RENDER, /import \{ openFileView \} from "\.\/file-view";/);
  // VS Code keeps the host editor
  assert.match(RENDER, /vscodeApi\.postMessage\(sid \? \{ type: "openFile", path, id: sid \} : \{ type: "openFile", path \}\);/);
});

// executed: openPath's web-side branch (the user 2026-08-20). The DEFAULT is upstream's design — the
// viewer opens over the pane that was clicked; the fileLinkPane preference ("feed"/"pane", gear.js)
// relays the open to the shell so the viewer opens in the FEED pane (the transcript stays readable
// while the file is up) or the FILES pane (its own column). The GATE lives here at the click site,
// not in the shell: the shell forwards whatever arrives (browseFiles' contract), so a message that is
// never sent is a click that opens in place — no message can be silently swallowed by a shell-side
// setting check. Since 2026-09-04 an OPEN Files pane takes the click whatever the setting says (the
// user: the pane being open IS the intent; a click that opened as a modal over the chat while the
// pane sat empty was the bug) — the setting decides only where a link goes while the pane is closed.
test("fileLinkRoute: an open Files pane takes the click; otherwise the preference relays only when framed", () => {
  const fileLinkRoute = (pane: unknown, framed: boolean, filesOpen: boolean): "feed" | "pane" | "here" => {
    if (!framed) return "here";
    if (filesOpen) return "pane";
    return pane === "feed" || pane === "pane" ? pane : "here";
  };
  // the Files pane is OPEN: every setting value routes there (the 2026-09-04 rule)
  for (const setting of ["chat", "feed", "pane", undefined, "purple"]) {
    assert.equal(fileLinkRoute(setting, true, true), "pane", `Files pane open & framed, setting=${String(setting)} → the Files pane, whatever the setting`);
  }
  // the Files pane is CLOSED: the setting's own table, exactly as before
  assert.equal(fileLinkRoute("feed", true, false), "feed", "setting=feed & framed → hand the open to the shell, for the feed");
  assert.equal(fileLinkRoute("pane", true, false), "pane", "setting=pane & framed → the shell, for the Files pane (2026-09-03) — which brings the closed pane forward");
  assert.equal(fileLinkRoute("chat", true, false), "here", "the default: exactly the pre-setting behavior");
  assert.equal(fileLinkRoute(undefined, true, false), "here", "an unset store reads as the default");
  assert.equal(fileLinkRoute("purple", true, false), "here", "a foreign stored value falls to the default");
  // UNFRAMED (standalone /chat): no shell, no other pane — "here" regardless of setting or pane bit
  for (const setting of ["chat", "feed", "pane", undefined]) {
    for (const open of [true, false]) {
      assert.equal(fileLinkRoute(setting, false, open), "here", `standalone /chat, setting=${String(setting)}, filesOpen=${open} → open in place`);
    }
  }
  // replica ↔ source: the pure function's exact body, so the executed table above is the shipped logic
  assert.match(RENDER, /function fileLinkRoute\(pane: unknown, framed: boolean, filesOpen: boolean\): "feed" \| "pane" \| "here" \{\n\s*if \(!framed\) return "here";\n\s*if \(filesOpen\) return "pane";\n\s*return pane === "feed" \|\| pane === "pane" \? pane : "here";\n\}/);
  // the wiring: openPath consults it with the LIVE framed bit AND the shell's Files-pane bit, and posts up,
  // the message naming its target pane and carrying the session's identity for the Files pane's chip
  assert.match(RENDER, /const route = fileLinkRoute\(settings\.fileLinkPane, window\.parent !== window, panesOn\.files === true\);\n\s*if \(route !== "here"\) \{/);
  assert.match(RENDER, /const to = sid \|\| activeId \|\| null;\n\s*const s = to \? \(sessions\.get\(to\) \?\? tabMeta\.get\(to\)\) : undefined;\n\s*window\.parent\.postMessage\(\{ romp: "viewFile", path, sid: to, pane: route,\n\s*identity: s && s\.name \? \{ name: s\.name, color: s\.color \?\? null \} : null \}, "\*"\);/);
});

// The Files-pane bit openPath routes by is the SHELL's pane set, cached from the shell's own broadcast —
// {romp:"panes", on:{key:bool}} on every toggle (the shell's apply()) and on this iframe's load (kernel.py
// _LANDING_COLLAPSE_JS; pinned in tests/test_pane_state_broadcast.py) — never a per-click read of the
// parent's DOM or a poll. Whole-set replace, so a key the shell stops naming cannot linger as on.
test("the chat caches the shell's pane set from its romp:panes broadcast, and openPath reads the Files bit from it", () => {
  assert.match(RENDER, /let panesOn: Record<string, boolean> = \{\};/);
  assert.match(RENDER, /if \(m\.romp === "panes"\) \{\n\s*if \(m\.on && typeof m\.on === "object"\) \{\n\s*const on: Record<string, boolean> = \{\};\n\s*for \(const k of Object\.keys\(m\.on\)\) on\[k\] = m\.on\[k\] === true;\n\s*panesOn = on;\n\s*\}\n\s*return;\n\s*\}/);
  assert.match(RENDER, /fileLinkRoute\(settings\.fileLinkPane, window\.parent !== window, panesOn\.files === true\)/);
  assert.equal((RENDER.match(/panesOn\.files/g) || []).length, 1, "one reader: openPath's route decision");
  // executed: the listener's fold, as the source spells it — strict booleans in, unknown keys dropped on the next set
  const fold = (on: Record<string, unknown>): Record<string, boolean> => {
    const out: Record<string, boolean> = {};
    for (const k of Object.keys(on)) out[k] = on[k] === true;
    return out;
  };
  assert.deepEqual(fold({ chat: true, feed: false, files: true }), { chat: true, feed: false, files: true });
  assert.deepEqual(fold({ files: "yes" }), { files: false }, "only a real true counts as on");
  assert.equal(fold({ chat: true }).files, undefined, "a set that stops naming a pane leaves it off (=== true fails)");
});

test("every file-link surface in the chat goes through openPath — no direct openFile posts left", () => {
  for (const call of [/openPath\(path\);/, /openPath\(open, relative \? \(sid \?\? activeId\) : null\);/,
                      /openPath\(p, id \|\| null\);/]) assert.match(RENDER, call);
  // the ONLY openFile postMessage left in render.ts is openPath's own fallback branch
  assert.equal((RENDER.match(/type: "openFile"/g) || []).length, 2,
               "both remaining mentions are the two arms of openPath's fallback");
});

test("the shell relays viewFile again — the click site gates it; the pane juggling mirrors browseFiles", () => {
  const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");
  // 2026-08-15 removed this relay ("a file view must never touch the feed"); 2026-08-20 brings it
  // back OPT-IN: openPath posts viewFile up only when the fileLinkPane preference says feed (the
  // gate is chat-side — see the fileLinkRoute test), and the shell forwards unconditionally, the
  // browseFiles contract, into the feed iframe where initFileView's viewFile branch opens the viewer
  assert.match(KERNEL, /if\(m\.romp==='viewFile'\)\{var vf=document\.getElementById\('f-feed'\);/);
  assert.match(KERNEL, /postMessage\(\{romp:'viewFile',path:m\.path,sid:m\.sid\},'\*'\)/);
  // ARM ON ACK (review 2026-08-20): postMessage up the relay is fire-and-forget, so the shell only
  // STASHES the was-off bit at relay time and COMMITS the restore flag when the feed acks the real
  // open — a viewFile lost to a mid-reload feed iframe leaves no armed flag behind for a later
  // open/close cycle to consume (which hid a pane the user was using: a surprise on no new
  // information). The flag stays SEPARATE from the browser's, so the two overlays' independent
  // closes each restore only their own bring-forward (the one deliberate coupling is the browser
  // handoff — the transfer test below).
  const vrelay = KERNEL.split("if(m.romp==='viewFile')")[1].split("if(m.romp==='viewFileOpened')")[0];
  assert.ok(vrelay.includes("window.__rompFeedWasOffViewPend=!document.body.classList.contains('po-feed');"),
    "stashed at relay time, on the pending var — not the flag");
  assert.ok(!vrelay.includes("window.__rompFeedWasOffView=true"), "no commit before the feed answers");
  assert.ok(vrelay.includes("window.__rompMobileTab&&window.__rompMobileTab('feed')"), "phone: one pane at a time");
  const ack = KERNEL.split("if(m.romp==='viewFileOpened')")[1].split("if(m.romp==='viewFileClosed')")[0];
  assert.ok(ack.includes("if(window.__rompFeedWasOffViewPend)window.__rompFeedWasOffView=true;"),
    "the ack alone commits the restore obligation");
  assert.ok(ack.includes("window.__rompFeedWasOffViewPend=false;"), "…and the stash never outlives it");
  assert.match(KERNEL, /if\(m\.romp==='viewFileClosed'\)\{/);
  assert.match(KERNEL, /if\(window\.__rompFeedWasOffView\)\{window\.__rompFeedWasOffView=false;/);
  // the feed-side viewer knows it was relay-opened and announces ONLY that close to the shell —
  // an in-document open (the file browser's, or a chat-hosted viewer) still announces nothing
  assert.match(VIEW, /viaRelay = true;/);
  assert.match(VIEW, /if \(viaRelay\) \{/);
  assert.match(VIEW, /window\.parent\.postMessage\(\{ romp: "viewFileClosed" \}, "\*"\);/);
  // the file BROWSER's relay (plans/file-browser.md) keeps its own door: its own was-off
  // flag, its own browseClosed restore
  assert.match(KERNEL, /if\(m\.romp==='browseFiles'\)\{var bf=document\.getElementById\('f-feed'\);/);
  assert.match(KERNEL, /window\.__rompFeedWasOff=true;/);
  assert.match(KERNEL, /m\.romp==='browseClosed'/);
  assert.match(KERNEL, /window\.__rompMobileTab&&window\.__rompMobileTab\('feed'\)/, "phone: one pane at a time");
});

test("a relayed viewFile OPENS the viewer in the feed document, session id intact — and acks only a REAL open", () => {
  // the receiving end of the relay: the feed boots initFileView (pinned below with the WS poster),
  // whose viewFile branch opens the viewer — so raw edits and the GitHub link ride the feed's own
  // poster exactly like a browser-opened file, and the review layer stays dark there (no sink)
  assert.match(VIEW, /if \(m\.romp === "viewFile" && typeof m\.path === "string" && m\.path\) \{/);
  // VETO PURITY (review 2026-08-20): openFileView can DECLINE — the dirty-edit guard keeps the
  // previous viewer — and that survivor keeps its own provenance: a vetoed relay must not re-tag an
  // in-document viewer as relay-opened (a false viewFileClosed on its close) nor ack an open that
  // never happened (a false armed flag shell-side). So openFileView reports, and the branch gates
  // BOTH viaRelay and the viewFileOpened ack on a real open.
  assert.match(VIEW, /export function openFileView\(path: string, sid\?: string \| null, opts\?: \{ todoId\?: string \| null \}\): boolean \{/);
  const openFn = VIEW.split("export function openFileView")[1].split("function offersDownload")[0];
  assert.match(openFn, /&& closeGuard && !closeGuard\(\)\) return false;/, "the veto is a reported verdict");
  assert.match(openFn, /\n  return true;\n\}/, "a completed open says so");
  assert.match(VIEW, /if \(openFileView\(m\.path, typeof m\.sid === "string" \? m\.sid : null\)\) \{/);
  const relayBranch = VIEW.split('if (m.romp === "viewFile"')[1].split("} else if")[0];
  assert.ok(relayBranch.includes("viaRelay = true;"), "tagged only inside the real-open branch");
  assert.ok(relayBranch.includes('window.parent.postMessage({ romp: "viewFileOpened" }, "*");'),
    "the arm-on-ack ack, sent only inside the real-open branch");
});

test("browser handoff: a relay viewer closed FOR the browser stays silent — the browser owns the pane", () => {
  const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");
  // "Browse" (the viewer's dir-link, the chat's Browse button) closes a viewer that is up to surface
  // the listing — and when that viewer was RELAY-opened, its announce would hand the shell a
  // viewFileClosed at the exact moment the browser opens inside the pane, hiding the browser the
  // click asked for. The ownership-aware suppress (the pre-2026-08-15 idiom, keyed on the browser's
  // element, which openFileBrowse builds BEFORE closing us) keeps that close silent; the shell moves
  // the restore obligation onto the browser's own flag, so browseClosed still puts the pane back.
  const closeFn = VIEW.split("export function closeFileView")[1].split("/** Show `path`")[0];
  assert.match(closeFn, /if \(document\.getElementById\("romp-filebrowse"\)\) return;/);
  assert.ok(closeFn.indexOf('"romp-filebrowse"') < closeFn.indexOf('"viewFileClosed"'),
    "the suppress sits before the announce, inside the viaRelay branch");
  assert.ok(closeFn.indexOf("viaRelay = false;") < closeFn.indexOf('"romp-filebrowse"'),
    "the tag clears even on a silent close — the survivor of a handoff is the BROWSER's, not the relay's");
  // shell side, both handoff routes: browseFiles-through-the-shell TRANSFERS the COMMITTED viewer
  // flag onto the browser's and RETIRES a still-pending stash (never converts it — no ack may ever
  // come for a lost/vetoed viewFile, and converting the stale bit hid the pane at a much-later
  // browse close); the feed-document route (the viewer's own dir-link) never sends browseFiles
  // through the shell at all, so browseClosed consumes EITHER flag — the overlay chain's end
  // discharges whatever bring-forward the chain still owes, exactly once
  assert.match(KERNEL, /if\(window\.__rompFeedWasOffView\)\{window\.__rompFeedWasOff=true;window\.__rompFeedWasOffView=false;\}/);
  assert.match(KERNEL, /window\.__rompFeedWasOffViewPend=false;\n  if\(!document\.body\.classList\.contains\('po-feed'\)\)/,
    "the pend retires at the transfer, unconditionally — before the browser's own arming");
  assert.match(KERNEL, /if\(m\.romp==='browseClosed'&&\(window\.__rompFeedWasOff\|\|window\.__rompFeedWasOffView\)\)\{/);
});

test("mobile: closing a relay-opened viewer returns the phone to the Chat tab", () => {
  const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");
  // the open half switches a phone to the Feed tab (one pane at a time); without the return trip the
  // close stranded the user there (review 2026-08-20). The relay only ever fires from a chat click,
  // so viewFileClosed goes back to Chat — unconditionally, not gated on the was-off flag, because
  // the tab switch happened whatever the pane's desktop state was. The silent browser handoff posts
  // no viewFileClosed at all, so heading into the browser correctly STAYS on the Feed tab.
  const closed = KERNEL.split("if(m.romp==='viewFileClosed')")[1].split("// One id per dashboard")[0];
  assert.ok(closed.includes("window.__rompMobileTab&&window.__rompMobileTab('chat')"),
    "the symmetric return to the tab the click always comes from");
  assert.ok(closed.indexOf("__rompMobileTab") < closed.indexOf("__rompFeedWasOffView"),
    "the return is not gated on the desktop was-off flag");
});

// executed: the shell's flag algebra, end to end — the five arms EXTRACTED from kernel.py's landing
// shell at test time and run against a shimmed window/document, so the model under test IS the
// shipped source. (The first cut hand-copied the arms, which let kernel.py drift while the replica
// stayed green — review 2026-08-20; the anchor asserts below fail loudly if the arms move instead.)
test("shell flag algebra: both handoff routes restore once, a lost viewFile arms nothing", () => {
  const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");
  const start = KERNEL.indexOf("if(m.romp==='browseFiles')");
  const stop = KERNEL.indexOf("// One id per dashboard", start);
  assert.ok(start >= 0 && stop > start, "arm anchors not found — the landing shell moved; re-anchor this extraction");
  let arms = KERNEL.slice(start, stop).trimEnd();
  assert.ok(arms.endsWith("}});"), "the slice no longer ends at the message listener's close — re-anchor");
  arms = arms.slice(0, -3);   // drop the listener's own `});` — the arms are plain statements without it
  for (const a of ["browseFiles", "browseClosed", "viewFile", "viewFileOpened", "viewFileClosed"])
    assert.ok(arms.includes("if(m.romp==='" + a + "'"), "extraction lost the " + a + " arm");
  const armsFn = new Function("window", "document", "m", arms) as (w: unknown, d: unknown, m: unknown) => void;
  type S = { paneOn: boolean; pend: boolean; wasOffView: boolean; wasOff: boolean; mobile: string };
  const shell = (s: S, msg: string): S => {
    const n = { ...s };
    const win = {
      __rompFeedWasOff: s.wasOff, __rompFeedWasOffView: s.wasOffView, __rompFeedWasOffViewPend: s.pend,
      __rompPaneToggle: (pane: string, on: boolean) => { if (pane === "feed") n.paneOn = on; },
      __rompMobileTab: (tab: string) => { n.mobile = tab; },
    };
    const doc = {   // the pane bit lives on body.po-feed; no feed iframe, so the forwards no-op
      body: { classList: { contains: (c: string) => c === "po-feed" && n.paneOn } },
      getElementById: () => null,
    };
    armsFn(win, doc, { romp: msg });
    return { ...n, wasOff: !!win.__rompFeedWasOff, wasOffView: !!win.__rompFeedWasOffView,
             pend: !!win.__rompFeedWasOffViewPend };
  };
  const run = (msgs: string[]) => msgs.reduce(shell,
    { paneOn: false, pend: false, wasOffView: false, wasOff: false, mobile: "chat" });
  // the plain relay round-trip: arm on ack, restore on close, phone back on Chat
  assert.deepEqual(run(["viewFile", "viewFileOpened", "viewFileClosed"]),
    { paneOn: false, pend: false, wasOffView: false, wasOff: false, mobile: "chat" });
  // handoff THROUGH the shell (the chat's Browse button): the committed obligation transfers to the
  // browser's flag the moment browseFiles arrives — no stale viewer flag can linger under an open
  // browser — and browseClosed restores the pane to its original (off) state
  assert.deepEqual(run(["viewFile", "viewFileOpened", "browseFiles", "browseClosed"]),
    { paneOn: false, pend: false, wasOffView: false, wasOff: false, mobile: "feed" });
  // handoff INSIDE the feed document (the viewer's dir-link): no browseFiles ever reaches the shell,
  // so the browseClosed union is what discharges the viewer's bring-forward — once, nothing lingers
  assert.deepEqual(run(["viewFile", "viewFileOpened", "browseClosed"]),
    { paneOn: false, pend: false, wasOffView: false, wasOff: false, mobile: "feed" });
  // a LOST viewFile (mid-reload iframe): no ack → nothing armed; the pane parks forward (acceptable)
  const lost = run(["viewFile"]);
  assert.equal(lost.paneOn, true);
  assert.equal(lost.wasOffView, false, "no ack, no armed flag");
  // …a LATER open/close cycle over the now-on pane hides nothing — the stale-flag surprise the
  // arm-on-ack fix removed (the pre-fix shell armed at send time, and this exact sequence hid the pane)
  assert.equal(run(["viewFile", "viewFile", "viewFileOpened", "viewFileClosed"]).paneOn, true);
  // …and a LATER browse open/close cycle hides nothing either: the transfer converts only the
  // COMMITTED flag and RETIRES the stale pend (review 2026-08-20 — converting the pend let a
  // viewFile lost long before turn the next browse close into a pane-hide under active use)
  assert.deepEqual(run(["viewFile", "browseFiles", "browseClosed"]),
    { paneOn: true, pend: false, wasOffView: false, wasOff: false, mobile: "feed" });
  assert.equal(run(["viewFile", "browseFiles"]).pend, false,
    "the transfer retires the stash — nothing is left cocked for any later cycle");
  // an ack landing AFTER the browser took over arms nothing: the genuinely in-flight open loses only
  // its restore (the pane parks forward, arm-on-ack's one named price), never gains a surprise hide
  assert.deepEqual(run(["viewFile", "browseFiles", "viewFileOpened", "browseClosed"]),
    { paneOn: true, pend: false, wasOffView: false, wasOff: false, mobile: "feed" });
  // a VETOED open is a delivered message with no ack — same algebra as the lost one
  assert.equal(run(["viewFile"]).wasOffView, false);
});

test("the viewer is a singleton MODAL over its pane: ~95% card, dimmed backdrop, ✕/Esc/backdrop close", () => {
  assert.match(VIEW, /document\.getElementById\("romp-fileview"\)\?\.remove\(\);/, "re-opening replaces, never stacks");
  // the backdrop closes on ITS OWN clicks only — content clicks don't (the lightbox contract)
  assert.match(VIEW, /wrap\.onclick = \(ev\) => \{ if \(ev\.target === wrap\) closeFileView\(\); \};/);
  assert.match(VIEW, /close\.addEventListener\("click", closeFileView\);/);
  assert.match(VIEW, /if \(e\.key !== "Escape" \|\| !document\.getElementById\("romp-fileview"\)\) return;/);
  // the panels treatment on the CHAT sheet: dimmed rgba(0,0,0,0.55) backdrop, the content behind visible
  assert.match(CHAT_CSS, /#romp-fileview \{ position: fixed; inset: 0; z-index: 1200; background: var\(--overlay-dim\);/);
  assert.match(CHAT_CSS, /\.fileview \{ width: 95%; height: 95%;/);
  // …and mirrored on the FEED sheet, which still hosts the viewer when the file BROWSER opens a file
  // (one treatment, two sheets — the hljs-palette precedent below)
  assert.match(FEED_CSS, /#romp-fileview \{ position: fixed; inset: 0;/);
  assert.match(FEED_CSS, /\.fileview \{ width: 95%; height: 95%;/);
  assert.match(FEED, /initFileView\(\(m\) => vscodeApi\?\.postMessage\(m\)\);/,
    "the feed boots the listener with the WS poster (saves ride it — the raw-mode slice)");
});

// ── selection → quote chip (the user 2026-08-23, the three-verbs consolidation): the viewer's
// separate review layer (per-file comment store, marks, one-shot Submit — romp:fileviewComments +
// buildReviewMessage) is GONE. Selecting a passage now seeds the chat composer's own labeled quote
// chip, exactly like a VS Code editor highlight, and batching rides the chip + ⌘⏎ staging flow the
// chat already has. "Comment" means only the transcript's live threads now. ──

test("selecting in the viewer seeds the composer's editor chip — the editorSelection shape, path:line label", () => {
  // mouseup posts to our OWN window (the browseFiles precedent — no import cycle with render.ts),
  // and render.ts's existing editorSelection handler owns the chip end to end
  assert.match(VIEW, /box\.addEventListener\("mouseup", \(\) => \{/);
  assert.match(VIEW, /seedTarget\.postMessage\(\{ type: "editorSelection", text: picked, sid: sid \|\| undefined, src: quoteSrcLabel\(path, doc, picked\) \}, "\*"\);/);
  // a collapsed or out-of-viewer selection seeds nothing, and CodeMirror selections are edits
  assert.match(VIEW, /if \(!sel \|\| sel\.isCollapsed \|\| !sel\.anchorNode \|\| !box\.contains\(sel\.anchorNode\)\) return;/);
  assert.match(VIEW, /if \(editing\) return;/);
});

test("the chip lands in the session the file was opened FOR — the posted sid beats activeId-at-gesture", () => {
  // the modal stays up across a tab switch (nothing closes it on focus), so seeding into activeId
  // would put session A's path:line quote into session B's composer — the 2026-08-19 routing rule
  // the retired review layer already learned once. Host (VS Code) posts carry no sid → activeId.
  assert.match(RENDER, /const to = typeof m\.sid === "string" && m\.sid \? m\.sid : activeId;/);
  assert.match(RENDER, /if \(to\) seedEditorQuote\(to, m\.text, typeof m\.src === "string" \? m\.src : undefined\);/);
});

test("the label's line is minted against a FRESH read, and a failed re-read falls back to the snapshot", () => {
  // agents edit these same trees while you read: the open-time snapshot's numbering may have moved,
  // so the line is anchored at selection time — and a failed re-read must not fabricate drift
  // nobody observed (the retired Submit guard's rule), so it anchors the snapshot instead. The
  // snapshot is viewText, not text: the SVG Source view's snapshot is the decoded blob and `text`
  // stays null in media mode, so falling back to it would strip every SVG quote's line label.
  assert.match(VIEW, /const seq = \+\+seedSeq;/);
  assert.match(VIEW, /fetch\(fileUrl\(path, sid\), \{ cache: "no-store" \}\)\n\s*\.then\(\(r\) => \(r\.ok \? r\.text\(\) : Promise\.reject\(new Error\(String\(r\.status\)\)\)\)\)\n\s*\.catch\(\(\) => viewText\(\)\)/);
  assert.match(VIEW, /const viewText = \(\): string \| null => \(svgSource && svgText !== null \? svgText : text\);/);
  assert.match(VIEW, /if \(seq !== seedSeq\) return;/, "two racing reads: the last gesture wins");
});

test("a viewer whose document has no composer seeds THROUGH the shell: the Files pane and the feed reach the chat's chip", () => {
  // Until 2026-09-03 the seed gated on a composer in the SAME document, so the feed-hosted viewer (the
  // file browser's document) was dead air by design. The Files pane hosts the viewer without a composer
  // too, and a pane that cannot quote is a step down from the chat modal — so the TARGET is resolved:
  // this window when it holds the composer, else the same-origin shell, which forwards the unchanged
  // message into the chat pane. No composer and no shell (VS Code's cross-origin parent, a standalone
  // pane) still stands the gesture down before the fresh read (the no-sink gating).
  assert.match(VIEW, /function composerWindow\(\): Window \| null \{\n\s*if \(document\.getElementById\("composer-input"\)\) return window;\n\s*try \{ if \(window\.parent !== window && window\.parent\.document\.getElementById\("chat-pane"\)\) return window\.parent; \}\n\s*catch \{[^}]*\}\n\s*return null;\n\}/);
  assert.match(VIEW, /const seedTarget = composerWindow\(\);\n\s*if \(!seedTarget\) return;/);
  // the shell's arm: the SAME message, forwarded whole into the chat frame — sid intact, so the chip
  // lands in the session the file was opened for (the 2026-08-19 routing rule holds across documents)
  const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");
  assert.match(KERNEL, /if\(m\.type==='editorSelection'&&typeof m\.text==='string'\)\{var fc=document\.getElementById\('f-chat'\);\n\s*try\{fc&&fc\.contentWindow&&fc\.contentWindow\.postMessage\(m,'\*'\);\}catch\(e\)\{\}\}/);
  // …and the chat's existing window-message handler is the receiver: nothing new listens in feed.ts
  assert.match(RENDER, /else if \(m\.type === "editorSelection" && typeof m\.text === "string" && m\.text\.trim\(\)\) \{/);
  assert.doesNotMatch(FEED, /editorSelection/);
  // the review layer is gone from every module and both sheets, and the orphaned store is swept
  for (const source of [VIEW, RENDER, FEED, CHAT_CSS, FEED_CSS]) {
    assert.doesNotMatch(source, /setCommentSink|buildReviewMessage|fv-hl|fileview-submit/);
  }
  assert.match(VIEW, /localStorage\.removeItem\("romp:fileviewComments"\)/);
});

// executed: composerWindow's ladder, lifted from the source (a hand copy would drift), run against
// shimmed window/document pairs for each hosting situation
test("composerWindow, executed: own composer → the same-origin shell's chat pane → nothing", () => {
  const m = VIEW.match(/function composerWindow\(\): Window \| null \{[\s\S]*?\n\}/);
  assert.ok(m, "composerWindow found");
  const body = m![0].replace(/^function composerWindow\(\): Window \| null /, "");
  const run = new Function("window", "document", "return (function()" + body + ")();") as (w: unknown, d: unknown) => unknown;
  const doc = (ids: string[]) => ({ getElementById: (id: string) => (ids.includes(id) ? {} : null) });
  const self: any = {}; self.parent = self;
  assert.equal(run(self, doc(["composer-input"])), self, "the chat document: its own window");
  const shell = { document: doc(["chat-pane"]) };
  const framed = { parent: shell };
  assert.equal(run(framed, doc([])), shell, "a pane inside the shell: the shell, which forwards into the chat");
  assert.equal(run(framed, doc(["composer-input"])), framed, "a composer at hand always wins over the relay");
  assert.equal(run({ parent: { get document() { throw new Error("cross-origin"); } } }, doc([])), null,
    "VS Code's cross-origin parent is not the shell — the gesture stands down");
  assert.equal(run({ parent: { document: doc([]) } }, doc([])), null, "a same-origin parent that is not the shell");
  assert.equal(run(self, doc([])), null, "unframed and composer-less: nowhere to seed");
});

test("it waits with the romp loader and fails with the kernel's own words, never a blank pane", () => {
  assert.match(VIEW, /romp-swirl-glyph\.svg/, "loading-state rule: the swirl goes up first");
  assert.match(VIEW, /fileview-dot/);
  // a 404/413/415 body IS the explanation (the 413 names the size and the cap) — show it, don't swallow
  // it. The status rides along since 2026-08-09, so the catch can decide whether to offer the download.
  assert.match(VIEW, /if \(!r\.ok\) return r\.text\(\)\.then\(\(t\) => \{\s*\n\s*throw Object\.assign\(new Error\(t \|\| \("HTTP " \+ r\.status\)\), \{ status: r\.status \}\);\s*\n\s*\}\);/);
  assert.match(VIEW, /const why = el\("div", "fileview-err"\);/);
  // a reply that lands after the user closed the viewer paints nothing
  assert.match(VIEW, /if \(!document\.getElementById\("romp-fileview"\)\) return;/);
});

test("it reuses fileUrl, so a REMOTE session's file is relayed from the host that owns it", () => {
  assert.match(VIEW, /import \{ fileUrl \} from "\.\/preview";/);
  assert.match(VIEW, /fetch\(fileUrl\(path, sid\), \{ cache: "no-store" \}\)/);
});

// executed: the extension→language map must never GUESS. highlightAuto on a config file or a log picks a
// language at random and paints it as information the file does not contain.
test("langFor maps known extensions and returns null rather than guessing", () => {
  const LANG: Record<string, string> = {
    py: "python", pyi: "python", js: "javascript", jsx: "javascript", mjs: "javascript",
    cjs: "javascript", ts: "typescript", tsx: "typescript", json: "json", jsonc: "json",
    yaml: "yaml", yml: "yaml", sh: "bash", bash: "bash", zsh: "bash", bats: "bash",
    html: "xml", htm: "xml", xml: "xml", svg: "xml", vue: "xml", css: "css", scss: "css",
    md: "markdown", markdown: "markdown", diff: "diff", patch: "diff",
  };
  const langFor = (p: string): string | null => LANG[p.slice(p.lastIndexOf(".") + 1).toLowerCase()] || null;
  assert.equal(langFor("kernel/kernel.py"), "python");
  assert.equal(langFor("ui/webview/render.TS"), "typescript");   // case-insensitive
  assert.equal(langFor("notes.md"), "markdown");
  for (const p of ["server.log", "Makefile", "a.conf", "data.csv", "x.rs"]) {
    assert.equal(langFor(p), null, p + " has no registered grammar → plain, not a guess");
  }
  assert.doesNotMatch(VIEW, /hljs\.highlightAuto\(/, "auto-detection is what this map exists to avoid");
});

// ── formatting (the user 2026-08-09): the hljs palette, Raw ⇄ Rendered for markdown, and word wrap ──

// A. The viewer wraps every token in .hljs-* spans, and it renders in BOTH documents — the chat (file
// links) and the feed (the file browser) — so both sheets must carry the SAME palette (one treatment,
// two sheets — the .romp-acted precedent). This pins every rule in both and catches drift.
test("the hljs token palette lives in feed.css too, identical to the chat's", () => {
  const STYLES = CHAT_CSS;
  // tokenized 2026-09-02 (the light theme re-inks the same names; theme-parity.test.ts holds the
  // token set + its contrast in both themes) — the dark :root values are the exact hexes these
  // rules always carried: fg #d8c6a8, kw #c98a6a, str #9fb878, num #d4a36a, cmt #6f6a5f,
  // title #e1c08d, meta #9a8f7a, attr #cdaf7e
  const rules = [
    /\.hljs \{ color: var\(--hl-fg\); background: transparent; \}/,
    /\.hljs-keyword, \.hljs-built_in, \.hljs-literal, \.hljs-type \{ color: var\(--hl-kw\); \}/,
    /\.hljs-string, \.hljs-attr, \.hljs-regexp \{ color: var\(--hl-str\); \}/,
    /\.hljs-number \{ color: var\(--hl-num\); \}/,
    /\.hljs-comment, \.hljs-quote \{ color: var\(--hl-cmt\); font-style: italic; \}/,
    /\.hljs-title, \.hljs-title\.function_, \.hljs-section \{ color: var\(--hl-title\); \}/,
    /\.hljs-name, \.hljs-tag \{ color: var\(--hl-kw\); \}/,
    /\.hljs-params, \.hljs-variable, \.hljs-property \{ color: var\(--hl-fg\); \}/,
    /\.hljs-meta \{ color: var\(--hl-meta\); \}/,
    /\.hljs-attribute \{ color: var\(--hl-attr\); \}/,
    /\.hljs-addition \{ color: var\(--hl-str\); \}/,
    /\.hljs-deletion \{ color: var\(--err\); \}/,
    /--hl-fg: #d8c6a8; --hl-kw: #c98a6a; --hl-str: #9fb878; --hl-num: #d4a36a;/,
    /--hl-cmt: #6f6a5f; --hl-title: #e1c08d; --hl-meta: #9a8f7a; --hl-attr: #cdaf7e;/,
  ];
  for (const r of rules) {
    assert.match(FEED_CSS, r, "feed.css is missing a palette rule: " + r.source);
    assert.match(STYLES, r, "styles.css drifted from the shared palette: " + r.source);
  }
});

// B, executed: the persisted view-format prefs. RENDERED is the markdown default (the user's explicit
// call, 2026-08-09) and any malformed stored value reads as the defaults — a corrupt entry may cost the
// preference, never the viewer (feed-view-state's parseViewState contract).
test("format prefs: rendered is the markdown default, and a corrupt entry reads as the defaults", () => {
  // wrap is GONE from the format state (the user 2026-08-24) — a stored wrap key from the toggle
  // era parses away silently
  type Fmt = { md: "rendered" | "raw" };
  const parseFmt = (raw: string | null): Fmt => {
    const def: Fmt = { md: "rendered" };
    if (!raw) return def;
    try {
      const o = JSON.parse(raw) as { md?: unknown };
      if (!o || typeof o !== "object") return def;
      return { md: o.md === "raw" ? "raw" : "rendered" };
    } catch { return def; }
  };
  assert.deepEqual(parseFmt(null), { md: "rendered" }, "first open: rendered");
  assert.deepEqual(parseFmt('{"md":"raw","wrap":true}'), { md: "raw" }, "the toggle-era wrap key parses away");
  assert.deepEqual(parseFmt("not json"), { md: "rendered" });
  assert.deepEqual(parseFmt('{"md":"purple","wrap":"yes"}'), { md: "rendered" },
                   "foreign values fall to the defaults field by field");
  // replica ↔ source
  assert.match(VIEW, /const def: FileViewFmt = \{ md: "rendered" \};/);
  assert.match(VIEW, /return \{ md: o\.md === "raw" \? "raw" : "rendered" \};/);
  // …and the prefs persist in localStorage, the feed-view-state call: per-BROWSER view state that must
  // survive a kernel restart without a round-trip to the thing that just restarted
  assert.match(VIEW, /const FMT_KEY = "romp:fileviewFmt";/);
  assert.match(VIEW, /localStorage\.getItem\(FMT_KEY\)/);
  assert.match(VIEW, /localStorage\.setItem\(FMT_KEY, JSON\.stringify\(f\)\)/);
});

// B: the toggle itself — markdown only, and the rendered path is sanitized. These are arbitrary bytes
// off a disk and marked emits raw HTML verbatim, so DOMPurify sits between it and .innerHTML with the
// same profile the chat's md() uses (render.ts).
test("Raw ⇄ Rendered exists for markdown ONLY, and nothing reaches innerHTML unsanitized", () => {
  assert.match(VIEW, /const isMd = langFor\(path\) === "markdown";/);
  // the two buttons are built inside the isMd gate — a .py file shows no Rendered/Raw toggle
  assert.match(VIEW, /if \(isMd\) \{\s*\n\s*for \(const mode of \["rendered", "raw"\] as const\)/);
  assert.match(VIEW, /const rendered = isMd && fmt\.md === "rendered";/, "non-md never renders as prose");
  assert.match(VIEW, /import DOMPurify from "dompurify";/);
  // html + svg, in lockstep with the chat's md(): KaTeX draws stretchy glyphs as inline <svg>
  assert.match(VIEW, /box\.innerHTML = DOMPurify\.sanitize\(dirty, \{ USE_PROFILES: \{ html: true, svg: true \}, ADD_DATA_URI_TAGS: \["img"\] \}\);/);
  // a README's links open a NEW tab rather than navigating the hosting pane's document away
  assert.match(VIEW, /target = "_blank"/);
  assert.match(VIEW, /rel = "noopener"/);
  // fenced blocks highlight only a NAMED, registered language — same no-guessing rule as langFor
  assert.match(VIEW, /if \(!lang \|\| !hljs\.getLanguage\(lang\)\) return;/);
  // the prose typography exists on BOTH sheets (the chat's .md block is the reference aesthetic)
  assert.match(FEED_CSS, /\.fileview-md \{/);
  assert.match(FEED_CSS, /\.fileview-md pre code \{/);
  assert.match(CHAT_CSS, /\.fileview-md \{/);
  assert.match(CHAT_CSS, /\.fileview-md pre code \{/);
  // toggles acknowledge in the same synchronous tick: click → save → renderBody, which flips .on
  assert.match(VIEW, /b\.addEventListener\("click", \(\) => \{ fmt\.md = mode; saveFmt\(fmt\); renderBody\(\); \}\);/);
  assert.match(VIEW, /b\.classList\.toggle\("on", on\);/);
  assert.match(FEED_CSS, /\.fileview-btn\.on \{ color: var\(--accent\); border-color: var\(--accent\);/);
  assert.match(CHAT_CSS, /\.fileview-btn\.on \{ color: var\(--accent\); border-color: var\(--accent\);/);
});

// C, executed: wrap mode's numbering. A flat gutter misaligns the moment one logical line wraps onto
// several visual lines, so wrap mode restructures — each logical line is a .fv-cl row numbered by a CSS
// counter — instead of shipping a drifting column. hljs spans can cross newlines, so each row must
// re-open what the previous row left unclosed (render.ts's wrapCodeLines balance walk).
test("wrap mode: per-line rows, spans rebalanced across newlines, no phantom trailing row", () => {
  const wrapNumberedHtml = (html: string): string => {
    const lines = html.split("\n");
    if (lines.length && lines[lines.length - 1] === "") lines.pop();
    let open: string[] = [];
    return lines.map((ln) => {
      const prefix = open.join("");
      const re = /<span[^>]*>|<\/span>/g; let m; const stack = open.slice();
      while ((m = re.exec(ln))) { if (m[0] === "</span>") stack.pop(); else stack.push(m[0]); }
      const suffix = "</span>".repeat(Math.max(0, stack.length));
      open = stack;
      return `<span class="fv-cl"><span class="fv-ct">${prefix}${ln}${suffix}</span></span>`;
    }).join("");
  };
  // a string token spanning a newline: closed at the end of row 1, re-opened at the start of row 2
  const out = wrapNumberedHtml('<span class="hljs-string">"a\nb"</span>\nplain');
  const rows = out.split('<span class="fv-cl">').filter(Boolean);
  assert.equal(rows.length, 3, "three logical lines, three rows");
  for (const row of rows) {
    const opens = (row.match(/<span[^>]*>/g) || []).length;
    const closes = (row.match(/<\/span>/g) || []).length;
    // +1: the .fv-cl open itself was consumed as the split delimiter
    assert.equal(opens + 1, closes, "a row must close every span it opens: " + row);
  }
  assert.match(rows[0], /<span class="hljs-string">"a<\/span>/);
  assert.match(rows[1], /^<span class="fv-ct"><span class="hljs-string">b"<\/span>/);
  assert.equal((wrapNumberedHtml("a\n").match(/fv-cl/g) || []).length, 1,
               "a trailing newline is not a phantom row — same rule as the gutter");
  // replica ↔ source
  assert.match(VIEW, /return `<span class="fv-cl"><span class="fv-ct">\$\{prefix\}\$\{ln\}\$\{suffix\}<\/span><\/span>`;/);
});

// C: the toggle and the CSS that carries the honest gutter answer
test("long lines ALWAYS soft-wrap — the dedicated toggle button is gone (the user 2026-08-24)", () => {
  assert.doesNotMatch(VIEW, /wrapBtn/, "no wrap chrome anywhere in the modal");
  assert.match(VIEW, /codeBlock\(text, path, true\)/, "the pre view is born wrapped");
  // wrap mode returns BEFORE the sibling gutter is built — a misaligned column cannot exist
  assert.match(VIEW, /if \(wrapLines\) \{[\s\S]*?return wrap;\s*\}\s*const gutter = el\("div", "fileview-gutter"\);/);
  // plain files wrap too: no grammar → the text is HTML-escaped before the line walk
  assert.match(VIEW, /code\.innerHTML = wrapNumberedHtml\(hl !== null \? hl : escapeHtml\(text\)\);/);
  for (const SHEET of [FEED_CSS, CHAT_CSS]) {
    assert.match(SHEET, /\.fileview-pre\.fileview-wrap \{ white-space: pre-wrap/);
    assert.match(SHEET, /\.fileview-wrap \.fv-cl::before \{[\s\S]*?counter-increment: fvln/);
    assert.match(SHEET, /\.fileview-wrap \.fv-cl::before \{[\s\S]*?user-select: none/);
  }
});

test("a file opened FROM the listing offers the way back — close only the viewer, listing intact beneath", () => {
  // the one-directional stack: the browser sits beneath, so closing just the viewer IS the back;
  // presence-gated on the browser's DOM id (import-free), absent for path-link opens
  assert.match(VIEW, /if \(document\.getElementById\("romp-filebrowse"\)\) \{/);
  assert.match(VIEW, /back\.textContent = "‹ Files"; back\.title = "Back to the file listing";/);
  assert.match(VIEW, /back\.addEventListener\("click", \(\) => closeFileView\(\)\);/);
});

// ── download (the user 2026-08-09): any linked file can be SAVED, including everything the pane cannot
// show — the kernel's ?download=1 serves anything on disk (the rationale lives with _file_download in
// kernel.py: the view allowlists are a rendering choice, not a security boundary). ──

test("the title bar offers Download next to Copy path, at the same-origin download URL", () => {
  // the URL is fileUrl + the download switch: same origin, cookie-authed, and federation-aware for
  // free — fileUrl already routes a remote session's file through the /remote/<host>/file relay
  assert.match(VIEW, /const dlUrl = fileUrl\(path, sid\) \+ "&download=1";/);
  assert.match(VIEW, /dl\.textContent = "Download";/);
  // next to Copy path: appended into the same acts bar, wearing the same button class
  assert.match(VIEW, /acts\.appendChild\(dl\);\n\n  const copy = el\("button", "fileview-btn"\)/);
  assert.match(VIEW, /const dl = el\("button", "fileview-btn"\) as HTMLButtonElement;/, "no new styling, no new font size");
});

test("startDownload hands the URL to the browser's downloader and never wipes the pane", () => {
  // an <a download> click: the BROWSER owns the request (its progress UI, its save location), and the
  // kernel's attachment disposition means the page never navigates — the viewer stays put
  assert.match(VIEW, /const a = document\.createElement\("a"\);\s*\n\s*a\.href = url;\s*\n\s*a\.download = "";/);
  assert.match(VIEW, /document\.body\.appendChild\(a\);\s*\n\s*a\.click\(\);\s*\n\s*a\.remove\(\);/);
  assert.doesNotMatch(VIEW, /location\.href\s*=/, "no navigation — a wiped pane is the failure mode this avoids");
  // …and the click acknowledges itself (ui/CLAUDE.md): the download UI can take a beat over a tunnel
  assert.match(VIEW, /btn\.textContent = "Downloading…";/);
});

// executed: which fetch failures still deserve a Download offer? Exactly the ones that mean the file
// EXISTS — 413 (too large to render) and 415 (on disk but not viewable: a .zip, a binary named like
// text). A 404 is genuinely missing, and offering to download it would be a lie.
test("offersDownload: 413 and 415 offer, 404 and everything else do not", () => {
  const offersDownload = (status: number | undefined): boolean => status === 413 || status === 415;
  assert.equal(offersDownload(413), true, "too big to render ≠ too big to save");
  assert.equal(offersDownload(415), true, "exists-but-unviewable is the case the button exists for");
  assert.equal(offersDownload(404), false, "genuinely missing → nothing to offer");
  assert.equal(offersDownload(403), false);
  assert.equal(offersDownload(undefined), false, "a network failure carries no status and no offer");
  // replica ↔ source
  assert.match(VIEW, /return status === 413 \|\| status === 415;/);
});

test("a refusal renders the kernel's words PLUS the way out — gated on offersDownload", () => {
  // the status rides the thrown error so the catch can tell "there but unshowable" from "not there"
  assert.match(VIEW, /throw Object\.assign\(new Error\(t \|\| \("HTTP " \+ r\.status\)\), \{ status: r\.status \}\);/);
  // the offer appends to the SAME error pane that shows the kernel's message — an offer, not a dead end
  assert.match(VIEW, /if \(offersDownload\(\(err as \{ status\?: number \}\)\.status\)\) \{/);
  assert.match(VIEW, /const offer = el\("button", "fileview-btn fileview-err-dl"\) as HTMLButtonElement;/);
  assert.match(VIEW, /why\.appendChild\(offer\);/);
  assert.match(VIEW, /offer\.addEventListener\("click", \(\) => startDownload\(dlUrl, offer\)\);/);
  assert.match(FEED_CSS, /\.fileview-err-dl \{ display: block; margin-top: 10px; \}/);
  assert.match(CHAT_CSS, /\.fileview-err-dl \{ display: block; margin-top: 10px; \}/);
});

test("Edit is consent-gated, and the gate is the KERNEL's flag, not the button (the user 2026-08-22)", () => {
  // the click asks the kernel's live flag first — never a cached copy, another machine may have flipped it
  assert.match(VIEW, /fetch\(kernelUrl\("\/version"\), \{ cache: "no-store" \}\)/);
  assert.match(VIEW, /\.fileEditing;/);
  // no flag → a plain-words popup; only a YES posts the opt-in, and it broadcasts (KERNEL_SETTING)
  // — stamped with the gesture's own time, so a copy queued for a down host and flushed hours
  // later can never outrank a newer pick at the kernel (the store orders applies by gt)
  assert.match(VIEW, /window\.confirm\(\s*\n?\s*"Allow editing files from the dashboard\?/);
  assert.match(VIEW, /post\(\{ type: "setFileEditing", enabled: true, gt: Date\.now\(\) \}\);/);
  // the popup's promise of a gear off-switch is real, and the save route refuses server-side
  const GEAR = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "gear.js"), "utf8");
  assert.ok(GEAR.includes("'setFileEditing'"), "the gear can turn it back off");
  const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");
  assert.match(KERNEL, /if not _file_editing_on\(\):/);
  assert.match(KERNEL, /dashboard file editing is off on this machine/);
});

// executed: the Escape handler's LIFECYCLE. Each open registers its own document-level onKey
// closure; the REPLACE path (the conflict-Reload re-open) used to leave the old viewer's handler
// registered, and with a new viewer up its `!getElementById` guard no longer no-ops — the stale
// closure (editing still true from before the replace) ran exitEdit against the NEW viewer's
// world and nulled the module-level editHooks an in-flight save was waiting on, so the fileSaved
// ack matched nothing and Save wedged at "Saving…" (Reload → re-edit → Escape mid-save). The
// model replays that journey against both lifecycles.
test("replace-open drops the previous viewer's Escape handler — a stale closure cannot null a new save's hooks", () => {
  const sim = (dropOnReplace: boolean) => {
    const listeners: Array<() => void> = [];
    let editHooks: { reqId: number } | null = null;     // module-level, as in the source
    let live: (() => void) | null = null;
    const dropOnKey = () => {
      if (live) { const i = listeners.indexOf(live); if (i >= 0) listeners.splice(i, 1); live = null; }
    };
    const open = () => {
      if (dropOnReplace) dropOnKey();                   // the fix: the replace path unregisters
      editHooks = null;                                 // the replace path's existing module drops
      const v = { editing: false, dirty: false };
      const exitEdit = () => { v.editing = false; editHooks = null; };  // source: exitEdit nulls the hooks
      const onKey = () => {                             // Escape peels edit mode behind confirmDiscard
        if (v.editing && !v.dirty) exitEdit();          // !dirty short-circuits the confirm — no user gate
      };
      listeners.push(onKey); live = onKey;
      return v;
    };
    const a = open();
    a.editing = true; a.dirty = true;                   // mid-edit when the agent's write conflicts
    a.dirty = false;                                    // Reload's confirmed discard clears it pre-replace
    const b = open();                                   // the replace-open (openFileView over viewer A)
    b.editing = true; b.dirty = true;                   // re-edit…
    editHooks = { reqId: 7 };                           // …Save in flight ("Saving…")
    for (const fn of [...listeners]) fn();              // Escape mid-save; the user keeps B's edits
    return { ackLands: editHooks !== null, liveHandlers: listeners.length };
  };
  assert.equal(sim(false).ackLands, false,
    "pre-fix lifecycle: A's stale closure nulls the hooks and B's ack is dropped — the wedge");
  const fixed = sim(true);
  assert.equal(fixed.ackLands, true, "with the replace-path drop only the live viewer's handler runs");
  assert.equal(fixed.liveHandlers, 1, "one viewer, one document-level handler");
  // replica ↔ source: ONE live handler tracked at module level, dropped by BOTH exits after their
  // dirty guards — closeFileView and the replace path — and re-pointed at each open's own closure
  assert.match(VIEW, /let onKeyLive: \(\(e: KeyboardEvent\) => void\) \| null = null;/);
  const closeFn = VIEW.split("export function closeFileView")[1].split("/** Show `path`")[0];
  assert.match(closeFn, /dropOnKey\(\);/, "closeFileView unregisters the handler it would strand");
  const openFn = VIEW.split("export function openFileView")[1].split("function offersDownload")[0];
  assert.ok(openFn.indexOf("dropOnKey();") > openFn.indexOf("closeGuard && !closeGuard()) return false;"),
    "the drop sits AFTER the dirty-guard veto — a kept viewer keeps its handler");
  assert.ok(openFn.indexOf("dropOnKey();") < openFn.indexOf('document.getElementById("romp-fileview")?.remove();'),
    "…and with the replace path's other module-level drops, before the old viewer is torn down");
  assert.match(openFn, /document\.addEventListener\("keydown", onKey\);\s*\n\s*onKeyLive = onKey;/);
});

// executed: the consent gate is enforced by the file-OWNING kernel, but the Edit click's /version
// read sees only the LOCAL flag — a mesh kernel attached AFTER the one yes never heard the
// broadcast, so it refuses every save with copy pointing at a popup the local flag keeps from ever
// re-showing. The failed handler therefore recognizes the gate refusal, re-offers the SAME consent
// naming the machine that refused, and a yes re-broadcasts setFileEditing (KERNEL_SETTING reaches
// every attached kernel, the late one included) and retries the save — the broadcast and the save
// ride the same ordered socket, so the flag lands first.
test("a save refused by the OWNING kernel's edit gate re-offers the consent and re-broadcasts", () => {
  const gateRefusal = (err: string): boolean => /file editing is off/.test(err);
  assert.equal(gateRefusal("cannot save ~/notes-api/app.py: dashboard file editing is off on this "
    + "machine — the viewer's Edit button asks to turn it on"), true);
  assert.equal(gateRefusal("~/notes-api/app.py changed on disk since you opened it — reload before "
    + "editing (someone else, likely an agent, wrote it)"), false,
    "a conflict keeps its Reload offer — never a consent popup");
  assert.equal(gateRefusal("cannot save ~/notes-api/app.py: the file is not UTF-8 on disk — saving "
    + "would silently re-encode bytes you never touched"), false);
  // replica ↔ source: the failed handler carries the branch, names the host, re-posts, retries
  assert.match(VIEW, /if \(\/file editing is off\/\.test\(err\)\) \{/);
  assert.match(VIEW, /import \{[^}]*\bhostOf\b[^}]*\} from "\.\/host-prefix";/,   // beside the session chip's helpers since 2026-09-03
    "the popup names the refusing machine — the host prefix the viewer's sid already carries");
  const failedArm = VIEW.split("failed: (err) => {")[1].split("body.prepend(bar2);")[0];
  assert.ok(failedArm.includes('post({ type: "setFileEditing", enabled: true, gt: Date.now() });'),
    "a yes re-broadcasts the SAME opt-in the first popup sends — gesture-stamped like it");
  assert.ok(failedArm.includes("doSave();"), "…and retries the save the refusal interrupted");
  assert.ok(failedArm.indexOf("setFileEditing") < failedArm.indexOf("doSave();"),
    "the opt-in rides the socket ahead of the retry");
  // the two sides of the text match are pinned TOGETHER so drift fails loudly, and the broadcast
  // route the re-offer relies on is federation's, not a new one
  const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");
  assert.match(KERNEL, /dashboard file editing is off on this machine/);
  const FED = web("federation.ts");
  assert.ok(FED.includes('"setFileEditing"'), "setFileEditing is a KERNEL_SETTING…");
  assert.match(FED, /if \(KERNEL_SETTING\.has\(msg\.type\)\) return \[LOCAL, \.\.\.\(knownHosts \|\| \[\]\)\]/,
    "…and KERNEL_SETTING broadcasts to every attached kernel");
});

// ── inline images + PDFs: a clicked .png used to open as line-numbered mojibake — the fetch pipeline
// called r.text() unconditionally on any 200. The viewer branches on the KERNEL'S OWN Content-Type
// verdict (the authoritative-source rule; the kernel derives mime locally and the relay re-derives
// it, so the header is a verdict, never an echo — no client-side extension re-test), takes the
// already-fetched bytes as a blob (no second request), and renders media as media. ──

// executed: the routing replica — which body call a 200 gets, by the kernel's header alone
test("the media branch keys on the kernel's Content-Type verdict, never the extension", () => {
  const mediaKind = (ct: string): "img" | "pdf" | null =>
    ct.startsWith("image/") ? "img" : ct.startsWith("application/pdf") ? "pdf" : null;
  assert.equal(mediaKind("image/png"), "img");
  assert.equal(mediaKind("image/svg+xml"), "img", "SVG is an image here — the <img> surface");
  assert.equal(mediaKind("application/pdf"), "pdf");
  assert.equal(mediaKind("text/plain; charset=utf-8"), null, "text keeps the r.text() pipeline unchanged");
  assert.equal(mediaKind(""), null, "no header → the text path, exactly the pre-image behavior");
  // replica ↔ source: the flags read the kernel's header, and blob is taken ONLY for media
  assert.match(VIEW, /const ct = r\.headers\.get\("Content-Type"\) \|\| "";/);
  assert.match(VIEW, /isImage = ct\.startsWith\("image\/"\);/);
  assert.match(VIEW, /isPdf = ct\.startsWith\("application\/pdf"\);/);
  assert.match(VIEW, /return isImage \|\| isPdf \? r\.blob\(\) : r\.text\(\);/);
  // never a client-side extension re-test: preview.ts's extension probe stays out of this module
  assert.doesNotMatch(VIEW, /previewKind\(/);
  assert.doesNotMatch(VIEW, /IMG_EXT/);
});

test("a 200 image renders ONE <img> at an object URL; the quote gesture stays off RENDERED media", () => {
  const openFn = VIEW.split("export function openFileView")[1].split("function offersDownload")[0];
  // the blob becomes an object URL only AFTER the still-open/still-this-viewer checks — a viewer
  // closed or replaced mid-flight creates nothing to leak
  assert.ok(openFn.indexOf('if (!document.getElementById("romp-fileview")) return;')
            < openFn.indexOf("URL.createObjectURL"),
    "no URL is minted for a viewer that is already gone");
  assert.match(openFn, /if \(!wrap\.isConnected\) return;/);
  // renderBody's img/PDF arm renders and returns — an <img>/iframe body has no honest text to
  // quote (affordance honesty: no real target, no affordance), so the mouseup seed gates off
  // RENDERED media too. The SVG SOURCE view is the deliberate exception — a text view, covered by
  // the media-gate test below.
  const mediaBranch = VIEW.split("if (isImage || isPdf) {")[1].split("if (text === null || editing) return;")[0];
  const renderedArm = mediaBranch.slice(mediaBranch.indexOf("body.replaceChildren(isPdf"));
  assert.ok(renderedArm.length > 0, "the img/PDF render arm exists");
  assert.match(mediaBranch, /imgBlock\(objUrl, path, imgFailed\)/);
  assert.match(VIEW, /if \(\(isImage \|\| isPdf\) && !\(svgSource && svgText !== null\)\) return;/);
  // the romp loader holds the body until the bytes land (the loading-state rule)
  assert.match(mediaBranch, /if \(objUrl === null\) return;/);
  // the <img> itself: one element, src = the object URL, capped like the lightbox's image on BOTH
  // sheets (the viewer mounts in both documents — the .romp-acted precedent)
  const imgFn = VIEW.split("function imgBlock")[1].split("// The PDF body")[0];
  assert.match(imgFn, /el\("img", "fileview-img"\)/);
  assert.match(imgFn, /img\.src = objUrl;/);
  for (const SHEET of [FEED_CSS, CHAT_CSS]) {
    assert.match(SHEET, /\.fileview-img \{[^}]*object-fit: contain[^}]*\}/);
    assert.match(SHEET, /\.fileview-imgbox \{/);
  }
});

// ── media gating is RENDERED-media gating (re-homed from the retired review layer's
// suite): the gate's rationale — "no honest text to quote" — is true of the img/PDF
// surfaces only. The SVG SOURCE view is codeBlock output, real text nodes, so a selection there
// seeds a labeled quote chip exactly as in any text view; a blanket media gate would make an
// .svg's XML unquotable. ──
test("the quote seed gates off RENDERED media only — the SVG Source view is a text view like any other", () => {
  // executed: the seed offer across the view states (the no-target gate holds throughout —
  // a reachable composer (own document, or the chat's through the shell) plays the role the old
  // comment sink did: no real target, no gesture)
  const seedable = (target: boolean, isImage: boolean, isPdf: boolean, srcView: boolean): boolean =>
    target && !((isImage || isPdf) && !srcView);
  assert.equal(seedable(true, true, false, true), true, "SVG Source view: the selection seeds a chip");
  assert.equal(seedable(true, true, false, false), false, "the img view has no honest text to quote");
  assert.equal(seedable(true, false, true, false), false, "the PDF iframe owns its own surface");
  assert.equal(seedable(false, true, false, true), false, "no composer reachable still gates everything off");
  assert.equal(seedable(true, false, false, false), true, "plain text views are untouched");
  // source: the media arm of the mouseup gate carves out the Source view, sitting AFTER the
  // no-target gate (whose pin lives in the feed-inert test above)
  assert.match(VIEW, /if \(!seedTarget\) return;\n(\s*\/\/[^\n]*\n)*\s*if \(\(isImage \|\| isPdf\) && !\(svgSource && svgText !== null\)\) return;/);
  // anchoring reads the text THE VIEW SHOWS — the Source view's decoded XML, never the text
  // pipeline's null — so a quote on the XML earns its path:line label (viewText, pinned with the
  // fresh-read test above); renderBody's Source arm builds those text nodes through codeBlock
  const mediaBranch = VIEW.split("if (isImage || isPdf) {")[1].split("if (text === null || editing) return;")[0];
  const srcArm = (mediaBranch.split("if (svgSource && svgText !== null) {")[1] || "").split("\n      }")[0];
  assert.ok(srcArm, "the Source-view arm exists inside the media branch");
  assert.match(srcArm, /body\.replaceChildren\(codeBlock\(svgText, path, true\)\);/);
});

test("image mode hides Edit; Download, Copy path, GitHub, ✕ and the dir-link survive", () => {
  const mediaBranch = VIEW.split("if (isImage || isPdf) {")[1].split("if (text === null || editing) return;")[0];
  // (Wrap needs no hiding — the toggle button is gone everywhere, its stored key pinned away above)
  // Edit was ALREADY gated on the kernel's text verdict — an image/* response sets isText false, so
  // the existing arm hides it; both halves stay pinned (file-edit.test.ts pins the isText line too)
  assert.match(VIEW, /isText = \(r\.headers\.get\("Content-Type"\) \|\| ""\)\.startsWith\("text\/plain"\)/);
  assert.match(VIEW, /editBtn\.hidden = editing \|\| text === null \|\| !isText \|\| !mtimeNs;/);
  // the media branch touches NONE of the keepers — they are built unconditionally before the fetch
  // (the dir-link rides the title bar, outside renderBody entirely)
  for (const keeper of ["dl.", "copy.", "close.", "gh."])
    assert.ok(!mediaBranch.includes(keeper), keeper + " must not be re-hidden for images");
  // markdown's Rendered/Raw segs exist only for .md files (the isMd gate, pinned above), and an .md
  // is never served image/* — so the segs cannot coexist with an image body by construction
});

test("SVG renders via <img> ONLY — never innerHTML, never an iframe: its scripts must never run", () => {
  // the kernel serves .svg as image/svg+xml on purpose (an <img> never runs SVG scripts — kernel.py's
  // preview comment), and the relay re-derives the type locally; the viewer must keep that surface
  const imgFn = VIEW.split("function imgBlock")[1].split("// The PDF body")[0];
  assert.doesNotMatch(imgFn, /innerHTML/, "the XSS property: SVG bytes never become live DOM");
  assert.doesNotMatch(imgFn, /iframe/, "an iframed SVG is a document — scripts would run");
  assert.match(imgFn, /el\("img", "fileview-img"\)/);
  // THE MEDIA BRANCH ITSELF is the surface a mutation actually hits (a proven mutation: a
  // `body.innerHTML = svgText` swapped into the branch kept every test green — the innerHTML pin
  // above covers only imgBlock, and a codeBlock string pin matched its own commented-out corpse).
  // So the branch source is audited directly: no HTML-parsing sink of ANY kind, in code or comment.
  const mediaBranch = VIEW.split("if (isImage || isPdf) {")[1].split("if (text === null || editing) return;")[0];
  assert.ok(mediaBranch.length > 0, "media-branch anchors moved — re-anchor this extraction");
  assert.doesNotMatch(mediaBranch, /innerHTML/, "the XSS property, on the branch that holds the bytes");
  assert.doesNotMatch(mediaBranch, /insertAdjacentHTML/);
  assert.doesNotMatch(mediaBranch, /outerHTML|document\.write|DOMParser|createContextualFragment/);
  // …its only writes to the body element are replaceChildren of BUILT elements (the safe sink) —
  // a new sink added to the branch must show up here and be argued for
  const sinks = mediaBranch.match(/body\.\w+\s*[(=]/g) || [];
  assert.ok(sinks.length > 0 && sinks.every((s) => /^body\.replaceChildren\s*\($/.test(s)),
    "the media branch's only body writes are replaceChildren(...): " + JSON.stringify(sinks));
  // …and the Source toggle's codeBlock render — the same escape/highlight path every text file
  // takes (textContent / escapeHtml), never a parse into live DOM — is LIVE CODE, not a comment
  const live = mediaBranch.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/[^\n]*/g, "");
  assert.match(live, /body\.replaceChildren\(codeBlock\(svgText, path, true\)\)/,
    "the SVG Source view renders through codeBlock, uncommented (born wrapped, like every code view)");
  assert.match(VIEW, /isSvgImage = ct === "image\/svg\+xml";/, "the toggle keys on the kernel's verdict too");
  assert.match(VIEW, /mediaBlob\.text\(\)/, "the source view decodes the SAME fetched bytes — no second request");
});

// executed: the object-URL lifecycle (the Escape-handler test's shape) — every teardown revokes
test("the object URL is revoked on close AND on replace-open — none leaks, one live at a time", () => {
  const sim = () => {
    let live: string | null = null;
    let seq = 0;
    const revoked: string[] = [];
    const dropMediaUrl = () => { if (live) { revoked.push(live); live = null; } };
    const openView = () => { dropMediaUrl(); live = "blob:" + ++seq; };  // replace-teardown, then the fetch lands
    const closeView = () => dropMediaUrl();
    openView();          // an image opens
    openView();          // Reload / a second click replaces it — blob:1 must go
    closeView();         // ✕ — blob:2 must go
    return { revoked, live };
  };
  const r = sim();
  assert.deepEqual(r.revoked, ["blob:1", "blob:2"], "the replaced URL AND the closed URL both go");
  assert.equal(r.live, null, "nothing outlives the viewer");
  // replica ↔ source: ONE module-level registration, dropped by BOTH exits (the editHooks/gitHooks/
  // onKeyLive precedent), revoking through URL.revokeObjectURL
  assert.match(VIEW, /let mediaUrlLive: string \| null = null;/);
  assert.match(VIEW, /URL\.revokeObjectURL\(mediaUrlLive\)/);
  const closeFn = VIEW.split("export function closeFileView")[1].split("/** Show `path`")[0];
  assert.match(closeFn, /dropMediaUrl\(\);/, "close revokes");
  const openFn = VIEW.split("export function openFileView")[1].split("function offersDownload")[0];
  assert.match(openFn, /dropMediaUrl\(\);/, "the replace path revokes (the conflict Reload re-opens through here)");
  assert.ok(openFn.indexOf("dropMediaUrl();") < openFn.indexOf('document.getElementById("romp-fileview")?.remove();'),
    "…before the old viewer is torn down, beside the other module-level drops");
  assert.match(openFn, /mediaUrlLive = objUrl;/, "the minted URL is exactly what the teardowns revoke");
});

test("an oversize image lands on the kernel's words + Download — a 413 never reaches the media branch", () => {
  // executed: the pipeline model — !ok throws (status attached) BEFORE any Content-Type branching
  const route = (ok: boolean, ct: string): "error" | "img" | "pdf" | "text" => {
    if (!ok) return "error";
    return ct.startsWith("image/") ? "img" : ct.startsWith("application/pdf") ? "pdf" : "text";
  };
  assert.equal(route(false, "text/plain"), "error",
    "the kernel 413s an oversize image with a text/plain body naming the size and the cap");
  assert.equal(route(true, "image/png"), "img");
  const offersDownload = (status: number | undefined): boolean => status === 413 || status === 415;
  assert.equal(offersDownload(413), true, "…and the error pane still offers the Download the view could not be");
  // source ordering: the throw sits before the media flags are ever assigned
  assert.ok(VIEW.indexOf("if (!r.ok) return r.text().then((t) => {")
            < VIEW.indexOf('isImage = ct.startsWith("image/");'));
});

test("a PDF takes the lightbox's exact iframe treatment, aimed at the already-fetched blob", () => {
  const PREVIEW = web("preview.ts");
  // the reference: openLightbox's pdf arm is a PLAIN iframe — className, src, title, no sandbox
  // attributes to mirror or forget
  assert.match(PREVIEW, /frame\.className = "romp-lightbox-frame";\s*\n\s*frame\.src = fileUrl\(path, sid\);\s*\n\s*frame\.title = path;/);
  const pdfFn = VIEW.split("function pdfBlock")[1].split("/** Bind the pane's WS poster")[0];
  assert.match(pdfFn, /el\("iframe", "fileview-frame"\)/);
  assert.match(pdfFn, /frame\.src = objUrl;/, "the blob URL — the bytes were already fetched once");
  assert.match(pdfFn, /frame\.title = path;/);
  assert.doesNotMatch(pdfFn, /sandbox/, "the lightbox sets none; inventing one here would be a different surface");
  const mediaBranch = VIEW.split("if (isImage || isPdf) {")[1].split("if (text === null || editing) return;")[0];
  assert.match(mediaBranch, /isPdf \? pdfBlock\(objUrl, path\) : imgBlock\(objUrl, path, imgFailed\)/);
  for (const SHEET of [FEED_CSS, CHAT_CSS]) assert.match(SHEET, /\.fileview-frame \{[^}]*height: 100%/);
});

// ── decode failure: a zero-byte or mid-write/truncated image is a 200 whose BYTES will not decode —
// the browser fires the img's error event and used to leave its mute broken-image glyph: no reason,
// no way out. The viewer answers with the 413/415 pane idiom instead: plain words naming what
// happened, the path, and the Download the view could not be. The img's own error event is the
// exact deciding signal (never a timer, never a byte sniff). The PDF iframe has NO equivalent
// failure event — the browser's own viewer owns that surface and reports inside it — so this
// covers images only, deliberately. ──

test("an image 200 that fails to DECODE swaps to the failure pane: plain words + Download, never a mute glyph", () => {
  // executed: the handler's continuation — an object URL of garbage bytes fires `error` once, and
  // the pane replaces the glyph; a decodable image never invokes it
  const sim = (decodes: boolean) => {
    let pane: string[] = [];
    let armed: (() => void) | null = null;
    const imgBlock = (onDecodeFail: () => void): string => { armed = onDecodeFail; return "img"; };
    const imgFailed = () => { pane = ["this image failed to decode — it may be mid-write or truncated", "Download"]; };
    pane = [imgBlock(imgFailed)];              // the media branch renders the img, handler armed
    if (!decodes) armed!();                    // garbage bytes: the browser fires the img's error event
    return pane;
  };
  assert.deepEqual(sim(true), ["img"], "a decodable image just shows");
  assert.deepEqual(sim(false),
    ["this image failed to decode — it may be mid-write or truncated", "Download"],
    "garbage bytes land on words + the way out");
  // source: the handler rides the img itself, armed BEFORE src so no event can slip past it
  const imgFn = VIEW.split("function imgBlock")[1].split("// The PDF body")[0];
  assert.match(imgFn, /^\(objUrl: string, path: string, onDecodeFail: \(\) => void\)/);
  assert.match(imgFn, /img\.addEventListener\("error", onDecodeFail, \{ once: true \}\);\s*\n\s*img\.src = objUrl;/);
  // …and the continuation builds the EXACT failure idiom the 413/415 catch renders: fileview-err
  // words + the path hint + the fileview-err-dl Download wired through startDownload
  const openFn = VIEW.split("export function openFileView")[1].split("function offersDownload")[0];
  const failFn = (openFn.split("const imgFailed = ")[1] || "").split("\n  };")[0];
  assert.ok(failFn, "imgFailed lives in the open viewer's closure — it needs body and dlUrl");
  assert.match(failFn, /el\("div", "fileview-err"\)/);
  assert.match(failFn, /failed to decode/);
  assert.match(failFn, /mid-write or truncated/);
  assert.match(failFn, /el\("div", "fileview-err-hint"\)/);
  assert.match(failFn, /hint\.textContent = path;/);
  assert.match(failFn, /el\("button", "fileview-btn fileview-err-dl"\)/);
  assert.match(failFn, /startDownload\(dlUrl, offer\)/);
  assert.match(failFn, /body\.replaceChildren\(why\);/);
  // a decode failure that settles after the viewer was closed or replaced paints nothing
  assert.match(failFn, /if \(!wrap\.isConnected\) return;/);
  // the PDF arm stays bare — an iframe fires no decode-failure event to key on
  const pdfFn = VIEW.split("function pdfBlock")[1].split("/** Bind the pane's WS poster")[0];
  assert.doesNotMatch(pdfFn, /addEventListener/, "no synthetic failure signal invented for the iframe");
});

// executed: the gutter is a SIBLING of the code, so selecting the code copies it without line numbers
test("the line gutter numbers every line and drops a trailing newline's phantom line", () => {
  const lines = (text: string): string[] => {
    const l = text.split("\n");
    if (l.length && l[l.length - 1] === "") l.pop();
    return l;
  };
  assert.deepEqual(lines("a\nb\nc\n").length, 3, "a trailing newline is not a fourth line");
  assert.deepEqual(lines("a\nb\nc").length, 3);
  assert.deepEqual(lines(""), []);
  assert.match(VIEW, /gutter\.textContent = lines\.map\(\(_, i\) => String\(i \+ 1\)\)\.join\("\\n"\);/);
  assert.match(VIEW, /wrap\.appendChild\(gutter\); wrap\.appendChild\(pre\);/, "sibling, not inside the pre");
  assert.match(FEED_CSS, /\.fileview-gutter \{[\s\S]*?user-select: none;/);
  assert.match(CHAT_CSS, /\.fileview-gutter \{[\s\S]*?user-select: none;/);
});

// ── the session chip (the user 2026-09-03): the title bar names the session the file was opened
// from. The viewer knows only a sid — and three of its four openers (the shell relay, the conflict
// Reload, the file browser) live inside this module or hand over a bare sid — so the identity is
// RESOLVED from the sid through a lookup each hosting document registers once at boot. ──

test("the title bar carries a session chip resolved from the sid — never invented, absent when unknown", () => {
  assert.match(VIEW, /import \{ hostOf, bareId, hostNameNodes \} from "\.\/host-prefix";/);
  assert.match(VIEW, /export interface FileViewIdentity \{ name: string; color: \{ bg: string; fg: string \} \| null \}/);
  assert.match(VIEW, /let identityOf: \(sid: string\) => FileViewIdentity \| null = \(\) => null;/,
    "unregistered → nothing to show, not a guess");
  assert.match(VIEW, /export function setFileViewIdentity\(fn: typeof identityOf\): void \{ identityOf = fn; \}/);
  const openFn = VIEW.split("export function openFileView")[1].split("function offersDownload")[0];
  assert.match(openFn, /const owner = sid \? identityOf\(sid\) : null;/, "no sid → the resolver is not even asked");
  assert.match(openFn, /if \(owner\) \{\n\s*sess = el\("span", "fileview-sess"\);/, "no identity → no chip element at all");
  assert.match(openFn, /sess\.replaceChildren\(\.\.\.hostNameNodes\(owner\.name, sid\)\);/, "host: quiet for a remote session");
  assert.match(openFn, /if \(owner\.color\) \{ sess\.style\.background = owner\.color\.bg; sess\.style\.color = owner\.color\.fg; \}/,
    "the session's identity colour, inline — an uncolored stub keeps the sheet's neutral pill");
  assert.match(openFn, /sess\.title = "Opened from the " \+ owner\.name \+ " session";/,
    "capitalized like this bar's other tooltips; 'session' so a name like web is not read as a place");
  assert.match(openFn, /bar\.appendChild\(name\); if \(sess\) bar\.appendChild\(sess\); bar\.appendChild\(acts\);/,
    "between the path and the actions");
  // the signatures every opener and the relay pin depend on are as they were, plus the optional todoId
  // provenance (plans/file-review.md Slice 0: the Waiting-on-you detail link) — every existing caller unchanged
  assert.match(VIEW, /export function openFileView\(path: string, sid\?: string \| null, opts\?: \{ todoId\?: string \| null \}\): boolean \{/);
  // (the optional onRelay — the Files pane's own relay contract, 2026-09-03 — leaves the poster's shape alone)
  assert.match(VIEW, /export function initFileView\(poster: \(m: Record<string, unknown>\) => void,\n\s*onRelay\?: \(m: \{ path: string; sid\?: unknown; identity\?: unknown; todoId\?: unknown \}\) => void\): void \{/);
});

test("both hosting documents register a resolver beside their initFileView boot", () => {
  // the chat document: the tab set, the way renderTabs names a tab (the session first, then the
  // kernel's tab meta, which keeps a dormant session's name and colour)
  assert.match(RENDER, /import \{ initFileView, setFileViewIdentity, hostStub \} from "\.\/file-view";/);
  assert.match(RENDER, /initFileView\(\(m\) => vscodeApi\?\.postMessage\(m\)\);\n(\/\/.*\n)*setFileViewIdentity\(\(id\) => \{\n\s*const s = sessions\.get\(id\) \?\? tabMeta\.get\(id\);\n\s*return s && s\.name \? \{ name: s\.name, color: s\.color \?\? null \} : hostStub\(id\);\n\}\);/);
  // the feed document: its session list (the same tab set, relayed per frame), else a card carrying
  // the session's name and colour — never sessionColors, which is keyed by NAME, not sid
  assert.match(FEED, /import \{ initFileView, setFileViewIdentity, hostStub \} from "\.\/file-view";/);
  assert.match(FEED, /initFileView\(\(m\) => vscodeApi\?\.postMessage\(m\)\);.*\n(\/\/.*\n)*setFileViewIdentity\(\(id\) => \{\n\s*const s = sessionsMeta\.find\(\(x\) => x\.sid === id\) \?\? asks\.find\(\(a\) => a\.sid === id\);\n\s*return s && s\.name \? \{ name: s\.name, color: s\.color \?\? null \} : hostStub\(id\);\n\}\);/);
  const feedReg = FEED.split("setFileViewIdentity(")[1].split("});")[0];
  assert.doesNotMatch(feedReg, /sessionColors/, "a name-keyed index cannot answer a sid");
});

// executed: the ladder each document's resolver runs — its own lists, then the kernel's
// _peer_identity fallback (a remote sid's host + the sid's first 8 characters, uncolored), then no
// chip at all. Synthetic rows: the notes-api world, TESTHOST for the remote kernel.
test("resolver ladder: a named session, then a host-prefixed 8-char stub, then no chip", () => {
  type Id = { name: string; color: { bg: string; fg: string } | null };
  const hostOf = (id: string) => { const i = id.indexOf(":"); return i > 0 ? id.slice(0, i) : ""; };
  const bareId = (id: string) => { const i = id.indexOf(":"); return i > 0 ? id.slice(i + 1) : id; };
  const hostStub = (sid: string): Id | null => {
    const bare = bareId(sid);
    if (!bare) return null;
    const host = hostOf(sid);
    return { name: (host ? host + ":" : "") + bare.slice(0, 8), color: null };
  };
  const WEB = "11111111-2222-3333-4444-555555555555";
  const API = "22222222-3333-4444-5555-666666666666";
  const TESTS = "33333333-4444-5555-6666-777777777777";
  const rows = new Map<string, Id>([
    [WEB, { name: "web", color: { bg: "#3a7bd5", fg: "#ffffff" } }],
    ["TESTHOST:" + API, { name: "TESTHOST:api", color: { bg: "#d53a7b", fg: "#ffffff" } }],   // federation prefixes sid AND name
    [TESTS, { name: "", color: null }],                                                        // a placeholder tab, name not yet known
  ]);
  const resolve = (id: string): Id | null => {
    const s = rows.get(id);
    return s && s.name ? { name: s.name, color: s.color ?? null } : hostStub(id);
  };
  assert.deepEqual(resolve(WEB), { name: "web", color: { bg: "#3a7bd5", fg: "#ffffff" } });
  assert.deepEqual(resolve("TESTHOST:" + API), { name: "TESTHOST:api", color: { bg: "#d53a7b", fg: "#ffffff" } },
    "a remote row keeps its host: prefix — hostNameNodes renders it as quiet metadata");
  assert.deepEqual(resolve("44444444-5555-6666-7777-888888888888"), { name: "44444444", color: null },
    "an unknown local sid → the kernel's 8-character stub, uncolored");
  assert.deepEqual(resolve("TESTHOST:44444444-5555-6666-7777-888888888888"), { name: "TESTHOST:44444444", color: null },
    "an unknown remote sid → host: + stub, so the host still reads as metadata");
  assert.deepEqual(resolve(TESTS), { name: "33333333", color: null },
    "a row with no name yet is not a name — the stub, never an empty chip");
  assert.equal(resolve(""), null, "no sid → no chip");
  assert.equal(resolve("TESTHOST:"), null, "a host with no sid names nothing");
  // replica ↔ source
  assert.match(VIEW, /export function hostStub\(sid: string\): FileViewIdentity \| null \{\n\s*const bare = bareId\(sid\);\n\s*if \(!bare\) return null;\n\s*const host = hostOf\(sid\);\n\s*return \{ name: \(host \? host \+ ":" : ""\) \+ bare\.slice\(0, 8\), color: null \};\n\}/);
});

test("the chip's dress is in BOTH sheets: a fixed-width pill that never yields to the path", () => {
  for (const css of [CHAT_CSS, FEED_CSS]) {
    assert.match(css, /\.fileview-sess \{ flex: 0 0 auto; display: inline-flex;/);
    // color:inherit so the host: token takes the pill's own fg — the global .host-prefix{color:var(--dim)}
    // otherwise wins over the inline white and the token is near-invisible on a coloured pill (the
    // 2026-09-03 review: ~1:1 contrast for a remote session's chip). opacity keeps it quiet without dimming
    // to gray.
    assert.match(css, /\.fileview-sess \.host-prefix \{ color: inherit; opacity: 0\.75; \}/, "the host: token uses the pill's fg, quiet");
  }
});
