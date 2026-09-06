// A SECTION'S SNAPSHOT (the user 2026-09-06): the pane the transcript normally fills shows one compact
// row per session in a tab-strip section — name, emoji, state pip, what it is doing now in the user's
// terms, when it last did anything, and whether it needs the user — so a group can be surveyed at a
// glance and any of its sessions opened from there. It shows when a section header is clicked (which
// also folds or opens the section) and stays until a session is picked; a section holding the tab being
// read folds like any other now, its header standing in for the hidden tab (tab-groups.ts planStrip).
//
// PURE: the model is a function from what the chat client already holds per session — the session
// frame (name, emoji, color, status, userTodos, the events tail) and its ledger (the same summary /
// current task / recent tops the tab hover tip and the Outline pane render, plus the postal working
// note the kernel puts on the ledger) — to plain rows, with NO clock in it: the last-activity time is
// an epoch the renderer formats, so a push that changed nothing yields the SAME object (snapshotModel
// returns `prev`) and the renderer rebuilds nothing — the rule that views move only on new
// information, applied to a list that is rebuilt from every push. render.ts paints it; the shapes
// below are the minimal "Like" views of render.ts's types (the tab-state.ts idiom), so the rule runs
// in node tests without a DOM.
import { tabStateClass, type TabStateLike } from "./tab-state";

export interface SnapStatusLike extends TabStateLike { sinceEpoch?: number | null }
export interface SnapEventLike { kind?: string; md?: string; text?: string; ts?: string; t?: number }
export interface SnapColor { bg: string; fg: string }
export interface SnapSessionLike {
  name?: string; emoji?: string; color?: SnapColor | null; status?: SnapStatusLike | null;
  userTodos?: ReadonlyArray<unknown> | null; events?: ReadonlyArray<SnapEventLike> | null;
}
export interface SnapLedgerLike {
  summary?: string | null; workingNote?: string | null;
  tree?: ReadonlyArray<{ text?: string; current?: boolean }> | null;
  recent?: ReadonlyArray<{ text?: string; t?: number }> | null;
}
export interface SnapSectionLike { name: string | null; color: string; ids: readonly string[] }

/** The pip a row wears — the tab's own colors by the tab's own rule (tab-state.ts), plus the two
 *  states the strip paints on the chip rather than the tab: `waiting` (idle, but background work it
 *  dispatched is still running — the Outline's await-green) and `unknown` (no session frame yet). An
 *  idle or ready session wears none, as in the Outline. */
export type SnapPip = "working" | "blocked" | "awaiting" | "retrying" | "compacting" | "waiting" | "unknown" | "";

export interface SnapRow {
  id: string;
  name: string;
  emoji: string;
  color: SnapColor | null;
  pip: SnapPip;
  /** the state in words — the row's spoken label and its title; "" for idle/ready */
  state: string;
  /** on YOU: blocked on an API error only you can clear, a live permission or picker prompt, or an open
   *  user todo — the tab's alarm-red cases and its ⚑ */
  needsYou: boolean;
  /** waiting on something that is not you: dispatched background work */
  waiting: boolean;
  todos: number;
  /** what it is doing now, in the user's terms: the working note, else the current task, else the
   *  ledger summary, else the most recent top task; "" when nothing is known */
  now: string;
  /** when it last did anything (epoch s): the newest event in the tail, else the state's start */
  lastT: number | null;
  /** the last assistant message, for the hover */
  lastMsg: string;
  closed: boolean;
  /** no session frame yet (a placeholder tab): name and color from the strip's meta alone */
  loading: boolean;
}

export interface SnapModel { name: string; color: string; rows: SnapRow[] }

const NOW_MAX = 200;      // the now line: one row, the CSS ellipsis does the rest; the cap bounds the model
const MSG_MAX = 400;      // the hover excerpt

const oneLine = (s: unknown, max: number): string => {
  const t = String(s ?? "").replace(/\s+/g, " ").trim();
  return t.length > max ? t.slice(0, max - 1) + "…" : t;
};

function eventEpoch(ev: SnapEventLike): number | null {
  if (ev.ts) { const ms = Date.parse(ev.ts); if (!isNaN(ms)) return Math.floor(ms / 1000); }
  if (ev.kind === "postal-service" && ev.t != null) return Math.floor(ev.t);
  return null;
}

/** THE now line: the session's own claim first (the postal working note — what it says it owns), then
 *  the judges' current task, then the archiver's headline, then the most recent top task. */
export function nowLine(lg: SnapLedgerLike | null | undefined): string {
  if (!lg) return "";
  if (lg.workingNote && oneLine(lg.workingNote, NOW_MAX)) return oneLine(lg.workingNote, NOW_MAX);
  const cur = (lg.tree || []).find((n) => n.current && oneLine(n.text, NOW_MAX));
  if (cur) return oneLine(cur.text, NOW_MAX);
  if (lg.summary && oneLine(lg.summary, NOW_MAX)) return oneLine(lg.summary, NOW_MAX);
  const r = (lg.recent || []).find((x) => oneLine(x.text, NOW_MAX));
  return r ? oneLine(r.text, NOW_MAX) : "";
}

/** The newest event's time, else the state's start. The tail is in transcript order, so the walk is
 *  from the end; an event with no time (a live-stream atom) is skipped, not zero. */
export function lastActivity(s: SnapSessionLike): number | null {
  const evs = s.events || [];
  for (let i = evs.length - 1; i >= 0; i--) { const t = eventEpoch(evs[i]); if (t) return t; }
  return s.status?.sinceEpoch ? Math.floor(s.status.sinceEpoch) : null;
}

