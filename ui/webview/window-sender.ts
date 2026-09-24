// WHO POSTED A WINDOW MESSAGE. A pane's window `message` listener hears every window that can post to it, not only
// romp's own. windowSender names the sender of one message, so a listener can act on a message only from the senders
// that legitimately post it:
//   dispatch  no source: an event this document's own script dispatched (the pane shim's and federation.js's kernel
//             frames), or a handler called directly with a plain object. A real postMessage always carries a source.
//   self      this window posted it: a same-document post, such as the file viewer mounted in the chat's document.
//   embedder  this window's parent posted it: the romp shell (same origin, since the kernel serves its pages with
//             frame-ancestors 'self').
//   peer      another window on this document's own origin, such as a second chat column, or the VS Code webview host.
//             VS Code's script in the webview's frame replaces window.parent with the frame itself (older releases
//             delete it), so window.parent never refers to the host that forwards the extension's messages; the host
//             posts from its own window on the webview's origin. A same-origin window can already reach this
//             document's script directly, so its posts carry no authority it lacks.
//   foreign   anything else, such as a sandboxed iframe (its origin is "null", which never matches, even when this
//             document's own origin is "null").
// A listener that acts on a message from a foreign sender acts for a page romp does not control; see the chat's frame
// handler in render.ts, which ignores every message from a foreign sender.
export type WindowSender = "self" | "embedder" | "dispatch" | "peer" | "foreign";

export function windowSender(e: { source?: unknown; origin?: unknown } | null | undefined,
                             w: { parent?: unknown; location?: { origin?: string } } = window): WindowSender {
  if (!e) return "foreign";
  const src = e.source;
  if (src === null || src === undefined) return "dispatch";
  if (src === w) return "self";
  if (w.parent && w.parent !== w && src === w.parent) return "embedder";
  const own = w.location && w.location.origin;
  if (typeof own === "string" && own !== "null" && e.origin === own) return "peer";
  return "foreign";
}
