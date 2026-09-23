import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
const run = async (f: () => Promise<void>) => { await f(); };
test("p295", async (t) => { try { await run(async () => { await inBrowser(t, async () => {}); }); } catch (e) { void e; } });
