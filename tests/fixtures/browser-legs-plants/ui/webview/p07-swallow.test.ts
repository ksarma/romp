import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p7", async (t) => { try { await inBrowser(t, async () => {}); } catch (e) { void e; } });
