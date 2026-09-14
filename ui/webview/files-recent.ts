// The Files pane's recent-files list (files.ts): the pure half, importable by the tests. When nothing
// is open the pane lists the files most recently open there as re-open links, so a thread dropped
// yesterday costs one click to pick up. Stored per browser (localStorage), most recent first, one row
// per path + session, capped; the identity a row carries is whatever the shell's relay handed over when
// the file was opened, so the row's session chip re-renders without a session list of the pane's own.
// Since Slice 6 of plans/markdown-viewer.md a row also carries the reader's PLACE in the file, the record
// the viewer hands its host when the file is left (file-view.ts RememberedPlace, through initFileView's
// `onLeave`): the top block's source span and pixel offset, the view, the file's mtime, the numeric
// scrollTop and, for a Rendered read, the open folds by ordinal, never a word of the file. The pane hands it back
// on every open of the FILE here, the row's click or any other (files.ts openHere, openFileView's `place`), so the note
// returns to where it was read: the rows are per path + session, the file a row names is the viewer's rule (latestPlace,
// below), and of the rows for one file the later record seats. The place is used, never shown: the row looks as it did.
export interface RecentIdentity { name: string; color: { bg: string; fg: string } | null }
/** The viewer's RememberedPlace (file-view.ts), spelled here so the pane's pure half imports nothing of the viewer:
 *  the same eight fields, by structure. `start`/`end`: the top block's source span; `top`: its top edge's offset from
 *  the body's top in px (negative when it starts above the edge); `atTop`: the body stood at its very top; `view`: the
 *  view it was read in; `mtimeNs`: the file's mtime string when read; `scrollTop`: the body's, the fallback when the
 *  span is no block of the file any more; `t`: when; `folds`, for a Rendered read: the ordinals in document order of the
 *  `<details>` the reader had open (the review's round 3; absent for a Raw read, a note with no fold and a record an older
 *  store wrote).
 *  No text field, ever: this goes to localStorage. */
export interface RecentPlace { start: number; end: number; top: number; atTop: boolean; view: "rendered" | "raw"; mtimeNs: string; scrollTop: number; t: number; folds?: number[] }
export interface RecentFile { path: string; sid: string | null; identity: RecentIdentity | null; t: number; place: RecentPlace | null }
export const RECENT_KEY = "romp:files-recent";
export const RECENT_MAX = 8;

/** A relayed or stored identity, validated to the chip's shape. Anything else is no identity: the chip is
 *  looked up, never invented (file-view.ts's rule), and a resolver miss falls to the kernel's stub there. */
export function asIdentity(x: unknown): RecentIdentity | null {
  if (!x || typeof x !== "object") return null;
  const o = x as { name?: unknown; color?: unknown };
  if (typeof o.name !== "string" || !o.name) return null;
  const c = o.color as { bg?: unknown; fg?: unknown } | null | undefined;
  const color = c && typeof c === "object" && typeof c.bg === "string" && typeof c.fg === "string" ? { bg: c.bg, fg: c.fg } : null;
  return { name: o.name, color };
}

const finite = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
/** A stored place, validated field by field to the viewer's record: a span of non-negative offsets in order, finite
 *  pixel offsets (the scrollTop never negative), a boolean, one of the two views, a string mtime and a number for the
 *  time, and, when present, the open folds as a list of non-negative integers (absent is fine: a Raw read, a note with no
 *  fold, an older store's record). Anything else is NO place (null): the row it rode on is kept, since a path is worth listing whatever
 *  happened to its place, and the viewer then opens the file at its top as it always did. Never widened: a field
 *  this pane does not know is dropped, so nothing but these nine ever reaches the store. */
