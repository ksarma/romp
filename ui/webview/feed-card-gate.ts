// The feed pane's per-card UPDATE GATE (2026-09-06): reconcileCol calls updateAskCard only for a card
// whose inputs changed since it was last painted. Before the gate every render re-ran updateAskCard
// on every card (~810 on the recorded board): the class rewrite, the tint, the name nodes minted
// anew, the delegation lines rebuilt — a whole-board style invalidation — and then the scroll
// restore at the end of render() forced a synchronous layout of the whole invalidated tree. A
// 542 KB feedDelta carrying 58 changed cards cost as much as a full 6.6 MB frame (about 480 ms in the
// handler paired against this change in one load window, 775 ms in the first unpaired recording; the
// headless-Chrome bench, tools/ui-bench.mjs, PR #227): about 55% the forced layout at the scrollTop restore,
// about 20% the 810 updateAskCard calls, about 10% the FLIP rect passes, about 10% the parse.
// Skipping the unchanged cards shrinks the dirty set that layout has to process as well as the JS.
//
// What a card's face depends on, and how each dependency reaches the gate:
//   - the ask object itself. The delta path keeps an unchanged card's object BY REFERENCE
//     (feed-delta.ts upsertById; federation.ts mergeHostFeeds pushes it through unchanged), so a new
//     object means the kernel sent this card: `card._it !== it` (updateAskCard stashes `_it`).
//   - every board-level input updateAskCard reads OUTSIDE the ask object: cardInputsKey folds them
//     into one string, computed from an env the render builds once. The list below is the complete
//     set (a source scan of updateAskCard, applySections, quarWho, wireNodeZones and dotFor); a
//     missed input shows as a stale badge on an unchanged card, so keep it complete.
//   - a local gesture (a section toggle, the bell, hover/pin): its handler writes the DOM directly
//     and, where a column could change, calls render(); hover/pin are also in the key.
//   - time: the 15 s live pass (feed.ts livePass) moves every stamped age, tint and duration. The
//     gate is what makes stamping them necessary: a card that is not re-sent is not re-painted.
// The card's column and its place in the column are NOT gated — reconcileCol re-applies both every
// render — so a card whose column or sort key changed still moves (a column change always arrives
// as a new object; a follow-move prediction is a copy).
//
// Deliberately NOT in the key: secChoice / cardTreeExpanded (their handlers repaint the card
// locally; the settings-driven reset rides prefs.collapsed), pendingDone (the modal reads it, the
// card does not), the clock (the live pass owns it). Pure: node --test runs it without a DOM.

/** The slice of an ask the key reads. Structural, so tests pass plain objects. */
export interface GateItem {
  itemId: string;
  sid: string;
  name: string;
  color?: { bg: string } | null;
  blocked?: { state: string } | null;
  tree?: { kind: string; who: string; whoSid?: string }[] | null;
  delegTracked?: { name: string }[] | null;
}

/** The board-level inputs, resolved by the render once per pass. */
export interface GateEnv {
  /** dotFor: the working / awaiting / unknown state of a session by name — the card's own dot, the
   *  apiRecovered rule (working or awaiting), and each tracked delegation peer's dot. */
  dot: (name: string) => string;
  /** workingSet membership by name: the handoff delegation lines show only live-working recipients. */
  working: (name: string) => boolean;
  /** userTodosMap: sid → open user-todo count (the "waiting on you" marker). */
  userTodos: Record<string, number>;
  /** hoverAskId ?? pinnedAskId, and pinnedAskId: the .focused / .pinned classes. */
  focusId: string | null;
  pinnedId: string | null;
  /** cardNotifyOn: the bell's effective state (pendingNotify over the payload's notify). */
  notifyOn: (it: GateItem) => boolean;
  /** feedPrefs: grouped hides the name row, collapsed is the section default (resolveSec), and a
   *  colormap change must repaint every tint at once (onSettingsChanged → render(), as today). */
  prefs: { grouped: boolean; collapsed: boolean; colormap: string };
  /** hostIsDown(sid): the struck "host:" prefix on a remote session's name. */
  hostDown: (sid: string) => boolean;
  /** feedSelfHost: the quarantine route's recipient host. */
  selfHost: string;
  /** A per-render counter for cards that must never skip: a quarantine card reads sessionColors by
   *  name, a map the payload rebuilds every frame, so its key is unique per render. */
  seq: number;
}

/** One string of every board-level input this card's face reads. Two renders with equal inputs
 *  give equal keys; a change in any one of them changes the key. */
export function cardInputsKey(it: GateItem, env: GateEnv): string {
  const parts: string[] = [
    env.dot(it.name),
    String(env.userTodos[it.sid] || 0),
    it.itemId === env.focusId ? "f" : "",
    it.itemId === env.pinnedId ? "p" : "",
    env.notifyOn(it) ? "n" : "",
    env.prefs.grouped ? "g" : "",
    env.prefs.collapsed ? "c" : "",
    env.prefs.colormap,
    env.hostDown(it.sid) ? "d" : "",
    env.selfHost,
    // the colour echo (feed.ts applyColorEcho) writes `a.color` IN PLACE — the one write into a shared
    // ask object — so identity cannot carry it; the colour rides the key instead
    (it.color && it.color.bg) || "",
  ];
  for (const n of it.tree || []) {
    if (n.kind !== "handoff" || !n.whoSid) continue;
    parts.push(n.whoSid + (env.working(n.who) ? "w" : ""));
  }
  for (const d of it.delegTracked || []) parts.push(env.dot(d.name));
  if (it.blocked && it.blocked.state === "quarantine") parts.push("q" + env.seq);
  return parts.join("|");
}

/** The card element's gate fields, as updateAskCard and reconcileCol keep them. */
export interface GatedCard { _it?: unknown; _ik?: string }

/** True when the card was last painted from a different object, or under different inputs. */
export function cardNeedsUpdate(card: GatedCard, it: unknown, key: string): boolean {
  return card._it !== it || card._ik !== key;
}

/** The FLIP passes' gate (the same design, one level up): a column whose planned key sequence equals
 *  its current one moved nothing — no card entered, left, or changed place — so its rects need no
 *  reading. Order-sensitive, by design: a sort change is a move. */
export function sameKeySeq(current: readonly string[], planned: readonly string[]): boolean {
  if (current.length !== planned.length) return false;
  for (let i = 0; i < current.length; i++) if (current[i] !== planned[i]) return false;
  return true;
}
