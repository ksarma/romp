// THE TAB STRIP'S STATE → CLASS RULE, in one place. The tab itself wears it (render.ts renderTabs),
// and a folded section header's member-derived summary pip (tab groups, 2026-09-04) reads the SAME rule
// — the header once classed any "blocked" member red, while the strip distinguishes an on-you block
// from a transient API error that auto-retries (amber, needs no attention), so a folded group showed a
// red "waiting on you" pip over a tab that, unfolded, was amber. The header is a LABEL (the user
// 2026-09-06): it wears no state class of its own; the pip and the user-todo flag below are the two
// member-derived marks a fold must not hide. Pure and DOM-free so it runs in node tests; the Status
// interface in render.ts is a superset of the shape read here.
export interface TabStateLike {
  state?: string;
  apiTooLong?: boolean;
  apiSpendLimit?: boolean;
  apiModelLimit?: boolean;
  apiAuthErr?: boolean;
  apiRefusal?: boolean;
  needsYou?: boolean | null;   // the FEED's per-session needs-you verdict (build_session's status; null before the first feed build)
}

/** The tab's state class for a status, or "" for a state with no tab treatment (ready/idle). */
export function tabStateClass(s: TabStateLike | null | undefined): string {
  const st = s?.state || "";
  if (st === "working") return "tab-working";
  // "blocked" is an API error. An on-YOU one — "prompt is too long" (compact), a monthly spend cap
  // (raise it, the user 2026-07-14), a spent model allowance (switch model, the user 2026-08-01), an
  // auth failure, or a safeguards refusal (rewrite the ask, the user 2026-08-15) — is alarm-red
  // dashed; a TRANSIENT API error is auto-retrying and needs no attention → the amber retrying
  // treatment, not red (the user 2026-06-29).
  if (st === "blocked") return (s!.apiTooLong || s!.apiSpendLimit || s!.apiModelLimit || s!.apiAuthErr || s!.apiRefusal) ? "tab-blocked" : "tab-retrying";
  if (st === "needsInput" || st === "awaiting") return "tab-awaiting";   // legacy name = an older remote kernel
  if (st === "retrying") return "tab-retrying";                          // amber: soft-blocked on an API auto-retry
  if (st === "compacting" || st === "clearing") return "tab-compacting"; // both: a context op in flight
  if (st === "closed") return "tab-closed";                              // dead session: read-only, struck-through label
  return "";
}

/** THE RINGS a tab can wear, in PRECEDENCE order (the rings-as-widgets change, 2026-09-14): each is a widget of the
 *  tab-widget registry (tab-widgets.ts, slot "ring") with its own switch in the settings' Tab widgets section, and a
 *  tab wears ONE at a time, the first in this order whose switch is on and whose test holds. Red over yellow over
 *  amber: a live prompt or an API stop only you can clear says "needs you now"; a card of the session's under
 *  needs-you says something is waiting on you, whatever else the session is doing; a transient API retry needs no
 *  attention at all. This is the pure, DOM-free twin of the registry's composition (composeTabRing), read by the
 *  folded header's pip below, so the strip and the pip cannot disagree; tab-widgets.test.ts pins the two equal over
 *  every synthetic status and every switch set. */
export type RingId = "ring-needs-you" | "ring-waiting-on-you" | "ring-retrying";
export const RING_ORDER: readonly RingId[] = ["ring-needs-you", "ring-waiting-on-you", "ring-retrying"];
export const RING_TEST: Record<RingId, (s: TabStateLike | null | undefined) => boolean> = {
  // the RED ring: a LIVE prompt (a permission or picker prompt, tab-awaiting), or an API stop only you can clear
  // (tab-blocked: prompt too long, a spend cap, a spent model allowance, an auth failure, a refusal)
  "ring-needs-you": (s) => { const c = tabStateClass(s); return c === "tab-awaiting" || c === "tab-blocked"; },
  // the YELLOW ring (the ask ring, 2026-09-13): the feed filed a card of this session under needs-you (status.needsYou,
  // the kernel's per-session read of the feed's needs_input column in build_session, the same verdict the
  // section-at-a-glance row's chip and the feed's Blocked list speak, so the three can never disagree) and the tab is
  // not dead. The session may be idle, awaiting background work or still WORKING while the card waits, and the ring
  // shows in every one of those, composed with the working dot rather than replacing it: a session with something
  // waiting on you should grab attention without a click, even while it goes on working. Only TRUE is a verdict: null
  // (no feed build yet) and false are the same nothing, as is an older kernel's absent field. The test itself no
  // longer stands down under the red states; the composition's first-on-ring rule does, so with the red ring switched
  // off a stopped session with a card wears the yellow, which is true of that tab.
  "ring-waiting-on-you": (s) => s?.needsYou === true && tabStateClass(s) !== "tab-closed",
  // the AMBER ring: the state retrying, or blocked with none of the on-you flags (the API is backing off and retrying
  // on its own)
  "ring-retrying": (s) => tabStateClass(s) === "tab-retrying",
};
/** The ring a tab wears for a status: the first of RING_ORDER whose switch (`on`; every ring on by default) is on and
 *  whose test holds; null for none. */