export function asPlace(x: unknown): RecentPlace | null {
  if (!x || typeof x !== "object") return null;
  const o = x as Record<string, unknown>;
  if (!finite(o.start) || !finite(o.end) || o.start < 0 || o.end < o.start) return null;
  if (!finite(o.top) || !finite(o.scrollTop) || o.scrollTop < 0 || !finite(o.t)) return null;
  if (typeof o.atTop !== "boolean" || typeof o.mtimeNs !== "string") return null;
  if (o.view !== "rendered" && o.view !== "raw") return null;
  const place: RecentPlace = { start: o.start, end: o.end, top: o.top, atTop: o.atTop, view: o.view, mtimeNs: o.mtimeNs, scrollTop: o.scrollTop, t: o.t };
  if (o.folds !== undefined) {
    if (!Array.isArray(o.folds) || !o.folds.every((k) => typeof k === "number" && Number.isInteger(k) && k >= 0)) return null;
    place.folds = (o.folds as number[]).slice();
  }
  return place;
}

/** The stored list, tolerant of junk: a corrupt entry costs the list, never the pane; a corrupt place costs the place, never the row. */
export function parseRecent(raw: string | null): RecentFile[] {
  if (!raw) return [];
  try {
    const v = JSON.parse(raw);
    if (!Array.isArray(v)) return [];
    const out: RecentFile[] = [];
    for (const e of v) {
      if (!e || typeof e !== "object" || typeof e.path !== "string" || !e.path) continue;
      out.push({ path: e.path, sid: typeof e.sid === "string" && e.sid ? e.sid : null,
                 identity: asIdentity(e.identity), t: typeof e.t === "number" ? e.t : 0, place: asPlace(e.place) });
    }
    return out.slice(0, RECENT_MAX);
  } catch { return []; }
}

/** Most recent first, one row per path + session (a re-open moves the row up and refreshes its identity), capped.
 *  A re-open that brings no place keeps the row's: the viewer hands the pane the place of the file it LEAVES (onLeave)
 *  before the re-open's own row is written, so an entry built with none must not erase what was just stored (an open
 *  of the same file over itself, the shell's relay for a path already in the list). An entry that brings one wins. */
export function rememberRecent(list: RecentFile[], entry: RecentFile, max = RECENT_MAX): RecentFile[] {
  const same = (r: RecentFile) => r.path === entry.path && r.sid === entry.sid;
  const kept = entry.place ?? list.find(same)?.place ?? null;
  const rest = list.filter((r) => !same(r));
  return [{ ...entry, place: kept }, ...rest].slice(0, max);
}

/** The list with `place` written on the row for `path` + `sid`, the other rows untouched; no such row, the list as it
 *  is (a place is stored for a file the pane opened, which always has a row; nothing is invented for one it did not). */
export function placeRecent(list: RecentFile[], path: string, sid: string | null, place: RecentPlace | null): RecentFile[] {
  return list.map((r) => (r.path === path && r.sid === sid ? { ...r, place } : r));
}

/** The record to seat at an open: the LATEST (by `t`) among the rows `sameFile` admits, null when none of them holds one.
 *  The rows are per path + session while the viewer's in-page memory is per FILE (file-view.ts placeKey: an absolute or `~`
 *  path is one file for every session of this kernel that names it, a session attached from another kernel, whose sid
 *  carries its host, reads that kernel's disk, so its key carries the host too and the two kernels' files are two files (the
 *  PR review's round 1); a relative path one per session, since the kernel resolves it against the session's cwd), so
 *  files.ts admits the rows whose placeKey is the open's. Two sessions' rows for one absolute path then seat the same
 *  record, the later, as the in-page memory seats the file's last leave before a page reload; with the open's own row alone
 *  read, the same row landed at the file's latest place before a reload and at its session's older place after one (the
 *  Slice 6 review, round 5). A tie keeps the first row admitted, the most recent. */
export function latestPlace(list: RecentFile[], sameFile: (r: RecentFile) => boolean): RecentPlace | null {
  let best: RecentPlace | null = null;
  for (const r of list) if (r.place && sameFile(r) && (!best || r.place.t > best.t)) best = r.place;
  return best;
}
