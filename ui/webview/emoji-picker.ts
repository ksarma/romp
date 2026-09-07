// The tab menu's emoji picker (2026-09-07): the pure half, importable by the tests. render.ts's
// showEmojiPrompt builds the dialog from these: the search filter, the Recent row's storage shape, the
// section list the grid is drawn from, and the keyboard model that moves focus through it. Nothing here
// touches the DOM or the kernel; the kernel's validator (kernel/kernel.py _emoji_check) stays the one
// judge of what a tab accepts, and the dialog shows its answer, so this module never decides whether a
// string is an emoji. It only knows the curated list and how to move through it.
import { EMOJI_CATEGORIES, EmojiCategory, EmojiEntry } from "./emoji-data";

/** Where the Recent row lives: one localStorage key per browser profile (a VS Code webview has its own),
 *  a JSON array of emoji strings, most recent first. Namespaced like romp:files-recent and romp:color-echo. */
export const EMOJI_RECENT_KEY = "romp:emoji-recent";
export const EMOJI_RECENT_MAX = 16;
/** Cells per grid row. styles.css's .emoji-grid repeats the same count; the keyboard model needs the
 *  number to move a row up or down, so it is declared once here and the sheet mirrors it. */
export const EMOJI_GRID_COLS = 8;

/** Two strings for the same emoji: equal once every emoji presentation selector (U+FE0F) is dropped. The
 *  list carries fully-qualified forms only, but the kernel's validator stores what it is given, so a tab
 *  set through `romp emoji`, the set_emoji tool or the footer field can wear a keycap without the selector,
 *  the rainbow flag without it, or a presentation emoji with a redundant one; and many apps copy a
 *  text-default base bare (U+2764 alone for the red heart). Every comparison in this module goes through
 *  these, and render.ts's .cur ring does too. No two list entries collide after the strip
 *  (emoji-data.test.ts checks), so the key is as exact as the list needs. */
export function emojiKey(s: string): string { return s.replace(/\uFE0F/g, ""); }
export function sameEmoji(a: string, b: string): boolean { return emojiKey(a) === emojiKey(b); }

/** The stored Recent list, tolerant of junk: a corrupt value costs the row, never the dialog. Strings only,
 *  deduped, capped. */
export function parseRecentEmoji(raw: string | null): string[] {
  if (!raw) return [];
  try {
    const v = JSON.parse(raw);
    if (!Array.isArray(v)) return [];
    const out: string[] = [];
    for (const e of v) {
      if (typeof e !== "string" || !e || out.some((o) => sameEmoji(o, e))) continue;
      out.push(e);
      if (out.length >= EMOJI_RECENT_MAX) break;
    }
    return out;
  } catch { return []; }
}

/** Most recent first, one row per emoji (picking again moves it to the front), capped. */
export function rememberEmoji(list: readonly string[], emoji: string, max = EMOJI_RECENT_MAX): string[] {
  if (!emoji) return list.slice(0, max);
  return [emoji, ...list.filter((e) => !sameEmoji(e, emoji))].slice(0, max);
}

/** The curated name of an emoji, for a Recent cell's tooltip; undefined for one the list does not carry
 *  (a typed or pasted one that landed). Selector-insensitive: a tab wearing the keycap without U+FE0F
 *  still gets the list's name. */
export function emojiName(emoji: string, cats: readonly EmojiCategory[] = EMOJI_CATEGORIES): string | undefined {
  for (const c of cats) for (const it of c.items) if (sameEmoji(it[0], emoji)) return it[1];
  return undefined;
}

const words = (s: string): string[] => s.toLowerCase().split(/[\s-]+/).filter(Boolean);

/** Search: every typed word must begin some word of the name or the keywords (case-insensitive, no
 *  network, no fuzziness), or the query is the emoji itself (pasted into the search box, with or without
 *  its U+FE0F selector). Ranked so that a name starting with the query comes first, then a name whose
 *  later word starts with it, then a keyword hit; ties keep category order. An empty query matches
 *  nothing: the caller shows the categories instead. So does a query with no word in it (hyphens only:
 *  "-", "- -"), which would otherwise match everything, since every() over no words is true, and hand
 *  Enter in the search box the first emoji of the list. */
