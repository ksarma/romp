import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p47", async (t) => { const inBrowser = async (x: any, f: any) => open(x, f); await inBrowser(t, async () => {}); });
async function open(t: any, f: any): Promise<void> { await inBrowser(t, f); }