/** The last assistant message in the tail, one line, for the hover. */
export function lastMessage(s: SnapSessionLike): string {
  const evs = s.events || [];
  for (let i = evs.length - 1; i >= 0; i--) {
    const e = evs[i];
    if (e.kind === "assistant") { const t = oneLine(e.md ?? e.text, MSG_MAX); if (t) return t; }
  }
  return "";
}

/** The pip and the state word for a status — the tab's rule for the colors, the statusline's words. */
export function rowState(st: SnapStatusLike | null | undefined): { pip: SnapPip; state: string; needsYou: boolean; waiting: boolean; closed: boolean } {
  if (!st) return { pip: "unknown", state: "", needsYou: false, waiting: false, closed: false };
  const cls = tabStateClass(st);
  const s = st.state || "";
  if (cls === "tab-blocked") return { pip: "blocked", state: "needs you — stopped on an API error", needsYou: true, waiting: false, closed: false };
  if (cls === "tab-awaiting") return { pip: "awaiting", state: "needs you — waiting on your answer", needsYou: true, waiting: false, closed: false };
  if (cls === "tab-retrying") return { pip: "retrying", state: "API error, retrying on its own", needsYou: false, waiting: false, closed: false };
  if (cls === "tab-compacting") return { pip: "compacting", state: s === "clearing" ? "clearing" : "compacting", needsYou: false, waiting: false, closed: false };
  if (cls === "tab-closed") return { pip: "", state: "closed", needsYou: false, waiting: false, closed: true };
  if (cls === "tab-working") return { pip: "working", state: "working", needsYou: false, waiting: false, closed: false };
  if (s === "awaitingBg") return { pip: "waiting", state: "waiting on background work", needsYou: false, waiting: true, closed: false };
  if (s === "interrupting") return { pip: "", state: "interrupting", needsYou: false, waiting: false, closed: false };
  if (s === "opening") return { pip: "unknown", state: "opening", needsYou: false, waiting: false, closed: false };
  return { pip: "", state: "", needsYou: false, waiting: false, closed: false };
}

export function snapshotRow(id: string, s: SnapSessionLike | null | undefined, lg: SnapLedgerLike | null | undefined): SnapRow {
  const st = rowState(s?.status);
  const todos = Array.isArray(s?.userTodos) ? s!.userTodos!.length : 0;
  return {
    id,
    name: String(s?.name || "").trim() || "(unnamed)",
    emoji: s?.emoji || "",
    color: s?.color && s.color.bg && s.color.fg ? { bg: s.color.bg, fg: s.color.fg } : null,
    pip: s ? st.pip : "unknown",
    state: st.state,
    needsYou: st.needsYou || todos > 0,
    waiting: st.waiting,
    todos,
    now: nowLine(lg),
    lastT: s ? lastActivity(s) : null,
    lastMsg: s ? lastMessage(s) : "",
    closed: st.closed,
    loading: !s,
  };
}

const sameRow = (a: SnapRow, b: SnapRow): boolean =>
  a.id === b.id && a.name === b.name && a.emoji === b.emoji && a.pip === b.pip && a.state === b.state
  && a.needsYou === b.needsYou && a.waiting === b.waiting && a.todos === b.todos && a.now === b.now
  && a.lastT === b.lastT && a.lastMsg === b.lastMsg && a.closed === b.closed && a.loading === b.loading
  && (a.color === b.color || (!!a.color && !!b.color && a.color.bg === b.color.bg && a.color.fg === b.color.fg));

export function sameModel(a: SnapModel | null | undefined, b: SnapModel): boolean {
  return !!a && a.name === b.name && a.color === b.color && a.rows.length === b.rows.length
    && a.rows.every((r, i) => sameRow(r, b.rows[i]));
}

/** The snapshot of one section: a row per member in strip order. `session`/`ledger` look up what the
 *  client holds (a null session = a placeholder tab). Returns `prev` ITSELF when nothing a row shows
 *  has changed, so the caller can skip the rebuild (the same-object contract the tests pin). */
export function snapshotModel(sec: SnapSectionLike, session: (id: string) => SnapSessionLike | null | undefined,
                              ledger: (id: string) => SnapLedgerLike | null | undefined, prev: SnapModel | null): SnapModel {
  const next: SnapModel = { name: sec.name ?? "", color: sec.color || "",
                            rows: sec.ids.map((id) => snapshotRow(id, session(id), ledger(id))) };
  return prev && sameModel(prev, next) ? prev : next;
}

/** The heading's words: the section's name and its count, and the spoken label for the region. */
export function snapshotHeading(name: string, n: number): { count: string; label: string } {
  const count = `${n} session${n === 1 ? "" : "s"}`;
  return { count, label: `${name}: ${count}; click one to open it` };
}

/** A row's spoken label — name, state, what it needs, what it is doing — and its hover title. */
export function rowWords(r: SnapRow): { label: string; title: string } {
  const parts = [r.name];
  if (r.loading) parts.push("opening");
  else if (r.state) parts.push(r.state);
  if (r.todos) parts.push(`${r.todos} thing${r.todos === 1 ? "" : "s"} it needs from you`);
  if (r.now) parts.push(r.now);
  const title = (r.lastMsg ? `Last message: ${r.lastMsg}` : r.loading ? "opening…" : "No messages yet.") + "\nClick to open this session.";
  return { label: parts.join(" — "), title };
}
