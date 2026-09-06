// TAB GROUPS ARE TAGS (the user 2026-09-04). The chat tab strip renders one section per tag, in the
// user's tag order, each tab under its HOME tag — the FIRST holder tag in tagOrder, the rule
// revealIn already states ("a tagged session's home is its first holder tag"), so a tab's section
// and its reveal agree. Sessions in no tag trail in an unlabeled section. No new store and no new
// session field: the kernel's views blob (tags, members, tagOrder) is the whole model, the headers
// are the very tags the Tags flyout edits, and reordering the groups IS reordering tagOrder — the
// kernel-persisted union order the timeline's tag-pill drag writes too, so the two surfaces cannot
// disagree. A session may hold other tags as well; they filter, they do not section.
//
// Per-browser state, this viewer's like romp:vieworder: whether the strip sections at all (ON by
// default whenever some tag holds a visible tab; the chat tag-lens menu's "Group tabs by tag" turns
// it off) and which sections are folded. `archived` starts folded — that tag exists to put sessions
// away. Notification is view-order.ts's two-path idiom: localStorage reaches other panes (the
// storage event), a same-window CustomEvent reaches the writer. Pure and DOM-free (the tab-order.ts
// pattern) so the rule executes in node tests; render.ts paints it.
import { SessionViews, TagUnion, viewTags } from "./session-views";

export const TABGROUPS_KEY = "romp:tabgroups";
export const TABGROUPS_EVENT = "romp-tabgroups";
/** sections that start folded until the user opens them (remembered per browser once toggled) */
export const DEFAULT_COLLAPSED: ReadonlySet<string> = new Set(["archived"]);

/** One strip section: a tag's name + colour and the visible tabs homed in it, plus `key`, the tag's
 *  stored id (sectionKey) — the per-browser pin state is keyed by it, so a pin follows the TAG, not its
 *  spelling, and a session moved to another group starts unpinned. name null = the trailing untagged
 *  section (unlabeled by the user's ruling — a separator, not a header; key ""). */
export interface TabSection { name: string | null; key: string; color: string; ids: string[] }

/** A member kept visible under its folded section — the tab menu's "Show when folded" (the user
 *  2026-09-06) — keyed by (tag id, sid). A view preference like the fold itself: per browser. */
export interface PinnedRef { tag: string; sid: string }

export interface TabGroupsState {
  on: boolean;          // the sectioned strip (default true)
  collapsed: string[];  // sections the user folded
  expanded: string[];   // default-folded sections the user opened
  pinned: PinnedRef[];  // members shown under their folded section
}

/** The id a section's pins are keyed by: the local tag's stored id, else the first remote's; a
 *  union with no ids at all (never built by viewTagUnion) falls back to its name. */
export function sectionKey(u: TagUnion): string {
  return u.localId || u.ids[0] || u.name;
}

/** THE home-tag rule: the first union (they arrive in tagOrder) holding the id, or null. */
export function homeTag(id: string, unions: readonly TagUnion[]): TagUnion | null {
  return unions.find((u) => u.members.includes(id)) || null;
}

/** Section the visible ids: one section per home tag, sections in UNION order (tagOrder governs —
 *  which is why reordering tags is first-class), tabs inside keep their strip order, the untagged
 *  trail last. A tag holding no visible id yields no section. */
export function sectionTabs(visibleIds: readonly string[], unions: readonly TagUnion[]): TabSection[] {
  const byName = new Map<string, TabSection>();
  const loose: string[] = [];
  for (const id of visibleIds) {
    const home = homeTag(id, unions);
    if (!home) { loose.push(id); continue; }
    let s = byName.get(home.name);
    if (!s) { s = { name: home.name, key: sectionKey(home), color: home.color || "", ids: [] }; byName.set(home.name, s); }
    s.ids.push(id);
  }
  const out: TabSection[] = [];
  for (const u of unions) { const s = byName.get(u.name); if (s && !out.includes(s)) out.push(s); }
  if (loose.length) out.push({ name: null, key: "", color: "", ids: loose });
  return out;
}

/** Does any tag hold a visible tab? Sectioning is on by default exactly then — an untagged world
 *  renders the flat strip it always had. */
export function anySectioned(visibleIds: readonly string[], unions: readonly TagUnion[]): boolean {
  return visibleIds.some((id) => homeTag(id, unions) !== null);
}

