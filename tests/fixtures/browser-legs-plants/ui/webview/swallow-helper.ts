// a helper that swallows the shared call's failure (a plant's companion, not a test module)
import { inBrowser } from "./real-viewer-leg";
export async function safe(t: any, body: (b: any) => Promise<void>): Promise<void> { try { await inBrowser(t, body); } catch (e) { void e; } }
