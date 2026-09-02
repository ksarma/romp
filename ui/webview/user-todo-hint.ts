// The "more behind this" hint on a user-todo row (the split to-do card's "Waiting on you" section,
// plans/user-todos.md). A user todo is a one-line ask; the postal tool may attach a longer
// `detail`, which the row hides behind a keyed fold (click the text). Before this, a row with
// detail looked exactly like a bare one until hovered — the user could not tell AT A GLANCE whether
// a click would reveal anything (the user 2026-09-02). Now a row WITH detail wears a small trailing
// hint after its text — "▸ details", flipping to "▾ details" while the fold is open — and a bare row
// renders nothing extra, so the distinction is binary and glanceable. The gate is the payload row's
// own `detail`: the kernel ships that key only for a non-blank detail (test_user_todos.py pins it),
// so its presence IS the has-detail flag and no second field exists to drift from the text.
//
// Pure: this decides what the hint SAYS; render.ts materializes it INSIDE the .ut-text span, which
// is already the delegated uttoggle click target — the hint widens no target and hangs no listener
// of its own. Split out so the decision runs in a test (render.ts has no jsdom harness).

export const UT_HINT_CLASS = "ut-more";

export interface UtHint { text: string; title: string; }

// What the hint says in each fold state. The title doubles as the aria-label: plain words about what
// is here and what a click does. The caret follows the chat's fold vocabulary (▸ closed, ▾ open).
export function utHintFor(open: boolean): UtHint {
  return open
    ? { text: "▾ details", title: "click to hide the details" }
    : { text: "▸ details", title: "has details — click to read" };
}

// The has-detail gate: null (render nothing) unless the detail has substance. Whitespace is no
// detail — the kernel already drops it; this keeps the client honest should a row ever arrive raw.
export function utDetailHint(detail: string | null | undefined, open: boolean): UtHint | null {
  return (detail || "").trim() ? utHintFor(open) : null;
}

// The three surfaces the hint paints: its text, the hover title, and the same words for assistive
// tech. Structural so a test can hand it a plain object; an HTMLElement satisfies it.
export interface UtHintNode { textContent: string | null; title: string; setAttribute(name: string, value: string): void; }

export function applyUtHint(node: UtHintNode, hint: UtHint): void {
  node.textContent = hint.text;
  node.title = hint.title;
  node.setAttribute("aria-label", hint.title);
}
