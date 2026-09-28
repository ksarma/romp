// WHO POSTED A WINDOW MESSAGE. A pane's window `message` listener hears every window that can post to it, not only
// romp's own. windowSender names the sender of one message, so a listener can act on a message only from the senders
// that legitimately post it:
//   dispatch  no source and no origin: an event this document's own script dispatched (the pane shim's and
//             federation.js's kernel frames, each a new MessageEvent("message", { data }), whose origin is the empty
//             string), or a handler called directly with a plain object. A post from another window names that
//             window's origin, and it keeps it when it arrives with no source, so a sourceless message that carries
//             an origin is judged by the origin rules below, never counted as this document's own.
//   self      this window posted it: a same-document post, such as the file viewer mounted in the chat's document.
//   embedder  this window's parent posted it: the romp shell (same origin, since the kernel serves its pages with
//             frame-ancestors 'self').
//   peer      another window on this page's location.origin, the origin of its URL: a second chat column, or the
//             VS Code webview host, which is never window.parent (VS Code's script in the webview's frame replaces it
//             with the frame itself; older releases delete it) and posts from its own window on the webview's origin.
//             Such a window can reach this document's script, so its posts carry no authority it lacks; on a sandboxed
//             page served over http it cannot (the document's origin is opaque, location.origin still the URL's).
//   foreign   anything else, such as a sandboxed iframe (its origin is "null", which never matches, even when this
//             page's location.origin is "null", as for a URL whose origin is opaque, such as about:srcdoc or data:).
// A listener that acts on a message from a foreign sender acts for a page romp does not control; see the chat's frame
// handler in render.ts, which ignores every message from a foreign sender.
export type WindowSender = "self" | "embedder" | "dispatch" | "peer" | "foreign";

export function windowSender(e: { source?: unknown; origin?: unknown } | null | undefined,
                             w: { parent?: unknown; location?: { origin?: string } } = window): WindowSender {
  if (!e) return "foreign";
  const src = e.source;
  if (src === null || src === undefined) {
    if (e.origin === undefined || e.origin === null || e.origin === "") return "dispatch";
  } else {
    if (src === w) return "self";
    if (w.parent && w.parent !== w && src === w.parent) return "embedder";
  }
  const own = w.location && w.location.origin;
  if (typeof own === "string" && own !== "null" && e.origin === own) return "peer";
  return "foreign";
}
