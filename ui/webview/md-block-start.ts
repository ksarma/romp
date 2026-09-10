// Block-start hints against marked's paragraph clip: one scan per lexer frame, not one per paragraph.
//
// marked 12's block lexer (Lexer.blockTokens) calls every block extension's `start` hint before EVERY top-level
// paragraph, on the remaining source less its first character, and clips the paragraph at the nearest index a hint
// returns (marked.esm.js, "top-level paragraph"). A hint that scans the rest of the note for its construct therefore
// runs once per paragraph over the whole remainder, and the lex is quadratic in the paragraph count. Measured in the
// Slice 4 review (round 2, node, marked 12.0.2, medians): a 272 KB note of 8,000 one-line paragraphs lexed in 34 ms
// with no block hint, 493 ms with the chat's one hint on the base, 1,299 ms with the two hints the branch carried at
// round 2 (the math one and the callout's; the callout's is gone since round 3, md-config.ts, so the math hint is the
// one memoised here); a 200 KB transcript-sized reply 30, 83 and 161 ms. The hints were exact and cheap per call; the
// count of calls was the cost.
//
// The remedy is exact, not a heuristic. Within one blockTokens call every hint call's source is a SUFFIX of the
// previous one: marked only ever shortens `src` by substring as it consumes tokens. So a hint that returns the FIRST
// position where its construct starts, judged from the text at and after that position, has the same answer at the
// next call shifted by the characters consumed, until that position itself is consumed; and "none in the rest" stays
// true to the end of the frame. memoBlockStart keeps the answer as a distance from the END of the source, the same
// number for every suffix, and calls the finder again only when the remembered position has been consumed. Nested
// calls (a blockquote's body, a list item's, a callout's) lex a different string on the same lexer, so the memo is per
// FRAME: blockTokens is wrapped to keep a stack of frames on the lexer, and a hint reads the innermost. A hint called
// with no lexer (a test calling it directly) or a lexer whose blockTokens is not the wrapped one runs the finder every
// time, the plain behaviour.
//
// The wrap is installed when this module loads, not by applyMdConfig: chat-md.ts's instance for the user's own words
// takes the extension list without calling applyMdConfig, and the Lexer class is the one marked gives every instance.
// Two copies of this module in one process (a test bundling the source beside a compiled copy) each wrap and each keep
// their own stack, so a hint always finds the frames its own copy pushed; the guard below only spares one copy
// wrapping itself twice.
import { Lexer } from "marked";
import type { TokenizerStartFunction } from "marked";

/** One blockTokens call's scratch: what each memoised hint, and the math tokenizer, remembers for the frame, keyed by
 *  the owner (the hint's finder; a module-private key). Read through frameOf. */
export type Frame = Map<unknown, unknown>;

const stacks = new WeakMap<object, Frame[]>();
type BlockTokens = (this: object, src: string, tokens?: unknown[]) => unknown;
const WRAPPED = Symbol("romp md-block-start frames");

function installFrames(proto: { blockTokens: BlockTokens }): void {
  const orig = proto.blockTokens as BlockTokens & { [WRAPPED]?: true };
  if (orig[WRAPPED]) return;
  const wrapped = function (this: object, ...args: [string, unknown[]?]) {
    if (!this || typeof this !== "object") return orig.apply(this, args);   // no lexer to key a frame on: plain marked
    let stack = stacks.get(this);
    if (!stack) { stack = []; stacks.set(this, stack); }
    stack.push(new Map());
    try { return orig.apply(this, args); } finally { stack.pop(); }
  } as BlockTokens & { [WRAPPED]?: true };
  wrapped[WRAPPED] = true;
  proto.blockTokens = wrapped;
}
installFrames(Lexer.prototype as unknown as { blockTokens: BlockTokens });

/** The innermost frame of the lexer a hint or tokenizer was called for (marked binds `{ lexer }` as `this`), or
 *  undefined when there is none: no lexer, or one whose blockTokens this module did not wrap. */
export function frameOf(lexer: unknown): Frame | undefined {
  if (!lexer || typeof lexer !== "object") return undefined;
  const stack = stacks.get(lexer);
  return stack && stack.length ? stack[stack.length - 1] : undefined;
}

type StartMemo = { fromEnd: number };   // the remembered answer as a distance from the end of the source; -1 for none

/** A block extension's `start` hint over `find`, which returns the index of the FIRST position in `src` where the
 *  extension's construct starts, or -1, judged only from the text at and after that position (so the answer for a
 *  suffix of `src` is the same position, shifted, or none). The hint remembers the answer per frame and asks `find`
 *  again only once the remembered position has been consumed. `find` receives the frame as well, for any memo of its
 *  own (the math tokenizer's closer search keeps one). */
export function memoBlockStart(find: (src: string, frame: Frame | undefined) => number): TokenizerStartFunction {
  return function (this: { lexer?: unknown } | undefined, src: string): number | undefined {
    const frame = frameOf(this && this.lexer);
    const memo = frame && (frame.get(find) as StartMemo | undefined);
    if (memo) {
      if (memo.fromEnd < 0) return undefined;
      if (memo.fromEnd <= src.length) return src.length - memo.fromEnd;
    }
    const at = find(src, frame);
    if (frame) frame.set(find, { fromEnd: at < 0 ? -1 : src.length - at });
    return at < 0 ? undefined : at;
  };
}
