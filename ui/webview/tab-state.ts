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

export type SectionPip = "blocked" | "retrying" | "working";

/** A folded header's ONE pip for its members' states, in the tab's own colours and by the tab's own
 *  rule: red when a member is blocked on you or waiting for you; else gold when one is working; else
 *  amber when one is stalled on an API error that is auto-retrying (shown only when nothing in the
 *  group is making progress — it is not on you); null when nothing is happening. */
export function sectionPip(states: ReadonlyArray<TabStateLike | null | undefined>): SectionPip | null {
  const cls = states.map(tabStateClass);
  if (cls.some((c) => c === "tab-blocked" || c === "tab-awaiting")) return "blocked";
  if (cls.includes("tab-working")) return "working";
  if (cls.includes("tab-retrying")) return "retrying";
  return null;
}

/** The pip's phrase for ONE session (and the bare phrase when no name is known). */
export const SECTION_PIP_TITLE: Record<SectionPip, string> = {
  blocked: "a session in this group is blocked or waiting on you",
  working: "a session in this group is working",
  retrying: "a session in this group hit an API error and is retrying on its own",
};

/** The same three for SEVERAL sessions, counted — the flag's tooltip already counts this way
 *  (sectionTodoTitle); a singular phrase before a list of names read as one session, then two. */
export const SECTION_PIP_TITLE_MANY: Record<SectionPip, (n: number) => string> = {
  blocked: (n) => `${n} sessions in this group are blocked or waiting on you`,
  working: (n) => `${n} sessions in this group are working`,
  retrying: (n) => `${n} sessions in this group hit an API error and are retrying on their own`,
};

const PIP_CLASSES: Record<SectionPip, readonly string[]> = {
  blocked: ["tab-blocked", "tab-awaiting"], working: ["tab-working"], retrying: ["tab-retrying"],
};

export interface TabMemberLike { name?: string; status?: TabStateLike | null }

/** The members whose own tab wears the pip's color — the sessions its tooltip names, in strip order. */
export function sectionPipMembers(kind: SectionPip, members: ReadonlyArray<TabMemberLike | null | undefined>): string[] {
  const names: string[] = [];
  for (const m of members) if (m && PIP_CLASSES[kind].includes(tabStateClass(m.status))) names.push(String(m.name || "").trim() || "(unnamed)");
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
// every frame and the resolve that clears the tab's glyph clears the header's flag in the same render.
export interface TabTodoLike { name?: string; userTodos?: ReadonlyArray<unknown> | null }

/** The members holding an open user todo, in strip order. The COUNT is sessions, not todos: the
 *  folded header's other number is a session count too, and the tooltip names exactly those sessions. */
export interface SectionTodoFlag { count: number; names: string[] }

export function sectionTodoFlag(members: ReadonlyArray<TabTodoLike | null | undefined>): SectionTodoFlag | null {
  const names: string[] = [];
  for (const m of members) {
    if (!m || !Array.isArray(m.userTodos) || !m.userTodos.length) continue;   // no session yet, or nothing open
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
