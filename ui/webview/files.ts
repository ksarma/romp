// "Files" — the file VIEWER as its own column of the dashboard (the user 2026-09-03). A file opened
// over the chat or the feed covers what the person was reading and goes the moment they look away;
// this pane keeps the file up beside the chat and the feed, and when nothing is open it lists the
// files most recently open here as re-open links, so a thread dropped yesterday costs one click.
//
// It hosts the same shared viewer (file-view.ts) every other document does, pane-resident by CSS
// alone (files-pane.css, keyed on body.fileview-pane: no backdrop, no card inset). The pane is NOT a
// feed consumer: the viewer is request/response — bytes over HTTP /file (fileUrl, host-routed for a
// remote session's file), and its WS ops answer this socket — so no frame is parsed here; the shim
// opens app=files with the ready hold alone, and federation.js (loaded by the page, never imported)
// routes a host:sid op to the kernel that owns the session through the fake acquireVsCodeApi.
//
// Two things the pane supplies itself, because it has NO session list of its own:
//   • the shell's relay ({romp:"viewFile", path, sid, identity}) carries the session's name and colour,
//     resolved at the click site (render.ts openPath knows its tabs); the pane caches them per sid and
//     registers that cache as the viewer's identity resolver, so the title bar's session chip renders
//     here exactly as it does over the chat (the kernel's 8-character stub when the relay carried none);
//   • the relay is taken WHOLE (initFileView's onRelay): the default relay branch is the FEED's contract
//     (viaRelay + the viewFileOpened ack, which arm the shell's pane restore), and the Files pane owes
//     the shell no restore — it stays up; that is the point of it.
//   • the shell's browseFiles relay ({romp:"browseFiles", path, sid, identity}: a folder clicked in the chat
//     while this pane is on screen or the File-links setting names it, render.ts openBrowse; the user
//     2026-09-06) opens the file BROWSER here, the listing as its own column. The identity it carries is
//     cached the same way, so a file picked from the listing names its session in the chip. The browser
//     owes the shell no browseClosed either (initFileBrowse's shellRestore false): the pane stays up, and
//     that message is the FEED's restore.
// Close returns to the empty state, never to a hidden pane: closeFileView and closeFileBrowse only remove
// their element, and the placeholder repaints when neither is up (a body childList observer — the event
// itself, no polling), which also covers the browser's "‹ Files" back path and the conflict Reload's replace.
import { initFileView, openFileView, setFileViewIdentity, hostStub, type FileViewIdentity } from "./file-view";
import { initFileBrowse, openFileBrowse } from "./file-browse";
import { delegate } from "./actions";
import { applyTheme } from "./theme";
import { loadSettings, installSettingsSync, onExternalSettingsChange } from "./settings";
import { hostNameNodes } from "./host-prefix";
import { asIdentity, parseRecent, rememberRecent, RECENT_KEY, type RecentFile } from "./files-recent";

const vscodeApi =
  typeof (window as any).acquireVsCodeApi === "function" ? (window as any).acquireVsCodeApi() : undefined;

// sid → the identity the relay (or a recent row) handed over; the viewer's session chip resolves through it
const identities = new Map<string, FileViewIdentity>();
let recent: RecentFile[] = parseRecent(readStore());

function el(tag: string, cls?: string): HTMLElement { const e = document.createElement(tag); if (cls) e.className = cls; return e; }
// The pane is SHOWING something while the viewer or the browser is up: both are body children by id (the
// viewer's modal wrap, the browser's fixed box), both come and go by element, so presence is the state.
function surfaceUp(): boolean {
  return !!(document.getElementById("romp-fileview") || document.getElementById("romp-filebrowse"));
}
function readStore(): string | null { try { return localStorage.getItem(RECENT_KEY); } catch { return null; } }
function writeStore(): void { try { localStorage.setItem(RECENT_KEY, JSON.stringify(recent)); } catch { /* storage may be denied */ } }

/** Open `path` here: cache the identity so the chip resolves, open the shared viewer, and record the file
 *  as recent only when the open really happened (a dirty-edit veto keeps the previous viewer up).
 *  `todoId` is the user todo a Waiting-on-you detail link opened it from (the relay carries it; the recent
 *  list does not — a re-open is no longer that todo). */
function openHere(path: string, sid: string | null, identity: FileViewIdentity | null, todoId: string | null = null): void {
  if (sid && identity) identities.set(sid, identity);
  if (!openFileView(path, sid, { todoId })) return;
  const known = identity ?? (sid ? identities.get(sid) ?? null : null);
  recent = rememberRecent(recent, { path, sid, identity: known, t: Date.now() });
  writeStore();
  paint();
}

