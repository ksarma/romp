import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p309", async (t) => { const p = inBrowser(t, async () => {}); await p.catch(() => {}); });