const fresh = (): TabGroupsState => ({ on: true, collapsed: [], expanded: [], pinned: [] });

/** A stored blob; anything malformed reads as the default rather than throwing (view-order's rule:
 *  a corrupt entry may cost you a preference, never the dashboard). */
export function parseTabGroups(raw: string | null | undefined): TabGroupsState {
  if (!raw) return fresh();
  try {
    const o = JSON.parse(raw);
    if (!o || typeof o !== "object" || Array.isArray(o)) return fresh();
    const strs = (xs: unknown) => (Array.isArray(xs) ? xs.filter((x): x is string => typeof x === "string") : []);
    const pins = (xs: unknown): PinnedRef[] => (Array.isArray(xs)
      ? xs.filter((x) => !!x && typeof x === "object" && typeof x.tag === "string" && typeof x.sid === "string")
          .map((x) => ({ tag: x.tag as string, sid: x.sid as string }))
      : []);
    return { on: o.on !== false, collapsed: strs(o.collapsed), expanded: strs(o.expanded), pinned: pins(o.pinned) };
  } catch {
    return fresh();
  }
}

export function readTabGroups(): TabGroupsState {
  try {
    return parseTabGroups(localStorage.getItem(TABGROUPS_KEY));
  } catch {
    return fresh();   // private mode / blocked storage → the defaults, every time
  }
}

/** Persist and tell every pane — `storage` fires only in OTHER same-origin contexts, so the writing
 *  window gets the same news through a CustomEvent (one notification path, two deliveries). */
export function writeTabGroups(st: TabGroupsState): void {
  try {
    localStorage.setItem(TABGROUPS_KEY, JSON.stringify({ on: st.on, collapsed: st.collapsed, expanded: st.expanded, pinned: st.pinned }));
  } catch {
    /* quota / private mode → this preference just doesn't outlive the page */
  }
  try {
    window.dispatchEvent(new CustomEvent(TABGROUPS_EVENT));
  } catch {
    /* no window (node test) */
  }
}

/** Folded? The user's explicit fold or open wins; otherwise the default set decides. */
export function isSectionCollapsed(st: TabGroupsState, name: string): boolean {
  if (st.collapsed.includes(name)) return true;
  if (st.expanded.includes(name)) return false;
  return DEFAULT_COLLAPSED.has(name);
}

/** Set a section's fold state EXPLICITLY. The header's click passes the state it RENDERED, not the
 *  stored one: the active tab's section renders open whatever the store says, and toggling the
 *  stored bit there inverted the click — "fold" on a stored-folded, rendered-open `archived` stored
 *  it OPEN for good, with nothing visible changing. Minimal storage: a name is listed only where it
 *  differs from the default set. */
export function setSectionCollapsed(st: TabGroupsState, name: string, folded: boolean): TabGroupsState {
  const collapsed = st.collapsed.filter((n) => n !== name);
  const expanded = st.expanded.filter((n) => n !== name);
  if (folded) { if (!DEFAULT_COLLAPSED.has(name)) collapsed.push(name); }
  else if (DEFAULT_COLLAPSED.has(name)) expanded.push(name);
  return { on: st.on, collapsed, expanded, pinned: st.pinned };
}

export function toggleSectionCollapsed(st: TabGroupsState, name: string): TabGroupsState {
  return setSectionCollapsed(st, name, !isSectionCollapsed(st, name));
}

/** Is this member kept visible under its folded section? Keyed by (tag id, sid) — see PinnedRef. */
export function isPinned(st: TabGroupsState, tag: string, sid: string): boolean {
  return st.pinned.some((p) => p.tag === tag && p.sid === sid);
}

/** Set a member's pin EXPLICITLY (the fold's own idiom: the menu row passes the state it rendered). */
export function setPinned(st: TabGroupsState, tag: string, sid: string, on: boolean): TabGroupsState {
  const pinned = st.pinned.filter((p) => !(p.tag === tag && p.sid === sid));
  if (on) pinned.push({ tag, sid });
  return { on: st.on, collapsed: st.collapsed, expanded: st.expanded, pinned };
}

export function togglePinned(st: TabGroupsState, tag: string, sid: string): TabGroupsState {
  return setPinned(st, tag, sid, !isPinned(st, tag, sid));
}

/** One strip item: a section header (folded or open; `active` = it holds the active tab; `hidden` =
 *  the member ids a folded header stands in for — its members less the pinned ones, [] when open) or
 *  a tab. */