// The empty state: the pane's purpose in one line, and the recent files as re-open rows. The rows wear
// the viewer's own title-bar classes (path split dir/base, the session chip), so a path reads here
// exactly as it does above an open file. Hidden, not removed, while a viewer is up.
function paint(): void {
  const empty = document.getElementById("files-empty");
  if (!empty) return;
  const open = surfaceUp();
  empty.hidden = open;
  if (open) return;
  const title = el("div", "fs-title"); title.textContent = "No file open";
  const hint = el("div", "fs-hint");
  hint.textContent = "To open files here, set File links open in to the Files pane in the gear.";
  const out: HTMLElement[] = [title, hint];
  if (recent.length) {
    const box = el("div", "fs-recent");
    const head = el("div", "fs-recent-head"); head.textContent = "Recent";
    box.appendChild(head);
    recent.forEach((r, i) => {
      const row = el("div", "fs-row");
      row.dataset.act = "open"; row.dataset.i = String(i); row.title = r.path;
      const name = el("div", "fileview-name");
      const cut = r.path.lastIndexOf("/");
      const dir = el("span", "fileview-dir"); dir.textContent = cut >= 0 ? r.path.slice(0, cut + 1) : "";
      const base = el("span", "fileview-base"); base.textContent = r.path.slice(cut + 1);
      name.append(dir, base);
      row.appendChild(name);
      if (r.identity) {
        const sess = el("span", "fileview-sess");
        sess.replaceChildren(...hostNameNodes(r.identity.name, r.sid));
        if (r.identity.color) { sess.style.background = r.identity.color.bg; sess.style.color = r.identity.color.fg; }
        row.appendChild(sess);
      }
      box.appendChild(row);
    });
    out.push(box);
  }
  empty.replaceChildren(...out);
}

// ── boot ──────────────────────────────────────────────────────────────────────────────────────────
applyTheme(document, loadSettings());
installSettingsSync();
onExternalSettingsChange((s) => applyTheme(document, s));

// the chip's resolver: what the relay told us about the sid, else the kernel's 8-character stub
setFileViewIdentity((id) => identities.get(id) ?? hostStub(id));
// the shared viewer, with this pane's own relay contract (see the header); saves and the GitHub link ride
// this socket's poster, and the file browser (a viewer dir-link, or its own rows) opens here too
initFileView((m) => vscodeApi?.postMessage(m), (m) => {
  openHere(m.path, typeof m.sid === "string" ? m.sid : null, asIdentity(m.identity), typeof m.todoId === "string" ? m.todoId : null);
});
initFileBrowse((m) => vscodeApi?.postMessage(m), {
  shellRestore: false,   // the pane stays up; browseClosed is the FEED's restore (see the header)
  onRelay: (m) => {
    const sid = typeof m.sid === "string" ? m.sid : null;
    const id = asIdentity(m.identity);
    if (sid && id) identities.set(sid, id);   // so a file picked from the listing names its session
    openFileBrowse(m.path || ".", sid);
  },
});

// re-open rows: delegated on the stable #files-empty (actions.ts), so a repaint mid-click still lands
(() => {
  const empty = document.getElementById("files-empty");
  if (!empty) return;
  delegate(empty, {
    open: (x) => { const r = recent[Number(x.dataset.i)]; if (r) openHere(r.path, r.sid, r.identity); },
  });
})();
// the viewer's or the browser's element coming and going IS the open/close event: one observer on the body
// covers every path (the relays, a recent row, the browser's rows and its "‹ Files" back, ✕, Escape, the
// Reload replace). The CLOSE edge, nothing left up, is also told to the shell ({romp:"filesViewerClosed"}): on
// a phone the relay switched tabs to show this pane, and the shell puts the person back on the tab the click
// came from (a no-op on desktop, where the column simply shows its recent list again). Edge, not every
// mutation: the Reload replace and an open-over-open remove and re-add within one batch, so the viewer is
// still up when the observer runs; and a viewer closing back onto the listing beneath it ("‹ Files") is no
// edge either, since the browser is still up.
let viewerUp = surfaceUp();
function onBodyChange(): void {
  paint();
  const up = surfaceUp();
  if (viewerUp && !up && window.parent !== window) window.parent.postMessage({ romp: "filesViewerClosed" }, "*");
  viewerUp = up;
}
new MutationObserver(onBodyChange).observe(document.body, { childList: true });

paint();
vscodeApi?.postMessage({ type: "ready" });   // lifts the shim's hold: this socket carries keepalives and op replies only

export {};   // module scope
