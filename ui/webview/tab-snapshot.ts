// A SECTION AT A GLANCE: the pane the transcript normally fills shows one compact row per session in a
// tab-strip section (name, emoji, state pip, what it is doing now in the user's terms, when it last did
// anything, and whether it needs the user), so a group can be surveyed at a glance and any of its sessions
// opened from there. It shows when a section header is clicked (which also folds or opens the section) and
// stays until a session is picked; a section holding the tab being read folds like any other, its header
// standing in for the hidden tab (tab-groups.ts planStrip).
//
// PURE: the model is a function from what the chat client already holds per session (the session frame:
// name, emoji, color, status, userTodos, the events tail; and its ledger: the same summary / current task /
// recent tops the tab hover tip renders, plus two fields the kernel puts on the ledger for this view: the
// postal working note, and whether the feed files one of the session's cards under needs-you) to plain
// rows, with NO clock in it: the last-activity time is an epoch the renderer formats, so a push that
// changed nothing yields the SAME object (snapshotModel returns `prev`) and the renderer rebuilds nothing.
// render.ts paints it; the shapes below are the minimal "Like" views of render.ts's types (the tab-state.ts
// idiom), so the rule runs in node tests without a DOM.
import { tabStateClass, sectionPip, sectionPipMembers, type TabStateLike, type SectionPip, type RingId } from "./tab-state";
import { chipWords, type ChipStatusLike, type ChipWords } from "./status-chip";
import { stripInline } from "./docreview";

/** The tab's state fields, the chip's awaiting fields (kind, count, rows, peers: what an awaiting session waits on), the clock. */
export interface SnapStatusLike extends TabStateLike, ChipStatusLike { sinceEpoch?: number | null }
export interface SnapEventLike { kind?: string; md?: string; text?: string; ts?: string; t?: number }
export interface SnapColor { bg: string; fg: string }
export interface SnapSessionLike {
  name?: string; emoji?: string; color?: SnapColor | null; status?: SnapStatusLike | null;
  userTodos?: ReadonlyArray<unknown> | null; events?: ReadonlyArray<SnapEventLike> | null;
}
export interface SnapLedgerLike {
  summary?: string | null; workingNote?: string | null;
  /** the feed's verdict, from the kernel's last feed build: true when one of this session's cards is filed
   *  under needs-you there (the column the feed's Blocked list is), false when none is, null when no feed
   *  has been built since the kernel started (the first push cycle) */
  needsInput?: boolean | null;
  tree?: ReadonlyArray<{ text?: string; current?: boolean }> | null;
  recent?: ReadonlyArray<{ text?: string; t?: number }> | null;
}
/** `hides`: the members hidden inside the section (tab-groups.ts StripHead.hides, the user 2026-09-08); the
 *  pane lists them under its Hidden fold, with a Show button each. Absent or empty: nothing hidden. */
export interface SnapSectionLike { name: string | null; color: string; ids: readonly string[]; hides?: readonly string[] }
/** The strip's meta for a tab whose session frame has not landed (render.ts tabMeta): its name and color alone. */
export interface SnapMetaLike { name?: string; color?: SnapColor | null }

/** The pip a row wears: the tab's own colors by the tab's own rule (tab-state.ts), plus the two states the
 *  strip paints on the chip rather than the tab: `waiting` (idle, but background work it dispatched is
 *  still running) and `unknown` (no session frame yet). An idle or ready session wears none. */
export type SnapPip = "working" | "blocked" | "awaiting" | "retrying" | "compacting" | "waiting" | "unknown" | "";

