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
// it off), which sections are folded, and which members show through their section's fold (the
// tab menu's "Show when folded"). `archived` starts folded — that tag exists to put sessions away.
// Notification is view-order.ts's two-path idiom: localStorage reaches other panes (the storage
// event), a same-window CustomEvent reaches the writer. Pure and DOM-free (the tab-order.ts
// pattern) so the rule executes in node tests; render.ts paints it.
import { SessionViews, TagUnion, viewTags } from "./session-views";

export const TABGROUPS_KEY = "romp:tabgroups";
export const TABGROUPS_EVENT = "romp-tabgroups";
/** sections that start folded until the user opens them (remembered per browser once toggled) */
export const DEFAULT_COLLAPSED: ReadonlySet<string> = new Set(["archived"]);

/** One strip section: a tag's name + color and the visible tabs homed in it, plus `localId` — the
 *  local tag's stored id when the union has one, null for a union only remote hosts' tags make —
 *  which its pins are matched against beside its name (isPinned). name null = the trailing untagged
 *  section (unlabeled by the user's ruling — a separator, not a header; localId null). */
export interface TabSection { name: string | null; localId: string | null; color: string; ids: string[] }

/** A section as a pin is matched and written against it: its name and its local tag's id. The plan's
 *  TabSection is one; sectionRef builds one from a union (the menu row's home tag). */
export type SectionRef = Pick<TabSection, "name" | "localId">;

/** A member kept visible under its folded section — the tab menu's "Show when folded" (the user
 *  2026-09-06). ONE entry per (tab, section): `sid` the tab, `name` the section's displayed name when
 *  the pin was made, `id` the local tag's id when the section had one (a remote host's tag id is never
 *  stored: it is the host's, and a section a remote tag makes is addressed by its name). A view
 *  preference like the fold itself: per browser.
 *
 *  Why both: a section is what the user sees, and it is made by whichever tags share the name — the
 *  local one, remote hosts' ones, or both together — a set that changes under the pin with no gesture
 *  on the tab (a host attaches or detaches, a same-named tag appears on the other side, the local one
 *  is renamed or deleted). Three rounds of the branch's review (2026-09-06) found the same defect in
 *  every scheme that derived ONE key from the holders at click time: the tab folded away when the set
 *  later changed. Storing the name AND the local id, and matching under either, follows the section
 *  through every such change; the id follows the local tag's rename, the name follows the remote
 *  tag's hold. */
export interface PinnedRef { sid: string; name: string; id?: string }

export interface TabGroupsState {
  on: boolean;          // the sectioned strip (default true)
  collapsed: string[];  // sections the user folded
  expanded: string[];   // default-folded sections the user opened
  pinned: PinnedRef[];  // members shown under their folded section
}

/** The section a union makes, as pins are matched and written against it. */
export function sectionRef(u: TagUnion): SectionRef {
  return { name: u.name, localId: u.localId };
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
    if (!s) { s = { name: home.name, localId: home.localId, color: home.color || "", ids: [] }; byName.set(home.name, s); }
    s.ids.push(id);
  }
  const out: TabSection[] = [];
  for (const u of unions) { const s = byName.get(u.name); if (s && !out.includes(s)) out.push(s); }
  if (loose.length) out.push({ name: null, localId: null, color: "", ids: loose });
  return out;
}

/** Does any tag hold a visible tab? Sectioning is on by default exactly then — an untagged world
 *  renders the flat strip it always had. */
export function anySectioned(visibleIds: readonly string[], unions: readonly TagUnion[]): boolean {
  return visibleIds.some((id) => homeTag(id, unions) !== null);
}

const fresh = (): TabGroupsState => ({ on: true, collapsed: [], expanded: [], pinned: [] });

/** A stored blob; anything malformed reads as the default rather than throwing (view-order's rule:
 *  a corrupt entry may cost you a preference, never the dashboard). `unions` — the current tag
 *  unions — serve the one migration: an entry in the branch's earlier shape, `{tag, sid}` with `tag`
 *  a local tag's id or a union's name, becomes `{sid, id: tag, name: <that union's name>}` when `tag`
 *  is a current local id, else `{sid, name: tag}` (a name, or a deleted tag's id — the prune drops the
 *  latter on the next pin write, as before). Readers that write back pass the unions they have, so a
 *  migration is faithful; a read before the first views frame sees none and would keep such an
 *  entry's id as a name — nothing writes the store before a sectioned strip has rendered, and that
 *  needs a frame. */
