// Fenced code, dressed the same wherever it renders (Slice 3 of plans/markdown-viewer.md, 2026-09-08): the per-line
// rows that make a soft-wrap read distinctly from a real newline (the user 2026-06-16) and the automatic Copy button
// (the user 2026-06-22). The chat's highlight() (render.ts) and the viewer's mdBlock (file-view.ts) both call these.
// The module exists because the two functions lived module-private in render.ts and file-view.ts cannot import
// render.ts: render.ts imports file-view.ts, and the Files and feed bundles must not carry the chat. They moved here
// as they were; the chat's behaviour is unchanged.
//
//   - wrapLinesHtml is the pure walk: highlighted HTML split into lines, each wrapped in
//     `<span class="cl"><span class="ct">…</span></span>`, an hljs span that straddles a newline re-opened on the next
//     line so the markup stays valid. The NEWLINES ARE DROPPED: a row stands for its line and the CSS counter on .cl
//     draws the number. Whatever reads a wrapped block's lines puts the newline back between rows (anchor-map.ts
//     codeRuns: the paint fallback, the reader's place, Slice 8's mapping), and Copy never reads the rows: its caller
//     hands addCopyBtn the text to copy, settled before the rewrite. For the chat that is the code element's
//     textContent as captured (render.ts highlight); for the viewer it is the fence's text as the NOTE holds it
//     (fence-source.ts: marked expanded the note's leading tabs to spaces before the textContent existed), the
//     captured textContent only for a fence the module does not find in the note (file-view.ts mdBlock).
//   - wrapCodeLines applies it to a code element.
//   - addCopyBtn parks a Copy button top-right of the <pre>, idempotent (a re-render can run it again), copying the
//     text it was given: the on-screen textContent lost its newlines to the wrap and is not copy-safe.
//   - copyText: the async Clipboard API with a hidden-textarea execCommand fallback.
//
// Click-safety (ui/CLAUDE.md): the Copy button's action stays on the button. Delegating it to a stable ancestor would
// change nothing for the one way a press on it is lost, a surface that REPLACES the fence while the pointer is down:
// a pressed node removed before the mouseup dispatches no click at all, to the button or to any ancestor (Chromium,
// probed 2026-09-08; actions.ts, the header). The surface that rebuilds is what waits: the viewer's body is swapped
// by a reload's fetch landing with no gesture behind it (the Comments panel's poll saw a session's write), and that
// landing is held while a pointer is pressed over the body and runs on the release (actions.ts pressHold;
// file-view-copy-held-browser.test.ts pins it). The chat rebuilds a card on its own paths; that is the chat's matter.
// A KEYBOARD press has the same window and no hold reads it (the hold reads pointer events; the chat has none): a
// button's Space activation is native to the keyup (Enter's to the keydown), so a swap between the keydown and the
// keyup took the focused button and the keyup clicked nothing (the Slice 3 review, round 2). The button closes that
// window itself: Space acts on the KEYDOWN, as Enter does, with the key's default prevented on the keydown (the button is
// never put :active by the key, so its keyup dispatches no click) and on the keyup; a held key's repeats copy nothing
// more. That is the same reading of Space the Comments panel gives its own controls (file-comments.ts, KEY_ACTS), and
// every surface with a Copy gets it (file-view-copy-space-browser.test.ts pins it over the viewer).
//
// The sheets: the chat's unscoped `pre code .cl` / `.ct` / `.code-copy` rules (styles.css) and the viewer's scoped
// `.fileview-md` copies in styles.css and feed.css (the feed page loads only feed.css), byte-equal
// (code-block.test.ts, fileview-parity.test.ts).

const el = (tag: string, cls: string): HTMLElement => { const e = document.createElement(tag); e.className = cls; return e; };

/** Highlighted HTML as per-line rows: `<span class="cl"><span class="ct">…</span></span>` per line, spans re-balanced
 *  across the line break, the newlines dropped. A trailing newline is not a blank line. */
