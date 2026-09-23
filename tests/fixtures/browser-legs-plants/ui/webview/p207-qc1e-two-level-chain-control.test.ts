import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
async function go(t: any, e: string): Promise<void> { return inBrowser(t, async () => {}, e as any); }
async function outer(t: any, e: string): Promise<void> { return go(t, e); }
test("p207", async (t) => { await outer(t, "firefox"); });