export function parseTabGroups(raw: string | null | undefined, unions: readonly TagUnion[] = []): TabGroupsState {
  if (!raw) return fresh();
  try {
    const o = JSON.parse(raw);
    if (!o || typeof o !== "object" || Array.isArray(o)) return fresh();
    const strs = (xs: unknown) => (Array.isArray(xs) ? xs.filter((x): x is string => typeof x === "string") : []);
    const pins = (xs: unknown): PinnedRef[] => {
      if (!Array.isArray(xs)) return [];
      const out: PinnedRef[] = [];
      for (const x of xs) {
        if (!x || typeof x !== "object" || typeof x.sid !== "string") continue;
        if (typeof x.name === "string") { out.push(typeof x.id === "string" ? { sid: x.sid, name: x.name, id: x.id } : { sid: x.sid, name: x.name }); continue; }
        if (typeof x.tag !== "string") continue;
        const u = unions.find((g) => g.localId === x.tag);
        out.push(u ? { sid: x.sid, name: u.name, id: x.tag } : { sid: x.sid, name: x.tag });
      }
      return out;
    };
    return { on: o.on !== false, collapsed: strs(o.collapsed), expanded: strs(o.expanded), pinned: pins(o.pinned) };
  } catch {
    return fresh();
  }
}

export function readTabGroups(unions: readonly TagUnion[] = []): TabGroupsState {
  try {
    return parseTabGroups(localStorage.getItem(TABGROUPS_KEY), unions);
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

/** Does an entry name this section? Its name, OR its id when the section has a local tag. The
 *  untagged trail has no fold, so nothing names it. */
function pinNames(sec: SectionRef, p: PinnedRef): boolean {
  return sec.name !== null && (p.name === sec.name || (p.id !== undefined && p.id === sec.localId));
}

/** The entry a pin on `sid` in this section stores: the section's name, and its local tag's id when
 *  it has one. */
function pinEntry(sec: SectionRef, sid: string): PinnedRef {
  const name = sec.name ?? "";
  return sec.localId ? { sid, name, id: sec.localId } : { sid, name };
}

/** Is this member kept visible under its folded section? An entry for the sid naming the section by
 *  its name or its local id — see PinnedRef. */
export function isPinned(st: TabGroupsState, sec: SectionRef, sid: string): boolean {
  return st.pinned.some((p) => p.sid === sid && pinNames(sec, p));
}

/** Set a member's pin EXPLICITLY (the fold's own idiom: the menu row passes the state it rendered).
 *  A write is PER SECTION: on adds, or replaces, the tab's entry for the section that is its home now
 *  (the entries naming it by name or by id collapse into one), and off removes exactly those. Entries
 *  the tab holds for OTHER sections stand either way — the menu row is offered in the home section
 *  alone, its copy speaks of that section ("while <name> is folded"), and a pin the user set under a
 *  section that a drag or a rename later makes the home again is theirs until they clear it there
 *  (round 4 of the 2026-09-06 review: an on that replaced every entry silently dropped a pin set
 *  under another section, and the row's copy had promised a per-section preference). */
export function setPinned(st: TabGroupsState, sec: SectionRef, sid: string, on: boolean): TabGroupsState {
  const pinned = st.pinned.filter((p) => !(p.sid === sid && pinNames(sec, p)));
  if (on && sec.name !== null) pinned.push(pinEntry(sec, sid));
  return { on: st.on, collapsed: st.collapsed, expanded: st.expanded, pinned };
}

export function togglePinned(st: TabGroupsState, sec: SectionRef, sid: string): TabGroupsState {
  return setPinned(st, sec, sid, !isPinned(st, sec, sid));
}

/** Drop the pins nothing can render any more, judged PER ENTRY: the session is still among the tabs
 *  the strip knows, and some union the entry names (by its name, or by its id as a local id) still
 *  holds the session — so the store does not keep an entry for every tag ever deleted, session ever
 *  closed, or member moved out. On the WRITE path only (the pin row's click): a prune there moves
 *  nothing on screen, where a prune per render could act on a transient frame (a views blob
 *  mid-write, a host's tags not yet arrived) and put a tab away with no gesture. Returns `st` itself
 *  when nothing is dropped. */
export function prunePinned(st: TabGroupsState, unions: readonly TagUnion[], knownIds: ReadonlySet<string>): TabGroupsState {
  const pinned = st.pinned.filter((p) => knownIds.has(p.sid)
    && unions.some((u) => (u.name === p.name || (p.id !== undefined && u.localId === p.id)) && u.members.includes(p.sid)));
  return pinned.length === st.pinned.length ? st : { on: st.on, collapsed: st.collapsed, expanded: st.expanded, pinned };
}

/** A tag that kept its id and changed its name between two views blobs: `local` for one of this
 *  kernel's tags (the id a pin may carry), false for a remote host's; `members` what it holds now. */
export interface TagRename { id: string; from: string; to: string; local: boolean; members: readonly string[] }

/** The tags `next` renames relative to `prev` — the previously adopted blob, so a client watching the
 *  stream sees every rename, local or a remote host's, as the frame that carries it arrives. No
 *  previous blob (the page's first frame) → none: a rename that happened while no client watched is
 *  matched by id where an id was stored (isPinned), and is missed for a remote-only pin, which has
 *  none (followTagRenames states the limit). */
export function tagRenames(prev: SessionViews | null | undefined, next: SessionViews | null | undefined): TagRename[] {
  if (!prev || !next) return [];
  const before = new Map<string, string>();
  for (const t of viewTags(prev)) before.set(t.id, t.name || "tag");
  for (const t of prev.remoteTags || []) before.set(t.id, t.name || "tag");
  const out: TagRename[] = [];
  const see = (id: string, name: string | undefined, local: boolean, members: readonly string[] | undefined) => {
    const from = before.get(id), to = name || "tag";
    if (from !== undefined && from !== to) out.push({ id, from, to, local, members: members || [] });
  };
  for (const t of viewTags(next)) see(t.id, t.name, true, t.members);
  for (const t of next.remoteTags || []) see(t.id, t.name, false, t.members);
  return out;
}

/** Carry the pins across the tags a blob renamed (tagRenames), so a pinned tab stays pinned to its
 *  group through the group's rename — the name a pin stores is the section's displayed name, and a
 *  rename changes it. An entry FOLLOWS a rename when it carries the renamed tag's id, or carries the
 *  old name with no id and the renamed tag holds its tab (a remote-only pin, made before a local tag
 *  of the name existed; the other same-named tags' pins are not this tag's to move). It is rewritten
 *  to the new name, with the tag's id when the tag is local — so the next rename finds it by id even
 *  from a client with no previous blob. Where the rename SPLITS the section — a same-named tag on the
 *  other side still holds the tab, so the tab's home after the rename is whichever half tagOrder
 *  puts first (the kernel leaves tagOrder alone on a rename, so an old name once dragged into place
 *  keeps it and the renamed local tag falls behind) — an entry for the old-name half stays beside
 *  the rewritten one: the tab is pinned in both halves, and the prune drops the half that stops
 *  holding it. `unions` are the NEXT blob's. Exact duplicates collapse. Returns `st` itself when no
 *  entry changed.
 *
 *  THE LIMIT: a remote-only pin has no id, so a rename of the remote tag that happens while no client
 *  of this browser is watching (the page closed, the blob's first frame after it) leaves the entry
 *  under the old name, where it matches nothing until the user pins the tab again. A local tag's pin
 *  carries the id and has no such gap. */
export function followTagRenames(st: TabGroupsState, renames: readonly TagRename[], unions: readonly TagUnion[]): TabGroupsState {
  if (!renames.length || !st.pinned.length) return st;
  const out: PinnedRef[] = [];
  const seen = new Set<string>();
  const put = (p: PinnedRef) => { const k = `${p.sid} ${p.name} ${p.id ?? ""}`; if (!seen.has(k)) { seen.add(k); out.push(p); } };
  for (const p of st.pinned) {
    const r = renames.find((x) => (p.id !== undefined ? x.id === p.id : x.from === p.name && x.members.includes(p.sid)));
    if (!r) { put(p); continue; }
    put(r.local ? { sid: p.sid, name: r.to, id: r.id } : { sid: p.sid, name: r.to });
    const rest = unions.find((u) => u.name === r.from && u.members.includes(p.sid));
    if (rest) put(pinEntry(sectionRef(rest), p.sid));
  }
  // by value: a second pane that adopts the same frame after the first has written finds the entries
  // already carried, and must not write (and notify) again
  const same = out.length === st.pinned.length && out.every((p, i) => p.sid === st.pinned[i].sid && p.name === st.pinned[i].name && p.id === st.pinned[i].id);
  return same ? st : { on: st.on, collapsed: st.collapsed, expanded: st.expanded, pinned: out };
}

/** The words a section header wears — its count, its tooltip and its accessible name — pure so the copy
 *  executes in tests (render.ts paints them). Folded, the count is the HIDDEN members, what the header
 *  stands in for; a pinned member's own tab is on screen and is not counted. When EVERY member is pinned
 *  the fold hides nothing, and a "0" beside two visible tabs read as a broken number (the 2026-09-06
 *  review): the count is then the total, and the title says why nothing is hidden. The chevron stays
 *  truthful either way — the section IS folded, and the click opens it. */
export interface HeadWords { count: string; title: string; label: string }

export function headWords(name: string, total: number, hidden: number, folded: boolean, holdsActive: boolean): HeadWords {
  const n = (k: number) => `${k} session${k === 1 ? "" : "s"}`;
  if (holdsActive) {
    return { count: String(total), label: `${name}, ${n(total)}`,
             title: `${name} — ${n(total)}; holds the active tab, so it stays open; drag to reorder the groups` };
  }
  if (!folded) {
    return { count: String(total), label: `${name}, ${n(total)}`,
             title: `${name} — ${n(total)}; click to fold this group; drag to reorder the groups` };
  }
  if (hidden === 0) {
    const all = total === 1 ? "its one session is" : `all ${total} sessions are`;
    return { count: String(total), label: `${name}, ${n(total)}, folded, all shown`,
             title: `${name} — folded, but ${all} set to show when folded, so none is hidden; click to open` };
  }
  return { count: String(hidden), label: `${name}, ${n(hidden)} folded`, title: `${name} — ${n(hidden)} folded; click to open` };
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
    const hidden = f ? sec.ids.filter((id) => !isPinned(st, sec, id)) : [];
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
