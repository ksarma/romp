// The types of tools/css-rules.mjs for the webview tests that import it (the typecheck reads this file beside the module).
export interface CssRule {
  /** The selector list, whitespace collapsed to single spaces. */
  selector: string;
  /** The declarations between the braces, whitespace collapsed, trimmed. */
  body: string;
  /** The preludes of the at-rules enclosing the rule, outermost first. */
  chain: string[];
}
export function stripCssComments(css: string): string;
export function cssRules(css: string): CssRule[];
export function renderRule(rule: CssRule): string;
export function underScreen(chain: string[]): boolean;
