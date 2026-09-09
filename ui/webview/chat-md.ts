// The renderer for the user's OWN words in the chat.
//
// Two marked configurations render the chat, and they must agree on everything except line breaks:
//   - the shared `marked` singleton (md-config.ts applyMdConfig, called by render.ts, file-view.ts and
//     anchor-map.ts) — `breaks: false`: assistant output is real markdown, where a single newline is a soft wrap
//     and a paragraph break takes a blank line;
//   - `userMarked` below — `breaks: true`: what the user typed is not authored markdown. Shift+Enter in the
//     composer means "new line", and the bubble must show the line the person made (the user 2026-09-06:
//     a multi-line message ran together into one paragraph once it reached the chat). marked's `breaks`
//     option turns each newline inside a paragraph into <br> and touches nothing else — fenced code keeps
//     its literal newlines, lists stay lists, a blank line is still a paragraph break.
// Both take the SAME extensions, `mdExtensions` in md-config.ts (the one grammar since Slice 4 of
// plans/markdown-viewer.md; the list lived in this module under its own name before), so a user message with math or
// strikethrough renders exactly as it did before — only its newlines are kept. Pure (no DOM): the executed tests
// import it directly. Sanitizing is the caller's job: render.ts's userMd() runs the output through the same
// DOMPurify profile md() uses before it ever reaches innerHTML; the math fill rides that sanitize as a post-pass
// md-config.ts registers, so no caller renders it by hand.
import { Marked } from "marked";
import { mdExtensions } from "./md-config";

// The user-text instance: the shared grammar with hard line breaks. Its own `Marked` so the singleton's
// `breaks: false` — every assistant message — is untouched.
export const userMarked = new Marked({ gfm: true, breaks: true }, ...mdExtensions);

/** marked's HTML for the user's own typed text: newlines kept as <br>, otherwise the shared grammar.
 *  UNSANITIZED: render.ts's userMd() is the only caller that reaches innerHTML; it purifies first, and the
 *  sanitize renders the math placeholders (the post-pass md-config.ts registers) on the sanitized DOM. */
export function userMdHtml(src: string): string {
  return userMarked.parse(src) as string;
}