export function wrapLinesHtml(html: string): string {
  const lines = html.split("\n");
  if (lines.length > 1 && lines[lines.length - 1] === "") lines.pop();   // a trailing newline isn't a blank line
  let open: string[] = [];
  return lines.map((ln) => {
    const prefix = open.join("");
    const re = /<span[^>]*>|<\/span>/g; let m; const stack = open.slice();
    while ((m = re.exec(ln))) { if (m[0] === "</span>") stack.pop(); else stack.push(m[0]); }
    const suffix = "</span>".repeat(Math.max(0, stack.length));
    open = stack;
    return `<span class="cl"><span class="ct">${prefix}${ln}${suffix}</span></span>`;
  }).join("");
}

/** Wrap each logical line of a (highlighted or plain) code element in the rows above, and write the digits of its last
 *  line number on the element (`--ln-digits`): the sheets' gutter basis reads it, so every row of a 10000-line block
 *  carries a five-digit gutter and the text column stays one line (the Slice 3 review, round 2: a flex item's min-content
 *  widened the one row a five-digit number outgrew, and `:has(> .cl:nth-child(10000))` in the sheet cost the layout six
 *  times over on every fence). The rows are the element's children, so childElementCount is the line count; both callers
 *  wrap after any sanitize, so the inline property stands. */
export function wrapCodeLines(code: HTMLElement): void {
  code.innerHTML = wrapLinesHtml(code.innerHTML);
  code.style.setProperty("--ln-digits", String(String(code.childElementCount).length));
}

// Copy text to the clipboard, falling back to a hidden-textarea execCommand when the async Clipboard API
// is unavailable (it needs a secure context; localhost counts, but stay safe). Returns whether it copied.
export function copyText(text: string): Promise<boolean> {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    return navigator.clipboard.writeText(text).then(() => true, () => fallbackCopy(text));
  }
  return Promise.resolve(fallbackCopy(text));
}
function fallbackCopy(text: string): boolean {
  try {
    const ta = document.createElement("textarea");
    ta.value = text; ta.style.position = "fixed"; ta.style.top = "-9999px"; ta.style.opacity = "0";
    document.body.appendChild(ta); ta.focus(); ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return ok;
  } catch { return false; }
}

// An automatic "Copy" button parked top-right of every rendered code block (the user 2026-06-22). The text to copy
// is the caller's, closed over here and never read off the block: the on-screen markup adds a line-number gutter
// and drops the newline joins, so its textContent would be wrong. The chat passes the textContent it captured
// before the highlight rewrite; the viewer passes the fence's text as the note holds it (fence-source.ts), the
// captured textContent only for a fence not found there (the header). Faint until the block is hovered; flips to
// a green "Copied" for ~1.2s on success. Idempotent (highlight can re-run on a re-render).
export function addCopyBtn(pre: HTMLElement, raw: string): void {
  if (pre.querySelector(":scope > .code-copy")) return;
  pre.classList.add("has-copy");
  const btn = el("button", "code-copy") as HTMLButtonElement;
  btn.type = "button"; btn.textContent = "Copy"; btn.title = "copy this code block";
  const copy = (): void => {
    copyText(raw).then((ok) => {
      btn.textContent = ok ? "Copied" : "Copy failed";
      btn.classList.toggle("copied", ok);
      window.setTimeout(() => { btn.textContent = "Copy"; btn.classList.remove("copied"); }, 1200);
    });
  };
  btn.addEventListener("click", (ev) => {
    ev.preventDefault(); ev.stopPropagation();
    copy();
  });
  // Space on the keydown, not the native keyup (header, Click-safety): the keydown's default prevented keeps the button
  // out of :active for the key, so the keyup clicks nothing; the keyup's prevented too, for an engine that would click
  // anyway. Repeats of a held key are the same press. Enter is left to the button: its click is on the keydown already.
  btn.addEventListener("keydown", (ev) => {
    if (ev.key !== " ") return;
    ev.preventDefault();
    if (ev.repeat) return;
    copy();
  });
  btn.addEventListener("keyup", (ev) => { if (ev.key === " ") ev.preventDefault(); });
  pre.appendChild(btn);
}