export type StripItem = { head: TabSection; folded: boolean; active: boolean; hidden: string[] } | { id: string };
export interface StripPlan {
  items: StripItem[];
  folded: Set<string>;   // the ids a folded header stands in for — keyboard cycling skips them
  sectioned: boolean;
}

/** The strip PLAN render.ts paints, pure so the rule executes in node tests.
 *  - `phone`: the kernel's phone chat page hides the strip and builds its own session list by scraping
 *    every rendered tab; it has no header to unfold and no switch, so a folded section there made its
 *    sessions unreachable (`archived` starts folded). Sectioning is DESKTOP-ONLY: on the phone layout
 *    the plan is the flat strip, always — every visible id, nothing folded.
 *  - `pending`: a provisional tab (a create in flight) with the tags the request named. Its future
 *    home is the first of those in tagOrder — the kernel's own home-tag rule — so it renders there
 *    from the first paint instead of landing in the untagged trail and jumping when the frame arrives.
 *  - A folded section hides its members EXCEPT the pinned ones (the tab menu's "Show when folded"),
 *    which keep their place under the header in strip order; the header stands in for `hidden` alone
 *    (its count and its flag read those), and only those ids join the `folded` set.
 *  - The ACTIVE tab's section never renders folded: keyboard focus must never land on a hidden node.
 *    Its header is marked `active`, and render.ts gives that header no fold action: a fold stored
 *    there could not render (nothing changed on screen, on every click) and then bit when the user
 *    switched tabs. The section is unfoldable while it holds the active tab. */
export function planStrip(visibleIds: readonly string[], unions: readonly TagUnion[], st: TabGroupsState,
                          activeId: string | null, phone: boolean,
                          pending?: { id: string; tags: readonly string[] } | null): StripPlan {
  let u = unions;
  if (pending && pending.tags.length && visibleIds.includes(pending.id)) {
    u = unions.map((x) => (pending.tags.includes(x.name) && !x.members.includes(pending.id)
      ? { ...x, members: [...x.members, pending.id] } : x));
  }
  const sectioned = !phone && st.on && anySectioned(visibleIds, u);
  const items: StripItem[] = [];
  const folded = new Set<string>();
  if (!sectioned) {
    for (const id of visibleIds) items.push({ id });
    return { items, folded, sectioned };
  }
  for (const sec of sectionTabs(visibleIds, u)) {
    const active = activeId !== null && sec.ids.includes(activeId);
    const f = sec.name !== null && !active && isSectionCollapsed(st, sec.name);
    const hidden = f ? sec.ids.filter((id) => !isPinned(st, sec.key, id)) : [];
    items.push({ head: sec, folded: f, active, hidden });
    for (const id of sec.ids) { if (hidden.includes(id)) folded.add(id); else items.push({ id }); }
  }
  return { items, folded, sectioned };
}

/** The header drag: `from` takes `to`'s slot in the FULL union order (every name, not only the
 *  sectioned ones — the persisted order must stay complete). Unknown or equal names → unchanged. */
export function reorderTagOrder(names: readonly string[], from: string, to: string): string[] {
  const list = names.filter((n, i) => typeof n === "string" && names.indexOf(n) === i);
  const fi = list.indexOf(from), ti = list.indexOf(to);
  if (fi < 0 || ti < 0 || fi === ti) return list;
  const out = list.filter((n) => n !== from);
  const at = out.indexOf(to);
  out.splice(fi < ti ? at + 1 : at, 0, from);
  return out;
}

/** Write an order onto a views blob the way the timeline's pill drag does: tagOrder carries the
 *  whole union order (remote-homed names included, viewer-side), and the local tags array re-sorts
 *  to match — the natural store for local-only readers. Returns a new blob. */
export function applyTagOrder(views: SessionViews | null | undefined, order: readonly string[]): SessionViews {
  const nv: SessionViews = JSON.parse(JSON.stringify(views || {}));
  nv.tagOrder = order.slice();
  const ix = new Map(order.map((n, i) => [n, i] as const));
  const rank = (name: string | undefined) => (name !== undefined && ix.has(name) ? ix.get(name)! : order.length);
  nv.tags = viewTags(nv).slice().sort((a, b) => rank(a.name) - rank(b.name));
  delete nv.groups;
  return nv;
}
