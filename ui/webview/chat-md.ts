// The chat's two marked instances: a reply's, and the user's OWN words'.
//
// Two marked configurations render the chat, and they must agree on everything except line breaks:
//   - `chatMarked` below, `breaks: false`: assistant output is real markdown, where a single newline is a soft wrap
//     and a paragraph break takes a blank line. It carries the shared singleton's configuration (md-config.ts
//     applyMdConfig, called by render.ts, file-view.ts and anchor-map.ts) plus the chat's own pathAwareEmphasis,
//     which is why a reply parses here and not on the singleton since 2026-09-19: the chat links the file paths in
//     its rendered text, and an emphasis pair opened or closed inside a path cut the token the walk looks for
//     (`/a-_b/c_/d.md` rendered `/a-<em>b/c</em>/d.md`; md-config.ts says the rest). The viewer, the hover preview
//     and the anchor map stay on the singleton, whose rendering of a note is GitHub's; the feed's notice cards are
//     on neither: they render on a bare instance of their own (feed.ts noticeMarked, gfm with hard breaks and no
//     extensions), which takes nothing from this module or md-config.ts and links no paths;
//   - `userMarked` below — `breaks: true`: what the user typed is not authored markdown. Shift+Enter in the
//     composer means "new line", and the bubble must show the line the person made (the user 2026-09-06:
//     a multi-line message ran together into one paragraph once it reached the chat). marked's `breaks`
//     option turns each newline inside a paragraph into <br> and touches nothing else — fenced code keeps
//     its literal newlines, lists stay lists, a blank line is still a paragraph break.
// Both take the SAME extensions, `mdExtensions` in md-config.ts (the one grammar since Slice 4 of
// plans/markdown-viewer.md; the list lived in this module under its own name before) plus pathAwareEmphasis, so a
// user message with math or strikethrough renders exactly as it did before, a path in it is linked as a reply's is,
// and only its newlines differ. Pure (no DOM): the executed tests import it directly. Sanitizing is the caller's job:
// render.ts's md() and userMd() run the output through the same sanitizer (sanitizeMd, md-sanitize.ts) before it
// ever reaches innerHTML; the math fill rides that sanitize as a post-pass md-config.ts registers, so no caller
// renders it by hand.
import { Marked } from "marked";
import { mdExtensions, pathAwareEmphasis } from "./md-config";

// The reply instance: the singleton's grammar, soft wraps, and emphasis that never cuts a file path.
export const chatMarked = new Marked({ gfm: true, breaks: false }, ...mdExtensions, pathAwareEmphasis);
// The user-text instance: the same grammar with hard line breaks. Its own `Marked` so the singleton's
// `breaks: false` is untouched.
export const userMarked = new Marked({ gfm: true, breaks: true }, ...mdExtensions, pathAwareEmphasis);

/** marked's HTML for a reply (and every other assistant-authored surface render.ts's md() renders): the chat's
 *  grammar with soft wraps. UNSANITIZED, as userMdHtml is: render.ts's md() purifies before innerHTML. */
export function chatMdHtml(src: string): string {
  return chatMarked.parse(src) as string;
}
/** marked's HTML for the user's own typed text: newlines kept as <br>, otherwise the shared grammar.
 *  UNSANITIZED: render.ts's userMd() is the only caller that reaches innerHTML; it purifies first, and the
 *  sanitize renders the math placeholders (the post-pass md-config.ts registers) on the sanitized DOM. */
export function userMdHtml(src: string): string {
  return userMarked.parse(src) as string;
}
