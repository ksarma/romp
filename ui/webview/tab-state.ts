// THE TAB STRIP'S STATE → CLASS RULE, in one place (render.ts renderTabs wears it on the tab). Pure and
// DOM-free so it runs in node tests; the Status interface in render.ts is a superset of the shape read
// here. The folded section header once summarized its members with a pip by this rule; the header reads
// as a LABEL now (the user 2026-09-06) and carries no pip — its one member-derived mark is the user-todo
// flag below, and a member's own state shows on its own tab.
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

/** The flag's hover text: the sessions by name, and what the click does. */
export function sectionTodoTitle(flag: SectionTodoFlag): string {
  const who = flag.count === 1
    ? `${flag.names[0]} flagged something it needs from you`
    : `${flag.count} sessions flagged something they need from you: ${flag.names.join(", ")}`;
  return `waiting on you — ${who}; click to open this group`;
}