export interface SnapRow {
  id: string;
  name: string;
  emoji: string;
  color: SnapColor | null;
  pip: SnapPip;
  /** the state in words: the row's spoken label and its title; "" for idle/ready */
  state: string;
  /** on YOU, by the feed's rule: a card of this session filed under needs-you in the kernel's last feed
   *  build (the same column the feed's Blocked list shows: a question the agent asked and stopped on, a
   *  live prompt, an API error only you can clear); plus the tab's own alarm-red cases, which the feed
   *  build can trail by one push, and an open user todo, the tab's ⚑ */
  needsYou: boolean;
  /** waiting on something that is not you: dispatched background work */
  waiting: boolean;
  todos: number;
  /** the state chip the row wears beside the name, or null for none: the SHARED status chip's words and class
   *  (status-chip.ts chipWords), the same the bar under the transcript shows for the session you are reading.
   *  Only the states a row says in words: on you (needsInput's "Blocked", the feed's column word; the tab's own
   *  "API error" when its rule sees an API error only you can clear) and awaiting background work ("Awaiting 3 agents", "Awaiting watch", the
   *  one peer's name). Working, ready and the rest ride the pip alone: a blank beside the name means alive and
   *  quiet, the Sessions pane's rule (T322b, the user 2026-09-10). */
  chip: ChipWords | null;
  /** what it is doing now, in the user's terms: the judges' current task, else the archiver's headline,
   *  else the most recent top task; "" when nothing is known */
  now: string;
  /** the session's own note of what it is working on (the postal working note: its claim to a branch and
   *  files, written for peer sessions), one line; "" when it has published none. A quieter second line of
   *  the row, under the now line, never in its place. */
  note: string;
  /** when it last did anything (epoch s): the newest event in the tail, else the state's start */
  lastT: number | null;
  /** the last assistant message, for the hover */
  lastMsg: string;
  closed: boolean;
  /** no session frame yet (a placeholder tab): name and color from the strip's meta alone */
  loading: boolean;
  /** hidden inside its section (the user 2026-09-08): no tab on the strip while the section is open; the
   *  pane lists the row under its Hidden fold, with a Show button where a shown row has Hide */
  hidden: boolean;
}

export interface SnapModel { name: string; color: string; rows: SnapRow[] }

/** The hidden members' needs-you count, for the Hidden fold's chip: what a hidden session must not lose. */
export function hiddenNeeds(rows: readonly SnapRow[]): number {
  return rows.filter((r) => r.hidden && r.needsYou).length;
}

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

/** THE now line, in the user's terms: the judges' current task, then the archiver's headline, then the
 *  most recent top task. The working note is NOT a rung here: it is the session's claim to a branch and
 *  files, written for peer sessions, so it rides the row as its own line (noteLine) and never stands in
 *  for what the session is accomplishing. */
export function nowLine(lg: SnapLedgerLike | null | undefined): string {
  if (!lg) return "";
  const cur = (lg.tree || []).find((n) => n.current && oneLine(n.text, NOW_MAX));
  if (cur) return oneLine(cur.text, NOW_MAX);
  if (lg.summary && oneLine(lg.summary, NOW_MAX)) return oneLine(lg.summary, NOW_MAX);
  const r = (lg.recent || []).find((x) => oneLine(x.text, NOW_MAX));
  return r ? oneLine(r.text, NOW_MAX) : "";
}

/** The row's second line: the postal working note, one line, "" when none. */
export function noteLine(lg: SnapLedgerLike | null | undefined): string {
  return lg ? oneLine(lg.workingNote, NOW_MAX) : "";
}

/** The newest event's time, else the state's start. The tail is in transcript order, so the walk is
 *  from the end; an event with no time (a live-stream atom) is skipped, not zero. sinceEpoch is in
 *  MILLISECONDS everywhere (the kernel's since_ms, the client's own Date.now() placeholders), while the
 *  row's lastT is epoch SECONDS like the event times: passed through unconverted it would read as a time
 *  far in the future and every empty-tail row would say "0s ago". */
export function lastActivity(s: SnapSessionLike): number | null {
  const evs = s.events || [];
  for (let i = evs.length - 1; i >= 0; i--) { const t = eventEpoch(evs[i]); if (t) return t; }
  return s.status?.sinceEpoch ? Math.floor(s.status.sinceEpoch / 1000) : null;
}

const ENTITIES: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', "#39": "'", apos: "'", nbsp: " " };

/** A markdown message as plain words on one line, for a title attribute (a native tooltip renders text,
 *  so the source's markers would show as typed): HTML comments go whole, fence lines go, each remaining
 *  line loses its block and inline markers (docreview.ts stripInline, the file viewer's rule), the lines
 *  join with spaces, and the join loses what the viewer keeps on purpose and the transcript never shows
 *  as typed: HTML tags (the chat renders a reply through marked and DOMPurify, so <details>, <summary>,
 *  <br>, <b> paint as structure, never as text; each becomes a space), the entities that stand for a
 *  character once the tags are gone (&amp; &lt; &gt; &quot; &#39; &nbsp;), and underscore emphasis at
 *  word edges (_x_, __x__). snake_case keeps its underscores, as in the viewer; code spans are not
 *  parsed, so a tag typed inside backticks goes with the rest. */