export function filterEmoji(query: string, cats: readonly EmojiCategory[] = EMOJI_CATEGORIES): EmojiEntry[] {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  const toks = words(q);
  if (!toks.length) return [];
  const scored: Array<[number, EmojiEntry]> = [];
  for (const c of cats) {
    for (const it of c.items) {
      const [emoji, name, keywords] = it;
      if (sameEmoji(emoji, q)) { scored.push([-1, it]); continue; }
      const nameWords = words(name);
      const all = nameWords.concat(words(keywords));
      if (!toks.every((t) => all.some((w) => w.startsWith(t)))) continue;
      const score = name.toLowerCase().startsWith(q) ? 0 : nameWords.some((w) => w.startsWith(toks[0])) ? 1 : 2;
      scored.push([score, it]);
    }
  }
  return scored.sort((a, b) => a[0] - b[0]).map((s) => s[1]);   // Array.prototype.sort is stable
}

export interface GridSection { id: string; label: string; cells: readonly EmojiEntry[] }

/** The sections the grid draws, top to bottom. Searching replaces everything with one Results section
 *  (which may be empty: the caller says so and points at the free-text field); otherwise the Recent row
 *  (only when there is something in it) leads the categories. A recent emoji the list does not know
 *  (typed or pasted, then accepted) is shown with itself as its name. Any non-blank query is a search,
 *  a hyphen-only one included: it draws an EMPTY Results section rather than the categories, so the
 *  dialog's Enter-picks-the-top-hit has nothing to pick (the categories would put the first emoji of
 *  the list, or of the Recent row, under it). */
export function gridSections(query: string, recents: readonly string[],
                             cats: readonly EmojiCategory[] = EMOJI_CATEGORIES): GridSection[] {
  if (query.trim()) return [{ id: "results", label: "Results", cells: filterEmoji(query, cats) }];
  const out: GridSection[] = [];
  if (recents.length) {
    out.push({ id: "recent", label: "Recent",
               cells: recents.map((e): EmojiEntry => [e, emojiName(e, cats) || e, ""]) });
  }
  for (const c of cats) out.push({ id: c.id, label: c.label, cells: c.items });
  return out;
}

export interface GridPos { section: number; index: number }

const GRID_KEYS = new Set(["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End"]);

/** Where focus goes from `pos` on `key`, over sections of the given lengths laid out `cols` per row.
 *  Left/Right run along the reading order and cross into the neighboring section at a row's end;
 *  Up/Down keep the column and cross a section boundary onto the nearest row of the next one (clamped
 *  to its last cell when that row is short); Down from a section's last row that is not yet at the
 *  section's last cell goes to that last cell first. Home and End are the whole grid's first and last
 *  cell. Empty sections are skipped; the edges hold (no wrap-around). null when `key` is not a grid
 *  key, so Enter and Space fall through to the focused button's own activation. */
export function moveInGrid(lengths: readonly number[], pos: GridPos, key: string,
                           cols = EMOJI_GRID_COLS): GridPos | null {
  if (!GRID_KEYS.has(key)) return null;
  const n = lengths.length;
  const nextSec = (s: number) => { for (let i = s + 1; i < n; i++) if (lengths[i] > 0) return i; return -1; };
  const prevSec = (s: number) => { for (let i = s - 1; i >= 0; i--) if (lengths[i] > 0) return i; return -1; };
  const { section: s, index: i } = pos;
  const len = lengths[s] || 0;
  if (key === "Home") { const f = nextSec(-1); return f < 0 ? pos : { section: f, index: 0 }; }
  if (key === "End") { const l = prevSec(n); return l < 0 ? pos : { section: l, index: lengths[l] - 1 }; }
  if (key === "ArrowRight") {
    if (i + 1 < len) return { section: s, index: i + 1 };
    const t = nextSec(s); return t < 0 ? pos : { section: t, index: 0 };
  }
  if (key === "ArrowLeft") {
    if (i > 0) return { section: s, index: i - 1 };
    const t = prevSec(s); return t < 0 ? pos : { section: t, index: lengths[t] - 1 };
  }
  const col = i % cols;
  if (key === "ArrowDown") {
    if (i + cols < len) return { section: s, index: i + cols };
    if (Math.floor(i / cols) < Math.floor((len - 1) / cols)) return { section: s, index: len - 1 };
    const t = nextSec(s); return t < 0 ? pos : { section: t, index: Math.min(col, lengths[t] - 1) };
  }
  // ArrowUp
  if (i - cols >= 0) return { section: s, index: i - cols };
  const t = prevSec(s);
  if (t < 0) return pos;
  const lastRow = Math.floor((lengths[t] - 1) / cols) * cols;
  return { section: t, index: Math.min(lastRow + col, lengths[t] - 1) };
}
