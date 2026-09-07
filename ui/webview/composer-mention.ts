// @-mention autocomplete for the composer (the user 2026-09-07): typing "@ro" in the message box offers
// the live sessions whose names match, and a pick puts the plain name in the text the way an agent
// addresses a peer with its mail tools ("@web ", or "@host:web " for a session on another kernel, the
// form postal takes to break a name tie). This module is the PURE half, so it runs for real under
// node --test: the trigger rule, the matcher, the insertion arithmetic, the keyboard model and the
// transcript segmenter. render.ts owns the DOM: the card, its rows, the composer wiring, the chip.
import { hostPrefix } from "./host-prefix";

export interface MentionCandidate {
  id: string;        // the session id as the webview holds it ("host:uuid" for a federated session)
  name: string;      // the display name as the webview holds it ("host:name" for a federated session)
  emoji?: string;
  color?: { bg: string; fg: string } | null;
}

/** The "@query" token the caret ends: where its "@" sits and the text after it. */
export interface MentionQuery { start: number; query: string; }

export const MENTION_MAX_ROWS = 8;

/** The "@query" token the caret sits at the end of, or null. The "@" must OPEN a word: at the start
 *  of the box or after whitespace, so an email address (a@b.example) or a path (/tmp/@x) never
 *  triggers. The query is the run of characters after the "@" up to the caret, with no whitespace and
 *  no second "@", at least one character long; and the caret must END the word, so a caret placed back
 *  inside "@ro|mp" opens nothing. */
export function mentionQuery(text: string, caret: number): MentionQuery | null {
  if (typeof text !== "string" || caret < 0 || caret > text.length) return null;
  if (caret < text.length && !/\s/.test(text[caret])) return null;
  const m = /(^|\s)@([^\s@]+)$/.exec(text.slice(0, caret));
  if (!m) return null;
  return { start: caret - m[2].length - 1, query: m[2] };
}

/** The name without the "host:" the viewer prefixed onto a federated session (host-prefix.ts). */
export function mentionBareName(c: MentionCandidate): string {
  const p = hostPrefix(c.name, c.id);
  return p ? p.rest : c.name;
}

/** Rank the roster against the query, case-insensitively: a prefix of the name first, then a prefix
 *  of the whole "host:name" (a federated session found by its host), then a substring anywhere;
 *  alphabetical by name within a rank. The session being written to is left out (a message to it
 *  never needs its own name), and the list stops at MENTION_MAX_ROWS. An empty query matches nothing:
 *  the card opens on "@" plus a character, never on the bare "@". */
export function matchMentions(query: string, roster: readonly MentionCandidate[], selfId: string | null | undefined): MentionCandidate[] {
  const q = (query || "").toLowerCase();
  if (!q) return [];
  const scored: { c: MentionCandidate; rank: number; key: string; remote: number }[] = [];
  for (const c of roster) {
    if (!c || !c.name || (selfId && c.id === selfId)) continue;
    const bareName = mentionBareName(c);
    const bare = bareName.toLowerCase();
    const full = c.name.toLowerCase();
    const rank = bare.startsWith(q) ? 3 : full.startsWith(q) ? 2 : full.includes(q) ? 1 : 0;
    if (rank) scored.push({ c, rank, key: bare, remote: bareName === c.name ? 0 : 1 });
  }
  // same rank and same bare name (a local "web" and a remote "host:web"): the local one first
  scored.sort((a, b) => b.rank - a.rank || a.key.localeCompare(b.key) || a.remote - b.remote || a.c.name.localeCompare(b.c.name));
  return scored.slice(0, MENTION_MAX_ROWS).map((x) => x.c);
}

/** The text a pick inserts: "@" + the name as an agent's mail tools take it (the bare name for a
 *  session on this kernel, "host:name" for a federated one, which is exactly the display name the
 *  webview holds), then one space so typing continues. Plain text, no markup: the receiving agent
 *  reads the name literally. */
export function mentionToken(c: MentionCandidate): string {
  return "@" + c.name + " ";
}

/** Replace the typed "@query" (from its "@" to the caret) with the token; the caret lands after it. */
export function insertMention(text: string, at: MentionQuery, caret: number, token: string): { text: string; caret: number } {
  const head = text.slice(0, at.start);
  return { text: head + token + text.slice(caret), caret: head.length + token.length };
}

export type MentionKeyAction =
  | { kind: "move"; sel: number }
  | { kind: "pick"; sel: number }
  | { kind: "close" }
  | null;

/** What a key does while the card is open, given the highlighted row and the row count. Up and down
 *  move the highlight and wrap; Enter and Tab pick the highlighted row; Escape closes without
 *  inserting. Null means the key is not the card's: the composer handles it as usual. With the card
 *  closed nothing is consumed, so Enter keeps sending; and a modifier (Shift+Enter for a newline,
 *  Cmd/Ctrl+Enter to stage) keeps its own meaning even while the card is up. */
export function mentionKeyAction(key: string, open: boolean, sel: number, count: number, modifier = false): MentionKeyAction {
  if (!open || count <= 0 || modifier) return null;
  if (key === "ArrowDown") return { kind: "move", sel: (sel + 1) % count };
  if (key === "ArrowUp") return { kind: "move", sel: (sel - 1 + count) % count };
  if (key === "Enter" || key === "Tab") return { kind: "pick", sel: Math.min(Math.max(sel, 0), count - 1) };
  if (key === "Escape") return { kind: "close" };
  return null;
}

export interface MentionSegment<T> { text: string; hit?: T; }

/** Split a run of plain text at the "@name" tokens that name a live session: `lookup` answers the
 *  session for a word, or null. The same word-boundary rule as the trigger, with trailing sentence
 *  punctuation left outside the token ("ask @web." names web). A word that names nothing stays text,
 *  and so does an email address. The segments concatenate back to the input exactly. */
export function mentionSegments<T>(text: string, lookup: (word: string) => T | null | undefined): MentionSegment<T>[] {
  const out: MentionSegment<T>[] = [];
  const re = /(^|\s)@([^\s@]+)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text))) {
    const word = m[2].replace(/[.,;:!?)\]}'"]+$/, "");
    const hit = word ? lookup(word) : null;
    if (!hit) continue;
    const start = m.index + m[1].length;
    if (start > last) out.push({ text: text.slice(last, start) });
    out.push({ text: "@" + word, hit });
    last = start + 1 + word.length;
    re.lastIndex = last;   // rescan from the token's end, so stripped punctuation stays plain text
  }
  if (last < text.length) out.push({ text: text.slice(last) });
  return out;
}
