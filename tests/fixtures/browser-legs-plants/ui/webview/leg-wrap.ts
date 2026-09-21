// a wrapper: calls the launcher's inBrowser for the module that imports it (a plant's companion, not a test module)
import { inBrowser } from "./real-viewer-leg";
export function withPage(t: any, f: (b: any) => Promise<void>): Promise<void> { return inBrowser(t, f); }