export function tabRingId(s: TabStateLike | null | undefined, on: (id: RingId) => boolean = () => true): RingId | null {
  for (const id of RING_ORDER) if (on(id) && RING_TEST[id](s)) return id;
  return null;
}

export type SectionPip = "blocked" | "ask" | "retrying" | "working";

/** A folded header's ONE pip for its members' states, in the tab's own colours and by the tab's own rule, under the
 *  same ring switches (`on`) the members' tabs wear, so a fold never shows a colour no unfolded tab would: red when a
 *  member wears the red ring (blocked on you or waiting for you); else yellow when one wears the yellow ring (something
 *  waiting on you, whatever else it is doing); else gold when one is working; else amber when one wears the amber ring
 *  (stalled on an API error that is auto-retrying: shown only when nothing in the group is making progress, since it
 *  is not on you); null when nothing is happening. */
export function sectionPip(states: ReadonlyArray<TabStateLike | null | undefined>, on: (id: RingId) => boolean = () => true): SectionPip | null {
  const rings = states.map((s) => tabRingId(s, on));
  if (rings.includes("ring-needs-you")) return "blocked";
  if (rings.includes("ring-waiting-on-you")) return "ask";
  if (states.some((s) => tabStateClass(s) === "tab-working")) return "working";
  if (rings.includes("ring-retrying")) return "retrying";
  return null;
}

/** The pip's phrase for ONE session (and the bare phrase when no name is known). */
export const SECTION_PIP_TITLE: Record<SectionPip, string> = {
  blocked: "a session in this group is blocked or waiting on you",
  ask: "a session in this group has something waiting on you",
  working: "a session in this group is working",
  retrying: "a session in this group hit an API error and is retrying on its own",
};

/** The same four for SEVERAL sessions, counted: a singular phrase before a list of names read as one
 *  session, then two. */
export const SECTION_PIP_TITLE_MANY: Record<SectionPip, (n: number) => string> = {
  blocked: (n) => `${n} sessions in this group are blocked or waiting on you`,
  ask: (n) => `${n} sessions in this group have something waiting on you`,
  working: (n) => `${n} sessions in this group are working`,
  retrying: (n) => `${n} sessions in this group hit an API error and are retrying on their own`,
};

/** The ring each pip kind names (the working pip is the state's, not a ring's). */
const PIP_RING: Record<Exclude<SectionPip, "working">, RingId> = { blocked: "ring-needs-you", ask: "ring-waiting-on-you", retrying: "ring-retrying" };

export interface TabMemberLike { name?: string; status?: TabStateLike | null }

/** The members whose own tab wears the pip's colour, under the same switches: the sessions its tooltip names, in
 *  strip order. A working session that also wears a ring is named under both kinds. */
export function sectionPipMembers(kind: SectionPip, members: ReadonlyArray<TabMemberLike | null | undefined>, on: (id: RingId) => boolean = () => true): string[] {
  const names: string[] = [];
  const wears = (s: TabStateLike | null | undefined) => kind === "working" ? tabStateClass(s) === "tab-working" : tabRingId(s, on) === PIP_RING[kind];
  for (const m of members) if (m && wears(m.status)) names.push(String(m.name || "").trim() || "(unnamed)");
  return names;
}

/** The pip's hover text: the rule's phrase — singular for one session, counted for several — then the
 *  sessions by name. */
export function sectionPipTitle(kind: SectionPip, names: readonly string[]): string {
  if (!names.length) return SECTION_PIP_TITLE[kind];
  const phrase = names.length === 1 ? SECTION_PIP_TITLE[kind] : SECTION_PIP_TITLE_MANY[kind](names.length);
  return `${phrase}: ${names.join(", ")}`;
}

// A FOLDED HEADER'S USER-TODO FLAG (the user 2026-09-06): a session tab with an open user todo wears
// a ⚑ — "this session flagged something it needs from you" — and a fold hid it. The header derives
// its flag from the SAME field the tab reads, the session payload's userTodos (the kernel's
// build_session blanks it for an ended session and every chat delta carries it), so the two agree on
// every frame and the resolve that clears the tab's glyph clears the header's flag in the same render. Since 2026-09-22
// the field is a COUNT on a member whose payload this page has not been served (a skeleton or placeholder tab: its
// tabOrder roster row, tab-meta.ts) and the rows on a loaded member's session: one rule over both shapes, so the header
// agrees with the tab whichever kind it is drawn as, and 0 (or an empty list) is a real value, nothing open.
export interface TabTodoLike { name?: string; userTodos?: number | ReadonlyArray<unknown> | null }

