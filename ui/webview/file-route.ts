// Where a click on a FILE or a FOLDER opens: one ladder, two callers (render.ts openPath for a file link,
// openBrowse for a folder), pure and DOM-free so the table runs for real in tests (file-route.test.ts,
// browse-route.test.ts). The caller reads every input at CLICK time:
//   web        the page is served over http(s): the dashboard or standalone /chat. Off in VS Code, whose
//              webview cannot reach the kernel origin; the editor has its own explorer and opener.
//   pane       the gear's "File links open in" (settings.fileLinkPane): "chat" (the default), "feed" or
//              "pane"; a foreign stored value reads as the default.
//   framed     window.parent !== window: a shell exists to relay to. Standalone /chat has no shell and no
//              other pane, so everything opens in place there.
//   filesOpen  the shell's Files-pane bit (render.ts panesOn.files, cached from the shell's own broadcast):
//              the pane is ON SCREEN, a desktop column toggled on or the tab showing on a phone.
//   filesAvail the shell's word that the Files control exists (render.ts panesAvail.files, the same broadcast):
//              the gear's Files row (Settings, General, Panes) is on (off by default since T317b). Off, there is no pane to
//              bring forward, so a click that would have gone there opens here (T317).
// A verdict names the TARGET: "pane" is the Files pane (the shell brings a closed one forward; the click is
// the gesture), "feed" is the feed pane (brought forward for the duration and put back), "here" is this
// document, the viewer or the file browser as a modal over the pane that was clicked, and "editor" (a folder
// in VS Code) is the host editor's own opener.

export type FileRoute = "feed" | "pane" | "here";
export type BrowseRoute = FileRoute | "editor";

/** A FILE link. An OPEN Files pane takes the click whatever the setting says: the pane being open IS the
 *  intent, and a file that opened as a modal over the chat while the pane sat there empty was the bug.
 *  Closed, the setting decides; "here" is the default. A pane the shell does not have (filesAvail off, T317)
 *  is never a verdict: the open bit is ignored and a setting naming it falls to "here" (the folder ladder
 *  then substitutes "feed", browseRoute below). */
export function fileLinkRoute(pane: unknown, framed: boolean, filesOpen: boolean, filesAvail: boolean = true): FileRoute {
  if (!framed) return "here";
  if (filesOpen && filesAvail) return "pane";
  return pane === "feed" ? "feed" : pane === "pane" && filesAvail ? "pane" : "here";
}

/** A FOLDER click (the folder shown under the chat, the system context card's Directory row, a tab menu's
 *  Browse files, a chat-hosted viewer's directory link; render.ts openBrowse) walks the SAME ladder as a
 *  file link, with one difference: a framed chat never browses in place. The viewer's "here" is a modal the
 *  person dismisses once the file is read; a listing is a place to stay and navigate, and the dashboard has
 *  two surfaces built for it, the Files pane's column and the feed pane's browser (the shell's browseFiles
 *  relay), so the default lands on the feed, never over the transcript (the user 2026-09-06, who wanted the
 *  folder at the bottom of the chat to open in the Files pane or over the feed, not over the chat). "here"
 *  survives only unframed: standalone /chat, where neither surface exists. Web only: in VS Code the folder
 *  link keeps the editor's own opener (asFolderLink's openFolder act), so the ladder is never asked. */
export function browseRoute(web: boolean, pane: unknown, framed: boolean, filesOpen: boolean, filesAvail: boolean = true): BrowseRoute {
  if (!web) return "editor";
  const r = fileLinkRoute(pane, framed, filesOpen, filesAvail);
  return framed && r === "here" ? "feed" : r;
}
