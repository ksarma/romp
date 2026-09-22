// The types of ui/webview/host-sheets.mjs for the webview tests that import it (the typecheck reads this file beside the module).
export interface HostSheet {
  /** The sheet's path in the tree (`ui/webview/<file>.css`), `kernel/kernel.py <NAME>` for a constant the kernel inlines, or `kernel/kernel.py _<helper>` for the
   *  block a helper the page calls writes into its HTML at serve time. */
  name: string;
  /** The sheet's text as the page loads it. */
  css: string;
  /** The pages that load it: a kernel page function's name, or the extension's source path. */
  loadedBy: string[];
}
/** Every sheet a page of either host loads, derived from the page assembly under `root`, sorted by name. */
export function hostSheets(root: string): HostSheet[];
/** The kernel's served pages: each `def _<name>_page(...)` of kernel.py whose `)` closes on `:` at the end of its line, whatever its parameters (a signature
 *  wrapped across lines included), with the function's own text up to the first column-zero statement outside a triple-quoted literal, comment lines dropped;
 *  a page def in any other shape (a return annotation, a `)` inside a default, a trailing comment after the colon, an async def) fails by name, and a
 *  def-shaped line at column zero inside a literal is read as a page too (a phantom that adds and never removes, disclosed). */
export function kernelPages(kernel: string): Array<{ name: string; body: string }>;
/** A module-level string constant of kernel.py by name, decoded as Python decodes it. */
export function pyStringConstant(src: string, name: string): string;
