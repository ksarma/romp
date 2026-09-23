// a helper that skips before the shared call (a plant's companion, not a test module)
import { inBrowser } from "./real-viewer-leg";
export async function maybe(t: any, body: (b: any) => Promise<void>): Promise<void> { if (!process.env.HAS_BROWSER) t.skip("no browser here"); return inBrowser(t, body); }
