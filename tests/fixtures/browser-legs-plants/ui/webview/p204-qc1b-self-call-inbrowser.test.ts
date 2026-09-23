import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
async function go(t: any, engine: string, again: boolean): Promise<void> { if (again) return go(t, engine, false); return inBrowser(t, async () => {}, engine as any); }
test("p204", async (t) => { await go(t, "firefox", true); });
