// STAGED messages (the user 2026-08-15): compose against a highlight, hold it, keep reading — then
// release the whole run together. ⌘/Ctrl+⏎ stages the composer's text WITH its citation chips; a
// plain send flushes the stack in stage order with the typed message last; the strip's Send now
// releases the stack alone. Deliberately NOT "queued": queued is romp's injection-side wait (sent,
// pending injection into the session); staged is user-side — not sent at all, just held where it
// was written so each message keeps the context it was written against.
//
// This is the PURE stack — per-tab isolation, order, flush-clears, discard, persistence round-trip —
// and the outgoing BODY (quoteReplyBody, stagedBatchBody), so staged-messages.test.ts EXECUTES the
// rules instead of regexing render.ts (the repo's extract-for-execution idiom). The DOM strip and the
// send routing live in render.ts.

export interface StagedMsg { text: string; cites: unknown[] }

/** The outgoing body for QUOTE citations (the user 2026-07-13): the highlighted text rides ahead of the
 *  typed message as a markdown quote block, so the agent knows exactly which part is being replied to.
 *  Also what the chip's audit preview shows: one function, no drift. Stacked chips (the user 2026-08-04)
 *  become one section each, in the order they sit in the strip. `src` (the VS Code editor flavor,
 *  2026-07-13) names where a highlight came from, a workspace-relative file:lines, so that section's
 *  lead-in points the agent at the code, not the conversation. No quotes at all is the text alone. */
export function quoteReplyBody(cites: { quote?: string; src?: string | null }[], text: string): string {
  const sections = cites.map((c) => {
    const q = (c.quote || "").split("\n").map((l) => "> " + l).join("\n");
    const lead = c.src ? "Replying to this highlighted code (" + c.src + "):" : "Replying to this part of the conversation:";
    return lead + "\n" + q;
  });
  const quoted = sections.join("\n\n");
  return quoted && text ? quoted + "\n\n" + text : quoted || text;
}

/** ONE body from the staged run (the user 2026-09-08, who wanted staged comments to land as one message,
 *  not a series): each item in stage order as its own section, the quote block(s) it was written against
 *  and then its comment, byte for byte what the item used to send on its own; items separated by a blank
 *  line; the typed message, when the send carries one, last. An item with nothing to say (no quote, no
 *  text) adds nothing; no items and nothing typed is "". A goal citation is not a quote and plays no part
 *  here: the kernel wraps a goal follow-up itself (render.ts routes those). */
export function stagedBatchBody(items: readonly StagedMsg[], typed?: { text: string; cites?: unknown[] } | null): string {
  const parts: string[] = [];
  for (const it of typed ? [...items, typed] : items) {
    const quotes = (it.cites || []).filter((c): c is { quote: string; src?: string | null } =>
      !!c && typeof (c as { quote?: unknown }).quote === "string" && !!(c as { quote?: string }).quote);
    const s = quoteReplyBody(quotes, it.text || "");
    if (s) parts.push(s);
  }
  return parts.join("\n\n");
}

export class StagedStack {
  private m = new Map<string, StagedMsg[]>();

  list(sid: string): readonly StagedMsg[] { return this.m.get(sid) || []; }
  count(sid: string): number { return (this.m.get(sid) || []).length; }

  push(sid: string, msg: StagedMsg): void {
    const l = this.m.get(sid) || [];
    l.push(msg);
    this.m.set(sid, l);
  }

  removeAt(sid: string, i: number): void {
    const l = this.m.get(sid);
    if (!l) return;
    l.splice(i, 1);
    if (!l.length) this.m.delete(sid);
  }

  /** The flush: every staged message for this tab, in stage order, and the stack is now empty —
   *  release is one-shot, never a re-send. */
  takeAll(sid: string): StagedMsg[] {
    const l = this.m.get(sid) || [];
    this.m.delete(sid);
    return l;
  }

  /** Persistence shape (rides the drafts store): sid → messages. */
  entries(): Record<string, StagedMsg[]> {
    return Object.fromEntries(this.m);
  }

  /** Hydrate from a persisted shape; junk entries are dropped, never a crash. */
  restore(saved: unknown): void {
    if (!saved || typeof saved !== "object") return;
    for (const [sid, v] of Object.entries(saved as Record<string, unknown>)) {
      const list: StagedMsg[] = [];
      for (const m of Array.isArray(v) ? v : []) {
        if (m && typeof (m as any).text === "string" && (m as any).text)
          list.push({ text: (m as any).text, cites: Array.isArray((m as any).cites) ? (m as any).cites : [] });
      }
      if (list.length) this.m.set(sid, list);
    }
  }
}
