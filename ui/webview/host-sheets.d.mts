// The types of ui/webview/host-sheets.mjs for the webview tests that import it (the typecheck reads this file beside the module).
export interface HostSheet {
  /** The sheet's path in the tree (`ui/webview/<file>.css`), or `kernel/kernel.py <NAME>` for a constant the kernel inlines. */
  name: string;
  /** The sheet's text as the page loads it. */
  css: string;
  /** The pages that load it: a kernel page function's name, or the extension's source path. */
  loadedBy: string[];
}
/** Every sheet a page of either host loads, derived from the page assembly under `root`, sorted by name. */
export function hostSheets(root: string): HostSheet[];
/** The kernel's served pages, each `def _<name>_page():` of kernel.py with the function's own text, comment lines dropped. */
export function kernelPages(kernel: string): Array<{ name: string; body: string }>;
/** A module-level string constant of kernel.py by name, decoded as Python decodes it. */
export function pyStringConstant(src: string, name: string): string;
