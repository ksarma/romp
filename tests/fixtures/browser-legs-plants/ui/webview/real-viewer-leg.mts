// the launcher's .mts twin (a plant's companion, not a test module): a real-viewer-leg.mts beside the stub launcher with no .mjs
// there, the file the bundler loads for a specifier spelled ./real-viewer-leg.mjs, and it launches Firefox itself (p371)
import { firefox } from "playwright";
export async function inBrowser(t: unknown, body: (b: unknown) => Promise<void>): Promise<void> { void t; const b = await firefox.launch(); try { await body(b); } finally { await b.close(); } }
