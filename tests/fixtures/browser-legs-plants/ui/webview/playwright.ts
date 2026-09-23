// a local module named like the package: binds and calls the launcher's inBrowser (a plant's companion, not a test module)
import { inBrowser } from "./real-viewer-leg";
export function run(t: any): Promise<void> { return inBrowser(t, async () => {}); }