/** THE ONE SPELLING of "something open" over the field, for every reader of it: the folded header (sectionTodoFlag below),
 *  the skeleton and placeholder builders and the strip signature's two rows (render.ts), the section snapshot's needs-you
 *  (tab-snapshot.ts). A positive count, or a non-empty list of rows; NaN, a negative number or an absent field is nothing.
 *  A count from the kernel is a non-negative integer (tests/test_user_todos_roster.py holds it to that, and render.ts's
 *  parse of the roster admits nothing else), and one predicate keeps every surface's "open" the same fact over it:
 *  tab-usertodo-skeleton.test.ts derives the readers from the sources and holds each to this name (correctness-1, review
 *  round 1 of the roster change, 2026-09-22). */
export const openUserTodo = (v: TabTodoLike["userTodos"]): boolean =>
  typeof v === "number" ? v > 0 : Array.isArray(v) && v.length > 0;

/** The members holding an open user todo, in strip order. The COUNT is sessions, not todos: the
 *  folded header's other number is a session count too, and the tooltip names exactly those sessions. */
export interface SectionTodoFlag { count: number; names: string[] }

export function sectionTodoFlag(members: ReadonlyArray<TabTodoLike | null | undefined>): SectionTodoFlag | null {
  const names: string[] = [];
  for (const m of members) {
    if (!m || !openUserTodo(m.userTodos)) continue;   // no session and no roster row yet, or nothing open
    names.push(String(m.name || "").trim() || "(unnamed)");
  }
  return names.length ? { count: names.length, names } : null;
}

/** THE NON-FOLDING DOOR's click phrase (round 1 of the tabhide review, 2026-09-08): what a press on one of an OPEN
 *  header's doors does (render.ts show-group): the section's snapshot in the pane, the fold as it was. The count is
 *  a door on every open header (round 2) and wears this phrase over the members hidden inside the section (with
 *  nothing hidden its words say what the pane is for, sectionDoorTitle); the pip and the flag, which the header
 *  wears over those members, wear it too. */
export const SHOW_GROUP_CLICK = "click to show this group's sessions";

/** THE WAY BACK's click phrase: what a press does while the pane already shows the section (render.ts show-transcript,
 *  leaveSnapshot). The header's second click says it (tab-groups.ts headWords, `back`: open, holding the tab being
 *  read) and so do the three doors of any open header whose section the pane shows, holding that tab or not: the
 *  count, the pip and the flag (doorClick `shown`, through sectionDoorTitle, the pip's title and sectionTodoTitle;
 *  round 3 of the tabhide review): one voice for one act. */
export const BACK_TO_TRANSCRIPT_CLICK = "click to go back to the transcript";

/** THE DOORS' click clause, from one place for the three controls of an OPEN header (the count, the pip, the flag;
 *  render.ts makeGroupHead): the pane (SHOW_GROUP_CLICK), or, while the pane already shows the section (`shown`), the
 *  way back (BACK_TO_TRANSCRIPT_CLICK; round 3 of the tabhide review). The act follows the same bit there (doorAct). */
export function doorClick(shown: boolean): string {
  return shown ? BACK_TO_TRANSCRIPT_CLICK : SHOW_GROUP_CLICK;
}

/** AN OPEN HEADER'S COUNT over members hidden inside the section, in its compact form: `<shown>+<hidden>`, the tabs
 *  on the strip and the hidden members ("6+2" for eight members with two hidden; "0+3" when every member is hidden).
 *  Round 1 of the tabhide review (2026-09-08) had the count say how many are hidden, in words, because the bare total
 *  beside two tabs read as a wrong number; the same day the user, who runs a dozen tag groups, found those words too
 *  wide a head for a strip that full. The compact form keeps the honesty, its first number the tabs beside it, and is
 *  as narrow as a plain count. One source for the header's count (tab-groups.ts headWords) and the door's words
 *  (sectionDoorTitle), which lead with it. Nothing hidden: the total, as before. */
export function compactCount(total: number, hidden: number): string {
  return hidden > 0 ? `${total - hidden}+${hidden}` : String(total);
}

/** The compact count spelled out, for a hover or a spoken name: "2 on the strip and 1 hidden"; "none on the strip and
 *  3 hidden" when every member is hidden. */
export function stripAndHidden(total: number, hidden: number): string {
  const shown = total - hidden;
  return `${shown === 0 ? "none" : shown} on the strip and ${hidden} hidden`;
}

