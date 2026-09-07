// Where a click on a FILE or a FOLDER opens: one ladder, two callers (render.ts openPath and openBrowse),
// pure and DOM-free so the table runs for real in tests (file-view.test.ts, browse-route.test.ts).
//
// The inputs, all read at CLICK time by the caller:
//   web        the page is served over http(s): the dashboard or standalone /chat. Off in VS Code, whose
//              webview cannot reach the kernel origin; the editor has its own explorer and opener.
//   pane       the gear's "File links open in" (settings.fileLinkPane): "chat" (the default), "feed" or
//              "pane"; a foreign stored value reads as the default.
//   framed     window.parent !== window: a shell exists to relay to. Standalone /chat has no shell and no
//              other pane, so everything opens in place there.
//   filesOpen  the shell's Files-pane bit (render.ts panesOn.files, cached from the shell's own broadcast):
//              the pane is ON SCREEN: a desktop column toggled on, or the tab showing on a phone.
//
// A verdict names the TARGET: "pane" is the Files pane (the shell brings a closed one forward; the click is
// the gesture), "feed" is the feed pane (brought forward for the duration and put back), "here" is this
// document, "editor" is the VS Code host's own opener.

export type FileRoute = "feed" | "pane" | "here";
export type BrowseRoute = FileRoute | "editor";

/** A FILE link (render.ts openPath). An open Files pane takes the click whatever the setting says (the user
 *  2026-09-04: the pane being open IS the intent; a file that opened as a modal over the chat while the pane
 *  sat empty was the bug). Closed, the setting's own table; "here" is the viewer as a modal over the pane
 *  that was clicked, upstream's design and the default. */
export function fileLinkRoute(pane: unknown, framed: boolean, filesOpen: boolean): FileRoute {
  if (!framed) return "here";
  if (filesOpen) return "pane";
  return pane === "feed" || pane === "pane" ? pane : "here";
}

/** A FOLDER click (the statusline's directory, the System-context row, a tab menu's Browse files; render.ts
 *  openBrowse) walks the SAME ladder as a file, with one difference: a framed chat never browses in place. The
 *  viewer's "here" is a modal the person dismisses once the file is read; a listing is a place to stay and
 *  navigate, and the dashboard has two surfaces built for it, the Files pane's column and the feed pane's
 *  browser (the shell's browseFiles relay), so the default lands on the feed, never over the transcript
 *  (the user 2026-09-06, who wanted the folder at the bottom of the chat to open in the Files pane or over
 *  the feed, not over the chat). "here" survives only unframed: standalone /chat, where neither surface
 *  exists. In VS Code the folder link keeps the configured opener (asFolderLink's openFolder act). */
export function browseRoute(web: boolean, pane: unknown, framed: boolean, filesOpen: boolean): BrowseRoute {
  if (!web) return "editor";
  const r = fileLinkRoute(pane, framed, filesOpen);
  return framed && r === "here" ? "feed" : r;
}