export function plainText(md: string, max: number): string {
  const lines = md.replace(/<!--[\s\S]*?-->/g, " ").replace(/\r\n?/g, "\n").split("\n").filter((l) => !/^\s*(```|~~~)/.test(l));
  const joined = lines.map(stripInline).join(" ")
    .replace(/<\/?[A-Za-z][^<>]*>/g, " ")
    .replace(/&(amp|lt|gt|quot|#39|apos|nbsp);/g, (_, e: string) => ENTITIES[e])
    .replace(/(^|[^\w])_{1,2}([^_\s](?:[^_]*?[^_\s])?)_{1,2}(?=[^\w]|$)/g, "$1$2");
  return oneLine(joined, max);
}

/** The last assistant message in the tail, one line of plain text, for the hover. */
export function lastMessage(s: SnapSessionLike): string {
  const evs = s.events || [];
  for (let i = evs.length - 1; i >= 0; i--) {
    const e = evs[i];
    if (e.kind === "assistant") { const t = plainText(String(e.md ?? e.text ?? ""), MSG_MAX); if (t) return t; }
  }
  return "";
}

/** The pip and the state word for a status: the tab's rule for the colors, the statusline's words. */
export function rowState(st: SnapStatusLike | null | undefined): { pip: SnapPip; state: string; needsYou: boolean; waiting: boolean; closed: boolean } {
  if (!st) return { pip: "unknown", state: "", needsYou: false, waiting: false, closed: false };
  const cls = tabStateClass(st);
  const s = st.state || "";
  if (cls === "tab-blocked") return { pip: "blocked", state: "needs you: stopped on an API error", needsYou: true, waiting: false, closed: false };
  if (cls === "tab-awaiting") return { pip: "awaiting", state: "needs you: waiting on your answer", needsYou: true, waiting: false, closed: false };
  if (cls === "tab-retrying") return { pip: "retrying", state: "API error, retrying on its own", needsYou: false, waiting: false, closed: false };
  if (cls === "tab-compacting") return { pip: "compacting", state: s === "clearing" ? "clearing" : "compacting", needsYou: false, waiting: false, closed: false };
  if (cls === "tab-closed") return { pip: "", state: "closed", needsYou: false, waiting: false, closed: true };
  if (cls === "tab-working") return { pip: "working", state: "working", needsYou: false, waiting: false, closed: false };
  if (s === "awaitingBg") return { pip: "waiting", state: chipWords(st).text, needsYou: false, waiting: true, closed: false };   // the chip's own words ("Awaiting 3 agents"), spoken as shown (T322b)
  if (s === "interrupting") return { pip: "", state: "interrupting", needsYou: false, waiting: false, closed: false };
  if (s === "opening") return { pip: "unknown", state: "opening", needsYou: false, waiting: false, closed: false };
  return { pip: "", state: "", needsYou: false, waiting: false, closed: false };
}

/** A member's name as its tab shows it; "(unnamed)" for a blank one (the tab-state.ts rule). */
const memberName = (s: { name?: string } | null | undefined): string => String(s?.name || "").trim() || "(unnamed)";

/** ON YOU, one judgment for every surface that shows a session or stands in for it (round 1 of the tabhide
 *  review, 2026-09-08): the feed's verdict for it (lg.needsInput: a card of its filed under needs-you in the
 *  kernel's last feed build) or the tab's own alarm-red cases (rowState: a live prompt, an API error only you
 *  can clear), which the feed build can trail by one push. The row's chip and the Hidden fold's count read it
 *  (snapshotRow, with an open user todo besides), and so does the header's stand-in pip over the members with
 *  no tab on the strip (standInPip), so a hidden idle session the feed files under needs-you is red on the
 *  strip, as the Hide button's hover promises. */
export function onYou(st: SnapStatusLike | null | undefined, lg: SnapLedgerLike | null | undefined): boolean {
  return lg?.needsInput === true || rowState(st).needsYou;
}

/** What the header's stand-in pip reads per member: the session frame and its ledger, either absent. */
export interface StandInLike { session: SnapSessionLike | null | undefined; ledger: SnapLedgerLike | null | undefined }

/** THE HEADER'S STAND-IN PIP over the members with no tab on the strip (render.ts makeGroupHead: folded, the
 *  unpinned members; open, the members hidden inside the section): the tab's own rule (tab-state.ts sectionPip:
 *  red for a member blocked on you or waiting for you, yellow for one with something waiting on you (the ask
 *  ring, 2026-09-13: a fold must not hide it), gold for one working, amber for one retrying an API error on its
 *  own) with onYou folded in, so a member the feed files under needs-you is red as well, and the names its
 *  phrase is about (sectionPipTitle), in strip order. `on` is the ring SWITCHES the members' tabs wear
 *  (tab-widgets.ts ringSwitch over the Tab widgets settings, 2026-09-14), handed to the tab's rule and gating
 *  the fold-in's red (the needs-you ring's kind), so a fold never shows a colour no unfolded tab would. Null
 *  when nothing is happening. */
export function standInPip(members: ReadonlyArray<StandInLike>, on: (id: RingId) => boolean = () => true): { kind: SectionPip; names: string[] } | null {
  const names = on("ring-needs-you") ? members.filter((m) => onYou(m.session?.status, m.ledger)).map((m) => memberName(m.session)) : [];
  if (names.length) return { kind: "blocked", names };
  const kind = sectionPip(members.map((m) => m.session?.status), on);
  return kind ? { kind, names: sectionPipMembers(kind, members.map((m) => m.session), on) } : null;
}

/** One row. `s` is the session frame (null for a placeholder tab, whose frame has not landed); `meta` the
 *  strip's meta for it (name and color), read only when the frame is absent, so a loading row still wears
 *  the tab's name and color; `hidden`, the row is hidden inside its section (the user 2026-09-08). */
export function snapshotRow(id: string, s: SnapSessionLike | null | undefined, lg: SnapLedgerLike | null | undefined,
                            hidden = false, meta?: SnapMetaLike | null): SnapRow {
  const st = rowState(s?.status);
  const src: SnapMetaLike | null | undefined = s ?? meta;
  const todos = Array.isArray(s?.userTodos) ? s!.userTodos!.length : 0;
  // NEEDS YOU is the feed's call: the tab's rule (tab-state.ts) knows only the live states the chip carries
  // (a permission or picker prompt, an on-you API error), so a judge-filed block on a session that went idle
  // after asking would show a plain idle row here while the feed shows a red card. lg.needsInput is that
  // column, per session, from the kernel's last feed build (build_session); the tab's own cases stay as a
  // floor because the feed build trails the chip by one push. The one judgment is onYou (the header's
  // stand-in pip reads the same); the row adds an open user todo, the tab's ⚑.
  const feedBlock = lg?.needsInput === true;
  // the chip: on you → "API error" when the tab's own rule sees an API error only you can clear (tab-blocked: the
  // flags ride beside the state; a flagless API error is the kernel's transient, auto-retried one, and with a feed-filed
  // block it reads "Blocked" like every other on-you row), else the feed's column word ("Blocked", needsInput's chip);
  // awaiting → the awaiting chip's words from the status's kind, count, rows and peers; otherwise none
  const chip = (feedBlock || st.needsYou) ? chipWords({ state: s?.status && tabStateClass(s.status) === "tab-blocked" ? "blocked" : "needsInput" })
    : st.waiting ? chipWords(s?.status || {}) : null;
  return {
    id,
    name: memberName(src),
    emoji: s?.emoji || "",
    color: src?.color && src.color.bg && src.color.fg ? { bg: src.color.bg, fg: src.color.fg } : null,
    pip: s ? st.pip : "unknown",
    state: st.state,   // the tab's own phrase; a feed-filed block on a quiet session has none, its chip ("Blocked") is the word (T322b)
    needsYou: feedBlock || st.needsYou || todos > 0,
    waiting: st.waiting,
    todos,
    chip,
    now: nowLine(lg),
    note: noteLine(lg),
    lastT: s ? lastActivity(s) : null,
    lastMsg: s ? lastMessage(s) : "",
    closed: st.closed,
    loading: !s,
    hidden,
  };
}

const sameChip = (a: ChipWords | null, b: ChipWords | null): boolean =>
  a === b || (!!a && !!b && a.state === b.state && a.text === b.text
    && (a.peer === b.peer || (!!a.peer && !!b.peer && a.peer.name === b.peer.name && (a.peer.host || "") === (b.peer.host || "")
                              && (a.peer.color?.bg || "") === (b.peer.color?.bg || ""))));
const sameRow = (a: SnapRow, b: SnapRow): boolean =>
  a.id === b.id && a.name === b.name && a.emoji === b.emoji && a.pip === b.pip && a.state === b.state
  && a.needsYou === b.needsYou && a.waiting === b.waiting && sameChip(a.chip, b.chip) && a.todos === b.todos && a.now === b.now
  && a.note === b.note && a.hidden === b.hidden
  && a.lastT === b.lastT && a.lastMsg === b.lastMsg && a.closed === b.closed && a.loading === b.loading
  && (a.color === b.color || (!!a.color && !!b.color && a.color.bg === b.color.bg && a.color.fg === b.color.fg));

export function sameModel(a: SnapModel | null | undefined, b: SnapModel): boolean {
  return !!a && a.name === b.name && a.color === b.color && a.rows.length === b.rows.length
    && a.rows.every((r, i) => sameRow(r, b.rows[i]));
}

/** The rows of one section: one per member in strip order. `session`/`ledger`/`meta` look up what the
 *  client holds (a null session = a placeholder tab, whose row takes its name and color from `meta`).
 *  Returns `prev` ITSELF when nothing a row shows has changed, so the caller can skip the rebuild (the
 *  same-object contract the tests pin). */
export function snapshotModel(sec: SnapSectionLike, session: (id: string) => SnapSessionLike | null | undefined,
                              ledger: (id: string) => SnapLedgerLike | null | undefined, prev: SnapModel | null,
                              meta?: (id: string) => SnapMetaLike | null | undefined): SnapModel {
  const hides = sec.hides || [];
  const next: SnapModel = { name: sec.name ?? "", color: sec.color || "",
                            rows: sec.ids.map((id) => snapshotRow(id, session(id), ledger(id), hides.includes(id), meta ? meta(id) : null)) };
  return prev && sameModel(prev, next) ? prev : next;
}

/** The heading's words: the count (and how many are hidden, when any are), and the spoken label for the region,
 *  "Overview of <tag>: N sessions", the words the heading shows (T322: "Overview of", the tag's chip, the count). */
export function snapshotHeading(name: string, n: number, hidden = 0): { count: string; label: string } {
  const count = `${n} session${n === 1 ? "" : "s"}` + (hidden > 0 ? `, ${hidden} hidden` : "");
  return { count, label: `Overview of ${name}: ${count}; click one to open it` };
}

/** The Hidden fold's words (the user 2026-09-08): its text, the needs-you chip over the hidden members (""
 *  when none needs you: the chip is the one thing a hide must not put away), the button's spoken label and
 *  its hover. `open`: the fold is showing its rows, so the click folds them. */
export function hiddenFoldWords(n: number, needs: number, open: boolean): { text: string; needs: string; label: string; title: string } {
  const text = `Hidden (${n})`;
  const chip = needs === 0 ? "" : needs === 1 ? "1 needs you" : `${needs} need you`;
  const click = open ? "click to fold them" : "click to see them";
  const who = `${n} session${n === 1 ? "" : "s"} hidden from the strip while this group is open`;
  return { text, needs: chip, label: `Hidden, ${who}${chip ? `, ${chip}` : ""}; ${click}`,
           title: `${who}${chip ? `; ${chip}` : ""}; ${click}` };
}

/** The Hide or Show button's words for a row: `text` its face, `label` what a reader hears, `title` the hover.
 *  Hide speaks of THIS section: the flag is per section, as a pin is, and the row is offered in the section's
 *  own view. */
export function actWords(r: SnapRow, section: string): { text: string; label: string; title: string } {
  if (r.hidden) return { text: "Show", label: `Show ${r.name} on the strip again`, title: `Put ${r.name}'s tab back on the strip` };
  return { text: "Hide", label: `Hide ${r.name} from the strip while ${section} is open`,
           title: `Hide ${r.name}'s tab from the strip while ${section} is open; it stays in ${section}, listed under Hidden here, and its needs-you still shows on the header` };
}

/** A row's spoken label (name, the chip's words, the state phrase, what it is doing, its own note) and its hover
 *  title. The CHIP's words are spoken whenever the row wears one ("Blocked", "API error", "Awaiting 3 agents"),
 *  once, where the painted chip sits beside the pip: an awaiting row's state phrase IS the chip's words, so it is
 *  not repeated; an on-you row's tab phrase ("needs you: waiting on your answer") follows the word. The button's
 *  aria-label replaces its content for a reader, so a word only the chip carried would never be spoken, and a
 *  word the chip does not show would be heard and not seen (T322b: the label says what is shown). A hidden row
 *  says so right after its name, and an open user todo count follows the state phrase (the Hidden fold and the
 *  tab's flag, the user 2026-09-08). */
export function rowWords(r: SnapRow): { label: string; title: string } {
  const parts = [r.name];
  if (r.hidden) parts.push("hidden from the strip");   // the row sits under the Hidden fold; a reader hears why (2026-09-08)
  const stateWord = r.loading ? "opening" : r.state;
  if (r.chip && r.chip.text && stateWord !== r.chip.text) parts.push(r.chip.text);
  if (stateWord) parts.push(stateWord);
  if (r.todos) parts.push(`${r.todos} thing${r.todos === 1 ? "" : "s"} it needs from you`);
  if (r.now) parts.push(r.now);
  if (r.note) parts.push(`its note: ${r.note}`);
  const title = (r.lastMsg ? `Last message: ${r.lastMsg}` : r.loading ? "opening…" : "No messages yet.") + "\nClick to open this session.";
  return { label: parts.join("; "), title };
}