/** EVERY OPEN header's count, as the button it is there (render.ts makeGroupHead): what a reader hears and the
 *  hover. The words LEAD WITH THE COUNT'S VISIBLE TEXT (headWords' count: the compact "S+K" over hidden members,
 *  compactCount; the total otherwise), so the name a voice control hears contains the label it sees (round 2 of the
 *  tabhide review); over hidden members the count is then spelled out (stripAndHidden), since "2+1" alone names no
 *  unit. Over hidden members the click shows the group's sessions in the pane; with nothing hidden they are
 *  all on the strip already, so the words say what the pane is for instead (round 2: the door existed only once
 *  something was hidden, and the first hide of a group went through the header's click, which folds the group
 *  over its reader). The fold's own words for the hidden members are hiddenFoldWords (tab-snapshot.ts).
 *  WHILE THE PANE ALREADY SHOWS THE SECTION (`shown`; round 3: the door's click then changed nothing and its words
 *  still promised the pane), the door mirrors the header's way back: the words say the sessions are shown below and
 *  the click goes back to the transcript (BACK_TO_TRANSCRIPT_CLICK), still led by the visible count. */
export function sectionDoorTitle(hidden: number, total: number, shown = false): string {
  const over = () => `${compactCount(total, hidden)}: ${stripAndHidden(total, hidden)} while this group is open`;
  if (shown) {
    const lead = hidden > 0 ? `${over()}; the group's sessions are shown below`
                            : `${total} session${total === 1 ? "" : "s"}, shown below`;
    return `${lead}; ${doorClick(true)}`;
  }
  if (hidden > 0) return `${over()}; ${doorClick(false)}`;
  return total === 1 ? "1 session; click to see it at a glance and hide it from the strip"
                     : `${total} sessions; click to see them at a glance and hide any from the strip`;
}

/** The flag's phrase alone: the sessions by name, no click clause. The header's spoken label appends THIS (round 2
 *  of the tabhide review): the header's own click folds the group or puts the transcript back, so a label that
 *  ended with the flag's click clause announced the door's instruction as the header's own. */
export function sectionTodoPhrase(flag: SectionTodoFlag): string {
  const who = flag.count === 1
    ? `${flag.names[0]} flagged something it needs from you`
    : `${flag.count} sessions flagged something they need from you: ${flag.names.join(", ")}`;
  return `waiting on you — ${who}`;
}

/** The flag's hover text: the phrase, and what the click does. On a folded header the click opens the group
 *  (render.ts open-group); on an open one (`door`) it shows the group's sessions in the pane and leaves the fold
 *  alone (show-group), or, while the pane already shows the section (`shown`), goes back to the transcript, as the
 *  count does (doorClick; round 3 of the tabhide review). Round 1: the flag on an open header promised to open a
 *  group that was already open. */
export function sectionTodoTitle(flag: SectionTodoFlag, door = false, shown = false): string {
  return `${sectionTodoPhrase(flag)}; ${door ? doorClick(shown) : "click to open this group"}`;
}

/** The state dot every tab carries (T262g, the user 2026-09-08: the strip's row count flapped with a tab's state).
 *  A tab's width must not depend on its state: the dot's slot is laid out in EVERY state and merely hidden when the
 *  state has no dot ("tab-dot none"), so a session starting or finishing work cannot add or remove a row of the strip
 *  and slide the transcript under the reader by a row's height. working → the solid dot; awaitingBg → the await-green
 *  dot; a missing state → the gray ring; opening → the accent loader dot; compacting → null (its animated bar takes
 *  the slot); everything else → the hidden slot. */
export function tabDotClass(st: string | undefined | null): string | null {
  if (st === "compacting") return null;
  if (st === "working") return "tab-dot";
  if (st === "awaitingBg") return "tab-dot await";
  if (!st) return "tab-dot unknown";
  if (st === "opening") return "tab-dot opening";
  return "tab-dot none";
}

/** What a tab's dot says on hover (the user 2026-07-22: each pip explains itself, the same titles the feed's
 *  DOT_TIP speaks), beside the class rule above so the two can never disagree on what a dot means: working,
 *  awaitingBg, a missing state and opening have a title; the hidden slot ("tab-dot none") and the compacting
 *  bar (no dot) say nothing. render.ts sets it on the slot tabDotClass classed. */
export function tabDotTitle(st: string | undefined | null): string | null {
  if (st === "working") return "working — a turn is running right now";
  if (st === "awaitingBg") return "awaiting — idle, but background work it dispatched is still running";
  if (!st) return "state unknown — romp couldn't read this session's live state";
  if (st === "opening") return "opening — this session is still starting up";
  return null;
}
